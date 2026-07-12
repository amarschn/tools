"""Rolling-bearing screening and bore-first catalog selection.

The catalog slice in this module is transcribed from NTN's *Ball and Roller
Bearings* catalog No. 2203/E. Ratings are manufacturer-specific and must not be
treated as interchangeable with similarly dimensioned bearings from another
manufacturer.
"""

from __future__ import annotations

from typing import Any


NTN_CATALOG_INDEX = (
    "https://www.ntnglobal.com/en/products/catalog/en/2203/index.html"
)

TYPE_METADATA: dict[str, dict[str, Any]] = {
    "deep_groove_ball": {
        "label": "Deep-groove ball",
        "life_exponent": 3.0,
        "source_url": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b02.pdf",
        "best_for": "General-purpose radial duty with moderate axial load.",
        "limitation": "Axial capacity and misalignment tolerance are limited.",
    },
    "angular_contact_ball": {
        "label": "Angular-contact ball (30°)",
        "life_exponent": 3.0,
        "source_url": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b04.pdf",
        "best_for": "Combined loads and accurate axial location.",
        "limitation": (
            "Normally used in opposed pairs; arrangement forces are not solved here."
        ),
    },
    "cylindrical_roller": {
        "label": "Cylindrical roller (NU)",
        "life_exponent": 10.0 / 3.0,
        "source_url": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b06.pdf",
        "best_for": "High radial capacity and a floating shaft position.",
        "limitation": "The selected NU series does not support axial load.",
    },
    "tapered_roller": {
        "label": "Tapered roller",
        "life_exponent": 10.0 / 3.0,
        "source_url": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b07.pdf",
        "best_for": "Combined radial and axial load with adjustable clearance.",
        "limitation": (
            "Normally used in opposed pairs; arrangement forces are not solved here."
        ),
    },
    "spherical_roller": {
        "label": "Spherical roller",
        "life_exponent": 10.0 / 3.0,
        "source_url": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b08.pdf",
        "best_for": "Heavy combined load where misalignment is expected.",
        "limitation": "Larger envelope, friction, and cost than simpler bearing types.",
    },
}


def _row(
    designation: str,
    bearing_type: str,
    bore_mm: float,
    outside_diameter_mm: float,
    width_mm: float,
    dynamic_rating_kn: float,
    static_rating_kn: float,
    grease_rpm: float,
    oil_rpm: float,
    mass_kg: float,
    **factors: float,
) -> dict[str, Any]:
    """Build one normalized manufacturer catalog record.

    ---Parameters---
    designation : str
        NTN bearing designation as printed in catalog No. 2203/E.
    bearing_type : str
        Internal bearing-family identifier.
    bore_mm : float
        Nominal bore diameter in millimetres.
    outside_diameter_mm : float
        Nominal outside diameter in millimetres.
    width_mm : float
        Catalog width or overall width in millimetres.
    dynamic_rating_kn : float
        Basic dynamic load rating in kilonewtons.
    static_rating_kn : float
        Basic static load rating in kilonewtons.
    grease_rpm : float
        Catalog grease-lubricated allowable speed in revolutions per minute.
    oil_rpm : float
        Catalog oil-lubricated allowable speed in revolutions per minute.
    mass_kg : float
        Catalog bearing mass in kilograms.
    factors : float
        Manufacturer load factors required by the selected bearing family.

    ---Returns---
    catalog_record : dict
        Normalized catalog row with SI load ratings and source metadata.

    ---LaTeX---
    C_{N} = 1000 C_{kN}
    C_{0,N} = 1000 C_{0,kN}
    """
    return {
        "designation": designation,
        "bearing_type": bearing_type,
        "bore_mm": float(bore_mm),
        "outside_diameter_mm": float(outside_diameter_mm),
        "width_mm": float(width_mm),
        "dynamic_rating_n": dynamic_rating_kn * 1000.0,
        "static_rating_n": static_rating_kn * 1000.0,
        "grease_speed_rpm": float(grease_rpm),
        "oil_speed_rpm": float(oil_rpm),
        "mass_kg": float(mass_kg),
        "manufacturer": "NTN",
        "catalog": "Ball and Roller Bearings, No. 2203/E",
        "source_url": TYPE_METADATA[bearing_type]["source_url"],
        **factors,
    }


