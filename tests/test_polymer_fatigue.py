import math

import pytest

from pycalcs.polymer_fatigue import (
    POLYMER_FATIGUE_PRESETS,
    _basquin_life,
    _compute_stress_state,
    _creep_life,
    _energy_life,
    _environment_damage_factor,
    _hybrid_life,
    _reference_equivalent_stress,
    _surrogate_loop_metrics,
    compare_polymer_fatigue_criteria,
)


def _table_by_model(results):
    return {row["model"]: row for row in results["comparison_table"]}


def _pa66_gf50():
    return dict(POLYMER_FATIGUE_PRESETS["pa66_gf50"])


def test_preset_load_case_returns_all_models():
    results = compare_polymer_fatigue_criteria(
        material_preset="pa66_gf50",
        workflow_mode="preset_load_case",
        stress_amplitude_mpa=42.0,
        load_ratio=0.1,
        temperature_c=23.0,
        load_frequency_hz=2.0,
        target_life_cycles=1e6,
    )

    table = _table_by_model(results)

    assert results["material_preset_name"].startswith("PA66-GF50")
    assert results["lcf_hcf_regime"] in {"LCF", "transition", "HCF"}
    assert results["mechanism_regime"] in {
        "hysteresis-dominated",
        "creep-dominated",
        "mixed",
    }
    assert set(table) == {"reference", "energy", "cyclic_creep", "hybrid"}
    assert results["life_spread_ratio"] >= 1.0
    assert table["reference"]["estimated_life_cycles"] > 0.0
    assert table["energy"]["estimated_life_cycles"] > 0.0
    assert table["cyclic_creep"]["estimated_life_cycles"] > 0.0
    assert table["hybrid"]["estimated_life_cycles"] > 0.0


def test_measured_loop_uses_direct_metrics_and_hybrid_is_bounded():
    results = compare_polymer_fatigue_criteria(
        material_preset="pa66_gf30",
        workflow_mode="measured_loop",
        stress_amplitude_mpa=36.0,
        load_ratio=-0.2,
        direct_loop_energy_mj_per_m3=1.30,
        direct_cyclic_creep_rate_per_cycle=2.2e-6,
        target_life_cycles=5e5,
    )

    table = _table_by_model(results)
    energy_life = table["energy"]["estimated_life_cycles"]
    creep_life = table["cyclic_creep"]["estimated_life_cycles"]
    hybrid_life = table["hybrid"]["estimated_life_cycles"]

    assert table["energy"]["used_observables"]["energy_source"] == "direct entry"
    assert table["cyclic_creep"]["used_observables"]["creep_source"] == "direct entry"
    assert min(energy_life, creep_life) <= hybrid_life <= max(energy_life, creep_life)


def test_missing_measured_loop_metric_invalidates_relevant_models():
    results = compare_polymer_fatigue_criteria(
        material_preset="pa66_gf50",
        workflow_mode="measured_loop",
        stress_amplitude_mpa=35.0,
        load_ratio=0.0,
        direct_loop_energy_mj_per_m3=0.90,
        direct_cyclic_creep_rate_per_cycle=0.0,
        target_life_cycles=5e5,
    )

    table = _table_by_model(results)

    assert table["energy"]["applicability_state"] != "invalid"
    assert table["cyclic_creep"]["applicability_state"] == "invalid"
    assert table["hybrid"]["applicability_state"] == "invalid"
    assert table["cyclic_creep"]["estimated_life_cycles"] is None
    assert table["hybrid"]["estimated_life_cycles"] is None


def test_out_of_range_condition_generates_warning():
    results = compare_polymer_fatigue_criteria(
        material_preset="pa66_gf30",
        workflow_mode="preset_load_case",
        stress_amplitude_mpa=48.0,
        load_ratio=0.8,
        temperature_c=85.0,
        load_frequency_hz=12.0,
        moisture_state="wet",
        target_life_cycles=1e6,
    )

    assert any("outside the preset calibration range" in item for item in results["warnings"])
    assert any(
        row["applicability_state"] == "warning" for row in results["comparison_table"]
    )


