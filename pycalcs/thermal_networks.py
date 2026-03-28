"""Generic steady-state thermal network helpers and solver."""

from __future__ import annotations

from typing import Any

import math


MVP_TEMPLATE_IDS = {
    "simple_chain",
    "package_to_sink",
    "housing_wall_path",
    "dual_path_to_ambient",
    "custom",
}

ALLOWED_ANALYSIS_MODES = {
    "solve_temperatures",
    "solve_required_segment",
}

ALLOWED_SEGMENT_MODES = {
    "direct",
    "tim_area_normalized",
    "tim_conductivity",
    "simple_conduction_slab",
    "solved_unknown",
}


def validate_thermal_network_model(model: dict[str, object]) -> dict[str, object]:
    """
    Validate and normalize a canonical thermal resistance network model.

    The model represents a steady-state thermal network with one positive heat
    source and one fixed-temperature boundary in the MVP. Validation checks the
    graph structure, the segment definitions, and the solve-mode-specific
    constraints before the solver is called.

    ---Parameters---
    model : dict[str, object]
        Canonical thermal-network model using the schema described in the
        thermal path budget tool spec. The dictionary must contain the keys
        ``schema_version``, ``template_id``, ``analysis_mode``, and ``network``.

    ---Returns---
    is_valid : bool
        ``True`` when the model is solvable under the MVP contract.
    errors : list[str]
        Hard validation errors that should prevent solving.
    warnings : list[str]
        Non-fatal cautions about model fit or reporting assumptions.
    normalized_model : dict[str, object]
        Normalized copy of the model with defaults filled in and numeric values
        coerced to floats where practical.

    ---LaTeX---
    Q_{ij} = \\frac{T_i - T_j}{R_{ij}}
    """
    errors: list[str] = []
    warnings: list[str] = []

    normalized = _normalize_model(model, errors)
    if not normalized:
        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "normalized_model": {},
        }

    template_id = normalized["template_id"]
    analysis_mode = normalized["analysis_mode"]
    network = normalized["network"]
    nodes: list[dict[str, Any]] = network["nodes"]
    segments: list[dict[str, Any]] = network["segments"]

    if template_id not in MVP_TEMPLATE_IDS:
        errors.append(f"Unknown template_id '{template_id}' for the supported MVP template library.")

    if analysis_mode not in ALLOWED_ANALYSIS_MODES:
        errors.append(
            f"Unsupported analysis_mode '{analysis_mode}'. "
            f"Valid modes: {sorted(ALLOWED_ANALYSIS_MODES)}."
        )

    node_ids: set[str] = set()
    fixed_temperature_nodes: list[str] = []
    positive_heat_nodes: list[str] = []

    for node in nodes:
        node_id = node["id"]
        if node_id in node_ids:
            errors.append(f"Duplicate node id '{node_id}'.")
        node_ids.add(node_id)

        fixed_temperature_c = node["fixed_temperature_c"]
        if fixed_temperature_c is not None:
            fixed_temperature_nodes.append(node_id)

        heat_input_w = node["heat_input_w"]
        if heat_input_w > 0.0:
            positive_heat_nodes.append(node_id)

        if node["kind"] == "boundary" and fixed_temperature_c is None:
            warnings.append(
                f"Boundary node '{node_id}' has no fixed temperature and will be solved as an internal node."
            )
        if node["kind"] == "internal" and fixed_temperature_c is not None:
            warnings.append(
                f"Internal node '{node_id}' has a fixed temperature and behaves like a boundary."
            )

    if len(fixed_temperature_nodes) == 0:
        errors.append("At least one node must define fixed_temperature_c.")
    if len(fixed_temperature_nodes) > 1:
        warnings.append("Multiple fixed-temperature boundary nodes defined; the solver handles this but headline metrics assume a single reference.")
    if len(positive_heat_nodes) == 0:
        warnings.append("No positive heat_input_w node defined; all node temperatures will equal the boundary temperature.")
    if len(positive_heat_nodes) > 1:
        warnings.append("Multiple heat-input nodes defined; the solver handles this but effective total resistance is an aggregate, not a single-path value.")

    segment_ids: set[str] = set()
    solved_unknown_ids: list[str] = []
    adjacency: dict[str, set[str]] = {node["id"]: set() for node in nodes}

    for segment in segments:
        segment_id = segment["id"]
        if segment_id in segment_ids:
            errors.append(f"Duplicate segment id '{segment_id}'.")
        segment_ids.add(segment_id)

        from_node_id = segment["from_node_id"]
        to_node_id = segment["to_node_id"]

        if from_node_id == to_node_id:
            errors.append(f"Segment '{segment_id}' cannot connect a node to itself.")

        if from_node_id not in node_ids:
            errors.append(
                f"Segment '{segment_id}' references missing from_node_id '{from_node_id}'."
            )
        if to_node_id not in node_ids:
            errors.append(
                f"Segment '{segment_id}' references missing to_node_id '{to_node_id}'."
            )

        if from_node_id in adjacency and to_node_id in adjacency:
            adjacency[from_node_id].add(to_node_id)
            adjacency[to_node_id].add(from_node_id)

        mode = segment["mode"]
        if mode not in ALLOWED_SEGMENT_MODES:
            errors.append(
                f"Segment '{segment_id}' uses unsupported mode '{mode}'. "
                f"Valid modes: {sorted(ALLOWED_SEGMENT_MODES)}."
            )
            continue

        if mode == "solved_unknown":
            solved_unknown_ids.append(segment_id)
        else:
            try:
                _resolve_segment_resistance(segment, solved_unknown_overrides={})
            except ValueError as exc:
                errors.append(f"Segment '{segment_id}': {exc}")

        if mode == "simple_conduction_slab":
            warnings.append(
                f"Segment '{segment_id}' uses a 1D conduction slab; verify that spreading is not the dominant effect."
            )

    if nodes and segments and not errors and not _is_connected(adjacency, nodes[0]["id"]):
        errors.append("The network is disconnected.")

    if analysis_mode == "solve_temperatures":
        if solved_unknown_ids:
            errors.append(
                "Segments using mode 'solved_unknown' require analysis_mode='solve_required_segment'."
            )
    elif analysis_mode == "solve_required_segment":
        solve_target = normalized["solve_target"]
        if len(solved_unknown_ids) != 1:
            errors.append("Exactly one segment must use mode 'solved_unknown' in solve_required_segment mode.")
        if not solve_target:
            errors.append("solve_target is required in solve_required_segment mode.")
        else:
            target_node_id = solve_target.get("target_node_id")
            target_type = solve_target.get("target_type")
            unknown_segment_id = solve_target.get("unknown_segment_id")

            if target_node_id not in node_ids:
                errors.append("solve_target.target_node_id must reference an existing node.")
            if target_type != "max_temperature":
                errors.append("The MVP supports solve_target.target_type='max_temperature' only.")
            if unknown_segment_id not in segment_ids:
                errors.append("solve_target.unknown_segment_id must reference an existing segment.")
            if solved_unknown_ids and unknown_segment_id not in solved_unknown_ids:
                errors.append(
                    "solve_target.unknown_segment_id must match the only segment using mode 'solved_unknown'."
                )
            try:
                _coerce_float(solve_target.get("target_value_c"), "solve_target.target_value_c")
            except ValueError as exc:
                errors.append(str(exc))

    if not any(node["max_temperature_c"] is not None for node in nodes):
        warnings.append("No node temperature limits are defined; status will be informational only.")

    if template_id == "custom":
        warnings.append("Custom topology used where a standard template may be clearer.")

    if not segments:
        errors.append("At least one segment is required.")
    if not nodes:
        errors.append("At least one node is required.")

    return {
        "is_valid": not errors,
        "errors": errors,
        "warnings": _dedupe_strings(warnings),
        "normalized_model": normalized,
    }


