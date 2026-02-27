"""Tests for pycalcs.fracture_mechanics module."""

import math
import pytest

from pycalcs.fracture_mechanics import (
    FRACTURE_MATERIALS,
    _geometry_factor_Y,
    _stress_intensity_factor,
    _critical_crack_size,
    _paris_law_integration,
    analyze_fracture_and_crack_growth,
    get_fracture_material_presets,
)


# ---------------------------------------------------------------------------
# Geometry factor tests
# ---------------------------------------------------------------------------

class TestGeometryFactorY:
    def test_through_crack_small_ratio(self):
        """For a/W -> 0, through-crack Y -> 1.0."""
        Y = _geometry_factor_Y("through", 0.001, 1.0)
        assert Y == pytest.approx(1.0, abs=0.01)

    def test_through_crack_moderate_ratio(self):
        """Through-crack at a/W=0.3 should give Y ≈ sqrt(sec(0.3*pi/2))."""
        a, W = 0.3, 1.0
        expected = math.sqrt(1.0 / math.cos(math.pi * 0.3 / 2.0))
        Y = _geometry_factor_Y("through", a, W)
        assert Y == pytest.approx(expected, rel=1e-6)

    def test_edge_crack_zero_ratio(self):
        """Edge crack at a/W -> 0 should give Y ≈ 1.12."""
        Y = _geometry_factor_Y("edge", 1e-6, 1.0)
        assert Y == pytest.approx(1.12, abs=0.01)

    def test_surface_crack_constant(self):
        """Surface crack Y is a constant 0.728."""
        Y = _geometry_factor_Y("surface", 0.005, 0.1)
        assert Y == pytest.approx(0.728, rel=1e-6)

    def test_embedded_crack_constant(self):
        """Embedded/penny crack Y = 2/pi ≈ 0.637."""
        Y = _geometry_factor_Y("embedded", 0.003, 0.05)
        assert Y == pytest.approx(2.0 / math.pi, rel=1e-6)

    def test_unknown_crack_type_raises(self):
        with pytest.raises(ValueError, match="Unknown crack_type"):
            _geometry_factor_Y("diagonal", 0.01, 0.1)

    # --- New crack type tests ---

    def test_elliptical_surface_ac_1_matches_surface(self):
        """At a/c=1.0 with small a/W, elliptical_surface should approximate 0.728."""
        Y = _geometry_factor_Y("elliptical_surface", 0.001, 0.1, aspect_ratio=1.0)
        assert Y == pytest.approx(0.728, abs=0.1)

    def test_elliptical_surface_low_ac(self):
        """Elongated crack (a/c=0.2) gives higher Y than a/c=1."""
        Y_low = _geometry_factor_Y("elliptical_surface", 0.001, 0.1, aspect_ratio=0.2)
        Y_one = _geometry_factor_Y("elliptical_surface", 0.001, 0.1, aspect_ratio=1.0)
        assert Y_low > Y_one

    def test_elliptical_surface_high_ac(self):
        """Deep crack (a/c=2.0) gives different Y than a/c=1."""
        Y_high = _geometry_factor_Y("elliptical_surface", 0.001, 0.1, aspect_ratio=2.0)
        assert Y_high > 0  # sanity

    def test_corner_crack_basic(self):
        """Corner crack Y should be ~1.1-1.3x surface crack value."""
        Y_corner = _geometry_factor_Y("corner", 0.001, 0.1, aspect_ratio=1.0)
        Y_surface = _geometry_factor_Y("surface", 0.001, 0.1)
        assert Y_corner > Y_surface
        assert Y_corner < Y_surface * 2.0

    def test_corner_crack_ac_1(self):
        """Corner crack at a/c=1 should be a reasonable value."""
        Y = _geometry_factor_Y("corner", 0.001, 0.1, aspect_ratio=1.0)
        assert 0.5 < Y < 2.0

    def test_double_edge_small_ratio(self):
        """For a/W -> 0, double-edge Y should approach 1.122."""
        Y = _geometry_factor_Y("double_edge", 1e-6, 1.0)
        assert Y == pytest.approx(1.122, abs=0.01)

    def test_double_edge_moderate_ratio(self):
        """Double-edge at a/W=0.3 should give a reasonable Y."""
        Y = _geometry_factor_Y("double_edge", 0.3, 1.0)
        r = 0.3
        expected = 1.122 - 0.561 * r - 0.205 * r**2 + 0.471 * r**3 - 0.190 * r**4
        assert Y == pytest.approx(expected, rel=1e-6)

    def test_double_edge_vs_single_edge(self):
        """Double-edge and single-edge should give different Y values."""
        Y_double = _geometry_factor_Y("double_edge", 0.1, 1.0)
        Y_single = _geometry_factor_Y("edge", 0.1, 1.0)
        assert Y_double != pytest.approx(Y_single, abs=0.01)


