# Motor Thermal Estimator

A first-order engineering tool to estimate the thermal performance of Brushless DC (BLDC) motors under continuous load.

## Purpose
Prevent motor burnout by predicting:
1.  **Steady-State Temperature:** Will the motor eventually overheat?
2.  **Time-to-Limit:** How long can it run at this current before damaging magnets?

## Methodology
This tool uses a **Lumped Parameter Thermal Network** (LPTN) approach. It treats the motor as a single thermal node with:
*   **Heat Generation:** $P = I^2 R$, accounting for resistance increase with temperature ($0.00393 / ^\circ C$).
*   **Thermal Mass ($C_{th}$):** Weighted average of Copper, Iron, and Aluminum components.
*   **Thermal Resistance ($R_{th}$):** Derived from surface area and convection coefficients ($h$).

## Key Assumptions
*   **Uniform Temperature:** The entire motor is assumed to be at one "bulk" temperature. In reality, inner windings are hotter than the case.
*   **Constant Cooling:** Convection coefficients are estimates based on typical scenarios (Static, Prop Wash, etc.).
*   **Iron Losses:** Magnetic losses (eddy currents/hysteresis) are neglected. This tool focuses on Copper Loss ($I^2R$), which dominates at high torque/load.

## Usage
1.  **Input Motor Data:** Measure or find resistance, mass, and dimensions in the datasheet.
2.  **Select Environment:** Choose the airflow condition that matches your application.
3.  **Simulate:** Run the calculation to see the heating curve.

## Disclaimer
This is an estimation tool. Always verify with real-world testing using a temperature gun or telemetry sensor.
