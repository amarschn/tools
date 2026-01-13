"""Reliability and MTBF calculations."""

from __future__ import annotations

import math
from typing import Any


def _format_value(value: float, precision: int = 4) -> str:
    if not math.isfinite(value):
        return "inf"
    return f"{value:.{precision}g}"


def _validate_lengths(*arrays: list[Any]) -> None:
    if not arrays:
        return
    length = len(arrays[0])
    if any(len(arr) != length for arr in arrays):
        raise ValueError("Component input arrays must have the same length.")


def _system_reliability_at_time(
    failure_rates: list[float],
    series_counts: list[int],
    parallel_counts: list[int],
    time_hours: float,
) -> float:
    reliability = 1.0
    for failure_rate, series_count, parallel_count in zip(
        failure_rates, series_counts, parallel_counts
    ):
        r_single = math.exp(-failure_rate * time_hours)
        r_parallel = 1.0 - (1.0 - r_single) ** parallel_count
        r_block = r_parallel ** series_count
        reliability *= r_block
    return reliability


def analyze_reliability(
    component_names: list[str],
    component_mtbf_hours: list[float],
    component_series_count: list[int],
    component_parallel_count: list[int],
    mission_time_hours: float,
    target_system_reliability: float | None = None,
    allocation_component_count: int | None = None,
) -> dict[str, Any]:
    """
    Estimate system reliability from component MTBF values.

    Uses an exponential (constant failure rate) model for each component.
    Components are treated as series blocks, with optional parallel
    redundancy within each block.

    ---Parameters---
    component_names : list[str]
        Component labels used for reporting. Must align with the other
        component input arrays.
    component_mtbf_hours : list[float]
        Mean time between failures for each component (hours). Values
        must be positive.
    component_series_count : list[int]
        Number of identical components in series for each block. Use 1
        for a single component.
    component_parallel_count : list[int]
        Parallel redundancy count for each block. Use 1 for no redundancy.
    mission_time_hours : float
        Mission time for the reliability evaluation (hours).
    target_system_reliability : float | None
        Optional target system reliability for equal allocation (0 to 1).
    allocation_component_count : int | None
        Number of identical series components for allocation.

    ---Returns---
    system_reliability : float
        System reliability at the mission time (0 to 1).
    equivalent_failure_rate_per_hour : float
        Effective failure rate derived from system reliability (1/hour).
    equivalent_mtbf_hours : float
        Equivalent MTBF based on the effective failure rate (hours).
    component_blocks : list[dict]
        Per-block summary with failure rate and reliability details.
    reliability_curve : dict
        Time history for the system reliability curve.
    allocation_performed : bool
        True when allocation inputs are provided.
    allocation_required_reliability : float | None
        Required component reliability for the allocation case.
    allocation_required_failure_rate_per_hour : float | None
        Required failure rate for the allocation case (1/hour).
    allocation_required_mtbf_hours : float | None
        Required MTBF for the allocation case (hours).

    ---LaTeX---
    Equation_1 = R = e^{-\\lambda t}
    Equation_2 = R_{parallel} = 1 - (1 - R)^n
    Equation_3 = R_{sys} = \\prod R_i
    Equation_4 = \\lambda_{eq} = -\\frac{\\ln R_{sys}}{t}
    Equation_5 = MTBF_{eq} = 1/\\lambda_{eq}
    Equation_6 = R_{comp} = R_{sys}^{1/N}
    Equation_7 = \\lambda_{req} = -\\frac{\\ln R_{comp}}{t}
    Equation_8 = MTBF_{req} = 1/\\lambda_{req}
    """
    if not math.isfinite(mission_time_hours) or mission_time_hours <= 0:
        raise ValueError("Mission time must be greater than zero.")

    if not component_mtbf_hours:
        raise ValueError("At least one component is required.")

    _validate_lengths(
        component_names,
        component_mtbf_hours,
        component_series_count,
        component_parallel_count,
    )

    if any((not math.isfinite(mtbf)) or mtbf <= 0 for mtbf in component_mtbf_hours):
        raise ValueError("Component MTBF values must be greater than zero.")

    if any(count < 1 for count in component_series_count):
        raise ValueError("Series counts must be 1 or greater.")

    if any(count < 1 for count in component_parallel_count):
        raise ValueError("Parallel counts must be 1 or greater.")

    if target_system_reliability is None and allocation_component_count is not None:
        raise ValueError("Provide a target system reliability for allocation.")

    if target_system_reliability is not None:
        if not math.isfinite(target_system_reliability):
            raise ValueError("Target system reliability must be a finite number.")
        if target_system_reliability <= 0 or target_system_reliability > 1:
            raise ValueError("Target system reliability must be between 0 and 1.")
        if allocation_component_count is None or allocation_component_count < 1:
            raise ValueError("Allocation component count must be 1 or greater.")

    failure_rates = [1.0 / mtbf for mtbf in component_mtbf_hours]

    component_blocks: list[dict[str, Any]] = []
    system_reliability = 1.0
    for idx, (name, mtbf, series_count, parallel_count, failure_rate) in enumerate(
        zip(
            component_names,
            component_mtbf_hours,
            component_series_count,
            component_parallel_count,
            failure_rates,
        )
    ):
        label = (
            name.strip()
            if isinstance(name, str) and name.strip()
            else f"Component {idx + 1}"
        )
        r_single = math.exp(-failure_rate * mission_time_hours)
        r_parallel = 1.0 - (1.0 - r_single) ** parallel_count
        r_block = r_parallel ** series_count
        system_reliability *= r_block

        component_blocks.append(
            {
                "name": label,
                "mtbf_hours": mtbf,
                "series_count": series_count,
                "parallel_count": parallel_count,
                "failure_rate_per_hour": failure_rate,
                "reliability_single": r_single,
                "reliability_parallel": r_parallel,
                "reliability_block": r_block,
            }
        )

    if system_reliability <= 0:
        equivalent_failure_rate = math.inf
    else:
        equivalent_failure_rate = -math.log(system_reliability) / mission_time_hours

    if equivalent_failure_rate == 0 or math.isinf(equivalent_failure_rate):
        equivalent_mtbf = math.inf
    else:
        equivalent_mtbf = 1.0 / equivalent_failure_rate

    curve_points = 60
    curve_times = [
        mission_time_hours * i / curve_points for i in range(curve_points + 1)
    ]
    curve_reliabilities = [
        _system_reliability_at_time(
            failure_rates,
            component_series_count,
            component_parallel_count,
            time_point,
        )
        for time_point in curve_times
    ]

    reliability_curve = {
        "time_hours": curve_times,
        "system_reliability": curve_reliabilities,
    }

    displayed_blocks = [
        _format_value(block["reliability_block"]) for block in component_blocks
    ]
    if len(displayed_blocks) > 6:
        displayed_blocks = displayed_blocks[:5] + ["..."]
    product_chain = " * ".join(displayed_blocks) if displayed_blocks else "1"

    subst_system_reliability = (
        f"R_{{sys}} = {product_chain} = {_format_value(system_reliability)}"
    )
    subst_equivalent_failure_rate = (
        "\\lambda_{eq} = -\\frac{\\ln R_{sys}}{t} = "
        f"-\\frac{{\\ln({_format_value(system_reliability)})}}{{"
        f"{_format_value(mission_time_hours)}\\,\\text{{hr}}}}"
        f" = {_format_value(equivalent_failure_rate)}\\,\\text{{1/hr}}"
    )
    subst_equivalent_mtbf = (
        "MTBF_{eq} = \\frac{1}{\\lambda_{eq}} = "
        f"\\frac{{1}}{{{_format_value(equivalent_failure_rate)}}}"
        f" = {_format_value(equivalent_mtbf)}\\,\\text{{hr}}"
    )

    allocation_performed = False
    allocation_required_reliability = None
    allocation_required_failure_rate = None
    allocation_required_mtbf = None
    subst_allocation_required_reliability = ""
    subst_allocation_required_failure_rate = ""
    subst_allocation_required_mtbf = ""

    if target_system_reliability is not None and allocation_component_count is not None:
        allocation_performed = True
        allocation_required_reliability = target_system_reliability ** (
            1.0 / allocation_component_count
        )
        allocation_required_failure_rate = (
            -math.log(allocation_required_reliability) / mission_time_hours
            if allocation_required_reliability > 0
            else math.inf
        )
        if allocation_required_failure_rate == 0 or math.isinf(
            allocation_required_failure_rate
        ):
            allocation_required_mtbf = math.inf
        else:
            allocation_required_mtbf = 1.0 / allocation_required_failure_rate

        subst_allocation_required_reliability = (
            "R_{comp} = R_{sys}^{1/N} = "
            f"{_format_value(target_system_reliability)}^{{1/{allocation_component_count}}}"
            f" = {_format_value(allocation_required_reliability)}"
        )
        subst_allocation_required_failure_rate = (
            "\\lambda_{req} = -\\frac{\\ln R_{comp}}{t} = "
            f"-\\frac{{\\ln({_format_value(allocation_required_reliability)})}}{{"
            f"{_format_value(mission_time_hours)}\\,\\text{{hr}}}}"
            f" = {_format_value(allocation_required_failure_rate)}\\,\\text{{1/hr}}"
        )
        subst_allocation_required_mtbf = (
            "MTBF_{req} = \\frac{1}{\\lambda_{req}} = "
            f"\\frac{{1}}{{{_format_value(allocation_required_failure_rate)}}}"
            f" = {_format_value(allocation_required_mtbf)}\\,\\text{{hr}}"
        )

    return {
        "system_reliability": system_reliability,
        "equivalent_failure_rate_per_hour": equivalent_failure_rate,
        "equivalent_mtbf_hours": equivalent_mtbf,
        "component_blocks": component_blocks,
        "reliability_curve": reliability_curve,
        "allocation_performed": allocation_performed,
        "allocation_required_reliability": allocation_required_reliability,
        "allocation_required_failure_rate_per_hour": allocation_required_failure_rate,
        "allocation_required_mtbf_hours": allocation_required_mtbf,
        "subst_system_reliability": subst_system_reliability,
        "subst_equivalent_failure_rate_per_hour": subst_equivalent_failure_rate,
        "subst_equivalent_mtbf_hours": subst_equivalent_mtbf,
        "subst_allocation_required_reliability": subst_allocation_required_reliability,
        "subst_allocation_required_failure_rate_per_hour": subst_allocation_required_failure_rate,
        "subst_allocation_required_mtbf_hours": subst_allocation_required_mtbf,
    }
