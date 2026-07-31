# Project log

A concise, newest-first record of completed work, decisions, and milestone
gates. Active work belongs in [`TODO.md`](TODO.md); detailed rationale belongs
in the linked plans and decision documents.

## Current status

- Phase: M0 synthetic experience spike complete; entering the M1 data-contract
  phase.
- Selected interaction candidate: Prototype 05, dual-mode lookup.
- Current UI evidence: synthetic fixture only, with no network requests or
  engineering claims.
- Next gate: validate a versioned domain contract with adversarial synthetic
  cases before a small two-source reality check.

## 2026-07-30 — Project history and work queue established

- Initialized the repository on the `main` branch.
- Added this running project log and a prioritized live work queue.
- Expanded ignore rules for local environments, credentials, caches, coverage,
  browser-test output, and logs.
- Kept the reproducible `materials/` build output tracked intentionally for the
  current static demo.

## 2026-07-30 — Dual-mode interaction selected for further development

- Added Prototype 05 without removing the four earlier UI directions.
- Material queries open complete datasheets; material plus property queries
  open a focused property with access to the complete record.
- Precise property queries open taxonomy-grouped observed ranges.
- Broad properties require clarification; comparison and ranking requests
  remain outside the product boundary.
- Added category drilldown, clickable taxonomy breadcrumbs, and inline
  material/state actions.
- Put category, material, and state ranges and coverage counts on shared column
  tracks while keeping indentation in the hierarchy label only.
- Verified interaction behavior and layouts down to 320 px.
- Updated the seed plan, prototype notes, and schema findings to reflect the
  dual-mode direction.

Related:

- [`prototypes/decision-notes.md`](prototypes/decision-notes.md)
- [`docs/prototype-schema-findings.md`](docs/prototype-schema-findings.md)
- [`2026-07-29_materials_lookup_standalone.md`](2026-07-29_materials_lookup_standalone.md)

## 2026-07-29 — Synthetic UI bake-off

- Added one shared synthetic semantic corpus with 50 data-bearing records and
  360 observations.
- Added shared typed query parsing and relevance tests.
- Built four deliberately different interfaces: compact index, material-first,
  split inspector, and query resolver.
- Exercised designation collisions, missing properties, named states,
  cross-classification, conflicting conditioned observations, and empty
  categories.
- Revised the project plan so interaction and data-contract questions are
  tested synthetically before broad source research.

## 2026-07-29 — Initial implementation spike

- Added the static site builder, source and property registries, curated
  prototype records, generated material/property pages, and build validation.
- Recorded the initial `family → grade → variant` schema as a prototype
  decision.
- Added licensing and visible prototype-data warnings.

## Verification

Run before milestone commits:

```sh
python3 scripts/build_site.py --check
python3 -m unittest discover -s tests -v
node tests/prototype_search.test.js
```
