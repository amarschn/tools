# Coefficient of Friction Lookup

## Purpose

Provide an interactive reference that estimates the coefficient of friction
between pairs of engineering materials under typical surface conditions. The
tool focuses on early-stage design and verification, offering quick access to
static and kinetic friction ranges plus contextual guidance.

## Requirements

- Let the user pick two materials from the shared friction catalog and choose a
  surface condition (dry, lubricated, wet, etc.).
- Display static and kinetic coefficient ranges (minimum, maximum, and typical
  values) returned by `pycalcs.friction.lookup_coefficient_of_friction`.
- Surface explanatory notes, comparable material pairings, and representative
  applications for the selected combination.
- Leverage the shared docstring parsing utility so the UI uses the Python
  documentation as the single source of truth for descriptions and equations.
- Expose the same material catalog to the frontend via
  `pycalcs.friction.get_friction_catalog` so no material metadata is duplicated
  in the browser code.
