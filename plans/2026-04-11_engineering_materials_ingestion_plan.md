# Engineering Materials Data Ingestion Plan

Date: 2026-04-11
Status: Proposed execution plan before implementation
Related existing assets:
- `plans/2026-04-07_materials_selection_suite.md`
- `data/materials/schema.json`
- `data/materials/materials.json`
- `pycalcs/material_db.py`
- `pycalcs/material_indices.py`
- `tools/materials-explorer/index.html`
- `shared/ashby-plot.js`
- `tests/test_material_db.py`
- `tests/test_material_indices.py`

## 1. Purpose

Define how this repo should ingest large amounts of engineering-grade materials information without turning into a legally risky scraper farm or a low-trust pile of flattened datasheet values.

The plan covers:

1. which source classes are worth ingesting,
2. which source classes must not be scraped or redistributed in bulk,
3. the architecture for discovery, fetch, parsing, normalization, review, and publish,
4. how ingested evidence becomes curated material records for the tools,
5. the milestone sequence for shipping this safely.

This plan is intentionally narrower than the full materials-suite plan. It addresses the data acquisition and curation backbone that the suite depends on.

## 2. Executive Recommendation

Do not build "a scraper for materials websites."

Build a rights-aware ingestion pipeline with four source lanes:

- `Lane A: direct-ingest sources`
  - Explicit API, CSV/XLS export, open data dump, or written permission.
  - Fully automatable.
- `Lane B: public vendor datasheet sources`
  - Public product pages and technical datasheets where basic crawling is permitted.
  - Automate discovery and extraction conservatively.
  - Store extracted facts plus provenance, not mirrored copies of proprietary databases.
- `Lane C: restricted reference sources`
  - Useful for analyst cross-checking, taxonomy, and conflict resolution.
  - No bulk scraping or republishing.
- `Lane D: licensed sources`
  - Integrate only if the project later obtains a license or explicit written permission.

The practical strategy should be:

1. ingest public vendor datasheets and structured public product pages first,
2. keep restricted engineering databases as manual reference sources only,
3. require human review before any datum reaches the curated database,
4. treat provenance, conditions, units, and basis as first-class data.

## 3. What Problem This Plan Solves

The project needs engineering-useful data for:

- metals and alloys,
- commodity and engineering polymers,
- thermosets and elastomers,
- composites and laminates,
- foams,
- fabrics and fiber products,
- ceramics and glasses,
- natural materials,
- selected soft materials such as gels and elastomeric systems.

The project does not need a general atomistic or molecules database as its primary backbone. Research databases such as Materials Project, JARVIS, OQMD, and NOMAD are useful for future advanced workflows, but they are not the right primary source class for screening real engineering materials by grade, form, temper, processability, and datasheet properties.

The central challenge is not just "getting numbers." It is preserving enough engineering context that the tools can answer questions honestly:

- Is this a generic family value or a specific grade?
- Is the number typical, minimum, design allowable, or estimated?
- Was the polymer dry-as-molded or conditioned?
- Is the composite datum lamina-directional or laminate quasi-isotropic?
- Did the number come from a vendor TDS, a handbook, a standard, or a manually curated estimate?

## 4. Source Strategy

### 4.1 Source lanes

| Lane | Meaning | Allowed automation | Publish eligibility |
|---|---|---|---|
| A | API / export / open dump / explicit permission | Full | Yes |
| B | Public vendor pages and datasheets | Controlled crawl and parse | Yes, after review |
| C | Restricted public reference source | Manual consultation only | No direct republish |
| D | Paid or licensed source | Only per license | Per license |

### 4.2 Initial source posture

This table is the default policy unless later superseded by written permission or a formal license review.

| Source class | Example posture | Default lane | Notes |
|---|---|---|---|
| Public vendor TDS/PDS PDFs | Usually best first target | B | Highest engineering relevance; conditions often stated |
| Public vendor selector tables | Strong target | B | Often easier to parse than PDFs |
| Public CSV/XLS downloads from suppliers | Excellent target | A or B | Treat as A only if export/reuse posture is clear |
| Open government or academic engineering datasets | Good supplement | A | Must verify license and coverage |
| MatWeb | Reference only | C | Useful cross-check; do not plan bulk scrape/republication |
| MakeItFrom | Reference only | C | Useful for taxonomy/comparison; not a bulk-ingest target |
| PoLyInfo | Reference only | C | Useful polymer reference; do not scrape |
| CAMPUS | Licensed only | D | Engineering-grade but proprietary |
| ASM / MMPDS / standards handbooks | Licensed/reference only | D | High-value, not open |

