"""
Tests for pycalcs/vibration_severity.py
"""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pycalcs import vibration_severity


# =============================================================================
# HELPERS
# =============================================================================

def default_eval(**overrides):
    """Run evaluate_vibration with sensible defaults, allowing field overrides."""
    defaults = dict(
        machine_type="pump",
        nominal_power_kw=75.0,
        rated_rpm=1480.0,
        operating_rpm=1480.0,
        bearing_type_de="rolling_element",
        mounting="rigid",
        measurement_direction="radial_h",
        vibration_quantity="velocity_rms",
        measured_value=3.2,
        machine_group="2",
        zone_ab=3.5,
        zone_bc=7.1,
        zone_cd=11.2,
    )
    defaults.update(overrides)
    return vibration_severity.evaluate_vibration(**defaults)


# =============================================================================
# ZONE CLASSIFICATION
# =============================================================================

class TestZoneClassification:
    def test_zone_a(self):
        result = default_eval(measured_value=2.0)
        assert result["zone"] == "A"
        assert result["zone_css_class"] == "success"

    def test_zone_b(self):
        result = default_eval(measured_value=5.0)
        assert result["zone"] == "B"
        assert result["zone_css_class"] == "success"

    def test_zone_c(self):
        result = default_eval(measured_value=9.0)
        assert result["zone"] == "C"
        assert result["zone_css_class"] == "warning"

    def test_zone_d(self):
        result = default_eval(measured_value=15.0)
        assert result["zone"] == "D"
        assert result["zone_css_class"] == "danger"

    def test_zone_boundary_ab_exact(self):
        """Value exactly at A/B boundary is still Zone A (≤ limit → zone below)."""
        result = default_eval(measured_value=3.5)
        assert result["zone"] == "A"

    def test_zone_boundary_cd_exact(self):
        """Value exactly at C/D boundary is Zone C (≤ limit → zone below)."""
        result = default_eval(measured_value=11.2)
        assert result["zone"] == "C"

    def test_custom_limits(self):
        result = vibration_severity.evaluate_vibration(
            machine_type="motor_medium",
            nominal_power_kw=110.0,
            rated_rpm=1500.0,
            operating_rpm=1500.0,
            bearing_type_de="rolling_element",
            mounting="rigid",
            measurement_direction="radial_v",
            vibration_quantity="velocity_rms",
            measured_value=4.0,
            machine_group="1",
            zone_ab=2.3,
            zone_bc=4.5,
            zone_cd=7.1,
        )
        assert result["zone"] == "C"


# =============================================================================
# UNIT CONVERSION
# =============================================================================

class TestUnitConversion:
    def test_velocity_rms_no_conversion(self):
        result = default_eval(measured_value=3.2, vibration_quantity="velocity_rms")
        assert result["value_for_comparison"] == pytest.approx(3.2)
        assert result["conversion_note"] == ""

    def test_displacement_pp_conversion(self):
        # At 1480 RPM, f = 1480/60 = 24.67 Hz
        # v_rms = π * f * D_pp (µm * 1e-3) / sqrt(2)
        f = 1480 / 60
        d_pp_um = 100.0  # µm
        expected_v = (3.14159265 * f * d_pp_um * 1e-3) / (2 ** 0.5)
        result = default_eval(
            measured_value=d_pp_um,
            vibration_quantity="displacement_pp",
            operating_rpm=1480.0,
        )
        assert result["value_for_comparison"] == pytest.approx(expected_v, rel=0.01)
        assert "converted" in result["conversion_note"].lower()

    def test_accel_rms_conversion(self):
        # v_rms = a_rms / (2π f) * 1000
        f = 1480 / 60
        a_rms = 2.5  # m/s²
        expected_v = (a_rms / (2 * 3.14159265 * f)) * 1000
        result = default_eval(
            measured_value=a_rms,
            vibration_quantity="accel_rms",
            operating_rpm=1480.0,
        )
        assert result["value_for_comparison"] == pytest.approx(expected_v, rel=0.01)


# =============================================================================
# DELTA & TREND
# =============================================================================

