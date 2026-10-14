"""
Background refreshing of matches from their platforms, run by the
sync_matches management command.

Each unfinished match falls in a tier by how live or how soon it is, and is
refreshed once its tier's interval has passed since the last attempt. Failing
matches back off, and unfinished matches long past their start time are
flagged for an admin (sync_disabled) instead of being retried forever.
"""

import logging
import time
from collections import Counter
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from ..models import Match
from . import platform_sync
from .platform_sync import PLATFORM_UPDATERS, STALE_AFTER

logger = logging.getLogger(__name__)

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)

# Most urgent first: a pass refreshes in this order, so the LeagueSpot cap
# drops the least urgent matches
TIERS = ["live", "overdue", "imminent", "today", "upcoming", "straggler"]

# How often each tier is refreshed. LeagueSpot's API is reverse engineered
# from their site, so it's polled far less to avoid getting rate limited; it
# has no live scores anyway, only a switch to completed.
INTERVALS = {
    "live": {"default": MINUTE, "leaguespot": 5 * MINUTE},
    "overdue": {"default": 2 * MINUTE, "leaguespot": 10 * MINUTE},
    "imminent": {"default": 5 * MINUTE, "leaguespot": 15 * MINUTE},
    "today": {"default": 30 * MINUTE, "leaguespot": 2 * HOUR},
    "upcoming": {"default": 6 * HOUR, "leaguespot": 12 * HOUR},
    "straggler": {"default": 6 * HOUR, "leaguespot": 24 * HOUR},
}

# At most this many LeagueSpot matches per pass (a pass runs every 30s), with
# a pause between them, so requests never burst
LEAGUESPOT_PER_PASS = 3
LEAGUESPOT_GAP_SECONDS = 2.0

# Failing matches wait interval * 2^failures, up to this
MAX_BACKOFF = HOUR


# Past their start time by more than this, unfinished matches are stragglers:
# probably stuck (e.g. Faceit's MANUAL_RESULT, waiting on an admin), not live
STRAGGLER_AFTER = timedelta(hours=12)


def tier_for(match, now):
    """The match's tier, or None if it isn't refreshed in the background."""
    if match.status not in ("scheduled", "in_progress"):
        return None
    until_start = match.date - now
    if -until_start > STRAGGLER_AFTER:
        return "straggler"
    if match.status == "in_progress":
        return "live"
    if until_start < timedelta(0):
        return "overdue"
    if until_start <= HOUR:
        return "imminent"
    if until_start <= timedelta(hours=24):
        return "today"
    if until_start <= timedelta(days=7):
        return "upcoming"
    return None


def interval_for(tier, match):
    intervals = INTERVALS[tier]
    interval = intervals.get(match.platform, intervals["default"])
    if match.sync_failures:
        interval = max(interval, min(interval * 2**match.sync_failures, MAX_BACKOFF))
    return interval


def is_due(match, tier, now):
    return (
        match.last_synced_at is None
        or now - match.last_synced_at >= interval_for(tier, match)
    )


def flag_stale_matches(now):
    """
    Stop refreshing unfinished matches long past their start time; they show
    up in the admin's needs-review list instead. Returns how many were flagged.
    """
    return Match.objects.filter(
        status__in=["scheduled", "in_progress"],
        date__lt=now - STALE_AFTER,
        sync_disabled=False,
    ).update(sync_disabled=True)


def tracked_queryset(now):
    return Match.objects.filter(
        sync_disabled=False,
        platform__in=PLATFORM_UPDATERS.keys(),
        date__gte=now - STALE_AFTER,
        date__lte=now + timedelta(days=7),
        status__in=["scheduled", "in_progress"],
    ).select_related("team1", "team2", "competition", "season")


def tracked_matches(now):
    """Matches the background sync refreshes, with their tier."""
    for match in tracked_queryset(now):
        tier = tier_for(match, now)
        if tier:
            yield tier, match


def due_matches(now):
    """(tier, match) pairs due a refresh, most urgent tier first."""
    due = [
        (tier, match)
        for tier, match in tracked_matches(now)
        if is_due(match, tier, now)
    ]
    due.sort(key=lambda pair: (TIERS.index(pair[0]), pair[1].date))
    return due


