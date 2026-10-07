"""Team Elo calculation, recalculation and ranking snapshots."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import models, transaction
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


ELO_FIELDS_CLEARED = {
    "elo_applied": False,
    "team1_elo_before": None,
    "team2_elo_before": None,
    "team1_elo_change": None,
    "team2_elo_change": None,
}


def _lock_teams(*team_ids):
    """Lock team rows in a consistent order and return them keyed by id."""
    teams = Team.objects.select_for_update().filter(id__in=team_ids).order_by("id")
    return {team.id: team for team in teams}


def match_elo_data(match):
    """Elo bookkeeping for a match, as returned by the API."""
    return {
        "applied": match.elo_applied,
        "team1_before": match.team1_elo_before,
        "team2_before": match.team2_elo_before,
        "team1_change": match.team1_elo_change,
        "team2_change": match.team2_elo_change,
    }


def update_match_elos(match):
    """
    Apply a completed match's result to both teams' Elo and record the
    before/change values on the match.

    Idempotent: does nothing if the match has already been applied. The match
    must already be saved.

    Args:
        match (Match): The completed match to process

    Returns:
        bool: True if ELOs were updated, False otherwise
    """
    if match.status != "completed" or match.winner_id is None:
        return False
    if match.winner_id not in (match.team1_id, match.team2_id):
        return False

    with transaction.atomic():
        if Match.objects.select_for_update().get(pk=match.pk).elo_applied:
            match.elo_applied = True
            return False

        teams = _lock_teams(match.team1_id, match.team2_id)
        team1, team2 = teams[match.team1_id], teams[match.team2_id]

        # Results: 1.0 for win, 0.0 for loss
        team1_result = 1.0 if match.winner_id == team1.id else 0.0
        new_team1_elo = calculate_new_elo(team1.elo, team2.elo, team1_result)
        new_team2_elo = calculate_new_elo(team2.elo, team1.elo, 1.0 - team1_result)

        fields = {
            "elo_applied": True,
            "team1_elo_before": team1.elo,
            "team2_elo_before": team2.elo,
            "team1_elo_change": new_team1_elo - team1.elo,
            "team2_elo_change": new_team2_elo - team2.elo,
        }
        Match.objects.filter(pk=match.pk).update(**fields)
        for name, value in fields.items():
            setattr(match, name, value)

        team1.elo = new_team1_elo
        team2.elo = new_team2_elo
        team1.save(update_fields=["elo"])
        team2.save(update_fields=["elo"])
        # Keep the caller's cached team objects in sync
        match.team1, match.team2 = team1, team2

    logger.info(
        f"Updated ELOs for match {match.id}: "
        f"{team1.name} {fields['team1_elo_before']}→{new_team1_elo}, "
        f"{team2.name} {fields['team2_elo_before']}→{new_team2_elo}"
    )

    return True


def revert_match_elos(match):
    """
    Undo a match's applied Elo by subtracting the recorded changes from the
    teams it was applied to, and clear the match's Elo fields.

    Uses the teams stored in the database, not the in-memory match, so it is
    safe to call after editing match.team1/team2 but before saving.

    Elo is path-dependent: reverting an older match doesn't re-derive later
    matches. Run a full recalculation when exact history matters.

    Returns:
        bool: True if Elo was reverted, False if nothing was applied or the
        match was applied before change tracking existed.
    """
    with transaction.atomic():
        row = Match.objects.select_for_update().filter(pk=match.pk).first()
        if row is None or not row.elo_applied:
            return False
        if row.team1_elo_change is None or row.team2_elo_change is None:
            logger.warning(
                f"Match {match.id} had Elo applied before change tracking; "
                f"can't revert it. Run an Elo recalculation to correct ratings."
            )
            return False

        teams = _lock_teams(row.team1_id, row.team2_id)
        teams[row.team1_id].elo -= row.team1_elo_change
        teams[row.team2_id].elo -= row.team2_elo_change
        for team in teams.values():
            team.save(update_fields=["elo"])

        Match.objects.filter(pk=match.pk).update(**ELO_FIELDS_CLEARED)
        for name, value in ELO_FIELDS_CLEARED.items():
            setattr(match, name, value)

    logger.info(
        f"Reverted ELOs for match {match.id}: "
        f"team1 {-row.team1_elo_change:+d}, team2 {-row.team2_elo_change:+d}"
    )
    return True


def revert_match_elos_if_outcome_changed(match):
    """
    Call before saving edits to a match. If its applied Elo no longer matches
    the edited outcome (no longer completed, or different teams/winner),
    revert it so update_match_elos can re-apply after the save.

    Returns:
        bool: True if Elo was reverted.
    """
    if not match.elo_applied:
        return False
    saved = (
        Match.objects.filter(pk=match.pk)
        .values("team1_id", "team2_id", "winner_id")
        .first()
    )
    if saved is None:
        return False
    unchanged = match.status == "completed" and saved == {
        "team1_id": match.team1_id,
        "team2_id": match.team2_id,
        "winner_id": match.winner_id,
    }
    if unchanged:
        return False
    return revert_match_elos(match)


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
    # Reset all team ELOs to default if requested. Otherwise matches that are
    # already applied are skipped, so this only applies the ones that aren't.
    if reset_to_default:
        Team.objects.all().update(elo=default_elo)
        Match.objects.update(**ELO_FIELDS_CLEARED)
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

        if match.elo_applied:
            return Response(
                {"error": "Elo has already been applied for this match"},
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
@firebase_auth_required(min_role="admin")
def revert_match_elo(request, match_id):
    """
    Undo the Elo applied for one match, using the changes recorded when it was
    applied. Later matches are not recalculated.
    """
    try:
        match = get_object_or_404(Match, id=match_id)

        if not match.elo_applied:
            return Response(
                {"error": "Elo has not been applied for this match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if match.team1_elo_change is None or match.team2_elo_change is None:
            return Response(
                {
                    "error": "This match's Elo was applied before changes were "
                    "tracked, so it can't be reverted. Run an Elo recalculation instead."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        team1_change = match.team1_elo_change
        team2_change = match.team2_elo_change
        revert_match_elos(match)
        match.team1.refresh_from_db(fields=["elo"])
        match.team2.refresh_from_db(fields=["elo"])

        return Response(
            {
                "message": "Match Elo reverted successfully",
                "match_id": str(match.id),
                "team1": {
                    "id": str(match.team1.id),
                    "name": match.team1.name,
                    "reverted_change": team1_change,
                    "new_elo": match.team1.elo,
                },
                "team2": {
                    "id": str(match.team2.id),
                    "name": match.team2.name,
                    "reverted_change": team2_change,
                    "new_elo": match.team2.elo,
                },
            }
        )
    except Exception as e:
        logger.error(f"Error reverting Elo for match {match_id}: {str(e)}")
        return Response(
            {"error": f"Failed to revert match Elo: {str(e)}"},
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
