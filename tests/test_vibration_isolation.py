import math

import pytest

from pycalcs import vibration_isolation


def test_transmissibility_at_isolation_threshold():
    mass = 10.0
    num_mounts = 4.0
    excitation_frequency = 10.0
    frequency_ratio = math.sqrt(2.0)
    natural_frequency = excitation_frequency / frequency_ratio
    total_stiffness = (2.0 * math.pi * natural_frequency) ** 2 * mass
    mount_stiffness = total_stiffness / num_mounts

    results = vibration_isolation.calculate_vibration_isolation(
        mode="analyze",
        excitation_type="base",
        mass_kg=mass,
        num_mounts=num_mounts,
        stiffness_input_mode="per_mount",
        mount_stiffness_n_per_m=mount_stiffness,
        static_deflection_m=0.0,
        damping_input_mode="ratio",
        damping_ratio=0.05,
        damping_coefficient_ns_per_m=0.0,
        excitation_frequency_hz=excitation_frequency,
        target_transmissibility=0.5,
        base_displacement_m=0.0,
        force_amplitude_n=0.0,
        max_static_deflection_m=0.0,
    )

    assert results["frequency_ratio"] == pytest.approx(frequency_ratio, rel=1e-3)
    assert results["transmissibility"] == pytest.approx(1.0, rel=1e-3)


def test_design_mode_hits_target_transmissibility():
    results = vibration_isolation.calculate_vibration_isolation(
        mode="design",
        excitation_type="force",
        mass_kg=5.0,
        num_mounts=4.0,
        stiffness_input_mode="per_mount",
        mount_stiffness_n_per_m=20000.0,
        static_deflection_m=0.0,
        damping_input_mode="ratio",
        damping_ratio=0.04,
        damping_coefficient_ns_per_m=0.0,
        excitation_frequency_hz=30.0,
        target_transmissibility=0.5,
        base_displacement_m=0.0,
        force_amplitude_n=0.0,
        max_static_deflection_m=0.0,
    )

    assert results["frequency_ratio"] >= math.sqrt(2.0)
    assert results["transmissibility"] == pytest.approx(0.5, rel=1e-3)
    assert results["total_stiffness_n_per_m"] > 0.0