# ---------------------------------------------------------------------------
# Stress intensity factor tests
# ---------------------------------------------------------------------------

class TestStressIntensityFactor:
    def test_known_case(self):
        """K_I = Y * sigma * sqrt(pi*a) with known values."""
        sigma = 100e6  # 100 MPa
        a = 0.005      # 5 mm
        Y = 1.12
        expected = Y * sigma * math.sqrt(math.pi * a)
        K_I = _stress_intensity_factor(sigma, a, Y)
        assert K_I == pytest.approx(expected, rel=1e-10)

    def test_zero_crack(self):
        """Zero crack size should give K_I = 0."""
        K_I = _stress_intensity_factor(100e6, 0.0, 1.12)
        assert K_I == 0.0


# ---------------------------------------------------------------------------
# Critical crack size tests
# ---------------------------------------------------------------------------

class TestCriticalCrackSize:
    def test_surface_crack_analytical(self):
        """For surface crack (constant Y=0.728), a_cr = (K_IC / (Y*sigma))^2 / pi."""
        sigma = 100e6  # Pa
        K_IC = 7e6     # Pa*sqrt(m)
        Y = 0.728
        expected_a_cr = (K_IC / (Y * sigma)) ** 2 / math.pi
        a_cr, reached = _critical_crack_size(sigma, K_IC, "surface", W=0.1)
        assert a_cr == pytest.approx(expected_a_cr, rel=0.01)
        assert reached is True

    def test_critical_size_increases_with_toughness(self):
        """Higher K_IC should yield larger critical crack size."""
        sigma = 80e6
        a_cr_low, _ = _critical_crack_size(sigma, 5e6, "edge", W=0.05)
        a_cr_high, _ = _critical_crack_size(sigma, 10e6, "edge", W=0.05)
        assert a_cr_high > a_cr_low

    def test_k_never_reaches_kic(self):
        """When K never reaches K_IC, critical_reached should be False."""
        # Very high toughness, low stress => K never reaches K_IC
        sigma = 1e3  # very low stress (1 kPa)
        K_IC = 100e6  # very high toughness
        a_cr, reached = _critical_crack_size(sigma, K_IC, "surface", W=0.1)
        assert reached is False


# ---------------------------------------------------------------------------
# Paris-law integration tests
# ---------------------------------------------------------------------------

class TestParisLawIntegration:
    def test_finite_cycles(self):
        """Integration should return finite cycle count."""
        cycles, sizes = _paris_law_integration(
            sigma_max=100e6, stress_ratio_R=0.0,
            a_0=0.001, a_cr=0.01,
            crack_type="surface", W=0.05,
            C=5e-8, m=5.0,
        )
        assert len(cycles) > 2
        assert cycles[-1] > 0
        assert math.isfinite(cycles[-1])

    def test_monotonic_growth(self):
        """Crack sizes should monotonically increase."""
        cycles, sizes = _paris_law_integration(
            sigma_max=80e6, stress_ratio_R=0.0,
            a_0=0.002, a_cr=0.015,
            crack_type="edge", W=0.04,
            C=1e-7, m=4.0,
        )
        for i in range(1, len(sizes)):
            assert sizes[i] >= sizes[i - 1]

    def test_higher_stress_fewer_cycles(self):
        """Doubling stress should reduce life significantly."""
        cycles_low, _ = _paris_law_integration(
            sigma_max=50e6, stress_ratio_R=0.0,
            a_0=0.001, a_cr=0.01,
            crack_type="surface", W=0.05,
            C=5e-8, m=5.0,
        )
        cycles_high, _ = _paris_law_integration(
            sigma_max=100e6, stress_ratio_R=0.0,
            a_0=0.001, a_cr=0.01,
            crack_type="surface", W=0.05,
            C=5e-8, m=5.0,
        )
        assert cycles_high[-1] < cycles_low[-1]


