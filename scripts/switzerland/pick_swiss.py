#!/usr/bin/env python3
"""Pick 20 wallpaper-worthy Switzerland images from the candidate pool."""
import json, re

rows = json.load(open("/tmp/swiss_candidates.json"))
print(f"pool: {len(rows)}")

POS = {
    # iconic subjects (strong)
    r"matterhorn": 6, r"oeschinensee|oeschinen|öschinen": 6, r"lauterbrunnen": 6,
    r"jungfrau": 5, r"eiger": 4, r"mönch|monch": 3, r"aletsch": 5, r"bietschhorn": 4,
    r"chillon": 5, r"lavaux": 5, r"brienz": 5, r"thun": 4, r"lucerne|luzern|vierwaldst": 4,
    r"léman|leman|geneva|genève|geneve": 4, r"klöntal|klontal": 4, r"rigi": 4,
    r"engadin|sils|silvaplana|st\.? moritz|maloja": 4, r"appenzell": 4, r"sempach": 4,
    r"zermatt": 4, r"grindelwald": 4, r"zinalrothorn|weisshorn|dent blanche": 4,
    r"grande-dixence|grande dixence": 3, r"rheinfall|rhine falls": 5, r"muottas muragl": 4,
    r"lago maggiore|locarno|lugano": 3, r"mont tendre|chasseral|jura|creux du van": 3,
    r"pilatus": 3, r"säntis|santis|alpstein|fronalpstock|hardergrat|brienzer rothorn": 4,
    r"fronalpstock": 4, r"interlaken": 3, r"spiez": 3, r"basel": 2, r"zürich|zurich": 2,
    r"bern(e)?": 2, r"montreux|vevey": 3, r"gruy|fribourg|morat": 2, r"landwasser|brusio": 3,
    r"gletscher|glacier": 3, r"panorama": 2, r"alpen|alps": 2,
    # look cues
    r"sonnenuntergang|sunset|abendrot|coucher|crépuscule|crepuscule": 3,
    r"sonnenaufgang|sunrise|morgenrot|lever de soleil|morgenstimmung|morgensonne": 3,
    r"herbst|autumn|automne": 2, r"nebelmeer|nebel|foggy|fog|nuages|wolken": 3,
    r"spiegel|reflection|reflections": 2, r"winter|snow|schnee|verschneit": 2,
    r"panoramarundweg|aussicht|blick|view": 1,
}
NEG = (r"mushroom|pilz|alpenblumen|blumen|flowers|flower|butterfly|papillon|insect|bee|"
       r"hoverfly|spider|snail|slug|swan|kingfisher|deer|fox|renard|mouse|sheep|schaf|"
       r"cow|kuh|kühe|kuehe|cattle|ibex|steinbock|marmot|chamois|gämse|bird|vogel|"
       r"tulip|raps|rapeseed|corn field|cornfield|work by|son\.|cat |cows|horses|alpaca|"
       r"nels?son|event|world cup|mie|sbb|equipment|tractor|farm|slug|roedeer|roe deer|"
       r"quadrat|1x|betula|fjord|cruise ship|cruiseship|aircraft|plane|helicopter|hubschrauber|"
       r"sign|bridge of|building|shop|statue|fountain|villa|hotel|museum|parliament|"
       r"football|stadium|sport|race|bikeride|road|highway|motorway|slope in|almens|"
       r"green|meadow|wiese|field|field of|grass|camp|zoo|park |cern|vignoble|vineyard|raisins")

def score(r):
    t = r["title"] + " " + r["description"]
    if re.search(NEG, t, re.I):
        return None
    s = 0.0
    for pat, w in POS.items():
        if re.search(pat, t, re.I):
            s += w
    # prefer wallpaper aspect ratios
    ar = r["aspect"]
    if 1.55 <= ar <= 1.85:
        s += 3
    elif 1.4 <= ar < 1.55:
        s += 1.5
    elif 1.85 < ar <= 2.05:
        s += 1.0
    else:
        s -= 1.0
    if r["width"] >= 6000:
        s += 1.5
    if r["width"] >= 5000:
        s += 1.0
    return round(s, 2)

scored = []
for r in rows:
    s = score(r)
    if s is not None:
        scored.append((s, r))
scored.sort(key=lambda x: -x[0])

# diversify: max 2 per subject key
def key(r):
    t = r["title"]
    for k in ["eiger", "jungfrau", "mönch", "aletsch", "klöntal", "locarno", "lago",
              "pilatus", "rigi", "brienz", "thun", "luzern", "lucerne", "zermatt",
              "chillon", "lavaux", "basel", "zurich", "zürich", "giles", "beverin",
              "rofl", "flims", "oberalp", "biosphare", "valcalanca", "pardiel",
              "silvaplana", "sils", "matterhorn", "oeschinen", "montreux", "vevey"]:
        if re.search(k, t, re.I):
            return k
    return re.sub(r"[^a-z]", "", t.lower())[:12]

picks, used = [], {}
for s, r in scored:
    k = key(r)
    if used.get(k, 0) >= 1:
        continue
    used[k] = used.get(k, 0) + 1
    picks.append((s, r))
    if len(picks) == 20:
        break

for s, r in picks:
    print(f"{s:5} {r['width']}x{r['height']} {r['aspect']:<6} {r['bytes']//1024//1024}MB | {r['title'][5:80]}")
json.dump([r for _, r in picks], open("/tmp/swiss_picks.json", "w"), indent=2)
print(f"\npicked {len(picks)}")
