"""
Comprehensive tests for ISO 286 fits calculations.

Tests verify against ISO 286-1/2 standard tables and
Machinery's Handbook reference values.
"""

import math
import pytest

from pycalcs import fits


# =============================================================================
# BASIC CLEARANCE FIT TESTS
# =============================================================================

class TestClearanceFits:
    """Test clearance fit calculations."""

    def test_h7_h6_clearance_basic(self):
        """H7/h6 is the fundamental clearance fit with zero shaft deviation."""
        results = fits.calculate_iso_fit(25.0, "H7/h6")

        # Should be classified as clearance
        assert results["fit_type"] == "clearance"

        # Min clearance should be zero (hole EI = 0, shaft es = 0)
        assert results["min_clearance_mm"] == pytest.approx(0.0, abs=1e-6)

        # Max clearance should be positive (hole ES > 0, shaft ei < 0)
        assert results["max_clearance_mm"] > 0

        # H-hole has EI = 0
        assert results["hole_lower_dev_um"] == pytest.approx(0.0, abs=1e-6)

        # h-shaft has es = 0
        assert results["shaft_upper_dev_um"] == pytest.approx(0.0, abs=1e-6)

    def test_h7_g6_sliding_fit(self):
        """H7/g6 is a sliding fit with small clearance."""
        results = fits.calculate_iso_fit(50.0, "H7/g6")

        assert results["fit_type"] == "clearance"
        assert results["min_clearance_mm"] > 0  # Always positive clearance
        assert results["max_clearance_mm"] > results["min_clearance_mm"]

        # g-shaft has negative upper deviation
        assert results["shaft_upper_dev_um"] < 0

    def test_h9_d9_free_running(self):
        """H9/d9 is a free running fit with larger clearance."""
        results = fits.calculate_iso_fit(30.0, "H9/d9")

        assert results["fit_type"] == "clearance"
        assert results["min_clearance_mm"] > 0.02  # Minimum ~20μm
        assert results["max_clearance_mm"] > 0.1   # Several tenths clearance


# =============================================================================
# TRANSITION FIT TESTS
# =============================================================================

class TestTransitionFits:
    """Test transition fit calculations."""

    def test_h7_js6_centered_transition(self):
        """H7/js6 is a centered transition fit."""
        results = fits.calculate_iso_fit(25.0, "H7/js6")

        assert results["fit_type"] == "transition"

        # JS is centered, so deviations should be symmetric
        shaft_upper = results["shaft_upper_dev_um"]
        shaft_lower = results["shaft_lower_dev_um"]
        assert shaft_upper == pytest.approx(-shaft_lower, rel=0.01)

        # Should have both positive max clearance and negative min clearance
        assert results["min_clearance_mm"] < 0  # Can have interference
        assert results["max_clearance_mm"] > 0  # Can have clearance

    def test_h7_k6_light_transition(self):
        """H7/k6 is a light transition fit."""
        results = fits.calculate_iso_fit(40.0, "H7/k6")

        assert results["fit_type"] == "transition"

        # k-shaft has small positive lower deviation
        assert results["shaft_lower_dev_um"] >= 0

    def test_h7_n6_tight_transition(self):
        """H7/n6 is near the interference boundary."""
        results = fits.calculate_iso_fit(25.0, "H7/n6")

        # n6 is often still transition, but very tight
        # Min clearance should be negative
        assert results["min_clearance_mm"] < 0


# =============================================================================
# INTERFERENCE FIT TESTS
# =============================================================================

class TestInterferenceFits:
    """Test interference fit calculations."""

    def test_h7_p6_light_press(self):
        """H7/p6 is a light press/interference fit."""
        results = fits.calculate_iso_fit(25.0, "H7/p6")

        assert results["fit_type"] == "interference"

        # Both min and max clearance should be negative
        assert results["min_clearance_mm"] < 0
        assert results["max_clearance_mm"] < 0

        # Interference values should be positive
        assert results["min_interference_mm"] > 0
        assert results["max_interference_mm"] > 0

    def test_h7_s6_heavy_press(self):
        """H7/s6 is a heavy press fit."""
        results = fits.calculate_iso_fit(50.0, "H7/s6")

        assert results["fit_type"] == "interference"
        assert results["max_interference_mm"] > results["min_interference_mm"]

        # s-shaft has significant positive deviation
        assert results["shaft_lower_dev_um"] > 30  # At least 30μm

    def test_h7_u6_force_fit(self):
        """H7/u6 is a force/shrink fit with heavy interference."""
        results = fits.calculate_iso_fit(80.0, "H7/u6")

        assert results["fit_type"] == "interference"

        # Heavy interference
        assert results["max_interference_mm"] > 0.05  # >50μm


# =============================================================================
# TOLERANCE GRADE TESTS
# =============================================================================

