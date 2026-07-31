# Materials Lookup prototype

This repository contains the first demo-able slice of the standalone
Materials Lookup plan:

- hierarchical family, grade, and variant records;
- observation-level values with conditions, uncertainty, and source locators;
- a static, search-first interface with material, family, and property results;
- generated material record pages and sorted property pages;
- no framework, package install, server compute, or hand-edited build output.

The seed corpus is deliberately small. It exists to stress the schema and the
interaction model, not to support engineering decisions. The generated site
shows the same warning wherever values are presented.

## Run the demo

```sh
python3 scripts/build_site.py
python3 -m http.server 8000
```

Then open <http://localhost:8000/materials/>.

Useful searches include `6061`, `7075-T6`, `mild steel`, `stiffness`,
`yield strength`, `delrin`, and `aluminium`.

The source/credit index is at
<http://localhost:8000/materials/sources/>.

## Synthetic UI bake-off

Five additional compact UI directions live at
<http://localhost:8000/prototypes/>. They share a synthetic-only stress corpus
and test a lookup-only product boundary:

- compact directory;
- material-first lookup;
- split result/record inspector;
- explicit query resolver;
- dual-mode material datasheets and property/category overviews.

The fixture separates taxonomy, concrete material identities, named states, and
observations. It contains 50 data-bearing records and no factual claims or
network requests. See
[`docs/prototype-schema-findings.md`](docs/prototype-schema-findings.md) for the
schema problems it exposes.

## Validate and test

```sh
python3 scripts/build_site.py --check
python3 -m unittest discover -s tests -v
node tests/prototype_search.test.js
```

## Project tracking

- [`PROJECT_LOG.md`](PROJECT_LOG.md) records completed work, decisions, and
  milestone gates.
- [`TODO.md`](TODO.md) is the prioritized live work queue.

When a meaningful task is completed, remove it from `TODO.md` and add the
outcome to the newest dated entry in `PROJECT_LOG.md`.

## Source and generated files

```text
curated/        hand-reviewed prototype records and source registry
registry/       registered properties and observation condition keys
src/            static page source and templates
scripts/        validation and site generation
tests/          build and schema checks
materials/      generated site; do not hand-edit
```

Rebuild after changing anything in `curated/`, `registry/`, or `src/`.
The `raw/`, `extract/`, `normalized/`, and `review/` ingestion stages from the
plan are intentionally deferred until the first independent source ingestion.

## Prototype decisions

The original static-site spike adopts this hierarchy:

```text
family → grade → variant → conditioned observations
```

Only variants carry measured observations. Family and grade summaries are
generated as observed envelopes over descendants, so an aggregate range cannot
be mistaken for a measurement or become a second source of truth. Prominence is
used only as a small ranking tie-breaker.

The browser receives a compact search index; complete records are emitted
separately and record/property pages are pre-rendered as static HTML.

The newer synthetic UI bake-off tests a separate
`taxonomy → material → named state → observation` contract. That remains a
working hypothesis until the M1 tasks in [`TODO.md`](TODO.md) are complete; it
has not silently replaced the original decision in
[`docs/schema-decision.md`](docs/schema-decision.md).

Code is MIT licensed. Original data is CC BY 4.0; source-specific attribution
and the prototype-estimate warning are described in
[`DATA-LICENSE.md`](DATA-LICENSE.md).
