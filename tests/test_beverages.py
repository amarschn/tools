import pytest

from pycalcs.beverages import compute_optimal_coffee_serving_temperature


def test_compute_optimal_coffee_serving_temperature_nominal():
    result = compute_optimal_coffee_serving_temperature(
        initial_temp_c=93.0,
        ambient_temp_c=22.0,
        beverage_mass_g=240.0,
        cup_material="ceramic",
        preference_profile="balanced",
    )

    assert 58.5 <= result["optimal_temp_c"] <= 60.5
    assert result["wait_time_min"] == pytest.approx(10.03, rel=1e-2)
    assert 90.0 <= result["comfort_score"] <= 100.0
    assert result["cooling_constant_per_min"] == pytest.approx(0.065, rel=1e-2)
    assert "ln" in result["subst_wait_time_min"]
    assert "Scanned" in result["subst_optimal_temp_c"]


def test_invalid_cup_material_raises():
    with pytest.raises(ValueError):
        compute_optimal_coffee_serving_temperature(
            initial_temp_c=90.0,
            ambient_temp_c=20.0,
            beverage_mass_g=200.0,
            cup_material="steel",
            preference_profile="balanced",
        )
