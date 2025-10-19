# Thermal Calculator

A web-based tool for modeling basic thermal behavior of objects, including finned heat sinks, using convection and radiation heat transfer.

## Purpose

This calculator provides engineering estimates for:
- **Transient Cooling:** How quickly a hot object cools down in air over time.
- **Steady State Temperature:** The final equilibrium temperature an object reaches when subjected to a constant heat input power.

It helps understand heat transfer rates, temperature profiles (for transient), equilibrium points, and time constants for simple shapes and standard extruded heat sinks.

## Features

- Supports two calculation modes:
    - **Transient Cooling:** Simulates temperature drop from an initial state.
    - **Steady State (with Heat Source):** Calculates equilibrium temperature with constant power input.
- Supports multiple geometries:
  - Rectangular plates
  - Cylinders
  - **Finned Heat Sinks:** With user-defined base, fin, and spacing parameters.
- Models both **natural** and **forced** convection with appropriate correlations for each geometry.
- Includes radiation heat transfer.
- Handles different material properties (presets and custom).
- Visualizes results (plots for transient, summary and charts for steady state).
- Provides theoretical background and equations.

## Usage Instructions

1.  **Select Mode:** Choose between "Transient Cooling" or "Steady State".
2.  **Input Parameters:**
    *   Select geometry type (Plate, Cylinder, or **Heatsink**) and orientation.
    *   Enter dimensions for the selected geometry.
    *   Choose material (from presets or custom properties). Note: Density and Specific Heat are only used in Transient mode.
    *   Set thermal conditions:
        *   *Transient:* Initial temperature, ambient temperature, air velocity.
        *   *Steady State:* Heat input power (W), ambient temperature, air velocity.
    *   *Transient:* Adjust simulation time and number of steps if needed.
3.  **Calculate Results:**
    *   Click "Compute".
    *   *Transient:* View results including cooling time constants, final temperature, and examine temperature/heat loss rate plots.
    *   *Steady State:* View the calculated equilibrium temperature and the balance between heat input and heat loss, including a breakdown of convection vs. radiation.

4.  **Theory Section:**
    *   Learn about the heat transfer mechanisms and calculation methods.
    *   Understand the equations used for each geometry.
    *   Review assumptions and limitations.

## Mathematical Approach

- **Transient Cooling:** Uses the lumped capacitance method (assumes uniform internal temperature). Solves the energy balance equation `ρVcₚ dT/dt = - (q_conv + q_rad)` over discrete time steps.
- **Steady State:** Solves the steady-state energy balance `Q_input = q_conv + q_rad`. Finds the surface temperature `T_ss` where `Q_input = h(T_ss)A(T_ss - T_amb) + εσA(T_ss_K⁴ - T_amb_K⁴)` using an iterative numerical solver.
- **Heatsink Modeling:**
  - **Natural Convection:** The characteristic length is assumed to be the **fin spacing (`s`)**. The fins are modeled as an array of vertical plates, which is the most effective orientation for natural convection.
  - **Forced Convection:** Models airflow through the channels between fins.
    - The **in-channel air velocity** is calculated, accounting for blockage by the fins.
    - The characteristic length is the **hydraulic diameter (`D_h = 2s`)**.
    - A specific Nusselt number correlation for **developing flow in a duct** is used to find the convection coefficient `h`.
- **Convection & Radiation:** All modes use the same underlying functions to calculate `q_conv` and `q_rad`, based on empirical correlations and the Stefan-Boltzmann law.

## Limitations

This tool provides approximate results and is intended for educational and early design purposes.

- Assumes uniform temperature throughout the object (Lumped Capacitance/uniform surface temp). Less accurate for large objects, low-conductivity materials, or very tall fins.
- **Heatsink model is simplified:** It does not account for fin efficiency, heat spreading resistance in the base, or airflow bypassing the heat sink.
- Steady state assumes heat input is instantly and uniformly distributed over the base.
- Uses empirical correlations for convection coefficients (`h`).
- Assumes simple radiation view factor of 1 to surroundings.
- Assumes constant material properties (except air properties for `h`) and ambient conditions.

For more detailed analysis, CFD (Computational Fluid Dynamics) or FEA (Finite Element Analysis) simulations are recommended.

## Technical Implementation

- Frontend: HTML, CSS, JavaScript
- Calculation Logic: Python (via Pyodide for in-browser execution)
- Visualization: Chart.js for plots