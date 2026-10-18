"""Per-IP request limits for endpoints anyone can call. Rates are in settings."""

from rest_framework.throttling import AnonRateThrottle


class PublicRateThrottle(AnonRateThrottle):
    """The public read API (cc/urls_public.py)."""

    scope = "public"


class ProxyRateThrottle(AnonRateThrottle):
    """Public proxies that spend our third-party API quota (Faceit, NWES)."""

    scope = "proxy"
