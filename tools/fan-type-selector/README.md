# Fan Type Selector

Architecture-level fan screening before detailed curve selection.

## Purpose

This tool answers the earlier question than catalog selection:

- Given a required flow and pressure rise, what kind of fan should I start with?
- How do axial, mixed-flow, forward-curved centrifugal, and backward-curved centrifugal options compare at the same duty point?
- What specific speed and Cordier-based wheel size does that duty imply?

It is designed as a Phase-0 triage tool. The output should narrow the search space before handing the problem into the Fan Curve Explorer for real candidate comparison.

## What The Tool Does

- Computes dimensionless specific speed `N_s` and specific diameter `D_s`
- Uses the Cordier correlation to estimate an efficient outer wheel diameter
- Converts that outer wheel diameter into a family-specific reference flow section:
  - Axial / mixed-flow: rotor annulus
  - Centrifugal: inlet eye annulus
- Applies family-default hub or eye ratios plus blockage factors to estimate:
  - Gross flow area
  - Effective flow area
  - Reference-section velocity
- Screens four candidate fan types:
  - Axial
  - Mixed-flow
  - Backward-curved centrifugal
  - Forward-curved centrifugal
- Supports optional machine constraints:
  - Fixed RPM
  - Fixed wheel diameter
- Supports optional family-aware geometry overrides:
  - Axial / mixed-flow hub ratio or hub diameter
  - Centrifugal eye ratio set or eye diameters
- Supports optional passage-geometry checks:
  - Target bulk velocity
  - Known passage area
- Splits radial recommendations into backward-curved vs forward-curved guidance
- Adds practical screening signals:
  - Packaging signature
  - Nominal hardware size suggestions
  - Drive recommendation spanning direct-drive induction, VFD induction, belt or gearbox reduction, and ECM / BLDC style direct drive
  - Acoustic proxy risk from tip speed, passage velocity, and architecture margin
  - Tip Mach check (flags duty points where the incompressible Cordier screen starts to break down, roughly above `M_tip ≈ 0.30`)
  - Tip Reynolds check (flags small or slow wheels where `Re_D < ~1e5` so the efficiency envelope no longer applies cleanly)
  - Madison-style sound-power screening index with per-family offsets, used for ranking only — not an AMCA 300 sound-power calculation
  - Forward-curved stall hump notice when the lead family is forward-curved centrifugal
  - Architecture margin inside each family's natural `N_s` band
- Hands the duty point and suggested family into the Fan Curve Explorer

## What The Tool Does Not Do

- Replace vendor fan curves
- Predict acoustics directly
- Perform AMCA certification calculations
- Solve full duct networks
- Design blade geometry

## Core Outputs

- Recommended family and candidate type
- Predicted wheel diameter
- Nearby nominal hardware sizes to check first
- Estimated RPM
- Estimated peak efficiency (capped at a 0.88 screening ceiling)
- Shaft power
- Tip speed, tip Mach, and tip Reynolds
- Drive recommendation
- Acoustic proxy risk plus Madison-style sound-power screening index
- Forward-curved stall-hump notice when the lead family is FC
- Architecture margin
- Packaging preview comparing predicted wheel size against the optional passage geometry
- Hardware audit showing modeled reference section, effective flow area, and reference velocity
- Geometry-override aware reference sections that state when family defaults have been replaced by user-imposed hub or eye dimensions
- Screening-decision audit showing how the family screen was made, why the top two separated, and why the weights are arranged the way they are
- Expandable calculation trace showing equations, substituted values, interpretation, and score provenance
- `N_s` and `D_s` as technical basis rather than the first thing forced onto the user
- Side-by-side comparison table for all four candidate types
- Work-file support:
  - `Save Inputs` writes a raw display-unit input file for reloading a screening setup later
  - `Export Analysis` writes a fuller package with normalized inputs, solver results, and recommendation summary
  - `Load Work` accepts either file type and can restore a saved analysis or reload inputs for a fresh solve

## Method Summary

The ranking is driven primarily by specific-speed fit. Estimated efficiency, tip-speed realism, and the optional passage geometry check adjust that recommendation. Passage geometry is now compared against a modeled fan-side reference area rather than only outer wheel diameter, which makes the packaging screen more physically meaningful. The practical signals are there to expose the usual real-world vetoes and tradeoffs, not to pretend the tool can replace a catalog, a noise test, or a real fan curve. Representative fan curves are shown only for family-shape comparison; they are not real catalog curves.

### Single Source of Truth for Balje Physics

All Balje-plane physics lives in `pycalcs.fan_selection`:

- `FAN_TYPES[type_id]` holds `ns_optimal`, `sigma_ln_ns`, `typical_peak_efficiency`, and per-family `tip_speed_quiet_ms` / `tip_speed_alert_ms` thresholds.
- `balje_eta_family(type_id, N_s, D_s)` evaluates the single-family Gaussian envelope.
- `balje_eta_envelope(N_s, D_s)` is the `max` over families, clamped at the screening ceiling (0.88).
- `cordier_efficiency(N_s)` delegates to the envelope on the Cordier ridge, so the score uses the same curve the plot shows.
- `generate_balje_field()` and `family_anchors()` produce the payload that `renderCordierPlot` consumes; the JS layer owns zero physics.

The 0.88 ceiling is deliberately below peak laboratory values — it is a *screening* ceiling for first-pass efficiency estimates, not a claim about best-in-class hardware.

### Reference-Section Asymmetry

Axial / mixed-flow families use a rotor annulus (outer wheel minus hub) as their reference flow section, while centrifugal families use the inlet eye annulus. The packaging check compares system passage area against that modeled reference section, not the outer wheel envelope. For axial fans this means a casing bore just slightly larger than the rotor can still score well even though the rotor annulus is modest; the tool reports the basis explicitly alongside every candidate so the asymmetry stays visible.

## References

- Balje, O.E. *Turbomachines: A Guide to Design, Selection, and Theory*
- Dixon, S.L. & Hall, C.A. *Fluid Mechanics and Thermodynamics of Turbomachinery*
- Eck, B. *Fans*
- ANSI/AMCA 210-25
- AMCA Publication 201-23
- DOE *Improving Fan System Performance Sourcebook*

## Workflow

Recommended use:

1. Enter the duty point.
2. Add RPM, diameter, or passage constraints if they are already known.
3. Read the recommendation and physical sizing first, then open the decision trace if you need to verify how the tool got there.
4. Use the comparison table and Cordier tab to check the alternatives and the dimensionless screening context.
5. Open the Fan Curve Explorer with the handoff button to compare real candidates.

## Work Files

The tool follows the same basic work-file pattern as the thermal tool:

- Saved input files:
  - `tool`
  - `type: "saved_inputs"`
  - `timestamp`
  - `inputs` using the raw display-unit form values
- Exported analysis packages:
  - `tool`
  - `version`
  - `timestamp`
  - `inputs` using normalized SI solver inputs
  - `results` containing the full analysis payload

The fan selector also includes `display_inputs` in exported analysis packages so a later import can restore the original form presentation cleanly even when the normalized solver inputs are all SI-based.
