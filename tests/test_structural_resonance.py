"""Reference frequencies and physical invariants for thin plates and free rings."""

import math

import pytest

from pycalcs.structural_resonance import MATERIALS, calculate_structural_resonance
from pycalcs.utils import get_documentation


def calculate(**overrides):
    """Return a selected mode, defaulting to a 1 m square steel plate."""
    parameters = {
        "geometry_type": "plate", "thickness_mm": 10.0,
        "length_mm": 1000.0, "width_mm": 1000.0, "diameter_mm": 1000.0,
        "mode_1": 1, "mode_2": 1, "material": "steel",
    }
    return calculate_structural_resonance(**(parameters | overrides))


def ring(**overrides):
    """Return a free-ring bending mode, allowing per-test overrides."""
    return calculate(**({"geometry_type": "cylinder", "mode_2": 2} | overrides))


def test_square_plate_reference_frequency_parameter():
    """Leissa NASA SP-160 Ch. 4: fundamental omega*a²*sqrt(rho*h/D)=2*pi²."""
    result = calculate()
    assert result["natural_frequency_hz"] == pytest.approx(47.98646111714)
    nondimensional = (
        2 * math.pi * result["natural_frequency_hz"]
        * math.sqrt(7850 * 0.01 / result["flexural_rigidity_n_m"])
    )
    assert nondimensional == pytest.approx(2 * math.pi**2)
    assert result["geometry_display"] == "Rectangular Plate, Mode (1,1)"


@pytest.mark.parametrize("mode, expected_hz", [
    (0, 1702.351), (2, 20.713), (3, 58.585), (4, 112.332),
])
def test_nasa_free_ring_reference_table(mode, expected_hz):
    """NASA/CR-2006-214281 pp. 40-41, radial and in-plane flexural tables.

    E=10 Msi, mean radius=20/pi inches, radial thickness=0.1 inch;
    weight density=5/6 lbf/in³ and reference gravity=386.4 in/s².
    Convert weight density to mass density using the reference gravity, not
    standard gravity, to reproduce the published benchmark's conventions.
    """
    inch_m = 0.0254
    lbf_n = 4.4482216152605
    density = ((5 / 6) * lbf_n / inch_m**3) / (386.4 * inch_m)
    result = ring(
        thickness_mm=2.54,
        diameter_mm=(40 / math.pi) * 25.4,
        mode_2=mode,
        material="custom",
        custom_e_gpa=10e6 * lbf_n / inch_m**2 / 1e9,
        custom_rho_kg_m3=density,
        custom_nu=0,
    )
    assert result["natural_frequency_hz"] == pytest.approx(expected_hz, abs=0.00051)


def test_ring_ovaling_excludes_plate_poisson_stiffening():
    result = ring(
        thickness_mm=2, diameter_mm=100, material="aluminum", mode_2=2
    )
    assert result["natural_frequency_hz"] == pytest.approx(498.5725997310)
    assert result["flexural_rigidity_n_m"] == pytest.approx(46)
    assert "EI/b" in result["stiffness_label"]


def test_free_ring_is_independent_of_poisson_ratio():
    for mode in (0, 2, 4):
        low_nu = ring(material="custom", mode_2=mode, custom_nu=-0.4)
        high_nu = ring(material="custom", mode_2=mode, custom_nu=0.49)
        assert high_nu["natural_frequency_hz"] == low_nu["natural_frequency_hz"]
        assert high_nu["flexural_rigidity_n_m"] == low_nu["flexural_rigidity_n_m"]


def test_plate_axis_exchange_and_square_mode_ratio():
    first = calculate(length_mm=300, width_mm=200, mode_1=2, mode_2=3)
    swapped = calculate(length_mm=200, width_mm=300, mode_1=3, mode_2=2)
    assert first["natural_frequency_hz"] == swapped["natural_frequency_hz"]
    fundamental = calculate()["natural_frequency_hz"]
    assert calculate(mode_1=2)["natural_frequency_hz"] == pytest.approx(
        2.5 * fundamental
    )


def test_geometry_scaling():
    fundamental = calculate()["natural_frequency_hz"]
    assert calculate(thickness_mm=20)["natural_frequency_hz"] == pytest.approx(
        2 * fundamental
    )
    assert calculate(length_mm=2000, width_mm=2000)["natural_frequency_hz"] == (
        pytest.approx(fundamental / 4)
    )
    ring_frequency = ring()["natural_frequency_hz"]
    assert ring(thickness_mm=20)["natural_frequency_hz"] == pytest.approx(
        2 * ring_frequency
    )
    assert ring(diameter_mm=2000)["natural_frequency_hz"] == pytest.approx(
        ring_frequency / 4
    )
    breathing = ring(mode_2=0)["natural_frequency_hz"]
    assert ring(mode_2=0, thickness_mm=20)["natural_frequency_hz"] == breathing
    assert ring(mode_2=0, diameter_mm=2000)["natural_frequency_hz"] == (
        pytest.approx(breathing / 2)
    )