def sync_due_matches(now=None, sleep=time.sleep):
    """
    One background pass: flag stale matches, then refresh every due match.
    Returns counts, e.g. {"flagged_stale": 0, "live:updated": 2, ...}.
    """
    now = now or timezone.now()
    summary = Counter(flagged_stale=flag_stale_matches(now))

    leaguespot_done = 0
    for tier, match in due_matches(now):
        # A pass can take a while (LeagueSpot's gaps, slow responses), and the
        # sync saves the whole match: reload it so an admin's edit since the
        # pass started (e.g. Mark cancelled) isn't written back over
        match = tracked_queryset(now).filter(pk=match.pk).first()
        if match is None:
            summary[f"{tier}:skipped"] += 1
            continue

        if match.platform == "leaguespot":
            if leaguespot_done >= LEAGUESPOT_PER_PASS:
                summary[f"{tier}:deferred"] += 1
                continue
            if leaguespot_done:
                sleep(LEAGUESPOT_GAP_SECONDS)
            leaguespot_done += 1

        outcome, _ = platform_sync.sync_match(match, now)
        summary[f"{tier}:{outcome}"] += 1

    return dict(summary)


# A due match waiting this much longer than a pass means the worker is behind
# or not running
WORKER_LATE_AFTER = 5 * MINUTE


def sync_status(now=None):
    """Health numbers for the admin control panel."""
    now = now or timezone.now()
    tiers = {tier: {"tracked": 0, "due": 0} for tier in TIERS}
    platforms = {
        platform: {"tracked": 0, "due": 0, "failing": 0, "last_synced_at": None}
        for platform in PLATFORM_UPDATERS
    }
    most_late = timedelta(0)

    for tier, match in tracked_matches(now):
        tiers[tier]["tracked"] += 1
        platform = platforms[match.platform]
        platform["tracked"] += 1
        if match.sync_failures:
            platform["failing"] += 1
        if is_due(match, tier, now):
            tiers[tier]["due"] += 1
            platform["due"] += 1
            if match.last_synced_at:
                late = now - match.last_synced_at - interval_for(tier, match)
                most_late = max(most_late, late)

    for platform, last in (
        Match.objects.filter(platform__in=PLATFORM_UPDATERS.keys())
        .values_list("platform")
        .annotate(last=Max("last_synced_at"))
    ):
        platforms[platform]["last_synced_at"] = last

    last_synced_at = max(
        (p["last_synced_at"] for p in platforms.values() if p["last_synced_at"]),
        default=None,
    )
    # Matches are due but nothing has been refreshed lately: the worker isn't
    # running. (Matches never synced don't count towards most_late, so this
    # is what catches a worker that never started.)
    due_now = sum(tier["due"] for tier in tiers.values())
    stalled = due_now > 0 and (
        last_synced_at is None or now - last_synced_at > WORKER_LATE_AFTER
    )
    recent_errors = (
        Match.objects.filter(last_sync_error__isnull=False)
        .select_related("team1", "team2")
        .order_by("-last_synced_at")[:10]
    )
    return {
        "now": now,
        "last_synced_at": last_synced_at,
        # Due matches waiting well past their interval: the worker is down,
        # or there's more to refresh than it gets through
        "worker_behind": stalled or most_late > WORKER_LATE_AFTER,
        "worker_stalled": stalled,
        "most_late_seconds": int(most_late.total_seconds()),
        "tiers": tiers,
        "platforms": platforms,
        "failing": Match.objects.filter(sync_failures__gt=0, sync_disabled=False).count(),
        "disabled": Match.objects.filter(sync_disabled=True)
        .exclude(status__in=["completed", "cancelled"])
        .count(),
        "recent_errors": [
            {
                "match_id": str(match.id),
                "team1": match.team1.name,
                "team2": match.team2.name,
                "platform": match.platform,
                "error": match.last_sync_error,
                "failures": match.sync_failures,
                "at": match.last_synced_at,
            }
            for match in recent_errors
        ],
    }
