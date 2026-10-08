#!/usr/bin/env python3
"""Generate README.md and ATTRIBUTION.md from the downloaded set."""
import json, os, re, html, subprocess

OUT = "/Users/davidalecrim/switzerland-wallpapers"
data = json.load(open("/tmp/downloaded_swiss.json"))

def dims(path):
    try:
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                             capture_output=True, text=True).stdout
        w = int(re.search(r"pixelWidth:\s*(\d+)", out).group(1))
        h = int(re.search(r"pixelHeight:\s*(\d+)", out).group(1))
        return w, h
    except Exception:
        return None

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return html.unescape(re.sub(r"\s+", " ", s)).strip()

labels = {}
for fname, r in data:
    n = int(fname.split("-")[0])
    labels[n] = (fname, r)

rows_md = []
for n in sorted(labels):
    fname, r = labels[n]
    title = r["title"][5:]
    artist = clean(r["artist"]) or "Unknown"
    artist = re.sub(r"\s*/\s*", " / ", artist)[:160]
    lic = r["license"]
    lic_link = f"[{lic}]({r['license_url']})" if r.get("license_url") else lic
    d = dims(os.path.join(OUT, fname))
    dim_txt = f"{d[0]} x {d[1]} px" if d else f"{r['width']} x {r['height']} px"
    if d and (r["width"] > d[0] or r["height"] > d[1]):
        dim_txt += f" (downscaled from the {r['width']} x {r['height']} px original)"
    rows_md.append(
        f"### {n:02d}. `{fname}`\n\n"
        f"- **Title:** [{title}]({r['descriptionurl']})\n"
        f"- **Author:** {artist}\n"
        f"- **Licence:** {lic_link}\n"
        f"- **Resolution:** {dim_txt} ({r['aspect']}:1)\n"
        f"- **Source (original):** {r['url'].split('?')[0]}\n"
        f"- **Date:** {r['date'] or 'n/a'}\n"
        + (f"- **Description:** {clean(r['description'])}\n" if r.get("description") else "")
    )

attr = (
    "# Attribution\n\n"
    "All images in this repository are sourced from **Wikimedia Commons**. "
    "Each file is published under the licence stated below (typically a Creative Commons "
    "licence or public domain). When you reuse or redistribute a file, keep the credit, "
    "the licence name and a link to the licence.\n\n"
    "Files are numbered in the order they appear in the repository.\n\n"
    + "\n".join(rows_md)
)
open(os.path.join(OUT, "ATTRIBUTION.md"), "w").write(attr)

first_file = labels[sorted(labels)[0]][0]
first_path = os.path.join(OUT, first_file)
osascript = (
    "osascript -e 'tell application \"System Events\" to set picture of every desktop "
    f"to POSIX file \"{first_path}\"'"
)
total_mb = sum(os.path.getsize(os.path.join(OUT, f)) for f, _ in data) / 1e6
readme = f"""# Switzerland Wallpapers

A curated set of {len(data)} high-resolution photographs of Switzerland, chosen to look good
as desktop wallpapers on macOS.

## What's inside

- {len(data)} JPEG images, all **3840 px or wider** (4K and above)
- Landscape orientation, mostly 3:2 and 16:9
- Iconic locations: Matterhorn, Oeschinensee, Lauterbrunnen, Lake Brienz/Lucerne/Thun/Geneva/Zug,
  the Aletsch Glacier, the Grande-Dixence dam, Rhine Falls, Lavaux vineyards, Engadin, Säntis and more

Total size: about {total_mb:.0f} MB.

## Use them as a Mac wallpaper

1. Open **System Settings → Wallpaper**.
2. Click **Add Photo → Choose…** and pick one or more files from this folder.
3. The images are larger than any Mac display, so enable rotation or just set a static one.

Or from the terminal:

```sh
{osascript}
```

## Licensing

These are not my photographs. Every image comes from Wikimedia Commons under a free
licence (Creative Commons or public domain). See [ATTRIBUTION.md](ATTRIBUTION.md) for the
author and licence of each file. Redistribution must preserve that attribution.
"""
open(os.path.join(OUT, "README.md"), "w").write(readme)
print("wrote README.md and ATTRIBUTION.md")
print(f"images: {len(data)}, total {total_mb:.0f} MB")
