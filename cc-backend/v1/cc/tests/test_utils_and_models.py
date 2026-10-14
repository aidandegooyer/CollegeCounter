import unittest
from datetime import datetime, timezone as dt_timezone

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

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
    Season,
    Team,
)
from cc.views import calculate_new_elo, safe_parse_datetime


class SafeParseDatetimeTests(SimpleTestCase):
    def test_iso_with_z_is_utc(self):
        parsed = safe_parse_datetime("2025-10-25T00:30:00Z")
        self.assertEqual(parsed, datetime(2025, 10, 25, 0, 30, tzinfo=dt_timezone.utc))

    def test_iso_with_offset_keeps_offset(self):
        parsed = safe_parse_datetime("2025-10-25T00:30:00-05:00")
        self.assertEqual(parsed, datetime(2025, 10, 25, 5, 30, tzinfo=dt_timezone.utc))

    def test_naive_iso_is_assumed_utc(self):
        parsed = safe_parse_datetime("2025-10-25T00:30:00")
        self.assertEqual(parsed.tzinfo, dt_timezone.utc)
        self.assertEqual(parsed.hour, 0)

    def test_unix_timestamp_values(self):
        expected = datetime(2025, 1, 1, tzinfo=dt_timezone.utc).timestamp()
        for value in (int(expected), float(expected), str(int(expected))):
            with self.subTest(value=value):
                parsed = safe_parse_datetime(value)
                self.assertIsNotNone(parsed)
                self.assertEqual(parsed.timestamp(), expected)

    def test_unix_timestamp_is_timezone_aware(self):
        for value in (1735689600, 1735689600.0, "1735689600"):
            with self.subTest(value=value):
                parsed = safe_parse_datetime(value)
                self.assertIsNotNone(parsed.tzinfo)
                self.assertEqual(parsed.timestamp(), 1735689600)

    def test_unparseable_values_return_none(self):
        for value in ("not a date", "", None, [], {}):
            with self.subTest(value=value):
                self.assertIsNone(safe_parse_datetime(value))


class CalculateNewEloTests(SimpleTestCase):
    def test_even_match(self):
        self.assertEqual(calculate_new_elo(1000, 1000, 1.0), 1075)
        self.assertEqual(calculate_new_elo(1000, 1000, 0.0), 925)
        self.assertEqual(calculate_new_elo(1000, 1000, 0.5), 1000)

    def test_underdog_gains_more_than_favorite(self):
        underdog_gain = calculate_new_elo(1000, 1400, 1.0) - 1000
        favorite_gain = calculate_new_elo(1400, 1000, 1.0) - 1400
        self.assertGreater(underdog_gain, favorite_gain)
        self.assertGreater(favorite_gain, 0)

    def test_changes_are_zero_sum_for_equal_k(self):
        a, b = 1100, 1300
        new_a = calculate_new_elo(a, b, 1.0)
        new_b = calculate_new_elo(b, a, 0.0)
        self.assertAlmostEqual((new_a - a) + (new_b - b), 0, delta=1)

    def test_returns_int(self):
        self.assertIsInstance(calculate_new_elo(1234, 987, 1.0), int)


class ModelTests(TestCase):
    def setUp(self):
        self.season = Season.objects.create(
            name="S1", start_date="2025-08-01T00:00:00Z", end_date="2026-05-01T00:00:00Z"
        )
        self.competition = Competition.objects.create(name="League")
        self.team = Team.objects.create(name="Alpha")
        self.other = Team.objects.create(name="Bravo")

    def test_str_methods(self):
        player = Player.objects.create(name="p1", team=self.team)
        match = Match.objects.create(
            team1=self.team,
            team2=self.other,
            date=datetime(2025, 10, 1, 18, tzinfo=dt_timezone.utc),
        )
        event = Event.objects.create(
            name="Cup", start_date="2025-10-01T00:00:00Z", end_date="2025-10-02T00:00:00Z"
        )
        ranking = Ranking.objects.create(season=self.season)
        ranking.refresh_from_db()
        item = RankingItem.objects.create(ranking=ranking, team=self.team, rank=1, elo=1100)
        event_match = EventMatch.objects.create(match=match, event=event)
        custom = CustomEvent.objects.create(event=event)

        self.assertEqual(str(self.team), "Alpha")
        self.assertEqual(str(player), "p1")
        self.assertEqual(str(match), "Alpha vs Bravo on 2025-10-01 18:00:00")
        self.assertEqual(str(self.season), "S1")
        self.assertEqual(str(self.competition), "League")
        self.assertEqual(str(event), "Cup")
        self.assertTrue(str(ranking).startswith("Ranking on "))
        self.assertEqual(str(item), "Alpha - Rank 1 - Elo 1100")
        self.assertEqual(str(event_match), "EVENTMATCH: Alpha vs Bravo on 2025-10-01 18:00:00")
        self.assertEqual(str(custom), "Custom: Cup")

    def test_participant_str_handles_missing_relations(self):
        self.assertEqual(
            str(Participant.objects.create(team=self.team, competition=self.competition)),
            "Alpha - League",
        )
        self.assertEqual(str(Participant.objects.create()), "No Team - No Competition")

    def test_captain_must_be_on_team(self):
        outsider = Player.objects.create(name="out", team=self.other)
        self.team.captain = outsider
        with self.assertRaises(ValidationError):
            self.team.clean()

        member = Player.objects.create(name="in", team=self.team)
        self.team.captain = member
        self.team.clean()  # no error

    def test_defaults(self):
        self.assertEqual(self.team.elo, 1000)
        match = Match.objects.create(
            team1=self.team, team2=self.other, date="2025-10-01T18:00:00Z"
        )
        self.assertEqual(match.status, "scheduled")
        self.assertEqual(match.platform, "other")
        self.assertFalse(match.elo_applied)


class IndexTests(TestCase):
    def test_index(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"College Counter", response.content)
