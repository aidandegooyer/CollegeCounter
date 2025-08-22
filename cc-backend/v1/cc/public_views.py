from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.dateparse import parse_datetime
from datetime import datetime
import uuid

from .models import Competition, Team, Player, Match, Season, Participant

# Maximum items per page
MAX_PAGE_SIZE = 100


@api_view(["GET"])
def public_teams(request):
    """
    Public API endpoint to fetch teams with various filters.

    Query Parameters:
    - id: Filter by team ID (comma-separated for multiple)
    - name: Filter by team name (partial match)
    - school_name: Filter by school name (partial match)
    - season_id: Filter by season ID
    - competition_id: Filter by competition ID
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - sort: Sort field (default: name)
    - order: Sort order (asc or desc, default: asc)

    Returns a paginated list of teams.
    """
    # Parse query parameters
    team_ids = (
        request.query_params.get("id", "").split(",")
        if request.query_params.get("id")
        else []
    )
    team_ids = [id.strip() for id in team_ids if id.strip()]

    name = request.query_params.get("name", "")
    school_name = request.query_params.get("school_name", "")
    season_id = request.query_params.get("season_id", "")
    competition_id = request.query_params.get("competition_id", "")

    page = int(request.query_params.get("page", "1"))
    page_size = min(int(request.query_params.get("page_size", "20")), MAX_PAGE_SIZE)

    sort_field = request.query_params.get("sort", "name")
    sort_order = request.query_params.get("order", "asc")

    # Sort
    valid_sort_fields = ["name", "school_name", "elo"]
    if sort_field not in valid_sort_fields:
        sort_field = "name"

    if sort_order.lower() == "desc":
        sort_field = f"-{sort_field}"

    # Build query and filter
    query = Q()

    if team_ids:
        query &= Q(id__in=team_ids)

    if name:
        query &= Q(name__icontains=name)

    if school_name:
        query &= Q(school_name__icontains=school_name)

    if season_id or competition_id:
        participant_query = Q()

        if season_id:
            try:
                uuid.UUID(season_id)  # Validate UUID
                participant_query &= Q(season_id=season_id)
            except ValueError:
                return Response(
                    {"error": "Invalid season_id format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if competition_id:
            try:
                uuid.UUID(competition_id)  # Validate UUID
                participant_query &= Q(competition_id=competition_id)
            except ValueError:
                return Response(
                    {"error": "Invalid competition_id format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        team_ids_from_participants = Participant.objects.filter(
            participant_query
        ).values_list("team_id", flat=True)

        query &= Q(id__in=team_ids_from_participants)

    teams = Team.objects.filter(query).order_by(sort_field)

    # Paginate
    paginator = Paginator(teams, page_size)

    try:
        paginated_teams = paginator.page(page)
    except Exception:
        paginated_teams = paginator.page(paginator.num_pages)

    # Format response
    result = {
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page,
        "page_size": page_size,
        "results": [],
    }

    for team in paginated_teams:
        captain = None
        if team.captain:
            captain = {
                "id": team.captain.id,
                "name": team.captain.name,
                "picture": team.captain.picture,
            }

        result["results"].append(
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
def public_players(request):
    """
    Public API endpoint to fetch players with various filters.

    Query Parameters:
    - id: Filter by player ID (comma-separated for multiple)
    - name: Filter by player name (partial match)
    - team_id: Filter by team ID
    - steam_id: Filter by Steam ID
    - faceit_id: Filter by Faceit ID
    - visible: Filter by visibility (true/false)
    - benched: Filter by bench status (true/false)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - sort: Sort field (default: name)
    - order: Sort order (asc or desc, default: asc)

    Returns a paginated list of players.
    """
    # Parse query parameters
    player_ids = (
        request.query_params.get("id", "").split(",")
        if request.query_params.get("id")
        else []
    )
    player_ids = [id.strip() for id in player_ids if id.strip()]

    name = request.query_params.get("name", "")
    team_id = request.query_params.get("team_id", "")
    steam_id = request.query_params.get("steam_id", "")
    faceit_id = request.query_params.get("faceit_id", "")

    visible = request.query_params.get("visible", "")
    benched = request.query_params.get("benched", "")

    page = int(request.query_params.get("page", "1"))
    page_size = min(int(request.query_params.get("page_size", "20")), MAX_PAGE_SIZE)

    sort_field = request.query_params.get("sort", "name")
    sort_order = request.query_params.get("order", "asc")

    # sort
    valid_sort_fields = ["name", "elo", "skill_level"]
    if sort_field not in valid_sort_fields:
        sort_field = "name"

    if sort_order.lower() == "desc":
        sort_field = f"-{sort_field}"

    # Build query and filter
    query = Q()

    if player_ids:
        query &= Q(id__in=player_ids)

    if name:
        query &= Q(name__icontains=name)

    if team_id:
        try:
            uuid.UUID(team_id)  # Validate UUID
            query &= Q(team_id=team_id)
        except ValueError:
            return Response(
                {"error": "Invalid team_id format"}, status=status.HTTP_400_BAD_REQUEST
            )

    if steam_id:
        query &= Q(steam_id=steam_id)

    if faceit_id:
        query &= Q(faceit_id=faceit_id)

    if visible.lower() in ["true", "false"]:
        query &= Q(visible=(visible.lower() == "true"))

    if benched.lower() in ["true", "false"]:
        query &= Q(benched=(benched.lower() == "true"))

    if not visible:
        query &= Q(visible=True)

    players = Player.objects.filter(query).order_by(sort_field)

    # Paginate
    paginator = Paginator(players, page_size)

    try:
        paginated_players = paginator.page(page)
    except Exception:
        paginated_players = paginator.page(paginator.num_pages)

    # Format response
    result = {
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page,
        "page_size": page_size,
        "results": [],
    }

    for player in paginated_players:
        team = None
        if player.team:
            team = {
                "id": player.team.id,
                "name": player.team.name,
                "picture": player.team.picture,
            }

        result["results"].append(
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
def public_matches(request):
    """
    Public API endpoint to fetch matches with various filters.

    Query Parameters:
    - id: Filter by match ID (comma-separated for multiple)
    - team_id: Filter by team ID (matches where team is team1 or team2)
    - status: Filter by status (scheduled, in_progress, completed, cancelled)
    - platform: Filter by platform (faceit, playfly)
    - date_from: Filter by date (matches after this date, format: YYYY-MM-DD)
    - date_to: Filter by date (matches before this date, format: YYYY-MM-DD)
    - season_id: Filter by season ID
    - competition_id: Filter by competition ID
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - sort: Sort field (default: -date for most recent first)
    - order: Sort order (asc or desc, default: asc)

    Returns a paginated list of matches.
    """
    # Parse query parameters
    match_ids = (
        request.query_params.get("id", "").split(",")
        if request.query_params.get("id")
        else []
    )
    match_ids = [id.strip() for id in match_ids if id.strip()]

    team_id = request.query_params.get("team_id", "")
    status = request.query_params.get("status", "")
    platform = request.query_params.get("platform", "")
    date_from = request.query_params.get("date_from", "")
    date_to = request.query_params.get("date_to", "")
    season_id = request.query_params.get("season_id", "")
    competition_id = request.query_params.get("competition_id", "")

    page = int(request.query_params.get("page", "1"))
    page_size = min(int(request.query_params.get("page_size", "20")), MAX_PAGE_SIZE)

    sort_field = request.query_params.get("sort", "date")
    sort_order = request.query_params.get("order", "desc")  # Default to most recent

    # sort
    valid_sort_fields = ["date", "status"]
    if sort_field not in valid_sort_fields:
        sort_field = "date"

    if sort_order.lower() == "desc":
        sort_field = f"-{sort_field}"

    # Build query and filter
    query = Q()

    if match_ids:
        query &= Q(id__in=match_ids)

    if team_id:
        try:
            uuid.UUID(team_id)
            query &= Q(team1_id=team_id) | Q(team2_id=team_id)
        except ValueError:
            return Response(
                {"error": "Invalid team_id format"}, status=status.HTTP_400_BAD_REQUEST
            )

    if status and status in ["scheduled", "in_progress", "completed", "cancelled"]:
        query &= Q(status=status)

    if platform and platform in ["faceit", "playfly"]:
        query &= Q(platform=platform)

    if date_from:
        try:
            from_date = parse_datetime(f"{date_from}T00:00:00Z")
            if from_date:
                query &= Q(date__gte=from_date)
        except Exception:
            return Response(
                {"error": "Invalid date_from format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if date_to:
        try:
            to_date = parse_datetime(f"{date_to}T23:59:59Z")
            if to_date:
                query &= Q(date__lte=to_date)
        except Exception:
            return Response(
                {"error": "Invalid date_to format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if season_id or competition_id:
        event_query = Q()

        if season_id:
            try:
                uuid.UUID(season_id)  # Validate UUID
                event_query &= Q(season_id=season_id)
            except ValueError:
                return Response(
                    {"error": "Invalid season_id format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if competition_id:
            try:
                uuid.UUID(competition_id)  # Validate UUID
                event_query &= Q(competition_id=competition_id)
            except ValueError:
                return Response(
                    {"error": "Invalid competition_id format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            # If no matches found in the specified season/competition, return empty
            return Response(
                {
                    "count": 0,
                    "total_pages": 0,
                    "current_page": page,
                    "page_size": page_size,
                    "results": [],
                }
            )

    matches = Match.objects.filter(query).order_by(sort_field)

    # Paginate
    paginator = Paginator(matches, page_size)

    try:
        paginated_matches = paginator.page(page)
    except Exception:
        paginated_matches = paginator.page(paginator.num_pages)

    # Format response
    result = {
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page,
        "page_size": page_size,
        "results": [],
    }

    for match in paginated_matches:
        winner = None
        if match.winner:
            winner = {
                "id": match.winner.id,
                "name": match.winner.name,
            }

        result["results"].append(
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


@api_view(["GET"])
def public_seasons(request):
    """
    Public API endpoint to fetch seasons.

    Query Parameters:
    - id: Filter by season ID (comma-separated for multiple)
    - current: Filter for current season (true/false)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - sort: Sort field (default: -start_date for most recent first)
    - order: Sort order (asc or desc, default: desc)

    Returns a paginated list of seasons.
    """
    # Parse query parameters
    season_ids = (
        request.query_params.get("id", "").split(",")
        if request.query_params.get("id")
        else []
    )
    season_ids = [id.strip() for id in season_ids if id.strip()]

    current = request.query_params.get("current", "")

    page = int(request.query_params.get("page", "1"))
    page_size = min(int(request.query_params.get("page_size", "20")), MAX_PAGE_SIZE)

    sort_field = request.query_params.get("sort", "start_date")
    sort_order = request.query_params.get("order", "desc")  # Default to most recent

    # sort
    valid_sort_fields = ["name", "start_date", "end_date"]
    if sort_field not in valid_sort_fields:
        sort_field = "start_date"

    if sort_order.lower() == "desc":
        sort_field = f"-{sort_field}"

    # Build query and filter
    query = Q()

    if season_ids:
        query &= Q(id__in=season_ids)

    if current.lower() == "true":
        today = datetime.now().date()
        query &= Q(start_date__lte=today, end_date__gte=today)

    seasons = Season.objects.filter(query).order_by(sort_field)

    paginator = Paginator(seasons, page_size)

    try:
        paginated_seasons = paginator.page(page)
    except Exception:
        paginated_seasons = paginator.page(paginator.num_pages)

    # Format response
    result = {
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page,
        "page_size": page_size,
        "results": [],
    }

    for season in paginated_seasons:
        # Convert datetime to date for comparison if needed
        current_date = datetime.now().date()
        is_current = False
        if season.start_date and season.end_date:
            is_current = (
                season.start_date.date() <= current_date <= season.end_date.date()
            )

        result["results"].append(
            {
                "id": season.id,
                "name": season.name,
                "start_date": season.start_date,
                "end_date": season.end_date,
                "is_current": is_current,
            }
        )

    return Response(result)


@api_view(["GET"])
def public_competition_name(request, competition_id):
    """
    Public API endpoint to fetch the name of a competition by its ID.

    Path Parameters:
    - competition_id: The UUID of the competition

    Returns the name of the competition.
    """
    try:
        uuid.UUID(competition_id)  # Validate UUID format
    except ValueError:
        return Response(
            {"error": "Invalid competition_id format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        competition = Competition.objects.get(id=competition_id)
        return Response({"name": competition.name})
    except Competition.DoesNotExist:
        return Response(
            {"error": "Competition not found"}, status=status.HTTP_404_NOT_FOUND
        )
