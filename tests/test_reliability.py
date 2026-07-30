import math

import pytest

from pycalcs import _stats
from pycalcs.reliability import (
    _lognormal_log_likelihood,
    _median_ranks,
    _weibull_log_likelihood,
    analyze_reliability,
    estimate_mtbf,
)


def test_series_system_nominal():
    results = analyze_reliability(
        component_names=["A", "B", "C"],
        component_mtbf_hours=[100.0, 200.0, 300.0],
        component_series_count=[1, 1, 1],
        component_parallel_count=[1, 1, 1],
        mission_time_hours=100.0,
    )

    assert results["system_reliability"] == pytest.approx(0.1598797461, rel=1e-6)
    assert results["equivalent_failure_rate_per_hour"] == pytest.approx(0.0183333333, rel=1e-6)
    assert results["equivalent_mtbf_hours"] == pytest.approx(54.545454545, rel=1e-6)
    assert results["component_blocks"][0]["failure_rate_per_hour"] == pytest.approx(
        0.01, rel=1e-6
    )


def test_parallel_redundancy_and_allocation():
    results = analyze_reliability(
        component_names=["Pump"],
        component_mtbf_hours=[100.0],
        component_series_count=[1],
        component_parallel_count=[2],
        mission_time_hours=50.0,
        target_system_reliability=0.9,
        allocation_component_count=3,
    )

    expected_single = math.exp(-0.5)
    expected_parallel = 1.0 - (1.0 - expected_single) ** 2
    expected_lambda_eq = -math.log(expected_parallel) / 50.0

    assert results["system_reliability"] == pytest.approx(expected_parallel, rel=1e-6)
    assert results["equivalent_failure_rate_per_hour"] == pytest.approx(
        expected_lambda_eq, rel=1e-6
    )
    assert results["allocation_required_reliability"] == pytest.approx(
        0.9 ** (1.0 / 3.0), rel=1e-6
    )


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        analyze_reliability(
            component_names=["Bad"],
            component_mtbf_hours=[-1.0],
            component_series_count=[1],
            component_parallel_count=[1],
            mission_time_hours=10.0,
        )


# ---------------------------------------------------------------------
# Special functions used by the MTBF estimator
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "probability, dof, expected",
    [
        (0.95, 6, 12.59159),
        (0.05, 4, 0.710723),
        (0.975, 10, 20.48318),
        (0.99, 1, 6.634897),
        (0.90, 2, 4.605170),
    ],
)
def test_chi2_quantile_matches_tables(probability, dof, expected):
    assert _stats.chi2_quantile(probability, dof) == pytest.approx(expected, rel=1e-5)


@pytest.mark.parametrize(
    "probability, expected",
    [(0.975, 1.959964), (0.90, 1.281552), (0.10, -1.281552), (1e-8, -5.612001)],
)
def test_normal_quantile_matches_tables(probability, expected):
    assert _stats.normal_quantile(probability) == pytest.approx(expected, rel=1e-6)


def test_normal_cdf_round_trip():
    for probability in (0.01, 0.25, 0.5, 0.8, 0.999):
        z = _stats.normal_quantile(probability)
        assert _stats.normal_cdf(z) == pytest.approx(probability, rel=1e-12)


def test_gamma_p_known_values():
    # P(1, x) is the exponential CDF.
    assert _stats.gamma_p(1.0, 2.0) == pytest.approx(1.0 - math.exp(-2.0), rel=1e-12)
    assert _stats.gamma_p(0.5, 0.5) == pytest.approx(math.erf(math.sqrt(0.5)), rel=1e-12)


# ---------------------------------------------------------------------
# Exponential MTBF estimation
# ---------------------------------------------------------------------