def test_custom_calibrated_preset_uses_user_coefficients():
    results = compare_polymer_fatigue_criteria(
        material_preset="custom_calibrated",
        workflow_mode="preset_load_case",
        stress_amplitude_mpa=30.0,
        load_ratio=0.2,
        reference_strength_coeff_mpa=200.0,
        reference_exponent=-0.10,
        energy_life_constant=9.5e5,
        energy_life_exponent=1.3,
        creep_life_constant=0.75,
        creep_life_exponent=0.82,
    )

    table = _table_by_model(results)

    assert results["material_preset_name"] == "Custom calibrated polymer"
    assert table["reference"]["estimated_life_cycles"] > 0.0
    assert table["energy"]["estimated_life_cycles"] > 0.0


def test_high_frequency_guidance_reports_published_evidence():
    results = compare_polymer_fatigue_criteria(
        material_preset="pa66_gf30",
        workflow_mode="preset_load_case",
        stress_amplitude_mpa=36.0,
        load_ratio=0.1,
        load_frequency_hz=20.0,
    )

    guidance = results["frequency_guidance"]

    assert guidance["criterion_fit_max_hz"] == pytest.approx(8.0)
    assert guidance["highest_continuous_frequency_hz"] == pytest.approx(60.0)
    assert guidance["highest_any_frequency_hz"] == pytest.approx(20000.0)
    assert any(
        record["material_match"] == "exact" and record["frequency_text"] == "3 Hz and 20 kHz"
        for record in guidance["evidence_records"]
    )
    assert any("criterion-fit window" in warning for warning in results["warnings"])


def test_in_range_frequency_has_no_frequency_extrapolation_warning():
    results = compare_polymer_fatigue_criteria(
        material_preset="pa66_gf50",
        workflow_mode="preset_load_case",
        stress_amplitude_mpa=40.0,
        load_ratio=0.1,
        load_frequency_hz=5.0,
    )

    assert results["frequency_guidance"]["within_fit_range"] is True
    assert not any("criterion-fit window" in warning for warning in results["warnings"])


# ---------------------------------------------------------------------------
# Quantitative hand-calculation tests
# ---------------------------------------------------------------------------


def test_reference_life_hand_calculation():
    """sigma_a=42, R=0.1, pa66_gf50 at reference conditions."""
    preset = _pa66_gf50()
    sigma_a = 42.0
    R = 0.1
    uts = preset["ultimate_strength_mpa"]  # 190
    k_m = preset["mean_stress_sensitivity"]  # 0.34
    sigma_f = preset["reference_strength_coeff_mpa"]  # 330
    b = preset["reference_exponent"]  # -0.118

    # Stress state
    sigma_max = 2 * sigma_a / (1 - R)  # 93.333
    sigma_mean = sigma_max * (1 + R) / 2  # 51.333

    # Equivalent stress (tensile mean stress)
    sigma_eq = sigma_a * (1 + k_m * sigma_mean / uts)  # 45.858

    # Basquin (reversals)
    expected_life = 0.5 * (sigma_eq / sigma_f) ** (1 / b)  # ~9.173e6

    results = compare_polymer_fatigue_criteria(
        material_preset="pa66_gf50",
        workflow_mode="preset_load_case",
        stress_amplitude_mpa=42.0,
        load_ratio=0.1,
        temperature_c=23.0,
        load_frequency_hz=2.0,
        target_life_cycles=1e6,
    )
    table = _table_by_model(results)
    assert table["reference"]["estimated_life_cycles"] == pytest.approx(expected_life, rel=1e-6)


def test_energy_life_hand_calculation():
    """W_d=0.95 -> N_f = 1.55e6 * 0.95^(-1.48)."""
    preset = _pa66_gf50()
    W_d = 0.95
    expected_life = float(preset["energy_life_constant"]) * W_d ** (
        -float(preset["energy_life_exponent"])
    )  # ~1.672e6

    actual = _energy_life(W_d, preset)
    assert actual == pytest.approx(expected_life, rel=1e-9)
    assert actual == pytest.approx(1.672248e6, rel=1e-4)


