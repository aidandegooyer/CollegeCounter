import uuid
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from cc.models import (
    Competition,
    CustomEvent,
    Event,
    Match,
    Participant,
    Player,
    Team,
)

from .helpers import Fixtures, admin_settings, dev_client, fake_response


@admin_settings
class ListTeamsAndPlayersTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_list_teams_includes_captain(self):
        captain = Player.objects.create(name="cap", team=self.alpha, picture="https://p/1")
        self.alpha.captain = captain
        self.alpha.save()

        response = self.client.get(reverse("list_teams"))
        self.assertEqual(response.status_code, 200)
        teams = {team["name"]: team for team in response.json()}
        self.assertEqual(teams["Alpha"]["captain"]["name"], "cap")
        self.assertIsNone(teams["Bravo"]["captain"])
        self.assertEqual(teams["Bravo"]["elo"], 1200)

    def test_list_players(self):
        Player.objects.create(name="a", team=self.alpha, steam_id="s1", benched=True)
        Player.objects.create(name="free agent")
        response = self.client.get(reverse("list_players"))
        self.assertEqual(response.status_code, 200)
        players = {player["name"]: player for player in response.json()}
        self.assertEqual(players["a"]["team"]["name"], "Alpha")
        self.assertTrue(players["a"]["benched"])
        self.assertIsNone(players["free agent"]["team"])