class TestDeltaAndTrend:
    def test_delta_baseline(self):
        result = default_eval(measured_value=4.0, baseline_value=3.0)
        assert result["delta_baseline_abs"] == pytest.approx(1.0, abs=1e-4)
        assert result["delta_baseline_pct"] == pytest.approx(33.3, abs=0.5)

    def test_delta_increasing_trend(self):
        result = default_eval(measured_value=5.0, previous_value=4.0)
        assert result["trend"] == "increasing"

    def test_delta_decreasing_trend(self):
        result = default_eval(measured_value=4.0, previous_value=5.0)
        assert result["trend"] == "decreasing"

    def test_delta_stable_trend(self):
        result = default_eval(measured_value=4.0, previous_value=4.1)
        assert result["trend"] == "stable"

    def test_no_previous_insufficient_data(self):
        result = default_eval(measured_value=4.0)
        assert result["trend"] == "insufficient_data"

    def test_large_baseline_delta_triggers_warning(self):
        result = default_eval(measured_value=5.0, baseline_value=3.0)
        warnings = json.loads(result["scope_warnings_json"])
        assert any("baseline" in w.lower() or "%" in w for w in warnings)


# =============================================================================
# FAULT SCORING
# =============================================================================

class TestFaultScoring:
    def test_fault_matches_returned(self):
        result = default_eval()
        matches = json.loads(result["fault_matches_json"])
        assert len(matches) > 0

    def test_ranks_are_sequential(self):
        result = default_eval()
        matches = json.loads(result["fault_matches_json"])
        ranks = [m["rank"] for m in matches]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_axial_direction_boosts_misalignment(self):
        result_axial = default_eval(measurement_direction="axial")
        result_radial = default_eval(measurement_direction="radial_h")
        matches_axial = json.loads(result_axial["fault_matches_json"])
        matches_radial = json.loads(result_radial["fault_matches_json"])

        def find_score(matches, fault_id):
            for m in matches:
                if m["fault_id"] == fault_id:
                    return m["score"]
            return 0

        axial_misalign_score = find_score(matches_axial, "misalignment_angular")
        radial_misalign_score = find_score(matches_radial, "misalignment_angular")
        assert axial_misalign_score > radial_misalign_score

    def test_bearing_defect_excluded_for_fluid_film(self):
        result = default_eval(bearing_type_de="fluid_film")
        matches = json.loads(result["fault_matches_json"])
        bearing_ids = [m["fault_id"] for m in matches]
        assert "bearing_defect" not in bearing_ids

    def test_bearing_defect_included_for_rolling_element(self):
        result = default_eval(bearing_type_de="rolling_element")
        matches = json.loads(result["fault_matches_json"])
        bearing_ids = [m["fault_id"] for m in matches]
        assert "bearing_defect" in bearing_ids

    def test_electrical_fault_excluded_for_pump(self):
        result = default_eval(machine_type="pump")
        matches = json.loads(result["fault_matches_json"])
        ids = [m["fault_id"] for m in matches]
        assert "electrical" not in ids

    def test_confidence_labels_valid(self):
        result = default_eval()
        matches = json.loads(result["fault_matches_json"])
        valid = {"High", "Medium", "Low", "Possible"}
        for m in matches:
            assert m["confidence"] in valid


# =============================================================================
# BEARING DEFECT FREQUENCIES
# =============================================================================

