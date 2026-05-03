"""Transient lumped thermal RC simulator.

Implements implicit-Euler simulation of a small thermal RC network with
time-varying heat input.  Supports step, pulse, and repeating duty-cycle
power profiles, and reports time-to-limit, peak temperatures, cooldown
time, and cyclic-steady-state convergence.

Companion plan: ``plans/2026-04-25_transient_heatsink_tool_plan.md``.
"""

from __future__ import annotations

import math
from typing import Any


# Default density and specific heat for thermal-capacitance presets (SI).
# Sources: standard handbook tables (Cengel & Ghajar, Incropera).
MATERIAL_PRESETS: dict[str, dict[str, float | str]] = {
    "aluminum_6063": {
        "label": "Aluminum 6063",
        "density_kg_per_m3": 2700.0,
        "heat_capacity_j_per_kgk": 900.0,
        "notes": "Default extruded heatsink alloy.",
    },
    "aluminum_6061": {
        "label": "Aluminum 6061",
        "density_kg_per_m3": 2700.0,
        "heat_capacity_j_per_kgk": 896.0,
        "notes": "Common machined plate or sink stock.",
    },
    "copper_c110": {
        "label": "Copper C110",
        "density_kg_per_m3": 8960.0,
        "heat_capacity_j_per_kgk": 385.0,
        "notes": "High mass and conductivity.",
    },
    "steel": {
        "label": "Carbon steel",
        "density_kg_per_m3": 7850.0,
        "heat_capacity_j_per_kgk": 470.0,
        "notes": "Chassis, brackets, motor frames.",
    },
    "fr4": {
        "label": "FR-4 (effective)",
        "density_kg_per_m3": 1850.0,
        "heat_capacity_j_per_kgk": 900.0,
        "notes": "Approximate PCB lump.",
    },
    "silicon": {
        "label": "Silicon die",
        "density_kg_per_m3": 2330.0,
        "heat_capacity_j_per_kgk": 700.0,
        "notes": "Die or source approximation.",
    },
}


PROFILE_TYPES = {"step", "pulse", "duty_cycle"}
NODE_KINDS = {"dynamic", "boundary"}


# --------------------------------------------------------------------------- #
# Material / capacitance helpers                                              #
# --------------------------------------------------------------------------- #


def get_material_presets() -> dict[str, dict[str, float | str]]:
    """Return the available thermal-capacitance material presets."""

    return {key: dict(value) for key, value in MATERIAL_PRESETS.items()}


def estimate_thermal_capacitance(
    volume_m3: float,
    material_id: str | None = None,
    density_kg_per_m3: float | None = None,
    heat_capacity_j_per_kgk: float | None = None,
) -> dict[str, Any]:
    r"""
    Estimate lumped thermal capacitance from geometry and material properties.

    ---Parameters---
    volume_m3 : float
        Solid volume of the lumped body in cubic metres. Must be positive.
    material_id : str
        Optional preset key from :func:`get_material_presets`. When supplied,
        the preset density and heat capacity are used unless explicitly
        overridden by the keyword arguments.
    density_kg_per_m3 : float
        Override for material density.
    heat_capacity_j_per_kgk : float
        Override for specific heat capacity.

    ---Returns---
    capacitance_j_per_k : float
        Lumped thermal capacitance ``C = rho * V * c_p`` in joules per kelvin.
    mass_kg : float
        Estimated mass ``m = rho * V``.
    density_kg_per_m3 : float
        Density used in the calculation.
    heat_capacity_j_per_kgk : float
        Specific heat used in the calculation.
    subst_capacitance : str
        Substituted equation string for ``C``.

    ---LaTeX---
    C = \rho V c_p
    """

    if volume_m3 <= 0.0:
        raise ValueError("volume_m3 must be greater than zero.")

    rho = density_kg_per_m3
    cp = heat_capacity_j_per_kgk
    if material_id is not None:
        preset = MATERIAL_PRESETS.get(material_id)
        if preset is None:
            raise ValueError(
                f"Unknown material_id '{material_id}'."
                f" Use one of {sorted(MATERIAL_PRESETS)}."
            )
        if rho is None:
            rho = float(preset["density_kg_per_m3"])
        if cp is None:
            cp = float(preset["heat_capacity_j_per_kgk"])

    if rho is None or cp is None:
        raise ValueError(
            "Provide either material_id or both density_kg_per_m3 and"
            " heat_capacity_j_per_kgk."
        )
    if rho <= 0.0 or cp <= 0.0:
        raise ValueError("density and specific heat must be greater than zero.")

    mass = rho * volume_m3
    capacitance = mass * cp
    return {
        "capacitance_j_per_k": capacitance,
        "mass_kg": mass,
        "density_kg_per_m3": rho,
        "heat_capacity_j_per_kgk": cp,
        "subst_capacitance": (
            f"C = \\rho V c_p = {rho:.1f} \\times {volume_m3:.6g}"
            f" \\times {cp:.1f} = {capacitance:.2f}\\,\\mathrm{{J/K}}"
        ),
    }


