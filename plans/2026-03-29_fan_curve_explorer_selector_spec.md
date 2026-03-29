# Fan Curve Explorer & Selector

Date: 2026-03-29
Status: Proposed product spec — revised after external review
Supersedes: `plans/2026-03-23_fan_curve_explorer_selector_spec.md` (retained as historical reference)
Review history: Initial draft reviewed by Gemini and Codex; critiques incorporated in this revision.
Related existing assets:
- `TODO.md` ("Pump/fan selection tool that intersects system and pump curves")
- `DESIGN.md`
- `tools/example_tool_advanced/index.html`
- `plans/thermal_tool_family_future_plan.md`
- `pycalcs/heatsinks.py` (existing fan curve solver functions)

---

## 1. Purpose

Build a browser-based tool for selecting, comparing, and understanding fans.

The tool should answer two intertwined questions equally well:

> **Selection:** Given a system requirement and one or more candidate fans, where will each fan actually operate, how much power will it draw, how efficient will it be, and which is the best fit for my chosen criterion?

> **Exploration:** Given a fan (or a type of fan), how does it behave as I change the system, the speed, the density, or the duty point? What happens if I choose differently?

These two questions are not separate modes. They are the same activity viewed from different directions — analysis and design are always linked. A user who starts by selecting often ends up exploring, and a user who starts exploring eventually needs a selection answer. The tool must serve both directions fluidly without forcing users to choose one workflow up front.

This is not a blade geometry designer, a CFD tool, or an aerodynamic synthesis engine. It is a data-driven selection, comparison, and curve-understanding tool.

---

## 2. Audience

This tool serves anyone who needs to match a fan to a system or understand how a fan behaves in context. The audience spans a wide range, and the tool must be useful across that range without becoming incoherent.

### Primary audiences

| Who | Typical scale | What they need | How they talk about it |
|-----|--------------|----------------|----------------------|
| HVAC / mechanical engineer | Building AHUs, large centrifugal fans | Selection at a duty point, energy comparison, AMCA context | Static pressure, system effect, FEI |
| Electronics cooling engineer | 40–120mm axial fans for enclosures and heatsinks | Fan-vs-impedance intersection, thermal margin | Impedance curve, operating point, CFM |
| Industrial / process engineer | Process ventilation, fume extraction | Duty point verification, density correction | Standard air, altitude correction |
| Student or self-educator | Any scale | Understanding curve shapes, affinity laws, why fans stall | "What does this curve mean?" |
| Hobbyist / maker | Small fans for projects, 3D printer enclosures | Quick answer with minimal jargon | "Will this fan work?" |

### How to serve all of them without splintering the tool

The tool does **not** need separate modes per audience. Instead:

- **Vocabulary adapts via context, not configuration.** Tooltips and educational panels use plain language first, then introduce standard terminology. An electronics engineer who sees "system impedance curve" and an HVAC engineer who sees "system resistance curve" are looking at the same thing — the tool should acknowledge both terms naturally in its educational content.
- **Defaults are minimal and jargon-light.** The initial form asks for flow, pressure, and a fan curve. It does not open with AMCA terminology or assume the user knows what "pressure basis" means.
- **Depth is available on demand.** Pressure basis selection, density correction, FEI display, and affinity-law scaling are all present but not forced. They appear when relevant or when the user expands advanced options.
- **The built-in fan library provides scale-appropriate examples.** A user exploring small axial fans should see small-axial examples by default, not industrial centrifugal curves. The library should cover the range.

---

## 3. Product Definition

### What This Tool Is

A browser-based engineering tool that:

- visualizes fan pressure, power, and efficiency curves interactively,
- overlays those curves with a system curve,
- solves the operating point in real time as inputs change,
- lets users explore the design space by dragging, sliding, and adjusting — or by typing values directly,
- scales tested data to new speeds and air densities using affinity laws,
- compares multiple fans against the same duty point with user-selected ranking criteria,
- teaches how fans, systems, and operating points interact through progressive disclosure,
- surfaces tiered warnings when a comparison is not valid or results depend on unmodeled effects.

### What This Tool Is Not

This tool is not, in its first implementation:

- a blade geometry designer,
- a CFD replacement,
- a duct network solver for arbitrary branched systems,
- a sound prediction tool from first principles,
- an AMCA certification engine,
- an official Fan Energy Index calculator from incomplete input data,
- a substitute for manufacturer selection software when the selection depends on proprietary corrections or unpublished preferred operating region limits.

---

## 4. Core User Questions

The tool should be designed around these questions:

1. **Will this fan meet my duty point?**
2. **At what flow, pressure, speed, and power will it actually operate in my system?**
3. **How efficient is it at that operating point — not just at peak?**
4. **How do two or more fans compare for the same duty point?**
5. **What changes if I vary speed, density, or system resistance?**
6. **How far is the operating point from the peak-efficiency region?**
7. **How much annual energy does each option consume?**
8. **What kind of fan do I need for this system?** (exploration direction)
9. **How does changing my system change which fan is best?** (design/analysis reversal)

Questions 1–7 are analysis. Questions 8–9 are exploration. Both are first-class.

---

## 5. The Interaction Model

This is the section that defines what the tool *feels like* to use. It is the most important design decision in the spec.

### The core principle: every interactive element has a typed-input equivalent, and every typed input has an interactive equivalent

The plot and the form are two views of the same state. Typing a number updates the plot. Dragging on the plot updates the form. Neither is primary. This means:

- The hurried engineer uses the form, glances at the result cards, and is done.
- The curious student drags things on the plot and watches what happens.
- The verifying expert reads the derivation panel and checks the math.

All three are using the same tool in the same default state. No one is penalized, and no one has to opt into a "mode."

### Implementation priority

The form-driven workflow must work completely and correctly before any interactive plot behavior is added. If implementation budget runs short, the form still works without drag interactions. The drag layer is an enhancement to a tool that already works via typed inputs — not the other way around.

### What "interactive" means concretely

| Element | Typed input equivalent | Interactive equivalent | Phase |
|---------|----------------------|----------------------|-------|
| Duty point (flow, pressure) | Number fields | Draggable marker that slides along the current system curve (constant K) | 1 |
| Fan speed | Per-fan RPM field + per-fan slider | Slider in the fan's input block that deforms its curve via affinity laws | 1 |
| Air density | Temperature + elevation fields, or direct density | (No drag equivalent — form only) | 1 |
| System curve steepness | K coefficient or reference point fields | Draggable system curve (modifies K only, holds ΔP_fixed constant) | 2 |
| Operating point | Computed result card | Visible dot on plot that moves as any input changes (read-only, not draggable) | 1 |

