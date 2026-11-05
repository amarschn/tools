import pytest

from pycalcs.interference_fits import (
    analyze_interference_fit,
    get_interference_fit_material_presets,
    size_interference_fit,
)


def test_material_presets_include_expected_keys():
    presets = get_interference_fit_material_presets()
    assert "steel" in presets
    assert "aluminum" in presets
    assert presets["steel"]["youngs_modulus_mpa"] == pytest.approx(200000.0)
    assert presets["steel"]["density_kg_m3"] == pytest.approx(7850.0)


def test_material_presets_include_hardened_aisi_52100():
    preset = get_interference_fit_material_presets()["steel_52100_hardened"]

    assert preset["display_name"] == "AISI 52100 (Hardened 65-68 HRC)"
    assert preset["condition"] == "through hardened, 65-68 HRC"
    assert preset["youngs_modulus_mpa"] == pytest.approx(212000.0)
    assert preset["poisson_ratio"] == pytest.approx(0.30)
    assert preset["yield_strength_mpa"] == pytest.approx(1800.0)
    assert preset["thermal_expansion_e6_per_c"] == pytest.approx(12.0)
    assert preset["density_kg_m3"] == pytest.approx(7850.0)
    assert "ideal-tek" in preset["source"]


def test_sizing_solves_required_interference_from_torque():
    results = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        required_torque_nm=1000.0,
        shaft_material="steel",
        hub_material="steel",
        friction_coefficient=0.15,
        required_slip_sf=1.5,
        required_yield_sf=1.2,
    )

    expected_pressure_mpa = (
        2.0 * 1000.0 * 1.5
        / (0.15 * 3.141592653589793 * 0.05**2 * 0.075)
        / 1e6
    )
    expected_minimum_mm = (
        expected_pressure_mpa * results["compliance"]["total_term_mm_per_mpa"]
    )

    assert results["load_requirement"]["required_contact_pressure_mpa"] == pytest.approx(
        expected_pressure_mpa
    )
    assert results["design_range"]["required_minimum_mm"] == pytest.approx(
        expected_minimum_mm
    )
    assert results["design_range"]["allowable_maximum_mm"] == pytest.approx(
        0.0833333333, rel=1e-6
    )
    assert results["design_range"]["recommended_nominal_mm"] == pytest.approx(
        0.5 * (expected_minimum_mm + 0.0833333333), rel=1e-6
    )
    assert results["status"] == "acceptable"


def test_sizing_hot_aluminum_hub_increases_required_reference_interference():
    cold = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        required_torque_nm=1000.0,
        shaft_material="steel",
        hub_material="aluminum_6061_t6",
        minimum_operating_temperature_c=20.0,
        maximum_operating_temperature_c=20.0,
    )
    hot = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        required_torque_nm=1000.0,
        shaft_material="steel",
        hub_material="aluminum_6061_t6",
        minimum_operating_temperature_c=20.0,
        maximum_operating_temperature_c=120.0,
    )

    expected_relief_mm = 50.0 * (23.6 - 12.0) * 1e-6 * 100.0
    assert hot["design_range"]["required_minimum_mm"] == pytest.approx(
        cold["design_range"]["required_minimum_mm"] + expected_relief_mm
    )
    assert "120.0 deg C" in hot["design_range"]["governing_lower_label"]


def test_sizing_speed_accounts_for_centrifugal_fit_relief_and_stress():
    stationary = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        required_torque_nm=1000.0,
        maximum_speed_rpm=0.0,
    )
    rotating = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        required_torque_nm=1000.0,
        maximum_speed_rpm=20000.0,
    )

    rotating_state = next(
        state
        for state in rotating["service_states"]
        if state["speed_rpm"] == pytest.approx(20000.0)
    )
    assert rotating_state["speed_relief_mm"] > 0.0
    assert rotating_state["hub_bore_diametral_growth_mm"] > rotating_state[
        "shaft_diametral_growth_mm"
    ]
    assert rotating["design_range"]["required_minimum_mm"] > stationary[
        "design_range"
    ]["required_minimum_mm"]
    assert rotating["design_range"]["allowable_maximum_mm"] < stationary[
        "design_range"
    ]["allowable_maximum_mm"]


def test_sizing_combines_torque_and_axial_traction_vectorially():
    torque_only = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        required_torque_nm=1000.0,
    )
    combined = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        required_torque_nm=1000.0,
        applied_axial_force_n=40000.0,
    )

    tangential_force = torque_only["load_requirement"]["tangential_force_n"]
    expected_ratio = (tangential_force**2 + 40000.0**2) ** 0.5 / tangential_force
    assert combined["load_requirement"]["required_contact_pressure_mpa"] == pytest.approx(
        torque_only["load_requirement"]["required_contact_pressure_mpa"]
        * expected_ratio
    )


