#!/usr/bin/env python3
"""Import manually-downloaded Unsplash images from the repo root into images/.

Re-fetches anything below 4K at 3840px, renames to <place>-NN-name.jpg and records
attribution in the metadata cache so build_docs picks them up.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE = os.path.join(ROOT, ".cache")

# source filename -> (place, new filename, photographer, unsplash id, description)
IMPORTS = [
    ("anders-jilden-cYrMQA7a3Wc-unsplash.jpg", "cinque-terre", "cinque-terre-01-manarola-sunset.jpg",
     "Anders Jilden", "cYrMQA7a3Wc",
     "Manarola, Cinque Terre, Italy at sunset"),
    ("claudio-schwarz-oNWvPQXoEKc-unsplash.jpg", "switzerland", "switzerland-13-matterhorn-starry-night.jpg",
     "Claudio Schwarz", "oNWvPQXoEKc",
     "The Matterhorn under a starry night sky, Zermatt, Switzerland"),
    ("cristina-gottardi-CSpjU6hYo_0-unsplash.jpg", "dolomites", "dolomites-01-rocky-peak-sunset.jpg",
     "Cristina Gottardi", "CSpjU6hYo_0",
     "A rocky Dolomites massif at sunset"),
    ("john-towner-JgOeRuGD_Y4-unsplash.jpg", "dolomites", "dolomites-02-alpenglow-ridge.jpg",
     "John Towner", "JgOeRuGD_Y4",
     "Red alpenglow on a snow-flecked mountain ridge at dusk"),
    ("pascal-debrunner-HUYPJupBvwE-unsplash.jpg", "alps", "alps-01-milky-way-lake-reflection.jpg",
     "Pascal Debrunner", "HUYPJupBvwE",
     "The Milky Way over an alpine lake with a mirror reflection"),
    ("pedro-lastra-Nyvq2juw4_o-unsplash.jpg", "chicago", "chicago-01-skyline-sunset.jpg",
     "Pedro Lastra", "Nyvq2juw4_o",
     "Aerial view of the Chicago skyline and Lake Michigan at sunset"),
    ("v2osk-Ovn1hyBge38-unsplash.jpg", "iceland", "iceland-01-aurora-lagoon.jpg",
     "v2osk", "Ovn1hyBge38",
     "Green aurora borealis over a glacial lagoon, Iceland"),
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def dims(path):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                         capture_output=True, text=True).stdout
    return (int(re.search(r"pixelWidth:\s*(\d+)", out).group(1)),
            int(re.search(r"pixelHeight:\s*(\d+)", out).group(1)))


def fetch_3840(photo_id, dest):
    url = f"https://unsplash.com/photos/{photo_id}/download?force=true&w=3840"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as fh:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)


def main():
    entries = []
    for src, place, newname, artist, pid, desc in IMPORTS:
        src_path = os.path.join(ROOT, src)
        dest = os.path.join(ROOT, "images", newname)
        if not os.path.exists(src_path):
            print(f"  !! missing {src}")
            continue
        w, h = dims(src_path)
        if w < 3840 or h < 2160:
            print(f"  refetch 4K  {src} ({w}x{h}) -> {newname}")
            fetch_3840(pid, dest)
            time.sleep(2)
        else:
            os.rename(src_path, dest)
            print(f"  move        {src} -> {newname}")
        if os.path.exists(src_path):
            os.remove(src_path)
        w, h = dims(dest)
        entries.append({
            "place": place,
            "tier": 0,
            "category": "unsplash",
            "title": f"Unsplash photo {pid}",
            "url": f"https://unsplash.com/photos/{pid}",
            "width": w, "height": h, "aspect": round(w / h, 3),
            "bytes": os.path.getsize(dest),
            "sha1": "",
            "descriptionurl": f"https://unsplash.com/photos/{pid}",
            "artist": artist,
            "license": "Unsplash License",
            "license_url": "https://unsplash.com/license",
            "credit": f"Photo by {artist} on Unsplash",
            "description": desc,
            "date": "",
            "file": f"images/{newname}",
        })

    path = os.path.join(CACHE, "manifest.json")
    rows = json.load(open(path)) if os.path.exists(path) else []
    rows = [r for r in rows if r["file"] not in {e["file"] for e in entries}]
    rows.extend(entries)
    json.dump(rows, open(path, "w"), indent=1)
    print(f"\nimported {len(entries)} images")


if __name__ == "__main__":
    main()
