"""Tests for pycalcs.power_screws."""

import math

import pytest

from pycalcs.power_screws import (
    END_FIXITIES,
    SCREW_PRESETS,
    THREAD_FORMS,
    analyze_jack_screw,
    ball_screw_comparison,
    column_buckling,
    critical_speed,
    screw_torques,
    thread_geometry,
    thread_stresses,
)


# --- Textbook validation ----------------------------------------------------


def test_shigley_example_8_1_square_thread():
    """Shigley, Mechanical Engineering Design 10th ed., Example 8-1.

    A 25 mm square thread, 5 mm pitch, single start, raising 6.4 kN with
    thread and collar friction of 0.08 and a 40 mm collar. The book gives
    T_R = 21.16 N*m, T_L = 10.9 N*m, efficiency 24.1 percent.
    """
    result = screw_torques(
        load_n=6400.0,
        mean_diameter_mm=22.5,
        lead_mm=5.0,
        thread_friction=0.08,
        thread_half_angle_deg=0.0,
        collar_friction=0.08,
        collar_diameter_mm=40.0,
    )
    assert result["raise_torque_total_nm"] == pytest.approx(21.16, abs=0.02)
    assert result["lower_torque_total_nm"] == pytest.approx(10.9, abs=0.05)
    assert result["efficiency"] == pytest.approx(0.241, abs=0.001)
    assert result["self_locking"] is True


def test_acme_costs_more_torque_than_square():
    """The sec(alpha) term makes an angled flank drag more for the same mu."""
    common = dict(
        load_n=6400.0, mean_diameter_mm=22.5, lead_mm=5.0, thread_friction=0.08
    )
    square = screw_torques(thread_half_angle_deg=0.0, **common)
    acme = screw_torques(thread_half_angle_deg=14.5, **common)
    assert acme["raise_torque_total_nm"] > square["raise_torque_total_nm"]
    assert acme["efficiency"] < square["efficiency"]


def test_critical_speed_matches_published_imperial_constant():
    """The lead screw trade formula is N = 4.76e6 * Cs * d_root / L^2, inches.

    Deriving from the beam eigenvalue should reproduce that constant for the
    pinned-pinned case where Cs = 1.
    """
    root_in, length_in = 0.75, 30.0
    result = critical_speed(
        minor_diameter_mm=root_in * 25.4,
        unsupported_length_mm=length_in * 25.4,
        modulus_gpa=205.0,
        density_kg_m3=7850.0,
        end_fixity="pinned_pinned",
    )
    published = 4.76e6 * root_in / length_in ** 2
    assert result["critical_speed_rpm"] == pytest.approx(published, rel=0.02)


def test_end_fixity_speed_factors_match_published_table():
    """Published Cs factors are 0.36, 1.0, ~1.47 and ~2.23 relative to pinned."""
    base = None
    ratios = {}
    for key in ("pinned_pinned", "fixed_free", "fixed_pinned", "fixed_fixed"):
        speed = critical_speed(20.0, 600.0, 205.0, 7850.0, key)["critical_speed_rpm"]
        if key == "pinned_pinned":
            base = speed
        ratios[key] = speed / base
    assert ratios["fixed_free"] == pytest.approx(0.36, abs=0.01)
    assert ratios["fixed_pinned"] == pytest.approx(1.5, abs=0.1)
    assert ratios["fixed_fixed"] == pytest.approx(2.25, abs=0.1)


# --- Geometry ---------------------------------------------------------------


def test_geometry_basic_proportions():
    geometry = thread_geometry(32.0, 6.0, starts=1, thread_form="square")
    assert geometry["mean_diameter_mm"] == pytest.approx(29.0)
    assert geometry["minor_diameter_mm"] == pytest.approx(26.0)
    assert geometry["lead_mm"] == pytest.approx(6.0)
    assert geometry["lead_angle_deg"] == pytest.approx(
        math.degrees(math.atan(6.0 / (math.pi * 29.0)))
    )


def test_multiple_starts_multiply_lead():
    single = thread_geometry(32.0, 6.0, starts=1)
    double = thread_geometry(32.0, 6.0, starts=2)
    assert double["lead_mm"] == pytest.approx(2.0 * single["lead_mm"])
    assert double["lead_angle_deg"] > single["lead_angle_deg"]


def test_measured_diameters_override_derived_ones():
    geometry = thread_geometry(
        25.4, 5.08, thread_form="acme", minor_diameter_mm=19.812
    )
    assert geometry["minor_diameter_mm"] == pytest.approx(19.812)


def test_every_preset_builds_valid_geometry():
    for preset in SCREW_PRESETS:
        geometry = thread_geometry(
            preset["nominal_diameter_mm"],
            preset["pitch_mm"],
            1,
            preset["form"],
            preset["minor_diameter_mm"],
        )
        assert 0.0 < geometry["minor_diameter_mm"] < preset["nominal_diameter_mm"]
        assert geometry["lead_angle_deg"] < 20.0


