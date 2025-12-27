"""
Orders-of-magnitude exploration helpers for cross-domain scale intuition.
"""

from __future__ import annotations

import math
from typing import Any


PREFIX_SYMBOLS: dict[int, str] = {
    -24: "y",
    -21: "z",
    -18: "a",
    -15: "f",
    -12: "p",
    -9: "n",
    -6: "u",
    -3: "m",
    0: "",
    3: "k",
    6: "M",
    9: "G",
    12: "T",
    15: "P",
    18: "E",
    21: "Z",
    24: "Y",
}

PREFIX_EXPONENTS = sorted(PREFIX_SYMBOLS.keys())

DOMAIN_CONFIG: dict[str, dict[str, Any]] = {
    "length": {
        "label": "Length",
        "base_unit": "m",
        "prefix_unit": "m",
        "prefix_scale": 1.0,
        "min_exponent": -15.0,
        "max_exponent": 12.0,
        "anchors": [
            {"label": "Proton diameter", "value": 1.0e-15},
            {"label": "Hydrogen atom", "value": 1.0e-10},
            {"label": "Virus", "value": 1.0e-7},
            {"label": "Bacterium", "value": 1.0e-6},
            {"label": "Grain of sand", "value": 1.0e-3},
            {"label": "Human height", "value": 1.7},
            {"label": "Football field", "value": 100.0},
            {"label": "Mountain height", "value": 1.0e3},
            {"label": "Earth radius", "value": 6.37e6},
            {"label": "Earth-Sun distance", "value": 1.50e11},
        ],
    },
    "mass": {
        "label": "Mass",
        "base_unit": "kg",
        "prefix_unit": "g",
        "prefix_scale": 1.0e3,
        "min_exponent": -31.0,
        "max_exponent": 31.0,
        "anchors": [
            {"label": "Electron", "value": 9.11e-31},
            {"label": "Dust grain", "value": 1.0e-12},
            {"label": "Grain of sand", "value": 1.0e-6},
            {"label": "Paperclip", "value": 1.0e-3},
            {"label": "Apple", "value": 0.1},
            {"label": "Human", "value": 70.0},
            {"label": "Car", "value": 1.5e3},
            {"label": "Blue whale", "value": 1.0e5},
            {"label": "Earth", "value": 5.97e24},
            {"label": "Sun", "value": 1.99e30},
        ],
    },
    "time": {
        "label": "Time",
        "base_unit": "s",
        "prefix_unit": "s",
        "prefix_scale": 1.0,
        "min_exponent": -15.0,
        "max_exponent": 18.0,
        "anchors": [
            {"label": "Femtosecond", "value": 1.0e-15},
            {"label": "Nanosecond", "value": 1.0e-9},
            {"label": "Millisecond", "value": 1.0e-3},
            {"label": "Second", "value": 1.0},
            {"label": "Minute", "value": 60.0},
            {"label": "Hour", "value": 3600.0},
            {"label": "Day", "value": 86400.0},
            {"label": "Year", "value": 3.154e7},
            {"label": "Human lifetime", "value": 2.5e9},
            {"label": "Age of universe", "value": 4.35e17},
        ],
    },
    "energy": {
        "label": "Energy",
        "base_unit": "J",
        "prefix_unit": "J",
        "prefix_scale": 1.0,
        "min_exponent": -21.0,
        "max_exponent": 21.0,
        "anchors": [
            {"label": "Visible photon", "value": 3.0e-19},
            {"label": "Falling apple (1 m)", "value": 1.0},
            {"label": "Dietary Calorie", "value": 4.184e3},
            {"label": "1 kWh", "value": 3.6e6},
            {"label": "Lightning strike", "value": 1.0e9},
            {"label": "Hiroshima blast", "value": 6.3e13},
            {"label": "1 kg mass-energy", "value": 9.0e16},
            {"label": "World annual energy", "value": 6.0e20},
        ],
    },
    "power": {
        "label": "Power",
        "base_unit": "W",
        "prefix_unit": "W",
        "prefix_scale": 1.0,
        "min_exponent": -6.0,
        "max_exponent": 27.0,
        "anchors": [
            {"label": "LED indicator", "value": 1.0e-3},
            {"label": "Smartphone charging", "value": 2.0},
            {"label": "Human resting", "value": 100.0},
            {"label": "Microwave oven", "value": 1.0e3},
            {"label": "Car engine", "value": 1.0e5},
            {"label": "Wind turbine", "value": 2.0e6},
            {"label": "Large power plant", "value": 1.0e9},
            {"label": "World average power", "value": 2.0e13},
            {"label": "Sun output", "value": 3.8e26},
        ],
    },
    "pressure": {
        "label": "Pressure",
        "base_unit": "Pa",
        "prefix_unit": "Pa",
        "prefix_scale": 1.0,
        "min_exponent": -9.0,
        "max_exponent": 12.0,
        "anchors": [
            {"label": "Interstellar medium", "value": 1.0e-9},
            {"label": "Gentle breeze", "value": 1.0},
            {"label": "Atmospheric", "value": 1.013e5},
            {"label": "Car tire", "value": 2.0e5},
            {"label": "Scuba tank", "value": 2.0e7},
            {"label": "Deep ocean trench", "value": 1.0e8},
            {"label": "Steel yield stress", "value": 2.0e9},
            {"label": "Earth core", "value": 3.0e11},
        ],
    },
    "data": {
        "label": "Data size",
        "base_unit": "B",
        "prefix_unit": "B",
        "prefix_scale": 1.0,
        "min_exponent": 0.0,
        "max_exponent": 18.0,
        "anchors": [
            {"label": "Single byte", "value": 1.0},
            {"label": "Text page", "value": 2.0e3},
            {"label": "Photo (JPEG)", "value": 3.0e6},
            {"label": "Song (MP3)", "value": 5.0e6},
            {"label": "HD movie", "value": 5.0e9},
            {"label": "4K movie", "value": 2.0e10},
            {"label": "1 TB drive", "value": 1.0e12},
            {"label": "Large data center", "value": 1.0e15},
            {"label": "Global traffic/day", "value": 1.0e18},
        ],
    },
}


