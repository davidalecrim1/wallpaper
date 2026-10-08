"""Shared Wikimedia Commons client with rate-limit handling.

Wikimedia throttles anonymous bulk access:
  * the API (commons.wikimedia.org/w/api.php) returns HTTP 429 on bursts;
  * upload.wikimedia.org rejects any direct request that is NOT one of the
    standard thumbnail widths (20, 40, 60, 120, 250, 330, 500, 960, 1280,
    1920, 3840 px). Full-resolution originals are throttled.
See docs/METHOD.md.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "WikiWallpaperCollector/1.0 (personal wallpaper collection; contact: davidalecrim1)"
STANDARD_THUMB_WIDTHS = (20, 40, 60, 120, 250, 330, 500, 960, 1280, 1920, 3840)
MIN_WIDTH = 3840          # "4K" floor
MIN_HEIGHT = 2160
MIN_BYTES = 1_500_000
ASPECT_RANGE = (1.2, 2.2)


def api(params: dict, tries: int = 6) -> dict:
    """GET the Commons API with maxlag and exponential backoff on 429."""
    params = dict(params, format="json", maxlag="5")
    url = API + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(data["error"].get("info", "api error"))
            return data
        except Exception as exc:  # noqa: BLE001 - transient rate limits
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"API request failed after {tries} tries: {last}")


def clean_html(value) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def thumb_url(original_url: str, width: int = 3840) -> str:
    """Rewrite an original file URL to a standard-size thumbnail URL."""
    if width not in STANDARD_THUMB_WIDTHS:
        raise ValueError(f"{width} is not a standard Wikimedia thumbnail width")
    url = original_url.split("?")[0]
    name = url.rsplit("/", 1)[1]
    return url.replace("/commons/", "/commons/thumb/", 1) + f"/{width}px-{name}"


def is_wallpaper_candidate(width: int, height: int, byte_size: int) -> bool:
    if width < MIN_WIDTH or height < MIN_HEIGHT or width <= height:
        return False
    if not ASPECT_RANGE[0] <= width / height <= ASPECT_RANGE[1]:
        return False
    return byte_size >= MIN_BYTES
