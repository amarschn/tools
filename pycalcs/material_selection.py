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
FAMILIES = {
    "metals": "metal", "engineering-plastics": "polymer", "ceramics": "ceramic",
    "composites": "composite", "woods": "wood", "foams": "foam",
    "elastomers": "elastomer", "glasses": "glass", "concretes": "concrete", "fibers": "fiber",
}
AMBIENT_TEMPERATURE_K = (293.15, 298.15)
CHART_SCHEMA_VERSION = 2
CORE_SIGNIFICANT_DIGITS = 9
# The largest material has 125 rows today. A batch that passes this needs a look.
MAX_ROWS_PER_MATERIAL = 300
# Short names people type in formula axes and typed filters.
PROPERTY_FORMULA_SYMBOLS = {
    "density": "rho", "youngs_modulus": "E", "flexural_modulus": "Ef",
    "ultimate_tensile_strength": "UTS", "tensile_yield_strength": "Sy",
    "flexural_strength": "MOR", "compressive_strength": "Sc",
    "thermal_conductivity": "k", "specific_heat": "cp", "poissons_ratio": "nu",
    "elongation_at_break": "el", "max_service_temperature": "Tmax",
}


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
        Known product forms, orientations and thickness ranges must agree.
        Different temperatures may be paired only when both fall in the stated
        20-25 degrees Celsius reference band. The original temperatures remain
        attached to both observations; no interpolation is performed.
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
    for key in a.keys() & b.keys():
        if a[key] == b[key]:
            continue
        if key == "temperature_K" and all(
            AMBIENT_TEMPERATURE_K[0] <= value <= AMBIENT_TEMPERATURE_K[1]
            for value in (a[key], b[key])
        ):
            continue
        return False
    return True