def _select_prefix_exponent(value: float) -> int:
    exponent = math.log10(abs(value))
    prefix_exp = int(math.floor(exponent / 3.0) * 3)
    prefix_exp = min(max(prefix_exp, PREFIX_EXPONENTS[0]), PREFIX_EXPONENTS[-1])
    return prefix_exp


def _format_scaled_value(value: float, prefix_unit: str, prefix_scale: float) -> tuple[float, str, int]:
    scaled_value = value * prefix_scale
    if scaled_value == 0.0:
        return 0.0, prefix_unit, 0
    prefix_exp = _select_prefix_exponent(scaled_value)
    prefix = PREFIX_SYMBOLS[prefix_exp]
    scaled = scaled_value / (10.0**prefix_exp)
    return scaled, f"{prefix}{prefix_unit}", prefix_exp


def _annotate_anchor(
    anchor: dict[str, float | str],
    prefix_unit: str,
    prefix_scale: float,
) -> dict[str, float | str]:
    value = float(anchor["value"])
    exponent = math.log10(value)
    scaled_value, scaled_unit, _ = _format_scaled_value(value, prefix_unit, prefix_scale)
    return {
        "label": str(anchor["label"]),
        "value": value,
        "exponent": exponent,
        "scaled_value": scaled_value,
        "scaled_unit": scaled_unit,
    }


