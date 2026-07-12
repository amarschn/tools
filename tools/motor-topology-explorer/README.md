# Motor Topology Explainer/Explorer

## Purpose

This tool is an educational explorer for building intuition about common electric motor topologies. It explains what each topology is, why it exists, what tradeoffs distinguish it, and how later performance and control plots should be interpreted.

## Requirements

- Present the initial topology set from the project plan: surface-mount PMSM/BLDC, squirrel-cage induction, and permanent-magnet brushed DC.
- Load topology data from `pycalcs/motors.py` through Pyodide so the Python module remains the single source of truth.
- Show only the Overview tab in the first build step, with the remaining tabs visible as planned future surfaces.
- Keep advanced performance parameters as data defaults for later chart work, not as visible first-step inputs.
- Use progressive disclosure: one-sentence takeaway first, then description, facts, applications, pros/cons, controls, tradeoffs, and references.

## Scope Notes

This first skeleton does not size or select motors. It also does not predict performance yet. Later build steps add synthetic pedagogical plots for torque-speed envelopes, efficiency maps, control waveforms, and comparison views.
