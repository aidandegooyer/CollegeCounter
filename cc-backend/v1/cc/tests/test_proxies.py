import uuid
from unittest.mock import patch

import requests
from django.core.cache import caches
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from cc import images
from cc.models import Match
from cc.views import get_leaguespot_headers
from cc.views.proxies import FACEIT_NO_STATS_CACHE_SECONDS
from cc.webhooks import SanityWebhookView

from .helpers import (
    Fixtures,
    admin_settings,
    clear_caches,
    dev_client,
    fake_response,
    real_caches,
    token_client,
)
from .test_images import PUBLIC_ADDRESS, image_response, png


class LeaguespotHeadersTests(SimpleTestCase):
    @override_settings(PLAYFLY_API_KEY="secret-key")
    def test_includes_api_key(self):
        headers = get_leaguespot_headers()
        self.assertEqual(headers["Authorization"], "secret-key")
        self.assertIn("X-League-Id", headers)


@admin_settings
class LeaguespotSeasonProxyTests(SimpleTestCase):
    def get(self, response=None, error=None):
        with patch("cc.views.proxies.requests.get") as get:
            if error:
                get.side_effect = error
            else:
                get.return_value = response
            result = dev_client().get(reverse("proxy_leaguespot_season", args=["s1"]))
        return result, get

    def test_success_returns_json(self):
        response, get = self.get(fake_response(json_data={"id": "s1"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": "s1"})
        self.assertEqual(
            get.call_args.args[0], "https://api.leaguespot.gg/api/v1/seasons/s1"
        )

    def test_upstream_error_status_is_passed_through(self):
        response, _ = self.get(fake_response(status_code=404, text="missing"))
        self.assertEqual(response.status_code, 404)
        self.assertIn("missing", response.json()["error"])

    def test_empty_body_is_502(self):
        response, _ = self.get(fake_response(text="   "))
        self.assertEqual(response.status_code, 502)

    def test_invalid_json_is_502(self):
        response, _ = self.get(fake_response(text="<html>"))
        self.assertEqual(response.status_code, 502)

    def test_request_exception_is_500(self):
        response, _ = self.get(error=requests.exceptions.ConnectionError("down"))
        self.assertEqual(response.status_code, 500)


@admin_settings
class LeaguespotSimpleProxyTests(SimpleTestCase):
    routes = [
        ("proxy_leaguespot_stage", "https://api.leaguespot.gg/api/v1/stages/x"),
        (
            "proxy_leaguespot_round_matches",
            "https://api.leaguespot.gg/api/v1/rounds/x/matches",
        ),
        ("proxy_leaguespot_match", "https://api.leaguespot.gg/api/v2/matches/x"),
        (
            "proxy_leaguespot_participants",
            "https://api.leaguespot.gg/api/v1/matches/x/participants",
        ),
    ]

    def test_success(self):
        for name, upstream in self.routes:
            with self.subTest(name=name), patch(
                "cc.views.proxies.requests.get",
                return_value=fake_response(json_data=[{"ok": True}]),
            ) as get:
                response = dev_client().get(reverse(name, args=["x"]))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [{"ok": True}])
                self.assertEqual(get.call_args.args[0], upstream)

    def test_http_error_is_500(self):
        upstream = fake_response(status_code=503)
        upstream.raise_for_status.side_effect = requests.exceptions.HTTPError("503")
        for name, _ in self.routes:
            with self.subTest(name=name), patch(
                "cc.views.proxies.requests.get", return_value=upstream
            ):
                response = dev_client().get(reverse(name, args=["x"]))
                self.assertEqual(response.status_code, 500)


class LeaguespotProxyAuthTests(SimpleTestCase):
    """Only the admin import page uses these, and they spend our Playfly key."""

    names = [
        "proxy_leaguespot_season",
        "proxy_leaguespot_stage",
        "proxy_leaguespot_round_matches",
        "proxy_leaguespot_match",
        "proxy_leaguespot_participants",
    ]

    def assert_refused(self, client, status_code):
        for name in self.names:
            with self.subTest(name=name), patch("cc.views.proxies.requests.get") as get:
                response = client.get(reverse(name, args=["x"]))
                self.assertEqual(response.status_code, status_code)
                get.assert_not_called()

    def test_requires_login(self):
        self.assert_refused(APIClient(), 401)

    def test_requires_admin(self):
        client, patcher = token_client({"uid": "u1", "role": "base"})
        self.addCleanup(patcher.stop)
        self.assert_refused(client, 403)


@override_settings(NWES_API_KEY="nwes-key")
class NwesProxyTests(SimpleTestCase):
    def get(self, response=None, error=None, query="?tournament_id=59"):
        with patch("cc.views.proxies.requests.get") as get:
            if error:
                get.side_effect = error
            else:
                get.return_value = response
            result = APIClient().get(reverse("proxy_nwes") + query)
        return result, get

    def test_forwards_params_with_api_key(self):
        response, get = self.get(fake_response(json_data={"teams": []}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"teams": []})
        self.assertEqual(
            get.call_args.kwargs["params"],
            {"tournament_id": "59", "api_key": "nwes-key"},
        )

    def test_upstream_auth_errors_are_502_and_alert(self):
        # Our key is bad; the client isn't unauthenticated
        for upstream in (401, 403):
            with self.subTest(upstream=upstream), self.assertLogs(
                "cc.views.proxies", "ERROR"
            ):
                response, _ = self.get(fake_response(status_code=upstream))
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json()["upstream_status"], upstream)

    def test_unknown_tournament_is_404_without_a_warning(self):
        with self.assertNoLogs("cc.views.proxies", "WARNING"):
            response, _ = self.get(fake_response(status_code=404))
        self.assertEqual(response.status_code, 404)

    def test_upstream_rate_limit_is_503_with_retry_after(self):
        upstream = fake_response(status_code=429, headers={"Retry-After": "30"})
        with self.assertLogs("cc.views.proxies", "WARNING"):
            response, _ = self.get(upstream)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Retry-After"], "30")

    def test_other_upstream_errors_are_502(self):
        with self.assertLogs("cc.views.proxies", "WARNING") as logs:
            response, _ = self.get(fake_response(status_code=500, text="x" * 1000))
        self.assertEqual(response.status_code, 502)
        self.assertLess(len(logs.output[0]), 400)

    def test_empty_body_is_502(self):
        with self.assertLogs("cc.views.proxies", "ERROR"):
            response, _ = self.get(fake_response(text=""))
        self.assertEqual(response.status_code, 502)

    def test_non_json_body_is_502(self):
        with self.assertLogs("cc.views.proxies", "ERROR"):
            response, _ = self.get(fake_response(text="<html>error</html>"))
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("<html>", response.content.decode())

    def test_timeout_is_504(self):
        with self.assertLogs("cc.views.proxies", "WARNING"):
            response, _ = self.get(error=requests.exceptions.Timeout("slow"))
        self.assertEqual(response.status_code, 504)

    def test_request_exception_is_502_without_leaking_the_url(self):
        # requests puts the full URL, query string included, in the message
        error = requests.exceptions.ConnectionError(
            "Max retries exceeded with url: /api?tournament_id=59&api_key=nwes-key"
        )
        with self.assertLogs("cc.views.proxies", "ERROR") as logs:
            response, _ = self.get(error=error)
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("nwes-key", response.content.decode())
        self.assertNotIn("nwes-key", "".join(logs.output))

    def test_only_tournament_id_is_forwarded(self):
        _, get = self.get(
            fake_response(json_data={}), query="?tournament_id=59&action=delete"
        )
        self.assertEqual(
            get.call_args.kwargs["params"],
            {"tournament_id": "59", "api_key": "nwes-key"},
        )

    def test_missing_or_invalid_tournament_id_is_400(self):
        for query in ("", "?tournament_id=", "?tournament_id=59%26x%3D1"):
            with self.subTest(query=query):
                response, get = self.get(query=query)
                self.assertEqual(response.status_code, 400)
                get.assert_not_called()

    @override_settings(NWES_API_KEY="")
    def test_missing_api_key_is_503(self):
        with self.assertLogs("cc.views.proxies", "ERROR"):
            response, get = self.get()
        self.assertEqual(response.status_code, 503)
        get.assert_not_called()


@real_caches
@override_settings(NWES_API_KEY="nwes-key")
class NwesProxyCacheTests(SimpleTestCase):
    def setUp(self):
        clear_caches()

    def get(self, tournament_id, response):
        with patch("cc.views.proxies.requests.get", return_value=response) as get:
            result = APIClient().get(
                reverse("proxy_nwes"), {"tournament_id": tournament_id}
            )
        return result, get

    def test_repeat_requests_are_served_from_cache(self):
        self.get("59", fake_response(json_data={"teams": [1]}))
        response, get = self.get("59", fake_response(json_data={"teams": [2]}))
        self.assertEqual(response.json(), {"teams": [1]})
        get.assert_not_called()

    def test_tournaments_are_cached_separately(self):
        self.get("59", fake_response(json_data={"teams": [1]}))
        response, get = self.get("60", fake_response(json_data={"teams": [2]}))
        self.assertEqual(response.json(), {"teams": [2]})
        get.assert_called_once()

    def test_errors_are_not_cached(self):
        with self.assertLogs("cc.views.proxies", "WARNING"):
            self.get("59", fake_response(status_code=500, text="down"))
        response, get = self.get("59", fake_response(json_data={"teams": []}))
        self.assertEqual(response.status_code, 200)
        get.assert_called_once()


@admin_settings
class ImageProxyTests(SimpleTestCase):
    def setUp(self):
        patcher = patch.object(
            images.socket, "getaddrinfo", return_value=PUBLIC_ADDRESS
        )
        self.getaddrinfo = patcher.start()
        self.addCleanup(patcher.stop)

    def proxy(self, url, client=None):
        return (client or dev_client()).get(reverse("proxy_image"), {"url": url})

    def test_requires_login(self):
        with patch.object(images.requests, "get") as get:
            response = self.proxy("https://example.com/a.png", client=APIClient())
        self.assertEqual(response.status_code, 401)
        get.assert_not_called()

    def test_read_only_users_can_use_it(self):
        client, patcher = token_client({"uid": "u1", "role": "base"})
        self.addCleanup(patcher.stop)
        with patch.object(images.requests, "get", return_value=image_response(png())):
            response = self.proxy("https://example.com/a.png", client=client)
        self.assertEqual(response.status_code, 200)

    def test_url_is_required(self):
        response = dev_client().get(reverse("proxy_image"))
        self.assertEqual(response.status_code, 400)

    def test_returns_image_with_private_cache_header(self):
        picture = png()
        with patch.object(
            images.requests, "get", return_value=image_response(picture)
        ) as get:
            response = self.proxy("https://example.com/a.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, picture)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Cache-Control"], "private, max-age=3600")
        self.assertEqual(get.call_args.args[0], "https://example.com/a.png")

    def test_content_type_comes_from_the_image_not_the_host(self):
        upstream = image_response(png())
        upstream.headers["Content-Type"] = "text/html"
        with patch.object(images.requests, "get", return_value=upstream):
            response = self.proxy("https://example.com/a")
        self.assertEqual(response["Content-Type"], "image/png")

    def test_refuses_what_isnt_an_image(self):
        upstream = image_response(b"<script>alert(1)</script>")
        with patch.object(images.requests, "get", return_value=upstream):
            response = self.proxy("https://example.com/a.png")
        self.assertEqual(response.status_code, 400)

    def test_refuses_private_addresses(self):
        for address in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "::1"):
            self.getaddrinfo.return_value = [(10, 1, 6, "", (address, 443))]
            with patch.object(images.requests, "get") as get:
                response = self.proxy("https://sneaky.example/a.png")
            self.assertEqual(response.status_code, 400, address)
            get.assert_not_called()

    def test_refuses_a_redirect_to_a_private_address(self):
        self.getaddrinfo.side_effect = lambda host, port: (
            [(2, 1, 6, "", ("169.254.169.254", 443))]
            if host == "internal.example"
            else PUBLIC_ADDRESS
        )
        redirect = image_response(b"", 302, location="https://internal.example/meta")
        with patch.object(images.requests, "get", return_value=redirect) as get:
            response = self.proxy("https://example.com/a.png")
        self.assertEqual(response.status_code, 400)
        get.assert_called_once()

    def test_only_https(self):
        with patch.object(images.requests, "get") as get:
            for url in ("http://example.com/a.png", "file:///etc/passwd"):
                self.assertEqual(self.proxy(url).status_code, 400, url)
        get.assert_not_called()

    def test_upstream_failure_is_502(self):
        with patch.object(images.requests, "get", return_value=image_response(b"", 404)):
            response = self.proxy("https://e.com/a")
        self.assertEqual(response.status_code, 502)

    def test_unexpected_error_is_500(self):
        with patch.object(images.requests, "get", side_effect=KeyError("x")):
            response = self.proxy("https://e.com/a")
        self.assertEqual(response.status_code, 500)


