# Materials data consolidation
Date: 2026-09-11
Status: Plan for review; nothing implemented

Three materials datasets now live in this repository. This plan reduces them to
one without changing any tool, using the existing `pycalcs/material_db.py`
interface as the seam and its 63 tests as the acceptance gate.

## What exists today

| Store | Size | Model | Consumers |
| --- | --- | --- | --- |
| `materials-lookup/curated/` | 222 grades, 519 entity records, 1,593 observations, 10 properties, 28 sources | observation-based, each value carrying conditions, basis and a page-level citation | `tools/materials/` |
| `data/materials/materials.json` | 60 materials, 29 properties, 18 sources | one record per material, values scalar or `{value, min, max}` | `tools/materials-explorer/` through `pycalcs/material_db.py` and `pycalcs/material_indices.py` |
| `pycalcs/materials.py` | 7 materials, 3 properties | a hardcoded tuple in source | `tools/ashby-chart/` |

`materials-lookup/` arrived on 2026-09-11 from a project that is now closed.
The other two predate it: `data/materials/` and `scripts/materials_ingest/`
were committed 2026-04-24, `pycalcs/material_db.py` on 2026-04-11.

## How much actually overlaps

Less than the names suggest.

Materials: three of the 60 selection entries have a counterpart among the 511
lookup entities, and only at family level.

    Aluminium 6061-T6      ~ Aluminium 6061
    Aluminium 6063-T5      ~ Aluminium 6063
    Polycarbonate (PC)     ~ Polycarbonate (PC)

Properties: all 10 lookup properties already exist in the 29-property registry
once naming is reconciled. `max_service_temperature` is `max_service_temp`,
`tensile_yield_strength` is `yield_strength`, and `ultimate_tensile_strength`
is `tensile_strength`.

The selection store carries 19 properties the lookup store has no concept of.
Three of those are the reason the Ashby tools exist at all.

The two stores are therefore complementary rather than competing: one holds
broad generic materials with cost and environmental data for choosing between
them, the other holds specific commercial grades with the provenance to defend
a number. Nothing is currently broken. The cost of leaving them apart is two
schemas, two ingest paths, and no way to ask a grade-level question in a
selection chart.

## Why the observation model wins

It is strictly richer, and the selection store is already partway there. Its
1,593 property values break down as:

    230  bare integer
    224  bare float
    150  {value, min, max}
     58  {value, basis, source_id}
     12  {value, basis, min, max}
     11  {value, condition}

Basis, per-property source, and condition already appear. Those are exactly the
fields an observation carries, so the mapping is a widening, not a
reinterpretation. Going the other way would flatten 1,593 cited observations
into single values and discard their conditions and page locators.

## The seam that makes this safe

`pycalcs/material_db.py` is already the right interface, and it is already
parameterised by path:

```python
def load_database(path=None, *, reload=False) -> dict
def get_value(material, property_name)           -> float | None
def get_range(material, property_name)           -> tuple[float, float] | None
def get_source(material, property_name, sources) -> dict | None
def get_basis(material, property_name)           -> str
```

Per-property source and basis are already in the contract. An observation store
can answer every one of these. No tool needs to change, because no tool reads
the data directly: `materials-explorer` and `material_indices.py` both go
through this module.

`tests/test_material_db.py` (39 tests) and `tests/test_material_indices.py`
(24 tests) pin the behaviour. **Those 63 tests passing unchanged is the
acceptance gate for the whole migration.**

## Steps

### 1. Spike: prove the interface can be satisfied

Write an adapter that projects lookup-store records into the shape
`material_db` expects. Cover only the three overlapping materials. Migrate no
data and change no tool. Run the 63 tests against a database assembled through
the adapter.

This either de-risks everything below or invalidates it, for about a day of
work. Do it before committing to the rest.

### 2. Reconcile the property registry

