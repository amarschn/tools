# Heatsink Designer — Model Scope, Applicability, and Progressive Disclosure Feedback

> **Purpose:** Capture the most important product-level feedback from the recent heatsink designer audit so it can be handed to Claude for deep consideration. This document is intentionally broader than a solver spec. It focuses on model fit, user guidance, problem framing, and how progressive disclosure should work in a real design workflow.

---

## 1. Executive Summary

The main architectural gap is no longer "missing equations" or even "missing features."

The larger problem is that the tool is becoming increasingly capable for one specific class of problem, while still allowing users to approach it as if it were a general-purpose heatsink design environment.

That is risky.

Right now the tool does not force the user to declare what physical problem they are actually solving:

- IC or module on a flat plate-fin sink
- flat housing or motor pad mounted to a sink
- distributed source on a plate
- curved or radial body with fins
- enclosure wall acting as a spreader

Because the workflow does not branch by problem archetype, the same labels and assumptions are stretched across incompatible use cases. The result is a tool that can look more certain than it should.

### Main recommendation

Before adding more solver sophistication, improve the tool's epistemic safety:

1. Add a front-end applicability gate.
2. Separate problem archetypes explicitly.
3. Separate boundary-condition modes.
4. Separate heat-entry geometry from contact/TIM geometry.
5. Reframe progressive disclosure around decisions and confidence, not only equations.

---

## 2. Core Thesis

This tool should stop pretending the primary question is:

> "What is the thermal resistance of this heatsink?"

For real users, the primary questions are:

1. Is this model applicable to my hardware at all?
2. What temperature node am I actually constraining?
3. What is limiting the design right now?
4. Which change is most likely to help?
5. How much confidence should I have in the prediction?

The UI, data model, and disclosure structure should be organized around those questions.

---

## 3. Supported Use Classes

### Good fit

These should be treated as the intended target of the current tool:

- Flat straight plate-fin heatsink
- Single dominant mounted source
- Flat contact surface
- Air cooling only
- Channel-aligned flow or simplified fan-limited flow
- One meaningful inlet-air or ambient-air temperature
- Steady-state design questions

### Use with caution

These are not necessarily wrong to model, but the tool should explicitly warn the user that the abstraction is stretched:

- Module baseplates
- LED boards or MCPCBs
- Chassis wall spreaders
- Motor housings with a flat mounting pad
- Unducted fan cooling
- Enclosure recirculation
- Mixed convection
- Cases where heat-entry area and contact area differ materially

### Out of scope / guide away

These should trigger an out-of-scope warning or a strong caution state before calculation:

- Radial-fin motor bodies
- Cylindrical or curved housings
- Cast fin bodies with non-plate-fin geometry
- Pin-fin or radial-fin heatsinks
- Impingement cooling
- Strongly angled or crossflow-dominated cooling
- Swirl or plenum-driven flow fields
- Multiple separated sources
- Distributed winding-loss problems
- Transient duty cycles
- Systems where the "heatsink" is only one segment of a larger conduction network

---

## 4. Key Feedback and Why It Matters

### 4.1 The Current `source footprint` Is Overloaded

#### Problem

The current `source footprint` is doing two different jobs at once:

- defining the heat-entry patch used for spreading resistance, and
- defining the contact area used to convert TIM data into `R_theta,cs`.

For many real systems, those are not the same area.

Examples:

- silicon die vs package tab
- LED die vs MCPCB pad
- winding hotspot vs motor frame contact patch
- internal module loss region vs external baseplate contact area

#### Why this is dangerous

If the same area is used for both effects when it should not be, the tool can bias both spreading resistance and interface resistance in the same direction and make the result look more self-consistent than it really is.

This is one of the highest-priority conceptual fixes.

#### Implementation ideas

- Split `source footprint` into two first-class concepts:
  - `heat-entry area`
  - `contact / TIM area`
- Default to a checkbox or toggle:
  - `Contact area same as heat-entry area`
- Use `heat-entry area` only for:
  - spreading resistance
  - spreading heatmap / source overlay
  - base-plane localization
- Use `contact area` only for:
  - TIM impedance conversion
  - conductivity + bondline conversion
  - interface-temperature interpretation
- Show both areas in the preview with different outlines or colors.
- Add a caution rule:
  - if `contact area / heat-entry area` differs significantly, surface a note that interface and spreading are now being treated separately by design.

#### Acceptance signal

A user cooling a motor housing or module baseplate can model:

- internal hotspot area,
- external contact area,
- interface resistance,

without abusing a single geometry field.

---

