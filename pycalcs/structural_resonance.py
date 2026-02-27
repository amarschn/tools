"""
Structural resonance calculators for flat plates and cylindrical rings.
These estimates are useful for eNVH (Electrified Noise, Vibration, and Harshness) 
to determine if electromagnetic excitation frequencies might excite structural modes 
in motor housings or inverter covers.
"""

from __future__ import annotations

import math
from typing import Dict, Any

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

def _validate_positive(value: float, label: str) -> float:
    if value <= 0.0:
        raise ValueError(f"{label} must be positive.")
    return value

def _validate_non_negative(value: float, label: str) -> float:
    if value < 0.0:
        raise ValueError(f"{label} cannot be negative.")
    return value

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
    """
    Estimate natural frequencies for simply-supported flat plates or cylindrical rings.
    
    For rectangular plates, computes the f_{m,n} bending mode frequency.
    For cylindrical rings (like motor stators), computes the circumferential inextensional 
    ovaling/bending modes (n>=2) or the fundamental radial breathing mode (n=0).

    ---Parameters---
    geometry_type : str
        Either "plate" (rectangular) or "cylinder" (ring).
    thickness_mm : float
        Material thickness (mm).
    length_mm : float
        Plate length (mm). Ignored for cylinder.
    width_mm : float
        Plate width (mm). Ignored for cylinder.
    diameter_mm : float
        Cylinder mean diameter (mm). Ignored for plate.
    mode_1 : int
        Mode number 'm' for plate (x-direction half-waves, m >= 1). Ignored for cylinder.
    mode_2 : int
        Mode number 'n' for plate (y-direction half-waves, n >= 1) or circumferential wave number for cylinder (n=0, 2, 3...).
    material : str
        Material preset ('steel', 'aluminum', 'cast_iron', 'titanium', or 'custom').
    custom_e_gpa : float
        Custom elastic modulus (GPa). Used only if material is 'custom'.
    custom_rho_kg_m3 : float
        Custom density (kg/m^3). Used only if material is 'custom'.
    custom_nu : float
        Custom Poisson's ratio. Used only if material is 'custom'.

    ---Returns---
    natural_frequency_hz : float
        Estimated natural frequency (Hz).
    flexural_rigidity_n_m : float
        Plate/Shell flexural rigidity D (N·m).
    wave_velocity_m_s : float
        Longitudinal wave velocity in the material (m/s).
    material_display : str
        Human-readable material name.
    geometry_display : str
        Description of the analyzed geometry and mode.
    subst_natural_frequency_hz : str
        Substituted equation for natural frequency (LaTeX).

    ---LaTeX---
    D = \\frac{E h^3}{12 (1 - \\nu^2)}
    f_{m,n} = \\frac{\\pi}{2} \\sqrt{\\frac{D}{\\rho h}} \\left( \\left(\\frac{m}{a}\\right)^2 + \\left(\\frac{n}{b}\\right)^2 \\right)
    f_{0} = \\frac{1}{2\\pi R} \\sqrt{\\frac{E}{\\rho}}
    f_{n} = \\frac{1}{2\\pi} \\sqrt{\\frac{E h^2}{12 \\rho R^4 (1 - \\nu^2)}} \\frac{n(n^2-1)}{\\sqrt{n^2+1}}
    """
    
    if material == "custom":
        e_gpa = _validate_positive(custom_e_gpa, "custom_e_gpa")
        rho = _validate_positive(custom_rho_kg_m3, "custom_rho_kg_m3")
        nu = _validate_non_negative(custom_nu, "custom_nu")
        if nu >= 0.5:
            raise ValueError("Poisson's ratio must be less than 0.5.")
        mat_display = "Custom Material"
    else:
        if material not in MATERIALS:
            raise ValueError(f"Unknown material: {material}")
        mat_props = MATERIALS[material]
        e_gpa = mat_props["elastic_modulus_gpa"]
        rho = mat_props["density_kg_m3"]
        nu = mat_props["poisson_ratio"]
        mat_display = mat_props["display"]

    e_pa = e_gpa * 1e9
    h_m = _validate_positive(thickness_mm, "thickness_mm") / 1000.0
    
    # Flexural rigidity D
    D = (e_pa * h_m**3) / (12.0 * (1.0 - nu**2))
    
    wave_vel = math.sqrt(e_pa / rho)

    if geometry_type == "plate":
        a_m = _validate_positive(length_mm, "length_mm") / 1000.0
        b_m = _validate_positive(width_mm, "width_mm") / 1000.0
        m = max(1, int(mode_1))
        n = max(1, int(mode_2))
        
        rho_h = rho * h_m
        term = (m / a_m)**2 + (n / b_m)**2
        freq = (math.pi / 2.0) * math.sqrt(D / rho_h) * term
        
        geom_display = f"Rectangular Plate, Mode ({m},{n})"
        
        subst_freq = (
            f"f_{{{m},{n}}} = \\frac{{\\pi}}{{2}} \\sqrt{{\\frac{{D}}{{\\rho h}}}} "
            f"\\left( \\left(\\frac{{{m}}}{{{a_m:.3f}}}\\right)^2 + \\left(\\frac{{{n}}}{{{b_m:.3f}}}\\right)^2 \\right)"
            f" = {freq:.1f}\\,\\text{{Hz}}"
        )

    elif geometry_type == "cylinder":
        R_m = (_validate_positive(diameter_mm, "diameter_mm") / 1000.0) / 2.0
        n = max(0, int(mode_2))
        if n == 1:
            raise ValueError("Mode n=1 is a rigid body translation, frequency is 0.")
        
        if n == 0:
            # Breathing mode
            freq = wave_vel / (2.0 * math.pi * R_m)
            geom_display = "Cylindrical Ring, Breathing Mode (n=0)"
            subst_freq = (
                f"f_0 = \\frac{{1}}{{2\\pi R}} \\sqrt{{\\frac{{E}}{{\\rho}}}} = "
                f"\\frac{{1}}{{2\\pi ({R_m:.4f})}} \\sqrt{{\\frac{{{e_pa:.2e}}}{{{rho:.1f}}}}} = {freq:.1f}\\,\\text{{Hz}}"
            )
        else:
            # Ovaling/bending modes
            coeff1 = 1.0 / (2.0 * math.pi)
            coeff2 = math.sqrt((e_pa * h_m**2) / (12.0 * rho * R_m**4 * (1.0 - nu**2)))
            coeff3 = (n * (n**2 - 1.0)) / math.sqrt(n**2 + 1.0)
            freq = coeff1 * coeff2 * coeff3
            geom_display = f"Cylindrical Ring, Inextensional Bending (n={n})"
            
            subst_freq = (
                f"f_{{{n}}} = \\frac{{1}}{{2\\pi}} \\sqrt{{\\frac{{E h^2}}{{12 \\rho R^4 (1 - \\nu^2)}}}} "
                f"\\frac{{{n}({n}^2-1)}}{{\\sqrt{{{n}^2+1}}}} = {freq:.1f}\\,\\text{{Hz}}"
            )
            
    else:
        raise ValueError("geometry_type must be 'plate' or 'cylinder'.")

    return {
        "natural_frequency_hz": freq,
        "flexural_rigidity_n_m": D,
        "wave_velocity_m_s": wave_vel,
        "material_display": mat_display,
        "geometry_display": geom_display,
        "subst_natural_frequency_hz": subst_freq,
    }
