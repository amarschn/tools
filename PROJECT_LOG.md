# Project log

A concise, newest-first record of completed work, decisions, and milestone
gates. Active work belongs in [`TODO.md`](TODO.md); detailed rationale belongs
in the linked plans and decision documents.

## Current status

- Phase: local release candidate 1.0.0-rc.1 complete; public deployment pending.
- Selected interaction: dual-mode material datasheets and property/category lookup.
- Catalog: 134 material identities, 24 named states, 840 observations, 5 source
  documents. The factual release uses the normalized v0.1.0 contract.
- Review artifact and verification: [docs/release-candidate.md](docs/release-candidate.md).
- Next gate: review the local candidate, choose the publishing destination, and
  verify an authorized deployment at its actual public URL.

## 2026-09-09 — Complete local release candidate

- Recovered the September 7 factual import work that had not reached the UI or
  project notes. Connected the selected dual-mode interaction to that catalog
  through one canonical adapter and deterministic release compiler.
- Added material/state/form lookup, category/property ranges, ambiguity and broad
  property clarification, persistent metric/imperial units and property overrides,
  source-page links, printed values, JSON records, and complete JSON/CSV exports.
- Dissolved 111 artificial reference-state wrappers; retained 24 named states.
  Kept stainless physical-table observations at grade level. One-sided limits
  stay out of measured ranges, with explicit coverage and separate limit labels.
- Rechecked Hydro page 2: removed duplicated alloy-wide density, preserved its
  original precision and exact conversion, and restored the stated conductivity
  temperature. Every retained authoring observation survives the canonical
  adapter with a page locator and source literal.
- Added source snapshot hashing and a read-only import reconstruction check for
  all five saved PDFs. The adapter rejects unmapped uncertainty and reported/SI
  discrepancies rather than silently losing information.
- Replaced stale generated output with a self-contained, relocatable publish
  directory. Hashed assets/data, matching-build checks, retained legacy redirects,
  and retry/reload behavior cover cache updates and subpath hosting.
- Added factual-contract, projection-parity, search, conversion, provenance,
  determinism, output-freshness, and browser checks; the optional validator is
  installed and full structural tests pass locally.
- Browser evidence covers desktop and 320px screens, root and nested mounts,
  persistent units, browser history, ambiguous/missing queries, delayed loading,
  cache mismatch recovery, and no external or full-corpus browsing requests.
- Added CI verification and artifact packaging. No public deployment or remote
  configuration was performed.
- Recorded [Schema Decision 002](docs/schema-decision-002-release.md). The old
  full-scale bake-off and tools compatibility export remain deferred; the local
  release milestone does not silently mark those earlier gates complete.

## 2026-08-23 — Phase 2 contract, validation, and migration

- Added contract v0.1.0: a JSON Schema for document shape and a standard-library
  semantic validator for references, taxonomy, placement, units, precision, and
  provenance, with stable diagnostic codes negative fixtures assert against.
- Migrated the full prototype corpus with zero validation errors and no
  unexplained loss. Every observation, material, and taxon id survives and every
  canonical number is unchanged.
- Verified before removing anything that the 228 state-attributes copied onto
  observations were exact duplicates, with no conflicts and no orphans; the
  check re-runs against the legacy corpus rather than trusting the number.
- Retired `material_state` into precise keys, recovered temper from display
  labels, split labels of the form `T6 · plate`, and dissolved three states that
  product form alone had defined.
- Added an adversarial overlay for shapes the corpus lacked: interval, one-sided
  bound, uncertainty with sample count, unavailable and not-applicable
  assertions, a superseded observation, a long structured locator, an
  undesignated commercial grade, and a supplemental classification path.
- Made 24 negative fixtures executable, each asserting its own diagnostic code
  rather than merely failing.
- Moved counting and range rules out of page code into tested projections,
  including the checkpoint 1 drill-down where product form yields a landable
  level while staying stored on the observation.
- Modelled unit conversion as affine rather than a single scale factor. The
  legacy scale factor could not express temperature, so the prototype hardcodes
  a 273.15 subtraction in its formatter; the offset is now data, and adding
  Fahrenheit needs a registry entry rather than another renderer special case.
- Test count rose from 14 to 93. `jsonschema` is a development-only dependency;
  semantic validation and the suite still pass without it.

Related:

- [`docs/schema-lab-migration-report.md`](docs/schema-lab-migration-report.md)
- [`schemas/v0.1.0/dataset.schema.json`](schemas/v0.1.0/dataset.schema.json)
- [`fixtures/schema-lab/v0.1.0/`](fixtures/schema-lab/v0.1.0/)

## 2026-08-22 — Checkpoint 1 closed with modifications

- Adopted purchasability as the governing test for what earns a page, refined so
  that discrete purchasable choices become navigable levels while continuous
  quantities remain filters.
- Confirmed named states as landable lookup targets, and required every level to
  report a range aggregated from its members so intermediate pages are never
  empty while data exists beneath them.
- Made product form a navigable drill-down level while keeping it stored on
  observations, separating where a fact lives from what a user can land on.
- Inverted the result-form roles: the canonical value drives display and
  conversion, and the reported value is retained for audit and significant
  figures rather than for display.
- Accepted the property renames and carried the structured designation form.
- Recorded a new requirement not previously in the plan: display units are a
  user preference with a metric default, imperial option, and per-property
  override.
- No contract is frozen yet; Schema Decision 002 still lands at Phase 5.

Related:

- [`docs/schema-lab-checkpoint-1-decisions.md`](docs/schema-lab-checkpoint-1-decisions.md)

## 2026-08-02 — Schema lab baseline and first review checkpoint

- Froze the two existing data models, serving paths, entity counts, artifact
  sizes, legacy mappings, and selected Prototype 05 behavior.
- Added a 21-case executable query baseline covering exact and ambiguous
  identities, property and category routes, typo recall, empty categories, and
  rejected comparison intent.
- Made the selected dual-mode route explicit while preserving the earlier
  prototypes' legacy resolver states.
- Proposed the bounded v1 vocabulary and state-versus-observation condition
  matrix, including retirement of the catch-all `material_state` key.
- Added one complete proposed dataset example and five focused invalid examples
  for review before validator implementation.
- No schema contract has been adopted yet; work pauses at checkpoint 1 for the
  recorded semantic decisions.

Related:

- [`docs/schema-lab-review-checkpoint-1.md`](docs/schema-lab-review-checkpoint-1.md)
- [`docs/schema-lab-m0-baseline.md`](docs/schema-lab-m0-baseline.md)
- [`docs/materials-domain-glossary.md`](docs/materials-domain-glossary.md)
- [`docs/state-condition-matrix.md`](docs/state-condition-matrix.md)

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
.venv/bin/python3.13 scripts/build_site.py --check
.venv/bin/python3.13 scripts/schema_lab.py check
.venv/bin/python3.13 -m unittest discover -s tests
.venv/bin/python3.13 scripts/verify_release.py
npm test
npm run test:browser
```

`schema_lab.py check` re-runs the migration in memory and fails when the
checked-in corpus differs, then validates it. Structural validation needs
`pip install -r requirements-dev.txt`; without it the semantic checks still run
and the structural tests skip rather than fail.
