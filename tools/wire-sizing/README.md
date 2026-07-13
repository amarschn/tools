# Wire Sizing Calculator (Ampacity & Voltage Drop)

A web-based tool for estimating appropriate wire sizes based on electrical load, installation conditions, and safety standards.

## Purpose

This calculator helps determine:
- **Required Wire Size:** The minimum conductor gauge (AWG or mm²) needed to safely carry a given current without overheating, according to standard ampacity tables (e.g., NEC-based or simplified IEC).
- **Voltage Drop:** The expected voltage loss along the length of the selected wire.
- **Suitability Check:** Whether a *chosen* wire size is adequate for the specified load and conditions.

It aids in preliminary electrical design and component selection.

**IMPORTANT:** This tool provides estimates based on standard tables and calculations. **Always consult relevant local electrical codes (like the NEC in the US, or applicable IEC standards), manufacturer specifications, and a qualified professional for final design and installation.** Safety factors and specific application nuances may not be fully captured here.

## Features

- Supports two calculation modes:
    - **Calculate Minimum Wire Size:** Determines the required gauge based on load and conditions.
    - **Check Existing Wire Size:** Evaluates if a user-specified gauge is suitable.
- Handles AC (single-phase) and DC circuits.
- Allows input via Voltage/Current, Voltage/Power, or Current/Power.
- Considers key factors affecting ampacity:
    - Conductor material (Copper, Aluminum)
    - Insulation temperature rating (e.g., 60°C, 75°C, 90°C)
    - Ambient temperature
    - Installation method (Free Air, Conduit)
    - Bundling/Grouping of multiple conductors
- Calculates expected voltage drop and power loss in the wire.
- Uses data derived from standard ampacity tables (e.g., simplified NEC Table 310.16 / IEC 60364-5-52).

## Usage Instructions

1.  **Select Mode:** Choose "Calculate Minimum Wire Size" or "Check Existing Wire Size".
2.  **Input Electrical Parameters:**
    *   Select AC or DC.
    *   Choose how to define the load (V & I, V & P, I & P) and enter the known values.
    *   If AC, enter Frequency (optional, for future reactance) and Power Factor.
3.  **Input Operational & Installation Parameters:**
    *   Enter the length of the wire run.
    *   Select Conductor Material (Copper/Aluminum).
    *   Select the Insulation Temperature Rating.
    *   Enter the maximum Ambient Temperature.
    *   Specify the Installation Method (e.g., Free Air, In Conduit).
    *   If applicable, enter the number of current-carrying conductors bundled together.
    *   *(If in "Check Mode"):* Select the Wire Gauge (AWG or mm²) to check.
4.  **Calculate Results:**
    *   Click "Calculate".
    *   *Calculate Mode:* View the recommended minimum wire size, its corrected ampacity, estimated voltage drop, and power loss.
    *   *Check Mode:* View the corrected ampacity of the selected wire, whether it meets the requirement (Pass/Fail), estimated voltage drop, and power loss.

## Calculation Approach

- **Ampacity:**
    - Base ampacity values for different wire sizes, conductor materials, and insulation ratings are retrieved from internal tables (derived from standards like NEC 310.16).
    - Correction factors are applied for:
        - Ambient temperature deviating from the table's base temperature.
        - Bundling/grouping of multiple current-carrying conductors (adjustment factors from NEC 310.15(C)(1)).
    - The *corrected ampacity* must be greater than or equal to the required load current.
- **Resistance:** Calculated using `R = ρ * (1 + α * (T_op - T_ref)) * Length / Area`, where ρ is resistivity, α is the temperature coefficient, and T_op is the estimated operating temperature (often approximated as the insulation rating for worst-case ampacity calculation, or calculated iteratively for voltage drop). Cross-sectional areas for AWG/mm² sizes are stored internally.
- **Voltage Drop:** `V_drop = Current * Resistance` (for DC or AC with PF=1). For AC with PF<1, `V_drop ≈ Current * R * PF` is a simple approximation, ignoring reactance for basic cases. A more precise calculation `V_drop = I * Z = I * sqrt(R² + X²)` where X is reactance might be added later.
- **Power Loss:** `P_loss = Current² * Resistance`.
- **Load Calculation:** Calculates the missing V, I, or P based on the two provided inputs (P=VI for DC, P=VI*PF for AC single phase).

## Limitations

- **Standard Reliance:** Primarily based on simplified data derived from NEC or similar standards. Specific conditions or newer standards might differ.
- **Reactance:** Basic calculations may ignore AC inductive reactance, which can be significant for larger wires or higher frequencies.
*   **Transient/Duty Cycle:** This version focuses on steady-state operation. Ampacity for pulsed loads or short-duration events requires different analysis (e.g., considering thermal mass, I²t limits) not included here.
- **Termination Temperature:** Assumes termination ratings match or exceed wire insulation rating (per NEC 110.14(C)).
- **Complex Installations:** Does not cover highly specific installation scenarios (e.g., direct burial depth variations, conduit fill complexities beyond simple bundling).
- **Not a Code Compliance Tool:** This is an estimation tool. Final design MUST comply with all applicable codes and regulations.

## Technical Implementation

- Frontend: HTML, CSS, JavaScript
- Calculation Logic: Python (via Pyodide)
- Data: Internal Python dictionaries/lists for ampacity tables, material properties, derating factors.