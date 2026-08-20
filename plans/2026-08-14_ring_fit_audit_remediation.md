# Ring Fit Calculator: Audit Remediation

Date: 2026-08-14

## Context

An audit of `tools/ring-fit/` and `pycalcs/interference_fits.py` found the core elasticity
to be correct (thick-cylinder compliance, Lamé surface stresses, and rotating-disk growth all
check out by hand) but turned up eight correctness bugs, two mislabeled material presets, one
wrong failure criterion, several missing physical effects, and a set of UI defects. This plan
covers the repairs plus the two capabilities the audit recommended: a Check mode that evaluates
a fit the user already has, and an mm/inch unit toggle.

Branch: `task/ring-fit-required-interference`.

## Phase 1: Engine correctness

1. **Non-finite input guard.** `_validate_positive` and `_validate_nonnegative` use `value <= 0`,
   which is `False` for NaN, so a blank UI field flows through the whole analysis and returns
   zeros with an `unacceptable` verdict. Add `math.isfinite` to every validator and a matching
   client-side check in `readInputs()`.
2. **Assembly temperature practicality.** `_sizing_assembly_temperatures` has no floor. A 20 mm
   shaft in a 200 mm hub prints "Shaft cooling only: -283.0 °C" next to an `acceptable` status.
   Add tiered feasibility (dry ice at -78 °C, liquid nitrogen at -196 °C, absolute zero) and
   surface the tier plus a warning. Do the same on the hot side for steel temper limits.
3. **Hub heating target below maximum service temperature.** When the hub-only assembly target
   is at or below the top of the service envelope, the joint can unseat under a thermal gradient.
   Raise a warning.
4. **Torque-or-axial duty.** `required_torque_nm` is validated strictly positive, which rejects
   pure axial retention (bushings, liners, seal carriers). The pressure model already combines
   the two vectorially. Relax to "torque or axial force must be positive".
5. **Duplicate governing candidate.** `analyze_interference_fit` appends the yield-margin
   candidate twice. Remove the duplicate.
6. **Vectorial slip in `analyze_interference_fit`.** The checker evaluates torque and axial slip
   independently while the sizer combines them as a resultant. The two halves of one module
   disagree about the same physics. Move the checker onto the resultant, keeping the separate
   per-axis capacities as reported values.
7. **Bisection cost.** `_maximum_allowable_pressure_mpa` runs 52 fixed iterations and recomputes
   the pressure-independent rotating-disk profile inside every one. Hoist the profile out of the
   loop and stop on a relative tolerance. This is the dominant runtime cost under Pyodide and
   blocks live recalculation.

## Phase 2: Material data

`MATERIAL_PRESETS` gains a `condition` string and a `source` string on every entry, both shown
in the UI.

| Preset | Problem | Fix |
| --- | --- | --- |
| `steel_4140_qt` | 655 MPa is the normalized yield, not quenched and tempered. It is the default shaft material. | Rename to `steel_4140_normalized`, add a true `steel_4140_qt` at 1100 MPa. |
| `steel_4340_qt` | 470 MPa is the annealed yield. | Rename to `steel_4340_annealed`, add a true `steel_4340_qt` at 1180 MPa. |
| `cast_iron_gray` | Modeled with von Mises against a yield strength it does not have. | Add a brittle failure criterion (see Phase 3). |
| `bronze` / `bronze_bearing` | Byte-identical datasets under two dropdown entries. | Give `bronze_bearing` real C93200 properties. |
| `brass_7030` | Thermal expansion 19.1, cartridge brass is 19.9. | Correct the value. |
| `steel_1020` | 210 MPa is hot-rolled; the label does not say. | State the condition. |

Preset key renames need a back-compatibility alias map so existing shared URLs keep working.

## Phase 3: Model additions

1. **Surface roughness smoothing.** Real interference is reduced by asperity flattening at
   assembly. Follow DIN 7190: effective interference is the specified interference minus
   `0.8 (Rz_shaft + Rz_hub)`. For a ground 50 mm fit that is 4 to 8 µm, a large fraction of a
   typical window, and it is always a loss on the slip side. New inputs `shaft_roughness_rz_um`
   and `hub_roughness_rz_um`, defaulting to 0 so existing behavior and tests are unchanged, with
   a UI default matching a ground finish.
2. **Length-to-diameter credit cap.** Torque capacity is currently linear in fit length forever:
   L/d = 10 on a 50 mm shaft returns 0.0034 mm required interference with no warning. Pressure
   and micro-slip concentrate at the fit ends. Cap credited length at L/d = 1.5 and warn above it.
