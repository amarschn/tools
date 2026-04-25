# Transient Heatsink Tool Plan

Date: 2026-04-25
Status: Proposed implementation plan for critique before development

> Purpose: Define a focused transient heatsink tool that predicts warmup,
> cooldown, pulse survival, duty-cycle sustainability, and time-to-limit for
> heatsink assemblies. This plan positions the tool relative to the existing
> steady-state plate-fin heatsink designer, thermal-path budget tool, and
> motor-specific thermal tools.

---

## 1. Why This Tool Exists

The current thermal tools answer mostly steady-state questions:

- `tools/simple_thermal/` answers "what will this plate-fin heatsink do at
  steady state?"
- `tools/thermal-path-budget/` answers "what temperatures result from this
  steady-state resistance network?"
- `tools/motor-thermal/` and `tools/motor-hotspot/` cover motor-specific
  thermal estimates and cooldown reconstruction.

Many real heatsink decisions are transient:

- Can the assembly survive a short overload?
- How long can the product run before the source exceeds its limit?
- Is a duty cycle thermally sustainable?
- How much cooldown time is needed between pulses?
- Does extra heatsink mass help enough to justify the weight and size?
- Does a fan delay, fan ramp, or startup condition create a temporary limit?

Those are not steady-state sizing questions. They require thermal capacitance,
time-varying power, and temperature-vs-time output.

### Strategic Role

This tool should be the transient counterpart to the plate-fin heatsink
designer and the thermal-path budget tool. It should reuse their resistances
and geometry-derived estimates, but its primary product is time behavior rather
than a static temperature budget.

---

## 2. Tool Positioning

### What This Tool Is

A transient thermal RC simulator for common heatsink assemblies.

It should answer:

1. Time until a source, case, base, or sink node reaches a temperature limit.
2. Peak temperature during a pulse or repeated duty cycle.
3. Final cyclic steady-state temperatures for repeating loads.
4. Cooldown time after power is removed.
5. Which node, resistance, or capacitance controls the transient response.

### What This Tool Is Not

It is not:

- a CFD tool,
- a full arbitrary thermal-network editor in v1,
- a replacement for `simple_thermal`,
- a detailed semiconductor transient thermal impedance curve fitter,
- a motor-only thermal model,
- a detailed phase-change or heat-pipe transient model.

### Relationship To Existing Tools

#### `simple_thermal`

Use `simple_thermal` when the main question is steady-state plate-fin heatsink
geometry, convection, fin efficiency, pressure drop, or fan operating point.

Use this new transient tool when the main question is how quickly the same
assembly warms, cools, or responds to pulses.

The transient tool can optionally call the steady-state plate-fin solver to
derive sink-to-ambient resistance, pressure-drop context, surface area, volume,
and sink mass.

#### `thermal-path-budget`

Use `thermal-path-budget` when only scalar resistances are known and the user
wants a steady-state node-temperature budget.

Use this new transient tool when those same nodes also need thermal capacitance
and time-varying heat input.

The transient tool should share model vocabulary with the thermal-path tool:
nodes, segments, heat inputs, fixed-temperature boundary, resistance modes, and
diagnosis language.

#### `motor-hotspot`

`motor-hotspot` estimates hidden winding temperature from cooldown data. It is
an inference tool driven by measured sensor data.

The transient heatsink tool is a forward simulator driven by planned heat loads,
thermal resistances, capacitances, and heatsink assumptions.

---

## 3. Core User Questions

The UI should be organized around these questions:

1. How long can I run before I hit the temperature limit?
2. What peak temperature will a pulse or repeated duty cycle create?
3. Does the design reach a safe cyclic steady state?
4. How much cooldown time do I need?
5. Is the bottleneck resistance-limited, capacitance-limited, or both?
6. Would improving the interface, sink resistance, or heatsink mass help most?

This framing is more useful than exposing a blank RC graph first.

---

## 4. MVP Scope

