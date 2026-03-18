# Polymer Fatigue Criteria Explorer

Date: 2026-03-17
Status: Proposed plan for critique before implementation
Related existing assets:
- `tools/fatigue-life-estimator/`
- `tools/fatigue-mean-stress-explorer/`
- `pycalcs/fatigue.py`
- `tests/test_fatigue.py`

## 1. Purpose

Build an exploratory fatigue tool focused on one polymer-specific question:

> For a given polymer material system and cyclic load case, how do different fatigue criteria compare, and when do hysteresis energy, cyclic creep, and hybrid models materially disagree on life?

The tool should help users compare polymer fatigue criteria side by side, understand when a criterion is being applied inside or outside its calibration range, and see how the response shifts between low-cycle, high-cycle, creep-dominated, and hysteresis-dominated behavior.

This is not meant to replace the existing `fatigue-life-estimator`. That tool is a broad screening calculator with a classical stress-life backbone. The new tool should be comparison-first, polymer-specific, and explicit about calibration ranges and model applicability.

## 2. Positioning Relative to Existing Tooling

The existing [fatigue-life-estimator](../tools/fatigue-life-estimator/README.md) already supports a polymer mode, but that mode is still fundamentally:

- a Basquin-style stress-life workflow,
- coupled to heuristic polymer derating factors, and
- oriented toward one-scenario design checking rather than criteria comparison.

The new tool should differ in these ways:

- It should compare multiple polymer fatigue criteria at once instead of forcing one model selection up front.
- It should treat stabilized loop observables as first-class inputs where required, rather than pretending all polymer fatigue can be reduced to stress amplitude alone.
- It should surface criterion validity limits, calibration source, and environmental coverage as primary outputs.
- It should use classical stress-life or strain-life only as a reference layer, not as the main polymer model.

## 3. User Jobs

### Hurried engineer

- Select a polymer system and loading case.
- See which fatigue criterion is most conservative and which is outside its supported range.
- Compare predicted lives without reading the full literature first.

### Curious student

- Understand why polymer fatigue is not captured well by a single S-N curve.
- See how hysteresis energy, ratcheting / cyclic creep, and hybrid metrics relate to damage progression.
- Learn how LCF and HCF map onto polymer-specific mechanisms rather than metal-only definitions.

### Verifying expert

- Inspect the exact equations, coefficients, units, and calibration source for each criterion.
- Confirm whether the current point is inside the cited range of load ratio, temperature, frequency, moisture state, and orientation.
- Trace every plotted prediction back to either a literature-backed preset or directly entered loop metrics.

## 4. Scope

### In Scope for v1

- Uniaxial, constant-amplitude polymer fatigue exploration.
- Emphasis on short-fiber reinforced thermoplastics in v1 because the best-supported mixed energy / creep-rate criteria are concentrated there.
- Side-by-side comparison of:
  - reference stress-life or strain-life model,
  - hysteresis dissipated energy criterion,
  - cyclic creep strain rate criterion,
  - hybrid energy + cyclic creep strain rate criterion.
- User-facing LCF / transition / HCF labeling.
- User-facing mechanism labeling:
  - `hysteresis-dominated`
  - `creep-dominated`
  - `mixed`
- Two input workflows:
  - `calibrated preset exploration`
  - `measured stabilized-loop workflow`
- Plot-ready data returned from the backend.
- Strong validity and extrapolation warnings.

### Explicitly Out of Scope for v1

- Variable-amplitude loading, rainflow counting, and Miner damage.
- Multiaxial fatigue.
- Full constitutive viscoelastic-viscoplastic modeling.
- FE-linked local hotspot or notch-root modeling.
- Fully generic predictions for commodity polymers with no supporting calibration dataset.
- Automatic import and fitting of raw CSV loop histories.
- A single universal polymer life equation spanning neat thermoplastics, elastomers, thermosets, and short-fiber composites.

## 5. Core Product Decision

The new tool should not be implemented as a light extension of `pycalcs/fatigue.py`.

Recommended structure:

- Keep the existing fatigue tool intact for generic screening and backwards compatibility.
- Create a new module, `pycalcs/polymer_fatigue.py`, for polymer-specific criteria and preset metadata.
- Reuse only low-level generic helpers where they are truly shared, such as Basquin algebra or hours-from-cycles conversion.
- Do not reuse the current `POLYMER_PRESETS` in `pycalcs/fatigue.py` as authoritative polymer fatigue calibrations. They are useful for the screening calculator, but they are too shallow and insufficiently provenance-rich for a criteria-comparison tool.

