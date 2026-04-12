"""
Query layer for the shared materials database.

Loads ``data/materials/materials.json`` and exposes functions for
extracting property values (scalar or rich-datum), filtering, ranking,
comparing materials, and computing virtual properties.

All numeric properties are stored in base SI units.  The property
registry attached to the database contains display metadata
(``display_unit``, ``display_multiplier``) for UI presentation.

This module is intentionally dependency-free beyond the Python
standard library so it can run under Pyodide without extra wheels.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Sequence

# ---------------------------------------------------------------------------
# Database loading
# ---------------------------------------------------------------------------

_DB_CACHE: dict[str, Any] | None = None

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "materials" / "materials.json"


def load_database(path: str | Path | None = None, *, reload: bool = False) -> dict[str, Any]:
    """Load and cache the materials database.

    Parameters
    ----------
    path : str or Path, optional
        Override the JSON file location.  Defaults to the repo-relative
        ``data/materials/materials.json``.
    reload : bool
        Force re-read even if already cached.

    Returns
    -------
    dict
        The full database dict with keys ``sources``, ``property_registry``,
        and ``materials``.
    """
    global _DB_CACHE
    if _DB_CACHE is not None and not reload:
        return _DB_CACHE

    db_path = Path(path) if path else _DEFAULT_DB_PATH
    with open(db_path, encoding="utf-8") as fh:
        _DB_CACHE = json.load(fh)
    return _DB_CACHE


# ---------------------------------------------------------------------------
# Property accessors
# ---------------------------------------------------------------------------

def get_value(material: dict, property_name: str) -> float | None:
    """Extract the numeric value from a property, handling both scalar and
    rich datum forms.

    Returns ``None`` when the property is absent or explicitly null.
    """
    raw = material.get(property_name)
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, dict):
        v = raw.get("value")
        return float(v) if v is not None else None
    return None


def get_range(material: dict, property_name: str) -> tuple[float, float] | None:
    """Extract the min/max range from a rich datum.

    Returns ``None`` when the property is a bare scalar or the rich datum
    does not contain both ``min`` and ``max``.
    """
    raw = material.get(property_name)
    if isinstance(raw, dict) and raw.get("min") is not None and raw.get("max") is not None:
        return (float(raw["min"]), float(raw["max"]))
    return None


def get_source(material: dict, property_name: str, sources: dict) -> dict | None:
    """Return the source record for *property_name*.

    If the property's rich datum has an explicit ``source_id``, that
    source is returned.  Otherwise the material's ``default_source_id``
    is used as a fallback.
    """
    raw = material.get(property_name)
    if isinstance(raw, dict) and raw.get("source_id"):
        return sources.get(raw["source_id"])
    return sources.get(material.get("default_source_id"))


def get_basis(material: dict, property_name: str) -> str:
    """Return the confidence basis for *property_name*.

    Defaults to ``'typical'`` when not explicitly specified.
    """
    raw = material.get(property_name)
    if isinstance(raw, dict):
        return raw.get("basis", "typical")
    return "typical"


# ---------------------------------------------------------------------------
# Computed / virtual properties
# ---------------------------------------------------------------------------

# Formulas keyed by virtual property name.  Each callable takes a material
# dict and returns float | None.  If any input is None the result is None.

def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _safe_mul(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a * b


_COMPUTED_FORMULAS: dict[str, Callable[[dict], float | None]] = {
    "thermal_diffusivity": lambda m: _safe_div(
        get_value(m, "thermal_conductivity"),
        _safe_mul(get_value(m, "density"), get_value(m, "specific_heat")),
    ),
    "specific_stiffness": lambda m: _safe_div(
        get_value(m, "youngs_modulus"), get_value(m, "density")
    ),
    "specific_strength": lambda m: _safe_div(
        get_value(m, "yield_strength"), get_value(m, "density")
    ),
    "volumetric_heat_capacity": lambda m: _safe_mul(
        get_value(m, "density"), get_value(m, "specific_heat")
    ),
    "price_per_m3": lambda m: _safe_mul(
        get_value(m, "price_per_kg"), get_value(m, "density")
    ),
}


def get_computed_property(material: dict, property_name: str) -> float | None:
    """Compute a virtual property for *material*.

    Falls back to ``get_value`` if *property_name* is not a known
    computed property.
    """
    fn = _COMPUTED_FORMULAS.get(property_name)
    if fn is not None:
        return fn(material)
    return get_value(material, property_name)


# ---------------------------------------------------------------------------
# Material lookup
# ---------------------------------------------------------------------------

def get_material(material_id: str, db: dict | None = None) -> dict | None:
    """Return the material record with the given *material_id*, or ``None``."""
    if db is None:
        db = load_database()
    for m in db["materials"]:
        if m["id"] == material_id:
            return m
    return None


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_materials(
    materials: Sequence[dict] | None = None,
    *,
    family: str | None = None,
    sub_family: str | None = None,
    record_kind: str | None = None,
    search: str | None = None,
    property_ranges: dict[str, tuple[float | None, float | None]] | None = None,
    exclude_estimate: bool = True,
    db: dict | None = None,
) -> list[dict]:
    """Return materials matching all supplied filters.

    Parameters
    ----------
    materials : sequence of dicts, optional
        Material list to filter.  Defaults to the full database.
    family, sub_family, record_kind : str, optional
        Exact-match identity filters.
    search : str, optional
        Case-insensitive substring search across ``name``, ``id``,
        ``designation``, and ``common_names``.
    property_ranges : dict, optional
        Map of property name → ``(min_value, max_value)`` bounds.
        Either bound may be ``None`` (unbounded).  Materials whose
        property is ``None`` are excluded.
    exclude_estimate : bool
        When ``True`` (default), materials where a property used in
        *property_ranges* has ``basis == 'estimate'`` are excluded.
    db : dict, optional
        Database dict (for resolving defaults).
    """
    if materials is None:
        if db is None:
            db = load_database()
        materials = db["materials"]

    results: list[dict] = []
    for m in materials:
        if family and m.get("family") != family:
            continue
        if sub_family and m.get("sub_family") != sub_family:
            continue
        if record_kind and m.get("record_kind") != record_kind:
            continue
        if search:
            q = search.lower()
            haystack = " ".join([
                m.get("name", ""),
                m.get("id", ""),
                m.get("designation", ""),
                " ".join(m.get("common_names", [])),
            ]).lower()
            if q not in haystack:
                continue

        # Property range filters
        skip = False
        if property_ranges:
            for prop, (lo, hi) in property_ranges.items():
                val = get_computed_property(m, prop)
                if val is None:
                    skip = True
                    break
                if exclude_estimate and get_basis(m, prop) == "estimate":
                    skip = True
                    break
                if lo is not None and val < lo:
                    skip = True
                    break
                if hi is not None and val > hi:
                    skip = True
                    break
        if skip:
            continue
        results.append(m)
    return results


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def rank_by_index(
    materials: Sequence[dict],
    index_fn: Callable[[dict], float | None],
    *,
    higher_is_better: bool = True,
    limit: int | None = None,
    use_min_values: bool = False,
) -> list[tuple[dict, float]]:
    """Rank *materials* by an index function.

    Parameters
    ----------
    index_fn : callable
        Takes a material dict and returns a numeric index or ``None``
        (material is skipped).
    higher_is_better : bool
        Sort direction.
    limit : int, optional
        Return at most this many results.
    use_min_values : bool
        Not yet implemented (placeholder for conservative screening).

    Returns
    -------
    list of (material, index_value) tuples, sorted by index.
    """
    scored: list[tuple[dict, float]] = []
    for m in materials:
        val = index_fn(m)
        if val is not None:
            scored.append((m, val))
    scored.sort(key=lambda pair: pair[1], reverse=higher_is_better)
    if limit is not None:
        scored = scored[:limit]
    return scored


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_materials(
    material_ids: Sequence[str],
    properties: Sequence[str],
    db: dict | None = None,
) -> list[dict]:
    """Build a side-by-side comparison table.

    Returns a list of dicts, one per *property*, each containing the
    property name and a value (or ``None``) per material id.
    """
    if db is None:
        db = load_database()
    mats = {mid: get_material(mid, db) for mid in material_ids}

    rows: list[dict] = []
    for prop in properties:
        row: dict[str, Any] = {"property": prop}
        for mid in material_ids:
            m = mats.get(mid)
            if m is None:
                row[mid] = None
            else:
                row[mid] = get_computed_property(m, prop)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Substitute finder
# ---------------------------------------------------------------------------

def find_substitutes(
    material_id: str,
    properties: Sequence[str],
    *,
    tolerance: float = 0.20,
    db: dict | None = None,
) -> list[tuple[dict, float]]:
    """Find materials similar to *material_id* across *properties*.

    Each property is compared as a fractional deviation.  The overall
    distance is the max absolute fractional deviation across all
    requested properties.  Materials whose distance is within
    *tolerance* (default 20 %) are returned, sorted by distance.

    Materials that lack any of the requested properties are excluded.
    """
    if db is None:
        db = load_database()
    ref = get_material(material_id, db)
    if ref is None:
        raise ValueError(f"Unknown material id: {material_id!r}")

    ref_vals: dict[str, float] = {}
    for p in properties:
        v = get_computed_property(ref, p)
        if v is None or v == 0:
            raise ValueError(
                f"Reference material {material_id!r} has no value for {p!r}"
            )
        ref_vals[p] = v

    candidates: list[tuple[dict, float]] = []
    for m in db["materials"]:
        if m["id"] == material_id:
            continue
        max_dev = 0.0
        skip = False
        for p, rv in ref_vals.items():
            cv = get_computed_property(m, p)
            if cv is None:
                skip = True
                break
            dev = abs(cv - rv) / abs(rv)
            if dev > max_dev:
                max_dev = dev
        if skip or max_dev > tolerance:
            continue
        candidates.append((m, max_dev))

    candidates.sort(key=lambda pair: pair[1])
    return candidates