3. **Brittle failure criterion.** Gray iron has no yield point, and its compressive strength is
   roughly three to four times its tensile strength. Add `failure_criterion` to the preset schema
   (`von_mises` or `brittle`), carry `tensile_strength_mpa` and `compressive_strength_mpa`, and
   evaluate brittle members with a Mohr-Coulomb margin instead of von Mises.
4. **ISO 286 window grading.** A feasible answer of 0.1343 ±0.0014 mm on a 50 mm fit is roughly
   IT2 to IT3 and not manufacturable in a normal shop. Map the computed window onto IT grades and
   name a candidate shaft/bore pair so the output lands on a drawing.
5. **Assembly and release forces.** Report the axial force to press the joint together cold and
   the force to push it apart. Both fall out of quantities already computed.
6. **Friction presets.** The friction coefficient is the dominant uncertainty, defaults to 0.15,
   and sits behind Expert Mode as a bare number. Add a preset table keyed to material pair and
   assembly method, per DIN 7190.

## Phase 4: Check mode

The rewrite turned a checker into a sizer. Most users arrive with a drawing already in hand and
want a verdict, not a fresh size. Restore that path as a second mode over the same engine.

- Mode toggle at the top of the input column: Size (solve for interference) and Check (evaluate
  a given fit).
- Check mode inputs: interference minimum, nominal, and maximum, or shaft and bore limits that
  the tool reduces to an interference band.
- Check mode calls `analyze_interference_fit`, which keeps its own result shape. Route the two
  functions through one dispatcher in the page so tabs, derivations, and settings are shared.
- Bring `analyze_interference_fit` up to the sizer's standard first: roughness, L/d cap, brittle
  criterion, assembly practicality, and the vectorial slip fix all apply to both entry points.

## Phase 5: UI repairs

1. **Window graphic.** `.window-feasible` is `inset: 0` and `.window-target` is pinned at
   `left: 50%`, so the band always spans the full track and the tick never moves. Only the color
   changes. Drive both from the actual values, add numeric end labels, and show the overlap when
   the window is negative.
2. **Isothermal chart.** When minimum and maximum service temperature are equal the sweep is a
   single point and the envelope canvas draws nothing. Widen the display span around the single
   temperature and mark the operating point.
3. **Infeasible labeling.** When no window exists, results are evaluated at the required minimum
   but the panel still reads "At the recommended target" next to a tile reading "No target".
   Switch the heading to match what was evaluated.
4. **URL state ordering.** `shared/url-state.js` initializes on `DOMContentLoaded`, before the
   material selects have options, and `populateMaterials()` then hard-sets both selects and
   overwrites custom properties. Shared links silently reset materials. Re-apply URL state after
   the presets populate.
5. **Keyboard and screen reader access.** The derivation triggers are click handlers on divs with
   no role or tabindex. The tab strip has no `role="tablist"`, `role="tab"`, `role="tabpanel"`,
   or `aria-selected`. Tooltip triggers are unlabeled buttons whose text lives only in a CSS
   `::after`. Fix all three.
6. **Micrometre display.** 0.0468 mm is four leading zeros of noise. Show interference in µm,
   which is how tolerances are discussed, and keep mm as a secondary readout.
7. **Export.** Add copy-to-clipboard and CSV download of the result set.
8. **Chart polish.** Add a hover readout, and lay the legend out from measured text width instead
   of fixed pixel offsets that collide at narrow widths.

## Phase 6: Units

Wire `shared/units.js` into the page so length, force, torque, temperature, pressure, and speed
switch between MMGS and imperial. Every input carries a quantity type, every formatter reads the
active system, and the unit labels update in place. Interference stays in µm or mils.

## Phase 7: Tests and docs

- Regression tests for each Phase 1 bug: non-finite rejection, assembly temperature floors, the
  torque-or-axial path, and the vectorial slip fix.
- Tests for each Phase 3 addition: roughness reduction, L/d cap, brittle criterion, IT grade
  mapping, assembly and release forces.
- A `tools/ring-fit/test-cases/` directory, which this tool lacks while six other tools have one.
  Cases: default steel pair, aluminum hub hot, infeasible cast iron, axial-only retention,
  isothermal, and a Check mode fit.
- Update `README.md`, the Method tab, and the `catalog.json` entry to match the new scope, and
  document the plane-stress assumption and the first-yield cap that the audit flagged as unstated.
- Re-run `scripts/generate_sitemap.py` and `scripts/inject_seo_meta.py` after the catalog edit.

## Verification

- `pytest tests/test_interference_fits.py` green, including the existing 17 cases.
- Hand-checked values preserved: default case interface pressure 72.7 MPa, hub von Mises
  169.7 MPa, hub bore centrifugal growth 0.584 µm diametral at 3600 rpm.
