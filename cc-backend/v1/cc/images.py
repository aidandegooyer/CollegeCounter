"""
Team, player and event pictures, stored in our own bucket in a few fixed sizes.

Each picture is decoded, shrunk to fit within each of WIDTHS (never enlarged)
and saved as WebP, under a key built from a hash of the original bytes:

    teams/<team id>/<hash>/64.webp, 128.webp, 256.webp, 512.webp, original

The model's `picture` keeps a plain URL to the 512px copy, so everything that
reads it (the public API, older frontend builds) still gets a working image,
and the frontend swaps "512.webp" for the size it shows (src/lib/images.ts).
A new picture gets a new hash and so a new URL, which is what lets the CDN
and browsers cache every file forever.

Pictures on other hosts (mostly Faceit avatars from imports) are copied in by
mirror_pending(), from the mirror_images command and the match-sync loop.
"""

import functools
import hashlib
import io
import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlsplit

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Event, Player, Team

logger = logging.getLogger(__name__)

WIDTHS = (64, 128, 256, 512)
MAX_BYTES = 10 * 1024 * 1024
# Refuse anything bigger before decoding it (a small file can decode huge)
MAX_PIXELS = 40_000_000
CACHE_CONTROL = "public, max-age=31536000, immutable"
WEBP_QUALITY = 82
FETCH_TIMEOUT = 10
MAX_REDIRECTS = 3
# Same as proxy_image: some image hosts turn away requests without one
FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:144.0) Gecko/20100101 Firefox/144.0",
    "Accept": "image/avif,image/webp,image/png,image/*;q=0.8,*/*;q=0.5",
}

# Bucket prefix for each model with a picture
KINDS = {"teams": Team, "players": Player, "events": Event}

# What a failed upload or copy raises when the bucket itself is the problem
StorageError = (BotoCoreError, ClientError)


class ImageError(ValueError):
    """The picture can't be used: not an image, too big, or not fetchable."""


def is_configured():
    return bool(settings.IMAGE_STORAGE_BUCKET and settings.IMAGE_CDN_BASE_URL)


def is_hosted(url):
    """Whether `url` is already one of our copies."""
    base = settings.IMAGE_CDN_BASE_URL
    return bool(base and url and url.startswith(base + "/"))


@functools.cache
def _client():
    return boto3.client(
        "s3",
        region_name=settings.IMAGE_STORAGE_REGION,
        endpoint_url=settings.IMAGE_STORAGE_ENDPOINT_URL,
        aws_access_key_id=settings.IMAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.IMAGE_AWS_SECRET_ACCESS_KEY,
    )


def _decode(data):
    """
    Open `data` as an upright RGB or RGBA image (keeping transparency), with
    its original format, or raise ImageError.
    """
    if len(data) > MAX_BYTES:
        raise ImageError(f"Picture is over {MAX_BYTES // (1024 * 1024)} MB")
    try:
        image = Image.open(io.BytesIO(data))
        if image.width * image.height > MAX_PIXELS:
            raise ImageError("Picture dimensions are too large")
        image_format = image.format
        image.load()
        image = ImageOps.exif_transpose(image)
        has_alpha = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
        image = image.convert("RGBA" if has_alpha else "RGB")
    except ImageError:
        raise
    # ValueError: modes Pillow can't convert
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as e:
        raise ImageError("Not a supported image") from e
    return image, image_format


