"""The public API's OpenAPI schema (cc/public_schema.py) and openapi.yaml."""

import copy
import io
import tempfile
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from jsonschema import Draft202012Validator
from rest_framework.test import APIClient

from cc.models import (
    CustomEvent,
    Event,
    EventMatch,
    Match,
    Participant,
    Player,
)

from .helpers import past_season
from .test_public_views import PublicFixtures

COMMITTED_SCHEMA = Path(settings.BASE_DIR) / "openapi.yaml"
REGENERATE = "python manage.py spectacular --validate --fail-on-warn --file openapi.yaml"


def strict(components):
    """
    The schema's components, but refusing properties they don't list, so a
    view that adds a field without documenting it fails too.
    """
    components = copy.deepcopy(components)
    for schema in components["schemas"].values():
        if "properties" in schema:
            schema["additionalProperties"] = False
    return components


class CommittedSchemaTests(SimpleTestCase):
    def test_openapi_yaml_is_up_to_date(self):
        """openapi.yaml is what the code generates, so API changes show in diffs."""
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / "openapi.yaml"
            # --fail-on-warn: e.g. a view whose schema can't be worked out
            call_command(
                "spectacular",
                "--validate",
                "--fail-on-warn",
                "--file",
                str(generated),
                stderr=io.StringIO(),
            )
            self.assertEqual(
                COMMITTED_SCHEMA.read_text(),
                generated.read_text(),
                f"openapi.yaml is out of date. In cc-backend/v1, run: {REGENERATE}",
            )


