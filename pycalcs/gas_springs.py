# gas_springs.py
"""
Gas Spring Calculator for hinged panels (trap doors, hatches, lids).

This module provides physics-based calculations for sizing and analyzing
gas springs used to assist or counterbalance hinged panel mechanisms.

Includes a comprehensive catalog of standard gas springs based on industry
specifications from manufacturers like Suspa, Stabilus, and others.
"""
import math
from typing import Dict, List, Tuple, Any, Optional

# Gravitational acceleration (m/s²)
G = 9.81

# =============================================================================
# STANDARD GAS SPRING CATALOG
# Based on industry specifications from Suspa, Stabilus, Metrol, and others
# Organized by series (rod diameter / tube diameter)
# =============================================================================

GAS_SPRING_CATALOG = [
    # 6/15 Series - Light duty (rod 6mm, tube 15mm)
    # Force range: 50-400N, typical for cabinet doors, small hatches
    {"series": "6/15", "stroke_mm": 50, "extended_mm": 175, "compressed_mm": 125, "force_n": 50, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 50, "extended_mm": 175, "compressed_mm": 125, "force_n": 100, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 50, "extended_mm": 175, "compressed_mm": 125, "force_n": 150, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 50, "extended_mm": 175, "compressed_mm": 125, "force_n": 200, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 80, "extended_mm": 245, "compressed_mm": 165, "force_n": 50, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 80, "extended_mm": 245, "compressed_mm": 165, "force_n": 100, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 80, "extended_mm": 245, "compressed_mm": 165, "force_n": 150, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 80, "extended_mm": 245, "compressed_mm": 165, "force_n": 200, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 80, "extended_mm": 245, "compressed_mm": 165, "force_n": 250, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 100, "extended_mm": 305, "compressed_mm": 205, "force_n": 50, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 100, "extended_mm": 305, "compressed_mm": 205, "force_n": 100, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 100, "extended_mm": 305, "compressed_mm": 205, "force_n": 150, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 100, "extended_mm": 305, "compressed_mm": 205, "force_n": 200, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 100, "extended_mm": 305, "compressed_mm": 205, "force_n": 250, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 100, "extended_mm": 305, "compressed_mm": 205, "force_n": 300, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 120, "extended_mm": 355, "compressed_mm": 235, "force_n": 100, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 120, "extended_mm": 355, "compressed_mm": 235, "force_n": 150, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 120, "extended_mm": 355, "compressed_mm": 235, "force_n": 200, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 120, "extended_mm": 355, "compressed_mm": 235, "force_n": 250, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 120, "extended_mm": 355, "compressed_mm": 235, "force_n": 300, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 150, "extended_mm": 430, "compressed_mm": 280, "force_n": 100, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 150, "extended_mm": 430, "compressed_mm": 280, "force_n": 150, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 150, "extended_mm": 430, "compressed_mm": 280, "force_n": 200, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 150, "extended_mm": 430, "compressed_mm": 280, "force_n": 250, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 150, "extended_mm": 430, "compressed_mm": 280, "force_n": 300, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 150, "extended_mm": 430, "compressed_mm": 280, "force_n": 350, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 150, "extended_mm": 430, "compressed_mm": 280, "force_n": 400, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 200, "extended_mm": 555, "compressed_mm": 355, "force_n": 100, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 200, "extended_mm": 555, "compressed_mm": 355, "force_n": 150, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 200, "extended_mm": 555, "compressed_mm": 355, "force_n": 200, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 200, "extended_mm": 555, "compressed_mm": 355, "force_n": 250, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 200, "extended_mm": 555, "compressed_mm": 355, "force_n": 300, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 200, "extended_mm": 555, "compressed_mm": 355, "force_n": 350, "rod_mm": 6, "tube_mm": 15},
    {"series": "6/15", "stroke_mm": 200, "extended_mm": 555, "compressed_mm": 355, "force_n": 400, "rod_mm": 6, "tube_mm": 15},

    # 8/18 Series - Medium duty (rod 8mm, tube 18mm)
    # Force range: 80-750N, typical for toolbox lids, equipment covers
    {"series": "8/18", "stroke_mm": 80, "extended_mm": 265, "compressed_mm": 185, "force_n": 100, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 80, "extended_mm": 265, "compressed_mm": 185, "force_n": 150, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 80, "extended_mm": 265, "compressed_mm": 185, "force_n": 200, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 80, "extended_mm": 265, "compressed_mm": 185, "force_n": 250, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 100, "extended_mm": 315, "compressed_mm": 215, "force_n": 100, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 100, "extended_mm": 315, "compressed_mm": 215, "force_n": 150, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 100, "extended_mm": 315, "compressed_mm": 215, "force_n": 200, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 100, "extended_mm": 315, "compressed_mm": 215, "force_n": 250, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 100, "extended_mm": 315, "compressed_mm": 215, "force_n": 300, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 100, "extended_mm": 315, "compressed_mm": 215, "force_n": 400, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 150, "extended_mm": 440, "compressed_mm": 290, "force_n": 150, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 150, "extended_mm": 440, "compressed_mm": 290, "force_n": 200, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 150, "extended_mm": 440, "compressed_mm": 290, "force_n": 250, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 150, "extended_mm": 440, "compressed_mm": 290, "force_n": 300, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 150, "extended_mm": 440, "compressed_mm": 290, "force_n": 400, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 150, "extended_mm": 440, "compressed_mm": 290, "force_n": 500, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 200, "extended_mm": 565, "compressed_mm": 365, "force_n": 150, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 200, "extended_mm": 565, "compressed_mm": 365, "force_n": 200, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 200, "extended_mm": 565, "compressed_mm": 365, "force_n": 250, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 200, "extended_mm": 565, "compressed_mm": 365, "force_n": 300, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 200, "extended_mm": 565, "compressed_mm": 365, "force_n": 400, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 200, "extended_mm": 565, "compressed_mm": 365, "force_n": 500, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 200, "extended_mm": 565, "compressed_mm": 365, "force_n": 600, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 250, "extended_mm": 690, "compressed_mm": 440, "force_n": 200, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 250, "extended_mm": 690, "compressed_mm": 440, "force_n": 300, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 250, "extended_mm": 690, "compressed_mm": 440, "force_n": 400, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 250, "extended_mm": 690, "compressed_mm": 440, "force_n": 500, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 250, "extended_mm": 690, "compressed_mm": 440, "force_n": 600, "rod_mm": 8, "tube_mm": 18},
    {"series": "8/18", "stroke_mm": 250, "extended_mm": 690, "compressed_mm": 440, "force_n": 750, "rod_mm": 8, "tube_mm": 18},

    # 10/22 Series - Heavy duty (rod 10mm, tube 22mm)
    # Force range: 100-1200N, typical for trap doors, heavy hatches
    {"series": "10/22", "stroke_mm": 100, "extended_mm": 335, "compressed_mm": 235, "force_n": 150, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 100, "extended_mm": 335, "compressed_mm": 235, "force_n": 200, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 100, "extended_mm": 335, "compressed_mm": 235, "force_n": 300, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 100, "extended_mm": 335, "compressed_mm": 235, "force_n": 400, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 150, "extended_mm": 460, "compressed_mm": 310, "force_n": 200, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 150, "extended_mm": 460, "compressed_mm": 310, "force_n": 300, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 150, "extended_mm": 460, "compressed_mm": 310, "force_n": 400, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 150, "extended_mm": 460, "compressed_mm": 310, "force_n": 500, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 150, "extended_mm": 460, "compressed_mm": 310, "force_n": 600, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 200, "extended_mm": 585, "compressed_mm": 385, "force_n": 200, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 200, "extended_mm": 585, "compressed_mm": 385, "force_n": 300, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 200, "extended_mm": 585, "compressed_mm": 385, "force_n": 400, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 200, "extended_mm": 585, "compressed_mm": 385, "force_n": 500, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 200, "extended_mm": 585, "compressed_mm": 385, "force_n": 600, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 200, "extended_mm": 585, "compressed_mm": 385, "force_n": 800, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 250, "extended_mm": 710, "compressed_mm": 460, "force_n": 300, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 250, "extended_mm": 710, "compressed_mm": 460, "force_n": 400, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 250, "extended_mm": 710, "compressed_mm": 460, "force_n": 500, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 250, "extended_mm": 710, "compressed_mm": 460, "force_n": 600, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 250, "extended_mm": 710, "compressed_mm": 460, "force_n": 800, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 250, "extended_mm": 710, "compressed_mm": 460, "force_n": 1000, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 300, "extended_mm": 835, "compressed_mm": 535, "force_n": 400, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 300, "extended_mm": 835, "compressed_mm": 535, "force_n": 500, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 300, "extended_mm": 835, "compressed_mm": 535, "force_n": 600, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 300, "extended_mm": 835, "compressed_mm": 535, "force_n": 800, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 300, "extended_mm": 835, "compressed_mm": 535, "force_n": 1000, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 300, "extended_mm": 835, "compressed_mm": 535, "force_n": 1200, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 400, "extended_mm": 1085, "compressed_mm": 685, "force_n": 500, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 400, "extended_mm": 1085, "compressed_mm": 685, "force_n": 600, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 400, "extended_mm": 1085, "compressed_mm": 685, "force_n": 800, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 400, "extended_mm": 1085, "compressed_mm": 685, "force_n": 1000, "rod_mm": 10, "tube_mm": 22},
    {"series": "10/22", "stroke_mm": 400, "extended_mm": 1085, "compressed_mm": 685, "force_n": 1200, "rod_mm": 10, "tube_mm": 22},

    # 14/28 Series - Extra heavy duty (rod 14mm, tube 28mm)
    # Force range: 200-2500N, typical for large doors, industrial applications
    {"series": "14/28", "stroke_mm": 150, "extended_mm": 490, "compressed_mm": 340, "force_n": 300, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 150, "extended_mm": 490, "compressed_mm": 340, "force_n": 400, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 150, "extended_mm": 490, "compressed_mm": 340, "force_n": 500, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 150, "extended_mm": 490, "compressed_mm": 340, "force_n": 600, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 200, "extended_mm": 615, "compressed_mm": 415, "force_n": 400, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 200, "extended_mm": 615, "compressed_mm": 415, "force_n": 500, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 200, "extended_mm": 615, "compressed_mm": 415, "force_n": 600, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 200, "extended_mm": 615, "compressed_mm": 415, "force_n": 800, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 200, "extended_mm": 615, "compressed_mm": 415, "force_n": 1000, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 250, "extended_mm": 740, "compressed_mm": 490, "force_n": 500, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 250, "extended_mm": 740, "compressed_mm": 490, "force_n": 600, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 250, "extended_mm": 740, "compressed_mm": 490, "force_n": 800, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 250, "extended_mm": 740, "compressed_mm": 490, "force_n": 1000, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 250, "extended_mm": 740, "compressed_mm": 490, "force_n": 1200, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 300, "extended_mm": 865, "compressed_mm": 565, "force_n": 600, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 300, "extended_mm": 865, "compressed_mm": 565, "force_n": 800, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 300, "extended_mm": 865, "compressed_mm": 565, "force_n": 1000, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 300, "extended_mm": 865, "compressed_mm": 565, "force_n": 1200, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 300, "extended_mm": 865, "compressed_mm": 565, "force_n": 1500, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 400, "extended_mm": 1115, "compressed_mm": 715, "force_n": 800, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 400, "extended_mm": 1115, "compressed_mm": 715, "force_n": 1000, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 400, "extended_mm": 1115, "compressed_mm": 715, "force_n": 1200, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 400, "extended_mm": 1115, "compressed_mm": 715, "force_n": 1500, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 400, "extended_mm": 1115, "compressed_mm": 715, "force_n": 2000, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 500, "extended_mm": 1365, "compressed_mm": 865, "force_n": 1000, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 500, "extended_mm": 1365, "compressed_mm": 865, "force_n": 1200, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 500, "extended_mm": 1365, "compressed_mm": 865, "force_n": 1500, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 500, "extended_mm": 1365, "compressed_mm": 865, "force_n": 2000, "rod_mm": 14, "tube_mm": 28},
    {"series": "14/28", "stroke_mm": 500, "extended_mm": 1365, "compressed_mm": 865, "force_n": 2500, "rod_mm": 14, "tube_mm": 28},
]

