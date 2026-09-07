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

    @pytest.mark.parametrize("system", ["iso_metric", "unified"])
    def test_every_included_coarse_diameter_has_a_fine_counterpart(self, system):
        """Missing fine diameters must not force an artificial size jump."""
        records = get_thread_catalog()[system]
        assert len({r["designation"] for r in records}) == len(records)
        for coarse in (r for r in records if r["series"] == "coarse"):
            fine = [
                r for r in records
                if r["series"] == "fine"
                and r["nominal_diameter"] == coarse["nominal_diameter"]
            ]
            assert fine, coarse["designation"]
            assert all(r["pitch"] < coarse["pitch"] for r in fine)

    @pytest.mark.parametrize(
        "system,designation,diameter,pitch",
        [
            ("iso_metric", "M2x0.25", 0.002, 0.00025),
            ("iso_metric", "M2.5x0.35", 0.0025, 0.00035),
            ("iso_metric", "M4x0.5", 0.004, 0.0005),
            ("iso_metric", "M6x0.75", 0.006, 0.00075),
            ("iso_metric", "M24x2.0", 0.024, 0.002),
            ("unified", "#2-64 UNF", 0.086 * 0.0254, 0.0254 / 64),
            ("unified", "7/16-20 UNF", 7 / 16 * 0.0254, 0.0254 / 20),
        ],
    )
    def test_supplemental_fine_dimensions(
        self, system, designation, diameter, pitch,
    ):
        """Check nominal pairs against Gühring and Boneham thread tables."""
        record = next(
            r for r in get_thread_catalog()[system]
            if r["designation"] == designation
        )
        assert record["nominal_diameter"] == pytest.approx(diameter)
        assert record["pitch"] == pytest.approx(pitch)
        assert record["series"] == "fine"


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

    def test_fine_metric_does_not_double_m4_to_m8(self):
        """Regression: a 3 kN load formerly skipped all fine sizes below M8."""
        results = {
            series: screen_thread_size("iso_metric", series, 3_000, 580e6, 1.5)
            for series in ("coarse", "fine")
        }
        assert results["coarse"]["recommended_designation"] == "M4x0.7"
        assert results["fine"]["recommended_designation"] == "M4x0.5"
        assert results["fine"]["proof_capacity"] > results["coarse"]["proof_capacity"]
        assert results["fine"]["previous_designation"] == "M3x0.35"
        assert results["fine"]["previous_proof_capacity"] < 4_500

    def test_small_unf_does_not_jump_to_number_ten(self):
        """Regression: the fine catalog formerly started at #10-32 UNF."""
        result = screen_thread_size("unified", "fine", 1_500, 580e6, 1.5)
        assert result["recommended_designation"] == "#4-48 UNF"
        assert result["previous_designation"] == "#2-64 UNF"

    @pytest.mark.parametrize("system", ["iso_metric", "unified"])
    def test_fine_diameter_never_exceeds_coarse_across_load_boundaries(self, system):
        """Equal proof strength and complete counterpart coverage preserve this invariant."""
        records = get_thread_catalog()[system]
        by_name = {r["designation"]: r for r in records}
        for record in (r for r in records if r["series"] == "coarse"):
            area = calculate_basic_thread_geometry(
                system, record["nominal_diameter"], record["pitch"],
            )["tensile_stress_area"]
            for factor in (0.5, 0.999999, 1.0, 1.000001):
                load = area * 580e6 / 1.5 * factor
                coarse = screen_thread_size(system, "coarse", load, 580e6, 1.5)
                fine = screen_thread_size(system, "fine", load, 580e6, 1.5)
                if coarse["status"] == "no_size":
                    continue
                assert fine["status"] == "sized"
                assert (
                    by_name[fine["recommended_designation"]]["nominal_diameter"]
                    <= by_name[coarse["recommended_designation"]]["nominal_diameter"]
                ), (system, load, coarse, fine)
                assert fine["proof_capacity"] >= load * 1.5

    def test_catalog_scope_exposes_smallest_candidate_boundary(self):
        """A passing minimum catalog entry must not imply a global minimum."""
        result = screen_thread_size("iso_metric", "fine", 100, 580e6, 1.5)
        assert result["recommended_designation"] == "M2x0.25"
        assert f"Searched {len(result['candidates'])} fine candidates" in result["limitations"]
        assert "from M2x0.25 to M24x1.5" in result["limitations"]
        assert "smaller threads outside this catalog were not evaluated" in result["limitations"]

    def test_catalog_scope_does_not_claim_minimum_boundary_for_larger_choice(self):
        """Only a result at the catalog minimum gets the smaller-sizes warning."""
        result = screen_thread_size("iso_metric", "fine", 3_000, 580e6, 1.5)
        assert "not a complete standards catalog" in result["limitations"]
        assert "smallest catalog entry already passes" not in result["limitations"]

    @pytest.mark.parametrize(
        "system,series,expected_suffix",
        [
            ("iso_metric", "fine", "x0.25"),
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

    def test_size_mode_returns_added_fine_thread_and_catalog_scope(self):
        """The browser API must return the new fine thread, its profile, and scope."""
        result = analyze_thread(
            "size", "iso_metric", "M10x1.5", 0.01, 0.0015,
            3_000, 580e6, 1.5, "fine",
        )
        assert result["designation"] == "M4x0.5"
        assert result["nominal_diameter"] == pytest.approx(0.004)
        assert result["pitch"] == pytest.approx(0.0005)
        assert result["proof_margin"] >= 1.5
        assert "Searched" in result["limitations"]

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