class TestToleranceGrades:
    """Test IT tolerance calculations against ISO 286 tables."""

    def test_it7_at_30_50mm(self):
        """
        Reference check: IT7 at 30-50mm step.
        ISO 286-1 gives IT7 = 25μm for this range.
        """
        results = fits.calculate_iso_fit(40.0, "H7/h6")

        # H7 tolerance should be approximately 25μm
        assert results["hole_tolerance_um"] == pytest.approx(25.0, rel=0.05)

    def test_it6_at_30_50mm(self):
        """IT6 at 30-50mm step should be approximately 16μm."""
        results = fits.calculate_iso_fit(40.0, "H7/h6")

        # h6 tolerance should be approximately 16μm
        assert results["shaft_tolerance_um"] == pytest.approx(16.0, rel=0.05)

    def test_tolerance_scales_with_diameter(self):
        """Tolerance should increase with diameter."""
        small = fits.calculate_iso_fit(10.0, "H7/h6")
        large = fits.calculate_iso_fit(100.0, "H7/h6")

        assert large["hole_tolerance_um"] > small["hole_tolerance_um"]
        assert large["shaft_tolerance_um"] > small["shaft_tolerance_um"]


# =============================================================================
# FUNDAMENTAL DEVIATION TESTS
# =============================================================================

class TestFundamentalDeviations:
    """Test fundamental deviation values against ISO 286-2 tables."""

    def test_h_shaft_zero_deviation(self):
        """h-shaft always has upper deviation = 0."""
        for diameter in [5, 25, 100, 200]:
            results = fits.calculate_iso_fit(diameter, "H7/h6")
            assert results["shaft_upper_dev_um"] == pytest.approx(0.0, abs=1e-6)

    def test_g_shaft_negative_deviation(self):
        """g-shaft has small negative upper deviation."""
        results = fits.calculate_iso_fit(25.0, "H7/g6")

        # g at 18-30mm: es = -7μm per ISO 286-2
        assert results["shaft_upper_dev_um"] == pytest.approx(-7.0, abs=1.0)

    def test_p_shaft_positive_deviation(self):
        """p-shaft has positive lower deviation (interference)."""
        results = fits.calculate_iso_fit(25.0, "H7/p6")

        # p at 18-30mm: ei = +22μm per ISO 286-2
        assert results["shaft_lower_dev_um"] == pytest.approx(22.0, abs=2.0)


# =============================================================================
# DIAMETER RANGE TESTS
# =============================================================================

class TestDiameterRanges:
    """Test calculations across the ISO 286 diameter range."""

    def test_minimum_diameter(self):
        """Test at minimum diameter (1mm)."""
        results = fits.calculate_iso_fit(1.0, "H7/h6")
        assert results["fit_type"] == "clearance"
        assert results["diameter_step"] == "1.0-3.0 mm"

    def test_maximum_diameter(self):
        """Test at maximum diameter (500mm)."""
        results = fits.calculate_iso_fit(500.0, "H7/h6")
        assert results["fit_type"] == "clearance"
        assert results["diameter_step"] == "400.0-500.0 mm"

    def test_diameter_below_range_raises(self):
        """Diameter below 1mm should raise error."""
        with pytest.raises(ValueError, match="at least 1 mm"):
            fits.calculate_iso_fit(0.5, "H7/h6")

    def test_diameter_above_range_raises(self):
        """Diameter above 500mm should raise error."""
        with pytest.raises(ValueError, match="not exceed 500 mm"):
            fits.calculate_iso_fit(600.0, "H7/h6")

    def test_zero_diameter_raises(self):
        """Zero diameter should raise error."""
        with pytest.raises(ValueError, match="greater than zero"):
            fits.calculate_iso_fit(0.0, "H7/h6")


# =============================================================================
# ACTUAL SIZE CALCULATIONS
# =============================================================================

class TestActualSizes:
    """Test actual size limit calculations."""

    def test_hole_size_limits(self):
        """Verify hole size = nominal + deviation."""
        D = 50.0
        results = fits.calculate_iso_fit(D, "H7/h6")

        expected_min = D + results["hole_lower_dev_mm"]
        expected_max = D + results["hole_upper_dev_mm"]

        assert results["hole_min_mm"] == pytest.approx(expected_min, rel=1e-6)
        assert results["hole_max_mm"] == pytest.approx(expected_max, rel=1e-6)

    def test_shaft_size_limits(self):
        """Verify shaft size = nominal + deviation."""
        D = 50.0
        results = fits.calculate_iso_fit(D, "H7/g6")

        expected_min = D + results["shaft_lower_dev_mm"]
        expected_max = D + results["shaft_upper_dev_mm"]

        assert results["shaft_min_mm"] == pytest.approx(expected_min, rel=1e-6)
        assert results["shaft_max_mm"] == pytest.approx(expected_max, rel=1e-6)

    def test_clearance_calculation(self):
        """Verify clearance = hole - shaft."""
        results = fits.calculate_iso_fit(30.0, "H7/g6")

        # Min clearance = hole_min - shaft_max
        expected_min_clear = results["hole_min_mm"] - results["shaft_max_mm"]
        assert results["min_clearance_mm"] == pytest.approx(expected_min_clear, rel=1e-6)

        # Max clearance = hole_max - shaft_min
        expected_max_clear = results["hole_max_mm"] - results["shaft_min_mm"]
        assert results["max_clearance_mm"] == pytest.approx(expected_max_clear, rel=1e-6)


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================

