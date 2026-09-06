"""Drawing designations and specification notes, without tolerance-limit claims.

Nominal Unified size/pitch pairs: Optimas, UNC/UNF/UNEF Thread Table,
https://optimas.com/en_gb/technical-resources/unc-and-unf-thread/ . Only nominal
pairs are transcribed, not the table's rounded or occasionally erroneous
derived diameters. Metric names reuse threads.py. Pipe sizes/pitches follow
Swagelok's Thread and End Connection Identification Guide, MS-13-77.

Designation references: ISO 965, ASME B1.1, ASME B1.20.1/B1.20.3, ISO 228-1,
and ISO 7-1. These notes do not reproduce dimensional tolerance tables or
certify compliance. Product-specific screws require a supplier specification.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from typing import Any

try:
    from .fasteners import (
        _parse_unified_size,
        calculate_basic_thread_geometry,
        parse_metric_thread_designation,
    )
    from .threads import analyze_thread, get_thread_catalog
except ImportError:  # Pyodide loads modules as top-level files.
    from fasteners import (
        _parse_unified_size,
        calculate_basic_thread_geometry,
        parse_metric_thread_designation,
    )
    from threads import analyze_thread, get_thread_catalog


# Nominal pairs, not a claim of exhaustive ASME coverage.
UNIFIED_PAIRS = {
    "unc": (
        "#1:64 #2:56 #3:48 #4:40 #5:40 #6:32 #8:32 #10:24 #12:24 "
        "1/4:20 5/16:18 3/8:16 7/16:14 1/2:13 9/16:12 5/8:11 "
        "3/4:10 7/8:9 1:8 1_1/8:7 1_1/4:7 1_3/8:6 1_1/2:6 "
        "1_3/4:5 2:4.5"
    ),
    "unf": (
        "#0:80 #1:72 #2:64 #3:56 #4:48 #5:44 #6:40 #8:36 #10:32 "
        "#12:28 1/4:28 5/16:24 3/8:24 7/16:20 1/2:20 9/16:18 "
        "5/8:18 3/4:16 7/8:14 1:12 1_1/8:12 1_1/4:12 1_3/8:12 1_1/2:12"
    ),
    "unef": (
        "#12:32 1/4:32 5/16:32 3/8:32 7/16:28 1/2:28 9/16:24 "
        "5/8:24 11/16:24 3/4:20 13/16:20 7/8:20 15/16:20 1:20 "
        "1_1/16:18 1_1/8:18 1_3/16:18 1_1/4:18 1_5/16:18 "
        "1_3/8:18 1_7/16:18 1_1/2:18 1_9/16:18 1_5/8:18 1_11/16:18"
    ),
}

PIPE_PAIRS = {
    "npt": "1/16:27 1/8:27 1/4:18 3/8:18 1/2:14 3/4:14 1:11.5 1_1/4:11.5 1_1/2:11.5 2:11.5",
    "bsp": "1/8:28 1/4:19 3/8:19 1/2:14 3/4:14 1:11 1_1/4:11 1_1/2:11 2:11",
}

FAMILIES = {
    "metric": {
        "label": "ISO metric (M)",
        "group": "Machine threads",
        "kind": "machine",
        "standard": "ISO 68-1 / ISO 724 / ISO 965",
        "unit": "mm",
        "default_size": "M10x1.5",
        "help": "General-purpose 60° fastening thread. Diameter and pitch are in millimetres; coarse and fine pitches are listed explicitly.",
        "fit_help": "6H internal / 6g external is a common general-purpose pair. The number sets tolerance width (larger is wider); the letter sets its position. Uppercase is internal. Fit is not a strength grade.",
        "classes": {
            "internal": ["6H", "6G", "5H", "7H"],
            "external": ["6g", "6h", "4h", "8g"],
        },
    },
    "unc": {
        "label": "Unified coarse (UNC)",
        "group": "Machine threads",
        "kind": "machine",
        "standard": "ASME B1.1",
        "unit": "in",
        "default_size": "1/4-20 UNC",
        "help": "General-purpose 60° inch fastening thread. The number after the dash is threads per inch (TPI).",
    },
    "unf": {
        "label": "Unified fine (UNF)",
        "group": "Machine threads",
        "kind": "machine",
        "standard": "ASME B1.1",
        "unit": "in",
        "default_size": "1/4-28 UNF",
        "help": "Finer pitch than UNC at the same nominal diameter. Match the series to the mating component, not just its diameter.",
    },
    "unef": {
        "label": "Unified extra fine (UNEF)",
        "group": "Machine threads",
        "kind": "machine",
        "standard": "ASME B1.1",
        "unit": "in",
        "default_size": "1/4-32 UNEF",
        "help": "Extra-fine 60° inch thread. Used where the design calls for a fine pitch; it is not interchangeable with UNC or UNF.",
    },
    "npt": {
        "label": "NPT · tapered pipe",
        "group": "Pipe threads",
        "kind": "pipe",
        "standard": "ASME B1.20.1",
        "unit": "in",
        "default_size": "1/4",
        "help": "60° pipe thread, tapered 1:16 on diameter. The nominal pipe size is not the measured outside diameter. Thread sealant is normally required.",
        "fit_help": "NPT has its own gaging requirements. Do not append a Unified 2A or 2B class.",
        "classes": {"internal": [], "external": []},
    },
    "nptf": {
        "label": "NPTF · Dryseal pipe",
        "group": "Pipe threads",
        "kind": "pipe",
        "standard": "ASME B1.20.3",
        "unit": "in",
        "default_size": "1/4",
        "help": "60° tapered Dryseal thread with controlled crest/root interference. Do not substitute NPT or infer a pressure rating from the thread designation.",
        "fit_help": "Classes 1 and 2 have the same basic dimensions. Class 2 additionally requires inspection of crest/root truncation. This is not a pressure or strength class.",
        "classes": {"internal": ["1", "2"], "external": ["1", "2"]},
    },
    "bspp": {
        "label": "BSPP · parallel pipe (G)",
        "group": "Pipe threads",
        "kind": "pipe",
        "standard": "ISO 228-1",
        "unit": "in",
        "default_size": "1/4",
        "help": "55° parallel pipe thread. The pressure seal is made at a separate face, washer, or seal feature, not by the thread itself.",
        "fit_help": "G external threads have tolerance classes A (closer) and B (wider). Internal G threads have one tolerance class and no A/B suffix.",
        "classes": {"internal": [], "external": ["A", "B"]},
    },
    "bspt": {
        "label": "BSPT / ISO 7 (R, Rc, Rp)",
        "group": "Pipe threads",
        "kind": "pipe",
        "standard": "ISO 7-1",
        "unit": "in",
        "default_size": "1/4",
        "help": "55° jointing thread. R is tapered external, Rc is tapered internal, and Rp is parallel internal. Taper is 1:16 on diameter. Rp is not the same specification as G.",
        "fit_help": "Select the internal form explicitly: Rc tapered or Rp parallel. Both mate with R external under ISO 7; they do not use Unified fit classes.",
        "classes": {"internal": ["Rc", "Rp"], "external": ["R"]},
    },
    "forming_metal": {
        "label": "Thread-forming screw · metal",
        "group": "Self-forming & wood screws",
        "kind": "product",
        "standard": "Supplier product specification; DIN 7500 where applicable",
        "unit": "mm",
        "help": "A forming screw displaces material in a pilot hole. Specify a product (for example a DIN 7500 screw) and the substrate. Pilot diameter and installation torque need supplier data and application tests.",
    },
    "forming_plastic": {
        "label": "Thread-forming screw · plastic",
        "group": "Self-forming & wood screws",
        "kind": "product",
        "standard": "Supplier product specification",
        "unit": "mm",
        "help": "Plastic-fastening screws use product-specific profiles, such as EJOT DELTA PT. Specify the resin, reinforcement, boss, pilot hole, and installation requirements using that product's data.",
    },
    "wood": {
        "label": "Wood / structural timber screw",
        "group": "Self-forming & wood screws",
        "kind": "product",
        "standard": "Supplier specification and applicable product evaluation",
        "unit": "mm",
        "help": "Specify a screw product, diameter and length, head/drive, coating, and timber. Structural capacity depends on the product evaluation, wood, penetration, spacing, load direction, and service conditions.",
    },
}

for _key in UNIFIED_PAIRS:
    FAMILIES[_key]["classes"] = {
        "internal": ["2B", "1B", "3B"],
        "external": ["2A", "1A", "3A"],
    }
    FAMILIES[_key]["fit_help"] = (
        "A means external; B means internal. Class 2 is the usual general-purpose "
        "choice, Class 1 has wider tolerances, and Class 3 is closer. "
        "A 3A/3B thread is not a stronger bolt."
    )


MANUFACTURING_METHODS = {
    "unspecified": {
        "label": "Not specified",
        "sides": ["internal", "external", "product"],
        "help": "Leave the process to the manufacturer unless the design requires a specific method.",
    },
    "turned": {
        "label": "Turned / single-point cut",
        "sides": ["internal", "external"],
        "help": "A cutting tool generates the thread. Specify entry, runout, and relief separately where required.",
    },
    "cut_tapped": {
        "label": "Cut tapped",
        "sides": ["internal"],
        "help": "The tap removes material. Pilot-hole and chip-clearance requirements depend on the tool and material.",
    },
    "form_tapped": {
        "label": "Form tapped (displaced material)",
        "sides": ["internal"],
        "help": "The tap displaces material without cutting chips. Confirm material ductility, pilot-hole size, lubrication, and usable thread depth with the tool supplier.",
    },
    "rolled": {
        "label": "Rolled / formed external",
        "sides": ["external"],
        "help": "Dies displace material to form an external thread. Confirm material condition, blank diameter, runout, and the manufacturing sequence. No strength increase is assumed.",
    },
    "milled": {
        "label": "Thread milled",
        "sides": ["internal", "external"],
        "help": "A milling cutter generates the helix. Confirm tool access and entry/runout requirements.",
    },
    "ground": {
        "label": "Thread ground",
        "sides": ["internal", "external"],
        "help": "Specify grinding and the required finished condition when the part design requires it.",
    },
    "supplier": {
        "label": "Per supplier product specification",
        "sides": ["product"],
        "help": "Use the selected screw product's manufacturing and installation requirements.",
    },
}

MATERIAL_FAMILIES = {
    "unspecified": "Not specified / parent drawing",
    "steel": "Carbon / alloy steel",
    "stainless": "Stainless steel",
    "aluminium": "Aluminium alloy",
    "brass": "Brass / copper alloy",
    "titanium": "Titanium alloy",
    "plastic": "Engineering plastic",
    "other": "Other material",
}


def specification_options() -> dict[str, Any]:
    """Return independent expert-option catalogs, with no inferred strengths.

    ---Parameters---

    ---Returns---
    processes : dict
        Manufacturing methods with applicable thread sides and process guidance.
    materials : dict
        Material-family labels. Exact alloy, condition, and strength are separate.

    ---LaTeX---
    No numerical equations are used. Process guidance follows Sandvik Coromant's
    Threading Application Guide and Gühring's fluteless-tap guide. A process
    selection does not alter standardized nominal geometry or load capacity.
    """
    return {
        "processes": deepcopy(MANUFACTURING_METHODS),
        "materials": dict(MATERIAL_FAMILIES),
    }


def _pairs(text: str) -> list[tuple[str, str]]:
    """Decode compact nominal pairs into (size text, TPI text) tuples.

    Parameters: text is whitespace-separated size:TPI data with underscores
    for mixed-number spaces. Returns a fresh list; no dimensions are rounded.
    """
    return [tuple(item.replace("_", " ").split(":")) for item in text.split()]


def specification_catalog() -> dict[str, dict[str, Any]]:
    """Return independent family metadata and nominal size choices.

    ---Parameters---

    ---Returns---
    families : dict
        Keyed family definitions with labels, fit choices, units, guidance,
        standards, and sizes. This is a working catalog, not every standard size.

    ---LaTeX---
    P = 25.4 / TPI

    P: pitch in millimetres. TPI: threads per inch. References are in the
    module docstring. No numerical tolerance limits are computed.
    """
    families = deepcopy(FAMILIES)
    for key, family in families.items():
        machine = family["kind"] == "machine"
        family["capabilities"] = {
            "specify": True,
            "identify_external": machine,
            "identify_internal": machine,
            "print_pitch": family["kind"] != "product",
            "print_profile": machine,
            "step": machine,
        }
        if key == "metric":
            family["sizes"] = [
                record["designation"] for record in get_thread_catalog()["iso_metric"]
            ]
        elif key in UNIFIED_PAIRS:
            family["sizes"] = [
                f"{size}-{tpi} {key.upper()}"
                for size, tpi in _pairs(UNIFIED_PAIRS[key])
            ]
        elif family["kind"] == "pipe":
            family["sizes"] = [
                size
                for size, _ in _pairs(
                    PIPE_PAIRS["npt" if key in ("npt", "nptf") else "bsp"]
                )
            ]
        else:
            family["sizes"] = []
    return families


def _text(value: Any, label: str) -> str:
    """Validate user text as one line, up to 240 characters.

    Parameters: value is a string and label names it in errors. Returns trimmed
    text. Raises ValueError for control characters or excessive length, keeping
    pasted specifications from adding hidden note lines.
    """
    if (
        not isinstance(value, str)
        or len(value) > 240
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise ValueError(f"{label} must be a single line of at most 240 characters.")
    return value.strip()


def _positive(value: Any, label: str) -> str:
    """Return a finite positive dimension as decimal text, or raise ValueError.

    Parameters: value is numeric text in the selected units; label identifies
    the field. Returns up to ten significant figures, without unit conversion.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        # Expected input validation should not expose float()'s conversion error.
        raise ValueError(f"Enter a positive {label}.") from None
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"Enter a positive {label}.")
    return f"{number:.10g}"


