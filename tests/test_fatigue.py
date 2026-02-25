import math

import pytest

from pycalcs.fatigue import estimate_fatigue_life


def test_fatigue_life_nominal():
    # Use stress above endurance limit to test finite life calculation via Basquin.
    # alternating = 400 MPa, endurance_limit = 300 MPa, so Basquin equation applies.
    results = estimate_fatigue_life(
        max_stress_mpa=400.0,
        min_stress_mpa=-400.0,
        ultimate_strength_mpa=600.0,
        yield_strength_mpa=350.0,
        mean_stress_correction="goodman",
        endurance_limit_ratio=0.5,
        surface_factor=1.0,
        size_factor=1.0,
        reliability_factor=1.0,
        fatigue_strength_coeff_ratio=1.5,
        fatigue_strength_exponent=-0.09,
        target_life_cycles=1e6,
        required_fatigue_factor=1.5,
        required_yield_factor=1.2,
    )

    assert results["alternating_stress_mpa"] == pytest.approx(400.0, rel=1e-6)
    assert results["mean_stress_mpa"] == pytest.approx(0.0, abs=1e-6)
    assert results["equivalent_stress_mpa"] == pytest.approx(400.0, rel=1e-6)
    assert results["endurance_limit_mpa"] == pytest.approx(300.0, rel=1e-6)
    assert results["fatigue_safety_factor"] == pytest.approx(0.75, rel=1e-6)
    assert results["yield_safety_factor"] == pytest.approx(0.875, rel=1e-6)

    # Basquin: N = 0.5 * (sigma_eq / sigma_f')^(1/b)
    # sigma_f' = 1.5 * 600 = 900 MPa
    expected_life = 0.5 * (400.0 / 900.0) ** (1.0 / -0.09)
    assert results["estimated_life_cycles"] == pytest.approx(expected_life, rel=1e-6)
    assert results["status"] == "unacceptable"


def test_infinite_life_case():
    results = estimate_fatigue_life(
        max_stress_mpa=150.0,
        min_stress_mpa=-150.0,
        ultimate_strength_mpa=600.0,
        yield_strength_mpa=350.0,
        mean_stress_correction="goodman",
        endurance_limit_ratio=0.5,
        surface_factor=1.0,
        size_factor=1.0,
        reliability_factor=1.0,
        fatigue_strength_coeff_ratio=1.5,
        fatigue_strength_exponent=-0.09,
        target_life_cycles=1e6,
        required_fatigue_factor=1.5,
        required_yield_factor=1.2,
    )

    assert math.isinf(results["estimated_life_cycles"])
    assert math.isinf(results["life_safety_factor"])
    assert results["status"] == "acceptable"


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        estimate_fatigue_life(
            max_stress_mpa=100.0,
            min_stress_mpa=200.0,
            ultimate_strength_mpa=600.0,
            yield_strength_mpa=350.0,
        )

    with pytest.raises(ValueError):
        estimate_fatigue_life(
            max_stress_mpa=200.0,
            min_stress_mpa=100.0,
            ultimate_strength_mpa=600.0,
            yield_strength_mpa=350.0,
            mean_stress_correction="invalid",
        )


def test_polymer_mode_uses_target_life_reference_and_derating():
    results = estimate_fatigue_life(
        max_stress_mpa=24.0,
        min_stress_mpa=4.0,
        ultimate_strength_mpa=70.0,
        yield_strength_mpa=60.0,
        material_family="polymer",
        material_preset="pom",
        temperature_c=60.0,
        load_frequency_hz=8.0,
        moisture_derating_factor=0.95,
        chemical_derating_factor=0.90,
        uv_derating_factor=0.92,
        target_life_cycles=1e6,
    )

    assert results["material_family"] == "polymer"
    assert results["reference_stress_basis"] == "target_life"
    assert results["polymer_derating_factor"] < 1.0
    assert results["endurance_limit_mpa"] == pytest.approx(0.0, abs=1e-12)
    assert math.isfinite(results["estimated_life_cycles"])
    assert math.isfinite(results["estimated_life_hours"])


def test_stress_uncertainty_life_bounds():
    results = estimate_fatigue_life(
        max_stress_mpa=260.0,
        min_stress_mpa=20.0,
        ultimate_strength_mpa=600.0,
        yield_strength_mpa=350.0,
        stress_uncertainty_pct=20.0,
        target_life_cycles=1e6,
    )

    assert results["uncertainty_active"] is True
    assert results["conservative_life_cycles"] <= results["estimated_life_cycles"]
    assert results["optimistic_life_cycles"] >= results["estimated_life_cycles"]
    assert (
        results["conservative_life_safety_factor"]
        <= results["life_safety_factor"]
    )
