import math
import sys

# --- Constants ---
LARGE_SAFETY_FACTOR = 1e9  # Represents a very safe condition if stress is zero/negligible

# --- Helper Functions ---
def _validate_inputs(geometry, materials, conditions):
    """ Basic validation for physical sensibility """
    D = geometry['nom_diameter_mm']
    Do = geometry['hub_od_mm']
    Di = geometry.get('shaft_id_mm', 0)  # Default to solid shaft
    interference = geometry['interference_mm']
    L = geometry['engagement_length_mm']

    if not (D > 0 and Do > D and L > 0 and interference >= 0):
        raise ValueError("Invalid geometry: Diameters/Length must be positive, Hub OD > Nom. Diameter, Interference >= 0.")
    if Di >= D:
        raise ValueError("Invalid geometry: Shaft ID must be less than nominal diameter.")

    if not all(k in materials.get('hub', {}) for k in ['youngs_modulus_mpa', 'poisson_ratio']):
         raise ValueError("Hub material properties (E, nu) are missing.")
    if not all(k in materials.get('shaft', {}) for k in ['youngs_modulus_mpa', 'poisson_ratio']):
        raise ValueError("Shaft material properties (E, nu) are missing.")

    return True

def calculate_pressure(geometry, materials, conditions):
    """ Calculates interface pressure based on geometry, materials, interference, and optionally a thin-wall assumption """
    D = geometry['nom_diameter_mm'] * 1e-3  # m
    Do = geometry['hub_od_mm'] * 1e-3         # m
    Di = geometry.get('shaft_id_mm', 0) * 1e-3  # m (Allow for hollow shaft)
    interference = geometry['interference_mm'] * 1e-3  # m

    E_h = materials['hub']['youngs_modulus_mpa'] * 1e6  # Pa
    nu_h = materials['hub']['poisson_ratio']
    E_s = materials['shaft']['youngs_modulus_mpa'] * 1e6  # Pa
    nu_s = materials['shaft']['poisson_ratio']

    if E_h <= 0 or E_s <= 0:
        raise ValueError("Young's Modulus must be positive.")
    if interference == 0:
        return 0.0  # No interference means no pressure

    # --- Determine hub geometry factor ---
    if conditions.get("thin_wall", False):
        if (Do - D) == 0:
            raise ValueError("Calculation error: Hub thickness is zero for thin-wall approximation.")
        term_hub_geom = D / (Do - D)
    else:
        if (Do**2 - D**2) == 0:
            raise ValueError("Calculation error: Hub OD cannot equal Nominal Diameter.")
        term_hub_geom = (Do**2 + D**2) / (Do**2 - D**2)

    # Shaft geometry factor
    if Di == 0:  # Solid shaft
        term_shaft_geom = 1.0
    else:  # Hollow shaft
        if (D**2 - Di**2) == 0:
            raise ValueError("Calculation error: Shaft Diameter cannot equal Shaft ID for hollow shaft.")
        term_shaft_geom = (D**2 + Di**2) / (D**2 - Di**2)

    if Di == 0:  # Solid shaft
        denominator = (D / E_h) * (term_hub_geom + nu_h) + (D / E_s) * (1.0 - nu_s)
    else:  # Hollow shaft
        denominator = (D / E_h) * (term_hub_geom + nu_h) + (D / E_s) * (term_shaft_geom - nu_s)

    if denominator <= 1e-14:
        raise ValueError("Calculation error: Denominator is zero or near-zero in pressure calculation.")

    pressure_pa = interference / denominator
    return pressure_pa  # Pa

