# thermal_calc.py
import math
import sys # Needed for float_info.epsilon

# --- Core Heat Transfer Functions (Unchanged) ---

def conduction_heat_transfer(k, A, T_hot, T_cold, L):
    """
    Calculate heat transfer through conduction (Not used in lumped model directly,
    but kept for potential future use or reference).

    Parameters:
    - k: Thermal conductivity (W/m·K)
    - A: Cross-sectional area (m²)
    - T_hot: Hot side temperature (°C)
    - T_cold: Cold side temperature (°C)
    - L: Material thickness (m)

    Returns:
    - Heat transfer rate (W)
    """
    if L <= 0:
        return float('inf') # Avoid division by zero, indicate infinite conductance
    return k * A * (T_hot - T_cold) / L

def natural_convection_coefficient(surface_type, char_length, T_surface, T_ambient, orientation='vertical'):
    """
    Estimate natural convection heat transfer coefficient.

    Parameters:
    - surface_type: 'plate', 'cylinder', etc.
    - char_length: Characteristic length (m)
    - T_surface: Surface temperature (°C)
    - T_ambient: Ambient temperature (°C)
    - orientation: 'vertical', 'horizontal_up', 'horizontal_down'

    Returns:
    - Estimated heat transfer coefficient (W/m²·K)
    """
    # Prevent calculations if temps are identical (causes division by zero in Ra)
    if abs(T_surface - T_ambient) < sys.float_info.epsilon:
        return 2.0 # Return minimum value if no temp difference

    # Convert temperatures to Kelvin for property calculations
    T_surface_K = T_surface + 273.15
    T_ambient_K = T_ambient + 273.15
    T_film = (T_surface_K + T_ambient_K) / 2  # Film temperature

    # Properties of air at film temperature (approximated for typical ranges)
    beta = 1 / T_film  # Thermal expansion coefficient (1/K)
    # Kinematic viscosity (m²/s) approximated as function of temperature
    nu = 1.46e-5 * (T_film/293.15)**1.75 # Adjusted exponent for better fit
    # Thermal diffusivity (m²/s) approximated as function of temperature
    alpha = 2.0e-5 * (T_film/293.15)**1.75 # Adjusted exponent
    # Prandtl number (dimensionless) - relatively constant for air
    Pr = 0.71
    # Thermal conductivity of air (W/m·K)
    k_air = 0.0257 * (T_film/293.15)**0.85 # Adjusted exponent

    # Calculate Rayleigh number
    g = 9.81  # Gravity (m/s²)
    delta_T = abs(T_surface - T_ambient)
    # Avoid division by zero if nu or alpha become extremely small (unlikely)
    if nu * alpha == 0:
        return 2.0 # Failsafe
    Ra = (g * beta * delta_T * char_length**3) / (nu * alpha)

    # Calculate Nusselt number based on surface type and orientation
    Nu = 0

    if surface_type == 'plate':
        if orientation == 'vertical':
            # Churchill and Chu correlation (valid for all Ra)
            term1 = 0.825
            term2 = 0.387 * Ra**(1/6)
            term3 = (1 + (0.492/Pr)**(9/16))**(8/27)
            Nu_laminar_turbulent = (term1 + term2 / term3)**2
            # Laminar only part (simplified for comparison, not used in final calc)
            # Nu_laminar = 0.68 + 0.67 * Ra**0.25 / (1 + (0.492/Pr)**(9/16))**(4/9) if Ra < 1e9 else 0
            Nu = Nu_laminar_turbulent # Use the combined form

        elif orientation == 'horizontal_up' and T_surface > T_ambient: # Hot surface facing up
             if Ra < 1e7: Nu = 0.54 * Ra**0.25 # Laminar
             else: Nu = 0.15 * Ra**(1/3) # Turbulent
        elif orientation == 'horizontal_down' and T_surface > T_ambient: # Hot surface facing down
             # Generally lower heat transfer
             Nu = 0.27 * Ra**0.25 # Primarily laminar boundary layer
        elif orientation == 'horizontal_up' and T_surface < T_ambient: # Cold surface facing up
             Nu = 0.27 * Ra**0.25
        elif orientation == 'horizontal_down' and T_surface < T_ambient: # Cold surface facing down
             if Ra < 1e7: Nu = 0.54 * Ra**0.25
             else: Nu = 0.15 * Ra**(1/3)

    elif surface_type == 'cylinder':
        # For horizontal cylinders (Churchill and Chu)
        term1 = 0.60
        term2 = 0.387 * Ra**(1/6)
        term3 = (1 + (0.559/Pr)**(9/16))**(8/27)
        Nu = (term1 + term2 / term3)**2

    # Calculate heat transfer coefficient
    if char_length <= 0 or k_air <= 0: return 2.0 # Failsafe
    h = Nu * k_air / char_length

    # Ensure minimum value for natural convection
    return max(h, 2.0)


