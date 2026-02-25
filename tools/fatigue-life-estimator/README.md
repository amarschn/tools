# Fatigue Life Estimator

Estimate fatigue life for a cyclic stress history using mean stress correction
and a Basquin S-N model. The tool now supports both metal and polymer/plastic
workflows, plus stress-uncertainty bounds when stress is not known exactly.

## Tool Requirements

- **Inputs (core):** material family, material preset (or custom), max/min
  stress, uncertainty band, and mean stress correction method.
- **Inputs (advanced):** endurance modifiers, Basquin coefficients, target
  life and required safety factors, and polymer derating controls
  (temperature, frequency, moisture/chemical/UV factors).
- **Outputs:** nominal life (cycles and hours), life/fatigue/static safety
  factors, uncertainty bounds (conservative and optimistic life), status, and
  recommendations.
- **Visualizations:** S-N curve with operating point and mean stress diagram.
- **Derivations:** equations with substituted values for key results.

## Assumptions and Notes

- Constant-amplitude loading (no Miner's rule or variable-amplitude spectrum).
- Single-axis stress; no multiaxial, notch-root strain, or crack-growth model.
- Material presets are starting points only. Replace with test data for design.
- Polymer mode does not assume true infinite life by default.

## Unknown Stress Workflow

If the stress cycle is uncertain, use the `Stress Uncertainty (+/- %)` input.
The tool evaluates:

- **Nominal case:** stress values as entered.
- **Conservative case:** stress magnitudes increased by the uncertainty band.
- **Optimistic case:** stress magnitudes reduced by the uncertainty band.

Status assessment uses the conservative case so results remain decision-safe.

## Theory and Background

Fatigue design grew out of late 1800s railway axle failures studied by
Wohler, which established that repeated stress can cause failure well below
static strength. Those tests led to the S-N curve: a relationship between
stress amplitude and cycles to failure. Basquin later proposed a power-law
fit for high-cycle fatigue on a log-log scale.

Mean stress corrections (Goodman, Gerber, Soderberg) adjust alternating
stress to account for tensile mean stress. Goodman is linear, Gerber is
parabolic and less conservative at higher mean stress, and Soderberg uses
yield strength as a conservative cap.

For polymers/plastics, the tool applies additional derating factors for
service temperature, cycle frequency, and environmental exposure.

## Model Assumptions

- Constant-amplitude, uniaxial loading.
- Stress-life model (Basquin) in the high-cycle regime.
- No overload, sequence, or cumulative damage effects.
- Stresses represent local hot-spot stress at the critical location.

## References

- Shigley's Mechanical Engineering Design, fatigue chapter.
- Juvinall & Marshek, Fundamentals of Machine Component Design.
- ASTM E466, constant amplitude axial fatigue testing.
- ASTM D7791, uniaxial fatigue properties of plastics.
