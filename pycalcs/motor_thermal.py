"""
Motor Thermal Estimator module.

This module provides thermal analysis for Brushless DC (BLDC) motors using
a lumped parameter thermal network approach. It estimates steady-state
temperatures and transient thermal response based on motor geometry,
materials, and operating conditions.

References:
    - Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer"
    - J.R. Hendershot & T. Miller, "Design of Brushless Permanent-Magnet Machines"
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

# =============================================================================
# CONSTANTS & PROPERTIES
# =============================================================================

# Specific Heat Capacities (J/kg·K)
CP_COPPER = 385.0
CP_IRON = 449.0
CP_ALUMINUM = 897.0
CP_NEODYMIUM = 420.0  # Approx for magnets

# Temperature Coefficient of Resistance (1/K)
ALPHA_COPPER = 0.00393  # At 20°C

# Default Convection Coefficients (W/m²·K) based on simplified scenarios
CONVECTION_PRESETS = {
    "static_bench": {
        "h": 12.0,
        "description": "Static air (natural convection only)",
        "factor": 1.0
    },
    "enclosed_fuselage": {
        "h": 8.0,
        "description": "Enclosed in fuselage/housing (poor airflow)",
        "factor": 0.6
    },
    "low_airflow": {
        "h": 30.0,
        "description": "Low airflow (e.g., car moving, internal fan)",
        "factor": 2.5
    },
    "prop_wash_moderate": {
        "h": 60.0,
        "description": "Direct prop wash (moderate speed)",
        "factor": 5.0
    },
    "prop_wash_high": {
        "h": 100.0,
        "description": "Direct prop wash (high speed/drone)",
        "factor": 8.3
    },
}

@dataclass
class ThermalResult:
    """Container for thermal analysis results."""
    steady_state_temp: float
    time_to_limit: float
    thermal_resistance: float
    thermal_mass: float
    initial_power_loss: float
    final_power_loss: float
    curve_data: List[Dict[str, float]]
    status: str
    warnings: List[str]

# =============================================================================
# MOTOR DATABASE & ESTIMATION
# =============================================================================

MOTOR_PRESETS = {
    "1104_tiny": {
        "name": "1104 (Tiny Whoop)", 
        "description": "Small inrunner/outrunner for micro drones",
        "d": 14.0, "l": 12.0, "type": "outrunner", 
        "m_cu": 1.5, "m_fe": 3.5, "m_al": 1.5,
        "r_phase": 0.35, "current_typ": 4.0
    },
    "2207_fpv": {
        "name": "2207 (5\" FPV Drone)", 
        "description": "Standard racing drone motor",
        "d": 27.5, "l": 32.0, "type": "outrunner", 
        "m_cu": 10.0, "m_fe": 19.0, "m_al": 6.0,
        "r_phase": 0.045, "current_typ": 25.0
    },
    "2806_cinewhoop": {
        "name": "2806 (Cinewhoop)", 
        "description": "Flat pancake motor for efficiency",
        "d": 33.0, "l": 20.0, "type": "outrunner", 
        "m_cu": 12.0, "m_fe": 22.0, "m_al": 8.0,
        "r_phase": 0.055, "current_typ": 20.0
    },
    "3548_plane": {
        "name": "3548 (RC Plane)", 
        "description": "Mid-size outrunner for fixed wing",
        "d": 35.0, "l": 48.0, "type": "outrunner", 
        "m_cu": 45.0, "m_fe": 85.0, "m_al": 25.0,
        "r_phase": 0.035, "current_typ": 40.0
    },
    "5055_eskate": {
        "name": "5055 (E-Skate/Scooter)", 
        "description": "Large outrunner for traction",
        "d": 50.0, "l": 55.0, "type": "outrunner", 
        "m_cu": 110.0, "m_fe": 230.0, "m_al": 60.0,
        "r_phase": 0.025, "current_typ": 50.0
    },
    "6374_longboard": {
        "name": "6374 (E-Longboard)", 
        "description": "Powerful traction motor",
        "d": 63.0, "l": 74.0, "type": "outrunner", 
        "m_cu": 200.0, "m_fe": 450.0, "m_al": 100.0,
        "r_phase": 0.018, "current_typ": 70.0
    },
    "inrunner_3650": {
        "name": "3650 (1/10 RC Car)", 
        "description": "Standard 540-size inrunner",
        "d": 36.0, "l": 50.0, "type": "inrunner", 
        "m_cu": 60.0, "m_fe": 100.0, "m_al": 40.0,
        "r_phase": 0.012, "current_typ": 60.0
    }
}

def get_motor_presets() -> Dict[str, Dict[str, Any]]:
    """Return the database of motor presets."""
    return MOTOR_PRESETS

def estimate_mass_breakdown(
    diameter_mm: float,
    length_mm: float,
    motor_type: str = "outrunner",
    fill_factor: float = 0.4
) -> Dict[str, float]:
    """
    Estimate component masses based on geometry and type.
    
    This is a heuristic estimation for typical hobby BLDC motors.
    
    Parameters
    ----------
    diameter_mm : float
        Motor outer diameter.
    length_mm : float
        Motor can length.
    motor_type : str
        'outrunner' or 'inrunner'.
    fill_factor : float
        Slot fill factor (0.0 to 1.0). Typical 0.3-0.45.
    
    Returns
    -------
    dict
        {'m_cu': g, 'm_fe': g, 'm_al': g}
    """
    # Volume in cm^3
    vol_total = (math.pi * (diameter_mm/20)**2) * (length_mm/10)
    
    # Heuristic Density Factors (g/cm^3 of total volume)
    # Typical BLDC density is ~3.5 - 4.5 g/cm^3 overall.
    
    if motor_type == "outrunner":
        # Outrunner: More Iron (rotor ring + stator), less Al (base only)
        # Copper depends heavily on fill factor.
        
        # Scaling estimates:
        # Iron: ~50% of volume is effective iron density?
        # Copper: Stator volume * fill factor
        
        # Simplified ratio approach based on 5055 data:
        # Vol = 108 cm3. Mass = 400g. Density ~ 3.7.
        # Cu=110 (27%), Fe=230 (57%), Al=60 (15%).
        
        base_density = 3.8 # g/cm3
        mass_total = vol_total * base_density
        
        # Adjust Copper ratio based on Fill Factor (baseline 0.4)
        cu_ratio = 0.28 * (fill_factor / 0.4)
        fe_ratio = 0.57 # Assumed constant frame
        al_ratio = 0.15
        
        # Normalize
        total_ratio = cu_ratio + fe_ratio + al_ratio
        
        m_cu = mass_total * (cu_ratio / total_ratio)
        m_fe = mass_total * (fe_ratio / total_ratio)
        m_al = mass_total * (al_ratio / total_ratio)
        
    else: # Inrunner
        # Inrunner: Heavier case (Al), Iron rotor core, Stator iron
        # Generally denser? ~4.0 g/cm3
        
        base_density = 4.0
        mass_total = vol_total * base_density
        
        # Typical RC Car 3650:
        # Mass ~200g. Vol ~50cm3. Density ~4.
        # Cu ~30%, Fe ~50%, Al ~20%
        
        cu_ratio = 0.30 * (fill_factor / 0.4)
        fe_ratio = 0.50
        al_ratio = 0.20
        
        total_ratio = cu_ratio + fe_ratio + al_ratio
        
        m_cu = mass_total * (cu_ratio / total_ratio)
        m_fe = mass_total * (fe_ratio / total_ratio)
        m_al = mass_total * (al_ratio / total_ratio)

    return {
        "m_cu": round(m_cu, 1),
        "m_fe": round(m_fe, 1),
        "m_al": round(m_al, 1)
    }

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_surface_area(diameter_mm: float, length_mm: float) -> float:
    """Calculate external surface area of a cylinder (excluding ends if mounted)."""
    d_m = diameter_mm / 1000.0
    l_m = length_mm / 1000.0
    # Assuming cylinder side + one end face exposed (one mounted)
    # Area = pi * d * l + pi * (d/2)^2
    side_area = math.pi * d_m * l_m
    end_area = math.pi * (d_m / 2.0)**2
    return side_area + end_area

def calculate_thermal_mass(
    mass_copper_g: float,
    mass_iron_g: float,
    mass_housing_g: float
) -> float:
    """
    Calculate total thermal mass (Heat Capacity) in J/K.
    C_th = sum(m_i * Cp_i)
    """
    # Convert grams to kg
    m_cu = mass_copper_g / 1000.0
    m_fe = mass_iron_g / 1000.0
    m_al = mass_housing_g / 1000.0

    C_th = (m_cu * CP_COPPER) + (m_fe * CP_IRON) + (m_al * CP_ALUMINUM)
    return C_th

def calculate_resistance(R_ref: float, T_ref: float, T_target: float) -> float:
    """
    Calculate electrical resistance at target temperature.
    R(T) = R_ref * (1 + alpha * (T - T_ref))
    """
    return R_ref * (1.0 + ALPHA_COPPER * (T_target - T_ref))

# =============================================================================
# CORE CALCULATION
# =============================================================================

def analyze_motor_thermal(
    # Electrical Params
    current_amp: float,
    resistance_ohms: float,  # Phase resistance (line-to-line usually measured)
    
    # Geometry & Mass
    diameter_mm: float,
    length_mm: float,
    mass_copper_g: float,
    mass_iron_g: float,
    mass_housing_g: float,

    # Environment
    ambient_temp_c: float = 25.0,
    max_temp_limit_c: float = 80.0, # Magnet safe limit usually
    airflow_type: str = "static_bench",
    custom_h: Optional[float] = None,

    # Simulation Params
    duration_seconds: int = 600,
    time_step: float = 1.0
) -> Dict[str, Any]:
    """
    Perform lumped-parameter thermal analysis of a BLDC motor.

    Parameters
    ----------
    current_amp : float
        Continuous current load (Amps).
    resistance_ohms : float
        Motor phase resistance (at ambient/reference temp).
    diameter_mm : float
        Motor outer diameter (mm).
    length_mm : float
        Motor length (mm).
    mass_copper_g : float
        Estimated mass of copper windings (g).
    mass_iron_g : float
        Estimated mass of stator iron (g).
    mass_housing_g : float
        Estimated mass of aluminum housing/base (g).
    ambient_temp_c : float, optional
        Ambient air temperature (°C). Default 25.0.
    max_temp_limit_c : float, optional
        Critical temperature limit (°C). Default 80.0.
    airflow_type : str, optional
        Key from CONVECTION_PRESETS. Default "static_bench".
    custom_h : float, optional
        Override heat transfer coefficient (W/m²·K).
    duration_seconds : int, optional
        Simulation max duration. Default 600s.
    time_step : float, optional
        Simulation time step. Default 1.0s.

    Returns
    -------
    dict
        Dictionary containing steady state results, transient curve data,
        and safety warnings.
    """
    
    # 1. Determine Heat Transfer Coefficient (h)
    if custom_h is not None and custom_h > 0:
        h = float(custom_h)
        h_desc = "Custom User Value"
    else:
        preset = CONVECTION_PRESETS.get(airflow_type, CONVECTION_PRESETS["static_bench"])
        h = preset["h"]
        h_desc = preset["description"]

    # 2. Geometric & Thermal Properties
    surface_area = calculate_surface_area(diameter_mm, length_mm)
    thermal_mass = calculate_thermal_mass(mass_copper_g, mass_iron_g, mass_housing_g) # J/K
    
    # Thermal Resistance (R_th) = 1 / (h * A)
    # Note: This simplifies conduction through the motor. 
    # We assume the surface temp is representative of the lumped mass temp.
    # In reality, winding temp > surface temp. 
    # We add a small internal resistance factor or just acknowledge this is "bulk" temp.
    # For this estimator, we'll treat it as a single node for simplicity.
    if surface_area <= 0:
        return {"error": "Invalid surface area"}
    
    R_th = 1.0 / (h * surface_area) # K/W

    # 3. Iterative Simulation (Forward Euler)
    # We simulate because Resistance changes with Temp, making power loss non-linear.
    
    t = 0.0
    T_current = ambient_temp_c
    curve_data = []
    
    warnings = []
    limit_reached_time = None
    
    # Initial Power Loss
    # P = I^2 * R (Assume 3-phase BLDC, total heat is often approximated. 
    # If R is line-to-line, P_total = 1.5 * I^2 * R_phase?? 
    # Standard measurement: P_copper = 3 * I_phase^2 * R_phase.
    # If user gives 'current' as DC current into ESC, and R as line-to-line... 
    # Let's assume standard simplified: Loss = I^2 * R * 1.5 (approx for 3-phase trapezoidal) or just I^2*R for DC equivalent.
    # To be safe and generic, we'll assume the input Current is the "Motor Current" (Phase current RMS) 
    # and Resistance is Phase Resistance. 
    # Loss = 3 * I_phase_rms^2 * R_phase.
    # However, usually hobbyists know "Current Draw" (DC from battery) and "Internal Resistance" (line-to-line).
    # If R is Rm (line-to-line), then P_loss = I_dc^2 * Rm is a decent approximation for heat.
    # Let's stick to P = I^2 * R_input and note this in docs.
    
    P_initial = current_amp**2 * resistance_ohms

    for _ in range(int(duration_seconds / time_step) + 1):
        # Update Resistance based on current Temp
        R_temp = calculate_resistance(resistance_ohms, ambient_temp_c, T_current)
        
        # Heat Generation (Power In)
        P_gen = current_amp**2 * R_temp
        
        # Heat Dissipation (Power Out)
        # P_out = (T_surf - T_amb) / R_th
        P_diss = (T_current - ambient_temp_c) / R_th
        
        # Net Heat Flow
        P_net = P_gen - P_diss
        
        # Temperature Change: dT = (P_net / C_th) * dt
        dT = (P_net / thermal_mass) * time_step
        
        T_new = T_current + dT
        
        # Record Data
        if t % max(1, int(duration_seconds/100)) == 0: # Downsample for graph
            curve_data.append({
                "time": round(t, 2),
                "temp": round(T_current, 2),
                "power_loss": round(P_gen, 2),
                "dissipation": round(P_diss, 2)
            })
        
        # Check Limit
        if limit_reached_time is None and T_current >= max_temp_limit_c:
            limit_reached_time = t
            warnings.append(f"Temperature limit ({max_temp_limit_c}°C) reached at {t}s")

        # Update
        T_current = T_new
        t += time_step

    # 4. Steady State Calculation (Analytical Check)
    # At steady state, P_gen = P_diss
    # I^2 * R_amb * (1 + alpha*(T_ss - T_amb)) = (T_ss - T_amb) / R_th
    # Let delta_T = T_ss - T_amb
    # I^2 * R_amb * (1 + alpha * delta_T) = delta_T / R_th
    # I^2 * R_amb + I^2 * R_amb * alpha * delta_T = delta_T / R_th
    # I^2 * R_amb = delta_T * (1/R_th - I^2 * R_amb * alpha)
    # delta_T = (I^2 * R_amb) / (1/R_th - I^2 * R_amb * alpha)
    # Note: If denominator <= 0, thermal runaway occurs (heat gen grows faster than dissipation)

    numerator = P_initial
    denominator = (1.0 / R_th) - (P_initial * ALPHA_COPPER)
    
    if denominator <= 0:
        steady_state_temp = 999.0 # Thermal Runaway
        status = "runaway"
        warnings.append("WARNING: Thermal Runaway predicted! Cooling is insufficient for this current.")
    else:
        delta_T_ss = numerator / denominator
        steady_state_temp = ambient_temp_c + delta_T_ss
        status = "stable"
    
    # Check if steady state is crazy high
    if steady_state_temp > 300:
        steady_state_temp = 300 # Cap for UI display safety
        if status != "runaway":
             warnings.append("Projected steady-state temperature is extremely high (>300°C).")
             status = "critical"

    return {
        "steady_state_temp": round(steady_state_temp, 1),
        "final_sim_temp": round(T_current, 1),
        "time_to_limit": round(limit_reached_time, 1) if limit_reached_time else None,
        "thermal_resistance": round(R_th, 3),
        "thermal_mass": round(thermal_mass, 2),
        "surface_area_cm2": round(surface_area * 10000, 1), # m2 to cm2
        "initial_power_loss": round(P_initial, 1),
        "h_used": h,
        "h_description": h_desc,
        "status": status,
        "warnings": warnings,
        "curve_data": curve_data,
        "inputs": {
            "current": current_amp,
            "resistance": resistance_ohms,
            "ambient": ambient_temp_c,
            "limit": max_temp_limit_c
        }
    }

def get_convection_presets() -> Dict[str, Dict[str, Any]]:
    """Return available airflow presets."""
    return CONVECTION_PRESETS
