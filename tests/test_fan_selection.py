"""Tests for pycalcs.fan_selection."""

import json

import pytest

from pycalcs.fan_selection import (
    analyze_fan_types,
    balje_eta_envelope,
    balje_eta_family,
    compute_air_density,
    cordier_ds,
    cordier_efficiency,
    estimate_reference_geometry,
    evaluate_acoustic_risk,
    evaluate_architecture_margin,
    evaluate_drive_fit,
    evaluate_passage_fit,
    evaluate_velocity_constraint,
    family_anchors,
    full_analysis,
    generate_balje_field,
    recommend_radial_subtype,
    specific_diameter,
    specific_speed,
    suggest_nominal_diameter,
)


class TestDimensionlessQuantities:
    def test_specific_speed_matches_hand_calculation_range(self):
        ns = specific_speed(1.0, 500.0, 1500.0, 1.204)
        assert ns == pytest.approx(1.71, rel=0.03)

    def test_specific_diameter_matches_hand_calculation_range(self):
        ds = specific_diameter(0.4, 1.0, 500.0, 1.204)
        assert ds == pytest.approx(1.806, rel=0.02)


class TestVelocityConstraint:
    def test_target_velocity_constraint_infers_area(self):
        constraint = evaluate_velocity_constraint(
            flow_m3s=1.2,
            velocity_mode="target_velocity",
            target_velocity_ms=10.0,
        )
        assert constraint["active"] is True
        assert constraint["area_m2"] == pytest.approx(0.12)
        assert constraint["equivalent_diameter_m"] == pytest.approx(0.391, rel=0.02)

    def test_passage_fit_distinguishes_axial_and_radial_preferences(self):
        constraint = evaluate_velocity_constraint(
            flow_m3s=1.0,
            velocity_mode="target_velocity",
            target_velocity_ms=9.0,
        )
        axial_geometry = estimate_reference_geometry("axial", 0.38, 1.0)
        radial_geometry = estimate_reference_geometry("centrifugal_bc", 0.38, 1.0)
        axial_fit = evaluate_passage_fit("axial", axial_geometry, constraint)
        radial_fit = evaluate_passage_fit("radial", radial_geometry, constraint)
        assert axial_fit["combined_fit"] > radial_fit["combined_fit"]
        assert axial_fit["area_ratio"] < radial_fit["area_ratio"]

    def test_reference_geometry_returns_annulus_area(self):
        geometry = estimate_reference_geometry("axial", 0.4, 1.0)
        assert geometry["basis_label"] == "Rotor annulus"
        assert geometry["reference_outer_diameter_m"] == pytest.approx(0.4)
        assert geometry["reference_inner_diameter_m"] == pytest.approx(0.144, rel=0.01)
        assert geometry["gross_flow_area_m2"] == pytest.approx(0.108, rel=0.03)
        assert geometry["effective_flow_area_m2"] < geometry["gross_flow_area_m2"]

    def test_reference_geometry_returns_centrifugal_eye_area(self):
        geometry = estimate_reference_geometry("centrifugal_bc", 0.5, 1.0)
        assert geometry["basis_label"] == "Inlet eye annulus"
        assert geometry["eye_outer_diameter_m"] == pytest.approx(0.29, rel=0.01)
        assert geometry["effective_flow_area_m2"] == pytest.approx(0.050, rel=0.08)
        assert geometry["reference_velocity_ms"] > 10.0

    def test_axial_hub_diameter_override_is_used(self):
        geometry = estimate_reference_geometry(
            "axial",
            0.4,
            1.0,
            {"axial": {"hub_diameter_m": 0.12}},
        )
        assert geometry["override_active"] is True
        assert geometry["reference_inner_diameter_m"] == pytest.approx(0.12)
        assert geometry["override_note"].startswith("Custom geometry override active")

    def test_centrifugal_eye_diameter_override_json_is_used(self):
        geometry = estimate_reference_geometry(
            "centrifugal_bc",
            0.5,
            1.0,
            json.dumps({"centrifugal_bc": {"eye_outer_diameter_m": 0.26, "eye_hub_diameter_m": 0.11}}),
        )
        assert geometry["override_active"] is True
        assert geometry["reference_outer_diameter_m"] == pytest.approx(0.26)
        assert geometry["reference_inner_diameter_m"] == pytest.approx(0.11)


