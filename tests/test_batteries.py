import math

import pytest

from pycalcs import batteries


# ─────────────────────────────────────────────────────────────────────────────
# Constant current mode tests
# ─────────────────────────────────────────────────────────────────────────────


def test_runtime_constant_current_nominal() -> None:
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )

    assert math.isclose(results["runtime_hours"], 5.0, rel_tol=1e-6)
    assert math.isclose(results["runtime_minutes"], 300.0, rel_tol=1e-6)
    assert math.isclose(results["average_current_a"], 2.0, rel_tol=1e-6)
    assert math.isclose(results["average_power_w"], 24.0, rel_tol=1e-6)
    assert math.isclose(results["energy_delivered_wh"], 120.0, rel_tol=1e-6)


def test_runtime_with_peukert_effect() -> None:
    """Peukert: C_eff = C * (I_ref/I)^(k-1) with k=1.2, I_ref=5 A, I=20 A."""
    results = batteries.estimate_battery_runtime(
        chemistry="lead_acid",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=100.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_current",
        load_current_a=20.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.2,
        reference_current_a=5.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )

    expected_capacity = 100.0 * (5.0 / 20.0) ** 0.2
    expected_runtime = expected_capacity / 20.0
    expected_energy = 12.0 * expected_capacity

    assert math.isclose(results["effective_capacity_ah"], expected_capacity, rel_tol=1e-6)
    assert math.isclose(results["runtime_hours"], expected_runtime, rel_tol=1e-6)
    assert math.isclose(results["energy_delivered_wh"], expected_energy, rel_tol=1e-6)


def test_runtime_constant_current_with_converter_efficiency() -> None:
    """Converter efficiency 80%: battery current = load current / 0.8."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=0.8,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # Battery current = 2.0 / 0.8 = 2.5 A, runtime = 10 / 2.5 = 4 h
    assert math.isclose(results["average_current_a"], 2.5, rel_tol=1e-6)
    assert math.isclose(results["runtime_hours"], 4.0, rel_tol=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# Constant power mode tests
# ─────────────────────────────────────────────────────────────────────────────


def test_runtime_constant_power_no_resistance() -> None:
    """Constant power mode with zero internal resistance."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_power",
        load_current_a=0.0,
        load_power_w=24.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # I = P / V = 24 / 12 = 2 A, runtime = 10 / 2 = 5 h
    assert math.isclose(results["average_current_a"], 2.0, rel_tol=1e-6)
    assert math.isclose(results["runtime_hours"], 5.0, rel_tol=1e-6)


