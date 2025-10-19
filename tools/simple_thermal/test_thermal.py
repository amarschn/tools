import thermal_calc
import pytest

# --- Test Core Heat Transfer Functions ---

def test_conduction():
    q = thermal_calc.conduction_heat_transfer(k=50, A=0.01, T_hot=100, T_cold=25, L=0.005)
    assert abs(q - 7500) < 1

def test_natural_convection_coefficient():
    h = thermal_calc.natural_convection_coefficient('plate', 0.1, 80, 20, 'vertical')
    assert 2 < h < 15

def test_forced_convection_duct():
    # Test the new duct/channel flow correlation
    h = thermal_calc.forced_convection_coefficient(
        surface_type='duct', char_length=0.01, velocity=2.0, 
        T_surface=60, T_ambient=20, duct_length=0.1
    )
    assert 10 < h < 100 # Expect a higher h value for forced duct flow

def test_radiation():
    q = thermal_calc.radiation_heat_transfer(emissivity=0.9, A=0.1, T_surface=100, T_ambient=20)
    assert 0 < q < 100

# --- Test Geometry Calculations ---

def test_heatsink_geometry():
    dims = {"base_length": 0.1, "base_width": 0.08, "base_thickness": 0.005,
            "fin_height": 0.03, "fin_thickness": 0.001, "num_fins": 10}
    details = thermal_calc._get_geometry_details("heatsink", dims, "vertical")
    
    # s = (80 - 10*1) / (10-1) = 70 / 9 = 7.77mm
    assert abs(details["fin_spacing"] - 0.00777) < 1e-4
    # A = L*W + 2*N*L*H = 0.1*0.08 + 2*10*0.1*0.03 = 0.008 + 0.06 = 0.068
    assert abs(details["total_area"] - 0.068) < 1e-4
    # Lc_forced = 2*s = 15.55mm
    assert abs(details["char_length_forced"] - 0.01555) < 1e-4
    
    # Test edge case with invalid fins
    with pytest.raises(ValueError):
        dims_invalid = dims.copy()
        dims_invalid["fin_thickness"] = 0.01 
        thermal_calc._get_geometry_details("heatsink", dims_invalid, "vertical")


# --- Test Full Calculation Wrapper ---

def test_transient_plate():
    result = thermal_calc.thermal_calculation_py(
        calculation_mode="transient", geometry_type="plate", orientation="vertical",
        length=0.1, width_or_diameter=0.1, thickness=0.01,
        # Heatsink dims (not used)
        base_length=0, base_width=0, base_thickness=0, fin_height=0, fin_thickness=0, num_fins=0,
        # Material
        thermal_conductivity=50, density=7800, specific_heat=490, emissivity=0.8,
        # Conditions
        initial_temp=100, ambient_temp=20, air_velocity=0, heat_input=0,
        # Sim
        time_steps=50, total_time=1800
    )
    assert result["mode"] == "transient"
    assert "times" in result
    assert "final_temp" in result
    assert result["final_temp"] < 100
    assert result["temperatures"][0] > result["temperatures"][-1]

def test_steady_state_cylinder_forced():
    result = thermal_calc.thermal_calculation_py(
        calculation_mode="steady_state", geometry_type="cylinder", orientation="vertical",
        length=0.1, width_or_diameter=0.05, thickness=0,
        base_length=0, base_width=0, base_thickness=0, fin_height=0, fin_thickness=0, num_fins=0,
        thermal_conductivity=1, density=1, specific_heat=1, emissivity=0.3,
        initial_temp=0, ambient_temp=25, air_velocity=2.0, heat_input=15.0,
        time_steps=10, total_time=10
    )
    assert result["mode"] == "steady_state"
    assert "steady_state_temp" in result
    assert result["steady_state_temp"] > 25
    assert abs(result["final_q_output"] - result["heat_input"]) < 0.1
    assert result["convection_type"] == "forced"
    assert result["converged"] is True

def test_steady_state_heatsink_natural():
    result = thermal_calc.thermal_calculation_py(
        calculation_mode="steady_state", geometry_type="heatsink", orientation="vertical",
        length=0, width_or_diameter=0, thickness=0,
        base_length=0.1, base_width=0.08, base_thickness=0.005, 
        fin_height=0.03, fin_thickness=0.001, num_fins=10,
        thermal_conductivity=200, density=2700, specific_heat=900, emissivity=0.85,
        initial_temp=0, ambient_temp=20, air_velocity=0, heat_input=10.0
    )
    assert result["mode"] == "steady_state"
    assert "steady_state_temp" in result
    assert result["steady_state_temp"] > 20
    assert result["convection_type"] == "natural"
    assert abs(result["final_q_output"] - 10.0) < 0.1
    assert result["converged"] is True

def test_transient_heatsink_forced():
    result = thermal_calc.thermal_calculation_py(
        calculation_mode="transient", geometry_type="heatsink", orientation="vertical",
        length=0, width_or_diameter=0, thickness=0,
        base_length=0.1, base_width=0.08, base_thickness=0.005, 
        fin_height=0.03, fin_thickness=0.001, num_fins=10,
        thermal_conductivity=200, density=2700, specific_heat=900, emissivity=0.1,
        initial_temp=120, ambient_temp=25, air_velocity=3.0, heat_input=0,
        time_steps=100, total_time=600
    )
    assert result["mode"] == "transient"
    assert result["convection_type"] == "forced"
    assert "final_temp" in result
    assert result["final_temp"] < 120
    assert result["final_temp"] > 25
    assert "error" not in result

def test_invalid_heatsink_dims_wrapper():
    # Test that the wrapper catches the ValueError from the core logic
    result = thermal_calc.thermal_calculation_py(
        calculation_mode="steady_state", geometry_type="heatsink", orientation="vertical",
        length=0, width_or_diameter=0, thickness=0,
        base_length=0.1, base_width=0.08, base_thickness=0.005, 
        fin_height=0.03, fin_thickness=0.01, num_fins=10, # Invalid: 10 fins * 10mm > 80mm base
        thermal_conductivity=200, density=2700, specific_heat=900, emissivity=0.85,
        initial_temp=0, ambient_temp=20, air_velocity=0, heat_input=10.0
    )
    assert "error" in result
    assert "wider than the base width" in result["error"]