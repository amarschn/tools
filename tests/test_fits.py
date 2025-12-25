"""Tests for ISO 286 fit calculations."""

import pytest

from pycalcs import fits


def test_h7_h6_clearance_basic():
    """Nominal check: H7/h6 should yield a clearance fit."""
    results = fits.calculate_iso_fit(10.0, "H7/h6")
    assert results["min_clearance_mm"] >= 0
    assert results["max_clearance_mm"] > 0
    assert results["hole_lower_dev_mm"] == pytest.approx(0.0)
    assert results["shaft_upper_dev_mm"] == pytest.approx(0.0)


def test_h7_p6_interference_basic():
    """Nominal check: H7/p6 should yield interference (negative min clearance)."""
    results = fits.calculate_iso_fit(10.0, "H7/p6")
    assert results["min_clearance_mm"] < 0
    assert results["max_clearance_mm"] > 0


def test_it_grade_matches_iso_table_reference():
    """
    Reference check against ISO 286 table values for IT7 at 30-50 mm.

    ISO 286-1 gives IT7 = 25 um for the 30-50 mm step. The formula-based
    calculation should be close to this value.
    """
    results = fits.calculate_iso_fit(40.0, "H7/h6")
    hole_upper_um = results["hole_upper_dev_mm"] * 1000.0
    assert hole_upper_um == pytest.approx(25.0, abs=1.0)


def test_js_zone_is_centered():
    """JS shaft zones should be centered about zero."""
    results = fits.calculate_iso_fit(25.0, "H7/js6")
    shaft_upper = results["shaft_upper_dev_mm"]
    shaft_lower = results["shaft_lower_dev_mm"]
    assert shaft_upper == pytest.approx(-shaft_lower, rel=1e-3, abs=1e-6)


def test_invalid_fit_raises():
    """Invalid fit designations should raise clear errors."""
    with pytest.raises(ValueError):
        fits.calculate_iso_fit(10.0, "H7/z6")

    with pytest.raises(ValueError):
        fits.calculate_iso_fit(10.0, "H4/h3")

    with pytest.raises(ValueError):
        fits.calculate_iso_fit(10.0, "BADFIT")