def explore_orders_of_magnitude(
    domain: str,
    exponent: float,
    anchor_window: float,
    use_custom_value: bool,
    custom_value: float,
) -> dict[str, float | str | list[dict[str, float | str]]]:
    """
    Explore orders of magnitude for common physical quantities with reference anchors.

    The tool converts a log10 magnitude into a base-unit value, formats a scaled
    SI-prefix representation, and highlights nearby real-world reference points.

    ---Parameters---
    domain : str
        Domain key to explore. Options: length, mass, time, energy, power, pressure, data.
    exponent : float
        Base-10 exponent used to generate the magnitude (value = 10^exponent).
    anchor_window : float
        Half-width of the anchor window in orders of magnitude (e.g., 1.5 shows
        anchors within +/- 1.5 decades of the selected exponent).
    use_custom_value : bool
        Whether to compute the order of magnitude for the custom value input.
    custom_value : float
        Optional custom value expressed in the domain base unit.

    ---Returns---
    effective_exponent : float
        Exponent actually used after clamping to the domain range.
    base_value : float
        Magnitude value in the domain base unit.
    base_unit : str
        Base unit symbol for the domain.
    scaled_value : float
        Value scaled to a nearby SI prefix for readability.
    scaled_unit : str
        Unit string for the scaled value (prefix + unit).
    nearest_anchor : str
        Label of the closest anchor to the selected exponent.
    nearest_anchor_value : float
        Anchor magnitude value in base units.
    nearest_anchor_ratio : float
        Ratio of selected value to the nearest anchor.
    anchors_window : list
        Anchors within the requested window, each with label, value, exponent,
        scaled_value, and scaled_unit.
    domain_label : str
        Human-readable name of the domain.
    domain_min_exponent : float
        Minimum supported exponent for the domain.
    domain_max_exponent : float
        Maximum supported exponent for the domain.
    custom_exponent : float
        Log10 exponent for the custom value (if enabled).
    custom_scaled_value : float
        Custom value scaled to a nearby SI prefix (if enabled).
    custom_scaled_unit : str
        Unit string for the custom scaled value (if enabled).

    ---LaTeX---
    V = 10^{n} \\times U
    V_{\\text{scaled}} = \\frac{V}{10^{k}}
    R = \\frac{V}{V_{\\text{ref}}}
    n = \\log_{10}(V)
    """
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"Unknown domain '{domain}'.")
    if anchor_window <= 0.0:
        raise ValueError("anchor_window must be positive.")

    config = DOMAIN_CONFIG[domain]
    min_exp = float(config["min_exponent"])
    max_exp = float(config["max_exponent"])

    effective_exponent = max(min(exponent, max_exp), min_exp)
    base_value = 10.0**effective_exponent

    base_unit = str(config["base_unit"])
    prefix_unit = str(config["prefix_unit"])
    prefix_scale = float(config["prefix_scale"])

    scaled_value, scaled_unit, prefix_exp = _format_scaled_value(
        base_value, prefix_unit, prefix_scale
    )

    anchors = [
        _annotate_anchor(anchor, prefix_unit, prefix_scale)
        for anchor in config["anchors"]
    ]
    anchors.sort(key=lambda item: float(item["exponent"]))

    nearest_anchor = min(
        anchors,
        key=lambda item: abs(float(item["exponent"]) - effective_exponent),
    )
    nearest_anchor_value = float(nearest_anchor["value"])
    nearest_anchor_ratio = base_value / nearest_anchor_value

    window_min = effective_exponent - anchor_window
    window_max = effective_exponent + anchor_window
    anchors_window = [
        anchor
        for anchor in anchors
        if window_min <= float(anchor["exponent"]) <= window_max
    ]

    if not anchors_window:
        anchors_window = sorted(
            anchors,
            key=lambda item: abs(float(item["exponent"]) - effective_exponent),
        )[:3]
        anchors_window.sort(key=lambda item: float(item["exponent"]))

    results: dict[str, float | str | list[dict[str, float | str]]] = {
        "effective_exponent": effective_exponent,
        "base_value": base_value,
        "base_unit": base_unit,
        "scaled_value": scaled_value,
        "scaled_unit": scaled_unit,
        "nearest_anchor": str(nearest_anchor["label"]),
        "nearest_anchor_value": nearest_anchor_value,
        "nearest_anchor_ratio": nearest_anchor_ratio,
        "anchors_window": anchors_window,
        "domain_label": str(config["label"]),
        "domain_min_exponent": min_exp,
        "domain_max_exponent": max_exp,
    }

    results["subst_base_value"] = (
        f"V = 10^{{{effective_exponent:.2f}}} \\times 1\\,\\text{{{base_unit}}}"
        f" = {base_value:.3e}\\,\\text{{{base_unit}}}"
    )
    results["subst_scaled_value"] = (
        f"V_{{\\text{{scaled}}}} = "
        f"\\frac{{{base_value:.3e}\\,\\text{{{base_unit}}}}}{{10^{{{prefix_exp}}}}}"
        f" = {scaled_value:.3g}\\,\\text{{{scaled_unit}}}"
    )
    results["subst_nearest_anchor_ratio"] = (
        f"R = \\frac{{{base_value:.3e}}}{{{nearest_anchor_value:.3e}}}"
        f" = {nearest_anchor_ratio:.3g}"
    )

    if use_custom_value:
        if custom_value <= 0.0:
            raise ValueError("custom_value must be positive when enabled.")
        custom_exponent = math.log10(custom_value)
        custom_scaled_value, custom_scaled_unit, _ = _format_scaled_value(
            custom_value, prefix_unit, prefix_scale
        )
        results["custom_exponent"] = custom_exponent
        results["custom_scaled_value"] = custom_scaled_value
        results["custom_scaled_unit"] = custom_scaled_unit

    return results