def solve_thermal_network(model: dict[str, object]) -> dict[str, object]:
    """
    Solve a steady-state thermal resistance network and build a render-ready payload.

    The solver normalizes the input model, resolves every segment into a scalar
    thermal resistance, solves the nodal temperatures using steady-state energy
    balance, and returns a single payload for summary cards, diagnosis,
    derivations, the network diagram, and export.

    ---Parameters---
    model : dict[str, object]
        Canonical thermal-network model. The model may be in
        ``solve_temperatures`` mode or ``solve_required_segment`` mode.

    ---Returns---
    status : str
        Overall solve outcome: ``acceptable``, ``marginal``, ``unacceptable``,
        or ``invalid``.
    mode : str
        Echo of the analysis mode used for the solve.
    summary : dict[str, object]
        Headline results including hottest node, total rise, effective thermal
        resistance, dominant segment, and limit margin.
    diagnosis : dict[str, object]
        Action-oriented interpretation of the dominant bottleneck and the first
        improvement target.
    applicability : dict[str, object]
        Model-fit assessment with caution flags and optional routing guidance.
    reporting_basis : dict[str, object]
        Explicit conventions used by headline values and contribution metrics.
    nodes : list[dict[str, object]]
        Solved node payload for the UI and export.
    segments : list[dict[str, object]]
        Solved segment payload with resolved resistance, heat flow, and
        substituted equations.
    parallel_groups : list[dict[str, object]]
        Parallel branch summaries where multiple segments share the same entry
        and exit nodes.
    diagram_payload : dict[str, object]
        Graph data for frontend rendering.
    derivations : list[dict[str, object]]
        Canonical derivation objects linked to summary items, segments, and
        parallel groups.
    warnings : list[str]
        Non-fatal cautions from validation and solve-time interpretation.
    recommendations : list[str]
        Short suggested actions based on the dominant bottleneck.
    assumptions : list[str]
        Explicit modeling assumptions used by the solve.
    normalized_model : dict[str, object]
        Normalized copy of the input model ready for export/debugging.

    ---LaTeX---
    \\sum_j \\frac{T_i - T_j}{R_{ij}} = Q_i
    """
    validation = validate_thermal_network_model(model)
    normalized = validation["normalized_model"]

    if not validation["is_valid"]:
        return {
            "status": "invalid",
            "mode": normalized.get("analysis_mode", "invalid"),
            "summary": {},
            "diagnosis": {},
            "applicability": {
                "status": "better_in_other_tool",
                "score_label": "Invalid model",
                "flags": validation["errors"],
                "routing_suggestion": None,
            },
            "reporting_basis": {},
            "nodes": [],
            "segments": [],
            "parallel_groups": [],
            "diagram_payload": {},
            "derivations": [],
            "warnings": validation["warnings"],
            "recommendations": [],
            "assumptions": [],
            "normalized_model": normalized,
            "errors": validation["errors"],
        }

    solve_target = normalized.get("solve_target")
    if normalized["analysis_mode"] == "solve_required_segment":
        unknown_segment_id = str(solve_target["unknown_segment_id"])
        unknown_resistance = _solve_required_segment_resistance(normalized, unknown_segment_id)
        solved_temperatures, resolved_segments = _solve_temperatures(
            normalized,
            solved_unknown_overrides={unknown_segment_id: unknown_resistance},
        )
    else:
        unknown_resistance = None
        solved_temperatures, resolved_segments = _solve_temperatures(
            normalized,
            solved_unknown_overrides={},
        )

    node_results = _build_node_results(normalized, solved_temperatures, resolved_segments)
    summary = _build_summary(normalized, node_results, resolved_segments, unknown_resistance)
    diagnosis = _build_diagnosis(summary, normalized, resolved_segments)
    applicability = _build_applicability(normalized, resolved_segments)
    reporting_basis = {
        "reference_boundary_node_id": summary["reference_node_id"],
        "positive_heat_input_node_ids": [
            node["id"] for node in normalized["network"]["nodes"] if node["heat_input_w"] > 0.0
        ],
        "effective_total_resistance_definition": "(T_hottest - T_ref) / Q_total_positive",
        "contribution_definition": "100 * abs(delta_t_c) / total_temperature_rise_c",
        "contribution_caveat": "For parallel branches sharing entry/exit nodes, contributions will sum to more than 100% because each branch reports its own delta_T independently.",
    }

    status = _determine_status(node_results, summary)
    warnings = _dedupe_strings(validation["warnings"] + applicability["flags"])
    recommendations = _build_recommendations(diagnosis, resolved_segments, normalized)
    assumptions = _build_assumptions(normalized)
    parallel_groups = _build_parallel_groups(resolved_segments)
    derivations = _build_derivations(summary, resolved_segments, parallel_groups)
    diagram_payload = _build_diagram_payload(normalized, node_results, resolved_segments, summary)

    return {
        "status": status,
        "mode": normalized["analysis_mode"],
        "summary": summary,
        "diagnosis": diagnosis,
        "applicability": applicability,
        "reporting_basis": reporting_basis,
        "nodes": node_results,
        "segments": resolved_segments,
        "parallel_groups": parallel_groups,
        "diagram_payload": diagram_payload,
        "derivations": derivations,
        "warnings": warnings,
        "recommendations": recommendations,
        "assumptions": assumptions,
        "normalized_model": normalized,
    }


