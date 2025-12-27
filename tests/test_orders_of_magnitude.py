import pytest

from pycalcs import orders_of_magnitude


def test_orders_of_magnitude_time_catalog():
    result = orders_of_magnitude.catalog_orders_of_magnitude("time")
    anchors = result["anchors"]
    labels = {anchor["label"] for anchor in anchors}

    assert "Second" in labels
    assert result["anchor_count"] == pytest.approx(len(anchors))

    exponents = [anchor["exponent"] for anchor in anchors]
    expected_span = max(exponents) - min(exponents)
    assert result["anchor_span_exponent"] == pytest.approx(expected_span)


def test_orders_of_magnitude_mass_human_anchor():
    result = orders_of_magnitude.catalog_orders_of_magnitude("mass")
    human_anchor = next(anchor for anchor in result["anchors"] if anchor["label"] == "Human")

    assert human_anchor["scaled_unit"] == "kg"
    assert human_anchor["scaled_value"] == pytest.approx(70.0)
