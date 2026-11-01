"""Reviewed October 2026 batch from the gathered source documents.

The tables below are transcriptions of the documents pinned in
curated/gathered-2026-10-documents.json. Earlier records stay byte-for-byte: an
existing grade gains values through a new record beside it. Normal site builds
use curated JSON. See docs/gathered-2026-10-batch-review.md.
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
LEDGER = "gathered-2026-10.json"
PSI = 6894.757293168
KSI = PSI * 1e3
MSI = PSI * 1e6
PCF = 16.01846337
LB_PER_IN3 = 27679.9047102
MPA, GPA, GCC = (1e6, "MPa"), (1e9, "GPa"), (1000, "g/cm³")

# Compositions and strength bands in MN/RC 1998-11 Tables 7.3-A (dry) and 7.3-B
# (wet): band in MPa, band in psi, then {composition: (modulus psi, modulus GPa)}.
HSC_COMPOSITIONS = {"reference": "reference mix", "fly-ash": "fly ash", "silica-fume": "silica fume",
                    "fly-ash-silica-fume": "fly ash and silica fume"}
HSC_TABLES = {
    "dry": ("7.3-A", [
        ("41–55", "6000–8000", {"fly-ash": ("5935081", "40.93"), "fly-ash-silica-fume": ("4761277", "32.84")}),
        ("55–69", "8000–10000", {"reference": ("6229454", "42.96"), "fly-ash": ("6116327", "42.18"), "fly-ash-silica-fume": ("5574077", "38.44")}),
        ("69–83", "10000–12000", {"reference": ("6480240", "44.69"), "fly-ash": ("6046899", "41.70"), "silica-fume": ("5942101", "40.98"), "fly-ash-silica-fume": ("5805725", "40.04")}),
        ("83–97", "12000–14000", {"reference": ("6481006", "44.70"), "fly-ash": ("6671571", "46.01"), "silica-fume": ("6256218", "43.15"), "fly-ash-silica-fume": ("6002017", "41.39")}),
        ("97–110", "14000–16000", {"reference": ("6897061", "47.57"), "fly-ash": ("6699881", "46.21"), "silica-fume": ("6876352", "47.42"), "fly-ash-silica-fume": ("6793345", "46.85")}),
        ("110–124", "16000–18000", {"reference": ("6853158", "47.26"), "fly-ash": ("7129840", "49.17"), "silica-fume": ("6847908", "47.23"), "fly-ash-silica-fume": ("6971692", "48.08")}),
        ("124–138", "18000–20000", {"reference": ("7437487", "51.29"), "silica-fume": ("7288696", "50.27"), "fly-ash-silica-fume": ("7215740", "49.76")}),
    ]),
    "wet": ("7.3-B", [
        ("69–83", "10000–12000", {"reference": ("7149000", "49.30"), "fly-ash": ("6999200", "48.27")}),
        ("83–97", "12000–14000", {"reference": ("7547220", "52.05"), "fly-ash": ("7664104", "52.86"), "silica-fume": ("7039000", "48.54"), "fly-ash-silica-fume": ("7308667", "50.40")}),
        ("97–110", "14000–16000", {"reference": ("7518004", "51.85"), "fly-ash": ("7643564", "52.71"), "silica-fume": ("7641750", "52.70"), "fly-ash-silica-fume": ("7522631", "51.88")}),
        ("110–124", "16000–18000", {"reference": ("7754038", "53.48"), "fly-ash": ("8078583", "55.71"), "silica-fume": ("7659101", "52.82"), "fly-ash-silica-fume": ("7873020", "54.30")}),
        ("124–138", "18000–20000", {"silica-fume": ("7699161", "53.10")}),
    ]),
}

# ASM entry per existing aluminium grade: id, alloy, PDF page, printed page, GPa.
ASM_MODULUS = [("al-1060", "1060", 1, "62", "69"), ("al-1100", "1100", 2, "63", "69"),
               ("al-1350", "1350", 5, "66", "69"), ("al-6005", "6005", 40, "101", "69"),
               ("al-6101", "6101", 44, "105", "68.9")]

# ACP table columns: id, name, column, subfamily, E1 GPa, Xt MPa, Xc MPa, density.
ACP_LAMINATES = [
    ("acp-kevlar-ud-epoxy", "Kevlar / epoxy UD laminate", "Kevlar UD", "ud-aramid-epoxy", "75", "1300", "280", "1.4"),
    ("acp-kevlar-fabric-epoxy", "Kevlar / epoxy fabric laminate", "Kevlar Fabric", "woven-aramid-epoxy", "30", "480", "190", "1.4"),
    ("acp-eglass-ud-epoxy", "E-glass / epoxy UD laminate", "E glass UD", "ud-glass-epoxy", "40", "1000", "600", "1.9"),
    ("acp-eglass-fabric-epoxy", "E-glass / epoxy fabric laminate", "E glass Fabric", "woven-glass-epoxy", "25", "440", "425", "1.9"),
    ("acp-carbon-ud-epoxy", "Standard carbon / epoxy UD laminate", "Std CF UD", "ud-carbon-epoxy", "135", "1500", "1200", "1.6"),
    ("acp-carbon-fabric-epoxy", "Standard carbon / epoxy fabric laminate", "Std CF Fabric", "woven-carbon-epoxy", "70", "600", "570", "1.6"),
]


def row(prop, raw, sid, page, name, label, method, factor=None, unit=None, note="", basis="typical", kind=None, **conditions):
    """Build one observation, keeping its note and optional result kind."""
    if note:
        conditions["material_state"] = note
    value = obs(prop, raw, sid, page, name, label, method=method, basis=basis, factor=factor, raw_unit=unit, conditions=conditions)
    if kind:
        value["result_kind"] = kind
    return value


def existing_family(rid):
    """Copy the classification of the grade a new record sits beside."""
    rows = json.loads((ROOT / "curated/materials.json").read_text())["materials"]
    return next(r["family"] for r in rows if r["id"] == rid)


def import_gathered(source_dir: Path, records: list, sources: list, manifest: list) -> None:
    """Append reviewed facts; require every original to match its checked hash."""
    documents = json.loads((ROOT / "curated/gathered-2026-10-documents.json").read_text())
    for doc in documents:
        path = source_dir / doc["filename"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != doc["sha256"]:
            raise ValueError(f"{doc['filename']}: source differs from the reviewed snapshot")
        manifest.append({"id": doc["id"], "url": doc["url"], "filename": doc["filename"], "sha256": doc["sha256"],
                         "bytes": path.stat().st_size, "pages": doc["pages"], "retrieved_date": DATE})
        sources.append({"id": doc["id"], "title": doc["title"], "organization": doc["organization"],
                        "source_type": doc["source_type"], "publication_date": None, "revision": doc["revision"],
                        "url": doc["url"], "retrieved_date": DATE,
                        "license": "Selected numerical facts with attribution. Source document not redistributed.",
                        "notes": "See gathered-2026-10-batch-review.md for scope, exclusions, and conversions.",
                        "sha256": doc["sha256"]})
    records.append(record("fibers", "Fibers", "family", None, ["fiber"],
                          "Reinforcing fibers and yarns with source-specific property observations.",
                          aliases=["fiber", "fibers", "fibre", "fibres", "yarn", "aramid"]))
    for rid, name, label in [("polymer-ldpe", "Low-density polyethylene (LDPE)", "LDPE"),
                             ("polymer-ps", "Polystyrene (PS)", "PS"),
                             ("polymer-up", "Unsaturated polyester (UP)", "UP")]:
        records.append(record(rid, name, "family", "engineering-plastics", ["polymer", label],
                              f"Supplier grades of {name.lower()}."))
    _concrete(records)
    _metals(records)
    _plastics(records)
    _rubber(records)
    _aramid_and_laminates(records)
    web = {doc["id"] for doc in documents if doc["filename"].endswith(".html")}
    for rec in records:
        for value in rec["observations"]:
            if value["source_id"] in web:
                value["source_locator"] = value["source_locator"].replace("Page 1, ", "Web page, ", 1)


def _concrete(records):
    for moisture, (table, bands) in HSC_TABLES.items():
        for mpa, band_psi, cells in bands:
            for composition, (psi, gpa) in cells.items():
                if abs(int(psi) * PSI * 1e-9 - float(gpa)) > 0.03:
                    raise ValueError(f"Table {table} {band_psi} {composition}: {psi} psi does not match {gpa} GPa")
                label = HSC_COMPOSITIONS[composition]
                low = mpa.split("–")[0]
                name = f"High-strength concrete, {label}, {mpa} MPa, tested {moisture}"
                where = f"Table {table} (printed page 212)"
                note = (f"Average modulus of mixes in this strength level, 100 x 200 mm cylinders tested {moisture}. "
                        f"The strength is the level the mixes fall in, not a measured value. Printed {psi} psi.")
                pair(records, f"mndot-hsc-{composition}-{moisture}-{low}", name, "concretes",
                     ["concrete", "high-strength-concrete"],
                     "Laboratory high-strength concrete from a University of Minnesota study for MnDOT. Density is not reported for these groups.",
                     [row("compressive_strength", mpa, "mndot-1998-11", 244, where, f"Compressive strength level, {composition}",
                          "Report strength level", *MPA, note=f"Strength level {band_psi} psi.", kind="interval"),
                      row("youngs_modulus", gpa, "mndot-1998-11", 244, where, f"{band_psi} psi, {composition}",
                          "Report static modulus test", *GPA, note=note)],
                     aliases=["high strength concrete", "HSC", label],
                     designations={"Report": "MN/RC 1998-11"})


def _metals(records):
    # A36 draws on three documents, because no one reachable document has all of it.
    pair(records, "steel-astm-a36", "Steel ASTM A36", "carbon-steels", ["metal", "steel"],
         "Structural carbon steel. Modulus from AISC 360, strengths from SSAB plate data, density from a distributor.",
         [row("youngs_modulus", "29,000", "aisc-360-16", 29, "Symbols (printed page 16.1-xxvii)", "E, modulus of elasticity of steel",
              "AISC 360-16", KSI, "ksi", note="AISC value for structural steel, not specific to A36.", basis="reference"),
          row("density", "7.85", "bushwick-a36", 1, "A36 properties page", "Density", "Distributor page; method not stated", *GCC,
              note="Printed as approximate.", basis="reference"),
          row("yield_strength", "36", "ssab-a36", 1, "ASTM A36 tensile table", "Yield strength (min)", "ASTM A6", KSI, "ksi",
              basis="minimum", product_form="plate", orientation="LT", note="SSAB plate; tested transverse."),
          row("tensile_strength", "58–80", "ssab-a36", 1, "ASTM A36 tensile table", "Tensile strength", "ASTM A6", KSI, "ksi",
              basis="specified_range", kind="interval", product_form="plate", orientation="LT", note="SSAB plate; tested transverse.")],
         aliases=["A36", "ASTM A36", "A36 steel", "structural steel"], designations={"ASTM": "A36"})
    pair(records, "steel-c45", "Steel C45 (AISI 1045)", "carbon-steels", ["metal", "steel"],
         "Medium-carbon steel. Machining service datasheet that lists C45 and AISI 1045 as equivalents.",
         [row("density", "7.8", "weerg-c45", 1, "Steel C45", "Density", "Weerg datasheet; method not stated", *GCC, basis="reference"),
          row("youngs_modulus", "210", "weerg-c45", 1, "Steel C45", "Elastic modulus", "ISO 6892", *GPA, basis="reference"),
          row("tensile_strength", "650", "weerg-c45", 1, "Steel C45", "Tensile strength", "ISO 6892", *MPA),
          row("yield_strength", "460", "weerg-c45", 1, "Steel C45", "Yield strength", "ISO 6892", *MPA),
          row("elongation_at_break", "15", "weerg-c45", 1, "Steel C45", "Elongation at break", "ISO 6892"),
          row("thermal_conductivity", "40–45", "weerg-c45", 1, "Steel C45", "Thermal conductivity (20 °C)", "Weerg datasheet",
              kind="interval", temperature_K=293.15)],
         aliases=["C45", "C45E", "CK45", "1.1191", "AISI 1045 equivalent"], designations={"EN": "C45E"})
    pair(records, "stainless-440c", "Stainless steel 440C", "stainless-steels",
         ["metal", "steel", "stainless-steel", "martensitic"],
         "High-carbon martensitic stainless steel. Physical values only; the source lists no mechanical data for this grade.",
         [row("density", "0.275", "suppliersonline-440c", 1, "440C, Physical Data", "Density", "Supplier page; method not stated",
              LB_PER_IN3, "lb/in³", basis="reference"),
          row("youngs_modulus", "29", "suppliersonline-440c", 1, "440C, Physical Data", "Modulus of Elasticity Tension",
              "Supplier page; method not stated", MSI, "10⁶ psi",
              note="The page prints 29 with no unit. 10⁶ psi is inferred from the magnitude.", basis="reference")],
         aliases=["440C", "AISI 440C", "S44004"], designations={"AISI": "440C", "UNS": "S44004"})
    for rid, alloy, page, printed, gpa in ASM_MODULUS:
        records.append(record(rid + "-asm", f"Aluminium {alloy} — handbook physical reference", "variant", rid, existing_family(rid),
                              "Grade-level elastic modulus from the ASM Handbook.", condition="supplier reference state",
                              observations=[row("youngs_modulus", gpa, "asm-wrought-al", page, f"{alloy} entry (printed page {printed})",
                                                "Elastic modulus, tension", "ASM Handbook Volume 2", *GPA, basis="reference")]))


def _plastics(records):
    def exxon(rid, name, sid, values, aliases):
        pair(records, rid, name, "polymer-ldpe", ["polymer", "LDPE"], "ExxonMobil low-density polyethylene resin.", values,
             aliases=["LDPE", "low density polyethylene", *aliases], designations={"Supplier": name, "Polymer": "LDPE"})
    method = "ExxonMobil data sheet"
    exxon("exxon-ld-150013-ba", "ExxonMobil LD 150013.BA", "exxon-ld-150013", [
        row("density", "0.913", "exxon-ld-150013", 1, "LD 150013.BA", "Density", "ASTM D1505", *GCC),
        row("youngs_modulus", "100", "exxon-ld-150013", 1, "LD 150013.BA", "Tensile Modulus", "ISO 527-1/1A/1", *MPA),
        row("elongation_at_break", "470", "exxon-ld-150013", 1, "LD 150013.BA", "Tensile Strain at Break", "ISO 527-2/1A/50"),
    ], ["LD 150013"])
    exxon("exxon-ld-2119-ln", "ExxonMobil LD 2119.LN", "exxon-ld-2119", [
        row("density", "0.919", "exxon-ld-2119", 1, "LD 2119.LN", "Density", "ASTM D1505", *GCC),
        row("flexural_modulus", "210", "exxon-ld-2119", 1, "LD 2119.LN", "Flexural Modulus, 1% Secant", method, *MPA),
        row("yield_strength", "11", "exxon-ld-2119", 1, "LD 2119.LN", "Tensile Strength at Yield", method, *MPA),
        row("tensile_strength", "10", "exxon-ld-2119", 1, "LD 2119.LN", "Tensile Strength at Break", method, *MPA, note="At break, below yield."),
        row("elongation_at_break", "445", "exxon-ld-2119", 1, "LD 2119.LN", "Elongation at Break", method),
    ], ["LD 2119"])
    exxon("exxon-ld-33021-07", "ExxonMobil LD 33021.07", "exxon-ld-33021", [
        row("density", "0.921", "exxon-ld-33021", 1, "LD 33021.07", "Density", "ASTM D1505", *GCC),
        row("flexural_modulus", "240", "exxon-ld-33021", 1, "LD 33021.07", "Flexural Modulus, 1% Secant", method, *MPA),
        row("yield_strength", "13", "exxon-ld-33021", 1, "LD 33021.07", "Tensile Strength at Yield", method, *MPA),
        row("tensile_strength", "9.6", "exxon-ld-33021", 1, "LD 33021.07", "Tensile Strength at Break", method, *MPA, note="At break, below yield."),
        row("elongation_at_break", "94", "exxon-ld-33021", 1, "LD 33021.07", "Elongation at Break", method),
    ], ["LD 33021"])
    sid = "plastics-intl-ldpe"
    pair(records, "plastics-intl-ldpe", "Plastics International LDPE", "polymer-ldpe", ["polymer", "LDPE"],
         "Distributor LDPE stock shape.",
         [row("density", "57.39", sid, 1, "LDPE", "Density", "ASTM D-792", PCF, "lb/ft³"),
          row("yield_strength", "1,363", sid, 1, "LDPE", "Yield Point", "ASTM D-638", PSI, "psi"),
          row("tensile_strength", "1,943", sid, 1, "LDPE", "Tensile Break", "ASTM D-638", PSI, "psi"),
          row("elongation_at_break", "515", sid, 1, "LDPE", "Elongation at Break", "ASTM D-638"),
          row("youngs_modulus", "41,615", sid, 1, "LDPE", "Tensile Modulus", "ASTM D-638", PSI, "psi"),
          row("flexural_modulus", "28,565", sid, 1, "LDPE", "Flexural Modulus", "ASTM D-790", PSI, "psi"),
          row("flexural_strength", "1,175", sid, 1, "LDPE", "Flexural Strength", "ASTM D-790", PSI, "psi")],
         aliases=["LDPE", "low density polyethylene"], designations={"Supplier": "Plastics International LDPE", "Polymer": "LDPE"})
    sid = "styrolution-ps-158k"
    pair(records, "styrolution-ps-158k", "Styrolution PS 158K", "polymer-ps", ["polymer", "PS"],
         "INEOS Styrolution general purpose polystyrene.",
         [row("density", "1048", sid, 2, "PS 158K", "Density", "ISO 1183", 1, "kg/m³"),
          row("youngs_modulus", "3300", sid, 1, "PS 158K", "Tensile Modulus", "ISO 527", *MPA),
          row("yield_strength", "55", sid, 1, "PS 158K", "Tensile Stress at Yield, 23 °C", "ISO 527", *MPA, temperature_K=296.15),
          row("elongation_at_break", "3", sid, 1, "PS 158K", "Tensile Strain at Break, 23 °C", "ISO 527", temperature_K=296.15)],
         aliases=["GPPS", "polystyrene", "PS 158K"], designations={"Supplier": "Styrolution PS 158K", "Polymer": "PS"})
    for grade, sid, strength, flex, modulus, unit, factor, methods in [
        ("GP 125", "kumho-gp-125", "42", "57", "2,860", "MPa", 1e6, ("ISO 527", "ISO 178")),
        ("GP 125E", "kumho-gp-125e", "48", "72", "3,000", "MPa", 1e6, ("ISO 527", "ISO 178")),
        ("GP 125EB", "kumho-gp-125eb", "6,390", "10,224", "426,000", "psi", PSI, ("ASTM D638", "ASTM D790")),
        ("GP 150I", "kumho-gp-150i", "7,384", "12,638", "468,600", "psi", PSI, ("ASTM D638", "ASTM D790")),
    ]:
        density_method = "ISO 1183" if methods[0].startswith("ISO") else "ASTM D792"
        pair(records, sid, f"Kumho {grade}", "polymer-ps", ["polymer", "PS"],
             "Kumho Petrochemical general purpose polystyrene. Typical values; the sheet gives flexural, not tensile, modulus.",
             [row("density", "1.04", sid, 1, grade, "Density", density_method, *GCC),
              row("tensile_strength", strength, sid, 1, grade, "Tensile Strength", methods[0], factor, unit),
              row("elongation_at_break", "3.5", sid, 1, grade, "Elongation", methods[0]),
              row("flexural_strength", flex, sid, 1, grade, "Flexural Strength", methods[1], factor, unit),
              row("flexural_modulus", modulus, sid, 1, grade, "Flexural Modulus", methods[1], factor, unit)],
             aliases=["GPPS", "polystyrene", grade], designations={"Supplier": f"Kumho {grade}", "Polymer": "PS"})
    pair(records, "crystic-198", "Crystic 198", "polymer-up", ["polymer", "UP"],
         "Scott Bader heat and chemical resistant polyester, fully cured unfilled casting.",
         [row("density", "1.22", "crystic-198", 2, "Crystic 198, fully cured unfilled casting", "Specific Gravity at 25 °C", "BS 2782", 1000, "specific gravity", temperature_K=298.15),
          row("tensile_strength", "57", "crystic-198", 2, "Crystic 198, fully cured unfilled casting", "Tensile strength", "BS 2782", *MPA),
          row("youngs_modulus", "3700", "crystic-198", 2, "Crystic 198, fully cured unfilled casting", "Tensile modulus", "BS 2782", *MPA),
          row("elongation_at_break", "1.8", "crystic-198", 2, "Crystic 198, fully cured unfilled casting", "Elongation at break", "BS 2782")],
         aliases=["polyester resin", "unsaturated polyester", "Crystic"], designations={"Supplier": "Crystic 198", "Polymer": "UP"})
    for rid, name, strength, modulus, elongation, flex, flex_modulus in [
        ("polynt-norsodyne-h-16243", "Norsodyne H 16243", "40", "3475", "1.25", "115", "3770"),
        ("polynt-enydyne-c-65134", "Enydyne C 65134", "71", "3811", "2.53", "124", "3765"),
        ("polynt-distitron-3501-s", "Distitron 3501 S", "65", "4100", "2.0", "110", "4000"),
    ]:
        where = f"{name}, cured unreinforced resin"
        pair(records, rid, f"Polynt {name}", "polymer-up", ["polymer", "UP"],
             "Polynt polyester resin, cured and unreinforced. The sheet's only density is for the liquid resin, so none is recorded.",
             [row("tensile_strength", strength, rid, 1, where, "Tensile strength", "ISO 527", *MPA),
              row("youngs_modulus", modulus, rid, 1, where, "Tensile modulus", "ISO 527", *MPA),
              row("elongation_at_break", elongation, rid, 1, where, "Elongation at break", "ISO 527"),
              row("flexural_strength", flex, rid, 1, where, "Flexural strength", "ISO 178", *MPA),
              row("flexural_modulus", flex_modulus, rid, 1, where, "Flexural modulus", "ISO 178", *MPA)],
             aliases=["polyester resin", "unsaturated polyester", name], designations={"Supplier": name, "Polymer": "UP"})


def _rubber(records):
    family = ["elastomer", "natural-rubber"]
    aliases = ["natural rubber", "NR", "polyisoprene"]
    pair(records, "apso-nr-40-75-01", "APSOparts NR 40.75-01", "elastomers", family,
         "Natural rubber compound, 40 Shore A. Its printed 26% elongation is not recorded because it is implausible for this rubber.",
         [row("density", "0.98", "apso-nr-40-75-01", 1, "NR 40.75-01", "Density nominal", "DIN ISO 2781", *GCC, note="Printed as 0.98 ±0.03."),
          row("tensile_strength", "20.00", "apso-nr-40-75-01", 1, "NR 40.75-01", "Tensile strength", "ISO 37-1", *MPA)],
         aliases=aliases, designations={"Supplier": "NR 40.75-01"})
    pair(records, "apso-nr-60-01-02", "APSOparts NR 60.01-02", "elastomers", family,
         "Sulfur-cured natural rubber compound, 60 Shore A.",
         [row("density", "1.12", "apso-nr-60-01-02", 1, "NR 60.01-02", "Density nominal", "Supplier sheet; method not stated", *GCC, note="Printed as 1.12 ±0.05."),
          row("tensile_strength", "20.00", "apso-nr-60-01-02", 1, "NR 60.01-02", "Tensile strength", "ISO 37", *MPA),
          row("elongation_at_break", "500.00", "apso-nr-60-01-02", 1, "NR 60.01-02", "Elongation at break", "ISO 37")],
         aliases=aliases, designations={"Supplier": "NR 60.01-02"})
    pair(records, "tse-natural-rubber", "TSE natural rubber", "elastomers", family,
         "Generic natural rubber reference from a molder. Reinforced compound, durometer 30 to 100.",
         [row("density", "0.93", "tse-natural-rubber", 1, "Natural Rubber", "Specific Gravity", "Supplier sheet; method not stated", 1000, "specific gravity"),
          row("tensile_strength", "4,000", "tse-natural-rubber", 1, "Natural Rubber", "Tensile Strength", "Supplier sheet; method not stated", PSI, "psi",
              note="Printed as 4,000+.", kind="lower_bound"),
          row("elongation_at_break", "500", "tse-natural-rubber", 1, "Natural Rubber", "Elongation (% reinforced)", "Supplier sheet; method not stated")],
         aliases=aliases, designations={"Supplier": "TSE natural rubber"})


def _aramid_and_laminates(records):
    for rid, name, strength, modulus, elongation, literal in [
        ("kevlar-29", "Kevlar 29 yarn", "2,920", "70,500", "3.6", "10.2 x 10⁶ psi"),
        ("kevlar-49", "Kevlar 49 yarn", "3,000", "112,400", "2.4", "6.3 x 10⁶ psi, an error for 16.3 per Table II-2"),
    ]:
        where = "Table II-1 (printed page 5)"
        note = "Straight test on conditioned yarn. Dry fiber, not a laminate."
        pair(records, rid, name, "fibers", ["fiber", "aramid"],
             "DuPont para-aramid yarn, typical values. Not a product specification.",
             [row("density", "1.44", "kevlar-guide", 5, where, "Density", "DuPont guide; method not stated", *GCC),
              row("tensile_strength", strength, "kevlar-guide", 5, where, "Breaking Tenacity", "ASTM D885-85", *MPA, note=note),
              row("youngs_modulus", modulus, "kevlar-guide", 5, where, "Tensile Modulus", "ASTM D885-85", *MPA, note=f"{note} The psi row prints {literal}."),
              row("elongation_at_break", elongation, "kevlar-guide", 5, where, "Elongation at Break", "ASTM D885-85")],
             aliases=["Kevlar", "aramid", "para-aramid", "aramid fiber"], designations={"Supplier": name.removesuffix(" yarn")})
    for rid, name, column, subfamily, modulus, tension, compression, density in ACP_LAMINATES:
        ud = "UD" in column
        note = f"Epoxy, 120 °C cure, {'60' if ud else '50'}% fiber volume, dry, room temperature. Supplier reference table, not a guarantee of performance."
        pair(records, rid, f"ACP {name}", "composites", ["composite", subfamily],
             f"Generic {name} from a composites supplier's reference table. Not a specific product.",
             [row("density", density, "acp-composites", 2, column, "Density", "Reference table", *GCC),
              row("youngs_modulus", modulus, "acp-composites", 1, column, "Young's Modulus 0°", "Reference table", *GPA, note=note, orientation="L"),
              row("tensile_strength", tension, "acp-composites", 1, column, "Ult. Tensile Strength 0°", "Reference table", *MPA, note=note, orientation="L"),
              row("compressive_strength", compression, "acp-composites", 1, column, "Ult. Comp. Strength 0°", "Reference table", *MPA, note=note, orientation="L")],
             aliases=[name, "composite laminate"], designations={"Supplier": f"ACP {column}"})


def main() -> None:
    """Rebuild only this batch, preserving every earlier curated record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    records, sources, documents = [], [], []
    import_gathered(args.source_dir, records, sources, documents)
    grades = [r for r in records if r["record_type"] == "grade"]
    ledger = {
        "date": DATE,
        "added_materials": len(grades),
        "added_observations": sum(len(r["observations"]) for r in records),
        "material_ids": [r["id"] for r in grades],
        "authored_ids": [r["id"] for r in records],
        "extended_material_ids": [r["parent_id"] for r in records if r["id"].endswith("-asm")],
        "source_ids": [r["id"] for r in sources],
        "excluded": [
            {"id": "atlas-carbon-and-alloy-grades", "reason": "The Atlas handbook and 1045 sheet give no density or modulus for 1045, 1214FM, 12L14FM, M1020, M1030, 6580, 6582, 6587, 6657 or Micro900."},
            {"id": "al-6042-al-6105", "reason": "The ASM chapter has no 6105 entry and no 6042 modulus was found."},
            {"id": "mndot-mix-level-tables", "reason": "Appendix A and B per-mix tables are rotated scans. The averaged tables 7.3-A and 7.3-B were transcribed instead."},
            {"id": "concrete-density", "reason": "MN/RC 1998-11 reports no density for these groups, and none was calculated."},
            {"id": "polynt-density", "reason": "Polynt sheets give specific weight for the liquid resin only."},
            {"id": "fhwa-hif-16-002", "reason": "Confirms E = 29,000 ksi for structural steel but adds nothing beyond AISC 360."},
        ],
    }
    for filename, key, additions in [("materials", "materials", records),
                                     ("sources", "sources", sources),
                                     ("reference-manifest", "documents", documents)]:
        path = ROOT / "curated" / (filename + ".json")
        data = json.loads(path.read_text())
        remaining = {r["id"]: r for r in additions}
        data[key] = [remaining.pop(r["id"], r) for r in data[key]] + list(remaining.values())
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
