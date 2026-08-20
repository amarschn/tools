"""Regression tests for the interference-fit audit fixes.

Each test here pins a defect found in the 2026-08-14 audit of the ring-fit
tool. See plans/2026-08-14_ring_fit_audit_remediation.md.
"""

import math

import pytest

from pycalcs.interference_fits import (
    BRITTLE,
    VON_MISES,
    _classify_manufacturing_window,
    _iso286_tolerance_unit_um,
    _smoothing_loss_mm,
    _strength_safety_factor,
    analyze_interference_fit,
    get_interference_fit_friction_presets,
    get_interference_fit_material_presets,
    get_interference_fit_roughness_presets,
    size_interference_fit,
)


SIZE_BASE = dict(
    shaft_outer_diameter_mm=50.0,
    hub_outer_diameter_mm=100.0,
    fit_length_mm=75.0,
    required_torque_nm=1000.0,
)
CHECK_BASE = dict(
    shaft_outer_diameter_mm=50.0,
    hub_outer_diameter_mm=100.0,
    fit_length_mm=75.0,
    interference_min_mm=0.045,
    interference_nominal_mm=0.06,
    interference_max_mm=0.075,
    applied_torque_nm=1000.0,
)


# --- Non-finite inputs -----------------------------------------------------

@pytest.mark.parametrize(
    "field",
    [
        "shaft_outer_diameter_mm",
        "hub_outer_diameter_mm",
        "fit_length_mm",
        "minimum_operating_temperature_c",
        "maximum_operating_temperature_c",
        "reference_temperature_c",
        "shaft_roughness_rz_um",
    ],
)
@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_sizing_rejects_non_finite_inputs(field, bad):
    """NaN compares False against every ordering check, so it must be screened."""
    args = {**SIZE_BASE, field: bad}
    with pytest.raises(ValueError, match="finite"):
        size_interference_fit(**args)


def test_checker_rejects_non_finite_inputs():
    with pytest.raises(ValueError, match="finite"):
        analyze_interference_fit(**{**CHECK_BASE, "operating_temperature_c": float("nan")})


# --- Torque or axial duty --------------------------------------------------

def test_sizing_accepts_axial_only_duty():
    """Thrust-only retention is a real design and used to be rejected."""
    results = size_interference_fit(
        **{**SIZE_BASE, "required_torque_nm": 0.0, "applied_axial_force_n": 50000.0}
    )
    assert results["design_range"]["required_minimum_mm"] > 0.0
    assert results["load_requirement"]["tangential_force_n"] == pytest.approx(0.0)
    assert results["load_requirement"]["equivalent_force_n"] == pytest.approx(50000.0)


def test_sizing_rejects_a_joint_with_no_duty():
    with pytest.raises(ValueError, match="required_torque_nm or applied_axial_force_n"):
        size_interference_fit(**{**SIZE_BASE, "required_torque_nm": 0.0})


# --- Vectorial slip in the checker -----------------------------------------

def test_checker_combines_torque_and_axial_vectorially():
    """Both loads draw on one friction budget, so the resultant governs."""
    results = analyze_interference_fit(
        **{**CHECK_BASE, "applied_axial_force_n": 20000.0}
    )
    operating = results["nominal_case"]["operating"]
    tangential = 2.0 * 1000.0 / 0.050
    expected = math.hypot(tangential, 20000.0)
    assert operating["equivalent_force_n"] == pytest.approx(expected)

    combined = operating["combined_slip_safety_factor"]
    assert combined < operating["torque_slip_safety_factor"]
    assert combined < operating["axial_slip_safety_factor"]
    capacity = operating["axial_capacity_n"]
    assert combined == pytest.approx(capacity / expected)


# --- Surface roughness smoothing -------------------------------------------

def test_smoothing_loss_follows_din_7190():
    assert _smoothing_loss_mm(4.0, 4.0) == pytest.approx(0.8 * 8.0 * 1e-3)
    assert _smoothing_loss_mm(0.0, 0.0) == 0.0


