"""Convert a source-specific raw file into staging records."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .import_legacy_review import RECORD_KIND_GUESSES, write_staging_bundle
from .importers import get_importer


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slugify(value: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in value.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _material_property_entries(material: dict[str, Any]) -> list[tuple[str, Any]]:
    metadata_keys = {
        "id",
        "name",
        "family",
        "sub_family",
        "record_kind",
        "designation",
        "common_names",
        "condition",
        "notes",
        "related_ids",
    }
    return [(key, value) for key, value in material.items() if key not in metadata_keys]


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON file from *path*."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def import_source_file_to_staging(
    importer_id: str,
    input_path: str | Path,
    *,
    source_registry: dict[str, Any],
    curated_db: dict[str, Any],
    artifact_url: str | None = None,
) -> dict[str, Any]:
    """Parse a source-specific raw file into staging records."""
    importer = get_importer(importer_id)
    input_path = Path(input_path)
    parse_result = importer.parse_file(input_path)

    property_registry = curated_db.get("property_registry", {})
    artifact_id = f"source-artifact-{_slugify(importer.source_id)}-{_slugify(input_path.stem)}"

    artifacts = [
        {
            "artifact_id": artifact_id,
            "source_id": importer.source_id,
            "artifact_type": importer.artifact_type,
            "original_url": artifact_url or importer.default_url or str(input_path),
            "retrieved_at": _now_iso(),
            "http_status": None,
            "content_hash": _content_hash(input_path),
            "local_path": str(input_path),
            "content_type": None,
            "discovery_context": (
                f"Imported from local raw source file via source-specific importer {importer_id}."
            ),
            "parent_artifact_id": None,
        }
    ]

    candidates: list[dict[str, Any]] = []
    datums: list[dict[str, Any]] = []

    candidate_key_counter: Counter[str] = Counter()
    unknown_property_ids: Counter[str] = Counter()

    for material in parse_result.materials:
        base_key = _slugify(f"{importer.source_id}-{material.get('id', 'unknown-material')}")
        candidate_key_counter[base_key] += 1
        occurrence = candidate_key_counter[base_key]
        candidate_material_key = base_key if occurrence == 1 else f"{base_key}-dup-{occurrence}"

        family_guess = material.get("family")
        record_kind_guess = material.get("record_kind") or RECORD_KIND_GUESSES.get(
            family_guess, "product"
        )

        raw_description_parts = []
        if material.get("notes"):
            raw_description_parts.append(str(material["notes"]))
        if material.get("condition"):
            raw_description_parts.append(f"Condition: {material['condition']}")
        raw_description_parts.append(f"Source material id: {material.get('id')}")

        candidates.append(
            {
                "candidate_material_key": candidate_material_key,
                "source_id": importer.source_id,
                "manufacturer": None,
                "trade_name": None,
                "grade_or_designation": material.get("designation"),
                "generic_family_guess": family_guess,
                "record_kind_guess": record_kind_guess,
                "form_guess": material.get("sub_family"),
                "raw_title": material.get("name", candidate_material_key),
                "raw_description": " | ".join(raw_description_parts),
                "related_artifact_ids": [artifact_id],
            }
        )

        for property_id, raw_value in _material_property_entries(material):
            property_meta = property_registry.get(property_id)
            if property_meta is None:
                unknown_property_ids[property_id] += 1

            if isinstance(raw_value, (int, float)):
                datums.append(
                    {
                        "candidate_material_key": candidate_material_key,
                        "property_id": property_id,
                        "value": float(raw_value),
                        "min": None,
                        "max": None,
                        "raw_text": str(raw_value),
                        "raw_units": None,
                        "normalized_units": property_meta.get("unit") if property_meta else None,
                        "basis": None,
                        "test_standard": None,
                        "temperature": None,
                        "humidity": None,
                        "moisture_state": None,
                        "orientation": None,
                        "processing_state": material.get("condition"),
                        "thickness_or_form": material.get("sub_family"),
                        "parser_confidence": None,
                        "source_id": importer.source_id,
                        "artifact_id": artifact_id,
                        "page_or_section": None,
                        "review_status": "needs_review",
                        "review_notes": f"Imported via source-specific importer {importer_id}.",
                    }
                )
                continue

            if not isinstance(raw_value, dict):
                continue

            notes = raw_value.get("notes")
            review_note = f"Imported via source-specific importer {importer_id}."
            if notes:
                review_note = f"{review_note} {notes}"

            datums.append(
                {
                    "candidate_material_key": candidate_material_key,
                    "property_id": property_id,
                    "value": raw_value.get("value"),
                    "min": raw_value.get("min"),
                    "max": raw_value.get("max"),
                    "raw_text": json.dumps(raw_value, sort_keys=True),
                    "raw_units": None,
                    "normalized_units": property_meta.get("unit") if property_meta else None,
                    "basis": raw_value.get("basis"),
                    "test_standard": raw_value.get("test_standard"),
                    "temperature": raw_value.get("temperature"),
                    "humidity": raw_value.get("humidity"),
                    "moisture_state": raw_value.get("moisture_state"),
                    "orientation": raw_value.get("orientation"),
                    "processing_state": raw_value.get("condition") or material.get("condition"),
                    "thickness_or_form": material.get("sub_family"),
                    "parser_confidence": None,
                    "source_id": importer.source_id,
                    "artifact_id": artifact_id,
                    "page_or_section": None,
                    "review_status": "needs_review",
                    "review_notes": review_note,
                }
            )

    report = {
        "importer_id": importer_id,
        "source_id": importer.source_id,
        "input_path": str(input_path),
        "artifact_count": len(artifacts),
        "candidate_material_count": len(candidates),
        "duplicate_candidate_key_bases": sum(
            1 for count in candidate_key_counter.values() if count > 1
        ),
        "extracted_datum_count": len(datums),
        "unknown_property_ids": dict(sorted(unknown_property_ids.items())),
        "parse_report": parse_result.report,
    }

    return {
        "artifacts": artifacts,
        "candidate_materials": candidates,
        "extracted_datums": datums,
        "import_report": report,
    }


def load_and_import_source_file(
    importer_id: str,
    input_path: str | Path,
    *,
    source_registry_path: str | Path,
    curated_db_path: str | Path,
    artifact_url: str | None = None,
) -> dict[str, Any]:
    """Load registry and curated DB, then import a source-specific raw file."""
    return import_source_file_to_staging(
        importer_id,
        input_path,
        source_registry=load_json(source_registry_path),
        curated_db=load_json(curated_db_path),
        artifact_url=artifact_url,
    )


__all__ = [
    "import_source_file_to_staging",
    "load_and_import_source_file",
    "write_staging_bundle",
]
