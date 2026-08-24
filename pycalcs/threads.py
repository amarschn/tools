"""Thread geometry, identification, and direct-axial size screening.

The standard designation lists are shared with :mod:`pycalcs.fasteners`. This
module parses those designations and uses the canonical geometry equations in
:mod:`pycalcs.fasteners`, so both tools report the same dimensions and areas.

References:
    - ISO 68-1:2023, ISO general purpose screw threads, basic and design
      profiles, Part 1: Metric screw threads.
    - ISO 724:2023, ISO general purpose metric screw threads, basic dimensions.
    - ISO 262:2023, selected metric sizes for bolts, screws, studs, and nuts.
    - ASME B1.1-2024, Unified Inch Screw Threads (UN and UNR thread form).
    - NIST Handbook 28, Screw-Thread Standards for Federal Services.
    - NASA fastener training material, cross-sectional areas for stress
      calculations, NASA NTRS 20110016427.
"""

from __future__ import annotations

import math
from typing import Any

try:
    from .fasteners import (
        ISO_FASTENER_GEOMETRY,
        UTS_FASTENER_GEOMETRY,
        calculate_basic_thread_geometry,
        parse_metric_thread_designation,
        parse_unified_thread_designation,
    )
except ImportError:  # Pyodide loads modules as top-level files.
    from fasteners import (
        ISO_FASTENER_GEOMETRY,
        UTS_FASTENER_GEOMETRY,
        calculate_basic_thread_geometry,
        parse_metric_thread_designation,
        parse_unified_thread_designation,
    )


INCH_TO_M = 0.0254
METERS_TO_MM = 1000.0
VALID_THREAD_SYSTEMS = ("iso_metric", "unified")
VALID_THREAD_SERIES = ("coarse", "fine", "all")

def _validate_thread_system(thread_system: str) -> None:
    """Validate a thread-system identifier.

    Parameters:
        thread_system: ``"iso_metric"`` or ``"unified"``.

    Returns:
        ``None`` when the identifier is valid.

    Raises:
        ValueError: If the identifier is not supported.
    """
    if thread_system not in VALID_THREAD_SYSTEMS:
        raise ValueError(
            "thread_system must be 'iso_metric' or 'unified'."
        )
