"""
Deck planning utilities for estimating material quantities, mass, and cost.

The module captures the arithmetic typically used during schematic deck
planning.  It assumes conventional residential framing with dimensional
lumber, equal joist spacing, and uniformly distributed posts supporting
multi-ply beams.  The calculations intentionally favour transparency over
structural nuance so owners can sanity-check shopping lists before engaging
an engineer or supplier.
"""

from __future__ import annotations

import math
from typing import Dict

DECKING_LIBRARY: Dict[str, Dict[str, float | str]] = {
    "pressure_treated_54x6": {
        "label": "5/4×6 Pressure-Treated Pine",
        "board_width_in": 5.5,
        "gap_in": 0.125,
        "cost_per_linear_ft": 2.25,
        "weight_per_linear_ft": 2.0,
    },
    "cedar_54x6": {
        "label": "5/4×6 Western Red Cedar",
        "board_width_in": 5.5,
        "gap_in": 0.1875,
        "cost_per_linear_ft": 3.45,
        "weight_per_linear_ft": 1.45,
    },
    "composite_1x6": {
        "label": "1×6 Wood-Plastic Composite",
        "board_width_in": 5.5,
        "gap_in": 0.125,
        "cost_per_linear_ft": 4.85,
        "weight_per_linear_ft": 2.7,
    },
    "ipe_34x6": {
        "label": "3/4×6 Ipe Hardwood",
        "board_width_in": 5.5,
        "gap_in": 0.125,
        "cost_per_linear_ft": 5.9,
        "weight_per_linear_ft": 2.9,
    },
}

FRAMING_LIBRARY: Dict[str, Dict[str, float | str]] = {
    "pt_2x8": {
        "label": "2×8 Pressure-Treated (1.5\"×7.25\")",
        "cost_per_linear_ft": 1.95,
        "weight_per_linear_ft": 3.0,
        "plies_per_beam": 2,
    },
    "pt_2x10": {
        "label": "2×10 Pressure-Treated (1.5\"×9.25\")",
        "cost_per_linear_ft": 2.45,
        "weight_per_linear_ft": 3.8,
        "plies_per_beam": 2,
    },
    "pt_2x12": {
        "label": "2×12 Pressure-Treated (1.5\"×11.25\")",
        "cost_per_linear_ft": 3.05,
        "weight_per_linear_ft": 4.5,
        "plies_per_beam": 2,
    },
}

POST_LIBRARY: Dict[str, Dict[str, float | str]] = {
    "pt_4x4": {
        "label": "4×4 Pressure-Treated Post",
        "cost_per_unit": 18.0,
        "weight_per_unit": 22.0,
    },
    "pt_6x6": {
        "label": "6×6 Pressure-Treated Post",
        "cost_per_unit": 34.0,
        "weight_per_unit": 48.0,
    },
}

CONCRETE_LIBRARY: Dict[str, Dict[str, float | str]] = {
    "sack_80lb": {
        "label": "80 lb Premix Concrete Sack",
        "coverage_cuft": 0.6,
        "cost_per_unit": 5.5,
        "weight_per_unit": 80.0,
    }
}


def list_catalogues() -> Dict[str, Dict[str, str]]:
    """
    Return user-facing labels for the deck planning catalogues.

    The helper keeps the UI synchronised with the data embedded inside
    this module so drop-down menus can be generated dynamically.
    """

    return {
        "decking": {key: spec["label"] for key, spec in DECKING_LIBRARY.items()},
        "framing": {key: spec["label"] for key, spec in FRAMING_LIBRARY.items()},
        "posts": {key: spec["label"] for key, spec in POST_LIBRARY.items()},
        "concrete": {key: spec["label"] for key, spec in CONCRETE_LIBRARY.items()},
    }


def _validate_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _round(value: float) -> float:
    return round(value, 4)


