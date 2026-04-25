"""Source registry helpers for the materials ingestion pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_LANES = {"A", "B", "C", "D"}
ALLOWED_SOURCE_TYPES = {
    "api",
    "csv_export",
    "html_export",
    "licensed",
    "reference_only",
    "tsv_export",
    "vendor_html",
    "vendor_pdf",
    "xlsx_export",
}
ALLOWED_PRIORITIES = {"high", "medium", "low"}
ALLOWED_STATUSES = {
    "active",
    "blocked_mixed_provenance",
    "licensed_only",
    "pending_rights_review",
    "pending_upstream_provenance_review",
    "reference_only",
}

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "source_registry.yaml"


def load_source_registry(path: str | Path | None = None) -> dict[str, Any]:
    """Load the source registry.

    The registry file uses JSON-compatible YAML so it can be parsed with the
    standard library for now.
    """
    registry_path = Path(path) if path else DEFAULT_REGISTRY_PATH
    with open(registry_path, encoding="utf-8") as fh:
        return json.load(fh)


def validate_source_registry(registry: dict[str, Any]) -> list[str]:
    """Return a list of validation errors for *registry*."""
    errors: list[str] = []

    if not isinstance(registry, dict):
        return ["Registry root must be an object."]

    version = registry.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append("Registry must include integer version >= 1.")

    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("Registry must include a non-empty 'sources' array.")
        return errors

    seen_ids: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"{prefix}.source_id must be a non-empty string.")
        elif source_id in seen_ids:
            errors.append(f"{prefix}.source_id {source_id!r} is duplicated.")
        else:
            seen_ids.add(source_id)

        for key in ("name", "organization", "base_url", "status"):
            value = source.get(key)
            if not isinstance(value, str) or not value:
                errors.append(f"{prefix}.{key} must be a non-empty string.")

        lane = source.get("lane")
        if lane not in ALLOWED_LANES:
            errors.append(f"{prefix}.lane must be one of {sorted(ALLOWED_LANES)}.")

        source_type = source.get("source_type")
        if source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(
                f"{prefix}.source_type must be one of {sorted(ALLOWED_SOURCE_TYPES)}."
            )

        priority = source.get("priority")
        if priority not in ALLOWED_PRIORITIES:
            errors.append(
                f"{prefix}.priority must be one of {sorted(ALLOWED_PRIORITIES)}."
            )

        status = source.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(ALLOWED_STATUSES)}.")

        for key in ("automation_allowed", "redistribution_allowed", "requires_login"):
            value = source.get(key)
            if not isinstance(value, bool):
                errors.append(f"{prefix}.{key} must be a boolean.")

        family_focus = source.get("family_focus")
        if not isinstance(family_focus, list) or not family_focus:
            errors.append(f"{prefix}.family_focus must be a non-empty string array.")
        elif not all(isinstance(item, str) and item for item in family_focus):
            errors.append(f"{prefix}.family_focus entries must be non-empty strings.")

        review_notes = source.get("review_notes")
        if not isinstance(review_notes, list) or not review_notes:
            errors.append(f"{prefix}.review_notes must be a non-empty string array.")
        elif not all(isinstance(item, str) and item for item in review_notes):
            errors.append(f"{prefix}.review_notes entries must be non-empty strings.")

        if lane == "A" and not source.get("automation_allowed", False):
            errors.append(f"{prefix} is lane A but automation_allowed is false.")
        if lane in {"C", "D"} and source.get("automation_allowed", False):
            errors.append(f"{prefix} must not allow automation for lane {lane}.")

    return errors


def get_registry_summary(registry: dict[str, Any]) -> dict[str, Any]:
    """Return a compact summary of the source registry."""
    sources = registry.get("sources", [])
    lane_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    for source in sources:
        lane = source.get("lane", "unknown")
        status = source.get("status", "unknown")
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "version": registry.get("version"),
        "source_count": len(sources),
        "lane_counts": dict(sorted(lane_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "automatable_source_ids": sorted(
            source["source_id"]
            for source in sources
            if source.get("automation_allowed") is True
        ),
        "blocked_source_ids": sorted(
            source["source_id"]
            for source in sources
            if source.get("automation_allowed") is False
        ),
    }
