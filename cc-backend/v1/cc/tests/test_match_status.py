"""Mapping platform match states to our statuses."""

from types import SimpleNamespace

from django.test import SimpleTestCase

from cc.views.match_status import is_known_platform_status, map_platform_status
from cc.views.platform_sync import apply_platform_status


class MapPlatformStatusTests(SimpleTestCase):
    def test_known_states(self):
        cases = [
            ("faceit", "READY", "scheduled"),
            ("faceit", "VOTING", "in_progress"),
            ("faceit", "MANUAL_RESULT", "in_progress"),
            ("faceit", "FINISHED", "completed"),
            ("faceit", "ABORTED", "cancelled"),
            ("leaguespot", "2", "in_progress"),
            ("regentsleague", "Completed", "completed"),
        ]
        for platform, raw, expected in cases:
            with self.subTest(platform=platform, raw=raw):
                self.assertEqual(map_platform_status(platform, raw), expected)

    def test_leaguespot_states_arrive_as_ints(self):
        self.assertEqual(map_platform_status("leaguespot", 3), "completed")
        self.assertEqual(map_platform_status("leaguespot", 0), "scheduled")

    def test_none_is_unknown_without_a_warning(self):
        with self.assertNoLogs("cc.views.match_status"):
            self.assertIsNone(map_platform_status("faceit", None))

    def test_unknown_states_are_logged(self):
        for platform, raw in (("faceit", "SOMETHING_NEW"), ("faceit", "ready"), ("playfly", "READY")):
            with self.subTest(platform=platform, raw=raw):
                with self.assertLogs("cc.views.match_status", "WARNING"):
                    self.assertIsNone(map_platform_status(platform, raw))

    def test_is_known_platform_status(self):
        self.assertTrue(is_known_platform_status("faceit", "ONGOING"))
        self.assertTrue(is_known_platform_status("leaguespot", 2))
        self.assertFalse(is_known_platform_status("faceit", "SOMETHING_NEW"))
        self.assertFalse(is_known_platform_status("faceit", None))
        self.assertFalse(is_known_platform_status("playfly", "READY"))


class ApplyPlatformStatusTests(SimpleTestCase):
    def match(self, status="scheduled", platform_status=None):
        return SimpleNamespace(status=status, platform_status=platform_status)

    def test_sets_status_and_records_the_raw_state(self):
        match = self.match()
        self.assertTrue(apply_platform_status(match, "faceit", "ONGOING"))
        self.assertEqual((match.status, match.platform_status), ("in_progress", "ONGOING"))

    def test_no_change_returns_false(self):
        match = self.match("in_progress", "ONGOING")
        self.assertFalse(apply_platform_status(match, "faceit", "ONGOING"))

    def test_new_raw_state_with_the_same_status_is_a_change(self):
        match = self.match("in_progress", "ONGOING")
        self.assertTrue(apply_platform_status(match, "faceit", "PAUSED"))
        self.assertEqual((match.status, match.platform_status), ("in_progress", "PAUSED"))

    def test_unknown_state_keeps_the_status_but_is_recorded(self):
        match = self.match("in_progress", "ONGOING")
        with self.assertLogs("cc.views.match_status", "WARNING"):
            self.assertTrue(apply_platform_status(match, "faceit", "SOMETHING_NEW"))
        self.assertEqual((match.status, match.platform_status), ("in_progress", "SOMETHING_NEW"))

    def test_raw_state_is_stored_as_a_string(self):
        match = self.match()
        self.assertTrue(apply_platform_status(match, "leaguespot", 2))
        self.assertEqual((match.status, match.platform_status), ("in_progress", "2"))
        self.assertFalse(apply_platform_status(match, "leaguespot", "2"))
