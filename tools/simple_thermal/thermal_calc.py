# thermal_calc.py
import math
import sys # Needed for float_info.epsilon

# --- Core Heat Transfer Functions (Updated) ---

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
    - surface_type: 'plate', 'cylinder', etc. For heatsinks, 'plate' is used with fin spacing as char_length.
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
            Nu = Nu_laminar_turbulent

        elif orientation == 'horizontal_up' and T_surface > T_ambient: # Hot surface facing up
             if Ra < 1e7: Nu = 0.54 * Ra**0.25 # Laminar
             else: Nu = 0.15 * Ra**(1/3) # Turbulent
        elif orientation == 'horizontal_down' and T_surface > T_ambient: # Hot surface facing down
             Nu = 0.27 * Ra**0.25
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


def forced_convection_coefficient(surface_type, char_length, velocity, T_surface, T_ambient, duct_length=None):
    """
    Estimate forced convection heat transfer coefficient.

    Parameters:
    - surface_type: 'plate', 'cylinder', or 'duct' (for heatsink channels)
    - char_length: Characteristic length (m) (plate length, cylinder diameter, or duct hydraulic diameter)
    - velocity: Fluid velocity (m/s) (free-stream or in-duct)
    - T_surface: Surface temperature (°C)
    - T_ambient: Ambient temperature (°C)
    - duct_length: Length of the duct/channel (m), required for 'duct' type.

    Returns:
    - Estimated heat transfer coefficient (W/m²·K)
    """
    # Convert temperatures to Kelvin for property calculations
    T_surface_K = T_surface + 273.15
    T_ambient_K = T_ambient + 273.15
    T_film = (T_surface_K + T_ambient_K) / 2  # Film temperature

    # Air properties at film temperature
    nu = 1.46e-5 * (T_film/293.15)**1.75
    k_air = 0.0257 * (T_film/293.15)**0.85
    Pr = 0.71

    if nu <= 0: return 5.0 # Failsafe
    Re = velocity * char_length / nu
    Nu = 0

    if surface_type == 'plate':
        if Re < 5e5:  # Laminar
            Nu = 0.664 * Re**0.5 * Pr**(1/3)
        else:  # Turbulent (mixed)
            Nu = (0.037 * Re**0.8 - 871) * Pr**(1/3)
            Nu = max(Nu, 0)

    elif surface_type == 'cylinder':
        C, m = 0, 0
        Re_ranges = {(1, 40): (0.75, 0.4), (40, 1000): (0.51, 0.5), (1000, 2e5): (0.26, 0.6), (2e5, 1e6): (0.076, 0.7)}
        for r, params in Re_ranges.items():
            if r[0] <= Re < r[1]:
                C, m = params
                break
        if C == 0 and Re >= 1e6: C, m = (0.076, 0.7)
        if C > 0: Nu = C * Re**m * Pr**(0.37)
        else: Nu = 0.3 + (0.62 * Re**0.5 * Pr**(1/3)) / (1 + (0.4/Pr)**(2/3))**0.25

    elif surface_type == 'duct':
        if duct_length is None or duct_length <= 0:
            raise ValueError("Duct length must be a positive number for 'duct' surface type.")
        D_h = char_length
        if D_h <= 0: return 5.0 # Failsafe

        if Re < 2300:  # Laminar Flow
            # Correlation for combined entry length (thermal and hydrodynamic) for constant wall temp
            # (Shah and London, referenced in Incropera & DeWitt)
            g_z_star = (Re * Pr) / (duct_length / D_h)
            if g_z_star < 1e-3: # Approaching fully developed flow
                 Nu = 3.66
            else:
                 term1 = 3.66
                 term2 = 1.615 * (g_z_star)**(1/3)
                 # Blending correlation
                 Nu = (term1**3 + term2**3)**(1/3)
        else:  # Turbulent Flow
            # Dittus-Boelter equation (for heating, Pr^0.4)
            Nu = 0.023 * Re**0.8 * Pr**0.4

    # Calculate heat transfer coefficient
    if char_length <= 0 or k_air <= 0: return 5.0 # Failsafe
    h = Nu * k_air / char_length
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
        details['char_length_natural'] = length if orientation == 'vertical' else width
        details['char_length_forced'] = length

    elif geometry_type == 'cylinder':
        diameter = dimensions['diameter']
        length = dimensions['length']
        radius = diameter / 2
        area_curved = math.pi * diameter * length
        area_ends = 2 * (math.pi * radius**2)
        details['total_area'] = area_curved + area_ends
        details['volume'] = math.pi * radius**2 * length
        details['char_length_natural'] = diameter
        details['char_length_forced'] = diameter

    elif geometry_type == 'heatsink':
        L = dimensions['base_length']
        W = dimensions['base_width']
        t_base = dimensions['base_thickness']
        H_fin = dimensions['fin_height']
        t_fin = dimensions['fin_thickness']
        N_fins = dimensions['num_fins']

        # Fin spacing calculation
        if N_fins <= 1:
            fin_spacing = float('inf') # Effectively a flat plate
        else:
            fin_spacing = (W - N_fins * t_fin) / (N_fins - 1)
        if fin_spacing < 0:
            raise ValueError("Invalid dimensions: Fins are wider than the base width allows.")
        details['fin_spacing'] = fin_spacing

        # Simplified total area calculation (Base area + Fin area)
        area_base = L * W
        area_fins = 2 * N_fins * L * H_fin
        details['total_area'] = area_base + area_fins

        # Volume calculation
        volume_base = L * W * t_base
        volume_fins = N_fins * L * H_fin * t_fin
        details['volume'] = volume_base + volume_fins

        # Characteristic length for natural convection is fin spacing
        details['char_length_natural'] = fin_spacing
        # Characteristic length for forced convection is hydraulic diameter of fin channels
        details['char_length_forced'] = 2 * fin_spacing if fin_spacing > 0 else 0

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
    geo_details = _get_geometry_details(geometry_type, dimensions, orientation)
    total_area = geo_details['total_area']
    volume = geo_details['volume']
    
    rho = material_properties['density']
    c_p = material_properties['specific_heat']
    emissivity = material_properties.get('emissivity', 0.9)
    T_initial = thermal_conditions['initial_temp']
    T_ambient = thermal_conditions['ambient_temp']
    air_velocity = thermal_conditions.get('air_velocity', 0)
    dt = total_time / time_steps

    T_current = T_initial
    time_points = [0]
    temp_points = [T_initial]
    heat_rate_points = [0]
    convection_coeffs = []
    
    if volume <= 0 or rho <= 0 or c_p <= 0:
        return { "error": "Zero or negative volume/density/specific heat." }
    thermal_mass = rho * volume * c_p

    convection_type = "natural" if air_velocity <= 0.1 else "forced"

    for step in range(1, time_steps + 1):
        h = 0
        if convection_type == "natural":
            L_c = geo_details['char_length_natural']
            # For heatsinks, natural convection is best modeled as vertical plates (the fins)
            surface = 'plate' if geometry_type == 'heatsink' else geometry_type
            orient = 'vertical' if geometry_type == 'heatsink' else orientation
            h = natural_convection_coefficient(surface, L_c, T_current, T_ambient, orient)
        else: # Forced
            if geometry_type == 'heatsink':
                s = geo_details['fin_spacing']
                t_fin = dimensions['fin_thickness']
                L_duct = dimensions['base_length']
                D_h = geo_details['char_length_forced']
                # Calculate velocity between fins, accounting for blockage
                V_channel = air_velocity * s / (s + t_fin) if (s + t_fin) > 0 else air_velocity
                h = forced_convection_coefficient('duct', D_h, V_channel, T_current, T_ambient, duct_length=L_duct)
            else:
                L_c = geo_details['char_length_forced']
                h = forced_convection_coefficient(geometry_type, L_c, air_velocity, T_current, T_ambient)
        convection_coeffs.append(h)

        q_conv = convection_heat_transfer(h, total_area, T_current, T_ambient)
        q_rad = radiation_heat_transfer(emissivity, total_area, T_current, T_ambient)
        q_total_loss = q_conv + q_rad

        delta_T = - (q_total_loss / thermal_mass) * dt
        T_current += delta_T

        if (T_initial > T_ambient and T_current < T_ambient) or (T_initial < T_ambient and T_current > T_ambient):
             T_current = T_ambient
             q_total_loss = 0
        
        time_points.append(step * dt)
        temp_points.append(T_current)
        heat_rate_points.append(q_total_loss)

    tau_time = None
    if T_initial != T_ambient:
        temp_diff_initial = abs(T_initial - T_ambient)
        target_temp_diff = temp_diff_initial * math.exp(-1)
        for i, temp in enumerate(temp_points):
            current_temp_diff = abs(temp - T_ambient)
            if current_temp_diff <= target_temp_diff and i > 0:
                prev_temp_diff = abs(temp_points[i-1] - T_ambient)
                t_prev, t_curr = time_points[i-1], time_points[i]
                if prev_temp_diff > target_temp_diff:
                     fraction = (prev_temp_diff - target_temp_diff) / (prev_temp_diff - current_temp_diff)
                     tau_time = t_prev + fraction * (t_curr - t_prev)
                else: tau_time = t_curr
                break
    
    time_to_equilibrium = 5 * tau_time if tau_time is not None else None
    avg_h = sum(convection_coeffs) / len(convection_coeffs) if convection_coeffs else 0

    return {
        "time_points": time_points, "temp_points": temp_points,
        "heat_rate_points": heat_rate_points, "convection_coeffs": convection_coeffs,
        "convection_type": convection_type, "avg_convection_coeff": avg_h,
        "time_constant": tau_time, "time_to_equilibrium": time_to_equilibrium,
        "final_temp": temp_points[-1], "final_delta_t": temp_points[-1] - T_ambient,
        "total_area": total_area, "volume": volume, **geo_details
    }


