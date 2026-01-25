"""
Fatigue life estimation utilities.

Provides a high-level fatigue life estimator using mean stress correction
and Basquin S-N relationships. Intended for educational and early-stage
design estimation.
"""

from __future__ import annotations

from typing import Dict, List
import math


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be > 0. Got {value}.")




def _mean_stress_equivalent(
    alternating_stress_mpa: float,
    mean_stress_mpa: float,
    ultimate_strength_mpa: float,
    yield_strength_mpa: float,
    method: str,
) -> float:
    method_clean = method.strip().lower()

    if method_clean == "none":
        return alternating_stress_mpa

    if method_clean == "goodman":
        denominator = 1.0 - (mean_stress_mpa / ultimate_strength_mpa)
    elif method_clean == "soderberg":
        denominator = 1.0 - (mean_stress_mpa / yield_strength_mpa)
    elif method_clean == "gerber":
        denominator = 1.0 - (mean_stress_mpa / ultimate_strength_mpa) ** 2
    else:
        raise ValueError(
            "mean_stress_correction must be one of: goodman, soderberg, gerber, none."
        )

    if denominator <= 0.0:
        raise ValueError(
            "Mean stress correction denominator is <= 0. "
            "Reduce mean stress or select a different correction."
        )

    return alternating_stress_mpa / denominator


def _generate_sn_curve(
    fatigue_strength_coeff_mpa: float,
    fatigue_strength_exponent: float,
    endurance_limit_mpa: float,
    n_min: float = 1e3,
    n_max: float = 1e7,
    n_points: int = 60,
) -> Dict[str, List[float]]:
    if n_points < 2:
        raise ValueError("n_points must be >= 2.")
    if n_min <= 0 or n_max <= 0 or n_max <= n_min:
        raise ValueError("n_min and n_max must be positive with n_max > n_min.")

    log_min = math.log10(n_min)
    log_max = math.log10(n_max)
    cycles = []
    stresses = []

    for i in range(n_points):
        log_n = log_min + i * (log_max - log_min) / (n_points - 1)
        n_cycles = 10 ** log_n
        stress = fatigue_strength_coeff_mpa * (2.0 * n_cycles) ** fatigue_strength_exponent
        if endurance_limit_mpa > 0.0:
            stress = max(stress, endurance_limit_mpa)
        cycles.append(n_cycles)
        stresses.append(stress)

    return {
        "cycles": cycles,
        "stress_amplitude_mpa": stresses,
        "endurance_limit_mpa": endurance_limit_mpa,
    }


def _generate_mean_stress_curve(
    mean_stress_mpa: float,
    ultimate_strength_mpa: float,
    yield_strength_mpa: float,
    endurance_limit_mpa: float,
    method: str,
    n_points: int = 60,
) -> Dict[str, List[float]]:
    method_clean = method.strip().lower()
    if method_clean == "soderberg":
        limit = yield_strength_mpa
    else:
        limit = ultimate_strength_mpa

    mean_min = min(0.0, mean_stress_mpa * 1.2)
    mean_max = max(limit * 0.9, mean_stress_mpa * 1.2, 0.0)
    if mean_max == mean_min:
        mean_max = mean_min + 1.0

    mean_values = []
    allowable = []

    for i in range(n_points):
        sigma_m = mean_min + i * (mean_max - mean_min) / (n_points - 1)

        if method_clean == "none":
            sigma_a = endurance_limit_mpa
        elif method_clean == "goodman":
            sigma_a = endurance_limit_mpa * (1.0 - sigma_m / ultimate_strength_mpa)
        elif method_clean == "soderberg":
            sigma_a = endurance_limit_mpa * (1.0 - sigma_m / yield_strength_mpa)
        elif method_clean == "gerber":
            sigma_a = endurance_limit_mpa * (1.0 - (sigma_m / ultimate_strength_mpa) ** 2)
        else:
            raise ValueError(
                "mean_stress_correction must be one of: goodman, soderberg, gerber, none."
            )

        sigma_a = max(0.0, sigma_a)
        mean_values.append(sigma_m)
        allowable.append(sigma_a)

    return {
        "mean_stress_mpa": mean_values,
        "allowable_alternating_mpa": allowable,
    }


