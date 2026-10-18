import hashlib
import io
from datetime import timedelta
from unittest.mock import patch

import requests
from botocore.exceptions import EndpointConnectionError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from cc import image_views, images
from cc.management.commands import sync_matches
from cc.models import CustomEvent, Event, Player, Team

from .helpers import admin_settings, dev_client, fake_response, token_client

CDN = "https://img.test"
storage_settings = override_settings(
    IMAGE_STORAGE_BUCKET="pics", IMAGE_CDN_BASE_URL=CDN, IMAGE_STORAGE_ACL=""
)
FACEIT_URL = "https://distribution.faceit-cdn.net/images/logo.jpeg"
PUBLIC_ADDRESS = [(2, 1, 6, "", ("93.184.216.34", 443))]


def png(size=(600, 300), mode="RGBA", color=(255, 0, 0, 128)):
    out = io.BytesIO()
    Image.new(mode, size, color).save(out, "PNG")
    return out.getvalue()


def short_hash(data):
    return hashlib.sha256(data).hexdigest()[:12]


class FakeS3:
    """Keeps put_object calls by key."""

    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[Key] = {"Bucket": Bucket, "Body": Body, **kwargs}


class FakeS3Mixin:
    def setUp(self):
        super().setUp()
        self.s3 = FakeS3()
        patcher = patch.object(images, "_client", return_value=self.s3)
        patcher.start()
        self.addCleanup(patcher.stop)


def image_response(content, status_code=200, location=None):
    response = fake_response(
        status_code=status_code, headers={"Location": location} if location else {}
    )
    response.is_redirect = location is not None
    response.iter_content.return_value = [content]
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