### 4.3 What to ingest first

The first wave should prioritize sources with these properties:

1. public access,
2. stable URLs,
3. engineering-grade product data,
4. named test conditions,
5. enough structure for semi-automated extraction,
6. families aligned with the project's first tools.

That means:

- polymer vendor datasheets,
- common metal alloy product/spec sheets,
- engineering plastics selector tables,
- engineering ceramics supplier datasheets,
- insulation/foam vendor datasheets,
- fiber/fabric product data sheets.

### 4.4 What not to do

Do not:

- build a generic site scraper that ignores terms, robots posture, or licensing,
- mirror other companies' materials databases into this repo,
- flatten restricted sources into unattributed scalar values,
- assume "publicly visible" means "allowed to ingest and republish at scale,"
- start with difficult PDF families before the review loop exists.

## 5. Non-Negotiable Principles

1. No source enters automation until its access posture is classified.
2. No datum is publishable without provenance.
3. No datum is publishable without units.
4. No ranking should rely on `estimate` by default.
5. No curated record should be overwritten automatically by later scrapes.
6. Raw evidence must remain recoverable after normalization.
7. The pipeline must support multiple candidate datums for the same property before curation decides what is canonical.
8. The ingestion system can use heavier Python dependencies; the publish/query layer used by Pyodide must remain lightweight.

## 6. Architecture Overview

### 6.1 Separate the system into three layers

1. `Raw ingestion layer`
   - Discovery results, fetched HTML/PDF/XLS artifacts, parser outputs.
   - Many records may be noisy, duplicated, or partial.
2. `Staging and review layer`
   - Normalized extracted datums with provenance and review status.
   - Supports multiple conflicting values for the same property.
3. `Curated publish layer`
   - The materials database actually used by the Explorer and pycalcs query layer.
   - Stable, reviewed, intentionally narrower.

### 6.2 Why this separation is mandatory

The current publish-facing schema in `data/materials/schema.json` is suited to a curated database, not to raw harvesting. It allows one property slot per material record, but ingestion needs to handle:

- multiple candidate values,
- multiple source artifacts,
- parser confidence,
- extraction errors,
- unresolved identity collisions,
- family-specific condition metadata.

Therefore:

- raw and staging data must use richer schemas than the final publish database,
- the curated publish database remains optimized for product use,
- no parser should write directly into `data/materials/materials.json`.

## 7. Proposed Repository Structure

```text
scripts/materials_ingest/
  README.md
  source_registry.yaml
  aliases/
    properties.yaml
    units.yaml
    materials.yaml
  adapters/
    base.py
    html_table.py
    pdf_datasheet.py
    csv_xlsx.py
    manual_import.py
  discovery/
    seed_lists.py
    vendor_catalog.py
  normalize/
    properties.py
    units.py
    identity.py
    conditions.py
  review/
    queue.py
    export.py
  cli.py

data/materials/
  raw/
    artifacts/
    manifests/
  staging/
    extracted_datums.jsonl
    material_candidates.jsonl
    review_queue.jsonl
  curated/
    materials.json
    schema.json
    sources.json
```

Notes:

- `data/materials/materials.json` and `data/materials/schema.json` may remain the active publish path initially if the current Explorer code expects that location.
- If the repo later adopts `data/materials/curated/` as canonical, add a clear migration and generation step. Do not leave source-of-truth ambiguous.

## 8. Data Models

### 8.1 Source registry record

Every onboarded source should have a registry entry with fields like:

- `source_id`
- `name`
- `organization`
- `source_type`
  - `vendor_pdf`
  - `vendor_html`
  - `csv_export`
  - `xlsx_export`
  - `api`
  - `reference_only`
  - `licensed`
- `lane`
  - `A`, `B`, `C`, or `D`
- `base_url`
- `robots_checked_at`
- `terms_checked_at`
- `automation_allowed`
- `redistribution_allowed`
- `requires_login`
- `rate_limit_policy`
- `family_focus`
- `priority`
- `review_notes`

This registry is the control plane. If `automation_allowed` is not explicitly true, bulk automation must not run for that source.

### 8.2 Raw artifact record

Every fetched artifact should store:

- `artifact_id`
- `source_id`
- `artifact_type`
  - `html`, `pdf`, `csv`, `xlsx`, `json`
