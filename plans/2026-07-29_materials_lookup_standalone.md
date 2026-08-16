# Materials Lookup: Standalone Project Seed Plan

Date: 2026-07-29

Seed plan for a materials property lookup database, developed in a separate
repository and merged into `transparent.tools` later. This document is the
starting context for that new repo. It assumes no knowledge of the tools repo
beyond what is written here.

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

### The core interaction

One search box, focused on page load. Results update as you type. The result list
is heterogeneous and each row is visibly typed:

| Query | Row type surfaced | Action on select |
|---|---|---|
| `6061` | Material | Go to that material's record |
| `yield strength` | Property | Go to the sorted list for that property |
| `stiffness` | Property (via alias to Young's modulus) | Same |
| `mild steel` | Material (via alias to 1018) | Record |
| `aluminium` | Family | Filtered list |

Results are capped at roughly 50 rendered rows. Never render 10,000 nodes.

### Sorted property pages

`/materials/by/thermal-conductivity` lists every material that has a value for
that property, ranked. These are generated as static pages at build time, not
computed live, because they are the main organic search surface ("materials with
highest thermal conductivity" is a real query people type).

### The alias thesaurus

The single highest-leverage cheap component. A hand-written map from what people
type to what the database calls things. Target 300 to 500 entries before launch.

```
stiffness, MOE, E, elastic modulus     -> youngs_modulus
springiness                             -> youngs_modulus
how hot can it get, service temp        -> max_service_temp
durometer, shore                        -> hardness_shore
mild steel                              -> steel-1018
aircraft aluminium                      -> al-2024-t3, al-7075-t6
delrin, acetal                          -> pom
```

Aliases apply to materials, properties, and families. This is the difference
between search that works and search where you already have to know the answer.

### Comparison

Deferred. A "compare" link from a record is fine to stub, but v1 is lookup only.

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
    "thickness_mm": [1.6, 6.3],
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

All values stored in SI base units. Conversion happens in the frontend for
display. This matches the tools repo convention and `UNITS_DISCUSSION.md` there.

### 4.4 The granularity problem (unresolved)

This is the hardest open design question in the project and it is not primarily a
search-ranking problem, which is how it first appeared.

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

**Current leaning, to be confirmed at M0/M1.** B as the data model, E as the
ranking layer on top of it, C in the UI for genuine near-duplicates inside one
grade, and A demoted to a small manual override list for the handful of cases the
others get wrong. D is not chosen outright, but note that the compatibility bridge
means the simple tool keeps existing regardless, fed from the same source.

The reason to favour B despite the cost: it is the only option that is hard to
retrofit. A, C, and E can all be added or removed later without touching stored
data. Getting the hierarchy wrong means re-ingesting everything. Decide this at
M0, on paper, before any ingestion.

---

## 5. Data sources

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
| Search index | id, name, aliases, family, prominence, a few headline numbers | ~250 B each, 2.5 MB raw, roughly 400 KB compressed |
| Full records | all observations | fetched on navigation only |

400 KB compressed, loaded once and cached behind a content hash, is fine. Netlify
compresses automatically. This stays a static site with no compute and no hosting
cost through at least 50,000 materials.

### Structure

Pack as parallel arrays rather than arrays of objects. Repeating JSON keys 10,000
times is roughly a 40% size penalty for nothing.

```json
{
  "fields": ["id", "name", "family", "prominence", "density", "youngs_modulus"],
  "rows": [["al-6061-t6", "Aluminium 6061-T6", 12, 3, 2700, 68.9e9], ...],
  "tokens": { "6061": [12, 458], "alumin": [12, 13, 14] },
  "properties": [...],
  "thesaurus": {...}
}
```

Token postings map tokens to row indices. Ship the token list sorted so the
client can binary-search for prefix matches, which gives instant as-you-type
behaviour without shipping a trie.

### Performance reality

At 10,000 short documents this is not a hard problem. A prebuilt inverted index
resolves in well under a millisecond, and even naive substring scanning over a
flat array is a few milliseconds. Client-side search only becomes genuinely hard
north of roughly 500,000 documents. Do not reach for a search library before
measuring; Fuse.js in particular is the slowest reasonable option and the largest
bundle.

### Ranking

Ranking quality matters far more than speed. Order:

1. Exact match on id or alias
2. Prefix match on name, weighted by `prominence`
3. Token match, weighted by `prominence`
4. Fuzzy match, only when the above return few results

---

## 8. Frontend

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

**M0. Prove the schema, and decide the granularity model.** Settle section 4.4 on
paper first, since it is the one choice that is expensive to reverse. Then
hand-write records that stress it: AA7075-T6 with all six tensile yield values
across product form, thickness, and grain direction (variant level), 6061 with
several tempers (grade level), and an "aluminium alloys" envelope (family level).
If the schema cannot express all three cleanly, fix it before writing any code. No
pipeline, no UI.

**M1. Prove the search.** ~500 records (any source, quality not yet the point) and
the full search UI including the alias thesaurus. This is the milestone where the
product either feels good or does not. Everything downstream is data entry, so
find out early.

**M2. Pipeline plus a complete free dataset.** Build `raw` through `curated`, then
ingest the USDA Wood Handbook and the elements. Roughly 320 records, fully cited,
complete for their domains. Wood is the best first ingestion: public domain,
tabular, and it covers an entire property category with no gaps.

**M3. Engineering alloys and polymers.** The hand work, promoted ahead of any bulk
ingestion. MIL-HDBK-5H transcription for aerospace metals, manufacturer datasheets
for engineering plastics. Target the few hundred materials people actually
specify: common aluminium grades and tempers, carbon and alloy steels, stainless,
titanium, brass, magnesium, and the standard engineering plastics. Small count,
high effort, and the entire reason anyone would use the site.

**M4. Merge.** Compatibility bridge, URL move, `DESIGN.md` conformance, sitemap and
meta integration.

**Deferred, explicitly not v1.** Bulk chemicals (`chemicals`, `thermo`), Materials
Project crystals, NASA outgassing, radiation attenuation. All are cheap to add and
all risk drowning the engineering materials. Revisit behind a scope filter once M3
is solid. The narrow CoolProp fluid set from section 5 is the one candidate that
could reasonably land earlier.

---

## 12. How this fails

Worth stating plainly so it can be watched for.

- **Going broad first.** Publishing the 10,606-record corpus yields wide coverage
  of untrustworthy numbers that users cannot verify and cannot tell apart from
  the good ones. That spends credibility on nothing.
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

1. Does the search index need every property value for every material, or only
   headline numbers? Sorted property pages being static resolves this in favour of
   headline numbers only, but confirm before locking the index format.
2. **Which granularity model?** Section 4.4. Decide at M0, before ingestion.
3. How are near-duplicate conditions collapsed in the record view? AA7075-T6 with
   six yield values needs a default display plus a way to see all six without
   overwhelming the page. Related to 4.4 but distinct: this is within one variant.
4. If family-level records exist, are they stored or generated? Generating
   envelopes from child grades keeps one source of truth but means a family's range
   silently shifts every time a grade is added.
5. What is the record id scheme for materials with no standard designation, such
   as a specific manufacturer's PEEK grade? This is also the case that fits the
   hierarchy worst.
6. Is there a v1 answer for ratings-only properties (weldability, machinability),
   or are they deferred entirely?
