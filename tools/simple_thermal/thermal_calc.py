# thermal_calc.py
import math

def conduction_heat_transfer(k, A, T_hot, T_cold, L):
    """
    Calculate heat transfer through conduction
    
    Parameters:
    - k: Thermal conductivity (W/m·K)
    - A: Cross-sectional area (m²)
    - T_hot: Hot side temperature (°C)
    - T_cold: Cold side temperature (°C)
    - L: Material thickness (m)
    
    Returns:
    - Heat transfer rate (W)
    """
    return k * A * (T_hot - T_cold) / L

def natural_convection_coefficient(surface_type, char_length, T_surface, T_ambient, orientation='vertical'):
    """
    Estimate natural convection heat transfer coefficient
    
    Parameters:
    - surface_type: 'plate', 'cylinder', etc.
    - char_length: Characteristic length (m)
    - T_surface: Surface temperature (°C)
    - T_ambient: Ambient temperature (°C)
    - orientation: 'vertical', 'horizontal_up', 'horizontal_down'
    
    Returns:
    - Estimated heat transfer coefficient (W/m²·K)
    """
    # Convert temperatures to Kelvin for property calculations
    T_surface_K = T_surface + 273.15
    T_ambient_K = T_ambient + 273.15
    T_film = (T_surface_K + T_ambient_K) / 2  # Film temperature
    
    # Properties of air at film temperature (approximated for typical ranges)
    # These are simplified approximations
    beta = 1 / T_film  # Thermal expansion coefficient (1/K)
    
    # Kinematic viscosity (m²/s) approximated as function of temperature
    nu = 1.46e-5 * (T_film/293.15)**1.5
    
    # Thermal diffusivity (m²/s) approximated as function of temperature
    alpha = 2.0e-5 * (T_film/293.15)**1.5
    
    # Prandtl number (dimensionless)
    Pr = 0.71
    
    # Calculate Rayleigh number
    g = 9.81  # Gravity (m/s²)
    delta_T = abs(T_surface - T_ambient)
    Ra = (g * beta * delta_T * char_length**3) / (nu * alpha)
    
    # Calculate Nusselt number based on surface type and orientation
    Nu = 0
    
    if surface_type == 'plate':
        if orientation == 'vertical':
            if Ra < 1e9:
                Nu = 0.59 * Ra**0.25
            else:
                Nu = 0.1 * Ra**0.33
        elif orientation == 'horizontal_up' and T_surface > T_ambient:
            # Hot surface facing up
            Nu = 0.54 * Ra**0.25
        elif orientation == 'horizontal_down' and T_surface > T_ambient:
            # Hot surface facing down
            Nu = 0.27 * Ra**0.25
    
    elif surface_type == 'cylinder':
        # For horizontal cylinders
        if Ra >= 1e-5 and Ra <= 1e12:
            Nu = 0.6 + 0.387 * Ra**(1/6) / (1 + (0.559/Pr)**(9/16))**(8/27)
    
    # Calculate thermal conductivity of air (W/m·K)
    k_air = 0.0257 * (T_film/293.15)**0.8
    
    # Calculate heat transfer coefficient
    h = Nu * k_air / char_length
    
    # Ensure minimum value for natural convection
    return max(h, 2.0)