@storage_settings
class StorePictureTests(FakeS3Mixin, SimpleTestCase):
    def test_writes_every_size_as_webp_and_returns_the_largest(self):
        data = png((600, 300))
        url = images.store_picture("teams", "abc", data)

        prefix = f"teams/abc/{short_hash(data)}"
        self.assertEqual(url, f"{CDN}/{prefix}/512.webp")
        self.assertEqual(
            set(self.s3.objects),
            {
                f"{prefix}/{name}"
                for name in ("original", "64.webp", "128.webp", "256.webp", "512.webp")
            },
        )
        for width in images.WIDTHS:
            stored = self.s3.objects[f"{prefix}/{width}.webp"]
            image = Image.open(io.BytesIO(stored["Body"]))
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (width, width // 2))
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(stored["ContentType"], "image/webp")
            self.assertEqual(stored["CacheControl"], images.CACHE_CONTROL)
            self.assertNotIn("ACL", stored)
        original = self.s3.objects[f"{prefix}/original"]
        self.assertEqual(original["Body"], data)
        self.assertEqual(original["ContentType"], "image/png")

    def test_never_enlarges(self):
        data = png((100, 100), mode="RGB", color=(0, 0, 255))
        images.store_picture("players", "p1", data)
        stored = self.s3.objects[f"players/p1/{short_hash(data)}/512.webp"]
        image = Image.open(io.BytesIO(stored["Body"]))
        self.assertEqual(image.size, (100, 100))
        self.assertEqual(image.mode, "RGB")

    def test_same_picture_same_url(self):
        data = png()
        self.assertEqual(
            images.store_picture("teams", "abc", data),
            images.store_picture("teams", "abc", data),
        )

    @override_settings(IMAGE_STORAGE_ACL="public-read")
    def test_acl_and_source_url(self):
        images.store_picture("teams", "abc", png(), source_url=FACEIT_URL)
        for stored in self.s3.objects.values():
            self.assertEqual(stored["ACL"], "public-read")
            self.assertEqual(stored["Metadata"], {"source-url": FACEIT_URL})

    def test_rejects_non_images(self):
        with self.assertRaises(images.ImageError):
            images.store_picture("teams", "abc", b"<svg></svg>")
        self.assertEqual(self.s3.objects, {})

    def test_rejects_large_files_and_dimensions(self):
        with (
            patch.object(images, "MAX_BYTES", 10),
            self.assertRaises(images.ImageError),
        ):
            images.store_picture("teams", "abc", png())
        with (
            patch.object(images, "MAX_PIXELS", 100),
            self.assertRaises(images.ImageError),
        ):
            images.store_picture("teams", "abc", png())
        self.assertEqual(self.s3.objects, {})

    def test_is_hosted(self):
        self.assertTrue(images.is_hosted(f"{CDN}/teams/abc/0123456789ab/512.webp"))
        self.assertFalse(images.is_hosted(FACEIT_URL))
        self.assertFalse(images.is_hosted("https://img.test.evil.com/x.webp"))
        self.assertFalse(images.is_hosted(None))


class FetchImageTests(SimpleTestCase):
    def setUp(self):
        patcher = patch.object(
            images.socket, "getaddrinfo", return_value=PUBLIC_ADDRESS
        )
        self.getaddrinfo = patcher.start()
        self.addCleanup(patcher.stop)

    def test_downloads(self):
        with patch.object(
            images.requests, "get", return_value=image_response(b"data")
        ) as get:
            self.assertEqual(images.fetch_image(FACEIT_URL), b"data")
        self.assertEqual(get.call_args.args[0], FACEIT_URL)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    def test_only_https(self):
        with patch.object(images.requests, "get") as get:
            for url in ("http://example.com/a.png", "file:///etc/passwd", "not a url"):
                with self.assertRaises(images.ImageError):
                    images.fetch_image(url)
        get.assert_not_called()

    def test_refuses_private_addresses(self):
        for address in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "::1"):
            self.getaddrinfo.return_value = [(10, 1, 6, "", (address, 443))]
            with (
                patch.object(images.requests, "get") as get,
                self.assertRaises(images.ImageError),
            ):
                images.fetch_image("https://sneaky.example/a.png")
            get.assert_not_called()

    def test_checks_every_redirect(self):
        self.getaddrinfo.side_effect = lambda host, port: (
            [(2, 1, 6, "", ("10.0.0.5", 443))]
            if host == "internal.example"
            else PUBLIC_ADDRESS
        )
        redirect = image_response(b"", 302, location="https://internal.example/secret")
        with patch.object(images.requests, "get", return_value=redirect) as get:
            with self.assertRaises(images.ImageError):
                images.fetch_image(FACEIT_URL)
        get.assert_called_once()

    def test_follows_a_public_redirect(self):
        responses = [
            image_response(b"", 301, location="/moved.png"),
            image_response(b"data"),
        ]
        with patch.object(images.requests, "get", side_effect=responses) as get:
            self.assertEqual(images.fetch_image(FACEIT_URL), b"data")
        self.assertEqual(
            get.call_args.args[0], "https://distribution.faceit-cdn.net/moved.png"
        )

    def test_stops_downloading_past_the_size_cap(self):
        response = image_response(b"")
        response.iter_content.return_value = [b"x" * 8, b"x" * 8]
        with (
            patch.object(images, "MAX_BYTES", 10),
            patch.object(images.requests, "get", return_value=response),
            self.assertRaises(images.ImageError),
        ):
            images.fetch_image(FACEIT_URL)

    def test_gives_up_on_a_slow_download(self):
        with (
            # Already past the deadline when the first chunk arrives
            patch.object(images, "FETCH_DEADLINE", -1),
            patch.object(images.requests, "get", return_value=image_response(b"x")),
            self.assertRaisesMessage(images.ImageError, "Download took over"),
        ):
            images.fetch_image(FACEIT_URL)


