import math

import pytest

from pycalcs import resonators


def test_ringdown_support_ratio():
    base = dict(
        resonator_type="beam",
        support_condition="cantilever",
        cross_section="rectangular",
        length_mm=100.0,
        width_mm=10.0,
        thickness_mm=2.0,
        diameter_mm=0.0,
        material="steel",
        elastic_modulus_gpa=0.0,
        density_kg_m3=0.0,
        quality_factor=200.0,
        initial_displacement_mm=1.0,
        simulation_duration_s=0.2,
        sample_rate_hz=2000.0,
        noise_rms_mm=0.0,
    )

    cantilever = resonators.simulate_ringdown_resonator(**base)
    clamped = resonators.simulate_ringdown_resonator(
        **{**base, "support_condition": "clamped_clamped"}
    )

    expected_ratio = (4.73004074 / 1.87510407) ** 2
    assert clamped["fundamental_frequency_hz"] / cantilever["fundamental_frequency_hz"] == pytest.approx(
        expected_ratio, rel=1e-3
    )


def test_ringdown_decay_and_samples():
    duration = 0.5
    sample_rate = 1000.0

    results = resonators.simulate_ringdown_resonator(
        resonator_type="tuning_fork",
        support_condition="cantilever",
        cross_section="rectangular",
        length_mm=80.0,
        width_mm=6.0,
        thickness_mm=4.0,
        diameter_mm=0.0,
        material="steel",
        elastic_modulus_gpa=0.0,
        density_kg_m3=0.0,
        quality_factor=500.0,
        initial_displacement_mm=0.5,
        simulation_duration_s=duration,
        sample_rate_hz=sample_rate,
        noise_rms_mm=0.0,
    )

    expected_count = int(round(duration * results["effective_sample_rate_hz"])) + 1
    assert results["sample_count"] == expected_count
    assert len(results["ringdown_curve"]["time_s"]) == expected_count
    assert results["t60_time_s"] == pytest.approx(
        math.log(1000.0) * results["decay_time_constant_s"], rel=1e-6
    )
