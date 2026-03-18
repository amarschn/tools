# Shared Parameter Profiles and Cross-Tool Input Mapping

Date: 2026-03-18
Status: Proposed architecture plan for critique before implementation
Related existing assets:
- `AGENTS.md` ("Parameter JSON Test Cases")
- `tools/composite-fracture-analyzer/test-cases/*.json`
- `tools/composite-fracture-analyzer/index.html` JSON import/export UI
- `tools/fits/fit_library.json`
- `pycalcs/units.py`

## 1. Purpose

Define a reusable, versioned input-data system for the repository that supports all of the following without turning into an unmaintainable abstraction:

1. exact save/load of a tool's current input state,
2. reusable named parameter sets that can be shared across tools,
3. metadata about source, intent, version compatibility, and provenance,
4. compatibility checks before loading into a tool,
5. eventual library/search functionality for curated engineering scenarios.

The motivating problem is real: several tools either already share inputs or will soon share them, but the current JSON pattern is tool-local, flat, and not expressive enough to safely represent cross-tool reuse.

## 2. Executive Recommendation

This is worth doing, but only if it is split into two different document types and implemented in phases.

Do not try to solve "exact tool snapshot" and "shared cross-tool profile" with one magical universal JSON format from day one. Those are related but different problems:

- A `tool input snapshot` should reproduce one tool's form state exactly.
- A `shared parameter profile` should capture canonical engineering facts that multiple tools may consume in different ways.

If those two ideas are forced into one format too early, the result will become messy very quickly:

- snapshots want tool-specific field names,
- cross-tool profiles want canonical field IDs,
- snapshots want perfect round-trip fidelity,
- profiles want partial compatibility and explicit mapping,
- snapshots are easy,
- profiles require schema, contracts, units, enum vocabularies, and migration rules.

Recommended stance:

1. Standardize tool-local JSON exports first.
2. Add explicit input contracts per tool.
3. Introduce a shared field registry only for parameter families with proven overlap.
4. Support cross-tool reuse only through declared mappings, never by guessing from field names.

## 3. Current State in This Repo

Today the repo already has a useful but narrow pattern:

- `tools/composite-fracture-analyzer/test-cases/*.json` stores flat parameter objects
- `name` and `description` are treated as UI metadata
- all other top-level keys map directly to the Python function arguments
- the tool UI can export the current form state and load those JSON files back in

This is good for sample cases and regression scenarios, but it has hard limits:

- no formal schema version,
- no formal tool compatibility contract,
- no distinction between user-entered inputs and metadata,
- no canonical parameter dictionary,
- no safe way to say "this file is partially compatible with tool B",
- no migration strategy when a tool renames or restructures inputs.

The repo also has adjacent patterns:

- `tools/fits/fit_library.json` shows that metadata-heavy JSON is already acceptable
- `pycalcs/units.py` provides a foundation for unit normalization and conversion

That means the repo is ready for a structured JSON-based system, but not yet ready for fully automatic cross-tool interoperability.

## 4. Problems to Solve Separately

There are actually at least five different needs hiding inside this idea:

### 4.1 Tool snapshots

"Save exactly what I entered in this specific tool and reload it later."

### 4.2 Sample/reference cases

"Ship known-good scenarios with the tool for demos, QA, and regression."

### 4.3 Shared engineering profiles

"Define one engineering case once, then load the relevant subset into several compatible tools."

### 4.4 Canonical parameter definitions

"Have one source of truth for what a parameter means, what units it uses, and how it maps across tools."

### 4.5 Compatibility and migration

"Know whether an older file can still be loaded into the current tool, and if not, why not."

If these are not explicitly separated, the implementation will sprawl.

## 5. Goals

### In Scope

- Versioned, human-readable input documents.
- A canonical format that works in a static browser app without server dependencies.
- Metadata for provenance and compatibility.
- Safe load behavior with explicit validation and user-facing warnings.
- Ability to reuse one scenario across multiple tools when overlap is real and declared.
- Support for curated libraries of named scenarios.
- Backward-compatible path from current flat test-case JSON files.

