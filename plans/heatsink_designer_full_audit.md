# Heatsink Designer — Full Audit & Improvement Register

This document is the authoritative record of every identified improvement for the heatsink designer tool. Each item has a unique ID, category, priority, effort estimate, and acceptance criteria. The companion document `heatsink_designer_implementation_plan.md` provides the sequenced implementation guidance.

---

## Item Index

| ID | Category | Title | Priority | Effort | Status |
|----|----------|-------|----------|--------|--------|
| A1 | Accuracy | Spreading resistance model | High | Large | **Done** |
| A2 | Accuracy | Airflow bypass model | High | Large | **Done** |
| A3 | Accuracy | Heatsink orientation input | High | Medium | **Done** |
| A4 | Accuracy | Mixed convection regime | Medium | Medium | **Done** |
| A5 | Accuracy | Friction factor consistency (turbulent branch) | High | Small | **Done** |
| A6 | Accuracy | Natural convection induced velocity estimate | Low | Small | **Done** |
| A7 | Accuracy | Improved air thermal conductivity fit | Medium | Small | **Done** |
| A8 | Accuracy | Validation against reference benchmarks | High | Large | **Done** |
| A9 | Accuracy | Non-parabolic fan curve model | Medium | Medium | **Done** |
| A10 | Accuracy | Fin-to-fin radiation view factor correction | High | Medium | **Done** |
| B1 | Feature | 1D sensitivity sweep | High | Large | **Done** |
| B2 | Feature | 2D trade-space contour | High | Large | **Done** |
| B3 | Feature | Fan curve vs system curve plot | Medium | Medium | **Done** |
| B4 | Feature | Geometry sweep plots | Medium | Medium | Open |
| B5 | Feature | Worked examples in Background tab | Medium | Medium | **Done** |
| B6 | Feature | Exportable design summary | Medium | Medium | **Done** |
| B7 | Feature | Parameter JSON test cases | Low | Small | **Done** |
| C1 | UI/UX | Millimeter units for geometry inputs | High | Small | **Done** |
| C2 | UI/UX | Auto-calculate / live results | High | Medium | **Done** |
| C3 | UI/UX | Inline input validation | Medium | Medium | **Done** |
| C4 | UI/UX | Tablet layout breakpoint refinement | Low | Small | **Done** |
| C5 | UI/UX | Show fin spacing in geometry preview | Medium | Small | **Done** |
| C6 | UI/UX | Stale results indicator | High | Small | **Done** |
| C7 | UI/UX | Required vs achieved Rθ comparison indicator | Medium | Small | **Done** |
| C8 | UI/UX | Fin efficiency displayed as percentage | Low | Small | **Done** |
| C9 | UI/UX | Fix expert mode toggle positioning | Medium | Small | **Done** |
| C10 | UI/UX | Dark mode link/accent color contrast | Medium | Small | **Done** |
| C11 | UI/UX | Empty chart state guidance | Low | Small | **Done** |
| C12 | UI/UX | Actionable recommendations | Medium | Medium | **Done** |
| C13 | UI/UX | MathJax loading fallback | Low | Small | **Done** |
| C14 | UI/UX | Footer with attribution and Ko-fi link | Low | Small | **Done** |
| D1 | Code | Extract JS from single HTML file | Medium | Medium | Open |
| D2 | Code | SVG rendering refactor | Low | Medium | Open |
| D3 | Code | Pyodide timeout protection | Medium | Small | **Done** |
| D4 | Code | Consistent event binding (no inline handlers) | Low | Small | **Done** |
| D5 | Code | Simplify normalizeNestedDict | Low | Small | Open |
| D6 | Code | Keyboard accessibility for derivation panels | Medium | Small | **Done** |
| E1 | Testing | Absolute accuracy benchmark tests | High | Large | **Done** |
| E2 | Testing | Edge case tests (extreme geometries) | Medium | Medium | **Done** |
| E3 | Testing | Turbulent flow branch test | High | Small | **Done** |
| E4 | Testing | Approach velocity conversion test | Medium | Small | **Done** |
| E5 | Testing | HTML smoke test (Playwright) | Low | Large | Open |
| E6 | Testing | Radiation-dominant case test | Medium | Small | **Done** |