# Force thresholds for hand force classification (Newtons)
FORCE_THRESHOLD_GOOD = 20      # Under 20N is easy (about 2kg)
FORCE_THRESHOLD_ACCEPTABLE = 40  # Under 40N is acceptable (about 4kg)
FORCE_THRESHOLD_HIGH = 60      # Under 60N is manageable but hard
# Above 60N is considered difficult/dangerous


def get_catalog() -> List[Dict]:
    """
    Return the complete gas spring catalog.

    Returns
    -------
    list
        List of gas spring specifications with keys:
        - series: Size series (e.g., "6/15")
        - stroke_mm: Stroke length in mm
        - extended_mm: Extended length in mm
        - compressed_mm: Compressed length in mm
        - force_n: Rated force in Newtons
        - rod_mm: Rod diameter in mm
        - tube_mm: Tube diameter in mm
    """
    return GAS_SPRING_CATALOG.copy()


def find_compatible_springs(
    required_stroke_mm: float,
    min_force_n: float,
    max_force_n: float,
    max_extended_mm: Optional[float] = None,
    num_springs: int = 1
) -> List[Dict]:
    """
    Find gas springs from catalog that meet the requirements.

    Parameters
    ----------
    required_stroke_mm : float
        Minimum required stroke in mm
    min_force_n : float
        Minimum acceptable force per spring (N)
    max_force_n : float
        Maximum acceptable force per spring (N)
    max_extended_mm : float, optional
        Maximum acceptable extended length in mm
    num_springs : int
        Number of springs (affects force requirements)

    Returns
    -------
    list
        List of compatible gas springs, sorted by closeness to optimal force
    """
    target_force = (min_force_n + max_force_n) / 2
    compatible = []

    for spring in GAS_SPRING_CATALOG:
        # Check stroke
        if spring["stroke_mm"] < required_stroke_mm:
            continue

        # Check force range
        if spring["force_n"] < min_force_n or spring["force_n"] > max_force_n:
            continue

        # Check extended length constraint
        if max_extended_mm and spring["extended_mm"] > max_extended_mm:
            continue

        # Add with score (lower is better)
        score = abs(spring["force_n"] - target_force)
        compatible.append({**spring, "score": score})

    # Sort by score (best match first)
    compatible.sort(key=lambda x: x["score"])
    return compatible