BEARING_CATALOG: tuple[dict[str, Any], ...] = (
    # NTN 62 series deep-groove ball bearings.
    _row(
        "6205", "deep_groove_ball", 25, 52, 15, 15.5, 7.85,
        13000, 15000, 0.128, f0=13.9,
    ),
    _row(
        "6206", "deep_groove_ball", 30, 62, 16, 21.6, 11.3,
        11000, 13000, 0.199, f0=13.8,
    ),
    _row(
        "6207", "deep_groove_ball", 35, 72, 17, 28.4, 15.3,
        9800, 11000, 0.288, f0=13.8,
    ),
    _row(
        "6208", "deep_groove_ball", 40, 80, 18, 32.5, 17.8,
        8700, 10000, 0.366, f0=14.0,
    ),
    _row(
        "6209", "deep_groove_ball", 45, 85, 19, 36.0, 20.4,
        7800, 9200, 0.398, f0=14.1,
    ),
    _row(
        "6210", "deep_groove_ball", 50, 90, 20, 39.0, 23.2,
        7100, 8300, 0.454, f0=14.4,
    ),
    # NTN 30-degree 72 series single-row angular-contact ball bearings.
    _row(
        "7205", "angular_contact_ball", 25, 52, 15, 18.0, 10.3,
        14000, 19000, 0.125, e=0.80, y2=0.76,
    ),
    _row(
        "7206", "angular_contact_ball", 30, 62, 16, 24.9, 14.8,
        12000, 16000, 0.193, e=0.80, y2=0.76,
    ),
    _row(
        "7207", "angular_contact_ball", 35, 72, 17, 33.0, 20.1,
        11000, 14000, 0.281, e=0.80, y2=0.76,
    ),
    _row(
        "7208", "angular_contact_ball", 40, 80, 18, 39.0, 25.1,
        9600, 13000, 0.355, e=0.80, y2=0.76,
    ),
    _row(
        "7209", "angular_contact_ball", 45, 85, 19, 44.0, 28.7,
        8700, 12000, 0.404, e=0.80, y2=0.76,
    ),
    _row(
        "7210", "angular_contact_ball", 50, 90, 20, 45.5, 31.5,
        7900, 10000, 0.457, e=0.80, y2=0.76,
    ),
    # NTN NU-EA cylindrical roller bearings.
    _row("NU205EA", "cylindrical_roller", 25, 52, 15, 34.5, 27.7, 13000, 18000, 0.151),
    _row("NU206EA", "cylindrical_roller", 30, 62, 16, 46.0, 37.5, 11000, 15600, 0.226),
    _row("NU207EA", "cylindrical_roller", 35, 72, 17, 59.5, 50.0, 9500, 13200, 0.327),
    _row("NU208EA", "cylindrical_roller", 40, 80, 18, 66.0, 55.5, 8500, 12000, 0.426),
    _row("NU209EA", "cylindrical_roller", 45, 85, 19, 74.5, 66.5, 7600, 10800, 0.495),
    _row("NU210EA", "cylindrical_roller", 50, 90, 20, 81.5, 76.5, 6900, 9700, 0.503),
    # NTN 4T-320 metric tapered roller bearings.
    _row(
        "4T-32005X", "tapered_roller", 25, 47, 15, 31.0, 33.5,
        7900, 11000, 0.113, e=0.43, y2=1.39, y0=0.77,
    ),
    _row(
        "4T-32006X", "tapered_roller", 30, 55, 17, 41.5, 46.0,
        6900, 9200, 0.172, e=0.43, y2=1.39, y0=0.77,
    ),
    _row(
        "4T-32007X", "tapered_roller", 35, 62, 18, 46.0, 52.5,
        6100, 8100, 0.223, e=0.45, y2=1.32, y0=0.73,
    ),
    _row(
        "4T-32008X", "tapered_roller", 40, 68, 19, 55.5, 65.5,
        5300, 7100, 0.272, e=0.38, y2=1.58, y0=0.87,
    ),
    _row(
        "4T-32009X", "tapered_roller", 45, 75, 20, 64.0, 76.5,
        4800, 6400, 0.341, e=0.39, y2=1.53, y0=0.84,
    ),
    _row(
        "4T-32010X", "tapered_roller", 50, 80, 20, 69.5, 88.0,
        4400, 5800, 0.373, e=0.42, y2=1.42, y0=0.78,
    ),
    # NTN 222-EA spherical roller bearings.
    _row(
        "22205EAW33", "spherical_roller", 25, 52, 18, 57.3, 46.1,
        10400, 13000, 0.173, e=0.34, y1=2.00, y2=2.98, y0=1.96,
    ),
    _row(
        "22206EAW33", "spherical_roller", 30, 62, 20, 75.7, 64.5,
        8800, 11000, 0.278, e=0.31, y1=2.15, y2=3.20, y0=2.10,
    ),
    _row(
        "22207EAW33", "spherical_roller", 35, 72, 23, 100.0, 92.0,
        7500, 9400, 0.438, e=0.31, y1=2.21, y2=3.29, y0=2.16,
    ),
    _row(
        "22208EAD1", "spherical_roller", 40, 80, 23, 116.0, 105.0,
        6800, 8500, 0.528, e=0.27, y1=2.47, y2=3.67, y0=2.41,
    ),
    _row(
        "22209EAD1", "spherical_roller", 45, 85, 23, 121.0, 113.0,
        6100, 7700, 0.572, e=0.26, y1=2.64, y2=3.93, y0=2.58,
    ),
    _row(
        "22210EAD1", "spherical_roller", 50, 90, 23, 130.0, 124.0,
        5700, 7200, 0.614, e=0.24, y1=2.84, y2=4.23, y0=2.78,
    ),
)


