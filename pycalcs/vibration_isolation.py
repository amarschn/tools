"""
Vibration isolation calculations for single-degree-of-freedom systems.
"""

from __future__ import annotations

import math


GRAVITY_M_S2 = 9.80665


def _response_terms(frequency_ratio: float, damping_ratio: float) -> tuple[float, float, float]:
    denominator = math.sqrt(
        (1.0 - frequency_ratio**2) ** 2 + (2.0 * damping_ratio * frequency_ratio) ** 2
    )
    transmissibility = math.sqrt(1.0 + (2.0 * damping_ratio * frequency_ratio) ** 2) / denominator
    relative_ratio = (frequency_ratio**2) / denominator
    magnification = 1.0 / denominator
    return transmissibility, relative_ratio, magnification


def _validate_choice(value: str, label: str, choices: set[str]) -> str:
    normalized = value.strip().lower()
    if normalized not in choices:
        raise ValueError(f"{label} must be one of {sorted(choices)}.")
    return normalized


def _validate_positive(value: float, label: str) -> float:
    if value <= 0.0:
        raise ValueError(f"{label} must be positive.")
    return value


def calculate_vibration_isolation(
    mode: str,
    excitation_type: str,
    mass_kg: float,
    num_mounts: float,
    stiffness_input_mode: str,
    mount_stiffness_n_per_m: float,
    static_deflection_m: float,
    damping_input_mode: str,
    damping_ratio: float,
    damping_coefficient_ns_per_m: float,
    excitation_frequency_hz: float,
    target_transmissibility: float,
    base_displacement_m: float,
    force_amplitude_n: float,
    max_static_deflection_m: float,
) -> dict[str, float | list[float]]:
    """
    Analyze or size a vibration isolator using a single-degree-of-freedom model.

    The model assumes linear stiffness and viscous damping with harmonic excitation.
    Use analyze mode to evaluate an existing isolator, or design mode to solve
    for the stiffness needed to reach a target transmissibility at the excitation
    frequency.

    ---Parameters---
    mode : str
        "analyze" to evaluate a given isolator or "design" to solve for stiffness.
    excitation_type : str
        "base" for base displacement excitation or "force" for applied harmonic force.
    mass_kg : float
        Supported mass on the isolators (kg).
    num_mounts : float
        Number of isolators acting in parallel (must be a positive integer).
    stiffness_input_mode : str
        "per_mount" to specify mount stiffness or "static_deflection" to use gravity deflection.
    mount_stiffness_n_per_m : float
        Stiffness of a single mount (N/m) when stiffness_input_mode is "per_mount".
    static_deflection_m : float
        Static deflection under gravity (m) when stiffness_input_mode is "static_deflection".
    damping_input_mode : str
        "ratio" to specify damping ratio or "coefficient" to specify viscous damping.
    damping_ratio : float
        Damping ratio zeta (dimensionless) when damping_input_mode is "ratio".
    damping_coefficient_ns_per_m : float
        Viscous damping coefficient c (N*s/m) when damping_input_mode is "coefficient".
    excitation_frequency_hz : float
        Excitation frequency (Hz).
    target_transmissibility : float
        Target transmissibility (dimensionless) used in design mode (0 < T < 1).
    base_displacement_m : float
        Base displacement amplitude (m) used to compute response amplitudes.
    force_amplitude_n : float
        Applied force amplitude (N) used to compute response amplitudes.
    max_static_deflection_m : float
        Allowable static deflection (m) for utilization reporting; set to 0 to disable.

    ---Returns---
    natural_frequency_hz : float
        Natural frequency of the isolated system (Hz).
    natural_angular_frequency_rad_s : float
        Natural angular frequency of the isolated system (rad/s).
    total_stiffness_n_per_m : float
        Equivalent stiffness of all mounts in parallel (N/m).
    mount_stiffness_n_per_m : float
        Stiffness per mount (N/m).
    static_deflection_m : float
        Static deflection under gravity (m).
    damping_ratio : float
        Damping ratio zeta (dimensionless).
    damping_coefficient_ns_per_m : float
        Equivalent viscous damping coefficient (N*s/m).
    frequency_ratio : float
        Frequency ratio r = f_exc / f_n (dimensionless).
    transmissibility : float
        Primary transmissibility (X/Y for base excitation, F_T/F_0 for force excitation).
    isolation_frequency_hz : float
        Isolation threshold frequency (Hz), equal to sqrt(2) * f_n.
    isolation_margin : float
        Margin to isolation threshold, r - sqrt(2) (dimensionless).
    relative_displacement_amplitude_m : float
        Relative displacement amplitude Z (m) when excitation amplitude is provided.
    absolute_displacement_amplitude_m : float
        Absolute displacement amplitude X (m) when excitation amplitude is provided.
    transmitted_force_amplitude_n : float
        Transmitted force amplitude to the base (N) when excitation amplitude is provided.
    acceleration_amplitude_m_s2 : float
        Acceleration amplitude of the mass (m/s^2) when excitation amplitude is provided.
    dynamic_magnification : float
        Dynamic magnification factor X / (F0/k) for force excitation.
    static_deflection_utilization : float
        Ratio of static deflection to the allowable deflection (dimensionless), if enabled.
    plot_frequency_ratio : list[float]
        Frequency ratio samples for plotting.
    plot_transmissibility : list[float]
        Transmissibility samples for plotting.

    ---LaTeX---
    k_{total} = n k_{mount}
    k_{total} = \\frac{m g}{\\delta_{static}}
    k_{total} = m \\omega_n^2
    k_{mount} = \\frac{k_{total}}{n}
    \\omega_n = \\sqrt{\\frac{k_{total}}{m}}
    f_n = \\frac{\\omega_n}{2 \\pi}
    r = \\frac{f_{exc}}{f_n}
    \\zeta = \\frac{c}{2 m \\omega_n}
    c = 2 m \\omega_n \\zeta
    T = \\frac{\\sqrt{1 + (2 \\zeta r)^2}}{\\sqrt{(1-r^2)^2 + (2 \\zeta r)^2}}
    \\frac{Z}{Y} = \\frac{r^2}{\\sqrt{(1-r^2)^2 + (2 \\zeta r)^2}}
    F_T = k_{total} Z \\sqrt{1 + (2 \\zeta r)^2}
    \\delta_{static} = \\frac{m g}{k_{total}}
    M = \\frac{1}{\\sqrt{(1-r^2)^2 + (2 \\zeta r)^2}}

    References: Inman, D. J., *Engineering Vibration*, 4th ed., 2014.
    """

    mode = _validate_choice(mode, "mode", {"analyze", "design"})
    excitation_type = _validate_choice(excitation_type, "excitation_type", {"base", "force"})
    damping_input_mode = _validate_choice(
        damping_input_mode, "damping_input_mode", {"ratio", "coefficient"}
    )

    mass_kg = _validate_positive(mass_kg, "mass_kg")
    excitation_frequency_hz = _validate_positive(
        excitation_frequency_hz, "excitation_frequency_hz"
    )

    if num_mounts <= 0.0 or abs(num_mounts - round(num_mounts)) > 1e-6:
        raise ValueError("num_mounts must be a positive integer.")
    num_mounts_int = int(round(num_mounts))

    if base_displacement_m < 0.0:
        raise ValueError("base_displacement_m cannot be negative.")
    if force_amplitude_n < 0.0:
        raise ValueError("force_amplitude_n cannot be negative.")
    if max_static_deflection_m < 0.0:
        raise ValueError("max_static_deflection_m cannot be negative.")

    if damping_input_mode == "ratio":
        _validate_positive(damping_ratio, "damping_ratio")
    else:
        _validate_positive(damping_coefficient_ns_per_m, "damping_coefficient_ns_per_m")

    stiffness_input_mode = _validate_choice(
        stiffness_input_mode, "stiffness_input_mode", {"per_mount", "static_deflection"}
    )

    omega_excitation = 2.0 * math.pi * excitation_frequency_hz

    def transmissibility_for_ratio(r_value: float, zeta_value: float) -> float:
        transmissibility, _, _ = _response_terms(r_value, zeta_value)
        return transmissibility

    frequency_ratio = 0.0
    total_stiffness = 0.0
    mount_stiffness = mount_stiffness_n_per_m

    if mode == "analyze":
        if stiffness_input_mode == "per_mount":
            _validate_positive(mount_stiffness_n_per_m, "mount_stiffness_n_per_m")
            total_stiffness = mount_stiffness_n_per_m * num_mounts_int
        else:
            _validate_positive(static_deflection_m, "static_deflection_m")
            total_stiffness = mass_kg * GRAVITY_M_S2 / static_deflection_m
            mount_stiffness = total_stiffness / num_mounts_int
        omega_natural = math.sqrt(total_stiffness / mass_kg)
        frequency_ratio = omega_excitation / omega_natural
    else:
        if not 0.0 < target_transmissibility < 1.0:
            raise ValueError("target_transmissibility must be between 0 and 1 for design mode.")

        def zeta_for_r(r_value: float) -> float:
            omega_natural_local = omega_excitation / r_value
            if damping_input_mode == "ratio":
                return damping_ratio
            return damping_coefficient_ns_per_m / (2.0 * mass_kg * omega_natural_local)

        if damping_input_mode == "coefficient":
            coeff_factor = damping_coefficient_ns_per_m / (2.0 * mass_kg * omega_excitation)
            transmissibility_floor = (2.0 * coeff_factor) / math.sqrt(
                1.0 + (2.0 * coeff_factor) ** 2
            )
            if target_transmissibility < transmissibility_floor:
                raise ValueError(
                    "target_transmissibility is below the asymptotic limit for the "
                    "specified damping coefficient. Reduce damping or increase the "
                    "target."
                )

        r_low = math.sqrt(2.0)
        r_high = r_low * 1.1
        for _ in range(60):
            t_high = transmissibility_for_ratio(r_high, zeta_for_r(r_high))
            if t_high <= target_transmissibility:
                break
            r_high *= 1.5
            if r_high > 1e4:
                raise ValueError(
                    "Unable to bracket a solution for the target transmissibility. "
                    "Check damping inputs or target."
                )

        for _ in range(80):
            r_mid = 0.5 * (r_low + r_high)
            t_mid = transmissibility_for_ratio(r_mid, zeta_for_r(r_mid))
            if t_mid > target_transmissibility:
                r_low = r_mid
            else:
                r_high = r_mid

        frequency_ratio = r_high
        omega_natural = omega_excitation / frequency_ratio
        total_stiffness = mass_kg * omega_natural**2
        mount_stiffness = total_stiffness / num_mounts_int

    omega_natural = math.sqrt(total_stiffness / mass_kg)
    natural_frequency_hz = omega_natural / (2.0 * math.pi)
    static_deflection = mass_kg * GRAVITY_M_S2 / total_stiffness

    if damping_input_mode == "ratio":
        damping_ratio_value = damping_ratio
        damping_coefficient = 2.0 * mass_kg * omega_natural * damping_ratio_value
    else:
        damping_coefficient = damping_coefficient_ns_per_m
        damping_ratio_value = damping_coefficient / (2.0 * mass_kg * omega_natural)

    transmissibility, relative_ratio, magnification = _response_terms(
        frequency_ratio, damping_ratio_value
    )

    absolute_displacement = float("nan")
    relative_displacement = float("nan")
    transmitted_force = float("nan")
    acceleration = float("nan")
    dynamic_magnification = float("nan")

    if excitation_type == "base":
        if base_displacement_m > 0.0:
            absolute_displacement = transmissibility * base_displacement_m
            relative_displacement = relative_ratio * base_displacement_m
            transmitted_force = (
                total_stiffness
                * relative_displacement
                * math.sqrt(1.0 + (2.0 * damping_ratio_value * frequency_ratio) ** 2)
            )
            acceleration = omega_excitation**2 * absolute_displacement
    else:
        dynamic_magnification = magnification
        if force_amplitude_n > 0.0:
            absolute_displacement = (
                force_amplitude_n / total_stiffness * dynamic_magnification
            )
            relative_displacement = absolute_displacement
            transmitted_force = transmissibility * force_amplitude_n
            acceleration = omega_excitation**2 * absolute_displacement

    static_deflection_utilization = float("nan")
    if max_static_deflection_m > 0.0:
        static_deflection_utilization = static_deflection / max_static_deflection_m

    plot_max_ratio = max(5.0, frequency_ratio * 1.5)
    plot_max_ratio = min(plot_max_ratio, 20.0)
    plot_points = 200
    plot_frequency_ratio = [
        plot_max_ratio * idx / (plot_points - 1) for idx in range(plot_points)
    ]
    plot_transmissibility: list[float] = []
    for r_value in plot_frequency_ratio:
        t_value = transmissibility_for_ratio(r_value, damping_ratio_value)
        if not math.isfinite(t_value):
            t_value = float("nan")
        plot_transmissibility.append(t_value)

    results: dict[str, float | list[float]] = {
        "natural_frequency_hz": natural_frequency_hz,
        "natural_angular_frequency_rad_s": omega_natural,
        "total_stiffness_n_per_m": total_stiffness,
        "mount_stiffness_n_per_m": mount_stiffness,
        "static_deflection_m": static_deflection,
        "damping_ratio": damping_ratio_value,
        "damping_coefficient_ns_per_m": damping_coefficient,
        "frequency_ratio": frequency_ratio,
        "transmissibility": transmissibility,
        "isolation_frequency_hz": math.sqrt(2.0) * natural_frequency_hz,
        "isolation_margin": frequency_ratio - math.sqrt(2.0),
        "relative_displacement_amplitude_m": relative_displacement,
        "absolute_displacement_amplitude_m": absolute_displacement,
        "transmitted_force_amplitude_n": transmitted_force,
        "acceleration_amplitude_m_s2": acceleration,
        "dynamic_magnification": dynamic_magnification,
        "static_deflection_utilization": static_deflection_utilization,
        "plot_frequency_ratio": plot_frequency_ratio,
        "plot_transmissibility": plot_transmissibility,
    }

    if mode == "analyze" and stiffness_input_mode == "per_mount":
        results["subst_total_stiffness_n_per_m"] = (
            "k_{total} = n k_{mount} = "
            f"{num_mounts_int} \times {mount_stiffness:.3e} = {total_stiffness:.3e}"
        )
    elif mode == "analyze" and stiffness_input_mode == "static_deflection":
        results["subst_total_stiffness_n_per_m"] = (
            "k_{total} = m g / delta_{static} = "
            f"{mass_kg:.3f} \times {GRAVITY_M_S2:.3f} / {static_deflection_m:.3e} "
            f"= {total_stiffness:.3e}"
        )
    else:
        results["subst_total_stiffness_n_per_m"] = (
            "k_{total} = m \omega_n^2 = "
            f"{mass_kg:.3f} \times {omega_natural:.3f}^2 = {total_stiffness:.3e}"
        )

    results["subst_mount_stiffness_n_per_m"] = (
        f"k_{{mount}} = k_{{total}} / n = {total_stiffness:.3e} / {num_mounts_int} "
        f"= {mount_stiffness:.3e}"
    )
    results["subst_natural_frequency_hz"] = (
        "f_n = (1 / 2\pi) \sqrt{k_{total} / m} = "
        f"(1 / 2\pi) \sqrt{{{total_stiffness:.3e} / {mass_kg:.3f}}} "
        f"= {natural_frequency_hz:.3f}"
    )
    results["subst_frequency_ratio"] = (
        f"r = f_{{exc}} / f_n = {excitation_frequency_hz:.3f} / {natural_frequency_hz:.3f} "
        f"= {frequency_ratio:.3f}"
    )
    results["subst_transmissibility"] = (
        "T = sqrt(1 + (2 zeta r)^2) / sqrt((1 - r^2)^2 + (2 zeta r)^2) = "
        f"{transmissibility:.3f}"
    )
    results["subst_static_deflection_m"] = (
        f"delta_{{static}} = m g / k_{{total}} = {mass_kg:.3f} \times {GRAVITY_M_S2:.3f} "
        f"/ {total_stiffness:.3e} = {static_deflection:.3e}"
    )

    if damping_input_mode == "ratio":
        results["subst_damping_coefficient_ns_per_m"] = (
            "c = 2 m \omega_n zeta = "
            f"2 \times {mass_kg:.3f} \times {omega_natural:.3f} \times "
            f"{damping_ratio_value:.3f} = {damping_coefficient:.3e}"
        )
    else:
        results["subst_damping_ratio"] = (
            "zeta = c / (2 m \omega_n) = "
            f"{damping_coefficient:.3e} / (2 \times {mass_kg:.3f} \times "
            f"{omega_natural:.3f}) = {damping_ratio_value:.3f}"
        )

    return results
