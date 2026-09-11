"""Adversarial cases the migrated corpus does not already cover.

The legacy corpus is all point values with no uncertainty, no lifecycle, and no
structured locators, so migrating it alone cannot prove the contract handles the
harder shapes. This module adds the smallest set that exercises them.

Additions are an overlay rather than edits to the migration, so the migration
stays provably lossless and every synthetic addition stays separately auditable.
"""

from __future__ import annotations

from typing import Any, Mapping

from .units import find_conversion, round_to_significant_figures

ADVERSARIAL_SOURCE_ID = "synthetic-source-adversarial"

_MATERIAL_ID = "synthetic-advdemo-cfpeek"
_STATE_ID = "synthetic-advdemo-cfpeek-cf30"


def _canonical(quantity_kind: str, display_value: float, display_unit: str) -> float:
    conversion = find_conversion(quantity_kind, display_unit)
    if conversion is None:
        raise ValueError(f"no conversion for {display_unit!r} in {quantity_kind!r}")
    return conversion.to_canonical(display_value)


def _point(
    quantity_kind: str,
    display_value: float,
    display_unit: str,
    canonical_unit: str,
    figures: int,
) -> dict[str, Any]:
    return {
        "kind": "point",
        "reported": {
            "value": display_value,
            "unit": display_unit,
            "significant_figures": figures,
        },
        "canonical": {
            "value": round_to_significant_figures(
                _canonical(quantity_kind, display_value, display_unit), 12
            ),
            "unit": canonical_unit,
        },
    }


def _interval(
    quantity_kind: str,
    low: float,
    high: float,
    display_unit: str,
    canonical_unit: str,
    figures: int,
) -> dict[str, Any]:
    return {
        "kind": "interval",
        "reported": {
            "minimum": low,
            "maximum": high,
            "unit": display_unit,
            "significant_figures": figures,
        },
        "canonical": {
            "minimum": round_to_significant_figures(
                _canonical(quantity_kind, low, display_unit), 12
            ),
            "maximum": round_to_significant_figures(
                _canonical(quantity_kind, high, display_unit), 12
            ),
            "unit": canonical_unit,
        },
    }


def _bound(
    kind: str,
    quantity_kind: str,
    display_value: float,
    display_unit: str,
    canonical_unit: str,
    figures: int,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "reported": {
            "value": display_value,
            "unit": display_unit,
            "significant_figures": figures,
        },
        "canonical": {
            "value": round_to_significant_figures(
                _canonical(quantity_kind, display_value, display_unit), 12
            ),
            "unit": canonical_unit,
        },
    }


