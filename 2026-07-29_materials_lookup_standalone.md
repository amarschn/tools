# Materials Lookup: Standalone Project Seed Plan

Date: 2026-07-29

Seed plan for a materials property lookup database, developed in a separate
repository and merged into `transparent.tools` later. This document is the
starting context for that new repo. It assumes no knowledge of the tools repo
beyond what is written here.

**Revision note.** Execution now begins with a synthetic-data-only discovery
track. Interaction and data-contract questions are settled with disposable UI
prototypes before any new source research, factual claims, or ingestion work.

---

## 1. What this is

A search-first materials property database. You type a material name, a property
name, or a rough description, and you immediately get a ranked list of matches.
Every number carries its test conditions, its uncertainty, and a citation
specific enough to look up (source plus table or page number).

The bet: MatWeb has far more data than this will ever have and is nearly
unusable. Ansys Granta is excellent and costs thousands of dollars per seat.
Search that actually works over a few thousand well-sourced materials beats
100,000 badly searchable ones for daily engineering use.

### What it is not

- Not a chart tool. No Ashby plots in v1. The existing `materials-explorer` tool
  in the tools repo already does that and keeps doing it.
- Not a calculator. It looks things up. Calculators consume it.
- Not a scraper of commercial databases. See section 10.
- Not a CAD or CAE integration.
- No user accounts, no live pricing, no supplier inventory.

---

## 2. Why a separate repo, and how it merges back

Developed separately because the ingestion pipeline, the build step, and the
data volume are all unlike anything in the tools repo, and because iterating on
schema design inside a repo whose core principle is "single source of truth"
creates friction before the schema has settled.

**Merge criteria.** Merge back when all of these hold:

1. The schema has been stable through at least two independent source ingestions.
2. The database can emit a drop-in replacement for the tools repo's
   `data/materials/materials.json` (see section 9).
3. Search feels instant on a mid-range laptop with the full index loaded.

**Merge mechanics.** Design for these from day one so the merge is a file move:

- Public URLs are `/materials/`, `/materials/<id>`, `/materials/by/<property>`.
  Keep that exact shape in the standalone repo so nothing rewrites at merge time.
- The frontend is one self-contained HTML page plus static JSON. No framework, no
  bundler. The tools repo serves static files from the repo root with no build
  step for pages, and this must not break that.
- Build scripts are Python 3, standard library where possible, and live in
  `scripts/`. The tools repo already runs `scripts/generate_sitemap.py` and
  `scripts/inject_seo_meta.py` on deploy, so an additional build script fits.

---

## 3. Product definition

### Prototype the experience before building it

The first artifacts are decision tools, not production code. Use the same
deterministic semantic fixture to make at least three deliberately different,
disposable UI prototypes:

| Direction | Question it should answer |
|---|---|
| Dense search-first list | How much information can a result row carry before scanning becomes slow? |
| Material-first lookup | Does requiring one material before property selection make the lookup-only boundary clearer? |
| Split list/detail view | Does keeping one selected record visible make repeated lookup faster without encouraging comparison? |
| Explicit query resolver | Is clarification better than guessing when category, material, or property intent is ambiguous? |
| Dual-mode lookup | Can material datasheets and property/category reference ranges share one search box without becoming a full comparison workspace? |

Each direction must cover the same small task set: find a material by exact name,
alias, and misspelling; move from a family to a grade and variant; inspect a
property with several conditioned observations; follow a value to its synthetic
provenance; and focus a concrete material record on one precise property. Small
isolated sketches may be added for observation tables or query clarification when
those questions are not answered by the end-to-end directions.

Keep this spike intentionally cheap:

- One HTML file per direction, backed by the same checked-in fixture and pure
  search/parser contract so the UI—not ranking drift—is what changes. No
  framework, build pipeline, routing, shared UI component library, or production
  styling.
- Set one total model-token and time budget for the entire spike before starting.
  A practical default is at most 4,000 model output tokens and 60 minutes per
  direction, plus one 2,000-token/30-minute comparison pass. Only the winner may
  receive a separately approved refinement pass. The limits are ceilings, not
  targets.
- Stop when the task questions can be evaluated. Do not spend the spike on
  complete settings, SEO, animations, exhaustive responsiveness, or visual
  polish.