---

## Detailed Item Descriptions

### A1 — Spreading Resistance Model

**Problem:** The solver assumes the heatsink base is isothermal. When the heat source mounting pad is smaller than the base, thermal spreading resistance adds a non-negligible temperature rise between the contact area and the far edges of the base. This can cause the tool to underpredict base temperature by 10–30% in common electronics layouts.

**Root cause:** The current `analyze_plate_fin_heatsink()` function models the entire base as one lumped node.

**Acceptance criteria:**
- New function `spreading_resistance(source_width, source_length, base_width, base_length, base_thickness, conductivity)` using the Lee et al. (1995) or Yovanovich (1998) analytical spreading resistance model.
- Two new UI inputs: source footprint width and length (default to base dimensions, making spreading resistance zero by default for backwards compatibility).
- Spreading resistance appears as a separate node in the thermal path diagram.
- Unit test comparing against a published example from Yovanovich.

**Key references:**
- Yovanovich, M. M., Muzychka, Y. S., Culham, J. R. (1999). Spreading Resistance of Isoflux Rectangles and Strips on Compound Flux Channels.
- Lee, S., Song, S., Au, V., Moran, K. P. (1995). Constriction/Spreading Resistance Model for Electronics Packaging. ASME/JSME Thermal Engineering Conference.

---

### A2 — Airflow Bypass Model

**Problem:** In unducted configurations, not all forced air passes through the fin channels. Some fraction bypasses around the heatsink. Ignoring this overpredicts the effective flow through the fins and underpredicts thermal resistance.

**Root cause:** `forced_convection_plate_array()` uses the full volumetric flow rate as if the heatsink is fully ducted.

**Acceptance criteria:**
- New UI toggle: "Ducted" vs "Unducted" (default: Ducted, preserving current behavior).
- When unducted, apply bypass fraction estimation based on the Azar & Tavassoli (2003) bypass model or a simple first-order correction: `Q_through = Q_total * (1 - bypass_fraction)` where bypass fraction is a function of fin density, fin height, and approach velocity.
- Alternatively, use Simons' (2004) bypass flow estimation method for parallel plate arrays.
- Unit test verifying that unducted mode predicts higher thermal resistance than ducted mode for the same approach velocity.

**Key references:**
- Azar, K., Tavassoli, B. (2003). How Much Heat Can Be Extracted from a Heat Sink? Electronics Cooling.
- Simons, R. E. (2004). Estimating the Effect of Flow Bypass on Parallel Plate-Fin Heat Sink Performance. Electronics Cooling.

---

### A3 — Heatsink Orientation Input

**Problem:** The Bar-Cohen/Rohsenow natural convection correlation assumes vertical parallel plates. Horizontal orientations (fins pointing up, fins pointing down, or fins horizontal) use completely different correlations and can have dramatically different performance.

**Acceptance criteria:**
- New select input: "Orientation" with options: Vertical (default), Horizontal fins up, Horizontal fins down.
- For vertical: use existing Bar-Cohen/Rohsenow.
- For horizontal fins up: use Harahap & McManus (1967) or similar correlation.
- For horizontal fins down: use a reduced-performance correlation or warning.
- Natural convection function dispatches to the appropriate correlation based on orientation.
- Unit test verifying horizontal-up gives different (typically lower) performance than vertical for the same geometry.

**Key references:**
- Harahap, F., McManus, H. N. (1967). Natural Convection Heat Transfer from Horizontal Rectangular Fin Arrays. ASME J. Heat Transfer.
- Starner, K. E., McManus, H. N. (1963). An Experimental Investigation of Free-Convection Heat Transfer from Rectangular-Fin Arrays.