**Critical interaction rule — duty point dragging:** When the user drags the duty point marker on the plot, it slides **along the existing system curve** (K stays constant). This means the user is exploring "what flow does my system deliver?" — not reinventing the system. To change the system itself (modify K), the user either edits the form fields or, in Phase 2, drags the system curve directly. These are separate actions that must never be conflated.

### The passive-until-touched rule

Every interactive element starts in a **resolved state**. The plot is pre-solved on load — it shows a default fan, a default system, and the intersection. Nothing is blank, nothing waits for the user to act. The sliders exist but are already at their default values. The duty point marker is already at the typed value. You can use this tool without ever touching the plot.

Interaction is discovered, not required:

- Hover over the operating point → tooltip shows the numbers (desktop). Tap to inspect (touch).
- Grab the duty point marker → drag it along the system curve, watch results update.
- Move a fan's speed slider → watch that fan's curve stretch/compress.
- Nothing breaks if you never do any of this.

### Result cards: one active candidate above the fold

The primary result — operating point, meets duty yes/no, power, efficiency — is shown in a result card for the **currently selected/active fan** above the plot. When multiple fans are loaded, the user selects which fan is "active" (click in comparison table or on the plot curve), and the result card updates. The full multi-fan comparison lives in the comparison table below the plot, not in a row of cards that crowds the above-the-fold area.

### Touch device interaction model

On touch devices (detected via pointer type or screen width):

- **Hover → tap-to-inspect.** Tapping a curve or point spawns a persistent tooltip. Tapping elsewhere dismisses it.
- **Drag duty point** remains functional (touch-drag along system curve).
- **Speed slider** remains functional (standard touch slider).
- **System curve drag (Phase 2)** is disabled on touch. Use form inputs instead.
- All results remain fully accessible via typed inputs — the form is the primary interface on mobile.

### Real-time update budget

**Drag and slider interactions** must update within a single animation frame (~16ms target, 50ms acceptable). The solver is lightweight (piecewise-linear intersection) so this should be achievable.

**Data-entry paths** (CSV paste, manual table edits, multi-fan recomputation) should be **debounced and validation-first**. Parse and validate on commit (blur, Enter, or paste-complete), not on every keystroke. Show a brief processing indicator if validation takes >100ms.

---

## 6. Experience Walkthroughs

These are concrete scenarios showing how the tool serves each persona. They are design requirements, not suggestions.

### The hurried engineer (30 seconds to answer)

1. Opens tool. Sees a pre-loaded example fan and system with the operating point already solved.
2. Clicks "Load fan from library" → picks a fan close to what they need (or pastes CSV data).
3. Types their duty point: 500 CFM, 0.3 in. w.g.
4. Result card updates instantly: "Operating point: 485 CFM @ 0.31 in. w.g. — Duty: MET. Power: 142W."
5. Done. Never touched the plot. Never expanded anything.

### The curious student (5 minutes of exploration)

1. Opens tool. Sees the pre-loaded example.
2. Notices the operating point dot on the plot. Hovers over it — sees a tooltip.
3. Grabs the duty point marker and drags it along the system curve. Watches the "meets duty" indicator change from green to red as they push past what the fan can deliver.
4. Adjusts the fan's speed slider. Watches the fan curve expand outward — the operating point moves, the power number climbs, and they *see* the affinity laws in action without reading a single equation.
5. Expands the derivation panel. Sees the affinity law equations with their current numbers substituted in.
6. Switches to a different fan archetype from the library (clearly labeled as educational). The curve changes shape — "oh, that's what a backward-curved centrifugal fan looks like compared to an axial."
7. Learns more in 5 minutes of dragging than in an hour of reading.

### The verifying expert (2 minutes of checking)

1. Opens tool. Pastes their own fan curve data (or loads a JSON file).
2. Enters exact duty point and air conditions.
3. Checks result card. Looks at the warning panel — sees a CAUTION-tier warning: "Density correction applied: 1.225 → 1.067 kg/m³" and an INFO-tier note: "No power data supplied, efficiency not computed."
4. Expands the derivation panel. Reads Equation (2) with substituted values. Confirms the density scaling math matches their hand calculation.
5. Trusts the tool or identifies exactly where they disagree.

---

## 7. Workflows and Entry Points

### Default workflow: known duty point

The default entry asks for the minimum needed for a selection answer:

- target airflow (with unit selection),
- target pressure requirement,
- pressure basis (visible with inline explanation — see Section 11),
- one candidate fan (selected from library or entered/imported).

Air state and system-curve details default to sensible values (standard air, simple duty-point-inferred system curve) and can be adjusted if needed.

### Advanced workflow: known system curve

Some users know the system rather than a single pressure value. An expandable "System Curve Builder" section exposes:

- fixed pressure loss term (ΔP_fixed),
- quadratic resistance coefficient (K), or
- one known (Q, ΔP) reference point to solve for K,
- optional installation margin / system-effect allowance.

### Exploration workflow: learn the curves

The built-in fan library includes synthetic educational archetypes (see Section 16). Users can load these to compare curve shapes, understand how fan type affects selection stability, or explore affinity-law behavior. Archetypes use the same solver and plot as real data, but are **visually segregated** — see Section 16 for the visual treatment rules.

---

## 8. Scope

### Covered in Phase 1

- Single-air-stream fan selection for air at moderate pressure rise.
- Static-pressure and total-pressure selection basis with inline explanation.
- User-entered, CSV-pasted, or library-loaded fan pressure-vs-flow data.
- Optional power-vs-flow data.
- Optional efficiency-vs-flow data.
- System curve: `ΔP_system = ΔP_fixed + K Q²`.
- Density correction from reference to operating conditions.
- Per-fan speed scaling via affinity laws, with warnings.
- Interactive plot with draggable duty point (slides along system curve) and per-fan speed sliders.
- Side-by-side comparison of multiple candidate fans with user-selected ranking criterion.
- Annual energy and operating-cost comparison.
- Built-in fan library with synthetic archetypes covering major fan types and scales, visually segregated from real data.
- Progressive-disclosure educational content (derivations, background panels).
- Tiered result warnings (blocking / caution / informational).
- Global unit coordinate system with automatic conversion of imported fan data.
- Touch-device interaction fallback.

### Deferred to later phases

- Draggable system curve on plot (Phase 2).
- RPM solving — "what speed do I need to hit this duty point?" (Phase 2).
- Fan arrays (Phase 3).
- Fans in series or parallel (Phase 3).
- Acoustic prediction or sound-power comparison (Phase 3, only with tested data).
- Compressible high-pressure applications.
- Non-air gas properties beyond simple density input.
- Full duct fitting library and network solver.
- Motor thermal limits, surge/stall maps, or structural rotor checks.
- Automatic import from arbitrary manufacturer PDFs.
- Design-space envelope visualization (shaded speed-range region).
- User-saved scenarios / JSON import-export.