def generate_thermal_network_sensitivity(
    model: dict[str, object],
    segment_ids: list[str],
    variation_fraction: float = 0.2,
    points: int = 21,
) -> dict[str, object]:
    """
    Sweep selected segment resistances one at a time around a nominal solution.

    ---Parameters---
    model : dict[str, object]
        Canonical thermal-network model to analyze.
    segment_ids : list[str]
        Segment ids to sweep one at a time.
    variation_fraction : float
        Fractional variation about the nominal resistance. A value of ``0.2``
        sweeps from ``0.8 * R_nominal`` to ``1.2 * R_nominal``.
    points : int
        Number of sweep points for each selected segment. Must be at least 3.

    ---Returns---
    series : list[dict[str, object]]
        Plot-ready series keyed by segment id. Each series contains resistance
        sweep values and the resulting hottest-node temperature.

    ---LaTeX---
    R_{\\text{swept}} = R_{\\text{nominal}} \\left(1 + \\delta\\right)
    """
    if points < 3:
        raise ValueError("Sensitivity sweep requires at least 3 points.")
    if variation_fraction <= 0.0:
        raise ValueError("variation_fraction must be positive.")

    baseline = solve_thermal_network(model)
    if baseline["status"] == "invalid":
        raise ValueError("Cannot generate sensitivity for an invalid model.")

    normalized = baseline["normalized_model"]
    baseline_segments = {
        segment["id"]: segment for segment in baseline["segments"]
    }

    series: list[dict[str, object]] = []
    for segment_id in segment_ids:
        if segment_id not in baseline_segments:
            continue

        segment = baseline_segments[segment_id]
        nominal = float(segment["resolved_resistance_k_per_w"])
        if nominal <= 0.0:
            continue

        x_values: list[float] = []
        y_values: list[float] = []
        for index in range(points):
            frac = -variation_fraction + 2.0 * variation_fraction * index / (points - 1)
            candidate = nominal * (1.0 + frac)
            x_values.append(candidate)
            temps, _ = _solve_temperatures(
                normalized,
                solved_unknown_overrides={segment_id: candidate},
            )
            hottest_temperature = max(temps.values())
            y_values.append(hottest_temperature)

        series.append(
            {
                "segment_id": segment_id,
                "segment_label": segment["label"],
                "x_resistance_k_per_w": x_values,
                "y_hottest_temperature_c": y_values,
                "nominal_resistance_k_per_w": nominal,
                "nominal_hottest_temperature_c": baseline["summary"]["hottest_temperature_c"],
            }
        )

    return {"series": series}


def _normalize_model(model: dict[str, object], errors: list[str]) -> dict[str, Any]:
    if not isinstance(model, dict):
        errors.append("Model must be a dictionary.")
        return {}

    network = model.get("network")
    if not isinstance(network, dict):
        errors.append("Model.network must be a dictionary.")
        return {}

    raw_nodes = network.get("nodes")
    raw_segments = network.get("segments")
    if not isinstance(raw_nodes, list):
        errors.append("Model.network.nodes must be a list.")
        raw_nodes = []
    if not isinstance(raw_segments, list):
        errors.append("Model.network.segments must be a list.")
        raw_segments = []

    nodes: list[dict[str, Any]] = []
    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            errors.append("Each node must be a dictionary.")
            continue
        nodes.append(
            {
                "id": str(raw_node.get("id", "")).strip(),
                "label": str(raw_node.get("label", raw_node.get("id", ""))).strip(),
                "kind": str(raw_node.get("kind", "internal")).strip(),
                "heat_input_w": _coerce_float(raw_node.get("heat_input_w", 0.0), "node.heat_input_w", allow_default=True),
                "fixed_temperature_c": _coerce_optional_float(raw_node.get("fixed_temperature_c")),
                "max_temperature_c": _coerce_optional_float(raw_node.get("max_temperature_c")),
                "min_temperature_c": _coerce_optional_float(raw_node.get("min_temperature_c")),
                "notes": str(raw_node.get("notes", "")),
                "tags": list(raw_node.get("tags", [])) if isinstance(raw_node.get("tags", []), list) else [],
            }
        )

    segments: list[dict[str, Any]] = []
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            errors.append("Each segment must be a dictionary.")
            continue
        inputs = raw_segment.get("inputs", {})
        if not isinstance(inputs, dict):
            errors.append("Segment inputs must be dictionaries.")
            inputs = {}
        segments.append(
            {
                "id": str(raw_segment.get("id", "")).strip(),
                "label": str(raw_segment.get("label", raw_segment.get("id", ""))).strip(),
                "from_node_id": str(raw_segment.get("from_node_id", "")).strip(),
                "to_node_id": str(raw_segment.get("to_node_id", "")).strip(),
                "category": str(raw_segment.get("category", "other")).strip(),
                "mode": str(raw_segment.get("mode", "direct")).strip(),
                "inputs": {str(key): value for key, value in inputs.items()},
                "notes": str(raw_segment.get("notes", "")),
                "tags": list(raw_segment.get("tags", [])) if isinstance(raw_segment.get("tags", []), list) else [],
            }
        )

    solve_target = model.get("solve_target")
    normalized_target: dict[str, Any] | None = None
    if isinstance(solve_target, dict):
        normalized_target = {
            "target_node_id": str(solve_target.get("target_node_id", "")).strip(),
            "target_type": str(solve_target.get("target_type", "")).strip(),
            "target_value_c": solve_target.get("target_value_c"),
            "unknown_segment_id": str(solve_target.get("unknown_segment_id", "")).strip(),
        }

    options = model.get("options", {})
    if not isinstance(options, dict):
        options = {}

    return {
        "schema_version": str(model.get("schema_version", "1.0")),
        "template_id": str(model.get("template_id", "custom")).strip(),
        "analysis_mode": str(model.get("analysis_mode", "solve_temperatures")).strip(),
        "network": {
            "id": str(network.get("id", "main_network")).strip(),
            "label": str(network.get("label", "Thermal network")).strip(),
            "notes": str(network.get("notes", "")),
            "nodes": nodes,
            "segments": segments,
        },
        "solve_target": normalized_target,
        "options": {
            "include_derivations": bool(options.get("include_derivations", True)),
            "include_diagram_payload": bool(options.get("include_diagram_payload", True)),
            "include_equivalent_groups": bool(options.get("include_equivalent_groups", True)),
            "sensitivity_segment_ids": list(options.get("sensitivity_segment_ids", []))
            if isinstance(options.get("sensitivity_segment_ids", []), list)
            else [],
            "sensitivity_variation_fraction": _coerce_float(
                options.get("sensitivity_variation_fraction", 0.2),
                "options.sensitivity_variation_fraction",
                allow_default=True,
            ),
            "sensitivity_points": int(options.get("sensitivity_points", 21)),
        },
    }


