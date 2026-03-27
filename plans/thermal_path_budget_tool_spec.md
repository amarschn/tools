# Generic Thermal Path Budget Tool Spec

> **Purpose:** Define a concrete product and implementation spec for a new generic steady-state thermal-path / resistance-network tool. This is intended as a handoff document for future implementation work and as a boundary document relative to `simple_thermal` and `motor-hotspot`.

---

## 1. Why This Tool Exists

The current flat plate-fin heatsink designer is increasingly capable, but many users reach for it when their real problem is not "design this heatsink geometry."

Their actual problem is closer to:

- "What temperature will each node in my thermal stack reach?"
- "Which segment of the path is dominating the temperature rise?"
- "How good does the interface or sink need to be?"
- "Can I compare two thermal paths before I know the final geometry?"

Those questions are common in:

- early concept design,
- module and package budgeting,
- motor or enclosure thermal paths,
- nonstandard assemblies,
- vendor-datasheet resistance stacking,
- sanity checks before detailed geometry work.

That problem deserves its own tool.

### Strategic role

This tool should catch users who are currently forcing non-plate-fin problems into `simple_thermal` only because it is the closest available thermal page.

It also creates a clean bridge between:

- geometry-specific steady-state tools,
- spreading / chassis tools,
- and future transient RC tools.

---

## 2. Tool Positioning

### What this tool is

A **generic steady-state thermal network solver** for thermal resistance chains and simple branching networks.

It should answer:

- node temperatures,
- segment temperature drops,
- total path resistance,
- dominant bottlenecks,
- required maximum resistance for a segment to meet a temperature target.

### What this tool is not

It is **not**:

- a heatsink geometry optimizer,
- a CFD substitute,
- a transient thermal model,
- a motor-specific estimator,
- a replacement for `simple_thermal`.

### Relationship to `simple_thermal`

`simple_thermal` should remain the authoritative tool for:

- flat rectangular bases,
- straight plate-fin heatsinks,
- aligned air flow,
- and geometry-driven sink performance.

The thermal-path tool should be used when:

- geometry is unknown,
- geometry is out of scope,
- only datasheet / estimated `R_theta` values are known,
- or the user primarily needs a thermal budget rather than a sink design.

### Relationship to `motor-hotspot`

`tools/motor-hotspot/` is a **specialized transient inference tool** that reconstructs an internal hot-spot temperature from cooldown data.

This new tool should not duplicate that workflow.

Instead:

- `motor-hotspot` stays focused on post-shutdown estimation and fitted RC behavior,
- the new thermal-path tool handles **steady-state** node temperatures and resistance budgets,
- future transient RC work can later share backend abstractions across both.

---

## 3. Product Goal

Create a thermal tool that is:

- simpler and more honest than misusing a geometry-specific heatsink page,
- rigorous enough for expert review,
- useful for electronics, housings, motors, modules, and enclosure paths,
- structured around progressive disclosure and decision support instead of only equations.

The user should be able to get a meaningful first answer in under a minute using a standard template, then progressively refine the model if needed.

---

## 4. Target Use Cases

### Good fit

- Junction -> case -> TIM -> spreader -> sink -> ambient budgeting
- Housing or chassis temperature prediction from known upstream losses
- Comparing alternate interface materials or mounting assumptions
- Estimating required sink-to-ambient resistance from a temperature target
- Modeling dual thermal paths, such as:
  - case to sink and case to PCB,
  - winding to housing and winding to shaft,
  - module to cold plate and module to enclosure wall
- Sanity-checking vendor datasheet `R_theta` stacks

### Use with caution

- Large distributed heat sources where a lumped network may hide spreading limits
- Strongly temperature-dependent materials not represented in the inputs
- Systems with significant radiation dominance unless radiation is explicitly represented
- Problems with poorly known contact conditions

### Out of scope

- Detailed heatsink geometry synthesis
- Transient duty-cycle or startup heating
- Natural-convection correlation selection
- Fan / system curve intersection
- Nonlinear phase-change devices
- Full 2D or 3D conduction fields
- Severe temperature-dependent nonlinearity beyond a simple iterative correction

---

## 5. Core User Questions

The UI and outputs should be organized around these questions:

