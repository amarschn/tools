"""Analytical and regression checks for one-dimensional wall conduction."""

import math

import pytest

from pycalcs.heat_transfer import composite_wall_analysis
from pycalcs.utils import get_documentation


def wall(**overrides):
    """Evaluate a 2 m², two-layer wall with a 30 K boundary difference."""
    arguments = {
        "area": 2.0,
        "interior_temperature": 30.0,
        "exterior_temperature": 0.0,
        "layer_thicknesses": [0.1, 0.2],
        "layer_conductivities": [0.2, 0.2],
    }
    return composite_wall_analysis(**(arguments | overrides))


def test_two_layer_analytical_solution_without_films():
    """Fourier series network: R_A=0.1/0.2+0.2/0.2=1.5 m² K/W."""
    result = wall()
    assert result["total_r_value_si"] == pytest.approx(1.5)
    assert result["total_thermal_resistance"] == pytest.approx(0.75)
    assert result["overall_u_value"] == pytest.approx(2 / 3)
    assert result["heat_flux"] == pytest.approx(20)
    assert result["heat_transfer_rate"] == pytest.approx(40)
    assert result["film_resistances"] == {}
    assert result["interface_temperatures"] == pytest.approx([20, 0])
    assert result["temperature_profile"][0]["name"] == "Interior surface"


def test_films_and_layers_preserve_energy_at_each_interface():
    """Add R_A=0.5 at each film: 30 K / 2.5 m² K/W = 12 W/m²."""
    result = wall(
        interior_convection_coefficient=2,
        exterior_convection_coefficient=2,
    )
    assert result["total_r_value_si"] == pytest.approx(2.5)
    assert result["heat_transfer_rate"] == pytest.approx(24)
    assert result["film_resistances"] == pytest.approx(
        {"interior": 0.25, "exterior": 0.25}
    )
    profile = result["temperature_profile"]
    assert [node["temperature_c"] for node in profile] == pytest.approx(
        [30, 24, 18, 6, 0]
    )
    assert [node["distance_m"] for node in profile] == pytest.approx(
        [0, 0, 0.1, 0.3, 0.3]
    )
    assert [node["cumulative_resistance_k_per_w"] for node in profile] == (
        pytest.approx([0, 0.25, 0.5, 1.0, 1.25])
    )
    for previous, current in zip(profile, profile[1:]):
        temperature_drop = previous["temperature_c"] - current["temperature_c"]
        assert temperature_drop / current["resistance_k_per_w"] == (
            pytest.approx(result["heat_transfer_rate"])
        )


@pytest.mark.parametrize("film_side", ["interior", "exterior"])
def test_one_sided_film(film_side):
    result = wall(**{f"{film_side}_convection_coefficient": 2})
    assert result["total_r_value_si"] == pytest.approx(2)
    assert result["heat_transfer_rate"] == pytest.approx(30)
    assert set(result["film_resistances"]) == {film_side}
    profile = result["temperature_profile"]
    assert profile[-1]["temperature_c"] == pytest.approx(0)
    assert profile[-1]["cumulative_resistance_k_per_w"] == pytest.approx(1)
    assert profile[-1]["distance_m"] == pytest.approx(0.3)


def test_area_scales_heat_flow_but_not_u_or_area_normalized_r():
    small = wall(area=1)
    large = wall(area=10)
    for key in (
        "overall_u_value", "overall_u_value_ip", "total_r_value_si",
        "total_r_value_ip", "heat_flux", "heat_flux_ip",
    ):
        assert large[key] == pytest.approx(small[key])
    assert large["heat_transfer_rate"] == pytest.approx(
        10 * small["heat_transfer_rate"]
    )
    assert large["total_thermal_resistance"] == pytest.approx(
        small["total_thermal_resistance"] / 10
    )
    assert large["overall_u_value"] * large["total_r_value_si"] == (
        pytest.approx(1)
    )
    # Existing inch-pound conversion constants are rounded to six decimals.
    assert large["overall_u_value_ip"] * large["total_r_value_ip"] == (
        pytest.approx(1, rel=2e-6)
    )
    assert large["interface_temperatures"] == pytest.approx(
        small["interface_temperatures"]
    )


