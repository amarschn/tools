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
Settings selects a light or dark theme, or follows the system. Copy link shares
the current search or record. The Tools link returns to the tools hub.

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

## Where this comes from

This directory is **generated**, including this README from
`materials-lookup/src/README.md`. Edit the source and rebuild, then run
`scripts/inject_seo_meta.py` to restore the catalog metadata.

The source of truth is `materials-lookup/` at the repository root, which holds the
curated data, the builder and the validation gates. Adding a material, fixing a
value, or changing the interface all happen there.

```sh
python3 materials-lookup/builder/build_site.py --output ../tools/materials
python3 scripts/inject_seo_meta.py
python3 scripts/generate_sitemap.py
python3 scripts/generate_homepage_metadata.py
```

See [materials-lookup/README.md](../../materials-lookup/README.md) for the full workflow.
`release-manifest.json` records the build id, per-file hashes and the counts
above, so a published copy can always be checked against the build it came
from.

## Where source documents live

Manufacturer datasheets and other originals are never committed and never
served. Keep them in `private-sources/` at the repository root, which is
git-ignored apart from its README. That directory explains why it sits there
rather than under `tools/`: this repository publishes its root, and the
documented local server serves untracked files too.

`tests/test_source_documents_stay_private.py` enforces it. No document may be
tracked by git, the published data may carry no document URL, every cited
source must keep its publisher and snapshot hash, and the vendored build must
still hash to `release-manifest.json` apart from the catalog metadata added to
`index.html`. The release verifier also checks that complete page against the
shared metadata generator.

## Licensing

* Code: MIT, see `code-license.txt`.
* Data: CC BY 4.0, see `data-license.txt`. Individual observations keep
  source-specific attribution. Public-domain and manufacturer-published
  material is cited rather than relicensed, and downstream users follow the
  terms attached to each source.

## Caching

The build emits a Netlify `_headers` file, which only takes effect at a
publish root, so it is inert here. Its rules are reproduced for this path in
the repository's `netlify.toml`: content-hashed `assets/` and `data/` are
immutable for a year, everything else revalidates.

## Not yet done

* Pages for individual materials are redirects, not rendered content, so
  search engines see one page rather than several hundred. Pre-rendering them
  in `materials-lookup/release/compiler.py` is the open opportunity.
* The dataset is tool-local for now. Promoting it to a shared location, and
  pointing `pycalcs/materials.py` at it so the Ashby tools rank all 222
  materials instead of a hardcoded seven, is planned separately.