# --- Self-locking -----------------------------------------------------------


def test_many_starts_break_self_locking():
    """Lead angle rises with starts until it overruns the friction angle."""
    geometry = thread_geometry(32.0, 6.0, starts=4, thread_form="acme")
    result = screw_torques(
        25000.0, geometry["mean_diameter_mm"], geometry["lead_mm"], 0.10,
        geometry["thread_half_angle_deg"],
    )
    assert result["self_locking_thread_only"] is False
    assert result["holding_torque_nm"] > 0.0
    assert result["self_locking_margin"] < 1.0


def test_self_locking_margin_is_thread_only():
    """A generous collar must not make a back-driving thread look safe."""
    geometry = thread_geometry(32.0, 6.0, starts=4, thread_form="acme")
    result = screw_torques(
        25000.0, geometry["mean_diameter_mm"], geometry["lead_mm"], 0.10,
        geometry["thread_half_angle_deg"],
        collar_friction=0.5, collar_diameter_mm=90.0,
    )
    assert result["self_locking"] is True
    assert result["self_locking_thread_only"] is False


def test_collar_only_self_locking_is_flagged_critical():
    result = analyze_jack_screw(
        starts=4, thread_friction=0.10, collar_friction=0.5, collar_diameter_mm=90.0
    )
    assert result["verdict"] == "unacceptable"
    assert any(
        w["level"] == "critical" and "collar friction" in w["message"]
        for w in result["warnings"]
    )


def test_self_locking_boundary_matches_lead_angle_condition():
    """mu*sec(alpha) == tan(lambda) is the tipping point."""
    geometry = thread_geometry(32.0, 6.0, starts=1, thread_form="acme")
    tan_lambda = geometry["lead_mm"] / (math.pi * geometry["mean_diameter_mm"])
    mu_critical = tan_lambda * math.cos(math.radians(14.5))
    just_below = screw_torques(
        10000.0, geometry["mean_diameter_mm"], geometry["lead_mm"],
        mu_critical * 0.98, 14.5,
    )
    just_above = screw_torques(
        10000.0, geometry["mean_diameter_mm"], geometry["lead_mm"],
        mu_critical * 1.02, 14.5,
    )
    assert just_below["self_locking_thread_only"] is False
    assert just_above["self_locking_thread_only"] is True


# --- Stresses ---------------------------------------------------------------


def test_bearing_pressure_matches_hand_calculation():
    geometry = thread_geometry(32.0, 6.0, 1, "acme")
    result = thread_stresses(25000.0, geometry, 48.0, 0.0, "acme")
    engaged = 48.0 / 6.0
    expected = 25000.0 / (math.pi * geometry["mean_diameter_mm"] * 3.0 * engaged)
    assert result["engaged_threads"] == pytest.approx(engaged)
    assert result["bearing_pressure_mpa"] == pytest.approx(expected)


def test_body_von_mises_combines_axial_and_torsion():
    geometry = thread_geometry(32.0, 6.0, 1, "acme")
    result = thread_stresses(25000.0, geometry, 48.0, 150.0, "acme")
    expected = math.sqrt(
        result["body_axial_stress_mpa"] ** 2
        + 3.0 * result["body_torsional_shear_mpa"] ** 2
    )
    assert result["body_von_mises_mpa"] == pytest.approx(expected)
    assert result["body_von_mises_mpa"] > result["body_axial_stress_mpa"]


def test_longer_nut_lowers_bearing_pressure_proportionally():
    geometry = thread_geometry(32.0, 6.0, 1, "acme")
    short = thread_stresses(25000.0, geometry, 24.0, 0.0, "acme")
    long = thread_stresses(25000.0, geometry, 48.0, 0.0, "acme")
    assert long["bearing_pressure_mpa"] == pytest.approx(
        short["bearing_pressure_mpa"] / 2.0
    )


def test_first_thread_pressure_ignores_nut_length():
    """Load concentration means extra threads do not relieve the first one."""
    geometry = thread_geometry(32.0, 6.0, 1, "acme")
    short = thread_stresses(25000.0, geometry, 24.0, 0.0, "acme")
    long = thread_stresses(25000.0, geometry, 96.0, 0.0, "acme")
    assert short["bearing_pressure_first_thread_mpa"] == pytest.approx(
        long["bearing_pressure_first_thread_mpa"]
    )


def test_engagement_below_one_pitch_is_rejected():
    geometry = thread_geometry(32.0, 6.0, 1, "acme")
    with pytest.raises(ValueError, match="shorter than one pitch"):
        thread_stresses(25000.0, geometry, 4.0, 0.0, "acme")