---

### A4 — Mixed Convection Regime

**Problem:** When low forced airflow and significant buoyancy coexist, the current tool forces a binary choice between natural and forced. Real designs often operate in the mixed regime.

**Acceptance criteria:**
- When forced mode is selected and the Richardson number (Gr/Re²) exceeds 0.1, display an informational callout noting that buoyancy effects may be significant.
- Optionally implement an assisting-flow mixed convection combination: `Nu_mixed = (Nu_forced^n + Nu_natural^n)^(1/n)` where n=3 (Churchill & Usagi correlation).
- This can be gated behind expert mode.

---

### A5 — Friction Factor Consistency (Turbulent Branch)

**Problem:** In the turbulent forced convection branch (`forced_convection_plate_array`, lines 386–397), the Darcy friction factor for pressure drop uses Blasius (`0.3164 * Re^-0.25`) but the Gnielinski Nusselt correlation uses the Petukhov friction factor (`(0.79 * ln(Re) - 1.64)^-2`). The Gnielinski correlation is designed to use the Petukhov friction factor for both heat transfer AND pressure drop.

**Fix:** Use the Petukhov friction factor for both the Nusselt number calculation and the pressure drop calculation in the turbulent branch. Remove the Blasius line.

**Acceptance criteria:**
- Single friction factor variable used for both Nu and ΔP in the turbulent branch.
- Existing tests still pass (may need tolerance adjustments).
- New test: at Re=10000, verify friction factor matches Petukhov within 1%.

---

### A6 — Natural Convection Induced Velocity Estimate

**Problem:** Under natural convection, the tool returns `channel_velocity = 0.0` and `volumetric_flow_rate = 0.0`. The buoyancy-driven flow does have an effective induced velocity that can be back-calculated.

**Fix:** After computing the natural convection coefficient, estimate the induced velocity from the heat balance: `V_induced ≈ Q / (rho * cp * A_channel * ΔT_air_rise)` or use the chimney flow approximation.

**Acceptance criteria:**
- Natural convection results include non-zero `channel_velocity` and `volumetric_flow_rate`.
- Values are physically reasonable (order of 0.1–0.5 m/s for typical heatsinks).

---

### A7 — Improved Air Thermal Conductivity Fit

**Problem:** `k_air = 0.0241 * (T/273.15)^0.9` is a single-term fit that drifts at elevated film temperatures above ~150°C.

**Fix:** Replace with a two-term polynomial or use the Sutherland-type fit for thermal conductivity: `k = 0.0241 * (T/273.15)^0.81` or a quadratic in temperature.

**Acceptance criteria:**
- Air thermal conductivity at 500 K matches NIST data within 2%.
- All existing tests pass.

---

### A8 — Validation Against Reference Benchmarks

**Problem:** No test compares the combined solver output against a known benchmark. The tool could be systematically biased and we wouldn't know.

**Acceptance criteria:**
- At least 3 benchmark test cases:
  1. Natural convection: compare against a published Bar-Cohen example or manufacturer datasheet (e.g., Wakefield 621K heatsink).
  2. Forced convection: compare against a known textbook example (Incropera Chapter 3 extended surface example or Simons 2003 worked example).
  3. Fan curve: compare against a published fan + heatsink pairing from a manufacturer application note.
- Each benchmark test asserts the predicted thermal resistance is within 15% of the reference value.
- Document the reference source in the test docstring.

---

### A9 — Non-Parabolic Fan Curve Model

**Problem:** Real fan curves are not parabolic. Many axial fans have a stall region and a flattened shutoff region.

**Acceptance criteria:**
- Support an optional piecewise-linear fan curve input (array of [flow, pressure] points).
- The parabolic model remains as a convenience default.
- Linear interpolation between provided points.
- Fan curve plot (B3) can render both the parabolic model and user-supplied data.

---

