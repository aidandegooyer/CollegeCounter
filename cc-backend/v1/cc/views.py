from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
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
            imported_matches = import_playfly_matches(api_data, competition, season)
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
        if isinstance(dt, str):
            return parse_datetime(dt)
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
        process_player(player_data, team)

    return team, created


def process_player(player_data, team):
    """
    Process player data and associate with team
    """
    player_id = player_data.get("player_id")
    nickname = player_data.get("nickname", "Unknown Player")
    avatar = player_data.get("avatar")

    # Try to find player by Faceit ID
    try:
        player = Player.objects.get(faceit_id=player_id)
        player.benched = False  # Reset benched status
    except Player.DoesNotExist:
        # Create new player
        player = Player.objects.create(
            name=nickname, picture=avatar, faceit_id=player_id, team=team
        )

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
