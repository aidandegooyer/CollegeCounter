"""Refresh due matches from their platforms; see cc.views.match_sync."""

import logging
import time

from django.core.management.base import BaseCommand
from django.db import connection

from cc.images import StorageError, is_configured, mirror_pending
from cc.views.match_sync import sync_due_matches

logger = logging.getLogger(__name__)

PASS_SECONDS = 30
# Arbitrary constant identifying this job's Postgres advisory lock
LOCK_ID = 7_210_431

# The loop also copies pictures hosted elsewhere (new imports, pasted URLs)
# into the image bucket, a few at a time, at most once an hour (cc.images).
# The first copy of everything is the mirror_images command.
PICTURE_SWEEP_SECONDS = 3600
PICTURE_SWEEP_LIMIT = 25
# A picture that couldn't be copied is tried again after a day
PICTURE_RETRY_SECONDS = 86400


class Command(BaseCommand):
    help = "Refresh matches from Faceit, LeagueSpot and Regents League by how live or soon they are"

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop",
            action="store_true",
            help=f"Keep running, one pass every {PASS_SECONDS}s (default: a single pass)",
        )

    def handle(self, *args, **options):
        if not options["loop"]:
            self.run_pass()
            return

        self.stdout.write("Match sync started")
        self.last_picture_sweep = None
        self.picture_failures = {}  # URL -> when it last failed
        while True:
            started = time.monotonic()
            try:
                self.run_pass()
            except Exception:
                # Keep the worker alive through database or platform outages
                logger.exception("Match sync pass failed")
                # Start the next pass on a fresh connection (closing it also
                # drops the advisory lock)
                try:
                    connection.close()
                except Exception:
                    logger.exception("Couldn't close the database connection")
            self.maybe_mirror_pictures()
            time.sleep(max(0, PASS_SECONDS - (time.monotonic() - started)))

    def run_pass(self):
        if not self.acquire_lock():
            logger.info("Another match sync is running; skipping this pass")
            return
        try:
            summary = sync_due_matches()
        finally:
            try:
                self.release_lock()
            except Exception:
                # Don't hide whatever broke the pass; the lock goes with
                # the connection, which the loop closes
                logger.exception("Couldn't release the match sync lock")

        activity = {key: count for key, count in summary.items() if count}
        if activity:
            message = ", ".join(f"{key}={count}" for key, count in sorted(activity.items()))
            failed = any(key.endswith(":failed") for key in activity)
            logger.log(logging.WARNING if failed else logging.INFO, "Match sync: %s", message)
            self.stdout.write(message)

    def maybe_mirror_pictures(self):
        now = time.monotonic()
        if not is_configured() or (
            self.last_picture_sweep is not None
            and now - self.last_picture_sweep < PICTURE_SWEEP_SECONDS
        ):
            return
        self.last_picture_sweep = now
        self.picture_failures = {
            url: failed_at
            for url, failed_at in self.picture_failures.items()
            if now - failed_at < PICTURE_RETRY_SECONDS
        }
        try:
            copied, failed = mirror_pending(
                limit=PICTURE_SWEEP_LIMIT, skip=self.picture_failures
            )
        except StorageError:
            logger.warning("Couldn't store pictures; trying again in an hour", exc_info=True)
            return
        except Exception:
            # Never let pictures take the match sync down
            logger.exception("Picture sweep failed")
            return
        self.picture_failures.update(dict.fromkeys(failed, now))
        if copied or failed:
            message = f"Pictures: copied {copied}, {len(failed)} couldn't be copied"
            logger.info(message)
            self.stdout.write(message)

    # Two workers (e.g. during a deploy) would refresh every match twice
    def acquire_lock(self):
        if connection.vendor != "postgresql":
            return True
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_ID])
            return cursor.fetchone()[0]

    def release_lock(self):
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])
