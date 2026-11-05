"""Traceability and condition boundaries for the Ashby catalog projection."""

from copy import deepcopy
import gzip
from itertools import combinations
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from pycalcs.material_selection import (
    build_chart_files, build_selection_database, compatible_observations,
    compatible_rows, index_exponents, observation_value,
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
    """The older 60-material store has these moduli; the curated sources do not."""
    plotted = {p["material_id"] for p in selection["charts"]["density|youngs_modulus"]["points"]}
    assert {"al-6042", "al-6105"} <= set(selection["materials"])
    assert not {"al-6042", "al-6105"} & plotted
    assert len(selection["materials"]) == 1453


def test_6061_modulus_comes_from_the_pinned_handbook(selection):
    rows = [o for o in selection["observations"].values()
            if o["material_id"] == "al-6061" and o["property_id"] == "youngs_modulus"]
    assert [o["source_id"] for o in rows] == ["mil-hdbk-5j"]
    assert any(p["material_id"] == "al-6061" for p in selection["charts"]["density|youngs_modulus"]["points"])


def test_every_october_addition_has_a_plottable_density_property_pair(selection):
    report = json.loads((ROOT / "materials-lookup/curated/catalog-expansion-2026-10.json").read_text())
    plotted = {p["material_id"] for key, chart in selection["charts"].items()
               if key.startswith("density|") and key != "density|density"
               for p in chart["points"]}
    assert set(report["material_ids"]) <= plotted


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


def test_titanium_room_temperature_reference_pair_keeps_both_temperatures(selection):
    points = [p for p in selection["charts"]["density|youngs_modulus"]["points"]
              if p["material_id"] in {"ti-6al-4v", "ti-6al-2sn-4zr-6mo"}]
    assert {p["material_id"] for p in points} == {
        "ti-6al-4v", "ti-6al-2sn-4zr-6mo"}
    for point in points:
        assert point["temperatures_K"] == [293.15, 295.15]
        assert "temperature_K" not in point["conditions"]
        assert {selection["observations"][oid]["conditions"]["temperature_K"]
                for oid in point["observations"]} == {293.15, 295.15}
    assert not compatible_observations(
        observation(conditions={"temperature_K": 295.15}),
        observation("youngs_modulus", 100e9,
                    conditions={"temperature_K": 303.15}),
    )


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


def assert_projection_matches(actual, expected, path=()):
    """Compare exactly except for adjacent floats in computed isoline endpoints.

    Fractional powers in get_isoline_points can differ by one representable
    float across platform math libraries. Only coordinates at
    charts/<chart>/points/<point>/isolines/<index>/<endpoint>/<axis> permit
    that roundoff; source values, scores, citations and structure remain exact.
    """
    if isinstance(expected, dict):
        assert isinstance(actual, dict), path
        assert actual.keys() == expected.keys(), path
        for key in expected:
            assert_projection_matches(actual[key], expected[key], (*path, key))
    elif isinstance(expected, list):
        assert isinstance(actual, list), path
        assert len(actual) == len(expected), path
        for position, (left, right) in enumerate(zip(actual, expected)):
            assert_projection_matches(left, right, (*path, position))
    elif (len(path) == 8 and path[0] == "charts" and path[2] == "points"
          and path[4] == "isolines" and path[6] in (0, 1) and path[7] in (0, 1)):
        assert type(actual) in (int, float) and type(expected) in (int, float), path
        assert math.isfinite(actual) and math.isfinite(expected), path
        assert (
            math.nextafter(expected, -math.inf)
            <= actual <= math.nextafter(expected, math.inf)
        ), (path, actual, expected)
    else:
        assert actual == expected, (path, actual, expected)


def test_generated_projection_matches_published_source_and_keeps_citations(selection):
    generated = json.loads((ROOT / "data/materials/selection.json").read_text())
    manifest = json.loads((ROOT / "tools/materials/release-manifest.json").read_text())
    assert generated.pop("source_build_id") == manifest["build_id"]
    assert generated.pop("source_sha256") == manifest["files"][manifest["catalog"]]["sha256"]
    assert_projection_matches(generated, selection)
    for source in selection["sources"].values():
        assert source["organization"] and source["title"] and source["sha256"]
    payload = json.dumps(selection).lower()
    assert ".pdf" not in payload
    assert "http://" not in payload and "https://" not in payload


@pytest.fixture
def projection_sample():
    """Small projection for testing the scope of the roundoff allowance."""
    return {
        "observations": {"rho": {"plot_value": 2700.0}},
        "sources": {"source": {"title": "Reference", "sha256": "original"}},
        "charts": {"density|youngs_modulus": {
            "properties": ["density", "youngs_modulus"],
            "points": [{
                "observations": ["rho", "e"],
                "conditions": {"temperature_K": 293.15},
                "scores": {"stiff_light_beam": 42.0},
                "isolines": {"stiff_light_beam": [[100.0, 200.0], [400.0, 800.0]]},
            }],
        }},
    }


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("direction", [-math.inf, math.inf])
def test_projection_comparison_accepts_only_adjacent_endpoint_floats(
    projection_sample, axis, direction
):
    expected = deepcopy(projection_sample)
    endpoint = projection_sample["charts"]["density|youngs_modulus"]["points"][0][
        "isolines"]["stiff_light_beam"][1]
    endpoint[axis] = math.nextafter(endpoint[axis], direction)
    assert_projection_matches(projection_sample, expected)
    endpoint[axis] = math.nextafter(endpoint[axis], direction)
    with pytest.raises(AssertionError):
        assert_projection_matches(projection_sample, expected)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "800"])
