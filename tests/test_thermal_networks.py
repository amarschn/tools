"""Tests for the generic thermal network solver."""

from __future__ import annotations

import math

import pytest

from pycalcs.thermal_networks import (
    generate_thermal_network_sensitivity,
    solve_thermal_network,
    validate_thermal_network_model,
)


def make_package_to_sink_model() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "template_id": "package_to_sink",
        "analysis_mode": "solve_temperatures",
        "network": {
            "id": "main_network",
            "label": "Package to sink budget",
            "notes": "",
            "nodes": [
                {
                    "id": "junction",
                    "label": "Junction",
                    "kind": "internal",
                    "heat_input_w": 25.0,
                    "fixed_temperature_c": None,
                    "max_temperature_c": 110.0,
                },
                {
                    "id": "case",
                    "label": "Case",
                    "kind": "internal",
                    "heat_input_w": 0.0,
                    "fixed_temperature_c": None,
                },
                {
                    "id": "sink",
                    "label": "Sink",
                    "kind": "internal",
                    "heat_input_w": 0.0,
                    "fixed_temperature_c": None,
                },
                {
                    "id": "ambient",
                    "label": "Ambient",
                    "kind": "boundary",
                    "heat_input_w": 0.0,
                    "fixed_temperature_c": 40.0,
                },
            ],
            "segments": [
                {
                    "id": "r_jc",
                    "label": "Junction to case",
                    "from_node_id": "junction",
                    "to_node_id": "case",
                    "category": "junction_to_case",
                    "mode": "direct",
                    "inputs": {"resistance_k_per_w": 0.4},
                },
                {
                    "id": "r_cs",
                    "label": "Case to sink interface",
                    "from_node_id": "case",
                    "to_node_id": "sink",
                    "category": "interface",
                    "mode": "direct",
                    "inputs": {"resistance_k_per_w": 0.2},
                },
                {
                    "id": "r_sa",
                    "label": "Sink to ambient",
                    "from_node_id": "sink",
                    "to_node_id": "ambient",
                    "category": "sink_to_ambient",
                    "mode": "direct",
                    "inputs": {"resistance_k_per_w": 2.0},
                },
            ],
        },
        "solve_target": None,
        "options": {},
    }


def test_validate_nominal_package_to_sink_model() -> None:
    validation = validate_thermal_network_model(make_package_to_sink_model())
    assert validation["is_valid"] is True
    assert validation["errors"] == []


def test_solve_direct_series_network() -> None:
    result = solve_thermal_network(make_package_to_sink_model())

    assert result["status"] == "acceptable"
    assert math.isclose(result["summary"]["hottest_temperature_c"], 105.0, rel_tol=1e-9)
    assert math.isclose(result["summary"]["effective_total_resistance_k_per_w"], 2.6, rel_tol=1e-9)
    assert result["summary"]["dominant_segment_id"] == "r_sa"

    nodes = {node["id"]: node for node in result["nodes"]}
    assert math.isclose(nodes["sink"]["temperature_c"], 90.0, rel_tol=1e-9)
    assert math.isclose(nodes["case"]["temperature_c"], 95.0, rel_tol=1e-9)
    assert math.isclose(nodes["junction"]["temperature_c"], 105.0, rel_tol=1e-9)


def test_tim_conductivity_mode_resolves_expected_resistance() -> None:
    model = make_package_to_sink_model()
    model["network"]["segments"][1]["mode"] = "tim_conductivity"
    model["network"]["segments"][1]["inputs"] = {
        "bondline_thickness_m": 0.0002,
        "conductivity_w_per_mk": 3.0,
        "contact_area_m2": 0.0004,
    }

    result = solve_thermal_network(model)
    segments = {segment["id"]: segment for segment in result["segments"]}
    assert math.isclose(
        segments["r_cs"]["resolved_resistance_k_per_w"],
        0.0002 / (3.0 * 0.0004),
        rel_tol=1e-9,
    )


