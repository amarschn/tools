# Unit Converter Tool

## Purpose

Offer a fast, trustworthy way to translate engineering quantities between SI,
imperial, and other frequently used unit systems. The tool exposes the shared
conversion logic so future calculators can reuse the same single source of
truth while engineers can validate calculations interactively.

## Requirements

- Allow the user to select a quantity family (length, mass, temperature, etc.)
  from the catalog provided by `pycalcs.units.get_unit_catalog`.
- Surface the available units for the chosen quantity using their symbols and
  descriptive names.
- Convert a numeric value from one unit to another using
  `pycalcs.units.convert_units`.
- Display the converted value, the intermediate SI-base value, and (when
  applicable) the pure multiplicative factor between the two units.
- Render any errors from the conversion helper as user-friendly messages.
- Provide contextual documentation parsed from the function docstrings in
  `pycalcs.units`, following the standard AGENTS template pattern.
