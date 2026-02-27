# Rotating Disk Hoop Stress (Prototype)

Estimate hoop, radial, and von Mises stresses in high-speed rotors using
closed-form rotating-disk equations from Shigley's Mechanical Engineering Design.

## Purpose

This prototype supports quick screening of burst-risk and speed margin for:

- Solid disks
- Annular disks
- Thin rings

It is intended for early design iteration and educational verification.

## Requirements

### Core Inputs

- Geometry type (`solid_disk`, `annular_disk`, `thin_ring`)
- Inner/outer radius
- Thickness
- Density
- Poisson ratio
- Speed
- Yield strength

### Outputs

- Maximum hoop stress
- Maximum radial stress
- Maximum von Mises stress
- Yield safety factor
- Allowable speed at required safety factor
- Stress profile vs radius for visualization
- Live rotor cross-section visualization with rotation axis

### Scope Notes

- Uniform thickness and homogeneous isotropic material
- Elastic closed-form model only
- Geometry scope is limited to solid disks, annular disks, and thin rings
- No thermal gradients, residual stress, blade attachment effects, or stress concentrations

## References

- Budynas, R. G., and Nisbett, J. K., *Shigley's Mechanical Engineering Design*,
  rotating rings/disks stress relations.
- Timoshenko, S. P., and Goodier, J. N., *Theory of Elasticity*,
  axisymmetric rotating disk solutions.
- Boresi, A. P., and Schmidt, R. J., *Advanced Mechanics of Materials*,
  plane-stress von Mises equivalent stress relation.
