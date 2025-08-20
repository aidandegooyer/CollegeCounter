from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime

import json
import uuid
from .models import (
    Team,
    Player,
    Match,
    Season,
    Participant,
    Competition,
    Event,
    EventMatch,
)


def index(request):
    return HttpResponse("Hello! This is the College Counter backend API.")


@csrf_exempt
@api_view(["POST"])
def import_matches(request):
    """
    Import matches from an external API (Faceit or Playfly) into the database.
    Expected request format:
    {
        "platform": "faceit" | "playfly",
        "competition_name": "string",
        "season_id": "uuid",
        "data": {...} // API response data
    }
    """
    try:
        data = request.data
        platform = data.get("platform", "").lower()
        competition_name = data.get("competition_name", "")
        season_id = data.get("season_id")
        api_data = data.get("data", {})

        # Get or create the competition
        competition, created = Competition.objects.get_or_create(name=competition_name)

        # Get the season
        try:
            season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            return Response(
                {"error": "Season not found"}, status=status.HTTP_400_BAD_REQUEST
            )

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
        match_id = match_data.get("match_id")
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

    return imported_matches


def get_or_create_team(team_data, competition, season):
    """
    Helper function to get or create a team from API data
    """
    team_name = team_data.get("name", "Unknown Team")
    team_avatar = team_data.get("avatar")

    # Try to find existing team by name
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
            "faceit_id": team_data.get("id")  # Adjust field as needed
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
    except Player.DoesNotExist:
        # Create new player
        player = Player.objects.create(
            name=nickname, picture=avatar, faceit_id=player_id, team=team
        )

    return player


@api_view(["GET"])
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
            }
        )

    return Response(result)
