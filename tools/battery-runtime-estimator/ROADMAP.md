# Battery Runtime Estimator - Feature Roadmap

This document captures planned improvements for future implementation sessions.

## Phase 1: Visualization (High Impact)

### 1.1 Discharge Curve Visualization
**Priority:** High
**Effort:** Medium

Add an interactive SVG or Canvas chart showing voltage vs. time (or vs. capacity consumed).

**Implementation notes:**
- Use simple SVG polylines (no external charting library needed for basic curves)
- X-axis: Time (0 to runtime) or Capacity (0 to effective capacity)
- Y-axis: Voltage (cutoff to nominal)
- Show horizontal line at cutoff voltage
- Approximate curve shape based on chemistry (LiFePO4 = flat plateau, Li-ion = gradual slope, Lead-acid = linear)
- Could use lookup tables or polynomial fits for each chemistry
- Add hover/touch to show values at any point

**Data needed:**
- Already have: nominal voltage, cutoff voltage, runtime, chemistry
- Need to add: discharge curve coefficients per chemistry (or use typical normalized curves)

**Files to modify:**
- `index.html`: Add chart container, SVG rendering functions
- `batteries.py`: Optionally add curve point generation, or do it client-side

### 1.2 Comparison Mode
**Priority:** High
**Effort:** Medium-High

Allow side-by-side comparison of two battery configurations.

**Implementation notes:**
- Add "Compare" tab or toggle button
- Show two input columns (Config A, Config B)
- Results displayed in comparison table with delta/percentage difference
- Highlight which config is better for each metric
- Could also overlay discharge curves on same chart

**UI approach:**
- Duplicate input form or use tabbed A/B inputs
- Results table: Metric | Config A | Config B | Difference

## Phase 2: Practical Enhancements

### 2.1 Commercial Cell Presets
**Priority:** Medium-High
**Effort:** Low

Add dropdown with real cell models and their datasheet specs.

**Implementation notes:**
- Add to CHEMISTRY_DEFAULTS or create CELL_PRESETS object
- Include: model name, nominal voltage, capacity, internal resistance, max continuous discharge, weight, dimensions

**Suggested cells to include:**
```javascript
CELL_PRESETS = {
    // High Energy 18650
    'panasonic_ncr18650b': { name: 'Panasonic NCR18650B', voltage: 3.6, capacity: 3.4, resistance: 0.045, maxC: 2, weight: 47.5, diameter: 18.5, length: 65.3 },
    'samsung_35e': { name: 'Samsung 35E', voltage: 3.6, capacity: 3.5, resistance: 0.040, maxC: 2, weight: 50, diameter: 18.5, length: 65.2 },
    'lg_mj1': { name: 'LG MJ1', voltage: 3.635, capacity: 3.5, resistance: 0.040, maxC: 2, weight: 49, diameter: 18.4, length: 65.1 },

    // High Power 18650
    'samsung_25r': { name: 'Samsung 25R', voltage: 3.6, capacity: 2.5, resistance: 0.020, maxC: 8, weight: 45, diameter: 18.3, length: 64.9 },
    'sony_vtc6': { name: 'Sony VTC6', voltage: 3.6, capacity: 3.0, resistance: 0.015, maxC: 10, weight: 46.5, diameter: 18.4, length: 65.2 },
    'molicel_p28a': { name: 'Molicel P28A', voltage: 3.6, capacity: 2.8, resistance: 0.018, maxC: 12, weight: 46, diameter: 18.5, length: 65.1 },

    // 21700 format
    'samsung_50e': { name: 'Samsung 50E', voltage: 3.6, capacity: 5.0, resistance: 0.025, maxC: 2, weight: 68.9, diameter: 21.1, length: 70.2 },
    'molicel_p42a': { name: 'Molicel P42A', voltage: 3.6, capacity: 4.2, resistance: 0.018, maxC: 10, weight: 70, diameter: 21.4, length: 70.2 },

    // LiFePO4
    'headway_38120': { name: 'Headway 38120S', voltage: 3.2, capacity: 10, resistance: 0.006, maxC: 3, weight: 330, diameter: 38, length: 120 },

    // Lead-acid (per cell equivalent)
    'generic_agm': { name: 'Generic AGM (per 2V cell)', voltage: 2.0, capacity: 100, resistance: 0.002, maxC: 0.5, weight: 3000 }
}
```

### 2.2 Thermal Rise Estimation
**Priority:** Medium
**Effort:** Medium

Estimate battery temperature increase during discharge.

**Implementation notes:**
- Add inputs: ambient temp (already have), thermal mass (J/K or Wh/K), thermal resistance to ambient (K/W)
- Calculate: steady-state temp rise = P_loss * R_thermal
- Calculate: transient temp rise over runtime using thermal mass
- Add output: estimated max temperature, temperature at end of discharge
- Add warning if temp exceeds safe limits (typically 60C for Li-ion)

**Equations:**
```
T_rise_steady = P_loss * R_thermal_to_ambient
T_rise_transient = P_loss * runtime / thermal_mass  (simplified)
T_final = T_ambient + T_rise
```

**Typical values to document:**
- 18650 cell thermal mass: ~40 J/K
- Natural convection R_thermal: ~20-40 K/W per cell
- Forced air: ~5-10 K/W per cell

### 2.3 Multi-Stage Load Profiles
**Priority:** Medium
**Effort:** High