@admin_settings
@override_settings(FACEIT_API_KEY="faceit-key")
class PlayerEloTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_update_player_elo_from_faceit(self):
        found = Player.objects.create(name="found", steam_id="111")
        missing_cs2 = Player.objects.create(name="no cs2", steam_id="222")
        not_found = Player.objects.create(name="404", steam_id="333")
        errored = Player.objects.create(name="err", steam_id="444")
        no_steam = Player.objects.create(name="none", elo=777)

        def fake_get(url, headers, params):
            self.assertEqual(headers["Authorization"], "Bearer faceit-key")
            steam_id = params["game_player_id"]
            if steam_id == "111":
                return fake_response(
                    json_data={"games": {"cs2": {"faceit_elo": 2100, "skill_level": 10}}}
                )
            if steam_id == "222":
                return fake_response(json_data={"games": {}})
            if steam_id == "333":
                return fake_response(status_code=404)
            raise ValueError("network")

        with patch("cc.views.teams.requests.get", side_effect=fake_get):
            response = self.client.post(reverse("update_player_elo"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated_players"], 1)
        self.assertEqual(response.json()["not_found"], 3)
        found.refresh_from_db()
        self.assertEqual((found.elo, found.skill_level), (2100, 10))
        for player in (missing_cs2, not_found, errored):
            player.refresh_from_db()
            self.assertEqual(player.elo, 1000)
        no_steam.refresh_from_db()
        self.assertEqual(no_steam.elo, 777)

    def test_reset_player_elo(self):
        Player.objects.create(name="a", elo=2000, skill_level=9)
        Player.objects.create(name="b", elo=1500, skill_level=5)
        response = self.client.post(
            reverse("reset_player_elo"),
            {"default_elo": 900, "default_skill_level": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated_players"], 2)
        self.assertEqual(
            set(Player.objects.values_list("elo", "skill_level")), {(900, 2)}
        )

    def test_reset_player_elo_defaults(self):
        Player.objects.create(name="a", elo=2000, skill_level=9)
        self.client.post(reverse("reset_player_elo"))
        self.assertEqual(Player.objects.get().elo, 1000)
        self.assertEqual(Player.objects.get().skill_level, 1)


@admin_settings
class MergeTeamsTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def merge(self, primary, secondary, **extra):
        return self.client.post(
            reverse("merge_teams"),
            {"primary_team_id": str(primary), "secondary_team_id": str(secondary), **extra},
            format="json",
        )

    def test_validation(self):
        response = self.client.post(reverse("merge_teams"), {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.merge(self.alpha.id, self.alpha.id).status_code, 400)
        self.assertEqual(self.merge(uuid.uuid4(), self.bravo.id).status_code, 404)
        self.assertEqual(self.merge(self.alpha.id, uuid.uuid4()).status_code, 404)

    def test_merge_moves_players_matches_and_participants(self):
        charlie = Team.objects.create(name="Charlie")
        player = Player.objects.create(name="p", team=self.bravo)
        as_team1 = Match.objects.create(
            team1=self.bravo, team2=charlie, date="2025-10-01T00:00:00Z", winner=self.bravo
        )
        as_team2 = Match.objects.create(
            team1=charlie, team2=self.bravo, date="2025-10-02T00:00:00Z"
        )
        moved = Participant.objects.create(
            team=self.bravo, competition=self.competition, season=self.season, faceit_id="f-b"
        )

        response = self.merge(self.alpha.id, self.bravo.id)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["merged_data"]["players_moved"], 1)
        self.assertEqual(body["merged_data"]["participants_merged"], 1)
        self.assertEqual(body["merged_data"]["matches_updated"], 2)
        self.assertEqual(body["primary_team"]["elo"], 1000)

        self.assertFalse(Team.objects.filter(id=self.bravo.id).exists())
        player.refresh_from_db()
        as_team1.refresh_from_db()
        as_team2.refresh_from_db()
        moved.refresh_from_db()
        self.assertEqual(player.team, self.alpha)
        self.assertEqual((as_team1.team1, as_team1.winner), (self.alpha, self.alpha))
        self.assertEqual(as_team2.team2, self.alpha)
        self.assertEqual(moved.team, self.alpha)

    def test_merge_combines_participants_in_same_competition(self):
        existing = Participant.objects.create(
            team=self.alpha, competition=self.competition, season=self.season, faceit_id="f-a"
        )
        Participant.objects.create(
            team=self.bravo,
            competition=self.competition,
            season=self.season,
            faceit_id="f-b",
            playfly_id="pf",
            playfly_participant_id="pp",
            regentsleague_id=7,
        )
        self.merge(self.alpha.id, self.bravo.id)
        existing.refresh_from_db()
        self.assertEqual(Participant.objects.count(), 1)
        # Existing IDs are kept, missing ones filled in from the secondary
        self.assertEqual(existing.faceit_id, "f-a")
        self.assertEqual(existing.playfly_id, "pf")
        self.assertEqual(existing.playfly_participant_id, "pp")
        self.assertEqual(existing.regentsleague_id, 7)

    def test_merge_clears_platform_ids_that_conflict_elsewhere(self):
        other_competition = Competition.objects.create(name="Other")
        Participant.objects.create(
            team=self.alpha,
            competition=other_competition,
            faceit_id="dup",
            playfly_id="dup-pf",
            playfly_participant_id="dup-pp",
        )
        moved = Participant.objects.create(
            team=self.bravo,
            competition=self.competition,
            faceit_id="dup",
            playfly_id="dup-pf",
            playfly_participant_id="dup-pp",
        )
        self.merge(self.alpha.id, self.bravo.id)
        moved.refresh_from_db()
        self.assertEqual(moved.team, self.alpha)
        self.assertIsNone(moved.faceit_id)
        self.assertIsNone(moved.playfly_id)
        self.assertIsNone(moved.playfly_participant_id)

    def test_merge_conflict_checks_playfly_ids_without_faceit_id(self):
        Participant.objects.create(team=self.alpha, playfly_participant_id="pp")
        moved = Participant.objects.create(
            team=self.bravo, competition=self.competition, playfly_participant_id="pp"
        )
        self.merge(self.alpha.id, self.bravo.id)
        moved.refresh_from_db()
        self.assertIsNone(moved.playfly_participant_id)

    def test_keep_secondary_elo(self):
        response = self.merge(self.alpha.id, self.bravo.id, keep_secondary_elo=True)
        self.assertEqual(response.json()["primary_team"]["elo"], 1200)
        self.alpha.refresh_from_db()
        self.assertEqual(self.alpha.elo, 1200)


@admin_settings
class UpdateTeamAndPlayerTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_update_team(self):
        response = self.client.put(
            reverse("update_team", args=[self.alpha.id]),
            {
                "name": "Alpha 2",
                "school_name": "State",
                "elo": "1300",
                "picture": "https://storage/img.png?alt=media&token=secret",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.alpha.refresh_from_db()
        self.assertEqual(self.alpha.name, "Alpha 2")
        self.assertEqual(self.alpha.school_name, "State")
        self.assertEqual(self.alpha.elo, 1300)
        # Firebase download tokens are stripped
        self.assertEqual(self.alpha.picture, "https://storage/img.png?alt=media")

    def test_update_team_returns_captain(self):
        captain = Player.objects.create(name="cap", team=self.alpha)
        self.alpha.captain = captain
        self.alpha.save()
        response = self.client.put(
            reverse("update_team", args=[self.alpha.id]), {}, format="json"
        )
        self.assertEqual(response.json()["team"]["captain"]["name"], "cap")

    def test_update_team_errors(self):
        missing = self.client.put(
            reverse("update_team", args=[uuid.uuid4()]), {}, format="json"
        )
        self.assertEqual(missing.status_code, 404)
        bad_elo = self.client.put(
            reverse("update_team", args=[self.alpha.id]), {"elo": "abc"}, format="json"
        )
        self.assertEqual(bad_elo.status_code, 500)

    def test_update_player(self):
        player = Player.objects.create(name="p", steam_id="s", faceit_id="f")
        response = self.client.put(
            reverse("update_player", args=[player.id]),
            {
                "name": "renamed",
                "steam_id": "",
                "faceit_id": "",
                "elo": "1500",
                "skill_level": "7",
                "team_id": str(self.alpha.id),
                "benched": 1,
                "visible": 0,
                "picture": "https://storage/p.png?x=1&token=abc",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        player.refresh_from_db()
        self.assertEqual(player.name, "renamed")
        # Blank IDs are stored as NULL so the unique constraint isn't hit
        self.assertIsNone(player.steam_id)
        self.assertIsNone(player.faceit_id)
        self.assertEqual((player.elo, player.skill_level), (1500, 7))
        self.assertEqual(player.team, self.alpha)
        self.assertTrue(player.benched)
        self.assertFalse(player.visible)
        self.assertEqual(player.picture, "https://storage/p.png?x=1")
        self.assertEqual(response.json()["player"]["team"]["name"], "Alpha")

    def test_update_player_clears_team(self):
        player = Player.objects.create(name="p", team=self.alpha)
        response = self.client.put(
            reverse("update_player", args=[player.id]), {"team_id": None}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        player.refresh_from_db()
        self.assertIsNone(player.team)

    def test_update_player_errors(self):
        player = Player.objects.create(name="p")
        url = reverse("update_player", args=[player.id])
        self.assertEqual(
            self.client.put(
                reverse("update_player", args=[uuid.uuid4()]), {}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.put(url, {"team_id": str(uuid.uuid4())}, format="json").status_code,
            400,
        )
        self.assertEqual(
            self.client.put(url, {"skill_level": "x"}, format="json").status_code, 500
        )


@admin_settings
class CreateEventAndCompetitionTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def test_create_event(self):
        response = self.client.post(
            reverse("create_event"),
            {
                "name": "Cup",
                "start_date": "2025-10-01T00:00:00Z",
                "end_date": "2025-10-02T00:00:00Z",
                "description": "desc",
                "picture": "https://img/cup.png",
                "season_id": str(self.season.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["season_id"], str(self.season.id))
        event = Event.objects.get(name="Cup")
        self.assertEqual(event.season, self.season)

    def test_create_event_without_season(self):
        response = self.client.post(
            reverse("create_event"),
            {"name": "Cup", "start_date": "2025-10-01T00:00:00Z", "end_date": "2025-10-02T00:00:00Z"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("season_id", response.json())

    def test_create_event_errors(self):
        url = reverse("create_event")
        self.assertEqual(self.client.post(url, {"name": "x"}, format="json").status_code, 400)
        self.assertEqual(
            self.client.post(
                url,
                {"name": "x", "start_date": "2025-10-01", "end_date": "2025-10-02", "season_id": str(uuid.uuid4())},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                url, {"name": "x", "start_date": "nope", "end_date": "nope"}, format="json"
            ).status_code,
            500,
        )

    def test_create_competition(self):
        url = reverse("create_competition")
        response = self.client.post(url, {"name": "New League"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Competition.objects.filter(name="New League").exists())

        duplicate = self.client.post(url, {"name": "New League"}, format="json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)


@admin_settings
class CustomEventTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def create(self, **data):
        payload = {
            "name": "Invitational",
            "start_date": "2025-10-01T00:00:00Z",
            "end_date": "2025-10-02T00:00:00Z",
        }
        payload.update(data)
        return self.client.post(reverse("custom_events"), payload, format="json")

    def test_create_new_event_with_details(self):
        response = self.create(
            winner_id=str(self.alpha.id),
            prize_pool="1500.50",
            entry_fee=25,
            max_teams="16",
            registration_deadline="2025-09-30T00:00:00Z",
            division="honors",
            is_featured=True,
            metadata={"tier": "S"},
        )
        self.assertEqual(response.status_code, 201, response.content)
        custom = CustomEvent.objects.get(id=response.json()["custom_event_id"])
        self.assertEqual(custom.event.name, "Invitational")
        self.assertEqual(custom.event.winner, self.alpha)
        self.assertEqual(custom.prize_pool, Decimal("1500.50"))
        self.assertEqual(custom.entry_fee, Decimal("25"))
        self.assertEqual(custom.max_teams, 16)
        self.assertEqual(custom.division, "honors")
        self.assertTrue(custom.is_featured)
        self.assertEqual(custom.metadata, {"tier": "S"})

    def test_create_with_unknown_winner(self):
        self.assertEqual(self.create(winner_id=str(uuid.uuid4())).status_code, 400)

    def test_extend_existing_event(self):
        event = Event.objects.create(
            name="Base", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        response = self.create(event_id=str(event.id), winner_id=str(self.bravo.id))
        self.assertEqual(response.status_code, 201, response.content)
        event.refresh_from_db()
        self.assertEqual(event.winner, self.bravo)
        self.assertEqual(response.json()["event_id"], str(event.id))

    def test_extend_existing_event_clearing_winner(self):
        event = Event.objects.create(
            name="Base",
            start_date="2025-10-01T00:00:00Z",
            end_date="2025-10-02T00:00:00Z",
            winner=self.alpha,
        )
        response = self.create(event_id=str(event.id), winner_id="")
        self.assertEqual(response.status_code, 201)
        event.refresh_from_db()
        self.assertIsNone(event.winner)

    def test_extend_errors(self):
        self.assertEqual(self.create(event_id=str(uuid.uuid4())).status_code, 404)
        event = Event.objects.create(
            name="Base", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        self.assertEqual(
            self.create(event_id=str(event.id), winner_id=str(uuid.uuid4())).status_code, 400
        )
        # An event can only be extended once (one-to-one)
        self.assertEqual(self.create(event_id=str(event.id)).status_code, 201)
        self.assertEqual(self.create(event_id=str(event.id)).status_code, 500)

    def test_list_and_detail(self):
        created = self.create(winner_id=str(self.alpha.id), prize_pool="100", entry_fee="5")
        custom_id = created.json()["custom_event_id"]

        listing = self.client.get(reverse("custom_events"))
        self.assertEqual(listing.status_code, 200)
        [item] = listing.json()["custom_events"]
        self.assertEqual(item["event"]["winner"]["name"], "Alpha")
        self.assertEqual(item["prize_pool"], "100.00")
        self.assertEqual(item["entry_fee"], "5.00")

        detail = self.client.get(reverse("custom_event_detail", args=[custom_id]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["event"]["name"], "Invitational")

    def test_list_and_detail_without_optional_values(self):
        custom_id = self.create().json()["custom_event_id"]
        [item] = self.client.get(reverse("custom_events")).json()["custom_events"]
        self.assertIsNone(item["event"]["winner"])
        self.assertIsNone(item["prize_pool"])
        detail = self.client.get(reverse("custom_event_detail", args=[custom_id])).json()
        self.assertIsNone(detail["entry_fee"])
        self.assertIsNone(detail["event"]["winner"])

    def test_update(self):
        custom_id = self.create(prize_pool="100").json()["custom_event_id"]
        url = reverse("custom_event_detail", args=[custom_id])
        response = self.client.put(
            url,
            {
                "name": "Renamed",
                "start_date": "2025-11-01T00:00:00Z",
                "end_date": "2025-11-02T00:00:00Z",
                "description": "new",
                "picture": "https://img/new.png",
                "winner_id": str(self.bravo.id),
                "bracket_link": "https://b",
                "stream_link": "https://s",
                "secondary_stream_link": "https://s2",
                "discord_link": "https://d",
                "registration_link": "https://r",
                "rules_document": "https://rules",
                "prize_pool": "",
                "prize_currency": "EUR",
                "max_teams": "8",
                "entry_fee": "10",
                "format": "Swiss",
                "game_mode": "5v5",
                "division": "open",
                "is_featured": True,
                "is_trophycase": True,
                "is_public": False,
                "registration_open": True,
                "registration_deadline": "2025-10-30T00:00:00Z",
                "twitter_hashtag": "cup",
                "metadata": {"a": 1},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        custom = CustomEvent.objects.select_related("event").get(id=custom_id)
        self.assertEqual(custom.event.name, "Renamed")
        self.assertEqual(custom.event.winner, self.bravo)
        self.assertIsNone(custom.prize_pool)
        self.assertEqual(custom.entry_fee, Decimal("10"))
        self.assertEqual(custom.max_teams, 8)
        self.assertEqual(custom.prize_currency, "EUR")
        self.assertEqual(custom.division, "open")
        self.assertTrue(custom.is_trophycase)
        self.assertFalse(custom.is_public)
        self.assertEqual(custom.metadata, {"a": 1})

    def test_update_clears_values(self):
        custom_id = self.create(
            winner_id=str(self.alpha.id), max_teams=4, entry_fee=5
        ).json()["custom_event_id"]
        url = reverse("custom_event_detail", args=[custom_id])
        response = self.client.put(
            url, {"winner_id": None, "max_teams": None, "entry_fee": None}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        custom = CustomEvent.objects.select_related("event").get(id=custom_id)
        self.assertIsNone(custom.event.winner)
        self.assertIsNone(custom.max_teams)
        self.assertIsNone(custom.entry_fee)

    def test_update_with_unknown_winner(self):
        custom_id = self.create().json()["custom_event_id"]
        response = self.client.put(
            reverse("custom_event_detail", args=[custom_id]),
            {"winner_id": str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_with_invalid_number_is_500(self):
        custom_id = self.create().json()["custom_event_id"]
        response = self.client.put(
            reverse("custom_event_detail", args=[custom_id]),
            {"max_teams": "many"},
            format="json",
        )
        self.assertEqual(response.status_code, 500)

    def test_delete_removes_base_event(self):
        response = self.create()
        custom_id = response.json()["custom_event_id"]
        event_id = response.json()["event_id"]
        deleted = self.client.delete(reverse("custom_event_detail", args=[custom_id]))
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(CustomEvent.objects.exists())
        self.assertFalse(Event.objects.filter(id=event_id).exists())

    def test_missing_custom_event(self):
        response = self.client.get(reverse("custom_event_detail", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)

    def test_list_error_is_500(self):
        with patch("cc.admin_views.CustomEvent.objects.select_related", side_effect=RuntimeError):
            response = self.client.get(reverse("custom_events"))
        self.assertEqual(response.status_code, 500)


@admin_settings
@override_settings(FACEIT_API_KEY="faceit-key")
class ImportTeamFromFaceitTests(Fixtures, TestCase):
    TEAM_ID = "0f1e2d3c-aaaa-bbbb-cccc-1234567890ab"

    def setUp(self):
        self.make_base()
        self.client = dev_client()

    def post(self, data, responses):
        def fake_get(url, headers):
            self.assertEqual(headers["Authorization"], "Bearer faceit-key")
            result = responses[url]
            if isinstance(result, Exception):
                raise result
            return result

        with patch("cc.admin_views.requests.get", side_effect=fake_get):
            return self.client.post(reverse("import_team_from_faceit"), data, format="json")

    def team_url(self):
        return f"https://open.faceit.com/data/v4/teams/{self.TEAM_ID}"

    def player_url(self, player_id):
        return f"https://open.faceit.com/data/v4/players/{player_id}"

    def test_imports_team_and_roster_from_url(self):
        existing_free_agent = Player.objects.create(name="old", faceit_id="u-free")
        existing_rostered = Player.objects.create(name="kept", faceit_id="u-kept", team=self.bravo)
        responses = {
            self.team_url(): fake_response(
                json_data={
                    "nickname": "Charlie",
                    "avatar": "https://img/c.png",
                    "members": [
                        {"user_id": "u-new"},
                        {"user_id": "u-free"},
                        {"user_id": "u-kept"},
                        {"user_id": "u-404"},
                        {"user_id": "u-error"},
                        {},
                    ],
                }
            ),
            self.player_url("u-new"): fake_response(
                json_data={
                    "nickname": "newbie",
                    "avatar": "https://img/n.png",
                    "games": {
                        "cs2": {"game_player_id": "steam-1", "faceit_elo": 1800, "skill_level": 8}
                    },
                }
            ),
            self.player_url("u-404"): fake_response(status_code=404),
            self.player_url("u-error"): ValueError("network"),
        }
        response = self.post(
            {"team_url": f"https://www.faceit.com/en/teams/{self.TEAM_ID}"}, responses
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["faceit_team_id"], self.TEAM_ID)

        team = Team.objects.get(name="Charlie")
        self.assertEqual(team.picture, "https://img/c.png")
        new_player = Player.objects.get(faceit_id="u-new")
        self.assertEqual(
            (new_player.name, new_player.steam_id, new_player.elo, new_player.skill_level, new_player.team),
            ("newbie", "steam-1", 1800, 8, team),
        )
        existing_free_agent.refresh_from_db()
        existing_rostered.refresh_from_db()
        self.assertEqual(existing_free_agent.team, team)
        # Players already on a team aren't moved
        self.assertEqual(existing_rostered.team, self.bravo)
        self.assertEqual(
            sorted((p["name"], p["existed"]) for p in body["players"]),
            [("newbie", False), ("old", True)],
        )

    def test_existing_team_by_name_or_participant(self):
        responses = {self.team_url(): fake_response(json_data={"name": "Alpha"})}
        response = self.post({"team_id": self.TEAM_ID}, responses)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["team_id"], str(self.alpha.id))

        Participant.objects.create(team=self.bravo, faceit_id=self.TEAM_ID)
        responses = {self.team_url(): fake_response(json_data={"nickname": "Renamed"})}
        response = self.post({"team_id": self.TEAM_ID}, responses)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["team_id"], str(self.bravo.id))

    def test_validation_errors(self):
        self.assertEqual(self.post({}, {}).status_code, 400)
        self.assertEqual(
            self.post({"team_url": "https://www.faceit.com/en/players/x"}, {}).status_code, 400
        )
        responses = {self.team_url(): fake_response(status_code=404)}
        self.assertEqual(self.post({"team_id": self.TEAM_ID}, responses).status_code, 400)

    @override_settings(FACEIT_API_KEY="")
    def test_missing_api_key(self):
        self.assertEqual(self.post({"team_id": self.TEAM_ID}, {}).status_code, 500)

    def test_team_fetch_exception_is_500(self):
        responses = {self.team_url(): ValueError("down")}
        self.assertEqual(self.post({"team_id": self.TEAM_ID}, responses).status_code, 500)
