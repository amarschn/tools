# Fan Curve Explorer & Selector

Date: 2026-03-23
Status: Proposed product spec for critique before implementation
Related existing assets:
- `TODO.md` ("Pump/fan selection tool that intersects system and pump curves")
- `DESIGN.md`
- `tools/example_tool_advanced/index.html`

## 1. Purpose

Define a fan-focused tool that is genuinely useful in practice, educational for users who want to understand fan behavior, and honest about what can and cannot be inferred from limited inputs.

The tool should answer the real selection question:

> Given a required duty point and one or more candidate fans, where will each fan actually operate, how much power will it draw, how efficient will it be there, and which option is the best fit?

This is a different problem from aerodynamic fan design. The first version should be a fan selection, comparison, and curve-understanding tool, not a blade or impeller synthesis tool.

---

## 2. Executive Recommendation

Build a tool named **Fan Curve Explorer & Selector**.

Recommended product stance:

1. **Primary job:** Solve and visualize the operating point by intersecting a fan curve with a system curve.
2. **Secondary job:** Compare multiple candidate fans at the same duty point on an apples-to-apples basis.
3. **Educational job:** Teach users how pressure, flow, power, efficiency, density, and system effects interact.
4. **Non-goal for V1:** Do not pretend to generate a real manufacturer-quality fan design from sparse geometry inputs.

Why this is the right first tool:

- It matches the repo's Progressive Simplicity principle: most users know the flow they want and either know or can estimate the required pressure.
- It produces fast time-to-value: users can enter a duty point, load a curve, and immediately see the operating point.
- It supports both the hurried engineer and the curious student:
  - the engineer gets a duty-point answer,
  - the student gets a curve plot and derivation path,
  - the expert gets explicit assumptions and source references.
- It avoids the biggest trap in "fan design" tools: inventing performance curves that look plausible but are not selection-grade.

---

## 3. Product Definition

### What This Tool Is

A browser-based engineering calculator that:

- visualizes fan pressure, power, and efficiency curves,
- overlays those curves with a system curve,
- solves the operating point,
- scales tested data to new speeds and air densities where appropriate,
- compares multiple fans against the same duty point,
- surfaces warnings when the comparison is not valid or the result depends on unmodeled installation effects.

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
2. **At what flow, pressure, speed, and power will it operate in my system?**
3. **How efficient is it at that operating point, not just at peak?**
4. **How do two or more fans compare for the same duty point?**
5. **What changes if I vary speed, density, or system resistance?**
6. **How far is the operating point from the peak-efficiency region or known preferred operating range?**
7. **How much annual energy does each option consume?**

These questions are far more valuable for this repo than "what should the impeller blade angle be?"

---

## 5. Recommended Entry Point

### Default Workflow: Known Duty Point

The default entry point should ask for the minimum information needed to make a selection decision:

- target airflow,
- target pressure requirement,
- pressure basis: `static` or `total`,
- air state: temperature plus elevation, or directly density,
- one or more candidate fan curves.

This is the correct default because it reflects how most practical fan selections begin: the user has a required duty point and wants to know which candidate fan can satisfy it efficiently.

### Advanced Workflow: Known System Rather Than Known Pressure

Some users will know the system rather than a single duty-point pressure value. For them the tool should expose an advanced system-curve builder:

- fixed pressure loss term,
- quadratic resistance term,
- optionally one known `(Q, ΔP)` reference point to solve for the system constant,
- optional user-entered installation margin or system-effect allowance.

### Educational Workflow: Learn the Curves

The tool should optionally support a "learn mode" that uses generic, synthetic fan archetype curves for:

- axial fans,
- backward-curved centrifugal fans,
- forward-curved centrifugal fans,
- mixed-flow fans.

This mode is educational only and must be visually and textually separated from real selection mode.

---

## 6. Scope

### Covered in Phase 1

- Single-air-stream fan selection for air or air-like gases at moderate pressure rise.
- Static-pressure and total-pressure selection basis.
- User-entered or imported fan pressure-vs-flow data.
- Optional imported power-vs-flow data.
- Optional imported efficiency-vs-flow data.
- One system curve of the form `ΔP_system = ΔP_fixed + K Q²`.
- Density correction of pressure and power from reference test conditions to operating conditions.
- Speed scaling using affinity-law assumptions, with warnings.
- Side-by-side comparison of multiple fans at the same duty point.
- Annual energy and operating-cost comparison.
- Explicit result warnings when inputs are incomplete, inconsistent, or beyond the supplied data envelope.

