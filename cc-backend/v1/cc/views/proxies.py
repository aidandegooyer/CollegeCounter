"""Proxies for third-party APIs that the frontend can't call directly (CORS)."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status

import logging
import requests

logger = logging.getLogger(__name__)


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
def proxy_nwes(request):
    """
    Proxy NWES API to avoid CORS issues and keep API key secure.

    The frontend can call this endpoint with query parameters like:
    /proxy/nwes/?tournament_id=59

    The backend will append the API key and forward the request to NWES.
    """
    try:
        # Get the API key from settings
        nwes_api_key = getattr(
            settings,
            "NWES_API_KEY",
            "9cTmWJ2A4q53fw8wGRJcollegecounterB2iLc8be5gRHfPDQ2FY",
        )

        # Get all query parameters from the frontend request
        query_params = request.GET.dict()

        # Add the API key to the query parameters
        query_params["api_key"] = nwes_api_key

        # Build the NWES API URL
        nwes_api_url = "https://nwes.gg/api/api-tournament.php"

        # Make the request to NWES
        response = requests.get(
            nwes_api_url,
            params=query_params,
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
