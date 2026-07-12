# Bearing Selector V2: Catalog, Arrangement, and Technology Triage

Date: 2026-07-11
Status: Proposed plan for implementation after review

## Objective

Turn the current proof-of-concept into a useful bearing-system design assistant without implying that a catalog L10 calculation is a complete bearing design.

V2 should answer three progressively deeper questions:

1. **Catalog selection:** Which rolling bearings fit the bore, loads, speed, life, envelope, and environment?
2. **Arrangement analysis:** How should one or more bearings locate and support the shaft, and what loads does each bearing actually see?
3. **Technology triage:** When rolling-element bearings are a poor fit, which other bearing technologies deserve investigation and why?

These are separate calculation and education layers. The tool must not apply rolling-bearing equations to journal, gas, magnetic, or other non-rolling technologies.

## Why V2 Is Needed

The current version validates the basic UI and L10 pipeline, but it is too narrow for serious selection work:

- only 30 catalog bearings are included, at six bores from 25 to 50 mm;
- only one representative series is present for each of five rolling-bearing families;
- exact-bore filtering gives no help when the desired shaft size is absent;
- chart purpose, axes, log scales, thresholds, and engineering interpretation are underexplained;
- preload is mentioned only as a warning;
- there is no bearing cross-section or arrangement visualization;
- the tool assumes loads at one bearing are already known and does not teach locating/floating or paired arrangements;
- lubrication is reduced to a grease/oil speed-column switch;
- dry/no-lubricant operation is not an explicit design condition;
- non-rolling bearing technologies are invisible;
- exported analyses cannot be loaded again;
- inputs lack accessible, useful tooltips;
- constant-load L10 is overemphasized relative to variable duty, contamination, fits, clearance, temperature, misalignment, seals, and reliability.

## Product Structure

V2 should use four top-level workflow steps while preserving a fast default path:

1. **Duty** — load, speed, bore/envelope, life, environment, and operating schedule.
2. **Arrangement** — known single-bearing reactions, a known multi-bearing load set, or an assisted shaft arrangement.
3. **Candidates** — rolling-bearing catalog results and comparison.
4. **Alternatives** — technology-triage suggestions when rolling bearings are marginal or incompatible.

The default remains minimal: radial load, axial load, speed, and target bore. Every additional layer is optional and progressively disclosed.

## Workstream 1: Catalog Expansion and Data Integrity

### Scope

Replace the 30-row demonstration slice with a useful, traceable manufacturer catalog dataset.

Initial target:

- at least **500 catalog rows**;
- common metric bores from approximately **5 to 200 mm**, with actual catalog increments rather than invented interpolation;
- multiple dimension/capacity series at each common bore;
- enough choices for compact, general-purpose, heavy-duty, high-speed, thrust, and misalignment-tolerant selection;
- an on-screen coverage indicator showing how many catalog records were searched, filtered, excluded, and displayed.

Families and series to investigate for inclusion:

- deep-groove ball: miniature, thin/light, 60, 62, 63, and 64 series;
- angular-contact ball: multiple dimensional series and supported contact angles;
- double-row angular-contact ball;
- self-aligning ball;
- cylindrical roller: N, NU, NJ, NUP, and supported double-row variants, with axial-location capability encoded by design;
- needle roller and drawn-cup needle bearings where catalog data support the same screening method;
- tapered roller: several metric light through heavy series;
- spherical roller: light through heavy and compact series;
- thrust ball, cylindrical roller thrust, needle thrust, tapered thrust, and spherical roller thrust;
- insert bearings/bearing units only if housing and locking-method metadata can be represented honestly.

### Data rules

- Keep manufacturer identity explicit. Never create a synthetic “consensus” rating.
- Start by expanding the existing NTN source. Add another manufacturer only as a separately selectable catalog.
- Store catalog edition, official URL, table/page, designation, dimensions, ratings, speed limits, load factors, contact angle, internal-clearance/preload metadata, seals/shields, and design capabilities where available.
- Distinguish dimensional standards from manufacturer-specific ratings.
- Use `null` for unavailable data; never infer a rating from a neighboring size.
- Add a catalog schema version and a deterministic dataset checksum to saved analyses.
- Move the catalog out of a hand-maintained Python tuple. Choose one canonical JSON/CSV source and make Python and browser tests consume that source.
- Follow the repository reference-promotion rule. If only this tool consumes the data, keep it tool-local; promote it only when another tool genuinely depends on it.

### Selection behavior