def test_sizing_reports_when_no_elastic_interference_window_exists():
    results = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=60.0,
        fit_length_mm=20.0,
        required_torque_nm=10000.0,
    )

    assert results["status"] == "unacceptable"
    assert results["design_range"]["feasible"] is False
    assert results["design_range"]["recommended_nominal_mm"] is None
    assert results["design_range"]["required_minimum_mm"] > results[
        "design_range"
    ]["allowable_maximum_mm"]


def test_sizing_rejects_reversed_temperature_envelope():
    with pytest.raises(ValueError, match="minimum_operating_temperature_c"):
        size_interference_fit(
            shaft_outer_diameter_mm=50.0,
            hub_outer_diameter_mm=100.0,
            fit_length_mm=75.0,
            required_torque_nm=1000.0,
            minimum_operating_temperature_c=100.0,
            maximum_operating_temperature_c=20.0,
        )


def test_nominal_same_material_case_matches_legacy_baseline():
    results = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.05,
        interference_nominal_mm=0.05,
        interference_max_mm=0.05,
        shaft_material="steel",
        hub_material="steel",
        friction_coefficient=0.15,
        reference_temperature_c=20.0,
        operating_temperature_c=20.0,
        assembly_clearance_mm=0.01,
    )

    reference_case = results["reference_case"]
    operating_case = results["operating_case"]
    assembly = results["assembly"]

    assert reference_case["pressure_mpa"] == pytest.approx(75.0, abs=1.0)
    assert reference_case["hub_hoop_stress_mpa"] == pytest.approx(125.0, abs=1.0)
    assert reference_case["hub_radial_stress_mpa"] == pytest.approx(-75.0, abs=1.0)
    assert reference_case["hub_von_mises_mpa"] == pytest.approx(175.0, abs=1.0)
    assert reference_case["shaft_hoop_stress_mpa"] == pytest.approx(-75.0, abs=1.0)
    assert reference_case["shaft_radial_stress_mpa"] == pytest.approx(-75.0, abs=1.0)
    assert reference_case["shaft_von_mises_mpa"] == pytest.approx(75.0, abs=1.0)
    assert operating_case["torque_capacity_nm"] == pytest.approx(3298.7, abs=20.0)
    assert operating_case["axial_capacity_kn"] == pytest.approx(131.9, abs=1.0)
    assert assembly["hub_heating_temperature_c"] == pytest.approx(120.0, abs=1.0)
    assert assembly["shaft_cooling_temperature_c"] == pytest.approx(-80.0, abs=1.0)


def test_hollow_shaft_reduces_pressure():
    solid = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.05,
        interference_nominal_mm=0.05,
        interference_max_mm=0.05,
        shaft_material="steel",
        hub_material="steel",
    )
    hollow = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=25.0,
        interference_min_mm=0.05,
        interference_nominal_mm=0.05,
        interference_max_mm=0.05,
        shaft_material="steel",
        hub_material="steel",
    )

    assert hollow["reference_case"]["pressure_mpa"] < solid["reference_case"]["pressure_mpa"]
    assert hollow["reference_case"]["pressure_mpa"] > 0.0


def test_same_material_temperature_change_preserves_pressure():
    results = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.05,
        interference_nominal_mm=0.05,
        interference_max_mm=0.05,
        shaft_material="steel",
        hub_material="steel",
        reference_temperature_c=20.0,
        operating_temperature_c=100.0,
    )

    assert results["reference_case"]["pressure_mpa"] == pytest.approx(
        results["operating_case"]["pressure_mpa"], abs=0.05
    )


def test_mixed_material_heating_reduces_pressure_and_can_lose_fit():
    reduced = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.05,
        interference_nominal_mm=0.05,
        interference_max_mm=0.05,
        shaft_material="steel",
        hub_material="aluminum",
        reference_temperature_c=20.0,
        operating_temperature_c=100.0,
    )
    lost = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.05,
        interference_nominal_mm=0.05,
        interference_max_mm=0.05,
        shaft_material="steel",
        hub_material="aluminum",
        reference_temperature_c=20.0,
        operating_temperature_c=130.0,
    )

    assert reduced["operating_case"]["pressure_mpa"] < reduced["reference_case"]["pressure_mpa"]
    assert reduced["operating_case"]["pressure_mpa"] > 0.0
    assert lost["operating_case"]["pressure_mpa"] == pytest.approx(0.0, abs=1e-9)
    assert lost["minimum_case"]["operating"]["fit_retained"] is False
    assert lost["status"] == "unacceptable"


