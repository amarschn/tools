"""Compressive strength and the October concrete batch."""

import json
from pathlib import Path

import pytest
from builder.build_site import load_database
from builder.import_concrete import DOCUMENTS
from release.compiler import compile_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def batch():
    database = load_database(ROOT)
    data, _, _, records, _ = compile_data(database)
    report = json.loads((ROOT / "curated/concrete-2026-10.json").read_text())
    return database, data, records, report


def rows(data, mid, pid):
    return [o for o in data["observations"] if o["material_id"] == mid and o["property_id"] == pid]


def test_compressive_strength_is_registered_and_in_the_strength_group(batch):
    _, data, _, _ = batch
    assert any(p["id"] == "compressive_strength" for p in data["properties"])
    group = next(g for g in data["property_groups"] if g["id"] == "strength")
    assert "compressive_strength" in group["member_property_ids"]


def test_every_concrete_material_has_compressive_strength_and_modulus(batch):
    _, data, _, report = batch
    assert len(report["material_ids"]) == report["added_materials"] == 12
    for mid in report["material_ids"]:
        assert rows(data, mid, "compressive_strength"), mid
        assert rows(data, mid, "youngs_modulus"), mid


@pytest.mark.parametrize("mid,pid,expected,tolerance", [
    ("stocrete-ts-108", "compressive_strength", 74e6, 1),
    ("stocrete-ts-108", "density", 2100, 0.01),
    ("sikaemaco-488-ci", "youngs_modulus", 34.47e9, 0.01e9),
    ("flexcrete-monolite", "density", 1250, 0.01),
    ("emer-patch-repair-40", "youngs_modulus", 18.4e9, 1e3),
])
def test_reviewed_values_convert_correctly(batch, mid, pid, expected, tolerance):
    _, data, _, _ = batch
    assert abs(rows(data, mid, pid)[0]["result"]["canonical"]["value"] - expected) <= tolerance


def test_ranges_and_bounds_keep_their_printed_meaning(batch):
    _, data, _, _ = batch
    ductal = rows(data, "ductal-uhpc", "compressive_strength")[0]["result"]
    assert ductal["kind"] == "interval"
    assert ductal["canonical"]["minimum"] == 180e6 and ductal["canonical"]["maximum"] == 225e6
    assert rows(data, "sikacrete-650-tecfast", "compressive_strength")[0]["result"]["kind"] == "lower_bound"


def test_density_states_stay_labelled(batch):
    _, data, _, _ = batch
    assert "Fresh" in rows(data, "stocrete-sm", "density")[0]["notes"]
    assert "Hardened" in rows(data, "sikacrete-650-tecfast", "density")[0]["notes"]
    assert "Mixed" in rows(data, "flexcrete-monolite", "density")[0]["notes"]


def test_mortars_are_not_described_as_structural_concrete(batch):
    database, _, _, _ = batch
    for rid in ("stocrete-sm", "sikaemaco-488-ci", "flexcrete-monolite"):
        row = next(r for r in database.materials if r["id"] == rid)
        assert "not ready-mix concrete" in row["description"]


def test_all_sources_are_pinned(batch):
    database, _, _, report = batch
    pinned = {d[0]: d[5] for d in DOCUMENTS}
    assert set(report["source_ids"]) == set(pinned)
    sources = {s["id"]: s for s in database.sources}
    assert all(sources[sid]["sha256"] == digest for sid, digest in pinned.items())