- Score every direction on search relevance, hierarchy legibility, condition and
  uncertainty visibility, provenance visibility, keyboard use, narrow-screen
  use, and implementation complexity.
- Record the choice and the rejected tradeoffs. Discard the losing prototypes.
  Reimplement the selected contracts cleanly in `src/`; do not quietly promote a
  spike into the product.

### The core interaction

One search box, focused on page load. Results update as you type. The result list
is heterogeneous and each row is visibly typed:

| Query | Row type surfaced | Action on select |
|---|---|---|
| `6061` | Material | Go to that material's record |
| `6061 yield strength` | Material + property intent | Open 6061 focused on yield observations |
| `yield strength` | Property | Open category-grouped observed ranges |
| `plastic strength` | Category + ambiguous property group | Ask for a strength type, then open a plastics-scoped property view |
| `mild steel` | Broad material concept | Browse matching concrete materials |
| `aluminium` | Category | Browse concrete members; show no category-level values |

Results are capped at roughly 50 rendered rows. Never render 10,000 nodes.

### Property queries

A property term focuses a concrete material record when material intent is also
present. A precise property-only query opens a category-grouped reference view:
top-level categories show derived observed ranges and coverage counts, then
expand through subcategories to individual materials. It is never a flat list
ranked by value. A category + property query opens the same view already scoped
to that category.

A broad term such as `strength` is a typed property group and asks the user to
choose tensile yield, ultimate tensile, compressive, flexural, impact, or another
precise property supported by the corpus.

Property pages combine definitions, units, aliases, lookup guidance, and these
category rollups. Every range is labelled as a projection over covered
observations, with material/state/observation counts and mixed-condition warnings.

### The alias thesaurus

The single highest-leverage cheap component. A hand-written map from what people
type to what the database calls things. Target 300 to 500 entries before launch.

```
stiffness, MOE, elastic modulus   -> property: youngs_modulus
strength                          -> property group: strength (requires clarification)
plastic, polymer                  -> category: polymers
engineering plastic              -> category: engineering_plastics
6061                              -> material identity: al-6061
6061 T6                           -> named state: al-6061-t6
```

Aliases live in typed namespaces for categories, material identities, named
states, properties, and property groups. A phrase may map to several typed
choices, but it may not silently turn a broad concept into one arbitrary
material.

### Comparison

Explicitly out of scope, not deferred. There are no compare controls, flat
value-ranked material lists, "best material" answers, or winner highlighting.
Category ranges are allowed only as fixed, taxonomy-ordered coverage summaries
and are never presented as intrinsic category values. Queries such as `strongest
plastic` should explain the boundary and suggest a precise property reference
query instead.

---

## 4. Data model

The central decision. Store **observations**, not values.

A property is not one number per material. AA7075-T6 has at least six different
tensile yield strengths depending on product form, thickness, and grain
direction. A flat `{"yield_strength": 480e6}` cannot express that, and trying to
force conditioned data into an unconditioned container is what will stall the
project.

### Material record

```json
{
  "id": "al-6061-t6",
  "name": "Aluminium 6061-T6",
  "aliases": ["6061-T6", "6061T6", "AA6061-T6", "AlMg1SiCu T6"],
  "family": ["metal", "aluminium", "6xxx"],
  "designations": {
    "UNS": "A96061",
    "EN": "AW-6061",
    "ASTM": "B209"
  },
  "condition": "T6",
  "prominence": 3,
  "observations": [ ... ]
}
```

`prominence` is shown here as a placeholder. It is one of several competing
answers to the granularity problem, which is unresolved. See section 4.4.

### Observation record

```json
{
  "property": "yield_strength",
  "value": 276e6,
  "unit": "Pa",
  "uncertainty": { "kind": "range", "min": 240e6, "max": 290e6 },
  "basis": "typical",
  "conditions": {
    "temperature_K": 293,
    "product_form": "sheet",
    "thickness_m": [0.0016, 0.0063],
    "orientation": "L"
  },
  "test_method": "ASTM E8",
  "source_id": "mil-hdbk-5h",
  "source_locator": "Table 3.6.2.1.0(b1)"
}
```

