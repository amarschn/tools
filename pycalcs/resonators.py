"""
Resonator ring-down simulation utilities.
"""

from __future__ import annotations

import math
import random


MATERIALS = {
    "steel": {
        "display": "Steel (AISI 1020)",
        "elastic_modulus_gpa": 200.0,
        "density_kg_m3": 7850.0,
    },
    "aluminum": {
        "display": "Aluminum 6061-T6",
        "elastic_modulus_gpa": 69.0,
        "density_kg_m3": 2700.0,
    },
    "brass": {
        "display": "Brass (C360)",
        "elastic_modulus_gpa": 100.0,
        "density_kg_m3": 8500.0,
    },
    "titanium": {
        "display": "Titanium (Grade 5)",
        "elastic_modulus_gpa": 116.0,
        "density_kg_m3": 4430.0,
    },
}


RESONATOR_TYPES = {
    "tuning_fork": {"display": "Tuning fork (two tines)", "tine_count": 2},
    "beam": {"display": "Single beam/rod", "tine_count": 1},
}


SUPPORT_CONDITIONS = {
    "cantilever": {"display": "Cantilever (clamped-free)", "beta_1": 1.87510407},
    "simply_supported": {"display": "Simply supported", "beta_1": math.pi},
    "clamped_clamped": {"display": "Clamped-clamped", "beta_1": 4.73004074},
    "free_free": {"display": "Free-free (suspended)", "beta_1": 4.73004074},
}


CROSS_SECTIONS = {
    "rectangular": "Rectangular",
    "circular": "Circular",
}


def _validate_positive(value: float, label: str) -> float:
    if value <= 0.0:
        raise ValueError(f"{label} must be positive.")
    return value


def _validate_non_negative(value: float, label: str) -> float:
    if value < 0.0:
        raise ValueError(f"{label} cannot be negative.")
    return value


def _validate_choice(value: str, label: str, choices: set[str]) -> str:
    normalized = value.strip().lower()
    if normalized not in choices:
        raise ValueError(f"{label} must be one of {sorted(choices)}.")
    return normalized


