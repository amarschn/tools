# PID Tuning (Ultimate Gain)

## Purpose

This tool computes PI and PID controller settings from an ultimate gain test using the classic Ziegler-Nichols and Tyreus-Luyben rules. It provides parallel-form gains (Kp, Ki, Kd) plus the equivalent time constants (Ti, Td) so you can implement the results in common industrial controllers.

## Requirements

### Inputs

- Ultimate gain Ku measured at the onset of sustained oscillations (dimensionless).
- Ultimate period Pu measured at Ku (seconds).
- Tuning rule selection: Ziegler-Nichols or Tyreus-Luyben.
- Controller type selection: PI or PID.

### Outputs

- Proportional gain Kp (dimensionless).
- Integral time constant Ti (s).
- Derivative time constant Td (s), zero for PI.
- Integral gain Ki (1/s).
- Derivative gain Kd (s).

## Method Summary

1. Close the loop with proportional-only control.
2. Increase proportional gain until sustained oscillation appears.
3. Record Ku and the oscillation period Pu.
4. Apply the selected tuning rule to compute Kp, Ti, Td, then derive Ki and Kd.

## Visualization

- Time constants chart for Ti and Td (seconds).
- Dimensionless tuning coefficients chart for C_Kp = Kp/Ku, C_Ti = Ti/Pu, C_Td = Td/Pu.

## Assumptions and Limitations

- Results are starting points; confirm stability, noise sensitivity, and actuator limits before deployment.
- The controller is assumed to use the parallel form u = Kp * e + Ki * integral(e dt) + Kd * de/dt.
- Derivative filtering and anti-windup are not included in the equations and must be configured in the controller.

## References

- J. G. Ziegler and N. B. Nichols, "Optimum Settings for Automatic Controllers," Trans. ASME, 1942.
- B. D. Tyreus and W. L. Luyben, "Tuning PI Controllers for Integrator/Dead Time Processes," Ind. Eng. Chem. Res., 1992.
