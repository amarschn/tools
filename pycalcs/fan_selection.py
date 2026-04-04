"""
Fan type selection via specific-speed analysis and Cordier-based sizing.

This module answers the front-end question "what fan family should I start
with?" for low-compressibility air-moving applications. It is intentionally
architecture-level rather than vendor-model-level: the calculations compare
axial, mixed-flow, forward-curved centrifugal, and backward-curved centrifugal
fans at a common duty point, then return sizing and suitability context for
handoff into detailed fan-curve comparison.

The model combines:
- Dimensionless specific speed and specific diameter
- A Cordier-line diameter estimate
- Family-level efficiency and curve-shape heuristics
- Optional machine constraints (fixed RPM or fixed wheel diameter)
- Optional passage-geometry checks using target velocity or known area

References:
    Balje, O.E. (1981). Turbomachines: A Guide to Design, Selection,
        and Theory. John Wiley & Sons.
    Dixon, S.L. & Hall, C.A. (2014). Fluid Mechanics and Thermodynamics
        of Turbomachinery, 7th ed. Butterworth-Heinemann.
    Eck, B. (1973). Fans. Pergamon Press.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_AIR_DENSITY = 1.204  # kg/m^3 at 20 C, sea level

_CORD_A = 0.833
_CORD_B = -0.524
_CORD_C = 0.008

_ETA_A = 0.90
_ETA_B = 0.017
_ETA_C = -0.059

_MAX_TYPICAL_EFFICIENCY = 0.85

_PASSAGE_PREFS = {
    "axial": {
        "velocity_min": 4.0,
        "velocity_max": 14.0,
        "velocity_optimal": 9.0,
    },
    "mixed": {
        "velocity_min": 6.0,
        "velocity_max": 18.0,
        "velocity_optimal": 12.0,
    },
    "radial": {
        "velocity_min": 8.0,
        "velocity_max": 24.0,
        "velocity_optimal": 16.0,
    },
}

_AREA_MATCH_PREFS = {
    "ratio_min": 0.72,
    "ratio_max": 1.38,
    "ratio_optimal": 1.0,
}

_GEOMETRY_DEFAULTS = {
    "axial": {
        "basis_label": "Rotor annulus",
        "section_type": "rotor_annulus",
        "hub_tip_ratio": 0.36,
        "blockage_factor": 0.93,
        "centerbody_label": "Hub / motor pod",
        "flow_path_summary": (
            "Uses the blade annulus at the axial rotor plane. The centerbody is treated as "
            "a hub or motor pod that blocks the middle of the disc."
        ),
    },
    "mixed": {
        "basis_label": "Rotor annulus",
        "section_type": "rotor_annulus",
        "hub_tip_ratio": 0.50,
        "blockage_factor": 0.91,
        "centerbody_label": "Hub / cone",
        "flow_path_summary": (
            "Uses the mixed-flow rotor annulus. The larger centerbody reflects the stronger "
            "hub and cone needed in a more pressure-capable inline wheel."
        ),
    },
    "centrifugal_bc": {
        "basis_label": "Inlet eye annulus",
        "section_type": "inlet_eye_annulus",
        "eye_outer_ratio": 0.58,
        "eye_hub_ratio": 0.35,
        "blockage_factor": 0.89,
        "centerbody_label": "Eye hub / shaft nose",
        "flow_path_summary": (
            "Uses the centrifugal inlet eye as the reference flow section. The scroll and "
            "rectangular discharge are not modeled here."
        ),
    },
    "centrifugal_fc": {
        "basis_label": "Inlet eye annulus",
        "section_type": "inlet_eye_annulus",
        "eye_outer_ratio": 0.72,
        "eye_hub_ratio": 0.46,
        "blockage_factor": 0.86,
        "centerbody_label": "Eye hub / shaft nose",
        "flow_path_summary": (
            "Uses the centrifugal inlet eye as the reference flow section. Forward-curved "
            "wheels are treated as having a larger eye and slightly higher blockage."
        ),
    },
}

_STANDARD_DRIVE_SPEEDS = [
    {"rpm": 900.0, "label": "8-pole direct drive"},
    {"rpm": 1200.0, "label": "6-pole direct drive"},
    {"rpm": 1500.0, "label": "4-pole direct drive (50 Hz)"},
    {"rpm": 1800.0, "label": "4-pole direct drive (60 Hz)"},
    {"rpm": 3000.0, "label": "2-pole direct drive (50 Hz)"},
    {"rpm": 3600.0, "label": "2-pole direct drive (60 Hz)"},
]

_NOMINAL_DIAMETER_SERIES_MM = [
    100,
    125,
    160,
    180,
    200,
    224,
    250,
    280,
    315,
    355,
    400,
    450,
    500,
    560,
    630,
    710,
    800,
    900,
    1000,
    1120,
    1250,
    1400,
    1600,
    1800,
    2000,
]


FAN_TYPES: Dict[str, Dict[str, Any]] = {
    "centrifugal_fc": {
        "name": "Forward-Curved Centrifugal",
        "short_name": "FC Centrifugal",
        "family": "radial",
        "family_label": "Radial",
        "ns_min": 0.30,
        "ns_max": 1.20,
        "ns_optimal": 0.60,
        "typical_peak_efficiency": 0.65,
        "bep_flow_fraction": 0.55,
        "power_overloading": True,
        "color": "#c27b2b",
        "description": (
            "Compact and inexpensive, with a pressure hump that demands more "
            "care around stall margin and motor sizing."
        ),
        "packaging_signature": "90-degree turn, shallow wheel depth, compact face area.",
        "tip_speed_quiet_ms": 18.0,
        "tip_speed_alert_ms": 40.0,
        "advantages": [
            "Compact scroll packaging",
            "Low nominal wheel speed",
            "Lower first cost",
            "Good flow per frontal size",
        ],
        "limitations": [
            "Lower efficiency",
            "Overloading power curve",
            "Hump-region stall risk",
        ],
        "applications": [
            "Residential HVAC",
            "Packaged units",
            "Furnace blowers",
        ],
    },
    "centrifugal_bc": {
        "name": "Backward-Curved Centrifugal",
        "short_name": "BC Centrifugal",
        "family": "radial",
        "family_label": "Radial",
        "ns_min": 0.30,
        "ns_max": 1.50,
        "ns_optimal": 0.80,
        "typical_peak_efficiency": 0.85,
        "bep_flow_fraction": 0.70,
        "power_overloading": False,
        "color": "#56616e",
        "description": (
            "The efficiency-first radial option, usually favored when stable "
            "operation and non-overloading power matter."
        ),
        "packaging_signature": "90-degree turn, deeper housing, compact face area.",
        "tip_speed_quiet_ms": 20.0,
        "tip_speed_alert_ms": 48.0,
        "advantages": [
            "Highest efficiency ceiling",
            "Non-overloading power curve",
            "Stable operating range",
            "Good restrictive-system tolerance",
        ],
        "limitations": [
            "Larger package than FC",
            "Higher cost than FC",
            "Requires a 90-degree turn through the wheel",
        ],
        "applications": [
            "Commercial air handlers",
            "Clean rooms",
            "Industrial ventilation",
        ],
    },
    "mixed": {
        "name": "Mixed Flow",
        "short_name": "Mixed Flow",
        "family": "mixed",
        "family_label": "Mixed Flow",
        "ns_min": 0.80,
        "ns_max": 3.00,
        "ns_optimal": 1.80,
        "typical_peak_efficiency": 0.84,
        "bep_flow_fraction": 0.65,
        "power_overloading": False,
        "color": "#0f766e",
        "description": (
            "Bridges axial and radial behavior: more pressure capability than "
            "axial with a more compact inline package than centrifugal fans."
        ),
        "packaging_signature": "Inline package, moderate depth, medium face area.",
        "tip_speed_quiet_ms": 24.0,
        "tip_speed_alert_ms": 52.0,
        "advantages": [
            "Inline package",
            "Good pressure capability",
            "Strong efficiency",
            "Useful bridge architecture",
        ],
        "limitations": [
            "Less catalog depth than axial or BC",
            "Can be costlier than axial",
            "Less tolerant of severe fouling than radial",
        ],
        "applications": [
            "Duct boosting",
            "Compact HVAC",
            "Parking garage ventilation",
        ],
    },
    "axial": {
        "name": "Axial",
        "short_name": "Axial",
        "family": "axial",
        "family_label": "Axial",
        "ns_min": 2.00,
        "ns_max": 8.00,
        "ns_optimal": 3.50,
        "typical_peak_efficiency": 0.82,
        "bep_flow_fraction": 0.65,
        "power_overloading": False,
        "color": "#2563eb",
        "description": (
            "High-flow inline architecture with limited pressure rise, usually "
            "best when packaging rewards a large low-resistance flow passage."
        ),
        "packaging_signature": "Straight-through inline, low depth, large face area.",
        "tip_speed_quiet_ms": 22.0,
        "tip_speed_alert_ms": 50.0,
        "advantages": [
            "Compact inline mounting",
            "High flow capacity",
            "Large outlet area",
            "Simple flow path",
        ],
        "limitations": [
            "Limited pressure rise",
            "Stall risk at low flow",
            "Tip-speed noise when heavily loaded",
        ],
        "applications": [
            "General ventilation",
            "Electronics cooling",
            "Cooling towers",
            "Tunnel fans",
        ],
    },
}


# =============================================================================
# BASIC HELPERS
# =============================================================================


def _validate_positive(name: str, value: float, *, allow_zero: bool = False) -> float:
    """Validate that a numeric quantity is finite and positive.

    ---Parameters---
    name : str
        Human-readable quantity name for exception messages.
    value : float
        Numeric value to validate.
    allow_zero : bool
        When True, zero is accepted. Negative values still raise.

    ---Returns---
    validated_value : float
        The validated numeric value.

    ---LaTeX---
    x > 0
    """
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if allow_zero:
        if value < 0:
            raise ValueError(f"{name} must be greater than or equal to zero.")
    elif value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return value


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a value to a closed interval.

    ---Parameters---
    value : float
        Value to clamp.
    lower : float
        Lower bound.
    upper : float
        Upper bound.

    ---Returns---
    clamped_value : float
        Value limited to the interval [lower, upper].

    ---LaTeX---
    x_{clamped} = \\min(\\max(x, x_{min}), x_{max})
    """
    return max(lower, min(upper, value))


def _round_if_number(value: Optional[float], digits: int = 3) -> Optional[float]:
    """Round a numeric value when present.

    ---Parameters---
    value : float or None
        Numeric value to round.
    digits : int
        Decimal places for rounding.

    ---Returns---
    rounded_value : float or None
        Rounded numeric value, or None when the input is None.

    ---LaTeX---
    x_r = \\operatorname{round}(x, n)
    """
    if value is None:
        return None
    return round(value, digits)


def _range_fit_log(value: float, minimum: float, maximum: float, optimal: float) -> float:
    """Return a 0-1 log-space fit score for a quantity with a preferred band.

    ---Parameters---
    value : float
        Evaluated quantity.
    minimum : float
        Lower bound of the preferred band.
    maximum : float
        Upper bound of the preferred band.
    optimal : float
        Preferred center of the band.

    ---Returns---
    fit_score : float
        Score from 0 to 1, where 1 is best fit.

    ---LaTeX---
    s = f\\left(\\ln x, \\ln x_{min}, \\ln x_{max}, \\ln x_{opt}\\right)
    """
    _validate_positive("value", value)
    _validate_positive("minimum", minimum)
    _validate_positive("maximum", maximum)
    _validate_positive("optimal", optimal)

    ln_value = math.log(value)
    ln_min = math.log(minimum)
    ln_max = math.log(maximum)
    ln_opt = math.log(optimal)
    band = max(ln_max - ln_min, 1.0e-9)

    if minimum <= value <= maximum:
        distance = abs(ln_value - ln_opt)
        return _clamp(1.0 - 0.18 * distance / band, 0.82, 1.0)

    outside_distance = (ln_min - ln_value) / band if value < minimum else (ln_value - ln_max) / band
    return _clamp(0.72 - 0.45 * outside_distance, 0.08, 0.72)


def _tip_speed_fit(tip_speed_ms: float) -> float:
    """Rate tip speed as a soft acoustic / mechanical suitability proxy.

    ---Parameters---
    tip_speed_ms : float
        Impeller tip speed in m/s.

    ---Returns---
    fit_score : float
        Score from 0 to 1, where lower tip speeds are favored.

    ---LaTeX---
    U_{tip} = \\frac{\\pi D N}{60}
    """
    _validate_positive("tip speed", tip_speed_ms)
    if tip_speed_ms <= 20.0:
        return 1.0
    if tip_speed_ms <= 35.0:
        return 0.9
    if tip_speed_ms <= 50.0:
        return 0.75
    if tip_speed_ms <= 65.0:
        return 0.55
    return _clamp(0.55 * 65.0 / tip_speed_ms, 0.15, 0.55)


def _equivalent_diameter_from_area(area_m2: float) -> float:
    """Compute a circular equivalent diameter from area.

    ---Parameters---
    area_m2 : float
        Passage area in square metres.

    ---Returns---
    equivalent_diameter_m : float
        Circular equivalent diameter in metres.

    ---LaTeX---
    D_{eq} = \\sqrt{\\frac{4A}{\\pi}}
    """
    _validate_positive("passage area", area_m2)
    return math.sqrt(4.0 * area_m2 / math.pi)


def _annulus_area(outer_diameter_m: float, inner_diameter_m: float) -> float:
    """Compute annulus area from outer and inner diameters.

    ---Parameters---
    outer_diameter_m : float
        Outer diameter in metres.
    inner_diameter_m : float
        Inner blocked diameter in metres.

    ---Returns---
    annulus_area_m2 : float
        Flow area of the annulus in square metres.

    ---LaTeX---
    A = \\frac{\\pi}{4} \\left(D_o^2 - D_i^2\\right)
    """
    _validate_positive("outer diameter", outer_diameter_m)
    _validate_positive("inner diameter", inner_diameter_m, allow_zero=True)
    if inner_diameter_m >= outer_diameter_m:
        raise ValueError("Inner diameter must be smaller than the outer diameter.")
    return math.pi * 0.25 * (outer_diameter_m ** 2 - inner_diameter_m ** 2)