def test_projection_comparison_rejects_invalid_endpoint_values(projection_sample, value):
    expected = deepcopy(projection_sample)
    projection_sample["charts"]["density|youngs_modulus"]["points"][0][
        "isolines"]["stiff_light_beam"][1][1] = value
    with pytest.raises(AssertionError):
        assert_projection_matches(projection_sample, expected)


@pytest.mark.parametrize("change", [
    "observation", "score", "condition", "citation", "source_hash",
    "missing_line", "extra_line", "missing_endpoint", "point_reference",
])
def test_projection_comparison_keeps_source_data_and_structure_exact(
    projection_sample, change
):
    expected = deepcopy(projection_sample)
    point = projection_sample["charts"]["density|youngs_modulus"]["points"][0]
    if change == "observation":
        projection_sample["observations"]["rho"]["plot_value"] = math.nextafter(2700.0, math.inf)
    elif change == "score":
        point["scores"]["stiff_light_beam"] = math.nextafter(42.0, math.inf)
    elif change == "condition":
        point["conditions"]["temperature_K"] = math.nextafter(293.15, math.inf)
    elif change == "citation":
        projection_sample["sources"]["source"]["title"] = "Changed reference"
    elif change == "source_hash":
        projection_sample["sources"]["source"]["sha256"] = "changed"
    elif change == "missing_line":
        del point["isolines"]["stiff_light_beam"]
    elif change == "extra_line":
        point["isolines"]["extra"] = [[100.0, 200.0], [400.0, 800.0]]
    elif change == "missing_endpoint":
        point["isolines"]["stiff_light_beam"].pop()
    else:
        point["observations"][0] = "another-observation"
    with pytest.raises(AssertionError):
        assert_projection_matches(projection_sample, expected)


def chart_files(selection):
    return build_chart_files(selection)


def published_pairs(selection):
    pairs = set()
    for key, chart in selection["charts"].items():
        if chart["properties"][0] != chart["properties"][1]:
            pairs |= {frozenset(point["observations"]) for point in chart["points"]}
    return pairs


def test_rows_reproduce_every_published_pair_and_no_others(selection):
    core, details = chart_files(selection)
    ids = [row["id"] for row in details["observations"]]
    found = set()
    for row in core["rows"]:
        names = [ids[i] for i in row]
        found |= {frozenset(pair) for pair in combinations(names, 2)}
    assert found == published_pairs(selection)
    # Every observation appears somewhere, including those with no partner.
    assert {ids[i] for row in core["rows"] for i in row} == set(selection["observations"])