def _catalog_records(thread_system: str) -> list[dict[str, Any]]:
    """Build exact catalog records from the shared designation list.

    ISO coarse pitch is the largest included pitch at a given nominal diameter.
    Unified series comes from the UNC or UNF suffix.

    Parameters:
        thread_system: ``"iso_metric"`` or ``"unified"``.

    Returns:
        Fresh dictionaries containing designation, system, series, nominal
        diameter, pitch, and threads per inch. Callers can safely mutate them.

    Raises:
        ValueError: If ``thread_system`` is unsupported.
    """
    _validate_thread_system(thread_system)

    if thread_system == "unified":
        records = []
        for designation in UTS_FASTENER_GEOMETRY:
            diameter_m, pitch_m, tpi, series = parse_unified_thread_designation(
                designation
            )
            records.append(
                {
                    "designation": designation,
                    "thread_system": thread_system,
                    "series": series,
                    "nominal_diameter": diameter_m,
                    "pitch": pitch_m,
                    "threads_per_inch": float(tpi),
                }
            )
        return sorted(
            records,
            key=lambda item: (
                item["nominal_diameter"],
                -item["pitch"],
                item["designation"],
            ),
        )

    parsed = []
    for designation in ISO_FASTENER_GEOMETRY:
        diameter_m, pitch_m = parse_metric_thread_designation(designation)
        parsed.append((designation, diameter_m, pitch_m))

    coarse_pitch_by_diameter: dict[float, float] = {}
    for _, diameter_m, pitch_m in parsed:
        coarse_pitch_by_diameter[diameter_m] = max(
            coarse_pitch_by_diameter.get(diameter_m, 0.0), pitch_m
        )

    records = []
    for designation, diameter_m, pitch_m in parsed:
        series = (
            "coarse"
            if math.isclose(
                pitch_m,
                coarse_pitch_by_diameter[diameter_m],
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            else "fine"
        )
        records.append(
            {
                "designation": designation,
                "thread_system": thread_system,
                "series": series,
                "nominal_diameter": diameter_m,
                "pitch": pitch_m,
                "threads_per_inch": INCH_TO_M / pitch_m,
            }
        )
    return sorted(
        records,
        key=lambda item: (
            item["nominal_diameter"],
            -item["pitch"],
            item["designation"],
        ),
    )


def get_thread_catalog() -> dict[str, list[dict[str, Any]]]:
    r"""
    Return the supported ISO metric and Unified thread catalogs.

    Records are generated from the shared fastener designation lists and use
    exact parsed dimensions. This function is intended for dropdown population
    and does not calculate tolerance limits or gage dimensions.

    ---Parameters---

    ---Returns---
    iso_metric : list
        Supported ISO metric records with designation, series, diameter, pitch,
        and threads per inch.
    unified : list
        Supported UNC and UNF records with exact inch-derived diameter and pitch.

    ---LaTeX---
    P_{UN} = \frac{25.4}{n}\ \mathrm{mm}
    """
    return {
        "iso_metric": _catalog_records("iso_metric"),
        "unified": _catalog_records("unified"),
    }


def _geometry_for_designation(
    thread_system: str,
    designation: str,
) -> dict[str, Any]:
    """Return a catalog record combined with its calculated geometry.

    Parameters:
        thread_system: ``"iso_metric"`` or ``"unified"``.
        designation: A supported designation in that catalog.

    Returns:
        A new dictionary containing catalog fields and all fields returned by
        :func:`calculate_basic_thread_geometry`.

    Raises:
        ValueError: If the designation is not in the selected catalog.
    """
    records = _catalog_records(thread_system)
    record = next(
        (item for item in records if item["designation"] == designation),
        None,
    )
    if record is None:
        raise ValueError(
            f"Unknown {thread_system} thread designation '{designation}'."
        )
    geometry = calculate_basic_thread_geometry(
        thread_system,
        record["nominal_diameter"],
        record["pitch"],
    )
    return {**record, **geometry}


def identify_standard_thread(
    thread_system: str,
    measured_major_diameter: float,
    measured_pitch: float,
    candidate_count: int = 3,
) -> dict[str, Any]:
    r"""
    Find the nearest supported nominal thread from diameter and pitch.

    The ranking compares relative diameter and pitch residuals. It identifies
    the nearest entry in this tool's catalog; it is not a tolerance or gaging
    decision.

    ---Parameters---
    thread_system : str
        Standard family to search: "iso_metric" or "unified".
    measured_major_diameter : float
        Measured external major diameter in metres. Must be positive.
    measured_pitch : float
        Measured axial pitch in metres. For a Unified thread, convert measured
        threads per inch with P = 0.0254 / n before calling.
    candidate_count : int
        Number of nearest catalog entries to return. Must be between 1 and the
        number of supported entries.

    ---Returns---
    nearest_designation : str
        Designation with the lowest relative-distance score.
    diameter_difference : float
        Measured minus nominal major diameter for the nearest entry, in metres.
    pitch_difference : float
        Measured minus nominal pitch for the nearest entry, in metres.
    relative_distance : float
        Dimensionless ranking distance for the nearest entry.
    candidates : list
        Ranked candidate records with designation, nominal dimensions,
        residuals, and relative distance.
    search_scope : str
        Reminder that the result is nearest within the included catalog.
    subst_relative_distance : str
        LaTeX substitution for the nearest-candidate ranking distance.

    ---LaTeX---
    \mathrm{Equation\ (7)}\quad s = \sqrt{\left(\frac{d_m-d}{d}\right)^2 + \left(\frac{P_m-P}{P}\right)^2}
    """
    _validate_thread_system(thread_system)
    if measured_major_diameter <= 0:
        raise ValueError("measured_major_diameter must be positive.")
    if measured_pitch <= 0:
        raise ValueError("measured_pitch must be positive.")

    records = _catalog_records(thread_system)
    if not 1 <= candidate_count <= len(records):
        raise ValueError(
            f"candidate_count must be between 1 and {len(records)}."
        )

    candidates = []
    for record in records:
        diameter_difference = (
            measured_major_diameter - record["nominal_diameter"]
        )
        pitch_difference = measured_pitch - record["pitch"]
        relative_distance = math.hypot(
            diameter_difference / record["nominal_diameter"],
            pitch_difference / record["pitch"],
        )
        candidates.append(
            {
                **record,
                "diameter_difference": diameter_difference,
                "pitch_difference": pitch_difference,
                "relative_distance": relative_distance,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["relative_distance"],
            abs(item["diameter_difference"]),
            abs(item["pitch_difference"]),
            item["nominal_diameter"],
            item["designation"],
        )
    )
    nearest = candidates[0]
    return {
        "nearest_designation": nearest["designation"],
        "diameter_difference": nearest["diameter_difference"],
        "pitch_difference": nearest["pitch_difference"],
        "relative_distance": nearest["relative_distance"],
        "candidates": [dict(item) for item in candidates[:candidate_count]],
        "search_scope": (
            "Nearest nominal size in the supported catalog. Thread class, "
            "allowance, plating, wear, and measurement uncertainty are not "
            "included."
        ),
        "subst_relative_distance": (
            "s = \\sqrt{"
            f"\\left(\\frac{{{measured_major_diameter*METERS_TO_MM:.6g} - "
            f"{nearest['nominal_diameter']*METERS_TO_MM:.6g}}}"
            f"{{{nearest['nominal_diameter']*METERS_TO_MM:.6g}}}\\right)^2 + "
            f"\\left(\\frac{{{measured_pitch*METERS_TO_MM:.6g} - "
            f"{nearest['pitch']*METERS_TO_MM:.6g}}}"
            f"{{{nearest['pitch']*METERS_TO_MM:.6g}}}\\right)^2"
            f"}} = {nearest['relative_distance']:.6g}"
        ),
    }


def screen_thread_size(
    thread_system: str,
    thread_series: str,
    axial_load: float,
    proof_strength: float,
    design_factor: float,
) -> dict[str, Any]:
    r"""
    Screen the smallest supported thread for direct axial proof load.

    The check multiplies the service load by the required design factor and
    compares that demand with proof strength times tensile-stress area. It does
    not model a preloaded bolted joint.

    ---Parameters---
    thread_system : str
        Standard family: "iso_metric" or "unified".
    thread_series : str
        "coarse", "fine", or "all". Coarse means ISO coarse pitch or UNC;
        fine means included ISO fine pitches or UNF.
    axial_load : float
        Maximum direct tensile service load per fastener in newtons.
    proof_strength : float
        Conservative minimum proof strength Sp in pascals. The supplied value
        must be valid for every candidate diameter in the searched series.
    design_factor : float
        Required ratio of proof capacity to service load. Must be at least 1.

    ---Returns---
    design_load : float
        Factored axial demand Fd in newtons.
    required_stress_area : float
        Minimum tensile-stress area required in square metres.
    recommended_designation : str
        Smallest supported designation meeting the factored demand, or an empty
        string when the catalog contains no passing size.
    recommended_stress_area : float
        Tensile-stress area of the recommended thread in square metres.
    proof_capacity : float
        Recommended proof capacity SpAs in newtons.
    proof_margin : float
        Proof capacity divided by unfactored service load.
    utilization_percent : float
        Factored demand divided by proof capacity, expressed as a percentage.
    previous_designation : str
        Largest lower-capacity candidate, or an empty string.
    previous_proof_capacity : float
        Proof capacity of the previous candidate in newtons.
    previous_proof_margin : float
        Previous proof capacity divided by service load.
    status : str
        "sized" when a candidate passes or "no_size" when none pass.
    candidates : list
        Candidate records sorted by tensile-stress area.
    limitations : str
        Scope statement for the preliminary direct-tension screen.
    subst_design_load : str
        LaTeX substitution for the factored demand.
    subst_required_stress_area : str
        LaTeX substitution for the required tensile-stress area.
    subst_proof_capacity : str
        LaTeX substitution for the selected proof capacity.
    subst_proof_margin : str
        LaTeX substitution for the selected proof margin.

    ---LaTeX---
    \mathrm{Equation\ (7)}\quad F_d = n_d F
    \mathrm{Equation\ (8)}\quad A_{s,req} = \frac{F_d}{S_p}
    \mathrm{Equation\ (9)}\quad F_p = S_p A_s
    \mathrm{Equation\ (10)}\quad n_p = \frac{F_p}{F}
    """
    _validate_thread_system(thread_system)
    if thread_series not in VALID_THREAD_SERIES:
        raise ValueError("thread_series must be 'coarse', 'fine', or 'all'.")
    if axial_load <= 0:
        raise ValueError("axial_load must be positive.")
    if proof_strength <= 0:
        raise ValueError("proof_strength must be positive.")
    if design_factor < 1.0:
        raise ValueError("design_factor must be at least 1.0.")

    design_load = axial_load * design_factor
    required_area = design_load / proof_strength
    records = _catalog_records(thread_system)
    if thread_series != "all":
        records = [
            record for record in records if record["series"] == thread_series
        ]
    if not records:
        raise ValueError(
            f"No {thread_series} entries are available for {thread_system}."
        )

    candidates = []
    for record in records:
        geometry = calculate_basic_thread_geometry(
            thread_system,
            record["nominal_diameter"],
            record["pitch"],
        )
        stress_area = float(geometry["tensile_stress_area"])
        proof_capacity = proof_strength * stress_area
        candidates.append(
            {
                **record,
                "tensile_stress_area": stress_area,
                "proof_capacity": proof_capacity,
                "proof_margin": proof_capacity / axial_load,
                "passes": proof_capacity >= design_load,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["tensile_stress_area"],
            item["nominal_diameter"],
            item["pitch"],
            item["designation"],
        )
    )
    passing_index = next(
        (index for index, item in enumerate(candidates) if item["passes"]),
        None,
    )
    limitations = (
        "Smallest passing size in the included catalog, based on a preliminary "
        "direct-axial proof-load screen. The entered proof strength must be "
        "valid across the searched diameter range. The screen omits preload, "
        "joint stiffness and load sharing, fatigue, shear, thread stripping, "
        "engagement length, temperature, and installation scatter."
    )

    if passing_index is None:
        last = candidates[-1]
        return {
            "design_load": design_load,
            "required_stress_area": required_area,
            "recommended_designation": "",
            "recommended_stress_area": 0.0,
            "proof_capacity": 0.0,
            "proof_margin": 0.0,
            "utilization_percent": math.inf,
            "previous_designation": last["designation"],
            "previous_proof_capacity": last["proof_capacity"],
            "previous_proof_margin": last["proof_margin"],
            "status": "no_size",
            "candidates": [dict(item) for item in candidates],
            "limitations": limitations,
            "subst_design_load": (
                f"F_d = {design_factor:.6g}({axial_load/1000:.6g}) = "
                f"{design_load/1000:.6g}\\text{{ kN}}"
            ),
            "subst_required_stress_area": (
                f"A_{{s,req}} = \\frac{{{design_load/1000:.6g}\\text{{ kN}}}}"
                f"{{{proof_strength/1e6:.6g}\\text{{ MPa}}}} = "
                f"{required_area*1e6:.6g}\\text{{ mm}}^2"
            ),
            "subst_proof_capacity": "",
            "subst_proof_margin": "",
        }

    selected = candidates[passing_index]
    previous = candidates[passing_index - 1] if passing_index > 0 else None
    utilization = 100.0 * design_load / selected["proof_capacity"]
    return {
        "design_load": design_load,
        "required_stress_area": required_area,
        "recommended_designation": selected["designation"],
        "recommended_stress_area": selected["tensile_stress_area"],
        "proof_capacity": selected["proof_capacity"],
        "proof_margin": selected["proof_margin"],
        "utilization_percent": utilization,
        "previous_designation": previous["designation"] if previous else "",
        "previous_proof_capacity": previous["proof_capacity"] if previous else 0.0,
        "previous_proof_margin": previous["proof_margin"] if previous else 0.0,
        "status": "sized",
        "candidates": [dict(item) for item in candidates],
        "limitations": limitations,
        "subst_design_load": (
            f"F_d = {design_factor:.6g}({axial_load/1000:.6g}) = "
            f"{design_load/1000:.6g}\\text{{ kN}}"
        ),
        "subst_required_stress_area": (
            f"A_{{s,req}} = \\frac{{{design_load/1000:.6g}\\text{{ kN}}}}"
            f"{{{proof_strength/1e6:.6g}\\text{{ MPa}}}} = "
            f"{required_area*1e6:.6g}\\text{{ mm}}^2"
        ),
        "subst_proof_capacity": (
            f"F_p = {proof_strength/1e6:.6g}\\text{{ MPa}}"
            f"({selected['tensile_stress_area']*1e6:.6g}\\text{{ mm}}^2) = "
            f"{selected['proof_capacity']/1000:.6g}\\text{{ kN}}"
        ),
        "subst_proof_margin": (
            f"n_p = \\frac{{{selected['proof_capacity']/1000:.6g}}}"
            f"{{{axial_load/1000:.6g}}} = {selected['proof_margin']:.6g}"
        ),
    }


def analyze_thread(
    mode: str,
    thread_system: str,
    thread_designation: str,
    measured_major_diameter: float,
    measured_pitch: float,
    axial_load: float,
    proof_strength: float,
    design_factor: float,
    thread_series: str = "coarse",
) -> dict[str, Any]:
    r"""
    Explore, identify, or screen a standard fastening thread.

    The wrapper supplies one stable browser API for the tool's three modes. It
    always returns the selected thread geometry plus mode-specific evidence.

    ---Parameters---
    mode : str
        Task to run: "explore", "identify", or "size".
    thread_system : str
        Standard family: "iso_metric" or "unified".
    thread_designation : str
        Supported designation used in explore mode. Other modes replace it with
        the identified or recommended designation.
    measured_major_diameter : float
        External major-diameter measurement in metres for identify mode.
    measured_pitch : float
        Axial pitch measurement in metres for identify mode.
    axial_load : float
        Direct tensile service load per fastener in newtons for size mode.
    proof_strength : float
        Conservative minimum proof strength in pascals for size mode. It must
        be valid across every candidate diameter in the searched series.
    design_factor : float
        Required proof-capacity ratio for size mode. Must be at least 1.
    thread_series : str
        Candidate series for size mode: "coarse", "fine", or "all".

    ---Returns---
    mode : str
        Completed task identifier.
    thread_system : str
        Selected standard family.
    designation : str
        Explored, identified, or recommended thread designation.
    series : str
        Coarse or fine series for the selected designation.
    nominal_diameter : float
        Basic major diameter in metres.
    pitch : float
        Axial thread pitch in metres.
    threads_per_inch : float
        Reciprocal pitch in threads per inch.
    included_angle_deg : float
        Included thread angle in degrees.
    fundamental_height : float
        Fundamental triangle height H in metres.
    pitch_diameter_basic : float
        Basic pitch diameter d2 in metres.
    internal_minor_diameter_basic : float
        Basic internal minor diameter D1 in metres.
    external_minor_diameter_basic : float
        ISO external design-profile root diameter d3 in metres, or None for
        Unified threads.
    profile_minor_diameter : float
        Minor-diameter reference used by the schematic in metres.
    external_thread_depth : float
        Radial schematic external thread depth in metres.
    internal_thread_depth : float
        Radial basic internal thread depth in metres.
    tensile_stress_area : float
        Effective tensile-stress area As in square metres.
    lead_angle_deg : float
        Single-start lead angle at the pitch diameter in degrees.
    profile_note : str
        Scope note for the displayed profile.
    diameter_difference : float
        Measurement residual in metres for identify mode, otherwise zero.
    pitch_difference : float
        Pitch residual in metres for identify mode, otherwise zero.
    relative_distance : float
        Identification ranking score, otherwise zero.
    match_candidates : list
        Nearest nominal candidates for identify mode.
    search_scope : str
        Identification scope note, empty in other modes.
    design_load : float
        Factored direct axial demand in newtons for size mode.
    required_stress_area : float
        Required tensile-stress area in square metres for size mode.
    proof_capacity : float
        Selected proof capacity in newtons for size mode.
    proof_margin : float
        Proof capacity divided by service load for size mode.
    utilization_percent : float
        Factored-demand utilization of proof capacity in size mode.
    previous_designation : str
        Largest lower-capacity sizing candidate, when one exists.
    previous_proof_capacity : float
        Previous candidate proof capacity in newtons.
    previous_proof_margin : float
        Previous candidate proof margin.
    sizing_status : str
        "sized", "no_size", or an empty string outside size mode.
    sizing_candidates : list
        All sizing candidates in ascending stress-area order.
    limitations : str
        Direct-axial sizing scope note, empty outside size mode.
    subst_fundamental_height : str
        LaTeX substitution for Equation (1).
    subst_pitch_diameter_basic : str
        LaTeX substitution for Equation (2).
    subst_internal_minor_diameter_basic : str
        LaTeX substitution for Equation (3).
    subst_profile_minor_diameter : str
        LaTeX substitution for Equation (4).
    subst_tensile_stress_area : str
        LaTeX substitution for Equation (5a) or (5b).
    subst_lead_angle_deg : str
        LaTeX substitution for Equation (6).
    subst_relative_distance : str
        LaTeX substitution for Equation (7) in identify mode.
    subst_design_load : str
        LaTeX substitution for Equation (7), empty outside size mode.
    subst_required_stress_area : str
        LaTeX substitution for Equation (8), empty outside size mode.
    subst_proof_capacity : str
        LaTeX substitution for Equation (9), empty outside size mode.
    subst_proof_margin : str
        LaTeX substitution for Equation (10), empty outside size mode.

    ---LaTeX---
    \mathrm{Equation\ (1)}\quad H = \frac{\sqrt{3}}{2}P
    \mathrm{Equation\ (2)}\quad d_2 = d - \frac{3}{4}H
    \mathrm{Equation\ (3)}\quad D_1 = D - \frac{5}{4}H
    \mathrm{Equation\ (4a)}\quad d_3 = d - \frac{17}{12}H
    \mathrm{Equation\ (4b)}\quad d_{basic} = d - \frac{3}{2}H
    \mathrm{Equation\ (5a)}\quad A_{s,M} = \frac{\pi}{4}(d - 0.938194P)^2
    \mathrm{Equation\ (5b)}\quad A_{s,UN} = \frac{\pi}{4}(d - 0.9743P)^2
    \mathrm{Equation\ (6)}\quad \lambda = \tan^{-1}\left(\frac{P}{\pi d_2}\right)
    \mathrm{Equation\ (7,identify)}\quad s = \sqrt{\left(\frac{d_m-d}{d}\right)^2 + \left(\frac{P_m-P}{P}\right)^2}
    \mathrm{Equation\ (7,size)}\quad F_d = n_d F
    \mathrm{Equation\ (8,size)}\quad A_{s,req} = \frac{F_d}{S_p}
    \mathrm{Equation\ (9,size)}\quad F_p = S_p A_s
    \mathrm{Equation\ (10,size)}\quad n_p = \frac{F_p}{F}
    """
    _validate_thread_system(thread_system)
    if mode not in ("explore", "identify", "size"):
        raise ValueError("mode must be 'explore', 'identify', or 'size'.")

    identification: dict[str, Any] = {}
    sizing: dict[str, Any] = {}

    if mode == "explore":
        designation = thread_designation
    elif mode == "identify":
        identification = identify_standard_thread(
            thread_system,
            measured_major_diameter,
            measured_pitch,
            candidate_count=3,
        )
        designation = identification["nearest_designation"]
    else:
        sizing = screen_thread_size(
            thread_system,
            thread_series,
            axial_load,
            proof_strength,
            design_factor,
        )
        designation = sizing["recommended_designation"]
        if not designation:
            records = _catalog_records(thread_system)
            filtered = (
                records
                if thread_series == "all"
                else [
                    record
                    for record in records
                    if record["series"] == thread_series
                ]
            )
            designation = filtered[-1]["designation"]

    geometry = _geometry_for_designation(thread_system, designation)
    return {
        "mode": mode,
        "thread_system": thread_system,
        "designation": designation,
        "series": geometry["series"],
        "nominal_diameter": geometry["nominal_diameter"],
        "pitch": geometry["pitch"],
        "threads_per_inch": geometry["threads_per_inch"],
        "included_angle_deg": geometry["included_angle_deg"],
        "fundamental_height": geometry["fundamental_height"],
        "pitch_diameter_basic": geometry["pitch_diameter_basic"],
        "internal_minor_diameter_basic": geometry[
            "internal_minor_diameter_basic"
        ],
        "external_minor_diameter_basic": geometry[
            "external_minor_diameter_basic"
        ],
        "profile_minor_diameter": geometry["profile_minor_diameter"],
        "external_thread_depth": geometry["external_thread_depth"],
        "internal_thread_depth": geometry["internal_thread_depth"],
        "tensile_stress_area": geometry["tensile_stress_area"],
        "lead_angle_deg": geometry["lead_angle_deg"],
        "profile_note": geometry["profile_note"],
        "diameter_difference": identification.get(
            "diameter_difference", 0.0
        ),
        "pitch_difference": identification.get("pitch_difference", 0.0),
        "relative_distance": identification.get("relative_distance", 0.0),
        "match_candidates": identification.get("candidates", []),
        "search_scope": identification.get("search_scope", ""),
        "design_load": sizing.get("design_load", 0.0),
        "required_stress_area": sizing.get("required_stress_area", 0.0),
        "proof_capacity": sizing.get("proof_capacity", 0.0),
        "proof_margin": sizing.get("proof_margin", 0.0),
        "utilization_percent": sizing.get("utilization_percent", 0.0),
        "previous_designation": sizing.get("previous_designation", ""),
        "previous_proof_capacity": sizing.get(
            "previous_proof_capacity", 0.0
        ),
        "previous_proof_margin": sizing.get("previous_proof_margin", 0.0),
        "sizing_status": sizing.get("status", ""),
        "sizing_candidates": sizing.get("candidates", []),
        "limitations": sizing.get("limitations", ""),
        "subst_fundamental_height": geometry["subst_fundamental_height"],
        "subst_pitch_diameter_basic": geometry[
            "subst_pitch_diameter_basic"
        ],
        "subst_internal_minor_diameter_basic": geometry[
            "subst_internal_minor_diameter_basic"
        ],
        "subst_profile_minor_diameter": geometry[
            "subst_profile_minor_diameter"
        ],
        "subst_tensile_stress_area": geometry[
            "subst_tensile_stress_area"
        ],
        "subst_lead_angle_deg": geometry["subst_lead_angle_deg"],
        "subst_relative_distance": identification.get(
            "subst_relative_distance", ""
        ),
        "subst_design_load": sizing.get("subst_design_load", ""),
        "subst_required_stress_area": sizing.get(
            "subst_required_stress_area", ""
        ),
        "subst_proof_capacity": sizing.get("subst_proof_capacity", ""),
        "subst_proof_margin": sizing.get("subst_proof_margin", ""),
    }
