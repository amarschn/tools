# Transient Heatsink Simulator

Lumped thermal RC simulator for heatsink assemblies under step, pulse, and
duty-cycle loads. Predicts time-to-limit, peak temperature, cyclic steady
state, and cooldown time.

## When to use this tool

- "How long can I run before I hit the temperature limit?"
- "What peak temperature will a pulse or repeated duty cycle create?"
- "Does this design reach a safe cyclic steady state?"
- "How much cooldown time do I need?"
- "Should I improve resistance, or add thermal mass?"

For steady-state plate-fin geometry, fin efficiency, and pressure drop, use
the [Heatsink Designer](../simple_thermal/) instead. For a static
resistance-network temperature budget, use the
[Thermal Path Budget](../thermal-path-budget/) tool.

## Model

Three-node series RC network: **Source → Sink → Ambient**.

- `R_jc` — source-to-case (or source-to-sink) thermal resistance, K/W
- `R_sa` — sink-to-ambient thermal resistance, K/W
- `C_source` — thermal capacitance of the source/package, J/K
- `C_sink` — thermal capacitance of the heatsink, J/K

The solver uses implicit Euler on the linear network ODEs:

```
C_i dT_i/dt = Q_i(t) + sum_j (T_j - T_i) / R_ij
```

Implicit Euler is unconditionally stable for this linear problem, so the
time step is chosen for resolution rather than stability. The default time
step samples the shortest profile event at least 25 times.

## Power profiles

| Profile | Inputs | Reports |
| --- | --- | --- |
| Step | `power_w`, `duration_s` | Time-to-limit, peak T, final T |
| Pulse | `pulse_power_w`, `pulse_duration_s`, `cooldown_duration_s`, `cooldown_target_c` | Peak T, time-to-limit, cooldown time |
| Duty cycle | `on_power_w`, `on_time_s`, `off_power_w`, `off_time_s`, total simulation time | Per-cycle peak/min, cyclic steady state |

Cyclic steady state is detected when consecutive cycles' peak and min
temperatures differ by less than 0.05 °C.

## Backend

Implemented in `pycalcs/thermal_transient.py`:

- `simulate_transient_thermal_model(model)` — main entry
- `validate_transient_thermal_model(model)` — input validation
- `generate_power_profile(profile, time_s)` — series Q(t) for step / pulse / duty
- `estimate_thermal_capacitance(volume_m3, material_id, …)` — `C = ρ V c_p`
  with material presets (aluminum 6063/6061, copper, steel, FR-4, silicon)
- `compute_plate_fin_sink_properties(...)` — derives `R_sa` and `C_sink` from
  plate-fin geometry by calling the steady-state solver in `pycalcs.heatsinks`
- `build_plate_fin_transient_model(...)` — convenience wrapper that returns a
  ready-to-simulate model dict from plate-fin geometry plus profile/time
- `generate_transient_sensitivity(model, parameter, fractions=None)` — sweep
  one of `r_sa`, `r_jc`, `c_source`, `c_sink`, `on_time`, `off_time` and
  return peak T, time-to-limit, and steady-state T at each fraction
- `compute_design_lever_recommendation(model)` — compares "halve R_sa" to
  "double C_sink" and returns a directional recommendation

## Sink properties: direct or from plate-fin geometry

The UI offers two modes for sink-side inputs:

- **Direct**: type `R_sa` and `C_sink` outright, or compute `C_sink` from a
  material preset and a sink volume.
- **From plate-fin geometry**: enter base/fin dimensions, fin count, alloy,
  and airflow; both `R_sa` and `C_sink` are computed and shown live above
  the calculate button. Out-of-envelope warnings (very low fin efficiency,
  very high channel Reynolds) surface alongside the readout.

The [Heatsink Designer](../simple_thermal/) tool has a **Send to Transient**
button that opens this tool with the same plate-fin geometry pre-loaded.

## Tests

`tests/test_thermal_transient.py` covers:

1. Material presets and capacitance estimate (with and without overrides)
2. Step / pulse / duty power profile shapes
3. One-lump step response vs. analytical exponential
4. One-lump cooldown vs. analytical decay
5. Energy balance (heat in − heat rejected = stored ΔE)
6. Two-node limiting cases (low / high internal resistance)
7. Time-to-limit interpolation between time steps
8. Duty cycle convergence to cyclic steady state
9. Duty cycle overload triggers time-to-limit and unacceptable status
10. Validation errors (disconnected nodes, negative capacitance, zero resistance)

`tests/test_transient_heatsink_ui.py` also verifies the HTML/JavaScript ID
wiring, Pyodide module bootstrap, sample links, and every declared expectation
in the tool-local JSON examples.

## Scope and deferred items

This implementation covers Phases 1–5 of
[`plans/2026-04-25_transient_heatsink_tool_plan.md`](../../plans/2026-04-25_transient_heatsink_tool_plan.md):

- Package-on-heatsink series RC modeling with step, pulse, and duty-cycle loads.
- Implicit Euler integration, time-to-limit, cooldown, and cyclic walk-up.
- Direct resistance/capacitance entry or plate-fin geometry-derived sink values.
- Sensitivity sweeps and resistance-versus-capacitance design-lever guidance.
- Background theory, five executable examples, JSON model exchange, and
  Markdown calculation reports.

Deferred beyond this release:

- Multiple templates (Single Lump, Plate-Fin From Geometry, Known Thermal Path).
- Arbitrary RC graph editor.
- Multiple heat sources or ambient boundaries.
- Temperature-dependent properties, fan-control transients, and JEDEC
  transient-impedance curve fitting.
- Full browser automation; current UI smoke tests are static and backend-driven.

## References

- Incropera, DeWitt, Bergman, Lavine — *Fundamentals of Heat and Mass Transfer*
- Çengel, Ghajar — *Heat and Mass Transfer: Fundamentals and Applications*
- JEDEC JESD51 family — for thermal resistance and transient terminology
- Bar-Cohen, Kraus — *Advances in Thermal Modeling of Electronic Components*
