from unittest.mock import patch

import requests
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from cc.views import get_leaguespot_headers
from cc.webhooks import SanityWebhookView

from .helpers import fake_response


class LeaguespotHeadersTests(SimpleTestCase):
    @override_settings(PLAYFLY_API_KEY="secret-key")
    def test_includes_api_key(self):
        headers = get_leaguespot_headers()
        self.assertEqual(headers["Authorization"], "secret-key")
        self.assertIn("X-League-Id", headers)


class LeaguespotSeasonProxyTests(SimpleTestCase):
    def get(self, response=None, error=None):
        with patch("cc.views.proxies.requests.get") as get:
            if error:
                get.side_effect = error
            else:
                get.return_value = response
            result = APIClient().get(reverse("proxy_leaguespot_season", args=["s1"]))
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
                response = APIClient().get(reverse(name, args=["x"]))
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
                response = APIClient().get(reverse(name, args=["x"]))
                self.assertEqual(response.status_code, 500)


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

    def test_upstream_error_status(self):
        response, _ = self.get(fake_response(status_code=403, text="denied"))
        self.assertEqual(response.status_code, 403)

    def test_empty_body_is_502(self):
        response, _ = self.get(fake_response(text=""))
        self.assertEqual(response.status_code, 502)

    def test_non_json_body_is_returned_as_content(self):
        response, _ = self.get(fake_response(text="plain text"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"content": "plain text"})

    def test_request_exception_is_500(self):
        response, _ = self.get(error=requests.exceptions.Timeout("slow"))
        self.assertEqual(response.status_code, 500)

    def test_unexpected_exception_is_500(self):
        response, _ = self.get(error=KeyError("boom"))
        self.assertEqual(response.status_code, 500)


class ImageProxyTests(SimpleTestCase):
    def test_url_is_required(self):
        response = APIClient().get(reverse("proxy_image"))
        self.assertEqual(response.status_code, 400)

    def test_returns_image_with_cors_and_cache_headers(self):
        upstream = fake_response(headers={"Content-Type": "image/png"}, content=b"PNG")
        with patch("cc.admin_views.requests.get", return_value=upstream) as get:
            response = APIClient().get(
                reverse("proxy_image") + "?url=https://example.com/a.png"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"PNG")
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertEqual(response["Cache-Control"], "public, max-age=3600")
        self.assertEqual(get.call_args.args[0], "https://example.com/a.png")

    def test_defaults_content_type_to_jpeg(self):
        with patch(
            "cc.admin_views.requests.get", return_value=fake_response(content=b"x")
        ):
            response = APIClient().get(reverse("proxy_image") + "?url=https://e.com/a")
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_upstream_failure_is_502(self):
        upstream = fake_response(status_code=404)
        upstream.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        with patch("cc.admin_views.requests.get", return_value=upstream):
            response = APIClient().get(reverse("proxy_image") + "?url=https://e.com/a")
        self.assertEqual(response.status_code, 502)

    def test_unexpected_error_is_500(self):
        with patch("cc.admin_views.requests.get", side_effect=KeyError("x")):
            response = APIClient().get(reverse("proxy_image") + "?url=https://e.com/a")
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
