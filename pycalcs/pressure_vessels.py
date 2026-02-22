"""Thin-wall pressure vessel sizing and stress checks."""

from __future__ import annotations

import math


def analyze_pressure_vessel(
    geometry: str,
    pressure_mpa: float,
    diameter_mm: float,
    thickness_mm: float,
    allowable_stress_mpa: float,
    safety_factor: float = 2.0,
    joint_efficiency: float = 1.0,
    corrosion_allowance_mm: float = 0.0,
) -> dict[str, float | str | list[str]]:
    """
    Compute thin-wall stresses and required thickness for pressure vessels.

    This calculation uses classic thin-wall membrane theory for cylindrical
    and spherical shells under internal pressure. It is intended for quick
    sizing and educational checks, not code-compliant design.

    ---Parameters---
    geometry : str
        Vessel shape selection: "cylinder" or "sphere".
        Cylinders assume closed ends for longitudinal stress.
    pressure_mpa : float
        Internal gauge pressure in MPa. Must be greater than zero.
    diameter_mm : float
        Mean diameter in millimeters (mm). Must be greater than zero.
    thickness_mm : float
        Net wall thickness in millimeters (mm). Must be greater than zero.
        Corrosion allowance is added separately to required thickness.
    allowable_stress_mpa : float
        Allowable membrane stress in MPa for sizing checks.
    safety_factor : float
        Design safety factor applied to allowable stress. Must be greater than zero.
    joint_efficiency : float
        Weld/joint efficiency factor E (0 < E <= 1.0).
    corrosion_allowance_mm : float
        Additional thickness in millimeters (mm) added to required thickness.
        Must be zero or greater.

    ---Returns---
    required_thickness_mm : float
        Governing required thickness in mm including corrosion allowance.
    required_thickness_hoop_mm : float
        Hoop-based required thickness in mm including corrosion allowance.
    required_thickness_longitudinal_mm : float
        Longitudinal-based required thickness in mm including corrosion allowance.
    hoop_stress_mpa : float
        Hoop (circumferential) membrane stress in MPa.
    longitudinal_stress_mpa : float
        Longitudinal membrane stress in MPa.
    von_mises_stress_mpa : float
        Von Mises equivalent stress in MPa from membrane stresses.
    effective_allowable_mpa : float
        Allowable stress after joint efficiency and safety factor in MPa.
    utilization : float
        Ratio of von Mises stress to effective allowable (dimensionless).
    thin_wall_ratio : float
        Thickness-to-radius ratio t/r (dimensionless).
    status : str
        Thin-wall validity flag: "acceptable", "marginal", or "unacceptable".
    status_message : str
        Human-readable thin-wall check summary.
    recommendations : list[str]
        Actionable notes based on validity and utilization checks.
    subst_required_thickness_mm : str
        Substituted equation string for required thickness.
    subst_hoop_stress_mpa : str
        Substituted equation string for hoop/membrane stress.
    subst_longitudinal_stress_mpa : str
        Substituted equation string for longitudinal stress.
    subst_von_mises_stress_mpa : str
        Substituted equation string for von Mises stress.
    subst_utilization : str
        Substituted equation string for utilization.

    ---LaTeX---
    \\sigma_h = \\frac{P r}{t}
    \\sigma_l = \\frac{P r}{2 t}
    \\sigma_s = \\frac{P r}{2 t}
    \\sigma_{vm} = \\sqrt{\\sigma_h^2 + \\sigma_l^2 - \\sigma_h \\sigma_l}
    \\sigma_{allow,eff} = \\frac{\\sigma_{allow} E}{SF}
    t_{req,cyl} = \\frac{P r}{\\sigma_{allow,eff}} + c
    t_{req,sph} = \\frac{P r}{2 \\sigma_{allow,eff}} + c

    ---References---
    Budynas, R. G., & Nisbett, J. K. (2015). Shigley's Mechanical Engineering Design (10th ed.).
    Young, W. C., & Budynas, R. G. (2002). Roark's Formulas for Stress and Strain (7th ed.).
    """
    geometry_key = geometry.strip().lower()
    if geometry_key not in {"cylinder", "sphere"}:
        raise ValueError("Geometry must be 'cylinder' or 'sphere'.")
    if not math.isfinite(pressure_mpa):
        raise ValueError("Pressure must be a finite number.")
    if not math.isfinite(diameter_mm):
        raise ValueError("Diameter must be a finite number.")
    if not math.isfinite(thickness_mm):
        raise ValueError("Thickness must be a finite number.")
    if not math.isfinite(allowable_stress_mpa):
        raise ValueError("Allowable stress must be a finite number.")
    if not math.isfinite(safety_factor):
        raise ValueError("Safety factor must be a finite number.")
    if not math.isfinite(joint_efficiency):
        raise ValueError("Joint efficiency must be a finite number.")
    if not math.isfinite(corrosion_allowance_mm):
        raise ValueError("Corrosion allowance must be a finite number.")
    if pressure_mpa <= 0:
        raise ValueError("Pressure must be greater than zero.")
    if diameter_mm <= 0:
        raise ValueError("Diameter must be greater than zero.")
    if thickness_mm <= 0:
        raise ValueError("Thickness must be greater than zero.")
    if allowable_stress_mpa <= 0:
        raise ValueError("Allowable stress must be greater than zero.")
    if safety_factor <= 0:
        raise ValueError("Safety factor must be greater than zero.")
    if not (0 < joint_efficiency <= 1.0):
        raise ValueError("Joint efficiency must be in the range (0, 1].")
    if corrosion_allowance_mm < 0:
        raise ValueError("Corrosion allowance must be zero or greater.")

    radius_mm = diameter_mm / 2.0
    effective_allowable_mpa = (allowable_stress_mpa * joint_efficiency) / safety_factor
    if effective_allowable_mpa <= 0:
        raise ValueError("Effective allowable stress must be greater than zero.")

    if geometry_key == "sphere":
        hoop_stress_mpa = pressure_mpa * radius_mm / (2.0 * thickness_mm)
        longitudinal_stress_mpa = hoop_stress_mpa
        required_thickness_hoop_mm = (
            pressure_mpa * radius_mm / (2.0 * effective_allowable_mpa)
            + corrosion_allowance_mm
        )
        required_thickness_longitudinal_mm = required_thickness_hoop_mm
        thickness_equation = "t = \\frac{P r}{2 \\sigma_{allow,eff}} + c"
        hoop_equation = "\\sigma_s = \\frac{P r}{2 t}"
    else:
        hoop_stress_mpa = pressure_mpa * radius_mm / thickness_mm
        longitudinal_stress_mpa = pressure_mpa * radius_mm / (2.0 * thickness_mm)
        required_thickness_hoop_mm = (
            pressure_mpa * radius_mm / effective_allowable_mpa
            + corrosion_allowance_mm
        )
        required_thickness_longitudinal_mm = (
            pressure_mpa * radius_mm / (2.0 * effective_allowable_mpa)
            + corrosion_allowance_mm
        )
        thickness_equation = "t = \\frac{P r}{\\sigma_{allow,eff}} + c"
        hoop_equation = "\\sigma_h = \\frac{P r}{t}"

    required_thickness_mm = max(required_thickness_hoop_mm, required_thickness_longitudinal_mm)

    von_mises_stress_mpa = math.sqrt(
        hoop_stress_mpa ** 2
        + longitudinal_stress_mpa ** 2
        - hoop_stress_mpa * longitudinal_stress_mpa
    )
    utilization = von_mises_stress_mpa / effective_allowable_mpa
    thin_wall_ratio = thickness_mm / radius_mm

    recommendations: list[str] = []
    if thin_wall_ratio <= 0.1:
        status = "acceptable"
        status_message = (
            f"Thin-wall check OK: t/r = {thin_wall_ratio:.3f} <= 0.100."
        )
    elif thin_wall_ratio <= 0.2:
        status = "marginal"
        status_message = (
            f"Borderline thin-wall: t/r = {thin_wall_ratio:.3f} > 0.100."
        )
        recommendations.append(
            "Consider thick-wall (Lame) equations for improved accuracy."
        )
    else:
        status = "unacceptable"
        status_message = (
            f"Thin-wall assumption likely invalid: t/r = {thin_wall_ratio:.3f}."
        )
        recommendations.append(
            "Switch to thick-wall (Lame) formulas or a code-based tool."
        )

    if utilization > 1.0:
        recommendations.append(
            "Utilization exceeds 1.0. Increase thickness or allowable stress."
        )
    if required_thickness_mm > thickness_mm:
        recommendations.append(
            "Required thickness exceeds current thickness. Increase wall thickness."
        )

    fmt = lambda value: f"{value:.3f}"

    subst_hoop_stress_mpa = (
        f"{hoop_equation} = "
        f"\\frac{{{fmt(pressure_mpa)} \\times {fmt(radius_mm)}}}"
        f"{{{fmt(2.0 * thickness_mm) if geometry_key == 'sphere' else fmt(thickness_mm)}}}"
        f" = {fmt(hoop_stress_mpa)}\\,\\text{{MPa}}"
    )

    if geometry_key == "sphere":
        subst_longitudinal_stress_mpa = subst_hoop_stress_mpa
    else:
        subst_longitudinal_stress_mpa = (
            "\\sigma_l = \\frac{P r}{2 t} = "
            f"\\frac{{{fmt(pressure_mpa)} \\times {fmt(radius_mm)}}}"
            f"{{{fmt(2.0 * thickness_mm)}}}"
            f" = {fmt(longitudinal_stress_mpa)}\\,\\text{{MPa}}"
        )

    subst_von_mises_stress_mpa = (
        "\\sigma_{vm} = \\sqrt{\\sigma_h^2 + \\sigma_l^2 - \\sigma_h \\sigma_l} = "
        f"{fmt(von_mises_stress_mpa)}\\,\\text{{MPa}}"
    )

    subst_required_thickness_mm = (
        f"{thickness_equation} = "
        f"\\frac{{{fmt(pressure_mpa)} \\times {fmt(radius_mm)}}}"
        f"{{{fmt(effective_allowable_mpa)}"
        f"{'' if geometry_key == 'cylinder' else ' \\times 2'}}}"
        f" + {fmt(corrosion_allowance_mm)}"
        f" = {fmt(required_thickness_mm)}\\,\\text{{mm}}"
    )

    subst_utilization = (
        "U = \\frac{\\sigma_{vm}}{\\sigma_{allow,eff}} = "
        f"\\frac{{{fmt(von_mises_stress_mpa)}}}{{{fmt(effective_allowable_mpa)}}}"
        f" = {fmt(utilization)}"
    )

    return {
        "required_thickness_mm": float(required_thickness_mm),
        "required_thickness_hoop_mm": float(required_thickness_hoop_mm),
        "required_thickness_longitudinal_mm": float(required_thickness_longitudinal_mm),
        "hoop_stress_mpa": float(hoop_stress_mpa),
        "longitudinal_stress_mpa": float(longitudinal_stress_mpa),
        "von_mises_stress_mpa": float(von_mises_stress_mpa),
        "effective_allowable_mpa": float(effective_allowable_mpa),
        "utilization": float(utilization),
        "thin_wall_ratio": float(thin_wall_ratio),
        "status": status,
        "status_message": status_message,
        "recommendations": recommendations,
        "subst_required_thickness_mm": subst_required_thickness_mm,
        "subst_hoop_stress_mpa": subst_hoop_stress_mpa,
        "subst_longitudinal_stress_mpa": subst_longitudinal_stress_mpa,
        "subst_von_mises_stress_mpa": subst_von_mises_stress_mpa,
        "subst_utilization": subst_utilization,
    }
