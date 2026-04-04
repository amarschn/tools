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
- Estimated peak efficiency
- Shaft power
- Tip speed
- Drive recommendation
- Acoustic proxy risk
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
