# Fatigue Mean-Stress Explorer

Date: 2026-03-12
Status: Proposed plan for critique before implementation
Related existing assets:
- `tools/fatigue-life-estimator/`
- `pycalcs/fatigue.py`
- `tests/test_fatigue.py`

## 1. Purpose

Build an exploratory fatigue tool focused on one question:

> How does mean stress change allowable alternating stress and predicted life, and how much do Goodman, Gerber, and Soderberg disagree for the same loading point?

The tool is intended to help users build intuition, compare mean-stress correction methods side by side, and understand when method choice materially changes the answer.

This is not meant to replace the existing `fatigue-life-estimator`. That tool is a single-scenario design calculator. This new tool should be comparison-first, visualization-first, and explicitly educational.

## 2. Positioning Relative to Existing Tool

The existing [fatigue-life-estimator](../tools/fatigue-life-estimator/README.md) already computes life for one chosen method and shows a mean-stress plot. The new tool should differ in these ways:

- It compares multiple correction methods at once instead of forcing one method selection up front.
- It centers the Haigh/Goodman diagram as the primary interface, not a secondary chart.
- It emphasizes sensitivity and method spread, not just a single life prediction.
- It is intentionally exploratory and should avoid overconfident pass/fail messaging.

## 3. User Jobs

### Hurried engineer

- Enter a stress state and material.
- See whether Goodman, Gerber, and Soderberg materially disagree.
- Identify the governing conservative method quickly.

### Curious student

- Understand the relationship between `sigma_max`, `sigma_min`, `sigma_m`, `sigma_a`, and `R`.
- See how a point moves on the mean-stress diagram.
- Observe how positive tensile mean stress reduces fatigue margin.

### Verifying expert

- Inspect equations and assumptions.
- Verify the plotted envelopes are based on either endurance limit or target-life stress.
- Confirm where the tool is and is not valid.

## 4. Scope

### In Scope for v1

- Uniaxial, constant-amplitude, stress-life exploration.
- Metallic materials only in v1.
- Material presets plus custom material entry.
- Side-by-side comparison of:
  - No mean-stress correction
  - Goodman
  - Gerber
  - Soderberg
- Haigh / mean-stress interaction diagram with all enabled methods overlaid.
- Life comparison table for all enabled methods.
- Sensitivity sweep showing how mean stress changes life or allowable alternating stress.
- Derived stress-state metrics:
  - `sigma_max`
  - `sigma_min`
  - `sigma_m`
  - `sigma_a`
  - stress ratio `R`
- Explicit warnings when the input approaches or exceeds the valid range of a method.

### Deferred / Out of Scope for v1

- Polymers and viscoelastic fatigue behavior.
- Variable-amplitude loading, Miner damage, rainflow counting.
- Strain-life / Coffin-Manson low-cycle fatigue.
- Multiaxial fatigue.
- Weld-specific fatigue categories.
- Notch sensitivity and local stress concentration modeling.
- Residual stress relaxation and shot peening benefit.
- Smith-Watson-Topper, Walker, Morrow, Crossland, Dang Van, or other advanced criteria.

## 5. Design Principle for v1

Keep the core model narrow and classical. The fastest way to make this tool confusing or untrustworthy is to combine mean-stress comparison, polymer derating, notches, and spectrum loading into one interface.

v1 should answer one clean question well.

## 6. Core Model

### 6.1 Stress State Definitions

Users should be able to specify the operating point in one primary way:

- Default input mode: `sigma_a` and `sigma_m`

Derived values:

- `sigma_max = sigma_m + sigma_a`
- `sigma_min = sigma_m - sigma_a`
- `R = sigma_min / sigma_max` when `sigma_max != 0`

Advanced input modes may be added later, but v1 should keep the default interaction centered on the Haigh diagram axes.

### 6.2 Material Properties

Use the existing fatigue material preset structure in `pycalcs/fatigue.py` as the single source of truth where practical.

v1 material support:

- Metal presets from `pycalcs/fatigue.py`
- Custom metal entry with:
  - `ultimate_strength_mpa`
  - `yield_strength_mpa`
  - `endurance_limit_ratio`
  - `surface_factor`
  - `size_factor`
  - `reliability_factor`
  - `fatigue_strength_coeff_ratio`
  - `fatigue_strength_exponent`

Derived material values:

- `S_e = endurance_limit_ratio * S_ut * k_surface * k_size * k_reliability`
- `sigma_f' = fatigue_strength_coeff_ratio * S_ut`

### 6.3 Mean-Stress Methods to Compare

The tool should compare these equations explicitly:

1. No correction

`sigma_a,eq = sigma_a`

2. Goodman

`sigma_a,eq = sigma_a / (1 - sigma_m / S_ut)`

3. Gerber

`sigma_a,eq = sigma_a / (1 - (sigma_m / S_ut)^2)`

4. Soderberg

`sigma_a,eq = sigma_a / (1 - sigma_m / S_y)`

These methods should be shown as overlays on the same plot and as separate rows in the comparison table.

### 6.4 Allowable Alternating Stress Envelopes

For a chosen reference alternating stress `sigma_ref`, the tool should compute allowable alternating stress as a function of mean stress:

- Goodman: `sigma_a,allow = sigma_ref * (1 - sigma_m / S_ut)`
- Gerber: `sigma_a,allow = sigma_ref * (1 - (sigma_m / S_ut)^2)`
- Soderberg: `sigma_a,allow = sigma_ref * (1 - sigma_m / S_y)`
- None: `sigma_a,allow = sigma_ref`

The reference stress basis should be user-selectable:

- `target_life`
- `endurance_limit`

Rules:

- `target_life` basis is always available.
- `endurance_limit` basis is available only when `S_e > 0`.
- Default basis for v1: `target_life`, because it works for all supported metal presets and keeps the comparison tied to a stated life target instead of silently assuming infinite-life design.

### 6.5 Life Model

Use the same Basquin-style life model already implemented in `pycalcs/fatigue.py`:

`sigma_a,eq = sigma_f' * (2N)^b`

Rearranged:

`N = 0.5 * (sigma_a,eq / sigma_f')^(1 / b)`

If the material supports an endurance limit and `sigma_a,eq <= S_e`, return `N = inf`.

The plan should preserve the current repo behavior for the fatigue life estimator so the explorer and calculator remain internally consistent.

### 6.6 Method Comparison Outputs

For each method, compute:

- `equivalent_stress_mpa`
- `estimated_life_cycles`
- `estimated_life_hours`
- `fatigue_safety_factor`
- `yield_safety_factor`
- `allowable_alternating_stress_mpa`
- `pass_target_life`
- `validity_state`
- `warning_messages`

The tool should also compute:

- `most_conservative_method`
- `least_conservative_method`
- `life_spread_ratio`
- `equivalent_stress_spread_pct`

These spread metrics are part of what makes the tool exploratory rather than just another fatigue calculator.

### 6.7 Compressive Mean Stress Handling

This is an area the review should challenge.

Proposed v1 behavior:

- Allow compressive mean stress input.
- Plot the operating point in the compressive region.
- Use the direct equation forms for comparison curves.
- Display a persistent warning when `sigma_m < 0`:
  - "Compressive mean stress benefit is model-sensitive and may be over-predicted by classical correction formulas. Do not claim fatigue credit without material-specific validation."

Reason for this choice:

- It preserves the educational value of the diagram.
- It avoids silently clipping the model without telling the user.
- It clearly marks the regime as cautionary rather than authoritative.

### 6.8 Validity and Failure Rules

The backend should reject or flag these cases:

- `sigma_a <= 0`
- `S_ut <= 0`
- `S_y <= 0`
- `S_y > S_ut` should trigger a warning or explicit validation review path
- `fatigue_strength_exponent >= 0`
- denominator `<= 0` for the selected method
- `sigma_max` above static strength should trigger warning and degrade confidence
- `target_life_cycles <= 0`

Method-specific validity:

