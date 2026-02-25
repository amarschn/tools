"""
Fatigue life estimation utilities.

Supports metals and polymers using a stress-life model with selectable
mean stress correction and optional stress-uncertainty bounding.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


# -----------------------------------------------------------------------------
# Material preset databases
# -----------------------------------------------------------------------------

METAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "custom": {
        "display_name": "Custom Metal",
        "supports_endurance_limit": True,
    },
    "steel_1045": {
        "display_name": "Steel 1045 (normalized)",
        "ultimate_strength_mpa": 625.0,
        "yield_strength_mpa": 530.0,
        "endurance_limit_ratio": 0.50,
        "fatigue_strength_coeff_ratio": 1.55,
        "fatigue_strength_exponent": -0.090,
        "surface_factor": 1.00,
        "size_factor": 1.00,
        "reliability_factor": 1.00,
        "supports_endurance_limit": True,
    },
    "aluminum_6061_t6": {
        "display_name": "Aluminum 6061-T6",
        "ultimate_strength_mpa": 310.0,
        "yield_strength_mpa": 276.0,
        "endurance_limit_ratio": 0.0,
        "fatigue_strength_coeff_ratio": 1.45,
        "fatigue_strength_exponent": -0.095,
        "surface_factor": 1.00,
        "size_factor": 1.00,
        "reliability_factor": 1.00,
        "supports_endurance_limit": False,
    },
    "ti_6al_4v": {
        "display_name": "Ti-6Al-4V",
        "ultimate_strength_mpa": 950.0,
        "yield_strength_mpa": 880.0,
        "endurance_limit_ratio": 0.45,
        "fatigue_strength_coeff_ratio": 1.60,
        "fatigue_strength_exponent": -0.085,
        "surface_factor": 1.00,
        "size_factor": 1.00,
        "reliability_factor": 1.00,
        "supports_endurance_limit": True,
    },
}

POLYMER_PRESETS: Dict[str, Dict[str, Any]] = {
    "custom": {
        "display_name": "Custom Polymer",
        "supports_endurance_limit": False,
    },
    "abs": {
        "display_name": "ABS (injection molded)",
        "ultimate_strength_mpa": 45.0,
        "yield_strength_mpa": 40.0,
        "endurance_limit_ratio": 0.0,
        "fatigue_strength_coeff_ratio": 1.20,
        "fatigue_strength_exponent": -0.105,
        "surface_factor": 1.00,
        "size_factor": 1.00,
        "reliability_factor": 1.00,
        "supports_endurance_limit": False,
    },
    "pc": {
        "display_name": "Polycarbonate (PC)",
        "ultimate_strength_mpa": 67.0,
        "yield_strength_mpa": 60.0,
        "endurance_limit_ratio": 0.0,
        "fatigue_strength_coeff_ratio": 1.25,
        "fatigue_strength_exponent": -0.095,
        "surface_factor": 1.00,
        "size_factor": 1.00,
        "reliability_factor": 1.00,
        "supports_endurance_limit": False,
    },
    "pom": {
        "display_name": "Acetal / POM",
        "ultimate_strength_mpa": 70.0,
        "yield_strength_mpa": 65.0,
        "endurance_limit_ratio": 0.0,
        "fatigue_strength_coeff_ratio": 1.30,
        "fatigue_strength_exponent": -0.090,
        "surface_factor": 1.00,
        "size_factor": 1.00,
        "reliability_factor": 1.00,
        "supports_endurance_limit": False,
    },
    "pa6": {
        "display_name": "Nylon PA6 (dry as molded)",
        "ultimate_strength_mpa": 75.0,
        "yield_strength_mpa": 65.0,
        "endurance_limit_ratio": 0.0,
        "fatigue_strength_coeff_ratio": 1.18,
        "fatigue_strength_exponent": -0.110,
        "surface_factor": 1.00,
        "size_factor": 1.00,
        "reliability_factor": 1.00,
        "supports_endurance_limit": False,
    },
    "peek": {
        "display_name": "PEEK (unfilled)",
        "ultimate_strength_mpa": 100.0,
        "yield_strength_mpa": 90.0,
        "endurance_limit_ratio": 0.0,
        "fatigue_strength_coeff_ratio": 1.30,
        "fatigue_strength_exponent": -0.085,
        "surface_factor": 1.00,
        "size_factor": 1.00,
        "reliability_factor": 1.00,
        "supports_endurance_limit": False,
    },
}


def get_fatigue_material_presets() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Return fatigue material presets grouped by material family."""
    return {
        "metal": METAL_PRESETS,
        "polymer": POLYMER_PRESETS,
    }


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be > 0. Got {value}.")


