# Generic Thermal Path Budget Tool

This tool solves steady-state thermal resistance networks when you know or can estimate path resistances, but do not yet have a geometry-specific sink or spreading model.

## Purpose

It is intended to answer:

- What temperature will each node in the thermal path reach?
- Which segment is dominating the rise from the source to ambient?
- What segment should be improved first?
- How low does one selected resistance need to be to meet a temperature target?

## Good Fits

- Junction -> case -> TIM -> sink -> ambient budgeting
- Housing or wall thermal paths with known interface and ambient-side resistance
- Dual path comparisons such as sink path versus PCB path
- Early concept studies before final sink geometry is known

## Included In This MVP

- Steady-state solving only
- One positive heat-input node
- One fixed-temperature boundary node
- Series chains
- Simple dual-path branching
- Direct resistance inputs
- TIM resistance from datasheet impedance per area
- TIM resistance from bondline thickness, conductivity, and area
- Simple 1D conduction slab resistance
- Required-resistance sizing for one selected unknown segment
- Segment sensitivity sweeps

## Not Included Yet

- Transient RC behavior
- Multiple independent heat sources
- Multiple fixed-temperature boundaries
- Arbitrary graph editing
- Native radiation segments
- 2D/3D spreading
- Geometry-specific heatsink correlations

## Modeling Notes

- This is a lumped thermal network tool. Every segment is treated as a scalar thermal resistance.
- If spreading inside a plate or housing dominates, this tool should be treated as approximate.
- If the sink geometry is known, the plate-fin heatsink designer is often a better follow-on check for the sink-to-ambient segment.
