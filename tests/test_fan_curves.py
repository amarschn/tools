"""Tests for pycalcs.fan_curves module."""

import math
import pytest

from pycalcs.fan_curves import (
    compute_air_density,
    convert_flow,
    convert_pressure,
    convert_curve_units,
    interpolate_curve,
    scale_curve_speed,
    scale_curve_density,
    infer_system_k,
    evaluate_system_curve,
    system_pressure_at_flow,
    find_intersections,
    validate_curve_data,
    analyze_fan_operating_point,
    compare_fans,
    generate_plot_data,
    format_equations,
    get_fan_library,
    get_fan_archetype,
    get_library_summary,
    FAN_LIBRARY,
    STANDARD_AIR_DENSITY,
)


# =============================================================================
# Unit Conversion
# =============================================================================


class TestUnitConversion:
    def test_cfm_to_m3s_roundtrip(self):
        cfm_val = 100.0
        m3s = convert_flow(cfm_val, "CFM", "m3/s")
        back = convert_flow(m3s, "m3/s", "CFM")
        assert abs(back - cfm_val) < 0.01

    def test_inwg_to_pa_roundtrip(self):
        inwg_val = 1.0
        pa = convert_pressure(inwg_val, "in_wg", "Pa")
        assert abs(pa - 249.089) < 0.1
        back = convert_pressure(pa, "Pa", "in_wg")
        assert abs(back - inwg_val) < 0.001

    def test_identity_conversion(self):
        assert convert_flow(5.0, "m3/s", "m3/s") == 5.0
        assert convert_pressure(100.0, "Pa", "Pa") == 100.0

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError):
            convert_flow(1.0, "gallons", "m3/s")
        with pytest.raises(ValueError):
            convert_pressure(1.0, "Pa", "psi")

    def test_convert_curve_units(self):
        curve = [[100.0, 1.0], [200.0, 0.5]]  # CFM, in_wg
        result = convert_curve_units(curve, "CFM", "in_wg", "m3/s", "Pa")
        assert len(result) == 2
        assert result[0][0] == pytest.approx(convert_flow(100.0, "CFM", "m3/s"), rel=1e-3)
        assert result[0][1] == pytest.approx(convert_pressure(1.0, "in_wg", "Pa"), rel=1e-3)


# =============================================================================
# Air Density
# =============================================================================


class TestAirDensity:
    def test_standard_conditions(self):
        rho = compute_air_density(20.0, 0.0)
        assert abs(rho - 1.204) < 0.01

    def test_denver_altitude(self):
        # Denver ~1609m, ~20C
        rho = compute_air_density(20.0, 1609.0)
        assert 0.99 < rho < 1.05  # Roughly 1.0 kg/m3 at Denver

    def test_hot_air_is_less_dense(self):
        rho_cold = compute_air_density(0.0, 0.0)
        rho_hot = compute_air_density(40.0, 0.0)
        assert rho_cold > rho_hot


# =============================================================================
# Interpolation
# =============================================================================


class TestInterpolation:
    def test_basic_interpolation(self):
        curve = [[0.0, 100.0], [0.5, 50.0], [1.0, 0.0]]
        assert interpolate_curve(curve, 0.25) == pytest.approx(75.0)
        assert interpolate_curve(curve, 0.75) == pytest.approx(25.0)

    def test_boundary_clamping(self):
        curve = [[0.0, 100.0], [1.0, 0.0]]
        assert interpolate_curve(curve, -0.5) == 100.0
        assert interpolate_curve(curve, 1.5) == 0.0

    def test_exact_point(self):
        curve = [[0.0, 100.0], [0.5, 50.0], [1.0, 0.0]]
        assert interpolate_curve(curve, 0.5) == pytest.approx(50.0)

    def test_empty_curve_returns_none(self):
        assert interpolate_curve([], 0.5) is None
        assert interpolate_curve([[1.0, 2.0]], 0.5) is None

    def test_unsorted_curve_still_works(self):
        curve = [[1.0, 0.0], [0.0, 100.0], [0.5, 50.0]]
        assert interpolate_curve(curve, 0.25) == pytest.approx(75.0)

    def test_no_clamp_returns_none_outside_domain(self):
        curve = [[0.0, 100.0], [1.0, 0.0]]
        assert interpolate_curve(curve, -0.1, clamp=False) is None
        assert interpolate_curve(curve, 1.1, clamp=False) is None


