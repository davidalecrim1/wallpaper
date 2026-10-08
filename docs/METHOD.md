# Method

How the wallpapers in this repository were found, filtered and downloaded.

## Why Wikimedia Commons

- Every file has a machine-readable licence (Creative Commons or public domain),
  so a public repository can credit them properly.
- The MediaWiki API exposes category membership, dimensions, MIME type and full
  licence metadata in bulk.
- Commons already curates quality: the **Featured pictures** and **Quality images**
  categories are editor-reviewed, which gives a good starting pool per place.

## Pipeline

The scripts run in order and share a `.cache/` directory (git-ignored).

1. `scripts/collect.py` walks a per-place list of Commons categories and, for each
   page of up to 500 files, asks the API for `imageinfo` in the same request
   (`generator=categorymembers` + `prop=imageinfo`). That keeps the request count low.
   Candidates are filtered to JPEG, landscape, width >= 3840, height >= 2160 and
   aspect ratio between 1.2 and 2.2. Output: `.cache/candidates.json`.
2. `scripts/curate.py` scores each candidate (curated category, iconic landmark
   keywords, wallpaper-ish aspect ratio, resolution) and rejects close-ups,
   interiors and artworks. It selects a quota per place, at most one image per
   landmark. Output: `.cache/picks.json`.
3. `scripts/download.py` downloads the picks using `scripts/commons.py` and writes
   them to `images/<place>-NN-slug.jpg` (flat, so macOS can select the folder).
   Output: `.cache/manifest.json`.
4. `scripts/build_docs.py` regenerates `README.md`, `docs/ATTRIBUTION.md` and
   `docs/LOCATIONS.md` from the manifests.

`scripts/commons.py` holds the shared API client, the thumbnail-URL helper and the
filter constants.

## Wikimedia rate limits (important)

Two separate throttles bite when doing bulk downloads anonymously:

- **The API** (`commons.wikimedia.org/w/api.php`) returns `HTTP 429` on bursts.
  Mitigation: a descriptive `User-Agent`, the `maxlag=5` parameter, and exponential
  backoff on failure.
- **The file host** (`upload.wikimedia.org`) rejects any direct request that is not
  one of the standard thumbnail widths. The standard widths are:

  ```
  20, 40, 60, 120, 250, 330, 500, 960, 1280, 1920, 3840
  ```

  Full-resolution originals are throttled. The largest standard width, **3840px**,
  is used here, which still satisfies the 4K requirement. See Wikimedia's
  "Common thumbnail sizes" page for the authoritative list.

If a download still fails, the scripts back off and retry; a slow trickle is
expected.

## The 4K rule

A file qualifies only if `width >= 3840` **and** `height >= 2160` and it is
landscape. Files stored as 3840px thumbnails are 3840 x 2160 for 16:9 sources and
3840 x 2560 for 3:2 sources, so they stay at or above the 4K floor.

## Licensing

The images are not the author's work. Each is under a free licence that requires
attribution. `docs/ATTRIBUTION.md` lists the author, licence and source for every
file. Any redistribution must preserve those credits.

## Adding another place

1. Add an entry to `LOCATIONS` in `scripts/collect.py` with the relevant Commons
   categories (start from `Category:Featured pictures of X` and
   `Category:Quality images of X`, then broaden).
2. Add the place to `QUOTA` and `POSITIVE` in `scripts/curate.py`.
3. Run `collect.py`, `curate.py`, `download.py`, `build_docs.py`.
4. Review the output and adjust the keywords; re-run as needed.

## Switzerland (first batch)

The Switzerland set predates this structure and used the same approach against
`Category:Featured pictures of Switzerland`, `Category:Featured pictures of the
Alps`, `Category:Quality images of Switzerland` and
`Category:Images from Wiki Loves Earth 2022 in Switzerland`. Its metadata is
preserved in `.cache/switzerland.json` for `build_docs.py`.