def forced_convection_coefficient(surface_type, char_length, velocity, T_surface, T_ambient):
    """
    Estimate forced convection heat transfer coefficient.

    Parameters:
    - surface_type: 'plate', 'cylinder'
    - char_length: Characteristic length (m) (use length in flow direction for plate)
    - velocity: Fluid velocity (m/s)
    - T_surface: Surface temperature (°C)
    - T_ambient: Ambient temperature (°C)

    Returns:
    - Estimated heat transfer coefficient (W/m²·K)
    """
    # Convert temperatures to Kelvin for property calculations
    T_surface_K = T_surface + 273.15
    T_ambient_K = T_ambient + 273.15
    T_film = (T_surface_K + T_ambient_K) / 2  # Film temperature

    # Air properties at film temperature (simplified approximations)
    # Kinematic viscosity (m²/s)
    nu = 1.46e-5 * (T_film/293.15)**1.75
    # Thermal conductivity of air (W/m·K)
    k_air = 0.0257 * (T_film/293.15)**0.85
    # Prandtl number (dimensionless)
    Pr = 0.71

    # Calculate Reynolds number
    if nu <= 0: return 5.0 # Failsafe
    Re = velocity * char_length / nu

    # Calculate Nusselt number based on surface type and flow regime
    Nu = 0

    if surface_type == 'plate':
        # Using correlations for average Nu over the plate length (char_length)
        if Re < 5e5:  # Laminar flow
            Nu = 0.664 * Re**0.5 * Pr**(1/3)
        else:  # Turbulent flow (mixed boundary layer)
            # Correlation accounts for initial laminar section
            Nu = (0.037 * Re**0.8 - 871) * Pr**(1/3)
            # Ensure Nu is positive, turbulent correlations can be negative for low Re > Re_crit
            Nu = max(Nu, 0.664 * (5e5)**0.5 * Pr**(1/3)) # Fallback to end of laminar if needed

    elif surface_type == 'cylinder':
         # Using Zukauskas correlation (more accurate across wider Re range)
        C, m = 0, 0
        Re_ranges = {
            (1, 40): (0.75, 0.4),
            (40, 1000): (0.51, 0.5),
            (1000, 2e5): (0.26, 0.6),
            (2e5, 1e6): (0.076, 0.7)
        }
        for r, params in Re_ranges.items():
            if r[0] <= Re < r[1]:
                C, m = params
                break
        if C == 0 and Re >= 1e6: # Handle highest range if not caught
             C, m = (0.076, 0.7) # Extrapolate last range or find better correlation if needed

        if C > 0:
            # Pr_s is Pr evaluated at T_surface, approximating Pr/Pr_s ^ 0.25 as ~1 for air
            Nu = C * Re**m * Pr**(0.37) # Simplified Pr exponent
        else:
            # Fallback for very low Re if needed (e.g., Whitaker correlation part)
            Nu = 0.3 + (0.62 * Re**0.5 * Pr**(1/3)) / (1 + (0.4/Pr)**(2/3))**0.25 # Simplified, check validity


    # Calculate heat transfer coefficient
    if char_length <= 0 or k_air <= 0: return 5.0 # Failsafe
    h = Nu * k_air / char_length

    # Ensure minimum value often observed for forced convection
    return max(h, 5.0)


def convection_heat_transfer(h, A, T_surface, T_ambient):
    """Calculate heat transfer through convection."""
    return h * A * (T_surface - T_ambient)

