# Composite Wall Heat Loss

## Purpose

Provide a fast, inspectable calculator for steady 1-D conduction through layered walls. The tool reports heat transfer rate, heat flux, overall U-value, and interface temperatures so designers can validate insulation stacks or retrofit options.

## Requirements

### Python Logic

* Implemented in `pycalcs/heat_transfer.py`.
* Function `composite_wall_analysis(area, interior_temperature, exterior_temperature, layer_thicknesses, layer_conductivities, interior_convection_coefficient=None, exterior_convection_coefficient=None)`:
  * Validates positive dimensions, matching layer arrays, and optional film coefficients.
  * Computes total thermal resistance by combining film and conduction resistances.
  * Returns a dictionary with:
    * `heat_transfer_rate` (W)
    * `heat_flux` (W/m²)
    * `overall_u_value` (W/m²·K)
    * `total_thermal_resistance` (K/W)
    * `interface_temperatures` (list of °C values from interior surface to ambient)
    * Supporting `subst_*` strings for each scalar result.
  * Docstring must contain description, parameters, returns, LaTeX equations, and Incropera reference.

### UI

* Based on `tools/example_tool/index.html`.
* Inputs:
  * Wall area, interior/exterior temperatures.
  * Optional interior/exterior convection coefficients.
  * Drop-down for 1–3 layers; each layer includes thickness (m) and conductivity (W/m·K).
* Results:
  * Render scalar outputs with equations in expandable details.
  * Show interface temperatures as a list (interior surface → ambient).
  * Provide a Plotly visualization linking node index to temperature.
* Background tab must echo docstring description and equations with MathJax.

### Usage Notes

* Warn users if any layer thickness or conductivity is missing.
* Default values should illustrate a typical insulated wall (e.g., insulation + sheathing + brick).
* Temperatures assumed in °C; coefficients in SI units; no unit conversions provided.

### Testing Guidance

* Compare against hand-calculated R-value chains:
  * Example: Area = 10 m², T_in = 21 °C, T_out = −5 °C, layers: [0.2 m @ 0.038 W/m·K, 0.02 m @ 0.21 W/m·K], hi = 8, ho = 25 → Expect Q ≈ 434 W.
* Validate interface temperatures decrease monotonically and final value matches exterior ambient.
