"""Values, provenance and judgement calls of the October gathered batch."""

import json
from pathlib import Path

import pytest
from builder.build_site import load_database
from builder.import_gathered import HSC_TABLES, PSI
from release.compiler import compile_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def batch():
    database = load_database(ROOT)
    data, _, _, records, _ = compile_data(database)
    report = json.loads((ROOT / "curated/gathered-2026-10.json").read_text())
    return database, data, records, report


def rows(data, mid, pid):
    return [o for o in data["observations"] if o["material_id"] == mid and o["property_id"] == pid]


def value(data, mid, pid):
    return rows(data, mid, pid)[0]["result"]["canonical"]["value"]


def test_every_previously_missing_material_now_exists(batch):
    _, data, _, report = batch
    ids = {m["id"] for m in data["materials"]}
    assert {"steel-astm-a36", "stainless-440c", "steel-c45", "kevlar-29", "kevlar-49", "crystic-198",
            "styrolution-ps-158k", "exxon-ld-2119-ln", "apso-nr-60-01-02", "acp-kevlar-ud-epoxy"} <= ids
    assert report["added_materials"] == len(report["material_ids"]) == 66


def test_aluminium_alloys_gained_a_handbook_modulus(batch):
    _, data, _, report = batch
    assert sorted(report["extended_material_ids"]) == ["al-1060", "al-1100", "al-1350", "al-6005", "al-6101"]
    for mid in report["extended_material_ids"]:
        row = rows(data, mid, "youngs_modulus")[0]
        assert row["source_id"] == "asm-wrought-al" and row["state_id"] is None


def test_1350_does_not_take_the_62_gpa_printed_for_the_alloy_above_it(batch):
    _, data, _, _ = batch
    assert value(data, "al-1350", "youngs_modulus") == pytest.approx(69e9)


@pytest.mark.parametrize("mid,pid,expected", [
    ("steel-astm-a36", "youngs_modulus", 199.95e9),
    ("steel-astm-a36", "density", 7850),
    ("stainless-440c", "density", 7612),
    ("kevlar-49", "youngs_modulus", 112.4e9),
    ("kevlar-29", "ultimate_tensile_strength", 2920e6),
    ("acp-kevlar-ud-epoxy", "compressive_strength", 280e6),
    ("crystic-198", "density", 1220),
    ("styrolution-ps-158k", "density", 1048),
    ("kumho-gp-150i", "flexural_modulus", 3.231e9),
    ("mndot-hsc-reference-wet-69", "youngs_modulus", 49.30e9),
])
def test_reviewed_values_convert_correctly(batch, mid, pid, expected):
    _, data, _, _ = batch
    assert value(data, mid, pid) == pytest.approx(expected, rel=2e-3)


def test_concrete_tables_agree_in_both_printed_units():
    count = 0
    for _, bands in HSC_TABLES.values():
        for _, _, cells in bands:
            for psi, gpa in cells.values():
                assert int(psi) * PSI * 1e-9 == pytest.approx(float(gpa), abs=0.03)
                count += 1
    assert count == 39


def test_concrete_strength_levels_stay_intervals_and_say_what_they_are(batch):
    _, data, _, _ = batch
    row = rows(data, "mndot-hsc-silica-fume-wet-124", "compressive_strength")[0]
    assert row["result"]["kind"] == "interval"
    assert "Strength level" in row["notes"]
    assert "not a measured value" in rows(data, "mndot-hsc-silica-fume-wet-124", "youngs_modulus")[0]["notes"]


def test_no_density_is_invented_where_the_source_gives_none_for_the_cured_material(batch):
    _, data, _, _ = batch
    for mid in ("mndot-hsc-reference-wet-69", "polynt-norsodyne-h-16243", "polynt-enydyne-c-65134", "polynt-distitron-3501-s"):
        assert not rows(data, mid, "density"), mid


def test_suspect_printed_values_are_flagged_or_left_out(batch):
    _, data, _, _ = batch
    assert not rows(data, "apso-nr-40-75-01", "elongation_at_break")
    assert "inferred" in rows(data, "stainless-440c", "youngs_modulus")[0]["notes"]
    assert "error for 16.3" in rows(data, "kevlar-49", "youngs_modulus")[0]["notes"]
    assert rows(data, "tse-natural-rubber", "ultimate_tensile_strength")[0]["result"]["kind"] == "lower_bound"


def test_all_sources_are_pinned(batch):
    database, _, _, report = batch
    pinned = {d["id"]: d["sha256"] for d in json.loads((ROOT / "curated/gathered-2026-10-documents.json").read_text())}
    assert set(report["source_ids"]) == set(pinned)
    sources = {s["id"]: s for s in database.sources}
    assert all(sources[sid]["sha256"] == digest for sid, digest in pinned.items())