def test_solve_required_unknown_segment() -> None:
    model = make_package_to_sink_model()
    model["analysis_mode"] = "solve_required_segment"
    model["network"]["segments"][2]["mode"] = "solved_unknown"
    model["network"]["segments"][2]["inputs"] = {
        "initial_guess_k_per_w": 1.0,
        "lower_bound_k_per_w": 0.1,
        "upper_bound_k_per_w": 5.0,
    }
    model["solve_target"] = {
        "target_node_id": "junction",
        "target_type": "max_temperature",
        "target_value_c": 110.0,
        "unknown_segment_id": "r_sa",
    }

    result = solve_thermal_network(model)
    assert result["status"] == "marginal"
    assert math.isclose(result["summary"]["sized_unknown_resistance_k_per_w"], 2.2, rel_tol=1e-5)
    assert math.isclose(result["summary"]["hottest_temperature_c"], 110.0, rel_tol=1e-6)
    assert result["diagnosis"]["required_improvement_summary"] is not None


def test_parallel_path_group_and_heat_split() -> None:
    model = {
        "schema_version": "1.0",
        "template_id": "dual_path_to_ambient",
        "analysis_mode": "solve_temperatures",
        "network": {
            "id": "dual_path",
            "label": "Dual path",
            "notes": "",
            "nodes": [
                {"id": "source", "label": "Source", "kind": "internal", "heat_input_w": 25.0},
                {"id": "case", "label": "Case", "kind": "internal", "heat_input_w": 0.0},
                {"id": "ambient", "label": "Ambient", "kind": "boundary", "heat_input_w": 0.0, "fixed_temperature_c": 40.0},
            ],
            "segments": [
                {
                    "id": "r_sc",
                    "label": "Source to case",
                    "from_node_id": "source",
                    "to_node_id": "case",
                    "category": "junction_to_case",
                    "mode": "direct",
                    "inputs": {"resistance_k_per_w": 0.2},
                },
                {
                    "id": "r_sink",
                    "label": "Case to sink path",
                    "from_node_id": "case",
                    "to_node_id": "ambient",
                    "category": "sink_to_ambient",
                    "mode": "direct",
                    "inputs": {"resistance_k_per_w": 2.0},
                },
                {
                    "id": "r_pcb",
                    "label": "Case to PCB path",
                    "from_node_id": "case",
                    "to_node_id": "ambient",
                    "category": "parallel_path",
                    "mode": "direct",
                    "inputs": {"resistance_k_per_w": 6.0},
                },
            ],
        },
        "solve_target": None,
        "options": {},
    }

    result = solve_thermal_network(model)
    assert result["parallel_groups"]
    group = result["parallel_groups"][0]
    assert math.isclose(group["equivalent_resistance_k_per_w"], 1.5, rel_tol=1e-9)
    assert math.isclose(sum(group["heat_split_w"].values()), 25.0, rel_tol=1e-9)


def test_validation_warns_on_multiple_heat_inputs() -> None:
    model = make_package_to_sink_model()
    model["network"]["nodes"][1]["heat_input_w"] = 5.0

    validation = validate_thermal_network_model(model)
    assert validation["is_valid"] is True
    assert any("Multiple heat-input nodes" in w for w in validation["warnings"])


def test_sensitivity_sweeps_selected_segment() -> None:
    result = generate_thermal_network_sensitivity(
        make_package_to_sink_model(),
        segment_ids=["r_sa"],
        variation_fraction=0.1,
        points=5,
    )

    assert len(result["series"]) == 1
    series = result["series"][0]
    assert series["segment_id"] == "r_sa"
    assert len(series["x_resistance_k_per_w"]) == 5
    assert len(series["y_hottest_temperature_c"]) == 5
    assert series["y_hottest_temperature_c"][0] < series["y_hottest_temperature_c"][-1]


