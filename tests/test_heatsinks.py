"""Tests for the heatsink analysis module."""

from __future__ import annotations

import math

import pytest

from pycalcs.heatsinks import (
    air_properties,
    analyze_heatsink_spreading_view,
    analyze_plate_fin_heatsink,
    calculate_plate_fin_geometry,
    estimate_bypass_fraction,
    fan_curve_pressure,
    fin_channel_radiation_view_factor,
    forced_convection_plate_array,
    get_heatsink_sweep_metadata,
    natural_convection_horizontal_plate_array,
    natural_convection_plate_array,
    rectangular_fin_efficiency,
    rectangular_spreading_resistance,
    required_sink_thermal_resistance,
    run_heatsink_1d_sweep,
    run_heatsink_2d_contour,
    solve_fan_operating_point,
)
from pycalcs.heatsink_spreading import solve_base_spreading_field


def test_geometry_derivation() -> None:
    geometry = calculate_plate_fin_geometry(
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.025,
        fin_thickness=0.0015,
        fin_count=10,
    )
    expected_spacing = (0.08 - 10 * 0.0015) / 9
    assert math.isclose(geometry.fin_spacing, expected_spacing, rel_tol=1e-9)
    assert geometry.channel_count == 9
    assert geometry.total_area > geometry.exposed_base_area
    assert geometry.open_area_ratio < 1.0


def test_air_properties_are_physical() -> None:
    props = air_properties(40.0)
    assert 1.0 < props.density < 1.2
    assert 1.5e-5 < props.dynamic_viscosity < 2.5e-5
    assert 0.6 < props.prandtl < 0.8


def test_required_sink_resistance_budget() -> None:
    required = required_sink_thermal_resistance(
        heat_load=20.0,
        ambient_temperature=30.0,
        target_junction_temperature=100.0,
        interface_resistance=0.2,
        junction_to_case_resistance=0.5,
    )
    assert math.isclose(required, 2.8, rel_tol=1e-9)


def test_fin_efficiency_drops_with_higher_h() -> None:
    low_h = rectangular_fin_efficiency(
        fin_height=0.03,
        fin_thickness=0.001,
        fin_length=0.08,
        heat_transfer_coefficient=10.0,
        thermal_conductivity=201.0,
    )
    high_h = rectangular_fin_efficiency(
        fin_height=0.03,
        fin_thickness=0.001,
        fin_length=0.08,
        heat_transfer_coefficient=80.0,
        thermal_conductivity=201.0,
    )
    assert 0.0 < high_h < low_h <= 1.0


def test_natural_convection_strength_increases_with_temperature_rise() -> None:
    geometry = calculate_plate_fin_geometry(
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
    )
    cool = natural_convection_plate_array(geometry, surface_temperature=45.0, ambient_temperature=25.0)
    hot = natural_convection_plate_array(geometry, surface_temperature=85.0, ambient_temperature=25.0)
    assert hot["convection_coefficient"] > cool["convection_coefficient"] > 0.0
    assert hot["nusselt_number"] > cool["nusselt_number"] > 0.0


def test_forced_convection_pressure_drop_increases_with_flow() -> None:
    geometry = calculate_plate_fin_geometry(
        base_length=0.12,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=12,
    )
    low_flow = forced_convection_plate_array(
        geometry,
        surface_temperature=70.0,
        ambient_temperature=25.0,
        volumetric_flow_rate=0.0010,
    )
    high_flow = forced_convection_plate_array(
        geometry,
        surface_temperature=70.0,
        ambient_temperature=25.0,
        volumetric_flow_rate=0.0025,
    )
    assert high_flow["pressure_drop"] > low_flow["pressure_drop"] > 0.0
    assert high_flow["convection_coefficient"] > low_flow["convection_coefficient"] > 0.0


def test_fan_operating_point_stays_within_curve_limits() -> None:
    geometry = calculate_plate_fin_geometry(
        base_length=0.10,
        base_width=0.06,
        base_thickness=0.004,
        fin_height=0.025,
        fin_thickness=0.001,
        fin_count=10,
    )
    operating = solve_fan_operating_point(
        geometry=geometry,
        surface_temperature=60.0,
        ambient_temperature=25.0,
        fan_max_pressure=55.0,
        fan_max_flow_rate=0.004,
    )
    assert 0.0 < operating["volumetric_flow_rate"] < 0.004
    assert operating["pressure_drop"] > 0.0
    assert math.isclose(operating["pressure_drop"], operating["fan_pressure"], rel_tol=1e-3)


