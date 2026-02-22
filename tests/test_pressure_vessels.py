import math

import pytest

from pycalcs import pressure_vessels


def test_pressure_vessel_cylinder_nominal():
    result = pressure_vessels.analyze_pressure_vessel(
        geometry="cylinder",
        pressure_mpa=2.0,
        diameter_mm=1000.0,
        thickness_mm=10.0,
        allowable_stress_mpa=200.0,
        safety_factor=2.0,
        joint_efficiency=1.0,
        corrosion_allowance_mm=0.0,
    )

    assert result["hoop_stress_mpa"] == pytest.approx(100.0)
    assert result["longitudinal_stress_mpa"] == pytest.approx(50.0)
    assert result["von_mises_stress_mpa"] == pytest.approx(math.sqrt(7500.0))
    assert result["required_thickness_mm"] == pytest.approx(10.0)
    assert result["utilization"] == pytest.approx(math.sqrt(7500.0) / 100.0)
    assert result["thin_wall_ratio"] == pytest.approx(0.02)
    assert result["status"] == "acceptable"


def test_pressure_vessel_sphere_nominal():
    result = pressure_vessels.analyze_pressure_vessel(
        geometry="sphere",
        pressure_mpa=2.0,
        diameter_mm=1000.0,
        thickness_mm=10.0,
        allowable_stress_mpa=200.0,
        safety_factor=2.0,
        joint_efficiency=1.0,
        corrosion_allowance_mm=0.0,
    )

    assert result["hoop_stress_mpa"] == pytest.approx(50.0)
    assert result["longitudinal_stress_mpa"] == pytest.approx(50.0)
    assert result["von_mises_stress_mpa"] == pytest.approx(50.0)
    assert result["required_thickness_mm"] == pytest.approx(5.0)
    assert result["utilization"] == pytest.approx(0.5)
    assert result["thin_wall_ratio"] == pytest.approx(0.02)


def test_pressure_vessel_invalid_efficiency():
    with pytest.raises(ValueError):
        pressure_vessels.analyze_pressure_vessel(
            geometry="cylinder",
            pressure_mpa=2.0,
            diameter_mm=1000.0,
            thickness_mm=10.0,
            allowable_stress_mpa=200.0,
            safety_factor=2.0,
            joint_efficiency=1.2,
            corrosion_allowance_mm=0.0,
        )
