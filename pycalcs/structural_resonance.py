"""
Natural-frequency estimates for simply supported thin plates and free thin rings.
These idealized models do not predict forced-response amplitude or the modes of
an assembled motor housing, laminated stator, or constrained cylindrical shell.
"""

from __future__ import annotations

import math
from typing import Any

MATERIALS = {
    "steel": {
        "display": "Steel (General)",
        "elastic_modulus_gpa": 200.0,
        "density_kg_m3": 7850.0,
        "poisson_ratio": 0.30,
    },
    "aluminum": {
        "display": "Aluminum 6061",
        "elastic_modulus_gpa": 69.0,
        "density_kg_m3": 2700.0,
        "poisson_ratio": 0.33,
    },
    "cast_iron": {
        "display": "Cast Iron (Gray)",
        "elastic_modulus_gpa": 100.0,
        "density_kg_m3": 7200.0,
        "poisson_ratio": 0.28,
    },
    "titanium": {
        "display": "Titanium (Grade 5)",
        "elastic_modulus_gpa": 116.0,
        "density_kg_m3": 4430.0,
        "poisson_ratio": 0.34,
    },
}


def _finite_number(value: float, label: str, *, positive: bool = False) -> float:
    """Validate a scalar input and return its finite float representation.

    Parameters are the value, its error-message label, and whether positivity
    is required. Booleans, nonnumeric values, and nonfinite numbers raise
    ValueError. No physical equation or reference is needed for this check.
    """
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{label} must be a finite number.") from error
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number.")
    if positive and number <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return number


def _mode_number(value: int, label: str, minimum: int) -> int:
    """Return an integer mode number, rejecting truncation or clamping.

    Parameters are the supplied mode, its error-message label, and the smallest
    allowed integer. Raises ValueError for a noninteger, boolean, nonfinite, or
    too-small mode. This is input validation, with no physical equation.
    """
    number = _finite_number(value, label)
    if not number.is_integer() or number < minimum:
        raise ValueError(f"{label} must be an integer of at least {minimum}.")
    return int(number)


def _latex_number(value: float) -> str:
    r"""Format a finite number with eight significant figures for LaTeX.

    The input is a scalar value and the return is a numeric LaTeX string.
    Scientific notation uses ``mantissa \times 10^{exponent}`` so the letter
    e is not mistaken for a variable. This changes presentation, not values.
    """
    formatted = f"{value:.8g}"
    if "e" not in formatted:
        return formatted
    mantissa, exponent = formatted.split("e")
    return f"{mantissa}\\times 10^{{{int(exponent)}}}"


