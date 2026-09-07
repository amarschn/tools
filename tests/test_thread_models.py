"""Identification windows and physical export model regressions."""

import json
import math
from itertools import pairwise

import pytest

from pycalcs.thread_models import comparison_records, find_threads, step_model


def find(**kwargs):
    return find_threads(json.dumps(kwargs))


def test_empty_is_not_an_identification():
    assert find()["status"] == "incomplete"
    assert find()["candidates"] == []


def test_cross_system_lookalikes_are_preserved():
    result = find(diameter=7.95, pitch=1.25)
    assert result["status"] == "possible-match"
    names = [row["designation"] for row in result["candidates"]]
    assert "M8x1.25" in names
    assert "5/16-20 UNEF" not in names  # Not a supported standard pair.
    # Pitch-only comparisons must retain 1.25 mm and 20 TPI = 1.27 mm.
    pitches = [row["pitch_mm"] for row in find(pitch=1.25)["candidates"]]
    assert 1.25 in pitches and pytest.approx(1.27) in pitches


def test_internal_bore_uses_basic_minor_not_major():
    internal = find(side="internal", diameter=8.4, pitch=1.5)
    external = find(side="external", diameter=8.4, pitch=1.5)
    assert "M10x1.5" in [row["designation"] for row in internal["candidates"]]
    assert "M10x1.5" not in [row["designation"] for row in external["candidates"]]
    assert all(row["basis"] == "basic internal minor" for row in internal["candidates"])


def test_partial_measurements_and_out_of_band():
    diameter = find(diameter=10)
    assert diameter["status"] == "ambiguous"
    assert all(row["delta_p_mm"] is None for row in diameter["candidates"])
    assert find(diameter=12345, pitch=123)["status"] == "no-close-supported-match"
    assert find(side="unsure", diameter=10)["status"] == "incomplete"


def test_intervals_tpi_and_units():
    result = find(span=0.5, intervals=10, unit="in")
    assert result["pitch_mm"] == pytest.approx(1.27)
    assert len(result["equations"]) == 2
    assert find(pitch=20, pitch_unit="tpi")["pitch_mm"] == pytest.approx(1.27)
    assert find(diameter=0.25, unit="in")["diameter_mm"] == pytest.approx(6.35)
    with pytest.raises(ValueError, match="whole number"):
        find(span=10, intervals=10.5)


def test_pipe_taper_does_not_establish_diameter_match():
    result = find(diameter=13, second_diameter=14, separation=16, pitch=25.4 / 27)
    assert result["taper"] == pytest.approx(1 / 16)
    assert {row["family"] for row in result["candidates"]} >= {"npt", "nptf"}
    assert all(
        row["pitch_only"] and row["delta_d_mm"] is None for row in result["candidates"]
    )
    assert all(row["kind"] == "pipe" for row in result["candidates"])


@pytest.mark.parametrize("value", [-1, 0, "abc", "inf", "nan", 1e999, 1e308, 1e-320])
def test_bad_measurements_rejected(value):
    with pytest.raises(ValueError):
        find(diameter=value)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"span": 10},
        {"separation": 5},
        {"side": "root"},
        {"unit": "cm"},
        {"family": "fake"},
    ],
)
def test_missing_or_unsupported_basis_rejected(kwargs):
    with pytest.raises(ValueError):
        find(**kwargs)


def test_uncertainty_is_not_a_confidence_percentage():
    narrow = find(diameter=10.4, pitch=1.5, diameter_uncertainty=0.01)
    wide = find(diameter=10.4, pitch=1.5, diameter_uncertainty=0.3)
    assert not narrow["candidates"]
    assert "M10x1.5" in [row["designation"] for row in wide["candidates"]]
    assert "confidence" not in json.dumps(wide)


def test_catalog_covers_unef_and_caps_missing_pipe_geometry():
    records = comparison_records()
    assert any(row["designation"] == "1/4-32 UNEF" for row in records)
    assert len([row for row in records if row["family"] == "metric"]) >= 35
    for row in records:
        if row["kind"] == "pipe":
            assert row["diameter_mm"] is None and row["model"] is None
            assert row["capabilities"]["print_pitch"]
            assert not row["capabilities"]["step"]


@pytest.mark.parametrize("side", ["external", "internal"])
def test_physical_profile_closes_one_pitch_with_60_degree_flanks(side):
    for row in comparison_records():
        if not row["model"]:
            continue
        profile = row["model"][side]
        assert profile[-1][0] == pytest.approx(row["pitch_mm"])
        assert profile[0][1] == profile[-1][1]
        for (x1, r1), (x2, r2) in pairwise(profile):
            if r1 != r2:
                assert abs((r2 - r1) / (x2 - x1)) == pytest.approx(math.sqrt(3))


