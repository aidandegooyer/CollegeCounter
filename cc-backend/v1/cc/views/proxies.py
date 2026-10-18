"""Proxies for third-party APIs that the frontend can't call directly (CORS)."""

from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from django.conf import settings
from django.core.cache import caches
from rest_framework import status

import logging
import re
import requests

from ..middleware import firebase_auth_required
from ..models import Match
from ..throttles import ProxyRateThrottle

logger = logging.getLogger(__name__)

# Loose on purpose: just keeps junk out of the request we send NWES
NWES_TOURNAMENT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
# Same as the Match page's staleTime for this data
NWES_CACHE_SECONDS = 60 * 5
# Stats for a completed match don't change; the cache's MAX_ENTRIES bounds
# memory, not this
FACEIT_STATS_CACHE_SECONDS = 60 * 60 * 24
# Faceit has no stats for some completed matches, and can take a little
# while to publish them for others, so "none" is only cached briefly
FACEIT_NO_STATS_CACHE_SECONDS = 60 * 15
NO_FACEIT_STATS = "none"


def get_leaguespot_headers():
    """Get the standard headers needed for LeagueSpot API requests"""
    apikey = getattr(settings, "PLAYFLY_API_KEY", None)
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "X-App": "web",
        "X-Version": "20251009.2",
        "X-League-Id": "53015f28-5b33-4882-9f8b-16dcbb13deee",
        "Origin": "https://esports.pcl.gg",
        "Connection": "keep-alive",
        "Referer": "https://esports.pcl.gg/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Authorization": apikey,
    }


