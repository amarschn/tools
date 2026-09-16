"""Basic pipe-thread dimensions and the diameters derived from them.

Each table stores only the anchor values the standard publishes. Every other
diameter is derived here with the standard's own form equations, so one
transcribed number cannot disagree with a second transcribed number.

NPT and NPTF (ASME B1.20.1, ASME B1.20.3): 60 degree form truncated to a basic
thread height h = 0.8 P, tapered 1:16 on diameter. Stored per size are threads
per inch, pipe outside diameter, pitch diameter at the small end of the external
thread (E0), length of hand-tight engagement (L1), and length of effective
thread (L2). The pitch diameter at the gage plane follows from the taper as
E1 = E0 + L1 / 16, which every stored row satisfies exactly and which
`tests/test_pipe_threads.py` asserts as a transcription check.

BSPP (ISO 228-1) and BSPT / ISO 7-1: 55 degree Whitworth form with rounded
crests and roots, basic thread height h = 0.640327 P. BSPP is parallel, so one
major diameter describes the whole thread. ISO 7-1 uses the same basic
diameters taken at the gauge plane, plus a gauge length from the small end and a
useful thread length.

Values are transcribed from the sources listed in the tool README: the AmesWeb
ASME B1.20.1 and ISO 228-1 charts, cross-checked against Engineers Edge and the
Wikipedia British Standard Pipe table for BSP, and against the taper identity
above for NPT. These are basic dimensions, not acceptance limits, and no gaging
or pressure conclusion follows from them.
"""

from __future__ import annotations

from typing import Any

MM_PER_INCH = 25.4

# Whitworth 55 degree basic thread height factor, ISO 228-1 and ISO 7-1.
WHITWORTH_HEIGHT_FACTOR = 0.640327
# American taper pipe thread basic height factor, ASME B1.20.1.
AMERICAN_HEIGHT_FACTOR = 0.8
# Taper on diameter, both families.
DIAMETER_TAPER = 1 / 16

# size: (threads per inch, pipe outside diameter, E0, L1, L2), all inches.
NPT_BASIC = {
    "1/16": (27, 0.3125, 0.27118, 0.1600, 0.2611),
    "1/8": (27, 0.4050, 0.36351, 0.1615, 0.2639),
    "1/4": (18, 0.5400, 0.47739, 0.2278, 0.4018),
    "3/8": (18, 0.6750, 0.61201, 0.2400, 0.4078),
    "1/2": (14, 0.8400, 0.75843, 0.3200, 0.5337),
    "3/4": (14, 1.0500, 0.96768, 0.3390, 0.5457),
    "1": (11.5, 1.3150, 1.21363, 0.4000, 0.6828),
    "1 1/4": (11.5, 1.6600, 1.55713, 0.4200, 0.7068),
    "1 1/2": (11.5, 1.9000, 1.79609, 0.4200, 0.7235),
    "2": (11.5, 2.3750, 2.26902, 0.4360, 0.7565),
}

# size: (threads per inch, major diameter in mm). Parallel, one plane.
BSPP_BASIC = {
    "1/8": (28, 9.728),
    "1/4": (19, 13.157),
    "3/8": (19, 16.662),
    "1/2": (14, 20.955),
    "3/4": (14, 26.441),
    "1": (11, 33.249),
    "1 1/4": (11, 41.910),
    "1 1/2": (11, 47.803),
    "2": (11, 59.614),
}

# size: (threads per inch, major diameter at gauge plane mm, gauge length mm,
# useful thread length mm). Diameters match BSPP for the same designation.
BSPT_BASIC = {
    "1/8": (28, 9.728, 4.0, 6.5),
    "1/4": (19, 13.157, 6.0, 9.7),
    "3/8": (19, 16.662, 6.4, 10.1),
    "1/2": (14, 20.955, 8.2, 13.2),
    "3/4": (14, 26.441, 9.5, 14.5),
    "1": (11, 33.249, 10.4, 16.8),
    "1 1/4": (11, 41.910, 12.7, 19.1),
    "1 1/2": (11, 47.803, 12.7, 19.1),
    "2": (11, 59.614, 15.9, 23.4),
}

PIPE_FAMILIES = ("npt", "nptf", "bspp", "bspt")


def _table(family: str) -> dict[str, tuple]:
    """Return the anchor table backing one pipe family."""
    if family in ("npt", "nptf"):
        return NPT_BASIC
    if family == "bspp":
        return BSPP_BASIC
    if family == "bspt":
        return BSPT_BASIC
    raise ValueError("Unknown pipe family.")


