from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status
from datetime import datetime
from datetime import timedelta
from django.utils import timezone
from django.db import models
from .models import (
    Team,
    Player,
    Match,
    Season,
    Participant,
    Competition,
    Event,
    EventMatch,
    Ranking,
    RankingItem,
)
from .middleware import firebase_auth_required

import logging
import requests

logger = logging.getLogger(__name__)


def safe_parse_datetime(dt):
    """
    Parse a datetime from either a string (e.g. "2025-10-25T00:30:00Z")
    or a unix timestamp (int/float, seconds since epoch).
    Returns a timezone-aware datetime or None.
    """
    if isinstance(dt, str):
        # Try to parse ISO format with Z
        parsed = parse_datetime(dt)
        if parsed:
            return parsed
        # If parse_datetime fails, try to parse as unix timestamp string
        try:
            ts = float(dt)
            return datetime.fromtimestamp(ts)
        except ValueError:
            return None
    if isinstance(dt, (int, float)):
        return datetime.fromtimestamp(dt)
    return None


def calculate_new_elo(current_elo, opponent_elo, result):
    """
    Calculate new ELO rating after a match.

    Args:
        current_elo (int): Current ELO of the team
        opponent_elo (int): ELO of the opponent team
        result (float): Match result (1.0 for win, 0.0 for loss, 0.5 for draw)

    Returns:
        int: New ELO rating
    """
    k = 150  # K-factor, determines the maximum possible adjustment per game
    expected_score = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 800))
    new_elo = current_elo + k * (result - expected_score)
    return round(new_elo)


def update_match_elos(match):
    """
    Update team ELOs based on match result.
    Only updates if the match is completed and has a winner.

    Args:
        match (Match): The completed match to process

    Returns:
        bool: True if ELOs were updated, False otherwise
    """
    if match.status != "completed" or not match.winner:
        return False

    # Get current ELOs
    team1_elo = match.team1.elo
    team2_elo = match.team2.elo

    # Determine results (1.0 for win, 0.0 for loss)
    if match.winner == match.team1:
        team1_result = 1.0
        team2_result = 0.0
    elif match.winner == match.team2:
        team1_result = 0.0
        team2_result = 1.0
    else:
        return False

    # Calculate new ELOs
    new_team1_elo = calculate_new_elo(team1_elo, team2_elo, team1_result)
    new_team2_elo = calculate_new_elo(team2_elo, team1_elo, team2_result)

    # Update teams
    match.team1.elo = new_team1_elo
    match.team2.elo = new_team2_elo
    match.team1.save()
    match.team2.save()

    logger.info(
        f"Updated ELOs for match {match.id}: {match.team1.name} {team1_elo}→{new_team1_elo}, {match.team2.name} {team2_elo}→{new_team2_elo}"
    )

    return True


def recalculate_all_elos(reset_to_default=False, default_elo=1000):
    """
    Recalculate ELO ratings for all teams based on completed matches in chronological order.
    This is useful when importing historical match data.

    Args:
        reset_to_default (bool): Whether to reset all team ELOs to default before recalculating
        default_elo (int): Default ELO to reset teams to if reset_to_default is True

    Returns:
        dict: Summary of the recalculation process
    """
    # Reset all team ELOs to default if requested
    if reset_to_default:
        Team.objects.all().update(elo=default_elo)
        logger.info(f"Reset all team ELOs to {default_elo}")

    # Get all completed matches with winners, ordered by date
    completed_matches = (
        Match.objects.filter(status="completed", winner__isnull=False)
        .exclude(
            models.Q(team1__name__iexact="bye") | models.Q(team2__name__iexact="bye")
        )
        .order_by("date")
    )

    processed_count = 0
    error_count = 0
    elo_changes = []

    for match in completed_matches:
        try:
            # Store ELOs before update for logging
            old_team1_elo = match.team1.elo
            old_team2_elo = match.team2.elo

            # Update ELOs for this match
            if update_match_elos(match):
                processed_count += 1

                # Log the change
                elo_changes.append(
                    {
                        "match_id": str(match.id),
                        "date": match.date.isoformat() if match.date else None,
                        "team1": match.team1.name,
                        "team2": match.team2.name,
                        "winner": match.winner.name if match.winner else "Unknown",
                        "team1_elo_change": f"{old_team1_elo} → {match.team1.elo}",
                        "team2_elo_change": f"{old_team2_elo} → {match.team2.elo}",
                    }
                )

                logger.info(
                    f"Processed match {match.id}: {match.team1.name} vs {match.team2.name}, "
                    f"winner: {match.winner.name if match.winner else 'Unknown'}, "
                    f"ELO changes: {match.team1.name} {old_team1_elo}→{match.team1.elo}, "
                    f"{match.team2.name} {old_team2_elo}→{match.team2.elo}"
                )
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing match {match.id}: {str(e)}")

    return {
        "total_matches": completed_matches.count(),
        "processed_count": processed_count,
        "error_count": error_count,
        "reset_to_default": reset_to_default,
        "default_elo": default_elo if reset_to_default else None,
        "elo_changes": elo_changes,
    }


