# State versus observation condition matrix

Status: proposed v1 placement decisions for review checkpoint 1

This matrix decides where each condition concept in the current synthetic
corpus belongs in the v1 contract. It also covers the additional concepts named
in the approved M1 plan. The goal is consistent lookup identity, not a universal
model of manufacturing history.

## Core rule

A **named state** is a stable formulation or processing outcome that a user or
source deliberately names and looks up. A **condition** describes the specimen,
test, or reported result and may vary without changing that lookup identity.

V1 uses two separate containers:

- `state.fixed_attributes` for registered state-defining facts; and
- `observation.conditions` for registered specimen and test context.

`observation.test_method` and `observation.basis` are explicit observation
fields, not entries in the generic conditions object. Fixed attributes are not
copied into observations. A renderer derives effective context from both
containers.

## Placement decisions

| Concept | Current or proposed key | V1 placement | Decision and migration rule |
|---|---|---|---|
| Temper designation | `temper` | Named state only | A source-recognized temper such as T4, T6, or T651 is a lookup identity. Create one state and store the controlled temper token in `fixed_attributes`. Do not repeat it on observations. |
| Heat-treatment outcome | `heat_treatment` | Named state only | Stable named outcomes such as annealed, normalized, or solution-treated-and-aged define states. V1 records the outcome, not its complete furnace schedule. |
| Mechanical or work condition | `work_condition` | Named state only | Stable named outcomes such as cold-drawn, cold-worked, soft, or hard define states when the source treats them as distinct lookup forms. Reduction percentage may be part of the fixed state when it is the named condition. |
| Generic legacy state | current `material_state` | Retired; migrate to a named state and a specific fixed attribute | `material_state` currently hides several meanings. Map each value to `temper`, `heat_treatment`, `work_condition`, `formulation`, or `conditioning_state`. Unknown values require review; v1 has no catch-all state key. |
| Formulation | current `formulation` | Named state only | A deliberately named formulation such as unfilled is stable product identity below the material. If the formulation is itself independently sold or specified as the material, model it as the material instead of adding a redundant state. |
| Reinforcement kind | current `reinforcement` | Named state only | Glass-filled and carbon-filled formulations define named states when they are stable product variants. Use a controlled token such as `glass_fiber` or `carbon_fiber`; do not repeat it on each observation. |
| Nominal reinforcement mass fraction | current `fiber_mass_fraction_1` | Named state only | In the present polymer fixtures, 20% or 30% by mass is part of the named formulation. The key means nominal formulation fraction in v1, stored as a dimensionless fraction. A measured specimen fraction would require a separately defined observation key. |
| Measured reinforcement volume fraction | current `fiber_volume_fraction_1` | Observation only | The current laminate fixtures use this as specimen/test context. Keep the measured fraction on each observation because it may vary between specimens of the same layup. Do not reinterpret it as nominal formulation data. |
| Laminate layup class | current `layup` | Named state only | A source-named layup such as unidirectional, quasi-isotropic, or woven 0/90 is a stable lookup state. Ply-by-ply schedules and arbitrary stacking sequences are outside v1. |
| Conditioning label | `conditioning_state` | Named state only | A named outcome such as “dry as molded” or “conditioned” may define a state. The label must come from the source or fixture; the tool must not manufacture one from a measured moisture number. |
| Moisture content | current `moisture_content_1` | Observation only | Store the actual or source-reported specimen moisture as a dimensionless fraction on the observation. Nylon's named dry/conditioned states migrate to `conditioning_state`, while their numeric moisture moves to the observations. Wood moisture remains observation context and does not create several wood materials or states. |
| Product form | current `product_form` | Observation only | Sheet, plate, extrusion, bar, and molded specimen form affect reported evidence but normally do not create material identity. Legacy labels such as “T6 · plate” are reviewed so form is not silently fixed by the label; the form remains explicit on each observation. |
| Thickness | current `thickness_m` | Observation only | Thickness describes the product or specimen range to which an observation applies. Store it in canonical metres, including an explicitly one-sided range when that is what the source reports. |
| Cross-sectional area | current builder-only `cross_sectional_area_m2` | Observation only | Cross-sectional area is specimen or product context for one reported result. Store it in canonical square metres; it never creates a material or named state. |
| Loading or measurement orientation | current `orientation` | Observation only | L, LT, ST, radial, longitudinal, and in-plane directions can yield several valid observations for the same material or state. They must remain visible rather than creating pseudo-states or selecting one representative answer. |
| Test or service temperature | current `temperature_K` | Observation only | Store the temperature that applies to the reported result in kelvin. Temperature-dependent results are multiple observations in v1; curves and equations are deferred. Do not default a missing temperature to room temperature. |
| Test method | current `test_method` field | Observation field only | A method describes how one result was obtained. It never defines a material state. Preserve a registered method ID or the exact source-reported label; a state may have observations from several methods. |
| Statistical or reporting basis | current `basis` field | Observation field only | Typical, minimum, A-basis, B-basis, computed, and estimated describe the meaning of one reported result. Basis must not be inherited from a state, material, source, or category. |