DEEP_GROOVE_FACTORS: tuple[tuple[float, float, float], ...] = (
    (0.172, 0.19, 2.30),
    (0.345, 0.22, 1.99),
    (0.689, 0.26, 1.71),
    (1.03, 0.28, 1.55),
    (1.38, 0.30, 1.45),
    (2.07, 0.34, 1.31),
    (3.45, 0.38, 1.15),
    (5.17, 0.42, 1.04),
    (6.89, 0.44, 1.00),
)


def list_bore_sizes() -> list[float]:
    r"""Return the distinct bore sizes in the embedded catalog slice.

    ---Parameters---

    ---Returns---
    bore_sizes_mm : list
        Sorted nominal bore diameters in millimetres.

    ---LaTeX---
    D_{bore} \in \{25, 30, 35, 40, 45, 50\}\,\mathrm{mm}
    """
    return sorted({row["bore_mm"] for row in BEARING_CATALOG})


def get_bearing_type_metadata() -> dict[str, dict[str, Any]]:
    r"""Return display names, use guidance, and source links by bearing type.

    ---Parameters---

    ---Returns---
    bearing_type_metadata : dict
        A copy of the user-facing metadata for each supported family.

    ---LaTeX---
    p = 3\;\mathrm{(ball)},\qquad p = \frac{10}{3}\;\mathrm{(roller)}
    """
    return {key: dict(value) for key, value in TYPE_METADATA.items()}


def _interpolate_deep_groove_factors(q_value: float) -> tuple[float, float]:
    r"""Interpolate NTN deep-groove limiting ratio and axial factor.

    ---Parameters---
    q_value : float
        Dimensionless catalog argument ``f0 * Fa / C0``.

    ---Returns---
    factors : tuple
        Interpolated ``(e, Y)`` values, clamped to the catalog table bounds.

    ---LaTeX---
    q = \frac{f_0 F_a}{C_0}
    Y = Y_1 + (Y_2-Y_1)\frac{q-q_1}{q_2-q_1}
    """
    if q_value <= DEEP_GROOVE_FACTORS[0][0]:
        return DEEP_GROOVE_FACTORS[0][1:]
    if q_value >= DEEP_GROOVE_FACTORS[-1][0]:
        return DEEP_GROOVE_FACTORS[-1][1:]
    for lower, upper in zip(DEEP_GROOVE_FACTORS, DEEP_GROOVE_FACTORS[1:]):
        if lower[0] <= q_value <= upper[0]:
            fraction = (q_value - lower[0]) / (upper[0] - lower[0])
            e_value = lower[1] + fraction * (upper[1] - lower[1])
            y_value = lower[2] + fraction * (upper[2] - lower[2])
            return e_value, y_value
    raise RuntimeError("Unable to interpolate deep-groove load factors.")


