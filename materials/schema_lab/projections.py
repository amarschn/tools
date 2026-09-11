"""Derived semantics: record assembly, coverage counts, and level projections.

These are the counting and range rules the prototype currently performs inside
page code. Moving them here makes them testable and keeps the canonical records
immutable: assembly composes a view, it never writes back.

The level projection implements the drill-down adopted at checkpoint 1. A
navigable condition such as product form generates a level below a named state
even though it is stored on the observation, so `AX70 T6 plate` is a place a
user can land without product form becoming part of a stored identity.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

NUMERIC_KINDS = frozenset({"point", "interval", "lower_bound", "upper_bound"})
ASSERTION_KINDS = frozenset({"unavailable", "not_applicable"})


class Corpus:
    """Indexed read-only view over a validated dataset."""

    def __init__(self, dataset: Mapping[str, Any]) -> None:
        self.dataset = dataset
        self.taxa = {row["id"]: row for row in dataset.get("taxa", ())}
        self.properties = {row["id"]: row for row in dataset.get("properties", ())}
        self.property_groups = {row["id"]: row for row in dataset.get("property_groups", ())}
        self.conditions = {row["id"]: row for row in dataset.get("conditions", ())}
        self.materials = {row["id"]: row for row in dataset.get("materials", ())}
        self.states = {row["id"]: row for row in dataset.get("states", ())}
        self.observations = list(dataset.get("observations", ()))

        self.states_by_material: dict[str, list[dict]] = {}
        for state in dataset.get("states", ()):
            self.states_by_material.setdefault(state["material_id"], []).append(state)
        for bucket in self.states_by_material.values():
            bucket.sort(key=lambda row: (row["name"], row["id"]))

        self.observations_by_material: dict[str, list[dict]] = {}
        self.observations_by_state: dict[str, list[dict]] = {}
        for observation in self.observations:
            self.observations_by_material.setdefault(
                observation["material_id"], []
            ).append(observation)
            if observation.get("state_id"):
                self.observations_by_state.setdefault(
                    observation["state_id"], []
                ).append(observation)

        self.children_by_taxon: dict[str, list[dict]] = {}
        for taxon in dataset.get("taxa", ()):
            parent = taxon.get("primary_parent_id")
            if parent:
                self.children_by_taxon.setdefault(parent, []).append(taxon)
        for bucket in self.children_by_taxon.values():
            bucket.sort(key=lambda row: (row["name"], row["id"]))

        # Primary membership only. Supplemental membership is navigation, and
        # counting it here would double-count the material in its coverage.
        self.materials_by_primary_taxon: dict[str, list[dict]] = {}
        for material in dataset.get("materials", ()):
            self.materials_by_primary_taxon.setdefault(
                material["primary_taxon_id"], []
            ).append(material)
        for bucket in self.materials_by_primary_taxon.values():
            bucket.sort(key=lambda row: (row["name"], row["id"]))

    def navigable_conditions(self) -> list[str]:
        return sorted(
            row["id"] for row in self.conditions.values() if row.get("navigable")
        )

    def descendant_taxa(self, taxon_id: str) -> list[str]:
        """Taxon plus every descendant on the primary browse path, depth first."""
        collected = [taxon_id]
        for child in self.children_by_taxon.get(taxon_id, ()):
            collected.extend(self.descendant_taxa(child["id"]))
        return collected

    def materials_under(self, taxon_id: str) -> list[dict]:
        seen: dict[str, dict] = {}
        for descendant in self.descendant_taxa(taxon_id):
            for material in self.materials_by_primary_taxon.get(descendant, ()):
                seen.setdefault(material["id"], material)
        return [seen[key] for key in sorted(seen, key=lambda k: (seen[k]["name"], k))]


# --------------------------------------------------------------------------
# Spans
# --------------------------------------------------------------------------


def active(observations: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Superseded observations stay auditable but are excluded by default."""
    return [row for row in observations if row.get("status", "active") == "active"]