def test_main_solver_balances_heat_load_natural_convection() -> None:
    result = analyze_plate_fin_heatsink(
        heat_load=15.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
        surface_emissivity=0.85,
        airflow_mode="natural",
        interface_resistance=0.2,
        junction_to_case_resistance=0.5,
    )
    assert result["convection_mode_used"] == "natural_vertical"
    assert result["base_temperature"] > 25.0
    assert math.isclose(result["heat_rejected"], 15.0, rel_tol=5e-4)
    assert result["sink_thermal_resistance"] > 0.0


def test_main_solver_forced_flow_reduces_temperature() -> None:
    natural = analyze_plate_fin_heatsink(
        heat_load=20.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
        surface_emissivity=0.85,
        airflow_mode="natural",
    )
    forced = analyze_plate_fin_heatsink(
        heat_load=20.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
        surface_emissivity=0.85,
        airflow_mode="forced",
        volumetric_flow_rate=0.002,
    )
    assert forced["base_temperature"] < natural["base_temperature"]
    assert forced["pressure_drop"] > 0.0


def test_invalid_geometry_raises() -> None:
    with pytest.raises(ValueError):
        calculate_plate_fin_geometry(
            base_length=0.10,
            base_width=0.01,
            base_thickness=0.005,
            fin_height=0.03,
            fin_thickness=0.002,
            fin_count=8,
        )


def test_air_thermal_conductivity_at_elevated_temperature() -> None:
    """Sutherland fit should match NIST data within ~2% at 500 K."""
    props = air_properties(227.0)  # 500 K film temperature
    # NIST value at 500 K is approximately 0.0395 W/mK
    assert 0.038 < props.thermal_conductivity < 0.041


def test_radiation_view_factor_decreases_with_tight_spacing() -> None:
    wide = fin_channel_radiation_view_factor(fin_height=0.02, fin_spacing=0.02)
    tight = fin_channel_radiation_view_factor(fin_height=0.02, fin_spacing=0.004)
    assert 0.4 < wide < 0.6  # H/s = 1, F ≈ 0.5
    assert 0.1 < tight < 0.25  # H/s = 5, F ≈ 0.167
    assert wide > tight


def test_radiation_view_factor_edge_cases() -> None:
    assert fin_channel_radiation_view_factor(0.0, 0.01) == 1.0
    assert fin_channel_radiation_view_factor(0.01, 0.0) == 1.0


def test_natural_convection_reports_induced_velocity() -> None:
    geometry = calculate_plate_fin_geometry(
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
    )
    result = natural_convection_plate_array(
        geometry=geometry,
        surface_temperature=80.0,
        ambient_temperature=25.0,
    )
    # Should report a small but positive induced velocity
    assert result["channel_velocity"] > 0.0
    assert result["channel_velocity"] < 2.0
    assert result["volumetric_flow_rate"] > 0.0


def test_solver_returns_radiation_view_factor() -> None:
    result = analyze_plate_fin_heatsink(
        heat_load=10.0,
        ambient_temperature=25.0,
        target_junction_temperature=85.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
    )
    assert "radiation_view_factor" in result
    assert 0.0 < result["radiation_view_factor"] < 1.0


def test_horizontal_down_gives_lower_performance_than_vertical() -> None:
    geometry = calculate_plate_fin_geometry(
        base_length=0.10, base_width=0.08, base_thickness=0.005,
        fin_height=0.03, fin_thickness=0.001, fin_count=10,
    )
    vertical = natural_convection_plate_array(geometry, 70.0, 25.0)
    horiz_down = natural_convection_horizontal_plate_array(geometry, 70.0, 25.0, facing="down")
    assert vertical["convection_coefficient"] > horiz_down["convection_coefficient"]


def test_horizontal_up_returns_positive_coefficient() -> None:
    geometry = calculate_plate_fin_geometry(
        base_length=0.10, base_width=0.08, base_thickness=0.005,
        fin_height=0.03, fin_thickness=0.001, fin_count=10,
    )
    result = natural_convection_horizontal_plate_array(geometry, 70.0, 25.0, facing="up")
    assert result["convection_coefficient"] > 0.0
    assert result["nusselt_number"] > 0.0


