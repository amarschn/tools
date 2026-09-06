"""Physical thread profiles and measurement comparisons, in millimetres.

Nominal catalogs and provenance come from thread_specifications. Basic geometry
comes from fasteners (ISO 68-1 / ISO 724 and ASME B1.1). The search windows below
are identification heuristics, NOT tolerance or inspection limits.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from itertools import pairwise
from typing import Any

try:
    from .thread_specifications import (
        PIPE_PAIRS,
        _pairs,
        _parse_unified_size,
        calculate_basic_thread_geometry,
        parse_metric_thread_designation,
        specification_catalog,
    )
except ImportError:
    from thread_specifications import (
        PIPE_PAIRS,
        _pairs,
        _parse_unified_size,
        calculate_basic_thread_geometry,
        parse_metric_thread_designation,
        specification_catalog,
    )


MODEL_VERSION = "nominal-axial-v1"
LIMITATION = (
    "Representative nominal geometry, not tolerance-controlled manufacturing "
    "geometry. Straight flanks and simplified flat roots; no allowance, root "
    "radius, runout, lead-in, coating, or tolerance class is modeled."
)


def physical_profile(geometry: dict[str, Any]) -> dict[str, Any]:
    """Express the existing explanatory axial profiles in physical coordinates.

    ---Parameters---
    geometry : dict
        Basic geometry returned by fasteners, with lengths in metres.

    ---Returns---
    model : dict
        Versioned millimetre dimensions and one-pitch [axial, radius] polylines.
        Internal sharp root reference matches the educational SVG, not a tool.

    ---LaTeX---
    r = d / 2
    x = P y / (2H)

    r: radius; d: diameter; P: pitch; H: fundamental triangle height;
    y: radial distance below the sharp external apex. All lengths in mm.
    Reference: the basic profiles in ISO 68-1 and ASME B1.1, simplified as stated.
    """
    pitch = geometry["pitch"] * 1000
    height = geometry["fundamental_height"] * 1000
    radius = geometry["nominal_diameter"] * 500
    root = radius - geometry["external_thread_depth"] * 1000
    minor = radius - geometry["internal_thread_depth"] * 1000
    sharp = radius + height / 8
    crest_x = pitch / 16
    root_x = pitch * (sharp - root) / (2 * height)
    minor_x = pitch * (sharp - minor) / (2 * height)
    return {
        "version": MODEL_VERSION,
        "unit": "mm",
        "pitch_mm": pitch,
        "major_diameter_mm": radius * 2,
        "pitch_diameter_mm": geometry["pitch_diameter_basic"] * 1000,
        "internal_minor_mm": minor * 2,
        "external_minor_mm": root * 2,
        "sharp_radius_mm": sharp,
        "included_angle_deg": 60,
        "external": [
            [0, radius],
            [crest_x, radius],
            [root_x, root],
            [pitch - root_x, root],
            [pitch - crest_x, radius],
            [pitch, radius],
        ],
        "internal": [
            [0, sharp],
            [minor_x, minor],
            [pitch - minor_x, minor],
            [pitch, sharp],
        ],
        "limitation": LIMITATION,
    }


@lru_cache(maxsize=1)
def _records() -> tuple[dict[str, Any], ...]:
    """Normalize the specification catalog once; callers never mutate records."""
    records = []
    for family, meta in specification_catalog().items():
        machine = meta["kind"] == "machine"
        for size in meta["sizes"]:
            geometry = model = None
            if machine:
                if family == "metric":
                    diameter, pitch = parse_metric_thread_designation(size)
                else:
                    nominal, tpi = size.rsplit(" ", 1)[0].rsplit("-", 1)
                    diameter = _parse_unified_size(nominal) * 0.0254
                    pitch = 0.0254 / float(tpi)
                geometry = calculate_basic_thread_geometry(
                    "iso_metric" if family == "metric" else "unified", diameter, pitch
                )
                geometry.update(designation=size, mode="explore", series=family.upper())
                model = physical_profile(geometry)
                geometry["physical_model"] = model
                pitch_mm = model["pitch_mm"]
            else:
                pairs = dict(
                    _pairs(PIPE_PAIRS["npt" if family in ("npt", "nptf") else "bsp"])
                )
                pitch_mm = 25.4 / float(pairs[size])
            records.append(
                {
                    "id": family + ":" + size,
                    "family": family,
                    "size": size,
                    "designation": size if machine else size + " " + family.upper(),
                    "kind": meta["kind"],
                    "source": meta["standard"],
                    "pitch_mm": pitch_mm,
                    "tpi": 25.4 / pitch_mm,
                    "diameter_mm": model["major_diameter_mm"] if model else None,
                    "internal_minor_mm": model["internal_minor_mm"] if model else None,
                    "model": model,
                    "geometry": geometry,
                    "diagram": None
                    if machine
                    else {
                        "kind": "pipe",
                        "pitch_mm": pitch_mm,
                        "pitch_in": pitch_mm / 25.4,
                        "tpi": 25.4 / pitch_mm,
                        "included_angle_deg": 60 if family in ("npt", "nptf") else 55,
                        "diameter_taper": 0 if family == "bspp" else 1 / 16,
                        "half_angle_deg": 0
                        if family == "bspp"
                        else math.degrees(math.atan(1 / 32)),
                    },
                    "capabilities": {
                        "specify": True,
                        "identify_external": machine,
                        "identify_internal": machine,
                        "print_pitch": True,
                        "print_profile": machine,
                        "step": machine,
                    },
                }
            )
    return tuple(records)


def _number(state: dict, key: str, default: float | None = None) -> float | None:
    """Read an optional positive finite measurement, rejecting malformed values."""
    value = state.get(key)
    if value in (None, ""):
        return default
    try:
        result = float(value)
    except (ValueError, TypeError) as error:
        raise ValueError(key.replace("_", " ") + " must be a number.") from error
    if not math.isfinite(result) or result <= 0:
        raise ValueError(key.replace("_", " ") + " must be positive and finite.")
    if result < 1e-9 or result > 1e9:
        raise ValueError(
            key.replace("_", " ")
            + " is outside the supported numerical range. Check its units."
        )
    return result


def find_threads(state_json: str) -> dict[str, Any]:
    """Compare observations to supported nominal threads without assigning a fit.

    ---Parameters---
    state_json : str
        JSON: side external/internal/unsure; diameter, span, separation and
        second_diameter in unit mm/in; optional pitch in pitch_unit mm/tpi;
        intervals counts spaces, not crests. Optional diameter_uncertainty in
        selected length unit and pitch_uncertainty in mm. Family all or catalog
        key; form unknown/parallel/tapered; hand unknown/RH/LH is an observation.

    ---Returns---
    result : dict
        State, shortlist, measurement explanation, warnings and search windows.
        No score is a probability. Pipe rows compare pitch only, not diameter.

    ---LaTeX---
    P = S / n
    TPI = 25.4 / P
    T = |d_b - d_a| / L

    P: pitch (mm); S: span (mm); n: positive integer pitch intervals;
    TPI: threads/inch; T: diameter taper; d_a, d_b: measured diameters (mm);
    L: positive separation (mm). Search defaults below are engineering
    comparison windows, not dimensional limits from ISO or ASME standards.
    """
    state = json.loads(state_json)
    side = state.get("side", "external")
    unit = state.get("unit", "mm")
    pitch_unit = state.get("pitch_unit", "mm")
    form = state.get("form", "unknown")
    family = state.get("family", "all")
    if side not in ("external", "internal", "unsure") or unit not in ("mm", "in"):
        raise ValueError("Choose a supported measurement type and length unit.")
    if pitch_unit not in ("mm", "tpi") or form not in (
        "unknown",
        "parallel",
        "tapered",
    ):
        raise ValueError("Choose a supported pitch unit and thread form.")
    if family != "all" and family not in specification_catalog():
        raise ValueError("Unknown family filter.")
    if state.get("hand", "unknown") not in ("unknown", "RH", "LH"):
        raise ValueError("Choose unknown, right hand, or left hand.")
    factor = 25.4 if unit == "in" else 1
    diameter = _number(state, "diameter")
    diameter = diameter * factor if diameter is not None else None
    pitch = _number(state, "pitch")
    if pitch is not None and pitch_unit == "tpi":
        pitch = 25.4 / pitch
    equations = []
    span, intervals = _number(state, "span"), _number(state, "intervals")
    if span is not None or intervals is not None:
        if span is None or intervals is None or not intervals.is_integer():
            raise ValueError(
                "Enter a span and a positive whole number of intervals (spaces)."
            )
        pitch = span * factor / intervals
        equations.append(
            f"Equation (1): P = S / n = {span * factor:g} / {intervals:g} = {pitch:g} mm. P: pitch; S: span in mm; n: intervals."
        )
    if pitch is not None:
        equations.append(
            f"Equation (2): TPI = 25.4 / P = 25.4 / {pitch:g} = {25.4 / pitch:g}. P: pitch in mm; TPI: threads per inch."
        )
    taper = None
    second, separation = _number(state, "second_diameter"), _number(state, "separation")
    if second is not None or separation is not None:
        if diameter is None or second is None or separation is None:
            raise ValueError("Taper needs two diameters and their axial separation.")
        taper = abs(second * factor - diameter) / (separation * factor)
        equations.append(
            f"Equation (3): T = |d_b - d_a| / L = |{second * factor:g} - {diameter:g}| / {separation * factor:g} = {taper:g}. T: diameter taper; diameters and separation in mm."
        )
    diameter_uncertainty = (
        _number(state, "diameter_uncertainty", 0.05 / factor) * factor
    )
    pitch_uncertainty = _number(state, "pitch_uncertainty", 0.03)
    # Allow ordinary crest truncation/wear and a wider internal basic-bore
    # comparison. These symmetric windows deliberately retain lookalikes.
    diameter_window = diameter_uncertainty + (0.35 if side == "internal" else 0.20)
    pitch_window = pitch_uncertainty
    warnings = [
        "Preliminary identification only. Fit class, material, process, strength and pressure rating cannot be inferred. Do not force an unknown thread into a mating part.",
        f"Search windows: diameter ±{diameter_window:g} mm (entered uncertainty plus {'0.35' if side == 'internal' else '0.20'} mm comparison allowance); pitch ±{pitch_window:g} mm. These are not standard tolerance limits.",
    ]
    if side == "internal":
        warnings.append(
            "Internal diameter compares your bore reading to BASIC minor diameter, not acceptance limits. Caliper access, crest truncation and wear can change the reading."
        )
    if side == "unsure" and diameter is not None:
        warnings.append(
            "Diameter is not used until its measurement basis is known. Compare pitch or measure a known mating screw."
        )
    if pitch is None:
        warnings.append(
            "Measure pitch across several intervals to separate same-diameter candidates, or print a comparison sheet."
        )
    if taper is not None:
        taper_error = 2 * diameter_uncertainty / (separation * factor)
        if taper > taper_error:
            form = "tapered"
        else:
            warnings.append(
                "The measured taper is within diameter uncertainty; it does not establish a parallel thread."
            )
    candidates = []
    for record in _records():
        if family != "all" and record["family"] != family:
            continue
        machine = record["kind"] == "machine"
        if form == "tapered" and (machine or record["family"] == "bspp"):
            continue
        if form == "parallel" and record["family"] in ("npt", "nptf"):
            continue
        expected = (
            record["internal_minor_mm"] if side == "internal" else record["diameter_mm"]
        )
        use_diameter = machine and side != "unsure" and diameter is not None
        if not use_diameter and pitch is None:
            continue
        delta_d = diameter - expected if use_diameter else None
        delta_p = pitch - record["pitch_mm"] if pitch is not None else None
        if delta_d is not None and abs(delta_d) > diameter_window + 1e-10:
            continue
        if delta_p is not None and abs(delta_p) > pitch_window + 1e-10:
            continue
        score = sum(
            value
            for value in (
                abs(delta_d) / diameter_window if delta_d is not None else 0,
                abs(delta_p) / pitch_window if delta_p is not None else 0,
            )
        )
        candidates.append(
            {
                **record,
                "delta_d_mm": delta_d,
                "delta_p_mm": delta_p,
                "expected_diameter_mm": expected if side != "unsure" else None,
                "basis": "basic internal minor"
                if side == "internal"
                else "nominal external major",
                "pitch_only": not use_diameter,
                "distance": score,
            }
        )
    candidates.sort(
        key=lambda row: (row["pitch_only"], row["distance"], row["designation"])
    )
    if any(row["kind"] == "pipe" for row in candidates):
        warnings.append(
            "Pipe candidates are PITCH ONLY: diameter-at-measurement-plane data are not implemented. Nominal pipe size is not OD. NPT/NPTF may be inseparable by these readings; BSPT internal form also needs checking."
        )
    usable = pitch is not None or (diameter is not None and side != "unsure")
    status = (
        "incomplete"
        if not usable
        else "no-close-supported-match"
        if not candidates
        else "ambiguous"
        if len(candidates) > 1 or pitch is None or candidates[0]["pitch_only"]
        else "possible-match"
    )
    return {
        "status": status,
        "candidates": candidates,
        "warnings": warnings,
        "equations": equations,
        "diameter_mm": diameter,
        "pitch_mm": pitch,
        "taper": taper,
        "side": side,
        "observations": state,
        "diameter_window_mm": diameter_window,
        "pitch_window_mm": pitch_window,
    }


def comparison_records() -> list[dict[str, Any]]:
    """Return supported pitch/profile records for local printing.

    ---Parameters---

    ---Returns---
    records : list
        JSON-safe nominal records, with provenance and per-operation capabilities.

    ---LaTeX---
    P = 25.4 / TPI

    P: pitch in mm; TPI: threads per inch. Catalog sources: module docstring.
    """
    return list(_records())


def step_model(state_json: str) -> dict[str, Any]:
    r"""Validate a nominal straight-thread specimen for the browser CAD worker.

    ---Parameters---
    state_json : str
        JSON with family, size, hand RH/LH, specimen external/internal, length
        and body_diameter in mm. Explicit blind_coupon acknowledgement required
        when feature is blind. Blank length uses the export-only default 2d.

    ---Returns---
    model : dict
        Physical profile, bounded length, body diameter and representation note.

    ---LaTeX---
    L_0 = 2d
    N = L / P
    V = \pi L \sum_i \Delta x_i (r_i^2 + r_i r_{i+1} + r_{i+1}^2) / (3P)

    L_0: suggested specimen length; d: major diameter; L: model length;
    P: pitch; N: turns. Millimetres throughout. Ends clip partial threads;
    L is not usable full-thread length. V: external solid volume (mm cubed);
    x_i, r_i: axial/radial profile vertices. The internal coupon subtracts this
    swept bore volume from its surrounding cylinder. This identity integrates
    the piecewise linear axial profile over a full angular revolution at each
    height; it also applies to clipped fractional turns.
    This does not model a tolerance class.
    """
    state = json.loads(state_json)
    record = next(
        (
            row
            for row in _records()
            if row["family"] == state.get("family") and row["size"] == state.get("size")
        ),
        None,
    )
    if record is None or not record["capabilities"]["step"]:
        raise ValueError(
            "STEP needs a validated metric or Unified profile. Pipe and supplier profiles are not modeled."
        )
    specimen, hand = state.get("specimen", "external"), state.get("hand", "RH")
    if specimen not in ("external", "internal") or hand not in ("RH", "LH"):
        raise ValueError("Choose a supported specimen and handedness.")
    if state.get("feature") == "blind" and (
        state.get("blind_coupon") is not True or specimen != "internal"
    ):
        raise ValueError(
            "Blind geometry is not supported. Explicitly select a separate through-thread reference coupon."
        )
    model = record["model"]
    diameter, pitch = model["major_diameter_mm"], model["pitch_mm"]
    length = _number(state, "length", 2 * diameter)
    if length < pitch or length / pitch > 20 or length > 250:
        raise ValueError(
            "Use a specimen at least one pitch long, at most 20 turns and at most 250 mm. This limits browser CAD work."
        )
    body = _number(state, "body_diameter", 1.8 * diameter)
    if body > 500:
        raise ValueError("Use a coupon outside diameter at most 500 mm.")
    if specimen == "internal" and body <= 2 * model["sharp_radius_mm"] + 0.2:
        raise ValueError(
            "Coupon body must leave more than 0.1 mm wall beyond the thread root."
        )
    profile = model[specimen]
    swept_volume = (
        math.pi
        * length
        / pitch
        * sum(
            (x2 - x1) * (r1 * r1 + r1 * r2 + r2 * r2) / 3
            for (x1, r1), (x2, r2) in pairwise(profile)
        )
    )
    expected_volume = (
        math.pi * body * body * length / 4 - swept_volume
        if specimen == "internal"
        else swept_volume
    )
    return {
        **model,
        "designation": record["designation"],
        "source": record["source"],
        "expected_volume_mm3": expected_volume,
        "length_mm": length,
        "body_diameter_mm": body,
        "hand": hand,
        "specimen": specimen,
        "length_is_default": state.get("length") in (None, ""),
        "end_condition": "Square clipped ends; partial turns, no runout or entry chamfer.",
        "tolerance_requirement": state.get("fit", "Unspecified"),
    }
