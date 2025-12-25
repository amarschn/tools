"""
VDI 2230-style bolted joint analysis with ISO and SAE/ASTM fastener databases.

This module provides comprehensive calculations for preloaded bolted joints
including torque-tension relationships, joint stiffness analysis, embedding
losses, and safety factor verification per VDI 2230:2015.

References:
    - VDI 2230:2015 - Systematic calculation of highly stressed bolted joints
    - ISO 898-1:2013 - Mechanical properties of fasteners (metric)
    - SAE J429 - Mechanical and Material Requirements for Externally Threaded Fasteners
    - ASME B1.1 - Unified Inch Screw Threads
    - ISO 262 - ISO general purpose metric screw threads
    - Bickford, J.H. (2007), Introduction to the Design and Behavior of Bolted Joints
    - Shigley's Mechanical Engineering Design, 11th ed., Chapter 8
"""

from __future__ import annotations

import math
from typing import Dict, Tuple, Any, List


# =============================================================================
# BOLT GRADE DATABASES
# =============================================================================

# ISO Metric Bolt Grades per ISO 898-1:2013
# Format: grade -> (proof_strength_MPa, tensile_strength_MPa, yield_strength_MPa)
ISO_BOLT_GRADES: Dict[str, Dict[str, float]] = {
    "4.6": {
        "proof_strength": 225e6,      # Rp0.2 approximation
        "tensile_strength": 400e6,    # Rm min
        "yield_strength": 240e6,      # ReL min
        "elastic_modulus": 205e9,
        "description": "Low/medium carbon steel",
    },
    "5.6": {
        "proof_strength": 280e6,
        "tensile_strength": 500e6,
        "yield_strength": 300e6,
        "elastic_modulus": 205e9,
        "description": "Medium carbon steel",
    },
    "8.8": {
        "proof_strength": 640e6,      # 0.8 × Rm
        "tensile_strength": 800e6,
        "yield_strength": 640e6,
        "elastic_modulus": 205e9,
        "description": "Medium carbon steel, quenched and tempered",
    },
    "10.9": {
        "proof_strength": 830e6,
        "tensile_strength": 1040e6,
        "yield_strength": 940e6,
        "elastic_modulus": 205e9,
        "description": "Alloy steel, quenched and tempered",
    },
    "12.9": {
        "proof_strength": 970e6,
        "tensile_strength": 1220e6,
        "yield_strength": 1100e6,
        "elastic_modulus": 205e9,
        "description": "Alloy steel, quenched and tempered",
    },
}

# SAE/ASTM Bolt Grades per SAE J429 and ASTM specifications
SAE_BOLT_GRADES: Dict[str, Dict[str, float]] = {
    "SAE Grade 2": {
        "proof_strength": 310e6,      # 45 ksi (1/4-3/4)
        "tensile_strength": 448e6,    # 65 ksi min
        "yield_strength": 352e6,      # 51 ksi
        "elastic_modulus": 207e9,
        "description": "Low/medium carbon steel",
    },
    "SAE Grade 5": {
        "proof_strength": 586e6,      # 85 ksi
        "tensile_strength": 827e6,    # 120 ksi min
        "yield_strength": 634e6,      # 92 ksi
        "elastic_modulus": 207e9,
        "description": "Medium carbon steel, quenched and tempered",
    },
    "SAE Grade 8": {
        "proof_strength": 827e6,      # 120 ksi
        "tensile_strength": 1034e6,   # 150 ksi min
        "yield_strength": 896e6,      # 130 ksi
        "elastic_modulus": 207e9,
        "description": "Medium carbon alloy steel, Q&T",
    },
    "ASTM A325": {
        "proof_strength": 586e6,      # 85 ksi min
        "tensile_strength": 827e6,    # 120 ksi min
        "yield_strength": 634e6,      # 92 ksi
        "elastic_modulus": 207e9,
        "description": "Structural bolt, medium carbon steel",
    },
    "ASTM A490": {
        "proof_strength": 827e6,      # 120 ksi min
        "tensile_strength": 1034e6,   # 150 ksi min
        "yield_strength": 896e6,      # 130 ksi
        "elastic_modulus": 207e9,
        "description": "Structural bolt, alloy steel",
    },
}


# =============================================================================
# FASTENER GEOMETRY DATABASES
# =============================================================================

