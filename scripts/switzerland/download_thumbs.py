#!/usr/bin/env python3
"""Download remaining picks as standard 3840px thumbnails (Wikimedia-sanctioned 4K size)."""
import json, os, re, sys, time, urllib.request

OUT = "/Users/davidalecrim/switzerland-wallpapers"
ROWS = json.load(open("/tmp/swiss_candidates.json"))
UA = "SwitzerlandWallpaperCollector/1.0 (personal wallpaper collection; contact davidalecrim1)"

CURATION = [
    (r"^File:Riffelsee with Matterhorn behind\.jpg$",                      "01-matterhorn-riffelsee.jpg"),
    (r"^File:Coucher du soleil Oeschinensee",                              "02-oeschinensee-sunset.jpg"),
    (r"^File:Sunrise over Lauterbrunnen valley, Switzerland\.jpg$",        "03-lauterbrunnen-sunrise.jpg"),
    (r"^File:Château de Chillon sunset over Lake Geneva with a long",      "04-chillon-castle-sunset.jpg"),
    (r"^File:Aletschgletscher mit Alpenrosen\.jpg$",                       "05-aletsch-glacier.jpg"),
    (r"^File:Blick auf den Brienzersee\.jpg$",                             "06-lake-brienz.jpg"),
    (r"^File:Vierwaldst.tter See mit Urnersee Richtung Pilatus\.jpg$",     "07-lake-lucerne-pilatus.jpg"),
    (r"^File:Morgenstimmung auf Genfersee bei Grandvaux\.jpg$",            "08-lavaux-lake-geneva.jpg"),
    (r"^File:Rhine Falls in Schaffhausen canton, Switzerland\.jpg$",       "09-rhine-falls.jpg"),
    (r"^File:Barrage de la Grande-Dixence\.jpg$",                          "10-grande-dixence-dam.jpg"),
    (r"^File:Engadin valley, Graubunden\.jpg$",                            "11-engadin-valley.jpg"),
    (r"^File:Lever de soleil au Klontalersee\.jpg$",                       "12-klontalersee-sunrise.jpg"),
    (r"^File:Autour du S.ntis\.jpg$",                                      "13-santis-appenzell.jpg"),
    (r"^File:048 Eiger at end of Sunset Photo by Giles Laurent\.jpg$",     "14-eiger-sunset.jpg"),
    (r"^File:Morgensonne .ber dem Lago Maggiore\.jpg$",                    "15-lago-maggiore-morning.jpg"),
    (r"^File:034 Creux du Van and Swiss Alps with snow at Sunset",         "16-creux-du-van-sunset.jpg"),
    (r"^File:Wandern in M",                                                "17-murren-valley.jpg"),
    (r"^File:Zugersee vom Ufer in Zug\.jpg$",                              "18-lake-zug.jpg"),
    (r"^File:French alps at Lake Geneva during the blue hour with",        "19-lake-geneva-blue-hour.jpg"),
    (r"^File:View of Lake Thun\.jpg$",                                     "20-lake-thun.jpg"),
]

def find(pat):
    rx = re.compile(pat)
    m = [r for r in ROWS if rx.search(r["title"])]
    return max(m, key=lambda r: r["bytes"]) if m else None

def thumb_url(orig, width=3840):
    u = orig.split("?")[0]
    name = u.rsplit("/", 1)[1]
    return u.replace("/commons/", "/commons/thumb/", 1) + f"/{width}px-" + name

chosen = []
for pat, fname in CURATION:
    r = find(pat)
    if not r:
        print(f"  !! no match {pat}", file=sys.stderr)
        continue
    dest = os.path.join(OUT, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
        print(f"  = {fname} (keep existing)")
        chosen.append((fname, r))
        continue
    url = thumb_url(r["url"])
    ok = False
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as f:
                while True:
                    c = resp.read(1 << 16)
                    if not c:
                        break
                    f.write(c)
            ok = True
            break
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"    retry {attempt+1} in {wait}s: {e}", file=sys.stderr)
            time.sleep(wait)
    if ok:
        print(f"  > {fname} ({os.path.getsize(dest)//1024}KB)")
    chosen.append((fname, r))
    time.sleep(2)

json.dump(chosen, open("/tmp/downloaded_swiss.json", "w"), indent=2)
print(f"\nset: {len(chosen)} files")
