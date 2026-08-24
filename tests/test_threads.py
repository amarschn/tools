"""Tests for thread geometry, identification, and axial size screening."""

import math

import pytest

from pycalcs.threads import (
    analyze_thread,
    calculate_basic_thread_geometry,
    get_thread_catalog,
    identify_standard_thread,
    screen_thread_size,
)


class TestBasicThreadGeometry:
    """Verify standard 60-degree profile equations."""

    def test_iso_m10_geometry(self):
        """M10x1.5 should match the ISO basic geometry equations."""
        result = calculate_basic_thread_geometry(
            "iso_metric",
            nominal_diameter=10e-3,
            pitch=1.5e-3,
        )

        assert result["fundamental_height"] == pytest.approx(
            1.2990381057e-3,
            rel=1e-9,
        )
        assert result["pitch_diameter_basic"] == pytest.approx(
            9.0257214207e-3,
            rel=1e-9,
        )
        assert result["external_minor_diameter_basic"] == pytest.approx(
            8.1596960170e-3,
            rel=1e-9,
        )
        assert result["internal_minor_diameter_basic"] == pytest.approx(
            8.3762023679e-3,
            rel=1e-9,
        )
        assert result["tensile_stress_area"] == pytest.approx(
            57.9895969e-6,
            rel=1e-8,
        )

    def test_unified_half_inch_geometry_uses_exact_tpi_pitch(self):
        """Unified geometry should use exact pitch and the Unified area rule."""
        pitch = 0.0254 / 13
        result = calculate_basic_thread_geometry(
            "unified",
            nominal_diameter=0.5 * 0.0254,
            pitch=pitch,
        )

        assert result["pitch"] == pytest.approx(pitch, rel=1e-12)
        assert result["pitch_diameter_basic"] == pytest.approx(
            11.4309396968e-3,
            rel=1e-8,
        )
        assert result["internal_minor_diameter_basic"] == pytest.approx(
            10.5848994946e-3,
            rel=1e-8,
        )
        assert result["external_minor_diameter_basic"] is None
        assert result["tensile_stress_area"] == pytest.approx(
            91.5472315e-6,
            rel=1e-8,
        )

    @pytest.mark.parametrize(
        "system,diameter,pitch,error",
        [
            ("other", 0.01, 0.0015, "thread_system"),
            ("iso_metric", 0.0, 0.0015, "nominal_diameter"),
            ("iso_metric", 0.01, 0.0, "pitch"),
            ("iso_metric", 0.001, 0.001, "too large"),
            ("iso_metric", 0.001, 0.0009, "nonpositive derived"),
            ("unified", 0.001, 0.0008, "nonpositive derived"),
        ],
    )
    def test_invalid_geometry_inputs_raise(self, system, diameter, pitch, error):
        """Nonphysical or unsupported geometry inputs should fail clearly."""
        with pytest.raises(ValueError, match=error):
            calculate_basic_thread_geometry(system, diameter, pitch)


class TestThreadCatalog:
    """Verify shared designations are parsed into exact catalog records."""

    def test_catalog_contains_expected_designations(self):
        """The browser catalog should expose common metric and Unified sizes."""
        catalog = get_thread_catalog()
        iso_names = {item["designation"] for item in catalog["iso_metric"]}
        unified_names = {item["designation"] for item in catalog["unified"]}

        assert "M10x1.5" in iso_names
        assert "M10x1.25" in iso_names
        assert "1/2-13 UNC" in unified_names
        assert "1/2-20 UNF" in unified_names

    def test_unified_catalog_pitch_is_not_rounded_millimetres(self):
        """The 13 TPI record should retain its exact reciprocal-inch pitch."""
        catalog = get_thread_catalog()["unified"]
        half_inch = next(
            item for item in catalog if item["designation"] == "1/2-13 UNC"
        )

        assert half_inch["pitch"] == pytest.approx(0.0254 / 13, rel=1e-12)
        assert half_inch["nominal_diameter"] == pytest.approx(0.0127)
        assert half_inch["series"] == "coarse"


class TestThreadIdentification:
    """Verify nearest-nominal ranking and residual reporting."""

    @pytest.mark.parametrize(
        "diameter_mm,pitch_mm,expected",
        [
            (9.92, 1.49, "M10x1.5"),
            (10.00, 1.24, "M10x1.25"),
        ],
    )
    def test_identifies_metric_thread(self, diameter_mm, pitch_mm, expected):
        """Nearby metric measurements should rank the intended nominal first."""
        result = identify_standard_thread(
            "iso_metric",
            measured_major_diameter=diameter_mm / 1000,
            measured_pitch=pitch_mm / 1000,
        )

        assert result["nearest_designation"] == expected
        assert len(result["candidates"]) == 3
        scores = [item["relative_distance"] for item in result["candidates"]]
        assert scores == sorted(scores)

    def test_identifies_unified_thread(self):
        """A near-half-inch, near-13-TPI measurement should rank 1/2-13 UNC."""
        result = identify_standard_thread(
            "unified",
            measured_major_diameter=0.498 * 0.0254,
            measured_pitch=0.0254 / 13.1,
        )

        assert result["nearest_designation"] == "1/2-13 UNC"
        assert result["diameter_difference"] == pytest.approx(
            -0.002 * 0.0254,
        )

    @pytest.mark.parametrize(
        "diameter,pitch,count,error",
        [
            (0.0, 0.001, 3, "measured_major_diameter"),
            (0.01, 0.0, 3, "measured_pitch"),
            (0.01, 0.001, 0, "candidate_count"),
        ],
    )
    def test_invalid_identification_inputs_raise(
        self,
        diameter,
        pitch,
        count,
        error,
    ):
        """Identification should reject invalid measurements and list sizes."""
        with pytest.raises(ValueError, match=error):
            identify_standard_thread(
                "iso_metric",
                diameter,
                pitch,
                candidate_count=count,
            )