# ISO Metric Thread Geometry per ISO 262 and ISO 724
# Format: designation -> (nominal_d_mm, pitch_mm, stress_area_mm2, minor_d_mm, pitch_d_mm)
ISO_FASTENER_GEOMETRY: Dict[str, Dict[str, float]] = {
    # Small sizes (M2 - M5)
    "M2x0.4": {
        "nominal_diameter": 2.0e-3,
        "pitch": 0.4e-3,
        "stress_area": 2.07e-6,
        "minor_diameter": 1.509e-3,
        "pitch_diameter": 1.740e-3,
        "head_diameter": 4.0e-3,
        "head_height": 1.4e-3,
    },
    "M2.5x0.45": {
        "nominal_diameter": 2.5e-3,
        "pitch": 0.45e-3,
        "stress_area": 3.39e-6,
        "minor_diameter": 1.948e-3,
        "pitch_diameter": 2.208e-3,
        "head_diameter": 5.0e-3,
        "head_height": 1.7e-3,
    },
    "M3x0.5": {
        "nominal_diameter": 3.0e-3,
        "pitch": 0.5e-3,
        "stress_area": 5.03e-6,
        "minor_diameter": 2.387e-3,
        "pitch_diameter": 2.675e-3,
        "head_diameter": 5.5e-3,
        "head_height": 2.0e-3,
    },
    "M4x0.7": {
        "nominal_diameter": 4.0e-3,
        "pitch": 0.7e-3,
        "stress_area": 8.78e-6,
        "minor_diameter": 3.141e-3,
        "pitch_diameter": 3.545e-3,
        "head_diameter": 7.0e-3,
        "head_height": 2.8e-3,
    },
    "M5x0.8": {
        "nominal_diameter": 5.0e-3,
        "pitch": 0.8e-3,
        "stress_area": 14.2e-6,
        "minor_diameter": 4.019e-3,
        "pitch_diameter": 4.480e-3,
        "head_diameter": 8.0e-3,
        "head_height": 3.5e-3,
    },
    # Coarse pitch series (M6+)
    "M6x1.0": {
        "nominal_diameter": 6.0e-3,
        "pitch": 1.0e-3,
        "stress_area": 20.1e-6,
        "minor_diameter": 4.773e-3,
        "pitch_diameter": 5.350e-3,
        "head_diameter": 10.0e-3,
        "head_height": 4.0e-3,
    },
    "M8x1.25": {
        "nominal_diameter": 8.0e-3,
        "pitch": 1.25e-3,
        "stress_area": 36.6e-6,
        "minor_diameter": 6.466e-3,
        "pitch_diameter": 7.188e-3,
        "head_diameter": 13.0e-3,
        "head_height": 5.3e-3,
    },
    "M10x1.5": {
        "nominal_diameter": 10.0e-3,
        "pitch": 1.5e-3,
        "stress_area": 58.0e-6,
        "minor_diameter": 8.160e-3,
        "pitch_diameter": 9.026e-3,
        "head_diameter": 16.0e-3,
        "head_height": 6.4e-3,
    },
    "M12x1.75": {
        "nominal_diameter": 12.0e-3,
        "pitch": 1.75e-3,
        "stress_area": 84.3e-6,
        "minor_diameter": 9.853e-3,
        "pitch_diameter": 10.863e-3,
        "head_diameter": 18.0e-3,
        "head_height": 7.5e-3,
    },
    "M14x2.0": {
        "nominal_diameter": 14.0e-3,
        "pitch": 2.0e-3,
        "stress_area": 115.0e-6,
        "minor_diameter": 11.546e-3,
        "pitch_diameter": 12.701e-3,
        "head_diameter": 21.0e-3,
        "head_height": 8.8e-3,
    },
    "M16x2.0": {
        "nominal_diameter": 16.0e-3,
        "pitch": 2.0e-3,
        "stress_area": 157.0e-6,
        "minor_diameter": 13.546e-3,
        "pitch_diameter": 14.701e-3,
        "head_diameter": 24.0e-3,
        "head_height": 10.0e-3,
    },
    "M18x2.5": {
        "nominal_diameter": 18.0e-3,
        "pitch": 2.5e-3,
        "stress_area": 192.0e-6,
        "minor_diameter": 14.933e-3,
        "pitch_diameter": 16.376e-3,
        "head_diameter": 27.0e-3,
        "head_height": 11.5e-3,
    },
    "M20x2.5": {
        "nominal_diameter": 20.0e-3,
        "pitch": 2.5e-3,
        "stress_area": 245.0e-6,
        "minor_diameter": 16.933e-3,
        "pitch_diameter": 18.376e-3,
        "head_diameter": 30.0e-3,
        "head_height": 12.5e-3,
    },
    "M22x2.5": {
        "nominal_diameter": 22.0e-3,
        "pitch": 2.5e-3,
        "stress_area": 303.0e-6,
        "minor_diameter": 18.933e-3,
        "pitch_diameter": 20.376e-3,
        "head_diameter": 34.0e-3,
        "head_height": 14.0e-3,
    },
    "M24x3.0": {
        "nominal_diameter": 24.0e-3,
        "pitch": 3.0e-3,
        "stress_area": 353.0e-6,
        "minor_diameter": 20.319e-3,
        "pitch_diameter": 22.051e-3,
        "head_diameter": 36.0e-3,
        "head_height": 15.0e-3,
    },
    # Fine pitch series
    "M8x1.0": {
        "nominal_diameter": 8.0e-3,
        "pitch": 1.0e-3,
        "stress_area": 39.2e-6,
        "minor_diameter": 6.773e-3,
        "pitch_diameter": 7.350e-3,
        "head_diameter": 13.0e-3,
        "head_height": 5.3e-3,
    },
    "M10x1.25": {
        "nominal_diameter": 10.0e-3,
        "pitch": 1.25e-3,
        "stress_area": 61.2e-6,
        "minor_diameter": 8.466e-3,
        "pitch_diameter": 9.188e-3,
        "head_diameter": 16.0e-3,
        "head_height": 6.4e-3,
    },
    "M10x1.0": {
        "nominal_diameter": 10.0e-3,
        "pitch": 1.0e-3,
        "stress_area": 64.5e-6,
        "minor_diameter": 8.773e-3,
        "pitch_diameter": 9.350e-3,
        "head_diameter": 16.0e-3,
        "head_height": 6.4e-3,
    },
    "M12x1.5": {
        "nominal_diameter": 12.0e-3,
        "pitch": 1.5e-3,
        "stress_area": 88.1e-6,
        "minor_diameter": 10.160e-3,
        "pitch_diameter": 11.026e-3,
        "head_diameter": 18.0e-3,
        "head_height": 7.5e-3,
    },
    "M12x1.25": {
        "nominal_diameter": 12.0e-3,
        "pitch": 1.25e-3,
        "stress_area": 92.1e-6,
        "minor_diameter": 10.466e-3,
        "pitch_diameter": 11.188e-3,
        "head_diameter": 18.0e-3,
        "head_height": 7.5e-3,
    },
    "M16x1.5": {
        "nominal_diameter": 16.0e-3,
        "pitch": 1.5e-3,
        "stress_area": 167.0e-6,
        "minor_diameter": 14.160e-3,
        "pitch_diameter": 15.026e-3,
        "head_diameter": 24.0e-3,
        "head_height": 10.0e-3,
    },
    "M20x1.5": {
        "nominal_diameter": 20.0e-3,
        "pitch": 1.5e-3,
        "stress_area": 272.0e-6,
        "minor_diameter": 18.160e-3,
        "pitch_diameter": 19.026e-3,
        "head_diameter": 30.0e-3,
        "head_height": 12.5e-3,
    },
}