def _lookup_preset(material_family: str, material_preset: str) -> Dict[str, Any]:
    family = material_family.strip().lower()
    preset = material_preset.strip().lower()

    if family == "metal":
        database = METAL_PRESETS
    elif family == "polymer":
        database = POLYMER_PRESETS
    else:
        raise ValueError("material_family must be one of: metal, polymer.")

    if preset not in database:
        valid = ", ".join(sorted(database.keys()))
        raise ValueError(
            f"Unknown preset '{material_preset}' for material_family='{material_family}'. "
            f"Valid presets: {valid}."
        )

    return database[preset]


def _resolve_material_properties(
    material_family: str,
    material_preset: str,
    ultimate_strength_mpa: float,
    yield_strength_mpa: float,
    endurance_limit_ratio: float,
    surface_factor: float,
    size_factor: float,
    reliability_factor: float,
    fatigue_strength_coeff_ratio: float,
    fatigue_strength_exponent: float,
) -> Dict[str, Any]:
    family = material_family.strip().lower()
    preset = material_preset.strip().lower()
    if family not in {"metal", "polymer"}:
        raise ValueError("material_family must be one of: metal, polymer.")

    resolved = {
        "material_family": family,
        "material_preset": preset,
        "material_preset_name": "Custom" if preset == "custom" else preset,
        "ultimate_strength_mpa": ultimate_strength_mpa,
        "yield_strength_mpa": yield_strength_mpa,
        "endurance_limit_ratio": endurance_limit_ratio,
        "surface_factor": surface_factor,
        "size_factor": size_factor,
        "reliability_factor": reliability_factor,
        "fatigue_strength_coeff_ratio": fatigue_strength_coeff_ratio,
        "fatigue_strength_exponent": fatigue_strength_exponent,
        "supports_endurance_limit": family == "metal",
    }

    if preset != "custom":
        preset_data = _lookup_preset(family, preset)
        resolved["material_preset_name"] = str(preset_data.get("display_name", preset))
        resolved["supports_endurance_limit"] = bool(
            preset_data.get("supports_endurance_limit", family == "metal")
        )

    return resolved


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
    has_endurance_limit: bool,
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
    cycles: List[float] = []
    stresses: List[float] = []

    for i in range(n_points):
        log_n = log_min + i * (log_max - log_min) / (n_points - 1)
        n_cycles = 10 ** log_n
        stress = fatigue_strength_coeff_mpa * (2.0 * n_cycles) ** fatigue_strength_exponent

        if has_endurance_limit and endurance_limit_mpa > 0.0:
            stress = max(stress, endurance_limit_mpa)

        cycles.append(n_cycles)
        stresses.append(stress)

    return {
        "cycles": cycles,
        "stress_amplitude_mpa": stresses,
        "endurance_limit_mpa": endurance_limit_mpa,
        "has_endurance_limit": has_endurance_limit,
    }