1. What node is hottest?
2. Where is the largest temperature drop?
3. Which segment should I improve first?
4. What maximum resistance is allowable for each segment?
5. Is this network abstraction appropriate for my problem at all?

This is the right disclosure frame for the tool. It is more useful than presenting a list of equally weighted thermal resistances and equations.

---

## 6. Scope

### 6.1 MVP scope

The first shipped version should support:

- steady-state only,
- one ambient boundary temperature,
- one or more heat inputs at defined nodes,
- series chains,
- simple parallel branches,
- node temperature solve,
- segment temperature-drop breakdown,
- required-resistance solve for one selected unknown segment,
- sensitivity view for selected segments,
- network diagram visualization,
- exportable calculation report.

### 6.2 Deferred scope

Do not put these into v1:

- fully arbitrary graph editing,
- transient capacitance / RC dynamics,
- automatic geometry inference,
- multi-ambient / conjugate heat transfer problems,
- Monte Carlo uncertainty analysis,
- empirical fan or natural-convection correlations,
- coupled electrical loss estimation.

The first version should be a strong steady-state budget tool, not a universal thermal simulator.

---

## 7. Progressive Simplicity and Disclosure

This tool should be a model example of the repo's design principles.

### L0: Summary

Show immediately:

- hottest node temperature,
- target margin,
- total path `R_theta`,
- dominant bottleneck segment,
- overall status.

### L1: Network Breakdown

Show:

- each node in order,
- each segment resistance,
- each segment `Delta T`,
- percent contribution to total rise.

This layer should answer "what is driving the result?" without making the user read equations.

### L2: Equations and Substitution

For each computed result, show:

- governing equation,
- substituted values,
- segment-level math,
- clear variable legends.

### L3: Intermediate Logic

Show optional deeper detail for:

- parallel-path equivalent resistance,
- required-resistance back-solves,
- temperature-source handling,
- contact-resistance derivations from thickness / conductivity / area.

### L4: Applicability

Show:

- where a lumped network is a good abstraction,
- when spreading or geometry-specific tools are better,
- how to map physical hardware into nodes responsibly.

### L5: References and Recipes

Include:

- background on thermal circuits,
- example mapping recipes,
- common node definitions,
- references and caveats.

---

## 8. Workflow

The workflow should be staged so the user does not start with an empty graph editor.

### Step 1 — Choose a modeling template

Offer a small set of templates:

- `Simple chain`
- `Package to sink`
- `Housing / wall path`
- `Dual path to ambient`
- `Custom network`

This keeps time-to-value short.

### Step 2 — Choose boundary condition mode

Support these modes:

- `Analyze temperatures`
- `Size one segment for a target`
- `Budget required sink resistance`
- `Compare two path options`

This avoids forcing every user into the same target language.

### Step 3 — Define nodes and segments

For MVP, do this with a structured list, not a free-form canvas.

Each segment should define:

- label,
- resistance mode,
- numeric value or derived inputs,
- notes / assumptions,
- optional category.

Each node should define:

- label,
- heat input if any,
- target limit if relevant,
- optional display name.

### Step 4 — Review diagnosis

Results should immediately answer:

- pass/fail,
- hottest node,
- biggest drop,
- required improvement,
- applicability notes.

### Step 5 — Expand into derivations / report

Experts can then inspect:

- the full path math,
- equivalent resistances,
- substituted equations,
- and assumptions.

---

## 9. Solver Model

### 9.1 Conceptual abstraction

Represent the problem as a thermal resistor network:

- nodes carry temperatures,
- edges carry thermal resistances,
- heat inputs are applied at nodes,
- ambient or fixed-temperature boundaries anchor the system.

This is the thermal analogue of a resistive circuit.

### 9.2 Mathematical basis

For a segment between nodes `i` and `j`:

`Q_ij = (T_i - T_j) / R_ij`

For each unknown-temperature node:

`sum(Q_in) - sum(Q_out) + Q_applied = 0`

This yields a linear system in the unknown node temperatures.

### 9.3 Required-resistance mode

The tool should also support solving for one unknown segment resistance when:

- a target node temperature is specified,
- all other resistances are known,
- and the topology remains linear.

For MVP, limit this to one selected unknown segment at a time.

