"""Residential heating and cooling load calculation from published physics.

The heating side is the steady-state UA*dT procedure in ASHRAE Handbook
Fundamentals Chapter 17. The cooling side solves a 24-hour design day:

* clear-sky solar on each surface (ASHRAE Fundamentals Chapter 14 geometry),
* periodic conduction through the actual wall and roof layers (transmission
  matrices, the exact one-dimensional solution, as in the CIBSE admittance
  method and Carslaw and Jaeger),
* an attic heat balance (ASHRAE Chapter 17, Equation 5),
* a zone air and thermal mass model that finds the capacity which holds the
  room within an allowed temperature swing above the thermostat setting,
  the same control assumption as ASHRAE's Residential Heat Balance method.

Air leakage follows ASHRAE Chapter 17 Equations 8 to 14. Duct losses come from
an energy balance on the duct system, the formulation behind ASHRAE Standard
152. All units are US customary: Btu/h, °F, ft², cfm, unless noted.
"""

from __future__ import annotations

import cmath
import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# =============================================================================
# PHYSICAL CONSTANTS AND TABLES
# =============================================================================

HOURS = list(range(1, 25))
N_HARMONICS = 8
TON_BTUH = 12000.0
KW_BTUH = 3412.14

# ASHRAE clear-sky coefficients for the 21st of each month (A in Btu/h·ft²):
# (apparent solar irradiation, atmospheric extinction, diffuse ratio).
CLEAR_SKY = {
    1: (390, 0.142, 0.058),
    2: (385, 0.144, 0.060),
    3: (376, 0.156, 0.071),
    4: (360, 0.180, 0.097),
    5: (350, 0.196, 0.121),
    6: (345, 0.205, 0.134),
    7: (344, 0.207, 0.136),
    8: (351, 0.201, 0.122),
    9: (365, 0.177, 0.092),
    10: (378, 0.160, 0.073),
    11: (387, 0.149, 0.063),
    12: (391, 0.142, 0.057),
}
DECLINATION_DEG = {
    1: -20.0, 2: -10.8, 3: 0.0, 4: 11.6, 5: 20.0, 6: 23.45,
    7: 20.6, 8: 12.3, 9: 0.0, 10: -10.5, 11: -19.8, 12: -23.45,
}

# ASHRAE Fundamentals Chapter 14: fraction of the daily range below the peak
# temperature at each solar hour (hour 15 is the peak).
DAILY_RANGE_FRACTION = [
    0.88, 0.92, 0.95, 0.98, 1.00, 0.98, 0.91, 0.74, 0.55, 0.38, 0.23, 0.13,
    0.05, 0.00, 0.00, 0.06, 0.14, 0.24, 0.39, 0.50, 0.59, 0.68, 0.75, 0.82,
]

# Window solar heat gain relative to normal incidence, double glazing
# (ASHRAE Fundamentals Chapter 15, Table 4 pattern).
SHGC_ANGLE = [
    (0, 1.00), (40, 0.98), (50, 0.93), (60, 0.83),
    (70, 0.62), (80, 0.34), (90, 0.0),
]
SHGC_DIFFUSE_RATIO = 0.89

COMPASS_DEG = {
    "S": 0.0, "SW": 45.0, "W": 90.0, "NW": 135.0,
    "N": 180.0, "NE": -135.0, "E": -90.0, "SE": -45.0,
}

# Material properties: conductivity Btu/h·ft·°F, density lb/ft³, specific heat.
MATERIALS = {
    "insulation": (0.025, 1.5, 0.22),
    "gypsum": (0.093, 50.0, 0.26),
    "osb": (0.08, 40.0, 0.31),
    "siding": (0.10, 40.0, 0.30),
    "brick": (0.45, 120.0, 0.20),
    "cmu": (0.55, 90.0, 0.20),
    "concrete": (0.80, 140.0, 0.20),
    "shingle": (0.10, 70.0, 0.30),
}

# Layer stacks from outside to inside. Insulation thickness is solved so the
# whole assembly matches the U-factor the user chose.
WALL_LAYERS = {
    "frame": [("siding", 0.5), ("osb", 0.5), ("insulation", None), ("gypsum", 0.5)],
    "brick_veneer": [("brick", 3.625), ("osb", 0.5), ("insulation", None), ("gypsum", 0.5)],
    "cmu": [("cmu", 8.0), ("insulation", None), ("gypsum", 0.5)],
    "concrete": [("insulation", None), ("concrete", 6.0), ("insulation", None), ("gypsum", 0.5)],
}
ROOF_LAYERS = [("shingle", 0.25), ("osb", 0.625), ("insulation", None), ("gypsum", 0.5)]
CEILING_LAYERS = [("insulation", None), ("gypsum", 0.5)]

R_FILM_IN = 0.68
H_OUT_WALL = 3.0
H_OUT_ROOF = 4.0

# Radiant share of each gain. The radiant part warms room surfaces first and
# reaches the air later. ASHRAE Fundamentals Chapter 18, Table 14.
RADIANT_FRACTION = {
    "walls": 0.46, "doors": 0.46, "ceiling": 0.60, "floor": 0.46,
    "window_conduction": 0.33, "window_solar": 1.00, "internal": 0.50,
    "infiltration": 0.0, "ventilation": 0.0,
}

# Active thermal mass per ft² of floor, as capacity (Btu/°F) and surface
# conductance (Btu/h·°F). The light values were calibrated once, so a 3 °F swing
# reproduces the ASHRAE Chapter 17 worked example's room load. That gives a time
# constant of one hour, in line with ASHRAE's light-construction radiant time
# series. Medium and heavy double and quadruple the capacity.
THERMAL_MASS = {
    "light": {"capacity": 1.5, "conductance": 1.5},
    "medium": {"capacity": 3.0, "conductance": 1.5},
    "heavy": {"capacity": 6.0, "conductance": 1.5},
}

ROOF_ABSORPTANCE = {
    "white": 0.30, "light": 0.60, "medium": 0.85, "dark": 0.92,
    "metal_light": 0.50, "tile_light": 0.40,
}
INTERIOR_SHADE_IAC = {
    "none": 1.00, "light_blinds_half": 0.90, "drapes_half": 0.84,
    "blinds_closed": 0.74, "cellular_closed": 0.60,
}
SCREEN_TX = {"none": 1.00, "half": 0.82, "full": 0.64}

# Slab edge heat-loss coefficient F_p, Btu/h·ft·°F. "none" matches current
# Manual J software output; "r5" is the ASHRAE Chapter 17 worked example.
SLAB_EDGE_F = {"none": 1.18, "r5": 0.50, "r10": 0.40, "r15": 0.33}
SOIL_K = 0.8

DUCT_LOCATIONS = (
    "conditioned", "attic", "vented_crawl", "sealed_crawl", "basement", "garage",
)
ZONE_GAIN_WEIGHT = {
    "kitchen": 3.0, "living": 2.0, "bedroom": 0.3, "bath": 0.2,
    "office": 0.5, "other": 0.3,
}

# =============================================================================
# PRESETS (the single source for every dropdown and quick-mode assumption)
# =============================================================================

WALL_PRESETS = {
    "2x4_none": {"label": "2x4, no insulation (often pre-1960)", "u": 0.23, "layers": "frame"},
    "2x4_r11": {"label": "2x4, R-11 cavity", "u": 0.105, "layers": "frame"},
    "2x4_r13": {"label": "2x4, R-13 cavity", "u": 0.090, "layers": "frame"},
    "2x4_r15": {"label": "2x4, R-15 cavity", "u": 0.083, "layers": "frame"},
    "2x6_r19": {"label": "2x6, R-19 cavity", "u": 0.065, "layers": "frame"},
    "2x6_r21": {"label": "2x6, R-21 cavity", "u": 0.060, "layers": "frame"},
    "2x6_r21_ci5": {"label": "2x6, R-21 + R-5 foam sheathing", "u": 0.048, "layers": "frame"},
    "brick_r13": {"label": "Brick veneer over 2x4, R-13", "u": 0.085, "layers": "brick_veneer"},
    "cmu_none": {"label": "Block or brick masonry, no insulation", "u": 0.35, "layers": "cmu"},
    "cmu_r10": {"label": "Block with R-10 interior insulation", "u": 0.075, "layers": "cmu"},
    "icf": {"label": "Insulated concrete forms", "u": 0.045, "layers": "concrete"},
}
CEILING_PRESETS = {
    "none": {"label": "No insulation", "u": 0.50},
    "r11": {"label": "R-11", "u": 0.083},
    "r19": {"label": "R-19", "u": 0.050},
    "r30": {"label": "R-30", "u": 0.032},
    "r38": {"label": "R-38", "u": 0.026},
    "r49": {"label": "R-49", "u": 0.020},
    "r60": {"label": "R-60", "u": 0.016},
}
WINDOW_PRESETS = {
    "single_clear": {"label": "Single pane, wood frame", "u": 0.89, "shgc": 0.64},
    "single_alum": {"label": "Single pane, aluminum frame", "u": 1.27, "shgc": 0.75},
    "single_storm": {"label": "Single pane with storm window", "u": 0.51, "shgc": 0.57},
    "double_clear_alum": {"label": "Double clear, aluminum frame", "u": 0.81, "shgc": 0.67},
    "double_clear": {"label": "Double clear, vinyl or wood", "u": 0.51, "shgc": 0.57},
    "double_lowe_low": {"label": "Double low-e, low solar gain", "u": 0.32, "shgc": 0.26},
    "double_lowe_high": {"label": "Double low-e, high solar gain", "u": 0.35, "shgc": 0.52},
    "triple_lowe": {"label": "Triple low-e", "u": 0.22, "shgc": 0.21},
}
ERA_PRESETS = {
    "pre1950": {
        "label": "Before 1950, mostly original",
        "wall_preset": "2x4_none", "ceiling_preset": "r11",
        "window_preset": "single_storm", "ach50": 15.0,
        "slab_edge": "none", "duct_leakage_pct": 15.0, "duct_r": 2.0,
    },
    "1950s_70s": {
        "label": "1950 to 1979",
        "wall_preset": "2x4_r11", "ceiling_preset": "r19",
        "window_preset": "double_clear_alum", "ach50": 10.0,
        "slab_edge": "none", "duct_leakage_pct": 12.0, "duct_r": 4.0,
    },
    "1980s_90s": {
        "label": "1980 to 1999",
        "wall_preset": "2x4_r13", "ceiling_preset": "r30",
        "window_preset": "double_clear", "ach50": 7.0,
        "slab_edge": "none", "duct_leakage_pct": 10.0, "duct_r": 6.0,
    },
    "2000s": {
        "label": "2000 to 2015",
        "wall_preset": "2x4_r15", "ceiling_preset": "r38",
        "window_preset": "double_lowe_low", "ach50": 5.0,
        "slab_edge": "r5", "duct_leakage_pct": 7.0, "duct_r": 8.0,
    },
    "new_code": {
        "label": "2016 or newer",
        "wall_preset": "2x6_r21", "ceiling_preset": "r49",
        "window_preset": "double_lowe_low", "ach50": 3.0,
        "slab_edge": "r10", "duct_leakage_pct": 4.0, "duct_r": 8.0,
    },
    "high_perf": {
        "label": "High performance or deep retrofit",
        "wall_preset": "2x6_r21_ci5", "ceiling_preset": "r60",
        "window_preset": "triple_lowe", "ach50": 1.5,
        "slab_edge": "r15", "duct_leakage_pct": 3.0, "duct_r": 8.0,
    },
}


def get_presets() -> Dict[str, Any]:
    """Return every preset table so the page has one source for its options."""
    return {
        "walls": WALL_PRESETS,
        "ceilings": CEILING_PRESETS,
        "windows": WINDOW_PRESETS,
        "eras": ERA_PRESETS,
    }


# =============================================================================
# MOIST AIR
# =============================================================================


def pressure_psia(elevation_ft: float) -> float:
    """Standard atmospheric pressure at elevation (ASHRAE Fundamentals Ch. 1)."""
    return 14.696 * (1 - 6.8754e-6 * elevation_ft) ** 5.2559


def saturation_pressure_psia(t_f: float) -> float:
    """Saturation vapor pressure over liquid water (Hyland and Wexler)."""
    t_k = (t_f + 459.67) / 1.8
    ln_pws = (
        -5.8002206e3 / t_k + 1.3914993 - 4.8640239e-2 * t_k
        + 4.1764768e-5 * t_k ** 2 - 1.4452093e-8 * t_k ** 3
        + 6.5459673 * math.log(t_k)
    )
    return math.exp(ln_pws) / 6894.757


def humidity_ratio_from_rh(t_f: float, rh_pct: float, p_psia: float) -> float:
    """Humidity ratio (lb water per lb dry air) from dry bulb and RH."""
    pw = rh_pct / 100.0 * saturation_pressure_psia(t_f)
    return 0.621945 * pw / (p_psia - pw)


def humidity_ratio_from_wet_bulb(t_f: float, wb_f: float, p_psia: float) -> float:
    """Humidity ratio from dry bulb and wet bulb (ASHRAE Ch. 1, Eq. 35)."""
    ps = saturation_pressure_psia(wb_f)
    ws = 0.621945 * ps / (p_psia - ps)
    return ((1093 - 0.556 * wb_f) * ws - 0.240 * (t_f - wb_f)) / (
        1093 + 0.444 * t_f - wb_f
    )


def air_factors(elevation_ft: float) -> Tuple[float, float]:
    """Sensible and latent air factors, Btu/h per cfm, corrected for altitude.

    C_s is 1.08 Btu/h·cfm·°F and C_l is 4840 Btu/h·cfm per lb/lb at sea level.
    """
    ratio = pressure_psia(elevation_ft) / 14.696
    return 1.08 * ratio, 4840.0 * ratio


# =============================================================================
# SOLAR
# =============================================================================


def solar_altitude_azimuth(latitude: float, declination: float, hour: float) -> Tuple[float, float]:
    """Solar altitude and azimuth (degrees, azimuth from south, west positive)."""
    lat = math.radians(latitude)
    dec = math.radians(declination)
    hour_angle = math.radians(15.0 * (hour - 12.0))
    sin_alt = (
        math.cos(lat) * math.cos(dec) * math.cos(hour_angle)
        + math.sin(lat) * math.sin(dec)
    )
    altitude = math.asin(max(-1.0, min(1.0, sin_alt)))
    if math.cos(altitude) < 1e-6:
        return math.degrees(altitude), 0.0
    sin_az = math.sin(hour_angle) * math.cos(dec) / math.cos(altitude)
    cos_az = (
        math.cos(hour_angle) * math.cos(dec) * math.sin(lat)
        - math.sin(dec) * math.cos(lat)
    ) / math.cos(altitude)
    return math.degrees(altitude), math.degrees(math.atan2(sin_az, cos_az))


def surface_irradiance(
    latitude: float,
    month: int,
    hour: float,
    surface_azimuth: float,
    tilt: float = 90.0,
    ground_reflectance: float = 0.2,
) -> Dict[str, float]:
    """Clear-sky direct, diffuse, and reflected irradiance on a surface.

    ---Parameters---
    latitude : float
        Site latitude in degrees north.
    month : int
        Month of the design day (solar values are for the 21st).
    hour : float
        Solar time, 0 to 24.
    surface_azimuth : float
        Direction the surface faces, degrees from south, west positive.
    tilt : float
        Surface tilt from horizontal in degrees, 90 for a wall.
    ground_reflectance : float
        Fraction of horizontal irradiance reflected by the ground.

    ---Returns---
    direct : float
        Beam irradiance on the surface, Btu/h·ft².
    diffuse : float
        Sky plus ground-reflected irradiance, Btu/h·ft².
    cos_incidence : float
        Cosine of the angle between the sun and the surface normal.
    altitude : float
        Solar altitude, degrees.
    gamma : float
        Sun azimuth relative to the surface azimuth, degrees.

    ---LaTeX---
    I_{DN} = A \\exp(-B / \\sin\\beta)
    \\cos\\theta = \\cos\\beta\\cos\\gamma\\sin\\Sigma + \\sin\\beta\\cos\\Sigma
    E_d = C I_{DN} Y + \\rho_g I_{DN}(C + \\sin\\beta)\\frac{1-\\cos\\Sigma}{2}
    """
    altitude, azimuth = solar_altitude_azimuth(latitude, DECLINATION_DEG[month], hour)
    gamma = azimuth - surface_azimuth
    gamma = (gamma + 180.0) % 360.0 - 180.0
    if altitude <= 0.5:
        return {"direct": 0.0, "diffuse": 0.0, "cos_incidence": 0.0,
                "altitude": altitude, "gamma": gamma}
    a, b, c = CLEAR_SKY[month]
    beta = math.radians(altitude)
    sigma = math.radians(tilt)
    i_dn = a * math.exp(-b / math.sin(beta))
    cos_theta = (
        math.cos(beta) * math.cos(math.radians(gamma)) * math.sin(sigma)
        + math.sin(beta) * math.cos(sigma)
    )
    direct = i_dn * max(cos_theta, 0.0)
    if tilt > 89.0:
        y = max(0.45, 0.55 + 0.437 * cos_theta + 0.313 * cos_theta ** 2)
        sky = c * i_dn * y
    else:
        sky = c * i_dn * (1 + math.cos(sigma)) / 2
    reflected = (
        i_dn * (c + math.sin(beta)) * ground_reflectance * (1 - math.cos(sigma)) / 2
    )
    return {"direct": direct, "diffuse": sky + reflected,
            "cos_incidence": max(cos_theta, 0.0), "altitude": altitude, "gamma": gamma}


def _interpolate(table: Sequence[Tuple[float, float]], x: float) -> float:
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def _overhang_shaded_fraction(
    sun: Dict[str, float], depth: float, gap: float, height: float
) -> float:
    """Fraction of a window shaded by an overhang at this hour."""
    if depth <= 0 or sun["altitude"] <= 0 or abs(sun["gamma"]) >= 89.9:
        return 0.0
    shadow = depth * math.tan(math.radians(sun["altitude"])) / math.cos(
        math.radians(sun["gamma"])
    )
    return max(0.0, min(1.0, (shadow - gap) / max(height, 0.1)))


# =============================================================================
# PERIODIC HEAT CONDUCTION
# =============================================================================


def _dft(series: Sequence[float]) -> List[complex]:
    """Fourier coefficients of a 24-hour series, zero through N_HARMONICS."""
    coefficients = []
    for n in range(N_HARMONICS + 1):
        total = 0j
        for hour, value in zip(HOURS, series):
            total += value * cmath.exp(-2j * math.pi * n * hour / 24.0)
        coefficients.append(total / 24.0)
    return coefficients


def _idft(coefficients: Sequence[complex]) -> List[float]:
    out = []
    for hour in HOURS:
        value = coefficients[0].real
        for n in range(1, len(coefficients)):
            value += 2.0 * (
                coefficients[n] * cmath.exp(2j * math.pi * n * hour / 24.0)
            ).real
        out.append(value)
    return out


