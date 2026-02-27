import pytest
import math
from pycalcs.structural_resonance import calculate_structural_resonance

def test_rectangular_plate_fundamental():
    # Steel plate, 1m x 1m, 10mm thick, simply supported
    res = calculate_structural_resonance(
        geometry_type="plate",
        thickness_mm=10.0,
        length_mm=1000.0,
        width_mm=1000.0,
        diameter_mm=0.0,
        mode_1=1,
        mode_2=1,
        material="steel"
    )
    # E = 200e9, nu = 0.3, rho = 7850, h = 0.01, a=1, b=1
    # D = 200e9 * 0.01**3 / (12 * (1 - 0.3**2)) = 200e3 / 10.92 = 18315.018 N*m
    # rho_h = 78.5 kg/m^2
    # f_11 = (pi/2) * sqrt(18315.018 / 78.5) * (1/1^2 + 1/1^2)
    # f_11 = (pi/2) * 15.27 * 2 = pi * 15.27 ≈ 47.9 Hz
    
    assert res["natural_frequency_hz"] == pytest.approx(47.98, rel=0.01)
    assert res["geometry_display"] == "Rectangular Plate, Mode (1,1)"

def test_cylinder_breathing():
    # Steel cylinder, 1m diameter, 10mm thick
    res = calculate_structural_resonance(
        geometry_type="cylinder",
        thickness_mm=10.0,
        length_mm=0.0,
        width_mm=0.0,
        diameter_mm=1000.0,
        mode_1=0,
        mode_2=0,
        material="steel"
    )
    # R = 0.5m
    # wave_vel = sqrt(200e9 / 7850) ≈ 5047.5 m/s
    # f_0 = 5047.5 / (2*pi*0.5) ≈ 1606 Hz
    assert res["natural_frequency_hz"] == pytest.approx(1606.7, rel=0.01)
    assert res["geometry_display"] == "Cylindrical Ring, Breathing Mode (n=0)"

def test_cylinder_ovaling():
    # Aluminum cylinder, 100mm diameter, 2mm thick, n=2 (ovaling)
    res = calculate_structural_resonance(
        geometry_type="cylinder",
        thickness_mm=2.0,
        length_mm=0.0,
        width_mm=0.0,
        diameter_mm=100.0,
        mode_1=0,
        mode_2=2,
        material="aluminum"
    )
    # E = 69e9, rho = 2700, nu = 0.33, h = 0.002, R = 0.05
    # f_2 = ...
    assert res["natural_frequency_hz"] > 0
    assert "n=2" in res["geometry_display"]
