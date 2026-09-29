"""Adapt reviewed legacy authoring records to the checkpoint-1 contract.

The authoring files remain the only edited data. This adapter preserves each
observation and its citation, dissolves artificial reference states, and keeps
source metadata and printed literals in a serving sidecar (the v0.1 contract
does not have fields for those). No inference or network access is performed.
"""
from copy import deepcopy
import hashlib
import json
import re

from schema_lab.registries import condition_registry
from schema_lab.validator import validate
from builder.import_steel_grades import STATE_ATTRIBUTES as STEEL_STATE_ATTRIBUTES, HARDNESS_CONDITIONS

PROPERTY_IDS = {"yield_strength": "tensile_yield_strength", "tensile_strength": "ultimate_tensile_strength"}
REVIEWED_TEMPERS = ("O", "H111", "H112", "T1", "T4", "T5", "T6", "T61", "T63", "T64")
REVIEWED_HEAT_TREATMENTS = {
    "mill annealed": "annealed",
    "duplex annealed": "annealed",
    "solution treated and aged": "solution_treated_aged",
}


def canonical_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def adapt(database):
    rows = database.materials
    conditions = [c for c in condition_registry() if not c.get("retired")]
    by_condition = {c["id"]: c for c in conditions}
    by_condition["product_form"]["allowed_values"].extend(["stock_shape", "coil"])
    by_condition["work_condition"]["allowed_values"].append("cold_rolled")
    by_condition["temper"]["allowed_values"] = sorted(set(by_condition["temper"]["allowed_values"]) | set(REVIEWED_TEMPERS))
    by_condition["thickness_m"]["nullable_bounds"] = True
    by_condition["heat_treatment"]["allowed_values"].extend(["hardened_tempered", "carburized_hardened_tempered"])
    by_condition["work_condition"]["allowed_values"].append("thermomechanically_rolled")
    conditions.append({"id": "hardness_condition", "name": "Hardness", "value_type": "enum",
        "canonical_unit": None, "allowed_values": HARDNESS_CONDITIONS[:],
        "allowed_placement": "state_fixed_attribute"})
    has_steel_taxon = any(r["id"] == "steels" for r in rows)
    data = {
        "dataset": {"id": "materials-reference", "contract_version": "0.1.0", "corpus_version": "1.0.0-rc.1", "synthetic": False,
                    "warning": "Published reference values. Check source, basis and conditions for your application."},
        "taxa": [], "materials": [], "states": [], "observations": [],
        "properties": [], "property_groups": [], "conditions": conditions,
        "bases": [{"id": b, "name": b.replace("_", " ").capitalize()} for b in sorted({o["basis"] for r in rows for o in r["observations"]})],
        "sources": [],
    }
    extras = {"sources": deepcopy(database.sources), "observations": {}, "legacy_targets": {}}
    for source in database.sources:
        if source["source_type"] == "prototype_seed" or source["id"].startswith("synthetic-"):
            raise ValueError("Release cannot contain prototype or synthetic sources")
        if not source.get("url", "").startswith("https://"):
            raise ValueError(f"Source {source['id']} needs an HTTPS citation")
        data["sources"].append({k: source[k] for k in ("id", "title", "organization", "source_type", "publication_date", "revision", "license")})
    for prop in database.properties:
        quantity = {"density": "mass_density"}.get(prop["quantity_kind"], prop["quantity_kind"])
        if prop["id"] == "poissons_ratio": quantity = "ratio"
        data["properties"].append({"id": PROPERTY_IDS.get(prop["id"], prop["id"]), "name": prop["name"],
            "aliases": sorted(set(prop["aliases"] + [prop["id"].replace("_", " ")])),
            "quantity_kind": quantity, "canonical_unit": prop["canonical_unit"], "definition": prop["description"]})
    data["property_groups"] = [{"id": "strength", "name": "Strength", "aliases": ["strength"],
        "member_property_ids": ["tensile_yield_strength", "ultimate_tensile_strength", "flexural_strength"]}]
    for row in rows:
        rid = row["id"]
        if rid.startswith("synthetic-") or "demo" in rid:
            raise ValueError(f"Non-factual identity in release: {rid}")
        if row["record_type"] == "family":
            aliases = list(row["aliases"])
            if rid == "engineering-plastics": aliases += ["plastic", "plastics", "polymer", "polymers"]
            if rid == "stainless-steels":
                aliases += ["stainless", "stainless steel"] + ([] if has_steel_taxon else ["steel", "steels"])
            if rid == "ceramics": aliases += ["ceramic"]
            data["taxa"].append({"id": rid, "name": row["name"], "aliases": sorted(set(aliases)),
                "primary_parent_id": "steels" if rid == "stainless-steels" and has_steel_taxon else row["parent_id"], "supplemental_broader_ids": []})
            extras["legacy_targets"][rid] = {"category": rid}
        elif row["record_type"] == "grade":
            data["materials"].append({"id": rid, "name": row["name"], "aliases": row["aliases"],
                "identity_kind": "standard_grade" if any(k != "Supplier" for k in row["designations"]) else "commercial_grade",
                "primary_taxon_id": row["parent_id"], "supplemental_taxon_ids": [],
                "designations": [{"system_id": k.lower(), "value": v} for k, v in row["designations"].items()],
                "notes": row["description"]})
            extras["legacy_targets"][rid] = {"material": rid}
        else:
            material_id = row["parent_id"]
            state_id = None
            if row["condition"] in REVIEWED_TEMPERS:
                state_id = rid
                fixed = {"temper": row["condition"]}
                name = row["condition"]
            elif row["condition"] in REVIEWED_HEAT_TREATMENTS:
                state_id = rid
                fixed = {"heat_treatment": REVIEWED_HEAT_TREATMENTS[row["condition"]]}
                name = row["condition"].capitalize()
            elif row["condition"] in STEEL_STATE_ATTRIBUTES:
                state_id = rid
                fixed = deepcopy(STEEL_STATE_ATTRIBUTES[row["condition"]])
                name = row["condition"][0].upper() + row["condition"][1:]
            elif row["condition"] in ("cold rolled sheet", "cold rolled coil", "cold rolled"):
                state_id = rid
                fixed = {"work_condition": "cold_rolled"}
                name = "Cold rolled"
            elif row["condition"] not in ("stock shape", "supplier reference state"):
                raise ValueError(f"Unreviewed state mapping: {rid}")
            if state_id:
                data["states"].append({"id": state_id, "material_id": material_id, "name": name,
                    "aliases": sorted(set(row["aliases"] + [row["name"]])), "fixed_attributes": fixed,
                    "supplemental_taxon_ids": []})
            extras["legacy_targets"][rid] = {"material": material_id, **({"state": state_id} if state_id else {})}
            for old in row["observations"]:
                if old["uncertainty"]["kind"] not in ("implied", "range"):
                    raise ValueError(f"Unreviewed uncertainty mapping for {rid}/{old['property']}")
                if old["uncertainty"]["kind"] == "range" and old.get("result_kind") != "interval":
                    raise ValueError(f"A range needs an explicit interval result kind: {rid}/{old['property']}")
                # IDs are based on source identity and locator, never on a value.
                identity = [rid, old["property"], old["source_id"], old["source_locator"]]
                oid = "obs-" + hashlib.sha256(canonical_bytes(identity)).hexdigest()[:20]
                context = deepcopy(old["conditions"])
                note = context.pop("material_state", "")
                if "thickness_m" in context:
                    low, high = context["thickness_m"]
                    context["thickness_m"] = {"minimum": low, "maximum": high}
                owner_state = state_id
                # The physical table is grade-level. Do not imply that it was
                # measured on the cold rolled sheet used by the mechanical table.
                if row["condition"] in ("cold rolled sheet", "cold rolled coil", "cold rolled") and not note:
                    owner_state = None
                if old["source_id"] == "hydro-6061-2019" and old["property"] == "density":
                    owner_state = None
                raw = old.get("source_value")
                if not raw:
                    raise ValueError(f"Missing source literal for {rid}/{old['property']}; review the source before release")
                nums = [float(v.replace(",", "")) for v in re.split("[–]", raw["text"])]
                scale, offset = raw["scale_to_si"], raw.get("offset_to_si", 0)
                kind = old.get("result_kind", "lower_bound" if old["basis"] == "minimum" else "point")
                if kind not in ("point", "interval", "lower_bound", "upper_bound"):
                    raise ValueError(f"Unreviewed result kind: {oid}/{kind}")
                if len(nums) != (2 if kind == "interval" else 1):
                    raise ValueError(f"Invalid source literal: {oid}")
                keys = ("minimum", "maximum") if kind == "interval" else ("value",)
                canonical = {k: n * scale + offset for k, n in zip(keys, nums)}
                expected = [old["uncertainty"][k] for k in ("min", "max")] if kind == "interval" else [old["value"]]
                for got, want in zip(canonical.values(), expected):
                    if abs(got - want) > max(1e-10, abs(want) * 1e-10):
                        raise ValueError(f"Reported/SI mismatch: {oid}: {got} != {want}")
                reported = dict(zip(keys, nums), unit=raw["unit"], significant_figures=raw["significant_figures"])
                observation = {"id": oid, "material_id": material_id, "state_id": owner_state,
                    "property_id": PROPERTY_IDS.get(old["property"], old["property"]),
                    "result": {"kind": kind, "reported": reported, "canonical": dict(canonical, unit=old["unit"])},
                    "basis": old["basis"], "conditions": context, "uncertainty": None,
                    "test_method": {"reported_label": old["test_method"]}, "source_id": old["source_id"],
                    "source_locator": {"label": old["source_locator"], "page": old["source_page"]},
                    "status": "active", "supersedes_observation_ids": [], "notes": note}
                data["observations"].append(observation)
                extras["observations"][oid] = {"source_value": raw, "legacy_record_id": rid}
    data["dataset"]["expected_counts"] = {k: len(v) for k, v in data.items() if isinstance(v, list)}
    errors = [d for d in validate(data) if d.severity == "error"]
    if errors:
        raise ValueError("Canonical release validation failed:\n" + "\n".join(str(d) for d in errors))
    return data, extras
