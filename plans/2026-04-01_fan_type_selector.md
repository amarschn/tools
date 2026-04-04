# Fan Type Selector
Date: 2026-04-01

## Problem Statement

The existing fan-curve-explorer (branch `task/fan-curve-explorer`) answers: "Given specific fan curve data, where's the operating point?" But the **first** question engineers actually have is: **"What TYPE of fan should I even be looking at?"**

User feedback: the fan-curve-explorer is "basically total dogshit," though some pycalc equations behind it might be useful.

## Concept: Fan Type Selector

A tool that answers: "Given my flow and pressure requirement, what type of fan is optimal, and how do axial, mixed-flow, and centrifugal fans compare at my operating point?"

### Core approach: Cordier diagram + representative curve comparison

1. User enters flow rate and pressure requirement
2. Tool computes **dimensionless specific speed** (omega_s) to locate them on the **Cordier diagram** — the classic turbomachinery type selection map
3. Tool generates **representative curves for each fan type** (axial, mixed, BC centrifugal, FC centrifugal) all sized to the user's duty point — side-by-side curve shape comparison
4. **Comparison table** shows: diameter, RPM, efficiency, shaft power, tip speed (noise proxy) for each type

### Key differentiators from fan-curve-explorer
- Starts from the **requirement**, not from specific fan data
- Compares fan **types**, not specific catalog models
- Works with just flow + pressure (no curve data needed)
- Answers the "what kind?" question, not the "which model?" question

## What Exists (prototype, branch `task/fan-type-selector`)

### Python module: `pycalcs/fan_selection.py` — COMPLETE, TESTED

Core calculations, all working:

- **Specific speed/diameter** (Balje convention, dimensionless)
- **Cordier line** — polynomial fit from Balje 1981 data: `ln(δs) = 0.833 - 0.524·ln(ωs) + 0.008·(ln(ωs))²`
- **Cordier efficiency** — peak achievable η as function of ωs
- **Inverse Cordier** — binary search to find ωs from δs
- **4 fan type definitions** with metadata:
  - FC Centrifugal (ωs 0.3–1.2, η ~65%)
  - BC Centrifugal (ωs 0.3–1.5, η ~85%)
  - Mixed Flow (ωs 0.8–3.0, η ~84%)
  - Axial (ωs 2.0–8.0, η ~82%)
- **Representative curve generation** — characteristic pressure, power, and efficiency curves for each type, scaled so BEP aligns with user's duty point
- **System curve** — quadratic through duty point
- **Type comparison analysis** — suitability scoring, efficiency derating when out of range
- **`full_analysis_json()`** — single call returning all data for the UI (JSON-serializable)

#### Verified output at 1.0 m³/s, 500 Pa (unconstrained):

| Type | Diameter | RPM | Efficiency | Power | Tip Speed | Score |
|------|----------|-----|------------|-------|-----------|-------|
| BC Centrifugal | 573 mm | 703 | 85.0% | 588 W | 21.1 m/s | 85% |
| Mixed Flow | 376 mm | 1581 | 84.0% | 595 W | 31.1 m/s | 84% |
| Axial | 268 mm | 3075 | 82.0% | 610 W | 43.1 m/s | 82% |
| FC Centrifugal | 667 mm | 527 | 65.0% | 769 W | 18.4 m/s | 65% |

Trade-off is clear: centrifugal → axial = smaller impeller but faster spin (more noise).

#### Curve shape functions (normalized, x = Q/Q_free_delivery):

- **Axial:** `1 - x^1.8` (steep monotonic drop)
- **BC Centrifugal:** `1 - 0.3x - 0.7x^2.2` (gentle concave decline)
- **FC Centrifugal:** `1 + 0.3x - 0.5x^0.8 - 0.8x^2.5` (pressure hump then drop)
- **Mixed Flow:** `1 - 0.15x - 0.85x²` (between axial and centrifugal)

### HTML tool: `tools/fan-type-selector/index.html` — COMPLETE DRAFT

Full single-page tool with:
- **Sidebar inputs:** flow + unit, pressure + unit, optional constraint (none/fixed RPM/fixed diameter), air conditions (expandable)
- **Recommendation banner** at top of results
- **Comparison table** with color dots, all key metrics
- **Three tabs:**
  1. **Curve Comparison** — all 4 types' pressure-flow curves overlaid + system curve + duty point (Plotly)
  2. **Selection Map** — Cordier diagram with colored type regions, efficiency gradient, type markers (Plotly)
  3. **Type Details** — 4 cards with metrics, advantages/limitations tags, applications
- **Equations section** (expandable) — specific speed, specific diameter, Cordier line, system curve in LaTeX
- Pyodide integration, debounced live updates, dark mode, responsive

### Default experience
On load: 1.0 m³/s at 500 Pa, no constraint, 20°C sea level. Results display immediately after Pyodide loads (follows "passive-until-touched" rule).

## Known Issues / Next Steps

### Issues found during prototyping

1. **Constrained mode shows same diameter for all types** — When RPM is fixed, all types get the same ωs → same Cordier δs → same diameter. Physically correct but confusing in the table. Should also show each type's "would need" RPM/diameter at its own optimal ωs to make comparison richer.

2. **No "would need" fields yet** — When constrained, should add `type_optimal_speed` and `type_optimal_diameter` showing what each type would ideally want if unconstrained. Enables messaging like "BC Centrifugal wants ~700 RPM (you have 1500)."

3. **Not yet tested in browser** — Python module verified via CLI, HTML not yet served/tested.

4. **Not registered in catalog.json** — Needs entry for landing page.

### Potential enhancements (future)

- Power and efficiency curve tabs (data is already computed, just needs plot traces)
- Draggable duty point on the curves plot
- RPM slider that live-updates the Cordier position
- Noise estimation beyond just tip speed
- Link to fan-curve-explorer for users who then want to compare specific models
- Export comparison as CSV/PDF
- Test cases JSON file

## Relationship to fan-curve-explorer

These are complementary tools, not replacements:
- **Fan Type Selector** → "What kind of fan?" (this tool, uses Cordier diagram + representative curves)
- **Fan Curve Explorer** → "Which specific fan model?" (existing tool on `task/fan-curve-explorer`, uses real curve data)

Natural workflow: Type Selector first → narrow down to a type → Fan Curve Explorer with catalog data from that type.

The `pycalcs/fan_selection.py` module is independent of `pycalcs/fan_curves.py`. They could share air density calculation but are otherwise separate concerns.