---

## 9. Explicit Non-Goals for Phase 1

The tool shall not:

- synthesize a real fan curve from only diameter, RPM, and a vague fan type,
- infer a preferred operating range unless that range is supplied or clearly approximated as a heuristic,
- claim official FEI compliance without full AMCA 208 context,
- estimate sound from duty point alone,
- silently extrapolate beyond user-supplied data,
- mix static and total pressure bases without an explicit conversion path and warning,
- hide installation effects behind false-precision output,
- force users to understand AMCA terminology to get a basic answer,
- require interaction with the plot to get a result (forms must always work independently),
- auto-select a "best" candidate without the user choosing what "best" means,
- solve for required RPM (that is Phase 2 — the speed slider is "what if," not "solve for").

---

## 10. Functional Requirements

### 10.1 Operating Point Solver

The tool shall:

- accept a system requirement (single duty-point pressure or full system curve),
- accept one or more candidate fan curves,
- scale each fan's curve independently to operating density and its own speed setting,
- compute the fan/system intersection point for each candidate,
- report operating flow, pressure, speed, power, and efficiency per candidate,
- update all outputs in real time as any input changes (typed or interactive).

If no valid intersection exists, the tool shall say so plainly and explain why (fan cannot deliver required pressure, system is too restrictive, etc.).

#### Multiple intersection handling

If multiple intersections exist (e.g., forward-curved centrifugal stall region), the tool shall:

- **Plot both intersection points.** The stable (right-side, higher-flow) branch gets the normal operating-point marker. The unstable (left-side, lower-flow) branch gets a distinct warning marker (e.g., hollow red circle).
- **Use the stable branch** for all result-card values and comparison-table data.
- **Display a CAUTION-tier warning** explaining: "This fan has two mathematical operating points at this system curve. The marked stable point (higher flow) is shown. The unstable point (lower flow, marked in red) represents a region where the fan may surge or hunt. Avoid operating near the unstable intersection."
- **In the educational panel,** explain what stall/surge means and why forward-curved fans are prone to this.

### 10.2 Comparison Engine

The tool shall compare multiple candidate fans using the same:

- flow basis,
- pressure basis,
- air density,
- operating scenario.

Each candidate may have its own speed setting (per-fan speed control).

Each candidate shall return at least:

- meets duty point: yes / no,
- operating flow,
- operating pressure,
- operating speed,
- shaft power,
- electrical power if motor/VFD efficiency is available,
- operating efficiency,
- energy cost estimate if operating schedule is provided,
- distance from peak efficiency (as a percentage or qualitative indicator),
- warning tier and flags.

#### Ranking and "best" candidate

The tool shall **not** auto-declare a "best" candidate. Instead:

- The comparison table is **sortable by any column** (click column header to sort).
- An optional **"Rank by"** dropdown lets the user choose a ranking criterion: lowest shaft power, lowest electrical power, lowest annual cost, highest efficiency at duty, most duty margin, or most stable intersection.
- The selected ranking highlights the top candidate in the table but does not editorialize ("best"). It simply sorts.
- If no ranking is selected, the table shows candidates in the order they were added.

### 10.3 Interactive Visualization

This is the differentiating feature and must be built with care. However, the form-driven workflow must be fully functional before interactive plot features are added (see Section 5, Implementation Priority).

#### Primary plot: pressure vs. flow

The main plot shall show:

- one or more fan pressure-vs-flow curves,
- the active system curve (visually distinguished by source — see below),
- the target duty point as a draggable marker (constrained to slide along the system curve),
- the solved operating point for each fan as a labeled dot,
- unstable operating points (if they exist) as warning-styled markers,
- optional peak-efficiency marker if efficiency data is present.

#### System curve visual distinction

The system curve must be visually distinguishable by its source:

| Source | Visual treatment | Label |
|--------|-----------------|-------|
| Inferred from duty point (simple mode) | **Thin dashed line**, muted color | "Inferred system curve (from duty point)" |
| User-defined (advanced mode, K or reference point entered) | **Solid line**, standard weight | "User-defined system curve" |

The inferred curve must never look as authoritative as a user-defined one. An inline note in the system-definition section: "This curve is estimated from your duty point assuming pure quadratic resistance. For a more accurate model, expand the System Curve Builder."

#### Interactive behaviors on the primary plot

| Interaction | What happens | Phase |
|------------|-------------|-------|
| Drag duty point marker | Marker slides **along the existing system curve** (K stays constant); flow and pressure update in the form; operating points re-solve; result card updates | 1 |
| Move per-fan speed slider | That fan's curve scales via affinity laws; a ghost of the original-speed curve remains as reference; operating point re-solves | 1 |
| Hover on any curve (desktop) | Tooltip shows (flow, pressure) at cursor position | 1 |
| Tap on any curve (touch) | Persistent tooltip spawns; tap elsewhere to dismiss | 1 |
| Hover/tap on operating point | Tooltip shows full operating-point summary | 1 |
| Click on operating point | Scrolls to / highlights the corresponding comparison-table row and derivation | 1 |
| Drag system curve | K changes (ΔP_fixed held constant); operating points re-solve; K field updates in form | **2** |

#### Secondary plots (tabbed or stacked below primary)

When data exists:

- **Efficiency vs. flow:** shows efficiency curve(s) with operating point(s) marked. Reveals where the fan is operating relative to its peak.
- **Power vs. flow:** shows shaft power curve(s) with operating point(s) marked. If the fan has a non-overloading characteristic, this is visible.

Secondary plots share the same flow axis as the primary plot and update in sync with all interactions.

#### Visual design rules for plots

- Use the project's Polestar-inspired visual language (DESIGN.md).
- Fan curves: solid lines with distinct colors per candidate. Use the project's semantic color palette, not arbitrary rainbow colors.
- System curve: styled by source (see table above).
- Duty point marker: prominent, draggable (grab cursor on desktop), constrained to system curve.
- Stable operating points: filled circles with a contrasting border.
- Unstable operating points: hollow circles with red/danger border and a warning icon.
- Ghost curves (original speed before slider adjustment): thin, low-opacity, same color as the scaled curve.
- Synthetic archetype curves: rendered with a subtle pattern or reduced opacity to distinguish from real data (see Section 16).
- Interpolated regions: solid line through user-supplied points.
- Extrapolated regions (if enabled): dashed continuation with a warning pattern.
- Data points: small dots on the curve at user-supplied values, visible on hover or always if the dataset is sparse.
- Axes: clean, labeled with units (using the global unit coordinate system), auto-scaled with sensible padding.
- Dark mode: all plot elements must respect the dark-mode CSS variable system.

