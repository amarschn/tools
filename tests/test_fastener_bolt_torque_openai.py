import pytest

from pycalcs import fastener_bolt_torque_openai


def test_nut_factor_direct_preload_metric_openai():
    results = fastener_bolt_torque_openai.calculate_bolt_torque_openai(
        thread_standard="metric",
        nominal_diameter=10.0,
        thread_pitch=1.5,
        threads_per_inch=0.0,
        thread_angle_deg=60.0,
        bearing_diameter=18.0,
        mu_thread=0.15,
        mu_bearing=0.15,
        torque_model="nut_factor",
        nut_factor=0.2,
        preload_method="direct",
        target_preload=20.0,
        percent_proof=75.0,
        proof_strength=830.0,
        tensile_stress_area=0.0,
    )

    assert results["clamp_load_n"] == pytest.approx(20000.0)
    assert results["torque_total_nm"] == pytest.approx(40.0, rel=1e-3)
    assert results["torque_total_nut_factor_nm"] == pytest.approx(40.0, rel=1e-3)
    assert results["tensile_stress_area_mm2"] == pytest.approx(57.99, rel=0.02)
    assert results["bolt_stress_mpa"] == pytest.approx(345.0, rel=0.03)


def test_percent_proof_unified_openai():
    results = fastener_bolt_torque_openai.calculate_bolt_torque_openai(
        thread_standard="unified",
        nominal_diameter=0.375,
        thread_pitch=0.0,
        threads_per_inch=16.0,
        thread_angle_deg=60.0,
        bearing_diameter=0.0,
        mu_thread=0.15,
        mu_bearing=0.15,
        torque_model="nut_factor",
        nut_factor=0.2,
        preload_method="percent_proof",
        target_preload=0.0,
        percent_proof=75.0,
        proof_strength=120.0,
        tensile_stress_area=0.0,
    )

    assert results["tensile_stress_area_in2"] == pytest.approx(0.07749, rel=0.01)
    assert results["proof_load_lbf"] == pytest.approx(9299.0, rel=0.01)
    assert results["clamp_load_lbf"] == pytest.approx(6974.0, rel=0.01)
    assert results["torque_total_nm"] == pytest.approx(59.1, rel=0.02)