class TestBearingDefectFrequencies:
    def test_calculation(self):
        freqs = vibration_severity.calculate_bearing_defect_frequencies(
            rpm=1480.0,
            roller_count=9,
            pitch_diameter_mm=52.0,
            roller_diameter_mm=10.0,
            contact_angle_deg=0.0,
        )
        assert "bpfo_hz" in freqs
        assert "bpfi_hz" in freqs
        assert "bsf_hz" in freqs
        assert "ftf_hz" in freqs
        # BPFO should be between FTF and shaft frequency bounds
        assert freqs["bpfo_hz"] > freqs["ftf_hz"]
        assert freqs["bpfi_hz"] > freqs["bpfo_hz"]

    def test_bpfo_bpfi_relationship(self):
        """BPFO + BPFI should equal N_r * shaft_hz."""
        freqs = vibration_severity.calculate_bearing_defect_frequencies(
            rpm=1500.0,
            roller_count=8,
            pitch_diameter_mm=50.0,
            roller_diameter_mm=9.0,
            contact_angle_deg=0.0,
        )
        nr = 8
        expected_sum = nr * freqs["shaft_hz"]
        assert freqs["bpfo_hz"] + freqs["bpfi_hz"] == pytest.approx(expected_sum, rel=1e-4)

    def test_bearing_freqs_in_result(self):
        result = default_eval(
            bearing_roller_count=9.0,
            bearing_pitch_dia_mm=52.0,
            bearing_roller_dia_mm=10.0,
            bearing_contact_angle_deg=0.0,
        )
        assert result["bearing_freqs_json"] != ""
        freqs = json.loads(result["bearing_freqs_json"])
        assert "bpfo_hz" in freqs

    def test_bearing_freqs_empty_without_geometry(self):
        result = default_eval()
        assert result["bearing_freqs_json"] == ""

    def test_invalid_roller_count_raises(self):
        with pytest.raises(ValueError):
            vibration_severity.calculate_bearing_defect_frequencies(
                rpm=1000, roller_count=2,
                pitch_diameter_mm=50, roller_diameter_mm=10, contact_angle_deg=0
            )


# =============================================================================
# SCOPE WARNINGS & APPLICABILITY
# =============================================================================

class TestScopeWarnings:
    def test_low_power_warning(self):
        result = default_eval(nominal_power_kw=10.0)
        warnings = json.loads(result["scope_warnings_json"])
        assert any("15 kW" in w for w in warnings)

    def test_out_of_range_rpm_warning(self):
        result = default_eval(rated_rpm=50.0)
        warnings = json.loads(result["scope_warnings_json"])
        assert any("120" in w or "15,000" in w or "15000" in w for w in warnings)

    def test_reciprocating_compressor_warning(self):
        result = default_eval(machine_type="compressor_reciprocating")
        warnings = json.loads(result["scope_warnings_json"])
        assert any("20816-8" in w or "reciprocating" in w.lower() for w in warnings)

    def test_applicable_standard_pump(self):
        result = default_eval(machine_type="pump")
        assert "ISO 20816-3" in result["applicable_standard"]

    def test_applicable_standard_gearbox(self):
        result = default_eval(machine_type="gearbox")
        assert "20816-9" in result["applicable_standard"]


# =============================================================================
# INPUT VALIDATION
# =============================================================================

class TestInputValidation:
    def test_negative_power_raises(self):
        with pytest.raises(ValueError):
            default_eval(nominal_power_kw=-10.0)

    def test_zero_measured_value_raises(self):
        with pytest.raises(ValueError):
            default_eval(measured_value=0.0)

    def test_invalid_machine_type_raises(self):
        with pytest.raises(ValueError):
            default_eval(machine_type="rocket_engine")

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            default_eval(measurement_direction="diagonal")

    def test_invalid_zone_order_raises(self):
        with pytest.raises(ValueError):
            default_eval(zone_ab=7.1, zone_bc=3.5, zone_cd=11.2)

    def test_invalid_bearing_type_raises(self):
        with pytest.raises(ValueError):
            default_eval(bearing_type_de="magnetic_levitation")


# =============================================================================
# REPORT GENERATION
# =============================================================================

class TestReport:
    def test_report_contains_zone(self):
        result = default_eval(measured_value=3.2)
        assert "Zone" in result["report_text"]
        assert result["zone"] in result["report_text"]

    def test_report_contains_disclaimer(self):
        result = default_eval()
        assert "DISCLAIMER" in result["report_text"]

    def test_next_steps_populated(self):
        result = default_eval()
        steps = json.loads(result["next_steps_json"])
        assert len(steps) > 0

    def test_zone_d_urgent_step(self):
        result = default_eval(measured_value=20.0)
        steps = json.loads(result["next_steps_json"])
        assert any("URGENT" in s or "shutdown" in s.lower() for s in steps)
