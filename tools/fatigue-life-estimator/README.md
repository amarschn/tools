# Fatigue Life Estimator

Estimate fatigue life for a cyclic stress history using mean stress correction
and a Basquin S-N model. The tool highlights both fatigue life margin and
static yield margin for early-stage sizing and comparison.

## Tool Requirements

- **Inputs (core):** max/min stress, ultimate strength, yield strength,
  mean stress correction method.
- **Inputs (advanced):** endurance limit ratio with modifiers, Basquin
  coefficients, target life, and required safety factors.
- **Outputs:** equivalent alternating stress, estimated cycles to failure,
  life safety factor, fatigue safety factor, yield safety factor, status,
  and recommendations.
- **Visualizations:** S-N curve with operating point and mean stress diagram.
- **Derivations:** equations with substituted values for key results.

## Assumptions and Notes

- Constant amplitude loading (no Miner's rule or load spectra).
- Single-axis stress; no multiaxial or notch sensitivity effects.
- Default coefficients are approximate; replace with test data for design work.

## Theory and Background

Fatigue design grew out of late 1800s railway axle failures studied by
Wohler, which established that repeated stress can cause failure well below
static strength. Those tests led to the S-N curve: a relationship between
stress amplitude and cycles to failure. Basquin later proposed a power-law
fit for high-cycle fatigue on a log-log scale.

Mean stress corrections (Goodman, Gerber, Soderberg) adjust alternating
stress to account for tensile mean stress. Goodman is linear, Gerber is
parabolic and less conservative at higher mean stress, and Soderberg uses
yield strength as a conservative cap. This tool implements all three and a
no-correction option for comparison.

Endurance limit modifiers (surface, size, reliability) approximate how
real-world conditions reduce the rotating-beam endurance limit. For
materials without a true endurance limit (many nonferrous alloys), set the
endurance limit ratio to 0 to remove the infinite-life floor.

## Model Assumptions

- Constant-amplitude, uniaxial loading.
- Linear elastic fatigue behavior (Basquin regime).
- No overload, sequence, or cumulative damage effects.
- Stresses represent local hot-spot stress at the critical location.

## References

- Shigley's Mechanical Engineering Design, fatigue chapter.
- Juvinall & Marshek, Fundamentals of Machine Component Design.
- ASTM E466, constant amplitude axial fatigue testing.