This separation keeps the new tool honest without breaking the current tool.

## 6. Model Strategy

### 6.1 Reference Layer: Stress-Life and Strain-Life

Use a classical life model as a reference layer only.

Recommended reference stack:

- `Basquin` when only elastic stress-life data are available.
- `Basquin-Coffin-Manson` when the preset includes a defensible strain-life calibration spanning lower-cycle response.

Why this stays a reference layer:

- It gives users a familiar anchor.
- It helps explain LCF / HCF terminology.
- It should not be presented as the governing polymer model when stronger loop-based criteria are available.

### 6.2 Hysteresis Dissipated Energy Criterion

Make stabilized hysteresis dissipated energy the first polymer-specific criterion.

Core observable:

- `W_d = \oint \sigma \, d\varepsilon`

Typical life relation:

- `\log N_f = A + B \log W_d`
- or an equivalent preset-specific power-law form.

Why it belongs in v1:

- It is physically intuitive for polymers.
- It reflects internal dissipation and self-heating trends.
- It is supported by both review literature and short-fiber composite studies.
- It gives a useful comparison against creep-rate criteria when cyclic ratcheting is not dominant.

### 6.3 Cyclic Creep Strain Rate Criterion

Make cyclic creep strain rate the second polymer-specific criterion.

Recommended form for v1:

- Use a maximum-strain-based steady-state criterion rather than an older mean-strain-based one.

Core observable:

- `d\varepsilon_{max}/dN` measured over the stabilized or secondary regime.

Typical life relation:

- `\log N_f = C + D \log (d\varepsilon_{max}/dN)`
- or an equivalent preset-specific power-law form.

Why this is the better default:

- Recent validation work extended the criterion across a wider range of load ratios, including negative `R`.
- It appears to unify creep and fatigue response more cleanly than earlier mean-strain-rate formulations.
- It is especially useful for polymers where cyclic creep or ratcheting is an important part of the damage signature.

### 6.4 Hybrid Energy + Cyclic Creep Strain Rate Criterion

This should be the flagship criterion for the tool.

Recommended approach:

- Support preset-specific mixed formulations where a creep-rate term governs or dominates for positive load ratios, and an added energy term extends the criterion across negative load ratios and mixed hysteresis conditions.

Implementation rule:

- Do not hard-code one universal hybrid equation unless the chosen preset family shares that form.
- Store the hybrid equation form and coefficients with the preset metadata so the backend can evaluate the correct relation for that source.

Why this should be the flagship model:

- It is directly aligned with the strongest short-fiber reinforced thermoplastic literature identified for this tool concept.
- It covers cases where energy-only and creep-only criteria each miss part of the physics.
- It is the best fit to the user's stated goal of comparing hysteresis energy against hybrid energy + cyclic creep criteria.

### 6.5 Why These Models

The literature direction is consistent:

- reviews emphasize that creep development and energy dissipation are both informative damage measures,
- plastic-strain-development-based models often show the best agreement with experiments,
- mixed criteria improve robustness across load-ratio changes, and
- maximum-strain cyclic creep criteria extend the usable load-ratio range further than older creep-only variants.

That means the tool should not try to crown one universal winner. It should compare:

- a classical reference model,
- a dissipation-focused model,
- a creep-focused model, and
- a combined model.

### 6.6 LCF / HCF Handling

Do not use `LCF` and `HCF` as the primary model selector.

Recommended behavior:

- Show cycle-band labels for orientation:
  - `LCF` when predicted life is roughly `N < 1e4`
  - `transition` when `1e4 <= N < 1e5`
  - `HCF` when `N >= 1e5`
- Also show a mechanism tag based on current observables and criterion spread:
  - `hysteresis-dominated`
  - `creep-dominated`
  - `mixed`

Why:

- In polymers, time-dependent effects and loop evolution blur a simple metal-style LCF/HCF split.
- Users still benefit from familiar cycle-range language, but the real educational value is in showing which physical observable is organizing the data best.

## 7. Data and Calibration Design

### 7.1 Preset Philosophy

v1 should prefer a small number of high-provenance presets over a large number of shallow ones.

Rules:

- Every preset must cite its source paper.
- Every preset must carry explicit validity ranges.
- Every preset must state whether it is:
  - literature-calibrated,
  - reference-only, or
  - user-calibrated.
- No placeholder coefficients should be invented just to populate dropdowns.

### 7.2 Minimum Preset Fields

Each preset should include at least:

- `display_name`
- `material_family`
- `matrix`
- `reinforcement`
- `fiber_weight_fraction` or `fiber_volume_fraction` when known
- `conditioning_state`
- `orientation_options`
- `supported_load_ratios`
- `supported_temperature_range_c`
- `supported_frequency_range_hz`
- `supported_moisture_states`
- `control_mode`
- `reference_model`
- `energy_model`
- `cyclic_creep_model`
- `hybrid_model`
- `source_title`
- `source_url`
- `notes`

Each model entry should include:

- coefficient names and values,
- equation identifier,
- required observables,
- unit conventions,
- calibration scatter or expected error band when reported.

### 7.3 Recommended Initial Preset Set

Start narrower than the current generic polymer preset list.

Recommended initial calibration set:

1. One deeply supported `PA66-GF50` family with orientation and conditioning options where the cited papers support them.
2. One additional short-fiber reinforced thermoplastic family only if the literature provides comparable mixed-criterion coverage.
3. A `user-calibrated` custom mode that lets advanced users enter their own coefficients and loop metrics.

This is better than shipping generic `ABS`, `PC`, `POM`, or `PEEK` fatigue criteria without real criterion-specific provenance.

### 7.4 Validity and Extrapolation Rules

The backend should distinguish:

- `valid`
- `warning`
- `invalid`

Examples:

- Outside the source load-ratio range but near the edge: `warning`
- Outside temperature or frequency range by a small margin: `warning`
- Missing required loop metric for a chosen criterion: `invalid`
- Applying a criterion to a preset that was never calibrated for that criterion: `invalid`

The UI should never silently extrapolate a criterion and present the result as equivalent in confidence to an in-range prediction.

## 8. Backend Architecture

### 8.1 New Module

Create:

- `pycalcs/polymer_fatigue.py`

Keep tests separate from the current fatigue test module unless small helper extraction makes a shared test useful.

Recommended companion files:

- `tests/test_polymer_fatigue.py`
- `tools/polymer-fatigue-criteria-explorer/index.html`
- `tools/polymer-fatigue-criteria-explorer/README.md`

### 8.2 Recommended Public API

Tentative public functions:

```python
def get_polymer_fatigue_presets() -> dict[str, dict[str, object]]:
    ...


def compare_polymer_fatigue_criteria(
    material_preset: str,
    load_ratio: float,
    temperature_c: float = 23.0,
    load_frequency_hz: float = 2.0,
    moisture_state: str = "dry_as_molded",
    orientation_bucket: str = "0_deg",
    stress_amplitude_mpa: float | None = None,
    max_stress_mpa: float | None = None,
    strain_amplitude_pct: float | None = None,
    max_strain_pct: float | None = None,
    stabilized_loop_energy_mj_per_m3: float | None = None,
    stabilized_max_strain_rate_per_cycle: float | None = None,
    target_life_cycles: float = 1e6,
    enabled_models: str = "reference,energy,cyclic_creep,hybrid",
) -> dict[str, object]:
    ...
```

The exact signature can change, but the behavior should remain:

- one operating point in,
- all enabled criteria compared out,
- plot-ready data returned,
- every criterion tagged with its applicability state.

### 8.3 Input Workflow Design

The backend should explicitly support two workflows.

#### Workflow A: Calibrated preset exploration

Users enter:

- material preset,
- `R`,
- stress or strain loading summary,
- environment,
- orientation.

This mode is allowed only when the preset includes enough information to map the current operating point to the observables needed by the criterion or to evaluate the published reduced equation directly.

#### Workflow B: Measured stabilized-loop workflow

Users enter:

- stabilized loop energy,
- stabilized cyclic creep strain-rate metric,
- plus context such as `R`, temperature, frequency, and orientation.

This mode is the honest fallback when no trustworthy preset-side mapping exists from ordinary load inputs to the needed observables.

This workflow is critical because it lets the tool stay useful without inventing unsupported load-to-loop surrogate models.

### 8.4 Backend Return Shape

Top-level return structure should include:

```python
{
    "material_preset": ...,
    "material_preset_name": ...,
    "workflow_mode": ...,
    "load_ratio": ...,
    "temperature_c": ...,
    "load_frequency_hz": ...,
    "moisture_state": ...,
    "orientation_bucket": ...,
    "target_life_cycles": ...,
    "lcf_hcf_regime": ...,
    "mechanism_regime": ...,
    "comparison_table": [...],
    "governing_model": ...,
    "least_conservative_model": ...,
    "life_spread_ratio": ...,
    "warnings": [...],
    "applicability_summary": [...],
    "criterion_plot_data": {...},
    "sweep_plot_data": {...},
    "calibration_plot_data": {...},
    "subst_loop_energy": ...,
    "subst_cyclic_creep_rate": ...,
}
```