The first version should support:

- transient thermal RC simulation,
- one fixed ambient boundary,
- one primary heat-input node,
- one to four dynamic thermal nodes,
- series thermal paths,
- optional plate-fin heatsink resistance and mass estimation from existing
  `pycalcs.heatsinks` functions,
- known-resistance mode for users with datasheet `R_theta` values,
- known-capacitance mode for users with measured or estimated heat capacity,
- step, pulse, and repeating duty-cycle power profiles,
- time-to-limit solve,
- cooldown-time solve,
- temperature-vs-time plots,
- power-vs-time plot,
- RC ladder visualization,
- exportable JSON and CSV summary,
- substituted-equation strings for the governing RC model and key time
  constants.

### User-Facing Templates

Start with opinionated templates instead of arbitrary graph editing:

1. **Single Lump**
   - Source and heatsink treated as one lumped thermal mass.
   - Inputs: heat load, ambient, total `R_theta`, total thermal capacitance.
   - Best for fast sanity checks and measured systems.

2. **Package On Heatsink**
   - Junction/source, case/base, heatsink, ambient.
   - Inputs: `R_jc`, `R_cb` or TIM, `R_sa`, source/case/sink capacitances.
   - Best for power electronics and IC packages.

3. **Plate-Fin Heatsink From Geometry**
   - Uses the existing plate-fin solver for `R_sa`.
   - Estimates sink thermal capacitance from volume, density, and specific heat.
   - Best when the user has a physical heatsink geometry.

4. **Known Thermal Path**
   - Imports or mirrors a simple series chain from the thermal-path budget
     vocabulary.
   - Best when resistances come from datasheets or previous estimates.

### Deferred Scope

Do not put these into v1:

- arbitrary graph editing,
- multiple heat sources,
- multiple ambients,
- nonlinear radiation-only transient solving,
- temperature-dependent material properties,
- fan speed control loops,
- detailed fan spin-up dynamics,
- heat pipes and phase-change devices,
- JEDEC-style transient thermal impedance curve fitting,
- PCB spreading models,
- Monte Carlo uncertainty,
- CSV custom power profiles beyond a simple table/paste prototype.

---

## 5. Physical Model

### Governing Equation

For each dynamic thermal node:

```text
C_i dT_i/dt = Q_i(t) + sum_j((T_j - T_i) / R_ij)
```

Where:

- `C_i` is thermal capacitance of node `i` in J/K.
- `T_i` is node temperature in C.
- `Q_i(t)` is heat injected into node `i` in W.
- `R_ij` is thermal resistance between connected nodes in K/W.

The ambient node is fixed:

```text
T_ambient(t) = T_ambient
```

For a one-lump system:

```text
T(t) = T_ambient + Q R (1 - exp(-t / (R C))) + (T_initial - T_ambient) exp(-t / (R C))
```

The tool should use the analytical one-lump solution for explanation and
validation, but use the general numerical solver for all templates.

### Solver Choice

Use an implicit Euler or trapezoidal linear solve for the RC network.

Reason:

- Thermal systems can have very different time constants.
- Explicit Euler can become unstable or require tiny time steps.
- The network equations are linear when resistances and capacitances are fixed.
- A small dense linear solve is feasible in Pyodide for v1 node counts.

For each time step:

```text
(C / dt + L_uu) T_next = C / dt T_current + Q_next + boundary_terms
```

Where `L_uu` is the conductance Laplacian for unknown dynamic nodes. Boundary
conductances to ambient contribute to the diagonal of `L_uu` and add
`G_boundary T_boundary` terms to the right-hand side. Test matrix signs against
the analytical one-lump response.

### Time Step Strategy

Default automatic time-step selection:

- Estimate time constants from `R*C` values.
- Use at least 25 samples across the shortest important event duration.
- Use at least 50 samples across the smallest dominant time constant.
- Cap default result arrays around 2000 points for browser responsiveness.
- Allow expert override for `dt` and total simulation time.

