"""
JSON-driven benchmark and regression tests for the heatsink tool.

Discovers test-case JSON files in ``tools/simple_thermal/test-cases/``.
Files that include an ``expected_outputs`` key are treated as validation
benchmarks; all files are checked for crash-free execution.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pycalcs.heatsinks import analyze_plate_fin_heatsink
from tests.heatsink_test_utils import check_tolerance, resolve_test_case_parameters

CASES_DIR = Path(__file__).resolve().parent.parent / "tools" / "simple_thermal" / "test-cases"


def _load_cases(require_expected: bool = False):
    """Discover test-case JSONs, optionally filtering to those with expected outputs."""
    cases = []
    for json_path in sorted(CASES_DIR.glob("*.json")):
        with open(json_path) as f:
            data = json.load(f)
        if require_expected and "expected_outputs" not in data:
            continue
        cases.append(pytest.param(data, id=json_path.stem))
    return cases


# ---------------------------------------------------------------------------
# Benchmark tests — validate outputs against expected tolerances
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", _load_cases(require_expected=True))
def test_benchmark_case(case):
    """Run a benchmark test case and check all expected outputs."""
    kwargs = resolve_test_case_parameters(case["parameters"])
    result = analyze_plate_fin_heatsink(**kwargs)

    for key, spec in case["expected_outputs"].items():
        assert key in result, (
            f"Output key '{key}' not found in result. "
            f"Available keys: {sorted(result.keys())}"
        )
        check_tolerance(result[key], spec, key=key)


# ---------------------------------------------------------------------------
# Smoke tests — every JSON should run without crashing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", _load_cases(require_expected=False))
def test_case_runs_without_error(case):
    """Every test-case JSON should produce a valid result dict."""
    kwargs = resolve_test_case_parameters(case["parameters"])
    result = analyze_plate_fin_heatsink(**kwargs)
    assert "status" in result, "Result missing 'status' key"
    assert "sink_thermal_resistance" in result