def radiation_heat_transfer(emissivity, A, T_surface, T_ambient):
    """Calculate heat transfer through radiation."""
    T_surface_K = T_surface + 273.15
    T_ambient_K = T_ambient + 273.15
    sigma = 5.67e-8 # Stefan-Boltzmann constant (W/m²·K⁴)
    return emissivity * sigma * A * (T_surface_K**4 - T_ambient_K**4)

# --- Helper to get Geometry Info ---
def _get_geometry_details(geometry_type, dimensions, orientation):
    """ Helper to calculate area, volume, characteristic lengths. """
    details = {}
    if geometry_type == 'plate':
        length = dimensions['length']
        width = dimensions['width']
        thickness = dimensions['thickness']

        area_faces = 2 * (length * width)
        area_edges = 2 * (length * thickness + width * thickness)
        details['total_area'] = area_faces + area_edges
        details['volume'] = length * width * thickness

        # Characteristic length depends on mode and orientation
        # For natural convection: Use height for vertical, Lc = A/P for horizontal? Use width as approx.
        # For forced convection: Use length in direction of flow (assume along 'length' dimension)
        details['char_length_natural'] = length if orientation == 'vertical' else width # Simplification
        details['char_length_forced'] = length # Assume flow along length

    elif geometry_type == 'cylinder':
        diameter = dimensions['diameter']
        length = dimensions['length']
        radius = diameter / 2

        area_curved = math.pi * diameter * length
        area_ends = 2 * (math.pi * radius**2)
        details['total_area'] = area_curved + area_ends
        details['volume'] = math.pi * radius**2 * length

        # Characteristic length is typically diameter for both natural and forced convection over cylinder
        details['char_length_natural'] = diameter
        details['char_length_forced'] = diameter
    else:
        raise ValueError(f"Unsupported geometry type: {geometry_type}")

    return details

# --- Transient Cooling Calculation ---

