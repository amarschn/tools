# Future Thermal Tool Family Plan

> **Purpose:** Define which thermal / heatsink problems should stay inside the current plate-fin heatsink designer and which should become separate tools. This is a product-boundary plan, not a commitment to implement every tool immediately.

---

## 1. Decision Principle

The current `tools/simple_thermal/` page should **not** become a universal heatsink calculator.

That would create:

- ambiguous labels,
- incompatible assumptions hidden behind toggles,
- a combinatorial UI,
- weaker validation,
- lower trust.

Instead, the project should aim for a **thermal tool family**:

- separate tools for materially different physical problem classes,
- shared backend equations and utilities in `pycalcs`,
- clear routing so users land in the correct tool early.

### Guiding rule

Create a new tool when one or more of these changes materially:

1. the geometry family,
2. the airflow topology,
3. the boundary-condition language,
4. the dominant user decision flow,
5. the core solver abstraction.

If those remain the same, broaden the existing tool.

---

## 2. What Should Stay in `simple_thermal`

The current tool should remain the authoritative calculator for:

- flat rectangular base,
- straight plate-fin heatsink,
- air cooling,
- channel-aligned flow or simple fan/system intersection,
- steady-state analysis,
- one or more localized or distributed heat-entry patches on a flat base.

### Safe expansions inside the existing tool

These are still coherent with the current solver family:

- boundary-condition modes:
  - target source/junction temperature,
  - target case temperature,
  - target base temperature,
  - required sink `R_theta` only
- separate `heat-entry area` and `contact area`
- flat housing / motor pad archetype
- multiple rectangular source patches on the same flat base
- better applicability scoring and out-of-scope gating
- richer derivation and diagnosis views

### Examples that still belong here

- IC package on extruded plate-fin heatsink
- power module on flat finned baseplate
- flat motor housing pad bolted to an external plate-fin sink
- chassis-mounted plate-fin sink with one dominant contact patch

---

## 3. When To Split Into Separate Tools

The following problem classes should become separate tools rather than feature-creeping the current plate-fin page.

### 3.1 Radial-Fin / Cylindrical-Body Heatsink Tool

#### Why separate

This is not a small variant of a plate-fin sink.

It changes:

- geometry representation,
- fin spacing logic,
- characteristic lengths,
- natural-convection behavior,
- user mental model.

#### Should address

- cylindrical or near-cylindrical bodies
- radial fins around motors or round housings
- body-to-air cooling with or without external shrouding
- natural convection around vertical/horizontal cylinders
- forced flow across radial fins
- circumferential fin count and spacing
- outer diameter, body diameter, fin thickness, fin length, axial length

#### Typical users / use cases

- motor housings with integral radial fins
- cylindrical LED or power housings
- round enclosures with finned shells
- TO-can or round-body cooling approximations

#### Explicitly different from `simple_thermal`

- no flat rectangular base assumption
- no plate-channel flow assumption
- no rectangular spreading overlay as the primary abstraction

#### Suggested outputs

- body temperature
- fin efficiency
- effective external area
- natural vs forced convection estimate
- applicability warnings for orientation / enclosure / crossflow

---

### 3.2 Spreader Plate / Chassis Wall Thermal Tool

#### Why separate

Many users are not designing a discrete heatsink; they are using:

- a chassis wall,
- an enclosure panel,
- a spreader plate,
- a cold plate-like panel with mild convection.

The problem is conduction-dominant first and fin-convection second, if fins exist at all.

#### Should address

- flat plates acting as spreaders
- one or multiple heat-entry patches
- conduction through plate thickness and in-plane spreading
- convection from one side or both sides
- optional attached fins as a later extension
- mounted electronics or modules on enclosure walls
- chassis heat spreading before air rejection

#### Typical users / use cases

- electronics bolted to an aluminum wall
- LED boards mounted to a chassis panel
- battery enclosure wall as a heat spreader
- power module on a plain aluminum plate

#### Suggested outputs