def _endpoints(result: Mapping[str, Any]) -> tuple[float, float] | None:
    """Canonical endpoints an observation contributes to a span.

    A reported interval contributes both endpoints. Uncertainty is deliberately
    ignored: it describes confidence in one result and must not silently widen
    the range a category appears to span.
    """
    kind = result.get("kind")
    canonical = result.get("canonical")
    if kind not in NUMERIC_KINDS or not isinstance(canonical, Mapping):
        return None
    if kind == "interval":
        low, high = canonical.get("minimum"), canonical.get("maximum")
        if low is None or high is None:
            return None
        return float(low), float(high)
    value = canonical.get("value")
    if value is None:
        return None
    return float(value), float(value)


def span(
    observations: Iterable[Mapping[str, Any]],
    property_id: str,
    *,
    include_superseded: bool = False,
) -> dict[str, Any] | None:
    """Observed range for one property, or None when there is no coverage.

    Zero coverage is a valid empty result rather than a zero, and a single
    observed value renders as one value rather than a degenerate `x-x` range.

    Superseded observations are excluded by default. Filtering here rather than
    in each caller is deliberate: a withdrawn value silently widening a
    published range is the failure this rule exists to prevent, and it should
    not depend on every call site remembering to filter first.
    """
    lows: list[float] = []
    highs: list[float] = []
    unit: str | None = None
    counted = 0
    unavailable = 0
    bounded = False
    # A range must not be rendered more precisely than its least precise
    # contributor, so the span carries the minimum rather than dropping the
    # per-observation precision the contract went to trouble to keep.
    figures: list[int] = []

    pool = observations if include_superseded else active(observations)
    for observation in pool:
        if observation.get("property_id") != property_id:
            continue
        result = observation.get("result") or {}
        if result.get("kind") in ASSERTION_KINDS:
            unavailable += 1
            continue
        pair = _endpoints(result)
        if pair is None:
            continue
        if result.get("kind") in ("lower_bound", "upper_bound"):
            bounded = True
        lows.append(pair[0])
        highs.append(pair[1])
        canonical_unit = (result.get("canonical") or {}).get("unit")
        if unit is None:
            unit = canonical_unit
        reported_figures = (result.get("reported") or {}).get("significant_figures")
        if isinstance(reported_figures, int):
            figures.append(reported_figures)
        counted += 1

    if counted == 0:
        if unavailable:
            return {
                "property_id": property_id,
                "observation_count": 0,
                "unavailable_count": unavailable,
                "minimum": None,
                "maximum": None,
                "unit": None,
                "singleton": False,
                "includes_bound": False,
                "significant_figures": None,
            }
        return None

    minimum, maximum = min(lows), max(highs)
    return {
        "property_id": property_id,
        "observation_count": counted,
        "unavailable_count": unavailable,
        "minimum": minimum,
        "maximum": maximum,
        "unit": unit,
        "singleton": minimum == maximum,
        "includes_bound": bounded,
        "significant_figures": min(figures) if figures else None,
    }


def mixed_condition_flags(
    observations: Sequence[Mapping[str, Any]], corpus: Corpus
) -> list[str]:
    """Condition keys taking more than one value across these observations.

    Deterministic and sorted, so a warning list never reorders between runs.
    """
    values: dict[str, set[str]] = {}
    for observation in observations:
        for key, value in (observation.get("conditions") or {}).items():
            values.setdefault(key, set()).add(_stable(value))
    flags = [key for key, seen in values.items() if len(seen) > 1]
    bases = {observation.get("basis") for observation in observations}
    if len(bases) > 1:
        flags.append("basis")
    methods = {
        _stable((observation.get("test_method") or {}).get("reported_label"))
        for observation in observations
    }
    if len(methods) > 1:
        flags.append("test_method")
    return sorted(flags)


def _stable(value: Any) -> str:
    if isinstance(value, Mapping):
        return "{" + ",".join(f"{k}:{_stable(value[k])}" for k in sorted(value)) + "}"
    return repr(value)


# --------------------------------------------------------------------------
# Record assembly
# --------------------------------------------------------------------------


