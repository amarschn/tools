# Beam Bending Calculator — Improvement Plan

## High Priority (Safety & Core Usability)

### 1. Lateral-Torsional Buckling (LTB) Check
The tool checks bending stress and deflection but not LTB, which is a common governing failure mode for steel I-beams with long unbraced lengths.
- Add an **unbraced length** input (Lb) to the Material or Geometry tab
- Compute Lp (plastic limit) and Lr (inelastic limit) per AISC Chapter F
- Compute nominal moment capacity Mn considering LTB (plastic, inelastic, elastic buckling zones)
- Add an LTB utilization gauge alongside the existing stress and deflection gauges
- Show Cb (moment gradient factor) calculation — default to 1.0 with option to override
- Display which zone governs (plastic, inelastic LTB, elastic LTB)
- **Files:** `pycalcs/beam_analysis.py` (add LTB functions), `tools/beam-bending/index.html` (UI + display)

### 2. Shear & Moment Diagrams
The Diagram tab only shows beam configuration and deflected shape. V(x) and M(x) diagrams are fundamental.
- Add shear force diagram SVG below the deflected shape in the Diagram tab
- Add bending moment diagram SVG below the shear diagram
- Draw with proper sign conventions (positive moment = sagging, positive shear per beam convention)
- Label key values: reactions, max/min moments, zero-crossing points
- Use the existing `curve` data (already has `moment` and `shear` at each x-point)
- Shade positive/negative regions with different colors
- **Files:** `tools/beam-bending/index.html` (new `drawShearDiagram()` and `drawMomentDiagram()` functions)

### 3. Partial Distributed Loads
Only full-span UDL is currently supported. Real loads often cover a portion of the span.
- Add a partial UDL load case: uniform load from position `a` to position `b`
- In Advanced mode, each distributed load entry gets start/end position inputs
- Python backend: add `_compute_simply_supported_partial_udl()` and similar for other support types
- Use superposition or direct integration for the closed-form solution
- Update beam preview SVG to show partial load extent
- **Files:** `pycalcs/beam_analysis.py`, `tools/beam-bending/index.html`

### 4. Dark Mode Contrast Fixes
The accent color swap (`#111827` light to `#f9fafb` dark) creates low-contrast text in several places.
- Audit all `body[data-theme="dark"]` overrides for WCAG AA contrast ratios (4.5:1 for text)
- Fix `.mode-btn.active` text color in dark mode (currently invisible)
- Fix status banner text contrast in dark mode
- Fix accent-colored borders and small text elements
- **Files:** `tools/beam-bending/index.html` (CSS dark mode section)

### 5. Self-Weight Inclusion
Beam weight is computed from section area and material density but not included in loading.
- Add a "Include self-weight" toggle/checkbox in the Loading tab
- When enabled, automatically add `w_self = rho * A * g` to the distributed load
- In Advanced mode, add self-weight as a separate read-only load entry
- Display the self-weight value so users can verify it
- **Files:** `pycalcs/beam_analysis.py` (compute self-weight), `tools/beam-bending/index.html` (toggle + display)

---

## Medium Priority (Feature Completeness)

### 6. Expanded AISC Section Database
Only 8 W-shapes are currently available. Engineers need a broader selection.
- Add common C-channels (C10x15.3, C12x20.7, etc.)
- Add HSS/tube sections (HSS6x6x1/4, HSS8x4x1/2, etc.)
- Add S-beams (S8x18.4, S12x31.8, etc.)
- Add angles (L4x4x1/4, L6x4x3/8, etc.)
- Organize by category in the dropdown with optgroups
- Store properties in a JS object or fetch from a JSON file
- Consider adding a search/filter for the section selector
- **Files:** `tools/beam-bending/index.html` (section database + UI)

### 7. Applied Moment Loads
Concentrated moments (torques) at a point are a standard load case in Roark's.
- Add "Concentrated Moment" as a load type option
- Python: add `_compute_simply_supported_moment()` and variants for other supports
- Beam preview: draw moment as a curved arrow at the application point
- Available in both Simple mode (new dropdown option) and Advanced mode (load type)
- **Files:** `pycalcs/beam_analysis.py`, `tools/beam-bending/index.html`