**`basis`** is a closed vocabulary: `typical`, `minimum`, `A-basis`, `B-basis`,
`S-basis`, `computed`, `estimated`. Mixing a typical value and a statistical
minimum in the same column without labelling them is the most common way
materials data misleads people.

**`source_locator`** is what makes a number verifiable and is the thing
commercial aggregators omit. A citation without a table number is not checkable.

**`conditions`** keys come from a registered vocabulary so they stay filterable.
Adding a key requires adding it to the conditions registry.

### Uncertainty

Confidence is expressed as a number, never as a badge or a colour.

```json
{ "kind": "range",   "min": 240e6, "max": 290e6 }
{ "kind": "stddev",  "sd": 18e6, "n": 12 }
{ "kind": "implied", "sigfigs": 2 }
null
```

Two hard display rules:

1. **Never show more precision than the uncertainty supports.** A value of
   `544999.9999999999` is a bug, not data.
2. **Never arithmetically average a log-scale property.** Electrical resistivity
   spanning 1e12 to 1e15 has a geometric mean of 3.2e13, not 5.0e14. The existing
   review corpus in the tools repo contains exactly this error, which is a useful
   reminder that mechanical ingestion produces confident nonsense.

Provenance quality is conveyed by naming the source and locator, not by a score.
"MIL-HDBK-5H, Table 3.6.2.1.0(b1)" tells an engineer everything a badge would,
and more.

### Units

All values are stored in coherent SI units, base or derived. Conversion happens
in the frontend for display. This matches the tools repo convention and
`UNITS_DISCUSSION.md` there.

### 4.4 The granularity problem (unresolved)

This is the hardest open design question in the project and it is not primarily a
search-ranking problem, which is how it first appeared.

**Product decision:** comparison is out of scope. Family-level searches are
therefore navigation and clarification, not requests for representative values or
property envelopes. That removes the main reason to make a family look like a
data-bearing material.

Users arrive at three different levels of specificity, and all three are common:

| Level | Example query | What they want |
|---|---|---|
| **Family** | "aluminium vs magnesium" | A class-level comparison. No specific grade in mind. |
| **Grade** | "6061 vs 1020 steel" | The most common case. A named material, no interest in temper. |
| **Variant** | "6061-T4 vs T6 vs T651" | Full detail, deliberately comparing conditions. |

A flat list of records serves exactly one of these well. If records are variants,
a family query returns hundreds of rows and a grade query returns a dozen
near-identical ones. If records are grades, the variant detail has nowhere to
live. Five approaches, with tradeoffs.

**A. Prominence score.** A hand-set integer per record used to weight search
ranking. Common materials float, obscure variants sink.

- Cheap, no schema change, works immediately.
- Manual and permanent. Every new record needs a judgement call, and the scale
  needs re-tuning as the database grows.
- Does nothing for family-level queries. There is no "aluminium" record to rank.
- Arbitrary, and therefore hard for a contributor to apply consistently.

**B. Hierarchical records: family, grade, variant.** Three record levels with real
parent and child links. Search indexes all three. A bare `6061` query returns one
grade row that expands to its tempers. `aluminium` returns a family row.

- Matches how engineers actually think, and solves all three granularities with
  one mechanism instead of patching each separately.
- No manual scoring to maintain.
- Real schema work, and it is the choice that is expensive to reverse later.
- Forces a decision on what a family-level number even means. Recommended answer:
  family rows carry **ranges**, not point values, labelled as envelopes. This is
  the Ashby convention and it is honest. A single "typical aluminium" modulus is a
  fiction.
- Some records resist the hierarchy. A specific manufacturer's PEEK grade has no
  clean parent.

**C. Accept the duplicates, collapse them visually.** No data model change. The UI
groups results by grade and shows "6061-T6" plus "11 more variants".

- Purely presentational, cheapest possible fix, no maintenance.
- The grouping key has to be derived by parsing ids or names, which is fragile
  exactly where designations are irregular.
- Still no answer for family queries.
- Ranking *within* a group remains unsolved, so it tends to pull option A back in.

**D. Two separate tools.** A simple comparison tool over ~100 well-known materials,
and a separate deep database with everything.

- Each is optimised for its use case, and the simple one probably serves most
  traffic.
- **This already partially exists.** `materials-explorer` in the tools repo is the
  simple tool: 60 curated materials, comparison oriented. That is a genuine
  argument that D is the de facto architecture already and the new project should
  just be the deep half.
