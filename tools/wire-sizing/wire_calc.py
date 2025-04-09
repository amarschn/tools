# wire_calc.py
import math
import json # Or use built-in dicts directly

# --- Data Tables (Simplified Example - Populate with actual data) ---
# NEC 310.16 simplified Copper, 75C Insulation, 30C Ambient, <= 3 conductors in raceway
AMPACITY_TABLE_CU_75C = {
    "14 AWG": 20, "12 AWG": 25, "10 AWG": 35, "8 AWG": 50,
    "6 AWG": 65, "4 AWG": 85, "3 AWG": 100, "2 AWG": 115,
    "1 AWG": 130, "1/0 AWG": 150, "2/0 AWG": 175, "3/0 AWG": 200,
    "4/0 AWG": 230, "250 kcmil": 255, "300 kcmil": 285,
    # ... add more sizes
}
# Example Aluminum Table (Needs real data)
AMPACITY_TABLE_AL_75C = {
    "12 AWG": 20, "10 AWG": 25, "8 AWG": 40, "6 AWG": 50,
    # ... etc.
}

# NEC Table 310.15(B)(1) - Ambient Temp Correction (Based on 30°C Ambient) for 75C wire
TEMP_CORRECTION_75C = {
    (21, 25): 1.08, (26, 30): 1.00, (31, 35): 0.91, (36, 40): 0.82,
    (41, 45): 0.71, (46, 50): 0.58, (51, 55): 0.41,
    # ... add more ranges
}

# NEC Table 310.15(C)(1) - Bundling Adjustment Factors
BUNDLING_ADJUSTMENT = {
    (4, 6): 0.80, (7, 9): 0.70, (10, 20): 0.50,
    (21, 30): 0.45, (31, 40): 0.40, (41, 999): 0.35,
}

# Wire Resistance Data (Approximate Resistance in Ohms per 1000 ft at 20°C)
# Convert to Ohms per meter for calculations: R_m = R_1000ft / (1000 * 0.3048)
RESISTANCE_OHMS_PER_METER_20C = {
    "copper": {
        "14 AWG": 0.00828, "12 AWG": 0.00521, "10 AWG": 0.00328, "8 AWG": 0.00206,
        "6 AWG": 0.00130, "4 AWG": 0.000815, "2 AWG": 0.000513, "1/0 AWG": 0.000323,
        # ... add more sizes
    },
    "aluminum": {
        "12 AWG": 0.00857, "10 AWG": 0.00539, "8 AWG": 0.00339, "6 AWG": 0.00213,
         # ... add more sizes (use ~1.6x copper resistance)
    }
}

# Temperature coefficient of resistance (per °C near 20°C)
ALPHA = {"copper": 0.00393, "aluminum": 0.00403}
REFERENCE_TEMP = 20 # °C

# AWG to Area (mm²) - Approximate
AWG_TO_AREA_MM2 = {
    "14 AWG": 2.08, "12 AWG": 3.31, "10 AWG": 5.26, "8 AWG": 8.37,
    "6 AWG": 13.3, "4 AWG": 21.15, "2 AWG": 33.6, "1/0 AWG": 53.5,
    # ... add more sizes
}


# --- Helper Functions ---

def get_base_ampacity(wire_size, conductor_material, insulation_rating_c):
    """Looks up base ampacity from tables (simplified)."""
    # This needs to be more robust, selecting the right table based on all params
    # For now, just using the example 75C copper table
    if conductor_material.lower() == 'copper' and insulation_rating_c == 75:
        return AMPACITY_TABLE_CU_75C.get(wire_size, 0)
    elif conductor_material.lower() == 'aluminum' and insulation_rating_c == 75:
         return AMPACITY_TABLE_AL_75C.get(wire_size, 0)
    # TODO: Add logic for other insulation ratings (60C, 90C) and potentially Free Air
    else:
        # Placeholder - need tables for other conditions
        print(f"Warning: Ampacity table not found for {conductor_material} {insulation_rating_c}C. Using Cu 75C as fallback.")
        return AMPACITY_TABLE_CU_75C.get(wire_size, 0)