def test_roughness_raises_both_interference_limits_equally():
    """Smoothing shifts the whole window up; it does not narrow it."""
    smooth = size_interference_fit(**SIZE_BASE)
    rough = size_interference_fit(
        **{**SIZE_BASE, "shaft_roughness_rz_um": 4.0, "hub_roughness_rz_um": 4.0}
    )
    loss = _smoothing_loss_mm(4.0, 4.0)
    assert rough["design_range"]["required_minimum_mm"] == pytest.approx(
        smooth["design_range"]["required_minimum_mm"] + loss
    )
    assert rough["design_range"]["allowable_maximum_mm"] == pytest.approx(
        smooth["design_range"]["allowable_maximum_mm"] + loss
    )
    assert rough["smoothing"]["smoothing_loss_um"] == pytest.approx(6.4)


def test_checker_roughness_reduces_effective_interference():
    results = analyze_interference_fit(
        **{**CHECK_BASE, "shaft_roughness_rz_um": 4.0, "hub_roughness_rz_um": 4.0}
    )
    reference = results["nominal_case"]["reference"]
    assert reference["effective_interference_mm"] == pytest.approx(0.06 - 0.0064)
    bare = analyze_interference_fit(**CHECK_BASE)
    assert reference["pressure_mpa"] < bare["nominal_case"]["reference"]["pressure_mpa"]


# --- Length credit cap -----------------------------------------------------

def test_length_credit_caps_torque_capacity():
    """An absurdly long fit used to need almost no interference at all."""
    short = size_interference_fit(**{**SIZE_BASE, "fit_length_mm": 75.0})
    long = size_interference_fit(**{**SIZE_BASE, "fit_length_mm": 500.0})
    assert long["geometry"]["effective_fit_length_mm"] == pytest.approx(75.0)
    assert long["design_range"]["required_minimum_mm"] == pytest.approx(
        short["design_range"]["required_minimum_mm"]
    )
    assert any("credited" in w for w in long["warnings"])


def test_length_credit_can_be_disabled():
    uncapped = size_interference_fit(
        **{**SIZE_BASE, "fit_length_mm": 500.0, "length_credit_ratio": 0.0}
    )
    assert uncapped["geometry"]["effective_fit_length_mm"] == pytest.approx(500.0)


# --- Brittle failure criterion ---------------------------------------------

def test_gray_iron_uses_coulomb_mohr():
    presets = get_interference_fit_material_presets()
    gray = presets["cast_iron_gray"]
    assert gray["failure_criterion"] == BRITTLE
    assert gray["compressive_strength_mpa"] > 3.0 * gray["tensile_strength_mpa"]

    # Hub bore: tensile hoop over radial compression.
    equivalent, factor = _strength_safety_factor(-100.0, 166.67, gray)
    demand = 166.67 / gray["tensile_strength_mpa"] + 100.0 / gray["compressive_strength_mpa"]
    assert factor == pytest.approx(1.0 / demand)

    # Pure compression is cheap for a brittle material and expensive for
    # von Mises, which is the whole reason the criterion matters.
    _, brittle_factor = _strength_safety_factor(-100.0, -100.0, gray)
    _, ductile_factor = _strength_safety_factor(-100.0, -100.0, presets["steel_1045_annealed"])
    assert brittle_factor > 2.0 * ductile_factor


def test_ductile_criterion_still_matches_von_mises():
    steel = get_interference_fit_material_presets()["steel"]
    equivalent, factor = _strength_safety_factor(-75.0, 125.0, steel)
    expected = math.sqrt(125.0**2 - 125.0 * -75.0 + 75.0**2)
    assert equivalent == pytest.approx(expected)
    assert factor == pytest.approx(350.0 / expected)


def test_brittle_members_raise_a_criterion_warning():
    results = size_interference_fit(**{**SIZE_BASE, "hub_material": "cast_iron_gray"})
    assert any("Coulomb-Mohr" in w for w in results["warnings"])


# --- Assembly temperature practicality -------------------------------------

def test_assembly_never_reports_a_temperature_below_absolute_zero():
    """This case used to print 'Shaft cooling only: -283 C' next to 'acceptable'."""
    results = size_interference_fit(
        shaft_outer_diameter_mm=20.0,
        hub_outer_diameter_mm=200.0,
        fit_length_mm=60.0,
        required_torque_nm=800.0,
        shaft_material="steel_4140_qt",
        hub_material="steel_4140_qt",
    )
    assembly = results["assembly"]
    assert assembly["shaft_cooling_feasible"] is False
    assert "impossible" in assembly["shaft_cooling_route"]
    assert results["status"] != "acceptable"
    assert any("thermal assembly route" in w for w in results["warnings"])


