"""
OpenAPI descriptions of the public API (cc/urls_public.py), served at
/v1/public/schema/ with Swagger UI at /v1/public/docs/.

The public views build their responses as dicts, so the serializers here only
describe those responses for the schema; nothing is serialized with them.
cc/tests/test_openapi.py checks real responses against the schema, so a view
that changes shape without updating this file fails the tests. After changing
either, regenerate openapi.yaml (see "Public API docs" in the README).
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers


def public_endpoints_only(endpoints, **kwargs):
    """Preprocessing hook: the admin API isn't documented."""
    return [
        endpoint for endpoint in endpoints if endpoint[0].startswith("/v1/public/")
    ]


# --- Shared pieces ---------------------------------------------------------


class Ref(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class TeamRef(Ref):
    pass


class SeasonRef(Ref):
    pass


class CompetitionRef(Ref):
    pass


class EventRef(Ref):
    pass


class TeamWithPicture(Ref):
    picture = serializers.URLField(allow_null=True)


class PlayerWithPicture(Ref):
    picture = serializers.URLField(allow_null=True)


class RankedTeam(TeamWithPicture):
    school_name = serializers.CharField(allow_null=True)


class RankingRef(serializers.Serializer):
    id = serializers.UUIDField()
    date = serializers.DateTimeField()


class Error(serializers.Serializer):
    error = serializers.CharField()


class Throttled(serializers.Serializer):
    detail = serializers.CharField()


def paginated(item):
    """A page of `item`, as built by the paginated public views."""
    name = item.__name__.removeprefix("Public")
    return type(
        f"Paginated{name}List",
        (serializers.Serializer,),
        {
            "count": serializers.IntegerField(help_text="Results across all pages"),
            "total_pages": serializers.IntegerField(),
            "current_page": serializers.IntegerField(),
            "page_size": serializers.IntegerField(),
            "results": item(many=True),
        },
    )


def uuid_param(name, description, required=False):
    return OpenApiParameter(
        name, OpenApiTypes.UUID, required=required, description=description
    )


def str_param(name, description, enum=None):
    return OpenApiParameter(name, OpenApiTypes.STR, description=description, enum=enum)


def bool_param(name, description):
    return OpenApiParameter(
        name, OpenApiTypes.STR, enum=["true", "false"], description=description
    )


def ids_param(kind):
    return str_param("id", f"{kind} ID, or several comma-separated")


def page_params(sort_fields, default_sort, default_order):
    return [
        OpenApiParameter("page", OpenApiTypes.INT, description="Default 1"),
        OpenApiParameter(
            "page_size", OpenApiTypes.INT, description="Default 20, at most 100"
        ),
        str_param("sort", f"Default {default_sort}", enum=sort_fields),
        str_param("order", f"Default {default_order}", enum=["asc", "desc"]),
    ]


def public_schema(
    operation_id, summary, response, parameters=(), errors=(400,), description=None
):
    """extend_schema for a public GET endpoint, with its error responses."""
    responses = {200: response}
    for code in errors:
        responses[code] = OpenApiResponse(Error, description="See `error`")
    responses[429] = OpenApiResponse(
        Throttled, description="Too many requests from this IP; see Retry-After"
    )
    return extend_schema(
        operation_id=operation_id,
        summary=summary,
        description=description,
        parameters=list(parameters),
        responses=responses,
        tags=["public"],
        auth=[],
    )


# --- Version ---------------------------------------------------------------


class Version(serializers.Serializer):
    api = serializers.CharField(help_text="Semver version of this API's contract")
    build = serializers.CharField(
        help_text="Git commit the server was built from, or dev"
    )
    built_at = serializers.DateTimeField(allow_null=True)


version_schema = public_schema(
    "get_version",
    "Get the API version and running build",
    Version,
    errors=(),
)


# --- Search ----------------------------------------------------------------


class SearchTeam(Ref):
    school_name = serializers.CharField(allow_null=True)
    picture = serializers.URLField(allow_null=True)
    elo = serializers.IntegerField()


class SearchPlayer(Ref):
    picture = serializers.URLField(allow_null=True)
    elo = serializers.IntegerField()
    team = TeamRef(allow_null=True)


class SearchEvent(Ref):
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    picture = serializers.URLField(allow_null=True)
    season = SeasonRef(allow_null=True)
    winner = TeamRef(allow_null=True)


class SearchResults(serializers.Serializer):
    query = serializers.CharField()
    limit = serializers.IntegerField()
    total_results = serializers.IntegerField()
    teams = SearchTeam(many=True)
    players = SearchPlayer(many=True)
    events = SearchEvent(many=True)


search_schema = public_schema(
    "search",
    "Search teams, players and events",
    SearchResults,
    [
        str_param("q", "Search text; an empty query returns no results"),
        OpenApiParameter(
            "limit", OpenApiTypes.INT, description="Results per section, 1-20 (default 6)"
        ),
    ],
    errors=(),
)


# --- Teams -----------------------------------------------------------------


class TeamCurrentRanking(serializers.Serializer):
    id = serializers.UUIDField()
    rank = serializers.IntegerField()
    elo = serializers.IntegerField()
    ranking = RankingRef()
    season = SeasonRef()


class PublicTeam(Ref):
    picture = serializers.URLField(allow_null=True)
    school_name = serializers.CharField(allow_null=True)
    elo = serializers.IntegerField()
    captain = PlayerWithPicture(allow_null=True)
    current_competitions = CompetitionRef(many=True)
    current_ranking = TeamCurrentRanking(
        allow_null=True, help_text="In the current season's latest ranking"
    )


teams_schema = public_schema(
    "list_teams",
    "List teams",
    paginated(PublicTeam),
    [
        ids_param("Team"),
        str_param("name", "Name contains"),
        str_param("school_name", "School name contains"),
        uuid_param("season_id", "Teams in this season"),
        uuid_param("competition_id", "Teams in this competition"),
        uuid_param("event_id", "Teams with a match in this event"),
        *page_params(["name", "school_name", "elo"], "name", "asc"),
    ],
)


# --- Players ---------------------------------------------------------------


class PublicPlayer(Ref):
    picture = serializers.URLField(allow_null=True)
    skill_level = serializers.IntegerField()
    steam_id = serializers.CharField(allow_null=True)
    faceit_id = serializers.CharField(allow_null=True)
    elo = serializers.IntegerField()
    team = TeamWithPicture(allow_null=True)
    benched = serializers.BooleanField()
    visible = serializers.BooleanField()


players_schema = public_schema(
    "list_players",
    "List players",
    paginated(PublicPlayer),
    [
        ids_param("Player"),
        str_param("name", "Name contains"),
        uuid_param("team_id", "Players on this team"),
        str_param("steam_id", "Exact Steam ID"),
        str_param("faceit_id", "Exact Faceit ID"),
        bool_param("visible", "Default: visible players only"),
        bool_param("benched", "Bench status"),
        uuid_param("season_id", "Players in this season"),
        *page_params(["name", "elo", "skill_level"], "name", "asc"),
    ],
)


# --- Matches ---------------------------------------------------------------

MATCH_STATUSES = ["scheduled", "in_progress", "completed", "cancelled"]


class MatchTeam(TeamWithPicture):
    elo = serializers.IntegerField(help_text="The team's current Elo")
    faceit_id = serializers.CharField(
        allow_null=True, help_text="The team's Faceit ID in this competition"
    )


class MatchElo(serializers.Serializer):
    applied = serializers.BooleanField()
    team1_before = serializers.IntegerField(allow_null=True)
    team2_before = serializers.IntegerField(allow_null=True)
    team1_change = serializers.IntegerField(allow_null=True)
    team2_change = serializers.IntegerField(allow_null=True)


class MatchEventMatch(serializers.Serializer):
    id = serializers.UUIDField()
    event = EventRef()
    round = serializers.IntegerField()
    num_in_bracket = serializers.IntegerField()
    is_bye = serializers.BooleanField()
    extra_info = serializers.DictField(help_text="Round name, bracket position, etc.")


class PublicMatch(serializers.Serializer):
    id = serializers.UUIDField()
    team1 = MatchTeam()
    team2 = MatchTeam()
    date = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=MATCH_STATUSES)
    url = serializers.URLField(allow_null=True)
    winner = TeamRef(allow_null=True)
    score_team1 = serializers.IntegerField()
    score_team2 = serializers.IntegerField()
    elo = MatchElo()
    platform = serializers.CharField(help_text="faceit, playfly, ...")
    season = SeasonRef(allow_null=True)
    competition = CompetitionRef(allow_null=True)
    event_match = MatchEventMatch(allow_null=True)