- peak plate temperature
- average plate temperature
- spreading map
- contribution of convection vs plate spreading
- sensitivity to thickness, conductivity, and mounting area

#### Relationship to current tool

This would likely reuse the base-plane spreading ideas already added to `simple_thermal`, but with a different top-level workflow and without pretending a finned sink is always present.

---

### 3.3 Generic Thermal Path / Resistance-Network Tool

#### Why separate

Some users do not need a geometry-specific heatsink model at all.

They need a clean way to model:

- source,
- case,
- interface,
- spreader,
- sink,
- ambient,

as a thermal network with optional parallel paths.

#### Should address

- generic steady-state thermal resistance chains
- optional branching paths
- known `R_theta` values from datasheets or test data
- what-if budget analysis
- temperature-node solves
- series and parallel thermal networks

#### Typical users / use cases

- early concept design
- systems where geometry is unknown but resistances are estimated
- thermal stack budgeting
- comparing whether upstream path or sink path dominates
- nonstandard assemblies where a geometry-specific heatsink solver is not appropriate

#### Suggested outputs

- node temperatures
- temperature drop by segment
- sensitivity to each resistance
- required maximum resistance for each segment
- network diagram and derivation tree

#### Why this matters strategically

This tool would catch a large class of users who currently misuse the plate-fin tool just because it is the closest available thermal page.

---

### 3.4 Transient Thermal Stack / RC Tool

#### Why separate

Steady-state and transient questions are different products.

Transient design introduces:

- thermal capacitance,
- time constants,
- duty cycles,
- startup and overload behavior,
- pulse-power questions.

That is a different workflow and solver family.

#### Should address

- thermal RC ladders
- step-load response
- pulsed duty cycles
- cooldown / warmup behavior
- time to limit
- junction / case / base / ambient transient curves

#### Typical users / use cases

- intermittent duty electronics
- overload windows
- motor startup heating approximations
- thermal soak time
- whether a design is safe for pulses but not continuous load

#### Suggested outputs

- temperature vs time plots
- peak temperature during pulse
- steady-state asymptote
- dominant time constants
- allowable duty cycle for a target limit

#### Shared backend potential

This tool should reuse the steady-state thermal-path abstractions and build an RC network layer on top of them.

---

### 3.5 Pin-Fin / Impingement / Non-Channel Forced-Air Tool

#### Why separate

These are not just “advanced cooling modes” for plate-fin sinks.

They involve different:

- geometry families,
- convection correlations,
- pressure-drop behavior,
- applicability language.

#### Should address

- pin-fin heatsinks
- impingement-cooled sinks
- non-channel forced-air topologies
- blower/plenum-fed arrays
- strong crossflow cases

#### Typical users / use cases

- forced-air electronics cooling with non-extruded sinks
- blower-fed compact devices
- top-down jet cooling approximations

#### Suggested outputs

- sink thermal resistance
- pressure drop / required fan capability
- velocity sensitivity
- geometry tradeoffs specific to pin-fin or impingement cases

#### Priority

This is likely lower priority than:

- the generic thermal-path tool,
- the spreader/chassis tool,
- and the radial-fin tool.

---

## 4. Proposed Shared Backend Refactor

If multiple thermal tools are added, shared equations should move into reusable `pycalcs` modules instead of being duplicated.

### Candidate module structure

- `pycalcs/thermal_air.py`
  - air properties
  - film-temperature helpers
- `pycalcs/thermal_contact.py`
  - TIM conversions
  - bondline-based contact resistance
  - contact-area helpers
- `pycalcs/thermal_budget.py`
  - required sink resistance
  - temperature-margin calculations
  - node-stack helpers
- `pycalcs/thermal_spreading.py`
  - spreading resistance
  - base-plane spreading solvers
- `pycalcs/thermal_fans.py`
  - parabolic fan curves
  - tabular fan curves
  - fan/system intersection helpers
- `pycalcs/heatsink_plate_fin.py`
  - current straight plate-fin solver family
- `pycalcs/heatsink_radial.py`
  - future radial-fin / cylindrical-body solver family
