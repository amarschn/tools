# Ideal Gas Law Explorer

## Purpose

Provide a fast `PV = nRT` solver that lets users solve for pressure, volume,
amount, or temperature with common SI/Imperial-friendly unit choices.

The tool is designed for:
- Rapid checks during process and thermal scoping.
- Equation traceability via substituted values.
- Unit-safe workflows where inputs and outputs stay in the user's selected units.

## Requirements

### Python Logic

- Implemented in `pycalcs/gases.py`.
- Expose `solve_ideal_gas_law(...)` with:
  - Solve target selection (`pressure`, `volume`, `amount`, `temperature`).
  - Unit-aware conversion to SI for calculation.
  - Validation of physical constraints (positive pressure/volume/amount and
    absolute temperature above zero kelvin).
  - Return values in both selected units and SI units.
  - Substituted equation strings for progressive disclosure.

### UI

- Built from the standard standalone template pattern in `tools/example_tool/`.
- Inputs:
  - Solve-for selector.
  - Pressure, volume, amount, and temperature values with unit dropdowns.
  - The solved field is disabled and computed automatically.
- Outputs:
  - Primary solved variable card.
  - Full state results (all four variables).
  - Derivation panel with equation and substituted values.
  - SI verification block and residual check (`PV - nRT`).
- Visualization:
  - P-V isotherm around the solved state with the solved point highlighted.

### Test Cases

- STP reference check: `n=1 mol`, `T=273.15 K`, `V=0.022414 m^3` -> `P ~= 101325 Pa`.
- Additional solve modes for volume, amount, and temperature.
- Input validation tests for invalid mode and non-physical values.
