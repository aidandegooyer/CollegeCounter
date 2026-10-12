"""Unexpected exceptions inside admin endpoints become JSON 500s, not crashes."""

import uuid
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from cc.models import Event, EventMatch, Match, Player
from cc.views import import_regentsleague_match_data

from .helpers import Fixtures, admin_settings, dev_client


@admin_settings
class UnexpectedErrorTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()
        self.match = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T00:00:00Z"
        )
        self.event = Event.objects.create(
            name="Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        EventMatch.objects.create(match=self.match, event=self.event)

    def assert_500(self, target, method, url, data=None):
        with patch(target, side_effect=RuntimeError("boom")):
            response = getattr(self.client, method)(url, data or {}, format="json")
        self.assertEqual(response.status_code, 500, response.content)
        self.assertIn("boom", response.json()["error"])

    def test_admin_data(self):
        self.assert_500(
            "cc.views.admin_data.Season.objects.create",
            "post",
            reverse("create_season"),
            {"name": "x", "start_date": "2026-01-01T00:00:00Z", "end_date": "2026-02-01T00:00:00Z"},
        )
        self.assert_500(
            "cc.views.admin_data.EventMatch.objects.all",
            "post",
            reverse("clear_database"),
            {"security_key": "confirm-database-clear-123"},
        )
        self.assert_500(
            "cc.views.admin_data.Competition.objects.get",
            "delete",
            reverse("delete_competition", args=[self.competition.id]),
            {"security_key": "confirm-delete-competition-789"},
        )
        self.assert_500(
            "cc.views.admin_data.Competition.objects.all", "get", reverse("list_competitions")
        )

    def test_teams(self):
        self.assert_500("cc.views.teams.Player.objects.filter", "post", reverse("update_player_elo"))
        self.assert_500("cc.views.teams.Player.objects.all", "post", reverse("reset_player_elo"))
        self.assert_500(
            "cc.views.teams.Player.objects.filter",
            "post",
            reverse("merge_teams"),
            {"primary_team_id": str(self.alpha.id), "secondary_team_id": str(self.bravo.id)},
        )

    def test_matches(self):
        self.assert_500(
            "cc.views.matches.Match.objects.create",
            "post",
            reverse("create_event_match"),
            {
                "team1_id": str(self.alpha.id),
                "team2_id": str(self.bravo.id),
                "event_id": str(self.event.id),
                "round": 1,
                "num_in_bracket": 1,
                "date": "2025-10-01T00:00:00Z",
            },
        )
        self.assert_500(
            "cc.views.matches.save_match_and_sync_elo",
            "patch",
            reverse("update_event_match", args=[self.match.id]),
        )
        self.assert_500(
            "cc.views.matches.delete_match_and_revert_elo",
            "delete",
            reverse("delete_match", args=[self.match.id]),
        )

    def test_list_matches_survives_event_match_lookup_error(self):
        with patch("cc.views.matches.EventMatch.objects.filter", side_effect=RuntimeError):
            response = self.client.get(reverse("list_matches"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()[0]["event_match"])

    def test_create_competition(self):
        self.assert_500(
            "cc.models.Competition.objects.create",
            "post",
            reverse("create_competition"),
            {"name": "New"},
        )

    def test_match_participants_post(self):
        self.assert_500(
            "cc.views.imports.Participant.objects.get",
            "post",
            reverse("match_participants"),
            {"participant_id": str(uuid.uuid4()), "team_id": str(self.alpha.id)},
        )


@admin_settings
class SmallBranchTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_update_player_elo_skips_blank_steam_id(self):
        Player.objects.create(name="blank", steam_id="", elo=1234)
        with patch("cc.views.teams.requests.get") as get:
            response = self.client.post(reverse("update_player_elo"))
        get.assert_not_called()
        self.assertEqual(response.json()["updated_players"], 0)

    def test_regentsleague_import_team2_winner(self):
        import_regentsleague_match_data(
            [
                {
                    "id": 9,
                    "status": "Completed",
                    "date": "2025-10-01T18:00:00Z",
                    "team1": {"id": 1, "name": "Alpha"},
                    "team2": {"id": 2, "name": "Bravo"},
                    "score_team1": 0,
                    "score_team2": 2,
                    "winner": {"id": 2},
                }
            ],
            self.competition,
            self.season,
        )
        self.assertEqual(Match.objects.get().winner, self.bravo)

    def test_public_matches_invalid_calendar_date_is_400(self):
        for param in ("date_from", "date_to"):
            with self.subTest(param=param):
                response = self.client.get(
                    reverse("public_matches") + f"?{param}=2025-13-45T00:00:00"
                )
                self.assertEqual(response.status_code, 400)
