"""Reviewed September 2026 additions for six underrepresented material families.

The small tables below are numerical transcriptions of the pinned primary
sources, checked against rendered pages. They preserve supplier grades,
directions, test conditions, and source literals. No population envelopes,
rubber stiffness estimates, or inferred laminate densities are imported.
Run through import_reference_tables.py; normal site builds use curated JSON.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DATE = "2026-09-30"
# id, title, publisher, URL, filename, SHA256, page count, revision, source type
DOCUMENTS = [
    ("kyocera-materials-2026", "Fine ceramic materials comparison", "KYOCERA Fineceramics Europe",
     "https://www.kyocera-fineceramics.de/en/materials", "kyocera-materials-2026.html",
     "1356e2a8b134d4f6a3cec384f902b09dba2f6fe4b3b6cae69d2b9cc8ad6d2559", None, "2026 web table", "supplier_catalog"),
    ("smooth-on-reference", "Technical Reference Chart: Silicone and Urethane Rubber", "Smooth-On",
     "https://www.smooth-on.com/assets/pdf/Technical_Data_Charts.pdf", "smooth-on-reference.pdf",
     "a6a60e2fd9010af6d6e83550c99d51bdda15657000ccfaf32f5544ecf0b9395f", 7, "Undated; retrieved 2026-09-30", "manufacturer_datasheet"),
    ("diab-h", "Divinycell H technical data, SI", "Diab",
     "https://diab-media.azureedge.net/eyajkrhd/diab-divinycell-h-may-2026-rev26-si.pdf", "diab-h.pdf",
     "d4a108dd3be35da9fef378037ddbe92133a7e24b991f5098a3ed0a2882c6e4a4", 2, "Rev26, May 2026", "manufacturer_datasheet"),
    ("diab-f", "Divinycell F technical data, SI", "Diab",
     "https://diab-media.azureedge.net/uithsbmv/diab-divinycell-f-may-2026-rev-33-si.pdf", "diab-f.pdf",
     "c015b1f325e5e307de281ee0f5a95656a645d20e17c28508873361c640f4c091", 2, "Rev33, May 2026", "manufacturer_datasheet"),
    ("schott-optical-glass", "Optical Glass Datasheets", "SCHOTT",
     "https://media.schott.com/api/public/content/820eba3413cc4e788433a3751f8edba9?v=97b3ea2b&download=true", "schott-optical-glass.pdf",
     "ea4176dd19fc3dfaadd1554f3543eaa5bf1130772b7b81bdf821410d3262cbdb", 139, "2025 collection; individual sheet dates retained", "manufacturer_datasheet"),
    ("usda-wood-mechanical", "Wood Handbook, Chapter 5: Mechanical Properties of Wood", "USDA Forest Products Laboratory",
     "https://research.fs.usda.gov/download/treesearch/37427.pdf", "usda-wood-mechanical.pdf",
     "7f4b2a07f15f8eee6413b1432ef98963f0fd341a97aef770762bebc167f236a2", 46, "FPL-GTR-190 (2010), 2018 errata", "government_handbook"),
    ("usda-wood-handbook", "Wood Handbook: Wood as an Engineering Material", "USDA Forest Products Laboratory",
     "https://research.fs.usda.gov/download/treesearch/37440.pdf", "usda-wood-physical.pdf",
     "dec06ab1ad9c97fbb4092779cd5d367a4d7fc4e3585f00b9e65f18b080ada2ec", 509, "FPL-GTR-190 (2010)", "government_handbook"),
    ("toray-3900", "3900 Prepreg System", "Toray Composite Materials America",
     "https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf", "toray-3900.pdf",
     "b6c1a6aadd57fda50cc7beb936bd486feb06f937d5193f9baea03279998bd94b", 4, "Rev.7.30.2020", "manufacturer_datasheet"),
    ("toray-2511", "2511 Prepreg System", "Toray Composite Materials America",
     "https://www.toraycma.com/wp-content/uploads/2511-Prepreg-System.pdf", "toray-2511.pdf",
     "cce21221ee914198b4a4b73d32e69a888bb87a303e6e7b2f5ae60afc882433a7", 7, "Pinned supplier sheet", "manufacturer_datasheet"),
    ("toray-2700", "2700 Prepreg System", "Toray Composite Materials America",
     "https://www.toraycma.com/wp-content/uploads/2700-Prepreg-System-1.pdf", "toray-2700.pdf",
     "ea0d35f84b0f53106e580b9564146202122a223051f2c22736f3b0409d090531", 3, "Rev.9.1.2024", "manufacturer_datasheet"),
    ("hexcel-8552", "HexPly 8552, European product data sheet", "Hexcel",
     "https://www.hexcel.com/wp-content/uploads/2025/12/HexPly_8552_eu_DataSheet1.pdf", "hexcel-8552.pdf",
     "be8db3daa2ebc662842c09385a754995a4c2fcf5560d5c08c51120187fd51b14", 6, "2023", "manufacturer_datasheet"),
]

# Supplier product code, reinforcement, page, direction, density [g/cc],
# tensile modulus [GPa], tensile strength [MPa]. Only RTA columns are used.
COMPOSITES = {
    "toray-3900": [
        ("P2362W-19L", "T800S-24K UD", 2, "L", "1.54", "148", "3006"),
        ("FM6673G-37KL", "T830H-6K PW", 3, "L", "1.51", "69.0", "1034"),
        ("FJ6361F-30HT", "T400H-3K PW", 3, "LT", "1.51", "68.2", "848"),
    ],
    "toray-2511": [
        ("F6273C-11M", "T700S-12K PW", 2, "L", "1.51", "59.2", "1089"),
        ("P211AS-200", "T800S-24K UD", 3, "L", "1.54", "145", "2792"),
        ("FM6673G-11M", "T830H-6K PW", 4, "LT", "1.54", "68.2", "848"),
        ("P6111-200", "M46J UD", 4, "L", "1.52", "225", "1682"),
    ],
    "toray-2700": [
        ("F6273C-T2XM-965", "T700S-12K PW", 2, "LT", "1.504", "58.3", "1056"),
        ("FT6243R-T2XM-965", "T1100G-12K PW", 3, "LT", "1.515", "77.9", "1324"),
    ],
    "hexcel-8552": [
        ("8552-AS4", "AS4-12K UD", 2, "L", "1.58", "141", "2207"),
        ("8552-IM7", "IM7-12K UD", 2, "L", "1.57", "164", "2724"),
    ],
}

# Species, subgroup, page, source row, G12, MOR [kPa], bending MOE [MPa].
WOODS = [
    ("Red alder", "hardwood", 4, "Alder, red", "0.41", "68,000", "9,500"),
    ("White ash", "hardwood", 4, "Ash: White", "0.60", "106,000", "12,000"),
    ("American beech", "hardwood", 4, "Beech, American", "0.64", "103,000", "11,900"),
    ("Yellow birch", "hardwood", 4, "Birch: Yellow", "0.62", "114,000", "13,900"),
    ("Black cherry", "hardwood", 4, "Cherry, black", "0.50", "85,000", "10,300"),
    ("Western redcedar", "softwood", 7, "Cedar: Western redcedar", "0.32", "51,700", "7,700"),
    ("Coast Douglas-fir", "softwood", 7, "Douglas-fir: Coast", "0.48", "85,000", "13,400"),
    ("Balsam fir", "softwood", 7, "Fir: Balsam", "0.35", "63,000", "10,000"),
    ("Eastern white pine", "softwood", 7, "Pine: Eastern white", "0.35", "59,000", "8,500"),
    ("Loblolly pine", "softwood", 7, "Pine: Loblolly", "0.51", "88,000", "12,300"),
]

# Glass, PDF page, rho [g/cm3], E [10^3 N/mm2], nu, k [W/mK], cp [J/gK], sheet date.
GLASSES = [
    ("N-FK5", 6, "2.45", "62", "0.232", "0.925", "0.808", "2014-02-02"),
    ("N-FK51A", 7, "3.68", "73", "0.302", "0.760", "0.690", "2023-12-01"),
    ("N-PSK53A", 12, "3.57", "76", "0.288", "0.640", "0.590", "2014-02-01"),
    ("N-BK7", 13, "2.51", "82", "0.206", "1.114", "0.858", "2023-12-01"),
    ("N-BAK4", 26, "3.05", "77", "0.240", "0.880", "0.680", "2014-02-01"),
    ("N-SK2", 34, "3.55", "78", "0.263", "0.776", "0.595", "2016-05-25"),
    ("N-LAK22", 58, "3.77", "90", "0.266", "0.750", "0.540", "2023-12-01"),
    ("N-SF6", 100, "3.37", "93", "0.262", "0.960", "0.690", "2018-06-01"),
    ("N-SF10", 104, "3.05", "87", "0.252", "0.960", "0.740", "2014-02-01"),
    ("N-SF11", 105, "3.22", "92", "0.257", "0.950", "0.710", "2014-02-01"),
]

# Product, subgroup, page, density [g/cc], tensile strength [psi], elongation [%].
RUBBERS = [
    ("Dragon Skin 15", "silicone", 1, "1.07", "537", "771"),
    ("Dragon Skin 20", "silicone", 1, "1.08", "550", "620"),
    ("Dragon Skin 30", "silicone", 1, "1.08", "500", "364"),
    ("Ecoflex 00-10", "silicone", 1, "1.04", "120", "800"),
    ("Ecoflex 00-30", "silicone", 1, "1.07", "200", "900"),
    ("ReoFlex 20", "polyurethane", 3, "1.01", "200", "1,000"),
    ("ReoFlex 30", "polyurethane", 3, "1.01", "450", "1,000"),
    ("ReoFlex 40", "polyurethane", 3, "1.02", "490", "1,000"),
    ("ReoFlex 50", "polyurethane", 3, "1.01", "580", "435"),
    ("ReoFlex 60", "polyurethane", 3, "1.04", "782", "581"),
]


def import_ashby_families(pdf_dir: Path, records: list, sources: list,
                         manifest: list, *, obs, record, pair, slug) -> None:
    """Append reviewed facts; require every original to match its checked hash."""
    for sid, title, publisher, url, filename, digest, pages, revision, source_type in DOCUMENTS:
        path = pdf_dir / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"{filename}: source differs from the reviewed snapshot")
        manifest.append({"id": sid, "url": url, "filename": filename,
                         "sha256": digest, "bytes": path.stat().st_size,
                         "pages": pages, "retrieved_date": DATE})
        sources.append({"id": sid, "title": title, "organization": publisher,
                        "source_type": source_type, "publication_date": None,
                        "revision": revision, "url": url, "retrieved_date": DATE,
                        "license": "Selected numerical facts with attribution. Source document not redistributed.",
                        "notes": "See ashby-families-review.md for scope, exclusions, and conversion review.",
                        "sha256": digest})
    roots = [("composites", "Synthetic composites", "composite"),
             ("woods", "Wood", "wood"), ("foams", "Foams", "foam"),
             ("elastomers", "Elastomers", "elastomer"), ("glasses", "Glasses", "glass")]
    for rid, name, family in roots:
        records.append(record(rid, name, "family", None, [family],
                              f"{name} with source-specific property observations."))
    for sid, rows in COMPOSITES.items():
        for code, fiber, page, direction, rho, modulus, strength in rows:
            woven = "PW" in fiber
            label = f"{code} ({fiber})"
            is_hexcel = sid == "hexcel-8552"
            temp = 298.15 if is_hexcel else 295.15
            cure = ("35% resin by mass; 134 g/m² fiber areal weight; dry"
                    if is_hexcel else "Oven cure; as received" if sid == "toray-2700"
                    else "Supplier autoclave cure; ambient")
            angle = "0°" if direction == "L" else "90°"
            note = f"{fiber}; {cure}. Tensile properties along {angle}; not quasi-isotropic."
            values = []
            for prop, raw, row, factor, unit in [
                ("density", rho, "Nominal laminate density" if is_hexcel else "Laminate density", 1000, "g/cm³"),
                ("youngs_modulus", modulus, angle + " tensile modulus", 1e9, "GPa"),
                ("tensile_strength", strength, angle + " tensile strength", 1e6, "MPa"),
            ]:
                conditions = {"material_state": note}
                if prop != "density":
                    conditions.update(temperature_K=temp, orientation=direction)
                values.append(obs(prop, raw, sid, page, label + (", 25 °C dry" if is_hexcel else ", RTA"), row,
                                  method=("Supplier method not stated" if is_hexcel else "ASTM D792" if prop == "density" else "ASTM D3039"),
                                  conditions=conditions, factor=factor, raw_unit=unit))
            name = ("HexPly " if is_hexcel else "Toray " + sid.split("-")[1] + " ") + label
            pair(records, sid + "-" + slug(code), name, "composites",
                 ["composite", "woven-carbon-epoxy" if woven else "ud-carbon-epoxy"],
                 note, values, aliases=[code, fiber, "CFRP", "carbon fiber epoxy"],
                 designations={"Supplier": code})
    for name, subgroup, page, row, gravity, strength, modulus in WOODS:
        note = "Small clear specimens; 12% moisture content on oven-dry mass basis; longitudinal bending."
        common = {"moisture_content_1": .12, "material_state": note}
        density = obs("density", gravity, "usda-wood-mechanical", page,
                      "Table 5-3a, " + row + ", 12% MC", "Specific gravity",
                      method="Computed from G12 using Wood Handbook Eq. (4-12), printed p. 4-10 (PDF p. 89)",
                      conditions={**common, "material_state": note + " Density includes moisture: rho12 = G12 × 1000 × (1 + 0.12) kg/m³. G12 uses oven-dry mass and volume at 12% MC. Equation source: USDA Wood Handbook FPL-GTR-190, Chapter 4, p. 4-10."},
                      basis="computed", factor=1120, raw_unit="1 (G12)")
        values = [density]
        for prop, raw, label, factor, unit in [
            ("flexural_strength", strength, "Static bending modulus of rupture", 1000, "kPa"),
            ("flexural_modulus", modulus, "Static bending modulus of elasticity", 1e6, "MPa"),
        ]:
            values.append(obs(prop, raw, "usda-wood-mechanical", page, "Table 5-3a, " + row + ", 12% MC", label,
                              method="Simply supported, center-loaded beam; span/depth 14:1; no 10% shear correction applied",
                              conditions={**common, "orientation": "L"}, factor=factor, raw_unit=unit, basis="reference"))
        pair(records, "wood-" + slug(name), name, "woods", ["wood", subgroup], note,
             values, aliases=[row, name + " wood", subgroup])
    for name, page, rho, modulus, nu, k, cp, revision in GLASSES:
        values = []
        for prop, raw, label, factor, unit in [
            ("density", rho, "Density rho", 1000, "g/cm³"),
            ("youngs_modulus", modulus, "Elasticity modulus E", 1e9, "10³ N/mm²"),
            ("poissons_ratio", nu, "Poisson's ratio mu", 1, "1"),
            ("thermal_conductivity", k, "Thermal conductivity lambda", 1, "W/(m·K)"),
            ("specific_heat", cp, "Average specific heat capacity cp", 1000, "J/(g·K)"),
        ]:
            values.append(obs(prop, raw, "schott-optical-glass", page, name + ", Other Properties", label,
                              method="Supplier reference property; method not stated on sheet",
                              conditions={"material_state": f"Optical glass reference data; sheet dated {revision}. Test temperature not specified for this row."},
                              factor=factor, raw_unit=unit, basis="reference"))
        pair(records, "schott-" + slug(name), "SCHOTT " + name, "glasses", ["glass", "optical-glass"],
             "Named optical glass composition; mechanical and thermal reference values.", values,
             aliases=[name, "optical glass"], designations={"Supplier": name})
    for name, subgroup, page, rho, strength, elongation in RUBBERS:
        values = []
        for prop, raw, label, factor, unit, method in [
            ("density", rho, "Specific gravity (printed g/cc)", 1000, "g/cc", "ASTM D1475"),
            ("tensile_strength", strength, "Tensile strength", 6894.757293168, "psi", "ASTM D412"),
            ("elongation_at_break", elongation, "Elongation at break", .01, "%", "ASTM D412"),
        ]:
            values.append(obs(prop, raw, "smooth-on-reference", page, name, label, method=method,
                              conditions={"temperature_K": 296.15, "material_state": "Measured after 7 days at 23 °C; supplier mixing and cure procedure."},
                              factor=factor, raw_unit=unit))
        pair(records, "smooth-on-" + slug(name), name, "elastomers", ["elastomer", subgroup],
             f"Smooth-On {subgroup} elastomer formulation. No small-strain Young's modulus supplied in the reference chart.",
             values, aliases=["Smooth-On " + name, subgroup, "rubber"], designations={"Supplier": name})
    for series, grades, densities, strengths, moduli in [
        ("H", "45 60 80 100 130 160 200 250", "48 60 80 100 130 160 200 250",
         "1.4 1.8 2.5 3.5 4.8 5.4 7.1 9.2", "55 75 95 130 175 205 250 320"),
        ("F", "40 50 90 130", "40 50 90 130", "1.5 1.9 2.8 3.3", None),
    ]:
        for i, grade in enumerate(grades.split()):
            name = "Divinycell " + series + grade
            sid = "diab-" + series.lower()
            foam = "PVC" if series == "H" else "PES"
            values = []
            properties = [("density", densities.split()[i], "Density, nominal", "ISO 845" if series == "H" else "ASTM D1622", 1, "kg/m³"),
                          ("tensile_strength", strengths.split()[i], "Tensile strength, nominal", "ASTM D1623", 1e6, "MPa")]
            if moduli:
                properties.append(("youngs_modulus", moduli.split()[i], "Tensile modulus, nominal", "ASTM D1623", 1e6, "MPa"))
            for prop, raw, label, method, factor, unit in properties:
                conditions = {"material_state": "Nominal average at nominal density."}
                if series == "H":
                    conditions["temperature_K"] = 296.15
                elif prop == "density":
                    conditions["material_state"] += " Supplier density tolerance ±10%."
                if prop != "density":
                    conditions["orientation"] = "ST"
                    conditions["material_state"] += " Through thickness, perpendicular to the sheet plane." + (" Type B specimen, flatwise tension." if series == "F" else "")
                values.append(obs(prop, raw, sid, 1, name, label, method=method,
                                  conditions=conditions, factor=factor, raw_unit=unit))
            pair(records, "diab-" + slug(name), name, "foams", ["foam", foam.lower() + "-foam"],
                 f"Diab {foam} structural foam, nominal density grade. Tensile and compressive moduli are distinct.",
                 values, aliases=["Diab " + name, foam + " foam"], designations={"Supplier": name})
    html = (pdf_dir / "kyocera-materials-2026.html").read_text()
    table = json.JSONDecoder().raw_decode(html.split("var DATA = ", 1)[1])[0]
    methods = {p["key"]: p["norm"] for p in table["props"]}
    for material in table["mats"]:
        if material["vals"]["emodul"]["value"] is None:
            continue
        values = []
        for key, prop, factor, unit in [
            ("rohdichte", "density", 1000, "g/cm³"),
            ("emodul", "youngs_modulus", 1e9, "GPa"),
            ("biegefestigkeit", "flexural_strength", 1e6, "MPa"),
            ("poisson", "poissons_ratio", 1, "1"),
            ("waermeleit", "thermal_conductivity", 1, "W/(m·K)"),
        ]:
            raw = material["vals"][key]["raw"]
            if raw is None:
                continue
            lower = raw.startswith("≥")
            value = obs(prop, raw.removeprefix("≥").strip(), "kyocera-materials-2026", 1,
                        material["name"] + " (web comparison table)", key, method=methods[key],
                        factor=factor, raw_unit=unit, basis="typical",
                        conditions={"material_state": "Source literal: " + raw + " " + unit + ". Typical laboratory samples; not guaranteed. Test temperature not stated."})
            if lower:
                value["result_kind"] = "lower_bound"
            value["source_locator"] = "Web comparison table, " + material["name"] + ", " + key
            values.append(value)
        subgroup = table["groups"][material["group"]]["de"]
        pair(records, "kyocera-" + slug(material["id"]), "KYOCERA " + material["name"], "ceramics",
             ["ceramic", slug(subgroup)], "KYOCERA " + subgroup.lower() + " grade.", values,
             aliases=[material["name"], subgroup], designations={"Supplier": material["name"]})


def main() -> None:
    """Rebuild only this batch, preserving every earlier curated record."""
    import argparse
    import sys
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from builder.import_reference_tables import obs, record, pair, slug
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    records, sources, documents = [], [], []
    import_ashby_families(args.pdf_dir, records, sources, documents,
                         obs=obs, record=record, pair=pair, slug=slug)
    for filename, key, additions in [("materials", "materials", records),
                                     ("sources", "sources", sources),
                                     ("reference-manifest", "documents", documents)]:
        path = root / "curated" / (filename + ".json")
        data = json.loads(path.read_text())
        # Replace in place so rechecking an earlier batch does not reorder
        # records around later additions or roll back the manifest date.
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
    print(f"Rebuilt {sum(r['record_type'] == 'grade' for r in records)} new material identities.")


if __name__ == "__main__":
    main()
