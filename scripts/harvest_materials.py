import json
import os
import urllib.request
import re
import csv
import io
import html

# Source URLs
SOURCES = {
    "nicoguaro_common": "https://raw.githubusercontent.com/nicoguaro/material_database/master/materials/common_materials.tsv",
    "nawale_metals": "https://raw.githubusercontent.com/purushottamnawale/material-selection-using-machine-learning/master/Data.csv",
    "oms_dataset": "https://raw.githubusercontent.com/mrealpe/OpenMaterialsSelector/master/datos.csv",
    "nims_fatigue": "https://raw.githubusercontent.com/George-JieXIONG/Materials-Dataset/main/Chapter4/NIMS-Fatigue.csv",
    "citrine_mpea": "https://raw.githubusercontent.com/CitrineInformatics/MPEA_dataset/master/MPEA_dataset.csv",
    "elena_low_alloy": "https://raw.githubusercontent.com/ElenaNKn/mechanical-properties/master/third_final_project/notebook/mechanical_properties_low-alloy_steels.csv",
    "a158_steel_strength": "https://raw.githubusercontent.com/A158-debug/Prediction-of-Mechanical-properties-of-Steel/master/steel_strength.csv"
}

OUTPUT_PATH = "data/materials/materials-review.json"

# Global Source Registry
SOURCE_REGISTRY = {
    "nicoguaro-2024": {
        "citation": "nicoguaro (2024). material_database. GitHub Repository. https://github.com/nicoguaro/material_database",
        "type": "online_database", "year": 2024
    },
    "nawale-2021": {
        "citation": "Nawale, P. (2021). material-selection-using-machine-learning. GitHub Repository. https://github.com/purushottamnawale/material-selection-using-machine-learning",
        "type": "online_database", "year": 2021
    },
    "oms-2020": {
        "citation": "Realpe, M. (2020). OpenMaterialsSelector. GitHub Repository. https://github.com/mrealpe/OpenMaterialsSelector",
        "type": "online_database", "year": 2020
    },
    "nims-fatigue-subset": {
        "citation": "NIMS (via George-JieXIONG). Materials-Dataset: NIMS-Fatigue.csv. https://github.com/George-JieXIONG/Materials-Dataset",
        "type": "experimental_database", "year": 2023
    },
    "citrine-mpea": {
        "citation": "Citrine Informatics. MPEA_dataset.csv. https://github.com/CitrineInformatics/MPEA_dataset",
        "type": "research_database", "year": 2016
    },
    "elena-low-alloy": {
        "citation": "ElenaNKn. mechanical_properties_low-alloy_steels.csv. https://github.com/ElenaNKn/mechanical-properties",
        "type": "research_database", "year": 2022
    },
    "a158-steel-strength": {
        "citation": "A158-debug. steel_strength.csv. https://github.com/A158-debug/Prediction-of-Mechanical-properties-of-Steel",
        "type": "research_database", "year": 2019
    },
    "point-solutions-2026": {
        "citation": "Expert Point Solutions Database (NIST AMMD approximations, Eco-Costs Idemat estimates).",
        "type": "handbook_range", "year": 2026
    }
}

def clean_value(val):
    if val is None: return None
    val = str(val).strip()
    if not val or val == "0" or val == "0.0" or val.lower() == "nan":
        return None
    try:
        return float(val.replace(",", "").strip())
    except ValueError:
        return None

def slugify(name):
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')

def map_family(category_str):
    c = category_str.lower()
    if any(x in c for x in ["metal", "steel", "alloy", "iron", "brass", "bronze", "copper", "aluminum", "titanium", "fcc", "bcc"]):
        return "metal"
    if any(x in c for x in ["polymer", "plastic", "thermoplastic", "thermoset", "elastomer", "nylon", "rubber"]):
        return "polymer"
    if any(x in c for x in ["ceramic", "glass", "oxide", "carbide", "nitride", "concrete", "stone", "quartz"]):
        return "ceramic"
    if any(x in c for x in ["composite", "fiber", "fabric"]):
        return "composite"
    if any(x in c for x in ["wood", "natural", "cork", "leather", "biological", "bone"]):
        return "natural"
    if "foam" in c:
        return "foam"
    return "other"