# Unified Thread Standard (UTS) per ASME B1.1
# Imperial thread geometry
UTS_FASTENER_GEOMETRY: Dict[str, Dict[str, float]] = {
    # Small machine screws
    "#2-56 UNC": {
        "nominal_diameter": 2.184e-3,    # 0.086 in
        "pitch": 0.454e-3,               # 1/56 in
        "stress_area": 1.89e-6,          # 0.00293 in^2
        "minor_diameter": 1.628e-3,
        "pitch_diameter": 1.905e-3,
        "head_diameter": 4.37e-3,
        "head_height": 1.52e-3,
    },
    "#4-40 UNC": {
        "nominal_diameter": 2.845e-3,    # 0.112 in
        "pitch": 0.635e-3,               # 1/40 in
        "stress_area": 3.08e-6,          # 0.00477 in^2
        "minor_diameter": 2.070e-3,
        "pitch_diameter": 2.458e-3,
        "head_diameter": 5.56e-3,
        "head_height": 1.91e-3,
    },
    "#6-32 UNC": {
        "nominal_diameter": 3.505e-3,    # 0.138 in
        "pitch": 0.794e-3,               # 1/32 in
        "stress_area": 5.26e-6,          # 0.00816 in^2
        "minor_diameter": 2.642e-3,
        "pitch_diameter": 3.073e-3,
        "head_diameter": 7.14e-3,
        "head_height": 2.31e-3,
    },
    "#8-32 UNC": {
        "nominal_diameter": 4.166e-3,    # 0.164 in
        "pitch": 0.794e-3,
        "stress_area": 8.78e-6,          # 0.0136 in^2
        "minor_diameter": 3.302e-3,
        "pitch_diameter": 3.734e-3,
        "head_diameter": 8.33e-3,
        "head_height": 2.74e-3,
    },
    "#10-24 UNC": {
        "nominal_diameter": 4.826e-3,    # 0.190 in
        "pitch": 1.058e-3,               # 1/24 in
        "stress_area": 10.6e-6,          # 0.0164 in^2
        "minor_diameter": 3.683e-3,
        "pitch_diameter": 4.255e-3,
        "head_diameter": 9.53e-3,
        "head_height": 3.18e-3,
    },
    "#10-32 UNF": {
        "nominal_diameter": 4.826e-3,
        "pitch": 0.794e-3,
        "stress_area": 12.7e-6,          # 0.0196 in^2
        "minor_diameter": 3.962e-3,
        "pitch_diameter": 4.394e-3,
        "head_diameter": 9.53e-3,
        "head_height": 3.18e-3,
    },
    "1/4-20 UNC": {
        "nominal_diameter": 6.35e-3,     # 0.250 in
        "pitch": 1.27e-3,                # 1/20 in
        "stress_area": 20.5e-6,          # 0.0318 in^2
        "minor_diameter": 4.978e-3,
        "pitch_diameter": 5.664e-3,
        "head_diameter": 11.11e-3,
        "head_height": 4.17e-3,
    },
    "1/4-28 UNF": {
        "nominal_diameter": 6.35e-3,
        "pitch": 0.907e-3,               # 1/28 in
        "stress_area": 23.5e-6,          # 0.0364 in^2
        "minor_diameter": 5.334e-3,
        "pitch_diameter": 5.842e-3,
        "head_diameter": 11.11e-3,
        "head_height": 4.17e-3,
    },
    "5/16-18 UNC": {
        "nominal_diameter": 7.938e-3,    # 0.3125 in
        "pitch": 1.411e-3,
        "stress_area": 32.6e-6,          # 0.0505 in^2
        "minor_diameter": 6.401e-3,
        "pitch_diameter": 7.170e-3,
        "head_diameter": 12.7e-3,
        "head_height": 5.21e-3,
    },
    "5/16-24 UNF": {
        "nominal_diameter": 7.938e-3,
        "pitch": 1.058e-3,
        "stress_area": 37.4e-6,          # 0.0580 in^2
        "minor_diameter": 6.794e-3,
        "pitch_diameter": 7.366e-3,
        "head_diameter": 12.7e-3,
        "head_height": 5.21e-3,
    },
    "3/8-16 UNC": {
        "nominal_diameter": 9.525e-3,    # 0.375 in
        "pitch": 1.588e-3,
        "stress_area": 48.4e-6,          # 0.0750 in^2
        "minor_diameter": 7.798e-3,
        "pitch_diameter": 8.661e-3,
        "head_diameter": 14.29e-3,
        "head_height": 6.25e-3,
    },
    "3/8-24 UNF": {
        "nominal_diameter": 9.525e-3,
        "pitch": 1.058e-3,
        "stress_area": 57.9e-6,          # 0.0898 in^2
        "minor_diameter": 8.382e-3,
        "pitch_diameter": 8.953e-3,
        "head_diameter": 14.29e-3,
        "head_height": 6.25e-3,
    },
    "7/16-14 UNC": {
        "nominal_diameter": 11.11e-3,    # 0.4375 in
        "pitch": 1.814e-3,
        "stress_area": 66.5e-6,          # 0.1031 in^2
        "minor_diameter": 9.144e-3,
        "pitch_diameter": 10.13e-3,
        "head_diameter": 17.46e-3,
        "head_height": 7.29e-3,
    },
    "1/2-13 UNC": {
        "nominal_diameter": 12.7e-3,     # 0.500 in
        "pitch": 1.954e-3,
        "stress_area": 84.3e-6,          # 0.1307 in^2
        "minor_diameter": 10.59e-3,
        "pitch_diameter": 11.65e-3,
        "head_diameter": 19.05e-3,
        "head_height": 8.33e-3,
    },
    "1/2-20 UNF": {
        "nominal_diameter": 12.7e-3,
        "pitch": 1.27e-3,
        "stress_area": 101.6e-6,         # 0.1576 in^2
        "minor_diameter": 11.33e-3,
        "pitch_diameter": 12.02e-3,
        "head_diameter": 19.05e-3,
        "head_height": 8.33e-3,
    },
    "9/16-12 UNC": {
        "nominal_diameter": 14.29e-3,    # 0.5625 in
        "pitch": 2.117e-3,
        "stress_area": 106.7e-6,         # 0.1655 in^2
        "minor_diameter": 11.99e-3,
        "pitch_diameter": 13.14e-3,
        "head_diameter": 22.23e-3,
        "head_height": 9.38e-3,
    },
    "5/8-11 UNC": {
        "nominal_diameter": 15.88e-3,    # 0.625 in
        "pitch": 2.309e-3,
        "stress_area": 130.3e-6,         # 0.2020 in^2
        "minor_diameter": 13.39e-3,
        "pitch_diameter": 14.63e-3,
        "head_diameter": 23.81e-3,
        "head_height": 10.42e-3,
    },
    "5/8-18 UNF": {
        "nominal_diameter": 15.88e-3,
        "pitch": 1.411e-3,
        "stress_area": 153.9e-6,         # 0.2386 in^2
        "minor_diameter": 14.34e-3,
        "pitch_diameter": 15.11e-3,
        "head_diameter": 23.81e-3,
        "head_height": 10.42e-3,
    },
    "3/4-10 UNC": {
        "nominal_diameter": 19.05e-3,    # 0.750 in
        "pitch": 2.54e-3,
        "stress_area": 193.5e-6,         # 0.3001 in^2
        "minor_diameter": 16.31e-3,
        "pitch_diameter": 17.68e-3,
        "head_diameter": 28.58e-3,
        "head_height": 12.5e-3,
    },
    "3/4-16 UNF": {
        "nominal_diameter": 19.05e-3,
        "pitch": 1.588e-3,
        "stress_area": 226.5e-6,         # 0.3513 in^2
        "minor_diameter": 17.33e-3,
        "pitch_diameter": 18.19e-3,
        "head_diameter": 28.58e-3,
        "head_height": 12.5e-3,
    },
    "7/8-9 UNC": {
        "nominal_diameter": 22.23e-3,    # 0.875 in
        "pitch": 2.822e-3,
        "stress_area": 265.8e-6,         # 0.4121 in^2
        "minor_diameter": 19.18e-3,
        "pitch_diameter": 20.70e-3,
        "head_diameter": 33.34e-3,
        "head_height": 14.58e-3,
    },
    "1-8 UNC": {
        "nominal_diameter": 25.4e-3,     # 1.000 in
        "pitch": 3.175e-3,
        "stress_area": 348.4e-6,         # 0.5402 in^2
        "minor_diameter": 22.00e-3,
        "pitch_diameter": 23.70e-3,
        "head_diameter": 38.1e-3,
        "head_height": 16.67e-3,
    },
    "1-12 UNF": {
        "nominal_diameter": 25.4e-3,
        "pitch": 2.117e-3,
        "stress_area": 391.0e-6,         # 0.6061 in^2
        "minor_diameter": 23.09e-3,
        "pitch_diameter": 24.25e-3,
        "head_diameter": 38.1e-3,
        "head_height": 16.67e-3,
    },
}


