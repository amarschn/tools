# M1 synthetic schema lab

Status: proposed; implementation waits for approval

Date: 2026-07-31

## Purpose

Turn the lessons from the five synthetic UI prototypes into one versioned data
contract and one measured static-serving strategy. The lab should answer the
expensive-to-reverse questions before we ingest real sources or rebuild the
production interface.

The output is not merely a prettier fixture. It is an executable contract that
can reject invalid data, generate every view used by Prototype 05, and explain
exactly what the browser must download for each lookup mode.

## Recommended starting hypothesis

Keep the canonical dataset normalized and independent of any one UI. Compile it
into small, task-shaped static JSON artifacts:

```text
versioned synthetic collections
  + fixed-seed scale generator
              |
              v
     structural + semantic validation
              |
              v
       deterministic compiler
          /       |        \
         v        v         v
  search index  material   property
  (identity +   record     projection
  availability) bundles    shards
         \        |         /
          \       |        /
           Prototype 05 adapter
                    |
                    v
          legacy compatibility export
```

The browser representation is a generated delivery format, not the source of
truth. Category/property spans are also generated projections, never facts
stored on taxonomy nodes.

The recommended serving candidate is:

- an eagerly loaded, typed search index containing identity and property
  availability but no numeric property values;
- one lazy-loaded bundle per material containing its named states, observations,
  source references, and observation locators;
- one lazy-loaded projection per exact property for taxonomy-grouped reference
  views; and
- a small manifest carrying contract, corpus, and build versions plus artifact
  hashes.

We will measure this against simpler alternatives before adopting it.

## Boundaries

This milestone is synthetic-only. Normal builds, tests, and demos make no
internet requests.

In scope:

- taxonomy, material, named-state, observation, property, property-group,
  condition, source, and locator contracts;
- derived material records and property/category reference views;
- search-index versus detail-payload boundaries;
- deterministic static artifacts, validation, migration, and benchmarks;
- a thin adapter proving the selected interaction still works; and
- the deterministic compatibility collapse required by the existing tools.

Out of scope:

- real-source lookup, extraction, licensing research, or ingestion;
- a database server, API, hosted search service, accounts, or paywall;
- a production UI rewrite or another visual-design bake-off;
- comparison, ranking by value, selection advice, or Ashby charts;
- a universal materials ontology or a generalized ingestion framework;
- curves, equations, and temperature-dependent models; and
- broad categorical ratings in v1. One ratings fixture may be used to confirm a
  deliberate rejection or deferral, not to expand the milestone by default.

## Known inconsistencies the lab must resolve

The repository currently contains two incompatible models, which is useful
evidence but cannot remain the long-term contract:

| Area | Existing builder | Synthetic Prototype 05 model |
|---|---|---|
| Entity model | `family -> grade -> variant` | taxonomy, material, named state, observation |
| Observation owner | variant only | material or named state |
| Property IDs | for example `yield_strength` | for example `tensile_yield_strength` |
| Designations | system-to-value map | array of strings |
| Primary taxonomy | hierarchy parent | implicit first item in `taxon_ids` |
| State conditions | variant fields | repeated into observations in places |
| Sources | source registry | referenced IDs but no synthetic source collection |
| Search payload | descriptions and numeric headlines | richer identity resolver over an inline corpus |

There is also one stale behavior assertion: the search test expects bare
`strength` to require a material, while the accepted product direction says it
should first request a precise property and then permit a property-reference
view. That baseline must be reconciled before parity tests are frozen.

### Present serving baseline

The existing static builder's 19-record search index is 36,120 bytes raw and
7,129 bytes gzip. It includes descriptions, headline values, postings, and a
duplicated token list. Its 19 complete record JSON files total 35,765 bytes raw
and 5,004 bytes gzip, but the browser does not currently consume them.

Prototype 05 takes the opposite approach: its runtime corpus is 164,694 bytes
raw and 10,889 bytes gzip, of which observations account for 142,193 raw bytes.
It eagerly loads everything and derives all rollups in the browser. These are
useful small-scale baselines, not evidence that either strategy will hold at the
planned scale.

The current stable `search-index.json` URL is requested with `force-cache`
without content-hash invalidation, and generated links assume a `/materials/`
deployment path. Cache version mismatch and subpath hosting therefore belong in
the serving tests rather than being left as deployment details.

## Decisions to make