#### Intersection stability indicator

When the fan curve and system curve intersect at a shallow angle, the operating point is sensitive to small changes in either curve. The tool should visually indicate this:

- **Stable intersection** (steep crossing angle): normal operating-point marker.
- **Sensitive intersection** (shallow crossing angle): operating-point marker with a warning halo or expanded uncertainty region, plus a CAUTION-tier warning explaining that small system changes will cause large flow shifts.

This is a heuristic, not a precision metric. The crossing angle between the interpolated curves at the intersection point is sufficient.

### 10.4 Educational Disclosure

Results shall support progressive disclosure as defined in AGENTS.md:

- **L0 — Result:** Operating point summary in the active-fan result card. Always visible.
- **L1 — Curves:** Interactive plot showing fan curve(s), system curve, and intersection(s). Always visible.
- **L2 — Substituted equations:** Derivation panel showing the actual numbers plugged into each equation. Expandable.
  - Equation (1): System curve — `ΔP_system(Q) = ΔP_fixed + K Q²`
  - Equation (2): Density scaling — `ΔP_op = ΔP_ref × (ρ_op / ρ_ref)`
  - Equation (3): Speed scaling (flow) — `Q₂ = Q₁ × (N₂ / N₁)`
  - Equation (4): Speed scaling (pressure) — `ΔP₂ = ΔP₁ × (N₂ / N₁)²`
  - Equation (5): Speed scaling (power) — `P₂ = P₁ × (N₂ / N₁)³`
  - Equation (6): Efficiency — `η = (Q × ΔP) / P_shaft`
- **L3 — Background panels:** Expandable educational content sections:
  - "Static vs. total pressure — and why it matters for selection"
  - "Lab curves vs. installed performance — system effect and why your fan won't hit the catalog point"
  - "Affinity laws — what they are, when they work, and when they lie"
  - "How to compare fans correctly — why peak efficiency alone is the wrong criterion"
  - "Fan types at a glance — axial, forward-curved, backward-curved, mixed-flow"
  - "What is stall? Why do some fans have two operating points?"
- **L4 — References:** Links to AMCA standards, DOE sourcebook, and other authoritative sources.

---

## 11. Inputs

### Section 1: Duty Point

| Field | Type | Default | Notes |
|---|---|---|---|
| Target airflow | Number | Pre-populated from example | User selects units: CFM, m³/s, m³/h, L/s |
| Pressure requirement | Number | Pre-populated from example | Editable directly or via plot drag |
| Pressure basis | Select | `static` | `static` or `total`; propagates throughout |
| Pressure units | Select | Pa | Pa, in. w.g., kPa, mmH₂O |

#### Pressure basis: inline explanation (not hidden)

Pressure basis must be visible in the default form — not collapsed behind an advanced toggle. However, it must be accompanied by a brief inline explanation so non-expert users are not confused:

> **Pressure basis** — Most fan datasheets and system calculations use *static pressure*. If you're unsure, leave this as "Static." [What's the difference?] ← expandable link to L3 background panel.