def transfer_admittances(
    layers: Sequence[Tuple[str, Optional[float]]], u_value: float, r_out: float
) -> List[complex]:
    """Heat flux into the room per degree of outside temperature, per harmonic.

    Each layer is a two-port transmission matrix. Their product is the exact
    periodic solution of the one-dimensional heat equation through the stack.

    ---Parameters---
    layers : list
        (material, thickness in inches) from outside to inside. A thickness of
        None marks insulation, sized so the assembly matches u_value.
    u_value : float
        Overall assembly U-factor, Btu/h·ft²·°F.
    r_out : float
        Outside surface film resistance, ft²·h·°F/Btu.

    ---Returns---
    admittances : list
        Complex transfer admittance for harmonics zero through N_HARMONICS.
        The zero harmonic equals u_value.

    ---LaTeX---
    M_j = \\begin{pmatrix} \\cosh(sL) & \\sinh(sL)/(ks) \\\\ ks\\sinh(sL) & \\cosh(sL) \\end{pmatrix}, \\quad s = \\sqrt{i\\omega\\rho c/k}
    Y_n = 1 / M_{12}
    """
    fixed_r = r_out + R_FILM_IN
    n_insulation = 0
    for material, inches in layers:
        if inches is None:
            n_insulation += 1
        else:
            fixed_r += (inches / 12.0) / MATERIALS[material][0]
    insulation_r = max((1.0 / u_value - fixed_r), 0.05 * n_insulation) / max(n_insulation, 1)
    # Thin assemblies can have fixed layers above the target R: scale them via
    # the steady term below so harmonic zero still equals u_value exactly.
    resolved: List[Tuple[str, float]] = []
    for material, inches in layers:
        if inches is None:
            thickness = insulation_r * MATERIALS["insulation"][0]
            resolved.append(("insulation", thickness))
        else:
            resolved.append((material, inches / 12.0))

    admittances: List[complex] = [complex(u_value)]
    for n in range(1, N_HARMONICS + 1):
        omega = 2.0 * math.pi * n / 24.0
        m11, m12, m21, m22 = 1 + 0j, complex(r_out), 0j, 1 + 0j
        for material, length in resolved:
            k, rho, c = MATERIALS[material]
            s = cmath.sqrt(1j * omega * rho * c / k)
            x = s * length
            a, b = cmath.cosh(x), cmath.sinh(x) / (k * s)
            d = k * s * cmath.sinh(x)
            m11, m12, m21, m22 = (
                m11 * a + m12 * d, m11 * b + m12 * a,
                m21 * a + m22 * d, m21 * b + m22 * a,
            )
        m12 = m11 * R_FILM_IN + m12
        admittances.append(1.0 / m12)
    return admittances


def periodic_flux(driving_excess: Sequence[float], admittances: Sequence[complex]) -> List[float]:
    """Hourly heat flux into the room for a 24-hour driving temperature."""
    coefficients = _dft(driving_excess)
    return _idft([c * y for c, y in zip(coefficients, admittances)])


def low_pass(series: Sequence[float], tau_hours: float) -> List[float]:
    """Periodic first-order lag: the exact response of one thermal mass."""
    coefficients = _dft(series)
    filtered = [
        c / (1 + 1j * (2 * math.pi * n / 24.0) * tau_hours)
        for n, c in enumerate(coefficients)
    ]
    return _idft(filtered)


# =============================================================================
# AIR LEAKAGE
# =============================================================================


def leakage_area_in2(ach50: float, volume_ft3: float) -> float:
    """Effective leakage area at 4 Pa from a blower door result.

    ---LaTeX---
    A_L = 0.055 \\times \\mathrm{CFM50} = 0.055 \\times \\frac{ACH_{50} V}{60}
    """
    return 0.055 * ach50 * volume_ft3 / 60.0


def infiltration_driving_force(stack_height_ft: float, delta_t_f: float, heating: bool,
                               flue_fraction: float = 0.0) -> float:
    """Infiltration driving force, cfm/in² (ASHRAE Ch. 17, Equation 10).

    ---LaTeX---
    IDF = \\frac{I_0 + H|\\Delta t|(I_1 + I_2 A_{L,flue}/A_L)}{1000}
    """
    i0, i1, i2 = (698.0, 0.81, 0.53) if heating else (343.0, 0.88, 0.28)
    return (i0 + stack_height_ft * abs(delta_t_f) * (i1 + i2 * flue_fraction)) / 1000.0


# =============================================================================
# DUCT LOSS FACTORS
# =============================================================================

# ASHRAE Fundamentals Chapter 17, Table 6, computed with the Francisco and
# Palmiter duct model for the ASHRAE Standard 152 default duct area. Keys are
# stories (1 or 2 and up), then mode, then location. Values are loss factors at
# duct insulation R-0, R-4, and R-8, for 11% and then 5% leakage on each side.
_DUCT_TABLE = {
    1: {
        "attic": {"C": ((1.26, 0.71, 0.63), (0.68, 0.33, 0.27)),
                  "F": ((0.49, 0.29, 0.25), (0.34, 0.16, 0.13)),
                  "HP": ((0.56, 0.37, 0.34), (0.34, 0.19, 0.16))},
        "basement": {"C": ((0.12, 0.09, 0.09), (0.07, 0.05, 0.04)),
                     "F": ((0.28, 0.18, 0.16), (0.19, 0.10, 0.08)),
                     "HP": ((0.23, 0.17, 0.16), (0.14, 0.09, 0.08))},
        "crawl": {"C": ((0.16, 0.12, 0.11), (0.10, 0.06, 0.05)),
                  "F": ((0.49, 0.29, 0.25), (0.34, 0.16, 0.13)),
                  "HP": ((0.56, 0.37, 0.34), (0.34, 0.19, 0.16))},
    },
    2: {
        "attic": {"C": ((1.02, 0.66, 0.60), (0.53, 0.29, 0.25)),
                  "F": ((0.41, 0.26, 0.24), (0.27, 0.14, 0.12)),
                  "HP": ((0.49, 0.35, 0.33), (0.28, 0.17, 0.15))},
        "basement": {"C": ((0.11, 0.09, 0.09), (0.06, 0.04, 0.04)),
                     "F": ((0.24, 0.17, 0.15), (0.16, 0.09, 0.08)),
                     "HP": ((0.20, 0.16, 0.15), (0.12, 0.08, 0.07))},
        "crawl": {"C": ((0.14, 0.12, 0.11), (0.08, 0.06, 0.05)),
                  "F": ((0.41, 0.26, 0.24), (0.27, 0.14, 0.12)),
                  "HP": ((0.49, 0.35, 0.33), (0.28, 0.17, 0.15))},
    },
}
# Air temperatures the table assumes: (room, surroundings).
_DUCT_TABLE_TEMPS = {
    "C": {"attic": (75.0, 120.0), "basement": (75.0, 68.0), "crawl": (75.0, 72.0)},
    "H": {"attic": (68.0, 32.0), "basement": (68.0, 64.0), "crawl": (68.0, 32.0)},
}
_DUCT_FAMILY = {
    "attic": "attic", "garage": "attic", "vented_crawl": "crawl",
    "sealed_crawl": "basement", "basement": "basement",
}


def duct_loss_factor(
    location: str,
    stories: int,
    leakage_pct: float,
    duct_r: float,
    mode: str,
    t_room: float,
    t_around: float,
) -> float:
    """
    Duct loss or gain as a fraction of the building load.

    Interpolates ASHRAE's published factors in duct R-value and leakage, then
    adjusts them from the temperatures the table assumes to the actual ones. The
    adjustment keeps the three physical terms separate. Supply leaks waste air
    that has already been conditioned, whatever surrounds the duct. Return leaks
    pull in air at the surrounding temperature. Conduction follows the difference
    between the supply air and the surroundings.

    ---Parameters---
    location : str
        conditioned, attic, vented_crawl, sealed_crawl, basement, or garage.
    stories : int
        Number of stories. Two and up use the shorter-duct column.
    leakage_pct : float
        Leakage on each of the supply and return sides, percent of fan flow.
    duct_r : float
        Duct insulation R-value.
    mode : str
        C for cooling, F for furnace heating, HP for heat pump heating.
    t_room : float
        Room air temperature (°F).
    t_around : float
        Air temperature around the ducts (°F).

    ---Returns---
    factor : float
        Duct load divided by building load, zero or above.

    ---LaTeX---
    q_d = F_{dl} \\, q_{bl}
    F_{dl} = F_{table}(R, \\ell)\\,\\frac{L(t_{room}, t_{around})}{L(t_{room,table}, t_{around,table})}
    L = \\ell \\Delta T_e + \\ell |t_{room} - t_{around}| + c_d |t_{supply} - t_{around}|, \\quad c_d = \\frac{0.417}{R + 0.7}
    """
    if location == "conditioned":
        return 0.0
    if location not in _DUCT_FAMILY:
        raise ValueError(f"Unknown duct location '{location}'.")
    family = _DUCT_FAMILY[location]
    table = _DUCT_TABLE[1 if stories <= 1 else 2][family][mode]

    def in_r(row: Tuple[float, float, float]) -> float:
        points = [(0.0, row[0]), (4.0, row[1]), (8.0, row[2])]
        value = _interpolate(points, duct_r)
        if duct_r > 8.0:
            # Beyond R-8 only the conduction share keeps falling.
            value = row[2] * (0.75 + 0.25 * 8.0 / duct_r)
        return value

    high, low = in_r(table[0]), in_r(table[1])
    if leakage_pct >= 5.0:
        factor = low + (high - low) * (leakage_pct - 5.0) / 6.0
    else:
        # Below 5% the conduction share remains when leaks go to zero.
        factor = low * (0.45 + 0.55 * leakage_pct / 5.0)
    temps = _DUCT_TABLE_TEMPS["C" if mode == "C" else "H"][family]
    leak = leakage_pct / 100.0
    conduction = 0.417 / (duct_r + 0.7)
    coil_dt = {"C": 20.0, "F": 55.0, "HP": 30.0}[mode]
    direction = -1.0 if mode == "C" else 1.0

    def driving(room: float, around: float) -> float:
        supply = room + direction * coil_dt
        return leak * coil_dt + leak * abs(room - around) + conduction * abs(supply - around)

    return max(factor * driving(t_room, t_around) / driving(temps[0], temps[1]), 0.0)


# =============================================================================
# BUILDING DESCRIPTION
# =============================================================================