def equivalent_dynamic_load(
    radial_load_n: float,
    axial_load_n: float,
    bearing: dict[str, Any],
) -> dict[str, float]:
    r"""Calculate the catalog equivalent dynamic radial load for one bearing.

    NTN catalog load factors are applied by family. For NU cylindrical roller
    bearings, any nonzero axial load is rejected because this catalog series is
    a floating radial bearing. Angular-contact and tapered-bearing loads must
    already represent the load at one bearing after arrangement analysis.

    ---Parameters---
    radial_load_n : float
        Non-negative radial load at one bearing in newtons.
    axial_load_n : float
        Non-negative axial load at one bearing in newtons.
    bearing : dict
        Normalized catalog row from ``BEARING_CATALOG``.

    ---Returns---
    equivalent_load : dict
        Equivalent load ``P`` and the applied ``X``, ``Y``, ``e``, and load ratio.

    ---LaTeX---
    P = X F_r + Y F_a
    """
    if radial_load_n < 0 or axial_load_n < 0:
        raise ValueError("Radial and axial loads must be non-negative.")
    if radial_load_n == 0 and axial_load_n == 0:
        raise ValueError("At least one applied load must be greater than zero.")

    bearing_type = bearing["bearing_type"]
    ratio = axial_load_n / radial_load_n if radial_load_n else float("inf")
    e_value = float(bearing.get("e", 0.0))
    x_value = 1.0
    y_value = 0.0

    if bearing_type == "deep_groove_ball":
        q_value = bearing["f0"] * axial_load_n / bearing["static_rating_n"]
        e_value, combined_y = _interpolate_deep_groove_factors(q_value)
        if ratio > e_value:
            x_value, y_value = 0.56, combined_y
    elif bearing_type == "angular_contact_ball":
        if ratio > e_value:
            x_value, y_value = 0.39, bearing["y2"]
    elif bearing_type == "cylindrical_roller":
        if axial_load_n > 0:
            raise ValueError(
                "NU cylindrical roller bearings do not support axial load."
            )
    elif bearing_type == "tapered_roller":
        if ratio > e_value:
            x_value, y_value = 0.40, bearing["y2"]
    elif bearing_type == "spherical_roller":
        if ratio <= e_value:
            x_value, y_value = 1.0, bearing["y1"]
        else:
            x_value, y_value = 0.67, bearing["y2"]
    else:
        raise ValueError(f"Unsupported bearing type: {bearing_type}")

    load_n = x_value * radial_load_n + y_value * axial_load_n
    return {
        "load_n": load_n,
        "x_factor": x_value,
        "y_factor": y_value,
        "e_limit": e_value,
        "axial_radial_ratio": ratio,
    }


def equivalent_static_load(
    radial_load_n: float,
    axial_load_n: float,
    bearing: dict[str, Any],
) -> dict[str, float]:
    r"""Calculate NTN equivalent static radial load for one catalog bearing.

    ---Parameters---
    radial_load_n : float
        Non-negative radial load at one bearing in newtons.
    axial_load_n : float
        Non-negative axial load at one bearing in newtons.
    bearing : dict
        Normalized catalog row from ``BEARING_CATALOG``.

    ---Returns---
    equivalent_static_load : dict
        Static equivalent load ``P0`` and the applied ``X0`` and ``Y0`` factors.

    ---LaTeX---
    P_0 = \max(X_0 F_r + Y_0 F_a, F_r)
    """
    if radial_load_n < 0 or axial_load_n < 0:
        raise ValueError("Radial and axial loads must be non-negative.")
    bearing_type = bearing["bearing_type"]
    if bearing_type == "deep_groove_ball":
        x0, y0 = 0.60, 0.50
    elif bearing_type == "angular_contact_ball":
        x0, y0 = 0.50, 0.33
    elif bearing_type == "cylindrical_roller":
        if axial_load_n > 0:
            raise ValueError(
                "NU cylindrical roller bearings do not support axial load."
            )
        x0, y0 = 1.0, 0.0
    elif bearing_type == "tapered_roller":
        x0, y0 = 0.50, bearing["y0"]
    elif bearing_type == "spherical_roller":
        x0, y0 = 1.0, bearing["y0"]
    else:
        raise ValueError(f"Unsupported bearing type: {bearing_type}")
    load_n = max(x0 * radial_load_n + y0 * axial_load_n, radial_load_n)
    return {"load_n": load_n, "x0_factor": x0, "y0_factor": y0}


