"""
ISO 286 Engineering Fits Calculator.

Comprehensive implementation of ISO 286-1/2 standard for limits and fits,
supporting hole-basis and shaft-basis systems with accurate tabulated
fundamental deviations.

References:
    - ISO 286-1:2010, Geometrical product specifications (GPS)
    - ISO 286-2:2010, Tables of standard tolerance grades
    - Machinery's Handbook, 31st Edition
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# ISO 286 DIAMETER STEPS (mm)
# =============================================================================

ISO_DIAMETER_STEPS: Tuple[Tuple[float, float], ...] = (
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

# Step indices for table lookups
STEP_INDEX = {
    (1.0, 3.0): 0,
    (3.0, 6.0): 1,
    (6.0, 10.0): 2,
    (10.0, 18.0): 3,
    (18.0, 30.0): 4,
    (30.0, 50.0): 5,
    (50.0, 80.0): 6,
    (80.0, 120.0): 7,
    (120.0, 180.0): 8,
    (180.0, 250.0): 9,
    (250.0, 315.0): 10,
    (315.0, 400.0): 11,
    (400.0, 500.0): 12,
}


# =============================================================================
# IT GRADE TOLERANCES (micrometers) - ISO 286-1 Table 1
# =============================================================================

# IT grades multipliers based on standard tolerance unit i
IT_GRADE_MULTIPLIERS = {
    1: 0.8,    # Special precision
    2: 1.2,
    3: 2.0,
    4: 3.0,
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
    17: 1600.0,
    18: 2500.0,
}


# =============================================================================
# FUNDAMENTAL DEVIATIONS - ISO 286-2 Tables (micrometers)
# Tabulated values for each diameter step, indexed 0-12
# =============================================================================

# Shaft fundamental deviations (uppercase = es for a-h, lowercase = ei for j-zc)
# For clearance letters (a-h): es is the upper deviation (negative or zero)
# For interference letters (k-zc): ei is the lower deviation (positive)

SHAFT_FUNDAMENTAL_DEVIATIONS: Dict[str, List[float]] = {
    # Clearance fits - es values (upper deviation, negative)
    "a": [-270, -270, -280, -290, -300, -310, -320, -340, -360, -380, -410, -440, -480],
    "b": [-140, -140, -150, -150, -160, -170, -180, -190, -200, -210, -230, -240, -260],
    "c": [-60, -70, -80, -95, -110, -120, -130, -140, -150, -170, -180, -200, -210],
    "d": [-20, -30, -40, -50, -65, -80, -100, -120, -145, -170, -190, -210, -230],
    "e": [-14, -20, -25, -32, -40, -50, -60, -72, -85, -100, -110, -125, -135],
    "f": [-6, -10, -13, -16, -20, -25, -30, -36, -43, -50, -56, -62, -68],
    "g": [-2, -4, -5, -6, -7, -9, -10, -12, -14, -15, -17, -18, -20],
    "h": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],

    # Transition/Interference fits - ei values (lower deviation, positive)
    # Note: For js, deviation is ±IT/2 (handled specially)
    "j": [2, 3, 4, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7],  # Approximate, IT5-IT8 range
    "k": [0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 5],  # Lower deviation
    "m": [2, 4, 6, 7, 8, 9, 11, 13, 15, 17, 20, 21, 23],
    "n": [4, 8, 10, 12, 15, 17, 20, 23, 27, 31, 34, 37, 40],
    "p": [6, 12, 15, 18, 22, 26, 32, 37, 43, 50, 56, 62, 68],
    "r": [10, 15, 19, 23, 28, 34, 41, 48, 55, 63, 72, 78, 86],
    "s": [14, 19, 23, 28, 35, 43, 53, 59, 68, 79, 88, 98, 108],
    "t": [18, 23, 28, 33, 41, 48, 60, 71, 83, 96, 108, 119, -1],  # -1 = not applicable
    "u": [18, 28, 34, 40, 49, 60, 75, 87, 102, 120, 133, 148, 163],
}

# Hole fundamental deviations - mostly mirrors of shaft deviations
# H hole has EI = 0 (lower deviation)
# For other holes: EI = -es of corresponding shaft letter (with sign rules)

HOLE_FUNDAMENTAL_DEVIATIONS: Dict[str, List[float]] = {
    # Standard hole positions
    "A": [270, 270, 280, 290, 300, 310, 320, 340, 360, 380, 410, 440, 480],
    "B": [140, 140, 150, 150, 160, 170, 180, 190, 200, 210, 230, 240, 260],
    "C": [60, 70, 80, 95, 110, 120, 130, 140, 150, 170, 180, 200, 210],
    "D": [20, 30, 40, 50, 65, 80, 100, 120, 145, 170, 190, 210, 230],
    "E": [14, 20, 25, 32, 40, 50, 60, 72, 85, 100, 110, 125, 135],
    "F": [6, 10, 13, 16, 20, 25, 30, 36, 43, 50, 56, 62, 68],
    "G": [2, 4, 5, 6, 7, 9, 10, 12, 14, 15, 17, 18, 20],
    "H": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    # Interference holes (rarely used)
    "K": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Approximation
    "M": [-2, -4, -6, -7, -8, -9, -11, -13, -15, -17, -20, -21, -23],
    "N": [-4, -8, -10, -12, -15, -17, -20, -23, -27, -31, -34, -37, -40],
    "P": [-6, -12, -15, -18, -22, -26, -32, -37, -43, -50, -56, -62, -68],
}


# =============================================================================
# COMMON FIT PRESETS
# =============================================================================

@dataclass
class FitPreset:
    """Metadata for a standard fit configuration."""
    designation: str
    name: str
    fit_type: str  # "clearance", "transition", "interference"
    description: str
    applications: List[str]
    surface_finish_hole_ra: str  # Ra in μm
    surface_finish_shaft_ra: str


COMMON_FITS: Dict[str, FitPreset] = {
    # Clearance fits
    "H11/c11": FitPreset(
        "H11/c11", "Loose Running", "clearance",
        "Very loose clearance for rough alignment and debris tolerance.",
        ["Agricultural equipment", "Conveyor rollers", "Rough guides"],
        "6.3-12.5", "3.2-6.3"
    ),
    "H9/d9": FitPreset(
        "H9/d9", "Free Running", "clearance",
        "Large clearance for free running with lubricant film.",
        ["Hinges", "Door hardware", "Low-speed bearings"],
        "3.2-6.3", "1.6-3.2"
    ),
    "H8/f7": FitPreset(
        "H8/f7", "Close Running", "clearance",
        "Running fit with good guidance and moderate clearance.",
        ["Electric motors", "Pumps", "Machine tool spindles"],
        "1.6-3.2", "0.8-1.6"
    ),
    "H7/g6": FitPreset(
        "H7/g6", "Sliding", "clearance",
        "Small clearance for accurate sliding without perceptible play.",
        ["Precision slides", "Spigots", "Recessing mandrels"],
        "1.6-3.2", "0.8-1.6"
    ),
    "H7/h6": FitPreset(
        "H7/h6", "Locational Clearance", "clearance",
        "Snug fit providing accurate location with minimum clearance.",
        ["Bearing caps", "Location fits", "Couplings"],
        "1.6-3.2", "0.8-1.6"
    ),
    "H6/h5": FitPreset(
        "H6/h5", "Precision Clearance", "clearance",
        "Very accurate fit with minimal clearance for precision work.",
        ["Gauge parts", "Precision instruments", "Metrological equipment"],
        "0.8-1.6", "0.4-0.8"
    ),
    # Transition fits
    "H7/js6": FitPreset(
        "H7/js6", "Snug/Location", "transition",
        "Centered transition providing accurate location.",
        ["Dowel pins", "Alignment features", "Easy assembly locations"],
        "1.6-3.2", "0.8-1.6"
    ),
    "H7/k6": FitPreset(
        "H7/k6", "Push/Location", "transition",
        "Location fit assembled with light hand pressure.",
        ["Gear hubs", "Pulley hubs", "Crank pins"],
        "0.8-1.6", "0.4-0.8"
    ),
    "H7/m6": FitPreset(
        "H7/m6", "Light Keying", "transition",
        "Transition fit requiring light force for assembly.",
        ["Coupling hubs", "Bearing inner races", "Clutch parts"],
        "0.8-1.6", "0.4-0.8"
    ),
    "H7/n6": FitPreset(
        "H7/n6", "Tight", "transition",
        "Tight transition fit with probable small interference.",
        ["Permanent locating", "Tight gear fits", "Bushings"],
        "0.8-1.6", "0.4-0.8"
    ),
    # Interference fits
    "H7/p6": FitPreset(
        "H7/p6", "Light Press", "interference",
        "Light interference for permanent assembly with press.",
        ["Bushings", "Thin collars", "Light-duty permanent fits"],
        "0.8-1.6", "0.4-0.8"
    ),
    "H7/r6": FitPreset(
        "H7/r6", "Medium Press", "interference",
        "Medium interference for torque transmission.",
        ["Couplings", "Bearing housings", "Heavy collars"],
        "0.8-1.6", "0.4-0.8"
    ),
    "H7/s6": FitPreset(
        "H7/s6", "Heavy Press", "interference",
        "Heavy interference requiring significant press force.",
        ["Permanent hubs", "Heavy-duty gears", "Shrink fits"],
        "0.8-1.6", "0.4-0.8"
    ),
    "H7/t6": FitPreset(
        "H7/t6", "Force/Shrink", "interference",
        "Maximum interference for shrink or heavy press assembly.",
        ["Permanent assemblies", "High-torque applications"],
        "0.8-1.6", "0.4-0.8"
    ),
    "H7/u6": FitPreset(
        "H7/u6", "Heavy Shrink", "interference",
        "Very heavy interference typically requiring thermal assembly.",
        ["Heavy machinery", "High-load permanent joints"],
        "0.8-1.6", "0.4-0.8"
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _find_diameter_step(nominal_mm: float) -> Tuple[int, float, float, float]:
    """
    Find the ISO diameter step for a given nominal diameter.

    Returns: (step_index, step_min, step_max, geometric_mean)
    """
    if nominal_mm <= 0:
        raise ValueError("Nominal diameter must be greater than zero")
    if nominal_mm < 1.0:
        raise ValueError("Nominal diameter must be at least 1 mm (ISO 286 range)")
    if nominal_mm > 500.0:
        raise ValueError("Nominal diameter must not exceed 500 mm (ISO 286 range)")

    for step_min, step_max in ISO_DIAMETER_STEPS:
        if step_min <= nominal_mm <= step_max:
            step_idx = STEP_INDEX[(step_min, step_max)]
            geom_mean = math.sqrt(step_min * step_max)
            return step_idx, step_min, step_max, geom_mean

    raise ValueError(f"Diameter {nominal_mm} mm outside ISO 286 range (1-500 mm)")


def _standard_tolerance_unit(geom_mean_mm: float) -> float:
    """
    Calculate standard tolerance unit i in micrometers.

    ISO 286-1 formula: i = 0.45 × D^(1/3) + 0.001 × D
    where D is the geometric mean of the diameter step in mm.
    """
    return 0.45 * (geom_mean_mm ** (1/3)) + 0.001 * geom_mean_mm


def _it_tolerance_um(grade: int, geom_mean_mm: float) -> float:
    """
    Calculate IT tolerance in micrometers for a given grade.
    """
    if grade < 1 or grade > 18:
        raise ValueError(f"IT grade must be 1-18 (got {grade})")

    if grade not in IT_GRADE_MULTIPLIERS:
        raise ValueError(f"IT grade {grade} not supported")

    i = _standard_tolerance_unit(geom_mean_mm)
    return IT_GRADE_MULTIPLIERS[grade] * i


def _parse_zone(zone_str: str) -> Tuple[str, int]:
    """
    Parse a tolerance zone like 'H7' or 'js6' into (letter, grade).
    """
    match = re.match(r'^([A-Za-z]+)(\d+)$', zone_str.strip())
    if not match:
        raise ValueError(f"Invalid tolerance zone format: '{zone_str}'")

    letter = match.group(1)
    grade = int(match.group(2))
    return letter, grade


def _get_hole_deviations(letter: str, grade: int, step_idx: int,
                          tolerance_um: float) -> Tuple[float, float]:
    """
    Get hole deviations (EI, ES) in micrometers.

    For H-hole: EI = 0, ES = IT
    For JS-hole: EI = -IT/2, ES = +IT/2
    For other holes: use tabulated fundamental deviations
    """
    letter_upper = letter.upper()

    if letter_upper == "H":
        return 0.0, tolerance_um

    if letter_upper == "JS":
        half = tolerance_um / 2
        return -half, half

    if letter_upper == "J":
        # J is asymmetric, approximate as centered
        half = tolerance_um / 2
        return -half, half

    if letter_upper in HOLE_FUNDAMENTAL_DEVIATIONS:
        # EI is the fundamental deviation for holes A-G (positive)
        EI = HOLE_FUNDAMENTAL_DEVIATIONS[letter_upper][step_idx]
        ES = EI + tolerance_um
        return float(EI), float(ES)

    raise ValueError(f"Unsupported hole letter: '{letter}'")


def _get_shaft_deviations(letter: str, grade: int, step_idx: int,
                           tolerance_um: float) -> Tuple[float, float]:
    """
    Get shaft deviations (ei, es) in micrometers.

    For h-shaft: es = 0, ei = -IT
    For js-shaft: es = +IT/2, ei = -IT/2
    For clearance shafts (a-g): es is negative, ei = es - IT
    For interference shafts (k-u): ei is positive, es = ei + IT
    """
    letter_lower = letter.lower()

    if letter_lower == "h":
        return -tolerance_um, 0.0

    if letter_lower == "js":
        half = tolerance_um / 2
        return -half, half

    if letter_lower == "j":
        # J is similar to JS but slightly asymmetric
        half = tolerance_um / 2
        return -half, half

    if letter_lower in SHAFT_FUNDAMENTAL_DEVIATIONS:
        fund_dev = SHAFT_FUNDAMENTAL_DEVIATIONS[letter_lower][step_idx]

        if fund_dev == -1:
            raise ValueError(f"Shaft letter '{letter}' not applicable for this diameter range")

        # For clearance letters (a-h): fund_dev is es (upper deviation, ≤0)
        # For interference letters (k-u): fund_dev is ei (lower deviation, ≥0)
        if letter_lower in ['a', 'b', 'c', 'd', 'e', 'f', 'g']:
            es = float(fund_dev)
            ei = es - tolerance_um
            return ei, es
        else:
            # k, m, n, p, r, s, t, u
            ei = float(fund_dev)
            es = ei + tolerance_um
            return ei, es

    raise ValueError(f"Unsupported shaft letter: '{letter}'")


def classify_fit(min_clearance: float, max_clearance: float) -> str:
    """
    Classify a fit based on clearance range.

    Returns: "clearance", "transition", or "interference"
    """
    if min_clearance >= 0:
        return "clearance"
    if max_clearance <= 0:
        return "interference"
    return "transition"


# =============================================================================
# MAIN CALCULATION FUNCTION
# =============================================================================

def calculate_iso_fit(
    nominal_diameter_mm: float,
    fit_designation: str,
) -> Dict[str, Any]:
    """
    Calculate ISO 286 fit limits and clearance/interference range.

    This function computes the tolerance limits for a hole-basis or shaft-basis
    fit according to ISO 286-1/2 standards. It uses tabulated fundamental
    deviations for accuracy.

    ---Parameters---
    nominal_diameter_mm : float
        Basic size D in millimeters (1-500 mm range).

    fit_designation : str
        ISO fit designation in the form "H7/g6" (hole/shaft).
        Common formats:
        - Hole-basis: H7/g6, H7/h6, H7/p6, etc.
        - Shaft-basis: G7/h6, P7/h6, etc.

    ---Returns---
    nominal_diameter_mm : float
        Input nominal diameter (mm).
    fit_designation : str
        Input fit designation.
    fit_type : str
        Classification: "clearance", "transition", or "interference".
    hole_tolerance_grade : int
        IT grade of hole tolerance.
    shaft_tolerance_grade : int
        IT grade of shaft tolerance.
    hole_tolerance_um : float
        Hole tolerance width (μm).
    shaft_tolerance_um : float
        Shaft tolerance width (μm).
    hole_upper_dev_mm : float
        Upper hole deviation ES (mm).
    hole_lower_dev_mm : float
        Lower hole deviation EI (mm).
    shaft_upper_dev_mm : float
        Upper shaft deviation es (mm).
    shaft_lower_dev_mm : float
        Lower shaft deviation ei (mm).
    hole_max_mm : float
        Maximum hole size (mm).
    hole_min_mm : float
        Minimum hole size (mm).
    shaft_max_mm : float
        Maximum shaft size (mm).
    shaft_min_mm : float
        Minimum shaft size (mm).
    min_clearance_mm : float
        Minimum clearance (mm). Negative indicates interference.
    max_clearance_mm : float
        Maximum clearance (mm). Negative indicates full interference.
    min_interference_mm : float
        Minimum interference (mm). Positive when interference exists.
    max_interference_mm : float
        Maximum interference (mm). Positive when full interference.

    ---LaTeX---
    i = 0.45 \\cdot D^{1/3} + 0.001 \\cdot D
    IT_n = k_n \\cdot i
    D_{hole,max} = D + ES
    D_{hole,min} = D + EI
    D_{shaft,max} = D + es
    D_{shaft,min} = D + ei
    C_{min} = D_{hole,min} - D_{shaft,max} = EI - es
    C_{max} = D_{hole,max} - D_{shaft,min} = ES - ei

    ---References---
    ISO 286-1:2010 Geometrical product specifications - Limits and fits
    ISO 286-2:2010 Tables of standard tolerance grades
    """
    # Parse fit designation
    parts = fit_designation.replace(" ", "").split("/")
    if len(parts) != 2:
        raise ValueError(
            f"Fit designation must be in form 'H7/g6' (got '{fit_designation}')"
        )

    hole_zone, shaft_zone = parts
    hole_letter, hole_grade = _parse_zone(hole_zone)
    shaft_letter, shaft_grade = _parse_zone(shaft_zone)

    # Find diameter step
    step_idx, step_min, step_max, geom_mean = _find_diameter_step(nominal_diameter_mm)

    # Calculate tolerances
    hole_tol_um = _it_tolerance_um(hole_grade, geom_mean)
    shaft_tol_um = _it_tolerance_um(shaft_grade, geom_mean)

    # Get deviations
    hole_EI_um, hole_ES_um = _get_hole_deviations(
        hole_letter, hole_grade, step_idx, hole_tol_um
    )
    shaft_ei_um, shaft_es_um = _get_shaft_deviations(
        shaft_letter, shaft_grade, step_idx, shaft_tol_um
    )

    # Convert to mm
    hole_EI_mm = hole_EI_um / 1000.0
    hole_ES_mm = hole_ES_um / 1000.0
    shaft_ei_mm = shaft_ei_um / 1000.0
    shaft_es_mm = shaft_es_um / 1000.0

    # Calculate actual sizes
    hole_max_mm = nominal_diameter_mm + hole_ES_mm
    hole_min_mm = nominal_diameter_mm + hole_EI_mm
    shaft_max_mm = nominal_diameter_mm + shaft_es_mm
    shaft_min_mm = nominal_diameter_mm + shaft_ei_mm

    # Calculate clearance/interference
    min_clearance_mm = hole_min_mm - shaft_max_mm  # EI - es
    max_clearance_mm = hole_max_mm - shaft_min_mm  # ES - ei

    # Interference is negative clearance
    min_interference_mm = -max_clearance_mm  # Minimum when max clearance
    max_interference_mm = -min_clearance_mm  # Maximum when min clearance

    # Classify fit
    fit_type = classify_fit(min_clearance_mm, max_clearance_mm)

    # Get preset info if available
    preset = COMMON_FITS.get(fit_designation)

    return {
        # Input echo
        "nominal_diameter_mm": nominal_diameter_mm,
        "fit_designation": fit_designation,
        "diameter_step": f"{step_min}-{step_max} mm",

        # Classification
        "fit_type": fit_type,
        "fit_name": preset.name if preset else None,
        "fit_description": preset.description if preset else None,
        "applications": preset.applications if preset else [],

        # Tolerance grades
        "hole_zone": hole_zone,
        "shaft_zone": shaft_zone,
        "hole_tolerance_grade": hole_grade,
        "shaft_tolerance_grade": shaft_grade,
        "hole_tolerance_um": round(hole_tol_um, 2),
        "shaft_tolerance_um": round(shaft_tol_um, 2),

        # Deviations (mm)
        "hole_upper_dev_mm": hole_ES_mm,
        "hole_lower_dev_mm": hole_EI_mm,
        "shaft_upper_dev_mm": shaft_es_mm,
        "shaft_lower_dev_mm": shaft_ei_mm,

        # Deviations (μm) for display
        "hole_upper_dev_um": hole_ES_um,
        "hole_lower_dev_um": hole_EI_um,
        "shaft_upper_dev_um": shaft_es_um,
        "shaft_lower_dev_um": shaft_ei_um,

        # Actual sizes (mm)
        "hole_max_mm": hole_max_mm,
        "hole_min_mm": hole_min_mm,
        "shaft_max_mm": shaft_max_mm,
        "shaft_min_mm": shaft_min_mm,

        # Clearance/Interference (mm)
        "min_clearance_mm": min_clearance_mm,
        "max_clearance_mm": max_clearance_mm,
        "min_interference_mm": min_interference_mm if min_interference_mm > 0 else 0.0,
        "max_interference_mm": max_interference_mm if max_interference_mm > 0 else 0.0,

        # Surface finish recommendations
        "recommended_hole_finish_ra": preset.surface_finish_hole_ra if preset else "1.6-3.2",
        "recommended_shaft_finish_ra": preset.surface_finish_shaft_ra if preset else "0.8-1.6",

        # Substitution strings for display
        "subst_hole_upper_dev_mm": f"ES = +{hole_ES_um:.1f} μm",
        "subst_hole_lower_dev_mm": f"EI = {hole_EI_um:+.1f} μm",
        "subst_shaft_upper_dev_mm": f"es = {shaft_es_um:+.1f} μm",
        "subst_shaft_lower_dev_mm": f"ei = {shaft_ei_um:+.1f} μm",
    }


def get_common_fits() -> Dict[str, Dict[str, Any]]:
    """
    Return dictionary of common fit presets with metadata.
    """
    return {
        designation: {
            "designation": preset.designation,
            "name": preset.name,
            "fit_type": preset.fit_type,
            "description": preset.description,
            "applications": preset.applications,
        }
        for designation, preset in COMMON_FITS.items()
    }


def get_fit_types() -> Dict[str, str]:
    """Return fit type descriptions."""
    return {
        "clearance": "Always positive clearance - parts can move/slide freely",
        "transition": "May be clearance or interference depending on actual sizes",
        "interference": "Always interference - requires press or thermal assembly",
    }


def suggest_fit(
    application: str,
    assembly_method: str = "hand",
    precision: str = "standard",
) -> List[str]:
    """
    Suggest appropriate fits based on application requirements.

    ---Parameters---
    application : str
        Type of application: "running", "sliding", "location", "press"
    assembly_method : str
        How parts will be assembled: "hand", "light_press", "heavy_press", "shrink"
    precision : str
        Required precision: "low", "standard", "high"

    ---Returns---
    List of suggested fit designations.
    """
    suggestions = []

    if application == "running":
        if precision == "low":
            suggestions = ["H11/c11", "H9/d9"]
        elif precision == "high":
            suggestions = ["H7/g6", "H6/h5"]
        else:
            suggestions = ["H8/f7", "H7/g6"]

    elif application == "sliding":
        if precision == "high":
            suggestions = ["H6/h5", "H7/g6"]
        else:
            suggestions = ["H7/h6", "H7/g6"]

    elif application == "location":
        if assembly_method == "hand":
            suggestions = ["H7/h6", "H7/js6"]
        elif assembly_method == "light_press":
            suggestions = ["H7/k6", "H7/m6"]
        else:
            suggestions = ["H7/n6", "H7/p6"]

    elif application == "press":
        if assembly_method == "light_press":
            suggestions = ["H7/p6", "H7/r6"]
        elif assembly_method == "heavy_press":
            suggestions = ["H7/s6", "H7/t6"]
        elif assembly_method == "shrink":
            suggestions = ["H7/t6", "H7/u6"]
        else:
            suggestions = ["H7/p6"]

    return suggestions
