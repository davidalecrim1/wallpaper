#!/usr/bin/env python3
"""Build README.md, docs/ATTRIBUTION.md and docs/LOCATIONS.md from the manifests."""
from __future__ import annotations

import json
import os
import re
import subprocess

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CACHE = os.path.join(ROOT, ".cache")

PLACE_NAMES = {
    "switzerland": "Switzerland",
    "paris": "Paris",
    "london": "London",
    "madrid": "Madrid",
    "new-york": "New York",
    "orlando": "Orlando / Walt Disney World",
    "disneyland": "Disneyland",
    "chile": "Chile (Atacama & Santiago)",
    "argentina": "Argentina (Buenos Aires)",
}
PLACE_ORDER = ["switzerland", "paris", "london", "madrid", "new-york",
               "orlando", "disneyland", "chile", "argentina"]


def load():
    rows = []
    for name in ("switzerland.json", "manifest.json"):
        path = os.path.join(CACHE, name)
        if os.path.exists(path):
            rows.extend(json.load(open(path)))
    # Ignore anything the user has deleted from images/.
    return [r for r in rows if os.path.exists(os.path.join(ROOT, r["file"]))]


def dims(path: str):
    try:
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                             capture_output=True, text=True).stdout
        w = int(re.search(r"pixelWidth:\s*(\d+)", out).group(1))
        h = int(re.search(r"pixelHeight:\s*(\d+)", out).group(1))
        return w, h
    except Exception:
        return None


def by_place(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["place"], []).append(row)
    for place in grouped:
        grouped[place].sort(key=lambda r: r["file"])
    return grouped


def order(grouped):
    known = [p for p in PLACE_ORDER if p in grouped]
    extra = sorted(p for p in grouped if p not in PLACE_ORDER)
    return known + extra


def label(place):
    return PLACE_NAMES.get(place, place.replace("-", " ").title())


def attribution(grouped):
    lines = [
        "# Attribution",
        "",
        "Every image in this repository comes from **Wikimedia Commons** and is published",
        "under a free licence (Creative Commons or public domain). Reuse must keep the",
        "author credit, the licence name and a link to the licence.",
        "",
        "Full-resolution sources are throttled by Wikimedia, so most files here are the",
        "standard 3840px render; the `Resolution` line shows the actual pixels stored and,",
        "where relevant, the size of the original upload.",
        "",
    ]
    for place in order(grouped):
        rows = grouped.get(place, [])
        if not rows:
            continue
        lines.append(f"## {label(place)}")
        lines.append("")
        for row in rows:
            title = row["title"][5:]
            d = dims(os.path.join(ROOT, row["file"]))
            dim = f"{d[0]} x {d[1]} px" if d else f"{row['width']} x {row['height']} px"
            if d and (row["width"] > d[0] or row["height"] > d[1]):
                dim += f" (from a {row['width']} x {row['height']} px original)"
            lic = row["license"]
            lic_link = f"[{lic}]({row['license_url']})" if row.get("license_url") else lic
            lines += [
                f"### `{row['file']}`",
                "",
                f"- **Title:** [{title}]({row['descriptionurl']})",
                f"- **Author:** {row['artist'] or 'Unknown'}",
                f"- **Licence:** {lic_link}",
                f"- **Resolution:** {dim}",
                f"- **Source:** {row['url'].split('?')[0]}",
                f"- **Date:** {row['date'] or 'n/a'}",
                "",
            ]
    return "\n".join(lines)


def locations(grouped):
    lines = ["# Locations", "",
             "| Place | Images | Folder |", "| --- | --- | --- |"]
    for place in order(grouped):
        rows = grouped.get(place, [])
        if rows:
            lines.append(f"| {label(place)} | {len(rows)} | `images/{place}-*` |")
    lines += ["", "## Files", ""]
    for place in order(grouped):
        rows = grouped.get(place, [])
        if not rows:
            continue
        lines.append(f"### {label(place)}")
        lines.append("")
        for row in rows:
            lines.append(f"- `{row['file']}` - {row['title'][5:]}")
        lines.append("")
    return "\n".join(lines)


def readme(grouped):
    total = sum(len(v) for v in grouped.values())
    places = len(order(grouped))
    return f"""# Wallpapers

{total} high-resolution (4K+) landscape photographs from Wikimedia Commons, picked to look
good as macOS desktop wallpapers, across {places} places.

- `images/<place>-NN-name.jpg` - the wallpapers (flat, so macOS can pick the folder)
- `docs/ATTRIBUTION.md` - author and licence for every file
- `docs/METHOD.md` - how the images are sourced
- `scripts/` - the collector and downloader

## Use on macOS

Open **System Settings -> Wallpaper -> Add Photo -> Choose...** and pick a folder under
`images/`.

## Add more

```
/load-wallpapers 10 Kyoto
```

The images are not mine. Each carries a free licence (mostly Creative Commons BY-SA);
keep the credits in `docs/ATTRIBUTION.md` when reusing.
"""


def main() -> None:
    rows = load()
    grouped = by_place(rows)
    open(os.path.join(ROOT, "README.md"), "w").write(readme(grouped))
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    open(os.path.join(ROOT, "docs", "ATTRIBUTION.md"), "w").write(attribution(grouped))
    open(os.path.join(ROOT, "docs", "LOCATIONS.md"), "w").write(locations(grouped))
    print("wrote README.md, docs/ATTRIBUTION.md, docs/LOCATIONS.md")
    for place in order(grouped):
        if grouped.get(place):
            print(f"  {place:<11} {len(grouped[place])}")


if __name__ == "__main__":
    main()
