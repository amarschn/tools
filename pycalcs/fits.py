"""
ISO 286 fits and tolerances calculations.

Provides ISO hole-basis fit limits using tolerance grades and shaft
fundamental deviation formulas.
"""

from __future__ import annotations

import math
import re
from typing import Dict, Tuple

ISO_DIAMETER_STEPS_MM: Tuple[Tuple[float, float], ...] = (
    (1.0, 3.0),
    (3.0, 6.0),
    (6.0, 10.0),
    (10.0, 18.0),
    (18.0, 30.0),
    (30.0, 50.0),
    (50.0, 80.0),
    (80.0, 120.0),
    (120.0, 180.0),
    (180.0, 250.0),
    (250.0, 315.0),
    (315.0, 400.0),
    (400.0, 500.0),
)

IT_GRADE_MULTIPLIERS = {
    5: 7.0,
    6: 10.0,
    7: 16.0,
    8: 25.0,
    9: 40.0,
    10: 64.0,
    11: 100.0,
    12: 160.0,
    13: 250.0,
    14: 400.0,
    15: 640.0,
    16: 1000.0,
}

SHAFT_DEVIATION_MODELS = {
    "a": (-50.0, 0.44),
    "b": (-40.0, 0.44),
    "c": (-25.0, 0.44),
    "d": (-16.0, 0.44),
    "e": (-11.0, 0.41),
    "f": (-5.5, 0.41),
    "g": (-2.5, 0.34),
    "k": (2.5, 0.34),
    "m": (7.0, 0.34),
    "n": (10.0, 0.34),
    "p": (16.0, 0.34),
    "r": (25.0, 0.34),
    "s": (40.0, 0.34),
    "t": (63.0, 0.34),
}


def _find_diameter_step(nominal_diameter_mm: float) -> Tuple[float, float, float]:
    """
    Locate the ISO diameter step and geometric mean for a nominal diameter.

    Parameters
    ----------
    nominal_diameter_mm : float
        Nominal diameter in millimeters.

    Returns
    -------
    Tuple[float, float, float]
        (step_min_mm, step_max_mm, step_geometric_mean_mm)
    """
    if nominal_diameter_mm <= 0:
        raise ValueError("Nominal diameter must be greater than zero.")

    for step_min, step_max in ISO_DIAMETER_STEPS_MM:
        if step_min <= nominal_diameter_mm <= step_max:
            step_geom = math.sqrt(step_min * step_max)
            return step_min, step_max, step_geom

    raise ValueError(
        "Nominal diameter is outside the supported ISO 286 ranges (1-500 mm)."
    )


def _standard_tolerance_unit_um(geometric_diameter_mm: float) -> float:
    """
    Compute the ISO 286 standard tolerance unit (i) in micrometers.

    Parameters
    ----------
    geometric_diameter_mm : float
        Geometric mean diameter for the step range (mm).

    Returns
    -------
    float
        Standard tolerance unit i in micrometers.
    """
    return 0.45 * geometric_diameter_mm ** (1.0 / 3.0) + 0.001 * geometric_diameter_mm


def _it_grade_tolerance_um(grade: int, geometric_diameter_mm: float) -> float:
    """
    Compute the ISO 286 IT tolerance for a grade in micrometers.

    Parameters
    ----------
    grade : int
        IT grade (5-16 supported).
    geometric_diameter_mm : float
        Geometric mean diameter for the step range (mm).

    Returns
    -------
    float
        IT tolerance in micrometers.
    """
    if grade not in IT_GRADE_MULTIPLIERS:
        raise ValueError(
            "IT grade must be one of 5-16 for this tool (got {}).".format(grade)
        )

    unit = _standard_tolerance_unit_um(geometric_diameter_mm)
    return IT_GRADE_MULTIPLIERS[grade] * unit


