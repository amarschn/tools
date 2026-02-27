"""
Energy density and vehicle energy storage calculations.
"""

from __future__ import annotations

# Database of energy storage options
ENERGY_SOURCES = {
    "gasoline": {
        "gravimetric_density_wh_kg": 12200,
        "volumetric_density_wh_l": 8800,
        "conversion_efficiency": 0.3,
        "container_weight_fraction": 0.1,
        "container_volume_fraction": 0.1,
        "type": "fuel",
        "name": "Gasoline (ICE)"
    },
    "diesel": {
        "gravimetric_density_wh_kg": 11900,
        "volumetric_density_wh_l": 10000,
        "conversion_efficiency": 0.4,
        "container_weight_fraction": 0.1,
        "container_volume_fraction": 0.1,
        "type": "fuel",
        "name": "Diesel (ICE)"
    },
    "hydrogen_700bar": {
        "gravimetric_density_wh_kg": 33300,
        "volumetric_density_wh_l": 1300,
        "conversion_efficiency": 0.5,
        "container_weight_fraction": 0.9, 
        "container_volume_fraction": 0.4,
        "type": "fuel",
        "name": "Hydrogen (700 bar)"
    },
    "li_ion_nmc": {
        "gravimetric_density_wh_kg": 250,
        "volumetric_density_wh_l": 600,
        "conversion_efficiency": 0.9,
        "container_weight_fraction": 0.3, 
        "container_volume_fraction": 0.3,
        "type": "battery",
        "name": "Li-Ion NMC Battery"
    },
    "lfp_battery": {
        "gravimetric_density_wh_kg": 160,
        "volumetric_density_wh_l": 350,
        "conversion_efficiency": 0.9,
        "container_weight_fraction": 0.3,
        "container_volume_fraction": 0.3,
        "type": "battery",
        "name": "LFP Battery"
    },
    "solid_state": {
        "gravimetric_density_wh_kg": 400,
        "volumetric_density_wh_l": 1000,
        "conversion_efficiency": 0.9,
        "container_weight_fraction": 0.2,
        "container_volume_fraction": 0.2,
        "type": "battery",
        "name": "Solid State Battery"
    },
    "jet_a": {
        "gravimetric_density_wh_kg": 11950,
        "volumetric_density_wh_l": 9600,
        "conversion_efficiency": 0.35,
        "container_weight_fraction": 0.05,
        "container_volume_fraction": 0.05,
        "type": "fuel",
        "name": "Jet A Fuel"
    }
}

VEHICLE_TYPES = {
    "bicycle": {
        "energy_consumption_wh_km": 15,
        "target_range_km": 50,
        "name": "E-Bike"
    },
    "commuter_car": {
        "energy_consumption_wh_km": 150,
        "target_range_km": 400,
        "name": "Compact Commuter Car"
    },
    "suv": {
        "energy_consumption_wh_km": 250,
        "target_range_km": 500,
        "name": "Large SUV"
    },
    "semi_truck": {
        "energy_consumption_wh_km": 1500,
        "target_range_km": 800,
        "name": "Class 8 Semi Truck"
    },
    "small_aircraft": {
        "energy_consumption_wh_km": 400,
        "target_range_km": 1000,
        "name": "4-Seat Aircraft"
    },
    "custom": {
        "energy_consumption_wh_km": 150,
        "target_range_km": 400,
        "name": "Custom Vehicle"
    }
}