Rename the three mismatched properties to one spelling. Decide it once and
apply it in both stores at the same time, because `material_indices.py` and the
Ashby performance indices reference them by name.

### 3. Classify the 19 properties the lookup store lacks

- **Mechanical, and a direct fit:** `fracture_toughness`, `cte`,
  `melting_point`, `shear_modulus`, `hardness_vickers`, `hardness_shore_a`,
  `hardness_shore_d`, `compressive_strength`, `flexural_modulus`,
  `impact_strength_izod`, `fatigue_endurance_limit`, `electrical_resistivity`,
  `thermal_diffusivity`, `glass_transition_temp`. Add to the registry and
  migrate as ordinary observations.
- **Derived, and should not be stored:** `specific_stiffness`,
  `specific_strength`. `get_computed_property` already derives these. Keep
  deriving them, and do not create a second definition. This is the Single
  Source of Truth rule from AGENTS.md applied to an equation rather than data.
- **Time and region dependent:** `price_per_kg`, `co2_footprint`,
  `embodied_energy`. These do not belong in a page-citation model, because
  "page 12 of a 2019 datasheet" is the wrong provenance shape for a price.
  Hold them in a separate overlay keyed by material id, with its own as-of
  date, and let `material_db` join them. Decide this before migrating, not
  during.

### 4. Two blockers found while writing this plan

- `SOURCE_TYPES` in `materials-lookup/builder/build_site.py` is
  `{supplier_catalog, government_handbook, manufacturer_datasheet,
  prototype_seed}`. The selection store cites textbooks, for example
  `Ashby, M. F. (2011), Materials Selection in Mechanical Design`. A migration
  needs a source type for a published reference work that is not a pinned
  document snapshot.
- `tests/test_source_documents_stay_private.py::test_published_sources_keep_attribution`
  requires a `sha256` on every source. The schema does not: it requires only
  `id`, `title` and `source_type`, and the hash lives in
  `curated/reference-manifest.json` for pinned PDFs. The test is stricter than
  the contract and will reject the first textbook source. Relax it to require a
  snapshot hash only for source types that are pinned documents, and keep
  requiring a publisher for all of them.

### 5. Migrate the 60

Write the migration as an importer under `materials-lookup/builder/`, reading
`data/materials/materials.json` and emitting curated records. It runs once, but
it belongs in the repository permanently as the reproducible record of how
those values arrived, exactly like the existing importers. Map each property
value to an observation: value or interval as given, basis from the value's own
`basis` where present, source from its `source_id` or the material's
`default_source_id`, and `condition` where the value carries one.

### 6. Flip the consumers

Point `load_database()` at the consolidated store. Run the 63 tests. They must
pass without edits. If a test needs changing, the migration changed behaviour
and the change needs justifying on its own terms, not as migration fallout.

### 7. Retire

Delete `data/materials/`, `scripts/materials_ingest/` and its staging schemas,
and the `_CANDIDATE_MATERIALS` tuple in `pycalcs/materials.py`.

## Independent of all of the above

`tools/ashby-chart/` ranks seven hardcoded materials. Point it at
`material_db`'s 60, which carry cost and environmental data it currently cannot
see. This removes one of the three stores, does not depend on any decision in
this plan, and is roughly an afternoon. Worth doing first whatever else is
decided.

## When to start

Step 1 is worth doing soon on its own merits. Steps 2 through 7 are a real
project, and the honest trigger is the first time a grade-level answer is
wanted in a selection chart, for example ranking 6061-T6 rather than
"aluminium alloy". Until then the two stores coexist without contradiction,
provided the boundary above is written down.

## Out of scope

- Pre-rendering the 530 redirect stubs in `tools/materials/` as real content.
  That is a separate opportunity, recorded in `tools/materials/README.md`.
- Merging `tools/materials-explorer/` and `tools/ashby-chart/`, or either with
  `tools/materials/`. Tool consolidation is a product question; this plan is
  only about the data behind them.