def _parse_fit_zone(zone: str) -> Tuple[str, int]:
    """
    Parse a fit zone string like "H7" or "js6" into letter + grade.

    Parameters
    ----------
    zone : str
        Fit zone string containing a letter code and grade number.

    Returns
    -------
    Tuple[str, int]
        (letter_code, grade)
    """
    match = re.match(r"^([A-Za-z]+)(\d+)$", zone.strip())
    if not match:
        raise ValueError(f"Invalid fit zone format: '{zone}'.")

    letters = match.group(1)
    grade = int(match.group(2))
    return letters, grade


def _hole_deviations_um(letter: str, tolerance_um: float) -> Tuple[float, float]:
    """
    Compute hole deviations (EI, ES) for supported hole letters.

    Parameters
    ----------
    letter : str
        Hole letter (H or JS supported).
    tolerance_um : float
        IT tolerance for the hole zone (micrometers).

    Returns
    -------
    Tuple[float, float]
        (EI, ES) in micrometers.
    """
    letter_upper = letter.upper()

    if letter_upper == "H":
        return 0.0, tolerance_um
    if letter_upper == "JS":
        half = 0.5 * tolerance_um
        return -half, half

    raise ValueError(
        "Only hole letters H and JS are supported in this tool (got {}).".format(letter)
    )


def _shaft_fundamental_deviation_um(
    letter: str,
    geometric_diameter_mm: float,
    tolerance_um: float,
) -> float:
    """
    Compute shaft upper deviation (es) for supported letters.

    Parameters
    ----------
    letter : str
        Shaft letter code.
    geometric_diameter_mm : float
        Geometric mean diameter for the step range (mm).
    tolerance_um : float
        IT tolerance for the shaft zone (micrometers).

    Returns
    -------
    float
        Upper deviation es in micrometers.
    """
    letter_lower = letter.lower()

    if letter_lower == "h":
        return 0.0
    if letter_lower in {"js", "j"}:
        return 0.5 * tolerance_um

    if letter_lower not in SHAFT_DEVIATION_MODELS:
        raise ValueError(
            "Unsupported shaft letter for ISO 286 hole-basis fits: {}".format(letter)
        )

    coefficient, exponent = SHAFT_DEVIATION_MODELS[letter_lower]
    return coefficient * geometric_diameter_mm ** exponent


