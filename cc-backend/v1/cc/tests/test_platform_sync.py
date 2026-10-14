"""Refreshing matches from Faceit / LeagueSpot / Regents League."""

import unittest
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cc.models import Competition, Match, Participant
from cc.views import (
    update_faceit_match,
    update_leaguespot_match,
    update_regentsleague_match,
)
from cc.views.platform_sync import PlatformSyncError

from .helpers import Fixtures, admin_settings, dev_client, fake_response


class SyncFixtures(Fixtures):
    def setUp(self):
        self.make_base()

    def make_match(self, **kwargs):
        defaults = dict(
            team1=self.alpha,
            team2=self.bravo,
            date=timezone.now() - timedelta(days=1),
            competition=self.competition,
            season=self.season,
        )
        defaults.update(kwargs)
        return Match.objects.create(**defaults)


@admin_settings
class UpdateMatchesEndpointTests(SyncFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.client = dev_client()

    def post(self, data=None, faceit=False, leaguespot=False, regents=False):
        with patch(
            "cc.views.platform_sync.update_faceit_match", return_value=faceit
        ) as f, patch(
            "cc.views.platform_sync.update_leaguespot_match", return_value=leaguespot
        ) as l, patch(
            "cc.views.platform_sync.update_regentsleague_match", return_value=regents
        ) as r:
            response = self.client.post(reverse("update_matches"), data or {}, format="json")
        return response, (f, l, r)

    def test_dispatches_by_platform_and_reports_results(self):
        faceit = self.make_match(platform="faceit")
        leaguespot = self.make_match(platform="leaguespot")
        regents = self.make_match(platform="regentsleague")
        self.make_match(platform="other")

        response, (f, l, r) = self.post(faceit=True, leaguespot=False, regents=True)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["updated_count"], 2)
        self.assertEqual(body["total_processed"], 4)
        statuses = {result["match_id"]: result["status"] for result in body["results"]}
        self.assertEqual(
            statuses,
            {str(faceit.id): "updated", str(leaguespot.id): "no_changes", str(regents.id): "updated"},
        )
        self.assertEqual(f.call_count, 1)
        self.assertEqual(l.call_count, 1)
        self.assertEqual(r.call_count, 1)

    def test_default_skips_completed_and_far_future_matches(self):
        self.make_match(platform="faceit", status="completed")
        self.make_match(platform="faceit", date=timezone.now() + timedelta(weeks=3))
        soon = self.make_match(platform="faceit", date=timezone.now() + timedelta(days=3))
        live_future = self.make_match(
            platform="faceit", status="in_progress", date=timezone.now() + timedelta(weeks=3)
        )
        response, (f, _, _) = self.post()
        processed = {result["match_id"] for result in response.json()["results"]}
        self.assertEqual(processed, {str(soon.id), str(live_future.id)})

    def test_filters(self):
        completed = self.make_match(platform="faceit", status="completed")
        other = self.make_match(platform="leaguespot")
        response, _ = self.post({"status_filter": "completed"})
        self.assertEqual(response.json()["total_processed"], 1)

        response, _ = self.post({"platform": "LeagueSpot"})
        self.assertEqual(
            [result["match_id"] for result in response.json()["results"]], [str(other.id)]
        )

        response, _ = self.post({"match_ids": [str(completed.id)], "auto_detect": False})
        self.assertEqual(
            [result["match_id"] for result in response.json()["results"]], [str(completed.id)]
        )

    def test_competition_filter(self):
        mine = self.make_match(platform="faceit")
        self.make_match(platform="faceit", competition=Competition.objects.create(name="Other"))
        response, _ = self.post({"competition_id": str(self.competition.id)})
        self.assertEqual(
            [result["match_id"] for result in response.json()["results"]], [str(mine.id)]
        )
        for competition_id in ("nope", str(uuid.uuid4())):
            response, _ = self.post({"competition_id": competition_id})
            self.assertEqual(response.status_code, 400)

    def test_errors_are_counted_per_match(self):
        self.make_match(platform="faceit")
        with patch(
            "cc.views.platform_sync.update_faceit_match", side_effect=RuntimeError("api down")
        ):
            response = self.client.post(reverse("update_matches"), {}, format="json")
        body = response.json()
        self.assertEqual(body["error_count"], 1)
        self.assertEqual(body["results"][0]["error"], "api down")

    def test_bad_request_data_is_500(self):
        response = self.client.post(
            reverse("update_matches"), {"match_ids": ["not-a-uuid"]}, format="json"
        )
        self.assertEqual(response.status_code, 500)