matches_schema = public_schema(
    "list_matches",
    "List matches",
    paginated(PublicMatch),
    [
        ids_param("Match"),
        uuid_param("team_id", "Matches this team played in"),
        uuid_param("team_id_1", "With team_id_2: matches between the two teams"),
        uuid_param("team_id_2", "With team_id_1: matches between the two teams"),
        str_param("status", "Match status", enum=MATCH_STATUSES),
        str_param("platform", "Platform", enum=["faceit", "playfly"]),
        str_param("date_from", "On or after: YYYY-MM-DD or ISO datetime"),
        str_param("date_to", "On or before (a bare date includes that day)"),
        uuid_param("season_id", "Matches in this season"),
        uuid_param("competition_id", "Matches in this competition"),
        str_param(
            "competition_name",
            "Exact competition name, ignoring case (see /competitions)",
        ),
        uuid_param("event_id", "Matches in this event"),
        *page_params(["date", "status"], "date", "desc"),
    ],
)


# --- Seasons and competitions ----------------------------------------------


class PublicSeason(Ref):
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    is_current = serializers.BooleanField()


seasons_schema = public_schema(
    "list_seasons",
    "List seasons",
    paginated(PublicSeason),
    [
        ids_param("Season"),
        bool_param("current", "true: only the current season"),
        *page_params(["name", "start_date", "end_date"], "start_date", "desc"),
    ],
    errors=(),
)


