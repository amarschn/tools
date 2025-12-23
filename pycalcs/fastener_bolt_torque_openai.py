"""Fastener torque calculations for bolt tightening."""

from __future__ import annotations

import math

N_PER_LBF = 4.4482216152605
MM_PER_IN = 25.4
MPA_PER_KSI = 6.894757293168
N_M_TO_LBF_FT = 0.7375621492772654


def calculate_bolt_torque_openai(
    thread_standard: str,
    nominal_diameter: float,
    thread_pitch: float,
    threads_per_inch: float,
    thread_angle_deg: float,
    bearing_diameter: float,
    mu_thread: float,
    mu_bearing: float,
    torque_model: str,
    nut_factor: float,
    preload_method: str,
    target_preload: float,
    percent_proof: float,
    proof_strength: float,
    tensile_stress_area: float,
) -> dict[str, float]:
    """
    Calculates tightening torque, clamp load, and proof utilization for a threaded fastener.

    The model combines thread geometry, friction coefficients, and proof strength to
    estimate tightening torque with either a detailed friction model or the classic
    nut-factor approximation. Inputs accept metric or unified thread standards; the
    tool reports both SI and inch-pound outputs. All calculations are performed in
    SI units after converting any inch-pound inputs.

    ---Parameters---
    thread_standard : str
        Thread standard and unit system. Use "metric" for ISO metric (mm, MPa, kN)
        or "unified" for inch-series (in, ksi, lbf).
    nominal_diameter : float
        Nominal fastener diameter d. Use mm for metric or inches for unified.
    thread_pitch : float
        Thread pitch p in mm (metric only). Ignored for unified threads.
    threads_per_inch : float
        Threads per inch n (unified only). Ignored for metric threads.
    thread_angle_deg : float
        Included thread angle in degrees (60 deg for ISO/Unified).
    bearing_diameter : float
        Effective bearing friction diameter D_b. Use mm or inches. Set to 0 to
        approximate as 1.5 * d.
    mu_thread : float
        Thread friction coefficient mu_t (dimensionless).
    mu_bearing : float
        Bearing friction coefficient mu_b (dimensionless).
    torque_model : str
        Torque model selection: "friction" or "nut_factor".
    nut_factor : float
        Nut factor K used when torque_model is "nut_factor".
    preload_method : str
        "percent_proof" to compute clamp load from proof, or "direct" for direct clamp load.
    target_preload : float
        Direct clamp load target. Use kN for metric or lbf for unified.
    percent_proof : float
        Percent of proof load when preload_method is "percent_proof" (0 to 100).
    proof_strength : float
        Proof strength S_p. Use MPa for metric or ksi for unified.
    tensile_stress_area : float
        Override tensile stress area A_t. Use mm^2 for metric or in^2 for unified. Set to 0 to auto-calc.

    ---Returns---
    clamp_load_n : float
        Target clamp load F in newtons.
    clamp_load_lbf : float
        Target clamp load F in pounds-force.
    proof_load_n : float
        Proof load F_p in newtons.
    proof_load_lbf : float
        Proof load F_p in pounds-force.
    proof_utilization_percent : float
        Clamp load as a percentage of proof load.
    tensile_stress_area_mm2 : float
        Tensile stress area A_t in square millimetres.
    tensile_stress_area_in2 : float
        Tensile stress area A_t in square inches.
    bolt_stress_mpa : float
        Bolt stress sigma in MPa.
    bolt_stress_ksi : float
        Bolt stress sigma in ksi.
    torque_total_nm : float
        Selected tightening torque in N*m.
    torque_total_lbf_ft : float
        Selected tightening torque in lbf*ft.
    torque_thread_nm : float
        Thread torque component in N*m.
    torque_bearing_nm : float
        Bearing torque component in N*m.
    torque_total_friction_nm : float
        Total torque from friction model in N*m.
    torque_total_nut_factor_nm : float
        Total torque from nut factor model in N*m.
    nut_factor_equiv : float
        Equivalent nut factor derived from friction model.
    lead_angle_deg : float
        Thread lead angle in degrees.

    ---LaTeX---
    A_t = \\frac{\\pi}{4} \\left(d - 0.9382 p\\right)^2
    A_t = \\frac{\\pi}{4} \\left(d - \\frac{0.9743}{n}\\right)^2
    F_p = A_t S_p
    F = k_p F_p
    \\lambda = \\arctan\\left(\\frac{p}{\\pi d_2}\\right)
    T_{\\text{thread}} = F \\frac{d_2}{2} \\frac{\\tan\\lambda + \\mu_t / \\cos\\alpha}{1 - (\\mu_t / \\cos\\alpha) \\tan\\lambda}
    T_{\\text{bearing}} = F \\mu_b \\frac{D_b}{2}
    T_{\\text{total}} = T_{\\text{thread}} + T_{\\text{bearing}}
    T = K F d
    K = \\frac{T_{\\text{total}}}{F d}
    \\sigma = \\frac{F}{A_t}

    ---Variables---
    A_t: Tensile stress area (mm^2)
    F: Clamp load (N)
    F_p: Proof load (N)
    k_p: Percent of proof load (0 to 1)
    S_p: Proof strength (MPa)
    d: Nominal diameter (mm)
    d_2: Pitch diameter (mm)
    p: Thread pitch (mm)
    n: Threads per inch (1/in)
    D_b: Bearing friction diameter (mm)
    \\mu_t: Thread friction coefficient (-)
    \\mu_b: Bearing friction coefficient (-)
    \\alpha: Thread half-angle (rad)
    \\lambda: Lead angle (rad)
    \\sigma: Bolt stress (MPa)
    T_thread: Thread torque (N*m)
    T_bearing: Bearing torque (N*m)
    T_total: Total torque (N*m)
    K: Nut factor (-)

    ---References---
    NASA Fastener Design Manual (NASA SP-8007).
    Shigley, Mechanical Engineering Design, thread torque relations for friction.
    ISO 898-1 for proof strength guidance.
    ASME B1.1 for Unified thread geometry and tensile stress area formula.
    """

    if not thread_standard:
        raise ValueError("thread_standard is required.")

    standard = str(thread_standard).strip().lower()
    if standard not in {"metric", "unified", "iso", "si", "imperial", "unc", "unf", "inch"}:
        raise ValueError("thread_standard must be 'metric' or 'unified'.")

    is_metric = standard in {"metric", "iso", "si"}

    if nominal_diameter <= 0.0:
        raise ValueError("nominal_diameter must be positive.")
    if thread_angle_deg <= 0.0 or thread_angle_deg >= 180.0:
        raise ValueError("thread_angle_deg must be between 0 and 180 degrees.")
    if mu_thread < 0.0 or mu_bearing < 0.0:
        raise ValueError("Friction coefficients cannot be negative.")
    if bearing_diameter < 0.0:
        raise ValueError("bearing_diameter cannot be negative.")
    if tensile_stress_area < 0.0:
        raise ValueError("tensile_stress_area cannot be negative.")
    if nut_factor <= 0.0:
        raise ValueError("nut_factor must be positive.")
    if proof_strength <= 0.0:
        raise ValueError("proof_strength must be positive.")

    preload_mode = str(preload_method).strip().lower()
    if preload_mode not in {"percent_proof", "direct"}:
        raise ValueError("preload_method must be 'percent_proof' or 'direct'.")

    torque_mode = str(torque_model).strip().lower()
    if torque_mode not in {"friction", "nut_factor"}:
        raise ValueError("torque_model must be 'friction' or 'nut_factor'.")

    if is_metric:
        d_mm = float(nominal_diameter)
        p_mm = float(thread_pitch)
        if p_mm <= 0.0:
            raise ValueError("thread_pitch must be positive for metric threads.")
        d_in = d_mm / MM_PER_IN
        tpi = float(threads_per_inch) if threads_per_inch else 0.0
        bearing_mm = float(bearing_diameter) if bearing_diameter > 0.0 else 1.5 * d_mm
        proof_strength_mpa = float(proof_strength)
        if preload_mode == "direct":
            if target_preload <= 0.0:
                raise ValueError("target_preload must be positive for direct preload.")
            clamp_load_n = float(target_preload) * 1000.0
        else:
            if percent_proof <= 0.0 or percent_proof > 100.0:
                raise ValueError("percent_proof must be between 0 and 100.")
            clamp_load_n = 0.0
        if tensile_stress_area > 0.0:
            tensile_area_mm2 = float(tensile_stress_area)
        else:
            tensile_area_mm2 = 0.25 * math.pi * (d_mm - 0.9382 * p_mm) ** 2
        tensile_area_in2 = tensile_area_mm2 / (MM_PER_IN**2)
    else:
        d_in = float(nominal_diameter)
        if threads_per_inch <= 0.0:
            raise ValueError("threads_per_inch must be positive for unified threads.")
        tpi = float(threads_per_inch)
        p_in = 1.0 / tpi
        p_mm = p_in * MM_PER_IN
        d_mm = d_in * MM_PER_IN
        bearing_mm = (float(bearing_diameter) if bearing_diameter > 0.0 else 1.5 * d_in) * MM_PER_IN
        proof_strength_mpa = float(proof_strength) * MPA_PER_KSI
        if preload_mode == "direct":
            if target_preload <= 0.0:
                raise ValueError("target_preload must be positive for direct preload.")
            clamp_load_n = float(target_preload) * N_PER_LBF
        else:
            if percent_proof <= 0.0 or percent_proof > 100.0:
                raise ValueError("percent_proof must be between 0 and 100.")
            clamp_load_n = 0.0
        if tensile_stress_area > 0.0:
            tensile_area_in2 = float(tensile_stress_area)
        else:
            tensile_area_in2 = 0.25 * math.pi * (d_in - 0.9743 / tpi) ** 2
        tensile_area_mm2 = tensile_area_in2 * (MM_PER_IN**2)

    if tensile_area_mm2 <= 0.0:
        raise ValueError("Tensile stress area must be positive.")

    proof_load_n = tensile_area_mm2 * proof_strength_mpa
    proof_load_lbf = proof_load_n / N_PER_LBF

    if preload_mode == "percent_proof":
        clamp_load_n = proof_load_n * (percent_proof / 100.0)

    if clamp_load_n <= 0.0:
        raise ValueError("Computed clamp load must be positive.")

    clamp_load_lbf = clamp_load_n / N_PER_LBF

    bolt_stress_mpa = clamp_load_n / tensile_area_mm2
    bolt_stress_ksi = bolt_stress_mpa / MPA_PER_KSI
    proof_utilization = (bolt_stress_mpa / proof_strength_mpa) * 100.0

    d2_mm = d_mm - 0.64952 * p_mm
    if d2_mm <= 0.0:
        raise ValueError("Computed pitch diameter is non-physical. Check thread inputs.")

    lead_angle_rad = math.atan(p_mm / (math.pi * d2_mm))
    lead_angle_deg = math.degrees(lead_angle_rad)

    alpha_rad = math.radians(thread_angle_deg / 2.0)
    cos_alpha = math.cos(alpha_rad)
    if cos_alpha <= 0.0:
        raise ValueError("Thread angle results in invalid geometry (cos(alpha) <= 0).")

    mu_prime = mu_thread / cos_alpha
    tan_lambda = math.tan(lead_angle_rad)
    denominator = 1.0 - mu_prime * tan_lambda
    if denominator <= 0.0:
        raise ValueError(
            "Thread geometry and friction create a self-locking condition in the torque model. "
            "Reduce friction or adjust thread geometry."
        )

    d2_m = d2_mm / 1000.0
    bearing_m = bearing_mm / 1000.0

    torque_thread_nm = clamp_load_n * (d2_m / 2.0) * (tan_lambda + mu_prime) / denominator
    torque_bearing_nm = clamp_load_n * mu_bearing * (bearing_m / 2.0)
    torque_total_friction_nm = torque_thread_nm + torque_bearing_nm

    d_m = d_mm / 1000.0
    torque_total_nut_factor_nm = nut_factor * clamp_load_n * d_m

    if torque_mode == "nut_factor":
        torque_total_nm = torque_total_nut_factor_nm
    else:
        torque_total_nm = torque_total_friction_nm

    torque_total_lbf_ft = torque_total_nm * N_M_TO_LBF_FT

    nut_factor_equiv = torque_total_friction_nm / (clamp_load_n * d_m)

    results: dict[str, float] = {
        "clamp_load_n": clamp_load_n,
        "clamp_load_lbf": clamp_load_lbf,
        "proof_load_n": proof_load_n,
        "proof_load_lbf": proof_load_lbf,
        "proof_utilization_percent": proof_utilization,
        "tensile_stress_area_mm2": tensile_area_mm2,
        "tensile_stress_area_in2": tensile_area_in2,
        "bolt_stress_mpa": bolt_stress_mpa,
        "bolt_stress_ksi": bolt_stress_ksi,
        "torque_total_nm": torque_total_nm,
        "torque_total_lbf_ft": torque_total_lbf_ft,
        "torque_thread_nm": torque_thread_nm,
        "torque_bearing_nm": torque_bearing_nm,
        "torque_total_friction_nm": torque_total_friction_nm,
        "torque_total_nut_factor_nm": torque_total_nut_factor_nm,
        "nut_factor_equiv": nut_factor_equiv,
        "lead_angle_deg": lead_angle_deg,
    }

    results["subst_proof_load_n"] = (
        f"F_p = A_t S_p = {tensile_area_mm2:.3f} \\times {proof_strength_mpa:.3f} = {proof_load_n:.3f}"
    )
    if preload_mode == "percent_proof":
        results["subst_clamp_load_n"] = (
            f"F = k_p F_p = {percent_proof / 100.0:.3f} \\times {proof_load_n:.3f} = {clamp_load_n:.3f}"
        )
    else:
        results["subst_clamp_load_n"] = f"F = {clamp_load_n:.3f}"

    results["subst_bolt_stress_mpa"] = (
        f"\\sigma = \\frac{{F}}{{A_t}} = \\frac{{{clamp_load_n:.3f}}}{{{tensile_area_mm2:.3f}}} = {bolt_stress_mpa:.3f}"
    )
    results["subst_torque_thread_nm"] = (
        f"T_{{thread}} = F \\frac{{d_2}}{{2}} \\frac{{\\tan\\lambda + \\mu_t/\\cos\\alpha}}{{1-(\\mu_t/\\cos\\alpha)\\tan\\lambda}}"
        f" = {torque_thread_nm:.3f}"
    )
    results["subst_torque_bearing_nm"] = (
        f"T_{{bearing}} = F \\mu_b \\frac{{D_b}}{{2}} = {torque_bearing_nm:.3f}"
    )

    if torque_mode == "nut_factor":
        results["subst_torque_total_nm"] = (
            f"T = K F d = {nut_factor:.3f} \\times {clamp_load_n:.3f} \\times {d_m:.6f} = {torque_total_nm:.3f}"
        )
    else:
        results["subst_torque_total_nm"] = (
            f"T = T_{{thread}} + T_{{bearing}} = {torque_thread_nm:.3f} + {torque_bearing_nm:.3f} = {torque_total_nm:.3f}"
        )

    results["subst_nut_factor_equiv"] = (
        f"K = \\frac{{T_{{total}}}}{{F d}} = \\frac{{{torque_total_friction_nm:.3f}}}"
        f"{{{clamp_load_n:.3f} \\times {d_m:.6f}}} = {nut_factor_equiv:.3f}"
    )

    return results
