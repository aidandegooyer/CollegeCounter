"""Background match sync: tiers, back-off, giving up, and the admin review views."""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cc.models import Match
from cc.views.match_sync import (
    LEAGUESPOT_PER_PASS,
    due_matches,
    interval_for,
    sync_due_matches,
    sync_status,
    tier_for,
)
from cc.views.platform_sync import sync_match

from .helpers import Fixtures, admin_settings, dev_client

NOW = timezone.now().replace(microsecond=0)


def patch_updaters(faceit=False, leaguespot=False, regents=False):
    def updater(result):
        kwargs = {"side_effect": result} if isinstance(result, Exception) else {
            "return_value": result
        }
        return kwargs

    return (
        patch("cc.views.platform_sync.update_faceit_match", **updater(faceit)),
        patch("cc.views.platform_sync.update_leaguespot_match", **updater(leaguespot)),
        patch("cc.views.platform_sync.update_regentsleague_match", **updater(regents)),
    )


class MatchSyncFixtures(Fixtures):
    def setUp(self):
        self.make_base()

    def make_match(self, starts_in=timedelta(hours=2), **kwargs):
        defaults = dict(
            team1=self.alpha,
            team2=self.bravo,
            date=NOW + starts_in,
            competition=self.competition,
            season=self.season,
            platform="faceit",
        )
        defaults.update(kwargs)
        return Match.objects.create(**defaults)

    def run_pass(self, now=NOW, **results):
        f, l, r = patch_updaters(**results)
        with f as faceit, l as leaguespot, r as regents:
            summary = sync_due_matches(now, sleep=lambda seconds: None)
        return summary, (faceit, leaguespot, regents)


class TierTests(MatchSyncFixtures, TestCase):
    def test_tiers(self):
        cases = [
            (dict(status="in_progress", starts_in=-timedelta(days=3)), "live"),
            (dict(starts_in=-timedelta(hours=2)), "overdue"),
            (dict(starts_in=-timedelta(hours=13)), "straggler"),
            (dict(starts_in=timedelta(minutes=30)), "imminent"),
            (dict(starts_in=timedelta(hours=5)), "today"),
            (dict(starts_in=timedelta(days=3)), "upcoming"),
            (dict(starts_in=timedelta(days=8)), None),
            (dict(status="completed", starts_in=-timedelta(hours=1)), None),
            (dict(status="cancelled"), None),
        ]
        for kwargs, tier in cases:
            with self.subTest(kwargs):
                self.assertEqual(tier_for(self.make_match(**kwargs), NOW), tier)

    def test_leaguespot_is_polled_less(self):
        faceit = self.make_match(status="in_progress")
        leaguespot = self.make_match(status="in_progress", platform="leaguespot")
        self.assertEqual(interval_for("live", faceit), timedelta(minutes=1))
        self.assertGreater(interval_for("live", leaguespot), interval_for("live", faceit))

    def test_failures_back_off(self):
        match = self.make_match(status="in_progress", sync_failures=3)
        self.assertEqual(interval_for("live", match), timedelta(minutes=8))
        match.sync_failures = 20
        self.assertEqual(interval_for("live", match), timedelta(hours=1))

    def test_due(self):
        live = self.make_match(status="in_progress", last_synced_at=NOW - timedelta(seconds=30))
        never = self.make_match(starts_in=timedelta(days=2))
        recent = self.make_match(starts_in=timedelta(days=2), last_synced_at=NOW - timedelta(hours=1))
        self.make_match(sync_disabled=True)
        self.make_match(platform="other")
        due = [match.id for _, match in due_matches(NOW)]
        self.assertEqual(due, [never.id])

        due = [match.id for _, match in due_matches(NOW + timedelta(minutes=1))]
        self.assertEqual(due, [live.id, never.id])
        self.assertNotIn(recent.id, due)

    def test_most_urgent_first(self):
        upcoming = self.make_match(starts_in=timedelta(days=2))
        live = self.make_match(status="in_progress")
        imminent = self.make_match(starts_in=timedelta(minutes=10))
        self.assertEqual(
            [match.id for _, match in due_matches(NOW)], [live.id, imminent.id, upcoming.id]
        )


