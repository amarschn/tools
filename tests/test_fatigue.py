import math

import pytest

from pycalcs.fatigue import estimate_fatigue_life, explore_mean_stress_methods


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

# =============================================================================
# explore_mean_stress_methods tests
# =============================================================================


def test_explore_stress_state_conversion():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=100.0,
        mean_stress_mpa=50.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
    )
    assert result["sigma_max_mpa"] == pytest.approx(150.0)
    assert result["sigma_min_mpa"] == pytest.approx(-50.0)
    assert result["stress_ratio"] == pytest.approx(-50.0 / 150.0)


def test_explore_zero_mean_stress_all_methods_equal():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=200.0,
        mean_stress_mpa=0.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
    )
    table = {row["method"]: row for row in result["comparison_table"]}
    for method in ("none", "goodman", "gerber", "soderberg"):
        assert table[method]["equivalent_stress_mpa"] == pytest.approx(200.0, rel=1e-6)
    assert result["equivalent_stress_spread_pct"] == pytest.approx(0.0, abs=1e-6)


def test_explore_positive_mean_stress_ordering():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=180.0,
        mean_stress_mpa=120.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
    )
    table = {row["method"]: row for row in result["comparison_table"]}
    eq_none = table["none"]["equivalent_stress_mpa"]
    eq_goodman = table["goodman"]["equivalent_stress_mpa"]
    eq_gerber = table["gerber"]["equivalent_stress_mpa"]
    eq_soderberg = table["soderberg"]["equivalent_stress_mpa"]
    # soderberg >= goodman >= gerber >= none for tensile mean stress
    assert eq_soderberg >= eq_goodman - 1e-9
    assert eq_goodman >= eq_gerber - 1e-9
    assert eq_gerber >= eq_none - 1e-9


def test_explore_goodman_invalid_at_sut():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=100.0,
        mean_stress_mpa=640.0,  # > S_ut=625
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
        enabled_methods="goodman",
    )
    row = result["comparison_table"][0]
    assert row["validity_state"] == "invalid"
    assert row["equivalent_stress_mpa"] is None
    assert row["estimated_life_cycles"] is None


def test_explore_soderberg_invalid_at_sy():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=100.0,
        mean_stress_mpa=540.0,  # > S_y=530
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
        enabled_methods="soderberg",
    )
    row = result["comparison_table"][0]
    assert row["validity_state"] == "invalid"


def test_explore_gerber_invalid_at_sut():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=100.0,
        mean_stress_mpa=-640.0,  # |sigma_m| > S_ut, Gerber denom <= 0
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
        enabled_methods="gerber",
    )
    row = result["comparison_table"][0]
    assert row["validity_state"] == "invalid"


def test_explore_consistency_with_estimate_life():
    # Use sigma_a=280 so equiv_stress > S_e and life is finite.
    sigma_a = 280.0
    sigma_m = 120.0
    S_ut = 625.0
    S_y = 530.0

    explore_result = explore_mean_stress_methods(
        alternating_stress_mpa=sigma_a,
        mean_stress_mpa=sigma_m,
        ultimate_strength_mpa=S_ut,
        yield_strength_mpa=S_y,
        material_preset="steel_1045",
        reference_basis="endurance_limit",
        enabled_methods="goodman",
        endurance_limit_ratio=0.50,
        surface_factor=1.0,
        size_factor=1.0,
        reliability_factor=1.0,
        fatigue_strength_coeff_ratio=1.55,
        fatigue_strength_exponent=-0.090,
        target_life_cycles=1e6,
        load_frequency_hz=2.0,
    )

    life_result = estimate_fatigue_life(
        max_stress_mpa=sigma_m + sigma_a,
        min_stress_mpa=sigma_m - sigma_a,
        ultimate_strength_mpa=S_ut,
        yield_strength_mpa=S_y,
        mean_stress_correction="goodman",
        endurance_limit_ratio=0.50,
        surface_factor=1.0,
        size_factor=1.0,
        reliability_factor=1.0,
        fatigue_strength_coeff_ratio=1.55,
        fatigue_strength_exponent=-0.090,
        target_life_cycles=1e6,
        load_frequency_hz=2.0,
    )

    row = explore_result["comparison_table"][0]
    assert row["method"] == "goodman"
    assert row["equivalent_stress_mpa"] == pytest.approx(
        life_result["equivalent_stress_mpa"], rel=1e-5
    )
    explore_life = row["estimated_life_cycles"]
    life_life = life_result["estimated_life_cycles"]
    if math.isinf(explore_life) and math.isinf(life_life):
        pass  # both infinite: consistent
    else:
        assert explore_life == pytest.approx(life_life, rel=1e-5)


