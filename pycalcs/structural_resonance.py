"""
Natural-frequency estimates for uniform beams, thin plates, and free thin rings.
These idealized models do not predict forced-response amplitude or the modes of
an assembled motor housing, laminated stator, or constrained cylindrical shell.
"""

from __future__ import annotations

import math
from typing import Any

if __package__:
    from .beam_analysis import compute_section_properties
else:  # Standalone Pyodide modules are loaded beside each other.
    from beam_analysis import compute_section_properties

_PLASTIC_MODEL_NOTES = (
    "Poisson ratio is an assumed modeling value, not reported by the linked "
    "manufacturer source. It affects the plate model only.",
    "Tensile-test modulus is a starting estimate for vibration. Plastic stiffness "
    "depends on temperature, loading rate and moisture; use measured dynamic "
    "properties for the operating conditions when available.",
    "These presets represent solid, unfilled material. Filled or 3D-printed "
    "parts may require direction-dependent properties outside this isotropic model.",
)

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
    "abs": {
        "display": "ABS (unfilled)",
        "elastic_modulus_gpa": 1.7,
        "density_kg_m3": 1040.0,
        "poisson_ratio": 0.35,
        "notes": [
            "Representative grade: Ensinger TECARAN ABS grey. Modulus is from a "
            "tensile test at 1 mm/min (ISO 527-2); the listed test temperature "
            "and conditioning are unspecified.",
            *_PLASTIC_MODEL_NOTES,
        ],
        "sources": [{
            "title": "Ensinger TECARAN ABS grey: tensile modulus and density",
            "url": "https://www.ensingerplastics.com/en-gb/shapes/tecaran-abs-grey",
            "properties": ["elastic_modulus_gpa", "density_kg_m3"],
        }],
    },
    "polycarbonate": {
        "display": "Polycarbonate (PC)",
        "elastic_modulus_gpa": 2.4,
        "density_kg_m3": 1200.0,
        "poisson_ratio": 0.37,
        "notes": [
            "Representative grade: Covestro Makrolon 2805. Tensile modulus is "
            "measured at 23 °C and 50% relative humidity, at 1 mm/min "
            "(ISO 527-1/-2); density is reported at 23 °C.",
            *_PLASTIC_MODEL_NOTES,
        ],
        "sources": [{
            "title": "Covestro Makrolon 2805: tensile modulus and density",
            "url": (
                "https://solutions.covestro.com/en/products/makrolon/"
                "makrolon-2805_000000000057534382"
            ),
            "properties": ["elastic_modulus_gpa", "density_kg_m3"],
        }],
    },
    "acetal": {
        "display": "Acetal (POM-C)",
        "elastic_modulus_gpa": 2.8,
        "density_kg_m3": 1410.0,
        "poisson_ratio": 0.35,
        "notes": [
            "Representative grade: Ensinger TECAFORM AH natural, unfilled POM-C. "
            "Modulus is from a tensile test at 1 mm/min (ISO 527-2); the listed "
            "test temperature and conditioning are unspecified.",
            *_PLASTIC_MODEL_NOTES,
        ],
        "sources": [{
            "title": "Ensinger TECAFORM AH natural: tensile modulus and density",
            "url": (
                "https://www.ensingerplastics.com/en-gb/shapes/"
                "acetal-tecaform-ah-natural"
            ),
            "properties": ["elastic_modulus_gpa", "density_kg_m3"],
        }],
    },
    "nylon6": {
        "display": "Nylon 6 (PA6, dry)",
        "elastic_modulus_gpa": 3.5,
        "density_kg_m3": 1130.0,
        "poisson_ratio": 0.39,
        "notes": [
            "Representative grade: BASF Ultramid B3S R03, uncoloured PA6 at "
            "23 °C. This preset uses the dry tensile modulus. Moisture "
            "conditioning substantially lowers stiffness; use custom material "
            "properties for conditioned parts.",
            *_PLASTIC_MODEL_NOTES,
        ],
        "sources": [{
            "title": "BASF Ultramid B3S R03: dry tensile modulus and density",
            "url": (
                "https://download.basf.com/p1/8a8082587fd4b608017fd66339d424db/"
                "en/ULTRAMID%25C2%25AE_B3S_R03"
            ),
            "properties": ["elastic_modulus_gpa", "density_kg_m3"],
        }],
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


def _material_properties(
    material: str, custom_e_gpa: float, custom_rho_kg_m3: float, custom_nu: float
) -> tuple[float, float, float, str]:
    """Return validated E (GPa), density (kg/m³), nu, and a material label.

    Inputs select a preset or supply custom isotropic properties. Custom E and
    density must be positive and finite; isotropic stability requires -1<nu<0.5.
    Presets use MATERIALS without consulting the inactive custom values.
    """
    if material == "custom":
        e_gpa = _finite_number(custom_e_gpa, "Young's modulus", positive=True)
        rho = _finite_number(custom_rho_kg_m3, "Density", positive=True)
        nu = _finite_number(custom_nu, "Poisson ratio")
        if not -1 < nu < 0.5:
            raise ValueError("Poisson ratio must be greater than -1 and less than 0.5.")
        return e_gpa, rho, nu, "Custom Material"
    if material not in MATERIALS:
        raise ValueError(f"Unknown material: {material}")
    properties = MATERIALS[material]
    return (
        properties["elastic_modulus_gpa"], properties["density_kg_m3"],
        properties["poisson_ratio"], properties["display"],
    )


def _plate_diagram(a_m: float, b_m: float, h_m: float, m: int, n: int) -> dict:
    r"""Sample the simply supported plate mode on normalized x/y coordinates.

    Inputs are SI dimensions and positive integer half-wave counts. Output has
    millimetre geometry and displacement[y][x] = sin(m*pi*x)*sin(n*pi*y).
    Each half-wave gets eight intervals and the maximum amplitude is one.
    Modes above 12 per axis retain geometry but are marked unavailable to
    avoid aliasing or excessive data. See Leissa NASA SP-160, Chapter 4.
    """
    diagram = {
        "kind": "plate", "available": True,
        "geometry": {
            "length_mm": a_m * 1000, "width_mm": b_m * 1000,
            "thickness_mm": h_m * 1000,
        },
        "mode_label": f"Plate mode ({m}, {n})",
        "support_type": "simply_supported",
    }
    if max(m, n) > 12:
        diagram.update(available=False, reason="Mode drawing supports m and n up to 12.")
        return diagram
    # Multiples of each index preserve nodal and antinodal stations.
    nx = 8 * m * max(1, math.ceil(3 / m))
    ny = 8 * n * max(1, math.ceil(3 / n))
    x = [i / nx for i in range(nx + 1)]
    y = [j / ny for j in range(ny + 1)]
    diagram.update(x=x, y=y, displacement=[
        [math.sin(m * math.pi * xi) * math.sin(n * math.pi * yi) for xi in x]
        for yi in y
    ])
    return diagram


def _ring_diagram(radius: float, h_m: float, n: int) -> dict:
    r"""Return radial and tangential free-ring mode samples around the circle.

    Inputs are mean radius and radial thickness in metres and mode index n.
    Output theta is in radians and geometry in mm. For n>=2, u=cos(n*theta)
    and v=-sin(n*theta)/n share one normalization and satisfy dv/dtheta+u=0,
    the linear inextensional condition. Breathing has u=1,v=0. See NASA
    CR-2006-214281 pp. 40-41. Above n=32, drawing is unavailable to avoid
    aliasing; frequencies and geometry remain valid outputs of the model.
    """
    diagram = {
        "kind": "ring", "available": True,
        "geometry": {"diameter_mm": radius * 2000, "thickness_mm": h_m * 1000},
        "mode_label": f"Ring mode n={n}", "support_type": "free",
    }
    if n > 32:
        diagram.update(available=False, reason="Mode drawing supports ring n up to 32.")
        return diagram
    segments = max(128, 32 * n)
    theta = [2 * math.pi * i / segments for i in range(segments + 1)]
    diagram.update(
        theta=theta,
        radial=[math.cos(n * angle) for angle in theta],
        tangential=[-math.sin(n * angle) / n if n else 0.0 for angle in theta],
    )
    return diagram


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
        A preset key from MATERIALS, or custom. Presets are representative
        isotropic properties; optional notes and sources describe the grade,
        test conditions and assumed properties.
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
        Model limits and selected preset material notes, including relevant
        test conditions and property assumptions.
    diagram_data : dict
        Selected physical mode shape, normalized to unit maximum displacement.
        kind is plate or ring; geometry holds dimensions in mm. Plate x and y
        run from 0 to 1, with displacement[y][x]. Ring theta is in radians, with
        radial and tangential arrays sharing one amplitude normalization.
        available is false with a reason above the drawing's sampling limits.
        Amplitudes describe shapes, not predicted vibration magnitudes.
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
    \phi_{m,n}(\xi,\eta) = \sin(m\pi\xi)\sin(n\pi\eta)
    u_n(\theta) = \cos(n\theta),\quad v_n(\theta) = -\frac{\sin(n\theta)}{n}\quad(n\ge2)
    u_0 = 1,\quad v_0 = 0

    ---Symbols---
    E: Young's modulus (Pa); h: thickness (m); ρ: mass density (kg/m³);
    ν: Poisson ratio; a, b: plate length and width (m); D: plate rigidity
    (N·m); m, n: integer mode indices; R: mean ring radius (m);
    I: ring section second moment (m⁴); b in EI/b: ring axial width (m);
    cₑ: extensional speed (m/s); f: frequency (Hz); xi, eta: x/a and y/b;
    phi: normalized transverse plate displacement; theta: angular position
    (radians); u, v: normalized radial and tangential ring displacements.

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

    e_gpa, rho, nu, mat_display = _material_properties(
        material, custom_e_gpa, custom_rho_kg_m3, custom_nu
    )

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
    notes.extend(MATERIALS.get(material, {}).get("notes", []))

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
        "diagram_data": (
            _plate_diagram(a_m, b_m, h_m, m, n) if geometry_type == "plate"
            else _ring_diagram(radius, h_m, n)
        ),
        "subst_natural_frequency_hz": subst_freq,
        "subst_flexural_rigidity_n_m": subst_rigidity,
        "subst_wave_velocity_m_s": (
            "c_e = \\sqrt{"
            f"\\frac{{{_latex_number(e_pa)}}}{{{_latex_number(rho)}}}"
            "}"
            f" = {_latex_number(wave_vel)}\\;\\mathrm{{m/s}}"
        ),
    }