def test_step_units_defaults_and_explicit_blind_coupon():
    inch = step_model(json.dumps({"family": "unc", "size": "1/4-20 UNC"}))
    assert inch["major_diameter_mm"] == pytest.approx(6.35)
    assert inch["length_mm"] == pytest.approx(12.7)
    assert inch["length_is_default"]
    state = {
        "family": "metric",
        "size": "M10x1.5",
        "feature": "blind",
        "specimen": "internal",
    }
    with pytest.raises(ValueError, match="Blind"):
        step_model(json.dumps(state))
    assert (
        step_model(json.dumps({**state, "blind_coupon": True}))["specimen"]
        == "internal"
    )
    with pytest.raises(ValueError, match="Blind"):
        step_model(json.dumps({**state, "blind_coupon": True, "specimen": "external"}))


@pytest.mark.parametrize(
    "changes",
    [
        {"family": "npt", "size": "1/4"},
        {"length": 1000},
        {"length": 0.1},
        {"hand": "unknown"},
        {"specimen": "internal", "body_diameter": 10},
    ],
)
def test_invalid_step_requests_are_not_silently_substituted(changes):
    with pytest.raises(ValueError):
        step_model(json.dumps({"family": "metric", "size": "M10x1.5", **changes}))


@pytest.mark.parametrize("internal", [False, True])
def test_chamfer_integral_matches_known_conical_frustum(internal):
    """A conical frustum has V = pi h (r1² + r1 r2 + r2²) / 3."""
    from pycalcs.thread_models import _end_volume

    radius = 1 if internal else 2
    profile = [[0, radius], [1, radius]]
    tip, base = (2, 1) if internal else (1, 2)
    assert _end_volume(profile, 1, 3, tip, base, internal) == pytest.approx(7 * math.pi)


@pytest.mark.parametrize("specimen", ["external", "internal"])
def test_end_geometry_volume_spans_and_notes(specimen):
    state = {"family": "metric", "size": "M10x1.5", "specimen": specimen, "length": 10}
    square = step_model(json.dumps({**state, "end_style": "square"}))
    both = step_model(json.dumps(state))
    start = step_model(json.dumps({**state, "ends": "start"}))
    end = step_model(json.dumps({**state, "ends": "end"}))
    assert (
        both["expected_volume_mm3"]
        < start["expected_volume_mm3"]
        < square["expected_volume_mm3"]
    )
    assert start["expected_volume_mm3"] == end["expected_volume_mm3"]
    assert square["expected_volume_mm3"] - both["expected_volume_mm3"] == pytest.approx(
        2 * (square["expected_volume_mm3"] - start["expected_volume_mm3"])
    )
    c = both["chamfer_depth_mm"]
    assert both["full_profile_range_mm"] == pytest.approx([c, 10 - c])
    assert start["full_profile_range_mm"] == pytest.approx([c, 10])
    assert end["full_profile_range_mm"] == pytest.approx([0, 10 - c])
    assert square["full_profile_range_mm"] == [0, 10]
    assert both["chamfer_angle_deg"] == 45
    assert "EXPORT ONLY" in both["cad_note"]
    assert "not a guaranteed usable engagement length" in both["cad_note"]
    assert "CHAMFER BOTH" in both["step_name"]
    assert "no lead-in" in square["end_condition"]
    assert "START FACE (z = 0)" in start["cad_note"]
    assert "END FACE (z = overall length)" in end["cad_note"]
    if specimen == "internal":
        assert "tap's cutting lead" in both["cad_note"]
        assert "rolling-blank instruction" not in both["cad_note"]
    else:
        assert "not a rolling-blank instruction" in both["cad_note"]
        assert "No end-type compliance is claimed" in both["cad_note"]


@pytest.mark.parametrize(
    "changes",
    [
        {"end_style": "dog"},
        {"ends": "left"},
        {"chamfer_angle": 0},
        {"chamfer_angle": 90},
        {"chamfer_angle": "nan"},
        {"chamfer_depth": "inf"},
        {"chamfer_depth": -0.1},
        {"chamfer_depth": 0.01},
        {"chamfer_depth": 10},
        {"length": 1.5},
        {"specimen": "internal", "body_diameter": 10.1},
    ],
)
def test_invalid_lead_ins_are_rejected(changes):
    with pytest.raises(ValueError):
        step_model(json.dumps({"family": "metric", "size": "M10x1.5", **changes}))


def test_square_reference_can_still_be_one_pitch_long():
    model = step_model(
        json.dumps(
            {
                "family": "metric",
                "size": "M10x1.5",
                "length": 1.5,
                "end_style": "square",
            }
        )
    )
    assert model["full_profile_range_mm"] == [0, 1.5]