# --- Buckling ---------------------------------------------------------------


def test_euler_branch_matches_closed_form():
    result = column_buckling(20.0, 600.0, 205.0, 530.0, "fixed_free")
    area = math.pi * 20.0 ** 2 / 4.0
    slenderness = 2.1 * 600.0 / (20.0 / 4.0)
    expected = math.pi ** 2 * 205000.0 * area / slenderness ** 2
    assert result["buckling_mode"] == "euler"
    assert result["critical_load_n"] == pytest.approx(expected)


def test_johnson_branch_governs_for_a_stocky_column():
    result = column_buckling(40.0, 150.0, 205.0, 530.0, "pinned_pinned")
    assert result["buckling_mode"] == "johnson"
    assert result["slenderness_ratio"] < result["transition_slenderness"]
    # Johnson must not exceed squash load, and must beat the Euler value here.
    area = math.pi * 40.0 ** 2 / 4.0
    euler = math.pi ** 2 * 205000.0 * area / result["slenderness_ratio"] ** 2
    assert result["critical_load_n"] < area * 530.0
    assert result["critical_load_n"] < euler


def test_buckling_load_falls_with_square_of_length():
    short = column_buckling(20.0, 500.0, 205.0, 530.0, "fixed_free")
    long = column_buckling(20.0, 1000.0, 205.0, 530.0, "fixed_free")
    assert short["buckling_mode"] == long["buckling_mode"] == "euler"
    assert long["critical_load_n"] == pytest.approx(short["critical_load_n"] / 4.0)


def test_fixity_ranks_as_expected():
    loads = {
        key: column_buckling(20.0, 800.0, 205.0, 530.0, key)["critical_load_n"]
        for key in END_FIXITIES
    }
    assert (
        loads["fixed_free"]
        < loads["pinned_pinned"]
        < loads["fixed_pinned"]
        < loads["fixed_fixed"]
    )


# --- Ball screw -------------------------------------------------------------


def test_ball_screw_back_drive_efficiency():
    result = ball_screw_comparison(25000.0, 6.0, 0.90)
    assert result["back_drive_efficiency"] == pytest.approx(2.0 - 1.0 / 0.90)
    assert result["self_locking"] is False
    assert result["back_drive_torque_nm"] > 0.0


def test_ball_screw_below_half_efficiency_self_locks():
    result = ball_screw_comparison(25000.0, 6.0, 0.45)
    assert result["self_locking"] is True
    assert result["back_drive_torque_nm"] == 0.0


def test_ball_screw_torque_is_the_frictionless_work_balance():
    result = ball_screw_comparison(25000.0, 6.0, 1.0 - 1e-9)
    assert result["raise_torque_nm"] == pytest.approx(25000.0 * 0.006 / (2 * math.pi))


# --- Top-level analysis -----------------------------------------------------


def test_default_case_is_a_workable_jack():
    result = analyze_jack_screw()
    assert result["verdict"] in ("ok", "caution")
    assert result["torque"]["self_locking_thread_only"] is True
    assert result["buckling"]["safety_factor"] > 1.0
    assert result["thread"]["bearing_margin"] > 1.0
    assert result["ball_screw"]["torque_ratio"] > 1.0


def test_optional_sections_are_skipped_when_lengths_are_zero():
    result = analyze_jack_screw(nut_engagement_length_mm=0.0, unsupported_length_mm=0.0)
    assert result["thread"]["evaluated"] is False
    assert result["buckling"]["evaluated"] is False
    assert result["whirl"]["evaluated"] is False
    assert result["torque"]["raise_torque_total_nm"] > 0.0


def test_overlong_column_is_called_out():
    result = analyze_jack_screw(unsupported_length_mm=2000.0)
    assert result["verdict"] == "unacceptable"
    assert any("buckles" in w["message"] for w in result["warnings"])


def test_overloaded_nut_is_called_out():
    result = analyze_jack_screw(load_n=120000.0, nut_engagement_length_mm=20.0)
    assert any(
        w["level"] == "critical" and "bearing pressure" in w["message"].lower()
        for w in result["warnings"]
    )


def test_speed_above_whirl_is_called_out():
    result = analyze_jack_screw(unsupported_length_mm=1200.0, rotational_speed_rpm=4000.0)
    assert any("whirl" in w["message"] for w in result["warnings"])


def test_material_overrides_take_precedence():
    preset = analyze_jack_screw()
    override = analyze_jack_screw(screw_yield_mpa=1100.0)
    assert override["materials"]["screw_yield_mpa"] == 1100.0
    assert (
        override["thread"]["body_safety_factor"] > preset["thread"]["body_safety_factor"]
    )


