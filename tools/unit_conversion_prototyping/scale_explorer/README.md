# Scale Explorer Prototype

## Purpose

Examine how the interface can visualise changes in order of magnitude by
showing the same measurement across multiple related units.

## Requirements

- Let the user pick between stress (Pa/kPa/MPa) and velocity (m/s/km/h/mph) bands.
- Accept an anchor unit from the selected band and convert the entered value across all band units.
- Present the converted magnitudes in a compact comparative layout.
- Use `pycalcs.unit_prototypes.cascade_unit_scales` to generate the results.
