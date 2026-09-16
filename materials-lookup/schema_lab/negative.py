"""Executable negative fixtures.

Each case is a patch against one small valid base dataset plus the diagnostic
code it must produce. Cases patch a minimal base rather than the full corpus so
their paths stay stable when the corpus grows.

The contract is that each case fails *for its intended reason*. A case that
merely fails is not evidence: it could be failing for an unrelated defect
introduced later, which is exactly the regression these fixtures exist to catch.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from . import CONTRACT_VERSION, diagnostics as D
from .registries import basis_registry, condition_registry


def base_dataset() -> dict[str, Any]:
    """One small, complete, valid dataset."""
    return {
        "dataset": {
            "id": "schema-lab-negative-base",
            "contract_version": CONTRACT_VERSION,
            "corpus_version": "negative-base-1.0.0",
            "synthetic": True,
            "warning": "Fabricated schema example only. Not engineering data.",
        },
        "taxa": [
            {
                "id": "metals",
                "name": "Metals",
                "aliases": ["metal"],
                "primary_parent_id": None,
                "supplemental_broader_ids": [],
            },
            {
                "id": "aluminium-like-alloys",
                "name": "Aluminium-like alloys",
                "aliases": ["aluminium alloy"],
                "primary_parent_id": "metals",
                "supplemental_broader_ids": [],
            },
        ],
        "properties": [
            {
                "id": "ultimate_tensile_strength",
                "name": "Ultimate tensile strength",
                "aliases": ["tensile strength", "UTS"],
                "quantity_kind": "pressure",
                "canonical_unit": "Pa",
                "group_id": "strength",
            },
            {
                "id": "density",
                "name": "Density",
                "aliases": ["mass density"],
                "quantity_kind": "mass_density",
                "canonical_unit": "kg/m^3",
                "group_id": None,
            },
        ],
        "property_groups": [
            {
                "id": "strength",
                "name": "Strength",
                "aliases": ["strength"],
                "member_property_ids": ["ultimate_tensile_strength"],
            }
        ],
        "conditions": condition_registry(),
        "bases": basis_registry(),
        "sources": [
            {
                "id": "synthetic-source-negative",
                "title": "Synthetic negative-fixture property sheet",
                "organization": "Materials Schema Lab",
                "source_type": "synthetic_fixture",
                "publication_date": "2026-08-23",
                "revision": "A",
                "license": "CC0-1.0",
                "synthetic": True,
            }
        ],
        "materials": [
            {
                "id": "synthetic-synal-ax70",
                "name": "Synal AX70",
                "identity_kind": "synthetic_standard_grade",
                "aliases": ["AX-70"],
                "designations": [{"system_id": "synthetic_fixture", "value": "AX70"}],
                "primary_taxon_id": "aluminium-like-alloys",
                "supplemental_taxon_ids": [],
            }
        ],
        "states": [
            {
                "id": "synthetic-synal-ax70-t6",
                "material_id": "synthetic-synal-ax70",
                "name": "T6",
                "aliases": ["AX70 T6"],
                "fixed_attributes": {"temper": "T6"},
                "supplemental_taxon_ids": [],
            }
        ],
        "observations": [
            {
                "id": "synthetic-obs-negative-0001",
                "material_id": "synthetic-synal-ax70",
                "state_id": None,
                "property_id": "density",
                "result": {
                    "kind": "point",
                    "reported": {
                        "value": 2.81,
                        "unit": "g/cm^3",
                        "significant_figures": 3,
                    },
                    "canonical": {"value": 2810, "unit": "kg/m^3"},
                },
                "uncertainty": None,
                "basis": "synthetic_typical",
                "conditions": {"temperature_K": 293.15},
                "test_method": None,
                "source_id": "synthetic-source-negative",
                "source_locator": {
                    "label": "Page 4, Table 2, AX70 density",
                    "page": 4,
                    "table": "2",
                    "row": "AX70",
                    "column": "Density",
                },
                "status": "active",
                "supersedes_observation_ids": [],
            },
            {
                "id": "synthetic-obs-negative-0002",
                "material_id": "synthetic-synal-ax70",
                "state_id": "synthetic-synal-ax70-t6",
                "property_id": "ultimate_tensile_strength",
                "result": {
                    "kind": "interval",
                    "reported": {
                        "minimum": 530,
                        "maximum": 560,
                        "unit": "MPa",
                        "significant_figures": 3,
                    },
                    "canonical": {
                        "minimum": 530000000,
                        "maximum": 560000000,
                        "unit": "Pa",
                    },
                },
                "uncertainty": None,
                "basis": "synthetic_typical",
                "conditions": {
                    "temperature_K": 293.15,
                    "product_form": "plate",
                    "thickness_m": {"minimum": 0.025, "maximum": 0.05},
                    "orientation": "LT",
                },
                "test_method": {"reported_label": "Synthetic tensile procedure STP-8"},
                "source_id": "synthetic-source-negative",
                "source_locator": {
                    "label": "Page 8, Table 4, AX70-T6 plate, LT tensile strength",
                    "page": 8,
                    "table": "4",
                    "row": "AX70-T6 plate",
                    "column": "Ultimate tensile strength, LT",
                },
                "status": "active",
                "supersedes_observation_ids": [],
            },
        ],
    }


def _condition_index(dataset: Mapping[str, Any], condition_id: str) -> int:
    for position, condition in enumerate(dataset["conditions"]):
        if condition["id"] == condition_id:
            return position
    raise KeyError(condition_id)


def cases() -> list[dict[str, Any]]:
    """Every negative case, each naming the one diagnostic it must produce."""
    dataset = base_dataset()
    thickness = _condition_index(dataset, "thickness_m")

    return [
        {
            "id": "observation-condition-on-state",
            "expected_code": D.ATTRIBUTE_PLACEMENT,
            "operations": [
                {"op": "add", "path": "/states/0/fixed_attributes/product_form", "value": "plate"}
            ],
            "reason": "Product form belongs to an observation in v1, not to a named state.",
        },
        {
            "id": "state-attribute-on-observation",
            "expected_code": D.CONDITION_PLACEMENT,
            "operations": [
                {"op": "add", "path": "/observations/1/conditions/temper", "value": "T4"}
            ],
            "reason": "Temper is fixed once on the named state and cannot be repeated or contradicted by an observation.",
        },
        {
            "id": "retired-legacy-state-key",
            "expected_code": D.LEGACY_STATE_KEY,
            "operations": [
                {
                    "op": "add",
                    "path": "/states/0/fixed_attributes/material_state",
                    "value": "annealed",
                }
            ],
            "reason": "The catch-all material_state key is retired and must be mapped to a precise attribute.",
        },
        {
            "id": "navigable-numeric-condition",
            "expected_code": D.NAVIGABLE_CONDITION_NOT_ENUM,
            "operations": [
                {"op": "add", "path": f"/conditions/{thickness}/navigable", "value": True}
            ],
            "reason": "Thickness is continuous. Marking it navigable would generate a page per measured range, which is the line checkpoint 1 drew.",
        },
        {
            "id": "observation-state-material-mismatch",
            "expected_code": D.STATE_MATERIAL_MISMATCH,
            "operations": [
                {
                    "op": "add",
                    "path": "/materials/-",
                    "value": {
                        "id": "synthetic-other-material",
                        "name": "Synthetic other material",
                        "identity_kind": "synthetic_standard_grade",
                        "aliases": [],
                        "designations": [
                            {"system_id": "synthetic_fixture", "value": "OTHER"}
                        ],
                        "primary_taxon_id": "aluminium-like-alloys",
                        "supplemental_taxon_ids": [],
                    },
                },
                {
                    "op": "replace",
                    "path": "/observations/1/material_id",
                    "value": "synthetic-other-material",
                },
            ],
            "reason": "An observation naming a state must name that state's material.",
        },
        {
            "id": "observation-attached-to-taxon",
            "expected_code": D.OBSERVATION_TAXON_ATTACHED,
            "operations": [
                {"op": "replace", "path": "/observations/0/material_id", "value": "metals"},
                {"op": "replace", "path": "/observations/0/state_id", "value": None},
            ],
            "reason": "Categories are navigation and never own measurements.",
        },
        {
            "id": "inverted-reported-interval",
            "expected_code": D.RESULT_INTERVAL_ORDER,
            "operations": [
                {"op": "replace", "path": "/observations/1/result/reported/minimum", "value": 570}
            ],
            "reason": "A reported interval's minimum cannot exceed its maximum.",
        },
        {
            "id": "missing-source-locator",
            "expected_code": D.SOURCE_LOCATOR_REQUIRED,
            "operations": [{"op": "remove", "path": "/observations/0/source_locator"}],
            "reason": "A source document without a precise location is not sufficient provenance.",
        },
        {
            "id": "missing-reported-precision",
            "expected_code": D.RESULT_PRECISION_REQUIRED,
            "operations": [
                {
                    "op": "remove",
                    "path": "/observations/0/result/reported/significant_figures",
                }
            ],
            "reason": "Without the source's precision, converting to another unit invents digits the source never claimed.",
        },
        {
            "id": "uncertainty-as-interval",
            "expected_code": D.UNCERTAINTY_AS_INTERVAL,
            "operations": [
                {
                    "op": "replace",
                    "path": "/observations/0/uncertainty",
                    "value": {
                        "kind": "standard_deviation",
                        "reported": {
                            "minimum": 2.79,
                            "maximum": 2.83,
                            "unit": "g/cm^3",
                            "significant_figures": 3,
                        },
                        "canonical": {"value": 20, "unit": "kg/m^3"},
                        "sample_count": 5,
                    },
                }
            ],
            "reason": "A source-reported range is a result of kind interval, not an uncertainty magnitude.",
        },
        {
            "id": "wrong-canonical-unit",
            "expected_code": D.UNIT_MISMATCH,
            "operations": [
                {"op": "replace", "path": "/observations/0/result/canonical/unit", "value": "Pa"}
            ],
            "reason": "A canonical value must use its property's canonical unit.",
        },
        {
            "id": "incoherent-canonical-unit",
            "expected_code": D.UNIT_INCOHERENT,
            "operations": [
                {"op": "replace", "path": "/properties/0/canonical_unit", "value": "MPa"}
            ],
            "reason": "Canonical units carry no decimal prefix, so values are comparable without a scale factor.",
        },
        {
            "id": "unknown-property",
            "expected_code": D.PROPERTY_UNKNOWN,
            "operations": [
                {"op": "replace", "path": "/observations/0/property_id", "value": "not_a_property"}
            ],
            "reason": "Observations may only use registered properties.",
        },
        {
            "id": "unknown-condition",
            "expected_code": D.CONDITION_UNKNOWN,
            "operations": [
                {"op": "add", "path": "/observations/0/conditions/strain_rate_1_s", "value": 0.001}
            ],
            "reason": "Unregistered condition keys are a hard error rather than an ad hoc field.",
        },
        {
            "id": "condition-value-not-registered",
            "expected_code": D.CONDITION_VALUE_INVALID,
            "operations": [
                {"op": "add", "path": "/observations/0/conditions/product_form", "value": "billet"}
            ],
            "reason": "An enumerated condition may only take a registered value.",
        },
        {
            "id": "unknown-basis",
            "expected_code": D.BASIS_UNKNOWN,
            "operations": [
                {"op": "replace", "path": "/observations/0/basis", "value": "vibes"}
            ],
            "reason": "Reporting basis must be registered so results are compared like for like.",
        },
        {
            "id": "unknown-source",
            "expected_code": D.SOURCE_UNKNOWN,
            "operations": [
                {"op": "replace", "path": "/observations/0/source_id", "value": "no-such-source"}
            ],
            "reason": "Every observation must resolve to a registered source.",
        },
        {
            "id": "missing-reference",
            "expected_code": D.REF_MISSING,
            "operations": [
                {
                    "op": "replace",
                    "path": "/materials/0/primary_taxon_id",
                    "value": "no-such-taxon",
                }
            ],
            "reason": "References must resolve within the dataset.",
        },
        {
            "id": "duplicate-id",
            "expected_code": D.ID_DUPLICATE,
            "operations": [
                {
                    "op": "add",
                    "path": "/taxa/-",
                    "value": {
                        "id": "metals",
                        "name": "Metals duplicate",
                        "aliases": [],
                        "primary_parent_id": None,
                        "supplemental_broader_ids": [],
                    },
                }
            ],
            "reason": "Identifiers must be unique within their collection.",
        },
        {
            "id": "malformed-id",
            "expected_code": D.ID_MALFORMED,
            "operations": [
                {"op": "replace", "path": "/taxa/1/id", "value": "Aluminium Alloys!"}
            ],
            "reason": "Identifiers are stable machine tokens, not display labels.",
        },
        {
            "id": "taxonomy-cycle",
            "expected_code": D.TAXON_CYCLE,
            "operations": [
                {
                    "op": "replace",
                    "path": "/taxa/0/primary_parent_id",
                    "value": "aluminium-like-alloys",
                }
            ],
            "reason": "The primary browse path must be a tree so drilldown terminates.",
        },
        {
            "id": "duplicate-taxon-membership",
            "expected_code": D.TAXON_MEMBERSHIP_DUPLICATE,
            "operations": [
                {
                    "op": "add",
                    "path": "/materials/0/supplemental_taxon_ids/-",
                    "value": "aluminium-like-alloys",
                }
            ],
            "reason": "A material listed twice under one taxon would be double-counted in coverage.",
        },
        {
            "id": "supersedes-self",
            "expected_code": D.SUPERSEDES_SELF,
            "operations": [
                {
                    "op": "add",
                    "path": "/observations/0/supersedes_observation_ids/-",
                    "value": "synthetic-obs-negative-0001",
                }
            ],
            "reason": "An observation cannot supersede itself.",
        },
        {
            "id": "unsupported-contract-version",
            "expected_code": D.CONTRACT_VERSION_UNSUPPORTED,
            "operations": [
                {"op": "replace", "path": "/dataset/contract_version", "value": "9.0.0"}
            ],
            "reason": "A dataset must declare a contract version this validator implements.",
        },
    ]


# --------------------------------------------------------------------------
# A minimal JSON Patch subset: add, replace, remove.
# --------------------------------------------------------------------------


def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _resolve(document: Any, tokens: Sequence[str]) -> tuple[Any, str]:
    cursor = document
    for token in tokens[:-1]:
        key = _unescape(token)
        cursor = cursor[int(key)] if isinstance(cursor, list) else cursor[key]
    return cursor, _unescape(tokens[-1])


def apply_operations(
    document: Mapping[str, Any], operations: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Apply patch operations to a deep copy of `document`."""
    result = copy.deepcopy(document)
    for operation in operations:
        tokens = operation["path"].split("/")[1:]
        container, key = _resolve(result, tokens)
        op = operation["op"]

        if isinstance(container, list):
            if op == "add":
                if key == "-":
                    container.append(operation["value"])
                else:
                    container.insert(int(key), operation["value"])
            elif op == "replace":
                container[int(key)] = operation["value"]
            elif op == "remove":
                del container[int(key)]
            else:
                raise ValueError(f"unsupported op {op!r}")
            continue

        if op in ("add", "replace"):
            container[key] = operation["value"]
        elif op == "remove":
            container.pop(key, None)
        else:
            raise ValueError(f"unsupported op {op!r}")
    return result
