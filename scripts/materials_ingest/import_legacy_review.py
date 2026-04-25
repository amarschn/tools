"""Convert legacy harvested review JSON into staging records."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .legacy_review import DEFAULT_METADATA_KEYS

LEGACY_SOURCE_ID_MAP = {
    "nicoguaro-2024": "nicoguaro-common-materials",
    "nawale-2021": "nawale-metals-dataset",
    "oms-2020": "open-materials-selector-oms",
    "nims-fatigue-subset": "nims-fatigue-dataset",
}

RECORD_KIND_GUESSES = {
    "metal": "bulk_material",
    "polymer": "bulk_material",
    "ceramic": "bulk_material",
    "natural": "bulk_material",
    "gel": "bulk_material",
    "foam": "foam",
    "fabric": "fabric",
    "composite": "product",
}


def _slugify(value: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in value.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _content_hash_or_fallback(path: Path, payload: dict[str, Any]) -> str:
    if path.exists():
        return _content_hash(path)

    digest = hashlib.sha256()
    digest.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def _material_property_entries(material: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        (key, value)
        for key, value in material.items()
        if key not in DEFAULT_METADATA_KEYS
    ]


def _normalize_source_id(legacy_source_id: str) -> str:
    return LEGACY_SOURCE_ID_MAP.get(legacy_source_id, legacy_source_id)


def _build_source_artifacts(
    review_path: Path,
    review_db: dict[str, Any],
    source_registry: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    registry_sources = {
        source["source_id"]: source for source in source_registry.get("sources", [])
    }
    retrieved_at = _now_iso()
    review_artifact_id = f"legacy-review-{_slugify(review_path.stem)}"

    artifacts = [
        {
            "artifact_id": review_artifact_id,
            "source_id": "legacy-review-file",
            "artifact_type": "json",
            "original_url": str(review_path),
            "retrieved_at": retrieved_at,
            "http_status": None,
            "content_hash": _content_hash_or_fallback(review_path, review_db),
            "local_path": str(review_path),
            "content_type": "application/json",
            "discovery_context": "Legacy harvested review file imported into staging.",
            "parent_artifact_id": None,
        }
    ]

    source_artifact_ids: dict[str, str] = {}
    unresolved_source_ids: list[str] = []

    for legacy_source_id in sorted(review_db.get("sources", {})):
        source_id = _normalize_source_id(legacy_source_id)
        source_artifact_id = f"legacy-source-{_slugify(source_id)}"
        source_artifact_ids[source_id] = source_artifact_id
        registry_source = registry_sources.get(source_id)
        if registry_source is None:
            unresolved_source_ids.append(source_id)
            original_url = legacy_source_id
        else:
            original_url = registry_source["base_url"]

        artifacts.append(
            {
                "artifact_id": source_artifact_id,
                "source_id": source_id,
                "artifact_type": "json",
                "original_url": original_url,
                "retrieved_at": retrieved_at,
                "http_status": None,
                "content_hash": review_artifact_id,
                "local_path": str(review_path),
                "content_type": "application/json",
                "discovery_context": (
                    f"Synthetic source artifact created from {review_path.name}; "
                    "raw upstream artifact was not preserved in the legacy harvest."
                ),
                "parent_artifact_id": review_artifact_id,
            }
        )

    return artifacts, source_artifact_ids, unresolved_source_ids


def convert_legacy_review_to_staging(
    review_db: dict[str, Any],
    *,
    review_path: str | Path,
    source_registry: dict[str, Any],
    curated_db: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert a legacy review database into staging artifacts."""
    review_path = Path(review_path)
    curated_property_registry = (
        curated_db.get("property_registry", {}) if curated_db is not None else {}
    )

    artifacts, source_artifact_ids, unresolved_source_ids = _build_source_artifacts(
        review_path, review_db, source_registry
    )

    materials = review_db.get("materials", [])
    candidates: list[dict[str, Any]] = []
    datums: list[dict[str, Any]] = []

    candidate_key_counter: Counter[str] = Counter()
    unknown_property_ids: Counter[str] = Counter()
    unsupported_property_types: Counter[str] = Counter()

    for material in materials:
        legacy_source_id = material.get("default_source_id", "unknown-source")
        source_id = _normalize_source_id(legacy_source_id)
        artifact_id = source_artifact_ids.get(source_id, artifacts[0]["artifact_id"])

        base_key = _slugify(f"{source_id}-{material.get('id', 'unknown-material')}")
        candidate_key_counter[base_key] += 1
        occurrence = candidate_key_counter[base_key]
        candidate_material_key = (
            base_key if occurrence == 1 else f"{base_key}-dup-{occurrence}"
        )

        family_guess = material.get("family")
        record_kind_guess = material.get("record_kind") or RECORD_KIND_GUESSES.get(
            family_guess, "product"
        )

        raw_description_parts = []
        if material.get("notes"):
            raw_description_parts.append(str(material["notes"]))
        if material.get("condition"):
            raw_description_parts.append(f"Condition: {material['condition']}")
        raw_description_parts.append(f"Legacy material id: {material.get('id')}")

        candidates.append(
            {
                "candidate_material_key": candidate_material_key,
                "source_id": source_id,
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
            property_meta = curated_property_registry.get(property_id)
            if property_meta is None:
                unknown_property_ids[property_id] += 1

            if isinstance(raw_value, (int, float)):
                datum = {
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
                    "source_id": source_id,
                    "artifact_id": artifact_id,
                    "page_or_section": None,
                    "review_status": "needs_review",
                    "review_notes": "Imported from legacy harvested review JSON.",
                }
            elif isinstance(raw_value, dict):
                property_source_id = _normalize_source_id(
                    raw_value.get("source_id", legacy_source_id)
                )
                datum = {
                    "candidate_material_key": candidate_material_key,
                    "property_id": property_id,
                    "value": raw_value.get("value"),
                    "min": raw_value.get("min"),
                    "max": raw_value.get("max"),
                    "raw_text": json.dumps(raw_value, sort_keys=True),
                    "raw_units": None,
                    "normalized_units": property_meta.get("unit") if property_meta else None,
                    "basis": raw_value.get("basis"),
                    "test_standard": None,
                    "temperature": raw_value.get("temperature"),
                    "humidity": raw_value.get("humidity"),
                    "moisture_state": raw_value.get("moisture_state"),
                    "orientation": raw_value.get("orientation"),
                    "processing_state": raw_value.get("condition") or material.get("condition"),
                    "thickness_or_form": material.get("sub_family"),
                    "parser_confidence": None,
                    "source_id": property_source_id,
                    "artifact_id": source_artifact_ids.get(property_source_id, artifact_id),
                    "page_or_section": None,
                    "review_status": "needs_review",
                    "review_notes": "Imported from legacy harvested review JSON.",
                }
            else:
                unsupported_property_types[type(raw_value).__name__] += 1
                continue

            datums.append(datum)

    report = {
        "review_path": str(review_path),
        "artifact_count": len(artifacts),
        "candidate_material_count": len(candidates),
        "extracted_datum_count": len(datums),
        "unresolved_source_ids": sorted(set(unresolved_source_ids)),
        "unknown_property_ids": dict(sorted(unknown_property_ids.items())),
        "unsupported_property_types": dict(sorted(unsupported_property_types.items())),
        "duplicate_candidate_key_bases": sum(
            1 for count in candidate_key_counter.values() if count > 1
        ),
    }

    return {
        "artifacts": artifacts,
        "candidate_materials": candidates,
        "extracted_datums": datums,
        "import_report": report,
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True) + "\n")


def write_staging_bundle(bundle: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Write a converted staging bundle to *output_dir*."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    artifact_path = output_path / "artifacts.jsonl"
    candidate_path = output_path / "candidate_materials.jsonl"
    datum_path = output_path / "extracted_datums.jsonl"
    report_path = output_path / "import_report.json"

    _write_jsonl(artifact_path, bundle["artifacts"])
    _write_jsonl(candidate_path, bundle["candidate_materials"])
    _write_jsonl(datum_path, bundle["extracted_datums"])
    report_path.write_text(
        json.dumps(bundle["import_report"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "artifacts": str(artifact_path),
        "candidate_materials": str(candidate_path),
        "extracted_datums": str(datum_path),
        "import_report": str(report_path),
    }


def load_and_convert_legacy_review(
    review_path: str | Path,
    *,
    source_registry_path: str | Path,
    curated_db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load a legacy review JSON file and convert it into staging records."""
    review_db = _load_json(review_path)
    source_registry = _load_json(source_registry_path)
    curated_db = _load_json(curated_db_path) if curated_db_path else None
    return convert_legacy_review_to_staging(
        review_db,
        review_path=review_path,
        source_registry=source_registry,
        curated_db=curated_db,
    )