class CompetitionName(serializers.Serializer):
    name = serializers.CharField()


class CompetitionNames(serializers.Serializer):
    results = CompetitionName(many=True)


competitions_schema = public_schema(
    "list_competitions",
    "List competition names",
    CompetitionNames,
    [uuid_param("season_id", "Competitions with matches in this season")],
    description=(
        "Deduplicated by name, ignoring case, and sorted by name. Filter "
        "matches by competition with `competition_name`."
    ),
)


# --- Rankings --------------------------------------------------------------


class PublicRanking(serializers.Serializer):
    id = serializers.UUIDField()
    date = serializers.DateTimeField()
    season = SeasonRef(allow_null=True)


rankings_schema = public_schema(
    "list_rankings",
    "List ranking snapshots",
    paginated(PublicRanking),
    [
        uuid_param("season_id", "Rankings in this season"),
        *page_params(["date"], "date", "desc"),
    ],
)


class PublicRankingItem(serializers.Serializer):
    id = serializers.UUIDField()
    rank = serializers.IntegerField()
    elo = serializers.IntegerField()
    team = RankedTeam()
    ranking = RankingRef()


ranking_items_schema = public_schema(
    "list_ranking_items",
    "List the teams in a ranking",
    paginated(PublicRankingItem),
    [
        uuid_param("ranking_id", "The ranking", required=True),
        *page_params(["rank", "elo"], "rank", "asc"),
    ],
)


class TeamRankingItem(PublicRankingItem):
    season = SeasonRef(allow_null=True)


