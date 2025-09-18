from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid
from .models import Team, Player
from .middleware import firebase_auth_required
import logging

logger = logging.getLogger(__name__)


@api_view(["PUT"])
@firebase_auth_required
def update_team(request, team_id):
    """
    Update team information
    """
    try:
        team = Team.objects.get(id=team_id)

        # Update fields if provided
        if "name" in request.data:
            team.name = request.data["name"]
        if "school_name" in request.data:
            team.school_name = request.data["school_name"]
        if "elo" in request.data:
            team.elo = int(request.data["elo"])

        team.save()

        # Return updated team data
        captain = None
        if team.captain:
            captain = {
                "id": team.captain.id,
                "name": team.captain.name,
                "picture": team.captain.picture,
            }

        team_data = {
            "id": team.id,
            "name": team.name,
            "picture": team.picture,
            "school_name": team.school_name,
            "elo": team.elo,
            "captain": captain,
        }

        return Response({"team": team_data}, status=status.HTTP_200_OK)

    except Team.DoesNotExist:
        return Response(
            {"error": f"Team with id {team_id} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error updating team {team_id}: {str(e)}")
        return Response(
            {"error": f"Failed to update team: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@firebase_auth_required
def upload_team_picture(request, team_id):
    """
    Upload team picture
    """
    try:
        team = Team.objects.get(id=team_id)

        if "picture" not in request.FILES:
            return Response(
                {"error": "No picture file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        picture_file = request.FILES["picture"]

        # Generate a unique filename
        file_extension = os.path.splitext(picture_file.name)[1]
        filename = f"teams/{team_id}_{uuid.uuid4()}{file_extension}"

        # Save the file
        file_path = default_storage.save(filename, ContentFile(picture_file.read()))

        # Update team picture URL
        team.picture = f"/media/{file_path}"
        team.save()

        return Response(
            {"picture_url": team.picture},
            status=status.HTTP_200_OK,
        )

    except Team.DoesNotExist:
        return Response(
            {"error": f"Team with id {team_id} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error uploading team picture {team_id}: {str(e)}")
        return Response(
            {"error": f"Failed to upload picture: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PUT"])
@firebase_auth_required
def update_player(request, player_id):
    """
    Update player information
    """
    try:
        player = Player.objects.get(id=player_id)

        # Update fields if provided
        if "name" in request.data:
            player.name = request.data["name"]
        if "steam_id" in request.data:
            player.steam_id = request.data["steam_id"] or None
        if "faceit_id" in request.data:
            player.faceit_id = request.data["faceit_id"] or None
        if "elo" in request.data:
            player.elo = int(request.data["elo"])
        if "skill_level" in request.data:
            player.skill_level = int(request.data["skill_level"])
        if "team_id" in request.data:
            team_id = request.data["team_id"]
            if team_id:
                try:
                    team = Team.objects.get(id=team_id)
                    player.team = team
                except Team.DoesNotExist:
                    return Response(
                        {"error": f"Team with id {team_id} not found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                player.team = None
        if "benched" in request.data:
            player.benched = bool(request.data["benched"])
        if "visible" in request.data:
            player.visible = bool(request.data["visible"])

        player.save()

        # Return updated player data
        team = None
        if player.team:
            team = {
                "id": player.team.id,
                "name": player.team.name,
                "picture": player.team.picture,
            }

        player_data = {
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

        return Response({"player": player_data}, status=status.HTTP_200_OK)

    except Player.DoesNotExist:
        return Response(
            {"error": f"Player with id {player_id} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error updating player {player_id}: {str(e)}")
        return Response(
            {"error": f"Failed to update player: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@firebase_auth_required
def upload_player_picture(request, player_id):
    """
    Upload player picture
    """
    try:
        player = Player.objects.get(id=player_id)

        if "picture" not in request.FILES:
            return Response(
                {"error": "No picture file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        picture_file = request.FILES["picture"]

        # Generate a unique filename
        file_extension = os.path.splitext(picture_file.name)[1]
        filename = f"players/{player_id}_{uuid.uuid4()}{file_extension}"

        # Save the file
        file_path = default_storage.save(filename, ContentFile(picture_file.read()))

        # Update player picture URL
        player.picture = f"/media/{file_path}"
        player.save()

        return Response(
            {"picture_url": player.picture},
            status=status.HTTP_200_OK,
        )

    except Player.DoesNotExist:
        return Response(
            {"error": f"Player with id {player_id} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        logger.error(f"Error uploading player picture {player_id}: {str(e)}")
        return Response(
            {"error": f"Failed to upload picture: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
