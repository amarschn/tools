"""Tests for bore-first rolling-bearing screening."""

import json
import math
from pathlib import Path

import pytest

from pycalcs.bearings import (
    BEARING_CATALOG,
    basic_rating_life_hours,
    equivalent_dynamic_load,
    equivalent_static_load,
    get_bearing_type_metadata,
    list_bore_sizes,
    select_bearings,
)


def catalog_bearing(designation: str) -> dict:
    """Return one test catalog row by designation."""
    return next(
        row for row in BEARING_CATALOG if row["designation"] == designation
    )


def test_catalog_has_one_of_each_type_at_each_supported_bore():
    """The v1 catalog slice stays complete and deterministic."""
    assert list_bore_sizes() == [25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    assert len(BEARING_CATALOG) == 30
    expected_types = set(get_bearing_type_metadata())
    for bore in list_bore_sizes():
        rows = [row for row in BEARING_CATALOG if row["bore_mm"] == bore]
        assert {row["bearing_type"] for row in rows} == expected_types


def test_catalog_values_retain_ntn_units_and_source_metadata():
    """A transcribed row preserves representative NTN catalog values."""
    bearing = catalog_bearing("6206")
    assert bearing["bore_mm"] == 30.0
    assert bearing["outside_diameter_mm"] == 62.0
    assert bearing["dynamic_rating_n"] == 21_600.0
    assert bearing["static_rating_n"] == 11_300.0
    assert bearing["grease_speed_rpm"] == 11_000.0
    assert bearing["manufacturer"] == "NTN"
    assert bearing["source_url"].startswith("https://www.ntnglobal.com/")


def test_basic_ball_bearing_life_matches_hand_calculation():
    """L10h follows 10^6/(60n)*(C/P)^3 for a ball bearing."""
    result = basic_rating_life_hours(10_000, 2_000, 1_000, 3.0)
    assert result["life_million_revolutions"] == pytest.approx(125.0)
    assert result["life_revolutions"] == pytest.approx(125_000_000.0)
    assert result["life_hours"] == pytest.approx(2083.3333333333)


def test_basic_roller_life_uses_ten_thirds_exponent():
    """Roller-bearing rating life uses the catalog 10/3 exponent."""
    result = basic_rating_life_hours(20_000, 5_000, 1_200, 10.0 / 3.0)
    expected = 1_000_000 / (60 * 1_200) * 4 ** (10.0 / 3.0)
    assert result["life_hours"] == pytest.approx(expected)


def test_deep_groove_dynamic_load_switches_factor_branch():
    """Deep-groove P switches from Fr to XFr+YFa above the interpolated e."""
    bearing = catalog_bearing("6205")
    radial_only = equivalent_dynamic_load(1_000, 0, bearing)
    combined = equivalent_dynamic_load(1_000, 1_000, bearing)
    assert radial_only["load_n"] == 1_000
    assert radial_only["x_factor"] == 1.0
    assert combined["x_factor"] == 0.56
    assert combined["y_factor"] > 1.0
    assert combined["load_n"] > 1_500


def test_angular_contact_catalog_factors_are_applied():
    """The 30-degree angular-contact combined-load branch uses X=.39 and Y=.76."""
    result = equivalent_dynamic_load(1_000, 1_000, catalog_bearing("7205"))
    assert result["x_factor"] == pytest.approx(0.39)
    assert result["y_factor"] == pytest.approx(0.76)
    assert result["load_n"] == pytest.approx(1_150.0)


def test_spherical_dynamic_and_static_factors_are_applied():
    """Spherical roller factors match the selected NTN catalog row."""
    bearing = catalog_bearing("22206EAW33")
    dynamic = equivalent_dynamic_load(3_000, 1_200, bearing)
    static = equivalent_static_load(3_000, 1_200, bearing)
    assert dynamic["x_factor"] == pytest.approx(0.67)
    assert dynamic["y_factor"] == pytest.approx(3.20)
    assert dynamic["load_n"] == pytest.approx(5_850.0)
    assert static["load_n"] == pytest.approx(5_520.0)


def test_nu_cylindrical_rejects_axial_load():
    """NU candidates are never allowed to silently ignore axial load."""
    with pytest.raises(ValueError, match="do not support axial load"):
        equivalent_dynamic_load(3_000, 1, catalog_bearing("NU206EA"))


def test_nominal_selection_compares_all_five_families():
    """A common duty returns complete, ranked, plot-ready screening results."""
    result = select_bearings(3_000, 800, 1_800, 30)
    assert result["status"] == "acceptable"
    assert len(result["candidates"]) == 5
    assert result["recommendation"]["designation"] == "4T-32006X"
    assert result["recommendation"]["qualified_count"] >= 1
    assert result["life_chart"]["required_life_hours"] == 20_000
    assert len(result["load_sensitivity"]["load_multipliers"]) == 6
    cylindrical = next(
        item
        for item in result["candidates"]
        if item["bearing_type"] == "cylindrical_roller"
    )
    assert cylindrical["status"] == "not_applicable"


def test_pure_radial_duty_keeps_nu_candidate_applicable():
    """NU bearings participate normally in radial-only floating-position duty."""
    result = select_bearings(4_000, 0, 1_500, 35)
    cylindrical = next(
        item
        for item in result["candidates"]
        if item["bearing_type"] == "cylindrical_roller"
    )
    assert cylindrical["applicable"] is True
    assert math.isfinite(cylindrical["life_hours"])
    assert cylindrical["load_n"] == 4_000


def test_speed_and_formula_range_failures_are_explicit():
    """Overspeed and very heavy loading cannot be reported as acceptable."""
    overspeed = select_bearings(
        1_000,
        0,
        20_000,
        25,
        bearing_types_csv="deep_groove_ball",
    )
    candidate = overspeed["candidates"][0]
    assert candidate["checks"]["speed"] is False
    assert candidate["status"] == "unacceptable"

    heavy = select_bearings(
        20_000,
        0,
        1_000,
        25,
        bearing_types_csv="deep_groove_ball",
    )
    assert heavy["candidates"][0]["checks"]["life_formula_range"] is False
    assert "formula range" in heavy["candidates"][0]["warnings"][0]


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"radial_load_n": 0, "axial_load_n": 0}, "At least one"),
        ({"speed_rpm": 0}, "Speed and required life"),
        ({"bore_mm": 32}, "Bore must be one of"),
        ({"lubrication": "water"}, "Lubrication"),
        ({"bearing_types_csv": "magnetic"}, "Unsupported bearing type"),
    ],
)
def test_selection_rejects_invalid_inputs(kwargs, message):
    """Invalid or unsupported duty inputs produce actionable errors."""
    inputs = {
        "radial_load_n": 3_000,
        "axial_load_n": 0,
        "speed_rpm": 1_500,
        "bore_mm": 30,
    }
    inputs.update(kwargs)
    with pytest.raises(ValueError, match=message):
        select_bearings(**inputs)


@pytest.mark.parametrize(
    "case_path",
    sorted(
        (Path(__file__).parents[1] / "tools" / "bearing-selector" / "test-cases").glob(
            "*.json"
        )
    ),
)
def test_documented_engineering_cases_remain_executable(case_path):
    """Tool-local example files are executable regression cases, not stale prose."""
    case = json.loads(case_path.read_text(encoding="utf-8"))
    result = select_bearings(**case["inputs"])
    expected = case["expected"]
    assert result["status"] == expected["status"]
    assert result["recommendation"]["designation"] == expected[
        "recommended_designation"
    ]
    if "excluded_designation" in expected:
        excluded = next(
            item
            for item in result["candidates"]
            if item["designation"] == expected["excluded_designation"]
        )
        assert excluded["status"] == "not_applicable"
