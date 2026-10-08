#!/usr/bin/env python3
"""Merge extra Commons categories into the cached candidate pool."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import collect  # noqa: E402
import commons  # noqa: E402

CACHE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".cache"))
POOL = os.path.join(CACHE, "candidates.json")

EXTRA = {
    "argentina": [
        "Category:Casa Rosada, Buenos Aires",
        "Category:Casa Rosada at night",
        "Category:Puerto Madero, Buenos Aires",
        "Category:Puerto Madero at night",
        "Category:Puente de la Mujer",
    ],
    "orlando": ["Category:Magic Kingdom"],
    "disneyland": ["Category:Main Street, U.S.A."],
    "chile": ["Category:Costanera Center"],
}


def main() -> None:
    rows = json.load(open(POOL))
    seen = {r["sha1"] for r in rows}
    before = len(rows)
    for place, cats in EXTRA.items():
        print(f"## {place}", file=sys.stderr)
        rows.extend(collect.collect_location(place, cats, seen))
    json.dump(rows, open(POOL, "w"), indent=1)
    print(f"pool: {before} -> {len(rows)}")


if __name__ == "__main__":
    main()