def basic_rating_life_hours(
    dynamic_rating_n: float,
    equivalent_dynamic_load_n: float,
    speed_rpm: float,
    life_exponent: float,
) -> dict[str, float]:
    r"""Calculate ISO-style basic rating life at 90 percent reliability.

    This is the catalog basic rating life, not a service-life prediction. It
    excludes lubrication quality, contamination, mounting, fits, temperature,
    misalignment, and modified-life factors.

    ---Parameters---
    dynamic_rating_n : float
        Manufacturer basic dynamic load rating ``C`` in newtons.
    equivalent_dynamic_load_n : float
        Equivalent dynamic radial load ``P`` in newtons.
    speed_rpm : float
        Constant rotational speed in revolutions per minute.
    life_exponent : float
        Exponent ``3`` for ball bearings or ``10/3`` for roller bearings.

    ---Returns---
    rating_life : dict
        Basic rating life in millions of revolutions, revolutions, and hours.

    ---LaTeX---
    L_{10} = \left(\frac{C}{P}\right)^p
    L_{10h} = \frac{10^6}{60n}\left(\frac{C}{P}\right)^p
    """
    if dynamic_rating_n <= 0 or equivalent_dynamic_load_n <= 0:
        raise ValueError("Dynamic rating and equivalent load must be positive.")
    if speed_rpm <= 0:
        raise ValueError("Speed must be positive.")
    if life_exponent <= 0:
        raise ValueError("Life exponent must be positive.")
    life_mrev = (dynamic_rating_n / equivalent_dynamic_load_n) ** life_exponent
    life_revolutions = life_mrev * 1_000_000.0
    life_hours = life_revolutions / (60.0 * speed_rpm)
    return {
        "life_million_revolutions": life_mrev,
        "life_revolutions": life_revolutions,
        "life_hours": life_hours,
    }


def evaluate_bearing(
    bearing: dict[str, Any],
    radial_load_n: float,
    axial_load_n: float,
    speed_rpm: float,
    lubrication: str,
    required_life_hours: float,
    required_static_safety_factor: float,
) -> dict[str, Any]:
    r"""Evaluate one catalog bearing against load, life, static, and speed checks.

    ---Parameters---
    bearing : dict
        Normalized catalog row from ``BEARING_CATALOG``.
    radial_load_n : float
        Radial load at one bearing in newtons.
    axial_load_n : float
        Axial load at one bearing in newtons.
    speed_rpm : float
        Operating speed in revolutions per minute.
    lubrication : str
        ``grease`` or ``oil`` for the catalog speed column.
    required_life_hours : float
        User-required basic rating life in operating hours.
    required_static_safety_factor : float
        User-required ratio ``C0/P0``.

    ---Returns---
    candidate : dict
        Catalog data, calculated loads and life, pass/fail checks, and derivations.

    ---LaTeX---
    s_0 = \frac{C_0}{P_0}
    m_n = \frac{n_{lim}}{n}
    """
    result = dict(bearing)
    result["type_label"] = TYPE_METADATA[bearing["bearing_type"]]["label"]
    result["warnings"] = []
    if bearing["bearing_type"] in {"angular_contact_ball", "tapered_roller"}:
        result["warnings"].append(
            "Evaluate the opposed bearing arrangement and induced axial forces "
            "before final selection."
        )
    try:
        dynamic = equivalent_dynamic_load(radial_load_n, axial_load_n, bearing)
        static = equivalent_static_load(radial_load_n, axial_load_n, bearing)
    except ValueError as error:
        result.update(
            {
                "applicable": False,
                "qualified": False,
                "status": "not_applicable",
                "status_reason": str(error),
                "warnings": result["warnings"] + [str(error)],
            }
        )
        return result

    life = basic_rating_life_hours(
        bearing["dynamic_rating_n"],
        dynamic["load_n"],
        speed_rpm,
        TYPE_METADATA[bearing["bearing_type"]]["life_exponent"],
    )
    static_safety = bearing["static_rating_n"] / static["load_n"]
    speed_limit = bearing[f"{lubrication}_speed_rpm"]
    speed_margin = speed_limit / speed_rpm
    formula_limit = min(
        bearing["static_rating_n"], 0.50 * bearing["dynamic_rating_n"]
    )
    life_formula_valid = dynamic["load_n"] <= formula_limit
    checks = {
        "life": life["life_hours"] >= required_life_hours,
        "static": static_safety >= required_static_safety_factor,
        "speed": speed_margin >= 1.0,
        "life_formula_range": life_formula_valid,
    }
    hard_failure = (
        static_safety < 1.0 or speed_margin < 1.0 or not life_formula_valid
    )
    qualified = all(checks.values())
    status = (
        "acceptable"
        if qualified
        else ("unacceptable" if hard_failure else "marginal")
    )
    if not life_formula_valid:
        result["warnings"].append(
            "Equivalent load exceeds NTN's stated basic-life formula range."
        )
    result.update(dynamic)
    result.update(
        {
            "static_load_n": static["load_n"],
            "x0_factor": static["x0_factor"],
            "y0_factor": static["y0_factor"],
            **life,
            "static_safety_factor": static_safety,
            "speed_limit_rpm": speed_limit,
            "speed_margin": speed_margin,
            "life_formula_limit_n": formula_limit,
            "life_formula_valid": life_formula_valid,
            "checks": checks,
            "applicable": True,
            "qualified": qualified,
            "status": status,
            "status_reason": (
                "Meets all screening requirements."
                if qualified
                else "Review the failed screening checks."
            ),
            "subst_equivalent_load": (
                f"P = XF_r + YF_a = {dynamic['x_factor']:.2f}({radial_load_n:.0f}) "
                f"+ {dynamic['y_factor']:.2f}({axial_load_n:.0f}) = "
                f"{dynamic['load_n']:.0f}\\,\\mathrm{{N}}"
            ),
            "subst_life_hours": (
                f"L_{{10h}} = \\frac{{10^6}}{{60({speed_rpm:.0f})}}"
                f"\\left(\\frac{{{bearing['dynamic_rating_n']:.0f}}}"
                f"{{{dynamic['load_n']:.0f}}}\\right)^"
                f"{{{TYPE_METADATA[bearing['bearing_type']]['life_exponent']:.3g}}} "
                f"= {life['life_hours']:.0f}\\,\\mathrm{{h}}"
            ),
            "subst_static_safety": (
                f"s_0 = \\frac{{C_0}}{{P_0}} = "
                f"\\frac{{{bearing['static_rating_n']:.0f}}}"
                f"{{{static['load_n']:.0f}}} = {static_safety:.2f}"
            ),
        }
    )
    return result


