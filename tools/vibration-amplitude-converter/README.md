# Vibration Amplitude Converter

Convert a vibration amplitude between **displacement**, **velocity**, and
**acceleration**, and between the **peak / RMS / peak-to-peak** conventions, at
a given frequency.

## Purpose

Field vibration data arrives in mismatched units: an accelerometer reads *g*,
ISO 20816 acceptance limits are in *mm/s RMS*, and proximity-probe shaft data is
in *µm peak-to-peak*. This tool does the `v = ωd`, `a = ω²d` conversion and the
peak/RMS/pk-pk bookkeeping in one step, showing all three quantities in both
metric and imperial units.

## Scope / assumptions

- **Single-frequency (sinusoidal) motion only.** The conversions are exact for a
  pure sinusoid at one frequency. Broadband or random signals have no single
  angular frequency ω and cannot be converted without their full spectrum.
- Amplitude conventions for a sinusoid are fixed ratios: `RMS = peak / √2`,
  `peak-to-peak = 2 × peak`.

## Inputs

- Quantity you have: displacement / velocity / acceleration
- Value + unit (displacement: µm, mm, mil, in · velocity: mm/s, in/s, m/s ·
  acceleration: g, m/s², in/s²)
- Amplitude convention: peak / RMS / peak-to-peak
- Frequency in Hz (with an RPM ÷ 60 helper)

## Outputs

- Displacement: µm pk-pk (and mil pk-pk)
- Velocity: mm/s RMS (and in/s peak)
- Acceleration: g peak (and m/s² RMS)
- ω = 2πf, the conversion basis

## Math

`pycalcs/vibration_amplitude.py :: calculate_vibration_amplitude` normalizes the
entry to a zero-to-peak SI amplitude, resolves the other two via ω = 2πf, then
re-expresses each in its common field convention.

## Related tools

- [Vibration Severity & Fault Triage](../vibration-severity-triage/): ISO 20816
  zone classification once you have velocity in mm/s.
- [Vibration Isolation Designer](../vibration-isolation-designer/)

## Status

Experimental. Pending human verification of the conversion outputs.
