"""Migrate the frozen prototype corpus into the canonical contract.

The legacy corpus is the M0 evidence base. Migration must be lossless and
auditable: every structural change produces a report entry naming what moved and
why, so a reviewer can confirm nothing was quietly dropped.

Three transformations do real semantic work, all of them consequences of
checkpoint 1:

1. `material_state` is retired. Each value maps to a precise state attribute.
2. Observation-context keys fixed on a state (product form, moisture) move to
   that state's observations. A state left with no defining attribute is
   dissolved, because product form is a navigable level rather than an identity.
3. Legacy state labels such as "T6 . plate" are split, so form is never silently
   fixed by a label.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from . import CONTRACT_VERSION
from .registries import (
    CONDITIONING_LABELS,
    LEGACY_MATERIAL_STATE,
    basis_registry,
    condition_registry,
    quantity_kind_for,
)
from .units import (
    default_display_unit,
    find_conversion,
    round_to_significant_figures,
    significant_figures,
)

LEGACY_SOURCE_ID = "synthetic-fixture"

# Property renames adopted at checkpoint 1. The prototype corpus already uses
# the precise ids; the mapping is retained as compatibility search data for the
# original static builder, which still uses the ambiguous names.
LEGACY_PROPERTY_IDS = {
    "yield_strength": "tensile_yield_strength",
    "tensile_strength": "ultimate_tensile_strength",
}

LABEL_SEPARATOR = " · "  # "T6 · plate"

TEMPER_PREFIXES = ("T4", "T6", "T651", "T73")


class MigrationReport:
    """Auditable record of every structural change migration performed."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {}

    def note(self, kind: str, subject: str, detail: str, **context: Any) -> None:
        self.entries.append(
            {"kind": kind, "subject": subject, "detail": detail, **context}
        )
        self.counts[kind] = self.counts.get(kind, 0) + 1

    def sorted_entries(self) -> list[dict[str, Any]]:
        return sorted(self.entries, key=lambda e: (e["kind"], e["subject"], e["detail"]))

    def as_dict(self) -> dict[str, Any]:
        return {
            "counts": dict(sorted(self.counts.items())),
            "entries": self.sorted_entries(),
        }


def _split_label(label: str) -> tuple[str, str | None]:
    """Split "T6 · plate" into its state name and the form the label embedded."""
    if LABEL_SEPARATOR in label:
        name, trailing = label.split(LABEL_SEPARATOR, 1)
        return name.strip(), trailing.strip()
    return label.strip(), None


def _interval(value: Any) -> Any:
    """Normalize a legacy `[min, max]` pair into the contract's interval object."""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2:
        return {"minimum": value[0], "maximum": value[1]}
    return value


# Trailing zeros in an integer are ambiguous: "50" may assert one or two
# significant digits. The conservative reading is that they are not significant,
# but taken literally that renders Shore A 50 as "5e+01". Two digits is the
# floor, which is what a datasheet writing a round number almost always means.
# This is a migration assumption about legacy synthetic data, not a general
# truth about numbers, so it lives here rather than in `units`.
MINIMUM_MIGRATED_SIGNIFICANT_FIGURES = 2


def _reported_from_canonical(
    canonical_value: float, quantity_kind: str
) -> tuple[float, str, int]:
    """Derive the reported form the legacy corpus displayed but never stored.

    The legacy corpus kept canonical values only, so source precision has to be
    recovered from how the number was written. This is exactly the information
    that would be unrecoverable if the contract dropped the reported form, and
    it is why checkpoint 1 kept it.
    """
    unit = default_display_unit(quantity_kind) or "1"
    conversion = find_conversion(quantity_kind, unit)
    figures = max(
        significant_figures(canonical_value), MINIMUM_MIGRATED_SIGNIFICANT_FIGURES
    )
    if conversion is None:
        return canonical_value, unit, figures
    displayed = conversion.to_display(canonical_value)
    return round_to_significant_figures(displayed, figures), unit, figures


