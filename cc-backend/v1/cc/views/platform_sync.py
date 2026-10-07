"""Refreshing existing matches from Faceit, LeagueSpot and Regents League."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status
from datetime import timedelta
from django.utils import timezone
from django.db import models
from ..models import (
    Match,
    Participant,
)
from ..middleware import firebase_auth_required

import logging
import requests

from .elo import update_match_elos
from .proxies import get_leaguespot_headers
from .utils import safe_parse_datetime

logger = logging.getLogger(__name__)


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def update_matches(request):
    """
    Update existing matches with fresh data from external APIs.
    This will fetch updated information for rescheduled times and match results.

    Expected request format:
    {
        "match_ids": ["uuid1", "uuid2", ...], // Optional - specific matches to update
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

        # Include matches that:
        # 1. Have no date (null dates)
        # 2. Are in the past or within the next week
        # 3. Are currently in progress (regardless of date)
        query = query.filter(
            models.Q(date__isnull=True)  # Matches with no date
            | models.Q(date__lte=one_week_from_now)  # Past matches or within next week
            | models.Q(status="in_progress")  # Currently in progress matches
        )

        matches = query
        updated_count = 0
        error_count = 0
        results = []

        for match in matches:
            try:
                updated = False

                if match.platform == "faceit":
                    updated = update_faceit_match(match)
                elif match.platform == "leaguespot":
                    updated = update_leaguespot_match(match)
                elif match.platform == "regentsleague":
                    updated = update_regentsleague_match(match)
                else:
                    logger.warning(
                        f"Unsupported platform for match {match.id}: {match.platform}"
                    )
                    continue

                if updated:
                    updated_count += 1
                    results.append(
                        {
                            "match_id": str(match.id),
                            "status": "updated",
                            "new_status": match.status,
                            "new_date": match.date.isoformat() if match.date else None,
                        }
                    )
                else:
                    results.append({"match_id": str(match.id), "status": "no_changes"})

            except Exception as e:
                error_count += 1
                logger.error(f"Error updating match {match.id}: {str(e)}")
                results.append(
                    {"match_id": str(match.id), "status": "error", "error": str(e)}
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
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def update_regentsleague_match(match: Match):
    """
    Update a single Regents League match with fresh data from the API
    Returns True if the match was updated, False if no changes
    """
    try:
        regentsleague_match_id = match.regentsleague_id
        response = requests.get(
            f"https://regent-league-api.poopdealer.lol/cc/match?id={regentsleague_match_id}",
            timeout=30,
        )

        if response.status_code != 200:
            logger.warning(
                f"Regent League API returned {response.status_code} for match {regentsleague_match_id}"
            )
            return False

        match_data: dict = response.json()
        # Check if any updates are needed
        updated = False

        # Update status
        status_mapping = {
            "Completed": "completed",
            "In Progress": "in_progress",
            "Scheduled": "scheduled",
        }
        new_status = status_mapping.get(match_data.get("status"), "scheduled")
        if new_status != match.status:
            match.status = new_status
            updated = True

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
        if updated:
            match.save()
            logger.info(f"Updated Regent League match {match.id}")

            # Update team ELOs if the match is now completed
            if match.status == "completed":
                update_match_elos(match)

        return updated

    except Exception as e:
        logger.error(f"Error updating Regents League match {match.id}: {str(e)}")
        raise


def update_faceit_match(match):
    """
    Update a single Faceit match with fresh data from the API
    Returns True if the match was updated, False if no changes
    """
    if not match.url:
        return False

    try:
        # Extract match ID from Faceit URL
        # URLs are typically like: https://www.faceit.com/en/csgo/room/1-abc123-def456...
        faceit_match_id = match.id

        # Fetch match data from Faceit API
        api_key = getattr(settings, "FACEIT_API_KEY", None)
        if not api_key:
            logger.error("FACEIT_API_KEY not configured")
            return False

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            f"https://open.faceit.com/data/v4/matches/1-{faceit_match_id}",
            headers=headers,
            timeout=30,
        )

        if response.status_code != 200:
            logger.warning(
                f"Faceit API returned {response.status_code} for match {faceit_match_id}"
            )
            return False

        match_data = response.json()

        # Check if any updates are needed
        updated = False

        # Update status
        status_mapping = {
            "FINISHED": "completed",
            "ONGOING": "in_progress",
            "CANCELLED": "cancelled",
            "READY": "scheduled",
        }
        new_status = status_mapping.get(match_data.get("status"), "scheduled")
        if new_status != match.status:
            match.status = new_status
            updated = True

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

        # Update results if match is finished
        if new_status == "completed":
            results = match_data.get("results", {})
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

                    if new_winner != match.winner:
                        match.winner = new_winner
                        updated = True
                else:
                    logger.warning(
                        f"Could not map factions to teams for match {match.id}. Team1: {match.team1.name}, Team2: {match.team2.name}, Faction1: {faction1_id}, Faction2: {faction2_id}"
                    )

        if updated:
            match.save()
            logger.info(f"Updated Faceit match {match.id}")

            # Update team ELOs if the match is now completed
            if match.status == "completed":
                update_match_elos(match)

        return updated

    except Exception as e:
        logger.error(f"Error updating Faceit match {match.id}: {str(e)}")
        raise


def update_leaguespot_match(match):
    """
    Update a single LeagueSpot match with fresh data from the API
    Returns True if the match was updated, False if no changes
    """

    try:
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
            print(
                f"LeagueSpot API returned {match_response.status_code} for match {leaguespot_match_id}"
            )
            return False

        match_data = match_response.json()

        # Check if any updates are needed
        updated = False

        # Update status based on LeagueSpot status
        status_mapping = {
            3: "completed",
            2: "in_progress",
            1: "scheduled",
            0: "scheduled",
        }
        api_status = match_data.get("currentState", 0)
        new_status = (
            status_mapping[api_status] if api_status in status_mapping else "scheduled"
        )
        print(f"LeagueSpot match {match.id} status from {match.status} to {new_status}")
        if new_status != match.status:
            match.status = new_status
            updated = True

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
            # If match is not completed, no need to update scores/winner
            match.save()
            print(f"Updated scheduled LeagueSpot match {match.id}")
            return updated

        print(f"Fetching participants for completed LeagueSpot match {match.id}")
        # Get participants data to check scores and winner
        participants_response = requests.get(
            f"https://api.leaguespot.gg/api/v1/matches/{leaguespot_match_id}/participants",
            headers=headers,
            timeout=30,
        )

        if participants_response.status_code == 200:
            participants_data = participants_response.json()

            if len(participants_data) >= 2:
                # Extract scores and winner from participants
                team1_score = 0
                team2_score = 0
                winner_team_id = None
                participant_score = 0

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
                            # Can't find this team, skip
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

        else:
            logger.warning(
                f"LeagueSpot participants API returned {participants_response.status_code} for match {leaguespot_match_id}"
            )

        if updated:
            match.save()
            logger.info(f"Updated LeagueSpot match {match.id}")

            # Update team ELOs if the match is now completed
            if match.status == "completed":
                update_match_elos(match)

        return updated

    except Exception as e:
        logger.error(f"Error updating LeagueSpot match {match.id}: {str(e)}")
        raise
