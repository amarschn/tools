# Vibration Severity & Fault Triage Tool
## ISO 20816 Severity Evaluator + VDI 3839 Fault Signature Matcher

---

## Overview

Field engineers and reliability analysts routinely face two sequential questions when reviewing vibration data:

1. **Is this level acceptable?** — answered by ISO 20816 zone classification
2. **Why is it this high?** — answered by VDI 3839 fault signature matching

This tool answers both in a single workflow. The user enters machine parameters and measured vibration values; the tool returns the applicable ISO 20816 part and machine group, the zone classification with delta-from-baseline logic, and a ranked list of probable fault signatures derived from VDI 3839 pattern rules, each with recommended follow-up measurements.

> **Copyright note**: No ISO or VDI threshold tables are republished. The tool prompts users to supply or confirm limit values from their own copy of the standard. The tool provides evaluation logic, interpretation guidance, fault pattern matching, and report structure.

---

## Scope

### Covered (Phase 1)
- **ISO 20816-3**: Industrial machines, nominal power > 15 kW, speeds 120–15,000 RPM (broadest industrial scope — pumps, fans, compressors, motors, generators)
- **VDI 3839 fault types**: Unbalance (Pt 2), Misalignment (Pt 3), Mechanical looseness (Pt 4), Rolling element bearing defects (Pt 5)

### Deferred (Phase 2)
- ISO 20816-9: Gear units (acceptance testing workflow)
- VDI 3839-7: Gear mesh fault signatures
- ISO 20816-5: Hydraulic machines
- Alarm/trip limit builder (ISO 20816-1 logic)

---

## Inputs

### Section 1 — Machine Description

| Field | Type | Options / Range | Notes |
|---|---|---|---|
| Machine type | Select | Electric motor, Centrifugal pump, Centrifugal fan/blower, Compressor (centrifugal), Compressor (reciprocating), Generator, Gearbox, General industrial machine | Drives ISO 20816 part/group selection |
| Nominal power | Number (kW) | > 0 | Used to confirm Part 3 applicability (> 15 kW) |
| Rated speed | Number (RPM) | 120–15,000 | Used for fault frequency calculation |
| Operating speed at measurement | Number (RPM) | 120–15,000 | May differ from rated; used for 1× frequency |
| Bearing type (drive end) | Select | Rolling element, Fluid film (journal), Magnetic, Unknown | Affects fault signature options |
| Bearing type (non-drive end) | Select | Same options | |
| Number of rotor poles (motors/generators) | Integer | Optional | Enables electrical fault frequency checks |
| Number of impeller vanes / fan blades | Integer | Optional | Enables vane pass frequency checks |
| Mounting / foundation | Select | Rigid (concrete/steel frame), Flexible (spring-isolated), Skid-mounted, Unknown | Affects zone limit group in ISO 20816-3 |
| Machine criticality | Select | Critical (no standby), Important (standby available), General purpose | Used in alarm threshold guidance |

### Section 2 — Measurement Context

| Field | Type | Options / Range | Notes |
|---|---|---|---|
| Measurement location | Select | Drive-end bearing housing, Non-drive-end bearing housing, Gearbox housing, Other structural point | |
| Measurement direction | Select | Radial – Horizontal, Radial – Vertical, Axial | ISO 20816 specifies which direction governs |
| Vibration quantity | Select | Velocity RMS (mm/s), Displacement peak-peak (µm), Acceleration RMS (m/s²) | ISO 20816-3 primarily uses velocity RMS |
| Measured value | Number | > 0 | In units matching quantity selected |
| Frequency band | Select | Broadband (10–1000 Hz), Custom range | |
| Custom band low (Hz) | Number | Optional | Only if custom range selected |
| Custom band high (Hz) | Number | Optional | Only if custom range selected |
| Measurement instrument type | Select | Handheld data collector, Online monitoring system, Temporary setup | Informational / report field |

### Section 3 — Baseline & History

| Field | Type | Notes |
|---|---|---|
| Baseline / reference value | Number (optional) | Previous known-good measurement in same quantity/location/direction |
| Baseline date | Date (optional) | For report traceability |
| Previous measurement value | Number (optional) | Most recent prior measurement for trend delta |
| Previous measurement date | Date (optional) | |
| Machine running hours since last service | Number (optional) | Context for bearing wear assessment |

### Section 4 — User-Supplied ISO Limits (copyright-safe input)

The tool prompts the user to enter the zone boundary values from their copy of ISO 20816-3 Table 1 (or equivalent) for their machine group. Pre-filled defaults are shown as placeholders labelled *"typical — verify against your standard"* and can be overridden.

| Field | Type | Notes |
|---|---|---|
| Machine group | Select | Group 1 (large machines, rigid foundation), Group 2 (large machines, flexible foundation), Group 3 (pumps, > 15 kW) | ISO 20816-3 grouping |
| Zone A/B boundary (mm/s RMS) | Number | Entered by user from their standard |
| Zone B/C boundary (mm/s RMS) | Number | |
| Zone C/D boundary (mm/s RMS) | Number | |