class TestInputValidation:
    """Test input validation and error handling."""

    def test_invalid_fit_format_raises(self):
        """Invalid fit format should raise error."""
        with pytest.raises(ValueError, match="form 'H7/g6'"):
            fits.calculate_iso_fit(25.0, "H7g6")

        with pytest.raises(ValueError, match="form 'H7/g6'"):
            fits.calculate_iso_fit(25.0, "BADFIT")

    def test_unsupported_shaft_letter_raises(self):
        """Unsupported shaft letter should raise error."""
        with pytest.raises(ValueError, match="Unsupported shaft"):
            fits.calculate_iso_fit(25.0, "H7/z6")

    def test_unsupported_hole_letter_raises(self):
        """Unsupported hole letter should raise error."""
        with pytest.raises(ValueError, match="Unsupported hole"):
            fits.calculate_iso_fit(25.0, "Z7/h6")

    def test_invalid_grade_raises(self):
        """Invalid IT grade should raise error."""
        with pytest.raises(ValueError, match="IT grade"):
            fits.calculate_iso_fit(25.0, "H0/h0")


# =============================================================================
# FIT CLASSIFICATION TESTS
# =============================================================================

class TestFitClassification:
    """Test automatic fit type classification."""

    def test_classify_clearance(self):
        """Positive min clearance = clearance fit."""
        assert fits.classify_fit(0.01, 0.05) == "clearance"
        assert fits.classify_fit(0.0, 0.03) == "clearance"

    def test_classify_interference(self):
        """Negative max clearance = interference fit."""
        assert fits.classify_fit(-0.05, -0.01) == "interference"

    def test_classify_transition(self):
        """Mixed clearance/interference = transition fit."""
        assert fits.classify_fit(-0.01, 0.02) == "transition"


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestHelperFunctions:
    """Test utility functions."""

    def test_get_common_fits(self):
        """Verify common fits list."""
        common = fits.get_common_fits()

        assert "H7/h6" in common
        assert "H7/p6" in common
        assert common["H7/h6"]["fit_type"] == "clearance"
        assert common["H7/p6"]["fit_type"] == "interference"

    def test_get_fit_types(self):
        """Verify fit type descriptions."""
        types = fits.get_fit_types()

        assert "clearance" in types
        assert "transition" in types
        assert "interference" in types

    def test_suggest_fit_running(self):
        """Suggest fits for running application."""
        suggestions = fits.suggest_fit("running", precision="standard")
        assert len(suggestions) > 0
        assert any("f" in s or "g" in s for s in suggestions)

    def test_suggest_fit_press(self):
        """Suggest fits for press application."""
        suggestions = fits.suggest_fit("press", assembly_method="heavy_press")
        assert len(suggestions) > 0
        assert any("s" in s or "t" in s for s in suggestions)


# =============================================================================
# RESULT COMPLETENESS TESTS
# =============================================================================

class TestResultCompleteness:
    """Test that all expected fields are returned."""

    def test_all_required_fields_present(self):
        """Verify all required result fields are present."""
        results = fits.calculate_iso_fit(25.0, "H7/h6")

        required_fields = [
            "nominal_diameter_mm",
            "fit_designation",
            "fit_type",
            "hole_zone",
            "shaft_zone",
            "hole_tolerance_grade",
            "shaft_tolerance_grade",
            "hole_tolerance_um",
            "shaft_tolerance_um",
            "hole_upper_dev_mm",
            "hole_lower_dev_mm",
            "shaft_upper_dev_mm",
            "shaft_lower_dev_mm",
            "hole_max_mm",
            "hole_min_mm",
            "shaft_max_mm",
            "shaft_min_mm",
            "min_clearance_mm",
            "max_clearance_mm",
        ]

        for field in required_fields:
            assert field in results, f"Missing field: {field}"

    def test_preset_info_for_common_fits(self):
        """Common fits should have preset information."""
        results = fits.calculate_iso_fit(25.0, "H7/h6")

        assert results["fit_name"] == "Locational Clearance"
        assert results["fit_description"] is not None
        assert len(results["applications"]) > 0

    def test_no_preset_for_custom_fits(self):
        """Custom fits should have None for preset fields."""
        results = fits.calculate_iso_fit(25.0, "H8/e8")

        assert results["fit_name"] is None
        assert results["fit_description"] is None