team_current_ranking_schema = public_schema(
    "get_team_current_ranking",
    "Get a team's current ranking",
    TeamRankingItem,
    [
        uuid_param("team_id", "The team", required=True),
        uuid_param("season_id", "Default: the current season"),
    ],
    errors=(400, 404),
    description="The team's place in the season's latest ranking.",
)


class RankingHistoryItem(serializers.Serializer):
    id = serializers.UUIDField()
    rank = serializers.IntegerField()
    elo = serializers.IntegerField()
    ranking_date = serializers.DateTimeField()
    season = SeasonRef(allow_null=True)


class TeamRankingHistory(serializers.Serializer):
    team_id = serializers.UUIDField()
    ranking_history = RankingHistoryItem(many=True, help_text="Newest first")


team_ranking_history_schema = public_schema(
    "get_team_ranking_history",
    "Get a team's ranking history",
    TeamRankingHistory,
    [
        uuid_param("team_id", "The team", required=True),
        uuid_param("season_id", "Only rankings in this season"),
    ],
)


# --- Events ----------------------------------------------------------------


class CustomEventDetails(serializers.Serializer):
    id = serializers.UUIDField()
    bracket_link = serializers.URLField(allow_null=True)
    stream_link = serializers.URLField(allow_null=True)
    secondary_stream_link = serializers.URLField(allow_null=True)
    discord_link = serializers.URLField(allow_null=True)
    registration_link = serializers.URLField(allow_null=True)
    rules_document = serializers.URLField(allow_null=True)
    prize_pool = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True, coerce_to_string=True
    )
    prize_currency = serializers.CharField()
    max_teams = serializers.IntegerField(allow_null=True)
    entry_fee = serializers.DecimalField(
        max_digits=8, decimal_places=2, allow_null=True, coerce_to_string=True
    )
    format = serializers.CharField(allow_null=True)
    game_mode = serializers.CharField(allow_null=True)
    division = serializers.CharField(allow_null=True, help_text="honors or open")
    is_featured = serializers.BooleanField()
    is_trophycase = serializers.BooleanField()
    is_public = serializers.BooleanField()
    registration_open = serializers.BooleanField()
    registration_deadline = serializers.DateTimeField(allow_null=True)
    twitter_hashtag = serializers.CharField(allow_null=True)
    metadata = serializers.DictField()


class PublicEvent(Ref):
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    description = serializers.CharField(allow_null=True)
    picture = serializers.URLField(allow_null=True)
    winner = RankedTeam(allow_null=True)
    season = SeasonRef(allow_null=True)
    custom_details = CustomEventDetails(
        required=False, help_text="Only for events created on College Counter"
    )


events_schema = public_schema(
    "list_events",
    "List events",
    paginated(PublicEvent),
    [
        ids_param("Event"),
        str_param("name", "Name contains"),
        uuid_param("season_id", "Events in this season"),
        uuid_param("winner_id", "Events this team won"),
        bool_param("featured", "Featured status"),
        bool_param("trophycase", "Trophy case status"),
        bool_param("public_only", "Default true: hide non-public events"),
        *page_params(["name", "start_date", "end_date"], "start_date", "desc"),
    ],
)

event_detail_schema = public_schema(
    "get_event",
    "Get an event",
    PublicEvent,
    errors=(404,),
)


# --- Team form -------------------------------------------------------------


class RecentResult(serializers.Serializer):
    result = serializers.ChoiceField(choices=["win", "loss", "draw"])
    opponent = TeamWithPicture()


class TeamRecentForm(serializers.Serializer):
    team_id = serializers.UUIDField()
    recent_form = RecentResult(many=True, help_text="Newest first")


team_recent_form_schema = public_schema(
    "get_team_recent_form",
    "Get a team's recent results",
    TeamRecentForm,
    [
        uuid_param("team_id", "The team", required=True),
        OpenApiParameter(
            "limit", OpenApiTypes.INT, description="Completed matches, at most 5 (default 3)"
        ),
    ],
)