### 4.2 Model Scope Is Too Hidden

#### Problem

The tool fundamentally assumes:

- one flat rectangular base,
- one straight plate-fin family,
- one rectangular heat-entry region.

That scope does exist in the copy, but it is too easy to miss.

#### Why this matters

A user can get deep into the workflow before realizing the abstraction is wrong for:

- a motor housing,
- a curved body,
- a cast sink,
- a radial fin arrangement,
- a saddle-mounted geometry,
- a non-flat interface.

#### Implementation ideas

- Add a visible scope chip or banner near the title:
  - `Current model: flat plate-fin heatsinks in air`
- Add a mandatory early selector:
  - `What are you cooling?`
- If the selected archetype is unsupported, do one of the following:
  - stop the workflow and explain why, or
  - allow entry but switch the whole tool into `Use with caution / Out of scope`.
- Keep the full purpose/scope write-up in the background tab, but do not rely on it as the primary guardrail.

#### Acceptance signal

The user should know whether the geometry family is even appropriate before entering detailed dimensions.

---

### 4.3 Boundary Conditions Are Still Too Semiconductor-Shaped

#### Problem

The current workflow still centers everything on:

- `Target Source / Junction Limit`
- `R_theta,jc`

That matches many electronics problems, but not many non-IC heatsink design problems.

#### Why this matters

Many real cases instead have:

- a housing temperature limit,
- a touch-safe surface limit,
- a winding limit coming from another model,
- a maximum base temperature,
- a required sink resistance only.

Forcing all of these through `junction temperature + R_theta,jc` creates fake precision.

#### Implementation ideas

- Add a `Boundary Condition Mode` selector with at least:
  - `Target source / junction temperature`
  - `Target case temperature`
  - `Target base temperature`
  - `Required sink R_theta only`
- Adapt visible inputs by mode:
  - `source/junction mode` needs `R_theta,jc`
  - `case mode` does not
  - `base mode` collapses upstream path entirely
  - `required sink R_theta only` becomes a sink-sizing tool
- Adapt result labels and ladder nodes by mode.
- For non-source modes, demote or hide source-node outputs unless the user explicitly opts into upstream estimation.

#### Acceptance signal

A user modeling a motor housing or external case can use the tool honestly without inventing an internal `R_theta,jc`.

---

### 4.4 `Ambient` Is Easy to Misuse in Forced Systems

#### Problem

The current `Ambient` input is easy to read as room temperature.

That is often wrong in forced systems, where the correct value is the inlet air temperature reaching the sink.

#### Why this matters

This is one of the most common thermal-design mistakes:

- room air is 25 C,
- but inlet air at the sink is 40 C or 55 C due to recirculation or enclosure heating.

The tool will look precise while being wrong at the boundary-condition level.

#### Implementation ideas

- Relabel based on cooling mode:
  - natural convection: `Ambient Air Temperature`
  - forced / fan: `Cooling Air Inlet Temperature`
- Add a short inline note:
  - `Use the air temperature entering the heatsink, not room air, if they differ.`
- Optionally support both:
  - `room/reference temperature`
  - `sink inlet temperature`
  but only solve with inlet temperature.
- Surface a diagnosis warning if the user is in fan/forced mode and no inlet-vs-room distinction has been acknowledged.

#### Acceptance signal

A forced-flow user should be nudged toward the correct temperature boundary condition before calculation.

---

### 4.5 The Airflow Model Is Narrower Than the UI Suggests

#### Problem

Current labels like `Approach Velocity` and `Fan Curve` imply general forced-cooling support.

The backend actually models a much narrower case:

- channel-aligned plate-fin flow,
- simplified bypass,
- simplified fan/system intersection.

#### Why this matters

The current UI can invite misuse for:

- crossflow,
- angled flow,
- impingement jets,
- blowers into plenums,
- nonuniform suction-side flow,
- distorted fan installation effects.

#### Implementation ideas

- Add an airflow arrangement selector:
  - `Channel-aligned stream`
  - `Unducted axial fan over sink`
  - `Crossflow / angled flow`
  - `Impingement / plenum`
- Only the first two should be treated as supported by the current solver.
- Unsupported airflow arrangements should trigger `Use with caution` or `Out of scope`.
- Make the `Fan Curve` mode wording explicit:
  - `Simple fan-curve operating point (aligned flow approximation)`
- If future work adds tabular fan curves, keep that separate from geometric applicability.

#### Acceptance signal

The UI should no longer imply that any fan or any forced-air setup can be modeled as long as the user types a velocity.

---

### 4.6 Natural-Convection Misuse Is Still Too Easy