def catalog_orders_of_magnitude(
    domain: str,
) -> dict[str, float | str | list[dict[str, float | str]]]:
    """
    Browse curated anchor lists across orders of magnitude for a domain.

    Orders of magnitude measure scale using base-10 exponents; each integer step
    represents a tenfold change. The catalog returns ordered anchors with span
    statistics and base-unit metadata for display.

    ---Parameters---
    domain : str
        Domain key to explore. Options: length, mass, time, energy, power, pressure, data.

    ---Returns---
    domain_label : str
        Human-readable name of the domain.
    base_unit : str
        Base unit symbol for the domain.
    domain_min_exponent : float
        Minimum supported exponent for the domain scale.
    domain_max_exponent : float
        Maximum supported exponent for the domain scale.
    anchor_count : float
        Number of anchors listed for the domain.
    anchor_span_exponent : float
        Difference between maximum and minimum anchor exponents (decades).
    anchor_span_ratio : float
        Ratio between the largest and smallest anchor values.
    min_anchor_label : str
        Label of the smallest anchor in the list.
    max_anchor_label : str
        Label of the largest anchor in the list.
    anchors : list
        Ordered anchors with label, value, exponent, scaled_value, and scaled_unit.

    ---LaTeX---
    n = \\log_{10}(V)
    \\Delta n = n_{\\text{max}} - n_{\\text{min}}
    R = 10^{\\Delta n}
    """
    if domain not in DOMAIN_CONFIG:
        raise ValueError(f"Unknown domain '{domain}'.")

    config = DOMAIN_CONFIG[domain]
    base_unit = str(config["base_unit"])
    prefix_unit = str(config["prefix_unit"])
    prefix_scale = float(config["prefix_scale"])

    anchors = [
        _annotate_anchor(anchor, prefix_unit, prefix_scale)
        for anchor in config["anchors"]
    ]
    anchors.sort(key=lambda item: float(item["exponent"]))

    min_anchor = anchors[0]
    max_anchor = anchors[-1]
    min_exp = float(min_anchor["exponent"])
    max_exp = float(max_anchor["exponent"])

    anchor_span_exponent = max_exp - min_exp
    anchor_span_ratio = 10.0**anchor_span_exponent

    results: dict[str, float | str | list[dict[str, float | str]]] = {
        "domain_label": str(config["label"]),
        "base_unit": base_unit,
        "domain_min_exponent": float(config["min_exponent"]),
        "domain_max_exponent": float(config["max_exponent"]),
        "anchor_count": float(len(anchors)),
        "anchor_span_exponent": anchor_span_exponent,
        "anchor_span_ratio": anchor_span_ratio,
        "min_anchor_label": str(min_anchor["label"]),
        "max_anchor_label": str(max_anchor["label"]),
        "anchors": anchors,
    }

    results["subst_anchor_span_exponent"] = (
        f"\\Delta n = {max_exp:.2f} - {min_exp:.2f} = {anchor_span_exponent:.2f}"
    )
    results["subst_anchor_span_ratio"] = (
        f"R = 10^{{{anchor_span_exponent:.2f}}} = {anchor_span_ratio:.3e}"
    )

    return results
