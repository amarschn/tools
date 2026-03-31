"""
Fan curve analysis, selection, and comparison engine.

Provides functions for:
- Piecewise-linear fan curve interpolation
- Fan/system curve intersection solving (single and multi-intersection)
- Affinity-law speed scaling and density scaling
- Multi-fan comparison with user-selected ranking
- Tiered warning generation (blocking / caution / info)
- Built-in synthetic fan archetype library for educational use
- Unit conversion for flow and pressure quantities
- Plot data generation for interactive visualization

This module has no external dependencies beyond the Python standard library.
All functions accept and return plain dicts and lists for Pyodide compatibility.

References:
- ANSI/AMCA 210-25: Laboratory methods of testing fans
- AMCA Publication 201-23: Fans and Systems
- U.S. DOE Improving Fan System Performance Sourcebook
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

# =============================================================================
# CONSTANTS
# =============================================================================

STANDARD_AIR_DENSITY = 1.225  # kg/m3, dry air at 15C, sea level (AMCA standard)
DEFAULT_AIR_DENSITY = 1.204  # kg/m3, dry air at 20C, sea level

# =============================================================================
# UNIT CONVERSION
# =============================================================================

# Flow: base unit is m3/s
FLOW_UNIT_TO_M3S = {
    "m3/s": 1.0,
    "CFM": 4.71947443e-4,
    "m3/h": 1.0 / 3600.0,
    "L/s": 1.0e-3,
}

# Pressure: base unit is Pa
PRESSURE_UNIT_TO_PA = {
    "Pa": 1.0,
    "in_wg": 249.08891,
    "kPa": 1000.0,
    "mmH2O": 9.80665,
}


def convert_flow(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a flow rate value between supported units.

    ---Parameters---
    value:
        The numeric flow rate to convert.
    from_unit:
        Source unit (m3/s, CFM, m3/h, L/s).
    to_unit:
        Target unit (m3/s, CFM, m3/h, L/s).

    ---Returns---
    result:
        The converted flow rate value.
    """
    if from_unit not in FLOW_UNIT_TO_M3S:
        raise ValueError(f"Unknown flow unit: {from_unit}")
    if to_unit not in FLOW_UNIT_TO_M3S:
        raise ValueError(f"Unknown flow unit: {to_unit}")
    base = value * FLOW_UNIT_TO_M3S[from_unit]
    return base / FLOW_UNIT_TO_M3S[to_unit]


