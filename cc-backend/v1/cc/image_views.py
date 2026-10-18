"""Admin picture uploads for teams, players and events, stored by cc.images."""

import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .images import MAX_BYTES, ImageError, StorageError, is_configured, store_picture
from .middleware import firebase_auth_required
from .models import CustomEvent, Player, Team

logger = logging.getLogger(__name__)


def _upload(request, kind, obj):
    """Store the multipart `picture` file as obj's picture."""
    if not is_configured():
        return Response(
            {"error": "Image storage isn't configured"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    picture = request.FILES.get("picture")
    if not picture:
        return Response(
            {"error": "No picture provided"}, status=status.HTTP_400_BAD_REQUEST
        )
    # Checked before reading so an oversized upload never sits in memory
    if picture.size > MAX_BYTES:
        return Response(
            {"error": f"Picture is over {MAX_BYTES // (1024 * 1024)} MB"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        url = store_picture(kind, obj.pk, picture.read())
    except ImageError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except StorageError:
        logger.exception("Couldn't store a %s picture", kind)
        return Response(
            {"error": "Couldn't save the picture"}, status=status.HTTP_502_BAD_GATEWAY
        )

    obj.picture = url
    obj.save(update_fields=["picture"])
    return Response({"message": "Picture uploaded", "picture_url": url})


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def upload_team_picture(request, team_id):
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return Response({"error": "Team not found"}, status=status.HTTP_404_NOT_FOUND)
    return _upload(request, "teams", team)


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def upload_player_picture(request, player_id):
    try:
        player = Player.objects.get(id=player_id)
    except Player.DoesNotExist:
        return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)
    return _upload(request, "players", player)


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def upload_event_picture(request, custom_event_id):
    try:
        event = (
            CustomEvent.objects.select_related("event").get(id=custom_event_id).event
        )
    except CustomEvent.DoesNotExist:
        return Response(
            {"error": "Custom event not found"}, status=status.HTTP_404_NOT_FOUND
        )
    return _upload(request, "events", event)