def migrate(legacy: Mapping[str, Any]) -> tuple[dict[str, Any], MigrationReport]:
    """Return the canonical dataset and an auditable migration report."""
    report = MigrationReport()

    properties = _migrate_properties(legacy)
    property_by_id = {prop["id"]: prop for prop in properties}
    taxa = _migrate_taxa(legacy)
    materials = _migrate_materials(legacy, report)
    states, dissolved, pushed_down = _migrate_states(legacy, report)
    observations = _migrate_observations(
        legacy, property_by_id, dissolved, pushed_down, report
    )

    dataset = {
        "dataset": {
            "id": "schema-lab-v0-1-0-migrated",
            "contract_version": CONTRACT_VERSION,
            "corpus_version": str(legacy.get("corpus_version", "unknown")),
            "synthetic": True,
            "warning": str(
                legacy.get(
                    "warning",
                    "Fabricated values for interface and schema testing only. "
                    "Not engineering data.",
                )
            ),
            "generator": {
                "name": "schema_lab.migrate",
                "version": CONTRACT_VERSION,
                "seed": None,
            },
            "expected_counts": {
                "taxa": len(taxa),
                "materials": len(materials),
                "states": len(states),
                "observations": len(observations),
                "properties": len(properties),
                "property_groups": len(legacy.get("property_groups") or []),
            },
        },
        "taxa": taxa,
        "properties": properties,
        "property_groups": _migrate_property_groups(legacy),
        "conditions": condition_registry(),
        "bases": basis_registry(),
        "sources": _sources(legacy),
        "materials": materials,
        "states": states,
        "observations": observations,
        "legacy_mappings": {
            "property_ids": dict(sorted(LEGACY_PROPERTY_IDS.items())),
            "condition_keys": {
                "material_state": "heat_treatment",
            },
            "state_ids": {state_id: None for state_id in sorted(dissolved)},
        },
    }
    return dataset, report


def _migrate_taxa(legacy: Mapping[str, Any]) -> list[dict[str, Any]]:
    migrated = []
    for taxon in legacy.get("taxa") or []:
        migrated.append(
            {
                "id": taxon["id"],
                "name": taxon["name"],
                "aliases": list(taxon.get("aliases") or []),
                "primary_parent_id": taxon.get("parent_id"),
                "supplemental_broader_ids": [],
            }
        )
    return migrated


def _migrate_properties(legacy: Mapping[str, Any]) -> list[dict[str, Any]]:
    migrated = []
    for prop in legacy.get("properties") or []:
        unit = prop["canonical_unit"]
        migrated.append(
            {
                "id": prop["id"],
                "name": prop["name"],
                "aliases": list(prop.get("aliases") or []),
                "quantity_kind": quantity_kind_for(prop["id"], unit),
                "canonical_unit": unit,
                "group_id": prop.get("group_id"),
            }
        )
    return migrated


def _migrate_property_groups(legacy: Mapping[str, Any]) -> list[dict[str, Any]]:
    migrated = []
    for group in legacy.get("property_groups") or []:
        migrated.append(
            {
                "id": group["id"],
                "name": group["name"],
                "aliases": list(group.get("aliases") or []),
                "member_property_ids": list(group.get("member_ids") or []),
            }
        )
    return migrated


# The legacy corpus carries no source collection, only source ids on
# observations. `synthetic-fixture-b` is the deliberate second source that
# disagrees with the first about AX70-T6 in the LT direction; it must stay a
# distinct source or the conflict collapses into a duplicate.
SOURCE_TITLES = {
    "synthetic-fixture": "Synthetic prototype fixture",
    "synthetic-fixture-b": "Synthetic prototype fixture, second issuer",
}


def _sources(legacy: Mapping[str, Any]) -> list[dict[str, Any]]:
    observed = {
        observation.get("source_id") or LEGACY_SOURCE_ID
        for observation in legacy.get("observations") or []
    }
    revision = str(legacy.get("build_version", "unknown"))
    return [
        {
            "id": source_id,
            "title": SOURCE_TITLES.get(source_id, "Synthetic prototype fixture"),
            "organization": "Materials Schema Lab",
            "source_type": "synthetic_fixture",
            "publication_date": None,
            "revision": revision,
            "license": "CC0-1.0",
            "synthetic": True,
        }
        for source_id in sorted(observed)
    ]


