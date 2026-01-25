# Resonator Ring-Down Simulator

## Purpose

Simulate the ring-down response of tuning forks and beam resonators using geometry-based frequency estimates and a damped oscillator model. The tool is designed for quick education and sanity checks on frequency, damping ratio, and decay time metrics.

## Requirements

### Inputs

- Resonator type (tuning fork or single beam) and support condition.
- Cross-section geometry (rectangular or circular) and active length.
- Material selection from the database, or custom elastic modulus and density.
- Quality factor Q and initial displacement amplitude.
- Simulation duration, sample rate, and optional noise level.

### Outputs

- Fundamental and damped frequencies (Hz).
- Damping ratio, decay time constant, and t20/t60 decay times.
- Geometry summary (area, second moment, moving mass, sample count).
- Ring-down waveform and decay envelope plots.

### Assumptions & Limitations

- Euler-Bernoulli beam theory with a single dominant bending mode.
- Linear viscous damping with a constant quality factor.
- Tuning fork modeled as two identical cantilever tines without base compliance.
- No acoustic radiation or mounting losses beyond the chosen Q value.

### References

- Inman, D. J., *Engineering Vibration*, 4th ed.
- Blevins, R. D., *Formulas for Natural Frequency and Mode Shape*.
- Thomson, W. T., *Theory of Vibration with Applications*.