def calculate_stresses(pressure_pa, geometry, materials):
    """ Calculates stresses in hub and shaft using Lame's equations """
    D = geometry['nom_diameter_mm'] * 1e-3  # m
    Do = geometry['hub_od_mm'] * 1e-3         # m
    Di = geometry.get('shaft_id_mm', 0) * 1e-3  # m

    stresses = {
        'hub': {'tangential_mpa': 0, 'radial_mpa': 0, 'von_mises_mpa': 0, 'safety_factor': None},
        'shaft': {'tangential_mpa': 0, 'radial_mpa': 0, 'von_mises_mpa': 0, 'safety_factor': None}
    }
    if pressure_pa == 0:
        stresses['hub']['safety_factor'] = LARGE_SAFETY_FACTOR
        stresses['shaft']['safety_factor'] = LARGE_SAFETY_FACTOR
        return stresses

    if (Do**2 - D**2) == 0:
         raise ValueError("Calculation error: Hub OD cannot equal Nominal Diameter.")
    sigma_th_pa = pressure_pa * (Do**2 + D**2) / (Do**2 - D**2)
    sigma_rh_pa = -pressure_pa
    sigma_vm_h_pa = math.sqrt(sigma_th_pa**2 - sigma_th_pa * sigma_rh_pa + sigma_rh_pa**2)

    stresses['hub']['tangential_mpa'] = sigma_th_pa / 1e6
    stresses['hub']['radial_mpa'] = sigma_rh_pa / 1e6
    stresses['hub']['von_mises_mpa'] = sigma_vm_h_pa / 1e6

    if Di == 0:  # Solid Shaft
        sigma_ts_pa = -pressure_pa
        sigma_rs_pa = -pressure_pa
        sigma_vm_s_pa = pressure_pa
    else:
         if (D**2 - Di**2) == 0:
             raise ValueError("Calculation error: Shaft Diameter cannot equal Shaft ID for hollow shaft.")
         sigma_ts_pa = -pressure_pa * (D**2 + Di**2) / (D**2 - Di**2)
         sigma_rs_pa = -pressure_pa
         sigma_vm_s_pa = math.sqrt(sigma_ts_pa**2 - sigma_ts_pa * sigma_rs_pa + sigma_rs_pa**2)

    stresses['shaft']['tangential_mpa'] = sigma_ts_pa / 1e6
    stresses['shaft']['radial_mpa'] = sigma_rs_pa / 1e6
    stresses['shaft']['von_mises_mpa'] = sigma_vm_s_pa / 1e6

    Sy_h_mpa = materials['hub'].get('yield_strength_mpa')
    Sy_s_mpa = materials['shaft'].get('yield_strength_mpa')

    if Sy_h_mpa is not None and Sy_h_mpa > 0:
        if stresses['hub']['von_mises_mpa'] <= 1e-6:
             stresses['hub']['safety_factor'] = LARGE_SAFETY_FACTOR
        else:
             stresses['hub']['safety_factor'] = Sy_h_mpa / stresses['hub']['von_mises_mpa']
    else:
        stresses['hub']['safety_factor'] = None

    if Sy_s_mpa is not None and Sy_s_mpa > 0:
         if stresses['shaft']['von_mises_mpa'] <= 1e-6:
             stresses['shaft']['safety_factor'] = LARGE_SAFETY_FACTOR
         else:
            stresses['shaft']['safety_factor'] = Sy_s_mpa / stresses['shaft']['von_mises_mpa']
    else:
        stresses['shaft']['safety_factor'] = None

    return stresses

def calculate_torque_force(pressure_pa, geometry, conditions):
    """ Calculates maximum transmissible torque and axial force """
    D = geometry['nom_diameter_mm'] * 1e-3  # m
    L = geometry['engagement_length_mm'] * 1e-3  # m
    mu = conditions['coeff_friction']

    if pressure_pa <= 0 or mu <= 0:
        return {'torque_nm': 0, 'force_kn': 0}

    contact_area = math.pi * D * L
    effective_pressure = max(0, pressure_pa)
    normal_force = effective_pressure * contact_area

    max_torque_nm = normal_force * mu * (D / 2)
    max_force_n = normal_force * mu

    return {'torque_nm': max_torque_nm, 'force_kn': max_force_n / 1000.0}

def calculate_assembly_temps(geometry, materials, conditions):
    """ Calculates required temperature change for assembly/disassembly """
    D = geometry['nom_diameter_mm']  # mm
    interference = geometry['interference_mm']
    clearance = conditions.get('assembly_clearance_mm', 0.01)

    alpha_h = materials['hub'].get('coeff_thermal_exp_e-6_c')
    alpha_s = materials['shaft'].get('coeff_thermal_exp_e-6_c')
    ref_temp_c = conditions.get('reference_temp_c', 20)

    required_delta_dim = interference + clearance

    temps = {'req_hub_heating_temp_c': None, 'req_shaft_cooling_temp_c': None}
    if alpha_h is not None and alpha_h > 1e-9:
        delta_T_h = required_delta_dim / (alpha_h * 1e-6 * D)
        temps['req_hub_heating_temp_c'] = ref_temp_c + delta_T_h
    else:
        temps['req_hub_heating_temp_c'] = None

    if alpha_s is not None and alpha_s > 1e-9:
        delta_T_s = -required_delta_dim / (alpha_s * 1e-6 * D)
        temps['req_shaft_cooling_temp_c'] = ref_temp_c + delta_T_s
    else:
        temps['req_shaft_cooling_temp_c'] = None

    return temps

