#!/usr/bin/env python3
"""Collect 4K+ landscape Switzerland images (generator+imageinfo, low request count)."""
import json, re, time, urllib.parse, urllib.request, sys, html

API = "https://commons.wikimedia.org/w/api.php"
UA = "SwitzerlandWallpaperCollector/1.0 (personal wallpaper collection; contact davidalecrim1)"

def api(params, tries=6):
    params = dict(params, format="json", maxlag="5")
    url = API + "?" + urllib.parse.urlencode(params)
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            if "error" in data:
                code = data["error"].get("code", "")
                if code == "maxlag" or "lag" in code:
                    raise RuntimeError("maxlag")
                raise RuntimeError(data["error"].get("info", "error"))
            return data
        except Exception as e:
            wait = 5 * (a + 1)
            print(f"  ... retry in {wait}s ({e})", file=sys.stderr)
            time.sleep(wait)
    print("  ! giving up on request", file=sys.stderr)
    return {}

def clean(sv):
    if not sv:
        return ""
    sv = re.sub(r"<[^>]+>", " ", str(sv))
    return html.unescape(re.sub(r"\s+", " ", sv)).strip()

CATS = [
    "Category:Featured pictures of Switzerland",
    "Category:Featured pictures of the Alps",
    "Category:Quality images of Switzerland",
    "Category:Images from Wiki Loves Earth 2022 in Switzerland",
]

CH = re.compile(r"switzerland|swiss|suisse|schweiz|svizzera|zürich|zurich|lucerne|luzern|"
                r"matterhorn|interlaken|grindelwald|lauterbrunnen|zermatt|geneva|geneve|"
                r"basel|bern(e)?|appenzell|oeschinen|engadin|ticino|valais|wallis|graubünden|"
                r"grisons|jura|alps|alpen|eiger|jungfrau|titlis|rigi|pilatus|aare|rhine|rhône|"
                r"thun|brienz|neuchatel|fribourg|sion|locarno|lugano|davos|st\.? moritz", re.I)

rows, seen_sha, seen_title = [], set(), set()
for cat in CATS:
    cont = None
    while True:
        p = {"action": "query", "generator": "categorymembers", "gcmtitle": cat,
             "gcmtype": "file", "gcmlimit": "500", "prop": "imageinfo",
             "iiprop": "url|size|mime|sha1|extmetadata"}
        if cont:
            p["gcmcontinue"] = cont
        d = api(p)
        pages = d.get("query", {}).get("pages", {})
        print(f"{cat}: {len(pages)} files", file=sys.stderr)
        for pg in pages.values():
            ii = (pg.get("imageinfo") or [{}])[0]
            if ii.get("mime") != "image/jpeg":
                continue
            w, h = ii.get("width", 0), ii.get("height", 0)
            if w < 3840 or h < 2160 or w <= h:
                continue
            ar = w / h
            if not (1.2 <= ar <= 2.2):
                continue
            if ii.get("size", 0) < 1_000_000:
                continue
            em = ii.get("extmetadata", {})
            blob = " ".join([pg["title"], clean(em.get("Categories", {}).get("value")),
                             clean(em.get("ImageDescription", {}).get("value")),
                             clean(em.get("ObjectName", {}).get("value"))])
            if not CH.search(blob):
                continue
            sha = ii.get("sha1", "")
            if sha in seen_sha or pg["title"] in seen_title:
                continue
            seen_sha.add(sha)
            seen_title.add(pg["title"])
            rows.append({
                "title": pg["title"], "url": ii["url"], "width": w, "height": h,
                "aspect": round(ar, 3), "bytes": ii.get("size", 0), "sha1": sha,
                "descriptionurl": ii.get("descriptionurl", ""),
                "artist": clean(em.get("Artist", {}).get("value")),
                "license": clean(em.get("LicenseShortName", {}).get("value")) or "see file page",
                "license_url": clean(em.get("LicenseUrl", {}).get("value")),
                "credit": clean(em.get("Credit", {}).get("value")),
                "description": clean(em.get("ImageDescription", {}).get("value"))[:300],
                "date": clean(em.get("DateTimeOriginal", {}).get("value"))[:20],
            })
        cont = d.get("continue", {}).get("gcmcontinue")
        if not cont:
            break
        time.sleep(2.5)
    time.sleep(2.5)

rows.sort(key=lambda r: -r["bytes"])
with open("/tmp/swiss_candidates.json", "w") as f:
    json.dump(rows, f, indent=2)
print(f"\nQUALIFYING: {len(rows)}", file=sys.stderr)
for r in rows:
    print(f"  {r['width']}x{r['height']} {r['bytes']//1024//1024}MB {r['aspect']} | {r['title'][5:75]}", file=sys.stderr)
