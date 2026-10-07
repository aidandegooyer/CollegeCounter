"""Team Elo calculation, recalculation and ranking snapshots."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import models
from django.shortcuts import get_object_or_404
from ..models import (
    Team,
    Player,
    Match,
    Season,
    Participant,
    Ranking,
    RankingItem,
)
from ..middleware import firebase_auth_required

import logging
import statistics

logger = logging.getLogger(__name__)


def calculate_new_elo(current_elo, opponent_elo, result):
    """
    Calculate new ELO rating after a match.

    Args:
        current_elo (int): Current ELO of the team
        opponent_elo (int): ELO of the opponent team
        result (float): Match result (1.0 for win, 0.0 for loss, 0.5 for draw)

    Returns:
        int: New ELO rating
    """
    k = 150  # K-factor, determines the maximum possible adjustment per game
    expected_score = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 800))
    new_elo = current_elo + k * (result - expected_score)
    return round(new_elo)


def update_match_elos(match):
    """
    Update team ELOs based on match result.
    Only updates if the match is completed and has a winner.

    Args:
        match (Match): The completed match to process

    Returns:
        bool: True if ELOs were updated, False otherwise
    """
    if match.status != "completed" or not match.winner:
        return False

    # Get current ELOs
    team1_elo = match.team1.elo
    team2_elo = match.team2.elo

    # Determine results (1.0 for win, 0.0 for loss)
    if match.winner == match.team1:
        team1_result = 1.0
        team2_result = 0.0
    elif match.winner == match.team2:
        team1_result = 0.0
        team2_result = 1.0
    else:
        return False

    # Calculate new ELOs
    new_team1_elo = calculate_new_elo(team1_elo, team2_elo, team1_result)
    new_team2_elo = calculate_new_elo(team2_elo, team1_elo, team2_result)

    # Update teams
    match.team1.elo = new_team1_elo
    match.team2.elo = new_team2_elo
    match.team1.save()
    match.team2.save()

    logger.info(
        f"Updated ELOs for match {match.id}: {match.team1.name} {team1_elo}→{new_team1_elo}, {match.team2.name} {team2_elo}→{new_team2_elo}"
    )

    return True


def recalculate_all_elos(reset_to_default=False, default_elo=1000):
    """
    Recalculate ELO ratings for all teams based on completed matches in chronological order.
    This is useful when importing historical match data.

    Args:
        reset_to_default (bool): Whether to reset all team ELOs to default before recalculating
        default_elo (int): Default ELO to reset teams to if reset_to_default is True

    Returns:
        dict: Summary of the recalculation process
    """
    # Reset all team ELOs to default if requested
    if reset_to_default:
        Team.objects.all().update(elo=default_elo)
        logger.info(f"Reset all team ELOs to {default_elo}")

    # Get all completed matches with winners, ordered by date
    completed_matches = (
        Match.objects.filter(status="completed", winner__isnull=False)
        .exclude(
            models.Q(team1__name__iexact="bye") | models.Q(team2__name__iexact="bye")
        )
        .order_by("date")
    )

    processed_count = 0
    error_count = 0
    elo_changes = []

    for match in completed_matches:
        try:
            # Store ELOs before update for logging
            old_team1_elo = match.team1.elo
            old_team2_elo = match.team2.elo

            # Update ELOs for this match
            if update_match_elos(match):
                processed_count += 1

                # Log the change
                elo_changes.append(
                    {
                        "match_id": str(match.id),
                        "date": match.date.isoformat() if match.date else None,
                        "team1": match.team1.name,
                        "team2": match.team2.name,
                        "winner": match.winner.name if match.winner else "Unknown",
                        "team1_elo_change": f"{old_team1_elo} → {match.team1.elo}",
                        "team2_elo_change": f"{old_team2_elo} → {match.team2.elo}",
                    }
                )

                logger.info(
                    f"Processed match {match.id}: {match.team1.name} vs {match.team2.name}, "
                    f"winner: {match.winner.name if match.winner else 'Unknown'}, "
                    f"ELO changes: {match.team1.name} {old_team1_elo}→{match.team1.elo}, "
                    f"{match.team2.name} {old_team2_elo}→{match.team2.elo}"
                )
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing match {match.id}: {str(e)}")

    return {
        "total_matches": completed_matches.count(),
        "processed_count": processed_count,
        "error_count": error_count,
        "reset_to_default": reset_to_default,
        "default_elo": default_elo if reset_to_default else None,
        "elo_changes": elo_changes,
    }


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def apply_match_elo(request, match_id):
    """
    Apply Elo calculation for one match using the two teams' current Elo values.
    This does not recalculate historical matches.
    """
    try:
        match = get_object_or_404(Match, id=match_id)

        if match.status != "completed" or not match.winner:
            return Response(
                {"error": "Match must be completed and have a winner to apply Elo"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_team1_elo = match.team1.elo
        old_team2_elo = match.team2.elo

        updated = update_match_elos(match)
        if not updated:
            return Response(
                {"error": "Unable to apply Elo for this match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Match Elo applied successfully",
                "match_id": str(match.id),
                "team1": {
                    "id": str(match.team1.id),
                    "name": match.team1.name,
                    "old_elo": old_team1_elo,
                    "new_elo": match.team1.elo,
                },
                "team2": {
                    "id": str(match.team2.id),
                    "name": match.team2.name,
                    "old_elo": old_team2_elo,
                    "new_elo": match.team2.elo,
                },
                "winner_id": str(match.winner.id),
            }
        )
    except Exception as e:
        logger.error(f"Error applying Elo for match {match_id}: {str(e)}")
        return Response(
            {"error": f"Failed to apply match Elo: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@firebase_auth_required(min_role="owner")
def recalculate_elos(request):
    """
    Recalculate ELO ratings for all teams based on completed matches in chronological order.
    This is useful when importing historical match data.

    Expected request format:
    {
        "reset_to_default": true, // Optional - default true
        "default_elo": 1000 // Optional - default 1000
    }
    """
    try:
        reset_to_default = request.data.get("reset_to_default", True)
        default_elo = request.data.get("default_elo", 1000)

        result = recalculate_all_elos(
            reset_to_default=reset_to_default, default_elo=default_elo
        )

        return Response(
            {
                "message": "ELO recalculation completed successfully",
                "summary": {
                    "total_matches": result["total_matches"],
                    "processed_count": result["processed_count"],
                    "error_count": result["error_count"],
                    "reset_to_default": result["reset_to_default"],
                    "default_elo": result["default_elo"],
                },
                "elo_changes": result["elo_changes"][:10]
                if len(result["elo_changes"]) > 10
                else result["elo_changes"],  # Limit to first 10 for response size
                "total_elo_changes": len(result["elo_changes"]),
            }
        )

    except Exception as e:
        logger.error(f"Error in recalculate_elos: {str(e)}")
        return Response(
            {"error": f"Failed to recalculate ELOs: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@firebase_auth_required(min_role="owner")
def calculate_team_elos(request):
    """
    Calculate team ELOs based on player ELOs.
    Formula: team_elo = mean(top 5 player ELOs) - 0.1 * std_dev(top 5 player ELOs)

    Expected request format:
    {
        "only_default_elo": true, // Optional - only calculate for teams with default ELO (1000)
        "default_elo": 1000 // Optional - what is considered the default ELO value
    }
    """
    try:
        # Get request parameters
        only_default_elo = request.data.get("only_default_elo", False)
        default_elo = request.data.get("default_elo", 1000)

        # Get teams based on filter
        if only_default_elo:
            teams = Team.objects.filter(elo=default_elo)
        else:
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
                "only_default_elo": only_default_elo,
                "default_elo_value": default_elo,
                "total_teams_processed": teams.count(),
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@firebase_auth_required(min_role="admin")
def create_ranking_snapshot(request):
    """
    Create a ranking snapshot based on current team ELO values.
    This captures the current state of team rankings for historical tracking.

    Optional request format:
    {
        "season_id": "uuid", // Optional - specific season to capture rankings for
        "name": "Custom Snapshot Name" // Optional - custom name for identification
    }
    """
    try:
        season_id = request.data.get("season_id")

        # Get the season if specified, otherwise use the most recent season
        season = None
        if season_id:
            try:
                season = Season.objects.get(id=season_id)
            except Season.DoesNotExist:
                return Response(
                    {"error": f"Season with ID {season_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Use the most recent season if no season specified
            season = Season.objects.order_by("-start_date").first()
            if not season:
                return Response(
                    {"error": "No seasons found in database"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Only rank teams that are active in this season (participant or match),
        # ordered by current ELO descending
        season_matches = Match.objects.filter(season=season)
        teams = (
            Team.objects.filter(elo__gt=0)
            .filter(
                models.Q(
                    id__in=Participant.objects.filter(season=season).values("team_id")
                )
                | models.Q(id__in=season_matches.values("team1_id"))
                | models.Q(id__in=season_matches.values("team2_id"))
            )
            .order_by("-elo")
        )

        if not teams.exists():
            return Response(
                {"error": f"No teams with ELO ratings found in season {season.name}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the ranking record
        ranking = Ranking.objects.create(season=season)

        # Create ranking items for each team
        ranking_items_created = 0
        for rank, team in enumerate(teams, start=1):
            RankingItem.objects.create(
                ranking=ranking, team=team, rank=rank, elo=team.elo
            )
            ranking_items_created += 1

        logger.info(
            f"Created ranking snapshot with {ranking_items_created} teams for season {season.name}"
        )

        return Response(
            {
                "success": True,
                "ranking_id": str(ranking.id),
                "season_name": season.name,
                "teams_ranked": ranking_items_created,
                "snapshot_date": ranking.date.isoformat(),
                "message": f"Ranking snapshot created successfully with {ranking_items_created} teams",
            }
        )

    except Exception as e:
        logger.error(f"Error creating ranking snapshot: {str(e)}")
        return Response(
            {"error": "Failed to create ranking snapshot"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
