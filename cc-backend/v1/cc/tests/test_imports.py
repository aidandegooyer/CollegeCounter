"""Import endpoint and helpers, beyond the Elo behaviour in test_elo_tracking."""

import uuid
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from cc.models import Competition, Event, EventMatch, Match, Participant, Player, Team
from cc.views import get_or_create_team, import_match_data, process_player

from .helpers import Fixtures, admin_settings, dev_client, fake_response, past_season

MATCH_UUID = "6f1c2a8e-4b1d-4c7e-9a52-0d3e8b7f1a90"
MATCH_UUID_2 = "7a2d3b9f-5c2e-4d8f-8b63-1e4f9c8a2b01"


def faceit_item(match_id=MATCH_UUID, status="FINISHED", winner="faction1", **extra):
    item = {
        "match_id": f"1-{match_id}",
        "faceit_url": f"https://www.faceit.com/en/cs2/room/1-{match_id}",
        "status": status,
        "scheduled_at": 1759300000,
        "teams": {
            "faction1": {"faction_id": "f-alpha", "name": "Alpha"},
            "faction2": {"faction_id": "f-bravo", "name": "Bravo"},
        },
        "results": {"winner": winner, "score": {"faction1": 1, "faction2": 0}}
        if winner
        else {},
    }
    item.update(extra)
    return item