Each comparison row should include:

```python
{
    "model": "hybrid",
    "estimated_life_cycles": ...,
    "estimated_life_hours": ...,
    "life_ratio_to_target": ...,
    "required_observables": [...],
    "used_observables": {...},
    "applicability_state": "valid" | "warning" | "invalid",
    "warning_messages": [...],
    "source_title": ...,
    "source_url": ...,
    "subst_estimated_life_cycles": ...,
}
```

### 8.5 Single Source of Truth

To preserve a single source of truth:

- keep polymer-specific criterion definitions and preset coefficients in `pycalcs/polymer_fatigue.py`,
- extract any truly shared Basquin-style helper math into a small shared helper if both fatigue modules need it,
- do not duplicate criterion equations in JavaScript,
- do not store hidden fallback coefficients in the frontend.

## 9. Frontend Plan

### 9.1 Template Choice

Use `tools/example_tool_advanced/index.html` as the base template.

Reason:

- multiple input sections,
- multiple comparison outputs,
- more than one chart,
- strong need for validity messaging,
- educational background content and references,
- likely settings persistence for comparison preferences.

### 9.2 Tool Layout

#### Left column: inputs

Sections:

1. `Material and Calibration`
   - material preset
   - source and validity summary
   - orientation
   - conditioning / moisture state

2. `Loading`
   - load ratio `R`
   - stress-controlled or strain-controlled input
   - max stress / amplitude or max strain / amplitude
   - frequency
   - temperature

3. `Loop Observables`
   - stabilized hysteresis energy
   - stabilized cyclic creep strain-rate metric
   - workflow indicator showing whether each observable is direct-entry, preset-derived, or unavailable

4. `Comparison Controls`
   - enabled criteria
   - target life
   - sweep variable
   - sweep range

#### Right column: outputs

Sections:

1. `Neutral Summary`
   - governing model
   - life spread ratio
   - regime labels
   - strongest applicability warning

2. `Comparison Table`
   - one row per criterion
   - predicted life
   - target-life ratio
   - applicability state
   - source badge

3. `Charts`
   - comparison plot,
   - sweep plot,
   - calibration-space plot.

4. `Derivations`
   - click a row to show criterion equation,
   - substituted values,
   - source citation.

5. `Background`
   - polymer fatigue theory,
   - LCF / HCF interpretation for polymers,
   - why energy and cyclic creep matter,
   - assumptions and limitations,
   - references.

### 9.3 Default Experience

The default load case should be finite-life and should show non-trivial disagreement between models.

Recommended default behavior:

- load a literature-backed `PA66-GF50` example preset,
- prefill one valid example operating point,
- prefill any required loop observables when using the literature example mode,
- present all criteria enabled by default,
- avoid a pass/fail headline.

The first screen should answer:

- what the current operating point is,
- which criterion is most conservative,
- and whether the comparison is fully in-range.

### 9.4 Charts

Recommended v1 charts:

1. `Life by Criterion`
   - bar or dot plot on log-life axis,
   - one point per model,
   - color by applicability state.

2. `Sweep Plot`
   - x-axis selectable between stress, strain, loop energy, or creep-rate metric when meaningful,
   - y-axis predicted life,
   - all enabled models shown together.

3. `Calibration-Space Plot`
   - current point against literature calibration data or validity envelope,
   - lets users see whether they are interpolating or extrapolating.

This plot is important because it makes the tool visibly calibration-aware rather than presenting every prediction as equally grounded.

### 9.5 Messaging and Tone

Use neutral language such as:

- `most conservative compared model`
- `predicted by calibrated criterion`
- `reference model only`
- `outside cited range`
- `loop metric required for high-confidence comparison`

Avoid language such as:

- `safe`
- `approved`
- `certified`
- `guaranteed life`

## 10. Implementation Phases

### Phase 1: Plan and Data Curation

- Confirm the initial preset family or families.
- Extract the exact equation forms and units from the chosen papers.
- Record validity ranges and scatter bands.
- Decide which observables are directly user-entered in v1.

### Phase 2: Backend

- Create `pycalcs/polymer_fatigue.py`.
- Implement preset lookup and validation.
- Implement reference, energy, cyclic-creep, and hybrid criteria.
- Return plot-ready comparison and sweep data.
- Add substituted-equation strings and source metadata.

### Phase 3: Frontend

- Create `tools/polymer-fatigue-criteria-explorer/index.html` from the advanced template.
- Build preset and workflow controls.
- Build the comparison table and charts.
- Add background content and references.

