# Heatsink Designer & Analysis Tool

This tool is being rebuilt as a dedicated heatsink design and analysis workflow for air-cooled plate-fin heatsinks.

## Purpose

The redesigned tool is meant to answer three practical questions:

1. What sink-to-ambient thermal resistance is required for a target source, junction, or case temperature?
2. How will a specific plate-fin heatsink perform under natural convection, forced flow, or a fan-limited operating point?
3. Which geometry changes matter most when trading thermal resistance against airflow impedance?

The tool is intentionally design-oriented rather than a generic "thermal calculator." The focus is understanding thermal capability, limits, and tradeoffs for realistic heatsink layouts while still supporting progressive simplicity and progressive disclosure.

## Progressive Simplicity

The default workflow should expose only the minimum inputs needed to get a useful result quickly:

- Heat load
- Ambient temperature
- Target source/junction or base temperature
- Cooling mode
- Envelope dimensions

Everything else belongs behind expert-mode toggles or deeper analysis views.

## Progressive Disclosure

The rebuilt tool will expose thermal reasoning in layers. The term "junction" is
kept for the upper thermal node because it matches standard thermal-resistance
notation, but in general heatsink work it should be read as the hottest internal
source temperature of the mounted part.

- **L0 Result:** Required thermal resistance, base temperature, source/junction temperature, pressure drop, and pass/fail margin
- **L1 Equation:** Numbered governing equations for resistance, convection, radiation, and fin efficiency
- **L2 Substitution:** Actual values inserted into each governing equation
- **L3 Intermediate steps:** Geometry breakdown, channel velocity, Reynolds/Rayleigh/Nusselt numbers, efficiency factors, and resistance stack
- **L4 Background:** Deep explanation of parallel-plate natural convection, developing duct flow, fan/system curves, and fin tradeoffs
- **L5 References:** Primary papers, textbooks, and validation notes

## Phase 1 Scope

The first implementation slice is limited to straight plate-fin heatsinks in air with steady-state analysis.

Included in Phase 1:

- Plate-fin geometry model
- Natural convection analysis for vertical plate arrays
- Forced convection analysis for user-specified flow or simple fan curves
- Radiation as a linearized coefficient
- Straight-fin efficiency and overall surface efficiency
- Pressure-drop estimation for fin channels
- Required sink-resistance calculation from thermal budget

Deferred to later phases:

- Transient thermal response
- Pin-fin or radial-fin geometries
- Multi-source spreading resistance models
- Airflow bypass estimation
- Export/report generation

## Technical Direction

The old local `thermal_calc.py` implementation is being retired in favor of a reusable `pycalcs` module and a full advanced-template UI. That aligns this tool with the project standard and removes the current legacy duplication problem.

The solver should stay explicit about what is modeled versus what is not. When a shortcut is used, the UI and background section must state it plainly.

## References Driving the Rewrite

- Bar-Cohen, A., Rohsenow, W. M. (1984). *Thermally Optimum Spacing of Vertical, Natural Convection Cooled, Parallel Plates*. Journal of Heat Transfer. https://doi.org/10.1115/1.3246622
- Teertstra, P., Yovanovich, M. M., Culham, J. R., Lemczyk, T. (1999). *Analytical forced convection modeling of plate fin heat sinks*. https://doi.org/10.1109/STHERM.1999.762426
- Muzychka, Y. S., Yovanovich, M. M. (2004). *Laminar Forced Convection Heat Transfer in the Combined Entry Region of Non-Circular Ducts*. Journal of Heat Transfer. https://doi.org/10.1115/1.1643752
- Simons, R. E. (2003/2016 reprint). *Estimating Parallel Plate-fin Heat Sink Pressure Drop*. Electronics Cooling. https://www.electronics-cooling.com/2016/04/calculation-corner-estimating-parallel-plate-fin-heat-sink-pressure-drop/
- Incropera, F. P., DeWitt, D. P., Bergman, T. L., Lavine, A. S. *Fundamentals of Heat and Mass Transfer*.