def _coerce_float(value: object, name: str, allow_default: bool = False) -> float:
    if value is None:
        if allow_default:
            return 0.0
        raise ValueError(f"{name} must be provided.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number.") from exc


def _coerce_optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _resolve_segment_resistance(
    segment: dict[str, Any],
    solved_unknown_overrides: dict[str, float],
) -> tuple[float, str, str, str, list[dict[str, str]]]:
    """Return (resistance, subst_latex, equation_number, equation_latex, variable_legend)."""
    mode = segment["mode"]
    inputs = segment["inputs"]

    if segment["id"] in solved_unknown_overrides:
        resistance = solved_unknown_overrides[segment["id"]]
        if resistance <= 0.0:
            raise ValueError("Solved unknown resistance must be positive.")
        return (
            resistance,
            (
                "R_{\\theta} = "
                f"{resistance:.4f}\\,\\mathrm{{K/W}}"
            ),
            "Equation (U1)",
            "R_{\\theta} \\;\\text{(solved by bisection to meet target)}",
            [
                {
                    "symbol": "R_\\theta",
                    "meaning": "solved thermal resistance",
                    "units": "K/W",
                }
            ],
        )

    if mode == "direct":
        resistance = _coerce_float(inputs.get("resistance_k_per_w"), "resistance_k_per_w")
        if resistance <= 0.0:
            raise ValueError("Direct resistance must be greater than zero.")
        return (
            resistance,
            (
                "R_{\\theta} = "
                f"{resistance:.4f}\\,\\mathrm{{K/W}}"
            ),
            "Equation (1)",
            "R_{\\theta} \\;\\text{(user-supplied)}",
            [
                {
                    "symbol": "R_\\theta",
                    "meaning": "thermal resistance",
                    "units": "K/W",
                }
            ],
        )

    if mode == "tim_area_normalized":
        impedance = _coerce_float(
            inputs.get("impedance_k_cm2_per_w"),
            "impedance_k_cm2_per_w",
        )
        area_m2 = _coerce_float(inputs.get("contact_area_m2"), "contact_area_m2")
        if impedance <= 0.0 or area_m2 <= 0.0:
            raise ValueError("TIM impedance and contact area must both be greater than zero.")
        area_cm2 = area_m2 * 10000.0
        resistance = impedance / area_cm2
        return (
            resistance,
            (
                "R_{\\theta} = \\frac{Z_{\\mathrm{area}}}{A_{\\mathrm{contact}}}"
                f" = \\frac{{{impedance:.4f}}}{{{area_cm2:.4f}}}"
                f" = {resistance:.4f}\\,\\mathrm{{K/W}}"
            ),
            "Equation (2)",
            "R_{\\theta} = \\frac{Z_{\\mathrm{area}}}{A_{\\mathrm{contact}}}",
            [
                {
                    "symbol": "R_\\theta",
                    "meaning": "thermal resistance",
                    "units": "K/W",
                },
                {
                    "symbol": "Z_{\\mathrm{area}}",
                    "meaning": "area-normalized impedance",
                    "units": "K*cm^2/W",
                },
                {
                    "symbol": "A_{\\mathrm{contact}}",
                    "meaning": "contact area",
                    "units": "cm^2",
                },
            ],
        )

    if mode == "tim_conductivity":
        thickness = _coerce_float(
            inputs.get("bondline_thickness_m"),
            "bondline_thickness_m",
        )
        conductivity = _coerce_float(
            inputs.get("conductivity_w_per_mk"),
            "conductivity_w_per_mk",
        )
        area = _coerce_float(inputs.get("contact_area_m2"), "contact_area_m2")
        if thickness <= 0.0 or conductivity <= 0.0 or area <= 0.0:
            raise ValueError("TIM thickness, conductivity, and contact area must all be greater than zero.")
        resistance = thickness / (conductivity * area)
        return (
            resistance,
            (
                "R_{\\theta} = \\frac{t}{kA}"
                f" = \\frac{{{thickness:.6f}}}{{{conductivity:.4f} \\times {area:.6f}}}"
                f" = {resistance:.4f}\\,\\mathrm{{K/W}}"
            ),
            "Equation (3)",
            "R_{\\theta} = \\frac{t}{kA}",
            [
                {"symbol": "t", "meaning": "bondline thickness", "units": "m"},
                {"symbol": "k", "meaning": "thermal conductivity", "units": "W/(m*K)"},
                {"symbol": "A", "meaning": "contact area", "units": "m^2"},
            ],
        )

    if mode == "simple_conduction_slab":
        thickness = _coerce_float(inputs.get("thickness_m"), "thickness_m")
        conductivity = _coerce_float(
            inputs.get("conductivity_w_per_mk"),
            "conductivity_w_per_mk",
        )
        area = _coerce_float(
            inputs.get("cross_section_area_m2"),
            "cross_section_area_m2",
        )
        if thickness <= 0.0 or conductivity <= 0.0 or area <= 0.0:
            raise ValueError(
                "Conduction slab thickness, conductivity, and cross-sectional area must all be greater than zero."
            )
        resistance = thickness / (conductivity * area)
        return (
            resistance,
            (
                "R_{\\theta} = \\frac{L}{kA}"
                f" = \\frac{{{thickness:.6f}}}{{{conductivity:.4f} \\times {area:.6f}}}"
                f" = {resistance:.4f}\\,\\mathrm{{K/W}}"
            ),
            "Equation (4)",
            "R_{\\theta} = \\frac{L}{kA}",
            [
                {"symbol": "L", "meaning": "conduction length", "units": "m"},
                {"symbol": "k", "meaning": "thermal conductivity", "units": "W/(m*K)"},
                {"symbol": "A", "meaning": "cross-sectional area", "units": "m^2"},
            ],
        )

    if mode == "solved_unknown":
        initial_guess = _coerce_float(
            inputs.get("initial_guess_k_per_w"),
            "initial_guess_k_per_w",
        )
        if initial_guess <= 0.0:
            raise ValueError("initial_guess_k_per_w must be greater than zero.")
        raise ValueError(
            "Segments using mode 'solved_unknown' require a resolved override from solve_required_segment mode."
        )

    raise ValueError(f"Unsupported segment mode '{mode}'.")