def _variants(image):
    """(width, WebP bytes) for each of WIDTHS."""
    for width in WIDTHS:
        resized = image.copy()
        resized.thumbnail((width, width), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        resized.save(out, "WEBP", quality=WEBP_QUALITY)
        yield width, out.getvalue()


def store_picture(kind, obj_id, data, source_url=None):
    """
    Save `data` as the picture of the `kind` object `obj_id` and return the
    URL to put in its `picture` field. Raises ImageError for bytes that aren't
    a usable image; storage failures raise one of StorageError.
    """
    image, image_format = _decode(data)
    prefix = f"{kind}/{obj_id}/{hashlib.sha256(data).hexdigest()[:12]}"
    extra = {"CacheControl": CACHE_CONTROL}
    if settings.IMAGE_STORAGE_ACL:
        extra["ACL"] = settings.IMAGE_STORAGE_ACL
    # S3 metadata is ASCII-only and size-limited
    if source_url and source_url.isascii() and len(source_url) <= 1024:
        extra["Metadata"] = {"source-url": source_url}

    client = _client()
    bucket = settings.IMAGE_STORAGE_BUCKET
    client.put_object(
        Bucket=bucket,
        Key=f"{prefix}/original",
        Body=data,
        ContentType=Image.MIME.get(image_format, "application/octet-stream"),
        **extra,
    )
    for width, body in _variants(image):
        client.put_object(
            Bucket=bucket,
            Key=f"{prefix}/{width}.webp",
            Body=body,
            ContentType="image/webp",
            **extra,
        )
    return f"{settings.IMAGE_CDN_BASE_URL}/{prefix}/{WIDTHS[-1]}.webp"


def _check_public_host(hostname):
    """Refuse hosts that resolve to private, loopback or link-local addresses."""
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(hostname, 443)}
    except (socket.gaierror, UnicodeError) as e:
        raise ImageError(f"Can't resolve {hostname}") from e
    for address in addresses:
        # Drop any IPv6 zone ("fe80::1%eth0") before parsing
        if not ipaddress.ip_address(address.split("%")[0]).is_global:
            raise ImageError(f"{hostname} isn't a public address")


def fetch_image(url):
    """
    Download an external picture, at most MAX_BYTES, from a public https host.
    Raises ImageError for a URL we won't fetch, requests' errors otherwise.
    """
    for _ in range(MAX_REDIRECTS + 1):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            raise ImageError("Only https pictures can be copied")
        _check_public_host(parts.hostname)
        # Redirects are followed by hand so each hop gets the host check
        response = requests.get(
            url,
            headers=FETCH_HEADERS,
            timeout=FETCH_TIMEOUT,
            stream=True,
            allow_redirects=False,
        )
        if response.is_redirect:
            url = urljoin(url, response.headers["Location"])
            response.close()
            continue
        with response:
            response.raise_for_status()
            chunks, total = [], 0
            for chunk in response.iter_content(64 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ImageError(f"Picture is over {MAX_BYTES // (1024 * 1024)} MB")
                chunks.append(chunk)
            return b"".join(chunks)
    raise ImageError("Too many redirects")


def mirror_picture(kind, obj):
    """
    Copy obj.picture into the bucket and point the row at the copy. Returns
    True if it was copied. A picture that can't be fetched or decoded is left
    as it is and logged at INFO, since it's one dead or odd link, not
    something to act on. Storage failures raise one of StorageError.
    """
    url = obj.picture
    try:
        data = fetch_image(url)
        new_url = store_picture(kind, obj.pk, data, source_url=url)
    except (requests.RequestException, ImageError) as e:
        logger.info("Couldn't copy %s picture %s: %s", kind, url, e)
        return False
    # Leave it if an admin changed the picture while this one was copying
    return bool(
        type(obj).objects.filter(pk=obj.pk, picture=url).update(picture=new_url)
    )


def pending_pictures():
    """(kind, row) for every picture that's set but isn't one of our copies."""
    base = settings.IMAGE_CDN_BASE_URL
    for kind, model in KINDS.items():
        rows = model.objects.exclude(picture__isnull=True).exclude(picture="")
        if base:
            rows = rows.exclude(picture__startswith=base + "/")
        yield from ((kind, row) for row in rows.only("pk", "picture").order_by("pk"))


def mirror_pending(limit=None, skip=()):
    """
    Copy up to `limit` external pictures into the bucket, passing over any
    URL in `skip`. Returns (number copied, URLs that failed). Storage
    failures stop the sweep and raise one of StorageError.
    """
    copied, failed = 0, []
    for kind, row in pending_pictures():
        if limit is not None and copied + len(failed) >= limit:
            break
        if row.picture in skip:
            continue
        try:
            ok = mirror_picture(kind, row)
        except StorageError:
            raise
        except Exception:
            # A bug with one picture shouldn't stop the rest
            logger.exception("Couldn't copy %s picture %s", kind, row.picture)
            ok = False
        if ok:
            copied += 1
        else:
            failed.append(row.picture)
    return copied, failed
