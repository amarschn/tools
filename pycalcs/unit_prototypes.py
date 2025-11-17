"""
Prototype-specific wrappers for unit conversion explorations.

These helpers lean on ``pycalcs.units`` so the UI can experiment with
different interaction models while sharing the same calculation backbone.
"""

from __future__ import annotations

from typing import Dict, Iterable

from . import units


def convert_unit_pair(quantity: str, from_unit: str, to_unit: str, value: float) -> dict[str, float]:
    """
    Convert a value between two arbitrary units within a quantity.

    This helper exposes the lower-level conversion routines with additional
    metadata useful for interactive UI prototypes (e.g. revealing the base-unit
    value or whether a pure multiplier exists).

    ---Parameters---
    quantity : str
        Quantity identifier supported by ``pycalcs.units`` (e.g. ``"length"`` or ``"pressure"``).
    from_unit : str
        Symbol for the source unit.
    to_unit : str
        Symbol for the destination unit.
    value : float
        Numerical value expressed in the source unit.

    ---Returns---
    converted_value : float
        Value expressed in the destination unit.
    base_value : float
        Intermediate value normalised to the quantity's base SI unit.
    has_multiplier_only : bool
        ``True`` when the conversion is purely multiplicative (no offset).
    multiplier : float
        Constant factor relating the source and destination units when available, otherwise ``0.0``.

    ---LaTeX---
    x_{\\text{base}} = f_{\\text{from}}(x_{\\text{from}}),\\quad
    x_{\\text{to}} = f_{\\text{to}}^{-1}(x_{\\text{base}})

    ---References---
    BIPM. (2019). *The International System of Units (SI)*, 9th edition.
    """

    numeric_value = float(value)
    converted = units.convert_value(quantity, from_unit, to_unit, numeric_value)
    base_value = units.QUANTITY_DEFINITIONS[quantity.lower()][from_unit].to_base(numeric_value)

    has_multiplier = False
    multiplier = 0.0
    try:
        multiplier = units.conversion_factor(quantity, from_unit, to_unit)
        has_multiplier = True
    except ValueError:
        has_multiplier = False

    return {
        "converted_value": converted,
        "base_value": base_value,
        "has_multiplier_only": has_multiplier,
        "multiplier": multiplier if has_multiplier else 0.0,
        "subst_converted_value": (
            f"x_{{\\text{{to}}}} = f_{{{to_unit}}}^{{-1}}"
            f"(f_{{{from_unit}}}({numeric_value})) = {converted:.6g}"
        ),
        "subst_base_value": f"x_{{\\text{{base}}}} = f_{{{from_unit}}}({numeric_value}) = {base_value:.6g}",
        "subst_multiplier": (
            f"k = \\frac{{f_{{{to_unit}}}^{{-1}}"
            f"(f_{{{from_unit}}}(1))}}{{1}} = {multiplier:.6g}"
            if has_multiplier
            else ""
        ),
    }


_SYSTEM_SCENARIOS: Dict[str, Dict[str, str]] = {
    "length_precision": {
        "quantity": "length",
        "imperial_unit": "in",
        "metric_unit": "mm",
        "label": "Precision length (inch <-> millimetre)",
        "description": "Machine design tolerancing and layout conversions between inches and millimetres.",
    },
    "pressure_hydraulics": {
        "quantity": "pressure",
        "imperial_unit": "psi",
        "metric_unit": "MPa",
        "label": "Hydraulic pressure (psi <-> MPa)",
        "description": "Hydraulic cylinder pressure translation between US customary and SI units.",
    },
    "velocity_transport": {
        "quantity": "velocity",
        "imperial_unit": "mph",
        "metric_unit": "km/h",
        "label": "Vehicle velocity (mph <-> km/h)",
        "description": "Road vehicle speed limits and performance comparisons.",
    },
}


def list_system_scenarios() -> dict[str, dict[str, str]]:
    """
    List the curated imperial ↔ metric scenarios with metadata for UI use.

    ---Returns---
    scenarios : dict[str, dict[str, str]]
        Mapping from scenario key to metadata fields (``label``, ``description``,
        ``quantity``, ``imperial_unit``, ``metric_unit``).

    ---LaTeX---
    \\mathcal{S} = \\{ (k, m_k) \\mid k \\in K \\}
    """

    data: dict[str, dict[str, str]] = {}
    for key, spec in _SYSTEM_SCENARIOS.items():
        data[key] = {
            "label": spec["label"],
            "description": spec["description"],
            "quantity": spec["quantity"],
            "imperial_unit": spec["imperial_unit"],
            "metric_unit": spec["metric_unit"],
        }
    return data