# Positive elastic-mode roots of cos(lambda)*cosh(lambda) = -1 or +1.
# Rigid-body roots are excluded. References are in calculate_beam_resonance.
BEAM_ROOTS = {
    "cantilever": (
        1.875104068711961, 4.694091132974174, 7.854757438237613,
        10.995540734875467, 14.13716839104647,
    ),
    "simply_supported": tuple(n * math.pi for n in range(1, 6)),
    "fixed_fixed": (
        4.730040744862704, 7.853204624095838, 10.99560783800167,
        14.137165491257464, 17.27875965739948,
    ),
}


def _tip_mass_characteristic(eigenvalue: float, mass_ratio: float) -> float:
    r"""Return the overflow-scaled point-tip-mass characteristic residual.

    Inputs are dimensionless lambda and r=M/(rho*A*L), both nonnegative.
    The returned value is F/[cosh(lambda)*max(1,r)], with
    F=1+cos(lambda)cosh(lambda)+r*lambda*(cos(lambda)sinh(lambda)
    -sin(lambda)cosh(lambda)). The positive scale preserves every root.
    A power series avoids cancellation near lambda=0; dividing by r for
    large masses avoids overflow. Source: NACA TN3459, equation (13).
    """
    if eigenvalue < 0.25:
        fourth = eigenvalue**4
        # cos(lambda)*cosh(lambda) = sum (-4)^k lambda^(4k)/(4k)!.
        base = 2.0
        mass_term = 0.0
        for k in range(1, 5):
            term = (-4.0)**k * fourth**k / math.factorial(4 * k)
            base += term
            mass_term += 4 * k * term
        value = (
            base / mass_ratio + mass_term if mass_ratio >= 1
            else base + mass_ratio * mass_term
        )
        return value / math.cosh(eigenvalue)
    c, s = math.cos(eigenvalue), math.sin(eigenvalue)
    base = c + 1 / math.cosh(eigenvalue)
    mass_term = eigenvalue * (c * math.tanh(eigenvalue) - s)
    return (
        base / mass_ratio + mass_term if mass_ratio >= 1
        else base + mass_ratio * mass_term
    )