@pytest.mark.parametrize("material", list(MATERIALS))
def test_preset_matches_explicit_custom_properties(material):
    properties = MATERIALS[material]
    preset = calculate(material=material)
    custom = calculate(
        material="custom", custom_e_gpa=properties["elastic_modulus_gpa"],
        custom_rho_kg_m3=properties["density_kg_m3"],
        custom_nu=properties["poisson_ratio"],
    )
    for key in (
        "natural_frequency_hz", "flexural_rigidity_n_m", "wave_velocity_m_s",
        "elastic_modulus_gpa", "density_kg_m3", "poisson_ratio",
    ):
        assert preset[key] == custom[key]


def test_material_scaling_and_auxetic_plate():
    baseline = calculate(material="custom")["natural_frequency_hz"]
    assert calculate(material="custom", custom_e_gpa=800)["natural_frequency_hz"] == (
        pytest.approx(2 * baseline)
    )
    assert calculate(material="custom", custom_rho_kg_m3=31400)["natural_frequency_hz"] == (
        pytest.approx(baseline / 2)
    )
    assert calculate(material="custom", custom_nu=-0.3)["natural_frequency_hz"] == (
        pytest.approx(baseline)
    )


@pytest.mark.parametrize("bad", [0, -1, 1.5, float("nan"), float("inf"), True])
@pytest.mark.parametrize("parameter", ["mode_1", "mode_2"])
def test_rejects_invalid_plate_modes_without_coercion(parameter, bad):
    with pytest.raises(ValueError):
        calculate(**{parameter: bad})


@pytest.mark.parametrize("bad", [-1, 1, 2.9, float("nan"), float("inf"), True])
def test_rejects_invalid_ring_modes_without_coercion(bad):
    with pytest.raises(ValueError):
        ring(mode_2=bad)


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), True])
@pytest.mark.parametrize("parameter", ["thickness_mm", "length_mm", "width_mm"])
def test_rejects_invalid_plate_dimensions(parameter, bad):
    with pytest.raises(ValueError):
        calculate(**{parameter: bad})


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), True])
def test_rejects_invalid_ring_diameter(bad):
    with pytest.raises(ValueError):
        ring(diameter_mm=bad)


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), True])
@pytest.mark.parametrize("parameter", ["custom_e_gpa", "custom_rho_kg_m3"])
def test_rejects_invalid_custom_modulus_and_density(parameter, bad):
    with pytest.raises(ValueError):
        calculate(material="custom", **{parameter: bad})


@pytest.mark.parametrize("bad", [-1, -2, 0.5, 1, float("nan"), float("inf"), True])
def test_rejects_invalid_poisson_ratio(bad):
    with pytest.raises(ValueError):
        calculate(material="custom", custom_nu=bad)


def test_inactive_fields_are_ignored():
    assert calculate(diameter_mm=float("nan"))["natural_frequency_hz"] == (
        calculate()["natural_frequency_hz"]
    )
    assert ring(length_mm=None, width_mm=-10, mode_1="unused")["natural_frequency_hz"] == (
        ring()["natural_frequency_hz"]
    )
    assert calculate(custom_e_gpa=None, custom_rho_kg_m3=-1, custom_nu=float("nan"))[
        "natural_frequency_hz"
    ] == calculate()["natural_frequency_hz"]


@pytest.mark.parametrize("thickness", [1000, 1001])
def test_ring_requires_positive_inner_diameter(thickness):
    with pytest.raises(ValueError, match="inner diameter is positive"):
        ring(thickness_mm=thickness, diameter_mm=1000)


@pytest.mark.parametrize("overrides", [
    {"thickness_mm": 1e308}, {"length_mm": 1e-308},
    {"material": "custom", "custom_e_gpa": 1e308},
    {"material": "custom", "custom_rho_kg_m3": 1e-308},
    {"mode_1": 1e308}, {"thickness_mm": 5e-324},
])
def test_extreme_inputs_return_clear_errors(overrides):
    with pytest.raises(ValueError, match="numeric range"):
        calculate(**overrides)


@pytest.mark.parametrize("overrides", [{"geometry_type": "cone"}, {"material": "unknown"}])
def test_unknown_model_or_material(overrides):
    with pytest.raises(ValueError):
        calculate(**overrides)


def test_return_documentation_and_numerical_substitutions():
    docs = get_documentation("pycalcs.structural_resonance", "calculate_structural_resonance")
    assert "error" not in docs
    assert set(docs["returns"]) == set(calculate())
    assert all(docs["returns"].values())
    assert all("=" in equation for equation in docs["latex"].splitlines())
    assert docs["symbols"] and docs["references"]
    for result in (calculate(), ring(), ring(mode_2=0)):
        assert result["model_assumptions"] and result["applicability_notes"]
        assert result["thickness_ratio"] > 0
        equation = result["subst_natural_frequency_hz"]
        assert "e+" not in equation and "e-" not in equation
        assert "\\rho" not in equation
        assert "Hz" in equation