def classify_hand_force(force_n: float) -> str:
    """
    Classify hand force into a category.

    Parameters
    ----------
    force_n : float
        Absolute hand force in Newtons

    Returns
    -------
    str
        Classification: "good", "acceptable", "high", or "excessive"
    """
    force_abs = abs(force_n)
    if force_abs <= FORCE_THRESHOLD_GOOD:
        return "good"
    elif force_abs <= FORCE_THRESHOLD_ACCEPTABLE:
        return "acceptable"
    elif force_abs <= FORCE_THRESHOLD_HIGH:
        return "high"
    else:
        return "excessive"


def check_spring_fit(
    door_mount_fraction: float,
    door_length: float,
    frame_mount_x: float,
    frame_mount_y: float,
    open_angle: float,
    spring_compressed_mm: float,
    spring_extended_mm: float,
    closed_angle: float = 0.0
) -> Dict[str, Any]:
    """
    Check if a spring with fixed dimensions fits the geometry.

    For a catalog spring with known compressed and extended lengths,
    check whether the frame mount position allows the spring to operate
    within its physical limits throughout the door's range of motion.

    Parameters
    ----------
    door_mount_fraction : float
        Door mount position as fraction of door length
    door_length : float
        Door length in meters
    frame_mount_x : float
        Frame mount X position (m)
    frame_mount_y : float
        Frame mount Y position (m)
    open_angle : float
        Maximum open angle (degrees)
    spring_compressed_mm : float
        Spring compressed length in mm
    spring_extended_mm : float
        Spring extended length in mm
    closed_angle : float
        Closed angle in degrees (default 0)

    Returns
    -------
    dict
        - fits: bool, whether spring fits throughout motion
        - min_length_mm: minimum spring length required
        - max_length_mm: maximum spring length required
        - over_compressed: bool, spring would be over-compressed
        - over_extended: bool, spring would be over-extended
    """
    door_mount_distance = door_length * door_mount_fraction

    # Check spring length at closed and open angles, plus intermediate
    angles_to_check = [closed_angle, open_angle]
    # Add intermediate angles for non-monotonic cases
    for a in range(int(closed_angle), int(open_angle) + 1, 10):
        if a not in angles_to_check:
            angles_to_check.append(a)

    spring_lengths = []
    for angle in angles_to_check:
        geom = calculate_spring_geometry(
            door_mount_distance, frame_mount_x, frame_mount_y, angle
        )
        spring_lengths.append(geom["spring_length"] * 1000)  # Convert to mm

    min_length_mm = min(spring_lengths)
    max_length_mm = max(spring_lengths)

    over_compressed = min_length_mm < spring_compressed_mm
    over_extended = max_length_mm > spring_extended_mm

    return {
        "fits": not over_compressed and not over_extended,
        "min_length_mm": min_length_mm,
        "max_length_mm": max_length_mm,
        "over_compressed": over_compressed,
        "over_extended": over_extended,
        "spring_compressed_mm": spring_compressed_mm,
        "spring_extended_mm": spring_extended_mm
    }