def _tip_mass_roots(mass_ratio: float) -> tuple[float, ...]:
    """Find the first five elastic cantilever roots for a point tip mass.

    The input r is finite and nonnegative. Returns dimensionless roots of the
    NACA TN3459 equation implemented by _tip_mass_characteristic. The first
    branch is bracketed from zero using the heavy-mass scale (3/r)^(1/4);
    later branches lie between (n-1)*pi and their unloaded roots. Bisection
    uses relative interval convergence, retaining small roots at large r.
    At exactly zero mass, the established unloaded root constants are returned.
    """
    if mass_ratio == 0:
        return BEAM_ROOTS["cantilever"]
    roots = []
    for index, unloaded in enumerate(BEAM_ROOTS["cantilever"]):
        lower = index * math.pi
        upper = unloaded + 1e-12
        if index == 0 and mass_ratio >= 1:
            upper = min(upper, 2 * (3 / mass_ratio)**0.25)
        f_lower = _tip_mass_characteristic(lower, mass_ratio)
        f_upper = _tip_mass_characteristic(upper, mass_ratio)
        if (f_lower > 0) == (f_upper > 0):
            raise ValueError("Unable to bracket the cantilever tip-mass mode.")
        for _ in range(100):
            midpoint = (lower + upper) / 2
            if midpoint == lower or midpoint == upper:
                break
            f_mid = _tip_mass_characteristic(midpoint, mass_ratio)
            if f_mid == 0:
                lower = upper = midpoint
                break
            if (f_mid > 0) == (f_lower > 0):
                lower, f_lower = midpoint, f_mid
            else:
                upper = midpoint
            if upper - lower <= 4e-16 * upper:
                break
        roots.append(min(unloaded, (lower + upper) / 2))
    return tuple(roots)


