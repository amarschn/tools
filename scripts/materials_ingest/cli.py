"""Command-line helpers for the materials ingestion pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .import_legacy_review import load_and_convert_legacy_review, write_staging_bundle
from .import_source_file import load_and_import_source_file
from .importers import list_importers
from .legacy_review import audit_review_database, load_json
from .registry import get_registry_summary, load_source_registry, validate_source_registry


def _write_output(payload: dict[str, Any], output_path: str | None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if output_path:
        Path(output_path).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Materials ingestion utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summarize_sources = subparsers.add_parser(
        "summarize-sources", help="Summarize the source registry."
    )
    summarize_sources.add_argument(
        "--registry",
        default=None,
        help="Override source registry path.",
    )
    summarize_sources.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path.",
    )

    validate_sources = subparsers.add_parser(
        "validate-sources", help="Validate the source registry."
    )
    validate_sources.add_argument(
        "--registry",
        default=None,
        help="Override source registry path.",
    )

    list_source_importers = subparsers.add_parser(
        "list-importers",
        help="List source-specific local-file importers.",
    )
    list_source_importers.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path.",
    )

    audit_review = subparsers.add_parser(
        "audit-review",
        help="Audit a harvested review JSON file against ingestion expectations.",
    )
    audit_review.add_argument("path", help="Path to the review JSON file.")
    audit_review.add_argument(
        "--schema",
        default="data/materials/schema.json",
        help="Curated schema path used to validate family enums and required fields.",
    )
    audit_review.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path.",
    )

    import_review = subparsers.add_parser(
        "import-legacy-review",
        help="Convert a legacy harvested review JSON file into staging JSONL records.",
    )
    import_review.add_argument("path", help="Path to the legacy review JSON file.")
    import_review.add_argument(
        "--registry",
        default="scripts/materials_ingest/source_registry.yaml",
        help="Source registry path.",
    )
    import_review.add_argument(
        "--curated-db",
        default="data/materials/materials.json",
        help="Curated materials DB used for property metadata lookup.",
    )
    import_review.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for generated staging files. Defaults to data/materials/staging/imports/<stem>/.",
    )

    import_source = subparsers.add_parser(
        "import-source-file",
        help="Import a local raw source file using a source-specific importer.",
    )
    import_source.add_argument("importer_id", help="Importer id, for example 'nicoguaro-common'.")
    import_source.add_argument("path", help="Path to the local raw source file.")
    import_source.add_argument(
        "--registry",
        default="scripts/materials_ingest/source_registry.yaml",
        help="Source registry path.",
    )
    import_source.add_argument(
        "--curated-db",
        default="data/materials/materials.json",
        help="Curated materials DB used for property metadata lookup.",
    )
    import_source.add_argument(
        "--artifact-url",
        default=None,
        help="Optional original source URL override for the artifact record.",
    )
    import_source.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for generated staging files. Defaults to data/materials/staging/imports/<stem>-<importer>/.",
    )

    args = parser.parse_args()

    if args.command == "summarize-sources":
        registry = load_source_registry(args.registry)
        payload = get_registry_summary(registry)
        _write_output(payload, args.output)
        return 0

    if args.command == "validate-sources":
        registry = load_source_registry(args.registry)
        errors = validate_source_registry(registry)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, indent=2))
            return 1
        print(json.dumps({"valid": True, "source_count": len(registry["sources"])}, indent=2))
        return 0

    if args.command == "list-importers":
        payload = {"importers": list_importers()}
        _write_output(payload, args.output)
        return 0

    if args.command == "audit-review":
        review_db = load_json(args.path)
        schema_path = Path(args.schema)
        curated_schema = load_json(schema_path) if schema_path.exists() else None
        payload = audit_review_database(review_db, curated_schema=curated_schema)
        _write_output(payload, args.output)
        return 0

    if args.command == "import-legacy-review":
        review_path = Path(args.path)
        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else Path("data/materials/staging/imports") / review_path.stem
        )
        bundle = load_and_convert_legacy_review(
            review_path,
            source_registry_path=args.registry,
            curated_db_path=args.curated_db,
        )
        written = write_staging_bundle(bundle, output_dir)
        payload = {
            "written_files": written,
            "import_report": bundle["import_report"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "import-source-file":
        source_path = Path(args.path)
        output_dir = (
            Path(args.output_dir)
            if args.output_dir
            else Path("data/materials/staging/imports")
            / f"{source_path.stem}-{args.importer_id}"
        )
        bundle = load_and_import_source_file(
            args.importer_id,
            source_path,
            source_registry_path=args.registry,
            curated_db_path=args.curated_db,
            artifact_url=args.artifact_url,
        )
        written = write_staging_bundle(bundle, output_dir)
        payload = {
            "written_files": written,
            "import_report": bundle["import_report"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
