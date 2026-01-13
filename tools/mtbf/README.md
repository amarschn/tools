# Reliability Prediction Tool

## Purpose

Estimate system reliability and equivalent MTBF from a list of component MTBF values. The tool uses a constant failure rate (exponential) model and supports simple parallel redundancy within each component block.

## Workflow

- Enter mission time in hours.
- Add components and their MTBF values. Use series count for repeated units in series.
- Toggle advanced options to add parallel redundancy and run a separate reliability allocation scenario.
- Review the system reliability, equivalent failure rate, and equivalent MTBF with derivations.

## Inputs

- Mission time (hours).
- Component table:
  - Component name (label only).
  - MTBF (hours).
  - Series count (identical units in series).
  - Parallel count (redundant units in parallel, advanced).
- Allocation inputs (advanced): target system reliability and component count for equal allocation.

## Outputs

- System reliability at mission time.
- Equivalent failure rate and MTBF based on the system reliability.
- Component summary table with per-block reliability.
- Reliability allocation targets when provided.

## Assumptions and Limitations

- Components follow an exponential failure distribution with constant hazard rate.
- Component failures are independent.
- Parallel redundancy assumes no repair during the mission.
- Equivalent failure rate and MTBF are derived from the mission time and are not time-invariant for redundant systems.

## References

- O'Connor, P.D.T. and Kleyner, A. Practical Reliability Engineering, 5th ed.
- Ebeling, C.E. An Introduction to Reliability and Maintainability Engineering.
- IEC 60300-3-1: Dependability management - Application guide.
