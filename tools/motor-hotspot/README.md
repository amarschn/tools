# Motor Hot-Spot Estimator

## Purpose

This tool reconstructs the peak internal temperature of an electric motor winding at the instant power is removed. By fitting a two-node lumped thermal RC network to the measured cool-down trace at an accessible sensor, the calculator infers the hidden hot-spot temperature, reports the dominant time constants, and highlights how the estimate shifts with different assumptions about the hot-spot thermal mass.

## Requirements

- **Inputs**
  - Ambient temperature during the cool-down sequence (°C).
  - A timed series of sensor measurements taken after the motor is de-energised (minimum four time/temperature pairs).
  - An estimated heat-capacitance ratio between the hot-spot and the monitored mass (C_h/C_s). Leaving the field blank applies the default value of 0.35.
  - Optional selection of the time units used in the data entry (seconds, minutes, or hours).

- **Python Logic**
  - The shared library must expose `estimate_motor_hotspot_temperature(times, sensor_temperatures, ambient_temperature, heat_capacity_ratio=None)` inside `pycalcs/heat_transfer.py`.
  - The function returns the inferred hot-spot trace, the reconstructed sensor response, fitted decay constants, the feasible bounds on C_h/C_s, and sensitivity information that the UI renders.

- **Outputs & Visualisation**
  - Card view showing the estimated hot-spot temperature, the initial sensor reading, and the model fit quality (RMSE).
  - Summary table listing the fast/slow thermal time constants, the chosen thermal-mass ratio, and the resistance ratio R_hs/R_sa.
  - Sensitivity table illustrating how the hot-spot estimate moves with nearby values of C_h/C_s.
  - SVG plot comparing the measured sensor trace, the reconstructed sensor curve, and the inferred hot-spot trajectory in real time units.

## Estimating the Heat-Capacitance Ratio

- Treat `C_h` as the thermal mass of the copper turns forming the hot spot: multiply the copper volume participating in the hot spot by its density and specific heat (`mass × c_p`).
- Treat `C_s` as the thermal mass of the material that equilibrates with the sensor quickly (iron core, slot wedge, nearby epoxy). Use the same `mass × c_p` approach.
- A starting range of `r = C_h/C_s` between 0.2 and 0.5 suits embedded RTDs or thermistors near concentrated strands. Broader, distributed probes may warrant values near 0.8–1.2.
- Use teardown data or finite-element estimates when available, then bracket the ratio with the tool’s sensitivity table to see how uncertainty shifts the inferred hot spot.
- If your dataset only covers the post-shutdown "soak-out" rise (sensor temperature increases toward a plateau without the later cooldown), the calculator automatically applies a single-mode fit and flags that assumption; adding late-time data that shows the curve flattening will tighten the estimate.