def _generate_mean_stress_curve(
    mean_stress_mpa: float,
    ultimate_strength_mpa: float,
    yield_strength_mpa: float,
    reference_stress_mpa: float,
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

    mean_values: List[float] = []
    allowable: List[float] = []

    for i in range(n_points):
        sigma_m = mean_min + i * (mean_max - mean_min) / (n_points - 1)

        if method_clean == "none":
            sigma_a = reference_stress_mpa
        elif method_clean == "goodman":
            sigma_a = reference_stress_mpa * (1.0 - sigma_m / ultimate_strength_mpa)
        elif method_clean == "soderberg":
            sigma_a = reference_stress_mpa * (1.0 - sigma_m / yield_strength_mpa)
        elif method_clean == "gerber":
            sigma_a = reference_stress_mpa * (1.0 - (sigma_m / ultimate_strength_mpa) ** 2)
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


def _polymer_derating_components(
    temperature_c: float,
    load_frequency_hz: float,
    moisture_derating_factor: float,
    chemical_derating_factor: float,
    uv_derating_factor: float,
) -> Dict[str, float]:
    _validate_positive("load_frequency_hz", load_frequency_hz)
    _validate_positive("moisture_derating_factor", moisture_derating_factor)
    _validate_positive("chemical_derating_factor", chemical_derating_factor)
    _validate_positive("uv_derating_factor", uv_derating_factor)

    if temperature_c > 23.0:
        temperature_factor = max(0.35, 1.0 - 0.005 * (temperature_c - 23.0))
    else:
        # Slight benefit below room temperature, capped for conservative behavior.
        temperature_factor = min(1.06, 1.0 + 0.001 * (23.0 - temperature_c))

    # Higher frequency can increase self-heating and reduce life in polymers.
    frequency_factor = max(0.60, 1.0 - 0.025 * max(load_frequency_hz - 2.0, 0.0))

    combined = (
        temperature_factor
        * frequency_factor
        * moisture_derating_factor
        * chemical_derating_factor
        * uv_derating_factor
    )
    combined = max(0.20, min(1.15, combined))

    return {
        "temperature_factor": temperature_factor,
        "frequency_factor": frequency_factor,
        "moisture_factor": moisture_derating_factor,
        "chemical_factor": chemical_derating_factor,
        "uv_factor": uv_derating_factor,
        "combined_factor": combined,
    }


def _cycles_to_hours(cycles: float, load_frequency_hz: float) -> float:
    if math.isinf(cycles):
        return float("inf")
    if load_frequency_hz <= 0.0:
        return float("inf")
    return cycles / (load_frequency_hz * 3600.0)


def _evaluate_single_case(
    max_stress_mpa: float,
    min_stress_mpa: float,
    ultimate_strength_mpa: float,
    yield_strength_mpa: float,
    mean_stress_correction: str,
    endurance_limit_mpa: float,
    has_endurance_limit: bool,
    fatigue_strength_coeff_mpa: float,
    fatigue_strength_exponent: float,
    target_life_cycles: float,
    load_frequency_hz: float,
) -> Dict[str, Any]:
    alternating_stress_mpa = 0.5 * (max_stress_mpa - min_stress_mpa)
    if alternating_stress_mpa <= 0.0:
        raise ValueError("Alternating stress must be positive.")

    mean_stress_mpa = 0.5 * (max_stress_mpa + min_stress_mpa)
    stress_ratio = min_stress_mpa / max_stress_mpa if max_stress_mpa != 0 else 0.0

    equivalent_stress_mpa = _mean_stress_equivalent(
        alternating_stress_mpa,
        mean_stress_mpa,
        ultimate_strength_mpa,
        yield_strength_mpa,
        mean_stress_correction,
    )

    if has_endurance_limit and endurance_limit_mpa > 0.0:
        reference_stress_mpa = endurance_limit_mpa
        reference_stress_basis = "endurance_limit"
    else:
        reference_stress_mpa = fatigue_strength_coeff_mpa * (
            2.0 * target_life_cycles
        ) ** fatigue_strength_exponent
        reference_stress_basis = "target_life"

    fatigue_safety_factor = (
        reference_stress_mpa / equivalent_stress_mpa
        if equivalent_stress_mpa > 0.0
        else float("inf")
    )

    peak_stress_mpa = max(abs(max_stress_mpa), abs(min_stress_mpa))
    yield_safety_factor = (
        yield_strength_mpa / peak_stress_mpa if peak_stress_mpa > 0 else float("inf")
    )

    if has_endurance_limit and equivalent_stress_mpa <= endurance_limit_mpa:
        estimated_life_cycles = float("inf")
        life_safety_factor = float("inf")
    else:
        estimated_life_cycles = 0.5 * (
            equivalent_stress_mpa / fatigue_strength_coeff_mpa
        ) ** (1.0 / fatigue_strength_exponent)
        life_safety_factor = estimated_life_cycles / target_life_cycles

    sn_curve = _generate_sn_curve(
        fatigue_strength_coeff_mpa=fatigue_strength_coeff_mpa,
        fatigue_strength_exponent=fatigue_strength_exponent,
        endurance_limit_mpa=endurance_limit_mpa,
        has_endurance_limit=has_endurance_limit,
    )
    mean_stress_curve = _generate_mean_stress_curve(
        mean_stress_mpa=mean_stress_mpa,
        ultimate_strength_mpa=ultimate_strength_mpa,
        yield_strength_mpa=yield_strength_mpa,
        reference_stress_mpa=reference_stress_mpa,
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
        subst_life = "\\sigma_{a,eq} \\le S_e \\Rightarrow N_f \\to \\infty"
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

    if reference_stress_basis == "endurance_limit":
        subst_fatigue_factor = (
            f"SF_D = \\frac{{S_e}}{{\\sigma_{{a,eq}}}}"
            f" = \\frac{{{reference_stress_mpa:.1f}}}{{{equivalent_stress_mpa:.1f}}}"
            f" = {fatigue_safety_factor:.2f}"
        )
    else:
        subst_fatigue_factor = (
            f"\\sigma_{{a,target}} = \\sigma_f' (2N_{{target}})^b = {reference_stress_mpa:.1f}\\text{{ MPa}},\\;"
            f" SF_D = \\frac{{\\sigma_{{a,target}}}}{{\\sigma_{{a,eq}}}}"
            f" = \\frac{{{reference_stress_mpa:.1f}}}{{{equivalent_stress_mpa:.1f}}}"
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
            "reference_stress_mpa": reference_stress_mpa,
            "reference_stress_basis": reference_stress_basis,
        }
    )
    mean_stress_curve.update(
        {
            "current_mean_mpa": mean_stress_mpa,
            "current_alt_mpa": alternating_stress_mpa,
            "reference_stress_mpa": reference_stress_mpa,
            "reference_stress_basis": reference_stress_basis,
        }
    )

    return {
        "estimated_life_cycles": estimated_life_cycles,
        "estimated_life_hours": _cycles_to_hours(estimated_life_cycles, load_frequency_hz),
        "life_safety_factor": life_safety_factor,
        "fatigue_safety_factor": fatigue_safety_factor,
        "yield_safety_factor": yield_safety_factor,
        "strength_safety_factor": yield_safety_factor,
        "equivalent_stress_mpa": equivalent_stress_mpa,
        "mean_stress_mpa": mean_stress_mpa,
        "alternating_stress_mpa": alternating_stress_mpa,
        "stress_ratio": stress_ratio,
        "endurance_limit_mpa": endurance_limit_mpa,
        "fatigue_strength_coeff_mpa": fatigue_strength_coeff_mpa,
        "reference_stress_mpa": reference_stress_mpa,
        "reference_stress_basis": reference_stress_basis,
        "peak_stress_mpa": peak_stress_mpa,
        "sn_curve": sn_curve,
        "mean_stress_curve": mean_stress_curve,
        "subst_equivalent_stress_mpa": subst_equivalent,
        "subst_estimated_life_cycles": subst_life,
        "subst_fatigue_safety_factor": subst_fatigue_factor,
        "subst_yield_safety_factor": subst_yield_factor,
        "subst_life_safety_factor": subst_life_factor,
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
    material_family: str = "metal",
    material_preset: str = "custom",
    temperature_c: float = 23.0,
    load_frequency_hz: float = 2.0,
    moisture_derating_factor: float = 1.0,
    chemical_derating_factor: float = 1.0,
    uv_derating_factor: float = 1.0,
    stress_uncertainty_pct: float = 0.0,
) -> Dict[str, Any]:
    r"""
    Estimate fatigue life using mean stress correction and Basquin S-N curves.

    Supports both metal and polymer workflows. Polymer mode applies optional
    environmental and rate derating and disables the infinite-life assumption
    by default.

    ---Parameters---
    max_stress_mpa : float
        Maximum cyclic stress in MPa for the loading cycle.
    min_stress_mpa : float
        Minimum cyclic stress in MPa for the loading cycle.
    ultimate_strength_mpa : float
        Ultimate tensile strength, S_ut, in MPa.
    yield_strength_mpa : float
        Yield or allowable static strength, S_y, in MPa.
    mean_stress_correction : str
        Mean stress correction method: goodman, gerber, soderberg, or none.
    endurance_limit_ratio : float
        Ratio S_e' / S_ut before modifiers. For polymers, this is not used as
        an infinite-life floor unless explicitly represented by test data.
    surface_factor : float
        Surface finish factor (dimensionless, <= 1.0 typical).
    size_factor : float
        Size factor (dimensionless, <= 1.0 typical).
    reliability_factor : float
        Reliability factor (dimensionless, <= 1.0 typical).
    fatigue_strength_coeff_ratio : float
        Basquin fatigue strength coefficient ratio, sigma_f' / S_ut.
    fatigue_strength_exponent : float
        Basquin exponent b (negative for stress-life usage).
    target_life_cycles : float
        Target life in cycles for safety factor comparison.
    required_fatigue_factor : float
        Required fatigue life safety factor (N_f / N_target).
    required_yield_factor : float
        Required yield safety factor (S_y / sigma_peak).
    material_family : str
        Material family, either metal or polymer.
    material_preset : str
        Preset key for the selected material family, or custom. In the UI,
        selecting a preset pre-fills material properties; this flag also
        controls preset-specific behavior (for example endurance support).
    temperature_c : float
        Service temperature in deg C; used for polymer derating.
    load_frequency_hz : float
        Cyclic loading frequency in Hz; used for polymer derating and
        converting cycles to hours.
    moisture_derating_factor : float
        User-selected multiplier for moisture effects (<=1.0 reduces life).
    chemical_derating_factor : float
        User-selected multiplier for chemical exposure effects.
    uv_derating_factor : float
        User-selected multiplier for UV/weathering effects.
    stress_uncertainty_pct : float
        Symmetric uncertainty percentage applied to stress magnitude for
        optimistic and conservative life bounds.

    ---Returns---
    estimated_life_cycles : float
        Nominal estimated cycles to failure, N_f.
    estimated_life_hours : float
        Nominal life in hours based on loading frequency.
    life_safety_factor : float
        Safety factor based on target life (N_f / N_target).
    fatigue_safety_factor : float
        Stress-based fatigue margin relative to reference allowable stress.
    yield_safety_factor : float
        Static safety factor (S_y / sigma_peak).
    strength_safety_factor : float
        Alias of yield_safety_factor for polymer workflows.
    equivalent_stress_mpa : float
        Mean-stress-corrected alternating stress in MPa.
    mean_stress_mpa : float
        Mean stress, sigma_m, in MPa.
    alternating_stress_mpa : float
        Alternating stress amplitude, sigma_a, in MPa.
    stress_ratio : float
        Stress ratio R = sigma_min / sigma_max.
    endurance_limit_mpa : float
        Modified endurance limit S_e in MPa (metal mode only for infinite life).
    fatigue_strength_coeff_mpa : float
        Basquin fatigue strength coefficient sigma_f' in MPa.
    reference_stress_mpa : float
        Reference allowable alternating stress used in fatigue safety factor.
    reference_stress_basis : str
        Basis for reference stress: endurance_limit or target_life.
    material_family : str
        Resolved material family used by the calculation.
    material_preset : str
        Resolved material preset key used by the calculation.
    material_preset_name : str
        Display name of the selected preset.
    polymer_derating_factor : float
        Combined polymer derating factor applied to stress-life strengths.
    temperature_factor : float
        Temperature component of polymer derating.
    frequency_factor : float
        Frequency component of polymer derating.
    moisture_factor : float
        Moisture derating component applied in polymer mode.
    chemical_factor : float
        Chemical exposure derating component applied in polymer mode.
    uv_factor : float
        UV/weathering derating component applied in polymer mode.
    uncertainty_active : bool
        True when stress uncertainty bounds are evaluated.
    conservative_life_cycles : float
        Life at increased stress (upper uncertainty bound).
    optimistic_life_cycles : float
        Life at reduced stress (lower uncertainty bound).
    conservative_life_safety_factor : float
        Life safety factor for conservative stress bound.
    optimistic_life_safety_factor : float
        Life safety factor for optimistic stress bound.
    status : str
        Overall assessment: acceptable, marginal, or unacceptable.
    recommendations : list
        Action recommendations based on margins and model assumptions.
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
    \sigma_m = \frac{\sigma_{max} + \sigma_{min}}{2}
    \sigma_a = \frac{\sigma_{max} - \sigma_{min}}{2}
    S_e = S_e' \cdot k_s \cdot k_d \cdot k_r
    \sigma_{a,eq} = \frac{\sigma_a}{1 - \sigma_m / S_{ut}}
    \sigma_{a,eq} = \sigma_f' (2N)^b
    N = \frac{1}{2} \left( \frac{\sigma_{a,eq}}{\sigma_f'} \right)^{1/b}
    SF_L = \frac{N_f}{N_{target}}
    SF_y = \frac{S_y}{\sigma_{peak}}
    """
    if max_stress_mpa < min_stress_mpa:
        raise ValueError("max_stress_mpa must be >= min_stress_mpa.")

    if endurance_limit_ratio < 0:
        raise ValueError("endurance_limit_ratio must be >= 0.")
    if fatigue_strength_exponent >= 0.0:
        raise ValueError("fatigue_strength_exponent must be negative for stress-life usage.")
    if stress_uncertainty_pct < 0.0 or stress_uncertainty_pct > 95.0:
        raise ValueError("stress_uncertainty_pct must be between 0 and 95.")

    _validate_positive("ultimate_strength_mpa", ultimate_strength_mpa)
    _validate_positive("yield_strength_mpa", yield_strength_mpa)
    _validate_positive("surface_factor", surface_factor)
    _validate_positive("size_factor", size_factor)
    _validate_positive("reliability_factor", reliability_factor)
    _validate_positive("fatigue_strength_coeff_ratio", fatigue_strength_coeff_ratio)
    _validate_positive("target_life_cycles", target_life_cycles)
    _validate_positive("required_fatigue_factor", required_fatigue_factor)
    _validate_positive("required_yield_factor", required_yield_factor)
    _validate_positive("load_frequency_hz", load_frequency_hz)

    resolved = _resolve_material_properties(
        material_family=material_family,
        material_preset=material_preset,
        ultimate_strength_mpa=ultimate_strength_mpa,
        yield_strength_mpa=yield_strength_mpa,
        endurance_limit_ratio=endurance_limit_ratio,
        surface_factor=surface_factor,
        size_factor=size_factor,
        reliability_factor=reliability_factor,
        fatigue_strength_coeff_ratio=fatigue_strength_coeff_ratio,
        fatigue_strength_exponent=fatigue_strength_exponent,
    )

    family = str(resolved["material_family"])
    preset = str(resolved["material_preset"])

    ultimate_strength_mpa = float(resolved["ultimate_strength_mpa"])
    yield_strength_mpa = float(resolved["yield_strength_mpa"])
    endurance_limit_ratio = float(resolved["endurance_limit_ratio"])
    surface_factor = float(resolved["surface_factor"])
    size_factor = float(resolved["size_factor"])
    reliability_factor = float(resolved["reliability_factor"])
    fatigue_strength_coeff_ratio = float(resolved["fatigue_strength_coeff_ratio"])
    fatigue_strength_exponent = float(resolved["fatigue_strength_exponent"])

    _validate_positive("resolved ultimate_strength_mpa", ultimate_strength_mpa)
    _validate_positive("resolved yield_strength_mpa", yield_strength_mpa)
    _validate_positive("resolved surface_factor", surface_factor)
    _validate_positive("resolved size_factor", size_factor)
    _validate_positive("resolved reliability_factor", reliability_factor)
    _validate_positive(
        "resolved fatigue_strength_coeff_ratio", fatigue_strength_coeff_ratio
    )
    if fatigue_strength_exponent >= 0.0:
        raise ValueError("Resolved fatigue_strength_exponent must be negative.")

    if family == "polymer":
        polymer_factors = _polymer_derating_components(
            temperature_c=temperature_c,
            load_frequency_hz=load_frequency_hz,
            moisture_derating_factor=moisture_derating_factor,
            chemical_derating_factor=chemical_derating_factor,
            uv_derating_factor=uv_derating_factor,
        )
    else:
        polymer_factors = {
            "temperature_factor": 1.0,
            "frequency_factor": 1.0,
            "moisture_factor": 1.0,
            "chemical_factor": 1.0,
            "uv_factor": 1.0,
            "combined_factor": 1.0,
        }

    property_derating_factor = float(polymer_factors["combined_factor"])

    endurance_limit_mpa = (
        endurance_limit_ratio
        * ultimate_strength_mpa
        * surface_factor
        * size_factor
        * reliability_factor
        * property_derating_factor
    )

    fatigue_strength_coeff_mpa = (
        fatigue_strength_coeff_ratio
        * ultimate_strength_mpa
        * property_derating_factor
    )

    supports_endurance_limit = bool(resolved["supports_endurance_limit"])
    if not supports_endurance_limit:
        endurance_limit_mpa = 0.0
    has_endurance_limit = supports_endurance_limit and endurance_limit_mpa > 0.0

    nominal = _evaluate_single_case(
        max_stress_mpa=max_stress_mpa,
        min_stress_mpa=min_stress_mpa,
        ultimate_strength_mpa=ultimate_strength_mpa,
        yield_strength_mpa=yield_strength_mpa,
        mean_stress_correction=mean_stress_correction,
        endurance_limit_mpa=endurance_limit_mpa,
        has_endurance_limit=has_endurance_limit,
        fatigue_strength_coeff_mpa=fatigue_strength_coeff_mpa,
        fatigue_strength_exponent=fatigue_strength_exponent,
        target_life_cycles=target_life_cycles,
        load_frequency_hz=load_frequency_hz,
    )

    uncertainty_active = stress_uncertainty_pct > 0.0
    conservative_case = nominal
    optimistic_case = nominal

    if uncertainty_active:
        upper_factor = 1.0 + stress_uncertainty_pct / 100.0
        lower_factor = max(0.05, 1.0 - stress_uncertainty_pct / 100.0)

        conservative_case = _evaluate_single_case(
            max_stress_mpa=max_stress_mpa * upper_factor,
            min_stress_mpa=min_stress_mpa * upper_factor,
            ultimate_strength_mpa=ultimate_strength_mpa,
            yield_strength_mpa=yield_strength_mpa,
            mean_stress_correction=mean_stress_correction,
            endurance_limit_mpa=endurance_limit_mpa,
            has_endurance_limit=has_endurance_limit,
            fatigue_strength_coeff_mpa=fatigue_strength_coeff_mpa,
            fatigue_strength_exponent=fatigue_strength_exponent,
            target_life_cycles=target_life_cycles,
            load_frequency_hz=load_frequency_hz,
        )

        optimistic_case = _evaluate_single_case(
            max_stress_mpa=max_stress_mpa * lower_factor,
            min_stress_mpa=min_stress_mpa * lower_factor,
            ultimate_strength_mpa=ultimate_strength_mpa,
            yield_strength_mpa=yield_strength_mpa,
            mean_stress_correction=mean_stress_correction,
            endurance_limit_mpa=endurance_limit_mpa,
            has_endurance_limit=has_endurance_limit,
            fatigue_strength_coeff_mpa=fatigue_strength_coeff_mpa,
            fatigue_strength_exponent=fatigue_strength_exponent,
            target_life_cycles=target_life_cycles,
            load_frequency_hz=load_frequency_hz,
        )

    assessment_life_factor = (
        conservative_case["life_safety_factor"] if uncertainty_active else nominal["life_safety_factor"]
    )
    assessment_strength_factor = (
        conservative_case["yield_safety_factor"]
        if uncertainty_active
        else nominal["yield_safety_factor"]
    )

    life_ok = assessment_life_factor >= required_fatigue_factor or math.isinf(
        assessment_life_factor
    )
    yield_ok = assessment_strength_factor >= required_yield_factor

    if life_ok and yield_ok:
        status = "acceptable"
    elif assessment_life_factor < 1.0 or assessment_strength_factor < 1.0:
        status = "unacceptable"
    else:
        status = "marginal"

    recommendations: List[str] = []
    if not life_ok:
        recommendations.append(
            "Reduce alternating stress, lower mean stress, or improve material/process controls to meet fatigue life."
        )
    if not yield_ok:
        recommendations.append(
            "Reduce peak stress or increase section size to improve static strength margin."
        )

    if family == "polymer":
        if temperature_c > 40.0:
            recommendations.append(
                "Polymer mode: elevated temperature derating is active. Validate with temperature-specific fatigue data."
            )
        if load_frequency_hz > 5.0:
            recommendations.append(
                "Polymer mode: higher cycle frequency can reduce life via self-heating. Check test data at similar frequency."
            )
        if (
            moisture_derating_factor < 0.98
            or chemical_derating_factor < 0.98
            or uv_derating_factor < 0.98
        ):
            recommendations.append(
                "Polymer mode: environmental derating is active. Confirm factors against datasheet or in-house testing."
            )
    else:
        if mean_stress_correction.strip().lower() == "none":
            recommendations.append(
                "Mean stress correction is disabled; consider Goodman or Gerber when tensile mean stress exists."
            )

    if uncertainty_active:
        recommendations.append(
            "Stress uncertainty band is active; status uses the conservative (high-stress) case."
        )

    if not recommendations:
        recommendations.append(
            "Margins meet targets. Validate assumptions with material-specific fatigue test data."
        )

    output = {
        # Nominal results (backward compatible keys)
        "estimated_life_cycles": nominal["estimated_life_cycles"],
        "estimated_life_hours": nominal["estimated_life_hours"],
        "life_safety_factor": nominal["life_safety_factor"],
        "fatigue_safety_factor": nominal["fatigue_safety_factor"],
        "yield_safety_factor": nominal["yield_safety_factor"],
        "strength_safety_factor": nominal["strength_safety_factor"],
        "equivalent_stress_mpa": nominal["equivalent_stress_mpa"],
        "mean_stress_mpa": nominal["mean_stress_mpa"],
        "alternating_stress_mpa": nominal["alternating_stress_mpa"],
        "stress_ratio": nominal["stress_ratio"],
        "endurance_limit_mpa": nominal["endurance_limit_mpa"],
        "fatigue_strength_coeff_mpa": nominal["fatigue_strength_coeff_mpa"],
        "reference_stress_mpa": nominal["reference_stress_mpa"],
        "reference_stress_basis": nominal["reference_stress_basis"],
        # Material + derating metadata
        "material_family": family,
        "material_preset": preset,
        "material_preset_name": resolved["material_preset_name"],
        "polymer_derating_factor": property_derating_factor,
        "temperature_factor": float(polymer_factors["temperature_factor"]),
        "frequency_factor": float(polymer_factors["frequency_factor"]),
        "moisture_factor": float(polymer_factors["moisture_factor"]),
        "chemical_factor": float(polymer_factors["chemical_factor"]),
        "uv_factor": float(polymer_factors["uv_factor"]),
        "temperature_c": temperature_c,
        "load_frequency_hz": load_frequency_hz,
        # Uncertainty outputs
        "uncertainty_active": uncertainty_active,
        "stress_uncertainty_pct": stress_uncertainty_pct,
        "conservative_life_cycles": conservative_case["estimated_life_cycles"],
        "conservative_life_hours": conservative_case["estimated_life_hours"],
        "conservative_life_safety_factor": conservative_case["life_safety_factor"],
        "conservative_yield_safety_factor": conservative_case["yield_safety_factor"],
        "optimistic_life_cycles": optimistic_case["estimated_life_cycles"],
        "optimistic_life_hours": optimistic_case["estimated_life_hours"],
        "optimistic_life_safety_factor": optimistic_case["life_safety_factor"],
        # Status
        "status": status,
        "recommendations": recommendations,
        # Visualization data
        "sn_curve": nominal["sn_curve"],
        "mean_stress_curve": nominal["mean_stress_curve"],
        # Substituted equations
        "subst_equivalent_stress_mpa": nominal["subst_equivalent_stress_mpa"],
        "subst_estimated_life_cycles": nominal["subst_estimated_life_cycles"],
        "subst_fatigue_safety_factor": nominal["subst_fatigue_safety_factor"],
        "subst_yield_safety_factor": nominal["subst_yield_safety_factor"],
        "subst_life_safety_factor": nominal["subst_life_safety_factor"],
    }

    return output