def forced_convection_coefficient(surface_type, char_length, velocity, T_surface, T_ambient):
    """
    Estimate forced convection heat transfer coefficient
    
    Parameters:
    - surface_type: 'plate', 'cylinder'
    - char_length: Characteristic length (m)
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
    
    # Air properties at film temperature (simplified)
    # Kinematic viscosity (m²/s)
    nu = 1.46e-5 * (T_film/293.15)**1.5
    
    # Thermal conductivity of air (W/m·K)
    k_air = 0.0257 * (T_film/293.15)**0.8
    
    # Prandtl number (dimensionless)
    Pr = 0.71
    
    # Calculate Reynolds number
    Re = velocity * char_length / nu
    
    # Calculate Nusselt number based on surface type
    Nu = 0
    
    if surface_type == 'plate':
        if Re < 5e5:  # Laminar flow
            Nu = 0.664 * Re**0.5 * Pr**(1/3)
        else:  # Turbulent flow
            Nu = 0.037 * Re**0.8 * Pr**(1/3)
    
    elif surface_type == 'cylinder':
        if Re >= 40 and Re <= 4000:
            Nu = 0.683 * Re**0.466 * Pr**(1/3)
        elif Re > 4000 and Re <= 40000:
            Nu = 0.193 * Re**0.618 * Pr**(1/3)
        elif Re > 40000 and Re <= 400000:
            Nu = 0.027 * Re**0.805 * Pr**(1/3)
    
    # Calculate heat transfer coefficient
    h = Nu * k_air / char_length
    
    # Ensure minimum value
    return max(h, 5.0)

def convection_heat_transfer(h, A, T_surface, T_ambient):
    """
    Calculate heat transfer through convection
    
    Parameters:
    - h: Heat transfer coefficient (W/m²·K)
    - A: Surface area (m²)
    - T_surface: Surface temperature (°C)
    - T_ambient: Ambient temperature (°C)
    
    Returns:
    - Heat transfer rate (W)
    """
    return h * A * (T_surface - T_ambient)

def radiation_heat_transfer(emissivity, A, T_surface, T_ambient):
    """
    Calculate heat transfer through radiation
    
    Parameters:
    - emissivity: Surface emissivity (dimensionless)
    - A: Surface area (m²)
    - T_surface: Surface temperature (°C)
    - T_ambient: Ambient temperature (°C)
    
    Returns:
    - Heat transfer rate (W)
    """
    # Convert temperatures to Kelvin for radiation calculation
    T_surface_K = T_surface + 273.15
    T_ambient_K = T_ambient + 273.15
    
    # Stefan-Boltzmann constant (W/m²·K⁴)
    sigma = 5.67e-8
    
    return emissivity * sigma * A * (T_surface_K**4 - T_ambient_K**4)

def calculate_total_heat_transfer(
    geometry, 
    dimensions, 
    material_properties, 
    thermal_conditions,
    time_steps=100,
    total_time=3600  # 1 hour by default
):
    """
    Calculate temperature change over time for an object
    
    Parameters:
    - geometry: Dict containing geometry type and orientation
    - dimensions: Dict containing dimensions of the object
    - material_properties: Dict containing material properties
    - thermal_conditions: Dict containing thermal conditions
    - time_steps: Number of time steps for simulation
    - total_time: Total simulation time in seconds
    
    Returns:
    - Dict containing simulation results
    """
    # Extract parameters
    geometry_type = geometry['type']  # 'plate' or 'cylinder'
    orientation = geometry.get('orientation', 'vertical')  # Default to vertical
    
    # For a plate: length, width, thickness
    # For a cylinder: diameter, length
    if geometry_type == 'plate':
        length = dimensions['length']
        width = dimensions['width']
        thickness = dimensions['thickness']
        
        # Calculate surface areas
        area_edges = 2 * (length * thickness + width * thickness)
        area_faces = 2 * (length * width)
        total_area = area_edges + area_faces
        
        # Characteristic length for natural convection
        char_length = length if orientation == 'vertical' else width
        
        # Volume
        volume = length * width * thickness
        
    elif geometry_type == 'cylinder':
        diameter = dimensions['diameter']
        length = dimensions['length']
        
        # Calculate surface areas
        area_curved = math.pi * diameter * length
        area_ends = 2 * (math.pi * (diameter/2)**2)
        total_area = area_curved + area_ends
        
        # Characteristic length
        char_length = diameter
        
        # Volume
        volume = math.pi * (diameter/2)**2 * length
        
    else:
        raise ValueError(f"Unsupported geometry type: {geometry_type}")
    
    # Material properties
    k = material_properties['thermal_conductivity']  # W/m·K
    rho = material_properties['density']  # kg/m³
    c_p = material_properties['specific_heat']  # J/kg·K
    emissivity = material_properties.get('emissivity', 0.9)  # Default to 0.9
    
    # Thermal conditions
    T_initial = thermal_conditions['initial_temp']  # °C
    T_ambient = thermal_conditions['ambient_temp']  # °C
    air_velocity = thermal_conditions.get('air_velocity', 0)  # m/s, 0 means natural convection
    
    # Time parameters
    dt = total_time / time_steps  # Time step size
    
    # Initialize results
    time_points = [0]
    temp_points = [T_initial]
    heat_rate_points = [0]
    convection_coeff = []
    
    # Current temperature
    T_current = T_initial
    
    # Calculate thermal mass (J/K)
    thermal_mass = rho * volume * c_p
    
    for step in range(1, time_steps + 1):
        # Determine convection coefficient
        if air_velocity <= 0.1:
            # Natural convection
            h = natural_convection_coefficient(
                geometry_type, char_length, T_current, T_ambient, orientation
            )
            convection_type = "natural"
        else:
            # Forced convection
            h = forced_convection_coefficient(
                geometry_type, char_length, air_velocity, T_current, T_ambient
            )
            convection_type = "forced"
        
        convection_coeff.append(h)
        
        # Calculate heat transfer rate
        q_conv = convection_heat_transfer(h, total_area, T_current, T_ambient)
        q_rad = radiation_heat_transfer(emissivity, total_area, T_current, T_ambient)
        
        # Total heat transfer rate
        q_total = q_conv + q_rad
        
        # Update temperature using lumped capacitance method
        dT = q_total * dt / thermal_mass
        T_current = T_current - dT  # Negative because heat is leaving the object when T_current > T_ambient
        
        # Store results
        time_points.append(step * dt)
        temp_points.append(T_current)
        heat_rate_points.append(q_total)
    
    # Calculate time constants and equilibrium
    # Time constant (τ) is the time it takes to reach 63.2% of the way to the final temperature
    temp_diff_initial = T_initial - T_ambient
    temp_diff_final = temp_points[-1] - T_ambient
    temp_diff_tau = temp_diff_initial * 0.368  # 36.8% of initial ΔT remains after one time constant
    
    # Find time constant (when temperature reaches T_ambient + temp_diff_tau)
    tau_target = T_ambient + temp_diff_tau
    tau_time = None
    
    for i, temp in enumerate(temp_points):
        if temp <= tau_target:
            tau_time = time_points[i]
            break
    
    # If we didn't reach the time constant, estimate it
    if tau_time is None:
        # Estimate time constant from thermal mass and average heat transfer coefficient
        avg_h = sum(convection_coeff) / len(convection_coeff)
        tau_time = thermal_mass / (avg_h * total_area)
    
    # Time to reach near-equilibrium (typically 5 time constants ≈ 99.3% complete)
    time_to_equilibrium = 5 * tau_time if tau_time else None
    
    return {
        "time_points": time_points,
        "temp_points": temp_points,
        "heat_rate_points": heat_rate_points,
        "convection_coeffs": convection_coeff,
        "convection_type": convection_type,
        "time_constant": tau_time,
        "time_to_equilibrium": time_to_equilibrium,
        "final_temp": temp_points[-1],
        "final_delta_t": temp_points[-1] - T_ambient,
        "total_area": total_area,
        "volume": volume
    }

# Convenience function for frontend
def thermal_dissipation_calculate(
    # Geometry
    geometry_type,
    orientation,
    # Dimensions
    length,
    width_or_diameter,
    thickness,
    # Material properties
    thermal_conductivity,
    density,
    specific_heat,
    emissivity,
    # Thermal conditions
    initial_temp,
    ambient_temp,
    air_velocity,
    # Simulation parameters
    time_steps=100,
    total_time=3600
):
    """
    Frontend-friendly function that returns a complete result set for the UI
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
    else:  # cylinder
        dimensions = {
            "diameter": width_or_diameter,
            "length": length
        }
        # thickness is ignored for cylinder geometry
    
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
    
    # Run the calculation
    result = calculate_total_heat_transfer(
        geometry,
        dimensions,
        material_properties,
        thermal_conditions,
        time_steps,
        total_time
    )
    
    # Create time segments for display (reduce data points if needed)
    display_points = min(50, time_steps)
    step = max(1, time_steps // display_points)
    
    display_times = [result["time_points"][i] for i in range(0, len(result["time_points"]), step)]
    display_temps = [result["temp_points"][i] for i in range(0, len(result["temp_points"]), step)]
    display_heat_rates = [result["heat_rate_points"][i] for i in range(0, len(result["heat_rate_points"]), step)]
    
    # Make sure the final point is included
    if len(result["time_points"]) % step != 0:
        display_times.append(result["time_points"][-1])
        display_temps.append(result["temp_points"][-1])
        display_heat_rates.append(result["heat_rate_points"][-1])
    
    # Return the results in a JSON-friendly format
    return {
        "times": display_times,
        "temperatures": display_temps,
        "heat_rates": display_heat_rates,
        "time_constant": result["time_constant"],
        "time_to_equilibrium": result["time_to_equilibrium"],
        "final_temp": result["final_temp"],
        "final_delta_t": result["final_delta_t"],
        "total_area": result["total_area"],
        "volume": result["volume"],
        "convection_type": result["convection_type"],
        "avg_convection_coeff": sum(result["convection_coeffs"]) / len(result["convection_coeffs"]) if result["convection_coeffs"] else 0
    }