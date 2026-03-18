# Ring Fit Tool

Date: 2026-03-12
Status: Proposed plan for critique before implementation
Primary reference: Shigley's Mechanical Engineering Design
Related existing assets:
- `tools/torque-transfer/`
- `tools/torque-transfer/interference_calc.py`
- `tools/torque-transfer/test_interference.py`

## 1. Purpose

Build a focused engineering tool for cylindrical press fits and shrink fits between a shaft and a hub/ring.

The tool should answer the questions engineers repeatedly need during machine design:

1. How much interface pressure does a given interference create?
2. Will the shaft or hub yield under the fit pressure?
3. How much torque and axial load can the fit transmit without slip?
4. What happens to the fit at operating temperature?
5. How much heating or cooling is needed for assembly?
6. How sensitive are pressure, stress, and capacity to interference range?

This should be a design-analysis and intuition tool, not just a torque calculator.

## 2. Positioning Relative to Existing Tool

The existing `tools/torque-transfer/` tool is a useful prototype, but it is not the right foundation for a production-quality interference-fit tool.

Key limitations in the current implementation:

- It uses a tool-local Python file instead of `pycalcs`, which violates repo architecture.
- It is framed mainly as torque transfer, not full fit design.
- It does not clearly separate nominal, minimum, and maximum interference cases.
- It does not make the modeling assumptions prominent enough.
- Its UI is older and does not follow the project template/design system.
- It exposes a "thin-wall hub" shortcut that should not remain unless explicitly justified and documented.

This new tool should supersede that workflow with:

- a `pycalcs` backend
- a modern advanced-template UI
- Shigley-based equations and documentation
- full pressure, stress, capacity, and thermal assembly analysis
- better handling of operating and tolerance scenarios

## 3. User Jobs

### Hurried engineer

- Enter shaft, hub, materials, and interference.
- Get contact pressure, torque capacity, and assembly temperature immediately.
- Check whether yielding or loss of fit is likely.

### Curious student

- See how Lamé cylinder theory produces contact pressure from interference.
- Understand why thick hubs behave differently from thin hubs.
- Explore how material stiffness, diameter ratio, and temperature alter fit behavior.

### Verifying expert

- Inspect the exact equations and assumptions.
- Verify whether the calculation is elastic-only and axisymmetric.
- Review min/nom/max interference results and identify the governing case.

## 4. Scope

### In Scope for v1

- Cylindrical interference fits only.
- Axisymmetric shaft and hub/ring geometry.
- Solid or hollow shaft.
- Solid hub/ring with defined outer diameter.
- Elastic press-fit / shrink-fit analysis using Shigley thick-cylinder relations.
- Reference-temperature and operating-temperature fit states.
- Torque and axial slip capacity from friction.
- Stress checks in both shaft and hub.
- Thermal assembly estimates:
  - heat hub only
  - cool shaft only
  - combined heating and cooling
- Interference sensitivity / range analysis.
- Material presets plus custom inputs.
- Clear warnings when assumptions are stretched or violated.

### Deferred / Out of Scope for v1

- Plastic press fits and post-yield redistribution.
- Tapered fits.
- Non-cylindrical or segmented hubs.
- Split clamps, shrink discs, keyed fits, splines, or serrations.
- Surface roughness flattening / embedding loss.
- Dynamic fretting wear or fatigue life from micro-slip.
- Centrifugal growth at speed.
- Differential radial temperature gradients through the hub wall.
- Coating thickness and coating compliance.
- ISO hole/shaft tolerance class lookup tables.
- FEA-grade local stress raisers from grooves, fillets, keyways, or reliefs.

## 5. Design Principle for v1

Keep the geometry narrow, but make the workflow complete.

This tool should do one joint type well:

> straight cylindrical shaft into thick-walled hub/ring, under elastic assumptions, with transparent thermal and slip-capacity analysis.

Avoid trying to absorb every fit/joint type in v1.

## 6. Core Model

### 6.1 Geometry Definitions

Required geometry inputs:

- `shaft_outer_diameter_mm` = fit diameter `d`
- `shaft_inner_diameter_mm` = `d_i` for hollow shaft, `0` for solid
- `hub_outer_diameter_mm` = `D`
- `fit_length_mm` = `L`
- interference input

Input modes for interference:

1. Default mode: direct diametral interference
   - `interference_nominal_mm`

2. Advanced mode: interference range
   - `interference_min_mm`
   - `interference_nominal_mm`
   - `interference_max_mm`

Range mode is mandatory in v1 because it captures one of the most common real design questions: whether the least-interference condition still carries load and whether the greatest-interference condition overstresses the parts.

Derived values:

- radial interference `delta_r = delta_d / 2`
- diameter ratios:
  - `D / d`
  - `d_i / d`
- contact area `A = pi d L`

### 6.2 Material Properties

Each component needs:

- Young's modulus `E`
- Poisson's ratio `nu`
- coefficient of thermal expansion `alpha`
- yield strength `S_y`

Use material presets for:

- carbon steel
- stainless steel
- aluminum alloy
- cast iron
- bronze
- brass
- copper

Allow custom entries for both shaft and hub.

The preset database should live in a `pycalcs` module, not in the HTML.

### 6.3 Fit States

The tool should evaluate at least three physical states:

1. Reference state
- interference and temperature as specified at assembly reference temperature

2. Operating state
- interference adjusted for differential thermal expansion

3. Assembly state
- additional temporary clearance required for slip assembly

Evaluate each state for:

- minimum interference
- nominal interference
- maximum interference

### 6.4 Pressure Model

Use the Shigley elastic interference-fit relations for cylinders.

Implementation requirement:

- choose one consistent Shigley formulation for diametral interference
- cite the exact edition and equation numbers in the docstring and README when coding begins
- do not mix textbook forms from memory or from multiple sources

The backend should compute interface pressure from diametral interference using shaft and hub radial compliance contributions.

Conceptually:

`delta_d = p d (C_h + C_s)`

Where:

- `C_h` is hub compliance from thick-cylinder expansion under internal pressure
- `C_s` is shaft compliance from solid or hollow cylinder contraction under external pressure

For solid shafts and thick hubs, this should reduce to the standard Shigley press-fit form.

The exact algebraic form must be lifted from the chosen Shigley edition and kept as the single source of truth in code comments and docstrings.

### 6.5 Operating Temperature Model

Operating interference should account for differential free thermal expansion:

`delta_d,op = delta_d,ref - d (alpha_h - alpha_s) DeltaT`

Where:

- `DeltaT = T_op - T_ref`

Rules:

- if `delta_d,op <= 0`, the fit has lost full interference and contact pressure becomes `0`
- the UI must show this as a physically meaningful state, not as a generic error

This operating-state check is a major value driver for the tool because aluminum-on-steel and similar combinations can lose fit dramatically with heat.

### 6.6 Stress Model

Use Lamé thick-cylinder stresses at the fit interface for both members.

Hub at bore:

- radial stress `sigma_r = -p`
- hoop stress from thick-cylinder relation at the bore

Shaft outer surface:

- solid shaft: compressive radial and hoop stresses of magnitude `p`
- hollow shaft: use the thick-cylinder relation at the outer radius

For reporting, compute:

- radial stress
- hoop stress
- von Mises equivalent stress
- yield safety factor

Use a plane-stress distortion-energy form unless review determines the axial state must be modeled differently.

This is an explicit review target because long fits can blur the plane-stress / plane-strain simplification.

### 6.7 Slip Capacity Model

Assume full uniform interface pressure over the contact area.

Compute:

- normal force `N = p pi d L`
- axial slip capacity `F_max = mu N`
- torque capacity `T_max = mu N (d / 2)`

Allow user entry for:

- friction coefficient `mu`
- optional applied torque
- optional applied axial force
- optional combined service factor / required slip safety factor

Outputs:

- torque capacity
- axial capacity
- torque slip safety factor
- axial slip safety factor

Combined torque-plus-axial friction utilization may be added later. For v1, keep torque and axial comparisons separate unless the review strongly pushes for a combined interaction check.

### 6.8 Assembly Temperature Model

The tool should estimate three assembly strategies:

1. Heat hub only
2. Cool shaft only
3. Combined heat hub + cool shaft

Inputs:

- assembly clearance target
- reference assembly temperature
- maximum allowable hub heating temperature (optional warning threshold)
- minimum allowable shaft cooling temperature (optional warning threshold)

Conceptually:

Required temporary diameter change must exceed:

`interference + assembly_clearance`

Then:

- hub heating only uses `alpha_h`
- shaft cooling only uses `alpha_s`
- combined mode splits required differential expansion between both parts

The tool should not imply metallurgical safety from the temperature estimate alone. It should explicitly note that allowable heating depends on material temper, coating, lubricant, and handling process.

### 6.9 Interference Sensitivity / Range Analysis

This is the exploratory core of the tool and is required in v1.

The backend should generate data for:

- pressure vs interference
- torque capacity vs interference
- hub and shaft von Mises stress vs interference
- assembly temperature requirement vs interference

If min/max interference is entered, shade the feasible band on these plots.

This turns the tool from a one-off calculator into a design-space explorer.

