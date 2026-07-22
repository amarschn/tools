# Vibration Amplitude Converter (Displacement ↔ Velocity ↔ Acceleration)

Date: 2026-07-22

## Problem / gap

The site has two vibration tools — `vibration-severity-triage` (ISO 20816 /
VDI 3839) and `vibration-isolation-designer` — but **no converter** between the
three amplitude quantities a technician actually measures. In the field you
read acceleration in *g* off an accelerometer, but the ISO 20816 acceptance
limits are in *mm/s RMS* velocity, and shaft/proximity data is in *µm
peak-to-peak* displacement. Converting between them by hand (`v = ωd`,
`a = ω²d`, plus peak/RMS/pk-pk bookkeeping) is error-prone and a high-intent
search target ("g to mm/s vibration", "acceleration to velocity calculator").

This is a genuine gap: no plan, branch, or existing tool covers it.

## Scope (Phase 1 — single-frequency sinusoid)

The exact `v = ωd`, `a = ω²d` relations hold **only for single-frequency
sinusoidal motion**. That is the whole scope of v1, and the tool must state the
limitation prominently: for broadband/random signals you cannot convert without
the full spectrum. (A future phase could add per-band or PSD-integral
conversion, but that is out of scope here.)

### Inputs
- **Quantity you have**: displacement / velocity / acceleration
- **Value** + **unit** (metric + imperial):
  - displacement: µm, mm, mil, in
  - velocity: mm/s, in/s, m/s
  - acceleration: g, m/s², in/s²
- **Amplitude convention**: peak (0-pk), RMS, peak-to-peak
- **Frequency** (Hz) — with an optional RPM helper (÷60)

### Outputs (all three quantities, common conventions, metric + imperial)
- Displacement — µm pk-pk, mil pk-pk
- Velocity — mm/s RMS, in/s peak
- Acceleration — g peak, m/s² RMS
- ω (rad/s) shown as the conversion basis

### Math
```
ω = 2πf
peak_in  = value × {peak:1, pkpk:0.5, rms:√2}   # normalize to zero-to-peak
convert quantity → SI peak (d_pk [m], v_pk [m/s], or a_pk [m/s²])
if given d:  v_pk = ω·d_pk,      a_pk = ω²·d_pk
if given v:  d_pk = v_pk/ω,      a_pk = ω·v_pk
if given a:  d_pk = a_pk/ω²,     v_pk = a_pk/ω
# then re-express each SI peak in every output unit/convention
# (rms = pk/√2, pkpk = 2·pk)
```
Errors: `frequency ≤ 0` → ValueError (division by zero for v/a inputs).

## Deliverables
- `pycalcs/vibration_amplitude.py` — `calculate_vibration_amplitude(...)`
- `tests/test_vibration_amplitude.py` — nominal + textbook-value cases
- `tools/vibration-amplitude-converter/index.html` (from `example_tool`
  template; live recalc on input change; light/dark + settings per Release
  Checklist)
- `tools/vibration-amplitude-converter/README.md`
- `catalog.json` entry + `generate_sitemap.py` / `inject_seo_meta.py`
- Cross-link to/from `vibration-severity-triage`

## Verification anchors (textbook)
- 1 g peak @ 60 Hz → v_pk = 9.80665/(2π·60) = 0.02601 m/s = 26.0 mm/s peak
  → 18.4 mm/s RMS; d_pk = a/ω² = 6.90e-5 m → 69.0 µm peak → 138 µm pk-pk.
- Consistency: feeding any one output back in reproduces the others.

Tool stays **Experimental** (no `human-verified` tag) until Drew spot-checks.
