#!/usr/bin/env python3
"""Collect 4K+ landscape wallpaper candidates from Wikimedia Commons.

For each place we walk a set of curated categories (Featured / Quality images
first, then broad location categories) using a single generator+imageinfo call
per 500 files, filter for wallpaper-friendly geometry, and cache the pool in
.cache/candidates.json.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import commons  # noqa: E402

CACHE = os.path.join(os.path.dirname(__file__), "..", ".cache", "candidates.json")

# Order matters: the first place to claim a file gets it.
LOCATIONS: dict[str, list[str]] = {
    "paris": [
        "Category:Featured pictures of Paris",
        "Category:Featured pictures of the Eiffel Tower",
        "Category:Quality images of Paris",
        "Category:Quality images of the Eiffel Tower",
    ],
    "london": [
        "Category:Featured pictures of London",
        "Category:Quality images of London",
    ],
    "madrid": [
        "Category:Featured pictures of Madrid",
        "Category:Quality images of Madrid",
    ],
    "new-york": [
        "Category:Featured pictures of New York City",
        "Category:Quality images of New York City",
    ],
    "orlando": [
        "Category:Cinderella Castle at Magic Kingdom",
        "Category:Orlando, Florida",
        "Category:Walt Disney World Resort",
    ],
    "disneyland": [
        "Category:Sleeping Beauty Castle at Disneyland",
        "Category:Disneyland",
        "Category:Disneyland Paris",
    ],
    "chile": [
        "Category:Featured pictures of Chile",
        "Category:Quality images of Chile",
        "Category:Valle de la Luna (Chile)",
        "Category:San Pedro de Atacama",
        "Category:Atacama Desert",
        "Category:Santiago de Chile",
    ],
    "argentina": [
        "Category:Featured pictures of Argentina",
        "Category:Quality images of Argentina",
        "Category:Buenos Aires",
    ],
}

# Obvious non-photographs / not wallpaper material.
EXCLUDE_TITLE = re.compile(
    r"\b(map|mapa|logo|coat of arms|wappen|flag|diagram|chart|graph|banknote|stamp|"
    r"signature|seal|poster|screenshot|table|plan|sketch|drawing|painting|engraving|"
    r"manuscript|document|page|text|cover|book|insignia|emblem|banner|coin|medal)\b",
    re.I,
)


def tier(category: str) -> int:
    if "Featured" in category:
        return 2
    if "Quality" in category:
        return 1
    return 0


def collect_location(place: str, categories: list[str], seen_sha: set[str]) -> list[dict]:
    rows: list[dict] = []
    for cat in categories:
        cont = None
        t = tier(cat)
        while True:
            params = {
                "action": "query",
                "generator": "categorymembers",
                "gcmtitle": cat,
                "gcmtype": "file",
                "gcmlimit": "500",
                "prop": "imageinfo",
                "iiprop": "url|size|mime|sha1|extmetadata",
            }
            if cont:
                params["gcmcontinue"] = cont
            data = commons.api(params)
            pages = data.get("query", {}).get("pages", {})
            kept = 0
            for page in pages.values():
                info = (page.get("imageinfo") or [{}])[0]
                title = page["title"]
                if info.get("mime") != "image/jpeg":
                    continue
                if not commons.is_wallpaper_candidate(
                        info.get("width", 0), info.get("height", 0), info.get("size", 0)):
                    continue
                if EXCLUDE_TITLE.search(title):
                    continue
                sha = info.get("sha1", "")
                if sha in seen_sha:
                    continue
                seen_sha.add(sha)
                em = info.get("extmetadata", {})
                rows.append({
                    "place": place,
                    "tier": t,
                    "category": cat,
                    "title": title,
                    "url": info["url"],
                    "width": info["width"],
                    "height": info["height"],
                    "aspect": round(info["width"] / info["height"], 3),
                    "bytes": info.get("size", 0),
                    "sha1": sha,
                    "descriptionurl": info.get("descriptionurl", ""),
                    "artist": commons.clean_html(em.get("Artist", {}).get("value")),
                    "license": commons.clean_html(em.get("LicenseShortName", {}).get("value"))
                               or "see file page",
                    "license_url": commons.clean_html(em.get("LicenseUrl", {}).get("value")),
                    "credit": commons.clean_html(em.get("Credit", {}).get("value")),
                    "description": commons.clean_html(em.get("ImageDescription", {}).get("value"))[:300],
                    "date": commons.clean_html(em.get("DateTimeOriginal", {}).get("value"))[:20],
                })
                kept += 1
            print(f"  {cat}: {len(pages)} scanned, {kept} kept", file=sys.stderr)
            cont = data.get("continue", {}).get("gcmcontinue")
            if not cont:
                break
            time.sleep(2.5)
        time.sleep(2.5)
    return rows


def main() -> None:
    seen_sha: set[str] = set()
    all_rows: list[dict] = []
    for place, cats in LOCATIONS.items():
        print(f"## {place}", file=sys.stderr)
        all_rows.extend(collect_location(place, cats, seen_sha))

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(all_rows, open(CACHE, "w"), indent=1)

    print(f"\ntotal candidates: {len(all_rows)}")
    by_place: dict[str, int] = {}
    for r in all_rows:
        by_place[r["place"]] = by_place.get(r["place"], 0) + 1
    for place, n in by_place.items():
        curated = sum(1 for r in all_rows if r["place"] == place and r["tier"] > 0)
        print(f"  {place:<11} {n:>5}  ({curated} from Featured/Quality)")


if __name__ == "__main__":
    main()