## 7. Status and Decision Logic

The tool should report results without pretending to be code-compliant design approval.

It should evaluate at least these outcome checks:

1. Fit retention at operating temperature
- retained
- marginal
- lost

2. Yield margin
- both parts above required safety factor
- one part marginal
- one part overstressed

3. Slip capacity
- torque margin
- axial margin

4. Assembly practicality
- heating/cooling within user thresholds
- unrealistic or process-risky temperatures required

Overall status proposal:

- `acceptable`
- `marginal`
- `unacceptable`

But the UI should still show which mechanism governs:

- hub yield
- shaft yield
- torque slip
- axial slip
- thermal fit loss
- assembly impracticality

## 8. Backend Architecture

### 8.1 Reuse / Refactor Strategy

Do not extend `tools/torque-transfer/interference_calc.py` in place.

Preferred approach:

- create `pycalcs/interference_fits.py`
- migrate and clean any reusable logic from the local tool
- expose import-safe functions for pressure, stress, capacity, thermal change, and sweeps
- add docstrings in the normal repo format

This also resolves the repo-level architectural issue of duplicated tool-local calculation code.

The intent is not to keep both tools indefinitely. Once the new tool reaches feature parity for the valid use cases of the legacy calculator and passes verification, the legacy `tools/torque-transfer/` implementation should be removed rather than maintained in parallel.

### 8.2 Proposed Public Functions

Possible function breakdown:

```python
def get_interference_fit_material_presets() -> dict[str, dict[str, float]]:
    ...

def analyze_interference_fit(
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    shaft_inner_diameter_mm: float = 0.0,
    interference_nominal_mm: float = 0.03,
    interference_min_mm: float | None = None,
    interference_max_mm: float | None = None,
    shaft_material: str = "steel",
    hub_material: str = "steel",
    shaft_youngs_modulus_mpa: float = 200000.0,
    shaft_poisson_ratio: float = 0.30,
    shaft_yield_strength_mpa: float = 450.0,
    shaft_thermal_expansion_e6_per_c: float = 12.0,
    hub_youngs_modulus_mpa: float = 200000.0,
    hub_poisson_ratio: float = 0.30,
    hub_yield_strength_mpa: float = 350.0,
    hub_thermal_expansion_e6_per_c: float = 12.0,
    friction_coefficient: float = 0.15,
    reference_temperature_c: float = 20.0,
    operating_temperature_c: float = 20.0,
    assembly_clearance_mm: float = 0.01,
    applied_torque_nm: float = 0.0,
    applied_axial_force_n: float = 0.0,
    required_slip_sf: float = 1.5,
    required_yield_sf: float = 1.2,
    sweep_min_interference_mm: float = 0.0,
    sweep_max_interference_mm: float = 0.08,
    n_sweep_points: int = 81,
) -> dict[str, Any]:
    ...
```

Exact naming can change, but the function should support:

- one nominal design point
- optional min/max fit band
- required output structure for charts and checks

### 8.3 Return Shape

Top-level structure should include:

```python
{
    "reference_case": {...},
    "operating_case": {...},
    "minimum_case": {...},
    "maximum_case": {...},
    "assembly": {...},
    "sweep_data": {...},
    "status": "acceptable" | "marginal" | "unacceptable",
    "governing_mode": "...",
    "warnings": [...],
    "recommendations": [...],
    "subst_interface_pressure_mpa": "...",
    "subst_operating_interference_mm": "...",
    "subst_torque_capacity_nm": "...",
    "subst_hub_von_mises_mpa": "...",
}
```

Case blocks should report:

- interference
- pressure
- hub radial stress
- hub hoop stress
- hub von Mises
- shaft radial stress
- shaft hoop stress
- shaft von Mises
- hub yield safety factor
- shaft yield safety factor
- torque capacity
- axial capacity
- torque slip safety factor
- axial slip safety factor

### 8.4 Plot Data Requirements

The backend should return plot-ready arrays for:

1. `pressure_vs_interference`
2. `torque_vs_interference`
3. `axial_capacity_vs_interference`
4. `hub_stress_vs_interference`
5. `shaft_stress_vs_interference`
6. `operating_pressure_vs_temperature`

The operating-temperature plot is especially valuable for mixed-material fits.

## 9. Frontend Plan

### 9.1 Template Choice

Use `tools/example_tool_advanced/index.html`.

Reason:

- multiple input sections
- multiple result states
- charts
- status assessment
- derivation panels
- material presets
- clear assumptions/background tab

### 9.2 Tool Layout

#### Left column: inputs

Sections:

1. Geometry
- shaft OD
- shaft ID
- hub OD
- fit length

