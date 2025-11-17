"""
Reusable calculations for snap-fit designs.
"""

from __future__ import annotations

import math


def calculate_cantilever_snap_fit(
    length: float,
    thickness: float,
    width: float,
    install_deflection: float,
    service_deflection: float,
    removal_deflection: float,
    modulus: float,
    allowable_strain: float,
    install_angle_deg: float,
    removal_angle_deg: float,
    friction_coefficient: float,
) -> dict[str, float]:
    """
    Evaluates a rectangular cantilever snap-fit using BASF handbook beam theory.

    The model follows the classical small-deflection solution for a rectangular
    cantilever snap arm. Installation, service, and removal states are assessed
    by combining beam tip stiffness with contact geometry to estimate the user
    forces. See BASF, *Snap-Fit Design Manual* (2016) for detailed background.

    ---Parameters---
    length : float
        Free length of the cantilever from the fixed root to the contact point (m).
    thickness : float
        Beam thickness measured in the bending direction (m).
    width : float
        Beam width perpendicular to bending (m).
    install_deflection : float
        Peak tip deflection required during installation (m).
    service_deflection : float
        Residual tip deflection while the assembly is engaged (m).
    removal_deflection : float
        Tip deflection required to disengage the latch (m).
    modulus : float
        Tensile modulus of the snap-fit material (Pa).
    allowable_strain : float
        Maximum allowable fiber strain for the material (dimensionless).
    install_angle_deg : float
        Ramp angle of the lead-in face relative to the insertion direction (deg).
    removal_angle_deg : float
        Ramp angle of the release face relative to the pull-off direction (deg).
    friction_coefficient : float
        Coefficient of friction between mating surfaces (dimensionless).

    ---Returns---
    spring_constant : float
        Tip stiffness of the cantilever (N/m).
    install_tip_force : float
        Peak transverse force applied at the snap tip during installation (N).
    install_axial_force : float
        Estimated axial user force required to seat the snap (N).
    install_stress : float
        Maximum bending stress at the fixed end during installation (Pa).
    install_strain : float
        Maximum fiber strain at the fixed end during installation (dimensionless).
    allowable_deflection : float
        Tip deflection limit corresponding to the allowable strain (m).
    install_safety_factor : float
        Ratio of allowable deflection to installation deflection (dimensionless).
    service_tip_force : float
        Reaction force at the tip in the engaged condition (N).
    service_stress : float
        Maximum bending stress at the fixed end in service (Pa).
    service_strain : float
        Maximum fiber strain at the fixed end in service (dimensionless).
    retention_axial_force : float
        Axial force maintained by the snap while engaged (N).
    removal_tip_force : float
        Transverse force required at the tip to release the snap (N).
    removal_axial_force : float
        Estimated axial pull necessary to disengage the snap (N).
    removal_stress : float
        Maximum bending stress at the fixed end during removal (Pa).
    removal_strain : float
        Maximum fiber strain at the fixed end during removal (dimensionless).

    ---LaTeX---
    k = \\frac{E\\,b\\,t^{3}}{4\\,L^{3}}
    F = k\\,\\delta
    \\sigma = \\frac{6 F L}{b t^{2}}
    \\varepsilon = \\frac{\\sigma}{E}
    \\delta_{\\text{allow}} = \\frac{2}{3}\\,\\varepsilon_{\\text{allow}}\\,\\frac{L^{2}}{t}
    F_{\\text{axial}} = F\\,\\frac{\\sin\\theta + \\mu \\cos\\theta}{\\cos\\theta - \\mu \\sin\\theta}
    """

    if length <= 0.0:
        raise ValueError("length must be positive.")
    if thickness <= 0.0:
        raise ValueError("thickness must be positive.")
    if width <= 0.0:
        raise ValueError("width must be positive.")
    if modulus <= 0.0:
        raise ValueError("modulus must be positive.")
    if allowable_strain <= 0.0:
        raise ValueError("allowable_strain must be positive.")
    if install_deflection < 0.0:
        raise ValueError("install_deflection cannot be negative.")
    if service_deflection < 0.0:
        raise ValueError("service_deflection cannot be negative.")
    if removal_deflection < 0.0:
        raise ValueError("removal_deflection cannot be negative.")
    if friction_coefficient < 0.0:
        raise ValueError("friction_coefficient cannot be negative.")

    stiffness = modulus * width * thickness**3 / (4.0 * length**3)

    def _state_outputs(deflection: float) -> tuple[float, float, float]:
        tip_force = stiffness * deflection
        stress = 0.0
        strain = 0.0
        if deflection > 0.0:
            stress = 6.0 * tip_force * length / (width * thickness**2)
            strain = stress / modulus
        return tip_force, stress, strain

    def _axial_force(tip_force: float, angle_deg: float) -> float:
        if tip_force == 0.0:
            return 0.0
        angle_rad = math.radians(angle_deg)
        sin_term = math.sin(angle_rad)
        cos_term = math.cos(angle_rad)
        denominator = cos_term - friction_coefficient * sin_term
        if denominator <= 0.0:
            raise ValueError(
                "The specified angle and friction coefficient create a self-locking "
                "interface (cos(theta) - mu*sin(theta) <= 0). Adjust geometry or "
                "lubrication to make assembly feasible."
            )
        numerator = sin_term + friction_coefficient * cos_term
        return tip_force * numerator / denominator

    install_tip_force, install_stress, install_strain = _state_outputs(install_deflection)
    service_tip_force, service_stress, service_strain = _state_outputs(service_deflection)
    removal_tip_force, removal_stress, removal_strain = _state_outputs(removal_deflection)

    allowable_deflection = (2.0 / 3.0) * allowable_strain * length**2 / thickness
    if install_deflection > 0.0:
        install_safety_factor = allowable_deflection / install_deflection
    else:
        install_safety_factor = math.inf

    install_axial_force = _axial_force(install_tip_force, install_angle_deg)
    retention_axial_force = _axial_force(service_tip_force, removal_angle_deg)
    removal_axial_force = _axial_force(removal_tip_force, removal_angle_deg)

    results: dict[str, float] = {
        "spring_constant": stiffness,
        "install_tip_force": install_tip_force,
        "install_axial_force": install_axial_force,
        "install_stress": install_stress,
        "install_strain": install_strain,
        "allowable_deflection": allowable_deflection,
        "install_safety_factor": install_safety_factor,
        "service_tip_force": service_tip_force,
        "service_stress": service_stress,
        "service_strain": service_strain,
        "retention_axial_force": retention_axial_force,
        "removal_tip_force": removal_tip_force,
        "removal_axial_force": removal_axial_force,
        "removal_stress": removal_stress,
        "removal_strain": removal_strain,
    }

    thickness_cubed = thickness**3
    length_cubed = length**3

    results["subst_spring_constant"] = (
        f"k = \\frac{{E b t^3}}{{4 L^3}} = "
        f"\\frac{{{modulus:.3e} \\times {width:.3e} \\times {thickness_cubed:.3e}}}"
        f"{{4 \\times {length_cubed:.3e}}} = {stiffness:.3e} \\, \\text{{N/m}}"
    )
    results["subst_install_tip_force"] = (
        f"F_{{\\text{{tip}}, i}} = k\\,\\delta_i = {stiffness:.3e}"
        f" \\times {install_deflection:.3e} = {install_tip_force:.3e} \\, \\text{{N}}"
    )
    results["subst_install_axial_force"] = (
        f"F_{{\\text{{axial}}, i}} = F_{{\\text{{tip}}, i}}"
        f" \\frac{{\\sin\\theta_i + \\mu \\cos\\theta_i}}{{\\cos\\theta_i - \\mu \\sin\\theta_i}}"
        f" = {install_axial_force:.3e} \\, \\text{{N}}"
    )
    results["subst_install_stress"] = (
        f"\\sigma_i = \\frac{{6 F_{{\\text{{tip}}, i}} L}}{{b t^2}} = {install_stress:.3e} \\, \\text{{Pa}}"
    )
    results["subst_allowable_deflection"] = (
        f"\\delta_{{\\text{{allow}}}} = \\frac{{2}}{{3}} \\varepsilon_{{\\text{{allow}}}}"
        f" \\frac{{L^2}}{{t}} = {allowable_deflection:.3e} \\, \\text{{m}}"
    )
    results["subst_install_safety_factor"] = (
        f"N_i = \\frac{{\\delta_{{\\text{{allow}}}}}}{{\\delta_i}} = {install_safety_factor:.3f}"
    )
    results["subst_retention_axial_force"] = (
        f"F_{{\\text{{axial}}, s}} = F_{{\\text{{tip}}, s}}"
        f" \\frac{{\\sin\\theta_r + \\mu \\cos\\theta_r}}{{\\cos\\theta_r - \\mu \\sin\\theta_r}}"
        f" = {retention_axial_force:.3e} \\, \\text{{N}}"
    )
    results["subst_removal_axial_force"] = (
        f"F_{{\\text{{axial}}, r}} = F_{{\\text{{tip}}, r}}"
        f" \\frac{{\\sin\\theta_r + \\mu \\cos\\theta_r}}{{\\cos\\theta_r - \\mu \\sin\\theta_r}}"
        f" = {removal_axial_force:.3e} \\, \\text{{N}}"
    )

    return results