- Splits the source of truth, which the tools repo explicitly forbids as a core
  principle. Mitigable via the compatibility bridge in section 9, where the deep
  database generates the simple tool's data rather than duplicating it.
- The user has to know which tool to open, and the boundary between them will be
  relitigated forever.

**E. Infer granularity from the query.** The query already states its own
specificity: "aluminium" is a family query, "6061" is a grade query, "6061-T6" is a
variant query. Match the result level to the detected query level.

- Elegant, zero maintenance, and it uses information that is already present.
- Not standalone. It needs option B underneath to have anything to return at each
  level. It is a ranking layer, not a data model.
- Ambiguous and misspelled queries degrade unpredictably.

**F. Separate taxonomy, material identity, named state, and observation.**
Categories such as engineering plastics are taxonomy nodes. A material is
something a specification, datasheet, or test report can identify independently.
A stable formulation or deliberately named processing condition may be a state
of that material. Test temperature, direction, moisture, geometry, and basis
remain conditions on an observation.

- Categories may be empty, overlap, and have several broader relationships
  without creating empty pseudo-material records.
- A glass-filled polymer may belong to both a polymer chemistry and a
  fiber-reinforced-composite category.
- Standard grades, commercial grades, pure substances, species, composite
  systems, and foams do not have to pretend to share one identity hierarchy.
- Only materials or named states own observations. Categories never own values.
  A property view may derive an explicitly labelled observed range over category
  members, but that projection is not stored as a category observation.
- The boundary between a named state and an observation condition still requires
  source-driven testing. A useful rule: create a state only when users and sources
  deliberately name it as a stable lookup identity.

**Current leaning, to be confirmed at M1/M2.** F as the storage model, with typed
query intent deciding whether a phrase is a category constraint, material
identity, named state, precise property, or ambiguous property group. The
synthetic UI bake-off under `prototypes/` tests this hypothesis. D remains the
product architecture: the existing explorer handles comparison while this tool
handles deep lookup, both fed from one observation source.

The reason to favour F: the first prototype showed that B conflates classification
with identity and makes broad categories appear to be materials. That becomes
unnecessary once comparison is removed. Decide the exact F contracts at M1,
against the synthetic task corpus, before any real-source ingestion.

---

## 5. Data sources

### Stage 0 synthetic corpus

M0 through M2 use synthetic data only. The source inventory later in this section
is a future ingestion backlog, not a prerequisite for prototyping. Do not browse
for, verify, or expand real sources during those milestones.

Use two deterministic fixtures:

1. A hand-authored **semantic fixture** of roughly 25 to 40 records with enough
   observations to stress the product rather than imitate a real database.
2. A generated **scale fixture** of 10,000 obviously fake records. It may repeat
   templates and exists only to measure index size, load time, ranking latency,
   and rendering limits.

The semantic fixture should include:

- family, grade, and variant records, including awkward or missing parents;
- aliases, misspellings, short designations, ambiguous tokens, and duplicate-like
  names;
- scalar, range, and missing values across several dimensions and SI units;
- multiple observations of one property with different temperature, direction,
  product-form, and basis conditions;
- uncertainty, multi-category membership, an empty category, ties, outliers, and
  deliberately long source locators.

Use conspicuous names, banners, reserved `synthetic-*` material and source ids,
and a separate output path so no value can be mistaken for engineering guidance.
Check in the semantic fixture and generate the scale fixture from a fixed seed;
builds and demos must never depend on a network request. Keep both outside the
production source tree, and add a release check that rejects reserved synthetic
ids once factual data is enabled.

Real-data work starts with the narrow walking skeleton in M3. At that point,
cache source snapshots and extraction notes in `raw/` so rebuilding and UI work
do not repeat internet lookups.

The Python ecosystem covers chemicals and fluids very well and engineering solids
not at all. Plan around that asymmetry.

### Tier 1: free, machine-readable, cited, automatable

