"""Posts warnings and errors to a Discord channel; wired up in settings.LOGGING."""

import logging
import os
import queue
import socket
import sys
import threading
import time
from urllib.parse import urlsplit

import requests

# Discord rejects embed descriptions over 4096 characters; the message and the
# traceback are capped separately so the code fence around the traceback survives
MESSAGE_LIMIT = 1000
TRACEBACK_LIMIT = 2900
COLORS = {logging.WARNING: 0xE67E22, logging.ERROR: 0xE74C3C}
# How long flush() (called by logging.shutdown at exit) waits for queued alerts
FLUSH_SECONDS = 5


class DiscordWebhookHandler(logging.Handler):
    """Sends each record as an embed from a background thread, so logging never
    waits on Discord. Repeats from the same line are collapsed for
    `cooldown_seconds`, so an outage (e.g. match sync failing every 30s) sends
    one alert, and the next one after the cooldown says how many were skipped.

    It never logs about itself (that could loop back into this handler);
    its own problems go to stderr, with the webhook token redacted."""

    def __init__(
        self,
        webhook_url="",
        cooldown_seconds=600,
        warn_if_disabled=False,
        level=logging.WARNING,
    ):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.cooldown_seconds = cooldown_seconds
        self.service = os.getenv("SERVICE_NAME") or socket.gethostname()
        # Source line -> (when it last posted, how many were skipped since)
        self._recent = {}
        self._recent_lock = threading.Lock()
        self._queue = queue.Queue(maxsize=100)
        self._thread = None
        if not webhook_url and warn_if_disabled:
            self._stderr("DISCORD_ALERTS_WEBHOOK_URL is not set; Discord alerts are disabled")

    def emit(self, record):
        if not self.webhook_url:
            return
        try:
            if self._enqueue(record):
                self._start_thread()
        except Exception:
            self.handleError(record)

    def _enqueue(self, record):
        """Queues the record unless its source line posted within the cooldown.
        Keyed by source line, not message, since messages often include IDs.
        A record dropped because the queue is full counts as skipped, so the
        next alert from that line still reports it."""
        key = (record.name, record.levelno, record.pathname, record.lineno)
        now = time.monotonic()
        with self._recent_lock:
            last_sent, skipped = self._recent.get(key, (None, 0))
            if last_sent is not None and now - last_sent < self.cooldown_seconds:
                self._recent[key] = (last_sent, skipped + 1)
                return False
            try:
                self._queue.put_nowait(self.build_payload(record, skipped))
            except queue.Full:
                self._recent[key] = (last_sent, skipped + 1)
                self._stderr(f"Discord alert dropped (queue full): {record.name}")
                return False
            self._recent[key] = (now, 0)
            return True

    def build_payload(self, record, suppressed=0):
        text = record.getMessage()
        if len(text) > MESSAGE_LIMIT:
            text = text[:MESSAGE_LIMIT] + "…"
        # exc_info=True outside an except block gives (None, None, None)
        if record.exc_info and record.exc_info[0]:
            trace = logging.Formatter().formatException(record.exc_info)
            # Keep the end of the traceback, where the actual error is
            if len(trace) > TRACEBACK_LIMIT:
                trace = "…\n" + trace[-TRACEBACK_LIMIT:]
            text += f"\n```\n{trace}\n```"
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
            payload = self._queue.get()
            try:
                self.send(payload)
            finally:
                self._queue.task_done()

    def flush(self):
        """Gives queued alerts a few seconds to post, so a process that logs an
        error and exits (e.g. a management command) doesn't lose them."""
        if self._thread is None or not self._thread.is_alive():
            return
        deadline = time.monotonic() + FLUSH_SECONDS
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.05)

    def send(self, payload):
        """Posts one payload. Never raises."""
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            if response.status_code == 429:
                time.sleep(min(float(response.json().get("retry_after", 1)), 30))
                response = requests.post(self.webhook_url, json=payload, timeout=5)
            if response.status_code >= 400:
                self._stderr(
                    f"Discord alert failed: HTTP {response.status_code} {response.text[:200]}"
                )
        except Exception as e:
            self._stderr(f"Discord alert failed: {type(e).__name__}: {e}")

    def _stderr(self, message):
        # requests errors include the URL path, which holds the webhook token
        secret = urlsplit(self.webhook_url).path.rstrip("/") or self.webhook_url
        if secret:
            message = message.replace(secret, "/<webhook>")
        print(message, file=sys.stderr)
