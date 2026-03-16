# Ring Fit Calculator

## Purpose

Analyze straight cylindrical press fits and shrink fits between a shaft and a hub. The tool reports elastic contact pressure, hub and shaft stresses, friction-based torque and axial slip capacity, thermal fit loss at operating temperature, and required assembly heating or cooling.

## Core Workflow

1. Enter shaft geometry, hub geometry, fit length, and the minimum / nominal / maximum diametral interference.
2. Select shaft and hub materials, review the displayed material properties, or switch either component to custom properties.
3. Enter service friction, reference / assembly / operating temperatures, and optional applied torque / axial load.
4. Review:
   - reference, assembly, and operating pressure
   - hub and shaft surface stresses at the governing locations
   - torque and axial slip capacity
   - actual assembly clearance at the user-entered hub temperature
   - required hub-only, shaft-only, and combined assembly temperatures
   - compliance factors and stress / temperature sensitivity visuals

## Scope

### Included

- Straight cylindrical shaft-hub fits
- Solid or hollow shafts
- Thick-walled hub/ring elasticity
- Minimum / nominal / maximum interference analysis
- Reference, assembly, and operating temperature states
- Operating-temperature interference loss
- Uniform-pressure friction torque and axial capacity
- Thermal assembly estimates for heating, cooling, or combined strategy
- Cross-section and radial stress-distribution visuals

### Not Included

- Plastic press fits
- Tapered fits
- Split clamps and shrink discs
- Keyways, grooves, serrations, and local stress risers
- Fretting fatigue or micro-slip life
- Detailed thermal gradients or transient heat-up modeling

## Model Notes

- Pressure is calculated from the combined elastic compliance of the shaft and hub using the standard thick-cylinder interference-fit treatment used in Shigley's Mechanical Engineering Design.
- Stress reporting uses Lamé radial and hoop stresses at the relevant member surfaces together with a plane-stress von Mises check.
- Slip capacity assumes uniform interface pressure and a single effective friction coefficient over the full contact length.
- Operating interference is adjusted using differential free thermal expansion:

  `delta_op = delta_ref - d (alpha_h - alpha_s) DeltaT`

- If operating interference becomes zero or negative, the tool reports fit loss and sets operating pressure to zero.

## Intended Use

- Early design
- Tolerance studies
- Assembly planning
- Quick verification against hand calculations
- Educational exploration of how stiffness ratio, interference, friction, temperature, and member geometry interact

## References

- Shigley's Mechanical Engineering Design, interference-fit / press-fit treatment
- Classical Lamé thick-cylinder stress relations
