from django.conf import settings
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import public_views
from .throttles import PublicRateThrottle

urlpatterns = [
    # OpenAPI schema and Swagger UI for these endpoints (cc/public_schema.py)
    path(
        "schema/",
        SpectacularAPIView.as_view(
            throttle_classes=[PublicRateThrottle],
            # Semver build metadata, e.g. 1.0.0+8f03a25, to match the footer
            custom_settings={
                "VERSION": f"{settings.API_VERSION}+{settings.BUILD_SHA}"
            },
        ),
        name="public_schema",
    ),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(
            url_name="public_schema", throttle_classes=[PublicRateThrottle]
        ),
        name="public_docs",
    ),
    path("version", public_views.public_version, name="public_version"),
    # Search endpoint
    path("search", public_views.public_search, name="public_search"),
    # Team endpoints
    path("teams", public_views.public_teams, name="public_teams"),
    # Player endpoints
    path("players", public_views.public_players, name="public_players"),
    # Match endpoints
    path("matches", public_views.public_matches, name="public_matches"),
    # Season endpoints
    path("seasons", public_views.public_seasons, name="public_seasons"),
    # Competition endpoints
    path("competitions", public_views.public_competitions, name="public_competitions"),
    # Ranking endpoints
    path("rankings", public_views.public_rankings, name="public_rankings"),
    path(
        "ranking-items", public_views.public_ranking_items, name="public_ranking_items"
    ),
    path(
        "team-current-ranking",
        public_views.public_team_current_ranking,
        name="public_team_current_ranking",
    ),
    # Event endpoints
    path("events", public_views.public_events, name="public_events"),
    path(
        "events/<uuid:event_id>",
        public_views.public_event_detail,
        name="public_event_detail",
    ),
    path(
        "team_recent_form",
        public_views.public_team_recent_form,
        name="public_team_recent_form",
    ),
    path(
        "team_ranking_history",
        public_views.public_team_ranking_history,
        name="public_team_ranking_history",
    ),
]