def calculate_force_zone_grid(
    door_mass: float,
    door_length: float,
    cg_fraction: float,
    door_mount_fraction: float,
    spring_force: float,
    open_angle: float,
    num_springs: int = 1,
    x_range: Tuple[float, float] = (-0.5, 1.0),
    y_range: Tuple[float, float] = (-0.5, 0.5),
    resolution: int = 20,
    spring_compressed_mm: Optional[float] = None,
    spring_extended_mm: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate a grid of force zones for frame mount positions.

    This creates a heatmap showing which frame mount positions result
    in good (green), acceptable (yellow), high (orange), or excessive (red)
    hand forces.

    When spring dimensions are provided (catalog spring), positions where
    the spring would be over-extended or over-compressed are marked invalid.

    Parameters
    ----------
    door_mass : float
        Door mass in kg
    door_length : float
        Door length in m
    cg_fraction : float
        Center of gravity fraction
    door_mount_fraction : float
        Door mount position fraction
    spring_force : float
        Spring force per spring in N
    open_angle : float
        Open angle in degrees
    num_springs : int
        Number of springs
    x_range : tuple
        (min, max) X position range for frame mount (m)
    y_range : tuple
        (min, max) Y position range for frame mount (m)
    resolution : int
        Grid resolution (points per axis)
    spring_compressed_mm : float, optional
        Fixed compressed length of catalog spring (mm)
    spring_extended_mm : float, optional
        Fixed extended length of catalog spring (mm)

    Returns
    -------
    dict
        - x_positions: List of X positions
        - y_positions: List of Y positions
        - zones: 2D list of zone classifications
        - max_hand_forces: 2D list of max hand forces
        - thresholds: Dict of force thresholds
        - has_constraints: Whether spring dimension constraints are active
    """
    x_positions = [x_range[0] + (x_range[1] - x_range[0]) * i / (resolution - 1)
                   for i in range(resolution)]
    y_positions = [y_range[0] + (y_range[1] - y_range[0]) * i / (resolution - 1)
                   for i in range(resolution)]

    has_constraints = spring_compressed_mm is not None and spring_extended_mm is not None
    zones = []
    max_hand_forces = []

    for y in y_positions:
        row_zones = []
        row_forces = []
        for x in x_positions:
            # First check if spring fits (if constraints provided)
            if has_constraints:
                fit_check = check_spring_fit(
                    door_mount_fraction, door_length, x, y, open_angle,
                    spring_compressed_mm, spring_extended_mm
                )
                if not fit_check["fits"]:
                    if fit_check["over_extended"]:
                        row_zones.append("over_extended")
                    else:
                        row_zones.append("over_compressed")
                    row_forces.append(float('inf'))
                    continue

            try:
                result = analyze_mechanism(
                    door_mass=door_mass,
                    door_length=door_length,
                    cg_fraction=cg_fraction,
                    door_mount_fraction=door_mount_fraction,
                    frame_mount_x=x,
                    frame_mount_y=y,
                    spring_force=spring_force,
                    open_angle=open_angle,
                    num_springs=num_springs,
                    angle_step=5.0  # Coarser for speed
                )
                max_force = max(abs(result["max_hand_force"]),
                              abs(result["min_hand_force"]))
                zone = classify_hand_force(max_force)
            except Exception:
                max_force = float('inf')
                zone = "invalid"

            row_zones.append(zone)
            row_forces.append(max_force)

        zones.append(row_zones)
        max_hand_forces.append(row_forces)

    return {
        "x_positions": x_positions,
        "y_positions": y_positions,
        "zones": zones,
        "max_hand_forces": max_hand_forces,
        "thresholds": {
            "good": FORCE_THRESHOLD_GOOD,
            "acceptable": FORCE_THRESHOLD_ACCEPTABLE,
            "high": FORCE_THRESHOLD_HIGH
        },
        "has_constraints": has_constraints
    }


def calculate_force_at_position(
    door_mass: float,
    door_length: float,
    cg_fraction: float,
    door_mount_fraction: float,
    frame_mount_x: float,
    frame_mount_y: float,
    spring_force: float,
    open_angle: float,
    num_springs: int = 1,
    spring_compressed_mm: Optional[float] = None,
    spring_extended_mm: Optional[float] = None
) -> Dict[str, Any]:
    """
    Quick calculation of max hand force at a given frame mount position.

    Used for real-time feedback during dragging.

    Parameters
    ----------
    spring_compressed_mm : float, optional
        Fixed compressed length of catalog spring (mm)
    spring_extended_mm : float, optional
        Fixed extended length of catalog spring (mm)

    Returns
    -------
    dict
        - max_hand_force: Peak hand force (N)
        - zone: Force classification
        - spring_stroke_mm: Required stroke (mm)
        - valid: Whether configuration is geometrically valid
        - spring_fits: Whether catalog spring fits (if constraints provided)
        - over_extended: Whether spring would be over-extended
        - over_compressed: Whether spring would be over-compressed
    """
    has_constraints = spring_compressed_mm is not None and spring_extended_mm is not None

    # Check spring fit first if constraints provided
    if has_constraints:
        fit_check = check_spring_fit(
            door_mount_fraction, door_length,
            frame_mount_x, frame_mount_y, open_angle,
            spring_compressed_mm, spring_extended_mm
        )
        if not fit_check["fits"]:
            zone = "over_extended" if fit_check["over_extended"] else "over_compressed"
            return {
                "max_hand_force": float('inf'),
                "zone": zone,
                "spring_stroke_mm": 0,
                "required_compressed_mm": fit_check["min_length_mm"],
                "required_extended_mm": fit_check["max_length_mm"],
                "valid": False,
                "spring_fits": False,
                "over_extended": fit_check["over_extended"],
                "over_compressed": fit_check["over_compressed"]
            }

    try:
        result = analyze_mechanism(
            door_mass=door_mass,
            door_length=door_length,
            cg_fraction=cg_fraction,
            door_mount_fraction=door_mount_fraction,
            frame_mount_x=frame_mount_x,
            frame_mount_y=frame_mount_y,
            spring_force=spring_force,
            open_angle=open_angle,
            num_springs=num_springs,
            angle_step=2.0
        )
        max_force = max(abs(result["max_hand_force"]),
                       abs(result["min_hand_force"]))
        return {
            "max_hand_force": max_force,
            "zone": classify_hand_force(max_force),
            "spring_stroke_mm": result["spring_stroke"] * 1000,
            "required_compressed_mm": result["spring_compressed"] * 1000,
            "required_extended_mm": result["spring_extended"] * 1000,
            "valid": True,
            "spring_fits": True,
            "over_extended": False,
            "over_compressed": False
        }
    except Exception as e:
        return {
            "max_hand_force": float('inf'),
            "zone": "invalid",
            "spring_stroke_mm": 0,
            "required_compressed_mm": 0,
            "required_extended_mm": 0,
            "valid": False,
            "spring_fits": False,
            "over_extended": False,
            "over_compressed": False,
            "error": str(e)
        }


def select_spring_from_catalog(
    door_mass: float,
    door_length: float,
    cg_fraction: float = 0.5,
    door_mount_fraction: float = 0.7,
    frame_mount_x: float = 0.3,
    frame_mount_y: float = -0.15,
    open_angle: float = 90.0,
    num_springs: int = 2,
    target_max_hand_force: float = 20.0
) -> Dict[str, Any]:
    """
    Select the best gas spring from the catalog for a given application.

    Finds springs that provide adequate stroke and force while minimizing
    hand effort.

    Parameters
    ----------
    door_mass : float
        Door mass in kg
    door_length : float
        Door length in m
    cg_fraction : float
        Center of gravity fraction (0.5 for uniform)
    door_mount_fraction : float
        Door mount position as fraction of length
    frame_mount_x : float
        Frame mount X position (m)
    frame_mount_y : float
        Frame mount Y position (m)
    open_angle : float
        Maximum open angle (degrees)
    num_springs : int
        Number of springs to use
    target_max_hand_force : float
        Target maximum hand force (N)

    Returns
    -------
    dict
        - recommended_spring: Best matching spring from catalog
        - alternatives: Other compatible springs
        - analysis: Full mechanism analysis with recommended spring
        - required_stroke_mm: Minimum required stroke
        - optimal_force: Calculated optimal force per spring
    """
    # First, get the required stroke
    initial = analyze_mechanism(
        door_mass=door_mass,
        door_length=door_length,
        cg_fraction=cg_fraction,
        door_mount_fraction=door_mount_fraction,
        frame_mount_x=frame_mount_x,
        frame_mount_y=frame_mount_y,
        spring_force=0,  # Just for geometry
        open_angle=open_angle,
        num_springs=num_springs
    )
    required_stroke = initial["spring_stroke"] * 1000 + 10  # Add 10mm margin

    # Get optimal force
    optimal_force = initial["optimal_spring_force"]

    # Define acceptable force range (±30% of optimal)
    min_force = optimal_force * 0.7
    max_force = optimal_force * 1.5  # Allow higher to reduce hand force

    # Find compatible springs
    compatible = find_compatible_springs(
        required_stroke_mm=required_stroke,
        min_force_n=min_force,
        max_force_n=max_force
    )

    if not compatible:
        # Try broader search
        compatible = find_compatible_springs(
            required_stroke_mm=required_stroke,
            min_force_n=optimal_force * 0.5,
            max_force_n=optimal_force * 2.0
        )

    if not compatible:
        # Return recommendation for custom spring
        return {
            "recommended_spring": None,
            "alternatives": [],
            "required_stroke_mm": required_stroke,
            "optimal_force": optimal_force,
            "message": "No standard spring found. Consider a custom spring with "
                      f"{required_stroke:.0f}mm stroke and {optimal_force:.0f}N force."
        }

    # Evaluate each compatible spring
    best_spring = None
    best_score = float('inf')
    evaluated = []

    for spring in compatible[:10]:  # Check top 10 candidates
        analysis = analyze_mechanism(
            door_mass=door_mass,
            door_length=door_length,
            cg_fraction=cg_fraction,
            door_mount_fraction=door_mount_fraction,
            frame_mount_x=frame_mount_x,
            frame_mount_y=frame_mount_y,
            spring_force=spring["force_n"],
            open_angle=open_angle,
            num_springs=num_springs
        )
        max_hand = max(abs(analysis["max_hand_force"]),
                      abs(analysis["min_hand_force"]))

        # Score: prioritize low hand force
        score = max_hand

        evaluated.append({
            **spring,
            "max_hand_force": max_hand,
            "zone": classify_hand_force(max_hand)
        })

        if score < best_score:
            best_score = score
            best_spring = {
                **spring,
                "max_hand_force": max_hand,
                "zone": classify_hand_force(max_hand)
            }

    # Sort alternatives by hand force
    evaluated.sort(key=lambda x: x["max_hand_force"])

    # Get full analysis with best spring
    if best_spring:
        final_analysis = analyze_mechanism(
            door_mass=door_mass,
            door_length=door_length,
            cg_fraction=cg_fraction,
            door_mount_fraction=door_mount_fraction,
            frame_mount_x=frame_mount_x,
            frame_mount_y=frame_mount_y,
            spring_force=best_spring["force_n"],
            open_angle=open_angle,
            num_springs=num_springs
        )
    else:
        final_analysis = None

    return {
        "recommended_spring": best_spring,
        "alternatives": evaluated[1:5] if len(evaluated) > 1 else [],
        "analysis": final_analysis,
        "required_stroke_mm": required_stroke,
        "optimal_force": optimal_force
    }


def calculate_door_moment(
    mass: float,
    cg_distance: float,
    angle_deg: float
) -> float:
    """
    Calculate gravitational moment (torque) of the door about the hinge.

    The door moment is the torque created by gravity acting on the door's
    center of mass, which varies with door angle as cos(θ).

    Parameters
    ----------
    mass : float
        Door mass in kg
    cg_distance : float
        Distance from hinge to center of gravity in meters
    angle_deg : float
        Door angle in degrees (0 = horizontal/closed, 90 = vertical/open)

    Returns
    -------
    float
        Moment in N·m (positive = tries to close door)
    """
    weight = mass * G
    angle_rad = math.radians(angle_deg)
    return weight * cg_distance * math.cos(angle_rad)


def calculate_spring_geometry(
    door_mount_distance: float,
    frame_mount_x: float,
    frame_mount_y: float,
    angle_deg: float
) -> Dict[str, float]:
    """
    Calculate spring geometry at a given door angle.

    Computes the spring length and the perpendicular lever arm
    from the hinge to the spring's line of action.

    Coordinate system:
    - Origin at hinge
    - +X along door when horizontal (θ=0)
    - +Y upward
    - Door rotates counterclockwise (opening = increasing angle)

    Parameters
    ----------
    door_mount_distance : float
        Distance from hinge to door mounting point in meters
    frame_mount_x : float
        X-coordinate of frame mounting point in meters
    frame_mount_y : float
        Y-coordinate of frame mounting point in meters
    angle_deg : float
        Door angle in degrees

    Returns
    -------
    dict
        Dictionary containing:
        - spring_length: Current spring length in meters
        - lever_arm: Perpendicular distance from hinge to spring line (m)
        - door_mount_x: X position of door mount point
        - door_mount_y: Y position of door mount point
        - spring_angle: Angle of spring from horizontal (degrees)
    """
    angle_rad = math.radians(angle_deg)

    # Door mount position (rotates with door)
    door_x = door_mount_distance * math.cos(angle_rad)
    door_y = door_mount_distance * math.sin(angle_rad)

    # Vector from frame mount to door mount
    dx = door_x - frame_mount_x
    dy = door_y - frame_mount_y

    # Spring length
    spring_length = math.sqrt(dx * dx + dy * dy)

    # Perpendicular distance from hinge (0,0) to the line through frame and door mounts
    # Using cross product formula: |OA × OB| / |AB|
    # where O is hinge, A is frame mount, B is door mount
    # Cross product in 2D: Ax*By - Ay*Bx
    cross_product = frame_mount_x * door_y - frame_mount_y * door_x

    # Lever arm is absolute value (we handle sign separately)
    if spring_length > 1e-9:
        lever_arm = abs(cross_product) / spring_length
    else:
        lever_arm = 0.0

    # Spring angle from horizontal
    if abs(dx) > 1e-9:
        spring_angle = math.degrees(math.atan2(dy, dx))
    else:
        spring_angle = 90.0 if dy > 0 else -90.0

    # Determine if spring creates opening (+) or closing (-) moment
    # Positive cross product means spring creates CCW (opening) moment
    moment_sign = 1.0 if cross_product > 0 else -1.0

    return {
        "spring_length": spring_length,
        "lever_arm": lever_arm,
        "lever_arm_signed": lever_arm * moment_sign,
        "door_mount_x": door_x,
        "door_mount_y": door_y,
        "spring_angle": spring_angle,
        "moment_sign": moment_sign
    }


def calculate_spring_force_linear(
    nominal_force: float,
    stroke: float,
    current_length: float,
    min_length: float,
    force_ratio: float = 1.0
) -> float:
    """
    Calculate gas spring force using linear force model.

    Gas springs typically have a slight force increase as they extend,
    characterized by the force ratio (F_extended / F_compressed).

    Parameters
    ----------
    nominal_force : float
        Nominal spring force in Newtons (typically rated at mid-stroke)
    stroke : float
        Total spring stroke in meters
    current_length : float
        Current spring length in meters
    min_length : float
        Minimum (fully compressed) length in meters
    force_ratio : float
        Ratio of extended force to compressed force (default 1.0 = constant)
        Typical gas springs have ratio 1.0 to 1.4

    Returns
    -------
    float
        Spring force in Newtons
    """
    if stroke < 1e-9:
        return nominal_force

    # Extension fraction (0 = compressed, 1 = extended)
    extension = (current_length - min_length) / stroke
    extension = max(0.0, min(1.0, extension))

    # For constant force spring (force_ratio = 1.0)
    if abs(force_ratio - 1.0) < 1e-9:
        return nominal_force

    # Linear interpolation between compressed and extended force
    # Compressed force is nominal / sqrt(force_ratio) to maintain nominal at mid-stroke
    f_compressed = nominal_force / math.sqrt(force_ratio)
    f_extended = f_compressed * force_ratio

    return f_compressed + (f_extended - f_compressed) * extension


def calculate_spring_moment(
    spring_force: float,
    lever_arm_signed: float
) -> float:
    """
    Calculate the moment (torque) created by the gas spring about the hinge.

    Parameters
    ----------
    spring_force : float
        Gas spring force in Newtons (always positive, pushes)
    lever_arm_signed : float
        Signed perpendicular distance from hinge to spring line (m)
        Positive = spring creates opening moment

    Returns
    -------
    float
        Moment in N·m (positive = opening, negative = closing)
    """
    return spring_force * lever_arm_signed


def calculate_hand_force(
    net_moment: float,
    hand_distance: float
) -> float:
    """
    Calculate the force required at a given point to hold/move the door.

    Parameters
    ----------
    net_moment : float
        Net moment on door in N·m (door moment - spring moment)
        Positive = door tends to close
    hand_distance : float
        Distance from hinge to where force is applied (m)

    Returns
    -------
    float
        Force in Newtons (positive = push up needed, negative = push down needed)
    """
    if abs(hand_distance) < 1e-9:
        return float('inf') if net_moment > 0 else float('-inf')
    return net_moment / hand_distance


def analyze_mechanism(
    door_mass: float,
    door_length: float,
    cg_fraction: float,
    door_mount_fraction: float,
    frame_mount_x: float,
    frame_mount_y: float,
    spring_force: float,
    open_angle: float = 90.0,
    closed_angle: float = 0.0,
    hand_position_fraction: float = 0.9,
    num_springs: int = 1,
    angle_step: float = 1.0
) -> Dict[str, Any]:
    """
    Comprehensive analysis of a gas spring assisted hinged panel.

    Analyzes the mechanism across its full range of motion, computing
    moments, forces, and hand effort required at each position.

    ---Parameters---
    door_mass : float
        Mass of the door/panel in kg
    door_length : float
        Length of door from hinge to free edge in meters
    cg_fraction : float
        Center of gravity position as fraction of door length (0=hinge, 1=edge)
        For uniform door, use 0.5
    door_mount_fraction : float
        Gas spring door attachment point as fraction of door length
    frame_mount_x : float
        Frame mount X position in meters (positive = forward from hinge)
    frame_mount_y : float
        Frame mount Y position in meters (positive = above hinge level)
    spring_force : float
        Nominal gas spring force in Newtons (per spring)
    open_angle : float
        Maximum open angle in degrees (default 90)
    closed_angle : float
        Closed angle in degrees (default 0 = horizontal)
    hand_position_fraction : float
        Position where user grips door, as fraction of length (default 0.9)
    num_springs : int
        Number of gas springs (default 1)
    angle_step : float
        Angle increment for analysis in degrees (default 1)

    ---Returns---
    angles : list
        List of angles analyzed (degrees)
    door_moments : list
        Door gravitational moment at each angle (N·m)
    spring_moments : list
        Total spring moment at each angle (N·m)
    net_moments : list
        Net moment at each angle (door - spring) (N·m)
    hand_forces : list
        Required hand force at each angle (N)
    spring_lengths : list
        Spring length at each angle (m)
    lever_arms : list
        Spring lever arm at each angle (m)
    spring_stroke : float
        Required spring stroke (max length - min length) (m)
    spring_compressed : float
        Spring length at compressed position (m)
    spring_extended : float
        Spring length at extended position (m)
    max_hand_force : float
        Maximum hand force magnitude (N)
    min_hand_force : float
        Minimum hand force magnitude (N)
    optimal_spring_force : float
        Suggested spring force to minimize peak hand effort (N)

    ---LaTeX---
    M_{door}(\\theta) = m g L_{cg} \\cos(\\theta)
    M_{spring}(\\theta) = n F_{spring} \\cdot r_{\\perp}(\\theta)
    r_{\\perp} = \\frac{|\\vec{OA} \\times \\vec{OB}|}{|\\vec{AB}|}
    M_{net}(\\theta) = M_{door}(\\theta) - M_{spring}(\\theta)
    F_{hand} = \\frac{M_{net}}{L_{hand}}
    """
    # Validate inputs
    if door_mass <= 0:
        raise ValueError("Door mass must be positive")
    if door_length <= 0:
        raise ValueError("Door length must be positive")
    if not 0 < cg_fraction <= 1:
        raise ValueError("CG fraction must be between 0 and 1")
    if not 0 < door_mount_fraction <= 1:
        raise ValueError("Door mount fraction must be between 0 and 1")
    if spring_force < 0:
        raise ValueError("Spring force cannot be negative")

    # Calculate distances
    cg_distance = door_length * cg_fraction
    door_mount_distance = door_length * door_mount_fraction
    hand_distance = door_length * hand_position_fraction
    total_spring_force = spring_force * num_springs

    # Generate angle range
    angles = []
    current_angle = closed_angle
    while current_angle <= open_angle + 1e-9:
        angles.append(current_angle)
        current_angle += angle_step
    if angles[-1] < open_angle:
        angles.append(open_angle)

    # First pass: find spring length range
    spring_lengths_temp = []
    for angle in angles:
        geom = calculate_spring_geometry(
            door_mount_distance, frame_mount_x, frame_mount_y, angle
        )
        spring_lengths_temp.append(geom["spring_length"])

    min_spring_length = min(spring_lengths_temp)
    max_spring_length = max(spring_lengths_temp)
    spring_stroke = max_spring_length - min_spring_length

    # Second pass: full analysis
    door_moments = []
    spring_moments = []
    net_moments = []
    hand_forces = []
    spring_lengths = []
    lever_arms = []

    for angle in angles:
        # Door moment (tries to close)
        m_door = calculate_door_moment(door_mass, cg_distance, angle)
        door_moments.append(m_door)

        # Spring geometry
        geom = calculate_spring_geometry(
            door_mount_distance, frame_mount_x, frame_mount_y, angle
        )
        spring_lengths.append(geom["spring_length"])
        lever_arms.append(geom["lever_arm"])

        # Spring moment (using constant force model for initial analysis)
        m_spring = calculate_spring_moment(
            total_spring_force, geom["lever_arm_signed"]
        )
        spring_moments.append(m_spring)

        # Net moment and hand force
        m_net = m_door - m_spring
        net_moments.append(m_net)

        f_hand = calculate_hand_force(m_net, hand_distance)
        hand_forces.append(f_hand)

    # Calculate statistics
    hand_forces_finite = [f for f in hand_forces if abs(f) < 1e6]
    max_hand_force = max(hand_forces_finite) if hand_forces_finite else 0.0
    min_hand_force = min(hand_forces_finite) if hand_forces_finite else 0.0

    # Calculate optimal spring force (minimizes peak hand effort)
    # We want to balance the mechanism so max positive = |max negative|
    # This requires finding the spring force where the peak moments are balanced
    optimal_spring_force = _calculate_optimal_spring_force(
        door_mass, cg_distance, door_mount_distance,
        frame_mount_x, frame_mount_y,
        angles, num_springs
    )

    return {
        "angles": angles,
        "door_moments": door_moments,
        "spring_moments": spring_moments,
        "net_moments": net_moments,
        "hand_forces": hand_forces,
        "spring_lengths": spring_lengths,
        "lever_arms": lever_arms,
        "spring_stroke": spring_stroke,
        "spring_compressed": min_spring_length,
        "spring_extended": max_spring_length,
        "max_hand_force": max_hand_force,
        "min_hand_force": min_hand_force,
        "optimal_spring_force": optimal_spring_force,
        # Substituted equations for display
        "subst_spring_stroke": f"\\text{{Stroke}} = L_{{max}} - L_{{min}} = {max_spring_length*1000:.1f}\\text{{ mm}} - {min_spring_length*1000:.1f}\\text{{ mm}} = {spring_stroke*1000:.1f}\\text{{ mm}}",
    }


def _calculate_optimal_spring_force(
    door_mass: float,
    cg_distance: float,
    door_mount_distance: float,
    frame_mount_x: float,
    frame_mount_y: float,
    angles: List[float],
    num_springs: int
) -> float:
    """
    Calculate optimal spring force to minimize peak hand effort.

    Uses weighted averaging of door moment divided by lever arm across
    the range of motion to find a spring force that balances the mechanism.
    """
    weighted_sum = 0.0
    weight_sum = 0.0

    for angle in angles:
        m_door = calculate_door_moment(door_mass, cg_distance, angle)
        geom = calculate_spring_geometry(
            door_mount_distance, frame_mount_x, frame_mount_y, angle
        )

        lever_arm = abs(geom["lever_arm_signed"])
        if lever_arm > 0.001:  # Avoid division by zero
            # Required force at this angle for equilibrium
            required_force = m_door / lever_arm

            # Weight by absolute moment (focus on high-load positions)
            weight = abs(m_door)
            weighted_sum += required_force * weight
            weight_sum += weight

    if weight_sum > 0:
        total_force = weighted_sum / weight_sum
        return total_force / max(num_springs, 1)
    else:
        return 0.0


def recommend_spring(
    door_mass: float,
    door_length: float,
    cg_fraction: float = 0.5,
    door_mount_fraction: float = 0.7,
    frame_mount_x: float = 0.0,
    frame_mount_y: float = -0.1,
    open_angle: float = 90.0,
    num_springs: int = 1,
    safety_factor: float = 1.2
) -> Dict[str, Any]:
    """
    Recommend gas spring specifications for a given door.

    Calculates optimal spring force and required stroke, then rounds
    to typical available spring sizes.

    ---Parameters---
    door_mass : float
        Mass of door in kg
    door_length : float
        Length of door from hinge to free edge in meters
    cg_fraction : float
        Center of gravity as fraction of length (default 0.5 for uniform door)
    door_mount_fraction : float
        Spring attachment point on door as fraction of length
    frame_mount_x : float
        Frame mount X position in meters
    frame_mount_y : float
        Frame mount Y position in meters
    open_angle : float
        Maximum open angle in degrees
    num_springs : int
        Number of gas springs to use
    safety_factor : float
        Safety factor to apply to calculated force (default 1.2)

    ---Returns---
    recommended_force : float
        Recommended force per spring (N)
    recommended_stroke : float
        Minimum required stroke (mm)
    total_length_estimate : float
        Estimated total spring length when compressed (mm)
    standard_forces : list
        Nearby standard force ratings (N)
    analysis : dict
        Full mechanism analysis at recommended force

    ---LaTeX---
    F_{recommended} = F_{optimal} \\times SF
    L_{stroke} = L_{extended} - L_{compressed}
    L_{total} \\approx 2.5 \\times L_{stroke} + 50\\text{ mm}
    """
    # First, analyze with zero spring force to understand the load
    initial_analysis = analyze_mechanism(
        door_mass=door_mass,
        door_length=door_length,
        cg_fraction=cg_fraction,
        door_mount_fraction=door_mount_fraction,
        frame_mount_x=frame_mount_x,
        frame_mount_y=frame_mount_y,
        spring_force=0.0,  # No spring initially
        open_angle=open_angle,
        num_springs=num_springs
    )

    # Get optimal spring force
    optimal_force = initial_analysis["optimal_spring_force"]
    recommended_force = optimal_force * safety_factor

    # Round to nearest standard spring force (typically 50N increments)
    standard_forces = [50, 75, 100, 125, 150, 200, 250, 300, 350, 400,
                       450, 500, 600, 700, 800, 900, 1000]

    # Find closest standard forces
    nearby_standards = sorted(standard_forces, key=lambda f: abs(f - recommended_force))[:3]

    # Required stroke
    stroke_mm = initial_analysis["spring_stroke"] * 1000

    # Estimate total length (typical ratio for gas springs)
    # Compressed length ≈ stroke × 2.5 + 50mm body length
    total_length_estimate = stroke_mm * 2.5 + 50

    # Re-analyze with recommended force
    final_analysis = analyze_mechanism(
        door_mass=door_mass,
        door_length=door_length,
        cg_fraction=cg_fraction,
        door_mount_fraction=door_mount_fraction,
        frame_mount_x=frame_mount_x,
        frame_mount_y=frame_mount_y,
        spring_force=recommended_force,
        open_angle=open_angle,
        num_springs=num_springs
    )

    return {
        "recommended_force": recommended_force,
        "optimal_force": optimal_force,
        "recommended_stroke": stroke_mm + 10,  # Add 10mm margin
        "min_stroke": stroke_mm,
        "total_length_estimate": total_length_estimate,
        "standard_forces": nearby_standards,
        "analysis": final_analysis,
        "spring_compressed_mm": initial_analysis["spring_compressed"] * 1000,
        "spring_extended_mm": initial_analysis["spring_extended"] * 1000,
        # Substituted equations
        "subst_recommended_force": f"F_{{rec}} = {optimal_force:.1f}\\text{{ N}} \\times {safety_factor} = {recommended_force:.1f}\\text{{ N}}",
        "subst_stroke": f"\\text{{Stroke}} = {initial_analysis['spring_extended']*1000:.1f} - {initial_analysis['spring_compressed']*1000:.1f} = {stroke_mm:.1f}\\text{{ mm}}",
    }


def optimize_mounting_points(
    door_mass: float,
    door_length: float,
    cg_fraction: float = 0.5,
    open_angle: float = 90.0,
    target_hand_force: float = 20.0,
    num_springs: int = 1
) -> Dict[str, Any]:
    """
    Find optimal mounting point configuration for a gas spring.

    Searches through reasonable mounting configurations to find one that
    minimizes peak hand force while maintaining practical spring dimensions.

    ---Parameters---
    door_mass : float
        Mass of door in kg
    door_length : float
        Length of door in meters
    cg_fraction : float
        Center of gravity fraction (default 0.5)
    open_angle : float
        Maximum open angle in degrees
    target_hand_force : float
        Target maximum hand force in Newtons
    num_springs : int
        Number of springs to use

    ---Returns---
    best_config : dict
        Best mounting configuration found
    all_configs : list
        All configurations tested with scores
    """
    best_config = None
    best_score = float('inf')
    all_configs = []

    # Search ranges
    door_mount_fractions = [0.5, 0.6, 0.7, 0.8, 0.9]
    frame_x_values = [f * door_length for f in [0.1, 0.2, 0.3, 0.4, 0.5]]
    frame_y_values = [f * door_length for f in [-0.3, -0.2, -0.1, 0.0, 0.1]]

    for door_frac in door_mount_fractions:
        for frame_x in frame_x_values:
            for frame_y in frame_y_values:
                try:
                    result = recommend_spring(
                        door_mass=door_mass,
                        door_length=door_length,
                        cg_fraction=cg_fraction,
                        door_mount_fraction=door_frac,
                        frame_mount_x=frame_x,
                        frame_mount_y=frame_y,
                        open_angle=open_angle,
                        num_springs=num_springs
                    )

                    analysis = result["analysis"]
                    max_hand = max(abs(analysis["max_hand_force"]), abs(analysis["min_hand_force"]))
                    stroke = result["min_stroke"]

                    # Score: penalize high hand force and extreme stroke
                    score = max_hand + stroke * 0.1

                    config = {
                        "door_mount_fraction": door_frac,
                        "frame_mount_x": frame_x,
                        "frame_mount_y": frame_y,
                        "recommended_force": result["recommended_force"],
                        "stroke_mm": stroke,
                        "max_hand_force": max_hand,
                        "score": score
                    }
                    all_configs.append(config)

                    if score < best_score:
                        best_score = score
                        best_config = config

                except Exception:
                    continue

    # Sort by score
    all_configs.sort(key=lambda x: x["score"])

    return {
        "best_config": best_config,
        "top_configs": all_configs[:5]
    }
