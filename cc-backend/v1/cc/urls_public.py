from django.urls import path

from . import public_views

urlpatterns = [
    # Team endpoints
    path("teams", public_views.public_teams, name="public_teams"),
    # Player endpoints
    path("players", public_views.public_players, name="public_players"),
    # Match endpoints
    path("matches", public_views.public_matches, name="public_matches"),
    # Season endpoints
    path("seasons", public_views.public_seasons, name="public_seasons"),
    # Ranking endpoints
    path("rankings", public_views.public_rankings, name="public_rankings"),
    path(
        "ranking-items", public_views.public_ranking_items, name="public_ranking_items"
    ),
]