def test_min_nom_max_ordering():
    results = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.03,
        interference_nominal_mm=0.05,
        interference_max_mm=0.07,
        shaft_material="steel",
        hub_material="steel",
        applied_torque_nm=1000.0,
    )

    assert results["minimum_case"]["reference"]["pressure_mpa"] < results["nominal_case"]["reference"]["pressure_mpa"]
    assert results["nominal_case"]["reference"]["pressure_mpa"] < results["maximum_case"]["reference"]["pressure_mpa"]
    assert results["minimum_case"]["operating"]["torque_capacity_nm"] < results["nominal_case"]["operating"]["torque_capacity_nm"]
    assert results["nominal_case"]["operating"]["torque_capacity_nm"] < results["maximum_case"]["operating"]["torque_capacity_nm"]
    assert results["minimum_operating_pressure_mpa"] == pytest.approx(
        results["minimum_case"]["operating"]["pressure_mpa"]
    )
    assert results["maximum_reference_pressure_mpa"] == pytest.approx(
        results["maximum_case"]["reference"]["pressure_mpa"]
    )


def test_sweep_outputs_have_expected_shapes():
    results = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.03,
        interference_nominal_mm=0.05,
        interference_max_mm=0.07,
        shaft_material="steel",
        hub_material="aluminum",
        reference_temperature_c=20.0,
        operating_temperature_c=100.0,
        n_sweep_points=21,
    )

    sweep = results["sweep_data"]
    temp_effect = sweep["temperature_effect"]
    assert len(sweep["interference_mm"]) == 21
    assert len(sweep["reference_pressure_mpa"]) == 21
    assert len(sweep["operating_pressure_mpa"]) == 21
    assert len(temp_effect["temperature_c"]) == 61
    assert len(temp_effect["operating_pressure_mpa"]) == 61


def test_returns_compliance_and_assembly_plan_metadata():
    results = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.04,
        interference_nominal_mm=0.05,
        interference_max_mm=0.06,
        shaft_material="steel",
        hub_material="aluminum_6061_t6",
        reference_temperature_c=20.0,
        operating_temperature_c=80.0,
        assembly_clearance_mm=0.01,
    )

    assert results["compliance"]["hub_coefficient"] > 0.0
    assert results["compliance"]["shaft_coefficient"] > 0.0
    assert results["compliance"]["total_term_mm_per_mpa"] > 0.0

    # The plan opens the maximum interference plus the slip clearance.
    assembly = results["assembly"]
    assert assembly["governing_interference_mm"] == pytest.approx(0.06)
    assert assembly["slip_clearance_mm"] == pytest.approx(0.01)
    assert assembly["required_total_diameter_change_mm"] == pytest.approx(0.07)
    assert assembly["recommended_route"]

    # Only reference and operating states exist; there is no separate
    # same-temperature "assembly" state, which only ever duplicated one of them.
    assert set(results["range_cases"]["nominal"]) == {"reference", "operating"}
    assert set(results["state_temperatures_c"]) == {"reference", "operating"}
    assert "assembly_case" not in results


def test_hollow_shaft_surface_results_include_bore_data():
    results = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=30.0,
        interference_min_mm=0.05,
        interference_nominal_mm=0.05,
        interference_max_mm=0.05,
        shaft_material="steel_4140_qt",
        hub_material="steel",
    )

    shaft_reference = results["reference_case"]["members"]["shaft"]
    assert shaft_reference["member_type"] == "hollow"
    assert shaft_reference["surfaces"]["inner_surface"] is not None
    assert results["reference_case"]["shaft_inner_hoop_stress_mpa"] < 0.0
    assert len(results["stress_distribution_cases"]["reference"]["shaft"]["radii_mm"]) > 0


def test_invalid_geometry_raises():
    with pytest.raises(ValueError):
        analyze_interference_fit(
            shaft_outer_diameter_mm=50.0,
            hub_outer_diameter_mm=40.0,
            fit_length_mm=75.0,
            shaft_inner_diameter_mm=0.0,
            interference_nominal_mm=0.05,
        )


def test_zero_interference_returns_zero_pressure():
    results = analyze_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=100.0,
        fit_length_mm=75.0,
        shaft_inner_diameter_mm=0.0,
        interference_min_mm=0.0,
        interference_nominal_mm=0.0,
        interference_max_mm=0.0,
        shaft_material="steel",
        hub_material="steel",
    )

    assert results["reference_case"]["pressure_mpa"] == pytest.approx(0.0, abs=1e-12)
    assert results["operating_case"]["pressure_mpa"] == pytest.approx(0.0, abs=1e-12)
    assert results["status"] == "unacceptable"