def calculate_transient_cooling(
    geometry,
    dimensions,
    material_properties,
    thermal_conditions,
    time_steps=100,
    total_time=3600
):
    """
    Calculate temperature change over time for an object cooling down.
    Uses Lumped Capacitance Method.
    """
    geometry_type = geometry['type']
    orientation = geometry.get('orientation', 'vertical')

    # Get geometric properties
    geo_details = _get_geometry_details(geometry_type, dimensions, orientation)
    total_area = geo_details['total_area']
    volume = geo_details['volume']
    # Use appropriate char length based on convection type later
    char_length_natural = geo_details['char_length_natural']
    char_length_forced = geo_details['char_length_forced']


    # Material properties
    rho = material_properties['density']
    c_p = material_properties['specific_heat']
    emissivity = material_properties.get('emissivity', 0.9)

    # Thermal conditions
    T_initial = thermal_conditions['initial_temp']
    T_ambient = thermal_conditions['ambient_temp']
    air_velocity = thermal_conditions.get('air_velocity', 0)

    # Time parameters
    dt = total_time / time_steps

    # Initial state
    T_current = T_initial
    time_points = [0]
    temp_points = [T_initial]
    heat_rate_points = [0] # Initial net heat rate (will be calculated in first step)
    convection_coeffs = [] # Store h at each step

    # Check for zero volume or density/Cp
    if volume <= 0 or rho <= 0 or c_p <= 0:
        print("Warning: Zero or negative volume/density/specific heat. Cannot simulate.")
        # Return initial state or raise error? Let's return initial state.
        return {
            "time_points": time_points, "temp_points": temp_points,
            "heat_rate_points": heat_rate_points, "convection_coeffs": [],
            "convection_type": "N/A", "time_constant": None,
            "time_to_equilibrium": None, "final_temp": T_initial,
            "final_delta_t": 0, "total_area": total_area, "volume": volume
        }

    thermal_mass = rho * volume * c_p
    if thermal_mass <= 0:
         print("Warning: Zero or negative thermal mass. Cannot simulate.")
         # Handle as above
         # ... (similar return block)

    convection_type = "natural" if air_velocity <= 0.1 else "forced"

    # Simulation loop
    for step in range(1, time_steps + 1):
        # Determine convection coefficient 'h' and characteristic length 'L_c' for this step
        if convection_type == "natural":
            L_c = char_length_natural
            h = natural_convection_coefficient(
                geometry_type, L_c, T_current, T_ambient, orientation
            )
        else: # Forced
            L_c = char_length_forced
            h = forced_convection_coefficient(
                geometry_type, L_c, air_velocity, T_current, T_ambient
            )
        convection_coeffs.append(h)

        # Calculate heat transfer rates
        q_conv = convection_heat_transfer(h, total_area, T_current, T_ambient)
        q_rad = radiation_heat_transfer(emissivity, total_area, T_current, T_ambient)
        q_total_loss = q_conv + q_rad # Positive value represents heat LEAVING the object

        # Update temperature using lumped capacitance method: dT = - (q_loss / thermal_mass) * dt
        delta_T = - (q_total_loss / thermal_mass) * dt
        T_current += delta_T

        # Avoid temperature going below ambient (or oscillating around it due to numerical steps)
        if (T_initial > T_ambient and T_current < T_ambient) or \
           (T_initial < T_ambient and T_current > T_ambient):
             T_current = T_ambient
             # Recalculate final q_loss if temp is clamped to ambient
             q_conv = convection_heat_transfer(h, total_area, T_current, T_ambient)
             q_rad = radiation_heat_transfer(emissivity, total_area, T_current, T_ambient)
             q_total_loss = q_conv + q_rad


        # Store results for this step
        time_points.append(step * dt)
        temp_points.append(T_current)
        heat_rate_points.append(q_total_loss) # Store heat loss rate


    # --- Post-processing: Time Constant Estimation ---
    tau_time = None
    if T_initial != T_ambient:
        temp_diff_initial = abs(T_initial - T_ambient)
        target_temp_diff = temp_diff_initial * math.exp(-1) # Target diff after 1 tau

        for i, temp in enumerate(temp_points):
            current_temp_diff = abs(temp - T_ambient)
            if current_temp_diff <= target_temp_diff:
                # Simple linear interpolation between points i-1 and i
                if i > 0:
                    prev_temp_diff = abs(temp_points[i-1] - T_ambient)
                    t_prev = time_points[i-1]
                    t_curr = time_points[i]
                    if prev_temp_diff > target_temp_diff: # Ensure we crossed the target
                         fraction = (prev_temp_diff - target_temp_diff) / (prev_temp_diff - current_temp_diff)
                         tau_time = t_prev + fraction * (t_curr - t_prev)
                    else: # Edge case if first point is already below target
                        tau_time = t_curr
                else: # First point is already below target
                    tau_time = time_points[i]
                break

    # Estimate time to equilibrium (5 time constants) if tau was found
    time_to_equilibrium = 5 * tau_time if tau_time is not None else None
    avg_h = sum(convection_coeffs) / len(convection_coeffs) if convection_coeffs else 0

    return {
        "time_points": time_points,
        "temp_points": temp_points,
        "heat_rate_points": heat_rate_points, # Represents heat loss rate
        "convection_coeffs": convection_coeffs,
        "convection_type": convection_type,
        "avg_convection_coeff": avg_h,
        "time_constant": tau_time,
        "time_to_equilibrium": time_to_equilibrium,
        "final_temp": temp_points[-1],
        "final_delta_t": temp_points[-1] - T_ambient,
        "total_area": total_area,
        "volume": volume
    }


# --- Steady State Calculation ---

