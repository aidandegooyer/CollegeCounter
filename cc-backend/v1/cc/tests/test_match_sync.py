"""Background match sync: tiers, back-off, giving up, and the admin review views."""

import io
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.db import connections
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cc.management.commands import sync_matches
from cc.models import Match, Participant
from cc.views.match_sync import (
    LEAGUESPOT_GAP_SECONDS,
    LEAGUESPOT_PER_PASS,
    due_matches,
    interval_for,
    sync_due_matches,
    sync_status,
    tier_for,
)
from cc.views.platform_sync import PlatformSyncError, sync_match

from .helpers import Fixtures, admin_settings, dev_client, fake_response, token_client

# Real time, since the endpoints use the clock; every boundary tested is
# minutes or hours wide, so the few seconds a run takes don't matter
NOW = timezone.now().replace(microsecond=0)


def sync_match_with(match, error):
    with patch("cc.views.platform_sync.update_faceit_match", side_effect=error):
        return sync_match(match, NOW)


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

    def run_pass(self, now=NOW, sleeps=None, **results):
        f, l, r = patch_updaters(**results)
        sleep = sleeps.append if sleeps is not None else (lambda seconds: None)
        with f as faceit, l as leaguespot, r as regents:
            summary = sync_due_matches(now, sleep=sleep)
        return summary, (faceit, leaguespot, regents)