# --------------------------------------------------------------------------- #
# Power profile generation                                                    #
# --------------------------------------------------------------------------- #


def generate_power_profile(profile: dict[str, Any], time_s: list[float]) -> list[float]:
    """
    Return the heat-input series ``Q(t)`` for the requested power profile.

    The profile dictionary must include a ``type`` key in
    ``{"step", "pulse", "duty_cycle"}``.  Step expects ``power_w``.  Pulse
    expects ``pulse_power_w``, ``pulse_duration_s``, optional
    ``cooldown_power_w`` (default 0).  Duty cycle expects ``on_power_w``,
    ``on_time_s``, ``off_power_w`` (default 0), ``off_time_s``.
    """

    profile_type = profile.get("type")
    if profile_type not in PROFILE_TYPES:
        raise ValueError(
            f"profile.type must be one of {sorted(PROFILE_TYPES)}, got {profile_type!r}."
        )

    if profile_type == "step":
        power = float(profile.get("power_w", 0.0))
        return [power for _ in time_s]

    if profile_type == "pulse":
        pulse_power = float(profile.get("pulse_power_w", 0.0))
        pulse_duration = float(profile.get("pulse_duration_s", 0.0))
        cooldown_power = float(profile.get("cooldown_power_w", 0.0))
        if pulse_duration < 0.0:
            raise ValueError("pulse_duration_s cannot be negative.")
        return [pulse_power if t < pulse_duration else cooldown_power for t in time_s]

    on_power = float(profile.get("on_power_w", 0.0))
    on_time = float(profile.get("on_time_s", 0.0))
    off_power = float(profile.get("off_power_w", 0.0))
    off_time = float(profile.get("off_time_s", 0.0))
    cycle = on_time + off_time
    if cycle <= 0.0:
        raise ValueError("duty_cycle on_time_s + off_time_s must be greater than zero.")
    series = []
    for t in time_s:
        phase = t - cycle * math.floor(t / cycle)
        series.append(on_power if phase < on_time else off_power)
    return series


# --------------------------------------------------------------------------- #
# Network validation                                                          #
# --------------------------------------------------------------------------- #