| Source | License | Covers | Approx count |
|---|---|---|---|
| `chemicals` (Caleb Bell) | MIT | Critical props, vapour pressure, Cp, viscosity, thermal conductivity, surface tension, density, CAS resolution | ~20,000 chemicals |
| `thermo` (same author) | MIT | Temperature-dependent properties built on `chemicals` | same |
| CoolProp | MIT | High-accuracy equations of state | ~120 fluids |
| USDA FPL Wood Handbook (FPL-GTR-190/282) | Public domain | MOE, MOR, compression parallel and perpendicular, shear, Janka, R/T/V shrinkage, specific gravity, at green and 12% moisture content | ~200 species |
| `periodictable`, `mendeleev` | Open | Element and isotope properties, neutron and X-ray cross sections | 118 elements |
| Materials Project | CC-BY-4.0 | DFT-computed crystal properties, elastic tensors, band gaps | ~150,000 crystals |
| NIST XCOM / ESTAR / ASTAR | Public domain | Radiation attenuation | elements + compounds |
| NASA outgassing database | Public domain | TML, CVCM | ~35,000 records |

**Decision: bulk chemicals are out of scope for v1.** Ingesting `chemicals` and
`thermo` reaches "20,000 materials" in an afternoon, but they are all chemical
compounds: acetone, benzene, ammonia. A mechanical engineer searching "4140
annealed" finds nothing, and 20,000 chemical records would outnumber the
engineering alloys roughly 30 to 1 and swamp every result list. The headline count
would look impressive while serving none of the target audience.

They stay listed here because the libraries are genuinely good and the option
should stay open. Revisit only after the engineering-materials side is solid, and
only behind an explicit scope filter rather than mixed into the default index.

A narrow exception worth considering earlier: roughly 30 common engineering fluids
(water, air, standard refrigerants, glycol mixes, hydraulic and lubricating oils)
via CoolProp. Those are things mechanical engineers actually look up, and 30
records cannot swamp anything.

### Tier 2: public domain, locked in PDFs, requires transcription

- **MIL-HDBK-5H.** US government work, public domain, superseded by the paid
  MMPDS but still valid for common alloys. A- and B-basis allowables for
  aerospace aluminium, steel, and titanium, broken out by product form,
  thickness, and grain direction, plus temperature knockdown curves. The only
  free source that natively has the conditioned record shape described above.
  Highest value and highest effort item in the plan.
- **CMH-17** (composites), older volumes public.
- **NIST cryogenic material property curve fits**, 4 K to 300 K.

### Tier 3: no structured source exists at any price

Tribology (friction, wear), corrosion resistance, weldability, machinability.
These exist as ordinal ratings in handbooks, not as numbers. Store them as
ratings with a source, or omit. Do not synthesise numbers.

### Tier 4: not lookup data

Price, availability, lead time, regulatory approvals. Per-supplier, per-lot, and
time-varying. Out of scope.

### What to do with the existing 10,606-record review corpus

The tools repo contains `data/materials/materials-review.json`, 10,606 materials
ingested from GitHub-hosted CSVs of unverified provenance (hobby databases and
ML-training sets, most likely derived from commercial data originally).

**Do not publish it.** Use it as a cross-check oracle: after curating a value,
assert it falls inside the community range, and flag when it does not. That
turns an unusable corpus into a useful regression test.

---

## 6. Ingestion pipeline

The previous attempt stalled. The structural fix is that normalised output is
never hand-edited. If a value is wrong, fix the extractor and re-run.

```
raw/           immutable downloaded artifacts, with SHA256 and retrieval date
extract/       one deterministic script per source, raw -> observations
normalized/    generated. canonical units, canonical property ids. never edited by hand
review/        diffs and cross-check failures awaiting a human decision
curated/       published. only what passed review
```

Rules:

- Network access is confined to explicit acquisition commands. Normal builds,
  tests, demos, extraction, and review run only from the immutable artifacts in
  `raw/`; they must never fetch opportunistically.
- Every extractor is re-runnable and produces identical output from identical
  input. No manual patching downstream.
- Every observation carries `source_id` and `source_locator` or it does not get
  written.
- Property ids come from a registry. An unknown property id is a hard error, not
  a warning. The previous run silently dropped 360 `fatigue_strength_10e7`
  records this way.
- Cross-check every curated value against the review corpus and against any
  overlapping source. Disagreement beyond the stated uncertainty is a review item.

---

## 7. Search index

Generated at build time, shipped as static JSON.

### Sizing