def test_documented_insulated_wall_and_btu_conversion():
    result = wall(
        area=10,
        interior_temperature=21,
        exterior_temperature=-5,
        layer_thicknesses=[0.2, 0.02, 0.01],
        layer_conductivities=[0.038, 0.21, 0.72],
        interior_convection_coefficient=8,
        exterior_convection_coefficient=25,
    )
    assert result["heat_transfer_rate"] == pytest.approx(46.95442002495)
    assert result["overall_u_value"] == pytest.approx(0.18059392317)
    assert result["total_r_value_si"] == pytest.approx(5.53728487886)
    assert result["total_r_value_ip"] == pytest.approx(31.44216, rel=1e-6)
    # International Table BTU = 1055.05585262 J; hour = 3600 s.
    expected_btu_per_hour = 46.95442002495 * 3600 / 1055.05585262
    assert result["heat_transfer_rate_ip"] == pytest.approx(
        expected_btu_per_hour, rel=1e-6
    )


@pytest.mark.parametrize("interior, exterior", [(0, 30), (20, 20)])
def test_reversed_and_equal_boundary_temperatures(interior, exterior):
    result = wall(
        interior_temperature=interior,
        exterior_temperature=exterior,
        interior_convection_coefficient=2,
        exterior_convection_coefficient=2,
    )
    assert result["heat_transfer_rate"] == pytest.approx(
        (interior - exterior) / 1.25
    )
    temperatures = [node["temperature_c"] for node in result["temperature_profile"]]
    assert temperatures == sorted(temperatures)
    assert temperatures[0] == pytest.approx(interior)
    assert temperatures[-1] == pytest.approx(exterior)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True])
@pytest.mark.parametrize("parameter", [
    "area", "interior_temperature", "exterior_temperature",
    "interior_convection_coefficient", "exterior_convection_coefficient",
    "layer_thicknesses", "layer_conductivities",
])
def test_rejects_nonfinite_values_and_booleans(parameter, value):
    if parameter.startswith("layer_"):
        value = [value, 0.2]
    with pytest.raises(ValueError, match="finite number"):
        wall(**{parameter: value})


@pytest.mark.parametrize("parameter", [
    "area", "interior_convection_coefficient", "exterior_convection_coefficient",
    "layer_thicknesses", "layer_conductivities",
])
@pytest.mark.parametrize("value", [0, -1])
def test_rejects_nonpositive_geometry_and_properties(parameter, value):
    if parameter.startswith("layer_"):
        value = [value, 0.2]
    with pytest.raises(ValueError, match="greater than zero"):
        wall(**{parameter: value})


def test_rejects_empty_and_mismatched_layer_lists():
    with pytest.raises(ValueError, match="At least one"):
        wall(layer_thicknesses=[], layer_conductivities=[])
    with pytest.raises(ValueError, match="same length"):
        wall(layer_thicknesses=[0.1])


@pytest.mark.parametrize("overrides", [
    {"layer_thicknesses": [1e308, 1e308]},
    {"layer_conductivities": [1e-320, 1e-320]},
    {"area": 1e-320},
    {"interior_temperature": 1e308, "exterior_temperature": -1e308},
])
def test_extreme_inputs_fail_with_clear_errors(overrides):
    with pytest.raises(ValueError, match="numeric range"):
        wall(**overrides)


def test_documentation_covers_every_returned_field():
    documentation = get_documentation("pycalcs.heat_transfer", "composite_wall_analysis")
    assert "error" not in documentation
    assert set(documentation["returns"]) == set(wall())
    assert all(documentation["returns"].values())
    assert all(math.isfinite(node["distance_m"]) for node in wall()["temperature_profile"])
