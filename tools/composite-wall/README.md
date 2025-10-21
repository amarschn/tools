# Composite Wall Heat Loss

## Purpose

Interactive workbook for steady one-dimensional conduction through layered walls. The tool now reports per-layer resistances, interface temperatures, and both SI and inch–pound conversions (U-value, R-value, heat flux) so envelope designs can be cross-checked against building-code requirements.

## Core Features

- **Layer-by-layer resistance audit** – automatic breakout of conduction and film resistances with symbolic derivations.
- **Sticky summary card** – keeps heat flux, U-value, total R-value, and heat transfer rate visible while scrolling long forms.
- **Imperial/SI dual output** – converts key metrics to BTU/hr·ft²·°F and hr·ft²·°F/BTU in addition to the native SI values.
- **Temperature profile plot** – Plotly visualization traces the interface temperatures across the stack, highlighting where major drops occur.

## Implementation Notes

- **Python** (`pycalcs/heat_transfer.py`)
  - `composite_wall_analysis(...)` now returns:
    - `heat_transfer_rate`, `heat_transfer_rate_ip`
    - `heat_flux`, `heat_flux_ip`
    - `overall_u_value`, `overall_u_value_ip`
    - `total_thermal_resistance`, `total_r_value_ip`
    - `layer_resistances`, `film_resistances`
    - `temperature_profile` (ordered dicts with name/type/temperature/resistance)
    - `interface_temperatures` (legacy list for compatibility)
    - Detailed `subst_*` strings for each calculation step.
  - Docstring expanded with additional references (Incropera, ASHRAE, Çengel & Ghajar) and explicit LaTeX for film/conduction resistances plus conversion factors.

- **UI** (`tools/composite-wall/index.html`)
  - Based on the **stacked** template variant: inputs appear first, outputs follow, and a sticky summary anchors to the viewport.
  - Inputs grouped into fieldsets (geometry, films, layers) with responsive grids and inline tooltips.
  - Results pane replaced with custom sections:
    - Metric grid for key outputs
    - Resistance table (with MathJax derivations)
    - Temperature profile table
    - Derivation list for heat flux/U-value conversions
  - Visualization tab plots the temperature profile using descriptive node labels.

## Usage Guidance

- Thickness must be entered in **metres**, conductivity in **W/m·K**, and film coefficients in **W/m²·K**.
- Leave the convection coefficients blank to exclude film resistances from the series network.
- Default values emulate a typical insulated wall (insulation + sheathing + brick) to provide a quick sanity check.

## Testing Checklist

1. Hand-verify the default scenario against an R-value chain:
   - Area = 10 m², T<sub>in</sub> = 21 °C, T<sub>out</sub> = −5 °C
   - Layers: [0.20 m @ 0.038 W/m·K, 0.02 m @ 0.21 W/m·K, 0.01 m @ 0.72 W/m·K]
   - h<sub>i</sub> = 8, h<sub>o</sub> = 25 → expect Q ≈ 48 W, U ≈ 0.48 W/m²·K.
2. Toggle layer counts (1–3) and confirm hidden layer cards do not contribute to resistance.
3. Validate that removing film coefficients updates the resistance table and brings the plotted exterior node temperature up to the final layer surface.
4. Compare SI↔IP conversions against trusted tables (1 W/m²·K = 0.176 BTU/hr·ft²·°F; 1 (m²·K)/W = 5.678 hr·ft²·°F/BTU).***
