from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Team, Player
from .middleware import firebase_auth_required
import uuid
import json
import os
import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase Storage (this would typically be done in your app's initialization)
# This assumes you've added the Firebase credentials to your Django settings
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_ADMIN_CREDENTIAL)
    firebase_admin.initialize_app(
        cred, {"storageBucket": "college-counter-9057f.firebasestorage.app"}
    )


@csrf_exempt
@require_http_methods(["POST"])
@firebase_auth_required
def upload_team_picture(request, team_id):
    """
    Upload a team picture to Firebase Storage and update the team's picture URL
    """
    try:
        team = Team.objects.get(id=team_id)

        # Get file from request
        picture = request.FILES.get("picture")
        if not picture:
            return JsonResponse({"error": "No picture provided"}, status=400)

        # Create a unique filename
        extension = os.path.splitext(picture.name)[1]
        filename = f"teams/{team_id}_{uuid.uuid4()}{extension}"

        # Upload to Firebase Storage
        bucket = storage.bucket()
        blob = bucket.blob(filename)

        # Set content type based on file extension
        content_type = f"image/{extension.lstrip('.')}"
        blob.content_type = content_type

        # Upload the file
        blob.upload_from_file(picture)

        # Make the blob publicly accessible
        blob.make_public()

        # Get the public URL
        picture_url = blob.public_url

        # Update the team's picture URL
        team.picture = picture_url
        team.save()

        return JsonResponse(
            {
                "message": "Team picture uploaded successfully",
                "picture_url": picture_url,
            }
        )

    except Team.DoesNotExist:
        return JsonResponse({"error": "Team not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@firebase_auth_required
def upload_player_picture(request, player_id):
    """
    Upload a player picture to Firebase Storage and update the player's picture URL
    """
    try:
        player = Player.objects.get(id=player_id)

        # Get file from request
        picture = request.FILES.get("picture")
        if not picture:
            return JsonResponse({"error": "No picture provided"}, status=400)

        # Create a unique filename
        extension = os.path.splitext(picture.name)[1]
        filename = f"players/{player_id}_{uuid.uuid4()}{extension}"

        # Upload to Firebase Storage
        bucket = storage.bucket("college-counter-9057f.firebasestorage.app")
        blob = bucket.blob(filename)

        # Set content type based on file extension
        content_type = f"image/{extension.lstrip('.')}"
        blob.content_type = content_type

        # Upload the file
        blob.upload_from_file(picture)

        # Make the blob publicly accessible
        blob.make_public()

        # Get the public URL
        picture_url = blob.public_url

        # Update the player's picture URL
        player.picture = picture_url
        player.save()

        return JsonResponse(
            {
                "message": "Player picture uploaded successfully",
                "picture_url": picture_url,
            }
        )

    except Player.DoesNotExist:
        return JsonResponse({"error": "Player not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
@firebase_auth_required
def update_team(request, team_id):
    """
    Update a team's details
    """
    try:
        team = Team.objects.get(id=team_id)
        data = json.loads(request.body)

        # Update fields
        if "name" in data:
            team.name = data["name"]
        if "school_name" in data:
            team.school_name = data["school_name"]
        if "elo" in data:
            team.elo = data["elo"]

        team.save()

        return JsonResponse(
            {
                "message": "Team updated successfully",
                "team": {
                    "id": str(team.id),
                    "name": team.name,
                    "school_name": team.school_name,
                    "elo": team.elo,
                    "picture": team.picture,
                },
            }
        )

    except Team.DoesNotExist:
        return JsonResponse({"error": "Team not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
@firebase_auth_required
def update_player(request, player_id):
    """
    Update a player's details
    """
    try:
        player = Player.objects.get(id=player_id)
        data = json.loads(request.body)

        # Update fields
        if "name" in data:
            player.name = data["name"]
        if "steam_id" in data:
            player.steam_id = data["steam_id"]
        if "faceit_id" in data:
            player.faceit_id = data["faceit_id"]
        if "elo" in data:
            player.elo = data["elo"]
        if "skill_level" in data:
            player.skill_level = data["skill_level"]
        if "team_id" in data:
            if data["team_id"]:
                try:
                    team = Team.objects.get(id=data["team_id"])
                    player.team = team
                except Team.DoesNotExist:
                    return JsonResponse({"error": "Team not found"}, status=400)
            else:
                player.team = None
        if "benched" in data:
            player.benched = data["benched"]
        if "visible" in data:
            player.visible = data["visible"]

        player.save()

        return JsonResponse(
            {
                "message": "Player updated successfully",
                "player": {
                    "id": str(player.id),
                    "name": player.name,
                    "steam_id": player.steam_id,
                    "faceit_id": player.faceit_id,
                    "elo": player.elo,
                    "skill_level": player.skill_level,
                    "team": {"id": str(player.team.id), "name": player.team.name}
                    if player.team
                    else None,
                    "benched": player.benched,
                    "visible": player.visible,
                    "picture": player.picture,
                },
            }
        )

    except Player.DoesNotExist:
        return JsonResponse({"error": "Player not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
