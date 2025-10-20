# Reynolds Number Explorer

## Purpose

Provide a compact fluid mechanics helper that:
* Computes the Reynolds number from user-specified velocity and characteristic length.
* Accepts either kinematic viscosity directly or the density/dynamic-viscosity pair.
* Classifies the resulting flow regime (laminar, transitional, turbulent) using standard thresholds.
* Surfaces the governing equation, substituted algebra, and property source in the UI.

## Requirements

### Python Logic

* Implemented in `pycalcs/fluids.py`.
* Expose `reynolds_number_analysis(velocity, characteristic_length, kinematic_viscosity=None, density=None, dynamic_viscosity=None)` which:
  * Validates input combinations and raises `ValueError` for invalid states.
  * Reuses shared helpers for the actual Reynolds number computation and flow classification.
  * Returns a dictionary containing:
    * `reynolds_number` (float)
    * `flow_regime` (string)
    * `viscosity_path` (string flag for UI messaging)
    * Optional `subst_*` entries for equation substitution rendering.
  * Includes a rich docstring with LaTeX equations and references (`Fox et al., Introduction to Fluid Mechanics`).

### UI

* Built from `tools/example_tool/index.html` template.
* Inputs:
  * Mean velocity (m/s).
  * Characteristic length (m).
  * Dropdown selecting either kinematic viscosity (m²/s) or density/dynamic viscosity (kg/m³ & Pa·s).
* Outputs:
  * Reynold number (scientific notation).
  * Flow regime classification and property-source badge.
  * Progressive disclosure card showing substituted algebra.
  * Plotly-powered visualization that shades laminar, transitional, and turbulent regions and marks the computed Reynolds number on a log axis.
* Includes export button that saves a JSON snapshot with inputs, results, and references.
* Background tab renders equations in MathJax using the docstring `---LaTeX---` block.

### Testing Guidance

* Laminar check: V = 0.1 m/s, L = 0.05 m, ν = 1.5e-5 m²/s → Re ≈ 333 (laminar).
* Transitional check: V = 0.5 m/s, L = 0.05 m, ν = 6.25e-6 m²/s → Re ≈ 4000 (transitional).
* Turbulent check via density/dynamic inputs: ρ = 998 kg/m³, μ = 1.0e-3 Pa·s, V = 2.0 m/s, L = 0.05 m → Re ≈ 9.98e4 (turbulent).