- Support exact bore, nearest standard bore, bore range, maximum OD, maximum width, and optional mass constraints.
- Clearly separate “no catalog row exists” from “rows exist but fail requirements.”
- Show excluded candidates and exclusion reasons without flooding the default view.
- Add sorting by smallest envelope, life margin, speed margin, mass, family, and designation.
- Never rank solely by maximum calculated life.

### Data acceptance criteria

- Automated schema and uniqueness validation passes for every row.
- Every row has manufacturer, catalog edition, source URL, and source location.
- A coverage-matrix test proves required families, bore bands, and series are populated.
- A sample of transcribed rows from every family is independently checked against the official source.
- Known manufacturer examples reproduce published equivalent-load and life calculations within stated rounding tolerance.

## Workstream 2: Input Help and Work Files

### Tooltips

Every input and non-obvious selector needs a tooltip available by hover, keyboard focus, and touch. Each tooltip should state:

- what the input physically means;
- expected units;
- valid or typical range where defensible;
- whether it applies per bearing, per shaft, or per duty segment;
- how the value affects selection;
- a short example;
- a warning when users commonly supply the wrong quantity.

The Python docstring remains the single source for calculation parameter definitions. UI-only controls such as unit system, chart mode, catalog, arrangement, and result sorting should use one frontend metadata object rather than duplicated HTML text.

Highest-priority tooltip clarification: radial and axial loads are reactions at one bearing unless the user enters the shaft-system workflow.

### Save, export, and load

Adopt the repository work-file pattern used by the fan selector:

- **Save Inputs** — raw display-unit values and UI choices;
- **Export Analysis** — normalized SI inputs, catalog version/checksum, complete results, warnings, and display preferences;
- **Load Work** — accept either saved inputs or exported analysis;
- validate `tool`, `type`, and schema `version` before applying a file;
- show a migration/error message for unsupported versions;
- preserve the original display units;
- rerun calculations when catalog data changed, while retaining the old result for comparison;
- add round-trip browser tests for both formats and invalid-file tests.

Do not treat the five regression-case JSON files as user work files; their schema and purpose remain separate.

## Workstream 3: Graph Explanations and Better Plots

Every graph needs four explanation layers:

1. a one-sentence purpose above the plot;
2. explicit axis names, units, scale type, and threshold lines;
3. hover text that explains the candidate and pass/fail basis;
4. a dynamic “How to read this result” paragraph below the plot.

### Existing life chart

- Explain that the vertical axis is logarithmic and why.
- Label the required-life threshold directly.
- Explain that L10 is a population reliability metric, not guaranteed service life.
- Allow switching between life hours, life margin, and millions of revolutions.
- Identify inapplicable candidates separately from failed candidates.

### Existing sensitivity chart

- Explain that both radial and axial loads are multiplied together in the current curve.
- State that the curve holds speed, load ratio, lubrication choice, and bearing factors fixed.
- Mark the entered duty point at `1.0×`.
- Add a required-life intersection and a tooltip explaining the ball-versus-roller life exponent.
- Add optional separate radial-load and axial-load sweeps; do not imply proportional loading is universal.

### Additional plots

- **Envelope versus capacity:** OD or mass against dynamic capacity, colored by family.
- **Speed versus load map:** operating point, allowable-speed boundary, and formula-validity region.
- **Duty-cycle contribution:** life-damage share by load segment when variable duty is enabled.
- **Arrangement load view:** bearing locations, reaction arrows, axial locating direction, and load path.

Charts must remain meaningful without color, use accessible contrast in light/dark themes, and include a compact data-table alternative.

## Workstream 4: Bearing and Arrangement Visualizations

Create code-native SVG diagrams rather than static decorative images.

### Bearing-family cross-sections

Provide simplified but recognizable sectional diagrams for:

- deep-groove and angular-contact ball;
- self-aligning and double-row ball;
- cylindrical, needle, tapered, and spherical roller;
- rolling-element thrust families.

Diagrams should show inner/outer rings, rolling elements, contact/load lines, contact angle where relevant, supported load directions, and ring movement permitted by designs such as NU/N. The selected candidate should display its actual bore, OD, and width proportions without pretending to reproduce internal proprietary geometry.

### Arrangement diagrams

Support diagrams for:

- locating/non-locating two-bearing systems;
- adjusted angular-contact or tapered pairs;
- back-to-back, face-to-face, and tandem arrangements;
- duplex and triplex sets where supported;
- fixed-fixed arrangements with thermal-growth warning;
- vertical shafts and thrust-location direction;
- touch-down/backup bearings when magnetic bearings are discussed.

Each SVG needs text alternatives, keyboard-accessible annotations, and load-arrow legends.

## Workstream 5: Lubrication and “No Lubricant” Operation

