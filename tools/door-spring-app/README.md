# Gas Spring Calculator

Design and analyze gas springs (gas struts) for hinged panels, trap doors, hatches, and lids.

## Features

- **Automatic spring sizing**: Enter door mass and dimensions, get recommended spring force and stroke
- **Moment equilibrium analysis**: See how door moment and spring moment balance across the full range of motion
- **Interactive visualization**: Drag mounting points to adjust geometry in real-time
- **Hand force analysis**: Understand how much effort is needed to operate the door at any angle
- **Physics explanation**: Background tab explains the math and provides design guidelines

## Common Applications

- Truck bed covers and tonneau lids
- Heavy trap doors and floor hatches
- Equipment enclosure lids
- Murphy beds and fold-down furniture
- Marine hatches and engine covers
- Tool box lids and storage compartments

## How It Works

The calculator uses moment equilibrium analysis to balance:

1. **Door Moment** (gravitational): M_door(θ) = m × g × L_cg × cos(θ)
2. **Spring Moment**: M_spring(θ) = n × F × r_⊥(θ)

Where:
- m = door mass (kg)
- g = gravitational acceleration (9.81 m/s²)
- L_cg = distance from hinge to center of gravity (m)
- θ = door angle from horizontal (degrees)
- n = number of springs
- F = force per spring (N)
- r_⊥ = perpendicular lever arm (varies with angle)

The optimal spring force minimizes the peak hand force required across the full range of motion.

## Input Parameters

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| Door Mass | Total mass of door/panel | 5-50 kg |
| Door Length | Hinge to free edge distance | 0.3-1.5 m |
| Open Angle | Maximum opening angle | 60-110° |
| CG Position | Center of gravity fraction | 0.4-0.6 |
| Door Mount | Spring attachment on door | 0.5-0.9 |
| Frame Mount X | Horizontal offset from hinge | 0.1-0.5 m |
| Frame Mount Y | Vertical offset (negative = below) | -0.3 to 0.1 m |

## Output

- **Recommended Force**: Optimal force per spring (N)
- **Required Stroke**: Minimum spring stroke (mm)
- **Spring Dimensions**: Compressed and extended lengths
- **Hand Force Analysis**: Peak and position-specific hand forces

## Technical Implementation

- **Python module**: `pycalcs/gas_springs.py`
- **Tests**: `tests/test_gas_springs.py`
- **Frontend**: Standard project template with Chart.js visualization

## References

- Stabilus Gas Spring Design Guide
- Suspa Gas Spring Engineering Manual
- General mechanical engineering principles for moment equilibrium
