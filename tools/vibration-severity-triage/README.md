# Vibration Severity & Fault Triage

ISO 20816-3 zone classification combined with VDI 3839 fault signature pattern matching.

## Purpose

Field engineers and reliability analysts face two sequential questions when reviewing vibration data:
1. **Is this level acceptable?** — answered by ISO 20816 zone classification
2. **Why is it this high?** — answered by VDI 3839 fault signature matching

This tool answers both in a single workflow from one broadband measurement.

## Inputs

- Machine type, nominal power, rated speed
- Drive-end bearing type and foundation/mounting
- Operating speed, measurement direction, vibration quantity and value
- ISO 20816-3 machine group and zone boundary values (user-entered from their standard)
- Optional: baseline value, previous measurement (for delta/trend), bearing geometry (for defect frequencies)

## Outputs

- **Zone Classification tab**: ISO 20816-3 zone (A/B/C/D) with visual zone bar, delta from baseline, and trend indicator
- **Fault Triage tab**: Ranked fault signature cards (VDI 3839) with matched/contra indicators and follow-up actions
- **Next Steps tab**: Prioritised action list based on zone and fault results
- **Report tab**: Plain-text evaluation record for printing or export

## Standards Coverage

### ISO 20816-3
Industrial machines, nominal power > 15 kW, 120–15,000 RPM. The tool selects the applicable part
and machine group based on machine type inputs.

### VDI 3839 Fault Types (Phase 1)
| Fault | Reference |
|---|---|
| Mass Unbalance | VDI 3839-2 |
| Angular Misalignment | VDI 3839-3 |
| Parallel (Offset) Misalignment | VDI 3839-3 |
| Structural / Foundation Looseness | VDI 3839-4 |
| Rotating Looseness (bearing seat / shaft fit) | VDI 3839-4 |
| Rolling Element Bearing Defect | VDI 3839-5 |
| Electrical / Electromagnetic Excitation | VDI 3839 (general) |

## Copyright Note

ISO zone threshold tables are copyright ISO. This tool **does not republish** them.
Zone boundary values must be entered by the user from their own copy of ISO 20816-3 Table 1.
Placeholder defaults shown in the UI are indicative only and labelled accordingly.

## Python Module

`pycalcs/vibration_severity.py`

Key functions:
- `evaluate_vibration(...)` — main entry point, returns full evaluation dict
- `calculate_bearing_defect_frequencies(...)` — BPFO/BPFI/BSF/FTF from bearing geometry

## Phase 2 (Planned)

- ISO 20816-9 gear unit acceptance workflow + VDI 3839-7 gear mesh fault signatures
- ISO 20816-5 hydraulic machines
- Alarm/trip limit builder (ISO 20816-1 logic)
- Multi-measurement comparison (H, V, axial in one session)