class SanityWebhookTests(SimpleTestCase):
    def post(self, data, webhook="https://discord.test/hook", post_error=None):
        with patch.object(SanityWebhookView, "webhook", webhook), patch(
            "cc.webhooks.requests.post"
        ) as post:
            if post_error:
                post.side_effect = post_error
            response = APIClient().post(reverse("sanity_webhook"), data, format="json")
        return response, post

    def test_posts_embed_to_discord(self):
        response, post = self.post(
            {
                "title": "Big Win",
                "slug": "big-win",
                "author": "Ann",
                "authorLink": "https://x.com/ann",
                "imageUrl": "https://img/1.png",
            }
        )
        self.assertEqual(response.status_code, 200)
        url = post.call_args.args[0]
        embed = post.call_args.kwargs["json"]["embeds"][0]
        self.assertEqual(url, "https://discord.test/hook")
        self.assertEqual(embed["title"], "Big Win")
        self.assertEqual(embed["description"], "By [Ann](https://x.com/ann)")
        self.assertIn("https://collegecounter.org/news/big-win", embed["fields"][0]["value"])
        self.assertEqual(embed["image"], {"url": "https://img/1.png"})

    def test_defaults_without_slug_author_or_image(self):
        response, post = self.post({})
        self.assertEqual(response.status_code, 200)
        embed = post.call_args.kwargs["json"]["embeds"][0]
        self.assertEqual(embed["title"], "Untitled")
        self.assertEqual(embed["description"], "By **Unknown**.")
        self.assertEqual(embed["fields"], [])
        self.assertIsNone(embed["image"])

    def test_missing_webhook_url_is_400(self):
        response, post = self.post({"title": "x"}, webhook="")
        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    def test_discord_failure_is_400(self):
        response, _ = self.post({"title": "x"}, post_error=requests.exceptions.ConnectionError())
        self.assertEqual(response.status_code, 400)


