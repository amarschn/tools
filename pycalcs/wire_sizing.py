"""Wire sizing calculations per NEC (National Electrical Code).

This module provides comprehensive wire sizing calculations based on:
- NEC 310.16: Ampacity tables for conductors
- NEC 310.15(B): Temperature correction factors
- NEC 310.15(C): Adjustment factors for bundled conductors
- Voltage drop calculations per standard formulas

All ampacity values are from NEC 2020 Table 310.16 for conductors
in raceway, cable, or earth (directly buried).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# =============================================================================
# Wire Size Definitions
# =============================================================================

# Ordered from smallest to largest (for proper iteration)
AWG_SIZES: List[str] = [
    "18 AWG", "16 AWG", "14 AWG", "12 AWG", "10 AWG", "8 AWG",
    "6 AWG", "4 AWG", "3 AWG", "2 AWG", "1 AWG",
    "1/0 AWG", "2/0 AWG", "3/0 AWG", "4/0 AWG",
    "250 kcmil", "300 kcmil", "350 kcmil", "400 kcmil", "500 kcmil",
    "600 kcmil", "700 kcmil", "750 kcmil", "800 kcmil", "900 kcmil",
    "1000 kcmil", "1250 kcmil", "1500 kcmil", "1750 kcmil", "2000 kcmil",
]

# Cross-sectional area in mm² (for visualization and calculations)
WIRE_AREA_MM2: Dict[str, float] = {
    "20 AWG": 0.519,
    "18 AWG": 0.823,
    "16 AWG": 1.31,
    "14 AWG": 2.08,
    "12 AWG": 3.31,
    "10 AWG": 5.26,
    "8 AWG": 8.37,
    "6 AWG": 13.3,
    "4 AWG": 21.2,
    "3 AWG": 26.7,
    "2 AWG": 33.6,
    "1 AWG": 42.4,
    "1/0 AWG": 53.5,
    "2/0 AWG": 67.4,
    "3/0 AWG": 85.0,
    "4/0 AWG": 107.2,
    "250 kcmil": 127.0,
    "300 kcmil": 152.0,
    "350 kcmil": 177.0,
    "400 kcmil": 203.0,
    "500 kcmil": 253.0,
    "600 kcmil": 304.0,
    "700 kcmil": 355.0,
    "750 kcmil": 380.0,
    "800 kcmil": 405.0,
    "900 kcmil": 456.0,
    "1000 kcmil": 507.0,
    "1250 kcmil": 633.0,
    "1500 kcmil": 760.0,
    "1750 kcmil": 887.0,
    "2000 kcmil": 1013.0,
}

# Diameter in mm (for visualization)
WIRE_DIAMETER_MM: Dict[str, float] = {
    size: math.sqrt(4 * area / math.pi) for size, area in WIRE_AREA_MM2.items()
}


# =============================================================================
# NEC 310.16 Ampacity Tables
# =============================================================================

# NEC 2020 Table 310.16: Allowable Ampacities of Insulated Conductors
# Rated 0 Through 2000 Volts, in Raceway, Cable, or Earth (Directly Buried)
# Based on Ambient Temperature of 30°C (86°F)

# Copper conductors
AMPACITY_COPPER_60C: Dict[str, int] = {
    "14 AWG": 15, "12 AWG": 20, "10 AWG": 30, "8 AWG": 40,
    "6 AWG": 55, "4 AWG": 70, "3 AWG": 85, "2 AWG": 95,
    "1 AWG": 110, "1/0 AWG": 125, "2/0 AWG": 145, "3/0 AWG": 165,
    "4/0 AWG": 195, "250 kcmil": 215, "300 kcmil": 240, "350 kcmil": 260,
    "400 kcmil": 280, "500 kcmil": 320, "600 kcmil": 350, "700 kcmil": 385,
    "750 kcmil": 400, "800 kcmil": 410, "900 kcmil": 435, "1000 kcmil": 455,
    "1250 kcmil": 495, "1500 kcmil": 520, "1750 kcmil": 545, "2000 kcmil": 560,
}

AMPACITY_COPPER_75C: Dict[str, int] = {
    "14 AWG": 20, "12 AWG": 25, "10 AWG": 35, "8 AWG": 50,
    "6 AWG": 65, "4 AWG": 85, "3 AWG": 100, "2 AWG": 115,
    "1 AWG": 130, "1/0 AWG": 150, "2/0 AWG": 175, "3/0 AWG": 200,
    "4/0 AWG": 230, "250 kcmil": 255, "300 kcmil": 285, "350 kcmil": 310,
    "400 kcmil": 335, "500 kcmil": 380, "600 kcmil": 420, "700 kcmil": 460,
    "750 kcmil": 475, "800 kcmil": 490, "900 kcmil": 520, "1000 kcmil": 545,
    "1250 kcmil": 590, "1500 kcmil": 625, "1750 kcmil": 650, "2000 kcmil": 665,
}

AMPACITY_COPPER_90C: Dict[str, int] = {
    "14 AWG": 25, "12 AWG": 30, "10 AWG": 40, "8 AWG": 55,
    "6 AWG": 75, "4 AWG": 95, "3 AWG": 115, "2 AWG": 130,
    "1 AWG": 145, "1/0 AWG": 170, "2/0 AWG": 195, "3/0 AWG": 225,
    "4/0 AWG": 260, "250 kcmil": 290, "300 kcmil": 320, "350 kcmil": 350,
    "400 kcmil": 380, "500 kcmil": 430, "600 kcmil": 475, "700 kcmil": 520,
    "750 kcmil": 535, "800 kcmil": 555, "900 kcmil": 585, "1000 kcmil": 615,
    "1250 kcmil": 665, "1500 kcmil": 705, "1750 kcmil": 735, "2000 kcmil": 750,
}

# Aluminum conductors
AMPACITY_ALUMINUM_60C: Dict[str, int] = {
    "12 AWG": 15, "10 AWG": 25, "8 AWG": 35,
    "6 AWG": 40, "4 AWG": 55, "3 AWG": 65, "2 AWG": 75,
    "1 AWG": 85, "1/0 AWG": 100, "2/0 AWG": 115, "3/0 AWG": 130,
    "4/0 AWG": 150, "250 kcmil": 170, "300 kcmil": 190, "350 kcmil": 210,
    "400 kcmil": 225, "500 kcmil": 260, "600 kcmil": 285, "700 kcmil": 310,
    "750 kcmil": 320, "800 kcmil": 330, "900 kcmil": 355, "1000 kcmil": 375,
    "1250 kcmil": 405, "1500 kcmil": 435, "1750 kcmil": 455, "2000 kcmil": 470,
}

AMPACITY_ALUMINUM_75C: Dict[str, int] = {
    "12 AWG": 20, "10 AWG": 30, "8 AWG": 40,
    "6 AWG": 50, "4 AWG": 65, "3 AWG": 75, "2 AWG": 90,
    "1 AWG": 100, "1/0 AWG": 120, "2/0 AWG": 135, "3/0 AWG": 155,
    "4/0 AWG": 180, "250 kcmil": 205, "300 kcmil": 230, "350 kcmil": 250,
    "400 kcmil": 270, "500 kcmil": 310, "600 kcmil": 340, "700 kcmil": 375,
    "750 kcmil": 385, "800 kcmil": 395, "900 kcmil": 425, "1000 kcmil": 445,
    "1250 kcmil": 485, "1500 kcmil": 520, "1750 kcmil": 545, "2000 kcmil": 560,
}

AMPACITY_ALUMINUM_90C: Dict[str, int] = {
    "12 AWG": 25, "10 AWG": 35, "8 AWG": 45,
    "6 AWG": 55, "4 AWG": 75, "3 AWG": 85, "2 AWG": 100,
    "1 AWG": 115, "1/0 AWG": 135, "2/0 AWG": 150, "3/0 AWG": 175,
    "4/0 AWG": 205, "250 kcmil": 230, "300 kcmil": 255, "350 kcmil": 280,
    "400 kcmil": 305, "500 kcmil": 350, "600 kcmil": 385, "700 kcmil": 420,
    "750 kcmil": 435, "800 kcmil": 450, "900 kcmil": 480, "1000 kcmil": 500,
    "1250 kcmil": 545, "1500 kcmil": 585, "1750 kcmil": 615, "2000 kcmil": 630,
}


# =============================================================================
# NEC 310.15(B) Temperature Correction Factors
# =============================================================================

# Correction factors for ambient temperatures other than 30°C
# Format: (min_temp, max_temp): {60C: factor, 75C: factor, 90C: factor}
TEMP_CORRECTION_FACTORS: List[Tuple[int, int, float, float, float]] = [
    # (min, max, 60C, 75C, 90C)
    (10, 15, 1.29, 1.20, 1.15),
    (16, 20, 1.22, 1.15, 1.12),
    (21, 25, 1.15, 1.11, 1.08),
    (26, 30, 1.00, 1.00, 1.00),  # Base temperature
    (31, 35, 0.91, 0.94, 0.96),
    (36, 40, 0.82, 0.88, 0.91),
    (41, 45, 0.71, 0.82, 0.87),
    (46, 50, 0.58, 0.75, 0.82),
    (51, 55, 0.41, 0.67, 0.76),
    (56, 60, 0.00, 0.58, 0.71),
    (61, 65, 0.00, 0.47, 0.65),
    (66, 70, 0.00, 0.33, 0.58),
    (71, 75, 0.00, 0.00, 0.50),
    (76, 80, 0.00, 0.00, 0.41),
]


# =============================================================================
# NEC 310.15(C) Bundling Adjustment Factors
# =============================================================================

# Adjustment factors for more than 3 current-carrying conductors
BUNDLING_FACTORS: List[Tuple[int, int, float]] = [
    # (min_conductors, max_conductors, factor)
    (1, 3, 1.00),
    (4, 6, 0.80),
    (7, 9, 0.70),
    (10, 20, 0.50),
    (21, 30, 0.45),
    (31, 40, 0.40),
    (41, 999, 0.35),
]


# =============================================================================
# Resistance Data
# =============================================================================

# DC resistance at 20°C in ohms per 1000 feet (NEC Chapter 9, Table 8)
# These are for stranded conductors (uncoated copper, aluminum)
RESISTANCE_OHMS_PER_1000FT_20C: Dict[str, Dict[str, float]] = {
    "copper": {
        "20 AWG": 12.36,
        "18 AWG": 7.77, "16 AWG": 4.89, "14 AWG": 3.07, "12 AWG": 1.93,
        "10 AWG": 1.21, "8 AWG": 0.764, "6 AWG": 0.491, "4 AWG": 0.308,
        "3 AWG": 0.245, "2 AWG": 0.194, "1 AWG": 0.154,
        "1/0 AWG": 0.122, "2/0 AWG": 0.0967, "3/0 AWG": 0.0766, "4/0 AWG": 0.0608,
        "250 kcmil": 0.0515, "300 kcmil": 0.0429, "350 kcmil": 0.0367,
        "400 kcmil": 0.0321, "500 kcmil": 0.0258, "600 kcmil": 0.0214,
        "700 kcmil": 0.0184, "750 kcmil": 0.0171, "800 kcmil": 0.0161,
        "900 kcmil": 0.0143, "1000 kcmil": 0.0129,
        "1250 kcmil": 0.0103, "1500 kcmil": 0.00858, "1750 kcmil": 0.00735,
        "2000 kcmil": 0.00643,
    },
    "aluminum": {
        "20 AWG": 20.35,
        "12 AWG": 3.18, "10 AWG": 2.00, "8 AWG": 1.26,
        "6 AWG": 0.808, "4 AWG": 0.508, "3 AWG": 0.403, "2 AWG": 0.319,
        "1 AWG": 0.253, "1/0 AWG": 0.201, "2/0 AWG": 0.159, "3/0 AWG": 0.126,
        "4/0 AWG": 0.100, "250 kcmil": 0.0847, "300 kcmil": 0.0707,
        "350 kcmil": 0.0605, "400 kcmil": 0.0529, "500 kcmil": 0.0424,
        "600 kcmil": 0.0353, "700 kcmil": 0.0303, "750 kcmil": 0.0282,
        "800 kcmil": 0.0265, "900 kcmil": 0.0235, "1000 kcmil": 0.0212,
        "1250 kcmil": 0.0169, "1500 kcmil": 0.0141, "1750 kcmil": 0.0121,
        "2000 kcmil": 0.0106,
    },
}

# Temperature coefficient of resistance (per °C)
TEMP_COEFFICIENT: Dict[str, float] = {
    "copper": 0.00393,
    "aluminum": 0.00403,
}

# Reference temperature for resistance values
RESISTANCE_REF_TEMP_C: float = 20.0


# =============================================================================
# Common Insulation Types
# =============================================================================

INSULATION_TYPES: Dict[str, Dict[str, any]] = {
    "TW": {"temp_rating": 60, "description": "Thermoplastic, wet locations"},
    "UF": {"temp_rating": 60, "description": "Underground feeder"},
    "THW": {"temp_rating": 75, "description": "Thermoplastic, heat & wet resistant"},
    "THWN": {"temp_rating": 75, "description": "Thermoplastic, heat & wet resistant, nylon jacket"},
    "XHHW": {"temp_rating": 75, "description": "Cross-linked polyethylene, wet locations (75°C wet)"},
    "THHN": {"temp_rating": 90, "description": "Thermoplastic, heat resistant, nylon jacket"},
    "XHHW-2": {"temp_rating": 90, "description": "Cross-linked polyethylene (90°C wet & dry)"},
    "RHH": {"temp_rating": 90, "description": "Rubber, heat resistant"},
    "RHW-2": {"temp_rating": 90, "description": "Rubber, heat & moisture resistant"},
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_ampacity_table(
    material: str,
    temp_rating: int,
) -> Dict[str, int]:
    """
    Get the appropriate ampacity table for the given material and temperature rating.

    ---Parameters---
    material : str
        Conductor material: "copper" or "aluminum".
    temp_rating : int
        Insulation temperature rating: 60, 75, or 90 (°C).

    ---Returns---
    table : Dict[str, int]
        Ampacity table mapping wire size to base ampacity in amperes.
    """
    material = material.lower()

    if material == "copper":
        if temp_rating == 60:
            return AMPACITY_COPPER_60C
        elif temp_rating == 75:
            return AMPACITY_COPPER_75C
        elif temp_rating == 90:
            return AMPACITY_COPPER_90C
    elif material == "aluminum":
        if temp_rating == 60:
            return AMPACITY_ALUMINUM_60C
        elif temp_rating == 75:
            return AMPACITY_ALUMINUM_75C
        elif temp_rating == 90:
            return AMPACITY_ALUMINUM_90C

    raise ValueError(f"No ampacity table for {material} at {temp_rating}°C")


def get_temp_correction_factor(
    ambient_temp_c: float,
    insulation_temp_rating: int,
) -> float:
    """
    Get temperature correction factor per NEC 310.15(B).

    ---Parameters---
    ambient_temp_c : float
        Ambient temperature in degrees Celsius.
    insulation_temp_rating : int
        Insulation temperature rating: 60, 75, or 90 (°C).

    ---Returns---
    factor : float
        Correction factor to multiply base ampacity.

    ---LaTeX---
    I_{corrected} = I_{base} \\times f_{temp}
    """
    # Map temp rating to column index
    col_map = {60: 2, 75: 3, 90: 4}
    col_idx = col_map.get(insulation_temp_rating)

    if col_idx is None:
        raise ValueError(f"Invalid insulation rating: {insulation_temp_rating}°C")

    for row in TEMP_CORRECTION_FACTORS:
        if row[0] <= ambient_temp_c <= row[1]:
            return row[col_idx]

    # Outside table range
    if ambient_temp_c < 10:
        return TEMP_CORRECTION_FACTORS[0][col_idx]  # Use coldest factor
    else:
        return 0.0  # Too hot, conductor cannot be used


def get_bundling_factor(num_conductors: int) -> float:
    """
    Get bundling adjustment factor per NEC 310.15(C).

    ---Parameters---
    num_conductors : int
        Number of current-carrying conductors in raceway/cable.

    ---Returns---
    factor : float
        Adjustment factor to multiply ampacity.

    ---LaTeX---
    I_{adjusted} = I_{base} \\times f_{temp} \\times f_{bundle}
    """
    if num_conductors < 1:
        raise ValueError("Number of conductors must be at least 1")

    for min_cond, max_cond, factor in BUNDLING_FACTORS:
        if min_cond <= num_conductors <= max_cond:
            return factor

    return 0.35  # Default for very large bundles


def get_resistance_per_meter(
    wire_size: str,
    material: str,
    temperature_c: float,
) -> float:
    """
    Calculate wire resistance per meter at a given temperature.

    ---Parameters---
    wire_size : str
        Wire size (e.g., "12 AWG", "4/0 AWG", "250 kcmil").
    material : str
        Conductor material: "copper" or "aluminum".
    temperature_c : float
        Operating temperature in degrees Celsius.

    ---Returns---
    resistance : float
        Resistance in ohms per meter.

    ---LaTeX---
    R_T = R_{20} \\times [1 + \\alpha (T - 20)]
    """
    material = material.lower()

    if material not in RESISTANCE_OHMS_PER_1000FT_20C:
        raise ValueError(f"Unknown material: {material}")

    r_table = RESISTANCE_OHMS_PER_1000FT_20C[material]
    r_20c_per_1000ft = r_table.get(wire_size)

    if r_20c_per_1000ft is None:
        raise ValueError(f"No resistance data for {wire_size} {material}")

    # Convert ohms/1000ft to ohms/meter
    # 1000 ft = 304.8 m
    r_20c_per_meter = r_20c_per_1000ft / 304.8

    # Temperature correction
    alpha = TEMP_COEFFICIENT[material]
    r_t = r_20c_per_meter * (1 + alpha * (temperature_c - RESISTANCE_REF_TEMP_C))

    return r_t


def get_wire_sizes_for_material(material: str) -> List[str]:
    """
    Get available wire sizes for a given material.

    ---Parameters---
    material : str
        Conductor material: "copper" or "aluminum".

    ---Returns---
    sizes : List[str]
        List of wire sizes in order from smallest to largest.
    """
    material = material.lower()

    # Get sizes that have ampacity data
    if material == "copper":
        available = set(AMPACITY_COPPER_75C.keys())
    else:
        available = set(AMPACITY_ALUMINUM_75C.keys())

    # Return in proper order
    return [s for s in AWG_SIZES if s in available]


# =============================================================================
# Main Calculation Functions
# =============================================================================

@dataclass
class WireSizingResult:
    """Result of wire sizing calculation."""

    # Input summary
    load_current_a: float
    voltage_v: float
    length_m: float
    material: str
    insulation_temp_rating: int
    ambient_temp_c: float
    num_conductors: int

    # Correction factors
    temp_correction_factor: float
    bundling_factor: float
    total_derating_factor: float

    # Sizing result
    required_ampacity_a: float
    recommended_size: str
    recommended_ampacity_a: float
    corrected_ampacity_a: float
    ampacity_margin_percent: float

    # Voltage drop
    resistance_ohm: float
    voltage_drop_v: float
    voltage_drop_percent: float
    power_loss_w: float

    # Wire properties
    wire_area_mm2: float
    wire_diameter_mm: float

    # Status
    ampacity_ok: bool
    voltage_drop_ok: bool
    overall_ok: bool
    warnings: List[str]


def calculate_wire_size(
    current_a: float,
    voltage_v: float,
    length_m: float,
    material: str = "copper",
    insulation_temp_rating: int = 75,
    ambient_temp_c: float = 30.0,
    num_conductors: int = 3,
    max_voltage_drop_percent: float = 3.0,
    circuit_type: str = "DC",
    termination_rating: Optional[int] = None,
) -> dict:
    """
    Calculate the recommended wire size for given electrical load.

    ---Parameters---
    current_a : float
        Load current in amperes.
    voltage_v : float
        System voltage in volts.
    length_m : float
        One-way wire run length in meters (total = 2× for round trip).
    material : str
        Conductor material: "copper" or "aluminum". Default: "copper".
    insulation_temp_rating : int
        Insulation temperature rating: 60, 75, or 90 (°C). Default: 75.
    ambient_temp_c : float
        Ambient temperature in degrees Celsius. Default: 30.0.
    num_conductors : int
        Number of current-carrying conductors in raceway. Default: 3.
    max_voltage_drop_percent : float
        Maximum acceptable voltage drop. Default: 3.0%.
    circuit_type : str
        "DC" or "AC". Default: "DC".

    ---Returns---
    result : dict
        Dictionary containing all calculation results.

    ---LaTeX---
    I_{required} = \\frac{I_{load}}{f_{temp} \\times f_{bundle}}

    V_{drop} = I \\times R \\times L_{roundtrip}

    ---References---
    NFPA 70: National Electrical Code (NEC), 2020 Edition.
    """
    warnings = []

    # Validate inputs
    if current_a <= 0:
        raise ValueError("Current must be positive")
    if voltage_v <= 0:
        raise ValueError("Voltage must be positive")
    if length_m <= 0:
        raise ValueError("Length must be positive")

    material = material.lower()
    if material not in ("copper", "aluminum"):
        raise ValueError("Material must be 'copper' or 'aluminum'")

    if insulation_temp_rating not in (60, 75, 90):
        raise ValueError("Insulation rating must be 60, 75, or 90")

    # Get correction factors
    temp_factor = get_temp_correction_factor(ambient_temp_c, insulation_temp_rating)
    bundling_factor = get_bundling_factor(num_conductors)
    total_derating = temp_factor * bundling_factor

    if total_derating <= 0:
        raise ValueError(f"Cannot operate at {ambient_temp_c}°C with {insulation_temp_rating}°C insulation")

    # Calculate required base ampacity
    required_ampacity = current_a / total_derating

    # Get ampacity table and find suitable wire
    ampacity_table = get_ampacity_table(material, insulation_temp_rating)
    available_sizes = get_wire_sizes_for_material(material)

    recommended_size = None
    recommended_ampacity = 0

    for size in available_sizes:
        base_ampacity = ampacity_table.get(size, 0)
        if base_ampacity >= required_ampacity:
            recommended_size = size
            recommended_ampacity = base_ampacity
            break

    if recommended_size is None:
        # Use largest available
        recommended_size = available_sizes[-1]
        recommended_ampacity = ampacity_table.get(recommended_size, 0)
        warnings.append(f"Load exceeds largest standard size; using {recommended_size}")

    corrected_ampacity = recommended_ampacity * total_derating
    ampacity_margin = ((corrected_ampacity - current_a) / current_a) * 100 if current_a > 0 else 0
    ampacity_ok = corrected_ampacity >= current_a

    # Calculate voltage drop
    # Use insulation temp rating as worst-case operating temperature
    r_per_m = get_resistance_per_meter(recommended_size, material, insulation_temp_rating)

    # Voltage-drop conductor-length factor: single-phase AC and DC use 2 (out and
    # back); balanced three-phase uses sqrt(3) (line-to-line drop).
    if circuit_type.upper() in ("3PH", "3-PHASE", "THREE-PHASE", "AC3"):
        round_trip_length = math.sqrt(3) * length_m
    else:
        round_trip_length = 2 * length_m

    total_resistance = r_per_m * round_trip_length
    voltage_drop = current_a * total_resistance
    voltage_drop_percent = (voltage_drop / voltage_v) * 100
    power_loss = current_a * current_a * total_resistance

    voltage_drop_ok = voltage_drop_percent <= max_voltage_drop_percent

    if not voltage_drop_ok:
        warnings.append(f"Voltage drop {voltage_drop_percent:.1f}% exceeds {max_voltage_drop_percent}% limit")

    # Get wire properties
    wire_area = WIRE_AREA_MM2.get(recommended_size, 0)
    wire_diameter = WIRE_DIAMETER_MM.get(recommended_size, 0)

    overall_ok = ampacity_ok and voltage_drop_ok

    return {
        # Inputs
        "load_current_a": current_a,
        "voltage_v": voltage_v,
        "length_m": length_m,
        "material": material,
        "insulation_temp_rating": insulation_temp_rating,
        "ambient_temp_c": ambient_temp_c,
        "num_conductors": num_conductors,
        "circuit_type": circuit_type,
        "max_voltage_drop_percent": max_voltage_drop_percent,

        # Correction factors
        "temp_correction_factor": temp_factor,
        "bundling_factor": bundling_factor,
        "total_derating_factor": total_derating,

        # Ampacity results
        "required_ampacity_a": required_ampacity,
        "recommended_size": recommended_size,
        "recommended_base_ampacity_a": recommended_ampacity,
        "corrected_ampacity_a": corrected_ampacity,
        "ampacity_margin_percent": ampacity_margin,
        "ampacity_ok": ampacity_ok,

        # Voltage drop results
        "resistance_ohm": total_resistance,
        "voltage_drop_v": voltage_drop,
        "voltage_drop_percent": voltage_drop_percent,
        "power_loss_w": power_loss,
        "voltage_drop_ok": voltage_drop_ok,

        # Wire properties
        "wire_area_mm2": wire_area,
        "wire_diameter_mm": wire_diameter,

        # Status
        "overall_ok": overall_ok,
        "warnings": warnings,
    }


def check_wire_size(
    wire_size: str,
    current_a: float,
    voltage_v: float,
    length_m: float,
    material: str = "copper",
    insulation_temp_rating: int = 75,
    ambient_temp_c: float = 30.0,
    num_conductors: int = 3,
    max_voltage_drop_percent: float = 3.0,
    circuit_type: str = "DC",
    termination_rating: Optional[int] = None,
) -> dict:
    """
    Check if a specific wire size is adequate for the given load.

    ---Parameters---
    wire_size : str
        Wire size to check (e.g., "12 AWG", "4/0 AWG").
    current_a : float
        Load current in amperes.
    voltage_v : float
        System voltage in volts.
    length_m : float
        One-way wire run length in meters.
    material : str
        Conductor material: "copper" or "aluminum".
    insulation_temp_rating : int
        Insulation temperature rating: 60, 75, or 90 (°C).
    ambient_temp_c : float
        Ambient temperature in degrees Celsius.
    num_conductors : int
        Number of current-carrying conductors in raceway.
    max_voltage_drop_percent : float
        Maximum acceptable voltage drop.
    circuit_type : str
        "DC" or "AC".

    ---Returns---
    result : dict
        Dictionary containing check results.

    ---LaTeX---
    \\text{PASS if } I_{corrected} \\geq I_{load} \\text{ and } V_{drop\\%} \\leq V_{max\\%}
    """
    warnings = []

    # Validate inputs
    if current_a <= 0:
        raise ValueError("Current must be positive")
    if voltage_v <= 0:
        raise ValueError("Voltage must be positive")
    if length_m <= 0:
        raise ValueError("Length must be positive")

    material = material.lower()

    # Get correction factors
    temp_factor = get_temp_correction_factor(ambient_temp_c, insulation_temp_rating)
    bundling_factor = get_bundling_factor(num_conductors)
    total_derating = temp_factor * bundling_factor

    if total_derating <= 0:
        raise ValueError(f"Cannot operate at {ambient_temp_c}°C with {insulation_temp_rating}°C insulation")

    # Base ampacity from the wire's own insulation column (used for derating).
    ampacity_table = get_ampacity_table(material, insulation_temp_rating)
    base_ampacity = ampacity_table.get(wire_size)

    if base_ampacity is None:
        raise ValueError(f"Unknown wire size: {wire_size}")

    derated_ampacity = base_ampacity * total_derating
    # NEC 110.14(C): the usable ampacity is capped by the termination temperature
    # column (60/75 C). Derating may use the 90 C column, but the final ampacity
    # is min(derated, termination-column base).
    if termination_rating is not None:
        termination_cap = get_ampacity_table(material, termination_rating).get(wire_size)
        corrected_ampacity = (min(derated_ampacity, termination_cap)
                              if termination_cap is not None else derated_ampacity)
    else:
        termination_cap = None
        corrected_ampacity = derated_ampacity

    ampacity_margin = ((corrected_ampacity - current_a) / current_a) * 100 if current_a > 0 else 0
    ampacity_ok = corrected_ampacity >= current_a

    if not ampacity_ok:
        warnings.append(f"Wire undersized: need {current_a:.1f}A, have {corrected_ampacity:.1f}A")

    # Calculate voltage drop
    r_per_m = get_resistance_per_meter(wire_size, material, insulation_temp_rating)

    # See calculate_wire_size: sqrt(3) for balanced three-phase, else 2.
    if circuit_type.upper() in ("3PH", "3-PHASE", "THREE-PHASE", "AC3"):
        round_trip_length = math.sqrt(3) * length_m
    else:
        round_trip_length = 2 * length_m

    total_resistance = r_per_m * round_trip_length
    voltage_drop = current_a * total_resistance
    voltage_drop_percent = (voltage_drop / voltage_v) * 100
    power_loss = current_a * current_a * total_resistance

    voltage_drop_ok = voltage_drop_percent <= max_voltage_drop_percent

    if not voltage_drop_ok:
        warnings.append(f"Voltage drop {voltage_drop_percent:.1f}% exceeds {max_voltage_drop_percent}% limit")

    # Get wire properties
    wire_area = WIRE_AREA_MM2.get(wire_size, 0)
    wire_diameter = WIRE_DIAMETER_MM.get(wire_size, 0)

    overall_ok = ampacity_ok and voltage_drop_ok
    check_result = "PASS" if overall_ok else "FAIL"

    return {
        # Inputs
        "wire_size": wire_size,
        "load_current_a": current_a,
        "voltage_v": voltage_v,
        "length_m": length_m,
        "material": material,
        "insulation_temp_rating": insulation_temp_rating,
        "ambient_temp_c": ambient_temp_c,
        "num_conductors": num_conductors,
        "circuit_type": circuit_type,

        # Correction factors
        "temp_correction_factor": temp_factor,
        "bundling_factor": bundling_factor,
        "total_derating_factor": total_derating,

        # Ampacity results
        "base_ampacity_a": base_ampacity,
        "derated_ampacity_a": derated_ampacity,
        "termination_rating": termination_rating,
        "termination_cap_a": termination_cap,
        "corrected_ampacity_a": corrected_ampacity,
        "ampacity_margin_percent": ampacity_margin,
        "ampacity_ok": ampacity_ok,

        # Voltage drop results
        "resistance_ohm": total_resistance,
        "voltage_drop_v": voltage_drop,
        "voltage_drop_percent": voltage_drop_percent,
        "power_loss_w": power_loss,
        "voltage_drop_ok": voltage_drop_ok,

        # Wire properties
        "wire_area_mm2": wire_area,
        "wire_diameter_mm": wire_diameter,

        # Status
        "check_result": check_result,
        "overall_ok": overall_ok,
        "warnings": warnings,
    }


def get_ampacity_table_data(
    material: str = "copper",
    insulation_temp_rating: int = 75,
) -> List[dict]:
    """
    Get ampacity table data for display.

    ---Parameters---
    material : str
        Conductor material: "copper" or "aluminum".
    insulation_temp_rating : int
        Insulation temperature rating: 60, 75, or 90 (°C).

    ---Returns---
    table : List[dict]
        List of dictionaries with wire size, ampacity, and area.
    """
    ampacity_table = get_ampacity_table(material, insulation_temp_rating)
    sizes = get_wire_sizes_for_material(material)

    result = []
    for size in sizes:
        ampacity = ampacity_table.get(size, 0)
        area = WIRE_AREA_MM2.get(size, 0)
        diameter = WIRE_DIAMETER_MM.get(size, 0)

        result.append({
            "size": size,
            "ampacity": ampacity,
            "area_mm2": area,
            "diameter_mm": diameter,
        })

    return result


def list_wire_sizes() -> List[str]:
    """
    Return list of all available wire sizes.

    ---Returns---
    sizes : List[str]
        Wire sizes from smallest to largest.
    """
    return AWG_SIZES.copy()


def list_insulation_types() -> Dict[str, Dict]:
    """
    Return dictionary of common insulation types and their ratings.

    ---Returns---
    types : Dict[str, Dict]
        Insulation type codes with temperature ratings and descriptions.
    """
    return INSULATION_TYPES.copy()


# =============================================================================
# Overcurrent Protection (breaker / fuse) sizing — NEC 240
# =============================================================================

# NEC 240.6(A): standard ampere ratings for fuses and inverse-time breakers.
NEC_STANDARD_OCPD_RATINGS: List[int] = [
    15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125, 150, 175,
    200, 225, 250, 300, 350, 400, 450, 500, 600, 700, 800, 1000, 1200, 1600,
    2000, 2500, 3000, 4000, 5000, 6000,
]

# NEC 240.4(D): small-conductor overcurrent protection limits (absolute caps,
# applied after any ampacity correction/adjustment). Aluminum 14 AWG is not a
# recognized building-wiring size, so it is omitted.
SMALL_CONDUCTOR_MAX_OCPD: Dict[str, Dict[str, int]] = {
    "copper": {"14 AWG": 15, "12 AWG": 20, "10 AWG": 30},
    "aluminum": {"12 AWG": 15, "10 AWG": 25},
}

# Verdict tuning: a code-compliant result with very little ampacity headroom
# (< 5%) is flagged "marginal". Common sizings (e.g. 60 A on 6 AWG / 65 A, ~8%)
# stay a clean "pass".
_AMPACITY_MARGINAL_PCT = 5.0


def next_standard_ocpd(current_a: float) -> Optional[int]:
    """
    Return the smallest NEC 240.6(A) standard OCPD rating >= ``current_a``.

    ---Parameters---
    current_a : float
        Required protective-device current in amperes.

    ---Returns---
    rating : Optional[int]
        Smallest standard ampere rating that is >= current_a, or None if the
        requirement exceeds the largest tabulated standard rating (6000 A).

    ---References---
    NFPA 70 (NEC), 240.6(A): Standard ampere ratings.
    """
    for rating in NEC_STANDARD_OCPD_RATINGS:
        if rating >= current_a - 1e-9:
            return rating
    return None


def select_breaker(load_current_a: float, continuous_load: bool = False) -> dict:
    """
    Select the minimum standard breaker/fuse rating to serve a load.

    For a continuous load (operating >= 3 hours) the overcurrent device must be
    rated for at least 125% of the load current per NEC 210.20(A)/215.3.

    ---Parameters---
    load_current_a : float
        Operating load current in amperes.
    continuous_load : bool
        True if the load is continuous (>= 3 hours). Default: False.

    ---Returns---
    result : dict
        {required_ocpd_a, breaker_rating_a, continuous_load}. ``breaker_rating_a``
        is None if the requirement exceeds the standard-rating table.

    ---LaTeX---
    I_{OCPD} \\geq k \\cdot I_{load}, \\quad k = 1.25 \\text{ (continuous)}, 1.0 \\text{ (otherwise)}

    ---References---
    NFPA 70 (NEC), 210.20(A), 215.3, 240.6(A).
    """
    if load_current_a <= 0:
        raise ValueError("Load current must be positive")
    factor = 1.25 if continuous_load else 1.0
    required = load_current_a * factor
    return {
        "required_ocpd_a": required,
        "breaker_rating_a": next_standard_ocpd(required),
        "continuous_load": continuous_load,
    }


def check_conductor_protection(
    breaker_rating_a: float,
    corrected_ampacity_a: float,
    wire_size: str,
    material: str,
) -> dict:
    """
    Check whether an OCPD rating properly protects a conductor per NEC 240.4.

    Applies the general rule (OCPD <= conductor ampacity), the 240.4(B)
    next-standard-size-up allowance (permitted up to 800 A when the conductor
    ampacity does not correspond to a standard rating), and the 240.4(D)
    small-conductor caps, which override the next-size-up allowance.

    ---Parameters---
    breaker_rating_a : float
        Selected standard OCPD rating in amperes.
    corrected_ampacity_a : float
        Conductor ampacity after temperature/bundling correction, in amperes.
    wire_size : str
        Conductor size (e.g. "12 AWG").
    material : str
        "copper" or "aluminum".

    ---Returns---
    result : dict
        {protected, small_conductor_cap_a, allowance, note}.

    ---References---
    NFPA 70 (NEC), 240.4(B) next standard size, 240.4(D) small conductors.
    """
    material = material.lower()
    cap = SMALL_CONDUCTOR_MAX_OCPD.get(material, {}).get(wire_size)
    allowance = "none"

    if breaker_rating_a <= corrected_ampacity_a + 1e-9:
        protected = True
        note = "OCPD rating does not exceed conductor ampacity (NEC 240.4)."
    else:
        # 240.4(B): the next standard rating above the conductor ampacity is
        # permitted, for ratings <= 800 A.
        next_up = next_standard_ocpd(corrected_ampacity_a + 1e-9)
        if next_up is not None and breaker_rating_a == next_up and breaker_rating_a <= 800:
            protected = True
            allowance = "240.4(B)"
            note = ("Protected via NEC 240.4(B): next standard OCPD size above "
                    "conductor ampacity is permitted (<= 800 A).")
        else:
            protected = False
            note = ("OCPD rating exceeds conductor ampacity; conductor is not "
                    "protected (NEC 240.4).")

    # 240.4(D) small-conductor cap is an absolute override.
    if cap is not None and breaker_rating_a > cap:
        protected = False
        allowance = "none"
        note = (f"NEC 240.4(D): {wire_size} {material} is limited to a {cap} A "
                f"overcurrent device.")

    return {
        "protected": protected,
        "small_conductor_cap_a": cap,
        "allowance": allowance,
        "note": note,
    }


def evaluate_circuit(
    current_a: float,
    voltage_v: float,
    length_m: float,
    material: str = "copper",
    insulation_temp_rating: int = 75,
    ambient_temp_c: float = 30.0,
    num_conductors: int = 3,
    max_voltage_drop_percent: float = 3.0,
    circuit_type: str = "DC",
    continuous_load: bool = False,
    termination_rating: int = 75,
    dwelling_service: bool = False,
) -> dict:
    """
    Full NEC branch-circuit evaluation with a single pass/fail verdict.

    ``dwelling_service`` applies the NEC 310.12 dwelling allowance: the service/
    feeder conductor may be sized at 83% of the rating, and the conductor being
    smaller than the overcurrent device is permitted (protection check waived).

    ``insulation_temp_rating`` is the WIRE's rating (used for derating); the
    usable ampacity is capped by ``termination_rating`` per NEC 110.14(C).

    Recommends the code-minimum conductor: the smallest size that satisfies
    ampacity, overcurrent protection (NEC 240.4/240.6), and — for continuous
    loads — the 125% conductor rule (NEC 210.19(A)). Voltage drop is treated as
    advisory (NEC Informational Notes), so it never drives the recommendation or
    the pass/fail verdict; instead the result reports the drop at the recommended
    conductor and, if it exceeds the target, the smallest conductor that would
    meet it.

    ---Parameters---
    current_a : float
        Operating load current in amperes.
    voltage_v : float
        System voltage in volts.
    length_m : float
        One-way run length in meters.
    material : str
        "copper" or "aluminum". Default: "copper".
    insulation_temp_rating : int
        Insulation rating 60, 75, or 90 (°C). Default: 75.
    ambient_temp_c : float
        Ambient temperature (°C). Default: 30.0.
    num_conductors : int
        Current-carrying conductors in the raceway. Default: 3.
    max_voltage_drop_percent : float
        Voltage-drop limit (NEC recommends 3% branch, 5% total). Default: 3.0.
    circuit_type : str
        "DC" or "AC". Default: "DC".
    continuous_load : bool
        True if the load runs >= 3 hours. Default: False.

    ---Returns---
    result : dict
        The recommended-conductor sizing dict, augmented with ``breaker``
        (selection), ``protection`` (240.4 check), ``continuous_conductor_ok``,
        ``voltage_drop_advisory`` = {target_percent, actual_percent,
        within_target, suggested_size, suggested_percent}, and a ``verdict`` =
        {status, headline, binding_constraint, reasons, checks}. ``checks``
        covers only the mandatory code checks (ampacity, overcurrent_protection,
        continuous_conductor). ``status`` is one of "pass", "marginal", "fail".

    ---References---
    NFPA 70 (NEC), 210.19(A), 210.20(A), 240.4, 240.6, 310.16.
    """
    breaker = select_breaker(current_a, continuous_load)
    breaker_rating = breaker["breaker_rating_a"]
    sizes = get_wire_sizes_for_material(material)

    # NEC 310.12: a dwelling service/feeder conductor may be sized at 83% of the
    # rating, and may be smaller than the OCPD (protection check waived).
    ampacity_factor = 0.83 if dwelling_service else 1.0

    def _evaluate_size(size: str):
        """Return (check_dict, protection_dict, continuous_ok) for one size."""
        chk = check_wire_size(
            size, current_a, voltage_v, length_m, material,
            insulation_temp_rating, ambient_temp_c, num_conductors,
            max_voltage_drop_percent, circuit_type, termination_rating,
        )
        # Apply the dwelling 83% ampacity allowance to the ampacity check.
        chk["ampacity_ok"] = (chk["corrected_ampacity_a"]
                              >= ampacity_factor * current_a - 1e-9)
        if dwelling_service:
            prot = {"protected": True, "small_conductor_cap_a": None,
                    "allowance": "310.12",
                    "note": "Dwelling service/feeder: conductor may be smaller "
                            "than the OCPD (NEC 310.12)."}
        elif breaker_rating is None:
            prot = {"protected": False, "small_conductor_cap_a": None,
                    "allowance": "none",
                    "note": "Load exceeds the largest standard OCPD rating."}
        else:
            prot = check_conductor_protection(
                breaker_rating, chk["corrected_ampacity_a"], size, material)
        cont_ok = (chk["corrected_ampacity_a"] >= 1.25 * current_a - 1e-9
                   if (continuous_load and not dwelling_service) else True)
        return chk, prot, cont_ok

    # Stage 1: smallest conductor meeting ampacity + overcurrent protection +
    # (for continuous loads) the 125% conductor rule. Voltage drop handled next.
    chosen = None
    for size in sizes:
        chk, prot, cont_ok = _evaluate_size(size)
        if chk["ampacity_ok"] and prot["protected"] and cont_ok:
            chosen = (size, chk, prot, cont_ok)
            break
    if chosen is None:
        size = sizes[-1]
        chosen = (size, *_evaluate_size(size))

    # The recommendation is the code-minimum conductor from Stage 1. Voltage
    # drop is advisory (NEC 210.19(A)/215.2(A) Informational Notes), so it does
    # NOT drive the recommendation or the pass/fail verdict — only ampacity and
    # overcurrent protection are code requirements.
    size, chk, protection, continuous_conductor_ok = chosen

    # Voltage-drop advisory, evaluated at the recommended conductor. If it
    # exceeds the target, find the smallest larger conductor that would meet it.
    vd_within_target = bool(chk["voltage_drop_ok"])
    suggested_vd_size = None
    suggested_vd_percent = None
    if not vd_within_target:
        idx = sizes.index(size)
        for s2 in sizes[idx + 1:]:
            c2, p2, ct2 = _evaluate_size(s2)
            if c2["voltage_drop_ok"] and c2["ampacity_ok"] and p2["protected"] and ct2:
                suggested_vd_size = s2
                suggested_vd_percent = c2["voltage_drop_percent"]
                break

    # Normalize to the calculate_wire_size field names the UI expects.
    sizing = dict(chk)
    sizing["recommended_size"] = sizing.pop("wire_size")
    sizing["recommended_base_ampacity_a"] = sizing.pop("base_ampacity_a")
    sizing["max_voltage_drop_percent"] = max_voltage_drop_percent
    derating = sizing.get("total_derating_factor") or 1.0
    sizing["required_ampacity_a"] = current_a / derating

    # Mandatory (code) checks only — voltage drop is advisory, not a check.
    checks = {
        "ampacity": bool(sizing["ampacity_ok"]),
        "overcurrent_protection": bool(protection["protected"]),
        "continuous_conductor": bool(continuous_conductor_ok),
    }

    reasons: List[str] = []
    if not checks["ampacity"]:
        reasons.append(
            f"Ampacity: corrected {sizing['corrected_ampacity_a']:.0f} A < load "
            f"{current_a:.0f} A (exceeds the largest standard conductor).")
    if not checks["overcurrent_protection"]:
        reasons.append(protection["note"])
    if not checks["continuous_conductor"]:
        reasons.append(
            "Continuous load: conductor ampacity below 125% of load "
            "(NEC 210.19(A)).")

    if not all(checks.values()):
        status = "fail"
        for key in ("ampacity", "overcurrent_protection", "continuous_conductor"):
            if not checks[key]:
                binding = key
                break
        headline = f"FAIL — {reasons[0]}"
    else:
        # Code-compliant. A thin ampacity margin is flagged as marginal.
        status = ("marginal"
                  if sizing["ampacity_margin_percent"] < _AMPACITY_MARGINAL_PCT
                  else "pass")
        binding = "ampacity"
        verb = "Marginal" if status == "marginal" else "Pass"
        headline = (f"{verb} — {sizing['recommended_size']} {material} on a "
                    f"{breaker_rating} A breaker (NEC code minimum).")

    sizing["breaker"] = breaker
    sizing["protection"] = protection
    sizing["continuous_load"] = continuous_load
    sizing["continuous_conductor_ok"] = continuous_conductor_ok
    sizing["voltage_drop_advisory"] = {
        "target_percent": max_voltage_drop_percent,
        "actual_percent": sizing["voltage_drop_percent"],
        "within_target": vd_within_target,
        "suggested_size": suggested_vd_size,
        "suggested_percent": suggested_vd_percent,
    }
    sizing["verdict"] = {
        "status": status,
        "headline": headline,
        "binding_constraint": binding,
        "reasons": reasons,
        "checks": checks,
    }
    return sizing


# =============================================================================
# Free-air ampacity — NEC Table 310.17 (for PV / free-air installations)
# =============================================================================
#
# Allowable ampacities of single-insulated conductors in FREE AIR, based on a
# 30 C ambient. These are higher than the Table 310.16 (raceway) values used by
# the premises calculator, and are the correct basis for PV array (single-
# conductor, free-air) circuits.
#
# DATA PROVENANCE (sourced & cross-checked 2026-07-14):
#   Cross-checked across three independent references. Copper small-conductor
#   values (14/12/10 AWG = 25/30/40 A at 60 C) were confirmed by two of three;
#   the Lapp Tannehill chart disagreed (listed 30/35/50) and was rejected.
#   Aluminum 90 C values show <=5 A variance between sources at a few sizes;
#   the values below follow buildmyowncabin's NEC 310-17 reproduction, which is
#   complete and internally consistent. This table is UNVERIFIED by a human and
#   the PV tool must remain Experimental until a maintainer checks it.
#   Refs: wireref.com/ampacity/free-air (NEC 2023);
#         buildmyowncabin.com/nec/nec2002_table310-17.html;
#         lapptannehill.com ampacity chart (copper large sizes only).

AMPACITY_FREE_AIR: Dict[str, Dict[int, Dict[str, int]]] = {
    "copper": {
        60: {
            "14 AWG": 25, "12 AWG": 30, "10 AWG": 40, "8 AWG": 60, "6 AWG": 80,
            "4 AWG": 105, "3 AWG": 120, "2 AWG": 140, "1 AWG": 165,
            "1/0 AWG": 195, "2/0 AWG": 225, "3/0 AWG": 260, "4/0 AWG": 300,
            "250 kcmil": 340, "300 kcmil": 375, "350 kcmil": 420, "400 kcmil": 455,
            "500 kcmil": 515, "600 kcmil": 575, "700 kcmil": 630, "750 kcmil": 655,
            "800 kcmil": 680, "900 kcmil": 730, "1000 kcmil": 780,
        },
        75: {
            "14 AWG": 30, "12 AWG": 35, "10 AWG": 50, "8 AWG": 70, "6 AWG": 95,
            "4 AWG": 125, "3 AWG": 145, "2 AWG": 170, "1 AWG": 195,
            "1/0 AWG": 230, "2/0 AWG": 265, "3/0 AWG": 310, "4/0 AWG": 360,
            "250 kcmil": 405, "300 kcmil": 445, "350 kcmil": 505, "400 kcmil": 545,
            "500 kcmil": 620, "600 kcmil": 690, "700 kcmil": 755, "750 kcmil": 785,
            "800 kcmil": 815, "900 kcmil": 870, "1000 kcmil": 935,
        },
        90: {
            "14 AWG": 35, "12 AWG": 40, "10 AWG": 55, "8 AWG": 80, "6 AWG": 105,
            "4 AWG": 140, "3 AWG": 165, "2 AWG": 190, "1 AWG": 220,
            "1/0 AWG": 260, "2/0 AWG": 300, "3/0 AWG": 350, "4/0 AWG": 405,
            "250 kcmil": 455, "300 kcmil": 505, "350 kcmil": 570, "400 kcmil": 615,
            "500 kcmil": 700, "600 kcmil": 780, "700 kcmil": 855, "750 kcmil": 885,
            "800 kcmil": 920, "900 kcmil": 985, "1000 kcmil": 1055,
        },
    },
    "aluminum": {
        60: {
            "12 AWG": 25, "10 AWG": 35, "8 AWG": 45, "6 AWG": 60, "4 AWG": 80,
            "3 AWG": 95, "2 AWG": 110, "1 AWG": 130, "1/0 AWG": 150, "2/0 AWG": 175,
            "3/0 AWG": 200, "4/0 AWG": 235, "250 kcmil": 265, "300 kcmil": 290,
            "350 kcmil": 330, "400 kcmil": 355, "500 kcmil": 405, "600 kcmil": 455,
            "700 kcmil": 500, "750 kcmil": 515, "800 kcmil": 535, "900 kcmil": 580,
            "1000 kcmil": 625,
        },
        75: {
            "12 AWG": 30, "10 AWG": 40, "8 AWG": 55, "6 AWG": 75, "4 AWG": 100,
            "3 AWG": 115, "2 AWG": 135, "1 AWG": 155, "1/0 AWG": 180, "2/0 AWG": 210,
            "3/0 AWG": 240, "4/0 AWG": 280, "250 kcmil": 315, "300 kcmil": 350,
            "350 kcmil": 395, "400 kcmil": 425, "500 kcmil": 485, "600 kcmil": 540,
            "700 kcmil": 595, "750 kcmil": 620, "800 kcmil": 645, "900 kcmil": 700,
            "1000 kcmil": 750,
        },
        90: {
            "12 AWG": 35, "10 AWG": 40, "8 AWG": 60, "6 AWG": 80, "4 AWG": 110,
            "3 AWG": 130, "2 AWG": 150, "1 AWG": 175, "1/0 AWG": 205, "2/0 AWG": 235,
            "3/0 AWG": 275, "4/0 AWG": 315, "250 kcmil": 355, "300 kcmil": 395,
            "350 kcmil": 445, "400 kcmil": 480, "500 kcmil": 545, "600 kcmil": 615,
            "700 kcmil": 675, "750 kcmil": 700, "800 kcmil": 725, "900 kcmil": 785,
            "1000 kcmil": 845,
        },
    },
}


def get_free_air_ampacity_table(material: str, insulation_temp_rating: int) -> Dict[str, int]:
    """
    Return the NEC Table 310.17 (free-air) ampacity table for a material/rating.

    ---Parameters---
    material : str
        "copper" or "aluminum".
    insulation_temp_rating : int
        60, 75, or 90 (deg C).

    ---Returns---
    table : Dict[str, int]
        Wire size -> free-air ampacity (A) at 30 C ambient.

    ---References---
    NFPA 70 (NEC), Table 310.17: single insulated conductors in free air.
    """
    material = material.lower()
    if material not in AMPACITY_FREE_AIR:
        raise ValueError("Material must be 'copper' or 'aluminum'")
    if insulation_temp_rating not in (60, 75, 90):
        raise ValueError("Insulation rating must be 60, 75, or 90")
    return dict(AMPACITY_FREE_AIR[material][insulation_temp_rating])


# =============================================================================
# Solar PV conductor sizing — NEC 690.8 / 690.9 (free-air basis)
# =============================================================================

def evaluate_pv_circuit(
    isc_a: float,
    voltage_v: float,
    length_m: float,
    material: str = "copper",
    insulation_temp_rating: int = 90,
    ambient_temp_c: float = 45.0,
    num_conductors: int = 1,
    max_voltage_drop_percent: float = 2.0,
) -> dict:
    """
    Size a PV source/output circuit conductor per NEC 690.8/690.9 (free air).

    The maximum circuit current is 125% of the module/array short-circuit
    current (NEC 690.8(A)(1)), accounting for irradiance/temperature. The
    conductor must satisfy BOTH 690.8(B) rules:
      (1) its table (un-derated) ampacity >= 156.25% of Isc (the 125% continuous
          factor on top of the 125% in the maximum current), and
      (2) its derated ampacity (temperature + conduit adjustment) >= the maximum
          circuit current (125% of Isc).
    The overcurrent device, where required, is 156.25% of Isc rounded up to a
    standard rating (690.9(B)). Free-air ampacity (Table 310.17) is used, as PV
    array conductors are single conductors in free air. Voltage drop is advisory.

    PV wire (USE-2/PV) is typically 90 C rated, so the 90 C column is the
    default basis for the ampacity/derating checks.

    ---Parameters---
    isc_a : float
        Module/array rated short-circuit current (Isc), in amperes.
    voltage_v : float
        Nominal circuit voltage, for the voltage-drop percentage.
    length_m : float
        One-way run length in meters (doubled for round-trip voltage drop).
    material : str
        "copper" or "aluminum". Default: "copper".
    insulation_temp_rating : int
        Conductor temperature column: 60, 75, or 90 (deg C). Default: 90.
    ambient_temp_c : float
        Ambient temperature at the array (deg C). Default: 45 (hot rooftop).
    num_conductors : int
        Current-carrying conductors bundled together. Default: 1 (free air).
    max_voltage_drop_percent : float
        Advisory voltage-drop target. Default: 2.0% (typical PV target).

    ---Returns---
    result : dict
        recommended_size, table/derated ampacities, design_current_a,
        required_base_ampacity_a, ocpd (breaker), voltage_drop_advisory, and a
        verdict {status, headline, binding_constraint, reasons, checks}. The
        mandatory check is 690.8(B) ampacity; voltage drop is advisory.

    ---LaTeX---
    I_{max} = 1.25 \\, I_{sc}

    A_{table} \\geq 1.25 \\, I_{max} = 1.5625 \\, I_{sc}

    A_{table} \\cdot f_{temp} \\cdot f_{bundle} \\geq I_{max}

    ---References---
    NFPA 70 (NEC), 690.8(A)(1), 690.8(B)(1)/(2), 690.9(B), Table 310.17.
    """
    if isc_a <= 0:
        raise ValueError("Isc must be positive")
    if voltage_v <= 0:
        raise ValueError("Voltage must be positive")
    if length_m <= 0:
        raise ValueError("Length must be positive")
    material = material.lower()
    if insulation_temp_rating not in (60, 75, 90):
        raise ValueError("Insulation rating must be 60, 75, or 90")

    design_current = 1.25 * isc_a                 # 690.8(A)(1) max circuit current
    required_base = 1.25 * design_current         # 690.8(B)(1): 156.25% of Isc

    temp_factor = get_temp_correction_factor(ambient_temp_c, insulation_temp_rating)
    bundling_factor = get_bundling_factor(num_conductors)
    total_derating = temp_factor * bundling_factor
    if total_derating <= 0:
        raise ValueError(
            f"Cannot operate at {ambient_temp_c} C with {insulation_temp_rating} C insulation")

    table = get_free_air_ampacity_table(material, insulation_temp_rating)
    sizes = [s for s in AWG_SIZES if s in table]

    # Smallest conductor satisfying BOTH 690.8(B) rules.
    chosen = None
    for size in sizes:
        base = table[size]
        if base >= required_base - 1e-9 and base * total_derating >= design_current - 1e-9:
            chosen = size
            break
    if chosen is None:
        chosen = sizes[-1]
    base_ampacity = table[chosen]
    corrected_ampacity = base_ampacity * total_derating
    ampacity_ok = (base_ampacity >= required_base - 1e-9
                   and corrected_ampacity >= design_current - 1e-9)

    # OCPD (690.9(B)): 156.25% of Isc, next standard rating up.
    # NOTE (unverified): the 240.4(D) small-conductor OCPD caps are NOT applied
    # here — PV free-air ampacities are high and 690.8 governs sizing, but the
    # 240.4(D) interaction for PV is a nuance for human review before this tool
    # leaves Experimental.
    ocpd_required = required_base
    ocpd_rating = next_standard_ocpd(ocpd_required)

    # Voltage drop (advisory), computed at the operating current (~Isc).
    r_per_m = get_resistance_per_meter(chosen, material, insulation_temp_rating)
    round_trip = 2 * length_m
    resistance = r_per_m * round_trip
    voltage_drop = isc_a * resistance
    voltage_drop_percent = (voltage_drop / voltage_v) * 100.0
    vd_within_target = voltage_drop_percent <= max_voltage_drop_percent

    suggested_vd_size = None
    suggested_vd_percent = None
    if not vd_within_target:
        idx = sizes.index(chosen)
        for s2 in sizes[idx + 1:]:
            r2 = get_resistance_per_meter(s2, material, insulation_temp_rating)
            vd2 = isc_a * r2 * round_trip
            vd2_pct = (vd2 / voltage_v) * 100.0
            if vd2_pct <= max_voltage_drop_percent:
                suggested_vd_size = s2
                suggested_vd_percent = vd2_pct
                break

    checks = {"ampacity": bool(ampacity_ok)}
    reasons: List[str] = []
    if not ampacity_ok:
        reasons.append(
            f"No conductor meets NEC 690.8(B): need table ampacity >= "
            f"{required_base:.0f} A and derated >= {design_current:.0f} A.")

    if not ampacity_ok:
        status = "fail"
        binding = "ampacity"
        headline = f"FAIL — {reasons[0]}"
    else:
        margin = (corrected_ampacity - design_current) / design_current * 100.0
        status = "marginal" if margin < _AMPACITY_MARGINAL_PCT else "pass"
        binding = "ampacity"
        verb = "Marginal" if status == "marginal" else "Pass"
        headline = (f"{verb} — {chosen} {material}, {ocpd_rating} A OCPD "
                    f"(NEC 690.8 minimum).")

    return {
        "isc_a": isc_a,
        "design_current_a": design_current,
        "required_base_ampacity_a": required_base,
        "voltage_v": voltage_v,
        "length_m": length_m,
        "material": material,
        "insulation_temp_rating": insulation_temp_rating,
        "ambient_temp_c": ambient_temp_c,
        "num_conductors": num_conductors,
        "max_voltage_drop_percent": max_voltage_drop_percent,
        "temp_correction_factor": temp_factor,
        "bundling_factor": bundling_factor,
        "total_derating_factor": total_derating,
        "recommended_size": chosen,
        "recommended_base_ampacity_a": base_ampacity,
        "corrected_ampacity_a": corrected_ampacity,
        "ampacity_ok": ampacity_ok,
        "resistance_ohm": resistance,
        "voltage_drop_v": voltage_drop,
        "voltage_drop_percent": voltage_drop_percent,
        "power_loss_w": isc_a * isc_a * resistance,
        "breaker": {"required_ocpd_a": ocpd_required, "breaker_rating_a": ocpd_rating,
                    "continuous_load": True},
        "voltage_drop_advisory": {
            "target_percent": max_voltage_drop_percent,
            "actual_percent": voltage_drop_percent,
            "within_target": vd_within_target,
            "suggested_size": suggested_vd_size,
            "suggested_percent": suggested_vd_percent,
        },
        "verdict": {
            "status": status,
            "headline": headline,
            "binding_constraint": binding,
            "reasons": reasons,
            "checks": checks,
        },
    }


# =============================================================================
# Automotive / low-voltage DC ampacity — single wire in free air (SAE-oriented)
# =============================================================================
#
# Maximum current for a single insulated conductor in free air ("chassis
# wiring") by AWG — the appropriate basis for automotive / RV / battery / DC
# point-to-point runs. (SAE J1128 is a wire-construction spec; ampacity comes
# from this free-air chart, per the SAE J1292 / J2183 tradition.)
#
# DATA PROVENANCE (sourced & cross-checked 2026-07-16): two independent
# references agree EXACTLY on every gauge for the chassis/free-air column:
#   powerstream.com/Wire_Size.htm ("maximum amps for chassis wiring")
#   fqwireharness.com/wire-gauge-ampacity-guide-2025 (open-air column)
# The classic chart's separate "power transmission" column is intentionally
# NOT used: the two sources disagree on it, so bundling is instead handled by a
# grouping derate applied to these free-air values (get_bundling_factor).
# UNVERIFIED by a human; the DC/automotive tool must ship Experimental.

AMPACITY_FREE_AIR_AUTOMOTIVE: Dict[str, int] = {
    "20 AWG": 11, "18 AWG": 16, "16 AWG": 22, "14 AWG": 32, "12 AWG": 41,
    "10 AWG": 55, "8 AWG": 73, "6 AWG": 101, "4 AWG": 135, "2 AWG": 181,
    "1 AWG": 211, "1/0 AWG": 245, "2/0 AWG": 283, "3/0 AWG": 328, "4/0 AWG": 380,
}


def get_automotive_ampacity_table() -> Dict[str, int]:
    """
    Single-wire-in-free-air ("chassis wiring") ampacity by AWG for
    automotive / low-voltage DC circuits. See the module note above for
    provenance and why the "power transmission" column is not used.

    ---Returns---
    table : Dict[str, int]
        Wire size -> free-air ("chassis") ampacity in amperes.

    ---References---
    Classic AWG chassis-wiring ampacity chart (Handbook of Electronic Tables and
    Formulas), cross-checked against automotive vendor reproductions. SAE J1128
    (wire construction); SAE J1292/J2183 (ampacity tradition).
    """
    return dict(AMPACITY_FREE_AIR_AUTOMOTIVE)


# =============================================================================
# Automotive / low-voltage DC circuit sizing (voltage-drop-driven)
# =============================================================================

# Standard automotive/marine blade & ANL fuse ratings (A) for suggesting an
# overcurrent device that protects the conductor.
DC_STANDARD_FUSE_RATINGS: List[int] = [
    1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 100, 125, 150,
    175, 200, 225, 250, 300,
]


def evaluate_dc_circuit(
    load_current_a: float,
    voltage_v: float,
    length_m: float,
    num_conductors: int = 1,
    max_voltage_drop_percent: float = 3.0,
    material: str = "copper",
) -> dict:
    """
    Size a low-voltage DC conductor (automotive / RV / marine / battery).

    Unlike premises wiring, voltage drop is the governing design constraint at
    12/24/48 V, so this sizes the conductor to satisfy BOTH the free-air
    ("chassis wiring") ampacity floor and the voltage-drop target. The target is
    user-set; the common conventions are 3% for critical circuits (pumps,
    electronics, main feeders) and 10% for non-critical circuits (general
    lighting).

    Ampacity is the single-wire-in-free-air value (see
    get_automotive_ampacity_table) reduced by a grouping/bundling derate for
    multiple bundled conductors. A suggested fuse (protecting the conductor) is
    also returned.

    ---Parameters---
    load_current_a : float
        Continuous load current in amperes.
    voltage_v : float
        DC system voltage (e.g. 12, 24, 48).
    length_m : float
        One-way run length in meters (doubled for round-trip drop).
    num_conductors : int
        Bundled current-carrying conductors. Default: 1 (single in free air).
    max_voltage_drop_percent : float
        Voltage-drop target. Default: 3.0% (critical). Use 10% for non-critical.
    material : str
        "copper" (default) or "aluminum". Automotive wiring is copper.

    ---Returns---
    result : dict
        recommended_size, ampacities, voltage-drop, a suggested fuse, and a
        verdict {status, headline, binding_constraint, reasons, checks}. Both
        ``ampacity`` and ``voltage_drop`` are mandatory checks here.

    ---LaTeX---
    V_{drop} = I \\cdot R \\cdot 2L, \\quad V_{drop\\%} = 100 \\cdot V_{drop} / V

    ---References---
    Free-air ("chassis wiring") AWG ampacity chart; ABYC E-11 voltage-drop
    conventions (3% critical / 10% non-critical).
    """
    if load_current_a <= 0:
        raise ValueError("Load current must be positive")
    if voltage_v <= 0:
        raise ValueError("Voltage must be positive")
    if length_m <= 0:
        raise ValueError("Length must be positive")

    table = get_automotive_ampacity_table()
    sizes = list(table.keys())  # small -> large (insertion order)
    bundling = get_bundling_factor(num_conductors)
    round_trip = 2.0 * length_m

    def vdrop(size: str):
        r_per_m = get_resistance_per_meter(size, material, RESISTANCE_REF_TEMP_C)
        vd = load_current_a * r_per_m * round_trip
        return vd, (vd / voltage_v) * 100.0, r_per_m

    # Stage 1: smallest conductor meeting the ampacity floor.
    amp_min = None
    for size in sizes:
        if table[size] * bundling >= load_current_a - 1e-9:
            amp_min = size
            break
    if amp_min is None:
        amp_min = sizes[-1]

    # Stage 2: from there, smallest that also meets the voltage-drop target.
    start = sizes.index(amp_min)
    chosen = None
    for size in sizes[start:]:
        _, pct, _ = vdrop(size)
        if pct <= max_voltage_drop_percent:
            chosen = size
            break
    vd_within_target = chosen is not None
    if chosen is None:
        chosen = sizes[-1]  # nothing meets the target; report the largest

    size = chosen
    voltage_drop_v, voltage_drop_percent, r_per_m = vdrop(size)
    free_air_ampacity = table[size]
    ampacity = free_air_ampacity * bundling
    ampacity_ok = ampacity >= load_current_a - 1e-9

    # Suggested fuse: smallest standard rating >= load and <= conductor ampacity.
    fuse_rating = None
    for f in DC_STANDARD_FUSE_RATINGS:
        if f >= load_current_a - 1e-9 and f <= ampacity + 1e-9:
            fuse_rating = f
            break

    checks = {"ampacity": bool(ampacity_ok), "voltage_drop": bool(vd_within_target)}
    reasons: List[str] = []
    if not ampacity_ok:
        reasons.append(
            f"No standard gauge carries {load_current_a:.0f} A in free air "
            f"(largest is {free_air_ampacity:.0f} A x {bundling:.2f} derate).")
    if not vd_within_target:
        reasons.append(
            f"No standard gauge holds voltage drop <= {max_voltage_drop_percent:.0f}% "
            f"on this run; smallest achievable is {voltage_drop_percent:.1f}%.")

    if not all(checks.values()):
        status = "fail"
        binding = "ampacity" if not ampacity_ok else "voltage_drop"
        headline = f"FAIL — {reasons[0]}"
    else:
        status = "pass"
        binding = "voltage_drop"  # the governing design constraint at low voltage
        headline = (f"Pass — {size} {material}, {voltage_drop_percent:.1f}% drop"
                    + (f", {fuse_rating} A fuse." if fuse_rating else "."))

    return {
        "load_current_a": load_current_a,
        "voltage_v": voltage_v,
        "length_m": length_m,
        "num_conductors": num_conductors,
        "material": material,
        "max_voltage_drop_percent": max_voltage_drop_percent,
        "bundling_factor": bundling,
        "recommended_size": size,
        "free_air_ampacity_a": free_air_ampacity,
        "corrected_ampacity_a": ampacity,
        "ampacity_margin_percent": ((ampacity - load_current_a) / load_current_a * 100.0
                                    if load_current_a > 0 else 0.0),
        "ampacity_ok": ampacity_ok,
        "resistance_ohm": r_per_m * round_trip,
        "voltage_drop_v": voltage_drop_v,
        "voltage_drop_percent": voltage_drop_percent,
        "voltage_drop_ok": vd_within_target,
        "power_loss_w": load_current_a * load_current_a * r_per_m * round_trip,
        "fuse": {"rating_a": fuse_rating},
        "verdict": {
            "status": status,
            "headline": headline,
            "binding_constraint": binding,
            "reasons": reasons,
            "checks": checks,
        },
    }


# =============================================================================
# Motor circuits — NEC Article 430 (FLC tables + sizing)
# =============================================================================
#
# Full-load currents from NEC Tables 430.248 (single-phase) and 430.250
# (three-phase). Per NEC 430.6(A)(1) these table values — NOT the nameplate —
# are used to size conductors, OCPD, and disconnects.
#
# DATA PROVENANCE (sourced & cross-checked 2026-07-18): buildmyowncabin's NEC
# 2014 reproductions, cross-checked against search-summary values which agree
# exactly (e.g. 3ph 10 HP: 28 A @230, 14 A @460; 1ph 5 HP: 28 A @230).
# UNVERIFIED by a human; the motor tool ships Experimental.

# HP -> FLC (A). Single-phase (Table 430.248).
MOTOR_FLC_1PH: Dict[int, Dict[float, float]] = {
    115: {0.166: 4.4, 0.25: 5.8, 0.333: 7.2, 0.5: 9.8, 0.75: 13.8, 1: 16,
          1.5: 20, 2: 24, 3: 34, 5: 56, 7.5: 80, 10: 100},
    230: {0.166: 2.2, 0.25: 2.9, 0.333: 3.6, 0.5: 4.9, 0.75: 6.9, 1: 8,
          1.5: 10, 2: 12, 3: 17, 5: 28, 7.5: 40, 10: 50},
}

# HP -> FLC (A). Three-phase induction (Table 430.250).
MOTOR_FLC_3PH: Dict[int, Dict[float, float]] = {
    208: {0.5: 2.4, 0.75: 3.5, 1: 4.6, 1.5: 6.6, 2: 7.5, 3: 10.6, 5: 16.7,
          7.5: 24.2, 10: 30.8, 15: 46.2, 20: 59.4, 25: 74.8, 30: 88, 40: 114,
          50: 143, 60: 169, 75: 211, 100: 273, 125: 343, 150: 396, 200: 528},
    230: {0.5: 2.2, 0.75: 3.2, 1: 4.2, 1.5: 6, 2: 6.8, 3: 9.6, 5: 15.2,
          7.5: 22, 10: 28, 15: 42, 20: 54, 25: 68, 30: 80, 40: 104, 50: 130,
          60: 154, 75: 192, 100: 248, 125: 312, 150: 360, 200: 480},
    460: {0.5: 1.1, 0.75: 1.6, 1: 2.1, 1.5: 3, 2: 3.4, 3: 4.8, 5: 7.6,
          7.5: 11, 10: 14, 15: 21, 20: 27, 25: 34, 30: 40, 40: 52, 50: 65,
          60: 77, 75: 96, 100: 124, 125: 156, 150: 180, 200: 240},
}


def get_motor_flc(hp: float, voltage_v: float, phase: str) -> float:
    """
    Full-load current (A) for a motor, per NEC Table 430.248/430.250.

    Voltage is mapped to the nearest standard motor column (single-phase:
    115/230; three-phase: 208/230/460).

    ---Parameters---
    hp : float
        Motor horsepower (must be a standard table rating).
    voltage_v : float
        Nominal system voltage.
    phase : str
        "single" or "three".

    ---Returns---
    flc : float
        Full-load current in amperes from the NEC table.

    ---References---
    NFPA 70 (NEC), 430.6(A)(1), Table 430.248, Table 430.250.
    """
    phase = phase.lower()
    if phase.startswith("s") or phase == "1":
        cols = MOTOR_FLC_1PH
    elif phase.startswith("t") or phase == "3":
        cols = MOTOR_FLC_3PH
    else:
        raise ValueError("phase must be 'single' or 'three'")
    col_v = min(cols.keys(), key=lambda v: abs(v - voltage_v))
    table = cols[col_v]
    if hp not in table:
        raise ValueError(
            f"HP {hp} not in NEC motor table for {phase}-phase; "
            f"available: {sorted(table)}")
    return table[hp]


def _select_conductor_for_ampacity(
    required_ampacity: float, material: str, insulation_temp_rating: int,
    ambient_temp_c: float, num_conductors: int, termination_rating: int,
) -> Tuple[Optional[str], float]:
    """Smallest conductor whose 110.14(C) usable ampacity >= required_ampacity.

    Returns (size, usable_ampacity). size is the largest available if none fits.
    """
    temp_factor = get_temp_correction_factor(ambient_temp_c, insulation_temp_rating)
    bundling = get_bundling_factor(num_conductors)
    derate = temp_factor * bundling
    wire_col = get_ampacity_table(material, insulation_temp_rating)
    term_col = get_ampacity_table(material, termination_rating)
    sizes = get_wire_sizes_for_material(material)
    last = sizes[-1]
    for size in sizes:
        usable = min(wire_col[size] * derate, term_col[size])
        if usable >= required_ampacity - 1e-9:
            return size, usable
    usable = min(wire_col[last] * derate, term_col[last])
    return last, usable


def evaluate_motor_circuit(
    hp: float,
    voltage_v: float,
    phase: str = "three",
    length_m: float = 0.0,
    material: str = "copper",
    insulation_temp_rating: int = 90,
    ambient_temp_c: float = 30.0,
    num_conductors: int = 3,
    max_voltage_drop_percent: float = 3.0,
    termination_rating: int = 75,
) -> dict:
    """
    Size a motor branch circuit per NEC Article 430.

    Conductor = 125% of the table FLC (430.22). Branch-circuit short-circuit /
    ground-fault OCPD = 250% of FLC for an inverse-time breaker, taken up to the
    next standard rating (430.52(C)(1) Ex. 1). That breaker does NOT protect the
    conductor from overload — a separate overload device (115-125% of nameplate,
    430.32) is required. Voltage drop is advisory.

    ---Parameters---
    hp : float
        Motor horsepower (standard NEC table rating).
    voltage_v : float
        Nominal system voltage.
    phase : str
        "single" or "three". Default: "three".
    length_m : float
        One-way run length (m) for the advisory voltage drop. Default: 0.
    material, insulation_temp_rating, ambient_temp_c, num_conductors,
    max_voltage_drop_percent, termination_rating : see evaluate_circuit.

    ---Returns---
    result : dict
        flc_a, conductor sizing current (1.25*FLC), recommended_size, usable
        ampacity, breaker (250% -> standard), an overload note, voltage-drop
        advisory, and a verdict.

    ---References---
    NFPA 70 (NEC), 430.6, 430.22, 430.52, 430.32; Tables 430.248/430.250.
    """
    flc = get_motor_flc(hp, voltage_v, phase)
    conductor_current = 1.25 * flc                       # 430.22

    size, usable = _select_conductor_for_ampacity(
        conductor_current, material, insulation_temp_rating, ambient_temp_c,
        num_conductors, termination_rating)
    ampacity_ok = usable >= conductor_current - 1e-9

    ocpd_rating = next_standard_ocpd(2.5 * flc)          # 430.52 inverse-time

    # Advisory voltage drop at FLC.
    voltage_drop_percent = 0.0
    voltage_drop_v = 0.0
    vd_within_target = True
    if length_m > 0:
        r_per_m = get_resistance_per_meter(size, material, insulation_temp_rating)
        factor = math.sqrt(3) if phase.lower().startswith("t") else 2.0
        voltage_drop_v = flc * r_per_m * factor * length_m
        voltage_drop_percent = voltage_drop_v / voltage_v * 100.0
        vd_within_target = voltage_drop_percent <= max_voltage_drop_percent

    checks = {"ampacity": bool(ampacity_ok)}
    reasons: List[str] = []
    if not ampacity_ok:
        reasons.append(
            f"No standard conductor provides the required {conductor_current:.0f} A "
            f"(125% of {flc:.1f} A FLC).")
    status = "fail" if not ampacity_ok else "pass"
    if status == "pass":
        headline = (f"Pass — {size} {material}, {ocpd_rating} A breaker "
                    f"(NEC 430; {flc:.1f} A FLC).")
        binding = "ampacity"
    else:
        headline = f"FAIL — {reasons[0]}"
        binding = "ampacity"

    overload_min = round(1.15 * flc, 1)
    overload_max = round(1.25 * flc, 1)

    return {
        "hp": hp, "voltage_v": voltage_v, "phase": phase,
        "material": material, "length_m": length_m,
        "flc_a": flc,
        "conductor_current_a": conductor_current,
        "recommended_size": size,
        "corrected_ampacity_a": usable,
        "ampacity_ok": ampacity_ok,
        "breaker": {"breaker_rating_a": ocpd_rating,
                    "required_ocpd_a": 2.5 * flc, "basis": "250% FLC (430.52)"},
        "overload": {"min_a": overload_min, "max_a": overload_max,
                     "note": "Separate overload device required at 115-125% of "
                             "the nameplate FLA (NEC 430.32)."},
        "voltage_drop_v": voltage_drop_v,
        "voltage_drop_percent": voltage_drop_percent,
        "voltage_drop_ok": vd_within_target,
        "max_voltage_drop_percent": max_voltage_drop_percent,
        "verdict": {"status": status, "headline": headline,
                    "binding_constraint": binding, "reasons": reasons,
                    "checks": checks},
    }


def evaluate_hvac_circuit(
    mca: float,
    mocp: float,
    voltage_v: float,
    length_m: float = 0.0,
    material: str = "copper",
    insulation_temp_rating: int = 90,
    ambient_temp_c: float = 30.0,
    num_conductors: int = 3,
    max_voltage_drop_percent: float = 3.0,
    termination_rating: int = 75,
    phase: str = "single",
) -> dict:
    """
    Size an air-conditioning / refrigeration circuit per NEC Article 440.

    Uses the nameplate values: the conductor ampacity must be at least the
    Minimum Circuit Ampacity (MCA), and the overcurrent device must not exceed
    the Maximum Overcurrent Protection (MOCP). The tool sizes the conductor to
    the MCA and reports the largest standard OCPD at or below the MOCP.

    ---Parameters---
    mca : float
        Minimum Circuit Ampacity from the equipment nameplate (A).
    mocp : float
        Maximum Overcurrent Protection from the nameplate (A).
    voltage_v, length_m, material, insulation_temp_rating, ambient_temp_c,
    num_conductors, max_voltage_drop_percent, termination_rating, phase :
        as elsewhere.

    ---References---
    NFPA 70 (NEC), 440.4, 440.6, 440.22, 440.32; 110.14(C).
    """
    if mca <= 0 or mocp <= 0:
        raise ValueError("MCA and MOCP must be positive")

    size, usable = _select_conductor_for_ampacity(
        mca, material, insulation_temp_rating, ambient_temp_c,
        num_conductors, termination_rating)
    ampacity_ok = usable >= mca - 1e-9

    # OCPD: largest standard rating <= MOCP (a smaller device is permitted).
    ocpd_rating = None
    for r in reversed(NEC_STANDARD_OCPD_RATINGS):
        if r <= mocp + 1e-9:
            ocpd_rating = r
            break

    voltage_drop_percent = 0.0
    voltage_drop_v = 0.0
    vd_within_target = True
    if length_m > 0:
        r_per_m = get_resistance_per_meter(size, material, insulation_temp_rating)
        factor = math.sqrt(3) if phase.lower().startswith("t") else 2.0
        voltage_drop_v = mca * r_per_m * factor * length_m
        voltage_drop_percent = voltage_drop_v / voltage_v * 100.0
        vd_within_target = voltage_drop_percent <= max_voltage_drop_percent

    checks = {"ampacity": bool(ampacity_ok)}
    reasons: List[str] = []
    if not ampacity_ok:
        reasons.append(f"No standard conductor provides the {mca:.0f} A MCA.")
    status = "fail" if not ampacity_ok else "pass"
    headline = (f"Pass — {size} {material}, up to {ocpd_rating} A breaker "
                f"(NEC 440; {mca:.0f} A MCA / {mocp:.0f} A MOCP)."
                if status == "pass" else f"FAIL — {reasons[0]}")

    return {
        "mca_a": mca, "mocp_a": mocp, "voltage_v": voltage_v,
        "material": material, "length_m": length_m,
        "recommended_size": size,
        "corrected_ampacity_a": usable,
        "ampacity_ok": ampacity_ok,
        "breaker": {"breaker_rating_a": ocpd_rating, "max_a": mocp,
                    "basis": "<= MOCP (440.22)"},
        "voltage_drop_v": voltage_drop_v,
        "voltage_drop_percent": voltage_drop_percent,
        "voltage_drop_ok": vd_within_target,
        "max_voltage_drop_percent": max_voltage_drop_percent,
        "verdict": {"status": status, "headline": headline,
                    "binding_constraint": "ampacity", "reasons": reasons,
                    "checks": checks},
    }