def calculate_steady_state_temperature(
    geometry,
    dimensions,
    material_properties,
    thermal_conditions,
    heat_input # New parameter: Heat input power (W)
):
    """
    Calculate the steady-state surface temperature for an object
    with continuous heat input. Balances heat input with convection
    and radiation losses.
    """
    geometry_type = geometry['type']
    orientation = geometry.get('orientation', 'vertical')

    # Get geometric properties
    geo_details = _get_geometry_details(geometry_type, dimensions, orientation)
    total_area = geo_details['total_area']
    volume = geo_details['volume'] # Keep for consistency, though not used in SS calc
    char_length_natural = geo_details['char_length_natural']
    char_length_forced = geo_details['char_length_forced']

    # Material properties (only emissivity needed for SS surface temp)
    emissivity = material_properties.get('emissivity', 0.9)

    # Thermal conditions
    T_ambient = thermal_conditions['ambient_temp']
    air_velocity = thermal_conditions.get('air_velocity', 0)

    # Iterative solver parameters
    max_iterations = 100
    tolerance = 0.01 # Tolerance for temperature convergence (°C)
    T_surface_guess = T_ambient + 20 # Initial guess

    convection_type = "natural" if air_velocity <= 0.1 else "forced"
    last_h = 0

    print(f"Starting steady-state calculation for Q_in = {heat_input} W")

    if total_area <= 0:
        print("Error: Total surface area is zero. Cannot calculate steady state.")
        return {"error": "Zero surface area"}

    for i in range(max_iterations):
        T_old_guess = T_surface_guess

        # 1. Calculate heat transfer coefficient 'h' based on current guess
        if convection_type == "natural":
            L_c = char_length_natural
            h = natural_convection_coefficient(
                geometry_type, L_c, T_surface_guess, T_ambient, orientation
            )
        else: # Forced
            L_c = char_length_forced
            h = forced_convection_coefficient(
                geometry_type, L_c, air_velocity, T_surface_guess, T_ambient
            )
        last_h = h # Store for final result

        # 2. Calculate heat loss rates at current guess temperature
        q_conv = convection_heat_transfer(h, total_area, T_surface_guess, T_ambient)
        q_rad = radiation_heat_transfer(emissivity, total_area, T_surface_guess, T_ambient)
        q_output = q_conv + q_rad

        # 3. Check for convergence
        # We want q_output = heat_input
        error = heat_input - q_output

        # If error is small enough, we've converged (based on heat balance)
        # Also check temperature change to avoid oscillations around solution
        # Use relative error for heat balance check
        relative_error = abs(error / heat_input) if heat_input != 0 else abs(error)

        # Check temperature change stability
        temp_change = abs(T_surface_guess - T_old_guess)

        # Convergence criteria: small error AND small temperature change from last step
        # Use a slightly more robust check than just temperature difference
        if i > 0 and relative_error < 0.001 and temp_change < tolerance: # 0.1% heat balance error
            print(f"Converged in {i+1} iterations.")
            break

        # 4. Update temperature guess
        # Estimate derivative d(q_output)/dT (approximation)
        # d(q_conv)/dT ≈ h * A  (ignoring change in h with T for derivative)
        # d(q_rad)/dT = ε * σ * A * 4 * T_surface_K^3
        # Need T_surface in Kelvin for radiation derivative
        T_surface_K = T_surface_guess + 273.15
        dq_rad_dT = emissivity * 5.67e-8 * total_area * 4 * T_surface_K**3
        dq_total_dT = h * total_area + dq_rad_dT

        # Newton-Raphson like step: T_new = T_old - f(T) / f'(T)
        # Here f(T) = q_output(T) - heat_input = -error
        # f'(T) = dq_total_dT
        if dq_total_dT > 1e-6: # Avoid division by zero or very small numbers
            delta_T_update = error / dq_total_dT
            T_surface_guess += delta_T_update
        else:
            # Fallback: If derivative is near zero, make a small fixed step
            # This might happen if T_ambient is very high or heat input low
            T_surface_guess += 0.1 * (1 if error > 0 else -1) # Step 0.1 deg in direction of error

        # Prevent guess from going below ambient (physically unlikely for heat input)
        T_surface_guess = max(T_surface_guess, T_ambient - 1) # Allow slightly below for numerical reasons

        # print(f"Iter {i}: T={T_old_guess:.2f}°C, h={h:.2f}, q_conv={q_conv:.1f}, q_rad={q_rad:.1f}, q_out={q_output:.1f}, err={error:.1f}, T_new={T_surface_guess:.2f}°C")


    else: # Loop finished without break (max iterations reached)
        print(f"Warning: Steady-state calculation did not fully converge within {max_iterations} iterations.")
        print(f"Final state: T={T_surface_guess:.2f}°C, q_out={q_output:.1f}W, error={error:.1f}W")


    # Final calculation of q values at the converged temperature
    final_h = last_h
    q_conv_final = convection_heat_transfer(final_h, total_area, T_surface_guess, T_ambient)
    q_rad_final = radiation_heat_transfer(emissivity, total_area, T_surface_guess, T_ambient)
    q_output_final = q_conv_final + q_rad_final

    return {
        "steady_state_temp": T_surface_guess,
        "final_convection_coeff": final_h,
        "final_q_conv": q_conv_final,
        "final_q_rad": q_rad_final,
        "final_q_output": q_output_final, # Should be very close to heat_input
        "heat_input": heat_input,
        "total_area": total_area,
        "volume": volume, # Included for info
        "convection_type": convection_type,
        "iterations": i + 1,
        "converged": i < max_iterations -1
    }


