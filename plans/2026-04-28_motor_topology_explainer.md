# Motor Topology Explainer/Explorer

Date: 2026-04-28
Status: Proposed plan for critique before implementation
Branch: `task/motor-explainer-explorer`

## 1. Goal

A pure **education / exploration** tool that helps a curious user build genuine intuition for electric motors:
- What the major motor topologies are and why they exist.
- The tradeoffs that distinguish them (torque density, power density, efficiency, speed range, cost, control complexity, smoothness, magnet content, ...).
- How the same motor behaves differently under different control strategies (six-step, sinusoidal, FOC with and without field weakening, scalar V/f, DTC).
- How to read the standard motor performance plots an engineer encounters in datasheets and papers, and how those plots change as a function of control choice.

This is the "what is it and how does it work" companion to the existing `motor-thermal` and `motor-hotspot` calculators (which answer "will it melt?").

## 2. Non-goals

- **Not a sizing or selection tool.** No "pick the right motor for my application" wizard.
- **Not a controller tuning tool.** Control content is conceptual and visual, not a PID tuner.
- **Not a thermal model.** Link out to `motor-thermal` and `motor-hotspot`.
- **Not a finite-element substitute.** All maps and waveforms are pedagogical synthetic models that capture the *shape* of the real thing, not bit-exact predictions of any specific machine. The tool will say so plainly.
- **Not exhaustive for niche topologies.** Linear, transverse-flux, hysteresis, etc. get a paragraph in Background, not a full page.

## 3. Target users

Three concurrent personas (per AGENTS.md "Two Core Principles"):
1. **The curious engineer / student** — has heard "PMSM," "FOC," "field weakening" and wants the mental model.
2. **The cross-discipline practitioner** — mechanical / firmware / systems engineer who needs to talk competently with a motor specialist.
3. **The verifying expert** — wants to see the equations, the assumptions behind every plot, and the references.

Progressive disclosure (per AGENTS.md table) maps to: result → plot → equation → substituted equation → derivation → references.

## 4. Topology coverage (scope)

Initial release ("v1"):

| Topology | Why included |
|---|---|
| DC brushed (PM rotor) | Pedagogical baseline; everything else is "fixing" something here |
| BLDC / PMSM — surface-mount (SPM) | Most common modern small-to-mid motor |
| PMSM — interior magnet (IPM) | Distinct field-weakening behavior, reluctance + magnet torque |
| Induction (squirrel cage) | The industrial workhorse; introduces slip |
| Synchronous reluctance (SynRM) | Magnet-free high-η alternative |
| Switched reluctance (SRM) | Distinct torque ripple and waveform story |
| Stepper (hybrid) | Open-loop positioning paradigm; microstepping |
| Universal (AC commutator) | Why your handheld vacuum is loud |

Cross-cutting form-factor cards (referenced from Background, not full pages): axial vs radial flux, slotted vs slotless, inrunner vs outrunner.

Held for "v2 / future" (named in Background so users know they exist): linear, transverse-flux, hysteresis, hollow-shaft, dual-rotor, integrated-magnetic-gear.

## 5. Tradeoff dimensions

Each topology gets typical-range entries for:
- Torque density (Nm/kg, Nm/L)
- Power density (W/kg, W/L)
- Peak efficiency (%) and efficiency-map shape descriptor
- Speed range / max safe speed
- Field-weakening capability (none / limited / strong)
- Cost band ($/kW, qualitative)
- Control complexity (1–5 ordinal)
- Cogging / smoothness (qualitative)
- Audible noise character
- Self-starting (yes/no/with-help)
- Position-sensor requirement
- Power factor (where applicable)
- Inertia (rotor J, qualitative band)
- Magnet content (none / ferrite / NdFeB / SmCo)
- Continuous-vs-peak ratio (typical)

These feed the radar / parallel-coordinates / bar comparisons.

## 6. Control concepts

Each control method gets: applicable-topologies list, what it does in one sentence, plotted phase-current and phase-voltage waveforms, plotted resulting torque ripple, and a "what it buys you" summary.

| Method | Applies to |
|---|---|
| Six-step / trapezoidal | BLDC, SRM (variant) |
| Sinusoidal (open-loop / scalar) | PMSM, induction (V/f) |
| FOC (Field-Oriented Control) | PMSM-SPM, PMSM-IPM, induction |
| FOC + MTPA (Maximum Torque per Amp) | PMSM-IPM, SynRM |
| FOC + field weakening | PMSM (SPM and IPM), induction |
| Direct Torque Control (DTC) | Induction, PMSM |
| Scalar V/f | Induction |
| Vector control (rotor-flux) | Induction |
| Sensored vs sensorless (Hall, encoder, back-EMF zero-cross, HFI) | Cross-cutting |
| Microstepping | Stepper |

