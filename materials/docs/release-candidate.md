# Local release candidate — 1.0.0-rc.1

Updated: 2026-09-10

The September 9 local-release milestone is complete: the selected dual-mode
interaction runs on the factual catalog, with persistent units, visible
provenance, generated downloads, and repeatable release checks. The publishable
directory is `materials/`. No public deployment has been made.

The interface follows Prototype 05: compact toolbar and search, expandable
category/material rows, and shared value/condition/source columns. The original
prototypes remain intact. Future interface redesigns require express permission.

## Review locally

Build using the README commands, then open `http://localhost:8001/materials/`.

1. Search `6061-T6`, find tensile yield strength, switch to imperial, and
   confirm the specified minimum displays as `≥ 35 ksi`. Override that property
   to MPa and reload; both preferences persist.
2. Check the text reference to Hydro page 2. The source title, revision,
   original printed value and significant figures are under Source details.
   There is no document link, viewer, or PDF download in the public app.
3. Open the grade from its breadcrumb. Alloy-wide density is present there;
   it is not silently inherited by each temper.
4. Search `plastic strength`, choose ultimate tensile strength, and drill down
   through a category into a supplier grade. Ranges and limits remain distinct.
5. Search `316L` to see the distinct EN grades behind an ambiguous ASTM label.
6. Search `TECAPEEK tensile strength`, then use Show all properties to see its
   seven reported properties. Search `TECAPEEK max service temperature` to see
   an explicitly unreported property.
7. Try `6061 T6 extrusion`, browser Back, the Sources page, and JSON/CSV downloads.
8. Search `2205`, `253 MA`, `904L`, and `Alloy 825` for the new manufacturer
   grades. The source references in their records and exports remain text-only.

9. Search `6063 T6 extrusion`, `C11000`, `bronze density` and `Ti6246 DA`.
   Check thickness unit conversion, reported copper ranges, and the titanium
   size restriction under Test details. See [batch review](nonferrous-batch-review.md).

10. Search `4140`, `1045`, `D2`, `H13` and `steel density`. Check specified
    versus typical minima, diameter scope under Test details, and the hardness
    conditions of tool steel properties. See [steel review](steel-batch-review.md).

## Evidence

- 140 Python tests pass with no skips. Full structural and semantic validation of the factual catalog and synthetic
  contract, including negative cases and exact source-to-SI conversion checks.
- Deterministic compilation; every checked-in artifact and manifest hash is
  verified against a fresh in-memory build. Extra files in the publish tree
  fail the release gate.
- 222 factual material identities, 92 named states, 1,593 observations,
  10 registered properties, and text references to 28 source documents. One registered property
  currently has no observations; missing data is displayed as unreported.
- Readable search index approximately 269 KB raw / 23 KB gzip. Warm Node query
  p95 is approximately 5–7 ms on the development machine. This measurement is a
  current-corpus baseline, not a large-corpus performance claim.
- Search routing, conversion, significant figures, bounds, intervals,
  uncertainty conversion, and compiler/browser parity across all 222 records.
- Chromium browser verification at root and `/nested/reference/`: material and
  property flows, clarification, ambiguity, rejected ranking intent, deep links,
  reload, browser history, units, missing data, and a 50-row result cap.
- One additional JSON request opens a full datasheet. Normal browsing makes no
  external requests and never loads the full-catalog export or synthetic corpus.
- Category, material, and state rows expand in place. Unit changes preserve open
  rows and source details; reopening a material uses its cached record.
- Typed input survives a delayed initial index. A mismatched lazy record is
  rejected, and retry succeeds after the correct data becomes available.
- Desktop and 320px layouts inspected, including long citations and a category
  overview. Browser runs finish without console errors or page exceptions.
- Saved PDF hashes checked for all 28 documents. The full import reconstructs
  the curated files byte-for-byte using `import_reference_tables.py --check`.
  The Hydro corrections are documented in Schema Decision 002. Reproducible
  extraction is not a substitute for an independent audit of every source fact.
- The compiler excludes document URLs from the entire public artifact, including
  JSON/CSV, and rejects source-document assets. Release verification rejects
  tracked source documents. Private owner review is separate from this build.

Screenshots and machine-readable browser results are generated in
`test-results/`. They are excluded from source control and uploaded as a CI
artifact. The version, counts, byte sizes, and exact hashes are recorded in
`materials/release-manifest.json`.

## Deployment handoff

1. Run `scripts/verify_release.py`, the Python/Node tests, and browser tests.
2. Publish **only `materials/`**, including its `data/` and `assets/` directories.
   Do not publish the repository root: it includes synthetic fixtures and
   development prototypes.
3. Mount the artifact at a root or directory URL ending in `/`. Serve `.mjs` as
   JavaScript, JSON as JSON, and the remaining files with their normal MIME types.
4. Revalidate HTML and the release manifest on navigation. Content-addressed
   assets/data may be cached immutably. `_headers` contains suggested rules for
   hosts that support that file; translate them for the selected host.
5. Publish atomically so HTML and its pinned data appear together. Keep a prior
   complete artifact if rollback or active old-tab continuity is required; the
   local builder prunes earlier generated builds rather than retaining releases.
6. Smoke-test the actual public URL, including a retained legacy material URL,
   a focused property query, and a download.

The repository includes a verification workflow and artifact packaging, but
there is no configured remote, domain, hosting account, or publishing workflow.
Those are the remaining deployment decisions. The large-scale serving bake-off
and tools-repository compatibility export are explicitly deferred.

Original document access for paying customers is also deferred to
[the source access plan](source-access-and-expansion.md); this static artifact
has no document delivery endpoint. It is not a paid-access implementation.
