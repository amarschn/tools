# Schema lab review checkpoint 1

Status: reviewed and closed 2026-08-22. Decisions 2 and 3 below were modified at
the gate; see [`schema-lab-checkpoint-1-decisions.md`](schema-lab-checkpoint-1-decisions.md)
for what was actually adopted. This document is retained as the question that
was asked, not as the answer.

## Short version

The proposed frontend-loadable database has four main layers:

```text
category
  -> material
       -> named state
            -> measurement + conditions + source
```

For the representative synthetic example:

```text
Aluminium-like alloys
  -> Synal AX70
       -> T6
            -> ultimate tensile strength: 530-560 MPa
               plate, LT direction, 25-50 mm, 293.15 K
               Synthetic property sheet, page 8, table 4
```

The database stores the normalized entities above. Later phases will compile
them into the small search file and lazy material/property files loaded by the
frontend.

## Proposed decisions

### 1. Categories are not materials

`Engineering plastics`, `metals`, and similar categories are navigation. They
can be empty, and they never own measurements. A category range is calculated
from its concrete members.

### 2. A named state is a recognizable lookup identity

T6 temper, a named glass-filled formulation, or a defined laminate layup may be
a state. Test temperature, specimen direction, thickness, and method remain on
individual measurements.

### 3. Product form is measurement context in v1

> **Modified at the gate.** Product form remains stored on observations as
> described here, but it is now also a *navigable* drill-down level: `AX70 T6`
> reports a range across forms and the user downselects to `AX70 T6 plate`. See
> the recorded decisions document.

Plate, extrusion, sheet, and molded form normally remain on an observation.
Thus `AX70 T6 plate` becomes the `T6` state with `product_form: plate` on its
measurements, rather than a separate plate state. We can revisit this if real
sources consistently treat form as part of the lookup identity.

### 4. Values preserve what the source said

> **Modified at the gate.** Both forms are still stored, but the canonical form
> is what the UI displays, converted into a user-selected unit. The reported
> form is retained for audit and significant figures rather than for display.
> See the recorded decisions document.

A result can be a point, reported interval, lower bound, upper bound, or an
explicit unavailable/not-applicable assertion. Numeric results retain both the
source's number/unit and the converted canonical number/unit. Uncertainty is a
separate field.

### 5. Measurements never inherit silently

A value attached directly to AX70 does not automatically apply to AX70-T6. A
T6 value does not automatically apply to T651. Reuse requires an explicit,
source-traceable observation.

### 6. Search terms and engineering meanings stay separate

`strength` is a group containing several exact properties. It never silently
means tensile strength. The proposed canonical IDs make the tensile properties
explicit:

- `yield_strength` becomes `tensile_yield_strength`;
- `tensile_strength` becomes `ultimate_tensile_strength`; and
- the old names remain compatibility/search mappings rather than duplicate
  properties.

Designations use a structured pair such as:

```json
{"system_id": "synthetic_fixture", "value": "AX70"}
```

This prevents a designation's issuing system from being lost. The current
unqualified synthetic designations use the explicit `synthetic_fixture` system;
the migration will not guess real standards from their spelling.

## State versus measurement context

The complete proposed matrix is in
[`state-condition-matrix.md`](state-condition-matrix.md). In compact form:

| Stored once on a named state | Stored on each applicable observation |
|---|---|
| temper and heat-treatment outcome | temperature |
| mechanical/work condition | product form and thickness |
| named formulation and reinforcement | cross-sectional area |
| nominal reinforcement mass fraction | loading/measurement orientation |
| named laminate layup | measured moisture content |
| named conditioning state | measured reinforcement volume fraction |
|  | test method and reporting/statistical basis |

The old catch-all `material_state` field is retired. Each value must be mapped
to a precise state attribute or reviewed.

## What is already frozen and executable

- The starting corpus has 27 taxa, 32 materials, 38 states, 360 observations,
  13 exact properties, and 5 property groups.
- A 21-query executable matrix now freezes exact IDs, aliases, near-collisions,
  typo behavior, category/property intent, empty categories, and rejected
  comparison intent.
- Bare `strength` now explicitly routes to precise-property clarification.
- Precise `tensile strength` explicitly routes to the property overview.
- Search results remain capped below the accepted maximum of 50.
- Existing Prototype 05 visible behavior is unchanged; the resolver now exposes
  the selected behavior without requiring a page-specific interpretation.

The baseline inventory is in
[`schema-lab-m0-baseline.md`](schema-lab-m0-baseline.md).

## Representative files

- [`canonical-example.json`](../fixtures/schema-lab/checkpoint-1/canonical-example.json)
  contains one material, one state, two source-backed observations, registered
  properties/conditions, and one synthetic source.
- [`invalid-examples.json`](../fixtures/schema-lab/checkpoint-1/invalid-examples.json)
  shows five cases the future validator must reject.
- [`materials-domain-glossary.md`](materials-domain-glossary.md) defines the
  detailed terms without broadening v1 into a universal ontology.

## Approval questions

Checkpoint 1 asks whether to proceed with these four choices:

1. taxonomy -> material -> named state -> observation as the database model;
2. the state-versus-observation placement summarized above, especially product
   form and moisture as observation context;
3. reported plus canonical result forms, with uncertainty separate; and
4. exact property IDs and structured `system_id`/`value` designations.

Approval moves the work to Phase 2: formal schemas, semantic validation, lossless
migration of the full synthetic corpus, adversarial fixtures, and executable
record/projection goldens. It still does not start real-data collection or a
backend.