def compatible_rows(observations: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    r"""Group one material's observations into maximal compatible sets.

    ---Parameters---
    observations : list of dict
        Active, plottable observations of a single material.

    ---Returns---
    rows : list of list of dict
        Every largest set of observations that are compatible pair by pair and
        hold at most one observation per property. Any compatible pair, or any
        larger compatible combination, is contained in at least one row, so a
        chart on any number of properties can read from this list alone.

    ---LaTeX---
    R \subseteq O : \forall a, b \in R,\; a \neq b \Rightarrow C(a, b) \wedge p_a \neq p_b

    Rows are the maximal cliques of the compatibility graph, found with the
    Bron-Kerbosch algorithm with pivoting. Sharing a row does not assert that
    the observations share a specimen or test.
    """
    by_id = {row["id"]: row for row in observations}
    neighbours = {
        left["id"]: {
            right["id"] for right in observations
            if right["id"] != left["id"]
            and right["property_id"] != left["property_id"]
            and compatible_observations(left, right)
        }
        for left in observations
    }
    found: list[list[str]] = []

    def extend(chosen: set[str], candidates: set[str], excluded: set[str]) -> None:
        if not candidates and not excluded:
            found.append(sorted(chosen))
            return
        pivot = max(candidates | excluded, key=lambda node: (len(neighbours[node] & candidates), node))
        for node in sorted(candidates - neighbours[pivot]):
            extend(chosen | {node}, candidates & neighbours[node], excluded & neighbours[node])
            candidates = candidates - {node}
            excluded = excluded | {node}

    extend(set(), set(by_id), set())
    return [[by_id[node] for node in row] for row in sorted(found)]


def index_exponents(index: Any) -> dict[str, float] | None:
    r"""Measure the power-law exponents of a performance index from its own code.

    ---Parameters---
    index : PerformanceIndex
        Entry from :data:`pycalcs.material_indices.INDICES`.

    ---Returns---
    exponents : dict or None
        Exponent per canonical property, or None when the index is not a pure
        power law. Doubling one property reveals its exponent, so the browser
        evaluates each index without a second, hand-written copy of its formula.

    ---LaTeX---
    M = \prod_i v_i^{e_i}, \qquad e_i = \log_2 \frac{M(2 v_i)}{M(v_i)}

    A second probe at unrelated values rejects any index that this product
    cannot reproduce.
    """
    names = list(index.required_properties)
    base = {name: 3.0 for name in names}
    start = index.compute(base)
    if start is None or start <= 0:
        return None
    exponents = {}
    for name in names:
        changed = index.compute({**base, name: 6.0})
        if changed is None or changed <= 0:
            return None
        exponents[name] = round(math.log2(changed / start), 9)
    constant = start / math.prod(3.0 ** value for value in exponents.values())
    probe = {name: 1.7 + i * 2.3 for i, name in enumerate(names)}
    expected = constant * math.prod(probe[name] ** exponents[name] for name in names)
    if not math.isclose(index.compute(probe), expected, rel_tol=1e-6) or not math.isclose(constant, 1.0, rel_tol=1e-6):
        return None
    return {PROPERTY_ALIASES.get(name, name): value for name, value in exponents.items()}


def _significant(value: float | None, digits: int = CORE_SIGNIFICANT_DIGITS) -> float | None:
    """Round a coordinate for the compact chart file. Exports use the details file."""
    return None if value is None else float(f"{value:.{digits}g}")


def build_chart_files(selection: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    r"""Split the selection database into a first-paint file and a details file.

    ---Parameters---
    selection : dict
        Result of :func:`build_selection_database`.

    ---Returns---
    core : dict
        Materials, property and index definitions, one compact column per
        observation field, and the table of compatible rows. Everything the chart,
        filters, results table and parallel axes need.
    details : dict
        Observation IDs, unrounded values, conditions, test methods, notes and
        citations, in the same order as the core observation columns. Loaded when
        someone opens sources or exports a CSV.

    ---LaTeX---
    \{(a, b) : C(a, b)\} = \bigcup_{R \in \mathcal{R}} \{(a, b) : a, b \in R\}

    The row table reproduces every published property pair and no others. Values
    in the core file are rounded to nine significant figures for plotting.

    Raises ``ValueError`` when one material needs more than
    ``MAX_ROWS_PER_MATERIAL`` rows, so that a batch with many conditions is
    reviewed and does not silently inflate the chart file.
    """
    properties = sorted(selection["property_registry"].values(), key=lambda row: row["id"])
    property_index = {row["id"]: i for i, row in enumerate(properties)}
    material_rows = list(selection["materials"].values())
    material_index = {row["id"]: i for i, row in enumerate(material_rows)}
    state_rows = list(selection["states"].values())
    state_index = {row["id"]: i for i, row in enumerate(state_rows)}
    observations = sorted(
        selection["observations"].values(),
        key=lambda row: (material_index[row["material_id"]], property_index[row["property_id"]], row["id"]),
    )
    observation_index = {row["id"]: i for i, row in enumerate(observations)}
    organizations = sorted({row["organization"] for row in selection["sources"].values()})
    organization_index = {name: i for i, name in enumerate(organizations)}
    bases = sorted({row["basis"] for row in observations})
    kinds = ["point", "interval", "lower_bound", "upper_bound"]

    states_by_material: dict[str, list[str]] = defaultdict(list)
    for row in state_rows:
        states_by_material[row["material_id"]].append(row["name"])
    materials = []
    for row in material_rows:
        classes = row.get("classification") or []
        search = [row["name"], row["family"], row["sub_family"], *row.get("aliases", []), *classes,
                  *(item["value"] for item in row.get("designations", [])), *states_by_material[row["id"]]]
        materials.append([
            row["id"], row["name"], row["family"], row["sub_family"],
            classes[-1] if classes else row["sub_family"],
            " ".join(dict.fromkeys(str(item) for item in search)).lower(),
        ])

    by_material: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        by_material[row["material_id"]].append(row)
    rows = []
    for material in material_rows:
        pool = by_material.get(material["id"], [])
        if not pool:
            continue
        found = compatible_rows(pool)
        if len(found) > MAX_ROWS_PER_MATERIAL:
            raise ValueError(
                f"{material['id']} needs {len(found)} compatible rows; review its conditions "
                f"or raise MAX_ROWS_PER_MATERIAL ({MAX_ROWS_PER_MATERIAL})."
            )
        rows.extend([observation_index[item["id"]] for item in row] for row in found)

    def canonical(row: dict[str, Any], key: str) -> float | None:
        return _significant(row["result"]["canonical"].get(key)) if row["result"]["kind"] == "interval" else None

    columns = {
        "material": [material_index[row["material_id"]] for row in observations],
        "state": [state_index[row["state_id"]] if row.get("state_id") else -1 for row in observations],
        "property": [property_index[row["property_id"]] for row in observations],
        "value": [_significant(row["plot_value"]) for row in observations],
        "kind": [kinds.index(row["result"]["kind"]) for row in observations],
        "minimum": [canonical(row, "minimum") for row in observations],
        "maximum": [canonical(row, "maximum") for row in observations],
        "basis": [bases.index(row["basis"]) for row in observations],
        "temperature": [row["conditions"].get("temperature_K") for row in observations],
        "organization": [organization_index[selection["sources"][row["source_id"]]["organization"]] for row in observations],
    }
    indices = {}
    for key, row in selection["indices"].items():
        source = INDICES[key]
        exponents = index_exponents(source)
        indices[key] = {
            **{name: row[name] for name in ("name", "expression", "derivation", "scope", "source",
                                            "maximize", "variables", "x", "y")},
            "slope": source.isoline_slope,
            "exponents": exponents,
        }
    core = {
        "schema_version": CHART_SCHEMA_VERSION,
        "counts": deepcopy(selection["counts"]),
        "properties": [{
            "id": row["id"], "symbol": PROPERTY_FORMULA_SYMBOLS[row["id"]], "label": row["label"],
            "unit": row["unit"], "display_unit": row["display_unit"].replace("^3", "³"),
            "display_multiplier": row["display_multiplier"], "definition": row.get("definition", ""),
        } for row in properties],
        "indices": indices,
        "materials": materials,
        "states": [[row["id"], row["name"]] for row in state_rows],
        "organizations": organizations, "bases": bases, "kinds": kinds,
        "ambient_temperature_K": list(AMBIENT_TEMPERATURE_K),
        "observations": columns,
        "rows": rows,
    }
    sources = {}
    for row in observations:
        source = selection["sources"][row["source_id"]]
        sources[row["source_id"]] = {
            "organization": source["organization"], "title": source["title"],
            "revision": source.get("revision"),
        }
    details = {
        "schema_version": CHART_SCHEMA_VERSION,
        "observations": [{
            "id": row["id"], "value": row["plot_value"], "unit": row["result"]["canonical"].get("unit", ""),
            "minimum": row["result"]["canonical"].get("minimum"),
            "maximum": row["result"]["canonical"].get("maximum"),
            "conditions": row["conditions"], "method": row["test_method"]["reported_label"],
            "notes": row.get("notes") or "", "source": row["source_id"],
            "locator": row["source_locator"]["label"],
        } for row in observations],
        "sources": dict(sorted(sources.items())),
    }
    return core, details


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
            "classification": deepcopy(bundle["citation_details"].get("classifications", {}).get(row["id"], [])),
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
                (1e-9, "GPa") if row["id"] in {"youngs_modulus", "flexural_modulus"} else (1e-6, "MPa")
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
                conditions = {**left.get("conditions", {}),
                              **right.get("conditions", {})}
                temperatures = sorted({o["conditions"]["temperature_K"]
                                       for o in (left, right)
                                       if "temperature_K" in o["conditions"]})
                if len(temperatures) > 1:
                    conditions.pop("temperature_K", None)
                points.append({
                    "id": left["id"] + ":" + right["id"],
                    "material_id": material_id,
                    "state_id": left.get("state_id") or right.get("state_id"),
                    "observations": [left["id"], right["id"]],
                    "conditions": conditions,
                    "temperatures_K": temperatures,
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