## 7. Performance plot catalog (the chart inventory)

Every plot below has: axes labelled with units, legend, scale type declared, brief explanation of what to look for, and links from the relevant topology and control pages so users discover them in context.

### 7.1 Steady-state envelopes

1. **Torque–speed envelope** (T vs ω): continuous and peak boundaries; constant-torque region, constant-power region, field-weakening region marked. Sliders: `V_dc`, `I_max`, `k_e`, `R_phase`, `L_d`, `L_q`. Annotations for base speed and characteristic speed.
2. **Power–speed curve** (P vs ω): derived from #1; shows where peak power lives and how long the constant-power region extends.
3. **Efficiency map** (heatmap of η over T–ω plane, with contour lines): synthetic but topology-characteristic. Slider: load-line overlay.
4. **Loss breakdown vs speed at rated load** (stacked area): copper, iron, mechanical/windage, switching. Shows why peak-η point is *not* at peak-power point.
5. **Power factor map** (induction, PMSM under FOC): cos φ contours over T–ω.

### 7.2 Topology-specific characteristic curves

6. **Slip–torque curve** (induction): pull-out torque, locked-rotor, motoring/braking/regenerating regions.
7. **Torque vs current-angle β** (PMSM-IPM, SynRM): shows magnet vs reluctance torque components and the MTPA optimum angle.
8. **Inductance vs rotor angle** (SRM): the source of reluctance torque and the reason for the characteristic ripple.
9. **Pull-in / pull-out curves** (stepper): max start frequency vs load torque; max running frequency.
10. **Back-EMF waveform shape** (BLDC trap vs PMSM sinusoidal vs distorted): per-phase and line-to-line.

### 7.3 Time-domain control response

11. **Phase-current waveforms** under each control mode: six-step (commutated trapezoid), sinusoidal, FOC clean sine, FOC with PWM ripple visible.
12. **Phase-voltage / PWM waveforms**: six-step, SPWM, SVPWM. Shows DC-bus utilization differences.
13. **Resulting torque vs angle / vs time**: the punchline — six-step BLDC has commutation ripple, sine FOC is smooth, SRM has structural ripple. Side-by-side at matched mean torque.
14. **id–iq trajectory plot** (FOC): current-limit circle, voltage-limit ellipse (shrinks with speed), MTPA curve, MTPV curve, operating point. Slider for speed shows the ellipse shrink → field weakening forces id < 0.
15. **Speed step response**: ω vs t for a commanded step, under (a) open-loop V/f, (b) sensored PI on speed, (c) FOC cascaded loops. Overlaid for comparison; shows bandwidth, overshoot, steady-state error.
16. **Disturbance rejection**: rated speed maintained, step load torque applied at t = t₀; ω-dip and recovery vs control method.
17. **Reference-tracking under sinusoidal command**: phase lag and amplitude attenuation vs frequency for each controller — leads naturally into #18.
18. **Closed-loop Bode plot** (magnitude + phase) of the speed loop for each control method: shows control bandwidth differences without making the user solve for them.

### 7.4 Comparison views (cross-topology)

19. **Radar chart**: normalized scores across the tradeoff dimensions (§5) for 1–N selected topologies.
20. **Parallel-coordinates plot**: the same dimensions, different visual; lets users brush a range and see which topologies survive.
21. **Bar/whisker plot**: typical range per dimension per topology.
22. **Scatter** (e.g., torque density vs cost, efficiency vs control complexity): user picks the two axes.

### 7.5 Background / pedagogical figures

23. **Cross-section diagrams** per topology (hand-drawn SVG, labelled).
24. **Rotating-field animation** (3-phase windings → rotating B-vector).
25. **TRV / sizing-equation visualization** (D²L bar comparison; torque scales with rotor volume × magnetic loading × electric loading).
26. **Field-weakening explainer**: voltage-limit ellipse animation as ω rises.

Total: ~26 distinct chart/figure types. Many are reused across topology and control pages.

## 8. Tool structure (UI layout)

Left-rail explorer, mirrors `tools/materials-explorer`:

```
┌─ Navbar ────────────────────────────────────────────────────┐
├─ Left rail ─────┬─ Main panel (tabs) ───────────────────────┤
│ TOPOLOGIES      │  [Overview] [Performance] [Control]       │
│ ◉ PMSM (SPM)    │  [Tradeoffs] [Equations] [Background]     │
│ ○ PMSM (IPM)    │                                           │
│ ○ Induction     │   ── tab content ──                       │
│ ○ SynRM         │                                           │
│ ○ SRM           │                                           │
│ ○ Stepper       │                                           │
│ ○ DC brushed    │                                           │
│ ○ Universal     │                                           │
│ ─────────────   │                                           │
│ ☐ Compare mode  │                                           │
│ (multi-select   │                                           │
│  appears here)  │                                           │
└─────────────────┴───────────────────────────────────────────┘
```

### 8.1 Per-tab specification

**Overview** — cross-section SVG (#23), one-paragraph description, distinguishing facts (4 bullets), where you find them in the wild, capsule pros/cons, "this topology in one sentence."

**Performance** — the charts from §7.1 and §7.2 relevant to this topology. For PMSM-IPM: envelope (#1), power (#2), efficiency map (#3), loss breakdown (#4), torque-vs-current-angle (#7), back-EMF (#10). All driven by the same parameter sliders so changing `V_dc` or `I_max` updates everything together. *(This addresses the user's concern about plotted motor performance.)*

**Control** — applicable methods (§6) as cards. For each: phase-current waveform (#11), phase-voltage / PWM (#12), resulting torque-vs-angle (#13), id–iq trajectory if vector-controlled (#14), step response (#15), disturbance rejection (#16), Bode (#18). A "Compare control methods" button overlays #13 and #15 across all applicable methods on the same axes — the punchline of the tool. *(This addresses the user's concern about response to various control approaches.)*

**Tradeoffs** — radar (#19), parallel-coords (#20), bar/whisker (#21), scatter (#22). In compare mode, all overlay multiple topologies.

**Equations** — the key relations for this topology with variable legends (per AGENTS.md): back-EMF constant, torque constant, sizing equation, MTPA condition for IPM, slip equation for IM, etc. Each expandable to derivation. Substituted-value strings (`subst_*` per AGENTS.md Pattern 2) populated from the current slider state.

**Background** — universal concepts, accessible regardless of topology selection: rotating fields (#24), torque production, magnetic vs electric loading and the sizing equation (#25), field weakening (#26), losses, thermal limits (link out to motor-thermal), sensor types, references.

### 8.2 Compare mode

Toggle in left rail. Select up to 4 topologies. Overview tab shows side-by-side cross-sections + capsule cards. Performance tab overlays #1, #2, #3 on shared axes. Tradeoffs tab overlays radar / parallel-coords / scatter. Control tab is disabled in compare mode (too noisy).

## 9. Data layer: `pycalcs/motors.py`

- `MOTOR_TOPOLOGIES`: dict; each entry has typical-range numbers for §5 dimensions, prose description, pros/cons lists, applicable control methods, standard application list, references.
- `CONTROL_METHODS`: dict; method → description, applicable topologies, complexity score, sensor requirements.
- `torque_speed_envelope(V_dc, I_max, k_e, R, L_d, L_q, topology, n_points)` → arrays for plot #1, with marked region boundaries.
- `power_speed_curve(envelope)` → plot #2 from #1.
- `efficiency_map_synthetic(topology, T_grid, w_grid, params)` → 2-D grid for plot #3. Pedagogical model: peak-η location and contour shape are topology-characteristic; values are not bit-exact.
- `loss_breakdown(speed, load, params)` → stacked-area data for plot #4.
- `slip_torque_curve(...)` → plot #6.
- `torque_vs_current_angle(L_d, L_q, psi_pm, I_max)` → plot #7; returns magnet, reluctance, total components and MTPA optimum.
- `srm_inductance_profile(...)` → plot #8.
- `stepper_pull_curves(...)` → plot #9.
- `back_emf_waveform(topology, ...)` → plot #10.
- `phase_current_waveform(control_method, params)` → plot #11.
- `pwm_voltage_waveform(modulation, params)` → plot #12.
- `torque_ripple_waveform(topology, control_method, ...)` → plot #13.
- `id_iq_trajectory(speed, params)` → plot #14, with current-limit circle, voltage-limit ellipse, MTPA curve, operating point.
- `speed_step_response(controller, params, t)` → plot #15. Toy second-order plant + chosen controller; pedagogical.
- `disturbance_response(controller, params, t)` → plot #16.
- `bode_speed_loop(controller, params, freqs)` → plot #18 magnitude + phase.
- `radar_data(topologies, dimensions)` → plot #19; normalized 0–1 scores.
- `parallel_coords_data(topologies, dimensions)` → plot #20.
- Diagram-only routines for #23–#26 are static SVG assets, not Python-generated.

All functions: PEP 8, type hints, docstring with `---Parameters---` / `---Returns---` / `---LaTeX---` per AGENTS.md. Pyodide-friendly (pure Python preferred; numpy permissible since Pyodide ships it).

## 10. Visualization library

Plotly.js (consistent with `materials-explorer`, `fan-curve-explorer`). Cross-section diagrams: hand-authored SVG embedded in HTML.

Per AGENTS.md Visualization Standards: every chart gets axes + units + legend + scale-type declaration + a one-paragraph "what to look for" caption.

## 11. Tests: `tests/test_motors.py`

- Topology database integrity (every entry has every required key; ranges are min ≤ typ ≤ max).
- Control-method database integrity.
- `torque_speed_envelope`: zero current → zero torque; envelope monotonically non-increasing past base speed; field-weakening past characteristic speed never exceeds voltage limit.
- `efficiency_map_synthetic`: bounded in [0, 1]; monotonic decay toward edges of operating region.
- `id_iq_trajectory`: operating point lies on or inside current-limit circle and voltage-limit ellipse for every speed.
- `speed_step_response`: bounded; reaches commanded speed within finite time for stable controllers.
- `bode_speed_loop`: magnitude rolls off at high frequency.
- Docstring parser smoke test for every public function.

## 12. Build order

Each step is its own commit on `task/motor-explainer-explorer`. We pause between steps for review.

1. **Skeleton** — `pycalcs/motors.py` with `MOTOR_TOPOLOGIES` for 3 topologies (PMSM-SPM, induction, DC brushed) + tests for database integrity. `tools/motor-topology-explorer/index.html` from `example_tool_advanced` template, left rail wired to those 3, Overview tab only.
2. **Performance tab core** — `torque_speed_envelope`, `power_speed_curve`, `efficiency_map_synthetic`, `loss_breakdown` + tests + tab UI with sliders.
3. **Topology-specific characteristics** — `slip_torque_curve`, `torque_vs_current_angle`, `srm_inductance_profile`, `back_emf_waveform`, `stepper_pull_curves` + tests. Wire into Performance tab per-topology.
4. **Control tab core** — `CONTROL_METHODS`, `phase_current_waveform`, `pwm_voltage_waveform`, `torque_ripple_waveform` + tests + tab UI with method picker and "compare methods" overlay.
5. **Vector-control visuals** — `id_iq_trajectory` + tests; FOC card extended with the trajectory plot.
6. **Closed-loop response** — `speed_step_response`, `disturbance_response`, `bode_speed_loop` + tests; controller comparison overlays in Control tab.
7. **Tradeoffs tab** — `radar_data`, `parallel_coords_data` + bar/whisker + scatter UI; compare-mode overlays.
8. **Remaining topologies** — fill out IPM, SynRM, SRM, stepper, universal in `MOTOR_TOPOLOGIES`; add their cross-section SVGs.
9. **Equations tab** — per-topology equations with substituted-value strings driven by sliders.
10. **Background tab** — universal concepts content, rotating-field animation (#24), TRV diagram (#25), field-weakening explainer (#26), references.
11. **Polish** — catalog entry, README, screenshots, settings panel (theme/density/precision), tool roadmap.
12. **Verification pass** — every chart against the AGENTS.md Visualization checklist; every public function against docstring smoke test; manual click-through in browser; codex review of the whole branch diff.

## 13. Codex involvement

- After each major build step (especially #2, #4, #6 — the chart-heavy steps), run `codex exec` with the relevant section of code + a "critique for technical accuracy and pedagogy" prompt. Surface findings before moving on.
- After step #12, run `codex review` against the full branch diff as a final check.
- During this planning phase: codex review of *this document* immediately after writing it.

## 14. Open questions for the user

1. Topology list (§4): keep at 8, trim to a focused 4–5, or add (linear, axial-flux as full pages instead of cross-cuts)?
2. Compare mode: cap at 4 topologies, or unlimited?
3. Controller models in §7.3: a toy second-order plant + tunable PI is enough for pedagogy, but should we offer slider-tunable Kp/Ki so users can "feel" the tradeoff, or fix them per controller and only let users switch controller type?
4. id–iq trajectory (#14): make it draggable (user moves operating point, plot reads out current/voltage utilization), or static-with-slider?
5. Audio: should the audible-noise discussion include a synthesized audio clip per topology+control combo, or stay textual?