# =============================================================================
# Scaling
# =============================================================================


class TestScaling:
    def test_speed_scaling_pressure(self):
        curve = [[0.0, 100.0], [1.0, 0.0]]
        scaled = scale_curve_speed(curve, 1000.0, 1200.0, "pressure")
        # Flow: 1.0 * 1.2 = 1.2
        assert scaled[1][0] == pytest.approx(1.2)
        # Pressure: 0.0 * 1.44 = 0.0 (at max flow)
        # Pressure at zero flow: 100 * 1.44 = 144
        assert scaled[0][1] == pytest.approx(144.0)

    def test_speed_scaling_power(self):
        curve = [[0.0, 10.0], [1.0, 20.0]]
        scaled = scale_curve_speed(curve, 1000.0, 2000.0, "power")
        # Power scales by (2000/1000)^3 = 8
        assert scaled[0][1] == pytest.approx(80.0)
        assert scaled[1][1] == pytest.approx(160.0)

    def test_speed_scaling_efficiency_unchanged(self):
        curve = [[0.0, 0.0], [0.5, 0.8], [1.0, 0.5]]
        scaled = scale_curve_speed(curve, 1000.0, 1500.0, "efficiency")
        # Efficiency values unchanged
        assert scaled[1][1] == pytest.approx(0.8)
        # Flow still scales
        assert scaled[1][0] == pytest.approx(0.75)

    def test_density_scaling(self):
        curve = [[0.0, 200.0], [1.0, 0.0]]
        scaled = scale_curve_density(curve, 1.225, 1.0)
        # Pressure scales by 1.0/1.225
        assert scaled[0][1] == pytest.approx(200.0 * 1.0 / 1.225, rel=1e-3)
        # Flow unchanged
        assert scaled[0][0] == 0.0
        assert scaled[1][0] == 1.0

    def test_affinity_law_manual_verification(self):
        """Hand-checkable: 1500 RPM to 1800 RPM (ratio = 1.2)."""
        curve = [[0.0, 500.0], [0.5, 300.0], [1.0, 0.0]]
        ratio = 1800.0 / 1500.0  # 1.2

        scaled_p = scale_curve_speed(curve, 1500.0, 1800.0, "pressure")
        assert scaled_p[0][0] == pytest.approx(0.0 * ratio)
        assert scaled_p[0][1] == pytest.approx(500.0 * ratio**2)
        assert scaled_p[1][0] == pytest.approx(0.5 * ratio)
        assert scaled_p[1][1] == pytest.approx(300.0 * ratio**2)

    def test_zero_rpm_raises(self):
        with pytest.raises(ValueError):
            scale_curve_speed([[0, 100]], 0, 1000, "pressure")


# =============================================================================
# System Curve
# =============================================================================


class TestSystemCurve:
    def test_infer_k(self):
        k = infer_system_k(0.5, 100.0)
        assert k == pytest.approx(400.0)  # 100 / 0.5^2

    def test_infer_k_with_fixed(self):
        k = infer_system_k(0.5, 100.0, dp_fixed=25.0)
        assert k == pytest.approx(300.0)  # (100-25) / 0.25

    def test_evaluate_system_curve(self):
        flows = [0.0, 0.5, 1.0]
        pressures = evaluate_system_curve(flows, k_coefficient=100.0, dp_fixed=10.0)
        assert pressures[0] == pytest.approx(10.0)
        assert pressures[1] == pytest.approx(35.0)  # 10 + 100*0.25
        assert pressures[2] == pytest.approx(110.0)  # 10 + 100*1.0

    def test_infer_k_with_margin(self):
        k = infer_system_k(0.5, 110.0, dp_fixed=10.0, margin=20.0)
        assert k == pytest.approx(320.0)

    def test_zero_flow_raises(self):
        with pytest.raises(ValueError):
            infer_system_k(0.0, 100.0)


# =============================================================================
# Intersection Solver
# =============================================================================


