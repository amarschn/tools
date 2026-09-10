"""Transcription checks for the product-family nominal dimensions.

ASME B18.6.1 sets wood screw diameter by an arithmetic rule, so a mistyped
diameter cannot agree with its own screw number. That is the check these tests
lean on, the same way the pipe tables lean on the taper identity.
"""

import pytest

from pycalcs.screw_products import (
    FORMING_METAL_SIZES,
    MM_PER_INCH,
    WOOD_SCREW_BASE_DIAMETER,
    WOOD_SCREW_BASIC,
    WOOD_SCREW_DIAMETER_STEP,
    product_dimensions,
    product_sizes,
    wood_screw_number,
)
from pycalcs.thread_specifications import specification_catalog


@pytest.mark.parametrize("size", list(WOOD_SCREW_BASIC))
def test_wood_screw_diameter_follows_the_asme_rule(size):
    """d = 0.060 + 0.013 N inches, which catches a typo in either column."""
    diameter_in, _ = WOOD_SCREW_BASIC[size]
    expected = WOOD_SCREW_BASE_DIAMETER + WOOD_SCREW_DIAMETER_STEP * wood_screw_number(
        size
    )
    assert diameter_in == pytest.approx(expected, abs=5e-7)


def test_wood_screw_pitch_falls_as_diameter_rises():
    """Threads per inch must decrease monotonically across the size range."""
    rows = [WOOD_SCREW_BASIC[size] for size in WOOD_SCREW_BASIC]
    diameters = [diameter for diameter, _ in rows]
    counts = [tpi for _, tpi in rows]
    assert diameters == sorted(diameters)
    assert counts == sorted(counts, reverse=True)


@pytest.mark.parametrize("size", list(WOOD_SCREW_BASIC))
def test_wood_screw_dimensions_convert_consistently(size):
    """The millimetre values must agree with the inch table they came from."""
    diameter_in, tpi = WOOD_SCREW_BASIC[size]
    result = product_dimensions("wood", size)
    assert result["major_mm"] == pytest.approx(diameter_in * MM_PER_INCH)
    assert result["pitch_mm"] == pytest.approx(MM_PER_INCH / tpi)
    assert result["tpi"] == tpi
    assert result["unit"] == "in"
    # No flank angle is published here, so none may be claimed.
    assert result["included_angle_deg"] is None


@pytest.mark.parametrize("size", FORMING_METAL_SIZES)
def test_forming_metal_reuses_the_metric_thread_of_the_same_size(size):
    """A DIN 7500 screw forms an ISO metric thread, so its numbers match it."""
    from pycalcs.fasteners import parse_metric_thread_designation

    diameter_m, pitch_m = parse_metric_thread_designation(size)
    result = product_dimensions("forming_metal", size)
    assert result["major_mm"] == pytest.approx(diameter_m * 1000)
    assert result["pitch_mm"] == pytest.approx(pitch_m * 1000)
    assert result["included_angle_deg"] == 60.0
    # The callout carries the size; the pitch is implied by it.
    assert result["callout_size"] == size.split("x")[0]


def test_plastic_forming_screws_offer_no_standard_sizes():
    """Proprietary profiles must not be given an invented size list."""
    assert product_sizes("forming_plastic") == []
    with pytest.raises(ValueError):
        product_dimensions("forming_plastic", "M5x0.8")


@pytest.mark.parametrize("family", ["wood", "forming_metal"])
def test_catalog_sizes_all_resolve_to_dimensions(family):
    """The size list and the dimension tables cannot drift apart."""
    catalog = specification_catalog()[family]
    assert catalog["sizes"] == product_sizes(family)
    assert catalog["default_size"] in catalog["sizes"]
    for size in catalog["sizes"]:
        assert product_dimensions(family, size)["major_mm"] > 0


@pytest.mark.parametrize(
    "family,size", [("wood", "#11"), ("forming_metal", "M12x1.75"), ("bogus", "#8")]
)
def test_unknown_family_or_size_raises(family, size):
    """Sizes outside the carried tables fail loudly instead of interpolating."""
    with pytest.raises(ValueError):
        product_dimensions(family, size)
