# test_interference.py
import math
import interference_calc as ic

# --- Test Data ---
test_geometry_solid = {
    'nom_diameter_mm': 50,
    'hub_od_mm': 100,
    'interference_mm': 0.05, # 50 microns
    'engagement_length_mm': 75,
    'shaft_id_mm': 0 # Specify solid shaft
}

test_geometry_hollow = {
    'nom_diameter_mm': 50,
    'hub_od_mm': 100,
    'interference_mm': 0.05,
    'engagement_length_mm': 75,
    'shaft_id_mm': 25 # Hollow shaft
}

test_materials_steel = {
    'hub': {
        'youngs_modulus_mpa': 200000, 'poisson_ratio': 0.3,
        'yield_strength_mpa': 350, 'coeff_thermal_exp_e-6_c': 12.0
    },
    'shaft': {
        'youngs_modulus_mpa': 200000, 'poisson_ratio': 0.3,
        'yield_strength_mpa': 450, 'coeff_thermal_exp_e-6_c': 12.0
    }
}

test_materials_al_hub_steel_shaft = {
     'hub': { # Aluminum
        'youngs_modulus_mpa': 70000, 'poisson_ratio': 0.33,
        'yield_strength_mpa': 150, 'coeff_thermal_exp_e-6_c': 23.0
    },
    'shaft': { # Steel
        'youngs_modulus_mpa': 200000, 'poisson_ratio': 0.3,
        'yield_strength_mpa': 450, 'coeff_thermal_exp_e-6_c': 12.0
    }
}


test_conditions_basic = {
    'coeff_friction': 0.15,
    'reference_temp_c': 20,
    'operating_temp_c': 20, # Same as ref initially
    'assembly_clearance_mm': 0.01
}

test_conditions_hot = {
    'coeff_friction': 0.15,
    'reference_temp_c': 20,
    'operating_temp_c': 100, # Operating hotter
    'assembly_clearance_mm': 0.01
}


# --- Test Functions ---

def test_pressure_solid():
    p_pa = ic.calculate_pressure(test_geometry_solid, test_materials_steel)
    p_mpa = p_pa / 1e6
    # Expected value based on online calculators / manual calc approx
    # δ = p*D/E * [ ( (Do/D)^2+1 )/ ( (Do/D)^2-1 ) + nu_h + 1 - nu_s ]  (for same material)
    # δ = p*D/E * [ (2^2+1)/(2^2-1) + 0.3 + 1 - 0.3 ] = p*D/E * [ 5/3 + 1 ] = p*D/E * 8/3
    # p = δ * E * 3 / (D * 8) = 0.05e-3 * 200e9 * 3 / (50e-3 * 8) = 30e6 / 0.4 = 75e6 Pa = 75 MPa
    print(f"Test Pressure (Solid): {p_mpa:.2f} MPa")
    assert abs(p_mpa - 75.0) < 1.0 # Check within reasonable tolerance

def test_pressure_hollow():
     p_pa = ic.calculate_pressure(test_geometry_hollow, test_materials_steel)
     p_mpa = p_pa / 1e6
     # Expect slightly lower pressure for hollow shaft as it's less stiff
     print(f"Test Pressure (Hollow): {p_mpa:.2f} MPa")
     assert p_mpa > 0 and p_mpa < 75.0

def test_stresses_solid():
    p_pa = ic.calculate_pressure(test_geometry_solid, test_materials_steel)
    stresses = ic.calculate_stresses(p_pa, test_geometry_solid, test_materials_steel)
    # Hub tangential stress: p * (Do^2+D^2)/(Do^2-D^2) = 75 * (100^2+50^2)/(100^2-50^2) = 75 * 12500 / 7500 = 75 * 5/3 = 125 MPa
    # Hub radial stress: -p = -75 MPa
    # Hub VM: sqrt(125^2 - 125*(-75) + (-75)^2) = sqrt(15625 + 9375 + 5625) = sqrt(30625) = 175 MPa
    # Shaft tangential/radial: -p = -75 MPa
    # Shaft VM: p = 75 MPa
    print(f"Test Stresses Hub (Solid): SigT={stresses['hub']['tangential_mpa']:.1f}, SigR={stresses['hub']['radial_mpa']:.1f}, SigVM={stresses['hub']['von_mises_mpa']:.1f}")
    print(f"Test Stresses Shaft (Solid): SigT={stresses['shaft']['tangential_mpa']:.1f}, SigR={stresses['shaft']['radial_mpa']:.1f}, SigVM={stresses['shaft']['von_mises_mpa']:.1f}")
    assert abs(stresses['hub']['tangential_mpa'] - 125.0) < 1.0
    assert abs(stresses['hub']['radial_mpa'] - (-75.0)) < 1.0
    assert abs(stresses['hub']['von_mises_mpa'] - 175.0) < 1.0
    assert abs(stresses['shaft']['tangential_mpa'] - (-75.0)) < 1.0
    assert abs(stresses['shaft']['radial_mpa'] - (-75.0)) < 1.0
    assert abs(stresses['shaft']['von_mises_mpa'] - 75.0) < 1.0
    assert stresses['hub']['safety_factor'] == 350 / stresses['hub']['von_mises_mpa']
    assert stresses['shaft']['safety_factor'] == 450 / stresses['shaft']['von_mises_mpa']