---

## Outputs

### Output 1 — Applicability Summary
- Confirmed applicable standard: **ISO 20816-3, [Machine Group X]**
- Measurement quantity and direction confirmed appropriate
- Any scope warnings (e.g., "power below 15 kW — Part 3 may not apply", "reciprocating machine — consider Part 6 or Part 8 instead")

### Output 2 — Zone Classification
- **Current zone**: A / B / C / D with plain-language interpretation
  - Zone A: New or recently serviced machine; normal operation
  - Zone B: Acceptable for long-term continuous operation
  - Zone C: Unsatisfactory for long-term operation; short-term operation permissible; investigate
  - Zone D: Damage risk; immediate action
- **Delta from baseline**: absolute change and % change, flagged if > 25% increase (significant change trigger)
- **Delta from previous**: trend direction indicator (stable / increasing / decreasing)
- Visual zone gauge (coloured A/B/C/D bar with needle)

### Output 3 — Fault Signature Triage

Ranked list of probable fault types based on pattern match score. Each entry includes:

| Field | Content |
|---|---|
| Rank | 1 (most likely) to N |
| Fault type | e.g., "Mass Unbalance (VDI 3839-2)" |
| Match confidence | High / Medium / Low / Possible |
| Key frequency indicators | e.g., "Dominant 1× RPM, radial direction" |
| Supporting evidence from inputs | e.g., "Horizontal > Vertical — consistent with unbalance" |
| Contra-indicators | e.g., "No axial component reported — misalignment less likely" |
| Recommended follow-up measurements | Specific actions to confirm or exclude this fault |
| Reference | VDI 3839 part number |

**Fault types included (Phase 1):**

1. **Mass Unbalance** (VDI 3839-2)
   - Dominant 1× RPM in radial direction
   - H ≈ V amplitude, low axial
   - Increases with speed (quadratic)

2. **Shaft/Coupling Misalignment** (VDI 3839-3)
   - Angular: dominant axial vibration at 1× and 2×
   - Parallel: dominant radial at 2× (sometimes 1×)
   - Phase difference 180° across coupling
   - Symptom split: angular vs parallel vs combined

3. **Mechanical Looseness** (VDI 3839-4)
   - Sub-harmonics (0.5×, 0.33×) and/or higher harmonics (3×, 4×…)
   - Phase instability
   - Sub-types: structural looseness vs rotating looseness vs bearing seat looseness

4. **Rolling Element Bearing Defect** (VDI 3839-5)
   - BPFO, BPFI, BSF, FTF frequency indicators (calculated from bearing geometry if provided)
   - High-frequency energy (acceleration) elevated
   - Impulsive content / kurtosis indicators (if spectrum data available)
   - Stage classification: early (high-freq noise floor), developing (bearing defect frequencies), advanced (sidebands + noise floor rise), severe (broadband + low-freq impact)

### Output 4 — Recommended Next Steps

Prioritised action list:
1. Immediate actions (if Zone C or D)
2. Confirmatory measurements to differentiate between ranked faults
3. Monitoring frequency recommendation based on zone and trend

### Output 5 — Evaluation Record (Printable Report)

Structured summary for documentation, including:
- Machine identification fields
- Date/time of measurement
- All entered values
- Zone result with user-supplied limits noted
- Fault triage ranking
- Next steps
- Disclaimer: *"This evaluation is based on user-supplied data and general pattern rules. Refer to ISO 20816 and VDI 3839 for authoritative limits and guidance."*

---

## Data Model

### `Machine`
```
Machine {
  id: string
  type: MachineType          // enum: motor | pump | fan | compressor_centrifugal | ...
  nominal_power_kw: float
  rated_rpm: float
  bearing_de: BearingType    // enum: rolling_element | fluid_film | magnetic | unknown
  bearing_nde: BearingType
  mounting: MountingType     // enum: rigid | flexible | skid | unknown
  criticality: Criticality   // enum: critical | important | general
  poles: int | null
  impeller_vanes: int | null
}
```

### `Measurement`
```
Measurement {
  machine_id: string
  timestamp: datetime
  location: MeasurementLocation   // enum: bearing_de | bearing_nde | gearbox | other
  direction: Direction            // enum: radial_h | radial_v | axial
  quantity: VibrationQuantity     // enum: velocity_rms | displacement_pp | accel_rms
  value: float
  units: string                   // mm/s | µm | m/s²
  freq_band_low_hz: float         // default 10
  freq_band_high_hz: float        // default 1000
  operating_rpm: float
  instrument_type: string | null
}
```

### `Baseline`
```
Baseline {
  machine_id: string
  location: MeasurementLocation
  direction: Direction
  quantity: VibrationQuantity
  value: float
  date: date
}
```

