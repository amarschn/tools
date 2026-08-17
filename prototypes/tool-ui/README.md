# Tool UI prototypes

These pages compare four possible directions for the next Engineering Tools page template. Each page runs the same inline bolt preload calculation with the same defaults, validity checks, equations, and metadata from `meta-sample.json`. Serve the repository root over HTTP, then open `/prototypes/tool-ui/option-a/` through `/option-d/`. Fetch-based metadata will not load from a `file://` URL.

## Option A: title block

Option A borrows the controlled-document cues of an engineering drawing. A compact title block exposes the revision, publication date, author, review status, source, and revision history without pretending the prototype is approved. Numbered notes and a restrained sheet layout make provenance prominent, though the drawing language may feel too formal for quick calculators.

## Option B: datasheet

Option B treats the calculator as a standards-based worked example. Inputs and results use symbol, value, and unit columns; scope and validity are stated before the method; equations and references have permanent numbered sections. This option makes assumptions hard to miss, but it is the densest page at phone widths.

## Option C: instrument panel

Option C gives the answer the visual weight of a bench instrument while keeping the dark treatment inside the readouts. It recalculates 150 ms after a valid edit, marks displayed values stale during the debounce, shows a short updating state, and blanks every readout when an input is invalid. The immediate response works well for exploration, but the instrument styling should stay subordinate to provenance and method.

## Option D: product UI

Option D keeps the familiar two-column calculator and raises the interaction baseline. It has a simulated initialization skeleton, a sticky result column, inline validation, Enter-to-calculate, result copy buttons, visible focus rings, an on-page section rail, and a one-click changelog. It is the easiest direction to apply broadly, though its visual language is less specific to engineering work.

## Recalculation modes

Button mode is used by Options A, B, and D. Any input edit marks the current result stale; the Calculate button then moves through pending and complete states. A production template should use this mode for expensive calculations, large Pyodide calls, or tools where users benefit from editing several coupled inputs before committing a run.

Live mode is used by Option C. It validates on every edit, waits 150 ms after the last valid input, marks old values as stale, then replaces them together. Invalid input cancels pending work and replaces all numeric values with a dash. A production template should use live mode for fast, deterministic calculations with a small input set.

## Shared calculation

All options calculate tensile stress area, proof load, target preload, and tightening torque. The model uses `A_s = π/4 (d - 0.9382p)²`, `F_p = S_p A_s`, `F_i = α F_p`, and `T = K d F_i`. The default M10×1.5, class 8.8, 75% preload, and K = 0.15 case returns 57.99 mm², 37.11 kN, 27.83 kN, and 41.8 N·m. This is a screening estimate. A critical joint still needs friction scatter, tightening scatter, joint stiffness, embedding, service load, and failure-mode checks.

## Automation hooks

Each page exposes the canonical input IDs `thread`, `grade`, `preload`, and `k-factor`; output nodes use `data-output`; the calculation control uses `data-action="calculate"` where applicable. Metadata, revisions, validation, equations, background content, and input help use `data-meta`, `data-revisions`, `data-validation`, `data-equation`, `data-background`, and `data-help`. The help strings in `meta-sample.json` stand in for the docstring text used by production tools. Each `?` button is keyboard focusable and points to a `role="tooltip"` description. The root tool element carries `data-calculation="bolt-torque-v1"`, and `window.prototypeCalculator.calculateBolt()` exposes the common pure calculation for parity tests.