def test_ordinary_shrink_fit_reports_a_practical_route():
    results = size_interference_fit(**SIZE_BASE)
    assembly = results["assembly"]
    assert assembly["hub_heating_feasible"] is True
    assert assembly["hub_heating_route"] in ("oven or induction", "no heating needed")


def test_hub_assembly_target_below_service_temperature_warns():
    """An aluminum hub only needs 164 C to slip on, well inside a 200 C duty."""
    results = size_interference_fit(
        **{
            **SIZE_BASE,
            "hub_material": "aluminum_6061_t6",
            "maximum_operating_temperature_c": 200.0,
        }
    )
    assert results["assembly"]["hub_heating_temperature_c"] < 200.0
    assert any("thermal gradient" in w for w in results["warnings"])


def test_no_gradient_warning_when_assembly_is_hotter_than_service():
    results = size_interference_fit(
        **{
            **SIZE_BASE,
            "hub_material": "aluminum_6061_t6",
            "maximum_operating_temperature_c": 150.0,
        }
    )
    assert results["assembly"]["hub_heating_temperature_c"] > 150.0
    assert not any("thermal gradient" in w for w in results["warnings"])


# --- Assembly plan: temperature is an output, capability is the input ------

def test_assembly_plan_opens_maximum_interference_plus_slip_clearance():
    results = size_interference_fit(**{**SIZE_BASE, "assembly_clearance_mm": 0.02})
    assembly = results["assembly"]
    assert assembly["slip_clearance_mm"] == pytest.approx(0.02)
    assert assembly["required_total_diameter_change_mm"] == pytest.approx(
        results["design_range"]["allowable_maximum_mm"] + 0.02
    )
    # Hub growth over that temperature rise equals the opening required.
    alpha = results["materials"]["hub"]["thermal_expansion_e6_per_c"] * 1e-6
    rise = assembly["hub_heating_temperature_c"] - 20.0
    assert 50.0 * alpha * rise == pytest.approx(
        assembly["required_total_diameter_change_mm"]
    )


def test_assembly_recommends_the_cheapest_workable_route():
    """Heating alone is cheapest, so it wins whenever the shop can do it."""
    free = size_interference_fit(**SIZE_BASE)
    assert free["assembly"]["recommended_route"] == "heat the hub"

    capped = size_interference_fit(**{**SIZE_BASE, "hub_max_assembly_temp_c": 120.0})
    assert capped["assembly"]["hub_heating_feasible"] is False
    assert capped["assembly"]["recommended_route"] == "chill the shaft"
    assert any("above the 120 deg C limit" in w for w in capped["warnings"])

    both = size_interference_fit(
        **{
            **SIZE_BASE,
            "hub_max_assembly_temp_c": 120.0,
            "shaft_min_assembly_temp_c": -78.0,
        }
    )
    assert both["assembly"]["recommended_route"] == "heat the hub and chill the shaft"
    assert both["assembly"]["combined_route_feasible"] is True


def test_impossible_equipment_limits_fall_back_to_pressing_cold():
    results = size_interference_fit(
        **{
            **SIZE_BASE,
            "hub_max_assembly_temp_c": 30.0,
            "shaft_min_assembly_temp_c": -10.0,
        }
    )
    assembly = results["assembly"]
    assert assembly["recommended_route"] == "press cold, no thermal route works"
    assert assembly["combined_route_feasible"] is False
    assert any("No thermal assembly route" in w for w in results["warnings"])


def test_both_modes_return_the_same_assembly_contract():
    sized = size_interference_fit(**SIZE_BASE)
    checked = analyze_interference_fit(**CHECK_BASE)
    assert set(sized["assembly"]) == set(checked["assembly"])


def test_checker_has_no_assembly_temperature_input():
    """Assembly temperature is derived, so it is not something you set."""
    import inspect

    parameters = inspect.signature(analyze_interference_fit).parameters
    assert "assembly_temperature_c" not in parameters
    assert "hub_max_assembly_temp_c" in parameters
    assert "shaft_min_assembly_temp_c" in parameters


