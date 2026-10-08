#!/usr/bin/env python3
"""Download N 4K wallpapers for an arbitrary target into ./images/<target>/.

This is the generic entry point used by the /load-wallpapers skill. It discovers
Commons categories for the target, falls back to a file search, filters for 4K
landscape photos, scores them, and downloads the top N as 3840px JPEGs.

    python3 scripts/load.py --target "Kyoto" --count 10
    python3 scripts/load.py --target "Iceland waterfalls" --count 5 --dry-run
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import commons  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE = os.path.join(ROOT, ".cache")

GENERIC_POSITIVE = {
    # ambience / landscape first: these read best as wallpapers
    r"landscape|scenery|scenic|paisaje|paisagem|landschaft|paysage|vista|viewpoint|overlook": 5,
    r"panorama|panoramic|aerial": 4,
    r"sunset|sunrise|dusk|dawn|golden hour|blue hour|twilight|night sky|stargaz|milky way|aurora": 4,
    r"\b(mountain|mountains|alps|valley|valleys|lake|lakes|river|coast|beach|desert|"
    r"glacier|waterfall|forest|island|cliff|fjord|canyon|meadow|field|sky|cloud|fog|"
    r"mist|snow|reflect|reflection)\b": 3,
    r"liftoff|\blaunch\b|launching|launch of|night launch": 4,
    r"falcon 9|falcon heavy|starship|super heavy|rocket|spacex|artemis|saturn v": 2,
    r"nebula|galaxy|planet|outer space|earth from|astronaut|satellite|mars|moon|milky way": 3,
    r"skyline|cityscape": 3,
    r"nature|wild": 2,
    r"castle|cathedral|temple|bridge|tower|palace|monument|square|plaza|church": 1,
    r"national park": 2,
}

# Anything that signals people or a busy scene is rejected outright; wallpapers
# should be unpopulated.
NEGATIVE = re.compile(
    r"\b(interior|inside|room|bedroom|bathroom|ceiling|staircase|corridor|hallway|"
    r"close[- ]?up|macro|detail|relief|plaque|inscription|signage|poster|advertisement|"
    r"painting|artwork|mural|graffiti|fresco|sculpture|statue of|bust|lithograph|"
    r"engraving|caricature|print|map|diagram|logo|coat of arms|flag|banknote|stamp|"
    r"document|construction|hangar|facilit|scaffold|assembly building|"
    r"landing stage|jetty|pier|dock|harbour|harbor|berth|"
    # people
    r"people|person|persons|human|man|men|woman|women|boy|girl|child|children|kid|"
    r"baby|family|couple|portrait|selfie|face|headshot|pedestrian|tourist|visitor|"
    r"crowd|audience|spectator|fan|fans|queue|group of|"
    r"performer|performing|musician|singer|dancer|actor|actress|model|athlete|"
    r"runner|runners|cyclist|hiker|climber|skier|swimmer|surfer|player|crew|team|"
    r"festival|concert|ceremony|wedding|party|meeting|conference|gathering|"
    r"protest|demonstration|marcha|riot|strike|parade|procession|military|soldier|"
    r"police|guard|worker|worker|staff|vendor|waiter|costume|cosplay|"
    r"food|dish|meal|restaurant|diner|menu|market stall|shop window|"
    r"ship|hms|boat|ferry|steamboat|schiff|dampfschiff|kayak|canoe|mine|tractor|"
    r"locomotive|train|railway|wreck|"
    r"swan|goose|duck|flamingo|turtle|bird|gull|condor|penguin|seal|lion|horse|cow|"
    r"cemetery|cementerio|grave|tomb|funeral|museum|museo)\b",
    re.I,
)


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text or "target"


def discover_categories(target: str) -> list[str]:
    cats: set[str] = set()
    for prefix in ("Quality images of", "Featured pictures of"):
        try:
            data = commons.api({"action": "query", "list": "allcategories",
                                "acprefix": f"{prefix} {target}", "aclimit": 100})
            for item in data.get("query", {}).get("allcategories", []):
                cats.add("Category:" + item["*"])
        except RuntimeError:
            pass
        time.sleep(1.5)
    cats.add(f"Category:{target}")
    cats |= {f"Category:Featured pictures of {target}", f"Category:Quality images of {target}"}

    # Find relevant category names (useful for subjects with no "Quality/Featured" tree).
    try:
        data = commons.api({"action": "query", "list": "search", "srsearch": target,
                            "srnamespace": "14", "srlimit": "8"})
        for item in data.get("query", {}).get("search", []):
            cats.add(item["title"])
    except RuntimeError:
        pass
    time.sleep(1.5)

    existing = []
    cat_list = sorted(cats)
    for i in range(0, len(cat_list), 40):
        try:
            data = commons.api({"action": "query", "prop": "categoryinfo",
                                "titles": "|".join(cat_list[i:i + 40])})
        except RuntimeError:
            continue
        for page in data.get("query", {}).get("pages", {}).values():
            if "missing" not in page and page.get("categoryinfo", {}).get("files", 0) > 0:
                existing.append(page["title"])
        time.sleep(1.5)
    return existing


def keep(info: dict, title: str) -> bool:
    if info.get("mime") != "image/jpeg":
        return False
    if not commons.is_wallpaper_candidate(info.get("width", 0), info.get("height", 0),
                                          info.get("size", 0)):
        return False
    return not NEGATIVE.search(title)


def row_from(page: dict, info: dict, source: str, tier: int) -> dict:
    em = info.get("extmetadata", {})
    return {
        "place": "",
        "tier": tier,
        "category": source,
        "title": page["title"],
        "url": info["url"],
        "width": info["width"],
        "height": info["height"],
        "aspect": round(info["width"] / info["height"], 3),
        "bytes": info.get("size", 0),
        "sha1": info.get("sha1", ""),
        "descriptionurl": info.get("descriptionurl", ""),
        "artist": commons.clean_html(em.get("Artist", {}).get("value")),
        "license": commons.clean_html(em.get("LicenseShortName", {}).get("value")) or "see file page",
        "license_url": commons.clean_html(em.get("LicenseUrl", {}).get("value")),
        "credit": commons.clean_html(em.get("Credit", {}).get("value")),
        "description": commons.clean_html(em.get("ImageDescription", {}).get("value"))[:300],
        "date": commons.clean_html(em.get("DateTimeOriginal", {}).get("value"))[:20],
    }


def _consume(data: dict, cat: str, tier: int, seen: set[str], rows: list[dict]) -> int:
    added = 0
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("sha1") in seen or not keep(info, page["title"]):
            continue
        seen.add(info["sha1"])
        rows.append(row_from(page, info, cat, tier))
        added += 1
    return added


def collect_categories(cats: list[str], seen: set[str]) -> list[dict]:
    rows: list[dict] = []
    for cat in cats:
        tier = 2 if "Featured" in cat else 1 if "Quality" in cat else 0
        name = cat.split(":", 1)[1] if ":" in cat else cat
        # Preferred: search inside the category while excluding files whose
        # structured data says they depict a human (P180 = Q5).
        added = 0
        offset = 0
        while offset < 500:
            try:
                data = commons.api({"action": "query", "generator": "search",
                                    "gsrsearch": f'incategory:"{name}" -haswbstatement:P180=Q5',
                                    "gsrnamespace": "6", "gsrlimit": "500", "gsroffset": offset,
                                    "prop": "imageinfo",
                                    "iiprop": "url|size|mime|sha1|extmetadata"})
            except RuntimeError:
                break
            added += _consume(data, cat, tier, seen, rows)
            if "continue" not in data:
                break
            offset += 500
            time.sleep(2)
        if added:
            time.sleep(2)
            continue
        # Fallback: plain category walk for files the search index misses.
        cont = None
        while True:
            params = {"action": "query", "generator": "categorymembers", "gcmtitle": cat,
                      "gcmtype": "file", "gcmlimit": "500", "prop": "imageinfo",
                      "iiprop": "url|size|mime|sha1|extmetadata"}
            if cont:
                params["gcmcontinue"] = cont
            try:
                data = commons.api(params)
            except RuntimeError:
                break
            _consume(data, cat, tier, seen, rows)
            cont = data.get("continue", {}).get("gcmcontinue")
            if not cont:
                break
            time.sleep(2)
        time.sleep(2)
    return rows


def collect_search(target: str, seen: set[str], limit: int) -> list[dict]:
    rows = []
    offset = 0
    while len(rows) < limit and offset < 500:
        try:
            data = commons.api({"action": "query", "list": "search",
                                "srsearch": f"{target} -haswbstatement:P180=Q5",
                                "srnamespace": "6", "srlimit": "50", "sroffset": offset,
                                "srprop": "size"})
        except RuntimeError:
            break
        titles = [r["title"] for r in data.get("query", {}).get("search", [])]
        if not titles:
            break
        for i in range(0, len(titles), 50):
            try:
                info_data = commons.api({"action": "query", "titles": "|".join(titles[i:i + 50]),
                                         "prop": "imageinfo",
                                         "iiprop": "url|size|mime|sha1|extmetadata"})
            except RuntimeError:
                continue
            for page in info_data.get("query", {}).get("pages", {}).values():
                info = (page.get("imageinfo") or [{}])[0]
                if info.get("sha1") in seen or not keep(info, page["title"]):
                    continue
                seen.add(info["sha1"])
                rows.append(row_from(page, info, f"search:{target}", 0))
            time.sleep(1.5)
        offset += 50
        time.sleep(2)
    return rows


def score(row: dict, target: str = "") -> float:
    text = row["title"] + " " + row["description"]
    s = float(row["tier"]) * 6
    if target and target.lower() in text.lower():
        s += 5
    for pat, weight in GENERIC_POSITIVE.items():
        if re.search(pat, text, re.I):
            s += weight
    aspect = row["aspect"]
    if 1.55 <= aspect <= 1.85:
        s += 3
    elif 1.4 <= aspect < 1.55 or 1.85 < aspect <= 2.05:
        s += 1.5
    else:
        s -= 1
    if row["width"] >= 6000:
        s += 1.5
    elif row["width"] >= 5000:
        s += 1
    return round(s, 2)


def select(rows: list[dict], count: int, target: str = "") -> list[dict]:
    good = [(score(r, target), r) for r in rows if not NEGATIVE.search(r["title"] + " " + r["description"])]
    good.sort(key=lambda x: -x[0])
    used: dict[str, int] = {}
    chosen = []
    for s, row in good:
        key = re.sub(r"[^a-z]", "", row["title"].lower())[:16]
        if used.get(key, 0) >= 1:
            continue
        used[key] = used.get(key, 0) + 1
        chosen.append(dict(row, score=s))
        if len(chosen) == count:
            break
    return chosen


def download(rows: list[dict], place: str, outdir: str) -> list[dict]:
    os.makedirs(outdir, exist_ok=True)
    # Continue numbering after any images already present for this place.
    start = 1
    for existing in glob.glob(os.path.join(outdir, f"{place}-*.jpg")):
        match = re.match(rf"{re.escape(place)}-(\d+)-", os.path.basename(existing))
        if match:
            start = max(start, int(match.group(1)) + 1)
    manifest = []
    for index, row in enumerate(rows, start=start):
        name = re.sub(r"^File:", "", row["title"])
        name = re.sub(r"\.(jpe?g|png)$", "", name, flags=re.I)
        slug = "-".join(re.sub(r"[^a-z0-9]+", "-", name.lower()).split("-")[:6]).strip("-")
        fname = f"{place}-{index:02d}-{slug or 'image'}.jpg"
        dest = os.path.join(outdir, fname)
        rel = os.path.relpath(dest, ROOT)
        if not (os.path.exists(dest) and os.path.getsize(dest) > 50_000):
            # Wide panoramas render shorter than 2160px at 3840 wide, so fetch
            # the original instead to stay at or above 4K.
            url = (row["url"].split("?")[0] if row["aspect"] > 3840 / 2160
                   else commons.thumb_url(row["url"], 3840))
            ok = False
            for attempt in range(5):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": commons.USER_AGENT})
                    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as fh:
                        while True:
                            chunk = resp.read(1 << 16)
                            if not chunk:
                                break
                            fh.write(chunk)
                    ok = os.path.getsize(dest) > 50_000
                    break
                except Exception:  # noqa: BLE001
                    time.sleep(10 * (attempt + 1))
            if not ok:
                print(f"  FAILED {rel}", file=sys.stderr)
                continue
            time.sleep(2)
        print(f"  {rel}")
        manifest.append(dict(row, place=place, file=rel))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Load 4K wallpapers for a target from Wikimedia Commons.")
    parser.add_argument("--target", required=True, help="place or subject, e.g. 'Kyoto' or 'Iceland waterfalls'")
    parser.add_argument("--count", type=int, default=10, help="how many images to download")
    parser.add_argument("--dir", default=os.path.join(ROOT, "images"), help="output images directory")
    parser.add_argument("--dry-run", action="store_true", help="collect and select only, do not download")
    args = parser.parse_args()

    place = slugify(args.target)
    print(f"target: {args.target}  ->  images/{place}-NN-*.jpg  ({args.count} images)")

    cats = discover_categories(args.target)
    print(f"categories: {len(cats)}")
    for c in cats:
        print(f"  {c}")

    seen: set[str] = set()
    rows = collect_categories(cats, seen)
    print(f"category candidates: {len(rows)}")

    if len(rows) < args.count * 4:
        extra = collect_search(args.target, seen, limit=args.count * 10)
        print(f"search candidates: {len(extra)}")
        rows.extend(extra)

    picks = select(rows, args.count, args.target)
    print(f"\nselected {len(picks)}/{args.count}")
    for row in picks:
        print(f"  {row['score']:5} {row['width']}x{row['height']} {row['aspect']:<6} "
              f"t{row['tier']} | {row['title'][5:78]}")
    if len(picks) < args.count:
        print(f"note: only {len(picks)} qualifying images found", file=sys.stderr)

    if args.dry_run:
        return

    manifest = download(picks, place, args.dir)
    path = os.path.join(CACHE, "manifest.json")
    existing = json.load(open(path)) if os.path.exists(path) else []
    new_files = {r["file"] for r in manifest}
    existing = [r for r in existing if r.get("file") not in new_files]
    existing.extend(manifest)
    os.makedirs(CACHE, exist_ok=True)
    json.dump(existing, open(path, "w"), indent=1)
    print(f"\nwrote {len(manifest)} files to images/")
    print("run: python3 scripts/build_docs.py")


if __name__ == "__main__":
    main()