def _whole_house_zone(p: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Describe the house as one zone, using a rectangle for the footprint."""
    stories = p["stories"]
    levels = stories + (1 if p["floor_type"] == "basement_conditioned" else 0)
    footprint = p["floor_area_ft2"] / levels
    length = math.sqrt(footprint * p["aspect_ratio"])
    width = footprint / length
    perimeter = 2 * (length + width)
    walls = {"N": length, "S": length, "E": width, "W": width}
    if p["window_area_n"] is not None:
        windows = {
            "N": p["window_area_n"], "E": p["window_area_e"],
            "S": p["window_area_s"], "W": p["window_area_w"],
        }
    else:
        total = p["window_pct_of_floor"] / 100.0 * p["floor_area_ft2"]
        windows = {side: total / 4.0 for side in "NESW"}
    return [{
        "name": "Whole house",
        "type": "whole",
        "area": p["floor_area_ft2"],
        "height": p["ceiling_height_ft"],
        "levels": stories,
        "wall_lengths": walls,
        "windows": windows,
        "door_area": p["door_area_ft2"],
        "ceiling_area": footprint,
        "floor_area_exposed": footprint,
        "perimeter": perimeter,
        "volume": p["floor_area_ft2"] * p["ceiling_height_ft"],
        "gain_weight": 1.0,
        "internal_btuh": None,
    }]


def _room_zones(p: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn the room table into zones, validating as it goes."""
    zones = []
    for index, room in enumerate(p["rooms"]):
        area = float(room.get("area", 0))
        if area <= 0:
            raise ValueError(f"Room {index + 1} needs a floor area above zero.")
        height = float(room.get("height") or p["ceiling_height_ft"])
        walls = {k: max(0.0, float(v or 0)) for k, v in (room.get("walls") or {}).items()}
        windows = {k: max(0.0, float(v or 0)) for k, v in (room.get("windows") or {}).items()}
        for side in list(walls) + list(windows):
            if side not in COMPASS_DEG:
                raise ValueError(f"Unknown compass direction '{side}'.")
        top = bool(room.get("top", True))
        ground = bool(room.get("ground", True))
        room_type = room.get("type", "other")
        internal = room.get("internal_btuh")
        zones.append({
            "name": room.get("name") or f"Room {index + 1}",
            "type": room_type,
            "area": area,
            "height": height,
            "levels": 1,
            "wall_lengths": walls,
            "windows": windows,
            "door_area": max(0.0, float(room.get("door_area", 0) or 0)),
            "ceiling_area": area if top else 0.0,
            "floor_area_exposed": area if ground else 0.0,
            "perimeter": sum(walls.values()) if ground else 0.0,
            "volume": area * height,
            "gain_weight": ZONE_GAIN_WEIGHT.get(room_type, 0.3) * area,
            "internal_btuh": None if internal in (None, "") else float(internal),
        })
    return zones


def _rotated_azimuth(side: str, rotation_deg: float) -> float:
    return COMPASS_DEG[side] + rotation_deg


def _ground_temperature(p: Dict[str, Any]) -> float:
    return p["ground_mean_f"] - p["ground_amp_f"]


def _below_grade_u(depth_ft: float, r_insulation: float) -> float:
    """Average below-grade wall U-factor (ASHRAE Ch. 18, Latta and Boileau)."""
    if depth_ft <= 0:
        return 0.0
    r_total = 0.68 + 0.8 + r_insulation
    term = 2 * SOIL_K * r_total / math.pi
    return (2 * SOIL_K / (math.pi * depth_ft)) * math.log((depth_ft + term) / term)


def _basement_floor_u(width_ft: float, depth_ft: float, r_insulation: float = 0.0) -> float:
    """Average basement floor U-factor (ASHRAE Ch. 18, Equation 38)."""
    term = depth_ft / 2.0 + SOIL_K * (0.68 + r_insulation) / math.pi
    return (2 * SOIL_K / (math.pi * width_ft)) * math.log((width_ft / 2.0 + term) / term)


def _buffer_temperature(ua_house: float, t_house: float, paths: Iterable[Tuple[float, float]]) -> float:
    """Steady buffer-space temperature from a heat balance (ASHRAE Ch. 17, Eq. 5)."""
    numerator = ua_house * t_house
    denominator = ua_house
    for ua, temperature in paths:
        numerator += ua * temperature
        denominator += ua
    return numerator / denominator if denominator > 0 else t_house


# =============================================================================
# HEATING
# =============================================================================


def _floor_heat_loss(zone: Dict[str, Any], p: Dict[str, Any], t_out: float, c_s: float) -> float:
    """Design heat loss through the floor of one zone, Btu/h."""
    t_in = p["indoor_heating_f"]
    area = zone["floor_area_exposed"]
    if area <= 0:
        return 0.0
    kind = p["floor_type"]
    ground = _ground_temperature(p)
    if kind == "slab":
        return SLAB_EDGE_F[p["slab_edge"]] * zone["perimeter"] * (t_in - t_out)
    if kind in ("crawl_vented", "over_ambient"):
        return p["floor_u"] * area * (t_in - t_out)
    if kind == "over_garage":
        return p["floor_u"] * area * (t_in - (t_out + 10.0))
    side = math.sqrt(max(area, 1.0))
    if kind == "crawl_sealed":
        wall_area = zone["perimeter"] * 3.0
        t_b = _buffer_temperature(p["floor_u"] * area, t_in, [
            (wall_area * 1.0 / (p["crawl_wall_r"] + 1.5), t_out),
            (area * 0.04, ground),
            (c_s * 0.02 * area, t_out),
        ])
        return p["floor_u"] * area * (t_in - t_b)
    if kind == "basement_unconditioned":
        depth = p["basement_depth_ft"]
        u_wall = _below_grade_u(depth, p["basement_wall_r"])
        t_b = _buffer_temperature(p["floor_u"] * area, t_in, [
            (u_wall * zone["perimeter"] * depth, ground),
            (_basement_floor_u(side, depth) * area, ground),
            (zone["perimeter"] * max(8.0 - depth, 0.0) * 0.35, t_out),
            (c_s * 0.67 * area * 8.0 / 60.0, t_out),
        ])
        return p["floor_u"] * area * (t_in - t_b)
    if kind == "basement_conditioned":
        depth = p["basement_depth_ft"]
        u_wall = _below_grade_u(depth, p["basement_wall_r"])
        below_wall = u_wall * zone["perimeter"] * depth * (t_in - ground)
        above_wall = zone["perimeter"] * max(8.0 - depth, 0.0) * p["wall_u"] * (t_in - t_out)
        slab = _basement_floor_u(side, depth) * area * (t_in - ground)
        return below_wall + above_wall + slab
    raise ValueError(f"Unknown floor type '{kind}'.")


def _air_flows(p: Dict[str, Any], volume: float, heating: bool) -> Dict[str, float]:
    """Infiltration plus ventilation flows, cfm (ASHRAE Ch. 17, Eqs. 8 to 14)."""
    delta_t = (
        p["indoor_heating_f"] - p["heating_design_f"]
        if heating else p["cooling_design_f"] - p["indoor_cooling_f"]
    )
    area_leak = leakage_area_in2(p["ach50"], volume)
    area_floor = p["floor_area_ft2"]
    stack = volume / area_floor if area_floor > 0 else p["ceiling_height_ft"]
    stack = max(stack * p["stories"], p["ceiling_height_ft"])
    idf = infiltration_driving_force(stack, delta_t, heating, p["flue_fraction"])
    infiltration = area_leak * idf

    kind = p["ventilation_type"]
    flow = p["ventilation_cfm"] if kind != "none" else 0.0
    balanced = flow if kind in ("balanced", "hrv", "erv") else 0.0
    unbalanced = flow if kind in ("exhaust", "supply") else 0.0
    combined = max(unbalanced, infiltration + 0.5 * unbalanced)
    return {
        "leak_area_in2": area_leak,
        "idf": idf,
        "stack_height": stack,
        "infiltration_natural": infiltration,
        "combined": combined,
        "balanced": balanced,
    }


def _heating_side(zones: List[Dict[str, Any]], p: Dict[str, Any], c_s: float) -> Dict[str, Any]:
    """Whole-house and per-zone design heat loss, Btu/h."""
    t_in = p["indoor_heating_f"]
    t_out = p["heating_design_f"]
    delta_t = t_in - t_out
    volume = sum(z["volume"] for z in zones)
    air = _air_flows(p, volume, heating=True)
    recovery = p["ventilation_effectiveness"] if p["ventilation_type"] in ("hrv", "erv") else 0.0

    per_zone = []
    totals = {key: 0.0 for key in (
        "walls", "windows", "doors", "ceiling", "floor", "infiltration", "ventilation")}
    for zone in zones:
        window_area = sum(zone["windows"].values())
        gross_wall = sum(zone["wall_lengths"].values()) * zone["height"] * zone["levels"]
        net_wall = max(gross_wall - window_area - zone["door_area"], 0.0)
        share = zone["volume"] / volume
        line = {
            "walls": p["wall_u"] * net_wall * delta_t,
            "windows": p["window_u"] * window_area * delta_t,
            "doors": p["door_u"] * zone["door_area"] * delta_t,
            "ceiling": p["ceiling_u"] * zone["ceiling_area"] * delta_t,
            "floor": _floor_heat_loss(zone, p, t_out, c_s),
            "infiltration": c_s * air["combined"] * delta_t * share,
            "ventilation": c_s * air["balanced"] * (1 - recovery) * delta_t * share,
        }
        for key, value in line.items():
            totals[key] += value
        per_zone.append(line)

    envelope = sum(totals.values())
    t_around = _duct_ambient(p, heating=True, t_out=t_out, t_attic=t_out, t_in=t_in)
    factor = duct_loss_factor(
        p["duct_location"], p["stories"], p["duct_leakage_pct"], p["duct_r"],
        "HP" if p["heating_system"] == "heat_pump" else "F", t_in, t_around,
    )
    eta = 1.0 / (1.0 + factor)
    duct_load = envelope * factor
    totals["ducts"] = duct_load
    coil_dt = 30.0 if p["heating_system"] == "heat_pump" else 55.0
    fan_cfm = (envelope + duct_load) / (c_s * coil_dt)

    for line in per_zone:
        zone_load = sum(line.values())
        line["ducts"] = zone_load * factor
        line["total"] = zone_load + line["ducts"]

    ua_total = (envelope + duct_load) / delta_t if delta_t > 0 else 0.0
    return {
        "total": envelope + duct_load,
        "components": totals,
        "delta_t": delta_t,
        "ua": ua_total,
        "duct_efficiency": eta,
        "air": air,
        "per_zone": per_zone,
        "fan_cfm": fan_cfm,
    }


def _duct_ambient(p: Dict[str, Any], heating: bool, t_out: float, t_attic: float, t_in: float) -> float:
    """Air temperature around the ducts for the chosen duct location."""
    location = p["duct_location"]
    if location == "conditioned":
        return t_in
    if location == "attic":
        return t_attic
    if location == "vented_crawl":
        return t_out if heating else t_in + 0.33 * (t_out - t_in)
    if location == "sealed_crawl":
        return t_in - 8.0 if heating else t_in - 3.0
    if location == "basement":
        return t_in - 6.0 if heating else t_in - 7.0
    if location == "garage":
        return t_out + 10.0 if heating else t_out + 5.0
    raise ValueError(f"Unknown duct location '{location}'.")


# =============================================================================
# COOLING
# =============================================================================


def outdoor_temperatures(design_f: float, daily_range_f: float) -> List[float]:
    """Hourly outdoor dry bulb on the design day, °F."""
    return [design_f - fraction * daily_range_f for fraction in DAILY_RANGE_FRACTION]


def _attic_series(p: Dict[str, Any], t_out: Sequence[float], c_s: float) -> List[float]:
    """Hourly attic air temperature from a heat balance on the attic node."""
    pitch = math.degrees(math.atan(p["roof_pitch"] / 12.0))
    roof_ratio = 1.0 / math.cos(math.radians(pitch))
    absorptance = ROOF_ABSORPTANCE[p["roof_color"]]
    inner = 0.55 if p["radiant_barrier"] else 1.15
    u_roof = roof_ratio / (1.0 / H_OUT_ROOF + 0.9 + 1.0 / inner)
    u_vent = c_s * p["attic_vent_cfm_per_ft2"]
    u_ceiling = p["ceiling_u"]
    t_in = p["indoor_cooling_f"]
    series = []
    for hour, t_o in zip(HOURS, t_out):
        irradiance = 0.0
        for azimuth in (0.0, 90.0, 180.0, -90.0):
            sun = surface_irradiance(p["latitude"], p["design_month"], hour - 0.5, azimuth, pitch)
            irradiance += (sun["direct"] + sun["diffuse"]) / 4.0
        t_solair = t_o + absorptance * irradiance / H_OUT_ROOF - 7.0 * math.cos(math.radians(pitch)) / (H_OUT_ROOF / 4.0)
        series.append(
            (u_roof * t_solair + u_vent * t_o + u_ceiling * t_in)
            / (u_roof + u_vent + u_ceiling)
        )
    # Sheathing and framing store heat, so attic air lags the sun by about an hour.
    return low_pass(series, 1.0)


def _crawl_cooling_excess(p: Dict[str, Any]) -> float:
    """Effective temperature above indoor for a floor over a crawlspace.

    ASHRAE Ch. 17, Table 7: floor over crawlspace behaves as 0.33 dt - 0.28 DR.
    """
    delta_t = p["cooling_design_f"] - p["indoor_cooling_f"]
    return 0.33 * delta_t - 0.28 * p["daily_range_f"]


def _zone_gain_series(
    zone: Dict[str, Any],
    p: Dict[str, Any],
    t_out: Sequence[float],
    t_attic: Sequence[float],
    wall_y: Sequence[complex],
    door_y: Sequence[complex],
    ceiling_y: Sequence[complex],
    rotation: float,
) -> Dict[str, List[float]]:
    """Hourly sensible heat gains of a zone before any storage, Btu/h."""
    t_in = p["indoor_cooling_f"]
    wall_alpha = p["wall_absorptance"]
    month = p["design_month"]
    lat = p["latitude"]

    walls = [0.0] * 24
    doors = [0.0] * 24
    win_cond = [0.0] * 24
    win_solar = [0.0] * 24

    window_total = sum(zone["windows"].values())
    window_areas = dict(zone["windows"])
    gross_by_side = {
        side: length * zone["height"] * zone["levels"]
        for side, length in zone["wall_lengths"].items()
    }
    gross_wall = sum(gross_by_side.values())

    # Doors are spread over the walls in proportion to their area.
    for side, gross in gross_by_side.items():
        azimuth = _rotated_azimuth(side, rotation)
        door_share = zone["door_area"] * gross / gross_wall if gross_wall > 0 else 0.0
        net = max(gross - window_areas.get(side, 0.0) - door_share, 0.0)
        solair_excess = []
        for hour, t_o in zip(HOURS, t_out):
            sun = surface_irradiance(lat, month, hour - 0.5, azimuth)
            incident = sun["direct"] + sun["diffuse"]
            solair_excess.append(t_o + wall_alpha * incident / H_OUT_WALL - t_in)
        for i, value in enumerate(periodic_flux(solair_excess, wall_y)):
            walls[i] += value * net
        for i, value in enumerate(periodic_flux(solair_excess, door_y)):
            doors[i] += value * door_share

    tx = SCREEN_TX[p["insect_screen"]]
    iac = INTERIOR_SHADE_IAC[p["interior_shade"]]
    open_fraction = 1.0 - p["site_shade_fraction"]
    for side, area in window_areas.items():
        if area <= 0:
            continue
        azimuth = _rotated_azimuth(side, rotation)
        for i, hour in enumerate(HOURS):
            sun = surface_irradiance(lat, month, hour - 0.5, azimuth)
            shaded = _overhang_shaded_fraction(
                sun, p["overhang_depth_ft"], p["overhang_gap_ft"], p["window_height_ft"]
            )
            direct = sun["direct"] * (1 - shaded) * open_fraction
            theta = math.degrees(math.acos(min(1.0, sun["cos_incidence"])))
            ratio = _interpolate(SHGC_ANGLE, theta)
            transmitted = tx * iac * p["window_shgc"] * (
                direct * ratio + sun["diffuse"] * SHGC_DIFFUSE_RATIO
            )
            win_solar[i] += area * transmitted
            win_cond[i] += area * p["window_u"] * (t_out[i] - t_in)

    ceiling = [0.0] * 24
    if zone["ceiling_area"] > 0:
        if p["ceiling_type"] == "attic":
            excess = [t - t_in for t in t_attic]
        else:
            pitch = math.degrees(math.atan(p["roof_pitch"] / 12.0))
            absorptance = ROOF_ABSORPTANCE[p["roof_color"]]
            excess = []
            for hour, t_o in zip(HOURS, t_out):
                irradiance = sum(
                    surface_irradiance(lat, month, hour - 0.5, azimuth, pitch)["direct"]
                    + surface_irradiance(lat, month, hour - 0.5, azimuth, pitch)["diffuse"]
                    for azimuth in (0.0, 90.0, 180.0, -90.0)
                ) / 4.0
                excess.append(t_o + absorptance * irradiance / H_OUT_ROOF - 7.0 - t_in)
        flux = periodic_flux(excess, ceiling_y)
        ceiling = [value * zone["ceiling_area"] for value in flux]

    floor_kind = p["floor_type"]
    floor_area = zone["floor_area_exposed"]
    floor = [0.0] * 24
    if floor_area > 0:
        if floor_kind in ("slab", "basement_conditioned"):
            cover_r = {"carpet": 1.2, "hard": 0.1}[p["floor_cover"]]
            # ASHRAE Ch. 17, Eq. 23: a slab is a small steady heat sink.
            floor = [(0.59 - 2.5 / (cover_r + 0.68)) * floor_area] * 24
        elif floor_kind == "crawl_vented":
            floor = [p["floor_u"] * floor_area * _crawl_cooling_excess(p)] * 24
        elif floor_kind == "over_ambient":
            floor = [p["floor_u"] * floor_area * (t - t_in) for t in t_out]
        elif floor_kind == "over_garage":
            floor = [p["floor_u"] * floor_area * (t + 5.0 - t_in) for t in t_out]

    return {
        "walls": walls, "doors": doors, "window_conduction": win_cond,
        "window_solar": win_solar, "ceiling": ceiling, "floor": floor,
    }


def _capacity_for_swing(
    convective: Sequence[float],
    radiant: Sequence[float],
    capacitance: float,
    conductance: float,
    ua: float,
    swing_f: float,
) -> float:
    """Smallest steady capacity that keeps the room within the allowed swing.

    Marches a two-node room (air, thermal mass) to a periodic state with a
    thermostat that cools up to a capacity limit, then bisects on the limit.

    ---LaTeX---
    C_m \\frac{d\\theta_m}{dt} = G_{rad} - H(\\theta_m - \\theta_a)
    0 = G_{conv} + H(\\theta_m - \\theta_a) - UA\\,\\theta_a - Q
    """
    substeps = 4
    dt = 1.0 / substeps
    if capacitance <= 0 or conductance <= 0:
        return max(c + r for c, r in zip(convective, radiant))

    def simulate(capacity: float) -> float:
        theta_m = 0.0
        peak_air = 0.0
        for _day in range(4):
            peak_air = -1e9
            for hour in range(24):
                conv_now, conv_next = convective[hour], convective[(hour + 1) % 24]
                rad_now, rad_next = radiant[hour], radiant[(hour + 1) % 24]
                for step in range(substeps):
                    weight = step / substeps
                    g_conv = conv_now + weight * (conv_next - conv_now)
                    g_rad = rad_now + weight * (rad_next - rad_now)
                    demand = g_conv + conductance * theta_m
                    if demand <= 0:
                        theta_a = demand / (conductance + ua)
                    elif demand <= capacity:
                        theta_a = 0.0
                    else:
                        theta_a = (demand - capacity) / (conductance + ua)
                    theta_m += dt * (g_rad - conductance * (theta_m - theta_a)) / capacitance
                    peak_air = max(peak_air, theta_a)
        return peak_air

    low = 0.0
    high = max(max(convective) + max(radiant), 1.0)
    # The upper bound always holds the room at its setpoint.
    for _ in range(18):
        middle = 0.5 * (low + high)
        if simulate(middle) > swing_f:
            low = middle
        else:
            high = middle
    return high


def _cooling_side(
    zones: List[Dict[str, Any]],
    p: Dict[str, Any],
    c_s: float,
    c_l: float,
    rotation: float,
) -> Dict[str, Any]:
    """Hourly design-day cooling load, sensible and latent."""
    t_in = p["indoor_cooling_f"]
    t_out = outdoor_temperatures(p["cooling_design_f"], p["daily_range_f"])
    pressure = pressure_psia(p["elevation_ft"])
    w_out = humidity_ratio_from_wet_bulb(
        p["cooling_design_f"], p["cooling_wet_bulb_f"], pressure)
    w_in = humidity_ratio_from_rh(t_in, p["indoor_rh_pct"], pressure)
    delta_w = max(w_out - w_in, 0.0)

    t_attic = _attic_series(p, t_out, c_s)
    wall_layers = WALL_LAYERS[p["wall_layers"]]
    wall_y = transfer_admittances(wall_layers, p["wall_u"], 1.0 / H_OUT_WALL)
    door_y = [complex(p["door_u"])] * (N_HARMONICS + 1)
    if p["ceiling_type"] == "attic":
        ceiling_y = transfer_admittances(CEILING_LAYERS, p["ceiling_u"], 0.30)
    else:
        ceiling_y = transfer_admittances(ROOF_LAYERS, p["ceiling_u"], 1.0 / H_OUT_ROOF)

    volume = sum(z["volume"] for z in zones)
    air = _air_flows(p, volume, heating=False)
    recovery_s = p["ventilation_effectiveness"] if p["ventilation_type"] in ("hrv", "erv") else 0.0
    recovery_l = (
        p["ventilation_latent_effectiveness"] if p["ventilation_type"] == "erv" else 0.0
    )

    area = p["floor_area_ft2"]
    occupants = p["occupants"]
    q_ig_s = p["internal_sensible_btuh"]
    if q_ig_s is None:
        q_ig_s = 464.0 + 0.7 * area + 75.0 * occupants
    q_ig_l = p["internal_latent_btuh"]
    if q_ig_l is None:
        q_ig_l = 68.0 + 0.07 * area + 41.0 * occupants

    weights = sum(z["gain_weight"] for z in zones)
    unassigned = q_ig_s - sum(z["internal_btuh"] or 0.0 for z in zones)
    mass = THERMAL_MASS[p["construction_mass"]]
    tau = mass["capacity"] / mass["conductance"]

    keys = ("walls", "doors", "window_conduction", "window_solar", "ceiling",
            "floor", "infiltration", "ventilation", "internal")
    totals = {key: [0.0] * 24 for key in keys}
    zone_results = []
    ua_house = 0.0

    for zone in zones:
        series = _zone_gain_series(
            zone, p, t_out, t_attic, wall_y, door_y, ceiling_y, rotation)
        share = zone["volume"] / volume
        series["infiltration"] = [c_s * air["combined"] * (t - t_in) * share for t in t_out]
        series["ventilation"] = [
            c_s * air["balanced"] * (1 - recovery_s) * (t - t_in) * share for t in t_out
        ]
        if zone["internal_btuh"] is not None:
            internal = zone["internal_btuh"]
        else:
            free_weight = sum(
                z["gain_weight"] for z in zones if z["internal_btuh"] is None) or weights
            internal = max(unassigned, 0.0) * zone["gain_weight"] / free_weight
        series["internal"] = [internal] * 24

        convective = [0.0] * 24
        radiant = [0.0] * 24
        for key in keys:
            fraction = RADIANT_FRACTION[key]
            for i, value in enumerate(series[key]):
                totals[key][i] += value
                convective[i] += value * (1 - fraction)
                radiant[i] += value * fraction
        delayed = low_pass(radiant, tau)
        load = [c + r for c, r in zip(convective, delayed)]
        peak_index = max(range(24), key=lambda i: load[i])
        zone_results.append({
            "load": load,
            "peak": max(load[peak_index], 0.0),
            "peak_hour": HOURS[peak_index],
            "series": series,
        })
        gross_wall = sum(zone["wall_lengths"].values()) * zone["height"] * zone["levels"]
        window_area = sum(zone["windows"].values())
        ua_house += (
            p["wall_u"] * max(gross_wall - window_area - zone["door_area"], 0.0)
            + p["window_u"] * window_area
            + p["door_u"] * zone["door_area"]
            + p["ceiling_u"] * zone["ceiling_area"]
        )
    ua_house += c_s * (air["combined"] + air["balanced"] * (1 - recovery_s))

    convective_total = [0.0] * 24
    radiant_total = [0.0] * 24
    for key in keys:
        fraction = RADIANT_FRACTION[key]
        for i, value in enumerate(totals[key]):
            convective_total[i] += value * (1 - fraction)
            radiant_total[i] += value * fraction
    delayed_total = low_pass(radiant_total, tau)
    fixed_load = [c + r for c, r in zip(convective_total, delayed_total)]
    fixed_peak = max(fixed_load)
    peak_index = fixed_load.index(fixed_peak)

    capacitance = mass["capacity"] * area
    conductance = mass["conductance"] * area
    swing = p["temperature_swing_f"]
    if swing > 0:
        room_load = _capacity_for_swing(
            convective_total, radiant_total, capacitance, conductance, ua_house, swing)
        room_load = min(room_load, fixed_peak)
    else:
        room_load = fixed_peak

    # Component breakdown at the peak hour, scaled so the parts add to the
    # swing-adjusted load the equipment must meet.
    delayed_by_key = {}
    for key in keys:
        fraction = RADIANT_FRACTION[key]
        rad = low_pass([v * fraction for v in totals[key]], tau)
        delayed_by_key[key] = [
            v * (1 - fraction) + r for v, r in zip(totals[key], rad)
        ]
    swing_ratio = room_load / fixed_peak if fixed_peak > 0 else 1.0
    components = {
        "walls": delayed_by_key["walls"][peak_index] * swing_ratio,
        "windows": (delayed_by_key["window_conduction"][peak_index]
                    + delayed_by_key["window_solar"][peak_index]) * swing_ratio,
        "doors": delayed_by_key["doors"][peak_index] * swing_ratio,
        "ceiling": delayed_by_key["ceiling"][peak_index] * swing_ratio,
        "floor": delayed_by_key["floor"][peak_index] * swing_ratio,
        "infiltration": delayed_by_key["infiltration"][peak_index] * swing_ratio,
        "ventilation": delayed_by_key["ventilation"][peak_index] * swing_ratio,
        "internal": delayed_by_key["internal"][peak_index] * swing_ratio,
    }

    # Duct gains at the hour of the peak.
    coil_dt = p["cooling_coil_dt_f"]
    leak = p["duct_leakage_pct"] / 100.0
    t_amb = _duct_ambient(p, False, t_out[peak_index], t_attic[peak_index], t_in)
    factor = duct_loss_factor(
        p["duct_location"], p["stories"], p["duct_leakage_pct"], p["duct_r"], "C", t_in, t_amb,
    )
    eta = 1.0 / (1.0 + factor)
    duct_sensible = room_load * factor
    fan_cfm = (room_load + duct_sensible) / (c_s * coil_dt)
    components["ducts"] = duct_sensible

    w_amb = w_out if p["duct_location"] in ("attic", "garage", "vented_crawl") else w_in
    latent_infiltration = c_l * air["combined"] * delta_w
    latent_ventilation = c_l * air["balanced"] * (1 - recovery_l) * delta_w
    latent_duct = c_l * fan_cfm * leak * max(w_amb - w_in, 0.0)
    latent = latent_infiltration + latent_ventilation + q_ig_l + latent_duct
    sensible = room_load + duct_sensible
    total = sensible + latent

    # Hourly profile for the chart, on the fixed-setpoint basis.
    hourly_keys = {
        "walls": delayed_by_key["walls"],
        "windows": [a + b for a, b in zip(
            delayed_by_key["window_conduction"], delayed_by_key["window_solar"])],
        "ceiling": delayed_by_key["ceiling"],
        "floor": [a + b for a, b in zip(delayed_by_key["floor"], delayed_by_key["doors"])],
        "air": [a + b for a, b in zip(
            delayed_by_key["infiltration"], delayed_by_key["ventilation"])],
        "internal": delayed_by_key["internal"],
    }

    total_room_peaks = sum(z["peak"] for z in zone_results)
    return {
        "room_load": room_load,
        "fixed_setpoint_peak": fixed_peak,
        "swing_ratio": swing_ratio,
        "peak_hour": HOURS[peak_index],
        "sensible": sensible,
        "latent": latent,
        "total": total,
        "shr": sensible / total if total > 0 else 1.0,
        "components": components,
        "latent_components": {
            "infiltration": latent_infiltration,
            "ventilation": latent_ventilation,
            "internal": q_ig_l,
            "ducts": latent_duct,
        },
        "duct_efficiency": eta,
        "fan_cfm": fan_cfm,
        "air": air,
        "delta_w": delta_w,
        "w_out": w_out,
        "w_in": w_in,
        "t_out": t_out,
        "t_attic": t_attic,
        "attic_at_peak": t_attic[peak_index],
        "hourly": hourly_keys,
        "hourly_fixed": fixed_load,
        "zones": zone_results,
        "sum_room_peaks": total_room_peaks,
        "q_internal_sensible": q_ig_s,
        "ua_house": ua_house,
    }


# =============================================================================
# INPUT HANDLING
# =============================================================================

DEFAULTS: Dict[str, Any] = {
    "floor_area_ft2": 2000.0,
    "stories": 1,
    "ceiling_height_ft": 8.0,
    "aspect_ratio": 1.5,
    "bedrooms": 3,
    "occupants": None,
    "latitude": 40.0,
    "elevation_ft": 500.0,
    "heating_design_f": 10.0,
    "cooling_design_f": 90.0,
    "cooling_wet_bulb_f": 74.0,
    "daily_range_f": 18.0,
    "ground_mean_f": 52.0,
    "ground_amp_f": 22.0,
    "design_month": 7,
    "indoor_heating_f": 70.0,
    "indoor_cooling_f": 75.0,
    "indoor_rh_pct": 50.0,
    "temperature_swing_f": 3.0,
    "construction_mass": "light",
    "wall_u": 0.090,
    "wall_layers": "frame",
    "wall_absorptance": 0.60,
    "ceiling_u": 0.032,
    "ceiling_type": "attic",
    "roof_color": "medium",
    "roof_pitch": 6.0,
    "radiant_barrier": False,
    "attic_vent_cfm_per_ft2": 0.30,
    "floor_type": "slab",
    "floor_u": 0.05,
    "floor_cover": "carpet",
    "slab_edge": "none",
    "crawl_wall_r": 10.0,
    "basement_depth_ft": 7.0,
    "basement_wall_r": 0.0,
    "window_u": 0.51,
    "window_shgc": 0.57,
    "window_pct_of_floor": 14.0,
    "window_area_n": None,
    "window_area_e": None,
    "window_area_s": None,
    "window_area_w": None,
    "window_height_ft": 5.0,
    "interior_shade": "drapes_half",
    "insect_screen": "half",
    "overhang_depth_ft": 1.0,
    "overhang_gap_ft": 1.0,
    "site_shade_fraction": 0.0,
    "door_area_ft2": 40.0,
    "door_u": 0.40,
    "ach50": 7.0,
    "flue_fraction": 0.0,
    "ventilation_type": "none",
    "ventilation_cfm": 0.0,
    "ventilation_effectiveness": 0.70,
    "ventilation_latent_effectiveness": 0.50,
    "duct_location": "attic",
    "duct_r": 6.0,
    "duct_leakage_pct": 10.0,
    "heating_system": "furnace",
    "cooling_coil_dt_f": 20.0,
    "rotation_deg": 0.0,
    "internal_sensible_btuh": None,
    "internal_latent_btuh": None,
    "rooms": None,
}

UNSIGNED_POSITIVE = (
    "floor_area_ft2", "ceiling_height_ft", "aspect_ratio", "wall_u", "ceiling_u",
    "window_u", "door_u", "window_height_ft", "cooling_coil_dt_f",
)
NON_NEGATIVE = (
    "ach50", "duct_r", "duct_leakage_pct", "door_area_ft2", "window_pct_of_floor",
    "overhang_depth_ft", "overhang_gap_ft", "ventilation_cfm", "temperature_swing_f",
    "attic_vent_cfm_per_ft2", "floor_u", "basement_wall_r", "crawl_wall_r",
)


def _normalize(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Merge inputs with defaults, coerce numbers, and validate ranges."""
    unknown = set(inputs) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown inputs: {sorted(unknown)}")
    p = dict(DEFAULTS)
    p.update({key: value for key, value in inputs.items() if value is not None})
    for key in UNSIGNED_POSITIVE:
        p[key] = float(p[key])
        if p[key] <= 0 or not math.isfinite(p[key]):
            raise ValueError(f"{key} must be greater than zero.")
    for key in NON_NEGATIVE:
        p[key] = float(p[key])
        if p[key] < 0 or not math.isfinite(p[key]):
            raise ValueError(f"{key} cannot be negative.")
    for key in ("window_shgc", "site_shade_fraction", "wall_absorptance", "flue_fraction"):
        p[key] = float(p[key])
        if not 0 <= p[key] <= 1:
            raise ValueError(f"{key} must be between 0 and 1.")
    for key in ("latitude", "elevation_ft", "heating_design_f", "cooling_design_f",
                "cooling_wet_bulb_f", "daily_range_f", "ground_mean_f", "ground_amp_f",
                "indoor_heating_f", "indoor_cooling_f", "indoor_rh_pct", "rotation_deg"):
        p[key] = float(p[key])
    if not -66 <= p["latitude"] <= 66:
        raise ValueError("Latitude must be between -66 and 66 degrees.")
    if p["elevation_ft"] > 14000:
        raise ValueError("Elevation above 14,000 ft is outside this method's range.")
    if p["heating_design_f"] >= p["indoor_heating_f"]:
        raise ValueError("The heating design temperature must be below the indoor temperature.")
    if p["cooling_wet_bulb_f"] > p["cooling_design_f"]:
        raise ValueError("The wet bulb cannot be above the dry bulb.")
    if not 20 <= p["indoor_rh_pct"] <= 80:
        raise ValueError("Indoor humidity must be between 20% and 80%.")
    if p["duct_leakage_pct"] >= 50:
        raise ValueError("Duct leakage must be below 50% of fan flow on each side.")
    p["stories"] = int(p["stories"])
    if not 1 <= p["stories"] <= 4:
        raise ValueError("This method covers one to four stories.")
    p["bedrooms"] = max(int(p["bedrooms"]), 1)
    p["design_month"] = int(p["design_month"])
    if p["occupants"] is None:
        p["occupants"] = p["bedrooms"] + 1
    p["occupants"] = float(p["occupants"])
    if p["occupants"] < 0:
        raise ValueError("Occupants cannot be negative.")
    choices = {
        "construction_mass": THERMAL_MASS, "wall_layers": WALL_LAYERS,
        "roof_color": ROOF_ABSORPTANCE, "slab_edge": SLAB_EDGE_F,
        "interior_shade": INTERIOR_SHADE_IAC, "insect_screen": SCREEN_TX,
    }
    for key, allowed in choices.items():
        if p[key] not in allowed:
            raise ValueError(f"Unknown {key} '{p[key]}'.")
    if p["duct_location"] not in DUCT_LOCATIONS:
        raise ValueError(f"Unknown duct location '{p['duct_location']}'.")
    if p["ceiling_type"] not in ("attic", "cathedral"):
        raise ValueError(f"Unknown ceiling type '{p['ceiling_type']}'.")
    if p["floor_cover"] not in ("carpet", "hard"):
        raise ValueError(f"Unknown floor cover '{p['floor_cover']}'.")
    if p["ventilation_type"] not in ("none", "balanced", "hrv", "erv", "exhaust", "supply"):
        raise ValueError(f"Unknown ventilation type '{p['ventilation_type']}'.")
    if p["heating_system"] not in ("furnace", "heat_pump"):
        raise ValueError(f"Unknown heating system '{p['heating_system']}'.")
    if p["design_month"] not in CLEAR_SKY:
        raise ValueError("Design month must be 1 to 12.")
    return p


def _run(p: Dict[str, Any], rotation_extra: float = 0.0) -> Dict[str, Any]:
    """Compute heating and cooling for a normalized input set."""
    c_s, c_l = air_factors(p["elevation_ft"])
    zones = _room_zones(p) if p.get("rooms") else _whole_house_zone(p)
    if p.get("rooms"):
        p = dict(p)
        p["floor_area_ft2"] = sum(z["area"] for z in zones)
    heating = _heating_side(zones, p, c_s)
    cooling = _cooling_side(zones, p, c_s, c_l, p["rotation_deg"] + rotation_extra)
    return {"zones": zones, "heating": heating, "cooling": cooling, "params": p}


# =============================================================================
# SIZE SUGGESTION AND DERIVATIONS
# =============================================================================

NOMINAL_TONS = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0)
FURNACE_OUTPUTS = (20000, 30000, 40000, 50000, 60000, 70000, 80000, 100000, 120000)


def rated_to_design_factor(cooling_design_f: float) -> float:
    """Generic ratio of capacity at 75 °F / 63 °F wet bulb to the rated capacity.

    A rated 1-ton unit is tested at 95 °F outdoors and 80/67 °F indoors. Drier
    return air and a different outdoor temperature both move the real capacity.
    """
    return (1 - 0.007 * (cooling_design_f - 95.0)) * (1 - 0.0135 * 4.0)


def effective_sensible_capacity(sensible: float, latent: float, latent_load: float) -> float:
    """Sensible capacity plus half of the latent capacity the house does not need."""
    return sensible + 0.5 * max(latent - latent_load, 0.0)


def suggest_sizes(
    heating_load: float,
    cooling_total: float,
    cooling_design_f: float,
    cooling_sensible: Optional[float] = None,
    equipment_shr: float = 0.75,
) -> Dict[str, Any]:
    """
    Smallest common equipment sizes that meet the design loads.

    A cooling size must reach ACCA's 90% lower limit on the total load and on
    the sensible load. Half of any latent capacity beyond the moisture load counts
    toward sensible, as in the Manual S worksheet: a coil with little moisture to
    remove runs drier and delivers more sensible cooling. The smallest size offered
    is 1.5 tons, the usual floor for ducted central equipment.

    ---Parameters---
    heating_load : float
        Design heat loss (Btu/h).
    cooling_total : float
        Total cooling load (Btu/h).
    cooling_design_f : float
        Cooling design temperature (°F).
    cooling_sensible : float
        Sensible cooling load. Blank checks total capacity only (Btu/h).
    equipment_shr : float
        Generic equipment sensible heat ratio at 75 °F, 63 °F wet bulb.

    ---Returns---
    cooling_tons : float
        Suggested nominal size, or None above the largest common unit.
    cooling_pct : float
        Capacity at design as a percent of the total load (%).
    cooling_sensible_pct : float
        Sensible capacity at design as a percent of the sensible load (%).
    furnace_output : float
        Smallest common furnace output that meets the heat loss (Btu/h).

    ---LaTeX---
    Q_{design} = Q_{rated}[1 - 0.007(T_d - 95)][1 - 0.0135 \\times 4]
    Q_s = SHR\\,Q_{design} + 0.5\\max(Q_l - q_l, 0)
    Q_{design} \\ge 0.9\\,q_t, \\quad Q_s \\ge 0.9\\,q_s
    """
    factor = rated_to_design_factor(cooling_design_f)
    latent = cooling_total - cooling_sensible if cooling_sensible is not None else 0.0

    def usable_sensible(capacity: float) -> float:
        return effective_sensible_capacity(
            capacity * equipment_shr, capacity * (1 - equipment_shr), latent)

    def fits(tons: float) -> bool:
        capacity = tons * TON_BTUH * factor
        if capacity < 0.9 * cooling_total:
            return False
        return cooling_sensible is None or usable_sensible(capacity) >= 0.9 * cooling_sensible

    tons = next((t for t in NOMINAL_TONS if t >= 1.5 and fits(t)), None)
    furnace = next((f for f in FURNACE_OUTPUTS if f >= heating_load), None)
    capacity = tons * TON_BTUH * factor if tons else None
    return {
        "cooling_tons": tons,
        "cooling_capacity_at_design": capacity,
        "cooling_pct": 100.0 * capacity / cooling_total if capacity and cooling_total > 0 else None,
        "cooling_sensible_pct": (
            100.0 * usable_sensible(capacity) / cooling_sensible
            if capacity and cooling_sensible else None
        ),
        "furnace_output": furnace,
        "furnace_pct": 100.0 * furnace / heating_load if furnace and heating_load > 0 else None,
        "derate_factor": factor,
    }


def _tex_number(value: float, digits: int = 0) -> str:
    return f"{value:,.{digits}f}".replace(",", "{,}")


def _derivations(run: Dict[str, Any]) -> Dict[str, Any]:
    """Equations with the actual numbers, for every line of the results."""
    p = run["params"]
    zones = run["zones"]
    heating = run["heating"]
    cooling = run["cooling"]
    c_s, c_l = air_factors(p["elevation_ft"])
    dt = heating["delta_t"]
    n = _tex_number

    windows = sum(sum(z["windows"].values()) for z in zones)
    doors = sum(z["door_area"] for z in zones)
    gross = sum(sum(z["wall_lengths"].values()) * z["height"] * z["levels"] for z in zones)
    net = max(gross - windows - doors, 0.0)
    ceiling = sum(z["ceiling_area"] for z in zones)
    perimeter = sum(z["perimeter"] for z in zones)
    heat = heating["components"]
    cool = cooling["components"]
    air_h = heating["air"]
    air_c = cooling["air"]
    factor_h = heat["ducts"] / max(heating["total"] - heat["ducts"], 1.0)
    factor_c = cool["ducts"] / max(cooling["room_load"], 1.0)
    peak = cooling["peak_hour"]
    t_peak = cooling["t_out"][peak - 1]
    legend_ua = "U: heat flow per ft² per °F. A: area. Δt: indoor minus outdoor temperature."

    def effective(q: float, ua: float) -> float:
        return q / ua if ua > 0 else 0.0

    floor_h: Dict[str, str]
    if p["floor_type"] == "slab":
        f_p = SLAB_EDGE_F[p["slab_edge"]]
        floor_h = {
            "equation": "q = F_p P \\Delta t",
            "values": f"{f_p:.2f} \\times {n(perimeter)} \\times {dt:.0f} = {n(heat['floor'])}",
            "legend": "F_p: slab edge heat-loss coefficient. P: exposed slab perimeter, ft. Slabs lose most of their heat at the edge.",
        }
    elif p["floor_type"] in ("crawl_vented", "over_ambient"):
        floor_h = {
            "equation": "q = U A \\Delta t",
            "values": f"{p['floor_u']:.3f} \\times {n(sum(z['floor_area_exposed'] for z in zones))} \\times {dt:.0f} = {n(heat['floor'])}",
            "legend": "The space below is taken at the outdoor temperature, as ASHRAE recommends for design.",
        }
    else:
        floor_h = {
            "equation": "q = \\sum U A (t_{in} - t_{ground\\ or\\ buffer})",
            "values": f"q = {n(heat['floor'])}",
            "legend": "Below-grade paths use ASHRAE's depth-averaged soil U-factors and a ground temperature of "
                      f"{_ground_temperature(p):.0f} °F. Buffer spaces use a steady heat balance (ASHRAE Ch. 17, Eq. 5).",
        }

    swing_note = (
        f"Holding exactly {p['indoor_cooling_f']:.0f} °F would need {cooling['fixed_setpoint_peak']:,.0f} Btu/h "
        f"at the peak. Letting the room drift up to {p['temperature_swing_f']:.1f} °F, with heat stored in the "
        f"structure, needs {cooling['room_load']:,.0f} Btu/h. Each cooling line in the table is scaled by "
        f"{cooling['swing_ratio']:.3f} so the parts add up to the capacity the equipment must supply."
    )

    latent = cooling["latent_components"]
    return {
        "heating": {
            "walls": {
                "title": "Walls", "equation": "q = U A \\Delta t",
                "values": f"{p['wall_u']:.3f} \\times {n(net)} \\times {dt:.0f} = {n(heat['walls'])}",
                "legend": legend_ua + " Area is gross wall minus windows and doors.",
            },
            "windows": {
                "title": "Windows", "equation": "q = U A \\Delta t",
                "values": f"{p['window_u']:.2f} \\times {n(windows)} \\times {dt:.0f} = {n(heat['windows'])}",
                "legend": legend_ua + " No credit for winter sun.",
            },
            "doors": {
                "title": "Doors", "equation": "q = U A \\Delta t",
                "values": f"{p['door_u']:.2f} \\times {n(doors)} \\times {dt:.0f} = {n(heat['doors'])}",
                "legend": legend_ua,
            },
            "ceiling": {
                "title": "Ceiling", "equation": "q = U A \\Delta t",
                "values": f"{p['ceiling_u']:.3f} \\times {n(ceiling)} \\times {dt:.0f} = {n(heat['ceiling'])}",
                "legend": legend_ua + " A vented attic is taken at the outdoor temperature.",
            },
            "floor": {"title": "Floor", **floor_h},
            "infiltration": {
                "title": "Air leakage",
                "equation": "q = C_s Q \\Delta t, \\quad Q = \\max(Q_{unbal}, A_L \\, IDF + 0.5 Q_{unbal})",
                "values": (
                    f"A_L = {air_h['leak_area_in2']:.1f}\\,\\text{{in}}^2,\\ IDF = {air_h['idf']:.3f},\\ "
                    f"Q = {air_h['combined']:.0f}\\,\\text{{cfm}};\\ q = {c_s:.3f} \\times {air_h['combined']:.0f} "
                    f"\\times {dt:.0f} = {n(heat['infiltration'])}"
                ),
                "legend": "A_L: leakage area, 0.055 × CFM50. IDF: stack and wind driving force at 15 mph. C_s: air heat factor at this elevation. Q_unbal: exhaust-only or supply-only fan flow.",
            },
            "ventilation": {
                "title": "Mechanical ventilation",
                "equation": "q = C_s Q_{bal} (1 - \\varepsilon) \\Delta t",
                "values": f"q = {n(heat['ventilation'])}",
                "legend": "Q_bal: balanced fan flow. ε: heat recovery effectiveness.",
            },
            "ducts": {
                "title": "Ducts", "equation": "q_d = F_{dl} \\sum q",
                "values": f"{factor_h:.3f} \\times {n(heating['total'] - heat['ducts'])} = {n(heat['ducts'])}",
                "legend": "F_dl: ASHRAE Ch. 17 Table 6 factor, interpolated for duct R-value and leakage, then adjusted to the actual temperatures around the ducts.",
            },
        },
        "cooling": {
            "note": swing_note,
            "walls": {
                "title": "Walls",
                "equation": "T_{sa} = T_o + \\alpha E_t / h_o, \\quad q(t) = A \\sum_n Y_n T_{sa,n} e^{i n \\omega t}",
                "values": (
                    f"U A = {p['wall_u']:.3f} \\times {n(net)};\\ q_{{peak}} = {n(cool['walls'])}"
                    f"\\ (\\text{{effective }} \\Delta t = {effective(cool['walls'], p['wall_u'] * net):.1f}\\,°F)"
                ),
                "legend": "T_sa: sol-air temperature on each wall face. α: surface absorptance. E_t: clear-sky irradiance. Y_n: transfer admittance of the wall layers, which sets the time lag.",
            },
            "windows": {
                "title": "Windows",
                "equation": "q = A[U(T_o - T_i) + T_x \\, IAC \\, SHGC (E_D f_\\theta (1 - F_{shd}) + 0.89 E_d)]",
                "values": (
                    f"U = {p['window_u']:.2f},\\ SHGC = {p['window_shgc']:.2f},\\ T_x = {SCREEN_TX[p['insect_screen']]:.2f},\\ "
                    f"IAC = {INTERIOR_SHADE_IAC[p['interior_shade']]:.2f},\\ A = {n(windows)};\\ q_{{peak}} = {n(cool['windows'])}"
                ),
                "legend": "E_D, E_d: direct and diffuse sun on the glass. f_θ: drop in gain at steep sun angles. F_shd: share shaded by the overhang at that hour. T_x: screen transmission. IAC: interior shade factor.",
            },
            "doors": {
                "title": "Doors", "equation": "q = U A (T_{sa} - T_i)",
                "values": f"q_{{peak}} = {n(cool['doors'])}",
                "legend": "Doors share the sol-air temperature of the walls they sit in, with no time lag.",
            },
            "ceiling": {
                "title": "Ceiling",
                "equation": "T_{attic} = \\frac{U_r T_{sa} + C_s Q_v T_o + U_c T_i}{U_r + C_s Q_v + U_c}",
                "values": (
                    f"T_{{attic}} = {cooling['attic_at_peak']:.0f}\\,°F\\text{{ at the peak}};\\ "
                    f"U A = {p['ceiling_u']:.3f} \\times {n(ceiling)};\\ q_{{peak}} = {n(cool['ceiling'])}"
                ),
                "legend": "U_r: roof deck coupling. Q_v: attic ventilation flow. U_c: ceiling U-factor. Attic air lags the sun by about an hour.",
            },
            "floor": {
                "title": "Floor",
                "equation": "q_{slab} = A \\left(0.59 - \\frac{2.5}{R_{cvr} + 0.68}\\right)",
                "values": f"q_{{peak}} = {n(cool['floor'])}",
                "legend": "A slab is a small steady heat sink, so this line can be negative (ASHRAE Ch. 17, Eq. 23). A floor over a crawlspace or garage uses U A times the buffer temperature difference.",
            },
            "infiltration": {
                "title": "Air leakage",
                "equation": "q = C_s Q (T_o - T_i)",
                "values": (
                    f"Q = {air_c['combined']:.0f}\\,\\text{{cfm}},\\ IDF = {air_c['idf']:.3f},\\ "
                    f"T_o = {t_peak:.1f}\\,°F;\\ q_{{peak}} = {n(cool['infiltration'])}"
                ),
                "legend": "Summer driving force uses 7.5 mph wind and a smaller stack effect, so summer leakage is about half of winter leakage.",
            },
            "ventilation": {
                "title": "Mechanical ventilation",
                "equation": "q = C_s Q_{bal} (1 - \\varepsilon)(T_o - T_i)",
                "values": f"q_{{peak}} = {n(cool['ventilation'])}",
                "legend": "Q_bal: balanced fan flow. ε: heat recovery effectiveness.",
            },
            "internal": {
                "title": "People and appliances",
                "equation": "q_{ig,s} = 464 + 0.7 A_{cf} + 75 N_{oc}",
                "values": (
                    f"q_{{ig,s}} = {n(cooling['q_internal_sensible'])}\\ \\text{{before storage}};\\ "
                    f"q_{{peak}} = {n(cool['internal'])}"
                ),
                "legend": "A_cf: conditioned floor area. N_oc: occupants. ASHRAE Ch. 17 Equation 30, from typical US home profiles at 4 pm.",
            },
            "ducts": {
                "title": "Ducts", "equation": "q_d = F_{dl} q_{room}",
                "values": f"{factor_c:.3f} \\times {n(cooling['room_load'])} = {n(cool['ducts'])}",
                "legend": "F_dl: ASHRAE Ch. 17 Table 6, adjusted to the temperature around the ducts at the peak hour.",
            },
            "latent": {
                "title": "Latent (moisture)",
                "equation": "q_l = C_l Q \\Delta W + q_{ig,l} + q_{duct,l}",
                "values": (
                    f"{c_l:,.0f} \\times {air_c['combined'] + air_c['balanced']:.0f} \\times {cooling['delta_w']:.4f} "
                    f"\\text{{ (before ERV recovery) }} + {n(latent['internal'])} + {n(latent['ducts'])} = {n(cooling['latent'])}"
                ).replace(",", "{,}", 1),
                "legend": "C_l: air latent factor. ΔW: outdoor minus indoor humidity ratio, lb water per lb dry air. q_ig,l: occupant and cooking moisture. q_duct,l: humid air pulled in by return leaks.",
            },
        },
    }


# =============================================================================
# DERIVATION TREE
# =============================================================================


def _var(symbol: str, meaning: str, value: Any = None, unit: str = "") -> Dict[str, Any]:
    return {"symbol": symbol, "meaning": meaning, "value": value, "unit": unit}


def _node(
    node_id: str,
    label: str,
    value: float,
    unit: str = "Btu/h",
    about: str = "",
    equation: str = "",
    substituted: str = "",
    variables: Optional[List[Dict[str, Any]]] = None,
    meaning: str = "",
    limits: Optional[List[str]] = None,
    reference: str = "",
    children: Optional[List[Dict[str, Any]]] = None,
    digits: int = 0,
) -> Dict[str, Any]:
    """One result: what it is, its equation, every variable, and what to make of it."""
    return {
        "id": node_id, "label": label, "value": value, "unit": unit, "digits": digits,
        "about": about, "equation": equation, "substituted": substituted,
        "variables": variables or [], "meaning": meaning, "limits": limits or [],
        "reference": reference, "children": children or [],
    }


def _derivation_tree(run: Dict[str, Any]) -> Dict[str, Any]:
    """Every result as a tree: value, description, equation, variables, and units."""
    p = run["params"]
    zones = run["zones"]
    heating = run["heating"]
    cooling = run["cooling"]
    c_s, c_l = air_factors(p["elevation_ft"])
    pressure = pressure_psia(p["elevation_ft"])
    n = _tex_number
    dt = heating["delta_t"]
    t_in_h, t_out_h = p["indoor_heating_f"], p["heating_design_f"]
    t_in_c = p["indoor_cooling_f"]

    windows = sum(sum(z["windows"].values()) for z in zones)
    doors = sum(z["door_area"] for z in zones)
    gross = sum(sum(z["wall_lengths"].values()) * z["height"] * z["levels"] for z in zones)
    net = max(gross - windows - doors, 0.0)
    ceiling = sum(z["ceiling_area"] for z in zones)
    floor_area = sum(z["floor_area_exposed"] for z in zones)
    perimeter = sum(z["perimeter"] for z in zones)
    volume = sum(z["volume"] for z in zones)
    heat = heating["components"]
    cool = cooling["components"]
    air_h, air_c = heating["air"], cooling["air"]
    envelope = heating["total"] - heat["ducts"]
    factor_h = heat["ducts"] / max(envelope, 1.0)
    factor_c = cool["ducts"] / max(cooling["room_load"], 1.0)
    peak = cooling["peak_hour"]
    t_peak = cooling["t_out"][peak - 1]
    attic = cooling["attic_at_peak"]
    ratio = cooling["swing_ratio"]
    recovery = p["ventilation_effectiveness"] if p["ventilation_type"] in ("hrv", "erv") else 0.0
    ash17 = "ASHRAE Handbook Fundamentals, Chapter 17"

    u_vars = lambda u, a, name: [
        _var("U", f"{name} U-factor: heat flow per ft² per °F. Lower is better insulated.", u, "Btu/h·ft²·°F"),
        _var("A", f"{name} area", a, "ft²"),
        _var("\\Delta t", "Indoor design temperature minus outdoor design temperature", dt, "°F"),
    ]

    def ua_node(node_id: str, label: str, u: float, a: float, name: str, extra: str, digits: int = 3) -> Dict[str, Any]:
        return _node(
            f"heat-{node_id}", label, heat[node_id],
            about=f"Heat conducted through the {name.lower()} on the coldest design hour. {extra}",
            equation="q = U A \\Delta t",
            substituted=f"q = {u:.{digits}f} \\times {n(a)} \\times {dt:.0f} = {n(heat[node_id])}\\ \\text{{Btu/h}}",
            variables=u_vars(u, a, name),
            meaning=f"{100 * heat[node_id] / max(heating['total'], 1):.0f}% of the design heat loss.",
            reference=f"{ash17}, Equation 33",
        )

    design_t = _node(
        "design-dt", "Design temperature difference", dt, "°F",
        about="How far the house must hold indoor air above outdoor air on a design winter hour. Every conduction line scales with it.",
        equation="\\Delta t = t_{in} - t_{out}",
        substituted=f"\\Delta t = {t_in_h:.0f} - ({t_out_h:.1f}) = {dt:.1f}\\ °F",
        variables=[
            _var("t_{in}", "Indoor winter design temperature", t_in_h, "°F"),
            _var("t_{out}", "Outdoor winter design temperature. Exceeded in about 99% of the hours of the year.", t_out_h, "°F"),
        ],
        reference="Outdoor value computed from NOAA hourly observations with ASHRAE's definition.",
        digits=1,
    )

    leak_area = _node(
        "heat-leak-area", "Effective leakage area", air_h["leak_area_in2"], "in²",
        about="The size of one hole with the same leakage as all the cracks in the house, converted from a blower door number.",
        equation="A_L = 0.055 \\, \\frac{ACH_{50} V}{60}",
        substituted=f"A_L = 0.055 \\times \\frac{{{p['ach50']:g} \\times {n(volume)}}}{{60}} = {air_h['leak_area_in2']:.1f}\\ \\text{{in}}^2",
        variables=[
            _var("ACH_{50}", "Air changes per hour at 50 Pa from a blower door test", p["ach50"], "1/h"),
            _var("V", "Conditioned volume", volume, "ft³"),
        ],
        limits=["The rule assumes a typical leakage exponent of 0.65."],
        digits=1,
    )
    driving = _node(
        "heat-idf", "Infiltration driving force", air_h["idf"], "cfm/in²",
        about="How hard winter stack effect and wind push air through each square inch of leakage.",
        equation="IDF = \\frac{I_0 + H \\, \\Delta t \\, (I_1 + I_2 \\, f)}{1000}",
        substituted=f"IDF = \\frac{{698 + {air_h['stack_height']:.1f} \\times {dt:.1f} \\times (0.81 + 0.53 \\times {p['flue_fraction']:g})}}{{1000}} = {air_h['idf']:.3f}\\ \\text{{cfm/in}}^2",
        variables=[
            _var("I_0, I_1, I_2", "ASHRAE coefficients for 15 mph wind and typical suburban shelter", "698, 0.81, 0.53", ""),
            _var("H", "Stack height, the average ceiling height above the floor or grade", air_h["stack_height"], "ft"),
            _var("f", "Share of leakage area that is flues", p["flue_fraction"], ""),
        ],
        limits=["Valid for typical suburban sheltering and flue share below one half."],
        reference=f"{ash17}, Equation 10",
        digits=3,
    )
    infiltration_h = _node(
        "heat-infiltration", "Air leakage", heat["infiltration"],
        about="Cold outdoor air replaces warm indoor air through cracks, and all of it must be heated.",
        equation="q = C_s Q \\Delta t, \\quad Q = \\max(Q_{unbal},\\ A_L \\, IDF + 0.5 Q_{unbal})",
        substituted=f"q = {c_s:.3f} \\times {air_h['combined']:.1f} \\times {dt:.1f} = {n(heat['infiltration'])}\\ \\text{{Btu/h}}",
        variables=[
            _var("C_s", "Heat carried per cfm per °F, reduced for altitude. 1.08 at sea level.", round(c_s, 3), "Btu/h·cfm·°F"),
            _var("Q", "Air leakage flow on the design day", air_h["combined"], "cfm"),
            _var("Q_{unbal}", "Exhaust-only or supply-only fan flow", p["ventilation_cfm"] if p["ventilation_type"] in ("exhaust", "supply") else 0.0, "cfm"),
        ],
        meaning=f"Equal to {air_h['combined'] * 60 / max(volume, 1):.2f} air changes per hour at design conditions.",
        reference=f"{ash17}, Equations 8, 14, and 15",
        children=[leak_area, driving],
    )
    if p["floor_type"] == "slab":
        f_p = SLAB_EDGE_F[p["slab_edge"]]
        floor_heat = _node(
            "heat-floor", "Floor", heat["floor"],
            about="A slab loses most of its heat sideways through the exposed edge, so the calculation uses perimeter and not floor area.",
            equation="q = F_p P \\Delta t",
            substituted=f"q = {f_p:.2f} \\times {n(perimeter)} \\times {dt:.1f} = {n(heat['floor'])}\\ \\text{{Btu/h}}",
            variables=[
                _var("F_p", "Heat-loss coefficient per foot of slab edge, set by edge insulation", f_p, "Btu/h·ft·°F"),
                _var("P", "Exposed slab perimeter", perimeter, "ft"),
                _var("\\Delta t", "Indoor minus outdoor design temperature", dt, "°F"),
            ],
            reference=f"{ash17}, Table 16, with ASHRAE Chapter 18 coefficients",
        )
    elif p["floor_type"] in ("crawl_vented", "over_ambient"):
        floor_heat = _node(
            "heat-floor", "Floor", heat["floor"],
            about="The space below is taken at the outdoor temperature, as ASHRAE recommends for design.",
            equation="q = U A \\Delta t",
            substituted=f"q = {p['floor_u']:.3f} \\times {n(floor_area)} \\times {dt:.1f} = {n(heat['floor'])}\\ \\text{{Btu/h}}",
            variables=u_vars(p["floor_u"], floor_area, "Floor"),
            reference=f"{ash17}, Equation 33",
        )
    else:
        floor_heat = _node(
            "heat-floor", "Floor and below-grade walls", heat["floor"],
            about="Heat flows to the ground, or to a basement or crawlspace whose temperature comes from a steady heat balance.",
            equation="q = \\sum U_{avg} A (t_{in} - t_{gr})",
            substituted=f"t_{{gr}} = {_ground_temperature(p):.1f}\\ °F; \\quad q = {n(heat['floor'])}\\ \\text{{Btu/h}}",
            variables=[
                _var("U_{avg}", "Depth-averaged U-factor through wall insulation and soil", None, "Btu/h·ft²·°F"),
                _var("A", "Below-grade wall and floor area", None, "ft²"),
                _var("t_{gr}", "Ground temperature: annual mean less the seasonal amplitude", _ground_temperature(p), "°F"),
            ],
            reference="ASHRAE Fundamentals, Chapter 18, Equations 37 to 42; Latta and Boileau 1969",
        )

    ducts_h = _node(
        "heat-ducts", "Ducts", heat["ducts"],
        about="Heat lost through duct walls and leaks before the air reaches the rooms. The equipment has to make it up.",
        equation="q_d = F_{dl} \\sum q",
        substituted=f"q_d = {factor_h:.3f} \\times {n(envelope)} = {n(heat['ducts'])}\\ \\text{{Btu/h}}" if p["duct_location"] != "conditioned" else "q_d = 0\\ \\text{(ducts are inside the conditioned space)}",
        variables=[
            _var("F_{dl}", "Duct loss factor for this location, insulation, and leakage, adjusted to these temperatures", round(factor_h, 3), ""),
            _var("\\sum q", "Everything else in the heat loss", envelope, "Btu/h"),
            _var("R", "Duct insulation", p["duct_r"], "ft²·h·°F/Btu"),
            _var("\\ell", "Leakage on each of the supply and return sides", p["duct_leakage_pct"], "% of fan flow"),
        ],
        meaning="Moving ducts inside conditioned space removes this line.",
        limits=["Factors assume the ASHRAE Standard 152 default duct area. Long runs can lose more."],
        reference=f"{ash17}, Table 6",
    )
    heat_children = [
        ua_node("walls", "Walls", p["wall_u"], net, "Walls", "Area is gross wall minus windows and doors."),
        ua_node("windows", "Windows", p["window_u"], windows, "Windows", "No credit is taken for winter sun.", 2),
        ua_node("doors", "Doors", p["door_u"], doors, "Doors", "", 2),
        ua_node("ceiling", "Ceiling", p["ceiling_u"], ceiling, "Ceiling", "A vented attic is taken at the outdoor temperature."),
        floor_heat,
        infiltration_h,
    ]
    if heat["ventilation"] > 0.5:
        heat_children.append(_node(
            "heat-ventilation", "Mechanical ventilation", heat["ventilation"],
            about="Balanced fans bring in outdoor air on purpose. A heat recovery core reclaims part of the heat.",
            equation="q = C_s Q_{bal} (1 - \\varepsilon) \\Delta t",
            substituted=f"q = {c_s:.3f} \\times {air_h['balanced']:.0f} \\times (1 - {recovery:.2f}) \\times {dt:.1f} = {n(heat['ventilation'])}\\ \\text{{Btu/h}}",
            variables=[
                _var("Q_{bal}", "Balanced ventilation flow", air_h["balanced"], "cfm"),
                _var("\\varepsilon", "Sensible heat recovery effectiveness", recovery, ""),
            ],
            reference=f"{ash17}, Equation 15",
        ))
    heat_children.append(ducts_h)
    heat_root = _node(
        "heating", "Design heat loss", heating["total"],
        about="The heat the equipment must deliver to hold the indoor temperature on a design winter hour, with no credit for sun, people, or stored heat.",
        equation="q_{heat} = \\sum q_{envelope} + q_{air} + q_{ducts}",
        substituted=f"q_{{heat}} = {n(envelope)} + {n(heat['ducts'])} = {n(heating['total'])}\\ \\text{{Btu/h}}",
        variables=[
            _var("UA", "Total heat loss per °F of temperature difference", heating["ua"], "Btu/h·°F"),
            _var("\\Delta t", "Indoor minus outdoor design temperature", dt, "°F"),
        ],
        meaning=f"Equal to {heating['total'] / KW_BTUH:.1f} kW. Heating is steady and worst case by design, which leaves a built-in margin.",
        reference=f"{ash17}, section 8",
        children=heat_children + [design_t],
    )

    # ------------------------------------------------------------------- cooling
    def scaled(key: str, about: str, equation: str, substituted: str, variables: List[Dict[str, Any]],
               label: str, meaning: str = "", children: Optional[List[Dict[str, Any]]] = None,
               reference: str = "") -> Dict[str, Any]:
        return _node(f"cool-{key}", label, cool[key], about=about, equation=equation,
                     substituted=substituted, variables=variables, meaning=meaning,
                     children=children, reference=reference)

    attic_node = _node(
        "cool-attic", "Attic temperature at the peak", attic, "°F",
        about="Sun heats the roof deck, the deck heats the attic air, and ventilation carries some of that away. This balance sets what the ceiling and attic ducts see.",
        equation="T_{attic} = \\frac{U_r T_{sa} + C_s Q_v T_o + U_c T_i}{U_r + C_s Q_v + U_c}",
        substituted=f"T_{{attic}} = {attic:.1f}\\ °F\\ \\text{{at solar hour {peak}}}",
        variables=[
            _var("U_r", "Heat transfer from the roof deck into attic air per ft² of ceiling", None, "Btu/h·ft²·°F"),
            _var("T_{sa}", "Sol-air temperature of the roof", None, "°F"),
            _var("Q_v", "Attic ventilation per ft² of ceiling", p["attic_vent_cfm_per_ft2"], "cfm/ft²"),
            _var("T_o", "Outdoor air temperature at this hour", t_peak, "°F"),
            _var("U_c", "Ceiling U-factor", p["ceiling_u"], "Btu/h·ft²·°F"),
        ],
        reference=f"{ash17}, Equation 5, with a one-hour lag for sheathing and framing",
        digits=1,
    )
    room_children = [
        scaled("walls", "Sun heats the outside of each wall, and that heat crosses the wall's layers hours later. The calculation follows each face through the day.",
               "T_{sa} = T_o + \\frac{\\alpha E_t}{h_o}, \\quad q(t) = A \\sum_n Y_n T_{sa,n} e^{i n \\omega t}",
               f"q_{{peak}} = {n(cool['walls'])}\\ \\text{{Btu/h}}\\ \\text{{over}}\\ {n(net)}\\ \\text{{ft}}^2",
               [_var("\\alpha", "Share of sunlight the wall absorbs", p["wall_absorptance"], ""),
                _var("E_t", "Clear-sky sun on each face at each hour", None, "Btu/h·ft²"),
                _var("h_o", "Outside surface conductance", H_OUT_WALL, "Btu/h·ft²·°F"),
                _var("Y_n", "How much of harmonic n of the daily temperature wave gets through the wall layers. This sets the time lag.", None, "Btu/h·ft²·°F"),
                _var("A", "Net wall area", net, "ft²")],
               "Walls", reference="Periodic conduction: Carslaw and Jaeger; checked against a finite-difference march in the test suite"),
        scaled("windows", "Windows admit sun directly and also conduct heat. Sun is the larger part, and it depends on direction, shading, and hour.",
               "q = A\\left[U(T_o - T_i) + T_x \\, IAC \\, SHGC\\left(E_D f_\\theta (1 - F_{shd}) + 0.89 E_d\\right)\\right]",
               f"q_{{peak}} = {n(cool['windows'])}\\ \\text{{Btu/h}}\\ \\text{{over}}\\ {n(windows)}\\ \\text{{ft}}^2",
               [_var("U", "Window U-factor", p["window_u"], "Btu/h·ft²·°F"),
                _var("SHGC", "Solar heat gain coefficient: share of sunlight that becomes heat inside", p["window_shgc"], ""),
                _var("T_x", "Transmission of insect screens", SCREEN_TX[p["insect_screen"]], ""),
                _var("IAC", "Interior shade attenuation", INTERIOR_SHADE_IAC[p["interior_shade"]], ""),
                _var("E_D, E_d", "Direct and diffuse sun on the glass", None, "Btu/h·ft²"),
                _var("f_\\theta", "Drop in gain at steep sun angles", None, ""),
                _var("F_{shd}", "Share of the window shaded by the overhang that hour", None, "")],
               "Windows", reference=f"{ash17}, Equations 25 to 29; ASHRAE clear-sky model, Chapter 14"),
    ]
    if cool["doors"]:
        room_children.append(scaled("doors", "Doors share the sol-air temperature of the walls they sit in, with no time lag.",
                                    "q = U A (T_{sa} - T_i)", f"q_{{peak}} = {n(cool['doors'])}\\ \\text{{Btu/h}}",
                                    [_var("U", "Door U-factor", p["door_u"], "Btu/h·ft²·°F"), _var("A", "Door area", doors, "ft²")], "Doors"))
    room_children += [
        scaled("ceiling", "The attic is far hotter than outdoors on a sunny day, so the ceiling sees a large temperature difference even with little sun on it directly.",
               "q(t) = A \\sum_n Y_n (T_{attic} - T_i)_n e^{i n \\omega t}",
               f"q_{{peak}} = {n(cool['ceiling'])}\\ \\text{{Btu/h}}\\ \\text{{over}}\\ {n(ceiling)}\\ \\text{{ft}}^2",
               [_var("U", "Ceiling U-factor", p["ceiling_u"], "Btu/h·ft²·°F"), _var("A", "Ceiling area", ceiling, "ft²"),
                _var("T_{attic}", "Attic air temperature at the peak", attic, "°F")],
               "Ceiling", children=[attic_node]),
        scaled("floor", "A slab is a small steady heat sink, so this line can be negative. A floor over a crawlspace or garage gains heat from the warmer space below.",
               "q_{slab} = A\\left(0.59 - \\frac{2.5}{R_{cvr} + 0.68}\\right)",
               f"q_{{peak}} = {n(cool['floor'])}\\ \\text{{Btu/h}}",
               [_var("A", "Floor area", floor_area, "ft²"), _var("R_{cvr}", "Resistance of the floor covering", 1.2 if p["floor_cover"] == "carpet" else 0.1, "ft²·h·°F/Btu")],
               "Floor", reference=f"{ash17}, Equation 23"),
        scaled("infiltration", "Hot outdoor air leaks in. Summer driving forces are about half of winter's, with less wind and a smaller stack effect.",
               "q = C_s Q (T_o - T_i)",
               f"q = {c_s:.3f} \\times {air_c['combined']:.1f} \\times ({t_peak:.1f} - {t_in_c:.0f}) \\times {ratio:.3f} = {n(cool['infiltration'])}\\ \\text{{Btu/h}}",
               [_var("Q", "Air leakage flow in summer", air_c["combined"], "cfm"), _var("T_o", "Outdoor temperature at the peak hour", t_peak, "°F"),
                _var("T_i", "Indoor summer temperature", t_in_c, "°F"), _var("r", "Swing ratio applied to all room lines", round(ratio, 3), "")],
               "Air leakage", reference=f"{ash17}, Equations 8 and 15"),
    ]
    if cool["ventilation"]:
        room_children.append(scaled("ventilation", "Fans bring in hot outdoor air on purpose. Heat recovery reclaims part of it.",
                                    "q = C_s Q_{bal} (1 - \\varepsilon)(T_o - T_i)", f"q_{{peak}} = {n(cool['ventilation'])}\\ \\text{{Btu/h}}",
                                    [_var("Q_{bal}", "Balanced ventilation flow", air_c["balanced"], "cfm"), _var("\\varepsilon", "Heat recovery effectiveness", recovery, "")],
                                    "Mechanical ventilation"))
    room_children.append(scaled("internal", "People, lights, and appliances. The value comes from typical US home profiles at 4 pm.",
                                "q_{ig,s} = 464 + 0.7 A_{cf} + 75 N_{oc}",
                                f"q_{{ig,s}} = {n(cooling['q_internal_sensible'])}\\ \\text{{Btu/h before storage}}",
                                [_var("A_{cf}", "Conditioned floor area", p["floor_area_ft2"], "ft²"), _var("N_{oc}", "Occupants", p["occupants"], "people")],
                                "People and appliances", reference=f"{ash17}, Equation 30"))
    mass = THERMAL_MASS[p["construction_mass"]]
    room_node = _node(
        "cool-room", "Room load with temperature swing", cooling["room_load"],
        about="Equipment need not hold the thermostat exactly at the peak. The room may drift a few degrees while the structure soaks up heat, which lowers the capacity required.",
        equation="C_m \\frac{d\\theta_m}{dt} = G_{rad} - H(\\theta_m - \\theta_a), \\quad 0 = G_{conv} + H(\\theta_m - \\theta_a) - UA \\, \\theta_a - Q",
        substituted=f"Q_{{fixed}} = {n(cooling['fixed_setpoint_peak'])} \\ \\rightarrow\\ Q_{{swing}} = {n(cooling['room_load'])}\\ \\text{{Btu/h}}",
        variables=[
            _var("\\theta_a, \\theta_m", "Air and thermal mass temperature above the thermostat setting", None, "°F"),
            _var("C_m", "Thermally active capacity of the structure and contents", mass["capacity"] * p["floor_area_ft2"], "Btu/°F"),
            _var("H", "Heat transfer between the mass and room air", mass["conductance"] * p["floor_area_ft2"], "Btu/h·°F"),
            _var("UA", "House conductance to outdoors", cooling["ua_house"], "Btu/h·°F"),
            _var("G_{rad}, G_{conv}", "Radiant and convective shares of each gain", None, "Btu/h"),
            _var("\\Delta T_{swing}", "Allowed rise above the thermostat", p["temperature_swing_f"], "°F"),
        ],
        meaning=f"Each line below is scaled by {ratio:.3f}, so the parts add up to the capacity required. The hourly peak falls at solar hour {peak}.",
        limits=["Thermal mass was calibrated once, to the ASHRAE Chapter 17 worked example."],
        reference="Control assumption of ASHRAE's Residential Heat Balance method (Barnaby, Spitler, and Xiao 2005)",
        children=room_children,
    )
    ducts_c = _node(
        "cool-ducts", "Ducts", cool["ducts"],
        about="Cold air gains heat through duct walls and leaks on the way to the rooms. In an attic this can be a large line.",
        equation="q_d = F_{dl} \\, q_{room}",
        substituted=f"q_d = {factor_c:.3f} \\times {n(cooling['room_load'])} = {n(cool['ducts'])}\\ \\text{{Btu/h}}" if p["duct_location"] != "conditioned" else "q_d = 0\\ \\text{(ducts are inside the conditioned space)}",
        variables=[
            _var("F_{dl}", "Duct gain factor adjusted to the temperature around the ducts at the peak", round(factor_c, 3), ""),
            _var("q_{room}", "Room load with temperature swing", cooling["room_load"], "Btu/h"),
        ],
        reference=f"{ash17}, Table 6",
    )
    sensible_node = _node(
        "cool-sensible", "Sensible cooling", cooling["sensible"],
        about="Heat that changes air temperature, the part a thermostat responds to.",
        equation="q_s = q_{room} + q_d",
        substituted=f"q_s = {n(cooling['room_load'])} + {n(cool['ducts'])} = {n(cooling['sensible'])}\\ \\text{{Btu/h}}",
        children=[room_node, ducts_c],
    )
    latent = cooling["latent_components"]
    w_node = _node(
        "cool-dw", "Moisture difference", cooling["delta_w"] * 7000.0, "grains/lb",
        about="How much wetter the outdoor air is than the indoor air you want. Zero in a dry climate.",
        equation="\\Delta W = W_o - W_i",
        substituted=f"\\Delta W = {cooling['w_out']:.4f} - {cooling['w_in']:.4f} = {cooling['delta_w']:.4f}\\ \\text{{lb/lb}}",
        variables=[
            _var("W_o", f"Outdoor humidity ratio at {p['cooling_design_f']:.1f} °F and a {p['cooling_wet_bulb_f']:.1f} °F wet bulb", round(cooling["w_out"], 4), "lb/lb"),
            _var("W_i", f"Indoor humidity ratio at {t_in_c:.0f} °F and {p['indoor_rh_pct']:.0f}% RH", round(cooling["w_in"], 4), "lb/lb"),
            _var("p", "Atmospheric pressure at this elevation", round(pressure, 2), "psia"),
        ],
        reference="ASHRAE Fundamentals, Chapter 1; Hyland and Wexler 1983",
        digits=1,
    )
    latent_node = _node(
        "cool-latent", "Latent cooling", cooling["latent"],
        about="Heat removed by condensing moisture out of the air. The equipment must do this as well as lower the temperature.",
        equation="q_l = C_l Q \\Delta W + q_{ig,l} + q_{duct,l}",
        substituted=(
            f"q_l = {n(latent['infiltration'] + latent['ventilation'])} + {n(latent['internal'])} + {n(latent['ducts'])} "
            f"= {n(cooling['latent'])}\\ \\text{{Btu/h}}"
        ),
        variables=[
            _var("C_l", "Latent heat carried per cfm per lb/lb, reduced for altitude. 4,840 at sea level.", round(c_l), "Btu/h·cfm"),
            _var("Q", "Outdoor air flow from leakage and ventilation", air_c["combined"] + air_c["balanced"], "cfm"),
            _var("\\Delta W", "Outdoor minus indoor humidity ratio", round(cooling["delta_w"], 4), "lb/lb"),
            _var("q_{ig,l}", "Moisture from people, cooking, and bathing: 68 + 0.07 A + 41 N", latent["internal"], "Btu/h"),
            _var("q_{duct,l}", "Humid air drawn in by return duct leaks", latent["ducts"], "Btu/h"),
        ],
        reference=f"{ash17}, Equations 16, 31, and 32",
        children=[w_node],
    )
    cool_root = _node(
        "cooling", "Total cooling load", cooling["total"],
        about="The sensible and latent heat the equipment must remove on a clear design day.",
        equation="q_t = q_s + q_l",
        substituted=f"q_t = {n(cooling['sensible'])} + {n(cooling['latent'])} = {n(cooling['total'])}\\ \\text{{Btu/h}}",
        variables=[
            _var("q_s", "Sensible cooling", cooling["sensible"], "Btu/h"),
            _var("q_l", "Latent cooling", cooling["latent"], "Btu/h"),
            _var("SHR", "Sensible heat ratio of the load", round(cooling["shr"], 2), ""),
        ],
        meaning=f"Equal to {cooling['total'] / TON_BTUH:.2f} tons. One ton is 12,000 Btu/h.",
        children=[sensible_node, latent_node],
    )
    return {"heating": heat_root, "cooling": cool_root}


def _room_tree(zone: Dict[str, Any], heat: Dict[str, float], p: Dict[str, Any], dt: float, c_s: float) -> List[Dict[str, Any]]:
    """Heat loss lines for one room, each with its equation and numbers."""
    n = _tex_number
    windows = sum(zone["windows"].values())
    gross = sum(zone["wall_lengths"].values()) * zone["height"] * zone["levels"]
    net = max(gross - windows - zone["door_area"], 0.0)
    rows = []

    def add(key: str, label: str, u: float, area: float) -> None:
        if heat.get(key, 0.0) <= 0.5:
            return
        rows.append(_node(
            f"room-{key}", label, heat[key], about="Conduction on the design winter hour.",
            equation="q = U A \\Delta t",
            substituted=f"q = {u:.3f} \\times {n(area)} \\times {dt:.1f} = {n(heat[key])}\\ \\text{{Btu/h}}",
            variables=[_var("U", f"{label} U-factor", u, "Btu/h·ft²·°F"), _var("A", f"{label} area in this room", area, "ft²"),
                       _var("\\Delta t", "Indoor minus outdoor design temperature", dt, "°F")],
        ))

    add("walls", "Exterior walls", p["wall_u"], net)
    add("windows", "Windows", p["window_u"], windows)
    add("doors", "Doors", p["door_u"], zone["door_area"])
    add("ceiling", "Ceiling", p["ceiling_u"], zone["ceiling_area"])
    if heat.get("floor", 0.0) > 0.5:
        rows.append(_node("room-floor", "Floor", heat["floor"], about="Heat lost through this room's floor or slab edge.",
                          variables=[_var("P", "Exposed perimeter in this room", zone["perimeter"], "ft")]))
    if heat.get("infiltration", 0.0) > 0.5:
        rows.append(_node("room-infiltration", "Air leakage share", heat["infiltration"],
                          about="ASHRAE allocates whole-house leakage to rooms by volume.",
                          variables=[_var("V", "Room volume", zone["volume"], "ft³")]))
    if heat.get("ducts", 0.0) > 0.5:
        rows.append(_node("room-ducts", "Duct share", heat["ducts"], about="Duct losses shared in proportion to the room's load."))
    return rows


# =============================================================================
# PUBLIC CALCULATION
# =============================================================================

# (input, label, low multiplier or offset unknown, high unknown, low known, high known, mode)
UNCERTAINTY_TERMS = [
    ("ach50", "Air leakage", 0.60, 1.50, 0.90, 1.10, "scale"),
    ("window_pct_of_floor", "Window area", 0.75, 1.25, 0.97, 1.03, "scale"),
    ("wall_u", "Wall insulation", 0.75, 1.30, 0.92, 1.08, "scale"),
    ("ceiling_u", "Ceiling insulation", 0.70, 1.40, 0.90, 1.10, "scale"),
    ("window_u", "Window U-factor", 0.80, 1.20, 0.95, 1.05, "scale"),
    ("window_shgc", "Window solar gain", 0.70, 1.30, 0.92, 1.08, "scale"),
    ("duct_leakage_pct", "Duct leakage", 0.50, 1.60, 0.80, 1.20, "scale"),
    ("duct_r", "Duct insulation", 0.70, 1.30, 0.90, 1.10, "scale"),
    ("occupants", "People and appliances", 0.60, 1.50, 0.80, 1.25, "scale"),
    ("heating_design_f", "Winter design temperature", -3.0, 3.0, -1.5, 1.5, "offset"),
    ("cooling_design_f", "Summer design temperature", -2.0, 2.0, -1.0, 1.0, "offset"),
]


def _with_change(p: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
    changed = dict(p)
    changed[key] = value
    if key in ("cooling_design_f",) and changed["cooling_wet_bulb_f"] > value:
        changed["cooling_wet_bulb_f"] = value
    base_pct = p["window_pct_of_floor"]
    if key == "window_pct_of_floor" and p.get("window_area_n") is not None:
        factor = value / base_pct if base_pct > 0 else 1.0
        for side in ("n", "e", "s", "w"):
            changed[f"window_area_{side}"] = p[f"window_area_{side}"] * factor
    if key == "window_pct_of_floor" and p.get("rooms"):
        factor = value / base_pct if base_pct > 0 else 1.0
        changed["rooms"] = [
            {**room, "windows": {k: float(v or 0) * factor for k, v in (room.get("windows") or {}).items()}}
            for room in p["rooms"]
        ]
    return changed


def _uncertainty(p: Dict[str, Any], base: Dict[str, Any], known: Iterable[str]) -> Dict[str, Any]:
    """One-at-a-time input ranges, combined as a root sum of squares."""
    known_set = set(known or ())
    base_heat = base["heating"]["total"]
    base_cool = base["cooling"]["total"]
    terms = []
    for key, label, lo_u, hi_u, lo_k, hi_k, mode in UNCERTAINTY_TERMS:
        if key == "duct_r" and p["duct_location"] == "conditioned":
            continue
        if key == "duct_leakage_pct" and p["duct_location"] == "conditioned":
            continue
        low, high = (lo_k, hi_k) if key in known_set else (lo_u, hi_u)
        values = (
            (p[key] * low, p[key] * high) if mode == "scale"
            else (p[key] + low, p[key] + high)
        )
        results = []
        for value in values:
            if key == "window_shgc":
                value = min(value, 0.95)
            if key == "heating_design_f":
                value = min(value, p["indoor_heating_f"] - 1)
            results.append(_run(_with_change(p, key, value)))
        heat = [r["heating"]["total"] - base_heat for r in results]
        cool = [r["cooling"]["total"] - base_cool for r in results]
        terms.append({
            "key": key, "label": label, "known": key in known_set,
            "heat_low": min(heat + [0.0]), "heat_high": max(heat + [0.0]),
            "cool_low": min(cool + [0.0]), "cool_high": max(cool + [0.0]),
        })
    def rss(field: str) -> float:
        return math.sqrt(sum(t[field] ** 2 for t in terms))
    terms.sort(
        key=lambda t: -((t["heat_high"] - t["heat_low"]) / max(base_heat, 1.0)
                        + (t["cool_high"] - t["cool_low"]) / max(base_cool, 1.0))
    )
    return {
        "terms": terms,
        "heating_low": base_heat - rss("heat_low"),
        "heating_high": base_heat + rss("heat_high"),
        "cooling_low": base_cool - rss("cool_low"),
        "cooling_high": base_cool + rss("cool_high"),
    }


def _upgrades(p: Dict[str, Any], base: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load reductions from common retrofits, each applied alone."""
    candidates = []
    if p["ach50"] > 3.0:
        candidates.append(("Air seal to 3 ACH50", {"ach50": 3.0}))
    if p["ceiling_u"] > CEILING_PRESETS["r60"]["u"] * 1.05:
        candidates.append(("Insulate ceiling to R-60", {"ceiling_u": CEILING_PRESETS["r60"]["u"]}))
    if p["window_u"] > 0.33 or p["window_shgc"] > 0.33:
        candidates.append(("Replace windows (U 0.30, SHGC 0.25)",
                           {"window_u": 0.30, "window_shgc": 0.25}))
    if p["wall_u"] > 0.07:
        candidates.append(("Fill or upgrade walls to about R-15 effective", {"wall_u": 0.065}))
    if p["duct_location"] != "conditioned":
        if p["duct_leakage_pct"] > 4 or p["duct_r"] < 8:
            candidates.append(("Seal ducts to 4% and insulate to R-8",
                               {"duct_leakage_pct": 4.0, "duct_r": 8.0}))
        candidates.append(("Move ducts inside conditioned space", {"duct_location": "conditioned"}))
    if p["interior_shade"] in ("none", "light_blinds_half", "drapes_half") and p["window_shgc"] > 0.3:
        candidates.append(("Keep cellular shades closed on hot days",
                           {"interior_shade": "cellular_closed"}))
    out = []
    for label, changes in candidates:
        changed = dict(p)
        changed.update(changes)
        result = _run(changed)
        out.append({
            "label": label,
            "heating_saved": base["heating"]["total"] - result["heating"]["total"],
            "cooling_saved": base["cooling"]["total"] - result["cooling"]["total"],
        })
    out.sort(key=lambda row: -(row["heating_saved"] / max(base["heating"]["total"], 1.0)
                               + row["cooling_saved"] / max(base["cooling"]["total"], 1.0)))
    return out


def _orientation_sweep(p: Dict[str, Any]) -> List[Dict[str, float]]:
    """Cooling total at eight rotations of the house."""
    return [
        {"rotation": float(angle), "total": _run(p, rotation_extra=float(angle))["cooling"]["total"]}
        for angle in range(0, 360, 45)
    ]


def _room_table(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Room loads and airflow shares."""
    heating = run["heating"]
    cooling = run["cooling"]
    swing_ratio = cooling["swing_ratio"]
    eta_c = cooling["duct_efficiency"]
    rows = []
    total_heat = sum(line["total"] for line in heating["per_zone"]) or 1.0
    total_cool = sum(z["peak"] for z in cooling["zones"]) or 1.0
    for zone, heat, cool in zip(run["zones"], heating["per_zone"], cooling["zones"]):
        cool_load = cool["peak"] * swing_ratio / eta_c
        rows.append({
            "name": zone["name"],
            "area": zone["area"],
            "heating": heat["total"],
            "cooling": cool_load,
            "peak_hour": cool["peak_hour"],
            "heating_cfm": heating["fan_cfm"] * heat["total"] / total_heat,
            "cooling_cfm": cooling["fan_cfm"] * cool["peak"] / total_cool,
            "hourly": [max(v, 0.0) * swing_ratio / eta_c for v in cool["load"]],
            "heating_parts": {k: v for k, v in heat.items() if k != "total"},
            "heating_tree": _room_tree(
                zone, heat, run["params"], heating["delta_t"], air_factors(run["params"]["elevation_ft"])[0]),
        })
    return rows


def calculate_hvac_loads(inputs: Dict[str, Any], known_inputs: Optional[List[str]] = None,
                         detail: bool = True) -> Dict[str, Any]:
    """
    Calculate residential heating and cooling design loads.

    Heating is a steady-state UA times temperature difference sum with no
    credit for sun or internal gains. Cooling is a 24-hour design day that
    finds the capacity needed to hold the house within an allowed temperature
    swing. Inputs are passed as one dictionary because the room table is a list.

    ---Parameters---
    floor_area_ft2 : float
        Conditioned floor area, measured to the outside of exterior walls (ft²).
    stories : int
        Number of above-grade stories, 1 to 4.
    ceiling_height_ft : float
        Floor-to-floor height used for wall area and air volume (ft).
    aspect_ratio : float
        Footprint length divided by width. A longer house has more wall.
    bedrooms : int
        Bedroom count. Sets the default occupancy of bedrooms plus one.
    occupants : float
        Number of people at the design condition.
    latitude : float
        Site latitude in degrees north. Sets the sun's path.
    elevation_ft : float
        Site elevation. Thinner air carries less heat per cfm (ft).
    heating_design_f : float
        Outdoor temperature for the heating design, usually the 99% value (°F).
    cooling_design_f : float
        Outdoor temperature for the cooling design, usually the 1% value (°F).
    cooling_wet_bulb_f : float
        Mean coincident wet bulb at the cooling design temperature (°F).
    daily_range_f : float
        Mean daily high minus low in the hottest month (°F).
    ground_mean_f : float
        Mean annual air temperature, used for ground temperature (°F).
    ground_amp_f : float
        Half the difference between the warmest and coldest monthly means (°F).
    design_month : int
        Month used for sun position, 1 to 12. July suits most houses.
    indoor_heating_f : float
        Winter thermostat setting used for design (°F).
    indoor_cooling_f : float
        Summer thermostat setting used for design (°F).
    indoor_rh_pct : float
        Indoor relative humidity held in summer (%).
    temperature_swing_f : float
        Allowed rise above the thermostat at the peak. ASHRAE's residential
        method uses 3 °F. Zero assumes the room never drifts (°F).
    construction_mass : str
        How much heat the structure and contents store: light, medium, heavy.
    wall_u : float
        Whole-wall U-factor including framing (Btu/h·ft²·°F).
    wall_layers : str
        Wall build-up used for time lag: frame, brick_veneer, cmu, concrete.
    wall_absorptance : float
        Fraction of sunlight the exterior wall absorbs, 0 to 1.
    ceiling_u : float
        Ceiling or roof assembly U-factor (Btu/h·ft²·°F).
    ceiling_type : str
        attic for a ceiling under a vented attic, cathedral for a roof assembly.
    roof_color : str
        Roof surface: white, light, medium, dark, metal_light, tile_light.
    roof_pitch : float
        Roof rise per 12 inches of run.
    radiant_barrier : bool
        True if the attic has a radiant barrier.
    attic_vent_cfm_per_ft2 : float
        Attic ventilation flow per ft² of ceiling (cfm/ft²).
    floor_type : str
        slab, crawl_vented, crawl_sealed, basement_conditioned,
        basement_unconditioned, over_garage, or over_ambient.
    floor_u : float
        U-factor of a framed floor over a crawlspace, basement, or garage.
    floor_cover : str
        carpet or hard. Bare slabs absorb more heat in summer.
    slab_edge : str
        Slab edge insulation: none, r5, r10, or r15.
    crawl_wall_r : float
        Insulation on sealed crawlspace walls (ft²·h·°F/Btu).
    basement_depth_ft : float
        Depth of basement walls below grade (ft).
    basement_wall_r : float
        Insulation on basement walls (ft²·h·°F/Btu).
    window_u : float
        Rated whole-window U-factor (Btu/h·ft²·°F).
    window_shgc : float
        Rated solar heat gain coefficient, 0 to 1.
    window_pct_of_floor : float
        Total window area as a percent of floor area, split evenly by side (%).
    window_area_n : float
        North-facing window area. Fill all four to override the percent (ft²).
    window_area_e : float
        East-facing window area (ft²).
    window_area_s : float
        South-facing window area (ft²).
    window_area_w : float
        West-facing window area (ft²).
    window_height_ft : float
        Typical window height, used for overhang shading (ft).
    interior_shade : str
        none, light_blinds_half, drapes_half, blinds_closed, cellular_closed.
    insect_screen : str
        Exterior screens on none, half, or full of the window area.
    overhang_depth_ft : float
        Horizontal depth of the eave beyond the wall (ft).
    overhang_gap_ft : float
        Vertical distance from window top to the eave (ft).
    site_shade_fraction : float
        Fraction of direct sun blocked by trees or neighbors, 0 to 1.
    door_area_ft2 : float
        Total exterior door area (ft²).
    door_u : float
        Door U-factor (Btu/h·ft²·°F).
    ach50 : float
        Air changes per hour at 50 Pa from a blower door test.
    flue_fraction : float
        Share of leakage area that is flues, 0 to 1. Zero for sealed combustion.
    ventilation_type : str
        none, balanced, hrv, erv, exhaust, or supply.
    ventilation_cfm : float
        Continuous mechanical ventilation flow (cfm).
    ventilation_effectiveness : float
        HRV or ERV sensible effectiveness, 0 to 1.
    ventilation_latent_effectiveness : float
        ERV moisture recovery effectiveness, 0 to 1.
    duct_location : str
        conditioned, attic, vented_crawl, sealed_crawl, basement, or garage.
    duct_r : float
        Duct insulation R-value (ft²·h·°F/Btu).
    duct_leakage_pct : float
        Leakage on each of the supply and return sides, percent of fan flow (%).
    heating_system : str
        furnace or heat_pump. A heat pump's cooler air loses less through ducts
        per degree but moves more of it, so ASHRAE gives it separate factors.
    cooling_coil_dt_f : float
        Air temperature drop across the cooling coil (°F).
    rotation_deg : float
        Rotate the house clockwise from the entered compass directions (degrees).
    internal_sensible_btuh : float
        Whole-house sensible internal gain. Blank uses ASHRAE's equation (Btu/h).
    internal_latent_btuh : float
        Whole-house latent internal gain. Blank uses ASHRAE's equation (Btu/h).
    rooms : list
        Optional room table. Each room has name, type, area, walls, windows,
        door_area, top, and ground. Walls hold exposed length by compass side.

    ---Returns---
    heating_total : float
        Whole-house design heat loss including ducts (Btu/h).
    cooling_sensible : float
        Sensible cooling load including duct gains (Btu/h).
    cooling_latent : float
        Latent cooling load (Btu/h).
    cooling_total : float
        Total cooling load (Btu/h).
    cooling_tons : float
        Total cooling load in tons of refrigeration.
    sensible_heat_ratio : float
        Sensible load divided by total load.
    heat_loss_coefficient : float
        Design heat loss per °F of indoor-outdoor difference (Btu/h·°F).
    square_feet_per_ton : float
        Floor area per ton, for comparison with the 500 ft²/ton rule of thumb.

    ---LaTeX---
    q_{heat} = \\frac{1}{\\eta_h}\\left[\\sum U A \\Delta t + F_p P \\Delta t + C_s Q \\Delta t\\right]
    q_{vi} = C_s Q_{vi} \\Delta t, \\quad Q_{vi} = \\max(Q_{unbal}, Q_i + 0.5 Q_{unbal}) + Q_{bal}
    T_{sa} = T_o + \\alpha E_t / h_o
    q_{cool} = \\frac{Q_{swing}}{\\eta_c} + C_l Q_{vi} \\Delta W + q_{ig,l}
    """
    p = _normalize(inputs)
    run = _run(p)
    p_used = run["params"]
    heating = run["heating"]
    cooling = run["cooling"]
    area = p_used["floor_area_ft2"]
    tons = cooling["total"] / TON_BTUH

    result: Dict[str, Any] = {
        "heating_total": heating["total"],
        "cooling_sensible": cooling["sensible"],
        "cooling_latent": cooling["latent"],
        "cooling_total": cooling["total"],
        "cooling_tons": tons,
        "sensible_heat_ratio": cooling["shr"],
        "heat_loss_coefficient": heating["ua"],
        "square_feet_per_ton": area / tons if tons > 0 else None,
        "floor_area": area,
        "heating": {
            "components": heating["components"],
            "delta_t": heating["delta_t"],
            "duct_efficiency": heating["duct_efficiency"],
            "fan_cfm": heating["fan_cfm"],
            "air": heating["air"],
        },
        "cooling": {
            "components": cooling["components"],
            "latent_components": cooling["latent_components"],
            "room_load": cooling["room_load"],
            "fixed_setpoint_peak": cooling["fixed_setpoint_peak"],
            "swing_ratio": cooling["swing_ratio"],
            "peak_hour": cooling["peak_hour"],
            "duct_efficiency": cooling["duct_efficiency"],
            "fan_cfm": cooling["fan_cfm"],
            "air": cooling["air"],
            "delta_w": cooling["delta_w"],
            "grains_difference": cooling["delta_w"] * 7000.0,
            "w_out": cooling["w_out"],
            "w_in": cooling["w_in"],
            "attic_at_peak": cooling["attic_at_peak"],
            "hours": HOURS,
            "t_out": cooling["t_out"],
            "t_attic": cooling["t_attic"],
            "hourly": cooling["hourly"],
            "hourly_fixed": cooling["hourly_fixed"],
            "internal_sensible": cooling["q_internal_sensible"],
        },
        "rooms": _room_table(run) if p.get("rooms") else [],
    }
    result["subst_heating_total"] = (
        f"q = U A \\Delta t\\text{{ terms}} + C_s Q \\Delta t = "
        f"{heating['ua']:,.0f} \\times {heating['delta_t']:.0f} = {heating['total']:,.0f}\\,\\text{{Btu/h}}"
    ).replace(",", "{,}")
    result["subst_cooling_total"] = (
        f"q_t = q_s + q_l = {cooling['sensible']:,.0f} + {cooling['latent']:,.0f} "
        f"= {cooling['total']:,.0f}\\,\\text{{Btu/h}}"
    ).replace(",", "{,}")

    result["tree"] = _derivation_tree(run)
    result["cooling"]["sun"] = [
        dict(zip(("altitude", "azimuth"), solar_altitude_azimuth(
            p_used["latitude"], DECLINATION_DEG[p_used["design_month"]], hour - 0.5)))
        for hour in HOURS
    ]
    result["cooling"]["ua_house"] = cooling["ua_house"]
    result["sizing"] = suggest_sizes(
        heating["total"], cooling["total"], p_used["cooling_design_f"], cooling["sensible"])
    result["design"] = {
        "heating_f": p_used["heating_design_f"],
        "cooling_f": p_used["cooling_design_f"],
        "indoor_heating_f": p_used["indoor_heating_f"],
        "indoor_cooling_f": p_used["indoor_cooling_f"],
    }

    if detail:
        result["derivations"] = _derivations(run)
        result["uncertainty"] = _uncertainty(p, run, known_inputs or [])
        result["upgrades"] = _upgrades(p, run)
        result["orientations"] = _orientation_sweep(p)
    return result


# =============================================================================
# ASSEMBLY DETAIL AND SENSITIVITY STUDIES
# =============================================================================


def assembly_u(
    cavity_r: float,
    framing_fraction: float = 0.25,
    continuous_r: float = 0.0,
    stud_r: float = 4.4,
    other_layers_r: float = 2.5,
) -> Dict[str, float]:
    """
    U-factor of a framed assembly by the parallel path method.

    Heat takes two routes through a framed wall: through the insulated cavity and
    through the studs, which conduct far better. The whole-wall value is the
    area-weighted sum of both, so framing lowers performance below the cavity label.

    ---Parameters---
    cavity_r : float
        Insulation in the cavity (ft²·h·°F/Btu).
    framing_fraction : float
        Share of the wall that is framing, 0 to 1. About 0.25 for 16 inch spacing.
    continuous_r : float
        Continuous insulation outside the framing (ft²·h·°F/Btu).
    stud_r : float
        Resistance through the framing member. 4.4 for a 2x4, 6.9 for a 2x6.
    other_layers_r : float
        Siding, sheathing, gypsum, and air films together (ft²·h·°F/Btu).

    ---Returns---
    u_value : float
        Whole-assembly U-factor (Btu/h·ft²·°F).
    effective_r : float
        Whole-assembly R-value, one over the U-factor.
    u_cavity_path : float
        U-factor through the insulated path.
    u_framing_path : float
        U-factor through the framing path.

    ---LaTeX---
    U = \\frac{f}{R_o + R_c + R_s} + \\frac{1 - f}{R_o + R_c + R_{cav}}
    """
    if cavity_r < 0 or continuous_r < 0 or stud_r <= 0 or other_layers_r <= 0:
        raise ValueError("Assembly R-values must be positive.")
    if not 0 <= framing_fraction <= 1:
        raise ValueError("Framing fraction must be between 0 and 1.")
    u_cavity = 1.0 / (other_layers_r + continuous_r + cavity_r)
    u_framing = 1.0 / (other_layers_r + continuous_r + stud_r)
    u_value = framing_fraction * u_framing + (1 - framing_fraction) * u_cavity
    return {
        "u_value": u_value,
        "effective_r": 1.0 / u_value,
        "u_cavity_path": u_cavity,
        "u_framing_path": u_framing,
    }


# name: (label, unit, what it is, range as a function of the current value)
SWEEP_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "ach50": {
        "label": "Air leakage", "unit": "ACH50",
        "about": "Air changes per hour at 50 Pa. Only a blower door test measures this.",
        "range": lambda v: (max(1.0, round(v * 0.4, 1)), round(max(v * 2.0, 5.0), 1)),
    },
    "wall_r": {
        "label": "Wall insulation", "unit": "R (whole wall)",
        "about": "Whole-wall R-value including framing. Hidden inside the wall in most houses.",
        "range": lambda v: (max(2.0, round(v * 0.55, 1)), round(v * 1.8, 1)),
    },
    "ceiling_r": {
        "label": "Ceiling insulation", "unit": "R",
        "about": "Insulation at the attic floor or in the roof. Settled or missing insulation is common.",
        "range": lambda v: (max(3.0, round(v * 0.5, 1)), round(v * 2.0, 1)),
    },
    "window_scale_pct": {
        "label": "Window area", "unit": "% of entered",
        "about": "Scales all window area, for when the takeoff is approximate.",
        "range": lambda v: (60.0, 140.0),
    },
    "window_u": {
        "label": "Window U-factor", "unit": "Btu/h·ft²·°F",
        "about": "Whole-window heat flow. Unrated older windows are often uncertain.",
        "range": lambda v: (round(max(0.15, v * 0.6), 2), round(min(1.3, v * 1.5), 2)),
    },
    "window_shgc": {
        "label": "Window solar gain", "unit": "SHGC",
        "about": "Share of sunlight that becomes heat inside. Coatings are invisible to the eye.",
        "range": lambda v: (round(max(0.15, v * 0.6), 2), round(min(0.85, v * 1.4), 2)),
    },
    "duct_leakage_pct": {
        "label": "Duct leakage", "unit": "% per side",
        "about": "Leakage on each of the supply and return sides. Only a duct test measures this.",
        "range": lambda v: (2.0, max(round(v * 2.0), 15.0)),
    },
    "duct_r": {
        "label": "Duct insulation", "unit": "R",
        "about": "Insulation on ducts in unconditioned space.",
        "range": lambda v: (0.0, 12.0),
    },
    "occupants": {
        "label": "People at home", "unit": "people",
        "about": "Occupants at the design hour, which also sets typical internal gains.",
        "range": lambda v: (1.0, max(round(v * 2.0), 6.0)),
    },
    "heating_design_f": {
        "label": "Winter design temperature", "unit": "°F",
        "about": "Choosing a colder design temperature adds margin for cold snaps.",
        "range": lambda v: (round(v - 15.0), round(v + 8.0)),
    },
    "cooling_design_f": {
        "label": "Summer design temperature", "unit": "°F",
        "about": "Hotter sites, or a more cautious design, push this up.",
        "range": lambda v: (round(v - 5.0), round(v + 8.0)),
    },
    "indoor_heating_f": {
        "label": "Winter thermostat", "unit": "°F",
        "about": "What the household actually keeps it at in winter.",
        "range": lambda v: (62.0, 76.0),
    },
    "indoor_cooling_f": {
        "label": "Summer thermostat", "unit": "°F",
        "about": "What the household actually keeps it at in summer.",
        "range": lambda v: (70.0, 80.0),
    },
    "temperature_swing_f": {
        "label": "Allowed temperature swing", "unit": "°F",
        "about": "How far the room may drift above the thermostat at the peak.",
        "range": lambda v: (0.0, 5.0),
    },
    "rotation_deg": {
        "label": "House orientation", "unit": "degrees",
        "about": "Rotates the house clockwise, for production plans or an uncertain bearing.",
        "range": lambda v: (0.0, 315.0),
    },
}


def _sweep_current(p: Dict[str, Any], name: str) -> float:
    if name == "wall_r":
        return 1.0 / p["wall_u"]
    if name == "ceiling_r":
        return 1.0 / p["ceiling_u"]
    if name == "window_scale_pct":
        return 100.0
    return float(p[name])


def _sweep_apply(p: Dict[str, Any], name: str, value: float) -> Dict[str, Any]:
    if name == "wall_r":
        return _with_change(p, "wall_u", 1.0 / max(value, 0.1))
    if name == "ceiling_r":
        return _with_change(p, "ceiling_u", 1.0 / max(value, 0.1))
    if name == "window_scale_pct":
        base = p["window_pct_of_floor"] or 1.0
        return _with_change(p, "window_pct_of_floor", base * value / 100.0)
    return _with_change(p, name, value)


def _sweep_point(p: Dict[str, Any]) -> Dict[str, float]:
    run = _run(p)
    return {
        "heating": run["heating"]["total"],
        "cooling_total": run["cooling"]["total"],
        "cooling_sensible": run["cooling"]["sensible"],
        "cooling_latent": run["cooling"]["latent"],
    }


def get_sweep_parameters(inputs: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Every variable a study can sweep, with its current value and a starting range."""
    p = _normalize(inputs)
    out = {}
    for name, spec in SWEEP_PARAMETERS.items():
        current = _sweep_current(p, name)
        low, high = spec["range"](current)
        out[name] = {
            "label": spec["label"], "unit": spec["unit"], "about": spec["about"],
            "current": current, "low": min(low, current), "high": max(high, current),
        }
    return out


def _evenly(low: float, high: float, points: int) -> List[float]:
    if points < 2:
        raise ValueError("A sweep needs at least two points.")
    if high <= low:
        raise ValueError("The top of a sweep range must be above the bottom.")
    return [low + (high - low) * i / (points - 1) for i in range(points)]


def sensitivity_sweep(
    inputs: Dict[str, Any],
    parameter: str,
    low: Optional[float] = None,
    high: Optional[float] = None,
    points: int = 11,
) -> Dict[str, Any]:
    """
    Recalculate the whole house across a range of one uncertain variable.

    Each point is a full calculation with only that variable changed, so curved
    responses and interactions with the rest of the house are captured. No result
    is extrapolated from the base case.

    ---Parameters---
    inputs : dict
        The same input dictionary as calculate_hvac_loads.
    parameter : str
        A name from SWEEP_PARAMETERS, such as ach50 or wall_r.
    low : float
        Bottom of the range. Blank uses a starting range for this variable.
    high : float
        Top of the range. Blank uses a starting range for this variable.
    points : int
        Number of calculations across the range.

    ---Returns---
    values : list
        The swept values.
    heating : list
        Design heat loss at each value (Btu/h).
    cooling_total : list
        Total cooling load at each value (Btu/h).
    base_heating : float
        Design heat loss at the current value (Btu/h).
    base_cooling : float
        Total cooling load at the current value (Btu/h).

    ---LaTeX---
    q_j = f(x_1, \\ldots, x_i = v_j, \\ldots, x_n), \\quad j = 1 \\ldots N
    """
    if parameter not in SWEEP_PARAMETERS:
        raise ValueError(f"Unknown sweep variable '{parameter}'.")
    p = _normalize(inputs)
    spec = SWEEP_PARAMETERS[parameter]
    current = _sweep_current(p, parameter)
    default_low, default_high = spec["range"](current)
    start = default_low if low is None else float(low)
    stop = default_high if high is None else float(high)
    values = _evenly(start, stop, int(points))
    rows = [_sweep_point(_sweep_apply(p, parameter, v)) for v in values]
    base = _sweep_point(_sweep_apply(p, parameter, current))
    return {
        "parameter": parameter, "label": spec["label"], "unit": spec["unit"], "about": spec["about"],
        "values": values, "current": current,
        "heating": [r["heating"] for r in rows],
        "cooling_total": [r["cooling_total"] for r in rows],
        "cooling_sensible": [r["cooling_sensible"] for r in rows],
        "base_heating": base["heating"],
        "base_cooling": base["cooling_total"],
    }


def sensitivity_grid(
    inputs: Dict[str, Any],
    parameter_x: str,
    parameter_y: str,
    low_x: Optional[float] = None,
    high_x: Optional[float] = None,
    low_y: Optional[float] = None,
    high_y: Optional[float] = None,
    points: int = 7,
) -> Dict[str, Any]:
    """
    Recalculate the whole house across two uncertain variables at once.

    Shows how two unknowns combine, which a one-at-a-time sweep cannot.

    ---Parameters---
    inputs : dict
        The same input dictionary as calculate_hvac_loads.
    parameter_x : str
        Variable for the horizontal axis, from SWEEP_PARAMETERS.
    parameter_y : str
        Variable for the vertical axis, from SWEEP_PARAMETERS.
    low_x : float
        Bottom of the x range.
    high_x : float
        Top of the x range.
    low_y : float
        Bottom of the y range.
    high_y : float
        Top of the y range.
    points : int
        Calculations along each axis.

    ---Returns---
    x : list
        Values along the horizontal axis.
    y : list
        Values along the vertical axis.
    heating : list
        Design heat loss, indexed by y then x (Btu/h).
    cooling_total : list
        Total cooling load, indexed by y then x (Btu/h).

    ---LaTeX---
    q_{jk} = f(x_a = v_j,\\ x_b = v_k,\\ \\ldots)
    """
    for name in (parameter_x, parameter_y):
        if name not in SWEEP_PARAMETERS:
            raise ValueError(f"Unknown sweep variable '{name}'.")
    if parameter_x == parameter_y:
        raise ValueError("Choose two different variables.")
    p = _normalize(inputs)
    cx, cy = _sweep_current(p, parameter_x), _sweep_current(p, parameter_y)
    dx = SWEEP_PARAMETERS[parameter_x]["range"](cx)
    dy = SWEEP_PARAMETERS[parameter_y]["range"](cy)
    xs = _evenly(dx[0] if low_x is None else float(low_x), dx[1] if high_x is None else float(high_x), int(points))
    ys = _evenly(dy[0] if low_y is None else float(low_y), dy[1] if high_y is None else float(high_y), int(points))
    heating: List[List[float]] = []
    cooling: List[List[float]] = []
    for y in ys:
        at_y = _sweep_apply(p, parameter_y, y)
        row = [_sweep_point(_sweep_apply(at_y, parameter_x, x)) for x in xs]
        heating.append([r["heating"] for r in row])
        cooling.append([r["cooling_total"] for r in row])
    return {
        "parameter_x": parameter_x, "parameter_y": parameter_y,
        "label_x": SWEEP_PARAMETERS[parameter_x]["label"], "label_y": SWEEP_PARAMETERS[parameter_y]["label"],
        "unit_x": SWEEP_PARAMETERS[parameter_x]["unit"], "unit_y": SWEEP_PARAMETERS[parameter_y]["unit"],
        "x": xs, "y": ys, "current_x": cx, "current_y": cy, "heating": heating, "cooling_total": cooling,
    }


def threshold_crossings(values: Sequence[float], loads: Sequence[float], capacity: float) -> List[float]:
    """Values of a swept variable where the load equals a capacity, by interpolation."""
    crossings = []
    for (x0, y0), (x1, y1) in zip(zip(values, loads), zip(values[1:], loads[1:])):
        if (y0 - capacity) == 0:
            crossings.append(x0)
        elif (y0 - capacity) * (y1 - capacity) < 0:
            crossings.append(x0 + (x1 - x0) * (capacity - y0) / (y1 - y0))
    if loads and loads[-1] == capacity:
        crossings.append(values[-1])
    return crossings


# =============================================================================
# EQUIPMENT CHECK
# =============================================================================


def _capacity_curve(points: Sequence[Tuple[float, float]], t_f: float) -> float:
    """Piecewise-linear capacity with extrapolation beyond the rated points."""
    ordered = sorted(points)
    if len(ordered) == 1:
        return ordered[0][1]
    if t_f <= ordered[0][0]:
        (t0, c0), (t1, c1) = ordered[0], ordered[1]
    elif t_f >= ordered[-1][0]:
        (t0, c0), (t1, c1) = ordered[-2], ordered[-1]
    else:
        for (t0, c0), (t1, c1) in zip(ordered, ordered[1:]):
            if t0 <= t_f <= t1:
                break
    return max(c0 + (c1 - c0) * (t_f - t0) / (t1 - t0), 0.0)


def evaluate_equipment(
    heating_load: float,
    cooling_sensible: float,
    cooling_latent: float,
    heating_design_f: float,
    cooling_design_f: float,
    indoor_heating_f: float = 70.0,
    internal_gain_btuh: float = 2000.0,
    cooling_rated_btuh: Optional[float] = None,
    cooling_shr: float = 0.75,
    cooling_stages: str = "single",
    cooling_total_at_design: Optional[float] = None,
    cooling_sensible_at_design: Optional[float] = None,
    hp_cap_47: Optional[float] = None,
    hp_cap_17: Optional[float] = None,
    hp_cap_5: Optional[float] = None,
    hp_min_47: Optional[float] = None,
    hp_cop_47: float = 3.5,
    hp_cop_17: float = 2.3,
    hp_lockout_f: Optional[float] = None,
    furnace_output_btuh: Optional[float] = None,
    aux_kw: float = 0.0,
    bins_start_f: Optional[float] = None,
    bins_hours: Optional[List[float]] = None,
    bin_width_f: float = 5.0,
) -> Dict[str, Any]:
    """
    Compare proposed equipment with the design loads.

    ACCA's 2014 revision of Manual S sets a lower limit of 90% of the cooling
    load and different upper limits by compressor type. The upper limits here
    (115%, 120%, 130%, and 140% for furnaces) are commonly cited values, not read
    from the standard, so they are advisory: check Section N2 of the current
    edition for a final selection. Manufacturer data at the actual design
    conditions always beats the rated-point estimate here.

    ---Parameters---
    heating_load : float
        Design heat loss (Btu/h).
    cooling_sensible : float
        Sensible cooling load (Btu/h).
    cooling_latent : float
        Latent cooling load (Btu/h).
    heating_design_f : float
        Heating design temperature (°F).
    cooling_design_f : float
        Cooling design temperature (°F).
    indoor_heating_f : float
        Indoor winter temperature (°F).
    internal_gain_btuh : float
        Average internal gain, which sets where the house stops needing heat.
    cooling_rated_btuh : float
        Rated cooling capacity at 95 °F outdoor, 80/67 °F indoor (Btu/h).
    cooling_shr : float
        Equipment sensible heat ratio at 75 °F, 63 °F wet bulb entering air.
    cooling_stages : str
        single, two, or variable. Sets the usual oversizing limit.
    cooling_total_at_design : float
        Total capacity from the maker's table at design conditions (Btu/h).
    cooling_sensible_at_design : float
        Sensible capacity from the maker's table at design conditions (Btu/h).
    hp_cap_47 : float
        Heat pump maximum capacity at 47 °F (Btu/h).
    hp_cap_17 : float
        Heat pump maximum capacity at 17 °F (Btu/h).
    hp_cap_5 : float
        Heat pump maximum capacity at 5 °F, for cold-climate models (Btu/h).
    hp_min_47 : float
        Heat pump minimum modulated capacity at 47 °F (Btu/h).
    hp_cop_47 : float
        Coefficient of performance at 47 °F.
    hp_cop_17 : float
        Coefficient of performance at 17 °F.
    hp_lockout_f : float
        Outdoor temperature below which the compressor turns off (°F).
    furnace_output_btuh : float
        Furnace output, input times AFUE (Btu/h).
    aux_kw : float
        Electric backup heat (kW).
    bins_start_f : float
        Lower edge of the first temperature bin (°F).
    bins_hours : list
        Hours per year in each temperature bin.
    bin_width_f : float
        Temperature bin width (°F).

    ---Returns---
    balance_point_f : float
        Outdoor temperature where heat pump capacity equals the house load (°F).
    backup_kw_at_design : float
        Backup heat needed at the heating design temperature (kW).
    heat_pump_energy_share : float
        Share of annual heat delivered by the compressor.
    cooling_total_pct : float
        Cooling capacity as a percent of the total load (%).
    cooling_sensible_pct : float
        Sensible capacity, plus half of any excess latent capacity, as a percent
        of the sensible load (%).
    furnace_pct : float
        Furnace output as a percent of the heating load (%).

    ---LaTeX---
    L(T) = q_{heat}\\frac{T_0 - T}{T_0 - T_d}, \\quad T_0 = T_i - \\frac{q_{int}}{UA}
    Q_{design} = Q_{rated}[1 - 0.007(T_d - 95)][1 - 0.0135(67 - T_{wb})]
    Q_{s,usable} = Q_s + 0.5\\max(Q_l - q_l, 0)
    """
    if heating_load <= 0:
        raise ValueError("The heating load must be above zero.")
    delta_t = indoor_heating_f - heating_design_f
    if delta_t <= 0:
        raise ValueError("The heating design temperature must be below indoor.")
    ua = heating_load / delta_t
    t_zero = indoor_heating_f - internal_gain_btuh / ua
    t_zero = max(t_zero, heating_design_f + 5.0)

    def load_at(t_f: float) -> float:
        return max(heating_load * (t_zero - t_f) / (t_zero - heating_design_f), 0.0)

    checks: List[Dict[str, Any]] = []
    out: Dict[str, Any] = {
        "t_zero_load_f": t_zero,
        "balance_point_f": None,
        "backup_kw_at_design": None,
        "heat_pump_energy_share": None,
        "cooling_total_pct": None,
        "furnace_pct": None,
    }

    total_load = cooling_sensible + cooling_latent
    has_cooling = bool(cooling_total_at_design or cooling_rated_btuh)
    if has_cooling:
        if cooling_total_at_design:
            cap_total = float(cooling_total_at_design)
            cap_sensible = float(cooling_sensible_at_design or cap_total * cooling_shr)
            source = "manufacturer table"
        else:
            cap_total = float(cooling_rated_btuh) * rated_to_design_factor(cooling_design_f)
            cap_sensible = cap_total * cooling_shr
            source = "estimate from rated capacity"
        cap_latent = max(cap_total - cap_sensible, 0.0)
        cap_usable = effective_sensible_capacity(cap_sensible, cap_latent, cooling_latent)
        pct = 100.0 * cap_total / total_load if total_load > 0 else 0.0
        limit = {"single": 115.0, "two": 120.0, "variable": 130.0}.get(cooling_stages, 115.0)
        out.update({
            "cooling_total_pct": pct,
            "cooling_capacity_total": cap_total,
            "cooling_capacity_sensible": cap_sensible,
            "cooling_capacity_latent": cap_latent,
            "cooling_source": source,
            "cooling_limit_pct": limit,
            "cooling_capacity_usable_sensible": cap_usable,
            "cooling_sensible_pct": 100.0 * cap_usable / cooling_sensible if cooling_sensible > 0 else 0.0,
            "cooling_latent_pct": 100.0 * cap_latent / cooling_latent if cooling_latent > 0 else None,
        })
        checks.append({"name": "Cooling capacity meets the load",
                       "ok": pct >= 90.0, "kind": "required",
                       "detail": f"{pct:.0f}% of total load"})
        checks.append({"name": f"Cooling not oversized past about {limit:.0f}%",
                       "ok": pct <= limit, "kind": "advisory",
                       "detail": f"{pct:.0f}% of total load"})
        checks.append({"name": "Sensible capacity meets the sensible load",
                       "ok": out["cooling_sensible_pct"] >= 90.0, "kind": "required",
                       "detail": f"{out['cooling_sensible_pct']:.0f}%"})
        if cooling_latent > 0:
            checks.append({"name": "Latent capacity meets the moisture load",
                           "ok": cap_latent >= cooling_latent, "kind": "advisory",
                           "detail": f"{cap_latent:,.0f} of {cooling_latent:,.0f} Btu/h"})

    has_hp = bool(hp_cap_47 and hp_cap_17)
    chart = None
    if has_hp:
        points = [(47.0, float(hp_cap_47)), (17.0, float(hp_cap_17))]
        if hp_cap_5:
            points.append((5.0, float(hp_cap_5)))
        min_ratio = (float(hp_min_47) / float(hp_cap_47)) if hp_min_47 else None
        lockout = float(hp_lockout_f) if hp_lockout_f not in (None, "") else None

        def cap_at(t_f: float) -> float:
            if lockout is not None and t_f < lockout:
                return 0.0
            return _capacity_curve(points, t_f)

        def cop_at(t_f: float) -> float:
            slope = (hp_cop_47 - hp_cop_17) / 30.0
            return max(1.0, hp_cop_47 + slope * (t_f - 47.0))

        balance = None
        t = 70.0
        previous_margin = cap_at(t) - load_at(t)
        while t > -60.0:
            t -= 0.1
            margin = cap_at(t) - load_at(t)
            if margin < 0 <= previous_margin:
                balance = t + 0.05
                break
            previous_margin = margin
        at_design = cap_at(heating_design_f)
        shortfall = max(heating_load - at_design, 0.0)
        backup_kw = shortfall / KW_BTUH
        out.update({
            "balance_point_f": balance,
            "hp_capacity_at_design": at_design,
            "hp_pct_of_load_at_design": 100.0 * at_design / heating_load,
            "backup_kw_at_design": backup_kw,
        })
        checks.append({"name": "Heat pump alone carries the design load",
                       "ok": shortfall <= 0, "kind": "advisory",
                       "detail": (f"Balance point {balance:.0f} °F" if balance is not None
                                  else "No balance point above -60 °F")})
        checks.append({"name": "Backup heat covers the shortfall at design",
                       "ok": (aux_kw * KW_BTUH + (furnace_output_btuh or 0.0)) >= shortfall - 1.0,
                       "kind": "required",
                       "detail": f"Needs {backup_kw:.1f} kW, has {aux_kw:.1f} kW"})

        if bins_hours and bins_start_f is not None:
            heat_hp = heat_backup = kwh_hp = kwh_backup = cycling = heating_hours = 0.0
            below_balance = 0.0
            for i, hours in enumerate(bins_hours):
                mid = bins_start_f + (i + 0.5) * bin_width_f
                load = load_at(mid)
                if load <= 0:
                    continue
                heating_hours += hours
                capacity = cap_at(mid)
                delivered = min(load, capacity)
                extra = load - delivered
                heat_hp += delivered * hours
                heat_backup += extra * hours
                kwh_hp += delivered * hours / KW_BTUH / cop_at(mid)
                kwh_backup += extra * hours / KW_BTUH
                if extra > 1:
                    below_balance += hours
                if min_ratio is not None and capacity * min_ratio > load:
                    cycling += hours
            total_heat = heat_hp + heat_backup
            out.update({
                "heat_pump_energy_share": heat_hp / total_heat if total_heat > 0 else None,
                "annual_heat_mbtu": total_heat / 1e6,
                "annual_kwh_compressor": kwh_hp,
                "annual_kwh_backup": kwh_backup,
                "hours_below_balance": below_balance,
                "heating_hours": heating_hours,
                "cycling_hours": cycling if min_ratio is not None else None,
                "seasonal_cop": total_heat / KW_BTUH / (kwh_hp + kwh_backup)
                if (kwh_hp + kwh_backup) > 0 else None,
            })
        low = min(heating_design_f - 15.0, -10.0)
        temps = [low + i * 2.5 for i in range(int((70.0 - low) / 2.5) + 1)]
        chart = {
            "t": temps,
            "load": [load_at(t) for t in temps],
            "capacity": [cap_at(t) for t in temps],
        }

    if furnace_output_btuh:
        pct = 100.0 * float(furnace_output_btuh) / heating_load
        out["furnace_pct"] = pct
        checks.append({"name": "Furnace output meets the heat loss",
                       "ok": pct >= 100.0, "kind": "required", "detail": f"{pct:.0f}% of load"})
        checks.append({"name": "Furnace not oversized past about 140%",
                       "ok": pct <= 140.0, "kind": "advisory", "detail": f"{pct:.0f}% of load"})

    out["checks"] = checks
    out["chart"] = chart
    return out


# =============================================================================
# FUEL BILL CROSS-CHECK
# =============================================================================

FUEL_BTU = {
    "gas_therm": 100000.0,
    "gas_ccf": 103000.0,
    "propane_gal": 91500.0,
    "oil_gal": 138500.0,
    "electric_kwh": 3412.14,
}


def bill_check(
    usage: float,
    fuel: str,
    efficiency_pct: float,
    degree_days: float,
    heating_design_f: float,
    baseline_usage: float = 0.0,
) -> Dict[str, Any]:
    """
    Estimate design heat loss from a winter fuel bill.

    Fuel burned for heat divided by the month's degree days gives a measured
    heat-loss coefficient. It includes real leakage and duct losses, and needs
    no assumptions about insulation, so it is an independent check on the model.

    ---Parameters---
    usage : float
        Fuel used in a cold billing period, in the fuel's own unit.
    fuel : str
        gas_therm, gas_ccf, propane_gal, oil_gal, or electric_kwh.
    efficiency_pct : float
        Heating equipment efficiency, AFUE or 100 for resistance heat (%).
    degree_days : float
        Base-65 °F heating degree days in the same billing period.
    heating_design_f : float
        Heating design temperature (°F).
    baseline_usage : float
        Non-heating use for the same period length, such as summer gas use.

    ---Returns---
    measured_ua : float
        Heat loss per °F, base 65 °F (Btu/h·°F).
    measured_design_load : float
        Implied heat loss at the design temperature (Btu/h).

    ---LaTeX---
    UA_{bill} = \\frac{(E - E_{base}) \\, h_{fuel} \\, \\eta}{24 \\, HDD_{65}}
    q_{bill} = UA_{bill} (65 - T_d)
    """
    if fuel not in FUEL_BTU:
        raise ValueError(f"Unknown fuel '{fuel}'.")
    if usage <= 0:
        raise ValueError("Fuel use must be above zero.")
    if degree_days <= 0:
        raise ValueError("Degree days must be above zero.")
    if not 0 < efficiency_pct <= 400:
        raise ValueError("Efficiency must be between 0 and 400%.")
    if baseline_usage < 0 or baseline_usage >= usage:
        raise ValueError("Baseline use must be below total use and not negative.")
    heat_btu = (usage - baseline_usage) * FUEL_BTU[fuel] * efficiency_pct / 100.0
    ua = heat_btu / (24.0 * degree_days)
    return {
        "measured_ua": ua,
        "measured_design_load": ua * (65.0 - heating_design_f),
        "subst_measured_ua": (
            f"UA = \\frac{{({usage:g} - {baseline_usage:g}) \\times {FUEL_BTU[fuel]:,.0f} \\times "
            f"{efficiency_pct / 100.0:.2f}}}{{24 \\times {degree_days:g}}} = {ua:,.0f}"
        ).replace(",", "{,}"),
    }
