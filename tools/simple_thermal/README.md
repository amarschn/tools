# Thermal Calculator

A web-based tool for modeling basic thermal behavior of objects using convection and radiation heat transfer.

## Purpose

This calculator provides engineering estimates for:
- **Transient Cooling:** How quickly a hot object cools down in air over time.
- **Steady State Temperature:** The final equilibrium temperature an object reaches when subjected to a constant heat input power.

It helps understand heat transfer rates, temperature profiles (for transient), equilibrium points, and time constants.

## Features

- Supports two calculation modes:
    - **Transient Cooling:** Simulates temperature drop from an initial state.
    - **Steady State (with Heat Source):** Calculates equilibrium temperature with constant power input.
- Supports two basic geometries:
  - Rectangular plates
  - Cylinders
- Models both natural and forced convection
- Includes radiation heat transfer
- Handles different material properties (presets and custom)
- Visualizes results (plots for transient, summary for steady state)
- Provides theoretical background and equations

## Usage Instructions

1.  **Select Mode:** Choose between "Transient Cooling" or "Steady State".
2.  **Input Parameters:**
    *   Select geometry type and orientation.
    *   Enter dimensions.
    *   Choose material (from presets or custom properties). Note: Density and Specific Heat are only used in Transient mode.
    *   Set thermal conditions:
        *   *Transient:* Initial temperature, ambient temperature, air velocity.
        *   *Steady State:* Heat input power (W), ambient temperature, air velocity.
    *   *Transient:* Adjust simulation time and number of steps if needed.
3.  **Calculate Results:**
    *   Click "Compute".
    *   *Transient:* View results including cooling time constants, final temperature, and examine temperature/heat loss rate plots.
    *   *Steady State:* View the calculated equilibrium temperature and the balance between heat input and heat loss (convection + radiation).

4.  **Theory Section:**
    *   Learn about the heat transfer mechanisms and calculation methods.
    *   Understand the equations used.
    *   Review assumptions and limitations.

## Mathematical Approach

- **Transient Cooling:** Uses the lumped capacitance method (assumes uniform internal temperature, Biot < 0.1). Solves the energy balance equation `ρVcₚ dT/dt = - (q_conv + q_rad)` over time steps.
- **Steady State:** Solves the steady-state energy balance `Q_input = q_conv + q_rad`. Finds the surface temperature `T_ss` where `Q_input = h(T_ss)A(T_ss - T_amb) + εσA(T_ss_K⁴ - T_amb_K⁴)` using an iterative numerical solver.
- **Convection & Radiation:** Both modes use the same underlying functions to calculate `h`, `q_conv`, and `q_rad`, based on empirical correlations and the Stefan-Boltzmann law.

## Limitations

This tool provides approximate results and is intended for educational and early design purposes.

- Assumes uniform temperature throughout the object (Lumped Capacitance for transient, uniform surface temp for steady state). Less accurate for large objects or low-conductivity materials.
- Steady state assumes heat input is instantly and uniformly distributed.
- Uses empirical correlations for convection coefficients (`h`).
- Assumes simple geometries and radiation view factor of 1 to surroundings.
- Assumes constant material properties (except air properties for `h`) and ambient conditions.

For more detailed analysis, CFD (Computational Fluid Dynamics) or FEA (Finite Element Analysis) simulations are recommended.

## Technical Implementation

- Frontend: HTML, CSS, JavaScript
- Calculation Logic: Python (via Pyodide for in-browser execution)
- Visualization: Chart.js for plots (transient mode only)