def test_torque_force_solid():
    p_pa = ic.calculate_pressure(test_geometry_solid, test_materials_steel)
    tf = ic.calculate_torque_force(p_pa, test_geometry_solid, test_conditions_basic)
    # T = p * pi * D^2 * L * mu / 2
    # T = 75e6 * pi * (50e-3)^2 * 75e-3 * 0.15 / 2
    # T = 75e6 * 3.14159 * 2500e-6 * 75e-3 * 0.15 / 2
    # T = 75 * 3.14159 * 2.5 * 0.075 * 0.15 / 2 = 3298 Nm
    # F = p * pi * D * L * mu
    # F = 75e6 * pi * 50e-3 * 75e-3 * 0.15 = 132537 N = 132.5 kN
    print(f"Test Torque/Force (Solid): T={tf['torque_nm']:.1f} Nm, F={tf['force_kn']:.1f} kN")
    assert abs(tf['torque_nm'] - 3298.7) < 10.0
    assert abs(tf['force_kn'] - 131.9) < 1.0

def test_assembly_temps_solid():
    temps = ic.calculate_assembly_temps(test_geometry_solid, test_materials_steel, test_conditions_basic)
    # Heat Hub: deltaT = (interf + clear) / (alpha * D)
    # deltaT = (0.05 + 0.01) / (12.0e-6 * 50) = 0.06 / 600e-6 = 100 C
    # T_hub = 20 + 100 = 120 C
    # Cool Shaft: deltaT = -(interf + clear) / (alpha * D)
    # deltaT = -100 C
    # T_shaft = 20 - 100 = -80 C
    print(f"Test Assembly Temps (Solid): Hub={temps['req_hub_heating_temp_c']:.1f} C, Shaft={temps['req_shaft_cooling_temp_c']:.1f} C")
    assert abs(temps['req_hub_heating_temp_c'] - 120.0) < 1.0
    assert abs(temps['req_shaft_cooling_temp_c'] - (-80.0)) < 1.0

def test_operational_pressure_hot_same_material():
    # Same material, interference shouldn't change much with temp
    p_op_pa = ic.calculate_operational_pressure(test_geometry_solid, test_materials_steel, test_conditions_hot)
    p_ref_pa = ic.calculate_pressure(test_geometry_solid, test_materials_steel)
    print(f"Test Op Pressure (Hot, Steel/Steel): Pop={p_op_pa/1e6:.2f} MPa, Pref={p_ref_pa/1e6:.2f} MPa")
    assert abs(p_op_pa - p_ref_pa) < 1e4 # Should be very close (small numerical diff possible)

def test_operational_pressure_hot_different_material():
    # Al hub (expands more) on steel shaft. Heating should REDUCE interference/pressure.
    p_op_pa = ic.calculate_operational_pressure(test_geometry_solid, test_materials_al_hub_steel_shaft, test_conditions_hot)
    p_ref_pa = ic.calculate_pressure(test_geometry_solid, test_materials_al_hub_steel_shaft)
    print(f"Test Op Pressure (Hot, Al/Steel): Pop={p_op_pa/1e6:.2f} MPa, Pref={p_ref_pa/1e6:.2f} MPa")
    assert p_op_pa < p_ref_pa # Pressure must decrease
    assert p_op_pa > 0 # Should still have some pressure

def test_full_calculation_solid():
    results = ic.calculate_interference_fit(test_geometry_solid, test_materials_steel, test_conditions_basic)
    assert results['error'] is None
    assert 'reference_conditions' in results
    assert 'operating_conditions' in results
    assert 'assembly' in results
    assert abs(results['reference_conditions']['pressure_mpa'] - 75.0) < 1.0
    assert abs(results['operating_conditions']['max_torque_nm'] - 3298.7) < 10.0
    print("Full calculation (Solid, Basic Cond) ran successfully.")

def test_full_calculation_hot_diff_material():
    results = ic.calculate_interference_fit(test_geometry_solid, test_materials_al_hub_steel_shaft, test_conditions_hot)
    assert results['error'] is None
    assert results['operating_conditions']['pressure_mpa'] < results['reference_conditions']['pressure_mpa']
    assert results['operating_conditions']['max_torque_nm'] < ic.calculate_torque_force(results['reference_conditions']['pressure_mpa']*1e6, test_geometry_solid, test_conditions_hot)['torque_nm'] # Torque should also decrease
    print("Full calculation (Solid, Hot Cond, Al/Steel) ran successfully.")

def test_validation_error():
    bad_geom = test_geometry_solid.copy()
    bad_geom['hub_od_mm'] = 40 # Less than nominal diameter
    results = ic.calculate_interference_fit(bad_geom, test_materials_steel, test_conditions_basic)
    assert results['error'] is not None
    assert "Hub OD > Nom. Diameter" in results['error']
    print("Validation error test passed.")


# --- Run Tests ---
if __name__ == "__main__":
    test_pressure_solid()
    test_pressure_hollow()
    test_stresses_solid()
    test_torque_force_solid()
    test_assembly_temps_solid()
    test_operational_pressure_hot_same_material()
    test_operational_pressure_hot_different_material()
    test_full_calculation_solid()
    test_full_calculation_hot_diff_material()
    test_validation_error()
    print("\nAll interference fit tests passed (within tolerance).")