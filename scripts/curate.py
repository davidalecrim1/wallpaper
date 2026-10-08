#!/usr/bin/env python3
"""Score and select wallpaper-worthy images per place from the cached pool.

Scoring favours curated (Featured/Quality) files, iconic landmarks, wallpaper
aspect ratios and high resolution, and rejects close-ups / interiors / artworks
that read badly as a desktop background.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "..", ".cache")
POOL = os.path.join(CACHE, "candidates.json")
PICKS = os.path.join(CACHE, "picks.json")

# How many images each place should contribute to this batch.
QUOTA = {
    "paris": 6,
    "london": 6,
    "madrid": 4,
    "new-york": 5,
    "orlando": 4,
    "disneyland": 3,
    "chile": 7,
    "argentina": 6,
}

POSITIVE = {
    "paris": {
        r"eiffel tower": 6, r"louvre": 5, r"arc de triomphe": 5, r"sacr[ée]-c[œo]ur": 5,
        r"notre[- ]dame": 5, r"seine": 4, r"champs[- ]?[ée]lys[ée]es": 4, r"montmartre": 3,
        r"concorde": 3, r"grand palais": 3, r"tuileries": 3, r"panth[ée]on": 3,
        r"skyline|panorama|aerial|panoramic": 3, r"skyline": 3, r"night|sunset|sunrise|twilight|blue hour": 3,
        r"pont|bridge": 2, r"quartier|cityscape": 2,
    },
    "london": {
        r"tower bridge": 6, r"big ben|elizabeth tower|westminster": 6, r"london eye": 5,
        r"tower of london": 4, r"st\.? paul": 4, r"the shard|tower 42|canary wharf": 3,
        r"thames": 4, r"skyline|panorama|aerial|panoramic": 4, r"night|sunset|sunrise|twilight|blue hour": 3,
        r"buckingham": 3, r"piccadilly": 2, r"trafalgar": 3, r"cityscape": 2, r"millennium bridge": 4,
    },
    "madrid": {
        r"palacio real|royal palace": 5, r"plaza mayor": 4, r"plaza de cibeles|cibeles": 4,
        r"puerta de alcal[áa]": 4, r"gran v[íi]a": 4, r"metr[óo]polis": 3, r"almudena": 4,
        r"prado": 3, r"retiro": 3, r"skyline|panorama|aerial|panoramic": 4, r"night|sunset|sunrise|twilight|blue hour": 3,
        r"edificio|azca|cuatro torres": 3, r"cityscape": 2,
    },
    "new-york": {
        r"skyline|manhattan|midtown|downtown": 5, r"brooklyn bridge": 6, r"statue of liberty": 6,
        r"empire state": 5, r"chrysler": 4, r"central park": 4, r"times square": 4,
        r"one world|world trade": 3, r"hudson|east river": 3, r"aerial|panorama|panoramic": 4,
        r"night|sunset|sunrise|twilight|blue hour": 3, r"cityscape": 2,
    },
    "orlando": {
        r"cinderella castle|magic kingdom": 6, r"walt disney world|disney world": 4,
        r"epcot|spaceship earth": 5, r"fireworks": 4, r"castle": 3, r"skyline|panorama|aerial": 3,
        r"night|sunset|sunrise|twilight|blue hour": 3, r"resort|lake": 2,
    },
    "disneyland": {
        r"sleeping beauty castle": 6, r"disneyland": 4, r"castle": 4, r"main street": 3,
        r"fireworks": 4, r"parade": 3, r"night|sunset|sunrise|twilight|blue hour": 3,
        r"panorama|aerial": 3, r"esplanade": 2,
    },
    "chile": {
        r"atacama": 5, r"valle de la luna|moon valley": 5, r"san pedro": 4, r"el tatio|geyser": 4,
        r"salar|salt flat": 4, r"licancabur|volc[áa]n|volcano": 4, r"andes|cordillera": 3,
        r"santiago": 4, r"gran torre|costanera|skyline": 4, r"desert|desierto": 3,
        r"flamingo": 3, r"laguna|lagoon|lake": 3, r"night|sunset|sunrise|stargaz|milky way": 3,
        r"panorama|aerial|panoramic": 3,
    },
    "argentina": {
        r"buenos aires": 4, r"obelisco|obelisk": 6, r"casa rosada": 5, r"puerto madero": 5,
        r"puente de la mujer|women'?s bridge": 4, r"recoleta": 3, r"catedral|metropolitana": 3,
        r"la boca|caminito": 3, r"palacio|palace": 3, r"skyline|panorama|aerial|panoramic": 4,
        r"night|sunset|sunrise|twilight|blue hour": 3, r"tango": 2, r"cityscape": 2,
    },
}

# A candidate must match at least one of these to be eligible for the place.
REQUIRED = {
    "paris": r"eiffel|louvre|arc de triomphe|sacr|notre|seine|concorde|montmartre|champs|"
             r"tuileries|panth|grand palais|pont|bridge|cityscape|skyline|panorama|"
             r"trocad|invalides|op[ée]ra|versailles",
    "london": r"tower bridge|big ben|westminster|elizabeth tower|london eye|thames|skyline|"
              r"st\.? paul|the shard|city of london|buckingham|trafalgar|piccadilly|"
              r"millennium bridge|canary wharf|cityscape|panorama|greenwich|kew",
    "madrid": r"palacio|cibeles|gran v[íi]a|puerta de alcal|plaza mayor|metr[óo]polis|"
              r"almudena|skyline|cuatro torres|azca|cityscape|prado|retiro|debod|"
              r"monumento|templo|panorama",
    "new-york": r"skyline|manhattan|brooklyn bridge|statue of liberty|empire state|chrysler|"
                r"central park|times square|one world|hudson|east river|cityscape|panorama|"
                r"lower manhattan|midtown|rockefeller|flatiron|washington square",
    "orlando": r"castle|disney|magic kingdom|epcot|spaceship earth|fireworks|skyline|"
               r"orlando|resort|lake",
    "disneyland": r"castle|disneyland|main street|fireworks|sleeping beauty|park|esplanade",
    "chile": r"atacama|valle de la luna|moon valley|san pedro|piedras rojas|miscanti|"
             r"el tatio|geyser|licancabur|salar|andes|cordillera|desert|desierto|"
             r"santiago|costanera|gran torre|skyline|valle|cordillera",
    "argentina": r"buenos aires|obelisco|obelisk|casa rosada|puerto madero|puente de la mujer|"
                 r"women'?s bridge|recoleta|caminito|la boca|catedral|metropolitana|"
                 r"cityscape|skyline|avenida|9 de julio|palacio|paseo|avenida",
}

NEGATIVE = re.compile(
    r"\b(interior|inside|room|bedroom|bathroom|ceiling|staircase|corridor|hallway|"
    r"close[- ]?up|macro|detail|relief|plaque|inscription|signage|poster|advertisement|"
    r"painting|artwork|mural|graffiti|fresco|sculpture|statue of|bust|lithograph|"
    r"engraving|caricature|print|currier|ives|"
    r"food|dish|meal|restaurant|diner|menu|market stall|shop window|"
    r"portrait|selfie|people|person|man |woman |crowd|protest|demonstration|marcha|"
    r"manifestaci|riot|strike|orgullo|parade of|"
    r"swan|goose|duck|flamingo|turtle|bird|gull|condor|penguin|seal|lion|horse|cow|"
    r"ship|hms|mine|tractor|locomotive|train|railway|ferrocarril|wagon|wreck|"
    r"rowing|regatta|marathon|race|"
    r"cemetery|cementerio|grave|tomb|funeral|museum|museo|"
    r"map|diagram|logo|coat of arms|flag|banknote|stamp|document)\b",
    re.I,
)


# Optional per-place sub-quotas: (regex, count) applied before the general fill,
# so a place with several regions mixes them instead of taking only the top one.
GROUPS = {
    "chile": [
        (r"atacama|valle de la luna|san pedro|piedras rojas|miscanti|tatio|paniri|"
         r"catedrales de tara|monjes|licancabur|salar|andes", 5),
        (r"santiago|costanera|gran torre|skyline", 2),
    ],
    "new-york": [
        (r"skyline|manhattan|panorama", 2),
        (r"brooklyn bridge|manhattan bridge|williamsburg", 1),
        (r"empire state|chrysler|rockefeller|one world", 1),
        (r"central park", 1),
    ],
}


def subject_key(place: str, row: dict) -> str:
    text = row["title"] + " " + row["description"]
    for pat in POSITIVE[place]:
        if re.search(pat, text, re.I):
            return pat
    return re.sub(r"[^a-z]", "", row["title"].lower())[:14]


def score(place: str, row: dict) -> float | None:
    text = row["title"] + " " + row["description"]
    if NEGATIVE.search(text):
        return None
    required = REQUIRED.get(place)
    if required and not re.search(required, text, re.I):
        return None
    s = float(row.get("tier", 0)) * 6
    for pat, weight in POSITIVE[place].items():
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


def main() -> None:
    pool = json.load(open(POOL))
    picks: dict[str, list[dict]] = {}
    for place, quota in QUOTA.items():
        scored = []
        for row in pool:
            if row["place"] != place:
                continue
            s = score(place, row)
            if s is not None:
                scored.append((s, row))
        scored.sort(key=lambda x: -x[0])

        used: dict[str, int] = {}
        cap = 2 if quota > 4 else 1
        chosen: list[dict] = []
        picked_sha: set[str] = set()

        def take(row: dict, s: float) -> bool:
            key = subject_key(place, row)
            if used.get(key, 0) >= cap or row["sha1"] in picked_sha:
                return False
            used[key] = used.get(key, 0) + 1
            picked_sha.add(row["sha1"])
            chosen.append(dict(row, score=s))
            return True

        # Optional per-subject quotas so a place with distinct regions mixes them.
        for pattern, count in GROUPS.get(place, []):
            taken = 0
            for s, row in scored:
                if taken >= count or len(chosen) >= quota:
                    break
                if re.search(pattern, row["title"] + " " + row["description"], re.I):
                    taken += take(row, s)
        for s, row in scored:
            if len(chosen) >= quota:
                break
            take(row, s)

        picks[place] = chosen
        print(f"\n## {place} ({len(chosen)}/{quota})")
        for row in chosen:
            print(f"  {row['score']:5} {row['width']}x{row['height']} "
                  f"{row['aspect']:<6} t{row['tier']} | {row['title'][5:78]}")

    json.dump(picks, open(PICKS, "w"), indent=1)
    total = sum(len(v) for v in picks.values())
    print(f"\npicked {total} images across {len(picks)} places")


if __name__ == "__main__":
    main()