The lab will record these as explicit decisions rather than letting file shapes
decide them accidentally.

| Question | Starting hypothesis | Evidence required |
|---|---|---|
| What is a taxonomy node? | A classification only; it never owns observations. | Empty and cross-classified fixtures remain valid. |
| How is default browsing deterministic? | Each taxon has a primary browse parent and each material has one primary taxon; supplemental links remain searchable but do not enter default rollups twice. | Golden path and count projections. |
| What is a material? | A source- or specification-identifiable substance, grade, species, or system. | Generic concepts and commercial grades both fit without invented parents. |
| What creates a named state? | A stable condition that users or sources deliberately name as a lookup identity. | A reviewed state-versus-observation-condition matrix. |
| Where do conditions live? | State-fixed attributes are stored once; test-specific conditions remain on observations. Effective conditions are derived and conflicts are rejected. | Positive merge and negative conflict fixtures. |
| What is an observation result? | A tagged form for point, source-reported interval, one-sided bound, or explicit unavailable/not-applicable assertion. Uncertainty remains separate. | Lossless round trips and projection goldens. |
| Does absence mean zero or missing? | Neither. Absence is unknown; an explicit source assertion is modeled separately and never enters a numeric range. | Missingness fixtures and coverage counts. |
| Are direct material values inherited by states? | No implicit inheritance. Direct and state observations remain independently traceable. | A deliberate material-plus-state fixture. |
| What belongs in search? | Typed identity, aliases, taxonomy, and compact property availability; no values, prose descriptions, or source details. | Correct golden routing within the payload budget. |
| How is a complete datasheet served? | One material bundle includes the material, its states, observations, and display-ready citation data. | One lazy payload can render the accepted record view. |
| How is a property-only view served? | A generated shard per exact property contains the taxonomy projection needed by the reference view. | No full-corpus download and correct range/count/warning goldens. |
| What is versioned? | Contract version, corpus version, generator version, and deterministic build ID are distinct. | Unsupported versions fail clearly; identical builds hash identically. |

## Canonical contract to prototype

The logical model will use typed, normalized collections. Physical files may be
split for reviewability, but nesting observations inside material authoring files
will not be the canonical truth.

### Dataset manifest

Pins the contract and corpus versions, collection locations, synthetic-data
marker, generator information, and expected entity counts. A deterministic
content hash becomes the build ID; a wall-clock timestamp must not make identical
inputs produce different bytes.

### Taxon

- stable ID, name, aliases, primary browse parent, and optional supplemental
  broader links;
- no property observations or hand-authored envelopes; and
- cycle-free, deterministic browse placement.

### Material

- stable ID independent of mutable names or taxonomy placement;
- name, aliases, identity kind, and one canonical structured designation form;
- explicit primary taxon and supplemental classifications; and
- no requirement for a standard designation or an invented material parent.

### Named state

- stable ID, material ID, source/user-recognizable label, aliases, and registered
  fixed attributes;
- optional supplemental classification only when it has real semantic value; and
- no duplicated observation-specific temperature, orientation, geometry, method,
  or basis fields.

### Observation

- stable opaque ID not derived from the numeric value;
- material ID plus optional state ID, with validator-enforced consistency;
- exact property ID and a discriminated reported-result form;
- reported representation and unit plus coherent canonical numeric form where
  applicable;
- uncertainty distinct from a reported interval and distinct from multiple
  observations;
- basis, registered observation conditions, test method, source ID, and precise
  structured locator; and
- minimal lifecycle fields for active/superseded observations without deleting
  history.

### Property and property group

- an exact semantic definition, quantity or dimension, canonical unit, display
  metadata, aliases, and optional group membership;
- broad terms such as `strength` remain property groups, not aliases for one
  arbitrarily selected property; and
- legacy property-ID mappings are explicit compatibility data, not extra
  canonical IDs.

### Condition registry

Defines each condition key's type, canonical unit or enum, and legal placement:
state, observation, or deliberately both. Unknown keys and conflicting
state-fixed/observation values are hard errors.

The first decision matrix will cover heat treatment, formulation or
reinforcement, laminate layup, moisture, product form, thickness, orientation,
temperature, test method, and statistical basis.

### Source and locator

Sources carry document identity, publisher, revision/date, license information,
and a stable synthetic source ID. Locators require a human-readable label and
may add structured page, table, figure, row, column, section, or record fields.
Every numeric observation must resolve to both a source and a locator.

