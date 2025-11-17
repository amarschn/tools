# Pairwise Converter Prototype

## Purpose

Explore a traditional dual-dropdown unit converter that still meets the
project's transparency requirements by surfacing base unit values and
pure multipliers when available.

## Requirements

- Let the user choose any quantity from the shared unit catalog.
- Populate the "from" and "to" unit dropdowns dynamically based on the chosen quantity.
- Display the converted value, the equivalent SI base value, and whether a simple multiplier exists.
- Use `pycalcs.unit_prototypes.convert_unit_pair` as the calculation backend.