def convert_pressure(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a pressure value between supported units.

    ---Parameters---
    value:
        The numeric pressure to convert.
    from_unit:
        Source unit (Pa, in_wg, kPa, mmH2O).
    to_unit:
        Target unit (Pa, in_wg, kPa, mmH2O).

    ---Returns---
    result:
        The converted pressure value.
    """
    if from_unit not in PRESSURE_UNIT_TO_PA:
        raise ValueError(f"Unknown pressure unit: {from_unit}")
    if to_unit not in PRESSURE_UNIT_TO_PA:
        raise ValueError(f"Unknown pressure unit: {to_unit}")
    base = value * PRESSURE_UNIT_TO_PA[from_unit]
    return base / PRESSURE_UNIT_TO_PA[to_unit]


def convert_curve_units(
    curve_points: List[List[float]],
    from_flow_unit: str,
    from_value_unit: str,
    to_flow_unit: str,
    to_value_unit: str,
) -> List[List[float]]:
    """Convert an entire curve's units (flow axis and value axis).

    ---Parameters---
    curve_points:
        List of [flow, value] pairs.
    from_flow_unit:
        Source flow unit.
    from_value_unit:
        Source value unit (pressure or power — use 'Pa' mapping for pressure).
    to_flow_unit:
        Target flow unit.
    to_value_unit:
        Target value unit.

    ---Returns---
    result:
        New list of [flow, value] pairs in the target units.
    """
    result = []
    for pt in curve_points:
        f = convert_flow(pt[0], from_flow_unit, to_flow_unit)
        v = convert_pressure(pt[1], from_value_unit, to_value_unit)
        result.append([f, v])
    return result


# =============================================================================
# AIR DENSITY
# =============================================================================


def compute_air_density(temperature_c: float = 20.0, elevation_m: float = 0.0) -> float:
    """Compute dry air density from temperature and elevation using ideal gas law.

    Uses the barometric formula for pressure at elevation and ideal gas law
    for density: rho = P / (R_specific * T).

    ---Parameters---
    temperature_c:
        Air temperature in degrees Celsius. Default 20.
    elevation_m:
        Elevation above sea level in meters. Default 0.

    ---Returns---
    density_kg_m3:
        Air density in kg/m3.

    ---LaTeX---
    \\rho = \\frac{P}{R_{specific} \\cdot T}
    P = P_0 \\left(1 - \\frac{L \\cdot h}{T_0}\\right)^{\\frac{g \\cdot M}{R \\cdot L}}
    """
    T_kelvin = temperature_c + 273.15
    # International standard atmosphere parameters
    P0 = 101325.0  # Pa, sea-level pressure
    L = 0.0065  # K/m, temperature lapse rate
    T0 = 288.15  # K, sea-level standard temperature
    g = 9.80665  # m/s2
    M = 0.0289644  # kg/mol, molar mass of dry air
    R = 8.31447  # J/(mol*K), universal gas constant
    R_specific = 287.058  # J/(kg*K), specific gas constant for dry air

    if elevation_m == 0.0:
        P = P0
    else:
        exponent = (g * M) / (R * L)
        P = P0 * (1.0 - (L * elevation_m) / T0) ** exponent

    return P / (R_specific * T_kelvin)


# =============================================================================
# INTERPOLATION
# =============================================================================


def interpolate_curve(
    curve_points: List[List[float]],
    query_flow: float,
    clamp: bool = True,
) -> Optional[float]:
    """Piecewise-linear interpolation on a fan curve.

    Points are sorted by flow internally. By default the function clamps at the
    data boundaries rather than extrapolating. Set ``clamp=False`` to return
    ``None`` outside the curve domain.

    ---Parameters---
    curve_points:
        List of [flow, value] pairs. Minimum 2 points.
    query_flow:
        The flow rate at which to evaluate the curve.
    clamp:
        When True, return the nearest endpoint value outside the curve domain.
        When False, return None outside the domain.

    ---Returns---
    value:
        Interpolated value, or None if curve_points is empty/invalid.
    """
    if not curve_points or len(curve_points) < 2:
        return None
    points = sorted(curve_points, key=lambda p: p[0])
    if query_flow <= points[0][0]:
        return points[0][1] if clamp else None
    if query_flow >= points[-1][0]:
        return points[-1][1] if clamp else None
    for i in range(len(points) - 1):
        if points[i][0] <= query_flow <= points[i + 1][0]:
            dq = points[i + 1][0] - points[i][0]
            if dq == 0:
                return points[i][1]
            frac = (query_flow - points[i][0]) / dq
            return points[i][1] + frac * (points[i + 1][1] - points[i][1])
    return points[-1][1]


def evaluate_curve_array(
    curve_points: List[List[float]],
    flow_array: List[float],
    clamp: bool = True,
) -> List[Optional[float]]:
    """Evaluate a piecewise-linear curve at an array of flow values.

    ---Parameters---
    curve_points:
        List of [flow, value] pairs.
    flow_array:
        List of flow values to evaluate at.
    clamp:
        Whether to clamp outside the curve domain.

    ---Returns---
    values:
        List of interpolated values.
    """
    return [interpolate_curve(curve_points, q, clamp=clamp) for q in flow_array]


# =============================================================================
# SCALING (AFFINITY LAWS & DENSITY)
# =============================================================================


def scale_curve_speed(
    curve_points: List[List[float]],
    ref_rpm: float,
    operating_rpm: float,
    curve_type: str = "pressure",
) -> List[List[float]]:
    """Scale a fan curve using affinity laws for a speed change.

    Pressure curves: Q2 = Q1*(N2/N1), dP2 = dP1*(N2/N1)^2
    Power curves: Q2 = Q1*(N2/N1), P2 = P1*(N2/N1)^3
    Efficiency curves: Q2 = Q1*(N2/N1), eta unchanged

    ---Parameters---
    curve_points:
        List of [flow, value] pairs at reference speed.
    ref_rpm:
        Reference speed in RPM.
    operating_rpm:
        Operating speed in RPM.
    curve_type:
        One of 'pressure', 'power', or 'efficiency'.

    ---Returns---
    scaled_points:
        New list of [flow, value] pairs at operating speed.

    ---LaTeX---
    Q_2 = Q_1 \\cdot \\frac{N_2}{N_1}
    \\Delta P_2 = \\Delta P_1 \\cdot \\left(\\frac{N_2}{N_1}\\right)^2
    P_2 = P_1 \\cdot \\left(\\frac{N_2}{N_1}\\right)^3
    """
    if ref_rpm <= 0:
        raise ValueError("Reference RPM must be positive.")
    ratio = operating_rpm / ref_rpm
    result = []
    for pt in curve_points:
        q_new = pt[0] * ratio
        if curve_type == "pressure":
            v_new = pt[1] * ratio**2
        elif curve_type == "power":
            v_new = pt[1] * ratio**3
        elif curve_type == "efficiency":
            v_new = pt[1]  # Efficiency unchanged by speed (ideal)
        else:
            raise ValueError(f"Unknown curve_type: {curve_type}")
        result.append([q_new, v_new])
    return result


def scale_curve_density(
    curve_points: List[List[float]],
    ref_density: float,
    operating_density: float,
) -> List[List[float]]:
    """Scale a fan pressure or power curve for a density change.

    Flow axis unchanged. Pressure and power scale by density ratio.

    ---Parameters---
    curve_points:
        List of [flow, value] pairs at reference density.
    ref_density:
        Reference air density in kg/m3.
    operating_density:
        Operating air density in kg/m3.

    ---Returns---
    scaled_points:
        New list of [flow, value] pairs at operating density.

    ---LaTeX---
    \\Delta P_{op} = \\Delta P_{ref} \\cdot \\frac{\\rho_{op}}{\\rho_{ref}}
    """
    if ref_density <= 0:
        raise ValueError("Reference density must be positive.")
    ratio = operating_density / ref_density
    return [[pt[0], pt[1] * ratio] for pt in curve_points]


# =============================================================================
# SYSTEM CURVE
# =============================================================================


def infer_system_k(
    duty_flow: float,
    duty_pressure: float,
    dp_fixed: float = 0.0,
    margin: float = 0.0,
) -> float:
    """Infer the quadratic resistance coefficient K from a duty point.

    K = (dP_duty - dP_fixed - margin) / Q_duty^2

    ---Parameters---
    duty_flow:
        Target airflow in m3/s.
    duty_pressure:
        Target pressure in Pa.
    dp_fixed:
        Fixed pressure loss component in Pa. Default 0.
    margin:
        Additional installation or design margin in Pa. Default 0.

    ---Returns---
    k_coefficient:
        System resistance coefficient in Pa/(m3/s)^2.
    """
    if duty_flow <= 0:
        raise ValueError("Duty flow must be positive.")
    net = duty_pressure - dp_fixed - margin
    if net < 0:
        raise ValueError("Duty pressure must be >= dp_fixed + margin.")
    return net / (duty_flow**2)


def evaluate_system_curve(
    flow_values: List[float],
    k_coefficient: float,
    dp_fixed: float = 0.0,
    margin: float = 0.0,
) -> List[float]:
    """Evaluate the system curve at given flow values.

    dP_system(Q) = dP_fixed + K * Q^2 + margin

    ---Parameters---
    flow_values:
        List of flow rates in m3/s.
    k_coefficient:
        Quadratic resistance coefficient.
    dp_fixed:
        Fixed pressure loss in Pa.
    margin:
        Installation margin in Pa.

    ---Returns---
    pressures:
        List of system pressures in Pa.
    """
    return [dp_fixed + k_coefficient * q**2 + margin for q in flow_values]


def system_pressure_at_flow(
    flow: float, k_coefficient: float, dp_fixed: float = 0.0, margin: float = 0.0
) -> float:
    """Evaluate system pressure at a single flow value."""
    return dp_fixed + k_coefficient * flow**2 + margin


# =============================================================================
# INTERSECTION SOLVER
# =============================================================================


def find_intersections(
    fan_curve_points: List[List[float]],
    k_coefficient: float,
    dp_fixed: float = 0.0,
    margin: float = 0.0,
) -> List[Dict]:
    """Find all intersection points between a piecewise-linear fan curve and
    a quadratic system curve.

    For each linear segment of the fan curve, solves analytically for the
    intersection with dP_system = dP_fixed + K*Q^2 + margin.

    Each intersection is classified as stable or unstable based on the
    relative slopes: if the fan curve is falling faster than the system curve
    is rising at the intersection, it is the stable operating point.

    ---Parameters---
    fan_curve_points:
        List of [flow, pressure] pairs defining the fan curve.
    k_coefficient:
        System quadratic resistance coefficient.
    dp_fixed:
        System fixed pressure loss in Pa.
    margin:
        System installation margin in Pa.

    ---Returns---
    intersections:
        List of dicts, each with keys: flow, pressure, is_stable,
        fan_slope, system_slope, intersection_angle_deg.
    """
    if not fan_curve_points or len(fan_curve_points) < 2:
        return []

    points = sorted(fan_curve_points, key=lambda p: p[0])
    intersections = []

    for i in range(len(points) - 1):
        q1, p1 = points[i]
        q2, p2 = points[i + 1]
        dq = q2 - q1
        if dq <= 0:
            continue

        # Fan segment: P_fan(Q) = p1 + ((p2-p1)/(q2-q1)) * (Q - q1)
        #            = p1 + m*(Q - q1)   where m = (p2-p1)/(q2-q1)
        # System:     P_sys(Q) = dp_fixed + K*Q^2 + margin
        #
        # Set equal: dp_fixed + K*Q^2 + margin = p1 + m*(Q - q1)
        # K*Q^2 - m*Q + (dp_fixed + margin - p1 + m*q1) = 0

        m = (p2 - p1) / dq
        c = dp_fixed + margin - p1 + m * q1

        # Quadratic: K*Q^2 - m*Q + c = 0
        a_coeff = k_coefficient
        b_coeff = -m
        c_coeff = c

        if abs(a_coeff) < 1e-15:
            # Degenerate: linear system curve
            if abs(b_coeff) < 1e-15:
                continue
            q_int = -c_coeff / b_coeff
        else:
            discriminant = b_coeff**2 - 4 * a_coeff * c_coeff
            if discriminant < 0:
                continue
            sqrt_d = math.sqrt(discriminant)
            roots = [
                (-b_coeff + sqrt_d) / (2 * a_coeff),
                (-b_coeff - sqrt_d) / (2 * a_coeff),
            ]
            for q_int in roots:
                if q1 - 1e-9 <= q_int <= q2 + 1e-9:
                    q_int = max(q1, min(q2, q_int))
                    p_int = system_pressure_at_flow(q_int, k_coefficient, dp_fixed, margin)

                    # Slopes at intersection
                    fan_slope = m
                    system_slope = 2 * k_coefficient * q_int

                    # Stability: stable if fan curve drops faster than system rises
                    # i.e., fan_slope < system_slope (fan_slope is typically negative)
                    is_stable = fan_slope < system_slope

                    # Intersection angle
                    angle_rad = abs(math.atan(fan_slope) - math.atan(system_slope))
                    angle_deg = math.degrees(angle_rad)

                    intersections.append({
                        "flow": q_int,
                        "pressure": p_int,
                        "is_stable": is_stable,
                        "fan_slope": fan_slope,
                        "system_slope": system_slope,
                        "intersection_angle_deg": angle_deg,
                    })
            continue  # We already processed roots in the loop above

        # Handle the single-root (linear system) case
        if q1 - 1e-9 <= q_int <= q2 + 1e-9:
            q_int = max(q1, min(q2, q_int))
            p_int = system_pressure_at_flow(q_int, k_coefficient, dp_fixed, margin)
            fan_slope = m
            system_slope = 2 * k_coefficient * q_int
            is_stable = fan_slope < system_slope
            angle_rad = abs(math.atan(fan_slope) - math.atan(system_slope))
            angle_deg = math.degrees(angle_rad)
            intersections.append({
                "flow": q_int,
                "pressure": p_int,
                "is_stable": is_stable,
                "fan_slope": fan_slope,
                "system_slope": system_slope,
                "intersection_angle_deg": angle_deg,
            })

    # Remove near-duplicate intersections (within 0.1% of flow range)
    if intersections:
        flow_range = points[-1][0] - points[0][0]
        tol = flow_range * 0.001 if flow_range > 0 else 1e-9
        unique = [intersections[0]]
        for ix in intersections[1:]:
            if abs(ix["flow"] - unique[-1]["flow"]) > tol:
                unique.append(ix)
        intersections = unique

    return intersections


# =============================================================================
# VALIDATION AND WARNINGS
# =============================================================================

def validate_curve_data(curve_points: List[List[float]]) -> List[Dict]:
    """Validate fan curve data and return any warnings.

    ---Parameters---
    curve_points:
        List of [flow, value] pairs.

    ---Returns---
    warnings:
        List of warning dicts with keys: tier, code, message.
    """
    warnings = []
    if not curve_points:
        warnings.append({
            "tier": "blocking",
            "code": "no-data",
            "message": "No curve data provided.",
        })
        return warnings

    if len(curve_points) < 3:
        warnings.append({
            "tier": "blocking",
            "code": "insufficient-points",
            "message": f"Fan curve has only {len(curve_points)} points. Minimum 3 required for reliable interpolation.",
        })

    for i, pt in enumerate(curve_points):
        if pt[0] < 0:
            warnings.append({
                "tier": "blocking",
                "code": "negative-flow",
                "message": f"Point {i+1} has negative flow ({pt[0]}). Flow must be >= 0.",
            })
        if pt[1] < 0:
            warnings.append({
                "tier": "caution",
                "code": "negative-value",
                "message": f"Point {i+1} has negative pressure/power ({pt[1]}). Check data.",
            })

    flows = [pt[0] for pt in curve_points]
    if flows != sorted(flows):
        warnings.append({
            "tier": "caution",
            "code": "unsorted-flow",
            "message": "Flow values are not in ascending order. Data will be sorted automatically.",
        })

    # Check for duplicates
    seen = set()
    for f in flows:
        if f in seen:
            warnings.append({
                "tier": "caution",
                "code": "duplicate-flow",
                "message": f"Duplicate flow value: {f}. Only the first occurrence will be used.",
            })
            break
        seen.add(f)

    return warnings


def generate_warnings(
    fan_candidate: Dict,
    operating_result: Dict,
    ref_density: float,
    operating_density: float,
    system_source_mode: str,
) -> List[Dict]:
    """Generate the full tiered warning list for an operating point result.

    ---Parameters---
    fan_candidate:
        The fan candidate dict.
    operating_result:
        The computed operating point result dict.
    ref_density:
        Fan's reference density in kg/m3.
    operating_density:
        Operating air density in kg/m3.
    system_source_mode:
        How the system curve was defined: 'duty-point-inferred', 'direct-k', 'reference-point'.

    ---Returns---
    warnings:
        List of warning dicts with keys: tier, code, message.
    """
    warnings = []

    # Blocking
    if operating_result.get("operating_flow") is None:
        warnings.append({
            "tier": "blocking",
            "code": "no-intersection",
            "message": "No valid operating point found. The fan cannot meet the system requirements at this speed and density.",
        })

    # Caution
    density_ratio = abs(operating_density - ref_density) / ref_density if ref_density > 0 else 0
    if density_ratio > 0.01:
        warnings.append({
            "tier": "caution",
            "code": "density-correction",
            "message": f"Density correction applied: {ref_density:.3f} -> {operating_density:.3f} kg/m3. This is an incompressible approximation.",
        })

    ref_rpm = fan_candidate.get("reference_speed_rpm", 0)
    op_rpm = fan_candidate.get("operating_speed_rpm", ref_rpm)
    if ref_rpm > 0 and op_rpm != ref_rpm:
        speed_dev = abs(op_rpm - ref_rpm) / ref_rpm
        if speed_dev > 0.30:
            warnings.append({
                "tier": "caution",
                "code": "large-speed-deviation",
                "message": f"Speed scaled by {speed_dev*100:.0f}% from reference ({ref_rpm} to {op_rpm} RPM). Affinity law accuracy degrades significantly beyond ~30%.",
            })
        elif speed_dev > 0.01:
            warnings.append({
                "tier": "caution",
                "code": "speed-scaling",
                "message": f"Speed scaling applied: {ref_rpm} to {op_rpm} RPM. Affinity laws are an approximation.",
            })

    if operating_result.get("has_unstable_intersection"):
        warnings.append({
            "tier": "caution",
            "code": "dual-intersection",
            "message": "This fan has two mathematical operating points at this system curve. The stable point (higher flow) is shown. The unstable point may cause surge or hunting.",
        })

    angle = operating_result.get("intersection_angle_deg")
    if angle is not None and angle < 15:
        warnings.append({
            "tier": "caution",
            "code": "shallow-intersection",
            "message": f"Shallow intersection angle ({angle:.1f} deg). Small system changes will cause large flow shifts. Consider a fan with a steeper curve in this region.",
        })

    # Info
    if fan_candidate.get("power_curve") is None:
        warnings.append({
            "tier": "info",
            "code": "no-power-data",
            "message": "No power data supplied. Efficiency cannot be computed.",
        })

    if system_source_mode == "duty-point-inferred":
        warnings.append({
            "tier": "info",
            "code": "inferred-system",
            "message": "System curve inferred from duty point (pure quadratic assumption). For a more accurate model, use the System Curve Builder.",
        })

    if fan_candidate.get("source_type") == "library-archetype":
        warnings.append({
            "tier": "info",
            "code": "archetype-data",
            "message": "Using synthetic archetype data for educational purposes. Not a real product.",
        })

    if fan_candidate.get("preferred_operating_region") is None:
        warnings.append({
            "tier": "info",
            "code": "no-preferred-range",
            "message": "Preferred operating range not available. Distance from peak efficiency shown as a heuristic.",
        })

    return warnings


# =============================================================================
# OPERATING POINT ANALYSIS
# =============================================================================


def analyze_fan_operating_point(
    fan_candidate: Dict,
    duty_flow: float,
    duty_pressure: float,
    k_coefficient: float,
    dp_fixed: float = 0.0,
    margin: float = 0.0,
    operating_density: float = DEFAULT_AIR_DENSITY,
    system_source_mode: str = "duty-point-inferred",
    operating_hours: float = 8760.0,
    electricity_rate: float = 0.12,
    required_pressure_basis: Optional[str] = None,
) -> Dict:
    """Analyze a single fan's operating point against a system curve.

    This is the primary analysis function. It handles density scaling,
    speed scaling, intersection solving, efficiency computation, and
    warning generation.

    ---Parameters---
    fan_candidate:
        Dict matching the FanCandidate data model. Must include at minimum:
        pressure_curve (list of [flow, pressure] pairs), reference_speed_rpm,
        reference_density_kg_m3, pressure_basis.
    duty_flow:
        Target airflow in m3/s.
    duty_pressure:
        Target pressure in Pa.
    k_coefficient:
        System quadratic resistance coefficient.
    dp_fixed:
        System fixed pressure loss in Pa.
    margin:
        System installation margin in Pa.
    operating_density:
        Operating air density in kg/m3.
    system_source_mode:
        How the system curve was defined.
    operating_hours:
        Annual operating hours for energy estimate.
    electricity_rate:
        Electricity cost in $/kWh.

    ---Returns---
    result:
        Dict matching the OperatingPointResult data model.
    """
    result = {
        "candidate_id": fan_candidate.get("candidate_id", "unknown"),
        "meets_duty": False,
        "operating_flow": None,
        "operating_pressure": None,
        "operating_speed_rpm": None,
        "shaft_power_w": None,
        "electrical_power_w": None,
        "operating_efficiency": None,
        "distance_from_peak_efficiency": None,
        "intersection_angle_deg": None,
        "has_unstable_intersection": False,
        "unstable_intersection_flow": None,
        "annual_energy_kwh": None,
        "annual_energy_cost": None,
        "duty_margin_pressure": None,
        "duty_margin_fraction": None,
        "warning_tier": "clear",
        "warnings": [],
    }

    # Validate curve data
    pressure_curve = fan_candidate.get("pressure_curve", [])
    curve_warnings = validate_curve_data(pressure_curve)
    has_blocking = any(w["tier"] == "blocking" for w in curve_warnings)
    if has_blocking:
        result["warnings"] = curve_warnings
        result["warning_tier"] = "blocking"
        return result

    fan_pressure_basis = fan_candidate.get("pressure_basis", "static")
    if required_pressure_basis and fan_pressure_basis != required_pressure_basis:
        result["warnings"] = [{
            "tier": "blocking",
            "code": "pressure-basis-mismatch",
            "message": (
                f"Pressure basis mismatch: system is on a {required_pressure_basis} basis "
                f"but fan data is marked {fan_pressure_basis}. Match the basis before comparing."
            ),
        }]
        result["warning_tier"] = "blocking"
        return result

    # Apply scaling
    ref_density = fan_candidate.get("reference_density_kg_m3", STANDARD_AIR_DENSITY)
    ref_rpm = fan_candidate.get("reference_speed_rpm", 0)
    op_rpm = fan_candidate.get("operating_speed_rpm", ref_rpm)

    scaled_pressure = list(pressure_curve)

    # Density scaling
    if abs(operating_density - ref_density) / ref_density > 0.001:
        scaled_pressure = scale_curve_density(scaled_pressure, ref_density, operating_density)

    # Speed scaling
    if ref_rpm > 0 and abs(op_rpm - ref_rpm) > 0.1:
        scaled_pressure = scale_curve_speed(scaled_pressure, ref_rpm, op_rpm, "pressure")

    # Find intersections
    intersections = find_intersections(scaled_pressure, k_coefficient, dp_fixed, margin)

    if not intersections:
        result["operating_speed_rpm"] = op_rpm
        result["warnings"] = generate_warnings(
            fan_candidate, result, ref_density, operating_density, system_source_mode
        )
        result["warnings"].extend(curve_warnings)
        result["warning_tier"] = "blocking"
        return result

    # Select stable intersection (highest flow among stable, or highest flow if none stable)
    stable = [ix for ix in intersections if ix["is_stable"]]
    if stable:
        primary = max(stable, key=lambda ix: ix["flow"])
    else:
        primary = max(intersections, key=lambda ix: ix["flow"])

    result["operating_flow"] = primary["flow"]
    result["operating_pressure"] = primary["pressure"]
    result["operating_speed_rpm"] = op_rpm
    result["intersection_angle_deg"] = primary["intersection_angle_deg"]

    # Check for unstable intersections
    unstable = [ix for ix in intersections if not ix["is_stable"]]
    if unstable:
        result["has_unstable_intersection"] = True
        result["unstable_intersection_flow"] = unstable[0]["flow"]

    # Duty check
    duty_system_pressure = system_pressure_at_flow(duty_flow, k_coefficient, dp_fixed, margin)
    fan_pressure_at_duty = interpolate_curve(scaled_pressure, duty_flow, clamp=False)
    if fan_pressure_at_duty is not None:
        result["duty_margin_pressure"] = fan_pressure_at_duty - duty_system_pressure
        if duty_system_pressure > 0:
            result["duty_margin_fraction"] = (
                result["duty_margin_pressure"] / duty_system_pressure
            )
    if fan_pressure_at_duty is not None and fan_pressure_at_duty >= duty_system_pressure * 0.99:
        result["meets_duty"] = True

    # Power and efficiency
    power_curve = fan_candidate.get("power_curve")
    if power_curve:
        scaled_power = list(power_curve)
        if abs(operating_density - ref_density) / ref_density > 0.001:
            scaled_power = scale_curve_density(scaled_power, ref_density, operating_density)
        if ref_rpm > 0 and abs(op_rpm - ref_rpm) > 0.1:
            scaled_power = scale_curve_speed(scaled_power, ref_rpm, op_rpm, "power")

        shaft_power = interpolate_curve(scaled_power, primary["flow"])
        if shaft_power is not None and shaft_power > 0:
            result["shaft_power_w"] = shaft_power

            # Efficiency
            eta = (primary["flow"] * primary["pressure"]) / shaft_power
            result["operating_efficiency"] = min(eta, 1.0)

            # Electrical power
            motor_eff = fan_candidate.get("motor_efficiency")
            vfd_eff = fan_candidate.get("vfd_efficiency")
            elec_power = shaft_power
            if motor_eff and motor_eff > 0:
                elec_power = elec_power / motor_eff
            if vfd_eff and vfd_eff > 0:
                elec_power = elec_power / vfd_eff
            result["electrical_power_w"] = elec_power

            # Annual energy
            result["annual_energy_kwh"] = elec_power * operating_hours / 1000.0
            result["annual_energy_cost"] = result["annual_energy_kwh"] * electricity_rate

    # Peak efficiency distance
    efficiency_curve = fan_candidate.get("efficiency_curve")
    if efficiency_curve and len(efficiency_curve) >= 2:
        peak_eff = max(pt[1] for pt in efficiency_curve)
        if peak_eff > 0 and result["operating_efficiency"] is not None:
            result["distance_from_peak_efficiency"] = result["operating_efficiency"] / peak_eff
    elif result["operating_efficiency"] is not None and power_curve:
        # Compute efficiency at each power curve point to find peak
        efficiencies = []
        for pt in scaled_pressure:
            q = pt[0]
            p = pt[1]
            pwr = interpolate_curve(
                scale_curve_density(power_curve, ref_density, operating_density)
                if abs(operating_density - ref_density) / ref_density > 0.001
                else power_curve,
                q,
            )
            if pwr and pwr > 0 and q > 0:
                efficiencies.append((q * p) / pwr)
        if efficiencies:
            peak_eff = max(efficiencies)
            if peak_eff > 0:
                result["distance_from_peak_efficiency"] = result["operating_efficiency"] / peak_eff

    # Generate warnings
    result["warnings"] = generate_warnings(
        fan_candidate, result, ref_density, operating_density, system_source_mode
    )
    result["warnings"].extend(curve_warnings)

    # Determine overall warning tier
    tiers = [w["tier"] for w in result["warnings"]]
    if "blocking" in tiers:
        result["warning_tier"] = "blocking"
    elif "caution" in tiers:
        result["warning_tier"] = "caution"
    elif "info" in tiers:
        result["warning_tier"] = "info"
    else:
        result["warning_tier"] = "clear"

    return result


# =============================================================================
# COMPARISON ENGINE
# =============================================================================

RANKING_CRITERIA = {
    "lowest_shaft_power": {
        "key": "shaft_power_w",
        "ascending": True,
        "label": "Lowest Shaft Power",
    },
    "lowest_annual_cost": {
        "key": "annual_energy_cost",
        "ascending": True,
        "label": "Lowest Annual Cost",
    },
    "highest_efficiency": {
        "key": "operating_efficiency",
        "ascending": False,
        "label": "Highest Efficiency at Duty",
    },
    "most_duty_margin": {
        "key": "_duty_margin",
        "ascending": False,
        "label": "Most Duty Margin",
    },
    "most_stable": {
        "key": "intersection_angle_deg",
        "ascending": False,
        "label": "Most Stable Intersection",
    },
}


def compare_fans(
    fan_candidates: List[Dict],
    duty_flow: float,
    duty_pressure: float,
    k_coefficient: float,
    dp_fixed: float = 0.0,
    margin: float = 0.0,
    operating_density: float = DEFAULT_AIR_DENSITY,
    system_source_mode: str = "duty-point-inferred",
    operating_hours: float = 8760.0,
    electricity_rate: float = 0.12,
    ranking_criterion: Optional[str] = None,
    required_pressure_basis: Optional[str] = None,
) -> Dict:
    """Compare multiple candidate fans at the same duty point.

    ---Parameters---
    fan_candidates:
        List of fan candidate dicts.
    duty_flow:
        Target airflow in m3/s.
    duty_pressure:
        Target pressure in Pa.
    k_coefficient:
        System quadratic resistance coefficient.
    dp_fixed:
        System fixed pressure loss in Pa.
    margin:
        System installation margin in Pa.
    operating_density:
        Operating air density in kg/m3.
    system_source_mode:
        How the system curve was defined.
    operating_hours:
        Annual operating hours.
    electricity_rate:
        Electricity cost in $/kWh.
    ranking_criterion:
        Optional key from RANKING_CRITERIA for sorting.
    required_pressure_basis:
        Required pressure basis for candidate compatibility checks.

    ---Returns---
    comparison:
        Dict with keys: results (list of OperatingPointResult dicts),
        ranked_order (list of candidate_ids in ranked order),
        ranking_criterion (the criterion used or None).
    """
    results = []
    for fan in fan_candidates:
        r = analyze_fan_operating_point(
            fan_candidate=fan,
            duty_flow=duty_flow,
            duty_pressure=duty_pressure,
            k_coefficient=k_coefficient,
            dp_fixed=dp_fixed,
            margin=margin,
            operating_density=operating_density,
            system_source_mode=system_source_mode,
            operating_hours=operating_hours,
            electricity_rate=electricity_rate,
            required_pressure_basis=required_pressure_basis,
        )
        results.append(r)

    # Ranking
    ranked_order = [r["candidate_id"] for r in results]
    if ranking_criterion and ranking_criterion in RANKING_CRITERIA:
        rc = RANKING_CRITERIA[ranking_criterion]
        key_name = rc["key"]

        def sort_key(r):
            if key_name == "_duty_margin":
                if r.get("duty_margin_pressure") is not None:
                    return r["duty_margin_pressure"]
                return float("-inf")
            val = r.get(key_name)
            if val is None:
                return float("-inf") if not rc["ascending"] else float("inf")
            return val

        sorted_results = sorted(results, key=sort_key, reverse=not rc["ascending"])
        ranked_order = [r["candidate_id"] for r in sorted_results]

    return {
        "results": results,
        "ranked_order": ranked_order,
        "ranking_criterion": ranking_criterion,
    }


# =============================================================================
# PLOT DATA GENERATION
# =============================================================================


def generate_plot_data(
    fan_candidates: List[Dict],
    k_coefficient: float,
    dp_fixed: float = 0.0,
    margin: float = 0.0,
    operating_density: float = DEFAULT_AIR_DENSITY,
    duty_flow: float = 0.0,
    duty_pressure: float = 0.0,
    n_points: int = 100,
) -> Dict:
    """Generate structured data for the frontend to render all plots.

    ---Parameters---
    fan_candidates:
        List of fan candidate dicts.
    k_coefficient:
        System quadratic resistance coefficient.
    dp_fixed:
        System fixed pressure loss in Pa.
    margin:
        System installation margin in Pa.
    operating_density:
        Operating air density in kg/m3.
    duty_flow:
        Target airflow in m3/s.
    duty_pressure:
        Target pressure in Pa.
    n_points:
        Number of points for smooth curve rendering.

    ---Returns---
    plot_data:
        Dict with keys: flow_range, system_curve, fan_curves (list of dicts
        with scaled_pressure, ghost_pressure, power, efficiency, operating_points),
        duty_point.
    """
    # Determine flow range from all fans
    all_flows = []
    for fan in fan_candidates:
        pc = fan.get("pressure_curve", [])
        if pc:
            ref_density = fan.get("reference_density_kg_m3", STANDARD_AIR_DENSITY)
            ref_rpm = fan.get("reference_speed_rpm", 0)
            op_rpm = fan.get("operating_speed_rpm", ref_rpm)
            scaled = list(pc)
            if abs(operating_density - ref_density) / ref_density > 0.001:
                scaled = scale_curve_density(scaled, ref_density, operating_density)
            if ref_rpm > 0 and abs(op_rpm - ref_rpm) > 0.1:
                scaled = scale_curve_speed(scaled, ref_rpm, op_rpm, "pressure")
            all_flows.extend([pt[0] for pt in scaled])
    if duty_flow > 0:
        all_flows.append(duty_flow * 1.2)

    if not all_flows:
        return {"flow_range": [], "system_curve": [], "fan_curves": [], "duty_point": None}

    q_min = 0.0
    q_max = max(all_flows) * 1.15
    flow_range = [q_min + i * (q_max - q_min) / n_points for i in range(n_points + 1)]

    # System curve
    system_curve = evaluate_system_curve(flow_range, k_coefficient, dp_fixed, margin)

    # Fan curves
    fan_plot_data = []
    for fan in fan_candidates:
        pc = fan.get("pressure_curve", [])
        if not pc:
            continue

        ref_density = fan.get("reference_density_kg_m3", STANDARD_AIR_DENSITY)
        ref_rpm = fan.get("reference_speed_rpm", 0)
        op_rpm = fan.get("operating_speed_rpm", ref_rpm)

        # Scaled pressure curve
        scaled_pressure = list(pc)
        if abs(operating_density - ref_density) / ref_density > 0.001:
            scaled_pressure = scale_curve_density(scaled_pressure, ref_density, operating_density)
        if ref_rpm > 0 and abs(op_rpm - ref_rpm) > 0.1:
            scaled_pressure = scale_curve_speed(scaled_pressure, ref_rpm, op_rpm, "pressure")

        scaled_p_values = evaluate_curve_array(scaled_pressure, flow_range, clamp=False)

        # Ghost curve (original speed, for comparison when speed differs)
        ghost_p_values = None
        if ref_rpm > 0 and abs(op_rpm - ref_rpm) > 0.1:
            ghost = list(pc)
            if abs(operating_density - ref_density) / ref_density > 0.001:
                ghost = scale_curve_density(ghost, ref_density, operating_density)
            ghost_p_values = evaluate_curve_array(ghost, flow_range, clamp=False)

        # Operating points
        intersections = find_intersections(scaled_pressure, k_coefficient, dp_fixed, margin)

        # Power curve
        power_values = None
        pwr_curve = fan.get("power_curve")
        if pwr_curve:
            scaled_power = list(pwr_curve)
            if abs(operating_density - ref_density) / ref_density > 0.001:
                scaled_power = scale_curve_density(scaled_power, ref_density, operating_density)
            if ref_rpm > 0 and abs(op_rpm - ref_rpm) > 0.1:
                scaled_power = scale_curve_speed(scaled_power, ref_rpm, op_rpm, "power")
            power_values = evaluate_curve_array(scaled_power, flow_range, clamp=False)

        # Efficiency curve
        efficiency_values = None
        eff_curve = fan.get("efficiency_curve")
        if eff_curve:
            scaled_eff = list(eff_curve)
            if ref_rpm > 0 and abs(op_rpm - ref_rpm) > 0.1:
                scaled_eff = scale_curve_speed(scaled_eff, ref_rpm, op_rpm, "efficiency")
            efficiency_values = evaluate_curve_array(scaled_eff, flow_range, clamp=False)
        elif power_values and scaled_p_values:
            # Derive efficiency from pressure and power
            efficiency_values = []
            for i in range(len(flow_range)):
                q = flow_range[i]
                p = scaled_p_values[i]
                pwr = power_values[i]
                if q > 0 and p is not None and pwr is not None and pwr > 0:
                    efficiency_values.append(min((q * p) / pwr, 1.0))
                else:
                    efficiency_values.append(None)

        fan_plot_data.append({
            "candidate_id": fan.get("candidate_id", ""),
            "title": fan.get("title", ""),
            "source_type": fan.get("source_type", "user-entered"),
            "pressure_values": scaled_p_values,
            "ghost_pressure_values": ghost_p_values,
            "power_values": power_values,
            "efficiency_values": efficiency_values,
            "operating_points": intersections,
            "data_points": [[pt[0], pt[1]] for pt in scaled_pressure],
        })

    return {
        "flow_range": flow_range,
        "system_curve": system_curve,
        "fan_curves": fan_plot_data,
        "duty_point": {"flow": duty_flow, "pressure": duty_pressure} if duty_flow > 0 else None,
    }


# =============================================================================
# SUBSTITUTED EQUATION FORMATTERS
# =============================================================================


def format_equations(
    fan_candidate: Dict,
    operating_result: Dict,
    k_coefficient: float,
    dp_fixed: float,
    margin: float,
    operating_density: float,
) -> Dict:
    """Generate substituted equation strings for the derivation panel.

    ---Parameters---
    fan_candidate:
        The fan candidate dict.
    operating_result:
        The computed operating point result dict.
    k_coefficient:
        System quadratic resistance coefficient.
    dp_fixed:
        System fixed pressure loss in Pa.
    margin:
        System installation margin in Pa.
    operating_density:
        Operating air density in kg/m3.

    ---Returns---
    equations:
        Dict with equation name -> substituted string.
    """
    ref_density = fan_candidate.get("reference_density_kg_m3", STANDARD_AIR_DENSITY)
    ref_rpm = fan_candidate.get("reference_speed_rpm", 0)
    op_rpm = fan_candidate.get("operating_speed_rpm", ref_rpm)
    op_flow = operating_result.get("operating_flow", 0)
    op_pressure = operating_result.get("operating_pressure", 0)

    eqs = {}

    # System curve
    if margin > 0:
        eqs["system_curve"] = (
            f"\\Delta P_{{system}} = {dp_fixed:.1f} + {k_coefficient:.1f} \\times {op_flow:.4f}^2 + {margin:.1f} = {op_pressure:.1f} \\text{{ Pa}}"
        )
    else:
        eqs["system_curve"] = (
            f"\\Delta P_{{system}} = {dp_fixed:.1f} + {k_coefficient:.1f} \\times {op_flow:.4f}^2 = {op_pressure:.1f} \\text{{ Pa}}"
        )

    # Density scaling
    if abs(operating_density - ref_density) / ref_density > 0.001:
        eqs["density_scaling"] = (
            f"\\Delta P_{{op}} = \\Delta P_{{ref}} \\times \\frac{{{operating_density:.3f}}}{{{ref_density:.3f}}} = \\Delta P_{{ref}} \\times {operating_density/ref_density:.4f}"
        )

    # Speed scaling
    if ref_rpm > 0 and abs(op_rpm - ref_rpm) > 0.1:
        ratio = op_rpm / ref_rpm
        eqs["speed_flow"] = f"Q_2 = Q_1 \\times \\frac{{{op_rpm:.0f}}}{{{ref_rpm:.0f}}} = Q_1 \\times {ratio:.4f}"
        eqs["speed_pressure"] = f"\\Delta P_2 = \\Delta P_1 \\times \\left(\\frac{{{op_rpm:.0f}}}{{{ref_rpm:.0f}}}\\right)^2 = \\Delta P_1 \\times {ratio**2:.4f}"
        eqs["speed_power"] = f"P_2 = P_1 \\times \\left(\\frac{{{op_rpm:.0f}}}{{{ref_rpm:.0f}}}\\right)^3 = P_1 \\times {ratio**3:.4f}"

    # Efficiency
    shaft_power = operating_result.get("shaft_power_w")
    if shaft_power and shaft_power > 0 and op_flow > 0 and op_pressure > 0:
        eta = operating_result.get("operating_efficiency", 0)
        eqs["efficiency"] = (
            f"\\eta = \\frac{{Q \\times \\Delta P}}{{P_{{shaft}}}} = \\frac{{{op_flow:.4f} \\times {op_pressure:.1f}}}{{{shaft_power:.1f}}} = {eta:.3f}"
        )

    return eqs


# =============================================================================
# FAN LIBRARY — SYNTHETIC ARCHETYPES
# =============================================================================


def _generate_axial_archetype(
    name: str,
    candidate_id: str,
    max_flow_m3s: float,
    max_pressure_pa: float,
    max_power_w: float,
    ref_rpm: float,
    description: str,
    n_points: int = 15,
) -> Dict:
    """Generate a synthetic axial fan archetype with realistic curve shapes."""
    pressure_curve = []
    power_curve = []
    for i in range(n_points + 1):
        q_frac = i / n_points
        q = q_frac * max_flow_m3s

        # Axial: pressure declines roughly parabolically
        p = max_pressure_pa * (1.0 - q_frac**1.8)
        p = max(p, 0.0)
        pressure_curve.append([q, p])

        # Power: rises to peak around 60-80% flow, then decreases slightly
        pwr = max_power_w * (0.3 + 1.4 * q_frac - 0.7 * q_frac**2)
        pwr = max(pwr, max_power_w * 0.2)
        power_curve.append([q, pwr])

    # Efficiency derived
    efficiency_curve = []
    for i in range(len(pressure_curve)):
        q = pressure_curve[i][0]
        p = pressure_curve[i][1]
        pwr = power_curve[i][1]
        if q > 0 and pwr > 0:
            eta = min((q * p) / pwr, 1.0)
        else:
            eta = 0.0
        efficiency_curve.append([q, eta])

    return {
        "candidate_id": candidate_id,
        "title": name,
        "source_type": "library-archetype",
        "archetype_note": "Synthetic archetype for educational use. Not a real product.",
        "reference_speed_rpm": ref_rpm,
        "operating_speed_rpm": ref_rpm,
        "reference_density_kg_m3": STANDARD_AIR_DENSITY,
        "pressure_basis": "static",
        "pressure_curve": pressure_curve,
        "power_curve": power_curve,
        "efficiency_curve": efficiency_curve,
        "fei": None,
        "motor_efficiency": None,
        "vfd_efficiency": None,
        "preferred_operating_region": None,
        "source_note": None,
        "description": description,
    }


def _generate_bc_centrifugal_archetype() -> Dict:
    """Generate a backward-curved centrifugal fan archetype.

    Characteristics: non-overloading power curve, high peak efficiency.
    """
    max_flow = 2.5  # m3/s
    max_pressure = 2500.0  # Pa
    max_power = 3500.0  # W
    ref_rpm = 1200.0
    n = 15

    pressure_curve = []
    power_curve = []
    for i in range(n + 1):
        q_frac = i / n
        q = q_frac * max_flow

        # BC centrifugal: gradual decline, slightly concave
        p = max_pressure * (1.0 - 0.3 * q_frac - 0.7 * q_frac**2.2)
        p = max(p, 0.0)
        pressure_curve.append([q, p])

        # Non-overloading: power peaks around 70% flow then drops
        pwr = max_power * (0.4 + 1.8 * q_frac - 1.5 * q_frac**2 + 0.3 * q_frac**3)
        pwr = max(pwr, max_power * 0.3)
        power_curve.append([q, pwr])

    efficiency_curve = []
    for i in range(len(pressure_curve)):
        q = pressure_curve[i][0]
        p = pressure_curve[i][1]
        pwr = power_curve[i][1]
        if q > 0 and pwr > 0:
            eta = min((q * p) / pwr, 1.0)
        else:
            eta = 0.0
        efficiency_curve.append([q, eta])

    return {
        "candidate_id": "bc-centrifugal",
        "title": "Backward-Curved Centrifugal (Educational)",
        "source_type": "library-archetype",
        "archetype_note": "Synthetic archetype for educational use. Not a real product.",
        "reference_speed_rpm": ref_rpm,
        "operating_speed_rpm": ref_rpm,
        "reference_density_kg_m3": STANDARD_AIR_DENSITY,
        "pressure_basis": "static",
        "pressure_curve": pressure_curve,
        "power_curve": power_curve,
        "efficiency_curve": efficiency_curve,
        "fei": None,
        "motor_efficiency": None,
        "vfd_efficiency": None,
        "preferred_operating_region": None,
        "source_note": None,
        "description": "Backward-curved centrifugal fans have a non-overloading power characteristic and high peak efficiency (70-85%). They are widely used in HVAC and industrial applications where efficiency and stability matter.",
    }


def _generate_fc_centrifugal_archetype() -> Dict:
    """Generate a forward-curved centrifugal fan archetype.

    Characteristics: hump/dip in pressure curve (dual intersection potential),
    overloading power curve, moderate efficiency.
    """
    max_flow = 3.0  # m3/s
    max_power = 2500.0  # W
    ref_rpm = 800.0
    n = 20

    pressure_curve = []
    power_curve = []
    for i in range(n + 1):
        q_frac = i / n
        q = q_frac * max_flow

        # FC centrifugal: characteristic hump at low flow, then steep decline
        # This creates a non-monotonic pressure curve that can produce dual intersections
        p = 800.0 * (1.0 + 0.3 * q_frac - 0.5 * q_frac**0.8 - 0.8 * q_frac**2.5)
        p = max(p, 0.0)
        pressure_curve.append([q, p])

        # Overloading: power increases continuously with flow
        pwr = max_power * (0.2 + 0.9 * q_frac + 0.1 * q_frac**2)
        pwr = max(pwr, max_power * 0.15)
        power_curve.append([q, pwr])

    efficiency_curve = []
    for i in range(len(pressure_curve)):
        q = pressure_curve[i][0]
        p = pressure_curve[i][1]
        pwr = power_curve[i][1]
        if q > 0 and pwr > 0:
            eta = min((q * p) / pwr, 1.0)
        else:
            eta = 0.0
        efficiency_curve.append([q, eta])

    return {
        "candidate_id": "fc-centrifugal",
        "title": "Forward-Curved Centrifugal (Educational)",
        "source_type": "library-archetype",
        "archetype_note": "Synthetic archetype for educational use. Not a real product.",
        "reference_speed_rpm": ref_rpm,
        "operating_speed_rpm": ref_rpm,
        "reference_density_kg_m3": STANDARD_AIR_DENSITY,
        "pressure_basis": "static",
        "pressure_curve": pressure_curve,
        "power_curve": power_curve,
        "efficiency_curve": efficiency_curve,
        "fei": None,
        "motor_efficiency": None,
        "vfd_efficiency": None,
        "preferred_operating_region": None,
        "source_note": None,
        "description": "Forward-curved centrifugal fans deliver high flow at low speed and low cost, but have an overloading power characteristic and a pressure-curve hump that can create unstable operating regions. Common in residential HVAC and low-pressure applications.",
    }


def _generate_mixed_flow_archetype() -> Dict:
    """Generate a mixed-flow fan archetype."""
    max_flow = 1.8  # m3/s
    max_pressure = 1200.0  # Pa
    max_power = 1500.0  # W
    ref_rpm = 1800.0
    n = 15

    pressure_curve = []
    power_curve = []
    for i in range(n + 1):
        q_frac = i / n
        q = q_frac * max_flow

        # Mixed-flow: between axial and centrifugal shape
        p = max_pressure * (1.0 - 0.15 * q_frac - 0.85 * q_frac**2.0)
        p = max(p, 0.0)
        pressure_curve.append([q, p])

        # Mildly overloading power
        pwr = max_power * (0.35 + 1.2 * q_frac - 0.55 * q_frac**2)
        pwr = max(pwr, max_power * 0.25)
        power_curve.append([q, pwr])

    efficiency_curve = []
    for i in range(len(pressure_curve)):
        q = pressure_curve[i][0]
        p = pressure_curve[i][1]
        pwr = power_curve[i][1]
        if q > 0 and pwr > 0:
            eta = min((q * p) / pwr, 1.0)
        else:
            eta = 0.0
        efficiency_curve.append([q, eta])

    return {
        "candidate_id": "mixed-flow",
        "title": "Mixed-Flow (Educational)",
        "source_type": "library-archetype",
        "archetype_note": "Synthetic archetype for educational use. Not a real product.",
        "reference_speed_rpm": ref_rpm,
        "operating_speed_rpm": ref_rpm,
        "reference_density_kg_m3": STANDARD_AIR_DENSITY,
        "pressure_basis": "static",
        "pressure_curve": pressure_curve,
        "power_curve": power_curve,
        "efficiency_curve": efficiency_curve,
        "fei": None,
        "motor_efficiency": None,
        "vfd_efficiency": None,
        "preferred_operating_region": None,
        "source_note": None,
        "description": "Mixed-flow fans combine axial and centrifugal characteristics, offering moderate pressure capability with compact size. Used in industrial ventilation and duct boosting applications.",
    }


# Build the library
FAN_LIBRARY: Dict[str, Dict] = {
    "small-axial-40mm": _generate_axial_archetype(
        name="Small Axial 40mm (Educational)",
        candidate_id="small-axial-40mm",
        max_flow_m3s=0.012,  # ~25 CFM
        max_pressure_pa=60.0,
        max_power_w=1.5,
        ref_rpm=5000.0,
        description="Typical 40mm electronics cooling fan. Low pressure, low flow. Common in small enclosures, embedded systems, and 3D printers.",
    ),
    "medium-axial-120mm": _generate_axial_archetype(
        name="Medium Axial 120mm (Educational)",
        candidate_id="medium-axial-120mm",
        max_flow_m3s=0.085,  # ~180 CFM
        max_pressure_pa=150.0,
        max_power_w=12.0,
        ref_rpm=2500.0,
        description="Mid-size axial fan common in PC cooling, electronics enclosures, and light-duty ventilation. Moderate flow and pressure.",
    ),
    "large-axial-500mm": _generate_axial_archetype(
        name="Large Axial 500mm (Educational)",
        candidate_id="large-axial-500mm",
        max_flow_m3s=3.5,  # ~7400 CFM
        max_pressure_pa=400.0,
        max_power_w=800.0,
        ref_rpm=1500.0,
        description="Large axial fan for industrial ventilation and HVAC. High flow, moderate pressure. Suitable for direct-drive wall exhaust or duct-mounted applications.",
    ),
    "bc-centrifugal": _generate_bc_centrifugal_archetype(),
    "fc-centrifugal": _generate_fc_centrifugal_archetype(),
    "mixed-flow": _generate_mixed_flow_archetype(),
}


def get_fan_library() -> Dict:
    """Return the full fan library for the frontend picker.

    ---Returns---
    library:
        Dict mapping archetype_id to fan candidate data.
    """
    return FAN_LIBRARY


def get_fan_archetype(archetype_id: str) -> Optional[Dict]:
    """Return a single fan archetype by ID.

    ---Parameters---
    archetype_id:
        The library key for the archetype.

    ---Returns---
    fan:
        Fan candidate dict, or None if not found.
    """
    fan = FAN_LIBRARY.get(archetype_id)
    if fan:
        # Return a copy so the caller can modify operating_speed_rpm etc.
        import copy
        return copy.deepcopy(fan)
    return None


def get_library_summary() -> List[Dict]:
    """Return a summary list for the library picker UI.

    ---Returns---
    summaries:
        List of dicts with candidate_id, title, description, type info.
    """
    summaries = []
    for key, fan in FAN_LIBRARY.items():
        summaries.append({
            "candidate_id": fan["candidate_id"],
            "title": fan["title"],
            "description": fan.get("description", ""),
            "source_type": "library-archetype",
        })
    return summaries
