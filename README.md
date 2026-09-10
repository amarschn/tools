# Materials Lookup

A local release candidate for source-traceable material and property lookup.
The static site contains **158 material identities, 37 named states, 1,138
observations, 10 registered properties and references to 8 source documents**. It has no
runtime dependencies, backend, accounts, or network search service.

Material queries open complete datasheets. Exact property queries open
category-grouped reference ranges. Broad queries such as `plastic strength`
ask for a precise property. Specified limits stay distinct from measured
values, and every observation retains its conditions and source citation.

## Build and preview

Use Python 3.10 or newer; development and CI are verified with Python 3.13.

```sh
python3.13 -m venv .venv
.venv/bin/python3.13 -m pip install -r requirements-dev.txt
.venv/bin/python3.13 scripts/build_site.py
python3 -m http.server 8001 --bind 127.0.0.1
```

Open <http://localhost:8001/materials/>. Useful searches:

- `6061-T6` or `6061 T6 extrusion`;
- `TECAPEEK tensile strength`;
- `PEEK` or `316L` (an ambiguous designation);
- `density` or `plastic strength`.
- `2205`, `253 MA`, `904L`, or `Alloy 825`.

The toolbar switches metric/imperial display. Each property has its own unit
override; individual values and citations appear below its heading. Both
preferences persist locally; switching the system resets property overrides.

Source references are text-only. Original manufacturer PDFs and document URLs
are excluded from the public site and all JSON/CSV exports. The material record
view remains available. Paid access to original documents is planned separately
in [the source access plan](docs/source-access-and-expansion.md).

## Release checks

```sh
.venv/bin/python3.13 scripts/build_site.py --check
.venv/bin/python3.13 scripts/schema_lab.py check
.venv/bin/python3.13 -m unittest discover -s tests
.venv/bin/python3.13 scripts/verify_release.py
npm ci
npx playwright install chromium
npm test
npm run test:browser
```

`verify_release.py` requires structural JSON Schema validation and checks that
all generated files exactly match the current inputs, including hashes. It
rejects extra files in the publish directory. Browser tests start their own
local server, exercise root and nested hosting paths, and save screenshots and
results in `test-results/`. The GitHub workflow runs these gates and packages
the static output; it does not deploy.

## Publish artifact

**Publish only `materials/`.** It can be mounted at a site root or any directory
ending in `/`; no SPA rewrite or server compute is required. Query URLs identify
materials, states, forms, properties and categories. Retained legacy record
URLs redirect to those views. Content-addressed assets and JSON stay in the same
release, with build IDs checked on lazy loads.

See [the release handoff](docs/release-candidate.md) for cache policy, atomic
publishing, verification evidence, and remaining deployment decisions. No
hosting account, Git remote, domain or public deployment is configured yet.

## Data and build path

```text
curated/ + registry/       reviewed authoring records and source snapshots' hashes
           |
     release/catalog.py   deterministic adapter into canonical contract v0.1.0
           |
     structural + semantic validation
           |
     release/compiler.py  compact index, lazy records, property projections,
           |              complete exports and release manifest
       materials/         generated static website
```

`src/` contains the production interface, based on Prototype 05. Interface
redesigns require express user permission; see [AGENTS.md](AGENTS.md).
The original static renderer remains
in `scripts/build_site.py` for compatibility fixtures; a root with `src/app.mjs`
uses the canonical release compiler. The synthetic schema lab and preserved
UI prototypes remain under `schema_lab/`, `fixtures/`, and `prototypes/`. They
are not part of the publish artifact.

The real-source mapping and differences from the original spike are recorded
in [Schema Decision 002](docs/schema-decision-002-release.md).

## Reconstruct the source import

Normal builds read checked-in JSON and make no external requests. PDF extraction
is an optional development task, using locally saved documents matching the
SHA-256 hashes in `curated/reference-manifest.json`.

Keep those PDFs outside the repository and the preview server root. To prepare
a local owner-only review index from already downloaded, hash-matching files:

```sh
.venv/bin/python3.13 scripts/prepare_source_review.py \
  --pdf-dir /private/tmp --output-dir /private/tmp/materials-source-documents
```

Open `/private/tmp/materials-source-documents/index.html` locally. This temporary
directory is not a backup; use a durable private directory outside the repository
for retained source snapshots. Never publish the review index or documents.

```sh
.venv/bin/python3.13 -m pip install -r requirements-ingest.txt
.venv/bin/python3.13 scripts/import_reference_tables.py --pdf-dir /path/to/pdfs --check
```

Omit `--check` to regenerate reviewed authoring files. The importer rejects
changed PDF snapshots; it does not download or redistribute the documents.

## Project tracking

[PROJECT_LOG.md](PROJECT_LOG.md) records milestones and decisions;
[TODO.md](TODO.md) contains the remaining work. The earlier schema-lab plan is
retained as history, including its deferred large-scale serving experiments.
Code is MIT licensed. See [DATA-LICENSE.md](DATA-LICENSE.md) for data attribution.
