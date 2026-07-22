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
    assert r["disp_pkpk_um"] == pytest.approx(d_pk * 2 * 1e6, rel=1e-9)
    assert r["disp_pkpk_um"] == pytest.approx(138.0, rel=1e-3)

    # We entered acceleration as 1 g peak, so it must come back as 1 g peak.
    assert r["accel_peak_g"] == pytest.approx(1.0, rel=1e-12)


def test_roundtrip_consistency():
    """Feeding an output back in must reproduce the other quantities."""
    base = calculate_vibration_amplitude("displacement", 100.0, "um", "pkpk", 25.0)

    # Take the velocity result and re-enter it; displacement/accel should match.
    again = calculate_vibration_amplitude(
        "velocity", base["vel_rms_mms"], "mm/s", "rms", 25.0
    )
    assert again["disp_pkpk_um"] == pytest.approx(base["disp_pkpk_um"], rel=1e-9)
    assert again["accel_peak_g"] == pytest.approx(base["accel_peak_g"], rel=1e-9)


def test_amplitude_convention_scaling():
    """RMS input equals peak/sqrt(2); pk-pk output is twice the peak."""
    peak_in = calculate_vibration_amplitude("velocity", 10.0, "mm/s", "peak", 50.0)
    rms_in = calculate_vibration_amplitude(
        "velocity", 10.0 / math.sqrt(2), "mm/s", "rms", 50.0
    )
    assert rms_in["disp_pkpk_um"] == pytest.approx(peak_in["disp_pkpk_um"], rel=1e-9)


def test_metric_imperial_unit_agreement():
    """um pk-pk and mil pk-pk describe the same physical displacement."""
    r = calculate_vibration_amplitude("acceleration", 2.0, "g", "rms", 30.0)
    # 1 mil = 25.4 um
    assert r["disp_pkpk_um"] == pytest.approx(r["disp_pkpk_mil"] * 25.4, rel=1e-9)


def test_zero_frequency_raises():
    with pytest.raises(ValueError):
        calculate_vibration_amplitude("velocity", 5.0, "mm/s", "rms", 0.0)


def test_bad_unit_for_quantity_raises():
    # mm/s is a velocity unit, not valid for displacement.
    with pytest.raises(ValueError):
        calculate_vibration_amplitude("displacement", 5.0, "mm/s", "peak", 10.0)


def test_bad_quantity_raises():
    with pytest.raises(ValueError):
        calculate_vibration_amplitude("jerk", 5.0, "mm/s", "peak", 10.0)