def test_spreading_resistance_is_positive_for_small_source() -> None:
    r_sp = rectangular_spreading_resistance(
        source_length=0.020,
        source_width=0.020,
        base_length=0.100,
        base_width=0.080,
        base_thickness=0.005,
        thermal_conductivity=201.0,
    )
    assert r_sp > 0.0
    assert r_sp < 2.0


def test_spreading_resistance_is_zero_when_source_covers_base() -> None:
    r_sp = rectangular_spreading_resistance(
        source_length=0.100,
        source_width=0.080,
        base_length=0.100,
        base_width=0.080,
        base_thickness=0.005,
        thermal_conductivity=201.0,
    )
    assert r_sp == 0.0


def test_solver_spreading_resistance_raises_junction_temp() -> None:
    """A small source should produce higher junction temp than full-base source."""
    base_args = dict(
        heat_load=15.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
    )
    no_spread = analyze_plate_fin_heatsink(**base_args)
    with_spread = analyze_plate_fin_heatsink(**base_args, source_length=0.02, source_width=0.02)
    assert with_spread["junction_temperature"] > no_spread["junction_temperature"]
    assert with_spread["spreading_resistance"] > 0.0


def test_bypass_fraction_increases_with_tight_fins() -> None:
    wide = calculate_plate_fin_geometry(
        base_length=0.10, base_width=0.08, base_thickness=0.005,
        fin_height=0.03, fin_thickness=0.001, fin_count=5,
    )
    tight = calculate_plate_fin_geometry(
        base_length=0.10, base_width=0.08, base_thickness=0.005,
        fin_height=0.03, fin_thickness=0.001, fin_count=15,
    )
    assert estimate_bypass_fraction(tight) > estimate_bypass_fraction(wide)


def test_fan_curve_piecewise_linear() -> None:
    points = [[0.0, 100.0], [0.005, 80.0], [0.01, 40.0], [0.015, 0.0]]
    # At midpoint between first two entries
    p = fan_curve_pressure(0.0025, 100.0, 0.015, fan_curve_points=points)
    assert math.isclose(p, 90.0, rel_tol=0.01)
    # Beyond last point
    p_end = fan_curve_pressure(0.02, 100.0, 0.015, fan_curve_points=points)
    assert p_end == 0.0


def test_actionable_recommendations_when_over_budget() -> None:
    """Recommendations should include specific parameter suggestions when design fails."""
    result = analyze_plate_fin_heatsink(
        heat_load=50.0,  # Very high for a small sink
        ambient_temperature=25.0,
        target_junction_temperature=60.0,
        base_length=0.05,
        base_width=0.04,
        base_thickness=0.003,
        fin_height=0.02,
        fin_thickness=0.001,
        fin_count=8,
        material_conductivity=201.0,
        surface_emissivity=0.3,
    )
    assert result["status"] == "unacceptable"
    recs = " ".join(result["recommendations"])
    assert "switch to forced convection" in recs
    assert "increase fin count from 8 to 12" in recs
    assert "increase fin height from 20 mm to 30 mm" in recs
    assert "black anodized" in recs


def test_negative_budget_recommendation_explains_cause() -> None:
    """When required R_sink is negative, recommendation should explain why and what to change."""
    result = analyze_plate_fin_heatsink(
        heat_load=100.0,
        ambient_temperature=25.0,
        target_junction_temperature=60.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
        junction_to_case_resistance=0.5,
        interface_resistance=0.2,
    )
    assert result["required_sink_thermal_resistance"] < 0
    recs = " ".join(result["recommendations"])
    assert "negative" in recs.lower()
    assert "upstream" in recs.lower()
    assert "heatsink geometry changes alone cannot fix this" in recs