def convert_between_primary_systems(scenario: str, direction: str, value: float) -> dict[str, float]:
    """
    Convert a value between paired imperial and metric units for curated scenarios.

    Each ``scenario`` encodes the quantity and canonical unit pairing so the UI
    can experiment with radio-button workflows without forcing users to pick
    every unit manually.

    ---Parameters---
    scenario : str
        Scenario key (e.g. ``"length_precision"``). See ``_SYSTEM_SCENARIOS`` for options.
    direction : str
        Either ``"imperial_to_metric"`` or ``"metric_to_imperial"`` specifying where the input value lives.
    value : float
        Numerical value expressed in the system identified by ``direction``.

    ---Returns---
    imperial_value : float
        Value normalised to the scenario's imperial unit.
    metric_value : float
        Equivalent value expressed in the scenario's metric unit.
    imperial_unit : str
        Symbol for the imperial unit linked to the scenario.
    metric_unit : str
        Symbol for the metric unit linked to the scenario.

    ---LaTeX---
    x_{\\text{metric}} = f_{\\text{metric}}^{-1}\\bigl(f_{\\text{imperial}}(x_{\\text{imperial}})\\bigr)
    """

    scenario_key = scenario.strip()
    if scenario_key not in _SYSTEM_SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'.")

    direction_key = direction.strip().lower()
    if direction_key not in {"imperial_to_metric", "metric_to_imperial"}:
        raise ValueError("Direction must be 'imperial_to_metric' or 'metric_to_imperial'.")

    spec = _SYSTEM_SCENARIOS[scenario_key]
    quantity = spec["quantity"]
    imperial_unit = spec["imperial_unit"]
    metric_unit = spec["metric_unit"]

    numeric_value = float(value)

    if direction_key == "imperial_to_metric":
        imperial_value = numeric_value
        metric_value = units.convert_value(quantity, imperial_unit, metric_unit, numeric_value)
    else:
        metric_value = numeric_value
        imperial_value = units.convert_value(quantity, metric_unit, imperial_unit, numeric_value)

    return {
        "imperial_value": imperial_value,
        "metric_value": metric_value,
        "imperial_unit": imperial_unit,
        "metric_unit": metric_unit,
        "subst_imperial_value": (
            f"x_{{\\text{{imperial}}}} = {imperial_value:.6g}~\\text{{{imperial_unit}}}"
        ),
        "subst_metric_value": (
            f"x_{{\\text{{metric}}}} = f_{{{metric_unit}}}^{{-1}}"
            f"(f_{{{imperial_unit}}}({imperial_value})) = {metric_value:.6g}"
            if direction_key == "imperial_to_metric"
            else f"x_{{\\text{{metric}}}} = {metric_value:.6g}~\\text{{{metric_unit}}}"
        ),
    }


_SCALE_CASES: Dict[str, Dict[str, Iterable[str]]] = {
    "stress_band": {
        "quantity": "pressure",
        "units": ("Pa", "kPa", "MPa"),
        "label": "Stress band (Pa / kPa / MPa)",
        "description": "Material and structural stress magnitudes across SI prefixes.",
    },
    "velocity_band": {
        "quantity": "velocity",
        "units": ("m/s", "km/h", "mph"),
        "label": "Velocity band (m/s / km/h / mph)",
        "description": "Linear speed comparison between SI and transport-friendly units.",
    },
}


def list_scale_cases() -> dict[str, dict[str, str]]:
    """
    Provide metadata for the predefined scaling bands.

    ---Returns---
    scale_cases : dict[str, dict[str, str]]
        Mapping from scale case key to ``label``, ``description``, ``quantity``,
        and a comma-delimited ``units`` string.

    ---LaTeX---
    \\mathcal{C} = \\{ (k, m_k) \\mid k \\in K \\}
    """

    data: dict[str, dict[str, str]] = {}
    for key, spec in _SCALE_CASES.items():
        units_sequence = tuple(spec["units"])
        data[key] = {
            "label": spec["label"],
            "description": spec["description"],
            "quantity": spec["quantity"],
            "units": ", ".join(units_sequence),
        }
    return data


def cascade_unit_scales(scale_case: str, anchor_unit: str, value: float) -> dict[str, float]:
    """
    Project a measurement across a curated trio of units to study order-of-magnitude changes.

    ---Parameters---
    scale_case : str
        Scale grouping key (``"stress_band"`` or ``"velocity_band"``).
    anchor_unit : str
        Unit symbol for the provided value. Must belong to the case's unit triplet.
    value : float
        Numerical value expressed in ``anchor_unit``.

    ---Returns---
    value_unit_1 : float
        Converted magnitude in the first unit listed for the case.
    value_unit_2 : float
        Converted magnitude in the second unit listed for the case.
    value_unit_3 : float
        Converted magnitude in the third unit listed for the case.
    unit_label_1 : str
        Symbol for the first unit.
    unit_label_2 : str
        Symbol for the second unit.
    unit_label_3 : str
        Symbol for the third unit.

    ---LaTeX---
    x_{i} = f_{u_i}^{-1}\\bigl(f_{u_a}(x_{a})\\bigr) \\quad \\text{for } i \\in \\{1,2,3\\}
    """

    case_key = scale_case.strip()
    if case_key not in _SCALE_CASES:
        raise ValueError(f"Unknown scale case '{scale_case}'.")

    config = _SCALE_CASES[case_key]
    quantity = config["quantity"]
    units_triplet = tuple(config["units"])

    if anchor_unit not in units_triplet:
        raise ValueError(
            f"Anchor unit '{anchor_unit}' is not part of the '{case_key}' scale set."
        )

    numeric_value = float(value)

    converted_values = []
    for unit_symbol in units_triplet:
        converted = units.convert_value(quantity, anchor_unit, unit_symbol, numeric_value)
        converted_values.append(converted)

    return {
        "value_unit_1": converted_values[0],
        "value_unit_2": converted_values[1],
        "value_unit_3": converted_values[2],
        "unit_label_1": units_triplet[0],
        "unit_label_2": units_triplet[1],
        "unit_label_3": units_triplet[2],
        "subst_value_unit_1": (
            f"x_1 = f_{{{units_triplet[0]}}}^{{-1}}"
            f"(f_{{{anchor_unit}}}({numeric_value})) = {converted_values[0]:.6g}"
        ),
        "subst_value_unit_2": (
            f"x_2 = f_{{{units_triplet[1]}}}^{{-1}}"
            f"(f_{{{anchor_unit}}}({numeric_value})) = {converted_values[1]:.6g}"
        ),
        "subst_value_unit_3": (
            f"x_3 = f_{{{units_triplet[2]}}}^{{-1}}"
            f"(f_{{{anchor_unit}}}({numeric_value})) = {converted_values[2]:.6g}"
        ),
    }