This balances visibility (it's a correctness input) with accessibility (non-experts get guidance without being forced to understand the distinction before proceeding).

### Section 2: Air State (collapsed by default)

| Field | Type | Default | Notes |
|---|---|---|---|
| Air temperature | Number | 20°C | Used with elevation for density estimate |
| Elevation | Number | 0 m | Sea level default |
| Air density | Number | 1.204 kg/m³ | Computed from temp + elevation; expert override if entered directly |
| Relative humidity | Optional | Hidden | Defer unless clear value demonstrated |

When air state differs from the fan's reference density, density correction is applied automatically and reported in the warning panel (CAUTION tier).

### Section 3: System Definition

Two paths, selectable by toggle. Default is the simple path.

**Simple path (default):** The system curve passes through the duty point with a pure-quadratic shape. No additional input required — K is inferred from the duty point.

**Important:** The inferred system curve is a convenience heuristic, not a real system model. The UI must:
- Label it as "Inferred from duty point" (never just "System curve").
- Render it as a thin dashed line on the plot (see Section 10.3).
- Include a note: "This curve assumes your system has pure quadratic resistance passing through your duty point. For a more accurate model, use the System Curve Builder below."

**System curve builder path (advanced, expandable):**

| Field | Type | Default | Notes |
|---|---|---|---|
| Fixed pressure term ΔP_fixed | Number | 0 | Constant pressure component (filters, coils, etc.) |
| Quadratic coefficient K | Number | Computed | For `K Q²` losses |
| Reference flow Q_ref | Optional | — | If user knows one point but not K directly |
| Reference pressure ΔP_ref | Optional | — | Used with Q_ref to infer K |
| Installation margin | Optional | 0 | User-entered allowance for system effect |

When the user enters values in the system curve builder, the system curve becomes "user-defined" and switches to solid-line visual treatment on the plot.

### Section 4: Fan Data

Fans can be loaded from three sources, and the UI should make all three obvious:

1. **Built-in library** — dropdown or searchable picker (see Section 16). Library fans are visually tagged as educational archetypes.
2. **Paste / CSV import** — paste tab-separated or comma-separated (flow, pressure) data. Optional additional columns for power and efficiency. The tool must detect and handle unit differences (see Section 10.5).
3. **Manual entry** — editable table of (flow, pressure) points with spreadsheet-like behavior (see below).

#### Manual entry table UX requirements

The manual data-entry table must minimize friction for users transcribing data from datasheets:

- Arrow-key navigation between cells.
- Tab from the last cell in a row automatically creates a new row.
- Enter in a cell commits the value and moves down.
- Tolerance for both commas and periods as decimal separators.
- Paste a block of tab-separated or comma-separated data into the first cell and it fills the table.
- A prominent tip near the table: "Extracting points from a PDF or image? Try a tool like WebPlotDigitizer to generate CSV data you can paste here."

#### Per-fan fields

Each candidate fan requires:

| Field | Type | Required | Notes |
|---|---|---|---|
| Name | Text | Yes | User-facing label; auto-populated from library |
| Reference speed | Number (RPM) | Yes | RPM of the supplied test curve |
| Reference density | Number (kg/m³) | Yes | Density at test conditions; defaults to standard air (1.225) |
| Pressure curve points | Array of (flow, pressure) | Yes | Minimum 3 points |
| Pressure basis | Select | Yes | `static` or `total`; with inline explanation |
| Operating speed | Number (RPM) + slider | No | Defaults to reference speed. User can adjust to explore "what if I run at X RPM?" |
| Flow units | Select | Yes | CFM, m³/s, m³/h, L/s — data is auto-converted to global units |
| Pressure units | Select | Yes | Pa, in. w.g., kPa — data is auto-converted to global units |

Optional but strongly recommended:

| Field | Type | Notes |
|---|---|---|
| Power curve points | Array of (flow, power) | Enables efficiency calculation and power comparison |
| Efficiency curve points | Array of (flow, efficiency) | Displayed if provided; otherwise derived if power is available |
| Motor efficiency | Number | For electrical-power estimate |
| VFD efficiency | Number | For wire-to-air estimate |
| Preferred operating range | [min_flow, max_flow] | Displayed if provided; not invented |
| FEI | Number | Displayed only, not computed |
| Source / notes | Text | Catalog page, datasheet link, AMCA listing, etc. |

### Section 5: Scenario / Cost (collapsed by default)

| Field | Type | Default | Notes |
|---|---|---|---|
| Operating hours per year | Number | 8760 | For annual energy estimate |
| Electricity rate | Number | 0.12 $/kWh | For annual cost estimate |

---

### 10.5 Global Unit Coordinate System

The tool enforces a single global coordinate system for all plotting and calculation, set by the user's unit selections in the Duty Point section (flow units and pressure units).

When a fan is imported or entered with different units than the global setting:

- The tool **silently and automatically converts** the fan's data into the global unit system before plotting or calculating.
- The fan's original units are stored in metadata and noted in the fan's detail view: "Data entered in CFM / in. w.g., converted to m³/s / Pa for comparison."
- The user never needs to manually convert vendor data before pasting it.
- If the user changes the global unit setting, all plotted data and result values update accordingly.

---

## 12. Outputs

### Output 1: Active Fan Result Card (always visible, above plot)

A single result card for the currently selected/active fan:

- **Fan name** — with color swatch matching its plot curve
- **Operating flow** — with units
- **Operating pressure** — with units and basis label
- **Duty status** — MET / NOT MET (prominent, color-coded)
- **Shaft power** — watts or HP depending on unit setting
- **Electrical power** — if motor efficiency provided
- **Operating efficiency** — if computable; "—" with note "Power data required" if not
- **Annual energy cost** — if scenario inputs provided
- **Warning summary** — highest-tier warning icon with brief text; click to expand

When only one fan is loaded, this is the only result view needed. When multiple fans are loaded, clicking a row in the comparison table or a curve on the plot switches the active fan.

### Output 2: Interactive Curve Plot (always visible, below result card)

See Section 10.3 for full specification.

Per-fan speed sliders appear within each fan's input block (Section 11, Section 4), not as a global control on the plot.

### Output 3: Comparison Table (visible when 2+ fans loaded)

Each row includes:

| Column | Notes |
|--------|-------|
| Candidate name | With color swatch matching plot curve; click to make active |
| Data source | "Library archetype" / "User data" / "Imported" — visual tag |
| Meets duty | Yes/No |
| Operating flow | At intersection |
| Operating pressure | At intersection |
| Operating speed | Current speed setting for this fan |
| Operating efficiency | If computable |
| Shaft power | At operating point |
| Electrical power | If motor data available |
| Distance from peak η | Percentage or qualitative |
| Annual energy cost | If scenario provided |
| Warning tier | Icon: BLOCKING (red), CAUTION (amber), INFO (blue), or clear |

The table is **sortable by any column**. An optional **"Rank by"** dropdown (above the table) lets the user choose: lowest shaft power, lowest annual cost, highest efficiency at duty, most duty margin, most stable intersection. Sorting highlights the top-ranked row but does not editorialize.

### Output 4: Warning / Assumption Panel (tiered)

Warnings are organized into three tiers:

#### BLOCKING (red) — result cannot be trusted
- No valid intersection exists (fan undersized for system).
- Pressure basis mismatch between system and fan data with no automatic conversion possible.
- Malformed or non-physical curve data.
- Fewer than 3 data points provided.

When a BLOCKING warning is active, the result card shows a prominent "RESULT UNRELIABLE" banner instead of confident numbers. The operating point is not plotted.

#### CAUTION (amber) — result usable with awareness
- Density correction applied (showing reference → operating density).
- Speed scaling applied with distance from reference speed (especially >±30%).
- Shallow intersection angle (sensitive operating point).
- Multiple intersections found (stable branch selected, unstable branch marked).
- Installation effects not modeled unless user added margin.
- Operating point outside manufacturer's preferred operating range (if range was provided).
- Extrapolation beyond supplied curve range (if user opted in).

#### INFO (blue) — context, not a problem
- Missing power data — efficiency not computed.
- Preferred operating range not available.
- Inferred system curve in use (not user-defined).
- Default standard-air density assumed (no air-state input provided).

### Output 5: Derivation / Explanation Panel (expandable)

Shows the equations used for the active calculation with substituted numerical values. See Section 10.4, L2 for the equation list.

---

## 13. UI Structure

This tool shall use the advanced template. The layout is:

### 1. Header
- Tool name: "Fan Curve Explorer & Selector"
- Subtitle: "Select, compare, and understand fan operating points"

### 2. Primary output area (above the fold)
- Active fan result card (single card, switches with selection)
- Interactive curve plot (dominant visual element)

### 3. Input panel (left side or collapsible on mobile)
- Duty Point (flow + pressure + pressure basis with inline explanation)
- Fan Selection (library picker + paste/import + manual entry; each fan block includes its own speed slider)
- Air State (collapsed by default)
- System Curve Builder (collapsed by default; simple mode inferred from duty point)
- Scenario / Cost (collapsed by default)

### 4. Secondary output area (below primary)
- Comparison table with "Rank by" dropdown (appears when 2+ fans loaded)
- Secondary plots (efficiency, power — tabbed)
- Warning / assumption panel (tiered)
- Derivation panel (expandable)

### 5. Background / educational content (expandable sections at bottom)
- Fan types overview
- Static vs. total pressure
- Affinity laws
- System curves and system effect
- What is stall / surge?
- How to compare fans
- References

### Default state on load

- One example fan pre-loaded from the library (a mid-size axial fan — relatable to the broadest audience), visually tagged as an educational archetype.
- System curve inferred from a sensible duty point, rendered as thin dashed line with "inferred" label.
- Operating point solved and displayed.
- Result card populated.
- Plot rendered with fan curve, system curve, and operating point visible.
- All advanced sections collapsed.
- Comparison table hidden (only one fan loaded).
- User can immediately see a complete, working example and start modifying.

### Graceful transition when user changes scale

When the user enters a duty point that is dramatically different from the pre-loaded example (e.g., types 10,000 CFM when the default is a 120mm PC fan), the tool should:

1. **Auto-scale the chart axes** to the new duty point range — never show a broken or absurdly zoomed-out chart.
2. **Show an INFO-tier note:** "The loaded fan does not cover this flow range. Try loading a different fan from the library." with a direct link to the library picker.
3. Optionally, **auto-suggest** a library archetype that covers the entered duty range (e.g., "The 'Large Axial (500mm)' archetype covers this range — load it?").

The tool must never feel like the user "broke" it by typing a number.

---

## 14. Calculation Rules

### 14.1 Flow Basis

Primary flow basis is **actual volumetric flow at operating conditions**, not standard or normalized flow.

This must be explicit in the UI because many published catalogs reference standard-air test conditions for pressure and power while showing actual volumetric flow. The tool treats pressure and power as density-sensitive while keeping the flow axis tied to the curve definition supplied by the user.

### 14.2 Density Scaling

When a fan curve is supplied at one density and applied at another:

- flow axis: unchanged (density-only correction),
- pressure: scaled by `ρ_op / ρ_ref`,
- power: scaled by `ρ_op / ρ_ref`,
- warning (CAUTION tier): "Density correction applied. This is an incompressible approximation."

### 14.3 Speed Scaling (Affinity Laws)

When a fan's speed slider is set to a value different from its reference speed:

- `Q₂ = Q₁ × (N₂ / N₁)`
- `ΔP₂ = ΔP₁ × (N₂ / N₁)²`
- `P₂ = P₁ × (N₂ / N₁)³`

The tool must warn (CAUTION tier) that this is an approximation that becomes less trustworthy far from the published test point or near unstable regions. If speed differs by more than ±30% from reference, the warning escalates to emphasize reduced reliability.

When speed scaling is active, the plot shows both the scaled curve (solid) and the original reference-speed curve (ghost).

**Important distinction:** The speed slider answers "what if I run this fan at X RPM?" It does **not** answer "what speed do I need to hit my duty point?" That reverse-solve is a Phase 2 feature (RPM solving). The UI should not imply the slider can find the answer — it is a manual "what-if" control.

### 14.4 System Curve

Default model:

`ΔP_system(Q) = ΔP_fixed + K Q² + ΔP_margin`

Simple mode: `ΔP_fixed = 0`, `ΔP_margin = 0`, K inferred from the duty point: `K = ΔP_duty / Q_duty²`.

If the user provides a reference point instead of K, solve: `K = (ΔP_ref - ΔP_fixed) / Q_ref²`.

**The inferred system curve is a heuristic check, not a real system model.** It answers "if my system has roughly this resistance, where would the fan operate?" It does not claim to know the actual system. This distinction must be reflected in the visual treatment (Section 10.3) and in an INFO-tier warning.

### 14.5 Efficiency

If efficiency is not supplied but pressure and power are supplied on a consistent basis:

- static efficiency = `(Q × ΔP_static) / P_shaft`
- total efficiency = `(Q × ΔP_total) / P_shaft`

If power data is missing, the tool must not invent efficiency. It should display "—" with a note: "Power data required to compute efficiency."

### 14.6 Preferred Operating Range

If manufacturer preferred-operating-range data is provided, display it as a shaded region on the plot.

If not provided, do not label any region as "preferred operating range." At most, display distance from the peak-efficiency point and label it as a heuristic ("X% of peak efficiency"), not as a manufacturer specification.

### 14.7 FEI

If FEI is supplied with the fan data, display it. Do not compute FEI from sparse inputs. A later phase can evaluate full AMCA 208 support.

---

## 15. Interpolation, Plotting, and Data Handling

- Use piecewise linear or shape-preserving monotonic interpolation for fan curves.
- Do not use high-order unconstrained polynomial fits.
- Visually mark user-supplied data points on the curve (small dots, visible on hover or always for sparse datasets).
- Refuse or warn on non-physical inputs: negative flow, negative absolute power, duplicated or unsorted flow points.
- Keep each candidate fan's reference metadata (speed, density, basis, original units) attached to its curve throughout the calculation chain.
- Extrapolation beyond the supplied range is opt-in and visually flagged (dashed line + CAUTION-tier warning).

---

## 16. Built-In Fan Library

The tool shall ship with a library of synthetic fan curves that are:

- educational (representative of real fan types and scales),
- clearly labeled as synthetic archetypes, not real products,
- covering a useful range of fan types and sizes,
- **visually segregated from real/imported fan data at every point in the UI.**

### Visual segregation rules

Synthetic archetype fans must be visually distinct from user-entered or imported real data **everywhere they appear**:

| UI element | Real fan treatment | Archetype treatment |
|-----------|-------------------|-------------------|
| Fan picker / library | Normal card | Card with "EDUCATIONAL ARCHETYPE" badge and muted/accent background |
| Plot curve | Solid line, full opacity | Solid line with subtle dot-dash pattern OR reduced opacity, plus a small "edu" label at curve end |
| Comparison table row | Normal row | Row with tinted background and "Archetype" tag in the data-source column |
| Result card (when active) | Normal card | Card with "Educational Archetype" subtitle; banner: "This is synthetic data for learning, not a real product." |
| Exported / printed output | Normal | Watermark or footnote: "Based on synthetic archetype, not manufacturer data" |

The goal: it must be impossible to screenshot this tool with an archetype and a real fan on the same plot and mistake the archetype for selection-grade data.

### Phase 1 library contents

| Archetype | Type | Scale | Purpose |
|-----------|------|-------|---------|
| Small axial (40mm) | Axial | Electronics cooling | Typical enclosure fan, low pressure |
| Medium axial (120mm) | Axial | Electronics / light industrial | Higher flow, moderate pressure |
| Large axial (500mm) | Axial | Industrial / HVAC | High flow, low-moderate pressure |
| Backward-curved centrifugal | Centrifugal | HVAC / industrial | Non-overloading power curve, high efficiency |
| Forward-curved centrifugal | Centrifugal | HVAC / residential | High flow at low speed, stall-prone curve shape |
| Mixed-flow | Mixed | Industrial | Between axial and centrifugal characteristics |

Each archetype includes:

- pressure-vs-flow curve (required),
- power-vs-flow curve (required — enables efficiency demonstration),
- efficiency-vs-flow curve (computed or provided),
- reference speed and density,
- a short description of what this fan type is and where it's used,
- a note: "Synthetic archetype for educational use. Not a real product."

### Curve generation approach

Archetype curves should be generated from published general-shape characteristics for each fan type (widely available in textbook and DOE resources), scaled to realistic operating ranges. They do not need to match any specific manufacturer's product. They need to be physically plausible — monotonic pressure decline (for axial), correct power-curve shape (non-overloading for backward-curved, overloading for forward-curved), and realistic efficiency peaks.

### Future library expansion

Later phases may add:

- user-contributed curves (with provenance tracking),
- public-domain manufacturer data (if found with clear redistribution rights),
- more size variants within each type.

---

## 17. Validation and Warning Rules

All warnings are assigned to a tier (see Section 12, Output 4 for tier definitions).

### BLOCKING warnings (result unreliable)

- No valid intersection exists.
- Pressure basis mismatch with no conversion path.
- Malformed or non-physical curve data.
- Fewer than 3 data points.

### CAUTION warnings (result usable with awareness)

- Density correction applied.
- Speed scaling applied (especially >±30% from reference).
- Shallow intersection angle (sensitive operating point).
- Multiple intersections (stable branch selected, unstable marked).
- Installation effects not modeled.
- Operating point outside preferred operating range (if range provided).
- Extrapolation beyond supplied curve range.
- Curve comparison across fans with different implicit reference densities.

### INFO warnings (context)

- No power data — efficiency not computed.
- Preferred operating range not available.
- Inferred system curve in use.
- Default standard-air density assumed.
- Archetype data in use (not real product data).
- Heuristic results where manufacturer data would be preferred.

Warnings are a feature, not noise. They are necessary for honest engineering behavior. But they must be **triaged so users can distinguish "don't trust this" from "be aware of this" from "just so you know."**

---

## 18. Data Model

### `AirState`

```text
AirState {
  temperature_c: float | null
  elevation_m: float | null
  density_kg_m3: float
  source: string  // "calculated" | "user-entered"
}
```

### `SystemCurve`

```text
SystemCurve {
  pressure_basis: string         // "static" | "total"
  delta_p_fixed_pa: float
  resistance_k: float
  installation_margin_pa: float
  source_mode: string            // "duty-point-inferred" | "direct-k" | "reference-point"
}
```

### `CurveSeries`

```text
CurveSeries {
  x_flow_values: list[float]
  y_values: list[float]
  units_x: string               // original entry units
  units_y: string               // original entry units
}
```

### `FanCandidate`

```text
FanCandidate {
  candidate_id: string
  title: string
  source_type: string              // "library-archetype" | "user-entered" | "imported"
  archetype_note: string | null    // "Synthetic archetype — not a real product"
  reference_speed_rpm: float
  operating_speed_rpm: float       // user-set speed (defaults to reference)
  reference_density_kg_m3: float
  pressure_basis: string           // "static" | "total"
  pressure_curve: CurveSeries
  power_curve: CurveSeries | null
  efficiency_curve: CurveSeries | null
  fei: float | null
  motor_efficiency: float | null
  vfd_efficiency: float | null
  preferred_operating_region: [float, float] | null
  source_note: string | null
}
```

### `OperatingPointResult`

```text
OperatingPointResult {
  candidate_id: string
  meets_duty: bool
  operating_flow: float | null
  operating_pressure: float | null
  operating_speed_rpm: float | null
  shaft_power_w: float | null
  electrical_power_w: float | null
  operating_efficiency: float | null
  distance_from_peak_efficiency: float | null  // fraction, e.g. 0.92 means 92% of peak
  intersection_angle_deg: float | null         // for stability indication
  has_unstable_intersection: bool              // true if a second (unstable) intersection exists
  unstable_intersection_flow: float | null     // flow at the unstable intersection, if applicable
  annual_energy_kwh: float | null
  annual_energy_cost: float | null
  warning_tier: string             // "blocking" | "caution" | "info" | "clear"
  warnings: list[Warning]
}
```

### `Warning`

```text
Warning {
  tier: string       // "blocking" | "caution" | "info"
  code: string       // machine-readable code, e.g. "no-intersection", "density-correction"
  message: string    // human-readable explanation
}
```

---

## 19. Reference and Copyright Strategy

This tool should be built around primary, official sources where possible.

### Recommended references

- **ANSI/AMCA 210-25**: laboratory methods and rating basis for fan aerodynamic performance.
- **AMCA Publication 201-23**: fan/system interaction and system effect guidance.
- **ANSI/AMCA 208-18** and AMCA FEI guidance: how FEI is used and why it is tied to selection context.
- **ANSI/AMCA 205-19** and **AMCA Publication 206-15**: fan efficiency classification context.
- **U.S. DOE Improving Fan System Performance Sourcebook**: system curves, controls, operating-point reasoning, and system-level energy thinking.
- **ANSI/AMCA 300-24** and **ANSI/AMCA 301-22**: only if sound data becomes supported.
- **ANSI/AMCA 270-23**: only if fan arrays become in scope.

### Recommended public links

- <https://www.energy.gov/cmei/ito/fan-systems>
- <https://www.energy.gov/sites/default/files/2014/05/f16/fan_sourcebook.pdf>
- <https://www.amca.org/certify/amca-certified-rating-program-search.html>

### Copyright boundary

The tool shall not republish copyrighted AMCA tables or protected standard text.

Safe implementation stance:

- let users import their own curve data,
- cite official standards and public pages in the references section,
- implement general engineering logic with transparent equations,
- avoid embedding protected tables without clear redistribution permission.

---

## 20. Testing and Verification Strategy

### Unit tests (pytest)

- no-intersection cases (fan undersized for system),
- one-intersection nominal cases,
- two-intersection cases (verify both are found, stable branch selected),
- density scaling (pressure and power scale correctly),
- speed scaling (affinity laws produce expected transformed curve),
- per-fan independent speed scaling (two fans at different speeds),
- efficiency derivation when power is present,
- efficiency refused when power is absent,
- comparison ranking logic for each ranking criterion,
- basis mismatch warning generation,
- malformed curve input rejection (non-monotonic, too few points, etc.),
- system-curve inference from duty point,
- intersection angle calculation,
- unit conversion (fan entered in CFM/in.w.g., compared in m³/s/Pa),
- warning tier assignment.

### Known-value test cases

- a simple synthetic fan/system intersection with hand-checkable numbers,
- a density-change case (e.g., sea level to Denver) with expected pressure and power scaling,
- a speed-change case with affinity-law-scaled values verified against manual calculation,
- a two-fan comparison where the "obvious" choice (higher peak efficiency) is not the best at the actual duty point,
- a forward-curved fan with two mathematical intersections (verify both found, correct one selected).

### Parameter JSON test cases

Following project convention (`test-cases/*.json`), ship with at least:

- `basic_intersection.json` — single fan, single duty point, simple system
- `density_correction.json` — standard-air fan applied at altitude
- `speed_scaling.json` — fan operated at non-reference speed
- `two_fan_comparison.json` — two candidates, same duty point, different outcomes
- `no_intersection.json` — system too restrictive for the fan
- `dual_intersection.json` — forward-curved fan with unstable region

### Browser integration tests

- Plot renders with expected elements (fan curve, system curve, operating point).
- Dragging duty point slides along system curve (K stays constant) and updates result card and input fields.
- Per-fan speed slider deforms only that fan's curve and shows ghost of original.
- Loading a library fan populates all required fields and shows archetype visual treatment.
- CSV paste creates a valid fan candidate with auto-converted units.
- Inferred system curve renders as thin dashed line; user-defined renders as solid.
- Blocking warning prevents confident result display.
- Touch: tap on curve spawns persistent tooltip.

---

## 21. Recommended Phasing

### Phase 1: The Complete Interactive Tool

This is not a "minimum viable" skeleton. Phase 1 ships a tool that is genuinely useful, educational, and interactive from day one. **Implementation order: form-driven workflow first, then plot interactions.**

- Form-driven operating point solver with real-time updates
- Active-fan result card with duty status, power, efficiency
- Interactive curve plot with draggable duty point (constrained to system curve)
- Per-fan speed sliders with affinity-law scaling and ghost curves
- Built-in fan library (6 archetypes) with visual segregation from real data
- Fan data entry via library, CSV paste, or manual entry (with spreadsheet-like table UX)
- Global unit coordinate system with automatic conversion
- System curve (simple inferred mode with visual distinction + advanced builder)
- Density correction with CAUTION-tier warnings
- Multi-fan comparison table with sortable columns and "Rank by" dropdown
- Annual energy/cost estimate
- Tiered warning system (blocking / caution / info)
- Pressure basis visible with inline explanation
- Multiple intersection detection and display (stable + unstable markers)
- Intersection stability indicator
- Derivation panel with substituted equations
- Background educational content (6 topic sections including stall/surge)
- Dark mode support
- Touch-device interaction fallback (tap-to-inspect, form-primary on mobile)
- Graceful scale-mismatch handling when user enters a duty point far from the loaded fan

### Phase 2: Deeper Exploration and Workflow

- Draggable system curve on plot (modifies K only, holds ΔP_fixed constant; desktop only)
- RPM solving — "find the speed needed to hit a duty point" (clearly distinct from the "what-if" speed slider)
- Design-space envelope visualization (shaded achievable region across speed range)
- User-saved scenarios / JSON import-export
- Expanded library (more sizes, user-contributed curves with provenance)
- Preferred operating range display when manufacturer data exists
- Animated fan-to-fan comparison transitions on plot
- Richer warning and explanation content

### Phase 3: Advanced System Use Cases

- Fan arrays
- Fans in series / parallel
- Sound-data comparison (when tested data provided)
- Expanded system-curve options (multiple operating points, variable systems)
- Tie-ins to future duct or airflow tools
- Full AMCA 208 FEI evaluation (if formulas are legally usable)

---

## 22. Design/Analysis Duality

This section captures a broader philosophical point that extends beyond this tool.

Engineering tools typically frame themselves as either:
- **Analysis tools:** "Given a design, predict performance." (Forward direction.)
- **Design tools:** "Given a requirement, synthesize a design." (Reverse direction.)

In practice, engineers constantly move between these directions. A fan selection that starts as analysis ("will this fan work?") immediately becomes design ("what if I change the duct to reduce resistance?"). A system exploration that starts as design ("what fan do I need?") immediately becomes analysis ("how does this specific fan perform at this specific point?").

This tool should not pick one direction. It should make switching directions effortless:

- Typing a duty point and reading results is analysis.
- Dragging the duty point along the system curve and watching which fans can still meet it is design.
- Loading a fan and reading the operating point is analysis.
- Moving the speed slider to see how performance changes is design exploration. (Phase 2 adds RPM solving — the reverse-direction complement.)

The tool's architecture (bidirectional binding between form inputs and plot interactions, real-time solving) inherently supports this duality. The key implementation requirement is: **no interaction should feel like it belongs to a different "mode."** Everything lives on one page, in one state, with one set of inputs that can be manipulated from either direction.

This principle may eventually be formalized as a project-wide norm in AGENTS.md. For now, this tool is the first to explicitly embody it.

---

## 23. Relationship to Existing Code

### Existing fan curve functions in `pycalcs/heatsinks.py`

The heatsink designer already contains:

- `fan_curve_pressure()` — parabolic and piecewise-linear fan curves
- `solve_fan_operating_point()` — binary search intersection solver

These functions work but are tightly coupled to the heatsink solver's needs. The fan tool should:

1. Extract and generalize this logic into a new `pycalcs/fan_curves.py` module (as proposed in `plans/thermal_tool_family_future_plan.md`).
2. Add density scaling, speed scaling, efficiency derivation, multi-intersection detection, unit conversion, and comparison logic.
3. Keep `pycalcs/heatsinks.py` working by either importing from the new module or maintaining a thin compatibility layer during transition.

### Shared backend per thermal tool family plan

The fan tool's backend module (`pycalcs/fan_curves.py`) should be designed for reuse:

- The heatsink designer can import fan/system intersection logic from it.
- Future duct or airflow tools can import system-curve logic from it.
- The module should have no UI dependencies — pure calculation with clear inputs and outputs.

---

## 24. Final Recommendation

This tool should be a **selection and comparison calculator that doubles as an interactive learning environment**. It should feel like the best fan engineering tool on the open web — not because it handles every edge case, but because it makes the fundamental concepts tangible while being rigorously honest about what it does and does not know.

The differentiators are:

1. **Interactivity as understanding.** Dragging a point along a curve and watching physics respond teaches faster than any textbook.
2. **Honest about its limits.** Tiered warnings, missing-data flags, explicit assumptions, and visual distinction between inferred and real data build trust that black-box vendor tools don't.
3. **Works for everyone.** From the HVAC engineer with AMCA data to the hobbyist with a datasheet PDF — no one is excluded, and no one is forced through someone else's workflow.
4. **Fast for the hurried, deep for the curious.** The same tool, the same page, the same state — the form is the fast path, the plot is the exploration path, and they're the same state.
5. **Never misleading.** Synthetic data looks different from real data. Inferred curves look different from defined curves. Unstable intersections are shown, not hidden. The tool earns trust by showing its work and its limits.

If the implementation stays data-driven, basis-explicit, warning-tiered, and interactively responsive, it will be a strong engineering tool. If it sacrifices honesty for polish or interactivity for feature breadth, it will be just another static calculator with a nice chart.