### Deferred to Later Phases

- Fan arrays.
- Fans in series or parallel.
- Acoustic prediction or sound-power comparison unless tested sound data is provided.
- Compressible high-pressure applications and detailed compressibility corrections.
- Non-air gas properties beyond simple density input.
- Full duct fitting library and network solver.
- Motor thermal limits, surge/stall map prediction, or structural rotor checks.
- Automatic import from arbitrary manufacturer PDFs.

---

## 7. Functional Requirements

### 7.1 Selection / Operating Point Solver

The tool shall:

- accept a system requirement or system curve,
- accept one or more candidate fan curves,
- scale the fan curves to the user's operating density and speed assumptions,
- compute the fan/system intersection point,
- report the resulting operating flow, pressure, speed, power, and efficiency.

If no valid intersection exists inside the supplied curve range, the tool shall say so plainly and explain why.

### 7.2 Comparison Engine

The tool shall compare multiple candidate fans using the same:

- flow basis,
- pressure basis,
- air density,
- operating scenario,
- speed/control assumptions.

Each candidate shall return at least:

- meets duty point: yes / no,
- operating flow,
- operating pressure,
- operating speed,
- shaft power,
- electrical power if motor/VFD efficiency is available,
- operating efficiency,
- energy cost estimate if operating schedule is provided,
- warnings and missing-data flags.

### 7.3 Visualization

The tool shall render a primary plot showing:

- one or more fan pressure curves,
- the active system curve,
- the selected duty point,
- the solved operating point for each fan.

When data exists, the tool should also support:

- efficiency-vs-flow plot,
- power-vs-flow plot,
- optional scenario overlays for alternative speeds or densities.

### 7.4 Educational Disclosure

Results should support progressive disclosure:

- L0: operating point and best candidate summary,
- L1: curve plot and comparison table,
- L2: substituted equations for density scaling, affinity-law scaling, and system-curve evaluation,
- L3: background panels explaining static vs total pressure, lab rating vs installed performance, and why peak efficiency alone is not enough.

---

## 8. Explicit Non-Goals for Phase 1

The tool shall not:

- synthesize a real fan curve from only diameter, RPM, and a vague fan type,
- infer a preferred operating range unless that range is supplied or clearly approximated as a heuristic,
- claim official FEI compliance without full AMCA 208 context,
- estimate sound from duty point alone,
- silently extrapolate beyond user-supplied data,
- mix static and total pressure bases without an explicit conversion path and warning,
- hide installation effects behind a false precision output.

---

## 9. Inputs

### Section 1: Duty Point

| Field | Type | Notes |
|---|---|---|
| Target airflow | Number | User selects units such as CFM, m^3/s, or m^3/h |
| Pressure requirement | Number | Either direct pressure requirement or derived from system curve |
| Pressure basis | Select | `static` or `total`; must propagate throughout the calculation |
| Units | Select | Typical pressure units: Pa, in. w.g., kPa |

### Section 2: Air State

| Field | Type | Notes |
|---|---|---|
| Air temperature | Number | Used to estimate density if direct density is not supplied |
| Elevation | Number | Used with temperature for density estimate |
| Air density | Number | Expert override; if supplied directly, this takes precedence |
| Relative humidity | Optional | Defer unless there is a clear value case |

### Section 3: System Definition

Two mutually exclusive user paths should exist:

1. **Simple duty-point pressure path**
2. **System-curve builder path**

System-curve builder inputs:

| Field | Type | Notes |
|---|---|---|
| Fixed pressure term `ΔP_fixed` | Number | Constant pressure component |
| Quadratic coefficient `K` | Number | For `K Q²` losses |
| Reference flow `Q_ref` | Optional | If user knows one point but not `K` directly |
| Reference pressure `ΔP_ref` | Optional | Used with `Q_ref` to infer `K` |
| Installed-performance margin | Optional | User-entered allowance for installation/system effect |

### Section 4: Fan Data Import

Each candidate fan should minimally require:

| Field | Type | Notes |
|---|---|---|
| Candidate name | Text | User-facing label |
| Reference speed | Number | RPM of the supplied test curve |
| Reference density | Number | Density at which the curve was tested or published |
| Pressure curve points | Required array | `(flow, pressure)` pairs |
| Pressure basis of curve | Required select | `static` or `total` |

Optional but strongly recommended:

| Field | Type | Notes |
|---|---|---|
| Power curve points | Optional array | `(flow, power)` pairs |
| Efficiency curve points | Optional array | `(flow, efficiency)` pairs |
| FEI | Optional number | Display only if supplied or later computed with full context |
| Motor efficiency | Optional number | For electrical power estimate |
| VFD efficiency | Optional number | For wire-to-air estimate |
| Preferred operating range bounds | Optional array | If manufacturer data provides them |
| Sound data | Optional array | Defer in V1 display unless clearly supported |
| Source / notes | Optional text | Catalog page, submittal, AMCA-certified listing, etc. |

### Section 5: Scenario / Cost Inputs

| Field | Type | Notes |
|---|---|---|
| Operating hours per year | Optional number | For annual energy estimate |
| Electricity rate | Optional number | Cost per kWh |
| Speed control mode | Select | Fixed speed or variable speed |
| Allowed speed range | Optional range | Required if the tool solves for RPM to hit a duty point |

---

## 10. Outputs

### Output 1: Primary Result Cards

The default visible outputs should be:

- operating flow,
- operating pressure,
- required speed,
- shaft power,
- electrical power,
- operating efficiency,
- duty-point status: met / not met,
- annual energy cost if enabled.

### Output 2: Main Curve Plot

The main plot should show:

- system curve,
- candidate fan curves,
- operating points,
- target duty point marker,
- optional peak-efficiency marker if efficiency data is present.

### Output 3: Comparison Table

Each candidate row should include:

- candidate name,
- meets duty point,
- operating flow and pressure,
- operating speed,
- operating efficiency,
- shaft power,
- electrical power,
- FEI if available,
- annual energy use,
- warnings.

### Output 4: Warning / Assumption Panel

The tool should clearly report:

- extrapolation beyond supplied curve range,
- mismatch between system pressure basis and fan pressure basis,
- missing power or efficiency data,
- density correction applied,
- installation effects not modeled unless user added margin,
- preferred operating range unavailable,
- sound data unavailable.

### Output 5: Derivation / Explanation Panel

This panel should show:

- Equation (1): system curve relation,
- Equation (2): pressure scaling with density,
- Equation (3): affinity-law speed scaling,
- Equation (4): power scaling,
- Equation (5): efficiency calculation if derived from pressure and power,
- substituted numerical forms for the active fan and scenario.

---

## 11. UI Recommendation

This tool should use the advanced template because the workflow involves:

- multiple input groups,
- imported datasets,
- multiple result views,
- at least one chart,
- comparison tables,
- expandable educational content.

Recommended UI structure:

1. **Header**
   - Tool name
   - one-sentence subtitle

2. **Above-the-fold result area**
   - primary result cards
   - main curve plot

3. **Left-side inputs**
   - Duty Point
   - Air State
   - System Definition
   - Candidate Fan Data
   - Scenario / Cost

4. **Right-side outputs**
   - result cards
   - plot tabs
   - comparison table
   - warnings

5. **Expandable background section**
   - static vs total pressure
   - lab curve vs installed performance
   - affinity laws and their limitations
   - how to compare fans correctly

Default state should remain simple:

- one example fan preloaded,
- one system curve preloaded,
- comparison section empty until a second fan is added,
- advanced fields hidden unless expert mode is enabled.

---

## 12. Calculation Rules

### 12.1 Flow Basis

For Phase 1, the primary flow basis should be **actual volumetric flow at operating conditions**, not normalized or standard volumetric flow.

This must be made explicit in the UI because many published catalogs reference standard-air test conditions for pressure and power but still show volumetric flow directly. The tool should treat pressure and power as density-sensitive while keeping the flow axis tied to the actual curve definition supplied by the user.

### 12.2 Density Scaling

When a fan curve is supplied at one density and applied at another, the tool should:

- keep the flow axis unchanged for density-only correction,
- scale pressure in proportion to density ratio,
- scale power in proportion to density ratio,
- warn that this is an incompressible approximation.

### 12.3 Speed Scaling

