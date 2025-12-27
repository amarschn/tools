# Vibration Isolation Designer

## Purpose
- Evaluate single-degree-of-freedom isolators for base displacement or applied force excitation.
- Size the required stiffness to meet a target transmissibility at a specified excitation frequency.
- Provide progressive detail: core isolation metrics in simple mode, optional response amplitudes and checks in advanced mode.

## Requirements
- Inputs are SI: mass in kg, stiffness in N/m, damping in N*s/m or ratio, displacement in m, force in N, frequency in Hz.
- Analyze mode requires either per-mount stiffness or static deflection under gravity.
- Design mode requires a target transmissibility between 0 and 1.
- Advanced response amplitudes require either base displacement amplitude (base excitation) or force amplitude (force excitation).

## Assumptions
- Linear stiffness and viscous damping.
- Single-degree-of-freedom model with harmonic excitation.
- Small deflection response and steady-state sinusoidal behavior.

## References
- Inman, D. J., Engineering Vibration, 4th ed., 2014.
- Rao, S. S., Mechanical Vibrations, 6th ed., 2017.