def test_checker_no_longer_evaluates_a_redundant_assembly_state():
    """The old third state duplicated the reference case at the same temperature."""
    results = analyze_interference_fit(**CHECK_BASE)
    assert set(results["range_cases"]["nominal"]) == {"reference", "operating"}
    assert "assembly_case" not in results
    assert "assembly" not in results["stress_distribution_cases"]


# --- ISO 286 manufacturing window ------------------------------------------

def test_iso286_tolerance_unit_matches_published_grades():
    # 50 mm sits in the 30 to 50 step: i = 1.56 um, IT6 = 15.6, IT7 = 25.
    unit = _iso286_tolerance_unit_um(50.0)
    assert unit == pytest.approx(1.56, abs=0.02)


def test_iso286_step_boundary_is_tolerant_of_float_noise():
    """A unit round trip lands a hair over 50 mm; the grade must not jump."""
    assert _iso286_tolerance_unit_um(50.0) == pytest.approx(
        _iso286_tolerance_unit_um(50.0000016)
    )
    # A genuinely larger diameter still moves to the next step.
    assert _iso286_tolerance_unit_um(55.0) > _iso286_tolerance_unit_um(50.0)


def test_window_grading_flags_unbuildable_tolerances():
    tight = _classify_manufacturing_window(window_mm=0.0028, shaft_outer_diameter_mm=50.0)
    assert tight["practical"] is False
    roomy = _classify_manufacturing_window(window_mm=0.048, shaft_outer_diameter_mm=50.0)
    assert roomy["practical"] is True
    assert roomy["per_part_it_grade"] >= 6


def test_narrow_window_downgrades_status_and_explains_why():
    """A feasible answer can still be unbuildable; say so instead of passing it."""
    results = size_interference_fit(
        **{
            **SIZE_BASE,
            "hub_material": "aluminum_6061_t6",
            "maximum_operating_temperature_c": 150.0,
        }
    )
    assert results["design_range"]["feasible"] is True
    assert results["design_range"]["available_tolerance_mm"] > 0.0
    assert results["status"] == "marginal"
    assert results["manufacturing"]["practical"] is False
    assert any("per part" in w for w in results["warnings"])


# --- Assembly and release forces -------------------------------------------

def test_press_force_comes_from_the_effective_interference():
    """Same pressure as every other number in the tool, not an inflated one."""
    results = size_interference_fit(
        **{**SIZE_BASE, "shaft_roughness_rz_um": 4.0, "hub_roughness_rz_um": 4.0}
    )
    planned = results["assembly"]["planned"]
    maximum = results["assembly"]["governing_interference_mm"]
    smoothing = results["smoothing"]["smoothing_loss_mm"]
    compliance = results["compliance"]["total_term_mm_per_mpa"]

    expected_pressure = (maximum - smoothing) / compliance
    assert planned["ambient_press_pressure_mpa"] == pytest.approx(expected_pressure)

    expected_force = (
        0.15 * 1.5  # default friction, default insertion factor
        * expected_pressure * 1e6
        * math.pi * 0.050 * 0.075
    )
    assert planned["ambient_press_force_n"] == pytest.approx(expected_force)


def test_pressing_in_is_harder_than_pushing_out():
    """Insertion galls, so it carries the higher friction of the two."""
    results = size_interference_fit(
        **{**SIZE_BASE, "shaft_roughness_rz_um": 4.0, "hub_roughness_rz_um": 4.0}
    )
    planned = results["assembly"]["planned"]
    push_off = results["assembly_forces"]["push_off_force_n"]
    # Same pressure both ways; the whole difference is the friction factor.
    assert planned["ambient_press_force_n"] == pytest.approx(push_off * 1.5)
    assert planned["press_friction_coefficient"] == pytest.approx(0.15 * 1.5)


def test_press_friction_factor_is_adjustable():
    plain = size_interference_fit(**{**SIZE_BASE, "press_friction_factor": 1.0})
    assert plain["assembly"]["planned"]["ambient_press_force_n"] == pytest.approx(
        plain["assembly_forces"]["push_off_force_n"]
    )