def _observation(
    observation_id: str,
    property_id: str,
    result: Mapping[str, Any],
    *,
    state_id: str | None = _STATE_ID,
    conditions: Mapping[str, Any] | None = None,
    uncertainty: Mapping[str, Any] | None = None,
    basis: str = "synthetic_typical",
    locator: Mapping[str, Any] | None = None,
    status: str = "active",
    supersedes: list[str] | None = None,
    test_method: Mapping[str, Any] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    record = {
        "id": observation_id,
        "material_id": _MATERIAL_ID,
        "state_id": state_id,
        "property_id": property_id,
        "result": dict(result),
        "uncertainty": dict(uncertainty) if uncertainty else None,
        "basis": basis,
        "conditions": dict(conditions or {}),
        "test_method": dict(test_method) if test_method else None,
        "source_id": ADVERSARIAL_SOURCE_ID,
        "source_locator": dict(locator or {"label": f"Fabricated adversarial case {observation_id}"}),
        "status": status,
        "supersedes_observation_ids": list(supersedes or []),
    }
    if notes:
        record["notes"] = notes
    return record


def source() -> dict[str, Any]:
    return {
        "id": ADVERSARIAL_SOURCE_ID,
        "title": "Synthetic adversarial property sheet",
        "organization": "Materials Schema Lab",
        "source_type": "synthetic_fixture",
        "publication_date": "2026-08-23",
        "revision": "A",
        "license": "CC0-1.0",
        "synthetic": True,
    }


def material() -> dict[str, Any]:
    """A commercial grade with no standard designation.

    Its primary browse path is chemistry and its supplemental path is the
    composite family, which is the case that would double-count the material if
    supplemental membership were treated as a second primary.
    """
    return {
        "id": _MATERIAL_ID,
        "name": "AdvDemo CF-PEEK",
        "identity_kind": "synthetic_commercial_grade",
        "aliases": ["AdvDemo carbon PEEK"],
        "designations": [],
        "primary_taxon_id": "peek-like-polymers",
        "supplemental_taxon_ids": ["fiber-reinforced-polymers"],
        "notes": (
            "Commercial grade identified by trade name only. Deliberately carries "
            "no standard designation."
        ),
    }


def state() -> dict[str, Any]:
    return {
        "id": _STATE_ID,
        "material_id": _MATERIAL_ID,
        "name": "30% carbon-filled",
        "aliases": ["CF30", "30% carbon filled"],
        "fixed_attributes": {
            "reinforcement": "carbon_fiber",
            "fiber_mass_fraction_1": 0.3,
        },
        "supplemental_taxon_ids": [],
    }


def observations() -> list[dict[str, Any]]:
    plate = {"temperature_K": 293.15, "product_form": "plate", "orientation": "LT"}

    return [
        # A source-reported interval. Its endpoints, not a midpoint, contribute
        # to any corpus span.
        _observation(
            "synthetic-adv-obs-0001",
            "ultimate_tensile_strength",
            _interval("pressure", 210, 240, "MPa", "Pa", 3),
            conditions=plate,
            locator={
                "label": "Page 12, Table 3, CF-PEEK 30CF plate, LT ultimate tensile strength",
                "page": 12,
                "table": "3",
                "section": "3.2 Mechanical properties",
                "row": "CF-PEEK 30CF plate",
                "column": "UTS, LT",
                "record": "row-14",
            },
            test_method={"reported_label": "Synthetic tensile procedure STP-8"},
        ),
        # A one-sided bound: the source specifies a floor, not a value.
        _observation(
            "synthetic-adv-obs-0002",
            "tensile_yield_strength",
            _bound("lower_bound", "pressure", 130, "MPa", "Pa", 2),
            conditions=plate,
            basis="synthetic_minimum",
            locator={
                "label": "Page 12, Table 3, CF-PEEK 30CF specified minimum yield",
                "page": 12,
                "table": "3",
                "row": "CF-PEEK 30CF plate",
                "column": "Yield, min",
            },
        ),
        # A point with separate uncertainty. The uncertainty must not widen the
        # corpus span the way a reported interval does.
        _observation(
            "synthetic-adv-obs-0003",
            "density",
            _point("mass_density", 1410, "kg/m^3", "kg/m^3", 4),
            conditions={"temperature_K": 293.15},
            uncertainty={
                "kind": "standard_deviation",
                "reported": {
                    "value": 15,
                    "unit": "kg/m^3",
                    "significant_figures": 2,
                },
                "canonical": {"value": 15, "unit": "kg/m^3"},
                "sample_count": 7,
            },
            locator={
                "label": "Page 11, Table 1, CF-PEEK 30CF density",
                "page": 11,
                "table": "1",
                "row": "CF-PEEK 30CF",
                "column": "Density",
            },
        ),
        # An explicit unavailable assertion. Missing is not zero and must not be
        # inherited from the material or the category.
        _observation(
            "synthetic-adv-obs-0004",
            "electrical_resistivity",
            {
                "kind": "unavailable",
                "reason": "The synthetic source does not report resistivity for this state.",
            },
            conditions={},
            locator={"label": "Page 11, Table 1, CF-PEEK 30CF, resistivity column blank"},
        ),
        # An explicit not-applicable assertion, which is a different claim from
        # unavailable: the property has no meaning for this material.
        _observation(
            "synthetic-adv-obs-0005",
            "shore_a_hardness",
            {
                "kind": "not_applicable",
                "reason": "Shore A applies to elastomers; this is a rigid composite.",
            },
            conditions={},
            locator={"label": "Page 11, note 2, hardness scale applicability"},
        ),
        # A superseded observation and the revision that replaces it. History
        # stays auditable while default projections exclude it.
        _observation(
            "synthetic-adv-obs-0006",
            "thermal_conductivity",
            _point("thermal_conductivity", 0.42, "W/(m*K)", "W/(m*K)", 2),
            conditions={"temperature_K": 293.15},
            status="superseded",
            locator={
                "label": "Revision A page 11, Table 1, thermal conductivity",
                "page": 11,
                "table": "1",
                "row": "CF-PEEK 30CF",
                "column": "Thermal conductivity",
            },
            notes="Withdrawn by the issuer in revision B.",
        ),
        _observation(
            "synthetic-adv-obs-0007",
            "thermal_conductivity",
            _point("thermal_conductivity", 0.48, "W/(m*K)", "W/(m*K)", 2),
            conditions={"temperature_K": 293.15},
            supersedes=["synthetic-adv-obs-0006"],
            locator={
                "label": "Revision B page 11, Table 1, thermal conductivity",
                "page": 11,
                "table": "1",
                "row": "CF-PEEK 30CF",
                "column": "Thermal conductivity",
            },
        ),
        # Direct material data alongside state data. It must not flow down into
        # the state, and the state's values must not flow up.
        _observation(
            "synthetic-adv-obs-0008",
            "max_service_temperature",
            _point("temperature", 260, "degC", "K", 3),
            state_id=None,
            conditions={},
            locator={
                "label": "Page 10, Table 0, CF-PEEK family continuous service temperature",
                "page": 10,
                "table": "0",
                "row": "CF-PEEK family",
                "column": "Continuous service temperature",
            },
            notes="Reported for the grade as a whole rather than for one filled state.",
        ),
    ]


def apply(dataset: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return the dataset with adversarial cases added, plus a list of additions."""
    result = {key: value for key, value in dataset.items()}
    result["sources"] = list(dataset["sources"]) + [source()]
    result["materials"] = list(dataset["materials"]) + [material()]
    result["states"] = list(dataset["states"]) + [state()]
    added_observations = observations()
    result["observations"] = list(dataset["observations"]) + added_observations

    manifest = dict(dataset["dataset"])
    counts = dict(manifest.get("expected_counts") or {})
    counts["materials"] = len(result["materials"])
    counts["states"] = len(result["states"])
    counts["observations"] = len(result["observations"])
    manifest["expected_counts"] = counts
    result["dataset"] = manifest

    added = (
        [f"source:{ADVERSARIAL_SOURCE_ID}", f"material:{_MATERIAL_ID}", f"state:{_STATE_ID}"]
        + [f"observation:{item['id']}" for item in added_observations]
    )
    return result, added
