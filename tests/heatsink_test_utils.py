"""
Utilities for JSON-driven heatsink benchmark tests.

Provides parameter resolution (UI display units → SI) and tolerance checking
so that test-case JSON files are the single source of truth for both the
browser UI and the pytest suite.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict

from pycalcs.heatsinks import HEATSINK_MATERIALS, analyze_plate_fin_heatsink

# Fields whose UI display units are mm but the Python function expects meters.
MM_FIELDS = frozenset([
    "base_length", "base_width", "base_thickness",
    "fin_height", "fin_thickness",
    "source_length", "source_width", "source_x", "source_y",
])

# Keys in the JSON that are metadata, not function parameters.
_META_KEYS = frozenset([
    "name", "description", "notes", "material_preset",
])

# Valid function parameter names (introspected once).
_VALID_PARAMS = set(inspect.signature(analyze_plate_fin_heatsink).parameters.keys())


def resolve_test_case_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert UI-level test-case parameters to ``analyze_plate_fin_heatsink`` kwargs.

    1. Resolve ``material_preset`` → ``material_conductivity`` + ``surface_emissivity``.
    2. Convert mm fields to meters.
    3. Drop keys that are not function parameters.
    """
    kwargs: Dict[str, Any] = {}

    # Resolve material preset first so explicit overrides take precedence.
    preset = params.get("material_preset")
    if preset and preset in HEATSINK_MATERIALS:
        mat = HEATSINK_MATERIALS[preset]
        kwargs["material_conductivity"] = mat["thermal_conductivity"]
        kwargs["surface_emissivity"] = mat["emissivity"]

    for key, value in params.items():
        if key in _META_KEYS:
            continue
        # Explicit conductivity/emissivity override the preset.
        if key in ("material_conductivity", "surface_emissivity"):
            kwargs[key] = float(value)
            continue
        if key in MM_FIELDS:
            kwargs[key] = float(value) / 1000.0
            continue
        if key in _VALID_PARAMS:
            # Coerce types appropriately.
            sig_param = inspect.signature(analyze_plate_fin_heatsink).parameters[key]
            annotation = sig_param.annotation
            if annotation is int:
                kwargs[key] = int(value)
            elif annotation is bool:
                kwargs[key] = value if isinstance(value, bool) else str(value).lower() == "true"
            elif annotation is float:
                kwargs[key] = float(value)
            else:
                kwargs[key] = value

    return kwargs


def check_tolerance(actual: Any, spec: Dict[str, Any], key: str = "") -> None:
    """Assert that *actual* satisfies the tolerance specification *spec*.

    Spec modes (checked in order):
      * ``{"exact": value}`` — ``actual == value``
      * ``{"min": lo}`` and/or ``{"max": hi}`` — range bounds
      * ``{"approx": ref, "rtol": 0.1}`` — relative tolerance
      * ``{"approx": ref, "atol": 2.0}`` — absolute tolerance
      * ``{"approx": ref}`` — default 5 % relative tolerance

    If both ``rtol`` and ``atol`` are present, the check passes when *either*
    tolerance is satisfied (matching ``pytest.approx`` semantics).
    """
    label = f" for '{key}'" if key else ""

    # Exact match (strings, enums, integers).
    if "exact" in spec:
        assert actual == spec["exact"], (
            f"Expected exact {spec['exact']!r}{label}, got {actual!r}"
        )
        return

    # Range bounds.
    if "min" in spec:
        assert actual >= spec["min"], (
            f"Value {actual}{label} below minimum {spec['min']}"
        )
    if "max" in spec:
        assert actual <= spec["max"], (
            f"Value {actual}{label} above maximum {spec['max']}"
        )

    # Approximate match.
    if "approx" in spec:
        expected = spec["approx"]
        rtol = spec.get("rtol")
        atol = spec.get("atol")
        if rtol is None and atol is None:
            rtol = 0.05  # default 5 %

        passes = False
        if atol is not None and abs(actual - expected) <= atol:
            passes = True
        if rtol is not None:
            if expected != 0:
                if abs(actual - expected) / abs(expected) <= rtol:
                    passes = True
            elif actual == 0:
                passes = True

        assert passes, (
            f"Value {actual}{label} not within tolerance of {expected} "
            f"(rtol={rtol}, atol={atol})"
        )