def effective_context(
    observation: Mapping[str, Any], corpus: Corpus
) -> dict[str, Any]:
    """Union of a state's fixed attributes and an observation's own conditions.

    This is a derived display view. Canonical records are never mutated, and the
    two containers stay separate in storage so placement rules remain checkable.
    """
    context: dict[str, Any] = {}
    state_id = observation.get("state_id")
    if state_id and state_id in corpus.states:
        context.update(corpus.states[state_id].get("fixed_attributes") or {})
    context.update(observation.get("conditions") or {})
    return dict(sorted(context.items()))


def assemble_material_record(
    corpus: Corpus, material_id: str, *, include_superseded: bool = False
) -> dict[str, Any]:
    """Full record for one material: its own data plus each of its states.

    Direct material observations are not copied into states and state
    observations are not copied up. Reuse requires an explicit, source-traceable
    observation.
    """
    material = corpus.materials[material_id]
    all_observations = corpus.observations_by_material.get(material_id, [])
    pool = all_observations if include_superseded else active(all_observations)

    direct = sorted(
        (row for row in pool if not row.get("state_id")),
        key=lambda row: (row["property_id"], row["id"]),
    )

    states = []
    for state in corpus.states_by_material.get(material_id, []):
        state_observations = sorted(
            (row for row in pool if row.get("state_id") == state["id"]),
            key=lambda row: (row["property_id"], row["id"]),
        )
        states.append(
            {
                "id": state["id"],
                "name": state["name"],
                "fixed_attributes": dict(sorted((state.get("fixed_attributes") or {}).items())),
                "observations": [
                    {
                        "id": row["id"],
                        "property_id": row["property_id"],
                        "result": row["result"],
                        "uncertainty": row.get("uncertainty"),
                        "basis": row.get("basis"),
                        "effective_context": effective_context(row, corpus),
                        "source_id": row.get("source_id"),
                        "source_locator": row.get("source_locator"),
                        "status": row.get("status", "active"),
                    }
                    for row in state_observations
                ],
                "coverage": coverage(state_observations, corpus),
                "mixed_conditions": mixed_condition_flags(state_observations, corpus),
            }
        )

    return {
        "id": material["id"],
        "name": material["name"],
        "primary_taxon_id": material["primary_taxon_id"],
        "supplemental_taxon_ids": list(material.get("supplemental_taxon_ids") or []),
        "designations": list(material.get("designations") or []),
        "direct_observations": [
            {
                "id": row["id"],
                "property_id": row["property_id"],
                "result": row["result"],
                "effective_context": effective_context(row, corpus),
                "source_locator": row.get("source_locator"),
                "status": row.get("status", "active"),
            }
            for row in direct
        ],
        "states": states,
        "coverage": coverage(pool, corpus),
    }


# --------------------------------------------------------------------------
# Counts
# --------------------------------------------------------------------------


def coverage(
    observations: Sequence[Mapping[str, Any]], corpus: Corpus
) -> dict[str, int]:
    """Counts kept deliberately separate rather than collapsed into one number."""
    live = active(observations)
    return {
        "observations": len(live),
        "superseded_observations": len(observations) - len(live),
        "properties_covered": len(
            {
                row["property_id"]
                for row in live
                if (row.get("result") or {}).get("kind") in NUMERIC_KINDS
            }
        ),
        "unavailable_assertions": len(
            [
                row
                for row in live
                if (row.get("result") or {}).get("kind") in ASSERTION_KINDS
            ]
        ),
        "condition_sets": len({_stable(row.get("conditions") or {}) for row in live}),
        "bases": len({row.get("basis") for row in live}),
        "sources": len({row.get("source_id") for row in live}),
    }