class TestIntersectionSolver:
    def test_single_intersection_hand_checkable(self):
        """Simple case: parabolic-like fan, quadratic system.
        Fan: P = 200 - 200*Q^2 (at Q=0: 200Pa, at Q=1: 0Pa)
        System: P = 100*Q^2
        Intersection: 200 - 200*Q^2 = 100*Q^2 => 200 = 300*Q^2 => Q = sqrt(2/3)
        """
        # Approximate the parabolic fan with piecewise-linear segments
        n = 20
        fan_curve = []
        for i in range(n + 1):
            q = i / n
            p = 200.0 * (1.0 - q**2)
            fan_curve.append([q, p])

        intersections = find_intersections(fan_curve, k_coefficient=100.0)
        assert len(intersections) == 1

        expected_q = math.sqrt(2.0 / 3.0)  # ~0.8165
        assert intersections[0]["flow"] == pytest.approx(expected_q, abs=0.02)
        assert intersections[0]["is_stable"] is True

    def test_no_intersection_fan_undersized(self):
        """Fan max pressure (50 Pa) is below system pressure at all flows."""
        fan_curve = [[0.0, 50.0], [0.5, 30.0], [1.0, 0.0]]
        intersections = find_intersections(fan_curve, k_coefficient=200.0, dp_fixed=100.0)
        assert len(intersections) == 0

    def test_dual_intersection_fc_fan(self):
        """Forward-curved fan with hump should produce two intersections.

        The system curve starts above the fan at low flow (due to dp_fixed),
        dips below the hump, then rises back above at high flow. This creates
        two crossings — one unstable (on the rising side) and one stable
        (on the falling side).
        """
        fan_curve = [
            [0.0, 300.0],
            [0.3, 350.0],
            [0.6, 400.0],  # Hump peak
            [0.9, 380.0],
            [1.2, 300.0],
            [1.5, 180.0],
            [2.0, 50.0],
            [2.5, 0.0],
        ]
        # System: dP = 350 + 50*Q^2
        # At Q=0.0: 350 > fan 300 (system above)
        # At Q=0.6: 368 < fan 400 (fan above — first crossing happened)
        # At Q=0.9: 390.5 > fan 380 (system above again — second crossing)
        k = 50.0
        dp_fixed = 350.0
        intersections = find_intersections(fan_curve, k_coefficient=k, dp_fixed=dp_fixed)
        assert len(intersections) >= 2, (
            f"Expected >= 2 intersections, got {len(intersections)}: {intersections}"
        )

        stable_count = sum(1 for ix in intersections if ix["is_stable"])
        unstable_count = sum(1 for ix in intersections if not ix["is_stable"])
        assert stable_count >= 1
        assert unstable_count >= 1

    def test_intersection_angle_computed(self):
        fan_curve = [[0.0, 200.0], [0.5, 100.0], [1.0, 0.0]]
        intersections = find_intersections(fan_curve, k_coefficient=100.0)
        assert len(intersections) >= 1
        assert intersections[0]["intersection_angle_deg"] > 0


# =============================================================================
# Validation
# =============================================================================


class TestValidation:
    def test_fewer_than_3_points_blocking(self):
        warnings = validate_curve_data([[0, 100], [1, 0]])
        blocking = [w for w in warnings if w["tier"] == "blocking"]
        assert len(blocking) == 1
        assert blocking[0]["code"] == "insufficient-points"

    def test_negative_flow_blocking(self):
        warnings = validate_curve_data([[-1, 100], [0, 50], [1, 0]])
        blocking = [w for w in warnings if w["tier"] == "blocking"]
        assert any(w["code"] == "negative-flow" for w in blocking)

    def test_unsorted_flows_caution(self):
        warnings = validate_curve_data([[1, 0], [0, 100], [0.5, 50]])
        caution = [w for w in warnings if w["tier"] == "caution"]
        assert any(w["code"] == "unsorted-flow" for w in caution)

    def test_valid_curve_no_warnings(self):
        warnings = validate_curve_data([[0, 100], [0.5, 50], [1, 0]])
        blocking = [w for w in warnings if w["tier"] == "blocking"]
        assert len(blocking) == 0


# =============================================================================
# Operating Point Analysis
# =============================================================================


