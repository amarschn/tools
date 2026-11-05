"""Reviewed October 2026 concrete batch: UHPC, GFRC, and cementitious mortars.

The tables below are numerical transcriptions of the pinned sources. Densities
keep their printed state (fresh, mixed, hardened, or dry), because they are not
interchangeable. Normal site builds use curated JSON. See
docs/concrete-2026-10-batch-review.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from builder.import_reference_tables import obs, pair, record  # noqa: E402

DATE = "2026-10-31"
LEDGER = "concrete-2026-10.json"
PSI = 6894.757293168
MSI = PSI * 1e6
PCF = 16.01846337

# id, title, publisher, URL, filename, SHA256, page count, revision, source type
DOCUMENTS = [
    ("fhwa-hrt-06-103", "Material Property Characterization of Ultra-High Performance Concrete (FHWA-HRT-06-103)",
     "US Federal Highway Administration",
     "https://www.fhwa.dot.gov/publications/research/infrastructure/structures/06103/06103.pdf",
     "fhwa-hrt-06-103.pdf", "f045b9cc0be75d04c8b045e5857eeaf9fece7e4f04412b18975c041e4bb8096c",
     188, "August 2006", "government_handbook"),
    ("stocrete-sm", "StoCrete SM technical data sheet", "Sto",
     "https://www.specifiedby.com/sto/quick-repair-mortars/sto_quick-repair-mortars_techspec_5_stocrete-sm.pdf",
     "stocrete-sm.pdf", "0bb4a1bbdc92a445ff6e9c2cac15f6b1aabbef8ceb74a18761477352e441a9be",
     5, "Rev. 1, 2016-04-01", "manufacturer_datasheet"),
    ("stocrete-rm-f", "StoCrete RM F technical data sheet", "Sto",
     "https://www.specifiedby.com/sto/quick-repair-mortars/sto_quick-repair-mortars_techspec_3_stocrete-rm-f.pdf",
     "stocrete-rm-f.pdf", "25cd812fc7ecaefad1aea333d8104a14d44100911ac092a3693a8fd60c213660",
     6, "Rev. 1, 2016-08-12", "manufacturer_datasheet"),
    ("stocrete-ts-108", "StoCrete TS 108 technical data sheet", "Sto",
     "https://www.specifiedby.com/sto/spray-mortar/sto_spray-mortar_techspec_4_tm-stocrete-ts-108-20170925.pdf",
     "stocrete-ts-108.pdf", "94839be8be3d224018e5e72a2e25adf307af245350cb95e4d4982faa9af3ebef",
     6, "Rev. 1, 2017-09-25", "manufacturer_datasheet"),
    ("sikaemaco-488-ci", "SikaEmaco-488 CI product data sheet", "Sika",
     "https://usa.sika.com/content/dam/dms/us01/x/sikaemaco-488-ci.pdf",
     "sikaemaco-488-ci.pdf", "f21d67c8a6a3ead267402827c97344230b7e774218a0ed0cd85c85f83301ea1f",
     4, "July 2025, version 02.02", "manufacturer_datasheet"),
    ("sika-monotop-112", "Sika MonoTop-112 MultiUse Repair product data sheet", "Sika",
     "https://gbr.sika.com/dms/getdocument.get/4af61037-e693-4f1b-a36e-a20b8fa6540b/sika-monotop-112multiuserepair.pdf",
     "sika-monotop-112.pdf", "e9f1cecb044c5180763b09d40c50d9a8c861ba174bf2a75d4d231787a7b28c84",
     3, "April 2018, version 01.01", "manufacturer_datasheet"),
    ("sikaquick-pro-1000", "SikaQuick Pro 1000 product data sheet", "Sika",
     "https://usa.sika.com/content/dam/dms/us01/x/sikaquick-pro-1000.pdf",
     "sikaquick-pro-1000.pdf", "4e54f8f81db306409c1bdb7b7799111aac679e3de68135967e985603f09d343e",
     5, "May 2026, version 01.03", "manufacturer_datasheet"),
    ("sikacrete-650-tecfast", "Sikacrete-650 Tecfast product data sheet", "Sika",
     "https://gbr.sika.com/dms/getdocument.get/811d4ccd-6604-4692-8ef0-046974825c40/sikacrete-650-tecfast.pdf",
     "sikacrete-650-tecfast.pdf", "d718136f3e68ea2ebe66b8cb04794a192f20d0c97ef94999aae803146be3538a",
     4, "May 2026, version 01.01", "manufacturer_datasheet"),
    ("flexcrete-monolite", "Monolite product data sheet", "Flexcrete Technologies",
     "https://www.specifiedby.com/flexcrete-technologies/monolite-concrete-repair-materials/flexcrete-technologies-ltd_monolite_techspec_1_tds-monolite.pdf",
     "flexcrete-monolite.pdf", "323a1a7c75a634fc667950ac2602b21741a1a34d8b8beb46ee8076f1124d28d8",
     2, "Undated; retrieved 2026-10-31", "manufacturer_datasheet"),
    ("emer-patch-repair-40", "Emer-Patch Repair 40 technical data sheet", "Emer",
     "https://www.emer.com.au/sites/default/files/2023-08/Emer-Patch_Repair_40_TDS.pdf",
     "emer-patch-repair-40.pdf", "56d64624c2ed8e3a09f06b085ce011fa25e9f65c4852ce57a577099935a4256a",
     3, "August 2023", "manufacturer_datasheet"),
    ("forton-vf-774", "Forton VF-774 technical bulletin", "Forton, via Smooth-On",
     "https://www.smooth-on.com/tb/files/Forton_VF_774_TB.pdf",
     "forton-vf-774.pdf", "f1c99f430b33a839b6195fe0f248d3fa889003ee5c8de54f52d1b3541d05b518",
     3, "Undated; retrieved 2026-10-31", "manufacturer_datasheet"),
]

MPA, GPA = (1e6, "MPa"), (1e9, "GPa")
AGE = "28 days."
# id, name, subfamily, description, aliases, supplier, source, rows of
# (property, literal, page, printed row, method, scale, unit, note, kind).
MATERIALS = [
    ("ductal-uhpc", "Ductal UHPC", "uhpc",
     "Steel-fibre ultra-high performance concrete. Manufacturer-supplied ranges reported by FHWA.",
     ["UHPC", "ultra-high performance concrete", "Ductal", "UHPFRC"], "Ductal", "fhwa-hrt-06-103", [
         ("density", "2,440–2,550", 16, "Density", "Manufacturer-supplied characteristic", 1, "kg/m³", "Table 2, printed page 4.", "typical"),
         ("compressive_strength", "180–225", 16, "Compressive Strength", "Manufacturer-supplied characteristic", *MPA, "Table 2, printed page 4.", "typical"),
         ("youngs_modulus", "55–58.5", 16, "Modulus of Elasticity", "Manufacturer-supplied characteristic", *GPA, "Table 2, printed page 4.", "typical"),
         ("flexural_strength", "40–50", 16, "Flexural Strength", "Manufacturer-supplied characteristic", *MPA, "Table 2, printed page 4.", "typical"),
     ]),
    ("stocrete-ts-108", "StoCrete TS 108", "sprayed-mortar",
     "Sprayed cementitious structural repair mortar, not ready-mix concrete.",
     ["TS 108", "sprayed concrete", "shotcrete", "repair mortar"], "StoCrete TS 108", "stocrete-ts-108", [
         ("density", "2.1", 1, "Bulk density of fresh mortar", "EN 1015-6", 1000, "kg/dm³", "Fresh mortar, not hardened.", "typical"),
         ("compressive_strength", "74", 1, "Compressive strength (28 days)", "EN 12190", *MPA, AGE, "typical"),
         ("youngs_modulus", "27", 1, "Static modulus of elasticity (28 days)", "EN 13412", *GPA, AGE, "typical"),
         ("flexural_strength", "9", 1, "Flexural strength (28 days)", "TP BE SPCC", *MPA, AGE, "typical"),
     ]),
    ("stocrete-rm-f", "StoCrete RM F", "repair-mortar",
     "Cementitious structural repair mortar, not ready-mix concrete.",
     ["RM F", "repair mortar"], "StoCrete RM F", "stocrete-rm-f", [
         ("density", "2.0", 1, "Bulk density of fresh mortar", "EN 1015-6", 1000, "kg/dm³", "Fresh mortar, not hardened.", "typical"),
         ("compressive_strength", "40–50", 1, "Compressive strength (28 days)", "EN 12190", *MPA, AGE, "typical"),
         ("youngs_modulus", "22–26", 1, "Static modulus of elasticity (28 days)", "EN 13412", *GPA, AGE, "typical"),
         ("flexural_strength", "7–9", 1, "Flexural strength (28 days)", "TP BE-PCC", *MPA, AGE, "typical"),
     ]),
    ("stocrete-sm", "StoCrete SM", "repair-mortar",
     "Polymer-modified quick repair mortar, not ready-mix concrete.",
     ["SM", "repair mortar"], "StoCrete SM", "stocrete-sm", [
         ("density", "1.9", 1, "Bulk density of fresh mortar", "EN 1015-6", 1000, "kg/dm³", "Fresh mortar, not hardened.", "typical"),
         ("compressive_strength", "28", 1, "Compressive strength (28 days)", "EN 12190", *MPA, AGE, "typical"),
         ("youngs_modulus", "11", 1, "Static modulus of elasticity (28 days)", "EN 13412", *GPA, AGE, "typical"),
         ("flexural_strength", "6", 1, "Flexural strength (28 days)", "TP BE-PCC", *MPA, AGE, "typical"),
     ]),
    ("sikaemaco-488-ci", "SikaEmaco-488 CI", "repair-mortar",
     "Sprayable structural repair mortar, not ready-mix concrete.",
     ["488 CI", "repair mortar", "MasterEmaco"], "SikaEmaco-488 CI", "sikaemaco-488-ci", [
         ("density", "2,275", 1, "Density", "Sika data sheet; method not stated", 1, "kg/m³", "Sheet does not say fresh or hardened.", "typical"),
         ("compressive_strength", "62.1", 2, "Compressive Strength, 28 day", "ASTM C 109", *MPA, AGE, "typical"),
         ("youngs_modulus", "5.0", 2, "Modulus of Elasticity in Compression", "ASTM C 469", MSI, "10⁶ psi", AGE, "typical"),
         ("flexural_strength", "9.0", 2, "Flexural Strength, 28 day", "Sika data sheet", *MPA, AGE, "typical"),
     ]),
    ("sika-monotop-112", "Sika MonoTop-112 MultiUse Repair", "repair-mortar",
     "Multi-use cementitious repair mortar, not ready-mix concrete.",
     ["MonoTop 112", "repair mortar"], "Sika MonoTop-112", "sika-monotop-112", [
         ("density", "2.05", 1, "Fresh mortar density", "Sika data sheet; method not stated", 1000, "kg/l", "Fresh mortar, printed as approximate.", "typical"),
         ("compressive_strength", "50", 1, "Compressive Strength", "EN 12190", *MPA, "28 days, printed as approximate.", "typical"),
         ("youngs_modulus", "15.7", 1, "Modulus of Elasticity in Compression", "EN 13412", *GPA, "Printed as approximate.", "typical"),
     ]),
    ("sikaquick-pro-1000", "SikaQuick Pro 1000", "repair-mortar",
     "Rapid horizontal repair mortar, not ready-mix concrete. The sheet gives no material density.",
     ["SikaQuick 1000", "repair mortar", "rapid repair"], "SikaQuick Pro 1000", "sikaquick-pro-1000", [
         ("compressive_strength", "48.3", 2, "Compressive Strength, 28 days", "Sika data sheet", *MPA, AGE, "typical"),
         ("youngs_modulus", "32", 2, "Modulus of Elasticity in Compression, 28 days", "ASTM C 469", *GPA, AGE, "typical"),
         ("flexural_strength", "6.9", 2, "Flexural Strength, 28 days", "Sika data sheet", *MPA, AGE, "typical"),
     ]),
    ("sikacrete-650-tecfast", "Sikacrete-650 Tecfast", "repair-concrete",
     "Rapid-hardening cementitious repair concrete, class R4.",
     ["Sikacrete 650", "Tecfast", "repair concrete"], "Sikacrete-650 Tecfast", "sikacrete-650-tecfast", [
         ("density", "2350", 2, "Density", "Sika data sheet; method not stated", 1, "kg/m³", "Hardened density at 28 days, printed as approximate.", "typical"),
         ("compressive_strength", "85", 2, "Compressive Strength, 28 Days", "EN 1504-3 class R4", *MPA, "Printed as >85 MPa at +5, +20 and +30 °C.", "lower_bound"),
         ("youngs_modulus", "36.1", 2, "Modulus of Elasticity in Compression", "EN 13412", *GPA, AGE, "typical"),
     ]),
    ("flexcrete-monolite", "Flexcrete Monolite", "lightweight-mortar",
     "Lightweight cementitious repair mortar, not ready-mix concrete.",
     ["Monolite", "lightweight repair mortar"], "Monolite", "flexcrete-monolite", [
         ("density", "1250", 1, "Mixed Density", "Flexcrete data sheet; method not stated", 1, "kg/m³", "Mixed, at 0.16 water to powder ratio.", "typical"),
         ("compressive_strength", "30.0", 1, "Compressive Strength, 28 days", "BS 4551", *MPA, "28 days at 20 °C and 65% RH.", "typical"),
         ("youngs_modulus", "11.5", 1, "Young's Modulus of Elasticity, 28 days", "BS 1881-121", 1e9, "kN/mm²", AGE, "typical"),
         ("flexural_strength", "5.1", 1, "Flexural Strength, 28 days", "BS 4551", *MPA, "28 days at 20 °C and 65% RH.", "typical"),
     ]),
    ("emer-patch-repair-40", "Emer-Patch Repair 40", "lightweight-mortar",
     "Lightweight patch repair mortar, not ready-mix concrete.",
     ["Patch Repair 40", "repair mortar"], "Emer-Patch Repair 40", "emer-patch-repair-40", [
         ("density", "1780", 1, "Fresh Wet Density", "Emer data sheet; method not stated", 1, "kg/m³", "Fresh wet, not hardened.", "typical"),
         ("compressive_strength", "35", 1, "Compressive strength", "Emer data sheet", *MPA, AGE, "typical"),
         ("youngs_modulus", "18.4", 1, "Elastic Modulus", "Emer data sheet", *GPA, "Age not stated for this row.", "typical"),
         ("flexural_strength", "5.8", 1, "Flexural Strength", "Emer data sheet", *MPA, AGE, "typical"),
         ("tensile_strength", "3.1", 1, "Tensile Strength", "Emer data sheet", *MPA, AGE, "typical"),
     ]),
] + [
    (f"forton-gfrc-{slug}", f"Forton VF-774 GFRC, {label}", "gfrc",
     "Glass-fibre reinforced concrete with VF-774 acrylic polymer. Typical ranges; the bulletin says each producer must test its own composite.",
     ["GFRC", "GRC", "glass fiber reinforced concrete", "glass fibre reinforced concrete"], "Forton VF-774", "forton-vf-774", [
         ("density", rho, 1, f"Density (Dry), {label}", "Forton bulletin; method not stated", PCF, "pcf", "Dry density.", "typical"),
         ("compressive_strength", comp, 1, f"Compressive Strength (Edgewise), {label}", "Forton bulletin; method not stated", PSI, "psi", "Edgewise.", "typical"),
         ("youngs_modulus", mod, 1, f"Modulus of Elasticity, {label}", "Forton bulletin; method not stated", MSI, "10⁶ psi", "Listed under flexural properties.", "typical"),
         ("flexural_strength", flex, 1, f"Flexural Ultimate Strength (FU), {label}", "Forton bulletin; method not stated", PSI, "psi", "Ultimate, not yield.", "typical"),
     ])
    for slug, label, rho, comp, mod, flex in [
        ("premix", "premix", "110–130", "6,000–9,000", "1.0–2.9", "1,450–2,000"),
        ("spray-up", "spray-up", "120–140", "7,000–12,000", "1.0–3.0", "2,000–3,500"),
    ]
]


def import_concrete(source_dir: Path, records: list, sources: list, manifest: list) -> None:
    """Append reviewed facts; require every original to match its checked hash."""
    for sid, title, publisher, url, filename, digest, pages, revision, source_type in DOCUMENTS:
        path = source_dir / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"{filename}: source differs from the reviewed snapshot")
        manifest.append({"id": sid, "url": url, "filename": filename, "sha256": digest,
                         "bytes": path.stat().st_size, "pages": pages, "retrieved_date": DATE})
        sources.append({"id": sid, "title": title, "organization": publisher, "source_type": source_type,
                        "publication_date": None, "revision": revision, "url": url, "retrieved_date": DATE,
                        "license": "Selected numerical facts with attribution. Source document not redistributed.",
                        "notes": "See concrete-2026-10-batch-review.md for scope, exclusions, and conversions.",
                        "sha256": digest})
    records.append(record("concretes", "Concrete", "family", None, ["concrete"],
                          "Concretes and cementitious mortars with source-specific property observations.",
                          aliases=["concrete", "concretes", "cement", "mortar", "mortars"]))
    for rid, name, subfamily, description, aliases, supplier, sid, rows in MATERIALS:
        values = []
        for prop, raw, page, row, method, scale, unit, note, basis in rows:
            lower = basis == "lower_bound"
            value = obs(prop, raw, sid, page, name, row, method=method, basis="typical", factor=scale,
                        raw_unit=unit, conditions={"material_state": note})
            if lower:
                value["result_kind"] = "lower_bound"
            values.append(value)
        pair(records, rid, name, "concretes", ["concrete", subfamily], description, values,
             aliases=aliases, designations={"Supplier": supplier})


def main() -> None:
    """Rebuild only this batch, preserving every earlier curated record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    records, sources, documents = [], [], []
    import_concrete(args.source_dir, records, sources, documents)
    grades = [row for row in records if row["record_type"] == "grade"]
    ledger = {
        "date": DATE,
        "added_materials": len(grades),
        "added_observations": sum(len(row["observations"]) for row in records),
        "material_ids": [row["id"] for row in grades],
        "authored_ids": [row["id"] for row in records],
        "source_ids": [row["id"] for row in sources],
        "excluded": [
            {"id": "koster-repair-mortar-r4", "reason": "The sheet prints two different moduli (at least 20 GPa and above 15,000 N/mm²)."},
            {"id": "quikrete-and-rapid-set-mixes", "reason": "Reachable sheets give compressive strength but no density or modulus, so a single value cannot plot."},
            {"id": "normal-structural-concrete", "reason": "No reachable producer sheet or free standard gives density, modulus and strength together."},
        ],
    }
    for filename, key, additions in [("materials", "materials", records),
                                     ("sources", "sources", sources),
                                     ("reference-manifest", "documents", documents)]:
        path = ROOT / "curated" / (filename + ".json")
        data = json.loads(path.read_text())
        remaining = {row["id"]: row for row in additions}
        data[key] = [remaining.pop(row["id"], row) for row in data[key]] + list(remaining.values())
        if key == "documents":
            data["retrieved_date"] = max(data.get("retrieved_date", DATE), DATE)
        text = json.dumps(data, ensure_ascii=key == "documents", indent=2) + "\n"
        if args.check:
            if path.read_text() != text:
                raise ValueError(f"{filename}: differs from the reviewed batch")
        else:
            path.write_text(text)
    path = ROOT / "curated" / LEDGER
    text = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if path.read_text() != text:
            raise ValueError(f"{LEDGER}: differs from the reviewed batch")
    else:
        path.write_text(text)
    print(f"{'Checked' if args.check else 'Applied'} {len(grades)} new materials and {ledger['added_observations']} observations.")


if __name__ == "__main__":
    main()
