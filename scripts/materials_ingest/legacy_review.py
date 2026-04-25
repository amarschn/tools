"""Audit helpers for legacy harvested review files."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_METADATA_KEYS = {
    "id",
    "name",
    "family",
    "sub_family",
    "record_kind",
    "designation",
    "common_names",
    "default_source_id",
    "condition",
    "notes",
    "related_ids",
}


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON file from *path*."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _get_allowed_families(curated_schema: dict[str, Any] | None) -> set[str]:
    if curated_schema is None:
        return {
            "metal",
            "polymer",
            "ceramic",
            "composite",
            "natural",
            "foam",
            "fabric",
            "gel",
        }

    return set(
        curated_schema["$defs"]["material_record"]["properties"]["family"]["enum"]
    )


def _property_keys(material: dict[str, Any]) -> list[str]:
    return [key for key in material if key not in DEFAULT_METADATA_KEYS]


def audit_review_database(
    review_db: dict[str, Any],
    *,
    curated_schema: dict[str, Any] | None = None,
    sparse_threshold: int = 2,
) -> dict[str, Any]:
    """Audit a legacy review database against the ingestion expectations."""
    materials = review_db.get("materials", [])
    sources = review_db.get("sources", {})
    allowed_families = _get_allowed_families(curated_schema)

    family_counts = Counter()
    duplicate_counter = Counter()
    invalid_families = Counter()
    missing_default_source_ids = 0
    missing_record_kind = 0
    sparse_records = 0
    property_level_source_count = 0
    property_count_histogram = Counter()

    for material in materials:
        material_id = material.get("id", "")
        duplicate_counter[material_id] += 1

        family = material.get("family")
        if isinstance(family, str):
            family_counts[family] += 1
            if family not in allowed_families:
                invalid_families[family] += 1

        if material.get("default_source_id") not in sources:
            missing_default_source_ids += 1

        if "record_kind" not in material:
            missing_record_kind += 1

        property_keys = _property_keys(material)
        property_count = len(property_keys)
        property_count_histogram[property_count] += 1
        if property_count <= sparse_threshold:
            sparse_records += 1

        for key in property_keys:
            value = material.get(key)
            if isinstance(value, dict) and value.get("source_id"):
                property_level_source_count += 1

    duplicate_ids = sorted(
        material_id
        for material_id, count in duplicate_counter.items()
        if material_id and count > 1
    )

    top_level_keys = sorted(review_db.keys())
    has_property_registry = "property_registry" in review_db

    return {
        "top_level_keys": top_level_keys,
        "has_property_registry": has_property_registry,
        "source_count": len(sources),
        "material_count": len(materials),
        "missing_record_kind_count": missing_record_kind,
        "invalid_family_counts": dict(sorted(invalid_families.items())),
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_id_examples": duplicate_ids[:20],
        "missing_default_source_id_count": missing_default_source_ids,
        "property_level_source_count": property_level_source_count,
        "sparse_record_count": sparse_records,
        "sparse_record_threshold": sparse_threshold,
        "family_counts": dict(sorted(family_counts.items())),
        "property_count_histogram": dict(sorted(property_count_histogram.items())),
    }
