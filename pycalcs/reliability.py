"""Reliability and MTBF calculations.

Two independent entry points live here:

* :func:`analyze_reliability` combines known component MTBFs into a system
  reliability (the block-diagram direction).
* :func:`estimate_mtbf` goes the other way, fitting an MTBF or MTTF to
  observed test or field data.
"""

from __future__ import annotations

import math
from typing import Any

try:  # normal package import
    from . import _stats
except ImportError:  # Pyodide fetches each module as a flat top-level file
    import _stats  # type: ignore[no-redef]


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


# =====================================================================
# MTBF / MTTF estimation from test or field data
# =====================================================================

_DISTRIBUTIONS = ("exponential", "weibull", "lognormal")
_DATA_MODES = ("aggregate", "fleet", "failure_times")
_TERMINATIONS = ("time", "failure")


def _clean_times(values: list[float] | None, label: str) -> list[float]:
    if not values:
        return []
    cleaned: list[float] = []
    for value in values:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError(f"{label} must all be greater than zero.")
        cleaned.append(number)
    return cleaned


def _weibull_log_likelihood(
    beta: float,
    eta: float,
    failures: list[float],
    suspensions: list[float],
) -> float:
    if beta <= 0 or eta <= 0:
        return -math.inf
    r = len(failures)
    total = r * math.log(beta) - r * beta * math.log(eta)
    total += (beta - 1.0) * sum(math.log(t) for t in failures)
    total -= sum((t / eta) ** beta for t in failures + suspensions)
    return total


def _weibull_mle(failures: list[float], suspensions: list[float]) -> tuple[float, float]:
    """Maximum likelihood shape and scale for right-censored Weibull data.

    Solves the one-dimensional profile likelihood equation for beta by
    bisection, then recovers eta in closed form. The t**beta sums are
    accumulated in log space so that a large trial beta cannot overflow.
    """
    r = len(failures)
    all_times = failures + suspensions
    log_times = [math.log(t) for t in all_times]
    mean_log_failure = sum(math.log(t) for t in failures) / r

    def scaled_weights(beta: float) -> tuple[list[float], float]:
        """Return exp(beta*ln t - offset) for each time, plus the offset."""
        offset = max(beta * log_time for log_time in log_times)
        return [math.exp(beta * log_time - offset) for log_time in log_times], offset

    def score(beta: float) -> float:
        weights, _ = scaled_weights(beta)
        denominator = sum(weights)
        numerator = sum(w * log_time for w, log_time in zip(weights, log_times))
        return 1.0 / beta + mean_log_failure - numerator / denominator

    lo, hi = 1e-3, 1e3
    if score(lo) < 0:
        beta = lo
    elif score(hi) > 0:
        beta = hi
    else:
        for _ in range(300):
            beta = 0.5 * (lo + hi)
            if score(beta) > 0:
                lo = beta
            else:
                hi = beta
            if hi - lo < 1e-12 * hi:
                break
        beta = 0.5 * (lo + hi)

    weights, offset = scaled_weights(beta)
    eta = math.exp((offset + math.log(sum(weights) / r)) / beta)
    return beta, eta


def _lognormal_log_likelihood(
    mu: float,
    sigma: float,
    failures: list[float],
    suspensions: list[float],
) -> float:
    if sigma <= 0:
        return -math.inf
    total = 0.0
    for t in failures:
        z = (math.log(t) - mu) / sigma
        total += -math.log(t * sigma * math.sqrt(2.0 * math.pi)) - 0.5 * z * z
    for t in suspensions:
        survival = _stats.normal_cdf(-(math.log(t) - mu) / sigma)
        if survival <= 0:
            return -math.inf
        total += math.log(survival)
    return total


def _lognormal_mle(failures: list[float], suspensions: list[float]) -> tuple[float, float]:
    """Maximum likelihood log-mean and log-standard-deviation.

    Complete data has a closed form. Censored data is fit by simplex search
    over (mu, ln sigma) starting from the complete-data estimate.
    """
    logs = [math.log(t) for t in failures]
    mu = sum(logs) / len(logs)
    variance = sum((x - mu) ** 2 for x in logs) / len(logs)
    sigma = math.sqrt(variance) if variance > 0 else 1e-3

    if not suspensions:
        return mu, sigma

    def negative_ll(params: list[float]) -> float:
        value = _lognormal_log_likelihood(params[0], math.exp(params[1]), failures, suspensions)
        return -value if math.isfinite(value) else 1e300

    best = _stats.nelder_mead(negative_ll, [mu, math.log(sigma)], step=[0.5 * sigma, 0.25])
    return best[0], math.exp(best[1])


