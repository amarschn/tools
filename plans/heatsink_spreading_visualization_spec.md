# Heatsink Base-Spreading Solver & Visualization Spec

> **Purpose:** Define a focused implementation spec for adding a basic source-aware spreading solver and a top-view thermal visualization to the heatsink designer. This is intended as a standalone handoff document for an implementation session.

---

## 1. Why This Feature Exists

The current heatsink tool is strong on global thermal budgeting but weak on source-level intuition.

Today the tool:
- solves overall sink performance with an isothermal-base assumption,
- adds source-size effects as a single scalar `spreading_resistance`,
- shows geometry, temperature ladder, heat split, and sensitivity plots,
- does **not** show where the hot spot is on the base or how source position changes the field.

That gap makes the tool feel less useful than products that are visibly source-aware.

### External Workflow Cues Worth Adopting

Observed patterns from `heatsinkcalculator.com`:
- The workflow is source-centric, not just sink-centric.
- Geometry, airflow, power-source definition, and results are separated into clear conceptual steps.
- The plan-view source placement is visually important.
- A thermal contour / spreading visualization gives immediate intuition that scalar `R_theta` values do not.

Relevant references:
- https://www.heatsinkcalculator.com/
- https://www.heatsinkcalculator.com/calculator/demo-app.php
- https://www.heatsinkcalculator.com/blog/top-3-mistakes-made-when-selecting-a-heat-sink/
- https://www.heatsinkcalculator.com/blog/heat-sink-design-optimization-for-forced-convection/

This spec borrows the useful workflow ideas, but keeps the implementation aligned with this repo's constraints:
- no CFD,
- no external numerical libraries,
- explicit assumptions,
- Pyodide-safe runtime,
- progressive simplicity by default.

---

## 2. Product Goal

Add a new capability that answers:

1. Where is the base hot spot relative to the source footprint?
2. How much hotter is the local source region than the average base temperature?
3. How do source size and source position change that local temperature field?

The feature should make spreading visible without pretending to be full 3D CFD.

---

## 3. Scope

### In Scope for v1

- A **2D steady-state base-plane spreading solver** for the heatsink base.
- A **top-view temperature heatmap** over the base footprint.
- Support for **one localized rectangular source** in the default flow.
- Data model designed for **multiple sources later**, even if the initial UI exposes only one.
- A **source overlay** on the existing top-view preview.
- A new **Spread View** tab with:
  - temperature heatmap,
  - source overlay,
  - basic source summary metrics,
  - horizontal and vertical centerline plots,
  - an always-visible assumptions note.

### Out of Scope for v1

- Full 3D conduction through fins.
- CFD-like airflow visualization.
- Transient thermal response.
- Automatic geometry optimization.
- Claiming safety-grade absolute hotspot accuracy.
- Replacing the global plate-fin solver outright.

---

## 4. Design Principles

### 4.1 Keep the Existing Global Solver

The current `analyze_plate_fin_heatsink()` function in `pycalcs/heatsinks.py` should remain the primary baseline solver.

Reason:
- it already computes the global sink-to-ambient performance,
- it already drives the main results cards,
- it is already tested,
- replacing it immediately would be risky and unnecessary.

### 4.1.1 Put the New Field Solver in a Separate Module

The new base-spreading solver should **not** be added as a large block inside `pycalcs/heatsinks.py`.

Recommended structure:
- `pycalcs/heatsinks.py`
  - keep the existing global plate-fin solver,
  - own the user-facing orchestration function,
  - call into the spreading module when local-field results are requested.
- `pycalcs/heatsink_spreading.py`
  - own the 2D field solver,
  - own grid generation and source-overlap helpers,
  - own convergence logic,
  - own field-summary postprocessing.

Reason:
- the current `heatsinks.py` file is already large and handles several distinct concerns,
- the spreading solver is numerically different from the global resistance-based solver,
- a separate module is easier to test, reason about, and evolve,
- this keeps the main heatsink API readable instead of turning `heatsinks.py` into a grab bag.

The intended architecture is:
1. `heatsinks.py` solves global sink performance.
2. `heatsinks.py` passes geometry, material, ambient, and source data to `heatsink_spreading.py`.
3. `heatsink_spreading.py` returns field data and local source metrics.
4. `heatsinks.py` packages the combined result for the frontend.

### 4.2 Add a Secondary Local Solver

The new spreading solver should be a **secondary model** that sits on top of the global solve.