class TestThreadSizeScreening:
    """Verify direct-axial proof-load screening boundaries."""

    def test_metric_coarse_boundary_selects_m12(self):
        """A required 83.33 mm2 area should reject M10 and select M12."""
        result = screen_thread_size(
            "iso_metric",
            "coarse",
            axial_load=25_000,
            proof_strength=600e6,
            design_factor=2.0,
        )

        assert result["required_stress_area"] == pytest.approx(
            83.333333e-6,
        )
        assert result["recommended_designation"] == "M12x1.75"
        assert result["previous_designation"] == "M10x1.5"
        assert result["proof_capacity"] == pytest.approx(50_559.923, rel=1e-6)
        assert result["utilization_percent"] < 100

    def test_unified_coarse_boundary_selects_seven_sixteenths(self):
        """The Unified stress-area formula should select 7/16-14 UNC."""
        result = screen_thread_size(
            "unified",
            "coarse",
            axial_load=20_000,
            proof_strength=586e6,
            design_factor=2.0,
        )

        assert result["recommended_designation"] == "7/16-14 UNC"
        assert result["recommended_stress_area"] == pytest.approx(
            68.5858e-6,
            rel=1e-4,
        )
        assert result["proof_capacity"] == pytest.approx(40_190.9, rel=1e-4)

    def test_no_supported_size_returns_largest_candidate_as_evidence(self):
        """Oversized demand should return no recommendation and the max tried."""
        result = screen_thread_size(
            "iso_metric",
            "coarse",
            axial_load=1_000_000,
            proof_strength=225e6,
            design_factor=3.0,
        )

        assert result["status"] == "no_size"
        assert result["recommended_designation"] == ""
        assert result["previous_designation"] == "M24x3.0"
        assert math.isinf(result["utilization_percent"])

    @pytest.mark.parametrize(
        "system,series,expected_suffix",
        [
            ("iso_metric", "fine", "x1.0"),
            ("unified", "fine", "UNF"),
            ("iso_metric", "all", "x"),
        ],
    )
    def test_fine_and_all_candidate_filters(
        self,
        system,
        series,
        expected_suffix,
    ):
        """Fine and combined searches should return from the chosen set."""
        result = screen_thread_size(
            system,
            series,
            axial_load=1_000,
            proof_strength=500e6,
            design_factor=1.2,
        )

        assert result["status"] == "sized"
        assert expected_suffix in result["recommended_designation"]
        if series == "fine":
            assert all(item["series"] == "fine" for item in result["candidates"])

    @pytest.mark.parametrize(
        "series,load,strength,factor,error",
        [
            ("other", 1000, 600e6, 2.0, "thread_series"),
            ("coarse", 0, 600e6, 2.0, "axial_load"),
            ("coarse", 1000, 0, 2.0, "proof_strength"),
            ("coarse", 1000, 600e6, 0.9, "design_factor"),
        ],
    )
    def test_invalid_sizing_inputs_raise(
        self,
        series,
        load,
        strength,
        factor,
        error,
    ):
        """Sizing should reject invalid series and nonpositive design inputs."""
        with pytest.raises(ValueError, match=error):
            screen_thread_size(
                "iso_metric",
                series,
                axial_load=load,
                proof_strength=strength,
                design_factor=factor,
            )


class TestThreadAnalysisWrapper:
    """Verify the stable browser-facing API for all three modes."""

    def test_explore_mode_returns_geometry(self):
        """Explore mode should return the requested designation and geometry."""
        result = analyze_thread(
            "explore",
            "iso_metric",
            "M10x1.5",
            measured_major_diameter=0.01,
            measured_pitch=0.0015,
            axial_load=20_000,
            proof_strength=600e6,
            design_factor=1.5,
            thread_series="coarse",
        )

        assert result["designation"] == "M10x1.5"
        assert result["series"] == "coarse"
        assert result["sizing_status"] == ""
        assert result["match_candidates"] == []

    def test_size_mode_uses_recommended_thread_for_profile(self):
        """The profile and headline should follow the selected sizing result."""
        result = analyze_thread(
            "size",
            "iso_metric",
            "M10x1.5",
            measured_major_diameter=0.01,
            measured_pitch=0.0015,
            axial_load=20_000,
            proof_strength=600e6,
            design_factor=1.5,
            thread_series="coarse",
        )

        assert result["designation"] == "M10x1.5"
        assert result["sizing_status"] == "sized"
        assert result["proof_margin"] > 1.5
        assert result["previous_designation"] == "M8x1.25"

    def test_no_size_mode_keeps_largest_attempt_visible(self):
        """No-size results should still provide a profile and catalog evidence."""
        result = analyze_thread(
            "size",
            "iso_metric",
            "M10x1.5",
            measured_major_diameter=0.01,
            measured_pitch=0.0015,
            axial_load=1_000_000,
            proof_strength=225e6,
            design_factor=3.0,
            thread_series="coarse",
        )

        assert result["sizing_status"] == "no_size"
        assert result["designation"] == "M24x3.0"
        assert "included catalog" in result["limitations"]
        assert result["subst_proof_capacity"] == ""
