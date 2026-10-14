import io
import logging
import sys
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from cc.discord_logging import COLORS, MESSAGE_LIMIT, DiscordWebhookHandler

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


def capture_stderr():
    return patch("sys.stderr", new_callable=io.StringIO)


def record(level=logging.ERROR, msg="boom", name="cc.views.x", lineno=10, exc_info=None):
    return logging.LogRecord(name, level, "/app/cc/views/x.py", lineno, msg, None, exc_info)


def exc_info_for(error):
    try:
        raise error
    except type(error):
        return sys.exc_info()


class DiscordWebhookHandlerTests(SimpleTestCase):
    def test_no_url_sends_nothing(self):
        handler = make_handler(url="")
        handler.emit(record())
        self.assertEqual(queued(handler), [])

    def test_warns_when_disabled_if_asked(self):
        with capture_stderr() as stderr:
            make_handler(url="")
            self.assertEqual(stderr.getvalue(), "")
            make_handler(url="", warn_if_disabled=True)
        self.assertIn("Discord alerts are disabled", stderr.getvalue())

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
        handler = make_handler()
        handler.emit(record(exc_info=exc_info_for(ValueError("bad value"))))
        description = queued(handler)[0]["embeds"][0]["description"]
        self.assertIn("ValueError: bad value", description)
        self.assertTrue(description.endswith("```"))

    def test_exc_info_outside_except_adds_no_traceback(self):
        handler = make_handler()
        handler.emit(record(msg="boom", exc_info=(None, None, None)))
        self.assertEqual(queued(handler)[0]["embeds"][0]["description"], "boom")

    def test_long_message_is_truncated(self):
        handler = make_handler()
        handler.emit(record(msg="x" * 10_000))
        description = queued(handler)[0]["embeds"][0]["description"]
        self.assertEqual(len(description), MESSAGE_LIMIT + 1)
        self.assertTrue(description.endswith("…"))

    def test_long_message_and_traceback_fit_and_keep_the_code_block(self):
        class LongError(Exception):
            pass

        handler = make_handler()
        error = exc_info_for(LongError("y" * 10_000 + " the real error"))
        handler.emit(record(msg="x" * 10_000, exc_info=error))
        description = queued(handler)[0]["embeds"][0]["description"]
        self.assertLessEqual(len(description), 4096)
        self.assertIn("the real error", description)
        self.assertEqual(description.count("```"), 2)
        self.assertTrue(description.endswith("```"))

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

    def test_full_queue_drop_is_reported_and_counted(self):
        handler = make_handler()
        with capture_stderr() as stderr:
            for lineno in range(100):
                handler.emit(record(lineno=lineno))
            handler.emit(record(msg="dropped", lineno=500))
        self.assertIn("Discord alert dropped (queue full)", stderr.getvalue())
        self.assertEqual(len(queued(handler)), 100)

        # The drop didn't start a cooldown, and the next alert mentions it
        handler.emit(record(msg="retry", lineno=500))
        self.assertEqual(
            queued(handler)[0]["embeds"][0]["description"], "retry\n\n(+1 similar suppressed)"
        )


class SendTests(SimpleTestCase):
    def test_posts_payload(self):
        handler = make_handler()
        with patch("cc.discord_logging.requests.post", return_value=fake_response()) as post:
            handler.send({"embeds": []})
        post.assert_called_once_with("https://discord.test/hook", json={"embeds": []}, timeout=5)

    def test_request_failure_does_not_raise_or_leak_the_token(self):
        handler = make_handler(url="https://discord.com/api/webhooks/123/secret-token")
        error = requests.ConnectionError(
            "Max retries exceeded with url: /api/webhooks/123/secret-token"
        )
        with patch(
            "cc.discord_logging.requests.post", side_effect=error
        ), capture_stderr() as stderr:
            handler.send({"embeds": []})
        self.assertIn("ConnectionError", stderr.getvalue())
        self.assertNotIn("secret-token", stderr.getvalue())

    def test_http_error_reports_discords_reason(self):
        handler = make_handler()
        rejected = fake_response(status_code=404, text='{"message": "Unknown Webhook"}')
        with patch(
            "cc.discord_logging.requests.post", return_value=rejected
        ), capture_stderr() as stderr:
            handler.send({"embeds": []})
        self.assertIn("HTTP 404", stderr.getvalue())
        self.assertIn("Unknown Webhook", stderr.getvalue())

    def test_retries_once_when_rate_limited(self):
        handler = make_handler()
        limited = fake_response(status_code=429, json_data={"retry_after": 0.01})
        with patch(
            "cc.discord_logging.requests.post", side_effect=[limited, fake_response()]
        ) as post, patch("cc.discord_logging.time.sleep") as sleep:
            handler.send({"embeds": []})
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(0.01)


class SenderThreadTests(SimpleTestCase):
    def test_thread_posts_and_flush_waits_for_it(self):
        handler = DiscordWebhookHandler("https://discord.test/hook")
        with patch("cc.discord_logging.requests.post", return_value=fake_response()) as post:
            handler.emit(record(msg="from the thread"))
            handler.flush()
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["embeds"][0]["description"], "from the thread")

    def test_flush_without_thread_returns(self):
        DiscordWebhookHandler("https://discord.test/hook").flush()


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