Measured from the tools repo: the current curated file is 87 KB for 60 materials
at 29 properties, about 1.45 KB each. A conditioned observation record will run
6 to 10 KB. So 10,000 rich materials is roughly 80 MB, which obviously cannot be
shipped to a browser.

**Split the index from the payload.** Search never needs the full record.

| Layer | Contents | Size at 10,000 materials |
|---|---|---|
| Search index | typed category, material, state, property, and property-group identities | ~250 B per material/state, 2.5 MB raw, roughly 400 KB compressed |
| Full records | all observations | fetched on navigation only |

400 KB compressed, loaded once and cached behind a content hash, is fine. Netlify
compresses automatically. This stays a static site with no compute and no hosting
cost through at least 50,000 materials.

### Structure

Pack as parallel arrays rather than arrays of objects. Repeating JSON keys 10,000
times is roughly a 40% size penalty for nothing.

```json
{
  "categories": [{"id": "engineering-plastics", "aliases": ["technical plastics"]}],
  "materials": [{"id": "al-6061", "aliases": ["6061"], "category_ids": ["aluminium-alloys"]}],
  "states": [{"id": "al-6061-t6", "material_id": "al-6061", "aliases": ["6061 T6"]}],
  "properties": [{"id": "tensile_yield_strength", "aliases": ["yield strength"]}],
  "property_groups": [{"id": "strength", "members": ["tensile_yield_strength", "ultimate_tensile_strength"]}]
}
```

Keep the namespaces separate. Match typed aliases longest-phrase-first, remove
recognized category/property phrases, and rank only the remaining material/state
identity terms. Do not index descriptions or numeric values. Exact maps and
prefix postings can be added once the 10,000-record scale fixture proves they are
needed.

### Performance reality

At 10,000 short documents this is not a hard problem. A prebuilt inverted index
resolves in well under a millisecond, and even naive substring scanning over a
flat array is a few milliseconds. Client-side search only becomes genuinely hard
north of roughly 500,000 documents. Do not reach for a search library before
measuring; Fuse.js in particular is the slowest reasonable option and the largest
bundle.

### Ranking

Ranking quality matters far more than speed. Order:

1. Exact material/state id or designation
2. Exact canonical name
3. Exact typed alias
4. Name/designation prefix
5. Every remaining identity token matched
6. Fuzzy match, only when exact and prefix recall are empty

Category and property intent filter or focus a lookup; they never cause values
from different materials to be ranked together.

---

## 8. Frontend

The production frontend begins only after M0 selects an interaction direction and
M1 freezes the first data contract. The files under `prototypes/` are throwaway
evidence and are not dependencies of `src/`.

- One self-contained HTML page plus static JSON. Vanilla JS. No framework, no
  bundler, consistent with the tools repo.
- Start fetching the index on page load, render the search box immediately, and
  queue keystrokes entered before the index arrives. Never show a dead input.
- Cap rendered rows at ~50. Virtualise only if that proves insufficient.
- Record pages are pre-rendered static HTML for search engine indexing, not
  client-rendered from JSON.
- Follow the tools repo's `DESIGN.md`, settings panel pattern (theme, density,
  precision), and dark mode CSS variable conventions, so the merge does not
  require a visual rewrite.

---

## 9. Compatibility bridge back to the tools repo

The tools repo's `materials-explorer` and `pycalcs/material_db.py` read a flat
schema where each property is a single scalar or `{value, min, max}`.

Add a build target that collapses the observation database into exactly that flat
shape by selecting one representative observation per property per material
(prefer `basis: typical` at 293 K, longitudinal, most common product form). Emit
it as `materials.json` in the existing format.

Prove the collapse contract with expected synthetic output in M1, then repeat the
test against the conditioned real observations in M3. M6 should integrate an
already-tested export, not discover its selection rules for the first time.

This means the new database becomes the upstream source of truth, and the tools
repo's current file becomes a generated artifact. `materials-explorer`,
`material_indices.py`, and every calculator with a material dropdown keep working
with no changes. That is what makes the eventual merge low-risk.

---

## 10. Licensing and legal

- **Code:** MIT.
- **Data:** CC-BY-4.0. This is required anyway if Materials Project data is
  included, and it is the honest choice given the project's premise.
