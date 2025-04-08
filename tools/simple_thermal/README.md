# Thermal Dissipation Calculator

A tool for modeling basic thermal dissipation of hot objects using convection and radiation heat transfer equations.

## Purpose

This calculator provides engineering estimates for:
- How quickly a hot object cools down in air
- Heat transfer rates through convection and radiation
- Temperature profiles over time
- Time constants and time to reach equilibrium

## Features

- Supports two basic geometries:
  - Rectangular plates
  - Cylinders
- Models both natural and forced convection
- Includes radiation heat transfer
- Handles different material properties
- Visualizes temperature change over time
- Provides theoretical background and equations

## Usage Instructions

1. **Input Parameters:**
   - Select geometry type and orientation
   - Enter dimensions
   - Choose material (from presets or custom properties)
   - Set thermal conditions (initial temperature, ambient temperature, air velocity)
   - Adjust simulation time as needed

2. **Calculate Results:**
   - Click "Compute & Update" to run the calculation
   - View results, including cooling time constants and equilibrium temperature
   - Examine temperature and heat transfer rate plots
   - Watch the animated visualization

3. **Theory Section:**
   - Learn about the heat transfer mechanisms (conduction, convection, radiation)
   - Understand the equations used in the calculations
   - Review assumptions and limitations

## Mathematical Approach

The calculator uses the lumped capacitance method to model heat transfer, which assumes:
- Uniform temperature distribution within the object (valid for Biot number < 0.1)
- Combined convection and radiation heat transfer from the surface
- Temperature-dependent convection coefficients
- Constant material properties

## Limitations

This tool provides approximate results and is intended for educational and early design purposes. It has the following limitations:

- Assumes uniform temperature throughout the object (simplification)
- Uses empirical correlations for convection coefficients
- Doesn't account for complex geometries or fins
- No support for multiple materials or phase changes
- Assumes constant ambient conditions

For more detailed analysis, CFD (Computational Fluid Dynamics) or FEA (Finite Element Analysis) simulations are recommended.

## Technical Implementation

- Frontend: HTML, CSS, JavaScript
- Calculation Logic: Python (via Pyodide for in-browser execution)
- Visualization: Chart.js for plots, Canvas API for object visualization