# =============================================================================
# K-FACTOR (NUT FACTOR) DATABASE
# =============================================================================

# K-factor ranges per surface condition
# Reference: Bickford (2007), VDI 2230:2015, Machinery's Handbook
# Format: condition -> (K_min, K_typical, K_max)
K_FACTOR_DATABASE: Dict[str, Tuple[float, float, float]] = {
    "dry_steel": (0.16, 0.20, 0.25),
    "oiled": (0.12, 0.15, 0.18),
    "moly_lube": (0.08, 0.11, 0.14),
    "cadmium_plated": (0.10, 0.13, 0.16),
    "zinc_plated_dry": (0.17, 0.20, 0.23),
    "zinc_plated_oiled": (0.13, 0.16, 0.19),
    "phosphate_oil": (0.11, 0.14, 0.17),
    "ptfe_coated": (0.06, 0.09, 0.12),
    "silver_plated": (0.09, 0.12, 0.15),
    "copper_antiseize": (0.10, 0.13, 0.16),
    "nickel_antiseize": (0.11, 0.14, 0.17),
    "stainless_dry": (0.25, 0.30, 0.35),
    "stainless_lubed": (0.14, 0.17, 0.20),
    "aluminum_dry": (0.20, 0.25, 0.30),
}

# Thread and bearing friction coefficients
# Format: condition -> (mu_thread_min, mu_thread_max, mu_bearing_min, mu_bearing_max)
FRICTION_DATABASE: Dict[str, Tuple[float, float, float, float]] = {
    "dry_steel": (0.12, 0.18, 0.12, 0.18),
    "oiled": (0.08, 0.12, 0.08, 0.12),
    "moly_lube": (0.04, 0.08, 0.04, 0.08),
    "cadmium_plated": (0.06, 0.10, 0.06, 0.10),
    "zinc_plated_dry": (0.12, 0.16, 0.12, 0.16),
    "zinc_plated_oiled": (0.08, 0.12, 0.08, 0.12),
    "phosphate_oil": (0.08, 0.12, 0.08, 0.12),
    "ptfe_coated": (0.03, 0.06, 0.03, 0.06),
    "silver_plated": (0.05, 0.09, 0.05, 0.09),
    "stainless_dry": (0.18, 0.25, 0.18, 0.25),
    "stainless_lubed": (0.10, 0.14, 0.10, 0.14),
}


# =============================================================================
# EMBEDDING LOSS DATABASE (VDI 2230 Table 5)
# =============================================================================

# Embedding per interface in micrometers
# Format: surface_finish -> {grade_class: embedding_um}
EMBEDDING_DATABASE: Dict[str, Dict[str, float]] = {
    "machined_fine": {  # Ra < 1.6 um
        "low_strength": 2.0,   # <= 5.6 or Grade 2
        "medium_strength": 1.5,  # 8.8 or Grade 5
        "high_strength": 1.0,  # >= 10.9 or Grade 8
    },
    "machined": {  # Ra 1.6-6.3 um
        "low_strength": 3.0,
        "medium_strength": 2.5,
        "high_strength": 2.0,
    },
    "as_rolled": {  # Ra 6.3-25 um
        "low_strength": 6.0,
        "medium_strength": 5.0,
        "high_strength": 4.0,
    },
    "as_cast": {  # Ra > 25 um
        "low_strength": 10.0,
        "medium_strength": 8.0,
        "high_strength": 6.5,
    },
}


# =============================================================================
# TIGHTENING METHOD SCATTER FACTORS
# =============================================================================

# Scatter factor alpha_A = Fi_max / Fi_min per VDI 2230
SCATTER_FACTORS: Dict[str, float] = {
    "torque_wrench": 1.6,       # Standard hand torque wrench
    "torque_wrench_precision": 1.4,  # Calibrated click-type
    "angle_control": 1.25,     # Torque + angle method
    "yield_control": 1.1,      # Tighten to yield
    "hydraulic": 1.05,         # Hydraulic tensioner
    "ultrasonic": 1.02,        # Ultrasonic elongation control
}


# =============================================================================
# CALCULATION FUNCTIONS
# =============================================================================

def get_bolt_grade_properties(bolt_grade: str) -> Dict[str, float]:
    """Look up bolt material properties from grade designation."""
    if bolt_grade in ISO_BOLT_GRADES:
        return ISO_BOLT_GRADES[bolt_grade]
    elif bolt_grade in SAE_BOLT_GRADES:
        return SAE_BOLT_GRADES[bolt_grade]
    else:
        raise ValueError(
            f"Unknown bolt grade '{bolt_grade}'. "
            f"Valid ISO grades: {list(ISO_BOLT_GRADES.keys())}. "
            f"Valid SAE grades: {list(SAE_BOLT_GRADES.keys())}."
        )


def get_fastener_geometry(fastener_size: str) -> Dict[str, float]:
    """Look up fastener geometry from thread designation."""
    if fastener_size in ISO_FASTENER_GEOMETRY:
        return ISO_FASTENER_GEOMETRY[fastener_size]
    elif fastener_size in UTS_FASTENER_GEOMETRY:
        return UTS_FASTENER_GEOMETRY[fastener_size]
    else:
        raise ValueError(
            f"Unknown fastener size '{fastener_size}'. "
            f"Valid ISO sizes: {list(ISO_FASTENER_GEOMETRY.keys())}. "
            f"Valid UTS sizes: {list(UTS_FASTENER_GEOMETRY.keys())}."
        )


def get_strength_class(bolt_grade: str) -> str:
    """Classify bolt grade for embedding lookup."""
    if bolt_grade in ["4.6", "5.6", "SAE Grade 2"]:
        return "low_strength"
    elif bolt_grade in ["8.8", "SAE Grade 5", "ASTM A325"]:
        return "medium_strength"
    else:
        return "high_strength"


def calculate_k_factor_claude(
    pitch: float,
    pitch_diameter: float,
    nominal_diameter: float,
    friction_thread: float,
    friction_bearing: float,
    bearing_diameter_mean: float,
    thread_angle_deg: float = 60.0,
) -> float:
    """
    Calculate torque coefficient K from first principles.

    Uses the long-form equation that separates thread helix,
    thread friction, and bearing friction contributions.

    Reference: Shigley's MED 11th ed., Eq. (8-27)
    """
    thread_angle_rad = math.radians(thread_angle_deg / 2.0)  # Half angle
    lead_angle = math.atan(pitch / (math.pi * pitch_diameter))

    # Thread friction component (in pitch diameter)
    k_thread = (pitch / (2.0 * math.pi * pitch_diameter) +
                friction_thread / math.cos(thread_angle_rad))

    # Bearing friction component
    k_bearing = friction_bearing * bearing_diameter_mean / (2.0 * nominal_diameter)

    # Total K-factor
    k_total = (pitch_diameter / nominal_diameter) * k_thread + k_bearing

    return k_total


