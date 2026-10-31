"""Reviewed October 2026 additions for materials the Ashby chart was missing.

The tables below are numerical transcriptions of the pinned sources; the batch
review says how each was read. Every earlier curated record stays byte-for-byte: an
existing grade gains values through a new reference record beside it. Normal
site builds use curated JSON. See docs/chart-staples-2026-10-batch-review.md.
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

DATE = "2026-10-30"
LEDGER = "chart-staples-2026-10.json"
PSI = 6894.757293168
KSI = PSI * 1e3
THOUSAND_KSI = KSI * 1e3
MSI = PSI * 1e6
LB_PER_IN3 = 27679.9047102
INCH = 0.0254
MIL = "mil-hdbk-5j"
MIL_NOTE = "Room-temperature design table; A, B and S bases retain their handbook meaning."

# id, title, publisher, URL, filename, SHA256, page count, revision, source type
DOCUMENTS = [
    (MIL, "Metallic Materials and Elements for Aerospace Vehicle Structures (MIL-HDBK-5J)",
     "US Department of Defense",
     "https://everyspec.com/MIL-HDBK/MIL-HDBK-0001-0099/download.php?spec=MIL_HDBK_5J.139.pdf",
     "mil-hdbk-5j.pdf", "8df08dfbb6bb50e590b9f290963424ce92a8533aec19a50f45bb9fbfb54cc79d",
     1733, "31 January 2003; cancelled, succeeded by MMPDS", "government_handbook"),
    ("schott-borofloat-33", "BOROFLOAT 33 technical data sheet", "SCHOTT",
     "https://www.edmundoptics.com/ViewDocument/schott-borofloat-technical-data-sheet-english.pdf",
     "schott-borofloat-33.pdf", "52591e4aaf8bb75ade427c6e2df5a17317883ca69bee8d197cefaadc110291b7",
     1, "Undated; retrieved 2026-10-30", "manufacturer_datasheet"),
    ("pilkington-ats-129", "ATS-129: Properties of Soda-Lime Silica Float Glass", "Pilkington North America",
     "https://www.pilkington.com/-/media/pilkington/site-content/usa/window-manufacturers/technical-bulletins/ats-129---properties-of-soda-lime-silica-float-glass.pdf",
     "pilkington-ats-129.pdf", "522bcd3755480e473b98541cc8de38062a6fccc21a57fae4f6d2e37a7a6035dd",
     4, "Undated; retrieved 2026-10-30", "manufacturer_datasheet"),
    ("arkema-plexiglas-g", "Plexiglas G Acrylic Sheet brochure", "Altuglas International, Arkema",
     "https://www.alro.com/dataPDF/Plastics/PlasticsBrochures/Brochure_PlexiglasG.pdf",
     "arkema-plexiglas-g.pdf", "b54cececc027f5d5b86b7f988f4a7af9f04b01394545d6f991b97e4f385c1525",
     2, "Adv#20120-7/02/3m-GI, 2002", "manufacturer_datasheet"),
    ("ensinger-tecafine-hdpe", "TECAFINE HDPE natural product page", "Ensinger",
     "https://www.ensingerplastics.com/en-us/shapes/polyethylene-tecafine-hdpe-natural",
     "ensinger-tecafine-hdpe.html", "6e89b79523a23f2d17108505e17fd8e23972974e9c04f67e134f13ffec2aa370",
     None, "Web page retrieved 2026-10-30", "manufacturer_datasheet"),
    ("vectorply-e-ltm-1808", "E-LTM 1808 fabric data sheet", "Vectorply",
     "https://www.rockwestcomposites.com/downloads/E-LTM-1808.pdf",
     "vectorply-e-ltm-1808.pdf", "ff7fc55c303d72183379fc3eb09b9fb57027c084455e7ef5c3bda33dc0cf9dca",
     2, "Undated; retrieved 2026-10-30", "manufacturer_datasheet"),
    ("elgin-1018", "Carbon Steel Grade 1018 Data Sheet", "Elgin Fastener Group",
     "https://www.mwcomponents.com/uploads/Resource-Center/Elgin-Material-Sheets/Carbon-Steel-Grade-1018-Data-Sheet_Elgin.pdf",
     "elgin-1018.pdf", "a3c9a832aa991c3322fd1bc2e5fa8f5935338b4ed0cdf0483010e94887a6278b",
     2, "Undated; retrieved 2026-10-30", "supplier_catalog"),
    ("elgin-8620", "Alloy Steel Grade 8620 Fact Sheet", "Elgin Fastener Group",
     "https://www.mwcomponents.com/uploads/Resource-Center/Elgin-Material-Sheets/Alloy-Steel-Grade-8620-Fact-Sheet_Elgin-Website.pdf",
     "elgin-8620.pdf", "665a405fb0bd59192e3fc8ae8ca6c0c41342519d8ed43079ca5cb84443656ba9",
     2, "Undated; retrieved 2026-10-30", "supplier_catalog"),
] + [
    ("aalco-" + alloy.lower(), f"Aluminium Alloy {alloy} T6 Extrusions datasheet", "Aalco Metals",
     f"https://www.aalco.co.uk/datasheets/{page}.ashx", f"aalco-{alloy.lower()}-t6.html", digest,
     None, "Web page retrieved 2026-10-30", "supplier_catalog")
    for alloy, page, digest in [
        ("6005A", "Aluminium-Alloy-6005A-T6-Extrusion_157", "f5701885da7826f67fb6bdc1ffd63c7b20ebe608d6a0abef6370a5c93c5910fa"),
        ("6063", "Aluminium-Alloy-6063-T6-Extrusions_158", "3a5e4b465b2270d4dbebf16db364cdecaf8b57e80b541ea39d88b21d15c19157"),
        ("6082", "Aluminium-Alloy-6082-T6-Extrusions_338", "72c60a29166c8083410fcee557f7e16817a1131f8061e318b3bc7ba5a510f05d"),
        ("6262", "Aluminium-Alloy-6262-T6-Extrusions_156", "f8926974e236da9a9fe4263d0d477f4344b58911eac0b94126e7e486acc967e4"),
    ]
]

# id, name, parent, family, table, PDF page, printed page, E [10³ ksi],
# density [lb/in³], description, aliases, designations, state condition,
# form, thickness [in], orientation, ultimate [ksi], yield [ksi], column label.
MIL_METALS = [
    ("al-7075", "Aluminium 7075", "aluminium-alloys", ["metal", "aluminium-alloy"], "3.7.6.0(b1)", 673, "3-371",
     "10.3", "0.101", "Al-Zn-Mg-Cu wrought alloy. MIL-HDBK-5J sheet and plate design values.",
     ["7075", "AA7075", "7075-T6", "7075 aluminum"], {"AA": "7075", "UNS": "A97075"},
     "T6", "sheet", (0.040, 0.125), "L", "78", "70", "T6 and T62 sheet, 0.040-0.125 in, A basis"),
    ("al-2024", "Aluminium 2024", "aluminium-alloys", ["metal", "aluminium-alloy"], "3.2.3.0(b1)", 373, "3-71",
     "10.5", "0.100", "Al-Cu-Mg wrought alloy. MIL-HDBK-5J bare sheet design values.",
     ["2024", "AA2024", "2024-T3", "2024 aluminum"], {"AA": "2024", "UNS": "A92024"},
     "T3", "sheet", (0.010, 0.128), "L", "64", "47", "T3 sheet, 0.010-0.128 in, A basis"),
    ("al-5052", "Aluminium 5052", "aluminium-alloys", ["metal", "aluminium-alloy"], "3.5.1.0(b1)", 522, "3-220",
     "10.1", "0.097", "Al-Mg wrought alloy. MIL-HDBK-5J sheet and plate design values.",
     ["5052", "AA5052", "5052-H32", "5052 aluminum"], {"AA": "5052", "UNS": "A95052"},
     "H32", "sheet", (0.017, 2.000), "L", "31", "23", "H32 sheet and plate, 0.017-2.000 in, S basis"),
    ("mg-az31b", "Magnesium AZ31B", "magnesium-alloys", ["metal", "magnesium-alloy"], "4.2.1.0(b)", 841, "4-7",
     "6.5", "0.0639", "Mg-Al-Zn wrought alloy. MIL-HDBK-5J sheet and plate design values.",
     ["AZ31B", "AZ31", "AZ31B-H24", "AZ31B magnesium"], {"ASTM": "AZ31B", "UNS": "M11311"},
     "H24", "sheet", (0.016, 0.062), "L", "39", "29", "H24 sheet, 0.016-0.062 in, S basis"),
    ("inconel-718", "Inconel 718", "nickel-alloys", ["metal", "nickel-alloy"], "6.3.5.0(b)", 1092, "6-52",
     "29.4", "0.297", "Precipitation-hardened nickel alloy. MIL-HDBK-5J sheet and plate design values.",
     ["Alloy 718", "IN718", "718", "N07718", "Inconel 718"], {"UNS": "N07718", "Supplier": "Inconel 718"},
     "solution treated and aged", "sheet", (0.010, 0.187), "L", "180", "145", "Solution treated and aged sheet, 0.010-0.187 in, A basis"),
    ("inconel-625", "Inconel 625", "nickel-alloys", ["metal", "nickel-alloy"], "6.3.3.0(b)", 1075, "6-35",
     "29.8", "0.305", "Solid-solution nickel alloy. MIL-HDBK-5J annealed sheet and plate design values.",
     ["Alloy 625", "IN625", "625", "N06625", "Inconel 625"], {"UNS": "N06625", "Supplier": "Inconel 625"},
     "annealed", "sheet", (0.188, 0.250), "L", "119", "59", "Annealed sheet and plate, 0.188-0.250 in, S basis"),
    ("ti-cp-3", "Titanium commercially pure, composition CP-3", "titanium-alloys", ["metal", "titanium-alloy"], "5.2.1.0(c)", 900, "5-8",
     "15.5", "0.163", "Unalloyed titanium to AMS-T-81556 composition CP-3. MIL-HDBK-5J extruded bar and shape design values.",
     ["CP titanium", "commercially pure titanium", "CP-3", "unalloyed titanium"], {"AMS": "AMS-T-81556 CP-3"},
     "annealed", "extrusion", (0.188, 3.000), "L", "50", "40", "Comp. CP-3 annealed extruded bars and shapes, 0.188-3.000 in, S basis"),
    ("stainless-17-4ph", "Stainless steel 17-4PH", "stainless-steels", ["metal", "steel", "stainless-steel", "precipitation-hardening"], "2.6.9.0(b)", 251, "2-197",
     "28.5", "0.282", "Precipitation-hardening stainless steel. MIL-HDBK-5J sheet, strip and plate design values; density is the H900 value.",
     ["17-4", "17-4 PH", "17-4PH", "630", "S17400"], {"UNS": "S17400", "AISI": "630"},
     "H900", "sheet", None, "LT", "190", "170", "H900 sheet, strip and plate, up to 4.000 in, S basis"),
]

# Existing grade, MIL table, PDF page, printed page, E [10³ ksi], density [lb/in³].
MIL_EXISTING = [
    ("al-6061", "Aluminium 6061", "3.6.2.0(b2)", 567, "3-265", "9.9", None, "6061 plate design table; E is listed for the alloy."),
    ("steel-atlas-4140", "Steel Atlas 4140", "2.3.1.0(g2)", 79, "2-25", "29.0", "0.283", "AISI 4140 quenched and tempered low-alloy steel; not an Atlas-published value."),
    ("steel-atlas-4340", "Steel Atlas 4340", "2.3.1.0(g2)", 79, "2-25", "29.0", "0.283", "AISI 4340 quenched and tempered low-alloy steel; not an Atlas-published value."),
]

# Existing Hydro-sourced grade, alloy label, Aalco modulus [GPa].
AALCO_MODULUS = [("al-6005a", "6005A", "70"), ("al-6063", "6063", "69.5"),
                 ("al-6082", "6082", "70"), ("al-6262", "6262", "68.3")]


def lb_per_in3(raw, sid, page, column, row, method, note):
    return obs("density", raw, sid, page, column, row, method=method, basis="reference",
               factor=LB_PER_IN3, raw_unit="lb/in³", conditions={"material_state": note})


def import_chart_staples(source_dir: Path, records: list, sources: list, manifest: list) -> None:
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
                        "notes": "See chart-staples-2026-10-batch-review.md for scope, exclusions, and conversions.",
                        "sha256": digest})
    records.append(record("magnesium-alloys", "Magnesium alloys", "family", "metals", ["metal", "magnesium-alloy"],
                          "Wrought magnesium alloys with source-specific property observations."))
    for rid, name, label in [("polymer-hdpe", "High-density polyethylene (HDPE)", "HDPE"),
                             ("polymer-pmma", "Polymethyl methacrylate (PMMA)", "PMMA")]:
        records.append(record(rid, name, "family", "engineering-plastics", ["polymer", label],
                              f"Supplier grades of {name.lower()}."))
    for (rid, name, parent, family, table, page, printed, modulus, density, description, aliases,
         designations, condition, form, thickness, orientation, ultimate, yield_, column) in MIL_METALS:
        method = f"MIL-HDBK-5J Table {table}"
        where = f"Table {table} (printed page {printed})"
        physical = [
            obs("youngs_modulus", modulus, MIL, page, where, "E", method=method, basis="reference",
                factor=THOUSAND_KSI, raw_unit="10³ ksi", conditions={"material_state": MIL_NOTE}),
            lb_per_in3(density, MIL, page, where, "density", method, MIL_NOTE),
        ]
        pair(records, rid, name, parent, family, description, physical, aliases=aliases, designations=designations)
        conditions = {"product_form": form, "orientation": orientation}
        if thickness:
            conditions["thickness_m"] = [round(limit * INCH, 7) for limit in thickness]
        mechanical = [
            obs(prop, raw, MIL, page, f"{where}, {column}", label, method=method, basis="minimum",
                factor=KSI, raw_unit="ksi", conditions=dict(conditions, material_state=column + "."))
            for prop, raw, label in [("tensile_strength", ultimate, f"Ftu {orientation}"),
                                     ("yield_strength", yield_, f"Fty {orientation}")]
        ]
        records.append(record(f"{rid}-{condition.split()[0].lower()}", f"{name} {condition}", "variant", rid, family,
                              description, aliases=aliases, condition=condition, observations=mechanical,
                              designations=designations))
    # A plain carbon steel with no named state, so its annealed limits stay in a note.
    method = "MIL-HDBK-5J Table 2.2.1.0(b)"
    where = "Table 2.2.1.0(b) (printed page 2-8)"
    note = "Annealed sheet, strip and plate, S basis."
    pair(records, "steel-aisi-1025", "Steel AISI 1025", "carbon-steels", ["metal", "steel"],
         "Plain carbon steel. MIL-HDBK-5J design values.",
         [obs("youngs_modulus", "29.0", MIL, 62, where, "E", method=method, basis="reference",
              factor=THOUSAND_KSI, raw_unit="10³ ksi", conditions={"material_state": MIL_NOTE}),
          lb_per_in3("0.284", MIL, 62, where, "density", method, MIL_NOTE),
          obs("tensile_strength", "55", MIL, 62, where, "Ftu L", method=method, basis="minimum", factor=KSI,
              raw_unit="ksi", conditions={"product_form": "sheet", "orientation": "L", "material_state": note}),
          obs("yield_strength", "36", MIL, 62, where, "Fty L", method=method, basis="minimum", factor=KSI,
              raw_unit="ksi", conditions={"product_form": "sheet", "orientation": "L", "material_state": note})],
         aliases=["1025", "AISI 1025", "G10250"], designations={"AISI": "1025", "UNS": "G10250"})
    # Existing grades gain grade-level values through a new record beside them.
    for rid, name, table, page, printed, modulus, density, note in MIL_EXISTING:
        where, method = f"Table {table} (printed page {printed})", f"MIL-HDBK-5J Table {table}"
        values = [obs("youngs_modulus", modulus, MIL, page, where, "E", method=method, basis="reference",
                      factor=THOUSAND_KSI, raw_unit="10³ ksi", conditions={"material_state": note})]
        if density:
            values.append(lb_per_in3(density, MIL, page, where, "density", method, note))
        records.append(record(rid + "-staples", name + " — handbook physical reference", "variant", rid,
                              existing_family(rid), "Grade-level physical values from MIL-HDBK-5J.",
                              condition="supplier reference state", observations=values))
    for rid, alloy, modulus in AALCO_MODULUS:
        sid = "aalco-" + alloy.lower()
        values = [obs("youngs_modulus", modulus, sid, 1, f"Aluminium Alloy {alloy} T6 datasheet, Properties", "Modulus of Elasticity",
                      method="Supplier physical property table; test method not stated", basis="reference", factor=1e9, raw_unit="GPa",
                      conditions={"material_state": "Aalco lists this as a physical property of the alloy."})]
        values[0]["source_locator"] = f"Web datasheet, Aluminium Alloy {alloy} T6, Properties table, Modulus of Elasticity"
        records.append(record(rid + "-staples", f"Aluminium {alloy} — supplier physical reference", "variant", rid,
                              existing_family(rid), "Grade-level elastic modulus from a supplier datasheet.",
                              condition="supplier reference state", observations=values))
    method = "Elgin data sheet; test method not stated"
    records.append(record("steel-atlas-8620h-staples", "Steel Atlas 8620H — supplier physical reference", "variant",
                          "steel-atlas-8620h", existing_family("steel-atlas-8620h"),
                          "Grade-level physical values for AISI 8620 from a supplier fact sheet.",
                          condition="supplier reference state", observations=[
        obs("youngs_modulus", "205", "elgin-8620", 2, "AISI 8620, normalized, 13 mm round", "Modulus of Elasticity", method=method,
            basis="reference", factor=1e9, raw_unit="GPa",
            conditions={"material_state": "AISI 8620, not an Atlas value. The sheet labels this typical for steel."}),
        obs("density", "7.85", "elgin-8620", 1, "AISI 8620, normalized, 13 mm round", "Density", method=method,
            basis="reference", factor=1000, raw_unit="g/cc",
            conditions={"material_state": "AISI 8620, not an Atlas value."}),
    ]))
    pair(records, "steel-aisi-1018", "Steel AISI 1018", "carbon-steels", ["metal", "steel"],
         "Low-carbon steel. Supplier sheet for cold drawn AISI 1018.",
         [obs("density", "7.87", "elgin-1018", 1, "AISI 1018 Steel, cold drawn", "Density", method=method, basis="reference", factor=1000, raw_unit="g/cc"),
          obs("youngs_modulus", "200", "elgin-1018", 2, "AISI 1018 Steel, cold drawn", "Modulus of Elasticity", method=method, basis="reference", factor=1e9, raw_unit="GPa")],
         aliases=["1018", "AISI 1018", "G10180", "C1018"], designations={"AISI": "1018", "UNS": "G10180"})
    records.append(record("steel-aisi-1018-cold-drawn", "Steel AISI 1018 — cold drawn", "variant", "steel-aisi-1018", ["metal", "steel"],
                          "Low-carbon steel. Supplier sheet for cold drawn AISI 1018.",
                          aliases=["1018", "AISI 1018"], condition="cold drawn",
                          designations={"AISI": "1018", "UNS": "G10180"}, observations=[
        obs("tensile_strength", "440", "elgin-1018", 1, "AISI 1018 Steel, cold drawn", "Tensile Strength, Ultimate", method=method, basis="typical",
            factor=1e6, raw_unit="MPa", conditions={"material_state": "Cold drawn; supplier sheet does not state a size."}),
        obs("yield_strength", "370", "elgin-1018", 1, "AISI 1018 Steel, cold drawn", "Tensile Strength, Yield", method=method, basis="typical",
            factor=1e6, raw_unit="MPa", conditions={"material_state": "Cold drawn; supplier sheet does not state a size."}),
    ]))
    pair(records, "ensinger-tecafine-hdpe", "TECAFINE HDPE natural", "polymer-hdpe", ["polymer", "HDPE"],
         "Ensinger high-density polyethylene stock shape.",
         web_rows("ensinger-tecafine-hdpe", "TECAFINE HDPE natural", "Ensinger product page; ASTM method not repeated per row", [
             ("density", "0.95", "Density", 1000, "g/cm³"),
             ("youngs_modulus", "140,000", "Modulus of elasticity (tensile test)", PSI, "psi"),
             ("yield_strength", "3,700", "Tensile strength at yield", PSI, "psi")]),
         aliases=["HDPE", "high-density polyethylene", "TECAFINE HDPE"], designations={"Supplier": "TECAFINE HDPE", "Polymer": "HDPE"})
    page2 = "Average Physical Properties of Plexiglas G"
    method = "Plexiglas G brochure; ASTM method as printed"
    pair(records, "arkema-plexiglas-g", "Plexiglas G", "polymer-pmma", ["polymer", "PMMA"],
         "Cast acrylic sheet. Brochure values are averages at 0.236 in nominal thickness, not for specification.",
         [obs("density", "1.19", "arkema-plexiglas-g", 2, page2, "Specific gravity (D792)", method=method, factor=1000, raw_unit="specific gravity"),
          obs("youngs_modulus", "450,000", "arkema-plexiglas-g", 2, page2, "Tensile modulus of elasticity (D638)", method=method, factor=PSI, raw_unit="psi"),
          obs("tensile_strength", "10,500", "arkema-plexiglas-g", 2, page2, "Tensile strength, maximum (D638)", method=method, factor=PSI, raw_unit="psi"),
          obs("flexural_strength", "16,000", "arkema-plexiglas-g", 2, page2, "Flexural strength, maximum (D790)", method=method, factor=PSI, raw_unit="psi"),
          obs("flexural_modulus", "450,000", "arkema-plexiglas-g", 2, page2, "Flexural modulus of elasticity (D790)", method=method, factor=PSI, raw_unit="psi"),
          obs("elongation_at_break", "4.9", "arkema-plexiglas-g", 2, page2, "Elongation, rupture (D638)", method=method),
          obs("poissons_ratio", "0.35", "arkema-plexiglas-g", 2, page2, "Poisson's ratio", method=method)],
         aliases=["PMMA", "acrylic", "cast acrylic", "Plexiglas", "Plexiglass"], designations={"Supplier": "Plexiglas G", "Polymer": "PMMA"})
    column = "E-LTM 1808 resin infused, vinyl ester"
    note = ("0°/90° biaxial E-glass with chopped mat, 66% fiber by weight. The sheet's disclaimer "
            "warns that laminate values may be computer-generated predictions.")
    method = "Vectorply laminate table; test method not stated"
    pair(records, "vectorply-e-ltm-1808", "Vectorply E-LTM 1808 E-glass laminate", "composites", ["composite", "biaxial-glass-vinyl-ester"],
         "E-glass fabric laminate (GFRP) with supplier-listed properties. Laminate values may be predicted rather than tested.",
         [obs("density", "1.84", "vectorply-e-ltm-1808", 1, column, "Density", method=method, factor=1000, raw_unit="g/cc", conditions={"material_state": note}),
          obs("youngs_modulus", "3.17", "vectorply-e-ltm-1808", 2, column, "Ex", method=method, factor=MSI, raw_unit="Msi", conditions={"orientation": "L", "material_state": note}),
          obs("tensile_strength", "52", "vectorply-e-ltm-1808", 2, column, "Long. Ten.", method=method, factor=KSI, raw_unit="ksi", conditions={"orientation": "L", "material_state": note})],
         aliases=["GFRP", "E-glass", "fiberglass", "glass fiber laminate", "E-LTM 1808"], designations={"Supplier": "E-LTM 1808"})
    records_glass = [
        ("schott-borofloat-33", "SCHOTT BOROFLOAT 33", ["glass", "borosilicate-glass"], "Floated borosilicate glass.",
         ["BOROFLOAT", "borosilicate glass", "borosilicate"], {"Supplier": "BOROFLOAT 33"}, [
             obs("density", "2.23", "schott-borofloat-33", 1, "BOROFLOAT 33", "Density (25 °C)", method="SCHOTT data sheet", basis="reference", factor=1000, raw_unit="g/cm³", conditions={"temperature_K": 298.15}),
             obs("youngs_modulus", "64", "schott-borofloat-33", 1, "BOROFLOAT 33", "Young's Modulus", method="DIN 13316", basis="reference", factor=1e9, raw_unit="kN/mm²"),
             obs("poissons_ratio", "0.2", "schott-borofloat-33", 1, "BOROFLOAT 33", "Poisson's Ratio", method="DIN 13316", basis="reference", factor=1, raw_unit="1"),
             obs("thermal_conductivity", "1.2", "schott-borofloat-33", 1, "BOROFLOAT 33", "Thermal conductivity (90 °C)", method="SCHOTT data sheet", basis="reference", conditions={"temperature_K": 363.15}),
         ]),
        ("pilkington-float-glass", "Pilkington soda-lime float glass", ["glass", "soda-lime-glass"], "Soda-lime silica float glass.",
         ["soda-lime glass", "soda lime glass", "float glass", "window glass"], {"Supplier": "Pilkington float glass"}, [
             obs("density", "2500", "pilkington-ats-129", 2, "ATS-129", "Density", method="Pilkington bulletin; method not stated", basis="reference", factor=1, raw_unit="kg/m³"),
             obs("youngs_modulus", "72", "pilkington-ats-129", 1, "ATS-129", "Modulus of Elasticity (Young's)", method="Pilkington bulletin; method not stated", basis="reference", factor=1e9, raw_unit="GPa"),
             obs("poissons_ratio", "0.22", "pilkington-ats-129", 1, "ATS-129", "Poisson's Ratio", method="Pilkington bulletin; method not stated", basis="reference", factor=1, raw_unit="1"),
             obs("thermal_conductivity", "0.937", "pilkington-ats-129", 2, "ATS-129", "Thermal Conductivity at 75 °F", method="Pilkington bulletin; method not stated", basis="reference", conditions={"temperature_K": 297.04}),
             obs("specific_heat", "0.88", "pilkington-ats-129", 2, "ATS-129", "Specific Heat at 75 °F", method="Pilkington bulletin; method not stated", basis="reference", factor=1000, raw_unit="kJ/(kg·°C)", conditions={"temperature_K": 297.04}),
         ]),
    ]
    for rid, name, family, description, aliases, designations, values in records_glass:
        pair(records, rid, name, "glasses", family, description, values, aliases=aliases, designations=designations)


def web_rows(sid, name, method, rows):
    """Build observations from one web table, whose locator has no page."""
    values = []
    for prop, raw, label, factor, unit in rows:
        value = obs(prop, raw, sid, 1, name, label, method=method, factor=factor, raw_unit=unit)
        value["source_locator"] = f"Web page, {name}, technical data, {label}"
        values.append(value)
    return values


def existing_family(rid):
    """Copy the classification of the grade a new reference record sits beside."""
    rows = json.loads((ROOT / "curated/materials.json").read_text())["materials"]
    return next(row["family"] for row in rows if row["id"] == rid)


def main() -> None:
    """Rebuild only this batch, preserving every earlier curated record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    records, sources, documents = [], [], []
    import_chart_staples(args.source_dir, records, sources, documents)
    grades = [row for row in records if row["record_type"] == "grade"]
    ledger = {
        "date": DATE,
        "added_materials": len(grades),
        "added_observations": sum(len(row["observations"]) for row in records),
        "material_ids": [row["id"] for row in grades],
        "authored_ids": [row["id"] for row in records],
        "extended_material_ids": [row["parent_id"] for row in records if row["id"].endswith("-staples")],
        "source_ids": [row["id"] for row in sources],
        "excluded": [
            {"id": "astm-a36", "reason": "No accessible document gives both a density and a modulus for A36; AISC and FHWA downloads were refused."},
            {"id": "other-existing-aluminium", "reason": "1060, 1100, 1350, 6005, 6042, 6101 and 6105: no reachable alloy-specific modulus in a primary or identified supplier table."},
            {"id": "other-existing-steels", "reason": "Atlas 1045, 1214FM, 12L14FM, M1020, M1030, 6580, 6582, 6587, 6657 and Micro900: no reachable grade-specific density and modulus. The Atlas handbook now sits behind a bot check."},
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