def calculate_iso_fit(nominal_diameter_mm: float, fit_designation: str) -> Dict[str, float]:
    """
    Compute ISO 286 hole-basis fit limits and clearance range.

    Uses ISO 286-1/2 tolerance grade equations with the standard tolerance unit
    (i) and power-law fundamental deviations for common shaft positions. This
    implementation is scoped to hole-basis fits with H/JS holes and shaft letters
    a-h, js/j, k, m, n, p, r, s, t. The "j" position is approximated as a
    centered (js) zone.

    ---Parameters---
    nominal_diameter_mm : float
        Basic size D in millimeters.
    fit_designation : str
        ISO fit designation like "H7/h6" or "H7/js6".

    ---Returns---
    hole_upper_dev_mm : float
        Upper hole deviation ES (mm).
    hole_lower_dev_mm : float
        Lower hole deviation EI (mm).
    shaft_upper_dev_mm : float
        Upper shaft deviation es (mm).
    shaft_lower_dev_mm : float
        Lower shaft deviation ei (mm).
    hole_min_mm : float
        Minimum hole size (mm).
    hole_max_mm : float
        Maximum hole size (mm).
    shaft_min_mm : float
        Minimum shaft size (mm).
    shaft_max_mm : float
        Maximum shaft size (mm).
    min_clearance_mm : float
        Minimum clearance (mm), negative indicates interference.
    max_clearance_mm : float
        Maximum clearance (mm).

    ---LaTeX---
    i = 0.45 D^{1/3} + 0.001 D
    IT = k_{IT} i
    EI_H = 0, \quad ES_H = IT
    es = K D^{n}, \quad ei = es - IT
    D_{hole,min} = D + EI, \quad D_{hole,max} = D + ES
    D_{shaft,min} = D + ei, \quad D_{shaft,max} = D + es
    C_{min} = D_{hole,min} - D_{shaft,max}
    C_{max} = D_{hole,max} - D_{shaft,min}
    """
    step_min, step_max, step_geom = _find_diameter_step(nominal_diameter_mm)

    try:
        hole_zone, shaft_zone = fit_designation.split("/")
    except ValueError as exc:
        raise ValueError(
            "Fit designation must be in the form 'H7/h6'."
        ) from exc

    hole_letter, hole_grade = _parse_fit_zone(hole_zone)
    shaft_letter, shaft_grade = _parse_fit_zone(shaft_zone)

    hole_tol_um = _it_grade_tolerance_um(hole_grade, step_geom)
    shaft_tol_um = _it_grade_tolerance_um(shaft_grade, step_geom)

    hole_lower_um, hole_upper_um = _hole_deviations_um(hole_letter, hole_tol_um)

    shaft_upper_um = _shaft_fundamental_deviation_um(
        shaft_letter, step_geom, shaft_tol_um
    )
    shaft_lower_um = shaft_upper_um - shaft_tol_um

    hole_upper_mm = hole_upper_um / 1000.0
    hole_lower_mm = hole_lower_um / 1000.0
    shaft_upper_mm = shaft_upper_um / 1000.0
    shaft_lower_mm = shaft_lower_um / 1000.0

    hole_min_mm = nominal_diameter_mm + hole_lower_mm
    hole_max_mm = nominal_diameter_mm + hole_upper_mm
    shaft_min_mm = nominal_diameter_mm + shaft_lower_mm
    shaft_max_mm = nominal_diameter_mm + shaft_upper_mm

    min_clearance_mm = hole_min_mm - shaft_max_mm
    max_clearance_mm = hole_max_mm - shaft_min_mm

    def fmt(value: float) -> str:
        return f"{value:.6f}"

    return {
        "hole_upper_dev_mm": hole_upper_mm,
        "hole_lower_dev_mm": hole_lower_mm,
        "shaft_upper_dev_mm": shaft_upper_mm,
        "shaft_lower_dev_mm": shaft_lower_mm,
        "hole_min_mm": hole_min_mm,
        "hole_max_mm": hole_max_mm,
        "shaft_min_mm": shaft_min_mm,
        "shaft_max_mm": shaft_max_mm,
        "min_clearance_mm": min_clearance_mm,
        "max_clearance_mm": max_clearance_mm,
        "subst_hole_upper_dev_mm": f"ES = {fmt(hole_upper_mm)} \\text{{ mm}}",
        "subst_hole_lower_dev_mm": f"EI = {fmt(hole_lower_mm)} \\text{{ mm}}",
        "subst_shaft_upper_dev_mm": f"es = {fmt(shaft_upper_mm)} \\text{{ mm}}",
        "subst_shaft_lower_dev_mm": f"ei = {fmt(shaft_lower_mm)} \\text{{ mm}}",
        "subst_hole_min_mm": f"D_{{hole,min}} = {fmt(hole_min_mm)} \\text{{ mm}}",
        "subst_hole_max_mm": f"D_{{hole,max}} = {fmt(hole_max_mm)} \\text{{ mm}}",
        "subst_shaft_min_mm": f"D_{{shaft,min}} = {fmt(shaft_min_mm)} \\text{{ mm}}",
        "subst_shaft_max_mm": f"D_{{shaft,max}} = {fmt(shaft_max_mm)} \\text{{ mm}}",
        "subst_min_clearance_mm": f"C_{{min}} = {fmt(min_clearance_mm)} \\text{{ mm}}",
        "subst_max_clearance_mm": f"C_{{max}} = {fmt(max_clearance_mm)} \\text{{ mm}}",
    }
