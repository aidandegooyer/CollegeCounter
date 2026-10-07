from unittest.mock import MagicMock, patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from cc.models import Competition, Match, Participant, Season, Team
from cc.views import (
    calculate_new_elo,
    recalculate_all_elos,
    revert_match_elos,
    update_match_elos,
    update_regentsleague_match,
)


class EloTrackingTestCase(TestCase):
    def setUp(self):
        self.alpha = Team.objects.create(name="Alpha", elo=1000)
        self.bravo = Team.objects.create(name="Bravo", elo=1200)
        self.charlie = Team.objects.create(name="Charlie", elo=900)

    def make_match(self, winner=None, status="completed", **kwargs):
        defaults = dict(
            team1=self.alpha,
            team2=self.bravo,
            date="2025-10-01T18:00:00Z",
            status=status,
            winner=winner,
        )
        defaults.update(kwargs)
        return Match.objects.create(**defaults)

    def elos(self):
        return [
            Team.objects.get(pk=t.pk).elo for t in (self.alpha, self.bravo, self.charlie)
        ]


class ApplyRevertTests(EloTrackingTestCase):
    def test_apply_records_before_and_change(self):
        match = self.make_match(winner=self.alpha)
        self.assertTrue(update_match_elos(match))

        expected_alpha = calculate_new_elo(1000, 1200, 1.0)
        expected_bravo = calculate_new_elo(1200, 1000, 0.0)
        self.assertEqual(self.elos()[:2], [expected_alpha, expected_bravo])

        match.refresh_from_db()
        self.assertTrue(match.elo_applied)
        self.assertEqual(match.team1_elo_before, 1000)
        self.assertEqual(match.team2_elo_before, 1200)
        self.assertEqual(match.team1_elo_change, expected_alpha - 1000)
        self.assertEqual(match.team2_elo_change, expected_bravo - 1200)

    def test_apply_is_idempotent(self):
        match = self.make_match(winner=self.alpha)
        update_match_elos(match)
        after_first = self.elos()

        # Fresh instance, as a platform refresh would load it
        self.assertFalse(update_match_elos(Match.objects.get(pk=match.pk)))
        self.assertEqual(self.elos(), after_first)

    def test_not_applied_without_winner_or_completion(self):
        self.assertFalse(update_match_elos(self.make_match(winner=None)))
        self.assertFalse(
            update_match_elos(self.make_match(winner=self.alpha, status="scheduled"))
        )
        self.assertEqual(self.elos(), [1000, 1200, 900])

    def test_revert_restores_elo_and_clears_fields(self):
        match = self.make_match(winner=self.alpha)
        update_match_elos(match)

        self.assertTrue(revert_match_elos(match))
        self.assertEqual(self.elos(), [1000, 1200, 900])
        match.refresh_from_db()
        self.assertFalse(match.elo_applied)
        self.assertIsNone(match.team1_elo_change)

        # Nothing left to revert
        self.assertFalse(revert_match_elos(match))
        self.assertEqual(self.elos(), [1000, 1200, 900])

    def test_legacy_applied_match_is_not_reverted_or_reapplied(self):
        match = self.make_match(winner=self.alpha, elo_applied=True)

        self.assertFalse(revert_match_elos(match))
        self.assertFalse(update_match_elos(match))
        self.assertEqual(self.elos(), [1000, 1200, 900])


@override_settings(DEBUG=True)
class AdminEndpointTests(EloTrackingTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer dev")

    def patch_match(self, match, data):
        url = reverse("update_match", args=[match.id])
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_completing_match_applies_and_response_includes_elo(self):
        match = self.make_match(status="scheduled")
        body = self.patch_match(
            match, {"status": "completed", "winner_id": str(self.alpha.id)}
        )
        self.assertTrue(body["elo"]["applied"])
        self.assertGreater(body["elo"]["team1_change"], 0)
        self.assertLess(body["elo"]["team2_change"], 0)

    def test_score_edit_on_completed_match_does_not_reapply(self):
        match = self.make_match(winner=self.alpha)
        update_match_elos(match)
        after_apply = self.elos()

        self.patch_match(match, {"score_team1": 2, "score_team2": 1})
        self.assertEqual(self.elos(), after_apply)

    def test_winner_change_reverts_then_applies_for_new_winner(self):
        match = self.make_match(winner=self.alpha)
        update_match_elos(match)

        self.patch_match(match, {"winner_id": str(self.bravo.id)})

        self.assertEqual(
            self.elos()[:2],
            [calculate_new_elo(1000, 1200, 0.0), calculate_new_elo(1200, 1000, 1.0)],
        )

    def test_uncompleting_match_reverts(self):
        match = self.make_match(winner=self.alpha)
        update_match_elos(match)

        self.patch_match(match, {"status": "scheduled", "winner_id": ""})
        self.assertEqual(self.elos(), [1000, 1200, 900])
        match.refresh_from_db()
        self.assertFalse(match.elo_applied)

    def test_team_change_reverts_old_team_and_applies_to_new_team(self):
        match = self.make_match(winner=self.alpha)
        update_match_elos(match)

        self.patch_match(match, {"team2_id": str(self.charlie.id)})

        alpha, bravo, charlie = self.elos()
        self.assertEqual(bravo, 1200)  # fully restored
        self.assertEqual(alpha, calculate_new_elo(1000, 900, 1.0))
        self.assertEqual(charlie, calculate_new_elo(900, 1000, 0.0))

    def test_delete_match_reverts(self):
        match = self.make_match(winner=self.alpha)
        update_match_elos(match)

        response = self.client.delete(reverse("delete_match", args=[match.id]))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.elos(), [1000, 1200, 900])

    def test_apply_and_revert_endpoints(self):
        match = self.make_match(winner=self.alpha)
        apply_url = reverse("apply_match_elo", args=[match.id])
        revert_url = reverse("revert_match_elo", args=[match.id])

        self.assertEqual(self.client.post(apply_url).status_code, 200)
        self.assertEqual(self.client.post(apply_url).status_code, 400)  # already applied

        response = self.client.post(revert_url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.elos(), [1000, 1200, 900])
        self.assertEqual(self.client.post(revert_url).status_code, 400)  # nothing applied