def test_exponential_aggregate_time_terminated():
    """Two failures in 1000 unit-hours, 90% two-sided interval.

    Textbook result: point 500 hr, bounds 158.8 hr and 2814 hr
    (Ebeling, An Introduction to Reliability and Maintainability
    Engineering, Chapter 12).
    """
    results = estimate_mtbf(
        distribution="exponential",
        data_mode="aggregate",
        total_operating_hours=1000.0,
        failure_count=2,
        test_termination="time",
        confidence_level=0.9,
        mission_time_hours=100.0,
    )

    assert results["metric_label"] == "MTBF"
    assert results["mtbf_hours"] == pytest.approx(500.0, rel=1e-9)
    assert results["failure_rate_per_hour"] == pytest.approx(0.002, rel=1e-9)
    assert results["mtbf_lower_hours"] == pytest.approx(158.836, rel=1e-4)
    assert results["mtbf_upper_hours"] == pytest.approx(2814.036, rel=1e-4)
    assert results["reliability_at_mission"] == pytest.approx(math.exp(-0.2), rel=1e-9)
    assert results["median_life_hours"] == pytest.approx(500.0 * math.log(2.0), rel=1e-9)
    assert results["b10_life_hours"] == pytest.approx(-500.0 * math.log(0.9), rel=1e-9)


def test_exponential_failure_terminated_lower_bound_uses_2r_dof():
    """Failure-terminated tests lose the +2 degrees of freedom."""
    time_terminated = estimate_mtbf(
        data_mode="aggregate",
        total_operating_hours=1000.0,
        failure_count=2,
        test_termination="time",
        confidence_level=0.9,
    )
    failure_terminated = estimate_mtbf(
        data_mode="aggregate",
        total_operating_hours=1000.0,
        failure_count=2,
        test_termination="failure",
        confidence_level=0.9,
    )

    assert failure_terminated["mtbf_lower_hours"] == pytest.approx(
        2000.0 / _stats.chi2_quantile(0.95, 4), rel=1e-9
    )
    assert time_terminated["mtbf_lower_hours"] == pytest.approx(
        2000.0 / _stats.chi2_quantile(0.95, 6), rel=1e-9
    )
    # Same point estimate, but the failure-terminated bound is less punishing.
    assert failure_terminated["mtbf_hours"] == time_terminated["mtbf_hours"]
    assert failure_terminated["mtbf_lower_hours"] > time_terminated["mtbf_lower_hours"]
    assert failure_terminated["mtbf_upper_hours"] == pytest.approx(
        time_terminated["mtbf_upper_hours"], rel=1e-12
    )


def test_fleet_mode_multiplies_units_by_hours():
    results = estimate_mtbf(
        data_mode="fleet",
        unit_count=10,
        hours_per_unit=500.0,
        failure_count=4,
    )
    assert results["total_operating_hours"] == pytest.approx(5000.0, rel=1e-12)
    assert results["mtbf_hours"] == pytest.approx(1250.0, rel=1e-12)


def test_zero_failures_gives_lower_bound_only():
    """With no failures the MTBF is unbounded above; only a floor is provable."""
    results = estimate_mtbf(
        data_mode="fleet",
        unit_count=10,
        hours_per_unit=500.0,
        failure_count=0,
        confidence_level=0.9,
    )

    assert math.isinf(results["mtbf_hours"])
    assert math.isinf(results["mtbf_upper_hours"])
    # One-sided 90% lower bound is T / -ln(0.10).
    assert results["mtbf_lower_one_sided_hours"] == pytest.approx(
        5000.0 / -math.log(0.10), rel=1e-6
    )
    assert any("No failures" in note for note in results["notes"])


def test_exponential_from_failure_times_includes_suspensions():
    results = estimate_mtbf(
        data_mode="failure_times",
        failure_times_hours=[100.0, 200.0, 300.0],
        suspension_times_hours=[400.0],
    )
    assert results["total_operating_hours"] == pytest.approx(1000.0, rel=1e-12)
    assert results["failure_count"] == 3
    assert results["suspension_count"] == 1
    assert results["mtbf_hours"] == pytest.approx(1000.0 / 3.0, rel=1e-12)


# ---------------------------------------------------------------------
# Weibull estimation
# ---------------------------------------------------------------------

WEIBULL_SAMPLE = [30.0, 49.0, 82.0, 90.0, 96.0]


def _weibull_grid_maximum(failures, suspensions, steps=40000):
    """Brute-force profile likelihood maximum, used to check the solver."""
    best = None
    total = len(failures)
    for index in range(1, steps):
        beta = index * 0.001
        scale = (
            sum(t ** beta for t in failures + suspensions) / total
        ) ** (1.0 / beta)
        value = _weibull_log_likelihood(beta, scale, failures, suspensions)
        if best is None or value > best[0]:
            best = (value, beta, scale)
    return best[1], best[2]