- Goodman becomes invalid when `1 - sigma_m / S_ut <= 0`
- Gerber becomes invalid when `1 - (sigma_m / S_ut)^2 <= 0`
- Soderberg becomes invalid when `1 - sigma_m / S_y <= 0`

The UI should not collapse all invalid cases into a generic error. It should indicate which method failed and why.

## 7. Backend Architecture

### 7.1 Reuse Strategy

Do not create a new fatigue equations source unless absolutely necessary.

Preferred approach:

- Keep shared fatigue logic in `pycalcs/fatigue.py`
- Add a new public wrapper for multi-method comparison
- Reuse `estimate_fatigue_life(...)` internally for each method
- Reuse existing preset lookup functions
- Reuse or lightly extend the existing mean-stress curve generators

This preserves a single source of truth and minimizes divergence from the existing fatigue tool.

### 7.2 Proposed Public Function

Add a new function in `pycalcs/fatigue.py`, tentatively:

```python
def explore_mean_stress_methods(
    alternating_stress_mpa: float,
    mean_stress_mpa: float,
    ultimate_strength_mpa: float,
    yield_strength_mpa: float,
    endurance_limit_ratio: float = 0.5,
    surface_factor: float = 1.0,
    size_factor: float = 1.0,
    reliability_factor: float = 1.0,
    fatigue_strength_coeff_ratio: float = 1.5,
    fatigue_strength_exponent: float = -0.09,
    target_life_cycles: float = 1e6,
    load_frequency_hz: float = 2.0,
    material_family: str = "metal",
    material_preset: str = "steel_1045",
    reference_basis: str = "target_life",
    enabled_methods: str = "none,goodman,gerber,soderberg",
    sweep_variable: str = "mean_stress",
    sweep_min_mpa: float = -100.0,
    sweep_max_mpa: float = 400.0,
    n_sweep_points: int = 81,
) -> dict[str, Any]:
```

The exact signature can change, but the behavior should remain:

- one operating point in
- all method comparisons out
- plot-ready arrays included

### 7.3 Backend Return Shape

Top-level return structure should include:

```python
{
    "sigma_max_mpa": ...,
    "sigma_min_mpa": ...,
    "alternating_stress_mpa": ...,
    "mean_stress_mpa": ...,
    "stress_ratio": ...,
    "ultimate_strength_mpa": ...,
    "yield_strength_mpa": ...,
    "endurance_limit_mpa": ...,
    "fatigue_strength_coeff_mpa": ...,
    "reference_basis": ...,
    "reference_stress_mpa": ...,
    "comparison_table": [...],
    "haigh_diagram_data": {...},
    "sn_plot_data": {...},
    "sweep_data": {...},
    "most_conservative_method": ...,
    "least_conservative_method": ...,
    "life_spread_ratio": ...,
    "warnings": [...],
    "subst_sigma_max_mpa": ...,
    "subst_stress_ratio": ...,
    "subst_reference_stress_mpa": ...,
}
```

Each `comparison_table` row should include:

```python
{
    "method": "goodman",
    "equivalent_stress_mpa": ...,
    "estimated_life_cycles": ...,
    "fatigue_safety_factor": ...,
    "yield_safety_factor": ...,
    "allowable_alternating_stress_mpa": ...,
    "pass_target_life": True,
    "validity_state": "valid" | "warning" | "invalid",
    "warnings": [...],
    "subst_equivalent_stress_mpa": ...,
    "subst_estimated_life_cycles": ...,
}
```

### 7.4 Plot Data Requirements

The backend should return plot-ready data so the frontend remains mostly presentational.

Required plot datasets:

1. `haigh_diagram_data`
- mean-stress array
- per-method allowable alternating arrays
- yield line
- operating point
- axis limits

2. `sn_plot_data`
- base S-N curve
- one operating point per method using `sigma_a,eq`
- optional target-life marker
- optional endurance-limit line

3. `sweep_data`
- x array
- one y array per method
- selectable metric:
  - `estimated_life_cycles`
  - `allowable_alternating_stress_mpa`
  - `equivalent_stress_mpa`