def pipe_sizes(family: str) -> list[str]:
    """List the nominal sizes carried for one pipe family, in table order."""
    return list(_table(family))


def pipe_dimensions(family: str, size: str, parallel: bool = False) -> dict[str, Any]:
    """Return basic millimetre dimensions for one nominal pipe size.

    Parameters:
        family: one of npt, nptf, bspp, bspt.
        size: a nominal size listed for that family.
        parallel: treat an ISO 7 internal thread as the parallel Rp form, which
            has no taper and one set of diameters.

    Returns:
        A dictionary of millimetre dimensions. ``major_mm``/``pitch_mm_dia``/
        ``minor_mm`` are taken at the gage plane for a tapered thread and at the
        single plane of a parallel thread. ``external_major_band_mm`` and
        ``internal_minor_band_mm`` give the [smallest, largest] diameter a
        measurement can legitimately land on along the thread's own length; for
        a parallel thread both ends of the band are equal.

    Raises:
        ValueError: for an unknown family or size.
    """
    table = _table(family)
    if size not in table:
        raise ValueError("No basic dimensions carried for this pipe size.")

    if family in ("npt", "nptf"):
        tpi, outside_in, e0_in, l1_in, l2_in = table[size]
        pitch_in = 1 / tpi
        height_in = AMERICAN_HEIGHT_FACTOR * pitch_in
        gage_pitch_in = e0_in + l1_in * DIAMETER_TAPER
        # Pitch diameter at the small end and at the end of the effective thread.
        low_pitch_in = e0_in
        high_pitch_in = e0_in + l2_in * DIAMETER_TAPER
        result = {
            "family": family,
            "size": size,
            "tpi": float(tpi),
            "pitch_mm": pitch_in * MM_PER_INCH,
            "included_angle_deg": 60.0,
            "thread_height_mm": height_in * MM_PER_INCH,
            "outside_diameter_mm": outside_in * MM_PER_INCH,
            "gage_length_mm": l1_in * MM_PER_INCH,
            "effective_length_mm": l2_in * MM_PER_INCH,
            "pitch_diameter_small_end_mm": e0_in * MM_PER_INCH,
            "major_mm": (gage_pitch_in + height_in) * MM_PER_INCH,
            "pitch_mm_dia": gage_pitch_in * MM_PER_INCH,
            "minor_mm": (gage_pitch_in - height_in) * MM_PER_INCH,
            "external_major_band_mm": (
                (low_pitch_in + height_in) * MM_PER_INCH,
                (high_pitch_in + height_in) * MM_PER_INCH,
            ),
            "internal_minor_band_mm": (
                (low_pitch_in - height_in) * MM_PER_INCH,
                (high_pitch_in - height_in) * MM_PER_INCH,
            ),
            "tapered": True,
            "unit": "in",
        }
        return result

    if family == "bspp":
        tpi, major_mm = table[size]
        gage_length_mm = useful_mm = None
        tapered = False
    else:
        tpi, major_mm, gage_length_mm, useful_mm = table[size]
        tapered = not parallel

    pitch_mm = MM_PER_INCH / tpi
    height_mm = WHITWORTH_HEIGHT_FACTOR * pitch_mm
    if tapered:
        # Walk back from the gauge plane to the small end, then forward along
        # the useful thread. Both moves change the diameter by length / 16.
        low_major = major_mm - gage_length_mm * DIAMETER_TAPER
        high_major = low_major + useful_mm * DIAMETER_TAPER
    else:
        low_major = high_major = major_mm
    return {
        "family": family,
        "size": size,
        "tpi": float(tpi),
        "pitch_mm": pitch_mm,
        "included_angle_deg": 55.0,
        "thread_height_mm": height_mm,
        "outside_diameter_mm": None,
        "gage_length_mm": gage_length_mm,
        "effective_length_mm": useful_mm,
        "pitch_diameter_small_end_mm": None,
        "major_mm": major_mm,
        "pitch_mm_dia": major_mm - height_mm,
        "minor_mm": major_mm - 2 * height_mm,
        "external_major_band_mm": (low_major, high_major),
        "internal_minor_band_mm": (
            low_major - 2 * height_mm,
            high_major - 2 * height_mm,
        ),
        "tapered": tapered,
        "unit": "mm",
    }
