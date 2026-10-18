"""Shared fixtures for the cc test suite."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests
from django.core.cache import caches
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from cc.models import Competition, Season, Team


def fake_response(status_code=200, json_data=None, text=None, headers=None, content=b""):
    """A stand-in for requests.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.content = content
    if json_data is not None:
        response.json.return_value = json_data
        response.text = text if text is not None else str(json_data)
    else:
        response.json.side_effect = requests.JSONDecodeError("No JSON", "", 0)
        response.text = text if text is not None else ""
    return response


def dev_client():
    """An APIClient using the DEBUG-only "Bearer dev" token, which grants owner."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer dev")
    return client


def token_client(claims):
    """
    An APIClient whose Firebase token decodes to `claims`. Returns the client
    and the active patcher; stop it with addCleanup(patcher.stop).
    """
    patcher = patch("cc.middleware.auth.verify_id_token", return_value=claims)
    patcher.start()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer token")
    return client, patcher


def current_season(name="Current Season", **kwargs):
    now = timezone.now()
    return Season.objects.create(
        name=name,
        start_date=kwargs.pop("start_date", now - timedelta(days=60)),
        end_date=kwargs.pop("end_date", now + timedelta(days=60)),
        **kwargs,
    )


def past_season(name="Past Season"):
    now = timezone.now()
    return Season.objects.create(
        name=name,
        start_date=now - timedelta(days=500),
        end_date=now - timedelta(days=400),
    )


admin_settings = override_settings(DEBUG=True)

# Tests run with dummy caches (see CACHES in settings). This switches the
# real in-memory ones back on, for testing throttling and cached responses.
# Their contents outlive the override, so call clear_caches() in setUp.
real_caches = override_settings(
    CACHES={
        name: {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"test-{name}",
        }
        for name in ("default", "proxy")
    }
)


def clear_caches():
    for cache in caches.all():
        cache.clear()


class Fixtures:
    """Mixin with a couple of teams, a competition and a current season."""

    def make_base(self):
        self.season = current_season()
        self.competition = Competition.objects.create(name="League")
        self.alpha = Team.objects.create(name="Alpha", elo=1000)
        self.bravo = Team.objects.create(name="Bravo", elo=1200)