## 8. Frontend Plan

### 8.1 Template Choice

Use `tools/example_tool_advanced/index.html` as the base template.

Reason:

- 6+ meaningful inputs
- multiple charts
- advanced settings and theme support
- educational background tab
- comparison table plus derivation panels

### 8.2 Tool Layout

#### Left column: inputs

Sections:

1. Operating Point
- input mode label
- `alternating_stress_mpa`
- `mean_stress_mpa`
- derived `sigma_max`, `sigma_min`, `R` shown live after calculation

2. Material
- material preset dropdown
- custom material toggle
- strengths and fatigue properties

3. Reference Basis
- target life cycles
- reference basis selector

4. Advanced Factors
- endurance limit ratio
- surface factor
- size factor
- reliability factor
- load frequency for hours conversion

5. Sweep Controls
- sweep metric
- sweep min
- sweep max
- number of points

#### Right column: outputs

1. Neutral summary banner
- no single green/red "safe" headline by default
- focus on "method spread" and "governing method"

2. Comparison cards / table
- one row per method
- equivalent stress
- predicted life
- pass/fail against target life
- warning badge if invalid or cautionary

3. Charts tabset
- Haigh diagram
- S-N plot
- sensitivity sweep

4. Derivations
- click a method row to reveal substituted equations

5. Background tab
- theory, assumptions, examples, references

### 8.3 Default Inputs

Defaults should be chosen to produce an instructive, finite-life example on first load.

Suggested defaults:

- material preset: `steel_1045`
- `alternating_stress_mpa = 180`
- `mean_stress_mpa = 120`
- `target_life_cycles = 1e6`
- `reference_basis = target_life`
- all methods enabled

Why:

- zero-learning-curve first run
- visible method separation
- not immediately invalid
- not immediately infinite-life

### 8.4 Chart Behavior

#### Haigh diagram

Primary chart. Requirements:

- all enabled method envelopes on one plot
- operating point marker
- shaded "below envelope" region optional, but method lines are mandatory
- `S_ut` and `S_y` intercept markers
- clear distinction between tensile and compressive mean stress regions

#### S-N plot

Requirements:

- base S-N curve
- one operating point per method at its `sigma_a,eq`
- log-scaled cycles axis
- visible endurance-limit floor when applicable

#### Sweep plot

Default sweep:

- x-axis: mean stress
- y-axis: life

Secondary sweep modes can be supported later, but v1 should keep this simple and readable.

### 8.5 Messaging and Tone

This tool should not imply that one line on a Haigh diagram equals design approval.

Use neutral language such as:

- "most conservative compared method"
- "predicted by selected model"
- "classical mean-stress correction"
- "use material-specific fatigue data for sign-off"

Avoid strong design-grade language such as:

- "safe"
- "certified"
- "guaranteed life"

## 9. Background / Educational Content

The Background tab should include:

1. What mean stress is
2. How `sigma_m`, `sigma_a`, `sigma_max`, `sigma_min`, and `R` relate
3. What the Haigh / Goodman diagram represents
4. Why Goodman, Gerber, and Soderberg differ
5. When tensile mean stress hurts fatigue performance
6. Why compressive mean stress is not a free design credit
7. When this tool should not be used
8. Worked example with the default values

Suggested references:

- Shigley, fatigue chapter
- Juvinall & Marshek
- Dowling, Mechanical Behavior of Materials
- Bannantine, Comer, and Handrock, Fundamentals of Metal Fatigue Analysis

## 10. Validation and Error Handling

Backend validation should be primary. UI validation is secondary.

Required backend behaviors:

- raise `ValueError` for globally invalid input states
- return per-method invalidity status when only one method fails
- never return contradictory outputs such as:
  - finite life with invalid denominator
  - pass target life with negative allowable alternating stress

Frontend behaviors:

- keep previous results cleared on hard error
- preserve the user’s inputs
- show method-specific warning text inline in the comparison table

## 11. Testing Plan

Extend `tests/test_fatigue.py` rather than creating a disconnected fatigue test module.

