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

## Scope and deferred items

This is the v1 (MVP) implementation per
[`plans/2026-04-25_transient_heatsink_tool_plan.md`](../../plans/2026-04-25_transient_heatsink_tool_plan.md):

- Single template (Package On Heatsink, 3-node series).
- Step, pulse, duty-cycle profiles.
- One fixed ambient, one heat-input node.
- Implicit Euler with auto time step.

Deferred (planned for later phases):

- Plate-fin geometry-derived `R_sa` and sink mass (Phase 3 in the plan).
- Sensitivity sweeps (Phase 4).
- Background tab with worked examples (Phase 5).
- Multiple templates (Single Lump, Plate-Fin From Geometry, Known Thermal Path).
- Arbitrary RC graph editor.

## References

- Incropera, DeWitt, Bergman, Lavine — *Fundamentals of Heat and Mass Transfer*
- Çengel, Ghajar — *Heat and Mass Transfer: Fundamentals and Applications*
- JEDEC JESD51 family — for thermal resistance and transient terminology
- Bar-Cohen, Kraus — *Advances in Thermal Modeling of Electronic Components*
