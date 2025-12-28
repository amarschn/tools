"""
Comprehensive beam bending analysis module.

This module provides structural analysis for common beam configurations,
supporting multiple load cases, cross-sections, and materials with
full equation transparency and safety checking.

References:
    - Roark's Formulas for Stress and Strain, 8th Edition
    - AISC Steel Construction Manual, 15th Edition
    - Gere & Timoshenko, Mechanics of Materials, 4th Edition
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# MATERIAL DATABASE
# =============================================================================

MATERIALS: Dict[str, Dict[str, float]] = {
    "steel_structural": {
        "name": "Structural Steel (A36)",
        "E": 200e9,  # Pa
        "yield_strength": 250e6,  # Pa
        "density": 7850,  # kg/m³
        "poisson": 0.3,
    },
    "steel_stainless_304": {
        "name": "Stainless Steel 304",
        "E": 193e9,
        "yield_strength": 215e6,
        "density": 8000,
        "poisson": 0.29,
    },
    "aluminum_6061_t6": {
        "name": "Aluminum 6061-T6",
        "E": 68.9e9,
        "yield_strength": 276e6,
        "density": 2700,
        "poisson": 0.33,
    },
    "aluminum_7075_t6": {
        "name": "Aluminum 7075-T6",
        "E": 71.7e9,
        "yield_strength": 503e6,
        "density": 2810,
        "poisson": 0.33,
    },
    "wood_douglas_fir": {
        "name": "Douglas Fir (structural)",
        "E": 12.4e9,
        "yield_strength": 7.6e6,  # Bending allowable
        "density": 530,
        "poisson": 0.29,
    },
    "wood_oak": {
        "name": "Red Oak",
        "E": 12.5e9,
        "yield_strength": 10.3e6,
        "density": 660,
        "poisson": 0.35,
    },
    "titanium_6al4v": {
        "name": "Titanium 6Al-4V",
        "E": 113.8e9,
        "yield_strength": 880e6,
        "density": 4430,
        "poisson": 0.34,
    },
    "concrete_normal": {
        "name": "Concrete (Normal Weight)",
        "E": 25e9,
        "yield_strength": 3.5e6,  # Compressive
        "density": 2400,
        "poisson": 0.2,
    },
    "custom": {
        "name": "Custom Material",
        "E": 200e9,
        "yield_strength": 250e6,
        "density": 7850,
        "poisson": 0.3,
    },
}

# Common deflection limits per building codes
DEFLECTION_LIMITS: Dict[str, Dict[str, Any]] = {
    "L/180": {"ratio": 180, "application": "Roofs not supporting ceiling"},
    "L/240": {"ratio": 240, "application": "Floors, general"},
    "L/360": {"ratio": 360, "application": "Floors supporting brittle finishes"},
    "L/480": {"ratio": 480, "application": "Precision equipment support"},
    "L/600": {"ratio": 600, "application": "High-precision applications"},
    "custom": {"ratio": 360, "application": "User-defined"},
}


# =============================================================================
# STANDARD STEEL SECTIONS (Selected AISC W-shapes)
# =============================================================================

STEEL_SECTIONS: Dict[str, Dict[str, float]] = {
    # Format: "designation": {d, bf, tf, tw, Ix, Sx, A} in SI (m, m², m³, m⁴)
    "W8x31": {
        "name": "W8x31",
        "d": 0.2032,
        "bf": 0.2032,
        "tf": 0.01106,
        "tw": 0.00762,
        "Ix": 4.57e-5,
        "Sx": 4.49e-4,
        "A": 5.90e-3,
    },
    "W10x49": {
        "name": "W10x49",
        "d": 0.2540,
        "bf": 0.2540,
        "tf": 0.01422,
        "tw": 0.00864,
        "Ix": 1.13e-4,
        "Sx": 8.85e-4,
        "A": 9.29e-3,
    },
    "W12x26": {
        "name": "W12x26",
        "d": 0.3099,
        "bf": 0.1651,
        "tf": 0.00965,
        "tw": 0.00584,
        "Ix": 8.49e-5,
        "Sx": 5.49e-4,
        "A": 4.94e-3,
    },
    "W14x30": {
        "name": "W14x30",
        "d": 0.3517,
        "bf": 0.1715,
        "tf": 0.00991,
        "tw": 0.00686,
        "Ix": 1.21e-4,
        "Sx": 6.89e-4,
        "A": 5.68e-3,
    },
    "W16x40": {
        "name": "W16x40",
        "d": 0.4064,
        "bf": 0.1778,
        "tf": 0.01270,
        "tw": 0.00762,
        "Ix": 2.16e-4,
        "Sx": 1.06e-3,
        "A": 7.61e-3,
    },
    "W18x50": {
        "name": "W18x50",
        "d": 0.4572,
        "bf": 0.1905,
        "tf": 0.01422,
        "tw": 0.00889,
        "Ix": 3.45e-4,
        "Sx": 1.51e-3,
        "A": 9.48e-3,
    },
    "W21x62": {
        "name": "W21x62",
        "d": 0.5334,
        "bf": 0.2096,
        "tf": 0.01524,
        "tw": 0.01016,
        "Ix": 5.54e-4,
        "Sx": 2.08e-3,
        "A": 1.18e-2,
    },
    "W24x76": {
        "name": "W24x76",
        "d": 0.6096,
        "bf": 0.2286,
        "tf": 0.01778,
        "tw": 0.01143,
        "Ix": 8.70e-4,
        "Sx": 2.85e-3,
        "A": 1.44e-2,
    },
}


# =============================================================================
# LOAD CASE DEFINITIONS
# =============================================================================

@dataclass
class LoadCaseInfo:
    """Metadata for a beam loading configuration."""
    name: str
    description: str
    support_type: str  # "simply_supported", "cantilever", "fixed_fixed", "propped"
    load_type: str  # "point", "distributed", "moment", "triangular"
    max_moment_formula: str
    max_deflection_formula: str
    max_shear_formula: str


LOAD_CASES: Dict[str, LoadCaseInfo] = {
    "simply_supported_point_center": LoadCaseInfo(
        name="Simply Supported - Point Load at Center",
        description="Beam supported at both ends with concentrated load at midspan",
        support_type="simply_supported",
        load_type="point",
        max_moment_formula=r"M_{max} = \frac{PL}{4}",
        max_deflection_formula=r"\delta_{max} = \frac{PL^3}{48EI}",
        max_shear_formula=r"V_{max} = \frac{P}{2}",
    ),
    "simply_supported_point_any": LoadCaseInfo(
        name="Simply Supported - Point Load at Any Position",
        description="Beam supported at both ends with concentrated load at distance 'a' from left",
        support_type="simply_supported",
        load_type="point",
        max_moment_formula=r"M_{max} = \frac{Pab}{L}",
        max_deflection_formula=r"\delta_{max} = \frac{Pab(L^2-a^2-b^2)}{6EIL} \cdot \sqrt{\frac{L^2-a^2-b^2}{3}}",
        max_shear_formula=r"V_{max} = \frac{Pb}{L} \text{ or } \frac{Pa}{L}",
    ),
    "simply_supported_udl": LoadCaseInfo(
        name="Simply Supported - Uniform Distributed Load",
        description="Beam supported at both ends with uniformly distributed load over entire span",
        support_type="simply_supported",
        load_type="distributed",
        max_moment_formula=r"M_{max} = \frac{wL^2}{8}",
        max_deflection_formula=r"\delta_{max} = \frac{5wL^4}{384EI}",
        max_shear_formula=r"V_{max} = \frac{wL}{2}",
    ),
    "simply_supported_triangular": LoadCaseInfo(
        name="Simply Supported - Triangular Load",
        description="Beam with linearly varying load from zero at left to maximum at right",
        support_type="simply_supported",
        load_type="triangular",
        max_moment_formula=r"M_{max} = \frac{wL^2}{9\sqrt{3}} \approx 0.0642wL^2",
        max_deflection_formula=r"\delta_{max} = \frac{0.01304wL^4}{EI}",
        max_shear_formula=r"V_{max} = \frac{2wL}{3}",
    ),
    "cantilever_point_end": LoadCaseInfo(
        name="Cantilever - Point Load at Free End",
        description="Fixed at one end, point load at free end",
        support_type="cantilever",
        load_type="point",
        max_moment_formula=r"M_{max} = PL",
        max_deflection_formula=r"\delta_{max} = \frac{PL^3}{3EI}",
        max_shear_formula=r"V_{max} = P",
    ),
    "cantilever_point_any": LoadCaseInfo(
        name="Cantilever - Point Load at Any Position",
        description="Fixed at one end, point load at distance 'a' from fixed end",
        support_type="cantilever",
        load_type="point",
        max_moment_formula=r"M_{max} = Pa",
        max_deflection_formula=r"\delta_{max} = \frac{Pa^2(3L-a)}{6EI}",
        max_shear_formula=r"V_{max} = P",
    ),
    "cantilever_udl": LoadCaseInfo(
        name="Cantilever - Uniform Distributed Load",
        description="Fixed at one end, uniformly distributed load over entire length",
        support_type="cantilever",
        load_type="distributed",
        max_moment_formula=r"M_{max} = \frac{wL^2}{2}",
        max_deflection_formula=r"\delta_{max} = \frac{wL^4}{8EI}",
        max_shear_formula=r"V_{max} = wL",
    ),
    "fixed_fixed_point_center": LoadCaseInfo(
        name="Fixed-Fixed - Point Load at Center",
        description="Both ends fixed, point load at center",
        support_type="fixed_fixed",
        load_type="point",
        max_moment_formula=r"M_{max} = \frac{PL}{8}",
        max_deflection_formula=r"\delta_{max} = \frac{PL^3}{192EI}",
        max_shear_formula=r"V_{max} = \frac{P}{2}",
    ),
    "fixed_fixed_udl": LoadCaseInfo(
        name="Fixed-Fixed - Uniform Distributed Load",
        description="Both ends fixed, uniformly distributed load",
        support_type="fixed_fixed",
        load_type="distributed",
        max_moment_formula=r"M_{max} = \frac{wL^2}{12}",
        max_deflection_formula=r"\delta_{max} = \frac{wL^4}{384EI}",
        max_shear_formula=r"V_{max} = \frac{wL}{2}",
    ),
    "propped_cantilever_udl": LoadCaseInfo(
        name="Propped Cantilever - Uniform Distributed Load",
        description="Fixed at one end, simply supported at the other, with UDL",
        support_type="propped",
        load_type="distributed",
        max_moment_formula=r"M_{max} = \frac{wL^2}{8} \text{ (at fixed end)}",
        max_deflection_formula=r"\delta_{max} = \frac{wL^4}{185EI}",
        max_shear_formula=r"V_{max} = \frac{5wL}{8}",
    ),
}


# =============================================================================
# SECTION PROPERTY CALCULATIONS
# =============================================================================

def _require_positive(value: float, name: str) -> float:
    """Validate that a value is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero (got {value})")
    return float(value)


