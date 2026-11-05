# Structural Resonance Calculator

## Purpose

Estimate a selected natural frequency of a rectangular plate or a free circular
ring. The tool supports early vibration screening of covers, rings, and similar
components. It calculates free-vibration frequencies, not forced response or a
resonance pass/fail verdict.

## Models and requirements

The plate model uses classical thin-plate bending theory with all four edges
simply supported. The supports prevent transverse displacement and allow rotation.
Geometry consists of length, width, and uniform thickness. The two positive
integer mode indices count half-waves along each span; (1, 1) is the lowest mode.

The ring model is a free, complete, thin circular ring with a uniform rectangular
section. Inputs are mean diameter and radial thickness. It supports in-plane
ovaling/bending modes with circumferential order n ≥ 2, and radial breathing with
n = 0. Order 1 is rigid translation in the bending family and is not an elastic
mode. This model does not represent the axial deformation or attachment stiffness
of a finite cylindrical housing.

Both models assume uniform isotropic material, small vibration amplitude, and no
added components or prestress. Shear deformation and rotary inertia are omitted.
The results show the relevant thickness ratio and assumptions so users can judge
whether the thin-model approximation is suitable. High mode orders also shorten
the bending wavelength and limit that approximation.

## Interface

Geometry and Material are separate input sections. The default is a 300 × 200 ×
5 mm aluminum plate. Material presets come from the Python material table;
selecting Custom reveals elastic modulus, density, and Poisson's ratio. Presets
are representative values, not specifications for a particular batch or service
temperature.

Mode settings are expandable. Plate and ring modes have separate controls, so
switching from the default plate to a ring selects valid n = 2 bending. Choose
Breathing to use n = 0. Hidden geometry, mode, and custom-material inputs are
disabled and excluded from input validation; their values are retained when
switching models.

The right-hand panel contains Results and Background tabs. The primary result is
the natural frequency in Hz, with the calculated mode and a brief support/model
summary. Clicking the frequency reveals substituted calculations. Model assumptions
and applicability limits have their own expandable panel. Material properties,
bending stiffness, and extensional wave speed are also available on demand. Background contains numbered equations, variable definitions, and linked
references from the Python documentation.

The first valid case calculates after initialization. Later edits mark the results
as stale and require Calculate. Export is disabled until a successful calculation
matches the current inputs. Settings provide Light, Dark, or Auto theme, spacing,
and display precision; preferences persist locally.

## Calculation source

`pycalcs/structural_resonance.py` owns the material presets, equations, validation,
assumptions, applicability notes, and substituted expressions. The page calls
`calculate_structural_resonance` through Pyodide and formats its returned data.
There is no duplicate frequency implementation in JavaScript.

Plate flexural rigidity includes the Poisson correction for a plate. Free-ring
bending stiffness per unit axial width and free-ring frequencies use the ring
model without that correction. The intermediate speed is the extensional
rod/ring speed, not the three-dimensional longitudinal wave speed of a bulk solid.

Geometry must be finite and positive. Mode indices must be integers rather than
values that are rounded or clamped. Custom material properties require positive
modulus and density, with −1 < ν < 0.5. Ring thickness must be less than mean
diameter to leave a positive inner diameter.

## Sharing, export, and loading

Copy link saves the complete form, including inactive geometry and mode values,
custom properties, and blank fields. The page restores state before its first
calculation. Older ring links using `geometry_type=cylinder` and `mode_2` are
mapped to the ring controls. Background section links open the Background tab.

CSV export contains the calculated geometry, selected mode, effective material
properties, frequency, intermediate values, assumptions, and applicability notes.
Numeric values retain calculation precision. Export uses the last successful
calculation rather than mixing stale results with edited inputs.

The loading overlay remains visible while the browser loads Pyodide and the
Python files. Initialization failures show a retry button. A retry loads the model
again without requiring a page refresh. The tool needs access to its CDN on first
load and a static server for the Python module files.

## Checks

For aluminum with E = 69 GPa, ρ = 2700 kg/m³, and ν = 0.33:

| Case | Expected frequency |
| --- | ---: |
| 300 × 200 × 5 mm plate, mode (1, 1) | 438.449472 Hz |
| 150 mm mean-diameter ring, 5 mm radial thickness, n = 2 | 553.969555 Hz |
| Same ring, breathing n = 0 | 10727.574309 Hz |

Numerical regression tests are in `tests/test_structural_resonance.py`. The UI
syntax regression test is in `tests/test_structural_resonance_ui.py`.

Browser verification should cover initialization and retry, all presets, custom
properties, invalid and fractional mode indices, ring bending/breathing, shared
links, CSV, keyboard tab navigation, and mobile layout in light and dark themes.
Check that switching models retains values and disables hidden controls.

## References

- Leissa, A. W. (1969), *Vibration of Plates*, NASA SP-160, Chapter 4:
  [NASA record](https://ntrs.nasa.gov/citations/19700009156).
- Knight, N. F., Jr., and Rankin, C. C. (2006), *STAGS Example Problems Manual*,
  NASA/CR-2006-214281, free circular ring example, pp. 40–41:
  [NASA record](https://ntrs.nasa.gov/citations/20060008654).
