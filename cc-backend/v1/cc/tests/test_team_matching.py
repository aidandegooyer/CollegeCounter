import uuid

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from cc.models import Competition, Match, Participant, Player, Season, Team
from cc.views import get_or_create_team


def faceit_team(faction_id, name, player_ids=()):
    return {
        "faction_id": faction_id,
        "name": name,
        "roster": [{"player_id": pid, "nickname": pid} for pid in player_ids],
    }


def faceit_match(team1, team2, winner="faction1"):
    return {
        "match_id": f"1-{uuid.uuid4()}",
        "status": "FINISHED",
        "finished_at": 1759341600,
        "teams": {"faction1": team1, "faction2": team2},
        "results": {"winner": winner, "score": {"faction1": 1, "faction2": 0}},
    }


@override_settings(DEBUG=True)
class TeamMatchingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer dev")
        self.season = Season.objects.create(
            name="Fall 2026", start_date="2026-09-01", end_date="2026-12-15"
        )
        old_competition = Competition.objects.create(name="Longhorn round 1")

        # Linked to the platform by an earlier import, under a different name
        self.ashland = Team.objects.create(name="Ashland Eagles", elo=2000)
        Participant.objects.create(
            team=self.ashland,
            competition=old_competition,
            season=self.season,
            faceit_id="f-ashland",
        )
        # Never imported from the platform; known by name only
        self.bravo = Team.objects.create(name="Bravo", elo=1200)
        # Has players from an incoming team's roster
        self.roster_team = Team.objects.create(name="Wildcats Esports", elo=1500)
        for pid in ("p1", "p2", "p3"):
            Player.objects.create(name=pid, faceit_id=pid, team=self.roster_team)
        # Only a similar name to an incoming team
        self.similar = Team.objects.create(name="Kentucky Wildcats", elo=1100)

    def import_(self, items, participant_matches=None, platform="faceit", name="Longhorn round 2"):
        return self.client.post(
            reverse("import_matches"),
            {
                "platform": platform,
                "competition_name": name,
                "season_id": str(self.season.id),
                "data": {"items": items},
                "participant_matches": participant_matches or {},
            },
            format="json",
        )

    def counts(self):
        return (
            Team.objects.count(),
            Participant.objects.count(),
            Competition.objects.count(),
            Match.objects.count(),
        )

    def resolve(self, items, platform="faceit"):
        response = self.client.post(
            reverse("resolve_import_teams"),
            {"platform": platform, "season_id": str(self.season.id), "data": {"items": items}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return {t["key"]: t for t in response.json()["teams"]}

    def test_resolve_reports_matches_and_misses(self):
        teams = self.resolve(
            [
                faceit_match(
                    faceit_team("f-ashland", "Ashland Prem"),
                    faceit_team("f-bravo", "Bravo"),
                ),
                faceit_match(
                    faceit_team("f-uk", "UK Wildcats", ["p1", "p2", "p3", "p9"]),
                    faceit_team("f-bye", "BYE"),
                ),
                # Same team again, in another round
                faceit_match(
                    faceit_team("f-ashland", "Ashland Prem"),
                    faceit_team("f-uk", "UK Wildcats"),
                ),
            ]
        )

        self.assertEqual(set(teams), {"f-ashland", "f-bravo", "f-uk"})
        self.assertEqual(teams["f-ashland"]["match"]["team"]["id"], str(self.ashland.id))
        self.assertEqual(teams["f-ashland"]["match"]["method"], "platform_id")
        self.assertEqual(teams["f-bravo"]["match"]["method"], "name")

        miss = teams["f-uk"]
        self.assertIsNone(miss["match"])
        self.assertEqual(miss["roster_size"], 4)
        # Roster overlap outranks the similar name
        self.assertEqual(
            [(s["team"]["id"], s["roster_overlap"]) for s in miss["suggestions"][:2]],
            [(str(self.roster_team.id), 3), (str(self.similar.id), 0)],
        )

    def test_resolve_writes_nothing(self):
        counts = (Team.objects.count(), Participant.objects.count(), Competition.objects.count())
        self.resolve([faceit_match(faceit_team("f-new", "New"), faceit_team("f-new2", "New 2"))])
        self.assertEqual(
            (Team.objects.count(), Participant.objects.count(), Competition.objects.count()),
            counts,
        )

    def test_resolve_flags_ambiguous_names(self):
        Team.objects.create(name="Bravo")
        teams = self.resolve(
            [faceit_match(faceit_team("f-bravo", "Bravo"), faceit_team("f-x", "X"))]
        )
        self.assertIsNone(teams["f-bravo"]["match"])
        self.assertTrue(teams["f-bravo"]["ambiguous"])

    def test_import_applies_chosen_match_by_platform_id(self):
        teams_before = Team.objects.count()
        response = self.client.post(
            reverse("import_matches"),
            {
                "platform": "faceit",
                "competition_name": "Longhorn round 2",
                "season_id": str(self.season.id),
                "data": {
                    "items": [
                        faceit_match(
                            faceit_team("f-uk", "UK Wildcats"),
                            faceit_team("f-ashland", "Ashland Prem"),
                        )
                    ]
                },
                "participant_matches": {
                    "platform:faceit:id:f-uk": str(self.roster_team.id),
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        self.assertEqual(Team.objects.count(), teams_before)
        match = Match.objects.get()
        self.assertEqual(
            (match.team1_id, match.team2_id), (self.roster_team.id, self.ashland.id)
        )
        # The chosen link is stored by platform ID, so later rounds find it too
        self.assertTrue(
            Participant.objects.filter(team=self.roster_team, faceit_id="f-uk").exists()
        )

    def test_regentsleague_match_key_is_stored_as_int(self):
        response = self.client.post(
            reverse("import_matches"),
            {
                "platform": "regentsleague",
                "competition_name": "Regents",
                "season_id": str(self.season.id),
                "data": [
                    {
                        "id": 7,
                        "status": "Scheduled",
                        "date": "2026-10-01T18:00:00Z",
                        "team1": {"id": 11, "name": "Some Other Name"},
                        "team2": {"id": 12, "name": "Bravo"},
                    }
                ],
                "participant_matches": {
                    "platform:regentsleague:id:11": str(self.ashland.id),
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Match.objects.get().team1_id, self.ashland.id)

    def test_resolve_rejects_bad_season_and_data(self):
        url = reverse("resolve_import_teams")
        bad_season = self.client.post(
            url, {"platform": "faceit", "season_id": "not-a-uuid", "data": {}}, format="json"
        )
        self.assertEqual(bad_season.status_code, 400)
        bad_data = self.client.post(
            url,
            {"platform": "regentsleague", "season_id": str(self.season.id), "data": {}},
            format="json",
        )
        self.assertEqual(bad_data.status_code, 400)

    def test_hand_matched_team_gets_its_roster(self):
        mover = Player.objects.create(name="mover", faceit_id="p-mover", team=self.similar)
        response = self.import_(
            [
                faceit_match(
                    faceit_team("f-uk", "UK Wildcats", ["p-mover", "p-new"]),
                    faceit_team("f-ashland", "Ashland Prem"),
                )
            ],
            {"platform:faceit:id:f-uk": str(self.roster_team.id)},
        )
        self.assertEqual(response.status_code, 200, response.content)

        mover.refresh_from_db()
        self.assertEqual(mover.team_id, self.roster_team.id)
        self.assertEqual(Player.objects.get(faceit_id="p-new").team_id, self.roster_team.id)

    def test_next_round_links_hand_matched_team_without_a_pick(self):
        self.import_(
            [faceit_match(faceit_team("f-uk", "UK Wildcats"), faceit_team("f-ashland", "A"))],
            {"platform:faceit:id:f-uk": str(self.roster_team.id)},
        )
        teams_before = Team.objects.count()

        response = self.import_(
            [faceit_match(faceit_team("f-uk", "UK Wildcats"), faceit_team("f-bravo", "Bravo"))],
            name="Longhorn round 3",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Team.objects.count(), teams_before)
        round3 = Match.objects.get(competition__name="Longhorn round 3")
        self.assertEqual(round3.team1_id, self.roster_team.id)

    def test_ambiguous_name_fails_without_writing_anything(self):
        Team.objects.create(name="Bravo")
        counts = self.counts()
        response = self.import_(
            [
                faceit_match(faceit_team("f-ashland", "Ashland Prem"), faceit_team("f-new", "New")),
                faceit_match(faceit_team("f-ashland", "Ashland Prem"), faceit_team("f-bravo", "Bravo")),
            ]
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("Several teams are named 'Bravo'", response.json()["error"])
        self.assertEqual(self.counts(), counts)

    def test_ambiguous_name_imports_once_picked(self):
        Team.objects.create(name="Bravo")
        response = self.import_(
            [faceit_match(faceit_team("f-ashland", "A"), faceit_team("f-bravo", "Bravo"))],
            {"platform:faceit:id:f-bravo": str(self.bravo.id)},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Match.objects.get().team2_id, self.bravo.id)

    def test_unusable_picks_are_reported_not_applied(self):
        response = self.import_(
            [
                faceit_match(faceit_team("f-uk", "UK Wildcats"), faceit_team("f-y", "Yankton")),
                faceit_match(faceit_team("f-z", "Zion"), faceit_team("f-bravo", "Bravo")),
            ],
            {
                "platform:faceit:id:f-uk": str(self.roster_team.id),
                "platform:leaguespot:id:f-uk": str(self.bravo.id),
                "platform:faceit:team:Old Format": str(self.bravo.id),
                "platform:faceit:id:name:Zion": str(self.bravo.id),
                "platform:faceit:id:f-elsewhere": str(self.bravo.id),
                "platform:faceit:id:f-y": "not-a-uuid",
                "platform:faceit:id:f-z": str(uuid.uuid4()),
            },
        )
        self.assertEqual(response.status_code, 200, response.content)

        skipped = {
            s["key"]: (s["name"], s["reason"])
            for s in response.json()["skipped_participant_matches"]
        }
        self.assertEqual(
            skipped,
            {
                "platform:leaguespot:id:f-uk": (None, "Invalid key"),
                "platform:faceit:team:Old Format": (None, "Invalid key"),
                "platform:faceit:id:name:Zion": (None, "Invalid key"),
                "platform:faceit:id:f-elsewhere": (None, "Team not in this import"),
                "platform:faceit:id:f-y": ("Yankton", "Picked team not found"),
                "platform:faceit:id:f-z": ("Zion", "Picked team not found"),
            },
        )
        # The valid pick still applied; the others imported as if unpicked
        self.assertEqual(
            Match.objects.get(team2=self.bravo).team1.name, "Zion"
        )
        self.assertTrue(Match.objects.filter(team1=self.roster_team).exists())
        self.assertFalse(Participant.objects.filter(faceit_id__startswith="name:").exists())

    def test_confirmed_merge_imports_both_teams_as_one(self):
        response = self.import_(
            [
                faceit_match(faceit_team("f-uk", "UK Wildcats"), faceit_team("f-bravo", "Bravo")),
                faceit_match(faceit_team("f-uk-b", "UK Wildcats B"), faceit_team("f-ashland", "A")),
            ],
            {
                "platform:faceit:id:f-uk": str(self.roster_team.id),
                "platform:faceit:id:f-uk-b": str(self.roster_team.id),
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["skipped_participant_matches"], [])
        self.assertEqual(Match.objects.filter(team1=self.roster_team).count(), 2)
        # One participant per team per competition, as platform sync expects
        self.assertEqual(
            Participant.objects.filter(
                team=self.roster_team, competition__name="Longhorn round 2"
            ).count(),
            1,
        )

    def test_leaguespot_pick_stores_playfly_id(self):
        response = self.import_(
            [faceit_match(faceit_team("ls-uk", "UK Wildcats"), faceit_team("ls-b", "Bravo"))],
            {"platform:leaguespot:id:ls-uk": str(self.roster_team.id)},
            platform="leaguespot",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Match.objects.get().team1_id, self.roster_team.id)
        self.assertTrue(
            Participant.objects.filter(
                team=self.roster_team, faceit_id="ls-uk", playfly_id="ls-uk"
            ).exists()
        )

    def test_competition_participant_takes_precedence(self):
        competition = Competition.objects.create(name="Round 2")
        # Linked to Bravo in this competition, though the platform ID points at Ashland
        Participant.objects.create(
            team=self.bravo, competition=competition, season=self.season, faceit_id="f-ashland"
        )
        team, _ = get_or_create_team(
            faceit_team("f-ashland", "Ashland Eagles"), competition, self.season, "faceit"
        )
        self.assertEqual(team, self.bravo)

    def test_lookup_ignores_participants_without_a_faceit_id(self):
        competition = Competition.objects.create(name="Round 2")
        Participant.objects.create(team=self.bravo, competition=competition, season=self.season)
        team, _ = get_or_create_team(
            faceit_team("f-ashland", "Ashland Prem"), competition, self.season, "faceit"
        )
        self.assertEqual(team, self.ashland)