def get_temp_correction_factor(ambient_temp_c, insulation_rating_c):
    """Looks up temperature correction factor."""
    # This needs to select the right table based on insulation rating
    # Using 75C table as example
    if insulation_rating_c == 75:
        for temp_range, factor in TEMP_CORRECTION_75C.items():
            if temp_range[0] <= ambient_temp_c <= temp_range[1]:
                return factor
        return 0 # Outside table range
    else:
        # Placeholder - need tables for 60C, 90C etc.
        print(f"Warning: Temp correction table not found for {insulation_rating_c}C. Using 1.0.")
        return 1.0

def get_bundling_adjustment_factor(num_conductors):
    """Looks up bundling adjustment factor."""
    if num_conductors <= 3:
        return 1.0
    for num_range, factor in BUNDLING_ADJUSTMENT.items():
        if num_range[0] <= num_conductors <= num_range[1]:
            return factor
    return 0.35 # Default to lowest factor if very high number


def get_resistance_per_meter(wire_size, conductor_material, operating_temp_c):
    """Calculates resistance per meter at operating temperature."""
    base_resistance = RESISTANCE_OHMS_PER_METER_20C.get(conductor_material.lower(), {}).get(wire_size)
    alpha = ALPHA.get(conductor_material.lower())

    if base_resistance is None or alpha is None:
        print(f"Warning: Resistance data not found for {wire_size} {conductor_material}.")
        return None # Indicate error or missing data

    resistance = base_resistance * (1 + alpha * (operating_temp_c - REFERENCE_TEMP))
    return resistance

# --- Main Calculation Function ---

