# Polymer Fatigue Criteria Explorer

Compare multiple polymer-fatigue life criteria for a single operating point, with explicit visibility into model spread, calibration limits, and whether the current estimate is being driven more by hysteresis dissipation or cyclic creep.

## Tool Requirements

- **Core inputs:** material preset, workflow mode, stress amplitude, load ratio, temperature, frequency, orientation, moisture state, and target life.
- **Measured-loop workflow:** direct stabilized hysteresis energy and cyclic creep strain-rate inputs.
- **Advanced custom mode:** editable coefficients for the reference stress-life relation, energy-life relation, creep-life relation, and hybrid weighting.
- **Outputs:** side-by-side predicted life for reference, energy, cyclic-creep, and hybrid criteria; governing model; life spread ratio; LCF/HCF label; mechanism label; warnings and recommendations.
- **Frequency guidance:** separate reporting of the current criterion-fit frequency window versus broader published material-frequency evidence.
- **Visualizations:** life-by-criterion comparison plot, sweep plot, and calibration-envelope plot showing the current point against the preset envelope.
- **Derivations:** substituted equations for each criterion plus the loop metrics actually used by the calculation.

## Workflows

### Preset Load Case

Use this mode when you want a fast exploratory comparison from ordinary load inputs.

The backend estimates stabilized loop energy and cyclic creep strain rate from:

- stress amplitude,
- load ratio,
- temperature,
- frequency,
- orientation, and
- conditioning state.

This is useful for trend comparison, but it is not the same as measured loop data.

### Measured Loop

Use this mode when you have stabilized observables from testing or simulation:

- hysteresis dissipated energy per cycle, and
- cyclic creep strain-rate metric.

This is the higher-confidence workflow for comparing the energy, creep, and hybrid criteria because the tool is no longer inferring those observables from a preset-side surrogate.

## Current Scope

- Uniaxial, constant-amplitude loading only.
- Comparison-first tool, not a sign-off tool.
- Literature-inspired short-fiber thermoplastic presets in v1.
- Classical stress-life retained only as a reference layer.

## Important Assumptions

- No variable-amplitude loading or Miner damage.
- No multiaxial fatigue.
- No notch-root strain or local FE hotspot modeling.
- No universal polymer law is assumed; preset validity limits matter.
- Frequency evidence is not the same thing as criterion calibration. The tool now shows both explicitly.
- Results outside preset calibration ranges are still shown, but explicitly downgraded.

## Interpretation Notes

- **Governing model:** shortest valid predicted life among the enabled criteria.
- **Life spread ratio:** largest valid predicted life divided by the smallest valid predicted life.
- **Mechanism label:** a high-level indicator of whether the current point is more dissipation-driven, creep-driven, or mixed.
- **LCF/HCF label:** cycle-band orientation aid only. It is not a substitute for mechanism interpretation.
- **Frequency note:** higher-frequency literature points are surfaced as evidence, but the tool still flags them when the current loop-surrogate fit has not been recalibrated to that frequency regime.

## References

- Bogdanov, Panin, and Kosmachev, *Journal of Composites Science* 7(12), 484, 2023.
- Mixed strain-rate / energy criterion paper, *International Journal of Fatigue* 127, 2019.
- Validation across orientation, load ratio, and environment, *International Journal of Fatigue* 135, 2020.
- Cyclic creep strain-rate validation across wide load ratios, *International Journal of Fatigue* 183, 2024.
- Bellenger et al., PA66/GF thermal-mechanical fatigue transition at 2 and 10 Hz, *International Journal of Fatigue* 28(11), 2006.
- Esmaeillou et al., PA66/GF fatigue data spanning 2-60 Hz under multiple load modes, *Polymer Composites* 33(4), 2012.
- Noda et al., short glass-fiber reinforced Nylon 66 fatigue behavior at 20 Hz, *Polymer* 42(3), 2001.
- Lee et al., PA66-GF30 conventional 3 Hz and ultrasonic 20 kHz VHCF comparison, *Composites Science and Technology* 176, 2019.
- Heat-dissipation based fatigue assessment, *Composites Part B* 42(2), 2011.
