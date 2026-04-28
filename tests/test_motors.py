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

REQUIRED_DEFAULT_PARAMETERS = {
    "V_dc",
    "I_max",
    "k_e",
    "R_phase",
    "L_d",
    "L_q",
}


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

    missing_parameters = REQUIRED_DEFAULT_PARAMETERS - set(topology["default_parameters"])
    assert not missing_parameters, f"{topology_key} missing defaults {sorted(missing_parameters)}"


@pytest.mark.parametrize("topology_key, topology", motors.MOTOR_TOPOLOGIES.items())
def test_topology_tradeoff_ranges_are_complete_and_ordered(topology_key, topology):
    required_dimensions = set(motors.TRADEOFF_DIMENSIONS)
    missing = required_dimensions - set(topology["tradeoffs"])
    assert not missing, f"{topology_key} missing tradeoffs {sorted(missing)}"

    for dimension_key, range_data in topology["tradeoffs"].items():
        assert dimension_key in motors.TRADEOFF_DIMENSIONS
        for range_key in ("min", "typ", "max"):
            assert isinstance(range_data[range_key], (int, float))
        assert range_data["min"] <= range_data["typ"] <= range_data["max"]
        assert "unit" in range_data
        assert "display" in range_data


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