class TierTests(MatchSyncFixtures, TestCase):
    def test_tiers(self):
        cases = [
            (dict(status="in_progress", starts_in=-timedelta(hours=3)), "live"),
            # Still "live" this long after its start, it's stuck (e.g. Faceit's
            # MANUAL_RESULT), so it isn't polled every minute
            (dict(status="in_progress", starts_in=-timedelta(hours=13)), "straggler"),
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
        summary, _ = self.run_pass(faceit=PlatformSyncError("down"))
        self.assertEqual(summary["live:failed"], 1)
        match.refresh_from_db()
        self.assertEqual(match.sync_failures, 1)
        self.assertFalse(match.sync_disabled)
        self.assertEqual(match.last_sync_error, "down")

        self.run_pass(now=NOW + timedelta(minutes=5), faceit=True)
        match.refresh_from_db()
        self.assertIsNone(match.last_sync_error)

    def test_failures_back_off_between_passes(self):
        self.make_match(status="in_progress")
        self.run_pass(faceit=PlatformSyncError("down"))
        # One failure doubles the 1 minute live interval
        _, (faceit, _, _) = self.run_pass(now=NOW + timedelta(minutes=1))
        faceit.assert_not_called()
        _, (faceit, _, _) = self.run_pass(now=NOW + timedelta(minutes=2))
        faceit.assert_called_once()

    def test_matches_near_their_start_are_never_given_up_on(self):
        # A platform outage during a live match only backs it off
        match = self.make_match(status="in_progress", starts_in=-timedelta(hours=1), sync_failures=10)
        sync_match_with(match, PlatformSyncError("outage"))
        match.refresh_from_db()
        self.assertEqual(match.sync_failures, 11)
        self.assertFalse(match.sync_disabled)

    def test_give_up_needs_both_repeated_failures_and_an_old_match(self):
        cases = [
            # (failures before, started this long ago, given up)
            (4, timedelta(hours=13), True),
            (4, timedelta(hours=11), False),
            (3, timedelta(days=2), False),
            (4, timedelta(days=2), True),
        ]
        for failures, ago, given_up in cases:
            with self.subTest(failures=failures, ago=ago):
                match = self.make_match(starts_in=-ago, sync_failures=failures)
                sync_match_with(match, PlatformSyncError("404"))
                match.refresh_from_db()
                self.assertEqual(match.sync_failures, failures + 1)
                self.assertEqual(match.sync_disabled, given_up)

    def test_unexpected_errors_keep_the_traceback(self):
        match = self.make_match()
        with self.assertLogs("cc.views.platform_sync", "ERROR") as logs:
            sync_match_with(match, KeyError("teams"))
        self.assertIn("Traceback", logs.output[0])
        match.refresh_from_db()
        self.assertEqual(match.last_sync_error, "Internal error (KeyError): 'teams'")

    def test_long_errors_are_truncated(self):
        match = self.make_match()
        sync_match_with(match, PlatformSyncError("x" * 5000))
        match.refresh_from_db()
        self.assertEqual(len(match.last_sync_error), 1000)

    def test_admin_edits_during_a_pass_are_not_overwritten(self):
        match = self.make_match(status="in_progress")
        listed = due_matches(NOW)
        # An admin marks it cancelled after the pass listed it
        Match.objects.filter(pk=match.pk).update(status="cancelled")
        with patch("cc.views.match_sync.due_matches", return_value=listed):
            summary, (faceit, _, _) = self.run_pass(faceit=True)
        faceit.assert_not_called()
        self.assertEqual(summary["live:skipped"], 1)
        match.refresh_from_db()
        self.assertEqual(match.status, "cancelled")

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
        sleeps = []
        summary, (_, leaguespot, _) = self.run_pass(sleeps=sleeps)
        self.assertEqual(leaguespot.call_count, LEAGUESPOT_PER_PASS)
        self.assertEqual(summary["live:deferred"], 2)
        # A gap between requests, never a burst
        self.assertEqual(sleeps, [LEAGUESPOT_GAP_SECONDS] * (LEAGUESPOT_PER_PASS - 1))
        # The deferred ones go next pass
        summary, (_, leaguespot, _) = self.run_pass(now=NOW + timedelta(seconds=30))
        self.assertEqual(leaguespot.call_count, 2)

    def test_leaguespot_cap_keeps_the_most_urgent(self):
        today = [
            self.make_match(starts_in=timedelta(hours=3, minutes=i), platform="leaguespot")
            for i in range(LEAGUESPOT_PER_PASS)
        ]
        live = self.make_match(status="in_progress", platform="leaguespot")
        for _ in range(LEAGUESPOT_PER_PASS + 1):
            self.make_match(status="in_progress")  # Faceit doesn't count
        summary, (faceit, leaguespot, _) = self.run_pass()
        synced = [call.args[0].id for call in leaguespot.call_args_list]
        self.assertEqual(synced, [live.id] + [match.id for match in today[:-1]])
        self.assertEqual(summary["today:deferred"], 1)
        self.assertEqual(faceit.call_count, LEAGUESPOT_PER_PASS + 1)


@override_settings(FACEIT_API_KEY="faceit-key")
class MatchLifecycleTests(MatchSyncFixtures, TestCase):
    """A Faceit match driven through the background sync, start to finish."""

    def setUp(self):
        super().setUp()
        for team, faction in ((self.alpha, "f-alpha"), (self.bravo, "f-bravo")):
            Participant.objects.create(
                team=team, competition=self.competition, season=self.season, faceit_id=faction
            )
        self.match = self.make_match(starts_in=timedelta(minutes=30), url="https://faceit.com/x")

    def faceit_pass(self, now, state, score=None, winner=None):
        data = {
            "status": state,
            "teams": {
                "faction1": {"faction_id": "f-alpha"},
                "faction2": {"faction_id": "f-bravo"},
            },
        }
        if score:
            data["results"] = {
                "winner": winner,
                "score": {"faction1": score[0], "faction2": score[1]},
            }
        with patch(
            "cc.views.platform_sync.requests.get", return_value=fake_response(json_data=data)
        ) as get:
            sync_due_matches(now, sleep=lambda seconds: None)
        self.match.refresh_from_db()
        self.alpha.refresh_from_db()
        return get

    def test_elo_is_applied_once_on_completion(self):
        self.faceit_pass(NOW, "READY")
        self.assertEqual(self.match.status, "scheduled")

        self.faceit_pass(NOW + timedelta(minutes=10), "ONGOING", score=(1, 0))
        self.assertEqual(self.match.status, "in_progress")
        self.assertEqual(self.match.score_team1, 1)
        self.assertFalse(self.match.elo_applied)
        self.assertEqual(self.alpha.elo, 1000)

        self.faceit_pass(NOW + timedelta(minutes=20), "FINISHED", score=(2, 0), winner="faction1")
        self.assertEqual(self.match.status, "completed")
        self.assertEqual(self.match.winner, self.alpha)
        self.assertTrue(self.match.elo_applied)
        elo_after = self.alpha.elo
        self.assertGreater(elo_after, 1000)

        # Completed matches drop out, so Elo is never applied twice
        get = self.faceit_pass(
            NOW + timedelta(hours=1), "FINISHED", score=(2, 0), winner="faction1"
        )
        get.assert_not_called()
        self.assertEqual(self.alpha.elo, elo_after)

    def test_aborted_after_going_live_gets_no_result(self):
        self.faceit_pass(NOW, "ONGOING", score=(1, 0))
        self.faceit_pass(NOW + timedelta(minutes=5), "ABORTED", score=(1, 0))
        self.assertEqual(self.match.status, "cancelled")
        self.assertIsNone(self.match.winner)
        self.assertFalse(self.match.elo_applied)


class ManagementCommandTests(MatchSyncFixtures, TestCase):
    def call(self):
        out = io.StringIO()
        call_command("sync_matches", stdout=out)
        return out.getvalue()

    def other_connection(self):
        # Advisory locks are re-entrant within a session, so contend for it
        # from a second connection to the test database
        other = connections.create_connection("default")
        self.addCleanup(other.close)
        return other.cursor()

    def test_runs_a_pass(self):
        self.make_match(status="in_progress")
        f, l, r = patch_updaters(faceit=True)
        with f as faceit, l, r:
            output = self.call()
        faceit.assert_called_once()
        self.assertIn("live:updated=1", output)

    def test_skips_the_pass_while_another_worker_holds_the_lock(self):
        other = self.other_connection()
        other.execute("SELECT pg_advisory_lock(%s)", [sync_matches.LOCK_ID])
        with patch.object(sync_matches, "sync_due_matches") as sync:
            self.call()
        sync.assert_not_called()

        other.execute("SELECT pg_advisory_unlock(%s)", [sync_matches.LOCK_ID])
        with patch.object(sync_matches, "sync_due_matches", return_value={}) as sync:
            self.call()
        sync.assert_called_once()

    def test_releases_the_lock_when_a_pass_fails(self):
        with patch.object(sync_matches, "sync_due_matches", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.call()
        other = self.other_connection()
        other.execute("SELECT pg_try_advisory_lock(%s)", [sync_matches.LOCK_ID])
        self.assertTrue(other.fetchone()[0])
        other.execute("SELECT pg_advisory_unlock(%s)", [sync_matches.LOCK_ID])

    def test_loop_survives_a_failed_pass(self):
        class Stop(Exception):
            pass

        with patch.object(
            sync_matches.Command, "run_pass", side_effect=[RuntimeError("db down"), None]
        ) as run_pass, patch.object(
            sync_matches.time, "sleep", side_effect=[None, Stop()]
        ), patch.object(sync_matches, "connection") as connection, self.assertLogs(
            sync_matches.logger, "ERROR"
        ) as logs:
            with self.assertRaises(Stop):
                call_command("sync_matches", "--loop", stdout=io.StringIO())
        self.assertEqual(run_pass.call_count, 2)
        connection.close.assert_called_once()
        self.assertIn("Match sync pass failed", logs.output[0])


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

    def test_worker_that_never_ran_is_stalled(self):
        self.make_match(status="in_progress")
        status = sync_status(NOW)
        self.assertTrue(status["worker_stalled"])
        self.assertTrue(status["worker_behind"])

    def test_worker_that_stopped_is_stalled(self):
        self.make_match(starts_in=timedelta(days=2), last_synced_at=NOW - timedelta(hours=7))
        self.assertTrue(sync_status(NOW)["worker_stalled"])
        # Nothing due: a quiet worker isn't a stalled one
        self.assertFalse(sync_status(NOW - timedelta(hours=2))["worker_stalled"])

    def test_worker_behind(self):
        self.make_match(status="in_progress", last_synced_at=NOW - timedelta(minutes=10))
        status = sync_status(NOW)
        self.assertTrue(status["worker_behind"])
        self.assertEqual(status["most_late_seconds"], 9 * 60)


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

    def test_retry_that_fails_again(self):
        match = self.make_match(sync_disabled=True, sync_failures=5)
        with patch(
            "cc.views.platform_sync.update_faceit_match",
            side_effect=PlatformSyncError("still 404"),
        ):
            body = self.client.post(reverse("retry_match_sync", args=[match.id])).json()
        self.assertEqual((body["outcome"], body["error"]), ("failed", "still 404"))
        match.refresh_from_db()
        self.assertEqual(match.sync_failures, 1)

    def test_retry_of_a_stale_match_says_so(self):
        match = self.make_match(starts_in=-timedelta(days=20), sync_disabled=True)
        with patch("cc.views.platform_sync.update_faceit_match", return_value=False):
            body = self.client.post(reverse("retry_match_sync", args=[match.id])).json()
        self.assertTrue(body["still_stale"])

    def test_retry_of_an_unsupported_platform_keeps_it_flagged(self):
        match = self.make_match(platform="playfly", sync_disabled=True)
        body = self.client.post(reverse("retry_match_sync", args=[match.id])).json()
        self.assertEqual(body["outcome"], "unsupported")
        match.refresh_from_db()
        self.assertTrue(match.sync_disabled)

    def test_known_state_clears_it_from_review(self):
        match = self.make_match(platform_status="SOMETHING_NEW")
        Match.objects.filter(pk=match.pk).update(platform_status="READY")
        body = self.client.get(reverse("sync_review")).json()
        self.assertEqual(body["matches"], [])

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


class SyncEndpointAuthTests(MatchSyncFixtures, TestCase):
    def test_admin_only(self):
        match = self.make_match(sync_disabled=True)
        user, patcher = token_client({"role": "base"})
        self.addCleanup(patcher.stop)
        requests = [
            ("get", reverse("sync_review")),
            ("get", reverse("sync_status")),
            ("post", reverse("retry_match_sync", args=[match.id])),
        ]
        with patch("cc.views.platform_sync.update_faceit_match") as faceit:
            for method, url in requests:
                with self.subTest(url=url):
                    response = getattr(self.client_class(), method)(url)
                    self.assertEqual(response.status_code, 401)
                    response = getattr(user, method)(url)
                    self.assertEqual(response.status_code, 403)
        faceit.assert_not_called()
        match.refresh_from_db()
        self.assertTrue(match.sync_disabled)
