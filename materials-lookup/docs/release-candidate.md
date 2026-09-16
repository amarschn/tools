# Materials release review

Updated: 2026-09-15

The Materials lookup and data pipeline are integrated into the tools repository.
The generated page is `tools/materials/`, backed by `materials-lookup/`.
The September 15 review added persistent light/dark/system settings, a Tools
link, input help, copy-link sharing, and structured page metadata. The browser
and release checks now target the integrated output. The README is generated
from `src/README.md` so it survives a rebuild.

The interface follows Prototype 05: compact toolbar and search, expandable
category/material rows, and shared value/condition/source columns. The original
prototypes remain intact. Future interface redesigns require express permission.

## Review locally

Build using the README commands, serve the repository on port 8148, then open `http://127.0.0.1:8148/tools/materials/`.

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

11. Open Settings, switch light/dark/Auto, and reload. Check Copy link and the
    Tools navigation. Repeat at 320px; source details and unit controls remain
    visible. Download the record JSON, catalog JSON, and observations CSV.

## Evidence

- The combined repository suite passes: 1,603 tests and 2,611 subtests on
  Python 3.13, with no skips. This includes full structural and semantic
  validation, negative cases, and source-to-SI conversion checks.
- Node checks pass: 52 search cases, conversions, and all 222 record
  projections, plus 21 prototype queries.
- Both thread-tool browser suites pass, covering the pipe and product-screw
  work carried by this branch, including diagrams, unit changes, and exports.
- Deterministic compilation; every checked-in artifact and manifest hash is
  verified against a fresh in-memory build. Extra files in the publish tree
  fail the release gate.
- 222 factual material identities, 92 named states, 1,593 observations,
  10 registered properties, and text references to 28 source documents. One registered property
  currently has no observations; missing data is displayed as unreported.
- Readable search index approximately 269 KB raw / 23 KB gzip. Warm Node query
  p95 is approximately 8 ms on the development machine. This measurement is a
  current-corpus baseline, not a large-corpus performance claim.
- Search routing, conversion, significant figures, bounds, intervals,
  uncertainty conversion, and compiler/browser parity across all 222 records.
- Chromium browser verification at root, `/nested/reference/`, and
  `/tools/materials/`: material and
  property flows, clarification, ambiguity, rejected ranking intent, deep links,
  reload, browser history, units, missing data, and a 50-row result cap.
- One additional JSON request opens a full datasheet. Lookup data stays local;
  the shared Google Analytics script is the only external script. Browsing
  never loads the full-catalog export or synthetic corpus. Tests intercept
  Analytics requests and check export events without sending test traffic.
- Category, material, and state rows expand in place. Unit changes preserve open
  rows and source details; reopening a material uses its cached record.
- Typed input survives a delayed initial index. A mismatched lazy record is
  rejected, and retry succeeds after the correct data becomes available.
- Desktop and 320px layouts inspected in light and dark, including long
  citations, settings, and a category overview. Theme choices persist. Copy
  link matches the current URL. Downloaded JSON and CSV match the generated
  files. Browser runs finish without console errors or page exceptions.
- The earlier data-batch review checked saved hashes for all 28 documents
  and reconstructed the curated files with `import_reference_tables.py --check`.
  The Hydro corrections are documented in Schema Decision 002. Reproducible
  extraction is not a substitute for an independent audit of every source fact.
- The compiler excludes document URLs from the entire public artifact, including
  JSON/CSV, and rejects source-document assets. Release verification rejects
  tracked source documents. Private owner review is separate from this build.

Screenshots and machine-readable browser results are generated in
`materials-lookup/test-results/`, excluded from source control. The version,
counts, byte sizes, and hashes are in `tools/materials/release-manifest.json`.
The release gate compares all 776 outputs against the source, including the
complete index after the shared SEO transform.

## Deployment handoff

Follow the repository's [release procedure](../../docs/RELEASE.md): push the
verified task branch, compare local and remote SHAs, merge once into `main`,
check the integrated result, and push `main` once. Netlify publishes
`https://transparent.tools/tools/materials/`; GitHub Pages is the secondary host.
The user confirmed the Netlify project is active, has at least 15 credits, and
has no running deployment before this release.

After publication, verify the expected SHA, the homepage, Materials, the
changed thread tool, an unchanged calculator, and `sitemap.xml`. Save the
published SHA and live results with the local browser report before closing
the task.

Source documents remain in the ignored `private-sources/` directory. The
public artifact and exports contain citations only. Shared-data consolidation
and rendered pages for individual materials remain separate follow-up work.

Original document access for paying customers is also deferred to
[the source access plan](source-access-and-expansion.md); this static artifact
has no document delivery endpoint. It is not a paid-access implementation.