Conceptually:
1. Run the existing global solver.
2. Convert its solved sink performance into an equivalent distributed sink conductance.
3. Solve the base temperature field caused by localized source input plus distributed ambient rejection.
4. Visualize the resulting field and derive source-local metrics.

This keeps v1 incremental and low-risk.

### 4.3 Be Honest About Model Fidelity

The UI must explicitly state:
- this is a **2D base-plane conduction model**,
- fins are not individually meshed,
- heat rejection is represented as a distributed sink term,
- results are for **early design intuition**, not CFD replacement.

---

## 5. Recommended Workflow Changes

The current tool flow is still mostly sink-first. This feature should push it toward a more useful structure.

### v1 Workflow

Use these conceptual groups:

1. **Thermal Budget**
   - heat load
   - ambient temperature
   - target source/junction limit

2. **Heatsink Geometry**
   - base length
   - base width
   - base thickness
   - fin geometry

3. **Airflow**
   - natural / forced / fan curve
   - relevant airflow controls

4. **Source**
   - source length
   - source width
   - source position x/y
   - `R_theta,jc`
   - `R_theta,cs`

5. **Results**
   - global sink performance
   - spreading view
   - ladder / heat split / sweeps

### UX Guidance

- `source_length` and `source_width` should no longer feel optional or hidden if the spreading view is present.
- The top-view preview should show the source rectangle before calculation.
- Default the source to **centered**.
- Put source position controls behind expert mode if needed, but keep source size visible.

---

## 6. Solver Concept

### 6.1 Model Domain

Model only the **base plate footprint** in plan view:

- `x`: base length / flow direction
- `y`: base width across the fin array

The field variable is base temperature `T(x, y)`.

### 6.2 Physical Interpretation

The base plate does three things:

1. conducts heat laterally in-plane,
2. receives heat from one or more localized source footprints,
3. rejects heat to ambient through the finned sink as a distributed sink term.

### 6.3 Why This Is a Good v1 Approximation

This captures the main user-visible effect:
- small or off-center sources create local hot spots,
- thicker bases and higher conductivity spread heat better,
- the average base temperature may be acceptable while a local source region is significantly hotter.

That is exactly the missing intuition in the current tool.

---

## 7. Mathematical Model

### 7.1 Grid

Discretize the base plate into a regular `Nx * Ny` grid.

Recommended default:
- `Nx = 41`
- `Ny = 25`

This is dense enough for a useful contour and still cheap enough for pure Python in Pyodide.

### 7.2 In-Plane Conduction

For a cell with dimensions `dx` and `dy`, plate thickness `t`, and conductivity `k`:

```text
Gx = k * t * dy / dx
Gy = k * t * dx / dy
```

Use these conductances between east-west and north-south neighbors.

### 7.3 Distributed Sink Term

Convert the global sink result into an equivalent total sink conductance:

```text
G_sink,total = 1 / R_theta,sink
```

Distribute that over the grid cells:

```text
G_sink,ij = w_ij / sum(w) * G_sink,total
```

For v1, use:

```text
w_ij = A_cell
```

So the sink term is uniform over the footprint.

This has an important property:
- the weighted average field temperature above ambient remains consistent with the existing global solution because total sink conductance is preserved.

### 7.4 Source Heat Input

Represent each source as a rectangular patch:

```text
source = {
  x_center,
  y_center,
  length,
  width,
  power,
  r_jc,
  r_cs,
}
```

Distribute source power across overlapping cells by area fraction:

```text
Q_ij = sum_s (q''_s * overlap_area_ij,s)
```

where:

```text
q''_s = power_s / source_area_s
```

### 7.5 Cell Balance Equation

For each cell:

```text
sum_neighbors G_n * (T_ij - T_n) + G_sink,ij * (T_ij - T_ambient) = Q_ij
```

Rearranged for iterative update:

```text
T_ij =
(
  sum_neighbors G_n * T_n
  + G_sink,ij * T_ambient
  + Q_ij
)
/
(
  sum_neighbors G_n + G_sink,ij
)
```

### 7.6 Boundary Conditions

Use **adiabatic outer edges** in v1.

Reason:
- the global sink rejection is already represented by the distributed sink term,
- adding separate edge convection would double-count heat rejection.

### 7.7 Numerical Method

Use Gauss-Seidel with over-relaxation.

Recommended starting values:
- relaxation factor `omega = 1.4`
- `max_iterations = 4000`
- temperature convergence threshold `1e-6 K` max update