@admin_settings
class ImportMatchesEndpointTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def post(self, **data):
        payload = {
            "platform": "faceit",
            "competition_name": "Imported",
            "season_id": str(self.season.id),
            "data": {"items": []},
        }
        payload.update(data)
        return self.client.post(reverse("import_matches"), payload, format="json")

    def test_faceit_import(self):
        response = self.post(data={"items": [faceit_item()]})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["matches_imported"], 1)
        self.assertEqual(body["message"], "Import successful: 1 new match(es)")
        match = Match.objects.get()
        self.assertEqual(str(match.id), MATCH_UUID)
        self.assertEqual(match.competition.name, "Imported")
        self.assertEqual(match.platform, "faceit")

        # Re-import is skipped
        body = self.post(data={"items": [faceit_item()]}).json()
        self.assertEqual(body["matches_skipped"], 1)
        self.assertEqual(body["message"], "Import successful: 1 unchanged")

    def test_leaguespot_import(self):
        item = faceit_item(status="READY", winner=None)
        response = self.post(platform="LeagueSpot", data={"items": [item]})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Match.objects.get().platform, "leaguespot")

    def test_regentsleague_import(self):
        data = [
            {
                "id": 5,
                "status": "Scheduled",
                "date": "2025-10-01T18:00:00Z",
                "team1": {"id": 1, "name": "Alpha"},
                "team2": {"id": 2, "name": "Bravo"},
            }
        ]
        response = self.post(platform="regentsleague", data=data)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Match.objects.get().regentsleague_id, 5)

    def test_no_matches(self):
        body = self.post().json()
        self.assertEqual(body["message"], "No matches to import")

    def test_errors(self):
        self.assertEqual(self.post(season_id=str(uuid.uuid4())).status_code, 400)
        self.assertEqual(self.post(event_id=str(uuid.uuid4())).status_code, 400)
        self.assertEqual(self.post(platform="battlefy").status_code, 400)
        self.assertEqual(self.post(data="not a dict").status_code, 500)

    def test_event_import(self):
        event = Event.objects.create(
            name="Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        response = self.post(
            event_id=str(event.id),
            import_type="event",
            data={"items": [faceit_item(round=2, position=3, group=1)]},
        )
        self.assertEqual(response.status_code, 200, response.content)
        event_match = EventMatch.objects.get()
        self.assertEqual(event_match.event, event)
        self.assertEqual((event_match.round, event_match.num_in_bracket), (2, 3))
        self.assertEqual(event_match.extra_info["group"], 1)
        self.assertEqual(event_match.extra_info["round_name"], 2)
        self.assertEqual(event_match.extra_info["faceit_match_id"], MATCH_UUID)

    def test_participant_matches_link_picked_teams_by_platform_id(self):
        # Platform names that wouldn't match Alpha/Bravo by name
        item = faceit_item(
            teams={
                "faction1": {"faction_id": "f:alpha", "name": "Platform Alpha"},
                "faction2": {"faction_id": "f-bravo", "name": "Platform Bravo"},
            }
        )
        response = self.post(
            data={"items": [item]},
            participant_matches={
                "platform:faceit:id:f:alpha": str(self.alpha.id),
                "platform:faceit:id:f-bravo": str(self.bravo.id),
                # Old name-keyed format, another platform, and malformed
                "platform:faceit:team:Platform Alpha": str(self.bravo.id),
                "platform:leaguespot:id:f-bravo": str(self.alpha.id),
                "platform:bad": str(self.bravo.id),
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            sorted(s["key"] for s in response.json()["skipped_participant_matches"]),
            [
                "platform:bad",
                "platform:faceit:team:Platform Alpha",
                "platform:leaguespot:id:f-bravo",
            ],
        )

        match = Match.objects.get()
        self.assertEqual((match.team1, match.team2), (self.alpha, self.bravo))
        competition = Competition.objects.get(name="Imported")
        alpha_participant = Participant.objects.get(team=self.alpha, competition=competition)
        bravo_participant = Participant.objects.get(team=self.bravo, competition=competition)
        # Platform team IDs containing colons are kept whole
        self.assertEqual(alpha_participant.faceit_id, "f:alpha")
        self.assertIsNone(alpha_participant.playfly_id)
        self.assertEqual(bravo_participant.faceit_id, "f-bravo")
        self.assertFalse(Team.objects.filter(name__startswith="Platform").exists())

    def test_participant_matches_existing_participant_and_missing_ids(self):
        participant = Participant.objects.create(competition=self.competition)
        response = self.post(
            participant_matches={
                str(participant.id): str(self.alpha.id),
                str(uuid.uuid4()): str(self.alpha.id),
            }
        )
        self.assertEqual(response.status_code, 200)
        participant.refresh_from_db()
        self.assertEqual(participant.team, self.alpha)


class ImportMatchDataTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.event = Event.objects.create(
            name="Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )

    def import_(self, items, platform="faceit", event=None, import_type="league"):
        return import_match_data(
            {"items": items}, self.competition, self.season, platform, event, import_type
        )

    def test_status_scores_and_dates(self):
        result = self.import_(
            [
                faceit_item(
                    status="ONGOING",
                    winner="faction2",
                    started_at=1759310000,
                    results={"winner": "faction2", "score": {"faction1": 3, "faction2": 7}},
                )
            ]
        )
        self.assertEqual(len(result["imported"]), 1)
        match = Match.objects.get()
        self.assertEqual(match.status, "in_progress")
        self.assertEqual((match.score_team1, match.score_team2), (3, 7))
        self.assertEqual(match.winner, Team.objects.get(name="Bravo"))
        self.assertEqual(int(match.date.timestamp()), 1759310000)
        self.assertFalse(match.elo_applied)

    def test_unknown_status_is_scheduled(self):
        self.import_([faceit_item(status="WEIRD", winner=None)])
        self.assertEqual(Match.objects.get().status, "scheduled")

    def test_match_id_without_prefix(self):
        item = faceit_item(winner=None)
        item["match_id"] = MATCH_UUID
        self.import_([item])
        self.assertEqual(str(Match.objects.get().id), MATCH_UUID)

    def test_skips_matches_without_two_teams(self):
        item = faceit_item()
        item["teams"] = {"faction1": {"name": "Alpha"}}
        result = self.import_([item])
        self.assertEqual(result["imported"], [])

    def test_leaguespot_event_metadata_and_bye(self):
        item = faceit_item(winner=None, status="READY")
        item["teams"]["faction2"] = {"teamId": "pf-bye", "participantId": "pp-bye", "name": "BYE"}
        item["_event_match_metadata"] = {
            "round": 4,
            "num_in_bracket": 2,
            "round_name": "Quarterfinals",
            "round_state": 1,
            "best_of": 3,
        }
        self.import_([item], platform="leaguespot", event=self.event, import_type="event")
        event_match = EventMatch.objects.get()
        self.assertEqual((event_match.round, event_match.num_in_bracket), (4, 2))
        self.assertTrue(event_match.is_bye)
        self.assertEqual(
            event_match.extra_info,
            {
                "leaguespot_match_id": MATCH_UUID,
                "original_status": "READY",
                "round_name": "Quarterfinals",
                "round_state": 1,
                "best_of": 3,
            },
        )
        bye_participant = Participant.objects.get(team__name="BYE")
        self.assertEqual(bye_participant.playfly_id, "pf-bye")
        self.assertEqual(bye_participant.playfly_participant_id, "pp-bye")

    def test_league_import_does_not_create_event_matches(self):
        self.import_([faceit_item()], event=self.event, import_type="league")
        self.assertFalse(EventMatch.objects.exists())

    def test_event_import_position_defaults(self):
        self.import_(
            [faceit_item(winner=None), faceit_item(match_id=MATCH_UUID_2, winner=None)],
            event=self.event,
            import_type="event",
        )
        positions = sorted(EventMatch.objects.values_list("round", "num_in_bracket"))
        self.assertEqual(positions, [(1, 1), (1, 2)])

    def test_existing_match_is_linked_to_event(self):
        self.import_([faceit_item(winner=None)])
        result = self.import_(
            [faceit_item(winner=None, round=2, position=5, group="A")],
            event=self.event,
            import_type="event",
        )
        self.assertEqual(len(result["skipped"]), 1)
        event_match = EventMatch.objects.get()
        self.assertEqual((event_match.round, event_match.num_in_bracket), (2, 5))
        self.assertEqual(event_match.extra_info["group"], "A")

        # A second event import doesn't duplicate the link
        self.import_([faceit_item(winner=None)], event=self.event, import_type="event")
        self.assertEqual(EventMatch.objects.count(), 1)

    def test_existing_leaguespot_match_is_linked_with_metadata(self):
        item = faceit_item(winner=None)
        item["teams"]["faction2"]["name"] = "TBD"
        self.import_([item], platform="leaguespot")
        item["_event_match_metadata"] = {"round": 3}
        self.import_([item], platform="leaguespot", event=self.event, import_type="event")
        event_match = EventMatch.objects.get()
        self.assertEqual((event_match.round, event_match.num_in_bracket), (3, 1))
        self.assertTrue(event_match.is_bye)
        self.assertEqual(event_match.extra_info["round_name"], "")

    def test_roster_players_are_processed(self):
        item = faceit_item(winner=None)
        item["teams"]["faction1"]["roster"] = [
            {"player_id": "p1", "nickname": "one"},
            {"player_id": "p2", "nickname": "two"},
        ]
        self.import_([item])
        alpha = Team.objects.get(name="Alpha")
        self.assertEqual(
            sorted(Player.objects.filter(team=alpha).values_list("name", flat=True)),
            ["one", "two"],
        )


class GetOrCreateTeamTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()

    def test_existing_participant_in_competition_by_each_platform_id(self):
        cases = [
            ("faceit", {"faceit_id": "f1"}, {"faction_id": "f1"}),
            ("leaguespot", {"playfly_id": "pf1"}, {"teamId": "pf1"}),
            ("leaguespot", {"playfly_participant_id": "pp1"}, {"participantId": "pp1"}),
            ("regentsleague", {"regentsleague_id": 11}, {"id": 11}),
        ]
        for platform, participant_ids, team_data in cases:
            with self.subTest(platform=platform, ids=participant_ids):
                Participant.objects.all().delete()
                Participant.objects.create(
                    team=self.alpha, competition=self.competition, season=self.season, **participant_ids
                )
                team, created = get_or_create_team(
                    {"name": "Other Name", **team_data}, self.competition, self.season, platform
                )
                self.assertEqual(team, self.alpha)
                self.assertFalse(created)

    def test_falls_back_to_platform_id_from_earlier_season(self):
        old_season = past_season()
        old_competition = Competition.objects.create(name="Old")
        Participant.objects.create(
            team=self.alpha, competition=old_competition, season=old_season, faceit_id="f1"
        )
        team, created = get_or_create_team(
            {"name": "Renamed", "faction_id": "f1"}, self.competition, self.season, "faceit"
        )
        self.assertEqual(team, self.alpha)
        self.assertTrue(created)
        self.assertTrue(
            Participant.objects.filter(
                team=self.alpha, competition=self.competition, faceit_id="f1"
            ).exists()
        )

    def test_prefers_most_recent_season_for_platform_id(self):
        old_season = past_season()
        Participant.objects.create(team=self.bravo, season=old_season, faceit_id="f1")
        Participant.objects.create(team=self.alpha, season=self.season, faceit_id="f1")
        other_competition = Competition.objects.create(name="New")
        team, _ = get_or_create_team(
            {"name": "x", "faction_id": "f1"}, other_competition, self.season, "faceit"
        )
        self.assertEqual(team, self.alpha)

    def test_matches_by_name_then_creates(self):
        team, _ = get_or_create_team({"name": "Bravo"}, self.competition, self.season, "faceit")
        self.assertEqual(team, self.bravo)

        team, created = get_or_create_team(
            {"name": "Brand New", "picture": "https://img/r.png", "id": 99},
            self.competition,
            self.season,
            "regentsleague",
        )
        self.assertTrue(created)
        self.assertEqual(team.picture, "https://img/r.png")
        self.assertEqual(
            Participant.objects.get(team=team).regentsleague_id, 99
        )

    def test_unknown_team_name_default(self):
        team, _ = get_or_create_team({}, self.competition, self.season, "faceit")
        self.assertEqual(team.name, "Unknown Team")

    def test_existing_participant_missing_ids_is_filled_in(self):
        participant = Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season
        )
        get_or_create_team(
            {"name": "Alpha", "faction_id": "pf", "participantId": "pp"},
            self.competition,
            self.season,
            "leaguespot",
        )
        participant.refresh_from_db()
        self.assertEqual(participant.faceit_id, "pf")
        self.assertEqual(participant.playfly_id, "pf")
        self.assertEqual(participant.playfly_participant_id, "pp")

        get_or_create_team({"name": "Alpha", "id": 5}, self.competition, self.season, "regentsleague")
        participant.refresh_from_db()
        self.assertEqual(participant.regentsleague_id, 5)


@override_settings(FACEIT_API_KEY="faceit-key")
class ProcessPlayerTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()

    def process(self, data, faceit=None):
        with patch("cc.views.imports.requests.get") as get:
            if isinstance(faceit, Exception):
                get.side_effect = faceit
            else:
                get.return_value = faceit or fake_response(status_code=404)
            player = process_player(data, self.alpha, self.season)
        return player, get

    def test_new_player_enriched_from_faceit(self):
        faceit = fake_response(
            json_data={
                "player_id": "fid",
                "nickname": "faceit-name",
                "avatar": "https://img/a.png",
                "games": {"cs2": {"faceit_elo": 2200}},
            }
        )
        player, get = self.process({"game_player_id": "steam1", "nickname": "nick"}, faceit)
        self.assertEqual(get.call_args.kwargs["params"]["game_player_id"], "steam1")
        self.assertEqual(
            (player.name, player.faceit_id, player.steam_id, player.elo, player.picture),
            ("faceit-name", "fid", "steam1", 2200, "https://img/a.png"),
        )
        self.assertEqual(list(player.seasons.all()), [self.season])

    def test_faceit_lookup_failures_fall_back_to_payload(self):
        for faceit in (fake_response(status_code=500), ValueError("network")):
            with self.subTest(faceit=faceit):
                Player.objects.all().delete()
                player, _ = self.process(
                    {"steam_id": "steam1", "player_id": "pid", "nickname": "nick"}, faceit
                )
                self.assertEqual((player.name, player.faceit_id, player.elo), ("nick", "pid", 1000))

    def test_no_faceit_lookup_without_steam_id(self):
        player, get = self.process({"player_id": "pid", "nickname": "nick", "game_player_id": ""})
        get.assert_not_called()
        self.assertIsNone(player.steam_id)

    @override_settings(FACEIT_API_KEY="")
    def test_no_faceit_lookup_without_api_key(self):
        _, get = self.process({"game_player_id": "steam1", "nickname": "nick"})
        get.assert_not_called()

    def test_existing_player_found_by_steam_faceit_or_name_is_moved(self):
        cases = [
            ({"steam_id": "s1"}, {"game_player_id": "s1", "nickname": "x"}),
            ({"faceit_id": "f1"}, {"player_id": "f1", "nickname": "x"}),
            ({}, {"nickname": "SameName"}),
        ]
        for existing_fields, data in cases:
            with self.subTest(existing=existing_fields):
                Player.objects.all().delete()
                existing = Player.objects.create(
                    name="SameName", team=self.bravo, benched=True, **existing_fields
                )
                player, _ = self.process(data)
                self.assertEqual(player.id, existing.id)
                self.assertEqual(player.team, self.alpha)
                self.assertFalse(player.benched)
                # Manually set names aren't overwritten
                self.assertEqual(player.name, "SameName")
                self.assertIn(self.season, player.seasons.all())

    def test_existing_player_gets_missing_ids(self):
        existing = Player.objects.create(name="nick")
        player, _ = self.process({"nickname": "nick", "player_id": "pid"})
        self.assertEqual(player.id, existing.id)
        self.assertEqual(player.faceit_id, "pid")

        existing = Player.objects.create(name="other", faceit_id="f2")
        player, _ = self.process({"player_id": "f2", "steam_id": "s2"})
        self.assertEqual(player.id, existing.id)
        self.assertEqual(player.steam_id, "s2")

    def test_duplicate_names_create_new_player(self):
        Player.objects.create(name="dup")
        Player.objects.create(name="DUP")
        player, _ = self.process({"nickname": "dup"})
        self.assertEqual(Player.objects.filter(name__iexact="dup").count(), 3)
        self.assertEqual(player.team, self.alpha)

    def test_unknown_player_name_is_never_matched_by_name(self):
        Player.objects.create(name="Unknown Player")
        self.process({})
        self.assertEqual(Player.objects.filter(name="Unknown Player").count(), 2)

    def test_create_failure_without_ids_is_raised(self):
        with patch(
            "cc.views.imports.Player.objects.create", side_effect=IntegrityError("dup")
        ):
            with self.assertRaises(IntegrityError):
                self.process({"nickname": "new"})

    def test_create_failure_retries_by_faceit_id(self):
        racer = Player.objects.create(name="racer", faceit_id="f9", team=self.bravo)
        real_get = Player.objects.get
        lookups = []

        def get_after_race(**kwargs):
            # The first faceit_id lookup misses (the other import hadn't saved yet)
            if kwargs == {"faceit_id": "f9"}:
                lookups.append(kwargs)
                if len(lookups) == 1:
                    raise Player.DoesNotExist
            return real_get(**kwargs)

        with patch("cc.views.imports.Player.objects.get", side_effect=get_after_race), patch(
            "cc.views.imports.Player.objects.create", side_effect=IntegrityError("dup")
        ):
            player, _ = self.process({"player_id": "f9", "steam_id": "s9", "nickname": "Unknown Player"})
        self.assertEqual(player.id, racer.id)
        self.assertEqual(player.team, self.alpha)
        self.assertEqual(player.steam_id, "s9")

    def test_create_failure_retry_miss_raises(self):
        with patch(
            "cc.views.imports.Player.objects.create", side_effect=IntegrityError("dup")
        ):
            with self.assertRaises(IntegrityError):
                self.process({"player_id": "nobody", "nickname": "Unknown Player"})


@admin_settings
class MatchParticipantsTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_get_lists_participants_and_teams(self):
        Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season, faceit_id="f"
        )
        Participant.objects.create(playfly_id="pf")
        response = self.client.get(reverse("match_participants"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["teams"]), 2)
        by_team = {p["team_name"]: p for p in body["participants"]}
        self.assertEqual(by_team["Alpha"]["competition_name"], "League")
        self.assertEqual(by_team["Alpha"]["season_name"], "Current Season")
        self.assertIsNone(by_team[None]["competition_id"])
        self.assertEqual(by_team[None]["playfly_id"], "pf")

    def test_post_links_participant_to_team(self):
        participant = Participant.objects.create(competition=self.competition, season=self.season)
        response = self.client.post(
            reverse("match_participants"),
            {"participant_id": str(participant.id), "team_id": str(self.alpha.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["participant"]["competition_name"], "League")
        participant.refresh_from_db()
        self.assertEqual(participant.team, self.alpha)

    def test_post_without_competition_or_season(self):
        participant = Participant.objects.create()
        response = self.client.post(
            reverse("match_participants"),
            {"participant_id": str(participant.id), "team_id": str(self.alpha.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["participant"]["season_id"])

    def test_post_errors(self):
        url = reverse("match_participants")
        participant = Participant.objects.create()
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)
        self.assertEqual(
            self.client.post(
                url, {"participant_id": str(uuid.uuid4()), "team_id": str(self.alpha.id)}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                url, {"participant_id": str(participant.id), "team_id": str(uuid.uuid4())}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                url, {"participant_id": "not-a-uuid", "team_id": str(self.alpha.id)}, format="json"
            ).status_code,
            500,
        )
