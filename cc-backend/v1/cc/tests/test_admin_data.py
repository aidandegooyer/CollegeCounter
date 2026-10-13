import unittest
import uuid

from django.test import TestCase
from django.urls import reverse

from cc.models import (
    Competition,
    Event,
    EventMatch,
    Match,
    Participant,
    Player,
    Ranking,
    RankingItem,
    Season,
    Team,
)

from .helpers import Fixtures, admin_settings, dev_client, past_season, token_client


@admin_settings
class SeasonEndpointTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_list_seasons(self):
        past_season()
        response = self.client.get(reverse("list_seasons"))
        self.assertEqual(response.status_code, 200)
        names = sorted(season["name"] for season in response.json())
        self.assertEqual(names, ["Current Season", "Past Season"])

    def test_list_seasons_requires_auth(self):
        response = self.client_class().get(reverse("list_seasons"))
        self.assertEqual(response.status_code, 401)

    def test_create_season(self):
        response = self.client.post(
            reverse("create_season"),
            {
                "name": "2026-27",
                "start_date": "2026-08-01T00:00:00Z",
                "end_date": "2027-05-01T00:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        season = Season.objects.get(name="2026-27")
        self.assertEqual(season.start_date.year, 2026)

    def test_create_season_missing_fields(self):
        response = self.client.post(
            reverse("create_season"), {"name": "x"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_create_season_requires_owner(self):
        client, patcher = token_client({"role": "admin"})
        self.addCleanup(patcher.stop)
        response = client.post(
            reverse("create_season"),
            {"name": "x", "start_date": "2026-01-01", "end_date": "2026-02-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


@admin_settings
class ClearDatabaseTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()
        Player.objects.create(name="p", team=self.alpha)
        match = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T00:00:00Z"
        )
        event = Event.objects.create(
            name="Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        EventMatch.objects.create(match=match, event=event)
        ranking = Ranking.objects.create(season=self.season)
        RankingItem.objects.create(ranking=ranking, team=self.alpha, rank=1)
        Participant.objects.create(team=self.alpha, competition=self.competition)

    def test_wrong_key_is_rejected(self):
        response = self.client.post(
            reverse("clear_database"), {"security_key": "nope"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Team.objects.exists())

    def test_clears_data_but_keeps_seasons_and_competitions(self):
        response = self.client.post(
            reverse("clear_database"),
            {"security_key": "confirm-database-clear-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        for model in (Team, Player, Match, Event, EventMatch, Ranking, RankingItem, Participant):
            self.assertFalse(model.objects.exists(), model.__name__)
        self.assertTrue(Season.objects.exists())
        self.assertTrue(Competition.objects.exists())


@admin_settings
class CompetitionEndpointTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def delete(self, competition_id, key="confirm-delete-competition-789"):
        return self.client.delete(
            reverse("delete_competition", args=[competition_id]),
            {"security_key": key},
            format="json",
        )

    def test_list_competitions_counts_and_seasons(self):
        other_season = past_season()
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season
        )
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season
        )
        Participant.objects.create(competition=self.competition, season=self.season)
        Match.objects.create(
            team1=self.alpha,
            team2=self.bravo,
            date="2025-10-01T00:00:00Z",
            competition=self.competition,
            season=other_season,
        )
        Competition.objects.create(name="Empty")

        response = self.client.get(reverse("list_competitions"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_competitions"], 2)
        league = next(c for c in body["competitions"] if c["name"] == "League")
        self.assertEqual(league["participants_count"], 3)
        self.assertEqual(league["matches_count"], 1)
        self.assertEqual(league["teams_count"], 1)
        self.assertEqual(
            [s["name"] for s in league["seasons"]], ["Current Season", "Past Season"]
        )
        empty = next(c for c in body["competitions"] if c["name"] == "Empty")
        self.assertEqual(empty["seasons"], [])
        self.assertIsNone(league["source"])

    def test_list_competitions_import_source(self):
        Competition.objects.filter(pk=self.competition.pk).update(
            source_platform="leaguespot", source_id="s1", source_id_type="stage",
            import_type="league",
        )
        body = self.client.get(reverse("list_competitions")).json()
        self.assertEqual(
            body["competitions"][0]["source"],
            {
                "platform": "leaguespot", "id": "s1", "id_type": "stage",
                "import_type": "league", "event_id": None,
            },
        )

    def test_list_competitions_import_source_event(self):
        event = Event.objects.create(
            name="Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        Competition.objects.filter(pk=self.competition.pk).update(
            source_platform="faceit", source_id="c1", import_type="event", source_event=event,
        )
        body = self.client.get(reverse("list_competitions")).json()
        self.assertEqual(body["competitions"][0]["source"]["event_id"], str(event.id))

    def test_delete_requires_key(self):
        response = self.delete(self.competition.id, key="wrong")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Competition.objects.filter(id=self.competition.id).exists())

    def test_delete_missing_competition(self):
        self.assertEqual(self.delete(uuid.uuid4()).status_code, 404)

    def test_delete_removes_matches_participants_and_competition(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season
        )
        Match.objects.create(
            team1=self.alpha,
            team2=self.bravo,
            date="2025-10-01T00:00:00Z",
            competition=self.competition,
        )
        other = Competition.objects.create(name="Other")
        kept_match = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T00:00:00Z", competition=other
        )

        response = self.delete(self.competition.id)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["deleted_data"]["matches"], 1)
        self.assertEqual(body["deleted_data"]["participants"], 1)
        self.assertFalse(Competition.objects.filter(id=self.competition.id).exists())
        self.assertTrue(Match.objects.filter(id=kept_match.id).exists())
        # Teams are not deleted
        self.assertTrue(Team.objects.filter(id=self.alpha.id).exists())

    @unittest.expectedFailure
    def test_delete_keeps_unrelated_events_in_same_season(self):
        # BUG: delete_competition deletes every Event (and EventMatch) in any
        # season the competition has participants in, even events that have
        # nothing to do with the competition.
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season
        )
        unrelated = Event.objects.create(
            name="Unrelated Cup",
            start_date="2025-10-01T00:00:00Z",
            end_date="2025-10-02T00:00:00Z",
            season=self.season,
        )
        self.delete(self.competition.id)
        self.assertTrue(Event.objects.filter(id=unrelated.id).exists())
