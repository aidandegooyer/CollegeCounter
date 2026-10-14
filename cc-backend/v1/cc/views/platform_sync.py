"""Refreshing existing matches from Faceit, LeagueSpot and Regents League."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status
from datetime import timedelta
from django.utils import timezone
from django.db import models
from ..models import (
    Competition,
    Match,
    Participant,
)
from ..middleware import firebase_auth_required

import logging
import uuid

import requests

from .elo import save_match_and_sync_elo
from .match_status import is_known_platform_status, map_platform_status
from .proxies import get_leaguespot_headers
from .utils import safe_parse_datetime

logger = logging.getLogger(__name__)


class PlatformSyncError(Exception):
    """A platform couldn't be asked about a match (bad response, missing config)."""


def apply_platform_status(match, platform, raw):
    """
    Record the platform's raw state and set our status from it. Unknown states
    leave the status as it was. Returns True if anything changed.
    """
    raw = None if raw is None else str(raw)
    changed = raw != match.platform_status
    match.platform_status = raw
    new_status = map_platform_status(platform, raw)
    if new_status and new_status != match.status:
        match.status = new_status
        changed = True
    return changed


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def update_matches(request):
    """
    Update existing matches with fresh data from external APIs.
    This will fetch updated information for rescheduled times and match results.

    Expected request format:
    {
        "match_ids": ["uuid1", "uuid2", ...], // Optional - specific matches to update
        "competition_id": "uuid", // Optional - only this competition's matches
        "platform": "faceit" | "leaguespot", // Optional - filter by platform
        "status_filter": "scheduled" | "in_progress" | "completed", // Optional - filter by status
        "auto_detect": true // Optional - automatically detect what needs updating
    }
    """
    try:
        data = request.data
        match_ids = data.get("match_ids", [])
        platform_filter = data.get("platform", "").lower()
        status_filter = data.get("status_filter", "")
        auto_detect = data.get("auto_detect", True)

        # Build query for matches to update
        query = Match.objects.all()

        if match_ids:
            query = query.filter(id__in=match_ids)

        competition_id = data.get("competition_id")
        if competition_id:
            try:
                uuid.UUID(str(competition_id))
            except ValueError:
                return Response(
                    {"error": "Invalid competition_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Otherwise a missing competition looks like one with nothing to update
            if not Competition.objects.filter(id=competition_id).exists():
                return Response(
                    {"error": f"Competition {competition_id} not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            query = query.filter(competition_id=competition_id)

        if platform_filter:
            query = query.filter(platform=platform_filter)

        if status_filter:
            query = query.filter(status=status_filter)
        elif auto_detect:
            # By default, update scheduled and in_progress matches
            query = query.filter(status__in=["scheduled", "in_progress"])

        # Filter to only include matches that happened in the past or are within the next week
        now = timezone.now()
        one_week_from_now = now + timedelta(weeks=1)

        if not match_ids:
            # Matches the background sync gave up on, and old ones it no
            # longer tries, are only refreshed when asked for by ID
            query = query.filter(sync_disabled=False).exclude(
                models.Q(date__lt=now - STALE_AFTER)
                & ~models.Q(status__in=["completed", "cancelled"])
            )

        # Include matches that:
        # 1. Have no date (null dates)
        # 2. Are in the past or within the next week
        # 3. Are currently in progress (regardless of date)
        query = query.filter(
            models.Q(date__isnull=True)  # Matches with no date
            | models.Q(date__lte=one_week_from_now)  # Past matches or within next week
            | models.Q(status="in_progress")  # Currently in progress matches
        )

        matches = list(query)
        updated_count = 0
        error_count = 0
        results = []

        for match in matches:
            outcome, error = sync_match(match, now)
            if outcome == "unsupported":
                logger.warning(
                    f"Unsupported platform for match {match.id}: {match.platform}"
                )
                results.append({"match_id": str(match.id), "status": "unsupported"})
            elif outcome == "updated":
                updated_count += 1
                results.append(
                    {
                        "match_id": str(match.id),
                        "status": "updated",
                        "new_status": match.status,
                        "new_date": match.date.isoformat() if match.date else None,
                    }
                )
            elif outcome == "unchanged":
                results.append({"match_id": str(match.id), "status": "no_changes"})
            else:
                error_count += 1
                results.append(
                    {"match_id": str(match.id), "status": "error", "error": error}
                )

        return Response(
            {
                "message": "Match update completed",
                "updated_count": updated_count,
                "error_count": error_count,
                "total_processed": len(matches),
                "results": results,
            }
        )

    except Exception as e:
        logger.exception("update_matches failed")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


PLATFORM_UPDATERS = {
    "faceit": "update_faceit_match",
    "leaguespot": "update_leaguespot_match",
    "regentsleague": "update_regentsleague_match",
}

# A match that keeps failing this long after it was due to start is given up
# on (sync_disabled) after this many failures in a row. Matches nearer their
# start time back off instead, so a platform outage can't disable live matches.
MAX_SYNC_FAILURES = 5
GIVE_UP_AFTER = timedelta(hours=12)

# Unfinished matches this far past their start time aren't refreshed any more;
# the background sync flags them for review (sync_disabled)
STALE_AFTER = timedelta(days=14)

# Failures that are the platform's, not ours: bad or missing responses, and
# JSON that won't parse (ValueError)
EXPECTED_SYNC_ERRORS = (PlatformSyncError, requests.RequestException, ValueError)


def save_synced_match(match, platform):
    """Save a refreshed match, keeping its Elo in step with the outcome."""
    warning = save_match_and_sync_elo(match)
    if warning:
        logger.warning("Match %s: %s", match.id, warning)
    logger.info("Updated %s match %s", platform, match.id)


def sync_match(match, now=None):
    """
    Refresh one match from its platform and record the attempt.

    Returns (outcome, error): outcome is "updated", "unchanged", "failed" or
    "unsupported" (a platform we can't refresh), and error is the failure's
    message.
    """
    now = now or timezone.now()
    updater_name = PLATFORM_UPDATERS.get(match.platform)
    if not updater_name:
        return "unsupported", None

    try:
        # Looked up at call time so tests can patch the updaters
        updated = globals()[updater_name](match)
    except Exception as e:
        if isinstance(e, EXPECTED_SYNC_ERRORS):
            error = str(e)
        else:
            # A bug or database error, not the platform: keep the traceback.
            # It's still recorded and backed off so one broken match can't
            # stop the rest of the pass.
            logger.exception("Unexpected error syncing match %s", match.id)
            error = f"Internal error ({type(e).__name__}): {e}"
        failures = match.sync_failures + 1
        give_up = failures >= MAX_SYNC_FAILURES and match.date < now - GIVE_UP_AFTER
        fields = {
            "last_synced_at": now,
            "sync_failures": failures,
            # Truncated so a huge HTML error page can't bloat the row
            "last_sync_error": error[:1000],
        }
        if give_up:
            fields["sync_disabled"] = True
        Match.objects.filter(pk=match.pk).update(**fields)
        match.sync_failures = failures
        if give_up:
            match.sync_disabled = True
            logger.warning(
                "Giving up syncing match %s after %d failures: %s",
                match.id,
                failures,
                error,
            )
        else:
            logger.warning("Error updating match %s: %s", match.id, error)
        return "failed", error

    Match.objects.filter(pk=match.pk).update(
        last_synced_at=now, sync_failures=0, last_sync_error=None
    )
    match.last_synced_at = now
    match.sync_failures = 0
    match.last_sync_error = None
    return ("updated" if updated else "unchanged"), None


@api_view(["GET"])
@firebase_auth_required(min_role="admin")
def sync_review(request):
    """
    Unfinished matches the background sync needs an admin for: ones it gave up
    on (sync_disabled), and ones in a platform state we don't recognise.
    """
    unfinished = (
        Match.objects.exclude(status__in=["completed", "cancelled"])
        .filter(models.Q(sync_disabled=True) | models.Q(platform_status__isnull=False))
        .select_related("team1", "team2", "competition")
        .order_by("-date")
    )
    matches = [
        match
        for match in unfinished
        if match.sync_disabled
        or not is_known_platform_status(match.platform, match.platform_status)
    ]
    return Response(
        {
            "matches": [
                {
                    "id": str(match.id),
                    "team1": match.team1.name,
                    "team2": match.team2.name,
                    "date": match.date.isoformat(),
                    "status": match.status,
                    "platform": match.platform,
                    "platform_status": match.platform_status,
                    "unknown_platform_status": not is_known_platform_status(
                        match.platform, match.platform_status
                    )
                    and match.platform_status is not None,
                    "sync_disabled": match.sync_disabled,
                    "sync_failures": match.sync_failures,
                    "last_sync_error": match.last_sync_error,
                    "last_synced_at": (
                        match.last_synced_at.isoformat() if match.last_synced_at else None
                    ),
                    "competition": match.competition.name if match.competition else None,
                }
                for match in matches
            ]
        }
    )


@api_view(["GET"])
@firebase_auth_required(min_role="admin")
def sync_status_view(request):
    """How the background match sync is doing, for the control panel."""
    # Imported here: match_sync imports this module
    from .match_sync import sync_status

    return Response(sync_status())


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def retry_match_sync(request, match_id):
    """Re-enable background sync for a match and refresh it now."""
    try:
        match = Match.objects.select_related("team1", "team2").get(id=match_id)
    except Match.DoesNotExist:
        return Response({"error": "Match not found"}, status=status.HTTP_404_NOT_FOUND)

    if match.platform not in PLATFORM_UPDATERS:
        # Nothing can refresh it; re-enabling it would only hide it from review
        return Response(
            {
                "outcome": "unsupported",
                "error": None,
                "status": match.status,
                "platform_status": match.platform_status,
                "still_stale": False,
            }
        )

    Match.objects.filter(pk=match.pk).update(sync_disabled=False, sync_failures=0)
    match.sync_disabled = False
    match.sync_failures = 0
    outcome, error = sync_match(match)
    match.refresh_from_db()
    return Response(
        {
            "outcome": outcome,
            "error": error,
            "status": match.status,
            "platform_status": match.platform_status,
            # Still long past its start time, so the next pass flags it again
            "still_stale": match.status in ("scheduled", "in_progress")
            and match.date < timezone.now() - STALE_AFTER,
        }
    )


def update_regentsleague_match(match: Match):
    """
    Update a single Regents League match with fresh data from the API
    Returns True if the match was updated, False if no changes
    """
    regentsleague_match_id = match.regentsleague_id
    response = requests.get(
        f"https://regent-league-api.poopdealer.lol/cc/match?id={regentsleague_match_id}",
        timeout=30,
    )

    if response.status_code != 200:
        raise PlatformSyncError(
            f"Regents League API returned {response.status_code} for match {regentsleague_match_id}"
        )

    match_data: dict = response.json()
    updated = apply_platform_status(
        match, "regentsleague", match_data.get("status")
    )
    new_status = match.status

    parsed_date = safe_parse_datetime(match_data.get("date"))
    if parsed_date and parsed_date != match.date:
        match.date = parsed_date
        updated = True

    # Update results if match is finished
    if new_status == "completed":
        # Get team data to map factions to our teams using Faceit IDs
        team1_data: dict = match_data.get("team1")
        team2_data: dict = match_data.get("team2")

        team1_id = team1_data.get("id")
        team2_id = team2_data.get("id")

        flipped = False
        team1_participant = None
        team2_participant = None
        try:
            team1_participant = Participant.objects.get(
                team=match.team1,
                competition=match.competition,
                season=match.season,
                regentsleague_id=team1_id,
            )
        except Participant.DoesNotExist:
            # Sometimes team1 and team2 gets flipped after scored are entered.
            try:
                team1_participant = Participant.objects.get(
                    team=match.team1,
                    competition=match.competition,
                    season=match.season,
                    regentsleague_id=team2_id,
                )
                flipped = True
            except Participant.DoesNotExist:
                logger.warning(
                    f"Could not find participant for team1 {match.team1.name} in match {match.id}"
                )

        try:
            team2_participant = Participant.objects.get(
                team=match.team2,
                competition=match.competition,
                season=match.season,
                regentsleague_id=team2_id,
            )
        except Participant.DoesNotExist:
            # Sometimes team1 and team2 gets flipped after scored are entered.
            try:
                team2_participant = Participant.objects.get(
                    team=match.team2,
                    competition=match.competition,
                    season=match.season,
                    regentsleague_id=team1_id,
                )
                flipped = True
            except Participant.DoesNotExist:
                logger.warning(
                    f"Could not find participant for team2 {match.team2.name} in match {match.id}"
                )

        if team1_participant and team2_participant:
            if flipped:
                team1 = match.team1
                team2 = match.team2

                match.team2 = team1
                match.team1 = team2
            logger.info(
                f"Match {match.id}: {match.team1.name} -> {team1_participant}, {match.team2.name} -> {team2_participant}"
            )

            # Get scores
            new_score_team1 = match_data.get("score_team1")
            new_score_team2 = match_data.get("score_team2")

            # Update scores if they changed
            if new_score_team1 != match.score_team1:
                match.score_team1 = new_score_team1
                updated = True
            if new_score_team2 != match.score_team2:
                match.score_team2 = new_score_team2
                updated = True

            # Determine winner
            winner_id = (match_data.get("winner") or {}).get("id")
            new_winner = None
            if winner_id is not None and winner_id == team1_participant.regentsleague_id:
                new_winner = team1_participant.team
            elif winner_id is not None and winner_id == team2_participant.regentsleague_id:
                new_winner = team2_participant.team
            if new_winner != match.winner:
                match.winner = new_winner
                updated = True
        else:
            # Saving it completed without a result would stick: completed
            # matches aren't refreshed again
            raise PlatformSyncError(
                f"Finished on Regents League, but its teams don't match ours "
                f"({match.team1.name}, {match.team2.name})"
            )
    if updated:
        # Saves and reverts/applies Elo if the outcome changed
        save_synced_match(match, "Regents League")

    return updated


def update_faceit_match(match):
    """
    Update a single Faceit match with fresh data from the API
    Returns True if the match was updated, False if no changes
    """
    if not match.url:
        raise PlatformSyncError("Match has no Faceit URL")

    # Extract match ID from Faceit URL
    # URLs are typically like: https://www.faceit.com/en/csgo/room/1-abc123-def456...
    faceit_match_id = match.id

    # Fetch match data from Faceit API
    api_key = getattr(settings, "FACEIT_API_KEY", None)
    if not api_key:
        raise PlatformSyncError("FACEIT_API_KEY not configured")

    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(
        f"https://open.faceit.com/data/v4/matches/1-{faceit_match_id}",
        headers=headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise PlatformSyncError(
            f"Faceit API returned {response.status_code} for match {faceit_match_id}"
        )

    match_data = response.json()
    updated = apply_platform_status(match, "faceit", match_data.get("status"))
    new_status = match.status

    # Update date/time
    scheduled_at = match_data.get("scheduled_at")
    started_at = match_data.get("started_at")
    finished_at = match_data.get("finished_at")

    # Use the most appropriate timestamp
    if finished_at:
        new_date = finished_at
    elif started_at:
        new_date = started_at
    elif scheduled_at:
        new_date = scheduled_at
    else:
        new_date = None

    if new_date:
        parsed_date = safe_parse_datetime(new_date)
        if parsed_date and parsed_date != match.date:
            match.date = parsed_date
            updated = True

    # Scores while live too, if Faceit has any yet (e.g. maps won in a Bo3);
    # the winner only once it's finished
    if new_status in ("in_progress", "completed"):
        results = match_data.get("results") or {}
        if results:
            # Get team data to map factions to our teams using Faceit IDs
            teams_data = match_data.get("teams", {})
            faction1_data = teams_data.get("faction1", {})
            faction2_data = teams_data.get("faction2", {})

            faction1_id = faction1_data.get("faction_id")
            faction2_id = faction2_data.get("faction_id")

            # Look up teams by Faceit ID in participant table
            team1_faction = None
            team2_faction = None

            try:
                # Find which faction corresponds to team1
                team1_participant = Participant.objects.get(
                    team=match.team1,
                    competition=match.competition,
                    season=match.season,
                    faceit_id__isnull=False,
                )
                if team1_participant.faceit_id == faction1_id:
                    team1_faction = "faction1"
                    team2_faction = "faction2"
                elif team1_participant.faceit_id == faction2_id:
                    team1_faction = "faction2"
                    team2_faction = "faction1"
            except Participant.DoesNotExist:
                logger.warning(
                    f"Could not find participant for team1 {match.team1.name} in match {match.id}"
                )

            # Double-check with team2 if we haven't found a mapping yet
            if not team1_faction:
                try:
                    team2_participant = Participant.objects.get(
                        team=match.team2,
                        competition=match.competition,
                        season=match.season,
                        faceit_id__isnull=False,
                    )
                    if team2_participant.faceit_id == faction1_id:
                        team2_faction = "faction1"
                        team1_faction = "faction2"
                    elif team2_participant.faceit_id == faction2_id:
                        team2_faction = "faction2"
                        team1_faction = "faction1"
                except Participant.DoesNotExist:
                    logger.warning(
                        f"Could not find participant for team2 {match.team2.name} in match {match.id}"
                    )

            if team1_faction and team2_faction:
                logger.info(
                    f"Match {match.id}: {match.team1.name} -> {team1_faction}, {match.team2.name} -> {team2_faction}"
                )

                # Get scores
                scores = results.get("score", {})
                new_score_team1 = scores.get(team1_faction, 0)
                new_score_team2 = scores.get(team2_faction, 0)

                # Update scores if they changed
                if new_score_team1 != match.score_team1:
                    match.score_team1 = new_score_team1
                    updated = True
                if new_score_team2 != match.score_team2:
                    match.score_team2 = new_score_team2
                    updated = True

                # Determine winner
                winner_faction = results.get("winner")
                new_winner = None
                if winner_faction == team1_faction:
                    new_winner = match.team1
                elif winner_faction == team2_faction:
                    new_winner = match.team2

                if new_status == "completed":
                    if new_winner is None:
                        raise PlatformSyncError(
                            f"Finished on Faceit, but its winner {winner_faction!r} isn't either of our teams"
                        )
                    if new_winner != match.winner:
                        match.winner = new_winner
                        updated = True
            elif new_status == "completed":
                # Saving it completed without a result would stick: completed
                # matches aren't refreshed again
                raise PlatformSyncError(
                    f"Finished on Faceit, but its teams don't match ours "
                    f"({match.team1.name}, {match.team2.name}; factions {faction1_id}, {faction2_id})"
                )
            else:
                logger.warning(
                    f"Could not map factions to teams for match {match.id}. Team1: {match.team1.name}, Team2: {match.team2.name}, Faction1: {faction1_id}, Faction2: {faction2_id}"
                )
        elif new_status == "completed":
            raise PlatformSyncError("Finished on Faceit, but it has no results yet")

    if updated:
        # Saves and reverts/applies Elo if the outcome changed
        save_synced_match(match, "Faceit")

    return updated



def update_leaguespot_match(match):
    """
    Update a single LeagueSpot match with fresh data from the API
    Returns True if the match was updated, False if no changes
    """

    # Extract match ID from LeagueSpot URL or use the stored match ID
    leaguespot_match_id = match.id

    # First, get the match data to check status and timing
    headers = get_leaguespot_headers()
    match_response = requests.get(
        f"https://api.leaguespot.gg/api/v2/matches/{leaguespot_match_id}",
        headers=headers,
        timeout=30,
    )

    if match_response.status_code != 200:
        raise PlatformSyncError(
            f"LeagueSpot API returned {match_response.status_code} for match {leaguespot_match_id}"
        )

    match_data = match_response.json()
    updated = apply_platform_status(
        match, "leaguespot", match_data.get("currentState")
    )

    # Update date/time
    scheduled_time = match_data.get("scheduled_at") or match_data.get(
        "startTimeUTC"
    )
    if scheduled_time:
        parsed_date = safe_parse_datetime(scheduled_time)
        if parsed_date and parsed_date != match.date:
            match.date = parsed_date
            updated = True

    if match.status != "completed":
        # LeagueSpot has no live scores, so only status and time can change
        if updated:
            save_synced_match(match, "LeagueSpot")
        return updated

    # Get participants data to check scores and winner
    participants_response = requests.get(
        f"https://api.leaguespot.gg/api/v1/matches/{leaguespot_match_id}/participants",
        headers=headers,
        timeout=30,
    )

    # It's completed on LeagueSpot: any problem getting the result fails the
    # sync rather than saving it completed without one, which would stick
    # (completed matches aren't refreshed again)
    if participants_response.status_code != 200:
        raise PlatformSyncError(
            f"LeagueSpot participants API returned {participants_response.status_code} for match {leaguespot_match_id}"
        )

    participants_data = participants_response.json()
    if len(participants_data) < 2:
        raise PlatformSyncError(
            f"Finished on LeagueSpot, but it lists {len(participants_data)} participant(s)"
        )

    # Extract scores and winner from participants
    team1_score = None
    team2_score = None
    winner_team_id = None

    # Find the participant that matches each team using the Participant model
    for participant in participants_data:
        participant_team_id = participant.get("teamId")
        participant_id = participant.get("participantId")
        participant_score = participant.get("score", 0)
        is_winner = participant.get("isWinner", False)

        # Try to find our team through the Participant model
        try:
            # First try by playfly_participant_id
            db_participant = Participant.objects.get(
                playfly_participant_id=participant_id,
                competition=match.competition,
                season=match.season,
            )
            team = db_participant.team
        except Participant.DoesNotExist:
            # If not found by participant ID, try by playfly_id (team ID)
            try:
                db_participant = Participant.objects.get(
                    playfly_id=participant_team_id,
                    competition=match.competition,
                    season=match.season,
                )
                team = db_participant.team
            except Participant.DoesNotExist:
                # Can't find this team; checked below
                logger.warning(
                    f"Could not find team for LeagueSpot participant {participant_id} or team {participant_team_id}"
                )
                continue

        # Check which team this matches
        if team and team.id == match.team1.id:
            team1_score = int(participant_score)
            if is_winner:
                winner_team_id = match.team1.id
        elif team and team.id == match.team2.id:
            team2_score = int(participant_score)
            if is_winner:
                winner_team_id = match.team2.id

    if team1_score is None or team2_score is None:
        raise PlatformSyncError(
            f"Finished on LeagueSpot, but its participants don't match our teams "
            f"({match.team1.name}, {match.team2.name})"
        )

    # Update scores if they changed
    if team1_score != match.score_team1:
        match.score_team1 = team1_score
        updated = True

    if team2_score != match.score_team2:
        match.score_team2 = team2_score
        updated = True

    # Update winner
    new_winner = None
    if winner_team_id:
        if winner_team_id == match.team1.id:
            new_winner = match.team1
        elif winner_team_id == match.team2.id:
            new_winner = match.team2

    if new_winner != match.winner:
        match.winner = new_winner
        updated = True

    if updated:
        # Saves and reverts/applies Elo if the outcome changed
        save_synced_match(match, "LeagueSpot")

    return updated

