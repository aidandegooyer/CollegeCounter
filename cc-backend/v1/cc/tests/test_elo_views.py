"""Elo endpoints not already covered by test_elo_tracking."""

import uuid
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from cc.models import Match, Participant, Player, Ranking, RankingItem, Season, Team
from cc.views import (
    apply_elos_in_date_order,
    delete_match_and_revert_elo,
    recalculate_all_elos,
    update_match_elos,
)

from .helpers import Fixtures, admin_settings, dev_client, past_season


@admin_settings
class CalculateTeamElosTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def add_players(self, team, elos, benched=False):
        for i, elo in enumerate(elos):
            Player.objects.create(name=f"{team.name}-{i}-{elo}", team=team, elo=elo, benched=benched)

    def test_uses_top_five_active_players(self):
        # Top 5 of [2000, 1800, 1600, 1400, 1200, 100]; the benched player is ignored
        self.add_players(self.alpha, [2000, 1800, 1600, 1400, 1200, 100])
        self.add_players(self.alpha, [3000], benched=True)
        # Only one active player, so not enough to calculate
        self.add_players(self.bravo, [1500])

        response = self.client.post(reverse("calculate_team_elos"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["updated_teams"], 1)
        self.assertEqual(body["teams_without_enough_players"], 1)
        self.assertEqual(body["total_teams_processed"], 2)

        self.alpha.refresh_from_db()
        self.bravo.refresh_from_db()
        # mean 1600, sample stdev ~316.23 -> 1600 - 31.6 = 1568
        self.assertEqual(self.alpha.elo, 1568)
        self.assertEqual(self.bravo.elo, 1200)

    def test_ignores_zero_elo_players(self):
        self.add_players(self.alpha, [1500, 0])
        self.client.post(reverse("calculate_team_elos"))
        self.alpha.refresh_from_db()
        self.assertEqual(self.alpha.elo, 1000)

    def test_only_default_elo(self):
        self.add_players(self.alpha, [1500, 1500])
        self.add_players(self.bravo, [1500, 1500])
        response = self.client.post(
            reverse("calculate_team_elos"),
            {"only_default_elo": True, "default_elo": 1000},
            format="json",
        )
        self.assertEqual(response.json()["total_teams_processed"], 1)
        self.alpha.refresh_from_db()
        self.bravo.refresh_from_db()
        self.assertEqual(self.alpha.elo, 1500)
        self.assertEqual(self.bravo.elo, 1200)

    def test_error_is_500(self):
        with patch("cc.views.elo.Team.objects.all", side_effect=RuntimeError("db")):
            response = self.client.post(reverse("calculate_team_elos"))
        self.assertEqual(response.status_code, 500)


@admin_settings
class RankingSnapshotTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_snapshot_ranks_active_teams_by_elo(self):
        charlie = Team.objects.create(name="Charlie", elo=1100)
        Team.objects.create(name="Inactive", elo=5000)
        Team.objects.create(name="Zero", elo=0)
        Participant.objects.create(team=self.alpha, season=self.season)
        Match.objects.create(
            team1=charlie, team2=self.bravo, date="2025-10-01T00:00:00Z", season=self.season
        )

        response = self.client.post(
            reverse("create_ranking_snapshot"), {"season_id": str(self.season.id)}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["teams_ranked"], 3)
        ranking = Ranking.objects.get()
        self.assertEqual(ranking.season, self.season)
        items = RankingItem.objects.filter(ranking=ranking).order_by("rank")
        self.assertEqual(
            [(i.rank, i.team.name, i.elo) for i in items],
            [(1, "Bravo", 1200), (2, "Charlie", 1100), (3, "Alpha", 1000)],
        )

    def test_defaults_to_most_recent_season(self):
        old = past_season()
        Participant.objects.create(team=self.alpha, season=old)
        Participant.objects.create(team=self.bravo, season=self.season)
        response = self.client.post(reverse("create_ranking_snapshot"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["season_name"], "Current Season")
        self.assertEqual(RankingItem.objects.get().team, self.bravo)

    def test_errors(self):
        url = reverse("create_ranking_snapshot")
        self.assertEqual(
            self.client.post(url, {"season_id": str(uuid.uuid4())}, format="json").status_code,
            404,
        )
        # Season with no active teams
        self.assertEqual(self.client.post(url).status_code, 400)
        Season.objects.all().delete()
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertFalse(Ranking.objects.exists())

    def test_unexpected_error_is_500(self):
        Participant.objects.create(team=self.alpha, season=self.season)
        with patch("cc.views.elo.Ranking.objects.create", side_effect=RuntimeError):
            response = self.client.post(reverse("create_ranking_snapshot"))
        self.assertEqual(response.status_code, 500)


@admin_settings
class RecalculateEndpointTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_recalculate_resets_by_default(self):
        Match.objects.create(
            team1=self.alpha,
            team2=self.bravo,
            date="2025-10-01T00:00:00Z",
            status="completed",
            winner=self.alpha,
        )
        response = self.client.post(reverse("recalculate_elos"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["summary"]["processed_count"], 1)
        self.assertTrue(body["summary"]["reset_to_default"])
        self.assertEqual(body["summary"]["default_elo"], 1000)
        self.assertEqual(body["message"], "ELO recalculation completed successfully")
        self.alpha.refresh_from_db()
        self.bravo.refresh_from_db()
        self.assertEqual((self.alpha.elo, self.bravo.elo), (1075, 925))

    def test_response_limits_elo_changes_to_ten(self):
        for day in range(1, 13):
            Match.objects.create(
                team1=self.alpha,
                team2=self.bravo,
                date=f"2025-10-{day:02d}T00:00:00Z",
                status="completed",
                winner=self.alpha,
            )
        body = self.client.post(reverse("recalculate_elos")).json()
        self.assertEqual(len(body["elo_changes"]), 10)
        self.assertEqual(body["total_elo_changes"], 12)

    def test_reports_errors(self):
        Match.objects.create(
            team1=self.alpha,
            team2=self.bravo,
            date="2025-10-01T00:00:00Z",
            status="completed",
            winner=self.alpha,
        )
        with patch("cc.views.elo.update_match_elos", side_effect=RuntimeError("bad")):
            body = self.client.post(reverse("recalculate_elos")).json()
        self.assertEqual(body["summary"]["error_count"], 1)
        self.assertIn("1 match(es) skipped", body["message"])

    def test_unexpected_error_is_500(self):
        with patch("cc.views.elo.recalculate_all_elos", side_effect=RuntimeError):
            response = self.client.post(reverse("recalculate_elos"))
        self.assertEqual(response.status_code, 500)

    def test_recalculate_skips_bye_matches(self):
        bye = Team.objects.create(name="BYE")
        Match.objects.create(
            team1=self.alpha, team2=bye, date="2025-10-01T00:00:00Z", status="completed", winner=self.alpha
        )
        result = recalculate_all_elos(reset_to_default=True)
        self.assertEqual(result["total_matches"], 0)


@admin_settings
class ApplyRevertEndpointErrorTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def make(self, **kwargs):
        defaults = dict(team1=self.alpha, team2=self.bravo, date="2025-10-01T00:00:00Z")
        defaults.update(kwargs)
        return Match.objects.create(**defaults)

    def test_apply_rejects_unfinished_or_applied(self):
        scheduled = self.make()
        response = self.client.post(reverse("apply_match_elo", args=[scheduled.id]))
        self.assertEqual(response.status_code, 400)

        applied = self.make(status="completed", winner=self.alpha, elo_applied=True)
        response = self.client.post(reverse("apply_match_elo", args=[applied.id]))
        self.assertEqual(response.status_code, 400)

    def test_apply_with_winner_not_in_match(self):
        outsider = Team.objects.create(name="Outsider")
        match = self.make(status="completed", winner=outsider)
        response = self.client.post(reverse("apply_match_elo", args=[match.id]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Unable to apply Elo for this match")

    def test_apply_unexpected_error_is_500(self):
        match = self.make(status="completed", winner=self.alpha)
        with patch("cc.views.elo.update_match_elos", side_effect=RuntimeError):
            response = self.client.post(reverse("apply_match_elo", args=[match.id]))
        self.assertEqual(response.status_code, 500)

    def test_revert_rejects_unapplied_or_legacy(self):
        unapplied = self.make()
        response = self.client.post(reverse("revert_match_elo", args=[unapplied.id]))
        self.assertEqual(response.status_code, 400)

        legacy = self.make(status="completed", winner=self.alpha, elo_applied=True)
        response = self.client.post(reverse("revert_match_elo", args=[legacy.id]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("before changes were tracked", response.json()["error"])

    def test_revert_conflict_when_already_reverted(self):
        match = self.make(status="completed", winner=self.alpha)
        update_match_elos(match)
        with patch("cc.views.elo.revert_match_elos", return_value=False):
            response = self.client.post(reverse("revert_match_elo", args=[match.id]))
        self.assertEqual(response.status_code, 409)

    def test_revert_unexpected_error_is_500(self):
        match = self.make(status="completed", winner=self.alpha)
        update_match_elos(match)
        with patch("cc.views.elo.revert_match_elos", side_effect=RuntimeError):
            response = self.client.post(reverse("revert_match_elo", args=[match.id]))
        self.assertEqual(response.status_code, 500)


class EloHelperTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()

    def test_update_match_elos_ignores_winner_outside_match(self):
        outsider = Team.objects.create(name="Outsider")
        match = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T00:00:00Z", status="completed", winner=outsider
        )
        self.assertFalse(update_match_elos(match))

    def test_apply_in_date_order_puts_undated_last(self):
        dated = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T00:00:00Z", status="completed", winner=self.alpha
        )
        undated = Match(
            team1=self.alpha, team2=self.bravo, date=None, status="completed", winner=self.bravo
        )
        applied_order = []
        with patch(
            "cc.views.elo.update_match_elos",
            side_effect=lambda m: applied_order.append(m) or True,
        ):
            count = apply_elos_in_date_order([undated, dated])
        self.assertEqual(count, 2)
        self.assertEqual(applied_order, [dated, undated])

    def test_delete_without_elo_returns_no_warning(self):
        match = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T00:00:00Z"
        )
        self.assertIsNone(delete_match_and_revert_elo(match))
        self.assertFalse(Match.objects.exists())