def build_thread_specification(state_json: str = "{}") -> dict[str, Any]:
    r"""Build a drawing callout and a detailed, reviewable specification note.

    Family and size choices are validated against the nominal catalog. A short
    callout identifies a thread, not a complete joint design. Unresolved material,
    coating, seal, or supplier decisions remain in the copied detailed note.
    No fastener grade, pressure rating, pilot diameter, or thread tolerance limits
    are inferred. References: ISO 965, ASME B1.1, ASME B1.20.1/B1.20.3, ISO 228-1,
    ISO 7-1 and supplier guides listed in the module docstring.

    ---Parameters---
    state_json : str
        JSON object. family: catalog key (default metric); size: nominal catalog
        choice; side: internal/external; fit: family-compatible class; hand: RH/LH;
        extent: thru/blind/length/unspecified; depth: positive usable full-thread length in
        the family unit. Optional material, finish, inspection, seal: single-line
        drawing requirements. Product families use product, screw_diameter,
        screw_length, product_unit (mm/in), head, and substrate instead of fit,
        side, hand, or thread depth. Missing product fields generate a draft.
        process: manufacturing-method key. material_family: material-category key.
        Neither option supplies mechanical properties or changes basic geometry.

    ---Returns---
    callout : str
        Short ASCII drawing callout or explicitly marked draft procurement note.
    note : str
        Detailed plain-text note, including unresolved review items.
    review_items : list
        Requirements still to be decided or verified before releasing a drawing.
    breakdown : list
        Label/value pairs explaining the actual chosen specification.
    family : str
        Selected family key.
    kind : str
        machine, pipe, or product. Pipe and product have no machine geometry.
    side : str
        internal or external for drawn threads; product for procurement notes.
    status : str
        Thread callout with review items, or product procurement draft.
    diagram : dict or None
        Pipe schematic annotations (pitch, included angle, diameter taper and
        half-angle to the axis), or validated supplier-entered product dimensions.
        Unknown product dimensions are None. Machine threads use the separate
        canonical geometry result. No pipe gage-plane diameter is inferred.

    ---LaTeX---
    P = \frac{25.4}{TPI}
    \beta = \arctan\left(\frac{T}{2}\right)

    P: pitch in millimetres; TPI: threads per inch; T: diameter change divided
    by axial distance (1/16 for NPT, NPTF and R/Rc; zero for G/Rp); beta:
    half-angle to the axis. This function does not compute tolerances or capacity.
    """
    try:
        state = json.loads(state_json)
    except (TypeError, ValueError) as error:
        raise ValueError("Specification input must be a JSON object.") from error
    if not isinstance(state, dict):
        raise ValueError("Specification input must be a JSON object.")  # noqa: TRY004 (invalid JSON schema)
    family_key = state.get("family", "metric")
    families = specification_catalog()
    if not isinstance(family_key, str) or family_key not in families:
        raise ValueError("Choose a supported thread family.")
    family = families[family_key]
    kind = family["kind"]
    review = []
    breakdown = [["Family", family["label"]], ["Thread standard", family["standard"]]]
    lines = []
    diagram = None

    if kind == "product":
        side = "product"
        product = _text(state.get("product", ""), "Product reference")
        unit = state.get("product_unit", "mm")
        if unit not in ("mm", "in"):
            raise ValueError("Product dimensions must use mm or in.")
        dimensions = []
        for key, label in (
            ("screw_diameter", "screw diameter"),
            ("screw_length", "screw length"),
        ):
            value = state.get(key, "")
            dimensions.append(
                _positive(value, label) if value != "" else f"[{label.upper()}]"
            )
            if value == "":
                review.append(
                    f"Specify {label} and its supplier-defined measurement convention."
                )
        callout = f"{product or '[MANUFACTURER / PART NUMBER]'}, {' x '.join(dimensions)} {unit}"
        lines.extend([family["label"].upper(), f"PRODUCT: {callout}"])
        if not product:
            review.append(
                "Select a manufacturer and exact product/part number; this family has no universal mating-hole callout."
            )
        for key, label in (("head", "Head / drive"), ("substrate", "Mating material")):
            value = _text(state.get(key, ""), label)
            if value:
                lines.append(f"{label.upper()}: {value}")
            else:
                review.append(f"Specify {label.lower()}.")
        review.append(
            "Confirm pilot hole, usable engagement, installation torque, and joint capacity against this product's data and the actual substrate."
        )
        if family_key == "wood":
            review.append(
                "For structural use, verify the product evaluation, timber grade/density, penetration, edge distances, spacing, and service environment."
            )
        breakdown.extend(
            [
                ["Product", product or "Not selected"],
                ["Dimensions", f"{' x '.join(dimensions)} {unit}"],
            ]
        )
        callout = "DRAFT: " + callout
        status = "Procurement draft; application checks required"
        diagram = {
            "kind": "product",
            "unit": unit,
            "diameter": float(dimensions[0])
            if state.get("screw_diameter", "") != ""
            else None,
            "length": float(dimensions[1])
            if state.get("screw_length", "") != ""
            else None,
        }
    else:
        size = state.get("size", family["default_size"])
        if size not in family["sizes"]:
            raise ValueError("Choose a listed nominal size for this family.")
        side = state.get("side", "internal")
        if side not in ("internal", "external"):
            raise ValueError("Choose internal or external thread.")
        classes = family["classes"][side]
        fit = state.get("fit", classes[0] if classes else "")
        if (classes and fit not in classes) or (not classes and fit):
            raise ValueError(
                "The selected fit/class does not apply to this family and thread side."
            )
        hand = state.get("hand", "RH")
        if hand not in ("RH", "LH") or (kind == "pipe" and hand != "RH"):
            raise ValueError(
                "Choose RH or LH for machine threads; pipe notes currently support RH only."
            )
        if family_key == "metric":
            diameter, pitch = parse_metric_thread_designation(size)
            callout = f"M{diameter * 1000:g} x {pitch * 1000:g}-{fit}"
            breakdown.extend(
                [
                    ["Major diameter", f"{diameter * 1000:g} mm"],
                    ["Pitch", f"{pitch * 1000:g} mm"],
                ]
            )
        elif family_key in UNIFIED_PAIRS:
            callout = f"{size}-{fit}"
            nominal, tpi = size.rsplit(" ", 1)[0].rsplit("-", 1)
            diameter_in = _parse_unified_size(nominal)
            breakdown.extend(
                [["Major diameter", f"{diameter_in:g} in"], ["Pitch", f"{tpi} TPI"]]
            )
        elif family_key in ("npt", "nptf"):
            tpi = dict(_pairs(PIPE_PAIRS["npt"]))[size]
            callout = f"{size}-{tpi} {family_key.upper()}" + (f"-{fit}" if fit else "")
        elif family_key == "bspp":
            callout = f"G {size}" + (f" {fit}" if fit else "")
        else:
            callout = f"{fit} {size}"
        if hand == "LH":
            callout += "-LH"
        lines.extend(
            [callout, f"{side.upper()} THREAD TO {family['standard']}; {hand}."]
        )
        breakdown.extend(
            [
                ["Thread side", side.capitalize()],
                ["Fit / form", fit or "Standard-specific, no suffix"],
                ["Hand", "Right-hand" if hand == "RH" else "Left-hand"],
            ]
        )
        if kind == "machine":
            extent = state.get("extent", "thru" if side == "internal" else "length")
            if extent not in (
                ("thru", "blind", "unspecified")
                if side == "internal"
                else ("length", "unspecified")
            ):
                raise ValueError(
                    "Internal threads must be through or blind; external threads need a full-thread length."
                )
            if extent == "unspecified":
                lines.append(
                    "NOMINAL THREAD ONLY; EXTENT TO BE SPECIFIED ON THE PART DRAWING."
                )
                review.append(
                    "Specify usable full-thread length/depth or a through hole on the part drawing."
                )
                breakdown.append(["Extent", "Not yet specified"])
            elif extent == "thru":
                callout += " THRU"
                lines.append("THREAD THROUGH.")
                breakdown.append(["Extent", "Through"])
            else:
                depth = _positive(
                    state.get("depth", ""), "usable full-thread depth / length"
                )
                extent_text = (
                    "MIN FULL THREAD DEPTH"
                    if extent == "blind"
                    else "MIN FULL THREAD LENGTH"
                )
                callout += f"\n{depth} {family['unit']} {extent_text}"
                lines.append(f"{extent_text}: {depth} {family['unit']}.")
                breakdown.append(["Usable full thread", f"{depth} {family['unit']}"])
                review.append(
                    "Dimension thread entry, runout, and relief; for a blind hole, provide drill depth separately from usable full-thread depth."
                )
            review.append(
                "Check the mating thread, engagement/stripping capacity, and applicable standard edition; this callout does not establish joint strength."
            )
        else:
            lines.append("NOMINAL PIPE SIZE IS NOT THE MEASURED OUTSIDE DIAMETER.")
            pipe_series = "npt" if family_key in ("npt", "nptf") else "bsp"
            pipe_tpi = float(dict(_pairs(PIPE_PAIRS[pipe_series]))[size])
            tapered = family_key != "bspp" and fit != "Rp"
            diameter_taper = 1 / 16 if tapered else 0.0
            diagram = {
                "kind": "pipe",
                "tpi": pipe_tpi,
                "pitch_in": 1 / pipe_tpi,
                "pitch_mm": 25.4 / pipe_tpi,
                "included_angle_deg": 60 if pipe_series == "npt" else 55,
                "diameter_taper": diameter_taper,
                "half_angle_deg": math.degrees(math.atan(diameter_taper / 2)),
            }
            taper_note = (
                f"1:16 on diameter; {diagram['half_angle_deg']:.3f} deg to axis"
                if tapered
                else "Parallel (no taper)"
            )
            breakdown.extend(
                [
                    ["Pitch", f"{pipe_tpi:g} TPI ({diagram['pitch_mm']:.4f} mm)"],
                    ["Included angle", f"{diagram['included_angle_deg']} deg"],
                    ["Taper", taper_note],
                    [
                        "Diameter at gage plane",
                        "Not included; verify the thread standard",
                    ],
                ]
            )
            lines.append(
                f"PITCH: {pipe_tpi:g} TPI; INCLUDED ANGLE: {diagram['included_angle_deg']} DEG."
            )
            lines.append("TAPER: " + taper_note.upper() + ".")
            seal = _text(state.get("seal", ""), "Seal specification")
            if seal:
                lines.append(f"SEAL / MATING CONNECTION: {seal}")
            else:
                review.append(
                    "Specify the separate sealing face/washer/O-ring and mating connection."
                    if family_key == "bspp"
                    else "Specify the mating connection and sealing/assembly requirements."
                )
            review.append(
                "Verify port geometry, gage plane, thread length, wall thickness, fluid/temperature compatibility, and the complete connection's pressure rating."
            )
            if family_key == "nptf":
                lines.append(
                    f"NPTF CLASS {fit}; USE THE APPLICABLE DRYSEAL INSPECTION REQUIREMENTS."
                )
            breakdown.append(["Nominal pipe size", size + " (not outside diameter)"])
        status = "Thread callout; review the complete part specification"

    process = state.get("process", "unspecified")
    if (
        not isinstance(process, str)
        or process not in MANUFACTURING_METHODS
        or side not in MANUFACTURING_METHODS[process]["sides"]
    ):
        raise ValueError(
            "Choose a manufacturing method compatible with this thread side."
        )
    material_family = state.get("material_family", "unspecified")
    if not isinstance(material_family, str) or material_family not in MATERIAL_FAMILIES:
        raise ValueError("Choose a listed material family.")
    if process != "unspecified":
        lines.append(f"THREAD MANUFACTURE: {MANUFACTURING_METHODS[process]['label']}.")
        breakdown.append(
            ["Manufacturing method", MANUFACTURING_METHODS[process]["label"]]
        )
        review.append(MANUFACTURING_METHODS[process]["help"])
    if material_family != "unspecified":
        lines.append(f"MATERIAL FAMILY: {MATERIAL_FAMILIES[material_family]}.")
        breakdown.append(["Material family", MATERIAL_FAMILIES[material_family]])
        review.append(
            "Confirm the exact alloy/resin, condition, product standard, and verified mechanical properties; a material-family label is not a strength value."
        )

    for key, label in (
        ("material", "Part material / hardware grade"),
        ("finish", "Finish / coating"),
        ("inspection", "Inspection requirement"),
    ):
        value = _text(state.get(key, ""), label)
        if value:
            lines.append(f"{label.upper()}: {value}")
        else:
            review.append(f"Specify {label.lower()} here or on the parent drawing.")
    if kind != "product":
        lines.append(
            "VERIFY THREAD ACCEPTANCE AT THE SPECIFIED FINISHED CONDITION; ACCOUNT FOR COATING."
        )
    note = (
        "\n".join(lines)
        + "\n\nDRAWING REVIEW ITEMS (NOT YET SPECIFIED):\n"
        + "\n".join(f"- {item}" for item in review)
    )
    return {
        "callout": callout,
        "note": note,
        "review_items": review,
        "breakdown": breakdown,
        "family": family_key,
        "kind": kind,
        "side": side,
        "status": status,
        "diagram": diagram,
    }