class RecalculateTests(EloTrackingTestCase):
    def test_reset_recalculation_populates_tracking(self):
        first = self.make_match(winner=self.alpha, date="2025-10-01T18:00:00Z")
        second = self.make_match(
            winner=self.charlie,
            team1=self.bravo,
            team2=self.charlie,
            date="2025-10-02T18:00:00Z",
        )
        # Legacy state: applied without tracked changes
        Match.objects.update(elo_applied=True)

        result = recalculate_all_elos(reset_to_default=True, default_elo=1000)
        self.assertEqual(result["processed_count"], 2)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.team1_elo_before, 1000)
        bravo_after_first = 1000 + first.team2_elo_change
        self.assertEqual(second.team1_elo_before, bravo_after_first)

    def test_non_reset_recalculation_skips_applied_matches(self):
        applied = self.make_match(winner=self.alpha)
        update_match_elos(applied)
        self.make_match(
            winner=self.charlie,
            team1=self.bravo,
            team2=self.charlie,
            date="2025-10-02T18:00:00Z",
        )

        result = recalculate_all_elos(reset_to_default=False)
        self.assertEqual(result["processed_count"], 1)


class PlatformRefreshTests(EloTrackingTestCase):
    def setUp(self):
        super().setUp()
        self.season = Season.objects.create(
            name="S", start_date="2025-08-01", end_date="2026-05-01"
        )
        self.competition = Competition.objects.create(name="Regents")
        for team, rid in [(self.alpha, 1), (self.bravo, 2)]:
            Participant.objects.create(
                team=team,
                competition=self.competition,
                season=self.season,
                regentsleague_id=rid,
            )

    def refresh(self, match, winner_id, score=(1, 0)):
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "id": 42,
            "status": "Completed",
            "date": "2025-10-01T18:00:00Z",
            "team1": {"id": 1},
            "team2": {"id": 2},
            "score_team1": score[0],
            "score_team2": score[1],
            "winner": {"id": winner_id},
        }
        with patch("cc.views.platform_sync.requests.get", return_value=response):
            update_regentsleague_match(Match.objects.get(pk=match.pk))

    def test_score_change_on_completed_match_does_not_double_apply(self):
        match = self.make_match(
            winner=self.alpha,
            regentsleague_id=42,
            competition=self.competition,
            season=self.season,
            platform="regentsleague",
        )
        update_match_elos(match)
        after_apply = self.elos()

        self.refresh(match, winner_id=1, score=(2, 0))
        self.assertEqual(self.elos(), after_apply)

    def test_winner_flip_on_refresh_reverts_and_reapplies(self):
        match = self.make_match(
            winner=self.alpha,
            regentsleague_id=42,
            competition=self.competition,
            season=self.season,
            platform="regentsleague",
        )
        update_match_elos(match)

        self.refresh(match, winner_id=2, score=(0, 1))
        self.assertEqual(
            self.elos()[:2],
            [calculate_new_elo(1000, 1200, 0.0), calculate_new_elo(1200, 1000, 1.0)],
        )


class MigrationCompatibilityTests(EloTrackingTestCase):
    def test_insert_without_elo_applied_column_uses_db_default(self):
        """Code deployed before migration 0012 inserts matches without the column."""
        if connection.vendor != "postgresql":
            self.skipTest("DB-level default is only set on PostgreSQL")
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO cc_match (id, team1_id, team2_id, date, status, "
                "score_team1, score_team2, platform) VALUES "
                "(gen_random_uuid(), %s, %s, now(), 'scheduled', 0, 0, 'other')",
                [self.alpha.id, self.bravo.id],
            )
        self.assertFalse(Match.objects.get().elo_applied)


class BackfillMigrationTests(TransactionTestCase):
    """0013 marks pre-existing completed matches as applied, nothing else."""

    before = [("cc", "0012_match_elo_tracking")]
    after = [("cc", "0013_backfill_match_elo_applied")]

    def tearDown(self):
        MigrationExecutor(connection).migrate(
            MigrationExecutor(connection).loader.graph.leaf_nodes()
        )

    def test_backfill(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        apps = executor.loader.project_state(self.before).apps
        OldTeam = apps.get_model("cc", "Team")
        OldMatch = apps.get_model("cc", "Match")

        a = OldTeam.objects.create(name="A", elo=1000)
        b = OldTeam.objects.create(name="B", elo=1000)
        common = dict(team1=a, team2=b, date="2025-10-01T18:00:00Z")
        completed = OldMatch.objects.create(status="completed", winner=a, **common)
        no_winner = OldMatch.objects.create(status="completed", **common)
        scheduled = OldMatch.objects.create(status="scheduled", **common)

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.after)

        applied = dict(Match.objects.values_list("id", "elo_applied"))
        self.assertEqual(
            applied,
            {completed.id: True, no_winner.id: False, scheduled.id: False},
        )
        self.assertIsNone(Match.objects.get(pk=completed.pk).team1_elo_change)
        self.assertEqual(
            list(Team.objects.order_by("name").values_list("elo", flat=True)),
            [1000, 1000],
        )
