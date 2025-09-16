from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status
from datetime import datetime
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
        "platform": "faceit" | "playfly",
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
                                    if platform_name == "playfly"
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
            imported_matches = import_faceit_matches(api_data, competition, season)
        elif platform == "playfly":
            imported_matches = import_faceit_matches(api_data, competition, season)
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


def import_faceit_matches(api_data, competition, season):
    """
    Process Faceit API data and import matches
    """

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

    imported_matches = []

    # Extract matches from the API response
    matches = api_data.get("items", [])

    for match_data in matches:
        # Extract match details
        # match_id = match_data.get("match_id")
        faceit_url = match_data.get("faceit_url")
        status_value = match_data.get("status")

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
        team1, _ = get_or_create_team(team1_data, competition, season)
        team2, _ = get_or_create_team(team2_data, competition, season)

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

        # Create the match
        match = Match.objects.create(
            team1=team1,
            team2=team2,
            date=safe_parse_datetime(match_date) if match_date else None,
            status=match_status,
            url=faceit_url,
            winner=winner,
            score_team1=score_team1,
            score_team2=score_team2,
            platform="faceit",
            season=season,
            competition=competition,
        )

        imported_matches.append(str(match.id))

    return imported_matches


def import_playfly_matches(api_data, competition, season):
    """
    Process Playfly API data and import matches
    Note: Implement based on Playfly API structure
    """
    # This is a placeholder - implement based on actual Playfly API structure
    imported_matches = []

    # Process matches similar to Faceit but adapted for Playfly's structure
    # When creating Match objects, include season and competition:
    # match = Match.objects.create(
    #     team1=team1,
    #     team2=team2,
    #     ...other fields...
    #     platform="playfly",
    #     season=season,
    #     competition=competition
    # )

    return imported_matches


def get_or_create_team(team_data, competition, season):
    """
    Helper function to get or create a team from API data
    """
    team_name = team_data.get("name", "Unknown Team")
    team_avatar = team_data.get("avatar")
    team_faceit_id = team_data.get("id")

    # First, check if there's an existing participant for this team ID in this competition/season
    existing_participant = None
    if team_faceit_id:
        try:
            existing_participant = Participant.objects.get(
                faceit_id=team_faceit_id, competition=competition, season=season
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
    participant, created = Participant.objects.get_or_create(
        team=team,
        competition=competition,
        season=season,
        defaults={
            "faceit_id": team_faceit_id  # Store the faceit ID
        },
    )

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
                        print(
                            f"Updated ELO for player {player.name} to {player.elo}"
                        )
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
def calculate_team_elos(request):
    """
    Calculate team ELOs based on player ELOs.
    Formula: team_elo = mean(top 5 player ELOs) - 0.1 * std_dev(top 5 player ELOs)
    """
    try:
        import statistics

        # Get all teams
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
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