def test_press_force_names_the_interference_it_used():
    feasible = size_interference_fit(**SIZE_BASE)
    assert feasible["assembly"]["governing_interference_label"] == "allowable maximum"
    assert feasible["assembly"]["governing_interference_mm"] == pytest.approx(
        feasible["design_range"]["allowable_maximum_mm"]
    )
    # Which is exactly the top of the band that gets released.
    assert feasible["assembly"]["governing_interference_mm"] == pytest.approx(
        feasible["design_range"]["recommended_nominal_mm"]
        + feasible["design_range"]["recommended_bilateral_tolerance_mm"]
    )


def test_infeasible_design_does_not_quote_a_press_force_for_a_band_that_does_not_exist():
    """It used to report the stress limit, a far smaller and misleading number."""
    results = size_interference_fit(
        shaft_outer_diameter_mm=50.0,
        hub_outer_diameter_mm=60.0,
        fit_length_mm=20.0,
        required_torque_nm=10000.0,
    )
    assert results["design_range"]["feasible"] is False
    assembly = results["assembly"]
    assert "no feasible band" in assembly["governing_interference_label"]
    assert assembly["governing_interference_mm"] == pytest.approx(
        results["design_range"]["required_minimum_mm"]
    )
    assert assembly["governing_interference_mm"] > results["design_range"][
        "allowable_maximum_mm"
    ]


def test_assembly_temperature_reduces_the_press_force():
    """Heating the hub without fully clearing is the usual shop compromise."""
    cold = size_interference_fit(**SIZE_BASE)["assembly"]["planned"]
    assert cold["is_ambient"] is True
    assert cold["force_reduction_percent"] == pytest.approx(0.0)

    warm = size_interference_fit(
        **{**SIZE_BASE, "hub_assembly_temperature_c": 150.0}
    )["assembly"]["planned"]
    assert warm["slips_together"] is False
    assert warm["remaining_interference_mm"] < cold["remaining_interference_mm"]
    assert warm["press_force_n"] < cold["press_force_n"]
    assert warm["force_reduction_percent"] > 50.0
    # The opening is just free thermal growth of the hub bore.
    assert warm["opening_mm"] == pytest.approx(50.0 * 12.0e-6 * (150.0 - 20.0))


def test_enough_assembly_heat_removes_the_press_entirely():
    results = size_interference_fit(
        **{**SIZE_BASE, "hub_assembly_temperature_c": 250.0}
    )
    planned = results["assembly"]["planned"]
    assert planned["slips_together"] is True
    assert planned["press_force_n"] == pytest.approx(0.0)
    assert planned["residual_clearance_mm"] > 0.0
    assert planned["force_reduction_percent"] == pytest.approx(100.0)


def test_chilling_the_shaft_also_opens_the_joint():
    hub_only = size_interference_fit(
        **{**SIZE_BASE, "hub_assembly_temperature_c": 100.0}
    )["assembly"]["planned"]
    both = size_interference_fit(
        **{
            **SIZE_BASE,
            "hub_assembly_temperature_c": 100.0,
            "shaft_assembly_temperature_c": -40.0,
        }
    )["assembly"]["planned"]
    assert both["opening_mm"] > hub_only["opening_mm"]
    assert both["press_force_n"] < hub_only["press_force_n"]
    # Chilling the shaft shrinks it, which counts as opening.
    assert both["shaft_growth_mm"] < 0.0


def test_recommended_temperature_matches_the_slip_on_threshold():
    """With no slip clearance asked for, the recommendation is the exact threshold."""
    args = {**SIZE_BASE, "assembly_clearance_mm": 0.0}
    required = size_interference_fit(**args)["assembly"]["hub_heating_temperature_c"]

    just_under = size_interference_fit(
        **{**args, "hub_assembly_temperature_c": required - 5.0}
    )["assembly"]["planned"]
    at_target = size_interference_fit(
        **{**args, "hub_assembly_temperature_c": required}
    )["assembly"]["planned"]
    assert just_under["slips_together"] is False
    assert at_target["slips_together"] is True
    assert at_target["press_force_n"] == pytest.approx(0.0)


