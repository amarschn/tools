"""
Cost and production planning utilities for manufacturing-focused tools.

This module centralises financial simulations that support make-versus-buy
decisions for additive manufacturing equipment.
"""

from __future__ import annotations

import json
import math
import random
from typing import Dict, List


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp ``value`` to the inclusive range ``[lower, upper]``."""
    return max(lower, min(upper, value))


def _percentile(samples: List[float], fraction: float) -> float:
    """Return the requested quantile using linear interpolation."""
    if not samples:
        return math.nan

    sorted_samples = sorted(samples)
    index = (len(sorted_samples) - 1) * fraction
    lower_idx = math.floor(index)
    upper_idx = math.ceil(index)

    if lower_idx == upper_idx:
        return sorted_samples[int(index)]

    lower_value = sorted_samples[lower_idx]
    upper_value = sorted_samples[upper_idx]

    return lower_value + (upper_value - lower_value) * (index - lower_idx)


def _sample_uptime(mean: float, std_dev: float) -> float:
    """
    Draw an uptime sample bounded in ``[0, 1]`` using a beta or truncated normal.
    """
    mean = _clamp(mean, 1e-6, 1.0 - 1e-6)
    std_dev = max(std_dev, 1e-6)

    variance = std_dev * std_dev
    max_variance = mean * (1.0 - mean)

    if variance < max_variance:
        alpha_beta = (mean * (1.0 - mean) / variance) - 1.0
        alpha = mean * alpha_beta
        beta = (1.0 - mean) * alpha_beta
        if alpha > 0 and beta > 0:
            return _clamp(random.betavariate(alpha, beta), 0.0, 1.0)

    sample = random.gauss(mean, std_dev)
    return _clamp(sample, 0.0, 1.0)


def _serialise_value(value: float) -> float | None:
    """Convert non-finite floating point values to ``None`` for JSON encoding."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def simulate_mjf_breakeven(
    purchase_price: float,
    machine_counts: str,
    analysis_years: int,
    simulations: int,
    annual_demand_mean: float,
    annual_demand_std: float,
    max_builds_per_machine: float,
    uptime_mean: float,
    uptime_std: float,
    variable_internal_cost: float,
    external_cost_per_build: float,
    fixed_annual_cost_per_machine: float,
    downtime_event_probability: float,
    downtime_event_duration_fraction: float,
    operator_issue_probability: float,
    operator_issue_duration_fraction: float,
    print_time_hours: float,
    cooldown_time_hours: float,
    operator_hours_per_build: float,
    operator_hours_available_per_year: float,
    external_turnaround_days: float,
    support_capital_cost: float,
    support_annual_operating_cost: float,
    hybrid_outsource_fraction: float,
) -> Dict[str, float | str]:
    """
    Run a Monte Carlo buy-versus-outsource study for MJF printer investments.

    The routine compares the annualised savings realised by operating one or
    more Multi Jet Fusion (MJF) printers against the baseline of outsourcing all
    builds. Demand and uptime are sampled stochastically so the model captures
    the impact of variability, unplanned downtime, and operator-driven losses.

    ---Parameters---
    purchase_price : float
        Capital expenditure for a single printer (USD). Applied once per machine
        at the beginning of the study horizon.
    machine_counts : str
        Comma-separated list of machine counts to evaluate (e.g., ``"1,2,3"``).
    analysis_years : int
        Number of operating years to simulate. Used to cap the break-even search.
    simulations : int
        Number of Monte Carlo trials. Higher counts narrow the confidence
        interval on the reported statistics.
    annual_demand_mean : float
        Expected number of build jobs required per year across the product mix.
    annual_demand_std : float
        Standard deviation of the annual demand distribution (jobs/year).
    max_builds_per_machine : float
        Theoretical maximum jobs a machine can process annually at 100 % uptime.
    uptime_mean : float
        Mean operational availability (0–1). Captures planned utilisation.
    uptime_std : float
        Standard deviation of availability (0–1). Expressed as a fraction.
    variable_internal_cost : float
        Variable cost per internally produced build (materials + labour) in USD.
    external_cost_per_build : float
        Outsourcing cost per build in USD. Represents the external supplier rate.
    fixed_annual_cost_per_machine : float
        Recurring annual cost per machine (maintenance, operators, facility) in USD.
    downtime_event_probability : float
        Probability that a major downtime event occurs in a given year (0–1).
    downtime_event_duration_fraction : float
        Fractional uptime loss when a major downtime event happens (0–1).
    operator_issue_probability : float
        Probability that operator constraints impose additional downtime (0–1).
    operator_issue_duration_fraction : float
        Fractional uptime loss when an operator issue occurs (0–1).
    print_time_hours : float
        Average active print time required for one build (hours).
    cooldown_time_hours : float
        Additional cooldown or depowdering time that blocks the machine (hours).
    operator_hours_per_build : float
        Direct operator labour required per build (hours).
    operator_hours_available_per_year : float
        Annual operator labour available per machine (hours).
    external_turnaround_days : float
        Supplier turnaround for outsourced builds (days).
    support_capital_cost : float
        One-time supporting capital spend (USD) such as depowdering stations,
        ventilation upgrades, shelving, or electrical work.
    support_annual_operating_cost : float
        Aggregate annual operating expense for supporting equipment and
        facilities improvements (USD/year).
    hybrid_outsource_fraction : float
        Target fraction of annual demand that remains outsourced in the hybrid
        scenario (0–1). For example, ``0.30`` forces 30 % of demand to stay
        external even when internal capacity exists.

    ---Returns---
    best_machine_count : float
        Machine count that maximises mean annual savings across the simulations.
    mean_break_even_years : float
        Expected time for the best machine count to recover the capital cost.
        Reports ``inf`` when break-even is not achieved within ``analysis_years``.
    probability_break_even : float
        Fraction of trials in which break-even occurs within ``analysis_years``.
    mean_builds_to_break_even : float
        Expected number of internal builds required to hit the break-even point.
    mean_annual_savings : float
        Average annual savings versus outsourcing for the best machine count.
    annual_savings_p10 : float
        10th percentile of the annual savings distribution (USD/year).
    annual_savings_p90 : float
        90th percentile of the annual savings distribution (USD/year).
    per_machine_summary_json : str
        JSON-encoded table of summary statistics for each evaluated machine count.
    cash_flow_curve_json : str
        Encoded list of cumulative cash-flow statistics (mean, 10th, and 90th percentiles)
        by analysis year for the recommended machine count.
    cost_curve_json : str
        Encoded mean cumulative cost trajectories for the outsourced-only,
        in-house (best machine count), and hybrid demand mixes.
    representative_event_log_json : str
        Encoded log describing a representative Monte Carlo year, including demand,
        realised uptime, downtime events, savings, and cash flow snapshots.
    cost_component_summary_json : str
        Aggregated cost breakdown (capital, variable, fixed, outsourced share)
        for the best machine count and its hybrid counterpart.
    average_internal_turnaround_days : float
        Typical internal turnaround per build derived from print and cooldown durations.
    turnaround_advantage_days : float
        Calculated time advantage relative to the supplied external turnaround.
    cycle_time_hours : float
        Sum of print and cooldown hours for one build cycle.
    hybrid_outsource_fraction : float
        Echo of the requested hybrid outsourcing share (0–1).

    ---LaTeX---
    C_{\\text{cap}} = N_m \\times P_0 \\\\
    B_{\\text{int},y} = \\min\\bigl(D_y, N_m \\times B_{\\max} \\times U_y\\bigr) \\\\
    S_y = B_{\\text{int},y} (C_{\\text{ext}} - C_{\\text{int}}) - N_m C_{\\text{fix}} \\\\
    C_{\\text{cum},y} = -C_{\\text{cap}} + \\sum_{k=1}^{y} S_k

    ---References---
    Gibson, I., Rosen, D. W., & Stucker, B. (2021). *Additive Manufacturing Technologies* (4th ed.). Springer.
    ASTM International. (2017). ISO/ASTM 52910-17: *Additive manufacturing — Design — Requirements, guidelines and recommendations*.
    """

    if purchase_price <= 0:
        raise ValueError("Purchase price must be positive.")
    if analysis_years <= 0:
        raise ValueError("Analysis years must be positive.")
    if simulations <= 0:
        raise ValueError("Simulation count must be positive.")
    if max_builds_per_machine <= 0:
        raise ValueError("Maximum builds per machine must be positive.")
    if external_cost_per_build <= 0:
        raise ValueError("External cost per build must be positive.")
    if variable_internal_cost < 0:
        raise ValueError("Variable internal cost cannot be negative.")
    if fixed_annual_cost_per_machine < 0:
        raise ValueError("Fixed annual cost per machine cannot be negative.")
    if print_time_hours <= 0:
        raise ValueError("Print time hours must be positive.")
    if cooldown_time_hours < 0:
        raise ValueError("Cooldown time hours cannot be negative.")
    if operator_hours_per_build <= 0:
        raise ValueError("Operator hours per build must be positive.")
    if operator_hours_available_per_year <= 0:
        raise ValueError("Available operator hours must be positive.")
    if external_turnaround_days <= 0:
        raise ValueError("External turnaround must be positive.")
    if support_capital_cost < 0:
        raise ValueError("Support capital cost cannot be negative.")
    if support_annual_operating_cost < 0:
        raise ValueError("Support annual operating cost cannot be negative.")
    if not 0.0 <= hybrid_outsource_fraction <= 1.0:
        raise ValueError("Hybrid outsource fraction must lie between 0 and 1.")

    machine_counts_list: List[int] = []
    for token in machine_counts.split(","):
        token = token.strip()
        if not token:
            continue
        count = int(token)
        if count <= 0:
            raise ValueError("Machine counts must be positive integers.")
        if count not in machine_counts_list:
            machine_counts_list.append(count)

    if not machine_counts_list:
        raise ValueError("Provide at least one machine count to simulate.")

    machine_counts_list.sort()

    downtime_event_probability = _clamp(downtime_event_probability, 0.0, 1.0)
    operator_issue_probability = _clamp(operator_issue_probability, 0.0, 1.0)
    downtime_event_duration_fraction = _clamp(downtime_event_duration_fraction, 0.0, 1.0)
    operator_issue_duration_fraction = _clamp(operator_issue_duration_fraction, 0.0, 1.0)

    HOURS_PER_YEAR = 24.0 * 365.0
    cycle_hours = print_time_hours + cooldown_time_hours
    if cycle_hours <= 0:
        raise ValueError("Combined print and cooldown hours must be positive.")

    per_machine_data: Dict[
        int,
        Dict[
            str,
            List[
                float
                | List[float]
                | List[Dict[str, float | bool]]
                | Dict[str, float]
            ],
        ],
    ] = {
        count: {
            "annual_savings": [],
            "break_even_years": [],
            "builds_to_break_even": [],
            "cash_flow_series": [],
            "event_logs": [],
            "baseline_cost_series": [],
            "internal_cost_series": [],
            "hybrid_cost_series": [],
            "component_totals": [],
        }
        for count in machine_counts_list
    }

    average_internal_turnaround_days = cycle_hours / 24.0
    turnaround_advantage_days = external_turnaround_days - average_internal_turnaround_days

    per_machine_data: Dict[
        int,
        Dict[
            str,
            List[
                float
                | List[float]
                | List[Dict[str, float | bool]]
                | Dict[str, float]
            ],
        ],
    ] = {
        count: {
            "annual_savings": [],
            "break_even_years": [],
            "builds_to_break_even": [],
            "cash_flow_series": [],
            "event_logs": [],
            "baseline_cost_series": [],
            "internal_cost_series": [],
            "hybrid_cost_series": [],
            "component_totals": [],
        }
        for count in machine_counts_list
    }

    for _ in range(simulations):
        yearly_demands: List[float] = []
        yearly_uptime_samples: List[float] = []
        yearly_downtime_events: List[bool] = []
        yearly_operator_events: List[bool] = []

        for _year in range(analysis_years):
            demand_sample = max(0.0, random.gauss(annual_demand_mean, annual_demand_std))
            uptime_sample = _sample_uptime(uptime_mean, uptime_std)

            downtime_flag = random.random() < downtime_event_probability
            if downtime_flag:
                uptime_sample *= 1.0 - downtime_event_duration_fraction

            operator_flag = random.random() < operator_issue_probability
            if operator_flag:
                uptime_sample *= 1.0 - operator_issue_duration_fraction

            yearly_demands.append(demand_sample)
            yearly_uptime_samples.append(_clamp(uptime_sample, 0.0, 1.0))
            yearly_downtime_events.append(downtime_flag)
            yearly_operator_events.append(operator_flag)

        for count in machine_counts_list:
            capital_cost = purchase_price * count + support_capital_cost
            cumulative_cash_flow = -capital_cost
            break_even_year = math.inf
            builds_to_break_even = math.inf

            annual_savings_values: List[float] = []
            cumulative_internal_builds = 0.0
            cash_flow_series: List[float] = []
            event_log: List[Dict[str, float | bool]] = []

            operator_capacity = (
                count * operator_hours_available_per_year / operator_hours_per_build
            )

            cumulative_baseline_cost = 0.0
            cumulative_internal_cost = capital_cost
            cumulative_hybrid_cost = capital_cost
            baseline_cost_series: List[float] = []
            internal_cost_series: List[float] = []
            hybrid_cost_series: List[float] = []

            total_demand = 0.0
            total_internal_variable_cost = 0.0
            total_internal_fixed_cost = 0.0
            total_internal_outsourced_cost = 0.0
            total_hybrid_variable_cost = 0.0
            total_hybrid_fixed_cost = 0.0
            total_hybrid_outsourced_cost = 0.0
            total_internal_outsourced_builds = 0.0
            total_hybrid_outsourced_builds = 0.0

            for year_index in range(analysis_years):
                demand = yearly_demands[year_index]
                uptime = yearly_uptime_samples[year_index]
                total_demand += demand

                nominal_capacity = count * max_builds_per_machine * uptime
                cycle_capacity = (
                    count * (uptime * HOURS_PER_YEAR) / cycle_hours
                    if cycle_hours > 0
                    else float("inf")
                )
                capacity = min(nominal_capacity, cycle_capacity, operator_capacity)

                # Internal-only scenario (used to determine best machine count)
                internal_builds = min(demand, capacity)
                outsourced_builds = max(demand - internal_builds, 0.0)

                baseline_cost = demand * external_cost_per_build
                internal_variable_cost = internal_builds * variable_internal_cost
                internal_outsource_cost = outsourced_builds * external_cost_per_build
                internal_fixed_cost = count * fixed_annual_cost_per_machine + support_annual_operating_cost
                internal_annual_cost = (
                    internal_variable_cost + internal_outsource_cost + internal_fixed_cost
                )

                savings = baseline_cost - internal_annual_cost
                annual_savings_values.append(savings)
                cumulative_internal_builds += internal_builds

                cumulative_cash_flow += savings
                cash_flow_series.append(cumulative_cash_flow)

                cumulative_baseline_cost += baseline_cost
                cumulative_internal_cost += internal_annual_cost

                # Hybrid scenario with forced outsourcing share
                forced_outsourced = demand * hybrid_outsource_fraction
                target_internal = max(demand - forced_outsourced, 0.0)
                hybrid_internal_builds = min(capacity, target_internal)
                hybrid_shortfall = max(target_internal - hybrid_internal_builds, 0.0)
                hybrid_total_outsourced = forced_outsourced + hybrid_shortfall

                hybrid_variable_cost = hybrid_internal_builds * variable_internal_cost
                hybrid_outsource_cost = hybrid_total_outsourced * external_cost_per_build
                hybrid_fixed_cost = internal_fixed_cost  # identical fixed burden
                hybrid_annual_cost = (
                    hybrid_variable_cost + hybrid_outsource_cost + hybrid_fixed_cost
                )

                cumulative_hybrid_cost += hybrid_annual_cost

                baseline_cost_series.append(cumulative_baseline_cost)
                internal_cost_series.append(cumulative_internal_cost)
                hybrid_cost_series.append(cumulative_hybrid_cost)

                if break_even_year is math.inf and cumulative_cash_flow >= 0.0:
                    break_even_year = year_index + 1
                    builds_to_break_even = cumulative_internal_builds

                event_log.append(
                    {
                        "year": float(year_index + 1),
                        "demand_builds": demand,
                        "uptime_fraction": uptime,
                        "internal_builds": internal_builds,
                        "outsourced_builds": outsourced_builds,
                        "hybrid_internal_builds": hybrid_internal_builds,
                        "hybrid_outsourced_builds": hybrid_total_outsourced,
                        "downtime_event": yearly_downtime_events[year_index],
                        "operator_issue": yearly_operator_events[year_index],
                        "annual_savings": savings,
                        "cumulative_cash_flow": cumulative_cash_flow,
                        "baseline_cumulative_cost": cumulative_baseline_cost,
                        "internal_cumulative_cost": cumulative_internal_cost,
                        "hybrid_cumulative_cost": cumulative_hybrid_cost,
                    }
                )

                total_internal_variable_cost += internal_variable_cost
                total_internal_fixed_cost += internal_fixed_cost
                total_internal_outsourced_cost += internal_outsource_cost
                total_hybrid_variable_cost += hybrid_variable_cost
                total_hybrid_fixed_cost += hybrid_fixed_cost
                total_hybrid_outsourced_cost += hybrid_outsource_cost
                total_internal_outsourced_builds += outsourced_builds
                total_hybrid_outsourced_builds += hybrid_total_outsourced

            mean_annual_savings = sum(annual_savings_values) / analysis_years

            per_machine_data[count]["annual_savings"].append(mean_annual_savings)
            per_machine_data[count]["break_even_years"].append(break_even_year)
            per_machine_data[count]["builds_to_break_even"].append(builds_to_break_even)
            per_machine_data[count]["cash_flow_series"].append(cash_flow_series)
            per_machine_data[count]["event_logs"].append(event_log)
            per_machine_data[count]["baseline_cost_series"].append(baseline_cost_series)
            per_machine_data[count]["internal_cost_series"].append(internal_cost_series)
            per_machine_data[count]["hybrid_cost_series"].append(hybrid_cost_series)
            per_machine_data[count]["component_totals"].append(
                {
                    "capital": capital_cost,
                    "internal_variable": total_internal_variable_cost,
                    "internal_fixed": total_internal_fixed_cost,
                    "internal_outsourced": total_internal_outsourced_cost,
                    "baseline_total": cumulative_baseline_cost,
                    "hybrid_variable": total_hybrid_variable_cost,
                    "hybrid_fixed": total_hybrid_fixed_cost,
                    "hybrid_outsourced": total_hybrid_outsourced_cost,
                    "demand_total": total_demand,
                    "internal_outsourced_builds": total_internal_outsourced_builds,
                    "hybrid_outsourced_builds": total_hybrid_outsourced_builds,
                }
            )

    summary: Dict[int, Dict[str, float]] = {}
    best_machine_count = machine_counts_list[0]
    best_mean_savings = float("-inf")

    for count, data in per_machine_data.items():
        annual_savings = data["annual_savings"]
        break_even_years = [
            value for value in data["break_even_years"] if value != math.inf
        ]
        builds_to_break_even = [
            value for value in data["builds_to_break_even"] if value != math.inf
        ]

        mean_savings = sum(annual_savings) / len(annual_savings)
        savings_p10 = _percentile(annual_savings, 0.10)
        savings_p90 = _percentile(annual_savings, 0.90)
        break_even_probability = len(break_even_years) / len(annual_savings)

        mean_break_even = math.inf
        mean_builds_break_even = math.inf

        if break_even_years:
            mean_break_even = sum(break_even_years) / len(break_even_years)
        if builds_to_break_even:
            mean_builds_break_even = sum(builds_to_break_even) / len(
                builds_to_break_even
            )

        summary[count] = {
            "mean_annual_savings": mean_savings,
            "savings_p10": savings_p10,
            "savings_p90": savings_p90,
            "probability_break_even": break_even_probability,
            "mean_break_even_years": mean_break_even,
            "mean_builds_to_break_even": mean_builds_break_even,
        }

        if mean_savings > best_mean_savings:
            best_mean_savings = mean_savings
            best_machine_count = count

    best_metrics = summary[best_machine_count]

    per_machine_summary = [
        {
            "machine_count": count,
            "mean_annual_savings": metrics["mean_annual_savings"],
            "savings_p10": metrics["savings_p10"],
            "savings_p90": metrics["savings_p90"],
            "probability_break_even": metrics["probability_break_even"],
            "mean_break_even_years": _serialise_value(
                metrics["mean_break_even_years"]
            ),
            "mean_builds_to_break_even": _serialise_value(
                metrics["mean_builds_to_break_even"]
            ),
        }
        for count, metrics in summary.items()
    ]

    cash_flow_curve = []
    cash_flow_series_all = per_machine_data[best_machine_count]["cash_flow_series"]
    if cash_flow_series_all:
        for year_index in range(analysis_years):
            year_values = [
                series[year_index] for series in cash_flow_series_all if len(series) > year_index
            ]
            if year_values:
                cash_flow_curve.append(
                    {
                        "year": year_index + 1,
                        "mean": _serialise_value(sum(year_values) / len(year_values)),
                        "p10": _serialise_value(_percentile(year_values, 0.10)),
                        "p90": _serialise_value(_percentile(year_values, 0.90)),
                    }
                )

    years = list(range(1, analysis_years + 1))
    baseline_cost_series_all = per_machine_data[best_machine_count]["baseline_cost_series"]
    internal_cost_series_all = per_machine_data[best_machine_count]["internal_cost_series"]
    hybrid_cost_series_all = per_machine_data[best_machine_count]["hybrid_cost_series"]

    def _mean_curve(series_all: List[List[float]]) -> List[float | None]:
        curve: List[float | None] = []
        for year_index in range(analysis_years):
            values = [
                series[year_index] for series in series_all if len(series) > year_index
            ]
            if values:
                curve.append(sum(values) / len(values))
            else:
                curve.append(None)
        return curve

    cost_curve_payload = {
        "years": years,
        "outsourced": [_serialise_value(v) for v in _mean_curve(baseline_cost_series_all)],
        "in_house": [_serialise_value(v) for v in _mean_curve(internal_cost_series_all)],
        "hybrid": [_serialise_value(v) for v in _mean_curve(hybrid_cost_series_all)],
    }

    component_totals_all = per_machine_data[best_machine_count]["component_totals"]
    component_summary = {}
    if component_totals_all:
        keys = [
            "capital",
            "internal_variable",
            "internal_fixed",
            "internal_outsourced",
            "baseline_total",
            "hybrid_variable",
            "hybrid_fixed",
            "hybrid_outsourced",
            "demand_total",
            "internal_outsourced_builds",
            "hybrid_outsourced_builds",
        ]
        component_summary = {
            key: _serialise_value(
                sum(item[key] for item in component_totals_all) / len(component_totals_all)
            )
            for key in keys
        }

        demand_total = sum(item["demand_total"] for item in component_totals_all)
        internal_outsourced_builds_total = sum(
            item["internal_outsourced_builds"] for item in component_totals_all
        )
        hybrid_outsourced_builds_total = sum(
            item["hybrid_outsourced_builds"] for item in component_totals_all
        )
        if demand_total > 0:
            component_summary["internal_outsource_share"] = _serialise_value(
                internal_outsourced_builds_total / demand_total
            )
            component_summary["hybrid_outsource_share"] = _serialise_value(
                hybrid_outsourced_builds_total / demand_total
            )
        else:
            component_summary["internal_outsource_share"] = None
            component_summary["hybrid_outsource_share"] = None
    annual_savings_list = per_machine_data[best_machine_count]["annual_savings"]
    representative_index = 0
    if annual_savings_list:
        representative_index = min(
            range(len(annual_savings_list)),
            key=lambda idx: abs(annual_savings_list[idx] - best_metrics["mean_annual_savings"]),
        )

    representative_log_raw = per_machine_data[best_machine_count]["event_logs"][representative_index]
    representative_log = [
        {
            "year": entry["year"],
            "demand_builds": _serialise_value(entry["demand_builds"]),
            "uptime_fraction": _serialise_value(entry["uptime_fraction"]),
            "internal_builds": _serialise_value(entry["internal_builds"]),
            "outsourced_builds": _serialise_value(entry["outsourced_builds"]),
            "hybrid_internal_builds": _serialise_value(entry["hybrid_internal_builds"]),
            "hybrid_outsourced_builds": _serialise_value(entry["hybrid_outsourced_builds"]),
            "downtime_event": entry["downtime_event"],
            "operator_issue": entry["operator_issue"],
            "annual_savings": _serialise_value(entry["annual_savings"]),
            "cumulative_cash_flow": _serialise_value(entry["cumulative_cash_flow"]),
            "baseline_cumulative_cost": _serialise_value(entry["baseline_cumulative_cost"]),
            "internal_cumulative_cost": _serialise_value(entry["internal_cumulative_cost"]),
            "hybrid_cumulative_cost": _serialise_value(entry["hybrid_cumulative_cost"]),
        }
        for entry in representative_log_raw
    ]

    result: Dict[str, float | str] = {
        "best_machine_count": float(best_machine_count),
        "mean_break_even_years": best_metrics["mean_break_even_years"],
        "probability_break_even": best_metrics["probability_break_even"],
        "mean_builds_to_break_even": best_metrics["mean_builds_to_break_even"],
        "mean_annual_savings": best_metrics["mean_annual_savings"],
        "annual_savings_p10": best_metrics["savings_p10"],
        "annual_savings_p90": best_metrics["savings_p90"],
        "per_machine_summary_json": json.dumps(per_machine_summary),
        "cash_flow_curve_json": json.dumps(cash_flow_curve),
        "cost_curve_json": json.dumps(cost_curve_payload),
        "representative_event_log_json": json.dumps(representative_log),
        "cost_component_summary_json": json.dumps(component_summary),
        "average_internal_turnaround_days": average_internal_turnaround_days,
        "turnaround_advantage_days": turnaround_advantage_days,
        "cycle_time_hours": cycle_hours,
        "hybrid_outsource_fraction": hybrid_outsource_fraction,
    }

    # Build substituted strings for LaTeX rendering in the UI.
    n_m = best_machine_count
    p_0 = purchase_price
    c_ext = external_cost_per_build
    c_int = variable_internal_cost
    c_fix = fixed_annual_cost_per_machine
    b_max = max_builds_per_machine

    result["subst_best_machine_count"] = f"N_m = {n_m}"
    if math.isfinite(best_metrics["mean_break_even_years"]):
        result["subst_mean_break_even_years"] = (
            f"N_m = {n_m}, \\; C_{{\\text{{cum}},y}} \\ge 0 \\text{{ at }} y = "
            f"{best_metrics['mean_break_even_years']:.2f}"
        )
    else:
        result["subst_mean_break_even_years"] = (
            f"N_m = {n_m}, \\; C_{{\\text{{cum}},y}} < 0 \\; \\forall y \\le {analysis_years}"
        )

    if math.isfinite(best_metrics["mean_builds_to_break_even"]):
        result["subst_mean_builds_to_break_even"] = (
            f"\\sum B_{{\\text{{int}},y}} = {best_metrics['mean_builds_to_break_even']:.1f}"
        )
    else:
        result["subst_mean_builds_to_break_even"] = (
            "\\sum B_{\\text{int},y} < \\infty \\text{ not reached within horizon}"
        )

    result["subst_probability_break_even"] = (
        f"\\Pr(C_{{\\text{{cum}},y}} \\ge 0) = "
        f"{best_metrics['probability_break_even']:.3f}"
    )

    result["subst_mean_annual_savings"] = (
        f"\\bar{{S}} = B_{{\\text{{int}}}} ( {c_ext} - {c_int} ) - {n_m} \\times {c_fix}"
    )
    result["subst_annual_savings_p10"] = (
        f"S_{{0.10}} = {best_metrics['savings_p10']:.2f}"
    )
    result["subst_annual_savings_p90"] = (
        f"S_{{0.90}} = {best_metrics['savings_p90']:.2f}"
    )
    result["subst_average_internal_turnaround_days"] = (
        f"T_{{\\text{{int}}}} = {average_internal_turnaround_days:.2f} \\text{{ days}}"
    )
    result["subst_turnaround_advantage_days"] = (
        f"\\Delta T = {turnaround_advantage_days:.2f} \\text{{ days}}"
    )
    result["subst_cycle_time_hours"] = (
        f"t_{{\\text{{cycle}}}} = {cycle_hours:.2f} \\text{{ h}}"
    )
    result["subst_hybrid_outsource_fraction"] = (
        f"f_{{\\text{{hybrid, out}}}} = {hybrid_outsource_fraction:.2f}"
    )

    return result
