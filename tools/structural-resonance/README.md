# Natural Frequency Quick Checker

## Purpose

Estimate natural frequencies of uniform beams, rectangular plates, and free
circular rings. The tool shows the structure's dimensions, supports, and selected
vibration mode alongside the frequency. Its URL remains
`/tools/structural-resonance/` so existing links continue to work.

These are free-vibration estimates for early design checks. The calculator does
not predict forced response or give a resonance pass/fail verdict.

## Models and requirements

### Beam bending

The beam model uses Euler–Bernoulli theory for a straight, uniform beam. Support
choices are cantilever, simply supported at both ends, and fixed at both ends.
Sections can be solid rectangles, round rods, round tubes, or rectangular tubes.
All dimensions are in millimetres. Tube dimensions are outside dimensions with a
uniform wall thickness.

The initial case is an aluminum cantilever: length 300 mm, width 25 mm, depth
5 mm, and bending mode 1. For a rectangle or rectangular tube, an optional bending
direction control selects deflection through the depth or width. The section
inset shows that direction. The two directions can have different frequencies.

Beam modes 1–5 are available. A compact list of the first five bending frequencies
can be expanded in Results; selecting one calculates that mode and updates its
shape. The list is disabled when inputs change so an old frequency cannot be
mistaken for a result from the edited beam.

This model omits shear deformation, rotary inertia, axial prestress, attached
masses, and joint flexibility. It calculates transverse bending, not axial or
torsional modes. Thin, slender geometry is an assumption, not a safety verdict.

### Plate bending

The plate model uses classical thin-plate theory with all four edges simply
supported. The supports prevent transverse displacement and allow rotation.
Geometry consists of length, width, and uniform thickness. The positive integer
mode indices count half-waves along each span; (1, 1) is the lowest mode.

### Free circular ring

The ring is complete and thin, with a uniform rectangular section. Inputs are mean
diameter and radial thickness. It supports in-plane ovaling/bending modes with
circumferential order n ≥ 2, and radial breathing with n = 0. Order 1 is rigid
translation in the bending family. This model does not represent the axial
deformation or attachment stiffness of a finite cylindrical housing.

Plate and ring assumptions include uniform isotropic material, small vibration
amplitude, and no added components or prestress. Shear deformation and rotary
inertia are omitted. Results include relevant geometry ratios and limits; higher
mode orders also shorten the bending wavelength and limit these approximations.

## Interface

Geometry and Material are separate input sections. Model-specific fields show
only the dimensions that apply. The material presets come from Python; selecting
Custom reveals elastic modulus, density, and Poisson's ratio. Presets are
representative values rather than specifications for a particular batch or service
temperature.

Mode and bending-direction settings are expandable. Beam, plate, and ring modes
have independent controls. Switching from a plate to a ring therefore selects
valid n = 2 bending; choose Breathing for n = 0. Hidden geometry, section, mode,
and custom-material inputs are disabled and excluded from validation. Their
values are retained when switching models.

The right-hand panel has Results and Background tabs. Results puts frequency and
a brief model/support summary first, followed by the visual. The visual has
geometry and mode-shape views with an optional animation. Deformation is
normalized and exaggerated, and animation runs slowly for inspection; neither
represents a predicted displacement or physical vibration rate.

Clicking the frequency opens substituted calculations. Assumptions and limits,
material properties, and intermediate values have separate disclosures.
Background contains model descriptions, numbered source equations, symbol
legends, and linked references.

The first valid case calculates after loading. Later edits mark the results and
visual as stale and require Calculate. CSV export and mode-list selection are
disabled until the current inputs have a successful result. Settings provide
Light, Dark, or Auto theme, spacing, and display precision.

## Calculation and visualization sources

`pycalcs/structural_resonance.py` owns the material presets, validation, natural
frequency calculations, mode-shape samples, model notes, and substituted
expressions. The page calls `calculate_beam_resonance` for beams and
`calculate_structural_resonance` for plates and rings through Pyodide. The beam
function reuses section properties from `pycalcs/beam_analysis.py`.

`visualization.js` draws the returned `diagram_data` and handles view/animation
controls. It exposes `FrequencyVisualization.render(container, data, options)`,
`setStale(container, boolean)`, and `destroy(container)`. The frontend does not
implement a second frequency calculation.

Beam bending rigidity has units N·m². Plate rigidity and ring stiffness per unit
axial width have units N·m. The results and CSV distinguish these quantities.
The intermediate speed is the extensional rod/ring speed, not the longitudinal
wave speed in a three-dimensional bulk solid.

## Validation

Dimensions must be finite and positive. Hollow sections require positive internal
dimensions. Mode indices are integers rather than values silently rounded or
clamped; beams support modes 1–5. Custom materials require positive modulus and
density, with −1 < ν < 0.5. Ring thickness must be smaller than its mean diameter.

Useful checks for aluminum with E = 69 GPa, ρ = 2700 kg/m³, and ν = 0.33:

| Case | Expected frequency |
| --- | ---: |
| 300 mm cantilever, 25 × 5 mm solid section, mode 1 through depth | 45.368082 Hz |
| 300 × 200 × 5 mm plate, mode (1, 1) | 438.449472 Hz |
| 150 mm mean-diameter ring, 5 mm radial thickness, n = 2 | 553.969555 Hz |
| Same ring, breathing n = 0 | 10727.574309 Hz |

Numerical regression tests are in `tests/test_structural_resonance.py`. The UI
syntax regression test is in `tests/test_structural_resonance_ui.py`.

## Sharing, export, and loading

Copy link saves the complete form, including inactive geometry, modes, section
values, custom properties, and blank fields. Version 3 links include the new beam
state. Earlier links without an explicit model retain the former plate default;
plain visits now default to the cantilever. Earlier ring links using
`geometry_type=cylinder` and `mode_2` map to the ring controls. Background
fragments open the Background tab.

CSV contains the calculated geometry, supports, section, selected mode, effective
material properties, frequency, intermediate values, and model notes. For beams
it also includes the first five bending frequencies. Numeric values retain
calculation precision; export uses the last successful calculation.

The loading overlay remains visible while Pyodide and the Python files load.
Initialization errors provide a retry button. A retry reloads the model without
requiring a page refresh. The page loads `beam_analysis.py` alongside the resonance
module and needs a static server plus access to the Pyodide CDN on first load.

## Browser checks

1. Verify the default cantilever, every support type, and all four sections.
2. Change the bending direction of a nonsquare rectangle and check that frequency
   and the section inset agree. Select modes 1–5 from the control and result list.
3. Check plate and ring calculations, including breathing and custom materials.
4. Confirm invalid dimensions and fractional modes give errors; hidden fields
   should not block a valid model.
5. Open shared beam, legacy plate, and legacy ring links, including a Background
   fragment. Compare results and CSV values.
6. Verify loading retry, tab keyboard navigation, diagram controls, animation,
   reduced-motion preference, and mobile layout in light and dark themes.
7. Edit an input while the visual is displayed. It should mark the previous
   calculation as stale and disable CSV and mode-list actions.
