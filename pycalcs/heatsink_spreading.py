"""
2D steady-state base-plane spreading solver for plate-fin heatsinks.

Solves in-plane conduction on a rectangular base plate with:
- localized rectangular heat sources,
- a distributed sink term derived from the global plate-fin solver,
- adiabatic outer edges (heat rejection is captured by the sink term).

Uses Gauss-Seidel iteration with successive over-relaxation (SOR).

Reference architecture:
    heatsinks.py  ->  analyze_plate_fin_heatsink()  (global R_sink)
    heatsinks.py  ->  analyze_heatsink_spreading_view()  (orchestrator)
    heatsink_spreading.py  ->  solve_base_spreading_field()  (this module)
"""

from __future__ import annotations

from typing import Any, Dict, List


def _source_cell_overlap(
    cell_x0: float,
    cell_x1: float,
    cell_y0: float,
    cell_y1: float,
    src_x0: float,
    src_x1: float,
    src_y0: float,
    src_y1: float,
) -> float:
    """Return the overlap area between a grid cell and a source rectangle."""
    ox = max(0.0, min(cell_x1, src_x1) - max(cell_x0, src_x0))
    oy = max(0.0, min(cell_y1, src_y1) - max(cell_y0, src_y0))
    return ox * oy


def solve_base_spreading_field(
    *,
    base_length: float,
    base_width: float,
    base_thickness: float,
    material_conductivity: float,
    ambient_temperature: float,
    sink_thermal_resistance: float,
    sources: List[Dict[str, float]],
    grid_x: int = 41,
    grid_y: int = 25,
    omega: float = 1.4,
    max_iterations: int = 4000,
    convergence_threshold: float = 1e-4,
) -> Dict[str, Any]:
    """
    Solve the 2D base-plane temperature field for localized heat sources.

    Parameters
    ----------
    base_length : float
        Base plate dimension in the flow direction (m).
    base_width : float
        Base plate dimension across the fin array (m).
    base_thickness : float
        Base plate thickness (m).
    material_conductivity : float
        Thermal conductivity of the base material (W/m·K).
    ambient_temperature : float
        Ambient air temperature (°C).
    sink_thermal_resistance : float
        Global sink-to-ambient thermal resistance from the plate-fin solver (K/W).
    sources : list of dict
        Each source has keys: id, x_center, y_center, length, width, power,
        junction_to_case_resistance, interface_resistance.
    grid_x : int
        Number of cells in the x (length) direction.
    grid_y : int
        Number of cells in the y (width) direction.
    omega : float
        SOR relaxation factor (1.0 = Gauss-Seidel, >1.0 = over-relaxation).
    max_iterations : int
        Maximum solver iterations.
    convergence_threshold : float
        Stop when the maximum cell temperature update is below this (K).

    Returns
    -------
    dict
        Field data, summary metrics, centerline profiles, and source summaries.
    """
    if base_length <= 0 or base_width <= 0 or base_thickness <= 0:
        raise ValueError("Base dimensions must be positive.")
    if material_conductivity <= 0:
        raise ValueError("Material conductivity must be positive.")
    if sink_thermal_resistance <= 0:
        raise ValueError("Sink thermal resistance must be positive for spreading solve.")

    dx = base_length / grid_x
    dy = base_width / grid_y
    cell_area = dx * dy
    total_area = base_length * base_width

    # In-plane conductances between neighbours.
    # Gx: conductance in the x direction between adjacent cells.
    # Gy: conductance in the y direction between adjacent cells.
    Gx = material_conductivity * base_thickness * dy / dx
    Gy = material_conductivity * base_thickness * dx / dy

    # Distributed sink conductance per cell (uniform weighting).
    G_sink_total = 1.0 / sink_thermal_resistance
    G_sink_cell = G_sink_total * cell_area / total_area

    # Build source heat input grid Q[i][j] (W per cell).
    Q = [[0.0] * grid_y for _ in range(grid_x)]
    assumptions: List[str] = [
        "2D base-plane conduction model — fins are not individually meshed.",
        "Heat rejection represented as a distributed sink term derived from the global solver.",
        "Adiabatic outer edges — edge convection is not modeled separately.",
    ]

    source_rects: List[Dict[str, Any]] = []
    total_source_power = 0.0
    effective_power: Dict[str, float] = {}  # source id -> clipped power

    for src in sources:
        s_len = src.get("length", 0.0)
        s_wid = src.get("width", 0.0)
        s_power = src.get("power", 0.0)
        if s_len <= 0 or s_wid <= 0 or s_power <= 0:
            continue

        s_xc = src.get("x_center", base_length / 2.0)
        s_yc = src.get("y_center", base_width / 2.0)
        src_x0 = s_xc - s_len / 2.0
        src_x1 = s_xc + s_len / 2.0
        src_y0 = s_yc - s_wid / 2.0
        src_y1 = s_yc + s_wid / 2.0

        # Clamp to base boundary.
        clipped = False
        if src_x0 < 0 or src_x1 > base_length or src_y0 < 0 or src_y1 > base_width:
            clipped = True
            src_x0 = max(src_x0, 0.0)
            src_x1 = min(src_x1, base_length)
            src_y0 = max(src_y0, 0.0)
            src_y1 = min(src_y1, base_width)

        clipped_area = (src_x1 - src_x0) * (src_y1 - src_y0)
        if clipped_area <= 0:
            continue

        heat_flux = s_power / (s_len * s_wid)  # W/m² based on original source area
        clipped_power = heat_flux * clipped_area
        if clipped:
            assumptions.append(
                f"Source '{src.get('id', '?')}' extends beyond base edge; "
                f"only the overlapping region contributes heat "
                f"({clipped_power:.2f} W of {s_power:.2f} W deposited)."
            )

        src_id = src.get("id", "source")
        effective_power[src_id] = clipped_power
        total_source_power += clipped_power

        source_rects.append({
            "id": src_id,
            "x0": src_x0,
            "x1": src_x1,
            "y0": src_y0,
            "y1": src_y1,
        })

        for i in range(grid_x):
            cx0 = i * dx
            cx1 = (i + 1) * dx
            for j in range(grid_y):
                cy0 = j * dy
                cy1 = (j + 1) * dy
                overlap = _source_cell_overlap(cx0, cx1, cy0, cy1, src_x0, src_x1, src_y0, src_y1)
                if overlap > 0:
                    Q[i][j] += heat_flux * overlap

    # Initialize temperature field to the uniform-base analytical estimate.
    # This gives a much better starting point than ambient, especially when
    # in-plane conductance >> sink conductance (typical for aluminum).
    T_uniform = ambient_temperature + total_source_power * sink_thermal_resistance
    T = [[T_uniform] * grid_y for _ in range(grid_x)]

    # Compute optimal SOR relaxation factor for the grid.
    # For a 2D problem, ω_opt ≈ 2 / (1 + sin(π / max(Nx, Ny))).
    import math as _math
    n_max = max(grid_x, grid_y)
    omega_opt = 2.0 / (1.0 + _math.sin(_math.pi / n_max))
    omega_use = min(omega, omega_opt)  # Use the lesser of user-supplied or optimal

    # Gauss-Seidel with SOR.
    converged = False
    iterations = 0
    max_update = 0.0

    for it in range(max_iterations):
        max_update = 0.0
        for i in range(grid_x):
            for j in range(grid_y):
                neighbor_sum = 0.0
                neighbor_G = 0.0

                # East
                if i < grid_x - 1:
                    neighbor_sum += Gx * T[i + 1][j]
                    neighbor_G += Gx
                # West
                if i > 0:
                    neighbor_sum += Gx * T[i - 1][j]
                    neighbor_G += Gx
                # North
                if j < grid_y - 1:
                    neighbor_sum += Gy * T[i][j + 1]
                    neighbor_G += Gy
                # South
                if j > 0:
                    neighbor_sum += Gy * T[i][j - 1]
                    neighbor_G += Gy

                denom = neighbor_G + G_sink_cell
                T_new = (neighbor_sum + G_sink_cell * ambient_temperature + Q[i][j]) / denom
                T_relaxed = T[i][j] + omega_use * (T_new - T[i][j])

                update = abs(T_relaxed - T[i][j])
                if update > max_update:
                    max_update = update

                T[i][j] = T_relaxed

        iterations = it + 1
        if max_update < convergence_threshold:
            converged = True
            break

    if not converged:
        raise ValueError(
            f"Spreading solver did not converge after {max_iterations} iterations "
            f"(max update = {max_update:.2e} K). Check inputs."
        )

    # Post-processing.
    # Coordinate arrays (cell centers).
    x_coords = [dx * (i + 0.5) for i in range(grid_x)]
    y_coords = [dy * (j + 0.5) for j in range(grid_y)]

    # Temperature statistics.
    all_temps = [T[i][j] for i in range(grid_x) for j in range(grid_y)]
    mean_temp = sum(all_temps) / len(all_temps)
    peak_temp = max(all_temps)
    min_temp = min(all_temps)

    # Rise grid.
    rise_grid = [
        [T[i][j] - ambient_temperature for j in range(grid_y)]
        for i in range(grid_x)
    ]

    # Energy balance check.
    total_sink_heat = sum(
        G_sink_cell * (T[i][j] - ambient_temperature)
        for i in range(grid_x) for j in range(grid_y)
    )
    energy_balance_error = abs(total_sink_heat - total_source_power) / max(total_source_power, 1e-12)

    # Centerline profiles — cut through the first source center if available,
    # otherwise fall back to the geometric center of the base.
    if sources:
        src0 = sources[0]
        cut_y_coord = src0.get("y_center", base_width / 2.0)
        cut_x_coord = src0.get("x_center", base_length / 2.0)
        # Find nearest grid index for the y-cut (row for x-centerline)
        center_j = min(range(grid_y), key=lambda j: abs(y_coords[j] - cut_y_coord))
        # Find nearest grid index for the x-cut (column for y-centerline)
        center_i = min(range(grid_x), key=lambda i: abs(x_coords[i] - cut_x_coord))
    else:
        center_j = grid_y // 2
        center_i = grid_x // 2

    centerline_x_temp = [T[i][center_j] for i in range(grid_x)]
    centerline_y_temp = [T[center_i][j] for j in range(grid_y)]

    # Source summaries.
    source_summaries: List[Dict[str, Any]] = []
    for s_idx, src in enumerate(sources):
        s_len = src.get("length", 0.0)
        s_wid = src.get("width", 0.0)
        if s_len <= 0 or s_wid <= 0:
            continue

        s_xc = src.get("x_center", base_length / 2.0)
        s_yc = src.get("y_center", base_width / 2.0)
        src_x0 = max(s_xc - s_len / 2.0, 0.0)
        src_x1 = min(s_xc + s_len / 2.0, base_length)
        src_y0 = max(s_yc - s_wid / 2.0, 0.0)
        src_y1 = min(s_yc + s_wid / 2.0, base_width)

        # Collect temperatures in source footprint.
        src_temps = []
        src_weights = []
        for i in range(grid_x):
            cx0 = i * dx
            cx1 = (i + 1) * dx
            for j in range(grid_y):
                cy0 = j * dy
                cy1 = (j + 1) * dy
                overlap = _source_cell_overlap(cx0, cx1, cy0, cy1, src_x0, src_x1, src_y0, src_y1)
                if overlap > 0:
                    src_temps.append(T[i][j])
                    src_weights.append(overlap)

        if src_temps:
            total_w = sum(src_weights)
            avg_base = sum(t * w for t, w in zip(src_temps, src_weights)) / total_w
            peak_base = max(src_temps)
        else:
            avg_base = ambient_temperature
            peak_base = ambient_temperature

        r_jc = src.get("junction_to_case_resistance", 0.0)
        r_cs = src.get("interface_resistance", 0.0)
        src_id = src.get("id", f"source_{s_idx + 1}")
        eff_power = effective_power.get(src_id, src.get("power", 0.0))

        source_summaries.append({
            "id": src_id,
            "power": eff_power,
            "avg_base_temperature": avg_base,
            "peak_base_temperature": peak_base,
            "avg_case_temperature": avg_base + eff_power * r_cs,
            "avg_junction_temperature": avg_base + eff_power * (r_cs + r_jc),
            "peak_junction_temperature_estimate": peak_base + eff_power * (r_cs + r_jc),
        })

    return {
        "x_coords": x_coords,
        "y_coords": y_coords,
        "temperature_grid": T,
        "temperature_rise_grid": rise_grid,
        "mean_base_temperature": mean_temp,
        "peak_base_temperature": peak_temp,
        "min_base_temperature": min_temp,
        "max_spreading_delta": peak_temp - mean_temp,
        "energy_balance_error": energy_balance_error,
        "iterations": iterations,
        "converged": converged,
        "sink_conductance_total": G_sink_total,
        "source_summaries": source_summaries,
        "centerline_x": {
            "coords": x_coords,
            "temperature": centerline_x_temp,
            "cut_y": y_coords[center_j],
        },
        "centerline_y": {
            "coords": y_coords,
            "temperature": centerline_y_temp,
            "cut_x": x_coords[center_i],
        },
        "source_rectangles": source_rects,
        "assumptions": assumptions,
    }