@override_settings(FACEIT_API_KEY="key")
class FaceitMatchStatsProxyTests(Fixtures, TestCase):
    def setUp(self):
        self.make_base()
        self.match = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T18:00:00Z",
            status="completed", platform="faceit",
        )

    def get(self, match_id, response):
        with patch("cc.views.proxies.requests.get", return_value=response):
            return APIClient().get(reverse("proxy_faceit_match_stats", args=[match_id]))

    def test_404s_are_not_logged_as_warnings(self):
        for match_id in (self.match.id, uuid.uuid4()):
            with self.subTest(match_id=match_id), self.assertNoLogs("cc.views.proxies", "WARNING"):
                response = self.get(match_id, fake_response(status_code=404))
                self.assertEqual(response.status_code, 404)

    def test_other_upstream_errors_still_warn(self):
        with self.assertLogs("cc.views.proxies", "WARNING"):
            response = self.get(self.match.id, fake_response(status_code=500))
        self.assertEqual(response.status_code, 502)

    def refused(self, match_id):
        """Request stats that should be refused before any call to Faceit."""
        with patch("cc.views.proxies.requests.get") as get:
            response = APIClient().get(
                reverse("proxy_faceit_match_stats", args=[match_id])
            )
        get.assert_not_called()
        return response

    def test_unknown_match_is_404(self):
        self.assertEqual(self.refused(uuid.uuid4()).status_code, 404)

    def test_non_faceit_match_is_400(self):
        Match.objects.filter(id=self.match.id).update(platform="playfly")
        self.assertEqual(self.refused(self.match.id).status_code, 400)

    def test_unfinished_match_is_409(self):
        for match_status in ("scheduled", "in_progress", "cancelled"):
            with self.subTest(status=match_status):
                Match.objects.filter(id=self.match.id).update(status=match_status)
                self.assertEqual(self.refused(self.match.id).status_code, 409)

    @override_settings(FACEIT_API_KEY="")
    def test_missing_api_key_is_503(self):
        with self.assertLogs("cc.views.proxies", "ERROR"):
            response = self.refused(self.match.id)
        self.assertEqual(response.status_code, 503)

    def test_only_the_match_id_reaches_faceit(self):
        with patch(
            "cc.views.proxies.requests.get",
            return_value=fake_response(json_data={"rounds": []}),
        ) as get:
            APIClient().get(
                reverse("proxy_faceit_match_stats", args=[self.match.id]),
                {"url": "https://example.com"},
            )
        self.assertEqual(
            get.call_args.args[0],
            f"https://open.faceit.com/data/v4/matches/1-{self.match.id}/stats",
        )
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer key")
        self.assertNotIn("params", get.call_args.kwargs)


