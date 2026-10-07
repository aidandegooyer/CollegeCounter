"""Seasons, competitions and destructive admin operations."""

from django.http import HttpResponse
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ..models import (
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
from ..middleware import firebase_auth_required

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def index(request):
    return HttpResponse("Hello! This is the College Counter backend API.")


@api_view(["GET"])
@firebase_auth_required(min_role="base")
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
@firebase_auth_required(min_role="owner")
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


@api_view(["POST"])
@firebase_auth_required(min_role="owner")
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


@api_view(["DELETE"])
@firebase_auth_required(min_role="owner")
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
@firebase_auth_required(min_role="base")
def list_competitions(request):
    """
    Get all competitions with their associated data counts.
    """
    try:
        competitions = Competition.objects.all()
        result = []

        # Competition has no season FK, so derive it from the participants and
        # matches attached to each competition (3 queries total, not per-row).
        season_ids_by_competition = defaultdict(set)
        for source in (Participant, Match):
            for competition_id, season_id in (
                source.objects.filter(
                    competition__isnull=False, season__isnull=False
                )
                .values_list("competition_id", "season_id")
                .distinct()
            ):
                season_ids_by_competition[competition_id].add(season_id)

        season_names = dict(Season.objects.values_list("id", "name"))

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

            seasons = sorted(
                (
                    {"id": str(season_id), "name": season_names[season_id]}
                    for season_id in season_ids_by_competition.get(competition.id, ())
                    if season_id in season_names
                ),
                key=lambda season: season["name"],
            )

            result.append(
                {
                    "id": str(competition.id),
                    "name": competition.name,
                    "participants_count": participants_count,
                    "matches_count": matches_count,
                    "teams_count": teams_count,
                    "seasons": seasons,
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