def test_creep_life_hand_calculation():
    """de/dN=9e-7 -> N_f = 1.05 * (9e-7)^(-0.90)."""
    preset = _pa66_gf50()
    creep_rate = 9e-7
    expected_life = float(preset["creep_life_constant"]) * creep_rate ** (
        -float(preset["creep_life_exponent"])
    )  # ~2.900e5

    actual = _creep_life(creep_rate, preset)
    assert actual == pytest.approx(expected_life, rel=1e-9)
    assert actual == pytest.approx(2.89982e5, rel=1e-4)


def test_hybrid_life_hand_calculation():
    """Harmonic mean of energy + creep lives with R-adjusted weights."""
    preset = _pa66_gf50()
    R = 0.1
    N_energy = _energy_life(0.95, preset)
    N_creep = _creep_life(9e-7, preset)

    # Weight adjustment: w_c = 0.62 + 0.18*0.1 - 0.15*0 = 0.638
    hw = preset["hybrid_weight_adjustment"]
    w_c = (
        float(preset["hybrid_creep_weight"])
        + hw["positive_R_adjustment"] * max(R, 0)
        - hw["negative_R_adjustment"] * max(-R, 0)
    )
    w_e = 1 - w_c
    expected_hybrid = 1.0 / (w_c / N_creep + w_e / N_energy)

    result = _hybrid_life(N_energy, N_creep, R, preset)
    assert result["hybrid_life_cycles"] == pytest.approx(expected_hybrid, rel=1e-9)
    assert result["creep_weight"] == pytest.approx(0.638, rel=1e-9)


def test_surrogate_energy_spot_check():
    """sigma_a=42, R=0.1 at reference conditions -> verify surrogate energy."""
    preset = _pa66_gf50()
    sigma_a = 42.0
    R = 0.1
    stress_state = _compute_stress_state(sigma_a, R)

    environment = _environment_damage_factor(
        temperature_c=23.0,
        load_frequency_hz=2.0,
        moisture_state="dry_as_molded",
        orientation_bucket="0_deg",
        preset=preset,
    )
    assert environment["combined_factor"] == pytest.approx(1.0, rel=1e-9)

    surr = _surrogate_loop_metrics(
        stress_amplitude_mpa=sigma_a,
        sigma_max_mpa=stress_state["sigma_max_mpa"],
        load_ratio=R,
        preset=preset,
        environment=environment,
    )

    # ratio_factor = (1 + 0.24*0.1) * (1 + 0.15*0) = 1.024
    ratio_factor = 1.024
    expected_energy = (
        float(preset["energy_surrogate_coeff"])
        * sigma_a ** float(preset["energy_surrogate_exponent"])
        * 1.0  # env factor
        * ratio_factor
    )
    assert surr["loop_energy_mj_per_m3"] == pytest.approx(expected_energy, rel=1e-6)


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


def test_fully_reversed_R_neg1():
    """R=-1: sigma_mean=0 exactly, no mean-stress correction."""
    preset = _pa66_gf50()
    sigma_a = 42.0
    stress_state = _compute_stress_state(sigma_a, -1.0)
    assert stress_state["sigma_mean_mpa"] == pytest.approx(0.0, abs=1e-12)

    sigma_eq = _reference_equivalent_stress(
        stress_amplitude_mpa=sigma_a,
        sigma_mean_mpa=0.0,
        ultimate_strength_mpa=float(preset["ultimate_strength_mpa"]),
        mean_stress_sensitivity=float(preset["mean_stress_sensitivity"]),
        preset=preset,
    )
    # With sigma_mean=0, tensile_factor = 1.0, so sigma_eq = sigma_a
    assert sigma_eq == pytest.approx(sigma_a, rel=1e-12)


def test_pulsating_tension_R_zero():
    """R=0: sigma_max = 2*sigma_a, tensile correction applied."""
    preset = _pa66_gf50()
    sigma_a = 42.0
    stress_state = _compute_stress_state(sigma_a, 0.0)

    assert stress_state["sigma_max_mpa"] == pytest.approx(2 * sigma_a, rel=1e-12)
    sigma_mean = stress_state["sigma_mean_mpa"]  # = 42.0
    assert sigma_mean == pytest.approx(sigma_a, rel=1e-12)

    sigma_eq = _reference_equivalent_stress(
        stress_amplitude_mpa=sigma_a,
        sigma_mean_mpa=sigma_mean,
        ultimate_strength_mpa=float(preset["ultimate_strength_mpa"]),
        mean_stress_sensitivity=float(preset["mean_stress_sensitivity"]),
        preset=preset,
    )
    expected_factor = 1 + 0.34 * 42.0 / 190.0  # 1.07516
    assert sigma_eq == pytest.approx(sigma_a * expected_factor, rel=1e-6)
    assert sigma_eq > sigma_a  # tensile correction increases equivalent stress