def compute_section_properties(
    section_type: str,
    dimensions: Dict[str, Any],
) -> Dict[str, float]:
    """
    Compute geometric properties for beam cross-sections.

    ---Parameters---
    section_type : str
        Section identifier. Supported types:
        - ``"rectangular"`` - Solid rectangle (width, depth)
        - ``"circular_solid"`` - Solid circle (diameter)
        - ``"circular_hollow"`` - Hollow tube (outer_diameter, inner_diameter)
        - ``"i_beam"`` - Symmetric I-section (overall_depth, flange_width, flange_thickness, web_thickness)
        - ``"box"`` - Rectangular hollow section (width, depth, wall_thickness)
        - ``"c_channel"`` - C-channel (depth, flange_width, flange_thickness, web_thickness)
        - ``"t_section"`` - T-beam (flange_width, flange_thickness, stem_depth, stem_thickness)
        - ``"standard_steel"`` - AISC W-shape (designation)
        - ``"custom"`` - User-provided (moment_of_inertia, c_top, c_bottom, area)

    dimensions : dict
        Required dimensions for the selected section type (all lengths in metres).

    ---Returns---
    area : float
        Cross-sectional area (m²)
    Ix : float
        Second moment of area about strong axis (m⁴)
    Sx_top : float
        Section modulus to top fibre (m³)
    Sx_bottom : float
        Section modulus to bottom fibre (m³)
    c_top : float
        Distance from centroid to top fibre (m)
    c_bottom : float
        Distance from centroid to bottom fibre (m)
    rx : float
        Radius of gyration (m)
    """
    section_key = section_type.lower().strip()

    if section_key == "rectangular":
        b = _require_positive(dimensions.get("width", 0), "width")
        h = _require_positive(dimensions.get("depth", 0), "depth")
        area = b * h
        Ix = b * h**3 / 12
        c_top = c_bottom = h / 2

    elif section_key == "circular_solid":
        d = _require_positive(dimensions.get("diameter", 0), "diameter")
        area = pi * d**2 / 4
        Ix = pi * d**4 / 64
        c_top = c_bottom = d / 2

    elif section_key == "circular_hollow":
        do = _require_positive(dimensions.get("outer_diameter", 0), "outer_diameter")
        di = _require_positive(dimensions.get("inner_diameter", 0), "inner_diameter")
        if di >= do:
            raise ValueError("Inner diameter must be less than outer diameter")
        area = pi * (do**2 - di**2) / 4
        Ix = pi * (do**4 - di**4) / 64
        c_top = c_bottom = do / 2

    elif section_key == "i_beam":
        d = _require_positive(dimensions.get("overall_depth", 0), "overall_depth")
        bf = _require_positive(dimensions.get("flange_width", 0), "flange_width")
        tf = _require_positive(dimensions.get("flange_thickness", 0), "flange_thickness")
        tw = _require_positive(dimensions.get("web_thickness", 0), "web_thickness")
        if 2 * tf >= d:
            raise ValueError("Flange thicknesses exceed total depth")
        hw = d - 2 * tf
        area = 2 * bf * tf + hw * tw
        # Parallel axis theorem for symmetric I
        Ix = (bf * d**3 - (bf - tw) * hw**3) / 12
        c_top = c_bottom = d / 2

    elif section_key == "box":
        b = _require_positive(dimensions.get("width", 0), "width")
        h = _require_positive(dimensions.get("depth", 0), "depth")
        t = _require_positive(dimensions.get("wall_thickness", 0), "wall_thickness")
        if 2 * t >= b or 2 * t >= h:
            raise ValueError("Wall thickness too large for section dimensions")
        bi = b - 2 * t
        hi = h - 2 * t
        area = b * h - bi * hi
        Ix = (b * h**3 - bi * hi**3) / 12
        c_top = c_bottom = h / 2

    elif section_key == "c_channel":
        d = _require_positive(dimensions.get("depth", 0), "depth")
        bf = _require_positive(dimensions.get("flange_width", 0), "flange_width")
        tf = _require_positive(dimensions.get("flange_thickness", 0), "flange_thickness")
        tw = _require_positive(dimensions.get("web_thickness", 0), "web_thickness")
        if 2 * tf >= d:
            raise ValueError("Flange thicknesses exceed total depth")
        hw = d - 2 * tf
        # Approximate - centroid on web centerline for symmetric loading
        area = 2 * bf * tf + hw * tw
        Ix = (tw * d**3 + 2 * bf * tf**3) / 12 + 2 * bf * tf * ((d - tf) / 2)**2
        c_top = c_bottom = d / 2

    elif section_key == "t_section":
        bf = _require_positive(dimensions.get("flange_width", 0), "flange_width")
        tf = _require_positive(dimensions.get("flange_thickness", 0), "flange_thickness")
        ds = _require_positive(dimensions.get("stem_depth", 0), "stem_depth")
        ts = _require_positive(dimensions.get("stem_thickness", 0), "stem_thickness")

        total_depth = tf + ds
        A_flange = bf * tf
        A_stem = ts * ds
        area = A_flange + A_stem

        # Centroid from top of flange
        y_flange = tf / 2
        y_stem = tf + ds / 2
        y_centroid = (A_flange * y_flange + A_stem * y_stem) / area

        c_top = y_centroid
        c_bottom = total_depth - y_centroid

        # Parallel axis theorem
        I_flange = bf * tf**3 / 12 + A_flange * (y_centroid - y_flange)**2
        I_stem = ts * ds**3 / 12 + A_stem * (y_stem - y_centroid)**2
        Ix = I_flange + I_stem

    elif section_key == "standard_steel":
        designation = dimensions.get("designation", "").replace(" ", "")
        # Case-insensitive lookup
        matched_key = None
        for key in STEEL_SECTIONS:
            if key.upper() == designation.upper():
                matched_key = key
                break
        if matched_key is None:
            available = ", ".join(STEEL_SECTIONS.keys())
            raise ValueError(f"Unknown steel section '{designation}'. Available: {available}")
        designation = matched_key
        props = STEEL_SECTIONS[designation]
        area = props["A"]
        Ix = props["Ix"]
        c_top = c_bottom = props["d"] / 2

    elif section_key == "custom":
        Ix = _require_positive(dimensions.get("moment_of_inertia", 0), "moment_of_inertia")
        c_top = _require_positive(dimensions.get("c_top", 0), "c_top")
        c_bottom = _require_positive(dimensions.get("c_bottom", 0), "c_bottom")
        area = float(dimensions.get("area", 0))

    else:
        raise ValueError(f"Unsupported section type: '{section_type}'")

    Sx_top = Ix / c_top
    Sx_bottom = Ix / c_bottom
    rx = sqrt(Ix / area) if area > 0 else 0

    return {
        "area": area,
        "Ix": Ix,
        "Sx_top": Sx_top,
        "Sx_bottom": Sx_bottom,
        "c_top": c_top,
        "c_bottom": c_bottom,
        "rx": rx,
    }


