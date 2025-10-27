"""
Ballistic planning utilities for two-dimensional projectile motion without drag.

The helpers in this module expose closed-form kinematic relationships so the
browser-based tools can keep educational text and numerical results perfectly
aligned.  All calculations operate in SI units and assume a flat landing plane.
"""

from __future__ import annotations

import math
from typing import Dict, List


def _validate_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def plan_projectile_trajectory(
    initial_speed_mps: float,
    launch_angle_deg: float,
    initial_height_m: float = 0.0,
    gravity_mps2: float = 9.80665,
) -> Dict[str, float | List[Dict[str, float]]]:
    """
    Compute key kinematics for a planar projectile launched from an elevated pad.

    The planner assumes a rigid body launched with a specified speed and angle,
    neglecting aerodynamic drag.  Inputs and outputs are expressed in SI units
    so the tool can run identically in Pyodide and conventional Python.  Invoke
    the helper once per launch angle when sweeping a family of trajectories.

    ---Parameters---
    initial_speed_mps : float
        Launch speed magnitude measured at t = 0 (m/s). Must be greater than zero.
    launch_angle_deg : float
        Launch angle above the horizontal (deg). Restricted to 0° < θ < 90°.
        UI workflows may accept comma-separated angles; invoke this helper once
        per entry when evaluating a sweep.
    initial_height_m : float
        Height of the launch point relative to the landing plane (m). Defaults to 0.
    gravity_mps2 : float
        Gravitational acceleration magnitude acting downward (m/s²). Defaults to 9.80665.

    ---Returns---
    vx0_mps : float
        Horizontal velocity component at launch (m/s).
    vy0_mps : float
        Vertical velocity component at launch (m/s).
    time_to_peak_s : float
        Time required to reach the apex where vertical velocity becomes zero (s).
    peak_height_m : float
        Maximum altitude of the projectile relative to the landing plane (m).
    peak_range_m : float
        Horizontal distance travelled when the projectile reaches the apex (m).
    time_of_flight_s : float
        Total flight duration from launch to ground impact (s).
    range_m : float
        Horizontal distance between launch and touchdown points (m).
    impact_vertical_velocity_mps : float
        Vertical velocity component immediately before impact (m/s).
    impact_speed_mps : float
        Magnitude of the velocity vector at impact (m/s).
    impact_angle_deg : float
        Magnitude of the impact flight-path angle measured below the horizontal (deg).

    ---LaTeX---
    v_{x0} = v_0 \\cos(\\theta)
    v_{y0} = v_0 \\sin(\\theta)
    t_{\\text{peak}} = \\frac{v_{y0}}{g}
    y_{\\text{peak}} = y_0 + v_{y0} t_{\\text{peak}} - \\tfrac{1}{2} g t_{\\text{peak}}^2
    x_{\\text{peak}} = v_{x0} t_{\\text{peak}}
    t_{\\text{flight}} = \\frac{v_{y0} + \\sqrt{v_{y0}^2 + 2 g y_0}}{g}
    x_{\\text{range}} = v_{x0} t_{\\text{flight}}
    v_{y,\\text{impact}} = v_{y0} - g t_{\\text{flight}}
    v_{\\text{impact}} = \\sqrt{v_{x0}^2 + v_{y,\\text{impact}}^2}
    \\gamma_{\\text{impact}} = \\tan^{-1}\\left( \\frac{|v_{y,\\text{impact}}|}{v_{x0}} \\right )

    ---Variables---
    v_0: launch speed magnitude (m/s)
    \\theta: launch angle measured in radians
    y_0: launch height above the landing plane (m)
    g: gravitational acceleration magnitude (m/s^2)
    v_{x0}: horizontal velocity component at launch (m/s)
    v_{y0}: vertical velocity component at launch (m/s)
    t_{\\text{peak}}: time required to reach the apex (s)
    y_{\\text{peak}}: peak altitude measured from the landing plane (m)
    x_{\\text{peak}}: horizontal distance travelled at the apex (m)
    t_{\\text{flight}}: time elapsed between launch and impact (s)
    x_{\\text{range}}: horizontal distance travelled at impact (m)
    v_{y,\\text{impact}}: vertical component of velocity at impact (m/s)
    v_{\\text{impact}}: impact speed magnitude (m/s)
    \\gamma_{\\text{impact}}: downward impact flight-path angle (rad)

    ---References---
    R. C. Hibbeler, *Engineering Mechanics: Dynamics*, 14th ed., Pearson, 2016.
    J. L. Meriam and L. G. Kraige, *Engineering Mechanics: Dynamics*, 9th ed., Wiley, 2017.
    """

    try:
        initial_speed_mps = float(initial_speed_mps)
        launch_angle_deg = float(launch_angle_deg)
        initial_height_m = float(initial_height_m)
        gravity_mps2 = float(gravity_mps2)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError("Inputs must be numeric values.") from exc

    _validate_positive(initial_speed_mps, "Initial speed")
    _validate_positive(gravity_mps2, "Gravity")

    if not 0.0 < launch_angle_deg < 90.0:
        raise ValueError("Launch angle must be between 0 and 90 degrees.")

    if initial_height_m < 0.0:
        raise ValueError("Initial height cannot be negative.")

    theta_rad = math.radians(launch_angle_deg)
    vx0 = initial_speed_mps * math.cos(theta_rad)
    vy0 = initial_speed_mps * math.sin(theta_rad)

    time_to_peak = vy0 / gravity_mps2 if vy0 > 0.0 else 0.0
    peak_height = (
        initial_height_m + vy0 * time_to_peak - 0.5 * gravity_mps2 * time_to_peak**2
    )
    peak_range = vx0 * time_to_peak

    discriminant = vy0**2 + 2.0 * gravity_mps2 * initial_height_m
    if discriminant < 0.0:  # pragma: no cover - defensive
        raise ValueError("Inputs produce a complex time of flight.")

    sqrt_discriminant = math.sqrt(discriminant)
    time_of_flight = (vy0 + sqrt_discriminant) / gravity_mps2
    range_horizontal = vx0 * time_of_flight

    impact_vertical_velocity = vy0 - gravity_mps2 * time_of_flight
    impact_speed = math.sqrt(vx0**2 + impact_vertical_velocity**2)
    impact_angle_rad = math.atan2(abs(impact_vertical_velocity), vx0)
    impact_angle_deg = math.degrees(impact_angle_rad)

    samples: List[Dict[str, float]] = []
    sample_count = 60
    for idx in range(sample_count + 1):
        t = time_of_flight * idx / sample_count
        x = vx0 * t
        y = initial_height_m + vy0 * t - 0.5 * gravity_mps2 * t**2
        samples.append(
            {
                "t": t,
                "x": x,
                "y": max(y, 0.0),
            }
        )

    results: Dict[str, float | List[Dict[str, float]]] = {
        "vx0_mps": vx0,
        "vy0_mps": vy0,
        "time_to_peak_s": time_to_peak,
        "peak_height_m": peak_height,
        "peak_range_m": peak_range,
        "time_of_flight_s": time_of_flight,
        "range_m": range_horizontal,
        "impact_vertical_velocity_mps": impact_vertical_velocity,
        "impact_speed_mps": impact_speed,
        "impact_angle_deg": impact_angle_deg,
        "trajectory_points": samples,
        "subst_vx0_mps": (
            f"v_{{x0}} = {initial_speed_mps:.3f} \\cos({theta_rad:.5f}) = {vx0:.3f}"
        ),
        "subst_vy0_mps": (
            f"v_{{y0}} = {initial_speed_mps:.3f} \\sin({theta_rad:.5f}) = {vy0:.3f}"
        ),
        "subst_time_to_peak_s": (
            f"t_{{\\text{{peak}}}} = {vy0:.3f} / {gravity_mps2:.3f} = {time_to_peak:.3f}"
        ),
        "subst_peak_height_m": (
            "y_{\\text{peak}} = "
            f"{initial_height_m:.3f} + {vy0:.3f} \\times {time_to_peak:.3f}"
            f" - 0.5 \\times {gravity_mps2:.3f} \\times {time_to_peak:.3f}^2"
            f" = {peak_height:.3f}"
        ),
        "subst_peak_range_m": (
            f"x_{{\\text{{peak}}}} = {vx0:.3f} \\times {time_to_peak:.3f} = {peak_range:.3f}"
        ),
        "subst_time_of_flight_s": (
            "t_{\\text{flight}} = ("
            f"{vy0:.3f} + \\sqrt{{{vy0:.3f}^2 + 2 \\times {gravity_mps2:.3f} "
            f"\\times {initial_height_m:.3f}}}"
            f") / {gravity_mps2:.3f} = {time_of_flight:.3f}"
        ),
        "subst_range_m": (
            f"x_{{\\text{{range}}}} = {vx0:.3f} \\times {time_of_flight:.3f} = {range_horizontal:.3f}"
        ),
        "subst_impact_vertical_velocity_mps": (
            "v_{y,\\text{impact}} = "
            f"{vy0:.3f} - {gravity_mps2:.3f} \\times {time_of_flight:.3f}"
            f" = {impact_vertical_velocity:.3f}"
        ),
        "subst_impact_speed_mps": (
            "v_{\\text{impact}} = \\sqrt{"
            f"{vx0:.3f}^2 + {impact_vertical_velocity:.3f}^2"
            f"}} = {impact_speed:.3f}"
        ),
        "subst_impact_angle_deg": (
            "\\gamma_{\\text{impact}} = \\tan^{-1}"
            f"\\left(\\frac{{{abs(impact_vertical_velocity):.3f}}}{{{vx0:.3f}}}\\right)"
            f" = {impact_angle_deg:.3f}^\\circ"
        ),
    }

    return results