Return:
- iteration count,
- final residual / max update,
- converged boolean.

If convergence fails, raise `ValueError` with a useful message.

---

## 8. Coupling Strategy

### Phase A: One-Way Coupled Visualization

This should be the initial implementation.

Flow:
1. Run `analyze_plate_fin_heatsink()`.
2. Use `sink_thermal_resistance` from that result to derive `G_sink,total`.
3. Solve the base-plane field.
4. Show the spreading map and local metrics.

Do **not** replace the main result cards yet.

This keeps the feature additive.

### Phase B: Optional Result Integration

After validation, optionally add:
- `source_base_temperature_avg`
- `source_base_temperature_peak`
- `worst_source_junction_temperature`

At that point, the local solver can inform or replace the current scalar spreading penalty for the reported source/junction result.

That should be a separate decision, not part of the first implementation slice.

---

## 9. Recommended Python API

Add the numerical field solver to a new module:

```python
# pycalcs/heatsink_spreading.py
```

Primary field-solver API:

```python
def solve_base_spreading_field(
    *,
    base_length: float,
    base_width: float,
    base_thickness: float,
    material_conductivity: float,
    ambient_temperature: float,
    sink_thermal_resistance: float,
    sources: list[dict[str, float]],
    grid_x: int = 41,
    grid_y: int = 25,
    sink_weighting: str = "uniform",
) -> dict[str, Any]:
    ...
```

### `sources` Shape

Each source dict should support:

```python
{
    "id": "source_1",
    "x_center": 0.04,
    "y_center": 0.025,
    "length": 0.02,
    "width": 0.02,
    "power": 80.0,
    "junction_to_case_resistance": 0.5,
    "interface_resistance": 0.2,
}
```

### Recommended Return Shape

```python
{
    "x_coords": [...],
    "y_coords": [...],
    "temperature_grid": [[...]],
    "temperature_rise_grid": [[...]],
    "mean_base_temperature": ...,
    "peak_base_temperature": ...,
    "min_base_temperature": ...,
    "max_spreading_delta": ...,
    "energy_balance_error": ...,
    "iterations": ...,
    "converged": True,
    "sink_conductance_total": ...,
    "source_summaries": [
        {
            "id": "source_1",
            "power": 80.0,
            "avg_base_temperature": ...,
            "peak_base_temperature": ...,
            "avg_case_temperature": ...,
            "avg_junction_temperature": ...,
            "peak_junction_temperature_estimate": ...,
        }
    ],
    "centerline_x": {
        "coords": [...],
        "temperature": [...],
    },
    "centerline_y": {
        "coords": [...],
        "temperature": [...],
    },
    "source_rectangles": [
        {
            "id": "source_1",
            "x0": ...,
            "x1": ...,
            "y0": ...,
            "y1": ...,
        }
    ],
    "assumptions": [
        "...",
        "...",
    ],
}
```

### Orchestration Wrapper

Add the frontend-facing wrapper in `pycalcs/heatsinks.py`:

Add a second callable that bridges the baseline solve to the local field solve:

```python
def analyze_heatsink_spreading_view(
    ... same user inputs as analyze_plate_fin_heatsink ...,
    source_x: float = 0.0,
    source_y: float = 0.0,
    grid_x: int = 41,
    grid_y: int = 25,
) -> dict[str, Any]:
    ...
```

This function should:
1. call `analyze_plate_fin_heatsink()`,
2. build the source list,
3. call `pycalcs.heatsink_spreading.solve_base_spreading_field()`,
4. return both baseline and field data.

This avoids duplicating frontend data gathering logic.

---

## 10. Input Rules

### v1 Required Source Inputs

- `source_length > 0`
- `source_width > 0`

If either is zero:
- disable the Spread View tab, or
- show a strong empty-state message instead of a meaningless near-uniform map.

Recommended UX:
- keep the tab visible,
- show an empty state that says a localized source footprint is required.

### Source Positioning

Use source center coordinates measured from the lower-left corner of the base footprint:

```text
0 <= x_center <= base_length
0 <= y_center <= base_width
```

Reject any source that extends outside the base.

### Multiple Sources

Even if the v1 UI only supports one source, implement the backend with a list-based source model.

That prevents a rewrite later.

---

## 11. Frontend Changes

Primary file:
- `tools/simple_thermal/index.html`

### 11.1 Add Source Overlay to Live Preview