- `pycalcs/thermal_networks.py`
  - generic resistance-network solver
- `pycalcs/thermal_transient.py`
  - RC transient solver utilities

### Key rule

Every equation should live in one canonical backend implementation, even if multiple tools expose it with different UI language.

---

## 5. Proposed Tool Boundaries

### Tool 1 — Plate-Fin Heatsink Designer

Path:
- existing `tools/simple_thermal/`

Owns:
- flat plate-fin geometry
- aligned flow
- fan/system curves
- spreading on flat rectangular bases

Does **not** own:
- radial bodies
- pin-fin
- generic resistance networks
- transient thermal RC analysis

### Tool 2 — Radial / Cylindrical Heatsink Estimator

Proposed scope:
- round bodies
- radial fins
- motor or cylindrical enclosure cooling

### Tool 3 — Spreader Plate / Chassis Thermal Tool

Proposed scope:
- flat plates
- multiple sources
- enclosure walls
- non-finned spreaders or weakly finned panels

### Tool 4 — Thermal Path Budget Tool

Proposed scope:
- generic `R_theta` chain / network
- no commitment to a specific geometry family

Implementation spec:
- see [plans/thermal_path_budget_tool_spec.md](/Users/drew/code/tools/plans/thermal_path_budget_tool_spec.md)
- API/schema contract: [plans/thermal_path_budget_tool_schema.md](/Users/drew/code/tools/plans/thermal_path_budget_tool_schema.md)

### Tool 5 — Transient Thermal Tool

Proposed scope:
- RC networks
- pulse/duty-cycle behavior

### Tool 6 — Pin-Fin / Impingement Tool

Proposed scope:
- non-channel forced cooling
- specialized sink families

---

## 6. Suggested Priority Order

If the repo expands into a thermal tool family, the recommended order is:

1. **Keep `simple_thermal` scoped and trustworthy**
   - archetype gating
   - boundary-condition modes
   - source/contact split
   - applicability scorecard
2. **Generic Thermal Path Budget Tool**
   - high leverage
   - catches many currently misfit use cases
3. **Spreader Plate / Chassis Tool**
   - strong overlap with existing spreading work
   - highly practical for electronics and enclosure problems
4. **Radial / Cylindrical Heatsink Tool**
   - addresses motors and radial bodies cleanly
5. **Transient Thermal Tool**
   - useful, but only after steady-state boundaries are clearer
6. **Pin-Fin / Impingement Tool**
   - likely most specialized and lowest immediate leverage

---

## 7. Routing Guidance

Long term, the thermal tools should not rely on users choosing correctly from a giant catalog.

There should be a lightweight routing layer asking:

1. Is your cooling body flat or cylindrical?
2. Are you designing a finned sink, a spreader plate, or only a thermal path budget?
3. Do you need steady-state or transient behavior?

Then direct the user to the appropriate tool.

This can live as:

- a future thermal landing page,
- a modal launcher,
- or a decision card on the current `simple_thermal` page.

---

## 8. Practical Product Guidance

### Broadening `simple_thermal` is good when:

- the hardware is still a flat plate-fin sink problem,
- the main changes are labels, targets, or contact/spreading interpretation,
- the governing solver family is unchanged.

### Creating a new tool is better when:

- the geometry family changes,
- the airflow topology changes,
- the primary user question changes,
- the vocabulary changes enough that reuse would confuse users,
- solver assumptions stop being honest.

---

## 9. Recommended Roadmap Language

The project should explicitly adopt this position:

> The current heatsink designer is the flat plate-fin authority, not the universal thermal authority.

Future breadth should come from:

- shared physics modules,
- clear tool boundaries,
- and honest routing,

not from endlessly adding toggles to one page.

---

## 10. Bottom Line

Yes, the repo should support more heatsink and thermal problem types over time.

But the right strategy is:

- **multiple focused tools**
- **shared backend equations**
- **clear boundaries**
- **explicit applicability**

not one all-purpose UI with hidden assumptions.
