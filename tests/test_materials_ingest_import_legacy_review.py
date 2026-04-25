"""Tests for converting legacy harvested review files into staging records."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.materials_ingest.import_legacy_review import (
    convert_legacy_review_to_staging,
)


def test_convert_legacy_review_to_staging_maps_sources_and_properties():
    review_db = {
        "sources": {
            "nicoguaro-2024": {"citation": "Example", "type": "online_database"},
        },
        "materials": [
            {
                "id": "sample-a",
                "name": "Sample A",
                "family": "foam",
                "sub_family": "foams",
                "default_source_id": "nicoguaro-2024",
                "notes": "Legacy note",
                "density": {
                    "value": 40.0,
                    "min": 30.0,
                    "max": 50.0,
                    "basis": "handbook_range",
                },
                "yield_strength": {"value": 2.5e6, "basis": "typical"},
            }
        ],
    }
    source_registry = {
        "version": 1,
        "sources": [
            {
                "source_id": "nicoguaro-common-materials",
                "name": "Nicoguaro",
                "organization": "nicoguaro",
                "source_type": "tsv_export",
                "lane": "C",
                "base_url": "https://github.com/nicoguaro/material_database",
                "automation_allowed": False,
                "redistribution_allowed": False,
                "requires_login": False,
                "priority": "medium",
                "status": "pending_rights_review",
                "family_focus": ["foam"],
                "review_notes": ["Review first."],
            }
        ],
    }
    curated_db = {
        "property_registry": {
            "density": {"unit": "kg/m^3"},
            "yield_strength": {"unit": "Pa"},
        }
    }

    bundle = convert_legacy_review_to_staging(
        review_db,
        review_path="/tmp/sample-review.json",
        source_registry=source_registry,
        curated_db=curated_db,
    )

    assert len(bundle["artifacts"]) == 2
    assert len(bundle["candidate_materials"]) == 1
    assert len(bundle["extracted_datums"]) == 2
    assert bundle["candidate_materials"][0]["source_id"] == "nicoguaro-common-materials"
    assert bundle["candidate_materials"][0]["record_kind_guess"] == "foam"
    assert bundle["extracted_datums"][0]["review_status"] == "needs_review"
    assert bundle["import_report"]["unknown_property_ids"] == {}


def test_convert_legacy_review_to_staging_reports_unknown_properties_and_duplicates():
    review_db = {
        "sources": {
            "nims-fatigue-subset": {"citation": "Example", "type": "experimental_database"},
        },
        "materials": [
            {
                "id": "dup-a",
                "name": "Dup A",
                "family": "metal",
                "sub_family": "steel",
                "default_source_id": "nims-fatigue-subset",
                "fatigue_strength_10e7": {"value": 300e6, "basis": "typical"},
            },
            {
                "id": "dup-a",
                "name": "Dup A variant",
                "family": "metal",
                "sub_family": "steel",
                "default_source_id": "nims-fatigue-subset",
                "fatigue_strength_10e7": {"value": 320e6, "basis": "typical"},
            },
        ],
    }
    source_registry = {
        "version": 1,
        "sources": [
            {
                "source_id": "nims-fatigue-dataset",
                "name": "NIMS fatigue",
                "organization": "NIMS upstream",
                "source_type": "csv_export",
                "lane": "C",
                "base_url": "https://github.com/George-JieXIONG/Materials-Dataset",
                "automation_allowed": False,
                "redistribution_allowed": False,
                "requires_login": False,
                "priority": "medium",
                "status": "pending_upstream_provenance_review",
                "family_focus": ["metal"],
                "review_notes": ["Review first."],
            }
        ],
    }

    bundle = convert_legacy_review_to_staging(
        review_db,
        review_path="/tmp/sample-review.json",
        source_registry=source_registry,
        curated_db={"property_registry": {}},
    )

    keys = [item["candidate_material_key"] for item in bundle["candidate_materials"]]
    assert keys[0] != keys[1]
    assert bundle["import_report"]["duplicate_candidate_key_bases"] == 1
    assert bundle["import_report"]["unknown_property_ids"]["fatigue_strength_10e7"] == 2