### Out of Scope for Initial Rollout

- Automatic inference of compatibility by matching similar field names.
- Cloud-backed user accounts or remote databases.
- Arbitrary formula execution inside imported files.
- Fully generic CSV interchange for every tool type.
- Universal mapping across unrelated tools.
- Solving every unit-conversion and every enum-translation edge case on day one.

## 6. Format Evaluation

### 6.1 JSON

Pros:

- Native in browser JavaScript.
- Already used in the repo.
- Easy to fetch, diff, validate, and export.
- No extra parser dependency needed in Pyodide or frontend JS.
- Good fit for nested metadata and typed values.

Cons:

- Less pleasant than YAML for hand-authoring comments.
- Verbose for large libraries.

Recommendation:

- Use JSON as the canonical committed format.

### 6.2 YAML

Pros:

- More pleasant for humans to hand-edit.
- Supports comments.

Cons:

- Requires a parser in the browser or a build step.
- Introduces another format to support and test.
- Easier for whitespace errors to create subtle issues.

Recommendation:

- Do not make YAML a primary format.
- Only consider YAML later as an authoring convenience that compiles to canonical JSON.

### 6.3 CSV

Pros:

- Familiar for tabular libraries.
- Easy to edit in spreadsheets.

Cons:

- Poor fit for nested metadata, enums, units, grouped values, and alternative input modes.
- Hard to represent partial mappings and compatibility contracts cleanly.

Recommendation:

- Do not use CSV as the canonical scenario format.
- Consider CSV only for export/import of simple tabular libraries later.

### 6.4 Database

Pros:

- Good for search, filtering, user libraries, multi-user curation.

Cons:

- Overkill for a static GitHub Pages / Netlify workflow.
- Adds deployment, auth, and operational complexity.

Recommendation:

- Do not start with a database.
- Start with versioned JSON files plus an index/manifest.

## 7. Recommended Architecture

The cleanest approach is a layered static-data architecture:

1. Shared metadata envelope
2. Tool input snapshot documents
3. Shared parameter profile documents
4. Canonical field registry
5. Tool input contract files
6. Compatibility/mapping engine

### 7.1 Shared Metadata Envelope

Both snapshots and shared profiles should include common metadata fields:

```json
{
  "schema_version": "1.0.0",
  "document_type": "tool_input_snapshot",
  "profile_id": "fan-rotor-pa6gf30-20krpm",
  "title": "Fan rotor finite-life reference case",
  "description": "Reference scenario for fracture and rotor tools.",
  "created_date": "2026-03-18",
  "modified_date": "2026-03-18",
  "author": "repo",
  "tags": ["rotor", "fracture", "reference-case"],
  "source": {
    "kind": "hand-entered",
    "reference": "Internal engineering scenario"
  }
}
```

Recommended required metadata:

- `schema_version`
- `document_type`
- `profile_id`
- `title`
- `created_date`

Recommended optional metadata:

- `description`
- `modified_date`
- `author`
- `tags`
- `source`
- `notes`
- `expected_behavior`
- `export_context`

## 8. Two Document Types

### 8.1 Tool Input Snapshot

Purpose:

- exact round-trip reproduction of one tool's inputs,
- regression fixtures,
- user save/load,
- sample cases that target one tool directly.

Suggested shape:

```json
{
  "schema_version": "1.0.0",
  "document_type": "tool_input_snapshot",
  "profile_id": "finite-life-radial-20k",
  "title": "Finite life radial crack at 20k RPM",
  "created_date": "2026-03-18",
  "target": {
    "tool_slug": "composite-fracture-analyzer",
    "input_contract_version": "1.0.0"
  },
  "export_context": {
    "tool_version": "0.4.0",
    "calculation_engine_version": "0.4.0",
    "build_id": "6516d37",
    "exported_at": "2026-03-18T14:22:00Z"
  },
  "inputs": {
    "geometry_type": "annular_disk",
    "inner_radius_mm": 20,
    "outer_radius_mm": 80,
    "speed_rpm": 20000
  }
}
```

