"""Build Ashby chart projections from the published observation catalog.

This module never invents a property or averages observations together. Each
chart point names the two observations it combines. The generated chart data
is a disposable projection of the Materials catalog, not another authoring
database. Performance indices come from :mod:`pycalcs.material_indices`.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from itertools import combinations_with_replacement, product
import math
from typing import Any

from pycalcs.material_indices import INDICES, PROPERTY_SYMBOLS, get_isoline_points


PROPERTY_ALIASES = {
    "yield_strength": "tensile_yield_strength",
    "tensile_strength": "ultimate_tensile_strength",
    "max_service_temp": "max_service_temperature",
}
GRADE_PHYSICAL_PROPERTIES = {
    "density", "youngs_modulus", "thermal_conductivity", "specific_heat",
    "poissons_ratio", "max_service_temperature",
}
FAMILIES = {"metals": "metal", "engineering-plastics": "polymer", "ceramics": "ceramic"}


def observation_value(observation: dict[str, Any]) -> float | None:
    r"""Return the positive SI plot coordinate of a reported observation.

    ---Parameters---
    observation : dict
        Canonical observation containing a result kind and canonical values.

    ---Returns---
    coordinate : float or None
        Point value, reported bound, or interval midpoint. Missing, nonfinite,
        and nonpositive results are omitted from logarithmic charts. The caller
        must preserve the result kind; a bound is not a measured point.

    ---LaTeX---
    v = \frac{v_{\min} + v_{\max}}{2}

    The original interval remains attached. This midpoint is a plotting
    convention, not an estimate of a population mean.
    """
    result = observation["result"]
    values = result["canonical"]
    if result["kind"] == "interval":
        low, high = values["minimum"], values["maximum"]
        if not all(math.isfinite(v) and v > 0 for v in (low, high)) or low > high:
            return None
        value = (low + high) / 2
    else:
        value = values.get("value")
    if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
        return value
    return None


def compatible_observations(left: dict[str, Any], right: dict[str, Any]) -> bool:
    r"""Check whether two observations can share an Ashby reference point.

    ---Parameters---
    left : dict
        First canonical observation, including material, state and conditions.
    right : dict
        Second canonical observation, including material, state and conditions.

    ---Returns---
    compatible : bool
        True for the same material and compatible state/condition claims.
        Known temperatures, product forms, orientations and thickness ranges
        must agree exactly. An unspecified condition is retained as unspecified.
        Grade-level physical properties may accompany a named state; a
        grade-level strength is never silently assigned to a named temper.

    ---LaTeX---
    C = \bigwedge_{k \in K_a \cap K_b} (a_k = b_k)

    This is a conservative join, with no interpolation or numerical equation.
    Pairing reference observations does not assert that they share a specimen
    or test. Each observation's own state, conditions, and source must be shown.
    """
    if left["material_id"] != right["material_id"]:
        return False
    states = (left.get("state_id"), right.get("state_id"))
    if all(states) and states[0] != states[1]:
        return False
    if bool(states[0]) != bool(states[1]):
        grade = left if not states[0] else right
        if grade["property_id"] not in GRADE_PHYSICAL_PROPERTIES:
            return False
    a, b = left.get("conditions", {}), right.get("conditions", {})
    return all(a[key] == b[key] for key in a.keys() & b.keys())


def build_selection_database(bundle: dict[str, Any]) -> dict[str, Any]:
    r"""Project the canonical Materials release into traceable Ashby pairs.

    ---Parameters---
    bundle : dict
        Public catalog export with ``canonical`` and ``citation_details``.
        Source citations must already have passed the publication privacy gate.

    ---Returns---
    selection : dict
        Property registry, material/state/observation/source maps, compatible
        chart pairs, Python-computed index values and isoline endpoints, and
        the catalog counts. Every point refers to its exact input observations.

    ---LaTeX---
    M_{\mathrm{beam}} = \frac{\sqrt{E}}{\rho}

    Index equations, scope, derivations, and citations come exclusively from
    :mod:`pycalcs.material_indices` (Ashby, *Materials Selection in Mechanical
    Design*, 4th ed., chapters 5-6). For example the beam index is
    :math:`M=E^{1/2}/\rho`; this module calls the existing implementation.
    Scores use the displayed reference coordinates. Their observation kinds
    remain explicit, including specified bounds and interval midpoints.
    """
    data = bundle["canonical"]
    taxa = {row["id"]: row for row in data["taxa"]}
    materials = {}
    for row in data["materials"]:
        taxon = taxa[row["primary_taxon_id"]]
        root = taxon
        while root["primary_parent_id"]:
            root = taxa[root["primary_parent_id"]]
        materials[row["id"]] = {
            **deepcopy(row),
            "family": FAMILIES.get(root["id"], root["id"]),
            "sub_family": taxon["name"],
        }
    observations = {
        row["id"]: {**deepcopy(row), "plot_value": observation_value(row)}
        for row in data["observations"]
        if row["status"] == "active" and observation_value(row) is not None
    }
    properties = {}
    used_properties = {row["property_id"] for row in observations.values()}
    for row in data["properties"]:
        if row["id"] not in used_properties:
            continue
        unit = row["canonical_unit"]
        multiplier, display_unit = 1, unit
        if unit == "Pa":
            multiplier, display_unit = (
                (1e-9, "GPa") if row["id"] == "youngs_modulus" else (1e-6, "MPa")
            )
        elif row["id"] == "elongation_at_break":
            multiplier, display_unit = 100, "%"
        elif unit == "1":
            display_unit = ""
        properties[row["id"]] = {
            **deepcopy(row), "label": row["name"], "unit": "" if unit == "1" else unit,
            "display_unit": display_unit, "display_multiplier": multiplier,
            "axis_scale": "log",
        }
    indices = {}
    for key, index in INDICES.items():
        required = {PROPERTY_ALIASES.get(p, p) for p in index.required_properties}
        axes = {PROPERTY_ALIASES.get(p, p)
                for p in (index.chart_x, index.chart_y)}
        if not required <= used_properties or not required <= axes:
            continue
        indices[key] = {
            "name": index.name, "expression": index.expression_display,
            "latex": index.expression_latex, "derivation": index.derivation,
            "scope": index.scope, "source": index.source, "maximize": index.maximize,
            "variables": [{"symbol": PROPERTY_SYMBOLS[p],
                           "property": PROPERTY_ALIASES.get(p, p)}
                          for p in index.required_properties],
            "x": PROPERTY_ALIASES.get(index.chart_x, index.chart_x),
            "y": PROPERTY_ALIASES.get(index.chart_y, index.chart_y),
        }
    by_material: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in observations.values():
        by_material[row["material_id"]][row["property_id"]].append(row)
    charts = {}
    for x_prop, y_prop in combinations_with_replacement(sorted(properties), 2):
        chart_indices = [key for key, idx in indices.items()
                         if {idx["x"], idx["y"]} == {x_prop, y_prop}]
        points = []
        for material_id, pool in by_material.items():
            for left, right in product(pool[x_prop], pool[y_prop]):
                if x_prop == y_prop and left["id"] != right["id"]:
                    continue
                if not compatible_observations(left, right):
                    continue
                values = {x_prop: observation_value(left), y_prop: observation_value(right)}
                for alias, canonical in PROPERTY_ALIASES.items():
                    if canonical in values:
                        values[alias] = values[canonical]
                scores = {}
                for key in chart_indices:
                    value = INDICES[key].compute(values)
                    if value is not None and math.isfinite(value) and value > 0:
                        scores[key] = value
                points.append({
                    "id": left["id"] + ":" + right["id"],
                    "material_id": material_id,
                    "state_id": left.get("state_id") or right.get("state_id"),
                    "observations": [left["id"], right["id"]],
                    "conditions": {**left.get("conditions", {}), **right.get("conditions", {})},
                    "scores": scores,
                })
        for key in chart_indices:
            idx = indices[key]
            axis = 0 if idx["x"] == x_prop else 1
            coordinates = [observations[p["observations"][axis]]["plot_value"]
                           for p in points]
            if not coordinates:
                continue
            domain = (min(coordinates) * 0.5, max(coordinates) * 2)
            for point in points:
                if key not in point["scores"]:
                    continue
                line = get_isoline_points(key, point["scores"][key], domain)
                if line and all(math.isfinite(v) and v > 0 for xy in line for v in xy):
                    point.setdefault("isolines", {})[key] = [list(xy) for xy in line]
        charts[x_prop + "|" + y_prop] = {
            "properties": [x_prop, y_prop], "indices": chart_indices,
            "points": points,
        }
    return {
        "schema_version": 1, "counts": deepcopy(data["dataset"]["expected_counts"]),
        "property_registry": properties, "materials": materials,
        "states": {row["id"]: deepcopy(row) for row in data["states"]},
        "observations": observations,
        "sources": {row["id"]: deepcopy(row) for row in bundle["citation_details"]["sources"]},
        "indices": indices, "charts": charts,
    }