2. Fit Definition
- interference mode
- nominal or min/nom/max interference

3. Materials
- shaft material preset / custom
- hub material preset / custom

4. Service Conditions
- friction coefficient
- applied torque
- applied axial force
- reference temperature
- operating temperature

5. Assembly
- assembly clearance
- optional practical temperature limits

6. Requirements
- required slip safety factor
- required yield safety factor

#### Right column: outputs

1. Summary banner
- governing mode
- retained/lost fit state
- key warning if min or operating case governs

2. Primary result cards
- reference pressure
- operating pressure
- torque capacity
- axial capacity
- required hub heat
- required shaft cooling

3. Case comparison table
- minimum
- nominal
- maximum
- reference vs operating columns where applicable

4. Chart tabs
- pressure / capacity sweep
- stress sweep
- temperature effect

5. Derivation panels
- pressure
- slip capacity
- thermal assembly
- stress and safety factor

6. Background tab
- assumptions, equations, examples, references

### 9.3 Default Inputs

Defaults should show a realistic same-material steel fit with moderate interference.

Suggested defaults:

- shaft OD: `50 mm`
- shaft ID: `0 mm`
- hub OD: `100 mm`
- fit length: `75 mm`
- interference nominal: `0.05 mm`
- friction coefficient: `0.15`
- reference temperature: `20 C`
- operating temperature: `20 C`
- assembly clearance: `0.01 mm`
- both materials: steel

These defaults are also close to the existing prototype regression case, which makes comparison and migration easier.

### 9.4 Charts

#### Pressure / capacity sweep

Primary exploratory chart.

Show:

- pressure vs interference
- torque capacity vs interference
- optional shaded min/max interference band

#### Stress sweep

Show:

- hub von Mises vs interference
- shaft von Mises vs interference
- yield threshold markers

#### Temperature effect chart

Show:

- operating interference vs temperature
- operating pressure vs temperature
- mark the zero-pressure temperature if fit loss occurs

## 10. Background / Educational Content

The Background tab should include:

1. What a press fit / shrink fit is
2. Why shaft and hub stiffness both matter
3. The difference between interference, pressure, and capacity
4. Why mixed materials can lose interference with temperature
5. Why thicker hubs reduce compliance and increase pressure
6. Why high friction assumptions can be misleading
7. Why keyways, chamfers, grooves, and roughness can invalidate the ideal model
8. When to switch from calculator to test/FEA/code-specific review

Primary references:

- Shigley's Mechanical Engineering Design, interference-fit / press-fit treatment

Secondary cross-check references if needed during implementation:

- Roark's Formulas for Stress and Strain
- machine design references on thick cylinders and shrink fits

Important note:

- The implementation should cite exact Shigley edition and equation numbers once the team agrees on the edition in use. Do not hard-code equation numbers in the plan without confirming the edition.

## 11. Validation and Error Handling

Backend validation must reject or flag:

- nonpositive shaft OD, hub OD, or fit length
- hub OD `<=` shaft OD
- shaft ID `< 0` or `>=` shaft OD
- negative friction coefficient
- Poisson ratio outside physical range
- nonpositive modulus
- nonpositive yield strength when safety-factor checks are requested
- negative assembly clearance
- `interference_min > interference_nominal`
- `interference_nominal > interference_max`

Method/state-specific handling:

- if operating interference becomes zero or negative, return a valid "fit lost" state
- if interference is zero, return zero pressure and zero slip capacity, not an error
- if assembly temperatures are unavailable due to missing `alpha`, return explicit null plus warning

The UI should distinguish:

- invalid input
- fit lost at operating temperature
- overstressed but still retained fit
- retained fit but insufficient slip capacity

## 12. Testing Plan

### 12.1 Backend Unit Tests

Create a dedicated `tests/test_interference_fits.py`.

Include:

1. Same-material solid shaft / thick hub nominal case
- pressure should match the known baseline close to the current prototype case

2. Hollow shaft case
- pressure lower than equivalent solid-shaft case

3. Hub stress case
- verify Lamé bore stress and von Mises calculation

4. Torque and axial capacity case
- confirm capacity equations against hand calculation

5. Operating temperature mixed-material case
- aluminum hub on steel shaft should lose pressure as temperature rises

6. Operating temperature same-material case
- equal expansion coefficients should preserve interference approximately

7. Lost-fit case
- sufficiently high operating temperature should drive pressure to zero

8. Range-case ordering
- max interference should produce higher pressure, higher stress, and higher slip capacity than min interference

9. Validation errors
- impossible geometry and negative material properties must raise

### 12.2 Regression / Reference Tests