def test_solver_orientation_parameter() -> None:
    """Solver should accept orientation and produce different results."""
    base_args = dict(
        heat_load=10.0,
        ambient_temperature=25.0,
        target_junction_temperature=85.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
    )
    vert = analyze_plate_fin_heatsink(**base_args, orientation="vertical")
    horiz = analyze_plate_fin_heatsink(**base_args, orientation="horizontal_down")
    assert vert["convection_mode_used"] == "natural_vertical"
    assert horiz["convection_mode_used"] == "natural_horizontal_down"
    # Horizontal down should run hotter
    assert horiz["base_temperature"] > vert["base_temperature"]


# --- Sensitivity analysis tests ---

BASELINE_INPUTS = {
    "heat_load": 15.0,
    "ambient_temperature": 25.0,
    "target_junction_temperature": 100.0,
    "base_length": 0.10,
    "base_width": 0.08,
    "base_thickness": 0.005,
    "fin_height": 0.03,
    "fin_thickness": 0.001,
    "fin_count": 10,
    "material_conductivity": 201.0,
    "surface_emissivity": 0.85,
    "airflow_mode": "natural",
}


def test_sweep_metadata_has_required_keys() -> None:
    meta = get_heatsink_sweep_metadata()
    assert "parameters" in meta
    assert "outputs" in meta
    assert "fin_height" in meta["parameters"]
    assert "sink_thermal_resistance" in meta["outputs"]
    for key, param in meta["parameters"].items():
        assert "label" in param
        assert "min" in param
        assert "max" in param


def test_approach_velocity_sweep_metadata_covers_supported_forced_flow_range() -> None:
    meta = get_heatsink_sweep_metadata()
    approach = meta["parameters"]["approach_velocity"]
    assert approach["modes"] == ["forced"]
    assert approach["max"] >= 30.0


def test_1d_sweep_returns_expected_shape() -> None:
    sweep_values = [0.02, 0.025, 0.03, 0.035, 0.04]
    result = run_heatsink_1d_sweep(
        BASELINE_INPUTS, "fin_height", sweep_values,
        output_keys=["sink_thermal_resistance"],
    )
    assert len(result["x_values"]) == 5
    assert len(result["series"]["sink_thermal_resistance"]) == 5
    assert len(result["valid_mask"]) == 5
    assert all(result["valid_mask"])
    assert result["baseline_x"] == 0.03
    assert "sink_thermal_resistance" in result["baseline_outputs"]


def test_1d_sweep_taller_fins_reduce_resistance() -> None:
    sweep_values = [0.02, 0.03, 0.04, 0.05]
    result = run_heatsink_1d_sweep(
        BASELINE_INPUTS, "fin_height", sweep_values,
        output_keys=["sink_thermal_resistance"],
    )
    r_values = result["series"]["sink_thermal_resistance"]
    # Taller fins should generally reduce thermal resistance
    assert r_values[0] > r_values[-1]


def test_1d_sweep_handles_invalid_geometry() -> None:
    """Sweeping fin_count too high should produce invalid points, not crash."""
    sweep_values = [5, 10, 200]  # 200 fins on 80mm base won't fit
    result = run_heatsink_1d_sweep(
        BASELINE_INPUTS, "fin_count", sweep_values,
        output_keys=["sink_thermal_resistance"],
    )
    assert len(result["valid_mask"]) == 3
    assert not result["valid_mask"][-1]  # 200 fins should fail


def test_2d_contour_returns_grid() -> None:
    x_vals = [0.02, 0.03, 0.04]
    y_vals = [0.0005, 0.001, 0.0015]
    result = run_heatsink_2d_contour(
        BASELINE_INPUTS, "fin_height", "fin_thickness",
        x_vals, y_vals, output_key="sink_thermal_resistance",
    )
    assert len(result["z_values"]) == 3
    assert len(result["z_values"][0]) == 3
    assert result["baseline_point"]["x"] == 0.03
    assert result["baseline_point"]["y"] == 0.001
    assert result["best_point"] is not None


# --- Phase 5: Testing & Validation ---


def test_turbulent_forced_convection_at_high_flow() -> None:
    """Verify the turbulent branch activates at high flow rates (E3)."""
    geometry = calculate_plate_fin_geometry(
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
    )
    result = forced_convection_plate_array(
        geometry,
        surface_temperature=70.0,
        ambient_temperature=25.0,
        volumetric_flow_rate=0.015,
    )
    assert result["reynolds_number"] > 2300.0
    assert result["nusselt_number"] > 0.0
    assert result["pressure_drop"] > 0.0
    assert result["convection_coefficient"] > 0.0