def estimate_deck_materials(
    deck_length_ft: float,
    deck_width_ft: float,
    joist_spacing_in: float,
    beam_spacing_ft: float,
    post_spacing_ft: float,
    decking_type: str,
    framing_type: str,
    post_type: str,
    waste_allowance_percent: float,
    concrete_choice: str = "sack_80lb",
) -> Dict[str, float | str]:
    """
    Estimate deck framing and surface material counts from key layout inputs.

    The estimator assumes single-span joists that bear on multi-ply beams
    supported by equally spaced posts.  Waste is modelled as a fractional
    linear-foot increase applied to both decking and framing members.

    ---Parameters---
    deck_length_ft : float
        Longitudinal deck dimension measured along the ledger or house face (ft).
    deck_width_ft : float
        Projection of the deck away from the house, shared with joist span (ft).
    joist_spacing_in : float
        Centre-to-centre spacing between joists (in). Typical residential values
        are 12, 16, or 24 inches.
    beam_spacing_ft : float
        Distance between beam lines measured perpendicular to the ledger (ft).
        A value of 6–8 ft is common for ground-level decks.
    post_spacing_ft : float
        Longitudinal spacing between posts along each beam (ft).
    decking_type : str
        Key referencing ``DECKING_LIBRARY`` inside this module.
    framing_type : str
        Key referencing ``FRAMING_LIBRARY`` for both joists and built-up beams.
    post_type : str
        Key referencing ``POST_LIBRARY`` for the selected post stock.
    waste_allowance_percent : float
        Percentage of additional material ordered to cover trims, mistakes, and
        defects. A value between 5 and 15 % is customary.
    concrete_choice : str
        Key referencing ``CONCRETE_LIBRARY`` that defines which premix sack the
        footing estimate should use.

    ---Returns---
    deck_area_sqft : float
        Plan area of the deck surface (sq ft).
    decking_board_count : float
        Number of deck boards to purchase after applying the waste allowance.
    decking_linear_ft : float
        Total linear feet of decking required including waste (ft).
    decking_cost_usd : float
        Estimated purchase cost for the decking boards (USD).
    decking_weight_lb : float
        Estimated mass of all decking boards (lb).
    joist_count : float
        Total joists required, excluding the rim pair.
    joist_linear_ft : float
        Linear footage of joists and rim boards plus waste (ft).
    joist_cost_usd : float
        Estimated joist and rim material cost (USD).
    joist_weight_lb : float
        Mass of joists and rims (lb).
    beam_count : float
        Count of multi-ply beams required in addition to the ledger.
    beam_linear_ft : float
        Linear footage of all beam plies including waste (ft).
    beam_cost_usd : float
        Estimated material cost for the beams (USD).
    beam_weight_lb : float
        Mass of all beam plies (lb).
    post_count : float
        Total number of posts (and footings) required.
    post_cost_usd : float
        Estimated cost of the posts alone (USD).
    post_weight_lb : float
        Mass of the posts (lb).
    footing_volume_cuft : float
        Concrete volume demanded by the post footings (ft³).
    footing_concrete_bags : float
        Count of premix concrete sacks required for footings.
    concrete_cost_usd : float
        Cost of premix concrete sacks for the footings (USD).
    concrete_weight_lb : float
        Mass of the premix concrete sacks (lb).
    total_material_cost_usd : float
        Combined purchase cost for all materials (USD).
    total_material_weight_lb : float
        Combined estimated weight of all materials (lb).
    selected_decking_label : str
        Human-readable description of the chosen decking profile.
    selected_framing_label : str
        Human-readable description of the chosen joist and beam stock.
    selected_post_label : str
        Human-readable description of the chosen post size.
    selected_concrete_label : str
        Human-readable description of the premix sack.

    ---LaTeX---
    A = L \\times W \\\\
    N_b = \\left\\lceil \\frac{12 W}{b + g} \\right\\rceil (1 + \\phi) \\\\
    L_b = N_b \\times L \\\\
    C_b = L_b \\times c_b \\\\
    W_b = L_b \\times w_b \\\\
    N_j = \\left\\lfloor \\frac{12 L}{s} \\right\\rfloor + 1 \\\\
    L_j = (N_j \\times W + 2 L) (1 + \\phi) \\\\
    C_j = L_j \\times c_j \\\\
    W_j = L_j \\times w_j \\\\
    B = \\max\\left(1, \\left\\lceil \\frac{W}{B_s} \\right\\rceil\\right) \\\\
    L_{beam} = B \\times p_b \\times L \\times (1 + \\phi) \\\\
    C_{beam} = L_{beam} \\times c_j \\\\
    W_{beam} = L_{beam} \\times w_j \\\\
    N_p = B \\times \\left(\\left\\lceil \\frac{L}{p} \\right\\rceil + 1\\right) \\\\
    C_p = N_p \\times c_p \\\\
    W_p = N_p \\times w_p \\\\
    V_f = N_p \\times \\pi r^2 F_d \\\\
    N_c = \\left\\lceil \\frac{V_f}{V_c} \\right\\rceil \\\\
    C_c = N_c \\times c_c \\\\
    W_c = N_c \\times w_c \\\\
    C_{\\text{total}} = C_b + C_j + C_{beam} + C_p + C_c \\\\
    W_{\\text{total}} = W_b + W_j + W_{beam} + W_p + W_c \\\\

    ---Variables---
    A: deck surface area (sq ft)
    L: deck length along the ledger (ft)
    W: deck width perpendicular to the ledger (ft)
    b: bare board width (in)
    g: gap between boards (in)
    \\phi: waste allowance fraction (-)
    L_b: decking linear footage (ft)
    c_b: decking cost per linear foot (USD/ft)
    w_b: decking weight per linear foot (lb/ft)
    s: joist spacing (in)
    N_j: joist count (excludes rim joists)
    L_j: joist + rim linear footage (ft)
    c_j: joist cost per linear foot (USD/ft)
    w_j: joist weight per linear foot (lb/ft)
    B: number of beam lines (-)
    B_s: spacing between beam lines (ft)
    p_b: number of plies per beam (-)
    p: post spacing (ft)
    N_p: total post count (-)
    c_p: cost per post (USD)
    w_p: weight per post (lb)
    r: assumed footing radius (ft)
    F_d: footing depth assumption (ft)
    V_c: concrete volume delivered per sack (ft³)
    N_c: number of concrete sacks (-)
    c_c: cost per concrete sack (USD)
    w_c: weight per concrete sack (lb)

    ---References---
    American Wood Council, *Prescriptive Residential Wood Deck Construction
    Guide* (DCA 6-15), 2015.
    Virginia Cooperative Extension, *Decking Materials: Weight and Cost
    Comparison*, Publication EN-03, 2019.
    """

    try:
        deck_length_ft = float(deck_length_ft)
        deck_width_ft = float(deck_width_ft)
        joist_spacing_in = float(joist_spacing_in)
        beam_spacing_ft = float(beam_spacing_ft)
        post_spacing_ft = float(post_spacing_ft)
        waste_allowance_percent = float(waste_allowance_percent)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError("All numeric inputs must be convertible to float.") from exc

    _validate_positive(deck_length_ft, "Deck length")
    _validate_positive(deck_width_ft, "Deck width")
    _validate_positive(joist_spacing_in, "Joist spacing")
    _validate_positive(beam_spacing_ft, "Beam spacing")
    _validate_positive(post_spacing_ft, "Post spacing")

    if waste_allowance_percent < 0:
        raise ValueError("Waste allowance cannot be negative.")

    decking_spec = DECKING_LIBRARY.get(decking_type)
    framing_spec = FRAMING_LIBRARY.get(framing_type)
    post_spec = POST_LIBRARY.get(post_type)
    concrete_spec = CONCRETE_LIBRARY.get(concrete_choice)

    if not decking_spec:
        raise ValueError("Unknown decking selection.")
    if not framing_spec:
        raise ValueError("Unknown framing selection.")
    if not post_spec:
        raise ValueError("Unknown post selection.")
    if not concrete_spec:
        raise ValueError("Unknown concrete selection.")

    waste_fraction = waste_allowance_percent / 100.0
    deck_area = deck_length_ft * deck_width_ft

    board_coverage_in = decking_spec["board_width_in"] + decking_spec["gap_in"]
    boards_raw = (deck_width_ft * 12.0) / board_coverage_in
    decking_board_count = math.ceil(boards_raw * (1.0 + waste_fraction))
    decking_linear_ft = decking_board_count * deck_length_ft
    decking_cost = decking_linear_ft * decking_spec["cost_per_linear_ft"]
    decking_weight = decking_linear_ft * decking_spec["weight_per_linear_ft"]

    joist_spacing_ft = joist_spacing_in / 12.0
    joist_count = math.floor(deck_length_ft / joist_spacing_ft) + 1
    rim_count = 2  # one rim plus ledger face
    joist_linear_ft = (joist_count * deck_width_ft + rim_count * deck_length_ft) * (
        1.0 + waste_fraction
    )
    joist_cost = joist_linear_ft * framing_spec["cost_per_linear_ft"]
    joist_weight = joist_linear_ft * framing_spec["weight_per_linear_ft"]

    beam_lines = max(1, math.ceil(deck_width_ft / beam_spacing_ft))
    beam_linear_ft = (
        beam_lines
        * framing_spec["plies_per_beam"]
        * deck_length_ft
        * (1.0 + waste_fraction)
    )
    beam_cost = beam_linear_ft * framing_spec["cost_per_linear_ft"]
    beam_weight = beam_linear_ft * framing_spec["weight_per_linear_ft"]

    posts_per_beam = math.ceil(deck_length_ft / post_spacing_ft) + 1
    post_count = beam_lines * posts_per_beam
    post_cost = post_count * post_spec["cost_per_unit"]
    post_weight = post_count * post_spec["weight_per_unit"]

    assumed_footing_depth_ft = 2.0  # conservative depth for volume estimate
    footing_radius_ft = 0.75
    footing_volume = post_count * math.pi * (footing_radius_ft**2) * assumed_footing_depth_ft
    sacks_required = math.ceil(
        footing_volume / concrete_spec["coverage_cuft"]
    )  # convert ft³ to sacks
    concrete_cost = sacks_required * concrete_spec["cost_per_unit"]
    concrete_weight = sacks_required * concrete_spec["weight_per_unit"]

    total_cost = decking_cost + joist_cost + beam_cost + post_cost + concrete_cost
    total_weight = (
        decking_weight + joist_weight + beam_weight + post_weight + concrete_weight
    )

    results: Dict[str, float | str] = {
        "deck_area_sqft": _round(deck_area),
        "decking_board_count": float(decking_board_count),
        "decking_linear_ft": _round(decking_linear_ft),
        "decking_weight_lb": _round(decking_weight),
        "decking_cost_usd": _round(decking_cost),
        "joist_count": float(joist_count),
        "joist_linear_ft": _round(joist_linear_ft),
        "joist_weight_lb": _round(joist_weight),
        "joist_cost_usd": _round(joist_cost),
        "beam_count": float(beam_lines),
        "beam_linear_ft": _round(beam_linear_ft),
        "beam_weight_lb": _round(beam_weight),
        "beam_cost_usd": _round(beam_cost),
        "post_count": float(post_count),
        "post_cost_usd": _round(post_cost),
        "post_weight_lb": _round(post_weight),
        "footing_volume_cuft": _round(footing_volume),
        "footing_concrete_bags": float(sacks_required),
        "concrete_cost_usd": _round(concrete_cost),
        "concrete_weight_lb": _round(concrete_weight),
        "total_material_cost_usd": _round(total_cost),
        "total_material_weight_lb": _round(total_weight),
        "selected_decking_label": str(decking_spec["label"]),
        "selected_framing_label": str(framing_spec["label"]),
        "selected_post_label": str(post_spec["label"]),
        "selected_concrete_label": str(concrete_spec["label"]),
    }

    results.update(
        {
            "subst_deck_area_sqft": (
                "A = {length:.2f} \\times {width:.2f} = {value:.2f}"
            ).format(
                length=deck_length_ft,
                width=deck_width_ft,
                value=deck_area,
            ),
            "subst_decking_board_count": (
                "N_b = \\lceil (12 \\times {width:.2f}) / ({board_width:.3f} + {gap:.3f}) "
                "\\rceil \\times (1 + {waste:.3f}) = {value:.0f}"
            ).format(
                width=deck_width_ft,
                board_width=decking_spec["board_width_in"],
                gap=decking_spec["gap_in"],
                waste=waste_fraction,
                value=decking_board_count,
            ),
            "subst_decking_linear_ft": (
                "L_b = {boards:.0f} \\times {length:.2f} = {value:.2f}"
            ).format(
                boards=decking_board_count,
                length=deck_length_ft,
                value=decking_linear_ft,
            ),
            "subst_decking_cost_usd": (
                "C_b = {lin_ft:.2f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                lin_ft=decking_linear_ft,
                rate=decking_spec["cost_per_linear_ft"],
                value=decking_cost,
            ),
            "subst_decking_weight_lb": (
                "W_b = {lin_ft:.2f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                lin_ft=decking_linear_ft,
                rate=decking_spec["weight_per_linear_ft"],
                value=decking_weight,
            ),
            "subst_joist_count": (
                "N_j = \\lfloor (12 \\times {length:.2f}) / {spacing:.2f} \\rfloor + 1 = {value:.0f}"
            ).format(
                length=deck_length_ft,
                spacing=joist_spacing_in,
                value=joist_count,
            ),
            "subst_joist_linear_ft": (
                "L_j = (({joists:.0f} \\times {width:.2f}) + (2 \\times {length:.2f})) "
                "\\times (1 + {waste:.3f}) = {value:.2f}"
            ).format(
                joists=joist_count,
                width=deck_width_ft,
                length=deck_length_ft,
                waste=waste_fraction,
                value=joist_linear_ft,
            ),
            "subst_joist_cost_usd": (
                "C_j = {lin_ft:.2f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                lin_ft=joist_linear_ft,
                rate=framing_spec["cost_per_linear_ft"],
                value=joist_cost,
            ),
            "subst_joist_weight_lb": (
                "W_j = {lin_ft:.2f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                lin_ft=joist_linear_ft,
                rate=framing_spec["weight_per_linear_ft"],
                value=joist_weight,
            ),
            "subst_beam_count": (
                "B = \\max\\left(1, \\lceil {width:.2f} / {spacing:.2f} \\rceil\\right) = {value:.0f}"
            ).format(
                width=deck_width_ft,
                spacing=beam_spacing_ft,
                value=beam_lines,
            ),
            "subst_beam_linear_ft": (
                "L_{{beam}} = {beams:.0f} \\times {plies:.0f} \\times {length:.2f} "
                "\\times (1 + {waste:.3f}) = {value:.2f}"
            ).format(
                beams=beam_lines,
                plies=framing_spec["plies_per_beam"],
                length=deck_length_ft,
                waste=waste_fraction,
                value=beam_linear_ft,
            ),
            "subst_beam_cost_usd": (
                "C_{{beam}} = {lin_ft:.2f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                lin_ft=beam_linear_ft,
                rate=framing_spec["cost_per_linear_ft"],
                value=beam_cost,
            ),
            "subst_beam_weight_lb": (
                "W_{{beam}} = {lin_ft:.2f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                lin_ft=beam_linear_ft,
                rate=framing_spec["weight_per_linear_ft"],
                value=beam_weight,
            ),
            "subst_post_count": (
                "N_p = {beams:.0f} \\times (\\lceil {length:.2f} / {spacing:.2f} \\rceil + 1) = {value:.0f}"
            ).format(
                beams=beam_lines,
                length=deck_length_ft,
                spacing=post_spacing_ft,
                value=post_count,
            ),
            "subst_post_cost_usd": (
                "C_p = {count:.0f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                count=post_count,
                rate=post_spec["cost_per_unit"],
                value=post_cost,
            ),
            "subst_post_weight_lb": (
                "W_p = {count:.0f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                count=post_count,
                rate=post_spec["weight_per_unit"],
                value=post_weight,
            ),
            "subst_footing_volume_cuft": (
                "V_f = {posts:.0f} \\times \\pi \\times {radius:.2f}^2 \\times {depth:.2f} = {value:.2f}"
            ).format(
                posts=post_count,
                radius=footing_radius_ft,
                depth=assumed_footing_depth_ft,
                value=footing_volume,
            ),
            "subst_footing_concrete_bags": (
                "N_c = \\left\\lceil \\frac{{{posts:.0f} \\times \\pi \\times {radius:.2f}^2 "
                "\\times {depth:.2f}}}{{{coverage:.2f}}} \\right\\rceil = {value:.0f}"
            ).format(
                posts=post_count,
                radius=footing_radius_ft,
                depth=assumed_footing_depth_ft,
                coverage=concrete_spec["coverage_cuft"],
                value=sacks_required,
            ),
            "subst_concrete_cost_usd": (
                "C_c = {bags:.0f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                bags=sacks_required,
                rate=concrete_spec["cost_per_unit"],
                value=concrete_cost,
            ),
            "subst_concrete_weight_lb": (
                "W_c = {bags:.0f} \\times {rate:.2f} = {value:.2f}"
            ).format(
                bags=sacks_required,
                rate=concrete_spec["weight_per_unit"],
                value=concrete_weight,
            ),
            "subst_total_material_cost_usd": (
                "C_{{total}} = {decking:.2f} + {joists:.2f} + {beams:.2f} + {posts:.2f} + {concrete:.2f} "
                "= {value:.2f}"
            ).format(
                decking=decking_cost,
                joists=joist_cost,
                beams=beam_cost,
                posts=post_cost,
                concrete=concrete_cost,
                value=total_cost,
            ),
            "subst_total_material_weight_lb": (
                "W_{{total}} = {decking:.2f} + {joists:.2f} + {beams:.2f} + {posts:.2f} + {concrete:.2f} "
                "= {value:.2f}"
            ).format(
                decking=decking_weight,
                joists=joist_weight,
                beams=beam_weight,
                posts=post_weight,
                concrete=concrete_weight,
                value=total_weight,
            ),
        }
    )

    return results
