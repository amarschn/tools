"""Static smoke tests for the Transient Heatsink tool's HTML/JS surface.

These tests don't drive a real browser — there's no Playwright/Selenium
setup in this repository — but they catch the most common failure modes
at near-zero cost:

* Every ``document.getElementById('foo')`` in the JS must point at an
  ``id="foo"`` somewhere in the HTML, otherwise a button is wired to
  nothing.
* The Pyodide bootstrap must fetch every ``pycalcs/<module>.py`` it
  later ``import``s, otherwise the page errors at load time the way
  it did when ``heatsinks`` was forgotten.
* Every sample ``test-cases/*.json`` simulates without errors and
  reports a sane status, so loading a sample never produces a broken
  results pane.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from pycalcs.thermal_transient import simulate_transient_thermal_model

TOOL_DIR = Path(__file__).parent.parent / "tools" / "transient-heatsink"
INDEX = TOOL_DIR / "index.html"
TEST_CASES_DIR = TOOL_DIR / "test-cases"


@pytest.fixture(scope="module")
def html_text() -> str:
    return INDEX.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# HTML / JS coupling                                                          #
# --------------------------------------------------------------------------- #


# IDs that the JS references but the HTML legitimately doesn't define
# inline (they're created at runtime by a render call). Add to this set
# only when an ID is genuinely dynamically inserted, not when one is
# missing-but-should-exist.
_ALLOWED_DYNAMIC_IDS: set[str] = set()


def _ids_in_js(html: str) -> set[str]:
    """Every literal id string referenced from JS via getElementById,
    querySelector('#id'), or similar."""
    ids: set[str] = set()
    ids.update(re.findall(r"""getElementById\(\s*['"]([\w-]+)['"]""", html))
    # querySelector('#foo') / querySelectorAll('#foo'); ignore class selectors.
    for sel in re.findall(
        r"""querySelector(?:All)?\(\s*['"]([^'"]+)['"]""", html
    ):
        for token in re.findall(r"#([\w-]+)", sel):
            ids.add(token)
    return ids


def _ids_in_html(html: str) -> set[str]:
    """Every id="..." attribute defined anywhere in the document."""
    return set(re.findall(r"""\bid=['"]([\w-]+)['"]""", html))


def test_every_js_referenced_id_exists_in_html(html_text: str) -> None:
    """Catches markup-vs-JS drift: if someone removes a button or input
    while leaving the JS handler in place, this test names the broken id."""
    referenced = _ids_in_js(html_text)
    defined = _ids_in_html(html_text)
    missing = referenced - defined - _ALLOWED_DYNAMIC_IDS
    # Filter out template-literal interpolations like 'tab-' + target — those
    # leave a stub like 'tab-' that won't match any literal id.
    missing = {m for m in missing if not m.endswith("-") and "${" not in m}
    assert not missing, (
        f"JS references these ids that aren't defined in the HTML: "
        f"{sorted(missing)}.  Either add the markup or remove the handler."
    )


def test_every_pyodide_imported_module_is_fetched(html_text: str) -> None:
    """The bootstrap must pyfetch every Python module it later imports —
    otherwise the page hits ImportError at load. Earlier, we shipped a
    bridge that imported `heatsinks` without fetching it."""
    # Find the bootstrap python block.
    match = re.search(
        r"""await\s+pyodide\.runPythonAsync\(`(.*?)`\)""",
        html_text,
        re.DOTALL,
    )
    assert match, "Could not locate the Pyodide bootstrap block."
    bootstrap = match.group(1)
    fetched = set(re.findall(r"""pyfetch\(['"][^'"]*?/([\w_]+)\.py""", bootstrap))
    # Match only top-level "import X" statements (not "from X import Y"),
    # since the latter pulls names out of an already-loaded module.
    imported = set(re.findall(r"""(?m)^\s*import\s+([\w_]+)\b""", bootstrap))
    not_fetched = imported - fetched
    # Ignore template variables like ${TOOL_MODULE_NAME} which the regex sees as bare uppercase names.
    not_fetched = {n for n in not_fetched if not n.isupper()}
    assert not not_fetched, (
        f"Imports without a pyfetch: {sorted(not_fetched)}. "
        "Add a pyfetch line for each, or the page will fail at load time."
    )


def test_every_sample_link_resolves_to_a_test_case_file(html_text: str) -> None:
    """Each Sample Test Cases link must point at a JSON file that exists."""
    srcs = re.findall(
        r"""class=['"]load-sample['"]\s+data-src=['"]([^'"]+)['"]""", html_text
    )
    assert srcs, "Found no .load-sample links in the HTML — the dropdown is empty."
    for src in srcs:
        target = TOOL_DIR / src
        assert target.exists(), (
            f"Sample link points at {src} but {target} does not exist."
        )


# --------------------------------------------------------------------------- #
# Sample test-case execution                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "case_path",
    sorted(TEST_CASES_DIR.glob("*.json")),
    ids=lambda p: p.name,
)
def test_sample_case_simulates_cleanly(case_path: Path) -> None:
    """Every shipped sample must simulate without errors and return a
    valid status — the user clicks 'Sample Test Cases' and expects a
    populated results pane, not a stack trace."""
    case = json.loads(case_path.read_text())
    assert "model" in case, f"{case_path.name} must wrap its model under a 'model' key."
    result = simulate_transient_thermal_model(case["model"])
    assert result["status"] != "invalid", (
        f"{case_path.name} produced invalid status with errors: {result.get('errors')}"
    )
    summary = result.get("summary") or {}
    assert summary.get("peak_temperature_c") is not None
    expected = case.get("expected_outputs") or {}
    expected_set = expected.get("status_is")
    if expected_set:
        assert result["status"] in expected_set, (
            f"{case_path.name} expected status in {expected_set} but got "
            f"{result['status']}."
        )

    for key, expected_value in expected.items():
        if key == "status_is":
            continue
        if key == "cycle_count_min":
            assert len(result.get("cycle_summary") or []) >= expected_value
            continue
        if key == "peak_node_id":
            assert summary.get(key) == expected_value
            continue
        if key.endswith("_is_finite"):
            metric = key.removesuffix("_is_finite")
            actual = summary.get(metric)
            assert actual is not None and math.isfinite(actual), (
                f"{case_path.name} expected finite {metric}, got {actual}."
            )
            continue
        if key.endswith("_min") or key.endswith("_max"):
            suffix = key[-4:]
            metric = key[:-4]
            actual = summary.get(metric)
            assert actual is not None, (
                f"{case_path.name} declares {key}, but summary has no {metric}."
            )
            if suffix == "_min":
                assert actual >= expected_value, (
                    f"{case_path.name}: {metric}={actual} < {expected_value}."
                )
            else:
                assert actual <= expected_value, (
                    f"{case_path.name}: {metric}={actual} > {expected_value}."
                )
            continue

        assert summary.get(key) == expected_value, (
            f"{case_path.name}: expected {key}={expected_value}, "
            f"got {summary.get(key)}."
        )
