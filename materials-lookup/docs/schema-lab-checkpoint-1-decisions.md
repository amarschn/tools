# Schema lab checkpoint 1 — recorded decisions

Status: approved 2026-08-22 with modifications to decisions 2 and 3

This records the outcome of the review gate posed in
[`schema-lab-review-checkpoint-1.md`](schema-lab-review-checkpoint-1.md). It is a
checkpoint record, not the final contract. Schema Decision 002 is still written
at Phase 5 and is what supersedes or retains
[`schema-decision.md`](schema-decision.md).

## Governing rule adopted at this gate

> If it is a specific material you can purchase, it gets a page of that
> material's properties.

This replaces "does a source deliberately name it" as the primary test for
whether something is a lookup identity. It is a better rule because it is
decidable from outside the data: you ask whether someone could order the thing,
not whether a particular document happened to name it.

The rule needs one refinement to terminate, because purchasability alone runs
past the point of usefulness — plate is purchasable, and so is plate at one
specific thickness. The adopted refinement:

- **Discrete and purchasable → a navigable level.** Temper, product form, named
  formulation, layup. A buyer chooses from a short enumerated list.
- **Continuous → a filter or footnote, never a level.** Thickness, temperature,
  measured moisture, orientation. A buyer specifies a number or a direction
  within a chosen product.

Continuous facts stay visible on the measurement. They just never generate their
own page.

## Decision 1 — taxonomy → material → named state → observation

**Approved.** Named states are landable lookup targets, not filters.

Added requirement: **every level shows a range aggregated from its members.**
Landing on `AX70` shows the range across all tempers, plus the temper options as
onward navigation. Landing on `AX70 T6` narrows that range. A user who does not
know which temper they want is not blocked; they see the envelope and drill down
when ready.

This makes the sparse-page concern from the review document less severe: an
intermediate page is never empty as long as anything beneath it carries data.

## Decision 2 — condition placement

**Modified.** The review document proposed that product form is measurement
context only. The adopted decision is that product form is a **navigable level**:

```text
AX70  →  AX70 T6  →  AX70 T6 plate  →  measurements
```

At `AX70 T6` a range must be reported across the forms beneath it, and the user
downselects to processing condition to narrow it.

### Storage does not change; navigation does

The important separation this gate surfaced is that **where a fact is stored and
what a user can land on are two different decisions.** The adopted model keeps
`product_form` in `observation.conditions` exactly as the matrix in
[`state-condition-matrix.md`](state-condition-matrix.md) specifies, and derives
the drill-down level from it in the compiler.

Reasons to derive rather than store:

- A stored named state must be something a source actually named. Manufacturing
  states out of whatever condition values happen to appear in the data is the
  failure the matrix's decision procedure exists to prevent — it is the same
  error as inventing a conditioning state from a measured moisture number.
- Product form is only meaningful for some material classes. A molded polymer
  has no plate/extrusion distinction, and a stored level would force an empty or
  synthetic value for every such material.
- Deriving keeps the reversal cheap. If real sources turn out to treat form as
  part of the published identity, promoting it to a stored state is a compiler
  change, not a re-modeling of every observation.

The user-visible result is identical either way. The difference is only in what
the validator is allowed to accept.

### What this requires from the contract

- The condition registry gains a `navigable` flag distinguishing conditions that
  generate drill-down levels (`product_form`) from those that remain filters
  (`thickness_m`, `orientation`, `temperature_K`).
- Only enum-valued conditions may be marked navigable. A `number` or
  `number_interval` condition marked navigable is a validation error.
- Range projections must be computed at every level, including levels derived
  from conditions rather than stored entities.
- A material or state with observations that do not name a navigable condition
  still renders — the drill-down level is absent, not empty.

## Decision 3 — result forms and units

**Modified.** The review document framed the reported form as what the user
sees, so that the page matches the source document. That framing is rejected.

The adopted decision: **display units are a user preference.** Metric is the
default. Imperial is available. A user may override the unit for an individual
property rather than only switching wholesale. Displayed numbers are not
expected to match the source document's printed units, and that is acceptable —
a reader comparing against a datasheet in different units can convert if they
care.

### Consequence: canonical becomes the source of truth for display

This inverts the roles proposed at the gate. `result.canonical` is what the UI
computes and renders from, because it is the only form that can be converted
into an arbitrary user-selected unit. `result.reported` is no longer a display
form.

`result.reported` is still retained, for two reasons that are not about display:

1. **Audit.** Verifying an ingest was correct requires knowing what the source
   printed, independent of what the system computed from it.
2. **Significant figures.** This is the load-bearing one. A source printing
   `2.81 g/cm^3` has asserted three significant figures. Stored only as
   `2810 kg/m^3`, that precision is unrecoverable, and rendering it in an
   arbitrary user-selected unit will invent digits the source never claimed —
   `530 MPa` becomes `76.8695...  ksi`. The current builder already recognizes
   this problem and carries an `uncertainty.kind == "implied"` form with an
   explicit `sigfigs` count; the new contract must preserve equivalent
   information or regress.

Uncertainty remains a separate field and must convert along with the value.

### New scope this creates

A unit-preference system is not currently in the plan or the TODO. It needs:

- a units registry mapping each `quantity_kind` to its permitted display units
  and conversion factors, with metric and imperial sets;
- per-property display-unit override, persisted client-side;
- significant-figure-aware formatting driven by source precision rather than a
  fixed `display_precision` per property; and
- golden tests covering conversion correctness and digit count, including the
  case where a converted value must not gain precision.

The existing static builder renders canonical SI units only
(`scripts/build_site.py`), so this is genuinely new work rather than a
refactor.

## Decision 4 — property IDs and designations

**Approved** for the property renames: `yield_strength` becomes
`tensile_yield_strength`, `tensile_strength` becomes
`ultimate_tensile_strength`, and the former names survive as search aliases
rather than stored identities. Rationale accepted at the gate: specificity
matters, and bare `strength` must route to clarification rather than guess.

The structured `{system_id, value}` designation form was not separately
contested and is **carried as proposed**, on the same specificity rationale — a
designation number without its issuing system cannot be disambiguated from a
collision in another system. Flag this if it was meant to be a narrower
approval.

## Effect on the plan

Phase 2 proceeds, with these additions to its scope:

- the condition registry's `navigable` flag and its validation rules;
- level projections for derived navigable conditions, not only for stored
  entities; and
- explicit source-precision capture, since the reported form no longer carries
  it implicitly by being what is displayed.

The unit-preference system is a Phase 3/4 concern — it affects serving and
interaction, not the canonical contract — but it is recorded here because it was
decided at this gate and would otherwise be lost.
