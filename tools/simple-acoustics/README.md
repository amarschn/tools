# Sound Level Calculator

## Purpose
Build fast, consistent sound level estimates. This tool converts between sound power level (SWL)
and sound pressure level (SPL), combines incoherent sources, and summarizes octave-band spectra
with optional A or C weighting.

## Requirements
- Convert SWL to SPL (and SPL to SWL) using point, line, or plane spreading models.
- Apply directivity factors and show geometric spreading loss.
- Combine multiple sources using logarithmic decibel addition.
- Accept octave-band inputs and report overall Z, A, or C weighted levels.
- Visualize SPL vs distance and octave-band spectra.

## Modeling Notes
- Spreading constants follow common ISO 9613 guidance for quick estimates.
- Directivity gain uses 10 log10(Q) for simple mounting conditions.
- Weighting offsets are octave-band approximations from IEC 61672.

## References
- ISO 9613-2: Acoustics - Attenuation of sound during propagation outdoors.
- IEC 61672-1: Electroacoustics - Sound level meters (frequency weighting).
- ISO 226: Normal equal-loudness-level contours.
- Bies, Hansen, and Zander. Engineering Noise Control (5th ed.).
