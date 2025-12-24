# PID Tuning (Ultimate Gain)

## Purpose

This tool computes PI and PID controller settings from an ultimate gain test, providing baseline tuning using classic rules. It supports the Ziegler-Nichols and Tyreus-Luyben ultimate gain methods and returns both parallel-form gains and equivalent time constants.

## Requirements

### Inputs

- Ultimate gain Ku from the onset of sustained oscillations (dimensionless).
- Ultimate period Pu of the oscillation (s).
- Tuning rule selection (Ziegler-Nichols or Tyreus-Luyben).
- Controller type (PI or PID).

### Outputs

- Proportional gain Kp (dimensionless).
- Integral and derivative time constants Ti, Td (s).
- Parallel-form gains Ki (1/s) and Kd (s).

### Assumptions and Limitations

- The ultimate gain test is performed in a closed loop and yields a stable, repeatable oscillation.
- Gains are intended as starting points and may require refinement for noise, actuator limits, or robustness.
- Derivative action is unfiltered in the equations; practical implementations may add a filter.

### References

- J. G. Ziegler and N. B. Nichols, "Optimum Settings for Automatic Controllers," Trans. ASME, 1942.
- B. D. Tyreus and W. L. Luyben, "Tuning PI Controllers for Integrator/Dead Time Processes," Ind. Eng. Chem. Res., 1992.
