# Materials Ingest

This package contains the offline ingestion and governance tooling for the shared materials database.

It is intentionally separate from `pycalcs/`:

- ingestion code can use heavier or more specialized tooling later,
- the browser runtime must stay lightweight and dependency-safe,
- raw and staging data must be separated from the curated publish database.

## Current Scope

This first implementation slice covers:

1. source governance through a registry,
2. staging schema definitions,
3. audit tooling for legacy harvested review files.

It does **not** yet attempt broad crawling or automatic promotion into the curated database.

## Source Registry

The authoritative source posture lives in:

- `scripts/materials_ingest/source_registry.yaml`

The file uses JSON-compatible YAML so it can be parsed with the Python standard library today. A source must be registered and classified before any automation is allowed against it.

## Staging Schemas

Initial staging schemas live in:

- `data/materials/staging/artifact.schema.json`
- `data/materials/staging/candidate_material.schema.json`
- `data/materials/staging/extracted_datum.schema.json`

These represent the raw/staging layer from the ingestion plan, not the curated `data/materials/materials.json` serving format.

## CLI

Run from the repo root:

```bash
python -m scripts.materials_ingest.cli summarize-sources
python -m scripts.materials_ingest.cli validate-sources
python -m scripts.materials_ingest.cli audit-review data/materials/materials-review.json
python -m scripts.materials_ingest.cli import-legacy-review data/materials/materials-review-old.json
python -m scripts.materials_ingest.cli list-importers
python -m scripts.materials_ingest.cli import-source-file nicoguaro-common /path/to/common_materials.tsv
```

The review audit command is intended for files like the current Gemini-generated `materials-review.json`. It reports structural and governance issues without attempting to mutate the curated database.

The legacy import command converts a harvested review file into staging artifacts:

- `artifacts.jsonl`
- `candidate_materials.jsonl`
- `extracted_datums.jsonl`
- `import_report.json`

This is the supported bridge from exploratory harvest output into the governed ingestion pipeline.

## Source-Specific Importers

The package now includes local-file importers for:

- `nicoguaro-common`
- `nawale-metals`
- `oms-dataset`
- `nims-fatigue`

These do **not** depend on `scripts/harvest_materials.py`.

They are designed to parse raw source files directly into staging records. This keeps source-specific logic isolated and avoids routing all future imports through one catch-all harvest script.

Current stance:

- use these importers on local raw CSV/TSV files,
- keep network fetching and unattended crawling separate,
- do not bypass the source registry just because a parser exists.