- `original_url`
- `retrieved_at`
- `http_status`
- `content_hash`
- `local_path`
- `content_type`
- `discovery_context`
- `parent_artifact_id`

This provides a chain from a curated datum back to the exact file that was parsed.

### 8.3 Extracted datum record

The staging layer should use a richer datum structure than the publish schema. Each extracted datum should support:

- `candidate_material_key`
- `property_id`
- `value`
- `min`
- `max`
- `raw_text`
- `raw_units`
- `normalized_units`
- `basis`
- `test_standard`
- `temperature`
- `humidity`
- `moisture_state`
- `orientation`
- `processing_state`
- `thickness_or_form`
- `parser_confidence`
- `source_id`
- `artifact_id`
- `page_or_section`
- `review_status`
- `review_notes`

### 8.4 Candidate material record

Before canonical IDs are assigned, staging should support `candidate_material` records with:

- `candidate_material_key`
- `source_id`
- `manufacturer`
- `trade_name`
- `grade_or_designation`
- `generic_family_guess`
- `record_kind_guess`
- `form_guess`
- `raw_title`
- `raw_description`
- `related_artifact_ids`

### 8.5 Curated publish record

The curated publish layer can remain simpler, but only after review collapses the evidence:

- one canonical material ID,
- one preferred published datum per property,
- optional range,
- explicit basis,
- explicit source link,
- condition notes,
- links to supporting evidence.

If the current schema cannot carry enough metadata for honest publication, extend it before scaling ingestion volume.

## 9. Property and Identity Normalization

### 9.1 Property alias registry

Create and maintain a registry that maps raw labels to canonical property IDs. Examples:

- `Young's Modulus`
- `Elastic Modulus`
- `Modulus of Elasticity`
- `Tensile Modulus`

These should not all blindly collapse to one field. The alias registry must be able to express:

- direct mapping,
- family-specific mapping,
- ambiguous mapping requiring review,
- rejected mapping.

Examples:

- polymer `tensile modulus` may map to `youngs_modulus` if the basis is clearly tensile modulus under standard conditions,
- `flexural modulus` must not silently become `youngs_modulus`,
- `service temperature` must not silently become `max_service_temp` without scope review.

### 9.2 Unit normalization

All published numeric values should land in base SI units. Raw units must still be preserved in staging.

Normalization must support:

- MPa, GPa, psi, ksi,
- g/cm^3 and kg/m^3,
- W/m-K and BTU-based thermal units if encountered,
- ppm/K and um/m-K for CTE,
- Shore scales as non-convertible categorical numeric scales,
- mixed vendor notation such as `%`, `% wt`, `% vol`.

### 9.3 Identity normalization

Canonical IDs must distinguish:

- generic materials,
- standard alloys,
- tempers,
- filled polymer grades,
- reinforced laminas,
- laminates,
- fabrics,
- foams,
- product-specific commercial grades.

The identity resolver should not collapse:

- `6061 aluminum` and `6061-T6`,
- `PA66` and `PA66 GF30`,
- `carbon/epoxy UD lamina` and `quasi-isotropic laminate`,
- `closed-cell PVC foam` and `PET foam`.

### 9.4 Family-specific required metadata

The normalization pipeline must enforce family-specific fields before publish:

- `metals`
  - alloy designation, temper or condition, product form where known
- `polymers`
  - filler state, moisture condition where known, flame grade if relevant
- `composites`
  - record kind, fiber type, matrix type, orientation, layup or laminate type
- `foams`
  - relative or absolute density, open/closed cell, base polymer
- `fabrics`
  - areal density, weave type, warp/fill if available, finish or coating
- `ceramics`
  - composition class, purity or grade where known

## 10. Parser Strategy

### 10.1 HTML table adapter

Use for:

- selector pages,
- structured product comparison tables,
- manufacturer material portals with stable table markup.

Responsibilities:

- extract row and header structure,
- infer candidate material records,
- map labeled values into extracted datums,
- capture section headings and footnotes.

### 10.2 PDF datasheet adapter

Use for:

- technical data sheets,
- product data sheets,
- grade comparison brochures.

Responsibilities:

- text extraction,
- table extraction,
- page-level evidence linking,
- confidence scoring for each parsed cell.

The PDF adapter should support multiple extraction backends because datasheets vary wildly in quality.

### 10.3 CSV/XLSX adapter