def fetch_url(url):
    print(f"Fetching {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def process_nicoguaro_common(data):
    lines = data.strip().split('\n')
    headers = [h.strip() for h in lines[0].split('\t')]
    idx = {h: i for i, h in enumerate(headers)}
    results = []
    for line in lines[1:]:
        row = line.split('\t')
        if len(row) < len(headers): continue
        name, cat = row[idx['Material']], row[idx['Category']]
        m = {
            "id": slugify("nic-" + name), "name": name, "family": map_family(cat),
            "sub_family": cat.lower(), "default_source_id": "nicoguaro-2024",
            "notes": f"Nicoguaro Common: {cat}"
        }
        def add_prop(key, low_h, high_h, factor=1.0):
            low, high = clean_value(row[idx[low_h]]), clean_value(row[idx[high_h]])
            if low is not None and high is not None:
                m[key] = {"value": (low + high)/2 * factor, "min": low * factor, "max": high * factor, "basis": "handbook_range"}
            elif low is not None:
                m[key] = {"value": low * factor, "basis": "handbook_range"}
        add_prop("youngs_modulus", "Young Modulus low", "Young Modulus high", 1e9)
        add_prop("density", "Density low", "Density high", 1.0)
        add_prop("yield_strength", "Yield Strength low", "Yield Strength high", 1e6)
        add_prop("tensile_strength", "Tensile Strength low", "Tensile Strength high", 1e6)
        add_prop("fracture_toughness", "Fracture Toughness low", "Fracture Toughness high", 1e6)
        add_prop("thermal_conductivity", "Thermal Conductivity low", "Thermal Conductivity high", 1.0)
        add_prop("cte", "Thermal Expansion low", "Thermal Expansion high", 1e-6)
        add_prop("electrical_resistivity", "Resistivity low", "Resistivity high", 1e-8)
        results.append(m)
    return results

def process_nawale_metals(data):
    f = io.StringIO(data)
    reader = csv.DictReader(f)
    results = []
    for row in reader:
        name, cond = row['Material'], row['Heat treatment']
        full_name = f"{name} ({cond})" if cond and cond.lower() != "nan" else name
        m = {
            "id": slugify("naw-" + full_name), "name": full_name, "family": "metal",
            "sub_family": "alloy", "condition": cond, "default_source_id": "nawale-2021",
            "notes": f"Nawale Metals Dataset. Std: {row['Std']}"
        }
        su, sy, e, ro, mu = clean_value(row['Su']), clean_value(row['Sy']), clean_value(row['E']), clean_value(row['Ro']), clean_value(row['mu'])
        if su: m["tensile_strength"] = {"value": su * 1e6, "basis": "typical"}
        if sy: m["yield_strength"] = {"value": sy * 1e6, "basis": "typical"}
        if e: m["youngs_modulus"] = {"value": e * 1e6, "basis": "typical"}
        if ro: m["density"] = {"value": ro, "basis": "typical"}
        if mu: m["poissons_ratio"] = {"value": mu, "basis": "typical"}
        results.append(m)
    return results

def process_oms_dataset(data):
    f = io.StringIO(data)
    reader = csv.DictReader(f)
    results = []
    for row in reader:
        name, cat = html.unescape(row['Name']), row['Category']
        m = {
            "id": slugify("oms-" + name), "name": name, "family": map_family(cat),
            "sub_family": cat.lower().replace(";", ","), "default_source_id": "oms-2020",
            "notes": f"OMS Dataset. URL: {row['url']}"
        }
        ro, e = clean_value(row['Density']), clean_value(row['Modulus of Elasticity'])
        if ro and ro < 0.001: ro = None
        if e and e < 0.001: e = None
        if ro: m["density"] = {"value": ro * 1000.0, "basis": "typical"}
        if e: m["youngs_modulus"] = {"value": e * 1e9, "basis": "typical"}
        if ro or e: results.append(m)
    return results

def process_nims_fatigue(data):
    f = io.StringIO(data)
    reader = csv.DictReader(f)
    results = []
    for i, row in enumerate(reader):
        c, si, mn, t_temp = row['C'], row['Si'], row['Mn'], row['Temperaing Temperature']
        name = f"NIMS Steel {c}C-{si}Si-{mn}Mn (T_temp={t_temp}C)"
        m = {
            "id": slugify(f"nims-steel-{i}"), "name": name, "family": "metal",
            "sub_family": "carbon-steel", "default_source_id": "nims-fatigue-subset",
            "notes": "Experimental NIMS Fatigue Data subset."
        }
        su, fs, hv = clean_value(row['Tensile Strength']), clean_value(row['Fatigue Strength (10E7 Cycles)']), clean_value(row['Hardness'])
        if su: m["tensile_strength"] = {"value": su * 1e6, "basis": "typical"}
        if fs: m["fatigue_strength_10e7"] = {"value": fs * 1e6, "basis": "typical"}
        if hv: m["hardness_vickers"] = {"value": hv, "basis": "typical"}
        results.append(m)
    return results

def process_citrine_mpea(data):
    f = io.StringIO(data)
    reader = csv.DictReader(f)
    results = []
    for i, row in enumerate(reader):
        formula = row.get('FORMULA') or row.get('IDENTIFIER: Reference ID')
        m = {
            "id": slugify(f"mpea-{formula}-{i}"), "name": formula, "family": "metal",
            "sub_family": "high-entropy-alloy", "default_source_id": "citrine-mpea",
            "notes": f"MPEA: {row.get('PROPERTY: Microstructure')}, Processing: {row.get('PROPERTY: Processing method')}"
        }
        ys, uts, el, e_exp, ro_exp, hv = clean_value(row.get('PROPERTY: YS (MPa)')), clean_value(row.get('PROPERTY: UTS (MPa)')), clean_value(row.get('PROPERTY: Elongation (%)')), clean_value(row.get('PROPERTY: Exp. Young modulus (GPa)')), clean_value(row.get('PROPERTY: Exp. Density (g/cm$^3$)')), clean_value(row.get('PROPERTY: HV'))
        if ys: m["yield_strength"] = {"value": ys * 1e6, "basis": "typical"}
        if uts: m["tensile_strength"] = {"value": uts * 1e6, "basis": "typical"}
        if el: m["elongation_at_break"] = {"value": el / 100.0, "basis": "typical"}
        if e_exp: m["youngs_modulus"] = {"value": e_exp * 1e9, "basis": "typical"}
        if ro_exp: m["density"] = {"value": ro_exp * 1000.0, "basis": "typical"}
        if hv: m["hardness_vickers"] = {"value": hv, "basis": "typical"}
        if ys or uts or e_exp: results.append(m)
    return results

def process_elena_low_alloy(data):
    f = io.StringIO(data)
    reader = csv.DictReader(f)
    results = []
    for i, row in enumerate(reader):
        comp = f"Low Alloy Steel C{row.get(' Carbon')}"
        m = {
            "id": slugify(f"elena-steel-{i}"), "name": comp, "family": "metal",
            "sub_family": "low-alloy-steel", "default_source_id": "elena-low-alloy",
            "notes": f"Experimental Steel Data. Temp: {row.get(' Temperature')}C"
        }
        ys, uts, el = clean_value(row.get(' 0.2% Proof Stress')), clean_value(row.get(' Tensile Strength')), clean_value(row.get(' Elongation'))
        if ys: m["yield_strength"] = {"value": ys * 1e6, "basis": "typical"}
        if uts: m["tensile_strength"] = {"value": uts * 1e6, "basis": "typical"}
        if el: m["elongation_at_break"] = {"value": el / 100.0, "basis": "typical"}
        if ys or uts: results.append(m)
    return results

def process_a158_steel_strength(data):
    f = io.StringIO(data)
    reader = csv.DictReader(f)
    results = []
    for i, row in enumerate(reader):
        name = f"Steel Alloy #{i}"
        m = {
            "id": slugify(f"a158-steel-{i}"), "name": name, "family": "metal",
            "sub_family": "alloy-steel", "default_source_id": "a158-steel-strength",
            "notes": "Steel Strength Prediction Dataset."
        }
        ys, uts, el = clean_value(row.get('yield strength')), clean_value(row.get('tensile strength')), clean_value(row.get('elongation'))
        if ys: m["yield_strength"] = {"value": ys * 1e6, "basis": "typical"}
        if uts: m["tensile_strength"] = {"value": uts * 1e6, "basis": "typical"}
        if el: m["elongation_at_break"] = {"value": el / 100.0, "basis": "typical"}
        if ys or uts: results.append(m)
    return results

def process_point_solutions():
    """Manually add specialized point solutions (AM Bench Additive, Eco/Embodied Carbon)."""
    solutions = []

    # --- 1. Additive Manufacturing (AM) Materials ---
    solutions.append({
        "id": "am-alsi10mg-dmls",
        "name": "AlSi10Mg (DMLS 3D Printed)",
        "family": "metal",
        "sub_family": "aluminum-alloy",
        "condition": "As-built (DMLS)",
        "default_source_id": "point-solutions-2026",
        "notes": "Typical properties for DMLS printed aluminum (NIST AM Bench reference)",
        "density": {"value": 2670.0, "basis": "typical"},
        "youngs_modulus": {"value": 60e9, "basis": "typical"},
        "yield_strength": {"value": 230e6, "basis": "typical"},
        "tensile_strength": {"value": 340e6, "basis": "typical"},
        "elongation_at_break": {"value": 0.05, "basis": "typical"},
        "processability": [{"process": "3d_printing", "rating": "excellent"}]
    })

    solutions.append({
        "id": "am-ti6al4v-dmls",
        "name": "Ti-6Al-4V (DMLS 3D Printed)",
        "family": "metal",
        "sub_family": "titanium-alloy",
        "condition": "As-built (DMLS)",
        "default_source_id": "point-solutions-2026",
        "notes": "Typical properties for DMLS printed titanium (NIST AM Bench reference)",
        "density": {"value": 4420.0, "basis": "typical"},
        "youngs_modulus": {"value": 110e9, "basis": "typical"},
        "yield_strength": {"value": 950e6, "basis": "typical"},
        "tensile_strength": {"value": 1050e6, "basis": "typical"},
        "elongation_at_break": {"value": 0.08, "basis": "typical"},
        "processability": [{"process": "3d_printing", "rating": "excellent"}]
    })

    solutions.append({
        "id": "am-pla-fdm",
        "name": "PLA (FDM 3D Printed)",
        "family": "polymer",
        "sub_family": "thermoplastic",
        "condition": "FDM 100% Infill",
        "default_source_id": "point-solutions-2026",
        "notes": "FDM 3D printed PLA. Properties highly dependent on print orientation.",
        "density": {"value": 1240.0, "basis": "typical"},
        "youngs_modulus": {"value": 2.3e9, "basis": "typical"},
        "tensile_strength": {"value": 45e6, "basis": "typical"},
        "glass_transition_temp": {"value": 60.0, "basis": "typical"},
        "processability": [{"process": "3d_printing", "rating": "excellent"}]
    })

    # --- 2. Eco / Sustainability Anchor Materials ---
    solutions.append({
        "id": "eco-concrete-c30",
        "name": "Concrete C30/37",
        "family": "ceramic",
        "sub_family": "concrete",
        "default_source_id": "point-solutions-2026",
        "notes": "Standard concrete mix. Eco data based on typical Idemat/ICE database.",
        "density": {"value": 2400.0, "basis": "typical"},
        "compressive_strength": {"value": 30e6, "basis": "typical"},
        "embodied_energy": {"value": 0.95, "basis": "typical", "notes": "MJ/kg"},
        "co2_footprint": {"value": 0.15, "basis": "typical", "notes": "kg CO2/kg"}
    })

    solutions.append({
        "id": "eco-steel-rebar",
        "name": "Steel Rebar (Recycled)",
        "family": "metal",
        "sub_family": "carbon-steel",
        "default_source_id": "point-solutions-2026",
        "notes": "100% Recycled steel rebar. Eco data based on typical Idemat/ICE database.",
        "density": {"value": 7850.0, "basis": "typical"},
        "youngs_modulus": {"value": 200e9, "basis": "typical"},
        "yield_strength": {"value": 500e6, "basis": "typical"},
        "embodied_energy": {"value": 9.5, "basis": "typical", "notes": "MJ/kg"},
        "co2_footprint": {"value": 0.85, "basis": "typical", "notes": "kg CO2/kg"}
    })

    solutions.append({
        "id": "eco-plywood",
        "name": "Plywood (Softwood)",
        "family": "natural",
        "sub_family": "wood",
        "default_source_id": "point-solutions-2026",
        "notes": "Softwood plywood. Includes carbon sequestration (biogenic carbon).",
        "density": {"value": 550.0, "basis": "typical"},
        "youngs_modulus": {"value": 8e9, "basis": "typical"},
        "embodied_energy": {"value": 15.0, "basis": "typical", "notes": "MJ/kg"},
        "co2_footprint": {"value": -1.2, "basis": "typical", "notes": "kg CO2/kg (negative due to sequestration)"}
    })

    return solutions

def main():
    all_materials = []
    data = fetch_url(SOURCES["nicoguaro_common"]); all_materials.extend(process_nicoguaro_common(data)) if data else None
    data = fetch_url(SOURCES["nawale_metals"]); all_materials.extend(process_nawale_metals(data)) if data else None
    data = fetch_url(SOURCES["oms_dataset"]); all_materials.extend(process_oms_dataset(data)) if data else None
    data = fetch_url(SOURCES["nims_fatigue"]); all_materials.extend(process_nims_fatigue(data)) if data else None
    data = fetch_url(SOURCES["citrine_mpea"]); all_materials.extend(process_citrine_mpea(data)) if data else None
    data = fetch_url(SOURCES["elena_low_alloy"]); all_materials.extend(process_elena_low_alloy(data)) if data else None
    data = fetch_url(SOURCES["a158_steel_strength"]); all_materials.extend(process_a158_steel_strength(data)) if data else None

    # Add Point Solutions
    all_materials.extend(process_point_solutions())

    output = {"sources": SOURCE_REGISTRY, "materials": all_materials}
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    print(f"Writing {len(all_materials)} materials to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    print("Done.")

if __name__ == "__main__":
    main()
