"""Tests for pycalcs.material_db — the materials database query layer."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from pycalcs.material_db import (
    compare_materials,
    filter_materials,
    find_substitutes,
    get_basis,
    get_computed_property,
    get_material,
    get_range,
    get_source,
    get_value,
    load_database,
    rank_by_index,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    return load_database(reload=True)


@pytest.fixture(scope="module")
def al6061(db):
    m = get_material("al-6061-t6", db)
    assert m is not None
    return m


# ---------------------------------------------------------------------------
# Database loading
# ---------------------------------------------------------------------------

class TestLoadDatabase:
    def test_loads_successfully(self, db):
        assert "sources" in db
        assert "property_registry" in db
        assert "materials" in db

    def test_has_minimum_materials(self, db):
        assert len(db["materials"]) >= 60

    def test_all_materials_have_required_fields(self, db):
        for m in db["materials"]:
            assert "id" in m
            assert "name" in m
            assert "family" in m
            assert "sub_family" in m
            assert "record_kind" in m
            assert "default_source_id" in m

    def test_all_default_source_ids_resolve(self, db):
        for m in db["materials"]:
            sid = m["default_source_id"]
            assert sid in db["sources"], f"{m['id']}: source {sid!r} not in registry"

    def test_validates_against_schema(self, db):
        schema_path = Path(__file__).resolve().parent.parent / "data" / "materials" / "schema.json"
        if not schema_path.exists():
            pytest.skip("schema.json not found")
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        with open(schema_path) as f:
            schema = json.load(f)
        jsonschema.validate(db, schema)


# ---------------------------------------------------------------------------
# get_value
# ---------------------------------------------------------------------------

class TestGetValue:
    def test_scalar_property(self, al6061):
        assert get_value(al6061, "density") == 2700.0

    def test_rich_datum(self, al6061):
        # yield_strength is a rich datum with value key
        val = get_value(al6061, "yield_strength")
        assert val is not None
        assert isinstance(val, float)
        assert val > 0

    def test_missing_property(self, al6061):
        assert get_value(al6061, "nonexistent_property") is None

    def test_null_property(self, db):
        # Find a material with an explicit null
        for m in db["materials"]:
            if m.get("fracture_toughness") is None and "fracture_toughness" not in m:
                continue
            if m.get("fracture_toughness") is None:
                assert get_value(m, "fracture_toughness") is None
                return
        # If no null found that's fine, skip

    def test_returns_float(self, al6061):
        # Even for integer input, should return float
        val = get_value(al6061, "density")
        assert isinstance(val, float)


# ---------------------------------------------------------------------------
# get_range
# ---------------------------------------------------------------------------

class TestGetRange:
    def test_rich_datum_with_range(self, al6061):
        r = get_range(al6061, "yield_strength")
        assert r is not None
        lo, hi = r
        assert lo < hi
        val = get_value(al6061, "yield_strength")
        assert lo <= val <= hi

    def test_scalar_has_no_range(self, al6061):
        assert get_range(al6061, "density") is None

    def test_missing_has_no_range(self, al6061):
        assert get_range(al6061, "nonexistent") is None


# ---------------------------------------------------------------------------
# get_source
# ---------------------------------------------------------------------------

class TestGetSource:
    def test_default_source(self, al6061, db):
        src = get_source(al6061, "density", db["sources"])
        assert src is not None
        assert "citation" in src

    def test_overridden_source(self, db):
        # Find a material with property-level source_id
        for m in db["materials"]:
            for prop in ("density", "youngs_modulus", "yield_strength", "price_per_kg"):
                raw = m.get(prop)
                if isinstance(raw, dict) and raw.get("source_id"):
                    src = get_source(m, prop, db["sources"])
                    assert src is not None
                    return
        pytest.skip("No property-level source_id found in database")


# ---------------------------------------------------------------------------
# get_basis
# ---------------------------------------------------------------------------

class TestGetBasis:
    def test_defaults_to_typical(self, al6061):
        assert get_basis(al6061, "density") == "typical"

    def test_explicit_basis(self, db):
        for m in db["materials"]:
            for prop in ("yield_strength", "tensile_strength", "price_per_kg", "compressive_strength"):
                raw = m.get(prop)
                if isinstance(raw, dict) and raw.get("basis"):
                    assert get_basis(m, prop) == raw["basis"]
                    return
        pytest.skip("No explicit basis found")


# ---------------------------------------------------------------------------
# get_computed_property
# ---------------------------------------------------------------------------

class TestGetComputedProperty:
    def test_specific_stiffness(self, al6061):
        val = get_computed_property(al6061, "specific_stiffness")
        expected = 69e9 / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_specific_strength(self, al6061):
        val = get_computed_property(al6061, "specific_strength")
        sy = get_value(al6061, "yield_strength")
        expected = sy / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_thermal_diffusivity(self, al6061):
        val = get_computed_property(al6061, "thermal_diffusivity")
        k = get_value(al6061, "thermal_conductivity")
        rho = get_value(al6061, "density")
        cp = get_value(al6061, "specific_heat")
        if k and rho and cp:
            assert val == pytest.approx(k / (rho * cp), rel=1e-6)

    def test_falls_back_to_stored(self, al6061):
        # Non-computed property should fall back to get_value
        assert get_computed_property(al6061, "density") == get_value(al6061, "density")

    def test_missing_input_returns_none(self, db):
        # Silicone rubber has no yield_strength, so specific_strength is None
        m = get_material("silicone-rubber", db)
        if m is not None:
            assert get_computed_property(m, "specific_strength") is None


# ---------------------------------------------------------------------------
# get_material
# ---------------------------------------------------------------------------

class TestGetMaterial:
    def test_finds_by_id(self, db):
        m = get_material("ss-304", db)
        assert m is not None
        assert m["name"] == "Stainless Steel 304"

    def test_returns_none_for_unknown(self, db):
        assert get_material("unobtainium", db) is None


# ---------------------------------------------------------------------------
# filter_materials
# ---------------------------------------------------------------------------

class TestFilterMaterials:
    def test_filter_by_family(self, db):
        metals = filter_materials(family="metal", db=db)
        assert all(m["family"] == "metal" for m in metals)
        assert len(metals) > 0

    def test_filter_by_sub_family(self, db):
        results = filter_materials(sub_family="stainless-steel", db=db)
        assert all(m["sub_family"] == "stainless-steel" for m in results)

    def test_filter_by_search(self, db):
        results = filter_materials(search="inconel", db=db)
        assert len(results) >= 2
        for m in results:
            haystack = (m["name"] + m["id"]).lower()
            assert "inconel" in haystack

    def test_filter_by_property_range(self, db):
        light = filter_materials(
            property_ranges={"density": (None, 2000)},
            db=db,
        )
        for m in light:
            assert get_value(m, "density") <= 2000

    def test_combined_filters(self, db):
        results = filter_materials(
            family="metal",
            property_ranges={"density": (None, 5000)},
            db=db,
        )
        for m in results:
            assert m["family"] == "metal"
            assert get_value(m, "density") <= 5000

    def test_no_results_returns_empty(self, db):
        results = filter_materials(search="zzz_nonexistent_zzz", db=db)
        assert results == []


# ---------------------------------------------------------------------------
# rank_by_index
# ---------------------------------------------------------------------------

class TestRankByIndex:
    def test_ranks_descending_by_default(self, db):
        ranked = rank_by_index(
            db["materials"],
            lambda m: get_value(m, "youngs_modulus"),
            limit=5,
        )
        vals = [v for _, v in ranked]
        assert vals == sorted(vals, reverse=True)

    def test_ranks_ascending(self, db):
        ranked = rank_by_index(
            db["materials"],
            lambda m: get_value(m, "density"),
            higher_is_better=False,
            limit=5,
        )
        vals = [v for _, v in ranked]
        assert vals == sorted(vals)

    def test_skips_none(self, db):
        ranked = rank_by_index(
            db["materials"],
            lambda m: get_value(m, "fracture_toughness"),
        )
        for _, v in ranked:
            assert v is not None
            assert math.isfinite(v)

    def test_limit(self, db):
        ranked = rank_by_index(
            db["materials"],
            lambda m: get_value(m, "density"),
            limit=3,
        )
        assert len(ranked) == 3


# ---------------------------------------------------------------------------
# compare_materials
# ---------------------------------------------------------------------------

class TestCompareMaterials:
    def test_basic_comparison(self, db):
        rows = compare_materials(
            ["al-6061-t6", "ss-304"],
            ["density", "youngs_modulus"],
            db=db,
        )
        assert len(rows) == 2
        assert rows[0]["property"] == "density"
        assert rows[0]["al-6061-t6"] == pytest.approx(2700)
        assert rows[0]["ss-304"] == pytest.approx(8000)

    def test_unknown_material_gives_none(self, db):
        rows = compare_materials(
            ["al-6061-t6", "unobtainium"],
            ["density"],
            db=db,
        )
        assert rows[0]["unobtainium"] is None


# ---------------------------------------------------------------------------
# find_substitutes
# ---------------------------------------------------------------------------

class TestFindSubstitutes:
    def test_finds_similar_materials(self, db):
        subs = find_substitutes(
            "al-6061-t6",
            ["density", "youngs_modulus"],
            tolerance=0.3,
            db=db,
        )
        assert len(subs) > 0
        for m, dist in subs:
            assert dist <= 0.3

    def test_raises_for_unknown(self, db):
        with pytest.raises(ValueError):
            find_substitutes("unobtainium", ["density"], db=db)

    def test_sorted_by_distance(self, db):
        subs = find_substitutes(
            "al-6061-t6",
            ["density", "youngs_modulus"],
            tolerance=0.5,
            db=db,
        )
        dists = [d for _, d in subs]
        assert dists == sorted(dists)