def _beam_mode_value(
    support_type: str, eigenvalue: float, xi: float, derivative: int = 0,
    mass_ratio: float = 0.0,
) -> float:
    r"""Evaluate a beam eigenfunction or its derivative with respect to x/L.

    Inputs are a supported boundary condition, its dimensionless root lambda,
    normalized position xi, derivative order 0..3, and optional tip/beam mass
    ratio. Returns an unnormalized scalar mode value. Simply supported modes
    use sin(lambda*xi). Clamped-left
    modes use cosh(z)-cos(z)-sigma*(sinh(z)-sin(z)); sigma has plus signs at a
    free end and minus signs at a clamped end. See the beam solver references.
    Derivatives allow direct checks of displacement, slope, moment and shear
    boundary conditions without finite-difference approximations.
    Small cantilever roots use the equivalent scaled function phi/lambda².
    For heavy tip masses, the exact tip-displacement identity obtained from
    the characteristic equation avoids subtracting nearly equal terms.
    """
    if derivative not in (0, 1, 2, 3):
        raise ValueError("Mode derivative order must be 0, 1, 2, or 3.")
    z = eigenvalue * xi
    if support_type == "simply_supported":
        terms = (math.sin(z), math.cos(z), -math.sin(z), -math.cos(z))
        return eigenvalue**derivative * terms[derivative]
    if (support_type == "cantilever" and eigenvalue >= 0.25
            and mass_ratio > 1e6 and xi == 1 and derivative == 0):
        return (
            2 * (math.cos(eigenvalue) + 1 / math.cosh(eigenvalue))
            / (math.tanh(eigenvalue) + math.sin(eigenvalue) / math.cosh(eigenvalue))
            / eigenvalue / mass_ratio
        )
    if support_type == "cantilever" and eigenvalue < 0.25:
        # Return phi/lambda²: arbitrary modal scaling keeps the heavy-tip-mass
        # shape finite as lambda tends to zero. Differentiate this same series.
        fourth = eigenvalue**4
        numerator = sum(fourth**k / math.factorial(4 * k) for k in range(5))
        denominator = sum(fourth**k / math.factorial(4 * k + 1) for k in range(5))
        ratio = numerator / denominator
        value = 0.0
        for k in range(5):
            power = 4 * k + 2
            if power >= derivative:
                value += (
                    2 * fourth**k * xi**(power - derivative)
                    / math.factorial(power - derivative)
                )
            power += 1
            if power >= derivative:
                value -= (
                    2 * ratio * fourth**k * xi**(power - derivative)
                    / math.factorial(power - derivative)
                )
        return value
    sign = 1 if support_type == "cantilever" else -1
    sigma = (
        (math.cosh(eigenvalue) + sign * math.cos(eigenvalue))
        / (math.sinh(eigenvalue) + sign * math.sin(eigenvalue))
    )
    ch, sh, c, s = math.cosh(z), math.sinh(z), math.cos(z), math.sin(z)
    terms = (
        ch - c - sigma * (sh - s),
        sh + s - sigma * (ch - c),
        ch + c - sigma * (sh + s),
        sh - s - sigma * (ch + c),
    )
    return eigenvalue**derivative * terms[derivative]


