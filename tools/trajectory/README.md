# Projectile Trajectory Planner

## Purpose
- Provide a transparent, education-friendly calculator for planar projectile motion without aerodynamic drag.
- Surface intermediate quantities (component velocities, apex timing, impact conditions) so students can validate hand calculations.
- Visualise the trajectory with a quick-look plot that stays in sync with the Python source equations.

## Requirements
- Accept initial speed, launch angle, launch height, and gravity input in SI units.
- Derive horizontal/vertical velocity components, peak height, flight time, range, and impact conditions.
- Generate equation substitutions for every reported result to support step-by-step review.
- Produce sampled trajectory points so the frontend can render a scaled plot of the flight path.
- Source all calculation logic from `/pycalcs/ballistics.py` via Pyodide to maintain a single source of truth.
