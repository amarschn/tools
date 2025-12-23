# Fastener and Bolt Torque Calculator_openai

## Purpose
- Estimate tightening torque from either a friction-based model or a nut-factor (K) approximation.
- Compute clamp load, tensile stress area, proof load utilization, and torque split between thread and bearing friction.
- Provide both SI and inch-pound outputs with visualization of torque vs clamp load.

## Requirements
- Use ISO metric or Unified thread geometry inputs with clear unit labels.
- Support direct clamp-load targets or percent-of-proof targets.
- Display numbered equations with variable legends and show references for standard values.
- Provide an exportable CSV of inputs and results.

## References
- NASA Fastener Design Manual (NASA SP-8007).
- Shigley, Mechanical Engineering Design, friction torque model for threaded fasteners.
- ISO 898-1 for proof strength guidance.
- ASME B1.1 for Unified thread geometry and tensile stress area formula.