@api_view(["GET"])
@firebase_auth_required(min_role="admin")
def proxy_leaguespot_season(request, season_id):
    """Proxy LeagueSpot season API to avoid CORS issues"""
    headers = get_leaguespot_headers()

    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v1/seasons/{season_id}",
            headers=headers,
            timeout=30,
        )

        # Log the response details for debugging
        logger.info(f"LeagueSpot season API response status: {response.status_code}")
        logger.info(f"LeagueSpot season API response headers: {dict(response.headers)}")
        if response.status_code != 200:
            return Response(
                {
                    "error": f"LeagueSpot API returned status {response.status_code}: {response.text}"
                },
                status=response.status_code,
            )

        # Check if response is empty
        if not response.text.strip():
            return Response(
                {"error": "LeagueSpot API returned empty response"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Try to parse JSON
        try:
            json_data = response.json()
            return Response(json_data)
        except ValueError as json_error:
            logger.error(f"Failed to parse JSON from LeagueSpot: {json_error}")
            logger.error(f"Raw response: {response.text}")
            return Response(
                {
                    "error": f"Invalid JSON response from LeagueSpot: {response.text[:200]}"
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot season {season_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch season data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@firebase_auth_required(min_role="admin")
def proxy_leaguespot_stage(request, stage_id):
    """Proxy LeagueSpot stage API to avoid CORS issues"""
    headers = get_leaguespot_headers()

    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v1/stages/{stage_id}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return Response(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot stage {stage_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch stage data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@firebase_auth_required(min_role="admin")
def proxy_leaguespot_round_matches(request, round_id):
    """Proxy LeagueSpot round matches API to avoid CORS issues"""
    headers = get_leaguespot_headers()

    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v1/rounds/{round_id}/matches",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return Response(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot round matches {round_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch round matches: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@firebase_auth_required(min_role="admin")
def proxy_leaguespot_match(request, match_id):
    """Proxy LeagueSpot match API to avoid CORS issues"""
    headers = get_leaguespot_headers()

    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v2/matches/{match_id}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return Response(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot match {match_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch match data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@firebase_auth_required(min_role="admin")
def proxy_leaguespot_participants(request, match_id):
    """Proxy LeagueSpot match participants API to avoid CORS issues"""
    headers = get_leaguespot_headers()
    try:
        response = requests.get(
            f"https://api.leaguespot.gg/api/v1/matches/{match_id}/participants",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return Response(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying LeagueSpot participants {match_id}: {str(e)}")
        return Response(
            {"error": f"Failed to fetch participants data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@throttle_classes([ProxyRateThrottle])
def proxy_nwes(request):
    """
    Proxy NWES tournament stats for the Match page, keeping our API key secret.

    /proxy/nwes/?tournament_id=59

    Only tournament_id is forwarded, so callers can't spend our key on other
    NWES queries. Responses are cached for as long as the Match page keeps
    them (its staleTime).
    """
    tournament_id = request.GET.get("tournament_id", "")
    if not NWES_TOURNAMENT_ID.fullmatch(tournament_id):
        return Response(
            {"error": "A valid tournament_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    nwes_api_key = settings.NWES_API_KEY
    if not nwes_api_key:
        logger.error("NWES_API_KEY is not configured")
        return Response(
            {"error": "NWES integration is not configured"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    cache_key = f"nwes:{tournament_id}"
    cached = caches["proxy"].get(cache_key)
    if cached is not None:
        return Response(cached)

    try:
        response = requests.get(
            "https://nwes.gg/api/api-tournament.php",
            params={"tournament_id": tournament_id, "api_key": nwes_api_key},
            timeout=30,
        )

        # Log the response for debugging
        logger.info(f"NWES API response status: {response.status_code}")

        if response.status_code != 200:
            logger.warning(f"NWES API returned {response.status_code}: {response.text}")
            return Response(
                {"error": f"NWES API returned status {response.status_code}"},
                status=response.status_code,
            )

        # Check if response is empty
        if not response.text.strip():
            return Response(
                {"error": "NWES API returned empty response"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Try to parse JSON and return it
        try:
            json_data = response.json()
            caches["proxy"].set(cache_key, json_data, NWES_CACHE_SECONDS)
            return Response(json_data)
        except ValueError as json_error:
            # If it's not JSON, return the text content
            logger.warning(f"NWES response is not JSON: {json_error}")
            return Response(
                {"content": response.text},
                status=status.HTTP_200_OK,
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying NWES API: {str(e)}")
        return Response(
            {"error": f"Failed to fetch NWES data: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        logger.error(f"Unexpected error in NWES proxy: {str(e)}")
        return Response(
            {"error": f"Unexpected error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@throttle_classes([ProxyRateThrottle])
def proxy_faceit_match_stats(request, match_id):
    match = Match.objects.filter(id=match_id).only("id", "platform", "status").first()

    if match is None:
        logger.info(
            "Rejected Faceit stats request for an unknown match: match_id=%s",
            match_id,
        )
        return Response(
            {"error": "Faceit match not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if match.platform.lower() != "faceit":
        return Response(
            {"error": "Match is not a Faceit match"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if match.status != "completed":
        return Response(
            {"error": "Faceit stats are only available for completed matches"},
            status=status.HTTP_409_CONFLICT,
        )

    cache_key = f"faceit-stats:{match_id}"
    cached = caches["proxy"].get(cache_key)
    if cached == NO_FACEIT_STATS:
        return Response(
            {
                "error": "Faceit rejected the match statistics request",
                "upstream_status": 404,
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    if cached is not None:
        return Response(cached)

    faceit_api_key = getattr(settings, "FACEIT_API_KEY", "")

    if not faceit_api_key:
        logger.error("FACEIT_API_KEY is not configured")
        return Response(
            {"error": "Faceit integration is not configured"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    api_url = f"https://open.faceit.com/data/v4/matches/1-{match_id}/stats"

    headers = {
        "Authorization": f"Bearer {faceit_api_key}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            api_url,
            headers=headers,
            timeout=20,
        )

    except requests.exceptions.Timeout:
        logger.warning(
            "Faceit match stats request timed out: match_id=%s",
            match_id,
        )
        return Response(
            {"error": "Faceit API request timed out"},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except requests.exceptions.RequestException:
        logger.exception(
            "Faceit match stats request failed: match_id=%s",
            match_id,
        )
        return Response(
            {"error": "Unable to reach the Faceit API"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if response.status_code != 200:
        # Don't pass Faceit's status through: a 401/403 means our API key is
        # bad, not that the client is unauthenticated. Only 404 (no stats yet)
        # is meaningful to the client.
        if response.status_code == 404:
            # Expected for matches Faceit has no stats for; not alert-worthy.
            client_status = status.HTTP_404_NOT_FOUND
            log = logger.info
            caches["proxy"].set(
                cache_key, NO_FACEIT_STATS, FACEIT_NO_STATS_CACHE_SECONDS
            )
        elif response.status_code in (401, 403):
            client_status = status.HTTP_502_BAD_GATEWAY
            log = logger.error
        elif response.status_code == 429:
            client_status = status.HTTP_503_SERVICE_UNAVAILABLE
            log = logger.warning
        else:
            client_status = status.HTTP_502_BAD_GATEWAY
            log = logger.warning
        log(
            "Faceit returned status %s for match %s: %s",
            response.status_code,
            match_id,
            response.text[:200],
        )
        error_response = Response(
            {
                "error": "Faceit rejected the match statistics request",
                "upstream_status": response.status_code,
            },
            status=client_status,
        )
        retry_after = response.headers.get("Retry-After")
        if response.status_code == 429 and retry_after:
            error_response["Retry-After"] = retry_after
        return error_response

    try:
        stats = response.json()
    except ValueError:
        logger.error(
            "Faceit returned invalid JSON for match %s",
            match_id,
        )
        return Response(
            {"error": "Faceit returned an invalid response"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    caches["proxy"].set(cache_key, stats, FACEIT_STATS_CACHE_SECONDS)
    return Response(stats)
