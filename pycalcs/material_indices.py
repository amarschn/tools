"""
Performance index library for Ashby-style material selection.

Each index is a structured :class:`PerformanceIndex` record with a
compute function, derivation summary, scope notes, and isoline
metadata for log-log charts.

All compute functions accept a material dict (as stored in the
database) and return ``float | None``.  ``None`` means the material
lacks one or more required properties and should be skipped.

Reference: Ashby, M. F. (2011). *Materials Selection in Mechanical
Design*, 4th ed. Butterworth-Heinemann, Chapters 5–6 and §11.7.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Callable

from pycalcs.material_db import get_value


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerformanceIndex:
    """Structured record for a single performance index."""

    id: str
    name: str
    expression_display: str
    expression_latex: str
    required_properties: tuple[str, ...]
    compute: Callable[[dict], float | None]
    derivation: str
    scope: str
    source: str
    maximize: bool
    chart_x: str
    chart_y: str
    isoline_slope: float | None  # None when isolines don't apply


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _props(m: dict, *names: str) -> tuple[float, ...] | None:
    """Extract multiple property values; returns None if any is missing."""
    vals: list[float] = []
    for n in names:
        v = get_value(m, n)
        if v is None or v == 0:
            return None
        vals.append(v)
    return tuple(vals)


_ASHBY_2011 = "Ashby, M. F. (2011). Materials Selection in Mechanical Design, 4th ed. Ch. 5–6."
_ASHBY_THERMAL = "Ashby, M. F. (2011). Materials Selection in Mechanical Design, 4th ed. §11.7."


# ---------------------------------------------------------------------------
# Index definitions
# ---------------------------------------------------------------------------

def _stiff_light_tie(m: dict) -> float | None:
    p = _props(m, "youngs_modulus", "density")
    return p[0] / p[1] if p else None


def _stiff_light_beam(m: dict) -> float | None:
    p = _props(m, "youngs_modulus", "density")
    return sqrt(p[0]) / p[1] if p else None


def _stiff_light_plate(m: dict) -> float | None:
    p = _props(m, "youngs_modulus", "density")
    return p[0] ** (1 / 3) / p[1] if p else None


def _strong_light_tie(m: dict) -> float | None:
    p = _props(m, "yield_strength", "density")
    return p[0] / p[1] if p else None


def _strong_light_beam(m: dict) -> float | None:
    p = _props(m, "yield_strength", "density")
    return p[0] ** (2 / 3) / p[1] if p else None


def _strong_light_plate(m: dict) -> float | None:
    p = _props(m, "yield_strength", "density")
    return p[0] ** (1 / 2) / p[1] if p else None


def _max_elastic_energy_mass(m: dict) -> float | None:
    p = _props(m, "yield_strength", "youngs_modulus", "density")
    return p[0] ** 2 / (p[1] * p[2]) if p else None


def _max_elastic_energy_vol(m: dict) -> float | None:
    p = _props(m, "yield_strength", "youngs_modulus")
    return p[0] ** 2 / p[1] if p else None


def _damage_tolerant(m: dict) -> float | None:
    p = _props(m, "fracture_toughness", "yield_strength")
    return p[0] / p[1] if p else None


def _thermal_shock(m: dict) -> float | None:
    # Use flexural_strength if available, fall back to tensile_strength
    sf = get_value(m, "flexural_strength") or get_value(m, "tensile_strength")
    E = get_value(m, "youngs_modulus")
    a = get_value(m, "cte")
    if sf is None or E is None or a is None or E == 0 or a == 0:
        return None
    return sf / (E * a)


def _thermal_distortion(m: dict) -> float | None:
    p = _props(m, "thermal_conductivity", "youngs_modulus", "cte")
    return p[0] / (p[1] * p[2]) if p else None


def _heat_spreading_mass(m: dict) -> float | None:
    p = _props(m, "thermal_conductivity", "density")
    return p[0] / p[1] if p else None


def _thermal_storage_vol(m: dict) -> float | None:
    p = _props(m, "density", "specific_heat")
    return p[0] * p[1] if p else None


def _thermal_insulation(m: dict) -> float | None:
    k = get_value(m, "thermal_conductivity")
    if k is None or k == 0:
        return None
    return 1.0 / k


def _stiff_cheap_beam(m: dict) -> float | None:
    p = _props(m, "youngs_modulus", "density", "price_per_kg")
    return sqrt(p[0]) / (p[1] * p[2]) if p else None


def _strong_cheap_tie(m: dict) -> float | None:
    p = _props(m, "yield_strength", "density", "price_per_kg")
    return p[0] / (p[1] * p[2]) if p else None


# ---------------------------------------------------------------------------
# Index registry
# ---------------------------------------------------------------------------

INDICES: dict[str, PerformanceIndex] = {}

def _register(idx: PerformanceIndex) -> PerformanceIndex:
    INDICES[idx.id] = idx
    return idx


_register(PerformanceIndex(
    id="stiff_light_tie",
    name="Stiff, light tie",
    expression_display="E / \u03c1",
    expression_latex=r"\frac{E}{\rho}",
    required_properties=("youngs_modulus", "density"),
    compute=_stiff_light_tie,
    derivation=(
        "For an axially loaded tie of fixed length, minimizing mass at "
        "constant axial stiffness yields M = E/\u03c1.  Derived from "
        "F/\u03b4 = EA/L with m = \u03c1AL."
    ),
    scope="Fixed length, axial stiffness constraint.",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="density",
    chart_y="youngs_modulus",
    isoline_slope=1.0,
))

_register(PerformanceIndex(
    id="stiff_light_beam",
    name="Stiff, light beam",
    expression_display="E\u00b9\u02f2 / \u03c1",
    expression_latex=r"\frac{E^{1/2}}{\rho}",
    required_properties=("youngs_modulus", "density"),
    compute=_stiff_light_beam,
    derivation=(
        "For a beam of fixed length and prescribed bending stiffness, "
        "minimizing mass yields M = E^(1/2)/\u03c1.  The cross-section "
        "is a free variable (can be resized)."
    ),
    scope="Fixed length, bending stiffness constraint, free cross-section.",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="density",
    chart_y="youngs_modulus",
    isoline_slope=2.0,
))

_register(PerformanceIndex(
    id="stiff_light_plate",
    name="Stiff, light plate",
    expression_display="E\u00b9\u02f3 / \u03c1",
    expression_latex=r"\frac{E^{1/3}}{\rho}",
    required_properties=("youngs_modulus", "density"),
    compute=_stiff_light_plate,
    derivation=(
        "For a plate of fixed area loaded in bending, minimizing mass "
        "at constant stiffness yields M = E^(1/3)/\u03c1.  Thickness is "
        "the free variable."
    ),
    scope="Fixed area, bending stiffness constraint (plate geometry).",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="density",
    chart_y="youngs_modulus",
    isoline_slope=3.0,
))

_register(PerformanceIndex(
    id="strong_light_tie",
    name="Strong, light tie",
    expression_display="\u03c3\u1d67 / \u03c1",
    expression_latex=r"\frac{\sigma_y}{\rho}",
    required_properties=("yield_strength", "density"),
    compute=_strong_light_tie,
    derivation=(
        "For a tie of fixed length that must not yield under axial load, "
        "minimizing mass yields M = \u03c3_y/\u03c1."
    ),
    scope="Fixed length, yield strength in tension.",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="density",
    chart_y="yield_strength",
    isoline_slope=1.0,
))

_register(PerformanceIndex(
    id="strong_light_beam",
    name="Strong, light beam",
    expression_display="\u03c3\u1d67\u00b2\u02f3 / \u03c1",
    expression_latex=r"\frac{\sigma_y^{2/3}}{\rho}",
    required_properties=("yield_strength", "density"),
    compute=_strong_light_beam,
    derivation=(
        "For a beam of fixed length that must not yield in bending, "
        "minimizing mass with free cross-section yields "
        "M = \u03c3_y^(2/3)/\u03c1."
    ),
    scope="Fixed length, bending strength, free cross-section.",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="density",
    chart_y="yield_strength",
    isoline_slope=1.5,
))

_register(PerformanceIndex(
    id="strong_light_plate",
    name="Strong, light plate",
    expression_display="\u03c3\u1d67\u00b9\u02f2 / \u03c1",
    expression_latex=r"\frac{\sigma_y^{1/2}}{\rho}",
    required_properties=("yield_strength", "density"),
    compute=_strong_light_plate,
    derivation=(
        "For a plate of fixed area that must not yield in bending, "
        "minimizing mass with free thickness yields "
        "M = \u03c3_y^(1/2)/\u03c1."
    ),
    scope="Fixed area, bending strength (plate geometry).",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="density",
    chart_y="yield_strength",
    isoline_slope=2.0,
))

_register(PerformanceIndex(
    id="max_elastic_energy_mass",
    name="Max elastic stored energy / mass",
    expression_display="\u03c3\u1d67\u00b2 / (E\u00b7\u03c1)",
    expression_latex=r"\frac{\sigma_y^2}{E \cdot \rho}",
    required_properties=("yield_strength", "youngs_modulus", "density"),
    compute=_max_elastic_energy_mass,
    derivation=(
        "The elastic energy stored per unit mass before yield is "
        "\u03c3_y\u00b2/(2E\u03c1).  Maximizing this (dropping the "
        "constant \u00bd) gives M = \u03c3_y\u00b2/(E\u03c1)."
    ),
    scope="Springs, elastic energy storage (mass-limited).",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="youngs_modulus",
    chart_y="yield_strength",
    isoline_slope=None,
))

_register(PerformanceIndex(
    id="max_elastic_energy_vol",
    name="Max elastic stored energy / volume",
    expression_display="\u03c3\u1d67\u00b2 / E",
    expression_latex=r"\frac{\sigma_y^2}{E}",
    required_properties=("yield_strength", "youngs_modulus"),
    compute=_max_elastic_energy_vol,
    derivation=(
        "The elastic energy stored per unit volume before yield is "
        "\u03c3_y\u00b2/(2E).  Maximizing this gives M = \u03c3_y\u00b2/E."
    ),
    scope="Springs, elastic energy storage (volume-limited).",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="youngs_modulus",
    chart_y="yield_strength",
    isoline_slope=None,
))

_register(PerformanceIndex(
    id="damage_tolerant",
    name="Damage-tolerant design",
    expression_display="K_IC / \u03c3\u1d67",
    expression_latex=r"\frac{K_{IC}}{\sigma_y}",
    required_properties=("fracture_toughness", "yield_strength"),
    compute=_damage_tolerant,
    derivation=(
        "The critical crack length before fast fracture is proportional "
        "to (K_IC/\u03c3_y)\u00b2.  Maximizing K_IC/\u03c3_y maximizes "
        "the tolerable flaw size (leak-before-break criterion)."
    ),
    scope="Flaw-tolerant structures, leak-before-break, pressure vessels.",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="yield_strength",
    chart_y="fracture_toughness",
    isoline_slope=None,
))

_register(PerformanceIndex(
    id="thermal_shock",
    name="Thermal shock resistance",
    expression_display="\u03c3\u1da0 / (E\u00b7\u03b1)",
    expression_latex=r"\frac{\sigma_f}{E \cdot \alpha}",
    required_properties=("youngs_modulus", "cte"),
    compute=_thermal_shock,
    derivation=(
        "The maximum survivable thermal shock \u0394T is proportional to "
        "\u03c3_f/(E\u00b7\u03b1), where \u03c3_f is the fracture or "
        "flexural strength and \u03b1 is the CTE."
    ),
    scope="Sudden temperature change, resist fracture.  Uses flexural strength for ceramics.",
    source=_ASHBY_THERMAL,
    maximize=True,
    chart_x="cte",
    chart_y="youngs_modulus",
    isoline_slope=None,
))

_register(PerformanceIndex(
    id="thermal_distortion",
    name="Thermal distortion resistance",
    expression_display="k / (E\u00b7\u03b1)",
    expression_latex=r"\frac{k}{E \cdot \alpha}",
    required_properties=("thermal_conductivity", "youngs_modulus", "cte"),
    compute=_thermal_distortion,
    derivation=(
        "For precision equipment, minimizing distortion under steady "
        "heat flux requires high k (to equalize temperature) and low "
        "E\u00b7\u03b1 (to minimize strain per \u0394T)."
    ),
    scope="Precision instruments, optical benches, minimize warping under heat flux.",
    source=_ASHBY_THERMAL,
    maximize=True,
    chart_x="cte",
    chart_y="thermal_conductivity",
    isoline_slope=None,
))

_register(PerformanceIndex(
    id="heat_spreading_mass",
    name="Heat spreading per unit mass",
    expression_display="k / \u03c1",
    expression_latex=r"\frac{k}{\rho}",
    required_properties=("thermal_conductivity", "density"),
    compute=_heat_spreading_mass,
    derivation=(
        "For lightweight heat spreaders (e.g. aerospace electronics), "
        "maximizing thermal conductivity per unit mass gives M = k/\u03c1."
    ),
    scope="Lightweight heat spreaders, mass-limited thermal management.",
    source=_ASHBY_THERMAL,
    maximize=True,
    chart_x="density",
    chart_y="thermal_conductivity",
    isoline_slope=1.0,
))

_register(PerformanceIndex(
    id="thermal_storage_vol",
    name="Volumetric thermal storage",
    expression_display="\u03c1\u00b7C\u209a",
    expression_latex=r"\rho \cdot C_p",
    required_properties=("density", "specific_heat"),
    compute=_thermal_storage_vol,
    derivation=(
        "The energy stored per unit volume for a given \u0394T is "
        "\u03c1\u00b7C\u209a\u00b7\u0394T.  Maximizing \u03c1\u00b7C\u209a "
        "maximizes volumetric thermal storage."
    ),
    scope=(
        "Thermal mass, passive thermal storage.  NOT heat sink "
        "performance (which depends on k and convection geometry)."
    ),
    source=_ASHBY_THERMAL,
    maximize=True,
    chart_x="density",
    chart_y="specific_heat",
    isoline_slope=None,
))

_register(PerformanceIndex(
    id="thermal_insulation",
    name="Thermal insulation",
    expression_display="1 / k",
    expression_latex=r"\frac{1}{k}",
    required_properties=("thermal_conductivity",),
    compute=_thermal_insulation,
    derivation=(
        "Minimizing steady-state heat flow through a wall of fixed "
        "thickness requires minimizing thermal conductivity."
    ),
    scope="Insulation, minimize heat loss.",
    source=_ASHBY_THERMAL,
    maximize=True,
    chart_x="thermal_conductivity",
    chart_y="density",
    isoline_slope=None,
))

_register(PerformanceIndex(
    id="stiff_cheap_beam",
    name="Stiff, cheap beam",
    expression_display="E\u00b9\u02f2 / (\u03c1\u00b7C\u2098)",
    expression_latex=r"\frac{E^{1/2}}{\rho \cdot C_m}",
    required_properties=("youngs_modulus", "density", "price_per_kg"),
    compute=_stiff_cheap_beam,
    derivation=(
        "Minimizing the cost of a beam of given bending stiffness, "
        "where cost = \u03c1\u00b7V\u00b7C_m and V scales as 1/E^(1/2), "
        "yields M = E^(1/2)/(\u03c1\u00b7C_m)."
    ),
    scope="Minimum-cost stiff beam, C_m = price per kg.",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="density",
    chart_y="youngs_modulus",
    isoline_slope=None,
))

_register(PerformanceIndex(
    id="strong_cheap_tie",
    name="Strong, cheap tie",
    expression_display="\u03c3\u1d67 / (\u03c1\u00b7C\u2098)",
    expression_latex=r"\frac{\sigma_y}{\rho \cdot C_m}",
    required_properties=("yield_strength", "density", "price_per_kg"),
    compute=_strong_cheap_tie,
    derivation=(
        "Minimizing the cost of a tie that must not yield, where "
        "cost = \u03c1\u00b7A\u00b7L\u00b7C_m and A scales as 1/\u03c3_y, "
        "yields M = \u03c3_y/(\u03c1\u00b7C_m)."
    ),
    scope="Minimum-cost strong tie, C_m = price per kg.",
    source=_ASHBY_2011,
    maximize=True,
    chart_x="density",
    chart_y="yield_strength",
    isoline_slope=None,
))


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def compute_index(index_id: str, material: dict) -> float | None:
    """Compute the named performance index for *material*.

    Raises ``KeyError`` if *index_id* is not in the library.
    """
    return INDICES[index_id].compute(material)


def get_isoline_points(
    index_id: str,
    index_value: float,
    x_range: tuple[float, float],
) -> list[tuple[float, float]] | None:
    """Return (x, y) points for a constant-index isoline on a log-log chart.

    For an index of the form Y^(1/n) / X the isoline is
    Y = (M * X)^n, which is a straight line on log-log axes with
    slope *n* (the ``isoline_slope``).

    Parameters
    ----------
    index_id : str
        Performance index ID.
    index_value : float
        The index value to draw the isoline for.
    x_range : (float, float)
        Min and max X-axis values (in base SI).

    Returns
    -------
    list of (x, y) tuples, or ``None`` if the index has no isoline.
    """
    idx = INDICES[index_id]
    if idx.isoline_slope is None:
        return None
    n = idx.isoline_slope
    x_min, x_max = x_range
    # Y = (M * X)^n  →  on log-log: log(Y) = n * log(M) + n * log(X)
    pts: list[tuple[float, float]] = []
    for x in (x_min, x_max):
        y = (index_value * x) ** n
        pts.append((x, y))
    return pts


def custom_index(
    material: dict,
    numerator_props: list[tuple[str, float]],
    denominator_props: list[tuple[str, float]],
) -> float | None:
    """Compute a user-defined generalised index.

    M = (P1^a1 * P2^a2 * ...) / (P3^a3 * P4^a4 * ...)

    Parameters
    ----------
    numerator_props : list of (property_name, exponent)
    denominator_props : list of (property_name, exponent)

    Returns ``None`` if any required property is missing.
    """
    num = 1.0
    for prop, exp in numerator_props:
        v = get_value(material, prop)
        if v is None or v == 0:
            return None
        num *= v ** exp

    den = 1.0
    for prop, exp in denominator_props:
        v = get_value(material, prop)
        if v is None or v == 0:
            return None
        den *= v ** exp

    if den == 0:
        return None
    return num / den