def calculate_operational_pressure(geometry, materials, conditions):
    """ Calculates interface pressure at operating temperature """
    D_mm = geometry['nom_diameter_mm']
    interference_initial_mm = geometry['interference_mm']

    alpha_h = materials['hub'].get('coeff_thermal_exp_e-6_c')
    alpha_s = materials['shaft'].get('coeff_thermal_exp_e-6_c')
    ref_temp_c = conditions.get('reference_temp_c', 20)
    op_temp_c = conditions.get('operating_temp_c', ref_temp_c)

    delta_T_op = op_temp_c - ref_temp_c

    delta_interference_thermal_mm = 0
    if delta_T_op != 0 and alpha_h is not None and alpha_s is not None:
         delta_interference_thermal_mm = (alpha_h - alpha_s) * 1e-6 * D_mm * delta_T_op

    interference_op_mm = interference_initial_mm - delta_interference_thermal_mm

    if interference_op_mm <= 1e-9:
         return 0.0

    geometry_op = geometry.copy()
    geometry_op['interference_mm'] = interference_op_mm

    return calculate_pressure(geometry_op, materials, conditions)

def calculate_interference_fit(geometry_js, materials_js, conditions_js):
    """
    Main function for calculating torque transfer.
    Accepts JsProxy objects; converts them and returns a dict of results.
    """
    try:
        geometry = geometry_js.to_py()
        materials = materials_js.to_py()
        conditions = conditions_js.to_py()
        _validate_inputs(geometry, materials, conditions)

        pressure_ref_pa = calculate_pressure(geometry, materials, conditions)
        pressure_ref_mpa = pressure_ref_pa / 1e6
        stresses_ref = calculate_stresses(pressure_ref_pa, geometry, materials)
        pressure_op_pa = calculate_operational_pressure(geometry, materials, conditions)
        pressure_op_mpa = pressure_op_pa / 1e6
        stresses_op = calculate_stresses(pressure_op_pa, geometry, materials)
        transmissibles = calculate_torque_force(max(0, pressure_op_pa), geometry, conditions)
        assembly_temps = calculate_assembly_temps(geometry, materials, conditions)

        results = {
            "inputs": {
                "geometry": geometry,
                "materials": materials,
                "conditions": conditions
            },
            "operating_conditions": {
                 "pressure_mpa": pressure_op_mpa,
                 "hub_stress_tangential_mpa": stresses_op['hub']['tangential_mpa'],
                 "hub_stress_radial_mpa": stresses_op['hub']['radial_mpa'],
                 "hub_stress_von_mises_mpa": stresses_op['hub']['von_mises_mpa'],
                 "hub_safety_factor": stresses_op['hub']['safety_factor'],
                 "shaft_stress_tangential_mpa": stresses_op['shaft']['tangential_mpa'],
                 "shaft_stress_radial_mpa": stresses_op['shaft']['radial_mpa'],
                 "shaft_stress_von_mises_mpa": stresses_op['shaft']['von_mises_mpa'],
                 "shaft_safety_factor": stresses_op['shaft']['safety_factor'],
                 "max_torque_nm": transmissibles['torque_nm'],
                 "max_axial_force_kn": transmissibles['force_kn']
            },
            "reference_conditions": {
                "pressure_mpa": pressure_ref_mpa,
                "hub_stress_tangential_mpa": stresses_ref['hub']['tangential_mpa'],
                "hub_stress_radial_mpa": stresses_ref['hub']['radial_mpa'],
                "hub_stress_von_mises_mpa": stresses_ref['hub']['von_mises_mpa'],
                "hub_safety_factor": stresses_ref['hub']['safety_factor'],
                "shaft_stress_tangential_mpa": stresses_ref['shaft']['tangential_mpa'],
                "shaft_stress_radial_mpa": stresses_ref['shaft']['radial_mpa'],
                "shaft_stress_von_mises_mpa": stresses_ref['shaft']['von_mises_mpa'],
                "shaft_safety_factor": stresses_ref['shaft']['safety_factor']
            },
            "assembly": {
                 "required_hub_heating_temp_c": assembly_temps['req_hub_heating_temp_c'],
                 "required_shaft_cooling_temp_c": assembly_temps['req_shaft_cooling_temp_c'],
                 "assembly_clearance_mm": conditions.get('assembly_clearance_mm', 0.01),
                 "reference_temp_c": conditions.get('reference_temp_c', 20)
            },
            "error": None
        }
        return results

    except ValueError as e:
        print(f"Calculation ValueError: {e}")
        return {"error": str(e)}
    except TypeError as e:
        print(f"Calculation TypeError: {e}")
        return {"error": f"A type error occurred during calculation: {e}"}
    except Exception as e:
        print(f"Unexpected Error during calculation: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"An unexpected error occurred: {e}"}