Support time-varying load profiles instead of single constant load.

**Implementation notes:**
- Add UI for defining load stages: [{power: 10, duration: 3600}, {power: 50, duration: 1800}, ...]
- Calculate capacity consumed per stage considering Peukert at each stage's current
- Sum stages until capacity exhausted or all stages complete
- Show which stage battery dies in (if applicable)

**UI approach:**
- Simple: Add 2-3 predefined stage inputs (Stage 1 power/duration, Stage 2, etc.)
- Advanced: Dynamic list with add/remove buttons
- Could also support CSV import of load profile

**Calculation approach:**
- For each stage: calculate current, apply Peukert, subtract from remaining capacity
- Track cumulative time
- Stop when capacity exhausted

## Phase 3: Design-Oriented Features

### 3.1 Cycle Life Estimation
**Priority:** Medium
**Effort:** Medium

Predict battery lifespan based on usage parameters.

**Implementation notes:**
- Cycle life depends on: DoD, C-rate, temperature, chemistry
- Use empirical curves/formulas from literature
- Rainflow counting for variable DoD (simplified: use average DoD)

**Typical cycle life models:**
```
Li-ion (simplified): cycles = base_cycles * DoD_factor * temp_factor * crate_factor
- base_cycles: 500-1000 (chemistry dependent)
- DoD_factor: ~1.5 at 80% DoD, ~1.0 at 100% DoD, ~3-4 at 50% DoD
- temp_factor: 1.0 at 25C, 0.5 at 45C, varies
- crate_factor: 1.0 at 1C, ~0.8 at 2C, varies

LiFePO4: Much higher base (2000-5000), less DoD sensitive
Lead-acid: Very DoD sensitive, 200-500 base cycles
```

**Outputs:**
- Estimated cycle life (cycles)
- Total lifetime energy throughput (kWh)
- If daily cycles known: estimated years of service

### 3.2 Energy Density Calculations
**Priority:** Low-Medium
**Effort:** Low

Calculate gravimetric and volumetric energy density.

**Implementation notes:**
- Add inputs: cell weight (g), cell dimensions or volume (cm³)
- Or: pack weight (kg), pack volume (L)
- Calculate: Wh/kg (gravimetric), Wh/L (volumetric)

**Pack-level calculation:**
```
pack_weight = n_cells * cell_weight + overhead_weight
pack_volume = n_cells * cell_volume * packing_factor + overhead_volume
energy_density_gravimetric = energy_delivered_wh / pack_weight
energy_density_volumetric = energy_delivered_wh / pack_volume
```

**Typical packing factors:**
- Cylindrical cells: 0.65-0.75 (hexagonal packing)
- Prismatic cells: 0.80-0.90
- Pouch cells: 0.85-0.95

### 3.3 Input Validation Warnings
**Priority:** Low-Medium
**Effort:** Low

Warn users when inputs are outside typical ranges.

**Implementation notes:**
- Add validation rules per parameter
- Show yellow warning badge next to input
- Add tooltip explaining the concern
- Don't block calculation, just warn

**Validation rules:**
```javascript
VALIDATION_RULES = {
    peukert_exponent: { min: 1.0, max: 1.5, warnMax: 1.3, msg: 'Peukert > 1.3 is unusual except for lead-acid' },
    cell_internal_resistance_ohm: { warnMin: 0.005, warnMax: 0.1, msg: 'Typical range is 5-100 mOhm' },
    converter_efficiency: { min: 0.5, max: 1.0, warnMin: 0.7, msg: 'Efficiency below 70% is poor' },
    c_rate_output: { warnMax: 3.0, msg: 'C-rate > 3C may exceed cell limits' },
    depth_of_discharge: { warnMax: 0.9, msg: 'DoD > 90% significantly reduces cycle life' },
    // etc.
}
```

## Phase 4: Nice-to-Have

### 4.1 Export/Save Functionality
- Save configuration to localStorage
- Export results to PDF or CSV
- Share configuration via URL parameters

### 4.2 BMS Overhead
- Add quiescent current input for BMS
- Subtract from runtime calculation
- More significant for low-power/long-duration applications

### 4.3 Self-Discharge Modeling
- Add self-discharge rate per chemistry
- Calculate capacity loss over storage/idle time
- Relevant for backup power, seasonal equipment

### 4.4 Charging Time Estimation
- Given charger current/power, estimate charge time
- Account for CC/CV phases
- Show charge curve alongside discharge curve

## Implementation Priority Summary

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Discharge curve visualization | High | Medium | 1 |
| Commercial cell presets | High | Low | 2 |
| Input validation warnings | Medium | Low | 3 |
| Comparison mode | High | Medium-High | 4 |
| Thermal rise estimation | Medium | Medium | 5 |
| Energy density calculations | Medium | Low | 6 |
| Cycle life estimation | Medium | Medium | 7 |
| Multi-stage load profiles | Medium | High | 8 |

## Notes for Future Sessions

- The tool uses Pyodide to run Python in the browser
- Core calculation is in `pycalcs/batteries.py`
- UI is self-contained in `index.html` with inline CSS/JS
- Follow patterns in DESIGN.md for UI consistency
- Test Python changes with `python -c "from pycalcs.batteries import ..."` before browser testing
- Browser may cache Python files - use hard refresh (Cmd+Shift+R) when testing changes