def index(request):
    return HttpResponse("Hello! This is the College Counter backend API.")


@csrf_exempt
@api_view(["POST"])
@firebase_auth_required
def import_matches(request):
    """
    Import matches from an external API (Faceit or Playfly) into the database.
    Expected request format:
    {
        "platform": "faceit" | "leaguespot",
        "competition_name": "string",
        "season_id": "uuid",
        "data": {...}, // API response data
        "participant_matches": { "participant_id": "team_id", ... } // Optional
    }
    """
    try:
        data = request.data
        platform = data.get("platform", "").lower()
        competition_name = data.get("competition_name", "")
        season_id = data.get("season_id")
        api_data = data.get("data", {})
        participant_matches = data.get("participant_matches", {})

        # Get or create the competition
        competition, created = Competition.objects.get_or_create(name=competition_name)

        # Get the season
        try:
            season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            return Response(
                {"error": "Season not found"}, status=status.HTTP_400_BAD_REQUEST
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

        # Process matches based on platform
        if platform == "faceit":
            imported_matches = import_match_data(
                api_data, competition, season, platform
            )
        elif platform == "leaguespot":
            imported_matches = import_match_data(
                api_data, competition, season, platform
            )
        else:
            return Response(
                {"error": "Unsupported platform"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "Import successful",
                "matches_imported": len(imported_matches),
                "match_ids": imported_matches,
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def import_match_data(api_data, competition, season, platform):
    """
    Process Faceit API data and import matches
    """
    imported_matches = []

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
        if Match.objects.filter(id=match_id).exists():
            continue  # Skip existing matches

        # Create the match
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

        imported_matches.append(str(match.id))

    return imported_matches


def get_or_create_team(team_data, competition, season, platform):
    """
    Helper function to get or create a team from API data
    """
    team_name = team_data.get("name", "Unknown Team")
    team_avatar = team_data.get("avatar")
    team_faceit_id = team_data.get("faction_id")

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

        if updated:
            participant.save()

    # Process players if needed
    roster = team_data.get("roster", [])
    for player_data in roster:
        process_player(player_data, team, season)

    return team, created


def process_player(player_data, team, season):
    """
    Process player data and associate with team
    """
    player_id = player_data.get("player_id")
    game_player_id = player_data.get("game_player_id")
    nickname = player_data.get("nickname", "Unknown Player")
    avatar = player_data.get("avatar")

    if game_player_id == "":
        game_player_id = None

    elo = 1000

    player_exists = (
        Player.objects.filter(steam_id=game_player_id).exists()
        if game_player_id
        else False
    )

    if not player_exists:
        try:
            print(f"Processing player {nickname} with game_player_id {game_player_id}")
            # If we have a game_player_id (steam_id), fetch Faceit player ID from Faceit API
            if game_player_id:
                faceit_api_url = "https://open.faceit.com/data/v4/players"
                api_key = getattr(settings, "FACEIT_API_KEY", None)
                if api_key:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    params = {"game": "cs2", "game_player_id": game_player_id}
                    response = requests.get(
                        faceit_api_url, headers=headers, params=params
                    )
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

    # Try to find player by steam_id first, then by faceit_id
    player = None

    # First, try to find by steam_id if available
    if game_player_id:
        try:
            player = Player.objects.get(steam_id=game_player_id)
            # Update player info if found by steam_id
            player.name = nickname
            player.picture = avatar
            player.faceit_id = player_id
            player.elo = elo
            player.team = team
            player.benched = False
            player.seasons.add(season)
            player.save()
            return player
        except Player.DoesNotExist:
            pass

    # If not found by steam_id, try to find by faceit_id
    if player_id:
        try:
            player = Player.objects.get(faceit_id=player_id)
            # Update steam_id if it was missing
            if game_player_id and not player.steam_id:
                player.steam_id = game_player_id
            player.name = nickname
            player.picture = avatar
            player.elo = elo
            player.team = team
            player.benched = False
            player.seasons.add(season)
            player.save()
            return player
        except Player.DoesNotExist:
            pass

    # If player not found by either ID, create new player
    player = Player.objects.create(
        name=nickname,
        picture=avatar,
        faceit_id=player_id,
        team=team,
        elo=elo,
        steam_id=game_player_id,
    )
    player.seasons.set([season])

    return player


@api_view(["GET"])
@firebase_auth_required
def list_seasons(request):
    """
    Get all seasons
    """
    seasons = Season.objects.all()
    result = []

    for season in seasons:
        result.append(
            {
                "id": season.id,
                "name": season.name,
                "start_date": season.start_date,
                "end_date": season.end_date,
            }
        )

    return Response(result)


@api_view(["POST"])
@firebase_auth_required
def create_season(request):
    """
    Create a new season
    """
    try:
        name = request.data.get("name")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not all([name, start_date, end_date]):
            return Response(
                {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
            )

        season = Season.objects.create(
            name=name,
            start_date=parse_datetime(start_date),
            end_date=parse_datetime(end_date),
        )

        return Response(
            {
                "id": season.id,
                "name": season.name,
                "start_date": season.start_date,
                "end_date": season.end_date,
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@firebase_auth_required
def list_teams(request):
    """
    Get all teams
    """
    teams = Team.objects.all()
    result = []

    for team in teams:
        captain = None
        if team.captain:
            captain = {
                "id": team.captain.id,
                "name": team.captain.name,
                "picture": team.captain.picture,
            }

        result.append(
            {
                "id": team.id,
                "name": team.name,
                "picture": team.picture,
                "school_name": team.school_name,
                "elo": team.elo,
                "captain": captain,
            }
        )

    return Response(result)


@api_view(["GET"])
@firebase_auth_required
def list_players(request):
    """
    Get all players
    """
    players = Player.objects.all()
    result = []

    for player in players:
        team = None
        if player.team:
            team = {
                "id": player.team.id,
                "name": player.team.name,
                "picture": player.team.picture,
            }

        result.append(
            {
                "id": player.id,
                "name": player.name,
                "picture": player.picture,
                "skill_level": player.skill_level,
                "steam_id": player.steam_id,
                "faceit_id": player.faceit_id,
                "elo": player.elo,
                "team": team,
                "benched": player.benched,
                "visible": player.visible,
            }
        )

    return Response(result)


@api_view(["GET"])
@firebase_auth_required
def list_matches(request):
    """
    Get all matches
    """
    matches = Match.objects.all().order_by("-date")
    result = []

    for match in matches:
        winner = None
        if match.winner:
            winner = {
                "id": match.winner.id,
                "name": match.winner.name,
            }

        result.append(
            {
                "id": match.id,
                "team1": {
                    "id": match.team1.id,
                    "name": match.team1.name,
                    "picture": match.team1.picture,
                },
                "team2": {
                    "id": match.team2.id,
                    "name": match.team2.name,
                    "picture": match.team2.picture,
                },
                "date": match.date,
                "status": match.status,
                "url": match.url,
                "winner": winner,
                "score_team1": match.score_team1,
                "score_team2": match.score_team2,
                "platform": match.platform,
                "season": {"id": match.season.id, "name": match.season.name}
                if match.season
                else None,
                "competition": {
                    "id": match.competition.id,
                    "name": match.competition.name,
                }
                if match.competition
                else None,
            }
        )

    return Response(result)


@api_view(["POST"])
@firebase_auth_required
def clear_database(request):
    """
    Clear the database for testing purposes.
    This will delete all matches, participants, teams, players, events, and rankings.
    It will NOT delete seasons or competitions to preserve the structure.
    """
    try:
        # Verify security key to prevent accidental deletion
        security_key = request.data.get("security_key")
        if security_key != "confirm-database-clear-123":  # Simple security key
            return Response(
                {"error": "Invalid security key"}, status=status.HTTP_403_FORBIDDEN
            )

        # Delete data in a specific order to prevent foreign key constraint issues
        EventMatch.objects.all().delete()
        Event.objects.all().delete()
        Match.objects.all().delete()
        RankingItem.objects.all().delete()
        Ranking.objects.all().delete()
        Participant.objects.all().delete()
        Player.objects.all().delete()
        Team.objects.all().delete()

        return Response({"message": "Database cleared successfully"})

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@firebase_auth_required
def update_player_elo(request):
    """
    Update player ELO ratings from Faceit API.
    This will fetch the latest ELO for all players with a faceit_id
    and update the values in our database.
    """
    try:
        # Get all players with faceit_id
        players = Player.objects.filter(steam_id__isnull=False)
        updated_count = 0
        not_found_count = 0
        faceit_api_url = "https://open.faceit.com/data/v4/players"

        # Get the API key from request headers or use default
        api_key = request.data.get("api_key", "3c0ddd87-ff50-45df-8d56-3cf62ef5fbc8")

        for player in players:
            if not player.steam_id:
                print(f"Skipping player {player.name} with no STEAM ID")
                continue

            try:
                api_key = getattr(settings, "FACEIT_API_KEY", None)
                headers = {"Authorization": f"Bearer {api_key}"}
                params = {"game": "cs2", "game_player_id": player.steam_id}
                response = requests.get(faceit_api_url, headers=headers, params=params)

                if response.status_code == 200:
                    player_data = response.json()
                    games = player_data.get("games", {})

                    # Look for CS2 or CS:GO game data
                    cs_data = games.get("cs2")

                    if cs_data and "faceit_elo" in cs_data:
                        player.elo = cs_data["faceit_elo"]
                        player.skill_level = cs_data.get("skill_level", 1)
                        player.save()
                        print(f"Updated ELO for player {player.name} to {player.elo}")
                        updated_count += 1
                    else:
                        not_found_count += 1
                else:
                    not_found_count += 1

            except Exception as e:
                print(f"Error updating player {player.name}: {str(e)}")
                not_found_count += 1

        return Response(
            {
                "message": "Player ELO update completed",
                "updated_players": updated_count,
                "not_found": not_found_count,
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@firebase_auth_required
def reset_player_elo(request):
    """
    Reset all player ELO ratings to the default value.
    """
    try:
        # Get default ELO value from request or use 1000
        default_elo = request.data.get("default_elo", 1000)
        default_skill_level = request.data.get("default_skill_level", 1)

        # Update all players
        players = Player.objects.all()
        updated_count = 0

        for player in players:
            player.elo = default_elo
            player.skill_level = default_skill_level
            player.save()
            updated_count += 1

        return Response(
            {
                "message": f"Player ELO reset to {default_elo}",
                "updated_players": updated_count,
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET", "POST"])
@firebase_auth_required
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


@api_view(["POST"])
@firebase_auth_required
def recalculate_elos(request):
    """
    Recalculate ELO ratings for all teams based on completed matches in chronological order.
    This is useful when importing historical match data.

    Expected request format:
    {
        "reset_to_default": true, // Optional - default true
        "default_elo": 1000 // Optional - default 1000
    }
    """
    try:
        reset_to_default = request.data.get("reset_to_default", True)
        default_elo = request.data.get("default_elo", 1000)

        result = recalculate_all_elos(
            reset_to_default=reset_to_default, default_elo=default_elo
        )

        return Response(
            {
                "message": "ELO recalculation completed successfully",
                "summary": {
                    "total_matches": result["total_matches"],
                    "processed_count": result["processed_count"],
                    "error_count": result["error_count"],
                    "reset_to_default": result["reset_to_default"],
                    "default_elo": result["default_elo"],
                },
                "elo_changes": result["elo_changes"][:10]
                if len(result["elo_changes"]) > 10
                else result["elo_changes"],  # Limit to first 10 for response size
                "total_elo_changes": len(result["elo_changes"]),
            }
        )

    except Exception as e:
        logger.error(f"Error in recalculate_elos: {str(e)}")
        return Response(
            {"error": f"Failed to recalculate ELOs: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@firebase_auth_required
def calculate_team_elos(request):
    """
    Calculate team ELOs based on player ELOs.
    Formula: team_elo = mean(top 5 player ELOs) - 0.1 * std_dev(top 5 player ELOs)

    Expected request format:
    {
        "only_default_elo": true, // Optional - only calculate for teams with default ELO (1000)
        "default_elo": 1000 // Optional - what is considered the default ELO value
    }
    """
    try:
        import statistics

        # Get request parameters
        only_default_elo = request.data.get("only_default_elo", False)
        default_elo = request.data.get("default_elo", 1000)

        # Get teams based on filter
        if only_default_elo:
            teams = Team.objects.filter(elo=default_elo)
        else:
            teams = Team.objects.all()

        updated_count = 0
        no_players_count = 0

        for team in teams:
            # Get active (non-benched) players for this team
            players = Player.objects.filter(team=team, benched=False)

            # Get player ELOs
            player_elos = [player.elo for player in players if player.elo > 0]

            # Need at least 2 players to calculate standard deviation
            if len(player_elos) < 2:
                no_players_count += 1
                continue

            # Take the highest 5 ELOs for this average
            player_elos.sort(reverse=True)
            player_elos = player_elos[:5]

            # Calculate team ELO
            mean_elo = statistics.mean(player_elos)
            std_dev = statistics.stdev(player_elos)
            k = 0.1
            team_elo = mean_elo - k * std_dev

            # Round to integer
            team_elo = round(team_elo)

            # Update team
            team.elo = team_elo
            team.save()
            logger.info(f"Updated ELO for team {team.name} to {team.elo}")
            updated_count += 1

        return Response(
            {
                "message": "Team ELO calculation completed",
                "updated_teams": updated_count,
                "teams_without_enough_players": no_players_count,
                "only_default_elo": only_default_elo,
                "default_elo_value": default_elo,
                "total_teams_processed": teams.count(),
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@firebase_auth_required
def create_ranking_snapshot(request):
    """
    Create a ranking snapshot based on current team ELO values.
    This captures the current state of team rankings for historical tracking.

    Optional request format:
    {
        "season_id": "uuid", // Optional - specific season to capture rankings for
        "name": "Custom Snapshot Name" // Optional - custom name for identification
    }
    """
    try:
        season_id = request.data.get("season_id")

        # Get the season if specified, otherwise use the most recent season
        season = None
        if season_id:
            try:
                season = Season.objects.get(id=season_id)
            except Season.DoesNotExist:
                return Response(
                    {"error": f"Season with ID {season_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Use the most recent season if no season specified
            season = Season.objects.order_by("-start_date").first()
            if not season:
                return Response(
                    {"error": "No seasons found in database"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Get all teams with their current ELO values, ordered by ELO descending
        teams = Team.objects.filter(elo__gt=0).order_by("-elo")

        if not teams.exists():
            return Response(
                {"error": "No teams found with ELO ratings"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the ranking record
        ranking = Ranking.objects.create(season=season)

        # Create ranking items for each team
        ranking_items_created = 0
        for rank, team in enumerate(teams, start=1):
            RankingItem.objects.create(
                ranking=ranking, team=team, rank=rank, elo=team.elo
            )
            ranking_items_created += 1

        logger.info(
            f"Created ranking snapshot with {ranking_items_created} teams for season {season.name}"
        )

        return Response(
            {
                "success": True,
                "ranking_id": str(ranking.id),
                "season_name": season.name,
                "teams_ranked": ranking_items_created,
                "snapshot_date": ranking.date.isoformat(),
                "message": f"Ranking snapshot created successfully with {ranking_items_created} teams",
            }
        )

    except Exception as e:
        logger.error(f"Error creating ranking snapshot: {str(e)}")
        return Response(
            {"error": "Failed to create ranking snapshot"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@firebase_auth_required
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


# LeagueSpot API Proxy Views
# These proxy the LeagueSpot API to avoid CORS issues in the frontend


def get_leaguespot_headers():
    """Get the standard headers needed for LeagueSpot API requests"""
    apikey = getattr(settings, "PLAYFLY_API_KEY", None)
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "X-App": "web",
        "X-Version": "20250907.4",
        "X-League-Id": "53015f28-5b33-4882-9f8b-16dcbb13deee",
        "Origin": "https://esports.pcl.gg",
        "Connection": "keep-alive",
        "Referer": "https://esports.pcl.gg/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Authorization": apikey,
    }


@api_view(["GET"])
def proxy_leaguespot_season(request, season_id):
    """Proxy LeagueSpot season API to avoid CORS issues"""
    headers = get_leaguespot_headers()

    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v1/seasons/{season_id}",
            headers=headers,
            timeout=30,
        )

        # Log the response details for debugging
        logger.info(f"LeagueSpot season API response status: {response.status_code}")
        logger.info(f"LeagueSpot season API response headers: {dict(response.headers)}")
        if response.status_code != 200:
            return Response(
                {
                    "error": f"LeagueSpot API returned status {response.status_code}: {response.text}"
                },
                status=response.status_code,
            )

        # Check if response is empty
        if not response.text.strip():
            return Response(
                {"error": "LeagueSpot API returned empty response"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Try to parse JSON
        try:
            json_data = response.json()
            return Response(json_data)
        except ValueError as json_error:
            logger.error(f"Failed to parse JSON from LeagueSpot: {json_error}")
            logger.error(f"Raw response: {response.text}")
            return Response(
                {
                    "error": f"Invalid JSON response from LeagueSpot: {response.text[:200]}"
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot season {season_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch season data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def proxy_leaguespot_stage(request, stage_id):
    """Proxy LeagueSpot stage API to avoid CORS issues"""
    headers = get_leaguespot_headers()

    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v1/stages/{stage_id}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return Response(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot stage {stage_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch stage data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def proxy_leaguespot_round_matches(request, round_id):
    """Proxy LeagueSpot round matches API to avoid CORS issues"""
    headers = get_leaguespot_headers()

    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v1/rounds/{round_id}/matches",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return Response(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot round matches {round_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch round matches: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def proxy_leaguespot_match(request, match_id):
    """Proxy LeagueSpot match API to avoid CORS issues"""
    headers = get_leaguespot_headers()

    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v2/matches/{match_id}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return Response(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot match {match_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch match data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def proxy_leaguespot_participants(request, match_id):
    """Proxy LeagueSpot match participants API to avoid CORS issues"""
    headers = get_leaguespot_headers()
    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v1/matches/{match_id}/participants",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return Response(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot participants {match_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch participants data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@firebase_auth_required
def merge_teams(request):
    """
    Merge two teams into one, combining rosters and transferring all match history.

    Expected request format:
    {
        "primary_team_id": "uuid",    // Team to keep
        "secondary_team_id": "uuid"   // Team to merge into primary (will be deleted)
    }

    This operation:
    1. Moves all players from secondary team to primary team
    2. Merges all participant records (preserving competition history)
    3. Updates all matches to reference the primary team
    4. Deletes the secondary team
    """
    try:
        primary_team_id = request.data.get("primary_team_id")
        secondary_team_id = request.data.get("secondary_team_id")

        if not primary_team_id or not secondary_team_id:
            return Response(
                {"error": "Both primary_team_id and secondary_team_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if primary_team_id == secondary_team_id:
            return Response(
                {"error": "Cannot merge a team with itself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the teams
        try:
            primary_team = Team.objects.get(id=primary_team_id)
        except Team.DoesNotExist:
            return Response(
                {"error": f"Primary team with id {primary_team_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            secondary_team = Team.objects.get(id=secondary_team_id)
        except Team.DoesNotExist:
            return Response(
                {"error": f"Secondary team with id {secondary_team_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Count data before merge for response
        players_to_move = Player.objects.filter(team=secondary_team).count()

        # Start the merge process

        # 1. Move all players from secondary team to primary team
        players_moved = 0
        for player in Player.objects.filter(team=secondary_team):
            player.team = primary_team
            player.save()
            players_moved += 1
            logger.info(
                f"Moved player {player.name} from {secondary_team.name} to {primary_team.name}"
            )

        # 2. Merge participant records
        participants_merged = 0
        for secondary_participant in Participant.objects.filter(team=secondary_team):
            # Check if primary team already has a participant for this competition/season
            existing_participant = Participant.objects.filter(
                team=primary_team,
                competition=secondary_participant.competition,
                season=secondary_participant.season,
            ).first()

            if existing_participant:
                # Merge IDs from secondary participant into existing one
                if (
                    secondary_participant.faceit_id
                    and not existing_participant.faceit_id
                ):
                    existing_participant.faceit_id = secondary_participant.faceit_id
                if (
                    secondary_participant.playfly_id
                    and not existing_participant.playfly_id
                ):
                    existing_participant.playfly_id = secondary_participant.playfly_id
                if (
                    secondary_participant.playfly_participant_id
                    and not existing_participant.playfly_participant_id
                ):
                    existing_participant.playfly_participant_id = (
                        secondary_participant.playfly_participant_id
                    )

                existing_participant.save()
                secondary_participant.delete()
                comp_name = (
                    secondary_participant.competition.name
                    if secondary_participant.competition
                    else "Unknown"
                )
                season_name = (
                    secondary_participant.season.name
                    if secondary_participant.season
                    else "Unknown"
                )
                logger.info(f"Merged participant for {comp_name}/{season_name}")
            else:
                # Before transferring, check if there's already a participant with the same IDs
                # that would cause a unique constraint violation
                conflict_participant = None

                # Check for faceit_id conflict
                if secondary_participant.faceit_id:
                    conflict_participant = (
                        Participant.objects.filter(
                            faceit_id=secondary_participant.faceit_id
                        )
                        .exclude(id=secondary_participant.id)
                        .first()
                    )

                # Check for playfly_id conflict if no faceit conflict
                if not conflict_participant and secondary_participant.playfly_id:
                    conflict_participant = (
                        Participant.objects.filter(
                            playfly_id=secondary_participant.playfly_id
                        )
                        .exclude(id=secondary_participant.id)
                        .first()
                    )

                # Check for playfly_participant_id conflict if no other conflicts
                if (
                    not conflict_participant
                    and secondary_participant.playfly_participant_id
                ):
                    conflict_participant = (
                        Participant.objects.filter(
                            playfly_participant_id=secondary_participant.playfly_participant_id
                        )
                        .exclude(id=secondary_participant.id)
                        .first()
                    )

                if conflict_participant:
                    # There's a conflict - we need to clear the conflicting IDs before transfer
                    logger.warning(
                        f"Clearing conflicting IDs for participant transfer: "
                        f"faceit_id={secondary_participant.faceit_id}, "
                        f"playfly_id={secondary_participant.playfly_id}, "
                        f"playfly_participant_id={secondary_participant.playfly_participant_id}"
                    )

                    # Clear the IDs that would cause conflicts
                    if (
                        conflict_participant.faceit_id
                        == secondary_participant.faceit_id
                    ):
                        secondary_participant.faceit_id = None
                    if (
                        conflict_participant.playfly_id
                        == secondary_participant.playfly_id
                    ):
                        secondary_participant.playfly_id = None
                    if (
                        conflict_participant.playfly_participant_id
                        == secondary_participant.playfly_participant_id
                    ):
                        secondary_participant.playfly_participant_id = None

                # Now transfer participant to primary team
                secondary_participant.team = primary_team
                secondary_participant.save()
                comp_name = (
                    secondary_participant.competition.name
                    if secondary_participant.competition
                    else "Unknown"
                )
                season_name = (
                    secondary_participant.season.name
                    if secondary_participant.season
                    else "Unknown"
                )
                logger.info(f"Transferred participant for {comp_name}/{season_name}")

            participants_merged += 1

        # 3. Update all matches to reference primary team
        matches_updated = 0

        # Update matches where secondary team is team1
        for match in Match.objects.filter(team1=secondary_team):
            match.team1 = primary_team
            match.save()
            matches_updated += 1
            logger.info(
                f"Updated match {match.id} team1 from {secondary_team.name} to {primary_team.name}"
            )

        # Update matches where secondary team is team2
        for match in Match.objects.filter(team2=secondary_team):
            match.team2 = primary_team
            match.save()
            matches_updated += 1
            logger.info(
                f"Updated match {match.id} team2 from {secondary_team.name} to {primary_team.name}"
            )

        # Update matches where secondary team is the winner
        for match in Match.objects.filter(winner=secondary_team):
            match.winner = primary_team
            match.save()
            logger.info(
                f"Updated match {match.id} winner from {secondary_team.name} to {primary_team.name}"
            )

        # 4. Store secondary team info for response, then delete it
        secondary_team_info = {
            "id": str(secondary_team.id),
            "name": secondary_team.name,
            "player_count": players_to_move,
        }

        secondary_team.delete()
        logger.info(f"Deleted secondary team {secondary_team_info['name']}")

        # Prepare response
        response_data = {
            "message": f"Successfully merged {secondary_team_info['name']} into {primary_team.name}",
            "primary_team": {
                "id": str(primary_team.id),
                "name": primary_team.name,
                "player_count": Player.objects.filter(team=primary_team).count(),
            },
            "secondary_team": secondary_team_info,
            "merged_data": {
                "players_moved": players_moved,
                "participants_merged": participants_merged,
                "matches_updated": matches_updated,
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error merging teams: {str(e)}")
        return Response(
            {"error": f"Failed to merge teams: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["DELETE"])
@firebase_auth_required
def delete_competition(request, competition_id):
    """
    Delete a competition and all its related data.
    This will remove all matches, participants, and the competition itself.

    WARNING: This is a destructive operation that cannot be undone.

    Expected request format:
    {
        "security_key": "confirm-delete-competition-789" // Required security key
    }
    """
    try:
        # Verify security key to prevent accidental deletion
        security_key = request.data.get("security_key")
        if security_key != "confirm-delete-competition-789":
            return Response(
                {"error": "Invalid security key."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get the competition
        try:
            competition = Competition.objects.get(id=competition_id)
        except Competition.DoesNotExist:
            return Response(
                {"error": f"Competition with ID {competition_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        competition_name = competition.name

        # Delete in proper order to avoid foreign key constraint issues
        # Note: Django's CASCADE should handle most of this automatically, but we'll be explicit

        # 1. Delete EventMatches related to this competition
        event_matches_deleted = 0
        for season in Season.objects.filter(
            participants__competition=competition
        ).distinct():
            for event in Event.objects.filter(season=season):
                event_matches = EventMatch.objects.filter(event=event)
                event_matches_deleted += event_matches.count()
                event_matches.delete()

        # 2. Delete Events related to this competition
        events_deleted = 0
        for season in Season.objects.filter(
            participants__competition=competition
        ).distinct():
            events = Event.objects.filter(season=season)
            events_deleted += events.count()
            events.delete()

        # 3. Delete Matches related to this competition
        matches = Match.objects.filter(competition=competition)
        matches_deleted = matches.count()
        matches.delete()

        # 4. Delete Participants related to this competition
        participants = Participant.objects.filter(competition=competition)
        participants_deleted = participants.count()
        participants.delete()

        # 5. Finally, delete the competition itself
        competition.delete()

        logger.info(f"Deleted competition '{competition_name}' and all related data")

        return Response(
            {
                "message": f"Successfully deleted competition '{competition_name}' and all related data",
                "competition_name": competition_name,
                "competition_id": str(competition_id),
                "deleted_data": {
                    "participants": participants_deleted,
                    "matches": matches_deleted,
                    "events": events_deleted,
                    "event_matches": event_matches_deleted,
                    "competition": 1,
                },
                "total_records_deleted": (
                    participants_deleted
                    + matches_deleted
                    + events_deleted
                    + event_matches_deleted
                    + 1
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error deleting competition {competition_id}: {str(e)}")
        return Response(
            {"error": f"Failed to delete competition: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@firebase_auth_required
def list_competitions(request):
    """
    Get all competitions with their associated data counts.
    """
    try:
        competitions = Competition.objects.all()
        result = []

        for competition in competitions:
            participants_count = Participant.objects.filter(
                competition=competition
            ).count()
            matches_count = Match.objects.filter(competition=competition).count()

            # Get unique teams participating in this competition
            teams_count = (
                Participant.objects.filter(competition=competition, team__isnull=False)
                .values("team")
                .distinct()
                .count()
            )

            result.append(
                {
                    "id": str(competition.id),
                    "name": competition.name,
                    "participants_count": participants_count,
                    "matches_count": matches_count,
                    "teams_count": teams_count,
                }
            )

        return Response(
            {
                "competitions": result,
                "total_competitions": len(result),
            }
        )

    except Exception as e:
        logger.error(f"Error listing competitions: {str(e)}")
        return Response(
            {"error": f"Failed to list competitions: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