def test_approach_velocity_converts_to_flow_rate() -> None:
    """Approach velocity should produce forced-convection results (E4)."""
    result = analyze_plate_fin_heatsink(
        heat_load=20.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
        surface_emissivity=0.85,
        airflow_mode="forced",
        approach_velocity=3.0,
        volumetric_flow_rate=0.0,
    )
    assert result["volumetric_flow_rate"] > 0.0
    assert result["pressure_drop"] > 0.0
    # Should run significantly cooler than natural convection
    natural = analyze_plate_fin_heatsink(
        heat_load=20.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
    )
    assert result["base_temperature"] < natural["base_temperature"]


def test_very_tall_fins_have_low_efficiency() -> None:
    """Very tall thin fins should have poor efficiency (E2)."""
    result = analyze_plate_fin_heatsink(
        heat_load=15.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.10,
        base_width=0.10,
        base_thickness=0.005,
        fin_height=0.15,
        fin_thickness=0.0004,
        fin_count=10,
        material_conductivity=201.0,
    )
    assert result["fin_efficiency"] < 0.6


def test_low_heat_load_near_ambient() -> None:
    """Low heat load should produce temperatures barely above ambient (E2)."""
    result = analyze_plate_fin_heatsink(
        heat_load=1.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
    )
    assert result["base_temperature"] < 35.0
    assert result["temperature_margin"] > 100.0


def test_radiation_significant_at_high_emissivity_low_load() -> None:
    """Radiation should contribute materially with high emissivity and wide spacing (E6)."""
    result = analyze_plate_fin_heatsink(
        heat_load=3.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.10,
        base_width=0.10,
        base_thickness=0.005,
        fin_height=0.02,
        fin_thickness=0.001,
        fin_count=5,
        material_conductivity=201.0,
        surface_emissivity=0.90,
    )
    assert result["radiation_heat_rejected"] > 0.25 * 3.0

    result_low_e = analyze_plate_fin_heatsink(
        heat_load=3.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.10,
        base_width=0.10,
        base_thickness=0.005,
        fin_height=0.02,
        fin_thickness=0.001,
        fin_count=5,
        material_conductivity=201.0,
        surface_emissivity=0.05,
    )
    assert result_low_e["base_temperature"] > result["base_temperature"]


# Benchmark test for Bar-Cohen natural convection has been migrated to
# tools/simple_thermal/test-cases/bar_cohen_natural_convection.json
# and is now run by tests/test_heatsink_benchmarks.py.


# --- Spreading solver tests ---

SPREADING_BASE = dict(
    base_length=0.10,
    base_width=0.08,
    base_thickness=0.005,
    material_conductivity=201.0,
    ambient_temperature=25.0,
    sink_thermal_resistance=2.0,
)


def test_spreading_full_footprint_is_nearly_uniform() -> None:
    """When source covers the entire base, field should be near-uniform (14.1)."""
    result = solve_base_spreading_field(
        **SPREADING_BASE,
        sources=[{
            "id": "full",
            "x_center": 0.05, "y_center": 0.04,
            "length": 0.10, "width": 0.08,
            "power": 10.0,
            "junction_to_case_resistance": 0.0,
            "interface_resistance": 0.0,
        }],
    )
    assert result["converged"]
    assert result["max_spreading_delta"] < 0.5  # Less than 0.5 K spread


def test_spreading_symmetry_for_centered_source() -> None:
    """Centered source on symmetric base should give symmetric field (14.2)."""
    result = solve_base_spreading_field(
        **SPREADING_BASE,
        sources=[{
            "id": "center",
            "x_center": 0.05, "y_center": 0.04,
            "length": 0.02, "width": 0.02,
            "power": 10.0,
            "junction_to_case_resistance": 0.0,
            "interface_resistance": 0.0,
        }],
        grid_x=21, grid_y=21,
    )
    T = result["temperature_grid"]
    nx = len(T)
    ny = len(T[0])
    mid_i = nx // 2
    mid_j = ny // 2
    # Check left-right symmetry
    for i in range(mid_i):
        for j in range(ny):
            assert abs(T[i][j] - T[nx - 1 - i][j]) < 0.01


