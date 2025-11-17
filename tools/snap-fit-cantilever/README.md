# Cantilever Snap-Fit Calculator

## Purpose

This agent evaluates a rectangular cantilever snap during installation, in-service engagement, and removal. It follows the methodology published in the **BASF Snap-Fit Design Manual (2016)** to:

- Predict the spring constant of the snap arm and the deflection required to clear an undercut.
- Estimate installer effort by combining beam theory with a frictional ramp model for the lead-in face.
- Check service loads, retention force, and available strain margin against an allowable design limit.
- Provide transparent, educational output with substituted LaTeX equations for each critical quantity.

## Requirements

### Inputs

- Free length, thickness, and width of the rectangular cantilever (metres).
- Peak deflection required during installation, residual deflection in service, and deflection required for removal (metres).
- Material tensile modulus (Pascals) and allowable surface strain (unitless).
- Lead-in angle and release face angle measured from the direction of travel (degrees).
- Coefficient of sliding friction between the hook and the mating component.

### Outputs

- Tip stiffness, transverse forces, axial user forces, stresses, and strains for install, service, and removal.
- Allowable deflection derived from the strain limit and the resulting safety factor.
- Substituted equation strings for the primary results so users can verify each step.

### Assumptions & Limitations

- Small-deflection Euler–Bernoulli beam behaviour with a constant rectangular cross-section.
- Linear elastic material response; allowable strain should be selected to keep the snap below its elastic limit.
- Angles that produce `cos(θ) - μ·sin(θ) ≤ 0` are considered self-locking and will raise an error.
- Thermal effects, creep, and geometric stiffening are not included.

### References

- BASF Corporation, *Designing with Plastics: Snap-Fit Joints for Plastics – A Design Manual*, 2016.
