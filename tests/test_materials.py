from __future__ import annotations

import math

import pytest

from pycalcs.materials import rank_materials_for_ashby


@pytest.mark.parametrize(
    ("mode", "threshold", "count", "expected_name"),
    [
        ("stiffness_limited_beam", 5.0e-5, 3, "Carbon Fibre/Epoxy (UD)"),
        ("strength_limited_tie", 5.0e-5, 2, "Carbon Fibre/Epoxy (UD)"),
        ("buckling_limited_column", 1.0e-6, 4, "Carbon Fibre/Epoxy (UD)"),
    ],
)
def test_rank_materials_returns_best_candidate(mode, threshold, count, expected_name):
    result = rank_materials_for_ashby(mode, threshold, count)
    assert result["best_material_name"] == expected_name
    assert math.isfinite(result["best_material_index"])


def test_rank_materials_respects_threshold_filter():
    result = rank_materials_for_ashby("strength_limited_tie", 2.0e-4, 5)
    # Only high specific-strength materials should remain
    assert "Glass Fibre/Epoxy" in result["ranked_summary"]
    assert "Low-Carbon Steel" not in result["ranked_summary"]


def test_rank_materials_raises_on_invalid_inputs():
    with pytest.raises(ValueError):
        rank_materials_for_ashby("unknown_case", 1.0e-4, 3)
    with pytest.raises(ValueError):
        rank_materials_for_ashby("strength_limited_tie", 0.0, 3)
    with pytest.raises(ValueError):
        rank_materials_for_ashby("strength_limited_tie", 1.0e-4, 0)
