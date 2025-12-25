"""
Kinematic calculations for translating roller cam profiles.

This module provides cam motion law primitives and a profile analyzer that
returns follower kinematics plus pitch-curve and cam-surface coordinates.
"""

from __future__ import annotations

import math
from typing import Any

TWO_PI = 2.0 * math.pi
EPS = 1e-9


def _cycloidal(u: float) -> tuple[float, float, float, float]:
    """Return normalized cycloidal displacement and its derivatives."""
    angle = TWO_PI * u
    s = u - math.sin(angle) / TWO_PI
    v = 1.0 - math.cos(angle)
    a = TWO_PI * math.sin(angle)
    j = (TWO_PI**2) * math.cos(angle)
    return s, v, a, j


def _simple_harmonic(u: float) -> tuple[float, float, float, float]:
    """Return normalized SHM displacement and its derivatives."""
    angle = math.pi * u
    s = 0.5 * (1.0 - math.cos(angle))
    v = 0.5 * math.pi * math.sin(angle)
    a = 0.5 * math.pi**2 * math.cos(angle)
    j = -0.5 * math.pi**3 * math.sin(angle)
    return s, v, a, j


def _poly_3_4_5(u: float) -> tuple[float, float, float, float]:
    """Return normalized 3-4-5 polynomial displacement and derivatives."""
    s = 10.0 * u**3 - 15.0 * u**4 + 6.0 * u**5
    v = 30.0 * u**2 - 60.0 * u**3 + 30.0 * u**4
    a = 60.0 * u - 180.0 * u**2 + 120.0 * u**3
    j = 60.0 - 360.0 * u + 360.0 * u**2
    return s, v, a, j


def _poly_4_5_6_7(u: float) -> tuple[float, float, float, float]:
    """Return normalized 4-5-6-7 polynomial displacement and derivatives."""
    s = 35.0 * u**4 - 84.0 * u**5 + 70.0 * u**6 - 20.0 * u**7
    v = 140.0 * u**3 - 420.0 * u**4 + 420.0 * u**5 - 140.0 * u**6
    a = 420.0 * u**2 - 1680.0 * u**3 + 2100.0 * u**4 - 840.0 * u**5
    j = 840.0 * u - 5040.0 * u**2 + 8400.0 * u**3 - 4200.0 * u**4
    return s, v, a, j


_MOTION_LAWS: dict[str, dict[str, Any]] = {
    "cycloidal": {
        "name": "Cycloidal",
        "description": "Zero velocity and acceleration at segment boundaries with smooth jerk.",
        "continuous_jerk": True,
        "function": _cycloidal,
    },
    "simple_harmonic": {
        "name": "Simple Harmonic (SHM)",
        "description": "Smooth displacement and velocity; acceleration is non-zero at the ends.",
        "continuous_jerk": False,
        "function": _simple_harmonic,
    },
    "poly_3_4_5": {
        "name": "Polynomial 3-4-5",
        "description": "Zero velocity and acceleration at the ends; finite jerk steps.",
        "continuous_jerk": False,
        "function": _poly_3_4_5,
    },
    "poly_4_5_6_7": {
        "name": "Polynomial 4-5-6-7",
        "description": "Zero velocity, acceleration, and jerk at the ends.",
        "continuous_jerk": True,
        "function": _poly_4_5_6_7,
    },
}


def _normalized_motion(law_key: str, u: float) -> tuple[float, float, float, float]:
    """Return normalized kinematics for the selected motion law."""
    law = _MOTION_LAWS.get(law_key)
    if law is None:
        valid = ", ".join(sorted(_MOTION_LAWS.keys()))
        raise ValueError(f"Unsupported motion_law '{law_key}'. Available: {valid}.")
    u_clamped = max(0.0, min(1.0, u))
    return law["function"](u_clamped)