This table covers every condition key currently present in the synthetic corpus:
`fiber_mass_fraction_1`, `fiber_volume_fraction_1`, `formulation`, `layup`,
`material_state`, `moisture_content_1`, `orientation`, `product_form`,
`reinforcement`, `temperature_K`, and `thickness_m`.

It also covers `cross_sectional_area_m2`, which exists only in the original
builder's registry, plus the more precise state keys required to replace the
legacy `material_state` catch-all.

## Decision procedure for new evidence

Apply these questions in order:

1. **Is this independently the material?** If a datasheet or specification
   identifies it as the thing being sold or specified, put it on the material,
   not in a state or observation condition.
2. **Does the source or its users deliberately name a stable outcome?** If yes,
   and it is one of the allowed state dimensions above, create a named state and
   store its registered fixed attributes once.
3. **Can it vary between reported results without changing that name?** If yes,
   it belongs to the observation.
4. **Is the wording ambiguous?** Do not infer a state to satisfy the UI. Preserve
   the source wording and locator, mark the candidate for review, and publish
   only after its placement is decided.
5. **Would the same fact appear in both containers?** Do not duplicate it. A key
   has one v1 placement. If two facts have different meanings—nominal
   reinforcement fraction versus measured specimen fraction—use distinct keys.

The number of observations does not decide the placement. Ten tests under T6
still use one T6 state, while one direction-specific result still keeps its
orientation on the observation.

## Effective context and conflicts

For display, effective context is the union of a state's fixed attributes and
an observation's conditions, followed by the observation's method and basis.
This is a derived view only.

- Canonical observations remain unchanged after assembly.
- A state and observation must refer to the same parent material.
- A state-only key appearing in `observation.conditions` is a validation error.
- An observation-only key appearing in `state.fixed_attributes` is a validation
  error.
- The retired `material_state` key is a migration error until it is mapped to a
  specific fixed attribute.
- Missing context stays missing. The compiler must not insert ambient
  temperature, isotropic orientation, typical basis, or another hidden default.
- Direct material observations do not flow into named states, and state
  observations do not flow to sibling states.

Examples from the synthetic fixture after migration:

- Synal AX70 T6 is a named state with `temper: T6`; plate, thickness, and LT
  orientation remain on its yield-strength observation.
- PeakDemo P100 30% carbon-filled is a named state with formulation,
  reinforcement, and nominal mass fraction fixed once.
- LamDemo CF-E1 UD is a named layup state; longitudinal orientation and measured
  fiber volume fraction remain on its observations.
- NylonDemo N6 conditioned is a named conditioning state; numeric moisture
  content is observation context.
- WoodDemo W1 remains one direct data-bearing material with moisture and grain
  direction on its observations.

## Explicitly deferred cases

The following require evidence from the later two-source audit or a future
contract version. They must not be squeezed into a v1 string field:

- complete heat-treatment schedules, dwell times, cooling rates, and prior
  thermal history;
- molding, extrusion, curing, sintering, aging, environmental exposure, and
  other time-dependent process histories;
- arbitrary ply-level stacking sequences, local laminate zones, textile
  architecture, and spatially varying fiber orientation;
- measured reinforcement mass fraction and nominal state-level fiber volume
  fraction until sources demonstrate the necessary distinct keys;
- humidity history, immersion duration, equilibrium criteria, and moisture
  profiles beyond a named conditioning state plus reported moisture content;
- detailed specimen geometry beyond registered dimensions such as thickness;
- strain rate, loading frequency, atmosphere, pressure, and other test
  conditions not yet exercised by the synthetic corpus;
- method clause, apparatus, specimen-preparation, and laboratory accreditation
  submodels beyond a method identifier or source-reported label;
- raw replicate distributions and statistical models beyond basis, uncertainty,
  and sample count;
- automatic equivalence or inheritance between similarly named states from
  different materials or sources; and
- curves, equations, tensors, and properties whose value changes continuously
  with state or condition.

Adding one of these later requires a registered key, an explicit placement
decision, positive and negative fixtures, and a contract-version review. It may
not enter canonical data as an ad hoc condition.
