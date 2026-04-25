"""Tests for the materials ingestion source registry helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.materials_ingest.registry import (
    get_registry_summary,
    load_source_registry,
    validate_source_registry,
)


def test_registry_loads():
    registry = load_source_registry()
    assert registry["version"] >= 1
    assert len(registry["sources"]) >= 3


def test_registry_validates_cleanly():
    registry = load_source_registry()
    assert validate_source_registry(registry) == []


def test_registry_summary_has_lane_counts():
    registry = load_source_registry()
    summary = get_registry_summary(registry)
    assert summary["source_count"] == len(registry["sources"])
    assert "C" in summary["lane_counts"]
    assert all(
        source_id in summary["blocked_source_ids"]
        for source_id in ("nicoguaro-common-materials", "nawale-metals-dataset")
    )