def test_explore_endurance_limit_gives_infinite_life():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=50.0,
        mean_stress_mpa=0.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
        endurance_limit_ratio=0.50,  # S_e = 312.5 MPa >> 50 MPa
        material_preset="steel_1045",
        reference_basis="endurance_limit",
        enabled_methods="none",
    )
    row = result["comparison_table"][0]
    assert math.isinf(row["estimated_life_cycles"])


def test_explore_sweep_monotonicity_goodman():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=150.0,
        mean_stress_mpa=50.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
        enabled_methods="goodman",
        sweep_min_mpa=0.0,
        sweep_max_mpa=400.0,
        n_sweep_points=40,
    )
    sweep = result["sweep_data"]
    mean_pts = sweep["mean_stress_mpa"]
    lives = sweep["life_cycles"]["goodman"]
    # For positive tensile mean stress with fixed sigma_a, life should be non-increasing
    prev_life = None
    for sm, life in zip(mean_pts, lives):
        if sm < 0 or life is None:
            continue
        if prev_life is not None:
            assert life <= prev_life * 1.001  # non-increasing with small tolerance
        prev_life = life


def test_explore_sweep_array_lengths():
    n = 41
    result = explore_mean_stress_methods(
        alternating_stress_mpa=180.0,
        mean_stress_mpa=120.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
        n_sweep_points=n,
    )
    sweep = result["sweep_data"]
    assert len(sweep["mean_stress_mpa"]) == n
    for lives in sweep["life_cycles"].values():
        assert len(lives) == n
    haigh = result["haigh_diagram_data"]
    assert len(haigh["mean_stress_mpa"]) == n


def test_explore_operating_point_within_haigh_bounds():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=180.0,
        mean_stress_mpa=120.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
    )
    haigh = result["haigh_diagram_data"]
    assert haigh["x_min"] <= result["mean_stress_mpa"] <= haigh["x_max"]
    assert result["alternating_stress_mpa"] <= haigh["y_max"]


def test_explore_spread_zero_at_zero_mean_stress():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=180.0,
        mean_stress_mpa=0.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
    )
    assert result["equivalent_stress_spread_pct"] == pytest.approx(0.0, abs=1e-6)


def test_explore_spread_positive_at_tensile_mean_stress():
    # Use sigma_a=350 so all method equiv stresses exceed S_e, giving finite lives.
    result = explore_mean_stress_methods(
        alternating_stress_mpa=350.0,
        mean_stress_mpa=120.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
    )
    assert result["equivalent_stress_spread_pct"] > 0.0
    assert result["life_spread_ratio"] > 1.0


def test_explore_compressive_mean_stress_warning():
    result = explore_mean_stress_methods(
        alternating_stress_mpa=180.0,
        mean_stress_mpa=-50.0,
        ultimate_strength_mpa=625.0,
        yield_strength_mpa=530.0,
    )
    assert any("compressive" in w.lower() for w in result["warnings"])
    # All methods should still compute valid results
    for row in result["comparison_table"]:
        assert row["equivalent_stress_mpa"] is not None


def test_explore_unknown_method_raises():
    with pytest.raises(ValueError, match="Unknown method"):
        explore_mean_stress_methods(
            alternating_stress_mpa=180.0,
            mean_stress_mpa=120.0,
            ultimate_strength_mpa=625.0,
            yield_strength_mpa=530.0,
            enabled_methods="goodman,walker",
        )


def test_explore_invalid_alternating_stress_raises():
    with pytest.raises(ValueError):
        explore_mean_stress_methods(
            alternating_stress_mpa=0.0,
            mean_stress_mpa=0.0,
            ultimate_strength_mpa=625.0,
            yield_strength_mpa=530.0,
        )