class TestOperatingPointAnalysis:
    @pytest.fixture
    def simple_fan(self):
        """A simple axial fan for testing."""
        return {
            "candidate_id": "test-fan",
            "title": "Test Fan",
            "source_type": "user-entered",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1000.0,
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [
                [0.0, 200.0],
                [0.2, 180.0],
                [0.4, 140.0],
                [0.6, 90.0],
                [0.8, 40.0],
                [1.0, 0.0],
            ],
            "power_curve": [
                [0.0, 20.0],
                [0.2, 35.0],
                [0.4, 50.0],
                [0.6, 55.0],
                [0.8, 50.0],
                [1.0, 40.0],
            ],
        }

    def test_basic_analysis(self, simple_fan):
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.5,
            duty_pressure=100.0,
            k_coefficient=infer_system_k(0.5, 100.0),
        )
        assert result["operating_flow"] is not None
        assert result["operating_flow"] > 0
        assert result["operating_pressure"] is not None
        assert result["warning_tier"] != "blocking"

    def test_meets_duty(self, simple_fan):
        k = infer_system_k(0.4, 80.0)
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.4,
            duty_pressure=80.0,
            k_coefficient=k,
        )
        assert result["meets_duty"] is True

    def test_efficiency_computed_with_power(self, simple_fan):
        k = infer_system_k(0.5, 100.0)
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.5,
            duty_pressure=100.0,
            k_coefficient=k,
        )
        assert result["operating_efficiency"] is not None
        assert 0 < result["operating_efficiency"] <= 1.0

    def test_efficiency_none_without_power(self, simple_fan):
        del simple_fan["power_curve"]
        k = infer_system_k(0.5, 100.0)
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.5,
            duty_pressure=100.0,
            k_coefficient=k,
        )
        assert result["operating_efficiency"] is None
        info_warnings = [w for w in result["warnings"] if w["code"] == "no-power-data"]
        assert len(info_warnings) == 1

    def test_density_correction_warning(self, simple_fan):
        k = infer_system_k(0.5, 100.0)
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.5,
            duty_pressure=100.0,
            k_coefficient=k,
            operating_density=1.0,  # Different from reference 1.225
        )
        density_warnings = [w for w in result["warnings"] if w["code"] == "density-correction"]
        assert len(density_warnings) == 1
        assert density_warnings[0]["tier"] == "caution"

    def test_speed_scaling_warning(self, simple_fan):
        simple_fan["operating_speed_rpm"] = 1500.0  # 50% increase
        k = infer_system_k(0.5, 100.0)
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.5,
            duty_pressure=100.0,
            k_coefficient=k,
        )
        speed_warnings = [w for w in result["warnings"] if "speed" in w["code"]]
        assert len(speed_warnings) >= 1

    def test_no_intersection_returns_blocking(self, simple_fan):
        # System requires much more pressure than fan can deliver
        # Fan max pressure is 200 Pa, so a system with dp_fixed=300 ensures no intersection
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.5,
            duty_pressure=1000.0,
            k_coefficient=5000.0,
            dp_fixed=300.0,
        )
        assert result["operating_flow"] is None
        assert result["warning_tier"] == "blocking"

    def test_annual_energy_computed(self, simple_fan):
        k = infer_system_k(0.5, 100.0)
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.5,
            duty_pressure=100.0,
            k_coefficient=k,
            operating_hours=8760.0,
            electricity_rate=0.10,
        )
        assert result["annual_energy_kwh"] is not None
        assert result["annual_energy_cost"] is not None
        assert result["annual_energy_cost"] > 0

    def test_pressure_basis_mismatch_blocks_result(self, simple_fan):
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.5,
            duty_pressure=100.0,
            k_coefficient=infer_system_k(0.5, 100.0),
            required_pressure_basis="total",
        )
        assert result["warning_tier"] == "blocking"
        assert any(w["code"] == "pressure-basis-mismatch" for w in result["warnings"])

    def test_duty_margin_reported(self, simple_fan):
        k = infer_system_k(0.4, 80.0)
        result = analyze_fan_operating_point(
            fan_candidate=simple_fan,
            duty_flow=0.4,
            duty_pressure=80.0,
            k_coefficient=k,
        )
        assert result["duty_margin_pressure"] is not None


# =============================================================================
# Comparison Engine
# =============================================================================