### A10 — Fin-to-Fin Radiation View Factor Correction

**Problem:** The linearized radiation calculation assumes all fin surface area radiates to a large enclosure at ambient temperature (view factor = 1). In reality, closely spaced fins radiate primarily at adjacent fins, which are at nearly the same temperature. This significantly overpredicts radiation heat transfer for tightly spaced fins.

**Fix:** Apply a view factor correction to the radiation coefficient based on the fin channel aspect ratio (H/s). For deeply recessed channels (H/s > 3), radiation is heavily attenuated.

**Acceptance criteria:**
- New function `fin_channel_radiation_view_factor(fin_height, fin_spacing)` returning an effective view factor for the channel.
- Radiation coefficient is multiplied by this factor before being used in the solver.
- For widely spaced fins (H/s < 1), factor should be near 1.0.
- For tightly spaced fins (H/s > 5), factor should be significantly reduced (0.2–0.4 range).
- Unit test verifying monotonic decrease of view factor with increasing H/s.

**Key reference:**
- Sparrow, E. M., Cess, R. D. (1978). Radiation Heat Transfer. Provides view factor expressions for parallel plate channels.

---

### B1 — 1D Sensitivity Sweep

See `plans/heatsink_sensitivity_analysis.md` for the full specification. This is the single most important feature addition.

**Acceptance criteria:**
- `get_heatsink_sweep_metadata()` function in `pycalcs/heatsinks.py`.
- `run_heatsink_1d_sweep()` function with the return shape specified in the plan.
- New "1D Sweep" tab in the UI, disabled until a baseline calculation succeeds.
- Parameter selector, range presets (±20%, ±50%, Custom), output metric selector.
- Plotly line chart with baseline marker and best-value marker.
- Summary cards for sensitivity magnitude and limit crossings.
- Unit tests for metadata integrity, sweep output shape, and monotonicity.

---

### B2 — 2D Trade-Space Contour

See `plans/heatsink_sensitivity_analysis.md` for the full specification.

**Acceptance criteria:**
- `run_heatsink_2d_contour()` function with the return shape specified in the plan.
- New "2D Trade Space" tab, disabled until baseline succeeds.
- X-parameter and Y-parameter selectors, output metric selector, grid resolution control.
- Plotly contour/heatmap with baseline marker and best feasible point marker.
- Optional infeasible-region overlay.
- Unit tests for output shape, baseline point location, and constraint masking.

---

### B3 — Fan Curve vs System Curve Plot

**Acceptance criteria:**
- When in fan_curve mode, render a Plotly chart showing:
  - Fan curve (pressure vs flow rate).
  - System curve (heatsink pressure drop vs flow rate).
  - Operating point marker at the intersection.
- This should appear in the results area or as an additional chart on the Heat Split tab.
- Uses the same theme-aware styling as existing Plotly charts.

---

### B4 — Geometry Sweep Plots

**Acceptance criteria:**
- Quick single-variable sweeps of fin_count, fin_height, and fin_spacing showing thermal resistance on the y-axis.
- Can be implemented as a lightweight version of B1 or as a standalone visualization.
- Should appear on a chart area within the results panel or as part of the 1D Sweep tab.

---

### B5 — Worked Examples in Background Tab

**Acceptance criteria:**
- At least two complete worked examples added to the Background tab:
  1. Natural convection example: Given a specific heatsink and heat load, walk through the entire calculation manually.
  2. Forced convection example: Same, with approach velocity specified.
- Each example shows all intermediate values and matches the tool output when the same inputs are entered.

---

### B6 — Exportable Design Summary

**Acceptance criteria:**
- "Export" button that generates a downloadable file (CSV or JSON) containing:
  - All input parameters with units.
  - All output results with units.
  - Solver metadata (correlation names, mode used).
- Stretch: PDF export with formatted equations and geometry sketch.

---

### B7 — Parameter JSON Test Cases

