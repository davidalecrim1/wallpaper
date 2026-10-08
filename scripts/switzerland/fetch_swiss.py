#!/usr/bin/env python3
"""Collect 4K+ landscape Switzerland images from Wikimedia Commons."""
import json, re, time, urllib.parse, urllib.request, sys, html

API = "https://commons.wikimedia.org/w/api.php"
UA = "SwitzerlandWallpaperCollector/1.0 (personal wallpaper use; contact: davidalecrim1)"

def api(params, tries=4):
    params = dict(params)
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(data["error"].get("info", "api error"))
            return data
        except Exception as e:
            if attempt == tries - 1:
                print(f"  ! failed: {e}", file=sys.stderr)
                return {}
            time.sleep(1.5 * (attempt + 1))
    return {}

def discover(prefix):
    names, cont = [], None
    while True:
        p = {"action": "query", "list": "allcategories", "acprefix": prefix, "aclimit": 100}
        if cont:
            p["accontinue"] = cont
        d = api(p)
        for c in d.get("query", {}).get("allcategories", []):
            names.append(c["*"])
        cont = d.get("continue", {}).get("accontinue")
        if not cont:
            break
        time.sleep(0.3)
    return names

def category_files(cat):
    files, cont = [], None
    while True:
        p = {"action": "query", "list": "categorymembers", "cmtitle": cat,
             "cmtype": "file", "cmlimit": 500}
        if cont:
            p["cmcontinue"] = cont
        d = api(p)
        for m in d.get("query", {}).get("categorymembers", []):
            files.append(m["title"])
        cont = d.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        time.sleep(0.3)
    return files

def imageinfo(titles):
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        d = api({"action": "query", "titles": "|".join(batch), "prop": "imageinfo",
                 "iiprop": "url|size|mime|sha1|extmetadata"})
        for page in d.get("query", {}).get("pages", {}).values():
            if "imageinfo" in page:
                out[page["title"]] = page["imageinfo"][0]
        time.sleep(0.4)
    return out

def clean(sv):
    if not sv:
        return ""
    sv = re.sub(r"<[^>]+>", " ", str(sv))
    return html.unescape(re.sub(r"\s+", " ", sv)).strip()

seeds = [
    "Featured pictures of Switzerland",
    "Featured pictures of the Alps",
    "Featured pictures of landscapes",
    "Quality images of Switzerland",
    "Images from Wiki Loves Earth 2024 in Switzerland",
    "Images from Wiki Loves Earth 2023 in Switzerland",
    "Images from Wiki Loves Earth 2022 in Switzerland",
    "Images from Wiki Loves Earth 2021 in Switzerland",
]
cats = []
for s in seeds:
    if s.startswith("Quality images of Switzerland"):
        cats += discover(s)
    else:
        cats.append("Category:" + s)
cats = sorted(set(cats))
print(f"categories: {len(cats)}", file=sys.stderr)

titles = set()
for c in cats:
    fs = category_files(c)
    print(f"  {c}: {len(fs)}", file=sys.stderr)
    titles.update(fs)
titles = sorted(titles)
print(f"unique files: {len(titles)}", file=sys.stderr)

info = imageinfo(titles)
print(f"with imageinfo: {len(info)}", file=sys.stderr)

# Switzerland relevance check for broad categories
CH = re.compile(r"switzerland|swiss|suisse|schweiz|svizzera|zürich|zurich|lucerne|luzern|"
                r"matterhorn|interlaken|grindelwald|lauterbrunnen|zermatt|geneva|geneve|"
                r"basel|bern|appenzell|oeschinen|engadin|ticino|valais|wallis|graubünden|"
                r"grisons|jura|alps|alpen|verbier|eiger|jungfrau|titlis|rigi|pilatus", re.I)

rows = []
for t, ii in info.items():
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
    blob = " ".join([t, clean(em.get("Categories", {}).get("value")),
                     clean(em.get("ImageDescription", {}).get("value")),
                     clean(em.get("ObjectName", {}).get("value"))])
    if not CH.search(blob):
        continue
    rows.append({
        "title": t,
        "url": ii["url"],
        "width": w, "height": h, "aspect": round(ar, 3),
        "bytes": ii.get("size", 0),
        "sha1": ii.get("sha1", ""),
        "descriptionurl": ii.get("descriptionurl", ""),
        "artist": clean(em.get("Artist", {}).get("value")),
        "license": clean(em.get("LicenseShortName", {}).get("value")) or "see file page",
        "license_url": clean(em.get("LicenseUrl", {}).get("value")),
        "credit": clean(em.get("Credit", {}).get("value")),
        "description": clean(em.get("ImageDescription", {}).get("value"))[:300],
        "date": clean(em.get("DateTimeOriginal", {}).get("value"))[:20],
    })

# dedupe by sha1
seen, uniq = set(), []
for r in sorted(rows, key=lambda r: -r["bytes"]):
    if r["sha1"] in seen:
        continue
    seen.add(r["sha1"])
    uniq.append(r)

with open("/tmp/swiss_candidates.json", "w") as f:
    json.dump(uniq, f, indent=2)

print(f"\nqualifying 4K+ landscape images: {len(uniq)}", file=sys.stderr)
for r in uniq:
    print(f"  {r['width']}x{r['height']} {r['bytes']//1024//1024}MB | {r['title'][5:70]}", file=sys.stderr)
