"""Structural engineering helpers for beam bending tools."""

from __future__ import annotations

from math import pi
from typing import Any, Dict, List


def _require_dimension(dimensions: dict[str, Any], name: str) -> float:
    """Pull a positive float dimension from the provided mapping."""
    try:
        value = float(dimensions[name])
    except KeyError as exc:
        raise ValueError(f"Missing dimension '{name}' for the selected section.") from exc
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Dimension '{name}' must be a real number.") from exc

    if value <= 0:
        raise ValueError(f"Dimension '{name}' must be greater than zero.")
    return value


def compute_section_properties(
    section_type: str,
    section_dimensions: dict[str, Any],
) -> dict[str, float]:
    """
    Compute geometric properties for common beam cross-sections.

    ---Parameters---
    section_type : str
        Identifier for the cross-section. Supported options are
        ``"rectangular"``, ``"circular_solid"``, ``"circular_hollow"``,
        ``"i_beam"``, and ``"custom"``.
    section_dimensions : dict[str, Any]
        Mapping of the dimensional inputs required for the chosen section.
        All lengths must be supplied in metres. For ``"custom"`` sections,
        provide ``moment_of_inertia`` (m^4) together with either
        ``section_modulus`` (m^3) or both ``c_top`` and ``c_bottom`` (m).

    ---Returns---
    area : float
        Cross-sectional area in square metres (m²).
    ix : float
        Second moment of area about the strong axis in metres to the fourth (m⁴).
    section_modulus_top : float
        Section modulus to the top fibre in cubic metres (m³).
    section_modulus_bottom : float
        Section modulus to the bottom fibre in cubic metres (m³).
    c_top : float
        Distance from centroid to extreme top fibre in metres (m).
    c_bottom : float
        Distance from centroid to extreme bottom fibre in metres (m).
    """

    if not isinstance(section_dimensions, dict):
        raise ValueError("section_dimensions must be a dictionary of named dimensions.")

    section_label = section_type.lower().strip()

    if section_label == "rectangular":
        width = _require_dimension(section_dimensions, "width")
        depth = _require_dimension(section_dimensions, "depth")
        area = width * depth
        ix = width * depth**3 / 12.0
        c_top = depth / 2.0
        c_bottom = depth / 2.0

    elif section_label == "circular_solid":
        diameter = _require_dimension(section_dimensions, "diameter")
        area = pi * diameter**2 / 4.0
        ix = pi * diameter**4 / 64.0
        c_top = diameter / 2.0
        c_bottom = diameter / 2.0

    elif section_label == "circular_hollow":
        outer = _require_dimension(section_dimensions, "outer_diameter")
        inner = _require_dimension(section_dimensions, "inner_diameter")
        if inner >= outer:
            raise ValueError("Inner diameter must be smaller than outer diameter.")
        area = pi * (outer**2 - inner**2) / 4.0
        ix = pi * (outer**4 - inner**4) / 64.0
        c_top = outer / 2.0
        c_bottom = outer / 2.0

    elif section_label == "i_beam":
        depth = _require_dimension(section_dimensions, "overall_depth")
        flange_width = _require_dimension(section_dimensions, "flange_width")
        flange_thickness = _require_dimension(section_dimensions, "flange_thickness")
        web_thickness = _require_dimension(section_dimensions, "web_thickness")

        if 2.0 * flange_thickness >= depth:
            raise ValueError("Flange thicknesses exceed total depth; check inputs.")

        web_height = depth - 2.0 * flange_thickness
        flange_area = flange_width * flange_thickness
        web_area = web_thickness * web_height

        # Neutral axis coincides with mid-depth for symmetric I-beams.
        centroid_offset = depth / 2.0 - flange_thickness / 2.0
        ix_flange = 2.0 * (
            (flange_width * flange_thickness**3) / 12.0
            + flange_area * centroid_offset**2
        )
        ix_web = (web_thickness * web_height**3) / 12.0

        area = 2.0 * flange_area + web_area
        ix = ix_flange + ix_web
        c_top = depth / 2.0
        c_bottom = depth / 2.0

    elif section_label == "custom":
        moment_of_inertia = _require_dimension(section_dimensions, "moment_of_inertia")
        section_modulus = section_dimensions.get("section_modulus")
        c_top = section_dimensions.get("c_top")
        c_bottom = section_dimensions.get("c_bottom")

        if section_modulus is not None:
            section_modulus = float(section_modulus)
            if section_modulus <= 0:
                raise ValueError("section_modulus must be greater than zero.")
            c_top = moment_of_inertia / section_modulus
            c_bottom = c_top if c_bottom is None else float(c_bottom)

        if c_top is None or c_bottom is None:
            raise ValueError(
                "Custom sections require either section_modulus or both c_top and c_bottom."
            )

        c_top = float(c_top)
        c_bottom = float(c_bottom)
        if c_top <= 0 or c_bottom <= 0:
            raise ValueError("Distances c_top and c_bottom must be positive.")

        area = float(section_dimensions.get("area", 0.0))
        ix = moment_of_inertia

    else:
        raise ValueError(f"Unsupported section type '{section_type}'.")

    section_modulus_top = ix / c_top
    section_modulus_bottom = ix / c_bottom

    return {
        "area": area,
        "ix": ix,
        "section_modulus_top": section_modulus_top,
        "section_modulus_bottom": section_modulus_bottom,
        "c_top": c_top,
        "c_bottom": c_bottom,
    }