### Validation approach

Use JSON Schema Draft 2020-12 for per-document shapes and a small Python semantic
validator for cross-document rules such as references, cycles, units, placement,
and conflicts. The schema validator is a pinned build/development dependency;
the generated browser has no runtime dependency. Diagnostics receive stable
codes and JSON-style paths so negative tests do not depend on changing prose.

## Fixture program

### Preserve the present evidence

First migrate the current synthetic corpus losslessly:

- 27 taxa;
- 32 materials;
- 38 named states;
- 360 observations;
- 13 properties; and
- 5 property groups.

Preserve valid stable IDs. Every rename or property-ID normalization requires an
explicit old-to-new mapping and a migration report. The current JS corpus remains
available as the frozen reference until parity is proved.

### Add only missing adversarial cases

The semantic fixture will gain the smallest set needed to cover:

- a source-reported interval, one-sided bound, uncertainty, and explicit
  unavailable/not-applicable assertion;
- two disagreeing conditioned observations and one superseded observation;
- direct material data, state-only data, and a deliberate direct-plus-state case;
- a commercial material with no standard designation;
- one material with a primary chemistry path and supplemental composite path;
- empty, singleton, and multi-member category/property coverage;
- converted reported units without losing the reported form;
- a long structured source locator including table/row/cell detail; and
- a state-fixed attribute versus observation-condition conflict as an invalid
  case.

The positive fixture should be rich, not large. It remains conspicuously
synthetic through reserved IDs, source names, warnings, and its output path.

### Negative fixtures

Each invalid fixture should fail for one intended invariant, including:

- malformed or duplicate IDs and unsupported contract versions;
- missing or wrong-namespace references and taxonomy cycles;
- missing primary membership or duplicated primary/supplemental membership;
- observation/state material mismatch or an observation attached to a taxon;
- unknown property, condition, source, basis, method, or unit;
- illegal condition placement and state/observation conflicts;
- non-finite values, inverted intervals, and incoherent canonical units;
- a reported interval disguised as uncertainty;
- missing source locators; and
- normalized alias collisions, which must at least produce a deterministic
  diagnostic for review.

### Scale fixture

Generate scale data on demand from a checked-in seed and configuration. Do not
commit the large generated corpus. Record generator version, seed, material,
state, searchable-identity, observation, and property counts plus output hashes.

The initial run should contain 10,000 searchable material/state identities. If
we instead choose 10,000 base materials, the state ratio and larger searchable
count must be stated explicitly so benchmark results remain comparable.

## Derived semantics and goldens

Move counting and projection rules out of Prototype 05's page code into testable
domain functions. Golden outputs must prove:

- supplemental classification does not double-count a material;
- categories never acquire stored observations or values;
- a state with two observations is one covered subject and two observations;
- direct material data is not silently inherited by every state;
- exact-property intervals contribute their reported endpoints to a corpus span,
  while uncertainty does not silently widen it;
- inactive/superseded observations remain auditable but are excluded by default;
- zero coverage stays a valid empty result and singleton coverage renders one
  value rather than `x-x`;
- missing properties are neither zero nor inherited;
- eligible subjects, covered subjects, materials, states, observations,
  condition sets, bases, and unavailable assertions are counted separately;
- mixed temperature, orientation, moisture, product form, thickness,
  formulation, layup, method, and basis flags are deterministic; and
- browse and drilldown order follows taxonomy/alphabetic rules, never a numeric
  endpoint.

Record assembly also gets a golden: it combines state-fixed and
observation-specific conditions for display without mutating canonical records.

## Static-serving bake-off

All candidates are generated from the same validated canonical fixture. We will
measure two independent choices instead of conflating them.

### Artifact topology

1. **Full monolith:** one complete snapshot. This is the simplicity baseline.
2. **Index plus records:** compact search data and per-material bundles. This
   exposes whether property-only lookup becomes awkward or request-heavy.
3. **Index, records, and raw property shards:** all observations for one selected
   property load together and the browser derives taxonomy rollups. This is the
   audit-friendly semantic oracle.
4. **Index, records, and generated property projections:** the recommended
   delivery candidate. It contains the range/count/warning tree needed by the
   accepted property-reference route. Every projection must still be checked
   against the raw-shard oracle during the build.

### Search-index encoding

Compare readable object rows with a compact columnar/parallel-array encoding.
Keep the readable source model either way. Adopt the compact encoding only if
measured transfer or parse savings justify its adapter complexity.