Characteristics:

- uses the tool's real parameter names,
- simplest thing to export from a form,
- easiest path for immediate repo-wide standardization,
- does not require any cross-tool abstraction.

### 8.2 Shared Parameter Profile

Purpose:

- express a reusable engineering case in canonical terms,
- allow multiple tools to consume the same underlying scenario,
- support partial compatibility with explicit mapping reports.

Suggested shape:

```json
{
  "schema_version": "1.0.0",
  "document_type": "shared_parameter_profile",
  "profile_id": "annular-pa6gf30-rotor-a",
  "title": "PA6-GF30 annular rotor baseline",
  "created_date": "2026-03-18",
  "parameter_family": "rotating_disk_core",
  "values": {
    "rotor.geometry.type": "annular_disk",
    "rotor.geometry.inner_radius": {
      "value": 20,
      "unit": "mm"
    },
    "rotor.geometry.outer_radius": {
      "value": 80,
      "unit": "mm"
    },
    "rotor.operating.speed": {
      "value": 20000,
      "unit": "rpm"
    },
    "material.density": {
      "value": 1360,
      "unit": "kg/m^3"
    }
  }
}
```

Characteristics:

- uses canonical field IDs,
- does not assume any specific tool,
- requires a mapping layer before loading into a tool,
- enables controlled cross-tool reuse.

## 9. Canonical Field Registry

This is the part that makes cross-tool reuse possible.

Create a shared registry of field definitions, probably in a root-level JSON file such as:

- `references/parameter-registry/fields.json`

Each canonical field should define:

- `field_id`
- `label`
- `description`
- `data_type`
- `dimension`
- `canonical_unit`
- `enum_values` where applicable
- `valid_range` where applicable
- `aliases` only for search/documentation, not for implicit loading logic

Example:

```json
{
  "rotor.operating.speed": {
    "label": "Rotational speed",
    "description": "Steady operating rotational speed.",
    "data_type": "number",
    "dimension": "angular_speed",
    "canonical_unit": "rpm",
    "minimum": 0
  }
}
```

Important rule:

- Similar names are not enough.
- A field is only considered equivalent across tools if it maps to the same canonical field ID.

## 10. Tool Input Contracts

Each tool that wants snapshot/profile support should declare an explicit input contract file, for example:

- `tools/<tool>/input-contract.json`

This file should describe:

- tool slug
- input contract version
- backend function name
- which form fields are user inputs
- mapping from tool field names to canonical field IDs
- tool-side units
- enum translations
- required vs optional fields
- supported import document types

Example:

```json
{
  "tool_slug": "composite-fracture-analyzer",
  "input_contract_version": "1.0.0",
  "backend_function": "analyze_rotor_fracture",
  "supports": ["tool_input_snapshot", "shared_parameter_profile"],
  "fields": {
    "outer_radius_mm": {
      "canonical_field_id": "rotor.geometry.outer_radius",
      "type": "number",
      "unit": "mm",
      "required": true
    },
    "speed_rpm": {
      "canonical_field_id": "rotor.operating.speed",
      "type": "number",
      "unit": "rpm",
      "required": true
    }
  }
}
```

This is where tool versioning should live.

Important recommendation:

- Do not key compatibility to the tool's page version, repo version, or deploy date.
- Key compatibility to `input_contract_version`.

That is the real thing the file depends on.

### 10.1 Traceability and Visible Versioning

This idea is worth adding, but the version labels need to be separated by purpose.

Recommended version fields:

- `tool_version`
  Human-facing version of the overall tool page and UX.
- `input_contract_version`
  Compatibility version for saved/imported input files.
- `calculation_engine_version`
  Version for equations, defaults, solver logic, and any numerical behavior that can change results.
- `build_id`
  Exact trace token such as short git SHA, release tag, or deploy identifier.

Recommended rule:

- if a change can affect numerical outputs, bump `calculation_engine_version`
- if a change only affects layout, copy, or styling, bump `tool_version`
- if a change breaks saved-file compatibility, bump `input_contract_version`