def estimate_fatigue_life(
    max_stress_mpa: float,
    min_stress_mpa: float,
    ultimate_strength_mpa: float,
    yield_strength_mpa: float,
    mean_stress_correction: str = "goodman",
    endurance_limit_ratio: float = 0.5,
    surface_factor: float = 1.0,
    size_factor: float = 1.0,
    reliability_factor: float = 1.0,
    fatigue_strength_coeff_ratio: float = 1.5,
    fatigue_strength_exponent: float = -0.09,
    target_life_cycles: float = 1e6,
    required_fatigue_factor: float = 1.5,
    required_yield_factor: float = 1.2,
) -> Dict:
    """
    Estimate fatigue life using mean stress correction and Basquin S-N curves.

    Combines a mean stress correction (Goodman/Gerber/Soderberg) with a
    Basquin relationship to estimate cycles to failure. Endurance limit
    modifiers are applied via correction factors.

    ---Parameters---
    max_stress_mpa : float
        Maximum cyclic stress in MPa for the loading cycle.
    min_stress_mpa : float
        Minimum cyclic stress in MPa for the loading cycle.
    ultimate_strength_mpa : float
        Ultimate tensile strength, S_ut, in MPa.
    yield_strength_mpa : float
        Yield strength, S_y, in MPa.
    mean_stress_correction : str
        Mean stress correction method: goodman, gerber, soderberg, or none.
    endurance_limit_ratio : float
        Ratio S_e' / S_ut before modifiers (typically 0.4-0.6 for steels).
        Set to 0.0 to disable an endurance limit floor.
    surface_factor : float
        Surface finish factor (dimensionless, <= 1.0 typical).
    size_factor : float
        Size factor (dimensionless, <= 1.0 typical).
    reliability_factor : float
        Reliability factor (dimensionless, <= 1.0 typical).
    fatigue_strength_coeff_ratio : float
        Basquin fatigue strength coefficient ratio, sigma_f' / S_ut.
    fatigue_strength_exponent : float
        Basquin exponent b (negative for metals).
    target_life_cycles : float
        Target life in cycles for safety factor comparison.
    required_fatigue_factor : float
        Required fatigue life safety factor (N_f / N_target).
    required_yield_factor : float
        Required yield safety factor (S_y / sigma_peak).

    ---Returns---
    mean_stress_mpa : float
        Mean stress, sigma_m, in MPa.
    alternating_stress_mpa : float
        Alternating stress amplitude, sigma_a, in MPa.
    stress_ratio : float
        Stress ratio R = sigma_min / sigma_max.
    equivalent_stress_mpa : float
        Mean-stress-corrected alternating stress in MPa.
    endurance_limit_mpa : float
        Modified endurance limit S_e in MPa.
    fatigue_strength_coeff_mpa : float
        Basquin fatigue strength coefficient sigma_f' in MPa.
    estimated_life_cycles : float
        Estimated cycles to failure (N_f). Infinity indicates endurance.
    life_safety_factor : float
        Safety factor based on target life (N_f / N_target).
    fatigue_safety_factor : float
        Endurance safety factor (S_e / sigma_a,eq).
    yield_safety_factor : float
        Static safety factor (S_y / sigma_peak).
    status : str
        Overall assessment: acceptable, marginal, or unacceptable.
    recommendations : list
        List of action recommendations based on margins.
    sn_curve : dict
        S-N curve data for plotting.
    mean_stress_curve : dict
        Mean stress diagram data for plotting.
    subst_equivalent_stress_mpa : str
        Substituted equation string for mean stress correction.
    subst_estimated_life_cycles : str
        Substituted equation string for Basquin life.
    subst_fatigue_safety_factor : str
        Substituted equation string for fatigue safety factor.
    subst_yield_safety_factor : str
        Substituted equation string for yield safety factor.
    subst_life_safety_factor : str
        Substituted equation string for life safety factor.

    ---LaTeX---
    \\sigma_m = \\frac{\\sigma_{max} + \\sigma_{min}}{2}
    \\sigma_a = \\frac{\\sigma_{max} - \\sigma_{min}}{2}
    S_e = S_e' \\cdot k_s \\cdot k_d \\cdot k_r
    \\sigma_{a,eq} = \\frac{\\sigma_a}{1 - \\sigma_m / S_{ut}}
    \\sigma_{a,eq} = \\sigma_f' (2N)^b
    N = \\frac{1}{2} \\left( \\frac{\\sigma_{a,eq}}{\\sigma_f'} \\right)^{1/b}
    SF_y = \\frac{S_y}{\\sigma_{peak}}
    """
    if max_stress_mpa < min_stress_mpa:
        raise ValueError("max_stress_mpa must be >= min_stress_mpa.")

    _validate_positive("ultimate_strength_mpa", ultimate_strength_mpa)
    _validate_positive("yield_strength_mpa", yield_strength_mpa)
    if endurance_limit_ratio < 0:
        raise ValueError("endurance_limit_ratio must be >= 0.")
    _validate_positive("surface_factor", surface_factor)
    _validate_positive("size_factor", size_factor)
    _validate_positive("reliability_factor", reliability_factor)
    _validate_positive("fatigue_strength_coeff_ratio", fatigue_strength_coeff_ratio)
    _validate_positive("target_life_cycles", target_life_cycles)
    _validate_positive("required_fatigue_factor", required_fatigue_factor)
    _validate_positive("required_yield_factor", required_yield_factor)
    if fatigue_strength_exponent >= 0.0:
        raise ValueError("fatigue_strength_exponent must be negative for metals.")

    alternating_stress_mpa = 0.5 * (max_stress_mpa - min_stress_mpa)
    if alternating_stress_mpa <= 0.0:
        raise ValueError("Alternating stress must be positive.")

    mean_stress_mpa = 0.5 * (max_stress_mpa + min_stress_mpa)
    stress_ratio = min_stress_mpa / max_stress_mpa if max_stress_mpa != 0 else 0.0

    endurance_limit_mpa = (
        endurance_limit_ratio
        * ultimate_strength_mpa
        * surface_factor
        * size_factor
        * reliability_factor
    )

    fatigue_strength_coeff_mpa = fatigue_strength_coeff_ratio * ultimate_strength_mpa

    equivalent_stress_mpa = _mean_stress_equivalent(
        alternating_stress_mpa,
        mean_stress_mpa,
        ultimate_strength_mpa,
        yield_strength_mpa,
        mean_stress_correction,
    )

    fatigue_safety_factor = (
        endurance_limit_mpa / equivalent_stress_mpa
        if equivalent_stress_mpa > 0.0
        else float("inf")
    )

    peak_stress_mpa = max(abs(max_stress_mpa), abs(min_stress_mpa))
    yield_safety_factor = (
        yield_strength_mpa / peak_stress_mpa if peak_stress_mpa > 0 else float("inf")
    )

    if equivalent_stress_mpa <= endurance_limit_mpa:
        estimated_life_cycles = float("inf")
        life_safety_factor = float("inf")
    else:
        estimated_life_cycles = 0.5 * (
            equivalent_stress_mpa / fatigue_strength_coeff_mpa
        ) ** (1.0 / fatigue_strength_exponent)
        life_safety_factor = estimated_life_cycles / target_life_cycles

    life_ok = life_safety_factor >= required_fatigue_factor or math.isinf(life_safety_factor)
    yield_ok = yield_safety_factor >= required_yield_factor

    if life_ok and yield_ok:
        status = "acceptable"
    elif life_safety_factor < 1.0 or yield_safety_factor < 1.0:
        status = "unacceptable"
    else:
        status = "marginal"

    recommendations = []
    if not life_ok:
        recommendations.append(
            "Reduce alternating stress or improve surface finish to meet fatigue life."
        )
    if not yield_ok:
        recommendations.append(
            "Reduce peak stress or increase section size to meet yield margin."
        )
    if mean_stress_correction.strip().lower() == "none":
        recommendations.append(
            "Mean stress correction is disabled; consider Goodman or Gerber for tension mean stress."
        )

    if not recommendations:
        recommendations.append("Margins meet targets. Consider validating assumptions with test data.")

    sn_curve = _generate_sn_curve(
        fatigue_strength_coeff_mpa=fatigue_strength_coeff_mpa,
        fatigue_strength_exponent=fatigue_strength_exponent,
        endurance_limit_mpa=endurance_limit_mpa,
    )
    mean_stress_curve = _generate_mean_stress_curve(
        mean_stress_mpa=mean_stress_mpa,
        ultimate_strength_mpa=ultimate_strength_mpa,
        yield_strength_mpa=yield_strength_mpa,
        endurance_limit_mpa=endurance_limit_mpa,
        method=mean_stress_correction,
    )

    method_clean = mean_stress_correction.strip().lower()
    if method_clean == "none":
        subst_equivalent = (
            f"\\sigma_{{a,eq}} = \\sigma_a = {alternating_stress_mpa:.1f}\\text{{ MPa}}"
        )
    elif method_clean == "goodman":
        subst_equivalent = (
            f"\\sigma_{{a,eq}} = \\frac{{\\sigma_a}}{{1 - \\sigma_m/S_{{ut}}}}"
            f" = \\frac{{{alternating_stress_mpa:.1f}}}{{1 - {mean_stress_mpa:.1f}/{ultimate_strength_mpa:.1f}}}"
            f" = {equivalent_stress_mpa:.1f}\\text{{ MPa}}"
        )
    elif method_clean == "soderberg":
        subst_equivalent = (
            f"\\sigma_{{a,eq}} = \\frac{{\\sigma_a}}{{1 - \\sigma_m/S_{{y}}}}"
            f" = \\frac{{{alternating_stress_mpa:.1f}}}{{1 - {mean_stress_mpa:.1f}/{yield_strength_mpa:.1f}}}"
            f" = {equivalent_stress_mpa:.1f}\\text{{ MPa}}"
        )
    else:
        subst_equivalent = (
            f"\\sigma_{{a,eq}} = \\frac{{\\sigma_a}}{{1 - (\\sigma_m/S_{{ut}})^2}}"
            f" = \\frac{{{alternating_stress_mpa:.1f}}}{{1 - ({mean_stress_mpa:.1f}/{ultimate_strength_mpa:.1f})^2}}"
            f" = {equivalent_stress_mpa:.1f}\\text{{ MPa}}"
        )

    if math.isinf(estimated_life_cycles):
        subst_life = (
            f"\\sigma_{{a,eq}} \\le S_e \\Rightarrow N_f \\to \\infty"
        )
    else:
        exponent_inv = 1.0 / fatigue_strength_exponent
        subst_life = (
            "\\sigma_{a,eq} = \\sigma_f' (2N)^b"
            f" \\Rightarrow N = 0.5 \\left(\\frac{{{equivalent_stress_mpa:.1f}}}{{{fatigue_strength_coeff_mpa:.1f}}}\\right)^{{{exponent_inv:.3f}}}"
            f" = {estimated_life_cycles:.2e}"
        )

    if math.isinf(life_safety_factor):
        subst_life_factor = "SF_L = N_f / N_{target} = \\infty"
    else:
        subst_life_factor = (
            f"SF_L = \\frac{{N_f}}{{N_{{target}}}}"
            f" = \\frac{{{estimated_life_cycles:.2e}}}{{{target_life_cycles:.2e}}}"
            f" = {life_safety_factor:.2f}"
        )

    subst_fatigue_factor = (
        f"SF_D = \\frac{{S_e}}{{\\sigma_{{a,eq}}}}"
        f" = \\frac{{{endurance_limit_mpa:.1f}}}{{{equivalent_stress_mpa:.1f}}}"
        f" = {fatigue_safety_factor:.2f}"
    )

    subst_yield_factor = (
        f"SF_y = \\frac{{S_y}}{{\\sigma_{{peak}}}}"
        f" = \\frac{{{yield_strength_mpa:.1f}}}{{{peak_stress_mpa:.1f}}}"
        f" = {yield_safety_factor:.2f}"
    )

    sn_curve.update(
        {
            "current_cycles": estimated_life_cycles,
            "current_stress_mpa": equivalent_stress_mpa,
        }
    )
    mean_stress_curve.update(
        {
            "current_mean_mpa": mean_stress_mpa,
            "current_alt_mpa": alternating_stress_mpa,
        }
    )

    return {
        # Primary outputs
        "estimated_life_cycles": estimated_life_cycles,
        "life_safety_factor": life_safety_factor,
        "fatigue_safety_factor": fatigue_safety_factor,
        "yield_safety_factor": yield_safety_factor,
        "equivalent_stress_mpa": equivalent_stress_mpa,
        # Intermediate values
        "mean_stress_mpa": mean_stress_mpa,
        "alternating_stress_mpa": alternating_stress_mpa,
        "stress_ratio": stress_ratio,
        "endurance_limit_mpa": endurance_limit_mpa,
        "fatigue_strength_coeff_mpa": fatigue_strength_coeff_mpa,
        # Status
        "status": status,
        "recommendations": recommendations,
        # Visualization data
        "sn_curve": sn_curve,
        "mean_stress_curve": mean_stress_curve,
        # Substituted equations
        "subst_equivalent_stress_mpa": subst_equivalent,
        "subst_estimated_life_cycles": subst_life,
        "subst_fatigue_safety_factor": subst_fatigue_factor,
        "subst_yield_safety_factor": subst_yield_factor,
        "subst_life_safety_factor": subst_life_factor,
    }
