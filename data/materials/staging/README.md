# Materials Staging Data

This directory is reserved for the offline ingestion pipeline.

It is intentionally separate from:

- `data/materials/materials.json`
- `data/materials/schema.json`

Those files define the curated publish database used by the Materials Explorer. The files in this directory define the raw/staging layer needed to ingest and review evidence safely before promotion into the curated dataset.

Current contents:

- `artifact.schema.json`
- `candidate_material.schema.json`
- `extracted_datum.schema.json`

These schemas are the first step toward the raw/staging/review model defined in [engineering_materials_ingestion_plan](/Users/drew/code/tools/plans/2026-04-11_engineering_materials_ingestion_plan.md).