# --- Frontend Convenience Functions ---

def thermal_calculation_py(
    # Mode Selection
    calculation_mode, # "transient" or "steady_state"
    # Geometry
    geometry_type,
    orientation,
    # Dimensions
    length,
    width_or_diameter,
    thickness,
    # Material properties
    thermal_conductivity, # Used only by conduction func, not directly here now
    density,
    specific_heat,
    emissivity,
    # Thermal conditions
    initial_temp, # Used in transient
    ambient_temp,
    air_velocity,
    heat_input,   # Used in steady_state
    # Simulation parameters
    time_steps=100, # Used in transient
    total_time=3600 # Used in transient
):
    """
    Frontend-friendly function that dispatches to the correct calculation mode.
    """
    # Set up the parameter dictionaries
    geometry = {"type": geometry_type, "orientation": orientation}

    dimensions = {}
    if geometry_type == "plate":
        dimensions = {
            "length": length,
            "width": width_or_diameter,
            "thickness": thickness
        }
    elif geometry_type == "cylinder":
        dimensions = {
            "diameter": width_or_diameter,
            "length": length
        }
        # thickness is ignored for cylinder geometry
    else:
         raise ValueError(f"Unsupported geometry type: {geometry_type}")

    # Note: k is not directly used by lumped capacitance or steady state surface temp
    # calculation, but keep it in properties dict for potential future use.
    material_properties = {
        "thermal_conductivity": thermal_conductivity,
        "density": density,
        "specific_heat": specific_heat,
        "emissivity": emissivity
    }

    thermal_conditions = {
        "initial_temp": initial_temp,
        "ambient_temp": ambient_temp,
        "air_velocity": air_velocity
    }

    if calculation_mode == "transient":
        result = calculate_transient_cooling(
            geometry,
            dimensions,
            material_properties,
            thermal_conditions,
            time_steps,
            total_time
        )
        # Process result for frontend (downsample if needed)
        display_points = min(50, time_steps + 1) # +1 because results include time=0
        step = max(1, (time_steps + 1) // display_points)

        display_times = [result["time_points"][i] for i in range(0, len(result["time_points"]), step)]
        display_temps = [result["temp_points"][i] for i in range(0, len(result["temp_points"]), step)]
        display_heat_rates = [result["heat_rate_points"][i] for i in range(0, len(result["heat_rate_points"]), step)]

        # Ensure the final point is included if step doesn't land on it
        if (len(result["time_points"]) - 1) % step != 0:
            display_times.append(result["time_points"][-1])
            display_temps.append(result["temp_points"][-1])
            display_heat_rates.append(result["heat_rate_points"][-1])

        # Return results in a JSON-friendly format
        return {
            "mode": "transient",
            "times": display_times,
            "temperatures": display_temps,
            "heat_rates": display_heat_rates, # Note: this is heat *loss* rate
            "time_constant": result.get("time_constant"),
            "time_to_equilibrium": result.get("time_to_equilibrium"),
            "final_temp": result.get("final_temp"),
            "final_delta_t": result.get("final_delta_t"),
            "total_area": result.get("total_area"),
            "volume": result.get("volume"),
            "convection_type": result.get("convection_type"),
            "avg_convection_coeff": result.get("avg_convection_coeff", 0)
        }

    elif calculation_mode == "steady_state":
        # Add heat_input to thermal conditions for steady state function
        # Note: calculate_steady_state_temperature takes heat_input as separate arg
        result = calculate_steady_state_temperature(
            geometry,
            dimensions,
            material_properties, # Only uses emissivity from this
            thermal_conditions, # Uses T_ambient, air_velocity
            heat_input
        )
        # Return steady state results directly
        return {"mode": "steady_state", **result} # Combine mode identifier with results dict

    else:
        raise ValueError(f"Unsupported calculation_mode: {calculation_mode}")