- Raw property values are facts and are not copyrightable in the US (*Feist v.
  Rural*). The compilation, and any site's terms of service, are separate matters.
- **Do not scrape MatWeb, Total Materia, Matmatch, or MakeItFrom.** Terms of
  service bind regardless of the copyright status of the underlying numbers, and
  the EU database right adds a second problem.
- Manufacturer datasheets are published for use. Citing a specific value to a
  specific datasheet revision is fine and is what the `source_locator` field is
  for.
- Attribute every CC-BY source in a visible credits page, not just in JSON.

---

## 11. Milestones

The order is deliberately experience, contract, implementation, evidence, then
coverage. A milestone does not begin merely because the previous demo exists; its
exit gate must be recorded.

**M0. Synthetic experience spike.** Create the semantic fixture and the five
disposable UI directions in section 3. No source lookups and no production
pipeline. Run the common task script with several people or structured
walkthroughs, score the results, and write a short decision note. Exit when one
interaction direction has been selected and the remaining unknowns are named.

**M1. Synthetic contract spike.** Expand the semantic fixture only where needed
to stress section 4.4, and add the generated scale fixture. Decide
the taxonomy/material/state/observation boundary, observation conditions, stable
observation ids, multi-category membership, and the boundary between record and
search-index data. Prove the compatibility collapse in section 9 with expected
synthetic output. Add executable examples for exact, alias, short-token, typo,
ambiguous-property, category-only, and comparison-intent queries. Exit when the
chosen schema and index can express every M0 task without UI-specific exceptions.
As minimum search gates, exact ids and explicit aliases rank first in every golden
query, typo targets rank in the top five, no query renders more than 50 rows, and
the 10,000-record scale fixture stays within an agreed index-size and
query-to-render-latency budget on a mid-range laptop. Record the measured budgets
instead of guessing them from implementation complexity. Still no real data or
source research.

**M2. Demo the selected product, still synthetically.** Reimplement the selected
direction cleanly against the semantic fixture, and run performance checks
against the scale fixture. Include the real navigation shape, alias handling,
record view, typed query clarification, queued index loading, keyboard path,
narrow-screen layout, and basic performance/relevance tests. Do not add property
rankings or compare controls. This is the first polished, demo-able prototype.
Exit when the product interaction can be judged independently of data coverage
and synthetic data is visibly watermarked.

**M3. Prove real provenance with a walking skeleton.** Activate separate factual
outputs and the synthetic-id rejection gate before starting targeted source work.
Ingest small slices from two independent sources with different shapes—for
example one machine-readable table and one public-domain PDF—rather than
completing either corpus. About 20 to 50 records are enough. Exercise
download/capture, raw snapshots, extraction, normalization, validation, human
verification of source locators, review resolution, curated promotion, the
compatibility export, and a full rebuild without network access. Also qualify the
exact source, license, and locator strategy for each M4 corpus. If real evidence
breaks the schema, return to M1 explicitly, rerun M2, then rerun both M3 source
slices; do not patch around it. Exit only when both paths reproduce offline with
no unresolved review items.

**M4. Pipeline plus a complete free dataset.** Harden `raw` through `curated`,
then ingest the USDA Wood Handbook. Add the 118 elements only if their exact
source, license, per-value locator, and property scope passed the M3 qualification
gate. That yields roughly 200 records from wood or about 320 with elements, fully
cited and complete for the declared property scope. Wood is a strong first
complete ingestion: public domain, tabular, and it covers an entire property
category with no gaps.

**M5. Engineering alloys and polymers.** Do the high-value hand work only after
the pipeline and evidence model survive M3/M4. Use MIL-HDBK-5H for aerospace
metals and manufacturer datasheets for engineering plastics. Target the few
hundred materials people actually specify: common aluminium grades and tempers,
carbon and alloy steels, stainless, titanium, brass, magnesium, and the standard
engineering plastics. Small count, high effort, and the main reason anyone would
use the site.

**M6. Merge.** Compatibility bridge, URL move, `DESIGN.md` conformance, sitemap
and meta integration. Verify that synthetic artifacts remain absent from factual
and production outputs; the rejection check has already been enforced since M3.

