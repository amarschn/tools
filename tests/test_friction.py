import pytest

from pycalcs import friction


def test_lookup_returns_expected_ranges():
    result = friction.lookup_coefficient_of_friction("steel", "steel", "Dry Clean")

    assert result["material_a_name"].startswith("Steel")
    assert result["surface_condition"] == "Dry Clean"
    assert result["mu_static_min"] == pytest.approx(0.5)
    assert result["mu_static_max"] == pytest.approx(0.8)
    assert result["mu_static_typical"] == pytest.approx(0.65)
    assert result["mu_kinetic_min"] == pytest.approx(0.42)
    assert result["mu_kinetic_max"] == pytest.approx(0.57)
    assert result["reference"].startswith("Source IDs:")
    assert result["typical_applications"]
    assert result["comparable_pairs"]
    assert "μ_s" in result["notes"]


@pytest.mark.parametrize(
    ("left", "right", "condition"),
    [
        ("steel", "PTFE", "Dry Clean"),
        ("ptfe", "steel", "Dry Clean"),
    ],
)
def test_lookup_is_order_independent(left, right, condition):
    output = friction.lookup_coefficient_of_friction(left, right, condition)
    assert output["mu_static_typical"] == pytest.approx(0.12, abs=1e-9)


def test_lookup_raises_for_missing_pair():
    with pytest.raises(ValueError):
        friction.lookup_coefficient_of_friction("steel", "glass", "Dry Clean")


def test_catalog_lists_pairs_and_materials():
    catalog = friction.get_friction_catalog()

    assert "materials" in catalog and "combinations" in catalog
    assert "steel" in catalog["materials"]
    pair_keys = {entry["pair_key"] for entry in catalog["combinations"]}
    assert "steel-steel" in pair_keys