When a user varies speed from the supplied reference speed, the tool should apply affinity-law scaling:

- `Q ∝ N`
- `ΔP ∝ N²`
- `P ∝ N³`

The tool must explicitly warn that this is an approximation and becomes less trustworthy farther from the published test point or when the fan is near unstable regions.

### 12.4 System Curve

The default model should be:

`ΔP_system(Q) = ΔP_fixed + K Q² + ΔP_installation_margin`

If the user provides one reference point instead of `K`, solve for `K` from that point.

### 12.5 Efficiency

If efficiency is not supplied but pressure and power are supplied on a consistent basis, the tool may compute:

- static efficiency for static-pressure basis,
- total efficiency for total-pressure basis.

If power data is missing, the tool must not invent efficiency.

### 12.6 Preferred Operating Range

If manufacturer preferred operating range data exists, display it.

If not, do not label a region as "preferred operating range" as though it were authoritative. At most, display distance from the peak-efficiency point and label it as a heuristic.

### 12.7 FEI

If FEI is supplied with the fan data, display it.

If FEI is not supplied, do not create an "official" FEI value from sparse user inputs in Phase 1. A later phase can evaluate full AMCA 208 support if the required formulas and reference data are available and legally usable.

---

## 13. Interpolation, Plotting, and Data Handling Requirements

The tool must be careful about how it turns discrete points into curves.

Requirements:

- Use piecewise linear or shape-preserving monotonic interpolation for plotted fan curves.
- Do not use high-order unconstrained polynomial fits for production results.
- Visually distinguish interpolated data from user-supplied points when useful.
- Refuse or warn on non-physical inputs such as negative flow, negative absolute power, or duplicated unsorted flow points.
- Keep each candidate fan's reference metadata attached to its curve.

If the user asks the tool to extrapolate beyond the supplied range, that must be opt-in and flagged.

---

## 14. Validation and Warning Rules

The tool shall validate and warn on:

- inconsistent pressure basis between system and fan data,
- missing reference density,
- missing speed range when RPM solving is requested,
- non-monotonic or malformed curve data,
- impossible or no-intersection operating point,
- multiple intersections where the selected branch is ambiguous,
- power or efficiency derived from mismatched bases,
- installed system effects omitted,
- curve comparison performed at different implicit air densities,
- heuristic results used where manufacturer data would be preferred.

Warnings are a feature, not noise. They are necessary for honest engineering behavior.

---

