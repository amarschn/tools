"""
Polymer fatigue criteria comparison utilities.

This module powers an exploratory tool for polymer fatigue life comparison.
It is intentionally comparison-first: it evaluates a reference stress-life
relation alongside dissipation-based, cyclic-creep-based, and hybrid criteria.
The calculations are designed for educational exploration and literature-backed
trend comparison, not final design sign-off.

Each material preset contains nested dictionaries — ``environment_sensitivity``,
``ratio_sensitivity``, ``compressive_mean_stress``, and
``hybrid_weight_adjustment`` — whose coefficients are *heuristic*: they were
tuned to reproduce published trends for short-fiber PA66 composites, not fit
to a single data set via regression.  See ``heuristic_provenance`` in each
preset for details.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


POLYMER_FATIGUE_PRESETS: Dict[str, Dict[str, Any]] = {
    "pa66_gf50": {
        "display_name": "PA66-GF50 (literature-inspired preset)",
        "material_family": "short-fiber thermoplastic",
        "matrix": "PA66",
        "reinforcement": "Glass fiber, 50 wt%",
        "conditioning_state": "dry_as_molded",
        "orientation_options": ["0_deg", "45_deg", "90_deg"],
        "supported_load_ratio_min": -1.0,
        "supported_load_ratio_max": 0.7,
        "supported_temperature_min_c": 23.0,
        "supported_temperature_max_c": 80.0,
        "supported_frequency_min_hz": 1.0,
        "supported_frequency_max_hz": 10.0,
        "frequency_evidence": [
            {
                "coverage_type": "discrete_points",
                "frequency_text": "2 and 10 Hz",
                "frequency_min_hz": 2.0,
                "frequency_max_hz": 10.0,
                "material_match": "adjacent",
                "test_method": "alternating bending",
                "source_title": "Thermal and mechanical fatigue of a PA66/glass fibers composite material",
                "source_url": "https://doi.org/10.1016/j.ijfatigue.2006.02.031",
                "summary": (
                    "At 23 C and R = -1, 2 Hz remained mechanically dominated while 10 Hz "
                    "produced strong self-heating and thermal-fatigue coupling."
                ),
            },
            {
                "coverage_type": "continuous_range",
                "frequency_text": "2-60 Hz",
                "frequency_min_hz": 2.0,
                "frequency_max_hz": 60.0,
                "material_match": "adjacent",
                "test_method": "tension-tension and flexural fatigue",
                "source_title": "Fatigue behavior of polyamide 66/glass fiber under various kinds of applied load",
                "source_url": "https://doi.org/10.1002/pc.22185",
                "summary": (
                    "PA66/GF was tested under tension-tension fatigue at R = 0.1 and 0.3 and "
                    "alternate flexural fatigue at R = -1 across 2-60 Hz."
                ),
            },
        ],
        "supported_moisture_states": ["dry_as_molded", "conditioned", "wet"],
        "ultimate_strength_mpa": 190.0,
        "yield_strength_mpa": 145.0,
        "reference_strength_coeff_mpa": 330.0,
        "reference_exponent": -0.118,
        "mean_stress_sensitivity": 0.34,
        "energy_surrogate_coeff": 3.6e-4,
        "energy_surrogate_exponent": 2.08,
        "energy_life_constant": 1.55e6,
        "energy_life_exponent": 1.48,
        "creep_surrogate_coeff": 1.1e-13,
        "creep_surrogate_exponent": 4.18,
        "creep_life_constant": 1.05,
        "creep_life_exponent": 0.90,
        "hybrid_creep_weight": 0.62,
        "orientation_damage_factor": {"0_deg": 1.00, "45_deg": 1.17, "90_deg": 1.42},
        "moisture_damage_factor": {
            "dry_as_molded": 1.00,
            "conditioned": 1.10,
            "wet": 1.24,
        },
        "calibration_energy_min_mj_per_m3": 0.25,
        "calibration_energy_max_mj_per_m3": 3.80,
        "calibration_creep_rate_min_per_cycle": 1.0e-8,
        "calibration_creep_rate_max_per_cycle": 8.0e-6,
        "representative_energy_mj_per_m3": 0.95,
        "representative_creep_rate_per_cycle": 9.0e-7,
        "source_title": (
            "Mixed strain-rate / energy and cyclic-creep criteria for short-fiber thermoplastics"
        ),
        "source_url": "https://doi.org/10.1016/j.ijfatigue.2019.06.003",
        "notes": (
            "Exploratory preset informed by PA66-GF literature trends. Use measured loop "
            "data for decision-grade comparison."
        ),
        "environment_sensitivity": {
            "temperature_reference_c": 23.0,
            "temperature_coeff_above": 0.012,
            "temperature_coeff_below": 0.004,
            "temperature_factor_floor": 0.88,
            "frequency_reference_hz": 2.0,
            "frequency_coeff_above": 0.04,
            "frequency_coeff_below": 0.03,
            "frequency_factor_floor": 0.90,
        },
        "ratio_sensitivity": {
            "energy_positive_R_coeff": 0.24,
            "energy_negative_R_coeff": 0.15,
            "creep_positive_R_coeff": 0.30,
        },
        "compressive_mean_stress": {
            "compressive_sensitivity": 0.10,
            "compressive_factor_floor": 0.88,
        },
        "hybrid_weight_adjustment": {
            "positive_R_adjustment": 0.18,
            "negative_R_adjustment": 0.15,
            "weight_min": 0.20,
            "weight_max": 0.80,
        },
        "basquin_convention": "reversals",
        "heuristic_provenance": (
            "The environment_sensitivity, ratio_sensitivity, compressive_mean_stress, "
            "and hybrid_weight_adjustment coefficients are heuristic values calibrated "
            "to reproduce published trends for short-fiber PA66 composites. They are not "
            "direct curve-fit parameters from a single data set."
        ),
    },
    "pa66_gf30": {
        "display_name": "PA66-GF30 (literature-inspired preset)",
        "material_family": "short-fiber thermoplastic",
        "matrix": "PA66",
        "reinforcement": "Glass fiber, 30 wt%",
        "conditioning_state": "conditioned",
        "orientation_options": ["0_deg", "45_deg", "90_deg"],
        "supported_load_ratio_min": -0.5,
        "supported_load_ratio_max": 0.5,
        "supported_temperature_min_c": 23.0,
        "supported_temperature_max_c": 60.0,
        "supported_frequency_min_hz": 1.0,
        "supported_frequency_max_hz": 8.0,
        "frequency_evidence": [
            {
                "coverage_type": "discrete_points",
                "frequency_text": "20 Hz",
                "frequency_min_hz": 20.0,
                "frequency_max_hz": 20.0,
                "material_match": "adjacent",
                "test_method": "stress-controlled tension-tension fatigue",
                "source_title": (
                    "Fatigue failure mechanisms of short glass-fiber reinforced nylon 66 "
                    "based on nonlinear dynamic viscoelastic measurement"
                ),
                "source_url": "https://doi.org/10.1016/S0032-3861(00)00897-1",
                "summary": (
                    "Short glass-fiber reinforced nylon 66 with 33 wt% GF was characterized "
                    "at 20 Hz across multiple temperatures."
                ),
            },
            {
                "coverage_type": "continuous_range",
                "frequency_text": "2-60 Hz",
                "frequency_min_hz": 2.0,
                "frequency_max_hz": 60.0,
                "material_match": "adjacent",
                "test_method": "tension-tension and flexural fatigue",
                "source_title": "Fatigue behavior of polyamide 66/glass fiber under various kinds of applied load",
                "source_url": "https://doi.org/10.1002/pc.22185",
                "summary": (
                    "PA66/GF was tested under tension-tension fatigue at R = 0.1 and 0.3 and "
                    "alternate flexural fatigue at R = -1 across 2-60 Hz."
                ),
            },
            {
                "coverage_type": "discrete_points",
                "frequency_text": "3 Hz and 20 kHz",
                "frequency_min_hz": 3.0,
                "frequency_max_hz": 20000.0,
                "material_match": "exact",
                "test_method": "conventional plus ultrasonic VHCF",
                "source_title": "Investigation on very high cycle fatigue of PA66-GF30 GFRP based on fiber orientation",
                "source_url": "https://doi.org/10.1016/j.compscitech.2019.05.021",
                "summary": (
                    "Exact PA66-GF30 data were reported at 3 Hz and 20 kHz under R = -1, "
                    "using conventional and ultrasonic fatigue methods."
                ),
            },
        ],
        "supported_moisture_states": ["dry_as_molded", "conditioned"],
        "ultimate_strength_mpa": 150.0,
        "yield_strength_mpa": 118.0,
        "reference_strength_coeff_mpa": 255.0,
        "reference_exponent": -0.124,
        "mean_stress_sensitivity": 0.31,
        "energy_surrogate_coeff": 4.2e-4,
        "energy_surrogate_exponent": 2.02,
        "energy_life_constant": 1.05e6,
        "energy_life_exponent": 1.42,
        "creep_surrogate_coeff": 1.7e-13,
        "creep_surrogate_exponent": 4.05,
        "creep_life_constant": 0.82,
        "creep_life_exponent": 0.88,
        "hybrid_creep_weight": 0.58,
        "orientation_damage_factor": {"0_deg": 1.00, "45_deg": 1.22, "90_deg": 1.55},
        "moisture_damage_factor": {
            "dry_as_molded": 1.00,
            "conditioned": 1.14,
            "wet": 1.28,
        },
        "calibration_energy_min_mj_per_m3": 0.20,
        "calibration_energy_max_mj_per_m3": 3.00,
        "calibration_creep_rate_min_per_cycle": 2.0e-8,
        "calibration_creep_rate_max_per_cycle": 1.2e-5,
        "representative_energy_mj_per_m3": 1.10,
        "representative_creep_rate_per_cycle": 1.4e-6,
        "source_title": (
            "Short-fiber thermoplastic fatigue criteria validated across load-ratio and environment"
        ),
        "source_url": "https://doi.org/10.1016/j.ijfatigue.2020.105574",
        "notes": (
            "Lower-fiber-fraction preset with stronger conditioning sensitivity. "
            "Best used inside the stated temperature and R-ratio ranges."
        ),
        "environment_sensitivity": {
            "temperature_reference_c": 23.0,
            "temperature_coeff_above": 0.012,
            "temperature_coeff_below": 0.004,
            "temperature_factor_floor": 0.88,
            "frequency_reference_hz": 2.0,
            "frequency_coeff_above": 0.04,
            "frequency_coeff_below": 0.03,
            "frequency_factor_floor": 0.90,
        },
        "ratio_sensitivity": {
            "energy_positive_R_coeff": 0.24,
            "energy_negative_R_coeff": 0.15,
            "creep_positive_R_coeff": 0.30,
        },
        "compressive_mean_stress": {
            "compressive_sensitivity": 0.10,
            "compressive_factor_floor": 0.88,
        },
        "hybrid_weight_adjustment": {
            "positive_R_adjustment": 0.18,
            "negative_R_adjustment": 0.15,
            "weight_min": 0.20,
            "weight_max": 0.80,
        },
        "basquin_convention": "reversals",
        "heuristic_provenance": (
            "The environment_sensitivity, ratio_sensitivity, compressive_mean_stress, "
            "and hybrid_weight_adjustment coefficients are heuristic values calibrated "
            "to reproduce published trends for short-fiber PA66 composites. They are not "
            "direct curve-fit parameters from a single data set."
        ),
    },
    "custom_calibrated": {
        "display_name": "Custom calibrated polymer",
        "material_family": "custom",
        "matrix": "User supplied",
        "reinforcement": "User supplied",
        "conditioning_state": "user_defined",
        "orientation_options": ["0_deg", "45_deg", "90_deg"],
        "supported_load_ratio_min": -1.0,
        "supported_load_ratio_max": 0.9,
        "supported_temperature_min_c": -20.0,
        "supported_temperature_max_c": 120.0,
        "supported_frequency_min_hz": 0.1,
        "supported_frequency_max_hz": 20.0,
        "frequency_evidence": [],
        "supported_moisture_states": ["dry_as_molded", "conditioned", "wet"],
        "ultimate_strength_mpa": 140.0,
        "yield_strength_mpa": 110.0,
        "reference_strength_coeff_mpa": 240.0,
        "reference_exponent": -0.120,
        "mean_stress_sensitivity": 0.32,
        "energy_surrogate_coeff": 4.0e-4,
        "energy_surrogate_exponent": 2.00,
        "energy_life_constant": 1.20e6,
        "energy_life_exponent": 1.45,
        "creep_surrogate_coeff": 1.5e-13,
        "creep_surrogate_exponent": 4.10,
        "creep_life_constant": 0.95,
        "creep_life_exponent": 0.90,
        "hybrid_creep_weight": 0.60,
        "orientation_damage_factor": {"0_deg": 1.00, "45_deg": 1.15, "90_deg": 1.35},
        "moisture_damage_factor": {
            "dry_as_molded": 1.00,
            "conditioned": 1.08,
            "wet": 1.18,
        },
        "calibration_energy_min_mj_per_m3": 0.15,
        "calibration_energy_max_mj_per_m3": 4.00,
        "calibration_creep_rate_min_per_cycle": 1.0e-9,
        "calibration_creep_rate_max_per_cycle": 2.0e-5,
        "representative_energy_mj_per_m3": 0.90,
        "representative_creep_rate_per_cycle": 1.0e-6,
        "source_title": "User supplied calibration",
        "source_url": "",
        "notes": "Enter coefficients from your own material campaign or literature fit.",
        "environment_sensitivity": {
            "temperature_reference_c": 23.0,
            "temperature_coeff_above": 0.012,
            "temperature_coeff_below": 0.004,
            "temperature_factor_floor": 0.88,
            "frequency_reference_hz": 2.0,
            "frequency_coeff_above": 0.04,
            "frequency_coeff_below": 0.03,
            "frequency_factor_floor": 0.90,
        },
        "ratio_sensitivity": {
            "energy_positive_R_coeff": 0.24,
            "energy_negative_R_coeff": 0.15,
            "creep_positive_R_coeff": 0.30,
        },
        "compressive_mean_stress": {
            "compressive_sensitivity": 0.10,
            "compressive_factor_floor": 0.88,
        },
        "hybrid_weight_adjustment": {
            "positive_R_adjustment": 0.18,
            "negative_R_adjustment": 0.15,
            "weight_min": 0.20,
            "weight_max": 0.80,
        },
        "basquin_convention": "reversals",
        "heuristic_provenance": (
            "The environment_sensitivity, ratio_sensitivity, compressive_mean_stress, "
            "and hybrid_weight_adjustment coefficients are heuristic values calibrated "
            "to reproduce published trends for short-fiber PA66 composites. They are not "
            "direct curve-fit parameters from a single data set."
        ),
    },
}


def get_polymer_fatigue_presets() -> Dict[str, Dict[str, Any]]:
    """Return the available polymer fatigue presets."""
    return POLYMER_FATIGUE_PRESETS


def _validate_positive(name: str, value: float) -> None:
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0. Got {value}.")


def _clamp(value: float, value_min: float, value_max: float) -> float:
    return max(value_min, min(value_max, value))


def _hours_from_cycles(cycles: float, load_frequency_hz: float) -> float:
    if not math.isfinite(cycles):
        return float("inf")
    return cycles / (load_frequency_hz * 3600.0)


def _format_frequency_hz(frequency_hz: float) -> str:
    if frequency_hz >= 1000.0:
        if abs(frequency_hz % 1000.0) < 1.0e-9:
            return f"{frequency_hz / 1000.0:.0f} kHz"
        return f"{frequency_hz / 1000.0:.1f} kHz"
    if frequency_hz >= 10.0:
        return f"{frequency_hz:.0f} Hz"
    if frequency_hz >= 1.0:
        return f"{frequency_hz:.1f} Hz"
    return f"{frequency_hz:.3g} Hz"


def _life_to_regime(life_cycles: float) -> str:
    if not math.isfinite(life_cycles):
        return "HCF"
    if life_cycles < 1.0e4:
        return "LCF"
    if life_cycles < 1.0e5:
        return "transition"
    return "HCF"


def _resolve_preset(
    material_preset: str,
    ultimate_strength_mpa: float,
    yield_strength_mpa: float,
    reference_strength_coeff_mpa: float,
    reference_exponent: float,
    energy_surrogate_coeff: float,
    energy_surrogate_exponent: float,
    energy_life_constant: float,
    energy_life_exponent: float,
    creep_surrogate_coeff: float,
    creep_surrogate_exponent: float,
    creep_life_constant: float,
    creep_life_exponent: float,
    hybrid_creep_weight: float,
    mean_stress_sensitivity: float,
) -> Dict[str, Any]:
    preset_key = material_preset.strip().lower()
    if preset_key not in POLYMER_FATIGUE_PRESETS:
        valid = ", ".join(sorted(POLYMER_FATIGUE_PRESETS))
        raise ValueError(
            f"Unknown material_preset '{material_preset}'. Valid presets: {valid}."
        )

    preset = dict(POLYMER_FATIGUE_PRESETS[preset_key])
    if preset_key == "custom_calibrated":
        preset.update(
            {
                "ultimate_strength_mpa": ultimate_strength_mpa,
                "yield_strength_mpa": yield_strength_mpa,
                "reference_strength_coeff_mpa": reference_strength_coeff_mpa,
                "reference_exponent": reference_exponent,
                "energy_surrogate_coeff": energy_surrogate_coeff,
                "energy_surrogate_exponent": energy_surrogate_exponent,
                "energy_life_constant": energy_life_constant,
                "energy_life_exponent": energy_life_exponent,
                "creep_surrogate_coeff": creep_surrogate_coeff,
                "creep_surrogate_exponent": creep_surrogate_exponent,
                "creep_life_constant": creep_life_constant,
                "creep_life_exponent": creep_life_exponent,
                "hybrid_creep_weight": hybrid_creep_weight,
                "mean_stress_sensitivity": mean_stress_sensitivity,
            }
        )
    return preset


def _compute_stress_state(stress_amplitude_mpa: float, load_ratio: float) -> Dict[str, float]:
    if load_ratio >= 1.0:
        raise ValueError("load_ratio must be < 1.0.")
    _validate_positive("stress_amplitude_mpa", stress_amplitude_mpa)

    sigma_max = 2.0 * stress_amplitude_mpa / (1.0 - load_ratio)
    sigma_min = load_ratio * sigma_max
    sigma_mean = 0.5 * (sigma_max + sigma_min)
    return {
        "sigma_max_mpa": sigma_max,
        "sigma_min_mpa": sigma_min,
        "sigma_mean_mpa": sigma_mean,
    }


def _environment_damage_factor(
    temperature_c: float,
    load_frequency_hz: float,
    moisture_state: str,
    orientation_bucket: str,
    preset: Dict[str, Any],
) -> Dict[str, float]:
    """Multiplicative environmental damage factor.

    Each sub-factor is treated as independent and multiplicative.  The
    temperature and frequency models are piecewise-linear around their
    reference points with separate slopes above and below, each clamped
    by a floor value.

    Limitations:
    - The linear frequency model is reasonable for ~1-10 Hz but diverges
      above ~15 Hz where self-heating becomes nonlinear.
    - The multiplicative independence assumption ignores
      temperature x frequency coupling (which matters at high frequency
      where self-heating is significant).
    - Reference conditions (temperature_reference_c, frequency_reference_hz)
      define the point where the corresponding sub-factor equals 1.0.
    """
    orientation_map = dict(preset["orientation_damage_factor"])
    moisture_map = dict(preset["moisture_damage_factor"])
    if orientation_bucket not in orientation_map:
        raise ValueError(
            f"Unknown orientation_bucket '{orientation_bucket}'. "
            f"Valid: {sorted(orientation_map)}"
        )
    if moisture_state not in moisture_map:
        raise ValueError(
            f"Unknown moisture_state '{moisture_state}'. "
            f"Valid: {sorted(moisture_map)}"
        )
    orientation_factor = orientation_map[orientation_bucket]
    moisture_factor = moisture_map[moisture_state]

    env = preset["environment_sensitivity"]
    t_ref = env["temperature_reference_c"]
    t_coeff_above = env["temperature_coeff_above"]
    t_coeff_below = env["temperature_coeff_below"]
    t_floor = env["temperature_factor_floor"]
    f_ref = env["frequency_reference_hz"]
    f_coeff_above = env["frequency_coeff_above"]
    f_coeff_below = env["frequency_coeff_below"]
    f_floor = env["frequency_factor_floor"]

    if temperature_c >= t_ref:
        temperature_factor = 1.0 + t_coeff_above * (temperature_c - t_ref)
    else:
        temperature_factor = max(t_floor, 1.0 - t_coeff_below * (t_ref - temperature_c))

    if load_frequency_hz >= f_ref:
        frequency_factor = 1.0 + f_coeff_above * (load_frequency_hz - f_ref)
    else:
        frequency_factor = max(f_floor, 1.0 - f_coeff_below * (f_ref - load_frequency_hz))

    combined = temperature_factor * frequency_factor * moisture_factor * orientation_factor
    return {
        "temperature_factor": temperature_factor,
        "frequency_factor": frequency_factor,
        "moisture_factor": moisture_factor,
        "orientation_factor": orientation_factor,
        "combined_factor": combined,
    }


def _reference_equivalent_stress(
    stress_amplitude_mpa: float,
    sigma_mean_mpa: float,
    ultimate_strength_mpa: float,
    mean_stress_sensitivity: float,
    preset: Dict[str, Any],
) -> float:
    """Equivalent fully-reversed stress amplitude accounting for mean stress.

    For tensile mean stress (sigma_mean >= 0):
        sigma_eq = sigma_a * (1 + k_m * sigma_mean / S_ut)
    where k_m is ``mean_stress_sensitivity``.

    For compressive mean stress (sigma_mean < 0):
        sigma_eq = sigma_a * max(floor, 1 - k_c * |sigma_mean| / S_ut)
    where k_c is ``compressive_sensitivity`` and ``floor`` is
    ``compressive_factor_floor``, both from ``preset["compressive_mean_stress"]``.
    The floor prevents the correction from over-crediting compressive mean
    stress at large |sigma_mean|.
    """
    comp = preset["compressive_mean_stress"]
    comp_sensitivity = comp["compressive_sensitivity"]
    comp_floor = comp["compressive_factor_floor"]

    tensile_factor = 1.0 + mean_stress_sensitivity * max(sigma_mean_mpa, 0.0) / ultimate_strength_mpa
    compressive_factor = 1.0 - comp_sensitivity * max(-sigma_mean_mpa, 0.0) / ultimate_strength_mpa
    compressive_factor = max(comp_floor, compressive_factor)
    if sigma_mean_mpa >= 0.0:
        return stress_amplitude_mpa * tensile_factor
    return stress_amplitude_mpa * compressive_factor


def _basquin_life(
    equivalent_stress_mpa: float,
    strength_coeff_mpa: float,
    exponent: float,
    basquin_convention: str = "reversals",
) -> float:
    """Basquin power-law life prediction.

    When ``basquin_convention`` is ``"reversals"`` (default), the relation is
    calibrated against reversal count 2Nf, so a factor of 0.5 converts to
    cycles: Nf = 0.5 * (sigma_eq / sigma_f')^(1/b).

    When ``basquin_convention`` is ``"cycles"``, the coefficients are already
    calibrated against Nf directly, so the 0.5 prefactor is omitted.
    """
    if basquin_convention not in {"reversals", "cycles"}:
        raise ValueError(
            f"basquin_convention must be 'reversals' or 'cycles', got '{basquin_convention}'."
        )
    if equivalent_stress_mpa <= 0.0:
        return float("inf")
    prefactor = 0.5 if basquin_convention == "reversals" else 1.0
    return prefactor * (equivalent_stress_mpa / strength_coeff_mpa) ** (1.0 / exponent)


def _surrogate_loop_metrics(
    stress_amplitude_mpa: float,
    sigma_max_mpa: float,
    load_ratio: float,
    preset: Dict[str, Any],
    environment: Dict[str, float],
) -> Dict[str, float]:
    """Estimate stabilized loop energy and cyclic creep rate from load case.

    The ratio_factor accounts for load-ratio effects on hysteresis loop area
    and creep accumulation.  It is a heuristic product of two terms:

    - Energy ratio factor: (1 + k_pos * max(R,0)) * (1 + k_neg * max(-R,0))
    - Creep ratio factor: (1 + k_creep * max(R,0))

    where k_pos, k_neg, k_creep come from ``preset["ratio_sensitivity"]``.
    These are not direct literature fits; they are tuned to reproduce the
    qualitative trend that positive R increases both dissipation and creep
    tendency while negative R broadens the hysteresis loop.
    """
    rs = preset["ratio_sensitivity"]
    positive_ratio_factor = 1.0 + rs["energy_positive_R_coeff"] * max(load_ratio, 0.0)
    negative_ratio_factor = 1.0 + rs["energy_negative_R_coeff"] * max(-load_ratio, 0.0)
    ratio_factor = positive_ratio_factor * negative_ratio_factor

    loop_energy = (
        float(preset["energy_surrogate_coeff"])
        * (stress_amplitude_mpa ** float(preset["energy_surrogate_exponent"]))
        * environment["combined_factor"]
        * ratio_factor
    )

    cyclic_creep_rate = (
        float(preset["creep_surrogate_coeff"])
        * (sigma_max_mpa ** float(preset["creep_surrogate_exponent"]))
        * environment["combined_factor"]
        * (1.0 + rs["creep_positive_R_coeff"] * max(load_ratio, 0.0))
    )
    return {
        "loop_energy_mj_per_m3": loop_energy,
        "cyclic_creep_rate_per_cycle": cyclic_creep_rate,
    }


def _energy_life(loop_energy_mj_per_m3: float, preset: Dict[str, Any]) -> float:
    _validate_positive("loop_energy_mj_per_m3", loop_energy_mj_per_m3)
    return float(preset["energy_life_constant"]) * (
        loop_energy_mj_per_m3 ** (-float(preset["energy_life_exponent"]))
    )


def _creep_life(cyclic_creep_rate_per_cycle: float, preset: Dict[str, Any]) -> float:
    _validate_positive("cyclic_creep_rate_per_cycle", cyclic_creep_rate_per_cycle)
    return float(preset["creep_life_constant"]) * (
        cyclic_creep_rate_per_cycle ** (-float(preset["creep_life_exponent"]))
    )


def _hybrid_life(
    energy_life_cycles: float,
    creep_life_cycles: float,
    load_ratio: float,
    preset: Dict[str, Any],
) -> Dict[str, float]:
    """Weighted harmonic mean of energy and creep lives.

    The creep weight is adjusted from its base value by load ratio:
        w_c = base + adj_pos * max(R,0) - adj_neg * max(-R,0)
    then clamped to [weight_min, weight_max].

    Physical motivation: positive R increases mean stress and therefore
    creep tendency, so the creep weight increases; negative R reduces
    mean stress and favors hysteresis-dominated failure, so creep weight
    decreases.  The harmonic mean ensures the hybrid life always lies
    between the component lives.
    """
    hw = preset["hybrid_weight_adjustment"]
    base_creep_weight = float(preset["hybrid_creep_weight"])
    creep_weight = (
        base_creep_weight
        + hw["positive_R_adjustment"] * max(load_ratio, 0.0)
        - hw["negative_R_adjustment"] * max(-load_ratio, 0.0)
    )
    creep_weight = _clamp(creep_weight, hw["weight_min"], hw["weight_max"])
    energy_weight = 1.0 - creep_weight
    hybrid_cycles = 1.0 / (
        creep_weight / creep_life_cycles + energy_weight / energy_life_cycles
    )
    return {
        "hybrid_life_cycles": hybrid_cycles,
        "creep_weight": creep_weight,
        "energy_weight": energy_weight,
    }


def _make_model_row(
    model_key: str,
    display_name: str,
    estimated_life_cycles: float | None,
    target_life_cycles: float,
    load_frequency_hz: float,
    source_title: str,
    source_url: str,
    used_observables: Dict[str, float | str],
    applicability_state: str,
    warning_messages: List[str],
    subst_estimated_life_cycles: str,
) -> Dict[str, Any]:
    life_ratio = None
    life_hours = None
    if estimated_life_cycles is not None:
        life_ratio = estimated_life_cycles / target_life_cycles
        life_hours = _hours_from_cycles(estimated_life_cycles, load_frequency_hz)

    return {
        "model": model_key,
        "display_name": display_name,
        "estimated_life_cycles": estimated_life_cycles,
        "estimated_life_hours": life_hours,
        "life_ratio_to_target": life_ratio,
        "required_observables": list(used_observables.keys()),
        "used_observables": used_observables,
        "applicability_state": applicability_state,
        "warning_messages": warning_messages,
        "source_title": source_title,
        "source_url": source_url,
        "subst_estimated_life_cycles": subst_estimated_life_cycles,
    }


def _append_range_warnings(
    warnings: List[str],
    preset: Dict[str, Any],
    load_ratio: float,
    temperature_c: float,
    load_frequency_hz: float,
    moisture_state: str,
    frequency_guidance: Dict[str, Any] | None = None,
) -> None:
    if load_ratio < float(preset["supported_load_ratio_min"]) or load_ratio > float(
        preset["supported_load_ratio_max"]
    ):
        warnings.append("Load ratio is outside the preset calibration range.")
    if temperature_c < float(preset["supported_temperature_min_c"]) or temperature_c > float(
        preset["supported_temperature_max_c"]
    ):
        warnings.append("Temperature is outside the preset calibration range.")
    if load_frequency_hz < float(preset["supported_frequency_min_hz"]) or load_frequency_hz > float(
        preset["supported_frequency_max_hz"]
    ):
        if frequency_guidance and frequency_guidance["warning_messages"]:
            warnings.extend(frequency_guidance["warning_messages"])
        else:
            warnings.append("Frequency is outside the preset calibration range.")
    if moisture_state not in set(preset["supported_moisture_states"]):
        warnings.append("Moisture state is outside the preset calibration range.")


def _build_frequency_guidance(preset: Dict[str, Any], load_frequency_hz: float) -> Dict[str, Any]:
    fit_min = float(preset["supported_frequency_min_hz"])
    fit_max = float(preset["supported_frequency_max_hz"])
    evidence_records_raw = list(preset.get("frequency_evidence", []))

    evidence_records: List[Dict[str, Any]] = []
    highest_any_frequency_hz = None
    highest_continuous_frequency_hz = None
    highest_any_record = None
    highest_continuous_record = None

    for record in evidence_records_raw:
        min_hz = float(record["frequency_min_hz"])
        max_hz = float(record["frequency_max_hz"])
        normalized_record = {
            "coverage_type": str(record.get("coverage_type", "continuous_range")),
            "frequency_text": str(record["frequency_text"]),
            "frequency_min_hz": min_hz,
            "frequency_max_hz": max_hz,
            "material_match": str(record.get("material_match", "adjacent")),
            "test_method": str(record.get("test_method", "fatigue test")),
            "source_title": str(record.get("source_title", "")),
            "source_url": str(record.get("source_url", "")),
            "summary": str(record.get("summary", "")),
        }
        evidence_records.append(normalized_record)

        if highest_any_frequency_hz is None or max_hz > highest_any_frequency_hz:
            highest_any_frequency_hz = max_hz
            highest_any_record = normalized_record

        if normalized_record["coverage_type"] == "continuous_range" and (
            highest_continuous_frequency_hz is None or max_hz > highest_continuous_frequency_hz
        ):
            highest_continuous_frequency_hz = max_hz
            highest_continuous_record = normalized_record

    warning_messages: List[str] = []
    fit_window_text = f"{_format_frequency_hz(fit_min)} to {_format_frequency_hz(fit_max)}"
    within_fit_range = fit_min <= load_frequency_hz <= fit_max

    if not within_fit_range:
        warning = (
            f"Frequency is outside the current criterion-fit window ({fit_window_text})."
        )
        if highest_continuous_frequency_hz is not None and highest_continuous_record is not None:
            warning += (
                f" Published conventional data reach "
                f"{_format_frequency_hz(highest_continuous_frequency_hz)} "
                f"({highest_continuous_record['frequency_text']}, "
                f"{highest_continuous_record['material_match']} match)."
            )
        if (
            highest_any_frequency_hz is not None
            and highest_any_record is not None
            and (
                highest_continuous_frequency_hz is None
                or highest_any_frequency_hz > highest_continuous_frequency_hz
            )
        ):
            warning += (
                f" Separate high-frequency evidence reaches "
                f"{_format_frequency_hz(highest_any_frequency_hz)} "
                f"via {highest_any_record['test_method']} "
                f"({highest_any_record['material_match']} match)."
            )
        warning += (
            " The current surrogate coefficients are not recalibrated to those studies, "
            "so treat this as a frequency extrapolation and prefer measured loop data."
        )
        warning_messages.append(warning)

    return {
        "criterion_fit_min_hz": fit_min,
        "criterion_fit_max_hz": fit_max,
        "criterion_fit_text": fit_window_text,
        "current_frequency_hz": load_frequency_hz,
        "within_fit_range": within_fit_range,
        "highest_continuous_frequency_hz": highest_continuous_frequency_hz,
        "highest_any_frequency_hz": highest_any_frequency_hz,
        "highest_continuous_frequency_text": (
            _format_frequency_hz(highest_continuous_frequency_hz)
            if highest_continuous_frequency_hz is not None
            else None
        ),
        "highest_any_frequency_text": (
            _format_frequency_hz(highest_any_frequency_hz)
            if highest_any_frequency_hz is not None
            else None
        ),
        "evidence_records": evidence_records,
        "warning_messages": warning_messages,
    }


def _calibration_plot_data(
    loop_energy_mj_per_m3: float,
    cyclic_creep_rate_per_cycle: float,
    preset: Dict[str, Any],
) -> Dict[str, Any]:
    energy_min = float(preset["calibration_energy_min_mj_per_m3"])
    energy_max = float(preset["calibration_energy_max_mj_per_m3"])
    creep_min = float(preset["calibration_creep_rate_min_per_cycle"])
    creep_max = float(preset["calibration_creep_rate_max_per_cycle"])
    representative_energy = float(preset["representative_energy_mj_per_m3"])
    representative_creep = float(preset["representative_creep_rate_per_cycle"])

    return {
        "energy_bounds": [energy_min, energy_max, energy_max, energy_min, energy_min],
        "creep_bounds": [creep_min, creep_min, creep_max, creep_max, creep_min],
        "current_energy_mj_per_m3": loop_energy_mj_per_m3,
        "current_creep_rate_per_cycle": cyclic_creep_rate_per_cycle,
        "representative_energy_mj_per_m3": representative_energy,
        "representative_creep_rate_per_cycle": representative_creep,
    }


def _build_stress_waveform_data(
    stress_state: Dict[str, float],
    stress_amplitude_mpa: float,
    load_ratio: float,
) -> Dict[str, Any]:
    """Build sinusoidal stress waveform data for one full cycle.

    Returns x (normalised time 0-1) and y (stress in MPa), plus horizontal
    reference values for sigma_max, sigma_min, and sigma_mean so the frontend
    can draw annotation lines.
    """
    n_points = 101
    sigma_max = stress_state["sigma_max_mpa"]
    sigma_min = stress_state["sigma_min_mpa"]
    sigma_mean = stress_state["sigma_mean_mpa"]
    sigma_a = stress_amplitude_mpa

    time_values = [i / (n_points - 1) for i in range(n_points)]
    stress_values = [sigma_mean + sigma_a * math.sin(2.0 * math.pi * t) for t in time_values]

    return {
        "time_values": time_values,
        "stress_values": stress_values,
        "sigma_max_mpa": sigma_max,
        "sigma_min_mpa": sigma_min,
        "sigma_mean_mpa": sigma_mean,
        "stress_amplitude_mpa": sigma_a,
        "load_ratio": load_ratio,
    }


def _build_sweep_plot_data(
    workflow_mode: str,
    preset: Dict[str, Any],
    load_ratio: float,
    temperature_c: float,
    load_frequency_hz: float,
    moisture_state: str,
    orientation_bucket: str,
    stress_amplitude_mpa: float,
    loop_energy_mj_per_m3: float,
    cyclic_creep_rate_per_cycle: float,
) -> Dict[str, Any]:
    x_values: List[float] = []
    reference_values: List[float] = []
    energy_values: List[float] = []
    creep_values: List[float] = []
    hybrid_values: List[float] = []

    if workflow_mode == "measured_loop":
        factors = [0.6 + 0.04 * i for i in range(21)]
        x_values = factors
        x_label = "Loop severity scale"
        for factor in factors:
            scaled_energy = loop_energy_mj_per_m3 * factor
            scaled_creep = cyclic_creep_rate_per_cycle * factor
            energy_cycles = _energy_life(scaled_energy, preset)
            creep_cycles = _creep_life(scaled_creep, preset) if scaled_creep > 0.0 else None
            hybrid_result = (
                _hybrid_life(energy_cycles, creep_cycles, load_ratio, preset)
                if creep_cycles is not None
                else {"hybrid_life_cycles": None}
            )
            reference_cycles = _basquin_life(
                stress_amplitude_mpa * factor,
                float(preset["reference_strength_coeff_mpa"]),
                float(preset["reference_exponent"]),
                basquin_convention=preset["basquin_convention"],
            )
            reference_values.append(reference_cycles)
            energy_values.append(energy_cycles)
            creep_values.append(creep_cycles)
            hybrid_values.append(hybrid_result["hybrid_life_cycles"])
    else:
        amplitudes = [stress_amplitude_mpa * (0.6 + 0.04 * i) for i in range(21)]
        x_values = amplitudes
        x_label = "Stress amplitude (MPa)"
        for amplitude in amplitudes:
            stress_state = _compute_stress_state(amplitude, load_ratio)
            environment = _environment_damage_factor(
                temperature_c=temperature_c,
                load_frequency_hz=load_frequency_hz,
                moisture_state=moisture_state,
                orientation_bucket=orientation_bucket,
                preset=preset,
            )
            surrogate = _surrogate_loop_metrics(
                stress_amplitude_mpa=amplitude,
                sigma_max_mpa=stress_state["sigma_max_mpa"],
                load_ratio=load_ratio,
                preset=preset,
                environment=environment,
            )
            sigma_eq = _reference_equivalent_stress(
                stress_amplitude_mpa=amplitude,
                sigma_mean_mpa=stress_state["sigma_mean_mpa"],
                ultimate_strength_mpa=float(preset["ultimate_strength_mpa"]),
                mean_stress_sensitivity=float(preset["mean_stress_sensitivity"]),
                preset=preset,
            )
            reference_cycles = _basquin_life(
                sigma_eq,
                float(preset["reference_strength_coeff_mpa"]),
                float(preset["reference_exponent"]),
                basquin_convention=preset["basquin_convention"],
            )
            energy_cycles = _energy_life(surrogate["loop_energy_mj_per_m3"], preset)
            creep_cycles = _creep_life(surrogate["cyclic_creep_rate_per_cycle"], preset)
            hybrid_result = _hybrid_life(energy_cycles, creep_cycles, load_ratio, preset)
            reference_values.append(reference_cycles)
            energy_values.append(energy_cycles)
            creep_values.append(creep_cycles)
            hybrid_values.append(hybrid_result["hybrid_life_cycles"])

    return {
        "x_values": x_values,
        "x_label": x_label,
        "reference_cycles": reference_values,
        "energy_cycles": energy_values,
        "creep_cycles": creep_values,
        "hybrid_cycles": hybrid_values,
    }


def compare_polymer_fatigue_criteria(
    material_preset: str = "pa66_gf50",
    workflow_mode: str = "preset_load_case",
    orientation_bucket: str = "0_deg",
    moisture_state: str = "dry_as_molded",
    load_ratio: float = 0.1,
    stress_amplitude_mpa: float = 42.0,
    temperature_c: float = 23.0,
    load_frequency_hz: float = 2.0,
    target_life_cycles: float = 1.0e6,
    direct_loop_energy_mj_per_m3: float = 0.95,
    direct_cyclic_creep_rate_per_cycle: float = 9.0e-7,
    ultimate_strength_mpa: float = 140.0,
    yield_strength_mpa: float = 110.0,
    reference_strength_coeff_mpa: float = 240.0,
    reference_exponent: float = -0.120,
    energy_surrogate_coeff: float = 4.0e-4,
    energy_surrogate_exponent: float = 2.00,
    energy_life_constant: float = 1.2e6,
    energy_life_exponent: float = 1.45,
    creep_surrogate_coeff: float = 1.5e-13,
    creep_surrogate_exponent: float = 4.10,
    creep_life_constant: float = 0.95,
    creep_life_exponent: float = 0.90,
    hybrid_creep_weight: float = 0.60,
    mean_stress_sensitivity: float = 0.32,
    basquin_convention: str = "",
    enabled_models: str = "reference,energy,cyclic_creep,hybrid",
) -> Dict[str, Any]:
    r"""
    Compare polymer fatigue criteria for a single operating point.

    This function evaluates a reference stress-life relation, a hysteresis
    dissipation criterion, a cyclic creep strain-rate criterion, and a hybrid
    criterion. It supports both a preset-driven load-case workflow and a
    measured-loop workflow where stabilized observables are entered directly.

    ---Parameters---
    material_preset : str
        Polymer preset key. Use a literature-inspired preset such as
        `pa66_gf50`, `pa66_gf30`, or `custom_calibrated`.
    workflow_mode : str
        Input workflow. `preset_load_case` estimates loop metrics from the
        load case using preset surrogate relations. `measured_loop` uses
        direct_loop_energy_mj_per_m3 and direct_cyclic_creep_rate_per_cycle.
    orientation_bucket : str
        Fiber or molding orientation bucket. Supported preset values are
        `0_deg`, `45_deg`, and `90_deg`.
    moisture_state : str
        Conditioning state for the preset. Typical values are
        `dry_as_molded`, `conditioned`, and `wet`.
    load_ratio : float
        Stress ratio `R = \sigma_{min} / \sigma_{max}`. Common fatigue cases are
        `R = -1` for fully reversed loading, `R = 0` for pulsating tension, and
        `R = 0.1` or higher for tension-tension loading. In this tool, `R`
        combines with stress_amplitude_mpa to recover `\sigma_{max}`,
        `\sigma_{min}`, and mean stress, so it strongly affects creep tendency
        and mean-stress sensitivity. Must be less than 1.
    stress_amplitude_mpa : float
        Cyclic stress amplitude in MPa. Used directly in the reference model
        and in preset-based loop-metric surrogates.
    temperature_c : float
        Service temperature in deg C. Used for range checking and explicit
        environmental sensitivity factors.
    load_frequency_hz : float
        Load frequency in Hz. Used for range checking, hours conversion, and
        preset-side environmental sensitivity factors.
    target_life_cycles : float
        Target life in cycles used for comparison and status messaging.
    direct_loop_energy_mj_per_m3 : float
        Stabilized hysteresis dissipation per cycle in MJ/m^3. Required for
        the `measured_loop` workflow when the energy criterion is enabled.
    direct_cyclic_creep_rate_per_cycle : float
        Stabilized cyclic creep strain-rate metric per cycle. Required for the
        `measured_loop` workflow when the creep or hybrid criteria are enabled.
    ultimate_strength_mpa : float
        Custom preset ultimate strength in MPa for `custom_calibrated`.
    yield_strength_mpa : float
        Custom preset static strength in MPa for `custom_calibrated`.
    reference_strength_coeff_mpa : float
        Reference stress-life coefficient in MPa for `custom_calibrated`.
    reference_exponent : float
        Reference stress-life exponent. Must be negative.
    energy_surrogate_coeff : float
        Coefficient for converting stress amplitude to loop energy in the
        preset-load-case workflow for `custom_calibrated`.
    energy_surrogate_exponent : float
        Exponent for the loop-energy surrogate relation.
    energy_life_constant : float
        Coefficient in the energy-life relation for `custom_calibrated`.
    energy_life_exponent : float
        Exponent in the energy-life relation. Must be positive.
    creep_surrogate_coeff : float
        Coefficient for converting max stress to cyclic creep rate in the
        preset-load-case workflow for `custom_calibrated`.
    creep_surrogate_exponent : float
        Exponent for the cyclic-creep surrogate relation.
    creep_life_constant : float
        Coefficient in the creep-life relation for `custom_calibrated`.
    creep_life_exponent : float
        Exponent in the creep-life relation. Must be positive.
    hybrid_creep_weight : float
        Base weighting toward the creep-life contribution in the hybrid
        criterion. Typical range is 0.2 to 0.8.
    mean_stress_sensitivity : float
        Sensitivity used by the reference model to penalize positive mean
        stress and limit over-credit from compressive mean stress.
    basquin_convention : str
        Reversal/cycle convention for the Basquin relation. When empty
        (default), uses the preset value. ``"reversals"`` applies a 0.5
        prefactor (2Nf convention); ``"cycles"`` omits it.
    enabled_models : str
        Comma-separated list of models to evaluate. Supported entries are
        `reference`, `energy`, `cyclic_creep`, and `hybrid`.

    ---Returns---
    material_preset_name : str
        Display name of the resolved preset.
    workflow_mode_resolved : str
        Workflow that was used for the computation.
    sigma_max_mpa : float
        Derived maximum stress in MPa from the amplitude and load ratio.
    sigma_min_mpa : float
        Derived minimum stress in MPa from the amplitude and load ratio.
    sigma_mean_mpa : float
        Derived mean stress in MPa.
    loop_energy_mj_per_m3 : float
        Stabilized hysteresis loop energy used in the comparison.
    cyclic_creep_rate_per_cycle : float
        Stabilized cyclic creep strain-rate metric used in the comparison.
    lcf_hcf_regime : str
        Regime label derived from the governing life estimate.
    mechanism_regime : str
        Mechanism label comparing the normalized energy and creep observables.
    comparison_table : list
        List of per-model comparison rows with life predictions and warnings.
    governing_model : str
        Model with the shortest valid predicted life.
    least_conservative_model : str
        Model with the longest valid predicted life.
    life_spread_ratio : float
        Ratio of maximum to minimum valid predicted life.
    status : str
        Overall comparison status: acceptable, marginal, or unacceptable.
    warnings : list
        Top-level warnings collected during validation and range checking.
    recommendations : list
        Suggested next actions or interpretation guidance.
    criterion_plot_data : dict
        Plot-ready life-by-criterion data.
    sweep_plot_data : dict
        Plot-ready sweep data for current workflow.
    calibration_plot_data : dict
        Plot-ready envelope data showing the current point against preset
        calibration bounds.
    frequency_guidance : dict
        Distinguishes the current criterion-fit frequency window from broader
        published fatigue-frequency evidence for the selected material family.
    subst_loop_energy : str
        Substituted relation used to define the loop-energy input.
    subst_cyclic_creep_rate : str
        Substituted relation used to define the cyclic-creep input.

    ---LaTeX---
    \sigma_{max} = \frac{2 \sigma_a}{1 - R}
    \sigma_{min} = R \sigma_{max}
    \sigma_m = \frac{\sigma_{max} + \sigma_{min}}{2}
    W_d = \oint \sigma \, d\varepsilon
    \log N_f = A + B \log W_d
    \log N_f = C + D \log \left( d\varepsilon_{max}/dN \right)
    \sigma_{a,ref} = \sigma_a \left(1 + k_m \frac{\max(\sigma_m, 0)}{S_{ut}} \right) \quad (\sigma_m \ge 0)
    \sigma_{a,ref} = \sigma_a \max\!\left(f_{\min},\; 1 - k_c \frac{|\sigma_m|}{S_{ut}} \right) \quad (\sigma_m < 0)
    N_f = \frac{1}{2} \left(\frac{\sigma_{a,ref}}{\sigma_f'}\right)^{1/b} \quad \text{(reversals convention)}
    f_R^{(\text{energy})} = \bigl(1 + k_+ \max(R,0)\bigr)\bigl(1 + k_- \max(-R,0)\bigr)
    f_R^{(\text{creep})} = 1 + k_c \max(R,0)
    w_c = \text{clamp}\!\left(w_{c,0} + a_+ \max(R,0) - a_- \max(-R,0),\; w_{\min},\; w_{\max}\right)
    \frac{1}{N_{hybrid}} = \frac{w_c}{N_{creep}} + \frac{1-w_c}{N_{energy}}
    """
    if workflow_mode not in {"preset_load_case", "measured_loop"}:
        raise ValueError("workflow_mode must be 'preset_load_case' or 'measured_loop'.")
    if reference_exponent >= 0.0:
        raise ValueError("reference_exponent must be negative.")
    if energy_life_exponent <= 0.0:
        raise ValueError("energy_life_exponent must be > 0.")
    if creep_life_exponent <= 0.0:
        raise ValueError("creep_life_exponent must be > 0.")

    _validate_positive("target_life_cycles", target_life_cycles)
    _validate_positive("load_frequency_hz", load_frequency_hz)

    enabled = [item.strip().lower() for item in enabled_models.split(",") if item.strip()]
    valid_models = {"reference", "energy", "cyclic_creep", "hybrid"}
    if not enabled or any(model not in valid_models for model in enabled):
        raise ValueError(
            "enabled_models must be a comma-separated subset of: "
            "reference, energy, cyclic_creep, hybrid."
        )

    preset = _resolve_preset(
        material_preset=material_preset,
        ultimate_strength_mpa=ultimate_strength_mpa,
        yield_strength_mpa=yield_strength_mpa,
        reference_strength_coeff_mpa=reference_strength_coeff_mpa,
        reference_exponent=reference_exponent,
        energy_surrogate_coeff=energy_surrogate_coeff,
        energy_surrogate_exponent=energy_surrogate_exponent,
        energy_life_constant=energy_life_constant,
        energy_life_exponent=energy_life_exponent,
        creep_surrogate_coeff=creep_surrogate_coeff,
        creep_surrogate_exponent=creep_surrogate_exponent,
        creep_life_constant=creep_life_constant,
        creep_life_exponent=creep_life_exponent,
        hybrid_creep_weight=hybrid_creep_weight,
        mean_stress_sensitivity=mean_stress_sensitivity,
    )

    if basquin_convention:
        preset["basquin_convention"] = basquin_convention

    _validate_positive("preset ultimate_strength_mpa", float(preset["ultimate_strength_mpa"]))
    _validate_positive("preset yield_strength_mpa", float(preset["yield_strength_mpa"]))
    _validate_positive(
        "preset reference_strength_coeff_mpa", float(preset["reference_strength_coeff_mpa"])
    )

    stress_state = _compute_stress_state(stress_amplitude_mpa, load_ratio)
    environment = _environment_damage_factor(
        temperature_c=temperature_c,
        load_frequency_hz=load_frequency_hz,
        moisture_state=moisture_state,
        orientation_bucket=orientation_bucket,
        preset=preset,
    )
    frequency_guidance = _build_frequency_guidance(
        preset=preset,
        load_frequency_hz=load_frequency_hz,
    )

    top_level_warnings: List[str] = []
    _append_range_warnings(
        warnings=top_level_warnings,
        preset=preset,
        load_ratio=load_ratio,
        temperature_c=temperature_c,
        load_frequency_hz=load_frequency_hz,
        moisture_state=moisture_state,
        frequency_guidance=frequency_guidance,
    )

    if orientation_bucket not in set(preset["orientation_options"]):
        top_level_warnings.append("Orientation bucket is outside the preset calibration range.")

    if workflow_mode == "measured_loop":
        loop_energy = direct_loop_energy_mj_per_m3
        cyclic_creep_rate = direct_cyclic_creep_rate_per_cycle
        loop_energy_source = "direct entry"
        cyclic_creep_source = "direct entry"
    else:
        surrogate = _surrogate_loop_metrics(
            stress_amplitude_mpa=stress_amplitude_mpa,
            sigma_max_mpa=stress_state["sigma_max_mpa"],
            load_ratio=load_ratio,
            preset=preset,
            environment=environment,
        )
        loop_energy = surrogate["loop_energy_mj_per_m3"]
        cyclic_creep_rate = surrogate["cyclic_creep_rate_per_cycle"]
        loop_energy_source = "preset surrogate"
        cyclic_creep_source = "preset surrogate"

    normalized_energy = loop_energy / float(preset["representative_energy_mj_per_m3"])
    normalized_creep = cyclic_creep_rate / float(preset["representative_creep_rate_per_cycle"])
    if normalized_energy > 1.25 * normalized_creep:
        mechanism_regime = "hysteresis-dominated"
    elif normalized_creep > 1.25 * normalized_energy:
        mechanism_regime = "creep-dominated"
    else:
        mechanism_regime = "mixed"

    sigma_reference = _reference_equivalent_stress(
        stress_amplitude_mpa=stress_amplitude_mpa,
        sigma_mean_mpa=stress_state["sigma_mean_mpa"],
        ultimate_strength_mpa=float(preset["ultimate_strength_mpa"]),
        mean_stress_sensitivity=float(preset["mean_stress_sensitivity"]),
        preset=preset,
    )
    reference_life_cycles = _basquin_life(
        sigma_reference,
        float(preset["reference_strength_coeff_mpa"]),
        float(preset["reference_exponent"]),
        basquin_convention=preset["basquin_convention"],
    )

    energy_life_cycles = _energy_life(loop_energy, preset) if loop_energy > 0.0 else None
    creep_life_cycles = (
        _creep_life(cyclic_creep_rate, preset) if cyclic_creep_rate > 0.0 else None
    )
    hybrid_result = (
        _hybrid_life(energy_life_cycles, creep_life_cycles, load_ratio, preset)
        if energy_life_cycles is not None and creep_life_cycles is not None
        else {"hybrid_life_cycles": None, "creep_weight": 0.0, "energy_weight": 0.0}
    )
    hybrid_life_cycles = hybrid_result["hybrid_life_cycles"]

    comparison_table: List[Dict[str, Any]] = []

    if "reference" in enabled:
        reference_warnings = list(top_level_warnings)
        if workflow_mode == "measured_loop":
            reference_warnings.append(
                "Reference model still uses stress amplitude; energy and creep metrics are not used."
            )
        reference_state = "warning" if reference_warnings else "valid"
        subst_reference = (
            r"\sigma_{a,ref} = \sigma_a \cdot \text{mean-stress factor}"
            f" = {stress_amplitude_mpa:.1f} \\times "
            f"{sigma_reference / stress_amplitude_mpa:.3f}"
            f" = {sigma_reference:.1f}\\,\\text{{MPa}},\\;"
            f"N_f = 0.5 \\left(\\frac{{{sigma_reference:.1f}}}{{{float(preset['reference_strength_coeff_mpa']):.1f}}}\\right)^"
            f"{{{1.0 / float(preset['reference_exponent']):.3f}}}"
            f" = {reference_life_cycles:.2e}"
        )
        comparison_table.append(
            _make_model_row(
                model_key="reference",
                display_name="Reference stress-life",
                estimated_life_cycles=reference_life_cycles,
                target_life_cycles=target_life_cycles,
                load_frequency_hz=load_frequency_hz,
                source_title="Internal reference model",
                source_url="",
                used_observables={
                    "stress_amplitude_mpa": stress_amplitude_mpa,
                    "sigma_mean_mpa": stress_state["sigma_mean_mpa"],
                },
                applicability_state=reference_state,
                warning_messages=reference_warnings,
                subst_estimated_life_cycles=subst_reference,
            )
        )

    if "energy" in enabled:
        energy_warnings = list(top_level_warnings)
        energy_state = "valid"
        if workflow_mode == "measured_loop" and direct_loop_energy_mj_per_m3 <= 0.0:
            energy_state = "invalid"
            energy_warnings.append("Measured-loop workflow requires positive loop energy.")
            energy_cycles_or_none = None
            subst_energy = r"W_d \text{ missing} \Rightarrow N_f \text{ unavailable}"
        else:
            energy_bounds = (
                float(preset["calibration_energy_min_mj_per_m3"]),
                float(preset["calibration_energy_max_mj_per_m3"]),
            )
            if loop_energy < energy_bounds[0] or loop_energy > energy_bounds[1]:
                energy_state = "warning"
                energy_warnings.append("Loop energy is outside the preset calibration envelope.")
            elif energy_warnings:
                energy_state = "warning"
            energy_cycles_or_none = energy_life_cycles
            subst_energy = (
                f"W_d = {loop_energy:.3f}\\,\\text{{MJ/m}}^3,\\;"
                f"N_f = {float(preset['energy_life_constant']):.2e}"
                f"\\times W_d^{{-{float(preset['energy_life_exponent']):.3f}}}"
                f" = {energy_life_cycles:.2e}"
            )
        comparison_table.append(
            _make_model_row(
                model_key="energy",
                display_name="Hysteresis energy criterion",
                estimated_life_cycles=energy_cycles_or_none,
                target_life_cycles=target_life_cycles,
                load_frequency_hz=load_frequency_hz,
                source_title=str(preset["source_title"]),
                source_url=str(preset["source_url"]),
                used_observables={
                    "loop_energy_mj_per_m3": loop_energy,
                    "energy_source": loop_energy_source,
                },
                applicability_state=energy_state,
                warning_messages=energy_warnings,
                subst_estimated_life_cycles=subst_energy,
            )
        )

    if "cyclic_creep" in enabled:
        creep_warnings = list(top_level_warnings)
        creep_state = "valid"
        if workflow_mode == "measured_loop" and direct_cyclic_creep_rate_per_cycle <= 0.0:
            creep_state = "invalid"
            creep_warnings.append("Measured-loop workflow requires positive cyclic creep rate.")
            creep_cycles_or_none = None
            subst_creep = r"d\varepsilon_{max}/dN \text{ missing} \Rightarrow N_f \text{ unavailable}"
        else:
            creep_bounds = (
                float(preset["calibration_creep_rate_min_per_cycle"]),
                float(preset["calibration_creep_rate_max_per_cycle"]),
            )
            if cyclic_creep_rate < creep_bounds[0] or cyclic_creep_rate > creep_bounds[1]:
                creep_state = "warning"
                creep_warnings.append("Cyclic creep rate is outside the preset calibration envelope.")
            elif creep_warnings:
                creep_state = "warning"
            creep_cycles_or_none = creep_life_cycles
            subst_creep = (
                r"\frac{d\varepsilon_{max}}{dN}"
                f" = {cyclic_creep_rate:.3e},\\;"
                f"N_f = {float(preset['creep_life_constant']):.3f}"
                f"\\times \\left(\\frac{{d\\varepsilon_{{max}}}}{{dN}}\\right)^"
                f"{{-{float(preset['creep_life_exponent']):.3f}}}"
                f" = {creep_life_cycles:.2e}"
            )
        comparison_table.append(
            _make_model_row(
                model_key="cyclic_creep",
                display_name="Cyclic creep-rate criterion",
                estimated_life_cycles=creep_cycles_or_none,
                target_life_cycles=target_life_cycles,
                load_frequency_hz=load_frequency_hz,
                source_title=str(preset["source_title"]),
                source_url=str(preset["source_url"]),
                used_observables={
                    "cyclic_creep_rate_per_cycle": cyclic_creep_rate,
                    "creep_source": cyclic_creep_source,
                },
                applicability_state=creep_state,
                warning_messages=creep_warnings,
                subst_estimated_life_cycles=subst_creep,
            )
        )

    if "hybrid" in enabled:
        hybrid_warnings = list(top_level_warnings)
        hybrid_state = "valid"
        if workflow_mode == "measured_loop" and (
            direct_loop_energy_mj_per_m3 <= 0.0 or direct_cyclic_creep_rate_per_cycle <= 0.0
        ):
            hybrid_state = "invalid"
            hybrid_warnings.append(
                "Hybrid criterion requires both loop energy and cyclic creep rate."
            )
            hybrid_cycles_or_none = None
            subst_hybrid = r"N_{hybrid} \text{ unavailable because one required observable is missing}"
        else:
            if hybrid_warnings:
                hybrid_state = "warning"
            if any(
                row["applicability_state"] == "invalid"
                for row in comparison_table
                if row["model"] in {"energy", "cyclic_creep"}
            ):
                hybrid_state = "invalid"
                hybrid_warnings.append(
                    "Hybrid criterion is invalid because one component criterion is invalid."
                )
                hybrid_cycles_or_none = None
                subst_hybrid = r"N_{hybrid} \text{ unavailable}"
            else:
                hybrid_cycles_or_none = hybrid_life_cycles
                subst_hybrid = (
                    f"w_c = {hybrid_result['creep_weight']:.3f},\\;"
                    f"N_{{hybrid}} = \\left(\\frac{{w_c}}{{N_{{creep}}}} + "
                    f"\\frac{{1-w_c}}{{N_{{energy}}}}\\right)^{{-1}}"
                    f" = {hybrid_life_cycles:.2e}"
                )
        comparison_table.append(
            _make_model_row(
                model_key="hybrid",
                display_name="Hybrid energy + creep criterion",
                estimated_life_cycles=hybrid_cycles_or_none,
                target_life_cycles=target_life_cycles,
                load_frequency_hz=load_frequency_hz,
                source_title=str(preset["source_title"]),
                source_url=str(preset["source_url"]),
                used_observables={
                    "loop_energy_mj_per_m3": loop_energy,
                    "cyclic_creep_rate_per_cycle": cyclic_creep_rate,
                    "creep_weight": hybrid_result["creep_weight"],
                },
                applicability_state=hybrid_state,
                warning_messages=hybrid_warnings,
                subst_estimated_life_cycles=subst_hybrid,
            )
        )

    valid_rows = [
        row
        for row in comparison_table
        if row["estimated_life_cycles"] is not None and row["applicability_state"] != "invalid"
    ]
    if not valid_rows:
        raise ValueError("No enabled model returned a valid life prediction for this operating point.")

    valid_rows_sorted = sorted(valid_rows, key=lambda row: float(row["estimated_life_cycles"]))
    governing_row = valid_rows_sorted[0]
    least_conservative_row = valid_rows_sorted[-1]
    life_spread_ratio = float(least_conservative_row["estimated_life_cycles"]) / float(
        governing_row["estimated_life_cycles"]
    )
    governing_life = float(governing_row["estimated_life_cycles"])
    governing_life_ratio = governing_life / target_life_cycles
    lcf_hcf_regime = _life_to_regime(governing_life)

    if governing_life_ratio >= 1.2 and life_spread_ratio <= 2.5:
        status = "acceptable"
    elif governing_life_ratio >= 1.0:
        status = "marginal"
    else:
        status = "unacceptable"

    recommendations: List[str] = []
    if status != "acceptable":
        recommendations.append(
            "Reduce stress amplitude, improve orientation/load path, or compare against measured loop data before relying on the governing criterion."
        )
    if any(row["applicability_state"] == "warning" for row in comparison_table):
        recommendations.append(
            "At least one compared criterion is outside or near its calibration limits. Treat the result as exploratory."
        )
    if workflow_mode == "preset_load_case":
        recommendations.append(
            "Use measured stabilized loop energy and cyclic creep rate when available; preset surrogates are useful for exploration but not sign-off."
        )
    if not frequency_guidance["within_fit_range"]:
        recommendations.append(
            "The requested cycling frequency is outside the current criterion-fit window. Keep the result as a data-informed extrapolation unless you recalibrate the model at that frequency."
        )
    if mechanism_regime == "creep-dominated":
        recommendations.append(
            "Cyclic creep is a strong damage indicator for this point. Review temperature, mean stress, and dwell effects before generalizing the life estimate."
        )
    elif mechanism_regime == "hysteresis-dominated":
        recommendations.append(
            "Dissipation is a strong damage indicator for this point. Watch self-heating and test frequency sensitivity."
        )
    else:
        recommendations.append(
            "Energy and cyclic creep indicators are of similar importance here; keep both in view rather than choosing a single metric too early."
        )

    criterion_plot_data = {
        "labels": [row["display_name"] for row in comparison_table],
        "life_cycles": [row["estimated_life_cycles"] for row in comparison_table],
        "life_ratio_to_target": [row["life_ratio_to_target"] for row in comparison_table],
        "applicability_states": [row["applicability_state"] for row in comparison_table],
        "target_life_cycles": target_life_cycles,
    }
    sweep_plot_data = _build_sweep_plot_data(
        workflow_mode=workflow_mode,
        preset=preset,
        load_ratio=load_ratio,
        temperature_c=temperature_c,
        load_frequency_hz=load_frequency_hz,
        moisture_state=moisture_state,
        orientation_bucket=orientation_bucket,
        stress_amplitude_mpa=stress_amplitude_mpa,
        loop_energy_mj_per_m3=loop_energy,
        cyclic_creep_rate_per_cycle=cyclic_creep_rate,
    )

    subst_loop_energy = (
        f"W_d = {loop_energy:.3f}\\,\\text{{MJ/m}}^3\\;"
        f"\\text{{({loop_energy_source})}}"
    )
    subst_cyclic_creep_rate = (
        r"\frac{d\varepsilon_{max}}{dN}"
        f" = {cyclic_creep_rate:.3e}\\;"
        f"\\text{{({cyclic_creep_source})}}"
    )

    return {
        "material_preset": material_preset,
        "material_preset_name": str(preset["display_name"]),
        "workflow_mode_resolved": workflow_mode,
        "load_ratio": load_ratio,
        "stress_amplitude_mpa": stress_amplitude_mpa,
        "sigma_max_mpa": stress_state["sigma_max_mpa"],
        "sigma_min_mpa": stress_state["sigma_min_mpa"],
        "sigma_mean_mpa": stress_state["sigma_mean_mpa"],
        "temperature_c": temperature_c,
        "load_frequency_hz": load_frequency_hz,
        "moisture_state": moisture_state,
        "orientation_bucket": orientation_bucket,
        "loop_energy_mj_per_m3": loop_energy,
        "cyclic_creep_rate_per_cycle": cyclic_creep_rate,
        "environment_factor": environment["combined_factor"],
        "temperature_factor": environment["temperature_factor"],
        "frequency_factor": environment["frequency_factor"],
        "moisture_factor": environment["moisture_factor"],
        "orientation_factor": environment["orientation_factor"],
        "target_life_cycles": target_life_cycles,
        "lcf_hcf_regime": lcf_hcf_regime,
        "mechanism_regime": mechanism_regime,
        "comparison_table": comparison_table,
        "governing_model": governing_row["display_name"],
        "least_conservative_model": least_conservative_row["display_name"],
        "life_spread_ratio": life_spread_ratio,
        "status": status,
        "warnings": top_level_warnings,
        "applicability_summary": [
            {
                "model": row["model"],
                "display_name": row["display_name"],
                "state": row["applicability_state"],
            }
            for row in comparison_table
        ],
        "recommendations": recommendations,
        "criterion_plot_data": criterion_plot_data,
        "sweep_plot_data": sweep_plot_data,
        "calibration_plot_data": _calibration_plot_data(
            loop_energy_mj_per_m3=loop_energy,
            cyclic_creep_rate_per_cycle=cyclic_creep_rate,
            preset=preset,
        ),
        "frequency_guidance": frequency_guidance,
        "stress_waveform_plot_data": _build_stress_waveform_data(
            stress_state=stress_state,
            stress_amplitude_mpa=stress_amplitude_mpa,
            load_ratio=load_ratio,
        ),
        "subst_loop_energy": subst_loop_energy,
        "subst_cyclic_creep_rate": subst_cyclic_creep_rate,
    }
