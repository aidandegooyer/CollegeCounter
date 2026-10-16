"""Platform match states mapped to our Match.status values."""

import logging

logger = logging.getLogger(__name__)

STATUS_MAPS = {
    "faceit": {
        "SCHEDULED": "scheduled",
        "READY": "scheduled",
        # Map veto / server setup counts as live: the teams are in the room
        "CONFIGURING": "in_progress",
        "VOTING": "in_progress",
        "ONGOING": "in_progress",
        "PAUSED": "in_progress",
        # Played, waiting on an admin to enter the result
        "MANUAL_RESULT": "in_progress",
        "FINISHED": "completed",
        "CANCELLED": "cancelled",
        "ABORTED": "cancelled",
    },
    # LeagueSpot's currentState (reverse engineered; only these are known)
    "leaguespot": {
        "0": "scheduled",
        "1": "scheduled",
        "2": "in_progress",
        "3": "completed",
    },
    "regentsleague": {
        "Scheduled": "scheduled",
        "In Progress": "in_progress",
        "Completed": "completed",
    },
}


def map_platform_status(platform, raw):
    """
    Our status for a platform's match state, or None if the state is unknown.
    Callers keep the match's current status for unknown states rather than
    guessing, and log them so new states get added here.
    """
    if raw is None:
        return None
    mapped = STATUS_MAPS.get(platform, {}).get(str(raw))
    if mapped is None:
        logger.warning("Unknown %s match status %r", platform, raw)
    return mapped


def is_known_platform_status(platform, raw):
    return raw is not None and str(raw) in STATUS_MAPS.get(platform, {})