def calculate_wire_parameters(
    # === Parameters WITHOUT defaults MUST come first ===
    # Mode
    mode, # "calculate_size" or "check_size"
    # Electrical Load
    circuit_type, # "AC" or "DC"
    voltage, # V (Will be None if not provided by JS)
    current, # A (Will be None if not provided by JS)
    power,   # W (Will be None if not provided by JS)
    # Wire Properties
    conductor_material, # "copper" or "aluminum"
    insulation_rating_c, # 60, 75, 90 etc.
    wire_length_m,
    # Installation
    ambient_temp_c,

    # === Parameters WITH defaults can come after ===
    power_factor=1.0, # For AC
    check_wire_size=None, # AWG string, used in "check_size" mode
    num_bundled_conductors=3, # Default <= 3 means factor = 1.0
    installation_method="conduit" # "conduit" or "free_air"
):
    """
    Calculates required wire size or checks an existing size based on inputs.
    Returns a dictionary with results.
    """
    results = {"inputs": locals()} # Store inputs for reference
    error_messages = []

    # 0. Validate & Calculate Load Current (if needed)
    load_current = None
    if current is not None and current > 0:
        load_current = current
    elif voltage is not None and power is not None and voltage != 0:
        if circuit_type == "DC":
            load_current = power / voltage
        else: # AC
             pf = power_factor if power_factor > 0 else 1.0
             load_current = power / (voltage * pf)
    elif voltage is not None and current is not None : # V & I provided
         load_current = current # Already set
         # Calculate Power for info
         if circuit_type == "DC":
             calculated_power = voltage * current
         else:
             pf = power_factor if power_factor > 0 else 1.0
             calculated_power = voltage * current * pf
         results['calculated_power'] = calculated_power
    # Add other combinations (I&P -> V) if needed

    if load_current is None or load_current <= 0:
        error_messages.append("Invalid load definition. Provide valid V&I, V&P, or I&P.")
        results["errors"] = error_messages
        return results

    results["load_current"] = load_current

    # 1. Determine Correction Factors
    temp_factor = get_temp_correction_factor(ambient_temp_c, insulation_rating_c)
    bundling_factor = get_bundling_adjustment_factor(num_bundled_conductors)
    total_derating_factor = temp_factor * bundling_factor

    results["temp_correction_factor"] = temp_factor
    results["bundling_adjustment_factor"] = bundling_factor
    results["total_derating_factor"] = total_derating_factor

    if total_derating_factor <= 0:
         error_messages.append("Cannot calculate ampacity with zero or negative derating factor (check ambient temp or bundling).")

    # 2. Perform Calculation based on Mode

    selected_wire_size = None
    calculated_ampacity = 0
    resistance_at_op_temp = None

    if mode == "calculate_size":
        required_ampacity = load_current / total_derating_factor if total_derating_factor > 0 else float('inf')
        results["required_base_ampacity"] = required_ampacity

        # Find the smallest wire size that meets the required_ampacity
        # Iterate through available sizes (assuming sorted order, which dicts aren't guaranteed - use a sorted list)
        # EXAMPLE: Assuming AMPACITY_TABLE_CU_75C keys represent orderable sizes (needs proper sorting)
        available_sizes = list(AMPACITY_TABLE_CU_75C.keys()) # Needs refinement based on actual tables used

        suitable_wire_found = False
        for size in available_sizes: # TODO: Ensure this iterates smallest to largest AWG/kcmil
            base_amp = get_base_ampacity(size, conductor_material, insulation_rating_c)
            if base_amp >= required_ampacity:
                selected_wire_size = size
                calculated_ampacity = base_amp * total_derating_factor
                suitable_wire_found = True
                break

        if not suitable_wire_found:
            error_messages.append(f"No standard wire size found capable of handling the required base ampacity ({required_ampacity:.1f} A). Load may be too high or conditions too severe.")
        else:
            results["recommended_wire_size"] = selected_wire_size
            results["corrected_ampacity"] = calculated_ampacity

    elif mode == "check_size":
        if not check_wire_size:
            error_messages.append("No wire size provided to check.")
        else:
            selected_wire_size = check_wire_size
            base_amp = get_base_ampacity(selected_wire_size, conductor_material, insulation_rating_c)
            if base_amp == 0:
                 error_messages.append(f"Could not find base ampacity data for {selected_wire_size} {conductor_material} {insulation_rating_c}C.")
            else:
                calculated_ampacity = base_amp * total_derating_factor
                results["selected_wire_size"] = selected_wire_size
                results["corrected_ampacity"] = calculated_ampacity
                if calculated_ampacity >= load_current:
                    results["check_result"] = "PASS"
                    results["ampacity_margin_percent"] = ((calculated_ampacity - load_current) / load_current) * 100 if load_current > 0 else 0
                else:
                    results["check_result"] = "FAIL"
                    results["ampacity_shortfall_percent"] = ((load_current - calculated_ampacity) / load_current) * 100 if load_current > 0 else 0

    # 3. Calculate Voltage Drop and Power Loss (if a wire size was determined/selected)
    if selected_wire_size and not error_messages:
        # Estimate operating temp for resistance calc - use insulation rating for worst-case Vdrop at full load?
        # Or use a lower temp? Let's use insulation rating for conservative Vdrop.
        op_temp_for_res = insulation_rating_c
        r_per_meter = get_resistance_per_meter(selected_wire_size, conductor_material, op_temp_for_res)

        if r_per_meter is not None:
            total_resistance = r_per_meter * wire_length_m
            # Vdrop calculation - simplified ignoring reactance
            voltage_drop = load_current * total_resistance
            power_loss = (load_current ** 2) * total_resistance

            results["estimated_resistance_ohm"] = total_resistance
            results["voltage_drop_v"] = voltage_drop
            if voltage is not None and voltage != 0:
                 results["voltage_drop_percent"] = (voltage_drop / voltage) * 100
            results["power_loss_w"] = power_loss
        else:
             error_messages.append(f"Could not calculate resistance for {selected_wire_size}.")


    if error_messages:
        results["errors"] = error_messages

    return results


# --- Example Usage (for testing) ---
if __name__ == "__main__":
    test_result = calculate_wire_parameters(
        mode="calculate_size",
        circuit_type="DC",
        voltage=120, current=28, power=None, # Calculate P=V*I
        conductor_material="copper",
        insulation_rating_c=75,
        wire_length_m=30, # ~100 ft
        ambient_temp_c=40,
        num_bundled_conductors=5,
        installation_method="conduit"
    )
    print("--- Calculate Size Example ---")
    print(json.dumps(test_result, indent=2))

    test_result_check = calculate_wire_parameters(
        mode="check_size",
        check_wire_size="10 AWG", # Check if 10 AWG is okay
        circuit_type="DC",
        voltage=120, current=28, power=None,
        conductor_material="copper",
        insulation_rating_c=75,
        wire_length_m=30,
        ambient_temp_c=40,
        num_bundled_conductors=5,
        installation_method="conduit"
    )
    print("\n--- Check Size Example ---")
    print(json.dumps(test_result_check, indent=2))