class TestFanTypeComparison:
    def test_unconstrained_screen_prefers_backward_curved_for_nominal_duty(self):
        comparison = analyze_fan_types(flow_m3s=1.0, pressure_pa=500.0)
        assert comparison[0]["type_id"] == "centrifugal_bc"
        assert comparison[0]["suitability_score"] > comparison[-1]["suitability_score"]
        assert comparison[0]["specific_speed"] == pytest.approx(0.8, rel=0.05)
        assert comparison[0]["score_breakdown"]["total"] == pytest.approx(comparison[0]["suitability_score"], rel=0.01)

    def test_fixed_speed_constraint_uses_shared_actual_speed(self):
        comparison = analyze_fan_types(flow_m3s=1.0, pressure_pa=500.0, speed_rpm=1500.0)
        assert all(candidate["speed_rpm"] == pytest.approx(1500.0) for candidate in comparison)
        assert len({candidate["specific_speed"] for candidate in comparison}) == 1

    def test_full_analysis_returns_radial_branch_and_geometry_payload(self):
        density = compute_air_density(20.0, 0.0)
        data = full_analysis(
            flow_m3s=1.0,
            pressure_pa=500.0,
            pressure_basis="static",
            density_kgm3=density,
            velocity_mode="target_velocity",
            target_velocity_ms=16.0,
        )
        assert data["velocity_constraint"]["active"] is True
        assert data["recommendation"]["best_type_id"] == "centrifugal_bc"
        assert data["recommendation"]["radial_branch"]["leader"]["type_id"] == "centrifugal_bc"
        assert "diameter_from_ds" in data["derivations"]
        assert "speed_from_ns" in data["derivations"]
        assert "score" in data["derivations"]
        assert "drive_fit" in data["derivations"]
        assert "architecture_margin" in data["derivations"]
        assert "acoustic_risk" in data["derivations"]
        assert "nominal_size" in data["derivations"]
        assert "reference_geometry" in data["derivations"]
        assert "reference_velocity" in data["derivations"]
        assert "passage_area_match" in data["derivations"]
        assert "decision_audit" in data
        assert len(data["decision_audit"]["stages"]) >= 4
        assert len(data["decision_audit"]["weight_rationale"]) >= 3
        assert data["decision_audit"]["candidate_outcomes"][0]["type"] == data["comparison"][0]["short_name"]
        best = data["comparison"][0]
        assert best["reference_geometry"]["effective_flow_area_m2"] > 0.0
        assert "packaging_signature" in best
        assert "drive_fit" in best
        assert "architecture_margin" in best
        assert "acoustic_risk" in best
        assert "nominal_size" in best
        assert data["decision_audit"]["weight_rationale"][0]["component"] == "Specific-speed fit"

    def test_full_analysis_carries_geometry_overrides_into_results(self):
        density = compute_air_density(20.0, 0.0)
        data = full_analysis(
            flow_m3s=1.0,
            pressure_pa=500.0,
            pressure_basis="static",
            density_kgm3=density,
            geometry_overrides={"axial": {"hub_diameter_m": 0.10}},
        )
        axial = next(item for item in data["comparison"] if item["type_id"] == "axial")
        assert axial["reference_geometry"]["override_active"] is True
        assert axial["reference_geometry"]["reference_inner_diameter_m"] == pytest.approx(0.10)
        assert data["inputs"]["geometry_overrides"]["axial"]["hub_diameter_m"] == pytest.approx(0.10)


class TestPracticalSignals:
    def test_nominal_size_suggestion_brackets_estimate(self):
        suggestion = suggest_nominal_diameter(0.412)
        assert suggestion["nearest_mm"] == 400
        assert suggestion["bracket_mm"] == [400, 450]

    def test_drive_fit_flags_standard_speed(self):
        drive_fit = evaluate_drive_fit(1800.0, shaft_power_w=750.0)
        assert drive_fit["label"] == "Standard direct-drive induction"
        assert drive_fit["nearest_rpm"] == pytest.approx(1800.0)
        assert drive_fit["frequency_dependency"] == "High"

    def test_drive_fit_can_recommend_gearbox(self):
        drive_fit = evaluate_drive_fit(320.0, shaft_power_w=5000.0)
        assert drive_fit["label"] == "Gearbox or gearmotor reduction"
        assert drive_fit["topology"] == "gearbox_reduction"
        assert drive_fit["torque_nm"] is not None

    def test_architecture_margin_and_acoustic_risk_are_directional(self):
        margin = evaluate_architecture_margin("axial", 2.2)
        quiet_constraint = evaluate_velocity_constraint(1.0, "none")
        acoustic = evaluate_acoustic_risk("axial", 62.0, quiet_constraint, margin["score"])
        assert margin["label"] in {"Moderate", "Tight", "High"}
        assert acoustic["label"] == "High"