def test_invalid_unknown_segment_mode_in_temperature_solve() -> None:
    model = make_package_to_sink_model()
    model["network"]["segments"][2]["mode"] = "solved_unknown"
    model["network"]["segments"][2]["inputs"] = {
        "initial_guess_k_per_w": 1.0,
    }

    validation = validate_thermal_network_model(model)
    assert validation["is_valid"] is False
    assert any("solve_required_segment" in error for error in validation["errors"])


def test_model_without_boundary_is_invalid() -> None:
    model = make_package_to_sink_model()
    model["network"]["nodes"][3]["fixed_temperature_c"] = None

    validation = validate_thermal_network_model(model)
    assert validation["is_valid"] is False
    assert any("fixed_temperature_c" in error for error in validation["errors"])


def test_sensitivity_requires_minimum_points() -> None:
    with pytest.raises(ValueError):
        generate_thermal_network_sensitivity(
            make_package_to_sink_model(),
            segment_ids=["r_sa"],
            points=2,
        )


# --- Additional coverage ---


def test_tim_area_normalized_mode() -> None:
    """Verify tim_area_normalized unit conversion: R = Z_area / (A_m2 * 1e4)."""
    model = make_package_to_sink_model()
    model["network"]["segments"][1]["mode"] = "tim_area_normalized"
    model["network"]["segments"][1]["inputs"] = {
        "impedance_k_cm2_per_w": 0.35,
        "contact_area_m2": 0.0004,
    }

    result = solve_thermal_network(model)
    segments = {s["id"]: s for s in result["segments"]}
    expected = 0.35 / (0.0004 * 10000.0)  # 0.35 / 4.0 = 0.0875
    assert math.isclose(segments["r_cs"]["resolved_resistance_k_per_w"], expected, rel_tol=1e-9)


def test_simple_conduction_slab_mode() -> None:
    """Verify R = L / (k * A) for a slab segment."""
    model = make_package_to_sink_model()
    model["network"]["segments"][1]["mode"] = "simple_conduction_slab"
    model["network"]["segments"][1]["inputs"] = {
        "thickness_m": 0.005,
        "conductivity_w_per_mk": 205.0,
        "cross_section_area_m2": 0.0009,
    }

    result = solve_thermal_network(model)
    segments = {s["id"]: s for s in result["segments"]}
    expected = 0.005 / (205.0 * 0.0009)
    assert math.isclose(segments["r_cs"]["resolved_resistance_k_per_w"], expected, rel_tol=1e-9)


def test_validation_detects_disconnected_network() -> None:
    model = make_package_to_sink_model()
    model["network"]["nodes"].append(
        {"id": "island", "label": "Island", "kind": "internal", "heat_input_w": 0.0}
    )

    validation = validate_thermal_network_model(model)
    assert validation["is_valid"] is False
    assert any("disconnected" in e.lower() for e in validation["errors"])


def test_validation_detects_duplicate_node_ids() -> None:
    model = make_package_to_sink_model()
    model["network"]["nodes"][1]["id"] = "junction"  # duplicate of node 0

    validation = validate_thermal_network_model(model)
    assert validation["is_valid"] is False
    assert any("Duplicate node id" in e for e in validation["errors"])


def test_validation_detects_duplicate_segment_ids() -> None:
    model = make_package_to_sink_model()
    model["network"]["segments"][1]["id"] = "r_jc"  # duplicate of segment 0

    validation = validate_thermal_network_model(model)
    assert validation["is_valid"] is False
    assert any("Duplicate segment id" in e for e in validation["errors"])


def test_validation_detects_nonexistent_node_reference() -> None:
    model = make_package_to_sink_model()
    model["network"]["segments"][0]["from_node_id"] = "nonexistent"

    validation = validate_thermal_network_model(model)
    assert validation["is_valid"] is False
    assert any("missing from_node_id" in e for e in validation["errors"])


