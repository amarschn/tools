"""
Interference-fit and shrink-fit calculations for cylindrical shaft-hub joints.

This module implements elastic press-fit relations for straight cylindrical
assemblies using the thick-cylinder compliance and stress treatment commonly
presented in Shigley's Mechanical Engineering Design.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

try:
    from .rotor_stress import calculate_rotor_hoop_stress
except ImportError:  # Pyodide loads tool modules as top-level files.
    from rotor_stress import calculate_rotor_hoop_stress


VON_MISES = "von_mises"
BRITTLE = "brittle"


def _ductile(
    display_name: str,
    condition: str,
    youngs_modulus_mpa: float,
    poisson_ratio: float,
    yield_strength_mpa: float,
    thermal_expansion_e6_per_c: float,
    density_kg_m3: float,
    source: str,
) -> Dict[str, float | str]:
    """Build a preset checked with von Mises against its yield strength."""

    return {
        "display_name": display_name,
        "condition": condition,
        "youngs_modulus_mpa": youngs_modulus_mpa,
        "poisson_ratio": poisson_ratio,
        "yield_strength_mpa": yield_strength_mpa,
        "tensile_strength_mpa": yield_strength_mpa,
        "compressive_strength_mpa": yield_strength_mpa,
        "thermal_expansion_e6_per_c": thermal_expansion_e6_per_c,
        "density_kg_m3": density_kg_m3,
        "failure_criterion": VON_MISES,
        "source": source,
    }


def _brittle(
    display_name: str,
    condition: str,
    youngs_modulus_mpa: float,
    poisson_ratio: float,
    tensile_strength_mpa: float,
    compressive_strength_mpa: float,
    thermal_expansion_e6_per_c: float,
    density_kg_m3: float,
    source: str,
) -> Dict[str, float | str]:
    """Build a preset checked with Coulomb-Mohr instead of von Mises.

    Gray iron has no yield point and carries roughly three to four times more
    compression than tension, so a von Mises check against a nominal "yield"
    is wrong in both directions. `yield_strength_mpa` is carried at the
    tensile strength so legacy consumers still read a sensible number.
    """

    return {
        "display_name": display_name,
        "condition": condition,
        "youngs_modulus_mpa": youngs_modulus_mpa,
        "poisson_ratio": poisson_ratio,
        "yield_strength_mpa": tensile_strength_mpa,
        "tensile_strength_mpa": tensile_strength_mpa,
        "compressive_strength_mpa": compressive_strength_mpa,
        "thermal_expansion_e6_per_c": thermal_expansion_e6_per_c,
        "density_kg_m3": density_kg_m3,
        "failure_criterion": BRITTLE,
        "source": source,
    }


ASM = "ASM Metals Handbook, typical room-temperature values"
ASTM_A48 = "ASTM A48 gray iron, typical class properties"
ASTM_A536 = "ASTM A536 ductile iron, typical grade properties"
CDA = "Copper Development Association alloy data"
IDEAL_TEK_52100 = (
    "ideal-tek AISI 52100 ball-bearing steel technical data sheet; "
    "Poisson ratio from Shah, INSA Lyon thesis (2011), Appendix A"
)

MATERIAL_PRESETS: Dict[str, Dict[str, float | str]] = {
    "steel": _ductile(
        "Steel (Generic)", "generic mild steel",
        200000.0, 0.30, 350.0, 12.0, 7850.0, ASM,
    ),
    "steel_1020": _ductile(
        "Steel 1020 (Hot Rolled)", "hot rolled",
        207000.0, 0.292, 210.0, 11.7, 7870.0, ASM,
    ),
    "steel_1020_cd": _ductile(
        "Steel 1020 (Cold Drawn)", "cold drawn",
        207000.0, 0.292, 350.0, 11.7, 7870.0, ASM,
    ),
    "steel_1045_annealed": _ductile(
        "Steel 1045 (Annealed)", "annealed",
        207000.0, 0.292, 310.0, 11.7, 7850.0, ASM,
    ),
    "steel_4140_normalized": _ductile(
        "Steel 4140 (Normalized)", "normalized at 870 C",
        207000.0, 0.292, 655.0, 11.7, 7850.0, ASM,
    ),
    "steel_4140_qt": _ductile(
        "Steel 4140 (Q&T 540 C)", "oil quenched, tempered at 540 C",
        207000.0, 0.292, 1140.0, 11.7, 7850.0, ASM,
    ),
    "steel_4340_annealed": _ductile(
        "Steel 4340 (Annealed)", "annealed",
        207000.0, 0.292, 470.0, 12.3, 7850.0, ASM,
    ),
    "steel_4340_qt": _ductile(
        "Steel 4340 (Q&T 540 C)", "oil quenched, tempered at 540 C",
        207000.0, 0.292, 1170.0, 12.3, 7850.0, ASM,
    ),
    "steel_52100_hardened": _ductile(
        "AISI 52100 (Hardened 65-68 HRC)", "through hardened, 65-68 HRC",
        212000.0, 0.30, 1800.0, 12.0, 7850.0, IDEAL_TEK_52100,
    ),
    "stainless_steel": _ductile(
        "Stainless Steel (Generic)", "generic austenitic, annealed",
        193000.0, 0.31, 215.0, 17.3, 8000.0, ASM,
    ),
    "stainless_304": _ductile(
        "Stainless 304", "annealed",
        193000.0, 0.29, 207.0, 17.2, 8000.0, ASM,
    ),
    "stainless_316": _ductile(
        "Stainless 316", "annealed",
        193000.0, 0.29, 207.0, 16.0, 8000.0, ASM,
    ),
    "stainless_17_4ph_h900": _ductile(
        "Stainless 17-4 PH (H900)", "solution treated and aged at 480 C",
        197000.0, 0.272, 1170.0, 10.8, 7800.0, ASM,
    ),
    "aluminum": _ductile(
        "Aluminum Alloy (Generic)", "generic wrought alloy",
        70000.0, 0.33, 150.0, 23.0, 2700.0, ASM,
    ),
    "aluminum_2024_t4": _ductile(
        "Aluminum 2024-T4", "solution treated and naturally aged",
        73000.0, 0.33, 324.0, 22.9, 2780.0, ASM,
    ),
    "aluminum_6061_t6": _ductile(
        "Aluminum 6061-T6", "solution treated and artificially aged",
        69000.0, 0.33, 276.0, 23.6, 2700.0, ASM,
    ),
    "aluminum_7075_t6": _ductile(
        "Aluminum 7075-T6", "solution treated and artificially aged",
        72000.0, 0.33, 503.0, 23.6, 2810.0, ASM,
    ),
    "cast_iron": _brittle(
        "Cast Iron (Generic Gray)", "as cast, generic gray iron",
        110000.0, 0.26, 210.0, 750.0, 10.8, 7200.0, ASTM_A48,
    ),
    "cast_iron_gray": _brittle(
        "Cast Iron (Gray, Class 30)", "as cast",
        103000.0, 0.26, 214.0, 752.0, 11.4, 7150.0, ASTM_A48,
    ),
    "cast_iron_gray_class40": _brittle(
        "Cast Iron (Gray, Class 40)", "as cast",
        124000.0, 0.26, 293.0, 965.0, 11.4, 7150.0, ASTM_A48,
    ),
    "ductile_iron_65_45_12": _ductile(
        "Ductile Iron 65-45-12", "as cast, ferritic",
        168000.0, 0.29, 310.0, 11.7, 7150.0, ASTM_A536,
    ),
    "bronze": _ductile(
        "Bronze C90300 (Tin)", "as cast",
        103000.0, 0.34, 145.0, 18.0, 8800.0, CDA,
    ),
    "bronze_bearing": _ductile(
        "Bronze C93200 (Bearing, SAE 660)", "as cast",
        100000.0, 0.34, 125.0, 18.0, 8930.0, CDA,
    ),
    "brass": _ductile(
        "Brass (Generic)", "generic wrought brass",
        100000.0, 0.35, 120.0, 20.0, 8500.0, CDA,
    ),
    "brass_7030": _ductile(
        "Brass 70/30 (Cartridge, H02)", "half hard",
        110000.0, 0.34, 200.0, 19.9, 8530.0, CDA,
    ),
    "copper": _ductile(
        "Copper (Generic)", "generic wrought copper",
        117000.0, 0.34, 70.0, 17.0, 8960.0, CDA,
    ),
    "copper_annealed": _ductile(
        "Copper C11000 (Annealed)", "annealed",
        117000.0, 0.34, 70.0, 16.5, 8960.0, CDA,
    ),
    "titanium_6al4v": _ductile(
        "Titanium 6Al-4V", "annealed",
        114000.0, 0.342, 880.0, 8.6, 4430.0, ASM,
    ),
    "custom": _ductile(
        "Custom Material", "user defined",
        200000.0, 0.30, 350.0, 12.0, 7850.0, "user supplied",
    ),
}


def get_interference_fit_material_presets() -> Dict[str, Dict[str, float | str]]:
    """
    Return the built-in shaft and hub material presets.

    Returns
    -------
    dict
        Material presets keyed by preset name.
    """

    return {
        key: dict(value)
        for key, value in MATERIAL_PRESETS.items()
    }


def get_interference_fit_friction_presets() -> Dict[str, Dict[str, float | str]]:
    """
    Return friction coefficient presets by material pair and assembly method.

    Values follow the typical ranges published in DIN 7190 for slip in the
    circumferential direction. Friction is the dominant uncertainty in any
    interference fit, so each preset carries the range it was drawn from.

    Returns
    -------
    dict
        Friction presets keyed by preset name.
    """

    return {key: dict(value) for key, value in FRICTION_PRESETS.items()}


def get_interference_fit_roughness_presets() -> Dict[str, Dict[str, float | str]]:
    """
    Return surface roughness presets used for the assembly smoothing loss.

    Returns
    -------
    dict
        Roughness presets keyed by preset name, carrying Rz in micrometres.
    """

    return {key: dict(value) for key, value in ROUGHNESS_PRESETS.items()}


def _smoothing_loss_mm(
    shaft_roughness_rz_um: float,
    hub_roughness_rz_um: float,
) -> float:
    """Return diametral interference lost to asperity flattening at assembly.

    DIN 7190 charges 0.8 (Rz_shaft + Rz_hub) against the specified diametral
    interference. The peaks of both surfaces crush down during assembly, so
    the interference that actually generates contact pressure is always less
    than the interference on the drawing.
    """

    total_rz_um = max(0.0, shaft_roughness_rz_um) + max(0.0, hub_roughness_rz_um)
    return 0.8 * total_rz_um * 1e-3


def _effective_fit_length_mm(
    fit_length_mm: float,
    shaft_outer_diameter_mm: float,
    length_credit_ratio: float,
) -> float:
    """Return the fit length credited with carrying load.

    Contact pressure and micro-slip concentrate at the ends of the joint, so
    length past roughly L/d = 1.5 adds very little capacity. Crediting
    the full length without a cap lets an unrealistically long fit appear to
    need almost no interference.
    """

    if length_credit_ratio <= 0.0:
        return fit_length_mm
    return min(fit_length_mm, length_credit_ratio * shaft_outer_diameter_mm)


# Diameters land on a step boundary far more often than not, and no real
# dimension is resolved below ten nanometres. Without this tolerance a value
# a few float bits over 50 mm drops into the next step and shifts the
# reported grade by a whole number.
_IT_STEP_TOLERANCE_MM = 1e-5


def _iso286_tolerance_unit_um(diameter_mm: float) -> float:
    """Return the ISO 286 tolerance unit i, in micrometres, for a diameter."""

    if diameter_mm > 500.0 + _IT_STEP_TOLERANCE_MM:
        return 0.004 * diameter_mm + 2.1

    for lower, upper in _IT_DIAMETER_STEPS_MM:
        if diameter_mm <= upper + _IT_STEP_TOLERANCE_MM:
            geometric_mean = math.sqrt(max(lower, 1.0) * upper)
            return (
                0.45 * geometric_mean ** (1.0 / 3.0)
                + 0.001 * geometric_mean
            )
    return 0.004 * diameter_mm + 2.1


def _iso286_grade_values_um(diameter_mm: float) -> Dict[int, float]:
    """Return IT grade tolerance values, in micrometres, for a diameter."""

    unit = _iso286_tolerance_unit_um(diameter_mm)
    return {
        grade: multiplier * unit
        for grade, multiplier in _IT_GRADE_MULTIPLIERS.items()
    }


def _classify_manufacturing_window(
    window_mm: float,
    shaft_outer_diameter_mm: float,
) -> Dict[str, Any]:
    """Grade the available interference window against ISO 286 IT grades.

    The window is the total spread allowed across both parts, so an equal
    split gives each part half of it. The reported grade is the coarsest, and
    therefore cheapest, IT grade that still fits inside that half.
    """

    grades = _iso286_grade_values_um(shaft_outer_diameter_mm)
    window_um = window_mm * 1000.0
    per_part_um = window_um / 2.0

    achievable = [
        grade for grade, value in sorted(grades.items())
        if value <= per_part_um
    ]
    best_grade = max(achievable) if achievable else None

    if best_grade is None:
        verdict = "tighter than IT5"
        practical = False
    elif best_grade <= 5:
        verdict = "IT5, gauge-room work"
        practical = False
    elif best_grade == 6:
        verdict = "IT6, precision grinding"
        practical = True
    elif best_grade == 7:
        verdict = "IT7, normal grinding"
        practical = True
    else:
        verdict = f"IT{best_grade} or coarser, routine machining"
        practical = True

    return {
        "total_window_um": window_um,
        "per_part_window_um": per_part_um,
        "per_part_it_grade": best_grade,
        "it_grade_values_um": grades,
        "verdict": verdict,
        "practical": practical,
    }


def _strength_safety_factor(
    radial_mpa: float,
    hoop_mpa: float,
    material: Dict[str, float | str],
) -> tuple[float, float]:
    """Return equivalent stress and safety factor under the right criterion.

    Ductile members use von Mises against yield. Brittle members such as gray
    iron have no yield point and carry far more compression than tension, so
    they use Coulomb-Mohr against separate tensile and compressive strengths.
    The reported equivalent stress for a brittle member is the tensile
    strength divided by its safety factor, so it stays comparable to the
    von Mises number the UI already plots.
    """

    criterion = str(material.get("failure_criterion", VON_MISES))
    tensile = float(material.get("tensile_strength_mpa", material["yield_strength_mpa"]))

    if criterion != BRITTLE:
        von_mises = math.sqrt(hoop_mpa**2 - hoop_mpa * radial_mpa + radial_mpa**2)
        yield_strength = float(material["yield_strength_mpa"])
        factor = yield_strength / von_mises if von_mises > 0.0 else float("inf")
        return von_mises, factor

    compressive = abs(float(material["compressive_strength_mpa"]))
    sigma_1 = max(radial_mpa, hoop_mpa)
    sigma_2 = min(radial_mpa, hoop_mpa)

    if sigma_1 >= 0.0 and sigma_2 >= 0.0:
        demand = sigma_1 / tensile if tensile > 0.0 else float("inf")
    elif sigma_1 >= 0.0 >= sigma_2:
        demand = sigma_1 / tensile - sigma_2 / compressive
    else:
        demand = abs(sigma_2) / compressive

    if demand <= 0.0:
        return 0.0, float("inf")
    return tensile * demand, 1.0 / demand


FRICTION_PRESETS: Dict[str, Dict[str, float | str]] = {
    "steel_steel_pressed_dry": {
        "display_name": "Steel on steel, pressed dry",
        "friction_coefficient": 0.09,
        "range_label": "0.07 to 0.12",
    },
    "steel_steel_pressed_oiled": {
        "display_name": "Steel on steel, pressed with light oil",
        "friction_coefficient": 0.07,
        "range_label": "0.05 to 0.10",
    },
    "steel_steel_shrink_dry": {
        "display_name": "Steel on steel, shrink fit, degreased",
        "friction_coefficient": 0.14,
        "range_label": "0.12 to 0.20",
    },
    "steel_cast_iron_pressed": {
        "display_name": "Steel on cast iron, pressed dry",
        "friction_coefficient": 0.10,
        "range_label": "0.08 to 0.12",
    },
    "steel_aluminum_pressed": {
        "display_name": "Steel on aluminum, pressed dry",
        "friction_coefficient": 0.06,
        "range_label": "0.05 to 0.08",
    },
    "steel_bronze_pressed": {
        "display_name": "Steel on bronze, pressed dry",
        "friction_coefficient": 0.06,
        "range_label": "0.05 to 0.10",
    },
    "custom": {
        "display_name": "Custom coefficient",
        "friction_coefficient": 0.15,
        "range_label": "user defined",
    },
}

ROUGHNESS_PRESETS: Dict[str, Dict[str, float | str]] = {
    "ground_fine": {"display_name": "Fine ground (Ra 0.4)", "rz_um": 2.5},
    "ground": {"display_name": "Ground (Ra 0.8)", "rz_um": 4.0},
    "turned_fine": {"display_name": "Fine turned (Ra 1.6)", "rz_um": 8.0},
    "turned": {"display_name": "Turned (Ra 3.2)", "rz_um": 16.0},
    "custom": {"display_name": "Custom Rz", "rz_um": 4.0},
}

# Standard ISO 286 diameter steps, in mm, used to pick the tolerance unit.
_IT_DIAMETER_STEPS_MM = [
    (0.0, 3.0), (3.0, 6.0), (6.0, 10.0), (10.0, 18.0), (18.0, 30.0),
    (30.0, 50.0), (50.0, 80.0), (80.0, 120.0), (120.0, 180.0),
    (180.0, 250.0), (250.0, 315.0), (315.0, 400.0), (400.0, 500.0),
]

# ISO 286 grade multipliers on the tolerance unit i, for IT5 and coarser.
_IT_GRADE_MULTIPLIERS: Dict[int, float] = {
    5: 7.0, 6: 10.0, 7: 16.0, 8: 25.0, 9: 40.0, 10: 64.0,
    11: 100.0, 12: 160.0, 13: 250.0, 14: 400.0, 15: 640.0, 16: 1000.0,
}

# Assembly temperature tiers, in deg C, used to judge shrink-fit practicality.
LIQUID_NITROGEN_C = -196.0
DRY_ICE_C = -78.0
ABSOLUTE_ZERO_C = -273.15


def _validate_finite(name: str, value: float) -> float:
    """Raise when a value is NaN or infinite.

    Comparisons against NaN are always False, so every ordering check below
    silently passes for a blank or malformed input. Screen it out first.
    """

    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number. Got {value}.")
    return number


def _validate_positive(name: str, value: float) -> None:
    """Raise when a value expected to be strictly positive is not."""

    number = _validate_finite(name, value)
    if number <= 0.0:
        raise ValueError(f"{name} must be > 0. Got {value}.")


def _validate_nonnegative(name: str, value: float) -> None:
    """Raise when a value expected to be nonnegative is not."""

    number = _validate_finite(name, value)
    if number < 0.0:
        raise ValueError(f"{name} must be >= 0. Got {value}.")


def _validate_poisson_ratio(name: str, value: float) -> None:
    """Validate a physically meaningful Poisson ratio."""

    number = _validate_finite(name, value)
    if number < 0.0 or number >= 0.5:
        raise ValueError(f"{name} must satisfy 0 <= nu < 0.5. Got {value}.")


def _lookup_material_preset(name: str) -> Dict[str, float | str]:
    """Look up a material preset by key."""

    key = name.strip().lower()
    if key not in MATERIAL_PRESETS:
        valid = ", ".join(sorted(MATERIAL_PRESETS))
        raise ValueError(f"Unknown material preset '{name}'. Valid presets: {valid}.")
    return dict(MATERIAL_PRESETS[key])


def _resolve_material(
    component_label: str,
    material_key: str,
    youngs_modulus_mpa: float,
    poisson_ratio: float,
    yield_strength_mpa: float,
    thermal_expansion_e6_per_c: float,
    density_kg_m3: float = 7850.0,
    compressive_strength_mpa: float = 0.0,
    failure_criterion: str = VON_MISES,
) -> Dict[str, float | str]:
    """Resolve a shaft or hub material from preset or custom values."""

    if material_key.strip().lower() != "custom":
        preset = _lookup_material_preset(material_key)
        resolved = {
            "material_key": material_key.strip().lower(),
            "display_name": str(preset["display_name"]),
            "condition": str(preset["condition"]),
            "youngs_modulus_mpa": float(preset["youngs_modulus_mpa"]),
            "poisson_ratio": float(preset["poisson_ratio"]),
            "yield_strength_mpa": float(preset["yield_strength_mpa"]),
            "tensile_strength_mpa": float(preset["tensile_strength_mpa"]),
            "compressive_strength_mpa": float(preset["compressive_strength_mpa"]),
            "thermal_expansion_e6_per_c": float(preset["thermal_expansion_e6_per_c"]),
            "density_kg_m3": float(preset["density_kg_m3"]),
            "failure_criterion": str(preset["failure_criterion"]),
            "source": str(preset["source"]),
        }
    else:
        criterion = failure_criterion.strip().lower()
        if criterion not in (VON_MISES, BRITTLE):
            raise ValueError(
                f"{component_label} failure_criterion must be "
                f"'{VON_MISES}' or '{BRITTLE}'. Got {failure_criterion}."
            )
        compressive = (
            float(compressive_strength_mpa)
            if compressive_strength_mpa > 0.0
            else float(yield_strength_mpa)
        )
        resolved = {
            "material_key": "custom",
            "display_name": f"Custom {component_label.title()} Material",
            "condition": "user defined",
            "youngs_modulus_mpa": youngs_modulus_mpa,
            "poisson_ratio": poisson_ratio,
            "yield_strength_mpa": yield_strength_mpa,
            "tensile_strength_mpa": yield_strength_mpa,
            "compressive_strength_mpa": compressive,
            "thermal_expansion_e6_per_c": thermal_expansion_e6_per_c,
            "density_kg_m3": density_kg_m3,
            "failure_criterion": criterion,
            "source": "user supplied",
        }

    _validate_positive(
        f"{component_label} youngs_modulus_mpa",
        float(resolved["youngs_modulus_mpa"]),
    )
    _validate_poisson_ratio(
        f"{component_label} poisson_ratio",
        float(resolved["poisson_ratio"]),
    )
    _validate_positive(
        f"{component_label} yield_strength_mpa",
        float(resolved["yield_strength_mpa"]),
    )
    _validate_positive(
        f"{component_label} density_kg_m3",
        float(resolved["density_kg_m3"]),
    )
    _validate_positive(
        f"{component_label} compressive_strength_mpa",
        float(resolved["compressive_strength_mpa"]),
    )
    _validate_nonnegative(
        f"{component_label} thermal_expansion_e6_per_c",
        float(resolved["thermal_expansion_e6_per_c"]),
    )

    return resolved


def _coerce_range(
    nominal: float,
    minimum: float | None,
    maximum: float | None,
) -> tuple[float, float, float]:
    """Resolve a nominal, minimum, and maximum interference triplet."""

    min_value = nominal if minimum is None else minimum
    max_value = nominal if maximum is None else maximum
    _validate_nonnegative("interference_nominal_mm", nominal)
    _validate_nonnegative("interference_min_mm", min_value)
    _validate_nonnegative("interference_max_mm", max_value)

    if min_value > nominal:
        raise ValueError("interference_min_mm must be <= interference_nominal_mm.")
    if nominal > max_value:
        raise ValueError("interference_nominal_mm must be <= interference_max_mm.")

    return min_value, nominal, max_value


def _hub_geometry_factor(fit_diameter_m: float, hub_outer_diameter_m: float) -> float:
    """Return the thick-cylinder compliance factor for the hub."""

    denominator = hub_outer_diameter_m**2 - fit_diameter_m**2
    if denominator <= 0.0:
        raise ValueError("hub_outer_diameter_mm must be greater than shaft_outer_diameter_mm.")
    return (hub_outer_diameter_m**2 + fit_diameter_m**2) / denominator


def _shaft_geometry_factor(
    fit_diameter_m: float,
    shaft_inner_diameter_m: float,
) -> float:
    """Return the thick-cylinder compliance factor for a hollow shaft."""

    if shaft_inner_diameter_m <= 0.0:
        return 1.0

    denominator = fit_diameter_m**2 - shaft_inner_diameter_m**2
    if denominator <= 0.0:
        raise ValueError("shaft_inner_diameter_mm must be less than shaft_outer_diameter_mm.")
    return (fit_diameter_m**2 + shaft_inner_diameter_m**2) / denominator


def _calculate_interface_pressure_mpa(
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    interference_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> float:
    """Calculate interface pressure from elastic diametral interference."""

    if interference_mm <= 0.0:
        return 0.0

    d = shaft_outer_diameter_mm * 1e-3
    D = hub_outer_diameter_mm * 1e-3
    di = shaft_inner_diameter_mm * 1e-3
    delta = interference_mm * 1e-3

    e_h = float(hub_material["youngs_modulus_mpa"]) * 1e6
    nu_h = float(hub_material["poisson_ratio"])
    e_s = float(shaft_material["youngs_modulus_mpa"]) * 1e6
    nu_s = float(shaft_material["poisson_ratio"])

    hub_factor = _hub_geometry_factor(d, D)
    shaft_factor = _shaft_geometry_factor(d, di)

    shaft_term = (1.0 - nu_s) if di <= 0.0 else (shaft_factor - nu_s)
    denominator = (d / e_h) * (hub_factor + nu_h) + (d / e_s) * shaft_term
    if denominator <= 0.0:
        raise ValueError("Calculated interference-fit compliance denominator is not positive.")

    return delta / denominator / 1e6


def _calculate_compliance_data(
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> Dict[str, float]:
    """Return Shigley-style geometry and compliance factors for the fit."""

    d_m = shaft_outer_diameter_mm * 1e-3
    D_m = hub_outer_diameter_mm * 1e-3
    di_m = shaft_inner_diameter_mm * 1e-3

    e_h = float(hub_material["youngs_modulus_mpa"]) * 1e6
    nu_h = float(hub_material["poisson_ratio"])
    e_s = float(shaft_material["youngs_modulus_mpa"]) * 1e6
    nu_s = float(shaft_material["poisson_ratio"])

    hub_geometry_factor = _hub_geometry_factor(d_m, D_m)
    shaft_geometry_factor = _shaft_geometry_factor(d_m, di_m)

    hub_coefficient = hub_geometry_factor + nu_h
    shaft_coefficient = (
        1.0 - nu_s
        if shaft_inner_diameter_mm <= 0.0
        else shaft_geometry_factor - nu_s
    )
    hub_term_m_per_pa = (d_m / e_h) * hub_coefficient
    shaft_term_m_per_pa = (d_m / e_s) * shaft_coefficient
    total_term_m_per_pa = hub_term_m_per_pa + shaft_term_m_per_pa

    return {
        "hub_geometry_factor": hub_geometry_factor,
        "shaft_geometry_factor": shaft_geometry_factor,
        "hub_coefficient": hub_coefficient,
        "shaft_coefficient": shaft_coefficient,
        "hub_term_m_per_pa": hub_term_m_per_pa,
        "shaft_term_m_per_pa": shaft_term_m_per_pa,
        "total_term_m_per_pa": total_term_m_per_pa,
        "total_term_mm_per_mpa": total_term_m_per_pa * 1e9,
    }


def _surface_result(
    location_label: str,
    radius_mm: float,
    radial_mpa: float,
    hoop_mpa: float,
    material: Dict[str, float | str] | None = None,
) -> Dict[str, float | str]:
    """Build a single surface-stress payload for UI and test consumption."""

    if abs(radial_mpa) < 1e-12:
        radial_mpa = 0.0
    if abs(hoop_mpa) < 1e-12:
        hoop_mpa = 0.0

    von_mises_mpa = math.sqrt(
        hoop_mpa**2 - hoop_mpa * radial_mpa + radial_mpa**2
    )
    if material is None:
        equivalent_mpa = von_mises_mpa
        safety_factor = float("inf")
        criterion = VON_MISES
    else:
        equivalent_mpa, safety_factor = _strength_safety_factor(
            radial_mpa, hoop_mpa, material
        )
        criterion = str(material.get("failure_criterion", VON_MISES))

    return {
        "location_label": location_label,
        "radius_mm": radius_mm,
        "radial_stress_mpa": radial_mpa,
        "hoop_stress_mpa": hoop_mpa,
        "von_mises_mpa": von_mises_mpa,
        "equivalent_stress_mpa": equivalent_mpa,
        "safety_factor": safety_factor,
        "failure_criterion": criterion,
    }


def _calculate_member_stresses_mpa(
    pressure_mpa: float,
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> Dict[str, Dict[str, Any]]:
    """Calculate member surface stresses and yield margins for the fit."""

    d = shaft_outer_diameter_mm
    D = hub_outer_diameter_mm
    di = shaft_inner_diameter_mm

    if pressure_mpa <= 0.0:
        zero_surface = _surface_result("Interface / outer surface", d / 2.0, 0.0, 0.0)
        hub_surfaces = {
            "inner_surface": _surface_result("Inner surface", d / 2.0, 0.0, 0.0),
            "outer_surface": _surface_result("Outer surface", D / 2.0, 0.0, 0.0),
        }
        shaft_surfaces: Dict[str, Dict[str, float | str] | None] = {
            "outer_surface": zero_surface,
            "inner_surface": None
            if di <= 0.0
            else _surface_result("Inner bore", di / 2.0, 0.0, 0.0),
        }
        return {
            "hub": {
                "surface_order": ["inner_surface", "outer_surface"],
                "surfaces": hub_surfaces,
                "max_von_mises_mpa": 0.0,
                "yield_safety_factor": float("inf"),
            },
            "shaft": {
                "member_type": "solid" if di <= 0.0 else "hollow",
                "surface_order": (
                    ["outer_surface"]
                    if di <= 0.0
                    else ["outer_surface", "inner_surface"]
                ),
                "surfaces": shaft_surfaces,
                "max_von_mises_mpa": 0.0,
                "yield_safety_factor": float("inf"),
            },
        }

    d_m = d * 1e-3
    D_m = D * 1e-3
    di_m = di * 1e-3

    hub_inner = _surface_result(
        "Inner surface",
        d / 2.0,
        -pressure_mpa,
        pressure_mpa * _hub_geometry_factor(d_m, D_m),
        hub_material,
    )
    hub_outer = _surface_result(
        "Outer surface",
        D / 2.0,
        0.0,
        2.0 * pressure_mpa * d_m**2 / (D_m**2 - d_m**2),
        hub_material,
    )
    hub_surface_list = [hub_inner, hub_outer]

    if di_m <= 0.0:
        shaft_outer = _surface_result(
            "Outer surface",
            d / 2.0,
            -pressure_mpa,
            -pressure_mpa,
            shaft_material,
        )
        shaft_inner = None
        shaft_surface_list = [shaft_outer]
        shaft_order = ["outer_surface"]
        shaft_member_type = "solid"
    else:
        shaft_outer = _surface_result(
            "Outer surface",
            d / 2.0,
            -pressure_mpa,
            -pressure_mpa * _shaft_geometry_factor(d_m, di_m),
            shaft_material,
        )
        shaft_inner = _surface_result(
            "Inner bore",
            di / 2.0,
            0.0,
            -2.0 * pressure_mpa * d_m**2 / (d_m**2 - di_m**2),
            shaft_material,
        )
        shaft_surface_list = [shaft_outer, shaft_inner]
        shaft_order = ["outer_surface", "inner_surface"]
        shaft_member_type = "hollow"

    hub_max_vm = max(float(item["equivalent_stress_mpa"]) for item in hub_surface_list)
    shaft_max_vm = max(float(item["equivalent_stress_mpa"]) for item in shaft_surface_list)
    hub_sf = min(float(item["safety_factor"]) for item in hub_surface_list)
    shaft_sf = min(float(item["safety_factor"]) for item in shaft_surface_list)

    return {
        "hub": {
            "surface_order": ["inner_surface", "outer_surface"],
            "surfaces": {
                "inner_surface": hub_inner,
                "outer_surface": hub_outer,
            },
            "max_von_mises_mpa": hub_max_vm,
            "failure_criterion": str(hub_material.get("failure_criterion", VON_MISES)),
            "yield_safety_factor": hub_sf,
        },
        "shaft": {
            "member_type": shaft_member_type,
            "surface_order": shaft_order,
            "surfaces": {
                "outer_surface": shaft_outer,
                "inner_surface": shaft_inner,
            },
            "max_von_mises_mpa": shaft_max_vm,
            "failure_criterion": str(shaft_material.get("failure_criterion", VON_MISES)),
            "yield_safety_factor": shaft_sf,
        },
    }


def _generate_stress_distribution(
    pressure_mpa: float,
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    n_hub_points: int = 80,
    n_shaft_points: int = 60,
) -> Dict[str, Any]:
    """Generate radial stress-distribution data for hub and shaft plots."""

    r_fit_mm = shaft_outer_diameter_mm / 2.0
    r_hub_outer_mm = hub_outer_diameter_mm / 2.0
    r_shaft_inner_mm = shaft_inner_diameter_mm / 2.0

    hub_radii_mm = [
        r_fit_mm + i * (r_hub_outer_mm - r_fit_mm) / max(n_hub_points - 1, 1)
        for i in range(n_hub_points)
    ]
    hub_radial: List[float] = []
    hub_hoop: List[float] = []

    if pressure_mpa > 0.0:
        k_h = pressure_mpa * r_fit_mm**2 / (r_hub_outer_mm**2 - r_fit_mm**2)
        for radius_mm in hub_radii_mm:
            hub_radial.append(k_h * (1.0 - r_hub_outer_mm**2 / radius_mm**2))
            hub_hoop.append(k_h * (1.0 + r_hub_outer_mm**2 / radius_mm**2))
    else:
        hub_radial = [0.0 for _ in hub_radii_mm]
        hub_hoop = [0.0 for _ in hub_radii_mm]

    shaft_payload: Dict[str, Any] = {
        "member_type": "solid" if shaft_inner_diameter_mm <= 0.0 else "hollow",
        "radii_mm": [],
        "radial_stress_mpa": [],
        "hoop_stress_mpa": [],
    }
    if shaft_inner_diameter_mm > 0.0:
        shaft_radii_mm = [
            r_shaft_inner_mm
            + i * (r_fit_mm - r_shaft_inner_mm) / max(n_shaft_points - 1, 1)
            for i in range(n_shaft_points)
        ]
        shaft_radial: List[float] = []
        shaft_hoop: List[float] = []
        if pressure_mpa > 0.0:
            k_s = -pressure_mpa * r_fit_mm**2 / (r_fit_mm**2 - r_shaft_inner_mm**2)
            for radius_mm in shaft_radii_mm:
                shaft_radial.append(k_s * (1.0 - r_shaft_inner_mm**2 / radius_mm**2))
                shaft_hoop.append(k_s * (1.0 + r_shaft_inner_mm**2 / radius_mm**2))
        else:
            shaft_radial = [0.0 for _ in shaft_radii_mm]
            shaft_hoop = [0.0 for _ in shaft_radii_mm]
        shaft_payload = {
            "member_type": "hollow",
            "radii_mm": shaft_radii_mm,
            "radial_stress_mpa": shaft_radial,
            "hoop_stress_mpa": shaft_hoop,
        }

    return {
        "hub": {
            "radii_mm": hub_radii_mm,
            "radial_stress_mpa": hub_radial,
            "hoop_stress_mpa": hub_hoop,
        },
        "shaft": shaft_payload,
    }


def _calculate_slip_capacities(
    pressure_mpa: float,
    shaft_outer_diameter_mm: float,
    fit_length_mm: float,
    friction_coefficient: float,
    applied_torque_nm: float,
    applied_axial_force_n: float,
) -> Dict[str, float]:
    """Calculate torque and axial slip capacities under uniform pressure."""

    d = shaft_outer_diameter_mm * 1e-3
    tangential_force_n = (
        2.0 * abs(applied_torque_nm) / d if abs(applied_torque_nm) > 0.0 else 0.0
    )
    equivalent_force_n = math.hypot(tangential_force_n, abs(applied_axial_force_n))

    if pressure_mpa <= 0.0 or friction_coefficient <= 0.0:
        return {
            "normal_force_n": 0.0,
            "torque_capacity_nm": 0.0,
            "axial_capacity_n": 0.0,
            "axial_capacity_kn": 0.0,
            "tangential_force_n": tangential_force_n,
            "equivalent_force_n": equivalent_force_n,
            "friction_capacity_n": 0.0,
            "torque_slip_safety_factor": 0.0 if abs(applied_torque_nm) > 0.0 else float("inf"),
            "axial_slip_safety_factor": 0.0 if abs(applied_axial_force_n) > 0.0 else float("inf"),
            "combined_slip_safety_factor": 0.0 if equivalent_force_n > 0.0 else float("inf"),
            "torque_utilization_percent": float("inf") if abs(applied_torque_nm) > 0.0 else 0.0,
            "axial_utilization_percent": float("inf") if abs(applied_axial_force_n) > 0.0 else 0.0,
        }

    pressure_pa = pressure_mpa * 1e6
    L = fit_length_mm * 1e-3
    contact_area = math.pi * d * L
    normal_force = pressure_pa * contact_area
    torque_capacity = normal_force * friction_coefficient * (d / 2.0)
    axial_capacity = normal_force * friction_coefficient

    torque_sf = (
        torque_capacity / abs(applied_torque_nm)
        if abs(applied_torque_nm) > 0.0
        else float("inf")
    )
    axial_sf = (
        axial_capacity / abs(applied_axial_force_n)
        if abs(applied_axial_force_n) > 0.0
        else float("inf")
    )
    # Torque and axial load share one friction budget, so simultaneous duty
    # has to be checked against the resultant traction, not each axis alone.
    combined_sf = (
        axial_capacity / equivalent_force_n
        if equivalent_force_n > 0.0
        else float("inf")
    )

    return {
        "normal_force_n": normal_force,
        "torque_capacity_nm": torque_capacity,
        "axial_capacity_n": axial_capacity,
        "axial_capacity_kn": axial_capacity / 1000.0,
        "tangential_force_n": tangential_force_n,
        "equivalent_force_n": equivalent_force_n,
        "friction_capacity_n": axial_capacity,
        "torque_slip_safety_factor": torque_sf,
        "axial_slip_safety_factor": axial_sf,
        "combined_slip_safety_factor": combined_sf,
        "torque_utilization_percent": (
            100.0 * abs(applied_torque_nm) / torque_capacity
            if torque_capacity > 0.0 and abs(applied_torque_nm) > 0.0
            else 0.0
        ),
        "axial_utilization_percent": (
            100.0 * abs(applied_axial_force_n) / axial_capacity
            if axial_capacity > 0.0 and abs(applied_axial_force_n) > 0.0
            else 0.0
        ),
    }


def _thermal_adjusted_interference_mm(
    interference_mm: float,
    shaft_outer_diameter_mm: float,
    reference_temperature_c: float,
    operating_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> float:
    """Adjust diametral interference for differential free thermal expansion."""

    delta_t = operating_temperature_c - reference_temperature_c
    alpha_h = float(hub_material["thermal_expansion_e6_per_c"]) * 1e-6
    alpha_s = float(shaft_material["thermal_expansion_e6_per_c"]) * 1e-6
    thermal_relief = shaft_outer_diameter_mm * (alpha_h - alpha_s) * delta_t
    return interference_mm - thermal_relief


def _fit_loss_temperature_c(
    interference_mm: float,
    shaft_outer_diameter_mm: float,
    reference_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> float | None:
    """Return the temperature where interference falls to zero, if finite."""

    delta_alpha = (
        float(hub_material["thermal_expansion_e6_per_c"])
        - float(shaft_material["thermal_expansion_e6_per_c"])
    ) * 1e-6
    if abs(delta_alpha) < 1e-14:
        return None

    return reference_temperature_c + (
        interference_mm / (shaft_outer_diameter_mm * delta_alpha)
    )


def _thermal_assembly_plan(
    maximum_interference_mm: float,
    slip_clearance_mm: float,
    shaft_outer_diameter_mm: float,
    fit_length_mm: float,
    friction_coefficient: float,
    compliance_mm_per_mpa: float,
    smoothing_loss_mm: float,
    press_friction_factor: float,
    reference_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    hub_assembly_temperature_c: float | None = None,
    shaft_assembly_temperature_c: float | None = None,
    hub_max_assembly_temp_c: float | None = None,
    shaft_min_assembly_temp_c: float | None = None,
    maximum_operating_temperature_c: float | None = None,
    governing_interference_label: str = "maximum interference",
) -> Dict[str, Any]:
    """Cost the ways of getting the joint together.

    Two questions, both answered here. What temperature would let the parts
    slip together with no press at all, and what does the temperature you
    actually plan to use leave you to push through. Heating the hub 100 deg C
    can take most of the press force away without clearing the fit entirely,
    which is the usual compromise on a shop floor.
    """

    required_total_change_mm = max(0.0, maximum_interference_mm) + slip_clearance_mm
    alpha_h = float(hub_material["thermal_expansion_e6_per_c"]) * 1e-6
    alpha_s = float(shaft_material["thermal_expansion_e6_per_c"]) * 1e-6
    d = shaft_outer_diameter_mm

    hub_temperature = (
        reference_temperature_c + required_total_change_mm / (alpha_h * d)
        if alpha_h > 0.0
        else None
    )
    shaft_temperature = (
        reference_temperature_c - required_total_change_mm / (alpha_s * d)
        if alpha_s > 0.0
        else None
    )
    combined_delta = (
        required_total_change_mm / ((alpha_h + alpha_s) * d)
        if alpha_h + alpha_s > 0.0
        else None
    )
    combined_hub = (
        None if combined_delta is None else reference_temperature_c + combined_delta
    )
    combined_shaft = (
        None if combined_delta is None else reference_temperature_c - combined_delta
    )

    # What the temperatures you actually plan to use leave behind. Growth is
    # signed: heating the hub opens the joint, heating the shaft closes it.
    planned_hub_c = (
        reference_temperature_c
        if hub_assembly_temperature_c is None
        else hub_assembly_temperature_c
    )
    planned_shaft_c = (
        reference_temperature_c
        if shaft_assembly_temperature_c is None
        else shaft_assembly_temperature_c
    )
    hub_growth_mm = d * alpha_h * (planned_hub_c - reference_temperature_c)
    shaft_growth_mm = d * alpha_s * (planned_shaft_c - reference_temperature_c)
    opening_mm = hub_growth_mm - shaft_growth_mm

    remaining_interference_mm = max(0.0, maximum_interference_mm - opening_mm)
    residual_clearance_mm = max(0.0, opening_mm - maximum_interference_mm)
    slips_together = opening_mm >= maximum_interference_mm

    # Sliding one part into the other galls and ploughs, so insertion friction
    # runs higher than the settled slip value. DIN 7190 treats the two
    # separately; the factor is exposed so the assumption stays visible.
    press_friction = friction_coefficient * press_friction_factor

    def press_force_n(interference_mm: float) -> tuple[float, float]:
        """Return contact pressure and axial force to push that interference on.

        The pressure is the one the joint actually develops, so it uses the
        interference left after roughness smoothing, exactly like every other
        pressure this module reports. Friction over the whole contact length
        turns it into a force.
        """

        effective_mm = interference_mm - smoothing_loss_mm
        if effective_mm <= 0.0 or compliance_mm_per_mpa <= 0.0:
            return 0.0, 0.0
        pressure_mpa = effective_mm / compliance_mm_per_mpa
        force = (
            press_friction
            * pressure_mpa
            * 1e6
            * math.pi
            * (shaft_outer_diameter_mm / 1000.0)
            * (fit_length_mm / 1000.0)
        )
        return pressure_mpa, force

    ambient_pressure_mpa, ambient_force_n = press_force_n(maximum_interference_mm)
    planned_pressure_mpa, planned_force_n = press_force_n(remaining_interference_mm)
    force_reduction_n = ambient_force_n - planned_force_n
    force_reduction_percent = (
        100.0 * force_reduction_n / ambient_force_n if ambient_force_n > 0.0 else 0.0
    )

    planned = {
        "hub_temperature_c": planned_hub_c,
        "shaft_temperature_c": planned_shaft_c,
        "is_ambient": (
            planned_hub_c == reference_temperature_c
            and planned_shaft_c == reference_temperature_c
        ),
        "hub_growth_mm": hub_growth_mm,
        "shaft_growth_mm": shaft_growth_mm,
        "opening_mm": opening_mm,
        "remaining_interference_mm": remaining_interference_mm,
        "residual_clearance_mm": residual_clearance_mm,
        "slips_together": slips_together,
        "press_friction_coefficient": press_friction,
        "press_pressure_mpa": planned_pressure_mpa,
        "press_force_n": planned_force_n,
        "press_force_kn": planned_force_n / 1000.0,
        "ambient_press_pressure_mpa": ambient_pressure_mpa,
        "ambient_press_force_n": ambient_force_n,
        "ambient_press_force_kn": ambient_force_n / 1000.0,
        "force_reduction_n": force_reduction_n,
        "force_reduction_kn": force_reduction_n / 1000.0,
        "force_reduction_percent": force_reduction_percent,
    }

    hub_route = _heating_route(hub_temperature, reference_temperature_c)
    shaft_route = _cooling_route(shaft_temperature)
    combined_hub_route = _heating_route(combined_hub, reference_temperature_c)
    combined_shaft_route = _cooling_route(combined_shaft)

    def within_heating_limit(temperature_c: float | None) -> bool:
        if hub_max_assembly_temp_c is None or temperature_c is None:
            return True
        return temperature_c <= hub_max_assembly_temp_c

    def within_cooling_limit(temperature_c: float | None) -> bool:
        if shaft_min_assembly_temp_c is None or temperature_c is None:
            return True
        return temperature_c >= shaft_min_assembly_temp_c

    hub_ok = bool(hub_route["feasible"]) and within_heating_limit(hub_temperature)
    shaft_ok = bool(shaft_route["feasible"]) and within_cooling_limit(shaft_temperature)
    combined_ok = (
        bool(combined_hub_route["feasible"])
        and bool(combined_shaft_route["feasible"])
        and within_heating_limit(combined_hub)
        and within_cooling_limit(combined_shaft)
    )

    # Heating the hub alone is the cheapest thing a shop can do, so it wins
    # when it works. Chilling alone comes next, then both together.
    if hub_ok:
        recommended_route = "heat the hub"
    elif shaft_ok:
        recommended_route = "chill the shaft"
    elif combined_ok:
        recommended_route = "heat the hub and chill the shaft"
    else:
        recommended_route = "press cold, no thermal route works"

    warnings: List[str] = []
    status = "acceptable"

    if not (hub_ok or shaft_ok or combined_ok):
        status = "marginal"
        warnings.append(
            "No thermal assembly route opens the maximum interference. Press the "
            "joint cold, raise the equipment limits, or reduce the maximum "
            "interference."
        )
    else:
        if hub_temperature is not None and not hub_route["feasible"]:
            warnings.append(
                "Hub-only heating is above normal shop practice. Verify temper, "
                "coatings, and handling, or chill the shaft as well."
            )
        if shaft_temperature is not None and not shaft_route["feasible"]:
            warnings.append(
                "Shaft-only chilling is colder than liquid nitrogen. Heat the hub "
                "instead, or do both together."
            )
        if hub_temperature is not None and not within_heating_limit(hub_temperature):
            warnings.append(
                f"Hub-only heating needs {hub_temperature:.0f} deg C, above the "
                f"{hub_max_assembly_temp_c:.0f} deg C limit you entered."
            )
        if shaft_temperature is not None and not within_cooling_limit(shaft_temperature):
            warnings.append(
                f"Shaft-only chilling needs {shaft_temperature:.0f} deg C, below the "
                f"{shaft_min_assembly_temp_c:.0f} deg C limit you entered."
            )

    if not planned["is_ambient"]:
        planned_hub_route = _heating_route(planned_hub_c, reference_temperature_c)
        planned_shaft_route = _cooling_route(planned_shaft_c)
        if not planned_hub_route["feasible"]:
            warnings.append(
                f"The planned hub temperature of {planned_hub_c:.0f} deg C is above "
                "normal shop practice. Verify temper, coatings, and handling."
            )
        if not planned_shaft_route["feasible"]:
            warnings.append(
                f"The planned shaft temperature of {planned_shaft_c:.0f} deg C is "
                "colder than liquid nitrogen."
            )

    if (
        maximum_operating_temperature_c is not None
        and hub_temperature is not None
        and hub_temperature <= maximum_operating_temperature_c
    ):
        warnings.append(
            "The hub assembly temperature is at or below the maximum service "
            "temperature. A thermal gradient that heats the hub faster than the "
            "shaft can unseat the joint in service."
        )

    return {
        "governing_interference_mm": maximum_interference_mm,
        "governing_interference_label": governing_interference_label,
        "slip_clearance_mm": slip_clearance_mm,
        "required_total_diameter_change_mm": required_total_change_mm,
        "planned": planned,
        "hub_heating_temperature_c": hub_temperature,
        "shaft_cooling_temperature_c": shaft_temperature,
        "combined_hub_temperature_c": combined_hub,
        "combined_shaft_temperature_c": combined_shaft,
        "combined_delta_t_c": combined_delta,
        "hub_heating_route": hub_route["route"],
        "hub_heating_feasible": hub_ok,
        "shaft_cooling_route": shaft_route["route"],
        "shaft_cooling_feasible": shaft_ok,
        "combined_route_feasible": combined_ok,
        # Physical practicality on its own, before the equipment limits are
        # applied, so a display can tell "your oven is too small" apart from
        # "no oven on earth is hot enough".
        "hub_heating_practical": bool(hub_route["feasible"]),
        "shaft_cooling_practical": bool(shaft_route["feasible"]),
        "combined_practical": bool(
            combined_hub_route["feasible"] and combined_shaft_route["feasible"]
        ),
        "combined_route": "both together",
        "hub_max_assembly_temp_c": hub_max_assembly_temp_c,
        "shaft_min_assembly_temp_c": shaft_min_assembly_temp_c,
        "recommended_route": recommended_route,
        "status": status,
        "warnings": warnings,
    }


def _evaluate_case(
    interference_mm: float,
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    friction_coefficient: float,
    applied_torque_nm: float,
    applied_axial_force_n: float,
    required_slip_sf: float,
    required_yield_sf: float,
    case_name: str,
    state_name: str,
    smoothing_loss_mm: float = 0.0,
    effective_fit_length_mm: float | None = None,
    speed_rpm: float = 0.0,
) -> Dict[str, Any]:
    """Evaluate one fit state at a specified interference."""

    warnings: List[str] = []
    if effective_fit_length_mm is None:
        effective_fit_length_mm = fit_length_mm
    # Roughness peaks flatten at assembly, so only the interference left after
    # smoothing ever turns into contact pressure.
    effective_interference_mm = max(0.0, interference_mm - smoothing_loss_mm)
    compliance = _calculate_compliance_data(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )
    pressure_mpa = _calculate_interface_pressure_mpa(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        interference_mm=effective_interference_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )
    stresses = _calculate_member_stresses_mpa(
        pressure_mpa=pressure_mpa,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )
    capacities = _calculate_slip_capacities(
        pressure_mpa=pressure_mpa,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        fit_length_mm=effective_fit_length_mm,
        friction_coefficient=friction_coefficient,
        applied_torque_nm=applied_torque_nm,
        applied_axial_force_n=applied_axial_force_n,
    )
    distributions = _generate_stress_distribution(
        pressure_mpa=pressure_mpa,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
    )

    # Rotation adds its own hoop stress on top of the fit pressure, so a
    # spinning state has to be judged on the superposed field, not on the
    # pressure stresses alone.
    rotating_state = None
    if speed_rpm > 0.0:
        rotating_state = _combined_rotating_fit_stress(
            pressure_mpa=pressure_mpa,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_material,
            hub_material=hub_material,
            speed_rpm=speed_rpm,
        )
        for member in ("hub", "shaft"):
            stresses[member]["max_von_mises_mpa"] = float(
                rotating_state[member]["max_von_mises_mpa"]
            )
            stresses[member]["yield_safety_factor"] = float(
                rotating_state[member]["yield_safety_factor"]
            )
            stresses[member]["critical_radius_mm"] = float(
                rotating_state[member]["critical_radius_mm"]
            )

    fit_retained = pressure_mpa > 0.0 and interference_mm > 0.0
    hub_sf = float(stresses["hub"]["yield_safety_factor"])
    shaft_sf = float(stresses["shaft"]["yield_safety_factor"])
    torque_sf = float(capacities["torque_slip_safety_factor"])
    axial_sf = float(capacities["axial_slip_safety_factor"])
    combined_sf = float(capacities["combined_slip_safety_factor"])
    has_duty = abs(applied_torque_nm) > 0.0 or abs(applied_axial_force_n) > 0.0
    min_yield_sf = min(hub_sf, shaft_sf)
    hub_inner = stresses["hub"]["surfaces"]["inner_surface"]
    hub_outer = stresses["hub"]["surfaces"]["outer_surface"]
    shaft_outer = stresses["shaft"]["surfaces"]["outer_surface"]
    shaft_inner = stresses["shaft"]["surfaces"]["inner_surface"]

    check_values: List[float] = [min_yield_sf]
    if has_duty:
        check_values.append(combined_sf)
    min_check_sf = min(check_values) if check_values else float("inf")

    if not fit_retained:
        status = "unacceptable"
        warnings.append("Interference is zero or negative in this state, so the fit no longer retains contact pressure.")
    elif min_yield_sf < 1.0 or (has_duty and combined_sf < 1.0):
        status = "unacceptable"
    elif min_yield_sf < required_yield_sf or (
        has_duty and combined_sf < required_slip_sf
    ):
        status = "marginal"
    else:
        status = "acceptable"

    if hub_sf < required_yield_sf:
        warnings.append("Hub strength safety factor is below the requested threshold.")
    if shaft_sf < required_yield_sf:
        warnings.append("Shaft strength safety factor is below the requested threshold.")
    if has_duty and combined_sf < required_slip_sf:
        if abs(applied_torque_nm) > 0.0 and abs(applied_axial_force_n) > 0.0:
            warnings.append(
                "Combined torque and axial slip safety factor is below the requested "
                "threshold. Both loads draw on the same friction budget."
            )
        else:
            warnings.append("Slip safety factor is below the requested threshold.")

    return {
        "case_name": case_name,
        "state_name": state_name,
        "interference_mm": interference_mm,
        "effective_interference_mm": effective_interference_mm,
        "smoothing_loss_mm": smoothing_loss_mm,
        "effective_fit_length_mm": effective_fit_length_mm,
        "fit_retained": fit_retained,
        "pressure_mpa": pressure_mpa,
        "members": stresses,
        "stress_distribution": distributions,
        "compliance": compliance,
        "hub_radial_stress_mpa": float(hub_inner["radial_stress_mpa"]),
        "hub_hoop_stress_mpa": float(hub_inner["hoop_stress_mpa"]),
        "hub_von_mises_mpa": float(hub_inner["von_mises_mpa"]),
        "hub_outer_radial_stress_mpa": float(hub_outer["radial_stress_mpa"]),
        "hub_outer_hoop_stress_mpa": float(hub_outer["hoop_stress_mpa"]),
        "hub_outer_von_mises_mpa": float(hub_outer["von_mises_mpa"]),
        "hub_max_von_mises_mpa": float(stresses["hub"]["max_von_mises_mpa"]),
        "hub_yield_safety_factor": hub_sf,
        "shaft_radial_stress_mpa": float(shaft_outer["radial_stress_mpa"]),
        "shaft_hoop_stress_mpa": float(shaft_outer["hoop_stress_mpa"]),
        "shaft_von_mises_mpa": float(shaft_outer["von_mises_mpa"]),
        "shaft_inner_radial_stress_mpa": (
            None if shaft_inner is None else float(shaft_inner["radial_stress_mpa"])
        ),
        "shaft_inner_hoop_stress_mpa": (
            None if shaft_inner is None else float(shaft_inner["hoop_stress_mpa"])
        ),
        "shaft_inner_von_mises_mpa": (
            None if shaft_inner is None else float(shaft_inner["von_mises_mpa"])
        ),
        "shaft_max_von_mises_mpa": float(stresses["shaft"]["max_von_mises_mpa"]),
        "shaft_yield_safety_factor": shaft_sf,
        "yield_safety_factor": min_yield_sf,
        "normal_force_n": float(capacities["normal_force_n"]),
        "torque_capacity_nm": float(capacities["torque_capacity_nm"]),
        "axial_capacity_n": float(capacities["axial_capacity_n"]),
        "axial_capacity_kn": float(capacities["axial_capacity_kn"]),
        "torque_slip_safety_factor": torque_sf,
        "axial_slip_safety_factor": axial_sf,
        "combined_slip_safety_factor": combined_sf,
        "equivalent_force_n": float(capacities["equivalent_force_n"]),
        "torque_utilization_percent": float(capacities["torque_utilization_percent"]),
        "axial_utilization_percent": float(capacities["axial_utilization_percent"]),
        "speed_rpm": speed_rpm,
        "status": status,
        "warnings": warnings,
        "governing_safety_factor": min_check_sf,
    }


def _generate_interference_sweep(
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    nominal_interference_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    friction_coefficient: float,
    reference_temperature_c: float,
    operating_temperature_c: float,
    sweep_min_interference_mm: float,
    sweep_max_interference_mm: float,
    n_sweep_points: int,
) -> Dict[str, List[float] | float]:
    """Generate plot-ready interference sweep data."""

    if n_sweep_points < 5:
        raise ValueError("n_sweep_points must be at least 5.")

    span_max = max(sweep_max_interference_mm, nominal_interference_mm * 1.4, 0.01)
    span_min = min(sweep_min_interference_mm, nominal_interference_mm * 0.4, nominal_interference_mm)
    if span_max <= span_min:
        span_max = span_min + max(0.01, nominal_interference_mm)

    interference_values = [
        span_min + i * (span_max - span_min) / (n_sweep_points - 1)
        for i in range(n_sweep_points)
    ]

    reference_pressure: List[float] = []
    operating_pressure: List[float] = []
    torque_capacity: List[float] = []
    axial_capacity_kn: List[float] = []
    hub_vm: List[float] = []
    shaft_vm: List[float] = []

    for interference_mm in interference_values:
        p_ref = _calculate_interface_pressure_mpa(
            shaft_outer_diameter_mm,
            hub_outer_diameter_mm,
            shaft_inner_diameter_mm,
            interference_mm,
            shaft_material,
            hub_material,
        )
        interference_op = _thermal_adjusted_interference_mm(
            interference_mm,
            shaft_outer_diameter_mm,
            reference_temperature_c,
            operating_temperature_c,
            shaft_material,
            hub_material,
        )
        p_op = _calculate_interface_pressure_mpa(
            shaft_outer_diameter_mm,
            hub_outer_diameter_mm,
            shaft_inner_diameter_mm,
            max(0.0, interference_op),
            shaft_material,
            hub_material,
        )
        stresses = _calculate_member_stresses_mpa(
            pressure_mpa=p_ref,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            shaft_material=shaft_material,
            hub_material=hub_material,
        )
        capacities = _calculate_slip_capacities(
            pressure_mpa=p_op,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            friction_coefficient=friction_coefficient,
            applied_torque_nm=0.0,
            applied_axial_force_n=0.0,
        )
        reference_pressure.append(p_ref)
        operating_pressure.append(p_op)
        torque_capacity.append(float(capacities["torque_capacity_nm"]))
        axial_capacity_kn.append(float(capacities["axial_capacity_kn"]))
        hub_vm.append(float(stresses["hub"]["max_von_mises_mpa"]))
        shaft_vm.append(float(stresses["shaft"]["max_von_mises_mpa"]))

    return {
        "interference_mm": interference_values,
        "reference_pressure_mpa": reference_pressure,
        "operating_pressure_mpa": operating_pressure,
        "torque_capacity_nm": torque_capacity,
        "axial_capacity_kn": axial_capacity_kn,
        "hub_von_mises_mpa": hub_vm,
        "shaft_von_mises_mpa": shaft_vm,
        "nominal_interference_mm": nominal_interference_mm,
    }


def _generate_temperature_sweep(
    nominal_interference_mm: float,
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    reference_temperature_c: float,
    operating_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    n_points: int = 61,
) -> Dict[str, List[float] | float | None]:
    """Generate plot-ready operating temperature sweep data."""

    fit_loss_temperature = _fit_loss_temperature_c(
        interference_mm=nominal_interference_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        reference_temperature_c=reference_temperature_c,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )

    temp_candidates = [reference_temperature_c - 80.0, operating_temperature_c - 20.0]
    temp_high_candidates = [reference_temperature_c + 140.0, operating_temperature_c + 20.0]
    if fit_loss_temperature is not None:
        temp_candidates.append(fit_loss_temperature - 25.0)
        temp_high_candidates.append(fit_loss_temperature + 25.0)
    t_min = min(temp_candidates)
    t_max = max(temp_high_candidates)
    if t_max <= t_min:
        t_max = t_min + 50.0

    temperature_values = [
        t_min + i * (t_max - t_min) / (n_points - 1)
        for i in range(n_points)
    ]
    operating_interference: List[float] = []
    operating_pressure: List[float] = []

    for temperature_c in temperature_values:
        interference_op = _thermal_adjusted_interference_mm(
            interference_mm=nominal_interference_mm,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            reference_temperature_c=reference_temperature_c,
            operating_temperature_c=temperature_c,
            shaft_material=shaft_material,
            hub_material=hub_material,
        )
        pressure_op = _calculate_interface_pressure_mpa(
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            interference_mm=max(0.0, interference_op),
            shaft_material=shaft_material,
            hub_material=hub_material,
        )
        operating_interference.append(interference_op)
        operating_pressure.append(pressure_op)

    return {
        "temperature_c": temperature_values,
        "operating_interference_mm": operating_interference,
        "operating_pressure_mpa": operating_pressure,
        "fit_loss_temperature_c": fit_loss_temperature,
    }


def analyze_interference_fit(
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    shaft_inner_diameter_mm: float = 0.0,
    interference_nominal_mm: float = 0.03,
    interference_min_mm: float | None = None,
    interference_max_mm: float | None = None,
    shaft_material: str = "steel",
    hub_material: str = "steel",
    shaft_youngs_modulus_mpa: float = 200000.0,
    shaft_poisson_ratio: float = 0.30,
    shaft_yield_strength_mpa: float = 450.0,
    shaft_thermal_expansion_e6_per_c: float = 12.0,
    hub_youngs_modulus_mpa: float = 200000.0,
    hub_poisson_ratio: float = 0.30,
    hub_yield_strength_mpa: float = 350.0,
    hub_thermal_expansion_e6_per_c: float = 12.0,
    friction_coefficient: float = 0.15,
    reference_temperature_c: float = 20.0,
    operating_temperature_c: float = 20.0,
    operating_speed_rpm: float = 0.0,
    assembly_clearance_mm: float = 0.01,
    hub_assembly_temperature_c: float | None = None,
    shaft_assembly_temperature_c: float | None = None,
    press_friction_factor: float = 1.5,
    applied_torque_nm: float = 0.0,
    applied_axial_force_n: float = 0.0,
    required_slip_sf: float = 1.5,
    required_yield_sf: float = 1.2,
    hub_max_assembly_temp_c: float | None = None,
    shaft_min_assembly_temp_c: float | None = None,
    shaft_roughness_rz_um: float = 0.0,
    hub_roughness_rz_um: float = 0.0,
    length_credit_ratio: float = 1.5,
    shaft_compressive_strength_mpa: float = 0.0,
    shaft_failure_criterion: str = VON_MISES,
    hub_compressive_strength_mpa: float = 0.0,
    hub_failure_criterion: str = VON_MISES,
    sweep_min_interference_mm: float = 0.0,
    sweep_max_interference_mm: float = 0.08,
    n_sweep_points: int = 81,
) -> Dict[str, Any]:
    r"""
    Analyze a cylindrical press fit / shrink fit between a shaft and a hub.

    This function evaluates elastic interference-fit pressure, Lamé stresses,
    slip capacity, operating-temperature interference loss, and thermal
    assembly temperatures for a straight cylindrical shaft-hub joint.

    The pressure model follows the classical Shigley-style thick-cylinder
    interference-fit treatment in which diametral interference is the product
    of interface pressure, fit diameter, and the combined radial compliances of
    the hub and shaft.

    ---Parameters---
    shaft_outer_diameter_mm : float
        Shaft outside diameter at the fit, in millimeters.
    hub_outer_diameter_mm : float
        Hub outside diameter, in millimeters. Must exceed the shaft diameter.
    fit_length_mm : float
        Axial engagement length of the fit, in millimeters.
    shaft_inner_diameter_mm : float
        Shaft inside diameter, in millimeters. Use 0 for a solid shaft.
    interference_nominal_mm : float
        Nominal diametral interference at the reference temperature, in mm.
    interference_min_mm : float
        Minimum diametral interference, in mm. If omitted, nominal is used.
    interference_max_mm : float
        Maximum diametral interference, in mm. If omitted, nominal is used.
    shaft_material : str
        Shaft material preset key, or `custom` to use the explicit shaft
        material property inputs.
    hub_material : str
        Hub material preset key, or `custom` to use the explicit hub material
        property inputs.
    shaft_youngs_modulus_mpa : float
        Custom shaft Young's modulus, in MPa, used when `shaft_material` is
        `custom`.
    shaft_poisson_ratio : float
        Custom shaft Poisson ratio, used when `shaft_material` is `custom`.
    shaft_yield_strength_mpa : float
        Custom shaft yield strength, in MPa, used when `shaft_material` is
        `custom`.
    shaft_thermal_expansion_e6_per_c : float
        Custom shaft thermal expansion coefficient, in microstrain per degree C,
        used when `shaft_material` is `custom`.
    hub_youngs_modulus_mpa : float
        Custom hub Young's modulus, in MPa, used when `hub_material` is
        `custom`.
    hub_poisson_ratio : float
        Custom hub Poisson ratio, used when `hub_material` is `custom`.
    hub_yield_strength_mpa : float
        Custom hub yield strength, in MPa, used when `hub_material` is
        `custom`.
    hub_thermal_expansion_e6_per_c : float
        Custom hub thermal expansion coefficient, in microstrain per degree C,
        used when `hub_material` is `custom`.
    friction_coefficient : float
        Friction coefficient used for slip-capacity calculations.
    reference_temperature_c : float
        Reference temperature at which the nominal interference is defined.
    operating_temperature_c : float
        Bulk operating temperature used for differential thermal expansion.
    operating_speed_rpm : float
        Common shaft and hub speed at the operating condition, in rev/min.
        Centrifugal growth opens the fit, and rotating hoop stress is
        superposed on the contact-pressure stresses for the operating check.
    assembly_clearance_mm : float
        Diametral slip clearance wanted when the parts go together, in mm. The
        thermal assembly plan has to open the maximum interference plus this.
    applied_torque_nm : float
        Applied service torque, in N·m, for torque slip safety factor checks.
    applied_axial_force_n : float
        Applied axial service load, in N, for axial slip safety factor checks.
    required_slip_sf : float
        Required slip safety factor for torque and axial load checks.
    required_yield_sf : float
        Required yield safety factor for shaft and hub stress checks.
    hub_assembly_temperature_c : float
        Temperature you plan to heat the hub to for assembly, in deg C.
        Defaults to the reference temperature, meaning no heating. Sets how
        much of the press force the plan removes.
    shaft_assembly_temperature_c : float
        Temperature you plan to chill the shaft to for assembly, in deg C.
        Defaults to the reference temperature, meaning no chilling.
    hub_max_assembly_temp_c : float
        Hottest the hub can be taken to, in deg C. Leave unset for no limit.
        Constrains which route the tool recommends.
    shaft_min_assembly_temp_c : float
        Coldest the shaft can be taken to, in deg C. Leave unset for no limit.
    press_friction_factor : float
        Multiplier on the friction coefficient for pressing the joint together.
        Sliding one part into the other galls, so insertion friction runs above
        the settled slip value. DIN 7190 treats the two separately.
    shaft_roughness_rz_um : float
        Shaft surface roughness Rz, in micrometres. Asperities flatten during
        assembly, so this interference never makes contact pressure.
    hub_roughness_rz_um : float
        Hub bore surface roughness Rz, in micrometres.
    length_credit_ratio : float
        Maximum length-to-diameter ratio credited with carrying load. Set to
        zero to credit the full contact length.
    shaft_compressive_strength_mpa : float
        Custom shaft compressive strength, in MPa, for the brittle criterion.
    shaft_failure_criterion : str
        `von_mises` for a ductile shaft or `brittle` for Coulomb-Mohr.
    hub_compressive_strength_mpa : float
        Custom hub compressive strength, in MPa, for the brittle criterion.
    hub_failure_criterion : str
        `von_mises` for a ductile hub or `brittle` for Coulomb-Mohr.
    sweep_min_interference_mm : float
        Lower bound for the interference sensitivity sweep, in mm.
    sweep_max_interference_mm : float
        Upper bound for the interference sensitivity sweep, in mm.
    n_sweep_points : float
        Number of points in the interference sensitivity sweep.

    ---Returns---
    reference_case : dict
        Nominal reference-temperature case with pressure, stresses, and capacity.
    operating_case : dict
        Nominal operating-temperature case with pressure, stresses, and capacity.
    nominal_case : dict
        Nominal interference results for both reference and operating states.
    minimum_case : dict
        Minimum interference results for both reference and operating states.
    maximum_case : dict
        Maximum interference results for both reference and operating states.
    range_cases : dict
        Dictionary of minimum, nominal, and maximum fit cases.
    assembly : dict
        Hub heating, shaft chilling, and combined temperatures that open the
        maximum interference, each with its route and whether it fits inside
        the stated equipment limits, plus the recommended route.
    compliance : dict
        Shigley-style geometry and compliance factors for the nominal fit.
    geometry : dict
        Key geometric quantities used by the UI and visualizations.
    state_temperatures_c : dict
        Reference, assembly, and operating temperatures used for the analysis.
    sweep_data : dict
        Plot-ready interference and temperature sweep arrays.
    status : str
        Overall assessment: acceptable, marginal, or unacceptable.
    governing_mode : str
        Governing limiting condition for the overall status.
    warnings : list
        Aggregate warning messages from the analysis.
    recommendations : list
        Action-oriented suggestions derived from the governing checks.
    shaft_material_name : str
        Resolved shaft material display name.
    hub_material_name : str
        Resolved hub material display name.
    fit_loss_temperature_c : float
        Temperature where nominal operating interference becomes zero, if finite.
    minimum_operating_pressure_mpa : float
        Lowest operating pressure across the min/nom/max interference cases.
    maximum_reference_pressure_mpa : float
        Highest reference pressure across the min/nom/max interference cases.
    minimum_yield_safety_factor : float
        Lowest shaft-or-hub yield safety factor across all states.
    minimum_torque_slip_safety_factor : float
        Lowest torque slip safety factor across operating states.
    minimum_axial_slip_safety_factor : float
        Lowest axial slip safety factor across operating states.
    subst_interface_pressure_mpa : str
        Substituted equation string for nominal reference interface pressure.
    subst_operating_interference_mm : str
        Substituted equation string for nominal operating interference.
    subst_torque_capacity_nm : str
        Substituted equation string for nominal operating torque capacity.
    subst_hub_von_mises_mpa : str
        Substituted equation string for nominal hub von Mises stress.

    ---LaTeX---
    \delta_d = p d \left(C_h + C_s\right)
    \delta_{d,op} = \delta_{d,ref} - d \left(\alpha_h - \alpha_s\right)\Delta T
    N = p \pi d L
    T_{max} = \mu N \frac{d}{2}
    F_{ax,max} = \mu N
    \sigma_{vm} = \sqrt{\sigma_\theta^2 - \sigma_\theta \sigma_r + \sigma_r^2}
    """

    _validate_positive("shaft_outer_diameter_mm", shaft_outer_diameter_mm)
    _validate_positive("hub_outer_diameter_mm", hub_outer_diameter_mm)
    _validate_positive("fit_length_mm", fit_length_mm)
    _validate_nonnegative("shaft_inner_diameter_mm", shaft_inner_diameter_mm)
    _validate_nonnegative("friction_coefficient", friction_coefficient)
    _validate_nonnegative("assembly_clearance_mm", assembly_clearance_mm)
    _validate_nonnegative("applied_torque_nm", abs(applied_torque_nm))
    _validate_nonnegative("applied_axial_force_n", abs(applied_axial_force_n))
    _validate_positive("required_slip_sf", required_slip_sf)
    _validate_positive("required_yield_sf", required_yield_sf)
    _validate_nonnegative("sweep_min_interference_mm", sweep_min_interference_mm)
    _validate_nonnegative("sweep_max_interference_mm", sweep_max_interference_mm)
    _validate_nonnegative("shaft_roughness_rz_um", shaft_roughness_rz_um)
    _validate_nonnegative("hub_roughness_rz_um", hub_roughness_rz_um)
    _validate_nonnegative("length_credit_ratio", length_credit_ratio)
    _validate_nonnegative("operating_speed_rpm", operating_speed_rpm)
    _validate_finite("reference_temperature_c", reference_temperature_c)
    _validate_finite("operating_temperature_c", operating_temperature_c)

    if hub_outer_diameter_mm <= shaft_outer_diameter_mm:
        raise ValueError("hub_outer_diameter_mm must be greater than shaft_outer_diameter_mm.")
    if shaft_inner_diameter_mm >= shaft_outer_diameter_mm:
        raise ValueError("shaft_inner_diameter_mm must be less than shaft_outer_diameter_mm.")
    if sweep_max_interference_mm < sweep_min_interference_mm:
        raise ValueError("sweep_max_interference_mm must be >= sweep_min_interference_mm.")

    interference_min_mm, interference_nominal_mm, interference_max_mm = _coerce_range(
        interference_nominal_mm,
        interference_min_mm,
        interference_max_mm,
    )

    shaft_props = _resolve_material(
        component_label="shaft",
        material_key=shaft_material,
        youngs_modulus_mpa=shaft_youngs_modulus_mpa,
        poisson_ratio=shaft_poisson_ratio,
        yield_strength_mpa=shaft_yield_strength_mpa,
        thermal_expansion_e6_per_c=shaft_thermal_expansion_e6_per_c,
        compressive_strength_mpa=shaft_compressive_strength_mpa,
        failure_criterion=shaft_failure_criterion,
    )
    hub_props = _resolve_material(
        component_label="hub",
        material_key=hub_material,
        youngs_modulus_mpa=hub_youngs_modulus_mpa,
        poisson_ratio=hub_poisson_ratio,
        yield_strength_mpa=hub_yield_strength_mpa,
        thermal_expansion_e6_per_c=hub_thermal_expansion_e6_per_c,
        compressive_strength_mpa=hub_compressive_strength_mpa,
        failure_criterion=hub_failure_criterion,
    )

    smoothing_loss_mm = _smoothing_loss_mm(
        shaft_roughness_rz_um=shaft_roughness_rz_um,
        hub_roughness_rz_um=hub_roughness_rz_um,
    )
    effective_fit_length_mm = _effective_fit_length_mm(
        fit_length_mm=fit_length_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        length_credit_ratio=length_credit_ratio,
    )
    compliance = _calculate_compliance_data(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        shaft_material=shaft_props,
        hub_material=hub_props,
    )
    speed_growth = _centrifugal_interference_relief_mm(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_material=shaft_props,
        hub_material=hub_props,
        speed_rpm=operating_speed_rpm,
    )
    speed_relief_mm = float(speed_growth["interference_relief_mm"])

    case_inputs = {
        "minimum": interference_min_mm,
        "nominal": interference_nominal_mm,
        "maximum": interference_max_mm,
    }
    range_cases: Dict[str, Dict[str, Any]] = {}
    all_warnings: List[str] = []

    for label, reference_interference in case_inputs.items():
        operating_interference = _thermal_adjusted_interference_mm(
            interference_mm=reference_interference,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            reference_temperature_c=reference_temperature_c,
            operating_temperature_c=operating_temperature_c,
            shaft_material=shaft_props,
            hub_material=hub_props,
        ) - speed_relief_mm
        reference_case = _evaluate_case(
            interference_mm=reference_interference,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_props,
            hub_material=hub_props,
            friction_coefficient=friction_coefficient,
            applied_torque_nm=applied_torque_nm,
            applied_axial_force_n=applied_axial_force_n,
            required_slip_sf=required_slip_sf,
            required_yield_sf=required_yield_sf,
            case_name=label,
            state_name="reference",
            smoothing_loss_mm=smoothing_loss_mm,
            effective_fit_length_mm=effective_fit_length_mm,
        )
        operating_case = _evaluate_case(
            interference_mm=max(0.0, operating_interference),
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_props,
            hub_material=hub_props,
            friction_coefficient=friction_coefficient,
            applied_torque_nm=applied_torque_nm,
            applied_axial_force_n=applied_axial_force_n,
            required_slip_sf=required_slip_sf,
            required_yield_sf=required_yield_sf,
            case_name=label,
            state_name="operating",
            smoothing_loss_mm=smoothing_loss_mm,
            effective_fit_length_mm=effective_fit_length_mm,
            speed_rpm=operating_speed_rpm,
        )
        operating_case["unclamped_interference_mm"] = operating_interference

        range_cases[label] = {
            "reference": reference_case,
            "operating": operating_case,
        }
        all_warnings.extend(reference_case["warnings"])
        all_warnings.extend(operating_case["warnings"])

    assembly = _thermal_assembly_plan(
        maximum_interference_mm=interference_max_mm,
        slip_clearance_mm=assembly_clearance_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        fit_length_mm=fit_length_mm,
        friction_coefficient=friction_coefficient,
        compliance_mm_per_mpa=float(compliance["total_term_mm_per_mpa"]),
        smoothing_loss_mm=smoothing_loss_mm,
        press_friction_factor=press_friction_factor,
        reference_temperature_c=reference_temperature_c,
        shaft_material=shaft_props,
        hub_material=hub_props,
        hub_assembly_temperature_c=hub_assembly_temperature_c,
        shaft_assembly_temperature_c=shaft_assembly_temperature_c,
        hub_max_assembly_temp_c=hub_max_assembly_temp_c,
        shaft_min_assembly_temp_c=shaft_min_assembly_temp_c,
        maximum_operating_temperature_c=operating_temperature_c,
        governing_interference_label="specified maximum interference",
    )
    all_warnings.extend(assembly["warnings"])

    nominal_case = range_cases["nominal"]
    minimum_case = range_cases["minimum"]
    maximum_case = range_cases["maximum"]
    reference_case = nominal_case["reference"]
    operating_case = nominal_case["operating"]

    fit_loss_temperature_c = _fit_loss_temperature_c(
        interference_mm=interference_nominal_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        reference_temperature_c=reference_temperature_c,
        shaft_material=shaft_props,
        hub_material=hub_props,
    )

    all_state_cases = [
        range_cases["minimum"]["reference"],
        range_cases["minimum"]["operating"],
        range_cases["nominal"]["reference"],
        range_cases["nominal"]["operating"],
        range_cases["maximum"]["reference"],
        range_cases["maximum"]["operating"],
    ]

    minimum_yield_safety_factor = min(case["yield_safety_factor"] for case in all_state_cases)
    minimum_operating_pressure_mpa = min(
        range_cases[label]["operating"]["pressure_mpa"] for label in ("minimum", "nominal", "maximum")
    )
    maximum_reference_pressure_mpa = max(
        range_cases[label]["reference"]["pressure_mpa"] for label in ("minimum", "nominal", "maximum")
    )

    minimum_torque_slip_safety_factor = min(
        range_cases[label]["operating"]["torque_slip_safety_factor"]
        for label in ("minimum", "nominal", "maximum")
    )
    minimum_axial_slip_safety_factor = min(
        range_cases[label]["operating"]["axial_slip_safety_factor"]
        for label in ("minimum", "nominal", "maximum")
    )
    minimum_combined_slip_safety_factor = min(
        range_cases[label]["operating"]["combined_slip_safety_factor"]
        for label in ("minimum", "nominal", "maximum")
    )
    has_duty = abs(applied_torque_nm) > 0.0 or abs(applied_axial_force_n) > 0.0

    governing_candidates: List[tuple[float, str]] = []
    if minimum_case["operating"]["fit_retained"]:
        governing_candidates.append((minimum_yield_safety_factor / required_yield_sf, "yield margin"))
    else:
        governing_candidates.append((0.0, "fit loss at minimum operating interference"))
    if has_duty:
        governing_candidates.append(
            (
                minimum_combined_slip_safety_factor / required_slip_sf,
                "combined slip at operating condition",
            )
        )
    if assembly["status"] != "acceptable":
        governing_candidates.append((0.95, "assembly temperature practicality"))

    governing_ratio, governing_mode = min(governing_candidates, key=lambda item: item[0])

    if not minimum_case["operating"]["fit_retained"]:
        status = "unacceptable"
    elif any(case["yield_safety_factor"] < 1.0 for case in all_state_cases):
        status = "unacceptable"
    elif has_duty and minimum_combined_slip_safety_factor < 1.0:
        status = "unacceptable"
    elif (
        minimum_yield_safety_factor < required_yield_sf
        or (has_duty and minimum_combined_slip_safety_factor < required_slip_sf)
        or assembly["status"] != "acceptable"
    ):
        status = "marginal"
    else:
        status = "acceptable"

    recommendations: List[str] = []
    if not minimum_case["operating"]["fit_retained"]:
        recommendations.append(
            "Increase minimum interference, reduce operating temperature, or use closer thermal expansion coefficients to retain fit."
        )
    if minimum_yield_safety_factor < required_yield_sf:
        recommendations.append(
            "Reduce maximum interference, increase hub wall thickness, or use stronger shaft/hub materials to improve yield margin."
        )
    if has_duty and minimum_combined_slip_safety_factor < required_slip_sf:
        recommendations.append(
            "Increase fit length, interference, or friction coefficient to improve slip margin."
        )
    if assembly["status"] != "acceptable":
        recommendations.append(
            "Review thermal assembly strategy; combined heating and cooling may be more practical than a single-sided temperature change."
        )
    if hub_outer_diameter_mm / shaft_outer_diameter_mm < 1.3:
        all_warnings.append(
            "Hub OD is only modestly larger than fit diameter; thin-wall behavior may increase sensitivity to assumptions."
        )
    if effective_fit_length_mm < fit_length_mm:
        all_warnings.append(
            f"Only {effective_fit_length_mm:.1f} mm of the {fit_length_mm:.1f} mm contact "
            f"length is credited. Pressure and micro-slip concentrate at the fit ends, so "
            f"length past L/d = {length_credit_ratio:.1f} adds little capacity."
        )
    if smoothing_loss_mm > 0.0:
        all_warnings.append(
            f"Surface roughness removes {smoothing_loss_mm * 1000.0:.1f} um of diametral "
            "interference at assembly. Contact pressure uses what is left."
        )
    else:
        all_warnings.append(
            "Surface roughness is set to zero, so no smoothing loss is charged. Real "
            "ground surfaces lose roughly 4 to 8 um of diametral interference."
        )
    for member_label, member_props in (("Shaft", shaft_props), ("Hub", hub_props)):
        if str(member_props["failure_criterion"]) == BRITTLE:
            all_warnings.append(
                f"{member_label} material is brittle, so it is checked with Coulomb-Mohr "
                "against separate tensile and compressive strengths rather than von Mises."
            )

    sweep_data = _generate_interference_sweep(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        fit_length_mm=fit_length_mm,
        nominal_interference_mm=interference_nominal_mm,
        shaft_material=shaft_props,
        hub_material=hub_props,
        friction_coefficient=friction_coefficient,
        reference_temperature_c=reference_temperature_c,
        operating_temperature_c=operating_temperature_c,
        sweep_min_interference_mm=sweep_min_interference_mm,
        sweep_max_interference_mm=sweep_max_interference_mm,
        n_sweep_points=int(n_sweep_points),
    )
    sweep_data["temperature_effect"] = _generate_temperature_sweep(
        nominal_interference_mm=interference_nominal_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        reference_temperature_c=reference_temperature_c,
        operating_temperature_c=operating_temperature_c,
        shaft_material=shaft_props,
        hub_material=hub_props,
    )
    sweep_data["interference_band"] = {
        "minimum_mm": interference_min_mm,
        "nominal_mm": interference_nominal_mm,
        "maximum_mm": interference_max_mm,
    }

    d = shaft_outer_diameter_mm
    denominator_m_per_pa = float(compliance["total_term_m_per_pa"])
    operating_interference_nominal = float(operating_case["unclamped_interference_mm"])

    subst_interface_pressure_mpa = (
        f"\\delta_d = p d (C_h + C_s) \\Rightarrow "
        f"p = \\frac{{{interference_nominal_mm:.4f}\\times10^{{-3}}}}{{{denominator_m_per_pa:.4e}}}"
        f" = {reference_case['pressure_mpa']:.2f}\\text{{ MPa}}"
    )
    subst_operating_interference_mm = (
        f"\\delta_{{d,op}} = \\delta_{{d,ref}} - d(\\alpha_h-\\alpha_s)\\Delta T"
        f" = {interference_nominal_mm:.4f} - {d:.1f}({float(hub_props['thermal_expansion_e6_per_c']):.2f}"
        f" - {float(shaft_props['thermal_expansion_e6_per_c']):.2f})\\times10^{{-6}}"
        f" \\times ({operating_temperature_c:.1f} - {reference_temperature_c:.1f})"
        f" = {operating_interference_nominal:.4f}\\text{{ mm}}"
    )
    subst_torque_capacity_nm = (
        f"T_{{max}} = \\mu p \\pi d L \\frac{{d}}{{2}}"
        f" = {friction_coefficient:.3f} \\times {operating_case['pressure_mpa']:.2f}\\times10^6"
        f" \\times \\pi \\times {d/1000:.4f} \\times {fit_length_mm/1000:.4f}"
        f" \\times \\frac{{{d/1000:.4f}}}{{2}}"
        f" = {operating_case['torque_capacity_nm']:.1f}\\text{{ N·m}}"
    )
    subst_hub_von_mises_mpa = (
        f"\\sigma_{{vm}} = \\sqrt{{\\sigma_\\theta^2 - \\sigma_\\theta\\sigma_r + \\sigma_r^2}}"
        f" = \\sqrt{{{reference_case['hub_hoop_stress_mpa']:.2f}^2 - "
        f"{reference_case['hub_hoop_stress_mpa']:.2f}({reference_case['hub_radial_stress_mpa']:.2f}) + "
        f"{reference_case['hub_radial_stress_mpa']:.2f}^2}}"
        f" = {reference_case['hub_von_mises_mpa']:.2f}\\text{{ MPa}}"
    )

    # Pushing a settled joint apart works against the interference that is
    # left after the roughness peaks have already flattened, which is less
    # than the press-on force reported in the assembly plan.
    settled_pressure_mpa = float(range_cases["maximum"]["reference"]["pressure_mpa"])
    push_off_force_n = (
        friction_coefficient
        * settled_pressure_mpa
        * 1e6
        * math.pi
        * (shaft_outer_diameter_mm / 1000.0)
        * (fit_length_mm / 1000.0)
    )
    assembly_forces = {
        "governing_interference_mm": interference_max_mm,
        "settled_pressure_mpa": settled_pressure_mpa,
        "push_off_force_n": push_off_force_n,
        "push_off_force_kn": push_off_force_n / 1000.0,
    }

    deduped_warnings = list(dict.fromkeys(all_warnings))
    deduped_recommendations = list(dict.fromkeys(recommendations))

    return {
        "reference_case": reference_case,
        "operating_case": operating_case,
        "nominal_case": nominal_case,
        "minimum_case": minimum_case,
        "maximum_case": maximum_case,
        "range_cases": range_cases,
        "assembly": assembly,
        "assembly_forces": assembly_forces,
        "compliance": compliance,
        "speed": {
            "operating_speed_rpm": operating_speed_rpm,
            "shaft_diametral_growth_mm": speed_growth["shaft_diametral_growth_mm"],
            "hub_bore_diametral_growth_mm": speed_growth["hub_bore_diametral_growth_mm"],
            "interference_relief_mm": speed_relief_mm,
        },
        "geometry": {
            "shaft_outer_diameter_mm": shaft_outer_diameter_mm,
            "shaft_inner_diameter_mm": shaft_inner_diameter_mm,
            "hub_outer_diameter_mm": hub_outer_diameter_mm,
            "fit_length_mm": fit_length_mm,
            "effective_fit_length_mm": effective_fit_length_mm,
            "length_credit_ratio": length_credit_ratio,
            "length_to_diameter_ratio": fit_length_mm / shaft_outer_diameter_mm,
            "shaft_outer_radius_mm": shaft_outer_diameter_mm / 2.0,
            "shaft_inner_radius_mm": shaft_inner_diameter_mm / 2.0,
            "hub_outer_radius_mm": hub_outer_diameter_mm / 2.0,
            "hub_to_shaft_diameter_ratio": hub_outer_diameter_mm / shaft_outer_diameter_mm,
            "shaft_member_type": "solid"
            if shaft_inner_diameter_mm <= 0.0
            else "hollow",
        },
        "materials": {
            "shaft": shaft_props,
            "hub": hub_props,
        },
        "state_temperatures_c": {
            "reference": reference_temperature_c,
            "operating": operating_temperature_c,
        },
        "stress_distribution_cases": {
            "reference": reference_case["stress_distribution"],
            "operating": operating_case["stress_distribution"],
        },
        "sweep_data": sweep_data,
        "status": status,
        "governing_mode": governing_mode,
        "warnings": deduped_warnings,
        "recommendations": deduped_recommendations,
        "shaft_material_name": str(shaft_props["display_name"]),
        "hub_material_name": str(hub_props["display_name"]),
        "fit_loss_temperature_c": fit_loss_temperature_c,
        "minimum_operating_pressure_mpa": minimum_operating_pressure_mpa,
        "maximum_reference_pressure_mpa": maximum_reference_pressure_mpa,
        "minimum_yield_safety_factor": minimum_yield_safety_factor,
        "minimum_torque_slip_safety_factor": minimum_torque_slip_safety_factor,
        "minimum_axial_slip_safety_factor": minimum_axial_slip_safety_factor,
        "minimum_combined_slip_safety_factor": minimum_combined_slip_safety_factor,
        "smoothing": {
            "shaft_roughness_rz_um": shaft_roughness_rz_um,
            "hub_roughness_rz_um": hub_roughness_rz_um,
            "smoothing_loss_mm": smoothing_loss_mm,
            "smoothing_loss_um": smoothing_loss_mm * 1000.0,
        },
        "subst_interface_pressure_mpa": subst_interface_pressure_mpa,
        "subst_operating_interference_mm": subst_operating_interference_mm,
        "subst_torque_capacity_nm": subst_torque_capacity_nm,
        "subst_hub_von_mises_mpa": subst_hub_von_mises_mpa,
    }


def _temperature_interference_relief_mm(
    shaft_outer_diameter_mm: float,
    reference_temperature_c: float,
    operating_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> float:
    """Return diametral fit relief from differential thermal expansion."""

    delta_t = operating_temperature_c - reference_temperature_c
    alpha_h = float(hub_material["thermal_expansion_e6_per_c"]) * 1e-6
    alpha_s = float(shaft_material["thermal_expansion_e6_per_c"]) * 1e-6
    return shaft_outer_diameter_mm * (alpha_h - alpha_s) * delta_t


def _free_rotating_radial_displacement_m(
    inner_radius_m: float,
    outer_radius_m: float,
    evaluation_radius_m: float,
    density_kg_m3: float,
    youngs_modulus_mpa: float,
    poisson_ratio: float,
    speed_rpm: float,
) -> float:
    """Return free radial growth of a uniform rotating disk or annulus."""

    if speed_rpm <= 0.0:
        return 0.0

    omega = 2.0 * math.pi * speed_rpm / 60.0
    youngs_modulus_pa = youngs_modulus_mpa * 1e6
    radius = evaluation_radius_m
    outer_sq = outer_radius_m**2

    if inner_radius_m <= 0.0:
        coefficient = density_kg_m3 * omega**2 / (8.0 * youngs_modulus_pa)
        return coefficient * (
            (1.0 - poisson_ratio)
            * (3.0 + poisson_ratio)
            * outer_sq
            * radius
            - (1.0 - poisson_ratio**2) * radius**3
        )

    inner_sq = inner_radius_m**2
    coefficient = density_kg_m3 * omega**2 / (8.0 * youngs_modulus_pa)
    return coefficient * (
        (1.0 - poisson_ratio)
        * (3.0 + poisson_ratio)
        * (inner_sq + outer_sq)
        * radius
        + (1.0 + poisson_ratio)
        * (3.0 + poisson_ratio)
        * inner_sq
        * outer_sq
        / radius
        - (1.0 - poisson_ratio**2) * radius**3
    )


def _centrifugal_interference_relief_mm(
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    speed_rpm: float,
) -> Dict[str, float]:
    """Return shaft growth, hub-bore growth, and net diametral fit relief."""

    shaft_outer_radius_m = shaft_outer_diameter_mm / 2000.0
    shaft_inner_radius_m = shaft_inner_diameter_mm / 2000.0
    hub_inner_radius_m = shaft_outer_radius_m
    hub_outer_radius_m = hub_outer_diameter_mm / 2000.0

    shaft_radial_growth_m = _free_rotating_radial_displacement_m(
        inner_radius_m=shaft_inner_radius_m,
        outer_radius_m=shaft_outer_radius_m,
        evaluation_radius_m=shaft_outer_radius_m,
        density_kg_m3=float(shaft_material["density_kg_m3"]),
        youngs_modulus_mpa=float(shaft_material["youngs_modulus_mpa"]),
        poisson_ratio=float(shaft_material["poisson_ratio"]),
        speed_rpm=speed_rpm,
    )
    hub_bore_radial_growth_m = _free_rotating_radial_displacement_m(
        inner_radius_m=hub_inner_radius_m,
        outer_radius_m=hub_outer_radius_m,
        evaluation_radius_m=hub_inner_radius_m,
        density_kg_m3=float(hub_material["density_kg_m3"]),
        youngs_modulus_mpa=float(hub_material["youngs_modulus_mpa"]),
        poisson_ratio=float(hub_material["poisson_ratio"]),
        speed_rpm=speed_rpm,
    )
    shaft_diametral_growth_mm = 2.0 * shaft_radial_growth_m * 1000.0
    hub_bore_diametral_growth_mm = 2.0 * hub_bore_radial_growth_m * 1000.0

    return {
        "shaft_diametral_growth_mm": shaft_diametral_growth_mm,
        "hub_bore_diametral_growth_mm": hub_bore_diametral_growth_mm,
        "interference_relief_mm": (
            hub_bore_diametral_growth_mm - shaft_diametral_growth_mm
        ),
    }


def _pressure_stress_at_radius_mpa(
    member: str,
    radius_m: float,
    pressure_mpa: float,
    inner_radius_m: float,
    outer_radius_m: float,
) -> tuple[float, float]:
    """Return Lamé radial and hoop stress from interface pressure."""

    if pressure_mpa <= 0.0:
        return 0.0, 0.0

    if member == "hub":
        coefficient = (
            pressure_mpa
            * inner_radius_m**2
            / (outer_radius_m**2 - inner_radius_m**2)
        )
        radial = coefficient * (1.0 - outer_radius_m**2 / radius_m**2)
        hoop = coefficient * (1.0 + outer_radius_m**2 / radius_m**2)
        return radial, hoop

    if inner_radius_m <= 0.0:
        return -pressure_mpa, -pressure_mpa

    coefficient = (
        -pressure_mpa
        * outer_radius_m**2
        / (outer_radius_m**2 - inner_radius_m**2)
    )
    radial = coefficient * (1.0 - inner_radius_m**2 / radius_m**2)
    hoop = coefficient * (1.0 + inner_radius_m**2 / radius_m**2)
    return radial, hoop


def _rotating_profile(
    inner_radius_mm: float,
    outer_radius_mm: float,
    fit_length_mm: float,
    material: Dict[str, float | str],
    speed_rpm: float,
    profile_points: int = 81,
) -> Dict[str, List[float]]:
    """Return a free-rotation stress profile, including a zero-speed case."""

    if speed_rpm > 0.0:
        result = calculate_rotor_hoop_stress(
            geometry_type=("solid_disk" if inner_radius_mm <= 0.0 else "annular_disk"),
            inner_radius_mm=inner_radius_mm,
            outer_radius_mm=outer_radius_mm,
            thickness_mm=fit_length_mm,
            density_kg_m3=float(material["density_kg_m3"]),
            poisson_ratio=float(material["poisson_ratio"]),
            speed_rpm=speed_rpm,
            yield_strength_mpa=float(material["yield_strength_mpa"]),
            required_safety_factor=1.0,
            profile_points=profile_points,
        )
        profile = result["stress_profile"]
        return {
            "radius_mm": list(profile["radius_mm"]),
            "sigma_r_mpa": list(profile["sigma_r_mpa"]),
            "sigma_theta_mpa": list(profile["sigma_theta_mpa"]),
        }

    start = max(0.0, inner_radius_mm)
    radii = [
        start + i * (outer_radius_mm - start) / (profile_points - 1)
        for i in range(profile_points)
    ]
    return {
        "radius_mm": radii,
        "sigma_r_mpa": [0.0 for _ in radii],
        "sigma_theta_mpa": [0.0 for _ in radii],
    }


def _rotation_profiles(
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    speed_rpm: float,
) -> Dict[str, Dict[str, List[float]]]:
    """Return free-rotation stress profiles for both members.

    These depend only on speed and geometry, not on contact pressure, so the
    pressure solver computes them once and reuses them across every iteration.
    """

    return {
        "shaft": _rotating_profile(
            inner_radius_mm=shaft_inner_diameter_mm / 2.0,
            outer_radius_mm=shaft_outer_diameter_mm / 2.0,
            fit_length_mm=fit_length_mm,
            material=shaft_material,
            speed_rpm=speed_rpm,
        ),
        "hub": _rotating_profile(
            inner_radius_mm=shaft_outer_diameter_mm / 2.0,
            outer_radius_mm=hub_outer_diameter_mm / 2.0,
            fit_length_mm=fit_length_mm,
            material=hub_material,
            speed_rpm=speed_rpm,
        ),
    }


def _combined_rotating_fit_stress(
    pressure_mpa: float,
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    speed_rpm: float,
    profiles: Dict[str, Dict[str, List[float]]] | None = None,
) -> Dict[str, Any]:
    """Superimpose free-rotation and pressure stresses for both members."""

    if profiles is None:
        profiles = _rotation_profiles(
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_material,
            hub_material=hub_material,
            speed_rpm=speed_rpm,
        )

    member_inputs = {
        "shaft": {
            "inner_radius_mm": shaft_inner_diameter_mm / 2.0,
            "outer_radius_mm": shaft_outer_diameter_mm / 2.0,
            "material": shaft_material,
        },
        "hub": {
            "inner_radius_mm": shaft_outer_diameter_mm / 2.0,
            "outer_radius_mm": hub_outer_diameter_mm / 2.0,
            "material": hub_material,
        },
    }
    output: Dict[str, Any] = {}

    for member, inputs in member_inputs.items():
        inner_radius_mm = float(inputs["inner_radius_mm"])
        outer_radius_mm = float(inputs["outer_radius_mm"])
        material = inputs["material"]
        profile = profiles[member]
        combined_radial: List[float] = []
        combined_hoop: List[float] = []
        combined_vm: List[float] = []
        combined_sf: List[float] = []

        for radius_mm, rotation_radial, rotation_hoop in zip(
            profile["radius_mm"],
            profile["sigma_r_mpa"],
            profile["sigma_theta_mpa"],
        ):
            pressure_radial, pressure_hoop = _pressure_stress_at_radius_mpa(
                member=member,
                radius_m=max(radius_mm / 1000.0, 1e-15),
                pressure_mpa=pressure_mpa,
                inner_radius_m=inner_radius_mm / 1000.0,
                outer_radius_m=outer_radius_mm / 1000.0,
            )
            radial = rotation_radial + pressure_radial
            hoop = rotation_hoop + pressure_hoop
            equivalent, factor = _strength_safety_factor(radial, hoop, material)
            combined_radial.append(radial)
            combined_hoop.append(hoop)
            combined_vm.append(equivalent)
            combined_sf.append(factor)

        max_index = max(range(len(combined_vm)), key=combined_vm.__getitem__)
        max_vm = combined_vm[max_index]
        output[member] = {
            "max_von_mises_mpa": max_vm,
            "failure_criterion": str(material.get("failure_criterion", VON_MISES)),
            "yield_safety_factor": min(combined_sf),
            "critical_radius_mm": profile["radius_mm"][max_index],
            "profile": {
                "radius_mm": profile["radius_mm"],
                "radial_stress_mpa": combined_radial,
                "hoop_stress_mpa": combined_hoop,
                "von_mises_mpa": combined_vm,
            },
        }

    output["minimum_yield_safety_factor"] = min(
        float(output["shaft"]["yield_safety_factor"]),
        float(output["hub"]["yield_safety_factor"]),
    )
    return output


def _maximum_allowable_pressure_mpa(
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    speed_rpm: float,
    required_yield_sf: float,
) -> Dict[str, Any]:
    """Solve the first pressure where either rotating member reaches its limit."""

    profiles = _rotation_profiles(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        fit_length_mm=fit_length_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
        speed_rpm=speed_rpm,
    )

    def evaluate(pressure_mpa: float) -> Dict[str, Any]:
        return _combined_rotating_fit_stress(
            pressure_mpa=pressure_mpa,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_material,
            hub_material=hub_material,
            speed_rpm=speed_rpm,
            profiles=profiles,
        )

    def governing_member(state: Dict[str, Any]) -> str:
        shaft_sf = float(state["shaft"]["yield_safety_factor"])
        hub_sf = float(state["hub"]["yield_safety_factor"])
        return "shaft" if shaft_sf <= hub_sf else "hub"

    rotation_only = evaluate(0.0)
    if float(rotation_only["minimum_yield_safety_factor"]) < required_yield_sf:
        return {
            "pressure_mpa": 0.0,
            "governing_member": governing_member(rotation_only),
            "stress_state": rotation_only,
            "rotation_only_exceeds_limit": True,
        }

    def is_within_limit(state: Dict[str, Any]) -> bool:
        return float(state["minimum_yield_safety_factor"]) >= required_yield_sf

    lower = 0.0
    upper = max(
        float(shaft_material["yield_strength_mpa"]),
        float(hub_material["yield_strength_mpa"]),
        1.0,
    )
    upper_state = evaluate(upper)
    while is_within_limit(upper_state) and upper < 1e6:
        lower = upper
        upper *= 2.0
        upper_state = evaluate(upper)

    # Stop once the bracket is tight enough to be invisible at display
    # precision. The old fixed 52 iterations chased float noise and, with the
    # rotation profile rebuilt inside each one, dominated the total runtime.
    for _ in range(60):
        if upper - lower <= max(1e-6 * upper, 1e-9):
            break
        midpoint = 0.5 * (lower + upper)
        if is_within_limit(evaluate(midpoint)):
            lower = midpoint
        else:
            upper = midpoint

    limit_state = evaluate(lower)
    return {
        "pressure_mpa": lower,
        "governing_member": governing_member(limit_state),
        "stress_state": limit_state,
        "rotation_only_exceeds_limit": False,
    }


def _required_combined_contact_pressure_mpa(
    required_torque_nm: float,
    applied_axial_force_n: float,
    shaft_outer_diameter_mm: float,
    fit_length_mm: float,
    friction_coefficient: float,
    required_slip_sf: float,
) -> Dict[str, float]:
    """Return contact pressure for combined circumferential and axial traction."""

    diameter_m = shaft_outer_diameter_mm / 1000.0
    length_m = fit_length_mm / 1000.0
    tangential_force_n = 2.0 * abs(required_torque_nm) / diameter_m
    equivalent_force_n = math.hypot(tangential_force_n, abs(applied_axial_force_n))
    required_friction_force_n = required_slip_sf * equivalent_force_n
    contact_area_m2 = math.pi * diameter_m * length_m
    pressure_mpa = required_friction_force_n / (
        friction_coefficient * contact_area_m2
    ) / 1e6
    return {
        "tangential_force_n": tangential_force_n,
        "axial_force_n": abs(applied_axial_force_n),
        "equivalent_force_n": equivalent_force_n,
        "required_friction_force_n": required_friction_force_n,
        "contact_area_m2": contact_area_m2,
        "required_contact_pressure_mpa": pressure_mpa,
    }


def _cooling_route(temperature_c: float | None) -> Dict[str, Any]:
    """Classify a shaft cooling target against real chilling methods."""

    if temperature_c is None:
        return {"route": "not available", "feasible": False}
    if temperature_c <= ABSOLUTE_ZERO_C:
        return {"route": "below absolute zero, impossible", "feasible": False}
    if temperature_c < LIQUID_NITROGEN_C:
        return {"route": "colder than liquid nitrogen, impractical", "feasible": False}
    if temperature_c < DRY_ICE_C:
        return {"route": "liquid nitrogen", "feasible": True}
    if temperature_c < 0.0:
        return {"route": "dry ice", "feasible": True}
    return {"route": "no chilling needed", "feasible": True}


def _heating_route(
    temperature_c: float | None,
    reference_temperature_c: float,
) -> Dict[str, Any]:
    """Classify a hub heating target against normal shop practice."""

    if temperature_c is None:
        return {"route": "not available", "feasible": False}
    rise = temperature_c - reference_temperature_c
    if rise <= 0.0:
        return {"route": "no heating needed", "feasible": True}
    if temperature_c <= 200.0:
        return {"route": "oven or induction", "feasible": True}
    if temperature_c <= 350.0:
        return {"route": "oven, verify temper and coatings", "feasible": True}
    return {"route": "above normal shop practice", "feasible": False}


def size_interference_fit(
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    required_torque_nm: float,
    maximum_speed_rpm: float = 0.0,
    minimum_operating_temperature_c: float = 20.0,
    maximum_operating_temperature_c: float = 20.0,
    shaft_inner_diameter_mm: float = 0.0,
    shaft_material: str = "steel",
    hub_material: str = "steel",
    friction_coefficient: float = 0.15,
    required_slip_sf: float = 1.5,
    required_yield_sf: float = 1.2,
    applied_axial_force_n: float = 0.0,
    reference_temperature_c: float = 20.0,
    assembly_clearance_mm: float = 0.01,
    hub_assembly_temperature_c: float | None = None,
    shaft_assembly_temperature_c: float | None = None,
    hub_max_assembly_temp_c: float | None = None,
    shaft_min_assembly_temp_c: float | None = None,
    press_friction_factor: float = 1.5,
    shaft_roughness_rz_um: float = 0.0,
    hub_roughness_rz_um: float = 0.0,
    length_credit_ratio: float = 1.5,
    shaft_youngs_modulus_mpa: float = 200000.0,
    shaft_poisson_ratio: float = 0.30,
    shaft_yield_strength_mpa: float = 450.0,
    shaft_thermal_expansion_e6_per_c: float = 12.0,
    shaft_density_kg_m3: float = 7850.0,
    shaft_compressive_strength_mpa: float = 0.0,
    shaft_failure_criterion: str = VON_MISES,
    hub_youngs_modulus_mpa: float = 200000.0,
    hub_poisson_ratio: float = 0.30,
    hub_yield_strength_mpa: float = 350.0,
    hub_thermal_expansion_e6_per_c: float = 12.0,
    hub_density_kg_m3: float = 7850.0,
    hub_compressive_strength_mpa: float = 0.0,
    hub_failure_criterion: str = VON_MISES,
) -> Dict[str, Any]:
    r"""
    Size the diametral interference range for a torque-transmitting ring fit.

    The lower drawing limit supplies the requested combined torque and axial
    traction at every temperature in the service envelope after differential
    thermal expansion and centrifugal growth. The upper drawing limit keeps the
    shaft and hub below their requested elastic yield limits at rest and at
    maximum running speed. The model assumes uniform contact pressure, Coulomb
    friction, uniform temperatures, and axisymmetric plane-stress members.

    References: Budynas and Nisbett, Shigley's Mechanical Engineering Design,
    interference fits; Timoshenko and Goodier, Theory of Elasticity, rotating
    disks and annuli.

    ---Parameters---
    shaft_outer_diameter_mm : float
        Nominal shaft and hub-bore fit diameter, in mm.
    hub_outer_diameter_mm : float
        Hub outside diameter through the fitted section, in mm.
    fit_length_mm : float
        Axial contact length of the cylindrical fit, in mm.
    required_torque_nm : float
        Maximum torque that the fit must transmit without slip, in N-m.
    maximum_speed_rpm : float
        Maximum common shaft and hub running speed, in rev/min.
    minimum_operating_temperature_c : float
        Lowest uniform shaft and hub service temperature, in deg C.
    maximum_operating_temperature_c : float
        Highest uniform shaft and hub service temperature, in deg C.
    shaft_inner_diameter_mm : float
        Shaft bore diameter, in mm. Use zero for a solid shaft.
    shaft_material : str
        Shaft material preset key, or `custom` for explicit properties.
    hub_material : str
        Hub material preset key, or `custom` for explicit properties.
    friction_coefficient : float
        Conservative static friction coefficient at the fitted interface.
    required_slip_sf : float
        Required safety factor against combined torque and axial slip.
    required_yield_sf : float
        Required elastic yield safety factor for both rotating members.
    applied_axial_force_n : float
        Simultaneous axial force carried by friction, in N.
    reference_temperature_c : float
        Temperature at which drawing diameters and interference apply, in deg C.
    assembly_clearance_mm : float
        Diametral slip clearance wanted when the parts go together, in mm. The
        thermal assembly plan has to open the maximum interference plus this.
    hub_assembly_temperature_c : float
        Temperature you plan to heat the hub to for assembly, in deg C.
        Defaults to the reference temperature, meaning no heating. Sets how
        much of the press force the plan removes.
    shaft_assembly_temperature_c : float
        Temperature you plan to chill the shaft to for assembly, in deg C.
        Defaults to the reference temperature, meaning no chilling.
    hub_max_assembly_temp_c : float
        Hottest the hub can be taken to, in deg C. Leave unset for no limit.
        Constrains which route the tool recommends.
    shaft_min_assembly_temp_c : float
        Coldest the shaft can be taken to, in deg C. Leave unset for no limit.
    press_friction_factor : float
        Multiplier on the friction coefficient for pressing the joint together.
        Sliding one part into the other galls, so insertion friction runs above
        the settled slip value. DIN 7190 treats the two separately.
    shaft_roughness_rz_um : float
        Shaft surface roughness Rz, in micrometres. Asperities flatten during
        assembly, so this interference is lost and never makes pressure.
    hub_roughness_rz_um : float
        Hub bore surface roughness Rz, in micrometres.
    length_credit_ratio : float
        Maximum length-to-diameter ratio credited with carrying load. Pressure
        concentrates at the fit ends, so length past roughly 1.5 adds little.
        Set to zero to credit the full contact length.
    shaft_youngs_modulus_mpa : float
        Custom shaft Young's modulus, in MPa.
    shaft_poisson_ratio : float
        Custom shaft Poisson ratio.
    shaft_yield_strength_mpa : float
        Custom shaft yield strength, in MPa.
    shaft_thermal_expansion_e6_per_c : float
        Custom shaft thermal expansion, in microstrain per deg C.
    shaft_density_kg_m3 : float
        Custom shaft density, in kg/m^3.
    shaft_compressive_strength_mpa : float
        Custom shaft compressive strength, in MPa, used when the shaft uses the
        brittle criterion. Defaults to the yield strength when left at zero.
    shaft_failure_criterion : str
        `von_mises` for ductile shafts or `brittle` for Coulomb-Mohr.
    hub_youngs_modulus_mpa : float
        Custom hub Young's modulus, in MPa.
    hub_poisson_ratio : float
        Custom hub Poisson ratio.
    hub_yield_strength_mpa : float
        Custom hub yield strength, in MPa.
    hub_thermal_expansion_e6_per_c : float
        Custom hub thermal expansion, in microstrain per deg C.
    hub_density_kg_m3 : float
        Custom hub density, in kg/m^3.
    hub_compressive_strength_mpa : float
        Custom hub compressive strength, in MPa, used when the hub uses the
        brittle criterion. Defaults to the yield strength when left at zero.
    hub_failure_criterion : str
        `von_mises` for ductile hubs or `brittle` for Coulomb-Mohr.

    ---Returns---
    design_range : dict
        Required minimum, allowable maximum, target, and tolerance in mm.
    load_requirement : dict
        Combined traction force, required pressure, and service interference.
    service_states : list
        Endpoint service checks with fit relief, pressure, capacity, and stress.
    reference_state : dict
        Stationary reference-temperature upper-limit stress check.
    assembly : dict
        Hub heating, shaft chilling, and combined temperatures that open the
        maximum interference, each with its route and whether it fits inside
        the stated equipment limits, plus the recommended route.
    assembly_forces : dict
        Force to push a settled joint apart at the maximum interference. The
        press-on force lives in `assembly.planned`, where it responds to the
        assembly temperatures.
    manufacturing : dict
        ISO 286 grading of the available interference window.
    smoothing : dict
        Interference lost to surface roughness flattening at assembly.
    compliance : dict
        Shaft, hub, and combined elastic compliance terms.
    geometry : dict
        Geometry values and diameter ratios used in the sizing model.
    materials : dict
        Resolved shaft and hub material properties.
    sweep_data : dict
        Temperature arrays for the instantaneous feasible interference window.
    status : str
        `acceptable`, `marginal`, or `unacceptable` sizing result.
    governing_mode : str
        Human-readable lower-bound and upper-bound governing conditions.
    warnings : list
        Model and manufacturability cautions raised by the calculation.
    recommendations : list
        Actions that can widen an infeasible or narrow design window.
    shaft_material_name : str
        Resolved shaft material display name.
    hub_material_name : str
        Resolved hub material display name.
    subst_required_contact_pressure_mpa : str
        Substituted combined-traction pressure equation.
    subst_required_interference_min_mm : str
        Substituted minimum reference-interference equation.
    subst_allowable_interference_max_mm : str
        Substituted maximum reference-interference equation.
    subst_recommended_interference_mm : str
        Substituted midpoint target equation.

    ---LaTeX---
    F_t = \frac{2T}{d}
    p_{req} = \frac{SF_s\sqrt{F_t^2+F_a^2}}{\mu\pi dL}
    \delta_{op,req} = p_{req}C_d
    \Delta\delta_T = d(\alpha_h-\alpha_s)(T-T_{ref})
    \Delta\delta_\omega = 2(u_{h,i}-u_{s,o})
    \delta_{ref,min} = \max_T(\delta_{op,req}+\Delta\delta_T+\Delta\delta_\omega)
    \delta_{ref,max} = \min_j(p_{allow,j}C_d+\Delta\delta_j)
    \delta_{target} = \frac{\delta_{ref,min}+\delta_{ref,max}}{2}
    """

    _validate_positive("shaft_outer_diameter_mm", shaft_outer_diameter_mm)
    _validate_positive("hub_outer_diameter_mm", hub_outer_diameter_mm)
    _validate_positive("fit_length_mm", fit_length_mm)
    _validate_nonnegative("required_torque_nm", abs(required_torque_nm))
    _validate_nonnegative("maximum_speed_rpm", maximum_speed_rpm)
    _validate_nonnegative("shaft_inner_diameter_mm", shaft_inner_diameter_mm)
    _validate_positive("friction_coefficient", friction_coefficient)
    _validate_positive("required_slip_sf", required_slip_sf)
    _validate_positive("required_yield_sf", required_yield_sf)
    _validate_nonnegative("applied_axial_force_n", abs(applied_axial_force_n))
    _validate_nonnegative("assembly_clearance_mm", assembly_clearance_mm)
    _validate_nonnegative("shaft_roughness_rz_um", shaft_roughness_rz_um)
    _validate_nonnegative("hub_roughness_rz_um", hub_roughness_rz_um)
    _validate_nonnegative("length_credit_ratio", length_credit_ratio)
    _validate_finite("minimum_operating_temperature_c", minimum_operating_temperature_c)
    _validate_finite("maximum_operating_temperature_c", maximum_operating_temperature_c)
    _validate_finite("reference_temperature_c", reference_temperature_c)

    # A joint held only against thrust is a normal design. Either duty alone
    # is enough to size the fit, but a fit with no duty at all is not.
    if abs(required_torque_nm) <= 0.0 and abs(applied_axial_force_n) <= 0.0:
        raise ValueError(
            "Either required_torque_nm or applied_axial_force_n must be > 0."
        )

    if hub_outer_diameter_mm <= shaft_outer_diameter_mm:
        raise ValueError("hub_outer_diameter_mm must be greater than shaft_outer_diameter_mm.")
    if shaft_inner_diameter_mm >= shaft_outer_diameter_mm:
        raise ValueError("shaft_inner_diameter_mm must be less than shaft_outer_diameter_mm.")
    if minimum_operating_temperature_c > maximum_operating_temperature_c:
        raise ValueError(
            "minimum_operating_temperature_c must be <= maximum_operating_temperature_c."
        )

    shaft_props = _resolve_material(
        component_label="shaft",
        material_key=shaft_material,
        youngs_modulus_mpa=shaft_youngs_modulus_mpa,
        poisson_ratio=shaft_poisson_ratio,
        yield_strength_mpa=shaft_yield_strength_mpa,
        thermal_expansion_e6_per_c=shaft_thermal_expansion_e6_per_c,
        density_kg_m3=shaft_density_kg_m3,
        compressive_strength_mpa=shaft_compressive_strength_mpa,
        failure_criterion=shaft_failure_criterion,
    )
    hub_props = _resolve_material(
        component_label="hub",
        material_key=hub_material,
        youngs_modulus_mpa=hub_youngs_modulus_mpa,
        poisson_ratio=hub_poisson_ratio,
        yield_strength_mpa=hub_yield_strength_mpa,
        thermal_expansion_e6_per_c=hub_thermal_expansion_e6_per_c,
        density_kg_m3=hub_density_kg_m3,
        compressive_strength_mpa=hub_compressive_strength_mpa,
        failure_criterion=hub_failure_criterion,
    )
    compliance = _calculate_compliance_data(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        shaft_material=shaft_props,
        hub_material=hub_props,
    )
    compliance_mm_per_mpa = float(compliance["total_term_mm_per_mpa"])
    effective_fit_length_mm = _effective_fit_length_mm(
        fit_length_mm=fit_length_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        length_credit_ratio=length_credit_ratio,
    )
    smoothing_loss_mm = _smoothing_loss_mm(
        shaft_roughness_rz_um=shaft_roughness_rz_um,
        hub_roughness_rz_um=hub_roughness_rz_um,
    )
    load_requirement = _required_combined_contact_pressure_mpa(
        required_torque_nm=required_torque_nm,
        applied_axial_force_n=applied_axial_force_n,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        fit_length_mm=effective_fit_length_mm,
        friction_coefficient=friction_coefficient,
        required_slip_sf=required_slip_sf,
    )
    required_pressure_mpa = float(load_requirement["required_contact_pressure_mpa"])
    required_operating_interference_mm = required_pressure_mpa * compliance_mm_per_mpa
    load_requirement["required_operating_interference_mm"] = required_operating_interference_mm
    load_requirement["effective_fit_length_mm"] = effective_fit_length_mm
    load_requirement["length_credit_applied"] = effective_fit_length_mm < fit_length_mm

    endpoint_speeds = [0.0]
    if maximum_speed_rpm > 0.0:
        endpoint_speeds.append(maximum_speed_rpm)
    speed_states: Dict[float, Dict[str, Any]] = {}
    for speed_rpm in endpoint_speeds:
        speed_states[speed_rpm] = {
            "growth": _centrifugal_interference_relief_mm(
                shaft_outer_diameter_mm=shaft_outer_diameter_mm,
                shaft_inner_diameter_mm=shaft_inner_diameter_mm,
                hub_outer_diameter_mm=hub_outer_diameter_mm,
                shaft_material=shaft_props,
                hub_material=hub_props,
                speed_rpm=speed_rpm,
            ),
            "pressure_limit": _maximum_allowable_pressure_mpa(
                shaft_outer_diameter_mm=shaft_outer_diameter_mm,
                shaft_inner_diameter_mm=shaft_inner_diameter_mm,
                hub_outer_diameter_mm=hub_outer_diameter_mm,
                fit_length_mm=fit_length_mm,
                shaft_material=shaft_props,
                hub_material=hub_props,
                speed_rpm=speed_rpm,
                required_yield_sf=required_yield_sf,
            ),
        }

    reference_pressure_limit = speed_states[0.0]["pressure_limit"]
    # Every drawing-interference bound carries the smoothing loss, because the
    # roughness peaks crush before any of the specified interference turns
    # into contact pressure.
    reference_max_interference_mm = (
        float(reference_pressure_limit["pressure_mpa"]) * compliance_mm_per_mpa
        + smoothing_loss_mm
    )

    endpoint_temperatures = [minimum_operating_temperature_c]
    if maximum_operating_temperature_c != minimum_operating_temperature_c:
        endpoint_temperatures.append(maximum_operating_temperature_c)

    lower_candidates: List[Dict[str, Any]] = []
    upper_candidates: List[Dict[str, Any]] = [
        {
            "label": "stationary reference-temperature yield limit",
            "temperature_c": reference_temperature_c,
            "value_mm": reference_max_interference_mm,
            "pressure_limit_mpa": float(reference_pressure_limit["pressure_mpa"]),
            "governing_member": reference_pressure_limit["governing_member"],
            "thermal_relief_mm": 0.0,
            "speed_relief_mm": 0.0,
            "total_relief_mm": 0.0,
        }
    ]

    for speed_rpm, speed_state in speed_states.items():
        speed_growth = speed_state["growth"]
        pressure_limit = speed_state["pressure_limit"]
        speed_relief_mm = float(speed_growth["interference_relief_mm"])
        for temperature_c in endpoint_temperatures:
            thermal_relief_mm = _temperature_interference_relief_mm(
                shaft_outer_diameter_mm=shaft_outer_diameter_mm,
                reference_temperature_c=reference_temperature_c,
                operating_temperature_c=temperature_c,
                shaft_material=shaft_props,
                hub_material=hub_props,
            )
            total_relief_mm = thermal_relief_mm + speed_relief_mm
            label = f"{temperature_c:.1f} deg C at {speed_rpm:.0f} rpm"
            common_state = {
                "label": label,
                "temperature_c": temperature_c,
                "speed_rpm": speed_rpm,
                "thermal_relief_mm": thermal_relief_mm,
                "shaft_diametral_growth_mm": speed_growth[
                    "shaft_diametral_growth_mm"
                ],
                "hub_bore_diametral_growth_mm": speed_growth[
                    "hub_bore_diametral_growth_mm"
                ],
                "speed_relief_mm": speed_relief_mm,
                "total_relief_mm": total_relief_mm,
            }
            lower_candidates.append(
                {
                    **common_state,
                    "value_mm": max(
                        0.0,
                        required_operating_interference_mm
                        + total_relief_mm
                        + smoothing_loss_mm,
                    ),
                }
            )
            upper_candidates.append(
                {
                    **common_state,
                    "label": f"{label} yield limit",
                    "value_mm": (
                        float(pressure_limit["pressure_mpa"])
                        * compliance_mm_per_mpa
                        + total_relief_mm
                        + smoothing_loss_mm
                    ),
                    "pressure_limit_mpa": float(pressure_limit["pressure_mpa"]),
                    "governing_member": pressure_limit["governing_member"],
                }
            )

    governing_lower = max(lower_candidates, key=lambda item: float(item["value_mm"]))
    governing_upper = min(upper_candidates, key=lambda item: float(item["value_mm"]))
    required_minimum_mm = float(governing_lower["value_mm"])
    allowable_maximum_mm = float(governing_upper["value_mm"])
    available_tolerance_mm = allowable_maximum_mm - required_minimum_mm
    rotation_only_exceeds_limit = any(
        bool(state["pressure_limit"]["rotation_only_exceeds_limit"])
        for state in speed_states.values()
    )
    feasible = available_tolerance_mm >= 0.0 and not rotation_only_exceeds_limit
    recommended_mm = (
        0.5 * (required_minimum_mm + allowable_maximum_mm) if feasible else None
    )
    bilateral_tolerance_mm = 0.5 * available_tolerance_mm if feasible else None

    service_states: List[Dict[str, Any]] = []
    evaluation_interference_mm = (
        float(recommended_mm) if recommended_mm is not None else required_minimum_mm
    )
    diameter_m = shaft_outer_diameter_mm / 1000.0
    equivalent_force_n = float(load_requirement["equivalent_force_n"])

    for lower_candidate in lower_candidates:
        total_relief_mm = float(lower_candidate["total_relief_mm"])
        operating_interference_mm = max(
            0.0,
            evaluation_interference_mm - total_relief_mm - smoothing_loss_mm,
        )
        pressure_mpa = operating_interference_mm / compliance_mm_per_mpa
        stress_state = _combined_rotating_fit_stress(
            pressure_mpa=pressure_mpa,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_props,
            hub_material=hub_props,
            speed_rpm=float(lower_candidate["speed_rpm"]),
        )
        capacities = _calculate_slip_capacities(
            pressure_mpa=pressure_mpa,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            fit_length_mm=effective_fit_length_mm,
            friction_coefficient=friction_coefficient,
            applied_torque_nm=required_torque_nm,
            applied_axial_force_n=applied_axial_force_n,
        )
        available_friction_force_n = (
            friction_coefficient
            * pressure_mpa
            * 1e6
            * math.pi
            * diameter_m
            * (effective_fit_length_mm / 1000.0)
        )
        combined_slip_sf = (
            available_friction_force_n / equivalent_force_n
            if equivalent_force_n > 0.0
            else float("inf")
        )
        service_states.append(
            {
                "label": lower_candidate["label"],
                "temperature_c": lower_candidate["temperature_c"],
                "speed_rpm": lower_candidate["speed_rpm"],
                "thermal_relief_mm": lower_candidate["thermal_relief_mm"],
                "shaft_diametral_growth_mm": lower_candidate[
                    "shaft_diametral_growth_mm"
                ],
                "hub_bore_diametral_growth_mm": lower_candidate[
                    "hub_bore_diametral_growth_mm"
                ],
                "speed_relief_mm": lower_candidate["speed_relief_mm"],
                "total_relief_mm": total_relief_mm,
                "reference_interference_mm": evaluation_interference_mm,
                "operating_interference_mm": operating_interference_mm,
                "pressure_mpa": pressure_mpa,
                "torque_capacity_nm": capacities["torque_capacity_nm"],
                "combined_slip_safety_factor": combined_slip_sf,
                "minimum_yield_safety_factor": stress_state[
                    "minimum_yield_safety_factor"
                ],
                "shaft_max_von_mises_mpa": stress_state["shaft"][
                    "max_von_mises_mpa"
                ],
                "hub_max_von_mises_mpa": stress_state["hub"][
                    "max_von_mises_mpa"
                ],
            }
        )

    reference_evaluation_pressure_mpa = (
        max(0.0, evaluation_interference_mm - smoothing_loss_mm)
        / compliance_mm_per_mpa
    )
    reference_stress_state = _combined_rotating_fit_stress(
        pressure_mpa=reference_evaluation_pressure_mpa,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        fit_length_mm=fit_length_mm,
        shaft_material=shaft_props,
        hub_material=hub_props,
        speed_rpm=0.0,
    )
    reference_state = {
        "temperature_c": reference_temperature_c,
        "speed_rpm": 0.0,
        "reference_interference_mm": evaluation_interference_mm,
        "pressure_mpa": reference_evaluation_pressure_mpa,
        "minimum_yield_safety_factor": reference_stress_state[
            "minimum_yield_safety_factor"
        ],
        "shaft_max_von_mises_mpa": reference_stress_state["shaft"][
            "max_von_mises_mpa"
        ],
        "hub_max_von_mises_mpa": reference_stress_state["hub"][
            "max_von_mises_mpa"
        ],
        "allowable_pressure_mpa": reference_pressure_limit["pressure_mpa"],
        "governing_member": reference_pressure_limit["governing_member"],
    }

    minimum_service_pressure_mpa = min(
        float(state["pressure_mpa"]) for state in service_states
    )
    minimum_service_torque_capacity_nm = min(
        float(state["torque_capacity_nm"]) for state in service_states
    )
    minimum_service_slip_sf = min(
        float(state["combined_slip_safety_factor"]) for state in service_states
    )
    minimum_design_yield_sf = min(
        float(reference_state["minimum_yield_safety_factor"]),
        *(float(state["minimum_yield_safety_factor"]) for state in service_states),
    )

    design_range = {
        "required_minimum_mm": required_minimum_mm,
        "allowable_maximum_mm": allowable_maximum_mm,
        "recommended_nominal_mm": recommended_mm,
        "recommended_bilateral_tolerance_mm": bilateral_tolerance_mm,
        "available_tolerance_mm": available_tolerance_mm,
        "feasible": feasible,
        "governing_lower_label": governing_lower["label"],
        "governing_upper_label": governing_upper["label"],
        "governing_upper_member": governing_upper.get("governing_member"),
        "minimum_service_pressure_mpa": minimum_service_pressure_mpa,
        "minimum_service_torque_capacity_nm": minimum_service_torque_capacity_nm,
        "minimum_service_slip_safety_factor": minimum_service_slip_sf,
        "minimum_design_yield_safety_factor": minimum_design_yield_sf,
    }
    # The joint has to be assembled at the tightest end of the band that gets
    # released, which is the target plus its tolerance and therefore the
    # allowable maximum. With no feasible band there is nothing to release, so
    # fall back to the interference the duty demands and say so.
    assembly_governing_mm = (
        allowable_maximum_mm if feasible else required_minimum_mm
    )
    assembly = _thermal_assembly_plan(
        maximum_interference_mm=assembly_governing_mm,
        slip_clearance_mm=assembly_clearance_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        fit_length_mm=fit_length_mm,
        friction_coefficient=friction_coefficient,
        compliance_mm_per_mpa=compliance_mm_per_mpa,
        smoothing_loss_mm=smoothing_loss_mm,
        press_friction_factor=press_friction_factor,
        reference_temperature_c=reference_temperature_c,
        shaft_material=shaft_props,
        hub_material=hub_props,
        hub_assembly_temperature_c=hub_assembly_temperature_c,
        shaft_assembly_temperature_c=shaft_assembly_temperature_c,
        hub_max_assembly_temp_c=hub_max_assembly_temp_c,
        shaft_min_assembly_temp_c=shaft_min_assembly_temp_c,
        maximum_operating_temperature_c=maximum_operating_temperature_c,
        governing_interference_label=(
            "allowable maximum" if feasible else "required minimum, no feasible band"
        ),
    )

    # Pushing a settled joint apart works against the interference that is
    # left after the roughness peaks have already flattened, which is less
    # than the press-on force reported in the assembly plan.
    settled_pressure_mpa = max(
        0.0, allowable_maximum_mm - smoothing_loss_mm
    ) / compliance_mm_per_mpa
    push_off_force_n = (
        friction_coefficient
        * settled_pressure_mpa
        * 1e6
        * math.pi
        * (shaft_outer_diameter_mm / 1000.0)
        * (fit_length_mm / 1000.0)
    )
    assembly_forces = {
        "governing_interference_mm": allowable_maximum_mm,
        "settled_pressure_mpa": settled_pressure_mpa,
        "push_off_force_n": push_off_force_n,
        "push_off_force_kn": push_off_force_n / 1000.0,
    }
    manufacturing = _classify_manufacturing_window(
        window_mm=max(0.0, available_tolerance_mm),
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
    )
    smoothing = {
        "shaft_roughness_rz_um": shaft_roughness_rz_um,
        "hub_roughness_rz_um": hub_roughness_rz_um,
        "smoothing_loss_mm": smoothing_loss_mm,
        "smoothing_loss_um": smoothing_loss_mm * 1000.0,
    }

    temperature_points = 41
    if maximum_operating_temperature_c == minimum_operating_temperature_c:
        temperatures = [minimum_operating_temperature_c]
    else:
        temperatures = [
            minimum_operating_temperature_c
            + i
            * (maximum_operating_temperature_c - minimum_operating_temperature_c)
            / (temperature_points - 1)
            for i in range(temperature_points)
        ]
    sweep_minimum: List[float] = []
    sweep_maximum: List[float] = []
    sweep_thermal_relief: List[float] = []
    maximum_speed_state = speed_states[maximum_speed_rpm]
    maximum_speed_growth = maximum_speed_state["growth"]
    maximum_speed_pressure_limit = maximum_speed_state["pressure_limit"]
    maximum_speed_relief_mm = float(maximum_speed_growth["interference_relief_mm"])
    for temperature_c in temperatures:
        thermal_relief_mm = _temperature_interference_relief_mm(
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            reference_temperature_c=reference_temperature_c,
            operating_temperature_c=temperature_c,
            shaft_material=shaft_props,
            hub_material=hub_props,
        )
        total_relief_mm = thermal_relief_mm + maximum_speed_relief_mm
        sweep_thermal_relief.append(thermal_relief_mm)
        sweep_minimum.append(
            max(
                0.0,
                required_operating_interference_mm
                + total_relief_mm
                + smoothing_loss_mm,
            )
        )
        sweep_maximum.append(
            min(
                reference_max_interference_mm,
                float(maximum_speed_pressure_limit["pressure_mpa"])
                * compliance_mm_per_mpa
                + total_relief_mm
                + smoothing_loss_mm,
            )
        )
    sweep_data = {
        "temperature_c": temperatures,
        "required_minimum_interference_mm": sweep_minimum,
        "allowable_maximum_interference_mm": sweep_maximum,
        "thermal_relief_mm": sweep_thermal_relief,
        "speed_relief_mm": maximum_speed_relief_mm,
        "recommended_nominal_mm": recommended_mm,
    }

    warnings: List[str] = []
    recommendations: List[str] = []
    narrow_window_threshold_mm = max(0.005, shaft_outer_diameter_mm * 0.0001)
    if rotation_only_exceeds_limit:
        warnings.append(
            "Rotation alone exceeds the requested yield margin at maximum speed."
        )
        recommendations.append(
            "Reduce speed, reduce rotating radius, or select a higher specific-strength material."
        )
    if not feasible:
        status = "unacceptable"
        recommendations.append(
            "Increase fit length or friction, reduce torque or slip safety factor, thicken the hub, or use stronger materials to create a feasible interference window."
        )
    elif available_tolerance_mm < narrow_window_threshold_mm:
        status = "marginal"
        warnings.append(
            "The calculated interference window is narrow relative to normal manufacturing variation."
        )
        recommendations.append(
            "Widen the design window before releasing tolerances; fit length and hub strength are usually the cleanest levers."
        )
    else:
        status = "acceptable"
        recommendations.append(
            "Use the calculated lower and upper values as the diametral interference limits, then allocate shaft and bore tolerances around the midpoint target."
        )
    if feasible and assembly["warnings"] and status == "acceptable":
        status = "marginal"
    if feasible and not manufacturing["practical"]:
        if status == "acceptable":
            status = "marginal"
        warnings.append(
            f"Splitting the window evenly leaves {manufacturing['per_part_window_um']:.1f} "
            f"um per part ({manufacturing['verdict']}), which is tighter than routine "
            "shop practice."
        )
        recommendations.append(
            "Widen the window before releasing tolerances, or plan on matched machining "
            "or select-fit assembly."
        )
    if bool(load_requirement["length_credit_applied"]):
        warnings.append(
            f"Only {effective_fit_length_mm:.1f} mm of the {fit_length_mm:.1f} mm contact "
            f"length is credited. Pressure and micro-slip concentrate at the fit ends, so "
            f"length past L/d = {length_credit_ratio:.1f} adds little capacity."
        )
    if smoothing_loss_mm > 0.0:
        warnings.append(
            f"Surface roughness removes {smoothing_loss_mm * 1000.0:.1f} um of diametral "
            "interference at assembly. Both interference limits already include it."
        )
    else:
        warnings.append(
            "Surface roughness is set to zero, so no smoothing loss is charged. Real "
            "ground surfaces lose roughly 4 to 8 um of diametral interference."
        )
    if maximum_speed_rpm > 0.0:
        warnings.append(
            "Centrifugal growth uses uniform plane-stress disk/annulus theory; stepped hubs, shoulders, and axial constraints require FEA or test correlation."
        )
    warnings.append(
        "Friction is uncertain in service. Use a coefficient supported by the actual finish, coating, lubrication, and assembly process."
    )
    if hub_outer_diameter_mm / shaft_outer_diameter_mm < 1.3:
        warnings.append(
            "The hub wall is relatively thin; local geometry and end effects may matter."
        )
    for member_label, member_props in (("Shaft", shaft_props), ("Hub", hub_props)):
        if str(member_props["failure_criterion"]) == BRITTLE:
            warnings.append(
                f"{member_label} material is brittle, so it is checked with Coulomb-Mohr "
                "against separate tensile and compressive strengths rather than von Mises."
            )
    warnings.extend(assembly["warnings"])

    governing_mode = (
        f"Lower: {governing_lower['label']}; upper: "
        f"{governing_upper['label']} ({governing_upper.get('governing_member', 'member')})."
    )
    geometry = {
        "shaft_outer_diameter_mm": shaft_outer_diameter_mm,
        "shaft_inner_diameter_mm": shaft_inner_diameter_mm,
        "hub_outer_diameter_mm": hub_outer_diameter_mm,
        "fit_length_mm": fit_length_mm,
        "effective_fit_length_mm": effective_fit_length_mm,
        "length_credit_ratio": length_credit_ratio,
        "length_to_diameter_ratio": fit_length_mm / shaft_outer_diameter_mm,
        "hub_to_shaft_diameter_ratio": hub_outer_diameter_mm
        / shaft_outer_diameter_mm,
        "shaft_member_type": "solid" if shaft_inner_diameter_mm <= 0.0 else "hollow",
        "maximum_speed_rpm": maximum_speed_rpm,
    }

    subst_required_contact_pressure_mpa = (
        "p_{req} = \\frac{SF_s\\sqrt{(2T/d)^2+F_a^2}}{\\mu\\pi dL}"
        f" = \\frac{{{required_slip_sf:.2f}\\sqrt{{(2({required_torque_nm:.1f})/"
        f"{diameter_m:.4f})^2+{abs(applied_axial_force_n):.1f}^2}}}}"
        f"{{{friction_coefficient:.3f}\\pi({diameter_m:.4f})({effective_fit_length_mm/1000.0:.4f})}}"
        "\\times10^{-6}"
        f" = {required_pressure_mpa:.2f}\\text{{ MPa}}"
    )
    subst_required_interference_min_mm = (
        "\\delta_{ref,min} = \\delta_{op,req}+\\Delta\\delta_T+\\Delta\\delta_\\omega"
        f" = {required_operating_interference_mm:.4f}+"
        f"{float(governing_lower['thermal_relief_mm']):.4f}+"
        f"{float(governing_lower['speed_relief_mm']):.4f}"
        f" = {required_minimum_mm:.4f}\\text{{ mm}}"
    )
    subst_allowable_interference_max_mm = (
        "\\delta_{ref,max} = p_{allow}C_d+\\Delta\\delta"
        f" = {float(governing_upper['pressure_limit_mpa']):.2f}"
        f"({compliance_mm_per_mpa:.6f})+{float(governing_upper['total_relief_mm']):.4f}"
        f" = {allowable_maximum_mm:.4f}\\text{{ mm}}"
    )
    if recommended_mm is not None:
        subst_recommended_interference_mm = (
            "\\delta_{target} = \\frac{\\delta_{min}+\\delta_{max}}{2}"
            f" = \\frac{{{required_minimum_mm:.4f}+{allowable_maximum_mm:.4f}}}{{2}}"
            f" = {recommended_mm:.4f}\\text{{ mm}}"
        )
    else:
        subst_recommended_interference_mm = (
            "\\delta_{ref,min} > \\delta_{ref,max}\\;\\Rightarrow\\;"
            "\\text{no feasible elastic interference range}"
        )

    return {
        "design_range": design_range,
        "load_requirement": load_requirement,
        "service_states": service_states,
        "reference_state": reference_state,
        "assembly": assembly,
        "assembly_forces": assembly_forces,
        "manufacturing": manufacturing,
        "smoothing": smoothing,
        "compliance": compliance,
        "geometry": geometry,
        "materials": {"shaft": shaft_props, "hub": hub_props},
        "sweep_data": sweep_data,
        "status": status,
        "governing_mode": governing_mode,
        "warnings": list(dict.fromkeys(warnings)),
        "recommendations": list(dict.fromkeys(recommendations)),
        "shaft_material_name": str(shaft_props["display_name"]),
        "hub_material_name": str(hub_props["display_name"]),
        "subst_required_contact_pressure_mpa": subst_required_contact_pressure_mpa,
        "subst_required_interference_min_mm": subst_required_interference_min_mm,
        "subst_allowable_interference_max_mm": subst_allowable_interference_max_mm,
        "subst_recommended_interference_mm": subst_recommended_interference_mm,
    }
