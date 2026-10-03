"""Identity, provenance and engineering semantics of the October catalog batch."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest
from builder import prepare_source_review as source_review
from builder.build_site import load_database
from builder.import_catalog_expansion import CDA_DEFERRED_CELLS, Batch
from release.compiler import compile_data

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA256 = "34c4b3cf17a04698cba924069d8223ba35be546848a7473bf08181c112a2e19d"


@pytest.fixture(scope="module")
def expansion():
    database = load_database(ROOT)
    data, extras, _, records, _ = compile_data(database)
    report = json.loads((ROOT / "curated/catalog-expansion-2026-10.json").read_text())
    return database, data, extras, records, report


def property_row(records, mid, pid):
    return next(o for o in records[mid]["observations"] if o["property_id"] == pid)


def test_additions_are_distinct_materials_with_two_properties_not_aliases_or_states(
    expansion,
):
    database, data, _, records, report = expansion
    ids = set(report["material_ids"])
    assert len(ids) == report["added_materials"] == 1072
    assert len(ids) >= 1000
    grades = [r for r in database.materials if r["id"] in ids]
    assert len(grades) == len(ids)
    assert all(r["record_type"] == "grade" for r in grades)
    assert len({r["name"].casefold() for r in grades}) == len(grades)
    assert (
        Counter(r["family"][0] for r in grades)
        == report["families"]
        == {
            "metal": 486,
            "glass": 249,
            "wood": 97,
            "polymer": 106,
            "elastomer": 97,
            "foam": 17,
            "ceramic": 16,
            "composite": 4,
        }
    )
    for mid in ids:
        properties = {o["property_id"] for o in records[mid]["observations"]}
        assert "density" in properties and len(properties) >= 2, mid
        assert not records[mid]["states"], mid
    assert (
        sum(o["material_id"] in ids for o in data["observations"])
        == report["added_observations"]
        == 4033
    )


def test_all_656_baseline_authored_records_survive_byte_for_byte(expansion):
    database, _, _, _, report = expansion
    added = set(report["authored_ids"])
    original = [r for r in database.materials if r["id"] not in added]
    assert len(original) == 656
    digest = hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest()
    assert digest == report["baseline_authored_sha256"] == BASELINE_SHA256


def test_new_copper_designations_do_not_duplicate_existing_uns_grades(expansion):
    database, _, _, _, report = expansion
    added = set(report["authored_ids"])
    old_uns = {
        code
        for r in database.materials
        if r["id"] not in added
        for code in re.findall(r"C\d{5}", r["designations"].get("UNS", ""))
    }
    new_uns = [
        r["designations"]["UNS"]
        for r in database.materials
        if r["id"] in report["material_ids"] and r["id"].startswith("cda-")
    ]
    assert len(new_uns) == len(set(new_uns)) == 486
    assert not set(new_uns) & old_uns


def test_all_new_facts_have_pinned_sources_and_exact_literals(expansion):
    database, data, extras, _, report = expansion
    documents = {
        r["id"]: r
        for r in json.loads((ROOT / "curated/reference-manifest.json").read_text())[
            "documents"
        ]
    }
    sources = {r["id"]: r for r in database.sources}
    for o in data["observations"]:
        if o["material_id"] not in report["material_ids"]:
            continue
        source = sources[o["source_id"]]
        assert source["sha256"] == documents[source["id"]]["sha256"]
        assert re.fullmatch(r"[a-f0-9]{64}", source["sha256"])
        assert o["source_locator"]["label"]
        assert o["source_locator"]["page"] > 0
        literal = extras["observations"][o["id"]]["source_value"]
        expected = (
            float(literal["text"].replace(",", "")) * literal["scale_to_si"]
            + literal["offset_to_si"]
        )
        assert o["result"]["canonical"]["value"] == pytest.approx(expected)
        assert o["basis"] in {"reference", "typical", "computed"}
    assert all("url" not in s for s in extras["sources"])


def test_changed_source_snapshot_is_rejected(tmp_path):
    (tmp_path / "cda-C67600.html").write_text("changed table")
    batch = Batch(tmp_path)
    with pytest.raises(ValueError, match="source differs from the reviewed snapshot"):
        batch.source("cda-c67600", "cda-C67600.html", "", "", "", "")


def test_private_batch_review_checks_pins_and_keeps_output_outside_repo(
    tmp_path, monkeypatch
):
    project = tmp_path / "repo/materials-lookup"
    curated = project / "curated"
    curated.mkdir(parents=True)
    originals = tmp_path / "originals"
    originals.mkdir()
    (originals / "new.html").write_bytes(b"reviewed numerical table")
    digest = hashlib.sha256(b"reviewed numerical table").hexdigest()
    (curated / "reference-manifest.json").write_text(
        json.dumps(
            {
                "documents": [
                    {"id": "new", "filename": "new.html", "sha256": digest},
                    {"id": "older", "filename": "unavailable.html", "sha256": digest},
                ]
            }
        )
    )
    (curated / "sources.json").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "new",
                        "organization": "Publisher",
                        "title": "Table",
                        "revision": "1",
                    },
                ]
            }
        )
    )
    monkeypatch.setattr(source_review, "ROOT", project)
    output = tmp_path / "private-review"
    assert source_review.prepare(originals, output, ["new"]) == 1
    assert (output / "new.html").read_bytes() == b"reviewed numerical table"
    assert (output / "new.html").stat().st_mode & 0o777 == 0o600
    assert "new.html" in (output / "index.html").read_text()
    with pytest.raises(ValueError, match="only known source IDs"):
        source_review.prepare(originals, output, ["unknown"])
    for unsafe in (project, project.parent, project.parent / "tools/review"):
        with pytest.raises(ValueError, match="outside the repository"):
            source_review.prepare(originals, unsafe, ["new"])
    (originals / "new.html").write_bytes(b"changed")
    with pytest.raises(ValueError, match="source differs"):
        source_review.prepare(originals, tmp_path / "failed-review", ["new"])
    assert not (tmp_path / "failed-review").exists()


@pytest.mark.parametrize(
    "mid,pid,expected",
    [
        ("cda-c67600", "density", 0.302 * 0.45359237 / 0.0254**3),
        ("cda-c67600", "youngs_modulus", 15000 * 6894757.293168),
        ("cda-c67600", "thermal_conductivity", 61 * 1.7307346663714),
        ("schott-n-fk58", "youngs_modulus", 70e9),
        ("ohara-s-bsl7", "density", 2520),
        ("ohara-s-bsl7", "youngs_modulus", 80e9),
        ("wood-black-ash", "density", 0.49 * 1120),
        ("wood-black-ash", "flexural_modulus", 11e9),
        ("smooth-on-mold-max-10", "ultimate_tensile_strength", 473 * 6894.757293168),
        ("smooth-on-mold-max-10", "elongation_at_break", 5.29),
        ("diab-divinycell-ht61", "density", 65),
        ("diab-divinycell-hp60", "youngs_modulus", 75e6),
        ("mcg-ketron-gf30-peek", "youngs_modulus", 1000 * 6894757.293168),
        ("kyocera-ao201b", "specific_heat", 790),
        ("kyocera-tc030o", "flexural_strength", 1810e6),
        ("hexcel-8552-agp280-5h", "youngs_modulus", 67e9),
        ("hexcel-8552-spg196-pw", "youngs_modulus", 85e9),
        ("hexcel-8552-spg370-8h", "youngs_modulus", 86e9),
    ],
)
def test_reviewed_source_values_cover_each_family(expansion, mid, pid, expected):
    observation = property_row(expansion[3], mid, pid)
    assert observation["result"]["canonical"]["value"] == pytest.approx(expected)


def test_conditions_and_property_meanings_stay_explicit(expansion):
    _, _, _, records, _ = expansion
    wood = records["wood-black-ash"]["observations"]
    assert all(o["conditions"]["moisture_content_1"] == 0.12 for o in wood)
    assert not any(o["property_id"] == "youngs_modulus" for o in wood)
    rubber = records["smooth-on-mold-max-10"]["observations"]
    assert not any(o["property_id"] == "youngs_modulus" for o in rubber)
    assert all("temperature_K" not in o["conditions"] for o in rubber)
    assert (
        "physical state"
        in property_row(records, "smooth-on-mold-max-10", "density")["notes"]
    )
    assert (
        "ASTM D638"
        in property_row(records, "mcg-ketron-gf30-peek", "youngs_modulus")[
            "test_method"
        ]["reported_label"]
    )
    foam = property_row(records, "diab-divinycell-hp60", "youngs_modulus")
    assert foam["conditions"] == {"temperature_K": 296.15, "orientation": "ST"}
    assert not any(
        o["property_id"] == "youngs_modulus"
        for o in records["diab-divinycell-ht61"]["observations"]
    )
    laminate = property_row(records, "hexcel-8552-spg196-pw", "youngs_modulus")
    assert laminate["conditions"] == {"temperature_K": 298.15, "orientation": "L"}
    assert "37% resin" in laminate["notes"]


def test_suspect_copper_cells_and_mismatched_laminate_rows_are_not_published(expansion):
    _, data, _, records, report = expansion
    for (code, key), (literal, _) in CDA_DEFERRED_CELLS.items():
        assert any(
            e["id"] == code + "/" + key and e["source_value"] == literal
            for e in report["excluded"]
        )
        assert not any(
            o["material_id"] == "cda-" + code.lower()
            and o["source_locator"]["label"].endswith(", " + key)
            for o in data["observations"]
        )
    for mid in [
        "ohara-s-tih53wn",
        "schott-n-bk7ht",
        "wood-young-growth-redwood",
        "smooth-on-epoxacoat-neutral",
        "smooth-on-epoxacast-655-ht-hardener",
        "smooth-on-smooth-cast-310",
        "mcg-tivar-1000-uhmw-pe-colors",
    ]:
        assert mid not in records