Add at least one textbook-style reference case once the exact Shigley example and edition are confirmed.

If no clean Shigley worked example is available in the chosen edition, keep:

- one hand-derived same-material sanity case
- one mixed-material thermal case

### 12.3 Manual Browser Checks

- default case loads and calculates cleanly
- min/nom/max band updates all tables and charts correctly
- warnings appear for fit loss and high stress
- dark mode chart contrast is readable
- derivation panels show substituted equations with units

## 13. Deliverables

Planned files:

- `plans/2026-03-12_ring_fit_press_shrink_fit_tool.md`
- `pycalcs/interference_fits.py`
- `tests/test_interference_fits.py`
- `tools/ring-fit/index.html`
- `tools/ring-fit/README.md`
- `catalog.json` entry

Required follow-up cleanup after rollout verification:

- retire and delete `tools/torque-transfer/`
- remove duplicated local Python logic rather than maintaining two interference-fit calculators
- update any catalog/navigation references so the new tool is the only supported workflow

## 13.1 Legacy Tool Migration Checklist

The old `tools/torque-transfer/` tool should be deleted after the following are true:

1. Functional parity for supported use cases
- the new tool reproduces the legacy calculator's core outputs for straight cylindrical elastic interference fits:
  - interface pressure
  - hub and shaft stress
  - torque capacity
  - axial capacity
  - assembly heating/cooling estimates

2. Backend migration is complete
- all reusable calculation logic has been moved into `pycalcs/interference_fits.py`
- no production interference-fit logic remains only in `tools/torque-transfer/interference_calc.py`

3. Regression coverage exists
- new automated tests cover the legacy baseline cases currently represented in `tools/torque-transfer/test_interference.py`
- same-material and mixed-material thermal cases pass in the new test suite

4. UI replacement is complete
- the new tool exposes all valid legacy workflows in a clearer form
- catalog and navigation point only to the new tool

5. Verification pass is complete
- manual browser verification confirms the new tool handles the legacy default case correctly
- the new tool is reviewed for calculation transparency, result consistency, and warning behavior

6. Deletion cleanup is complete
- remove `tools/torque-transfer/index.html`
- remove `tools/torque-transfer/interference_calc.py`
- remove `tools/torque-transfer/test_interference.py`
- remove or update any references in `catalog.json`, README text, or internal links

The migration intent is explicit:

- there should be one supported interference-fit calculator in the repo
- the old torque-transfer tool should not survive as a second, partially overlapping implementation

## 14. Recommended Implementation Sequence

1. Confirm equation source
- lock the Shigley edition to be cited
- identify exact interference-fit equations to implement

2. Backend first
- build pressure and stress functions
- add thermal and slip-capacity functions
- add mandatory min/nom/max wrapper
- add tests

3. Tool scaffold
- copy advanced template
- wire form inputs to backend
- render summary cards and case table

4. Add charts
- interference sweep
- stress sweep
- temperature effect

5. Add derivations and background content

6. Final cleanup
- README
- catalog registration
- remove `tools/torque-transfer/` after the new tool is verified to cover its supported use cases

## 15. Known Risks and Review Targets

These are the points other agents should challenge before implementation:

1. Plane stress vs plane strain
- Is plane stress acceptable for the intended tool, or should axial restraint be an explicit option?

2. Mandatory range mode in v1
- The plan requires min/nom/max interference. Review should focus on the best UI and result presentation, not whether the feature exists.

3. Combined slip interaction
- Should v1 include a combined axial-plus-torque friction interaction check, or keep them independent?

4. Thin-wall approximation
- Should the plan forbid it entirely in v1, or retain it as an expert-only comparison mode?

5. Thermal model simplicity
- Is uniform bulk temperature sufficient, or should even v1 distinguish assembly temperature from steady operating temperature more carefully?

6. Status banner
- Should there be a single overall status, or should the tool stay more neutral and simply report governing modes?

7. Legacy tool removal
- Is there any remaining valid workflow in `tools/torque-transfer/` that must be migrated before deletion, or can the old tool be removed immediately after parity verification?

8. Tool naming
- Is "Ring Fit Tool" clear enough, or should the user-facing title be "Press-Fit / Shrink-Fit Calculator" with "ring fit" in the subtitle?

## 16. Acceptance Criteria

The plan is ready for implementation review once the team agrees on:

1. The exact Shigley equation set and edition to use.
2. The exact v1 behavior and presentation of mandatory min/nom/max interference analysis.
3. Whether combined slip interaction is in or out for v1.
4. Whether plane stress is acceptable as the base stress assumption.
5. The migration criteria for deleting `tools/torque-transfer/` once the new tool is implemented and verified.