Extend the existing top-view preview in `tools/simple_thermal/index.html` to draw:
- source footprint rectangle,
- source center marker,
- optional label `Source 1`,
- immediate visual feedback when source dimensions or position change.

### 11.2 Add a New Tab

Insert a new tab:

```text
Results | Spread View | Temperature Ladder | Heat Split | 1D Sweep | 2D Trade Space | Background
```

Reason:
- the spreading view is more important than the ladder once source modeling exists,
- it directly explains why local temperatures differ from the global average.

### 11.3 Spread View Layout

Recommended content:

1. **Top-view thermal map**
   - Plotly heatmap over the base footprint
   - source rectangles overlaid as shapes
   - optional source labels

2. **Summary strip**
   - average base temperature
   - peak base temperature
   - spreading delta (`peak - mean`)
   - worst-source estimated junction temperature

3. **Centerline plots**
   - one line along source center in `x`
   - one line along source center in `y`

4. **Assumptions card**
   - always visible
   - short, blunt explanation of what is and is not modeled

### 11.4 Display Options

Add lightweight controls:
- `Absolute Temperature (°C)` vs `Rise Above Ambient (°C)`
- `Auto scale` vs `Fixed scale from ambient to peak`

Do not add too many knobs in v1.

### 11.5 Empty State

If no localized source is defined:
- do not render fake data,
- show a clear message:
  - "Set a source footprint to see localized base spreading."

---

## 12. Visual Style Guidance

The visualization should feel analytical, not decorative.

Use:
- a top-down engineering palette,
- visible source overlays,
- labeled axes in mm,
- a colorbar with units,
- restrained annotation.

Avoid:
- fake glow effects,
- animated heat shimmer,
- implying CFD resolution.

The plot should be readable on both desktop and mobile.

---

## 13. What Should Change in the Result Model

Do **not** disturb the current main result flow in the first pass.

However, add the following new secondary outputs:
- `mean_base_temperature`
- `peak_base_temperature`
- `max_spreading_delta`
- `worst_source_avg_junction_temperature`
- `worst_source_peak_junction_temperature_estimate`

Suggested user-facing definitions:
- **Average Base Temp**: area-weighted base average from the local field
- **Peak Base Temp**: hottest base cell under the current model
- **Spreading Delta**: `peak base temp - average base temp`

This gives a clear bridge from global to local behavior.

---

## 14. Testing Plan

Add tests in `tests/test_heatsinks.py`.

### 14.1 Full-Footprint Uniform Source

When the source footprint covers the entire base:
- field should be nearly uniform,
- `peak_base_temperature - mean_base_temperature` should be very small,
- mean should match the baseline base temperature within tolerance.

### 14.2 Symmetry

For a centered source on a symmetric base:
- temperature field should be symmetric about both centerlines.

### 14.3 Source Area Trend

Holding total power fixed:
- decreasing source area should increase peak temperature,
- average base temperature should change much less than peak temperature.

### 14.4 Material / Thickness Trend

Holding everything else fixed:
- increasing base thickness should reduce spreading delta,
- increasing thermal conductivity should reduce spreading delta.

### 14.5 Position Trend

Move the source toward an edge:
- the hotspot should move accordingly,
- the field should become visibly asymmetric.

### 14.6 Energy Balance

Check that:

```text
sum(G_sink,ij * (T_ij - T_ambient)) ~= total_source_power
```

within a small tolerance.

### 14.7 Convergence Guard

Verify the solver:
- converges for nominal cases,
- raises a clear error for invalid geometry or impossible inputs.

---

## 15. Validation Strategy

This feature should be validated in stages:

### Stage 1: Internal Consistency

- symmetry,
- monotonic trends,
- energy balance,
- convergence stability.

### Stage 2: Cross-Check Against Existing Scalar Spreading Resistance

For centered single-source cases:
- compare the source-region average base rise from the field solver to the scalar `rectangular_spreading_resistance()` result,
- expect the same trend and similar magnitude,
- do not require exact equality because the models are not identical.

### Stage 3: Qualitative Comparison Against External Tools

Compare shape and trend, not absolute CFD fidelity:
- source gets smaller -> hotspot intensifies,
- source moves off-center -> field skews,
- thicker base -> contour smooths out,
- higher conductivity -> contour smooths out.

---

## 16. Recommended Implementation Order

### Phase 1: Backend Solver ✓ (completed 2026-03-20)

