# Vibration Isolation Designer Roadmap

Future enhancements for this tool, roughly prioritized.

## High Priority

- [ ] **Unit toggle (SI/Imperial)** - Support lb, in, lbf in addition to kg, m, N
- [ ] **Logarithmic/dB plot options** - Log frequency axis and dB scale (20·log₁₀(T)) for transmissibility
- [x] **Phase angle display** - Show phase relationship between excitation and response
- [ ] **Resonance pass-through warning** - Calculate peak amplification when system starts/stops and passes through resonance (critical for rotating machinery)
- [ ] **Mount load capacity check** - Compare static load per mount against typical load ratings; flag undersized mounts

## Medium Priority

- [ ] **Common isolator lookup table** - Reference table of mount types (rubber, spring, wire rope, air spring) with representative stiffness/damping ranges and application notes
- [ ] **Temperature derating** - Rubber mount stiffness varies ~2-3x over operating temperature range; add correction factor or warning
- [ ] **Shock isolation mode** - Transient/impact loading analysis (SRS, drop height) as alternative to steady-state harmonic
- [ ] **Save/compare configurations** - Bookmark designs and compare alternatives side-by-side
- [ ] **Export summary** - Printable/PDF report with all parameters and plots

## Lower Priority

- [ ] **Coupled mode warning** - Note about rocking modes when CG height and mount spacing are relevant
- [ ] **Frequency sweep animation** - Visualize response as excitation frequency changes
- [ ] **Mount life estimation** - Estimate fatigue life based on dynamic deflection amplitude and mount type
