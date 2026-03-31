# Fan Curve Explorer & Selector

Select, compare, and understand fan operating points in one analysis workspace.

## Purpose

This tool helps engineers, students, and hobbyists answer the practical fan selection question: given a system requirement and one or more candidate fans, where will each fan actually operate, what margin or shortfall exists at the target duty, how much power will it draw, and how do competing architectures compare?

## Features

- **Single-workspace comparison** — active result, plot, assumptions, derivations, and candidate matrix stay visible together
- **Two system-definition paths** — quick duty-point inference or direct entry of a known system-resistance coefficient
- **Multi-curve visualization** — pressure, power, and efficiency views with operating-point markers
- **Real comparison logic** — ranking by power, cost, efficiency, duty margin, or stability
- **Per-candidate metadata** — each fan carries its own pressure basis, reference density, reference speed, and operating speed
- **Flexible import** — CSV / pasted data can include flow, pressure, optional power, and optional efficiency columns
- **Built-in fan library** — 6 synthetic archetypes (axial, centrifugal, mixed-flow) for architecture-level exploration
- **Tiered warning system** — blocking, caution, and info warnings shown per active candidate
- **Traceable derivations** — SI-based substituted equations for the active result

## Scope

### What this tool does

- Fan/system curve intersection at a duty point
- Direct system-curve comparison using a user-entered K coefficient
- Pressure-basis compatibility checks
- Density and speed scaling with affinity laws
- Energy and cost comparison when power data is available
- Architecture-level exploration across axial, mixed-flow, and centrifugal families

### What this tool does not do

- Blade geometry design
- CFD or acoustic prediction
- Duct network solving
- Official AMCA certification or FEI calculation

## References

- ANSI/AMCA 210-25: Laboratory methods of testing fans
- AMCA Publication 201-23: Fans and Systems
- U.S. DOE Improving Fan System Performance Sourcebook
- [DOE Fan Systems](https://www.energy.gov/cmei/ito/fan-systems)
- [DOE Fan Sourcebook (PDF)](https://www.energy.gov/sites/default/files/2014/05/f16/fan_sourcebook.pdf)
- [AMCA Certified Ratings Search](https://www.amca.org/certify/amca-certified-rating-program-search.html)

## Phase 1 Spec

See `plans/2026-03-29_fan_curve_explorer_selector_spec.md` for the full product specification.