**Acceptance criteria:**
- At least 3 JSON files in `tools/simple_thermal/test-cases/`:
  1. `natural_convection_baseline.json` — default inputs, natural convection.
  2. `forced_convection_high_flow.json` — forced mode with high approach velocity.
  3. `fan_curve_typical.json` — fan curve mode with typical small axial fan.
- Each file follows the project's parameter JSON test case format per AGENTS.md.

---

### C1 — Millimeter Units for Geometry Inputs

**Problem:** Geometry inputs are in meters. Users must enter `0.001` for a 1mm fin thickness. This is error-prone and unnatural.

**Fix:** Change all geometry input labels and fields to millimeters. Convert to meters in `gatherInputs()` before calling the Python solver. The Python API stays in SI meters.

**Acceptance criteria:**
- Labels read "Base Length (mm)", "Fin Height (mm)", etc.
- Default values updated: e.g., `100` instead of `0.10`, `1.0` instead of `0.001`.
- `gatherInputs()` divides by 1000 before passing to Python.
- Geometry preview notes show mm values.
- All results that display lengths also show mm where appropriate.

---

### C2 — Auto-Calculate / Live Results

**Problem:** Users must click Calculate manually after every input change, but geometry previews update live. This creates an inconsistent experience.

**Fix:** Debounce input changes (300–500ms) and auto-run the calculation when all inputs are valid.

**Acceptance criteria:**
- Calculation triggers automatically after input changes (debounced).
- The Calculate button remains as a manual override.
- While auto-calculating, show a subtle spinner or "Updating..." indicator.
- If auto-calculation produces an error, show the error inline without disrupting the form.

---

### C3 — Inline Input Validation

**Acceptance criteria:**
- Each numeric input validates on blur and on change.
- Invalid values get a red border and a brief error message below the input.
- The Calculate button is disabled while any input is invalid.
- Validation rules: positive numbers, fin_count >= 2, base_width > fin_count * fin_thickness, emissivity in (0,1], etc.

---

### C4 — Tablet Layout Breakpoint Refinement

**Fix:** Change the 1024px breakpoint to keep the two-column layout at tablet widths, collapsing to single-column only below ~768px. The geometry previews should remain adjacent to the inputs at tablet widths.

---

### C5 — Show Fin Spacing in Geometry Preview

**Fix:** Add a dimension line for fin spacing `s` in the front-view SVG, showing it between two adjacent fins. This is the most important derived dimension for natural convection.

---

### C6 — Stale Results Indicator

**Fix:** When any input changes after a calculation, overlay a subtle "Results outdated — recalculate" banner on the results panel, or dim the results grid.

**Acceptance criteria:**
- Any input change after a successful calculation triggers the stale indicator.
- The indicator clears when a new calculation completes.
- If auto-calculate (C2) is implemented, the stale indicator appears during the debounce delay.

---

### C7 — Required vs Achieved Rθ Comparison Indicator

**Fix:** Add a visual comparison between the two Rθ cards: a check mark (green) if achieved ≤ required, a warning icon (red) if achieved > required.

---

### C8 — Fin Efficiency as Percentage

**Fix:** Display fin efficiency as `94.2%` instead of `0.942`. Update the result card and any metric strips.

---

### C9 — Fix Expert Mode Toggle Positioning

**Problem:** The toggle knob (`::after` pseudo-element) uses `position: absolute` without a positioned ancestor, so positioning is fragile.

**Fix:** Add `position: relative` to the `.expert-toggle` element.

---

### C10 — Dark Mode Link/Accent Color Contrast

**Problem:** In dark mode, `--accent-color` is `#f9fafb` (near-white), making links indistinguishable from body text.

**Fix:** Set `--accent-color` in dark mode to a distinct, accessible color like `#60a5fa` (blue-400) that provides sufficient contrast against the dark background.

---

### C11 — Empty Chart State Guidance