def analyze_energy_storage(
    vehicle_type: str,
    custom_consumption_wh_km: float,
    target_range_km: float,
    energy_source_1: str,
    energy_source_2: str
) -> dict:
    r"""
    Calculates mass and volume requirements for different energy storage systems to achieve a target range.
    
    Compares two selected energy sources (fuels or batteries) for a given vehicle type.
    It takes into account the efficiency of the powertrain and the overhead weight/volume
    of the storage containers (tanks or battery packs).

    ---Parameters---
    vehicle_type : str
        Type of vehicle, determines default energy consumption (Wh/km).
    custom_consumption_wh_km : float
        Energy consumption at the wheels/propeller in Wh per km (used if vehicle_type is 'custom').
    target_range_km : float
        Desired range of the vehicle in km.
    energy_source_1 : str
        First energy source to evaluate (e.g., 'li_ion_nmc', 'gasoline').
    energy_source_2 : str
        Second energy source to evaluate for comparison.
        
    ---Returns---
    useful_energy_kwh : float
        Total energy required at the wheels/propeller for the full range (kWh).
    source1_total_energy_kwh : float
        Total chemical/electrical energy stored for source 1 (kWh).
    source1_total_mass_kg : float
        Total system mass for source 1 including container (kg).
    source1_total_volume_l : float
        Total system volume for source 1 including container (L).
    source1_system_gravimetric_wh_kg : float
        Effective system-level gravimetric energy density for source 1 (Wh/kg).
    source1_system_volumetric_wh_l : float
        Effective system-level volumetric energy density for source 1 (Wh/L).
    source2_total_energy_kwh : float
        Total chemical/electrical energy stored for source 2 (kWh).
    source2_total_mass_kg : float
        Total system mass for source 2 including container (kg).
    source2_total_volume_l : float
        Total system volume for source 2 including container (L).
    source2_system_gravimetric_wh_kg : float
        Effective system-level gravimetric energy density for source 2 (Wh/kg).
    source2_system_volumetric_wh_l : float
        Effective system-level volumetric energy density for source 2 (Wh/L).
        
    ---LaTeX---
    E_{useful} = C_{wheel} \times R
    E_{stored} = \frac{E_{useful}}{\eta}
    M_{media} = \frac{E_{stored}}{\rho_{g}}
    M_{total} = \frac{M_{media}}{1 - f_{wm}}
    V_{media} = \frac{E_{stored}}{\rho_{v}}
    V_{total} = \frac{V_{media}}{1 - f_{wv}}
    \rho_{sys,g} = \frac{E_{useful}}{M_{total}}
    \rho_{sys,v} = \frac{E_{useful}}{V_{total}}
    """
    
    if vehicle_type == "custom":
        consumption = custom_consumption_wh_km
    else:
        if vehicle_type not in VEHICLE_TYPES:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")
        consumption = VEHICLE_TYPES[vehicle_type]["energy_consumption_wh_km"]
        
    if target_range_km <= 0:
        raise ValueError("Target range must be positive.")
    if consumption <= 0:
        raise ValueError("Energy consumption must be positive.")
        
    if energy_source_1 not in ENERGY_SOURCES:
        raise ValueError(f"Unknown energy source 1: {energy_source_1}")
    if energy_source_2 not in ENERGY_SOURCES:
        raise ValueError(f"Unknown energy source 2: {energy_source_2}")
        
    useful_energy_wh = consumption * target_range_km
    useful_energy_kwh = useful_energy_wh / 1000.0
    
    def _calc_source(source_key):
        src = ENERGY_SOURCES[source_key]
        eta = src["conversion_efficiency"]
        f_wm = src["container_weight_fraction"]
        f_wv = src["container_volume_fraction"]
        rho_g = src["gravimetric_density_wh_kg"]
        rho_v = src["volumetric_density_wh_l"]
        
        stored_energy_wh = useful_energy_wh / eta
        media_mass = stored_energy_wh / rho_g
        total_mass = media_mass / (1 - f_wm)
        
        media_volume = stored_energy_wh / rho_v
        total_volume = media_volume / (1 - f_wv)
        
        sys_rho_g = useful_energy_wh / total_mass
        sys_rho_v = useful_energy_wh / total_volume
        
        return {
            "total_energy_kwh": stored_energy_wh / 1000.0,
            "total_mass_kg": total_mass,
            "total_volume_l": total_volume,
            "system_gravimetric_wh_kg": sys_rho_g,
            "system_volumetric_wh_l": sys_rho_v,
            "subst_stored": f"E_{{stored}} = \\frac{{{useful_energy_kwh:.1f} \\text{{ kWh}}}}{{{eta:.2f}}} = {stored_energy_wh/1000.0:.1f} \\text{{ kWh}}",
            "subst_mass": f"M_{{total}} = \\frac{{{media_mass:.1f} \\text{{ kg}}}}{{1 - {f_wm:.2f}}} = {total_mass:.1f} \\text{{ kg}}",
            "subst_volume": f"V_{{total}} = \\frac{{{media_volume:.1f} \\text{{ L}}}}{{1 - {f_wv:.2f}}} = {total_volume:.1f} \\text{{ L}}"
        }

    s1 = _calc_source(energy_source_1)
    s2 = _calc_source(energy_source_2)
    
    # Generate visualization data
    categories = [ENERGY_SOURCES[energy_source_1]["name"], ENERGY_SOURCES[energy_source_2]["name"]]
    mass_data = [s1["total_mass_kg"], s2["total_mass_kg"]]
    vol_data = [s1["total_volume_l"], s2["total_volume_l"]]
    
    return {
        "useful_energy_kwh": useful_energy_kwh,
        "source1_total_energy_kwh": s1["total_energy_kwh"],
        "source1_total_mass_kg": s1["total_mass_kg"],
        "source1_total_volume_l": s1["total_volume_l"],
        "source1_system_gravimetric_wh_kg": s1["system_gravimetric_wh_kg"],
        "source1_system_volumetric_wh_l": s1["system_volumetric_wh_l"],
        "source2_total_energy_kwh": s2["total_energy_kwh"],
        "source2_total_mass_kg": s2["total_mass_kg"],
        "source2_total_volume_l": s2["total_volume_l"],
        "source2_system_gravimetric_wh_kg": s2["system_gravimetric_wh_kg"],
        "source2_system_volumetric_wh_l": s2["system_volumetric_wh_l"],
        
        "subst_useful_energy": f"E_{{useful}} = {consumption:.1f} \\text{{ Wh/km}} \\times {target_range_km:.1f} \\text{{ km}} = {useful_energy_kwh:.1f} \\text{{ kWh}}",
        "subst_source1_stored": s1["subst_stored"],
        "subst_source1_mass": s1["subst_mass"],
        "subst_source1_volume": s1["subst_volume"],
        "subst_source2_stored": s2["subst_stored"],
        "subst_source2_mass": s2["subst_mass"],
        "subst_source2_volume": s2["subst_volume"],
        
        "viz_categories": categories,
        "viz_mass_data": mass_data,
        "viz_vol_data": vol_data
    }
