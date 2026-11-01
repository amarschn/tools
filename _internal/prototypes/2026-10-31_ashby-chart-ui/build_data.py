#!/usr/bin/env python3
"""Reduce the chart's selection.json to the small file these prototypes load.

Run from the repository root:
    python3 _internal/prototypes/2026-10-31_ashby-chart-ui/build_data.py

Each material gets one value per property: the median of its room-temperature
observations, with their full range. Production keeps the stricter rule, which pairs
observations by compatible conditions. This shortcut is for judging interface ideas
and is not a reference for design values.
"""
import gzip
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("data.json")
SYMBOLS = {
    "density": "rho", "youngs_modulus": "E", "flexural_modulus": "Ef",
    "ultimate_tensile_strength": "UTS", "tensile_yield_strength": "Sy",
    "flexural_strength": "MOR", "compressive_strength": "Sc",
    "thermal_conductivity": "k", "specific_heat": "cp", "poissons_ratio": "nu",
    "elongation_at_break": "el",
}
ORDER = list(SYMBOLS)


def main():
    selection = json.loads((ROOT / "data/materials/selection.json").read_text())
    registry = selection["property_registry"]
    sources = selection["sources"]
    source_rows = list(sources.values()) if isinstance(sources, dict) else sources
    source_index = {row["id"]: i for i, row in enumerate(source_rows)}
    grouped = defaultdict(lambda: defaultdict(list))
    for row in selection["observations"].values():
        temperature = row["conditions"].get("temperature_K")
        if isinstance(temperature, (int, float)) and not 288 <= temperature <= 303:
            continue
        if row["property_id"] in SYMBOLS and row.get("plot_value"):
            grouped[row["material_id"]][row["property_id"]].append(row)
    materials = []
    for mid, material in selection["materials"].items():
        values = {}
        for pid, rows in grouped[mid].items():
            multiplier = registry[pid]["display_multiplier"]
            plotted = [r["plot_value"] * multiplier for r in rows]
            low, high = plotted[:], plotted[:]
            for r in rows:
                canonical = r["result"]["canonical"]
                if "minimum" in canonical:
                    low.append(canonical["minimum"] * multiplier)
                if "maximum" in canonical:
                    high.append(canonical["maximum"] * multiplier)
            first = rows[0]
            values[SYMBOLS[pid]] = [
                float(f"{statistics.median(plotted):.5g}"), float(f"{min(low):.5g}"), float(f"{max(high):.5g}"),
                first["basis"], source_index[first["source_id"]], first["source_locator"].get("label", ""),
            ]
        classes = material.get("classification") or []
        materials.append({
            "id": mid, "n": material["name"], "f": material["family"],
            "c": classes[1] if len(classes) > 1 else material.get("sub_family", ""),
            "o": sorted({source_rows[v[4]]["organization"] for v in values.values()}),
            "v": values,
        })
    properties = [{"id": pid, "sym": SYMBOLS[pid], "label": registry[pid]["label"], "unit": registry[pid]["display_unit"].replace("^3", "³"),
                   "definition": registry[pid].get("definition", "")} for pid in ORDER]
    indices = []
    for iid, index in selection["indices"].items():
        indices.append({"id": iid, "name": index["name"], "expression": index["expression"], "maximize": index["maximize"],
                        "scope": index["scope"], "source": index["source"], "x": SYMBOLS.get(index["x"]), "y": SYMBOLS.get(index["y"]),
                        "derivation": index["derivation"]})
    data = {"generated_from": selection["source_build_id"], "properties": properties, "indices": indices,
            "sources": [[row["title"], row["organization"]] for row in source_rows], "materials": materials}
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(text)
    print(f"{len(materials)} materials, {len(text):,} bytes, {len(gzip.compress(text.encode())):,} gzip")


if __name__ == "__main__":
    main()
