"""Compile a validated catalog into a relocatable static website."""
import csv
from dataclasses import asdict
import gzip
import hashlib
import html
import io
import json
from urllib.parse import urlencode

from schema_lab.projections import Corpus, active, mixed_condition_flags, span
from schema_lab.units import conversions_for
from .catalog import PROPERTY_IDS, adapt, canonical_bytes
from .publication import public_source, verify_public_outputs

VERSION = "1.0.0-rc.1"
ASSETS = ("app.mjs", "search.mjs", "format.mjs", "app.css")


def summary(observations, property_id, corpus):
    pool = [o for o in active(observations) if o["property_id"] == property_id]
    measured = [o for o in pool if o["result"]["kind"] in ("point", "interval")]
    bounds = [o for o in pool if o["result"]["kind"] in ("lower_bound", "upper_bound")]
    limits = {}
    for kind in ("lower_bound", "upper_bound"):
        group = [o for o in bounds if o["result"]["kind"] == kind]
        if group:
            limits[kind] = {"minimum": min(o["result"]["canonical"]["value"] for o in group),
                "maximum": max(o["result"]["canonical"]["value"] for o in group),
                "significant_figures": min(o["result"]["reported"]["significant_figures"] for o in group), "count": len(group)}
    return {"range": span(measured, property_id), "limits": limits, "observation_count": len(pool),
        "material_count": len({o["material_id"] for o in pool}),
        "mixed_conditions": mixed_condition_flags(pool, corpus), "bases": sorted({o["basis"] for o in pool})}


def compile_data(database):
    data, extras = adapt(database)
    extras['sources'] = [public_source(s) for s in extras['sources']]
    corpus = Corpus(data)
    source_by_id = {s["id"]: s for s in extras["sources"]}
    material_by_id = corpus.materials
    entities, records = [], {}

    def lineage(taxon):
        ids = []
        while taxon:
            ids.append(taxon)
            taxon = corpus.taxa[taxon]["primary_parent_id"]
        return ids

    def entity(kind, row, route, aliases, observations, category_ids):
        entities.append({"id": row["id"], "kind": kind, "name": row["name"], "route": route,
            "aliases": sorted(set(aliases)), "category_ids": category_ids,
            "properties": sorted({o["property_id"] for o in observations}), "observation_count": len(observations)})

    for taxon in data["taxa"]:
        material_ids = {m["id"] for m in corpus.materials_under(taxon["id"])}
        pool = [o for o in data["observations"] if o["material_id"] in material_ids]
        entity("category", taxon, {"category": taxon["id"]}, taxon.get("aliases", []), pool, lineage(taxon["id"]))
    for material in data["materials"]:
        mid = material["id"]
        pool = corpus.observations_by_material.get(mid, [])
        states = corpus.states_by_material.get(mid, [])
        categories = lineage(material["primary_taxon_id"])
        aliases = material["aliases"] + [d["value"] for d in material["designations"]]
        category_terms = {a.lower() for cid in categories for a in [corpus.taxa[cid]["name"], *corpus.taxa[cid].get("aliases", [])]}
        identity_aliases = [a for a in aliases if a.lower() not in category_terms]
        entity("material", material, {"material": mid}, identity_aliases, pool, categories)
        for state in states:
            state_pool = corpus.observations_by_state.get(state["id"], [])
            # Shared grade aliases must never make a state look like an exact
            # answer to a grade-only query.
            state_aliases = [a for a in state["aliases"] if a not in aliases]
            state_aliases += [a + " " + state["name"] for a in aliases]
            entity("state", dict(state, name=material["name"] + " · " + state["name"]),
                {"material": mid, "state": state["id"]}, state_aliases, state_pool, categories)
        for state in [None] + states:
            sid = state["id"] if state else None
            own = [o for o in pool if o["state_id"] == sid]
            for form in sorted({o["conditions"]["product_form"] for o in own if "product_form" in o["conditions"]}):
                name = material["name"] + (" " + state["name"] if state else "") + " " + form.replace("_", " ")
                base_aliases = ([a + " " + state["name"] for a in aliases] if state else aliases)
                entity("form", {"id": (sid or mid) + "--" + form, "name": name},
                    {"material": mid, **({"state": sid} if sid else {}), "form": form},
                    [a + " " + form.replace("_", " ") for a in base_aliases],
                    [o for o in own if o["conditions"].get("product_form") == form], categories)
        records[mid] = {"material": material, "states": states, "observations": pool,
            "sources": [source_by_id[s] for s in sorted({o["source_id"] for o in pool})],
            "source_values": {o["id"]: extras["observations"][o["id"]]["source_value"] for o in pool},
            "summaries": {p["id"]: summary(pool, p["id"], corpus) for p in data["properties"]}}
    properties = []
    for p in data["properties"]:
        units = [asdict(u) for u in conversions_for(p["quantity_kind"])]
        properties.append(dict(p, units=units, metric_unit="GPa" if p["id"] == "youngs_modulus" else units[0]["unit"]))
    index = {"version": VERSION, "contract_version": "0.1.0", "counts": data["dataset"]["expected_counts"],
        "entities": entities, "taxa": data["taxa"], "properties": properties, "property_groups": data["property_groups"],
        "conditions": data["conditions"], "legacy_targets": extras["legacy_targets"], "property_aliases": PROPERTY_IDS}
    projections = {}
    for prop in properties:
        pid = prop["id"]
        projections[pid] = {"property_id": pid, "categories": {}, "materials": {}}
        for taxon in data["taxa"]:
            ids = {m["id"] for m in corpus.materials_under(taxon["id"])}
            projections[pid]["categories"][taxon["id"]] = summary([o for o in data["observations"] if o["material_id"] in ids], pid, corpus)
        for material in data["materials"]:
            projections[pid]["materials"][material["id"]] = records[material["id"]]["summaries"][pid]
    return data, extras, index, records, projections