For duty cycles, simulate until one of these conditions is met:

- requested number of cycles is reached,
- cyclic steady state is detected,
- a temperature limit is exceeded,
- maximum simulation time is reached.

Cyclic steady-state criterion:

```text
max_abs(T_end_of_cycle - T_start_of_cycle) < tolerance_c
```

Default tolerance: `0.05 C`.

---

## 6. Input Model

### Required Default Inputs

Minimal visible inputs:

- Heat load, W
- Ambient temperature, C
- Maximum allowed source temperature, C
- Power profile type
- Run time or pulse/duty settings
- Thermal model template
- Sink-to-ambient definition:
  - known `R_sa`, or
  - derive from plate-fin geometry

### Power Profiles

#### Step Load

Inputs:

- power, W
- run duration, s or min
- initial temperature, C

Outputs:

- time to limit,
- temperature at end of run,
- steady-state asymptote.

#### Single Pulse

Inputs:

- pulse power, W
- pulse duration,
- cooldown duration,
- initial temperature.

Outputs:

- peak temperature,
- temperature after cooldown,
- limit margin during pulse,
- cooldown time to target.

#### Repeating Duty Cycle

Inputs:

- on power, W
- on time,
- off power, W, default `0`
- off time,
- number of cycles or auto steady-cycle.

Outputs:

- first-cycle peak,
- final-cycle peak,
- final-cycle minimum,
- cyclic steady-state status,
- accumulated thermal walk-up.

### Expert Inputs

Expert mode should expose:

- node capacitance overrides,
- source capacitance,
- case/base capacitance,
- heatsink capacitance,
- contact/interface resistance,
- source-to-case resistance,
- base-to-sink resistance,
- initial temperature by node,
- ambient ramp or fixed ambient,
- integration time step,
- convergence tolerance,
- maximum number of cycles,
- known starting condition from previous run.

---

## 7. Thermal Capacitance Estimation

Thermal capacitance:

```text
C = m c_p = rho V c_p
```

The tool should provide presets for density and heat capacity:

| Material | Density kg/m3 | Heat capacity J/kg-K | Notes |
| --- | ---: | ---: | --- |
| Aluminum 6063 | 2700 | 900 | Default extruded heatsink material |
| Aluminum 6061 | 2700 | 896 | Common machined plate/sink |
| Copper C110 | 8960 | 385 | High mass and conductivity |
| Steel | 7850 | 470 | Chassis and brackets |
| FR-4 effective | 1850 | 900 | Approximate PCB lump |
| Silicon | 2330 | 700 | Die/source approximation |
| Generic package | user | user | For measured or vendor data |

For plate-fin geometry, reuse `calculate_plate_fin_geometry()` volume:

```text
C_sink = rho V_sink c_p
```

For source/package capacitance, default to manual preset values rather than
pretending geometry is usually known. Provide "small IC", "power module", and
"custom" presets with clear approximate warnings.

---

## 8. Output Design

### L0 Summary Cards

Show immediately:

- Time to limit
- Peak source temperature
- Peak sink/base temperature
- Final or cyclic steady-state source temperature
- Cooldown time to target
- Overall status

Status examples:

- `acceptable`: no node exceeds limit and cyclic steady state is reached.
- `marginal`: final peak is within 10 percent of the allowable rise.
- `unacceptable`: limit exceeded.
- `not_converged`: requested duty cycle did not reach a cyclic steady state
  within limits.

### L1 Plots

Primary plot:

- source, case/base, sink temperatures vs time,
- temperature limit line,
- ambient line,
- hover labels with node and cycle information.

Secondary plot:

- power vs time,
- cycle markers for duty mode.

### L2 RC Breakdown

Show:

- RC ladder diagram,
- resistance table,
- capacitance table,
- estimated time constants,
- dominant node and dominant segment.

### L3 Sensitivity

Run small local sweeps:

- sink `R_sa`,
- interface resistance,
- heatsink capacitance,
- source capacitance,
- duty-cycle on time,
- duty-cycle off time.

Outputs:

- time-to-limit vs parameter,
- peak temperature vs parameter,
- cooldown time vs parameter.

### L4 Math And Derivations

Expose:

- RC governing equation,
- one-lump analytical solution,
- matrix form for multi-node solve,
- substituted `R*C` time constants,
- energy balance checks,
- time-to-limit interpolation.

Every primary output should have a `subst_*` string or a derivation object.

### L5 Background

Include:

- thermal resistance vs thermal capacitance,
- why steady-state temperature can be safe but transient peak still matters,
- why large mass delays temperature rise but may not improve steady-state,
- how to estimate capacitance responsibly,
- how to map hardware into nodes,
- limitations of lumped models,
- when to use detailed FEA, CFD, or measurement.

---

## 9. Backend Architecture

### New Module

Create:

```text
pycalcs/thermal_transient.py
```

Core public functions:

```python
def simulate_transient_thermal_model(model: dict[str, object]) -> dict[str, object]:
    """Simulate a transient thermal RC model."""

def validate_transient_thermal_model(model: dict[str, object]) -> dict[str, object]:
    """Validate nodes, segments, capacitances, heat profiles, and limits."""

def generate_power_profile(profile: dict[str, object], time_s: list[float]) -> dict[str, object]:
    """Return node heat inputs over the requested time grid."""

def estimate_thermal_capacitance(
    material_id: str,
    volume_m3: float,
    density_kg_per_m3: float | None = None,
    heat_capacity_j_per_kgk: float | None = None,
) -> dict[str, object]:
    """Estimate C = rho V cp and return substituted equations."""

def generate_transient_sensitivity(
    model: dict[str, object],
    parameter: dict[str, object],
) -> dict[str, object]:
    """Sweep one parameter and return peak/time-to-limit series."""
```

Optional bridge function:

```python
def build_plate_fin_transient_model(heatsink_inputs: dict[str, object]) -> dict[str, object]:
    """Use the steady-state plate-fin solver to create a transient RC model."""
```

### Data Model

Use a dictionary structure similar to `thermal_networks.py`:

```json
{
  "version": "1.0",
  "analysis_mode": "simulate",
  "time": {
    "duration_s": 600.0,
    "time_step_s": null,
    "auto_step": true,
    "initial_temperature_c": 25.0
  },
  "profile": {
    "type": "duty_cycle",
    "on_power_w": 80.0,
    "on_time_s": 30.0,
    "off_power_w": 0.0,
    "off_time_s": 120.0,
    "cycles": 10,
    "auto_cyclic_steady_state": true
  },
  "network": {
    "nodes": [
      {
        "id": "source",
        "label": "Source",
        "kind": "dynamic",
        "capacitance_j_per_k": 12.0,
        "max_temperature_c": 110.0,
        "initial_temperature_c": null
      },
      {
        "id": "sink",
        "label": "Heatsink",
        "kind": "dynamic",
        "capacitance_j_per_k": 310.0,
        "max_temperature_c": null,
        "initial_temperature_c": null
      },
      {
        "id": "ambient",
        "label": "Ambient",
        "kind": "boundary",
        "fixed_temperature_c": 25.0
      }
    ],
    "segments": [
      {
        "id": "r_source_sink",
        "label": "Source to sink",
        "from_node_id": "source",
        "to_node_id": "sink",
        "resistance_k_per_w": 0.4
      },
      {
        "id": "r_sink_ambient",
        "label": "Sink to ambient",
        "from_node_id": "sink",
        "to_node_id": "ambient",
        "resistance_k_per_w": 1.8
      }
    ],
    "heat_inputs": [
      {
        "node_id": "source",
        "profile_role": "primary"
      }
    ]
  }
}
```

### Return Structure

Return:

```python
{
    "summary": {
        "status": "acceptable",
        "time_to_limit_s": None,
        "peak_temperature_c": 92.4,
        "peak_node_id": "source",
        "final_temperature_c": 84.1,
        "cyclic_steady_state_reached": True,
        "cooldown_time_to_target_s": 180.0,
        "dominant_time_constant_s": 420.0
    },
    "series": {
        "time_s": [...],
        "power_w": [...],
        "node_temperatures_c": {
            "source": [...],
            "sink": [...]
        }
    },
    "nodes": [...],
    "segments": [...],
    "time_constants": [...],
    "cycle_summary": [...],
    "diagnosis": [...],
    "recommendations": [...],
    "applicability": {...},
    "derivations": [...],
    "subst_time_constant": "...",
    "subst_thermal_capacitance": "..."
}
```

---

## 10. Frontend Architecture

### Tool Path

Create:

```text
tools/transient-heatsink/
```

Files:

- `tools/transient-heatsink/index.html`
- `tools/transient-heatsink/README.md`
- optional `tools/transient-heatsink/test-cases/*.json`

Use `tools/example_tool_advanced/index.html` as the foundation.

### Layout

Use a two-column advanced-tool layout:

- left side: workflow, inputs, power profile, RC template
- right side: summary, plots, network, derivations

Tabs:

1. **Results**
   - summary cards, temperature plot, power plot
2. **RC Model**
   - ladder diagram, node/segment table, capacitance estimates
3. **Sensitivity**
   - parameter sweep and impact ranking
4. **Math**
   - derivations and substituted equations
5. **Background**
   - guidance, assumptions, references, examples

### Progressive Simplicity

Default state:

- template: `Package On Heatsink`
- profile: `Step Load`
- heat load: `50 W`
- ambient: `25 C`
- source limit: `110 C`
- known `R_sa`: `1.5 K/W`
- source-to-sink resistance: `0.5 K/W`
- sink capacitance: estimated from a default aluminum heatsink
- source capacitance: small default with warning

The user should get a temperature-vs-time plot immediately after Pyodide loads.

### Progressive Disclosure

The UI should hide:

- detailed capacitance estimates,
- per-node initial temperatures,
- solver settings,
- advanced resistance modes,
- fan/geometry-derived sink performance,
- sensitivity settings,

until expert mode is enabled or the relevant tab is opened.

---

## 11. Validation And Tests

### Unit Tests

Create:

```text
tests/test_thermal_transient.py
```

Required tests:

1. **One-lump step response**
   - Compare numerical response to analytical solution.

2. **One-lump cooldown response**
   - Start above ambient with zero heat and compare to exponential decay.

3. **Energy balance sanity**
   - Integrated heat input minus rejected heat should match stored energy
     change within tolerance.

4. **Two-node limiting behavior**
   - Very low internal resistance should approach one combined capacitance.
   - Very high internal resistance should delay sink response.

5. **Time-to-limit interpolation**
   - Limit crossing between time steps should be interpolated.

6. **Duty-cycle cyclic steady state**
   - Repeated pulse train should converge to stable min/max temperatures.

7. **Input validation**
   - Negative capacitance, zero resistance, missing ambient, and disconnected
     nodes should raise or return validation errors.

8. **Plate-fin bridge**
   - If implemented in MVP, confirm sink capacitance and `R_sa` are derived
     consistently from `pycalcs.heatsinks`.

### Browser Smoke Tests

Add later, after the first implementation:

- Pyodide loads successfully.
- Default case calculates.
- Plotly plots are non-empty.
- Expert mode does not overlap or break mobile layout.
- Export buttons create JSON/CSV payloads.

---

## 12. References

Initial reference set:

- Incropera, DeWitt, Bergman, and Lavine, *Fundamentals of Heat and Mass
  Transfer*.
- Cengel and Ghajar, *Heat and Mass Transfer: Fundamentals and Applications*.
- JEDEC JESD51 family, for thermal resistance and transient thermal impedance
  terminology.
