# Materials

## Purpose

Look up a material and read its measured properties, with the source behind
every value. This is the entry point for material and property lookup on the
site: type a grade (`6061-T6`, `316L`, `PEEK`) to open a datasheet, or type a
property (`density`, `plastic strength`) to open category-grouped reference
ranges.

It answers "what is this material's yield strength, and who says so". For
choosing between materials, use the Ashby Chart Material Selector and Materials
Explorer instead.

## What it contains

222 material identities, 92 named states, 1,593 observations across 10
registered properties, citing 28 source documents.

Specified limits stay distinct from measured values, and every observation
keeps its test conditions and its citation. The toolbar switches metric and
imperial display, and each property carries its own unit override. Both
preferences persist in the browser.

## Requirements

### Frontend

* The page is a self-contained static app. It has no backend, no accounts, and
  no network search service. All queries run against local JSON.
* Data loads lazily: `data/<build>/index.json` is the preloaded search index,
  and a material's full record is fetched from `data/<build>/records/<id>.json`
  only when that material is opened.
* Every path is relative, so the app works from any hosting prefix. The data
  location is a single `data-path` attribute on `<body>`, read once by
  `app.mjs`. Do not hardcode data paths anywhere else; moving the dataset to a
  shared location later should be a one-line change.
* Deep links are served by small redirect pages, one per material, state and
  property. They carry a `<meta http-equiv="refresh">` to the app with the
  right query string, and exist to keep those URLs stable. They hold no
  content of their own.

### Data

* Source documents (manufacturer PDFs and document URLs) are excluded from the
  published site and from all JSON and CSV exports by design. Reference text
  and page citations remain.
* No record marked `prototype-seed-estimates-v0` may ship. Those are
  non-production demonstration values and are not present in this build.

## Provenance and updates

This tool is the built output of the Materials Lookup project, vendored here.
The generator, curated source data and ingestion scripts live in that separate
repository; this directory holds only its published site.

The as-is import is preserved in this repository's history (`git log --diff-filter=A
-- tools/materials`), including the upstream commit history brought in by
`git subtree`.

To take a new dataset: rebuild the site upstream, then replace this directory
with the new output and re-run the discoverability scripts in the repository
root. `release-manifest.json` records the build id, per-file hashes and the
counts above, so a vendored copy can always be checked against the build it
came from.

## Licensing

* Code: MIT, see `code-license.txt`.
* Data: CC BY 4.0, see `data-license.txt`. Individual observations keep
  source-specific attribution. Public-domain and manufacturer-published
  material is cited rather than relicensed, and downstream users follow the
  terms attached to each source.

## Caching

The upstream build ships a Netlify `_headers` file, which only takes effect at
a publish root. Its rules are reproduced for this path in the repository's
`netlify.toml`: content-hashed `assets/` and `data/` are immutable for a year,
everything else revalidates.

## Not yet done

* Pages for individual materials are redirects, not rendered content, so
  search engines see one page rather than several hundred. Pre-rendering them
  upstream is the open opportunity.
* The dataset is tool-local for now. Promoting it to a shared location, and
  pointing `pycalcs/materials.py` at it so the Ashby tools rank all 222
  materials instead of a hardcoded seven, is planned separately.