def _migrate_materials(
    legacy: Mapping[str, Any], report: MigrationReport
) -> list[dict[str, Any]]:
    migrated = []
    for material in legacy.get("materials") or []:
        taxon_ids = list(material.get("taxon_ids") or [])
        primary = taxon_ids[0] if taxon_ids else None
        supplemental = taxon_ids[1:]
        if supplemental:
            report.note(
                "material_supplemental_taxa",
                material["id"],
                "First taxon became the primary browse path; the rest became "
                "supplemental classifications.",
                primary=primary,
                supplemental=supplemental,
            )
        designations = [
            {"system_id": "synthetic_fixture", "value": value}
            for value in material.get("designations") or []
        ]
        record = {
            "id": material["id"],
            "name": material["name"],
            "identity_kind": material["identity_kind"],
            "aliases": list(material.get("aliases") or []),
            "designations": designations,
            "primary_taxon_id": primary,
            "supplemental_taxon_ids": supplemental,
        }
        if material.get("notes"):
            record["notes"] = material["notes"]
        migrated.append(record)
    return migrated


def _migrate_states(
    legacy: Mapping[str, Any], report: MigrationReport
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, dict[str, Any]]]:
    """Migrate states, returning survivors, dissolved states, and pushed-down context.

    `dissolved` maps a removed state id to its material id. `pushed_down` maps a
    state id to the observation context that state used to fix.
    """
    registry = {entry["id"]: entry for entry in condition_registry()}
    states: list[dict[str, Any]] = []
    dissolved: dict[str, str] = {}
    pushed_down: dict[str, dict[str, Any]] = {}

    for state in legacy.get("states") or []:
        state_id = state["id"]
        name, embedded_form = _split_label(str(state.get("label", "")))
        attributes: dict[str, Any] = {}
        context: dict[str, Any] = {}

        if embedded_form:
            report.note(
                "label_split",
                state_id,
                f"Label {state.get('label')!r} embedded product form "
                f"{embedded_form!r}; the state name is now {name!r} and form stays "
                "explicit on each observation.",
                name=name,
                product_form=embedded_form,
            )

        for key, value in (state.get("fixed_conditions") or {}).items():
            if key == "material_state":
                mapped = LEGACY_MATERIAL_STATE.get(value)
                if mapped is None:
                    report.note(
                        "unmapped_legacy_state",
                        state_id,
                        f"material_state {value!r} has no registered mapping and "
                        "requires review.",
                        value=value,
                    )
                    continue
                mapped_key, mapped_value = mapped
                attributes[mapped_key] = mapped_value
                report.note(
                    "legacy_state_mapped",
                    state_id,
                    f"material_state {value!r} became {mapped_key}={mapped_value!r}.",
                    key=mapped_key,
                    value=mapped_value,
                )
                continue

            registered = registry.get(key)
            if registered is None:
                report.note(
                    "unknown_condition",
                    state_id,
                    f"{key!r} is not registered and was dropped pending review.",
                    key=key,
                )
                continue

            if registered["allowed_placement"] == "observation_condition":
                context[key] = _interval(value)
                report.note(
                    "attribute_moved_to_observations",
                    state_id,
                    f"{key!r} is observation context and moved from the state onto "
                    "each of its observations.",
                    key=key,
                    value=value,
                )
                continue

            attributes[key] = _interval(value)

        # A temper is a lookup identity but the legacy corpus only carried it in
        # the label, so recover it as a registered attribute.
        if name in TEMPER_PREFIXES:
            attributes["temper"] = name
            report.note(
                "temper_recovered",
                state_id,
                f"Temper {name!r} was only present in the label and is now a "
                "registered fixed attribute.",
                temper=name,
            )

        # A named conditioning state must come from the label, never from a
        # measured moisture number.
        conditioning = CONDITIONING_LABELS.get(name.lower())
        if conditioning:
            attributes["conditioning_state"] = conditioning
            report.note(
                "conditioning_state_named",
                state_id,
                f"Label {name!r} became conditioning_state={conditioning!r}; the "
                "measured moisture stays on the observations.",
                conditioning_state=conditioning,
            )

        if context:
            pushed_down[state_id] = context

        if not attributes:
            dissolved[state_id] = state["material_id"]
            report.note(
                "state_dissolved",
                state_id,
                f"State {name!r} was defined only by observation context and is not "
                "a lookup identity. Its observations now attach directly to the "
                "material, and the drill-down level is derived from the navigable "
                "condition instead.",
                material_id=state["material_id"],
                name=name,
            )
            continue

        record = {
            "id": state_id,
            "material_id": state["material_id"],
            "name": name,
            "aliases": list(state.get("aliases") or []),
            "fixed_attributes": attributes,
            "supplemental_taxon_ids": list(state.get("taxon_ids") or []),
        }
        states.append(record)

    return states, dissolved, pushed_down