@storage_settings
class MirrorTests(FakeS3Mixin, TestCase):
    def make_event(self, picture):
        now = timezone.now()
        return Event.objects.create(
            name="Cup",
            start_date=now,
            end_date=now + timedelta(days=1),
            picture=picture,
        )

    def test_copies_external_pictures_and_skips_ours(self):
        team = Team.objects.create(name="Alpha", picture=FACEIT_URL)
        event = self.make_event("https://i.ibb.co/x/cup.png")
        hosted = f"{CDN}/players/p/0123456789ab/512.webp"
        Player.objects.create(name="hosted", picture=hosted)
        Player.objects.create(name="none", picture=None)
        Player.objects.create(name="empty", picture="")

        with patch.object(images, "fetch_image", return_value=png()) as fetch:
            copied, failed = images.mirror_pending()

        self.assertEqual((copied, failed), (2, {}))
        self.assertEqual(
            sorted(call.args[0] for call in fetch.call_args_list),
            sorted([FACEIT_URL, "https://i.ibb.co/x/cup.png"]),
        )
        team.refresh_from_db()
        event.refresh_from_db()
        self.assertTrue(team.picture.startswith(f"{CDN}/teams/{team.pk}/"))
        self.assertTrue(event.picture.startswith(f"{CDN}/events/{event.pk}/"))
        self.assertEqual(Player.objects.get(name="hosted").picture, hosted)
        stored = self.s3.objects[team.picture.removeprefix(CDN + "/")]
        self.assertEqual(stored["Metadata"], {"source-url": FACEIT_URL})

    def test_dead_link_is_left_alone_quietly(self):
        team = Team.objects.create(name="Alpha", picture=FACEIT_URL)
        error = requests.HTTPError("404 Client Error: Not Found")
        with (
            patch.object(images, "fetch_image", side_effect=error),
            self.assertLogs(images.logger, "INFO") as logs,
        ):
            copied, failed = images.mirror_pending()
        self.assertEqual(
            (copied, failed), (0, {FACEIT_URL: "404 Client Error: Not Found"})
        )
        self.assertIn("404 Client Error", logs.output[0])
        self.assertEqual(logs.records[0].levelname, "INFO")
        team.refresh_from_db()
        self.assertEqual(team.picture, FACEIT_URL)

    def test_an_unexpected_error_skips_just_that_picture(self):
        Team.objects.create(name="Alpha", picture=FACEIT_URL)
        Team.objects.create(name="Bravo", picture=FACEIT_URL + "?2")
        with (
            patch.object(
                images, "fetch_image", side_effect=[RuntimeError("bug"), png()]
            ),
            self.assertLogs(images.logger, "ERROR"),
        ):
            copied, failed = images.mirror_pending()
        self.assertEqual((copied, len(failed)), (1, 1))

    def test_unconvertible_image_is_an_image_error(self):
        out = io.BytesIO()
        Image.new("I;16", (10, 10)).save(out, "PNG")
        with patch.object(Image.Image, "convert", side_effect=ValueError("no")):
            with self.assertRaises(images.ImageError):
                images.store_picture("teams", "t", out.getvalue())

    def test_limit_and_skip(self):
        urls = [f"https://distribution.faceit-cdn.net/{n}.png" for n in range(3)]
        for n, url in enumerate(urls):
            Team.objects.create(name=f"T{n}", picture=url)
        with patch.object(images, "fetch_image", return_value=png()) as fetch:
            copied, failed = images.mirror_pending(limit=1, skip={urls[0], urls[1]})
        self.assertEqual((copied, failed), (1, {}))
        fetch.assert_called_once_with(urls[2])

    def test_starts_no_copy_past_the_time_budget(self):
        for n in range(3):
            Team.objects.create(name=f"T{n}", picture=f"{FACEIT_URL}?{n}")
        with (
            patch.object(images, "fetch_image", return_value=png()) as fetch,
            # Start, first picture at 0s, second at 100s
            patch.object(images, "time") as clock,
        ):
            clock.monotonic.side_effect = [0, 0, 100]
            copied, failed = images.mirror_pending(time_budget=20)
        self.assertEqual((copied, failed), (1, {}))
        fetch.assert_called_once()

    def test_reports_a_picture_changed_while_copying(self):
        team = Team.objects.create(name="Alpha", picture=FACEIT_URL)
        with patch.object(images, "mirror_picture", return_value=False):
            copied, failed = images.mirror_pending()
        self.assertEqual(copied, 0)
        self.assertIn("changed while copying", failed[team.picture])

    def test_storage_failure_stops_the_sweep(self):
        Team.objects.create(name="Alpha", picture=FACEIT_URL)
        Team.objects.create(name="Bravo", picture=FACEIT_URL + "?2")
        with (
            patch.object(images, "fetch_image", return_value=png()) as fetch,
            patch.object(
                self.s3,
                "put_object",
                side_effect=EndpointConnectionError(endpoint_url="x"),
            ),
            self.assertRaises(images.StorageError),
        ):
            images.mirror_pending()
        fetch.assert_called_once()
        self.assertEqual(Team.objects.filter(picture__startswith=CDN).count(), 0)

    def test_keeps_a_picture_changed_while_copying(self):
        team = Team.objects.create(name="Alpha", picture=FACEIT_URL)

        def admin_changes_it(url):
            Team.objects.filter(pk=team.pk).update(picture="https://new.example/a.png")
            return png()

        with patch.object(images, "fetch_image", side_effect=admin_changes_it):
            self.assertFalse(images.mirror_picture("teams", team))
        team.refresh_from_db()
        self.assertEqual(team.picture, "https://new.example/a.png")


