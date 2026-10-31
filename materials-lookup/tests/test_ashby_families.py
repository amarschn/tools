"""Coverage and source semantics for the six-family September 2026 batch."""
from collections import Counter
import json
from pathlib import Path

import pytest

from builder.build_site import load_database
from builder.import_ashby_families import DOCUMENTS
from release.compiler import compile_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def batch():
    database = load_database(ROOT)
    data, extras, _, records, _ = compile_data(database)
    return database, data, extras, records


def test_ten_distinct_new_identities_per_requested_family(batch):
    database, data, _, _ = batch
    # Later batches extend the same source tables. Keep the original batch's
    # identity boundary instead of treating every reuse of a source as new.
    new_ids = set(json.loads((ROOT / "tests/fixtures/ashby-families-2026-09-ids.json").read_text()))
    families = Counter(r["family"][0] for r in database.materials if r["id"] in new_ids)
    assert families == {"composite": 11, "wood": 10, "ceramic": 13,
                        "foam": 12, "elastomer": 10, "glass": 10}
    assert len(new_ids) == 66
    assert len({r["name"] for r in data["materials"] if r["id"] in new_ids}) == 66
    assert all(sum(o["material_id"] == mid for o in data["observations"]) >= 2 for mid in new_ids)


def prop(records, material, property_id):
    return next(o for o in records[material]["observations"] if o["property_id"] == property_id)


def test_wood_density_includes_water_and_bending_modulus_stays_distinct(batch):
    _, data, extras, records = batch
    density = prop(records, "wood-red-alder", "density")
    assert density["basis"] == "computed"
    assert density["result"]["canonical"]["value"] == pytest.approx(.41 * 1120)
    assert density["conditions"]["moisture_content_1"] == .12
    assert extras["observations"][density["id"]]["source_value"]["text"] == "0.41"
    assert "rho12 = G12" in density["notes"]
    modulus = prop(records, "wood-red-alder", "flexural_modulus")
    assert modulus["result"]["canonical"]["value"] == 9.5e9
    assert modulus["conditions"]["orientation"] == "L"
    assert not any(o["property_id"] == "youngs_modulus" for o in data["observations"] if o["material_id"].startswith("wood-"))


def test_foam_tensile_modulus_and_nominal_density_not_inferred_from_name(batch):
    records = batch[3]
    assert prop(records, "diab-divinycell-h45", "density")["result"]["canonical"]["value"] == 48
    modulus = prop(records, "diab-divinycell-h45", "youngs_modulus")
    assert modulus["result"]["canonical"]["value"] == 55e6
    assert modulus["conditions"] == {"temperature_K": 296.15, "orientation": "ST"}
    assert not any(o["property_id"] == "youngs_modulus" for o in records["diab-divinycell-f40"]["observations"])


def test_rubber_tensile_strength_is_not_a_youngs_modulus(batch):
    records = batch[3]
    strength = prop(records, "smooth-on-reoflex-20", "ultimate_tensile_strength")
    assert strength["result"]["canonical"]["value"] == pytest.approx(200 * 6894.757293168)
    assert strength["conditions"]["temperature_K"] == 296.15
    assert prop(records, "smooth-on-reoflex-20", "elongation_at_break")["result"]["canonical"]["value"] == 10
    assert not any(o["property_id"] == "youngs_modulus" for o in records["smooth-on-reoflex-20"]["observations"])


def test_composites_use_laminate_density_and_matching_cure_column(batch):
    records = batch[3]
    mid = "toray-2700-f6273c-t2xm-965"
    assert prop(records, mid, "density")["result"]["canonical"]["value"] == 1504
    modulus = prop(records, mid, "youngs_modulus")
    assert modulus["result"]["canonical"]["value"] == 58.3e9
    assert modulus["conditions"] == {"temperature_K": 295.15, "orientation": "LT"}
    assert "Oven cure" in modulus["notes"]
    assert prop(records, "hexcel-8552-8552-as4", "density")["result"]["canonical"]["value"] == 1580


def test_ceramic_limits_and_glass_units_survive(batch):
    records = batch[3]
    assert prop(records, "kyocera-f997", "density")["result"]["kind"] == "lower_bound"
    assert prop(records, "kyocera-f997", "density")["basis"] == "typical"
    interval = prop(records, "kyocera-al23", "density")["result"]
    assert interval["kind"] == "interval"
    assert interval["canonical"] == {"minimum": 3700, "maximum": 3950, "unit": "kg/m^3"}
    assert prop(records, "schott-n-bk7", "youngs_modulus")["result"]["canonical"]["value"] == 82e9
    assert prop(records, "schott-n-bk7", "specific_heat")["result"]["canonical"]["value"] == 858


def test_sources_are_pinned_without_publishing_the_documents(batch):
    database, _, extras, _ = batch
    for sid, _, _, _, _, digest, _, _, _ in DOCUMENTS:
        assert next(s for s in database.sources if s["id"] == sid)["sha256"] == digest
        public = next(s for s in extras["sources"] if s["id"] == sid)
        assert "url" not in public