class TestComparisonEngine:
    def test_two_fan_comparison(self):
        fan_a = {
            "candidate_id": "fan-a",
            "title": "Fan A",
            "source_type": "user-entered",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1000.0,
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [
                [0.0, 200.0], [0.3, 160.0], [0.6, 90.0], [1.0, 0.0],
            ],
            "power_curve": [
                [0.0, 20.0], [0.3, 40.0], [0.6, 50.0], [1.0, 35.0],
            ],
        }
        fan_b = {
            "candidate_id": "fan-b",
            "title": "Fan B",
            "source_type": "user-entered",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1000.0,
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [
                [0.0, 150.0], [0.3, 120.0], [0.6, 60.0], [1.0, 0.0],
            ],
            "power_curve": [
                [0.0, 15.0], [0.3, 25.0], [0.6, 30.0], [1.0, 20.0],
            ],
        }

        result = compare_fans(
            fan_candidates=[fan_a, fan_b],
            duty_flow=0.4,
            duty_pressure=80.0,
            k_coefficient=infer_system_k(0.4, 80.0),
        )
        assert len(result["results"]) == 2
        assert len(result["ranked_order"]) == 2

    def test_ranking_by_lowest_power(self):
        fan_a = {
            "candidate_id": "high-power",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1000.0,
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [[0.0, 200.0], [0.5, 100.0], [1.0, 0.0]],
            "power_curve": [[0.0, 50.0], [0.5, 80.0], [1.0, 60.0]],
        }
        fan_b = {
            "candidate_id": "low-power",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1000.0,
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [[0.0, 200.0], [0.5, 100.0], [1.0, 0.0]],
            "power_curve": [[0.0, 20.0], [0.5, 30.0], [1.0, 25.0]],
        }
        k = infer_system_k(0.4, 80.0)
        result = compare_fans(
            [fan_a, fan_b], 0.4, 80.0, k, ranking_criterion="lowest_shaft_power"
        )
        # low-power should rank first
        assert result["ranked_order"][0] == "low-power"

    def test_compare_fans_honors_required_basis(self):
        fan = {
            "candidate_id": "fan-a",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1000.0,
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [[0.0, 200.0], [0.5, 100.0], [1.0, 0.0]],
        }
        result = compare_fans(
            [fan],
            0.4,
            80.0,
            infer_system_k(0.4, 80.0),
            required_pressure_basis="total",
        )
        assert result["results"][0]["warning_tier"] == "blocking"

    def test_independent_per_fan_speed(self):
        fan_a = {
            "candidate_id": "slow",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 800.0,  # Slowed down
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [[0.0, 200.0], [0.5, 100.0], [1.0, 0.0]],
        }
        fan_b = {
            "candidate_id": "fast",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1200.0,  # Sped up
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [[0.0, 200.0], [0.5, 100.0], [1.0, 0.0]],
        }
        k = infer_system_k(0.4, 80.0)
        result = compare_fans([fan_a, fan_b], 0.4, 80.0, k)
        # Both should have results but at different operating points
        r_slow = [r for r in result["results"] if r["candidate_id"] == "slow"][0]
        r_fast = [r for r in result["results"] if r["candidate_id"] == "fast"][0]
        # Fast fan should have higher operating flow (if it intersects)
        if r_slow["operating_flow"] is not None and r_fast["operating_flow"] is not None:
            assert r_fast["operating_flow"] > r_slow["operating_flow"]


# =============================================================================
# Density Scaling Integration
# =============================================================================


class TestDensityScalingIntegration:
    def test_sea_level_to_denver(self):
        """Full integration: fan at sea level applied at Denver altitude."""
        fan = {
            "candidate_id": "test",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1000.0,
            "reference_density_kg_m3": 1.225,
            "pressure_basis": "static",
            "pressure_curve": [
                [0.0, 200.0], [0.25, 160.0], [0.5, 100.0], [0.75, 40.0], [1.0, 0.0],
            ],
        }
        denver_density = compute_air_density(20.0, 1609.0)
        k = infer_system_k(0.4, 80.0)

        result_sl = analyze_fan_operating_point(
            fan, 0.4, 80.0, k, operating_density=1.225,
        )
        result_denver = analyze_fan_operating_point(
            fan, 0.4, 80.0, k, operating_density=denver_density,
        )

        # At Denver, fan delivers less pressure, so operating flow should be lower
        if result_sl["operating_flow"] is not None and result_denver["operating_flow"] is not None:
            assert result_denver["operating_flow"] < result_sl["operating_flow"]