class ResponsesMatchSchemaTests(PublicFixtures, TestCase):
    """Every public endpoint's real response fits its documented schema."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        schema = SchemaGenerator().get_schema(request=None, public=True)
        cls.paths = schema["paths"]
        cls.components = strict(schema["components"])

    def setUp(self):
        super().setUp()
        # Fill in the optional parts (captain, winner, event match, custom
        # details, ...) so they're checked too, next to rows without them.
        self.player = Player.objects.create(
            name="Ace", team=self.alpha, steam_id="s1", faceit_id="f1", elo=1500
        )
        Player.objects.create(name="Free Agent", elo=1200)
        self.alpha.captain = self.player
        self.alpha.picture = "https://img.example/alpha.png"
        self.alpha.save()
        Participant.objects.create(
            team=self.alpha,
            season=self.season,
            competition=self.competition,
            faceit_id="faceit-alpha",
        )
        self.ranking_obj = self.ranking(self.season, [(self.alpha, 1300), (self.bravo, 1100)])
        self.ranking(past_season("Older"), [(self.alpha, 1000)])

        self.event = Event.objects.create(
            name="Spring Cup",
            start_date=self.season.start_date,
            end_date=self.season.end_date,
            winner=self.alpha,
            season=self.season,
        )
        CustomEvent.objects.create(
            event=self.event,
            division="honors",
            prize_pool=Decimal("500.00"),
            entry_fee=Decimal("25.00"),
            metadata={"sponsor": "x"},
        )
        Event.objects.create(
            name="Bare Event",
            start_date=self.season.start_date,
            end_date=self.season.end_date,
        )

        played = Match.objects.create(
            team1=self.alpha,
            team2=self.bravo,
            date=self.season.start_date,
            status="completed",
            platform="faceit",
            winner=self.alpha,
            score_team1=13,
            score_team2=7,
            season=self.season,
            competition=self.competition,
            url="https://faceit.example/match",
            elo_applied=True,
            team1_elo_before=1280,
            team2_elo_before=1120,
            team1_elo_change=20,
            team2_elo_change=-20,
        )
        EventMatch.objects.create(match=played, event=self.event, extra_info={"round_name": "Final"})
        Match.objects.create(
            team1=self.bravo, team2=self.charlie, date=self.season.end_date
        )

    def assert_matches_schema(self, name, query="", args=None):
        response = self.get(name, query, args)
        self.assertEqual(response.status_code, 200, response.content)
        path = "/" + reverse(name, args=args).strip("/")
        if args:
            path = path.rsplit("/", 1)[0] + "/{event_id}"
        operation = self.paths[path]["get"]
        schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        validator = Draft202012Validator({**schema, "components": self.components})
        errors = [
            f"{'/'.join(map(str, error.absolute_path))}: {error.message}"
            for error in validator.iter_errors(response.json())
        ]
        self.assertEqual(errors, [], f"{path} doesn't match its schema")
        return response.json()

    def test_version(self):
        self.assert_matches_schema("public_version")
        with override_settings(BUILD_SHA="8f03a25", BUILD_DATE="2026-10-18T12:00:00Z"):
            data = self.assert_matches_schema("public_version")
        self.assertEqual(
            data,
            {
                "api": settings.API_VERSION,
                "build": "8f03a25",
                "built_at": "2026-10-18T12:00:00Z",
            },
        )

    def test_search(self):
        data = self.assert_matches_schema("public_search", "q=a")
        self.assertTrue(data["teams"] and data["players"] and data["events"])
        self.assert_matches_schema("public_search")

    def test_teams(self):
        data = self.assert_matches_schema("public_teams")
        alpha = next(t for t in data["results"] if t["name"] == "Alpha")
        self.assertIsNotNone(alpha["captain"])
        self.assertIsNotNone(alpha["current_ranking"])
        self.assertTrue(alpha["current_competitions"])

    def test_players(self):
        data = self.assert_matches_schema("public_players")
        self.assertEqual({p["team"] is None for p in data["results"]}, {True, False})

    def test_matches(self):
        data = self.assert_matches_schema("public_matches")
        self.assertEqual(
            {m["event_match"] is None for m in data["results"]}, {True, False}
        )

    def test_seasons(self):
        self.assert_matches_schema("public_seasons")

    def test_competitions(self):
        self.assert_matches_schema("public_competitions")

    def test_rankings(self):
        self.assert_matches_schema("public_rankings")

    def test_ranking_items(self):
        self.assert_matches_schema(
            "public_ranking_items", f"ranking_id={self.ranking_obj.id}"
        )

    def test_team_current_ranking(self):
        self.assert_matches_schema(
            "public_team_current_ranking", f"team_id={self.alpha.id}"
        )

    def test_team_ranking_history(self):
        self.assert_matches_schema(
            "public_team_ranking_history", f"team_id={self.alpha.id}"
        )

    def test_team_recent_form(self):
        data = self.assert_matches_schema(
            "public_team_recent_form", f"team_id={self.alpha.id}"
        )
        self.assertTrue(data["recent_form"])

    def test_events(self):
        data = self.assert_matches_schema("public_events")
        self.assertEqual(
            {"custom_details" in e for e in data["results"]}, {True, False}
        )

    def test_event_detail(self):
        data = self.assert_matches_schema("public_event_detail", args=[self.event.id])
        self.assertIn("custom_details", data)

    def test_every_documented_endpoint_has_a_test_here(self):
        documented = {
            operation["operationId"]
            for path in self.paths.values()
            for operation in path.values()
        }
        expected = {
            "get_version", "search", "list_teams", "list_players", "list_matches", "list_seasons",
            "list_competitions", "list_rankings", "list_ranking_items",
            "get_team_current_ranking", "get_team_ranking_history",
            "get_team_recent_form", "list_events", "get_event",
        }
        self.assertEqual(
            documented, expected, "Add a response test above for each new endpoint"
        )


class DocsPageTests(SimpleTestCase):
    def test_schema_and_docs_are_served(self):
        client = APIClient()
        schema = client.get(reverse("public_schema"))
        self.assertEqual(schema.status_code, 200)
        self.assertIn(b"/v1/public/teams", schema.content)
        # The build is added to the served schema's version (not openapi.yaml's)
        self.assertIn(
            f"version: {settings.API_VERSION}+{settings.BUILD_SHA}".encode(),
            schema.content,
        )
        self.assertNotIn(b"/v1/matches/", schema.content)
        docs = client.get(reverse("public_docs"))
        self.assertEqual(docs.status_code, 200)
        self.assertIn(b"swagger-ui", docs.content)
