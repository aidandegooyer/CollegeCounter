from django.urls import path, include

from . import views

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
    # Include public API endpoints
    path("public/", include("cc.urls_public")),
]