def calculate_structural_resonance(
    geometry_type: str,
    thickness_mm: float,
    length_mm: float,
    width_mm: float,
    diameter_mm: float,
    mode_1: int,
    mode_2: int,
    material: str,
    custom_e_gpa: float = 200.0,
    custom_rho_kg_m3: float = 7850.0,
    custom_nu: float = 0.3,
) -> dict[str, Any]:
    r"""
    Estimate one natural frequency of a simply supported plate or free thin ring.

    The rectangular plate is homogeneous and isotropic, with all four edges
    simply supported, no membrane prestress, and small transverse deflection.
    Kirchhoff plate theory neglects transverse shear and rotary inertia.

    The ring is a free, complete circular beam with a rectangular cross section;
    thickness is radial and diameter is measured at the cross-section centerline.
    Its uniform axial width cancels from I/A = h²/12. The n=0 mode is radial
    extension (breathing); n>=2 are in-plane, approximately inextensional bending
    modes. Axial constraint and a Poisson stiffening factor are not included.
    The historical geometry key "cylinder" selects this free-ring model, not a
    finite-length cylindrical shell. Attachments, teeth, laminations, damping,
    applied forces, and assembled-system modal coupling are not modeled.

    Natural frequency alone does not establish resonance severity or avoidance.
    Inputs outside their stated domains, or producing unrepresentable numerical
    results, raise ValueError. Inactive dimensions and custom properties are
    ignored, so callers need not supply plausible values for hidden fields.

    ---Parameters---
    geometry_type : str
        "plate" for an all-edges simply supported rectangular plate, or
        "cylinder" for a free thin circular ring.
    thickness_mm : float
        Positive finite plate thickness or radial ring thickness h, in mm.
        Ring thickness must be less than its mean diameter (positive bore).
    length_mm : float
        Positive finite plate length a, in mm. Ignored for the ring.
    width_mm : float
        Positive finite plate width b, in mm. Ignored for the ring.
    diameter_mm : float
        Positive finite mean ring diameter 2R, in mm. Ignored for the plate.
    mode_1 : int
        Positive integer plate mode m, the number of half-waves along length a.
        Ignored for the ring.
    mode_2 : int
        Positive integer plate mode n along width b. For the ring: n=0 is
        breathing and integer n>=2 is in-plane bending. n=1 is a rigid-body
        translation in the bending family and is excluded from this calculator.
    material : str
        Preset key steel, aluminum, cast_iron, titanium, or custom. Presets are
        representative isotropic properties, not certified grade data.
    custom_e_gpa : float
        Positive finite Young's modulus E in GPa; used only for custom material.
    custom_rho_kg_m3 : float
        Positive finite mass density rho in kg/m³; used only for custom material.
    custom_nu : float
        Finite isotropic Poisson ratio nu satisfying -1 < nu < 0.5; used only
        for custom material. It affects plate bending but not free-ring modes.

    ---Returns---
    natural_frequency_hz : float
        Undamped natural frequency for the selected idealized mode, in Hz.
    flexural_rigidity_n_m : float
        Bending stiffness per unit width in N·m. Plate: D=Eh³/[12(1-nu²)].
        Ring: EI/b=Eh³/12, with b denoting axial width. See stiffness_label.
    stiffness_label : str
        Geometry-specific label distinguishing plate rigidity from ring EI/b.
    wave_velocity_m_s : float
        Extensional rod/ring wave speed sqrt(E/rho), in m/s. This is not the
        three-dimensional longitudinal wave speed in a bulk elastic solid.
    elastic_modulus_gpa : float
        Young's modulus actually used, in GPa.
    density_kg_m3 : float
        Mass density actually used, in kg/m³.
    poisson_ratio : float
        Poisson ratio of the selected material; not used in free-ring frequency.
    thickness_ratio : float
        h/min(a,b) for the plate or h/R for the ring. A thin-model diagnostic,
        not a pass/fail criterion; short mode wavelengths also limit accuracy.
    material_display : str
        Human-readable material name.
    geometry_display : str
        Description of the analyzed geometry and selected mode.
    model_assumptions : list
        Boundary conditions and mechanical assumptions for the active model.
    applicability_notes : list
        Limits needed to interpret the estimate; no safety certification implied.
    subst_natural_frequency_hz : str
        Fully substituted natural-frequency equation in LaTeX, using SI values.
    subst_flexural_rigidity_n_m : str
        Fully substituted active bending-stiffness equation in LaTeX.
    subst_wave_velocity_m_s : str
        Fully substituted extensional wave-speed equation in LaTeX.

    ---LaTeX---
    D = \frac{E h^3}{12(1-\nu^2)}
    f_{m,n} = \frac{\pi}{2}\sqrt{\frac{D}{\rho h}}\left[\left(\frac{m}{a}\right)^2+\left(\frac{n}{b}\right)^2\right]
    \frac{EI}{b} = \frac{E h^3}{12}
    c_e = \sqrt{\frac{E}{\rho}}
    f_0 = \frac{c_e}{2\pi R}
    f_n = \frac{1}{2\pi}\sqrt{\frac{E h^2}{12\rho R^4}}\frac{n(n^2-1)}{\sqrt{n^2+1}}

    ---Symbols---
    E: Young's modulus (Pa); h: thickness (m); ρ: mass density (kg/m³);
    ν: Poisson ratio; a, b: plate length and width (m); D: plate rigidity
    (N·m); m, n: integer mode indices; R: mean ring radius (m);
    I: ring section second moment (m⁴); b in EI/b: ring axial width (m);
    cₑ: extensional speed (m/s); f: frequency (Hz).

    ---References---
    Leissa, A. W. (1969), Vibration of Plates, NASA SP-160, rectangular plates
    with all edges simply supported, Chapter 4.
    https://ntrs.nasa.gov/citations/19700009156
    Knight, N. F., Jr., and Rankin, C. C. (2006), STAGS Example Problems Manual,
    NASA/CR-2006-214281, Free Vibration of Circular Ring, pp. 40-41. These
    analytical ring formulas cite Timoshenko, Young and Weaver (1974),
    Vibration Problems in Engineering, pp. 476-481.
    https://ntrs.nasa.gov/citations/20060008654
    """
    if geometry_type not in ("plate", "cylinder"):
        raise ValueError("Geometry must be 'plate' or 'cylinder' (free ring).")

    if material == "custom":
        e_gpa = _finite_number(custom_e_gpa, "Young's modulus", positive=True)
        rho = _finite_number(custom_rho_kg_m3, "Density", positive=True)
        nu = _finite_number(custom_nu, "Poisson ratio")
        if not -1 < nu < 0.5:
            raise ValueError("Poisson ratio must be greater than -1 and less than 0.5.")
        mat_display = "Custom Material"
    else:
        if material not in MATERIALS:
            raise ValueError(f"Unknown material: {material}")
        mat_props = MATERIALS[material]
        e_gpa = mat_props["elastic_modulus_gpa"]
        rho = mat_props["density_kg_m3"]
        nu = mat_props["poisson_ratio"]
        mat_display = mat_props["display"]

    h_m = _finite_number(thickness_mm, "Thickness", positive=True) / 1000.0
    if geometry_type == "plate":
        a_m = _finite_number(length_mm, "Plate length", positive=True) / 1000.0
        b_m = _finite_number(width_mm, "Plate width", positive=True) / 1000.0
        m = _mode_number(mode_1, "Plate mode m", 1)
        n = _mode_number(mode_2, "Plate mode n", 1)
        dimensions = (h_m, a_m, b_m)
    else:
        radius = _finite_number(diameter_mm, "Mean ring diameter", positive=True) / 2000.0
        if h_m >= 2 * radius:
            raise ValueError(
                "Ring thickness must be less than the mean diameter "
                "so the inner diameter is positive."
            )
        n = _mode_number(mode_2, "Ring mode n", 0)
        if n == 1:
            raise ValueError(
                "Ring n=1 is a rigid-body translation in the bending family. "
                "Choose n=0 for breathing or n>=2 for bending."
            )
        dimensions = (h_m, radius)
    if any(not math.isfinite(value) or value <= 0 for value in dimensions):
        raise ValueError("Dimensions are outside the supported numeric range.")

    try:
        e_pa = e_gpa * 1e9
        wave_vel = math.sqrt(e_pa / rho)
        if geometry_type == "plate":
            rigidity = e_pa * h_m**3 / (12 * (1 - nu**2))
            term = (m / a_m)**2 + (n / b_m)**2
            freq = math.pi / 2 * wave_vel * h_m / math.sqrt(12 * (1 - nu**2)) * term
            thickness_ratio = h_m / min(a_m, b_m)
            stiffness_label = "Plate flexural rigidity D"
            geom_display = f"Rectangular Plate, Mode ({m},{n})"
            assumptions = [
                "All four plate edges are simply supported; rotations are free.",
                "Uniform isotropic thin plate, small deflection, no membrane prestress.",
                "Shear deformation and rotary inertia are omitted.",
            ]
            subst_rigidity = (
                f"D = \\frac{{{_latex_number(e_pa)}({_latex_number(h_m)})^3}}"
                f"{{12[1-({_latex_number(nu)})^2]}}"
                f" = {_latex_number(rigidity)}\\;\\mathrm{{N\\,m}}"
            )
            subst_freq = (
                f"f_{{{m},{n}}} = \\frac{{\\pi}}{{2}}\\sqrt{{"
                f"\\frac{{{_latex_number(rigidity)}}}"
                f"{{{_latex_number(rho)}({_latex_number(h_m)})}}}}"
                f"\\left[\\left(\\frac{{{m}}}{{{_latex_number(a_m)}}}\\right)^2+"
                f"\\left(\\frac{{{n}}}{{{_latex_number(b_m)}}}\\right)^2\\right]"
                f" = {_latex_number(freq)}\\;\\mathrm{{Hz}}"
            )
            ratio_note = (
                f"Thickness / shorter span = {thickness_ratio:.4g}. Thin-plate "
                "theory also requires thickness small relative to the selected "
                "mode's bending wavelength."
            )
        else:
            rigidity = e_pa * h_m**3 / 12
            thickness_ratio = h_m / radius
            stiffness_label = "Ring bending stiffness per axial width EI/b"
            assumptions = [
                "Free complete circular ring with a uniform rectangular cross section.",
                "Diameter is the mean diameter; thickness is the radial dimension.",
                "Axial width cancels from I/A; axial constraint is not included.",
                "Thin-ring motion with no shear deformation or rotary inertia.",
            ]
            subst_rigidity = (
                "\\frac{EI}{b} = "
                f"\\frac{{{_latex_number(e_pa)}({_latex_number(h_m)})^3}}{{12}}"
                f" = {_latex_number(rigidity)}\\;\\mathrm{{N\\,m}}"
            )
            if n == 0:
                freq = wave_vel / (2 * math.pi * radius)
                geom_display = "Free Circular Ring, Breathing Mode (n=0)"
                subst_freq = (
                    f"f_0 = \\frac{{1}}{{2\\pi({_latex_number(radius)})}}"
                    "\\sqrt{"
                    f"\\frac{{{_latex_number(e_pa)}}}{{{_latex_number(rho)}}}"
                    "}"
                    f" = {_latex_number(freq)}\\;\\mathrm{{Hz}}"
                )
            else:
                factor = n * (n**2 - 1) / math.sqrt(n**2 + 1)
                freq = wave_vel * h_m / (math.sqrt(12) * radius**2) * factor / (2 * math.pi)
                geom_display = f"Free Circular Ring, In-Plane Bending (n={n})"
                subst_freq = (
                    f"f_{{{n}}} = \\frac{{1}}{{2\\pi}}\\sqrt{{"
                    f"\\frac{{{_latex_number(e_pa)}({_latex_number(h_m)})^2}}"
                    f"{{12({_latex_number(rho)})({_latex_number(radius)})^4}}}}"
                    f"\\frac{{{n}({n}^2-1)}}{{\\sqrt{{{n}^2+1}}}}"
                    f" = {_latex_number(freq)}\\;\\mathrm{{Hz}}"
                )
            ratio_note = (
                f"Radial thickness / mean radius = {thickness_ratio:.4g}. "
                "Thin-ring theory requires thickness small relative to radius "
                "and the selected circumferential wavelength."
            )
        numbers = (freq, rigidity, wave_vel, thickness_ratio)
        if any(not math.isfinite(value) or value <= 0 for value in numbers):
            raise ValueError("Inputs produce results outside the supported numeric range.")
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError("Inputs produce results outside the supported numeric range.") from error

    notes = [
        ratio_note,
        "Mountings, joints, attached masses, and material anisotropy can change the modes.",
        "Frequency coincidence alone does not predict vibration amplitude; forcing, "
        "spatial coupling, and damping also matter.",
    ]
    if geometry_type == "cylinder":
        notes.insert(
            1, "This is a free ring, not a finite-length cylindrical shell "
            "or assembled stator model."
        )

    return {
        "natural_frequency_hz": freq,
        "flexural_rigidity_n_m": rigidity,
        "stiffness_label": stiffness_label,
        "wave_velocity_m_s": wave_vel,
        "elastic_modulus_gpa": e_gpa,
        "density_kg_m3": rho,
        "poisson_ratio": nu,
        "thickness_ratio": thickness_ratio,
        "material_display": mat_display,
        "geometry_display": geom_display,
        "model_assumptions": assumptions,
        "applicability_notes": notes,
        "subst_natural_frequency_hz": subst_freq,
        "subst_flexural_rigidity_n_m": subst_rigidity,
        "subst_wave_velocity_m_s": (
            "c_e = \\sqrt{"
            f"\\frac{{{_latex_number(e_pa)}}}{{{_latex_number(rho)}}}"
            "}"
            f" = {_latex_number(wave_vel)}\\;\\mathrm{{m/s}}"
        ),
    }
