"""Reference frequencies and physical invariants for thin plates and free rings."""

import math

import pytest

from pycalcs.structural_resonance import (
    BEAM_ROOTS, MATERIALS, _beam_mode_value, calculate_beam_resonance,
    calculate_structural_resonance,
)
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


def test_default_beam_frequency_and_section_properties():
    """Georgia Tech cantilever root 1.875104... with Al 300×25×5 mm beam."""
    result = calculate_beam_resonance()
    assert result["section_area_m2"] == pytest.approx(1.25e-4)
    assert result["second_moment_m4"] == pytest.approx(2.604166666666667e-10)
    assert result["mass_per_length_kg_m"] == pytest.approx(0.3375)
    assert result["beam_mass_kg"] == pytest.approx(0.10125)
    assert result["natural_frequency_hz"] == pytest.approx(45.3680819916)
    assert [item["natural_frequency_hz"] for item in result["mode_frequencies"]] == (
        pytest.approx([45.3680819916, 284.316916626, 796.095599255,
                       1560.02964195, 2578.84077762])
    )


@pytest.mark.parametrize("support", list(BEAM_ROOTS))
def test_beam_roots_and_selected_spectrum_entry(support):
    for number, eigenvalue in enumerate(BEAM_ROOTS[support], 1):
        if support == "simply_supported":
            assert eigenvalue == pytest.approx(number * math.pi)
        else:
            rhs = -1 if support == "cantilever" else 1
            # Stable equivalent of cos(lambda)*cosh(lambda)=+/-1.
            assert math.cos(eigenvalue) - rhs / math.cosh(eigenvalue) == (
                pytest.approx(0, abs=3e-15)
            )
        result = calculate_beam_resonance(support_type=support, mode_number=number)
        assert result["natural_frequency_hz"] == result["mode_frequencies"][number - 1][
            "natural_frequency_hz"
        ]
        assert result["eigenvalue"] == eigenvalue


@pytest.mark.parametrize("support", list(BEAM_ROOTS))
def test_beam_shapes_satisfy_analytical_boundary_conditions(support):
    """Displacement/slope at clamps; moment/shear at free ends, not fitted curves."""
    for root in BEAM_ROOTS[support]:
        if support == "cantilever":
            boundaries = [(0, 0), (0, 1), (1, 2), (1, 3)]
        elif support == "fixed_fixed":
            boundaries = [(0, 0), (0, 1), (1, 0), (1, 1)]
        else:
            boundaries = [(0, 0), (0, 2), (1, 0), (1, 2)]
        for x, derivative in boundaries:
            value = _beam_mode_value(support, root, x, derivative) / root**derivative
            assert value == pytest.approx(0, abs=2e-8)


@pytest.mark.parametrize("support", list(BEAM_ROOTS))
@pytest.mark.parametrize("mode", range(1, 6))
def test_beam_diagram_normalization_and_internal_node_count(support, mode):
    diagram = calculate_beam_resonance(support_type=support, mode_number=mode)[
        "diagram_data"
    ]
    x, shape = diagram["x"], diagram["displacement"]
    assert len(x) == len(shape) == 201
    assert x[0] == 0 and x[-1] == 1
    assert max(abs(value) for value in shape) == pytest.approx(1)
    assert shape[0] == 0
    if support != "cantilever":
        assert shape[-1] == 0
    nonzero = [value for value in shape if abs(value) > 1e-8]
    crossings = sum(left * right < 0 for left, right in zip(nonzero, nonzero[1:]))
    assert crossings == mode - 1


def test_beam_scaling_support_and_bending_direction():
    baseline = calculate_beam_resonance()["natural_frequency_hz"]
    assert calculate_beam_resonance(length_mm=600)["natural_frequency_hz"] == (
        pytest.approx(baseline / 4)
    )
    assert calculate_beam_resonance(depth_mm=10)["natural_frequency_hz"] == (
        pytest.approx(2 * baseline)
    )
    assert calculate_beam_resonance(width_mm=50)["natural_frequency_hz"] == (
        pytest.approx(baseline)
    )
    assert calculate_beam_resonance(bending_axis="width")["natural_frequency_hz"] == (
        pytest.approx(5 * baseline)
    )
    pinned = calculate_beam_resonance(support_type="simply_supported")
    fundamental = pinned["natural_frequency_hz"]
    assert [row["natural_frequency_hz"] / fundamental for row in pinned["mode_frequencies"]] == (
        pytest.approx([1, 4, 9, 16, 25])
    )
    fixed = calculate_beam_resonance(support_type="fixed_fixed")["natural_frequency_hz"]
    assert fixed > fundamental > baseline


@pytest.mark.parametrize("section, overrides, area, inertia", [
    ("rectangular", {"width_mm": 20, "depth_mm": 10}, 200e-6, 1666.6666666667e-12),
    ("box", {"width_mm": 40, "depth_mm": 20, "wall_thickness_mm": 2},
     224e-6, 14378.6666666667e-12),
    ("circular_solid", {"outer_diameter_mm": 10}, math.pi * 25e-6, math.pi * 156.25e-12),
    ("circular_hollow", {"outer_diameter_mm": 10, "wall_thickness_mm": 1},
     math.pi * 9e-6, math.pi * 92.25e-12),
])
def test_beam_section_geometry(section, overrides, area, inertia):
    result = calculate_beam_resonance(section_type=section, **overrides)
    assert result["section_area_m2"] == pytest.approx(area)
    assert result["second_moment_m4"] == pytest.approx(inertia)