@override_settings(FACEIT_API_KEY="faceit-key")
class UpdateFaceitMatchTests(SyncFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.match = self.make_match(platform="faceit", url="https://faceit.com/room/1-x")

    def refresh(self, data=None, response=None):
        upstream = response or fake_response(json_data=data)
        with patch("cc.views.platform_sync.requests.get", return_value=upstream) as get:
            updated = update_faceit_match(Match.objects.get(pk=self.match.pk))
        self.match.refresh_from_db()
        return updated, get

    def finished(self, winner="faction1", score=(2, 1), faction1="f-alpha", faction2="f-bravo"):
        return {
            "status": "FINISHED",
            "finished_at": 1759341600,
            "teams": {
                "faction1": {"faction_id": faction1},
                "faction2": {"faction_id": faction2},
            },
            "results": {
                "winner": winner,
                "score": {"faction1": score[0], "faction2": score[1]},
            },
        }

    def test_no_url_is_noop_and_missing_api_key_fails(self):
        self.match.url = None
        self.match.save()
        self.assertFalse(update_faceit_match(self.match))
        self.match.url = "https://faceit.com/room/1-x"
        with override_settings(FACEIT_API_KEY=""):
            with self.assertRaises(PlatformSyncError):
                update_faceit_match(self.match)

    def test_non_200_fails(self):
        with self.assertRaises(PlatformSyncError):
            self.refresh(response=fake_response(status_code=404))
        with patch(
            "cc.views.platform_sync.requests.get",
            return_value=fake_response(json_data={"status": "READY"}),
        ) as get:
            update_faceit_match(Match.objects.get(pk=self.match.pk))
        self.assertEqual(
            get.call_args.args[0], f"https://open.faceit.com/data/v4/matches/1-{self.match.id}"
        )
        self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer faceit-key"})

    def test_unknown_state_keeps_status_and_records_it(self):
        updated, _ = self.refresh({"status": "SOMETHING_NEW"})
        self.assertTrue(updated)
        self.assertEqual(self.match.status, "scheduled")
        self.assertEqual(self.match.platform_status, "SOMETHING_NEW")
        updated, _ = self.refresh({"status": "SOMETHING_NEW"})
        self.assertFalse(updated)

    def test_veto_is_live(self):
        self.refresh({"status": "VOTING"})
        self.assertEqual(self.match.status, "in_progress")
        self.refresh({"status": "ABORTED"})
        self.assertEqual(self.match.status, "cancelled")

    def test_live_scores_without_a_winner(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season, faceit_id="f-alpha"
        )
        data = dict(self.finished(winner="faction1", score=(1, 0)), status="ONGOING")
        updated, _ = self.refresh(data)
        self.assertTrue(updated)
        self.assertEqual(self.match.status, "in_progress")
        self.assertEqual((self.match.score_team1, self.match.score_team2), (1, 0))
        self.assertIsNone(self.match.winner)
        self.assertFalse(self.match.elo_applied)

    def test_status_and_date_updates(self):
        updated, _ = self.refresh({"status": "ONGOING", "started_at": 1759341600})
        self.assertTrue(updated)
        self.assertEqual(self.match.status, "in_progress")
        self.assertEqual(int(self.match.date.timestamp()), 1759341600)

        updated, _ = self.refresh({"status": "CANCELLED", "scheduled_at": 1759341600})
        self.assertTrue(updated)
        self.assertEqual(self.match.status, "cancelled")

    @unittest.expectedFailure
    def test_unchanged_refresh_is_not_an_update(self):
        # BUG: safe_parse_datetime returns a naive datetime for unix timestamps
        # (which is what Faceit sends), and a naive datetime never equals the
        # aware one from the DB. So every refresh re-saves the match and
        # reports it as updated.
        data = {"status": "CANCELLED", "scheduled_at": 1759341600}
        self.refresh(data)
        updated, _ = self.refresh(data)
        self.assertFalse(updated)

    def test_finished_maps_factions_via_team1_participant(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season, faceit_id="f-alpha"
        )
        updated, _ = self.refresh(self.finished(winner="faction1", score=(2, 1)))
        self.assertTrue(updated)
        self.assertEqual(self.match.status, "completed")
        self.assertEqual((self.match.score_team1, self.match.score_team2), (2, 1))
        self.assertEqual(self.match.winner, self.alpha)
        self.assertTrue(self.match.elo_applied)

    def test_finished_with_team1_as_faction2(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season, faceit_id="f-alpha"
        )
        self.refresh(
            self.finished(winner="faction1", score=(2, 1), faction1="f-bravo", faction2="f-alpha")
        )
        self.assertEqual((self.match.score_team1, self.match.score_team2), (1, 2))
        self.assertEqual(self.match.winner, self.bravo)

    def test_finished_falls_back_to_team2_participant(self):
        Participant.objects.create(
            team=self.bravo, competition=self.competition, season=self.season, faceit_id="f-bravo"
        )
        for faction1, faction2, expected_winner in [
            ("f-bravo", "f-alpha", self.bravo),
            ("f-alpha", "f-bravo", self.alpha),
        ]:
            with self.subTest(faction1=faction1):
                self.refresh(
                    self.finished(winner="faction1", faction1=faction1, faction2=faction2)
                )
                self.assertEqual(self.match.winner, expected_winner)

    def test_finished_without_mapping_only_updates_status(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season, faceit_id="other"
        )
        updated, _ = self.refresh(self.finished())
        self.assertTrue(updated)
        self.assertEqual(self.match.status, "completed")
        self.assertIsNone(self.match.winner)

    def test_finished_without_any_participants(self):
        updated, _ = self.refresh(self.finished())
        self.assertTrue(updated)
        self.assertIsNone(self.match.winner)

    def test_finished_without_results(self):
        data = self.finished()
        data["results"] = {}
        updated, _ = self.refresh(data)
        self.assertTrue(updated)
        self.assertIsNone(self.match.winner)

    def test_unknown_winner_faction_clears_winner(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season, faceit_id="f-alpha"
        )
        self.match.winner = self.alpha
        self.match.status = "completed"
        self.match.save()
        self.refresh(self.finished(winner=None))
        self.assertIsNone(self.match.winner)

    def test_errors_are_raised(self):
        upstream = fake_response()  # json() raises
        with patch("cc.views.platform_sync.requests.get", return_value=upstream):
            with self.assertRaises(ValueError):
                update_faceit_match(self.match)


class UpdateLeaguespotMatchTests(SyncFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.match = self.make_match(platform="leaguespot")

    def refresh(self, match_data, participants=None, participants_status=200, match_status=200):
        match_url = f"https://api.leaguespot.gg/api/v2/matches/{self.match.id}"
        participants_url = f"https://api.leaguespot.gg/api/v1/matches/{self.match.id}/participants"

        def fake_get(url, headers, timeout):
            if url == match_url:
                return fake_response(status_code=match_status, json_data=match_data)
            if url == participants_url:
                return fake_response(status_code=participants_status, json_data=participants)
            raise AssertionError(f"unexpected url {url}")

        with patch("cc.views.platform_sync.requests.get", side_effect=fake_get):
            updated = update_leaguespot_match(Match.objects.get(pk=self.match.pk))
        self.match.refresh_from_db()
        return updated

    def test_non_200_fails(self):
        with self.assertRaises(PlatformSyncError):
            self.refresh({}, match_status=500)

    def test_scheduled_updates_date_and_status(self):
        self.assertTrue(
            self.refresh({"currentState": 2, "startTimeUTC": "2025-11-01T18:00:00Z"})
        )
        self.assertEqual(self.match.status, "in_progress")
        self.assertEqual(self.match.date.month, 11)
        self.assertFalse(
            self.refresh({"currentState": 2, "startTimeUTC": "2025-11-01T18:00:00Z"})
        )

    def test_unknown_state_keeps_status_and_records_it(self):
        self.match.status = "in_progress"
        self.match.save()
        self.assertTrue(self.refresh({"currentState": 99}))
        self.assertEqual(self.match.status, "in_progress")
        self.assertEqual(self.match.platform_status, "99")

    def test_unchanged_scheduled_match_is_not_saved(self):
        self.refresh({"currentState": 1})
        with patch("cc.views.platform_sync.save_match_and_sync_elo") as save:
            self.assertFalse(self.refresh({"currentState": 1}))
        save.assert_not_called()

    def test_completed_reads_participants(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season,
            playfly_participant_id="pp-alpha",
        )
        Participant.objects.create(
            team=self.bravo, competition=self.competition, season=self.season, playfly_id="t-bravo"
        )
        participants = [
            {"participantId": "pp-alpha", "teamId": "t-alpha", "score": "2", "isWinner": False},
            {"participantId": "pp-bravo", "teamId": "t-bravo", "score": 3, "isWinner": True},
            {"participantId": "pp-ghost", "teamId": "t-ghost", "score": 9, "isWinner": False},
        ]
        updated = self.refresh({"currentState": 3}, participants)
        self.assertTrue(updated)
        self.assertEqual(self.match.status, "completed")
        self.assertEqual((self.match.score_team1, self.match.score_team2), (2, 3))
        self.assertEqual(self.match.winner, self.bravo)
        self.assertTrue(self.match.elo_applied)

    def test_completed_team1_winner(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season, playfly_id="t-alpha"
        )
        Participant.objects.create(
            team=self.bravo, competition=self.competition, season=self.season, playfly_id="t-bravo"
        )
        participants = [
            {"participantId": "a", "teamId": "t-alpha", "score": 1, "isWinner": True},
            {"participantId": "b", "teamId": "t-bravo", "score": 0},
        ]
        self.refresh({"currentState": 3}, participants)
        self.assertEqual(self.match.winner, self.alpha)

    def test_completed_with_too_few_participants(self):
        self.assertTrue(self.refresh({"currentState": 3}, [{"participantId": "x"}]))
        self.assertIsNone(self.match.winner)

    def test_completed_participants_error(self):
        self.assertTrue(self.refresh({"currentState": 3}, participants_status=500))
        self.assertEqual(self.match.status, "completed")
        self.assertIsNone(self.match.winner)

    def test_errors_are_raised(self):
        with patch("cc.views.platform_sync.requests.get", side_effect=ValueError("boom")):
            with self.assertRaises(ValueError):
                update_leaguespot_match(self.match)


class UpdateRegentsleagueErrorTests(SyncFixtures, TestCase):
    def test_non_200_fails(self):
        match = self.make_match(platform="regentsleague", regentsleague_id=5)
        with patch(
            "cc.views.platform_sync.requests.get", return_value=fake_response(status_code=404)
        ) as get:
            with self.assertRaises(PlatformSyncError):
                update_regentsleague_match(match)
        self.assertIn("id=5", get.call_args.args[0])

    def test_status_and_date_only(self):
        match = self.make_match(platform="regentsleague", regentsleague_id=5)
        data = {"status": "In Progress", "date": "2025-11-01T18:00:00Z"}
        with patch(
            "cc.views.platform_sync.requests.get", return_value=fake_response(json_data=data)
        ):
            self.assertTrue(update_regentsleague_match(match))
        match.refresh_from_db()
        self.assertEqual(match.status, "in_progress")

    def test_errors_are_raised(self):
        match = self.make_match(platform="regentsleague", regentsleague_id=5)
        with patch("cc.views.platform_sync.requests.get", side_effect=ValueError("boom")):
            with self.assertRaises(ValueError):
                update_regentsleague_match(match)