### 11.1 Deterministic Unit Tests

Add tests for:

1. Stress-state conversion
- `sigma_max = sigma_m + sigma_a`
- `sigma_min = sigma_m - sigma_a`
- correct `R` ratio

2. Zero mean stress consistency
- Goodman, Gerber, Soderberg, and None all reduce to `sigma_a`

3. Positive mean-stress ordering
- for `0 < sigma_m < S_y < S_ut`:
  - `sigma_eq_soderberg >= sigma_eq_goodman >= sigma_eq_gerber >= sigma_eq_none`

4. Invalid denominator handling
- Goodman invalid at `sigma_m >= S_ut`
- Gerber invalid at `|sigma_m| >= S_ut`
- Soderberg invalid at `sigma_m >= S_y`

5. Consistency with existing life estimator
- each method’s row must match a direct call to `estimate_fatigue_life(...)` using the same operating point

6. Endurance-limit behavior
- if `sigma_eq <= S_e`, life becomes infinite for supported materials

### 11.2 Sweep and Plot Sanity Tests

Add tests for:

1. Increasing positive mean stress at fixed `sigma_a` should not improve life.
2. Increasing positive mean stress at fixed `sigma_ref` should not increase allowable stress for classical tensile-region envelopes.
3. Plot arrays should be the requested length and finite in valid domains.
4. Operating point should appear inside returned axis bounds.

### 11.3 Manual Verification

Manual browser checks:

- default example loads with meaningful separation between methods
- dark mode chart contrast is readable
- invalid-method warnings do not blank out valid method rows
- derivation panels show correct substituted equations
- Background tab equations render cleanly in MathJax

## 12. Deliverables

Planned files:

- `plans/fatigue_mean_stress_explorer.md`
- `tools/fatigue-mean-stress-explorer/index.html`
- `tools/fatigue-mean-stress-explorer/README.md`
- `pycalcs/fatigue.py` updates
- `tests/test_fatigue.py` updates
- `catalog.json` entry

## 13. Recommended Implementation Sequence

1. Backend wrapper and tests first
- add multi-method comparison function
- add sweep-data generation
- add deterministic tests

2. Tool scaffold
- copy advanced template
- connect Pyodide to new backend function
- render summary table and Haigh diagram first

3. Add S-N plot and sweep plot

4. Add derivation panels and educational content

5. Final polish
- README
- catalog entry
- dark mode audit
- browser verification

## 14. Known Risks and Review Targets

These are the main points other agents should challenge:

1. Metal-only v1
- Is this the right scope boundary, or is there a strong case for custom non-ferrous-only support instead of the current preset set?

2. Compressive mean stress treatment
- Should the tool display direct classical equations with warnings, or clip compressive benefit by default?

3. Reference basis default
- Is `target_life` the right default, or should steels default to endurance-limit mode because that matches many textbook Goodman diagrams?

4. Status messaging
- Should the tool avoid a single pass/fail banner entirely, or should it show a banner keyed to the most conservative enabled method?

5. Method set
- Is `none + goodman + gerber + soderberg` the right v1 comparison set, or should `none` be omitted to reduce clutter?

6. Input mode
- Is `sigma_a` + `sigma_m` the correct default, or should the tool default to `sigma_max` + `sigma_min` because that is what more practicing engineers enter first?

7. Naming
- Is "Fatigue Mean-Stress Explorer" the right user-facing title, or would "Goodman / Gerber / Soderberg Explorer" be clearer?

## 15.5 Adjustments from Code Review (2026-03-12)

After reading `pycalcs/fatigue.py` and the existing life estimator, the following adjustments should be applied before implementation begins.

### 15.5.1 Shared x-axis for Haigh diagram is not automatic

The existing `_generate_mean_stress_curve` computes its own x-range per method call based on the current operating point. For the multi-method Haigh diagram, all envelope curves must share one x-axis array. The new backend function must compute a global `mean_stress_range` first and pass it to every method envelope. Do not call `_generate_mean_stress_curve` independently per method and then stitch results together.