def test_compressive_mean_stress_correction():
    """Direct helper test: compressive branch and floor clamping."""
    preset = _pa66_gf50()
    sigma_a = 42.0

    # Moderate compressive mean stress: factor above floor
    sigma_eq_moderate = _reference_equivalent_stress(
        stress_amplitude_mpa=sigma_a,
        sigma_mean_mpa=-30.0,
        ultimate_strength_mpa=190.0,
        mean_stress_sensitivity=0.34,
        preset=preset,
    )
    # factor = 1.0 - 0.10 * 30/190 = 0.98421
    assert sigma_eq_moderate == pytest.approx(42.0 * 0.984211, rel=1e-4)
    assert sigma_eq_moderate < sigma_a  # compressive mean reduces equivalent stress

    # Large compressive mean stress: hits floor at 0.88
    sigma_eq_floor = _reference_equivalent_stress(
        stress_amplitude_mpa=sigma_a,
        sigma_mean_mpa=-250.0,
        ultimate_strength_mpa=190.0,
        mean_stress_sensitivity=0.34,
        preset=preset,
    )
    assert sigma_eq_floor == pytest.approx(42.0 * 0.88, rel=1e-9)


def test_basquin_cycles_convention():
    """basquin_convention='cycles' -> life is 2x reversals convention."""
    sigma_eq = 45.858
    strength_coeff = 330.0
    exponent = -0.118

    life_reversals = _basquin_life(sigma_eq, strength_coeff, exponent, "reversals")
    life_cycles = _basquin_life(sigma_eq, strength_coeff, exponent, "cycles")

    assert life_cycles == pytest.approx(2.0 * life_reversals, rel=1e-9)


# ---------------------------------------------------------------------------
# Monotonicity / property tests
# ---------------------------------------------------------------------------


def test_monotonicity_stress_vs_life():
    """sigma_a in [20, 30, 40, 50, 60]: all model lives strictly decrease."""
    amplitudes = [20.0, 30.0, 40.0, 50.0, 60.0]
    lives = []
    for sa in amplitudes:
        results = compare_polymer_fatigue_criteria(
            material_preset="pa66_gf50",
            stress_amplitude_mpa=sa,
            load_ratio=0.1,
            temperature_c=23.0,
            load_frequency_hz=2.0,
        )
        table = _table_by_model(results)
        lives.append(table["reference"]["estimated_life_cycles"])

    for i in range(len(lives) - 1):
        assert lives[i] > lives[i + 1], (
            f"Life did not decrease: sigma_a={amplitudes[i]} -> {lives[i]}, "
            f"sigma_a={amplitudes[i+1]} -> {lives[i+1]}"
        )


def test_monotonicity_energy_vs_life():
    """W_d in [0.3, 0.6, 1.0, 2.0, 3.0]: energy life strictly decreases."""
    preset = _pa66_gf50()
    energies = [0.3, 0.6, 1.0, 2.0, 3.0]
    lives = [_energy_life(w, preset) for w in energies]
    for i in range(len(lives) - 1):
        assert lives[i] > lives[i + 1]


def test_monotonicity_creep_rate_vs_life():
    """de/dN in [1e-8, 1e-7, 1e-6, 1e-5]: creep life strictly decreases."""
    preset = _pa66_gf50()
    rates = [1e-8, 1e-7, 1e-6, 1e-5]
    lives = [_creep_life(r, preset) for r in rates]
    for i in range(len(lives) - 1):
        assert lives[i] > lives[i + 1]


