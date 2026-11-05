# Unit Converter Tool

## Purpose

Convert engineering quantities between SI, imperial, and other common units.
Edit either value to convert in that direction. The Python module
`pycalcs.units` supplies the unit catalog and conversion factors.

The page is `index.html`; its browser logic is in `shared/dual-core.js`.
Use **Copy conversion link** to share the selected quantity, both units, and
the value. The loading screen covers initialization and offers a retry if the
Python runtime cannot load.

## Thermal power

Choose **Power / heat rate** for W, kW, MW, BTU/hr, kBTU/hr, MMBTU/hr,
refrigeration tons, kcal/hr, horsepower, and mW. Filter either unit list by
symbol or name, for example `BTU` or `refrigeration`.

- BTU uses the International Table (IT) definition, also used by the Energy
  category. One BTU/hr is approximately 0.293071 W.
- kBTU/hr means one thousand BTU/hr; MMBTU/hr means one million BTU/hr.
- One refrigeration ton (`ton_ref`) is 12,000 BTU/hr, approximately 3.51685 kW.
- kcal/hr uses the IT kilocalorie (4186.8 J), giving 1.163 W per kcal/hr.
  The existing nutritional Calorie under Energy uses 4184 J.

Factors follow [NIST SP 811, Appendix B.9](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9).
Python callers can also use `BTU/h`, `Btu/h`, `Btu/hr`, corresponding
`kBTU`/`kBtu` and `MMBTU`/`MMBtu` spellings, `kcal/h`, or `TR`. The browser
shows one entry per unit.

## Viscosity

Choose **Dynamic viscosity** for Pa·s, mPa·s, µPa·s, centipoise (cP),
poise (P), kg/(m·s), g/(cm·s), lb/(ft·s), and lbf·s/ft².
The pound-mass and pound-force units are distinct.

Choose **Kinematic viscosity** for m²/s, mm²/s, cm²/s, centistokes (cSt),
stokes (St), ft²/s, and in²/s.

One cP equals one mPa·s; one cSt equals one mm²/s. These factors follow
[NIST SP 811, Appendix B.8](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8).
The two viscosity categories stay separate because converting between them
requires fluid density at the same temperature. The converter changes units
within each category; it does not estimate fluid properties or density.

## Requirements

- Allow the user to select a quantity family (length, mass, temperature, etc.)
  from the catalog provided by `pycalcs.units.get_unit_catalog`.
- Surface the available units for the chosen quantity using their symbols and
  descriptive names.
- Convert a numeric value from one unit to another using
  `pycalcs.units.convert_units`. Results update instantly
  as the user types or changes a selection.
- Display the converted value, the intermediate SI-base value, and (when
  applicable) the pure multiplicative factor between the two units.
- Expose both “from” and “to” numeric fields, keep them synchronised, and
  surface SI base data with relatable comparisons.
- Render any errors from the conversion helper as user-friendly messages.
- Provide contextual documentation parsed from the function docstrings in
  `pycalcs.units`, following the standard AGENTS template pattern.