class TestBaljePhysics:
    @pytest.mark.parametrize("ns", [0.10, 0.30, 0.80, 1.80, 3.50, 8.0])
    def test_cordier_ds_is_finite_and_positive(self, ns):
        ds = cordier_ds(ns)
        assert ds > 0.0
        assert ds < 30.0

    def test_balje_eta_family_peaks_near_family_optimum(self):
        """BC's eta should peak near Ns=0.8 on its own ridge."""
        ds_opt = cordier_ds(0.8)
        peak = balje_eta_family("centrifugal_bc", 0.8, ds_opt)
        off_ridge = balje_eta_family("centrifugal_bc", 0.8, ds_opt * 1.8)
        off_ns = balje_eta_family("centrifugal_bc", 2.5, cordier_ds(2.5))
        assert peak > off_ridge
        assert peak > off_ns
        assert peak == pytest.approx(0.85, abs=0.01)

    def test_balje_eta_envelope_equals_cordier_efficiency_on_ridge(self):
        for ns in (0.30, 0.80, 1.80, 3.50):
            ds_opt = cordier_ds(ns)
            assert balje_eta_envelope(ns, ds_opt) == pytest.approx(cordier_efficiency(ns))

    def test_balje_eta_envelope_never_exceeds_ceiling(self):
        for ns in (0.08, 0.5, 1.0, 2.0, 5.0, 12.0):
            for ds in (0.4, 1.0, 3.0, 8.0):
                value = balje_eta_envelope(ns, ds)
                assert 0.0 <= value <= 0.88

    def test_generate_balje_field_shape_and_values(self):
        field = generate_balje_field(resolution=24)
        assert len(field["ns"]) == 24
        assert len(field["ds"]) == 24
        assert len(field["z"]) == 24
        assert all(len(row) == 24 for row in field["z"])
        flat = [v for row in field["z"] for v in row]
        assert max(flat) <= 0.88
        assert min(flat) >= 0.0

    def test_family_anchors_lie_on_cordier_line(self):
        anchors = family_anchors()
        assert len(anchors) == 4
        for anchor in anchors:
            assert anchor["ds"] == pytest.approx(cordier_ds(anchor["ns"]), rel=1e-6)
            assert 0.0 < anchor["eta"] <= 0.88

    def test_balje_payload_is_in_full_analysis(self):
        data = full_analysis(flow_m3s=1.0, pressure_pa=500.0)
        assert "balje" in data
        balje = data["balje"]
        assert "field" in balje and "ns" in balje["field"]
        assert "family_anchors" in balje and len(balje["family_anchors"]) == 4
        assert balje["off_ridge_beta"] > 0.0
        assert balje["efficiency_ceiling"] == pytest.approx(0.88, abs=0.001)


class TestTipSpeedFit:
    def test_tip_speed_fit_uses_per_family_thresholds(self):
        """Axial permits higher tip speed than FC centrifugal, so the same
        45 m/s reading should score better for axial than for FC."""
        from pycalcs.fan_selection import _tip_speed_fit
        fc_score = _tip_speed_fit(45.0, "centrifugal_fc")
        axial_score = _tip_speed_fit(45.0, "axial")
        assert axial_score > fc_score


class TestCandidateSignals:
    def test_candidate_carries_mach_reynolds_sound_signals(self):
        data = full_analysis(flow_m3s=1.0, pressure_pa=500.0)
        best = data["comparison"][0]
        assert "tip_mach" in best and best["tip_mach"] is not None
        assert "tip_reynolds" in best and best["tip_reynolds"] > 0
        assert "sound_power_index_db" in best and best["sound_power_index_db"] is not None

    def test_fc_candidate_carries_hump_warning(self):
        data = full_analysis(flow_m3s=1.0, pressure_pa=500.0)
        fc = next(c for c in data["comparison"] if c["type_id"] == "centrifugal_fc")
        assert fc["fc_hump"] is not None
        assert "hump" in fc["fc_hump"]["summary"].lower()


class TestRadialBranch:
    def test_backward_curved_is_default_engineering_bias(self):
        branch = recommend_radial_subtype(
            specific_speed_value=0.8,
            predicted_diameter_m=0.55,
            speed_rpm=1200.0,
            radial_passage_fit=0.75,
        )
        assert branch["leader"]["type_id"] == "centrifugal_bc"

    def test_forward_curved_can_win_for_compact_low_speed_case(self):
        branch = recommend_radial_subtype(
            specific_speed_value=0.45,
            predicted_diameter_m=0.32,
            speed_rpm=650.0,
            radial_passage_fit=0.7,
        )
        assert branch["leader"]["type_id"] == "centrifugal_fc"
