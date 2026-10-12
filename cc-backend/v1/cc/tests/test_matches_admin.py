import unittest
import uuid

from django.test import TestCase, override_settings
from django.urls import reverse

from cc.models import Event, EventMatch, Match, Team

from .helpers import Fixtures, admin_settings, dev_client


class MatchFixtures(Fixtures):
    def setUp(self):
        self.make_base()
        self.client = dev_client()
        self.event = Event.objects.create(
            name="Cup",
            start_date="2025-10-01T00:00:00Z",
            end_date="2025-10-02T00:00:00Z",
            season=self.season,
        )

    def make_match(self, **kwargs):
        defaults = dict(team1=self.alpha, team2=self.bravo, date="2025-10-01T18:00:00Z")
        defaults.update(kwargs)
        return Match.objects.create(**defaults)


@admin_settings
class ListAndGetMatchTests(MatchFixtures, TestCase):
    def test_list_matches_newest_first_with_event_data(self):
        old = self.make_match(date="2025-09-01T00:00:00Z")
        new = self.make_match(
            date="2025-10-01T00:00:00Z",
            status="completed",
            winner=self.alpha,
            season=self.season,
            competition=self.competition,
        )
        EventMatch.objects.create(match=new, event=self.event, round=2, extra_info={"x": 1})

        response = self.client.get(reverse("list_matches"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([m["id"] for m in body], [str(new.id), str(old.id)])
        self.assertEqual(body[0]["winner"]["name"], "Alpha")
        self.assertEqual(body[0]["season"]["name"], "Current Season")
        self.assertEqual(body[0]["competition"]["name"], "League")
        self.assertEqual(body[0]["event_match"]["round"], 2)
        self.assertEqual(body[0]["event_match"]["extra_info"], {"x": 1})
        self.assertIn("elo", body[0])
        self.assertIsNone(body[1]["winner"])
        self.assertIsNone(body[1]["event_match"])
        self.assertIsNone(body[1]["season"])

    def test_get_match(self):
        match = self.make_match(winner=self.bravo, season=self.season, competition=self.competition)
        response = self.client.get(reverse("get_match", args=[match.id]))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["winner"]["name"], "Bravo")
        self.assertEqual(body["team1"]["name"], "Alpha")
        self.assertEqual(body["competition"]["name"], "League")

    def test_get_match_without_optional_relations(self):
        match = self.make_match()
        body = self.client.get(reverse("get_match", args=[match.id])).json()
        self.assertIsNone(body["winner"])
        self.assertIsNone(body["season"])
        self.assertIsNone(body["competition"])

    @unittest.expectedFailure
    def test_get_missing_match_is_404(self):
        # BUG: get_object_or_404 runs inside `except Exception`, which catches
        # Http404 and turns it into a 500. Same for update_match,
        # update_event_match and delete_match.
        response = self.client.get(reverse("get_match", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)


@admin_settings
class CreateMatchTests(MatchFixtures, TestCase):
    def post(self, data, name="create_match"):
        return self.client.post(reverse(name), data, format="json")

    def base(self, **extra):
        data = {
            "team1_id": str(self.alpha.id),
            "team2_id": str(self.bravo.id),
            "date": "2025-10-01T18:00:00Z",
        }
        data.update(extra)
        return data

    def test_create_minimal(self):
        response = self.post(self.base())
        self.assertEqual(response.status_code, 201, response.content)
        match = Match.objects.get(id=response.json()["id"])
        self.assertEqual(match.status, "scheduled")
        self.assertEqual(match.platform, "other")
        self.assertIsNone(response.json()["event_match"])

    def test_create_with_all_fields_and_event(self):
        response = self.post(
            self.base(
                date="2025-10-01T18:00:00Z",
                status="scheduled",
                url="https://faceit.com/room/1",
                score_team1=1,
                score_team2=0,
                platform="faceit",
                season_id=str(self.season.id),
                competition_id=str(self.competition.id),
                winner_id=str(self.bravo.id),
                event_id=str(self.event.id),
                round=3,
                num_in_bracket=2,
                is_bye=True,
                extra_info={"round_name": "Final"},
            )
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["winner"]["name"], "Bravo")
        self.assertEqual(body["season"]["name"], "Current Season")
        self.assertEqual(body["competition"]["name"], "League")
        self.assertEqual(body["event_match"]["round"], 3)
        self.assertTrue(body["event_match"]["is_bye"])
        # Not completed, so Elo isn't applied
        self.assertFalse(body["elo"]["applied"])
        self.assertEqual(EventMatch.objects.get().extra_info, {"round_name": "Final"})

    def test_validation_errors(self):
        cases = [
            ({"team1_id": str(self.alpha.id)}, 400),
            (self.base(team2_id=str(self.alpha.id)), 400),
            (self.base(team2_id=str(uuid.uuid4())), 404),
            (self.base(date="not a date"), 400),
            (self.base(season_id=str(uuid.uuid4())), 404),
            (self.base(competition_id=str(uuid.uuid4())), 404),
            (self.base(winner_id=str(uuid.uuid4())), 400),
        ]
        for data, expected in cases:
            with self.subTest(data=data):
                self.assertEqual(self.post(data).status_code, expected)
        self.assertFalse(Match.objects.exists())

    @unittest.expectedFailure
    def test_date_is_optional(self):
        # BUG: the docstring says date is optional, but Match.date is NOT NULL,
        # so creating a match without one is a 500. The importers hit the same
        # thing for matches with no scheduled/started/finished time.
        data = self.base()
        del data["date"]
        self.assertEqual(self.post(data).status_code, 201)

    def test_unknown_event_deletes_the_new_match(self):
        response = self.post(self.base(event_id=str(uuid.uuid4())))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Match.objects.exists())

    def test_invalid_status_value_is_500(self):
        # status isn't validated against the choices; a too-long value fails at the DB
        response = self.post(self.base(status="x" * 50))
        self.assertEqual(response.status_code, 500)


@admin_settings
class CreateEventMatchTests(MatchFixtures, TestCase):
    def base(self, **extra):
        data = {
            "team1_id": str(self.alpha.id),
            "team2_id": str(self.bravo.id),
            "event_id": str(self.event.id),
            "round": 1,
            "num_in_bracket": 4,
            "date": "2025-10-01T18:00:00Z",
        }
        data.update(extra)
        return data

    def post(self, data):
        return self.client.post(reverse("create_event_match"), data, format="json")

    def test_create_completed_applies_elo(self):
        response = self.post(
            self.base(
                status="completed",
                winner_id=str(self.alpha.id),
                date="2025-10-01T18:00:00Z",
                season_id=str(self.season.id),
                competition_id=str(self.competition.id),
                extra_info={"round_name": "Semis"},
            )
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertTrue(body["elo"]["applied"])
        self.assertEqual(body["event_match"]["num_in_bracket"], 4)
        self.assertEqual(body["winner"]["name"], "Alpha")
        self.alpha.refresh_from_db()
        self.assertGreater(self.alpha.elo, 1000)

    def test_create_scheduled(self):
        response = self.post(self.base())
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIsNone(body["winner"])
        self.assertIsNone(body["season"])
        self.assertIsNone(body["competition"])

    def test_validation_errors(self):
        cases = [
            (self.base(round=None), 400),
            (self.base(team2_id=str(self.alpha.id)), 400),
            (self.base(team1_id=str(uuid.uuid4())), 404),
            (self.base(event_id=str(uuid.uuid4())), 404),
            (self.base(date="garbage"), 400),
            (self.base(season_id=str(uuid.uuid4())), 404),
            (self.base(competition_id=str(uuid.uuid4())), 404),
            (self.base(winner_id=str(uuid.uuid4())), 400),
        ]
        for data, expected in cases:
            with self.subTest(data=data):
                self.assertEqual(self.post(data).status_code, expected)
        self.assertFalse(Match.objects.exists())

    def test_winner_can_be_team2(self):
        response = self.post(self.base(winner_id=str(self.bravo.id)))
        self.assertEqual(response.json()["winner"]["name"], "Bravo")


@admin_settings
class UpdateMatchTests(MatchFixtures, TestCase):
    def update(self, match, data, method="patch", name="update_match"):
        return getattr(self.client, method)(
            reverse(name, args=[match.id]), data, format="json"
        )

    def test_patch_fields(self):
        match = self.make_match()
        other_season = self.season
        response = self.update(
            match,
            {
                "date": "2025-11-01T12:00:00Z",
                "status": "in_progress",
                "url": "https://u",
                "score_team1": 5,
                "score_team2": 3,
                "platform": "faceit",
                "season_id": str(other_season.id),
                "competition_id": str(self.competition.id),
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        match.refresh_from_db()
        self.assertEqual(match.status, "in_progress")
        self.assertEqual((match.score_team1, match.score_team2), (5, 3))
        self.assertEqual(match.platform, "faceit")
        self.assertEqual(match.season, other_season)
        self.assertEqual(match.competition, self.competition)
        self.assertEqual(match.date.month, 11)

    def test_patch_clears_relations_and_winner(self):
        match = self.make_match(
            season=self.season, competition=self.competition, winner=self.alpha
        )
        response = self.update(
            match, {"season_id": None, "competition_id": "", "winner_id": None}
        )
        self.assertEqual(response.status_code, 200)
        match.refresh_from_db()
        self.assertIsNone(match.season)
        self.assertIsNone(match.competition)
        self.assertIsNone(match.winner)

    def test_patch_null_date_sets_now(self):
        match = self.make_match()
        response = self.update(match, {"date": None})
        self.assertEqual(response.status_code, 200)
        match.refresh_from_db()
        self.assertGreater(match.date.year, 2025)

    def test_put_requires_teams(self):
        match = self.make_match()
        self.assertEqual(self.update(match, {}, method="put").status_code, 400)
        response = self.update(
            match,
            {"team1_id": str(self.bravo.id), "team2_id": str(self.alpha.id)},
            method="put",
        )
        self.assertEqual(response.status_code, 200)
        match.refresh_from_db()
        self.assertEqual((match.team1, match.team2), (self.bravo, self.alpha))

    def test_validation_errors(self):
        match = self.make_match()
        cases = [
            ({"team1_id": str(self.alpha.id), "team2_id": str(self.alpha.id)}, 400),
            ({"team1_id": str(uuid.uuid4())}, 404),
            ({"team2_id": str(uuid.uuid4())}, 404),
            ({"date": "garbage"}, 400),
            ({"season_id": str(uuid.uuid4())}, 404),
            ({"competition_id": str(uuid.uuid4())}, 404),
            ({"winner_id": str(uuid.uuid4())}, 400),
        ]
        for data, expected in cases:
            with self.subTest(data=data):
                self.assertEqual(self.update(match, data).status_code, expected)

    def test_winner_team2(self):
        match = self.make_match()
        response = self.update(match, {"winner_id": str(self.bravo.id)})
        self.assertEqual(response.json()["winner"]["name"], "Bravo")


@admin_settings
class UpdateEventMatchTests(MatchFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.match = self.make_match()
        self.event_match = EventMatch.objects.create(match=self.match, event=self.event)
        self.url = reverse("update_event_match", args=[self.match.id])

    def test_patch_event_match_and_match_fields(self):
        other_event = Event.objects.create(
            name="Other", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        charlie = Team.objects.create(name="Charlie")
        response = self.client.patch(
            self.url,
            {
                "team2_id": str(charlie.id),
                "event_id": str(other_event.id),
                "round": 2,
                "num_in_bracket": 3,
                "is_bye": True,
                "extra_info": {"round_name": "Final"},
                "date": "2025-12-01T00:00:00Z",
                "status": "completed",
                "url": "https://u",
                "score_team1": 2,
                "score_team2": 1,
                "platform": "leaguespot",
                "season_id": str(self.season.id),
                "competition_id": str(self.competition.id),
                "winner_id": str(self.alpha.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["team2"]["name"], "Charlie")
        self.assertEqual(body["event_match"]["event"]["name"], "Other")
        self.assertEqual(body["event_match"]["extra_info"], {"round_name": "Final"})
        self.assertTrue(body["elo"]["applied"])
        self.event_match.refresh_from_db()
        self.assertEqual((self.event_match.round, self.event_match.num_in_bracket), (2, 3))
        self.assertTrue(self.event_match.is_bye)

    def test_patch_clears_values(self):
        self.match.season = self.season
        self.match.competition = self.competition
        self.match.winner = self.alpha
        self.match.save()
        response = self.client.patch(
            self.url,
            {"season_id": None, "competition_id": None, "winner_id": None, "date": None},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIsNone(body["season"])
        self.assertIsNone(body["competition"])
        self.assertIsNone(body["winner"])

    def test_put_requirements(self):
        teams = {"team1_id": str(self.alpha.id), "team2_id": str(self.bravo.id)}
        self.assertEqual(self.client.put(self.url, {}, format="json").status_code, 400)
        self.assertEqual(self.client.put(self.url, teams, format="json").status_code, 400)
        full = {**teams, "event_id": str(self.event.id)}
        self.assertEqual(
            self.client.put(self.url, {**full, "round": None}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.put(self.url, {**full, "num_in_bracket": None}, format="json").status_code,
            400,
        )
        response = self.client.put(
            self.url, {**full, "round": 1, "num_in_bracket": 1}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_validation_errors(self):
        cases = [
            ({"team1_id": str(self.alpha.id), "team2_id": str(self.alpha.id)}, 400),
            ({"team1_id": str(uuid.uuid4())}, 404),
            ({"team2_id": str(uuid.uuid4())}, 404),
            ({"event_id": str(uuid.uuid4())}, 404),
            ({"date": "garbage"}, 400),
            ({"season_id": str(uuid.uuid4())}, 404),
            ({"competition_id": str(uuid.uuid4())}, 404),
            ({"winner_id": str(uuid.uuid4())}, 400),
        ]
        for data, expected in cases:
            with self.subTest(data=data):
                response = self.client.patch(self.url, data, format="json")
                self.assertEqual(response.status_code, expected)

    def test_winner_team2(self):
        response = self.client.patch(
            self.url, {"winner_id": str(self.bravo.id)}, format="json"
        )
        self.assertEqual(response.json()["winner"]["name"], "Bravo")


@admin_settings
class DeleteMatchTests(MatchFixtures, TestCase):
    def test_delete(self):
        match = self.make_match()
        response = self.client.delete(reverse("delete_match", args=[match.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_match"]["team1_name"], "Alpha")
        self.assertIsNone(response.json()["elo_warning"])
        self.assertFalse(Match.objects.exists())

    @override_settings(REQUIRE_MATCH_DELETE_SECURITY=True)
    def test_security_key_when_required(self):
        match = self.make_match()
        url = reverse("delete_match", args=[match.id])
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertEqual(
            self.client.delete(url, {"security_key": "wrong"}, format="json").status_code, 403
        )
        response = self.client.delete(
            url, {"security_key": "confirm-delete-match-456"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Match.objects.exists())