def test_weibull_complete_data_matches_grid_search():
    results = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=WEIBULL_SAMPLE,
        mission_time_hours=50.0,
    )
    beta = results["parameters"]["beta"]
    eta = results["parameters"]["eta_hours"]

    grid_beta, grid_eta = _weibull_grid_maximum(WEIBULL_SAMPLE, [])
    assert beta == pytest.approx(grid_beta, abs=1e-3)
    assert eta == pytest.approx(grid_eta, rel=1e-4)

    assert results["metric_label"] == "MTTF"
    assert results["mtbf_hours"] == pytest.approx(eta * math.gamma(1.0 + 1.0 / beta), rel=1e-12)
    assert results["median_life_hours"] == pytest.approx(
        eta * math.log(2.0) ** (1.0 / beta), rel=1e-12
    )
    assert results["b10_life_hours"] == pytest.approx(
        eta * (-math.log(0.9)) ** (1.0 / beta), rel=1e-12
    )
    assert results["reliability_at_mission"] == pytest.approx(
        math.exp(-((50.0 / eta) ** beta)), rel=1e-12
    )
    assert 0.0 < results["mtbf_lower_hours"] < results["mtbf_hours"] < results["mtbf_upper_hours"]


def test_weibull_censored_data_matches_grid_search():
    failures = [30.0, 49.0, 82.0]
    suspensions = [90.0, 96.0]
    results = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=failures,
        suspension_times_hours=suspensions,
    )
    grid_beta, grid_eta = _weibull_grid_maximum(failures, suspensions)

    assert results["parameters"]["beta"] == pytest.approx(grid_beta, abs=1e-3)
    assert results["parameters"]["eta_hours"] == pytest.approx(grid_eta, rel=1e-4)
    # Ignoring the suspensions would pull the scale down.
    ignored = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=failures,
    )
    assert results["parameters"]["eta_hours"] > ignored["parameters"]["eta_hours"]


def test_weibull_recovers_known_shape_from_large_sample():
    """A quantile-spaced sample from beta=2.5, eta=1000 fits back to itself."""
    beta_true, eta_true = 2.5, 1000.0
    sample = [
        eta_true * (-math.log(1.0 - (i - 0.5) / 200.0)) ** (1.0 / beta_true)
        for i in range(1, 201)
    ]
    results = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=sample,
    )
    assert results["parameters"]["beta"] == pytest.approx(beta_true, rel=0.02)
    assert results["parameters"]["eta_hours"] == pytest.approx(eta_true, rel=0.02)
    assert results["parameters"]["beta_lower"] > 1.0


def test_weibull_shape_note_flags_wear_out():
    beta_true, eta_true = 3.0, 500.0
    sample = [
        eta_true * (-math.log(1.0 - (i - 0.5) / 100.0)) ** (1.0 / beta_true)
        for i in range(1, 101)
    ]
    results = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=sample,
    )
    assert any("wear-out" in note for note in results["notes"])


# ---------------------------------------------------------------------
# Lognormal estimation
# ---------------------------------------------------------------------


def test_lognormal_complete_data_closed_form():
    results = estimate_mtbf(
        distribution="lognormal",
        data_mode="failure_times",
        failure_times_hours=WEIBULL_SAMPLE,
        mission_time_hours=50.0,
    )
    logs = [math.log(t) for t in WEIBULL_SAMPLE]
    mu = sum(logs) / len(logs)
    sigma = math.sqrt(sum((x - mu) ** 2 for x in logs) / len(logs))

    assert results["parameters"]["mu"] == pytest.approx(mu, rel=1e-12)
    assert results["parameters"]["sigma"] == pytest.approx(sigma, rel=1e-12)
    assert results["mtbf_hours"] == pytest.approx(math.exp(mu + 0.5 * sigma**2), rel=1e-12)
    assert results["median_life_hours"] == pytest.approx(math.exp(mu), rel=1e-12)
    assert results["b10_life_hours"] == pytest.approx(
        math.exp(mu + sigma * _stats.normal_quantile(0.10)), rel=1e-9
    )
    assert results["reliability_at_mission"] == pytest.approx(
        _stats.normal_cdf(-(math.log(50.0) - mu) / sigma), rel=1e-12
    )


