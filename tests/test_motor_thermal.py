"""
Tests for the Motor Thermal Estimator module.
"""

import pytest
from pycalcs import motor_thermal

def test_surface_area_calculation():
    # Cylinder d=50mm (0.05m), l=50mm (0.05m)
    # Side Area = pi * 0.05 * 0.05 = 0.00785 m^2
    # End Area = pi * (0.025)^2 = 0.00196 m^2
    # Total = 0.00981 m^2
    area = motor_thermal.calculate_surface_area(50, 50)
    assert area == pytest.approx(0.009817, rel=1e-3)

def test_thermal_mass_calculation():
    # 100g Copper, 100g Iron, 100g Al
    # 0.1 * 385 + 0.1 * 449 + 0.1 * 897 = 38.5 + 44.9 + 89.7 = 173.1 J/K
    mass = motor_thermal.calculate_thermal_mass(100, 100, 100)
    assert mass == pytest.approx(173.1, rel=1e-3)

def test_resistance_rise():
    # 1 Ohm at 20C, target 120C (delta 100)
    # R = 1 * (1 + 0.00393 * 100) = 1.393
    R = motor_thermal.calculate_resistance(1.0, 20.0, 120.0)
    assert R == pytest.approx(1.393, rel=1e-3)

def test_analyze_motor_thermal_basic():
    result = motor_thermal.analyze_motor_thermal(
        current_amp=10.0,
        resistance_ohms=0.1,
        diameter_mm=30.0,
        length_mm=40.0,
        mass_copper_g=50,
        mass_iron_g=100,
        mass_housing_g=30,
        ambient_temp_c=25.0,
        max_temp_limit_c=80.0,
        airflow_type="static_bench"
    )

    assert result["steady_state_temp"] > 25.0
    assert result["thermal_resistance"] > 0
    assert result["status"] in ["stable", "runaway", "critical"]
    assert "curve_data" in result
    assert len(result["curve_data"]) > 0

def test_thermal_runaway_detection():
    # Massive current, tiny motor, no cooling
    result = motor_thermal.analyze_motor_thermal(
        current_amp=200.0,
        resistance_ohms=0.1, # 4000W heat!
        diameter_mm=20.0,
        length_mm=20.0, # Tiny surface area
        mass_copper_g=10,
        mass_iron_g=20,
        mass_housing_g=10,
        airflow_type="enclosed_fuselage"
    )
    
    assert result["status"] == "runaway"
    assert any("WARNING: Thermal Runaway predicted!" in w for w in result["warnings"])

def test_custom_h_override():
    result = motor_thermal.analyze_motor_thermal(
        current_amp=10.0,
        resistance_ohms=0.1,
        diameter_mm=30,
        length_mm=40,
        mass_copper_g=50,
        mass_iron_g=100,
        mass_housing_g=30,
        custom_h=500.0 # Super cooling
    )
    
    assert result["h_used"] == 500.0
    assert result["h_description"] == "Custom User Value"
