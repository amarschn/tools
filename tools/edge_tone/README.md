# Whistle Acoustics Explorer

An interactive tool for analyzing the physics of whistles, flutes, and other resonant instruments by finding "acoustic locking" conditions where edge-tone frequencies match resonator natural modes.

## Purpose

This tool models the interaction between:
1. **Resonator Natural Frequencies**: The frequencies at which air inside a cavity or tube naturally vibrates
2. **Edge-Tone Frequencies**: Oscillating tones created when a jet of air strikes a sharp edge (labium)

A stable musical note is produced only when an edge-tone frequency exactly matches one of the resonator's natural modes—a phenomenon called "acoustic locking."

## Features

- **Two Resonator Models**:
  - **Pipe (Open-Closed)**: Models flutes, tin whistles, and similar tube instruments
  - **Helmholtz Resonator**: Models bottles and cavity-based instruments

- **Comprehensive Analysis**:
  - Calculates resonator mode frequencies based on geometry
  - Determines required jet velocities for acoustic locking
  - Shows all combinations of modes and edge-tone stages

- **Preset Configurations**: Quick-load typical instruments (tin whistle, bottle)

- **Progressive Disclosure**: Simple interface with detailed equations and explanations available on demand

## Physics Background

### Edge-Tone Formation

When a thin jet of air (velocity U, thickness d) strikes a sharp edge, it creates oscillating vortices at discrete frequencies. The edge-tone frequency is:

```
f_edge = St × U / d
```

Where St is the **Strouhal number** representing different "stages" of edge-tone behavior.

**Why These Specific Strouhal Numbers?**

Edge-tones don't occur at all frequencies—only at discrete "stages" corresponding to specific vortex shedding patterns. The default values are empirically determined from classic jet-edge interaction research (Powell, 1961):

- **Stage 1 (St ≈ 0.2):** Fundamental mode, lowest frequency, most stable
- **Stage 2 (St ≈ 0.4):** First overtone, moderate stability
- **Stage 3 (St ≈ 0.7):** Second overtone
- **Stage 4 (St ≈ 1.0):** Third overtone
- **Stage 5 (St ≈ 1.3):** Fourth overtone, requires high velocity, less stable

Higher stages require higher jet velocities but are increasingly unstable. Musical instruments typically lock to stages 1-3.

### Resonator Modes

**What is an Open-Closed Tube?**

An open-closed tube (also called a "stopped pipe") has:
- **One end open** to the atmosphere
- **One end closed** (or effectively closed)

Examples: flutes (embouchure end is effectively closed by the air column), tin whistles, clarinets, some organ pipes.

**Key characteristic:** Open-closed tubes produce only **odd harmonics** (1st, 3rd, 5th, 7th...), not all harmonics. This is why they sound different from open-open tubes (like pan pipes).

**For Pipe (Open-Closed)**:
```
f_n = (2n-1) × c / (4 × L_eff)
```
Where n = 1, 2, 3... The `(2n-1)` generates odd numbers: n=1 → 1st harmonic, n=2 → 3rd harmonic, n=3 → 5th harmonic, etc. The fundamental frequency is f₁ = c/(4L), and subsequent modes are 3f₁, 5f₁, 7f₁...

**End Correction (δ):** L_eff = L_physical + δ

The effective acoustic length is longer than the physical length because sound waves extend slightly beyond the pipe opening due to radiation and diffraction. Without this correction, calculated frequencies would be too high.

Typical end correction values:
- Unflanged pipe (most instruments): δ ≈ 0.6r ≈ 0.3-0.4d (where r=radius, d=diameter)
- Flanged pipe: δ ≈ 0.8r
- Example: 15mm bore → δ ≈ 5mm; 10mm bore → δ ≈ 3-4mm

**For Helmholtz Resonator**:
```
f = (c / 2π) × √(A / (V × L_eff))
```
Where A is neck area, V is cavity volume, L_eff is effective neck length.

### Acoustic Locking

Locking occurs when f_edge = f_mode. For each mode frequency and Strouhal stage, the required jet velocity is:

```
U_lock = (f_mode × d) / St
```

The tool calculates all these locking velocities, showing which jet speeds will produce stable tones.

## Implementation

- **Python Logic**: Core calculations in `/pycalcs/acoustics.py`
- **UI**: Follows the project's standard template with docstring-driven tooltips and equations
- **Client-Side**: Runs entirely in browser via Pyodide

## Usage

1. Select resonator type (pipe or Helmholtz)
2. Enter environmental and geometric parameters
3. Optionally load a preset configuration
4. Click Calculate to see:
   - Speed of sound at given temperature
   - Resonator mode frequencies
   - Complete table of locking conditions sorted by required velocity

## References

- Powell, A. (1961). "On the edge-tone." *Journal of the Acoustical Society of America*
- Fletcher, N.H. & Rossing, T.D. (1998). *The Physics of Musical Instruments*, 2nd ed.
- Benade, A.H. (1976). *Fundamentals of Musical Acoustics*
