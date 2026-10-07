"""
Admin API views, split by area. Everything is re-exported here so
`from . import views` / `views.<name>` in urls.py keeps working.
"""

from .utils import (  # noqa: F401
    safe_parse_datetime,
)
from .elo import (  # noqa: F401
    calculate_new_elo,
    match_elo_data,
    update_match_elos,
    revert_match_elos,
    revert_match_elos_if_outcome_changed,
    recalculate_all_elos,
    apply_match_elo,
    revert_match_elo,
    recalculate_elos,
    calculate_team_elos,
    create_ranking_snapshot,
)
from .imports import (  # noqa: F401
    import_matches,
    import_regentsleague_match_data,
    import_match_data,
    get_or_create_team,
    process_player,
    match_participants,
)
from .platform_sync import (  # noqa: F401
    update_matches,
    update_regentsleague_match,
    update_faceit_match,
    update_leaguespot_match,
)
from .matches import (  # noqa: F401
    list_matches,
    get_match,
    create_match,
    create_event_match,
    update_event_match,
    update_match,
    delete_match,
)
from .teams import (  # noqa: F401
    list_teams,
    list_players,
    merge_teams,
    update_player_elo,
    reset_player_elo,
)
from .admin_data import (  # noqa: F401
    index,
    list_seasons,
    create_season,
    clear_database,
    list_competitions,
    delete_competition,
)
from .proxies import (  # noqa: F401
    get_leaguespot_headers,
    proxy_leaguespot_season,
    proxy_leaguespot_stage,
    proxy_leaguespot_round_matches,
    proxy_leaguespot_match,
    proxy_leaguespot_participants,
    proxy_nwes,
)
