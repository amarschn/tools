"""Tests for the heatsink analysis module."""

from __future__ import annotations

import math

import pytest

from pycalcs.heatsinks import (
    air_properties,
    analyze_plate_fin_heatsink,
    calculate_plate_fin_geometry,
    forced_convection_plate_array,
    natural_convection_plate_array,
    rectangular_fin_efficiency,
    required_sink_thermal_resistance,
    solve_fan_operating_point,
)


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
    assert result["convection_mode_used"] == "natural"
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
