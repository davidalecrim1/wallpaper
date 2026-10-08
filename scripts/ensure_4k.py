#!/usr/bin/env python3
"""Ensure every image in images/ is 4K (>=3840 x >=2160) and not oversized.

Two corrections:
  * a 3840px-wide thumbnail of a panorama (aspect > 16:9) is shorter than 2160px,
    so fetch the original;
  * originals can be huge (and GitHub rejects files >100MB), so resample to the
    smallest width that keeps height >= 2160 (never below 4608) and re-encode.
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import commons  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE = os.path.join(ROOT, ".cache")
MAX_BYTES = 50_000_000


def dimensions(path: str):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                         capture_output=True, text=True).stdout
    try:
        return (int(re.search(r"pixelWidth:\s*(\d+)", out).group(1)),
                int(re.search(r"pixelHeight:\s*(\d+)", out).group(1)))
    except AttributeError:
        return None


def metadata() -> dict[str, dict]:
    rows = []
    for name in ("switzerland.json", "manifest.json"):
        path = os.path.join(CACHE, name)
        if os.path.exists(path):
            rows.extend(json.load(open(path)))
    return {os.path.normpath(r["file"]): r for r in rows}


def fetch(url: str, dest: str) -> bool:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": commons.USER_AGENT})
            with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as fh:
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    fh.write(chunk)
            return os.path.getsize(dest) > 50_000
        except Exception as exc:  # noqa: BLE001
            wait = 15 * (attempt + 1)
            print(f"    retry {attempt + 1} in {wait}s: {exc}", file=sys.stderr)
            time.sleep(wait)
    return False


def resample(path: str, width: int) -> None:
    tmp = path + ".tmp.jpg"
    subprocess.run(["sips", "--resampleWidth", str(width), "--out", tmp, path],
                   capture_output=True)
    if os.path.exists(tmp) and os.path.getsize(tmp) > 50_000:
        os.replace(tmp, path)
    elif os.path.exists(tmp):
        os.remove(tmp)


def main() -> None:
    meta = metadata()
    fixed, failed, ok = [], [], 0
    for path in sorted(glob.glob(os.path.join(ROOT, "images", "*.jpg"))):
        d = dimensions(path)
        size = os.path.getsize(path)
        below = d is None or d[0] < 3840 or d[1] < 2160
        oversize = size > MAX_BYTES
        if not below and not oversize:
            ok += 1
            continue
        rel = os.path.normpath(os.path.relpath(path, ROOT))
        row = meta.get(rel)
        if below and row:
            print(f"  fetching original for {rel} ({d[0]}x{d[1]})")
            fetch(row["url"].split("?")[0], path)
            d = dimensions(path)
        if d and (os.path.getsize(path) > MAX_BYTES or d[0] > 6000):
            aspect = d[0] / d[1]
            target = min(d[0], max(4608, int(2160 * aspect) + 1))
            print(f"  resampling {rel} {d[0]}x{d[1]} -> width {target}")
            resample(path, target)
            d = dimensions(path)
        if d and d[0] >= 3840 and d[1] >= 2160:
            fixed.append(rel)
        else:
            failed.append(rel)
        time.sleep(3)
    print(f"\nok: {ok}, fixed: {len(fixed)}, failed: {len(failed)}")
    for f in failed:
        print(f"  FAILED {f}", file=sys.stderr)


if __name__ == "__main__":
    main()