def test_each_row_holds_compatible_observations_with_one_value_per_property(selection):
    core, details = chart_files(selection)
    observations = selection["observations"]
    for row in core["rows"]:
        items = [observations[details["observations"][i]["id"]] for i in row]
        assert len({item["property_id"] for item in items}) == len(items)
        assert len({item["material_id"] for item in items}) == 1
        for left, right in combinations(items, 2):
            assert compatible_observations(left, right)


def test_rows_are_maximal_so_no_larger_combination_is_lost():
    density = {**observation(), "id": "rho"}
    modulus = {**observation("youngs_modulus", 69e9), "id": "e"}
    t4 = {**observation("tensile_yield_strength", 110e6, state="t4"), "id": "t4"}
    t6 = {**observation("tensile_yield_strength", 240e6, state="t6"), "id": "t6"}
    rows = [{item["id"] for item in row} for row in compatible_rows([density, modulus, t4, t6])]
    assert sorted(rows, key=sorted) == [{"e", "rho", "t4"}, {"e", "rho", "t6"}]


def test_a_batch_with_too_many_rows_stops_the_build(selection, monkeypatch):
    monkeypatch.setattr("pycalcs.material_selection.MAX_ROWS_PER_MATERIAL", 10)
    with pytest.raises(ValueError, match="compatible rows"):
        build_chart_files(selection)


def test_index_exponents_come_from_the_python_formula(selection):
    core, _ = chart_files(selection)
    for key, index in core["indices"].items():
        assert index["exponents"], key
    assert core["indices"]["stiff_light_beam"]["exponents"] == pytest.approx(
        {"youngs_modulus": 0.5, "density": -1})
    assert core["indices"]["strong_light_beam"]["exponents"] == pytest.approx(
        {"tensile_yield_strength": 2 / 3, "density": -1})
    assert core["indices"]["strong_light_beam"]["y"] == "tensile_yield_strength"
    not_power = SimpleNamespace(required_properties=("a", "b"), compute=lambda m: m["a"] + m["b"])
    assert index_exponents(not_power) is None


def test_chart_files_match_the_release_and_carry_no_document_links(selection):
    manifest = json.loads((ROOT / "tools/materials/release-manifest.json").read_text())
    for name in ("selection-core.json", "selection-details.json"):
        generated = json.loads((ROOT / "data/materials" / name).read_text())
        assert generated["source_build_id"] == manifest["build_id"]
        assert generated["source_sha256"] == manifest["files"][manifest["catalog"]]["sha256"]
        payload = json.dumps(generated).lower()
        assert ".pdf" not in payload
        assert "http://" not in payload and "https://" not in payload
        assert "private-sources" not in payload
    core, details = chart_files(selection)
    assert json.loads((ROOT / "data/materials/selection-core.json").read_text())["rows"] == core["rows"]
    assert len(details["observations"]) == len(core["observations"]["value"])
    # The first-paint file holds no citations.
    assert "source" not in core["observations"]
    assert all("locator" in row and "source" in row for row in details["observations"])
    assert set(details["sources"]) <= set(selection["sources"])


def test_first_paint_file_stays_small(selection):
    raw = (ROOT / "data/materials/selection-core.json").read_bytes()
    assert len(gzip.compress(raw)) < 200_000


def test_core_values_round_only_for_plotting_and_details_keep_full_precision(selection):
    core, details = chart_files(selection)
    for i, row in enumerate(details["observations"]):
        source = selection["observations"][row["id"]]
        assert row["value"] == source["plot_value"]
        assert core["observations"]["value"][i] == pytest.approx(source["plot_value"], rel=1e-8)


def test_same_property_plot_uses_one_observation_not_two_samples(selection):
    for point in selection["charts"]["density|density"]["points"]:
        assert point["observations"][0] == point["observations"][1]


def test_empty_property_is_not_offered_and_legacy_data_is_not_mixed_in(selection):
    assert "max_service_temperature" not in selection["property_registry"]
    assert "price_per_kg" not in selection["property_registry"]
    assert "carbon-fibre-epoxy-ud" not in selection["materials"]
    assert selection["charts"]["density|tensile_yield_strength"]["indices"]
