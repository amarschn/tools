"""
Fracture mechanics and fatigue crack growth for fiber-reinforced polymer rotors.

Combines static fracture assessment (K_I vs K_IC) with Paris-law fatigue
crack growth integration for rotating composite components under centrifugal
loading.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


def _validate_positive(name: str, value: float) -> None:
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0. Got {value}.")


def _linspace(start: float, end: float, points: int) -> List[float]:
    if points < 2:
        raise ValueError("points must be >= 2.")
    if end <= start:
        return [start] * points
    step = (end - start) / (points - 1)
    return [start + i * step for i in range(points)]


# ---------------------------------------------------------------------------
# Material database
# ---------------------------------------------------------------------------

FRACTURE_MATERIALS: Dict[str, Dict[str, Any]] = {
    "cfrp_hoop_wound": {
        "display_name": "Carbon Fiber / Epoxy (Hoop-wound)",
        "K_IC": 35.0,
        "paris_C": 1e-10,
        "paris_m": 3.5,
        "density": 1600.0,
        "E_gpa": 140.0,
        "sigma_uts": 1500.0,
    },
    "gfrp_epoxy": {
        "display_name": "Glass Fiber / Epoxy",
        "K_IC": 20.0,
        "paris_C": 5e-9,
        "paris_m": 4.0,
        "density": 2000.0,
        "E_gpa": 40.0,
        "sigma_uts": 800.0,
    },
    "aramid_epoxy": {
        "display_name": "Aramid / Epoxy (Kevlar)",
        "K_IC": 25.0,
        "paris_C": 3e-9,
        "paris_m": 3.8,
        "density": 1380.0,
        "E_gpa": 75.0,
        "sigma_uts": 1100.0,
    },
    "pa6_gf30": {
        "display_name": "30% Glass-filled Nylon (PA6-GF30)",
        "K_IC": 7.0,
        "paris_C": 5e-8,
        "paris_m": 5.0,
        "density": 1360.0,
        "E_gpa": 9.5,
        "sigma_uts": 180.0,
    },
    "peek_cf30": {
        "display_name": "30% Carbon-filled PEEK (PEEK-CF30)",
        "K_IC": 6.5,
        "paris_C": 2e-9,
        "paris_m": 4.0,
        "density": 1410.0,
        "E_gpa": 26.0,
        "sigma_uts": 212.0,
    },
    "generic_polymer": {
        "display_name": "Generic Isotropic Polymer",
        "K_IC": 3.0,
        "paris_C": 1e-7,
        "paris_m": 5.5,
        "density": 1200.0,
        "E_gpa": 3.0,
        "sigma_uts": 60.0,
    },
}


def get_fracture_material_presets() -> Dict[str, Dict[str, Any]]:
    """Return the full material preset dictionary for frontend consumption."""
    return FRACTURE_MATERIALS


# ---------------------------------------------------------------------------
# Centrifugal stress (self-contained, mirrors rotor_stress.py)
# ---------------------------------------------------------------------------

def _centrifugal_stress_at_radius(
    geometry_type: str,
    ri_m: float,
    ro_m: float,
    r_m: float,
    density: float,
    poisson_ratio: float,
    omega: float,
) -> Tuple[float, float]:
    """Return (sigma_hoop_Pa, sigma_radial_Pa) at radius r_m.

    Uses Shigley rotating-disk closed-form equations.  Duplicated from
    rotor_stress.py to keep Pyodide imports simple.
    """
    c = (3.0 + poisson_ratio) / 8.0 * density * omega ** 2
    d = (1.0 + 3.0 * poisson_ratio) / 8.0 * density * omega ** 2

    geom = geometry_type.strip().lower()
    if geom == "thin_ring":
        rm = 0.5 * (ri_m + ro_m)
        return (density * omega ** 2 * rm ** 2, 0.0)

    r2 = r_m ** 2
    if geom == "solid_disk":
        sigma_r = c * (ro_m ** 2 - r2)
        sigma_t = c * ro_m ** 2 - d * r2
    else:  # annular_disk
        ri2 = ri_m ** 2
        ro2 = ro_m ** 2
        if r2 == 0.0:
            r2 = 1e-30  # avoid division by zero at center
        sigma_r = c * (ri2 + ro2 - (ri2 * ro2) / r2 - r2)
        sigma_t = c * (ri2 + ro2 + (ri2 * ro2) / r2) - d * r2

    return (sigma_t, sigma_r)


# ---------------------------------------------------------------------------
# Geometry factors
# ---------------------------------------------------------------------------

def _geometry_factor_Y(crack_type: str, a: float, W: float, aspect_ratio: float = 1.0) -> float:
    """Dimensionless geometry correction factor Y for K_I = Y * sigma * sqrt(pi*a).

    Parameters
    ----------
    crack_type : str
        One of 'through', 'edge', 'surface', 'embedded', 'elliptical_surface',
        'corner', or 'double_edge'.
    a : float
        Crack half-length (or depth for edge crack).
    W : float
        Ligament width (specimen/component width for edge/through cracks).
    aspect_ratio : float
        Crack aspect ratio a/c (depth / half-surface-length). Only used by
        'elliptical_surface' and 'corner' types. Default 1.0.

    Returns
    -------
    float
        Geometry factor Y.
    """
    ct = crack_type.strip().lower()
    ratio = a / W if W > 0 else 0.0

    if ct == "through":
        # Feddersen / Tada: Y = sqrt(sec(pi*a/(2W)))
        arg = math.pi * ratio / 2.0
        if arg >= math.pi / 2.0:
            return float("inf")
        return math.sqrt(1.0 / math.cos(arg))

    if ct == "edge":
        # Tada 4-term polynomial for single-edge notch
        r = ratio
        return (1.12
                - 0.231 * r
                + 10.55 * r ** 2
                - 21.72 * r ** 3
                + 30.39 * r ** 4)

    if ct == "surface":
        # Newman-Raju simplified for semicircular surface crack (a/c=1)
        return 0.728

    if ct == "embedded":
        # Penny-shaped (embedded) crack
        return 2.0 / math.pi

    if ct == "elliptical_surface":
        # Newman-Raju parametric (NASA TM-85793) for semi-elliptical surface crack
        ac = max(aspect_ratio, 0.01)
        # Shape factor Q
        if ac <= 1.0:
            Q = 1.0 + 1.464 * ac ** 1.65
        else:
            Q = 1.0 + 1.464 * (1.0 / ac) ** 1.65
        # M-factors for deepest point of surface crack
        M1 = 1.13 - 0.09 * ac
        M2 = -0.54 + 0.89 / (0.2 + ac)
        M3 = 0.5 - 1.0 / (0.65 + ac) + 14.0 * (1.0 - ac) ** 24
        # Front-face correction
        aW = ratio
        f_w = math.sqrt(1.0 / math.cos(math.sqrt(aW) * math.pi / 2.0)) if aW < 0.95 else 5.0
        # Parametric stress intensity
        F = (M1 + M2 * aW ** 2 + M3 * aW ** 4) * f_w
        return F / math.sqrt(Q)

    if ct == "corner":
        # Quarter-elliptical corner crack: Newman-Raju surface crack with
        # corner free-surface correction factor
        ac = max(aspect_ratio, 0.01)
        if ac <= 1.0:
            Q = 1.0 + 1.464 * ac ** 1.65
        else:
            Q = 1.0 + 1.464 * (1.0 / ac) ** 1.65
        M1 = 1.13 - 0.09 * ac
        M2 = -0.54 + 0.89 / (0.2 + ac)
        M3 = 0.5 - 1.0 / (0.65 + ac) + 14.0 * (1.0 - ac) ** 24
        aW = ratio
        f_w = math.sqrt(1.0 / math.cos(math.sqrt(aW) * math.pi / 2.0)) if aW < 0.95 else 5.0
        F_surface = (M1 + M2 * aW ** 2 + M3 * aW ** 4) * f_w
        # Corner correction: additional free-surface factor (~1.1-1.2)
        corner_correction = 1.1 + 0.1 * aW
        return F_surface * corner_correction / math.sqrt(Q)

    if ct == "double_edge":
        # Tada/Isida symmetric double-edge notch polynomial
        r = ratio
        return (1.122
                - 0.561 * r
                - 0.205 * r ** 2
                + 0.471 * r ** 3
                - 0.190 * r ** 4)

    raise ValueError(f"Unknown crack_type: {crack_type}")


# ---------------------------------------------------------------------------
# Stress intensity factor
# ---------------------------------------------------------------------------

def _stress_intensity_factor(sigma: float, a: float, Y: float) -> float:
    """K_I = Y * sigma * sqrt(pi * a), with a in metres and sigma in Pa.

    Returns K_I in Pa*sqrt(m).
    """
    if a <= 0.0:
        return 0.0
    return Y * sigma * math.sqrt(math.pi * a)


# ---------------------------------------------------------------------------
# Critical crack size (bisection)
# ---------------------------------------------------------------------------

def _critical_crack_size(
    sigma: float,
    K_IC: float,
    crack_type: str,
    W: float,
    aspect_ratio: float = 1.0,
    a_min: float = 1e-8,
    a_max_factor: float = 0.95,
    tol: float = 1e-9,
    max_iter: int = 200,
) -> Tuple[float, bool]:
    """Find a_cr such that K_I(a_cr) = K_IC via bisection.

    Parameters use SI units: sigma in Pa, K_IC in Pa*sqrt(m), W in metres.

    Returns
    -------
    a_cr : float
        Critical crack size in metres.
    critical_reached : bool
        True if K_IC is actually reached within the ligament. False if K never
        reaches K_IC (returned a_cr is the upper search bound).
    """
    ct = crack_type.strip().lower()
    # Cap a_max_factor for edge and double_edge cracks (polynomial validity)
    if ct in ("edge", "double_edge"):
        a_max_factor = min(a_max_factor, 0.7)

    a_lo = a_min
    a_hi = a_max_factor * W

    # Check if K_I at a_lo already exceeds K_IC
    Y_lo = _geometry_factor_Y(crack_type, a_lo, W, aspect_ratio)
    if _stress_intensity_factor(sigma, a_lo, Y_lo) >= K_IC:
        return a_lo, True

    # Check if K_IC is never reached within ligament
    Y_hi = _geometry_factor_Y(crack_type, a_hi, W, aspect_ratio)
    K_hi = _stress_intensity_factor(sigma, a_hi, Y_hi)
    if K_hi < K_IC:
        return a_hi, False  # K never reaches K_IC

    for _ in range(max_iter):
        a_mid = 0.5 * (a_lo + a_hi)
        Y_mid = _geometry_factor_Y(crack_type, a_mid, W, aspect_ratio)
        K_mid = _stress_intensity_factor(sigma, a_mid, Y_mid)

        if abs(K_mid - K_IC) / K_IC < tol:
            return a_mid, True

        if K_mid < K_IC:
            a_lo = a_mid
        else:
            a_hi = a_mid

    return 0.5 * (a_lo + a_hi), True


# ---------------------------------------------------------------------------
# Paris-law crack growth integration
# ---------------------------------------------------------------------------

def _paris_law_integration(
    sigma_max: float,
    stress_ratio_R: float,
    a_0: float,
    a_cr: float,
    crack_type: str,
    W: float,
    C: float,
    m: float,
    aspect_ratio: float = 1.0,
    max_steps: int = 5000,
) -> Tuple[List[float], List[float]]:
    """Integrate da/dN = C * (DeltaK)^m from a_0 to a_cr.

    Uses adaptive forward-Euler with step-size control.

    Parameters (SI units):
        sigma_max : max cyclic stress in Pa
        stress_ratio_R : min/max stress ratio
        a_0, a_cr : initial and critical crack sizes in metres
        C, m : Paris-law constants (da/dN in m/cycle, DeltaK in Pa*sqrt(m))
        aspect_ratio : crack aspect ratio a/c (only used by elliptical_surface/corner)

    Returns
    -------
    cycles : list of float
        Cumulative cycle counts.
    crack_sizes : list of float
        Crack sizes in metres corresponding to each cycle count.
    """
    delta_sigma = sigma_max * (1.0 - stress_ratio_R)
    if delta_sigma <= 0.0:
        return [0.0], [a_0]

    a = a_0
    N = 0.0
    cycles = [0.0]
    crack_sizes = [a_0]

    for _ in range(max_steps):
        if a >= a_cr:
            break

        Y = _geometry_factor_Y(crack_type, a, W, aspect_ratio)
        delta_K = Y * delta_sigma * math.sqrt(math.pi * a)

        if delta_K <= 0.0:
            break

        da_dN = C * delta_K ** m
        if da_dN <= 0.0:
            break

        # Adaptive step: limit crack growth to 1% of current size or 2% of remaining
        da_target = min(0.01 * a, 0.02 * (a_cr - a))
        da_target = max(da_target, 1e-12)  # floor
        dN = da_target / da_dN

        a += da_target
        N += dN

        if a > a_cr:
            a = a_cr

        cycles.append(N)
        crack_sizes.append(a)

    return cycles, crack_sizes


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

def analyze_fracture_and_crack_growth(
    geometry_type: str,
    inner_radius_mm: float,
    outer_radius_mm: float,
    speed_rpm: float,
    crack_location_radius_mm: float,
    initial_crack_size_mm: float,
    crack_type: str = "edge",
    crack_orientation: str = "circumferential",
    material_preset: str = "pa6_gf30",
    fracture_toughness_mpa_sqrt_m: float = 7.0,
    paris_C: float = 5e-8,
    paris_m: float = 5.0,
    density_kg_m3: float = 1360.0,
    poisson_ratio: float = 0.35,
    tensile_strength_mpa: float = 180.0,
    stress_ratio_R: float = 0.0,
    design_life_cycles: float = 1e5,
    required_fracture_sf: float = 1.5,
    thickness_mm: float = 10.0,
    crack_aspect_ratio: float = 1.0,
) -> Dict[str, Any]:
    r"""
    Assess fracture risk and fatigue crack growth in a rotating composite component.

    Combines linear-elastic fracture mechanics (LEFM) with Paris-law fatigue
    crack growth integration for centrifugally loaded disks and rings.

    ---Parameters---
    geometry_type : str
        Rotor geometry: `solid_disk`, `annular_disk`, or `thin_ring`.
    inner_radius_mm : float
        Inner radius in mm.  Ignored for `solid_disk`.
    outer_radius_mm : float
        Outer radius in mm.
    speed_rpm : float
        Rotational speed in rev/min.
    crack_location_radius_mm : float
        Radial position of the crack in mm.
    initial_crack_size_mm : float
        Initial crack half-length (or depth) in mm.
    crack_type : str
        Crack geometry: `through`, `edge`, `surface`, `embedded`,
        `elliptical_surface`, `corner`, or `double_edge`.
    crack_orientation : str
        `circumferential` (crack opens under hoop stress) or
        `radial` (crack opens under radial stress).
    material_preset : str
        Key from the material database, or `custom` for user-supplied values.
    fracture_toughness_mpa_sqrt_m : float
        Plane-strain fracture toughness \(K_{IC}\) in MPa\(\sqrt{\text{m}}\).
    paris_C : float
        Paris-law coefficient \(C\) (m/cycle units, ΔK in MPa√m).
    paris_m : float
        Paris-law exponent \(m\).
    density_kg_m3 : float
        Material density in kg/m³.
    poisson_ratio : float
        Poisson's ratio.
    tensile_strength_mpa : float
        Ultimate tensile strength in MPa.
    stress_ratio_R : float
        Stress ratio \(R = \sigma_{min}/\sigma_{max}\), 0 for zero-to-max cycling.
    design_life_cycles : float
        Target design life in load cycles.
    required_fracture_sf : float
        Required minimum fracture safety factor \(K_{IC}/K_I\).
    thickness_mm : float
        Axial thickness of the component in mm.
    crack_aspect_ratio : float
        Crack depth-to-half-surface-length ratio (a/c). Only used by
        `elliptical_surface` and `corner` crack types. Default 1.0.

    ---Returns---
    K_I_mpa_sqrt_m : float
        Stress intensity factor at the initial crack size, in MPa√m.
    K_IC_mpa_sqrt_m : float
        Fracture toughness used in the analysis, in MPa√m.
    fracture_safety_factor : float
        \(SF = K_{IC} / K_I\).
    critical_crack_size_mm : float
        Crack size at which \(K_I = K_{IC}\), in mm.
    cycles_to_failure : float
        Predicted cycles to grow from \(a_0\) to \(a_{cr}\).
    life_fraction_used : float
        Ratio of design life to cycles-to-failure.
    inspection_interval_cycles : float
        Recommended inspection interval (cycles to failure ÷ 3).
    crack_growth_rate_mm_per_cycle : float
        Initial crack growth rate da/dN in mm/cycle.
    applied_hoop_stress_mpa : float
        Centrifugal hoop stress at the crack location, in MPa.
    applied_radial_stress_mpa : float
        Centrifugal radial stress at the crack location, in MPa.
    geometry_factor_Y : float
        Dimensionless geometry correction factor.
    ligament_width_mm : float
        Effective ligament width used for geometry factor, in mm.
    material_preset : str
        Material preset key used.
    material_display_name : str
        Human-readable material name.
    material_notes : str
        Brief notes about the material assumptions.
    status : str
        `acceptable`, `marginal`, or `unacceptable`.
    recommendations : list
        Actionable engineering recommendations.
    crack_growth_curve : dict
        Plot data: `cycles` and `crack_size_mm` arrays.
    K_vs_a_curve : dict
        Plot data: `crack_size_mm`, `K_I_mpa_sqrt_m`, and `K_IC_line` arrays.
    subst_K_I_mpa_sqrt_m : str
        Substituted LaTeX equation for K_I.
    subst_critical_crack_size_mm : str
        Substituted LaTeX equation for critical crack size.
    subst_fracture_safety_factor : str
        Substituted LaTeX equation for fracture safety factor.
    subst_cycles_to_failure : str
        Substituted LaTeX equation for cycles to failure.

    ---LaTeX---
    K_I = Y \sigma \sqrt{\pi a}
    a_{cr}: K_I(a_{cr}) = K_{IC}
    SF = \frac{K_{IC}}{K_I}
    \frac{da}{dN} = C (\Delta K)^m
    \Delta K = Y \Delta\sigma \sqrt{\pi a}

    References:
    - T.L. Anderson, *Fracture Mechanics: Fundamentals and Applications*, 4th ed.
    - Tada, Paris & Irwin, *The Stress Analysis of Cracks Handbook*, 3rd ed.
    - Paris & Erdogan, "A Critical Analysis of Crack Propagation Laws", 1963.
    """
    # ---- Resolve material preset ----
    mat = FRACTURE_MATERIALS.get(material_preset)
    if mat is not None:
        fracture_toughness_mpa_sqrt_m = mat["K_IC"]
        paris_C = mat["paris_C"]
        paris_m = mat["paris_m"]
        density_kg_m3 = mat["density"]
        tensile_strength_mpa = mat["sigma_uts"]
        material_display_name = mat["display_name"]
        material_notes = f"Properties from {mat['display_name']} preset."
    elif material_preset == "custom":
        material_display_name = "Custom Material"
        material_notes = "User-supplied material properties."
    else:
        raise ValueError(f"Unknown material_preset: '{material_preset}'.")

    # ---- Validate ----
    geom = geometry_type.strip().lower()
    if geom not in {"solid_disk", "annular_disk", "thin_ring"}:
        raise ValueError("geometry_type must be solid_disk, annular_disk, or thin_ring.")

    _validate_positive("outer_radius_mm", outer_radius_mm)
    _validate_positive("speed_rpm", speed_rpm)
    _validate_positive("initial_crack_size_mm", initial_crack_size_mm)
    _validate_positive("thickness_mm", thickness_mm)
    _validate_positive("fracture_toughness_mpa_sqrt_m", fracture_toughness_mpa_sqrt_m)
    _validate_positive("density_kg_m3", density_kg_m3)
    _validate_positive("tensile_strength_mpa", tensile_strength_mpa)

    if paris_C <= 0.0:
        raise ValueError("paris_C must be > 0.")
    if paris_m <= 0.0:
        raise ValueError("paris_m must be > 0.")
    if stress_ratio_R < 0.0 or stress_ratio_R >= 1.0:
        raise ValueError("stress_ratio_R must be in [0, 1).")
    if poisson_ratio < 0.0 or poisson_ratio >= 0.5:
        raise ValueError("poisson_ratio must be in [0, 0.5).")

    crack_type_clean = crack_type.strip().lower()
    crack_orient = crack_orientation.strip().lower()

    if geom == "solid_disk":
        ri_m = 0.0
    else:
        _validate_positive("inner_radius_mm", inner_radius_mm)
        ri_m = inner_radius_mm / 1000.0

    ro_m = outer_radius_mm / 1000.0
    if ro_m <= ri_m:
        raise ValueError("outer_radius_mm must be > inner_radius_mm.")

    r_crack_m = crack_location_radius_mm / 1000.0
    a_0_m = initial_crack_size_mm / 1000.0
    thickness_m = thickness_mm / 1000.0
    omega = 2.0 * math.pi * speed_rpm / 60.0

    # ---- Validate crack location within material bounds (Fix #3) ----
    if geom != "solid_disk" and (r_crack_m < ri_m or r_crack_m > ro_m):
        raise ValueError(
            f"Crack location ({crack_location_radius_mm} mm) must be between "
            f"inner radius ({ri_m * 1000:.1f} mm) and outer radius ({ro_m * 1000:.1f} mm)."
        )
    if geom == "solid_disk" and r_crack_m > ro_m:
        raise ValueError(
            f"Crack location ({crack_location_radius_mm} mm) must be within "
            f"outer radius ({ro_m * 1000:.1f} mm)."
        )

    # ---- Convert Paris C from MPa√m convention to Pa√m (SI) ----
    # Literature and material presets specify C for ΔK in MPa√m.
    # All internal calculations use Pa√m, so: C_si = C_mpa * (1e-6)^m
    paris_C_si = paris_C * (1e-6) ** paris_m

    # ---- Centrifugal stress at crack location ----
    sigma_hoop_pa, sigma_radial_pa = _centrifugal_stress_at_radius(
        geom, ri_m, ro_m, r_crack_m, density_kg_m3, poisson_ratio, omega
    )

    # Select driving stress based on crack orientation (Fix #1)
    if crack_orient == "radial":
        sigma_driving_pa = abs(sigma_hoop_pa)  # radial crack opens under hoop stress
    else:
        # circumferential crack opens under radial stress
        sigma_driving_pa = abs(sigma_radial_pa)

    sigma_hoop_mpa = sigma_hoop_pa / 1e6
    sigma_radial_mpa = sigma_radial_pa / 1e6

    # ---- Ligament width ----
    if crack_orient == "radial":
        W_m = thickness_m
    else:
        W_m = ro_m - ri_m  # circumferential: radial width

    ligament_width_mm = W_m * 1000.0

    # ---- K_I at initial crack size ----
    K_IC_pa = fracture_toughness_mpa_sqrt_m * 1e6  # Pa*sqrt(m)
    Y_0 = _geometry_factor_Y(crack_type_clean, a_0_m, W_m, crack_aspect_ratio)
    K_I_pa = _stress_intensity_factor(sigma_driving_pa, a_0_m, Y_0)
    K_I_mpa = K_I_pa / 1e6

    # ---- Fracture safety factor ----
    fracture_sf = fracture_toughness_mpa_sqrt_m / K_I_mpa if K_I_mpa > 0 else float("inf")

    # ---- Critical crack size (Fix #4: returns tuple) ----
    a_cr_m, critical_crack_reached = _critical_crack_size(
        sigma_driving_pa, K_IC_pa, crack_type_clean, W_m, crack_aspect_ratio,
    )
    a_cr_mm = a_cr_m * 1000.0

    # ---- Paris-law integration ----
    if not critical_crack_reached:
        # K never reaches K_IC within the ligament — no true critical crack size.
        # Life is effectively infinite; report inf cycles and zero life usage.
        cycles_list = [0.0]
        a_list = [a_0_m]
        cycles_to_failure = float("inf")
    elif a_0_m >= a_cr_m:
        # Initial crack already at or above critical — immediate failure
        cycles_list = [0.0, 0.0]
        a_list = [a_0_m, a_0_m]
        cycles_to_failure = 0.0
    else:
        cycles_list, a_list = _paris_law_integration(
            sigma_driving_pa, stress_ratio_R, a_0_m, a_cr_m,
            crack_type_clean, W_m, paris_C_si, paris_m, crack_aspect_ratio,
        )
        cycles_to_failure = cycles_list[-1] if len(cycles_list) > 1 else float("inf")

    life_fraction_used = design_life_cycles / cycles_to_failure if cycles_to_failure > 0 and math.isfinite(cycles_to_failure) else (float("inf") if cycles_to_failure == 0 else 0.0)
    inspection_interval = cycles_to_failure / 3.0 if cycles_to_failure > 0 and math.isfinite(cycles_to_failure) else 0.0

    # Initial crack growth rate
    delta_sigma = sigma_driving_pa * (1.0 - stress_ratio_R)
    delta_K_0 = Y_0 * delta_sigma * math.sqrt(math.pi * a_0_m) if a_0_m > 0 else 0.0
    da_dN_0 = paris_C_si * delta_K_0 ** paris_m if delta_K_0 > 0 else 0.0
    da_dN_mm = da_dN_0 * 1000.0  # m/cycle -> mm/cycle

    # ---- K vs a plot data ----
    n_plot = 50
    a_plot_max = min(a_cr_m * 1.2, 0.95 * W_m)
    a_plot_list = _linspace(max(a_0_m * 0.5, 1e-6), a_plot_max, n_plot)
    K_plot = []
    for ap in a_plot_list:
        Yp = _geometry_factor_Y(crack_type_clean, ap, W_m, crack_aspect_ratio)
        Kp = _stress_intensity_factor(sigma_driving_pa, ap, Yp) / 1e6
        K_plot.append(Kp)

    # ---- Status and recommendations ----
    recommendations: List[str] = []

    if fracture_sf >= required_fracture_sf:
        status = "acceptable"
    elif fracture_sf >= 1.0:
        status = "marginal"
    else:
        status = "unacceptable"

    if status == "unacceptable":
        recommendations.append(
            "Crack size exceeds critical threshold — immediate action required. "
            "Reduce operating speed, repair the defect, or replace the component."
        )
    elif status == "marginal":
        recommendations.append(
            "Safety factor is below the required target. Consider reducing speed, "
            "using a tougher material, or increasing inspection frequency."
        )

    if life_fraction_used > 1.0:
        recommendations.append(
            "Design life exceeds predicted crack growth life — increase inspection "
            "frequency or reduce design life target."
        )

    if da_dN_mm > 0.01:
        recommendations.append(
            "High initial crack growth rate detected. Prioritize NDT inspection "
            "and consider damage-tolerant design review."
        )

    if not critical_crack_reached:
        recommendations.append(
            "K_I never reaches K_IC within the available ligament. "
            "Fatigue crack growth life is effectively infinite for this geometry."
        )

    if not recommendations:
        recommendations.append(
            "Fracture margins meet the selected target. Validate with detailed "
            "fracture testing and periodic NDT inspection."
        )

    # ---- Substituted equations ----
    sigma_driving_mpa = sigma_driving_pa / 1e6

    subst_K_I = (
        f"K_I = Y \\sigma \\sqrt{{\\pi a}}"
        f" = {Y_0:.4f} \\times {sigma_driving_mpa:.2f}"
        f" \\times \\sqrt{{\\pi \\times {initial_crack_size_mm:.3f} \\times 10^{{-3}}}}"
        f" = {K_I_mpa:.3f}\\text{{ MPa}}\\sqrt{{\\text{{m}}}}"
    )

    subst_a_cr = (
        f"a_{{cr}}: K_I(a_{{cr}}) = K_{{IC}} = {fracture_toughness_mpa_sqrt_m:.1f}"
        f"\\text{{ MPa}}\\sqrt{{\\text{{m}}}}"
        f" \\Rightarrow a_{{cr}} = {a_cr_mm:.3f}\\text{{ mm}}"
    )

    subst_sf = (
        f"SF = \\frac{{K_{{IC}}}}{{K_I}}"
        f" = \\frac{{{fracture_toughness_mpa_sqrt_m:.2f}}}{{{K_I_mpa:.3f}}}"
        f" = {fracture_sf:.3f}"
    )

    def _fmt_cycles(n):
        """Format a cycle count for LaTeX display."""
        if math.isinf(n):
            return "\\infty"
        if n >= 1e6:
            exp = int(math.log10(n))
            coeff = n / 10 ** exp
            return f"{coeff:.2f} \\times 10^{{{exp}}}"
        return f"{n:.0f}"

    # Multi-step N_f derivation
    delta_sigma_mpa = sigma_driving_mpa * (1.0 - stress_ratio_R)
    delta_K_0_mpa = delta_K_0 / 1e6  # Pa√m -> MPa√m

    # Step 1: Stress range
    subst_nf_step_delta_sigma = (
        f"\\Delta\\sigma = \\sigma_{{max}}(1 - R)"
        f" = {sigma_driving_mpa:.2f} \\times (1 - {stress_ratio_R:.2f})"
        f" = {delta_sigma_mpa:.2f}\\text{{ MPa}}"
    )

    # Step 2: Initial ΔK
    subst_nf_step_delta_K = (
        f"\\Delta K_0 = Y \\cdot \\Delta\\sigma \\cdot \\sqrt{{\\pi a_0}}"
        f" = {Y_0:.4f} \\times {delta_sigma_mpa:.2f}"
        f" \\times \\sqrt{{\\pi \\times {initial_crack_size_mm:.3f}"
        f" \\times 10^{{-3}}}}"
        f" = {delta_K_0_mpa:.3f}\\text{{ MPa}}\\sqrt{{\\text{{m}}}}"
    )

    # Step 3: Initial growth rate
    # da/dN = C * (ΔK in MPa√m)^m gives m/cycle (C is in MPa√m convention)
    da_dN_from_mpa = paris_C * delta_K_0_mpa ** paris_m if delta_K_0_mpa > 0 else 0.0
    da_dN_display_mm = da_dN_from_mpa * 1000.0  # m/cycle -> mm/cycle
    subst_nf_step_dadN = (
        f"\\left.\\frac{{da}}{{dN}}\\right|_0 = C(\\Delta K_0)^m"
        f" = {paris_C:.2e} \\times {delta_K_0_mpa:.3f}^{{{paris_m:.1f}}}"
        f" = {da_dN_display_mm:.2e}\\text{{ mm/cycle}}"
    )

    # Step 4: Integration / result
    if math.isinf(cycles_to_failure):
        subst_nf_step_integral = (
            "N_f = \\infty \\text{ (crack does not grow)}"
        )
    else:
        subst_nf_step_integral = (
            f"N_f = \\int_{{a_0}}^{{a_{{cr}}}}"
            f" \\frac{{da}}{{C\\,[\\Delta K(a)]^m}}"
            f" = \\int_{{{initial_crack_size_mm:.2f}\\text{{ mm}}}}"
            f"^{{{a_cr_mm:.2f}\\text{{ mm}}}} \\cdots"
            f" = {_fmt_cycles(cycles_to_failure)}\\text{{ cycles}}"
        )

    # Keep a combined single-line version for compact display
    if math.isinf(cycles_to_failure):
        subst_N = "N_f = \\infty \\text{ (crack does not grow)}"
    else:
        subst_N = (
            f"\\frac{{da}}{{dN}} = C(\\Delta K)^m"
            f" = {paris_C:.2e} \\times (\\Delta K)^{{{paris_m:.1f}}}"
            f" \\Rightarrow N_f = {cycles_to_failure:.0f}\\text{{ cycles}}"
        )

    # Substituted life fraction equation
    if math.isinf(cycles_to_failure):
        subst_life = (
            f"\\text{{Life fraction}} = \\frac{{N_{{design}}}}{{N_f}}"
            f" = \\frac{{{_fmt_cycles(design_life_cycles)}}}{{\\infty}} = 0"
        )
    elif cycles_to_failure < 1.0:
        # N_f essentially zero — immediate failure
        subst_life = (
            f"\\text{{Life fraction}} = \\frac{{N_{{design}}}}{{N_f}}"
            f" = \\frac{{{_fmt_cycles(design_life_cycles)}}}{{\\approx 0}}"
            f" \\;\\rightarrow\\; \\text{{immediate failure}}"
        )
    else:
        subst_life = (
            f"\\text{{Life fraction}} = \\frac{{N_{{design}}}}{{N_f}}"
            f" = \\frac{{{_fmt_cycles(design_life_cycles)}}}{{{_fmt_cycles(cycles_to_failure)}}}"
            f" = {life_fraction_used:.3f}"
            f" \\;({life_fraction_used * 100:.1f}\\%)"
        )

    # Substituted hoop stress equation
    geom_lower = geom.strip().lower()
    if geom_lower == "thin_ring":
        subst_hoop = (
            f"\\sigma_\\theta = \\rho \\omega^2 r_m^2"
            f" = {density_kg_m3:.0f} \\times {omega:.2f}^2"
            f" \\times \\left(\\frac{{{ri_m * 1000:.1f} + {ro_m * 1000:.1f}}}{{2000}}\\right)^2"
            f" = {sigma_hoop_mpa:.2f}\\text{{ MPa}}"
        )
    elif geom_lower == "solid_disk":
        subst_hoop = (
            f"\\sigma_\\theta = \\frac{{3+\\nu}}{{8}} \\rho \\omega^2 r_o^2"
            f" - \\frac{{1+3\\nu}}{{8}} \\rho \\omega^2 r^2"
            f" = {sigma_hoop_mpa:.2f}\\text{{ MPa}}"
        )
    else:
        subst_hoop = (
            f"\\sigma_\\theta = \\frac{{3+\\nu}}{{8}} \\rho \\omega^2"
            f" \\left(r_i^2 + r_o^2 + \\frac{{r_i^2 r_o^2}}{{r^2}}\\right)"
            f" - \\frac{{1+3\\nu}}{{8}} \\rho \\omega^2 r^2"
            f" = {sigma_hoop_mpa:.2f}\\text{{ MPa}}"
        )

    return {
        # Primary fracture results
        "K_I_mpa_sqrt_m": K_I_mpa,
        "K_IC_mpa_sqrt_m": fracture_toughness_mpa_sqrt_m,
        "fracture_safety_factor": fracture_sf,
        "critical_crack_size_mm": a_cr_mm,
        "critical_crack_reached": critical_crack_reached,
        # Fatigue results
        "cycles_to_failure": cycles_to_failure,
        "life_fraction_used": life_fraction_used,
        "inspection_interval_cycles": inspection_interval,
        "crack_growth_rate_mm_per_cycle": da_dN_mm,
        # Stress
        "applied_hoop_stress_mpa": sigma_hoop_mpa,
        "applied_radial_stress_mpa": sigma_radial_mpa,
        "geometry_factor_Y": Y_0,
        "ligament_width_mm": ligament_width_mm,
        # Material
        "material_preset": material_preset,
        "material_display_name": material_display_name,
        "material_notes": material_notes,
        # Assessment
        "status": status,
        "recommendations": recommendations,
        # Plot data
        "crack_growth_curve": {
            "cycles": cycles_list,
            "crack_size_mm": [a * 1000.0 for a in a_list],
        },
        "K_vs_a_curve": {
            "crack_size_mm": [a * 1000.0 for a in a_plot_list],
            "K_I_mpa_sqrt_m": K_plot,
            "K_IC_line": [fracture_toughness_mpa_sqrt_m] * n_plot,
        },
        # Substituted equations
        "subst_K_I_mpa_sqrt_m": subst_K_I,
        "subst_critical_crack_size_mm": subst_a_cr,
        "subst_fracture_safety_factor": subst_sf,
        "subst_cycles_to_failure": subst_N,
        "subst_nf_step_delta_sigma": subst_nf_step_delta_sigma,
        "subst_nf_step_delta_K": subst_nf_step_delta_K,
        "subst_nf_step_dadN": subst_nf_step_dadN,
        "subst_nf_step_integral": subst_nf_step_integral,
        "subst_applied_hoop_stress": subst_hoop,
        "subst_life_fraction_used": subst_life,
    }