**Fix:** When the Temperature Ladder or Heat Split tabs are opened before any calculation, show a centered placeholder message: "Run a calculation to see this chart."

---

### C12 — Actionable Recommendations

**Fix:** Make recommendations parameter-specific. Instead of "Reduce heat load or increase heatsink surface area and airflow", say "Try increasing fin count from 10 to 14, or switching to forced convection." Use the actual input values to generate concrete suggestions.

---

### C13 — MathJax Loading Fallback

**Fix:** If MathJax fails to load within 10 seconds, hide equation boxes and show a plain-text fallback message.

---

### C14 — Footer with Attribution

**Fix:** Add a footer element with:
- "Transparent Tools" branding.
- Link to the Ko-fi page.
- Link back to the tools hub.

---

### D1 — Extract JS from Single HTML File

**Fix:** Move the `<script>` block (lines 1579–2582) into a separate `heatsink-designer.js` file. Reference it with `<script src="heatsink-designer.js"></script>`.

---

### D2 — SVG Rendering Refactor

**Fix:** Replace string-concatenation SVG building with a small helper module using `document.createElementNS()`. This is lower priority and can wait until the SVG code needs significant changes.

---

### D3 — Pyodide Timeout Protection

**Fix:** Wrap the Pyodide calculation call in a `Promise.race()` with a 30-second timeout. If the timeout fires, show an error message and re-enable the Calculate button.

---

### D4 — Consistent Event Binding

**Fix:** Replace all inline `onclick=` attributes in HTML with `addEventListener` calls in JS. Specifically: the `openTab()` calls on `.tab-link` buttons and the `toggleDerivation()` calls on result items.

---

### D5 — Simplify normalizeNestedDict

**Fix:** Use Pyodide's built-in `toJs({ dict_converter: Object.fromEntries, create_proxies: false })` to avoid the manual normalization pass. Test that the output shape is identical.

---

### D6 — Keyboard Accessibility for Derivation Panels

**Fix:** Add `tabindex="0"` and `role="button"` to clickable `.result-item` elements. Add a keydown handler for Enter and Space to trigger `toggleDerivation()`.

---

### E1 — Absolute Accuracy Benchmark Tests

See A8 for full description. These tests go in `tests/test_heatsinks.py`.

---

### E2 — Edge Case Tests

**Acceptance criteria:**
- Test with very tall fins (fin_height = 0.10 m, expect low efficiency).
- Test with very tight spacing (20 fins in 40mm width, expect high pressure drop).
- Test with very high heat load (200W, expect high base temperature).
- Test near-ambient operation (1W, expect base temperature barely above ambient).

---

### E3 — Turbulent Flow Branch Test

**Acceptance criteria:**
- Test case with volumetric_flow_rate high enough to produce Re > 2300.
- Assert that the Gnielinski Nusselt number is used (verify Nu > laminar limit for same geometry).
- Assert pressure drop uses the correct friction factor.

---

### E4 — Approach Velocity Conversion Test

**Acceptance criteria:**
- Test forced mode with `approach_velocity = 3.0` and `volumetric_flow_rate = 0.0`.
- Verify the internal flow rate equals `approach_velocity * frontal_area`.
- Verify results are physically consistent.

---

### E5 — HTML Smoke Test (Playwright)

**Acceptance criteria:**
- Playwright test that:
  1. Serves the repo with `python -m http.server`.
  2. Navigates to the heatsink tool.
  3. Waits for Pyodide to load.
  4. Clicks Calculate with default inputs.
  5. Asserts that the results grid is visible and contains numeric values.
- This is the lowest priority testing item due to infrastructure requirements.

---

### E6 — Radiation-Dominant Case Test

**Acceptance criteria:**
- Test with natural convection, high emissivity (0.9), low heat load (3W), and wide fin spacing.
- Assert that `radiation_heat_rejected > 0.3 * heat_load`.
- Assert that turning emissivity to 0.05 significantly increases base temperature.