def test_runtime_constant_power_with_resistance() -> None:
    """Constant power mode with internal resistance uses quadratic solution."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.1,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_power",
        load_current_a=0.0,
        load_power_w=24.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # Quadratic: I = (V - sqrt(V^2 - 4*R*P)) / (2*R)
    discriminant = 12.0**2 - 4 * 0.1 * 24.0
    expected_current = (12.0 - math.sqrt(discriminant)) / (2 * 0.1)
    assert math.isclose(results["average_current_a"], expected_current, rel_tol=1e-6)
    # Verify voltage sag is calculated
    assert results["voltage_sag_v"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Constant resistance mode tests
# ─────────────────────────────────────────────────────────────────────────────


def test_runtime_constant_resistance() -> None:
    """Constant resistance mode: I = V / (R_load + R_pack)."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_resistance",
        load_current_a=0.0,
        load_power_w=0.0,
        load_resistance_ohm=6.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # I = 12 / 6 = 2 A, runtime = 10 / 2 = 5 h
    assert math.isclose(results["average_current_a"], 2.0, rel_tol=1e-6)
    assert math.isclose(results["runtime_hours"], 5.0, rel_tol=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# Cell specs mode tests
# ─────────────────────────────────────────────────────────────────────────────


def test_runtime_cell_specs_mode() -> None:
    """Pack parameters derived from cell specs (4S2P configuration)."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=1,
        series_cells=4,
        parallel_cells=2,
        cell_nominal_voltage_v=3.7,
        cell_capacity_ah=3.0,
        cell_internal_resistance_ohm=0.05,
        cell_cutoff_voltage_v=3.0,
        pack_nominal_voltage_v=0.0,  # ignored when use_cell_specs=1
        pack_capacity_ah=0.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=0.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # 4S: V = 4 * 3.7 = 14.8 V
    # 2P: C = 2 * 3.0 = 6.0 Ah
    # R_pack = (4/2) * 0.05 = 0.1 ohm
    assert math.isclose(results["pack_nominal_voltage_v"], 14.8, rel_tol=1e-6)
    assert math.isclose(results["pack_capacity_ah"], 6.0, rel_tol=1e-6)
    assert math.isclose(results["pack_internal_resistance_ohm"], 0.1, rel_tol=1e-6)
    # Runtime = 6 / 2 = 3 h
    assert math.isclose(results["runtime_hours"], 3.0, rel_tol=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# Temperature, SOH, and DOD effects
# ─────────────────────────────────────────────────────────────────────────────


def test_runtime_temperature_effect() -> None:
    """Cold temperature reduces capacity."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=0.0,  # 25C below reference
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.01,  # 1% per degree
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # temp_factor = 1 + 0.01 * (0 - 25) = 0.75
    # effective_capacity = 10 * 0.75 = 7.5 Ah
    # runtime = 7.5 / 2 = 3.75 h
    assert math.isclose(results["effective_capacity_ah"], 7.5, rel_tol=1e-6)
    assert math.isclose(results["runtime_hours"], 3.75, rel_tol=1e-6)


def test_runtime_soh_effect() -> None:
    """State of health reduces usable capacity."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=0.8,  # 80% SOH
    )
    # effective_capacity = 10 * 0.8 = 8 Ah
    # runtime = 8 / 2 = 4 h
    assert math.isclose(results["effective_capacity_ah"], 8.0, rel_tol=1e-6)
    assert math.isclose(results["runtime_hours"], 4.0, rel_tol=1e-6)


def test_runtime_dod_effect() -> None:
    """Depth of discharge limits usable capacity."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=0.5,  # Only use 50%
        state_of_health=1.0,
    )
    # effective_capacity = 10 * 0.5 = 5 Ah
    # runtime = 5 / 2 = 2.5 h
    assert math.isclose(results["effective_capacity_ah"], 5.0, rel_tol=1e-6)
    assert math.isclose(results["runtime_hours"], 2.5, rel_tol=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# Duty cycle tests
# ─────────────────────────────────────────────────────────────────────────────


def test_runtime_duty_cycle() -> None:
    """Duty cycle extends runtime by reducing average current."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=0.5,  # 50% duty cycle
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # I_avg = 2 * 0.5 = 1 A
    # runtime = 10 / 1 = 10 h
    assert math.isclose(results["average_current_a"], 1.0, rel_tol=1e-6)
    assert math.isclose(results["runtime_hours"], 10.0, rel_tol=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# Internal resistance and voltage sag tests
# ─────────────────────────────────────────────────────────────────────────────


def test_voltage_sag_calculation() -> None:
    """Verify voltage sag = I * R_pack."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.5,
        pack_cutoff_voltage_v=9.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # V_sag = 2 * 0.5 = 1 V
    # V_load = 12 - 1 = 11 V
    assert math.isclose(results["voltage_sag_v"], 1.0, rel_tol=1e-6)
    assert math.isclose(results["loaded_voltage_v"], 11.0, rel_tol=1e-6)


def test_power_loss_calculation() -> None:
    """Verify power loss = I^2 * R."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.5,
        pack_cutoff_voltage_v=9.0,
        load_type="constant_current",
        load_current_a=2.0,
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # P_loss = 2^2 * 0.5 = 2 W
    assert math.isclose(results["power_loss_w"], 2.0, rel_tol=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# C-rate calculation tests
# ─────────────────────────────────────────────────────────────────────────────


def test_c_rate_calculation() -> None:
    """Verify C-rate = I_avg / C_pack."""
    results = batteries.estimate_battery_runtime(
        chemistry="li_ion_nmc",
        use_cell_specs=0,
        series_cells=0,
        parallel_cells=0,
        cell_nominal_voltage_v=0,
        cell_capacity_ah=0,
        cell_internal_resistance_ohm=0,
        cell_cutoff_voltage_v=0,
        pack_nominal_voltage_v=12.0,
        pack_capacity_ah=10.0,
        pack_internal_resistance_ohm=0.0,
        pack_cutoff_voltage_v=10.0,
        load_type="constant_current",
        load_current_a=5.0,  # 0.5C for 10 Ah pack
        load_power_w=0.0,
        load_resistance_ohm=0.0,
        converter_efficiency=1.0,
        duty_cycle=1.0,
        peukert_exponent=1.0,
        reference_current_a=1.0,
        ambient_temperature_c=25.0,
        reference_temperature_c=25.0,
        capacity_temp_coeff_per_c=0.0,
        depth_of_discharge=1.0,
        state_of_health=1.0,
    )
    # C-rate = 5 / 10 = 0.5
    assert math.isclose(results["c_rate"], 0.5, rel_tol=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# Validation error tests
# ─────────────────────────────────────────────────────────────────────────────


def test_invalid_load_type_raises() -> None:
    """Invalid load type should raise ValueError."""
    with pytest.raises(ValueError, match="load_type"):
        batteries.estimate_battery_runtime(
            chemistry="li_ion_nmc",
            use_cell_specs=0,
            series_cells=0,
            parallel_cells=0,
            cell_nominal_voltage_v=0,
            cell_capacity_ah=0,
            cell_internal_resistance_ohm=0,
            cell_cutoff_voltage_v=0,
            pack_nominal_voltage_v=12.0,
            pack_capacity_ah=10.0,
            pack_internal_resistance_ohm=0.0,
            pack_cutoff_voltage_v=10.0,
            load_type="invalid_type",
            load_current_a=2.0,
            load_power_w=0.0,
            load_resistance_ohm=0.0,
            converter_efficiency=1.0,
            duty_cycle=1.0,
            peukert_exponent=1.0,
            reference_current_a=1.0,
            ambient_temperature_c=25.0,
            reference_temperature_c=25.0,
            capacity_temp_coeff_per_c=0.0,
            depth_of_discharge=1.0,
            state_of_health=1.0,
        )


def test_zero_capacity_raises() -> None:
    """Zero pack capacity should raise ValueError."""
    with pytest.raises(ValueError, match="pack_capacity"):
        batteries.estimate_battery_runtime(
            chemistry="li_ion_nmc",
            use_cell_specs=0,
            series_cells=0,
            parallel_cells=0,
            cell_nominal_voltage_v=0,
            cell_capacity_ah=0,
            cell_internal_resistance_ohm=0,
            cell_cutoff_voltage_v=0,
            pack_nominal_voltage_v=12.0,
            pack_capacity_ah=0.0,
            pack_internal_resistance_ohm=0.0,
            pack_cutoff_voltage_v=10.0,
            load_type="constant_current",
            load_current_a=2.0,
            load_power_w=0.0,
            load_resistance_ohm=0.0,
            converter_efficiency=1.0,
            duty_cycle=1.0,
            peukert_exponent=1.0,
            reference_current_a=1.0,
            ambient_temperature_c=25.0,
            reference_temperature_c=25.0,
            capacity_temp_coeff_per_c=0.0,
            depth_of_discharge=1.0,
            state_of_health=1.0,
        )


def test_invalid_efficiency_raises() -> None:
    """Converter efficiency outside (0, 1] should raise ValueError."""
    with pytest.raises(ValueError, match="converter_efficiency"):
        batteries.estimate_battery_runtime(
            chemistry="li_ion_nmc",
            use_cell_specs=0,
            series_cells=0,
            parallel_cells=0,
            cell_nominal_voltage_v=0,
            cell_capacity_ah=0,
            cell_internal_resistance_ohm=0,
            cell_cutoff_voltage_v=0,
            pack_nominal_voltage_v=12.0,
            pack_capacity_ah=10.0,
            pack_internal_resistance_ohm=0.0,
            pack_cutoff_voltage_v=10.0,
            load_type="constant_current",
            load_current_a=2.0,
            load_power_w=0.0,
            load_resistance_ohm=0.0,
            converter_efficiency=1.5,  # Invalid: > 1
            duty_cycle=1.0,
            peukert_exponent=1.0,
            reference_current_a=1.0,
            ambient_temperature_c=25.0,
            reference_temperature_c=25.0,
            capacity_temp_coeff_per_c=0.0,
            depth_of_discharge=1.0,
            state_of_health=1.0,
        )


def test_peukert_less_than_one_raises() -> None:
    """Peukert exponent < 1 should raise ValueError."""
    with pytest.raises(ValueError, match="peukert_exponent"):
        batteries.estimate_battery_runtime(
            chemistry="li_ion_nmc",
            use_cell_specs=0,
            series_cells=0,
            parallel_cells=0,
            cell_nominal_voltage_v=0,
            cell_capacity_ah=0,
            cell_internal_resistance_ohm=0,
            cell_cutoff_voltage_v=0,
            pack_nominal_voltage_v=12.0,
            pack_capacity_ah=10.0,
            pack_internal_resistance_ohm=0.0,
            pack_cutoff_voltage_v=10.0,
            load_type="constant_current",
            load_current_a=2.0,
            load_power_w=0.0,
            load_resistance_ohm=0.0,
            converter_efficiency=1.0,
            duty_cycle=1.0,
            peukert_exponent=0.9,  # Invalid: < 1
            reference_current_a=1.0,
            ambient_temperature_c=25.0,
            reference_temperature_c=25.0,
            capacity_temp_coeff_per_c=0.0,
            depth_of_discharge=1.0,
            state_of_health=1.0,
        )