# =============================================================================
# Fan Library
# =============================================================================


class TestFanLibrary:
    def test_library_has_six_archetypes(self):
        assert len(FAN_LIBRARY) == 6

    def test_all_archetypes_have_required_fields(self):
        required_keys = [
            "candidate_id", "title", "source_type", "archetype_note",
            "reference_speed_rpm", "reference_density_kg_m3",
            "pressure_basis", "pressure_curve", "power_curve",
        ]
        for key, fan in FAN_LIBRARY.items():
            for rk in required_keys:
                assert rk in fan, f"Archetype {key} missing field {rk}"

    def test_all_archetypes_are_library_type(self):
        for key, fan in FAN_LIBRARY.items():
            assert fan["source_type"] == "library-archetype"

    def test_archetype_curves_are_physical(self):
        for key, fan in FAN_LIBRARY.items():
            pc = fan["pressure_curve"]
            assert len(pc) >= 10, f"{key} has too few pressure points"
            # Pressure at zero flow should be positive
            assert pc[0][1] > 0, f"{key} pressure at zero flow should be > 0"
            # All flows should be >= 0
            for pt in pc:
                assert pt[0] >= 0, f"{key} has negative flow"

    def test_get_fan_archetype_returns_copy(self):
        fan1 = get_fan_archetype("medium-axial-120mm")
        fan2 = get_fan_archetype("medium-axial-120mm")
        assert fan1 is not fan2
        fan1["operating_speed_rpm"] = 9999
        assert fan2["operating_speed_rpm"] != 9999

    def test_get_fan_archetype_unknown_returns_none(self):
        assert get_fan_archetype("nonexistent") is None

    def test_library_summary(self):
        summaries = get_library_summary()
        assert len(summaries) == 6
        for s in summaries:
            assert "candidate_id" in s
            assert "title" in s

    def test_each_archetype_intersects_reasonable_system(self):
        """Every archetype should find an operating point with a reasonable system."""
        for key, fan in FAN_LIBRARY.items():
            pc = fan["pressure_curve"]
            mid_idx = len(pc) // 2
            mid_flow = pc[mid_idx][0]
            mid_pressure = pc[mid_idx][1]
            if mid_flow <= 0 or mid_pressure <= 0:
                continue
            k = infer_system_k(mid_flow, mid_pressure * 0.6)
            result = analyze_fan_operating_point(
                fan_candidate=fan,
                duty_flow=mid_flow,
                duty_pressure=mid_pressure * 0.6,
                k_coefficient=k,
            )
            assert result["operating_flow"] is not None, (
                f"Archetype {key} failed to find operating point"
            )


# =============================================================================
# Plot Data Generation
# =============================================================================


class TestPlotDataGeneration:
    def test_basic_plot_data(self):
        fan = get_fan_archetype("medium-axial-120mm")
        k = infer_system_k(0.04, 50.0)
        data = generate_plot_data(
            [fan], k, duty_flow=0.04, duty_pressure=50.0,
        )
        assert len(data["flow_range"]) > 0
        assert len(data["system_curve"]) == len(data["flow_range"])
        assert len(data["fan_curves"]) == 1
        assert data["duty_point"] is not None


# =============================================================================
# Equation Formatting
# =============================================================================


class TestEquationFormatting:
    def test_basic_equations(self):
        fan = {
            "candidate_id": "test",
            "reference_speed_rpm": 1000.0,
            "operating_speed_rpm": 1200.0,
            "reference_density_kg_m3": 1.225,
        }
        result = {
            "operating_flow": 0.5,
            "operating_pressure": 100.0,
            "shaft_power_w": 60.0,
            "operating_efficiency": 0.833,
        }
        eqs = format_equations(fan, result, 500.0, 0.0, 0.0, 1.0)
        assert "system_curve" in eqs
        assert "density_scaling" in eqs
        assert "speed_flow" in eqs
        assert "efficiency" in eqs
