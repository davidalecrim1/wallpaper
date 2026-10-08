#!/usr/bin/env python3
"""Download the curated picks as 3840px standard-size JPEGs.

Originals are throttled by Wikimedia; 3840px is the largest standard thumbnail
width and still satisfies the 4K requirement (3840 x >=2160).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import commons  # noqa: E402

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CACHE = os.path.join(ROOT, ".cache")
PICKS = os.path.join(CACHE, "picks.json")

STOPWORDS = {"file", "the", "of", "in", "at", "and", "a", "an", "on", "de", "la", "el", "photo", "by"}


def slug(title: str, place: str) -> str:
    text = re.sub(r"^File:", "", title)
    text = re.sub(r"\.(jpe?g|png)$", "", text, flags=re.I)
    text = re.sub(r"^\d+[\s\-_]+", "", text)          # leading catalogue numbers
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    parts = [p for p in text.split("-") if p and p not in STOPWORDS]
    text = "-".join(parts[:6])
    if place in text:
        text = text.replace(place, "").strip("-")
        text = re.sub(r"-+", "-", text)
    return text or "image"


def download(url: str, dest: str) -> bool:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": commons.USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as fh:
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    fh.write(chunk)
            return os.path.getsize(dest) > 50_000
        except Exception as exc:  # noqa: BLE001
            wait = 10 * (attempt + 1)
            print(f"    retry {attempt + 1} in {wait}s: {exc}", file=sys.stderr)
            time.sleep(wait)
    return False


def main() -> None:
    picks = json.load(open(PICKS))
    manifest = []
    outdir = os.path.join(ROOT, "images")
    os.makedirs(outdir, exist_ok=True)
    for place, rows in picks.items():
        for index, row in enumerate(rows, start=1):
            fname = f"{place}-{index:02d}-{slug(row['title'], place)}.jpg"
            dest = os.path.join(outdir, fname)
            rel = os.path.relpath(dest, ROOT)
            if os.path.exists(dest) and os.path.getsize(dest) > 50_000:
                print(f"  = {rel}")
            else:
                # Wide panoramas render shorter than 2160px at 3840 wide, so
                # fetch the original instead to stay at or above 4K.
                url = (row["url"].split("?")[0] if row["aspect"] > 3840 / 2160
                       else commons.thumb_url(row["url"], 3840))
                print(f"  > {rel}")
                if not download(url, dest):
                    print(f"    FAILED {rel}", file=sys.stderr)
                    continue
                time.sleep(2)
            manifest.append(dict(row, file=rel))
    json.dump(manifest, open(os.path.join(CACHE, "manifest.json"), "w"), indent=1)
    print(f"\ndownloaded {len(manifest)} files")


if __name__ == "__main__":
    main()
