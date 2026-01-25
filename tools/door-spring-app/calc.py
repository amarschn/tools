# calc.py - Legacy compatibility wrapper
"""
DEPRECATED: This module is maintained for backward compatibility only.
New code should import from pycalcs.gas_springs instead.

The main calculation logic has moved to pycalcs/gas_springs.py which provides:
- Proper moment equilibrium analysis
- Interactive visualization support
- Spring recommendation functionality
- Comprehensive geometry calculations

This wrapper maintains the old trapdoor_calculate() function signature
for any existing code that depends on it.
"""
import sys
import os

# Add parent directory to path for pycalcs import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pycalcs.gas_springs import (
    analyze_mechanism,
    recommend_spring,
    calculate_door_moment,
    calculate_spring_geometry,
)


def trapdoor_calculate(
    mass_door,
    length_door,
    open_angle,
    door_mount_frac,
    cab_mount_x,
    cab_mount_y,
    num_springs,
    spring_nominal,
    spring_variation,
    handle_frac
):
    """
    Legacy function for backward compatibility.

    Maps old parameter names to new analyze_mechanism function.
    """
    result = analyze_mechanism(
        door_mass=mass_door,
        door_length=length_door,
        cg_fraction=0.5,  # Assume uniform door
        door_mount_fraction=door_mount_frac,
        frame_mount_x=cab_mount_x,
        frame_mount_y=cab_mount_y,
        spring_force=spring_nominal,
        open_angle=open_angle,
        closed_angle=0.0,
        hand_position_fraction=handle_frac,
        num_springs=int(num_springs),
        angle_step=1.0
    )

    # Map new result format to old format for compatibility
    return {
        "minLen": result["spring_compressed"],
        "maxLen": result["spring_extended"],
        "stroke": result["spring_stroke"],
        "maxForce": spring_nominal * num_springs,
        "maxHandleForce": max(abs(result["max_hand_force"]), abs(result["min_hand_force"])),
        "angles": result["angles"],
        "springForces": [spring_nominal * num_springs] * len(result["angles"]),
        "handleForces": result["hand_forces"]
    }