def test_lognormal_censored_beats_complete_data_likelihood():
    """The censored fit must maximise the censored likelihood, not the naive one."""
    failures = [30.0, 49.0, 82.0]
    suspensions = [90.0, 96.0]
    results = estimate_mtbf(
        distribution="lognormal",
        data_mode="failure_times",
        failure_times_hours=failures,
        suspension_times_hours=suspensions,
    )
    mu = results["parameters"]["mu"]
    sigma = results["parameters"]["sigma"]
    fitted = _lognormal_log_likelihood(mu, sigma, failures, suspensions)

    logs = [math.log(t) for t in failures]
    naive_mu = sum(logs) / len(logs)
    naive_sigma = math.sqrt(sum((x - naive_mu) ** 2 for x in logs) / len(logs))
    naive = _lognormal_log_likelihood(naive_mu, naive_sigma, failures, suspensions)

    assert fitted > naive
    # Grid check on the same likelihood surface.
    best = max(
        _lognormal_log_likelihood(m * 0.005, s * 0.005, failures, suspensions)
        for m in range(600, 1200)
        for s in range(20, 300)
    )
    assert fitted >= best - 1e-4


# ---------------------------------------------------------------------
# Plotting positions and validation
# ---------------------------------------------------------------------


def test_median_ranks_benard_without_suspensions():
    points = _median_ranks([10.0, 20.0, 30.0, 40.0, 50.0], [])
    ranks = [point["median_rank"] for point in points]
    expected = [(i - 0.3) / 5.4 for i in range(1, 6)]
    assert ranks == pytest.approx(expected, rel=1e-12)


def test_median_ranks_johnson_adjusted_with_suspensions():
    """Classic worked example: suspensions push later failures up the ranks."""
    points = _median_ranks([12.0, 20.0, 29.0], [10.0, 15.0, 25.0])
    adjusted = [point["adjusted_rank"] for point in points]
    assert adjusted == pytest.approx([1.1667, 2.625, 4.8125], rel=1e-4)


def test_probability_plot_line_passes_through_fit():
    results = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=WEIBULL_SAMPLE,
    )
    plot = results["probability_plot"]
    beta = results["parameters"]["beta"]
    eta = results["parameters"]["eta_hours"]

    assert plot["transform"] == "weibull"
    assert len(plot["time_hours"]) == len(WEIBULL_SAMPLE)
    for time_hours, y in zip(plot["fit_time_hours"], plot["fit_y"]):
        assert y == pytest.approx(beta * math.log(time_hours / eta), rel=1e-12)


def test_reliability_curve_is_monotonic():
    results = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=WEIBULL_SAMPLE,
    )
    curve = results["reliability_curve"]["reliability"]
    assert curve[0] == pytest.approx(1.0, rel=1e-12)
    assert all(later <= earlier + 1e-12 for earlier, later in zip(curve, curve[1:]))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"distribution": "gumbel", "data_mode": "aggregate"},
        {"data_mode": "monte-carlo"},
        {"data_mode": "aggregate", "total_operating_hours": 0.0, "failure_count": 1},
        {"data_mode": "aggregate", "total_operating_hours": 100.0, "failure_count": None},
        {"data_mode": "fleet", "unit_count": 0, "hours_per_unit": 10.0, "failure_count": 1},
        {"data_mode": "failure_times", "failure_times_hours": []},
        {"data_mode": "failure_times", "failure_times_hours": [-5.0]},
        {
            "data_mode": "aggregate",
            "total_operating_hours": 100.0,
            "failure_count": 0,
            "test_termination": "failure",
        },
        {
            "distribution": "weibull",
            "data_mode": "aggregate",
            "total_operating_hours": 100.0,
            "failure_count": 3,
        },
        {"distribution": "weibull", "data_mode": "failure_times", "failure_times_hours": [10.0]},
        {
            "data_mode": "aggregate",
            "total_operating_hours": 100.0,
            "failure_count": 1,
            "confidence_level": 1.0,
        },
        {
            "data_mode": "aggregate",
            "total_operating_hours": 100.0,
            "failure_count": 1,
            "mission_time_hours": 0.0,
        },
    ],
)
def test_estimate_mtbf_invalid_inputs_raise(kwargs):
    with pytest.raises(ValueError):
        estimate_mtbf(**kwargs)


# ---------------------------------------------------------------------
# Mission projection
# ---------------------------------------------------------------------


