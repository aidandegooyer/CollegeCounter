"""Public (unauthenticated) API endpoints."""

import unittest
import uuid
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from cc.models import (
    Competition,
    CustomEvent,
    Event,
    EventMatch,
    Match,
    Participant,
    Player,
    Ranking,
    RankingItem,
    Team,
)

from .helpers import current_season, past_season


class PublicFixtures:
    def setUp(self):
        self.client = APIClient()
        self.season = current_season()
        self.old_season = past_season()
        self.competition = Competition.objects.create(name="Spring League")
        self.alpha = Team.objects.create(name="Alpha", school_name="North U", elo=1300)
        self.bravo = Team.objects.create(name="Bravo", school_name="South U", elo=1100)
        self.charlie = Team.objects.create(name="Charlie", school_name="North State", elo=1200)
        self.bye = Team.objects.create(name="BYE")

    def get(self, name, query="", args=None):
        url = reverse(name, args=args)
        return self.client.get(f"{url}?{query}" if query else url)

    def ranking(self, season, items, date=None):
        ranking = Ranking.objects.create(season=season)
        if date:
            Ranking.objects.filter(pk=ranking.pk).update(date=date)
            ranking.refresh_from_db()
        for rank, (team, elo) in enumerate(items, start=1):
            RankingItem.objects.create(ranking=ranking, team=team, rank=rank, elo=elo)
        return ranking


