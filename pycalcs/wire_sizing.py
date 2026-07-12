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

    # Round trip length for voltage drop
    if circuit_type.upper() == "DC":
        round_trip_length = 2 * length_m  # Both conductors
    else:
        round_trip_length = 2 * length_m  # Single phase: 2 conductors

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

    # Get base ampacity for the specified size
    ampacity_table = get_ampacity_table(material, insulation_temp_rating)
    base_ampacity = ampacity_table.get(wire_size)

    if base_ampacity is None:
        raise ValueError(f"Unknown wire size: {wire_size}")

    corrected_ampacity = base_ampacity * total_derating
    ampacity_margin = ((corrected_ampacity - current_a) / current_a) * 100 if current_a > 0 else 0
    ampacity_ok = corrected_ampacity >= current_a

    if not ampacity_ok:
        warnings.append(f"Wire undersized: need {current_a:.1f}A, have {corrected_ampacity:.1f}A")

    # Calculate voltage drop
    r_per_m = get_resistance_per_meter(wire_size, material, insulation_temp_rating)

    if circuit_type.upper() == "DC":
        round_trip_length = 2 * length_m
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

# Verdict tuning: how much headroom before a passing result is only "marginal".
_AMPACITY_MARGINAL_PCT = 10.0   # < 10% ampacity headroom -> marginal
_VDROP_MARGINAL_FRACTION = 0.9  # within 10% of the VD limit -> marginal


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
) -> dict:
    """
    Full NEC branch-circuit evaluation with a single pass/fail verdict.

    Runs conductor sizing (ampacity + voltage drop), selects the overcurrent
    device (NEC 240.6/210.20), verifies the device protects the conductor
    (NEC 240.4), and — for continuous loads — checks that the conductor ampacity
    is at least 125% of the load (NEC 210.19(A)). Returns the underlying sizing
    result plus a verdict identifying the binding constraint.

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
        The ``calculate_wire_size`` dict, augmented with ``breaker`` (selection),
        ``protection`` (240.4 check), a ``continuous_conductor_ok`` flag, and a
        ``verdict`` = {status, headline, binding_constraint, reasons, checks}.
        ``status`` is one of "pass", "marginal", "fail".

    ---References---
    NFPA 70 (NEC), 210.19(A), 210.20(A), 240.4, 240.6, 310.16.
    """
    breaker = select_breaker(current_a, continuous_load)
    breaker_rating = breaker["breaker_rating_a"]
    sizes = get_wire_sizes_for_material(material)

    def _evaluate_size(size: str):
        """Return (check_dict, protection_dict, continuous_ok) for one size."""
        chk = check_wire_size(
            size, current_a, voltage_v, length_m, material,
            insulation_temp_rating, ambient_temp_c, num_conductors,
            max_voltage_drop_percent, circuit_type,
        )
        if breaker_rating is None:
            prot = {"protected": False, "small_conductor_cap_a": None,
                    "allowance": "none",
                    "note": "Load exceeds the largest standard OCPD rating."}
        else:
            prot = check_conductor_protection(
                breaker_rating, chk["corrected_ampacity_a"], size, material)
        cont_ok = (chk["corrected_ampacity_a"] >= 1.25 * current_a - 1e-9
                   if continuous_load else True)
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

    # Stage 2: from that size upward, upsize to the smallest conductor that also
    # satisfies the voltage-drop limit (a larger conductor only helps).
    start = sizes.index(chosen[0])
    for size in sizes[start:]:
        chk, prot, cont_ok = _evaluate_size(size)
        if chk["voltage_drop_ok"] and chk["ampacity_ok"] and prot["protected"] and cont_ok:
            chosen = (size, chk, prot, cont_ok)
            break

    size, chk, protection, continuous_conductor_ok = chosen

    # Normalize to the calculate_wire_size field names the UI expects.
    sizing = dict(chk)
    sizing["recommended_size"] = sizing.pop("wire_size")
    sizing["recommended_base_ampacity_a"] = sizing.pop("base_ampacity_a")
    sizing["max_voltage_drop_percent"] = max_voltage_drop_percent
    derating = sizing.get("total_derating_factor") or 1.0
    sizing["required_ampacity_a"] = current_a / derating

    checks = {
        "ampacity": bool(sizing["ampacity_ok"]),
        "voltage_drop": bool(sizing["voltage_drop_ok"]),
        "overcurrent_protection": bool(protection["protected"]),
        "continuous_conductor": bool(continuous_conductor_ok),
    }

    reasons: List[str] = []
    if not checks["ampacity"]:
        reasons.append(
            f"Ampacity: corrected {sizing['corrected_ampacity_a']:.0f} A < load "
            f"{current_a:.0f} A.")
    if not checks["voltage_drop"]:
        reasons.append(
            f"Voltage drop {sizing['voltage_drop_percent']:.1f}% exceeds "
            f"{max_voltage_drop_percent:.1f}% limit.")
    if not checks["overcurrent_protection"]:
        reasons.append(protection["note"])
    if not checks["continuous_conductor"]:
        reasons.append(
            "Continuous load: conductor ampacity below 125% of load "
            "(NEC 210.19(A)); increase conductor size.")

    if not all(checks.values()):
        status = "fail"
        # Binding constraint = first failing check, in priority order.
        for key in ("ampacity", "overcurrent_protection", "continuous_conductor",
                    "voltage_drop"):
            if not checks[key]:
                binding = key
                break
        headline = f"FAIL — {reasons[0]}"
    else:
        # All pass: flag marginal cases and report the tightest constraint.
        vd_fraction = (sizing["voltage_drop_percent"] / max_voltage_drop_percent
                       if max_voltage_drop_percent > 0 else 0.0)
        amp_marginal = sizing["ampacity_margin_percent"] < _AMPACITY_MARGINAL_PCT
        vd_marginal = vd_fraction >= _VDROP_MARGINAL_FRACTION
        if amp_marginal or vd_marginal:
            status = "marginal"
        else:
            status = "pass"
        # Tightest constraint: whichever has less headroom.
        binding = "voltage_drop" if vd_fraction >= (
            1.0 - sizing["ampacity_margin_percent"] / 100.0) else "ampacity"
        verb = "Marginal" if status == "marginal" else "Pass"
        headline = (
            f"{verb} — {sizing['recommended_size']} {material}, "
            f"{breaker_rating} A breaker, VD {sizing['voltage_drop_percent']:.1f}%.")

    sizing["breaker"] = breaker
    sizing["protection"] = protection
    sizing["continuous_load"] = continuous_load
    sizing["continuous_conductor_ok"] = continuous_conductor_ok
    sizing["verdict"] = {
        "status": status,
        "headline": headline,
        "binding_constraint": binding,
        "reasons": reasons,
        "checks": checks,
    }
    return sizing