def test_spreading_smaller_source_has_higher_peak() -> None:
    """Smaller source at same power should produce higher peak (14.3)."""
    large = solve_base_spreading_field(
        **SPREADING_BASE,
        sources=[{
            "id": "large", "x_center": 0.05, "y_center": 0.04,
            "length": 0.06, "width": 0.06, "power": 10.0,
            "junction_to_case_resistance": 0.0, "interface_resistance": 0.0,
        }],
    )
    small = solve_base_spreading_field(
        **SPREADING_BASE,
        sources=[{
            "id": "small", "x_center": 0.05, "y_center": 0.04,
            "length": 0.01, "width": 0.01, "power": 10.0,
            "junction_to_case_resistance": 0.0, "interface_resistance": 0.0,
        }],
    )
    assert small["peak_base_temperature"] > large["peak_base_temperature"]
    # Mean should be much closer between the two
    mean_diff = abs(small["mean_base_temperature"] - large["mean_base_temperature"])
    peak_diff = small["peak_base_temperature"] - large["peak_base_temperature"]
    assert peak_diff > mean_diff


def test_spreading_thicker_base_reduces_delta() -> None:
    """Thicker base should reduce spreading delta (14.4)."""
    thin = solve_base_spreading_field(
        base_length=0.10, base_width=0.08, base_thickness=0.002,
        material_conductivity=201.0, ambient_temperature=25.0,
        sink_thermal_resistance=2.0,
        sources=[{
            "id": "s", "x_center": 0.05, "y_center": 0.04,
            "length": 0.015, "width": 0.015, "power": 10.0,
            "junction_to_case_resistance": 0.0, "interface_resistance": 0.0,
        }],
    )
    thick = solve_base_spreading_field(
        base_length=0.10, base_width=0.08, base_thickness=0.010,
        material_conductivity=201.0, ambient_temperature=25.0,
        sink_thermal_resistance=2.0,
        sources=[{
            "id": "s", "x_center": 0.05, "y_center": 0.04,
            "length": 0.015, "width": 0.015, "power": 10.0,
            "junction_to_case_resistance": 0.0, "interface_resistance": 0.0,
        }],
    )
    assert thick["max_spreading_delta"] < thin["max_spreading_delta"]


def test_spreading_energy_balance() -> None:
    """Total sink heat rejection should match source power (14.6)."""
    result = solve_base_spreading_field(
        **SPREADING_BASE,
        sources=[{
            "id": "s", "x_center": 0.05, "y_center": 0.04,
            "length": 0.02, "width": 0.02, "power": 15.0,
            "junction_to_case_resistance": 0.0, "interface_resistance": 0.0,
        }],
    )
    assert result["energy_balance_error"] < 0.01  # Within 1%


def test_spreading_convergence() -> None:
    """Nominal case should converge well before max iterations."""
    result = solve_base_spreading_field(
        **SPREADING_BASE,
        sources=[{
            "id": "s", "x_center": 0.05, "y_center": 0.04,
            "length": 0.02, "width": 0.02, "power": 10.0,
            "junction_to_case_resistance": 0.0, "interface_resistance": 0.0,
        }],
    )
    assert result["converged"]
    assert result["iterations"] < 4000


def test_spreading_orchestrator_returns_both() -> None:
    """The orchestrator should return both baseline and spreading data."""
    result = analyze_heatsink_spreading_view(
        heat_load=15.0, ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10, base_width=0.08, base_thickness=0.005,
        fin_height=0.03, fin_thickness=0.001, fin_count=10,
        material_conductivity=201.0,
        source_length=0.02, source_width=0.02,
        interface_resistance=0.20,
        junction_to_case_resistance=0.50,
    )
    assert result["baseline"] is not None
    assert result["spreading"] is not None
    assert result["spreading_error"] is None
    assert result["spreading"]["converged"]
    assert len(result["spreading"]["source_summaries"]) == 1
    ss = result["spreading"]["source_summaries"][0]
    assert ss["avg_junction_temperature"] > ss["avg_base_temperature"]
    assert ss["peak_junction_temperature_estimate"] >= ss["avg_junction_temperature"]