def calculate_bolt_stiffness_claude(
    stress_area: float,
    nominal_diameter: float,
    minor_diameter: float,
    grip_length: float,
    head_height: float,
    elastic_modulus: float,
    thread_engaged_length: float = None,
) -> float:
    """
    Calculate bolt axial stiffness using VDI 2230 multi-zone approach.

    Divides bolt into zones: head, unthreaded shank, threaded shank,
    and engaged threads, each with different effective areas.

    Reference: VDI 2230:2015, Section 5.1.1
    """
    if grip_length <= 0:
        raise ValueError("grip_length must be positive.")

    # Estimate thread engaged length if not provided (1.5d typical)
    if thread_engaged_length is None:
        thread_engaged_length = 1.5 * nominal_diameter

    # Zone lengths (simplified model)
    # Head zone: contributes 0.4*head_height to flexibility
    # Shank zone: assume half grip is unthreaded
    # Thread zone: remaining grip plus engagement

    # Effective length for head contribution
    l_head = 0.4 * head_height

    # Assume free thread length is about 2 pitches above grip
    l_unthreaded = max(0, grip_length * 0.5)
    l_threaded_free = grip_length - l_unthreaded
    l_engaged = min(thread_engaged_length, 0.5 * grip_length)

    # Areas
    a_shank = math.pi * nominal_diameter**2 / 4.0
    a_thread = stress_area  # Use stress area for threaded portion

    # Flexibility = L / (A * E)
    flex_head = l_head / (a_shank * elastic_modulus)
    flex_shank = l_unthreaded / (a_shank * elastic_modulus)
    flex_thread_free = l_threaded_free / (a_thread * elastic_modulus)
    flex_engaged = (0.5 * l_engaged) / (a_thread * elastic_modulus)  # Half contributes

    total_flexibility = flex_head + flex_shank + flex_thread_free + flex_engaged

    if total_flexibility <= 0:
        raise ValueError("Invalid geometry: total flexibility is non-positive.")

    return 1.0 / total_flexibility


def calculate_joint_stiffness_claude(
    grip_length: float,
    hole_diameter: float,
    head_diameter: float,
    clamped_modulus: float,
    joint_type: str = "through_bolt",
    n_interfaces: int = 1,
) -> float:
    """
    Calculate clamped member stiffness using frustum cone model.

    Models the compression zone as a double frustum (barrel shape)
    with half-apex angle typically 30 degrees.

    Reference: VDI 2230:2015, Section 5.1.2; Shigley's Eq. (8-20)
    """
    if grip_length <= 0:
        raise ValueError("grip_length must be positive.")

    # Frustum half-apex angle (30 deg is standard assumption)
    alpha = math.radians(30)

    # Effective diameter at mid-grip
    d_hole = hole_diameter
    d_head = head_diameter

    # Rotscher's pressure cone formula (VDI 2230)
    # For through-bolt, consider full grip with double frustum
    if joint_type == "through_bolt":
        l_eff = grip_length / 2.0  # Each half contributes
    else:
        l_eff = grip_length  # Tap bolt: single frustum

    # Limiting diameter at mid-height
    d_limit = d_head + 2 * l_eff * math.tan(alpha)

    # Equivalent cylinder diameter (simplified Rotscher)
    d_equiv = 0.5 * (d_head + d_limit)

    # Annular area
    a_joint = math.pi / 4.0 * (d_equiv**2 - d_hole**2)

    if a_joint <= 0:
        # Fallback to simpler calculation if geometry is problematic
        a_joint = math.pi / 4.0 * (d_head**2 - d_hole**2) * 1.5

    # Stiffness = A * E / L
    if joint_type == "through_bolt":
        stiffness = 2.0 * a_joint * clamped_modulus / grip_length
    else:
        stiffness = a_joint * clamped_modulus / grip_length

    return stiffness


def calculate_embedding_loss_claude(
    grip_length: float,
    n_interfaces: int,
    surface_roughness: str,
    bolt_grade: str,
    bolt_stiffness: float,
    joint_stiffness: float,
) -> float:
    """
    Estimate preload loss due to surface embedding per VDI 2230.

    Embedding occurs at each interface under sustained load,
    causing permanent deformation and preload loss.

    Reference: VDI 2230:2015, Section 5.4.2
    """
    # Get embedding value from database
    if surface_roughness not in EMBEDDING_DATABASE:
        surface_roughness = "machined"  # Default

    strength_class = get_strength_class(bolt_grade)
    embedding_um = EMBEDDING_DATABASE[surface_roughness].get(strength_class, 2.5)
    embedding_m = embedding_um * 1e-6

    # Total embedding displacement
    total_embedding = n_interfaces * embedding_m

    # Add thread/head interface embedding (about 1 um per interface)
    total_embedding += 2 * 1.0e-6

    # Preload loss = embedding * combined stiffness
    # Combined stiffness for preload loss
    combined_stiffness = (bolt_stiffness * joint_stiffness) / (bolt_stiffness + joint_stiffness)
    preload_loss = total_embedding * combined_stiffness

    return preload_loss


