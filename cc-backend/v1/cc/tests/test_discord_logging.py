import logging
import sys
from unittest.mock import patch

from django.test import SimpleTestCase

from cc.discord_logging import COLORS, DESCRIPTION_LIMIT, DiscordWebhookHandler

from .helpers import fake_response


def make_handler(url="https://discord.test/hook", **kwargs):
    handler = DiscordWebhookHandler(url, **kwargs)
    # Tests read payloads off the queue instead of running the sender thread
    handler._start_thread = lambda: None
    return handler


def queued(handler):
    payloads = []
    while not handler._queue.empty():
        payloads.append(handler._queue.get_nowait())
    return payloads


def record(level=logging.ERROR, msg="boom", name="cc.views.x", lineno=10, exc_info=None):
    return logging.LogRecord(name, level, "/app/cc/views/x.py", lineno, msg, None, exc_info)


class DiscordWebhookHandlerTests(SimpleTestCase):
    def test_no_url_sends_nothing(self):
        handler = make_handler(url="")
        handler.emit(record())
        self.assertEqual(queued(handler), [])

    def test_warning_and_error_embeds(self):
        handler = make_handler()
        handler.emit(record(logging.WARNING, "slow", lineno=1))
        handler.emit(record(logging.ERROR, "broke", lineno=2))
        warning, error = [p["embeds"][0] for p in queued(handler)]
        self.assertEqual(warning["title"], "WARNING in cc.views.x")
        self.assertEqual(warning["color"], COLORS[logging.WARNING])
        self.assertEqual(warning["description"], "slow")
        self.assertEqual(error["color"], COLORS[logging.ERROR])
        self.assertEqual(error["fields"][1]["value"], "x.py:2")

    def test_exception_includes_traceback(self):
        try:
            raise ValueError("bad value")
        except ValueError:
            exc_info = sys.exc_info()
        handler = make_handler()
        handler.emit(record(exc_info=exc_info))
        description = queued(handler)[0]["embeds"][0]["description"]
        self.assertIn("ValueError: bad value", description)
        self.assertTrue(description.endswith("```"))

    def test_long_message_is_truncated(self):
        handler = make_handler()
        handler.emit(record(msg="x" * 10_000))
        description = queued(handler)[0]["embeds"][0]["description"]
        self.assertLessEqual(len(description), 4096)
        self.assertTrue(description.endswith("…"))

    def test_long_traceback_keeps_the_end(self):
        try:
            raise ValueError("the real error")
        except ValueError:
            exc_info = sys.exc_info()
        handler = make_handler()
        handler.emit(record(msg="x" * 10_000, exc_info=exc_info))
        description = queued(handler)[0]["embeds"][0]["description"]
        self.assertLessEqual(len(description), 4096)
        self.assertIn("ValueError: the real error", description)

    def test_repeats_are_collapsed_until_cooldown(self):
        handler = make_handler(cooldown_seconds=600)
        with patch("cc.discord_logging.time.monotonic", return_value=1000):
            handler.emit(record(msg="first"))
            handler.emit(record(msg="second"))
            handler.emit(record(msg="third"))
            # A different line isn't collapsed with the others
            handler.emit(record(msg="elsewhere", lineno=99))
        self.assertEqual(
            [p["embeds"][0]["description"] for p in queued(handler)], ["first", "elsewhere"]
        )

        with patch("cc.discord_logging.time.monotonic", return_value=1601):
            handler.emit(record(msg="later"))
        self.assertEqual(
            queued(handler)[0]["embeds"][0]["description"],
            "later\n\n(+2 similar suppressed)",
        )

    def test_full_queue_drops_records(self):
        handler = make_handler(cooldown_seconds=0)
        for lineno in range(150):
            handler.emit(record(lineno=lineno))
        self.assertEqual(len(queued(handler)), 100)


class SendTests(SimpleTestCase):
    def test_posts_payload(self):
        handler = make_handler()
        with patch("cc.discord_logging.requests.post", return_value=fake_response()) as post:
            handler.send({"embeds": []})
        post.assert_called_once_with("https://discord.test/hook", json={"embeds": []}, timeout=5)

    def test_request_failure_does_not_raise(self):
        handler = make_handler()
        with patch("cc.discord_logging.requests.post", side_effect=ConnectionError("down")), patch(
            "sys.stderr"
        ):
            handler.send({"embeds": []})

    def test_retries_once_when_rate_limited(self):
        handler = make_handler()
        limited = fake_response(status_code=429, json_data={"retry_after": 0.01})
        with patch(
            "cc.discord_logging.requests.post", side_effect=[limited, fake_response()]
        ) as post, patch("cc.discord_logging.time.sleep") as sleep:
            handler.send({"embeds": []})
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(0.01)


class LoggingConfigTests(SimpleTestCase):
    def discord_handler(self, logger_name):
        return next(
            h
            for h in logging.getLogger(logger_name).handlers
            if isinstance(h, DiscordWebhookHandler)
        )

    def test_app_warnings_reach_discord(self):
        handler = self.discord_handler("cc")
        with patch.object(handler, "webhook_url", "https://discord.test/hook"), patch.object(
            handler, "_start_thread"
        ):
            logging.getLogger("cc.views.proxies").warning("NWES returned 503")
            self.assertEqual(len(queued(handler)), 1)

    def test_request_404s_skipped_but_500s_sent(self):
        handler = self.discord_handler("django.request")
        with patch.object(handler, "webhook_url", "https://discord.test/hook"), patch.object(
            handler, "_start_thread"
        ):
            logging.getLogger("django.request").warning("Not Found: /nope")
            self.assertEqual(queued(handler), [])
            logging.getLogger("django.request").error("Internal Server Error: /api")
            self.assertEqual(len(queued(handler)), 1)
