"""
Rotor stress calculations for rotating disks and rings.

Implements closed-form stress equations for uniform, isotropic rotors
based on classical rotating-disk theory as presented in Shigley's.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


def _validate_positive(name: str, value: float) -> None:
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0. Got {value}.")


def _linspace(start: float, end: float, points: int) -> List[float]:
    if points < 2:
        raise ValueError("profile_points must be >= 2.")
    if end < start:
        raise ValueError("end must be >= start.")
    if end == start:
        return [start for _ in range(points)]
    step = (end - start) / (points - 1)
    return [start + i * step for i in range(points)]


def calculate_rotor_hoop_stress(
    geometry_type: str,
    inner_radius_mm: float,
    outer_radius_mm: float,
    thickness_mm: float,
    density_kg_m3: float,
    poisson_ratio: float,
    speed_rpm: float,
    yield_strength_mpa: float,
    required_safety_factor: float = 1.5,
    profile_points: int = 81,
) -> Dict[str, Any]:
    r"""
    Estimate stresses in rotating disks and rings using closed-form equations.

    Supports three rotor shapes:
    - `solid_disk`: classical solid rotating disk (inner radius forced to 0)
    - `annular_disk`: uniform annular disk with free inner and outer edges
    - `thin_ring`: thin rotating ring approximation with negligible radial stress

    This is an early-stage sizing tool for burst-margin and speed-limit checks.
    Primary references:
    - Budynas and Nisbett, Shigley's Mechanical Engineering Design
    - Timoshenko and Goodier, Theory of Elasticity (rotating disks/rings)

    ---Parameters---
    geometry_type : str
        Rotor geometry key: `solid_disk`, `annular_disk`, or `thin_ring`.
    inner_radius_mm : float
        Inner radius in mm. Ignored for `solid_disk`.
    outer_radius_mm : float
        Outer radius in mm.
    thickness_mm : float
        Axial thickness in mm (used for mass and inertia estimates).
    density_kg_m3 : float
        Material density in kg/m^3.
    poisson_ratio : float
        Poisson ratio, \(\nu\), typically 0.25 to 0.35 for metals.
    speed_rpm : float
        Rotational speed in rev/min.
    yield_strength_mpa : float
        Material yield strength in MPa.
    required_safety_factor : float
        Minimum acceptable yield safety factor, \(SF_{req}\).
    profile_points : int
        Number of radial points used to build stress distribution outputs.

    ---Returns---
    geometry_label : str
        Human-readable geometry label used in the UI.
    angular_speed_rad_s : float
        Angular speed, \(\omega\), in rad/s.
    tip_speed_m_s : float
        Rim speed at outer radius in m/s.
    mass_kg : float
        Rotor mass estimate from annulus volume and density.
    rotor_inertia_kg_m2 : float
        Polar mass moment of inertia about rotation axis.
    kinetic_energy_j : float
        Stored rotational kinetic energy, \(\tfrac{1}{2}I\omega^2\), in J.
    max_hoop_stress_mpa : float
        Maximum circumferential (hoop) stress in MPa.
    max_radial_stress_mpa : float
        Maximum absolute radial stress in MPa.
    max_von_mises_stress_mpa : float
        Maximum von Mises equivalent stress in MPa.
    critical_radius_mm : float
        Radius where maximum hoop stress occurs, in mm.
    yield_safety_factor : float
        Yield safety factor, \(SF_y = S_y/\sigma_{vm,max}\).
    allowable_speed_rpm : float
        Speed at which \(\sigma_{vm,max} = S_y/SF_{req}\), assuming
        stress scales with \(\omega^2\).
    utilization_percent : float
        Utilization relative to yield, \(100\sigma_{vm,max}/S_y\).
    status : str
        `acceptable`, `marginal`, or `unacceptable`.
    recommendations : list
        Actionable recommendations based on margins and assumptions.
    stress_profile : dict
        Radial stress profile arrays for plotting:
        `radius_mm`, `sigma_r_mpa`, `sigma_theta_mpa`, `sigma_vm_mpa`.
    subst_max_hoop_stress_mpa : str
        Substituted equation string for max hoop stress.
    subst_max_von_mises_stress_mpa : str
        Substituted equation string for max von Mises stress.
    subst_yield_safety_factor : str
        Substituted equation string for yield safety factor.
    subst_allowable_speed_rpm : str
        Substituted equation string for allowable speed.

    ---LaTeX---
    \omega = \frac{2\pi n}{60}
    \sigma_{r,\text{solid}} = \frac{3+\nu}{8}\rho\omega^2\left(r_o^2-r^2\right)
    \sigma_{\theta,\text{solid}} = \frac{3+\nu}{8}\rho\omega^2r_o^2-\frac{1+3\nu}{8}\rho\omega^2r^2
    \sigma_{r,\text{ann}} = \frac{3+\nu}{8}\rho\omega^2\left(r_i^2+r_o^2-\frac{r_i^2r_o^2}{r^2}-r^2\right)
    \sigma_{\theta,\text{ann}} = \frac{3+\nu}{8}\rho\omega^2\left(r_i^2+r_o^2+\frac{r_i^2r_o^2}{r^2}\right)-\frac{1+3\nu}{8}\rho\omega^2r^2
    \sigma_{\theta,ring} = \rho\omega^2 r_m^2
    \sigma_{vm} = \sqrt{\sigma_r^2 - \sigma_r\sigma_{\theta} + \sigma_{\theta}^2}
    SF_y = \frac{S_y}{\sigma_{vm,max}}
    n_{allow} = n \sqrt{\frac{S_y/SF_{req}}{\sigma_{vm,max}}}
    """
    geom = geometry_type.strip().lower()
    if geom not in {"solid_disk", "annular_disk", "thin_ring"}:
        raise ValueError(
            "geometry_type must be one of: solid_disk, annular_disk, thin_ring."
        )

    _validate_positive("outer_radius_mm", outer_radius_mm)
    _validate_positive("thickness_mm", thickness_mm)
    _validate_positive("density_kg_m3", density_kg_m3)
    _validate_positive("speed_rpm", speed_rpm)
    _validate_positive("yield_strength_mpa", yield_strength_mpa)
    _validate_positive("required_safety_factor", required_safety_factor)

    if poisson_ratio < 0.0 or poisson_ratio >= 0.5:
        raise ValueError("poisson_ratio must be in [0.0, 0.5).")

    if geom == "solid_disk":
        ri_m = 0.0
    else:
        if inner_radius_mm <= 0.0:
            raise ValueError("inner_radius_mm must be > 0 for annular_disk and thin_ring.")
        ri_m = inner_radius_mm / 1000.0

    ro_m = outer_radius_mm / 1000.0
    if ro_m <= ri_m:
        raise ValueError("outer_radius_mm must be greater than inner_radius_mm.")

    thickness_m = thickness_mm / 1000.0
    omega_rad_s = 2.0 * math.pi * speed_rpm / 60.0
    tip_speed_m_s = omega_rad_s * ro_m

    area_m2 = math.pi * (ro_m**2 - ri_m**2)
    volume_m3 = area_m2 * thickness_m
    mass_kg = density_kg_m3 * volume_m3
    rotor_inertia_kg_m2 = 0.5 * mass_kg * (ro_m**2 + ri_m**2)
    kinetic_energy_j = 0.5 * rotor_inertia_kg_m2 * omega_rad_s**2

    radius_profile_m: List[float]
    sigma_r_pa: List[float] = []
    sigma_theta_pa: List[float] = []

    if geom == "thin_ring":
        rm_m = 0.5 * (ri_m + ro_m)
        radius_profile_m = _linspace(ri_m, ro_m, profile_points)
        sigma_theta_const_pa = density_kg_m3 * omega_rad_s**2 * rm_m**2
        sigma_r_pa = [0.0 for _ in radius_profile_m]
        sigma_theta_pa = [sigma_theta_const_pa for _ in radius_profile_m]
        geometry_label = "Thin Ring"
    else:
        if geom == "solid_disk":
            radius_profile_m = _linspace(0.0, ro_m, profile_points)
            geometry_label = "Solid Disk"
        else:
            radius_profile_m = _linspace(ri_m, ro_m, profile_points)
            geometry_label = "Annular Disk"

        c_coeff = (3.0 + poisson_ratio) / 8.0 * density_kg_m3 * omega_rad_s**2
        d_coeff = (1.0 + 3.0 * poisson_ratio) / 8.0 * density_kg_m3 * omega_rad_s**2

        for r_m in radius_profile_m:
            if geom == "solid_disk":
                sigma_r = c_coeff * (ro_m**2 - r_m**2)
                sigma_theta = c_coeff * ro_m**2 - d_coeff * r_m**2
            else:
                # Annular disk free-surface solution with sigma_r(ri)=sigma_r(ro)=0.
                ri2 = ri_m**2
                ro2 = ro_m**2
                r2 = r_m**2
                sigma_r = c_coeff * (ri2 + ro2 - (ri2 * ro2) / r2 - r2)
                sigma_theta = c_coeff * (ri2 + ro2 + (ri2 * ro2) / r2) - d_coeff * r2

            sigma_r_pa.append(sigma_r)
            sigma_theta_pa.append(sigma_theta)

    sigma_vm_pa = [
        math.sqrt(sr**2 - sr * st + st**2)
        for sr, st in zip(sigma_r_pa, sigma_theta_pa)
    ]

    max_theta_pa = max(sigma_theta_pa)
    max_theta_idx = sigma_theta_pa.index(max_theta_pa)
    critical_radius_mm = radius_profile_m[max_theta_idx] * 1000.0
    max_radial_pa = max(abs(sr) for sr in sigma_r_pa)
    max_vm_pa = max(sigma_vm_pa)

    max_theta_mpa = max_theta_pa / 1e6
    max_radial_mpa = max_radial_pa / 1e6
    max_vm_mpa = max_vm_pa / 1e6

    yield_safety_factor = (yield_strength_mpa / max_vm_mpa) if max_vm_mpa > 0.0 else float("inf")
    utilization_percent = (100.0 * max_vm_mpa / yield_strength_mpa) if yield_strength_mpa > 0.0 else float("inf")

    allowable_vm_mpa = yield_strength_mpa / required_safety_factor
    allowable_speed_rpm = (
        speed_rpm * math.sqrt(allowable_vm_mpa / max_vm_mpa)
        if max_vm_mpa > 0.0
        else float("inf")
    )

    if yield_safety_factor >= required_safety_factor:
        status = "acceptable"
    elif yield_safety_factor >= 1.0:
        status = "marginal"
    else:
        status = "unacceptable"

    recommendations: List[str] = []
    if status != "acceptable":
        recommendations.append(
            "Reduce operating speed or increase radius/thickness margin to improve stress safety factor."
        )
    if geom == "thin_ring":
        ring_slenderness = (ro_m - ri_m) / (0.5 * (ro_m + ri_m))
        if ring_slenderness > 0.2:
            recommendations.append(
                "Thin-ring assumption may be optimistic for this width; compare against annular-disk model."
            )
    if tip_speed_m_s > 200.0:
        recommendations.append(
            "High rim speed detected; include containment, burst, and balancing considerations in final design."
        )
    if not recommendations:
        recommendations.append(
            "Stress margins meet the selected target. Validate with detailed FEA and overspeed test criteria."
        )

    if geom == "solid_disk":
        subst_max_hoop = (
            "\\sigma_{\\theta,max} = \\frac{3+\\nu}{8}\\rho\\omega^2r_o^2"
            f" = \\frac{{3+{poisson_ratio:.3f}}}{{8}}({density_kg_m3:.1f})({omega_rad_s:.2f})^2({ro_m:.4f})^2"
            f" = {max_theta_mpa:.3f}\\text{{ MPa}}"
        )
    elif geom == "annular_disk":
        subst_max_hoop = (
            "\\sigma_{\\theta,max}\\approx\\sigma_{\\theta}(r_i)"
            " = \\frac{\\rho\\omega^2}{4}\\left[(3+\\nu)r_o^2 + (1-\\nu)r_i^2\\right]"
            f" = \\frac{{{density_kg_m3:.1f}({omega_rad_s:.2f})^2}}{{4}}"
            f"\\left[(3+{poisson_ratio:.3f})({ro_m:.4f})^2 + (1-{poisson_ratio:.3f})({ri_m:.4f})^2\\right]"
            f" = {max_theta_mpa:.3f}\\text{{ MPa}}"
        )
    else:
        rm_m = 0.5 * (ri_m + ro_m)
        subst_max_hoop = (
            "\\sigma_{\\theta} = \\rho\\omega^2r_m^2"
            f" = ({density_kg_m3:.1f})({omega_rad_s:.2f})^2({rm_m:.4f})^2"
            f" = {max_theta_mpa:.3f}\\text{{ MPa}}"
        )

    subst_max_vm = (
        "\\sigma_{vm,max} = \\max\\left(\\sqrt{\\sigma_r^2 - \\sigma_r\\sigma_\\theta + \\sigma_\\theta^2}\\right)"
        f" = {max_vm_mpa:.3f}\\text{{ MPa}}"
    )

    subst_sf = (
        "SF_y = \\frac{S_y}{\\sigma_{vm,max}}"
        f" = \\frac{{{yield_strength_mpa:.2f}}}{{{max_vm_mpa:.3f}}}"
        f" = {yield_safety_factor:.3f}"
    )

    if math.isinf(allowable_speed_rpm):
        subst_allow_speed = "n_{allow} = \\infty"
    else:
        subst_allow_speed = (
            "n_{allow} = n\\sqrt{\\frac{S_y/SF_{req}}{\\sigma_{vm,max}}}"
            f" = {speed_rpm:.1f}\\sqrt{{\\frac{{{yield_strength_mpa:.2f}/{required_safety_factor:.2f}}}{{{max_vm_mpa:.3f}}}}}"
            f" = {allowable_speed_rpm:.1f}\\text{{ rpm}}"
        )

    return {
        "geometry_label": geometry_label,
        "angular_speed_rad_s": omega_rad_s,
        "tip_speed_m_s": tip_speed_m_s,
        "mass_kg": mass_kg,
        "rotor_inertia_kg_m2": rotor_inertia_kg_m2,
        "kinetic_energy_j": kinetic_energy_j,
        "max_hoop_stress_mpa": max_theta_mpa,
        "max_radial_stress_mpa": max_radial_mpa,
        "max_von_mises_stress_mpa": max_vm_mpa,
        "critical_radius_mm": critical_radius_mm,
        "yield_safety_factor": yield_safety_factor,
        "allowable_speed_rpm": allowable_speed_rpm,
        "utilization_percent": utilization_percent,
        "status": status,
        "recommendations": recommendations,
        "stress_profile": {
            "radius_mm": [r * 1000.0 for r in radius_profile_m],
            "sigma_r_mpa": [sr / 1e6 for sr in sigma_r_pa],
            "sigma_theta_mpa": [st / 1e6 for st in sigma_theta_pa],
            "sigma_vm_mpa": [sv / 1e6 for sv in sigma_vm_pa],
        },
        "subst_max_hoop_stress_mpa": subst_max_hoop,
        "subst_max_von_mises_stress_mpa": subst_max_vm,
        "subst_yield_safety_factor": subst_sf,
        "subst_allowable_speed_rpm": subst_allow_speed,
    }
