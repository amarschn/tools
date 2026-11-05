# Tipping and Stability roadmap

- [x] Rigid planar support model with slope, acceleration, turn, and force cases.
- [x] Component masses, custom contacts, and combined loading.
- [x] Edge reserves, diagrams, derivations, sharing, and CSV/JSON export.
- [x] Always-present support footprint linked to an edge-normal FBD.
- [x] Shared force labels, ground reactions, component locations, and selected edges.
- [x] Four-control starting view, footprint and FBD visible together, and separate disclosure of input customizations, force values, and calculations.
- [x] Eight FBD rendering studies with shared solver cases and library research: [comparison gallery](prototypes/).
- [x] Final [JSXGraph interaction lab](prototypes/jsxgraph-lab.html) with constrained handles, live moment-arm construction, automatic labels, and Python reactions.
- [x] Integrate selected study B's world-oriented section using native SVG. Keep all prototype pages and the JSXGraph lab available for future review.
- [x] Replace the confusing isometric illustration with a top-down footprint that keeps left/right orientation fixed. Support keyboard edge selection and linked application points.
- [ ] Make tipping and sliding equally visible, reduce scrolling, and expose the key results and edge table by default. Follow the [2026-09-30 UI plan](../../plans/2026-09-30_tipping_stability_ui_streamlining.md).
- [ ] Add sliding thresholds along the selected case parameter before comparing which limit occurs first. The current sliding check applies only at the entered operating point.
- [ ] Payload-position sweeps and uncertainty ranges for center of mass.
- [ ] Worst-case caster orientation search.
- [ ] Formula-bearing Excel export.
- [ ] Chair and freestanding-equipment presets with documented load cases.
- [ ] Separate models for suspension, axle articulation, and noncoplanar terrain.
- [ ] Industry test modes, after obtaining and validating the applicable protocols.
