import math

import pytest

from pycalcs.reliability import analyze_reliability


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