class MirrorCommandTests(FakeS3Mixin, TestCase):
    def call(self, *args):
        out = io.StringIO()
        call_command("mirror_images", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_counts_by_host(self):
        Team.objects.create(name="Alpha", picture=FACEIT_URL)
        Player.objects.create(name="p", picture=FACEIT_URL)
        Player.objects.create(
            name="q", picture="https://firebasestorage.googleapis.com/x"
        )
        with patch.object(images, "fetch_image") as fetch:
            output = self.call("--dry-run")
        fetch.assert_not_called()
        self.assertIn("Pictures to copy: 3 (players=2, teams=1)", output)
        self.assertIn("2  distribution.faceit-cdn.net", output)

    def test_needs_storage(self):
        with self.assertRaises(CommandError):
            self.call()

    @storage_settings
    def test_copies_and_lists_failures(self):
        Team.objects.create(name="Alpha", picture=FACEIT_URL)
        Team.objects.create(name="Bravo", picture="https://gone.example/a.png")

        def fetch(url):
            if "gone" in url:
                raise requests.ConnectionError("no route")
            return png()

        with patch.object(images, "fetch_image", side_effect=fetch):
            output = self.call()
        self.assertIn("couldn't copy https://gone.example/a.png: no route", output)
        self.assertIn("Pictures copied: 1, couldn't be copied: 1", output)

    @storage_settings
    def test_storage_failure_is_a_command_error(self):
        Team.objects.create(name="Alpha", picture=FACEIT_URL)
        with (
            patch.object(images, "fetch_image", return_value=png()),
            patch.object(
                self.s3,
                "put_object",
                side_effect=EndpointConnectionError(endpoint_url="x"),
            ),
            self.assertRaises(CommandError),
        ):
            self.call()


@admin_settings
@storage_settings
class UploadPictureTests(FakeS3Mixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = dev_client()
        self.team = Team.objects.create(name="Alpha", picture=FACEIT_URL)

    def upload(self, name, obj_id, data=None, client=None):
        files = {}
        if data is not None:
            files["picture"] = SimpleUploadedFile(
                "logo.png", data, content_type="image/png"
            )
        return (client or self.client).post(
            reverse(name, args=[obj_id]), files, format="multipart"
        )

    def test_team(self):
        data = png()
        response = self.upload("upload_team_picture", self.team.id, data)
        self.assertEqual(response.status_code, 200)
        url = f"{CDN}/teams/{self.team.id}/{short_hash(data)}/512.webp"
        self.assertEqual(response.json()["picture_url"], url)
        self.team.refresh_from_db()
        self.assertEqual(self.team.picture, url)

    def test_player(self):
        player = Player.objects.create(name="p")
        response = self.upload("upload_player_picture", player.id, png())
        self.assertEqual(response.status_code, 200)
        player.refresh_from_db()
        self.assertTrue(player.picture.startswith(f"{CDN}/players/{player.id}/"))

    def test_event(self):
        now = timezone.now()
        event = Event.objects.create(name="Cup", start_date=now, end_date=now)
        custom_event = CustomEvent.objects.create(event=event)
        response = self.upload("upload_event_picture", custom_event.id, png())
        self.assertEqual(response.status_code, 200)
        event.refresh_from_db()
        self.assertTrue(event.picture.startswith(f"{CDN}/events/{event.id}/"))

    def test_needs_admin(self):
        client, patcher = token_client({"role": "base"})
        self.addCleanup(patcher.stop)
        response = self.upload(
            "upload_team_picture", self.team.id, png(), client=client
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.s3.objects, {})

    def test_bad_requests(self):
        self.assertEqual(
            self.upload("upload_team_picture", self.team.id).status_code, 400
        )
        response = self.upload("upload_team_picture", self.team.id, b"not an image")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Not a supported image")
        missing = self.upload(
            "upload_team_picture", "00000000-0000-0000-0000-000000000000", png()
        )
        self.assertEqual(missing.status_code, 404)
        self.team.refresh_from_db()
        self.assertEqual(self.team.picture, FACEIT_URL)

    def test_refuses_an_oversized_upload_before_reading_it(self):
        with (
            patch.object(image_views, "MAX_BYTES", 10),
            patch.object(image_views, "store_picture") as store,
        ):
            response = self.upload("upload_team_picture", self.team.id, png())
        self.assertEqual(response.status_code, 400)
        self.assertIn("Picture is over", response.json()["error"])
        store.assert_not_called()

    @override_settings(IMAGE_STORAGE_BUCKET="")
    def test_unconfigured(self):
        response = self.upload("upload_team_picture", self.team.id, png())
        self.assertEqual(response.status_code, 503)

    def test_storage_failure(self):
        with (
            patch.object(
                self.s3,
                "put_object",
                side_effect=EndpointConnectionError(endpoint_url="x"),
            ),
            self.assertLogs("cc.image_views", "ERROR"),
        ):
            response = self.upload("upload_team_picture", self.team.id, png())
        self.assertEqual(response.status_code, 502)
        self.team.refresh_from_db()
        self.assertEqual(self.team.picture, FACEIT_URL)


@storage_settings
class PictureSweepTests(SimpleTestCase):
    def setUp(self):
        self.out = io.StringIO()
        self.command = sync_matches.Command(stdout=self.out)
        self.command.last_picture_sweep = None
        self.command.picture_failures = {}

    def sweep_at(self, now, **mirror):
        with (
            patch.object(sync_matches.time, "monotonic", return_value=now),
            patch.object(sync_matches, "mirror_pending", **mirror) as mirror_pending,
        ):
            self.command.maybe_mirror_pictures()
        return mirror_pending

    def test_hourly_and_retries_failures_after_a_day(self):
        first = self.sweep_at(
            1000, return_value=(2, {"https://bad.example/a.png": "404 Not Found"})
        )
        first.assert_called_once()
        self.assertEqual(
            first.call_args.kwargs["time_budget"],
            sync_matches.PICTURE_SWEEP_BUDGET_SECONDS,
        )
        output = self.out.getvalue()
        self.assertIn("Pictures: copied 2, 1 couldn't be copied", output)
        self.assertIn("couldn't copy https://bad.example/a.png: 404 Not Found", output)

        self.sweep_at(1000 + 60, return_value=(0, {})).assert_not_called()

        next_hour = self.sweep_at(1000 + 3600, return_value=(0, {}))
        self.assertIn("https://bad.example/a.png", next_hour.call_args.kwargs["skip"])

        next_day = self.sweep_at(1000 + 86400, return_value=(0, {}))
        self.assertNotIn("https://bad.example/a.png", next_day.call_args.kwargs["skip"])

    def test_failures_dont_escape(self):
        with self.assertLogs(sync_matches.logger, "WARNING") as logs:
            self.sweep_at(0, side_effect=EndpointConnectionError(endpoint_url="x"))
        self.assertIn("Couldn't store pictures", logs.output[0])

        with self.assertLogs(sync_matches.logger, "ERROR") as logs:
            self.sweep_at(3600, side_effect=RuntimeError("db down"))
        self.assertIn("Picture sweep failed", logs.output[0])

    @override_settings(IMAGE_STORAGE_BUCKET="")
    def test_off_without_storage(self):
        self.sweep_at(0, return_value=(0, {})).assert_not_called()