def test_mission_projection_onto_a_fleet():
    """1000-hour mission on 100 units at MTBF 2920 h."""
    results = estimate_mtbf(
        data_mode="aggregate",
        total_operating_hours=8760.0,
        failure_count=3,
        mission_time_hours=1000.0,
        mission_unit_count=100,
    )
    reliability = math.exp(-1000.0 / 2920.0)

    assert results["reliability_at_mission"] == pytest.approx(reliability, rel=1e-12)
    assert results["mission_unit_count"] == 100
    assert results["mission_expected_survivors"] == pytest.approx(100 * reliability, rel=1e-12)
    assert results["mission_expected_failures"] == pytest.approx(100 * (1 - reliability), rel=1e-12)
    assert results["mission_all_survive_probability"] == pytest.approx(reliability**100, rel=1e-9)
    # Repairable reading: expected failures to fix over the mission is N*t/MTBF.
    assert results["mission_expected_repairs"] == pytest.approx(100 * 1000.0 / 2920.0, rel=1e-12)
    # Survivors plus failures must account for the whole fleet.
    assert results["mission_expected_survivors"] + results["mission_expected_failures"] == (
        pytest.approx(100.0, rel=1e-12)
    )


def test_mission_projection_defaults_to_one_unit():
    results = estimate_mtbf(
        data_mode="aggregate",
        total_operating_hours=8760.0,
        failure_count=3,
        mission_time_hours=1000.0,
    )
    assert results["mission_unit_count"] == 1
    assert results["mission_expected_survivors"] == pytest.approx(
        results["reliability_at_mission"], rel=1e-12
    )


def test_mission_projection_absent_without_a_mission_time():
    results = estimate_mtbf(
        data_mode="aggregate", total_operating_hours=8760.0, failure_count=3
    )
    assert results["mission_unit_count"] is None
    assert results["mission_expected_survivors"] is None
    assert results["mission_all_survive_probability"] is None
    assert results["subst_reliability_at_mission"] == ""


def test_repair_count_is_exponential_only():
    """A renewal rate needs a constant hazard, so wear-out fits must not report one."""
    shared = dict(
        data_mode="failure_times",
        failure_times_hours=[142.0, 267.0, 310.0, 420.0, 586.0],
        suspension_times_hours=[700.0, 700.0],
        mission_time_hours=300.0,
        mission_unit_count=50,
    )
    exponential = estimate_mtbf(distribution="exponential", **shared)
    weibull = estimate_mtbf(distribution="weibull", **shared)
    lognormal = estimate_mtbf(distribution="lognormal", **shared)

    assert exponential["mission_expected_repairs"] is not None
    assert weibull["mission_expected_repairs"] is None
    assert lognormal["mission_expected_repairs"] is None
    # Survivor projections are still available for every distribution.
    for results in (exponential, weibull, lognormal):
        assert 0.0 < results["mission_expected_survivors"] < 50.0


def test_mission_unit_count_must_be_positive():
    with pytest.raises(ValueError):
        estimate_mtbf(
            data_mode="aggregate",
            total_operating_hours=100.0,
            failure_count=1,
            mission_time_hours=10.0,
            mission_unit_count=0,
        )


def test_missing_suspensions_are_called_out():
    """The costly mistake is omitting units that never failed, so it must be flagged."""
    results = estimate_mtbf(
        data_mode="failure_times",
        failure_times_hours=[142.0, 267.0, 310.0],
    )
    assert any("No suspensions were entered" in note for note in results["notes"])


def test_time_terminated_without_suspensions_is_flagged_as_contradictory():
    results = estimate_mtbf(
        data_mode="failure_times",
        failure_times_hours=[142.0, 267.0, 310.0],
        test_termination="time",
    )
    assert any("contradictory" in note for note in results["notes"])
    # Still computes, since the caller may know something the data does not show.
    assert results["mtbf_hours"] == pytest.approx(719.0 / 3.0, rel=1e-12)


def test_omitting_suspensions_understates_the_estimate():
    """Quantifies the trap: 20 units at 1000 h with 3 failures."""
    failures = [142.0, 267.0, 310.0]
    complete = estimate_mtbf(
        data_mode="failure_times",
        failure_times_hours=failures,
        suspension_times_hours=[1000.0] * 17,
    )
    forgotten = estimate_mtbf(data_mode="failure_times", failure_times_hours=failures)

    assert complete["total_operating_hours"] == pytest.approx(17719.0, rel=1e-12)
    assert forgotten["total_operating_hours"] == pytest.approx(719.0, rel=1e-12)
    assert complete["mtbf_hours"] > 20 * forgotten["mtbf_hours"]