Use for:

- supplier exports,
- public downloadable product tables,
- internal manually structured curation sheets.

This is likely the highest-value and lowest-risk ingestion path whenever available.

### 10.4 Manual import adapter

Required from day one.

Not every important source is automatable. The project needs a structured manual-entry path that produces the same staging objects as automated parsers. This lets a curator:

- enter a datum from a reference-only source,
- mark the source as non-redistributable,
- store only the allowed metadata and citation,
- keep a review trail without pretending the value was machine-ingested.

## 11. Review Workflow

### 11.1 Review states

Every extracted datum and candidate material should move through explicit states:

- `new`
- `parsed`
- `needs_review`
- `accepted`
- `accepted_with_edits`
- `rejected`
- `superseded`

### 11.2 Reviewer responsibilities

The reviewer must verify:

- property mapping is correct,
- units were converted correctly,
- material identity is correct,
- the datum belongs to the right family and record kind,
- the basis and condition were captured honestly,
- the source is publish-eligible,
- the number is not obviously corrupted by OCR or table misread.

### 11.3 Review tooling

The minimum viable review system can be CLI-first. It does not need a polished browser UI on day one.

Required capabilities:

- list pending candidates,
- show extracted values grouped by candidate material,
- show raw evidence excerpt and artifact pointer,
- accept/reject/edit mappings,
- assign canonical material IDs,
- emit a curated export patch.

## 12. Publish Rules

### 12.1 Publish eligibility

A datum may enter the curated database only if:

1. the source lane permits publication,
2. the datum has provenance,
3. units are normalized,
4. identity is resolved,
5. a reviewer accepted it,
6. basis and condition are set or explicitly marked unknown,
7. there is no unresolved conflict with a stronger existing datum.

### 12.2 Conflict resolution

When multiple candidate values exist for the same property:

- preserve all evidence in staging,
- choose one published value intentionally,
- record why it won,
- prefer stronger basis and clearer conditions over convenience,
- do not average incompatible sources just to force a single number.

### 12.3 Conservative publication policy

The publish layer should prefer:

- reviewable typical values for broad Explorer browsing,
- ranges when the source genuinely supports them,
- notes warning about condition dependence,
- explicit suppression of weak estimates from rankings by default.

## 13. Integration with the Existing Materials Database

### 13.1 Immediate compatibility strategy

The current `data/materials/schema.json` and `pycalcs/material_db.py` already provide a publish/query path. Do not throw that away.

Instead:

1. keep the current curated database as the serving format for the Explorer,
2. add a separate staging model for ingestion,
3. generate the curated database from reviewed staging data,
4. extend the curated schema only where necessary for honesty.

### 13.2 Schema changes likely needed soon

The publish schema should likely gain:

- source-rights metadata or source-class metadata,
- stronger condition structure than a single free-text string,
- better support for links to evidence,
- room for family/form metadata where that affects selection logic.

### 13.3 Query-layer constraints

`pycalcs/material_db.py` should continue to stay standard-library-only for Pyodide use.

All ingestion code with heavier dependencies should live under `scripts/materials_ingest/` and produce static artifacts consumed by the lightweight runtime.

## 14. First Source Shortlist

The first execution wave should be deliberately narrow.

### 14.1 Phase 1 families

- common metals and alloys,
- commodity and engineering polymers.

### 14.2 Phase 1 source classes

- public vendor datasheet PDFs,
- public structured vendor selector tables,
- any public CSV/XLS product exports with clear reuse posture.

### 14.3 Why this scope is correct

These families:

- directly support the Materials Explorer and Ashby workflows,
- cover the most common engineering screening tasks,
- have relatively abundant public datasheet coverage,
- avoid the worst parsing complexity of composites and fabrics,
- force the system to solve both metals-style and polymers-style condition issues early.

### 14.4 Families to defer until the review loop is stable

- laminates and prepregs,
- fabrics and textile products,
- foams with sparse or inconsistent test methods,
- gels and highly condition-sensitive soft materials.

## 15. Milestones

### Milestone 0: Governance and source policy

Deliverables:

- `scripts/materials_ingest/README.md`
- `source_registry.yaml`
- source lane definitions
- onboarding checklist for new sources

Exit criteria:

- at least 10 candidate sources classified,
- no automation allowed without registry entry,
- manual review policy written down.

### Milestone 1: Pipeline skeleton

Deliverables:

- CLI entry point,
- raw artifact manifest format,
- staging datum format,
- hashing and fetch cache,
- parser adapter interface.

Exit criteria:

- one source can be discovered, fetched, parsed, and written into staging,
- no direct writes to curated materials database.

### Milestone 2: Three ingestion adapters

Deliverables:

- HTML table adapter,
- PDF datasheet adapter,
- CSV/XLSX adapter.

Exit criteria:

- each adapter produces staging records with provenance,
- parser confidence is stored,
- failed parses are logged without corrupting outputs.

### Milestone 3: Review and curation workflow

Deliverables:

- review CLI,
- accept/reject/edit flow,
- curated export generator,
- conflict report.

Exit criteria:

- a reviewer can accept candidate materials into the curated database,
- every published datum can be traced to a source artifact.

### Milestone 4: Curated v0 dataset

Deliverables:

- first reviewed dataset for metals and polymers,
- updated `data/materials/materials.json`,
- validation tests,
- migration notes for Explorer integration.

Exit criteria:

- at least 50 reviewed materials,
- at least 10 canonical properties covered,
- no published datum lacking provenance,
- rankings exclude weak estimates by default.

### Milestone 5: Explorer integration and feedback loop

Deliverables:

- Explorer reads the generated curated dataset,
- source/basis/condition display is visible in UI,
- review findings from real Explorer usage feed back into schema and parser updates.

Exit criteria:

- materials can be filtered and ranked without obvious provenance blind spots,
- at least one export path preserves source information.

## 16. Testing and Verification

### 16.1 Automated tests

Add tests for:

- source registry validation,
- unit conversion,
- property alias mapping,
- parser output schema validation,
- identity normalization,
- curated export generation,
- regression tests for known tricky datasheets.

### 16.2 Golden files

Maintain a small set of known source artifacts with expected parser outputs. These should catch:

- OCR drift,
- column-shift parsing bugs,
- mistaken unit conversions,
- wrong property mappings.

### 16.3 Manual verification

For every ingestion milestone, manually inspect:

- at least 10 parsed artifacts,
- at least 20 accepted datums,
- at least 5 rejected datums,
- at least 5 conflict cases.

## 17. Risks and Mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Terms/licensing mistakes | Could invalidate the whole ingestion effort | Force source registry classification before automation |
| OCR and table parsing errors | Silent bad data is worse than sparse data | Human review queue; golden files; parser confidence |
| Identity collapse | Merges incompatible grades/forms | Strong canonical ID rules; no fuzzy auto-merge to publish |
| Over-flattened conditions | Makes rankings dishonest | Preserve condition metadata in staging; warn in publish layer |
| Curated schema too simple | Loses truth during export | Extend schema before volume scaling |
| Too many source types at once | Burns time before proving the loop | Start with metals + polymers and 3 adapters only |
| Dependency sprawl in runtime | Breaks Pyodide path | Keep heavy ingestion code outside `pycalcs/` |

## 18. Definition of Done for the Ingestion Backbone

This plan is fulfilled when all of the following are true:

1. the repo has a documented source registry and onboarding policy,
2. the ingestion code can process HTML, PDF, and CSV/XLSX sources into staging,
3. the review workflow can promote accepted evidence into the curated materials database,
4. the curated database used by the Explorer is generated from reviewed inputs rather than edited ad hoc,
5. every published datum can be traced to source and artifact,
6. restricted sources are cleanly separated from automatable ones,
7. the system has shipped an initial reviewed metals-and-polymers dataset.

## 19. Immediate Next Actions

1. Create `scripts/materials_ingest/README.md` and `source_registry.yaml`.
2. Populate the registry with the first 10-15 candidate sources and classify them into lanes.
3. Define the staging JSON or JSONL schemas for artifacts, candidate materials, and extracted datums.
4. Implement the adapter base class plus the CSV/XLSX adapter first.
5. Implement the HTML table adapter second.
6. Implement the PDF datasheet adapter third.
7. Build the CLI review flow before attempting broad-scale crawling.
8. Only after that, begin the first real ingestion wave for metals and polymers.

## 20. References for Source Policy

These links are relevant to source classification and should be checked before building any adapter against them:

- MatWeb terms and licensing pages
- MakeItFrom licensing and membership terms
- PoLyInfo access and use policy
- CAMPUS product/access information

The exact source posture should be recorded in `source_registry.yaml`, not left as tribal knowledge in a plan file.