def test_recommended_temperature_carries_the_slip_clearance_on_top():
    """The recommendation buys the interference plus the clearance you asked for."""
    args = {**SIZE_BASE, "assembly_clearance_mm": 0.02}
    results = size_interference_fit(**args)
    required = results["assembly"]["hub_heating_temperature_c"]
    at_target = size_interference_fit(
        **{**args, "hub_assembly_temperature_c": required}
    )["assembly"]["planned"]
    assert at_target["residual_clearance_mm"] == pytest.approx(0.02)


def test_checker_reports_the_same_assembly_plan():
    results = analyze_interference_fit(
        **{**CHECK_BASE, "hub_assembly_temperature_c": 150.0}
    )
    planned = results["assembly"]["planned"]
    assert planned["hub_temperature_c"] == pytest.approx(150.0)
    assert planned["press_force_n"] < planned["ambient_press_force_n"]


def test_impractical_planned_temperature_warns():
    results = size_interference_fit(
        **{**SIZE_BASE, "hub_assembly_temperature_c": 500.0}
    )
    assert any("planned hub temperature" in w for w in results["warnings"])


# --- Speed in the checker --------------------------------------------------

def test_checker_speed_opens_the_fit_and_adds_rotating_stress():
    stationary = analyze_interference_fit(**CHECK_BASE)
    spinning = analyze_interference_fit(**{**CHECK_BASE, "operating_speed_rpm": 20000.0})
    assert spinning["speed"]["interference_relief_mm"] > 0.0
    assert (
        spinning["nominal_case"]["operating"]["pressure_mpa"]
        < stationary["nominal_case"]["operating"]["pressure_mpa"]
    )
    # Pressure falls but rotating hoop stress more than makes up for it.
    assert (
        spinning["nominal_case"]["operating"]["yield_safety_factor"]
        < stationary["nominal_case"]["operating"]["yield_safety_factor"]
    )


# --- Material preset data --------------------------------------------------

def test_quenched_and_tempered_steels_carry_quenched_and_tempered_strength():
    presets = get_interference_fit_material_presets()
    assert presets["steel_4140_qt"]["yield_strength_mpa"] >= 1000.0
    assert presets["steel_4340_qt"]["yield_strength_mpa"] >= 1000.0
    # The old mislabeled values survive under honest names.
    assert presets["steel_4140_normalized"]["yield_strength_mpa"] == pytest.approx(655.0)
    assert presets["steel_4340_annealed"]["yield_strength_mpa"] == pytest.approx(470.0)


def test_every_preset_declares_its_condition_criterion_and_source():
    for key, preset in get_interference_fit_material_presets().items():
        assert preset["condition"], key
        assert preset["source"], key
        assert preset["failure_criterion"] in (VON_MISES, BRITTLE), key
        assert preset["compressive_strength_mpa"] > 0.0, key


def test_bearing_bronze_is_not_a_copy_of_tin_bronze():
    presets = get_interference_fit_material_presets()
    assert (
        presets["bronze"]["yield_strength_mpa"]
        != presets["bronze_bearing"]["yield_strength_mpa"]
    )


def test_friction_and_roughness_presets_are_usable():
    friction = get_interference_fit_friction_presets()
    assert "steel_steel_pressed_dry" in friction
    for preset in friction.values():
        assert preset["friction_coefficient"] > 0.0
        assert preset["range_label"]
    roughness = get_interference_fit_roughness_presets()
    assert roughness["ground"]["rz_um"] == pytest.approx(4.0)


# --- Custom brittle material path ------------------------------------------

def test_custom_material_can_declare_a_brittle_criterion():
    results = size_interference_fit(
        **{
            **SIZE_BASE,
            "hub_material": "custom",
            "hub_youngs_modulus_mpa": 103000.0,
            "hub_poisson_ratio": 0.26,
            "hub_yield_strength_mpa": 214.0,
            "hub_compressive_strength_mpa": 752.0,
            "hub_failure_criterion": "brittle",
            "hub_thermal_expansion_e6_per_c": 11.4,
            "hub_density_kg_m3": 7150.0,
        }
    )
    assert results["materials"]["hub"]["failure_criterion"] == BRITTLE


def test_unknown_failure_criterion_is_rejected():
    with pytest.raises(ValueError, match="failure_criterion"):
        size_interference_fit(
            **{**SIZE_BASE, "hub_material": "custom", "hub_failure_criterion": "guess"}
        )