**Deferred, explicitly not v1.** Bulk chemicals (`chemicals`, `thermo`), Materials
Project crystals, NASA outgassing, radiation attenuation. All are cheap to add and
all risk drowning the engineering materials. Revisit behind a scope filter once M5
is solid. The narrow CoolProp fluid set from section 5 is the one candidate that
could reasonably land earlier.

---

## 12. How this fails

Worth stating plainly so it can be watched for.

- **Going broad first.** Publishing the 10,606-record corpus yields wide coverage
  of untrustworthy numbers that users cannot verify and cannot tell apart from
  the good ones. That spends credibility on nothing.
- **Researching before the product questions are closed.** Accurate source work
  does not answer whether hierarchy, ranking, or conditioned values are usable,
  and may have to be normalized again after those decisions change.
- **Polishing the first UI idea.** A visually complete first direction makes it
  psychologically and economically harder to compare genuinely different
  interactions.
- **Letting synthetic data look authoritative.** A prototype value copied into a
  production build is worse than a missing value. Namespace, watermark, isolate,
  and reject it at release time.
- **Building a reusable prototype framework.** Shared abstractions make the spike
  slower and the losing ideas harder to discard.
- **Chasing the count.** Ingesting `chemicals` makes the headline number look
  great while serving none of the target audience. Ruled out for v1 in section 5,
  and the temptation will return every time the record count looks small.
- **Schema drift.** Adding condition keys ad hoc until nothing is filterable.
- **Getting the granularity model wrong.** Section 4.4. The only listed failure
  mode that cannot be fixed without re-ingesting everything.
- **Hand-editing generated files.** The one habit that guarantees the pipeline
  becomes unmaintainable.
- **Treating it as finishable.** A calculator is done when it is correct. A
  database is a standing commitment. If that commitment is not wanted, the right
  scope is 500 materials curated once, not 10,000 maintained forever.

---

## 13. Open questions

1. Does the search index need any property values? The lookup-only interaction
   suggests no: typed property ids and per-record availability counts may be
   enough, while observations load only after material selection. Confirm at M1.
2. **Which exact contracts implement option F?** Decide the
   taxonomy/material/state boundary at M1 with the synthetic stress corpus, before
   ingestion.
3. How are near-duplicate conditions collapsed in the record view? AA7075-T6 with
   six yield values needs a default display plus a way to see all six without
   overwhelming the page. Related to 4.4 but distinct: this is within one variant.
4. Which source-defined conditions deserve a stable named state, and which remain
   observation conditions? Heat treatment and formulation are common states;
   temperature, direction, specimen geometry, and moisture usually are not.
5. What is the record id scheme for materials with no standard designation, such
   as a specific manufacturer's PEEK grade? This is also the case that fits the
   hierarchy worst.
6. Is there a v1 answer for ratings-only properties (weldability, machinability),
   or are they deferred entirely?

---

## 14. If starting again

The first prototype demonstrated that the product can be built, but it combined
too many kinds of learning in one pass. Real 6061/7075 citations, hierarchy
rules, derived envelopes, search ranking, build validation, and visual polish
were all advanced together. That found useful problems, but source work and
hardening were already underway before the interaction had earned that
investment.

I would change the process in five ways:

1. **Separate learning tracks.** First learn what users need to see, then what
   contracts support it, then whether real evidence fits those contracts. A
   polished product and a broad corpus are delivery work, not discovery work.
2. **Make ranking examples executable immediately.** Short designations, aliases,
   stopwords, misspellings, hierarchy terms, and ambiguous queries should be a
   fixed relevance suite before CSS polish. They exposed more product risk than
   index speed did.
3. **Use real sources as an audit, not as seed content.** The first two source
   slices should be selected because they are structurally different and likely
   to break assumptions. Coverage comes only after that audit passes.
4. **Budget by decisions and passes.** Every spike should name the question, the
   artifacts, the total token/time cap, and the exit decision. When the budget is
   spent, reduce the question or choose; do not turn uncertainty into more polish.
5. **Keep what was learned, not necessarily what was coded.** Preserve task
   scripts, screenshots, relevance fixtures, contract tests, and decision notes.
   Treat prototype implementation as replaceable.

The resulting critical path is:

```text
synthetic fixture -> disposable UI trials -> schema/search contract
  -> selected synthetic demo -> two-source provenance audit -> coverage -> merge
```