## 15. Data Model

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
  source_mode: string            // "direct-k" | "reference-point" | "simple-duty-pressure"
}
```

### `CurveSeries`

```text
CurveSeries {
  x_flow_values: list[float]
  y_values: list[float]
  units_x: string
  units_y: string
}
```

### `FanCandidate`

```text
FanCandidate {
  candidate_id: string
  title: string
  reference_speed_rpm: float
  reference_density_kg_m3: float
  pressure_basis: string         // "static" | "total"
  pressure_curve: CurveSeries
  power_curve: CurveSeries | null
  efficiency_curve: CurveSeries | null
  fei: float | null
  motor_efficiency: float | null
  vfd_efficiency: float | null
  preferred_operating_region: list[float] | null
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
  annual_energy_kwh: float | null
  annual_energy_cost: float | null
  peak_efficiency_flow: float | null
  warnings: list[string]
}
```

---

## 16. Reference and Copyright Strategy

This tool should be built around primary, official sources where possible.

Recommended references:

- **ANSI/AMCA 210-25**: laboratory methods and rating basis for fan aerodynamic performance.
- **AMCA Publication 201-23**: fan/system interaction and system effect guidance.
- **ANSI/AMCA 208-18** and AMCA's FEI guidance pages: how FEI is used and why it is tied to selection context.
- **ANSI/AMCA 205-19** and **AMCA Publication 206-15**: fan efficiency classification context.
- **U.S. DOE Improving Fan System Performance Sourcebook**: system curves, controls, operating-point reasoning, and system-level energy thinking.
- **ANSI/AMCA 300-24** and **ANSI/AMCA 301-22**: only if sound data becomes a supported comparison axis.
- **ANSI/AMCA 270-23**: only if fan arrays become in scope.

Recommended public links to cite in the tool README / references section:

- <https://www.energy.gov/cmei/ito/fan-systems>
- <https://www.energy.gov/sites/default/files/2014/05/f16/fan_sourcebook.pdf>
- <https://www.amca.org/publish/publications-and-standards/amca-standards/amca-%EF%BB%BFstandard-210-07-laboratory-methods-of-testing-fans-for-certified-aerodynamic-performance-rating.html>
- <https://www.amca.org/publish/publications-and-standards/amca-publications/publication-201-02-%28r2011%29-fans-and-systems.html>
- <https://www.amca.org/publish/publications-and-standards/amca-standards/ansi/amca-standard-208-18-calculation-of-the-fan-energy-index.html>
- <https://www.amca.org/advocate/energy-efficiency-and-system-performance/about-fan-energy-index/>
- <https://www.amca.org/publish/publications-and-standards/amca-standards/amca-standard-205-19-energy-efficiency-classification-for-fans.html>
- <https://www.amca.org/publish/publications-and-standards/amca-publications/amca-publication-206-15-fan-efficiency-grade-%28feg%29-application-guide.html>
- <https://www.amca.org/publish/publications-and-standards/amca-standards/amca-standard-300-24-reverberant-room-methods-of-sound-testing-of-fans.html>
- <https://www.amca.org/publish/publications-and-standards/amca-standards/amca-standard-301-14-methods-for-calculating-fan-sound-ratings-from-laboratory-test-data.html>
- <https://www.amca.org/publish/publications-and-standards/amca-standards/ansi/amca-standard-270-23-laboratory-methods-of-aerodynamic-testing-fan-arrays-for-rating.html>
- <https://www.amca.org/certify/amca-certified-rating-program-search.html>

### Copyright / Standards Boundary

The tool should not republish copyrighted AMCA tables or protected standard text.

Safe implementation stance:

- let users import manufacturer or project-specific curve data,
- cite official standards and public AMCA/DOE pages in the references section,
- implement general engineering logic and transparent equations,
- avoid embedding protected tables unless the project has lawful access and clear permission to reproduce them.

This is especially important for:

- system-effect factor tables,
- preferred operating range guidance that is manufacturer-specific,
- any FEI baseline or classification material not clearly available for implementation.

---

## 17. Sample Data Strategy

The repo should ship with:

- one or two synthetic educational fan archetype datasets,
- one synthetic system-curve example,
- at least one comparison scenario that demonstrates why peak efficiency is not the same as best duty-point choice.

The repo should not initially ship with copied proprietary vendor curve libraries.

If public-domain or explicitly redistributable example curves are found later, they can be added with clear provenance.

---

## 18. Testing and Verification Strategy

The eventual implementation should include tests for:

- no-intersection cases,
- one-intersection nominal cases,
- density scaling,
- speed scaling,
- efficiency derivation when power is present,
- comparison ranking logic,
- basis mismatch warnings,
- malformed curve input rejection.

Known-value test cases should include:

- a simple synthetic fan/system intersection with hand-checkable numbers,
- a density-change case where pressure and power scale correctly,
- a speed-change case where affinity-law scaling produces the expected transformed curve.

---

## 19. Recommended Phasing

### Phase 1: Minimum Useful Tool

- Single fan + single system curve
- Imported pressure data
- Optional power/efficiency data
- Intersection solver
- Primary plot
- Basic derivation panel
- One-to-many comparison table
- Energy estimate

### Phase 2: Better Comparison and Education

- Learn mode with synthetic fan families
- RPM solving within allowed speed range
- Preferred operating range display when data exists
- User-saved scenarios / JSON import-export
- Improved warnings and explanation content

### Phase 3: Advanced System Use Cases

- Fan arrays
- Fans in series / parallel
- Sound-data comparison
- Expanded system-curve options
- Optional tie-ins to future duct or airflow tools

---

## 20. Final Recommendation

The first fan tool in this repo should be explicitly framed as a **selection and comparison tool with educational curve visualization**, not a generalized aerodynamic design engine.

That scope is:

- more honest,
- more implementable,
- more valuable to users,
- better aligned with the repo's design philosophy,
- and much easier to verify with transparent equations and synthetic test cases.

If the implementation stays data-driven, basis-explicit, and warning-heavy, it can become a strong engineering tool. If it tries to jump straight into "design a fan from a few geometry inputs," it will likely become misleading very quickly.
