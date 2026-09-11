# Schema lab migration report

Status: Phase 2 complete. The full synthetic corpus migrates to contract v0.1.0
with zero validation errors and no unexplained loss.

Regenerate with `python3 scripts/schema_lab.py migrate`. The machine-readable
form is [`migration-report.json`](../fixtures/schema-lab/v0.1.0/migration-report.json);
this document explains what the entries mean.

## What moved

| Change | Count | What it was |
|---|---|---|
| `duplicate_state_attribute_stripped` | 228 | State-fixed facts copied onto observations |
| `attribute_moved_to_observations` | 13 | Observation context wrongly fixed on a state |
| `legacy_state_mapped` | 12 | `material_state` values mapped to precise keys |
| `temper_recovered` | 6 | Temper present only in a display label |
| `label_split` | 5 | Labels of the form `T6 · plate` |
| `conditioning_state_named` | 4 | Named conditioning states |
| `state_dissolved` | 3 | States defined only by product form |
| `adversarial_additions` | 11 | New entities for cases the corpus lacked |

Entity counts after migration and overlay: 27 taxa, 33 materials, 36 states,
368 observations, 13 properties, 5 property groups.

## The three changes that did real semantic work

### 1. The 228 stripped duplicates were provably duplicates

The legacy corpus copied every state-fixed fact onto each of that state's
observations, so `formulation`, `reinforcement`, `layup`, `fiber_mass_fraction_1`,
and `material_state` appeared in both containers. The contract forbids this,
because a fact stored twice can disagree with itself.

Before stripping anything, migration verified the claim that makes removal safe:
across all 360 observations there were **228 exact duplicates, zero conflicts,
and zero cases where an observation carried a state-only key its state did not
fix.** `test_stripped_state_attributes_were_genuine_duplicates` re-derives this
against the legacy corpus on every run rather than trusting the number recorded
here.

### 2. Three states were dissolved because product form is not an identity

`PolyDemo ABS-A10 injection molded`, `PolyDemo PTFE-F10 compression molded`, and
`PolyDemo HDPE-H10 extruded` were named states whose only defining attribute was
product form. Under the checkpoint 1 decision, product form is observation
context, so these states had no identity left once the form moved down.

They are not lost. Their observations now attach directly to their material and
carry the form as a condition, and the drill-down level is *derived* from that
condition. A user can still land on the injection-moulded view; it is generated
rather than stored.

The aluminium states behave differently and were kept: their labels also
embedded a form (`T6 · plate`), but the temper survives as a real identity once
the form moves down, so only the label was split.

### 3. Temper existed only in display labels

The legacy corpus never stored temper as structured data. `T4`, `T6`, `T651`,
and `T73` lived in the state label, and `fixed_conditions` held product form
instead — an inversion of the correct placement in both directions at once.
Migration recovers the temper as a registered `temper` attribute and moves the
form to observations.

Splitting labels risks collapsing two states into one if a material had both
`T6 · plate` and `T6 · extrusion`. Migration checked for this and found no such
collision.

## Things that were deliberately not guessed

- **`material_state` values.** All eight legacy values map to `heat_treatment`
  or `work_condition` through an explicit table. An unmapped value produces an
  `unmapped_legacy_state` report entry and is dropped pending review rather than
  being guessed from its spelling. There are currently none.
- **Conditioning states.** `dry as molded` and `conditioned` become a registered
  `conditioning_state` attribute derived from the *label*. The measured moisture
  number stays on the observations and is never used to infer the state, which
  is the direction the matrix explicitly prohibits.
- **Designations.** Every legacy designation was an unqualified string. They are
  now `{"system_id": "synthetic_fixture", "value": ...}`. The migration does not
  attempt to infer real standards bodies from the spelling of synthetic
  designations.
- **The second source.** `synthetic-fixture-b` supplies exactly one observation:
  the deliberate disagreement with `synthetic-fixture` about AX70-T6 yield
  strength in the LT direction. It is registered as a distinct source, because
  merging it would silently destroy the conflict fixture.

## Recovering source precision

The legacy corpus stored canonical SI values only, with no record of what the
source printed. Under the checkpoint 1 unit decision the canonical value drives
display, but the *precision* of the original claim still has to survive, or
converting to another unit invents digits.

Migration recovers precision from how each number was written and stores it as
`result.reported.significant_figures`. One migration assumption is recorded
explicitly rather than hidden: trailing zeros in an integer are ambiguous, so
`50` could assert one or two significant digits. Read literally it is one, which
would render Shore A 50 as `5e+01`. Migration therefore applies a floor of two
significant figures, defined in `MINIMUM_MIGRATED_SIGNIFICANT_FIGURES`.

Modelling conversion as affine also removed a special case. The legacy corpus
expressed conversion as a single `display_scale` factor, which cannot express
temperature at all, so `prototypes/assets/search-core.js` hardcodes a 273.15
subtraction in its formatter and branches on the unit to decide when to apply
it. The prototype's numbers are correct; the conversion rule just lives in
rendering code rather than in data.

The new contract stores conversions as `value * factor + offset`, so temperature
stops being a branch. Adding Fahrenheit needs a registry entry rather than
another special case in a renderer, which matters because the unit preference
decided at checkpoint 1 will multiply the number of unit paths.

## Cases the corpus could not exercise

The legacy corpus is 360 point values with no uncertainty, no lifecycle, and no
structured locators, so migrating it alone cannot prove the contract handles
harder shapes. Eleven entities were added as a separate overlay — not as edits
to the migration — so losslessness stays provable and every synthetic addition
stays auditable.

The overlay adds one commercial grade with no standard designation, browsing
under a chemistry primary path and a composite supplemental path, with:

- a source-reported interval and a one-sided lower bound;
- a point value with separate standard-deviation uncertainty and a sample count;
- an explicit `unavailable` assertion and a distinct `not_applicable` assertion;
- a superseded observation and the revision that supersedes it;
- a long structured locator carrying page, table, section, row, column, record;
- and a direct material observation alongside state observations, to prove
  neither flows into the other.

## What the gate proves

- Valid data produces zero errors; the corpus validates clean under both the
  JSON Schema and the semantic validator.
- All 24 negative fixtures fail for their own intended diagnostic code, checked
  individually rather than in aggregate.
- Migration, validation, and projection are deterministic: repeated runs produce
  byte-identical output, enforced by `scripts/schema_lab.py check`.
- Every legacy observation, material, and taxon id survives, and every canonical
  number is unchanged.
