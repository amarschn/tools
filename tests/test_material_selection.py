"""Traceability and condition boundaries for the Ashby catalog projection."""

from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

from pycalcs.material_selection import (
    build_selection_database, compatible_observations, observation_value,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def selection():
    manifest = json.loads((ROOT / "tools/materials/release-manifest.json").read_text())
    bundle = json.loads((ROOT / "tools/materials" / manifest["catalog"]).read_text())
    return build_selection_database(bundle)


def observation(prop="density", value=2700, *, state=None, conditions=None, kind="point"):
    return {
        "material_id": "aluminium", "state_id": state, "property_id": prop,
        "conditions": conditions or {},
        "result": {"kind": kind, "canonical": {"value": value}},
    }


def test_grade_density_is_shared_without_merging_6061_tempers(selection):
    """Hydro reports 110 MPa for T4 and 240 MPa for T6 as distinct minima."""
    points = [p for p in selection["charts"]["density|tensile_yield_strength"]["points"]
              if p["material_id"] == "al-6061"]
    assert {p["state_id"] for p in points} == {"al-6061-t4", "al-6061-t6"}
    strength = {}
    density_ids = set()
    for point in points:
        rho, sigma = [selection["observations"][oid] for oid in point["observations"]]
        density_ids.add(rho["id"])
        assert rho["state_id"] is None
        assert sigma["state_id"] == point["state_id"]
        assert sigma["result"]["kind"] == "lower_bound"
        assert sigma["source_id"] == "hydro-6061-2019"
        assert sigma["source_locator"]["page"] == 2
        strength[point["state_id"]] = sigma["plot_value"]
        assert point["scores"]["strong_light_tie"] == pytest.approx(sigma["plot_value"] / rho["plot_value"])
    assert strength == {"al-6061-t4": 110e6, "al-6061-t6": 240e6}
    assert len(density_ids) == 1


def test_missing_modulus_is_not_filled_from_old_aluminium_entry(selection):
    """The older 60-material store has 6061 modulus; this source does not."""
    assert "al-6061" in selection["materials"]
    assert not any(p["material_id"] == "al-6061" for p in selection["charts"]["density|youngs_modulus"]["points"])
    assert len(selection["materials"]) == 222


@pytest.mark.parametrize("key,left,right", [
    ("temperature_K", 293.15, 573.15),
    ("product_form", "bar", "sheet"),
    ("orientation", "longitudinal", "transverse"),
    ("thickness_m", {"minimum": 0, "maximum": .01}, {"minimum": .01, "maximum": .02}),
])
def test_conflicting_conditions_are_never_combined(key, left, right):
    a = observation(conditions={key: left})
    b = observation("youngs_modulus", 69e9, conditions={key: right})
    assert not compatible_observations(a, b)


def test_named_states_and_unspecified_strength_stay_separate():
    assert not compatible_observations(observation(state="t4"), observation("youngs_modulus", 69e9, state="t6"))
    assert not compatible_observations(observation("tensile_yield_strength", 240e6), observation("youngs_modulus", 69e9, state="t6"))
    assert compatible_observations(observation(), observation("tensile_yield_strength", 240e6, state="t6"))
    other = observation("youngs_modulus", 69e9)
    other["material_id"] = "another-grade"
    assert not compatible_observations(observation(), other)


def test_missing_condition_is_preserved_without_mutating_source():
    a = observation()
    b = observation("youngs_modulus", 69e9, conditions={"temperature_K": 293.15})
    before = deepcopy((a, b))
    assert compatible_observations(a, b)
    assert (a, b) == before
    assert a["conditions"] == {}


def test_intervals_and_bounds_keep_their_meaning():
    item = observation(kind="interval")
    item["result"]["canonical"] = {"minimum": 2000, "maximum": 3000}
    assert observation_value(item) == 2500
    assert item["result"]["kind"] == "interval"
    bound = observation("tensile_yield_strength", 240e6, kind="lower_bound")
    assert observation_value(bound) == 240e6
    assert bound["result"]["kind"] == "lower_bound"
    item["result"]["canonical"]["minimum"] = 0
    assert observation_value(item) is None


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), None])
def test_nonplottable_values_are_omitted(value):
    assert observation_value(observation(value=value)) is None


def test_scores_and_isolines_use_actual_observations(selection):
    """Check sqrt(E)/rho independently, including the line's end coordinates."""
    points = selection["charts"]["density|youngs_modulus"]["points"]
    assert len({p["material_id"] for p in points}) > 150
    for point in points:
        rho, modulus = [selection["observations"][oid]["plot_value"] for oid in point["observations"]]
        index = math.sqrt(modulus) / rho
        assert point["scores"]["stiff_light_beam"] == pytest.approx(index)
        for x, y in point["isolines"]["stiff_light_beam"]:
            assert math.sqrt(y) / x == pytest.approx(index)


def test_generated_projection_matches_published_source_and_keeps_citations(selection):
    generated = json.loads((ROOT / "data/materials/selection.json").read_text())
    manifest = json.loads((ROOT / "tools/materials/release-manifest.json").read_text())
    assert generated.pop("source_build_id") == manifest["build_id"]
    assert generated.pop("source_sha256") == manifest["files"][manifest["catalog"]]["sha256"]
    assert generated == selection
    for source in selection["sources"].values():
        assert source["organization"] and source["title"] and source["sha256"]
    payload = json.dumps(selection).lower()
    assert ".pdf" not in payload
    assert "http://" not in payload and "https://" not in payload


def test_same_property_plot_uses_one_observation_not_two_samples(selection):
    for point in selection["charts"]["density|density"]["points"]:
        assert point["observations"][0] == point["observations"][1]


def test_empty_property_is_not_offered_and_legacy_data_is_not_mixed_in(selection):
    assert "max_service_temperature" not in selection["property_registry"]
    assert "price_per_kg" not in selection["property_registry"]
    assert "carbon-fibre-epoxy-ud" not in selection["materials"]
    assert selection["charts"]["density|tensile_yield_strength"]["indices"]