# ---------------------------------------------------------------------
# Annualized failure rate and availability
# ---------------------------------------------------------------------


def test_annualized_failure_rate_is_share_of_units_failing_in_a_year():
    results = estimate_mtbf(
        data_mode="aggregate", total_operating_hours=8760.0, failure_count=3
    )
    assert results["mtbf_hours"] == pytest.approx(2920.0, rel=1e-12)
    assert results["annualized_failure_rate"] == pytest.approx(
        1.0 - math.exp(-8760.0 / 2920.0), rel=1e-12
    )
    # Two definitions, deliberately both reported: 95% of units fail within a
    # year, but a repaired unit averages 3 failures over that year.
    assert results["annualized_failure_rate"] == pytest.approx(0.950213, rel=1e-5)
    assert results["expected_failures_per_unit_year"] == pytest.approx(3.0, rel=1e-12)


def test_afr_definitions_converge_for_long_lived_items():
    """At a million-hour MTBF the two AFR readings agree to within a rounding."""
    results = estimate_mtbf(
        data_mode="aggregate", total_operating_hours=1e6, failure_count=1
    )
    assert results["annualized_failure_rate"] == pytest.approx(
        results["expected_failures_per_unit_year"], rel=0.005
    )


def test_afr_uses_the_fitted_distribution_not_just_the_mean():
    """For a wear-out fit the AFR must come from R(8760), not from 8760/MTTF."""
    results = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=[9000.0, 11000.0, 12000.0, 13000.0, 15000.0],
    )
    eta = results["parameters"]["eta_hours"]
    beta = results["parameters"]["beta"]
    assert results["annualized_failure_rate"] == pytest.approx(
        1.0 - math.exp(-((8760.0 / eta) ** beta)), rel=1e-12
    )
    # Repair counts need a constant hazard, so this stays unavailable.
    assert results["expected_failures_per_unit_year"] is None


def test_availability_and_downtime():
    results = estimate_mtbf(
        data_mode="aggregate",
        total_operating_hours=8760.0,
        failure_count=3,
        repair_time_hours=4.0,
    )
    assert results["availability"] == pytest.approx(2920.0 / 2924.0, rel=1e-12)
    assert results["downtime_hours_per_year"] == pytest.approx(
        (1 - 2920.0 / 2924.0) * 8760.0, rel=1e-12
    )
    # Roughly 12 hours a year down.
    assert results["downtime_hours_per_year"] == pytest.approx(11.98, rel=1e-2)


def test_availability_absent_without_a_repair_time():
    results = estimate_mtbf(
        data_mode="aggregate", total_operating_hours=8760.0, failure_count=3
    )
    assert results["availability"] is None
    assert results["downtime_hours_per_year"] is None
    assert results["repair_time_hours"] is None


def test_availability_holds_for_wear_out_distributions():
    """Long-run availability of an alternating renewal process depends only on
    the means, so it is valid for any life distribution."""
    results = estimate_mtbf(
        distribution="weibull",
        data_mode="failure_times",
        failure_times_hours=[142.0, 267.0, 310.0, 420.0, 586.0],
        suspension_times_hours=[700.0, 700.0],
        repair_time_hours=8.0,
    )
    mttf = results["mtbf_hours"]
    assert results["availability"] == pytest.approx(mttf / (mttf + 8.0), rel=1e-12)


def test_zero_repair_time_gives_full_availability():
    results = estimate_mtbf(
        data_mode="aggregate",
        total_operating_hours=8760.0,
        failure_count=3,
        repair_time_hours=0.0,
    )
    assert results["availability"] == pytest.approx(1.0, rel=1e-12)
    assert results["downtime_hours_per_year"] == pytest.approx(0.0, abs=1e-9)


def test_negative_repair_time_raises():
    with pytest.raises(ValueError):
        estimate_mtbf(
            data_mode="aggregate",
            total_operating_hours=100.0,
            failure_count=1,
            repair_time_hours=-1.0,
        )