### Candidate generated artifacts

- `manifest.json`: versions, counts, paths, hashes, and synthetic warning;
- `search-index.json`: typed taxonomy/material/state/property identities,
  aliases/designations, primary/supplemental scope IDs, and compact property
  availability;
- `records/<material-id>.json`: the complete material, named states,
  observations, source IDs, and precise locators for one datasheet request;
- `sources.json`: shared source-document metadata keyed by source ID, rather
  than duplicated in every record;
- `property-observations/<property-id>.json`: raw property shards used as the
  semantic oracle and serving candidate;
- `properties/<property-id>.json`: generated hierarchy rows, ranges, counts,
  warnings, and record/state targets for the property reference view; and
- `compatibility/materials.json`: deterministic legacy collapse with the chosen
  observation ID recorded for every emitted value.

The manifest may point at content-hashed filenames for immutable caching. The
lab will be served by an ordinary static HTTP server; SQLite or another database
may be reconsidered only if the static candidates fail measured needs.

### Tasks to benchmark

- load the search surface and resolve a material identity;
- open a complete material datasheet;
- resolve a material-plus-property query and focus the record;
- open a precise property-only taxonomy view;
- navigate a category breadcrumb and drilldown; and
- repeat warm searches without additional data requests.

Measure build time, raw and gzip bytes, request count, parse/hydration time,
record and property payload sizes, browser heap, warm query p50/p95/p99, 50-row
DOM rendering, and end-to-end query-to-paint. Test cold and warm material/property
opens, a simulated slower network, cache-version mismatch, and both root and
subpath hosting. Record the machine, browser, Python/Node versions, warmup count,
and sample count.

Provisional guardrails to validate or revise from the recorded baseline:

- at most 3 MiB raw and 400 KiB gzip for 10,000 searchable identities;
- warm query p95 below 20 ms and p99 below 50 ms;
- query-to-paint p95 below 100 ms;
- never more than 50 rendered result rows;
- one additional material payload for a datasheet, plus at most one shared
  source-registry fetch when it is not cached, and one property payload for a
  property-reference route after the index is available; and
- byte-identical artifacts and hashes from identical inputs.

Correctness, size, determinism, and row-cap gates should run automatically.
Machine-sensitive latency gets a committed baseline and regression tolerance,
not a brittle universal CI threshold.

## Search and UI compatibility

Freeze a table-driven golden query suite before adapting the UI. It asserts the
route, chosen scope/property intent, result IDs and order, and result cap—not
merely that something matched.

Required cases include:

- exact IDs/designations: `AX60`, `AX60 T6`, `AX60 T651`;
- collisions: `AX60`/`AX61` and `N6`/`N66`;
- aliases and case, hyphen, space, and Unicode normalization;
- curated misspellings;
- material plus property: `P100 tensile strength`, `AX70 T6 yield`;
- precise property: `tensile strength`;
- category plus property: `plastic tensile strength`;
- ambiguous groups: `strength`, `plastic strength`;
- ambiguous category/property language: `glass strength`;
- category browse and empty category: `engineering plastics`, `thermosets`;
- unsupported comparison: `strongest plastic`; and
- no-match and overly broad queries.

Gates are 100% top-one for exact IDs, designations, and explicit aliases; all
curated typo targets in the top five; 100% correct route/intent; and no value
ranking for comparison intent.

Leave Prototypes 01-05 intact. Add only a schema-backed adapter or lab copy of
Prototype 05 to prove that material datasheets, focused properties, property
reference views, category navigation, and counts can be rendered from generated
artifacts without UI-only fields in the canonical contract.

## Compatibility and migration

Build three explicit bridges:

1. **Current synthetic JS to the new contract.** It must account for the frozen
   27/32/38/360 entity counts before intentional additions.
2. **New contract to the Prototype 05 adapter.** Accepted interactions and
   projection semantics must remain equivalent.
3. **New contract to the legacy scalar/range tool format.** Every collapse rule
   is deterministic, and each selected output names its source observation ID.
   No averaging or unexplained tie-breaking is allowed.

Keep the current curated builder unchanged during M1. Its factual/seed records
receive a mapping report, not a silent migration. Real evidence tests the new
contract only in the later two-source milestone.

## Execution sequence and review gates

### Phase 0 — freeze the baseline