def test_solve_payload_has_all_required_fields() -> None:
    result = solve_thermal_network(make_package_to_sink_model())

    # Top level
    for key in ("status", "mode", "summary", "nodes", "segments",
                "parallel_groups", "diagram_payload", "derivations",
                "warnings", "recommendations", "assumptions", "normalized_model"):
        assert key in result, f"Missing top-level key: {key}"

    # Summary
    summary = result["summary"]
    for key in ("hottest_node_id", "hottest_node_label", "hottest_temperature_c",
                "reference_node_id", "reference_temperature_c",
                "total_temperature_rise_c", "total_applied_heat_w",
                "effective_total_resistance_k_per_w",
                "dominant_segment_id", "dominant_segment_label",
                "dominant_segment_contribution_pct"):
        assert key in summary, f"Missing summary key: {key}"

    # Nodes
    for node in result["nodes"]:
        for key in ("id", "label", "kind", "temperature_c", "fixed_temperature_c",
                     "heat_input_w", "net_outgoing_heat_w", "connected_segment_ids"):
            assert key in node, f"Missing node key: {key}"

    # Segments
    for seg in result["segments"]:
        for key in ("id", "label", "from_node_id", "to_node_id", "category", "mode",
                     "resolved_resistance_k_per_w", "heat_flow_w", "delta_t_c",
                     "contribution_pct", "direction", "is_solved_unknown", "inputs",
                     "subst_resistance", "subst_delta_t"):
            assert key in seg, f"Missing segment key: {key}"

    # Derivations
    for drv in result["derivations"]:
        for key in ("id", "subject_type", "subject_id", "result_key", "title",
                     "equation_number", "equation_latex", "variable_legend",
                     "substitution_latex", "result_value", "result_units",
                     "depends_on", "step_type"):
            assert key in drv, f"Missing derivation key: {key}"


def test_derivation_equation_latex_is_not_just_lhs_symbol() -> None:
    """Regression: equation_latex must be the governing equation, not just R_theta."""
    result = solve_thermal_network(make_package_to_sink_model())
    for drv in result["derivations"]:
        if drv["step_type"] == "segment_resistance":
            # Should contain more than just a bare symbol
            assert len(drv["equation_latex"]) > 15 or "text" in drv["equation_latex"], (
                f"equation_latex too short for {drv['id']}: {drv['equation_latex']}"
            )


def test_zero_heat_input_all_nodes_equal_boundary() -> None:
    model = make_package_to_sink_model()
    model["network"]["nodes"][0]["heat_input_w"] = 0.0  # Remove heat source

    result = solve_thermal_network(model)
    for node in result["nodes"]:
        assert math.isclose(node["temperature_c"], 40.0, abs_tol=1e-9)


def test_multi_heat_source_solves_correctly() -> None:
    """After validator relaxation, multiple heat sources should solve."""
    model = make_package_to_sink_model()
    model["network"]["nodes"][0]["heat_input_w"] = 20.0  # junction
    model["network"]["nodes"][1]["heat_input_w"] = 5.0   # case

    result = solve_thermal_network(model)
    assert result["status"] != "invalid"
    nodes = {n["id"]: n for n in result["nodes"]}
    # Total heat = 25W flows through r_sa, so T_sink = 40 + 25*2.0 = 90
    assert math.isclose(nodes["sink"]["temperature_c"], 90.0, rel_tol=1e-9)
    # Case: 5W injected at case, 20W flows through r_jc, so 25W total
    # T_case = 90 + 25*0.2 = 95? No - 25W flows through r_cs, so T_case = 90 + 25*0.2 = 95
    assert math.isclose(nodes["case"]["temperature_c"], 95.0, rel_tol=1e-9)
    # Junction: 20W enters, all flows to case. T_junction = 95 + 20*0.4 = 103
    assert math.isclose(nodes["junction"]["temperature_c"], 103.0, rel_tol=1e-9)
