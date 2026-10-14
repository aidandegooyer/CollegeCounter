"""Refresh due matches from their platforms; see cc.views.match_sync."""

import logging
import time

from django.core.management.base import BaseCommand
from django.db import connection

from cc.views.match_sync import sync_due_matches

logger = logging.getLogger(__name__)

PASS_SECONDS = 30
# Arbitrary constant identifying this job's Postgres advisory lock
LOCK_ID = 7_210_431


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
        while True:
            started = time.monotonic()
            try:
                self.run_pass()
            except Exception:
                # Keep the worker alive through database or platform outages
                logger.exception("Match sync pass failed")
                connection.close()
            time.sleep(max(0, PASS_SECONDS - (time.monotonic() - started)))

    def run_pass(self):
        if not self.acquire_lock():
            logger.info("Another match sync is running; skipping this pass")
            return
        try:
            summary = sync_due_matches()
        finally:
            self.release_lock()

        activity = {key: count for key, count in summary.items() if count}
        if activity:
            message = ", ".join(f"{key}={count}" for key, count in sorted(activity.items()))
            logger.info("Match sync: %s", message)
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