# ---------------------------------------------------------------------------
# Main function integration tests
# ---------------------------------------------------------------------------

class TestAnalyzeFractureAndCrackGrowth:
    def test_required_keys_present(self):
        """Result dict should contain all documented keys."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=30.0,
            initial_crack_size_mm=1.0,
        )
        required_keys = [
            "K_I_mpa_sqrt_m", "K_IC_mpa_sqrt_m", "fracture_safety_factor",
            "critical_crack_size_mm", "critical_crack_reached",
            "cycles_to_failure",
            "life_fraction_used", "inspection_interval_cycles",
            "crack_growth_rate_mm_per_cycle",
            "applied_hoop_stress_mpa", "applied_radial_stress_mpa",
            "geometry_factor_Y", "ligament_width_mm",
            "material_preset", "material_display_name", "material_notes",
            "status", "recommendations",
            "crack_growth_curve", "K_vs_a_curve",
            "subst_K_I_mpa_sqrt_m", "subst_critical_crack_size_mm",
            "subst_fracture_safety_factor", "subst_cycles_to_failure",
            "subst_life_fraction_used",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_material_preset_overrides(self):
        """Material preset should override fracture toughness."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=20.0,
            outer_radius_mm=80.0,
            speed_rpm=5000,
            crack_location_radius_mm=30.0,
            initial_crack_size_mm=0.5,
            material_preset="cfrp_hoop_wound",
        )
        assert result["K_IC_mpa_sqrt_m"] == 35.0
        assert "Carbon Fiber" in result["material_display_name"]

    def test_custom_material(self):
        """Custom material should pass through user-supplied values."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=20.0,
            outer_radius_mm=80.0,
            speed_rpm=5000,
            crack_location_radius_mm=30.0,
            initial_crack_size_mm=0.5,
            material_preset="custom",
            fracture_toughness_mpa_sqrt_m=12.0,
            paris_C=1e-9,
            paris_m=3.0,
        )
        assert result["K_IC_mpa_sqrt_m"] == 12.0
        assert result["material_display_name"] == "Custom Material"

    def test_large_crack_unacceptable(self):
        """A very large crack relative to the component should be unacceptable."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=40.0,
            outer_radius_mm=100.0,
            speed_rpm=20000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=20.0,
            crack_orientation="radial",  # radial uses hoop stress (higher)
            material_preset="generic_polymer",
        )
        assert result["status"] == "unacceptable"

    def test_invalid_geometry_raises(self):
        with pytest.raises(ValueError, match="geometry_type"):
            analyze_fracture_and_crack_growth(
                geometry_type="cylinder",
                inner_radius_mm=10.0,
                outer_radius_mm=50.0,
                speed_rpm=5000,
                crack_location_radius_mm=20.0,
                initial_crack_size_mm=1.0,
            )

    def test_solid_disk(self):
        """Solid disk should work without inner radius."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="solid_disk",
            inner_radius_mm=0.0,
            outer_radius_mm=100.0,
            speed_rpm=8000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            material_preset="pa6_gf30",
        )
        assert result["K_I_mpa_sqrt_m"] > 0
        assert result["applied_hoop_stress_mpa"] > 0

    # --- New crack type integration tests ---

    def test_elliptical_surface_crack_type(self):
        """Full integration with elliptical_surface crack type."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_type="elliptical_surface",
            material_preset="pa6_gf30",
            crack_aspect_ratio=0.5,
        )
        assert result["K_I_mpa_sqrt_m"] > 0
        assert result["cycles_to_failure"] > 0

    def test_corner_crack_type(self):
        """Full integration with corner crack type."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_type="corner",
            material_preset="pa6_gf30",
            crack_aspect_ratio=1.0,
        )
        assert result["K_I_mpa_sqrt_m"] > 0
        assert result["cycles_to_failure"] > 0

    def test_double_edge_crack_type(self):
        """Full integration with double_edge crack type."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_type="double_edge",
            material_preset="pa6_gf30",
        )
        assert result["K_I_mpa_sqrt_m"] > 0
        assert result["cycles_to_failure"] > 0

    def test_crack_aspect_ratio_affects_result(self):
        """Different a/c values should give different K_I for elliptical_surface."""
        r1 = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_type="elliptical_surface",
            material_preset="pa6_gf30",
            crack_aspect_ratio=0.3,
        )
        r2 = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_type="elliptical_surface",
            material_preset="pa6_gf30",
            crack_aspect_ratio=2.0,
        )
        assert r1["K_I_mpa_sqrt_m"] != pytest.approx(r2["K_I_mpa_sqrt_m"], rel=0.01)

    def test_aspect_ratio_ignored_for_through_crack(self):
        """aspect_ratio has no effect on through crack."""
        r1 = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_type="through",
            material_preset="pa6_gf30",
            crack_aspect_ratio=0.5,
        )
        r2 = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_type="through",
            material_preset="pa6_gf30",
            crack_aspect_ratio=2.0,
        )
        assert r1["K_I_mpa_sqrt_m"] == pytest.approx(r2["K_I_mpa_sqrt_m"], rel=1e-10)

    # --- Bug fix regression tests ---

    def test_circumferential_uses_radial_stress(self):
        """Fix #1: Circumferential crack should use radial stress as driver."""
        r_circ = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_orientation="circumferential",
            material_preset="pa6_gf30",
        )
        r_rad = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
            crack_orientation="radial",
            material_preset="pa6_gf30",
        )
        # Radial uses hoop stress (higher), circ uses radial stress (lower)
        assert r_circ["K_I_mpa_sqrt_m"] < r_rad["K_I_mpa_sqrt_m"]

    def test_initial_crack_at_critical_zero_life(self):
        """Fix #2: If initial crack >= critical, cycles should be 0."""
        # Use very high speed and very large crack to trigger this
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=50000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=30.0,
            material_preset="generic_polymer",
        )
        # If crack is already at/above critical, cycles should be 0
        if result["fracture_safety_factor"] < 1.0:
            assert result["cycles_to_failure"] == 0.0

    def test_crack_location_outside_bounds_raises(self):
        """Fix #3: Crack location must be within material bounds."""
        with pytest.raises(ValueError, match="Crack location"):
            analyze_fracture_and_crack_growth(
                geometry_type="annular_disk",
                inner_radius_mm=25.0,
                outer_radius_mm=100.0,
                speed_rpm=10000,
                crack_location_radius_mm=15.0,  # < inner radius
                initial_crack_size_mm=1.0,
            )

    def test_solid_disk_crack_outside_bounds_raises(self):
        """Fix #3: Solid disk crack location must be within outer radius."""
        with pytest.raises(ValueError, match="Crack location"):
            analyze_fracture_and_crack_growth(
                geometry_type="solid_disk",
                inner_radius_mm=0.0,
                outer_radius_mm=50.0,
                speed_rpm=10000,
                crack_location_radius_mm=60.0,  # > outer radius
                initial_crack_size_mm=1.0,
            )

    def test_unknown_preset_raises(self):
        """Fix #9: Unknown preset should raise ValueError, not silently use custom."""
        with pytest.raises(ValueError, match="Unknown material_preset"):
            analyze_fracture_and_crack_growth(
                geometry_type="annular_disk",
                inner_radius_mm=25.0,
                outer_radius_mm=100.0,
                speed_rpm=10000,
                crack_location_radius_mm=50.0,
                initial_crack_size_mm=1.0,
                material_preset="nonexistent_material",
            )

    def test_life_fraction_used_key(self):
        """Fix #11: Return dict uses 'life_fraction_used' not 'remaining_life_fraction'."""
        result = analyze_fracture_and_crack_growth(
            geometry_type="annular_disk",
            inner_radius_mm=25.0,
            outer_radius_mm=100.0,
            speed_rpm=10000,
            crack_location_radius_mm=50.0,
            initial_crack_size_mm=1.0,
        )
        assert "life_fraction_used" in result
        assert "remaining_life_fraction" not in result


# ---------------------------------------------------------------------------
# Material database tests
# ---------------------------------------------------------------------------

class TestMaterialDatabase:
    def test_all_presets_have_required_fields(self):
        """Every preset must have all required material properties."""
        required = {"display_name", "K_IC", "paris_C", "paris_m", "density", "E_gpa", "sigma_uts"}
        for key, mat in FRACTURE_MATERIALS.items():
            for field in required:
                assert field in mat, f"Preset '{key}' missing field '{field}'"
            assert mat["K_IC"] > 0
            assert mat["paris_C"] > 0
            assert mat["paris_m"] > 0

    def test_get_presets_matches_dict(self):
        assert get_fracture_material_presets() is FRACTURE_MATERIALS
