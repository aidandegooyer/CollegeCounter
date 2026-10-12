"""Importing matches and teams from external platforms."""

import uuid
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status
from django.core.exceptions import ValidationError
from django.db import models, transaction
from ..models import (
    Team,
    Player,
    Match,
    Season,
    Participant,
    Competition,
    Event,
    EventMatch,
)
from ..middleware import firebase_auth_required

import difflib
import logging
import re
from collections import Counter
import requests

from .elo import apply_elos_in_date_order
from .utils import safe_parse_datetime

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["POST"])
@firebase_auth_required(min_role="owner")
def import_matches(request):
    """
    Import matches from an external API (Faceit or Playfly or Regents League) into the database.
    Expected request format:
    {
        "platform": "faceit" | "leaguespot" | "regentsleague",
        "competition_name": "string",
        "season_id": "uuid",
        "data": {...}, // API response data
        "participant_matches": { "participant_id" | "platform:{platform}:id:{team key}": "team_id", ... }, // Optional
        "event_id": "uuid", // Optional - if provided, imports as event matches
        "import_type": "league" | "event" // Optional - specifies import type
    }
    """
    try:
        data = request.data
        platform = data.get("platform", "").lower()
        competition_name = data.get("competition_name", "")
        season_id = data.get("season_id")
        api_data = data.get("data", {})
        participant_matches = data.get("participant_matches", {})
        event_id = data.get("event_id")
        import_type = data.get("import_type", "league")

        # Validate everything before writing, so a bad request leaves nothing behind
        if platform not in ("faceit", "leaguespot", "regentsleague"):
            return Response(
                {"error": "Unsupported platform"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get the season
        try:
            season = Season.objects.get(id=season_id)
        except (Season.DoesNotExist, ValidationError):
            return Response(
                {"error": "Season not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get the event if event_id is provided
        event = None
        if event_id:
            try:
                event = Event.objects.get(id=event_id)
            except (Event.DoesNotExist, ValidationError):
                return Response(
                    {"error": "Event not found"}, status=status.HTTP_400_BAD_REQUEST
                )

        # One transaction, so a failure partway (e.g. an ambiguous team name)
        # doesn't leave a half-imported competition whose completed matches are
        # skipped on retry and never get Elo applied
        with transaction.atomic():
            # Create a new competition (do not merge with existing ones with the same name)
            competition = Competition.objects.create(name=competition_name)

            skipped_participant_matches = apply_participant_matches(
                participant_matches, platform, api_data, competition, season
            )

            # Process matches based on platform and import type
            if platform == "regentsleague":
                result = import_regentsleague_match_data(api_data, competition, season)
            else:
                result = import_match_data(
                    api_data,
                    competition,
                    season,
                    platform,
                    event=event,
                    import_type=import_type,
                )

        # Build response message
        total_new = len(result["imported"])
        total_updated = len(result["updated"])
        total_skipped = len(result["skipped"])

        message_parts = []
        if total_new > 0:
            message_parts.append(f"{total_new} new match(es)")
        if total_updated > 0:
            message_parts.append(f"{total_updated} updated")
        if total_skipped > 0:
            message_parts.append(f"{total_skipped} unchanged")

        if not message_parts:
            message = "No matches to import"
        else:
            message = f"Import successful: {', '.join(message_parts)}"

        return Response(
            {
                "message": message,
                "matches_imported": total_new,
                "matches_updated": total_updated,
                "matches_skipped": total_skipped,
                "new_match_ids": result["imported"],
                "updated_match_ids": result["updated"],
                "skipped_match_ids": result["skipped"],
                "skipped_participant_matches": skipped_participant_matches,
            }
        )

    except AmbiguousTeamError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Match import failed")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AmbiguousTeamError(ValueError):
    """An imported team can't be matched by ID and several teams share its name."""


def apply_participant_matches(participant_matches, platform, api_data, competition, season):
    """
    Apply the links chosen in the participant matcher before importing: each
    platform team gets a participant in this competition for the chosen
    existing team, carrying its platform ID, so the import's competition lookup
    (and later rounds' platform ID lookup) finds it. The team's roster is
    imported here too, since the import skips rosters for teams it finds in the
    competition.

    Args:
        participant_matches: {"platform:{platform}:id:{team key}" | participant id: team id}

    Returns:
        list[dict]: picks that couldn't be applied, as {"key", "reason"}.
    """
    skipped = []
    import_teams = None
    # Existing team id -> the platform key already linked to it in this import
    linked_teams = {}

    for participant_id, team_id in (participant_matches or {}).items():
        try:
            team = Team.objects.get(id=team_id)
        except (Team.DoesNotExist, ValidationError):
            skipped.append({"key": participant_id, "reason": "Team not found"})
            continue

        if not participant_id.startswith("platform:"):
            # Regular participant ID
            try:
                participant = Participant.objects.get(id=participant_id)
            except (Participant.DoesNotExist, ValidationError):
                skipped.append({"key": participant_id, "reason": "Participant not found"})
                continue
            participant.team = team
            participant.save()
            continue

        # Format is "platform:{platform}:id:{platform team key}"
        parts = participant_id.split(":", 3)
        if len(parts) != 4 or parts[1] != platform or parts[2] != "id" or not parts[3]:
            skipped.append({"key": participant_id, "reason": "Invalid key"})
            continue
        key = parts[3]
        if platform == "regentsleague" and not key.isdigit():
            skipped.append({"key": participant_id, "reason": "Invalid key"})
            continue

        if team.id in linked_teams:
            skipped.append(
                {
                    "key": participant_id,
                    "reason": f"{team.name} is already linked to another team in this import",
                }
            )
            continue
        linked_teams[team.id] = key

        ids = {
            field: value
            for field, value in platform_team_ids(
                team_data_for_key(platform, key), platform
            ).items()
            if value
        }
        Participant.objects.create(team=team, competition=competition, season=season, **ids)

        if import_teams is None:
            import_teams = extract_import_teams(platform, api_data)
        for player_data in (import_teams.get(key) or {}).get("roster") or []:
            process_player(player_data, team, season)

    for entry in skipped:
        logger.warning(f"Skipped participant match {entry['key']}: {entry['reason']}")
    return skipped


def import_regentsleague_match_data(matches: list[dict], competition, season):
    """
    Process Regents League API data and import matches

    Args:
        matches: The API response data containing match information
        season: Season object

    Returns:
        dict: Contains lists of imported_matches, updated_matches, and skipped_matches
    """
    imported_matches = []
    updated_matches = []
    skipped_matches = []
    created_matches = []

    for match_data in matches:
        regentsleague_match_id = match_data.get("id")
        match_id = uuid.uuid5(
            uuid.NAMESPACE_DNS, f"regentsleague-{regentsleague_match_id}"
        )  # Create a UUID based on the Regents League match ID. In the miniscule offchance this conflicts with an existing ID from a different league out of pure unluckiness I'll do a backflip.
        team1_data: dict = match_data.get("team1")
        team2_data: dict = match_data.get("team2")
        team1_key = team1_data.get("id")
        team2_key = team2_data.get("id")
        team1, _ = get_or_create_team(team1_data, competition, season, "regentsleague")
        team2, _ = get_or_create_team(team2_data, competition, season, "regentsleague")

        if not team1 or not team2:
            continue  # Skip if teams could not be created

        # Extract results if available
        score_team1 = 0
        score_team2 = 0
        winner = None

        status_mapping = {
            "Completed": "completed",
            "In Progress": "in_progress",
            "Scheduled": "scheduled",
            # Add other status mappings as needed
        }
        match_status = status_mapping.get(match_data.get("status"), "scheduled")

        if match_status == "completed":
            score_team1 = match_data.get("score_team1")
            score_team2 = match_data.get("score_team2")

            # The API omits "winner" (or sends null) for some completed matches
            winner_key = (match_data.get("winner") or {}).get("id")
            if winner_key == team1_key:
                winner = team1
            elif winner_key == team2_key:
                winner = team2

        # Check if match already exists
        existing_match = Match.objects.filter(id=match_id).first()

        if existing_match:
            # Skip updating existing matches - only import new matches
            # Updates should be done separately through the update_matches endpoint
            skipped_matches.append(str(existing_match.id))
            logger.info(
                f"Skipped existing match {match_id} - use update endpoint to modify"
            )
            continue  # Move to next match

        # Create the match (only if it doesn't exist)
        match_date = match_data.get("date")
        match = Match.objects.create(
            id=match_id,
            regentsleague_id=regentsleague_match_id,
            team1=team1,
            team2=team2,
            date=safe_parse_datetime(match_date) if match_date else None,
            status=match_status,
            winner=winner,
            score_team1=score_team1,
            score_team2=score_team2,
            platform="regentsleague",
            season=season,
            competition=competition,
        )
        imported_matches.append(str(match.id))
        created_matches.append(match)

    # Matches imported already completed need their result applied to team Elo
    apply_elos_in_date_order(created_matches)

    return {
        "imported": imported_matches,
        "updated": updated_matches,
        "skipped": skipped_matches,
    }


def import_match_data(
    api_data, competition, season, platform, event=None, import_type="league"
):
    """
    Process Faceit/LeagueSpot API data and import matches

    Args:
        api_data: The API response data containing match information
        competition: Competition object
        season: Season object
        platform: Platform name (faceit or leaguespot)
        event: Optional Event object - if provided, creates EventMatch entries
        import_type: Type of import ("league" or "event")

    Returns:
        dict: Contains lists of imported_matches, updated_matches, and skipped_matches
    """
    imported_matches = []
    updated_matches = []
    skipped_matches = []
    created_matches = []

    # Extract matches from the API response
    matches = api_data.get("items", [])

    for match_data in matches:
        # Extract match details
        match_id = match_data.get("match_id")
        faceit_url = match_data.get("faceit_url")
        status_value = match_data.get("status")

        # Remove "1-" prefix from match_id if present
        if match_id and str(match_id).startswith("1-"):
            match_id = str(match_id)[2:]

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
        team1, _ = get_or_create_team(team1_data, competition, season, platform)
        team2, _ = get_or_create_team(team2_data, competition, season, platform)

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

        # Check if match already exists
        existing_match = Match.objects.filter(id=match_id).first()

        if existing_match:
            # Skip updating existing matches - only import new matches
            # Updates should be done separately through the update_matches endpoint
            skipped_matches.append(str(existing_match.id))
            logger.info(
                f"Skipped existing match {match_id} - use update endpoint to modify"
            )

            # For event imports, check if EventMatch exists and create link if needed
            if event and import_type == "event":
                event_match = EventMatch.objects.filter(
                    match=existing_match, event=event
                ).first()

                if not event_match:
                    # Match exists but not linked to this event - create EventMatch
                    # Extract event-specific data from match_data
                    event_metadata = match_data.get("_event_match_metadata", {})

                    if event_metadata and platform == "leaguespot":
                        # Use LeagueSpot round metadata
                        round_num = event_metadata.get("round", 1)
                        num_in_bracket = event_metadata.get(
                            "num_in_bracket", len(imported_matches) + 1
                        )

                        extra_info = {
                            "leaguespot_match_id": match_id,
                            "original_status": status_value,
                            "round_name": event_metadata.get("round_name", ""),
                            "round_state": event_metadata.get("round_state", 0),
                            "best_of": event_metadata.get("best_of", 1),
                        }
                    else:
                        # Faceit or legacy format
                        round_num = match_data.get("round", 1)
                        num_in_bracket = match_data.get(
                            "position", len(imported_matches) + 1
                        )

                        extra_info = {
                            "faceit_match_id": match_id,
                            "faceit_url": faceit_url,
                            "original_status": status_value,
                        }

                        if "round" in match_data:
                            extra_info["round_name"] = match_data.get("round")
                        if "group" in match_data:
                            extra_info["group"] = match_data.get("group")

                    # Check for bye matches
                    is_bye = False
                    team1_name = team1_data.get("name", "").lower()
                    team2_name = team2_data.get("name", "").lower()
                    if team1_name in ["bye", "tbd", "unknown team 1"] or team2_name in [
                        "bye",
                        "tbd",
                        "unknown team 2",
                    ]:
                        is_bye = True

                    EventMatch.objects.create(
                        match=existing_match,
                        event=event,
                        round=round_num,
                        num_in_bracket=num_in_bracket,
                        is_bye=is_bye,
                        extra_info=extra_info,
                    )
                    logger.info(f"Linked existing match {match_id} to event {event.id}")

            continue  # Move to next match

        # Create the match (only if it doesn't exist)
        match = Match.objects.create(
            id=match_id,
            team1=team1,
            team2=team2,
            date=safe_parse_datetime(match_date) if match_date else None,
            status=match_status,
            url=faceit_url,
            winner=winner,
            score_team1=score_team1,
            score_team2=score_team2,
            platform=platform,
            season=season,
            competition=competition,
        )

        # If this is an event import, create an EventMatch entry
        if event and import_type == "event":
            # Extract event-specific data from match_data
            # Check for LeagueSpot event metadata first, then fall back to Faceit
            event_metadata = match_data.get("_event_match_metadata", {})

            if event_metadata and platform == "leaguespot":
                # Use LeagueSpot round metadata
                round_num = event_metadata.get("round", 1)
                num_in_bracket = event_metadata.get(
                    "num_in_bracket", len(imported_matches) + 1
                )

                # Extra info contains LeagueSpot round metadata
                extra_info = {
                    "leaguespot_match_id": match_id,
                    "original_status": status_value,
                    "round_name": event_metadata.get("round_name", ""),
                    "round_state": event_metadata.get("round_state", 0),
                    "best_of": event_metadata.get("best_of", 1),
                }
            else:
                # Faceit or legacy format
                round_num = match_data.get(
                    "round", 1
                )  # Default to round 1 if not provided
                num_in_bracket = match_data.get("position", len(imported_matches) + 1)

                # Extra info can contain bracket-specific data
                extra_info = {
                    "faceit_match_id": match_id,
                    "faceit_url": faceit_url,
                    "original_status": status_value,
                }

                # Add any additional bracket metadata from Faceit
                if "round" in match_data:
                    extra_info["round_name"] = match_data.get("round")
                if "group" in match_data:
                    extra_info["group"] = match_data.get("group")

            # Check for bye matches (TBD or Bye team names)
            is_bye = False
            team1_name = team1_data.get("name", "").lower()
            team2_name = team2_data.get("name", "").lower()
            if team1_name in ["bye", "tbd", "unknown team 1"] or team2_name in [
                "bye",
                "tbd",
                "unknown team 2",
            ]:
                is_bye = True

            # Create EventMatch
            EventMatch.objects.create(
                match=match,
                event=event,
                round=round_num,
                num_in_bracket=num_in_bracket,
                is_bye=is_bye,
                extra_info=extra_info,
            )

        imported_matches.append(str(match.id))
        created_matches.append(match)

    # Matches imported already completed need their result applied to team Elo
    apply_elos_in_date_order(created_matches)

    return {
        "imported": imported_matches,
        "updated": updated_matches,
        "skipped": skipped_matches,
    }


def find_team_by_platform_id(faceit_id=None, playfly_id=None, regentsleague_id=None):
    """
    Find the team linked to a platform team ID through any competition's
    participant record, preferring the most recent season.

    Returns:
        Team | None
    """
    query = models.Q()
    if faceit_id:
        query |= models.Q(faceit_id=faceit_id)
    if playfly_id:
        query |= models.Q(playfly_id=playfly_id)
    if regentsleague_id:
        query |= models.Q(regentsleague_id=regentsleague_id)
    if not query:
        return None

    participant = (
        Participant.objects.filter(query, team__isnull=False)
        .select_related("team")
        .order_by(models.F("season__start_date").desc(nulls_last=True))
        .first()
    )
    return participant.team if participant else None


def platform_team_ids(team_data, platform):
    """
    The participant ID fields an imported team is identified by, as stored on
    Participant.
    """
    ids = {
        "faceit_id": team_data.get("faction_id"),
        "playfly_id": None,
        "playfly_participant_id": None,
        "regentsleague_id": None,
    }
    if platform == "leaguespot":
        ids["playfly_id"] = team_data.get("faction_id") or team_data.get("teamId")
        ids["playfly_participant_id"] = team_data.get("participantId")
    elif platform == "regentsleague":
        ids["regentsleague_id"] = team_data.get("id")
    return ids


def platform_team_key(team_data, platform):
    """The platform's own ID for an imported team, or None if it has none."""
    if platform == "regentsleague":
        key = team_data.get("id")
    else:
        key = team_data.get("faction_id") or team_data.get("teamId")
    return str(key) if key is not None else None


def team_data_for_key(platform, key):
    """
    Minimal team data carrying just a platform team key (see platform_team_key),
    enough for platform_team_ids. Regents League keys must be numeric.
    """
    if platform == "regentsleague":
        return {"id": int(key)}
    return {"faction_id": key}


def find_competition_participant(ids, competition, season):
    """
    The participant in this competition/season matching the given IDs, tried
    in order: Faceit ID, Playfly team ID, Playfly participant ID, Regents
    League ID.
    """
    participants = Participant.objects.filter(competition=competition, season=season)

    # Try Faceit ID first. Playfly IDs are also stored as faceit_id. Only
    # compare non-empty IDs: faceit_id=None would match every participant
    # without one.
    faceit_candidates = [i for i in (ids["faceit_id"], ids["playfly_id"]) if i]
    if ids["faceit_id"]:
        participant = participants.filter(faceit_id__in=faceit_candidates).first()
        if participant:
            return participant

    # Then Playfly team ID, Playfly participant ID and Regents League ID
    for field in ("playfly_id", "playfly_participant_id", "regentsleague_id"):
        if ids[field]:
            participant = participants.filter(**{field: ids[field]}).first()
            if participant:
                return participant
    return None


def resolve_team(team_data, competition, season, platform):
    """
    Find the existing team an imported team maps to, without writing anything.
    Shared by the import and the participant matcher's dry run, so the matcher
    shows exactly the teams the import would create.

    Lookup order: a participant in this competition (competition may be None
    for a dry run), then the team's platform ID from earlier competitions,
    then an exact name match. Picks from the participant matcher are applied
    as participants in the competition before the import runs, so the dry
    run (which has no competition) doesn't see them.

    Returns:
        tuple[Team | None, str]: the team and how it was found: "competition",
        "platform_id" or "name"; or None with "new" (no match) or
        "ambiguous_name" (several teams have that name).
    """
    ids = platform_team_ids(team_data, platform)

    if competition is not None:
        participant = find_competition_participant(ids, competition, season)
        if participant and participant.team:
            return participant.team, "competition"

    # Every import creates a new competition, so on a reimport the lookup above
    # finds nothing. Match the team by its platform ID from earlier competitions
    # before falling back to its name, which may have changed (e.g. a merged
    # team keeps the primary team's name). Playfly participant IDs are
    # per-competition, so they aren't used here.
    team = find_team_by_platform_id(
        faceit_id=ids["faceit_id"],
        playfly_id=ids["playfly_id"],
        regentsleague_id=ids["regentsleague_id"],
    )
    if team:
        return team, "platform_id"

    named = list(Team.objects.filter(name=team_data.get("name", "Unknown Team"))[:2])
    if len(named) == 1:
        return named[0], "name"
    return None, ("ambiguous_name" if named else "new")


def get_or_create_team(team_data, competition, season, platform):
    """
    Helper function to get or create a team from API data

    Raises:
        AmbiguousTeamError: the team matches no participant or platform ID and
        several teams share its name.
    """
    team_name = team_data.get("name", "Unknown Team")
    team_avatar = team_data.get("avatar")
    if platform == "regentsleague":
        team_avatar = team_data.get("picture")

    team, method = resolve_team(team_data, competition, season, platform)

    # Already linked to this competition
    if method == "competition":
        return team, False

    if method == "ambiguous_name":
        raise AmbiguousTeamError(
            f"Several teams are named '{team_name}'; match it to one in the "
            f"participant matcher or merge the duplicates"
        )

    if team is None:
        # Create new team
        team = Team.objects.create(name=team_name, picture=team_avatar)

    # Create participant record to link team to competition and season, with
    # whichever platform IDs are available
    ids = {field: value for field, value in platform_team_ids(team_data, platform).items() if value}

    participant, created = Participant.objects.get_or_create(
        team=team, competition=competition, season=season, defaults=ids
    )

    # If participant already existed but was missing some IDs, update them
    if not created:
        missing = {
            field: value for field, value in ids.items() if not getattr(participant, field)
        }
        if missing:
            for field, value in missing.items():
                setattr(participant, field, value)
            participant.save()

    # Process players if needed
    roster = team_data.get("roster", [])
    for player_data in roster:
        process_player(player_data, team, season)

    return team, created


def process_player(player_data, team, season):
    """
    Process player data and associate with team.
    Handles player transfers between teams and avoids unique constraint violations.
    """
    player_id = player_data.get("player_id")
    game_player_id = player_data.get("game_player_id") or player_data.get("steam_id")
    nickname = player_data.get("nickname", "Unknown Player")
    avatar = player_data.get("avatar")

    if game_player_id == "":
        game_player_id = None

    elo = 1000

    # Try to fetch updated player data from Faceit API if we have a game_player_id
    try:
        print(f"Processing player {nickname} with game_player_id {game_player_id}")
        # If we have a game_player_id (steam_id), fetch Faceit player ID from Faceit API
        if game_player_id:
            faceit_api_url = "https://open.faceit.com/data/v4/players"
            api_key = getattr(settings, "FACEIT_API_KEY", None)
            if api_key:
                headers = {"Authorization": f"Bearer {api_key}"}
                params = {"game": "cs2", "game_player_id": game_player_id}
                response = requests.get(faceit_api_url, headers=headers, params=params)
                if response.status_code == 200:
                    faceit_data = response.json()
                    player_id = faceit_data.get("player_id", player_id)
                    nickname = faceit_data.get("nickname", nickname)
                    avatar = faceit_data.get("avatar", avatar)
                    elo = (
                        faceit_data.get("games", {})
                        .get("cs2", {})
                        .get("faceit_elo", 1000)
                    )
                    print(f"Fetched Faceit ID {player_id} for player {nickname}")
                    print(f"Player ELO is {elo}")
                else:
                    print(
                        f"Failed to fetch Faceit player for game_player_id {game_player_id}: {response.status_code}"
                    )
    except Exception as e:
        logger.warning(f"Could not fetch Faceit player ID for {nickname}: {str(e)}")

    # Try to find existing player by multiple criteria
    player = None

    # Priority 1: Find by steam_id if available
    if game_player_id:
        try:
            player = Player.objects.get(steam_id=game_player_id)
            print(
                f"Found existing player by steam_id: {player.name} -> moving to {team.name}"
            )
        except Player.DoesNotExist:
            pass

    # Priority 2: Find by faceit_id if not found by steam_id
    if not player and player_id:
        try:
            player = Player.objects.get(faceit_id=player_id)
            print(
                f"Found existing player by faceit_id: {player.name} -> moving to {team.name}"
            )
        except Player.DoesNotExist:
            pass

    # Priority 3: Find by name if no unique identifiers found a match
    if not player and nickname and nickname != "Unknown Player":
        try:
            # Look for player with same name (case insensitive)
            player = Player.objects.get(name__iexact=nickname)
            print(
                f"Found existing player by name: {player.name} -> moving to {team.name}"
            )
        except Player.DoesNotExist:
            pass
        except Player.MultipleObjectsReturned:
            # If multiple players with same name, don't risk picking the wrong one
            print(f"Multiple players found with name {nickname}, creating new player")
            pass

    if player:
        # Update existing player with new information and move to new team
        old_team_name = player.team.name if player.team else "No team"

        # Update player information (but preserve manually set name and picture)
        # Don't update name or picture as they may have been set manually
        if player_id and not player.faceit_id:
            player.faceit_id = player_id
        if game_player_id and not player.steam_id:
            player.steam_id = game_player_id
        player.elo = elo
        player.team = team  # Move to new team
        player.benched = False
        player.seasons.add(season)

        player.save()

        print(f"Updated player {nickname}: {old_team_name} -> {team.name}")
        return player

    # If no existing player found, create a new one
    try:
        player = Player.objects.create(
            name=nickname,
            picture=avatar,
            faceit_id=player_id,
            team=team,
            elo=elo,
            steam_id=game_player_id,
        )
        player.seasons.set([season])
        print(f"Created new player: {nickname} for team {team.name}")
        return player
    except Exception as e:
        # If creation fails due to unique constraint, try one more time to find existing player
        logger.error(f"Failed to create player {nickname}: {str(e)}")

        # Last resort: try to find by any available identifier
        if player_id:
            try:
                player = Player.objects.get(faceit_id=player_id)
                print(f"Found existing player on retry by faceit_id: {player.name}")
                # Update and move to new team (but preserve manually set name and picture)
                # Don't update name or picture as they may have been set manually
                if game_player_id and not player.steam_id:
                    player.steam_id = game_player_id
                player.elo = elo
                player.team = team
                player.benched = False
                player.seasons.add(season)
                player.save()
                return player
            except Player.DoesNotExist:
                pass

        # If still failing, raise the original error
        raise e


@api_view(["GET", "POST"])
@firebase_auth_required(min_role="owner")
def match_participants(request):
    """
    Match participants between competitions/seasons and teams.

    GET: Get all unmatched participants and available teams
    POST: Create or update participant matches
    """
    if request.method == "GET":
        # Get all participants
        participants = Participant.objects.all()

        # Get teams
        teams = Team.objects.all()

        result = {"participants": [], "teams": []}

        # Format participants data
        for participant in participants:
            result["participants"].append(
                {
                    "id": participant.id,
                    "team_id": participant.team.id if participant.team else None,
                    "team_name": participant.team.name if participant.team else None,
                    "competition_id": participant.competition.id
                    if participant.competition
                    else None,
                    "competition_name": participant.competition.name
                    if participant.competition
                    else None,
                    "season_id": participant.season.id if participant.season else None,
                    "season_name": participant.season.name
                    if participant.season
                    else None,
                    "faceit_id": participant.faceit_id,
                    "playfly_id": participant.playfly_id,
                    "playfly_participant_id": participant.playfly_participant_id,
                }
            )

        # Format teams data
        for team in teams:
            result["teams"].append(
                {
                    "id": team.id,
                    "name": team.name,
                    "picture": team.picture,
                    "school_name": team.school_name,
                }
            )

        return Response(result)

    elif request.method == "POST":
        try:
            participant_id = request.data.get("participant_id")
            team_id = request.data.get("team_id")

            if not participant_id or not team_id:
                return Response(
                    {"error": "Missing participant_id or team_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the participant and team
            try:
                participant = Participant.objects.get(id=participant_id)
            except Participant.DoesNotExist:
                return Response(
                    {"error": f"Participant with ID {participant_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return Response(
                    {"error": f"Team with ID {team_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Update the participant
            participant.team = team
            participant.save()

            return Response(
                {
                    "message": "Participant matched successfully",
                    "participant": {
                        "id": participant.id,
                        "team_id": team.id,
                        "team_name": team.name,
                        "competition_id": participant.competition.id
                        if participant.competition
                        else None,
                        "competition_name": participant.competition.name
                        if participant.competition
                        else None,
                        "season_id": participant.season.id
                        if participant.season
                        else None,
                        "season_name": participant.season.name
                        if participant.season
                        else None,
                    },
                }
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Team names on the import that mean "no team yet"; never worth matching.
# Keep in sync with the bye checks in import_match_data.
PLACEHOLDER_TEAM_NAMES = {"bye", "tbd", "unknown team 1", "unknown team 2"}


def extract_import_teams(platform, data):
    """
    The distinct teams in an import's preview data, keyed by platform team key
    (or "name:<name>" for a team without one). Placeholder teams (BYE, TBD) are
    left out; a team in several matches keeps its first occurrence's data.
    """
    if platform == "regentsleague":
        pairs = [(m.get("team1"), m.get("team2")) for m in data or []]
    else:
        pairs = [
            list((item.get("teams") or {}).values())[:2]
            for item in (data or {}).get("items", [])
        ]

    teams = {}
    for pair in pairs:
        for team_data in pair:
            if not team_data:
                continue
            name = team_data.get("name") or ""
            if name.lower() in PLACEHOLDER_TEAM_NAMES:
                continue
            key = platform_team_key(team_data, platform) or f"name:{name}"
            teams.setdefault(key, team_data)
    return teams


def _normalize_name(name):
    return re.sub(r"[^a-z0-9 ]", "", (name or "").lower()).strip()


def _name_similarity(a, b):
    """0-1 similarity of two team names; containment scores at least 0.85."""
    a, b = _normalize_name(a), _normalize_name(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return max(0.85, difflib.SequenceMatcher(None, a, b).ratio())
    return difflib.SequenceMatcher(None, a, b).ratio()


def suggest_teams(team_data, all_teams, limit=5, min_name_score=0.6):
    """
    Rank existing teams an unmatched imported team might be: by how many of
    its roster players are already on the team, then by name similarity
    (name or school name). Teams with any roster overlap are included
    whatever their name; others need a name score of at least min_name_score.

    Args:
        team_data: the imported team (name, roster)
        all_teams: list of Team, to compare names against
        limit: maximum number of suggestions
        min_name_score: 0-1 name similarity needed without roster overlap

    Returns:
        list[dict]: {"team", "roster_overlap", "name_score"}, best first.
    """
    roster = team_data.get("roster") or []
    faceit_ids = {p.get("player_id") for p in roster if p.get("player_id")}
    steam_ids = {
        p.get("game_player_id") or p.get("steam_id")
        for p in roster
        if p.get("game_player_id") or p.get("steam_id")
    }

    overlap = Counter()
    if faceit_ids or steam_ids:
        players = Player.objects.filter(
            models.Q(faceit_id__in=faceit_ids) | models.Q(steam_id__in=steam_ids),
            team__isnull=False,
        ).values_list("team_id", flat=True)
        overlap.update(players)

    name = team_data.get("name", "")
    candidates = []
    for team in all_teams:
        name_score = max(
            _name_similarity(name, team.name), _name_similarity(name, team.school_name)
        )
        if overlap[team.id] or name_score >= min_name_score:
            candidates.append(
                {
                    "team": team,
                    "roster_overlap": overlap[team.id],
                    "name_score": round(name_score, 2),
                }
            )

    candidates.sort(key=lambda c: (c["roster_overlap"], c["name_score"]), reverse=True)
    return candidates[:limit]


def _team_summary(team):
    return {
        "id": str(team.id),
        "name": team.name,
        "school_name": team.school_name,
        "picture": team.picture,
        "elo": team.elo,
    }


@api_view(["POST"])
@firebase_auth_required(min_role="owner")
def resolve_import_teams(request):
    """
    Dry run of an import's team matching, for the participant matcher: which
    teams in the preview data link to an existing team, which would be created
    new, and which share their name with several teams (the import fails for
    those unless one is picked). Unmatched teams get suggested existing teams.
    Writes nothing.

    Expected request format (a subset of the import_matches fields):
    {
        "platform": "faceit" | "leaguespot" | "regentsleague",
        "season_id": "uuid",
        "data": {...}
    }

    Response: {"teams": [{
        "key": "platform team key, or name:<name>",
        "name": "...",
        "roster_size": 5,
        // null when new or ambiguous. "competition" can't occur: no competition exists yet
        "match": {"team": {...}, "method": "platform_id" | "name"} | null,
        "ambiguous": bool,  // several teams share the name, so it can't be auto-matched
        // [] when matched
        "suggestions": [{"team": {...}, "roster_overlap": 3, "name_score": 0.82}]
    }]}
    where team is {id, name, school_name, picture, elo}.
    """
    platform = (request.data.get("platform") or "").lower()
    if platform not in ("faceit", "leaguespot", "regentsleague"):
        return Response(
            {"error": "Unsupported platform"}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        season = Season.objects.get(id=request.data.get("season_id"))
    except (Season.DoesNotExist, ValidationError):
        return Response(
            {"error": "Season not found"}, status=status.HTTP_400_BAD_REQUEST
        )

    data = request.data.get("data")
    expected_type = list if platform == "regentsleague" else dict
    if not isinstance(data, expected_type):
        return Response(
            {"error": "Unexpected match data format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    all_teams = list(Team.objects.all())
    result = []
    for key, team_data in extract_import_teams(platform, data).items():
        # No competition exists yet at dry-run time; the import creates a new one
        team, method = resolve_team(team_data, None, season, platform)
        entry = {
            "key": key,
            "name": team_data.get("name", "Unknown Team"),
            "roster_size": len(team_data.get("roster") or []),
            "match": {"team": _team_summary(team), "method": method} if team else None,
            "ambiguous": method == "ambiguous_name",
            "suggestions": [],
        }
        if team is None:
            entry["suggestions"] = [
                {**s, "team": _team_summary(s["team"])}
                for s in suggest_teams(team_data, all_teams)
            ]
        result.append(entry)

    # Teams that need attention first
    result.sort(key=lambda e: (e["match"] is not None, e["name"].lower()))
    return Response({"teams": result})