Replace the grease/oil speed-column selector with a lubrication workflow.

### Top-level modes

- Unknown / not yet selected
- Grease
- Oil
- Sealed or lubricated-for-life bearing
- Solid lubricant or special coating
- No lubricant permitted / dry-running requirement

“No lubricant” must not silently apply a grease or oil catalog speed limit. Standard rolling candidates should be marked incompatible unless their sourced product metadata explicitly permits the condition. The alternative-technology layer should then become prominent.

### Grease guidance

Include educational inputs and screening for:

- base-oil type and viscosity;
- thickener/soap type;
- NLGI consistency;
- operating and start-up temperature;
- speed factor such as `n·dm`;
- load severity, shock, vibration, water, dust, vacuum, and chemical exposure;
- fill quantity and relubrication approach;
- compatibility warning when changing grease families.

Do not claim a universal “best grease.” Output a required property envelope and considerations; branded product matching should only use sourced manufacturer data.

### Oil guidance

Distinguish oil bath, splash, circulating oil, oil jet, oil mist, and air-oil methods. Screen viscosity at operating temperature, heat removal needs, filtration/cleanliness, churning risk, orientation, seals, and maintenance system complexity.

### Lubrication release boundary

The first lubrication release may remain advisory. Modified-life or thermal calculations should not ship until their required viscosity, contamination, temperature, and bearing-geometry inputs are available and validated.

## Workstream 6: Preload, Clearance, and Bearing Pairs

Preload requires more than adding one numeric field. Separate explanation from supported calculation.

### Educational layer

Explain:

- positive internal clearance, zero clearance, and preload;
- fixed-position versus constant-pressure preload;
- why preload can increase stiffness, accuracy, and resistance to skidding;
- why excessive preload reduces life and increases torque and heat;
- thermal growth and fit effects on operating preload;
- manufacturer preload classes and why they are not interchangeable;
- which bearing families are commonly preloaded and which are not.

### Arrangement inputs

- single bearing, paired bearings, or manufacturer-matched set;
- back-to-back, face-to-face, tandem, or custom arrangement;
- contact angle and axial load direction;
- fixed-position, spring/constant-force, or unknown preload method;
- sourced preload class or explicit preload force;
- spacer/shoulder arrangement and thermal-growth direction.

### Calculation boundary

- Do not calculate load sharing or life for a preloaded pair without the necessary load-deflection/stiffness relationship.
- For catalog sets with supported preload/stiffness data, calculate bearing-by-bearing axial load, contact-load change, and life.
- Otherwise provide arrangement guidance and flag the result as requiring manufacturer stiffness data.
- Show how preload changes the internal load path visually.

## Workstream 7: Multi-Bearing Systems and Variable Duty

### Three analysis levels

1. **Known single-bearing reactions** — current workflow.
2. **Known multi-bearing reactions** — user enters load/speed histories for each bearing; tool evaluates the set and identifies the limiting bearing.
3. **Assisted shaft system** — user enters bearing locations, external forces/moments, shaft spans, and locating behavior; the tool solves only arrangements supported by its mechanics model.

### Arrangement checks

- identify the axial locating bearing and permitted thermal expansion path;
- warn about overconstraint, absent axial location, or incompatible axial directions;
- explain when NU/N cylindrical designs act as non-locating bearings;
- treat paired angular-contact/tapered bearings as a coupled set;
- consider shaft/housing stiffness and misalignment inputs before analyzing statically indeterminate systems;
- distinguish inner-ring and outer-ring rotation;
- include minimum-load/skidding warnings when sourced criteria are available;
- point to the fits, ring-fit, and shaft-deflection tools as follow-on checks.

### Variable-duty analysis

- accept multiple load/speed/time segments;
- calculate equivalent dynamic load per segment with the correct family factors;
- accumulate life consumption using a documented damage rule;
- show each segment's contribution and the limiting bearing;
- support oscillating/reversing-duty warnings rather than blindly converting all motion to rpm;
- store the complete duty spectrum in work files.

### Solver boundary

Begin with determinate two-bearing systems and known reactions. Multi-support shafts, housing flexibility, gear mesh coupling, rotor dynamics, and nonlinear bearing stiffness require a later validated solver or a handoff to a dedicated shaft/rotor tool.

## Workstream 8: Alternative Bearing Technology Triage

Add an advisory panel that appears both on demand and automatically when rolling-bearing candidates are absent, overspeed, dry-operation incompatible, life-limited, precision-limited, or otherwise outside the catalog screen.

Technologies to describe:

- hydrodynamic journal and thrust bearings;
- hydrostatic liquid bearings;
- oil-impregnated sintered and plain sleeve bearings;
- polymer/composite plain bearings;
- aerostatic air bearings;
- aerodynamic and foil gas bearings;
- active magnetic bearings, including controls, power, sensors, and backup bearings;
- passive magnetic support where technically relevant;
- jewel/pivot bearings for very small precision mechanisms;
- flexure bearings for limited-angle, zero-friction motion.

### Triage inputs and triggers

- shaft diameter and speed/surface speed;
- radial and thrust load;
- continuous rotation versus oscillation;
- required precision, stiffness, runout, and noise;
- permitted friction and heat;
- lubricant prohibited, vacuum, cleanroom, food/medical, corrosive, or extreme-temperature environment;
- start/stop frequency and ability to tolerate contact at zero speed;
- maintenance tolerance, service life, cost, control complexity, and available utilities.

The output should say **why to investigate** a technology, its major advantages, its disqualifiers, and what information a specialist/vendor will request. It must not return a fake part size or rank technologies with an unexplained universal score.

Example prompts:

- very high speed plus clean compressed gas available → investigate aerostatic/aerodynamic gas bearings;
- high speed plus oil-free turbomachinery → investigate foil air bearings;
- zero contact, active control acceptable, and backup-bearing strategy available → investigate active magnetic bearings;
- moderate speed, high load, continuous rotation, oil system acceptable → investigate hydrodynamic journal bearings;
- low-cost low-speed duty → investigate sleeve, sintered, or polymer plain bearings.

These are prompts, not selection rules. Every trigger needs a cited technical basis and explicit uncertainty.

## Workstream 9: Additional Engineering Inputs

Add these only through expert or arrangement modes:

- reliability target and resulting life adjustment;
- variable load spectrum and duty cycle;
- shock/application factor with a named basis;
- rotating ring and load direction;
- temperature range and gradients;
- contamination and sealing environment;
- misalignment and shaft deflection;
- desired internal clearance and precision class;
- noise/vibration sensitivity;
- outer-ring or inner-ring rotation;
- required minimum load;
- maximum envelope, mass, torque, or heat generation;
- mounting, inspection, and maintenance constraints.

Each feature must either change a sourced calculation/check or remain clearly labeled as advisory. Avoid collecting inputs that the tool silently ignores.

## Architecture Changes

### Python

Split the current module by responsibility while keeping a stable public API:

- `pycalcs/bearings.py` — public orchestration and backward-compatible entry points;
- catalog loader/schema validation;
- rolling-bearing equivalent load and life calculations;
- arrangement and preload models;
- duty-cycle accumulation;
- technology-triage rules and explanations.

Exact module boundaries should be chosen after measuring size and coupling; do not create modules that only wrap one function.

Return structured provenance with every result:

- equation identifier;
- inputs and factors used;
- catalog row and source;
- applicability limits;
- warnings;
- substituted equation;
- interpretation.

### Frontend

Break the current monolithic inline script into tool-local JS modules once behavior expands. Keep calculations in Python; JS owns state, file handling, SVG/Plotly rendering, accessibility, and unit display.

Use one state object for inputs, arrangement, catalog filters, settings, and results. Add schema-versioned serialization before implementing more controls.

### Single source of truth

- equations and applicability rules: Python;
- catalog values: canonical data file;
- parameter definitions: Python docstrings/metadata;
- UI-only help: one frontend metadata object;
- bearing-family educational copy and alternative-technology profiles: structured sourced data, not repeated HTML paragraphs.

## Verification Strategy

### Calculation tests

- published manufacturer examples for every rolling family and load-factor branch;
- ball and roller life exponents;
- pure radial, pure axial where applicable, combined load, overspeed, and static overload;
- no-lubricant incompatibility;
- paired-bearing load direction and preload boundaries;
- locating/non-locating arrangement checks;
- variable-duty hand calculations;
- technology-triage trigger and non-trigger cases.

### Data tests

- schema, types, nonnegative values, designation uniqueness per catalog;
- dimensions `bore < OD` and positive width;
- source metadata completeness;
- bore/family/series coverage matrix;
- no interpolation or silent fallback for missing ratings;
- stable checksums and catalog-version migrations.

### Browser tests

- default calculation in under ten seconds after initialization;
- all tooltips via mouse, keyboard, and touch-sized controls;
- save/export/load round trips;
- chart explanations and table alternatives;
- light/dark themes and compact/mobile layouts;
- bearing and arrangement SVG labels;
- expert-mode state persistence;
- screen-reader labels, focus order, and no color-only status;
- error recovery from malformed files and unavailable catalog data.