# =============================================================================
# BEAM ANALYSIS FUNCTIONS
# =============================================================================

def _compute_simply_supported_point_center(
    x_vals: List[float],
    L: float,
    P: float,
    E: float,
    I: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Simply supported beam with point load at center."""
    deflections, moments, shears = [], [], []
    R = P / 2
    mid = L / 2

    for x in x_vals:
        if x <= mid:
            shears.append(R)
            moments.append(R * x)
            deflections.append(P * x * (3 * L**2 - 4 * x**2) / (48 * E * I))
        else:
            shears.append(-R)
            moments.append(R * x - P * (x - mid))
            xi = L - x
            deflections.append(P * xi * (3 * L**2 - 4 * xi**2) / (48 * E * I))

    return deflections, moments, shears


def _compute_simply_supported_point_any(
    x_vals: List[float],
    L: float,
    P: float,
    E: float,
    I: float,
    a: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Simply supported beam with point load at position 'a' from left."""
    deflections, moments, shears = [], [], []
    b = L - a
    Ra = P * b / L  # Reaction at left
    Rb = P * a / L  # Reaction at right

    for x in x_vals:
        if x <= a:
            shears.append(Ra)
            moments.append(Ra * x)
            deflections.append(P * b * x * (L**2 - b**2 - x**2) / (6 * E * I * L))
        else:
            shears.append(-Rb)
            moments.append(Rb * (L - x))
            deflections.append(P * a * (L - x) * (L**2 - a**2 - (L - x)**2) / (6 * E * I * L))

    return deflections, moments, shears


def _compute_simply_supported_udl(
    x_vals: List[float],
    L: float,
    w: float,
    E: float,
    I: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Simply supported beam with uniform distributed load."""
    deflections, moments, shears = [], [], []
    R = w * L / 2

    for x in x_vals:
        shears.append(R - w * x)
        moments.append(w * x * (L - x) / 2)
        deflections.append(w * x * (L**3 - 2 * L * x**2 + x**3) / (24 * E * I))

    return deflections, moments, shears


def _compute_simply_supported_triangular(
    x_vals: List[float],
    L: float,
    w_max: float,
    E: float,
    I: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Simply supported beam with triangular load (0 at left, w_max at right)."""
    deflections, moments, shears = [], [], []
    # Total load = w_max * L / 2
    # Reactions: Ra = w_max * L / 6, Rb = w_max * L / 3
    Ra = w_max * L / 6

    for x in x_vals:
        # Load at position x: w(x) = w_max * x / L
        # Shear: V(x) = Ra - integral of w from 0 to x = Ra - w_max * x² / (2L)
        V = Ra - w_max * x**2 / (2 * L)
        shears.append(V)

        # Moment: M(x) = Ra * x - w_max * x³ / (6L)
        M = Ra * x - w_max * x**3 / (6 * L)
        moments.append(M)

        # Deflection (from Roark's)
        delta = w_max * x * (3 * x**4 - 10 * L**2 * x**2 + 7 * L**4) / (180 * E * I * L)
        deflections.append(delta)

    return deflections, moments, shears


def _compute_cantilever_point_end(
    x_vals: List[float],
    L: float,
    P: float,
    E: float,
    I: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Cantilever with point load at free end. x=0 is at fixed end."""
    deflections, moments, shears = [], [], []

    for x in x_vals:
        shears.append(P)
        moments.append(P * (L - x))
        deflections.append(P * x**2 * (3 * L - x) / (6 * E * I))

    return deflections, moments, shears


def _compute_cantilever_point_any(
    x_vals: List[float],
    L: float,
    P: float,
    E: float,
    I: float,
    a: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Cantilever with point load at distance 'a' from fixed end."""
    deflections, moments, shears = [], [], []

    for x in x_vals:
        if x <= a:
            shears.append(P)
            moments.append(P * (a - x))
            deflections.append(P * x**2 * (3 * a - x) / (6 * E * I))
        else:
            shears.append(0)
            moments.append(0)
            deflections.append(P * a**2 * (3 * x - a) / (6 * E * I))

    return deflections, moments, shears


def _compute_cantilever_udl(
    x_vals: List[float],
    L: float,
    w: float,
    E: float,
    I: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Cantilever with uniform distributed load."""
    deflections, moments, shears = [], [], []

    for x in x_vals:
        shears.append(w * (L - x))
        moments.append(w * (L - x)**2 / 2)
        deflections.append(w * x**2 * (6 * L**2 - 4 * L * x + x**2) / (24 * E * I))

    return deflections, moments, shears


def _compute_fixed_fixed_point_center(
    x_vals: List[float],
    L: float,
    P: float,
    E: float,
    I: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Fixed-fixed beam with point load at center."""
    deflections, moments, shears = [], [], []
    R = P / 2
    M_fixed = P * L / 8
    mid = L / 2

    for x in x_vals:
        if x <= mid:
            shears.append(R)
            moments.append(-M_fixed + R * x)
            deflections.append(P * x**2 * (3 * L - 4 * x) / (48 * E * I))
        else:
            shears.append(-R)
            xi = L - x
            moments.append(-M_fixed + R * xi)
            deflections.append(P * xi**2 * (3 * L - 4 * xi) / (48 * E * I))

    return deflections, moments, shears


def _compute_fixed_fixed_udl(
    x_vals: List[float],
    L: float,
    w: float,
    E: float,
    I: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Fixed-fixed beam with uniform distributed load."""
    deflections, moments, shears = [], [], []
    R = w * L / 2
    M_fixed = w * L**2 / 12

    for x in x_vals:
        shears.append(R - w * x)
        moments.append(-M_fixed + R * x - w * x**2 / 2)
        deflections.append(w * x**2 * (L - x)**2 / (24 * E * I))

    return deflections, moments, shears


def _compute_propped_cantilever_udl(
    x_vals: List[float],
    L: float,
    w: float,
    E: float,
    I: float,
) -> Tuple[List[float], List[float], List[float]]:
    """Propped cantilever (fixed at left, pinned at right) with UDL."""
    deflections, moments, shears = [], [], []
    # Reactions: Ra = 5wL/8, Rb = 3wL/8, Ma = wL²/8
    Ra = 5 * w * L / 8
    Ma = w * L**2 / 8

    for x in x_vals:
        shears.append(Ra - w * x)
        moments.append(-Ma + Ra * x - w * x**2 / 2)
        # Deflection formula for propped cantilever
        deflections.append(w * x**2 * (L - x) * (2 * L - x) / (48 * E * I))

    return deflections, moments, shears


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def beam_analysis(
    load_case: str,
    section_type: str,
    section_dimensions: Dict[str, Any],
    span: float,
    load_value: float,
    material: str = "steel_structural",
    elastic_modulus: Optional[float] = None,
    yield_strength: Optional[float] = None,
    load_position: Optional[float] = None,
    deflection_limit: str = "L/360",
    custom_deflection_ratio: Optional[float] = None,
    num_points: int = 101,
    safety_factor: float = 1.5,
) -> Dict[str, Any]:
    """
    Comprehensive beam bending analysis with safety checks.

    This function analyzes elastic beam behavior for common loading
    configurations, computing deflections, moments, shears, and stresses
    with reference equations and safety assessments.

    ---Parameters---
    load_case : str
        Loading configuration identifier. Available cases:
        - ``"simply_supported_point_center"`` - Point load at midspan
        - ``"simply_supported_point_any"`` - Point load at specified position
        - ``"simply_supported_udl"`` - Uniform distributed load
        - ``"simply_supported_triangular"`` - Triangular distributed load
        - ``"cantilever_point_end"`` - Cantilever with end load
        - ``"cantilever_point_any"`` - Cantilever with load at position
        - ``"cantilever_udl"`` - Cantilever with distributed load
        - ``"fixed_fixed_point_center"`` - Fixed ends with center load
        - ``"fixed_fixed_udl"`` - Fixed ends with distributed load
        - ``"propped_cantilever_udl"`` - Propped cantilever with UDL

    section_type : str
        Cross-section type (see ``compute_section_properties``).

    section_dimensions : dict
        Dimensional parameters for the section (metres).

    span : float
        Beam span or length (m). Must be positive.

    load_value : float
        Applied load magnitude. For point loads use N, for distributed
        loads use N/m. Must be positive.

    material : str, optional
        Material identifier from the materials database. Defaults to
        ``"steel_structural"``. Use ``"custom"`` with explicit E and Fy.

    elastic_modulus : float, optional
        Override material's elastic modulus (Pa). Required if material
        is ``"custom"``.

    yield_strength : float, optional
        Override material's yield strength (Pa). Used for stress checks.

    load_position : float, optional
        Position of point load from left support (m). Required for
        ``"_any"`` load cases.

    deflection_limit : str, optional
        Deflection limit code (e.g., ``"L/360"``). Defaults to ``"L/360"``.

    custom_deflection_ratio : float, optional
        Custom deflection ratio when deflection_limit is ``"custom"``.

    num_points : int, optional
        Number of points for curve discretization. Default 101.

    safety_factor : float, optional
        Factor of safety for allowable stress. Default 1.5.

    ---Returns---
    max_deflection : float
        Maximum deflection magnitude (m).
    max_deflection_position : float
        Position of maximum deflection along span (m).
    max_moment : float
        Maximum bending moment magnitude (N·m).
    max_shear : float
        Maximum shear force magnitude (N).
    max_stress : float
        Maximum bending stress (Pa).
    allowable_deflection : float
        Deflection limit based on selected code (m).
    deflection_utilization : float
        Ratio of actual to allowable deflection (%).
    stress_utilization : float
        Ratio of actual to allowable stress (%).
    allowable_stress : float
        Yield strength divided by safety factor (Pa).
    curve : list
        List of dicts with x, deflection, moment, shear at each point.
    section_properties : dict
        Computed section properties.
    load_case_info : dict
        Metadata about the selected load case.
    status : str
        Overall status: "acceptable", "marginal", or "unacceptable".
    warnings : list
        List of warning messages.
    recommendations : list
        List of design recommendations.

    ---LaTeX---
    \\sigma_{max} = \\frac{M_{max} \\cdot c}{I}
    \\text{Utilization} = \\frac{\\sigma_{max}}{\\sigma_{allow}} \\times 100\\%
    \\delta_{allow} = \\frac{L}{\\text{limit ratio}}

    ---References---
    Roark's Formulas for Stress and Strain, 8th Edition, Table 8.1
    AISC Steel Construction Manual, 15th Edition, Chapter D
    """
    results: Dict[str, Any] = {
        "warnings": [],
        "recommendations": [],
    }

    # --- Input validation ---
    try:
        span = float(span)
        load_value = float(load_value)
        num_points = int(num_points)
        safety_factor = float(safety_factor)
    except (TypeError, ValueError) as e:
        return {"error": f"Invalid input type: {e}"}

    if span <= 0:
        return {"error": "Span must be greater than zero"}
    if load_value <= 0:
        return {"error": "Load value must be greater than zero"}
    if num_points < 10:
        return {"error": "Use at least 10 points for analysis"}
    if safety_factor < 1:
        return {"error": "Safety factor must be at least 1.0"}

    # --- Material properties ---
    mat_key = material.lower().strip()
    if mat_key not in MATERIALS:
        available = ", ".join(MATERIALS.keys())
        return {"error": f"Unknown material '{material}'. Available: {available}"}

    mat = MATERIALS[mat_key]
    E = elastic_modulus if elastic_modulus is not None else mat["E"]
    Fy = yield_strength if yield_strength is not None else mat["yield_strength"]

    if E <= 0:
        return {"error": "Elastic modulus must be positive"}
    if Fy <= 0:
        return {"error": "Yield strength must be positive"}

    # --- Section properties ---
    try:
        section_props = compute_section_properties(section_type, section_dimensions)
    except ValueError as e:
        return {"error": str(e)}

    I = section_props["Ix"]
    c_max = max(section_props["c_top"], section_props["c_bottom"])

    # --- Load case validation ---
    case_key = load_case.lower().strip()
    if case_key not in LOAD_CASES:
        available = ", ".join(LOAD_CASES.keys())
        return {"error": f"Unknown load case '{load_case}'. Available: {available}"}

    case_info = LOAD_CASES[case_key]

    # Validate load position for "any" cases
    a = None
    if "any" in case_key:
        if load_position is None:
            return {"error": f"Load position required for '{load_case}'"}
        a = float(load_position)
        if a <= 0 or a >= span:
            return {"error": f"Load position must be between 0 and span ({span} m)"}

    # --- Build x-coordinate array ---
    x_vals = [span * i / (num_points - 1) for i in range(num_points)]

    # --- Compute response curves ---
    if case_key == "simply_supported_point_center":
        deflections, moments, shears = _compute_simply_supported_point_center(
            x_vals, span, load_value, E, I
        )
    elif case_key == "simply_supported_point_any":
        deflections, moments, shears = _compute_simply_supported_point_any(
            x_vals, span, load_value, E, I, a
        )
    elif case_key == "simply_supported_udl":
        deflections, moments, shears = _compute_simply_supported_udl(
            x_vals, span, load_value, E, I
        )
    elif case_key == "simply_supported_triangular":
        deflections, moments, shears = _compute_simply_supported_triangular(
            x_vals, span, load_value, E, I
        )
    elif case_key == "cantilever_point_end":
        deflections, moments, shears = _compute_cantilever_point_end(
            x_vals, span, load_value, E, I
        )
    elif case_key == "cantilever_point_any":
        deflections, moments, shears = _compute_cantilever_point_any(
            x_vals, span, load_value, E, I, a
        )
    elif case_key == "cantilever_udl":
        deflections, moments, shears = _compute_cantilever_udl(
            x_vals, span, load_value, E, I
        )
    elif case_key == "fixed_fixed_point_center":
        deflections, moments, shears = _compute_fixed_fixed_point_center(
            x_vals, span, load_value, E, I
        )
    elif case_key == "fixed_fixed_udl":
        deflections, moments, shears = _compute_fixed_fixed_udl(
            x_vals, span, load_value, E, I
        )
    elif case_key == "propped_cantilever_udl":
        deflections, moments, shears = _compute_propped_cantilever_udl(
            x_vals, span, load_value, E, I
        )
    else:
        return {"error": f"Load case '{case_key}' not implemented"}

    # --- Extract maxima ---
    max_defl_idx = max(range(len(deflections)), key=lambda i: abs(deflections[i]))
    max_deflection = abs(deflections[max_defl_idx])
    max_deflection_position = x_vals[max_defl_idx]
    max_moment = max(abs(m) for m in moments)
    max_shear = max(abs(v) for v in shears)

    # --- Stress calculation ---
    max_stress = max_moment * c_max / I
    allowable_stress = Fy / safety_factor

    # --- Deflection limits ---
    if deflection_limit == "custom":
        if custom_deflection_ratio is None:
            return {"error": "custom_deflection_ratio required when using 'custom' limit"}
        limit_ratio = custom_deflection_ratio
    else:
        if deflection_limit not in DEFLECTION_LIMITS:
            available = ", ".join(DEFLECTION_LIMITS.keys())
            return {"error": f"Unknown deflection limit. Available: {available}"}
        limit_ratio = DEFLECTION_LIMITS[deflection_limit]["ratio"]

    allowable_deflection = span / limit_ratio

    # --- Utilization calculations ---
    deflection_utilization = (max_deflection / allowable_deflection) * 100
    stress_utilization = (max_stress / allowable_stress) * 100

    # --- Status determination ---
    warnings = []
    recommendations = []

    if stress_utilization > 100:
        status = "unacceptable"
        warnings.append(f"Stress exceeds allowable: {stress_utilization:.1f}% utilization")
        recommendations.append("Increase section size or reduce load")
        recommendations.append("Consider higher-strength material")
    elif deflection_utilization > 100:
        status = "unacceptable"
        warnings.append(f"Deflection exceeds limit: {deflection_utilization:.1f}% utilization")
        recommendations.append("Increase section stiffness (larger I)")
        recommendations.append("Reduce span or add intermediate supports")
    elif stress_utilization > 85 or deflection_utilization > 85:
        status = "marginal"
        if stress_utilization > 85:
            warnings.append(f"Stress utilization is high: {stress_utilization:.1f}%")
        if deflection_utilization > 85:
            warnings.append(f"Deflection utilization is high: {deflection_utilization:.1f}%")
        recommendations.append("Consider increasing section size for margin")
    else:
        status = "acceptable"

    # --- Beam weight estimate ---
    mat_density = mat.get("density", 7850)
    beam_weight = section_props["area"] * span * mat_density * 9.81  # N

    # --- Build curve data ---
    curve = [
        {
            "x": x,
            "deflection": d,
            "moment": m,
            "shear": v,
        }
        for x, d, m, v in zip(x_vals, deflections, moments, shears)
    ]

    # --- Compile results ---
    results.update({
        # Primary results
        "max_deflection": max_deflection,
        "max_deflection_position": max_deflection_position,
        "max_moment": max_moment,
        "max_shear": max_shear,
        "max_stress": max_stress,

        # Limits and utilization
        "allowable_deflection": allowable_deflection,
        "allowable_stress": allowable_stress,
        "deflection_utilization": deflection_utilization,
        "stress_utilization": stress_utilization,
        "deflection_limit_code": deflection_limit,

        # Status
        "status": status,
        "warnings": warnings,
        "recommendations": recommendations,

        # Properties
        "section_properties": section_props,
        "material": {
            "name": mat["name"],
            "E": E,
            "yield_strength": Fy,
            "density": mat_density,
        },
        "beam_weight": beam_weight,

        # Curve data
        "curve": curve,

        # Load case info
        "load_case_info": {
            "name": case_info.name,
            "description": case_info.description,
            "support_type": case_info.support_type,
            "load_type": case_info.load_type,
            "max_moment_formula": case_info.max_moment_formula,
            "max_deflection_formula": case_info.max_deflection_formula,
            "max_shear_formula": case_info.max_shear_formula,
        },

        # Input summary
        "inputs": {
            "span": span,
            "load_value": load_value,
            "load_position": a,
            "safety_factor": safety_factor,
        },
    })

    return results


def get_available_load_cases() -> Dict[str, str]:
    """Return dict of load case keys to display names."""
    return {key: info.name for key, info in LOAD_CASES.items()}


def get_available_materials() -> Dict[str, str]:
    """Return dict of material keys to display names."""
    return {key: mat["name"] for key, mat in MATERIALS.items()}


def get_available_steel_sections() -> Dict[str, str]:
    """Return dict of steel section designations."""
    return {key: props["name"] for key, props in STEEL_SECTIONS.items()}


def get_deflection_limits() -> Dict[str, str]:
    """Return dict of deflection limit codes to descriptions."""
    return {key: info["application"] for key, info in DEFLECTION_LIMITS.items()}