def analyze_thread_workflow(state_json: str = "{}") -> dict[str, Any]:
    r"""Build one consistent specification/profile result for all three tasks.

    Reuses :func:`build_thread_specification`, the canonical 60-degree geometry
    in fasteners, and the existing threads identification/axial screen. Pipe and
    product-specific families never receive machine-thread capacity calculations.

    ---Parameters---
    state_json : str
        Specification state plus task (specify/load/explore), identify (boolean,
        explore only), measured_diameter (mm for metric, inches for Unified),
        measured_pitch (mm for metric, TPI for Unified), axial_load (kN),
        proof_strength (MPa), design_factor (at least 1), and series
        (coarse/fine/all for metric; UNC and UNF select their named series).
        Expert process/material choices are note requirements, not strength data.

    ---Returns---
    task : str
        Selected task.
    specification : dict
        Callout, note, explanations, and review items; None if no size passes.
    geometry : dict
        Canonical metric/Unified basic geometry, or None for pipe/product/no-size.
    analysis : dict
        Existing calculation evidence for load or identification, otherwise None.
    resolved_family : str
        Family of the selected or identified nominal thread.
    resolved_size : str
        Selected/identified nominal designation, empty if no size passes.

    ---LaTeX---
    F_d = n F, \quad F_p = S_p A_s

    F_d: factored axial demand; n: design factor; F: service axial load;
    F_p: proof capacity; S_p: verified minimum proof strength; A_s: tensile area.
    Equations and reference details are implemented in pycalcs.threads, without
    a duplicate sizing calculation here. References: ISO 68-1, ISO 724, ASME B1.1,
    NASA fastener training material, and NIST Handbook 28.
    """
    try:
        state = json.loads(state_json)
    except (TypeError, ValueError):
        raise ValueError("Thread inputs must be a JSON object.") from None
    if not isinstance(state, dict):
        raise ValueError("Thread inputs must be a JSON object.")  # noqa: TRY004
    task = state.get("task", "specify")
    if task not in ("specify", "load", "explore"):
        raise ValueError("Choose Specify, Design for load, or Explore.")
    family = state.get("family", "metric")
    if not isinstance(family, str) or family not in FAMILIES:
        raise ValueError("Choose a supported thread family.")
    analysis = None
    identify = task == "explore" and state.get("identify") is True
    if task == "load" or identify:
        if family not in ("metric", "unc", "unf"):
            raise ValueError(
                "Load design and measured identification currently support metric, UNC, and UNF catalogs only."
            )
        system = "iso_metric" if family == "metric" else "unified"
        diameter, pitch = (9.96, 1.5) if system == "iso_metric" else (0.25, 20)
        load, proof, factor = 20.0, 580.0, 1.5
        if identify:
            diameter = float(
                _positive(
                    state.get("measured_diameter", diameter),
                    "measured outside diameter",
                )
            )
            pitch = float(
                _positive(state.get("measured_pitch", pitch), "measured pitch / TPI")
            )
        else:
            load = float(_positive(state.get("axial_load", load), "axial service load"))
            proof = float(
                _positive(
                    state.get("proof_strength", proof),
                    "verified minimum proof strength",
                )
            )
            factor = float(
                _positive(state.get("design_factor", factor), "design factor")
            )
        analysis = analyze_thread(
            "identify" if identify else "size",
            system,
            "M10x1.5" if system == "iso_metric" else "1/4-20 UNC",
            diameter / 1000 if system == "iso_metric" else diameter * 0.0254,
            pitch / 1000 if system == "iso_metric" else 0.0254 / pitch,
            load * 1000,
            proof * 1e6,
            factor,
            "all"
            if identify
            else state.get("series", "coarse")
            if family == "metric"
            else "coarse"
            if family == "unc"
            else "fine",
        )
        if task == "load" and analysis["sizing_status"] == "no_size":
            return {
                "task": task,
                "specification": None,
                "geometry": None,
                "analysis": analysis,
                "resolved_family": family,
                "resolved_size": "",
            }
        family = (
            "metric"
            if system == "iso_metric"
            else "unc"
            if analysis["designation"].endswith("UNC")
            else "unf"
        )
        state["family"] = family
        state["size"] = analysis["designation"]
        if task == "load":
            state.setdefault("side", "external")
            state.setdefault("extent", "unspecified")
    specification = build_thread_specification(json.dumps(state))
    size = state.get("size", FAMILIES[family].get("default_size", ""))
    geometry = None
    if FAMILIES[family]["kind"] == "machine":
        if family == "metric":
            diameter, pitch = parse_metric_thread_designation(size)
        else:
            nominal, tpi = size.rsplit(" ", 1)[0].rsplit("-", 1)
            diameter, pitch = _parse_unified_size(nominal) * 0.0254, 0.0254 / float(tpi)
        geometry = calculate_basic_thread_geometry(
            "iso_metric" if family == "metric" else "unified", diameter, pitch
        )
        series = family.upper()
        if family == "metric":
            series = next(
                record["series"]
                for record in get_thread_catalog()["iso_metric"]
                if record["designation"] == size
            )
        geometry.update({"designation": size, "mode": "explore", "series": series})
        try:
            from .thread_models import physical_profile
        except ImportError:
            from thread_models import physical_profile
        geometry["physical_model"] = physical_profile(geometry)
    if identify:
        caution = "NOMINAL MATCH ONLY. Measurements do not establish fit class, handedness, or feature extent. Verify these drawing choices."
        specification["note"] = caution + "\n\n" + specification["note"]
        specification["review_items"].insert(0, caution)
        specification["status"] = "Nominal match; fit and drawing details are assumed"
    elif task == "load":
        scope = f"AXIAL TENSION SCREEN ONLY: {load:g} kN service load; {proof:g} MPa specified minimum proof strength; required margin {factor:g}. Engagement, stripping, fatigue, and joint preload are not checked."
        specification["note"] = scope + "\n\n" + specification["note"]
        specification["review_items"].insert(0, scope)
        specification["status"] = (
            "Preliminary axial selection; joint design checks remain"
        )
    return {
        "task": task,
        "specification": specification,
        "geometry": geometry,
        "analysis": analysis,
        "resolved_family": family,
        "resolved_size": size,
    }