def taxon_coverage(corpus: Corpus, taxon_id: str, property_id: str) -> dict[str, Any]:
    """Coverage of one property across a category's concrete members.

    Categories never own measurements: this is calculated from members, and a
    material reached through a supplemental path is not counted twice.
    """
    materials = corpus.materials_under(taxon_id)
    observations: list[Mapping[str, Any]] = []
    covered_subjects = 0
    eligible_subjects = 0

    for material in materials:
        material_observations = active(
            corpus.observations_by_material.get(material["id"], [])
        )
        states = corpus.states_by_material.get(material["id"], [])
        # A material with named states offers those states as subjects; a
        # material carrying data directly is itself one subject.
        subjects = [state["id"] for state in states] or [material["id"]]
        eligible_subjects += len(subjects)
        for subject in subjects:
            subject_observations = [
                row
                for row in material_observations
                if (row.get("state_id") or row["material_id"]) == subject
            ]
            if span(subject_observations, property_id):
                covered_subjects += 1
        observations.extend(material_observations)

    result = span(observations, property_id) or {
        "property_id": property_id,
        "observation_count": 0,
        "unavailable_count": 0,
        "minimum": None,
        "maximum": None,
        "unit": None,
        "singleton": False,
        "includes_bound": False,
        "significant_figures": None,
    }
    result.update(
        {
            "taxon_id": taxon_id,
            "materials": len(materials),
            "eligible_subjects": eligible_subjects,
            "covered_subjects": covered_subjects,
        }
    )
    return result


# --------------------------------------------------------------------------
# Navigable levels
# --------------------------------------------------------------------------


def drilldown_levels(
    corpus: Corpus, material_id: str, state_id: str | None = None
) -> list[dict[str, Any]]:
    """Levels generated by navigable conditions beneath a material or state.

    This is the checkpoint 1 decision in code: product form is stored on the
    observation, but it still yields a landable level. A level is only offered
    when the observations actually distinguish one, so a material whose data
    names no navigable condition simply has no such level rather than an empty
    one.
    """
    if state_id:
        pool = active(corpus.observations_by_state.get(state_id, []))
    else:
        pool = [
            row
            for row in active(corpus.observations_by_material.get(material_id, []))
            if not row.get("state_id")
        ]

    levels: list[dict[str, Any]] = []
    for key in corpus.navigable_conditions():
        buckets: dict[str, list[Mapping[str, Any]]] = {}
        for observation in pool:
            value = (observation.get("conditions") or {}).get(key)
            if value is None:
                continue
            buckets.setdefault(str(value), []).append(observation)
        if not buckets:
            continue
        levels.append(
            {
                "condition_id": key,
                "material_id": material_id,
                "state_id": state_id,
                "values": [
                    {
                        "value": value,
                        "observation_count": len(buckets[value]),
                        "properties_covered": len(
                            {row["property_id"] for row in buckets[value]}
                        ),
                        "mixed_conditions": mixed_condition_flags(buckets[value], corpus),
                    }
                    # Alphabetic, never ordered by a numeric endpoint.
                    for value in sorted(buckets)
                ],
            }
        )
    return levels


def navigation_ranges(
    corpus: Corpus, material_id: str, property_id: str
) -> dict[str, Any]:
    """Ranges at every level under one material, for one property.

    Checkpoint 1 requires an aggregated range at each level so a user who does
    not yet know which state or form they want still sees the envelope and can
    narrow it, rather than hitting an empty page.
    """
    material_observations = active(corpus.observations_by_material.get(material_id, []))
    result: dict[str, Any] = {
        "material_id": material_id,
        "property_id": property_id,
        "material": span(material_observations, property_id),
        "states": [],
    }

    for state in corpus.states_by_material.get(material_id, []):
        state_observations = active(corpus.observations_by_state.get(state["id"], []))
        state_entry: dict[str, Any] = {
            "state_id": state["id"],
            "name": state["name"],
            "span": span(state_observations, property_id),
            "levels": [],
        }
        for level in drilldown_levels(corpus, material_id, state["id"]):
            key = level["condition_id"]
            values = []
            for entry in level["values"]:
                subset = [
                    row
                    for row in state_observations
                    if str((row.get("conditions") or {}).get(key)) == entry["value"]
                ]
                values.append(
                    {
                        "value": entry["value"],
                        "span": span(subset, property_id),
                    }
                )
            state_entry["levels"].append({"condition_id": key, "values": values})
        result["states"].append(state_entry)

    return result
