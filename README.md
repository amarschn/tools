# Materials Lookup

A local release candidate for source-traceable material and property lookup.
The static site contains **134 material identities, 24 named states, 840
observations, 10 registered properties and 5 source documents**. It has no
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
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://localhost:8000/materials/>. Useful searches:

- `6061-T6` or `6061 T6 extrusion`;
- `TECAPEEK tensile strength`;
- `PEEK` or `316L` (an ambiguous designation);
- `density` or `plastic strength`.

The Units control switches metric/imperial display. Expand a property to set
its own unit override and inspect the individual values and citations. Both
preferences persist locally; switching the system resets property overrides.

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

`src/` contains the production interface. The original static renderer remains
in `scripts/build_site.py` for compatibility fixtures; a root with `src/app.mjs`
uses the canonical release compiler. The synthetic schema lab and disposable
UI prototypes remain under `schema_lab/`, `fixtures/`, and `prototypes/`. They
are not part of the publish artifact.

The real-source mapping and differences from the original spike are recorded
in [Schema Decision 002](docs/schema-decision-002-release.md).

## Reconstruct the source import

Normal builds read checked-in JSON and make no external requests. PDF extraction
is an optional development task, using locally saved documents matching the
SHA-256 hashes in `curated/reference-manifest.json`.

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