def _numeric_hessian(function, point: list[float], step: float = 1e-4) -> list[list[float]]:
    n = len(point)
    hessian = [[0.0] * n for _ in range(n)]
    base = function(point)
    for i in range(n):
        for j in range(i, n):
            if i == j:
                forward, backward = list(point), list(point)
                forward[i] += step
                backward[i] -= step
                hessian[i][i] = (function(forward) - 2.0 * base + function(backward)) / (step * step)
            else:
                pp, pm, mp, mm = (list(point) for _ in range(4))
                pp[i] += step
                pp[j] += step
                pm[i] += step
                pm[j] -= step
                mp[i] -= step
                mp[j] += step
                mm[i] -= step
                mm[j] -= step
                value = (function(pp) - function(pm) - function(mp) + function(mm)) / (4.0 * step * step)
                hessian[i][j] = hessian[j][i] = value
    return hessian


def _numeric_gradient(function, point: list[float], step: float = 1e-5) -> list[float]:
    gradient = []
    for i in range(len(point)):
        forward, backward = list(point), list(point)
        forward[i] += step
        backward[i] -= step
        gradient.append((function(forward) - function(backward)) / (2.0 * step))
    return gradient


def _log_scale_bounds(
    log_likelihood,
    log_params: list[float],
    log_quantity,
    z_two_sided: float,
    z_one_sided: float,
) -> tuple[float | None, float | None, float | None]:
    """Delta-method confidence bounds for a positive quantity.

    Works on the natural log of both the parameters and the quantity, so the
    resulting interval is asymmetric and cannot go negative.
    """
    try:
        hessian = _numeric_hessian(log_likelihood, log_params)
        information = [[-value for value in row] for row in hessian]
        covariance = _stats.invert_2x2(information)
        gradient = _numeric_gradient(log_quantity, log_params)
        variance = 0.0
        for i in range(2):
            for j in range(2):
                variance += gradient[i] * covariance[i][j] * gradient[j]
        if not math.isfinite(variance) or variance <= 0:
            return None, None, None
        std_error = math.sqrt(variance)
    except (ArithmeticError, ValueError, OverflowError):
        return None, None, None

    center = log_quantity(log_params)
    lower = math.exp(center - z_two_sided * std_error)
    upper = math.exp(center + z_two_sided * std_error)
    lower_one_sided = math.exp(center - z_one_sided * std_error)
    return lower, upper, lower_one_sided


def _median_ranks(failures: list[float], suspensions: list[float]) -> list[dict[str, float]]:
    """Benard median ranks with Johnson adjusted ranks for suspended units."""
    items = [(t, True) for t in failures] + [(t, False) for t in suspensions]
    items.sort(key=lambda item: (item[0], not item[1]))
    n = len(items)
    points: list[dict[str, float]] = []
    previous_rank = 0.0
    for position, (time_hours, is_failure) in enumerate(items, start=1):
        if not is_failure:
            continue
        increment = (n + 1.0 - previous_rank) / (n + 2.0 - position)
        adjusted_rank = previous_rank + increment
        previous_rank = adjusted_rank
        points.append(
            {
                "time_hours": time_hours,
                "adjusted_rank": adjusted_rank,
                "median_rank": (adjusted_rank - 0.3) / (n + 0.4),
            }
        )
    return points