def test_spreading_off_center_source_shifts_hotspot() -> None:
    """An off-center source should produce an asymmetric field."""
    common = dict(
        **SPREADING_BASE,
        sources=[{
            "id": "off_center",
            "x_center": 0.02,
            "y_center": 0.04,
            "length": 0.02,
            "width": 0.02,
            "power": 15.0,
            "junction_to_case_resistance": 0.0,
            "interface_resistance": 0.0,
        }],
    )
    result = solve_base_spreading_field(**common)
    grid = result["temperature_grid"]
    nx = len(result["x_coords"])
    ny = len(result["y_coords"])
    # Peak should be in the left quarter (low x indices)
    peak_i, peak_j = 0, 0
    peak_t = grid[0][0]
    for i in range(nx):
        for j in range(ny):
            if grid[i][j] > peak_t:
                peak_t = grid[i][j]
                peak_i = i
                peak_j = j
    # Source is at x=0.02 out of 0.10, so peak should be in the first ~30% of x
    assert peak_i < nx * 0.35, f"Peak at i={peak_i}, expected in first 35% of {nx}"


# --- Bug fix tests ---


def test_clipped_source_energy_balance() -> None:
    """Clipped source should deposit less power and maintain energy balance (Fix 1)."""
    result = solve_base_spreading_field(
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        material_conductivity=201.0,
        ambient_temperature=25.0,
        sink_thermal_resistance=2.0,
        sources=[{
            "id": "clipped",
            "x_center": 0.0,  # half the source hangs off the left edge
            "y_center": 0.04,
            "length": 0.04,
            "width": 0.04,
            "power": 20.0,
            "junction_to_case_resistance": 0.5,
            "interface_resistance": 0.2,
        }],
    )
    assert result["converged"]
    assert result["energy_balance_error"] < 0.02  # Within 2%
    ss = result["source_summaries"][0]
    # Effective power should be less than the raw 20W (half clipped)
    assert ss["power"] < 20.0
    assert ss["power"] == pytest.approx(10.0, rel=0.01)


def test_centerline_cuts_through_source_center() -> None:
    """Off-center source should shift centerline cuts to source center (Fix 2)."""
    result = solve_base_spreading_field(
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        material_conductivity=201.0,
        ambient_temperature=25.0,
        sink_thermal_resistance=2.0,
        sources=[{
            "id": "off",
            "x_center": 0.02,
            "y_center": 0.02,
            "length": 0.01,
            "width": 0.01,
            "power": 10.0,
            "junction_to_case_resistance": 0.0,
            "interface_resistance": 0.0,
        }],
    )
    # Centerline cut coordinates should be near the source center, not geometric center
    cut_y = result["centerline_x"]["cut_y"]
    cut_x = result["centerline_y"]["cut_x"]
    dx = 0.10 / 41  # default grid_x
    dy = 0.08 / 25  # default grid_y
    assert abs(cut_y - 0.02) < dy, f"cut_y={cut_y}, expected near 0.02"
    assert abs(cut_x - 0.02) < dx, f"cut_x={cut_x}, expected near 0.02"
    # Peak on x-centerline should be near the source
    x_temps = result["centerline_x"]["temperature"]
    peak_idx = x_temps.index(max(x_temps))
    peak_x = result["centerline_x"]["coords"][peak_idx]
    assert peak_x < 0.04, f"Peak at x={peak_x}, expected near source at x=0.02"


def test_spreading_view_skips_baseline_when_r_sink_provided() -> None:
    """Providing sink_thermal_resistance should skip the baseline solver (Fix 3)."""
    result = analyze_heatsink_spreading_view(
        heat_load=15.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
        source_length=0.02,
        source_width=0.02,
        sink_thermal_resistance=2.0,
    )
    assert result["baseline"] is None
    assert result["spreading"] is not None
    assert result["spreading"]["converged"]
    assert result["spreading_error"] is None


def test_off_center_source_adds_assumption_to_baseline() -> None:
    """Off-center source should append an assumption note to the baseline (Fix 4)."""
    result = analyze_heatsink_spreading_view(
        heat_load=15.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
        source_length=0.02,
        source_width=0.02,
        source_x=0.02,
        source_y=0.02,
    )
    assert result["baseline"] is not None
    assumptions_text = " ".join(result["baseline"].get("assumptions", []))
    assert "centered-source" in assumptions_text