### `ISOLimits`
```
ISOLimits {
  standard: string            // "ISO 20816-3"
  machine_group: MachineGroup // enum: group_1 | group_2 | group_3
  zone_ab: float              // user-entered boundary
  zone_bc: float
  zone_cd: float
  quantity: VibrationQuantity
  entered_by_user: bool       // false = placeholder default shown only
}
```

### `ZoneResult`
```
ZoneResult {
  measurement_id: string
  applicable_standard: string
  machine_group: MachineGroup
  zone: Zone                  // enum: A | B | C | D
  value: float
  limits: ISOLimits
  delta_from_baseline: float | null      // absolute
  delta_from_baseline_pct: float | null
  delta_from_previous: float | null
  trend: TrendDirection       // enum: stable | increasing | decreasing | insufficient_data
  scope_warnings: string[]
}
```

### `FaultSignature`
```
FaultSignature {
  id: string
  fault_type: FaultType       // enum: unbalance | misalignment_angular | misalignment_parallel |
                              //        looseness_structural | looseness_rotating | bearing_defect_early |
                              //        bearing_defect_developing | bearing_defect_advanced | ...
  vdi_reference: string       // e.g. "VDI 3839-2"
  display_name: string
  primary_frequency_indicators: FrequencyIndicator[]
  direction_pattern: DirectionPattern
  bearing_type_applicability: BearingType[]   // which bearing types this fault applies to
  speed_dependency: SpeedDependency           // enum: quadratic | linear | none
  sub_harmonics: bool
  harmonics: bool
}
```

### `FrequencyIndicator`
```
FrequencyIndicator {
  multiple_of_rpm: float      // e.g. 1.0, 2.0, 0.5, or null for defect frequencies
  defect_freq_type: DefectFreqType | null   // enum: BPFO | BPFI | BSF | FTF | null
  amplitude_weight: float     // relative weight for scoring (0–1)
  direction: Direction | null // null = any
}
```

### `FaultMatchResult`
```
FaultMatchResult {
  fault_signature: FaultSignature
  rank: int
  confidence: Confidence       // enum: high | medium | low | possible
  matched_indicators: string[]
  contra_indicators: string[]
  follow_up_actions: string[]
}
```

### `EvaluationResult`
```
EvaluationResult {
  machine: Machine
  measurement: Measurement
  baseline: Baseline | null
  zone_result: ZoneResult
  fault_matches: FaultMatchResult[]    // ordered by rank
  next_steps: string[]
  generated_at: datetime
  report_text: string
}
```

---

## Fault Scoring Logic (Simplified)

Each `FaultSignature` has a scoring function that takes the `Measurement` + `Machine` as input and returns a 0–100 score:

```
score(fault, measurement, machine) =
    direction_score(fault, measurement)        * 0.35
  + frequency_indicator_score(fault, measurement) * 0.35
  + bearing_type_compatible(fault, machine)    * 0.15
  + speed_dependency_score(fault, measurement) * 0.15
```

Scores are normalised and ranked. Faults below a minimum threshold (e.g., 20) are excluded from output.

**Direction scoring:**
- Unbalance: radial_h ≈ radial_v → high score; large axial → penalty
- Angular misalignment: axial dominant → high score
- Parallel misalignment: radial_h or radial_v with 2× peak → high score
- Looseness: any direction with sub-harmonics or many harmonics → high score
- Bearing defect: elevated broadband or high-freq acceleration → high score regardless of direction

---

## UI Flow

```
[Step 1: Machine Description]
  → auto-selects ISO 20816 part and machine group
  → warns if out of scope

[Step 2: Measurement Input]
  → velocity/displacement/acceleration entry
  → operating conditions

[Step 3: ISO Limits]
  → user confirms or overrides zone boundaries
  → placeholder defaults shown with "verify against your standard" label

[Step 4: Results]
  Tab A: Zone Classification (gauge + delta)
  Tab B: Fault Triage (ranked cards with expand/collapse detail)
  Tab C: Next Steps (prioritised action list)
  Tab D: Report (printable evaluation record)
```

---

## Implementation Notes

- **Module**: `pycalcs/vibration_severity.py`
- **Key functions**:
  - `classify_zone(value, limits) → Zone`
  - `score_fault_signatures(measurement, machine, signatures) → List[FaultMatchResult]`
  - `calculate_bearing_defect_frequencies(rpm, geometry) → DefectFrequencies`
  - `generate_report(evaluation_result) → str`
- **Fault signature data**: stored as a static JSON/dict in the module (not a database); easily extensible for Phase 2 gear faults
- **No threshold tables republished**: all ISO zone boundaries are entered by user; tool stores only the user's own values for the session
- **Bearing defect frequencies**: if user provides bearing geometry (bore, OD, roller count, contact angle), BPFO/BPFI/BSF/FTF are calculated and shown as reference; otherwise fault matching falls back to high-frequency energy heuristics only