def estimate_mtbf(
    distribution: str = "exponential",
    data_mode: str = "aggregate",
    total_operating_hours: float | None = None,
    failure_count: int | None = None,
    unit_count: int | None = None,
    hours_per_unit: float | None = None,
    failure_times_hours: list[float] | None = None,
    suspension_times_hours: list[float] | None = None,
    test_termination: str = "time",
    confidence_level: float = 0.9,
    mission_time_hours: float | None = None,
    mission_unit_count: int | None = None,
    repair_time_hours: float | None = None,
) -> dict[str, Any]:
    """
    Estimate MTBF from observed operating time and failures.

    Three ways to describe the data are supported. "aggregate" takes the total
    operating time across the fleet plus a failure count. "fleet" takes a unit
    count and the hours each unit ran. "failure_times" takes the individual
    times to failure, plus the run times of any units that did not fail
    (suspensions), which is the only mode that carries enough information to
    fit a shape parameter.

    The exponential fit assumes a constant failure rate and gives the familiar
    MTBF = T / r with exact chi-squared confidence bounds. The Weibull and
    lognormal fits are maximum likelihood, handle right-censored data, and
    return a mean time to failure rather than an MTBF: once the hazard rate
    changes with age, a single "time between failures" number no longer
    describes the population. The Weibull shape parameter is the check on
    whether the constant-rate assumption was reasonable in the first place.

    ---Parameters---
    distribution : str
        Failure distribution to fit: "exponential", "weibull", or "lognormal".
    data_mode : str
        How the data is supplied: "aggregate", "fleet", or "failure_times".
        Weibull and lognormal fits require "failure_times".
    total_operating_hours : float | None
        Total operating time accumulated across all units (hours). Required
        for "aggregate" mode.
    failure_count : int | None
        Number of failures observed. Required for "aggregate" and "fleet".
    unit_count : int | None
        Number of units on test or in service. Required for "fleet" mode.
    hours_per_unit : float | None
        Operating time accumulated by each unit (hours). Required for "fleet".
    failure_times_hours : list[float] | None
        Individual times to failure (hours). Required for "failure_times".
    suspension_times_hours : list[float] | None
        Run times of units that had not failed when observation stopped
        (hours). Optional, used in "failure_times" mode.
    test_termination : str
        "time" when observation stopped at a planned time, "failure" when it
        stopped on the last failure. Changes the exponential upper bound.
    confidence_level : float
        Confidence level for the interval, between 0 and 1 (0.9 gives 90%).
    mission_time_hours : float | None
        Optional mission time at which to report reliability (hours).
    mission_unit_count : int | None
        Number of units to project the mission onto. Turns the reliability at
        the mission time into expected survivors and failures. Defaults to 1.
    repair_time_hours : float | None
        Mean time to repair, MTTR (hours). Supplying it adds steady-state
        availability and downtime per year. Leave it out for non-repairable
        items, where availability has no meaning.

    ---Returns---
    distribution : str
        Distribution that was fitted.
    total_operating_hours : float
        Total operating time used in the estimate (hours).
    failure_count : int
        Number of failures used in the estimate.
    suspension_count : int
        Number of suspended (non-failed) units included.
    mtbf_hours : float
        Point estimate of MTBF for the exponential fit, or the distribution
        mean time to failure for Weibull and lognormal (hours).
    failure_rate_per_hour : float
        Reciprocal of the point estimate (1/hour).
    mtbf_lower_hours : float | None
        Lower two-sided confidence bound on the point estimate (hours).
    mtbf_upper_hours : float | None
        Upper two-sided confidence bound on the point estimate (hours).
    mtbf_lower_one_sided_hours : float | None
        One-sided lower confidence bound on the point estimate (hours).
    metric_label : str
        "MTBF" for the exponential fit, "MTTF" otherwise.
    parameters : dict
        Fitted distribution parameters and their confidence bounds.
    median_life_hours : float
        Time by which half the population has failed (hours).
    b10_life_hours : float
        Time by which 10% of the population has failed (hours).
    annualized_failure_rate : float
        Share of units that fail within one year of 8760 operating hours,
        equal to 1 - R(8760). This is the AFR quoted for disk drives and
        consumer hardware.
    expected_failures_per_unit_year : float | None
        Expected number of failures per unit per operating year, 8760/MTBF.
        Exponential fit only, since it assumes each repair restores the unit.
        Equal to the AFR when the MTBF is long relative to a year, and larger
        than it when the MTBF is short, because one unit can fail repeatedly.
    repair_time_hours : float | None
        Mean time to repair that was supplied (hours).
    availability : float | None
        Steady-state availability, MTBF / (MTBF + MTTR).
    downtime_hours_per_year : float | None
        Expected downtime in a year of 8760 hours.
    reliability_at_mission : float | None
        Reliability at the mission time, when one is supplied.
    mission_unit_count : int | None
        Fleet size the mission projection was run for.
    mission_expected_survivors : float | None
        Units expected to complete the mission without failing.
    mission_expected_failures : float | None
        Units expected to fail during the mission.
    mission_all_survive_probability : float | None
        Probability that every unit in the fleet completes the mission.
    mission_expected_repairs : float | None
        For the exponential fit only: expected number of failures across the
        fleet during the mission when each failed unit is repaired and put
        back in service. None for the wear-out distributions, where a single
        renewal rate does not apply.
    reliability_curve : dict
        Time history of reliability and hazard rate for plotting.
    probability_plot : dict
        Median-rank plotting positions and the fitted straight line, in the
        linearizing coordinates for the chosen distribution.
    notes : list[str]
        Warnings about sample size and model assumptions.

    ---LaTeX---
    Equation_1 = \\hat{MTBF} = \\frac{T}{r}
    Equation_2 = MTBF_{lower} = \\frac{2T}{\\chi^2_{1-\\alpha/2,\\,2r+2}}
    Equation_3 = MTBF_{upper} = \\frac{2T}{\\chi^2_{\\alpha/2,\\,2r}}
    Equation_4 = R(t) = \\exp\\left[-\\left(\\frac{t}{\\eta}\\right)^{\\beta}\\right]
    Equation_5 = MTTF = \\eta\\,\\Gamma\\!\\left(1 + \\frac{1}{\\beta}\\right)
    Equation_6 = \\frac{1}{\\beta} + \\frac{1}{r}\\sum_{i \\in F} \\ln t_i - \\frac{\\sum_i t_i^{\\beta} \\ln t_i}{\\sum_i t_i^{\\beta}} = 0
    Equation_7 = R(t) = \\Phi\\!\\left(-\\frac{\\ln t - \\mu}{\\sigma}\\right)
    Equation_8 = MTTF = \\exp\\!\\left(\\mu + \\frac{\\sigma^2}{2}\\right)
    Equation_9 = F_i = \\frac{AR_i - 0.3}{n + 0.4}
    Equation_10 = t_{B10} = \\eta\\,(-\\ln 0.9)^{1/\\beta}
    Equation_11 = AFR = 1 - R(8760)
    Equation_12 = A = \\frac{MTBF}{MTBF + MTTR}

    ---References---
    Ebeling, C.E. An Introduction to Reliability and Maintainability
    Engineering, 3rd ed., Chapters 12 and 15.
    O'Connor, P.D.T. and Kleyner, A. Practical Reliability Engineering,
    5th ed., Chapters 3 and 13.
    IEC 60605-4:2001, Equipment reliability testing - Part 4: Statistical
    procedures for exponential distribution.
    IEC 61649:2008, Weibull analysis.
    """
    distribution = str(distribution).strip().lower()
    data_mode = str(data_mode).strip().lower()
    test_termination = str(test_termination).strip().lower()

    if distribution not in _DISTRIBUTIONS:
        raise ValueError(f"Distribution must be one of {_DISTRIBUTIONS}.")
    if data_mode not in _DATA_MODES:
        raise ValueError(f"Data mode must be one of {_DATA_MODES}.")
    if test_termination not in _TERMINATIONS:
        raise ValueError(f"Test termination must be one of {_TERMINATIONS}.")
    if not math.isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("Confidence level must be between 0 and 1.")
    if mission_time_hours is not None:
        if not math.isfinite(mission_time_hours) or mission_time_hours <= 0:
            raise ValueError("Mission time must be greater than zero.")
    if distribution != "exponential" and data_mode != "failure_times":
        raise ValueError(
            "Weibull and lognormal fits need individual failure times. "
            "Switch the data mode to 'failure_times'."
        )

    failures: list[float] = []
    suspensions: list[float] = []
    notes: list[str] = []

    if data_mode == "aggregate":
        if total_operating_hours is None or not math.isfinite(total_operating_hours):
            raise ValueError("Total operating hours is required for aggregate data.")
        if total_operating_hours <= 0:
            raise ValueError("Total operating hours must be greater than zero.")
        if failure_count is None:
            raise ValueError("Failure count is required for aggregate data.")
        total_time = float(total_operating_hours)
        failures_observed = int(failure_count)
    elif data_mode == "fleet":
        if unit_count is None or int(unit_count) < 1:
            raise ValueError("Unit count must be 1 or greater.")
        if hours_per_unit is None or not math.isfinite(hours_per_unit) or hours_per_unit <= 0:
            raise ValueError("Hours per unit must be greater than zero.")
        if failure_count is None:
            raise ValueError("Failure count is required for fleet data.")
        total_time = int(unit_count) * float(hours_per_unit)
        failures_observed = int(failure_count)
    else:
        failures = _clean_times(failure_times_hours, "Failure times")
        suspensions = _clean_times(suspension_times_hours, "Suspension times")
        if not failures:
            raise ValueError("At least one failure time is required.")
        total_time = sum(failures) + sum(suspensions)
        failures_observed = len(failures)

    if failures_observed < 0:
        raise ValueError("Failure count cannot be negative.")
    if failures_observed == 0 and test_termination == "failure":
        raise ValueError(
            "A failure-terminated test must have at least one failure."
        )
    if distribution != "exponential" and failures_observed < 2:
        raise ValueError(
            f"A {distribution} fit needs at least two failure times."
        )

    alpha = 1.0 - confidence_level
    z_two_sided = _stats.normal_quantile(1.0 - alpha / 2.0)
    z_one_sided = _stats.normal_quantile(confidence_level)

    parameters: dict[str, Any] = {}
    subst: dict[str, str] = {}

    if distribution == "exponential":
        if failures_observed == 0:
            point_estimate = math.inf
        else:
            point_estimate = total_time / failures_observed

        dof_lower = 2 * failures_observed + (2 if test_termination == "time" else 0)
        lower = 2.0 * total_time / _stats.chi2_quantile(1.0 - alpha / 2.0, dof_lower)
        lower_one_sided = 2.0 * total_time / _stats.chi2_quantile(confidence_level, dof_lower)
        if failures_observed == 0:
            upper = math.inf
        else:
            upper = 2.0 * total_time / _stats.chi2_quantile(alpha / 2.0, 2 * failures_observed)

        theta = point_estimate
        parameters = {
            "theta_hours": theta,
            "failure_rate_per_hour": (1.0 / theta) if math.isfinite(theta) and theta > 0 else 0.0,
        }

        def reliability(t: float) -> float:
            return math.exp(-t / theta) if math.isfinite(theta) else 1.0

        def hazard(t: float) -> float:
            return (1.0 / theta) if math.isfinite(theta) and theta > 0 else 0.0

        median_life = theta * math.log(2.0)
        b10_life = theta * -math.log(0.9)
        mean_life = theta
        metric_label = "MTBF"

        subst["point_estimate"] = (
            "\\hat{MTBF} = \\frac{T}{r} = "
            f"\\frac{{{_format_value(total_time)}\\,\\text{{hr}}}}{{{failures_observed}}}"
            f" = {_format_value(point_estimate)}\\,\\text{{hr}}"
        )
        subst["lower_bound"] = (
            f"MTBF_{{lower}} = \\frac{{2T}}{{\\chi^2_{{{_format_value(1.0 - alpha / 2.0, 3)},\\,{dof_lower}}}}} = "
            f"\\frac{{2 \\times {_format_value(total_time)}}}{{"
            f"{_format_value(_stats.chi2_quantile(1.0 - alpha / 2.0, dof_lower))}}}"
            f" = {_format_value(lower)}\\,\\text{{hr}}"
        )
        if math.isfinite(upper):
            subst["upper_bound"] = (
                f"MTBF_{{upper}} = \\frac{{2T}}{{\\chi^2_{{{_format_value(alpha / 2.0, 3)},\\,{2 * failures_observed}}}}} = "
                f"\\frac{{2 \\times {_format_value(total_time)}}}{{"
                f"{_format_value(_stats.chi2_quantile(alpha / 2.0, 2 * failures_observed))}}}"
                f" = {_format_value(upper)}\\,\\text{{hr}}"
            )
        else:
            subst["upper_bound"] = "MTBF_{upper} = \\infty \\quad (\\text{no failures observed})"

    elif distribution == "weibull":
        beta, eta = _weibull_mle(failures, suspensions)
        log_params = [math.log(beta), math.log(eta)]

        def weibull_ll(params: list[float]) -> float:
            return _weibull_log_likelihood(
                math.exp(params[0]), math.exp(params[1]), failures, suspensions
            )

        def log_mean(params: list[float]) -> float:
            b = math.exp(params[0])
            return params[1] + math.lgamma(1.0 + 1.0 / b)

        mean_life = eta * math.gamma(1.0 + 1.0 / beta)
        lower, upper, lower_one_sided = _log_scale_bounds(
            weibull_ll, log_params, log_mean, z_two_sided, z_one_sided
        )
        beta_lower, beta_upper, _ = _log_scale_bounds(
            weibull_ll, log_params, lambda p: p[0], z_two_sided, z_one_sided
        )
        eta_lower, eta_upper, _ = _log_scale_bounds(
            weibull_ll, log_params, lambda p: p[1], z_two_sided, z_one_sided
        )

        point_estimate = mean_life
        standard_deviation = eta * math.sqrt(
            max(math.gamma(1.0 + 2.0 / beta) - math.gamma(1.0 + 1.0 / beta) ** 2, 0.0)
        )
        parameters = {
            "beta": beta,
            "beta_lower": beta_lower,
            "beta_upper": beta_upper,
            "eta_hours": eta,
            "eta_lower_hours": eta_lower,
            "eta_upper_hours": eta_upper,
            "standard_deviation_hours": standard_deviation,
            "log_likelihood": _weibull_log_likelihood(beta, eta, failures, suspensions),
        }

        def reliability(t: float) -> float:
            return math.exp(-((t / eta) ** beta))

        def hazard(t: float) -> float:
            if t <= 0:
                return 0.0 if beta > 1 else math.inf
            return (beta / eta) * (t / eta) ** (beta - 1.0)

        median_life = eta * (math.log(2.0) ** (1.0 / beta))
        b10_life = eta * ((-math.log(0.9)) ** (1.0 / beta))
        metric_label = "MTTF"

        subst["point_estimate"] = (
            "MTTF = \\eta\\,\\Gamma(1 + 1/\\beta) = "
            f"{_format_value(eta)} \\times \\Gamma(1 + 1/{_format_value(beta)})"
            f" = {_format_value(mean_life)}\\,\\text{{hr}}"
        )
        subst["shape"] = f"\\beta = {_format_value(beta)}"
        subst["scale"] = f"\\eta = {_format_value(eta)}\\,\\text{{hr}}"
        subst["b10"] = (
            "t_{B10} = \\eta\\,(-\\ln 0.9)^{1/\\beta} = "
            f"{_format_value(eta)} \\times (0.10536)^{{1/{_format_value(beta)}}}"
            f" = {_format_value(b10_life)}\\,\\text{{hr}}"
        )

    else:  # lognormal
        mu, sigma = _lognormal_mle(failures, suspensions)
        params_point = [mu, math.log(sigma)]

        def lognormal_ll(params: list[float]) -> float:
            return _lognormal_log_likelihood(
                params[0], math.exp(params[1]), failures, suspensions
            )

        def log_mean(params: list[float]) -> float:
            return params[0] + 0.5 * math.exp(params[1]) ** 2

        mean_life = math.exp(mu + 0.5 * sigma * sigma)
        lower, upper, lower_one_sided = _log_scale_bounds(
            lognormal_ll, params_point, log_mean, z_two_sided, z_one_sided
        )
        sigma_lower, sigma_upper, _ = _log_scale_bounds(
            lognormal_ll, params_point, lambda p: p[1], z_two_sided, z_one_sided
        )

        point_estimate = mean_life
        parameters = {
            "mu": mu,
            "sigma": sigma,
            "sigma_lower": sigma_lower,
            "sigma_upper": sigma_upper,
            "median_hours": math.exp(mu),
            "log_likelihood": _lognormal_log_likelihood(mu, sigma, failures, suspensions),
        }

        def reliability(t: float) -> float:
            if t <= 0:
                return 1.0
            return _stats.normal_cdf(-(math.log(t) - mu) / sigma)

        def hazard(t: float) -> float:
            if t <= 0:
                return 0.0
            survival = reliability(t)
            if survival <= 0:
                return math.inf
            z = (math.log(t) - mu) / sigma
            return _stats.normal_pdf(z) / (t * sigma * survival)

        median_life = math.exp(mu)
        b10_life = math.exp(mu + sigma * _stats.normal_quantile(0.10))
        metric_label = "MTTF"

        subst["point_estimate"] = (
            "MTTF = \\exp(\\mu + \\sigma^2/2) = "
            f"\\exp({_format_value(mu)} + {_format_value(sigma)}^2/2)"
            f" = {_format_value(mean_life)}\\,\\text{{hr}}"
        )
        subst["shape"] = f"\\sigma = {_format_value(sigma)}"
        subst["scale"] = f"\\mu = {_format_value(mu)}"
        subst["b10"] = (
            "t_{B10} = \\exp(\\mu + \\sigma z_{0.10}) = "
            f"\\exp({_format_value(mu)} + {_format_value(sigma)} \\times "
            f"{_format_value(_stats.normal_quantile(0.10))})"
            f" = {_format_value(b10_life)}\\,\\text{{hr}}"
        )

    failure_rate = (
        1.0 / point_estimate
        if math.isfinite(point_estimate) and point_estimate > 0
        else 0.0
    )

    # Annualized failure rate. Two definitions circulate and they diverge for
    # short-lived items, so both are returned rather than silently picking one:
    # the share of units failing in a year, and the failures per unit-year.
    hours_per_year = 8760.0
    annualized_failure_rate = 1.0 - reliability(hours_per_year)
    expected_failures_per_unit_year = None
    if distribution == "exponential" and math.isfinite(point_estimate) and point_estimate > 0:
        expected_failures_per_unit_year = hours_per_year / point_estimate

    # Steady-state availability. For an alternating renewal process the long-run
    # availability depends only on the means, so this holds for any life
    # distribution, not just the exponential.
    availability = None
    downtime_hours_per_year = None
    if repair_time_hours is not None:
        if not math.isfinite(repair_time_hours) or repair_time_hours < 0:
            raise ValueError("Repair time must be zero or greater.")
        if math.isfinite(point_estimate):
            availability = point_estimate / (point_estimate + repair_time_hours)
            downtime_hours_per_year = (1.0 - availability) * hours_per_year

    reliability_at_mission = (
        reliability(mission_time_hours) if mission_time_hours is not None else None
    )

    # Project the mission onto a fleet. Survivors and failures apply to any
    # distribution; the repair count only means something when the rate is
    # constant, so it stays None otherwise.
    mission_units = None
    mission_survivors = None
    mission_failures = None
    mission_all_survive = None
    mission_repairs = None
    subst_reliability_at_mission = ""
    if mission_time_hours is not None:
        if mission_unit_count is None:
            mission_units = 1
        else:
            mission_units = int(mission_unit_count)
            if mission_units < 1:
                raise ValueError("Mission unit count must be 1 or greater.")
        mission_survivors = mission_units * reliability_at_mission
        mission_failures = mission_units * (1.0 - reliability_at_mission)
        mission_all_survive = reliability_at_mission ** mission_units
        if distribution == "exponential" and math.isfinite(point_estimate):
            mission_repairs = mission_units * mission_time_hours / point_estimate
            subst_reliability_at_mission = (
                "R(t) = e^{-t/MTBF} = "
                f"\\exp\\!\\left(-\\frac{{{_format_value(mission_time_hours)}}}{{"
                f"{_format_value(point_estimate)}}}\\right)"
                f" = {_format_value(reliability_at_mission)}"
            )
        elif distribution == "weibull":
            subst_reliability_at_mission = (
                "R(t) = \\exp[-(t/\\eta)^{\\beta}] = "
                f"\\exp\\!\\left[-\\left(\\frac{{{_format_value(mission_time_hours)}}}{{"
                f"{_format_value(eta)}}}\\right)^{{{_format_value(beta)}}}\\right]"
                f" = {_format_value(reliability_at_mission)}"
            )
        elif distribution == "lognormal":
            subst_reliability_at_mission = (
                "R(t) = \\Phi\\!\\left(-\\frac{\\ln t - \\mu}{\\sigma}\\right) = "
                f"\\Phi\\!\\left(-\\frac{{\\ln {_format_value(mission_time_hours)} - "
                f"{_format_value(mu)}}}{{{_format_value(sigma)}}}\\right)"
                f" = {_format_value(reliability_at_mission)}"
            )

    # Reliability and hazard curves.
    horizon_candidates = [median_life * 3.0]
    if math.isfinite(point_estimate):
        horizon_candidates.append(point_estimate * 2.5)
    if mission_time_hours is not None:
        horizon_candidates.append(mission_time_hours * 1.5)
    if failures:
        horizon_candidates.append(max(failures + suspensions) * 1.5)
    else:
        horizon_candidates.append(total_time)
    horizon = max(value for value in horizon_candidates if math.isfinite(value) and value > 0)

    curve_points = 80
    curve_times = [horizon * i / curve_points for i in range(curve_points + 1)]
    reliability_curve = {
        "time_hours": curve_times,
        "reliability": [reliability(t) for t in curve_times],
        "hazard_per_hour": [
            hazard(t) if math.isfinite(hazard(t)) else None for t in curve_times
        ],
    }

    # Probability plot in linearizing coordinates.
    if failures:
        rank_points = _median_ranks(failures, suspensions)
        plot_times = [point["time_hours"] for point in rank_points]
        plot_ranks = [point["median_rank"] for point in rank_points]
        if distribution == "lognormal":
            plot_y = [_stats.normal_quantile(f) for f in plot_ranks]
            y_label = "Standard normal quantile of median rank"
            fit_y = [
                (math.log(t) - mu) / sigma for t in (min(plot_times), max(plot_times))
            ]
        elif distribution == "weibull":
            plot_y = [math.log(-math.log(1.0 - f)) for f in plot_ranks]
            y_label = "ln(-ln(1 - F))"
            fit_y = [
                beta * (math.log(t) - math.log(eta))
                for t in (min(plot_times), max(plot_times))
            ]
        else:
            plot_y = [math.log(-math.log(1.0 - f)) for f in plot_ranks]
            y_label = "ln(-ln(1 - F))"
            fit_y = [
                math.log(t / theta) for t in (min(plot_times), max(plot_times))
            ]
        probability_plot = {
            "transform": distribution,
            "time_hours": plot_times,
            "median_rank": plot_ranks,
            "plot_y": plot_y,
            "fit_time_hours": [min(plot_times), max(plot_times)],
            "fit_y": fit_y,
            "x_label": "Time (hours, log scale)",
            "y_label": y_label,
        }
    else:
        probability_plot = {
            "transform": distribution,
            "time_hours": [],
            "median_rank": [],
            "plot_y": [],
            "fit_time_hours": [],
            "fit_y": [],
            "x_label": "Time (hours, log scale)",
            "y_label": "",
        }

    # Assumption and sample-size warnings.
    if failures_observed == 0:
        notes.append(
            "No failures were observed, so there is no point estimate. Only the "
            "lower confidence bound is meaningful: the data proves the MTBF is "
            "at least that high."
        )
    elif failures_observed < 5:
        notes.append(
            f"Only {failures_observed} failure(s) in the data. The confidence "
            "interval is wide, and the point estimate on its own is not worth "
            "quoting without it."
        )

    if distribution == "exponential":
        notes.append(
            "The exponential fit assumes a constant failure rate: no infant "
            "mortality and no wear-out. Fit a Weibull to individual failure "
            "times to test that assumption."
        )
    else:
        notes.append(
            "This is a mean time to failure, not an MTBF. The hazard rate "
            "changes with age here, so reliability at a given time matters "
            "more than the mean."
        )

    if distribution == "weibull":
        if parameters["beta_lower"] is not None and parameters["beta_lower"] > 1.0:
            notes.append(
                f"Shape beta = {beta:.2f} with a confidence interval above 1, "
                "which is wear-out. A constant failure rate model would "
                "overstate late-life reliability."
            )
        elif parameters["beta_upper"] is not None and parameters["beta_upper"] < 1.0:
            notes.append(
                f"Shape beta = {beta:.2f} with a confidence interval below 1, "
                "which is infant mortality. Burn-in or screening is likely to "
                "pay off more than raising the MTBF target."
            )
        else:
            notes.append(
                f"Shape beta = {beta:.2f} with a confidence interval spanning 1, "
                "so the data does not rule out a constant failure rate."
            )

    if suspensions:
        notes.append(
            f"{len(suspensions)} suspended unit(s) contributed operating time "
            "without failing. Dropping them would bias the estimate low."
        )
    elif data_mode == "failure_times":
        notes.append(
            "No suspensions were entered, so every unit in the sample is treated "
            "as having failed and T is the sum of the failure times alone. If any "
            "units were still running when the test stopped, add their hours as "
            "suspensions: leaving them out understates T and the MTBF with it."
        )
        if test_termination == "time":
            notes.append(
                "A time-terminated test with no suspensions is contradictory: if "
                "the clock stopped the test, something was still running at the "
                "stop time. The bound has been computed as requested, but check "
                "whether suspensions are missing."
            )

    return {
        "distribution": distribution,
        "data_mode": data_mode,
        "test_termination": test_termination,
        "confidence_level": confidence_level,
        "total_operating_hours": total_time,
        "failure_count": failures_observed,
        "suspension_count": len(suspensions),
        "metric_label": metric_label,
        "mtbf_hours": point_estimate,
        "failure_rate_per_hour": failure_rate,
        "mtbf_lower_hours": lower,
        "mtbf_upper_hours": upper,
        "mtbf_lower_one_sided_hours": lower_one_sided,
        "parameters": parameters,
        "median_life_hours": median_life,
        "b10_life_hours": b10_life,
        "annualized_failure_rate": annualized_failure_rate,
        "expected_failures_per_unit_year": expected_failures_per_unit_year,
        "repair_time_hours": repair_time_hours,
        "availability": availability,
        "downtime_hours_per_year": downtime_hours_per_year,
        "mission_time_hours": mission_time_hours,
        "reliability_at_mission": reliability_at_mission,
        "mission_unit_count": mission_units,
        "mission_expected_survivors": mission_survivors,
        "mission_expected_failures": mission_failures,
        "mission_all_survive_probability": mission_all_survive,
        "mission_expected_repairs": mission_repairs,
        "reliability_curve": reliability_curve,
        "probability_plot": probability_plot,
        "notes": notes,
        "subst_point_estimate": subst.get("point_estimate", ""),
        "subst_lower_bound": subst.get("lower_bound", ""),
        "subst_upper_bound": subst.get("upper_bound", ""),
        "subst_shape": subst.get("shape", ""),
        "subst_scale": subst.get("scale", ""),
        "subst_b10": subst.get("b10", ""),
        "subst_reliability_at_mission": subst_reliability_at_mission,
    }
