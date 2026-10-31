"""Values, provenance and identity of the October chart staples batch."""

import json
from pathlib import Path

import pytest
from builder.build_site import load_database
from builder.import_chart_staples import DOCUMENTS
from release.compiler import compile_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def batch():
    database = load_database(ROOT)
    data, _, _, records, _ = compile_data(database)
    report = json.loads((ROOT / "curated/chart-staples-2026-10.json").read_text())
    return database, data, records, report


def rows(data, mid, pid):
    return [o for o in data["observations"] if o["material_id"] == mid and o["property_id"] == pid]


def test_every_new_material_has_density_and_modulus(batch):
    _, data, _, report = batch
    assert len(report["material_ids"]) == report["added_materials"] == 15
    for mid in report["material_ids"]:
        assert rows(data, mid, "density"), mid
        assert rows(data, mid, "youngs_modulus"), mid


def test_extended_grades_now_plot_on_the_stiffness_chart(batch):
    _, data, _, report = batch
    assert len(report["extended_material_ids"]) == 8
    for mid in report["extended_material_ids"]:
        assert rows(data, mid, "density"), mid
        assert rows(data, mid, "youngs_modulus"), mid


@pytest.mark.parametrize("mid,pid,expected,tolerance", [
    ("al-7075", "youngs_modulus", 71.0e9, 0.1e9),
    ("al-7075", "density", 2796, 1),
    ("al-7075", "ultimate_tensile_strength", 537.8e6, 0.5e6),
    ("al-2024", "tensile_yield_strength", 324.1e6, 0.5e6),
    ("mg-az31b", "density", 1769, 1),
    ("inconel-718", "youngs_modulus", 202.7e9, 0.1e9),
    ("stainless-17-4ph", "ultimate_tensile_strength", 1310e6, 1e6),
    ("al-6063", "youngs_modulus", 69.5e9, 0.01e9),
    ("steel-atlas-4140", "density", 7833, 1),
    ("arkema-plexiglas-g", "youngs_modulus", 3.103e9, 0.001e9),
    ("pilkington-float-glass", "youngs_modulus", 72e9, 0.01e9),
])
def test_reviewed_values_convert_correctly(batch, mid, pid, expected, tolerance):
    _, data, _, _ = batch
    canonical = rows(data, mid, pid)[0]["result"]["canonical"]
    assert abs(canonical["value"] - expected) <= tolerance


def test_design_minimums_stay_lower_bounds_in_a_named_state(batch):
    _, data, _, _ = batch
    row = rows(data, "al-7075", "ultimate_tensile_strength")[0]
    assert row["result"]["kind"] == "lower_bound"
    assert row["state_id"] == "al-7075-t6"
    assert row["conditions"]["product_form"] == "sheet"
    assert row["conditions"]["orientation"] == "L"


def test_physical_values_are_grade_level_so_they_pair_with_any_state(batch):
    _, data, _, report = batch
    for mid in report["material_ids"] + report["extended_material_ids"]:
        for row in rows(data, mid, "youngs_modulus"):
            assert row["state_id"] is None, mid


def test_cross_supplier_values_say_so(batch):
    _, data, _, _ = batch
    for mid in ("steel-atlas-4140", "steel-atlas-4340", "steel-atlas-8620h"):
        assert "not an Atlas" in rows(data, mid, "youngs_modulus")[0]["notes"]
    assert "computer-generated" in rows(data, "vectorply-e-ltm-1808", "youngs_modulus")[0]["notes"]


def test_all_sources_are_pinned_and_recorded(batch):
    database, _, _, report = batch
    pinned = {d[0]: d[5] for d in DOCUMENTS}
    assert set(report["source_ids"]) == set(pinned)
    sources = {s["id"]: s for s in database.sources}
    for sid, digest in pinned.items():
        assert sources[sid]["sha256"] == digest


def test_gaps_are_recorded_rather_than_estimated(batch):
    database, _, _, report = batch
    assert {e["id"] for e in report["excluded"]} >= {"astm-a36"}
    assert not any("a36" in r["id"] for r in database.materials)
