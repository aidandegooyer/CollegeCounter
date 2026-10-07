"""Importing matches and teams from external platforms."""

import uuid
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status
from django.db import models
from ..models import (
    Team,
    Player,
    Match,
    Season,
    Participant,
    Competition,
    Event,
    EventMatch,
)
from ..middleware import firebase_auth_required

import logging
import requests

from .utils import safe_parse_datetime

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["POST"])
@firebase_auth_required(min_role="owner")
def import_matches(request):
    """
    Import matches from an external API (Faceit or Playfly or Regents League) into the database.
    Expected request format:
    {
        "platform": "faceit" | "leaguespot" | "regentsleague",
        "competition_name": "string",
        "season_id": "uuid",
        "data": {...}, // API response data
        "participant_matches": { "participant_id": "team_id", ... }, // Optional
        "event_id": "uuid", // Optional - if provided, imports as event matches
        "import_type": "league" | "event" // Optional - specifies import type
    }
    """
    try:
        data = request.data
        platform = data.get("platform", "").lower()
        competition_name = data.get("competition_name", "")
        season_id = data.get("season_id")
        api_data = data.get("data", {})
        participant_matches = data.get("participant_matches", {})
        event_id = data.get("event_id")
        import_type = data.get("import_type", "league")

        # Create a new competition (do not merge with existing ones with the same name)
        competition = Competition.objects.create(name=competition_name)

        # Get the season
        try:
            season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            return Response(
                {"error": "Season not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get the event if event_id is provided
        event = None
        if event_id:
            try:
                event = Event.objects.get(id=event_id)
            except Event.DoesNotExist:
                return Response(
                    {"error": "Event not found"}, status=status.HTTP_400_BAD_REQUEST
                )

        # Apply participant matches if provided
        if participant_matches:
            for participant_id, team_id in participant_matches.items():
                try:
                    # Check if this is a placeholder ID for a team match
                    if participant_id.startswith("platform:"):
                        # Format is "platform:{platform}:team:{team_name}"
                        parts = participant_id.split(":")
                        if len(parts) >= 4:
                            platform_name = parts[1]
                            team_name = ":".join(
                                parts[3:]
                            )  # Join in case team name has colons

                            # Find or create participant for this team
                            team = Team.objects.get(id=team_id)

                            # Create a participant record to link team to competition and season
                            participant, created = Participant.objects.get_or_create(
                                team=team,
                                competition=competition,
                                season=season,
                                defaults={
                                    "faceit_id": team_name
                                    if platform_name == "faceit"
                                    else None,
                                    "playfly_id": team_name
                                    if platform_name == "leaguespot"
                                    else None,
                                },
                            )
                    else:
                        # Regular participant ID
                        participant = Participant.objects.get(id=participant_id)
                        team = Team.objects.get(id=team_id)
                        participant.team = team
                        participant.save()
                except (Participant.DoesNotExist, Team.DoesNotExist) as e:
                    # Log this but don't fail the import
                    print(f"Error applying participant match: {e}")

        # Process matches based on platform and import type
        if platform == "faceit":
            result = import_match_data(
                api_data,
                competition,
                season,
                platform,
                event=event,
                import_type=import_type,
            )
        elif platform == "leaguespot":
            result = import_match_data(
                api_data,
                competition,
                season,
                platform,
                event=event,
                import_type=import_type,
            )
        elif platform == "regentsleague":
            result = import_regentsleague_match_data(api_data, competition, season)
        else:
            return Response(
                {"error": "Unsupported platform"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Build response message
        total_new = len(result["imported"])
        total_updated = len(result["updated"])
        total_skipped = len(result["skipped"])

        message_parts = []
        if total_new > 0:
            message_parts.append(f"{total_new} new match(es)")
        if total_updated > 0:
            message_parts.append(f"{total_updated} updated")
        if total_skipped > 0:
            message_parts.append(f"{total_skipped} unchanged")

        if not message_parts:
            message = "No matches to import"
        else:
            message = f"Import successful: {', '.join(message_parts)}"

        return Response(
            {
                "message": message,
                "matches_imported": total_new,
                "matches_updated": total_updated,
                "matches_skipped": total_skipped,
                "new_match_ids": result["imported"],
                "updated_match_ids": result["updated"],
                "skipped_match_ids": result["skipped"],
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def import_regentsleague_match_data(matches: list[dict], competition, season):
    """
    Process Regents League API data and import matches

    Args:
        matches: The API response data containing match information
        season: Season object

    Returns:
        dict: Contains lists of imported_matches, updated_matches, and skipped_matches
    """
    imported_matches = []
    updated_matches = []
    skipped_matches = []

    for match_data in matches:
        regentsleague_match_id = match_data.get("id")
        match_id = uuid.uuid5(
            uuid.NAMESPACE_DNS, f"regentsleague-{regentsleague_match_id}"
        )  # Create a UUID based on the Regents League match ID. In the miniscule offchance this conflicts with an existing ID from a different league out of pure unluckiness I'll do a backflip.
        team1_data: dict = match_data.get("team1")
        team2_data: dict = match_data.get("team2")
        team1_key = team1_data.get("id")
        team2_key = team2_data.get("id")
        team1, _ = get_or_create_team(team1_data, competition, season, "regentsleague")
        team2, _ = get_or_create_team(team2_data, competition, season, "regentsleague")

        if not team1 or not team2:
            continue  # Skip if teams could not be created

        # Extract results if available
        score_team1 = 0
        score_team2 = 0
        winner = None

        status_mapping = {
            "Completed": "completed",
            "In Progress": "in_progress",
            "Scheduled": "scheduled",
            # Add other status mappings as needed
        }
        match_status = status_mapping.get(match_data.get("status"), "scheduled")

        if match_status == "completed":
            score_team1 = match_data.get("score_team1")
            score_team2 = match_data.get("score_team2")

            # The API omits "winner" (or sends null) for some completed matches
            winner_key = (match_data.get("winner") or {}).get("id")
            if winner_key == team1_key:
                winner = team1
            elif winner_key == team2_key:
                winner = team2

        # Check if match already exists
        existing_match = Match.objects.filter(id=match_id).first()

        if existing_match:
            # Skip updating existing matches - only import new matches
            # Updates should be done separately through the update_matches endpoint
            skipped_matches.append(str(existing_match.id))
            logger.info(
                f"Skipped existing match {match_id} - use update endpoint to modify"
            )
            continue  # Move to next match

        # Create the match (only if it doesn't exist)
        match_date = match_data.get("date")
        match = Match.objects.create(
            id=match_id,
            regentsleague_id=regentsleague_match_id,
            team1=team1,
            team2=team2,
            date=safe_parse_datetime(match_date) if match_date else None,
            status=match_status,
            winner=winner,
            score_team1=score_team1,
            score_team2=score_team2,
            platform="regentsleague",
            season=season,
            competition=competition,
        )
        imported_matches.append(str(match.id))

    return {
        "imported": imported_matches,
        "updated": updated_matches,
        "skipped": skipped_matches,
    }


def import_match_data(
    api_data, competition, season, platform, event=None, import_type="league"
):
    """
    Process Faceit/LeagueSpot API data and import matches

    Args:
        api_data: The API response data containing match information
        competition: Competition object
        season: Season object
        platform: Platform name (faceit or leaguespot)
        event: Optional Event object - if provided, creates EventMatch entries
        import_type: Type of import ("league" or "event")

    Returns:
        dict: Contains lists of imported_matches, updated_matches, and skipped_matches
    """
    imported_matches = []
    updated_matches = []
    skipped_matches = []

    # Extract matches from the API response
    matches = api_data.get("items", [])

    for match_data in matches:
        # Extract match details
        match_id = match_data.get("match_id")
        faceit_url = match_data.get("faceit_url")
        status_value = match_data.get("status")

        # Remove "1-" prefix from match_id if present
        if match_id and str(match_id).startswith("1-"):
            match_id = str(match_id)[2:]

        # Convert Faceit status to our status format
        status_mapping = {
            "FINISHED": "completed",
            "ONGOING": "in_progress",
            "CANCELLED": "cancelled",
            "READY": "scheduled",
            # Add other status mappings as needed
        }
        match_status = status_mapping.get(status_value, "scheduled")

        # Parse scheduled/started/finished times
        scheduled_at = match_data.get("scheduled_at")
        started_at = match_data.get("started_at")
        finished_at = match_data.get("finished_at")

        # Use the most appropriate timestamp for match date
        if finished_at:
            match_date = finished_at
        elif started_at:
            match_date = started_at
        elif scheduled_at:
            match_date = scheduled_at
        else:
            match_date = None

        # Process teams data
        teams_data = match_data.get("teams", {})
        team_keys = list(teams_data.keys())

        if len(team_keys) < 2:
            continue  # Skip if not enough teams

        team1_key = team_keys[0]
        team2_key = team_keys[1]

        team1_data = teams_data.get(team1_key, {})
        team2_data = teams_data.get(team2_key, {})

        # Get or create teams
        team1, _ = get_or_create_team(team1_data, competition, season, platform)
        team2, _ = get_or_create_team(team2_data, competition, season, platform)

        if not team1 or not team2:
            continue  # Skip if teams could not be created

        # Extract results if available
        score_team1 = 0
        score_team2 = 0
        winner = None

        results = match_data.get("results", {})
        if results:
            scores = results.get("score", {})
            score_team1 = scores.get(team1_key, 0)
            score_team2 = scores.get(team2_key, 0)

            winner_key = results.get("winner")
            if winner_key == team1_key:
                winner = team1
            elif winner_key == team2_key:
                winner = team2

        # Check if match already exists
        existing_match = Match.objects.filter(id=match_id).first()

        if existing_match:
            # Skip updating existing matches - only import new matches
            # Updates should be done separately through the update_matches endpoint
            skipped_matches.append(str(existing_match.id))
            logger.info(
                f"Skipped existing match {match_id} - use update endpoint to modify"
            )

            # For event imports, check if EventMatch exists and create link if needed
            if event and import_type == "event":
                event_match = EventMatch.objects.filter(
                    match=existing_match, event=event
                ).first()

                if not event_match:
                    # Match exists but not linked to this event - create EventMatch
                    # Extract event-specific data from match_data
                    event_metadata = match_data.get("_event_match_metadata", {})

                    if event_metadata and platform == "leaguespot":
                        # Use LeagueSpot round metadata
                        round_num = event_metadata.get("round", 1)
                        num_in_bracket = event_metadata.get(
                            "num_in_bracket", len(imported_matches) + 1
                        )

                        extra_info = {
                            "leaguespot_match_id": match_id,
                            "original_status": status_value,
                            "round_name": event_metadata.get("round_name", ""),
                            "round_state": event_metadata.get("round_state", 0),
                            "best_of": event_metadata.get("best_of", 1),
                        }
                    else:
                        # Faceit or legacy format
                        round_num = match_data.get("round", 1)
                        num_in_bracket = match_data.get(
                            "position", len(imported_matches) + 1
                        )

                        extra_info = {
                            "faceit_match_id": match_id,
                            "faceit_url": faceit_url,
                            "original_status": status_value,
                        }

                        if "round" in match_data:
                            extra_info["round_name"] = match_data.get("round")
                        if "group" in match_data:
                            extra_info["group"] = match_data.get("group")

                    # Check for bye matches
                    is_bye = False
                    team1_name = team1_data.get("name", "").lower()
                    team2_name = team2_data.get("name", "").lower()
                    if team1_name in ["bye", "tbd", "unknown team 1"] or team2_name in [
                        "bye",
                        "tbd",
                        "unknown team 2",
                    ]:
                        is_bye = True

                    EventMatch.objects.create(
                        match=existing_match,
                        event=event,
                        round=round_num,
                        num_in_bracket=num_in_bracket,
                        is_bye=is_bye,
                        extra_info=extra_info,
                    )
                    logger.info(f"Linked existing match {match_id} to event {event.id}")

            continue  # Move to next match

        # Create the match (only if it doesn't exist)
        match = Match.objects.create(
            id=match_id,
            team1=team1,
            team2=team2,
            date=safe_parse_datetime(match_date) if match_date else None,
            status=match_status,
            url=faceit_url,
            winner=winner,
            score_team1=score_team1,
            score_team2=score_team2,
            platform=platform,
            season=season,
            competition=competition,
        )

        # If this is an event import, create an EventMatch entry
        if event and import_type == "event":
            # Extract event-specific data from match_data
            # Check for LeagueSpot event metadata first, then fall back to Faceit
            event_metadata = match_data.get("_event_match_metadata", {})

            if event_metadata and platform == "leaguespot":
                # Use LeagueSpot round metadata
                round_num = event_metadata.get("round", 1)
                num_in_bracket = event_metadata.get(
                    "num_in_bracket", len(imported_matches) + 1
                )

                # Extra info contains LeagueSpot round metadata
                extra_info = {
                    "leaguespot_match_id": match_id,
                    "original_status": status_value,
                    "round_name": event_metadata.get("round_name", ""),
                    "round_state": event_metadata.get("round_state", 0),
                    "best_of": event_metadata.get("best_of", 1),
                }
            else:
                # Faceit or legacy format
                round_num = match_data.get(
                    "round", 1
                )  # Default to round 1 if not provided
                num_in_bracket = match_data.get("position", len(imported_matches) + 1)

                # Extra info can contain bracket-specific data
                extra_info = {
                    "faceit_match_id": match_id,
                    "faceit_url": faceit_url,
                    "original_status": status_value,
                }

                # Add any additional bracket metadata from Faceit
                if "round" in match_data:
                    extra_info["round_name"] = match_data.get("round")
                if "group" in match_data:
                    extra_info["group"] = match_data.get("group")

            # Check for bye matches (TBD or Bye team names)
            is_bye = False
            team1_name = team1_data.get("name", "").lower()
            team2_name = team2_data.get("name", "").lower()
            if team1_name in ["bye", "tbd", "unknown team 1"] or team2_name in [
                "bye",
                "tbd",
                "unknown team 2",
            ]:
                is_bye = True

            # Create EventMatch
            EventMatch.objects.create(
                match=match,
                event=event,
                round=round_num,
                num_in_bracket=num_in_bracket,
                is_bye=is_bye,
                extra_info=extra_info,
            )

        imported_matches.append(str(match.id))

    return {
        "imported": imported_matches,
        "updated": updated_matches,
        "skipped": skipped_matches,
    }


def get_or_create_team(team_data, competition, season, platform):
    """
    Helper function to get or create a team from API data
    """
    team_name = team_data.get("name", "Unknown Team")
    team_avatar = team_data.get("avatar")
    team_faceit_id = team_data.get("faction_id")
    team_regentsleague_id = None
    if platform == "regentsleague":
        team_avatar = team_data.get("picture")
        team_regentsleague_id = team_data.get("id")

    # Only process LeagueSpot/Playfly IDs if we're actually importing from those platforms
    team_playfly_id = None
    participant_id = None

    # Check if this is LeagueSpot/Playfly data (not Faceit)
    if platform == "leaguespot":
        team_playfly_id = team_data.get("faction_id") or team_data.get("teamId")
        participant_id = team_data.get("participantId")

    # First, check if there's an existing participant for this team ID in this competition/season
    existing_participant = None

    # Try Faceit ID first
    if team_faceit_id:
        try:
            existing_participant = (
                Participant.objects.filter(competition=competition, season=season)
                .filter(
                    models.Q(faceit_id=team_faceit_id)
                    | models.Q(faceit_id=team_playfly_id)
                )
                .first()
            )
        except Participant.DoesNotExist:
            pass

    # Try Playfly team ID if Faceit lookup failed
    if not existing_participant and team_playfly_id:
        try:
            existing_participant = Participant.objects.get(
                playfly_id=team_playfly_id, competition=competition, season=season
            )
        except Participant.DoesNotExist:
            pass

    # Try Playfly participant ID if team ID lookup failed
    if not existing_participant and participant_id:
        try:
            existing_participant = Participant.objects.get(
                playfly_participant_id=participant_id,
                competition=competition,
                season=season,
            )
        except Participant.DoesNotExist:
            pass

    # Try Regents League ID if team Faceit and Playfly failed
    if not existing_participant and team_regentsleague_id:
        try:
            existing_participant = Participant.objects.get(
                regentsleague_id=team_regentsleague_id,
                competition=competition,
                season=season,
            )
        except Participant.DoesNotExist:
            pass

    # If we found a participant with a team, use that team
    if existing_participant and existing_participant.team:
        team = existing_participant.team
        return team, False

    # If no existing participant found, try to find an existing team by name
    try:
        team = Team.objects.get(name=team_name)
    except Team.DoesNotExist:
        # Create new team
        team = Team.objects.create(name=team_name, picture=team_avatar)

    # Create participant record to link team to competition and season
    participant_defaults = {}

    # Set the appropriate platform ID based on what's available
    if team_faceit_id:
        participant_defaults["faceit_id"] = team_faceit_id
    if team_playfly_id:
        participant_defaults["playfly_id"] = team_playfly_id
    if participant_id:
        participant_defaults["playfly_participant_id"] = participant_id
    if team_regentsleague_id:
        participant_defaults["regentsleague_id"] = team_regentsleague_id

    participant, created = Participant.objects.get_or_create(
        team=team, competition=competition, season=season, defaults=participant_defaults
    )

    # If participant already existed but was missing some IDs, update them
    if not created:
        updated = False
        if team_faceit_id and not participant.faceit_id:
            participant.faceit_id = team_faceit_id
            updated = True
        if team_playfly_id and not participant.playfly_id:
            participant.playfly_id = team_playfly_id
            updated = True
        if participant_id and not participant.playfly_participant_id:
            participant.playfly_participant_id = participant_id
            updated = True
        if team_regentsleague_id and not participant.regentsleague_id:
            participant.regentsleague_id = team_regentsleague_id
            updated = True

        if updated:
            participant.save()

    # Process players if needed
    roster = team_data.get("roster", [])
    for player_data in roster:
        process_player(player_data, team, season)

    return team, created


def process_player(player_data, team, season):
    """
    Process player data and associate with team.
    Handles player transfers between teams and avoids unique constraint violations.
    """
    player_id = player_data.get("player_id")
    game_player_id = player_data.get("game_player_id") or player_data.get("steam_id")
    nickname = player_data.get("nickname", "Unknown Player")
    avatar = player_data.get("avatar")

    if game_player_id == "":
        game_player_id = None

    elo = 1000

    # Try to fetch updated player data from Faceit API if we have a game_player_id
    try:
        print(f"Processing player {nickname} with game_player_id {game_player_id}")
        # If we have a game_player_id (steam_id), fetch Faceit player ID from Faceit API
        if game_player_id:
            faceit_api_url = "https://open.faceit.com/data/v4/players"
            api_key = getattr(settings, "FACEIT_API_KEY", None)
            if api_key:
                headers = {"Authorization": f"Bearer {api_key}"}
                params = {"game": "cs2", "game_player_id": game_player_id}
                response = requests.get(faceit_api_url, headers=headers, params=params)
                if response.status_code == 200:
                    faceit_data = response.json()
                    player_id = faceit_data.get("player_id", player_id)
                    nickname = faceit_data.get("nickname", nickname)
                    avatar = faceit_data.get("avatar", avatar)
                    elo = (
                        faceit_data.get("games", {})
                        .get("cs2", {})
                        .get("faceit_elo", 1000)
                    )
                    print(f"Fetched Faceit ID {player_id} for player {nickname}")
                    print(f"Player ELO is {elo}")
                else:
                    print(
                        f"Failed to fetch Faceit player for game_player_id {game_player_id}: {response.status_code}"
                    )
    except Exception as e:
        logger.warning(f"Could not fetch Faceit player ID for {nickname}: {str(e)}")

    # Try to find existing player by multiple criteria
    player = None

    # Priority 1: Find by steam_id if available
    if game_player_id:
        try:
            player = Player.objects.get(steam_id=game_player_id)
            print(
                f"Found existing player by steam_id: {player.name} -> moving to {team.name}"
            )
        except Player.DoesNotExist:
            pass

    # Priority 2: Find by faceit_id if not found by steam_id
    if not player and player_id:
        try:
            player = Player.objects.get(faceit_id=player_id)
            print(
                f"Found existing player by faceit_id: {player.name} -> moving to {team.name}"
            )
        except Player.DoesNotExist:
            pass

    # Priority 3: Find by name if no unique identifiers found a match
    if not player and nickname and nickname != "Unknown Player":
        try:
            # Look for player with same name (case insensitive)
            player = Player.objects.get(name__iexact=nickname)
            print(
                f"Found existing player by name: {player.name} -> moving to {team.name}"
            )
        except Player.DoesNotExist:
            pass
        except Player.MultipleObjectsReturned:
            # If multiple players with same name, don't risk picking the wrong one
            print(f"Multiple players found with name {nickname}, creating new player")
            pass

    if player:
        # Update existing player with new information and move to new team
        old_team_name = player.team.name if player.team else "No team"

        # Update player information (but preserve manually set name and picture)
        # Don't update name or picture as they may have been set manually
        if player_id and not player.faceit_id:
            player.faceit_id = player_id
        if game_player_id and not player.steam_id:
            player.steam_id = game_player_id
        player.elo = elo
        player.team = team  # Move to new team
        player.benched = False
        player.seasons.add(season)

        player.save()

        print(f"Updated player {nickname}: {old_team_name} -> {team.name}")
        return player

    # If no existing player found, create a new one
    try:
        player = Player.objects.create(
            name=nickname,
            picture=avatar,
            faceit_id=player_id,
            team=team,
            elo=elo,
            steam_id=game_player_id,
        )
        player.seasons.set([season])
        print(f"Created new player: {nickname} for team {team.name}")
        return player
    except Exception as e:
        # If creation fails due to unique constraint, try one more time to find existing player
        logger.error(f"Failed to create player {nickname}: {str(e)}")

        # Last resort: try to find by any available identifier
        if player_id:
            try:
                player = Player.objects.get(faceit_id=player_id)
                print(f"Found existing player on retry by faceit_id: {player.name}")
                # Update and move to new team (but preserve manually set name and picture)
                # Don't update name or picture as they may have been set manually
                if game_player_id and not player.steam_id:
                    player.steam_id = game_player_id
                player.elo = elo
                player.team = team
                player.benched = False
                player.seasons.add(season)
                player.save()
                return player
            except Player.DoesNotExist:
                pass

        # If still failing, raise the original error
        raise e


@api_view(["GET", "POST"])
@firebase_auth_required(min_role="owner")
def match_participants(request):
    """
    Match participants between competitions/seasons and teams.

    GET: Get all unmatched participants and available teams
    POST: Create or update participant matches
    """
    if request.method == "GET":
        # Get all participants
        participants = Participant.objects.all()

        # Get teams
        teams = Team.objects.all()

        result = {"participants": [], "teams": []}

        # Format participants data
        for participant in participants:
            result["participants"].append(
                {
                    "id": participant.id,
                    "team_id": participant.team.id if participant.team else None,
                    "team_name": participant.team.name if participant.team else None,
                    "competition_id": participant.competition.id
                    if participant.competition
                    else None,
                    "competition_name": participant.competition.name
                    if participant.competition
                    else None,
                    "season_id": participant.season.id if participant.season else None,
                    "season_name": participant.season.name
                    if participant.season
                    else None,
                    "faceit_id": participant.faceit_id,
                    "playfly_id": participant.playfly_id,
                    "playfly_participant_id": participant.playfly_participant_id,
                }
            )

        # Format teams data
        for team in teams:
            result["teams"].append(
                {
                    "id": team.id,
                    "name": team.name,
                    "picture": team.picture,
                    "school_name": team.school_name,
                }
            )

        return Response(result)

    elif request.method == "POST":
        try:
            participant_id = request.data.get("participant_id")
            team_id = request.data.get("team_id")

            if not participant_id or not team_id:
                return Response(
                    {"error": "Missing participant_id or team_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the participant and team
            try:
                participant = Participant.objects.get(id=participant_id)
            except Participant.DoesNotExist:
                return Response(
                    {"error": f"Participant with ID {participant_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return Response(
                    {"error": f"Team with ID {team_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Update the participant
            participant.team = team
            participant.save()

            return Response(
                {
                    "message": "Participant matched successfully",
                    "participant": {
                        "id": participant.id,
                        "team_id": team.id,
                        "team_name": team.name,
                        "competition_id": participant.competition.id
                        if participant.competition
                        else None,
                        "competition_name": participant.competition.name
                        if participant.competition
                        else None,
                        "season_id": participant.season.id
                        if participant.season
                        else None,
                        "season_name": participant.season.name
                        if participant.season
                        else None,
                    },
                }
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
