# Engineering Tools Backlog

This backlog consolidates platform work, template upgrades, and future tool ideas that span from lightweight utilities to large, multi-module experiences.

## Platform Improvements

- [ ] Implement a reusable SI/Imperial unit toggle in the shared template and apply it across tools.
- [ ] Design a schema-driven input renderer for tools with large parameter counts (auto-tooltips, validation, tabs).
- [ ] Convert legacy tools to the standard template (`beam-bending`, `simple_thermal`, `door-spring-app`, `fits`, `mtbf`, `trajectory`, `wire-sizing`).
- [ ] Establish automated docstring validation to enforce `---Parameters---` / `---Returns---` / `---LaTeX---` sections.
- [ ] Build a shared visualization helper (Plotly/Chart.js adapters) to reduce duplicated plotting code.
- [ ] Create integration tests that load each tool in Pyodide and exercise nominal + error paths.
- [x] Deploy Reynolds Number Explorer (fluid mechanics sanity-check tool).
- [x] Add Composite Wall Heat Loss calculator with interface temperature visualization.

### Export Functionality (Future)

- [ ] **PDF Export** - Generate professional PDF reports for design reviews with:
  - Tool name, version, and timestamp
  - All inputs with labels and units
  - All outputs with derivation steps
  - Equations used (rendered LaTeX)
  - Charts/visualizations embedded
- [ ] **Excel Export** - Generate calculation spreadsheets with:
  - Input cells (editable for verification)
  - Formula cells showing calculation logic
  - Output summary
  - Version and tool metadata
- [ ] Shared export module to standardize format across all tools

### Versioning System (Future)

- [ ] **Define versioning scheme** for tools:
  - `0.x` = Prototype/Experimental (unverified)
  - `1.x` = Verified (human-tested, equations validated)
  - Semantic versioning for updates (e.g., `1.2.3`)
- [ ] **User-visible version display** - Show version in tool UI (header or footer)
- [ ] **Version in exports** - All PDF/Excel exports must include:
  - Tool version number
  - Verification status (Experimental/Verified)
  - Export timestamp
- [ ] **Version tracking in catalog.json** - Add `version` field to each tool entry
- [ ] **Changelog per tool** - Track what changed between versions

## Aerospace Engineering Tools

- [ ] Airfoil lift and drag estimator with NACA parser and Cp plots.
- [ ] Tsiolkovsky rocket equation planner (staging, propellant tables, delta-v budget).
- [ ] Orbital mechanics sandbox (two-body propagator, transfer maneuvers, 3D visualization).
- [ ] Hypersonic stagnation heating calculator for blunt bodies (complex).

## Civil & Mechanical Engineering Tools

- [ ] Beam deflection and combined stress calculator with superposition library.
- [ ] Mohr's circle visualization with failure envelopes.
- [ ] Truss analysis tool using method of joints + determinacy checker.
- [ ] Shaft analysis module (critical speed, torsional stress, bearing loads).
- [ ] Gear design assistant (AGMA stress, contact ratio, geometry factors).
- [ ] Fastener torque and preload calculator with tightening strategies.
- [ ] Interference-fit predictor including thermal assembly planning.
- [ ] Vibration isolation selector (spring-damper tuning, transmissibility plots).
- [ ] Structural bolted joint fatigue life estimator (complex).

## Thermal & Fluid Sciences Tools

- [ ] Heat exchanger sizing and rating assistant (LMTD, effectiveness-NTU).
- [ ] Pump/fan selection tool that intersects system and pump curves.
- [ ] Refrigeration cycle analyzer with property tables and COP visualization.
- [ ] Pipe network solver (Darcy-Weisbach, minor losses, pumps in series/parallel).
- [ ] Radiative view-factor calculator for common geometries (complex).
- [ ] Natural convection correlation explorer (plates, cylinders, enclosures).
- [x] Reynolds number explorer with regime classification (complete).
- [x] Composite wall conduction calculator with film resistances (complete).

## Chemical & Process Engineering Tools

- [ ] Ideal gas law explorer with common engineering unit options.
- [ ] Reaction kinetics simulator (Arrhenius, CSTR/PFR sizing).
- [ ] Distillation column McCabe-Thiele assistant (complex).
- [ ] Process safety relief-valve sizing utility.

## Electrical & Electronics Tools

- [ ] Motor selection and acceleration profile calculator.
- [ ] Battery sizing and lifecycle estimator for duty-cycle driven loads.
- [ ] Power-factor correction planner (economic payback included).
- [ ] LED lighting design tool (photometric layout basics).
- [ ] Solar PV & storage sizing with location-based irradiance.
- [ ] High-speed PCB impedance calculator (microstrip/stripline, advanced).

## Mathematics, Data & Controls Tools

- [ ] Matrix operations and linear solver workspace.
- [ ] 3D vector visualization and coordinate transform helper.
- [ ] Fourier series synthesizer with audio playback.
- [ ] State-space control analysis tool (Bode, root locus, observer design).
- [ ] Kalman filter tuning playground (complex).

## Simple Utility Tools

- [ ] Basic unit converter (length, area, temperature, pressure) tied to the new unit system.
- [ ] Material property lookup dashboard with filtering/export.
- [ ] Engineering assumption checklist generator for reports.
- [ ] Template lint script that verifies MathJax legends in equations

## Complex / Long-Term Initiatives

- [ ] Multiphysics coupling framework (thermal + structural, modular solvers).
- [ ] Parametric optimization harness (link tools with sweeps and Pareto plots).
- [ ] BOM and cost estimator integrating outputs from multiple tools.
- [ ] Cloud-backed project saving/sharing for collaborative review workflows.