1. ✓ Create `pycalcs/heatsink_spreading.py`.
2. ✓ Add source data structure.
3. ✓ Add grid builder and source overlap helper.
4. ✓ Add distributed sink-weight builder.
5. ✓ Add Gauss-Seidel / SOR field solver.
6. ✓ Add derived summary metrics.
7. ✓ Add tests.

### Phase 2: Preview Overlay ✓ (completed 2026-03-20)

1. ✓ Draw source rectangle in the existing top-view SVG.
2. ✓ Add source position controls (expert mode for x/y).
3. ✓ Add empty-state logic if source size is zero.
4. ✓ Promote source length/width to default-visible Geometry section.

### Phase 3: Spread View Tab ✓ (completed 2026-03-20)

1. ✓ Add tab shell with empty-state message.
2. ✓ Add Plotly heatmap render function with source rectangle overlays.
3. ✓ Add centerline plot renderers (x and y).
4. ✓ Add summary cards (avg base, peak base, spreading ΔT, est. peak junction).
5. ✓ Add assumptions note.
6. ✓ Add absolute/rise display mode toggle.
7. ✓ Load `heatsink_spreading.py` in Pyodide bootstrap.

### Phase 4: Optional Result Integration

1. Decide whether to expose local hotspot metrics in the main results grid.
2. Decide whether to replace scalar spreading penalty in the headline thermal stack.

---

## 17. Recommended Minimum Slice

If implementation time is tight, do this and stop:

1. Keep the current global solver untouched.
2. Add a centered single-source overlay to the top-view preview.
3. Add a new Python field solver called only after a successful baseline solve.
4. Add a Spread View tab with:
   - heatmap,
   - source overlay,
   - average base temp,
   - peak base temp,
   - spreading delta.

That is enough to materially improve the tool.

---

## 18. Future Extensions

Do not build these in the first pass, but keep the design ready for them:

- multiple simultaneous sources,
- fin-root-weighted sink conductance map,
- source arrays,
- component presets,
- local TIM variation,
- mounting holes / keep-out regions,
- simple transient animation from an RC network,
- exportable contour snapshot,
- direct use of local source metrics in the main pass/fail decision.

---

## 19. Open Questions — Resolved

1. **Should source size become a default visible input for all users?**
   **Yes.** Source length and width already exist in expert mode. Promote them to the default Geometry input section. A heatsink analysis without a source footprint is incomplete — this is the single most common oversight in early thermal design.

2. **Should source position be visible by default or expert-only?**
   **Expert-only.** Most users have a centered source. Showing x/y position by default adds clutter for the 80% case. Expert mode reveals it.

3. **Should Spread View be available only when source dimensions are defined?**
   **Always visible, with an empty state.** When source size is zero or undefined, show: "Set a source footprint (length and width) to see localized base spreading." This is better for discoverability than hiding the tab.

4. **In later phases, should the reported source/junction temperature use source-average or source-peak?**
   **Source-average for the primary thermal stack.** Show source-peak as a separate hotspot warning metric. This matches how datasheet thermal limits are specified (junction average), while the peak gives a safety check.

---

## 20. Implementation Notes (added 2026-03-20)

### Performance in Pyodide

The 41×25 Gauss-Seidel grid produces ~1000 cells. At up to 4000 iterations that is ~4M cell updates in pure Python. Expected wall time in Pyodide: 2–5 seconds. Mitigations:
- SOR with omega = 1.4 should converge most cases in 500–1500 iterations.
- Add a "Computing spread..." indicator in the UI so the user knows work is happening.
- If convergence is reached early, break immediately — do not iterate to `max_iterations`.

### Source Clamping

When a source rectangle extends outside the base footprint, **clamp** the overlap to the base boundary rather than raising an error. Add a warning to the returned `assumptions` list: "Source extends beyond base edge; only the overlapping region contributes heat." This is more forgiving for users experimenting with off-center positions.

### Module Loading

The new `pycalcs/heatsink_spreading.py` module must be fetched in the Pyodide bootstrap (same pattern as `utils.py` and `heatsinks.py`), with the same `?v=${Date.now()}` cache-busting suffix.

---

## 21. Bottom Line

This feature should be treated as a **source-awareness upgrade**, not as cosmetic chart work.

The current tool already answers:
- "Is this sink globally good enough?"

This feature adds the missing question:
- "Where is the hot spot, and how badly does source spreading hurt me?"

That is the most valuable gap to close if the current heatsink designer still feels flat.