class SyncPassTests(MatchSyncFixtures, TestCase):
    def test_records_attempts(self):
        match = self.make_match(status="in_progress", sync_failures=2)
        summary, (faceit, _, _) = self.run_pass(faceit=True)
        self.assertEqual(summary["live:updated"], 1)
        faceit.assert_called_once()
        match.refresh_from_db()
        self.assertEqual((match.last_synced_at, match.sync_failures), (NOW, 0))

        # Not due again until the live interval has passed
        summary, (faceit, _, _) = self.run_pass(now=NOW + timedelta(seconds=30))
        faceit.assert_not_called()

    def test_failures_count_up_and_back_off(self):
        match = self.make_match(status="in_progress")
        summary, _ = self.run_pass(faceit=RuntimeError("down"))
        self.assertEqual(summary["live:failed"], 1)
        match.refresh_from_db()
        self.assertEqual(match.sync_failures, 1)
        self.assertFalse(match.sync_disabled)
        self.assertEqual(match.last_sync_error, "down")

        self.run_pass(now=NOW + timedelta(minutes=5), faceit=True)
        match.refresh_from_db()
        self.assertIsNone(match.last_sync_error)

    def test_live_matches_are_never_given_up_on(self):
        match = self.make_match(status="in_progress", starts_in=-timedelta(hours=1), sync_failures=10)
        sync_match_with(match, RuntimeError("outage"))
        match.refresh_from_db()
        self.assertEqual(match.sync_failures, 11)
        self.assertFalse(match.sync_disabled)

    def test_old_matches_are_given_up_on_after_repeated_failures(self):
        match = self.make_match(starts_in=-timedelta(days=2), sync_failures=4)
        sync_match_with(match, RuntimeError("404"))
        match.refresh_from_db()
        self.assertTrue(match.sync_disabled)

    def test_stale_matches_are_flagged_not_synced(self):
        stale = self.make_match(starts_in=-timedelta(days=15))
        stale_live = self.make_match(status="in_progress", starts_in=-timedelta(days=15))
        finished = self.make_match(status="completed", starts_in=-timedelta(days=15))
        summary, (faceit, _, _) = self.run_pass()
        self.assertEqual(summary["flagged_stale"], 2)
        faceit.assert_not_called()
        self.assertEqual(
            set(Match.objects.filter(sync_disabled=True).values_list("id", flat=True)),
            {stale.id, stale_live.id},
        )
        finished.refresh_from_db()
        self.assertEqual(finished.status, "completed")

    def test_leaguespot_is_capped_per_pass(self):
        for _ in range(LEAGUESPOT_PER_PASS + 2):
            self.make_match(status="in_progress", platform="leaguespot")
        summary, (_, leaguespot, _) = self.run_pass()
        self.assertEqual(leaguespot.call_count, LEAGUESPOT_PER_PASS)
        self.assertEqual(summary["live:deferred"], 2)
        # The deferred ones go next pass
        summary, (_, leaguespot, _) = self.run_pass(now=NOW + timedelta(seconds=30))
        self.assertEqual(leaguespot.call_count, 2)

    def test_management_command_runs_a_pass(self):
        self.make_match(status="in_progress")
        f, l, r = patch_updaters(faceit=True)
        with f as faceit, l, r:
            call_command("sync_matches", stdout=open("/dev/null", "w"))
        faceit.assert_called_once()