def validate_transient_thermal_model(model: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a transient RC model and return errors / warnings / normalized form.

    The model must define one boundary node, at least one dynamic node, a heat
    input node, a profile, time settings, and series segments connecting all
    dynamic nodes back to a boundary.
    """

    errors: list[str] = []
    warnings: list[str] = []

    network = model.get("network") or {}
    nodes = list(network.get("nodes") or [])
    segments = list(network.get("segments") or [])
    profile = dict(model.get("profile") or {})
    time_settings = dict(model.get("time") or {})
    heat_inputs = list(network.get("heat_inputs") or [])

    if not nodes:
        errors.append("Network must contain at least one node.")
    if not segments:
        errors.append("Network must contain at least one segment.")
    if not heat_inputs:
        errors.append("Network must define at least one heat_input.")

    boundary_nodes = [n for n in nodes if n.get("kind") == "boundary"]
    dynamic_nodes = [n for n in nodes if n.get("kind") == "dynamic"]
    if len(boundary_nodes) != 1:
        errors.append("Exactly one boundary node is required in the MVP.")
    if not dynamic_nodes:
        errors.append("At least one dynamic node is required.")

    seen_ids: set[str] = set()
    for node in nodes:
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            errors.append("Every node needs a non-empty string id.")
            continue
        if node_id in seen_ids:
            errors.append(f"Duplicate node id '{node_id}'.")
        seen_ids.add(node_id)
        kind = node.get("kind")
        if kind not in NODE_KINDS:
            errors.append(f"Node '{node_id}' has unknown kind '{kind}'.")
        if kind == "dynamic":
            cap = node.get("capacitance_j_per_k")
            if cap is None or float(cap) <= 0.0:
                errors.append(
                    f"Dynamic node '{node_id}' needs capacitance_j_per_k > 0."
                )
        if kind == "boundary" and node.get("fixed_temperature_c") is None:
            errors.append(f"Boundary node '{node_id}' needs fixed_temperature_c.")

    valid_node_ids = {n["id"] for n in nodes if isinstance(n.get("id"), str)}
    for segment in segments:
        seg_id = segment.get("id", "<unnamed>")
        for endpoint in ("from_node_id", "to_node_id"):
            target = segment.get(endpoint)
            if target not in valid_node_ids:
                errors.append(
                    f"Segment '{seg_id}' references unknown {endpoint} '{target}'."
                )
        resistance = segment.get("resistance_k_per_w")
        if resistance is None or float(resistance) <= 0.0:
            errors.append(f"Segment '{seg_id}' needs resistance_k_per_w > 0.")

    for heat_input in heat_inputs:
        target = heat_input.get("node_id")
        if target not in {n["id"] for n in dynamic_nodes if isinstance(n.get("id"), str)}:
            errors.append(
                f"heat_input.node_id '{target}' must reference a dynamic node."
            )

    # Connectivity: every dynamic node must reach the boundary through segments.
    if not errors and len(boundary_nodes) == 1 and dynamic_nodes:
        adjacency: dict[str, set[str]] = {n["id"]: set() for n in nodes}
        for segment in segments:
            adjacency[segment["from_node_id"]].add(segment["to_node_id"])
            adjacency[segment["to_node_id"]].add(segment["from_node_id"])
        boundary_id = boundary_nodes[0]["id"]
        seen = {boundary_id}
        stack = [boundary_id]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        for node in dynamic_nodes:
            if node["id"] not in seen:
                errors.append(
                    f"Dynamic node '{node['id']}' is not connected to the boundary."
                )

    if profile.get("type") not in PROFILE_TYPES:
        errors.append(
            f"profile.type must be one of {sorted(PROFILE_TYPES)}."
        )
    duration = time_settings.get("duration_s")
    if duration is None or float(duration) <= 0.0:
        errors.append("time.duration_s must be greater than zero.")
    initial = time_settings.get("initial_temperature_c")
    if initial is None:
        errors.append("time.initial_temperature_c is required.")

    normalized = {
        "network": {
            "nodes": [dict(n) for n in nodes],
            "segments": [dict(s) for s in segments],
            "heat_inputs": [dict(h) for h in heat_inputs],
        },
        "profile": profile,
        "time": time_settings,
    }

    return {
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "normalized_model": normalized,
    }


# --------------------------------------------------------------------------- #
# Time grid                                                                   #
# --------------------------------------------------------------------------- #


def _time_grid(duration: float, dt: float | None, profile: dict[str, Any]) -> list[float]:
    """Build the simulation time grid.

    Default ``dt`` is chosen so that the shortest profile event is sampled at
    least 25 times, capped at ``duration / 2000`` to keep arrays browser-sized.
    """

    if dt is not None and dt > 0.0:
        chosen_dt = float(dt)
    else:
        ptype = profile.get("type")
        if ptype == "pulse":
            short = float(profile.get("pulse_duration_s", duration))
        elif ptype == "duty_cycle":
            short = min(
                float(profile.get("on_time_s", duration)),
                float(profile.get("off_time_s", duration)),
            )
        else:
            short = duration
        short = max(short, 1e-6)
        chosen_dt = max(short / 25.0, duration / 2000.0)
        chosen_dt = min(chosen_dt, duration / 4.0)
    n_steps = max(2, int(math.ceil(duration / chosen_dt)) + 1)
    return [min(duration, i * chosen_dt) for i in range(n_steps)]


# --------------------------------------------------------------------------- #
# Linear solve (small dense Gauss-Jordan with partial pivoting)               #
# --------------------------------------------------------------------------- #


def _solve_linear_system(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    size = len(rhs)
    if size == 0:
        return []
    augmented = [row[:] + [b] for row, b in zip(matrix, rhs)]
    for pivot in range(size):
        pivot_row = max(range(pivot, size), key=lambda r: abs(augmented[r][pivot]))
        if abs(augmented[pivot_row][pivot]) < 1e-14:
            raise ValueError("Transient thermal matrix is singular.")
        if pivot_row != pivot:
            augmented[pivot], augmented[pivot_row] = augmented[pivot_row], augmented[pivot]
        pivot_value = augmented[pivot][pivot]
        for col in range(pivot, size + 1):
            augmented[pivot][col] /= pivot_value
        for row in range(size):
            if row == pivot:
                continue
            factor = augmented[row][pivot]
            if factor == 0.0:
                continue
            for col in range(pivot, size + 1):
                augmented[row][col] -= factor * augmented[pivot][col]
    return [augmented[r][size] for r in range(size)]


# --------------------------------------------------------------------------- #
# Time-to-limit interpolation                                                 #
# --------------------------------------------------------------------------- #


def _interpolate_crossing(
    t_prev: float, t_curr: float, T_prev: float, T_curr: float, limit: float
) -> float:
    if T_curr == T_prev:
        return t_curr
    fraction = (limit - T_prev) / (T_curr - T_prev)
    fraction = max(0.0, min(1.0, fraction))
    return t_prev + fraction * (t_curr - t_prev)


# --------------------------------------------------------------------------- #
# Main solver                                                                 #
# --------------------------------------------------------------------------- #


def simulate_transient_thermal_model(model: dict[str, Any]) -> dict[str, Any]:
    r"""
    Simulate a lumped transient thermal RC network with time-varying heat input.

    The solver builds the network conductance matrix once, then advances each
    time step with implicit Euler.  For every dynamic node ``i`` we discretize
    ``C_i dT_i/dt = Q_i(t) + sum_j (T_j - T_i) / R_ij`` as

    .. math::

        \left( \frac{C_i}{\Delta t} + \sum_j G_{ij} \right) T_i^{n+1}
        - \sum_j G_{ij} T_j^{n+1}
        = \frac{C_i}{\Delta t} T_i^n + Q_i^{n+1}
        + \sum_{j \in \text{boundary}} G_{ij} T_j

    which gives a small dense linear system per step.  The implicit scheme is
    unconditionally stable for the linear thermal RC problem, so the time
    step is chosen for resolution rather than stability.

    Step, pulse, and duty-cycle power profiles are supported.  The solver
    reports time-to-limit (with linear interpolation between samples), peak
    temperatures per node, cooldown time to a target temperature, and
    cyclic-steady-state convergence for duty cycles.

    ---Parameters---
    model : dict[str, Any]
        Transient thermal model dictionary. See
        ``plans/2026-04-25_transient_heatsink_tool_plan.md`` Section 9 for
        the full schema. Required keys: ``time``, ``profile``, ``network``.

    ---Returns---
    status : str
        ``acceptable``, ``marginal``, ``unacceptable``, ``not_converged``,
        or ``invalid``.
    summary : dict
        Headline metrics: ``time_to_limit_s``, ``peak_temperature_c``,
        ``peak_node_id``, ``final_temperature_c``,
        ``cyclic_steady_state_reached``, ``cooldown_time_to_target_s``,
        ``dominant_time_constant_s``, ``limiting_node_id``.
    series : dict
        Time series payload: ``time_s`` (list), ``power_w`` (list),
        ``node_temperatures_c`` (dict of node_id -> list).
    nodes : list[dict]
        Per-node payload with capacitance, peak temperature, and limit margin.
    segments : list[dict]
        Per-segment payload with resistance and time constant ``R*C_eff``.
    time_constants : list[dict]
        Estimated single-node time constants ``C_i / sum_j G_ij``, sorted.
    cycle_summary : list[dict]
        For duty-cycle mode, per-cycle peak/min temperatures of the limiting
        node. Empty list otherwise.
    diagnosis : list[str]
        Plain-language interpretation of the dominant time scale and bottleneck.
    recommendations : list[str]
        Suggested levers (resistance vs. mass) given the diagnosis.
    warnings : list[str]
        Non-fatal cautions (uncertain capacitance, very stiff system, etc.).
    errors : list[str]
        Validation errors when the model could not be solved.
    subst_governing : str
        Substituted-equation string for the governing RC ODE.

    ---LaTeX---
    C_i \frac{dT_i}{dt} = Q_i(t) + \sum_j \frac{T_j - T_i}{R_{ij}}
    """

    validation = validate_transient_thermal_model(model)
    if not validation["is_valid"]:
        return {
            "status": "invalid",
            "summary": {},
            "series": {"time_s": [], "power_w": [], "node_temperatures_c": {}},
            "nodes": [],
            "segments": [],
            "time_constants": [],
            "cycle_summary": [],
            "diagnosis": [],
            "recommendations": [],
            "warnings": validation["warnings"],
            "errors": validation["errors"],
            "subst_governing": "",
        }

    normalized = validation["normalized_model"]
    nodes = normalized["network"]["nodes"]
    segments = normalized["network"]["segments"]
    heat_inputs = normalized["network"]["heat_inputs"]
    profile = normalized["profile"]
    time_settings = normalized["time"]

    requested_duration = float(time_settings["duration_s"])
    dt_input = time_settings.get("time_step_s")
    initial_temp = float(time_settings["initial_temperature_c"])

    boundary_node = next(n for n in nodes if n["kind"] == "boundary")
    dynamic_nodes = [n for n in nodes if n["kind"] == "dynamic"]
    boundary_temp = float(boundary_node["fixed_temperature_c"])

    primary_input = heat_inputs[0]
    primary_node_id = primary_input["node_id"]

    # Initial temperatures
    node_temperatures: dict[str, list[float]] = {}
    for node in dynamic_nodes:
        if node.get("initial_temperature_c") is not None:
            node_temperatures[node["id"]] = [float(node["initial_temperature_c"])]
        else:
            node_temperatures[node["id"]] = [initial_temp]

    # Build static conductance contributions per dynamic node and to-boundary.
    dynamic_ids = [n["id"] for n in dynamic_nodes]
    index_of = {node_id: i for i, node_id in enumerate(dynamic_ids)}
    n_dyn = len(dynamic_ids)

    # G_ij for dynamic-dynamic conductances (symmetric), stored as dict for clarity.
    coupling: dict[str, dict[str, float]] = {nid: {} for nid in dynamic_ids}
    boundary_conductance: dict[str, float] = {nid: 0.0 for nid in dynamic_ids}
    for segment in segments:
        g = 1.0 / float(segment["resistance_k_per_w"])
        a, b = segment["from_node_id"], segment["to_node_id"]
        if a in index_of and b in index_of:
            coupling[a][b] = coupling[a].get(b, 0.0) + g
            coupling[b][a] = coupling[b].get(a, 0.0) + g
        else:
            dyn_id = a if a in index_of else b
            boundary_conductance[dyn_id] += g

    # Single-node time constants (informational): C_i / sum_j G_ij.  Useful as
    # a per-node sanity check, but for coupled networks the actual slowest
    # mode comes from the system eigenvalues — see _slowest_mode_tau below.
    time_constants_list = []
    for node in dynamic_nodes:
        nid = node["id"]
        sum_g = sum(coupling[nid].values()) + boundary_conductance[nid]
        tau = float(node["capacitance_j_per_k"]) / sum_g if sum_g > 0 else float("inf")
        time_constants_list.append(
            {
                "node_id": nid,
                "label": node.get("label", nid),
                "tau_s": tau,
                "capacitance_j_per_k": float(node["capacitance_j_per_k"]),
                "sum_conductance_w_per_k": sum_g,
            }
        )
    time_constants_list.sort(key=lambda x: x["tau_s"], reverse=True)

    capacitance = [float(n["capacitance_j_per_k"]) for n in dynamic_nodes]
    g_matrix = [[0.0 for _ in range(n_dyn)] for _ in range(n_dyn)]
    g_boundary_vec = [0.0 for _ in range(n_dyn)]
    for nid, idx in index_of.items():
        g_matrix[idx][idx] = sum(coupling[nid].values()) + boundary_conductance[nid]
        for other_id, g in coupling[nid].items():
            g_matrix[idx][index_of[other_id]] = -g
        g_boundary_vec[idx] = boundary_conductance[nid]

    # Slowest network mode via inverse iteration on the system matrix
    # A = C^{-1} G (smallest eigenvalue of A == largest eigenvalue of A^{-1}).
    slowest_tau = _slowest_mode_tau(g_matrix, capacitance)
    dominant_tau = slowest_tau if slowest_tau is not None else (
        time_constants_list[0]["tau_s"] if time_constants_list else 0.0
    )

    # Auto-extend the simulation window for step profiles whose user-supplied
    # duration is shorter than ~5 slow time constants — otherwise the plot can
    # truncate before the asymptote, leading users to read a falsely-OK peak
    # while the steady-state target sits above the limit.  Pulse and duty
    # cycles have a natural user-specified window and are not extended.
    auto_extension_warnings: list[str] = []
    duration = requested_duration
    if profile.get("type") == "step" and slowest_tau is not None and math.isfinite(slowest_tau):
        target_duration = 5.0 * slowest_tau
        if requested_duration < target_duration:
            duration = target_duration
            auto_extension_warnings.append(
                f"Simulation window extended from {requested_duration:.1f} s to "
                f"{duration:.1f} s (5x slowest time constant {slowest_tau:.1f} s) so "
                "the asymptote is visible in the temperature plot."
            )

    time_grid = _time_grid(duration, dt_input, profile)
    power_series = generate_power_profile(profile, time_grid)

    # Steady-state asymptote: G T_ss = Q + G_boundary * T_boundary.
    steady_rhs = [g_boundary_vec[i] * boundary_temp for i in range(n_dyn)]
    primary_idx = index_of[primary_node_id]
    # Steady-state heat input is the time-average of the profile.
    steady_q = _steady_state_power(profile)
    steady_rhs[primary_idx] += steady_q
    try:
        steady_T_vec = _solve_linear_system([row[:] for row in g_matrix], steady_rhs[:])
    except ValueError:
        steady_T_vec = [float("nan")] * n_dyn
    steady_state_temperatures = {
        nid: steady_T_vec[idx] for nid, idx in index_of.items()
    }
    steady_state_temperatures[boundary_node["id"]] = boundary_temp

    # Implicit-Euler time stepping.
    current_T = [node_temperatures[nid][0] for nid in dynamic_ids]
    for step in range(1, len(time_grid)):
        t_prev = time_grid[step - 1]
        t_now = time_grid[step]
        dt = t_now - t_prev
        if dt <= 0.0:
            for nid in dynamic_ids:
                node_temperatures[nid].append(node_temperatures[nid][-1])
            continue
        matrix = [[0.0 for _ in range(n_dyn)] for _ in range(n_dyn)]
        rhs = [0.0 for _ in range(n_dyn)]
        for nid, idx in index_of.items():
            c_over_dt = capacitance[idx] / dt
            matrix[idx][idx] = c_over_dt + sum(coupling[nid].values()) + boundary_conductance[nid]
            for other_id, g in coupling[nid].items():
                matrix[idx][index_of[other_id]] = -g
            heat_at_step = power_series[step] if nid == primary_node_id else 0.0
            rhs[idx] = c_over_dt * current_T[idx] + heat_at_step + boundary_conductance[nid] * boundary_temp
        next_T = _solve_linear_system(matrix, rhs)
        current_T = next_T
        for nid, idx in index_of.items():
            node_temperatures[nid].append(current_T[idx])

    # ---------- post-processing ---------- #
    limit_nodes = {
        n["id"]: float(n["max_temperature_c"]) for n in dynamic_nodes
        if n.get("max_temperature_c") is not None
    }
    if not limit_nodes:
        # Fall back to the primary heat-input node with no explicit limit; use +inf.
        limit_nodes = {primary_node_id: float("inf")}

    peak_temperature = -float("inf")
    peak_node_id = primary_node_id
    for nid, series in node_temperatures.items():
        local_peak = max(series)
        if local_peak > peak_temperature:
            peak_temperature = local_peak
            peak_node_id = nid

    time_to_limit: float | None = None
    limiting_node_id: str | None = None
    for nid, limit in limit_nodes.items():
        if not math.isfinite(limit):
            continue
        series = node_temperatures[nid]
        for i in range(1, len(series)):
            if series[i - 1] < limit <= series[i]:
                t_cross = _interpolate_crossing(
                    time_grid[i - 1], time_grid[i], series[i - 1], series[i], limit
                )
                if time_to_limit is None or t_cross < time_to_limit:
                    time_to_limit = t_cross
                    limiting_node_id = nid
                break

    final_temperature = node_temperatures[primary_node_id][-1]

    # Cyclic steady state: only meaningful for duty_cycle.
    cycle_summary: list[dict[str, Any]] = []
    cyclic_steady_state = False
    if profile.get("type") == "duty_cycle":
        cycle_period = float(profile.get("on_time_s", 0.0)) + float(profile.get("off_time_s", 0.0))
        if cycle_period > 0.0:
            n_cycles = int(math.floor(duration / cycle_period))
            ref_series = node_temperatures[primary_node_id]
            for c in range(n_cycles):
                t_start = c * cycle_period
                t_end = (c + 1) * cycle_period
                samples = [
                    ref_series[i] for i, t in enumerate(time_grid)
                    if t_start - 1e-9 <= t <= t_end + 1e-9
                ]
                if not samples:
                    continue
                cycle_summary.append(
                    {
                        "cycle": c + 1,
                        "t_start_s": t_start,
                        "t_end_s": t_end,
                        "peak_c": max(samples),
                        "min_c": min(samples),
                    }
                )
            if len(cycle_summary) >= 2:
                last = cycle_summary[-1]
                prev = cycle_summary[-2]
                cyclic_steady_state = (
                    abs(last["peak_c"] - prev["peak_c"]) < 0.05
                    and abs(last["min_c"] - prev["min_c"]) < 0.05
                )

    # Cooldown to target: first time after the heat-off transition where the
    # primary node drops below `target_temperature_c`. We use the last sampled
    # temperature minus 5 K as a sensible default if not specified.
    cooldown_target = time_settings.get("cooldown_target_c")
    cooldown_time: float | None = None
    if cooldown_target is not None:
        target = float(cooldown_target)
        ref_series = node_temperatures[primary_node_id]
        peak_index = max(range(len(ref_series)), key=lambda i: ref_series[i])
        for i in range(peak_index + 1, len(ref_series)):
            if ref_series[i] <= target:
                cooldown_time = time_grid[i] - time_grid[peak_index]
                break

    # Status determination.  Considers both the simulated peak and the
    # steady-state asymptote, so a too-short simulation window can't mask a
    # design that will eventually exceed its limit.
    status = _classify_status(
        peak_temperature=peak_temperature,
        limit_nodes=limit_nodes,
        node_temperatures=node_temperatures,
        steady_state_temperatures=steady_state_temperatures,
        cyclic_required=profile.get("type") == "duty_cycle",
        cyclic_steady_state=cyclic_steady_state,
        cycle_count=len(cycle_summary),
    )

    # Per-node and per-segment payloads.
    node_payload = []
    for node in dynamic_nodes:
        nid = node["id"]
        peak_local = max(node_temperatures[nid])
        limit_local = limit_nodes.get(nid)
        margin = (limit_local - peak_local) if (limit_local is not None and math.isfinite(limit_local)) else None
        steady_local = steady_state_temperatures.get(nid)
        node_payload.append(
            {
                "id": nid,
                "label": node.get("label", nid),
                "kind": "dynamic",
                "capacitance_j_per_k": float(node["capacitance_j_per_k"]),
                "max_temperature_c": limit_local if (limit_local is not None and math.isfinite(limit_local)) else None,
                "peak_temperature_c": peak_local,
                "final_temperature_c": node_temperatures[nid][-1],
                "steady_state_temperature_c": steady_local,
                "temperature_margin_c": margin,
            }
        )
    node_payload.append(
        {
            "id": boundary_node["id"],
            "label": boundary_node.get("label", boundary_node["id"]),
            "kind": "boundary",
            "fixed_temperature_c": boundary_temp,
        }
    )

    segment_payload = []
    capacitance_lookup = {n["id"]: float(n["capacitance_j_per_k"]) for n in dynamic_nodes}
    for segment in segments:
        r = float(segment["resistance_k_per_w"])
        a, b = segment["from_node_id"], segment["to_node_id"]
        c_a = capacitance_lookup.get(a)
        c_b = capacitance_lookup.get(b)
        c_eff = None
        if c_a is not None and c_b is not None:
            c_eff = c_a * c_b / (c_a + c_b)
        elif c_a is not None:
            c_eff = c_a
        elif c_b is not None:
            c_eff = c_b
        tau_segment = r * c_eff if c_eff is not None else None
        segment_payload.append(
            {
                "id": segment.get("id", f"{a}__{b}"),
                "label": segment.get("label", f"{a} -> {b}"),
                "from_node_id": a,
                "to_node_id": b,
                "resistance_k_per_w": r,
                "tau_s": tau_segment,
            }
        )

    # Diagnosis & recommendations
    diagnosis = _build_diagnosis(
        time_constants=time_constants_list,
        peak_temperature=peak_temperature,
        peak_node_id=peak_node_id,
        time_to_limit=time_to_limit,
        cyclic_steady_state=cyclic_steady_state,
        profile_type=profile.get("type"),
    )
    recommendations = _build_recommendations(
        status=status,
        time_constants=time_constants_list,
        segments=segment_payload,
        time_to_limit=time_to_limit,
        duration=duration,
        dominant_tau=dominant_tau,
    )

    primary_steady_T = steady_state_temperatures.get(primary_node_id)
    summary = {
        "status": status,
        "time_to_limit_s": time_to_limit,
        "peak_temperature_c": peak_temperature,
        "peak_node_id": peak_node_id,
        "final_temperature_c": final_temperature,
        "steady_state_temperature_c": primary_steady_T,
        "steady_state_node_id": primary_node_id,
        "cyclic_steady_state_reached": cyclic_steady_state,
        "cooldown_time_to_target_s": cooldown_time,
        "dominant_time_constant_s": dominant_tau,
        "slowest_mode_tau_s": slowest_tau,
        "limiting_node_id": limiting_node_id,
        "requested_duration_s": requested_duration,
        "simulated_duration_s": duration,
        "auto_extended_duration": duration > requested_duration + 1e-9,
    }

    subst_governing = (
        "C_i \\frac{dT_i}{dt} = Q_i(t) + \\sum_j \\frac{T_j - T_i}{R_{ij}}"
        f"\\quad\\text{{(with {n_dyn} dynamic node{'s' if n_dyn != 1 else ''})}}"
    )

    return {
        "status": status,
        "summary": summary,
        "series": {
            "time_s": list(time_grid),
            "power_w": list(power_series),
            "node_temperatures_c": {nid: list(series) for nid, series in node_temperatures.items()},
        },
        "nodes": node_payload,
        "segments": segment_payload,
        "time_constants": time_constants_list,
        "cycle_summary": cycle_summary,
        "diagnosis": diagnosis,
        "recommendations": recommendations,
        "warnings": list(validation["warnings"]) + auto_extension_warnings,
        "errors": [],
        "subst_governing": subst_governing,
    }


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _steady_state_power(profile: dict[str, Any]) -> float:
    """Time-average heat input for the asymptote calculation."""

    ptype = profile.get("type")
    if ptype == "step":
        return float(profile.get("power_w", 0.0))
    if ptype == "pulse":
        # Pulse asymptote is the cooldown power (hold value after the pulse).
        return float(profile.get("cooldown_power_w", 0.0))
    if ptype == "duty_cycle":
        on_p = float(profile.get("on_power_w", 0.0))
        off_p = float(profile.get("off_power_w", 0.0))
        on_t = float(profile.get("on_time_s", 0.0))
        off_t = float(profile.get("off_time_s", 0.0))
        period = on_t + off_t
        if period <= 0.0:
            return on_p
        return (on_p * on_t + off_p * off_t) / period
    return 0.0


def _slowest_mode_tau(
    g_matrix: list[list[float]], capacitance: list[float]
) -> float | None:
    """Return the slowest decay time constant of the linear system C dT/dt = -G T + b.

    The system matrix is ``A = C^{-1} G``.  We compute ``tau_slow = 1 / lambda_min(A)``
    via inverse iteration: power iteration on ``A^{-1} = G^{-1} C`` finds the
    largest eigenvalue, which equals ``1 / lambda_min``.
    Returns ``None`` for empty or singular systems.
    """

    n = len(capacitance)
    if n == 0:
        return None
    # Start with an arbitrary non-orthogonal vector.
    x = [1.0 / math.sqrt(n) for _ in range(n)]
    last_lambda = 0.0
    for _ in range(80):
        # y = C x  (diagonal multiply)
        y = [capacitance[i] * x[i] for i in range(n)]
        # Solve G z = y  =>  z = G^{-1} C x = A^{-1} x
        try:
            z = _solve_linear_system([row[:] for row in g_matrix], y[:])
        except ValueError:
            return None
        norm = math.sqrt(sum(v * v for v in z))
        if norm == 0.0 or not math.isfinite(norm):
            return None
        z = [v / norm for v in z]
        last_lambda = norm
        # Convergence: eigenvector stable
        diff = sum((z[i] - x[i]) ** 2 for i in range(n))
        x = z
        if diff < 1e-14:
            break
    if last_lambda <= 0.0 or not math.isfinite(last_lambda):
        return None
    return float(last_lambda)


def _classify_status(
    peak_temperature: float,
    limit_nodes: dict[str, float],
    node_temperatures: dict[str, list[float]],
    steady_state_temperatures: dict[str, float],
    cyclic_required: bool,
    cyclic_steady_state: bool,
    cycle_count: int,
) -> str:
    """Map the simulation outcome to an overall status string."""

    finite_limits = {nid: lim for nid, lim in limit_nodes.items() if math.isfinite(lim)}
    if finite_limits:
        for nid, limit in finite_limits.items():
            local_peak = max(node_temperatures[nid])
            steady = steady_state_temperatures.get(nid)
            if local_peak > limit:
                return "unacceptable"
            if steady is not None and math.isfinite(steady) and steady > limit:
                # Simulation stopped short, but the asymptote crosses the limit.
                return "unacceptable"
        # 5 K guard band, similar to plate-fin tool's marginal band.
        for nid, limit in finite_limits.items():
            local_peak = max(node_temperatures[nid])
            steady = steady_state_temperatures.get(nid)
            ref = max(local_peak, steady) if (steady is not None and math.isfinite(steady)) else local_peak
            if limit - ref < 5.0:
                if cyclic_required and cycle_count >= 2 and not cyclic_steady_state:
                    return "not_converged"
                return "marginal"
    if cyclic_required and cycle_count >= 2 and not cyclic_steady_state:
        return "not_converged"
    return "acceptable"


def _build_diagnosis(
    time_constants: list[dict[str, Any]],
    peak_temperature: float,
    peak_node_id: str,
    time_to_limit: float | None,
    cyclic_steady_state: bool,
    profile_type: str | None,
) -> list[str]:
    out: list[str] = []
    if time_constants:
        slowest = time_constants[0]
        out.append(
            f"Slowest time constant is {slowest['tau_s']:.1f} s at node "
            f"'{slowest['label']}' (C={slowest['capacitance_j_per_k']:.1f} J/K)."
        )
    if time_to_limit is not None:
        out.append(
            f"Limit is reached at t = {time_to_limit:.2f} s on node '{peak_node_id}'."
        )
    elif peak_temperature > -float("inf"):
        out.append(
            f"Peak temperature stays at {peak_temperature:.2f} C on node '{peak_node_id}'."
        )
    if profile_type == "duty_cycle":
        out.append(
            "Duty cycle reached cyclic steady state."
            if cyclic_steady_state
            else "Duty cycle has NOT reached cyclic steady state in the simulated window — temperatures are still walking up between cycles."
        )
    return out


def _build_recommendations(
    status: str,
    time_constants: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    time_to_limit: float | None,
    duration: float,
    dominant_tau: float,
) -> list[str]:
    out: list[str] = []
    if status == "unacceptable":
        if dominant_tau > 0 and duration < 3 * dominant_tau:
            out.append(
                "The system has not reached steady state — adding thermal mass (capacitance) buys runtime, but reducing thermal resistance changes the steady asymptote. If the load is brief, prioritize mass; if continuous, prioritize lower resistance."
            )
        else:
            out.append(
                "Temperature limit exceeded at steady state. Resistance reduction is the primary lever; added mass only delays the same outcome."
            )
        if segments:
            biggest = max(segments, key=lambda s: s["resistance_k_per_w"])
            out.append(
                f"Largest resistance segment is '{biggest['label']}' at"
                f" {biggest['resistance_k_per_w']:.3f} K/W — start here."
            )
    elif status == "marginal":
        out.append(
            "Design is within ~5 K of the temperature limit. Add margin by lowering one resistance or adding sink mass."
        )
    elif status == "not_converged":
        out.append(
            "Duty cycle has not stabilized — extend simulation duration or expect more thermal walk-up."
        )
    else:
        out.append("Thermal budget is met under the modeled assumptions.")
    return out
