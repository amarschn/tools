# Beam Bending Response Tool

## Purpose

This tool estimates elastic deflection, shear force, bending moment, and
extreme fibre stress for common beam loading scenarios. It is designed to
support quick sizing studies while keeping the governing equations fully
transparent for verification and learning.

## Requirements

- Allow a user to pick between:
  - Simply supported beam with a midspan point load
  - Simply supported beam with a uniform distributed load
  - Cantilever beam with a free-end point load
  - Cantilever beam with a uniform distributed load
- Accept inputs in base SI units (metres, newtons, pascals) and present results
  using the same convention.
- Provide multiple cross-section options:
  - Rectangular
  - Symmetric I-beam
  - Solid circular
  - Hollow circular (tube)
  - Custom properties (direct entry of moment of inertia and section modulus or
    fibre distances)
- Return structured output that includes:
  - Maximum deflection magnitude and location
  - Maximum bending moment and shear force
  - Extreme fibre bending stress
  - Tabulated response data for plotting
- Reference the shared `pycalcs.structures` module so that equations and logic
  live in a single, reusable location.