def test_hybrid_bounded_by_components():
    """min(N_energy, N_creep) <= N_hybrid <= max(N_energy, N_creep)."""
    preset = _pa66_gf50()
    for R in [-0.5, 0.0, 0.1, 0.3, 0.5]:
        N_energy = _energy_life(1.0, preset)
        N_creep = _creep_life(1e-6, preset)
        result = _hybrid_life(N_energy, N_creep, R, preset)
        N_hybrid = result["hybrid_life_cycles"]
        assert min(N_energy, N_creep) <= N_hybrid <= max(N_energy, N_creep), (
            f"R={R}: hybrid {N_hybrid} not between "
            f"energy {N_energy} and creep {N_creep}"
        )


# ---------------------------------------------------------------------------
# Environment factor spot-checks
# ---------------------------------------------------------------------------


def test_env_factor_at_reference_conditions():
    """T=23, f=2, dry, 0_deg -> all factors = 1.0."""
    preset = _pa66_gf50()
    env = _environment_damage_factor(
        temperature_c=23.0,
        load_frequency_hz=2.0,
        moisture_state="dry_as_molded",
        orientation_bucket="0_deg",
        preset=preset,
    )
    assert env["temperature_factor"] == pytest.approx(1.0, rel=1e-12)
    assert env["frequency_factor"] == pytest.approx(1.0, rel=1e-12)
    assert env["moisture_factor"] == pytest.approx(1.0, rel=1e-12)
    assert env["orientation_factor"] == pytest.approx(1.0, rel=1e-12)
    assert env["combined_factor"] == pytest.approx(1.0, rel=1e-12)


def test_env_factor_elevated_temperature():
    """T=60 -> factor = 1 + 0.012*37 = 1.444."""
    preset = _pa66_gf50()
    env = _environment_damage_factor(
        temperature_c=60.0,
        load_frequency_hz=2.0,
        moisture_state="dry_as_molded",
        orientation_bucket="0_deg",
        preset=preset,
    )
    assert env["temperature_factor"] == pytest.approx(1.444, rel=1e-6)


# ---------------------------------------------------------------------------
# Error path tests
# ---------------------------------------------------------------------------


def test_unknown_orientation_raises():
    """orientation_bucket='bad' -> ValueError."""
    preset = _pa66_gf50()
    with pytest.raises(ValueError, match="Unknown orientation_bucket"):
        _environment_damage_factor(
            temperature_c=23.0,
            load_frequency_hz=2.0,
            moisture_state="dry_as_molded",
            orientation_bucket="bad",
            preset=preset,
        )


def test_unknown_moisture_raises():
    """moisture_state='soaked' -> ValueError."""
    preset = _pa66_gf50()
    with pytest.raises(ValueError, match="Unknown moisture_state"):
        _environment_damage_factor(
            temperature_c=23.0,
            load_frequency_hz=2.0,
            moisture_state="soaked",
            orientation_bucket="0_deg",
            preset=preset,
        )


def test_invalid_basquin_convention_raises():
    """basquin_convention='wrong' -> ValueError."""
    with pytest.raises(ValueError, match="basquin_convention"):
        _basquin_life(50.0, 330.0, -0.118, basquin_convention="wrong")


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


def test_sweep_plot_data_length():
    """All sweep arrays have 21 entries."""
    results = compare_polymer_fatigue_criteria(
        material_preset="pa66_gf50",
        stress_amplitude_mpa=42.0,
        load_ratio=0.1,
    )
    sweep = results["sweep_plot_data"]
    assert len(sweep["x_values"]) == 21
    assert len(sweep["reference_cycles"]) == 21
    assert len(sweep["energy_cycles"]) == 21
    assert len(sweep["creep_cycles"]) == 21
    assert len(sweep["hybrid_cycles"]) == 21


def test_custom_preset_nested_dict_defaults():
    """custom_calibrated preset has all new nested fields."""
    preset = POLYMER_FATIGUE_PRESETS["custom_calibrated"]
    assert "environment_sensitivity" in preset
    assert "ratio_sensitivity" in preset
    assert "compressive_mean_stress" in preset
    assert "hybrid_weight_adjustment" in preset
    assert "basquin_convention" in preset

    env = preset["environment_sensitivity"]
    assert "temperature_reference_c" in env
    assert "temperature_coeff_above" in env
    assert "frequency_reference_hz" in env

    hw = preset["hybrid_weight_adjustment"]
    assert "weight_min" in hw
    assert "weight_max" in hw