def simulate_ringdown_resonator(
    resonator_type: str,
    support_condition: str,
    cross_section: str,
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    diameter_mm: float,
    material: str,
    elastic_modulus_gpa: float,
    density_kg_m3: float,
    quality_factor: float,
    initial_displacement_mm: float,
    simulation_duration_s: float,
    sample_rate_hz: float,
    noise_rms_mm: float,
) -> dict[str, float | int | str | dict[str, list[float]]]:
    """
    Simulate the ring-down response of a resonator modeled as a damped beam.

    The resonator is approximated as a uniform Euler-Bernoulli beam with a single
    dominant bending mode. The ring-down displacement is computed as a damped
    sinusoid with an exponential envelope.

    ---Parameters---
    resonator_type : str
        "tuning_fork" for two cantilever tines or "beam" for a single beam/rod.
        The tuning fork option treats each tine as a cantilever beam.
    support_condition : str
        Beam support condition: "cantilever", "simply_supported", "clamped_clamped",
        or "free_free". For tuning_fork, this must be "cantilever".
    cross_section : str
        Cross-section type: "rectangular" or "circular".
    length_mm : float
        Active length of the vibrating tine or beam (mm).
    width_mm : float
        Rectangular section width (mm). Ignored for circular sections.
    thickness_mm : float
        Rectangular section thickness in the bending direction (mm).
        Ignored for circular sections.
    diameter_mm : float
        Circular section diameter (mm). Ignored for rectangular sections.
    material : str
        Material key from the dropdown (steel, aluminum, brass, titanium) or "custom".
    elastic_modulus_gpa : float
        Elastic modulus in GPa, used only when material is "custom".
    density_kg_m3 : float
        Density in kg/m^3, used only when material is "custom".
    quality_factor : float
        Quality factor Q (dimensionless). Must be greater than 0.5 for an underdamped response.
    initial_displacement_mm : float
        Initial tip displacement amplitude at t=0 (mm).
    simulation_duration_s : float
        Total simulation duration (s).
    sample_rate_hz : float
        Sample rate for the simulated waveform (Hz). If this is below the
        minimum samples-per-cycle threshold, it is automatically increased to
        avoid aliasing in the plotted waveform.
    noise_rms_mm : float
        Optional RMS additive noise level (mm).

    ---Returns---
    fundamental_frequency_hz : float
        Undamped natural frequency f_n (Hz).
    damped_frequency_hz : float
        Damped natural frequency f_d (Hz).
    natural_angular_frequency_rad_s : float
        Undamped angular frequency omega_n (rad/s).
    damped_angular_frequency_rad_s : float
        Damped angular frequency omega_d (rad/s).
    quality_factor : float
        Quality factor Q (dimensionless).
    damping_ratio : float
        Damping ratio zeta (dimensionless).
    decay_time_constant_s : float
        Amplitude decay time constant tau = 1/(zeta * omega_n) (s).
    t20_time_s : float
        Time for amplitude to decay by 20 dB (s).
    t60_time_s : float
        Time for amplitude to decay by 60 dB (s).
    log_decrement : float
        Logarithmic decrement for adjacent peaks (dimensionless).
    section_area_mm2 : float
        Cross-section area (mm^2).
    second_moment_mm4 : float
        Second moment of area about the bending axis (mm^4).
    mass_per_tine_kg : float
        Mass of a single tine/beam (kg).
    total_moving_mass_kg : float
        Total moving mass (kg), accounting for both tines in a tuning fork.
    flexural_rigidity_n_m2 : float
        Flexural rigidity E*I (N*m^2).
    beta_1 : float
        Dimensionless mode constant for the first bending mode.
    sample_count : int
        Number of samples in the simulated response.
    effective_sample_rate_hz : float
        Sample rate actually used for simulation after aliasing safeguards (Hz).
    samples_per_cycle : float
        Effective samples per cycle based on damped frequency (dimensionless).
    ringdown_curve : dict[str, list[float]]
        Time history of the response with keys: time_s, displacement_mm,
        envelope_mm, envelope_neg_mm.
    decay_curve : dict[str, list[float]]
        Envelope decay in dB with keys: time_s, decay_db.
    resonator_type_display : str
        Human-readable resonator type.
    support_condition_display : str
        Human-readable support condition.
    cross_section_display : str
        Human-readable cross-section type.
    material_display : str
        Human-readable material label.
    subst_fundamental_frequency_hz : str
        Substituted equation for f_n (LaTeX).
    subst_damped_frequency_hz : str
        Substituted equation for f_d (LaTeX).
    subst_damping_ratio : str
        Substituted equation for zeta (LaTeX).
    subst_decay_time_constant_s : str
        Substituted equation for tau (LaTeX).
    subst_t20_time_s : str
        Substituted equation for t20 (LaTeX).
    subst_t60_time_s : str
        Substituted equation for t60 (LaTeX).

    ---LaTeX---
    f_n = \\frac{\\beta_1^2}{2\\pi} \\sqrt{\\frac{E I}{\\rho A L^4}}
    \\omega_n = 2\\pi f_n
    \\zeta = \\frac{1}{2Q}
    \\omega_d = \\omega_n \\sqrt{1 - \\zeta^2}
    x(t) = x_0 e^{-\\zeta \\omega_n t} \\cos(\\omega_d t)
    \\tau = \\frac{1}{\\zeta \\omega_n}
    t_{20} = \\frac{\\ln(10)}{\\zeta \\omega_n}
    t_{60} = \\frac{\\ln(1000)}{\\zeta \\omega_n}

    References: Inman, D. J., *Engineering Vibration*, 4th ed., 2014.
    """
    resonator_key = _validate_choice(resonator_type, "resonator_type", set(RESONATOR_TYPES))
    support_key = _validate_choice(
        support_condition, "support_condition", set(SUPPORT_CONDITIONS)
    )
    section_key = _validate_choice(cross_section, "cross_section", set(CROSS_SECTIONS))

    if resonator_key == "tuning_fork" and support_key != "cantilever":
        raise ValueError("tuning_fork requires support_condition = 'cantilever'.")

    length_mm = _validate_positive(length_mm, "length_mm")
    initial_displacement_mm = _validate_positive(
        initial_displacement_mm, "initial_displacement_mm"
    )
    quality_factor = _validate_positive(quality_factor, "quality_factor")
    simulation_duration_s = _validate_positive(simulation_duration_s, "simulation_duration_s")
    sample_rate_hz = _validate_positive(sample_rate_hz, "sample_rate_hz")
    noise_rms_mm = _validate_non_negative(noise_rms_mm, "noise_rms_mm")

    if quality_factor <= 0.5:
        raise ValueError("quality_factor must be greater than 0.5 for an underdamped response.")

    if section_key == "rectangular":
        width_mm = _validate_positive(width_mm, "width_mm")
        thickness_mm = _validate_positive(thickness_mm, "thickness_mm")
    else:
        diameter_mm = _validate_positive(diameter_mm, "diameter_mm")

    if material.strip().lower() == "custom":
        elastic_modulus_gpa = _validate_positive(elastic_modulus_gpa, "elastic_modulus_gpa")
        density_kg_m3 = _validate_positive(density_kg_m3, "density_kg_m3")
        material_display = "Custom"
    else:
        material_key = _validate_choice(material, "material", set(MATERIALS))
        material_entry = MATERIALS[material_key]
        elastic_modulus_gpa = material_entry["elastic_modulus_gpa"]
        density_kg_m3 = material_entry["density_kg_m3"]
        material_display = material_entry["display"]

    length_m = length_mm / 1000.0

    if section_key == "rectangular":
        width_m = width_mm / 1000.0
        thickness_m = thickness_mm / 1000.0
        area_m2 = width_m * thickness_m
        inertia_m4 = width_m * thickness_m**3 / 12.0
        section_area_mm2 = width_mm * thickness_mm
        second_moment_mm4 = width_mm * thickness_mm**3 / 12.0
    else:
        diameter_m = diameter_mm / 1000.0
        area_m2 = math.pi * diameter_m**2 / 4.0
        inertia_m4 = math.pi * diameter_m**4 / 64.0
        section_area_mm2 = math.pi * diameter_mm**2 / 4.0
        second_moment_mm4 = math.pi * diameter_mm**4 / 64.0

    beta_1 = SUPPORT_CONDITIONS[support_key]["beta_1"]
    elastic_modulus_pa = elastic_modulus_gpa * 1e9
    flexural_rigidity = elastic_modulus_pa * inertia_m4

    omega_n = beta_1**2 * math.sqrt(
        elastic_modulus_pa * inertia_m4 / (density_kg_m3 * area_m2 * length_m**4)
    )
    frequency_n = omega_n / (2.0 * math.pi)

    damping_ratio = 1.0 / (2.0 * quality_factor)
    if damping_ratio >= 1.0:
        raise ValueError("Damping ratio must be less than 1.0 for oscillatory ring-down.")
    omega_d = omega_n * math.sqrt(1.0 - damping_ratio**2)
    frequency_d = omega_d / (2.0 * math.pi)

    decay_time_constant = 1.0 / (damping_ratio * omega_n)
    t20_time = math.log(10.0) / (damping_ratio * omega_n)
    t60_time = math.log(1000.0) / (damping_ratio * omega_n)
    log_decrement = (2.0 * math.pi * damping_ratio) / math.sqrt(1.0 - damping_ratio**2)

    tine_count = RESONATOR_TYPES[resonator_key]["tine_count"]
    mass_per_tine = density_kg_m3 * area_m2 * length_m
    total_moving_mass = mass_per_tine * tine_count

    min_samples_per_cycle = 2.5
    effective_sample_rate_hz = sample_rate_hz
    samples_per_cycle = sample_rate_hz / frequency_d
    if samples_per_cycle < min_samples_per_cycle:
        effective_sample_rate_hz = min_samples_per_cycle * frequency_d
        samples_per_cycle = min_samples_per_cycle

    sample_count = max(2, int(round(simulation_duration_s * effective_sample_rate_hz)) + 1)
    dt = simulation_duration_s / (sample_count - 1)

    rng = random.Random(0)
    time_s: list[float] = []
    displacement_mm: list[float] = []
    envelope_mm: list[float] = []
    decay_db: list[float] = []

    for i in range(sample_count):
        t = i * dt
        envelope = initial_displacement_mm * math.exp(-damping_ratio * omega_n * t)
        displacement = envelope * math.cos(omega_d * t)
        if noise_rms_mm > 0.0:
            displacement += rng.gauss(0.0, noise_rms_mm)

        time_s.append(t)
        displacement_mm.append(displacement)
        envelope_mm.append(envelope)
        if envelope <= 0.0:
            decay_db.append(-120.0)
        else:
            decay_db.append(20.0 * math.log10(envelope / initial_displacement_mm))

    resonator_display = RESONATOR_TYPES[resonator_key]["display"]
    support_display = SUPPORT_CONDITIONS[support_key]["display"]
    section_display = CROSS_SECTIONS[section_key]

    subst_fundamental = (
        "f_n = \\frac{\\beta_1^2}{2\\pi} \\sqrt{\\frac{E I}{\\rho A L^4}}"
        f" = \\frac{{{beta_1:.4f}^2}}{{2\\pi}}"
        f" \\sqrt{{\\frac{{{elastic_modulus_pa:.3e} \\cdot {inertia_m4:.3e}}}"
        f"{{{density_kg_m3:.1f} \\cdot {area_m2:.3e} \\cdot {length_m:.4f}^4}}}}"
        f" = {frequency_n:.2f}\\,\\text{{Hz}}"
    )
    subst_damped = (
        f"f_d = f_n \\sqrt{{1-\\zeta^2}} = {frequency_n:.2f}"
        f" \\sqrt{{1-{damping_ratio:.5f}^2}}"
        f" = {frequency_d:.2f}\\,\\text{{Hz}}"
    )
    subst_zeta = (
        f"\\zeta = \\frac{{1}}{{2Q}} = \\frac{{1}}{{2\\times {quality_factor:.1f}}}"
        f" = {damping_ratio:.5f}"
    )
    subst_tau = (
        "\\tau = \\frac{1}{\\zeta \\omega_n}"
        f" = \\frac{{1}}{{{damping_ratio:.5f} \\times {omega_n:.2f}}}"
        f" = {decay_time_constant:.3f}\\,\\text{{s}}"
    )
    subst_t20 = (
        "t_{20} = \\frac{\\ln(10)}{\\zeta \\omega_n}"
        f" = \\frac{{{math.log(10.0):.3f}}}"
        f"{{{damping_ratio:.5f} \\times {omega_n:.2f}}}"
        f" = {t20_time:.3f}\\,\\text{{s}}"
    )
    subst_t60 = (
        "t_{60} = \\frac{\\ln(1000)}{\\zeta \\omega_n}"
        f" = \\frac{{{math.log(1000.0):.3f}}}"
        f"{{{damping_ratio:.5f} \\times {omega_n:.2f}}}"
        f" = {t60_time:.3f}\\,\\text{{s}}"
    )

    return {
        "fundamental_frequency_hz": frequency_n,
        "damped_frequency_hz": frequency_d,
        "natural_angular_frequency_rad_s": omega_n,
        "damped_angular_frequency_rad_s": omega_d,
        "quality_factor": quality_factor,
        "damping_ratio": damping_ratio,
        "decay_time_constant_s": decay_time_constant,
        "t20_time_s": t20_time,
        "t60_time_s": t60_time,
        "log_decrement": log_decrement,
        "section_area_mm2": section_area_mm2,
        "second_moment_mm4": second_moment_mm4,
        "mass_per_tine_kg": mass_per_tine,
        "total_moving_mass_kg": total_moving_mass,
        "flexural_rigidity_n_m2": flexural_rigidity,
        "beta_1": beta_1,
        "sample_count": sample_count,
        "effective_sample_rate_hz": effective_sample_rate_hz,
        "samples_per_cycle": samples_per_cycle,
        "ringdown_curve": {
            "time_s": time_s,
            "displacement_mm": displacement_mm,
            "envelope_mm": envelope_mm,
            "envelope_neg_mm": [-value for value in envelope_mm],
        },
        "decay_curve": {
            "time_s": time_s,
            "decay_db": decay_db,
        },
        "resonator_type_display": resonator_display,
        "support_condition_display": support_display,
        "cross_section_display": section_display,
        "material_display": material_display,
        "subst_fundamental_frequency_hz": subst_fundamental,
        "subst_damped_frequency_hz": subst_damped,
        "subst_damping_ratio": subst_zeta,
        "subst_decay_time_constant_s": subst_tau,
        "subst_t20_time_s": subst_t20,
        "subst_t60_time_s": subst_t60,
    }
