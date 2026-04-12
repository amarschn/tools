"""Tests for pycalcs.material_indices — performance index library."""

from __future__ import annotations

import math

import pytest

from pycalcs.material_db import get_material, get_value, load_database
from pycalcs.material_indices import (
    INDICES,
    PerformanceIndex,
    compute_index,
    custom_index,
    get_isoline_points,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    return load_database(reload=True)


@pytest.fixture(scope="module")
def al6061(db):
    return get_material("al-6061-t6", db)


@pytest.fixture(scope="module")
def steel_4340(db):
    return get_material("steel-4340", db)


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_has_16_indices(self):
        assert len(INDICES) == 16

    def test_all_have_required_fields(self):
        for idx in INDICES.values():
            assert isinstance(idx, PerformanceIndex)
            assert idx.id
            assert idx.name
            assert idx.expression_display
            assert idx.expression_latex
            assert len(idx.required_properties) > 0
            assert callable(idx.compute)
            assert idx.derivation
            assert idx.scope
            assert idx.source
            assert isinstance(idx.maximize, bool)
            assert idx.chart_x
            assert idx.chart_y

    def test_ids_are_unique(self):
        ids = list(INDICES.keys())
        assert len(ids) == len(set(ids))

    def test_all_ids_match_keys(self):
        for key, idx in INDICES.items():
            assert key == idx.id


# ---------------------------------------------------------------------------
# Compute correctness
# ---------------------------------------------------------------------------

class TestCompute:
    def test_stiff_light_tie(self, al6061):
        val = compute_index("stiff_light_tie", al6061)
        expected = 69e9 / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_stiff_light_beam(self, al6061):
        val = compute_index("stiff_light_beam", al6061)
        expected = math.sqrt(69e9) / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_stiff_light_plate(self, al6061):
        val = compute_index("stiff_light_plate", al6061)
        expected = (69e9) ** (1 / 3) / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_strong_light_tie(self, al6061):
        val = compute_index("strong_light_tie", al6061)
        sy = get_value(al6061, "yield_strength")
        expected = sy / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_strong_light_beam(self, al6061):
        val = compute_index("strong_light_beam", al6061)
        sy = get_value(al6061, "yield_strength")
        expected = sy ** (2 / 3) / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_strong_light_plate(self, al6061):
        val = compute_index("strong_light_plate", al6061)
        sy = get_value(al6061, "yield_strength")
        expected = sy ** (1 / 2) / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_max_elastic_energy_mass(self, al6061):
        val = compute_index("max_elastic_energy_mass", al6061)
        sy = get_value(al6061, "yield_strength")
        expected = sy ** 2 / (69e9 * 2700)
        assert val == pytest.approx(expected, rel=1e-6)

    def test_max_elastic_energy_vol(self, al6061):
        val = compute_index("max_elastic_energy_vol", al6061)
        sy = get_value(al6061, "yield_strength")
        expected = sy ** 2 / 69e9
        assert val == pytest.approx(expected, rel=1e-6)

    def test_heat_spreading_mass(self, al6061):
        val = compute_index("heat_spreading_mass", al6061)
        k = get_value(al6061, "thermal_conductivity")
        expected = k / 2700
        assert val == pytest.approx(expected, rel=1e-6)

    def test_thermal_insulation(self, al6061):
        val = compute_index("thermal_insulation", al6061)
        k = get_value(al6061, "thermal_conductivity")
        assert val == pytest.approx(1.0 / k, rel=1e-6)

    def test_returns_none_for_missing_props(self, db):
        # Silicone rubber has no yield_strength
        m = get_material("silicone-rubber", db)
        if m is not None:
            assert compute_index("strong_light_tie", m) is None

    def test_all_indices_return_finite_for_al6061(self, al6061):
        for idx_id, idx in INDICES.items():
            val = compute_index(idx_id, al6061)
            if val is not None:
                assert math.isfinite(val), f"{idx_id} returned non-finite: {val}"

    def test_damage_tolerant(self, steel_4340):
        val = compute_index("damage_tolerant", steel_4340)
        if val is not None:
            kic = get_value(steel_4340, "fracture_toughness")
            sy = get_value(steel_4340, "yield_strength")
            if kic and sy:
                assert val == pytest.approx(kic / sy, rel=1e-6)


# ---------------------------------------------------------------------------
# Isoline generation
# ---------------------------------------------------------------------------

class TestIsolines:
    def test_linear_slope_index(self):
        pts = get_isoline_points("stiff_light_tie", 1e7, (100, 20000))
        assert pts is not None
        assert len(pts) == 2
        # slope=1 means Y = M * X
        x1, y1 = pts[0]
        assert y1 == pytest.approx(1e7 * 100, rel=1e-6)

    def test_quadratic_slope_index(self):
        pts = get_isoline_points("stiff_light_beam", 3.0, (500, 10000))
        assert pts is not None
        x1, y1 = pts[0]
        # slope=2 means Y = (M * X)^2
        assert y1 == pytest.approx((3.0 * 500) ** 2, rel=1e-6)

    def test_no_isoline_for_multi_prop_index(self):
        pts = get_isoline_points("max_elastic_energy_mass", 1.0, (100, 10000))
        assert pts is None

    def test_raises_for_unknown_index(self):
        with pytest.raises(KeyError):
            get_isoline_points("nonexistent_index", 1.0, (100, 1000))


# ---------------------------------------------------------------------------
# Custom index
# ---------------------------------------------------------------------------

class TestCustomIndex:
    def test_custom_matches_preset(self, al6061):
        # E^0.5 / rho should match stiff_light_beam
        val = custom_index(
            al6061,
            [("youngs_modulus", 0.5)],
            [("density", 1.0)],
        )
        expected = compute_index("stiff_light_beam", al6061)
        assert val == pytest.approx(expected, rel=1e-6)

    def test_custom_with_missing_prop(self, db):
        m = get_material("silicone-rubber", db)
        if m is not None:
            val = custom_index(
                m,
                [("yield_strength", 1.0)],
                [("density", 1.0)],
            )
            assert val is None


# ---------------------------------------------------------------------------
# Backward compatibility with pycalcs.materials
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """Verify the old materials.py API still works."""

    def test_old_rank_still_works(self):
        from pycalcs.materials import rank_materials_for_ashby

        result = rank_materials_for_ashby("stiffness_limited_beam", 5e-5, 3)
        assert result["best_material_name"] == "Carbon Fibre/Epoxy (UD)"
        assert math.isfinite(result["best_material_index"])