This matters because "what version of the tool was this?" is usually not precise enough for engineering traceability. The real questions are:

1. Which UI or page version did the user see?
2. Which calculation logic produced the result?
3. Which input contract was the export based on?
4. Which exact build or commit was deployed?

### 10.2 Where Version Information Should Appear

Recommended visibility model:

- always-visible version chip in the tool header or footer
- detailed `About` or `Traceability` panel with all version fields
- embedded metadata in exported JSON, CSV, and PDF where possible
- subtle provenance stamp on exported charts/images

Recommendation on stamping:

- do not use a large diagonal watermark across the chart
- use a small bottom-right provenance stamp instead

Suggested stamp contents:

- tool slug
- `tool_version`
- `calculation_engine_version`
- export date
- `build_id`
- optional `profile_id`

Why:

- screenshots and exported graphs are often shared without the source JSON
- a visible provenance stamp makes old analyses traceable without ruining readability

### 10.3 Suggested Runtime Metadata Shape

Per-tool runtime metadata could look like this:

```json
{
  "tool_slug": "composite-fracture-analyzer",
  "tool_version": "0.4.0",
  "input_contract_version": "1.0.0",
  "calculation_engine_version": "0.4.0",
  "build_id": "6516d37",
  "release_date": "2026-03-18"
}
```

This should be treated as display and export provenance metadata, not as a substitute for the input contract.

### 10.4 UI Recommendation

Recommended visible UI elements:

- a compact version badge such as `v0.4.0`
- a hover tooltip or expandable area that shows:
  - `calculation_engine_version`
  - `input_contract_version`
  - `build_id`
  - export/profile provenance when a file is loaded

When a profile or snapshot is imported, the tool should also show:

- imported file title
- imported file creation date
- imported file schema version
- imported file compatibility result

### 10.5 Export Recommendation

Exports should carry provenance in both machine-readable and human-visible form.

For JSON:

- include full `export_context`

For CSV and tabular exports:

- prepend or append a small metadata block with tool slug, versions, build ID, and export timestamp

For PDFs and chart/image exports:

- include a footer or corner stamp with provenance

For manual screenshots:

- rely on the always-visible version badge and, where practical, a small always-visible analysis footer

### 10.6 Risks and Cautions

This only works if the repo defines version-bump discipline.

Without clear rules:

- version labels become noise,
- exported artifacts become misleading,
- users may think two results are comparable when the calculation engine changed underneath them.

Minimum rule set:

- any result-affecting change bumps `calculation_engine_version`
- any saved-file compatibility change bumps `input_contract_version`
- every export writes all three version dimensions plus `build_id`

## 11. Compatibility Model

Imported documents should not just "load" or "fail". They should produce a compatibility report.

Suggested compatibility states:

- `exact`
  All required fields mapped directly with no loss.
- `partial`
  Required fields mapped, but some optional fields are unused.
- `lossy`
  A conversion or approximation was required.
- `incompatible`
  One or more required fields are missing, ambiguous, or unsupported.

Suggested load behavior:

- Snapshots: reject if contract version is incompatible and no migration exists.
- Shared profiles: allow load only when required fields can be mapped safely.
- Always show ignored fields, unmapped fields, and transformed fields to the user.

## 12. Units, Enums, and Alternate Input Modes

These are the hidden complexity drivers.

### 12.1 Units

Cross-tool reuse requires an explicit unit policy.

Recommendation:

- canonical field registry stores one canonical unit per field,
- shared profiles store values with explicit units,
- tool contracts declare expected tool-side units,
- conversion uses `pycalcs/units.py` where possible,
- unsupported unit transforms must fail explicitly.

### 12.2 Enums and controlled vocabularies

Example problem:

- one tool might say `annular_disk`
- another might say `ring_with_bore`

Those are not load-compatible unless an explicit enum mapping exists in the tool contract.

### 12.3 Alternate input modes

Many tools can accept equivalent states through different input sets:

- `sigma_max` and `sigma_min`
- or `sigma_a` and `sigma_m`
- or maybe a preset material plus overrides

This means the system must distinguish:

- primary user-entered fields,
- derived fields,
- mutually exclusive input modes.

Recommendation:

- shared profiles store the canonical engineering facts,
- tool contracts declare which input modes they support and how a profile can populate them,
- do not store derived output values as canonical inputs.

## 13. Migration Strategy for Existing Files

The repo already contains flat snapshot-style JSON files. They should not be broken.

Recommended migration path:

### Phase 1 compatibility

Support both:

1. current legacy flat JSON:
   - top-level tool keys
   - optional `name` and `description`
2. new snapshot envelope:
   - metadata plus `inputs`

### Phase 2 normalization

- update exported files to the new snapshot envelope,
- gradually wrap existing sample cases,
- keep a legacy loader so old files still work.

### Phase 3 shared profiles

- only after tool contracts and field registry exist for the chosen pilot tools.

## 14. Storage Layout Recommendation

Suggested repository structure:

```text
/profiles/
  /shared/
    /rotating_disk_core/
      2026-03-18_annular_pa6gf30_baseline.json
  /snapshots/
    /composite-fracture-analyzer/
      2026-03-18_finite_life_radial_20k.json

/references/parameter-registry/
  fields.json
  parameter-families.json

/tools/composite-fracture-analyzer/
  input-contract.json
  test-cases/
```

Notes:

- `test-cases/` can remain tool-local for deterministic QA fixtures.
- `/profiles/shared/` should contain curated cross-tool scenario documents.
- `/profiles/snapshots/` is optional if exported user files are mostly ad hoc, but useful for committed reference cases.

## 15. UX Recommendation

The UI should distinguish three actions clearly:

### 15.1 Load snapshot

"Load an exact saved state for this tool."

### 15.2 Load shared profile

"Try to populate this tool from a cross-tool engineering profile."

This should show a compatibility summary:

- loaded fields,
- ignored fields,
- missing required fields,
- transformed fields.

### 15.3 Export snapshot

"Save exactly what is on this form right now."

Optional later action:

### 15.4 Export shared profile

"Export the subset of this tool's inputs that map cleanly into a canonical family."

That should only be enabled for tools with mature contracts and mappings.

### 15.5 Traceability UX

Every tool that supports snapshots or shared profiles should expose provenance clearly.

Recommended UX:

- show a persistent version chip on the page
- provide a `Traceability` panel that lists:
  - tool slug
  - `tool_version`
  - `calculation_engine_version`
  - `input_contract_version`
  - `build_id`
  - loaded profile title or snapshot title when applicable
- include the same provenance in exported artifacts

## 16. What Else You Are Probably Not Thinking About Yet

These are the problems most likely to make the system messy if they are not planned for up front.

### 16.1 Semantic overlap is not binary

Two tools can share 40 percent of their inputs and still be useful together. The system should embrace partial compatibility instead of pretending every import is exact.

### 16.2 Parameter names are not meaning

`thickness_mm` in one tool may not mean the same physical thing as `thickness_mm` in another. Canonical field IDs matter more than shared names.

### 16.3 Imported files may need provenance

If a parameter set came from a handbook, FEA, test coupon, vendor sheet, or field measurement, that matters. Provenance should be part of the metadata.

### 16.4 Some cases should carry expected results

For regression and validation, it may be valuable to optionally store expected outputs and tolerances.

Example future extension:

```json
{
  "expectations": {
    "composite-fracture-analyzer@1.0.0": {
      "fracture_safety_factor": {
        "value": 1.42,
        "tolerance": 0.02
      }
    }
  }
}
```

### 16.5 Library curation will need indexing

Once there are dozens of profiles, you will want a manifest with:

- title
- tags
- compatible tools
- parameter family
- validation status

That can still be static JSON and generated from files.

### 16.6 Validation status matters

Some profiles are:

- hand-entered examples,
- textbook reference cases,
- regression fixtures,
- field data,
- human-verified production references.

That status should be represented in metadata.

### 16.7 Old screenshots and exported charts need provenance

In practice, engineers will often circulate:

- screenshots,
- pasted charts in slides,
- cropped images in email or chat,
- PDFs detached from their source JSON.

If provenance is not visible on the artifact itself, traceability is lost quickly.

That is why the plan should treat version chips and export stamps as part of the data system, not as cosmetic extras.

### 16.8 Security still matters

Even in a static browser app:

- validate file shape,
- reject oversized files,
- escape metadata before inserting into the DOM,
- never execute anything from imported files.

## 17. Is It Worth Doing?

### Yes, if scoped correctly

This is worth doing because it improves:

- reproducibility,
- sharing,
- regression testing,
- migration safety,
- educational comparison across tools,
- future batch-analysis workflows.

### No, if the first implementation tries to be universal

It is not worth doing as a giant abstraction layer that assumes:

- every tool can read every profile,
- field-name similarity equals semantic compatibility,
- versioning can be hand-waved,
- units/enums will somehow sort themselves out.

That version would become brittle and expensive to maintain.

## 18. Recommended Pilot Strategy

Do this in controlled phases.

### Phase 0: Terminology and conventions

- Define `tool input snapshot` vs `shared parameter profile`.
- Define metadata envelope.
- Define `input_contract_version` concept.
- Document the conventions in `AGENTS.md`.

### Phase 1: Standardize snapshots repo-wide

- Create a shared snapshot schema.
- Update the composite fracture tool exporter to emit the new envelope.
- Keep support for legacy flat JSON.
- Add reusable import/export helpers so new tools do not copy bespoke logic.

Success criterion:

- at least one tool exports/imports the standardized snapshot format,
- existing legacy files still load.

### Phase 2: Add tool contracts

- Create `input-contract.json` for one or two tools.
- Explicitly declare tool field metadata and version compatibility.
- Build frontend validation against the contract.

Success criterion:

- importer can detect exact vs incompatible snapshot versions.

### Phase 3: Pilot a shared parameter family

Choose a parameter family with meaningful overlap. Good candidates:

1. rotating disk / rotor tools
2. fatigue tools with overlapping stress-state inputs

For the pilot:

- define canonical field IDs,
- add mappings for two tools,
- support compatibility report UI,
- do not try to cover the whole repo.

Success criterion:

- one shared profile can populate two tools with an explicit compatibility report.

### Phase 4: Curated profile library

- Add `/profiles/shared/`
- Add manifest/index generation
- Add tags, validation status, and source metadata

### Phase 5: Optional advanced features

- expected result baselines,
- batch import/export,
- CSV library export for simple tabular cases,
- YAML authoring only if really needed.

## 19. Candidate First Deliverables

If this plan moves forward, the first concrete implementation slice should probably be:

1. `schemas/tool-input-snapshot.schema.json`
2. `tools/composite-fracture-analyzer/input-contract.json`
3. per-tool runtime provenance manifest or equivalent version metadata file
4. shared JS helper for snapshot import/export/validation and provenance display
5. one migration pass for `tools/composite-fracture-analyzer/test-cases/*.json`
6. doc updates explaining snapshot vs shared profile and version semantics

That is small enough to finish and valuable enough to prove the concept.

## 20. Open Questions to Resolve Before Coding

1. Should tool-local committed sample cases remain in `test-cases/`, or should some move to `/profiles/snapshots/`?
2. Do you want exported user files to stay tool-local and exact, or do you want every export to default to the richer metadata envelope?
3. Which tool family should be the first true cross-tool pilot?
4. Should expected outputs be part of the document format, or remain test-only?
5. How much metadata is required versus optional before the format becomes annoying to use?

## 21. Bottom-Line Recommendation

Build this, but build it as:

- `exact snapshots first`,
- `contracts second`,
- `cross-tool profiles third`.

Use JSON, not YAML or CSV, as the canonical format.
Use static JSON registries, not a database, at least initially.
Use explicit field registry + tool contracts, not implied name matching.
Treat provenance and visible versioning as a core requirement, not a later polish item.

That gives you something genuinely reusable without creating a hard-to-maintain pseudo-database hidden inside ad hoc JSON files.