# --- Steady State Calculation ---

def calculate_steady_state_temperature(
    geometry,
    dimensions,
    material_properties,
    thermal_conditions,
    heat_input
):
    """
    Calculate the steady-state surface temperature for an object with continuous heat input.
    """
    geometry_type = geometry['type']
    orientation = geometry.get('orientation', 'vertical')
    geo_details = _get_geometry_details(geometry_type, dimensions, orientation)
    total_area = geo_details['total_area']
    volume = geo_details['volume']
    
    emissivity = material_properties.get('emissivity', 0.9)
    T_ambient = thermal_conditions['ambient_temp']
    air_velocity = thermal_conditions.get('air_velocity', 0)

    max_iterations = 100
    tolerance = 0.01
    T_surface_guess = T_ambient + 20

    convection_type = "natural" if air_velocity <= 0.1 else "forced"
    last_h = 0
    
    if total_area <= 0:
        return {"error": "Total surface area is zero. Cannot calculate steady state."}

    converged = False
    for i in range(max_iterations):
        T_old_guess = T_surface_guess
        h = 0
        if convection_type == "natural":
            L_c = geo_details['char_length_natural']
            surface = 'plate' if geometry_type == 'heatsink' else geometry_type
            orient = 'vertical' if geometry_type == 'heatsink' else orientation
            h = natural_convection_coefficient(surface, L_c, T_surface_guess, T_ambient, orient)
        else: # Forced
            if geometry_type == 'heatsink':
                s = geo_details['fin_spacing']
                t_fin = dimensions['fin_thickness']
                L_duct = dimensions['base_length']
                D_h = geo_details['char_length_forced']
                V_channel = air_velocity * s / (s + t_fin) if (s + t_fin) > 0 else air_velocity
                h = forced_convection_coefficient('duct', D_h, V_channel, T_surface_guess, T_ambient, duct_length=L_duct)
            else:
                L_c = geo_details['char_length_forced']
                h = forced_convection_coefficient(geometry_type, L_c, air_velocity, T_surface_guess, T_ambient)
        last_h = h

        q_conv = convection_heat_transfer(h, total_area, T_surface_guess, T_ambient)
        q_rad = radiation_heat_transfer(emissivity, total_area, T_surface_guess, T_ambient)
        q_output = q_conv + q_rad

        error = heat_input - q_output
        relative_error = abs(error / heat_input) if heat_input > 1e-6 else abs(error)
        temp_change = abs(T_surface_guess - T_old_guess)
        
        if i > 0 and relative_error < 0.001 and temp_change < tolerance:
            converged = True
            break

        T_surface_K = T_surface_guess + 273.15
        dq_rad_dT = emissivity * 5.67e-8 * total_area * 4 * T_surface_K**3
        dq_total_dT = h * total_area + dq_rad_dT

        if dq_total_dT > 1e-6:
            delta_T_update = error / dq_total_dT
            T_surface_guess += delta_T_update
        else:
            T_surface_guess += 0.1 * (1 if error > 0 else -1)

        T_surface_guess = max(T_surface_guess, T_ambient - 1)

    if not converged:
        print(f"Warning: Steady-state did not converge within {max_iterations} iterations.")

    final_h = last_h
    q_conv_final = convection_heat_transfer(final_h, total_area, T_surface_guess, T_ambient)
    q_rad_final = radiation_heat_transfer(emissivity, total_area, T_surface_guess, T_ambient)
    q_output_final = q_conv_final + q_rad_final

    return {
        "steady_state_temp": T_surface_guess, "final_convection_coeff": final_h,
        "final_q_conv": q_conv_final, "final_q_rad": q_rad_final,
        "final_q_output": q_output_final, "heat_input": heat_input,
        "total_area": total_area, "volume": volume, "convection_type": convection_type,
        "iterations": i + 1, "converged": converged, **geo_details
    }