### 8. Asymmetric Stress Reporting
For T-sections and C-channels, the tool reports `max_stress` but doesn't indicate which fiber is critical.
- Display both `stress_top` and `stress_bottom` in results (already computed in Python)
- Label which is tension and which is compression
- For asymmetric sections, show both in the results grid as separate cards
- Indicate which fiber governs the design
- **Files:** `tools/beam-bending/index.html` (results display)

### 9. PDF Export Completion
jsPDF is imported but the export may need refinement for professional use.
- Ensure PDF includes: input summary, section properties table, results table, safety checks
- Capture beam diagram SVG and charts as images
- Add company/project name fields for the report header
- Include analysis assumptions and limitations disclaimer
- Format with proper pagination for multi-page reports
- **Files:** `tools/beam-bending/index.html` (`exportPDF()` function)

### 10. Analysis Assumptions Disclosure
Engineers need to know the limits of the analysis.
- Add a visible disclaimer section (always shown, not collapsed) stating:
  - Linear elastic analysis (small deflections assumed)
  - Prismatic beam (constant cross-section along length)
  - No lateral-torsional effects (unless LTB check is added)
  - No shear deformation (Euler-Bernoulli, not Timoshenko)
  - Not a substitute for code-compliant design
- Show in the Results tab and include in PDF export
- **Files:** `tools/beam-bending/index.html`

---

## Lower Priority (Polish & Advanced Features)

### 11. Section Sizing Optimizer
"Find the smallest W-shape that satisfies deflection and stress limits."
- Add an "Auto-size" button or mode
- Iterate through the section database for the selected material
- Filter by stress utilization < 1.0 and deflection utilization < 1.0
- Rank by weight (lightest passing section wins)
- Display top 3-5 candidates with their utilization ratios
- **Files:** `tools/beam-bending/index.html` (optimizer UI + logic), `pycalcs/beam_analysis.py` (batch analysis)

### 12. Load Combinations (LRFD/ASD)
Real structural design uses factored load combinations.
- Allow users to tag loads as Dead (D), Live (L), Wind (W), etc.
- Compute standard combinations: 1.4D, 1.2D+1.6L, 1.2D+1.0W+L, etc. per ASCE 7
- Report governing combination and its utilization
- **Files:** `pycalcs/beam_analysis.py`, `tools/beam-bending/index.html`

### 13. Continuous / Multi-Span Beams
At least 2-span continuous beam support.
- Add support type "Continuous (2-span)" and "Continuous (3-span)"
- Use three-moment equation (Clapeyron's theorem) or stiffness method
- Show reactions at all supports, moment diagram with hogging at interior supports
- **Files:** `pycalcs/beam_analysis.py` (new solver), `tools/beam-bending/index.html`

### 14. Pyodide Caching via Service Worker
Currently re-downloads the full Python environment on every page load (~3.5s).
- Add a service worker that caches Pyodide WASM files
- Subsequent loads should be near-instant from cache
- **Files:** New `tools/beam-bending/sw.js`, update `index.html` to register it

### 15. Mobile Compact Density
Auto-apply compact density on narrow viewports.
- Add a CSS media query that applies `body[data-density="compact"]` styles at `max-width: 768px`
- Or apply via JS in the responsive breakpoint handler
- **Files:** `tools/beam-bending/index.html` (CSS responsive section)

---

## Code Quality Improvements

### Refactor `calculate()` Function
Split the ~100-line `calculate()` into `calculateSimple()` and `calculateAdvanced()` with shared result handling.

### Extract SVG Layout Constants
`margin = 60`, `width = 600`, `beamY = 90/100` are duplicated across `drawBeamPreview()`, `drawBeamDiagram()`, and `drawDeflectionDiagram()`. Extract to a shared `DIAGRAM_LAYOUT` constant.

### Memoize Section Diagram
`generateSectionDiagram()` rebuilds the full SVG on every keystroke. Cache the SVG and only regenerate when the section type or dimensions actually change.

### Consolidate Format Functions
`formatNumber()`, `formatCompact()`, `formatEngineering()`, and `formatAuto()` have overlapping purposes. Simplify to fewer functions with clearer responsibilities.
