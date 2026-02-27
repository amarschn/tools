import math

import pytest

from pycalcs.rotor_stress import calculate_rotor_hoop_stress


def test_solid_disk_center_hoop_matches_shigley():
    nu = 0.30
    rho = 7800.0
    ro_m = 0.10
    rpm = 6000.0
    omega = 2.0 * math.pi * rpm / 60.0

    results = calculate_rotor_hoop_stress(
        geometry_type="solid_disk",
        inner_radius_mm=0.0,
        outer_radius_mm=100.0,
        thickness_mm=12.0,
        density_kg_m3=rho,
        poisson_ratio=nu,
        speed_rpm=rpm,
        yield_strength_mpa=350.0,
        profile_points=201,
    )

    expected_mpa = ((3.0 + nu) / 8.0) * rho * omega**2 * ro_m**2 / 1e6
    assert results["max_hoop_stress_mpa"] == pytest.approx(expected_mpa, rel=1e-4)
    assert results["critical_radius_mm"] == pytest.approx(0.0, abs=1e-9)


def test_annular_disk_inner_hoop_matches_closed_form():
    nu = 0.30
    rho = 7800.0
    ri_m = 0.05
    ro_m = 0.10
    rpm = 6000.0
    omega = 2.0 * math.pi * rpm / 60.0

    results = calculate_rotor_hoop_stress(
        geometry_type="annular_disk",
        inner_radius_mm=50.0,
        outer_radius_mm=100.0,
        thickness_mm=10.0,
        density_kg_m3=rho,
        poisson_ratio=nu,
        speed_rpm=rpm,
        yield_strength_mpa=350.0,
        profile_points=401,
    )

    expected_inner_mpa = (
        (rho * omega**2) / 4.0 * ((3.0 + nu) * ro_m**2 + (1.0 - nu) * ri_m**2)
    ) / 1e6

    assert results["max_hoop_stress_mpa"] == pytest.approx(expected_inner_mpa, rel=2e-3)
    assert results["critical_radius_mm"] == pytest.approx(50.0, rel=1e-3)


def test_thin_ring_hoop_stress_constant_expression():
    rho = 7800.0
    ri_m = 0.07
    ro_m = 0.08
    rm_m = 0.5 * (ri_m + ro_m)
    rpm = 9000.0
    omega = 2.0 * math.pi * rpm / 60.0

    results = calculate_rotor_hoop_stress(
        geometry_type="thin_ring",
        inner_radius_mm=70.0,
        outer_radius_mm=80.0,
        thickness_mm=8.0,
        density_kg_m3=rho,
        poisson_ratio=0.30,
        speed_rpm=rpm,
        yield_strength_mpa=350.0,
    )

    expected_mpa = rho * omega**2 * rm_m**2 / 1e6
    assert results["max_hoop_stress_mpa"] == pytest.approx(expected_mpa, rel=1e-6)
    assert results["max_radial_stress_mpa"] == pytest.approx(0.0, abs=1e-12)


def test_invalid_geometry_raises_value_error():
    with pytest.raises(ValueError):
        calculate_rotor_hoop_stress(
            geometry_type="not-a-shape",
            inner_radius_mm=10.0,
            outer_radius_mm=20.0,
            thickness_mm=5.0,
            density_kg_m3=7800.0,
            poisson_ratio=0.30,
            speed_rpm=1000.0,
            yield_strength_mpa=350.0,
        )
