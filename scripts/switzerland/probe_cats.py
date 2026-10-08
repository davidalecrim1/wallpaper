#!/usr/bin/env python3
"""Probe which curated Commons categories exist and how big they are."""
import json, time, urllib.parse, urllib.request, sys

API = "https://commons.wikimedia.org/w/api.php"
UA = "WallpaperCollector/1.0 (personal wallpaper collection; contact davidalecrim1)"

def api(params, tries=6):
    params = dict(params, format="json", maxlag="5")
    url = API + "?" + urllib.parse.urlencode(params)
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
            if "error" in d:
                raise RuntimeError(d["error"].get("info"))
            return d
        except Exception as e:
            time.sleep(3 * (a + 1))
    print("  ! failed", file=sys.stderr)
    return {}

CATS = [
    "Category:Featured pictures of Paris",
    "Category:Quality images of Paris",
    "Category:Featured pictures of Paris by Benh",
    "Category:Featured pictures of the Eiffel Tower",
    "Category:Quality images of the Eiffel Tower",
    "Category:Featured pictures of London",
    "Category:Quality images of London",
    "Category:Featured pictures of Madrid",
    "Category:Quality images of Madrid",
    "Category:Featured pictures of New York City",
    "Category:Quality images of New York City",
    "Category:Featured pictures of Manhattan",
    "Category:Quality images of Orlando, Florida",
    "Category:Orlando, Florida",
    "Category:Disneyland",
    "Category:Sleeping Beauty Castle",
    "Category:Disneyland Paris",
    "Category:Featured pictures of Chile",
    "Category:Quality images of Chile",
    "Category:Atacama Desert",
    "Category:Valle de la Luna (Chile)",
    "Category:Santiago de Chile",
    "Category:Santiago, Chile",
    "Category:Featured pictures of Argentina",
    "Category:Quality images of Argentina",
    "Category:Buenos Aires",
]
for i in range(0, len(CATS), 40):
    d = api({"action": "query", "prop": "categoryinfo",
             "titles": "|".join(CATS[i:i + 40])})
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            print(f"  {'MISSING':>7}  {p['title']}")
        else:
            ci = p.get("categoryinfo", {})
            print(f"  {ci.get('size', 0):>7}  {ci.get('files', 0):>6} files  | {p['title']}")
    time.sleep(2.5)