def _validate_points_per_degree(points_per_degree: float) -> int:
    if points_per_degree <= 0:
        raise ValueError("points_per_degree must be a positive integer.")
    points_int = int(points_per_degree)
    if not math.isclose(points_per_degree, points_int, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError("points_per_degree must be an integer value.")
    return points_int


def analyze_cam_profile(
    segments: list[dict[str, Any]],
    base_circle_radius: float,
    roller_radius: float,
    angular_velocity_rpm: float,
    points_per_degree: int = 1,
) -> dict[str, Any]:
    """
    Analyze a translating roller follower cam profile from motion segments.

    The function builds the displacement/velocity/acceleration/jerk profiles
    over a full 360-degree cycle, then generates the pitch curve and cam
    surface coordinates for an in-line translating roller follower.

    ---Parameters---
    segments : list[dict]
        Ordered motion segments covering a full revolution. Each segment dict
        requires: type ('rise', 'fall', or 'dwell'), duration_deg (deg), and
        lift_mm (mm) for rise/fall segments. Rise/fall segments also require
        motion_law (one of the catalog keys).
    base_circle_radius : float
        Base circle radius of the cam (mm).
    roller_radius : float
        Roller follower radius (mm).
    angular_velocity_rpm : float
        Cam speed (revolutions per minute).
    points_per_degree : int
        Resolution of the analysis (points per degree of cam rotation).

    ---Returns---
    cam_angle_deg : list
        Cam rotation angles spanning 0 to 360 degrees (deg).
    displacement : list
        Follower displacement over the cycle (mm).
    velocity : list
        Follower velocity over the cycle (mm/s).
    acceleration : list
        Follower acceleration over the cycle (mm/s^2).
    jerk : list
        Follower jerk over the cycle (mm/s^3).
    pitch_curve_x : list
        Pitch curve X-coordinates (mm).
    pitch_curve_y : list
        Pitch curve Y-coordinates (mm).
    cam_profile_x : list
        Cam surface X-coordinates (mm).
    cam_profile_y : list
        Cam surface Y-coordinates (mm).
    pitch_radius : list
        Pitch curve radius at each angle (mm).
    cam_radius : list
        Cam surface radius at each angle (mm).
    max_displacement : float
        Maximum displacement (mm).
    max_velocity : float
        Maximum absolute velocity (mm/s).
    max_acceleration : float
        Maximum absolute acceleration (mm/s^2).
    max_jerk : float
        Maximum absolute jerk (mm/s^3).
    min_pitch_radius : float
        Minimum pitch radius (mm).
    max_pitch_radius : float
        Maximum pitch radius (mm).
    min_cam_radius : float
        Minimum cam surface radius (mm).
    max_cam_radius : float
        Maximum cam surface radius (mm).
    omega_rad_s : float
        Angular speed (rad/s).
    cycle_time : float
        Time for one revolution (s).
    total_duration_deg : float
        Total duration of all segments (deg).

    ---LaTeX---
    Equation_1 = \\omega = \\frac{2\\pi \\, \\text{RPM}}{60}
    Legend_1 = \\omega: angular speed (rad/s); \\text{RPM}: rotational speed (rev/min)
    Equation_2 = u = \\frac{\\theta}{\\beta}
    Legend_2 = u: normalized cam angle; \\theta: segment angle (rad); \\beta: segment duration (rad)
    Equation_3 = s = L \\left( u - \\frac{1}{2\\pi} \\sin(2\\pi u) \\right)
    Legend_3 = s: displacement (mm); L: segment lift (mm); u: normalized angle
    Equation_4 = v = \\frac{L}{\\beta} \\left( 1 - \\cos(2\\pi u) \\right)
    Legend_4 = v: ds/d\\theta (mm/rad); L: segment lift (mm); \\beta: segment duration (rad)
    Equation_5 = s = L (10 u^3 - 15 u^4 + 6 u^5)
    Legend_5 = s: displacement (mm); L: segment lift (mm); u: normalized angle
    Equation_6 = s = L (35 u^4 - 84 u^5 + 70 u^6 - 20 u^7)
    Legend_6 = s: displacement (mm); L: segment lift (mm); u: normalized angle
    Equation_7 = x_p = r_p \\cos\\theta, \\; y_p = r_p \\sin\\theta
    Legend_7 = x_p,y_p: pitch curve (mm); r_p: pitch radius (mm); \\theta: cam angle (rad)
    Equation_8 = r_p = R_b + s
    Legend_8 = r_p: pitch radius (mm); R_b: base circle radius (mm); s: displacement (mm)
    Equation_9 = \\vec{n} = \\frac{(-\\dot{y}_p, \\dot{x}_p)}{\\|(-\\dot{y}_p, \\dot{x}_p)\\|}
    Legend_9 = \\vec{n}: inward unit normal; \\dot{x}_p,\\dot{y}_p: derivatives w.r.t. \\theta
    Equation_10 = x_c = x_p + r_r n_x, \\; y_c = y_p + r_r n_y
    Legend_10 = x_c,y_c: cam surface (mm); r_r: roller radius (mm); n_x,n_y: normal components
    Equation_11 = V_{max} = \\max(|v|)\\,\\omega
    Legend_11 = V_{max}: peak velocity (mm/s); v: ds/d\\theta (mm/rad); \\omega: angular speed (rad/s)
    Equation_12 = A_{max} = \\max(|a|)\\,\\omega^2
    Legend_12 = A_{max}: peak acceleration (mm/s^2); a: d^2s/d\\theta^2 (mm/rad^2); \\omega: angular speed (rad/s)
    Equation_13 = J_{max} = \\max(|j|)\\,\\omega^3
    Legend_13 = J_{max}: peak jerk (mm/s^3); j: d^3s/d\\theta^3 (mm/rad^3); \\omega: angular speed (rad/s)
    Equation_14 = R_{c,\\min} = \\min(r_c)
    Legend_14 = R_{c,\\min}: minimum cam radius (mm); r_c: cam surface radius (mm)
    Equation_15 = T = \\frac{60}{\\text{RPM}}
    Legend_15 = T: cycle time (s); \\text{RPM}: rotational speed (rev/min)
    """
    if base_circle_radius <= 0.0:
        raise ValueError("base_circle_radius must be positive.")
    if roller_radius < 0.0:
        raise ValueError("roller_radius cannot be negative.")
    if angular_velocity_rpm <= 0.0:
        raise ValueError("angular_velocity_rpm must be positive.")

    points_per_degree_int = _validate_points_per_degree(points_per_degree)
    if not segments:
        raise ValueError("segments cannot be empty.")

    total_duration = 0.0
    current_displacement = 0.0
    normalized_segments: list[dict[str, Any]] = []

    for seg in segments:
        seg_type = str(seg.get("type", "")).strip().lower()
        duration = seg.get("duration_deg", seg.get("duration"))
        if duration is None:
            raise ValueError("Each segment must define duration_deg (deg).")
        duration = float(duration)
        if duration <= 0.0:
            raise ValueError("Segment duration must be positive.")

        if seg_type not in {"rise", "fall", "dwell"}:
            raise ValueError("Segment type must be 'rise', 'fall', or 'dwell'.")

        lift = 0.0
        motion_law = None
        if seg_type in {"rise", "fall"}:
            lift = float(seg.get("lift_mm", seg.get("lift", 0.0)))
            if lift <= 0.0:
                raise ValueError("Rise/fall segments require lift_mm > 0.")
            motion_law = str(seg.get("motion_law", "")).strip()
            if not motion_law:
                raise ValueError("Rise/fall segments require motion_law.")
            _normalized_motion(motion_law, 0.0)

        if seg_type == "fall" and current_displacement - lift < -EPS:
            raise ValueError("Segment sequence drives displacement below zero.")

        total_duration += duration
        direction = 1.0 if seg_type == "rise" else -1.0 if seg_type == "fall" else 0.0
        current_displacement += direction * lift
        normalized_segments.append(
            {
                "type": seg_type,
                "duration_deg": duration,
                "lift_mm": lift,
                "motion_law": motion_law,
                "direction": direction,
            }
        )

    if not math.isclose(total_duration, 360.0, abs_tol=1e-6):
        raise ValueError(
            f"Total duration of segments must be 360 degrees, but got {total_duration}."
        )
    if abs(current_displacement) > 1e-6:
        raise ValueError("Net lift over 360 degrees must return to zero.")

    omega_rad_s = angular_velocity_rpm * TWO_PI / 60.0
    total_points = int(round(360.0 * points_per_degree_int))
    cam_angle_deg = [i / points_per_degree_int for i in range(total_points + 1)]

    s_profile = [0.0] * (total_points + 1)
    v_profile = [0.0] * (total_points + 1)
    a_profile = [0.0] * (total_points + 1)
    j_profile = [0.0] * (total_points + 1)

    index = 0
    current_displacement = 0.0

    for seg_idx, seg in enumerate(normalized_segments):
        seg_duration = seg["duration_deg"]
        seg_points = int(round(seg_duration * points_per_degree_int))
        if seg_idx == len(normalized_segments) - 1:
            seg_points = total_points - index
        if seg_points <= 0:
            raise ValueError("Segment duration too small for resolution.")

        start_index = index
        end_index = index + seg_points
        beta_rad = math.radians(seg_duration)
        direction = seg["direction"]
        lift = seg["lift_mm"]
        motion_law = seg["motion_law"]

        for i in range(start_index, end_index):
            theta_deg = (i - start_index) / points_per_degree_int
            u = theta_deg / seg_duration

            if seg["type"] == "dwell":
                s_local = 0.0
                ds_dtheta = 0.0
                d2s_dtheta2 = 0.0
                d3s_dtheta3 = 0.0
            else:
                s_norm, v_norm, a_norm, j_norm = _normalized_motion(motion_law, u)
                s_local = direction * lift * s_norm
                ds_dtheta = direction * (lift / beta_rad) * v_norm
                d2s_dtheta2 = direction * (lift / beta_rad**2) * a_norm
                d3s_dtheta3 = direction * (lift / beta_rad**3) * j_norm

            s_profile[i] = current_displacement + s_local
            v_profile[i] = ds_dtheta * omega_rad_s
            a_profile[i] = d2s_dtheta2 * omega_rad_s**2
            j_profile[i] = d3s_dtheta3 * omega_rad_s**3

        current_displacement += direction * lift
        index = end_index

    s_profile[-1] = s_profile[0]
    v_profile[-1] = v_profile[0]
    a_profile[-1] = a_profile[0]
    j_profile[-1] = j_profile[0]

    pitch_radius = [base_circle_radius + s for s in s_profile]
    pitch_curve_x: list[float] = []
    pitch_curve_y: list[float] = []
    cam_profile_x: list[float] = []
    cam_profile_y: list[float] = []
    cam_radius: list[float] = []

    for i, angle_deg in enumerate(cam_angle_deg):
        theta = math.radians(angle_deg)
        r_pitch = pitch_radius[i]
        x_pitch = r_pitch * math.cos(theta)
        y_pitch = r_pitch * math.sin(theta)

        ds_dtheta = v_profile[i] / omega_rad_s
        dx_dtheta = ds_dtheta * math.cos(theta) - r_pitch * math.sin(theta)
        dy_dtheta = ds_dtheta * math.sin(theta) + r_pitch * math.cos(theta)
        tangent_norm = math.hypot(dx_dtheta, dy_dtheta)

        if tangent_norm < EPS:
            n_x = -math.cos(theta)
            n_y = -math.sin(theta)
        else:
            n_x = -dy_dtheta / tangent_norm
            n_y = dx_dtheta / tangent_norm
            if n_x * x_pitch + n_y * y_pitch > 0.0:
                n_x = -n_x
                n_y = -n_y

        x_cam = x_pitch + roller_radius * n_x
        y_cam = y_pitch + roller_radius * n_y

        pitch_curve_x.append(x_pitch)
        pitch_curve_y.append(y_pitch)
        cam_profile_x.append(x_cam)
        cam_profile_y.append(y_cam)
        cam_radius.append(math.hypot(x_cam, y_cam))

    finite_velocity = [abs(v) for v in v_profile if math.isfinite(v)]
    finite_accel = [abs(a) for a in a_profile if math.isfinite(a)]
    finite_jerk = [abs(j) for j in j_profile if math.isfinite(j)]

    max_displacement = max(s_profile)
    max_velocity = max(finite_velocity) if finite_velocity else 0.0
    max_acceleration = max(finite_accel) if finite_accel else 0.0
    max_jerk = max(finite_jerk) if finite_jerk else 0.0

    min_pitch_radius = min(pitch_radius)
    max_pitch_radius = max(pitch_radius)
    min_cam_radius = min(cam_radius)
    max_cam_radius = max(cam_radius)

    cycle_time = 60.0 / angular_velocity_rpm

    results: dict[str, Any] = {
        "cam_angle_deg": cam_angle_deg,
        "displacement": s_profile,
        "velocity": v_profile,
        "acceleration": a_profile,
        "jerk": j_profile,
        "pitch_curve_x": pitch_curve_x,
        "pitch_curve_y": pitch_curve_y,
        "cam_profile_x": cam_profile_x,
        "cam_profile_y": cam_profile_y,
        "pitch_radius": pitch_radius,
        "cam_radius": cam_radius,
        "max_displacement": max_displacement,
        "max_velocity": max_velocity,
        "max_acceleration": max_acceleration,
        "max_jerk": max_jerk,
        "min_pitch_radius": min_pitch_radius,
        "max_pitch_radius": max_pitch_radius,
        "min_cam_radius": min_cam_radius,
        "max_cam_radius": max_cam_radius,
        "omega_rad_s": omega_rad_s,
        "cycle_time": cycle_time,
        "total_duration_deg": total_duration,
    }

    results["subst_max_velocity"] = (
        f"V_{{max}} = \\max(|v|)\\,\\omega = {max_velocity:.3e} \\, \\text{{mm/s}}"
    )
    results["subst_max_acceleration"] = (
        f"A_{{max}} = \\max(|a|)\\,\\omega^2 = {max_acceleration:.3e} \\, \\text{{mm/s^2}}"
    )
    results["subst_max_jerk"] = (
        f"J_{{max}} = \\max(|j|)\\,\\omega^3 = {max_jerk:.3e} \\, \\text{{mm/s^3}}"
    )
    results["subst_min_cam_radius"] = (
        f"R_{{c,\\min}} = {min_cam_radius:.3f} \\, \\text{{mm}}"
    )
    results["subst_omega_rad_s"] = (
        f"\\omega = \\frac{{2\\pi \\times {angular_velocity_rpm:.3f}}}{{60}}"
        f" = {omega_rad_s:.3f} \\, \\text{{rad/s}}"
    )
    results["subst_cycle_time"] = f"T = \\frac{{60}}{{RPM}} = {cycle_time:.3f} \\, \\text{{s}}"

    return results


def get_cam_catalog() -> dict[str, Any]:
    """
    Return metadata for the available cam motion laws.

    ---Returns---
    motion_laws : dict
        Mapping from motion-law key to name, description, and jerk continuity.

    ---LaTeX---
    Catalog = \\{\\text{motion\\_laws}\\}
    """
    motion_laws: dict[str, Any] = {}
    for key, data in _MOTION_LAWS.items():
        motion_laws[key] = {
            "name": data["name"],
            "description": data["description"],
            "continuous_jerk": data["continuous_jerk"],
        }
    return {"motion_laws": motion_laws}


__all__ = [
    "analyze_cam_profile",
    "get_cam_catalog",
]