@real_caches
@override_settings(FACEIT_API_KEY="key")
class FaceitMatchStatsCacheTests(Fixtures, TestCase):
    def setUp(self):
        clear_caches()
        self.make_base()
        self.match = Match.objects.create(
            team1=self.alpha, team2=self.bravo, date="2025-10-01T18:00:00Z",
            status="completed", platform="faceit",
        )

    def get(self, response):
        with patch("cc.views.proxies.requests.get", return_value=response) as get:
            result = APIClient().get(
                reverse("proxy_faceit_match_stats", args=[self.match.id])
            )
        return result, get

    def test_repeat_requests_are_served_from_cache(self):
        self.get(fake_response(json_data={"rounds": [1]}))
        response, get = self.get(fake_response(json_data={"rounds": [2]}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rounds": [1]})
        get.assert_not_called()

    def test_missing_stats_are_cached_briefly(self):
        first, _ = self.get(fake_response(status_code=404))
        response, get = self.get(fake_response(json_data={"rounds": []}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), first.json())
        get.assert_not_called()

    def test_missing_stats_are_cached_for_less_time_than_stats(self):
        cache = caches["proxy"]
        with patch.object(cache, "set", wraps=cache.set) as cache_set:
            self.get(fake_response(status_code=404))
        self.assertEqual(cache_set.call_args.args[2], FACEIT_NO_STATS_CACHE_SECONDS)

    def test_other_errors_are_not_cached(self):
        self.get(fake_response(status_code=500))
        response, get = self.get(fake_response(json_data={"rounds": []}))
        self.assertEqual(response.status_code, 200)
        get.assert_called_once()
