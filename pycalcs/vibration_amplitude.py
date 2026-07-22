"""
Single-frequency vibration amplitude conversions.

Converts a sinusoidal vibration amplitude between displacement, velocity, and
acceleration, and between the peak / RMS / peak-to-peak conventions, at a given
frequency. The exact relations used here (v = omega * d, a = omega**2 * d) hold
ONLY for single-frequency (sinusoidal) motion; broadband or random signals
cannot be converted this way without the full spectrum.
"""

from __future__ import annotations

import math

G_TO_MS2 = 9.80665  # standard gravity (m/s^2)

# Multiply a value in the given unit by this to get SI (m, m/s, or m/s^2).
_DISP_TO_M = {"um": 1e-6, "mm": 1e-3, "m": 1.0, "mil": 25.4e-6, "in": 0.0254}
_VEL_TO_MS = {"mm/s": 1e-3, "um/s": 1e-6, "m/s": 1.0, "in/s": 0.0254}
_ACCEL_TO_MS2 = {"m/s2": 1.0, "mm/s2": 1e-3, "g": G_TO_MS2, "in/s2": 0.0254}

# Multiply a stated amplitude by this to get the zero-to-peak amplitude.
_AMPLITUDE_TO_PEAK = {"peak": 1.0, "rms": math.sqrt(2.0), "pkpk": 0.5}

_UNIT_TABLES = {
    "displacement": _DISP_TO_M,
    "velocity": _VEL_TO_MS,
    "acceleration": _ACCEL_TO_MS2,
}


def calculate_vibration_amplitude(
    input_quantity: str,
    input_value: float,
    input_unit: str,
    input_amplitude: str,
    frequency: float,
) -> dict[str, float]:
    """
    Converts a sinusoidal vibration amplitude between displacement, velocity,
    and acceleration at a single frequency.

    For pure sinusoidal motion the displacement, velocity, and acceleration
    amplitudes are locked together by the angular frequency omega = 2*pi*f:
    velocity peak = omega * displacement peak, and acceleration peak =
    omega**2 * displacement peak. This tool normalizes whatever you enter to a
    zero-to-peak SI amplitude, then re-expresses all three quantities in the
    common field units and amplitude conventions. The conversion is only valid
    for a single frequency; a broadband (random) signal has no single omega and
    cannot be converted without its spectrum.

    ---Parameters---
    input_quantity : str
        Which quantity you are entering: "displacement", "velocity", or
        "acceleration".
    input_value : float
        The measured amplitude magnitude, in the chosen unit and convention.
    input_unit : str
        Unit of the entered value. Displacement: um, mm, m, mil, in.
        Velocity: mm/s, um/s, m/s, in/s. Acceleration: m/s2, mm/s2, g, in/s2.
    input_amplitude : str
        Amplitude convention of the entered value: "peak" (zero-to-peak),
        "rms", or "pkpk" (peak-to-peak).
    frequency : float
        Vibration frequency in hertz (Hz). Must be greater than zero.

    ---Returns---
    disp_pkpk_um : float
        Displacement amplitude, micrometres, peak-to-peak.
    disp_pkpk_mil : float
        Displacement amplitude, mils (0.001 in), peak-to-peak.
    vel_rms_mms : float
        Velocity amplitude, millimetres per second, RMS.
    vel_peak_ips : float
        Velocity amplitude, inches per second, peak (zero-to-peak).
    accel_peak_g : float
        Acceleration amplitude, multiples of g, peak (zero-to-peak).
    accel_rms_ms2 : float
        Acceleration amplitude, metres per second squared, RMS.
    omega : float
        Angular frequency used for the conversion, radians per second.

    ---LaTeX---
    \\omega = 2\\pi f
    v_{pk} = \\omega\\, d_{pk}
    a_{pk} = \\omega^2 d_{pk}
    """
    quantity = str(input_quantity).strip().lower()
    unit = str(input_unit).strip()
    amplitude = str(input_amplitude).strip().lower()

    if quantity not in _UNIT_TABLES:
        raise ValueError(
            f"input_quantity must be displacement, velocity, or acceleration "
            f"(got '{input_quantity}')."
        )
    unit_table = _UNIT_TABLES[quantity]
    if unit not in unit_table:
        raise ValueError(
            f"Unit '{unit}' is not valid for {quantity}. "
            f"Choose one of: {', '.join(unit_table)}."
        )
    if amplitude not in _AMPLITUDE_TO_PEAK:
        raise ValueError(
            f"input_amplitude must be peak, rms, or pkpk (got '{input_amplitude}')."
        )

    value = abs(float(input_value))
    freq = float(frequency)
    if freq <= 0:
        raise ValueError("frequency must be greater than zero.")

    omega = 2.0 * math.pi * freq

    # Normalize the entered value to a zero-to-peak SI amplitude of its quantity.
    peak_si = value * _AMPLITUDE_TO_PEAK[amplitude] * unit_table[unit]

    # Resolve the three zero-to-peak SI amplitudes from whichever was given.
    if quantity == "displacement":
        disp_pk = peak_si
        vel_pk = omega * disp_pk
        accel_pk = omega * omega * disp_pk
    elif quantity == "velocity":
        vel_pk = peak_si
        disp_pk = vel_pk / omega
        accel_pk = omega * vel_pk
    else:  # acceleration
        accel_pk = peak_si
        vel_pk = accel_pk / omega
        disp_pk = accel_pk / (omega * omega)

    sqrt2 = math.sqrt(2.0)

    return {
        "disp_pkpk_um": (disp_pk * 2.0) / _DISP_TO_M["um"],
        "disp_pkpk_mil": (disp_pk * 2.0) / _DISP_TO_M["mil"],
        "vel_rms_mms": (vel_pk / sqrt2) / _VEL_TO_MS["mm/s"],
        "vel_peak_ips": vel_pk / _VEL_TO_MS["in/s"],
        "accel_peak_g": accel_pk / _ACCEL_TO_MS2["g"],
        "accel_rms_ms2": accel_pk / sqrt2,
        "omega": omega,
        "subst_disp_pkpk_um": (
            f"d_{{pk\\text{{-}}pk}} = {disp_pk * 2.0 / _DISP_TO_M['um']:.4g}\\ \\mu m"
        ),
        "subst_vel_rms_mms": (
            f"v_{{rms}} = {vel_pk / sqrt2 / _VEL_TO_MS['mm/s']:.4g}\\ mm/s"
        ),
        "subst_accel_peak_g": (
            f"a_{{pk}} = {accel_pk / _ACCEL_TO_MS2['g']:.4g}\\ g"
        ),
        "subst_omega": f"\\omega = 2\\pi \\times {freq:.4g} = {omega:.4g}\\ rad/s",
    }
