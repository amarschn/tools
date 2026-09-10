#!/usr/bin/env python3
"""Rebuild factual records from pinned manufacturer PDFs (development only).

Usage: python3 scripts/import_reference_tables.py --pdf-dir /path/to/downloads
Requires pypdf and pdfplumber. Normal site builds use curated JSON, not PDFs or
the network. Download URLs and SHA-256 hashes live in reference-manifest.json.
Only selected numerical facts are extracted; source documents are not bundled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.import_specialty_metals import DOCUMENTS as SPECIALTY_DOCUMENTS, DATE as SPECIALTY_DATE, import_specialty_metals
from scripts.import_nonferrous_metals import DOCUMENTS as NONFERROUS_DOCUMENTS, DATE as NONFERROUS_DATE, SOURCE_TYPES as NONFERROUS_SOURCE_TYPES, import_nonferrous_metals
DATE = "2026-09-07"
PROPERTIES = {
    "density": ("kg/m^3", "g/cm³", 1000),
    "youngs_modulus": ("Pa", "MPa", 1e6),
    "tensile_strength": ("Pa", "MPa", 1e6),
    "yield_strength": ("Pa", "MPa", 1e6),
    "elongation_at_break": ("1", "%", .01),
    "thermal_conductivity": ("W/(m*K)", "W/(m·K)", 1),
    "flexural_strength": ("Pa", "MPa", 1e6),
    "specific_heat": ("J/(kg*K)", "J/(kg·K)", 1),
    "poissons_ratio": ("1", "1", 1),
}
DOCUMENTS = [
    ("ensinger-manual", "Stock shapes — Engineering plastics manual", "Ensinger",
     "https://www.ensingerplastics.com/en-us/-/media/ensinger/files/document-teaser-files/brochures/shapes/engineering-plastics-manual-english.ashx",
     "Material standard values, pages 88–97. Typical guideline values after machining; moisture and specimen orientation affect results. The manual does not establish present product availability.", None),
    ("coorstek", "Ceramic Material Properties", "CoorsTek",
     "https://www.coorstek.com/media/4244/ceramic-material-properties.pdf",
     "Page 1, selected ceramic columns. Typical values; process, size, and shape affect properties. Generic steel comparison column excluded.", "2017"),
    ("outokumpu-core", "Core range datasheet", "Outokumpu",
     "https://www.outokumpu.com/-/media/files/products/core/outokumpu-core-range-datasheet.pdf",
     "Table 5: cold rolled sheet mechanical limits, with footnote-specific standards. Table 7: metric physical values. Table 6 is not imported; some published rows contain apparent unit inconsistencies.", None),
    ("outokumpu-supra", "Supra range datasheet", "Outokumpu",
     "https://www.outokumpu.com/-/media/files/products/supra/outokumpu-supra-range-datasheet.pdf",
     "Table 5: cold rolled sheet mechanical limits. Table 7: metric physical values. EN grades with the same ASTM name remain distinct.", None),
]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def digits(text):
    # Preserve written trailing zeros; integer trailing zeros are ambiguous,
    # so no greater precision is claimed than the written number provides.
    text = str(text).replace(",", "").split("(")[0].strip()
    return max(1, len(text.replace(".", "").lstrip("0")))


def obs(prop, raw, source, page, column, row, *, method, conditions=None,
        basis="typical", factor=None, raw_unit=None):
    unit, original_unit, scale = PROPERTIES[prop]
    scale = scale if factor is None else factor
    original_unit = raw_unit or original_unit
    cleaned = str(raw).replace(",", "").replace(" ", "")
    parts = re.split("[–-]", cleaned)
    if not all(re.fullmatch(r"(?:\d+(?:\.\d+)?|\.\d+)", p) for p in parts) or len(parts) > 2:
        raise ValueError((prop, raw, column))
    numbers = [float(p) * scale for p in parts]
    precision = min(digits(p) for p in parts)
    result = {
        "property": prop, "value": numbers[0], "unit": unit,
        "uncertainty": {"kind": "implied", "sigfigs": precision},
        "basis": basis, "conditions": conditions or {}, "test_method": method,
        "source_id": source,
        "source_locator": f"Page {page}, {column}, row {row}",
        "source_page": page,
        "source_value": {"text": str(raw), "unit": original_unit,
                         "scale_to_si": scale, "offset_to_si": 0,
                         "significant_figures": precision},
    }
    if len(numbers) == 2:
        result["result_kind"] = "interval"
        result["uncertainty"] = {"kind": "range", "min": numbers[0], "max": numbers[1]}
    return result


def record(id, name, type, parent, family, description, *, aliases=(), condition=None,
           observations=(), designations=None, prominence=2):
    return {"id": id, "name": name, "record_type": type, "parent_id": parent,
            "family": family, "description": description, "aliases": list(aliases),
            "condition": condition, "observations": list(observations),
            "designations": designations or {}, "prominence": prominence}


def pair(records, id, name, parent, family, description, observations,
         *, condition="supplier reference state", aliases=(), designations=None):
    records.append(record(id, name, "grade", parent, family, description,
                          aliases=aliases, designations=designations))
    records.append(record(id + "-reference", name + " — " + condition,
                          "variant", id, family, description, aliases=aliases,
                          condition=condition, observations=observations,
                          designations=designations))


# Column identities were checked against the PDF headers. Color-only variants
# are deliberately omitted from the material count.
PLASTICS = {
    88: [(0,"TECARAN ABS grey","ABS"),(1,"TECANYL MT coloured","PPE"),(2,"TECANYL GF30","PPE"),(3,"TECANYL 731 grey","PPE"),(4,"TECAFINE PMP","PMP"),(5,"TECAPRO MT","PP"),(6,"TECAFORM AH natural","POM-C"),(8,"TECAFORM AH GF25","POM-C"),(9,"TECAFORM AH ELS","POM-C")],
    89: [(0,"TECAFORM AH SD","POM-C"),(1,"TECAFORM AH ID blue","POM-C"),(2,"TECAFORM AH LA","POM-C"),(3,"TECAFORM AH SAN","POM-C"),(4,"TECAFORM AH MT coloured","POM-C"),(5,"TECAFORM AD","POM-H"),(7,"TECAFORM AD AF","POM-H"),(8,"TECAST T","PA6"),(9,"TECAST TM","PA6")],
    90: [(0,"TECAST L black","PA6"),(3,"TECAGLIDE green","PA6"),(4,"TECARIM 1500 yellow","PA6"),(5,"TECAMID 6","PA6"),(6,"TECAM 6 MO black","PA6"),(7,"TECAMID 6 GF25","PA6"),(8,"TECAMID 6 GF30 black","PA6"),(9,"TECAMID 66","PA66")],
    91: [(0,"TECAMID 66 MH","PA66"),(1,"TECAMID 66 GF30 black","PA66"),(2,"TECAMID 66 CF20 black","PA66"),(3,"TECAMID 66 HI","PA66"),(4,"TECAMID 66 LA","PA66"),(5,"TECAMID 66/X GF50","PA66"),(6,"TECAMID 46 redbrown","PA46"),(7,"TECAMID 12","PA12"),(8,"TECAPET","PET")],
    92: [(0,"TECAPET TF","PET"),(1,"TECADUR PET","PET"),(2,"TECADUR PBT GF30","PBT"),(3,"TECANAT","PC"),(4,"TECANAT GF30","PC"),(5,"TECAFLON PVDF","PVDF"),(6,"TECASON S","PSU"),(7,"TECAPEI","PEI"),(8,"TECASON P","PPSU"),(9,"TECASON P MT coloured","PPSU")],
    93: [(0,"TECATRON","PPS"),(1,"TECATRON GF40","PPS"),(3,"TECATRON PVX","PPS"),(4,"TECAPEEK","PEEK"),(7,"TECAPEEK GF30","PEEK"),(8,"TECAPEEK CF30","PEEK"),(9,"TECAPEEK PVX","PEEK")],
    94: [(0,"TECAPEEK ELS nano","PEEK"),(1,"TECAPEEK TF10","PEEK"),(2,"TECAPEEK ID blue","PEEK"),(3,"TECAPEEK MT","PEEK")],
    95: [(0,"TECAPEEK CF30 MT","PEEK"),(1,"TECAPEEK CLASSIX white","PEEK"),(2,"TECAPEEK TS","PEEK"),(3,"TECAPEEK CMF","PEEK"),(5,"TECAPEEK HT black","PEK"),(6,"TECAPEEK ST black","PEKEKK"),(7,"TECATEC PEEK CW50","PEEK"),(8,"TECATEC PEKK CW60","PEKK"),(9,"TECATOR 5013","PAI")],
    96: [(0,"TECATOR 5031 PVX","PAI")] + [(i+1,"TECASINT "+n,"PI") for i,n in enumerate(["1011","1021","1031","1041","1061","1101","1611","2011","2021"])],
    97: [(i,"TECASINT "+n, "PI" if i < 6 else "PAI" if i < 8 else "PTFE") for i,n in enumerate(["2031","2391","4011","4021","4111","4121","5051","5201 SD","8001"])],
}
POLYMER_NAMES = {"ABS":"Acrylonitrile butadiene styrene", "PPE":"Polyphenylene ether",
    "PMP":"Polymethylpentene", "PP":"Polypropylene", "POM-C":"Acetal copolymer",
    "POM-H":"Acetal homopolymer", "PA6":"Nylon 6", "PA66":"Nylon 66", "PA46":"Nylon 46",
    "PA12":"Nylon 12", "PET":"Polyethylene terephthalate", "PBT":"Polybutylene terephthalate",
    "PC":"Polycarbonate", "PVDF":"Polyvinylidene fluoride", "PSU":"Polysulfone",
    "PEI":"Polyetherimide", "PPSU":"Polyphenylsulfone", "PPS":"Polyphenylene sulfide",
    "PEEK":"Polyether ether ketone", "PEK":"Polyetherketone", "PEKEKK":"Polyetherketoneetherketoneketone",
    "PEKK":"Polyetherketoneketone", "PAI":"Polyamide-imide", "PI":"Polyimide", "PTFE":"Polytetrafluoroethylene"}


def import_plastics(pages, records):
    for symbol, name in POLYMER_NAMES.items():
        records.append(record("polymer-"+slug(symbol), f"{name} ({symbol})", "family",
                       "engineering-plastics", ["polymer",symbol],
                       f"Named supplier formulations based on {name.lower()}.", aliases=[symbol,name]))
    rows = [
        ("Density", "density", "DIN EN ISO 1183"),
        ("Modulus of elasticity (tensile test)","youngs_modulus","DIN EN ISO 527-2"),
        ("Tensile strength", "tensile_strength", "DIN EN ISO 527-2"),
        ("Tensile strength at yield", "yield_strength", "DIN EN ISO 527-2"),
        ("Elongation at break", "elongation_at_break", "DIN EN ISO 527-2"),
        ("Thermal conductivity", "thermal_conductivity", "ISO 22007-4:2008"),
        ("Flexural strength", "flexural_strength", "DIN EN ISO 178"),
    ]
    for page, columns in PLASTICS.items():
        words = pages[page-1].extract_words()
        headers = sorted([w for w in words if w["text"].startswith("TECA") and w["top"]<125], key=lambda w:w["x0"])
        assert len(headers) == (9 if page == 97 else 10), (page, headers)
        edges = [w["x0"]-.6 for w in headers]
        edges.append(edges[-1] + edges[1]-edges[0])
        grouped = []
        for word in sorted(words, key=lambda w:w["top"]):
            group = next((g for g in grouped if abs(g[0]["top"]-word["top"])<1.5), None)
            if group is None: grouped.append([word])
            else: group.append(word)
        lines = [sorted(g,key=lambda w:w["x0"]) for g in grouped]
        for index,name,symbol in columns:
            observations=[]
            for label,prop,method in rows:
                line = next(l for l in lines if " ".join(w["text"] for w in l).startswith(label + " ["))
                value = " ".join(w["text"] for w in line if edges[index] <= w["x0"] < edges[index+1])
                if not value or value in {"–", "n.a."}: continue
                if "(b)" in value: method="ISO 8302"
                if "(c)" in value: method="ASTM E1530"
                value = re.sub(r"\s*\([bc]\)", "", value)
                observations.append(obs(prop,value,"ensinger-manual",page,
                    f"Material standard values, column {index+1} ({name})",label,
                    method=method, conditions={"product_form":"stock_shape",
                    "material_state":"Machined specimen; tested after machining. Humidity affects polyamides; orientation and exact test temperature are not specified in this table."}))
            aliases=[symbol,POLYMER_NAMES[symbol],name.replace("TECA", "TECA ")]
            if symbol.startswith("POM"): aliases += ["POM","acetal","polyoxymethylene"]
            if symbol.startswith("PA") and symbol != "PAI": aliases += ["nylon", "polyamide"]
            pair(records,slug(name),name,"polymer-"+slug(symbol),["polymer",symbol],
                 f"Ensinger {symbol} formulation. Published stock-shape reference data for this named product.",
                 observations,condition="stock shape",aliases=aliases,
                 designations={"Supplier":name,"Polymer":symbol})


def import_ceramics(records):
    names = ["Porcelain","Steatite","Cordierite","Mullite","AD-85","AD-90","AD-94","AD-96","FG-995","AD-995","PlasmaPure AD-998","PlasmaPure-UC","ESD Alumina","ZTA 10%","Dura-Z TTZ","YTZP sintered","YTZP HIPed","SC-RB SC-2","UltraSiC SC-30","PureSiC CVD","RBB4C","HPB4C","WC ACI-NI6","HP AlN","SN 101C","NBD-200","NT 154"]
    vectors = {
        "density": ("Density","ASTM C20", "2.40 2.78 2.05 2.80 3.42 3.60 3.70 3.72 3.80 3.90 3.92 3.92 3.85 4.01 5.72 6.02 6.07 3.10 3.15 3.21 2.65 2.5 14.90 3.26 3.21 3.16 3.22"),
        "youngs_modulus": ("Elastic Modulus, 20 °C","ASTM C848", "104 110 40 150 221 276 303 303 350 370 380 386 370 360 200 210 210 393 410 435–460 379 460 614 330 310 320 310"),
        "thermal_conductivity": ("Thermal Conductivity, 20 °C","ASTM C408", "5.0 2.5 1.6 3.5 16.0 16.7 22.4 24.7 27.5 30.0 31.0 33.0 25 27.0 2.2 2.2 2.2 125.0 150.0 140.0 50.0 90 84.0 80.0 34 29 38"),
        "flexural_strength": ("Flexural Strength (MOR), 20 °C","ASTM F417; four-point bend", "130 140 55 170 296 338 352 358 375 379 390 400 300 450 900 1240 1720 462 480 470–520 250 410 2330 340 1000 900 900"),
        "poissons_ratio": ("Poisson’s Ratio, 20 °C","ASTM C848", "- - - - 0.22 0.22 0.21 0.21 0.22 0.22 0.22 0.22 0.22 0.30 0.30 0.30 0.30 0.20 0.21 0.21 0.18 0.17 - 0.25 0.27 0.26 0.27"),
        "specific_heat": ("Specific Heat, 100 °C","ASTM E1269", "- - - 950 920 920 880 880 880 880 880 870 - 885 400 400 400 800 800 665 - - - 740 - - 724"),
    }
    for _,_,values in vectors.values(): assert len(values.split()) == len(names)
    for i,name in enumerate(names):
        family="silicate" if i<4 else "alumina" if i<14 else "zirconia" if i<17 else "carbide" if i<23 else "nitride"
        observations=[]
        for prop,(label,method,values) in vectors.items():
            value=values.split()[i]
            if value=="-": continue
            conditions={} if prop=="density" else {"temperature_K":373.15 if prop=="specific_heat" else 293.15}
            observations.append(obs(prop,value,"coorstek",1,f"column {i+1} ({name})",label,method=method,
                conditions=conditions,factor=1e9 if prop=="youngs_modulus" else None,
                raw_unit="GPa" if prop=="youngs_modulus" else None))
        pair(records,"coorstek-"+slug(name),"CoorsTek "+name,"ceramics",["ceramic",family],
             f"CoorsTek {family} material with supplier-reported typical properties.",observations,
             aliases=[name,family],designations={"Supplier":name})


def import_stainless(all_pages, records):
    for group,mechanical_page,physical_page in [("core",8,10),("supra",6,8)]:
        pages=all_pages["outokumpu-"+group]
        prefix=group.capitalize()
        physical={}
        for line in pages[physical_page-1].split("Imperial")[0].splitlines():
            fields=re.split(r"\s{2,}",line.strip())
            if fields[0].startswith(prefix+" ") and len(fields)>5:
                physical[fields[0].rstrip("*")]=fields[1:]
        for line in pages[mechanical_page-1].splitlines():
            fields=re.split(r"\s{2,}",line.strip())
            if not fields[0].startswith(prefix+" ") or len(fields)<6: continue
            name=fields[0]
            if group=="core":
                en,astm,uns,form,yield02,yield10,tensile,elong,elong80=fields[1:]
            else:
                form,yield02,yield10,tensile,elong,elong80=fields[1:]
                en="1."+name.split("/")[-1] if "/" in name else "1.4420"
                astm=name.split()[1].split("/")[0]
                uns=""
            standard="EN 10088-2"
            if name=="Core 439M": standard="ASTM A240"
            if name in ["Core 4622","Supra 316plus"]: standard="EN 10028-7"
            conditions={"temperature_K":293.15,"product_form":"sheet",
                        "material_state":"Cold rolled coil and sheet (C); datasheet delivery condition"}
            observations=[]
            for prop,value,label in [("yield_strength",yield02,"Table 5, Rp0.2"),("tensile_strength",tensile,"Table 5, Rm"),("elongation_at_break",elong80,"Table 5, A80 (80 mm gauge length)")]:
                if value=="–": continue
                observations.append(obs(prop,value,"outokumpu-"+group,mechanical_page,name+", product form "+form,label,
                    method=standard,conditions=conditions,basis="specified_range" if "–" in value else "minimum"))
            physical_values=physical[name]
            for prop,index,label in [("density",0,"Density"),("youngs_modulus",1,"Modulus of elasticity at 20 °C"),("thermal_conductivity",3,"Thermal conductivity at 20 °C"),("specific_heat",4,"Thermal capacity at 20 °C")]:
                value=physical_values[index]
                if value=="–": continue
                observations.append(obs(prop,value,"outokumpu-"+group,physical_page,name,"Table 7, "+label,
                    method="EN 10088-1" if name not in ["Core 439M","Core 4622","Supra 316plus"] else "Outokumpu values (Table 7 footnote)",
                    conditions={} if prop=="density" else {"temperature_K":293.15},
                    factor=1e9 if prop=="youngs_modulus" else None,
                    raw_unit="GPa" if prop=="youngs_modulus" else "kg/dm³" if prop=="density" else None))
            family="ferritic" if name in ["Core 441/4509","Core 439M","Core 4622","Supra 444/4521"] else "austenitic"
            designations={k:v for k,v in {"EN":en,"ASTM":astm,"UNS":uns}.items() if v and v!="–"}
            pair(records,slug("stainless "+name),f"Stainless steel {name}","stainless-steels",["metal","steel","stainless-steel",family],
                 f"Outokumpu {family} stainless grade. Mechanical limits describe cold rolled sheet; physical values are listed separately by the supplier.",
                 observations,condition="cold rolled sheet",aliases=[name,*designations.values(),"stainless",family],designations=designations)


def main():
    from pypdf import PdfReader
    import pdfplumber
    import logging
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir",type=Path,required=True)
    parser.add_argument("--check", action="store_true", help="re-extract in memory and fail if curated outputs differ")
    args=parser.parse_args()
    manifest_path=ROOT/"curated/reference-manifest.json"
    pins=json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    sources=[]; manifest=[]; all_pages={}
    for id,title,organization,url,notes,published in DOCUMENTS + SPECIALTY_DOCUMENTS + NONFERROUS_DOCUMENTS:
        path=args.pdf_dir/(id+".pdf")
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if pins:
            pin=next(p for p in pins["documents"] if p["id"]==id)
            if pin["sha256"] != digest: raise ValueError(f"{id}: PDF differs from reviewed snapshot; review before changing the pin")
        pdf=PdfReader(path)
        all_pages[id]=[p.extract_text(extraction_mode="layout") for p in pdf.pages]
        retrieved = NONFERROUS_DATE if id in {d[0] for d in NONFERROUS_DOCUMENTS} else SPECIALTY_DATE if id in {d[0] for d in SPECIALTY_DOCUMENTS} else DATE
        manifest.append({"id":id,"url":url,"filename":path.name,"sha256":digest,"bytes":path.stat().st_size,"pages":len(pdf.pages),"retrieved_date":retrieved})
        sources.append({"id":id,"title":title,"organization":organization,
            "source_type":NONFERROUS_SOURCE_TYPES.get(id, "manufacturer_datasheet"),"publication_date":published,
            "revision":"Snapshot "+digest[:12],"url":url,"retrieved_date":retrieved,
            "license":"Publisher copyright retained; selected numerical facts with attribution. Source document not redistributed.",
            "notes":notes,"sha256":digest})
    seed_path=ROOT/"fixtures/legacy-site-seed/materials.json"
    seed_sources=ROOT/"fixtures/legacy-site-seed/sources.json"
    if not seed_path.exists():
        if args.check: raise ValueError("The frozen legacy seed is required for an import check")
        seed_path.parent.mkdir(parents=True,exist_ok=True)
        seed_path.write_bytes((ROOT/"curated/materials.json").read_bytes())
        seed_sources.write_bytes((ROOT/"curated/sources.json").read_bytes())
    seed=json.loads(seed_path.read_text())["materials"]
    records=[r for r in seed if r["id"] in ["metals","aluminium-alloys","al-6061","al-6061-t4","al-6061-t6","engineering-plastics"]]
    review_hydro_seed(records)
    sources += [s for s in json.loads(seed_sources.read_text())["sources"] if s["id"]=="hydro-6061-2019"]
    hydro_path = args.pdf_dir / "hydro-6061.pdf"
    hydro_digest = hashlib.sha256(hydro_path.read_bytes()).hexdigest()
    if hydro_digest != "cc3cc79ef34d7ccd2a69fe5216f726be23d23d0b07e12c2ea1091adbba7fd009":
        raise ValueError("Hydro PDF differs from the reviewed snapshot")
    sources[-1]["sha256"] = hydro_digest
    sources[-1]['license'] = 'Manufacturer-published datasheet; textual attribution only; source document not redistributed.'
    sources[-1]["notes"] += " Page 2 rechecked 2026-09-09: alloy-wide density is not temper-specific; thermal conductivity is at 25 °C."
    manifest.append({"id":"hydro-6061-2019","url":sources[-1]["url"],"filename":hydro_path.name,"sha256":hydro_digest,
                     "bytes":hydro_path.stat().st_size,"pages":len(PdfReader(hydro_path).pages),"retrieved_date":sources[-1]["retrieved_date"]})
    records += [record("stainless-steels","Stainless steels","family","metals",["metal","steel","stainless-steel"],"Austenitic and ferritic stainless grades with manufacturer references."),
                record("ceramics","Technical ceramics","family",None,["ceramic"],"Silicates, aluminas, zirconias, carbides, and nitrides with supplier references.")]
    with pdfplumber.open(args.pdf_dir/"ensinger-manual.pdf") as pdf:
        import_plastics(pdf.pages,records)
    import_ceramics(records)
    import_stainless(all_pages,records)
    import_specialty_metals(all_pages,records,obs=obs,record=record,pair=pair,slug=slug)
    import_nonferrous_metals(all_pages,records,obs=obs,record=record,pair=pair,slug=slug)
    outputs = {ROOT/f"curated/{name}.json": json.dumps({"schema_version":"0.1.0",key:data},ensure_ascii=False,indent=2)+"\n"
               for name,key,data in [("materials","materials",records),("sources","sources",sources)]}
    outputs[manifest_path] = json.dumps({"retrieved_date":NONFERROUS_DATE,"documents":manifest},indent=2)+"\n"
    for path, text in outputs.items():
        if args.check:
            if path.read_text() != text: raise ValueError(f"{path.name} differs from a fresh import")
        else: path.write_text(text)
    print(f"Imported {sum(r['record_type']=='grade' for r in records)} material identities, {sum(len(r['observations']) for r in records)} observations")


def review_hydro_seed(records):
    """Corrections verified against the saved Hydro PDF, page 2, 2026-09-09.

    Density is reported once for the alloy, outside the temper table. Its
    earlier rounded SI copy was repeated on two tempers. Retain one authoring
    copy; the canonical adapter assigns it to the grade.
    """
    for row in records:
        if row["id"] == "al-6061":
            row["description"] = "Al-Mg-Si-Cu wrought alloy. The cited Hydro datasheet reports extrusion limits by temper and alloy-wide density."
        if row["id"] not in ("al-6061-t4", "al-6061-t6"):
            continue
        if row["id"] == "al-6061-t6":
            row["observations"] = [o for o in row["observations"] if o["property"] != "density"]
        for observation in row["observations"]:
            prop = observation["property"]
            if prop == "density":
                literal, unit, factor, figures = "0.098", "lb/in³", 27679.904710203122, 2
                observation["conditions"] = {}
                observation["source_locator"] = "Page 2, alloy-wide density above the chemical composition table: 0.098 lb/in³; no temper specified"
                observation["value"] = float(literal) * factor
            elif prop == "yield_strength":
                literal = "110" if row["id"] == "al-6061-t4" else "240"
                unit, factor, figures = "MPa", 1e6, 2
            else:
                literal = "155" if row["id"] == "al-6061-t4" else "167"
                unit, factor, figures = "W/(m·K)", 1, 3
                observation["conditions"]["temperature_K"] = 298.15
            observation["source_page"] = 2
            observation["source_value"] = {"text": literal, "unit": unit, "scale_to_si": factor,
                "offset_to_si": 0, "significant_figures": figures}
            observation["uncertainty"] = {"kind": "implied", "sigfigs": figures}


if __name__=="__main__": main()
