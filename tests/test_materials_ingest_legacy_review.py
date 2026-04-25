"""Tests for auditing legacy materials review files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.materials_ingest.legacy_review import audit_review_database


def test_audit_flags_missing_registry_fields():
    review_db = {
        "sources": {"src-a": {"citation": "Example", "type": "online_database"}},
        "materials": [
            {
                "id": "sample-a",
                "name": "Sample A",
                "family": "other",
                "sub_family": "misc",
                "default_source_id": "src-a",
                "density": {"value": 1000.0, "basis": "typical"},
            }
        ],
    }

    audit = audit_review_database(review_db)
    assert audit["has_property_registry"] is False
    assert audit["missing_record_kind_count"] == 1
    assert audit["invalid_family_counts"]["other"] == 1
    assert audit["property_level_source_count"] == 0


def test_audit_counts_duplicate_ids_and_sparse_records():
    review_db = {
        "sources": {"src-a": {"citation": "Example", "type": "online_database"}},
        "materials": [
            {
                "id": "dup-a",
                "name": "Duplicate A1",
                "family": "metal",
                "sub_family": "alloy",
                "default_source_id": "src-a",
                "yield_strength": {"value": 100e6, "basis": "typical"},
            },
            {
                "id": "dup-a",
                "name": "Duplicate A2",
                "family": "metal",
                "sub_family": "alloy",
                "default_source_id": "src-a",
                "yield_strength": {"value": 120e6, "basis": "typical"},
            },
        ],
    }

    audit = audit_review_database(review_db)
    assert audit["duplicate_id_count"] == 1
    assert audit["duplicate_id_examples"] == ["dup-a"]
    assert audit["sparse_record_count"] == 2