#### Problem

The backend assumptions are reasonably explicit, but the frontend does not ask about nearby walls, tops, enclosure ceilings, or partially chimney-like configurations.

#### Why this matters

Natural convection is highly sensitive to surrounding geometry and orientation.

The current model is much more trustworthy in open air than inside an enclosure with:

- a nearby wall,
- a roof above the fin exit,
- stacked boards,
- a partial chimney,
- obstructed intake/outlet.

#### Implementation ideas

- Add simple applicability questions when `Natural Convection` is selected:
  - `Open to room air?`
  - `Near a wall or roof?`
  - `Inside enclosure?`
  - `Air path obstructed above fins?`
- These do not need to change the solver initially.
- They should feed an applicability scorecard and warnings.
- Add explicit recipes:
  - `If the sink is inside a small enclosure, use inlet air from the enclosure thermal model, or treat this tool as optimistic.`

#### Acceptance signal

A natural-convection user should be warned at input time when the geometry violates open-air assumptions.

---

### 4.7 There Is No First-Class `Problem Archetype`

#### Problem

The tool tries to generalize in copy, but the workflow never actually branches by what kind of hardware the user is modeling.

#### Why this matters

Without an archetype selector, the same terms:

- source,
- case,
- junction,
- interface,
- ambient,

have to carry different meanings for different users.

That is brittle and confusing.

#### Implementation ideas

Add a first-step selector:

1. `Package or module on flat heatsink`
2. `Flat housing or motor pad on heatsink`
3. `Distributed plate source`
4. `Curved or radial body`

Then branch the tool:

- Archetype 1:
  - source/junction language is primary
  - `R_theta,jc` visible by default
- Archetype 2:
  - source/junction language softened
  - case/base targets emphasized
  - `R_theta,jc` optional or hidden
- Archetype 3:
  - spreading language changes
  - distributed-source assumptions explicit
- Archetype 4:
  - current tool marked unsupported
  - suggest alternate modeling route

#### Acceptance signal

The tool should speak the user’s problem language instead of forcing everyone through an electronics vocabulary.

---

### 4.8 Manufacturing and Construction Assumptions Are Underrepresented

#### Problem

The current tool mostly validates geometry arithmetic, but does not bring enough attention to:

- integral vs bonded fin roots,
- extruded vs skived vs cast construction,
- manufacturable spacing/thickness ranges,
- flatness/contact quality,
- interface clamping quality.

#### Why this matters

A design can look excellent numerically while being unrealistic to manufacture or assemble with equivalent thermal performance.

#### Implementation ideas

- Add a `Construction` selector:
  - `Integral extrusion`
  - `Bonded fins`
  - `Skived`
  - `Cast / complex geometry`
  - `Unknown`
- Initially this can drive warnings rather than new physics.
- Add manufacturability guidance:
  - extremely thin fins,
  - extremely dense extrusion,
  - suspicious aspect ratios,
  - base thickness too thin for expected mounting flatness.
- Add an optional future penalty model for non-integral fin-root resistance.

#### Acceptance signal

The tool should warn when the geometry looks numerically valid but physically implausible for the likely manufacturing route.

---

### 4.9 Recommendations Are Too Generic

#### Problem

Current recommendations are mostly physics-generic:

- add emissivity,
- thicken base,
- reduce fin density,
- use a vapor chamber.

#### Why this matters

Those are not equally useful for:

- a package sink,
- a motor housing,
- a chassis spreader,
- a flat interface problem.

#### Implementation ideas

Split recommendations into categories:

- `Most likely limiting factor`
- `High-impact changes`
- `Model-fit cautions`

Key the recommendation engine on:

- problem archetype,
- boundary-condition mode,
- dominant thermal penalty,
- applicability score.

Examples:

- For `flat housing / motor pad`:
  - prioritize contact flatness, pressure, and compound before suggesting more fins.
- For `package/module`:
  - prioritize interface path and spreading when source area is tiny.
- For `unducted fan cooling`:
  - prioritize shrouding or bypass control before higher fin count.

#### Acceptance signal

Recommendations should read like they understand the physical situation, not just the equation that failed.

---

### 4.10 Progressive Disclosure Is Still Too Equation-Centric

#### Problem

The tool increasingly exposes equations, but that is not the same as exposing engineering reasoning.

Right now progressive disclosure still tends to mean:

- more derivations,
- more substitutions,
- more tabs.

That is not enough.

#### Why this matters

Users need layered answers to:

1. What happened?
2. Why?
3. What should I change?
4. Can I trust this model?
5. Where did the math come from?