def _selection_rank(candidate: dict[str, Any], load_ratio: float) -> tuple[float, ...]:
    r"""Build a transparent heuristic rank for qualifying candidates.

    The rank favors general-purpose deep-groove bearings at low axial ratios and
    combined-load types at higher axial ratios, then smaller envelopes and mass.

    ---Parameters---
    candidate : dict
        Evaluated and applicable candidate bearing.
    load_ratio : float
        Applied axial-to-radial load ratio.

    ---Returns---
    ranking : tuple
        Ascending family-suitability, outside-diameter, width, and mass values.

    ---LaTeX---
    R = (r_{family}, D, B, m)
    """
    bearing_type = candidate["bearing_type"]
    if load_ratio > 0.25:
        preference = {
            "angular_contact_ball": 0,
            "tapered_roller": 0,
            "spherical_roller": 1,
            "deep_groove_ball": 2,
            "cylindrical_roller": 9,
        }
    else:
        preference = {
            "deep_groove_ball": 0,
            "cylindrical_roller": 1,
            "angular_contact_ball": 2,
            "tapered_roller": 2,
            "spherical_roller": 3,
        }
    return (
        float(preference[bearing_type]),
        candidate["outside_diameter_mm"],
        candidate["width_mm"],
        candidate["mass_kg"],
    )


def _parse_types(bearing_types_csv: str) -> list[str]:
    r"""Parse and validate the comma-separated bearing-family filter.

    ---Parameters---
    bearing_types_csv : str
        Comma-separated internal type keys or the word ``all``.

    ---Returns---
    bearing_types : list
        Validated bearing-family keys in repository display order.

    ---LaTeX---
    T_{selected} \subseteq T_{catalog}
    """
    if not isinstance(bearing_types_csv, str):
        raise ValueError("Bearing types must be supplied as comma-separated text.")
    requested = [item.strip() for item in bearing_types_csv.split(",") if item.strip()]
    if not requested or "all" in requested:
        return list(TYPE_METADATA)
    unknown = sorted(set(requested) - set(TYPE_METADATA))
    if unknown:
        raise ValueError(f"Unsupported bearing type(s): {', '.join(unknown)}")
    return [key for key in TYPE_METADATA if key in requested]