class SyncStatusTests(MatchSyncFixtures, TestCase):
    def test_counts(self):
        self.make_match(status="in_progress", last_synced_at=NOW - timedelta(seconds=20))
        self.make_match(
            starts_in=timedelta(minutes=30), platform="leaguespot", last_synced_at=NOW
        )
        failing = self.make_match(
            starts_in=timedelta(days=2), sync_failures=2, last_sync_error="Faceit API returned 503",
            last_synced_at=NOW - timedelta(minutes=1),
        )
        self.make_match(starts_in=-timedelta(days=20), sync_disabled=True)

        status = sync_status(NOW)
        self.assertEqual(status["tiers"]["live"], {"tracked": 1, "due": 0})
        self.assertEqual(status["tiers"]["imminent"], {"tracked": 1, "due": 0})
        self.assertEqual(status["platforms"]["faceit"]["failing"], 1)
        self.assertEqual(status["platforms"]["leaguespot"]["last_synced_at"], NOW)
        self.assertEqual(status["last_synced_at"], NOW)
        self.assertEqual((status["failing"], status["disabled"]), (1, 1))
        self.assertEqual(status["recent_errors"][0]["match_id"], str(failing.id))
        self.assertFalse(status["worker_behind"])

    def test_worker_behind(self):
        self.make_match(status="in_progress", last_synced_at=NOW - timedelta(minutes=10))
        status = sync_status(NOW)
        self.assertTrue(status["worker_behind"])
        self.assertEqual(status["most_late_seconds"], 9 * 60)


def sync_match_with(match, error):
    with patch("cc.views.platform_sync.update_faceit_match", side_effect=error):
        return sync_match(match, NOW)


@admin_settings
class ReviewEndpointTests(MatchSyncFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.client = dev_client()

    def test_lists_given_up_and_unknown_state_matches(self):
        given_up = self.make_match(sync_disabled=True, sync_failures=5)
        unknown = self.make_match(platform_status="SOMETHING_NEW")
        self.make_match(platform_status="READY")
        self.make_match(status="completed", sync_disabled=True)
        body = self.client.get(reverse("sync_review")).json()
        rows = {row["id"]: row for row in body["matches"]}
        self.assertEqual(set(rows), {str(given_up.id), str(unknown.id)})
        self.assertTrue(rows[str(unknown.id)]["unknown_platform_status"])
        self.assertEqual(rows[str(given_up.id)]["sync_failures"], 5)

    def test_retry_reenables_and_syncs(self):
        match = self.make_match(sync_disabled=True, sync_failures=5)
        with patch("cc.views.platform_sync.update_faceit_match", return_value=True):
            body = self.client.post(reverse("retry_match_sync", args=[match.id])).json()
        self.assertEqual(body["outcome"], "updated")
        self.assertFalse(body["still_stale"])
        match.refresh_from_db()
        self.assertEqual((match.sync_disabled, match.sync_failures), (False, 0))

    def test_status_endpoint(self):
        self.make_match(status="in_progress")
        body = self.client.get(reverse("sync_status")).json()
        self.assertEqual(body["tiers"]["live"], {"tracked": 1, "due": 1})

    def test_retry_unknown_match(self):
        response = self.client.post(
            reverse("retry_match_sync", args=["6f1c2a8e-4b1d-4c7e-9a52-0d3e8b7f1a90"])
        )
        self.assertEqual(response.status_code, 404)


@admin_settings
class UpdateMatchesSkipsGivenUpTests(MatchSyncFixtures, TestCase):
    def test_skips_disabled_and_stale_unless_asked_by_id(self):
        client = dev_client()
        disabled = self.make_match(sync_disabled=True, starts_in=-timedelta(days=1))
        stale = self.make_match(starts_in=-timedelta(days=20))
        f, l, r = patch_updaters(faceit=False)
        with f as faceit, l, r:
            body = client.post(reverse("update_matches"), {}, format="json").json()
            self.assertEqual(body["total_processed"], 0)
            body = client.post(
                reverse("update_matches"),
                {"match_ids": [str(disabled.id), str(stale.id)]},
                format="json",
            ).json()
        self.assertEqual(body["total_processed"], 2)
        self.assertEqual(faceit.call_count, 2)
