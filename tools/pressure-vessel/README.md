# Pressure Vessel Quick Sizing

## Purpose
- Provide fast, thin-wall sizing for cylindrical and spherical pressure vessels under internal pressure.
- Support early design decisions and education, not code-compliant sizing.

## Inputs
- Geometry (cylinder or sphere)
- Internal pressure (MPa)
- Mean diameter (mm)
- Wall thickness (mm)
- Allowable stress (MPa)
- Safety factor (dimensionless)
- Joint efficiency E (0 to 1)
- Corrosion allowance (mm)

## Outputs
- Required thickness (mm) with corrosion allowance
- Hoop or membrane stress (MPa)
- Longitudinal stress (MPa) for cylinders
- Von Mises utilization ratio
- Thin-wall ratio t/r and validity status

## Assumptions
- Thin-wall membrane theory only (t/r <= 0.1)
- Uniform internal pressure and static loading
- Closed ends for cylinders
- Material is linear elastic, homogeneous, and isotropic
- No external pressure, thermal gradients, or local discontinuities
- Thickness input is net; corrosion allowance is added to required thickness

## When to Switch to Thick-Wall Methods
- t/r > 0.1 (or D/t < 20)
- High pressures or thick shells
- Significant external pressure or temperature effects
- Code compliance required (ASME Section VIII)

## References
- Shigley's Mechanical Engineering Design, 10th ed.
- Roark's Formulas for Stress and Strain, 7th ed.
