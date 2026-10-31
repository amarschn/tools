"""Provenance and judgement calls of the wood batch."""

import json
from pathlib import Path

import pytest
from builder.build_site import load_database
from builder.import_wood import EXCLUDED, GREEN_TO_12_PERCENT, SHEAR_CORRECTION, TABLE_5_3A, TABLE_5_7
from release.compiler import compile_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def batch():
    database = load_database(ROOT)
    data, extras, _, records, _ = compile_data(database)
    return database, data, extras, records


def rows(data, mid, pid):
    return [o for o in data["observations"] if o["material_id"] == mid and o["property_id"] == pid]


def number(text):
    return float(text.replace(",", ""))


def test_every_species_gains_stiffness_and_compression(batch):
    _, data, _, _ = batch
    species = [m["id"] for m in data["materials"] if m["primary_taxon_id"] == "woods"]
    assert len(species) == len(TABLE_5_3A) == 107
    assert {row[0] for row in TABLE_5_3A} == set(species)
    for mid in species:
        assert len(rows(data, mid, "youngs_modulus")) == 1, mid
        assert len(rows(data, mid, "compressive_strength")) == 1, mid


def test_youngs_modulus_is_the_printed_bending_value_plus_ten_percent(batch):
    _, data, extras, _ = batch
    for mid, _, _, modulus, _ in TABLE_5_3A:
        bending = rows(data, mid, "flexural_modulus")[0]
        assert extras["observations"][bending["id"]]["source_value"]["text"] == modulus, mid
        along = rows(data, mid, "youngs_modulus")[0]
        assert along["result"]["canonical"]["value"] == pytest.approx(number(modulus) * 1e6 * SHEAR_CORRECTION)
        assert along["basis"] == "computed"
        assert along["conditions"]["orientation"] == "L"
        assert along["conditions"]["moisture_content_1"] == 0.12
        assert extras["observations"][along["id"]]["source_value"]["text"] == modulus
        assert "footnote c" in along["test_method"]["reported_label"]


def test_compression_is_read_directly_and_cited(batch):
    _, data, extras, _ = batch
    expected = {"wood-red-alder": 40.1e6, "wood-western-hemlock": 49e6, "wood-western-white-pine": 34.7e6, "wood-butternut": 36.2e6}
    for mid, value in expected.items():
        row = rows(data, mid, "compressive_strength")[0]
        assert row["result"]["canonical"]["value"] == pytest.approx(value)
        assert row["basis"] == "reference"
        assert row["source_id"] == "usda-wood-mechanical"
        assert "Table 5-3a" in row["source_locator"]["label"]
        assert extras["observations"][row["id"]]["source_value"]["unit"] == "kPa"
    values = [number(row[4]) for row in TABLE_5_3A]
    assert 25_000 < min(values) and max(values) < 75_000


def test_tensile_strength_applies_the_adjustment_for_each_wood_class(batch):
    database, data, extras, _ = batch
    groups = {r["id"]: r["family"][1] for r in database.materials if r["id"].startswith("wood-") and r["record_type"] == "grade"}
    assert len(TABLE_5_7) == 21
    for mid, _, raw in TABLE_5_7:
        row = rows(data, mid, "ultimate_tensile_strength")[0]
        factor = GREEN_TO_12_PERCENT[groups[mid]]
        assert row["result"]["canonical"]["value"] == pytest.approx(number(raw) * 1000 * factor)
        assert row["basis"] == "computed"
        assert "tested green" in row["notes"]
        assert extras["observations"][row["id"]]["source_value"]["text"] == raw
    assert rows(data, "wood-american-beech", "ultimate_tensile_strength")[0]["result"]["canonical"]["value"] == pytest.approx(86.2e6 * 1.32)
    assert rows(data, "wood-sitka-spruce", "ultimate_tensile_strength")[0]["result"]["canonical"]["value"] == pytest.approx(59.3e6 * 1.13)
    assert not rows(data, "wood-red-alder", "ultimate_tensile_strength")


def test_batch_adds_no_material_and_records_what_it_left_out():
    ledger = json.loads((ROOT / "curated/wood-2026-10.json").read_text())
    assert ledger["added_materials"] == 0
    assert ledger["added_observations"] == 107 * 2 + 21 == 235
    assert ledger["excluded"] == EXCLUDED
    assert ledger["source_ids"] == ["usda-wood-mechanical"]
