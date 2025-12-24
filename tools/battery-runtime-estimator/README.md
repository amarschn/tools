# Battery Runtime Estimator

## Purpose

Estimate battery runtime with a configurable load model and practical corrections. The tool combines pack or cell-level specifications with internal resistance, Peukert effects, temperature impacts, and duty-cycle loading to deliver transparent, repeatable runtime estimates.

This estimator is designed for preliminary sizing, feasibility studies, and comparative analysis between battery chemistries or configurations. For detailed design validation, always verify results against manufacturer discharge curves and empirical testing.

## Key Features

- Multiple load types: Constant current, constant power, and constant resistance
- Cell-to-pack aggregation: Derive pack parameters from individual cell specs
- Temperature correction: Adjust capacity based on ambient temperature
- Peukert effect: Model capacity reduction at high discharge rates
- Degradation modeling: Account for state-of-health and depth-of-discharge
- Thermal analysis: Calculate heat dissipation for thermal management planning
- Transparent equations: View the mathematical model with substituted values

## How It Works

The estimator uses a constant nominal open-circuit voltage with a lumped internal resistance to approximate loaded terminal voltage. Capacity is adjusted for temperature, usable depth-of-discharge, state-of-health, and Peukert derating.

### Core Equations

- Loaded Voltage: V_load = V_pack - I_load * R_pack
- Temperature Capacity: C_temp = C_rated * [1 + alpha * (T - T_ref)]
- Usable Capacity: C_usable = C_temp * SOH * DoD
- Peukert Capacity: C_eff = C_usable * (I_ref / I_avg)^(k-1)
- Runtime: t = C_eff / I_avg
- Heat Dissipation: P_loss = I_load^2 * R_pack

## Inputs

### Pack Configuration
- Chemistry Preset - Selects default values for common chemistries
- Pack Nominal Voltage (V) - Average voltage during discharge
- Pack Capacity (Ah) - Rated capacity at standard discharge rate
- Pack Internal Resistance (Ohm) - Lumped DC resistance
- Pack Cutoff Voltage (V) - Minimum safe discharge voltage

### Cell Configuration
- Series Cells (Ns) - Number of cells in series (scales voltage)
- Parallel Cells (Np) - Number in parallel (scales capacity)
- Cell Nominal Voltage (V) - Per-cell nominal voltage
- Cell Capacity (Ah) - Per-cell rated capacity
- Cell Internal Resistance (Ohm) - Per-cell resistance
- Cell Cutoff Voltage (V) - Per-cell minimum voltage

### Load Parameters
- Load Type - Constant current, power, or resistance
- Load Current (A) - For constant current mode
- Load Power (W) - For constant power mode
- Load Resistance (Ohm) - For constant resistance mode
- Converter Efficiency (0-1) - Power conversion efficiency
- Duty Cycle (0-1) - Fraction of time load is active

### Environment and Degradation
- Ambient Temperature (C) - Operating temperature
- Reference Temperature (C) - Temperature for rated capacity
- Capacity Temp Coefficient (1/C) - Capacity change per degree
- Peukert Exponent (k >= 1) - Rate-dependent capacity factor
- Reference Current (A) - Current for rated capacity
- Depth of Discharge (0-1) - Fraction of capacity to use
- State of Health (0-1) - Remaining capacity fraction

## Outputs

- Runtime (hours, minutes) - Estimated operating time
- Effective Capacity (Ah) - Capacity after all adjustments
- Average Current (A) - Time-averaged battery current
- Average Power (W) - Power at loaded voltage
- Energy Delivered (Wh) - Total usable energy
- Loaded Voltage (V) - Terminal voltage under load
- Voltage Sag (V) - IR drop across internal resistance
- C-rate (1/h) - Discharge rate relative to capacity
- Heat Dissipation (W) - Power lost as heat (I^2 * R)

## Performance Indicators

The tool provides visual gauges for key metrics:

- C-rate severity - High C-rates reduce effective capacity and stress cells
- Voltage sag ratio - Excessive sag indicates power delivery issues
- Cutoff margin - Ensures loaded voltage stays above cutoff

## Chemistry Comparison

### Li-ion NMC/NCA
- Nominal: 3.6-3.7V, Cutoff: 3.0V, Peukert k: 1.02-1.05
- Best for: EVs, laptops, power tools
- High energy density (150-250 Wh/kg)

### LiPo (Lithium Polymer)
- Nominal: 3.7V, Cutoff: 3.2V, Peukert k: 1.02-1.04
- Best for: Drones, RC vehicles, high-power applications
- Supports high discharge rates (3-10C)

### LiFePO4 (Lithium Iron Phosphate)
- Nominal: 3.2V, Cutoff: 2.5V, Peukert k: 1.03-1.06
- Best for: Solar storage, EVs, safety-critical applications
- Excellent cycle life (2000-5000 cycles)

### NiMH (Nickel Metal Hydride)
- Nominal: 1.2V, Cutoff: 1.0V, Peukert k: 1.05-1.15
- Best for: Hybrid vehicles, consumer electronics
- Higher self-discharge than lithium

### Lead-Acid
- Nominal: 2.0V, Cutoff: 1.75V, Peukert k: 1.10-1.30
- Best for: UPS, automotive starting, low-cost storage
- Strong Peukert effect at high discharge rates

## Assumptions and Limitations

- Uses constant nominal voltage (no dynamic discharge curve)
- Internal resistance is constant (doesn't vary with SOC or temperature)
- Temperature effects are linear around reference
- All cells assumed identical and balanced
- No transient or recovery modeling
- Duty cycle averaging approximates intermittent loads

## Thermal Considerations

The Heat Dissipation output shows power lost as heat in internal resistance. Use this to assess thermal management needs:

- Less than 5% of output power: Passive cooling likely sufficient
- 5-10% of output power: Consider heat sinking or airflow
- Greater than 10%: Active cooling may be required

Higher discharge rates and higher internal resistance increase heat generation. Consider using lower-resistance cells or adding parallel strings for high-power applications.

## References

### Textbooks
- D. Linden, T. B. Reddy, Handbook of Batteries, 4th ed., McGraw-Hill, 2011
- H. A. Kiehne, Battery Technology Handbook, 2nd ed., CRC Press, 2003
- M. Yoshio et al., Lithium-Ion Batteries: Science and Technologies, Springer, 2009

### Online Resources
- Battery University (batteryuniversity.com) - Educational resource
- Battery Archive (batteryarchive.org) - Real cell test data
- NREL Battery Research - Thermal testing data

### Standards
- UN 38.3 - Transport testing for lithium batteries
- IEC 62133 - Safety requirements for portable cells
- UL 2054, UL 2271, UL 1973 - Battery safety standards

## Usage Tips

- Start with a chemistry preset to get reasonable defaults
- Replace defaults with manufacturer datasheet values for accuracy
- Use conservative temperature and SOH values for critical applications
- Check performance gauges (C-rate, sag, margin) for feasibility
- Iterate on series/parallel configuration to meet runtime needs
- Review heat dissipation to plan thermal management