def _is_connected(adjacency: dict[str, set[str]], start_node_id: str) -> bool:
    seen: set[str] = set()
    stack = [start_node_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(sorted(adjacency[current] - seen))
    return len(seen) == len(adjacency)


def _solve_required_segment_resistance(
    normalized: dict[str, Any],
    unknown_segment_id: str,
) -> float:
    solve_target = normalized["solve_target"]
    target_node_id = str(solve_target["target_node_id"])
    target_value_c = float(solve_target["target_value_c"])

    unknown_segment = next(
        segment
        for segment in normalized["network"]["segments"]
        if segment["id"] == unknown_segment_id
    )
    inputs = unknown_segment["inputs"]
    lower = float(inputs.get("lower_bound_k_per_w", 1e-4))
    upper = float(inputs.get("upper_bound_k_per_w", 20.0))
    if lower <= 0.0 or upper <= 0.0 or lower >= upper:
        raise ValueError("Invalid bounds for solved_unknown segment.")

    def evaluate(resistance: float) -> float:
        temperatures, _ = _solve_temperatures(
            normalized,
            solved_unknown_overrides={unknown_segment_id: resistance},
        )
        return temperatures[target_node_id]

    temp_low = evaluate(lower)
    if temp_low > target_value_c:
        raise ValueError(
            "Target temperature cannot be met even at the lower resistance bound."
        )

    temp_high = evaluate(upper)
    expand_count = 0
    while temp_high < target_value_c and expand_count < 20:
        upper *= 2.0
        temp_high = evaluate(upper)
        expand_count += 1

    if temp_high < target_value_c:
        raise ValueError(
            "Target temperature is not reached within the expanded upper resistance bound."
        )

    for _ in range(80):
        mid = 0.5 * (lower + upper)
        temp_mid = evaluate(mid)
        if temp_mid <= target_value_c:
            lower = mid
        else:
            upper = mid

    return lower


def _solve_temperatures(
    normalized: dict[str, Any],
    solved_unknown_overrides: dict[str, float],
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    nodes = normalized["network"]["nodes"]
    segments = normalized["network"]["segments"]

    node_lookup = {node["id"]: node for node in nodes}
    fixed_temperatures = {
        node["id"]: node["fixed_temperature_c"]
        for node in nodes
        if node["fixed_temperature_c"] is not None
    }
    unknown_ids = [node["id"] for node in nodes if node["fixed_temperature_c"] is None]
    unknown_index = {node_id: index for index, node_id in enumerate(unknown_ids)}

    resolved_data: list[dict[str, Any]] = []
    matrix = [[0.0 for _ in unknown_ids] for _ in unknown_ids]
    rhs = [float(node_lookup[node_id]["heat_input_w"]) for node_id in unknown_ids]

    for segment in segments:
        resistance, subst_resistance, equation_number, equation_latex, variable_legend = _resolve_segment_resistance(
            segment,
            solved_unknown_overrides=solved_unknown_overrides,
        )
        from_node_id = segment["from_node_id"]
        to_node_id = segment["to_node_id"]
        conductance = 1.0 / resistance

        if from_node_id in unknown_index:
            i = unknown_index[from_node_id]
            matrix[i][i] += conductance
            if to_node_id in unknown_index:
                matrix[i][unknown_index[to_node_id]] -= conductance
            else:
                rhs[i] += conductance * float(fixed_temperatures[to_node_id])

        if to_node_id in unknown_index:
            j = unknown_index[to_node_id]
            matrix[j][j] += conductance
            if from_node_id in unknown_index:
                matrix[j][unknown_index[from_node_id]] -= conductance
            else:
                rhs[j] += conductance * float(fixed_temperatures[from_node_id])

        resolved_data.append(
            {
                **segment,
                "resolved_resistance_k_per_w": resistance,
                "subst_resistance": subst_resistance,
                "equation_number": equation_number,
                "equation_latex": equation_latex,
                "variable_legend": variable_legend,
            }
        )

    unknown_temperatures = (
        _solve_linear_system(matrix, rhs) if unknown_ids else []
    )
    temperatures = {
        **{node_id: float(temp) for node_id, temp in fixed_temperatures.items()},
        **{
            node_id: float(unknown_temperatures[index])
            for node_id, index in unknown_index.items()
        },
    }

    total_rise = max(1e-12, max(temperatures.values()) - min(fixed_temperatures.values()))
    for resolved in resolved_data:
        temp_from = temperatures[resolved["from_node_id"]]
        temp_to = temperatures[resolved["to_node_id"]]
        signed_heat = (temp_from - temp_to) / resolved["resolved_resistance_k_per_w"]
        direction = "zero"
        if signed_heat > 1e-12:
            direction = "from_to"
        elif signed_heat < -1e-12:
            direction = "to_from"
        delta_t = abs(temp_from - temp_to)
        heat_flow = abs(signed_heat)
        resolved["heat_flow_w"] = heat_flow
        resolved["delta_t_c"] = delta_t
        resolved["contribution_pct"] = 100.0 * delta_t / total_rise
        resolved["direction"] = direction
        resolved["is_solved_unknown"] = resolved["id"] in solved_unknown_overrides
        resolved["subst_delta_t"] = (
            "\\Delta T = Q \\times R = "
            f"{heat_flow:.4f} \\times {resolved['resolved_resistance_k_per_w']:.4f}"
            f" = {delta_t:.4f}\\,\\mathrm{{C}}"
        )

    return temperatures, resolved_data


def _solve_linear_system(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    size = len(rhs)
    if size == 0:
        return []

    augmented = [row[:] + [rhs_value] for row, rhs_value in zip(matrix, rhs)]
    for pivot in range(size):
        pivot_row = max(range(pivot, size), key=lambda row: abs(augmented[row][pivot]))
        if abs(augmented[pivot_row][pivot]) < 1e-14:
            raise ValueError("Thermal network matrix is singular.")
        if pivot_row != pivot:
            augmented[pivot], augmented[pivot_row] = augmented[pivot_row], augmented[pivot]

        pivot_value = augmented[pivot][pivot]
        for column in range(pivot, size + 1):
            augmented[pivot][column] /= pivot_value

        for row in range(size):
            if row == pivot:
                continue
            factor = augmented[row][pivot]
            if factor == 0.0:
                continue
            for column in range(pivot, size + 1):
                augmented[row][column] -= factor * augmented[pivot][column]

    return [augmented[row][size] for row in range(size)]


def _build_node_results(
    normalized: dict[str, Any],
    temperatures: dict[str, float],
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    connected_segments: dict[str, list[str]] = {node["id"]: [] for node in normalized["network"]["nodes"]}
    for segment in segments:
        connected_segments[segment["from_node_id"]].append(segment["id"])
        connected_segments[segment["to_node_id"]].append(segment["id"])

    results: list[dict[str, Any]] = []
    for node in normalized["network"]["nodes"]:
        temperature = temperatures[node["id"]]
        max_temperature_c = node["max_temperature_c"]
        margin_to_max = None
        status = None
        if max_temperature_c is not None:
            margin_to_max = max_temperature_c - temperature
            status = "acceptable" if margin_to_max >= 5.0 else "marginal" if margin_to_max >= 0.0 else "unacceptable"

        results.append(
            {
                "id": node["id"],
                "label": node["label"],
                "kind": node["kind"],
                "temperature_c": temperature,
                "fixed_temperature_c": node["fixed_temperature_c"],
                "heat_input_w": node["heat_input_w"],
                "net_outgoing_heat_w": node["heat_input_w"],
                "max_temperature_c": max_temperature_c,
                "margin_to_max_c": margin_to_max,
                "status": status,
                "connected_segment_ids": connected_segments[node["id"]],
                "notes": node["notes"],
                "tags": node["tags"],
            }
        )

    return results


def _build_summary(
    normalized: dict[str, Any],
    node_results: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    unknown_resistance: float | None,
) -> dict[str, Any]:
    hottest_node = max(node_results, key=lambda node: node["temperature_c"])
    reference_node = next(
        node for node in node_results if node["fixed_temperature_c"] is not None
    )
    total_applied_heat = sum(max(0.0, node["heat_input_w"]) for node in node_results)
    total_rise = hottest_node["temperature_c"] - reference_node["temperature_c"]
    effective_resistance = total_rise / total_applied_heat if total_applied_heat > 0.0 else None
    dominant_segment = max(segments, key=lambda segment: segment["contribution_pct"])

    margin_to_limit = None
    controlling_limit_node_id = None
    limit_bearing_nodes = [node for node in node_results if node["margin_to_max_c"] is not None]
    if limit_bearing_nodes:
        controlling = min(limit_bearing_nodes, key=lambda node: float(node["margin_to_max_c"]))
        margin_to_limit = controlling["margin_to_max_c"]
        controlling_limit_node_id = controlling["id"]

    if normalized["analysis_mode"] == "solve_required_segment" and normalized["solve_target"]:
        target_node_id = normalized["solve_target"]["target_node_id"]
        target_node = next(node for node in node_results if node["id"] == target_node_id)
        margin_to_limit = float(normalized["solve_target"]["target_value_c"]) - target_node["temperature_c"]
        controlling_limit_node_id = target_node_id

    return {
        "hottest_node_id": hottest_node["id"],
        "hottest_node_label": hottest_node["label"],
        "hottest_temperature_c": hottest_node["temperature_c"],
        "reference_node_id": reference_node["id"],
        "reference_temperature_c": reference_node["temperature_c"],
        "total_temperature_rise_c": total_rise,
        "total_applied_heat_w": total_applied_heat,
        "effective_total_resistance_k_per_w": effective_resistance,
        "dominant_segment_id": dominant_segment["id"],
        "dominant_segment_label": dominant_segment["label"],
        "dominant_segment_contribution_pct": dominant_segment["contribution_pct"],
        "controlling_limit_node_id": controlling_limit_node_id,
        "margin_to_limit_c": margin_to_limit,
        "sized_unknown_segment_id": (
            str(normalized["solve_target"]["unknown_segment_id"])
            if normalized["analysis_mode"] == "solve_required_segment" and normalized["solve_target"]
            else None
        ),
        "sized_unknown_resistance_k_per_w": unknown_resistance,
    }


def _build_diagnosis(
    summary: dict[str, Any],
    normalized: dict[str, Any],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    dominant_segment = next(
        segment for segment in segments if segment["id"] == summary["dominant_segment_id"]
    )
    improvement_summary = None
    if summary["sized_unknown_segment_id"] and summary["sized_unknown_resistance_k_per_w"] is not None:
        target_segment = next(
            segment for segment in segments if segment["id"] == summary["sized_unknown_segment_id"]
        )
        improvement_summary = (
            f"Reduce {target_segment['label']} to "
            f"{summary['sized_unknown_resistance_k_per_w']:.3f} K/W or lower to meet the selected limit."
        )

    return {
        "dominant_segment_id": dominant_segment["id"],
        "dominant_segment_label": dominant_segment["label"],
        "dominant_segment_delta_t_c": dominant_segment["delta_t_c"],
        "dominant_segment_contribution_pct": dominant_segment["contribution_pct"],
        "first_improvement_target_id": dominant_segment["id"],
        "first_improvement_target_label": dominant_segment["label"],
        "first_improvement_reason": "Largest contribution to total temperature rise.",
        "required_improvement_summary": improvement_summary,
    }


def _build_applicability(
    normalized: dict[str, Any],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    status = "good_fit"
    flags: list[str] = []
    routing_suggestion: str | None = None

    if normalized["template_id"] == "custom":
        status = "use_with_caution"
        flags.append("Custom networks require careful physical mapping of nodes and resistances.")

    if any(segment["mode"] == "simple_conduction_slab" for segment in segments):
        status = "use_with_caution"
        flags.append("One-dimensional slab resistance may understate in-plane spreading effects.")

    if (
        normalized["template_id"] == "package_to_sink"
        and any(segment["category"] == "sink_to_ambient" and segment["mode"] == "direct" for segment in segments)
    ):
        routing_suggestion = (
            "If the sink geometry is known, cross-check the sink-to-ambient segment with the heatsink designer."
        )

    score_label = {
        "good_fit": "Good fit",
        "use_with_caution": "Use with caution",
        "better_in_other_tool": "Better in another tool",
    }[status]

    return {
        "status": status,
        "score_label": score_label,
        "flags": flags,
        "routing_suggestion": routing_suggestion,
    }


def _determine_status(node_results: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    margins = [
        float(node["margin_to_max_c"])
        for node in node_results
        if node["margin_to_max_c"] is not None
    ]
    if summary["margin_to_limit_c"] is not None:
        margins.append(float(summary["margin_to_limit_c"]))

    if not margins:
        return "acceptable"
    minimum_margin = min(margins)
    if minimum_margin < 0.0:
        return "unacceptable"
    if minimum_margin < 5.0:
        return "marginal"
    return "acceptable"


def _build_recommendations(
    diagnosis: dict[str, Any],
    segments: list[dict[str, Any]],
    normalized: dict[str, Any],
) -> list[str]:
    target_segment = next(
        segment for segment in segments if segment["id"] == diagnosis["first_improvement_target_id"]
    )
    category = target_segment["category"]

    recommendations: list[str] = []
    if category == "interface":
        recommendations.append("Reduce interface resistance by increasing contact area, pressure, or TIM conductivity.")
    elif category == "sink_to_ambient":
        recommendations.append("Reduce sink-to-ambient resistance by improving airflow, surface area, or sink selection.")
    elif category == "junction_to_case":
        recommendations.append("Reduce source-to-case resistance by selecting a lower-R_theta package or reducing heat load.")
    elif category == "conduction":
        recommendations.append("Shorten the conduction path or increase conductivity/cross-sectional area in the dominant slab.")
    else:
        recommendations.append("Lower the dominant segment resistance first; it currently owns the largest share of temperature rise.")

    if diagnosis["required_improvement_summary"]:
        recommendations.append(diagnosis["required_improvement_summary"])

    if normalized["template_id"] == "custom":
        recommendations.append("Confirm that each resistance maps to a real physical boundary or material path before trusting the result.")

    return _dedupe_strings(recommendations)


def _build_assumptions(normalized: dict[str, Any]) -> list[str]:
    assumptions = [
        "Steady-state heat flow only; no thermal capacitance or transient effects are included.",
        "The user-facing MVP assumes one positive heat-input node and one fixed-temperature boundary node.",
        "All segment resistances are treated as linear and temperature-independent for the solve.",
    ]
    if any(segment["mode"] == "simple_conduction_slab" for segment in normalized["network"]["segments"]):
        assumptions.append("Conduction slab segments use one-dimensional heat flow and do not include spreading penalties.")
    return assumptions


def _build_parallel_groups(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for segment in segments:
        key = tuple(sorted((segment["from_node_id"], segment["to_node_id"])))
        groups.setdefault(key, []).append(segment)

    parallel_groups: list[dict[str, Any]] = []
    for index, (key, members) in enumerate(groups.items(), start=1):
        if len(members) < 2:
            continue
        equivalent_resistance = 1.0 / sum(
            1.0 / float(member["resolved_resistance_k_per_w"]) for member in members
        )
        pieces = " + ".join(
            f"\\frac{{1}}{{{member['resolved_resistance_k_per_w']:.4f}}}" for member in members
        )
        parallel_groups.append(
            {
                "id": f"pg_{index}",
                "entry_node_id": members[0]["from_node_id"],
                "exit_node_id": members[0]["to_node_id"],
                "segment_ids": [member["id"] for member in members],
                "equivalent_resistance_k_per_w": equivalent_resistance,
                "heat_split_w": {
                    member["id"]: member["heat_flow_w"] for member in members
                },
                "subst_equivalent_resistance": (
                    "\\frac{1}{R_{\\mathrm{eq}}} = "
                    f"{pieces},\\; R_{{\\mathrm{{eq}}}} = {equivalent_resistance:.4f}\\,\\mathrm{{K/W}}"
                ),
            }
        )

    return parallel_groups


def _build_derivations(
    summary: dict[str, Any],
    segments: list[dict[str, Any]],
    parallel_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    derivations: list[dict[str, Any]] = []
    for segment in segments:
        derivations.append(
            {
                "id": f"drv_{segment['id']}_resistance",
                "subject_type": "segment",
                "subject_id": segment["id"],
                "result_key": "resolved_resistance_k_per_w",
                "title": f"{segment['label']} resistance",
                "equation_number": segment["equation_number"],
                "equation_latex": segment["equation_latex"],
                "variable_legend": segment["variable_legend"],
                "substitution_latex": segment["subst_resistance"],
                "result_value": segment["resolved_resistance_k_per_w"],
                "result_units": "K/W",
                "depends_on": [],
                "step_type": "segment_resistance",
            }
        )
        derivations.append(
            {
                "id": f"drv_{segment['id']}_delta_t",
                "subject_type": "segment",
                "subject_id": segment["id"],
                "result_key": "delta_t_c",
                "title": f"{segment['label']} temperature drop",
                "equation_number": "Equation (Q1)",
                "equation_latex": "\\Delta T = Q \\times R",
                "variable_legend": [
                    {"symbol": "\\Delta T", "meaning": "temperature drop", "units": "C"},
                    {"symbol": "Q", "meaning": "heat flow", "units": "W"},
                    {"symbol": "R", "meaning": "thermal resistance", "units": "K/W"},
                ],
                "substitution_latex": segment["subst_delta_t"],
                "result_value": segment["delta_t_c"],
                "result_units": "C",
                "depends_on": [f"drv_{segment['id']}_resistance"],
                "step_type": "segment_delta_t",
            }
        )

    if summary.get("effective_total_resistance_k_per_w") is not None:
        derivations.append(
            {
                "id": "drv_summary_effective_total_resistance",
                "subject_type": "summary",
                "subject_id": "summary",
                "result_key": "effective_total_resistance_k_per_w",
                "title": "Effective total thermal resistance",
                "equation_number": "Equation (S1)",
                "equation_latex": "R_{\\mathrm{eff}} = \\frac{T_{\\mathrm{hot}} - T_{\\mathrm{ref}}}{Q_{\\mathrm{total}}}",
                "variable_legend": [
                    {"symbol": "R_{\\mathrm{eff}}", "meaning": "effective total resistance", "units": "K/W"},
                    {"symbol": "T_{\\mathrm{hot}}", "meaning": "hottest node temperature", "units": "C"},
                    {"symbol": "T_{\\mathrm{ref}}", "meaning": "reference boundary temperature", "units": "C"},
                    {"symbol": "Q_{\\mathrm{total}}", "meaning": "total applied heat", "units": "W"},
                ],
                "substitution_latex": (
                    "R_{\\mathrm{eff}} = "
                    f"\\frac{{{summary['hottest_temperature_c']:.4f} - {summary['reference_temperature_c']:.4f}}}"
                    f"{{{summary['total_applied_heat_w']:.4f}}}"
                    f" = {summary['effective_total_resistance_k_per_w']:.4f}\\,\\mathrm{{K/W}}"
                ),
                "result_value": summary["effective_total_resistance_k_per_w"],
                "result_units": "K/W",
                "depends_on": [],
                "step_type": "summary_metric",
            }
        )

    for group in parallel_groups:
        derivations.append(
            {
                "id": f"drv_{group['id']}_parallel",
                "subject_type": "parallel_group",
                "subject_id": group["id"],
                "result_key": "equivalent_resistance_k_per_w",
                "title": "Parallel path equivalent resistance",
                "equation_number": "Equation (P1)",
                "equation_latex": "\\frac{1}{R_{\\mathrm{eq}}} = \\sum_i \\frac{1}{R_i}",
                "variable_legend": [
                    {"symbol": "R_{\\mathrm{eq}}", "meaning": "equivalent resistance", "units": "K/W"},
                    {"symbol": "R_i", "meaning": "branch resistance", "units": "K/W"},
                ],
                "substitution_latex": group["subst_equivalent_resistance"],
                "result_value": group["equivalent_resistance_k_per_w"],
                "result_units": "K/W",
                "depends_on": [],
                "step_type": "parallel_group",
            }
        )

    return derivations


def _build_diagram_payload(
    normalized: dict[str, Any],
    node_results: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    node_ranks = _assign_node_ranks(normalized["network"]["nodes"], segments, summary["reference_node_id"])
    return {
        "nodes": [
            {
                "id": node["id"],
                "label": node["label"],
                "temperature_c": node["temperature_c"],
                "rank": node_ranks.get(node["id"], 0),
                "is_reference": node["id"] == summary["reference_node_id"],
                "is_hottest": node["id"] == summary["hottest_node_id"],
            }
            for node in node_results
        ],
        "edges": [
            {
                "id": segment["id"],
                "from_node_id": segment["from_node_id"],
                "to_node_id": segment["to_node_id"],
                "resolved_resistance_k_per_w": segment["resolved_resistance_k_per_w"],
                "delta_t_c": segment["delta_t_c"],
                "heat_flow_w": segment["heat_flow_w"],
                "branch_group_id": None,
            }
            for segment in segments
        ],
        "reference_node_id": summary["reference_node_id"],
        "primary_hot_path_node_ids": _primary_hot_path(summary["hottest_node_id"], summary["reference_node_id"], segments),
    }


def _assign_node_ranks(
    nodes: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    reference_node_id: str,
) -> dict[str, int]:
    adjacency: dict[str, set[str]] = {node["id"]: set() for node in nodes}
    for segment in segments:
        adjacency[segment["from_node_id"]].add(segment["to_node_id"])
        adjacency[segment["to_node_id"]].add(segment["from_node_id"])

    ranks = {reference_node_id: 0}
    queue = [reference_node_id]
    while queue:
        current = queue.pop(0)
        for neighbor in sorted(adjacency[current]):
            if neighbor not in ranks:
                ranks[neighbor] = ranks[current] + 1
                queue.append(neighbor)
    max_rank = max(ranks.values()) if ranks else 0
    return {node_id: max_rank - rank for node_id, rank in ranks.items()}


def _primary_hot_path(
    hottest_node_id: str,
    reference_node_id: str,
    segments: list[dict[str, Any]],
) -> list[str]:
    adjacency: dict[str, list[str]] = {}
    for segment in segments:
        adjacency.setdefault(segment["from_node_id"], []).append(segment["to_node_id"])
        adjacency.setdefault(segment["to_node_id"], []).append(segment["from_node_id"])

    queue: list[tuple[str, list[str]]] = [(hottest_node_id, [hottest_node_id])]
    seen = {hottest_node_id}
    while queue:
        current, path = queue.pop(0)
        if current == reference_node_id:
            return path
        for neighbor in adjacency.get(current, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return [hottest_node_id, reference_node_id]


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
