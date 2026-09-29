# Materials UI bake-off

These prototypes test five compact lookup interactions against the same
synthetic-only corpus:

1. `01-compact-index.html` — dense directory;
2. `02-material-first.html` — choose a material, then a property;
3. `03-split-inspector.html` — list and one-record inspector;
4. `04-query-resolver.html` — explicit query clarification;
5. `05-dual-mode.html` — material datasheets plus category-grouped property
   overviews.

They are disposable decision artifacts. They do not import the production UI,
do not use the curated factual corpus, and do not write generated site files.

## Run

From the repository root:

```sh
python3 -m http.server 8000
```

Open <http://localhost:8000/prototypes/>.

The shared fixture is visibly synthetic and all identifiers are reserved under
`synthetic-*`. Its 50 data-bearing lookup records cover metal-like alloys,
steels, plastics, elastomers, foams, ceramics, glasses, composites, and wood.
There are deliberate designation collisions, missing properties, multiple
observations for the same property, cross-classification, and condition-sensitive
values.

Run the shared parser and corpus checks with:

```sh
node tests/prototype_search.test.js
```

## What is intentionally absent

- marketing copy and a hero section;
- custom web fonts, gradients, decorative color, large cards, and a settings
  drawer;
- sorted property rankings or compare controls;
- internet requests and factual material claims.

Every prototype keeps record count, corpus/build version, synthetic status, and
measured search time visible.

Prototype 05 also displays explicitly labelled category-level observed ranges.
These are derived reference projections over the fixture, not stored category
properties and not a flat ranking of materials.

See [`decision-notes.md`](decision-notes.md) for the tradeoff matrix and the
recommended next direction.