def beam_deflection_analysis(
    section_type: str,
    section_dimensions: dict[str, Any],
    span: float,
    elastic_modulus: float,
    load_case: str,
    load_value: float,
    load_position: float | None = None,
    num_points: int = 101,
) -> dict[str, Any]:
    """
    Calculate elastic beam response for common load/support cases.

    ---Parameters---
    section_type : str
        Cross-section descriptor passed through to :func:`compute_section_properties`.
    section_dimensions : dict[str, Any]
        Dimensional inputs (metres) required by the section calculator.
    span : float
        Clear span or free length of the beam in metres.
    elastic_modulus : float
        Young's modulus of the material in pascals (Pa). Must be positive.
    load_case : str
        Loading condition identifier. Supported values:
        ``"simply_supported_point_midspan"``, ``"simply_supported_uniform"``,
        ``"cantilever_point_free_end"``, and ``"cantilever_uniform"``.
    load_value : float
        Magnitude of the applied load. Use newtons (N) for point loads and
        newtons per metre (N/m) for distributed loads.
    load_position : float, optional
        Reserved for future load cases requiring positioning. Ignored for the
        current scenarios.
    num_points : int, optional
        Number of stations used to discretise the span for diagrams (default 101).

    ---Returns---
    max_deflection : float
        Maximum downward deflection in metres (m).
    max_deflection_position : float
        Position along the span where the maximum deflection occurs (m).
    max_bending_moment : float
        Maximum bending moment magnitude in newton-metres (N·m).
    max_shear_force : float
        Maximum shear force magnitude in newtons (N).
    extreme_fiber_stress : float
        Bending stress at the most distant fibre in pascals (Pa).

    ---LaTeX---
    y_{\\text{ss,mid}}(x) = \\frac{P x \\left(3 L^2 - 4 x^2\\right)}{48 E I}
    y_{\\text{ss,udl}}(x) = \\frac{w x \\left(L^3 - 2 L x^2 + x^3\\right)}{24 E I}
    y_{\\text{cantilever,point}}(x) = \\frac{P x^2 (3L - x)}{6 E I}
    y_{\\text{cantilever,udl}}(x) = \\frac{w x^2 \\left(6 L^2 - 4 L x + x^2\\right)}{24 E I}

    ---References---
    Gere, J. M., & Timoshenko, S. P. (1997). *Mechanics of Materials* (4th ed.).
    McGraw-Hill.
    """

    try:
        span = float(span)
        elastic_modulus = float(elastic_modulus)
        load_value = float(load_value)
    except (TypeError, ValueError) as exc:
        return {"error": f"All scalar inputs must be real numbers: {exc}"}

    if span <= 0:
        return {"error": "Span must be greater than zero."}
    if elastic_modulus <= 0:
        return {"error": "Elastic modulus must be greater than zero."}
    if num_points < 3:
        return {"error": "Use at least three points to build response diagrams."}

    try:
        section_props = compute_section_properties(section_type, section_dimensions)
    except ValueError as exc:
        return {"error": str(exc)}

    inertia = section_props["ix"]
    if inertia <= 0:
        return {"error": "Moment of inertia must be greater than zero."}

    c_extreme = max(section_props["c_top"], section_props["c_bottom"])

    load_key = load_case.strip().lower()
    x_vals = [span * i / (num_points - 1) for i in range(num_points)]
    deflections: List[float] = []
    moments: List[float] = []
    shears: List[float] = []

    if load_key == "simply_supported_point_midspan":
        if load_value <= 0:
            return {"error": "Point load must be greater than zero."}
        reaction = load_value / 2.0
        mid_span = span / 2.0

        for x in x_vals:
            if x <= mid_span:
                shear = reaction
                moment = reaction * x
                deflection = (
                    load_value * x * (3.0 * span**2 - 4.0 * x**2)
                ) / (48.0 * elastic_modulus * inertia)
            else:
                shear = -reaction
                moment = reaction * x - load_value * (x - mid_span)
                xi = span - x
                deflection = (
                    load_value * xi * (3.0 * span**2 - 4.0 * xi**2)
                ) / (48.0 * elastic_modulus * inertia)

            shears.append(shear)
            moments.append(moment)
            deflections.append(deflection)

        max_moment_formula = "M_{max} = \\frac{P L}{4}"
        max_deflection_formula = "\\delta_{max} = \\frac{P L^3}{48 E I}"
        max_shear_formula = "V_{max} = \\frac{P}{2}"

    elif load_key == "simply_supported_uniform":
        if load_value <= 0:
            return {"error": "Distributed load must be greater than zero."}
        reaction = load_value * span / 2.0

        for x in x_vals:
            shear = reaction - load_value * x
            moment = load_value * x * (span - x) / 2.0
            deflection = (
                load_value * x * (span**3 - 2.0 * span * x**2 + x**3)
            ) / (24.0 * elastic_modulus * inertia)

            shears.append(shear)
            moments.append(moment)
            deflections.append(deflection)

        max_moment_formula = "M_{max} = \\frac{w L^2}{8}"
        max_deflection_formula = "\\delta_{max} = \\frac{5 w L^4}{384 E I}"
        max_shear_formula = "V_{max} = \\frac{w L}{2}"

    elif load_key == "cantilever_point_free_end":
        if load_value <= 0:
            return {"error": "Point load must be greater than zero."}

        for x in x_vals:
            shear = load_value
            moment = load_value * (span - x)
            deflection = (
                load_value * x**2 * (3.0 * span - x)
            ) / (6.0 * elastic_modulus * inertia)

            shears.append(shear)
            moments.append(moment)
            deflections.append(deflection)

        max_moment_formula = "M_{max} = P L"
        max_deflection_formula = "\\delta_{max} = \\frac{P L^3}{3 E I}"
        max_shear_formula = "V_{max} = P"

    elif load_key == "cantilever_uniform":
        if load_value <= 0:
            return {"error": "Distributed load must be greater than zero."}

        for x in x_vals:
            shear = load_value * (span - x)
            moment = load_value * (span - x) ** 2 / 2.0
            deflection = (
                load_value * x**2 * (6.0 * span**2 - 4.0 * span * x + x**2)
            ) / (24.0 * elastic_modulus * inertia)

            shears.append(shear)
            moments.append(moment)
            deflections.append(deflection)

        max_moment_formula = "M_{max} = \\frac{w L^2}{2}"
        max_deflection_formula = "\\delta_{max} = \\frac{w L^4}{8 E I}"
        max_shear_formula = "V_{max} = w L"

    else:
        return {"error": f"Unsupported load case '{load_case}'."}

    # Determine maximum magnitudes.
    max_deflection_idx, max_deflection_raw = max(
        enumerate(deflections), key=lambda pair: abs(pair[1])
    )
    max_deflection = deflections[max_deflection_idx]
    max_moment = abs(max(moments, key=lambda val: abs(val), default=0.0))
    max_shear = abs(max(shears, key=lambda val: abs(val), default=0.0))

    extreme_fiber_stress = max_moment * c_extreme / inertia

    def format_number(value: float) -> str:
        return f"{value:.3e}"

    load_symbol = "P" if "point" in load_key else "w"
    L_str = format_number(span)
    E_str = format_number(elastic_modulus)
    I_str = format_number(inertia)
    c_str = format_number(c_extreme)

    if load_key == "simply_supported_point_midspan":
        deflection_subst = (
            f"\\frac{{{load_symbol} \\times {L_str}^3}}{{48 \\times {E_str} \\times {I_str}}}"
        )
        moment_subst = f"\\frac{{{load_symbol} \\times {L_str}}}{{4}}"
        shear_subst = f"\\frac{{{load_symbol}}}{{2}}"
    elif load_key == "simply_supported_uniform":
        deflection_subst = (
            f"\\frac{{5 \\times {load_symbol} \\times {L_str}^4}}{{384 \\times {E_str} \\times {I_str}}}"
        )
        moment_subst = f"\\frac{{{load_symbol} \\times {L_str}^2}}{{8}}"
        shear_subst = f"\\frac{{{load_symbol} \\times {L_str}}}{{2}}"
    elif load_key == "cantilever_point_free_end":
        deflection_subst = (
            f"\\frac{{{load_symbol} \\times {L_str}^3}}{{3 \\times {E_str} \\times {I_str}}}"
        )
        moment_subst = f"{load_symbol} \\times {L_str}"
        shear_subst = load_symbol
    else:  # cantilever_uniform
        deflection_subst = (
            f"\\frac{{{load_symbol} \\times {L_str}^4}}{{8 \\times {E_str} \\times {I_str}}}"
        )
        moment_subst = f"\\frac{{{load_symbol} \\times {L_str}^2}}{{2}}"
        shear_subst = f"{load_symbol} \\times {L_str}"

    results: Dict[str, Any] = {
        "max_deflection": max_deflection,
        "max_deflection_position": x_vals[max_deflection_idx],
        "max_bending_moment": max_moment,
        "max_shear_force": max_shear,
        "extreme_fiber_stress": extreme_fiber_stress,
        "curve": [
            {
                "x": x,
                "deflection": d,
                "moment": m,
                "shear": v,
            }
            for x, d, m, v in zip(x_vals, deflections, moments, shears)
        ],
        "section_properties": section_props,
        "active_formulae": {
            "deflection": max_deflection_formula,
            "moment": max_moment_formula,
            "shear": max_shear_formula,
        },
    }

    results["subst_max_deflection"] = (
        f"{max_deflection_formula} = "
        f"{deflection_subst}"
        f" = {format_number(max_deflection)}"
    )

    results["subst_max_bending_moment"] = (
        f"{max_moment_formula} = "
        f"{moment_subst}"
        f" = {format_number(max_moment)}"
    )

    results["subst_max_shear_force"] = (
        f"{max_shear_formula} = "
        f"{shear_subst}"
        f" = {format_number(max_shear)}"
    )

    results["subst_extreme_fiber_stress"] = (
        "\\sigma_{max} = \\frac{M_{max} c}{I} = "
        f"\\frac{{{format_number(max_moment)} \\times {c_str}}}{{{I_str}}}"
        f" = {format_number(extreme_fiber_stress)}"
    )

    return results