- Load the page and exercise both modes, both unit systems, the isothermal case, an infeasible
  case, and a shared URL carrying a non-default material.

## Deviations from this plan

Three things came out differently once the work started.

- **Material preset keys were not renamed.** The plan called for renaming `steel_4140_qt` and
  `steel_4340_qt` and adding an alias map. Correcting the values in place and adding separate
  `steel_4140_normalized` and `steel_4340_annealed` entries does the same job without breaking
  any shared URL, so no alias map was needed.
- **No ISO 286 fit designations.** The plan said to name a candidate shaft/bore pair such as
  H7/s6. Those letters need the fundamental deviation tables, which this repo does not carry,
  and shipping half-remembered values would repeat the exact defect the audit found in the
  material presets. The window is graded by IT number only, which comes from the published
  formula and is verifiable.
- **The checker gained a speed input.** Not in the original plan. Without it, Check mode could
  not see centrifugal fit loss or rotating stress, which would have left the two modes covering
  different physics.

## Follow-up: the assembly block was reworked

Review after the first pass flagged the assembly section as confusing, and it was right. Three
unrelated things were tangled in one place:

1. `assembly_temperature_c` was an input on the checker only, and it drove a whole third stress
   state (`state_name="assembly"`) that, at its default of 20 C, was a byte-identical copy of
   the reference case.
2. The same input fed a `hub_only_*` feasibility block that computed what pressure would exist
   if you forced the parts together at a temperature that does not clear them. Eight output
   keys, none of which the UI read, answering a question nobody asks.
3. The genuinely useful inputs, `hub_max_assembly_temp_c` and `shaft_min_assembly_temp_c`,
   already existed but were never exposed in the UI.

Meanwhile the sizer had no assembly temperature input at all, because there the temperature is
solved for. The two modes disagreed about what assembly temperature even was.

Resolution: assembly temperature is an **output** in both modes. The parts have to reach
whatever opens the maximum interference plus the slip clearance, so the tool solves for that
and costs three routes (heat the hub, chill the shaft, both), then recommends the cheapest one
that fits. The **input** is what the shop can do, which is what `hub_max_assembly_temp_c` and
`shaft_min_assembly_temp_c` already expressed; those are now exposed in Expert Mode in both
modes and default to blank, meaning no limit.

`_assembly_temperatures` and `_sizing_assembly_temperatures` collapsed into one
`_thermal_assembly_plan` returning one key set, so both modes now render from the same code.
`assembly_temperature_c`, the redundant assembly state, and the `hub_only_*` outputs are gone.

### Second pass: planned assembly temperatures

Removing `assembly_temperature_c` fixed the incoherence but lost something worth having. The
question a shop actually asks is not only "what would let this slip together" but "I can heat
to 150 C, how much press force is left?" Fully clearing a fit often needs more heat than the
part can take, while heating part way removes most of the force.

So the assembly block now answers both. `hub_assembly_temperature_c` and
`shaft_assembly_temperature_c` are the planned temperatures, defaulting to ambient, and the
plan reports the interference still in the way, the press force, and the reduction against the
cold baseline. The solved-for temperatures stay as the other half of the answer.

This is not a return of the old parameter. The old one drove a redundant stress state and a
`hub_only_*` block nobody read; these two produce one concrete number, the press force, and
touch nothing else.

The UI shows the planned temperatures rather than `hub_max_assembly_temp_c` /
`shaft_min_assembly_temp_c`, because a planned temperature is already a statement of what the
equipment can reach, and four temperature inputs in one section is how the confusion started.
The capability limits stay in the Python API, documented and tested, where they constrain the
recommended route.

Press-on and push-off separated while doing this. Pressing is what crushes the roughness
peaks, so press-on force uses the interference as drawn; a settled joint has already lost
them, so push-off uses the smoothed value. Press-on on the default case went from 117 kN to
238 kN, which is the correct number for sizing a press.

A latent bug surfaced during verification and was fixed: a diameter a few float bits over an
ISO 286 step boundary (50.0000016 mm after a unit round trip) dropped into the next step and
shifted the reported grade by a whole number. The step comparison now carries a 10 nm
tolerance, and the unit round trip preserves enough precision to land back on the original.

## Out of scope

- Elastic-plastic (contained plasticity) fits, which DIN 7190 permits and which the first-yield
  cap currently forecloses. Documented as a limit, not implemented.
- Plane-strain compliance as a user-selectable option. The plane-stress assumption gets stated
  in the Method tab instead.
- Thermal gradients, transients, and temperature-dependent properties.
- Fretting fatigue life.
