"""Posts warnings and errors to a Discord channel; wired up in settings.LOGGING."""

import logging
import os
import queue
import socket
import sys
import threading
import time

import requests

# Discord rejects embed descriptions over 4096 characters
DESCRIPTION_LIMIT = 4000
COLORS = {logging.WARNING: 0xE67E22, logging.ERROR: 0xE74C3C}


class DiscordWebhookHandler(logging.Handler):
    """Sends each record as an embed from a background thread, so logging never
    waits on Discord. Repeats from the same line are collapsed for
    `cooldown_seconds`, so an outage (e.g. match sync failing every 30s) sends
    one alert, and the next one after the cooldown says how many were skipped."""

    def __init__(self, webhook_url="", cooldown_seconds=600, level=logging.WARNING):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.cooldown_seconds = cooldown_seconds
        self.service = os.getenv("SERVICE_NAME") or socket.gethostname()
        # Source line -> (when it last posted, how many were skipped since)
        self._recent = {}
        self._recent_lock = threading.Lock()
        self._queue = queue.Queue(maxsize=100)
        self._thread = None

    def emit(self, record):
        if not self.webhook_url:
            return
        try:
            suppressed = self._check_cooldown(record)
            if suppressed is None:
                return
            self._queue.put_nowait(self.build_payload(record, suppressed))
            self._start_thread()
        except queue.Full:
            pass
        except Exception:
            self.handleError(record)

    def _check_cooldown(self, record):
        """Returns how many repeats were skipped, or None to skip this one too.
        Keyed by source line, not message, since messages often include IDs."""
        key = (record.name, record.levelno, record.pathname, record.lineno)
        now = time.monotonic()
        with self._recent_lock:
            last_sent, skipped = self._recent.get(key, (None, 0))
            if last_sent is not None and now - last_sent < self.cooldown_seconds:
                self._recent[key] = (last_sent, skipped + 1)
                return None
            self._recent[key] = (now, 0)
            return skipped

    def build_payload(self, record, suppressed=0):
        text = record.getMessage()
        if record.exc_info:
            text += "\n```\n" + logging.Formatter().formatException(record.exc_info)
            # Keep the end of the traceback, where the actual error is
            if len(text) > DESCRIPTION_LIMIT:
                text = text[: DESCRIPTION_LIMIT // 4] + "\n…\n" + text[-(DESCRIPTION_LIMIT * 3 // 4) :]
            text += "\n```"
        elif len(text) > DESCRIPTION_LIMIT:
            text = text[:DESCRIPTION_LIMIT] + "…"
        if suppressed:
            text += f"\n\n(+{suppressed} similar suppressed)"

        embed = {
            "title": f"{record.levelname} in {record.name}"[:256],
            "description": text,
            "color": COLORS.get(record.levelno, COLORS[logging.ERROR]),
            "fields": [
                {"name": "Service", "value": self.service, "inline": True},
                {
                    "name": "Where",
                    "value": f"{os.path.basename(record.pathname)}:{record.lineno}",
                    "inline": True,
                },
            ],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
        }
        return {"embeds": [embed]}

    def _start_thread(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="discord-logging", daemon=True)
            self._thread.start()

    def _run(self):
        while True:
            self.send(self._queue.get())

    def send(self, payload):
        """Posts one payload. Never raises or logs (logging here could loop back
        into this handler); failures go to stderr."""
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            if response.status_code == 429:
                time.sleep(min(float(response.json().get("retry_after", 1)), 30))
                response = requests.post(self.webhook_url, json=payload, timeout=5)
            if response.status_code >= 400:
                print(f"Discord alert failed: HTTP {response.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"Discord alert failed: {e!r}", file=sys.stderr)