- Bar-Cohen and Kraus, *Advances in Thermal Modeling of Electronic Components
  and Systems*.
- Existing project references in `tools/simple_thermal/README.md` for
  plate-fin steady-state correlations.

Use references for terminology and validation ranges. Keep the implementation
explicitly scoped to lumped RC modeling, not JEDEC package characterization.

---

## 13. Implementation Phases

### Phase 1: Backend Solver

- Create `pycalcs/thermal_transient.py`.
- Implement model validation.
- Implement one-lump and multi-node series RC simulation.
- Implement step, pulse, and duty-cycle profile generation.
- Implement time-to-limit and cooldown-time calculations.
- Add unit tests against analytical one-lump solutions.

### Phase 2: Basic Tool UI

- Create `tools/transient-heatsink/` from the advanced template.
- Add the default Package On Heatsink workflow.
- Add input forms for step, pulse, and duty cycle.
- Add summary cards and Plotly temperature/power plots.
- Add loading overlay, stale result indicator, and error states.
- Register the tool in `catalog.json`.

### Phase 3: Plate-Fin Integration

- Add an option to derive `R_sa` and sink capacitance from plate-fin geometry.
- Reuse material presets from `pycalcs.heatsinks` where appropriate.
- Surface warnings when steady-state plate-fin assumptions are out of scope.
- Add a handoff from `simple_thermal` to the transient tool when possible.

### Phase 4: Diagnosis And Sensitivity

- Add time constant ranking.
- Add sensitivity sweeps for `R_sa`, interface resistance, and sink
  capacitance.
- Add recommendations that distinguish resistance improvements from mass
  improvements.
- Add cycle-by-cycle summary for duty cycles.

### Phase 5: Documentation And Validation

- Build the Background tab.
- Add worked examples:
  - continuous step load,
  - overload pulse,
  - repeated duty cycle,
  - cooldown to service temperature.
- Add JSON test cases in the tool folder.
- Add exportable calculation report.
- Add browser smoke tests.

---

## 14. Catalog Entry Draft

```json
{
  "title": "Transient Heatsink Simulator",
  "path": "./tools/transient-heatsink/",
  "description": "Simulate heatsink warmup, cooldown, pulse loads, and duty cycles with a lumped thermal RC model.",
  "category": [
    "Thermal Sciences"
  ],
  "tags": [
    "thermal",
    "heatsink",
    "transient",
    "rc-network",
    "duty-cycle",
    "cooldown",
    "electronics-cooling"
  ]
}
```

---

## 15. Open Design Decisions

1. Should v1 support only series RC chains, or also one simple parallel path?
   - Recommendation: series only in v1. Add parallel once the UI proves clear.

2. Should the first UI derive `R_sa` from plate-fin geometry by default?
   - Recommendation: no. Default to known `R_sa` for fast use, then offer
     geometry-derived `R_sa` as a mode.

3. Should fan ramping be included?
   - Recommendation: defer. Treat fan-ramped `R_sa(t)` as a later advanced
     feature.

4. Should capacitance defaults be aggressive or conservative?
   - Recommendation: make source/package capacitance visibly approximate and
     encourage overrides. Sink capacitance from geometry is more defensible.

5. Should this be named "Transient Thermal RC Tool" instead of "Transient
   Heatsink Simulator"?
   - Recommendation: use "Transient Heatsink Simulator" for discoverability,
     while allowing known-RC-chain workflows inside it.

---

## 16. Bottom Line

Build this as a focused transient heatsink and thermal-stack simulator, not a
universal thermal graph editor.

The first useful version should let a user answer:

- "How long can I run?"
- "Will this pulse survive?"
- "Does this duty cycle walk up?"
- "How much cooldown do I need?"
- "Should I improve resistance or add thermal mass?"

That is a genuinely distinct product from the current steady-state thermal
tools and should live as a separate tool in the thermal family.