- Reconcile the stale `strength` assertion with the accepted product behavior.
- Capture present entity counts, query outcomes, projection examples, and build
  hashes.
- Write the acceptance matrix and migration mapping inventory.

Gate: the baseline describes what must remain equivalent and which old behaviors
are intentionally retired.

### Phase 1 — examples before machinery

- Write the domain glossary and state-versus-condition matrix.
- Draft one representative positive dataset and focused invalid examples.
- Draft the canonical property/designation/locator forms and legacy mappings.

Review checkpoint 1: approve the glossary, condition placement, and one complete
material/state/observation/source example before the full validator is built.

### Phase 2 — contract and validation

- Add the versioned structural schemas and semantic validator.
- Port the current fixture, add the missing adversarial cases, and make all
  negative diagnostics executable.
- Add deterministic record-assembly and projection goldens.

Gate: valid data has zero errors; every invalid fixture fails for its intended
stable diagnostic; repeated validation/builds are identical.

### Phase 3 — serving compiler and bake-off

- Generate the three artifact topologies and both index encodings.
- Prove every search target resolves and full record provenance survives.
- Generate and benchmark the fixed-seed scale fixture.
- Write a short serving decision report with measured tradeoffs.

Review checkpoint 2: choose the static artifact topology, index encoding, and
accepted performance/size budget from the evidence.

### Phase 4 — interaction and compatibility proof

- Connect the schema-backed Prototype 05 adapter.
- Run golden search, record, projection, navigation, narrow-screen, and offline
  paths.
- Produce and verify the legacy compatibility export.

Gate: current accepted tasks work without reading the inline corpus, downloading
the full observation database, or adding UI-specific source fields.

### Phase 5 — freeze the decision

- Record Schema Decision 002, explicitly superseding or retaining Decision 001.
- Commit the benchmark and migration reports, schemas, fixtures, tests, seed,
  generator, and chosen artifacts or reproducible build instructions.
- Update `PROJECT_LOG.md` and move completed M1 items out of `TODO.md`.

Review checkpoint 3: approve the frozen M1 contract before the two-source reality
check begins.

## Deliverables

Exact paths can be adjusted during implementation without changing scope, but
the completed lab should contain:

- versioned schema/contract files and a domain glossary;
- state-condition and legacy-ID mapping tables;
- checked-in semantic positive and negative fixtures;
- a fixed-seed scale generator, not its bulky output;
- one deterministic validate/build/benchmark command surface;
- unit, semantic, golden-query, projection, adapter, and compatibility tests;
- a schema-backed Prototype 05 lab entry while preserving all existing demos;
- a serving benchmark/decision report;
- Schema Decision 002; and
- updated project log and TODO state.

## M1 exit criteria

M1 is complete only when all of the following are true:

- every accepted M0 task is expressible without pseudo-material categories or
  UI-specific exceptions;
- the state-versus-condition matrix covers every current condition key;
- all current synthetic entities migrate with no unexplained loss;
- point, interval, bound, uncertainty, missingness, conflict, supersession, and
  locator cases round-trip losslessly;
- positive and negative validation suites pass with deterministic diagnostics;
- record and category/property projection goldens produce correct counts,
  ranges, and warnings without double counting or ranking;
- exact/alias/typo/intent query gates pass and no query renders over 50 rows;
- Prototype 05 behavior is reproduced through generated artifacts;
- the compatibility export matches a checked-in golden and identifies every
  selected observation;
- serving budgets are measured at the fixed scale and the chosen topology is
  recorded;
- normal builds and demos are deterministic and offline; and
- Schema Decision 002 explicitly records the result instead of silently editing
  Decision 001.

## Git and work-log discipline

Implementation should land in small reviewable commits, approximately:

1. approved plan, baseline, glossary, and examples;
2. contracts, semantic fixture migration, and validation;
3. derived projections and goldens;
4. static compiler, scale generator, and benchmark report;
5. Prototype adapter, compatibility export, ADR, and project-log closeout.

Generated scale data, browser traces, and temporary benchmark output stay
untracked. Seeds, expected goldens, environment metadata, and the final measured
report are committed. No phase is marked complete in `PROJECT_LOG.md` until its
gate actually passes.

## Approval meaning

Approving this plan authorizes the synthetic-only M1 work above. Implementation
begins with Phase 0 and pauses at the three review checkpoints; it does not
authorize real-source research, a backend, or a production UI rewrite.
