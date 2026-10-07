"""Shared helpers for the admin views."""

from django.utils.dateparse import parse_datetime
from datetime import datetime
from datetime import timezone as dt_timezone
from django.utils import timezone

import logging

logger = logging.getLogger(__name__)


def safe_parse_datetime(dt):
    """
    Parse a datetime from either a string (e.g. "2025-10-25T00:30:00Z")
    or a unix timestamp (int/float, seconds since epoch).
    Returns a timezone-aware datetime or None.
    """
    if isinstance(dt, str):
        # Try to parse ISO format with Z
        parsed = parse_datetime(dt)
        if parsed:
            # If no timezone info, assume UTC
            if parsed.tzinfo is None:
                parsed = timezone.make_aware(parsed, dt_timezone.utc)
            return parsed
        # If parse_datetime fails, try to parse as unix timestamp string
        try:
            ts = float(dt)
            return datetime.fromtimestamp(ts)
        except ValueError:
            return None
    if isinstance(dt, (int, float)):
        return datetime.fromtimestamp(dt)
    return None
