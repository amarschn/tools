# Battery Runtime Estimator

## Purpose

Estimate battery runtime with a configurable load model and practical corrections. The tool combines pack or
cell-level specifications with internal resistance, Peukert effects, temperature impacts, and duty-cycle
loading to deliver transparent, repeatable runtime estimates.

## Requirements

### Inputs

- Chemistry selection to seed sensible defaults (nominal voltage, cutoff voltage, Peukert exponent).
- Pack-level specs (nominal voltage, capacity, internal resistance, cutoff voltage) or cell-level specs
  (series/parallel count, per-cell voltage, capacity, internal resistance, cutoff voltage).
- Load model: constant current, constant power, or constant resistance.
- Converter efficiency and duty cycle (fraction of time the load is active).
- Temperature, reference temperature, and capacity temperature coefficient.
- Peukert exponent and reference current for rated capacity.
- Depth-of-discharge and state-of-health limits.

### Outputs

- Estimated runtime in hours and minutes.
- Effective usable capacity after adjustments.
- Average battery current and power.
- Energy delivered (Wh).
- Loaded voltage, voltage sag, and C-rate.
- Derived pack voltage, capacity, resistance, and cutoff voltage.

### Assumptions & Limitations

- Uses a constant nominal voltage and lumped internal resistance; no dynamic voltage curve or transient
  recovery modelling.
- Peukert correction is applied to average current; intermittent loads are approximated via duty cycle.
- Converter efficiency is applied as a simple scaling of load demand.
- Cell/pack heating, aging rate, and cut-off hysteresis are not modelled.

### References

- D. Linden and T. B. Reddy (eds.), *Handbook of Batteries*, 4th ed., McGraw-Hill, 2011.
- Peukert's law for lead-acid and high C-rate capacity reduction concepts.