# --- Frontend Convenience Functions ---

def thermal_calculation_py(
    calculation_mode,
    geometry_type, orientation,
    # Plate/Cylinder Dims
    length, width_or_diameter, thickness,
    # Heatsink Dims
    base_length, base_width, base_thickness, fin_height, fin_thickness, num_fins,
    # Material properties
    thermal_conductivity, density, specific_heat, emissivity,
    # Thermal conditions
    initial_temp, ambient_temp, air_velocity, heat_input,
    # Sim params
    time_steps=100, total_time=3600
):
    """
    Frontend-friendly function that dispatches to the correct calculation mode.
    """
    geometry = {"type": geometry_type, "orientation": orientation}
    dimensions = {}
    
    try:
        if geometry_type == "plate":
            dimensions = {"length": length, "width": width_or_diameter, "thickness": thickness}
        elif geometry_type == "cylinder":
            dimensions = {"diameter": width_or_diameter, "length": length}
        elif geometry_type == "heatsink":
            dimensions = {
                "base_length": base_length, "base_width": base_width, "base_thickness": base_thickness,
                "fin_height": fin_height, "fin_thickness": fin_thickness, "num_fins": num_fins
            }
        else:
             raise ValueError(f"Unsupported geometry type: {geometry_type}")

        material_properties = {
            "thermal_conductivity": thermal_conductivity, "density": density,
            "specific_heat": specific_heat, "emissivity": emissivity
        }
        thermal_conditions = {
            "initial_temp": initial_temp, "ambient_temp": ambient_temp, "air_velocity": air_velocity
        }

        if calculation_mode == "transient":
            result = calculate_transient_cooling(
                geometry, dimensions, material_properties, thermal_conditions,
                time_steps, total_time
            )
            if "error" in result: return result

            display_points = min(50, time_steps + 1)
            step = max(1, (time_steps + 1) // display_points)
            display_times = result["time_points"][::step]
            display_temps = result["temp_points"][::step]
            display_heat_rates = result["heat_rate_points"][::step]

            if (len(result["time_points"]) - 1) % step != 0:
                display_times.append(result["time_points"][-1])
                display_temps.append(result["temp_points"][-1])
                display_heat_rates.append(result["heat_rate_points"][-1])

            return {"mode": "transient", "times": display_times, "temperatures": display_temps, "heat_rates": display_heat_rates, **result}

        elif calculation_mode == "steady_state":
            result = calculate_steady_state_temperature(
                geometry, dimensions, material_properties, thermal_conditions, heat_input
            )
            return {"mode": "steady_state", **result}
        else:
            raise ValueError(f"Unsupported calculation_mode: {calculation_mode}")

    except ValueError as e:
        # Catch errors from _get_geometry_details (e.g., negative fin spacing)
        # and return them to the frontend.
        return {"error": str(e)}