def _migrate_observations(
    legacy: Mapping[str, Any],
    property_by_id: Mapping[str, Mapping[str, Any]],
    dissolved: Mapping[str, str],
    pushed_down: Mapping[str, Mapping[str, Any]],
    report: MigrationReport,
) -> list[dict[str, Any]]:
    registry = {entry["id"]: entry for entry in condition_registry()}
    migrated: list[dict[str, Any]] = []

    for observation in legacy.get("observations") or []:
        observation_id = observation["id"]
        state_id = observation.get("state_id")
        conditions: dict[str, Any] = {}

        for key, value in (observation.get("conditions") or {}).items():
            registered = registry.get(key)
            if registered is None:
                report.note(
                    "unknown_condition",
                    observation_id,
                    f"{key!r} is not registered and was dropped pending review.",
                    key=key,
                )
                continue
            if registered["allowed_placement"] == "state_fixed_attribute" or key == "material_state":
                # The state already fixes this fact. Checkpoint 1 forbids copying
                # a state-fixed attribute onto observations, and the corpus was
                # verified to hold no conflicting duplicate before stripping.
                report.note(
                    "duplicate_state_attribute_stripped",
                    observation_id,
                    f"{key!r} is fixed once on the named state and was removed from "
                    "the observation.",
                    key=key,
                )
                continue
            conditions[key] = _interval(value)

        # Context the state used to fix now belongs to each of its observations.
        for key, value in (pushed_down.get(state_id) or {}).items():
            conditions.setdefault(key, value)

        if state_id in dissolved:
            state_id = None

        prop = property_by_id.get(observation["property_id"])
        quantity_kind = prop["quantity_kind"] if prop else "unknown"
        result = _migrate_result(observation, quantity_kind)

        migrated.append(
            {
                "id": observation_id,
                "material_id": observation["material_id"],
                "state_id": state_id,
                "property_id": observation["property_id"],
                "result": result,
                "uncertainty": None,
                "basis": observation["basis"],
                "conditions": conditions,
                "test_method": None,
                "source_id": observation.get("source_id") or LEGACY_SOURCE_ID,
                "source_locator": _migrate_locator(observation),
                "status": "active",
                "supersedes_observation_ids": [],
            }
        )

    return migrated


def _migrate_result(
    observation: Mapping[str, Any], quantity_kind: str
) -> dict[str, Any]:
    unit = observation["unit"]
    value = observation.get("value")
    low = observation.get("value_min")
    high = observation.get("value_max")

    if value is not None:
        reported_value, reported_unit, figures = _reported_from_canonical(
            value, quantity_kind
        )
        return {
            "kind": "point",
            "reported": {
                "value": reported_value,
                "unit": reported_unit,
                "significant_figures": figures,
            },
            "canonical": {"value": value, "unit": unit},
        }

    if low is not None and high is not None:
        reported_low, reported_unit, low_figures = _reported_from_canonical(
            low, quantity_kind
        )
        reported_high, _, high_figures = _reported_from_canonical(high, quantity_kind)
        return {
            "kind": "interval",
            "reported": {
                "minimum": reported_low,
                "maximum": reported_high,
                "unit": reported_unit,
                "significant_figures": max(low_figures, high_figures),
            },
            "canonical": {"minimum": low, "maximum": high, "unit": unit},
        }

    return {
        "kind": "unavailable",
        "reason": "The prototype corpus recorded no value for this observation.",
    }


def _migrate_locator(observation: Mapping[str, Any]) -> dict[str, Any]:
    locator = observation.get("source_locator")
    if isinstance(locator, Mapping):
        return dict(locator)
    return {"label": str(locator) if locator else "Unlocated synthetic fixture entry"}
