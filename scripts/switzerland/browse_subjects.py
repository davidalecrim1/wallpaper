#!/usr/bin/env python3
import json, re
rows = json.load(open("/tmp/swiss_candidates.json"))
subjects = {
 "matterhorn": r"matterhorn",
 "oeschinensee": r"oeschinen|öschinen",
 "lauterbrunnen": r"lauterbrunnen",
 "chillon": r"chillon",
 "aletsch": r"aletsch",
 "brienz": r"brienzer|brienz",
 "thun": r"thun",
 "lucerne": r"luzern|lucerne|vierwaldst",
 "lavaux": r"lavaux",
 "rheinfall": r"rheinfall|rhine falls",
 "dixence": r"dixence",
 "engadin": r"engadin|sils|silvaplana|st\.? moritz|maloja|champfer",
 "klontal": r"klöntal|klontal",
 "appenzell": r"appenzell|säntis|santis|alpstein",
 "zermatt": r"zermatt",
 "jungfrau": r"eiger|mönch|jungfrau",
 "locarno": r"locarno|lago maggiore|maggiore",
 "chasseral": r"chasseral|creux du van|mont tendre|jura",
 "mürren": r"mürren|murren|schilthorn",
 "pilatus": r"pilatus",
 "lugano": r"lugano",
 "rigi": r"rigi",
 "weisshorn": r"bietschhorn|weisshorn|dent blanche|zinalrothorn|mischabel",
 "gruyere": r"gruy|fribourg|morat|neuchâtel|neuchatel",
 "landwasser": r"landwasser|brusio|bernina",
 "fronalp": r"fronalp|schwyz|stoos|klingenstock",
 "geneva": r"lac léman|leman|geneva|genève|geneve|jet d'eau",
 "grande_dixence": r"grande-dixence|grande dixence|barrage",
 "oberland": r"berner oberland|oberland",
}
for name, pat in subjects.items():
    sub = [r for r in rows if re.search(pat, r["title"] + " " + r["description"], re.I)
           and not re.search(r"mushroom|blumen|flower|butterfly|insect|bee|swan|bird|deer|fox|sheep|cow|ibex|marmot|chamois|tulip|cern|work by|event", r["title"], re.I)
           and 1.4 <= r["aspect"] <= 2.05]
    sub.sort(key=lambda r: -(min(r["width"], 9000) / 1000 + r["aspect"] * 2))
    print(f"\n## {name} ({len(sub)})")
    for r in sub[:4]:
        print(f"   {r['width']}x{r['height']} {r['aspect']:<6} {r['bytes']//1024//1024}MB | {r['title'][5:78]}")
        print(f"      {r['url'][:120]}")
