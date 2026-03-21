# Heatsink Designer Roadmap

This roadmap is the implementation contract for the heatsink rewrite.
For the full audit and detailed implementation plan, see:
- `plans/heatsink_designer_full_audit.md` — Complete item register
- `plans/heatsink_designer_implementation_plan.md` — Sequenced implementation guide

## Phase 1: Solver Foundation ✓

- [x] Create a dedicated task branch for the rewrite
- [x] Replace the old generic README with a heatsink-specific product definition
- [x] Build a new `pycalcs/heatsinks.py` module for plate-fin steady-state analysis
- [x] Add unit tests for geometry, convection, fin efficiency, pressure drop, and fan operating points
- [x] Keep the old local `thermal_calc.py` out of the new implementation path

## Phase 2: New Tool UI (partially complete)

- [x] Rebuild `tools/simple_thermal/index.html` from `tools/example_tool_advanced/index.html`
- [x] Add a default workflow for required sink resistance and basic heatsink analysis
- [x] Add expert mode for secondary resistances, emissivity, and fan parameters
- [x] Add derivation panels for every primary result card
- [x] Add a loading overlay, settings panel, and theme support
- [x] Fix expert mode toggle positioning (C9)
- [x] Fix dark mode accent color contrast (C10)
- [x] Convert geometry inputs to millimeters (C1)
- [x] Add stale results indicator (C6)
- [x] Add inline input validation (C3)
- [x] Consistent event binding — remove inline onclick handlers (D4)
- [x] Keyboard accessibility for derivation panels (D6)
- [x] Add footer with attribution and Ko-fi link (C14)
- [ ] Extract JS to separate file (D1)

## Phase 3: Accuracy Improvements

- [x] Fix friction factor consistency — use Petukhov for both Nu and ΔP in turbulent branch (A5)
- [x] Improve air thermal conductivity fit for elevated temperatures (A7)
- [x] Add fin-to-fin radiation view factor correction (A10)
- [x] Estimate induced velocity under natural convection (A6)
- [x] Add heatsink orientation input with horizontal correlations (A3)
- [x] Add spreading resistance model for undersized source footprints (A1)
- [x] Add airflow bypass model for unducted configurations (A2)
- [x] Add mixed convection Richardson number warning (A4)
- [x] Support optional piecewise-linear fan curve (A9)

## Phase 4: Visual Analysis & Sensitivity

- [x] Geometry sketch with labeled dimensions
- [x] Thermal-resistance ladder from junction to ambient
- [x] Show fin spacing dimension in geometry preview (C5)
- [x] Fan curve vs. heatsink pressure-drop curve plot (B3)
- [x] 1D sensitivity sweep tab (B1)
- [x] 2D trade-space contour tab (B2)
- [x] Auto-calculate with debounce (C2)
- [x] Required vs achieved Rθ comparison indicator (C7)
- [x] Fin efficiency displayed as percentage (C8)
- [x] Actionable recommendations with specific parameter suggestions (C12)
- [x] Empty chart state guidance (C11)
- [x] Tablet layout breakpoint refinement (C4)

## Phase 5: Background Depth & Testing

- [x] Build a deep background tab with numbered sections and variable legends
- [x] Add worked examples for natural and fan-assisted designs (B5)
- [x] Document validity limits of each convection/pressure-drop correlation
- [ ] Add validation notes comparing tool outputs against reference examples
- [x] Absolute accuracy benchmark tests against published data (E1/A8)
- [x] Turbulent flow branch test (E3)
- [x] Approach velocity conversion test (E4)
- [x] Edge case tests — extreme geometries and loads (E2)
- [x] Radiation-dominant case test (E6)
- [x] Parameter JSON test cases (B7)
- [x] MathJax loading fallback (C13)
- [ ] Pyodide timeout protection (D3) — current `withTimeout()` wraps synchronous calls with `setTimeout`, which cannot interrupt a blocked main thread. A Web Worker is needed for real preemptive timeout.

## Phase 6: Advanced Extensions

- [x] Exportable design summary — JSON/CSV export (B6)
- [x] Fan curve vs. heatsink pressure-drop curve plot (B3)
- [ ] Geometry sweep plots (B4) — covered by 1D sweep tab
- [ ] Additional geometries (pin fin, radial fin) — future
- [ ] HTML smoke test with Playwright (E5) — future

## Phase 7: Source-Aware Spreading Visualization

- [x] Create `pycalcs/heatsink_spreading.py` — 2D Gauss-Seidel/SOR base-plane solver
- [x] Add `analyze_heatsink_spreading_view()` orchestrator in `heatsinks.py`
- [x] Add spreading solver tests (symmetry, energy balance, convergence, trend)
- [x] Promote source length/width from expert-only to default Geometry inputs
- [x] Add source position (x/y) controls in expert mode
- [x] Draw source rectangle overlay on top-view SVG preview
- [x] Add Spread View tab with Plotly heatmap, source overlay shapes
- [x] Add centerline temperature plots (x and y)
- [x] Add summary metrics strip (avg base, peak base, spreading ΔT, est. peak junction)
- [x] Add absolute/rise display mode toggle
- [x] Add assumptions card on Spread View tab
- [x] Load `heatsink_spreading.py` in Pyodide bootstrap with cache-busting
- [x] Add off-center source test
- [ ] Optional: expose local hotspot metrics in main results grid (Phase B)
- [ ] Optional: replace scalar spreading penalty in headline thermal stack (Phase B)

## Phase 8: Progressive Disclosure & Audit Transparency

- [x] Enrich solver return with substituted-equation strings for all primary outputs (Phase A)
- [x] Add intermediate_values dict exposing air properties, fin parameters, geometry details (Phase A)
- [x] Add dynamic assumptions list in solver output (Phase A)
- [x] Add correlation_details dict with name/reference/validity for each model (Phase A)
- [x] Add derivation panels for case temperature, base temperature, channel velocity (Phase B)
- [x] Add correlation detail lines in pressure drop, fin efficiency, radiation panels (Phase D)
- [x] Populate assumptions card on Results tab from solver output (Phase D)
- [x] Show correlation details in heat split derivation section (Phase D)
- [x] Rewrite Background tab: 9 sections → 18 with full equations, validity, references (Phase C)
- [x] Add comprehensive references with DOIs and section cross-references (Phase C)
- [x] Enrich all parameter docstrings with typical ranges and sensitivity guidance (Phase E)
- [x] Add tooltip triggers to all inputs including source, orientation, ducted (Phase E)

## Guardrails

- Every new equation must trace to a named reference.
- Every primary output must have a substituted-equation string.
- The default experience must remain simple even as expert features are added.
- If a model assumption is weak, expose it in the UI instead of hiding it.
- Run `python3 -m pytest tests/test_heatsinks.py -v` after every phase.
