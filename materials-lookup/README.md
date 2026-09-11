# Materials data project

The source of truth behind the **Materials** tool. This directory holds the
curated data, the builder, and the validation gates. The published site it
generates lives at `tools/materials/` and is registered in `catalog.json` like
any other tool.

Adding a material happens here, not anywhere else. The project this came from
is closed; nothing upstream is maintained.

Current contents: **222 material identities, 92 named states, 1,593
observations, 10 registered properties and references to 28 source documents**.
The generated site has no runtime dependencies, backend, accounts, or network
search service.

Material queries open complete datasheets. Exact property queries open
category-grouped reference ranges. Broad queries such as `plastic strength`
ask for a precise property. Specified limits stay distinct from measured
values, and every observation retains its conditions and source citation.

## Build

The builder uses only the Python standard library, so a normal rebuild needs no
virtual environment:

```sh
python3 materials-lookup/builder/build_site.py --output ../tools/materials
```

Run it from the repository root. `--check` validates and renders in memory
without writing. After a rebuild, refresh the site's generated metadata:

```sh
python3 scripts/inject_seo_meta.py        # canonical + Open Graph from catalog.json
python3 scripts/generate_sitemap.py
python3 scripts/generate_homepage_metadata.py
```

Then preview from the repository root and open
<http://localhost:8000/tools/materials/>:

```sh
python3 -m http.server --bind 127.0.0.1
```

Useful searches: `6061-T6`, `TECAPEEK tensile strength`, `PEEK` or `316L` (an
ambiguous designation), `density`, `plastic strength`, `2205`, `253 MA`,
`904L`, `Alloy 825`, `C11000`, `Ti6Al4V`, `4140`, `D2`, `H13`.

The toolbar switches metric and imperial display. Each property has its own
unit override; values and citations appear below its heading. Both preferences
persist in the browser.

### What the build owns, and what it does not

`tools/materials/index.html` is generated from `src/index.html`. Anything that
must survive a rebuild belongs in the template, which is why the GA4 snippet
and the page description live there. Canonical and Open Graph tags are added
afterwards by `scripts/inject_seo_meta.py` from `catalog.json`, so they must be
re-run after every build. `tests/test_source_documents_stay_private.py` fails if
the published page loses any of them.

## Adding materials

1. Choose a bounded batch from a primary manufacturer table or a clearly
   identified supplier reference table. Prioritise gaps. Do not count alternate
   names or product forms as new materials.
2. Save the document to `private-sources/` at the repository root. It is
   git-ignored and must never be committed or served. See
   [`private-sources/README.md`](../private-sources/README.md).
3. Pin the snapshot by SHA-256 in `curated/reference-manifest.json`, with
   publisher, title, revision and retrieved date.
4. Add or extend an importer in `builder/import_*.py`. Keep exact printed
   numbers, units, page and column locators, conditions, and statistical
   meaning. Review footnotes, and represent grade-wide physical data separately
   from condition-specific limits. The importer is the reproducible record of
   how a number got here.
5. Run the checks below, rebuild, and commit the regenerated site together with
   the curated change.
6. Record the batch and its judgement calls in `docs/<name>-batch-review.md`.

Acceptance: new identities resolve in search and the category trees, imports
reconstruct the checked-in facts, old facts survive unchanged, and the build
still passes the document-exclusion gate.

## Checks

```sh
python3 materials-lookup/builder/build_site.py --check
python3 materials-lookup/builder/schema_lab.py check
python3 -m pytest materials-lookup/tests
python3 materials-lookup/builder/verify_release.py
```

`verify_release.py` needs `jsonschema` for structural validation; install
`requirements-dev.txt` for it. Semantic validation is standard library only, so
the test suite passes without it and the structural tests skip rather than
fail. The verifier checks that every generated file matches the current inputs
by hash and rejects extra files in the publish directory.

A bare `pytest` at the repository root runs this suite together with the tools'
own tests; `pytest.ini` lists both paths.

The Node browser tests (`package.json`) came from the standalone project and
still reference its own layout. This repository's browser tests live in
`tests/browser/`. Porting them is outstanding work.

## Where source documents live

Manufacturer PDFs and other originals are never committed and never served.
They belong in `private-sources/` at the repository root. Only textual
citations ship: publisher, title, revision, page or table locator, the source
literal, and a snapshot hash. No document URLs, embeds, download endpoints, or
files, enforced at compile time and by
`tests/test_source_documents_stay_private.py`.

To build a local owner-only review index from hash-matching downloads:

```sh
python3 materials-lookup/builder/prepare_source_review.py \
  --pdf-dir private-sources --output-dir /private/tmp/materials-source-documents
```

That script refuses to write inside a repository or a preview server root.
Never publish the review index or the documents.

PDF extraction is optional and only needed to reconstruct an import. Normal
builds read the checked-in JSON and make no external requests:

```sh
python3 -m pip install -r materials-lookup/requirements-ingest.txt
python3 materials-lookup/builder/import_reference_tables.py --pdf-dir private-sources --check
```

Omit `--check` to regenerate the reviewed authoring files. The importer rejects
changed PDF snapshots and never downloads or redistributes documents.

## Layout

```text
curated/ + registry/    reviewed authoring records and source snapshot hashes
        |
  release/catalog.py    deterministic adapter into canonical contract v0.1.0
        |
  structural + semantic validation
        |
  release/compiler.py   compact index, lazy records, property projections,
        |               complete exports and the release manifest
  tools/materials/      generated static website (published)
```

`src/` holds the production interface, based on Prototype 05. Interface
redesigns require express permission; see [AGENTS.md](AGENTS.md). `builder/`
holds the build, validation and import entry points; it was named `scripts/`
before the move and was renamed to avoid colliding with the repository's own
`scripts/`. The synthetic schema lab and preserved UI prototypes under
`schema_lab/`, `fixtures/` and `prototypes/` are not part of the published
site.

The real-source mapping and differences from the original spike are in
[Schema Decision 002](docs/schema-decision-002-release.md). Cache policy,
atomic publishing and verification evidence are in
[the release handoff](docs/release-candidate.md); its deployment questions are
now answered by this repository's Netlify setup.

## Project tracking

[PROJECT_LOG.md](PROJECT_LOG.md) records milestones and decisions;
[TODO.md](TODO.md) holds remaining work. Both predate the move and describe a
standalone project. Code is MIT, see [LICENSE](LICENSE); data is CC BY 4.0, see
[DATA-LICENSE.md](DATA-LICENSE.md).
