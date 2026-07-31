#!/usr/bin/env python3
"""Validate the curated materials database and build the static site.

The builder intentionally uses only the Python 3 standard library.  Run it from
any directory:

    python3 scripts/build_site.py

The repository root defaults to the parent of ``scripts/``.  Use ``--check`` to
perform every load and validation step without writing generated files.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import html
import json
import math
import os
import re
import sys
import tempfile
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse


BUILD_VERSION = 1
DEFAULT_SCHEMA_VERSION = "0.1.0"
SUPPORTED_SCHEMA_VERSIONS = {DEFAULT_SCHEMA_VERSION}
BASIS_VALUES = {
    "typical",
    "minimum",
    "A-basis",
    "B-basis",
    "S-basis",
    "computed",
    "estimated",
}
RECORD_TYPES = {"family", "grade", "variant"}
PARENT_TYPES = {"family": "family", "grade": "family", "variant": "grade"}
SOURCE_TYPES = {
    "government_handbook",
    "manufacturer_datasheet",
    "prototype_seed",
}

MATERIAL_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROPERTY_ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
CONDITION_KEY_RE = re.compile(r"^[a-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")
TEMPLATE_TOKEN_RE = re.compile(r"{{\s*([A-Z][A-Z0-9_]*)\s*}}")

# Coherent SI base/derived symbols. Prefixes are deliberately absent: the
# canonical store uses Pa, m and kg/m^3 rather than MPa, mm and g/cm^3.
SI_ATOMS = {
    "m",
    "kg",
    "s",
    "A",
    "K",
    "mol",
    "cd",
    "rad",
    "sr",
    "Hz",
    "N",
    "Pa",
    "J",
    "W",
    "C",
    "V",
    "F",
    "ohm",
    "Ω",
    "S",
    "Wb",
    "T",
    "H",
    "lm",
    "lx",
    "Bq",
    "Gy",
    "Sv",
    "kat",
}
SI_ATOM_PATTERN = "(?:" + "|".join(
    sorted((re.escape(atom) for atom in SI_ATOMS), key=len, reverse=True)
) + ")"
SI_POWER_PATTERN = r"(?:\^-?(?:\d+(?:\.\d+)?|\.\d+))?"
SI_FACTOR_PATTERN = SI_ATOM_PATTERN + SI_POWER_PATTERN
SI_PRODUCT_PATTERN = SI_FACTOR_PATTERN + r"(?:[*·]" + SI_FACTOR_PATTERN + r")*"
SI_EXPRESSION_RE = re.compile(
    r"^(?:1|" + SI_PRODUCT_PATTERN + r")(?:/(?:"
    + SI_PRODUCT_PATTERN
    + r"|\("
    + SI_PRODUCT_PATTERN
    + r"\)))?$"
)
SUPPORTED_CONDITION_TYPES = {
    "number",
    "numeric",
    "float",
    "range",
    "number_range",
    "numeric_range",
    "range_number",
    "string",
    "text",
    "enum",
    "choice",
    "boolean",
    "bool",
}

HEADLINE_PROPERTY_ORDER = (
    "density",
    "youngs_modulus",
    "yield_strength",
    "tensile_strength",
    "thermal_conductivity",
    "elongation_at_break",
    "max_service_temperature",
)

BUILTIN_STYLE = """\
:root{color-scheme:light dark;--bg:#f6f7f4;--panel:#fff;--ink:#17201b;--muted:#617067;--line:#d8ded9;--accent:#176b4b}
@media(prefers-color-scheme:dark){:root{--bg:#101512;--panel:#171e1a;--ink:#edf4ef;--muted:#9eaea4;--line:#344039;--accent:#72d8aa}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}
main{width:min(1120px,calc(100% - 2rem));margin:0 auto;padding:2.5rem 0 5rem}a{color:var(--accent)}
nav,.eyebrow{color:var(--muted);font-size:.875rem}h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.05;margin:.45rem 0 1rem}
h2{margin-top:2.25rem}.lede{max-width:70ch;font-size:1.1rem;color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;margin:1.25rem 0}.badge{padding:.18rem .5rem;border:1px solid var(--line);border-radius:999px}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:.65rem;background:var(--panel)}
table{width:100%;border-collapse:collapse;min-width:760px}th,td{padding:.75rem;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
th{font-size:.78rem;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}tr:last-child td{border-bottom:0}
.value{font-variant-numeric:tabular-nums;white-space:nowrap}.muted{color:var(--muted)}code{font-size:.88em}
.empty{padding:1.25rem;color:var(--muted)}.search{width:100%;padding:.9rem 1rem;font:inherit;border:1px solid var(--line);border-radius:.5rem;background:var(--panel);color:var(--ink)}
.results{list-style:none;padding:0}.results li{padding:.75rem 0;border-bottom:1px solid var(--line)}
"""


class BuildError(Exception):
    """A load, configuration, or generation failure."""


class ValidationError(BuildError):
    """One or more input records violate the build contract."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__(
            "validation failed with "
            f"{len(self.errors)} error{'s' if len(self.errors) != 1 else ''}"
        )


@dataclass(frozen=True)
class Collection:
    items: list[dict[str, Any]]
    schema_version: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Database:
    schema_version: str
    materials: list[dict[str, Any]]
    properties: list[dict[str, Any]]
    conditions: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    property_by_id: dict[str, dict[str, Any]]
    condition_by_key: dict[str, dict[str, Any]]
    source_by_id: dict[str, dict[str, Any]]
    material_by_id: dict[str, dict[str, Any]]
    thesaurus: dict[str, str | list[str]]


def _json_load(path: Path) -> Any:
    if not path.is_file():
        raise BuildError(f"required input is missing: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise BuildError(
            f"invalid JSON in {path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc


def _extract_collection(
    path: Path,
    collection_names: Sequence[str],
    map_id_field: str,
) -> Collection:
    """Accept a bare array, named array/map, single record, or id-keyed map."""

    document = _json_load(path)
    schema_version: str | None = None
    metadata: dict[str, Any] = {}
    value: Any = document

    if isinstance(document, dict):
        raw_version = document.get("schema_version")
        if raw_version is not None:
            if not isinstance(raw_version, str) or not raw_version.strip():
                raise BuildError(f"{path}: schema_version must be a non-empty string")
            schema_version = raw_version
        for key in ("thesaurus", "featured"):
            if key in document:
                metadata[key] = document[key]
        for name in collection_names:
            if name in document:
                value = document[name]
                break
        else:
            if map_id_field in document or (
                map_id_field == "key" and "id" in document
            ):
                value = [document]
            else:
                ignored = {"schema_version", "$schema", "thesaurus", "featured"}
                value = {key: val for key, val in document.items() if key not in ignored}

    if isinstance(value, list):
        items: list[dict[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise BuildError(
                    f"{path}: item {index} must be an object, got "
                    f"{type(item).__name__}"
                )
            items.append(dict(item))
        return Collection(items, schema_version, metadata)

    if isinstance(value, dict):
        items = []
        for key, item in value.items():
            if not isinstance(item, dict):
                raise BuildError(
                    f"{path}: map entry {key!r} must be an object, got "
                    f"{type(item).__name__}"
                )
            copied = dict(item)
            existing = copied.get(map_id_field)
            if existing is not None and existing != key:
                raise BuildError(
                    f"{path}: map key {key!r} conflicts with "
                    f"{map_id_field} {existing!r}"
                )
            copied.setdefault(map_id_field, key)
            items.append(copied)
        return Collection(items, schema_version, metadata)

    raise BuildError(
        f"{path}: expected an array, an id-keyed object, or a named collection"
    )


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_coherent_si_unit(unit: Any) -> bool:
    if unit == "1":
        return True
    if not isinstance(unit, str) or not SI_EXPRESSION_RE.fullmatch(unit):
        return False
    exponents = re.findall(r"\^(-?(?:\d+(?:\.\d+)?|\.\d+))", unit)
    return all(0 < abs(float(exponent)) <= 12 for exponent in exponents)


def _require_fields(
    obj: Mapping[str, Any],
    fields: Iterable[str],
    path: str,
    errors: list[str],
) -> None:
    for field in fields:
        if field not in obj:
            errors.append(f"{path}.{field}: required field is missing")


def _validate_string_list(
    value: Any,
    path: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
) -> None:
    if not isinstance(value, list):
        errors.append(f"{path}: must be an array of strings")
        return
    if not allow_empty and not value:
        errors.append(f"{path}: must not be empty")
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}[{index}]: must be a non-empty string")
        elif item in seen:
            errors.append(f"{path}[{index}]: duplicate value {item!r}")
        else:
            seen.add(item)


def _condition_key(condition: Mapping[str, Any]) -> Any:
    return condition.get("key", condition.get("id"))


def _condition_type(condition: Mapping[str, Any]) -> str | None:
    raw = condition.get("value_type", condition.get("type"))
    return raw.lower().replace("-", "_") if isinstance(raw, str) else None


def _validate_condition_value(
    value: Any,
    spec: Mapping[str, Any],
    path: str,
    errors: list[str],
) -> None:
    value_type = _condition_type(spec)
    allowed = spec.get("allowed_values", spec.get("values"))

    if value_type in {"number", "numeric", "float"}:
        if not _is_number(value):
            errors.append(f"{path}: must be a finite number")
    elif value_type in {
        "range",
        "number_range",
        "numeric_range",
        "range_number",
    }:
        if not isinstance(value, list) or len(value) != 2:
            errors.append(f"{path}: must be a two-item [min, max] array")
        else:
            low, high = value
            if low is None and high is None:
                errors.append(f"{path}: range must have at least one bound")
            for index, bound in enumerate(value):
                if bound is not None and not _is_number(bound):
                    errors.append(
                        f"{path}[{index}]: range bound must be null or a finite number"
                    )
            if _is_number(low) and _is_number(high) and low > high:
                errors.append(f"{path}: range minimum must not exceed maximum")
    elif value_type in {"string", "text"}:
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}: must be a non-empty string")
    elif value_type in {"enum", "choice"}:
        if not isinstance(value, str):
            errors.append(f"{path}: must be a string enum value")
    elif value_type in {"boolean", "bool"}:
        if not isinstance(value, bool):
            errors.append(f"{path}: must be a boolean")
    elif value_type is not None:
        errors.append(f"{path}: registry has unsupported value_type {value_type!r}")
    elif not (
        isinstance(value, (str, bool))
        or value is None
        or _is_number(value)
        or (
            isinstance(value, list)
            and all(item is None or _is_number(item) for item in value)
        )
    ):
        errors.append(f"{path}: value is not a supported condition scalar or range")

    if allowed is not None:
        if not isinstance(allowed, list) or not allowed:
            errors.append(
                f"registry condition {_condition_key(spec)!r}.allowed_values: "
                "must be a non-empty array"
            )
        elif value not in allowed:
            errors.append(
                f"{path}: {value!r} is not one of the registered values "
                f"{allowed!r}"
            )


def _validate_uncertainty(
    uncertainty: Any,
    value: Any,
    path: str,
    errors: list[str],
) -> None:
    if uncertainty is None:
        return
    if not isinstance(uncertainty, dict):
        errors.append(f"{path}: must be null or an object")
        return
    kind = uncertainty.get("kind")
    if kind == "range":
        _require_fields(uncertainty, ("min", "max"), path, errors)
        low = uncertainty.get("min")
        high = uncertainty.get("max")
        if not _is_number(low):
            errors.append(f"{path}.min: must be a finite number")
        if not _is_number(high):
            errors.append(f"{path}.max: must be a finite number")
        if _is_number(low) and _is_number(high):
            if low > high:
                errors.append(f"{path}: range minimum must not exceed maximum")
            if _is_number(value) and not low <= value <= high:
                errors.append(f"{path}: observation value must fall within the range")
    elif kind == "stddev":
        _require_fields(uncertainty, ("sd", "n"), path, errors)
        if not _is_number(uncertainty.get("sd")) or uncertainty.get("sd", 0) <= 0:
            errors.append(f"{path}.sd: must be a positive finite number")
        sample_count = uncertainty.get("n")
        if (
            not isinstance(sample_count, int)
            or isinstance(sample_count, bool)
            or sample_count < 2
        ):
            errors.append(f"{path}.n: must be an integer of at least 2")
    elif kind == "implied":
        _require_fields(uncertainty, ("sigfigs",), path, errors)
        sigfigs = uncertainty.get("sigfigs")
        if (
            not isinstance(sigfigs, int)
            or isinstance(sigfigs, bool)
            or not 1 <= sigfigs <= 15
        ):
            errors.append(f"{path}.sigfigs: must be an integer from 1 to 15")
    else:
        errors.append(
            f"{path}.kind: must be one of 'range', 'stddev', or 'implied'"
        )


def _validate_date(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        errors.append(f"{path}: must use YYYY, YYYY-MM, or YYYY-MM-DD")
        return
    if len(value) in {7, 10}:
        try:
            _datetime.date.fromisoformat(value if len(value) == 10 else value + "-01")
        except ValueError:
            errors.append(f"{path}: is not a real calendar date")


def _validate_registry(
    properties: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    errors: list[str],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    property_by_id: dict[str, dict[str, Any]] = {}
    for index, prop in enumerate(properties):
        path = f"registry/properties.json.properties[{index}]"
        _require_fields(prop, ("id", "name", "canonical_unit"), path, errors)
        prop_id = prop.get("id")
        if not isinstance(prop_id, str) or not PROPERTY_ID_RE.fullmatch(prop_id):
            errors.append(f"{path}.id: must be a canonical snake_case property id")
        elif prop_id in property_by_id:
            errors.append(f"{path}.id: duplicate property id {prop_id!r}")
        else:
            property_by_id[prop_id] = prop
        if not isinstance(prop.get("name"), str) or not prop.get("name", "").strip():
            errors.append(f"{path}.name: must be a non-empty string")
        unit = prop.get("canonical_unit")
        if not _is_coherent_si_unit(unit):
            errors.append(
                f"{path}.canonical_unit: {unit!r} is not a coherent SI unit"
            )
        aliases = prop.get("aliases", [])
        _validate_string_list(aliases, f"{path}.aliases", errors)
        precision = prop.get("display_precision")
        if precision is not None and (
            not isinstance(precision, int)
            or isinstance(precision, bool)
            or not 1 <= precision <= 15
        ):
            errors.append(
                f"{path}.display_precision: must be an integer from 1 to 15"
            )
        typical_scale = prop.get("typical_scale")
        if typical_scale is not None and (
            not _is_number(typical_scale) or typical_scale <= 0
        ):
            errors.append(f"{path}.typical_scale: must be a positive finite number")
        direction = prop.get("sort_direction")
        if direction is not None and direction not in ("asc", "desc"):
            errors.append(f"{path}.sort_direction: must be 'asc' or 'desc'")

    condition_by_key: dict[str, dict[str, Any]] = {}
    for index, condition in enumerate(conditions):
        path = f"registry/conditions.json.conditions[{index}]"
        key = _condition_key(condition)
        if not isinstance(key, str) or not CONDITION_KEY_RE.fullmatch(key):
            errors.append(
                f"{path}.key: must be a canonical condition key such as "
                "'temperature_K'"
            )
        elif key in condition_by_key:
            errors.append(f"{path}.key: duplicate condition key {key!r}")
        else:
            condition_by_key[key] = condition
        value_type = _condition_type(condition)
        if value_type is None:
            errors.append(f"{path}.value_type: required field is missing")
        elif value_type not in SUPPORTED_CONDITION_TYPES:
            errors.append(
                f"{path}.value_type: unsupported condition type {value_type!r}"
            )
        unit = condition.get("canonical_unit", condition.get("unit"))
        if unit is not None and not _is_coherent_si_unit(unit):
            errors.append(f"{path}.unit: {unit!r} is not a coherent SI unit")
        allowed = condition.get("allowed_values", condition.get("values"))
        if allowed is not None and (
            not isinstance(allowed, list) or not allowed
        ):
            errors.append(f"{path}.allowed_values: must be a non-empty array")

    source_by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        path = f"curated/sources.json.sources[{index}]"
        _require_fields(source, ("id", "title"), path, errors)
        source_id = source.get("id")
        if not isinstance(source_id, str) or not MATERIAL_ID_RE.fullmatch(source_id):
            errors.append(f"{path}.id: must be a canonical kebab-case source id")
        elif source_id in source_by_id:
            errors.append(f"{path}.id: duplicate source id {source_id!r}")
        else:
            source_by_id[source_id] = source
        if not isinstance(source.get("title"), str) or not source.get(
            "title", ""
        ).strip():
            errors.append(f"{path}.title: must be a non-empty string")
        source_type = source.get("source_type")
        if source_type is not None and (
            not isinstance(source_type, str) or source_type not in SOURCE_TYPES
        ):
            errors.append(
                f"{path}.source_type: must be one of {sorted(SOURCE_TYPES)!r}"
            )
        for field in ("publication_date", "retrieved_date"):
            if source.get(field) is not None:
                _validate_date(source[field], f"{path}.{field}", errors)
        url = source.get("url")
        if url is not None:
            parsed = urlparse(url) if isinstance(url, str) else None
            if (
                parsed is None
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
            ):
                errors.append(f"{path}.url: must be an absolute HTTP(S) URL")
        locator_pattern = source.get("locator_pattern")
        if locator_pattern is not None:
            if not isinstance(locator_pattern, str):
                errors.append(f"{path}.locator_pattern: must be a regular expression")
            else:
                try:
                    re.compile(locator_pattern)
                except re.error as exc:
                    errors.append(f"{path}.locator_pattern: invalid regex: {exc}")

    return property_by_id, condition_by_key, source_by_id


def _validate_materials(
    materials: list[dict[str, Any]],
    property_by_id: Mapping[str, dict[str, Any]],
    condition_by_key: Mapping[str, dict[str, Any]],
    source_by_id: Mapping[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    material_by_id: dict[str, dict[str, Any]] = {}
    required_fields = (
        "id",
        "name",
        "record_type",
        "parent_id",
        "aliases",
        "family",
        "designations",
        "condition",
        "prominence",
        "description",
        "observations",
    )

    for index, material in enumerate(materials):
        path = f"curated/materials.json.materials[{index}]"
        _require_fields(material, required_fields, path, errors)
        material_id = material.get("id")
        if not isinstance(material_id, str) or not MATERIAL_ID_RE.fullmatch(
            material_id
        ):
            errors.append(f"{path}.id: must be a canonical kebab-case material id")
        elif material_id in material_by_id:
            errors.append(f"{path}.id: duplicate material id {material_id!r}")
        else:
            material_by_id[material_id] = material

        if not isinstance(material.get("name"), str) or not material.get(
            "name", ""
        ).strip():
            errors.append(f"{path}.name: must be a non-empty string")
        record_type = material.get("record_type")
        if not isinstance(record_type, str) or record_type not in RECORD_TYPES:
            errors.append(f"{path}.record_type: must be one of {sorted(RECORD_TYPES)!r}")
        parent_id = material.get("parent_id")
        if parent_id is not None and (
            not isinstance(parent_id, str) or not MATERIAL_ID_RE.fullmatch(parent_id)
        ):
            errors.append(f"{path}.parent_id: must be null or a material id")
        _validate_string_list(material.get("aliases"), f"{path}.aliases", errors)
        _validate_string_list(material.get("family"), f"{path}.family", errors)
        designations = material.get("designations")
        if not isinstance(designations, dict):
            errors.append(f"{path}.designations: must be an object")
        else:
            for system, designation in designations.items():
                if not isinstance(system, str) or not system.strip():
                    errors.append(
                        f"{path}.designations: designation system must be a string"
                    )
                if not (
                    isinstance(designation, str)
                    and designation.strip()
                    or isinstance(designation, list)
                    and all(
                        isinstance(item, str) and item.strip()
                        for item in designation
                    )
                    and designation
                ):
                    errors.append(
                        f"{path}.designations.{system}: must be a non-empty string "
                        "or array of strings"
                    )
        condition = material.get("condition")
        if condition is not None and (
            not isinstance(condition, str) or not condition.strip()
        ):
            errors.append(f"{path}.condition: must be null or a non-empty string")
        elif record_type in ("family", "grade") and condition is not None:
            errors.append(
                f"{path}.condition: {record_type} records must have null condition"
            )
        elif record_type == "variant" and condition is None:
            errors.append(
                f"{path}.condition: variant records require a named condition"
            )
        prominence = material.get("prominence")
        if (
            not isinstance(prominence, int)
            or isinstance(prominence, bool)
            or prominence < 0
        ):
            errors.append(f"{path}.prominence: must be a non-negative integer")
        if not isinstance(material.get("description"), str) or not material.get(
            "description", ""
        ).strip():
            errors.append(f"{path}.description: must be a non-empty string")

        observations = material.get("observations")
        if not isinstance(observations, list):
            errors.append(f"{path}.observations: must be an array")
            continue
        if record_type in ("family", "grade") and observations:
            errors.append(
                f"{path}.observations: {record_type} records must be structural; "
                "property observations belong on variant records"
            )
        for obs_index, observation in enumerate(observations):
            obs_path = f"{path}.observations[{obs_index}]"
            if not isinstance(observation, dict):
                errors.append(f"{obs_path}: must be an object")
                continue
            _require_fields(
                observation,
                (
                    "property",
                    "value",
                    "unit",
                    "uncertainty",
                    "basis",
                    "conditions",
                    "test_method",
                    "source_id",
                    "source_locator",
                ),
                obs_path,
                errors,
            )
            property_id = observation.get("property")
            prop = (
                property_by_id.get(property_id)
                if isinstance(property_id, str)
                else None
            )
            if prop is None:
                errors.append(
                    f"{obs_path}.property: unknown registered property "
                    f"{property_id!r}"
                )
            if not _is_number(observation.get("value")):
                errors.append(f"{obs_path}.value: must be a finite number")
            unit = observation.get("unit")
            if not _is_coherent_si_unit(unit):
                errors.append(f"{obs_path}.unit: {unit!r} is not a coherent SI unit")
            elif prop is not None and unit != prop.get("canonical_unit"):
                errors.append(
                    f"{obs_path}.unit: expected canonical unit "
                    f"{prop.get('canonical_unit')!r}, got {unit!r}"
                )
            basis = observation.get("basis")
            if not isinstance(basis, str) or basis not in BASIS_VALUES:
                errors.append(
                    f"{obs_path}.basis: must be one of {sorted(BASIS_VALUES)!r}"
                )
            conditions = observation.get("conditions")
            if not isinstance(conditions, dict):
                errors.append(f"{obs_path}.conditions: must be an object")
            else:
                for key, value in conditions.items():
                    spec = condition_by_key.get(key)
                    if spec is None:
                        errors.append(
                            f"{obs_path}.conditions.{key}: unknown registered "
                            "condition key"
                        )
                    else:
                        _validate_condition_value(
                            value, spec, f"{obs_path}.conditions.{key}", errors
                        )
            test_method = observation.get("test_method")
            if test_method is not None and (
                not isinstance(test_method, str) or not test_method.strip()
            ):
                errors.append(
                    f"{obs_path}.test_method: must be null or a non-empty string"
                )
            source_id = observation.get("source_id")
            source = (
                source_by_id.get(source_id) if isinstance(source_id, str) else None
            )
            if source is None:
                errors.append(
                    f"{obs_path}.source_id: unknown source id {source_id!r}"
                )
            locator = observation.get("source_locator")
            if not isinstance(locator, str) or not locator.strip():
                errors.append(f"{obs_path}.source_locator: must be a non-empty string")
            elif source is not None and isinstance(
                source.get("locator_pattern"), str
            ):
                if not re.fullmatch(source["locator_pattern"], locator):
                    errors.append(
                        f"{obs_path}.source_locator: does not match source "
                        "locator_pattern"
                    )
            _validate_uncertainty(
                observation.get("uncertainty"),
                observation.get("value"),
                f"{obs_path}.uncertainty",
                errors,
            )

    # Hierarchy checks run after ids have been collected so file order is free.
    for index, material in enumerate(materials):
        path = f"curated/materials.json.materials[{index}]"
        material_id = material.get("id")
        record_type = material.get("record_type")
        parent_id = material.get("parent_id")
        if record_type == "family" and parent_id is None:
            continue
        if isinstance(record_type, str) and record_type in PARENT_TYPES:
            if parent_id is None:
                errors.append(
                    f"{path}.parent_id: {record_type} records require a "
                    f"{PARENT_TYPES[record_type]} parent"
                )
            elif parent_id == material_id:
                errors.append(f"{path}.parent_id: a record cannot parent itself")
            else:
                parent = (
                    material_by_id.get(parent_id)
                    if isinstance(parent_id, str)
                    else None
                )
                if parent is None:
                    errors.append(
                        f"{path}.parent_id: unknown parent material {parent_id!r}"
                    )
                elif parent.get("record_type") != PARENT_TYPES[record_type]:
                    errors.append(
                        f"{path}.parent_id: {record_type} parent must be a "
                        f"{PARENT_TYPES[record_type]}, got "
                        f"{parent.get('record_type')!r}"
                    )

    # Detect cycles even if record_type errors would otherwise mask one.
    state: dict[str, int] = {}

    def visit(material_id: str, chain: list[str]) -> None:
        marker = state.get(material_id, 0)
        if marker == 2:
            return
        if marker == 1:
            try:
                start = chain.index(material_id)
            except ValueError:
                start = 0
            cycle = chain[start:] + [material_id]
            errors.append("hierarchy: cycle detected: " + " -> ".join(cycle))
            return
        state[material_id] = 1
        parent_id = material_by_id[material_id].get("parent_id")
        if isinstance(parent_id, str) and parent_id in material_by_id:
            visit(parent_id, chain + [material_id])
        state[material_id] = 2

    for material_id in material_by_id:
        visit(material_id, [])

    return material_by_id


def _normalize_alias(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value.lower()))


def _tokenize(value: str) -> set[str]:
    normalized = _normalize_alias(value)
    tokens = set(normalized.split())
    if normalized:
        tokens.add(normalized)
    stems: set[str] = set()
    for token in tokens:
        if " " in token:
            continue
        if len(token) > 6 and token.endswith("ium"):
            stems.add(token[:-3])
        if len(token) > 6 and token.endswith("ies"):
            stems.add(token[:-3] + "y")
        elif len(token) > 5 and token.endswith("es"):
            stems.add(token[:-2])
        elif len(token) > 4 and token.endswith("s"):
            stems.add(token[:-1])
    return {token for token in tokens | stems if token}


def _metadata_thesaurus(
    metadata_values: Iterable[Any], errors: list[str]
) -> dict[str, str | list[str]]:
    thesaurus: dict[str, str | list[str]] = {}
    for metadata in metadata_values:
        if metadata is None:
            continue
        if not isinstance(metadata, dict):
            errors.append("thesaurus: must be an object mapping aliases to targets")
            continue
        for raw_alias, raw_target in metadata.items():
            alias = _normalize_alias(raw_alias) if isinstance(raw_alias, str) else ""
            if not alias:
                errors.append(f"thesaurus: invalid alias {raw_alias!r}")
                continue
            if isinstance(raw_target, str) and raw_target:
                target: str | list[str] = raw_target
            elif (
                isinstance(raw_target, list)
                and raw_target
                and all(isinstance(item, str) and item for item in raw_target)
            ):
                target = list(dict.fromkeys(raw_target))
            else:
                errors.append(
                    f"thesaurus.{raw_alias}: target must be a string or string array"
                )
                continue
            thesaurus[alias] = target
    return thesaurus


def load_database(root: Path) -> Database:
    root = root.resolve()
    material_collection = _extract_collection(
        root / "curated" / "materials.json",
        ("materials", "records"),
        "id",
    )
    property_collection = _extract_collection(
        root / "registry" / "properties.json",
        ("properties",),
        "id",
    )
    condition_collection = _extract_collection(
        root / "registry" / "conditions.json",
        ("conditions",),
        "key",
    )
    source_collection = _extract_collection(
        root / "curated" / "sources.json",
        ("sources",),
        "id",
    )

    errors: list[str] = []
    versions = {
        collection.schema_version
        for collection in (
            material_collection,
            property_collection,
            condition_collection,
            source_collection,
        )
        if collection.schema_version is not None
    }
    if len(versions) > 1:
        errors.append(
            "schema_version: all versioned inputs must agree, got "
            + ", ".join(sorted(versions))
        )
    schema_version = next(iter(versions), DEFAULT_SCHEMA_VERSION)
    for version in sorted(versions):
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            errors.append(
                f"schema_version: unsupported version {version!r}; supported "
                f"versions are {sorted(SUPPORTED_SCHEMA_VERSIONS)!r}"
            )

    property_by_id, condition_by_key, source_by_id = _validate_registry(
        property_collection.items,
        condition_collection.items,
        source_collection.items,
        errors,
    )
    material_by_id = _validate_materials(
        material_collection.items,
        property_by_id,
        condition_by_key,
        source_by_id,
        errors,
    )

    thesaurus = _metadata_thesaurus(
        (
            material_collection.metadata.get("thesaurus"),
            property_collection.metadata.get("thesaurus"),
        ),
        errors,
    )

    # Registry/material aliases become a deterministic baseline thesaurus.
    generated_aliases: defaultdict[str, list[str]] = defaultdict(list)
    for material in material_collection.items:
        material_id = material.get("id")
        if not isinstance(material_id, str):
            continue
        aliases = material.get("aliases")
        for alias in aliases if isinstance(aliases, list) else []:
            if isinstance(alias, str):
                normalized = _normalize_alias(alias)
                if normalized and material_id not in generated_aliases[normalized]:
                    generated_aliases[normalized].append(material_id)
    for prop in property_collection.items:
        prop_id = prop.get("id")
        if not isinstance(prop_id, str):
            continue
        aliases = prop.get("aliases")
        for alias in aliases if isinstance(aliases, list) else []:
            if isinstance(alias, str):
                normalized = _normalize_alias(alias)
                if normalized and prop_id not in generated_aliases[normalized]:
                    generated_aliases[normalized].append(prop_id)
    for alias, targets in generated_aliases.items():
        generated: str | list[str] = targets[0] if len(targets) == 1 else targets
        if alias not in thesaurus:
            thesaurus[alias] = generated
        else:
            explicit = thesaurus[alias]
            explicit_targets = [explicit] if isinstance(explicit, str) else explicit
            merged = list(dict.fromkeys(explicit_targets + targets))
            thesaurus[alias] = merged[0] if len(merged) == 1 else merged

    valid_targets = set(material_by_id) | set(property_by_id)
    for alias, target in thesaurus.items():
        for item in [target] if isinstance(target, str) else target:
            if item not in valid_targets:
                errors.append(
                    f"thesaurus.{alias}: target {item!r} is not a material or property id"
                )

    if errors:
        raise ValidationError(errors)

    return Database(
        schema_version=schema_version,
        materials=material_collection.items,
        properties=property_collection.items,
        conditions=condition_collection.items,
        sources=source_collection.items,
        property_by_id=property_by_id,
        condition_by_key=condition_by_key,
        source_by_id=source_by_id,
        material_by_id=material_by_id,
        thesaurus=dict(sorted(thesaurus.items())),
    )


def _property_slug(property_id: str) -> str:
    return property_id.replace("_", "-")


def _observation_rank(observation: Mapping[str, Any]) -> tuple[Any, ...]:
    basis_order = {
        "typical": 0,
        "minimum": 1,
        "A-basis": 2,
        "B-basis": 3,
        "S-basis": 4,
        "computed": 5,
        "estimated": 6,
    }
    conditions = observation.get("conditions")
    conditions = conditions if isinstance(conditions, dict) else {}
    temperature = conditions.get("temperature_K")
    temperature_distance = (
        abs(float(temperature) - 293.15) if _is_number(temperature) else 10_000.0
    )
    return (
        basis_order.get(observation.get("basis"), 99),
        temperature_distance,
        len(conditions),
        str(observation.get("source_id", "")),
        str(observation.get("source_locator", "")),
    )


def _representative_observations(
    database: Database,
) -> dict[str, list[tuple[dict[str, Any], dict[str, Any]]]]:
    by_property: defaultdict[
        str, list[tuple[dict[str, Any], dict[str, Any]]]
    ] = defaultdict(list)
    for material in database.materials:
        grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for observation in material["observations"]:
            grouped[observation["property"]].append(observation)
        for property_id, observations in grouped.items():
            selected = min(observations, key=_observation_rank)
            by_property[property_id].append((material, selected))

    for property_id, entries in by_property.items():
        prop = database.property_by_id[property_id]
        reverse = prop.get("sort_direction", "desc") != "asc"
        entries.sort(
            key=lambda entry: (
                float(entry[1]["value"]),
                entry[0]["name"].casefold(),
                entry[0]["id"],
            ),
            reverse=reverse,
        )
    return dict(by_property)


def _descendant_envelopes(
    database: Database,
) -> dict[str, list[dict[str, Any]]]:
    """Derive non-canonical family/grade ranges from descendant variants.

    Curated observations remain variant-only.  These envelopes are explicitly
    build products for browsing and never flow back into the source records.
    """

    children: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for material in database.materials:
        if material["parent_id"]:
            children[material["parent_id"]].append(material)

    descendant_cache: dict[str, list[dict[str, Any]]] = {}

    def descendant_variants(material_id: str) -> list[dict[str, Any]]:
        if material_id in descendant_cache:
            return descendant_cache[material_id]
        variants: list[dict[str, Any]] = []
        for child in children.get(material_id, []):
            if child["record_type"] == "variant":
                variants.append(child)
            else:
                variants.extend(descendant_variants(child["id"]))
        descendant_cache[material_id] = variants
        return variants

    result: dict[str, list[dict[str, Any]]] = {}
    for material in database.materials:
        if material["record_type"] == "variant":
            continue
        grouped: defaultdict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(
            list
        )
        for variant in descendant_variants(material["id"]):
            for observation in variant["observations"]:
                grouped[observation["property"]].append((variant["id"], observation))

        envelopes: list[dict[str, Any]] = []
        for property_id, entries in grouped.items():
            values: list[float] = []
            for _, observation in entries:
                values.append(observation["value"])
                uncertainty = observation.get("uncertainty")
                if isinstance(uncertainty, dict) and uncertainty.get("kind") == "range":
                    values.extend((uncertainty["min"], uncertainty["max"]))
            prop = database.property_by_id[property_id]
            envelopes.append(
                {
                    "property": property_id,
                    "min": min(values),
                    "max": max(values),
                    "unit": prop["canonical_unit"],
                    "variant_count": len({variant_id for variant_id, _ in entries}),
                    "observation_count": len(entries),
                }
            )
        envelopes.sort(
            key=lambda item: database.property_by_id[item["property"]][
                "name"
            ].casefold()
        )
        result[material["id"]] = envelopes
    return result


def _headline_observations(
    material: Mapping[str, Any],
    database: Database,
    envelopes: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    if material["record_type"] != "variant":
        by_id = {
            envelope["property"]: envelope
            for envelope in envelopes.get(material["id"], [])
        }
        explicitly_headline = [
            prop["id"] for prop in database.properties if prop.get("headline") is True
        ]
        order = list(explicitly_headline)
        order.extend(item for item in HEADLINE_PROPERTY_ORDER if item not in order)
        order.extend(
            prop["id"] for prop in database.properties if prop["id"] not in order
        )
        headline: list[dict[str, Any]] = []
        for property_id in order:
            envelope = by_id.get(property_id)
            if envelope is None:
                continue
            headline.append(
                {
                    "property": property_id,
                    "value": {
                        "min": envelope["min"],
                        "max": envelope["max"],
                    },
                    "unit": envelope["unit"],
                    "basis": "descendant-envelope",
                }
            )
            if len(headline) == 4:
                break
        return headline

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in material["observations"]:
        grouped[observation["property"]].append(observation)
    explicitly_headline = [
        prop["id"] for prop in database.properties if prop.get("headline") is True
    ]
    order = list(explicitly_headline)
    order.extend(item for item in HEADLINE_PROPERTY_ORDER if item not in order)
    order.extend(
        prop["id"] for prop in database.properties if prop["id"] not in order
    )
    headline: list[dict[str, Any]] = []
    for property_id in order:
        if property_id not in grouped:
            continue
        observation = min(grouped[property_id], key=_observation_rank)
        headline.append(
            {
                "property": property_id,
                "value": observation["value"],
                "unit": observation["unit"],
                "basis": observation["basis"],
            }
        )
        if len(headline) == 4:
            break
    return headline


def build_search_index(
    database: Database,
    representatives: Mapping[
        str, list[tuple[dict[str, Any], dict[str, Any]]]
    ],
    envelopes: Mapping[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    fields = [
        "id",
        "name",
        "record_type",
        "parent_id",
        "family",
        "aliases",
        "prominence",
        "href",
        "description",
        "headline",
    ]
    sorted_materials = sorted(
        database.materials,
        key=lambda item: (
            -item["prominence"],
            item["name"].casefold(),
            item["id"],
        ),
    )
    rows: list[list[Any]] = []
    postings: defaultdict[str, list[int]] = defaultdict(list)

    for row_index, material in enumerate(sorted_materials):
        rows.append(
            [
                material["id"],
                material["name"],
                material["record_type"],
                material["parent_id"],
                material["family"],
                material["aliases"],
                material["prominence"],
                f"/materials/{material['id']}/",
                material["description"],
                _headline_observations(material, database, envelopes),
            ]
        )
        searchable: list[str] = [
            material["id"],
            material["name"],
            material["description"],
            *material["aliases"],
            *material["family"],
        ]
        for system, value in material["designations"].items():
            searchable.append(system)
            if isinstance(value, str):
                searchable.append(value)
            else:
                searchable.extend(value)
        row_tokens: set[str] = set()
        for text in searchable:
            row_tokens.update(_tokenize(text))
        for token in row_tokens:
            postings[token].append(row_index)

    properties: list[dict[str, Any]] = []
    for prop in sorted(
        database.properties, key=lambda item: item["name"].casefold()
    ):
        property_id = prop["id"]
        prop_tokens: set[str] = set()
        for text in [property_id, prop["name"], *prop.get("aliases", [])]:
            prop_tokens.update(_tokenize(text))
        properties.append(
            {
                "id": property_id,
                "name": prop["name"],
                "aliases": prop.get("aliases", []),
                "unit": prop["canonical_unit"],
                "canonical_unit": prop["canonical_unit"],
                "symbol": prop.get("symbol"),
                "description": prop.get("description", ""),
                "count": len(representatives.get(property_id, [])),
                "href": f"/materials/by/{_property_slug(property_id)}/",
                "tokens": sorted(prop_tokens),
            }
        )

    top_materials = [
        material["id"]
        for material in sorted_materials
        if material["record_type"] != "family"
    ][:8]
    top_properties = [
        item["id"]
        for item in sorted(
            properties,
            key=lambda item: (-item["count"], item["name"].casefold()),
        )
        if item["count"]
    ][:8]
    sorted_postings = {key: postings[key] for key in sorted(postings)}

    return {
        "schema_version": database.schema_version,
        "fields": fields,
        "rows": rows,
        "tokens": sorted_postings,
        "token_list": list(sorted_postings),
        "properties": properties,
        "thesaurus": database.thesaurus,
        "featured": {
            "materials": top_materials,
            "properties": top_properties,
        },
    }


def _format_number(value: float, precision: int = 4) -> str:
    return format(value, f".{precision}g")


def _format_observation_value(
    observation: Mapping[str, Any], prop: Mapping[str, Any]
) -> str:
    precision = prop.get("display_precision", 4)
    uncertainty = observation.get("uncertainty")
    if (
        isinstance(uncertainty, dict)
        and uncertainty.get("kind") == "implied"
        and isinstance(uncertainty.get("sigfigs"), int)
    ):
        precision = min(precision, uncertainty["sigfigs"])
    value = _format_number(observation["value"], precision)
    if isinstance(uncertainty, dict):
        if uncertainty.get("kind") == "range":
            value += (
                " "
                f"({_format_number(uncertainty['min'], precision)}–"
                f"{_format_number(uncertainty['max'], precision)})"
            )
        elif uncertainty.get("kind") == "stddev":
            value += f" ± {_format_number(uncertainty['sd'], precision)}"
    return f"{html.escape(value)} <span class=\"muted\">{html.escape(prop['canonical_unit'])}</span>"


def _format_conditions(conditions: Mapping[str, Any]) -> str:
    if not conditions:
        return '<span class="muted">Unconditioned</span>'
    pieces: list[str] = []
    for key, value in conditions.items():
        label = key.replace("_", " ")
        if isinstance(value, list):
            low, high = value
            if low is None:
                rendered = f"≤ {high}"
            elif high is None:
                rendered = f"≥ {low}"
            else:
                rendered = f"{low}–{high}"
        else:
            rendered = str(value)
        pieces.append(f"<strong>{html.escape(label)}:</strong> {html.escape(rendered)}")
    return "<br>".join(pieces)


def _source_html(
    observation: Mapping[str, Any], database: Database
) -> str:
    source = database.source_by_id[observation["source_id"]]
    title = html.escape(source["title"])
    url = source.get("url")
    if isinstance(url, str):
        title = (
            f'<a href="{html.escape(url, quote=True)}" rel="noreferrer">{title}</a>'
        )
    return f"{title}<br><span class=\"muted\">{html.escape(observation['source_locator'])}</span>"


def _page_template(title: str, description: str, content: str) -> str:
    return f"""\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <link rel="stylesheet" href="/materials/assets/styles.css">
</head>
<body>
{content}
</body>
</html>
"""


def _apply_template(
    template: str | None,
    *,
    title: str,
    description: str,
    content: str,
    template_path: Path | None = None,
) -> str:
    if template is None:
        return _page_template(title, description, content)
    if "{{CONTENT}}" not in template:
        label = str(template_path) if template_path else "template"
        raise BuildError(f"{label}: template must contain {{{{CONTENT}}}}")
    replacements = {
        "TITLE": html.escape(title),
        "DESCRIPTION": html.escape(description, quote=True),
        "CONTENT": content,
        "STYLE": '<link rel="stylesheet" href="/materials/assets/styles.css">',
        "SCRIPT": "",
    }

    def replace(match: re.Match[str]) -> str:
        return replacements.get(match.group(1), match.group(0))

    return TEMPLATE_TOKEN_RE.sub(replace, template)


def _render_record_content(
    material: Mapping[str, Any],
    database: Database,
    children_by_parent: Mapping[str, list[dict[str, Any]]],
    envelopes: Mapping[str, list[dict[str, Any]]],
) -> str:
    parent = (
        database.material_by_id.get(material["parent_id"])
        if material["parent_id"]
        else None
    )
    breadcrumb = '<a href="/materials/">Materials</a>'
    if parent is not None:
        breadcrumb += (
            f' / <a href="/materials/{html.escape(parent["id"])}/">'
            f'{html.escape(parent["name"])}</a>'
        )
    breadcrumb += (
        ' · <a href="/materials/sources/">Sources &amp; licences</a>'
    )
    families = " · ".join(html.escape(item) for item in material["family"])
    condition = (
        f'<span class="badge">Condition: {html.escape(material["condition"])}</span>'
        if material["condition"]
        else ""
    )
    aliases = ", ".join(html.escape(item) for item in material["aliases"])
    rows: list[str] = []
    for observation in sorted(
        material["observations"],
        key=lambda item: (
            database.property_by_id[item["property"]]["name"].casefold(),
            _observation_rank(item),
        ),
    ):
        prop = database.property_by_id[observation["property"]]
        rows.append(
            "<tr>"
            f'<td><a href="/materials/by/{_property_slug(prop["id"])}/">'
            f'{html.escape(prop["name"])}</a></td>'
            f'<td class="value">{_format_observation_value(observation, prop)}</td>'
            f"<td>{html.escape(observation['basis'])}</td>"
            f"<td>{_format_conditions(observation['conditions'])}</td>"
            f"<td>{html.escape(observation['test_method'] or '—')}</td>"
            f"<td>{_source_html(observation, database)}</td>"
            "</tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Property</th><th>Value</th>'
        "<th>Basis</th><th>Conditions</th><th>Test method</th><th>Source</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        if rows
        else '<div class="empty">No published observations for this record yet.</div>'
    )

    envelope_rows: list[str] = []
    for envelope in envelopes.get(material["id"], []):
        prop = database.property_by_id[envelope["property"]]
        precision = prop.get("display_precision", 4)
        low = _format_number(envelope["min"], precision)
        high = _format_number(envelope["max"], precision)
        displayed_range = low if envelope["min"] == envelope["max"] else f"{low}–{high}"
        envelope_rows.append(
            "<tr>"
            f'<td><a href="/materials/by/{_property_slug(prop["id"])}/">'
            f'{html.escape(prop["name"])}</a></td>'
            f'<td class="value">{html.escape(displayed_range)} '
            f'<span class="muted">{html.escape(prop["canonical_unit"])}</span></td>'
            f"<td>{envelope['variant_count']}</td>"
            f"<td>{envelope['observation_count']}</td>"
            "</tr>"
        )
    envelope_html = ""
    if envelope_rows:
        envelope_html = (
            "<h2>Derived descendant envelopes</h2>"
            '<p class="muted">Build-time minimum and maximum across descendant '
            "variant observations, including explicit uncertainty-range bounds. "
            "These are discovery envelopes, not stored material observations or "
            "design allowables.</p>"
            '<div class="table-wrap"><table><thead><tr><th>Property</th>'
            "<th>Observed envelope</th><th>Variants</th><th>Observations</th>"
            "</tr></thead><tbody>"
            + "".join(envelope_rows)
            + "</tbody></table></div>"
        )

    child_items = children_by_parent.get(material["id"], [])
    children_html = ""
    if child_items:
        links = "".join(
            f'<li><a href="/materials/{html.escape(child["id"])}/">'
            f'{html.escape(child["name"])}</a> '
            f'<span class="muted">{html.escape(child["record_type"])}</span></li>'
            for child in child_items
        )
        children_html = f"<h2>More specific records</h2><ul>{links}</ul>"

    designation_html = ""
    if material["designations"]:
        rendered = []
        for system, value in material["designations"].items():
            values = value if isinstance(value, list) else [value]
            rendered.append(
                f"<strong>{html.escape(system)}:</strong> "
                + ", ".join(html.escape(item) for item in values)
            )
        designation_html = "<p>" + " · ".join(rendered) + "</p>"

    return f"""\
<main>
  <nav>{breadcrumb}</nav>
  <p class="eyebrow">{html.escape(material["record_type"]).upper()} RECORD</p>
  <h1>{html.escape(material["name"])}</h1>
  <p class="lede">{html.escape(material["description"])}</p>
  <div class="meta"><span class="badge">{families}</span>{condition}</div>
  {f'<p><strong>Also known as:</strong> {aliases}</p>' if aliases else ''}
  {designation_html}
  <h2>Property observations</h2>
  {table}
  {envelope_html}
  {children_html}
</main>
"""


def _render_property_content(
    prop: Mapping[str, Any],
    entries: Sequence[tuple[dict[str, Any], dict[str, Any]]],
    database: Database,
) -> str:
    rows: list[str] = []
    for rank, (material, observation) in enumerate(entries, start=1):
        rows.append(
            "<tr>"
            f"<td>{rank}</td>"
            f'<td><a href="/materials/{html.escape(material["id"])}/">'
            f'{html.escape(material["name"])}</a>'
            f'<br><span class="muted">{html.escape(material["record_type"])}</span></td>'
            f'<td class="value">{_format_observation_value(observation, prop)}</td>'
            f"<td>{html.escape(observation['basis'])}</td>"
            f"<td>{_format_conditions(observation['conditions'])}</td>"
            f"<td>{_source_html(observation, database)}</td>"
            "</tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Material</th>'
        "<th>Representative value</th><th>Basis</th><th>Conditions</th><th>Source</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        if rows
        else '<div class="empty">No materials currently publish this property.</div>'
    )
    description = prop.get("description") or (
        f"Materials ranked by {prop['name']} in the canonical unit "
        f"{prop['canonical_unit']}."
    )
    direction = (
        "lowest to highest"
        if prop.get("sort_direction") == "asc"
        else "highest to lowest"
    )
    return f"""\
<main>
  <nav><a href="/materials/">Materials</a> / Properties · <a href="/materials/sources/">Sources &amp; licences</a></nav>
  <p class="eyebrow">SORTED PROPERTY</p>
  <h1>{html.escape(prop["name"])}</h1>
  <p class="lede">{html.escape(description)}</p>
  <p class="muted">{len(entries)} records · {html.escape(direction)} · canonical unit {html.escape(prop["canonical_unit"])}</p>
  {table}
</main>
"""


def _render_sources_content(database: Database) -> str:
    rows: list[str] = []
    for source in sorted(
        database.sources, key=lambda item: item["title"].casefold()
    ):
        title = html.escape(source["title"])
        if isinstance(source.get("url"), str):
            title = (
                f'<a href="{html.escape(source["url"], quote=True)}" '
                f'rel="noreferrer">{title}</a>'
            )
        publication = source.get("publication_date") or "Undated"
        revision = source.get("revision")
        publication_text = html.escape(str(publication))
        if revision:
            publication_text += f"<br><span class=\"muted\">{html.escape(str(revision))}</span>"
        rows.append(
            "<tr>"
            f"<td>{title}<br><span class=\"muted\">"
            f"{html.escape(str(source.get('organization') or 'Unknown organization'))}"
            "</span></td>"
            f"<td>{publication_text}</td>"
            f"<td>{html.escape(str(source.get('license') or 'License not stated'))}</td>"
            f"<td>{html.escape(str(source.get('notes') or '—'))}</td>"
            "</tr>"
        )
    return f"""\
<main>
  <nav><a href="/materials/">Materials</a> / Sources</nav>
  <p class="eyebrow">PROVENANCE</p>
  <h1>Sources &amp; licences</h1>
  <p class="lede">Every published observation points to one of these source records and to a locator within it. Follow the source link and verify the cited table, page, revision, conditions, and basis before engineering use.</p>
  <div class="table-wrap"><table><thead><tr><th>Source</th><th>Publication</th><th>Licence</th><th>Scope notes</th></tr></thead><tbody>
    {''.join(rows)}
  </tbody></table></div>
</main>
"""


def _builtin_index() -> str:
    return """\
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Materials lookup</title><meta name="description" content="Search cited engineering material property observations.">
<link rel="stylesheet" href="/materials/assets/styles.css"></head>
<body><main><p class="eyebrow">MATERIALS LOOKUP</p><h1>Find a material or property</h1>
<p class="lede">Search material names, designations, aliases, families, and registered properties.</p>
<input class="search" id="q" type="search" autocomplete="off" autofocus placeholder="Try 6061, stiffness, aluminium…">
<p class="muted" id="status">Loading index…</p><ul class="results" id="results"></ul></main>
<script>
let index=null;const q=document.querySelector('#q'),out=document.querySelector('#results'),status=document.querySelector('#status');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function search(){if(!index)return;const needle=q.value.trim().toLowerCase();if(!needle){out.innerHTML='';status.textContent=`${index.rows.length} materials · ${index.properties.length} properties`;return}
const pos=Object.fromEntries(index.fields.map((f,i)=>[f,i]));const material=index.rows.map(r=>({name:r[pos.name],href:r[pos.href],kind:r[pos.record_type],hay:[r[pos.id],r[pos.name],...(r[pos.aliases]||[]),...(r[pos.family]||[])].join(' ').toLowerCase()})).filter(x=>x.hay.includes(needle));
const props=index.properties.filter(p=>[p.id,p.name,...p.aliases].join(' ').toLowerCase().includes(needle)).map(p=>({name:p.name,href:p.href,kind:'property'}));
const hits=[...props,...material].slice(0,50);status.textContent=`${hits.length}${hits.length===50?'+':''} matches`;out.innerHTML=hits.map(x=>`<li><a href="${esc(x.href)}">${esc(x.name)}</a> <span class="muted">${esc(x.kind)}</span></li>`).join('')}
q.addEventListener('input',search);fetch('/materials/search-index.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(x=>{index=x;search()}).catch(()=>status.textContent='Search index could not be loaded.');
</script></body></html>
"""


def render_outputs(root: Path, database: Database) -> dict[str, bytes]:
    representatives = _representative_observations(database)
    envelopes = _descendant_envelopes(database)
    search_index = build_search_index(database, representatives, envelopes)
    outputs: dict[str, bytes] = {}

    def add_text(relative_path: str, text: str) -> None:
        normalized = "\n".join(line.rstrip() for line in text.splitlines())
        if text.endswith("\n"):
            normalized += "\n"
        outputs[relative_path] = normalized.encode("utf-8")

    add_text(
        "search-index.json",
        json.dumps(
            search_index,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
    )

    src = root / "src"
    index_path = src / "index.html"
    add_text(
        "index.html",
        index_path.read_text(encoding="utf-8")
        if index_path.is_file()
        else _builtin_index(),
    )
    style_path = src / "styles.css"
    add_text(
        "assets/styles.css",
        style_path.read_text(encoding="utf-8")
        if style_path.is_file()
        else BUILTIN_STYLE,
    )

    detail_template_path = src / "detail_template.html"
    property_template_path = src / "property_template.html"
    detail_template = (
        detail_template_path.read_text(encoding="utf-8")
        if detail_template_path.is_file()
        else None
    )
    property_template = (
        property_template_path.read_text(encoding="utf-8")
        if property_template_path.is_file()
        else None
    )

    children_by_parent: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for material in database.materials:
        if material["parent_id"]:
            children_by_parent[material["parent_id"]].append(material)
    for children in children_by_parent.values():
        children.sort(key=lambda item: (item["name"].casefold(), item["id"]))

    for material in database.materials:
        record_json = dict(material)
        record_json["children"] = [
            child["id"] for child in children_by_parent.get(material["id"], [])
        ]
        record_json["derived_envelopes"] = envelopes.get(material["id"], [])
        record_json["source_details"] = {
            source_id: database.source_by_id[source_id]
            for source_id in sorted(
                {
                    observation["source_id"]
                    for observation in material["observations"]
                }
            )
        }
        add_text(
            f"records/{material['id']}.json",
            json.dumps(
                record_json,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n",
        )
        content = _render_record_content(
            material, database, children_by_parent, envelopes
        )
        add_text(
            f"{material['id']}/index.html",
            _apply_template(
                detail_template,
                title=f"{material['name']} — Materials lookup",
                description=material["description"],
                content=content,
                template_path=detail_template_path,
            ),
        )

    for prop in database.properties:
        property_id = prop["id"]
        entries = representatives.get(property_id, [])
        description = prop.get("description") or (
            f"Engineering materials ranked by {prop['name']}."
        )
        content = _render_property_content(prop, entries, database)
        add_text(
            f"by/{_property_slug(property_id)}/index.html",
            _apply_template(
                property_template,
                title=f"{prop['name']} by material — Materials lookup",
                description=description,
                content=content,
                template_path=property_template_path,
            ),
        )

    sources_content = _render_sources_content(database)
    add_text(
        "sources/index.html",
        _apply_template(
            detail_template,
            title="Sources & licences — Materials lookup",
            description=(
                "Sources, licences, revisions, and provenance notes for the "
                "Materials Lookup prototype."
            ),
            content=sources_content,
            template_path=detail_template_path,
        ),
    )

    return outputs


def _safe_manifest_paths(output: Path) -> set[str]:
    manifest_path = output / ".build-manifest.json"
    if manifest_path.is_symlink():
        raise BuildError(f"refusing to follow symlinked manifest: {manifest_path}")
    if not manifest_path.is_file():
        return set()
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read generated-file manifest {manifest_path}: {exc}")
    if not isinstance(document, dict):
        raise BuildError(f"{manifest_path}: manifest must be an object")
    if document.get("build_version") != BUILD_VERSION:
        raise BuildError(
            f"{manifest_path}: unsupported build_version "
            f"{document.get('build_version')!r}; expected {BUILD_VERSION}"
        )
    files = document.get("files")
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        raise BuildError(f"{manifest_path}: files must be an array of paths")
    safe: set[str] = set()
    for relative in files:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or relative in {"", "."}:
            raise BuildError(f"{manifest_path}: unsafe generated path {relative!r}")
        safe.add(path.as_posix())
    return safe


def _assert_no_output_symlink(output: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or relative in {"", "."}:
        raise BuildError(f"unsafe generated output path {relative!r}")
    candidate = output
    for part in path.parts:
        candidate /= part
        if candidate.is_symlink():
            raise BuildError(f"refusing to follow output symlink: {candidate}")
    return candidate


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary_name = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def write_outputs(output: Path, outputs: Mapping[str, bytes]) -> None:
    output = output.resolve()
    if output.exists() and not output.is_dir():
        raise BuildError(f"output path is not a directory: {output}")
    previous = _safe_manifest_paths(output)
    current = set(outputs)
    for relative in sorted(previous | current):
        _assert_no_output_symlink(output, relative)

    # A generated target is owned only after it appears in our manifest.  An
    # identical pre-existing file can be adopted; a differing one is unrelated
    # and must never be silently overwritten.
    adopted: set[str] = set()
    for relative in sorted(current):
        destination = output / relative
        if destination.exists() and relative not in previous:
            if destination.is_file() and destination.read_bytes() == outputs[relative]:
                adopted.add(relative)
            else:
                raise BuildError(
                    "refusing to overwrite untracked output file or directory: "
                    f"{destination}"
                )

    for relative in sorted(current - adopted):
        _atomic_write(output / relative, outputs[relative])

    # Delete only files explicitly claimed by the previous generated manifest.
    for relative in sorted(previous - current, reverse=True):
        stale = output / relative
        try:
            if stale.is_file() or stale.is_symlink():
                stale.unlink()
        except OSError as exc:
            raise BuildError(f"cannot remove stale generated file {stale}: {exc}") from exc
        parent = stale.parent
        while parent != output:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    manifest = {
        "build_version": BUILD_VERSION,
        "files": sorted(current),
    }
    _atomic_write(
        output / ".build-manifest.json",
        (
            json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False)
            + "\n"
        ).encode("utf-8"),
    )


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _validate_output_location(root: Path, output: Path) -> None:
    root = root.resolve()
    output = output.resolve()
    if output == root or _path_is_within(root, output):
        raise BuildError(
            f"output must not be the repository root or its ancestor: {output}"
        )
    for protected_name in ("curated", "registry", "src", "scripts", "tests"):
        protected = (root / protected_name).resolve()
        if output == protected or _path_is_within(output, protected):
            raise BuildError(
                f"output must not overlap source directory {protected}: {output}"
            )


def build(root: Path, output: Path | None = None, *, check: bool = False) -> tuple[int, int]:
    root = root.resolve()
    destination = (output or root / "materials").resolve()
    if not check:
        _validate_output_location(root, destination)
    database = load_database(root)
    outputs = render_outputs(root, database)
    if not check:
        write_outputs(destination, outputs)
    return len(database.materials), len(database.properties)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    default_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Validate curated materials data and build the static site."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help=f"repository root (default: {default_root})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="output directory (default: ROOT/materials)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and render in memory without writing generated files",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress success output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = args.root.resolve()
    output = args.output
    if output is not None and not output.is_absolute():
        output = root / output
    try:
        material_count, property_count = build(root, output, check=args.check)
    except ValidationError as exc:
        print(
            f"build_site.py: validation failed with {len(exc.errors)} "
            f"error{'s' if len(exc.errors) != 1 else ''}:",
            file=sys.stderr,
        )
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        return 2
    except (BuildError, OSError) as exc:
        print(f"build_site.py: {exc}", file=sys.stderr)
        return 1
    if not args.quiet:
        action = "Validated" if args.check else "Built"
        destination = "" if args.check else f" in {output or root / 'materials'}"
        print(
            f"{action} {material_count} material records and "
            f"{property_count} properties{destination}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