def select_bearings(
    radial_load_n: float,
    axial_load_n: float,
    speed_rpm: float,
    bore_mm: float,
    bearing_types_csv: str = "all",
    lubrication: str = "grease",
    required_life_hours: float = 20000.0,
    required_static_safety_factor: float = 1.0,
) -> dict[str, Any]:
    r"""Screen same-bore NTN bearing types for a specified constant duty point.

    The tool is a concept selector, not a final bearing or shaft-arrangement
    design. Applied loads must be reactions at one bearing. Basic L10 life is a
    90-percent-reliability fatigue metric and does not include modified-life or
    application factors.

    ---Parameters---
    radial_load_n : float
        Constant radial load at one bearing in newtons.
    axial_load_n : float
        Constant axial load at one bearing in newtons.
    speed_rpm : float
        Constant shaft speed in revolutions per minute.
    bore_mm : float
        Required nominal bearing bore in millimetres.
    bearing_types_csv : str
        Comma-separated family keys or ``all``.
    lubrication : str
        Catalog allowable-speed basis, either ``grease`` or ``oil``.
    required_life_hours : float
        Minimum requested basic rating life in operating hours.
    required_static_safety_factor : float
        Minimum requested basic static safety factor ``C0/P0``.

    ---Returns---
    status : str
        Overall screening status: acceptable, marginal, or unacceptable.
    recommendation : dict
        Top screening candidate and the explicit basis for its ranking.
    candidates : list
        Evaluated same-bore catalog candidates.
    type_summary : list
        Compact comparison data for result cards and tables.
    duty_point : dict
        Normalized user inputs and axial-to-radial load ratio.
    life_chart : dict
        Designations, calculated life, and required-life line for plotting.
    load_sensitivity : dict
        L10 life at six proportional load multipliers for applicable candidates.
    recommendations : list
        Engineering cautions and next-step guidance.
    catalog_meta : dict
        Manufacturer, catalog scope, bore sizes, and official references.
    subst_recommendation : str
        Plain-text statement of the recommendation ranking basis.

    ---LaTeX---
    P = XF_r + YF_a
    L_{10h} = \frac{10^6}{60n}\left(\frac{C}{P}\right)^p
    s_0 = \frac{C_0}{P_0}
    """
    numeric_inputs = {
        "radial load": radial_load_n,
        "axial load": axial_load_n,
        "speed": speed_rpm,
        "bore": bore_mm,
        "required life": required_life_hours,
        "required static safety factor": required_static_safety_factor,
    }
    for name, value in numeric_inputs.items():
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name.capitalize()} must be numeric.")
    if radial_load_n < 0 or axial_load_n < 0:
        raise ValueError("Loads must be non-negative.")
    if radial_load_n == 0 and axial_load_n == 0:
        raise ValueError("At least one applied load must be greater than zero.")
    if speed_rpm <= 0 or required_life_hours <= 0:
        raise ValueError("Speed and required life must be positive.")
    if required_static_safety_factor <= 0:
        raise ValueError("Required static safety factor must be positive.")
    if lubrication not in {"grease", "oil"}:
        raise ValueError("Lubrication must be 'grease' or 'oil'.")
    if float(bore_mm) not in list_bore_sizes():
        available = ", ".join(f"{value:g}" for value in list_bore_sizes())
        raise ValueError(f"Bore must be one of: {available} mm.")

    selected_types = _parse_types(bearing_types_csv)
    catalog_rows = [
        row
        for row in BEARING_CATALOG
        if row["bore_mm"] == float(bore_mm)
        and row["bearing_type"] in selected_types
    ]
    if not catalog_rows:
        raise ValueError("No catalog bearings match the selected bore and types.")

    candidates = [
        evaluate_bearing(
            row,
            radial_load_n,
            axial_load_n,
            speed_rpm,
            lubrication,
            required_life_hours,
            required_static_safety_factor,
        )
        for row in catalog_rows
    ]
    load_ratio = axial_load_n / radial_load_n if radial_load_n else float("inf")
    qualified = [candidate for candidate in candidates if candidate["qualified"]]
    applicable = [candidate for candidate in candidates if candidate["applicable"]]

    if qualified:
        top = min(qualified, key=lambda item: _selection_rank(item, load_ratio))
        status = "acceptable"
        basis = (
            "Meets life, static, speed, and formula-range checks; ranked by "
            "family suitability, then the smallest envelope."
        )
    elif applicable:
        top = max(
            applicable,
            key=lambda item: (
                sum(item["checks"].values()),
                min(item["life_hours"] / required_life_hours, 3.0)
                + min(
                    item["static_safety_factor"]
                    / required_static_safety_factor,
                    3.0,
                )
                + min(item["speed_margin"], 3.0),
            ),
        )
        status = "marginal" if not all(
            candidate["status"] == "unacceptable" for candidate in applicable
        ) else "unacceptable"
        basis = (
            "No candidate meets every requirement; this is the closest "
            "screening result."
        )
    else:
        top = candidates[0]
        status = "unacceptable"
        basis = "No selected bearing family is applicable to this duty point."

    type_summary = []
    for candidate in candidates:
        type_summary.append(
            {
                "designation": candidate["designation"],
                "bearing_type": candidate["bearing_type"],
                "type_label": candidate["type_label"],
                "status": candidate["status"],
                "qualified": candidate["qualified"],
                "life_hours": candidate.get("life_hours"),
                "static_safety_factor": candidate.get("static_safety_factor"),
                "speed_margin": candidate.get("speed_margin"),
                "outside_diameter_mm": candidate["outside_diameter_mm"],
                "width_mm": candidate["width_mm"],
            }
        )

    load_multipliers = [0.50, 0.75, 1.00, 1.25, 1.50, 2.00]
    sensitivity_series = []
    for candidate in applicable:
        lives = []
        for multiplier in load_multipliers:
            dynamic = equivalent_dynamic_load(
                radial_load_n * multiplier,
                axial_load_n * multiplier,
                candidate,
            )
            life = basic_rating_life_hours(
                candidate["dynamic_rating_n"],
                dynamic["load_n"],
                speed_rpm,
                TYPE_METADATA[candidate["bearing_type"]]["life_exponent"],
            )
            lives.append(life["life_hours"])
        sensitivity_series.append(
            {"designation": candidate["designation"], "life_hours": lives}
        )

    guidance = [
        "Treat L10 as a 90%-reliability fatigue screen, not guaranteed service life.",
        "Verify lubrication, contamination, fits, internal clearance, temperature, "
        "and mounting with the current manufacturer catalog.",
        "Resolve shaft reactions and bearing-arrangement forces before final "
        "selection.",
    ]
    if axial_load_n > 0 and any(
        item["bearing_type"] == "cylindrical_roller" for item in candidates
    ):
        guidance.append(
            "The NU cylindrical candidate is excluded because the duty includes "
            "axial load."
        )
    if top["bearing_type"] in {"angular_contact_ball", "tapered_roller"}:
        guidance.append(
            "The top family requires an opposed-pair calculation including induced "
            "axial load."
        )
    if top["bearing_type"] == "cylindrical_roller":
        guidance.append(
            "The top NU bearing is a floating-position bearing; provide axial "
            "location elsewhere in the shaft arrangement."
        )

    recommendation = {
        "designation": top["designation"],
        "bearing_type": top["bearing_type"],
        "type_label": top["type_label"],
        "status": top["status"],
        "basis": basis,
        "qualified_count": len(qualified),
        "candidate_count": len(candidates),
    }
    return {
        "status": status,
        "recommendation": recommendation,
        "candidates": candidates,
        "type_summary": type_summary,
        "duty_point": {
            "radial_load_n": radial_load_n,
            "axial_load_n": axial_load_n,
            "speed_rpm": speed_rpm,
            "bore_mm": float(bore_mm),
            "axial_radial_ratio": load_ratio,
            "lubrication": lubrication,
            "required_life_hours": required_life_hours,
            "required_static_safety_factor": required_static_safety_factor,
        },
        "life_chart": {
            "designations": [item["designation"] for item in applicable],
            "life_hours": [item["life_hours"] for item in applicable],
            "required_life_hours": required_life_hours,
        },
        "load_sensitivity": {
            "load_multipliers": load_multipliers,
            "series": sensitivity_series,
        },
        "recommendations": guidance,
        "catalog_meta": {
            "manufacturer": "NTN",
            "catalog": "Ball and Roller Bearings, No. 2203/E",
            "catalog_entry_count": len(BEARING_CATALOG),
            "available_bores_mm": list_bore_sizes(),
            "catalog_index_url": NTN_CATALOG_INDEX,
            "load_life_source_url": (
                "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_a03.pdf"
            ),
            "load_factor_source_url": (
                "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_a04.pdf"
            ),
            "scope": "One representative NTN series per family at 25–50 mm bore.",
        },
        "subst_recommendation": f"{top['designation']}: {basis}",
    }
