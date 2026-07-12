"""Rolling-bearing screening and bore-first catalog selection.

The catalog slice in this module is transcribed from NTN's *Ball and Roller
Bearings* catalog No. 2203/E. Ratings are manufacturer-specific and must not be
treated as interchangeable with similarly dimensioned bearings from another
manufacturer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

NTN_CATALOG_INDEX = "https://www.ntnglobal.com/en/products/catalog/en/2203/index.html"

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


def _load_catalog_data() -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    r"""Load and integrity-check the canonical NTN catalog data file.

    ---Parameters---

    ---Returns---
    catalog_data : tuple
        Catalog metadata followed by an immutable tuple of normalized records.

    ---LaTeX---
    h = \operatorname{SHA256}(\operatorname{canonicalJSON}(records))
    """
    data_path = Path(__file__).with_name("data") / "ntn_2203e_bearings.json"
    if not data_path.exists():
        raise FileNotFoundError(
            "Bearing catalog data is missing: data/ntn_2203e_bearings.json"
        )
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if payload.get("schema_version") != 2 or not isinstance(records, list):
        raise ValueError("Unsupported or malformed bearing catalog schema.")
    if payload.get("record_count") != len(records):
        raise ValueError("Bearing catalog record count does not match its metadata.")
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    actual_hash = hashlib.sha256(encoded).hexdigest()
    if actual_hash != payload.get("sha256"):
        raise ValueError("Bearing catalog checksum validation failed.")
    metadata = {key: value for key, value in payload.items() if key != "records"}
    return metadata, tuple(records)


# The external, checksummed dataset is the runtime source of truth.
CATALOG_DATA, BEARING_CATALOG = _load_catalog_data()


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
        x0, y0 = 0.50, bearing.get("y0", 0.33)
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
    unsupported_lubrication = lubrication in {"solid_special", "none"}
    if unsupported_lubrication:
        reason = "This standard catalog row has no sourced dry/solid-lubricant rating."
        result.update(
            {
                "applicable": False,
                "qualified": False,
                "status": "not_applicable",
                "status_reason": reason,
                "warnings": [reason],
                "lubrication_verified": False,
            }
        )
        return result
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
    speed_basis = "oil" if lubrication == "oil" else "grease"
    speed_limit = bearing[f"{speed_basis}_speed_rpm"]
    speed_margin = speed_limit / speed_rpm
    lubrication_verified = lubrication in {"grease", "oil"}
    if lubrication == "unknown":
        result["warnings"].append(
            "Lubricant is not selected; the grease speed column is only a "
            "conservative placeholder."
        )
    elif lubrication == "sealed_lifetime":
        result["warnings"].append(
            "The open-bearing catalog row does not verify seal-specific speed, "
            "grease life, or fill. Confirm an actual sealed designation."
        )
    formula_limit = min(bearing["static_rating_n"], 0.50 * bearing["dynamic_rating_n"])
    life_formula_valid = dynamic["load_n"] <= formula_limit
    checks = {
        "life": life["life_hours"] >= required_life_hours,
        "static": static_safety >= required_static_safety_factor,
        "speed": speed_margin >= 1.0,
        "life_formula_range": life_formula_valid,
        "lubrication": lubrication_verified,
    }
    hard_failure = static_safety < 1.0 or speed_margin < 1.0 or not life_formula_valid
    qualified = all(checks.values())
    status = (
        "acceptable" if qualified else ("unacceptable" if hard_failure else "marginal")
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
            "speed_basis": speed_basis,
            "lubrication_verified": lubrication_verified,
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


def lubrication_guidance(
    lubrication: str,
    speed_rpm: float,
    bore_mm: float,
    operating_temperature_c: float,
    environment: str,
) -> dict[str, Any]:
    r"""Return property-based lubrication guidance without choosing a product.

    ---Parameters---
    lubrication : str
        Unknown, grease, oil, sealed-for-life, special solid, or no lubricant.
    speed_rpm : float
        Operating speed in revolutions per minute.
    bore_mm : float
        Nominal bearing bore in millimetres.
    operating_temperature_c : float
        Expected stabilized bearing temperature in degrees Celsius.
    environment : str
        Normal, wet, dusty, vacuum, food, corrosive, or cleanroom environment.

    ---Returns---
    lubrication_assessment : dict
        Mode, preliminary speed factor, considerations, and verification status.

    ---LaTeX---
    n d = n \times d
    """
    speed_factor = speed_rpm * bore_mm
    common = [
        "Verify lubricant viscosity at operating—not room—temperature.",
        "Check cage, seal, fill quantity, relubrication interval, and compatibility.",
        "Use the actual bearing mean diameter for a final n·dm check.",
    ]
    mode_guidance = {
        "unknown": [
            "Select a lubrication concept before treating any candidate as qualified.",
            "Grease is often the simpler baseline; oil can remove heat and support "
            "higher speed but adds a supply and sealing system.",
        ],
        "grease": [
            "Specify base-oil type and viscosity, thickener, NLGI consistency, and "
            "additive compatibility with load and environment.",
            "Avoid overfilling at speed; establish replenishment quantity and interval.",
        ],
        "oil": [
            "Choose bath, splash, circulation, jet, mist, or air-oil delivery based "
            "on speed, heat removal, orientation, and cleanliness.",
            "Check churning level, filtration, drain capacity, seals, and start-up supply.",
        ],
        "sealed_lifetime": [
            "Confirm the exact sealed suffix, factory grease, seal temperature, and "
            "seal-limited speed from the product table.",
            "A sealed bearing is not automatically lubricated for the machine life.",
        ],
        "solid_special": [
            "Use only a product with an explicit solid-lubricant/coating rating for "
            "the load, speed, temperature, and atmosphere.",
        ],
        "none": [
            "Standard catalog rolling bearings are not qualified for intentional dry "
            "operation; investigate a purpose-designed alternative technology.",
        ],
    }
    environmental = {
        "wet": "Prioritize water resistance, corrosion protection, and seal integrity.",
        "dusty": "Prioritize exclusion seals, purge strategy, and contamination control.",
        "vacuum": "Check outgassing, vapor pressure, heat rejection, and vacuum-rated materials.",
        "food": "Require the applicable food-grade registration and contamination plan.",
        "corrosive": "Verify chemical compatibility of lubricant, seals, cage, and rings.",
        "cleanroom": "Control particle generation, lubricant migration, and outgassing.",
        "normal": "Confirm ambient contamination and moisture assumptions remain valid.",
    }
    temperature_note = (
        "Temperature is outside a typical general-purpose grease screening range; "
        "use a manufacturer temperature/life calculation."
        if operating_temperature_c < -20 or operating_temperature_c > 120
        else "Temperature still requires viscosity and grease-life verification."
    )
    return {
        "mode": lubrication,
        "verified_for_catalog_screen": lubrication in {"grease", "oil"},
        "bore_speed_factor_nd": speed_factor,
        "operating_temperature_c": operating_temperature_c,
        "environment": environment,
        "considerations": [
            *mode_guidance[lubrication],
            environmental[environment],
            temperature_note,
            *common,
        ],
    }


def technology_triage(
    radial_load_n: float,
    axial_load_n: float,
    speed_rpm: float,
    bore_mm: float,
    lubrication: str,
) -> list[dict[str, Any]]:
    r"""Identify non-rolling bearing technologies worth specialist investigation.

    The rules are transparent prompts, not sizing equations or universal rankings.

    ---Parameters---
    radial_load_n : float
        Radial reaction in newtons.
    axial_load_n : float
        Axial reaction in newtons.
    speed_rpm : float
        Shaft speed in revolutions per minute.
    bore_mm : float
        Nominal shaft diameter in millimetres.
    lubrication : str
        Selected lubrication mode.

    ---Returns---
    technology_options : list
        Alternative profiles with triggers, benefits, limitations, and next questions.

    ---LaTeX---
    n d = n \times d
    """
    nd_value = speed_rpm * bore_mm
    dry_required = lubrication in {"none", "solid_special"}
    high_speed = nd_value >= 300_000
    very_high_speed = nd_value >= 700_000
    low_speed = speed_rpm <= 2_000
    heavy_load = radial_load_n + axial_load_n >= 10_000

    profiles = [
        {
            "id": "hydrodynamic_journal",
            "name": "Hydrodynamic journal / thrust bearing",
            "triggered": lubrication == "oil" or (heavy_load and not dry_required),
            "why": "Strong candidate for continuous rotation, high load, damping, and an available oil system.",
            "limitations": "Has start/stop contact, needs oil supply/thermal design, and requires stability analysis.",
            "next": "Define journal geometry, viscosity-temperature curve, clearance, supply, heat rejection, and stability margin.",
        },
        {
            "id": "hydrostatic",
            "name": "Hydrostatic liquid bearing",
            "triggered": heavy_load and low_speed and lubrication != "none",
            "why": "Externally pressurized support can carry load at zero or low speed with high stiffness and precision.",
            "limitations": "Requires continuous clean pressurized fluid, restrictors, seals, and failure planning.",
            "next": "Define supply pressure, available flow, stiffness, accuracy, fluid, and emergency landing behavior.",
        },
        {
            "id": "plain_sleeve",
            "name": "Sleeve, sintered, or polymer plain bearing",
            "triggered": low_speed or dry_required,
            "why": "Can be compact, inexpensive, tolerant of oscillation, and available in self-lubricating materials.",
            "limitations": "PV, wear, creep, temperature, friction, and shaft-finish limits replace L10 sizing.",
            "next": "Provide pressure-velocity duty, motion cycle, shaft finish/hardness, temperature, and environment.",
        },
        {
            "id": "aerostatic",
            "name": "Aerostatic air bearing",
            "triggered": dry_required or very_high_speed,
            "why": "Externally supplied gas offers non-contact operation, low friction, and high precision at zero speed.",
            "limitations": "Needs clean compressed gas, tight geometry, restrictor design, and loss-of-supply planning.",
            "next": "Define gas supply, stiffness, flow, accuracy, contamination, thrust support, and touchdown strategy.",
        },
        {
            "id": "foil_gas",
            "name": "Aerodynamic / foil gas bearing",
            "triggered": high_speed and dry_required,
            "why": "Oil-free high-speed turbomachinery can use self-acting gas films after lift-off.",
            "limitations": "Start/stop wear, thermal management, rotor dynamics, coatings, and minimum lift-off speed are critical.",
            "next": "Engage a foil-bearing specialist with rotor mass, speed map, starts, temperature, gas, and load direction.",
        },
        {
            "id": "active_magnetic",
            "name": "Active magnetic bearing",
            "triggered": very_high_speed or dry_required,
            "why": "Non-contact controllable support is worth considering where oil-free operation or active vibration control matters.",
            "limitations": "Requires sensors, controls, amplifiers, power, rotor-dynamic validation, and touchdown bearings.",
            "next": "Define static/dynamic force spectra, air gap, power loss, control bandwidth, fault cases, and backup bearings.",
        },
    ]
    for profile in profiles:
        profile["screening_basis"] = {
            "nd_rpm_mm": nd_value,
            "dry_required": dry_required,
            "high_speed_prompt": high_speed,
            "heavy_load_prompt": heavy_load,
        }
    return profiles


def arrangement_guidance(
    arrangement: str,
    preload_method: str,
    preload_n: float,
) -> dict[str, Any]:
    r"""Assess a common bearing arrangement and its preload calculation boundary.

    ---Parameters---
    arrangement : str
        Single known reaction, locating/floating, back-to-back, face-to-face, or tandem.
    preload_method : str
        None, fixed-position, constant-pressure, or manufacturer catalog class.
    preload_n : float
        Explicit initial preload force in newtons when known.

    ---Returns---
    arrangement_assessment : dict
        Topology, load-path explanation, benefits, risks, and calculation support.

    ---LaTeX---
    C_{op} = C_{installed} - \Delta C_{fit} - \Delta C_{thermal}
    """
    profiles = {
        "single_known": {
            "label": "Known reaction at one bearing",
            "load_path": "The entered Fr and Fa are applied directly to one bearing.",
            "considerations": [
                "Confirm another component provides the shaft's remaining radial and axial support.",
                "Do not enter total shaft load unless it equals this bearing reaction.",
            ],
        },
        "locating_floating": {
            "label": "Two-bearing locating / floating system",
            "load_path": "One position locates the shaft axially; the other supports radial load while permitting thermal expansion.",
            "considerations": [
                "Define which bearing and ring provide axial location in each direction.",
                "Ensure the floating position can actually move under its selected fits and housing design.",
                "Check shaft and housing temperature gradients before fixing both positions.",
            ],
        },
        "back_to_back": {
            "label": "Opposed pair — back-to-back (DB)",
            "load_path": "Diverging contact lines resist overturning moment and locate the shaft in both axial directions.",
            "considerations": [
                "Pair load sharing depends on contact angle, preload, stiffness, fits, and temperature.",
                "DB generally provides a wider effective spread than DF but is sensitive to alignment and mounting accuracy.",
            ],
        },
        "face_to_face": {
            "label": "Opposed pair — face-to-face (DF)",
            "load_path": "Converging contact lines locate the shaft in both directions with more angular accommodation than DB.",
            "considerations": [
                "Pair load sharing depends on contact angle, preload, stiffness, fits, and temperature.",
                "DF has a narrower effective spread and lower moment stiffness than a comparable DB pair.",
            ],
        },
        "tandem": {
            "label": "Tandem pair (DT)",
            "load_path": "Parallel contact lines share axial load in one direction; another bearing must react reverse thrust.",
            "considerations": [
                "Use a matched set or validated spacer/deflection design for reliable load sharing.",
                "Tandem is not a two-direction locating arrangement by itself.",
            ],
        },
    }
    preload_profiles = {
        "none": [
            "Operating clearance still changes with fits, temperature, and centrifugal effects."
        ],
        "fixed_position": [
            "Fixed-position preload is stiff but changes strongly with fits and differential thermal growth.",
            "Spacer and shoulder tolerances become part of the preload stack-up.",
        ],
        "constant_pressure": [
            "Spring/constant-pressure preload is less sensitive to thermal growth but has lower system stiffness.",
            "Verify spring travel, force tolerance, speed, and resonance behavior.",
        ],
        "catalog_class": [
            "Manufacturer preload classes apply only to the stated matched bearing set and catalog conditions.",
            "Do not transfer a preload class or force between manufacturers or series.",
        ],
    }
    profile = profiles[arrangement]
    preload_requested = preload_method != "none" or preload_n > 0
    paired = arrangement in {"back_to_back", "face_to_face", "tandem"}
    return {
        "arrangement": arrangement,
        "label": profile["label"],
        "load_path": profile["load_path"],
        "paired": paired,
        "preload_method": preload_method,
        "preload_n": preload_n,
        "preload_requested": preload_requested,
        "preload_calculation_supported": not preload_requested,
        "considerations": [
            *profile["considerations"],
            *preload_profiles[preload_method],
            (
                "Preload was not added to internal bearing load because catalog "
                "load-deflection/stiffness data are not available for every candidate."
                if preload_requested
                else "No explicit preload force was applied in the life calculation."
            ),
        ],
    }


def variable_duty_life(
    bearing: dict[str, Any],
    duty_segments: list[dict[str, float]],
) -> dict[str, Any]:
    r"""Accumulate basic rating-life damage for repeated load/speed segments.

    ---Parameters---
    bearing : dict
        Normalized catalog bearing record.
    duty_segments : list
        Segment dictionaries with radial load, axial load, speed, and duration hours.

    ---Returns---
    variable_duty_result : dict
        Segment loads, cycles, damage fractions, equivalent load, and life hours.

    ---LaTeX---
    D = \sum_i \frac{N_i}{L_{10,i}},\qquad
    P_{eq} = \left(\frac{\sum_i P_i^p N_i}{\sum_i N_i}\right)^{1/p}
    """
    if not duty_segments:
        raise ValueError("Variable duty requires at least one segment.")
    exponent = TYPE_METADATA[bearing["bearing_type"]]["life_exponent"]
    segment_results = []
    total_cycles = 0.0
    weighted_load_power = 0.0
    pattern_hours = 0.0
    pattern_damage = 0.0
    maximum_static_load = 0.0
    maximum_speed = 0.0
    for index, segment in enumerate(duty_segments, start=1):
        try:
            radial = float(segment["radial_load_n"])
            axial = float(segment.get("axial_load_n", 0.0))
            speed = float(segment["speed_rpm"])
            duration = float(segment["duration_hours"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid variable-duty segment {index}.") from error
        if radial < 0 or axial < 0 or speed <= 0 or duration <= 0:
            raise ValueError(
                f"Segment {index} loads must be non-negative and speed/duration positive."
            )
        dynamic = equivalent_dynamic_load(radial, axial, bearing)
        static = equivalent_static_load(radial, axial, bearing)
        cycles = 60.0 * speed * duration
        rating_revolutions = (
            1_000_000.0 * (bearing["dynamic_rating_n"] / dynamic["load_n"]) ** exponent
        )
        damage = cycles / rating_revolutions
        total_cycles += cycles
        pattern_hours += duration
        pattern_damage += damage
        maximum_static_load = max(maximum_static_load, static["load_n"])
        maximum_speed = max(maximum_speed, speed)
        weighted_load_power += dynamic["load_n"] ** exponent * cycles
        segment_results.append(
            {
                "segment": index,
                "radial_load_n": radial,
                "axial_load_n": axial,
                "speed_rpm": speed,
                "duration_hours": duration,
                "equivalent_load_n": dynamic["load_n"],
                "cycles": cycles,
                "damage_fraction_per_pattern": damage,
            }
        )
    equivalent_load = (weighted_load_power / total_cycles) ** (1.0 / exponent)
    pattern_repetitions = 1.0 / pattern_damage
    return {
        "segments": segment_results,
        "pattern_hours": pattern_hours,
        "pattern_damage": pattern_damage,
        "pattern_repetitions_to_l10": pattern_repetitions,
        "life_hours": pattern_hours * pattern_repetitions,
        "equivalent_dynamic_load_n": equivalent_load,
        "total_cycles_per_pattern": total_cycles,
        "maximum_static_load_n": maximum_static_load,
        "maximum_speed_rpm": maximum_speed,
    }


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
    operating_temperature_c: float = 60.0,
    environment: str = "normal",
    arrangement: str = "single_known",
    preload_method: str = "none",
    preload_n: float = 0.0,
    duty_segments_json: str = "",
    bearing_positions_json: str = "",
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
    operating_temperature_c : float
        Expected stabilized bearing temperature in degrees Celsius.
    environment : str
        Normal, wet, dusty, vacuum, food, corrosive, or cleanroom environment.
    arrangement : str
        Single known reaction, locating/floating, DB, DF, or tandem topology.
    preload_method : str
        None, fixed-position, constant-pressure, or catalog-class preload.
    preload_n : float
        Explicit preload force in newtons when known; advisory until stiffness data exist.
    duty_segments_json : str
        Optional JSON array of repeated load/speed/duration segments.
    bearing_positions_json : str
        Optional JSON array of additional positions with already-solved reactions.

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
    lubrication_assessment : dict
        Property-based lubrication guidance and verification boundary.
    alternative_technologies : list
        Non-rolling technologies worth investigating and their tradeoffs.
    arrangement_assessment : dict
        Load-path, preload, thermal-growth, and calculation-boundary guidance.
    system_analysis : dict
        Position-by-position known-reaction screen and limiting status.

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
        "operating temperature": operating_temperature_c,
        "preload": preload_n,
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
    if preload_n < 0:
        raise ValueError("Preload force must be non-negative.")
    lubrication_modes = {
        "unknown",
        "grease",
        "oil",
        "sealed_lifetime",
        "solid_special",
        "none",
    }
    if lubrication not in lubrication_modes:
        raise ValueError(
            "Lubrication must be unknown, grease, oil, sealed_lifetime, "
            "solid_special, or none."
        )
    environments = {
        "normal",
        "wet",
        "dusty",
        "vacuum",
        "food",
        "corrosive",
        "cleanroom",
    }
    if environment not in environments:
        raise ValueError(
            f"Environment must be one of: {', '.join(sorted(environments))}."
        )
    arrangements = {
        "single_known",
        "locating_floating",
        "back_to_back",
        "face_to_face",
        "tandem",
    }
    if arrangement not in arrangements:
        raise ValueError(
            f"Arrangement must be one of: {', '.join(sorted(arrangements))}."
        )
    preload_methods = {
        "none",
        "fixed_position",
        "constant_pressure",
        "catalog_class",
    }
    if preload_method not in preload_methods:
        raise ValueError(
            f"Preload method must be one of: {', '.join(sorted(preload_methods))}."
        )
    if preload_method == "none" and preload_n > 0:
        raise ValueError(
            "Choose a preload method when preload force is greater than zero."
        )
    duty_segments: list[dict[str, float]] = []
    if duty_segments_json.strip():
        try:
            parsed_segments = json.loads(duty_segments_json)
        except json.JSONDecodeError as error:
            raise ValueError("Variable-duty segments must be valid JSON.") from error
        if not isinstance(parsed_segments, list):
            raise ValueError("Variable-duty JSON must contain an array of segments.")
        duty_segments = parsed_segments
    additional_positions: list[dict[str, Any]] = []
    if bearing_positions_json.strip():
        try:
            parsed_positions = json.loads(bearing_positions_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                "Additional bearing positions must be valid JSON."
            ) from error
        if not isinstance(parsed_positions, list):
            raise ValueError("Additional bearing positions must be a JSON array.")
        additional_positions = parsed_positions
    if float(bore_mm) not in list_bore_sizes():
        available = ", ".join(f"{value:g}" for value in list_bore_sizes())
        raise ValueError(f"Bore must be one of: {available} mm.")

    selected_types = _parse_types(bearing_types_csv)
    catalog_rows = [
        row
        for row in BEARING_CATALOG
        if row["bore_mm"] == float(bore_mm) and row["bearing_type"] in selected_types
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
    if duty_segments:
        for candidate in candidates:
            if not candidate["applicable"]:
                continue
            variable = variable_duty_life(candidate, duty_segments)
            candidate["variable_duty"] = variable
            candidate["life_hours"] = variable["life_hours"]
            candidate["load_n"] = variable["equivalent_dynamic_load_n"]
            candidate["static_load_n"] = variable["maximum_static_load_n"]
            candidate["static_safety_factor"] = (
                candidate["static_rating_n"] / variable["maximum_static_load_n"]
            )
            candidate["speed_margin"] = (
                candidate["speed_limit_rpm"] / variable["maximum_speed_rpm"]
            )
            candidate["life_formula_valid"] = (
                candidate["load_n"] <= candidate["life_formula_limit_n"]
            )
            candidate["checks"].update(
                {
                    "life": candidate["life_hours"] >= required_life_hours,
                    "static": candidate["static_safety_factor"]
                    >= required_static_safety_factor,
                    "speed": candidate["speed_margin"] >= 1.0,
                    "life_formula_range": candidate["life_formula_valid"],
                }
            )
            candidate["qualified"] = all(candidate["checks"].values())
            hard_failure = (
                candidate["static_safety_factor"] < 1.0
                or candidate["speed_margin"] < 1.0
                or not candidate["life_formula_valid"]
            )
            candidate["status"] = (
                "acceptable"
                if candidate["qualified"]
                else ("unacceptable" if hard_failure else "marginal")
            )
            candidate["status_reason"] = (
                "Meets all repeated-duty screening requirements."
                if candidate["qualified"]
                else "Review the failed repeated-duty screening checks."
            )
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
                    item["static_safety_factor"] / required_static_safety_factor,
                    3.0,
                )
                + min(item["speed_margin"], 3.0),
            ),
        )
        status = (
            "marginal"
            if not all(
                candidate["status"] == "unacceptable" for candidate in applicable
            )
            else "unacceptable"
        )
        basis = (
            "No candidate meets every requirement; this is the closest "
            "screening result."
        )
    else:
        top = candidates[0]
        status = "unacceptable"
        basis = "No selected bearing family is applicable to this duty point."

    arrangement_assessment = arrangement_guidance(
        arrangement, preload_method, preload_n
    )
    if (
        arrangement_assessment["preload_requested"]
        and not arrangement_assessment["preload_calculation_supported"]
    ):
        if status == "acceptable":
            status = "marginal"
        basis += (
            " Preload is advisory because candidate stiffness data are unavailable."
        )

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
    guidance.extend(arrangement_assessment["considerations"])

    recommendation = {
        "designation": top["designation"] if applicable else None,
        "bearing_type": top["bearing_type"] if applicable else None,
        "type_label": (
            top["type_label"] if applicable else "No applicable rolling candidate"
        ),
        "status": status,
        "basis": basis,
        "qualified_count": len(qualified),
        "candidate_count": len(candidates),
    }
    top_life = top.get("life_hours") if applicable else None
    system_positions = [
        {
            "name": "Position A",
            "status": status,
            "bore_mm": float(bore_mm),
            "radial_load_n": radial_load_n,
            "axial_load_n": axial_load_n,
            "speed_rpm": speed_rpm,
            "recommended_designation": recommendation["designation"],
            "recommended_type": recommendation["type_label"],
            "recommended_life_hours": top_life,
        }
    ]
    for index, position in enumerate(additional_positions, start=2):
        if not isinstance(position, dict):
            raise ValueError(f"Bearing position {index} must be an object.")
        try:
            position_radial = float(position["radial_load_n"])
            position_axial = float(position.get("axial_load_n", 0.0))
            position_speed = float(position.get("speed_rpm", speed_rpm))
            position_bore = float(position.get("bore_mm", bore_mm))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Bearing position {index} has invalid values.") from error
        position_result = select_bearings(
            radial_load_n=position_radial,
            axial_load_n=position_axial,
            speed_rpm=position_speed,
            bore_mm=position_bore,
            bearing_types_csv=bearing_types_csv,
            lubrication=lubrication,
            required_life_hours=required_life_hours,
            required_static_safety_factor=required_static_safety_factor,
            operating_temperature_c=operating_temperature_c,
            environment=environment,
            arrangement="single_known",
        )
        position_recommendation = position_result["recommendation"]
        position_top = next(
            (
                item
                for item in position_result["candidates"]
                if item["designation"] == position_recommendation["designation"]
            ),
            None,
        )
        system_positions.append(
            {
                "name": str(position.get("name", f"Position {index}")),
                "status": position_result["status"],
                "bore_mm": position_bore,
                "radial_load_n": position_radial,
                "axial_load_n": position_axial,
                "speed_rpm": position_speed,
                "recommended_designation": position_recommendation["designation"],
                "recommended_type": position_recommendation["type_label"],
                "recommended_life_hours": (
                    position_top.get("life_hours") if position_top else None
                ),
            }
        )
    severity = {"acceptable": 0, "marginal": 1, "unacceptable": 2}
    system_status = max(
        (position["status"] for position in system_positions),
        key=lambda item: severity[item],
    )
    finite_positions = [
        position
        for position in system_positions
        if position["recommended_life_hours"] is not None
    ]
    limiting_position = (
        min(finite_positions, key=lambda item: item["recommended_life_hours"])["name"]
        if finite_positions
        else None
    )
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
            "operating_temperature_c": operating_temperature_c,
            "environment": environment,
            "arrangement": arrangement,
            "preload_method": preload_method,
            "preload_n": preload_n,
            "duty_segments": duty_segments,
            "additional_bearing_positions": additional_positions,
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
        "lubrication_assessment": lubrication_guidance(
            lubrication,
            speed_rpm,
            float(bore_mm),
            operating_temperature_c,
            environment,
        ),
        "alternative_technologies": technology_triage(
            radial_load_n,
            axial_load_n,
            speed_rpm,
            float(bore_mm),
            lubrication,
        ),
        "arrangement_assessment": arrangement_assessment,
        "system_analysis": {
            "method": "known_reactions_only",
            "status": system_status,
            "positions": system_positions,
            "limiting_position": limiting_position,
            "warnings": [
                "Each position is screened independently from user-supplied reactions.",
                "This does not solve shaft equilibrium, stiffness-based load sharing, "
                "or coupled axial forces between positions.",
            ],
        },
        "catalog_meta": {
            "manufacturer": "NTN",
            "catalog": "Ball and Roller Bearings, No. 2203/E",
            "catalog_entry_count": len(BEARING_CATALOG),
            "catalog_version": CATALOG_DATA["catalog_version"],
            "catalog_sha256": CATALOG_DATA["sha256"],
            "available_bores_mm": list_bore_sizes(),
            "searched_count": len(BEARING_CATALOG),
            "same_bore_count": sum(
                row["bore_mm"] == float(bore_mm) for row in BEARING_CATALOG
            ),
            "evaluated_count": len(candidates),
            "qualified_count": len(qualified),
            "inapplicable_count": sum(
                not candidate["applicable"] for candidate in candidates
            ),
            "catalog_index_url": NTN_CATALOG_INDEX,
            "load_life_source_url": (
                "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_a03.pdf"
            ),
            "load_factor_source_url": (
                "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_a04.pdf"
            ),
            "scope": (
                f"{len(BEARING_CATALOG)} sourced NTN records across "
                f"{len(list_bore_sizes())} bores from "
                f"{min(list_bore_sizes()):g} to {max(list_bore_sizes()):g} mm."
            ),
        },
        "subst_recommendation": (
            f"{top['designation']}: {basis}"
            if applicable
            else f"No applicable rolling candidate: {basis}"
        ),
    }