def render_outputs(root, database):
    data, extras, index, records, projections = compile_data(database)
    assets = {name: (root / "src" / name).read_bytes() for name in ASSETS}
    template = (root / "src" / "index.html").read_text()
    fingerprint = hashlib.sha256(canonical_bytes([VERSION, data, extras, index, projections]))
    for path in sorted((root / "release").glob("*.py")):
        fingerprint.update(path.name.encode() + path.read_bytes())
    for name, content in sorted(assets.items()): fingerprint.update(name.encode() + content)
    fingerprint.update(template.encode())
    fingerprint.update((root / "src" / "README.md").read_bytes())
    build_id = fingerprint.hexdigest()[:20]
    prefix = f"data/{build_id}"
    index["build_id"] = build_id
    outputs = {}
    def add(path, content):
        outputs[path] = content if isinstance(content, bytes) else content.encode()
    def json_file(path, content): add(path, canonical_bytes(content))
    for name, content in assets.items(): add(f"assets/{build_id}/{name}", content)
    json_file(f"{prefix}/index.json", index)
    json_file(f"{prefix}/sources.json", extras["sources"])
    for mid, record in records.items():
        json_file(f"{prefix}/records/{mid}.json", dict(record, build_id=build_id, contract_version="0.1.0"))
    for pid, projection in projections.items():
        json_file(f"{prefix}/properties/{pid}.json", dict(projection, build_id=build_id))
    json_file(f"{prefix}/catalog.json", {"canonical": data, "citation_details": extras})
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["observation_id", "material_id", "state_id", "property", "result_kind", "value_si", "minimum_si", "maximum_si", "unit", "basis", "conditions", "method", "source_id", "source_organization", "source_title", "source_revision", "source_locator", "original_value", "original_unit", "significant_figures"])
    sources = {s["id"]: s for s in extras["sources"]}
    for o in data["observations"]:
        c = o["result"]["canonical"]
        raw = extras["observations"][o["id"]]["source_value"]
        source = sources[o['source_id']]
        writer.writerow([o["id"], o["material_id"], o["state_id"], o["property_id"], o["result"]["kind"], c.get("value", ""), c.get("minimum", ""), c.get("maximum", ""), c["unit"], o["basis"], json.dumps(o["conditions"], sort_keys=True), o["test_method"]["reported_label"], source['id'], source['organization'], source['title'], source['revision'], o["source_locator"]["label"], raw["text"], raw["unit"], raw["significant_figures"]])
    add(f"{prefix}/observations.csv", stream.getvalue())
    for token, value in {"BUILD_ID": build_id, "DATA_PATH": prefix, "VERSION": VERSION,
        "MATERIAL_COUNT": str(len(data["materials"])), "OBSERVATION_COUNT": str(len(data["observations"]))}.items():
        template = template.replace("{{" + token + "}}", value)
    add("index.html", template)
    add("README.md", (root / "src" / "README.md").read_bytes())
    add("data-license.txt", (root / "DATA-LICENSE.md").read_bytes())
    add("code-license.txt", (root / "LICENSE").read_bytes())

    def redirect(path, relative, route):
        target = relative + "?" + urlencode(route)
        safe = html.escape(target, quote=True)
        add(path, f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="refresh" content="0;url={safe}"><title>Materials Lookup</title><a href="{safe}">Open Materials Lookup</a></html>')
    for old, route in extras["legacy_targets"].items(): redirect(f"{old}/index.html", "../", route)
    for prop in database.properties:
        redirect("by/" + prop["id"].replace("_", "-") + "/index.html", "../../", {"property": PROPERTY_IDS.get(prop["id"], prop["id"])})
    redirect("sources/index.html", "../", {"view": "sources"})
    add("_headers", "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Cache-Control: no-cache\n/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n/data/*\n  Cache-Control: public, max-age=31536000, immutable\n")
    manifest = {"version": VERSION, "build_id": build_id, "contract_version": "0.1.0", "counts": index["counts"],
        "index": f"{prefix}/index.json", "catalog": f"{prefix}/catalog.json", "csv": f"{prefix}/observations.csv",
        "index_bytes": len(outputs[f"{prefix}/index.json"]), "index_gzip_bytes": len(gzip.compress(outputs[f"{prefix}/index.json"], mtime=0)),
        "files": {path: {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()} for path, content in sorted(outputs.items())}}
    json_file("release-manifest.json", manifest)
    verify_public_outputs(outputs, database.sources)
    return outputs
