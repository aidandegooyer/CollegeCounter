import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse
from rest_framework.test import APIClient

from cc import urls_public
from cc.throttles import ProxyRateThrottle, PublicRateThrottle

from .helpers import admin_settings, clear_caches, dev_client, real_caches

# Low limits so tests don't need hundreds of requests. Both classes share
# DRF's rates dict, so this patches it for both.
low_rates = patch.dict(
    PublicRateThrottle.THROTTLE_RATES, {"public": "2/minute", "proxy": "1/minute"}
)


@real_caches
@low_rates
class ThrottlingTests(TestCase):
    def setUp(self):
        clear_caches()

    def get(self, name="public_seasons", args=(), client=None, ip=None):
        extra = {"HTTP_X_FORWARDED_FOR": ip} if ip else {}
        return (client or APIClient()).get(reverse(name, args=args), **extra)

    def test_public_api_is_limited_per_ip(self):
        self.assertEqual(self.get().status_code, 200)
        self.assertEqual(self.get().status_code, 200)
        response = self.get()
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_client_ip_is_the_last_forwarded_for_entry(self):
        # nginx-proxy appends the address it saw; anything before that is
        # whatever the client sent, so it can't be used to dodge the limit.
        for spoofed in ("1.1.1.1", "2.2.2.2"):
            self.assertEqual(self.get(ip=f"{spoofed}, 9.9.9.9").status_code, 200)
        self.assertEqual(self.get(ip="3.3.3.3, 9.9.9.9").status_code, 429)
        self.assertEqual(self.get(ip="8.8.8.8").status_code, 200)

    def test_proxies_have_their_own_limit(self):
        self.get()
        self.get()
        args = [uuid.uuid4()]
        # Unknown match: refused before any Faceit call, but still counted
        self.assertEqual(
            self.get("proxy_faceit_match_stats", args).status_code, 404
        )
        self.assertEqual(
            self.get("proxy_faceit_match_stats", args).status_code, 429
        )

    @admin_settings
    def test_admin_endpoints_are_not_limited(self):
        client = dev_client()
        for _ in range(4):
            self.assertEqual(self.get("list_seasons", client=client).status_code, 200)


def view_throttles(view):
    # as_view(throttle_classes=...) overrides the class's, as for the docs
    return view.initkwargs.get("throttle_classes", view.cls.throttle_classes)


class EveryPublicViewIsThrottledTests(SimpleTestCase):
    """The tests above check one view; these catch one left off."""

    def test_public_api(self):
        for pattern in urls_public.urlpatterns:
            with self.subTest(pattern.name):
                self.assertIn(PublicRateThrottle, view_throttles(pattern.callback))

    def test_proxies(self):
        for name, args in (
            ("proxy_nwes", ()),
            ("proxy_faceit_match_stats", (uuid.uuid4(),)),
        ):
            with self.subTest(name):
                view = resolve(reverse(name, args=args)).func
                self.assertIn(ProxyRateThrottle, view_throttles(view))
