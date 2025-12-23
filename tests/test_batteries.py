import math

from pycalcs import batteries


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