def calculate_beam_resonance(
    support_type: str = "cantilever",
    section_type: str = "rectangular",
    length_mm: float = 300.0,
    width_mm: float = 25.0,
    depth_mm: float = 5.0,
    outer_diameter_mm: float = 10.0,
    wall_thickness_mm: float = 1.0,
    bending_axis: str = "depth",
    mode_number: int = 1,
    material: str = "aluminum",
    custom_e_gpa: float = 200.0,
    custom_rho_kg_m3: float = 7850.0,
    custom_nu: float = 0.3,
    tip_mass_kg: float = 0.0,
) -> dict[str, Any]:
    r"""Calculate bending natural frequencies and a uniform beam's selected mode.

    Euler-Bernoulli theory assumes a straight prismatic slender beam, linear
    isotropic elasticity, small deflection, no axial load, and ideal supports.
    A cantilever may carry a point mass at its tip centerline. Its translational
    inertia changes the end-shear condition and all five frequency roots.
    Tip rotational inertia, eccentricity, axial gravity loading, distributed
    attachments, shear deformation, damping, and support compliance are omitted.
    The first five elastic bending modes in
    the selected bending plane are returned; torsion and axial modes are not.
    These are natural frequencies, not predictions of forced-response amplitude.
    Section geometry is evaluated by beam_analysis.compute_section_properties,
    the shared source for cross-sectional area and second moment of area.
    Inactive section dimensions are ignored. Invalid active inputs and
    unrepresentable numerical results raise ValueError.

    ---Parameters---
    support_type : str
        cantilever: fixed at x=0, free at x=L. simply_supported: zero transverse
        displacement and bending moment at both ends. fixed_fixed: zero
        displacement and slope at both ends.
    section_type : str
        Uniform cross section: rectangular, circular_solid, circular_hollow,
        or box (rectangular hollow section).
    length_mm : float
        Positive finite free span L between ideal supports, in mm.
    width_mm : float
        Positive finite section width, in mm; used by rectangular and box only.
    depth_mm : float
        Positive finite section depth, in mm; used by rectangular and box only.
    outer_diameter_mm : float
        Positive finite circle diameter or tube outer diameter, in mm.
        Ignored for rectangular and box sections.
    wall_thickness_mm : float
        Positive finite wall thickness, in mm; used by circular_hollow and box.
        Must leave a positive inner diameter or both positive inner dimensions.
    bending_axis : str
        depth: deflection parallel to section depth (I=b*h³/12 for a rectangle).
        width: deflection parallel to width. Ignored for circular sections.
    mode_number : int
        Integer selected elastic bending mode from 1 through 5.
    material : str
        A preset key from MATERIALS, or custom. Representative isotropic
        properties and optional material notes and sources are shared with
        the plate and ring calculators.
    custom_e_gpa : float
        Positive finite custom Young's modulus E in GPa; otherwise ignored.
    custom_rho_kg_m3 : float
        Positive finite custom mass density rho in kg/m³; otherwise ignored.
    custom_nu : float
        Custom isotropic Poisson ratio, -1 < nu < 0.5. It is reported but does
        not enter this Euler-Bernoulli frequency model; otherwise ignored.
    tip_mass_kg : float
        Finite nonnegative point mass M at the cantilever tip centerline, in kg.
        Zero recovers the unloaded beam. Ignored for other support conditions.
        Rotational inertia, eccentricity and axial gravity loading are excluded.

    ---Returns---
    natural_frequency_hz : float
        Selected undamped bending natural frequency in Hz.
    section_area_m2 : float
        Cross-sectional area A in m², from the shared section-property helper.
    second_moment_m4 : float
        Second moment of area I for the selected bending plane, in m⁴.
    mass_per_length_kg_m : float
        Uniform beam mass per unit length mu=rho*A, in kg/m.
    beam_mass_kg : float
        Beam-only mass mu*L, in kg; attachments are not included.
    tip_mass_kg : float
        Effective cantilever tip mass, in kg; zero for other support conditions.
    tip_mass_ratio : float
        Effective tip mass divided by beam-only mass, r=M/(rho*A*L).
    total_mass_kg : float
        Beam-only mass plus the effective point tip mass, in kg.
    bending_rigidity_n_m2 : float
        Beam bending rigidity EI in N·m².
    eigenvalue : float
        Selected dimensionless positive frequency root lambda=beta*L.
    eigenvalue_residual : float
        Selected characteristic residual. For a cantilever it is divided by
        cosh(lambda)*max(1,r); for fixed-fixed by cosh(lambda). For pinned ends
        it is sin(lambda). This scaled dimensionless residual should be near zero.
    mode_frequencies : list
        First five bending modes, each with mode_number, eigenvalue, and
        natural_frequency_hz. All use the selected bending plane and supports.
    diagram_data : dict
        kind=beam, available=true, physical geometry in mm, support_type,
        section_type, bending_axis, mode_label and effective tip_mass_kg.
        x is normalized position x/L from 0 to 1; displacement is the selected
        normalized transverse
        eigenfunction at 201 stations, with maximum sampled absolute value 1.
        Shape amplitude is arbitrary, not a predicted displacement in mm.
    wave_velocity_m_s : float
        Extensional speed sqrt(E/rho) in m/s, not bulk longitudinal wave speed.
    elastic_modulus_gpa : float
        Young's modulus actually used, in GPa.
    density_kg_m3 : float
        Mass density actually used, in kg/m³.
    poisson_ratio : float
        Reported material Poisson ratio; not used in this beam frequency model.
    thickness_ratio : float
        Section size along deflection divided by beam length, dimensionless.
        This is a model diagnostic, not a pass/fail criterion.
    stiffness_label : str
        Human-readable name for the beam's bending rigidity EI.
    material_display : str
        Human-readable material name.
    geometry_display : str
        Active support condition, section and selected bending mode.
    model_assumptions : list
        Mechanical idealizations and boundary conditions for the selected beam.
    applicability_notes : list
        Limits of the thin-beam model, modal-frequency interpretation, and
        selected material preset, including property assumptions.
    subst_natural_frequency_hz : str
        Fully substituted selected natural-frequency equation in LaTeX.
    subst_bending_rigidity_n_m2 : str
        Fully substituted beam bending-rigidity equation in LaTeX.
    subst_wave_velocity_m_s : str
        Fully substituted extensional wave-speed equation in LaTeX.
    subst_mass_per_length_kg_m : str
        Fully substituted mass-per-unit-length equation in LaTeX.
    subst_tip_mass_ratio : str
        Substituted effective tip-mass ratio and total-mass equations in LaTeX.
    subst_eigenvalue : str
        Selected numeric root, effective mass ratio, and scaled residual in LaTeX.

    ---LaTeX---
    \mu = \rho A
    B = EI
    c_e = \sqrt{\frac{E}{\rho}}
    f_n = \frac{\lambda_n^2}{2\pi L^2}\sqrt{\frac{EI}{\rho A}}
    \cos\lambda_n\cosh\lambda_n = -1\quad\text{(cantilever, M=0)}
    r = \frac{M}{\rho A L}
    F(\lambda;r) = 1+\cos\lambda\cosh\lambda+r\lambda(\cos\lambda\sinh\lambda-\sin\lambda\cosh\lambda)=0
    \phi''(1)=0,\quad\phi'''(1)+r\lambda^4\phi(1)=0\quad\text{(cantilever tip)}
    \lambda_n = n\pi\quad\text{(simply supported)}
    \cos\lambda_n\cosh\lambda_n = 1\quad\text{(fixed-fixed)}
    \phi_n(\xi) = \cosh(\lambda_n\xi)-\cos(\lambda_n\xi)-\sigma_n[\sinh(\lambda_n\xi)-\sin(\lambda_n\xi)]
    \sigma_n = \frac{\cosh\lambda_n+\cos\lambda_n}{\sinh\lambda_n+\sin\lambda_n}\quad\text{(cantilever)}
    \sigma_n = \frac{\cosh\lambda_n-\cos\lambda_n}{\sinh\lambda_n-\sin\lambda_n}\quad\text{(fixed-fixed)}
    \phi_n(\xi) = \sin(n\pi\xi)\quad\text{(simply supported)}

    ---Symbols---
    E: Young's modulus (Pa); ρ: mass density (kg/m³); A: cross-sectional
    area (m²); I: section second moment in the selected bending plane (m⁴);
    B: beam bending rigidity (N·m²); μ: mass per unit length (kg/m); L:
    free span (m); n: selected elastic mode number; λ: dimensionless
    frequency root βL; β: wave number (1/m); ξ: position x/L;
    φ: eigenfunction before normalization; σ: support-specific shape
    coefficient; f: frequency (Hz); cₑ: extensional wave speed (m/s);
    M: point tip mass (kg); r: tip mass / beam mass; m_total: combined mass (kg);
    F: cantilever characteristic function; primes: derivatives with respect
    to ξ; ε: scaled characteristic residual, F/[cosh(λ) max(1,r)] for the
    cantilever, sin(λ) for pinned ends, cos(λ)-1/cosh(λ) for fixed-fixed ends.

    ---References---
    Georgia Institute of Technology, AE Resources, Beam Bending Example,
    equations (14)-(16), cantilever eigenvalues and mode shapes.
    https://aeresources.gatech.edu/strdyn/Webpage/BeamBending/Examples/BeamBending_p2.php
    Bower, A. F., Applied Mechanics of Solids, section 10.4.1, free vibration
    of a straight beam without axial force (pinned and cantilever cases).
    https://solidmechanics.org/Text/Chapter10_4/Chapter10_4.html
    Sauer, V. T. K. (2014), Nanophotonic detection of nanomechanical structures
    for use toward mass sensing applications, University of Alberta,
    section 2.2.1, equations (2.5)-(2.7), clamped-clamped frequency equation.
    https://sites.ualberta.ca/~freemanm/theses/Vince_thesis.pdf
    NACA TN3459 (1955), Beams With a Mass at the Tip, p. 17, equations
    (13)-(14), exact cantilever point-mass frequency relation and mode shape.
    https://ntrs.nasa.gov/citations/19930084187
    """
    if support_type not in BEAM_ROOTS:
        raise ValueError("Support must be cantilever, simply_supported, or fixed_fixed.")
    if section_type not in ("rectangular", "circular_solid", "circular_hollow", "box"):
        raise ValueError("Section must be rectangular, circular_solid, circular_hollow, or box.")
    mode = _mode_number(mode_number, "Beam mode", 1)
    if mode > 5:
        raise ValueError("Beam mode must be an integer from 1 through 5.")
    e_gpa, rho, nu, material_label = _material_properties(
        material, custom_e_gpa, custom_rho_kg_m3, custom_nu
    )
    effective_tip_mass = 0.0
    if support_type == "cantilever":
        effective_tip_mass = _finite_number(tip_mass_kg, "Tip mass")
        if effective_tip_mass < 0:
            raise ValueError("Tip mass must be nonnegative.")
    span_mm = _finite_number(length_mm, "Beam span", positive=True)
    geometry = {
        "length_mm": span_mm, "width_mm": 0.0, "depth_mm": 0.0,
        "outer_diameter_mm": 0.0, "wall_thickness_mm": 0.0,
    }
    if section_type in ("rectangular", "box"):
        if bending_axis not in ("depth", "width"):
            raise ValueError("Bending direction must be depth or width.")
        b = _finite_number(width_mm, "Section width", positive=True)
        h = _finite_number(depth_mm, "Section depth", positive=True)
        geometry.update(width_mm=b, depth_mm=h)
        if bending_axis == "width":
            b, h = h, b
        dimensions = {"width": b / 1000, "depth": h / 1000}
        bending_size_mm = h
    else:
        d = _finite_number(outer_diameter_mm, "Section diameter", positive=True)
        geometry["outer_diameter_mm"] = d
        dimensions = {"diameter": d / 1000, "outer_diameter": d / 1000}
        bending_size_mm = d
        bending_axis = "depth"  # Circular sections are rotationally symmetric.
    if section_type in ("box", "circular_hollow"):
        wall = _finite_number(wall_thickness_mm, "Section wall thickness", positive=True)
        geometry["wall_thickness_mm"] = wall
        dimensions["wall_thickness"] = wall / 1000
        if section_type == "circular_hollow":
            if 2 * wall >= d:
                raise ValueError("Tube wall thickness must leave a positive inner diameter.")
            dimensions["inner_diameter"] = (d - 2 * wall) / 1000
    span = span_mm / 1000
    if span <= 0 or any(value <= 0 for value in dimensions.values()):
        raise ValueError("Dimensions are outside the supported numeric range.")
    try:
        section = compute_section_properties(section_type, dimensions)
        area, inertia = section["area"], section["Ix"]
        e_pa = e_gpa * 1e9
        mass_per_length = rho * area
        beam_mass = mass_per_length * span
        mass_ratio = effective_tip_mass / beam_mass
        total_mass = beam_mass + effective_tip_mass
        if not math.isfinite(mass_ratio) or not math.isfinite(total_mass):
            raise ValueError("Tip mass produces results outside the supported numeric range.")
        rigidity = e_pa * inertia
        wave_speed = math.sqrt(e_pa / rho)
        scale = math.sqrt(rigidity / mass_per_length) / (2 * math.pi * span**2)
        roots = (
            _tip_mass_roots(mass_ratio) if support_type == "cantilever"
            else BEAM_ROOTS[support_type]
        )
        frequencies = [
            {"mode_number": i, "eigenvalue": root, "natural_frequency_hz": root**2 * scale}
            for i, root in enumerate(roots, 1)
        ]
        numbers = [area, inertia, mass_per_length, beam_mass, rigidity, wave_speed]
        numbers.extend(row["natural_frequency_hz"] for row in frequencies)
        if any(not math.isfinite(value) or value <= 0 for value in numbers):
            raise ValueError("Inputs produce results outside the supported numeric range.")
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError("Inputs produce results outside the supported numeric range.") from error
    selected = frequencies[mode - 1]
    root, frequency = selected["eigenvalue"], selected["natural_frequency_hz"]
    if support_type == "cantilever":
        root_residual = _tip_mass_characteristic(root, mass_ratio)
    elif support_type == "simply_supported":
        root_residual = math.sin(root)
    else:
        root_residual = math.cos(root) - 1 / math.cosh(root)
    x = [i / 200 for i in range(201)]
    shape = [
        _beam_mode_value(support_type, root, xi, mass_ratio=mass_ratio) for xi in x
    ]
    shape[0] = 0.0
    if support_type != "cantilever":
        shape[-1] = 0.0
    normalization = max(abs(value) for value in shape)
    if not math.isfinite(normalization) or normalization <= 0:
        raise ValueError("Mode shape is outside the supported numeric range.")
    displacement = [value / normalization for value in shape]
    support_label = {
        "cantilever": "Cantilever", "simply_supported": "Simply Supported",
        "fixed_fixed": "Fixed-Fixed",
    }[support_type]
    support_description = {
        "cantilever": (
            "Left end fixed; tip bending moment is zero and tip shear balances point-mass inertia."
            if effective_tip_mass else
            "Left end fixed; right end free of bending moment and shear."
        ),
        "simply_supported": "Both ends pinned: zero deflection and bending moment.",
        "fixed_fixed": "Both ends fixed: zero deflection and slope.",
    }[support_type]
    thickness_ratio = bending_size_mm / span_mm
    section_label = {
        "rectangular": "Rectangular bar", "circular_solid": "Round rod",
        "circular_hollow": "Round tube", "box": "Rectangular tube",
    }[section_type]
    return {
        "natural_frequency_hz": frequency,
        "section_area_m2": area,
        "second_moment_m4": inertia,
        "mass_per_length_kg_m": mass_per_length,
        "beam_mass_kg": beam_mass,
        "tip_mass_kg": effective_tip_mass,
        "tip_mass_ratio": mass_ratio,
        "total_mass_kg": total_mass,
        "bending_rigidity_n_m2": rigidity,
        "eigenvalue": root,
        "eigenvalue_residual": root_residual,
        "mode_frequencies": frequencies,
        "diagram_data": {
            "kind": "beam", "available": True, "geometry": geometry,
            "support_type": support_type, "section_type": section_type,
            "bending_axis": bending_axis, "mode_label": f"Bending mode {mode}",
            "tip_mass_kg": effective_tip_mass,
            "x": x, "displacement": displacement,
        },
        "wave_velocity_m_s": wave_speed,
        "elastic_modulus_gpa": e_gpa, "density_kg_m3": rho, "poisson_ratio": nu,
        "thickness_ratio": thickness_ratio,
        "stiffness_label": "Beam bending rigidity EI",
        "material_display": material_label,
        "geometry_display": f"{support_label} Beam, {section_label}, Mode {mode}",
        "model_assumptions": [
            support_description,
            "Straight uniform beam; homogeneous isotropic material; small deflections.",
            "Euler-Bernoulli bending; no axial load, shear deformation, or rotary inertia.",
            "Tip mass acts at the centerline without rotational inertia, eccentricity, or axial gravity loading.",
        ],
        "applicability_notes": [
            f"Section size along deflection / span = {thickness_ratio:.4g}. "
            "Slender-beam theory requires both section dimensions small relative "
            "to span and bending wavelength.",
            "These are bending modes in the selected plane, not a complete structure's spectrum.",
            "Distributed attachments, elastic supports, joints and axial stress can shift the frequencies.",
            "Normalized mode amplitude is arbitrary; forcing and damping set real response amplitude.",
            *MATERIALS.get(material, {}).get("notes", []),
        ],
        "subst_natural_frequency_hz": (
            f"f_{{{mode}}} = \\frac{{({_latex_number(root)})^2}}"
            f"{{2\\pi({_latex_number(span)})^2}}\\sqrt{{"
            f"\\frac{{({_latex_number(e_pa)})({_latex_number(inertia)})}}"
            f"{{({_latex_number(rho)})({_latex_number(area)})}}}}"
            f" = {_latex_number(frequency)}\\;\\mathrm{{Hz}}"
        ),
        "subst_bending_rigidity_n_m2": (
            f"EI = ({_latex_number(e_pa)})({_latex_number(inertia)})"
            f" = {_latex_number(rigidity)}\\;\\mathrm{{N\\,m^2}}"
        ),
        "subst_wave_velocity_m_s": (
            "c_e = \\sqrt{"
            f"\\frac{{{_latex_number(e_pa)}}}{{{_latex_number(rho)}}}"
            "}"
            f" = {_latex_number(wave_speed)}\\;\\mathrm{{m/s}}"
        ),
        "subst_mass_per_length_kg_m": (
            f"\\mu = ({_latex_number(rho)})({_latex_number(area)})"
            f" = {_latex_number(mass_per_length)}\\;\\mathrm{{kg/m}}"
        ),
        "subst_tip_mass_ratio": (
            f"r = \\frac{{{_latex_number(effective_tip_mass)}}}"
            f"{{{_latex_number(beam_mass)}}} = {_latex_number(mass_ratio)},\\quad "
            f"m_{{\\mathrm{{total}}}} = {_latex_number(beam_mass)}"
            f"+{_latex_number(effective_tip_mass)} = {_latex_number(total_mass)}\\;\\mathrm{{kg}}"
        ),
        "subst_eigenvalue": (
            f"r = {_latex_number(mass_ratio)},\\quad "
            f"\\lambda_{{{mode}}} = {_latex_number(root)},\\quad "
            f"\\varepsilon = {_latex_number(root_residual)}"
        ),
    }
