"""Copy external team/player/event pictures into our bucket; see cc.images."""

from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from cc.images import StorageError, is_configured, mirror_pending, pending_pictures


class Command(BaseCommand):
    help = (
        "Copy pictures hosted elsewhere (Faceit, Firebase, ...) into the image "
        "bucket, resized, and point the rows at the copies"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be copied, by host, without copying anything",
        )
        parser.add_argument(
            "--limit", type=int, help="Copy at most this many pictures (default: all)"
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.dry_run(options["limit"])
            return
        if not is_configured():
            raise CommandError("Set IMAGE_STORAGE_BUCKET and IMAGE_CDN_BASE_URL first")

        try:
            copied, failed = mirror_pending(limit=options["limit"])
        except StorageError as e:
            raise CommandError(f"Image storage failed: {e}") from e

        for url in failed:
            self.stdout.write(f"  couldn't copy {url}")
        self.stdout.write(f"Pictures copied: {copied}, couldn't be copied: {len(failed)}")

    def dry_run(self, limit):
        pending = list(pending_pictures())[:limit]
        by_kind = Counter(kind for kind, _ in pending)
        by_host = Counter(
            row.picture.split("/")[2] if "://" in row.picture else "(not a URL)"
            for _, row in pending
        )
        kinds = ", ".join(f"{kind}={count}" for kind, count in sorted(by_kind.items()))
        self.stdout.write(f"Pictures to copy: {len(pending)} ({kinds or 'none'})")
        for host, count in by_host.most_common():
            self.stdout.write(f"  {count:5d}  {host}")
