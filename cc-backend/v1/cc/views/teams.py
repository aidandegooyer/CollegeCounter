"""Admin team/player listing, team merging and player Elo."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status
from ..models import (
    Team,
    Player,
    Match,
    Participant,
)
from ..middleware import firebase_auth_required

import logging
import requests

logger = logging.getLogger(__name__)


@api_view(["GET"])
@firebase_auth_required(min_role="base")
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
@firebase_auth_required(min_role="base")
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


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
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
                        updated_count += 1
                        print(f"Updated {updated_count} of {players.count()} players")
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
@firebase_auth_required(min_role="owner")
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


@api_view(["POST"])
@firebase_auth_required(min_role="owner")
def merge_teams(request):
    """
    Merge two teams into one, combining rosters and transferring all match history.

    Expected request format:
    {
        "primary_team_id": "uuid",    // Team to keep
        "secondary_team_id": "uuid",  // Team to merge into primary (will be deleted)
        "keep_secondary_elo": false   // Optional: give primary team the secondary team's ELO
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
        keep_secondary_elo = bool(request.data.get("keep_secondary_elo", False))

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

        # 4. Optionally carry over the secondary team's ELO
        if keep_secondary_elo:
            logger.info(
                f"Setting {primary_team.name} ELO from {primary_team.elo} to "
                f"{secondary_team.elo} (from {secondary_team.name})"
            )
            primary_team.elo = secondary_team.elo
            primary_team.save(update_fields=["elo"])

        # 5. Store secondary team info for response, then delete it
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
                "elo": primary_team.elo,
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