def test_duty_outputs_scale_with_speed():
    result = analyze_jack_screw(rotational_speed_rpm=60.0)
    assert result["duty"]["travel_speed_mm_s"] == pytest.approx(6.0)
    assert result["duty"]["input_power_w"] > 0.0
    assert result["duty"]["pv_value_mpa_m_s"] > 0.0


def test_lever_arm_gives_operator_force():
    result = analyze_jack_screw(lever_arm_mm=500.0)
    expected = result["torque"]["raise_torque_total_nm"] / 0.5
    assert result["duty"]["operator_force_n"] == pytest.approx(expected)


# --- Input validation -------------------------------------------------------


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_non_finite_inputs_are_rejected(bad):
    with pytest.raises(ValueError, match="finite"):
        analyze_jack_screw(load_n=bad)


def test_zero_load_is_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        analyze_jack_screw(load_n=0.0)


def test_negative_friction_is_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        analyze_jack_screw(thread_friction=-0.1)


def test_unknown_thread_form_lists_the_valid_keys():
    with pytest.raises(ValueError, match="acme"):
        analyze_jack_screw(thread_form="triangular")


def test_pitch_larger_than_the_screw_is_rejected():
    with pytest.raises(ValueError, match="Thread depth"):
        thread_geometry(10.0, 12.0, 1, "acme")


def test_fractional_starts_are_rejected():
    with pytest.raises(ValueError, match="whole number"):
        thread_geometry(32.0, 6.0, starts=1.5, thread_form="acme")


def test_friction_that_prevents_motion_is_reported_clearly():
    with pytest.raises(ValueError, match="cannot be driven forward"):
        screw_torques(1000.0, 20.0, 5.0, thread_friction=20.0)


# --- Data table integrity ---------------------------------------------------


def test_thread_forms_carry_every_field_the_model_reads():
    required = {
        "label", "half_angle_deg", "depth_factor", "clearance_factor",
        "shear_width_screw", "shear_width_nut", "note",
    }
    for key, form in THREAD_FORMS.items():
        assert required <= set(form), f"{key} is missing {required - set(form)}"
        assert 0.0 <= form["half_angle_deg"] < 45.0


def test_preset_minor_diameters_sit_below_the_no_clearance_basic():
    """Standards cut a root clearance below the basic minor diameter.

    ISO 2904 uses 0.5 mm of clearance per flank for pitches of 3 to 12 mm;
    ASME B1.5 general purpose Acme uses 0.010 inch. Either way the table
    value must be at or below the no-clearance proportion, and within about
    a millimetre of it.
    """
    for preset in SCREW_PRESETS:
        form = THREAD_FORMS[preset["form"]]
        basic = preset["nominal_diameter_mm"] - 2.0 * form["depth_factor"] * preset["pitch_mm"]
        minor = preset["minor_diameter_mm"]
        assert minor <= basic + 1e-9, preset["key"]
        assert basic - minor <= 1.1, preset["key"]


def test_preset_minor_diameters_match_their_standard_formula():
    """Tr uses d - p - 2*ac; Acme uses d - p - 0.020 inch."""
    for preset in SCREW_PRESETS:
        d, p = preset["nominal_diameter_mm"], preset["pitch_mm"]
        if preset["form"] == "trapezoidal":
            clearance = 0.25 if p <= 2.0 else (0.5 if p <= 12.0 else 1.0)
            expected = d - p - 2.0 * clearance
        else:
            expected = d - p - 0.508
        assert preset["minor_diameter_mm"] == pytest.approx(expected, abs=0.01), preset["key"]


# --- Tool test-case fixtures ------------------------------------------------
#
# tools/jack-screw/test-cases/*.json are the scenarios documented for the tool.
# Running them here keeps the published cases honest: if the model moves, the
# numbers in those files have to move with it.

import json
import pathlib

CASE_DIR = pathlib.Path(__file__).resolve().parent.parent / "tools" / "jack-screw" / "test-cases"


def _dig(result, dotted):
    node = result
    for part in dotted.split("."):
        node = node[part]
    return node


def _case_files():
    return sorted(CASE_DIR.glob("*.json"))


def test_test_case_directory_is_populated():
    assert _case_files(), f"No test cases found in {CASE_DIR}"


@pytest.mark.parametrize("path", _case_files(), ids=lambda p: p.stem)
def test_tool_test_case_matches_its_expected_values(path):
    case = json.loads(path.read_text())
    assert {"name", "purpose", "inputs", "expected"} <= set(case), path.name

    result = analyze_jack_screw(**case["inputs"])

    for key, expected in case["expected"].items():
        actual = _dig(result, key)
        if isinstance(expected, bool) or isinstance(expected, str):
            assert actual == expected, f"{path.name}: {key} was {actual!r}"
        else:
            assert actual == pytest.approx(expected, rel=0.01), (
                f"{path.name}: {key} was {actual!r}, expected about {expected!r}"
            )