### Phase 4: Verification

- Add deterministic tests against published example points where possible.
- Add monotonicity and validation tests.
- Verify the UI handles missing metrics and out-of-range states cleanly.

### Phase 5: v2 Candidates

- CSV import for measured loop data.
- User fitting of criterion coefficients from uploaded test data.
- Additional preset families.
- Heat-build-up assisted calibration workflow.
- Multiaxial or notch-aware extensions only after the uniaxial core is stable.

## 11. Testing and Verification Plan

### Backend regression tests

- Every enabled criterion returns the expected life for at least one literature-backed example.
- Invalid missing-observable states return structured errors or `invalid` states, not silent fallbacks.
- Out-of-range conditions produce the correct warning tier.

### Property tests

- Increasing dissipated energy must not increase predicted life for the same criterion and preset.
- Increasing cyclic creep strain rate must not increase predicted life.
- Holding everything else fixed, the hybrid criterion should reduce to its documented sub-form when the preset specifies that regime.

### UI verification

- Default example loads fully and shows finite-life comparison.
- Each criterion row can open its derivation and source details.
- Warning banners do not disappear when the user switches charts.
- The calibration-space plot clearly marks the current point.

## 12. Acceptance Criteria

This plan can be considered implementation-ready when all are true:

1. The initial preset family is explicitly chosen and sourced.
2. Every shipped criterion has an equation form, units, and validity range documented in code and UI.
3. The tool can compare at least `reference`, `energy`, `cyclic_creep`, and `hybrid` predictions for one real preset without hidden heuristics.
4. Missing loop observables are handled explicitly rather than imputed silently.
5. The UI defaults to a meaningful finite-life example and avoids pass/fail overclaiming.

## 13. Sources

Primary sources used to shape this plan:

1. Bogdanov, Panin, and Kosmachev, "Fatigue Damage Assessment and Lifetime Prediction of Short Fiber Reinforced Polymer Composites—A Review," *Journal of Composites Science* 7(12), 484, 2023.
   - https://www.mdpi.com/2504-477X/7/12/484
   - Key planning takeaway: stiffness reduction, creep development, and energy dissipation are complementary; plastic-strain-development-based models often show the best agreement.

2. "A mixed strain rate and energy based fatigue criterion for short fiber reinforced thermoplastics," *International Journal of Fatigue* 127, 131-143, 2019.
   - https://doi.org/10.1016/j.ijfatigue.2019.06.003
   - Key planning takeaway: a mixed criterion is effective across orientation and load-ratio changes, with an added energy parameter needed for negative load ratios.

3. "Fatigue criteria for short fiber-reinforced thermoplastic validated over various fiber orientations, load ratios and environmental conditions," *International Journal of Fatigue* 135, 105574, 2020.
   - https://doi.org/10.1016/j.ijfatigue.2020.105574
   - Key planning takeaway: the criterion comparison needs explicit handling of orientation, load ratio, and environmental conditioning.

4. "Cyclic creep strain rate criterion for short-fibre reinforced thermoplastics: Validation of creep and fatigue performance across a wide range of load ratios," *International Journal of Fatigue* 183, 108257, 2024.
   - https://doi.org/10.1016/j.ijfatigue.2024.108257
   - Key planning takeaway: maximum-strain-based cyclic creep rate is a strong candidate for the core creep-focused comparator in v1.

5. "Fatigue strength assessment of a short fiber composite based on the specific heat dissipation," *Composites Part B: Engineering* 42(2), 217-225, 2011.
   - https://doi.org/10.1016/j.compositesb.2010.12.002
   - Key planning takeaway: dissipation-based fatigue assessment is experimentally grounded and useful as an energy-based comparator.

6. "Fast Prediction of the Fatigue Behavior of Short Fiber Reinforced Thermoplastics from Heat Build-up Measurements," *Procedia Engineering* 66, 737-745, 2013.
   - https://doi.org/10.1016/j.proeng.2013.12.127
   - Key planning takeaway: heat-build-up and energy-based workflows are promising, but they should remain a deferred extension rather than a hidden assumption in v1.

7. "Fatigue of short fiber thermoplastic composites: A review of recent experimental results and analysis," *International Journal of Fatigue* 102, 171-183, 2017.
   - https://doi.org/10.1016/j.ijfatigue.2017.01.037
   - Key planning takeaway: polymer fatigue is strongly affected by orientation, temperature, moisture, frequency, and mean stress, so validity ranges must be visible in the tool.
