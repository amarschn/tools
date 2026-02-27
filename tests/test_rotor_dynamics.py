import pytest
import math
from pycalcs.rotor_dynamics import calculate_rotor_balance, ISO_GRADES

def test_permissible_unbalance():
    # 10 kg rotor, 3000 RPM, G2.5
    # omega = 3000 * pi / 30 = 314.159 rad/s
    # e_per = 2.5 / 314.159 = 0.0079577 mm = 7.9577 um
    # U_per = 10 * 7.9577 = 79.577 g*mm
    res = calculate_rotor_balance(
        rotor_mass_kg=10.0,
        operating_rpm=3000.0,
        iso_grade="G2.5",
        measured_unbalance_g_mm=0.0,
        correction_radius_mm=50.0
    )
    
    assert res["specific_unbalance_e_per_um"] == pytest.approx(7.957, rel=0.01)
    assert res["permissible_unbalance_g_mm"] == pytest.approx(79.57, rel=0.01)
    assert res["status"] == "info"
    assert res["utilization_percent"] == 0.0
    assert res["centrifugal_force_n"] == 0.0

def test_centrifugal_force_and_status():
    # 5 kg rotor, 6000 RPM, G6.3
    # Measured unbalance = 100 g*mm
    # Force = U * 1e-6 * omega^2 = 100e-6 * (6000*pi/30)^2 = 100e-6 * (628.3)^2 = 39.478 N
    # U_per = 1000 * 5 * (6.3 / 628.3) = 50.13 g*mm
    res = calculate_rotor_balance(
        rotor_mass_kg=5.0,
        operating_rpm=6000.0,
        iso_grade="G6.3",
        measured_unbalance_g_mm=100.0,
        correction_radius_mm=25.0
    )
    
    assert res["centrifugal_force_n"] == pytest.approx(39.47, rel=0.01)
    assert res["correction_mass_g"] == pytest.approx(4.0, rel=0.01) # 100 / 25
    assert res["permissible_unbalance_g_mm"] == pytest.approx(50.13, rel=0.01)
    assert res["utilization_percent"] > 100.0
    assert res["status"] == "unacceptable"
