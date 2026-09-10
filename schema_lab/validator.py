"""Structural and semantic validation for the schema lab contract.

Structural validation uses JSON Schema Draft 2020-12 and needs the optional
`jsonschema` package. Semantic validation is pure standard library and always
runs, because it encodes the rules the checkpoint actually decided: reference
integrity, taxonomy shape, condition placement, unit coherence, precision, and
provenance.

Every diagnostic carries a stable code from `diagnostics.py` and a
JSON-pointer-style path, so negative fixtures assert on structure rather than
prose.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import CONTRACT_VERSION, diagnostics as D
from .diagnostics import Diagnostic
from .units import is_coherent_si_unit

# Uppercase is permitted because unit-suffixed condition keys carry SI symbol
# case deliberately: `temperature_K` is kelvin, and lowercasing it would lose
# that. Identifiers are otherwise lowercase by convention.
_ID_RE = re.compile(r"^[A-Za-z0-9]+([-_.][A-Za-z0-9]+)*$")

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "schemas" / "v0.1.0" / "dataset.schema.json"
)

_COLLECTIONS = (
    "taxa",
    "properties",
    "property_groups",
    "conditions",
    "bases",
    "sources",
    "materials",
    "states",
    "observations",
)

_NUMERIC_RESULT_KINDS = frozenset({"point", "interval", "lower_bound", "upper_bound"})
_ASSERTION_RESULT_KINDS = frozenset({"unavailable", "not_applicable"})


# --------------------------------------------------------------------------
# Structural validation
# --------------------------------------------------------------------------


def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def jsonschema_available() -> bool:
    try:  # pragma: no cover - trivial import probe
        import jsonschema  # noqa: F401
    except ImportError:
        return False
    return True


def validate_structure(dataset: Mapping[str, Any]) -> list[Diagnostic]:
    """Validate document shape against the JSON Schema.

    Returns an empty list when `jsonschema` is unavailable; callers that require
    structural coverage should check `jsonschema_available()` first.
    """
    try:
        import jsonschema
    except ImportError:
        return []

    validator_cls = jsonschema.validators.validator_for(schema())
    validator = validator_cls(schema())
    found: list[Diagnostic] = []
    for error in validator.iter_errors(dataset):
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        found.append(
            Diagnostic(
                code=D.SCHEMA_VIOLATION,
                path=pointer if pointer != "/" else "/",
                message=error.message,
                context={"validator": error.validator},
            )
        )
    return sorted(found, key=D.sort_key)


# --------------------------------------------------------------------------
# Semantic validation
# --------------------------------------------------------------------------


class _Semantic:
    def __init__(self, dataset: Mapping[str, Any]) -> None:
        self.dataset = dataset
        self.found: list[Diagnostic] = []
        self.index: dict[str, dict[str, Mapping[str, Any]]] = {}

    # -- helpers ---------------------------------------------------------

    def add(
        self,
        code: str,
        path: str,
        message: str,
        severity: str = D.ERROR,
        **context: Any,
    ) -> None:
        self.found.append(
            Diagnostic(
                code=code, path=path, message=message, severity=severity, context=context
            )
        )

    def rows(self, collection: str) -> Sequence[Mapping[str, Any]]:
        value = self.dataset.get(collection)
        return value if isinstance(value, list) else ()

    def known(self, collection: str, identifier: Any) -> bool:
        return identifier in self.index.get(collection, {})

    def require_ref(
        self, collection: str, identifier: Any, path: str, what: str
    ) -> bool:
        if identifier is None:
            return True
        if not self.known(collection, identifier):
            self.add(
                D.REF_MISSING,
                path,
                f"{what} {identifier!r} is not present in {collection}.",
                collection=collection,
                identifier=identifier,
            )
            return False
        return True

    # -- passes ----------------------------------------------------------

    def run(self) -> list[Diagnostic]:
        self.check_manifest()
        self.build_index()
        self.check_taxonomy()
        self.check_property_registry()
        self.check_condition_registry()
        self.check_materials()
        self.check_states()
        self.check_observations()
        self.check_alias_collisions()
        return sorted(self.found, key=D.sort_key)

    def check_manifest(self) -> None:
        manifest = self.dataset.get("dataset")
        if not isinstance(manifest, Mapping):
            return
        declared = manifest.get("contract_version")
        if declared is None:
            return
        base = str(declared).split("-", 1)[0]
        if base != CONTRACT_VERSION:
            self.add(
                D.CONTRACT_VERSION_UNSUPPORTED,
                "/dataset/contract_version",
                f"Contract version {declared!r} is not supported by this validator "
                f"(expected {CONTRACT_VERSION}).",
                declared=declared,
                supported=CONTRACT_VERSION,
            )

    def build_index(self) -> None:
        for collection in _COLLECTIONS:
            table: dict[str, Mapping[str, Any]] = {}
            for position, row in enumerate(self.rows(collection)):
                if not isinstance(row, Mapping):
                    continue
                identifier = row.get("id")
                path = f"/{collection}/{position}/id"
                if not isinstance(identifier, str) or not _ID_RE.match(identifier):
                    self.add(
                        D.ID_MALFORMED,
                        path,
                        f"{identifier!r} is not a well-formed identifier.",
                        identifier=identifier,
                    )
                    continue
                if identifier in table:
                    self.add(
                        D.ID_DUPLICATE,
                        path,
                        f"{identifier!r} is already used in {collection}.",
                        identifier=identifier,
                    )
                    continue
                table[identifier] = row
            self.index[collection] = table

    def check_taxonomy(self) -> None:
        taxa = self.index.get("taxa", {})
        for position, taxon in enumerate(self.rows("taxa")):
            if not isinstance(taxon, Mapping):
                continue
            path = f"/taxa/{position}"
            parent = taxon.get("primary_parent_id")
            self.require_ref("taxa", parent, f"{path}/primary_parent_id", "Parent taxon")
            supplemental = taxon.get("supplemental_broader_ids") or []
            for slot, broader in enumerate(supplemental):
                self.require_ref(
                    "taxa", broader, f"{path}/supplemental_broader_ids/{slot}", "Broader taxon"
                )
                if broader == parent:
                    self.add(
                        D.TAXON_MEMBERSHIP_DUPLICATE,
                        f"{path}/supplemental_broader_ids/{slot}",
                        f"{broader!r} is already this taxon's primary parent.",
                        taxon_id=taxon.get("id"),
                    )

        # Cycle detection over the primary browse path only. Supplemental links
        # are a lattice by design and are not required to be acyclic.
        for identifier in sorted(taxa):
            seen = [identifier]
            cursor = taxa[identifier].get("primary_parent_id")
            while isinstance(cursor, str) and cursor in taxa:
                if cursor in seen:
                    self.add(
                        D.TAXON_CYCLE,
                        f"/taxa/{identifier}",
                        "Primary parent chain forms a cycle: "
                        + " -> ".join(seen + [cursor])
                        + ".",
                        chain=seen + [cursor],
                    )
                    break
                seen.append(cursor)
                cursor = taxa[cursor].get("primary_parent_id")

    def check_property_registry(self) -> None:
        for position, prop in enumerate(self.rows("properties")):
            if not isinstance(prop, Mapping):
                continue
            path = f"/properties/{position}"
            unit = prop.get("canonical_unit")
            if not is_coherent_si_unit(unit):
                self.add(
                    D.UNIT_INCOHERENT,
                    f"{path}/canonical_unit",
                    f"{unit!r} is not a coherent SI unit; canonical values must not "
                    "carry a decimal prefix.",
                    unit=unit,
                )
            group_id = prop.get("group_id")
            self.require_ref("property_groups", group_id, f"{path}/group_id", "Property group")

        for position, group in enumerate(self.rows("property_groups")):
            if not isinstance(group, Mapping):
                continue
            path = f"/property_groups/{position}"
            for slot, member in enumerate(group.get("member_property_ids") or []):
                if not self.known("properties", member):
                    self.add(
                        D.PROPERTY_GROUP_MEMBER_UNKNOWN,
                        f"{path}/member_property_ids/{slot}",
                        f"Group member {member!r} is not a registered property.",
                        member=member,
                    )

    def check_condition_registry(self) -> None:
        for position, condition in enumerate(self.rows("conditions")):
            if not isinstance(condition, Mapping):
                continue
            path = f"/conditions/{position}"
            value_type = condition.get("value_type")
            if condition.get("navigable") and value_type != "enum":
                self.add(
                    D.NAVIGABLE_CONDITION_NOT_ENUM,
                    f"{path}/navigable",
                    f"Condition {condition.get('id')!r} is marked navigable but has "
                    f"value type {value_type!r}. Only enumerated conditions may "
                    "generate a drill-down level; continuous quantities stay filters.",
                    condition_id=condition.get("id"),
                    value_type=value_type,
                )
            if value_type == "enum" and not condition.get("allowed_values"):
                self.add(
                    D.CONDITION_VALUE_INVALID,
                    f"{path}/allowed_values",
                    f"Enumerated condition {condition.get('id')!r} must register its "
                    "allowed values.",
                    condition_id=condition.get("id"),
                )
            unit = condition.get("canonical_unit")
            if unit is not None and not is_coherent_si_unit(unit):
                self.add(
                    D.UNIT_INCOHERENT,
                    f"{path}/canonical_unit",
                    f"{unit!r} is not a coherent SI unit.",
                    unit=unit,
                )

    def check_materials(self) -> None:
        for position, material in enumerate(self.rows("materials")):
            if not isinstance(material, Mapping):
                continue
            path = f"/materials/{position}"
            primary = material.get("primary_taxon_id")
            if primary is None:
                self.add(
                    D.TAXON_PRIMARY_MISSING,
                    f"{path}/primary_taxon_id",
                    f"Material {material.get('id')!r} has no primary browse taxon.",
                    material_id=material.get("id"),
                )
            else:
                self.require_ref("taxa", primary, f"{path}/primary_taxon_id", "Primary taxon")
            for slot, supplemental in enumerate(material.get("supplemental_taxon_ids") or []):
                self.require_ref(
                    "taxa",
                    supplemental,
                    f"{path}/supplemental_taxon_ids/{slot}",
                    "Supplemental taxon",
                )
                if supplemental == primary:
                    self.add(
                        D.TAXON_MEMBERSHIP_DUPLICATE,
                        f"{path}/supplemental_taxon_ids/{slot}",
                        f"{supplemental!r} is already this material's primary taxon; "
                        "a duplicated membership would double-count it.",
                        material_id=material.get("id"),
                    )

    def check_states(self) -> None:
        conditions = self.index.get("conditions", {})
        for position, state in enumerate(self.rows("states")):
            if not isinstance(state, Mapping):
                continue
            path = f"/states/{position}"
            self.require_ref(
                "materials", state.get("material_id"), f"{path}/material_id", "Material"
            )
            attributes = state.get("fixed_attributes")
            if not isinstance(attributes, Mapping):
                continue
            for key in sorted(attributes):
                key_path = f"{path}/fixed_attributes/{key}"
                registered = conditions.get(key)
                if registered is None:
                    self.add(
                        D.CONDITION_UNKNOWN,
                        key_path,
                        f"{key!r} is not a registered condition.",
                        key=key,
                    )
                    continue
                if registered.get("retired"):
                    self.add(
                        D.LEGACY_STATE_KEY,
                        key_path,
                        f"{key!r} is retired: "
                        f"{registered.get('retired_reason', 'it must be mapped to a precise key')}.",
                        key=key,
                    )
                    continue
                if registered.get("allowed_placement") != "state_fixed_attribute":
                    self.add(
                        D.ATTRIBUTE_PLACEMENT,
                        key_path,
                        f"{key!r} is observation context and cannot be fixed on a "
                        "named state.",
                        key=key,
                    )
                    continue
                self.check_condition_value(registered, attributes[key], key_path)

    def check_observations(self) -> None:
        conditions = self.index.get("conditions", {})
        properties = self.index.get("properties", {})
        states = self.index.get("states", {})
        taxa = self.index.get("taxa", {})
        observations = self.index.get("observations", {})

        for position, observation in enumerate(self.rows("observations")):
            if not isinstance(observation, Mapping):
                continue
            path = f"/observations/{position}"
            material_id = observation.get("material_id")

            if material_id in taxa:
                self.add(
                    D.OBSERVATION_TAXON_ATTACHED,
                    f"{path}/material_id",
                    f"{material_id!r} is a taxon. Categories never own measurements; "
                    "their ranges are calculated from concrete members.",
                    taxon_id=material_id,
                )
            else:
                self.require_ref("materials", material_id, f"{path}/material_id", "Material")

            state_id = observation.get("state_id")
            if state_id is not None:
                if self.require_ref("states", state_id, f"{path}/state_id", "State"):
                    owner = states[state_id].get("material_id")
                    if owner != material_id:
                        self.add(
                            D.STATE_MATERIAL_MISMATCH,
                            f"{path}/state_id",
                            f"State {state_id!r} belongs to material {owner!r}, but this "
                            f"observation names {material_id!r}.",
                            state_material_id=owner,
                            observation_material_id=material_id,
                        )

            property_id = observation.get("property_id")
            if property_id is not None and not self.known("properties", property_id):
                self.add(
                    D.PROPERTY_UNKNOWN,
                    f"{path}/property_id",
                    f"{property_id!r} is not a registered property.",
                    property_id=property_id,
                )

            basis = observation.get("basis")
            if basis is not None and not self.known("bases", basis):
                self.add(
                    D.BASIS_UNKNOWN,
                    f"{path}/basis",
                    f"{basis!r} is not a registered reporting basis.",
                    basis=basis,
                )

            source_id = observation.get("source_id")
            if source_id is not None and not self.known("sources", source_id):
                self.add(
                    D.SOURCE_UNKNOWN,
                    f"{path}/source_id",
                    f"{source_id!r} is not a registered source.",
                    source_id=source_id,
                )

            self.check_observation_conditions(observation, conditions, path)
            self.check_result(
                observation, properties.get(property_id) if property_id else None, path
            )
            self.check_locator(observation, path)

            for slot, superseded in enumerate(
                observation.get("supersedes_observation_ids") or []
            ):
                slot_path = f"{path}/supersedes_observation_ids/{slot}"
                if superseded == observation.get("id"):
                    self.add(
                        D.SUPERSEDES_SELF,
                        slot_path,
                        "An observation cannot supersede itself.",
                        observation_id=superseded,
                    )
                elif superseded not in observations:
                    self.add(
                        D.SUPERSEDES_UNKNOWN,
                        slot_path,
                        f"Superseded observation {superseded!r} is not present.",
                        observation_id=superseded,
                    )

    def check_observation_conditions(
        self,
        observation: Mapping[str, Any],
        conditions: Mapping[str, Mapping[str, Any]],
        path: str,
    ) -> None:
        values = observation.get("conditions")
        if not isinstance(values, Mapping):
            return
        for key in sorted(values):
            key_path = f"{path}/conditions/{key}"
            registered = conditions.get(key)
            if registered is None:
                self.add(
                    D.CONDITION_UNKNOWN,
                    key_path,
                    f"{key!r} is not a registered condition.",
                    key=key,
                )
                continue
            if registered.get("retired"):
                self.add(
                    D.LEGACY_STATE_KEY,
                    key_path,
                    f"{key!r} is retired: "
                    f"{registered.get('retired_reason', 'it must be mapped to a precise key')}.",
                    key=key,
                )
                continue
            if registered.get("allowed_placement") != "observation_condition":
                self.add(
                    D.CONDITION_PLACEMENT,
                    key_path,
                    f"{key!r} is fixed once on a named state and must not be repeated "
                    "or contradicted by an observation.",
                    key=key,
                )
                continue
            self.check_condition_value(registered, values[key], key_path)

    def check_condition_value(
        self, registered: Mapping[str, Any], value: Any, path: str
    ) -> None:
        value_type = registered.get("value_type")
        key = registered.get("id")
        if value_type == "enum":
            allowed = registered.get("allowed_values") or []
            if not isinstance(value, str) or value not in allowed:
                self.add(
                    D.CONDITION_VALUE_INVALID,
                    path,
                    f"{value!r} is not a registered value for {key!r}.",
                    key=key,
                    value=value,
                )
        elif value_type == "number":
            if not _is_finite_number(value):
                self.add(
                    D.CONDITION_VALUE_INVALID,
                    path,
                    f"{key!r} requires a finite number, got {value!r}.",
                    key=key,
                    value=value,
                )
        elif value_type == "number_interval":
            if not isinstance(value, Mapping):
                self.add(
                    D.CONDITION_VALUE_INVALID,
                    path,
                    f"{key!r} requires an interval object, got {value!r}.",
                    key=key,
                    value=value,
                )
                return
            low, high = value.get("minimum"), value.get("maximum")
            if not _is_finite_number(low) or not _is_finite_number(high):
                self.add(
                    D.CONDITION_VALUE_INVALID,
                    path,
                    f"{key!r} requires finite interval bounds.",
                    key=key,
                    value=value,
                )
            elif low > high:
                self.add(
                    D.RESULT_INTERVAL_ORDER,
                    path,
                    f"{key!r} interval minimum {low} exceeds maximum {high}.",
                    key=key,
                )

    def check_result(
        self,
        observation: Mapping[str, Any],
        prop: Mapping[str, Any] | None,
        path: str,
    ) -> None:
        result = observation.get("result")
        if not isinstance(result, Mapping):
            return
        kind = result.get("kind")
        result_path = f"{path}/result"

        if kind not in _NUMERIC_RESULT_KINDS | _ASSERTION_RESULT_KINDS:
            self.add(
                D.RESULT_KIND_INVALID,
                f"{result_path}/kind",
                f"{kind!r} is not a supported result kind.",
                kind=kind,
            )
            return

        if kind in _ASSERTION_RESULT_KINDS:
            return

        reported = result.get("reported")
        canonical = result.get("canonical")

        if isinstance(reported, Mapping):
            if reported.get("significant_figures") is None:
                self.add(
                    D.RESULT_PRECISION_REQUIRED,
                    f"{result_path}/reported/significant_figures",
                    "A reported numeric result must state the precision the source "
                    "asserted, so a converted display value cannot invent digits.",
                )
            for field in ("value", "minimum", "maximum"):
                if field in reported and not _is_finite_number(reported[field]):
                    self.add(
                        D.RESULT_VALUE_NOT_FINITE,
                        f"{result_path}/reported/{field}",
                        f"Reported {field} must be a finite number.",
                    )

        if isinstance(canonical, Mapping):
            for field in ("value", "minimum", "maximum"):
                if field in canonical and not _is_finite_number(canonical[field]):
                    self.add(
                        D.RESULT_VALUE_NOT_FINITE,
                        f"{result_path}/canonical/{field}",
                        f"Canonical {field} must be a finite number.",
                    )
            unit = canonical.get("unit")
            if not is_coherent_si_unit(unit):
                self.add(
                    D.UNIT_INCOHERENT,
                    f"{result_path}/canonical/unit",
                    f"{unit!r} is not a coherent SI unit.",
                    unit=unit,
                )
            elif prop is not None and unit != prop.get("canonical_unit"):
                self.add(
                    D.UNIT_MISMATCH,
                    f"{result_path}/canonical/unit",
                    f"Expected the property's canonical unit "
                    f"{prop.get('canonical_unit')!r}, got {unit!r}.",
                    expected=prop.get("canonical_unit"),
                    actual=unit,
                )

        if kind == "interval":
            for container, label in ((reported, "reported"), (canonical, "canonical")):
                if not isinstance(container, Mapping):
                    continue
                low, high = container.get("minimum"), container.get("maximum")
                if _is_finite_number(low) and _is_finite_number(high) and low > high:
                    self.add(
                        D.RESULT_INTERVAL_ORDER,
                        f"{result_path}/{label}",
                        f"A reported interval's minimum ({low}) cannot exceed its "
                        f"maximum ({high}).",
                        minimum=low,
                        maximum=high,
                    )

        uncertainty = observation.get("uncertainty")
        if isinstance(uncertainty, Mapping):
            reported_uncertainty = uncertainty.get("reported")
            if isinstance(reported_uncertainty, Mapping) and (
                "minimum" in reported_uncertainty or "maximum" in reported_uncertainty
            ):
                self.add(
                    D.UNCERTAINTY_AS_INTERVAL,
                    f"{path}/uncertainty/reported",
                    "Uncertainty is a magnitude, not a range. A source-reported "
                    "interval belongs in a result of kind 'interval'.",
                )
            for container, label in (
                (reported_uncertainty, "reported"),
                (uncertainty.get("canonical"), "canonical"),
            ):
                if isinstance(container, Mapping):
                    magnitude = container.get("value")
                    if _is_finite_number(magnitude) and magnitude < 0:
                        self.add(
                            D.RESULT_VALUE_NOT_FINITE,
                            f"{path}/uncertainty/{label}/value",
                            "Uncertainty magnitude cannot be negative.",
                        )

    def check_locator(self, observation: Mapping[str, Any], path: str) -> None:
        result = observation.get("result")
        kind = result.get("kind") if isinstance(result, Mapping) else None
        if kind in _ASSERTION_RESULT_KINDS:
            return
        locator = observation.get("source_locator")
        if not isinstance(locator, Mapping) or not str(locator.get("label", "")).strip():
            self.add(
                D.SOURCE_LOCATOR_REQUIRED,
                f"{path}/source_locator",
                "A source document without a precise location is not sufficient "
                "provenance.",
            )

    def check_alias_collisions(self) -> None:
        """Report normalized search terms that resolve to more than one subject.

        This is a warning, not an error: near-collisions are deliberate fixtures
        for the resolver. The requirement is only that the diagnostic be
        deterministic so a reviewer sees the same list every run.
        """
        seen: dict[str, list[str]] = {}
        for collection, label_field in (
            ("materials", "name"),
            ("states", "name"),
            ("properties", "name"),
            ("property_groups", "name"),
            ("taxa", "name"),
        ):
            for row in self.rows(collection):
                if not isinstance(row, Mapping):
                    continue
                subject = f"{collection}:{row.get('id')}"
                terms = [row.get(label_field)] + list(row.get("aliases") or [])
                for term in terms:
                    if not isinstance(term, str):
                        continue
                    key = _normalize_term(term)
                    if not key:
                        continue
                    bucket = seen.setdefault(key, [])
                    if subject not in bucket:
                        bucket.append(subject)

        for key in sorted(seen):
            subjects = seen[key]
            if len(subjects) > 1:
                self.add(
                    D.ALIAS_COLLISION,
                    f"/aliases/{key}",
                    f"Search term {key!r} resolves to {len(subjects)} subjects: "
                    + ", ".join(sorted(subjects))
                    + ".",
                    severity=D.WARNING,
                    subjects=sorted(subjects),
                )


def _normalize_term(term: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_semantics(dataset: Mapping[str, Any]) -> list[Diagnostic]:
    return _Semantic(dataset).run()


def validate(dataset: Mapping[str, Any], *, structural: bool = True) -> list[Diagnostic]:
    """Run structural then semantic validation, returning sorted diagnostics."""
    found: list[Diagnostic] = []
    if structural:
        found.extend(validate_structure(dataset))
    found.extend(validate_semantics(dataset))
    return sorted(found, key=D.sort_key)


def errors(found: Iterable[Diagnostic]) -> list[Diagnostic]:
    return [item for item in found if item.severity == D.ERROR]
