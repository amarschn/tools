"""Nominal dimensions for screw families specified as products, not callouts.

These families are bought by product reference rather than by a drawing thread
callout, so most of what matters (head, drive, point, coating, pilot hole,
installation torque) comes from the supplier. Two of them still have a
published nominal thread that the tool can state exactly instead of leaving
blank.

Wood screws follow ASME B18.6.1, which sets nominal diameter by screw number as
d = 0.060 + 0.013 N inches, with a threads-per-inch value per size. Every row
below satisfies that identity, and `tests/test_screw_products.py` asserts it as
a transcription check.

DIN 7500 thread-forming screws for metal cut no chips: the trilobular shank
forms an ISO metric thread in the workpiece, so the screw's own thread is an
ordinary ISO metric thread and its basic dimensions come from the shared metric
geometry rather than from a separate table here.

Pilot and core hole diameters are deliberately absent. For wood they depend on
species and density, and for DIN 7500 they depend on material and engagement
length, so a single published number would be wrong more often than right.
Neither is a value this tool can state without the supplier's own data.

Sources are listed in the tool README: the Engineers Edge ANSI B18.6.1 wood
screw table, and the DIN 7500 size range as published by fastener suppliers.
"""

from __future__ import annotations

from typing import Any

MM_PER_INCH = 25.4

# ASME B18.6.1 screw number: (basic nominal diameter in inches, threads per inch).
WOOD_SCREW_BASIC = {
    "#0": (0.060, 32),
    "#1": (0.073, 28),
    "#2": (0.086, 26),
    "#3": (0.099, 24),
    "#4": (0.112, 22),
    "#5": (0.125, 20),
    "#6": (0.138, 18),
    "#7": (0.151, 16),
    "#8": (0.164, 15),
    "#9": (0.177, 14),
    "#10": (0.190, 13),
    "#12": (0.216, 11),
    "#14": (0.242, 10),
    "#16": (0.268, 9),
    "#18": (0.294, 8),
    "#20": (0.320, 8),
    "#24": (0.372, 7),
}

# ASME B18.6.1 nominal diameter rule, used as a transcription check.
WOOD_SCREW_BASE_DIAMETER = 0.060
WOOD_SCREW_DIAMETER_STEP = 0.013

# DIN 7500 covers these ISO metric threads. The thread itself is ISO metric, so
# its dimensions come from the metric geometry, not from a table here.
FORMING_METAL_SIZES = (
    "M2x0.4",
    "M2.5x0.45",
    "M3x0.5",
    "M4x0.7",
    "M5x0.8",
    "M6x1.0",
    "M8x1.25",
    "M10x1.5",
)

PRODUCT_SIZES = {
    "wood": tuple(WOOD_SCREW_BASIC),
    "forming_metal": FORMING_METAL_SIZES,
    # Plastic-fastening screws use proprietary profiles with supplier-specific
    # flank angles and pitches, so there is no standard list to offer.
    "forming_plastic": (),
}


def product_sizes(family: str) -> list[str]:
    """List the nominal sizes carried for one product family."""
    if family not in PRODUCT_SIZES:
        raise ValueError("Unknown product family.")
    return list(PRODUCT_SIZES[family])


def wood_screw_number(size: str) -> int:
    """Return the ASME B18.6.1 screw number from a '#8' style designation."""
    return int(size.lstrip("#"))


def product_dimensions(family: str, size: str) -> dict[str, Any]:
    """Return nominal thread dimensions for one product size.

    Parameters:
        family: wood or forming_metal.
        size: a size listed for that family.

    Returns:
        Millimetre dimensions plus the unit the standard states them in.
        ``pitch_mm`` and ``major_mm`` are nominal, not acceptance limits, and
        carry no head, point, or pilot-hole information.

    Raises:
        ValueError: for a family with no size list, or an unlisted size.
    """
    if family == "wood":
        if size not in WOOD_SCREW_BASIC:
            raise ValueError("No basic dimensions carried for this screw size.")
        diameter_in, tpi = WOOD_SCREW_BASIC[size]
        return {
            "family": family,
            "size": size,
            "designation": size,
            "callout_size": size,
            "standard": "ASME B18.6.1",
            "unit": "in",
            "tpi": float(tpi),
            "pitch_mm": MM_PER_INCH / tpi,
            "major_mm": diameter_in * MM_PER_INCH,
            "included_angle_deg": None,
        }
    if family == "forming_metal":
        if size not in FORMING_METAL_SIZES:
            raise ValueError("No basic dimensions carried for this screw size.")
        diameter_mm, pitch_mm = (float(part) for part in size[1:].split("x"))
        return {
            "family": family,
            "size": size,
            "designation": size.replace("x", " x "),
            # A DIN 7500 size implies its pitch, so the callout carries M5, not M5 x 0.8.
            "callout_size": size.split("x")[0],
            "standard": "DIN 7500 with an ISO 68-1 metric thread",
            "unit": "mm",
            "tpi": MM_PER_INCH / pitch_mm,
            "pitch_mm": pitch_mm,
            "major_mm": diameter_mm,
            "included_angle_deg": 60.0,
        }
    raise ValueError("This product family has no standard size list.")
