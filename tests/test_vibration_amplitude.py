"""Tests for pycalcs/vibration_amplitude.py."""

import math

import pytest

from pycalcs.vibration_amplitude import (
    G_TO_MS2,
    calculate_vibration_amplitude,
)


def test_textbook_1g_at_60hz():
    """1 g peak at 60 Hz -> known velocity and displacement amplitudes.

    omega = 2*pi*60 = 376.99 rad/s
    a_pk = 9.80665 m/s^2
    v_pk = a/omega = 0.026013 m/s -> 18.394 mm/s RMS
    d_pk = a/omega^2 = 6.9002e-5 m -> 69.00 um peak -> 138.0 um pk-pk
    """
    r = calculate_vibration_amplitude("acceleration", 1.0, "g", "peak", 60.0)

    omega = 2 * math.pi * 60.0
    assert r["omega"] == pytest.approx(omega, rel=1e-9)

    v_pk = G_TO_MS2 / omega
    assert r["vel_rms_mms"] == pytest.approx(v_pk / math.sqrt(2) * 1000.0, rel=1e-9)
    assert r["vel_rms_mms"] == pytest.approx(18.394, rel=1e-3)

    d_pk = G_TO_MS2 / omega**2
    assert r["disp_peak_um"] == pytest.approx(d_pk * 1e6, rel=1e-9)
    assert r["disp_peak_um"] == pytest.approx(69.00, rel=1e-3)
    assert r["disp_pkpk_um"] == pytest.approx(138.0, rel=1e-3)

    # We entered acceleration as 1 g peak, so it must come back as 1 g peak.
    assert r["accel_peak_g"] == pytest.approx(1.0, rel=1e-12)


def test_convention_ratios_within_quantity():
    """The user-facing invariant: pk-pk = 2*peak and rms = peak/sqrt(2)."""
    r = calculate_vibration_amplitude("velocity", 7.0, "mm/s", "peak", 45.0)
    assert r["vel_pkpk_mms"] == pytest.approx(2.0 * r["vel_peak_mms"], rel=1e-12)
    assert r["vel_rms_mms"] == pytest.approx(r["vel_peak_mms"] / math.sqrt(2), rel=1e-12)

    r = calculate_vibration_amplitude("displacement", 50.0, "um", "peak", 10.0)
    assert r["disp_pkpk_um"] == pytest.approx(2.0 * r["disp_peak_um"], rel=1e-12)

    r = calculate_vibration_amplitude("acceleration", 3.0, "g", "peak", 100.0)
    assert r["accel_pkpk_g"] == pytest.approx(2.0 * r["accel_peak_g"], rel=1e-12)
    assert r["accel_rms_g"] == pytest.approx(r["accel_peak_g"] / math.sqrt(2), rel=1e-12)


def test_input_convention_normalizes_to_same_signal():
    """Same physical signal entered in different conventions -> same output.

    A 20 um pk-pk displacement is the same signal as 10 um peak.
    """
    from_pkpk = calculate_vibration_amplitude("displacement", 20.0, "um", "pkpk", 25.0)
    from_peak = calculate_vibration_amplitude("displacement", 10.0, "um", "peak", 25.0)
    from_rms = calculate_vibration_amplitude(
        "displacement", 10.0 / math.sqrt(2), "um", "rms", 25.0
    )
    for key in ("vel_rms_mms", "accel_peak_g", "disp_pkpk_um"):
        assert from_pkpk[key] == pytest.approx(from_peak[key], rel=1e-9)
        assert from_rms[key] == pytest.approx(from_peak[key], rel=1e-9)


def test_roundtrip_consistency():
    """Feeding an output back in must reproduce the other quantities."""
    base = calculate_vibration_amplitude("displacement", 100.0, "um", "pkpk", 25.0)
    again = calculate_vibration_amplitude(
        "velocity", base["vel_rms_mms"], "mm/s", "rms", 25.0
    )
    assert again["disp_pkpk_um"] == pytest.approx(base["disp_pkpk_um"], rel=1e-9)
    assert again["accel_peak_g"] == pytest.approx(base["accel_peak_g"], rel=1e-9)


def test_metric_imperial_unit_agreement():
    """um pk-pk and mil pk-pk describe the same physical displacement."""
    r = calculate_vibration_amplitude("acceleration", 2.0, "g", "rms", 30.0)
    assert r["disp_pkpk_um"] == pytest.approx(r["disp_pkpk_mil"] * 25.4, rel=1e-9)


def test_zero_frequency_raises():
    with pytest.raises(ValueError):
        calculate_vibration_amplitude("velocity", 5.0, "mm/s", "rms", 0.0)


def test_bad_unit_for_quantity_raises():
    with pytest.raises(ValueError):
        calculate_vibration_amplitude("displacement", 5.0, "mm/s", "peak", 10.0)


def test_bad_quantity_raises():
    with pytest.raises(ValueError):
        calculate_vibration_amplitude("jerk", 5.0, "mm/s", "peak", 10.0)
