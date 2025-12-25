# Cam Profile Generator (Experimental)

## Purpose
- Build translating roller cam profiles from motion segments.
- Visualize displacement, velocity, acceleration, jerk, pitch curve, and cam surface.
- Provide a progressive workflow from quick presets to detailed segment edits.

## Requirements
- Accept a segment sequence (rise/fall/dwell) that sums to 360 degrees.
- Support common motion laws: Cycloidal, Simple Harmonic, Polynomial 3-4-5, Polynomial 4-5-6-7.
- Compute follower SVAJ and the in-line translating roller cam surface.
- Plot kinematics and geometry with labeled axes, units, and legends.
- Use docstring-driven tooltips, glossaries, and equations.

## Notes
- Pressure angle and undercut checks are out of scope for the current prototype.
- Net lift must return to zero for a closed cam profile.

## References
- TBD.