### Human verification

Before adding `human-verified`, a maintainer should work through at least:

- a simple electric-motor bearing pair;
- a belt-driven shaft with radial load and thermal expansion;
- a helical-gear shaft with thrust and paired bearings;
- a high-speed spindle with preload considerations;
- a low-speed heavy-load spherical roller case;
- an oil-free high-speed case that routes to alternative technologies;
- a variable-duty case;
- save, export, reload, and compare behavior.

## Incremental Delivery Plan

Keep each increment on its own task branch and merge only after its acceptance criteria pass.

### Increment A — UX debt and work files

- tooltips for every current input;
- explanations for both existing graphs;
- Save Inputs, Export Analysis, and Load Work with versioned schemas;
- browser round-trip tests.

This is the smallest high-value improvement and should be implemented first.

### Increment B — Catalog foundation and expansion

- canonical external dataset and schema;
- coverage/provenance tests;
- 500+ rows and wider bore coverage;
- bore range, nearest size, envelope filters, sorting, and searched/excluded counts.

### Increment C — Bearing visualizations

- family cross-section SVGs;
- contact/load direction overlays;
- arrangement diagrams for locating/floating and paired bearings.

### Increment D — Lubrication modes

- unknown, grease, oil, sealed-for-life, solid/special, and no-lubricant modes;
- property-based grease/oil guidance;
- dry-running incompatibility and alternative-technology handoff.

### Increment E — Preload and two-bearing arrangements

- preload/clearance education;
- arrangement selector and warnings;
- supported paired-bearing calculations only where stiffness/preload data exist.

### Increment F — Multi-bearing and variable-duty analysis

- known per-bearing load sets;
- determinate two-bearing reaction assistant;
- duty-segment analysis and life-consumption plot;
- explicit boundary for indeterminate systems.

### Increment G — Alternative-technology triage

- sourced profiles and transparent triggers;
- journal, hydrostatic, sleeve/plain, gas/foil, magnetic, and specialty options;
- no automatic sizing or unexplained universal ranking.

### Increment H — Release hardening

- full calculation/data/browser suite;
- accessibility audit;
- performance and mobile review;
- README, Background tab, examples, and plan status update;
- maintainer end-to-end verification.

## Explicit Non-Goals for V2

- claiming manufacturer interchangeability;
- designing an active magnetic bearing controller;
- sizing air, foil, journal, or hydrostatic bearings from first principles;
- full nonlinear rotor-dynamic analysis;
- thermal equilibrium prediction without heat-generation and heat-transfer models;
- preloaded-pair life calculations without stiffness/load-deflection data;
- automatic fit, tolerance, or clearance approval without linked shaft/housing conditions;
- hiding uncertainty behind a single opaque recommendation score.

## Source Set to Use During Implementation

Primary implementation sources should be official manufacturer catalogs and standards pages. The initial set is:

- [NTN *Ball and Roller Bearings*, catalog No. 2203/E](https://www.ntnglobal.com/en/products/catalog/en/2203/index.html);
- [NTN *Rolling Bearings Handbook*](https://www.ntnglobal.com/en/products/catalog/pdf/9012E.pdf) for arrangements, clearance, preload, lubrication, and application guidance;
- [NTN *Precision Rolling Bearings*](https://www.ntnglobal.com/en/products/catalog/pdf/2260E-all.pdf) for spindle arrangements and adjustable preload concepts;
- official manufacturer lubrication catalogs and relubrication guidance;
- [NASA oil-free turbomachinery research](https://ntrs.nasa.gov/citations/20050215290) for foil/gas-bearing application context;
- [ISO 14839 series pages](https://www.iso.org/standard/93607.html) for active-magnetic-bearing terminology and system considerations;
- official plain/sintered-bearing manufacturer handbooks for non-rolling alternatives.

Record the exact edition, URL, retrieval date, and table/page for every implemented formula, catalog row, and triage threshold. Secondary textbooks may explain theory but should not override current primary-source limits.

## Definition of Done

V2 is done when a user can:

1. search a genuinely useful range of shaft sizes and rolling-bearing series;
2. understand every input and every graph without outside explanation;
3. see the selected bearing geometry and load path;
4. model or at least correctly classify common two-bearing arrangements;
5. understand preload choices and the limits of available calculations;
6. specify grease, oil, unknown, special, or no-lubricant operation;
7. receive credible alternative-technology prompts outside the rolling-bearing design space;
8. save, export, reload, and reproduce an analysis;
9. audit equations, catalog sources, exclusions, warnings, and applicability limits;
10. distinguish a screening result from a final released bearing-system design.
