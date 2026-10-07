"""Admin CRUD for matches and event matches."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from ..models import (
    Team,
    Match,
    Season,
    Competition,
    Event,
    EventMatch,
)
from ..middleware import firebase_auth_required

import logging

from .elo import (
    delete_match_and_revert_elo,
    match_elo_data,
    save_match_and_sync_elo,
    update_match_elos,
)
from .utils import safe_parse_datetime

logger = logging.getLogger(__name__)


@api_view(["GET"])
@firebase_auth_required(min_role="base")
def list_matches(request):
    """
    Get all matches
    """
    matches = (
        Match.objects.select_related(
            "team1", "team2", "winner", "season", "competition"
        )
        .prefetch_related("event_matches__event")
        .all()
        .order_by("-date")
    )
    result = []

    for match in matches:
        winner = None
        if match.winner:
            winner = {
                "id": match.winner.id,
                "name": match.winner.name,
            }

        # Get event match data if exists
        event_match_data = None
        try:
            event_match = EventMatch.objects.filter(match=match).first()
            if event_match:
                event_match_data = {
                    "id": event_match.id,
                    "event": {
                        "id": event_match.event.id,
                        "name": event_match.event.name,
                    },
                    "round": event_match.round,
                    "num_in_bracket": event_match.num_in_bracket,
                    "is_bye": event_match.is_bye,
                    "extra_info": event_match.extra_info,
                }
        except Exception:
            # Handle case where EventMatch query fails
            pass

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
                "elo": match_elo_data(match),
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
                "event_match": event_match_data,
            }
        )

    return Response(result)


@api_view(["GET"])
@firebase_auth_required(min_role="base")
def get_match(request, match_id):
    """
    Get a single match by ID
    """
    try:
        match = get_object_or_404(Match, id=match_id)

        winner = None
        if match.winner:
            winner = {
                "id": match.winner.id,
                "name": match.winner.name,
            }

        result = {
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
            "elo": match_elo_data(match),
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

        return Response(result)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def create_match(request):
    """
    Create a new match

    Expected request format:
    {
        "team1_id": "uuid",
        "team2_id": "uuid",
        "date": "2025-01-01T15:00:00Z",  // Optional
        "status": "scheduled",  // Optional, defaults to "scheduled"
        "url": "https://example.com",  // Optional
        "score_team1": 0,  // Optional, defaults to 0
        "score_team2": 0,  // Optional, defaults to 0
        "platform": "faceit",  // Optional, defaults to "other"
        "season_id": "uuid",  // Optional
        "competition_id": "uuid",  // Optional
        "winner_id": "uuid"  // Optional, must be one of the two teams
    }
    """
    try:
        # Required fields
        team1_id = request.data.get("team1_id")
        team2_id = request.data.get("team2_id")

        if not team1_id or not team2_id:
            return Response(
                {"error": "team1_id and team2_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if team1_id == team2_id:
            return Response(
                {"error": "A team cannot play against itself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get teams
        try:
            team1 = Team.objects.get(id=team1_id)
            team2 = Team.objects.get(id=team2_id)
        except Team.DoesNotExist:
            return Response(
                {"error": "One or both teams not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Optional fields
        date_str = request.data.get("date")
        match_date = None
        if date_str:
            match_date = safe_parse_datetime(date_str)
            if not match_date:
                return Response(
                    {"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST
                )

        match_status = request.data.get("status", "scheduled")
        url = request.data.get("url")
        score_team1 = request.data.get("score_team1", 0)
        score_team2 = request.data.get("score_team2", 0)
        platform = request.data.get("platform", "other")

        # Optional season and competition
        season = None
        season_id = request.data.get("season_id")
        if season_id:
            try:
                season = Season.objects.get(id=season_id)
            except Season.DoesNotExist:
                return Response(
                    {"error": "Season not found"}, status=status.HTTP_404_NOT_FOUND
                )

        competition = None
        competition_id = request.data.get("competition_id")
        if competition_id:
            try:
                competition = Competition.objects.get(id=competition_id)
            except Competition.DoesNotExist:
                return Response(
                    {"error": "Competition not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # Optional winner
        winner = None
        winner_id = request.data.get("winner_id")
        if winner_id:
            if winner_id == team1_id:
                winner = team1
            elif winner_id == team2_id:
                winner = team2
            else:
                return Response(
                    {"error": "Winner must be one of the two teams in the match"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Create the match
        match = Match.objects.create(
            team1=team1,
            team2=team2,
            date=match_date,
            status=match_status,
            url=url,
            score_team1=score_team1,
            score_team2=score_team2,
            platform=platform,
            season=season,
            competition=competition,
            winner=winner,
        )

        # Create EventMatch if event_id is provided
        event_match = None
        event_id = request.data.get("event_id")
        if event_id:
            try:
                event = Event.objects.get(id=event_id)
                round_num = request.data.get("round", 1)
                num_in_bracket = request.data.get("num_in_bracket", 1)
                is_bye = request.data.get("is_bye", False)
                extra_info = request.data.get("extra_info", {})

                event_match = EventMatch.objects.create(
                    match=match,
                    event=event,
                    round=round_num,
                    num_in_bracket=num_in_bracket,
                    is_bye=is_bye,
                    extra_info=extra_info,
                )
            except Event.DoesNotExist:
                # Clean up the match if event creation fails
                match.delete()
                return Response(
                    {"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # Update ELOs if the match is completed and has a winner
        if match.status == "completed" and match.winner:
            update_match_elos(match)

        # Return the created match
        winner_data = None
        if match.winner:
            winner_data = {
                "id": match.winner.id,
                "name": match.winner.name,
            }

        event_match_data = None
        if event_match:
            event_match_data = {
                "id": event_match.id,
                "event": {
                    "id": event_match.event.id,
                    "name": event_match.event.name,
                },
                "round": event_match.round,
                "num_in_bracket": event_match.num_in_bracket,
                "is_bye": event_match.is_bye,
            }

        result = {
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
            "winner": winner_data,
            "score_team1": match.score_team1,
            "score_team2": match.score_team2,
            "elo": match_elo_data(match),
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
            "event_match": event_match_data,
        }

        return Response(result, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def create_event_match(request):
    """
    Create a new match specifically for an event

    Expected request format:
    {
        "team1_id": "uuid",
        "team2_id": "uuid",
        "event_id": "uuid",
        "round": 1,
        "num_in_bracket": 1,
        "date": "2025-01-01T15:00:00Z",  // Optional
        "status": "scheduled",  // Optional
        "url": "https://example.com",  // Optional
        "score_team1": 0,  // Optional
        "score_team2": 0,  // Optional
        "platform": "other",  // Optional
        "season_id": "uuid",  // Optional
        "competition_id": "uuid",  // Optional
        "winner_id": "uuid",  // Optional
        "is_bye": false,  // Optional
        "extra_info": {}  // Optional - JSON object for additional match info (round name, etc.)
    }
    """
    try:
        # Required fields
        team1_id = request.data.get("team1_id")
        team2_id = request.data.get("team2_id")
        event_id = request.data.get("event_id")
        round_num = request.data.get("round")
        num_in_bracket = request.data.get("num_in_bracket")

        if not all([team1_id, team2_id, event_id, round_num, num_in_bracket]):
            return Response(
                {
                    "error": "team1_id, team2_id, event_id, round, and num_in_bracket are required"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if team1_id == team2_id:
            return Response(
                {"error": "A team cannot play against itself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get teams and event
        try:
            team1 = Team.objects.get(id=team1_id)
            team2 = Team.objects.get(id=team2_id)
            event = Event.objects.get(id=event_id)
        except Team.DoesNotExist:
            return Response(
                {"error": "One or both teams not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Event.DoesNotExist:
            return Response(
                {"error": "Event not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Optional fields
        date_str = request.data.get("date")
        match_date = None
        if date_str:
            match_date = safe_parse_datetime(date_str)
            if not match_date:
                return Response(
                    {"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST
                )

        match_status = request.data.get("status", "scheduled")
        url = request.data.get("url")
        score_team1 = request.data.get("score_team1", 0)
        score_team2 = request.data.get("score_team2", 0)
        platform = request.data.get("platform", "other")
        is_bye = request.data.get("is_bye", False)
        extra_info = request.data.get("extra_info", {})

        # Optional season and competition
        season = None
        season_id = request.data.get("season_id")
        if season_id:
            try:
                season = Season.objects.get(id=season_id)
            except Season.DoesNotExist:
                return Response(
                    {"error": "Season not found"}, status=status.HTTP_404_NOT_FOUND
                )

        competition = None
        competition_id = request.data.get("competition_id")
        if competition_id:
            try:
                competition = Competition.objects.get(id=competition_id)
            except Competition.DoesNotExist:
                return Response(
                    {"error": "Competition not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # Optional winner
        winner = None
        winner_id = request.data.get("winner_id")
        if winner_id:
            if winner_id == team1_id:
                winner = team1
            elif winner_id == team2_id:
                winner = team2
            else:
                return Response(
                    {"error": "Winner must be one of the two teams in the match"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Create the match
        match = Match.objects.create(
            team1=team1,
            team2=team2,
            date=match_date,
            status=match_status,
            url=url,
            score_team1=score_team1,
            score_team2=score_team2,
            platform=platform,
            season=season,
            competition=competition,
            winner=winner,
        )

        # Create EventMatch
        event_match = EventMatch.objects.create(
            match=match,
            event=event,
            round=round_num,
            num_in_bracket=num_in_bracket,
            is_bye=is_bye,
            extra_info=extra_info,
        )

        # Update ELOs if the match is completed and has a winner
        if match.status == "completed" and match.winner:
            update_match_elos(match)

        # Return the created match with event match data
        winner_data = None
        if match.winner:
            winner_data = {
                "id": match.winner.id,
                "name": match.winner.name,
            }

        event_match_data = {
            "id": event_match.id,
            "event": {
                "id": event_match.event.id,
                "name": event_match.event.name,
            },
            "round": event_match.round,
            "num_in_bracket": event_match.num_in_bracket,
            "is_bye": event_match.is_bye,
        }

        result = {
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
            "winner": winner_data,
            "score_team1": match.score_team1,
            "score_team2": match.score_team2,
            "elo": match_elo_data(match),
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
            "event_match": event_match_data,
        }

        return Response(result, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PUT", "PATCH"])
@firebase_auth_required(min_role="admin")
def update_event_match(request, match_id):
    """
    Update an existing event match

    PUT: Full update (all fields required except optional ones)
    PATCH: Partial update (only provided fields will be updated)

    Expected request format (same as create_event_match):
    {
        "team1_id": "uuid",  // Required for PUT, optional for PATCH
        "team2_id": "uuid",  // Required for PUT, optional for PATCH
        "event_id": "uuid",  // Required for PUT, optional for PATCH
        "round": 1,  // Required for PUT, optional for PATCH
        "num_in_bracket": 1,  // Required for PUT, optional for PATCH
        "date": "2025-01-01T15:00:00Z",  // Optional
        "status": "scheduled",  // Optional
        "url": "https://example.com",  // Optional
        "score_team1": 0,  // Optional
        "score_team2": 0,  // Optional
        "platform": "other",  // Optional
        "season_id": "uuid",  // Optional
        "competition_id": "uuid",  // Optional
        "winner_id": "uuid",  // Optional
        "is_bye": false,  // Optional
        "extra_info": {}  // Optional - JSON object for additional match info
    }
    """
    try:
        match = get_object_or_404(Match, id=match_id)
        event_match = get_object_or_404(EventMatch, match=match)
        is_full_update = request.method == "PUT"


        # Handle team updates
        team1_id = request.data.get("team1_id")
        team2_id = request.data.get("team2_id")

        if is_full_update and (not team1_id or not team2_id):
            return Response(
                {"error": "team1_id and team2_id are required for full update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if team1_id and team2_id and team1_id == team2_id:
            return Response(
                {"error": "A team cannot play against itself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if team1_id:
            try:
                match.team1 = Team.objects.get(id=team1_id)
            except Team.DoesNotExist:
                return Response(
                    {"error": "Team1 not found"}, status=status.HTTP_404_NOT_FOUND
                )

        if team2_id:
            try:
                match.team2 = Team.objects.get(id=team2_id)
            except Team.DoesNotExist:
                return Response(
                    {"error": "Team2 not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # Handle event update
        event_id = request.data.get("event_id")
        if is_full_update and not event_id:
            return Response(
                {"error": "event_id is required for full update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if event_id:
            try:
                event_match.event = Event.objects.get(id=event_id)
            except Event.DoesNotExist:
                return Response(
                    {"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # Handle EventMatch specific fields
        if "round" in request.data:
            if is_full_update and request.data["round"] is None:
                return Response(
                    {"error": "round is required for full update"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            event_match.round = request.data["round"]

        if "num_in_bracket" in request.data:
            if is_full_update and request.data["num_in_bracket"] is None:
                return Response(
                    {"error": "num_in_bracket is required for full update"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            event_match.num_in_bracket = request.data["num_in_bracket"]

        if "is_bye" in request.data:
            event_match.is_bye = request.data["is_bye"]

        if "extra_info" in request.data:
            event_match.extra_info = request.data["extra_info"]

        # Handle date update
        if "date" in request.data:
            date_str = request.data["date"]
            if date_str:
                match_date = safe_parse_datetime(date_str)
                if not match_date:
                    return Response(
                        {"error": "Invalid date format"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                match.date = match_date
            elif not is_full_update:  # Only allow None for PATCH requests
                match.date = timezone.now()

        # Handle other Match field updates
        if "status" in request.data:
            match.status = request.data["status"]

        if "url" in request.data:
            match.url = request.data["url"]

        if "score_team1" in request.data:
            match.score_team1 = request.data["score_team1"]

        if "score_team2" in request.data:
            match.score_team2 = request.data["score_team2"]

        if "platform" in request.data:
            match.platform = request.data["platform"]

        # Handle season update
        if "season_id" in request.data:
            season_id = request.data["season_id"]
            if season_id:
                try:
                    season_obj = Season.objects.get(id=season_id)
                    match.season = season_obj  # type: ignore
                except Season.DoesNotExist:
                    return Response(
                        {"error": "Season not found"}, status=status.HTTP_404_NOT_FOUND
                    )
            else:
                match.season = None

        # Handle competition update
        if "competition_id" in request.data:
            competition_id = request.data["competition_id"]
            if competition_id:
                try:
                    competition_obj = Competition.objects.get(id=competition_id)
                    match.competition = competition_obj  # type: ignore
                except Competition.DoesNotExist:
                    return Response(
                        {"error": "Competition not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                match.competition = None

        # Handle winner update
        if "winner_id" in request.data:
            winner_id = request.data["winner_id"]
            if winner_id:
                if winner_id == str(match.team1.id):
                    match.winner = match.team1
                elif winner_id == str(match.team2.id):
                    match.winner = match.team2
                else:
                    return Response(
                        {"error": "Winner must be one of the two teams in the match"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                match.winner = None

        # Save both objects, reverting/applying Elo if the outcome changed
        with transaction.atomic():
            elo_warning = save_match_and_sync_elo(match)
            event_match.save()

        # Return the updated match with event match data
        winner_data = None
        if match.winner:
            winner_data = {
                "id": match.winner.id,
                "name": match.winner.name,
            }

        event_match_data = {
            "id": event_match.id,
            "event": {
                "id": event_match.event.id,
                "name": event_match.event.name,
            },
            "round": event_match.round,
            "num_in_bracket": event_match.num_in_bracket,
            "is_bye": event_match.is_bye,
            "extra_info": event_match.extra_info,
        }

        result = {
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
            "winner": winner_data,
            "score_team1": match.score_team1,
            "score_team2": match.score_team2,
            "elo": match_elo_data(match),
            "elo_warning": elo_warning,
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
            "event_match": event_match_data,
        }

        return Response(result)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PUT", "PATCH"])
@firebase_auth_required(min_role="admin")
def update_match(request, match_id):
    """
    Update an existing match

    PUT: Full update (all fields required except optional ones)
    PATCH: Partial update (only provided fields will be updated)

    Expected request format (same as create_match):
    {
        "team1_id": "uuid",  // Required for PUT, optional for PATCH
        "team2_id": "uuid",  // Required for PUT, optional for PATCH
        "date": "2025-01-01T15:00:00Z",  // Optional
        "status": "completed",
        "url": "https://example.com",
        "score_team1": 2,
        "score_team2": 1,
        "platform": "faceit",
        "season_id": "uuid",
        "competition_id": "uuid",
        "winner_id": "uuid"
    }
    """
    try:
        match = get_object_or_404(Match, id=match_id)
        is_full_update = request.method == "PUT"


        # Handle team updates
        team1_id = request.data.get("team1_id")
        team2_id = request.data.get("team2_id")

        if is_full_update and (not team1_id or not team2_id):
            return Response(
                {"error": "team1_id and team2_id are required for full update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if team1_id and team2_id and team1_id == team2_id:
            return Response(
                {"error": "A team cannot play against itself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if team1_id:
            try:
                match.team1 = Team.objects.get(id=team1_id)
            except Team.DoesNotExist:
                return Response(
                    {"error": "Team1 not found"}, status=status.HTTP_404_NOT_FOUND
                )

        if team2_id:
            try:
                match.team2 = Team.objects.get(id=team2_id)
            except Team.DoesNotExist:
                return Response(
                    {"error": "Team2 not found"}, status=status.HTTP_404_NOT_FOUND
                )

        # Handle date update
        if "date" in request.data:
            date_str = request.data["date"]
            if date_str:
                match_date = safe_parse_datetime(date_str)
                if not match_date:
                    return Response(
                        {"error": "Invalid date format"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                match.date = match_date
            elif not is_full_update:  # Only allow None for PATCH requests
                # For PATCH, if date is explicitly set to null, use current time as fallback
                match.date = timezone.now()

        # Handle other field updates
        if "status" in request.data:
            match.status = request.data["status"]

        if "url" in request.data:
            match.url = request.data["url"]

        if "score_team1" in request.data:
            match.score_team1 = request.data["score_team1"]

        if "score_team2" in request.data:
            match.score_team2 = request.data["score_team2"]

        if "platform" in request.data:
            match.platform = request.data["platform"]

        # Handle season update
        if "season_id" in request.data:
            season_id = request.data["season_id"]
            if season_id:
                try:
                    season_obj = Season.objects.get(id=season_id)
                    match.season = season_obj  # type: ignore
                except Season.DoesNotExist:
                    return Response(
                        {"error": "Season not found"}, status=status.HTTP_404_NOT_FOUND
                    )
            else:
                match.season = None

        # Handle competition update
        if "competition_id" in request.data:
            competition_id = request.data["competition_id"]
            if competition_id:
                try:
                    competition_obj = Competition.objects.get(id=competition_id)
                    match.competition = competition_obj  # type: ignore
                except Competition.DoesNotExist:
                    return Response(
                        {"error": "Competition not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                match.competition = None

        # Handle winner update
        if "winner_id" in request.data:
            winner_id = request.data["winner_id"]
            if winner_id:
                if winner_id == str(match.team1.id):
                    match.winner = match.team1
                elif winner_id == str(match.team2.id):
                    match.winner = match.team2
                else:
                    return Response(
                        {"error": "Winner must be one of the two teams in the match"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                match.winner = None

        # Save the match, reverting/applying Elo if the outcome changed
        elo_warning = save_match_and_sync_elo(match)

        # Return the updated match
        winner_data = None
        if match.winner:
            winner_data = {
                "id": match.winner.id,
                "name": match.winner.name,
            }

        result = {
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
            "winner": winner_data,
            "score_team1": match.score_team1,
            "score_team2": match.score_team2,
            "elo": match_elo_data(match),
            "elo_warning": elo_warning,
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

        return Response(result)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["DELETE"])
@firebase_auth_required(min_role="admin")
def delete_match(request, match_id):
    """
    Delete a match

    Optional request format:
    {
        "security_key": "confirm-delete-match-456"  // Optional security key for extra protection
    }
    """
    try:
        match = get_object_or_404(Match, id=match_id)

        # Optional security check
        security_key = request.data.get("security_key") if request.data else None
        require_security = getattr(settings, "REQUIRE_MATCH_DELETE_SECURITY", False)

        if require_security and security_key != "confirm-delete-match-456":
            return Response(
                {"error": "Security key required for match deletion"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Store match info for response
        match_info = {
            "id": str(match.id),
            "team1_name": match.team1.name,
            "team2_name": match.team2.name,
            "date": match.date,
            "status": match.status,
        }

        # Undo this match's Elo and delete it
        elo_warning = delete_match_and_revert_elo(match)

        logger.info(
            f"Deleted match {match_info['id']}: {match_info['team1_name']} vs {match_info['team2_name']}"
        )

        return Response(
            {
                "message": f"Successfully deleted match between {match_info['team1_name']} and {match_info['team2_name']}",
                "deleted_match": match_info,
                "elo_warning": elo_warning,
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
