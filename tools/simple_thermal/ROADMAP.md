# Heatsink Designer Roadmap

This roadmap is the implementation contract for the heatsink rewrite.

## Phase 1: Solver Foundation

- [x] Create a dedicated task branch for the rewrite
- [x] Replace the old generic README with a heatsink-specific product definition
- [x] Build a new `pycalcs/heatsinks.py` module for plate-fin steady-state analysis
- [x] Add unit tests for geometry, convection, fin efficiency, pressure drop, and fan operating points
- [x] Keep the old local `thermal_calc.py` out of the new implementation path

## Phase 2: New Tool UI

- [ ] Rebuild `tools/simple_thermal/index.html` from `tools/example_tool_advanced/index.html`
- [ ] Add a default workflow for required sink resistance and basic heatsink analysis
- [ ] Add expert mode for secondary resistances, emissivity, and fan parameters
- [ ] Add derivation panels for every primary result card
- [ ] Add a loading overlay, settings panel, and theme support

## Phase 3: Visual Analysis

- [ ] Geometry sketch with labeled dimensions
- [ ] Thermal-resistance ladder from junction to ambient
- [ ] Fan curve vs. heatsink pressure-drop curve
- [ ] Geometry sweep plots for fin count, spacing, and height
- [ ] Sensitivity view for emissivity and airflow

## Phase 4: Background Depth

- [ ] Build a deep background tab with numbered sections and variable legends
- [ ] Document validity limits of each convection/pressure-drop correlation
- [ ] Add worked examples for natural and fan-assisted designs
- [ ] Add validation notes comparing tool outputs against reference examples

## Phase 5: Advanced Extensions

- [ ] Multi-source spreading resistance
- [ ] Airflow bypass estimation
- [ ] Mixed-convection handling
- [ ] Additional geometries (pin fin, radial fin)
- [ ] Exportable design summary

## Guardrails

- Every new equation must trace to a named reference.
- Every primary output must have a substituted-equation string.
- The default experience must remain simple even as expert features are added.
- If a model assumption is weak, expose it in the UI instead of hiding it.
