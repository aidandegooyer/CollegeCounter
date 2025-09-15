from django.urls import path, include

from . import views
from . import image_views

urlpatterns = [
    path("", views.index, name="index"),
    path("import-matches/", views.import_matches, name="import_matches"),
    path("seasons/", views.list_seasons, name="list_seasons"),
    path("seasons/create/", views.create_season, name="create_season"),
    path("teams/", views.list_teams, name="list_teams"),
    path("players/", views.list_players, name="list_players"),
    path("matches/", views.list_matches, name="list_matches"),
    path("clear-database/", views.clear_database, name="clear_database"),
    path("participants/", views.match_participants, name="match_participants"),
    path("player-elo/update/", views.update_player_elo, name="update_player_elo"),
    path("player-elo/reset/", views.reset_player_elo, name="reset_player_elo"),
    path("team-elo/calculate/", views.calculate_team_elos, name="calculate_team_elos"),
    # Image upload endpoints
    path(
        "teams/<uuid:team_id>/picture/",
        image_views.upload_team_picture,
        name="upload_team_picture",
    ),
    path(
        "players/<uuid:player_id>/picture/",
        image_views.upload_player_picture,
        name="upload_player_picture",
    ),
    path("teams/<uuid:team_id>/", image_views.update_team, name="update_team"),
    path("players/<uuid:player_id>/", image_views.update_player, name="update_player"),
    # LeagueSpot API proxy endpoints
    path(
        "proxy/leaguespot/seasons/<str:season_id>/",
        views.proxy_leaguespot_season,
        name="proxy_leaguespot_season",
    ),
    path(
        "proxy/leaguespot/stages/<str:stage_id>/",
        views.proxy_leaguespot_stage,
        name="proxy_leaguespot_stage",
    ),
    path(
        "proxy/leaguespot/rounds/<str:round_id>/matches/",
        views.proxy_leaguespot_round_matches,
        name="proxy_leaguespot_round_matches",
    ),
    path(
        "proxy/leaguespot/matches/<str:match_id>/",
        views.proxy_leaguespot_match,
        name="proxy_leaguespot_match",
    ),
    path(
        "proxy/leaguespot/matches/<str:match_id>/participants/",
        views.proxy_leaguespot_participants,
        name="proxy_leaguespot_participants",
    ),
    # Include public API endpoints
    path("public/", include("cc.urls_public")),
]
