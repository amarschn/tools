"""Transcription and derivation checks for the pipe-thread basic dimensions.

The point of these tests is that a mistyped digit in one of the anchor tables
should fail here rather than reach a drawing. Each standard supplies an
identity the stored values must satisfy independently of the value being
checked, so a typo cannot pass by agreeing with itself.
"""

import pytest

from pycalcs.pipe_threads import (
    AMERICAN_HEIGHT_FACTOR,
    BSPP_BASIC,
    BSPT_BASIC,
    DIAMETER_TAPER,
    NPT_BASIC,
    WHITWORTH_HEIGHT_FACTOR,
    pipe_dimensions,
    pipe_sizes,
)
from pycalcs.thread_specifications import specification_catalog

# ASME B1.20.1 Table 1, pitch diameter at the gage plane, in inches.
PUBLISHED_NPT_GAGE_PITCH = {
    "1/16": 0.28118,
    "1/8": 0.37360,
    "1/4": 0.49163,
    "3/8": 0.62701,
    "1/2": 0.77843,
    "3/4": 0.98887,
    "1": 1.23863,
    "1 1/4": 1.58338,
    "1 1/2": 1.82234,
    "2": 2.29627,
}

# ISO 228-1, basic pitch and minor diameters in millimetres.
PUBLISHED_BSPP_DIAMETERS = {
    "1/8": (9.147, 8.566),
    "1/4": (12.301, 11.445),
    "3/8": (15.806, 14.950),
    "1/2": (19.793, 18.631),
    "3/4": (25.279, 24.117),
    "1": (31.770, 30.291),
    "1 1/4": (40.431, 38.952),
    "1 1/2": (46.324, 44.845),
    "2": (58.135, 56.656),
}


@pytest.mark.parametrize("size", list(NPT_BASIC))
def test_npt_gage_plane_follows_the_taper_from_the_small_end(size):
    """E1 = E0 + L1/16 must hold, which catches a typo in E0, L1 or E1."""
    _, _, e0_in, l1_in, _ = NPT_BASIC[size]
    assert e0_in + l1_in * DIAMETER_TAPER == pytest.approx(
        PUBLISHED_NPT_GAGE_PITCH[size], abs=5e-6
    )


@pytest.mark.parametrize("size", list(NPT_BASIC))
def test_npt_major_diameter_stays_under_the_pipe_outside_diameter(size):
    """The crest is truncated into the pipe wall, so major is under the OD."""
    _, outside_in, _, _, _ = NPT_BASIC[size]
    dimensions = pipe_dimensions("npt", size)
    major_in = dimensions["major_mm"] / 25.4
    assert 0.9 * outside_in < major_in < outside_in


@pytest.mark.parametrize("size", list(NPT_BASIC))
def test_npt_effective_thread_is_longer_than_hand_tight_engagement(size):
    """L2 runs past L1 by definition; a swapped pair would fail here."""
    _, _, _, l1_in, l2_in = NPT_BASIC[size]
    assert l2_in > l1_in


@pytest.mark.parametrize("size", list(BSPP_BASIC))
def test_bspp_diameters_match_the_published_whitworth_values(size):
    """Deriving from the major diameter must reproduce the printed table."""
    pitch_mm, minor_mm = PUBLISHED_BSPP_DIAMETERS[size]
    dimensions = pipe_dimensions("bspp", size)
    assert dimensions["pitch_mm_dia"] == pytest.approx(pitch_mm, abs=1e-3)
    assert dimensions["minor_mm"] == pytest.approx(minor_mm, abs=1e-3)


def test_bspt_shares_bspp_sizes_pitches_and_gauge_plane_diameters():
    """ISO 7-1 takes the ISO 228-1 basic diameters at its gauge plane."""
    assert list(BSPT_BASIC) == list(BSPP_BASIC)
    for size, (tpi, major_mm, _, _) in BSPT_BASIC.items():
        assert (tpi, major_mm) == BSPP_BASIC[size]


@pytest.mark.parametrize("family", ["npt", "nptf", "bspt"])
def test_tapered_bands_open_upward_and_contain_the_gage_plane(family):
    """The band runs small end to effective end and brackets the gage plane."""
    for size in pipe_sizes(family):
        dimensions = pipe_dimensions(family, size)
        low, high = dimensions["external_major_band_mm"]
        assert low < dimensions["major_mm"] < high
        inner_low, inner_high = dimensions["internal_minor_band_mm"]
        assert inner_low < dimensions["minor_mm"] < inner_high


@pytest.mark.parametrize("family", ["bspp"])
def test_parallel_bands_collapse_to_one_diameter(family):
    """A parallel thread has one plane, so its band has zero width."""
    for size in pipe_sizes(family):
        dimensions = pipe_dimensions(family, size)
        assert dimensions["external_major_band_mm"][0] == pytest.approx(
            dimensions["external_major_band_mm"][1]
        )
        assert dimensions["tapered"] is False


def test_iso_7_parallel_internal_form_drops_the_taper():
    """Rp is parallel even though its family table carries a gauge length."""
    tapered = pipe_dimensions("bspt", "1/2")
    parallel = pipe_dimensions("bspt", "1/2", parallel=True)
    assert tapered["tapered"] is True and parallel["tapered"] is False
    assert parallel["major_mm"] == tapered["major_mm"]
    low, high = parallel["external_major_band_mm"]
    assert low == pytest.approx(high)


@pytest.mark.parametrize(
    "family,factor,angle",
    [
        ("npt", AMERICAN_HEIGHT_FACTOR, 60.0),
        ("nptf", AMERICAN_HEIGHT_FACTOR, 60.0),
        ("bspp", WHITWORTH_HEIGHT_FACTOR, 55.0),
        ("bspt", WHITWORTH_HEIGHT_FACTOR, 55.0),
    ],
)
def test_thread_height_and_angle_follow_the_family_form(family, factor, angle):
    """Height is the family's factor times pitch, and majors exceed minors."""
    for size in pipe_sizes(family):
        dimensions = pipe_dimensions(family, size)
        assert dimensions["included_angle_deg"] == angle
        assert dimensions["thread_height_mm"] == pytest.approx(
            factor * dimensions["pitch_mm"]
        )
        assert dimensions["major_mm"] - dimensions["minor_mm"] == pytest.approx(
            2 * dimensions["thread_height_mm"]
        )


def test_every_catalog_pipe_size_has_dimensions():
    """The size list and the dimension tables cannot drift apart."""
    catalog = specification_catalog()
    for family in ("npt", "nptf", "bspp", "bspt"):
        assert catalog[family]["sizes"] == pipe_sizes(family)
        for size in catalog[family]["sizes"]:
            assert pipe_dimensions(family, size)["major_mm"] > 0


@pytest.mark.parametrize("family,size", [("npt", "3"), ("bspp", "6"), ("bogus", "1/2")])
def test_unknown_family_or_size_raises(family, size):
    """Sizes outside the carried tables fail loudly instead of interpolating."""
    with pytest.raises(ValueError):
        pipe_dimensions(family, size)