### 15.5.2 Compressive-region clamping must be disabled for envelopes

`_generate_mean_stress_curve` currently clamps `sigma_a = max(0.0, sigma_a)` at line 313. This suppresses the envelope shape in the compressive mean-stress region. For the explorer, remove this clamp (or add an optional `clamp_zero` flag) so the Goodman, Gerber, and Soderberg curves extend naturally into negative mean-stress territory. The compressive-region warning (section 6.7) covers the user guidance.

### 15.5.3 Yield line shape must be specified in the return structure

The plan mentions a yield line on the Haigh diagram but does not define it in the return shape. Add to `haigh_diagram_data`:

```python
"yield_line_mean_mpa": [...],   # x values: 0 to S_y
"yield_line_alt_mpa": [...],    # y values: S_y - sigma_m  (static yield boundary)
```

This represents `sigma_a + sigma_m = S_y`, the locus where `sigma_max = S_y`. Clip at `sigma_a >= 0`.

### 15.5.4 `equivalent_stress_spread_pct` is missing from the top-level return shape

Section 6.6 lists `equivalent_stress_spread_pct` as a required output, but it does not appear in the section 7.3 return dict. Add it:

```python
"equivalent_stress_spread_pct": ...,  # (max_eq - min_eq) / min_eq * 100, valid methods only
```

### 15.5.5 Define `life_spread_ratio` explicitly

The plan names the field but does not define the formula. Use:

```python
life_spread_ratio = max(finite_lives) / min(finite_lives)
```
computed over valid methods only. If all valid methods return infinite life, return `1.0`. If only one valid method exists, return `1.0`. Document this in the function docstring.

### 15.5.6 Per-method comparison table row is missing `estimated_life_hours`

Section 6.6 lists `estimated_life_hours` per method but it does not appear in the section 7.3 comparison table row schema. Add it:

```python
"estimated_life_hours": ...,
```

### 15.5.7 `reference_stress_mpa` is material-derived, not per-method

Clarify in sections 6.4 and 7.3 that `reference_stress_mpa` (the envelope baseline stress) is computed once from the material and `reference_basis` selection, then shared by all methods for envelope drawing. Each method computes its own `equivalent_stress_mpa` for life prediction, but the S-N reference stress is the same across the comparison.

### 15.5.8 Consistency test scope is narrower than stated

Section 11.1.5 requires each method row to match a direct call to `estimate_fatigue_life`. This only holds exactly when `reference_basis = "endurance_limit"` for a material that has one, because the existing `estimate_fatigue_life` auto-selects basis (prefers endurance limit when available). Narrow the test fixture to match this condition explicitly, or document the known difference when `reference_basis = "target_life"` is forced.

### 15.5.9 Soderberg with `S_y > S_ut` needs an explicit validity flag

The plan flags `S_y > S_ut` as a general warning (section 6.8), but Soderberg specifically becomes more conservative than Goodman in this case, which is physically wrong. Add a method-specific `validity_state = "warning"` on Soderberg rows when `S_y > S_ut`, with message: "Soderberg uses yield strength as the mean-stress limit. If S_y > S_ut, Soderberg is less conservative than Goodman, which is non-physical for standard metals."

### 15.5.10 Input signature uses comma-string for `enabled_methods`

The proposed signature uses `enabled_methods: str = "none,goodman,gerber,soderberg"`. This is workable from Pyodide/JS but document the expected format in the docstring and validate it explicitly at function entry (strip, lower, split on comma, check each against known set). Do not allow silent inclusion of unknown method names.

---

## 15. Acceptance Criteria

The tool is ready for implementation review once the plan is accepted on these points:

1. Clear differentiation from the existing fatigue-life estimator.
2. Agreement that v1 stays narrow: metal, uniaxial, constant-amplitude, classical methods.
3. Agreement on compressive mean-stress behavior.
4. Agreement on whether the tool should present a single overall status.
5. Agreement that the backend should reuse `pycalcs/fatigue.py` rather than duplicating equations.