def estimate_reference_geometry(
    type_id: str,
    wheel_outer_diameter_m: float,
    flow_m3s: float,
    geometry_overrides: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Estimate a family-specific reference flow section and effective flow area.

    Axial and mixed-flow fans use the rotor annulus as the reference section.
    Centrifugal fans use the inlet eye annulus because that is the most direct
    flow-area section that can be estimated from wheel diameter alone.

    ---Parameters---
    type_id : str
        Fan type identifier.
    wheel_outer_diameter_m : float
        Outer impeller diameter in metres.
    flow_m3s : float
        Volume flow rate in m^3/s.
    geometry_overrides : dict or str or None
        Optional per-type geometry override payload. May be passed as a Python
        dict or a JSON string. Supported keys are:
        ``hub_tip_ratio`` or ``hub_diameter_m`` for axial and mixed-flow, and
        ``eye_outer_ratio``, ``eye_hub_ratio``, ``eye_outer_diameter_m``, or
        ``eye_hub_diameter_m`` for centrifugal types.

    ---Returns---
    geometry : dict
        JSON-serialisable geometry payload with basis labels, hub or eye
        diameters, gross and effective flow area, blockage factor, equivalent
        diameter, and reference-section velocity.

    ---LaTeX---
    A_{gross} = \\frac{\\pi}{4} \\left(D_o^2 - D_i^2\\right)
    A_{eff} = \\phi_b A_{gross}
    V_{ref} = \\frac{Q}{A_{eff}}
    """
    _validate_positive("wheel diameter", wheel_outer_diameter_m)
    _validate_positive("flow", flow_m3s)
    if type_id not in FAN_TYPES:
        raise ValueError(f"Unknown fan type '{type_id}'.")
    if type_id not in _GEOMETRY_DEFAULTS:
        raise ValueError(f"No geometry defaults defined for fan type '{type_id}'.")

    defaults = _GEOMETRY_DEFAULTS[type_id]
    overrides = _normalize_geometry_overrides(geometry_overrides)
    type_override = overrides.get(type_id, {})
    family = FAN_TYPES[type_id]["family"]
    blockage_factor = defaults["blockage_factor"]
    override_active = False
    override_tokens: List[str] = []

    if defaults["section_type"] == "rotor_annulus":
        reference_outer_diameter_m = wheel_outer_diameter_m
        if type_override.get("hub_diameter_m") is not None:
            reference_inner_diameter_m = float(type_override["hub_diameter_m"])
            geometry_ratio = reference_inner_diameter_m / wheel_outer_diameter_m
            override_active = True
            override_tokens.append("hub diameter")
        elif type_override.get("hub_tip_ratio") is not None:
            geometry_ratio = float(type_override["hub_tip_ratio"])
            reference_inner_diameter_m = wheel_outer_diameter_m * geometry_ratio
            override_active = True
            override_tokens.append("hub ratio")
        else:
            geometry_ratio = defaults["hub_tip_ratio"]
            reference_inner_diameter_m = wheel_outer_diameter_m * geometry_ratio
        eye_outer_diameter_m = None
        geometry_ratio_label = "Hub / tip ratio"
    else:
        if type_override.get("eye_outer_diameter_m") is not None:
            eye_outer_diameter_m = float(type_override["eye_outer_diameter_m"])
            geometry_ratio = eye_outer_diameter_m / wheel_outer_diameter_m
            override_active = True
            override_tokens.append("eye diameter")
        elif type_override.get("eye_outer_ratio") is not None:
            geometry_ratio = float(type_override["eye_outer_ratio"])
            eye_outer_diameter_m = wheel_outer_diameter_m * geometry_ratio
            override_active = True
            override_tokens.append("eye ratio")
        else:
            geometry_ratio = defaults["eye_outer_ratio"]
            eye_outer_diameter_m = wheel_outer_diameter_m * geometry_ratio
        reference_outer_diameter_m = eye_outer_diameter_m
        if type_override.get("eye_hub_diameter_m") is not None:
            reference_inner_diameter_m = float(type_override["eye_hub_diameter_m"])
            override_active = True
            override_tokens.append("eye hub diameter")
        elif type_override.get("eye_hub_ratio") is not None:
            reference_inner_diameter_m = eye_outer_diameter_m * float(type_override["eye_hub_ratio"])
            override_active = True
            override_tokens.append("eye hub ratio")
        else:
            reference_inner_diameter_m = eye_outer_diameter_m * defaults["eye_hub_ratio"]
        geometry_ratio_label = "Eye / wheel ratio"

    _validate_positive("reference outer diameter", reference_outer_diameter_m)
    _validate_positive("reference inner diameter", reference_inner_diameter_m, allow_zero=True)
    if geometry_ratio <= 0.0 or geometry_ratio >= 1.0:
        raise ValueError(f"{type_id} geometry ratio must stay between zero and one.")
    if reference_inner_diameter_m >= reference_outer_diameter_m:
        raise ValueError(f"{type_id} inner geometry diameter must be smaller than the reference outer diameter.")

    gross_flow_area_m2 = _annulus_area(reference_outer_diameter_m, reference_inner_diameter_m)
    effective_flow_area_m2 = blockage_factor * gross_flow_area_m2
    reference_velocity_ms = flow_m3s / effective_flow_area_m2
    effective_equivalent_diameter_m = _equivalent_diameter_from_area(effective_flow_area_m2)

    if defaults["section_type"] == "rotor_annulus":
        area_formula_note = (
            "Rotor annulus area uses the impeller outer diameter and a family-default hub ratio."
        )
    else:
        area_formula_note = (
            "Inlet eye area uses the eye diameter inferred from wheel OD and a family-default eye hub ratio."
        )

    return {
        "section_type": defaults["section_type"],
        "basis_label": defaults["basis_label"],
        "centerbody_label": defaults["centerbody_label"],
        "family": family,
        "override_active": override_active,
        "override_note": (
            f"Custom geometry override active: {', '.join(override_tokens)}."
            if override_active
            else "Using family-default geometry ratios."
        ),
        "wheel_outer_diameter_m": round(wheel_outer_diameter_m, 6),
        "reference_outer_diameter_m": round(reference_outer_diameter_m, 6),
        "reference_inner_diameter_m": round(reference_inner_diameter_m, 6),
        "eye_outer_diameter_m": _round_if_number(eye_outer_diameter_m, 6),
        "geometry_ratio": round(geometry_ratio, 4),
        "geometry_ratio_label": geometry_ratio_label,
        "blockage_factor": round(blockage_factor, 4),
        "gross_flow_area_m2": round(gross_flow_area_m2, 6),
        "effective_flow_area_m2": round(effective_flow_area_m2, 6),
        "effective_equivalent_diameter_m": round(effective_equivalent_diameter_m, 6),
        "reference_velocity_ms": round(reference_velocity_ms, 4),
        "flow_path_summary": defaults["flow_path_summary"],
        "area_formula_note": area_formula_note,
    }


def _normalize_geometry_overrides(geometry_overrides: Optional[Any]) -> Dict[str, Dict[str, float]]:
    """Normalize optional geometry override input into a plain dict.

    ---Parameters---
    geometry_overrides : dict or str or None
        Optional override payload as a Python dict or JSON string.

    ---Returns---
    overrides : dict
        Plain dict keyed by fan type id.

    ---LaTeX---
    G = \\operatorname{normalize}(G_{in})
    """
    if geometry_overrides is None or geometry_overrides == "":
        return {}
    if isinstance(geometry_overrides, str):
        loaded = json.loads(geometry_overrides)
    else:
        loaded = geometry_overrides
    if not isinstance(loaded, dict):
        raise ValueError("geometry_overrides must be a dict, JSON string, or None.")

    normalized: Dict[str, Dict[str, float]] = {}
    for type_id, payload in loaded.items():
        if type_id not in FAN_TYPES or not isinstance(payload, dict):
            continue
        item: Dict[str, float] = {}
        for key in [
            "hub_tip_ratio",
            "hub_diameter_m",
            "eye_outer_ratio",
            "eye_hub_ratio",
            "eye_outer_diameter_m",
            "eye_hub_diameter_m",
        ]:
            value = payload.get(key)
            if value is None or value == "":
                continue
            numeric = float(value)
            _validate_positive(key, numeric)
            item[key] = numeric
        if item:
            normalized[type_id] = item
    return normalized


def _dominant_family(type_id: str) -> str:
    """Map a type identifier to its family key.

    ---Parameters---
    type_id : str
        Fan type identifier.

    ---Returns---
    family : str
        Family key: axial, mixed, or radial.

    ---LaTeX---
    f = f(type)
    """
    return FAN_TYPES[type_id]["family"]


# =============================================================================
# AIR DENSITY
# =============================================================================


def compute_air_density(temperature_c: float = 20.0, elevation_m: float = 0.0) -> float:
    """
    Compute dry-air density from temperature and elevation.

    Uses a standard-atmosphere barometric relation for pressure versus
    elevation, then applies the ideal gas law.

    ---Parameters---
    temperature_c : float
        Air temperature in degrees Celsius.
    elevation_m : float
        Elevation above mean sea level in metres.

    ---Returns---
    density_kg_m3 : float
        Dry-air density in kg/m^3.

    ---LaTeX---
    \\rho = \\frac{P}{R_{specific} T}
    P = 101325 \\left(1 - 2.25577 \\times 10^{-5} h\\right)^{5.25588}
    """
    temperature_k = temperature_c + 273.15
    if temperature_k <= 0:
        raise ValueError("Temperature must remain above absolute zero.")
    if elevation_m < 0:
        raise ValueError("Elevation must be greater than or equal to zero.")

    pressure_pa = 101325.0 * (1.0 - 2.25577e-5 * elevation_m) ** 5.25588
    return pressure_pa / (287.058 * temperature_k)


# =============================================================================
# DIMENSIONLESS TURBOMACHINERY PARAMETERS
# =============================================================================


def specific_speed(
    flow_m3s: float,
    pressure_pa: float,
    speed_rpm: float,
    density_kgm3: float = DEFAULT_AIR_DENSITY,
) -> float:
    """
    Compute Balje-form dimensionless specific speed.

    ---Parameters---
    flow_m3s : float
        Volume flow rate in m^3/s.
    pressure_pa : float
        Fan pressure rise in pascals.
    speed_rpm : float
        Rotational speed in revolutions per minute.
    density_kgm3 : float
        Working-fluid density in kg/m^3.

    ---Returns---
    specific_speed : float
        Dimensionless specific speed.

    ---LaTeX---
    \\omega_s = \\frac{\\omega \\sqrt{Q}}{(\\Delta P / \\rho)^{3/4}}
    \\omega = \\frac{2\\pi N}{60}
    """
    _validate_positive("flow", flow_m3s)
    _validate_positive("pressure rise", pressure_pa)
    _validate_positive("speed", speed_rpm)
    _validate_positive("density", density_kgm3)

    omega = speed_rpm * 2.0 * math.pi / 60.0
    delta_h = pressure_pa / density_kgm3
    return omega * math.sqrt(flow_m3s) / (delta_h ** 0.75)


def specific_diameter(
    diameter_m: float,
    flow_m3s: float,
    pressure_pa: float,
    density_kgm3: float = DEFAULT_AIR_DENSITY,
) -> float:
    """
    Compute Balje-form dimensionless specific diameter.

    ---Parameters---
    diameter_m : float
        Fan diameter in metres.
    flow_m3s : float
        Volume flow rate in m^3/s.
    pressure_pa : float
        Fan pressure rise in pascals.
    density_kgm3 : float
        Working-fluid density in kg/m^3.

    ---Returns---
    specific_diameter : float
        Dimensionless specific diameter.

    ---LaTeX---
    \\delta_s = \\frac{D (\\Delta P / \\rho)^{1/4}}{\\sqrt{Q}}
    """
    _validate_positive("diameter", diameter_m)
    _validate_positive("flow", flow_m3s)
    _validate_positive("pressure rise", pressure_pa)
    _validate_positive("density", density_kgm3)

    delta_h = pressure_pa / density_kgm3
    return diameter_m * (delta_h ** 0.25) / math.sqrt(flow_m3s)


def speed_for_ns(
    target_ns: float,
    flow_m3s: float,
    pressure_pa: float,
    density_kgm3: float = DEFAULT_AIR_DENSITY,
) -> float:
    """
    Compute the RPM required for a target specific speed.

    ---Parameters---
    target_ns : float
        Target dimensionless specific speed.
    flow_m3s : float
        Volume flow rate in m^3/s.
    pressure_pa : float
        Fan pressure rise in pascals.
    density_kgm3 : float
        Working-fluid density in kg/m^3.

    ---Returns---
    speed_rpm : float
        Rotational speed in RPM.

    ---LaTeX---
    N = \\frac{60}{2\\pi} \\omega_s \\frac{(\\Delta P / \\rho)^{3/4}}{\\sqrt{Q}}
    """
    _validate_positive("target specific speed", target_ns)
    _validate_positive("flow", flow_m3s)
    _validate_positive("pressure rise", pressure_pa)
    _validate_positive("density", density_kgm3)

    delta_h = pressure_pa / density_kgm3
    omega = target_ns * (delta_h ** 0.75) / math.sqrt(flow_m3s)
    return omega * 60.0 / (2.0 * math.pi)


def diameter_for_ds(
    target_ds: float,
    flow_m3s: float,
    pressure_pa: float,
    density_kgm3: float = DEFAULT_AIR_DENSITY,
) -> float:
    """
    Compute the diameter required for a target specific diameter.

    ---Parameters---
    target_ds : float
        Target dimensionless specific diameter.
    flow_m3s : float
        Volume flow rate in m^3/s.
    pressure_pa : float
        Fan pressure rise in pascals.
    density_kgm3 : float
        Working-fluid density in kg/m^3.

    ---Returns---
    diameter_m : float
        Fan diameter in metres.

    ---LaTeX---
    D = \\delta_s \\frac{\\sqrt{Q}}{(\\Delta P / \\rho)^{1/4}}
    """
    _validate_positive("target specific diameter", target_ds)
    _validate_positive("flow", flow_m3s)
    _validate_positive("pressure rise", pressure_pa)
    _validate_positive("density", density_kgm3)

    delta_h = pressure_pa / density_kgm3
    return target_ds * math.sqrt(flow_m3s) / (delta_h ** 0.25)


# =============================================================================
# CORDIER CORRELATION
# =============================================================================


def cordier_ds(specific_speed_value: float) -> float:
    """
    Evaluate the Cordier-line specific diameter fit.

    ---Parameters---
    specific_speed_value : float
        Dimensionless specific speed.

    ---Returns---
    specific_diameter : float
        Dimensionless specific diameter on the Cordier optimum line.

    ---LaTeX---
    \\ln(\\delta_s) = 0.833 - 0.524 \\ln(\\omega_s) + 0.008 [\\ln(\\omega_s)]^2
    """
    _validate_positive("specific speed", specific_speed_value)
    ln_ns = math.log(specific_speed_value)
    return math.exp(_CORD_A + _CORD_B * ln_ns + _CORD_C * ln_ns * ln_ns)


def cordier_efficiency(specific_speed_value: float) -> float:
    """
    Estimate the peak total-to-total efficiency along the Cordier line.

    ---Parameters---
    specific_speed_value : float
        Dimensionless specific speed.

    ---Returns---
    efficiency : float
        Estimated peak efficiency from 0 to 1.

    ---LaTeX---
    \\eta = 0.90 + 0.017 \\ln(\\omega_s) - 0.059 [\\ln(\\omega_s)]^2
    """
    _validate_positive("specific speed", specific_speed_value)
    ln_ns = math.log(specific_speed_value)
    eta = _ETA_A + _ETA_B * ln_ns + _ETA_C * ln_ns * ln_ns
    return _clamp(eta, 0.20, 0.95)


def cordier_ns_from_ds(target_ds: float, tol: float = 1.0e-6, max_iter: int = 60) -> float:
    """
    Invert the Cordier relation to find specific speed from specific diameter.

    ---Parameters---
    target_ds : float
        Target dimensionless specific diameter.
    tol : float
        Relative convergence tolerance for the binary search.
    max_iter : int
        Maximum search iterations.

    ---Returns---
    specific_speed : float
        Dimensionless specific speed that matches the target diameter.

    ---LaTeX---
    \\omega_s = f^{-1}(\\delta_s)
    """
    _validate_positive("target specific diameter", target_ds)
    _validate_positive("tolerance", tol)
    if max_iter < 1:
        raise ValueError("max_iter must be at least 1.")

    lo = math.log(0.05)
    hi = math.log(20.0)
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        current_ds = cordier_ds(math.exp(mid))
        if abs(current_ds - target_ds) / target_ds < tol:
            return math.exp(mid)
        if current_ds > target_ds:
            lo = mid
        else:
            hi = mid
    return math.exp(0.5 * (lo + hi))


def generate_cordier_line(ns_min: float = 0.08, ns_max: float = 15.0, n_points: int = 100) -> Dict[str, List[float]]:
    """
    Generate Cordier-line data for plotting.

    ---Parameters---
    ns_min : float
        Minimum specific speed for the sampled line.
    ns_max : float
        Maximum specific speed for the sampled line.
    n_points : int
        Number of plotted points.

    ---Returns---
    line_data : dict
        Dict with arrays ``ns``, ``ds``, and ``efficiency``.

    ---LaTeX---
    \\{\\omega_{s,i}, \\delta_{s,i}, \\eta_i\\}_{i=1}^{n}
    """
    _validate_positive("minimum specific speed", ns_min)
    _validate_positive("maximum specific speed", ns_max)
    if ns_max <= ns_min:
        raise ValueError("ns_max must exceed ns_min.")
    if n_points < 2:
        raise ValueError("n_points must be at least 2.")

    ns_vals: List[float] = []
    ds_vals: List[float] = []
    eta_vals: List[float] = []
    ln_lo = math.log(ns_min)
    ln_hi = math.log(ns_max)
    for idx in range(n_points):
        fraction = idx / (n_points - 1)
        ns_val = math.exp(ln_lo + fraction * (ln_hi - ln_lo))
        ns_vals.append(round(ns_val, 6))
        ds_vals.append(round(cordier_ds(ns_val), 6))
        eta_vals.append(round(cordier_efficiency(ns_val), 6))
    return {"ns": ns_vals, "ds": ds_vals, "efficiency": eta_vals}


# =============================================================================
# CURVE SHAPE FUNCTIONS
# =============================================================================


def _p_axial(x: float) -> float:
    """Normalised axial pressure curve.

    ---Parameters---
    x : float
        Flow ratio ``Q / Q_{free}``.

    ---Returns---
    pressure_ratio : float
        Normalised pressure ratio.

    ---LaTeX---
    p^* = 1 - x^{1.8}
    """
    return 1.0 - x ** 1.8


def _p_bc(x: float) -> float:
    """Normalised backward-curved pressure curve.

    ---Parameters---
    x : float
        Flow ratio ``Q / Q_{free}``.

    ---Returns---
    pressure_ratio : float
        Normalised pressure ratio.

    ---LaTeX---
    p^* = 1 - 0.3x - 0.7x^{2.2}
    """
    return 1.0 - 0.3 * x - 0.7 * x ** 2.2


def _p_fc(x: float) -> float:
    """Normalised forward-curved pressure curve with a hump.

    ---Parameters---
    x : float
        Flow ratio ``Q / Q_{free}``.

    ---Returns---
    pressure_ratio : float
        Normalised pressure ratio.

    ---LaTeX---
    p^* = 1 + 0.3x - 0.5x^{0.8} - 0.8x^{2.5}
    """
    return 1.0 + 0.3 * x - 0.5 * x ** 0.8 - 0.8 * x ** 2.5


def _p_mixed(x: float) -> float:
    """Normalised mixed-flow pressure curve.

    ---Parameters---
    x : float
        Flow ratio ``Q / Q_{free}``.

    ---Returns---
    pressure_ratio : float
        Normalised pressure ratio.

    ---LaTeX---
    p^* = 1 - 0.15x - 0.85x^2
    """
    return 1.0 - 0.15 * x - 0.85 * x ** 2.0


def _pwr_axial(x: float) -> float:
    """Normalised axial power curve.

    ---Parameters---
    x : float
        Flow ratio ``Q / Q_{free}``.

    ---Returns---
    power_ratio : float
        Normalised shaft-power ratio.

    ---LaTeX---
    P^* = 0.30 + 1.40x - 0.70x^2
    """
    return 0.30 + 1.40 * x - 0.70 * x * x


def _pwr_bc(x: float) -> float:
    """Normalised backward-curved power curve.

    ---Parameters---
    x : float
        Flow ratio ``Q / Q_{free}``.

    ---Returns---
    power_ratio : float
        Normalised shaft-power ratio.

    ---LaTeX---
    P^* = 0.40 + 1.80x - 1.50x^2 + 0.30x^3
    """
    return 0.40 + 1.80 * x - 1.50 * x * x + 0.30 * x * x * x


def _pwr_fc(x: float) -> float:
    """Normalised forward-curved power curve.

    ---Parameters---
    x : float
        Flow ratio ``Q / Q_{free}``.

    ---Returns---
    power_ratio : float
        Normalised shaft-power ratio.

    ---LaTeX---
    P^* = 0.20 + 0.90x + 0.10x^2
    """
    return 0.20 + 0.90 * x + 0.10 * x * x


def _pwr_mixed(x: float) -> float:
    """Normalised mixed-flow power curve.

    ---Parameters---
    x : float
        Flow ratio ``Q / Q_{free}``.

    ---Returns---
    power_ratio : float
        Normalised shaft-power ratio.

    ---LaTeX---
    P^* = 0.35 + 1.20x - 0.55x^2
    """
    return 0.35 + 1.20 * x - 0.55 * x * x


_CURVE_FNS = {
    "axial": (_p_axial, _pwr_axial),
    "centrifugal_bc": (_p_bc, _pwr_bc),
    "centrifugal_fc": (_p_fc, _pwr_fc),
    "mixed": (_p_mixed, _pwr_mixed),
}


# =============================================================================
# PASSAGE GEOMETRY CONSTRAINTS
# =============================================================================


def evaluate_velocity_constraint(
    flow_m3s: float,
    velocity_mode: str = "none",
    target_velocity_ms: Optional[float] = None,
    passage_area_m2: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Interpret optional passage-velocity or area inputs.

    The returned geometry is used as a packaging/acoustic realism check,
    not as an independent aerodynamic duty variable.

    ---Parameters---
    flow_m3s : float
        Volume flow rate in m^3/s.
    velocity_mode : str
        One of ``none``, ``target_velocity``, or ``known_area``.
    target_velocity_ms : float or None
        User-entered target bulk velocity in m/s when ``velocity_mode`` is
        ``target_velocity``.
    passage_area_m2 : float or None
        User-entered passage area in m^2 when ``velocity_mode`` is
        ``known_area``.

    ---Returns---
    constraint : dict
        Dict describing whether the constraint is active plus the implied area,
        equivalent diameter, velocity, and summary text.

    ---LaTeX---
    A = \\frac{Q}{V}
    V = \\frac{Q}{A}
    D_{eq} = \\sqrt{\\frac{4A}{\\pi}}
    """
    _validate_positive("flow", flow_m3s)

    inactive = {
        "active": False,
        "mode": "none",
        "area_m2": None,
        "velocity_ms": None,
        "equivalent_diameter_m": None,
        "summary": "No passage geometry constraint.",
    }

    if velocity_mode == "none":
        return inactive

    if velocity_mode == "target_velocity":
        if target_velocity_ms is None:
            raise ValueError("Target velocity is required when velocity_mode is 'target_velocity'.")
        _validate_positive("target velocity", target_velocity_ms)
        velocity_ms = target_velocity_ms
        area_m2 = flow_m3s / velocity_ms
    elif velocity_mode == "known_area":
        if passage_area_m2 is None:
            raise ValueError("Passage area is required when velocity_mode is 'known_area'.")
        _validate_positive("passage area", passage_area_m2)
        area_m2 = passage_area_m2
        velocity_ms = flow_m3s / area_m2
    else:
        raise ValueError("velocity_mode must be one of: none, target_velocity, known_area.")

    equivalent_diameter_m = _equivalent_diameter_from_area(area_m2)
    if velocity_mode == "target_velocity":
        summary = (
            f"Target passage velocity of {velocity_ms:.1f} m/s implies "
            f"{area_m2:.3f} m^2 of flow area."
        )
    else:
        summary = (
            f"Known passage area of {area_m2:.3f} m^2 implies "
            f"{velocity_ms:.1f} m/s bulk velocity."
        )

    return {
        "active": True,
        "mode": velocity_mode,
        "area_m2": area_m2,
        "velocity_ms": velocity_ms,
        "equivalent_diameter_m": equivalent_diameter_m,
        "summary": summary,
    }


def evaluate_passage_fit(
    family: str,
    reference_geometry: Dict[str, Any],
    velocity_constraint: Dict[str, Any],
) -> Dict[str, Optional[float]]:
    """
    Score a fan family against an optional passage-geometry constraint.

    The comparison uses a modeled fan reference area rather than only the
    outer wheel diameter. For axial and mixed-flow fans that reference area is
    the rotor annulus. For centrifugal fans it is the inlet eye annulus.

    ---Parameters---
    family : str
        Architecture family: axial, mixed, or radial.
    reference_geometry : dict
        Output from :func:`estimate_reference_geometry`.
    velocity_constraint : dict
        Output from :func:`evaluate_velocity_constraint`.

    ---Returns---
    fit_data : dict
        Dict with area-match fit, reference-velocity fit, combined fit, and
        area-ratio values. All are ``None`` when the constraint is inactive.

    ---LaTeX---
    \\phi_A = \\frac{A_{sys}}{A_{fan,eff}}
    s = w_A s_A + w_V s_V
    """
    if not velocity_constraint["active"]:
        return {
            "area_fit": None,
            "velocity_fit": None,
            "combined_fit": None,
            "area_ratio": None,
            "effective_diameter_ratio": None,
        }

    if family not in _PASSAGE_PREFS:
        raise ValueError(f"Unknown family '{family}'.")
    fan_area = reference_geometry.get("effective_flow_area_m2")
    fan_velocity = reference_geometry.get("reference_velocity_ms")
    _validate_positive("effective flow area", fan_area)
    _validate_positive("reference velocity", fan_velocity)

    prefs = _PASSAGE_PREFS[family]
    area_ratio = velocity_constraint["area_m2"] / fan_area
    area_fit = _range_fit_log(
        area_ratio,
        _AREA_MATCH_PREFS["ratio_min"],
        _AREA_MATCH_PREFS["ratio_max"],
        _AREA_MATCH_PREFS["ratio_optimal"],
    )
    velocity_fit = _range_fit_log(
        fan_velocity,
        prefs["velocity_min"],
        prefs["velocity_max"],
        prefs["velocity_optimal"],
    )
    combined_fit = 0.64 * area_fit + 0.36 * velocity_fit
    return {
        "area_fit": round(area_fit, 4),
        "velocity_fit": round(velocity_fit, 4),
        "combined_fit": round(combined_fit, 4),
        "area_ratio": round(area_ratio, 4),
        "effective_diameter_ratio": round(math.sqrt(area_ratio), 4),
    }


def suggest_nominal_diameter(diameter_m: float) -> Dict[str, Any]:
    """
    Suggest nearby nominal hardware diameters for a continuous wheel estimate.

    ---Parameters---
    diameter_m : float
        Continuous predicted wheel diameter in metres.

    ---Returns---
    suggestion : dict
        Dict containing estimated, nearest, lower, and upper nominal sizes in
        millimetres plus a short summary string.

    ---LaTeX---
    D_{nom} \\in \\{D_i\\}_{preferred}
    """
    _validate_positive("diameter", diameter_m)

    diameter_mm = diameter_m * 1000.0
    lower = _NOMINAL_DIAMETER_SERIES_MM[0]
    upper = _NOMINAL_DIAMETER_SERIES_MM[-1]
    for size_mm in _NOMINAL_DIAMETER_SERIES_MM:
        if size_mm <= diameter_mm:
            lower = size_mm
        if size_mm >= diameter_mm:
            upper = size_mm
            break

    if abs(diameter_mm - lower) <= abs(upper - diameter_mm):
        nearest = lower
    else:
        nearest = upper

    if lower == upper:
        bracket = [lower]
        summary = f"The estimate already lands on a nominal {nearest} mm size."
    else:
        bracket = [lower, upper]
        summary = (
            f"The continuous estimate is {diameter_mm:.0f} mm, so start by checking "
            f"roughly {lower} and {upper} mm hardware."
        )

    return {
        "estimate_mm": round(diameter_mm, 1),
        "nearest_mm": nearest,
        "lower_mm": lower,
        "upper_mm": upper,
        "bracket_mm": bracket,
        "summary": summary,
    }


def evaluate_drive_fit(speed_rpm: float, shaft_power_w: Optional[float] = None) -> Dict[str, Any]:
    """
    Recommend a likely drive approach for the screened wheel speed.

    ---Parameters---
    speed_rpm : float
        Required wheel speed in RPM.
    shaft_power_w : float or None
        Optional shaft power in watts. When present it is used to estimate
        shaft torque and strengthen gearbox guidance at low speed.

    ---Returns---
    drive_fit : dict
        Dict containing a qualitative drive recommendation, nearest nominal
        induction speed, deviation, torque estimate, frequency dependence, and
        summary guidance.

    ---LaTeX---
    \\epsilon_N = \\min_i \\left| \\frac{N - N_i}{N_i} \\right|
    T = \\frac{P}{\\omega}
    """
    _validate_positive("speed", speed_rpm)
    if shaft_power_w is not None:
        _validate_positive("shaft power", shaft_power_w)

    nearest = min(
        _STANDARD_DRIVE_SPEEDS,
        key=lambda item: abs(speed_rpm - item["rpm"]) / item["rpm"],
    )
    relative_error = abs(speed_rpm - nearest["rpm"]) / nearest["rpm"]
    torque_nm = None
    if shaft_power_w is not None:
        omega = speed_rpm * 2.0 * math.pi / 60.0
        torque_nm = shaft_power_w / max(omega, 1.0e-9)

    if relative_error <= 0.06 and 700.0 <= speed_rpm <= 4200.0:
        label = "Standard direct-drive induction"
        topology = "induction_direct"
        score = 1.0
        frequency_dependency = "High"
        summary = (
            f"Very close to {nearest['rpm']:.0f} RPM, so a direct-drive induction motor near "
            f"{nearest['label']} is plausible."
        )
        frequency_note = (
            "Line frequency and pole count matter here because the wheel speed is close to a "
            "near-synchronous induction-motor speed."
        )
    elif speed_rpm < 500.0 or (speed_rpm < 700.0 and torque_nm is not None and torque_nm >= 25.0):
        label = "Gearbox or gearmotor reduction"
        topology = "gearbox_reduction"
        score = 0.52
        frequency_dependency = "Moderate"
        summary = (
            "The wheel speed is well below common direct-drive motor speeds, so a reducer-based "
            "solution is more plausible than fixed direct drive."
        )
        if torque_nm is not None:
            summary += f" The current shaft torque is about {torque_nm:.1f} N-m, which further supports a geared reduction path."
        frequency_note = (
            "AC frequency is no longer the main speed-setting constraint because the reduction "
            "stage sets the final wheel speed."
        )
    elif speed_rpm < 900.0:
        label = "Belt reduction or gearbox"
        topology = "mechanical_reduction"
        score = 0.6
        frequency_dependency = "Moderate"
        summary = (
            "Below the usual direct-drive induction range. A belt reduction, gear reducer, or "
            "purpose-built low-speed EC motor is more plausible than plain fixed-frequency direct drive."
        )
        frequency_note = (
            "Motor line frequency matters less once a belt or gearbox is used to set the final wheel speed."
        )
    elif relative_error <= 0.18 and speed_rpm <= 4200.0:
        label = "VFD induction direct drive"
        topology = "vfd_induction"
        score = 0.84
        summary = (
            f"Near the {nearest['rpm']:.0f} RPM family, but not close enough for pure fixed-frequency "
            "direct drive. A VFD-driven induction motor is the most natural first recommendation."
        )
        frequency_dependency = "Low"
        frequency_note = (
            "AC line frequency is secondary here because the inverter would set the running speed."
        )
    elif speed_rpm <= 6000.0:
        label = "ECM / BLDC or PM direct drive"
        topology = "brushless_direct"
        score = 0.68
        summary = (
            "This speed is outside the comfortable fixed-frequency induction plateaus, but still in a range "
            "that often suits ECM, BLDC, or PM direct-drive hardware."
        )
        frequency_dependency = "Low"
        frequency_note = (
            "Line frequency is not the main limiter here; motor topology, inverter capability, and rotor "
            "mechanics matter more."
        )
    else:
        label = "High-speed PM / BLDC specialty drive"
        topology = "high_speed_specialty"
        score = 0.32
        summary = (
            "Well above the common induction direct-drive speeds, so expect PM, BLDC, or another "
            "high-speed specialty drive with careful attention to rotor and impeller mechanics."
        )
        frequency_dependency = "Low"
        frequency_note = (
            "AC mains frequency is largely irrelevant at this point; the controlling issues are inverter range, "
            "mechanical stress, bearings, and acoustic behavior."
        )

    return {
        "label": label,
        "topology": topology,
        "score": round(score, 4),
        "nearest_rpm": nearest["rpm"],
        "nearest_label": nearest["label"],
        "relative_error": round(relative_error, 4),
        "torque_nm": _round_if_number(torque_nm, 3),
        "frequency_dependency": frequency_dependency,
        "frequency_note": frequency_note,
        "summary": summary,
    }


def evaluate_architecture_margin(type_id: str, specific_speed_value: float) -> Dict[str, Any]:
    """
    Estimate how comfortably a duty point sits inside a type's natural band.

    ---Parameters---
    type_id : str
        Fan type identifier.
    specific_speed_value : float
        Candidate specific speed.

    ---Returns---
    margin : dict
        Dict containing a 0-1 margin score, qualitative label, and summary.

    ---LaTeX---
    M = \\min \\left(
        \\frac{\\ln(\\omega_s / \\omega_{s,min})}{\\ln(\\omega_{s,opt} / \\omega_{s,min})},
        \\frac{\\ln(\\omega_{s,max} / \\omega_s)}{\\ln(\\omega_{s,max} / \\omega_{s,opt})}
    \\right)
    """
    _validate_positive("specific speed", specific_speed_value)
    if type_id not in FAN_TYPES:
        raise ValueError(f"Unknown fan type '{type_id}'.")

    type_info = FAN_TYPES[type_id]
    ns_min = type_info["ns_min"]
    ns_max = type_info["ns_max"]
    ns_opt = type_info["ns_optimal"]

    if specific_speed_value < ns_min or specific_speed_value > ns_max:
        margin_score = 0.0
        label = "Outside natural band"
    else:
        ln_ns = math.log(specific_speed_value)
        ln_min = math.log(ns_min)
        ln_max = math.log(ns_max)
        ln_opt = math.log(ns_opt)
        left = (ln_ns - ln_min) / max(ln_opt - ln_min, 1.0e-9)
        right = (ln_max - ln_ns) / max(ln_max - ln_opt, 1.0e-9)
        margin_score = _clamp(min(left, right), 0.0, 1.0)
        if margin_score >= 0.68:
            label = "High"
        elif margin_score >= 0.35:
            label = "Moderate"
        else:
            label = "Tight"

    if type_id == "axial":
        if label == "High":
            summary = "Comfortably inside the axial band, so pressure-rise margin looks healthier."
        elif label == "Moderate":
            summary = "Still inside the axial band, but pressure loading is starting to tighten the margin."
        elif label == "Tight":
            summary = "Near the pressure-loaded edge of the axial band; confirm stall and noise margin on the real curve."
        else:
            summary = "Outside the axial comfort band; expect elevated stall and noise sensitivity if the system hardens."
    elif type_id == "centrifugal_fc":
        if label == "High":
            summary = "Comfortably inside the forward-curved band for a compact low-speed screen."
        elif label == "Moderate":
            summary = "Still in the FC band, but confirm the hump-region operating margin on the real curve."
        elif label == "Tight":
            summary = "Near the FC band edge; hump-region stability and motor loading deserve extra attention."
        else:
            summary = "Outside the FC comfort band; treat this as a weak architectural fit."
    elif type_id == "centrifugal_bc":
        if label == "High":
            summary = "Comfortably inside the BC band, which usually means a robust efficiency-first radial fit."
        elif label == "Moderate":
            summary = "Still within the BC band, but real-curve confirmation should check how much margin remains."
        elif label == "Tight":
            summary = "Near the BC band edge; the wheel is being pushed away from its natural centrifugal neighborhood."
        else:
            summary = "Outside the BC comfort band; a different architecture may fit the duty more naturally."
    else:
        if label == "High":
            summary = "Comfortably inside the mixed-flow band."
        elif label == "Moderate":
            summary = "Still inside the mixed-flow band, with some room left before the family crossover edges."
        elif label == "Tight":
            summary = "Near the mixed-flow crossover edge; confirm the final choice on real vendor curves."
        else:
            summary = "Outside the mixed-flow comfort band; another family likely fits the duty more naturally."

    return {
        "score": round(margin_score, 4),
        "label": label,
        "summary": summary,
    }


def evaluate_acoustic_risk(
    type_id: str,
    tip_speed_ms: float,
    velocity_constraint: Dict[str, Any],
    architecture_margin_score: float,
) -> Dict[str, Any]:
    """
    Create an acoustic-risk proxy from tip speed, passage velocity, and margin.

    This is intentionally a screening-level sentiment, not a sound-power
    prediction.

    ---Parameters---
    type_id : str
        Fan type identifier.
    tip_speed_ms : float
        Impeller tip speed in m/s.
    velocity_constraint : dict
        Optional passage-geometry payload.
    architecture_margin_score : float
        Architecture margin score from 0 to 1.

    ---Returns---
    acoustic_risk : dict
        Dict with normalized risk components, a qualitative label, and summary.

    ---LaTeX---
    R_{ac} = w_U R_U + w_V R_V + w_M (1 - M)
    """
    _validate_positive("tip speed", tip_speed_ms)
    if type_id not in FAN_TYPES:
        raise ValueError(f"Unknown fan type '{type_id}'.")

    type_info = FAN_TYPES[type_id]
    tip_component = _clamp(
        (tip_speed_ms - type_info["tip_speed_quiet_ms"])
        / max(type_info["tip_speed_alert_ms"] - type_info["tip_speed_quiet_ms"], 1.0e-9),
        0.0,
        1.0,
    )

    velocity_component: Optional[float] = None
    if velocity_constraint["active"]:
        prefs = _PASSAGE_PREFS[type_info["family"]]
        velocity_component = _clamp(
            (velocity_constraint["velocity_ms"] - prefs["velocity_optimal"])
            / max(prefs["velocity_max"] - prefs["velocity_optimal"], 1.0e-9),
            0.0,
            1.0,
        )
        risk_index = (
            0.65 * tip_component
            + 0.20 * velocity_component
            + 0.15 * (1.0 - architecture_margin_score)
        )
    else:
        risk_index = 0.82 * tip_component + 0.18 * (1.0 - architecture_margin_score)

    risk_index = _clamp(risk_index, 0.0, 1.0)
    if risk_index <= 0.30:
        label = "Low"
    elif risk_index <= 0.60:
        label = "Medium"
    else:
        label = "High"

    driver_terms = [f"tip speed {tip_speed_ms:.1f} m/s"]
    if velocity_component is not None:
        driver_terms.append(f"bulk passage velocity {velocity_constraint['velocity_ms']:.1f} m/s")
    if architecture_margin_score < 0.35:
        driver_terms.append("tight architecture margin")

    summary = (
        f"{label} acoustic proxy risk driven mainly by "
        + ", ".join(driver_terms)
        + ". This is a comparative screen, not a sound-power prediction."
    )

    return {
        "index": round(risk_index, 4),
        "label": label,
        "tip_component": round(tip_component, 4),
        "velocity_component": _round_if_number(velocity_component, 4),
        "summary": summary,
    }


# =============================================================================
# REPRESENTATIVE CURVE DATA
# =============================================================================


def generate_representative_curves(
    flow_m3s: float,
    pressure_pa: float,
    density_kgm3: float = DEFAULT_AIR_DENSITY,
    n_points: int = 80,
) -> Dict[str, Dict[str, List[float]]]:
    """
    Generate representative family curves scaled to the duty point.

    Each family curve is scaled so that its nominal best-efficiency point
    passes through the user duty point. The curves are pedagogical, not vendor
    curves.

    ---Parameters---
    flow_m3s : float
        Duty-point volume flow rate in m^3/s.
    pressure_pa : float
        Duty-point fan pressure rise in Pa.
    density_kgm3 : float
        Working-fluid density in kg/m^3.
    n_points : int
        Number of plotted points.

    ---Returns---
    curves : dict
        Per-type curve arrays for flow, pressure, power, and efficiency.

    ---LaTeX---
    P_{shaft} = \\frac{Q \\Delta P}{\\eta}
    """
    _validate_positive("flow", flow_m3s)
    _validate_positive("pressure rise", pressure_pa)
    _validate_positive("density", density_kgm3)
    if n_points < 8:
        raise ValueError("n_points must be at least 8.")

    results: Dict[str, Dict[str, List[float]]] = {}

    for type_id, info in FAN_TYPES.items():
        pressure_fn, power_fn = _CURVE_FNS[type_id]
        bep_x = info["bep_flow_fraction"]
        eta_peak = info["typical_peak_efficiency"]

        p_at_bep = pressure_fn(bep_x)
        pwr_at_bep = power_fn(bep_x)
        dp_shutoff = pressure_pa / p_at_bep
        q_max = flow_m3s / bep_x
        p_shaft_bep = flow_m3s * pressure_pa / eta_peak

        flow_values: List[float] = []
        pressure_values: List[float] = []
        power_values: List[float] = []
        efficiency_values: List[float] = []

        for idx in range(n_points + 1):
            x = idx / n_points
            flow_val = x * q_max
            pressure_val = max(dp_shutoff * pressure_fn(x), 0.0)
            power_val = max(p_shaft_bep * power_fn(x) / pwr_at_bep, 0.0)
            efficiency_val = 0.0
            if flow_val > 0.0 and pressure_val > 0.0 and power_val > 0.0:
                efficiency_val = _clamp(flow_val * pressure_val / power_val, 0.0, 1.0)

            flow_values.append(round(flow_val, 6))
            pressure_values.append(round(pressure_val, 3))
            power_values.append(round(power_val, 3))
            efficiency_values.append(round(efficiency_val, 5))

        results[type_id] = {
            "flow_values": flow_values,
            "pressure_values": pressure_values,
            "power_values": power_values,
            "efficiency_values": efficiency_values,
            "bep_flow": round(flow_m3s, 6),
            "bep_pressure": round(pressure_pa, 3),
            "shutoff_pressure": round(dp_shutoff, 3),
            "free_delivery_flow": round(q_max, 6),
        }

    return results


def generate_system_curve(duty_flow: float, duty_pressure: float, q_max: float, n_points: int = 80) -> Dict[str, List[float]]:
    """
    Generate a quadratic system curve through the duty point.

    ---Parameters---
    duty_flow : float
        Duty-point flow in m^3/s.
    duty_pressure : float
        Duty-point pressure in Pa.
    q_max : float
        Maximum plotted flow in m^3/s.
    n_points : int
        Number of plotted points.

    ---Returns---
    system_curve : dict
        Dict with ``flow_values`` and ``pressure_values`` arrays.

    ---LaTeX---
    \\Delta P_{sys} = KQ^2
    K = \\frac{\\Delta P_{duty}}{Q_{duty}^2}
    """
    _validate_positive("duty flow", duty_flow)
    _validate_positive("duty pressure", duty_pressure)
    _validate_positive("maximum plotted flow", q_max)
    if n_points < 8:
        raise ValueError("n_points must be at least 8.")

    coefficient = duty_pressure / (duty_flow * duty_flow)
    flow_values: List[float] = []
    pressure_values: List[float] = []
    for idx in range(n_points + 1):
        flow_val = idx / n_points * q_max
        flow_values.append(round(flow_val, 6))
        pressure_values.append(round(coefficient * flow_val * flow_val, 3))
    return {"flow_values": flow_values, "pressure_values": pressure_values}


# =============================================================================
# TYPE ANALYSIS
# =============================================================================


def _constraint_payload(
    flow_m3s: float,
    pressure_pa: float,
    density_kgm3: float,
    speed_rpm: Optional[float],
    diameter_m: Optional[float],
) -> Dict[str, Optional[float]]:
    """Normalize mutually exclusive RPM/diameter constraint inputs.

    ---Parameters---
    flow_m3s : float
        Duty-point flow in m^3/s.
    pressure_pa : float
        Duty-point pressure in Pa.
    density_kgm3 : float
        Working-fluid density in kg/m^3.
    speed_rpm : float or None
        Optional fixed speed constraint.
    diameter_m : float or None
        Optional fixed diameter constraint.

    ---Returns---
    constraint : dict
        Normalized constraint mode plus the actual speed, diameter, specific
        speed, and specific diameter implied by that mode.

    ---LaTeX---
    \\omega_s = \\frac{\\omega \\sqrt{Q}}{(\\Delta P / \\rho)^{3/4}}
    \\delta_s = \\frac{D (\\Delta P / \\rho)^{1/4}}{\\sqrt{Q}}
    """
    if speed_rpm is not None and diameter_m is not None:
        raise ValueError("Specify either speed_rpm or diameter_m, not both.")

    if speed_rpm is not None:
        _validate_positive("speed", speed_rpm)
        actual_ns = specific_speed(flow_m3s, pressure_pa, speed_rpm, density_kgm3)
        actual_ds = cordier_ds(actual_ns)
        actual_diameter = diameter_for_ds(actual_ds, flow_m3s, pressure_pa, density_kgm3)
        return {
            "mode": "speed",
            "actual_speed_rpm": speed_rpm,
            "actual_diameter_m": actual_diameter,
            "actual_specific_speed": actual_ns,
            "actual_specific_diameter": actual_ds,
        }

    if diameter_m is not None:
        _validate_positive("diameter", diameter_m)
        actual_ds = specific_diameter(diameter_m, flow_m3s, pressure_pa, density_kgm3)
        actual_ns = cordier_ns_from_ds(actual_ds)
        actual_speed = speed_for_ns(actual_ns, flow_m3s, pressure_pa, density_kgm3)
        return {
            "mode": "diameter",
            "actual_speed_rpm": actual_speed,
            "actual_diameter_m": diameter_m,
            "actual_specific_speed": actual_ns,
            "actual_specific_diameter": actual_ds,
        }

    return {
        "mode": "none",
        "actual_speed_rpm": None,
        "actual_diameter_m": None,
        "actual_specific_speed": None,
        "actual_specific_diameter": None,
    }


def _constraint_note(
    constraint_mode: str,
    actual_speed_rpm: float,
    actual_diameter_m: float,
    ideal_speed_rpm: float,
    ideal_diameter_m: float,
) -> str:
    """Generate concise constraint-mismatch guidance for a candidate type.

    ---Parameters---
    constraint_mode : str
        Constraint mode: none, speed, or diameter.
    actual_speed_rpm : float
        Actual or imposed speed in RPM.
    actual_diameter_m : float
        Actual or imposed diameter in metres.
    ideal_speed_rpm : float
        Unconstrained near-optimum speed in RPM.
    ideal_diameter_m : float
        Unconstrained near-optimum diameter in metres.

    ---Returns---
    note : str
        Human-readable note describing the constraint effect.

    ---LaTeX---
    \\Delta N = N_{actual} - N_{ideal}
    \\Delta D = D_{actual} - D_{ideal}
    """
    if constraint_mode == "speed":
        return (
            f"Fixed at {actual_speed_rpm:.0f} RPM; this type would ideally want "
            f"about {ideal_speed_rpm:.0f} RPM and a {ideal_diameter_m * 1000:.0f} mm wheel."
        )
    if constraint_mode == "diameter":
        return (
            f"Fixed at {actual_diameter_m * 1000:.0f} mm; this type would ideally want "
            f"about {ideal_diameter_m * 1000:.0f} mm and {ideal_speed_rpm:.0f} RPM."
        )
    return "Unconstrained sizing shown near each type's preferred specific speed."


def _score_candidate(
    ns_fit: float,
    estimated_efficiency: float,
    tip_speed_ms: float,
    passage_fit: Optional[float],
) -> float:
    """Blend fit terms into a 0-1 suitability score.

    ---Parameters---
    ns_fit : float
        Specific-speed fit score from 0 to 1.
    estimated_efficiency : float
        Estimated peak efficiency from 0 to 1.
    tip_speed_ms : float
        Tip speed in m/s.
    passage_fit : float or None
        Optional passage-geometry fit score from 0 to 1.

    ---Returns---
    score : float
        Overall suitability score from 0 to 1.

    ---LaTeX---
    S = w_N S_N + w_\\eta S_\\eta + w_U S_U + w_A S_A
    """
    eta_score = _clamp(estimated_efficiency / _MAX_TYPICAL_EFFICIENCY, 0.2, 1.0)
    tip_score = _tip_speed_fit(tip_speed_ms)
    if passage_fit is None:
        score = 0.58 * ns_fit + 0.27 * eta_score + 0.15 * tip_score
    else:
        score = 0.50 * ns_fit + 0.22 * eta_score + 0.12 * tip_score + 0.16 * passage_fit
    return _clamp(score, 0.0, 1.0)


def _score_breakdown(
    ns_fit: float,
    estimated_efficiency: float,
    tip_speed_ms: float,
    passage_fit: Optional[float],
) -> Dict[str, Any]:
    """Expose weighted score terms for frontend decision-trace rendering.

    ---Parameters---
    ns_fit : float
        Specific-speed fit score from 0 to 1.
    estimated_efficiency : float
        Estimated peak efficiency from 0 to 1.
    tip_speed_ms : float
        Tip speed in m/s.
    passage_fit : float or None
        Optional passage-geometry fit score from 0 to 1.

    ---Returns---
    breakdown : dict
        Weighted scoring components, weights, and total score.

    ---LaTeX---
    S = w_N S_N + w_\\eta S_\\eta + w_U S_U + w_A S_A
    """
    eta_score = _clamp(estimated_efficiency / _MAX_TYPICAL_EFFICIENCY, 0.2, 1.0)
    tip_score = _tip_speed_fit(tip_speed_ms)

    weights: Dict[str, float] = {
        "specific_speed_fit": 0.58,
        "efficiency_fit": 0.27,
        "tip_speed_fit": 0.15,
        "passage_fit": 0.0,
    }
    components: Dict[str, Optional[float]] = {
        "specific_speed_fit": round(ns_fit, 4),
        "efficiency_fit": round(eta_score, 4),
        "tip_speed_fit": round(tip_score, 4),
        "passage_fit": None,
    }
    contributions: Dict[str, Optional[float]] = {
        "specific_speed_fit": round(weights["specific_speed_fit"] * ns_fit, 4),
        "efficiency_fit": round(weights["efficiency_fit"] * eta_score, 4),
        "tip_speed_fit": round(weights["tip_speed_fit"] * tip_score, 4),
        "passage_fit": None,
    }

    if passage_fit is not None:
        weights = {
            "specific_speed_fit": 0.50,
            "efficiency_fit": 0.22,
            "tip_speed_fit": 0.12,
            "passage_fit": 0.16,
        }
        components["passage_fit"] = round(passage_fit, 4)
        contributions = {
            "specific_speed_fit": round(weights["specific_speed_fit"] * ns_fit, 4),
            "efficiency_fit": round(weights["efficiency_fit"] * eta_score, 4),
            "tip_speed_fit": round(weights["tip_speed_fit"] * tip_score, 4),
            "passage_fit": round(weights["passage_fit"] * passage_fit, 4),
        }

    total_score = _clamp(sum(value or 0.0 for value in contributions.values()), 0.0, 1.0)
    return {
        "weights": weights,
        "components": components,
        "contributions": contributions,
        "total": round(total_score, 4),
    }


def _candidate_strengths(
    type_info: Dict[str, Any],
    actual_ns: float,
    passage_fit: Optional[float],
    velocity_constraint: Dict[str, Any],
    drive_fit: Dict[str, Any],
    architecture_margin: Dict[str, Any],
) -> List[str]:
    """Build concise strengths text for a candidate.

    ---Parameters---
    type_info : dict
        Fan type metadata.
    actual_ns : float
        Actual candidate specific speed.
    passage_fit : float or None
        Optional passage-fit score.
    velocity_constraint : dict
        Velocity-constraint payload.
    drive_fit : dict
        Drive-fit payload for the candidate speed.
    architecture_margin : dict
        Architecture-margin payload.

    ---Returns---
    strengths : list[str]
        Up to three short strengths.

    ---LaTeX---
    \\omega_s \\in [\\omega_{s,min}, \\omega_{s,max}]
    """
    strengths: List[str] = []
    if type_info["ns_min"] <= actual_ns <= type_info["ns_max"]:
        strengths.append(
            f"N_s = {actual_ns:.2f} sits inside this type's natural operating range."
        )
    if architecture_margin["label"] in {"High", "Moderate"}:
        strengths.append(architecture_margin["summary"])
    if type_info["power_overloading"]:
        strengths.append("Compact low-speed packaging is one of this branch's main strengths.")
    else:
        strengths.append("Non-overloading or stable loading behavior is favorable here.")
    if drive_fit["score"] >= 0.84:
        strengths.append(drive_fit["summary"])
    if velocity_constraint["active"] and passage_fit is not None and passage_fit >= 0.82:
        strengths.append("The imposed system area matches this type's modeled fan-side flow area cleanly.")
    if not strengths:
        strengths.append("It remains viable mainly because it avoids a hard family mismatch.")
    return strengths[:3]


def _candidate_cautions(
    type_info: Dict[str, Any],
    actual_ns: float,
    passage_fit: Optional[float],
    velocity_constraint: Dict[str, Any],
    acoustic_risk: Dict[str, Any],
    drive_fit: Dict[str, Any],
    architecture_margin: Dict[str, Any],
) -> List[str]:
    """Build concise caution text for a candidate.

    ---Parameters---
    type_info : dict
        Fan type metadata.
    actual_ns : float
        Actual candidate specific speed.
    passage_fit : float or None
        Optional passage-fit score.
    velocity_constraint : dict
        Velocity-constraint payload.
    acoustic_risk : dict
        Acoustic-risk payload.
    drive_fit : dict
        Drive-fit payload.
    architecture_margin : dict
        Architecture-margin payload.

    ---Returns---
    cautions : list[str]
        Up to three short caution statements.

    ---LaTeX---
    \\omega_s \\notin [\\omega_{s,min}, \\omega_{s,max}]
    """
    cautions: List[str] = []
    if not (type_info["ns_min"] <= actual_ns <= type_info["ns_max"]):
        cautions.append(
            f"N_s = {actual_ns:.2f} is outside this type's preferred specific-speed band."
        )
    elif architecture_margin["label"] == "Tight":
        cautions.append(architecture_margin["summary"])
    if type_info["power_overloading"]:
        cautions.append("Check motor sizing carefully; the forward-curved branch can overload.")
    if velocity_constraint["active"] and passage_fit is not None and passage_fit < 0.58:
        cautions.append("The imposed system area is awkward relative to this type's modeled fan-side flow section.")
    if acoustic_risk["label"] == "High":
        cautions.append(acoustic_risk["summary"])
    if drive_fit["score"] <= 0.6:
        cautions.append(drive_fit["summary"])
    if "Axial" in type_info["name"] and architecture_margin["label"] != "High":
        cautions.append("Pressure capability falls off quickly if the real system becomes more restrictive.")
    if not cautions:
        cautions.append("Vendor curves still decide the final selection and stall margin.")
    return cautions[:3]


def _candidate_top_reason(candidate: Dict[str, Any]) -> str:
    """Return the strongest positive screening reason for a candidate."""
    if candidate["in_range"] and candidate["architecture_margin"]["label"] == "High":
        return (
            f"N_s = {candidate['specific_speed']:.2f} lands cleanly inside the "
            f"{candidate['short_name']} band with high margin."
        )
    if candidate["in_range"]:
        return (
            f"N_s = {candidate['specific_speed']:.2f} still sits inside the "
            f"{candidate['short_name']} family band."
        )
    if candidate["passage_fit"] is not None and candidate["passage_fit"] >= 0.8:
        return "The imposed system area fits this architecture's modeled fan-side flow section unusually well."
    if candidate["drive_fit"]["score"] >= 0.84:
        return "Its screened RPM lands close to a standard direct-drive motor speed."
    return candidate["strengths"][0]


def _candidate_main_blocker(candidate: Dict[str, Any]) -> str:
    """Return the dominant negative screening reason for a candidate."""
    if not candidate["in_range"]:
        return (
            f"N_s = {candidate['specific_speed']:.2f} sits outside the preferred "
            f"{candidate['short_name']} band."
        )
    if candidate["acoustic_risk"]["label"] == "High":
        return candidate["acoustic_risk"]["summary"]
    if candidate["architecture_margin"]["label"] == "Tight":
        return candidate["architecture_margin"]["summary"]
    if candidate["drive_fit"]["score"] <= 0.6:
        return candidate["drive_fit"]["summary"]
    if candidate["passage_fit"] is not None and candidate["passage_fit"] < 0.58:
        return "The imposed system area is awkward for this architecture's modeled flow section."
    return candidate["cautions"][0]


def _comparative_blocker(candidate: Dict[str, Any], best: Dict[str, Any]) -> str:
    """Return a stronger loser explanation when generic cautions are too weak."""
    generic = _candidate_main_blocker(candidate)
    if generic != "Vendor curves still decide the final selection and stall margin.":
        return generic
    if candidate["specific_speed"] != best["specific_speed"]:
        return (
            f"It needs a different N_s neighborhood than the winner, which pushes it toward "
            f"{candidate['speed_rpm']:.0f} RPM and {candidate['diameter_m'] * 1000:.0f} mm for the same duty."
        )
    if candidate["estimated_efficiency"] + 0.02 < best["estimated_efficiency"]:
        return (
            f"It gives up likely efficiency versus {best['short_name']} "
            f"({candidate['estimated_efficiency'] * 100:.1f}% vs {best['estimated_efficiency'] * 100:.1f}%)."
        )
    if candidate["tip_speed_ms"] > best["tip_speed_ms"] + 5.0:
        return (
            f"It gets there with a less comfortable tip-speed read than {best['short_name']} "
            f"({candidate['tip_speed_ms']:.1f} vs {best['tip_speed_ms']:.1f} m/s)."
        )
    return (
        f"It simply finishes behind {best['short_name']} once the realism modifiers are applied."
    )


def _weight_rationale(passage_active: bool) -> List[Dict[str, Any]]:
    """Return plain-language justification for the screening weights."""
    weights = {
        "specific_speed_fit": 0.50 if passage_active else 0.58,
        "efficiency_fit": 0.22 if passage_active else 0.27,
        "tip_speed_fit": 0.12 if passage_active else 0.15,
        "passage_fit": 0.16 if passage_active else 0.0,
    }
    reasons = [
        {
            "component": "Specific-speed fit",
            "weight": weights["specific_speed_fit"],
            "why": (
                "This carries the most weight because fan-family selection is primarily a "
                "specific-speed screening problem. The architecture bands are defined around N_s."
            ),
            "effect": "Rewards candidates whose actual or screened N_s lands near the center of their natural band.",
        },
        {
            "component": "Efficiency fit",
            "weight": weights["efficiency_fit"],
            "why": (
                "Efficiency matters, but only after the architecture is physically plausible. "
                "It should separate credible families, not override a bad family match."
            ),
            "effect": "Favors families with a stronger likely efficiency ceiling at the current duty-side N_s.",
        },
        {
            "component": "Tip-speed fit",
            "weight": weights["tip_speed_fit"],
            "why": (
                "Tip speed is a compact proxy for noise and mechanical realism, but it is still "
                "a secondary screen rather than the defining architecture criterion."
            ),
            "effect": "Penalizes candidates that only work by spinning a relatively small wheel very hard.",
        },
    ]
    if passage_active:
        reasons.append(
            {
                "component": "Passage fit",
                "weight": weights["passage_fit"],
                "why": (
                    "Once the user imposes duct area or target velocity, packaging realism should affect "
                    "the ranking directly rather than remaining just a side note."
                ),
                "effect": "Boosts families whose modeled fan-side flow area matches the imposed system area more naturally.",
            }
        )
    return reasons


def _component_delta_reason(
    component_key: str,
    best: Dict[str, Any],
    runner_up: Dict[str, Any],
) -> str:
    """Explain why a score component separates winner and runner-up."""
    if component_key == "specific_speed_fit":
        return (
            f"{best['short_name']} is closer to the center of its natural N_s band than "
            f"{runner_up['short_name']}."
        )
    if component_key == "efficiency_fit":
        return (
            f"{best['short_name']} carries a stronger estimated efficiency at this duty "
            f"({best['estimated_efficiency'] * 100:.1f}% vs {runner_up['estimated_efficiency'] * 100:.1f}%)."
        )
    if component_key == "tip_speed_fit":
        return (
            f"{best['short_name']} has the more comfortable tip-speed read "
            f"({best['tip_speed_ms']:.1f} vs {runner_up['tip_speed_ms']:.1f} m/s)."
        )
    return "The imposed system area fits the winner's modeled fan-side flow section more naturally."


def _build_decision_audit(
    comparison: List[Dict[str, Any]],
    velocity_constraint: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a plain-language audit trail for the screening decision."""
    best = comparison[0]
    runner_up = comparison[1] if len(comparison) > 1 else None
    passage_active = velocity_constraint["active"]
    weight_rationale = _weight_rationale(passage_active)

    if best["constraint_mode"] == "speed":
        duty_mode_summary = (
            f"Fixed RPM mode is active, so all families are being judged at the same actual "
            f"N_s = {best['specific_speed']:.2f} created by the imposed speed."
        )
    elif best["constraint_mode"] == "diameter":
        duty_mode_summary = (
            f"Fixed diameter mode is active, so all families are being judged at the same actual "
            f"D_s = {best['specific_diameter']:.2f} and matching N_s implied by that wheel size."
        )
    else:
        duty_mode_summary = (
            "No RPM or diameter was imposed, so each family was first allowed to sit near its "
            "own preferred N_s before the shortlist was compared at the same duty point."
        )

    family_screen_details = []
    candidate_outcomes = []
    for rank, candidate in enumerate(comparison, start=1):
        family_screen_details.append(
            {
                "type": candidate["short_name"],
                "summary": (
                    f"{candidate['short_name']}: N_s = {candidate['specific_speed']:.2f} versus "
                    f"a natural band of {FAN_TYPES[candidate['type_id']]['ns_min']:.2f}-"
                    f"{FAN_TYPES[candidate['type_id']]['ns_max']:.2f}"
                ),
                "detail": (
                    f"Preferred N_s band {FAN_TYPES[candidate['type_id']]['ns_min']:.2f}-"
                    f"{FAN_TYPES[candidate['type_id']]['ns_max']:.2f}; "
                    f"margin {candidate['architecture_margin']['label'].lower()}, "
                    f"score {candidate['suitability_score'] * 100:.0f}%."
                ),
            }
        )
        candidate_outcomes.append(
            {
                "rank": rank,
                "type": candidate["short_name"],
                "score_pct": round(candidate["suitability_score"] * 100.0, 1),
                "top_reason": _candidate_top_reason(candidate),
                "main_blocker": (
                    "This is the selected winner, so there is no blocker at the screening stage."
                    if rank == 1
                    else _comparative_blocker(candidate, best)
                ),
            }
        )

        realism_details = [
            f"{best['short_name']} estimated efficiency: {best['estimated_efficiency'] * 100:.1f}%.",
            f"{best['short_name']} tip speed: {best['tip_speed_ms']:.1f} m/s, so acoustic proxy risk is {best['acoustic_risk']['label'].lower()}.",
            (
                f"{best['short_name']} uses a {best['reference_geometry']['basis_label'].lower()} with "
                f"{best['reference_geometry']['effective_flow_area_m2']:.3f} m^2 effective area and "
                f"{best['reference_geometry']['reference_velocity_ms']:.1f} m/s reference velocity. "
                f"{best['reference_geometry']['override_note']}"
            ),
        (
            velocity_constraint["summary"]
            if passage_active
            else "No passage geometry was imposed, so packaging is being checked qualitatively rather than weighted directly."
        ),
    ]

    component_deltas: List[Dict[str, Any]] = []
    if runner_up is not None:
        for key in ["specific_speed_fit", "efficiency_fit", "tip_speed_fit", "passage_fit"]:
            best_contribution = best["score_breakdown"]["contributions"].get(key)
            runner_contribution = runner_up["score_breakdown"]["contributions"].get(key)
            if best_contribution is None or runner_contribution is None:
                continue
            delta = round(best_contribution - runner_contribution, 4)
            component_deltas.append(
                {
                    "component": key,
                    "best_contribution": best_contribution,
                    "runner_contribution": runner_contribution,
                    "delta": delta,
                    "why": _component_delta_reason(key, best, runner_up),
                }
            )
        component_deltas.sort(key=lambda item: abs(item["delta"]), reverse=True)

    if runner_up is not None:
        delta_points = round((best["suitability_score"] - runner_up["suitability_score"]) * 100.0, 1)
        if delta_points < 5.0:
            confidence = "Close call"
            implication = (
                f"The lead over {runner_up['short_name']} is small enough that real vendor curves, "
                "noise priorities, or packaging changes could still flip the order."
            )
        elif delta_points < 12.0:
            confidence = "Moderate separation"
            implication = (
                f"{best['short_name']} has a meaningful lead, but the runner-up still deserves a real-curve check."
            )
        else:
            confidence = "Clear separation"
            implication = (
                f"{best['short_name']} is not just slightly ahead; the current screen sees it as the natural architecture fit."
            )
    else:
        delta_points = None
        confidence = "Single candidate"
        implication = "Only one candidate was available, so there is no runner-up comparison."

    stages = [
        {
            "title": "1. Fix the duty and any imposed machine limits",
            "summary": duty_mode_summary,
            "details": [
                (
                    f"Passage geometry is active: {velocity_constraint['summary']}"
                    if passage_active
                    else "No passage geometry is active, so the initial screen is based on duty, size, and speed only."
                )
            ],
        },
        {
            "title": "2. Screen the duty-side specific speed against each family band",
            "summary": (
                "This is the main architecture filter. Specific-speed fit carries the largest score weight because "
                "family choice is fundamentally about whether the duty lands in the right N_s neighborhood."
            ),
            "details": [
                f"{item['type']}: {item['detail']}"
                for item in family_screen_details
            ],
        },
        {
            "title": "3. Apply realism modifiers",
            "summary": (
                "Families that survive the N_s screen are then separated by efficiency, tip speed, and optional "
                "passage geometry. These are sanity checks, not the primary architecture classifier."
            ),
            "details": realism_details,
        },
        {
            "title": "4. Rank the winner against the runner-up",
            "summary": implication,
            "details": [
                (
                    f"{best['short_name']} strongest positive: {_candidate_top_reason(best)}"
                ),
                (
                    f"{runner_up['short_name']} main blocker: {_candidate_main_blocker(runner_up)}"
                    if runner_up is not None
                    else "No runner-up was available."
                ),
            ],
        },
    ]

    return {
        "confidence": confidence,
        "delta_points": delta_points,
        "stages": stages,
        "weight_rationale": weight_rationale,
        "candidate_outcomes": candidate_outcomes,
        "component_deltas": component_deltas[:4],
    }


def analyze_fan_types(
    flow_m3s: float,
    pressure_pa: float,
    speed_rpm: Optional[float] = None,
    diameter_m: Optional[float] = None,
    density_kgm3: float = DEFAULT_AIR_DENSITY,
    velocity_mode: str = "none",
    target_velocity_ms: Optional[float] = None,
    passage_area_m2: Optional[float] = None,
    geometry_overrides: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Compare all supported fan types for a duty point.

    ---Parameters---
    flow_m3s : float
        Duty-point flow in m^3/s.
    pressure_pa : float
        Duty-point pressure rise in Pa.
    speed_rpm : float or None
        Optional fixed speed in RPM.
    diameter_m : float or None
        Optional fixed wheel diameter in metres.
    density_kgm3 : float
        Working-fluid density in kg/m^3.
    velocity_mode : str
        Optional passage-geometry mode: none, target_velocity, or known_area.
    target_velocity_ms : float or None
        Target bulk velocity in m/s when velocity_mode is target_velocity.
    passage_area_m2 : float or None
        Known flow area in m^2 when velocity_mode is known_area.
    geometry_overrides : dict or str or None
        Optional per-type geometry overrides for hub or eye dimensions.

    ---Returns---
    candidates : list[dict]
        Per-type comparison results sorted by descending suitability.

    ---LaTeX---
    P_{shaft} = \\frac{Q \\Delta P}{\\eta}
    U_{tip} = \\frac{\\pi D N}{60}
    """
    _validate_positive("flow", flow_m3s)
    _validate_positive("pressure rise", pressure_pa)
    _validate_positive("density", density_kgm3)

    constraint = _constraint_payload(flow_m3s, pressure_pa, density_kgm3, speed_rpm, diameter_m)
    velocity_constraint = evaluate_velocity_constraint(
        flow_m3s,
        velocity_mode,
        target_velocity_ms,
        passage_area_m2,
    )

    candidates: List[Dict[str, Any]] = []

    for type_id, type_info in FAN_TYPES.items():
        ideal_ns = type_info["ns_optimal"]
        ideal_ds = cordier_ds(ideal_ns)
        ideal_speed_rpm = speed_for_ns(ideal_ns, flow_m3s, pressure_pa, density_kgm3)
        ideal_diameter_m = diameter_for_ds(ideal_ds, flow_m3s, pressure_pa, density_kgm3)

        if constraint["mode"] == "none":
            actual_speed_rpm = ideal_speed_rpm
            actual_diameter_m = ideal_diameter_m
            actual_ns = ideal_ns
            actual_ds = ideal_ds
        else:
            actual_speed_rpm = constraint["actual_speed_rpm"]
            actual_diameter_m = constraint["actual_diameter_m"]
            actual_ns = constraint["actual_specific_speed"]
            actual_ds = constraint["actual_specific_diameter"]

        ns_fit = _range_fit_log(
            actual_ns,
            type_info["ns_min"],
            type_info["ns_max"],
            type_info["ns_optimal"],
        )
        in_range = type_info["ns_min"] <= actual_ns <= type_info["ns_max"]
        if actual_ns < type_info["ns_min"]:
            range_distance = (type_info["ns_min"] - actual_ns) / type_info["ns_optimal"]
        elif actual_ns > type_info["ns_max"]:
            range_distance = (actual_ns - type_info["ns_max"]) / type_info["ns_optimal"]
        else:
            range_distance = 0.0

        estimated_efficiency = type_info["typical_peak_efficiency"] * (0.55 + 0.45 * ns_fit)
        estimated_efficiency = min(estimated_efficiency, cordier_efficiency(max(actual_ns, 0.05)))
        shaft_power_w = flow_m3s * pressure_pa / max(estimated_efficiency, 1.0e-6)
        tip_speed_ms = math.pi * actual_diameter_m * actual_speed_rpm / 60.0
        reference_geometry = estimate_reference_geometry(
            type_id,
            actual_diameter_m,
            flow_m3s,
            geometry_overrides,
        )

        passage_fit_data = evaluate_passage_fit(
            _dominant_family(type_id),
            reference_geometry,
            velocity_constraint,
        )
        passage_fit = passage_fit_data["combined_fit"]
        nominal_size = suggest_nominal_diameter(actual_diameter_m)
        drive_fit = evaluate_drive_fit(actual_speed_rpm, shaft_power_w)
        architecture_margin = evaluate_architecture_margin(type_id, actual_ns)
        acoustic_risk = evaluate_acoustic_risk(
            type_id,
            tip_speed_ms,
            velocity_constraint,
            architecture_margin["score"],
        )
        score_breakdown = _score_breakdown(
            ns_fit,
            estimated_efficiency,
            tip_speed_ms,
            passage_fit,
        )
        suitability_score = _score_candidate(
            ns_fit,
            estimated_efficiency,
            tip_speed_ms,
            passage_fit,
        )

        candidates.append(
            {
                "type_id": type_id,
                "family": type_info["family"],
                "family_label": type_info["family_label"],
                "name": type_info["name"],
                "short_name": type_info["short_name"],
                "color": type_info["color"],
                "description": type_info["description"],
                "advantages": type_info["advantages"],
                "limitations": type_info["limitations"],
                "applications": type_info["applications"],
                "power_overloading": type_info["power_overloading"],
                "constraint_mode": constraint["mode"],
                "constraint_note": _constraint_note(
                    constraint["mode"],
                    actual_speed_rpm,
                    actual_diameter_m,
                    ideal_speed_rpm,
                    ideal_diameter_m,
                ),
                "in_range": in_range,
                "range_distance": round(range_distance, 4),
                "specific_speed": round(actual_ns, 4),
                "specific_diameter": round(actual_ds, 4),
                "ideal_specific_speed": round(ideal_ns, 4),
                "ideal_specific_diameter": round(ideal_ds, 4),
                "speed_rpm": round(actual_speed_rpm, 3),
                "diameter_m": round(actual_diameter_m, 6),
                "ideal_speed_rpm": round(ideal_speed_rpm, 3),
                "ideal_diameter_m": round(ideal_diameter_m, 6),
                "cordier_efficiency": round(cordier_efficiency(max(actual_ns, 0.05)), 4),
                "estimated_efficiency": round(estimated_efficiency, 4),
                "shaft_power_w": round(shaft_power_w, 3),
                "tip_speed_ms": round(tip_speed_ms, 4),
                "reference_geometry": reference_geometry,
                "ns_fit": round(ns_fit, 4),
                "passage_fit": passage_fit,
                "passage_area_fit": passage_fit_data["area_fit"],
                "passage_velocity_fit": passage_fit_data["velocity_fit"],
                "passage_area_ratio": passage_fit_data["area_ratio"],
                "passage_effective_diameter_ratio": passage_fit_data["effective_diameter_ratio"],
                "packaging_signature": type_info["packaging_signature"],
                "nominal_size": nominal_size,
                "drive_fit": drive_fit,
                "architecture_margin": architecture_margin,
                "acoustic_risk": acoustic_risk,
                "suitability_score": round(suitability_score, 4),
                "score_breakdown": score_breakdown,
                "strengths": _candidate_strengths(
                    type_info,
                    actual_ns,
                    passage_fit,
                    velocity_constraint,
                    drive_fit,
                    architecture_margin,
                ),
                "cautions": _candidate_cautions(
                    type_info,
                    actual_ns,
                    passage_fit,
                    velocity_constraint,
                    acoustic_risk,
                    drive_fit,
                    architecture_margin,
                ),
            }
        )

    candidates.sort(key=lambda item: item["suitability_score"], reverse=True)
    return candidates


def recommend_radial_subtype(
    specific_speed_value: float,
    predicted_diameter_m: float,
    speed_rpm: float,
    radial_passage_fit: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Split a radial recommendation into forward-curved versus backward-curved.

    ---Parameters---
    specific_speed_value : float
        Duty-side or constrained specific speed for the radial candidate.
    predicted_diameter_m : float
        Predicted wheel diameter in metres.
    speed_rpm : float
        Predicted wheel speed in RPM.
    radial_passage_fit : float or None
        Optional passage-fit score for the radial family.

    ---Returns---
    branch : dict
        Dict containing leader, runner_up, and summary text.

    ---LaTeX---
    S_{FC}, S_{BC} = f(\\omega_s, D, N)
    """
    _validate_positive("specific speed", specific_speed_value)
    _validate_positive("predicted diameter", predicted_diameter_m)
    _validate_positive("speed", speed_rpm)

    passage_fit = radial_passage_fit if radial_passage_fit is not None else 0.60
    fc_ns_fit = _range_fit_log(specific_speed_value, 0.30, 1.20, 0.60)
    bc_ns_fit = _range_fit_log(specific_speed_value, 0.30, 1.50, 0.80)

    if predicted_diameter_m <= 0.40:
        compact_bias = 0.80
    elif predicted_diameter_m <= 0.55:
        compact_bias = 0.58
    else:
        compact_bias = 0.36

    if speed_rpm < 900.0:
        low_speed_bias = 1.0
        bc_speed_bias = 0.45
    elif speed_rpm < 1500.0:
        low_speed_bias = 0.68
        bc_speed_bias = 0.72
    else:
        low_speed_bias = 0.36
        bc_speed_bias = 0.92

    fc_score = round(
        100.0
        * (
            0.45 * fc_ns_fit
            + 0.25 * compact_bias
            + 0.20 * low_speed_bias
            + 0.10 * passage_fit
        )
    )
    bc_score = round(
        100.0
        * (
            0.52 * bc_ns_fit
            + 0.23 * bc_speed_bias
            + 0.15 * passage_fit
            + 0.10 * (1.0 - 0.5 * compact_bias)
        )
    )

    fc = {
        "type_id": "centrifugal_fc",
        "name": "Forward-Curved",
        "score": fc_score,
        "copy": (
            "Compact and lower-speed friendly, but with hump-region and "
            "overloading caveats."
        ),
        "bullets": [
            "Often the better match when compactness and low nominal speed dominate.",
            "Usually chosen for cost and package reasons rather than peak efficiency.",
            "Watch stall margin and motor loading on the real fan curve.",
        ],
    }
    bc = {
        "type_id": "centrifugal_bc",
        "name": "Backward-Curved",
        "score": bc_score,
        "copy": "Efficiency-first and non-overloading, typically the safer engineered default.",
        "bullets": [
            "Usually preferred when efficiency, stability, and restrictive systems matter.",
            "Handles harder systems better than forward-curved fans.",
            "Expect a larger or faster-running package than the FC branch.",
        ],
    }

    leader = bc if bc_score >= fc_score else fc
    runner_up = fc if leader["type_id"] == "centrifugal_bc" else bc

    if leader["type_id"] == "centrifugal_bc":
        reason = "efficiency and stability outweigh compactness."
    else:
        reason = "compact packaging and lower nominal wheel speed dominate."

    return {
        "leader": leader,
        "runner_up": runner_up,
        "summary": (
            f"Within the radial family, N_s = {specific_speed_value:.2f} currently leans "
            f"toward {leader['name'].lower()} because {reason}"
        ),
    }


def _build_recommendation(
    comparison: List[Dict[str, Any]],
    velocity_constraint: Dict[str, Any],
    pressure_basis: str,
) -> Dict[str, Any]:
    """Build top-level recommendation text and handoff payload.

    ---Parameters---
    comparison : list[dict]
        Sorted output from :func:`analyze_fan_types`.
    velocity_constraint : dict
        Output from :func:`evaluate_velocity_constraint`.
    pressure_basis : str
        User-selected pressure basis label.

    ---Returns---
    recommendation : dict
        Recommendation summary with family, type, handoff payload, and summary
        text.

    ---LaTeX---
    rank = \\operatorname{sort}(S_i)
    """
    best = comparison[0]
    runner_up = comparison[1] if len(comparison) > 1 else None

    radial_branch = None
    suggested_architecture = best["family"]
    suggested_subtype = best["type_id"] if best["family"] == "radial" else None
    if best["family"] == "radial":
        radial_branch = recommend_radial_subtype(
            best["specific_speed"],
            best["diameter_m"],
            best["speed_rpm"],
            best["passage_fit"],
        )
        suggested_subtype = radial_branch["leader"]["type_id"]

    comparison_tail = ""
    if runner_up is not None:
        delta = best["suitability_score"] - runner_up["suitability_score"]
        if delta < 0.05:
            comparison_tail = (
                f"{runner_up['short_name']} is still close enough that real vendor curves "
                "could change the final order."
            )
        else:
            comparison_tail = f"{runner_up['short_name']} is the main fallback if packaging shifts."

    summary_text = (
        f"{best['short_name']} leads the current screening. "
        f"N_s = {best['specific_speed']:.2f} and Cordier D_s = {best['specific_diameter']:.2f} "
        f"imply a wheel around {best['diameter_m'] * 1000:.0f} mm at {best['speed_rpm']:.0f} RPM. "
    )
    if velocity_constraint["active"]:
        summary_text += velocity_constraint["summary"] + " "
    summary_text += comparison_tail

    practical_summary = (
        f"{best['packaging_signature']} Acoustic risk is {best['acoustic_risk']['label'].lower()} "
        f"and the drive recommendation is {best['drive_fit']['label'].lower()}. "
        f"The reference flow section is the {best['reference_geometry']['basis_label'].lower()} at "
        f"{best['reference_geometry']['effective_flow_area_m2']:.3f} m^2 effective area. "
        f"{best['reference_geometry']['override_note']} "
        f"Architecture margin is {best['architecture_margin']['label'].lower()}."
    )

    handoff = {
        "source": "fan-type-selector",
        "flow_unit": "m3/s",
        "pressure_unit": "Pa",
        "pressure_basis": pressure_basis,
        "system_mode": "quick-duty",
        "suggested_architecture": suggested_architecture,
        "suggested_subtype": suggested_subtype,
    }

    return {
        "best_type_id": best["type_id"],
        "best_family": best["family"],
        "best_name": best["name"],
        "best_short_name": best["short_name"],
        "summary_text": summary_text,
        "practical_summary": practical_summary,
        "runner_up_type_id": runner_up["type_id"] if runner_up else None,
        "runner_up_name": runner_up["short_name"] if runner_up else None,
        "radial_branch": radial_branch,
        "handoff": handoff,
    }


# =============================================================================
# FULL TOOL PAYLOAD
# =============================================================================


def full_analysis(
    flow_m3s: float,
    pressure_pa: float,
    pressure_basis: str = "static",
    speed_rpm: Optional[float] = None,
    diameter_m: Optional[float] = None,
    density_kgm3: float = DEFAULT_AIR_DENSITY,
    velocity_mode: str = "none",
    target_velocity_ms: Optional[float] = None,
    passage_area_m2: Optional[float] = None,
    geometry_overrides: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Run the complete fan type selector analysis.

    This is the main production entry point for the browser tool.

    ---Parameters---
    flow_m3s : float
        Duty-point flow in m^3/s.
    pressure_pa : float
        Pressure rise in Pa. The numeric value is interpreted according to
        ``pressure_basis``.
    pressure_basis : str
        Pressure basis label: ``static`` or ``total``.
    speed_rpm : float or None
        Optional fixed RPM constraint.
    diameter_m : float or None
        Optional fixed wheel diameter constraint in metres.
    density_kgm3 : float
        Working-fluid density in kg/m^3.
    velocity_mode : str
        Passage-geometry mode: none, target_velocity, or known_area.
    target_velocity_ms : float or None
        Passage velocity in m/s when velocity_mode is target_velocity.
    passage_area_m2 : float or None
        Known flow area in m^2 when velocity_mode is known_area.
    geometry_overrides : dict or str or None
        Optional per-type geometry overrides for hub or eye dimensions.

    ---Returns---
    analysis : dict
        JSON-serialisable payload containing comparison results, recommendation,
        Cordier data, representative curves, system curve, and derivation
        strings.

    ---LaTeX---
    \\omega_s = \\frac{\\omega \\sqrt{Q}}{(\\Delta P / \\rho)^{3/4}}
    \\delta_s = \\frac{D (\\Delta P / \\rho)^{1/4}}{\\sqrt{Q}}
    A = \\frac{Q}{V}
    """
    _validate_positive("flow", flow_m3s)
    _validate_positive("pressure rise", pressure_pa)
    _validate_positive("density", density_kgm3)
    if pressure_basis not in {"static", "total"}:
        raise ValueError("pressure_basis must be 'static' or 'total'.")

    velocity_constraint = evaluate_velocity_constraint(
        flow_m3s,
        velocity_mode,
        target_velocity_ms,
        passage_area_m2,
    )
    comparison = analyze_fan_types(
        flow_m3s=flow_m3s,
        pressure_pa=pressure_pa,
        speed_rpm=speed_rpm,
        diameter_m=diameter_m,
        density_kgm3=density_kgm3,
        velocity_mode=velocity_mode,
        target_velocity_ms=target_velocity_ms,
        passage_area_m2=passage_area_m2,
        geometry_overrides=geometry_overrides,
    )
    recommendation = _build_recommendation(comparison, velocity_constraint, pressure_basis)
    decision_audit = _build_decision_audit(comparison, velocity_constraint)
    curves = generate_representative_curves(flow_m3s, pressure_pa, density_kgm3)
    q_max = max(curve["free_delivery_flow"] for curve in curves.values())
    system = generate_system_curve(flow_m3s, pressure_pa, q_max * 1.05)
    cordier = generate_cordier_line()

    best = comparison[0]
    best_geometry = best["reference_geometry"]
    if best_geometry["section_type"] == "rotor_annulus":
        geometry_substitution = (
            r"D_h = \lambda_h D = "
            f"{best_geometry['geometry_ratio']:.3f}"
            r"\times "
            f"{best['diameter_m']:.4f}"
            r" = "
            f"{best_geometry['reference_inner_diameter_m']:.4f}\\,\\mathrm{{m}}; \\quad "
            r"A_{gross} = \frac{\pi}{4}(D^2 - D_h^2) = "
            f"{best_geometry['gross_flow_area_m2']:.4f}\\,\\mathrm{{m^2}}; \\quad "
            r"A_{eff} = \phi_b A_{gross} = "
            f"{best_geometry['blockage_factor']:.3f}"
            r"\times "
            f"{best_geometry['gross_flow_area_m2']:.4f}"
            r" = "
            f"{best_geometry['effective_flow_area_m2']:.4f}\\,\\mathrm{{m^2}}"
        )
    else:
        geometry_substitution = (
            r"D_{eye} = \lambda_e D_2 = "
            f"{best_geometry['geometry_ratio']:.3f}"
            r"\times "
            f"{best['diameter_m']:.4f}"
            r" = "
            f"{best_geometry['reference_outer_diameter_m']:.4f}\\,\\mathrm{{m}}; \\quad "
            r"D_h = \lambda_h D_{eye} = "
            f"{best_geometry['reference_inner_diameter_m'] / max(best_geometry['reference_outer_diameter_m'], 1.0e-9):.3f}"
            r"\times "
            f"{best_geometry['reference_outer_diameter_m']:.4f}"
            r" = "
            f"{best_geometry['reference_inner_diameter_m']:.4f}\\,\\mathrm{{m}}; \\quad "
            r"A_{gross} = \frac{\pi}{4}(D_{eye}^2 - D_h^2) = "
            f"{best_geometry['gross_flow_area_m2']:.4f}\\,\\mathrm{{m^2}}; \\quad "
            r"A_{eff} = \phi_b A_{gross} = "
            f"{best_geometry['blockage_factor']:.3f}"
            r"\times "
            f"{best_geometry['gross_flow_area_m2']:.4f}"
            r" = "
            f"{best_geometry['effective_flow_area_m2']:.4f}\\,\\mathrm{{m^2}}"
        )
    derivations = {
        "specific_speed": (
            r"\omega_s = \frac{\omega \sqrt{Q}}{(\Delta P / \rho)^{3/4}} = "
            f"\\frac{{({best['speed_rpm']:.1f}\\times 2\\pi/60)\\sqrt{{{flow_m3s:.3f}}}}}"
            f"{{({pressure_pa:.1f}/{density_kgm3:.3f})^{{3/4}}}} = {best['specific_speed']:.3f}"
        ),
        "specific_diameter": (
            r"\delta_s = \frac{D (\Delta P / \rho)^{1/4}}{\sqrt{Q}} = "
            f"\\frac{{{best['diameter_m']:.4f} ({pressure_pa:.1f}/{density_kgm3:.3f})^{{1/4}}}}"
            f"{{\\sqrt{{{flow_m3s:.3f}}}}} = {best['specific_diameter']:.3f}"
        ),
        "diameter_from_ds": (
            r"D = \delta_s \frac{\sqrt{Q}}{(\Delta P / \rho)^{1/4}} = "
            f"{best['specific_diameter']:.3f}"
            r"\frac{\sqrt{"
            f"{flow_m3s:.3f}"
            r"}}{("
            f"{pressure_pa:.1f}/{density_kgm3:.3f}"
            r")^{1/4}} = "
            f"{best['diameter_m']:.4f}\\,\\mathrm{{m}}"
        ),
        "reference_geometry": geometry_substitution,
        "reference_velocity": (
            r"V_{ref} = \frac{Q}{A_{eff}} = "
            f"\\frac{{{flow_m3s:.3f}}}{{{best_geometry['effective_flow_area_m2']:.4f}}}"
            f" = {best_geometry['reference_velocity_ms']:.2f}\\,\\mathrm{{m/s}}"
        ),
        "speed_from_ns": (
            r"N = \frac{60}{2\pi}\omega_s \frac{(\Delta P / \rho)^{3/4}}{\sqrt{Q}} = "
            r"\frac{60}{2\pi}"
            f"({best['specific_speed']:.3f})"
            r"\frac{("
            f"{pressure_pa:.1f}/{density_kgm3:.3f}"
            r")^{3/4}}{\sqrt{"
            f"{flow_m3s:.3f}"
            r"}} = "
            f"{best['speed_rpm']:.1f}\\,\\mathrm{{RPM}}"
        ),
        "shaft_power": (
            r"P_{shaft} = \frac{Q \Delta P}{\eta} = "
            f"\\frac{{{flow_m3s:.3f} \\times {pressure_pa:.1f}}}{{{best['estimated_efficiency']:.3f}}}"
            f" = {best['shaft_power_w']:.1f}\\,\\mathrm{{W}}"
        ),
        "tip_speed": (
            r"U_{tip} = \frac{\pi D N}{60} = "
            f"\\frac{{\\pi \\times {best['diameter_m']:.4f} \\times {best['speed_rpm']:.1f}}}{{60}}"
            f" = {best['tip_speed_ms']:.2f}\\,\\mathrm{{m/s}}"
        ),
        "drive_fit": (
            r"\epsilon_N = \min_i \left| \frac{N - N_i}{N_i} \right| = "
            r"\left| \frac{"
            f"{best['speed_rpm']:.1f} - {best['drive_fit']['nearest_rpm']:.0f}"
            r"}{"
            f"{best['drive_fit']['nearest_rpm']:.0f}"
            r"} \right| = "
            f"{best['drive_fit']['relative_error']:.3f}"
            + (
                r"; \quad T = \frac{P}{\omega} = "
                f"{best['drive_fit']['torque_nm']:.2f}\\,\\mathrm{{N\\cdot m}}"
                if best["drive_fit"]["torque_nm"] is not None
                else ""
            )
        ),
        "architecture_margin": (
            r"M = \min \left("
            r"\frac{\ln(\omega_s / \omega_{s,min})}{\ln(\omega_{s,opt} / \omega_{s,min})},"
            r"\frac{\ln(\omega_{s,max} / \omega_s)}{\ln(\omega_{s,max} / \omega_{s,opt})}"
            r"\right)"
            + " = "
            + (
                "0.000"
                if best["architecture_margin"]["score"] <= 0.0
                else f"{best['architecture_margin']['score']:.3f}"
            )
        ),
        "acoustic_risk": (
            r"R_{ac} = "
            + (
                r"0.65 R_U + 0.20 R_V + 0.15(1 - M)"
                if best["acoustic_risk"]["velocity_component"] is not None
                else r"0.82 R_U + 0.18(1 - M)"
            )
            + " = "
            + (
                f"{0.65 * best['acoustic_risk']['tip_component']:.3f}"
                + " + "
                + f"{0.20 * best['acoustic_risk']['velocity_component']:.3f}"
                + " + "
                + f"{0.15 * (1.0 - best['architecture_margin']['score']):.3f}"
                if best["acoustic_risk"]["velocity_component"] is not None
                else f"{0.82 * best['acoustic_risk']['tip_component']:.3f}"
                + " + "
                + f"{0.18 * (1.0 - best['architecture_margin']['score']):.3f}"
            )
            + " = "
            + f"{best['acoustic_risk']['index']:.3f}"
        ),
        "nominal_size": (
            f"D_{{est}} = {best['nominal_size']['estimate_mm']:.0f}\\,\\mathrm{{mm}}"
            + (
                f" \\rightarrow D_{{nom}} \\approx {best['nominal_size']['nearest_mm']}\\,\\mathrm{{mm}}"
                if len(best["nominal_size"]["bracket_mm"]) == 1
                else (
                    f" \\rightarrow \\{{{best['nominal_size']['lower_mm']}, "
                    f"{best['nominal_size']['upper_mm']}\\}}\\,\\mathrm{{mm}}"
                )
            )
        ),
        "score": (
            r"S = "
            f"{best['score_breakdown']['weights']['specific_speed_fit']:.2f}"
            r"S_N + "
            f"{best['score_breakdown']['weights']['efficiency_fit']:.2f}"
            r"S_{\eta} + "
            f"{best['score_breakdown']['weights']['tip_speed_fit']:.2f}"
            r"S_U"
            + (
                r" + "
                f"{best['score_breakdown']['weights']['passage_fit']:.2f}"
                r"S_A"
                if best["score_breakdown"]["weights"]["passage_fit"] > 0.0
                else ""
            )
            + " = "
            + f"{best['score_breakdown']['contributions']['specific_speed_fit']:.3f}"
            + " + "
            + f"{best['score_breakdown']['contributions']['efficiency_fit']:.3f}"
            + " + "
            + f"{best['score_breakdown']['contributions']['tip_speed_fit']:.3f}"
            + (
                " + "
                + f"{best['score_breakdown']['contributions']['passage_fit']:.3f}"
                if best["score_breakdown"]["contributions"]["passage_fit"] is not None
                else ""
            )
            + " = "
            + f"{best['score_breakdown']['total']:.3f}"
        ),
        "passage": None,
        "passage_area_match": None,
    }
    if velocity_constraint["active"]:
        if velocity_constraint["mode"] == "target_velocity":
            derivations["passage"] = (
                r"A = \frac{Q}{V} = "
                f"\\frac{{{flow_m3s:.3f}}}{{{velocity_constraint['velocity_ms']:.2f}}}"
                f" = {velocity_constraint['area_m2']:.4f}\\,\\mathrm{{m^2}}"
            )
        else:
            derivations["passage"] = (
                r"V = \frac{Q}{A} = "
                f"\\frac{{{flow_m3s:.3f}}}{{{velocity_constraint['area_m2']:.4f}}}"
                f" = {velocity_constraint['velocity_ms']:.2f}\\,\\mathrm{{m/s}}"
            )
        derivations["passage_area_match"] = (
            r"\phi_A = \frac{A_{sys}}{A_{fan,eff}} = "
            f"\\frac{{{velocity_constraint['area_m2']:.4f}}}{{{best_geometry['effective_flow_area_m2']:.4f}}}"
            f" = {best['passage_area_ratio']:.3f}"
        )

    type_regions = {
        type_id: {
            "short_name": info["short_name"],
            "color": info["color"],
            "family": info["family"],
            "ns_min": info["ns_min"],
            "ns_max": info["ns_max"],
            "ns_optimal": info["ns_optimal"],
        }
        for type_id, info in FAN_TYPES.items()
    }

    return {
        "comparison": comparison,
        "recommendation": recommendation,
        "decision_audit": decision_audit,
        "velocity_constraint": {
            "active": velocity_constraint["active"],
            "mode": velocity_constraint["mode"],
            "area_m2": _round_if_number(velocity_constraint["area_m2"], 6),
            "velocity_ms": _round_if_number(velocity_constraint["velocity_ms"], 6),
            "equivalent_diameter_m": _round_if_number(velocity_constraint["equivalent_diameter_m"], 6),
            "summary": velocity_constraint["summary"],
        },
        "curves": curves,
        "system": system,
        "cordier": cordier,
        "fan_types": type_regions,
        "inputs": {
            "flow_m3s": flow_m3s,
            "pressure_pa": pressure_pa,
            "pressure_basis": pressure_basis,
            "speed_rpm": speed_rpm,
            "diameter_m": diameter_m,
            "density_kgm3": density_kgm3,
            "velocity_mode": velocity_mode,
            "target_velocity_ms": target_velocity_ms,
            "passage_area_m2": passage_area_m2,
            "geometry_overrides": _normalize_geometry_overrides(geometry_overrides),
        },
        "derivations": derivations,
    }


def full_analysis_json(
    flow_m3s: float,
    pressure_pa: float,
    pressure_basis: str = "static",
    speed_rpm: Optional[float] = None,
    diameter_m: Optional[float] = None,
    density_kgm3: float = DEFAULT_AIR_DENSITY,
    velocity_mode: str = "none",
    target_velocity_ms: Optional[float] = None,
    passage_area_m2: Optional[float] = None,
    geometry_overrides: Optional[Any] = None,
) -> str:
    """
    Return :func:`full_analysis` output as a JSON string.

    ---Parameters---
    flow_m3s : float
        Duty-point flow in m^3/s.
    pressure_pa : float
        Pressure rise in Pa.
    pressure_basis : str
        Pressure basis label: static or total.
    speed_rpm : float or None
        Optional fixed RPM.
    diameter_m : float or None
        Optional fixed diameter in metres.
    density_kgm3 : float
        Working-fluid density in kg/m^3.
    velocity_mode : str
        Passage-geometry mode.
    target_velocity_ms : float or None
        Target velocity in m/s for target_velocity mode.
    passage_area_m2 : float or None
        Known area in m^2 for known_area mode.
    geometry_overrides : dict or str or None
        Optional per-type geometry overrides for hub or eye dimensions.

    ---Returns---
    analysis_json : str
        JSON string for browser / Pyodide interop.

    ---LaTeX---
    JSON = \\operatorname{serialize}(analysis)
    """
    return json.dumps(
        full_analysis(
            flow_m3s=flow_m3s,
            pressure_pa=pressure_pa,
            pressure_basis=pressure_basis,
            speed_rpm=speed_rpm,
            diameter_m=diameter_m,
            density_kgm3=density_kgm3,
            velocity_mode=velocity_mode,
            target_velocity_ms=target_velocity_ms,
            passage_area_m2=passage_area_m2,
            geometry_overrides=geometry_overrides,
        )
    )