If the tool starts with raw math instead of diagnosis and applicability, it serves experts only after they have already accepted the model.

#### Implementation ideas

Reorganize results into layers:

### L0 — Summary

- pass / fail / marginal
- source/case/base temperature
- required vs achieved sink `R_theta`
- operating flow point

### L1 — Diagnosis

Show the dominant penalties and what is limiting the design:

- upstream path
- spreading
- convection
- pressure drop / low flow
- inlet-air temperature
- applicability mismatch

### L2 — Math

- equations
- substitutions
- dependency tracing

### L3 — Applicability

- assumptions
- correlation limits
- geometry-family fit
- airflow-fit warnings
- source/contact mismatch

### L4 — Recipes and Background

- worked examples
- archetype-specific approximation guidance
- references

#### Strong recommendation for math disclosure pattern

Of the current disclosure prototypes, the best conceptual direction is:

- **Option D: foundation + tree**

Why:

- shared quantities like `h_conv`, `h_rad`, air properties, Reynolds number, and friction factor are true shared dependencies,
- they should be defined once,
- result-specific chains should reference those shared building blocks,
- this avoids duplication drift while still keeping local result reasoning legible.

Do **not** rely on:

- a pure report view as the main live UI,
- or a naive tree that duplicates shared derivations in multiple branches.

The recommended architecture is:

1. A canonical derivation DAG in data.
2. A `foundation` view for shared building blocks.
3. A result-chain view for local reasoning.
4. Optional report/export rendering from the same DAG.

#### Acceptance signal

The user should be able to answer:

- `What is limiting this design?`
- `Is this model even appropriate?`
- `Where does that number come from?`

without wading through every equation first.

---

### 4.11 Important Design-Level Logic Is Still Hidden or Fragmented

#### Problem

Several design-relevant intermediate quantities exist, but they are not surfaced in a way that builds trust:

- total area breakdown,
- open area derivation,
- bypass penalty,
- actual heat-balance interpretation,
- source/contact-area logic,
- where the temperature rise is being spent.

#### Why this matters

Users need a diagnostic mental model, not just final temperatures.

#### Implementation ideas

Add a dedicated `Design Diagnosis` layer with compact summaries such as:

- `Temperature rise allocation`
  - ambient -> base
  - base -> effective base
  - effective base -> case
  - case -> source
- `Area model`
  - fin area
  - exposed base area
  - total rejecting area
  - open flow area
- `Flow model`
  - volumetric flow,
  - channel velocity,
  - Reynolds / Rayleigh,
  - bypass fraction,
  - pressure-drop losses
- `Dominant penalties`
  - upstream path,
  - spreading,
  - sink resistance,
  - low fin efficiency,
  - flow limitation

#### Acceptance signal

The user should be able to see not only the final answer, but also where the design is losing performance.

---

## 5. Recommended Product Changes

### 5.1 Add an Applicability Gate Before Geometry Entry

This should be the first major step after the title and purpose.

Suggested questions:

1. `What are you cooling?`
   - package/module on flat sink
   - flat housing or motor pad
   - distributed plate source
   - curved/radial body
2. `What kind of cooling?`
   - natural convection
   - aligned forced flow
   - fan-limited aligned flow
   - other / not sure
3. `Is the contact surface flat and approximately rectangular?`
   - yes
   - approximately
   - no

Output:

- `Good fit`
- `Use with caution`
- `Out of scope`

This result should remain visible near the status banner.

---

### 5.2 Separate Boundary Condition Modes

Add a selector that changes both copy and visible inputs:

- `Source / junction temperature limit`
- `Case temperature limit`
- `Base temperature limit`
- `Required sink R_theta only`

This is one of the cleanest ways to make the tool useful for non-IC problems without pretending to know an internal hotspot path that the user does not actually have.

---

### 5.3 Separate `Heat Entry` From `Contact`

Add:

- heat-entry geometry
- contact/TIM geometry

Suggested UI behavior:

- default to `same as heat-entry area`
- expand only when the user untoggles that assumption

Suggested previews:

- red rectangle: heat-entry patch
- amber rectangle: contact patch

---

### 5.4 Split `Ambient` Terminology by Mode

Suggested labels:

- natural mode:
  - `Ambient Air Temperature`
- forced / fan mode:
  - `Cooling Air Inlet Temperature`

Suggested helper copy:

`Use the air temperature entering the heatsink, not the room air temperature, if the two differ.`

---

### 5.5 Add an Applicability Scorecard Near the Main Result

Suggested categories:

- Geometry fit
- Airflow fit
- Boundary-condition fit
- Source/contact abstraction fit
- Correlation validity

Overall outputs:

- `Good fit`
- `Use with caution`
- `Out of scope`

This should be more prominent than the long assumptions list.

---

### 5.6 Reorganize Results Around Decisions

Suggested tab / section structure:

- `Summary`
- `Diagnosis`
- `Math`
- `Applicability`
- `Background`

If the current multi-tab arrangement remains, the result cards should still visually separate:

- summary numbers,
- diagnosis,
- derivations,
- limitations.

---

### 5.7 Add Approximation Recipes

Warnings alone are not enough.

Add short recipes for at least:

#### Package / module on flat sink

- use heat-entry area for the die or module hotspot,
- use contact area for the package tab or baseplate,
- `R_theta,jc` is meaningful here.

#### Flat housing or motor pad on sink

- use case or base target mode,
- only use `R_theta,jc` if you truly have an internal thermal model,
- contact area is usually not the same as internal hotspot area,
- spread view is only meaningful if heat enters through a localized patch.

#### Distributed plate source

- do not use a tiny source footprint just to force a hot spot if the heat is actually distributed,
- consider disabling spread view or using a distributed-source mode.

#### Curved or radial body

- current tool is not appropriate,
- use a radial-fin or body-to-air model instead.

---

## 6. Suggested Data Model Additions

These are implementation-facing ideas that would support the product changes above.

### New front-end state

- `problem_archetype`
- `boundary_condition_mode`
- `heat_entry_length`
- `heat_entry_width`
- `contact_length`
- `contact_width`
- `contact_area_mode`
- `airflow_arrangement`
- `environment_context`
  - open air
  - enclosure
  - near wall / roof

### New derived state

- `applicability_score`
- `applicability_flags`
- `source_contact_area_ratio`
- `dominant_penalty`
- `confidence_level`

### New result categories

- `summary`
- `diagnosis`
- `math_derivations`
- `applicability`
- `recipes`

---

## 7. Suggested Implementation Order

### Phase 1 — Guardrails and labeling

No major physics changes yet.

- Add archetype selector
- Add boundary-condition mode selector
- Relabel ambient by cooling mode
- Add applicability scorecard
- Add strong out-of-scope messaging
- Add recipes / guided copy

### Phase 2 — Geometry and contact-model separation

- Split heat-entry area from contact area
- Update TIM derivation logic
- Update preview overlays
- Update spreading inputs and labels

### Phase 3 — Diagnosis-first results

- Build a diagnosis layer
- Expose dominant penalties
- Add rise allocation and area breakdown
- Reorganize status banner and result groupings

### Phase 4 — Canonical derivation architecture

- Build a canonical derivation DAG
- Render shared building blocks once
- Render result chains from the same source
- Support a report/export view from that DAG

### Phase 5 — Optional physics extensions

Only after the product architecture is safer:

- construction-type penalties
- richer airflow arrangement handling
- tabular fan curves
- distributed source modes
- non-integral fin-root penalties

---

## 8. Concrete Guidance for Claude

If this document is used as an implementation handoff, these principles should govern the work:

1. Do not add more solver sophistication before fixing problem framing and applicability.
2. Do not overload one field with multiple physical meanings.
3. Do not pretend unsupported geometries are merely "advanced cases."
4. Prefer explicit out-of-scope handling over fake generality.
5. Keep the default supported workflow simple and fast.
6. Put diagnosis and model-fit ahead of deep derivations.
7. Build derivation rendering from one canonical data structure, not duplicated HTML strings.
8. Prefer the `foundation + tree` disclosure architecture for math views.
9. Keep the assumptions list, but demote it behind a more actionable applicability summary.
10. Make the tool better at saying "this is not the right model" when that is the correct answer.

---

## 9. Success Criteria

This feedback should be considered successfully implemented when:

- a user is forced to declare the physical problem archetype early,
- unsupported use cases are flagged before detailed input entry,
- source/contact geometry can be modeled separately,
- non-IC users can solve case/base-limited problems honestly,
- forced-flow users are clearly guided to inlet-air temperature,
- results distinguish `summary`, `diagnosis`, `math`, and `applicability`,
- math disclosure no longer duplicates shared values inconsistently,
- the tool becomes more trustworthy even before any new physics is added.

---

## 10. Bottom Line

The next big step for the heatsink designer should not be "more equations."

It should be:

> make the tool explicit about what physical problem it is solving, how well the model fits that problem, and what the user should do next.

That is the difference between a feature-rich calculator and a genuinely trustworthy engineering design tool.