def test_beam_box_axis_swap_and_circle_symmetry():
    arguments = dict(section_type="box", width_mm=40, depth_mm=20, wall_thickness_mm=2)
    turned = calculate_beam_resonance(**arguments, bending_axis="width")
    exchanged = calculate_beam_resonance(**(arguments | {"width_mm": 20, "depth_mm": 40}))
    assert turned["natural_frequency_hz"] == exchanged["natural_frequency_hz"]
    for section in ("circular_solid", "circular_hollow"):
        depth = calculate_beam_resonance(section_type=section)
        width = calculate_beam_resonance(section_type=section, bending_axis="width")
        assert depth["natural_frequency_hz"] == width["natural_frequency_hz"]


@pytest.mark.parametrize("overrides", [
    {"length_mm": 0}, {"length_mm": float("nan")}, {"depth_mm": float("inf")},
    {"width_mm": True}, {"depth_mm": -1}, {"mode_number": 0},
    {"mode_number": 6}, {"mode_number": 1.5}, {"mode_number": True},
    {"support_type": "free"}, {"section_type": "i_beam"}, {"bending_axis": "invalid"},
    {"section_type": "box", "wall_thickness_mm": 3},
    {"section_type": "circular_hollow", "wall_thickness_mm": 5},
    {"section_type": "circular_hollow", "wall_thickness_mm": float("nan")},
    {"section_type": "circular_solid", "outer_diameter_mm": 0},
    {"material": "custom", "custom_e_gpa": float("inf")},
    {"material": "custom", "custom_rho_kg_m3": 0},
])
def test_beam_invalid_active_inputs(overrides):
    with pytest.raises(ValueError):
        calculate_beam_resonance(**overrides)


def test_beam_ignored_inputs_and_custom_material():
    default = calculate_beam_resonance()
    inactive = calculate_beam_resonance(
        outer_diameter_mm=None, wall_thickness_mm=float("nan"), custom_e_gpa=-1,
    )
    assert inactive["natural_frequency_hz"] == default["natural_frequency_hz"]
    circle = calculate_beam_resonance(
        section_type="circular_solid", width_mm=None, depth_mm=-1,
        bending_axis="ignored", wall_thickness_mm=float("nan"),
    )
    assert circle["natural_frequency_hz"] > 0
    custom = calculate_beam_resonance(
        material="custom", custom_e_gpa=69, custom_rho_kg_m3=2700, custom_nu=-0.2,
    )
    assert custom["natural_frequency_hz"] == default["natural_frequency_hz"]


@pytest.mark.parametrize("overrides", [
    {"length_mm": 5e-324}, {"width_mm": 1e308, "depth_mm": 1e100}, {"depth_mm": 1e308},
    {"material": "custom", "custom_e_gpa": 1e308}, {"length_mm": 1e-200},
])
def test_beam_extreme_inputs_fail_cleanly(overrides):
    with pytest.raises(ValueError):
        calculate_beam_resonance(**overrides)


def test_beam_documentation_matches_results():
    docs = get_documentation("pycalcs.structural_resonance", "calculate_beam_resonance")
    assert set(docs["returns"]) == set(calculate_beam_resonance())
    assert all(docs["returns"].values())
    assert docs["references"] and docs["symbols"]


def test_plate_mode_grid_boundary_nodes_and_signs():
    diagram = calculate(mode_1=2, mode_2=3)["diagram_data"]
    assert diagram["kind"] == "plate" and diagram["available"]
    x, y, grid = diagram["x"], diagram["y"], diagram["displacement"]
    assert len(grid) == len(y) and all(len(row) == len(x) for row in grid)
    assert max(abs(value) for row in grid for value in row) == pytest.approx(1)
    for row in grid:
        assert row[0] == pytest.approx(0, abs=1e-14)
        assert row[-1] == pytest.approx(0, abs=1e-14)
        assert row[x.index(0.5)] == pytest.approx(0, abs=1e-14)
    assert grid[0] == pytest.approx([0] * len(x), abs=1e-14)
    assert grid[-1] == pytest.approx([0] * len(x), abs=1e-14)
    assert grid[y.index(1 / 6)][x.index(0.25)] == pytest.approx(1)
    assert grid[y.index(1 / 6)][x.index(0.75)] == pytest.approx(-1)


def test_ring_bending_tangential_displacement_preserves_inextensionality():
    diagram = ring(mode_2=2)["diagram_data"]
    theta, radial, tangent = diagram["theta"], diagram["radial"], diagram["tangential"]
    assert radial[0] == radial[-1] == pytest.approx(1)
    assert tangent[0] == pytest.approx(tangent[-1], abs=1e-14)
    quarter_lobe = len(theta) // 8
    assert radial[quarter_lobe] == pytest.approx(0, abs=1e-14)
    assert tangent[quarter_lobe] == pytest.approx(-0.5)
    step = theta[1] - theta[0]
    for i in range(1, len(theta) - 1):
        tangent_derivative = (tangent[i + 1] - tangent[i - 1]) / (2 * step)
        assert tangent_derivative + radial[i] == pytest.approx(0, abs=0.002)
    breathing = ring(mode_2=0)["diagram_data"]
    assert all(value == 1 for value in breathing["radial"])
    assert all(value == 0 for value in breathing["tangential"])


def test_unresolvable_diagram_modes_keep_geometry_and_frequency():
    plate = calculate(mode_1=13)
    ring_result = ring(mode_2=33)
    for result in (plate, ring_result):
        assert result["natural_frequency_hz"] > 0
        diagram = result["diagram_data"]
        assert not diagram["available"] and diagram["reason"]
        assert diagram["geometry"]
        assert "displacement" not in diagram and "radial" not in diagram
