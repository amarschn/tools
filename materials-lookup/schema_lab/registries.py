"""Registries the contract depends on: conditions, bases, sources, quantities.

These encode the state-versus-observation matrix in executable form. The matrix
document (`docs/state-condition-matrix.md`) is the rationale; this module is the
thing the validator actually enforces, so the two must be changed together.
"""

from __future__ import annotations

from typing import Any

# Placement constants mirror the registry's `allowed_placement` values.
STATE = "state_fixed_attribute"
OBSERVATION = "observation_condition"


def condition_registry() -> list[dict[str, Any]]:
    """The v1 condition registry.

    `navigable` was added at checkpoint 1: a navigable condition generates a
    drill-down level (AX70 T6 -> AX70 T6 plate) even though it is stored on the
    observation. Only enumerated conditions may be navigable, because a
    continuous quantity has no finite set of pages to generate.
    """
    return [
        # -- state-defining attributes -----------------------------------
        {
            "id": "temper",
            "name": "Temper designation",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": ["T4", "T6", "T651", "T73"],
            "allowed_placement": STATE,
        },
        {
            "id": "heat_treatment",
            "name": "Heat-treatment outcome",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": [
                "annealed",
                "normalized",
                "solution_treated_aged",
                "quenched_tempered_550",
                "quenched_tempered_700",
            ],
            "allowed_placement": STATE,
        },
        {
            "id": "work_condition",
            "name": "Mechanical or work condition",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": ["cold_drawn", "cold_worked_20_percent", "cold_worked_hard"],
            "allowed_placement": STATE,
        },
        {
            "id": "formulation",
            "name": "Named formulation",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": ["unfilled"],
            "allowed_placement": STATE,
        },
        {
            "id": "reinforcement",
            "name": "Reinforcement kind",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": ["glass_fiber", "carbon_fiber"],
            "allowed_placement": STATE,
        },
        {
            "id": "fiber_mass_fraction_1",
            "name": "Nominal reinforcement mass fraction",
            "value_type": "number",
            "canonical_unit": "1",
            "allowed_values": None,
            "allowed_placement": STATE,
        },
        {
            "id": "layup",
            "name": "Laminate layup class",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": ["unidirectional", "quasi_isotropic", "woven_0_90"],
            "allowed_placement": STATE,
        },
        {
            "id": "conditioning_state",
            "name": "Named conditioning state",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": ["dry_as_molded", "conditioned"],
            "allowed_placement": STATE,
        },
        # -- observation context -----------------------------------------
        {
            "id": "product_form",
            "name": "Product form",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": [
                "plate",
                "sheet",
                "extrusion",
                "bar",
                "injection_molded",
                "compression_molded",
            ],
            "allowed_placement": OBSERVATION,
            "navigable": True,
        },
        {
            "id": "thickness_m",
            "name": "Product thickness",
            "value_type": "number_interval",
            "canonical_unit": "m",
            "allowed_values": None,
            "allowed_placement": OBSERVATION,
        },
        {
            "id": "cross_sectional_area_m2",
            "name": "Cross-sectional area",
            "value_type": "number",
            "canonical_unit": "m^2",
            "allowed_values": None,
            "allowed_placement": OBSERVATION,
        },
        {
            "id": "orientation",
            "name": "Loading or measurement orientation",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": [
                "L",
                "LT",
                "ST",
                "in_plane",
                "longitudinal",
                "transverse",
                "radial",
            ],
            "allowed_placement": OBSERVATION,
        },
        {
            "id": "temperature_K",
            "name": "Test or service temperature",
            "value_type": "number",
            "canonical_unit": "K",
            "allowed_values": None,
            "allowed_placement": OBSERVATION,
        },
        {
            "id": "moisture_content_1",
            "name": "Measured moisture content",
            "value_type": "number",
            "canonical_unit": "1",
            "allowed_values": None,
            "allowed_placement": OBSERVATION,
        },
        {
            "id": "fiber_volume_fraction_1",
            "name": "Measured reinforcement volume fraction",
            "value_type": "number",
            "canonical_unit": "1",
            "allowed_values": None,
            "allowed_placement": OBSERVATION,
        },
        # -- retired -------------------------------------------------------
        {
            "id": "material_state",
            "name": "Generic legacy material state",
            "value_type": "enum",
            "canonical_unit": None,
            "allowed_values": ["retired"],
            "allowed_placement": STATE,
            "retired": True,
            "retired_reason": (
                "the catch-all hid several meanings and must be mapped to temper, "
                "heat_treatment, work_condition, formulation, or conditioning_state"
            ),
        },
    ]


def basis_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "synthetic_typical",
            "name": "Typical (synthetic)",
            "definition": "A representative value as reported by the synthetic fixture.",
        },
        {
            "id": "synthetic_minimum",
            "name": "Minimum (synthetic)",
            "definition": "A specified minimum as reported by the synthetic fixture.",
        },
    ]


# Quantity kinds keyed by property id, falling back to canonical unit. Keyed
# first by id because `shore_a_hardness` and `elongation_at_break` share the
# dimensionless canonical unit while behaving differently on display.
QUANTITY_KIND_BY_PROPERTY = {
    "shore_a_hardness": "hardness_scale",
    "elongation_at_break": "dimensionless",
}

QUANTITY_KIND_BY_UNIT = {
    "Pa": "pressure",
    "kg/m^3": "mass_density",
    "W/(m*K)": "thermal_conductivity",
    "ohm*m": "electrical_resistivity",
    "K": "temperature",
    "J/m": "energy_per_length",
    "1": "dimensionless",
}


def quantity_kind_for(property_id: str, canonical_unit: str) -> str:
    if property_id in QUANTITY_KIND_BY_PROPERTY:
        return QUANTITY_KIND_BY_PROPERTY[property_id]
    return QUANTITY_KIND_BY_UNIT.get(canonical_unit, "unknown")


# Legacy `material_state` values mapped to their precise v1 key. Any value not
# listed here is a migration error requiring review rather than a guess.
LEGACY_MATERIAL_STATE = {
    "annealed": ("heat_treatment", "annealed"),
    "normalized": ("heat_treatment", "normalized"),
    "solution_treated_aged": ("heat_treatment", "solution_treated_aged"),
    "quenched_tempered_550": ("heat_treatment", "quenched_tempered_550"),
    "quenched_tempered_700": ("heat_treatment", "quenched_tempered_700"),
    "cold_drawn": ("work_condition", "cold_drawn"),
    "cold_worked_20_percent": ("work_condition", "cold_worked_20_percent"),
    "cold_worked_hard": ("work_condition", "cold_worked_hard"),
}

# State labels whose conditioning meaning must become a registered attribute
# rather than being inferred from a measured moisture number.
CONDITIONING_LABELS = {
    "dry as molded": "dry_as_molded",
    "conditioned": "conditioned",
}