def generate_joint_diagram_data_claude(
    preload: float,
    bolt_stiffness: float,
    joint_stiffness: float,
    external_load: float,
    n_points: int = 50,
) -> Dict[str, List[float]]:
    """
    Generate data for classic triangular bolt/joint force-extension diagram.

    The classic joint diagram (per VDI 2230 and Bickford) shows:
    - Bolt stiffness line from origin through preload point (slope = Kb)
    - Joint stiffness line from preload point back toward baseline (slope = -Kj)
    - The triangular region bounded by these lines and the x-axis
    - Working load shifts showing delta_Fb and delta_Fj under external load

    Returns arrays for plotting the classic triangular diagram with
    bolt line, joint line, working triangle, and key annotation points.
    """
    # Preload creates initial deformations
    delta_b_preload = preload / bolt_stiffness  # Bolt stretch at preload
    delta_j_preload = preload / joint_stiffness  # Joint compression at preload

    # Load factor (portion of external load carried by bolt)
    phi = bolt_stiffness / (bolt_stiffness + joint_stiffness)

    # Working state under external axial load
    work_bolt_force = preload + phi * external_load
    work_joint_force = max(0, preload - (1 - phi) * external_load)
    work_bolt_extension = work_bolt_force / bolt_stiffness
    work_joint_compression = work_joint_force / joint_stiffness

    # Separation load (external load at which joint separates)
    separation_load = preload / (1 - phi) if phi < 1 else float('inf')

    # ===== BOLT LINE (from origin through preload, extended to max working) =====
    # Extends from (0,0) through preload point and beyond to show working range
    max_bolt_ext = max(delta_b_preload * 1.3, work_bolt_extension * 1.1)
    bolt_extension = [i * max_bolt_ext / (n_points - 1) for i in range(n_points)]
    bolt_force = [ext * bolt_stiffness for ext in bolt_extension]

    # ===== JOINT LINE (from preload point back to x-axis) =====
    # This creates the classic triangular shape
    # Joint line has slope Kj but plotted from preload point toward origin
    # X positions from preload extension back to where joint force = 0
    # At preload: x = delta_b_preload, F = preload
    # At zero force: x = delta_b_preload + delta_j_preload (joint fully released)
    joint_start_x = delta_b_preload  # Preload point
    joint_end_x = delta_b_preload + delta_j_preload  # Full decompression point

    joint_x = [joint_start_x + i * (joint_end_x - joint_start_x) / (n_points - 1)
               for i in range(n_points)]
    # Force decreases from preload to zero as we move right (joint decompresses)
    joint_force_line = [preload - (x - delta_b_preload) * joint_stiffness
                        for x in joint_x]

    # ===== WORKING TRIANGLE VERTICES =====
    # Under external load, operating point moves from preload along both stiffness lines
    # Bolt force increases (moves up bolt line)
    # Joint force decreases (moves along joint line toward separation)

    # Calculate working point on joint line
    work_x = delta_b_preload + (preload - work_joint_force) / joint_stiffness

    # Triangle showing load distribution
    triangle_x = [delta_b_preload, work_bolt_extension, work_x, delta_b_preload]
    triangle_f = [preload, work_bolt_force, work_joint_force, preload]

    # ===== DELTA LINES (showing load pickup) =====
    # Vertical delta Fb (additional bolt force)
    delta_fb_x = [work_bolt_extension, work_bolt_extension]
    delta_fb_y = [preload, work_bolt_force]

    # Horizontal working line at external load application
    working_line_x = [work_bolt_extension, work_x]
    working_line_y = [work_bolt_force, work_joint_force]

    return {
        # Main stiffness lines
        "bolt_extension": bolt_extension,
        "bolt_force": bolt_force,
        "joint_x": joint_x,
        "joint_force": joint_force_line,

        # Key points
        "preload_extension": delta_b_preload,
        "preload_force": preload,
        "work_bolt_extension": work_bolt_extension,
        "work_bolt_force": work_bolt_force,
        "work_x": work_x,
        "work_joint_force": work_joint_force,

        # Working triangle
        "triangle_x": triangle_x,
        "triangle_f": triangle_f,

        # Delta lines for annotation
        "delta_fb_x": delta_fb_x,
        "delta_fb_y": delta_fb_y,
        "working_line_x": working_line_x,
        "working_line_y": working_line_y,

        # Reference values
        "separation_extension": joint_end_x,
        "separation_load": separation_load,
        "phi": phi,
        "delta_b_preload": delta_b_preload,
        "delta_j_preload": delta_j_preload,
    }


def generate_torque_tension_curve_claude(
    fastener_size: str,
    bolt_grade: str,
    surface_condition: str,
    n_points: int = 25,
) -> Dict[str, List[float]]:
    """
    Generate torque vs. preload relationship with K-factor uncertainty band.
    """
    geometry = get_fastener_geometry(fastener_size)
    grade = get_bolt_grade_properties(bolt_grade)
    k_min, k_typ, k_max = K_FACTOR_DATABASE.get(surface_condition, (0.15, 0.18, 0.22))

    nominal_d = geometry["nominal_diameter"]
    stress_area = geometry["stress_area"]
    proof_strength = grade["proof_strength"]

    # Maximum preload at proof load
    max_preload = proof_strength * stress_area

    # Generate preload range
    preloads = [i * max_preload / (n_points - 1) for i in range(n_points)]

    # Torque at each K value: T = K * d * F
    torque_min_k = [k_min * nominal_d * f for f in preloads]  # Min K = max preload
    torque_typ = [k_typ * nominal_d * f for f in preloads]
    torque_max_k = [k_max * nominal_d * f for f in preloads]  # Max K = min preload

    return {
        "preload": preloads,
        "torque_at_k_min": torque_min_k,
        "torque_at_k_typ": torque_typ,
        "torque_at_k_max": torque_max_k,
        "k_min": k_min,
        "k_typ": k_typ,
        "k_max": k_max,
    }