### 9.4 Parallel paths

Parallel paths should be supported in two forms:

- explicit network solve from the node equations,
- simplified equivalent-resistance presentation in the derivation layer.

The tool should never force the user to manually collapse parallel branches unless they want to.

### 9.5 Nonlinear extensions

Hold off on general nonlinear solvers for v1.

If a temperature-dependent resistance correction is added later, it should be:

- explicit,
- iterative,
- and clearly marked as an advanced approximation.

---

## 10. Recommended Data Model

The backend should use a canonical graph-like data model even if the frontend presents templates.

Suggested structure:

```python
{
    "mode": "analyze_temperatures",
    "ambient_temperature": 40.0,
    "nodes": [
        {"id": "source", "label": "Junction", "heat_w": 25.0, "fixed_temperature_c": None},
        {"id": "case", "label": "Case"},
        {"id": "sink", "label": "Sink Base"},
        {"id": "ambient", "label": "Ambient", "fixed_temperature_c": 40.0},
    ],
    "segments": [
        {"id": "r_jc", "from": "source", "to": "case", "mode": "direct", "r_theta_k_per_w": 0.4},
        {"id": "r_cs", "from": "case", "to": "sink", "mode": "tim_conductivity", ...},
        {"id": "r_sa", "from": "sink", "to": "ambient", "mode": "direct", "r_theta_k_per_w": 2.0},
    ],
}
```

### Design rules

- Every node and segment needs a stable id.
- Every computed resistance should retain its source inputs.
- The same segment object should drive:
  - solving,
  - reporting,
  - diagrams,
  - export,
  - derivation disclosure.

This is critical for single-source-of-truth behavior.

---

## 11. Resistance Input Modes

This tool becomes much more useful if segment resistances can be defined in more than one way.

### Required segment modes for MVP

- `direct`
  - user enters `R_theta` directly
- `tim_area_normalized`
  - user enters impedance per area and contact area
- `tim_conductivity`
  - user enters thickness, conductivity, and contact area
- `derived_from_total_and_other_segments`
  - used for required-resistance budgeting results

### Good early extensions

- `simple_conduction_slab`
  - `R = t / (k A)`
- `lookup_from_datasheet`
  - convenience mode backed by a preset library later

This is one of the key advantages of the generic path tool: it can translate between physical assumptions and lumped network values explicitly.

---

## 12. UI Structure

### Main tabs

- `Model`
- `Results`
- `Math`
- `Background`

### Model tab sections

- Template and mode
- Boundary conditions
- Node / segment editor
- Assumptions and applicability

### Results tab sections

- Summary banner
- Network diagram
- Node temperature table
- Segment drop / contribution table
- Bottleneck diagnosis
- Sensitivity chart

### Math tab sections

- Path equations
- Equivalent resistance steps
- Node balance equations
- Substituted values
- Required-resistance back-solve

### Background tab sections

- How to map hardware into a thermal network
- When not to use a lumped network
- Worked examples
- Reference equations

---

## 13. Visualization Recommendations

This tool needs a visualization that explains the network immediately.

### Primary visualization

A left-to-right thermal path diagram with:

- nodes as labeled blocks,
- segments as links with `R_theta`,
- `Delta T` annotations,
- the hottest node highlighted,
- branch splits shown explicitly when parallel paths exist.

### Secondary visuals

- stacked temperature-drop bar from hot node to ambient,
- contribution bar chart by segment,
- one-at-a-time sensitivity sweep for selected segments.

### Important rule

The diagram should reflect the solved network data, not a separately hand-authored UI diagram.

If the network changes, the diagram, tables, export, and derivation views must all update from the same data.

---

## 14. Output Requirements

### Core outputs

- hottest node temperature
- all node temperatures
- total path `R_theta`
- total rise above ambient
- segment `Delta T`
- percent contribution by segment
- status
- recommendations

### Diagnostic outputs

- dominant bottleneck segment
- required maximum `R_theta` for the selected segment
- margin to each node limit
- warnings about unsupported abstraction or missing data

### Disclosure outputs

- substituted equations for all major computed values
- intermediate equivalent-resistance calculations
- node-balance equations
- input provenance for each resistance

### Export outputs

The export should include:

- all inputs,
- all solved temperatures,
- all segment definitions,
- all assumptions,
- all derivation strings needed for audit.

The report should be complete enough that the user does not need the live UI to understand the model.

---

## 15. Guardrails and Applicability Guidance

This tool will be easy to misuse if it simply accepts any thermal network description without critique.

### Required guidance

- Warn when the user appears to be collapsing a clearly geometry-dominant problem into one resistance without noting that assumption.
- Warn when multiple major heat sources are being forced into a single-node model without explanation.
- Warn when a user selects a use case that is better handled by:
  - `simple_thermal`,
  - a future spreader-plate tool,
  - or a future transient RC tool.

### Applicability examples

- `Good fit`
  - vendor `R_theta,jc`, TIM estimate, sink `R_theta,sa`, ambient target
- `Use with caution`
  - motor frame path with uncertain internal hotspot-to-frame resistance
- `Better in another tool`
  - detailed extruded sink sizing,
  - plate spreading hotspot mapping,
  - cooldown or duty-cycle prediction

---

## 16. Shared Backend Architecture

This tool should help force a cleaner shared thermal backend.

### Recommended Python modules

- `pycalcs/thermal_budget.py`
  - node temperature helpers
  - margin logic
  - required-resistance calculations
- `pycalcs/thermal_contact.py`
  - TIM conversions
  - bondline / conductivity calculations
- `pycalcs/thermal_networks.py`
  - canonical network solver
  - equivalent-resistance helpers
  - serialization-ready data structures

### Key rule

The generic network equations should live in `pycalcs/thermal_networks.py` and be reused later by:

- the transient RC tool,
- possible export/report tooling,
- and any other page that needs thermal-path budgeting.

Do not bury generic network math inside a tool-local script.

---

## 17. Suggested Frontend Implementation Strategy

### Phase A — MVP

Ship:

- template-driven structured model entry,
- series chains,
- one simple branched topology,
- temperature solve,
- one unknown-segment sizing mode,
- diagram,
- results table,
- derivation report.

This should already be useful.

### Phase B — Strong steady-state tool

Add:

- richer branch handling,
- compare-two-options mode,
- presets for common thermal stacks,
- better applicability scoring,
- export polish.

### Phase C — Platform foundation

Use the shared backend to support:

- future transient RC work,
- cross-links from `simple_thermal`,
- possible import/export of saved thermal stacks.

---

## 18. Worked Example Templates To Support

The first version should ship with example templates such as:

- `Junction -> Case -> TIM -> Sink -> Ambient`
- `Power Module -> Baseplate -> Cold Plate`
- `Housing -> Interface -> Chassis Wall -> Ambient`
- `Node with dual path: Sink and PCB`
- `Motor winding -> frame -> sink -> ambient` with a caution note

These examples are important because they teach users how to map physical hardware into a defensible thermal network.

---

## 19. Open Questions for Implementation

These should be resolved before coding begins:

1. Should custom networks in v1 allow arbitrary node linking, or only approved topology templates?
   Recommendation: topology templates plus a restrained custom mode.
2. Should the first version permit more than one heat-input node?
   Recommendation: yes, but keep one input as the default template.
3. How should unknown-segment sizing work when multiple node limits are defined?
   Recommendation: v1 should size against one selected controlling limit only and report other margins secondarily.
4. Should radiation be a first-class segment type in v1?
   Recommendation: no. Treat it later or let users enter an equivalent `R_theta` directly.

---

## 20. Success Criteria

This tool is successful if it:

- reduces misuse pressure on `simple_thermal`,
- gives users a trustworthy thermal-budget workflow when geometry is unknown or out of scope,
- clearly identifies bottlenecks and required improvements,
- supports progressive disclosure without drowning the default UI in equations,
- and establishes reusable backend network infrastructure for future thermal tools.

---

## 21. Recommended Immediate Next Step

The coding-adjacent schema and API contract now live in:

- [plans/thermal_path_budget_tool_schema.md](/Users/drew/code/tools/plans/thermal_path_budget_tool_schema.md)

That document defines:

- the canonical network schema,
- the Python API signature for `pycalcs/thermal_networks.py`,
- validation rules,
- and the exact solved results / derivation payload expected by the frontend.
