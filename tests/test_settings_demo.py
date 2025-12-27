import pytest

from pycalcs import settings_demo


def test_calculate_settings_demo_nominal():
    result = settings_demo.calculate_settings_demo(10.0, 2.0, 5.0)

    assert result["scaled_value"] == pytest.approx(20.0)
    assert result["normalized_value"] == pytest.approx(4.0)
    assert result["percent_of_reference"] == pytest.approx(400.0)


def test_calculate_settings_demo_raises_on_zero_reference():
    with pytest.raises(ValueError):
        settings_demo.calculate_settings_demo(1.0, 1.0, 0.0)