def generate_k_factor_sensitivity_claude(
    nominal_diameter: float,
    target_torque: float,
    k_range: Tuple[float, float],
    n_points: int = 30,
) -> Dict[str, List[float]]:
    """
    Generate data showing preload sensitivity to K-factor variation.
    """
    k_min, k_max = k_range
    k_span = k_max - k_min
    k_values = [k_min + i * k_span / (n_points - 1) for i in range(n_points)]

    # Preload = T / (K * d)
    preloads = [target_torque / (k * nominal_diameter) for k in k_values]

    return {
        "k_values": k_values,
        "preload_achieved": preloads,
    }


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_bolted_joint_claude(
    fastener_size: str,
    bolt_grade: str,
    grip_length: float,
    clamped_material_modulus: float,
    external_axial_load: float,
    external_shear_load: float,
    tightening_method: str,
    surface_condition: str,
    temperature: float,
    n_bolts: int,
    joint_type: str,
    embedding_surface_roughness: str,
) -> Dict[str, Any]:
    """
    Perform VDI 2230-style bolted joint analysis for a preloaded connection.

    This function implements the systematic approach outlined in VDI 2230:2015
    for calculating bolt torque, preload, joint stiffness, working loads,
    embedding losses, and safety factors.

    ---Parameters---
    fastener_size : str
        Thread designation (e.g., "M10x1.5" for ISO or "1/2-13 UNC" for UTS).
        Must match entries in the fastener geometry database.
    bolt_grade : str
        Material grade identifier (e.g., "8.8", "10.9", "SAE Grade 5").
        Determines proof strength and material properties per ISO 898-1 or SAE J429.
    grip_length : float
        Total clamped length from bolt head to nut bearing surface (m).
        Affects joint and bolt stiffness calculations per VDI 2230.
    clamped_material_modulus : float
        Elastic modulus of clamped members (Pa). Use equivalent modulus for
        multi-material joints. Steel ~210 GPa, Aluminum ~70 GPa.
    external_axial_load : float
        Maximum axial working load per bolt in tension (N).
        Used for load factor and safety calculations.
    external_shear_load : float
        Maximum shear load per bolt perpendicular to bolt axis (N).
        Evaluated against friction grip capacity.
    tightening_method : str
        Assembly method affecting preload scatter. Options: "torque_wrench",
        "angle_control", "yield_control", "hydraulic".
    surface_condition : str
        Thread/bearing lubrication state. Options: "dry_steel", "oiled",
        "moly_lube", "zinc_plated_dry", etc. Affects K-factor per Bickford.
    temperature : float
        Operating temperature in degrees Celsius. Used for thermal
        differential assessment in dissimilar material joints.
    n_bolts : int
        Number of bolts in the joint pattern. Used for load distribution.
    joint_type : str
        Joint configuration. Options: "through_bolt" (nut on back),
        "tap_bolt" (threaded into component).
    embedding_surface_roughness : str
        Surface finish class per VDI 2230 Table 5. Options: "machined_fine",
        "machined", "as_rolled", "as_cast".

    ---Returns---
    assembly_torque : float
        Target tightening torque (N-m) for specified conditions.
    torque_range_low : float
        Lower bound torque accounting for K-factor uncertainty (N-m).
    torque_range_high : float
        Upper bound torque accounting for K-factor uncertainty (N-m).
    target_preload : float
        Assembly preload target Fi (N) at 90% of proof load.
    minimum_preload : float
        Minimum residual preload after embedding and scatter (N).
    k_factor : float
        Nut factor K (dimensionless) for specified surface condition.
    k_factor_min : float
        Lower bound K-factor for sensitivity analysis.
    k_factor_max : float
        Upper bound K-factor for sensitivity analysis.
    bolt_stiffness : float
        Axial stiffness of the bolt Kb (N/m).
    joint_stiffness : float
        Axial stiffness of clamped members Kj (N/m).
    load_factor : float
        Proportion of external load carried by bolt phi_n (dimensionless).
    bolt_load_max : float
        Maximum bolt force under working load Fb_max (N).
    clamp_load_min : float
        Minimum clamping force under working load Fj_min (N).
    embedding_loss : float
        Preload reduction due to surface settling (N).
    mean_stress : float
        Mean stress in bolt at working condition sigma_m (Pa).
    alternating_stress : float
        Stress amplitude for fatigue assessment sigma_a (Pa).
    safety_factor_yield : float
        Safety margin against bolt yield SF_y (dimensionless).
    safety_factor_clamp : float
        Safety margin for minimum clamping SF_k (dimensionless).
    safety_factor_fatigue : float
        Safety margin against fatigue SF_D (dimensionless). Approximate.
    safety_factor_shear : float
        Safety margin for friction grip shear resistance SF_G (dimensionless).
    utilization_yield : float
        Percentage of yield capacity used (%).
    utilization_clamp : float
        Percentage of clamping capacity used (%).
    status : str
        Overall assessment: "acceptable", "marginal", or "unacceptable".
    recommendations : list
        Design improvement suggestions based on analysis.
    joint_diagram_data : dict
        Data arrays for plotting force-extension diagram.
    torque_tension_data : dict
        Data arrays for plotting torque-tension curve.
    k_sensitivity_data : dict
        Data arrays for K-factor sensitivity chart.

    ---LaTeX---
    T = K \\cdot d \\cdot F_i
    K = \\frac{P}{2\\pi d_2} + \\frac{\\mu_t}{\\cos\\alpha} + \\frac{\\mu_b \\cdot D_m}{2 d}
    K_b = \\frac{A_s \\cdot E_b}{l_{eff}}
    K_j = \\frac{\\pi \\cdot E_j \\cdot d_w^2}{4 \\cdot l_{grip}} \\cdot C_{frustum}
    \\phi_n = \\frac{K_b}{K_b + K_j}
    F_{b,max} = F_i + \\phi_n \\cdot F_a
    F_{j,min} = F_i - (1 - \\phi_n) \\cdot F_a
    SF_y = \\frac{R_{p0.2} \\cdot A_s}{F_{b,max}}
    \\sigma_a = \\frac{\\phi_n \\cdot F_a}{2 \\cdot A_s}
    """
    # === INPUT VALIDATION ===
    if grip_length <= 0:
        raise ValueError("grip_length must be positive.")
    if clamped_material_modulus <= 0:
        raise ValueError("clamped_material_modulus must be positive.")
    if n_bolts <= 0:
        raise ValueError("n_bolts must be positive.")
    if external_axial_load < 0:
        raise ValueError("external_axial_load cannot be negative.")
    if external_shear_load < 0:
        raise ValueError("external_shear_load cannot be negative.")

    # === LOOKUP PROPERTIES ===
    geometry = get_fastener_geometry(fastener_size)
    grade = get_bolt_grade_properties(bolt_grade)

    nominal_d = geometry["nominal_diameter"]
    pitch = geometry["pitch"]
    pitch_d = geometry["pitch_diameter"]
    stress_area = geometry["stress_area"]
    head_d = geometry["head_diameter"]
    head_h = geometry["head_height"]
    hole_d = nominal_d * 1.1  # Assume 10% clearance hole

    proof_strength = grade["proof_strength"]
    yield_strength = grade["yield_strength"]
    tensile_strength = grade["tensile_strength"]
    bolt_modulus = grade["elastic_modulus"]

    # === K-FACTOR ===
    if surface_condition not in K_FACTOR_DATABASE:
        surface_condition = "oiled"  # Default

    k_min, k_typ, k_max = K_FACTOR_DATABASE[surface_condition]
    k_factor = k_typ

    # === BOLT STIFFNESS ===
    bolt_stiffness = calculate_bolt_stiffness_claude(
        stress_area=stress_area,
        nominal_diameter=nominal_d,
        minor_diameter=geometry["minor_diameter"],
        grip_length=grip_length,
        head_height=head_h,
        elastic_modulus=bolt_modulus,
    )

    # === JOINT STIFFNESS ===
    joint_stiffness = calculate_joint_stiffness_claude(
        grip_length=grip_length,
        hole_diameter=hole_d,
        head_diameter=head_d,
        clamped_modulus=clamped_material_modulus,
        joint_type=joint_type,
    )

    # === LOAD FACTOR (phi) ===
    load_factor = bolt_stiffness / (bolt_stiffness + joint_stiffness)

    # === PRELOAD DETERMINATION ===
    # Target: 90% of proof load (typical for static joints)
    target_preload = 0.90 * proof_strength * stress_area

    # Scatter factor from tightening method
    if tightening_method not in SCATTER_FACTORS:
        tightening_method = "torque_wrench"
    alpha_a = SCATTER_FACTORS[tightening_method]

    # Minimum assembly preload accounting for scatter
    min_assembly_preload = target_preload / alpha_a

    # === EMBEDDING LOSS ===
    n_interfaces = 2 if joint_type == "through_bolt" else 1
    embedding_loss = calculate_embedding_loss_claude(
        grip_length=grip_length,
        n_interfaces=n_interfaces,
        surface_roughness=embedding_surface_roughness,
        bolt_grade=bolt_grade,
        bolt_stiffness=bolt_stiffness,
        joint_stiffness=joint_stiffness,
    )

    # Minimum residual preload after embedding
    minimum_preload = min_assembly_preload - embedding_loss

    # === ASSEMBLY TORQUE ===
    assembly_torque = k_factor * nominal_d * target_preload
    torque_range_low = k_min * nominal_d * target_preload
    torque_range_high = k_max * nominal_d * target_preload

    # === WORKING LOADS ===
    # Maximum bolt force under external load
    bolt_load_max = target_preload + load_factor * external_axial_load

    # Minimum clamp force
    clamp_load_min = minimum_preload - (1 - load_factor) * external_axial_load

    # === STRESSES ===
    # Mean stress
    mean_stress = (target_preload + bolt_load_max) / (2 * stress_area)

    # Alternating stress (fatigue)
    alternating_stress = (load_factor * external_axial_load) / (2 * stress_area)

    # Maximum stress
    max_stress = bolt_load_max / stress_area

    # === SAFETY FACTORS ===
    # Yield safety factor
    if bolt_load_max > 0:
        safety_factor_yield = (yield_strength * stress_area) / bolt_load_max
    else:
        safety_factor_yield = float('inf')

    # Clamping safety factor
    required_clamp = 0.1 * target_preload  # Minimum 10% residual clamp
    if clamp_load_min > 0:
        safety_factor_clamp = clamp_load_min / required_clamp
    else:
        safety_factor_clamp = 0.0

    # Fatigue safety factor (simplified - assumes endurance limit ~ 0.45 * Su for rolled threads)
    # Reference: Shigley's for rolled threads with Kf ~ 2.2
    fatigue_limit = 0.45 * tensile_strength / 2.2  # Approximate Se' / Kf
    if alternating_stress > 0:
        safety_factor_fatigue = fatigue_limit / alternating_stress
    else:
        safety_factor_fatigue = float('inf')

    # Shear slip safety factor (friction grip)
    friction_coeff = 0.15  # Conservative slip coefficient
    friction_capacity = friction_coeff * minimum_preload
    if external_shear_load > 0:
        safety_factor_shear = friction_capacity / external_shear_load
    else:
        safety_factor_shear = float('inf')

    # === UTILIZATION ===
    utilization_yield = 100.0 * max_stress / yield_strength
    utilization_clamp = 100.0 * (1.0 - clamp_load_min / target_preload) if target_preload > 0 else 100.0
    utilization_fatigue = 100.0 * alternating_stress / fatigue_limit if fatigue_limit > 0 else 100.0

    # === STATUS DETERMINATION ===
    min_sf = min(safety_factor_yield, safety_factor_clamp, safety_factor_fatigue, safety_factor_shear)
    if min_sf >= 1.5:
        status = "acceptable"
    elif min_sf >= 1.0:
        status = "marginal"
    else:
        status = "unacceptable"

    # === RECOMMENDATIONS ===
    recommendations = []
    if safety_factor_yield < 1.5:
        recommendations.append("Consider higher strength bolt grade or larger size.")
    if safety_factor_clamp < 1.5:
        recommendations.append("Increase preload or reduce external load.")
    if safety_factor_fatigue < 2.0:
        recommendations.append("Consider fatigue-rated bolt or reduce load cycling.")
    if safety_factor_shear < 1.5 and external_shear_load > 0:
        recommendations.append("Add dowel pins or increase bolt count for shear load.")
    if k_max / k_min > 1.5:
        recommendations.append("Use controlled lubrication to reduce K-factor scatter.")

    # === GRAPH DATA ===
    joint_diagram_data = generate_joint_diagram_data_claude(
        preload=target_preload,
        bolt_stiffness=bolt_stiffness,
        joint_stiffness=joint_stiffness,
        external_load=external_axial_load,
    )

    torque_tension_data = generate_torque_tension_curve_claude(
        fastener_size=fastener_size,
        bolt_grade=bolt_grade,
        surface_condition=surface_condition,
    )

    k_sensitivity_data = generate_k_factor_sensitivity_claude(
        nominal_diameter=nominal_d,
        target_torque=assembly_torque,
        k_range=(k_min, k_max),
    )

    # === RETURN RESULTS ===
    return {
        # Primary outputs
        "assembly_torque": assembly_torque,
        "torque_range_low": torque_range_low,
        "torque_range_high": torque_range_high,
        "target_preload": target_preload,
        "minimum_preload": minimum_preload,
        "k_factor": k_factor,
        "k_factor_min": k_min,
        "k_factor_max": k_max,

        # Geometry and material properties (for progressive disclosure)
        "nominal_diameter": nominal_d,
        "stress_area": stress_area,
        "proof_strength": proof_strength,
        "yield_strength": yield_strength,
        "tensile_strength": tensile_strength,
        "external_axial_load": external_axial_load,
        "external_shear_load": external_shear_load,

        # Stiffness
        "bolt_stiffness": bolt_stiffness,
        "joint_stiffness": joint_stiffness,
        "load_factor": load_factor,

        # Working loads
        "bolt_load_max": bolt_load_max,
        "clamp_load_min": clamp_load_min,
        "embedding_loss": embedding_loss,

        # Stresses
        "mean_stress": mean_stress,
        "alternating_stress": alternating_stress,
        "max_stress": max_stress,

        # Safety factors
        "safety_factor_yield": safety_factor_yield,
        "safety_factor_clamp": safety_factor_clamp,
        "safety_factor_fatigue": safety_factor_fatigue,
        "safety_factor_shear": safety_factor_shear,

        # Utilization
        "utilization_yield": utilization_yield,
        "utilization_clamp": utilization_clamp,
        "utilization_fatigue": utilization_fatigue,

        # Status
        "status": status,
        "recommendations": recommendations,

        # Graph data
        "joint_diagram_data": joint_diagram_data,
        "torque_tension_data": torque_tension_data,
        "k_sensitivity_data": k_sensitivity_data,

        # Substituted equations for display
        "subst_assembly_torque": f"T = {k_factor:.3f} \\times {nominal_d*1000:.1f}\\text{{mm}} \\times {target_preload/1000:.1f}\\text{{kN}} = {assembly_torque:.1f}\\text{{N-m}}",
        "subst_load_factor": f"\\phi = \\frac{{{bolt_stiffness/1e6:.1f}}}{{{bolt_stiffness/1e6:.1f} + {joint_stiffness/1e6:.1f}}} = {load_factor:.3f}",
        "subst_bolt_load_max": f"F_{{b,max}} = {target_preload/1000:.1f} + {load_factor:.3f} \\times {external_axial_load/1000:.1f} = {bolt_load_max/1000:.1f}\\text{{kN}}",
        "subst_safety_yield": f"SF_y = \\frac{{{yield_strength/1e6:.0f} \\times {stress_area*1e6:.1f}}}{{{bolt_load_max/1000:.1f}}} = {safety_factor_yield:.2f}",
    }