class PublicSearchTests(PublicFixtures, TestCase):
    def test_searches_teams_players_and_events(self):
        Player.objects.create(name="northstar", team=self.bravo, elo=1500)
        Player.objects.create(name="hidden north", elo=1500, visible=False)
        Player.objects.create(name="default north", elo=1000)
        event = Event.objects.create(
            name="Winter Cup",
            start_date="2025-10-01T00:00:00Z",
            end_date="2025-10-02T00:00:00Z",
            season=self.season,
            winner=self.alpha,
        )
        CustomEvent.objects.create(event=event, division="honors", format="North Swiss")

        body = self.get("public_search", "q=north").json()
        self.assertEqual(body["query"], "north")
        self.assertEqual([t["name"] for t in body["teams"]], ["Alpha", "Charlie"])
        # Hidden players and players still on the default 1000 Elo are excluded
        self.assertEqual([p["name"] for p in body["players"]], ["northstar"])
        self.assertEqual(body["players"][0]["team"]["name"], "Bravo")
        self.assertEqual([e["name"] for e in body["events"]], ["Winter Cup"])
        self.assertEqual(body["events"][0]["winner"]["name"], "Alpha")
        self.assertEqual(body["events"][0]["season"]["name"], "Current Season")
        self.assertEqual(body["total_results"], 4)

    def test_player_without_team_and_event_without_relations(self):
        Player.objects.create(name="solo", elo=1500)
        Event.objects.create(
            name="solo event", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        body = self.get("public_search", "q=solo").json()
        self.assertIsNone(body["players"][0]["team"])
        self.assertIsNone(body["events"][0]["season"])
        self.assertIsNone(body["events"][0]["winner"])

    def test_excludes_bye_teams(self):
        body = self.get("public_search", "q=bye").json()
        self.assertEqual(body["teams"], [])

    def test_limit_is_clamped(self):
        for i in range(25):
            Team.objects.create(name=f"Team {i:02d}")
        for query, expected in [("limit=3", 3), ("limit=500", 20), ("limit=0", 1), ("limit=abc", 6)]:
            with self.subTest(query=query):
                body = self.get("public_search", f"q=Team&{query}").json()
                self.assertEqual(len(body["teams"]), expected)
                self.assertEqual(body["limit"], expected)


class PublicTeamsTests(PublicFixtures, TestCase):
    def test_lists_teams_without_byes_sorted_by_name(self):
        body = self.get("public_teams").json()
        self.assertEqual(body["count"], 3)
        self.assertEqual([t["name"] for t in body["results"]], ["Alpha", "Bravo", "Charlie"])

    def test_sorting(self):
        body = self.get("public_teams", "sort=elo&order=desc").json()
        self.assertEqual([t["name"] for t in body["results"]], ["Alpha", "Charlie", "Bravo"])
        body = self.get("public_teams", "sort=password").json()
        self.assertEqual(body["results"][0]["name"], "Alpha")

    def test_filters(self):
        Participant.objects.create(team=self.alpha, season=self.season, competition=self.competition)
        Participant.objects.create(team=self.bravo, season=self.old_season)
        event = Event.objects.create(
            name="Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        match = Match.objects.create(team1=self.bravo, team2=self.charlie, date="2025-10-01T00:00:00Z")
        EventMatch.objects.create(match=match, event=event)

        def names(query):
            return [t["name"] for t in self.get("public_teams", query).json()["results"]]

        self.assertEqual(names(f"id={self.alpha.id},{self.bravo.id}"), ["Alpha", "Bravo"])
        self.assertEqual(names("name=har"), ["Charlie"])
        self.assertEqual(names("school_name=north"), ["Alpha", "Charlie"])
        self.assertEqual(names(f"season_id={self.season.id}"), ["Alpha"])
        self.assertEqual(names(f"competition_id={self.competition.id}"), ["Alpha"])
        self.assertEqual(names(f"event_id={event.id}"), ["Bravo", "Charlie"])

    def test_invalid_uuid_filters(self):
        for param in ("season_id", "competition_id", "event_id"):
            with self.subTest(param=param):
                self.assertEqual(self.get("public_teams", f"{param}=nope").status_code, 400)

    def test_pagination(self):
        body = self.get("public_teams", "page_size=2&page=2").json()
        self.assertEqual(body["total_pages"], 2)
        self.assertEqual([t["name"] for t in body["results"]], ["Charlie"])
        # Out-of-range pages fall back to the last page
        body = self.get("public_teams", "page_size=2&page=99").json()
        self.assertEqual([t["name"] for t in body["results"]], ["Charlie"])
        # page_size is capped
        self.assertEqual(self.get("public_teams", "page_size=1000").json()["page_size"], 100)

    def test_current_competitions_ranking_and_captain(self):
        captain = Player.objects.create(name="cap", team=self.alpha)
        self.alpha.captain = captain
        self.alpha.save()
        Participant.objects.create(team=self.alpha, season=self.season, competition=self.competition)
        Participant.objects.create(team=self.alpha, season=self.season)
        Participant.objects.create(team=self.alpha, season=self.old_season, competition=self.competition)
        self.ranking(self.season, [(self.alpha, 1300)], date=timezone.now() - timedelta(days=7))
        latest = self.ranking(self.season, [(self.bravo, 1100), (self.alpha, 1290)])

        body = self.get("public_teams", f"id={self.alpha.id}").json()
        team = body["results"][0]
        self.assertEqual(team["captain"]["name"], "cap")
        self.assertEqual(team["current_competitions"], [{"id": str(self.competition.id), "name": "Spring League"}])
        self.assertEqual(team["current_ranking"]["rank"], 2)
        self.assertEqual(team["current_ranking"]["elo"], 1290)
        self.assertEqual(team["current_ranking"]["ranking"]["id"], str(latest.id))

    def test_unranked_team_in_current_season(self):
        self.ranking(self.season, [(self.bravo, 1100)])
        team = self.get("public_teams", f"id={self.alpha.id}").json()["results"][0]
        self.assertIsNone(team["current_ranking"])

    def test_no_current_season(self):
        self.season.delete()
        team = self.get("public_teams", f"id={self.alpha.id}").json()["results"][0]
        self.assertEqual(team["current_competitions"], [])
        self.assertIsNone(team["current_ranking"])

    @unittest.expectedFailure
    def test_non_numeric_page_is_not_a_server_error(self):
        # BUG: page/page_size are passed straight to int(), so ?page=abc is a
        # 500 on every paginated public endpoint.
        self.assertEqual(self.get("public_teams", "page=abc").status_code, 200)

    def test_browser_request_gets_json(self):
        # What a browser sends when someone opens the URL
        accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        response = self.client.get(reverse("public_teams"), HTTP_ACCEPT=accept)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")


class PublicPlayersTests(PublicFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.p1 = Player.objects.create(
            name="ace", team=self.alpha, elo=2000, skill_level=10, steam_id="s1", faceit_id="f1"
        )
        self.p2 = Player.objects.create(name="bench", team=self.alpha, elo=1500, benched=True)
        self.p3 = Player.objects.create(name="ghost", elo=1800, visible=False)
        self.p1.seasons.add(self.season)

    def names(self, query=""):
        return [p["name"] for p in self.get("public_players", query).json()["results"]]

    def test_visible_only_by_default(self):
        self.assertEqual(self.names(), ["ace", "bench"])
        self.assertEqual(self.names("visible=false"), ["ghost"])
        self.assertEqual(self.names("visible=true"), ["ace", "bench"])

    def test_filters(self):
        self.assertEqual(self.names(f"id={self.p1.id}"), ["ace"])
        self.assertEqual(self.names("name=ben"), ["bench"])
        self.assertEqual(self.names(f"team_id={self.alpha.id}"), ["ace", "bench"])
        self.assertEqual(self.names("steam_id=s1"), ["ace"])
        self.assertEqual(self.names("faceit_id=f1"), ["ace"])
        self.assertEqual(self.names("benched=true"), ["bench"])
        self.assertEqual(self.names("benched=false"), ["ace"])
        self.assertEqual(self.names(f"season_id={self.season.id}"), ["ace"])

    def test_sorting_and_serialization(self):
        self.assertEqual(self.names("sort=elo&order=desc"), ["ace", "bench"])
        self.assertEqual(self.names("sort=bogus"), ["ace", "bench"])
        body = self.get("public_players", "visible=false").json()
        self.assertIsNone(body["results"][0]["team"])
        body = self.get("public_players", f"id={self.p1.id}").json()
        self.assertEqual(body["results"][0]["team"]["name"], "Alpha")

    def test_invalid_uuid_filters(self):
        for param in ("team_id", "season_id"):
            with self.subTest(param=param):
                self.assertEqual(self.get("public_players", f"{param}=nope").status_code, 400)

    def test_out_of_range_page(self):
        body = self.get("public_players", "page=50").json()
        self.assertEqual(len(body["results"]), 2)


class PublicMatchesTests(PublicFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.event = Event.objects.create(
            name="Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        self.m1 = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T18:00:00Z",
            status="completed", winner=self.alpha, platform="faceit",
            season=self.season, competition=self.competition,
        )
        self.m2 = Match.objects.create(
            team1=self.charlie, team2=self.alpha, date="2025-10-05T18:00:00Z",
            status="scheduled", platform="playfly",
        )
        self.m3 = Match.objects.create(
            team1=self.bravo, team2=self.charlie, date="2025-10-10T18:00:00Z",
            status="cancelled",
        )
        Match.objects.create(team1=self.alpha, team2=self.bye, date="2025-10-02T18:00:00Z")
        EventMatch.objects.create(match=self.m2, event=self.event, round=2, extra_info={"a": 1})

    def ids(self, query=""):
        return [m["id"] for m in self.get("public_matches", query).json()["results"]]

    def test_newest_first_and_excludes_byes(self):
        self.assertEqual(self.ids(), [str(self.m3.id), str(self.m2.id), str(self.m1.id)])
        self.assertEqual(
            self.ids("order=asc"), [str(self.m1.id), str(self.m2.id), str(self.m3.id)]
        )
        self.assertEqual(self.ids("sort=status&order=asc")[0], str(self.m3.id))
        self.assertEqual(self.ids("sort=bogus")[0], str(self.m3.id))

    def test_filters(self):
        self.assertEqual(self.ids(f"id={self.m1.id}"), [str(self.m1.id)])
        self.assertEqual(self.ids(f"team_id={self.alpha.id}"), [str(self.m2.id), str(self.m1.id)])
        self.assertEqual(
            self.ids(f"team_id_1={self.alpha.id}&team_id_2={self.charlie.id}"), [str(self.m2.id)]
        )
        self.assertEqual(self.ids("status=cancelled"), [str(self.m3.id)])
        self.assertEqual(len(self.ids("status=bogus")), 3)
        self.assertEqual(self.ids("platform=playfly"), [str(self.m2.id)])
        self.assertEqual(len(self.ids("platform=other")), 3)
        self.assertEqual(self.ids("date_from=2025-10-04"), [str(self.m3.id), str(self.m2.id)])
        self.assertEqual(self.ids("date_to=2025-10-04"), [str(self.m1.id)])
        self.assertEqual(
            self.ids("date_from=2025-10-05T00:00:00Z&date_to=2025-10-06T00:00:00Z"),
            [str(self.m2.id)],
        )
        self.assertEqual(self.ids(f"season_id={self.season.id}"), [str(self.m1.id)])
        self.assertEqual(self.ids(f"competition_id={self.competition.id}"), [str(self.m1.id)])
        self.assertEqual(self.ids("competition_name=spring league"), [str(self.m1.id)])
        self.assertEqual(self.ids("competition_name=spring"), [])
        self.assertEqual(self.ids(f"event_id={self.event.id}"), [str(self.m2.id)])

    def test_date_to_includes_the_whole_day(self):
        self.assertEqual(self.ids("date_to=2025-10-05"), [str(self.m2.id), str(self.m1.id)])

    def test_unparseable_dates_are_ignored(self):
        self.assertEqual(len(self.ids("date_from=garbage&date_to=garbage")), 3)

    def test_invalid_params(self):
        cases = [
            "team_id=nope",
            f"team_id_1={self.alpha.id}",
            f"team_id_1=nope&team_id_2={self.alpha.id}",
            "season_id=nope",
            "competition_id=nope",
            "event_id=nope",
        ]
        for query in cases:
            with self.subTest(query=query):
                self.assertEqual(self.get("public_matches", query).status_code, 400)

    def test_serialization(self):
        results = {m["id"]: m for m in self.get("public_matches").json()["results"]}
        first = results[str(self.m1.id)]
        self.assertEqual(first["winner"]["name"], "Alpha")
        self.assertEqual(first["team1"]["elo"], 1300)
        self.assertEqual(first["season"]["name"], "Current Season")
        self.assertEqual(first["competition"]["name"], "Spring League")
        self.assertIsNone(first["event_match"])
        second = results[str(self.m2.id)]
        self.assertIsNone(second["winner"])
        self.assertIsNone(second["season"])
        self.assertIsNone(second["competition"])
        self.assertEqual(second["event_match"]["round"], 2)
        self.assertEqual(second["event_match"]["extra_info"], {"a": 1})

    def test_out_of_range_page(self):
        body = self.get("public_matches", "page_size=2&page=9").json()
        self.assertEqual(body["total_pages"], 2)
        self.assertEqual(len(body["results"]), 1)


class PublicCompetitionsTests(PublicFixtures, TestCase):
    def names(self, query=""):
        return [c["name"] for c in self.get("public_competitions", query).json()["results"]]

    def test_dedupes_by_name_and_sorts(self):
        # A re-imported competition shares its name with the original
        Competition.objects.create(name="Spring League")
        Competition.objects.create(name="spring league ")
        Competition.objects.create(name="Autumn Cup")
        self.assertEqual(self.names(), ["Autumn Cup", "Spring League"])

    def test_season_filter(self):
        Competition.objects.create(name="Autumn Cup")
        Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T18:00:00Z",
            season=self.season, competition=self.competition,
        )
        self.assertEqual(self.names(f"season_id={self.season.id}"), ["Spring League"])
        self.assertEqual(self.names(f"season_id={self.old_season.id}"), [])
        self.assertEqual(self.get("public_competitions", "season_id=nope").status_code, 400)


class PublicSeasonsTests(PublicFixtures, TestCase):
    def test_lists_seasons_with_current_flag(self):
        body = self.get("public_seasons").json()
        self.assertEqual(
            [(s["name"], s["is_current"]) for s in body["results"]],
            [("Current Season", True), ("Past Season", False)],
        )

    def test_filters_and_sorting(self):
        body = self.get("public_seasons", "current=true").json()
        self.assertEqual([s["name"] for s in body["results"]], ["Current Season"])
        body = self.get("public_seasons", f"id={self.old_season.id}").json()
        self.assertEqual([s["name"] for s in body["results"]], ["Past Season"])
        body = self.get("public_seasons", "sort=name&order=asc").json()
        self.assertEqual(body["results"][0]["name"], "Current Season")
        body = self.get("public_seasons", "sort=bogus&order=asc").json()
        self.assertEqual(body["results"][0]["name"], "Past Season")

    def test_out_of_range_page(self):
        body = self.get("public_seasons", "page=3").json()
        self.assertEqual(len(body["results"]), 2)


class PublicRankingsTests(PublicFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.old = self.ranking(
            self.season, [(self.alpha, 1250), (self.bravo, 1100)],
            date=timezone.now() - timedelta(days=7),
        )
        self.new = self.ranking(self.season, [(self.bravo, 1150), (self.alpha, 1120)])
        self.other = self.ranking(self.old_season, [(self.charlie, 1000)], date=timezone.now() - timedelta(days=400))
        self.no_season = Ranking.objects.create()

    def test_rankings(self):
        body = self.get("public_rankings", f"season_id={self.season.id}").json()
        self.assertEqual([r["id"] for r in body["results"]], [str(self.new.id), str(self.old.id)])
        self.assertEqual(body["results"][0]["season"]["name"], "Current Season")

        body = self.get("public_rankings", "order=asc&sort=bogus").json()
        self.assertEqual(body["results"][0]["id"], str(self.other.id))
        self.assertIsNone(
            next(r for r in body["results"] if r["id"] == str(self.no_season.id))["season"]
        )
        self.assertEqual(self.get("public_rankings", "season_id=nope").status_code, 400)
        self.assertEqual(len(self.get("public_rankings", "page=9").json()["results"]), 4)

    def test_ranking_items(self):
        body = self.get("public_ranking_items", f"ranking_id={self.new.id}").json()
        self.assertEqual(
            [(i["rank"], i["team"]["name"], i["elo"]) for i in body["results"]],
            [(1, "Bravo", 1150), (2, "Alpha", 1120)],
        )
        body = self.get("public_ranking_items", f"ranking_id={self.new.id}&sort=elo&order=desc").json()
        self.assertEqual(body["results"][0]["team"]["name"], "Bravo")
        body = self.get("public_ranking_items", f"ranking_id={self.new.id}&sort=bogus&page=5").json()
        self.assertEqual(body["results"][0]["rank"], 1)

    def test_ranking_items_validation(self):
        self.assertEqual(self.get("public_ranking_items").status_code, 400)
        self.assertEqual(self.get("public_ranking_items", "ranking_id=nope").status_code, 400)

    def test_team_current_ranking_defaults_to_current_season(self):
        body = self.get("public_team_current_ranking", f"team_id={self.alpha.id}").json()
        self.assertEqual(body["rank"], 2)
        self.assertEqual(body["ranking"]["id"], str(self.new.id))
        self.assertEqual(body["season"]["name"], "Current Season")

    def test_team_current_ranking_for_season(self):
        response = self.get(
            "public_team_current_ranking", f"team_id={self.charlie.id}&season_id={self.old_season.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rank"], 1)

    def test_team_current_ranking_errors(self):
        cases = [
            ("", 400),
            ("team_id=nope", 400),
            (f"team_id={self.alpha.id}&season_id=nope", 400),
            (f"team_id={self.charlie.id}", 404),  # not in the latest ranking
            (f"team_id={self.alpha.id}&season_id={uuid.uuid4()}", 404),  # no ranking
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(self.get("public_team_current_ranking", query).status_code, expected)

    def test_team_current_ranking_without_current_season(self):
        self.season.delete()
        response = self.get("public_team_current_ranking", f"team_id={self.alpha.id}")
        self.assertEqual(response.status_code, 404)

    def test_team_ranking_history(self):
        RankingItem.objects.create(ranking=self.no_season, team=self.alpha, rank=3, elo=999)
        body = self.get("public_team_ranking_history", f"team_id={self.alpha.id}").json()
        self.assertEqual([h["rank"] for h in body["ranking_history"]], [3, 2, 1])
        self.assertIsNone(body["ranking_history"][0]["season"])

        body = self.get(
            "public_team_ranking_history", f"team_id={self.alpha.id}&season_id={self.season.id}"
        ).json()
        self.assertEqual([h["rank"] for h in body["ranking_history"]], [2, 1])
        self.assertEqual(body["ranking_history"][0]["season"]["name"], "Current Season")

    def test_team_ranking_history_validation(self):
        for query in ("", "team_id=nope", f"team_id={self.alpha.id}&season_id=nope"):
            with self.subTest(query=query):
                self.assertEqual(self.get("public_team_ranking_history", query).status_code, 400)


class PublicEventsTests(PublicFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.plain = Event.objects.create(
            name="Plain Open", start_date="2025-09-01T00:00:00Z", end_date="2025-09-02T00:00:00Z",
            season=self.season, winner=self.alpha,
        )
        self.featured = Event.objects.create(
            name="Featured Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z",
        )
        CustomEvent.objects.create(
            event=self.featured, is_featured=True, is_trophycase=True,
            prize_pool="500", entry_fee="10", division="honors",
        )
        self.private = Event.objects.create(
            name="Private Scrim", start_date="2025-11-01T00:00:00Z", end_date="2025-11-02T00:00:00Z",
        )
        CustomEvent.objects.create(event=self.private, is_public=False)

    def names(self, query=""):
        return [e["name"] for e in self.get("public_events", query).json()["results"]]

    def test_public_events_newest_first(self):
        self.assertEqual(self.names(), ["Featured Cup", "Plain Open"])
        self.assertEqual(
            self.names("public_only=false&order=asc"), ["Plain Open", "Featured Cup", "Private Scrim"]
        )
        self.assertEqual(self.names("sort=name&order=bogus"), ["Plain Open", "Featured Cup"])
        self.assertEqual(self.names("sort=bogus&order=asc"), ["Plain Open", "Featured Cup"])

    def test_filters(self):
        self.assertEqual(self.names(f"id={self.plain.id}"), ["Plain Open"])
        self.assertEqual(self.names("name=cup"), ["Featured Cup"])
        self.assertEqual(self.names(f"season_id={self.season.id}"), ["Plain Open"])
        self.assertEqual(self.names(f"winner_id={self.alpha.id}"), ["Plain Open"])
        self.assertEqual(self.names("trophycase=true"), ["Featured Cup"])
        self.assertEqual(self.names("trophycase=false"), ["Plain Open"])
        self.assertEqual(self.names("featured=true"), ["Featured Cup"])
        self.assertEqual(self.names("featured=false&public_only=false"), ["Private Scrim"])

    def test_invalid_ids(self):
        for param in ("id", "season_id", "winner_id"):
            with self.subTest(param=param):
                self.assertEqual(self.get("public_events", f"{param}=nope").status_code, 400)

    def test_serialization(self):
        results = {e["name"]: e for e in self.get("public_events").json()["results"]}
        self.assertEqual(results["Plain Open"]["winner"]["name"], "Alpha")
        self.assertEqual(results["Plain Open"]["season"]["name"], "Current Season")
        self.assertNotIn("custom_details", results["Plain Open"])
        details = results["Featured Cup"]["custom_details"]
        self.assertEqual(details["prize_pool"], "500.00")
        self.assertEqual(details["entry_fee"], "10.00")
        self.assertEqual(details["division"], "honors")
        self.assertIsNone(results["Featured Cup"]["winner"])

    def test_detail(self):
        body = self.get("public_event_detail", args=[self.featured.id]).json()
        self.assertEqual(body["name"], "Featured Cup")
        self.assertTrue(body["custom_details"]["is_featured"])
        self.assertIsNone(body["season"])

        body = self.get("public_event_detail", args=[self.plain.id]).json()
        self.assertEqual(body["winner"]["name"], "Alpha")
        self.assertNotIn("custom_details", body)

    def test_detail_without_prize_values(self):
        CustomEvent.objects.filter(event=self.featured).update(prize_pool=None, entry_fee=None)
        body = self.get("public_event_detail", args=[self.featured.id]).json()
        self.assertIsNone(body["custom_details"]["prize_pool"])
        self.assertIsNone(body["custom_details"]["entry_fee"])

    def test_detail_hides_private_and_missing(self):
        self.assertEqual(self.get("public_event_detail", args=[self.private.id]).status_code, 404)
        self.assertEqual(self.get("public_event_detail", args=[uuid.uuid4()]).status_code, 404)


class PublicTeamRecentFormTests(PublicFixtures, TestCase):
    def test_recent_form(self):
        Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T00:00:00Z", status="completed", winner=self.alpha
        )
        Match.objects.create(
            team1=self.charlie, team2=self.alpha, date="2025-10-02T00:00:00Z", status="completed", winner=self.charlie
        )
        Match.objects.create(
            team1=self.alpha, team2=self.charlie, date="2025-10-03T00:00:00Z", status="completed"
        )
        Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-04T00:00:00Z", status="scheduled"
        )

        body = self.get("public_team_recent_form", f"team_id={self.alpha.id}").json()
        self.assertEqual(
            [(r["result"], r["opponent"]["name"]) for r in body["recent_form"]],
            [("draw", "Charlie"), ("loss", "Charlie"), ("win", "Bravo")],
        )
        body = self.get("public_team_recent_form", f"team_id={self.alpha.id}&limit=1").json()
        self.assertEqual(len(body["recent_form"]), 1)
        body = self.get("public_team_recent_form", f"team_id={self.alpha.id}&limit=50").json()
        self.assertEqual(len(body["recent_form"]), 3)

    def test_validation(self):
        self.assertEqual(self.get("public_team_recent_form").status_code, 400)
        self.assertEqual(self.get("public_team_recent_form", "team_id=nope").status_code, 400)
