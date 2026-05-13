"""Tests for motor topology educational data."""

import pytest

from pycalcs import motors
from pycalcs.utils import get_documentation


REQUIRED_TOPOLOGY_KEYS = {
    "name",
    "short_name",
    "family",
    "one_sentence",
    "description",
    "distinguishing_facts",
    "applications",
    "pros",
    "cons",
    "applicable_control_methods",
    "default_parameters",
    "tradeoffs",
    "references",
}

VALID_POLARITIES = {"higher_better", "lower_better", "context"}


def test_initial_topology_database_contains_step_one_scope():
    assert set(motors.MOTOR_TOPOLOGIES) == {
        "pmsm_spm",
        "induction_squirrel_cage",
        "dc_brushed_pm",
    }


@pytest.mark.parametrize("topology_key, topology", motors.MOTOR_TOPOLOGIES.items())
def test_topology_entries_have_required_fields(topology_key, topology):
    missing = REQUIRED_TOPOLOGY_KEYS - set(topology)
    assert not missing, f"{topology_key} missing {sorted(missing)}"

    for field in (
        "distinguishing_facts",
        "applications",
        "pros",
        "cons",
        "applicable_control_methods",
        "references",
    ):
        assert topology[field], f"{topology_key}.{field} must not be empty"

    # default_parameters is intentionally per-topology and may carry different
    # keys for each motor family (PMSM uses k_e/L_d/L_q; induction will need
    # L_m/R_r; reluctance will need saliency ratio). Just check the dict is
    # non-empty so step 2 can introduce topology-specific schemas without
    # rewriting this test.
    assert isinstance(topology["default_parameters"], dict)
    assert topology["default_parameters"], (
        f"{topology_key}.default_parameters must not be empty"
    )


@pytest.mark.parametrize("topology_key, topology", motors.MOTOR_TOPOLOGIES.items())
def test_topology_tradeoff_ranges_are_complete_and_ordered(topology_key, topology):
    required_dimensions = set(motors.TRADEOFF_DIMENSIONS)
    missing = required_dimensions - set(topology["tradeoffs"])
    assert not missing, f"{topology_key} missing tradeoffs {sorted(missing)}"

    for dimension_key, range_data in topology["tradeoffs"].items():
        assert dimension_key in motors.TRADEOFF_DIMENSIONS
        assert "unit" in range_data
        assert "display" in range_data

        if range_data.get("not_applicable"):
            for range_key in ("min", "typ", "max"):
                assert range_data[range_key] is None, (
                    f"{topology_key}.{dimension_key} flagged not_applicable but "
                    f"has a value in {range_key}"
                )
            continue

        for range_key in ("min", "typ", "max"):
            assert isinstance(range_data[range_key], (int, float)), (
                f"{topology_key}.{dimension_key}.{range_key} must be numeric "
                f"unless not_applicable=True"
            )
        assert range_data["min"] <= range_data["typ"] <= range_data["max"]


@pytest.mark.parametrize("dimension_key, dimension", motors.TRADEOFF_DIMENSIONS.items())
def test_tradeoff_dimension_has_polarity(dimension_key, dimension):
    assert "polarity" in dimension, f"{dimension_key} missing polarity"
    assert dimension["polarity"] in VALID_POLARITIES, (
        f"{dimension_key}.polarity={dimension['polarity']!r} not in {VALID_POLARITIES}"
    )


@pytest.mark.parametrize("dimension_key, dimension", motors.TRADEOFF_DIMENSIONS.items())
def test_ordinal_dimensions_carry_a_decoder_scale(dimension_key, dimension):
    if dimension["kind"] != "ordinal":
        return
    scale = dimension.get("scale")
    assert isinstance(scale, dict) and scale, (
        f"ordinal dimension {dimension_key} must define a non-empty scale dict"
    )
    for code, label in scale.items():
        assert isinstance(code, int), f"{dimension_key}.scale keys must be int (got {code!r})"
        assert isinstance(label, str) and label, (
            f"{dimension_key}.scale[{code}] must be a non-empty string"
        )


@pytest.mark.parametrize("topology_key, topology", motors.MOTOR_TOPOLOGIES.items())
def test_ordinal_typ_values_lie_within_their_scale(topology_key, topology):
    for dimension_key, range_data in topology["tradeoffs"].items():
        dimension = motors.TRADEOFF_DIMENSIONS[dimension_key]
        if dimension["kind"] != "ordinal" or range_data.get("not_applicable"):
            continue
        scale = dimension["scale"]
        valid_codes = set(scale)
        for range_key in ("min", "typ", "max"):
            value = range_data[range_key]
            assert int(value) == value, (
                f"{topology_key}.{dimension_key}.{range_key}={value!r} must be an integer code"
            )
            assert int(value) in valid_codes, (
                f"{topology_key}.{dimension_key}.{range_key}={int(value)} "
                f"not in scale codes {sorted(valid_codes)}"
            )


def test_calculate_topology_overview_returns_defensive_copy():
    overview = motors.calculate_topology_overview("pmsm_spm")
    overview["tradeoffs"]["peak_efficiency_percent"]["typ"] = -1.0

    fresh = motors.calculate_topology_overview("pmsm_spm")
    assert fresh["topology_key"] == "pmsm_spm"
    assert fresh["tradeoffs"]["peak_efficiency_percent"]["typ"] == 92.0


def test_calculate_topology_overview_rejects_unknown_topology():
    with pytest.raises(ValueError, match="Unknown motor topology"):
        motors.calculate_topology_overview("flux_capacitor_motor")


def test_calculate_topology_overview_docstring_parses_for_ui_tooltips():
    docs = get_documentation("pycalcs.motors", "calculate_topology_overview")

    assert "error" not in docs
    assert "topology" in docs["parameters"]
    for return_key in (
        "topology_key",
        "name",
        "tradeoffs",
        "references",
    ):
        assert return_key in docs["returns"]
