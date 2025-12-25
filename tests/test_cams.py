"""
Tests for the translating roller cam kinematics module.
"""

import math

import pytest

from pycalcs import cams


def test_get_cam_catalog():
    """Catalog contains expected motion laws."""
    catalog = cams.get_cam_catalog()
    motion_laws = catalog.get("motion_laws", {})
    assert "cycloidal" in motion_laws
    assert "simple_harmonic" in motion_laws
    assert "poly_3_4_5" in motion_laws
    assert "poly_4_5_6_7" in motion_laws


@pytest.mark.parametrize(
    "motion_law, expect_zero_accel, expect_zero_jerk",
    [
        ("cycloidal", True, False),
        ("simple_harmonic", False, False),
        ("poly_3_4_5", True, False),
        ("poly_4_5_6_7", True, True),
    ],
)
def test_rise_boundary_conditions(motion_law, expect_zero_accel, expect_zero_jerk):
    """Start/end of rise should meet boundary conditions for each motion law."""
    lift = 10.0
    segments = [
        {"type": "rise", "motion_law": motion_law, "lift_mm": lift, "duration_deg": 180.0},
        {"type": "fall", "motion_law": motion_law, "lift_mm": lift, "duration_deg": 180.0},
    ]
    results = cams.analyze_cam_profile(segments, 50.0, 5.0, 100.0)

    # Start of rise
    assert results["displacement"][0] == pytest.approx(0.0)
    assert results["velocity"][0] == pytest.approx(0.0)

    # End of rise
    end_index = 180
    assert results["displacement"][end_index] == pytest.approx(lift)
    assert results["velocity"][end_index] == pytest.approx(0.0)

    if expect_zero_accel:
        assert results["acceleration"][0] == pytest.approx(0.0)
        assert results["acceleration"][end_index] == pytest.approx(0.0)
    if expect_zero_jerk:
        assert results["jerk"][0] == pytest.approx(0.0)
        assert results["jerk"][end_index] == pytest.approx(0.0)


def test_cycloidal_midpoint():
    """Check cycloidal midpoint kinematics for a rise segment."""
    lift = 10.0
    omega_rpm = 120.0
    omega_rad_s = omega_rpm * 2.0 * math.pi / 60.0

    segments = [
        {"type": "rise", "motion_law": "cycloidal", "lift_mm": lift, "duration_deg": 180.0},
        {"type": "fall", "motion_law": "cycloidal", "lift_mm": lift, "duration_deg": 180.0},
    ]
    results = cams.analyze_cam_profile(segments, 50.0, 5.0, omega_rpm)

    mid_index = 90
    beta_rad = math.radians(180.0)
    expected_s = lift / 2.0
    expected_v = (2.0 * lift / beta_rad) * omega_rad_s
    expected_a = 0.0

    assert results["displacement"][mid_index] == pytest.approx(expected_s)
    assert results["velocity"][mid_index] == pytest.approx(expected_v)
    assert results["acceleration"][mid_index] == pytest.approx(expected_a)


def test_shm_midpoint():
    """Check SHM midpoint kinematics for a rise segment."""
    lift = 10.0
    omega_rpm = 120.0
    omega_rad_s = omega_rpm * 2.0 * math.pi / 60.0

    segments = [
        {"type": "rise", "motion_law": "simple_harmonic", "lift_mm": lift, "duration_deg": 180.0},
        {"type": "fall", "motion_law": "simple_harmonic", "lift_mm": lift, "duration_deg": 180.0},
    ]
    results = cams.analyze_cam_profile(segments, 50.0, 5.0, omega_rpm)

    mid_index = 90
    beta_rad = math.radians(180.0)
    expected_s = lift / 2.0
    expected_v = (math.pi * lift / (2.0 * beta_rad)) * omega_rad_s
    expected_a = 0.0

    assert results["displacement"][mid_index] == pytest.approx(expected_s)
    assert results["velocity"][mid_index] == pytest.approx(expected_v)
    assert results["acceleration"][mid_index] == pytest.approx(expected_a)


def test_invalid_duration():
    """Total duration must be 360 degrees."""
    segments = [
        {"type": "rise", "motion_law": "cycloidal", "lift_mm": 10.0, "duration_deg": 90.0},
        {"type": "dwell", "duration_deg": 180.0},
    ]
    with pytest.raises(ValueError, match="Total duration of segments must be 360"):
        cams.analyze_cam_profile(segments, 50.0, 5.0, 100.0)


def test_net_lift_must_close():
    """Net lift must return to zero over a full revolution."""
    segments = [
        {"type": "rise", "motion_law": "cycloidal", "lift_mm": 10.0, "duration_deg": 360.0},
    ]
    with pytest.raises(ValueError, match="Net lift over 360 degrees must return to zero"):
        cams.analyze_cam_profile(segments, 50.0, 5.0, 100.0)


def test_cam_profile_offset_distance():
    """Cam surface should be offset from the pitch curve by the roller radius."""
    roller_radius = 6.0
    segments = [
        {"type": "rise", "motion_law": "poly_4_5_6_7", "lift_mm": 8.0, "duration_deg": 180.0},
        {"type": "fall", "motion_law": "poly_4_5_6_7", "lift_mm": 8.0, "duration_deg": 180.0},
    ]
    results = cams.analyze_cam_profile(segments, 40.0, roller_radius, 90.0)

    indices = [0, 60, 120, 180, 240, 300]
    for idx in indices:
        dx = results["pitch_curve_x"][idx] - results["cam_profile_x"][idx]
        dy = results["pitch_curve_y"][idx] - results["cam_profile_y"][idx]
        distance = math.hypot(dx, dy)
        assert distance == pytest.approx(roller_radius, rel=1e-6, abs=1e-6)

    assert results["min_cam_radius"] < results["min_pitch_radius"]
