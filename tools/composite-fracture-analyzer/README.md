# Composite Fracture Analyzer

Assess fracture risk and fatigue crack growth in fiber-reinforced polymer rotors under centrifugal loading.

## What It Does

Combines two tightly coupled analyses for rotating composite components:

1. **Static fracture assessment** - Computes the stress intensity factor K_I at a pre-existing crack and compares it to the material's fracture toughness K_IC to determine the fracture safety factor and critical crack size.

2. **Fatigue crack growth** - Integrates the Paris law (da/dN = C(DeltaK)^m) from the initial crack size to the critical crack size, yielding the number of load cycles to failure and a recommended inspection interval.

## Inputs

- **Geometry**: Solid disk, annular disk, or thin ring with inner/outer radius and thickness
- **Loading**: Rotational speed (RPM)
- **Crack definition**: Location radius, initial size, type (edge/through/surface/embedded), orientation
- **Material**: 6 presets (CFRP, GFRP, Aramid, PA6-GF30, PEEK-CF30, generic polymer) or custom
- **Expert mode**: Paris law constants, stress ratio R, design life, Poisson ratio, required safety factor

## Backend

- Python module: `pycalcs/fracture_mechanics.py`
- Main function: `analyze_fracture_and_crack_growth()`
- Tests: `tests/test_fracture_mechanics.py` (21 tests)

## Key Equations

- K_I = Y * sigma * sqrt(pi * a)
- SF = K_IC / K_I
- da/dN = C * (DeltaK)^m
- Geometry factors from Tada/Paris/Irwin handbook

## References

- T.L. Anderson, *Fracture Mechanics: Fundamentals and Applications*, 4th ed.
- Tada, Paris & Irwin, *The Stress Analysis of Cracks Handbook*, 3rd ed.
- Paris & Erdogan, "A Critical Analysis of Crack Propagation Laws", 1963
