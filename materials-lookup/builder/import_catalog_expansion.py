#!/usr/bin/env python3
"""Import the October 2026 primary-source catalog expansion (offline).

Requires the private originals, PyMuPDF and BeautifulSoup for reconstruction
only. Builds and the public tools continue to use curated JSON. By default,
write a candidate report outside the repository; --apply installs a reviewed
batch. Once a source is in the manifest, its hash must match on every run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from builder.import_reference_tables import obs, pair, record, slug

DATE = "2026-10-03"
PSI = 6894.757293168
BASELINE_COMMIT = "e46b6ae"

# These published cells have ambiguous units/decimal placement, or conflict
# with the same table's shear modulus. Never repair them by guessing a value.
# Keeping the exact rejected literal makes the review reproducible.
CDA_DEFERRED_CELLS = {
    ("C15780", "Density"): (
        "0.038",
        "Implies 1,052 kg/m³ for copper; decimal/unit needs publisher confirmation",
    ),
    ("C90280", "Density"): (
        "8.81",
        "Implies 243,860 kg/m³; unit needs publisher confirmation",
    ),
    ("C14750", "SpecificHeatCapacity"): (
        "90",
        "Implies 376,812 J/(kg K); decimal/unit needs publisher confirmation",
    ),
    ("C18080", "ModulusofElasticityinTension"): (
        "185000",
        "Implies 1,276 GPa; decimal/unit needs publisher confirmation",
    ),
    ("C18085", "ModulusofElasticityinTension"): (
        "21",
        "Implies 0.145 GPa; unit needs publisher confirmation",
    ),
    ("C18085", "ThermalConductivity"): (
        "330",
        "Implies 571 W/(m K); unit needs publisher confirmation",
    ),
    ("C67340", "ThermalConductivity"): (
        "520",
        "Implies 900 W/(m K); unit needs publisher confirmation",
    ),
    ("C44270", "ModulusofElasticityinTension"): (
        "17",
        "Implies 0.117 GPa; unit needs publisher confirmation",
    ),
    ("C70335", "ModulusofElasticityinTension"): (
        "166",
        "Implies 1.145 GPa; unit needs publisher confirmation",
    ),
    ("C28340", "SpecificHeatCapacity"): (
        "0.9",
        "Implies 3,768 J/(kg K); decimal/unit needs publisher confirmation",
    ),
    ("C85560", "SpecificHeatCapacity"): (
        "0.9",
        "Implies 3,768 J/(kg K); decimal/unit needs publisher confirmation",
    ),
    ("C46250", "ModulusofElasticityinTension"): (
        "6600",
        "Implies 45.5 GPa; unusually low brass modulus needs confirmation",
    ),
    ("C27250", "ModulusofElasticityinTension"): (
        "6700",
        "Inconsistent with listed shear modulus 5750 ksi for brass",
    ),
    ("C27550", "ModulusofElasticityinTension"): (
        "7500",
        "Inconsistent with listed shear modulus 5450 ksi for brass",
    ),
}
CDA_REVIEW_RANGES = {
    "density": (6000, 11000),
    "youngs_modulus": (60e9, 220e9),
    "thermal_conductivity": (10, 450),
    "specific_heat": (100, 1000),
}


def clean(text: str) -> str:
    """Normalize layout whitespace, leaving significant digits intact."""
    return " ".join(text.replace("™", "").replace("®", "").split())


def numeric(text: str) -> bool:
    """True only for a complete positive decimal literal."""
    return bool(re.fullmatch(r"\d+(?:\.\d+)?|\.\d+", text))


class Batch:
    """Collect source-attributed additions without changing earlier records."""

    def __init__(self, source_dir: Path):
        self.directory = source_dir
        self.baseline = json.loads((ROOT / "curated/materials.json").read_text())[
            "materials"
        ]
        self.old_sources = {
            s["id"]: s
            for s in json.loads((ROOT / "curated/sources.json").read_text())["sources"]
        }
        self.old_documents = {
            s["id"]: s
            for s in json.loads((ROOT / "curated/reference-manifest.json").read_text())[
                "documents"
            ]
        }
        previous_report = ROOT / "curated/catalog-expansion-2026-10.json"
        previous = (
            json.loads(previous_report.read_text()) if previous_report.exists() else {}
        )
        self.prior_ids = set(previous.get("authored_ids", []))
        self.prior_source_ids = set(previous.get("source_ids", []))
        self.baseline_source_ids = self.old_sources.keys() - self.prior_source_ids
        self.baseline = [r for r in self.baseline if r["id"] not in self.prior_ids]
        self.existing = {r["id"] for r in self.baseline}
        self.existing_uns = {
            code
            for r in self.baseline
            for k, v in r["designations"].items()
            if k == "UNS"
            for code in re.findall(r"C\d{5}", v)
        }
        self.records: list[dict] = []
        self.sources: dict[str, dict] = {}
        self.documents: dict[str, dict] = {}
        self.review_source_ids: set[str] = set()
        self.excluded: list[dict] = []

    def source(
        self,
        sid: str,
        filename: str,
        title: str,
        publisher: str,
        url: str,
        revision: str,
        *,
        kind="manufacturer_datasheet",
    ) -> Path:
        """Read an original and enforce any previously accepted snapshot pin."""
        path = self.directory / filename
        if not path.exists() and filename.startswith("cda-C"):
            path = (
                self.directory / "expansion-2026-10/cda" / filename.removeprefix("cda-")
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        old = self.old_documents.get(sid)
        if old and old["sha256"] != digest:
            raise ValueError(f"{filename}: source differs from the reviewed snapshot")
        self.review_source_ids.add(sid)
        if sid not in self.baseline_source_ids:
            self.sources[sid] = {
                "id": sid,
                "title": title,
                "organization": publisher,
                "source_type": kind,
                "publication_date": None,
                "revision": revision,
                "url": url,
                "retrieved_date": DATE,
                "license": "Selected numerical facts with attribution. Source document not redistributed.",
                "notes": "October 2026 expansion. Reference/typical properties retain their source conditions; no design allowables inferred.",
                "sha256": digest,
            }
            self.documents[sid] = {
                "id": sid,
                "url": url,
                "filename": filename,
                "sha256": digest,
                "bytes": path.stat().st_size,
                "pages": None,
                "retrieved_date": DATE,
            }
        return path

    def pdf(
        self,
        sid: str,
        filename: str,
        title: str,
        publisher: str,
        url: str,
        revision: str,
    ):
        """Open a checked PDF and record its page count."""
        import pymupdf

        document = pymupdf.open(
            self.source(sid, filename, title, publisher, url, revision)
        )
        if sid in self.documents:
            self.documents[sid]["pages"] = len(document)
        return document

    def add(
        self,
        mid: str,
        name: str,
        parent: str,
        family: list[str],
        values: list[dict],
        note: str,
        *,
        aliases=(),
        designations=None,
    ) -> None:
        """Accept a distinct grade only when at least two properties are sourced."""
        if mid in self.existing:
            self.excluded.append(
                {"id": mid, "reason": "Already in the baseline catalog"}
            )
            return
        if any(r["id"] == mid for r in self.records):
            self.excluded.append({"id": mid, "reason": "Repeated source-table entry"})
            return
        properties = {v["property"] for v in values}
        if len(properties) < 2 or "density" not in properties:
            self.excluded.append(
                {"id": mid, "reason": "No density plus a second usable property"}
            )
            return
        pair(
            self.records,
            mid,
            name,
            parent,
            family,
            note,
            values,
            aliases=aliases,
            designations=designations,
        )

    def family(self, mid: str, name: str, parent: str, families: list[str]) -> None:
        """Create only missing taxonomy nodes, which never count as materials."""
        if mid not in self.existing and not any(r["id"] == mid for r in self.records):
            self.records.append(
                record(
                    mid,
                    name,
                    "family",
                    parent,
                    families,
                    f"Supplier grades of {name.lower()}.",
                )
            )


def schott(batch: Batch) -> None:
    """Read each named SCHOTT glass sheet, retaining its individual revision."""
    sid = "schott-optical-glass"
    old = batch.old_sources[sid]
    document = batch.pdf(
        sid,
        "schott-optical-glass.pdf",
        old["title"],
        old["organization"],
        old["url"],
        old["revision"],
    )
    fields = [
        ("density", r"r \[g/cm3\]\n([\d.]+)\n", "Density rho", 1000, "g/cm³"),
        (
            "youngs_modulus",
            r"E \[103 N/mm2\]\n([\d.]+)\n",
            "Elasticity modulus E",
            1e9,
            "10³ N/mm²",
        ),
        ("poissons_ratio", r"µ\n([\d.]+)\n", "Poisson's ratio mu", 1, "1"),
        (
            "thermal_conductivity",
            r"l \[W/\(m[•*]K\)\]\n([\d.]+)\n",
            "Thermal conductivity lambda",
            1,
            "W/(m·K)",
        ),
        (
            "specific_heat",
            r"cp \[J/\(g\*K\)\]\n([\d.]+)\n",
            "Specific heat capacity cp",
            1000,
            "J/(g·K)",
        ),
    ]
    for page in document:
        text = page.get_text()
        if not text.startswith("Datasheet\n"):
            continue
        name = text.splitlines()[1].replace("®", "").removeprefix("SCHOTT ")
        if "HT" in name:
            batch.excluded.append(
                {
                    "id": "schott-" + slug(name),
                    "reason": "High-transmission version; not counted as another base glass",
                }
            )
            continue
        revision = re.search(r"As of ([^\n]+)", text)
        note = (
            "Optical glass reference data; "
            + (revision[0] if revision else "individual sheet date not given")
            + ". Test temperature not specified for these rows."
        )
        values = []
        for prop, pattern, label, factor, unit in fields:
            match = re.search(pattern, text)
            if match:
                values.append(
                    obs(
                        prop,
                        match[1],
                        sid,
                        page.number + 1,
                        name + ", Other Properties",
                        label,
                        method="Supplier reference property; method not stated on sheet",
                        conditions={"material_state": note},
                        factor=factor,
                        raw_unit=unit,
                        basis="reference",
                    )
                )
        batch.add(
            "schott-" + slug(name),
            "SCHOTT " + name,
            "glasses",
            ["glass", "optical-glass"],
            values,
            "Named optical glass composition; mechanical and thermal reference values.",
            aliases=[name],
            designations={"Supplier": name},
        )


def ohara(batch: Batch) -> None:
    """Read OHARA's named glass sheets; optical precision is not a new grade."""
    sid = "ohara-optical-glass-2025"
    document = batch.pdf(
        sid,
        "ohara-optical-glass.pdf",
        "Optical glass: all detailed data",
        "OHARA",
        "https://oharacorp.com/wp-content/uploads/2025/04/all-detailed-data-20250418.pdf",
        "OHARA 25-04",
    )
    batch.pdf(
        "ohara-catalog-methods-2023",
        "ohara-pocket-catalog.pdf",
        "Optical glass pocket catalog: property definitions",
        "OHARA",
        "https://oharacorp.com/wp-content/uploads/2023/06/ohara-pocket-catalog-2023-05.pdf",
        "May 2023; density definition p. 85",
    )
    batch.source(
        "ohara-mechanical-methods",
        "ohara-mechanical-methods.html",
        "Mechanical Properties, section 5.1: Modulus of Elasticity",
        "OHARA",
        "https://oharacorp.com/optical-glass/mechanical-properties/",
        "Public method description, October 2026",
        kind="supplier_catalog",
    )
    for page in document:
        text = page.get_text()
        header = clean(page.get_text(clip=(0, 0, page.rect.width, 30))).replace(" ", "")
        names = re.findall(r"\b(?:[LS]-[A-Z]+\d+[A-Z]*|[A-Z]+\d+[A-Z]*)\b", header)
        if len(names) != 1:
            raise ValueError(f"OHARA p.{page.number + 1}: ambiguous grade {header!r}")
        name = names[0]
        if name in {"S-LAH99W", "S-NPH1W", "S-TIH53W", "S-TIH53WN"}:
            batch.excluded.append(
                {
                    "id": "ohara-" + slug(name),
                    "reason": "Transmission variant of an included base glass; not counted separately",
                }
            )
            continue
        note = "Annealed optical glass; room-temperature elastic-wave measurements. Numerical data: OHARA 25-04; method: OHARA Mechanical Properties, section 5.1."
        values = []
        for prop, pattern, label, factor, unit in [
            (
                "density",
                r"Specific Gravity d\n([\d.]+)\n",
                "Specific gravity d",
                1000,
                "g/cm³ (catalog density convention)",
            ),
            (
                "youngs_modulus",
                r"Young's Modulus E \(GPa\)\n([\d.]+)\n",
                "Young's modulus E",
                1e9,
                "GPa",
            ),
            (
                "poissons_ratio",
                r"Poisson's Ratio σ\n([\d.]+)\n",
                "Poisson's ratio",
                1,
                "1",
            ),
        ]:
            match = re.search(pattern, text)
            if not match:
                raise ValueError(f"OHARA {name}: missing {prop}")
            condition = (
                note
                if prop != "density"
                else "Well-annealed glass. OHARA May 2023 catalog p. 85 equates tabulated specific gravity d to density in g/cm³ at the reported precision; water reference at 4 °C."
            )
            values.append(
                obs(
                    prop,
                    match[1],
                    sid,
                    page.number + 1,
                    name,
                    label,
                    method="Supplier catalog: elastic-wave method"
                    if prop != "density"
                    else "JIS Z 8807; supplier density convention, g/cm³ converted to SI",
                    conditions={"material_state": condition},
                    factor=factor,
                    raw_unit=unit,
                    basis="reference",
                )
            )
        # Thermal conductivity has a stable right-hand cell; reading-order text
        # interleaves optical columns and is deliberately not used for this row.
        words = page.get_text("words")
        label = page.search_for("Thermal Conductivity")
        if len(label) == 1:
            rect = label[0]
            numbers = [
                w[4]
                for w in words
                if w[0] > 520 and abs(w[1] - rect.y0) < 2 and numeric(w[4])
            ]
            if len(numbers) == 1:
                values.append(
                    obs(
                        "thermal_conductivity",
                        numbers[0],
                        sid,
                        page.number + 1,
                        name,
                        "Thermal conductivity lambda",
                        method="Supplier catalog reference property",
                        conditions={
                            "material_state": "Optical glass reference value; measurement temperature not specified on this sheet."
                        },
                        factor=1,
                        raw_unit="W/(m·K)",
                        basis="reference",
                    )
                )
        batch.add(
            "ohara-" + slug(name),
            "OHARA " + name,
            "glasses",
            ["glass", "optical-glass"],
            values,
            "Named OHARA optical glass composition.",
            aliases=[name],
            designations={"Supplier": name},
        )


def cda(batch: Batch) -> None:
    """Import grade-level physical facts, not fabricated temper-independent strengths."""
    from bs4 import BeautifulSoup

    paths = sorted((batch.directory / "expansion-2026-10/cda").glob("C[0-9]*.html"))
    if not paths:
        paths = sorted(batch.directory.glob("cda-C[0-9]*.html"))
    for path in paths:
        code = path.stem.removeprefix("cda-")
        # A previously reviewed single-page download can predate the bulk
        # cache. Parse the same original whose hash source() will publish.
        flat_path = batch.directory / ("cda-" + code + ".html")
        if flat_path.exists():
            path = flat_path
        if code in batch.existing_uns:
            batch.excluded.append(
                {
                    "id": code,
                    "reason": "UNS designation already in the baseline catalog",
                }
            )
            continue
        soup = BeautifulSoup(path.read_text(), "html.parser")
        table = soup.find("table", id=code + "-physical-properties-table")
        if table is None:
            batch.excluded.append({"id": code, "reason": "No physical-property table"})
            continue
        sid = "cda-" + code.lower()
        values = []
        for key, prop, unit, factor, temperature in [
            ("Density", "density", "lb/cu in. at 68°F", 0.45359237 / 0.0254**3, 293.15),
            ("ModulusofElasticityinTension", "youngs_modulus", "ksi", PSI * 1000, None),
            (
                "ThermalConductivity",
                "thermal_conductivity",
                "Btu/ sq ft/ ft hr/ °F at 68°F",
                1.7307346663714,
                293.15,
            ),
            (
                "SpecificHeatCapacity",
                "specific_heat",
                "Btu/lb/°F at 68°F",
                4186.8,
                293.15,
            ),
        ]:
            header = table.find("th", id=f"{code}-physical-{key}-header")
            if not header:
                continue
            raw = clean(header.find_next_sibling("td").get_text())
            if not numeric(raw):
                continue
            label_unit = header.select_one(".measurement-unit-label").get_text(
                strip=True
            )
            if label_unit.replace(" ", "") != unit.replace(" ", ""):
                raise ValueError(f"{code}/{key}: unreviewed unit {label_unit!r}")
            deferred = CDA_DEFERRED_CELLS.get((code, key))
            if deferred:
                expected, reason = deferred
                if raw != expected:
                    raise ValueError(
                        f"{code}/{key}: deferred cell changed; review required"
                    )
                batch.excluded.append(
                    {
                        "id": code + "/" + key,
                        "source_value": raw,
                        "source_unit": label_unit,
                        "reason": reason,
                    }
                )
                continue
            low, high = CDA_REVIEW_RANGES[prop]
            if not low <= float(raw) * factor <= high:
                raise ValueError(
                    f"{code}/{key}: outside the reviewed range; inspect the source"
                )
            condition = {
                "material_state": "CDA grade-level reference approximation. No temper or product-form attribution. Values are not specification limits."
            }
            if temperature is not None:
                condition["temperature_K"] = temperature
            value = obs(
                prop,
                raw,
                sid,
                1,
                code + ", Physical Properties",
                key,
                method="CDA alloy reference table; underlying measurement method not specified",
                conditions=condition,
                factor=factor,
                raw_unit=label_unit,
                basis="reference",
            )
            value["source_locator"] = (
                f"{code}, public alloy reference, Physical Properties, {key}"
            )
            values.append(value)
        if len(values) >= 2 and any(v["property"] == "density" for v in values):
            batch.source(
                sid,
                "cda-" + code + ".html",
                code + " alloy reference: physical properties",
                "Copper Development Association",
                "https://alloys.copper.org/alloy/" + code,
                "Public reference snapshot, October 2026",
                kind="supplier_catalog",
            )
        else:
            batch.excluded.append(
                {
                    "id": code,
                    "reason": "No density plus a second usable physical property",
                }
            )
            continue
        number = int(code[1:])
        # UNS group boundaries distinguish brasses, bronzes and nickel-bearing
        # copper alloys. Keep copper as the common broad chart family.
        if 20000 <= number < 50000 or 83300 <= number < 90000:
            parent, subgroup = "brasses", "brass"
        elif 50000 <= number < 70000 or 90000 <= number < 96000:
            parent, subgroup = "bronzes", "bronze"
        else:
            parent, subgroup = "copper-alloys", "copper-alloy"
        trade = soup.select_one(".tradename")
        trade_name = clean(trade.get_text()) if trade else ""
        alloy_class = soup.select_one(".alloy-class")
        class_name = clean(alloy_class.get_text()) if alloy_class else "Copper alloy"
        batch.add(
            "cda-" + code.lower(),
            code + (" " + trade_name if trade_name else " copper alloy"),
            parent,
            ["metal", "copper", subgroup],
            values,
            "UNS " + code + "; grade-level CDA physical reference data.",
            aliases=[code, "UNS " + code, class_name]
            + ([trade_name] if trade_name else []),
            designations={"UNS": code},
        )


def woods(batch: Batch) -> None:
    """Read USDA table 5-3a at 12% moisture, with explicit density conversion."""
    sid = "usda-wood-mechanical"
    old = batch.old_sources[sid]
    document = batch.pdf(
        sid,
        "usda-wood-mechanical.pdf",
        old["title"],
        old["organization"],
        old["url"],
        old["revision"],
    )
    formula = batch.old_sources["usda-wood-handbook"]
    batch.source(
        "usda-wood-handbook",
        "usda-wood-physical.pdf",
        formula["title"],
        formula["organization"],
        formula["url"],
        formula["revision"],
        kind="government_handbook",
    )
    group = ""
    subgroup = "hardwood"
    for index in range(3, 8):
        page = document[index]
        words = page.get_text("words")
        moisture_rows = [w[1] for w in words if w[4] == "12%" and 145 < w[0] < 175]
        last_y = max(moisture_rows)
        lines: dict[float, list] = {}
        for word in words:
            if 132 < word[1] < last_y + 2:
                y = next((y for y in lines if abs(y - word[1]) < 1.5), word[1])
                lines.setdefault(y, []).append(word)
        for y, row in sorted(lines.items()):
            name_words = sorted((w for w in row if w[0] < 140), key=lambda w: w[0])
            label = " ".join(w[4] for w in name_words)
            if not label:
                continue
            if label == "Softwoods" or label == "Baldcypress":
                subgroup = "softwood"
            if "Green" not in [w[4] for w in row] or not any(
                180 < w[0] < 210 for w in row
            ):
                if label not in ("Hardwoods", "Softwoods"):
                    group = (
                        label.replace("—con.", "")
                        .replace("trued", "true")
                        .replace("Douglas-fire", "Douglas-fir")
                    )
                continue
            child = name_words[0][0] > 60
            source_row = group + ": " + label if child else label
            # Regional Douglas-fir populations and growth-age classes are not
            # new species. Keep the baseline Coast Douglas-fir and one redwood.
            if group == "Douglas-fir" and child:
                batch.excluded.append(
                    {
                        "id": source_row,
                        "reason": "Douglas-fir already present; regional population is not a new material",
                    }
                )
                continue
            if group == "Redwood" and child:
                if label != "Old-growth":
                    batch.excluded.append(
                        {
                            "id": source_row,
                            "reason": "Redwood growth-age condition, not a new species",
                        }
                    )
                    continue
                name = "Redwood"
            elif not child:
                name = (
                    " ".join(reversed(label.lower().split(", ")))
                    if ", " in label
                    else label
                )
                name = name[0].upper() + name[1:]
            elif label in (
                "Balsam poplar",
                "Cucumbertree",
                "Pecan",
                "Eastern redcedar",
                "Western redcedar",
            ):
                name = label
            else:
                name = label + " " + group.split(",")[0].lower()
            row_y = next((yy for yy in moisture_rows if 8 < yy - y < 13), None)
            if row_y is None:
                raise ValueError(f"USDA {source_row}: no matching 12% row")
            cells = [
                w[4]
                for w in sorted(words, key=lambda w: w[0])
                if abs(w[1] - row_y) < 2 and 180 < w[0] < 300
            ]
            if len(cells) != 3:
                raise ValueError(
                    f"USDA {source_row}: expected G12/MOR/MOE, found {cells}"
                )
            gravity, strength, modulus = cells
            note = "Small clear specimens; 12% moisture content on oven-dry mass basis; longitudinal bending."
            if name == "Redwood":
                note += " Old-growth reference population."
            common = {"moisture_content_1": 0.12, "material_state": note}
            values = []
            if numeric(gravity):
                values.append(
                    obs(
                        "density",
                        gravity,
                        sid,
                        index + 1,
                        "Table 5-3a, " + source_row + ", 12% MC",
                        "Specific gravity",
                        method="Computed using Wood Handbook Eq. (4-12), printed p. 4-10 (full handbook PDF p. 89)",
                        conditions={
                            **common,
                            "material_state": note
                            + " rho12 = G12 × 1000 × (1 + 0.12) kg/m³; G12 uses oven-dry mass and volume at 12% MC.",
                        },
                        basis="computed",
                        factor=1120,
                        raw_unit="1 (G12)",
                    )
                )
            for prop, raw, label, factor, unit in [
                (
                    "flexural_strength",
                    strength,
                    "Static bending modulus of rupture",
                    1000,
                    "kPa",
                ),
                (
                    "flexural_modulus",
                    modulus,
                    "Static bending modulus of elasticity",
                    1e6,
                    "MPa",
                ),
            ]:
                if numeric(raw.replace(",", "")):
                    values.append(
                        obs(
                            prop,
                            raw,
                            sid,
                            index + 1,
                            "Table 5-3a, " + source_row + ", 12% MC",
                            label,
                            method="Simply supported, center-loaded beam; span/depth 14:1; no shear correction applied",
                            conditions={**common, "orientation": "L"},
                            factor=factor,
                            raw_unit=unit,
                            basis="reference",
                        )
                    )
            batch.add(
                "wood-" + slug(name),
                name,
                "woods",
                ["wood", subgroup],
                values,
                note,
                aliases=[source_row, name + " wood", subgroup],
            )


def smooth_on(batch: Batch) -> None:
    """Read manufacturer comparison cells without substituting rubber moduli."""
    from bs4 import BeautifulSoup

    sid = "smooth-on-comparison-2026"
    path = batch.source(
        sid,
        "smooth-on-charts-2026.html",
        "Material comparison charts",
        "Smooth-On",
        "https://www.smooth-on.com/charts/",
        "Public comparison chart, October 2026",
        kind="supplier_catalog",
    )
    soup = BeautifulSoup(path.read_text(), "html.parser")
    for filename, title, url in [
        (
            "smooth-on-epoxacoat.pdf",
            "EpoxAcoat Series technical bulletin: laminate footnote",
            "https://www.smooth-on.com/tb/files/EPOXACOAT_SERIES_TB.pdf",
        ),
        (
            "smooth-on-epoxacast-655.pdf",
            "EpoxAcast 655 technical bulletin: mixed density and cured properties",
            "https://www.smooth-on.com/tb/files/EPOXACAST_655_TB.pdf",
        ),
        (
            "smooth-on-plasti-paste-epoxy.pdf",
            "Plasti-Paste EPOXY technical bulletin: property definitions",
            "https://www.smooth-on.com/tb/files/PLASTI-PASTE_EPOXY_TB.pdf",
        ),
    ]:
        batch.pdf(
            filename.removesuffix(".pdf"),
            filename,
            title,
            "Smooth-On",
            url,
            "Pinned technical bulletin; used to review deferred comparison rows",
        )
    groups = {
        "tin-silicone-tbl": ("elastomers", "elastomer", "silicone"),
        "platinum-silicone-tbl": ("elastomers", "elastomer", "silicone"),
        "urethane-rubber-tbl": ("elastomers", "elastomer", "polyurethane"),
        "urethane-resin-tbl": ("polymer-polyurethane", "polymer", "polyurethane"),
        "epoxy-tbl": ("polymer-epoxy", "polymer", "epoxy"),
        "polysulfide-tbl": ("elastomers", "elastomer", "polysulfide"),
    }
    batch.family(
        "polymer-polyurethane",
        "Casting polyurethanes",
        "engineering-plastics",
        ["polymer", "polyurethane"],
    )
    batch.family(
        "polymer-epoxy",
        "Epoxy casting resins",
        "engineering-plastics",
        ["polymer", "epoxy"],
    )
    skip_names = {
        "Body Double Fast Set": "Body Double Standard Set",
        "Dragon Skin 10 FAST": "Dragon Skin 10 MEDIUM",
        "Dragon Skin 10 SLOW": "Dragon Skin 10 MEDIUM",
        "Dragon Skin 10 VERY FAST": "Dragon Skin 10 MEDIUM",
        "Ecoflex 00-20 FAST": "Ecoflex 00-20",
        "PMC-746 Clear Amber": "PMC-746",
        "Shell Shock SLOW": "Shell Shock FAST",
        "Smooth-Cast 300Q": "Smooth-Cast 300",
        "Smooth-Cast ONYX SLOW": "Smooth-Cast ONYX FAST",
        "EpoxAcoat GREY": "EpoxAcoat NEUTRAL",
        "EpoxAcoat RED": "EpoxAcoat NEUTRAL",
        "EpoxAcoat WHITE": "EpoxAcoat NEUTRAL",
        "EpoxAmite WHITE 101": "EpoxAmite 101",
        "EpoxAmite WHITE 102": "EpoxAmite 102",
        "Free Form AIR FAST": "Free Form AIR",
        "EpoxAcast 650 + 102 Hardener": "EpoxAcast 650 + 101 Hardener",
        "EpoxAcast 650 + 103 Hardener": "EpoxAcast 650 + 101 Hardener",
        "EpoxAcast 655 + 102 Hardener": "EpoxAcast 655 + 101 Hardener",
        "EpoxAcast 655 + 103 Hardener": "EpoxAcast 655 + 101 Hardener",
        "EpoxAmite 102": "EpoxAmite 101",
        "EpoxAmite 103": "EpoxAmite 101",
        "Equinox 38 MEDIUM": "Equinox 35 FAST",
        "Equinox 40 SLOW": "Equinox 35 FAST",
        "Crystal Clear 206": "Crystal Clear 200",
        "Crystal Clear 204": "Crystal Clear 202",
        "Crystal Clear 221": "Crystal Clear 220",
        "Smooth-Cast 305": "Smooth-Cast 300",
        "Smooth-Cast 310": "Smooth-Cast 300",
        "Smooth-Cast 321": "Smooth-Cast 320",
        "Smooth-Cast 322": "Smooth-Cast 320",
        "Smooth-Cast 326": "Smooth-Cast 325",
        "Smooth-Cast 327": "Smooth-Cast 325",
        "Smooth-Cast 66D": "Smooth-Cast 65D",
        "TASK 3": "TASK 2",
        "TASK 14": "TASK 13",
    }
    for table_id, (parent, family, chemistry) in groups.items():
        table = soup.find("table", id=table_id)
        if table is None:
            raise ValueError(f"Missing Smooth-On table {table_id}")
        for tr in table.select("tbody tr"):
            cells = {
                td["data-spec"]: clean(td.get_text(" ", strip=True)).lstrip("› ")
                for td in tr.select("td[data-spec]")
            }
            name = cells["product-name"].replace("~", "-")
            if name in skip_names or name.startswith("EpoxAcast 650 BLACK"):
                batch.excluded.append(
                    {
                        "id": name,
                        "reason": "Color/cure-speed variant; not counted separately from "
                        + skip_names.get(name, "EpoxAcast 650"),
                    }
                )
                continue
            if name == "EpoxAcoat NEUTRAL":
                batch.excluded.append(
                    {
                        "id": name,
                        "reason": "Bulletin p. 1: strength is for a 6-ply laminate, density for the mixed resin; no matching pair",
                    }
                )
                continue
            if name.startswith("EpoxAcast 655 +") or name == "Plasti-Paste EPOXY":
                batch.excluded.append(
                    {
                        "id": name,
                        "reason": "Bulletin p. 1: coating/mixed-resin density is not a verified cured-material density; defer this formulation",
                    }
                )
                continue
            # Some products appear in multiple comparison families. The rubber
            # table owns elastomers; the resin table owns StyroCoat/UreCoat.
            if table_id == "epoxy-tbl" and (
                name in ("EZ-Spray StyroCoat", "UreCoat") or "Powder" in name
            ):
                batch.excluded.append(
                    {
                        "id": name,
                        "reason": "Cross-listed product or additive, not another cured resin",
                    }
                )
                continue
            condition_parts = [
                "Manufacturer comparison row; test method, test age and temperature are not stated on this web chart."
            ]
            for key, label in [
                ("mix-ratio-by-weight", "A:B by mass"),
                ("cure-time", "Listed cure time"),
            ]:
                if cells.get(key):
                    condition_parts.append(label + ": " + cells[key] + ".")
            condition = {"material_state": " ".join(condition_parts)}
            values = []
            seen_properties = set()
            for key, prop, unit, factor in [
                ("specific-gravity", "density", "g/cc", 1000),
                ("tensile-strength", "tensile_strength", "psi", PSI),
                ("ultimate-tensile", "tensile_strength", "psi", PSI),
                ("tensile-modulus", "youngs_modulus", "psi", PSI),
                ("flexural-modulus-psi", "flexural_modulus", "psi", PSI),
                ("flexural-strength", "flexural_strength", "psi", PSI),
                ("elongation-break", "elongation_at_break", "%", 0.01),
            ]:
                text = cells.get(key, "")
                if not text or prop in seen_properties:
                    continue
                match = re.fullmatch(r"([\d,.]+)\s*" + re.escape(unit), text)
                if not match:
                    batch.excluded.append(
                        {
                            "id": name + "/" + key,
                            "reason": "Cell requires separate review: " + text,
                        }
                    )
                    continue
                cell_conditions = dict(condition)
                if prop == "density":
                    cell_conditions["material_state"] += (
                        " Specific gravity is reported in g/cc; the web row does not identify the density specimen's physical state."
                    )
                value = obs(
                    prop,
                    match[1],
                    sid,
                    1,
                    name + ", " + table_id,
                    key,
                    method="Manufacturer comparison chart; test method not specified for this cell",
                    conditions=cell_conditions,
                    factor=factor,
                    raw_unit=unit,
                    basis="reference",
                )
                value["source_locator"] = (
                    f"Comparison chart {table_id}, product {name}, field {key}"
                )
                values.append(value)
                seen_properties.add(prop)
            batch.add(
                "smooth-on-" + slug(name),
                name,
                parent,
                [family, chemistry],
                values,
                "Smooth-On "
                + chemistry
                + " formulation; manufacturer comparison properties with source conditions retained.",
                aliases=["Smooth-On " + name, chemistry],
                designations={"Supplier": name},
            )


def diab(batch: Batch) -> None:
    """Read foam density and tension rows, keeping nominal and minimum distinct."""
    for series, url, revision in [
        (
            "HP",
            "https://diab-media.azureedge.net/enygao3k/diab-divinycell-hp-may-2026-rev29-si.pdf",
            "Rev29, May 2026",
        ),
        (
            "HT",
            "https://diab-media.azureedge.net/a4vdf1t3/diab-divinycell-ht-may-2026-rev-17-si.pdf",
            "Rev17, May 2026",
        ),
        (
            "HCP",
            "https://diab-media.azureedge.net/vtyojx0b/diab-divinycell-hcp-may-2026-rev23-si.pdf",
            "Rev23, May 2026",
        ),
    ]:
        sid = "diab-" + series.lower()
        document = batch.pdf(
            sid,
            sid + ".pdf",
            "Divinycell " + series + " technical data, SI",
            "Diab",
            url,
            revision,
        )
        text = document[0].get_text()
        grades = re.findall(r"^" + series + r"\s?\d+$", text, re.MULTILINE)
        fields = [
            (
                "Density",
                "density",
                1,
                "kg/m³",
                "ISO 845" if series != "HT" else "ASTM D1622",
            ),
            ("Tensile Strength1", "tensile_strength", 1e6, "MPa", "ASTM D1623"),
            ("Tensile Modulus1", "youngs_modulus", 1e6, "MPa", "ASTM D1623"),
        ]
        by_grade = [[] for _ in grades]
        for label, prop, factor, unit, method in fields:
            match = re.search(
                r"^\s*" + label + r"\n[^\n]+\n[^\n]+\nNominal\n((?:[\d.]+\n)+)",
                text,
                re.MULTILINE,
            )
            if not match:
                if prop == "youngs_modulus" and series != "HP":
                    continue
                raise ValueError(f"{sid}: missing {label}")
            numbers = match[1].splitlines()
            if len(numbers) != len(grades):
                raise ValueError(f"{sid}/{label}: misaligned columns")
            for i, (grade, raw) in enumerate(zip(grades, numbers)):
                condition = {
                    "temperature_K": 296.15,
                    "material_state": "Nominal average at nominal density.",
                }
                if prop != "density":
                    condition.update(orientation="ST")
                    condition["material_state"] += (
                        " Through thickness, perpendicular to the sheet plane."
                    )
                by_grade[i].append(
                    obs(
                        prop,
                        raw,
                        sid,
                        1,
                        grade + ", nominal",
                        label,
                        method=method,
                        conditions=condition,
                        factor=factor,
                        raw_unit=unit,
                    )
                )
        for grade, values in zip(grades, by_grade):
            name = "Divinycell " + grade.replace(" ", "")
            batch.add(
                "diab-" + slug(name),
                name,
                "foams",
                ["foam", "pvc-foam"],
                values,
                "Diab closed-cell PVC structural foam; nominal density and through-thickness tension properties.",
                aliases=["Diab " + name, "PVC foam"],
                designations={"Supplier": name},
            )


MCAM_COLUMNS = {
    15: [
        "Duratron CU60 PBI",
        "Duratron D7000 PI",
        "Duratron D7015G PI",
        "Duratron T4203 PAI",
        "Duratron T4503 PAI",
        "Duratron T4301 PAI",
        "Duratron T4501 PAI",
        "Duratron T5530 PAI",
        "Semitron ESd 520HR PAI",
    ],
    16: [
        "Duratron U1000 PEI",
        "Fluorosint 207 PTFE",
        "Fluorosint HPV PTFE",
        "Fluorosint 500 PTFE",
        "Fluorosint MT-01 PTFE",
        "Fluorosint 135 PTFE",
        "Ketron 1000 PEEK",
        "Ketron CA30 PEEK",
        "Ketron GF30 PEEK",
    ],
    17: [
        "Ketron HPV PEEK",
        "Ketron VMX Food Grade PEEK",
        "Sultron PSU",
        "Semitron ESd 410C PEI",
        "Semitron ESd 420 PEI",
        "Semitron ESd 420V PEI",
        "Semitron MDS 100 PEEK",
        "Semitron ESd 480 PEEK",
        "Semitron ESd 490HR PEEK",
    ],
    18: [
        "Semitron ESd 500 HR PTFE",
        "Semitron HPV ESd PEEK",
        "Semitron MPR-1000 PAI",
        "Semitron MP-370 PEEK",
        "Techtron 1000 PPS",
        "Techtron HPV PPS",
    ],
    19: [
        "Acetron GP POM-C / Ertacetal C POM-C",
        "Acetron VMX Food Grade POM-C",
        "Semitron ESd 225 POM-C",
        "Acetron POM-H / Ertacetal H POM-H",
        "Acetron AF Blend POM-H / Ertacetal H-TF POM-H",
        "Nylatron 4.6 PA4.6 / Ertalon 4.6 PA4.6",
        "Nylatron MC 907 PA6 / Ertalon 6PLA PA6",
        "Nylatron GSM PA6",
        "Nylatron NSM PA6",
    ],
    20: [
        "Nylatron 703 XL PA6",
        "Nylatron 101 PA66 / Ertalon 66 SA PA66",
        "Nylatron GF30 PA66 / Ertalon 66 GF30 PA66",
        "Nylatron GS PA66",
        "Ertalyte PET",
        "Ertalyte TX PET",
        "Altron PC",
    ],
    21: [
        "TIVAR 1000 natural UHMW-PE",
        "TIVAR 1000 UHMW-PE colors",
        "TIVAR ESD UHMW-PE / TIVAR 1000 antistatic UHMW-PE",
        "TIVAR 1000 EC UHMW-PE",
        "TIVAR ECO ESD UHMW-PE / TIVAR ECO black antistatic UHMW-PE",
        "TIVAR 88 UHMW-PE",
        "TIVAR 88 W/BurnGuard UHMW-PE / TIVAR Burnguard UHMW-PE",
        "TIVAR CERAM P UHMW-PE",
        "TIVAR CleanStat UHMW-PE",
    ],
    22: [
        "TIVAR DrySlide UHMW-PE",
        "TIVAR H.O.T. UHMW-PE",
        "TIVAR HPV UHMW-PE",
        "TIVAR Oil Filled UHMW-PE",
        "TIVAR SuperPlus UHMW-PE",
        "TIVAR VMX Food Grade UHMW-PE",
        "Proteus White Homopolymer PP",
    ],
}


def mcam(batch: Batch) -> None:
    """Read the guide's ASTM tables; regional aliases occupy one column/grade."""
    sid = "mcg-design-guide-2023"
    document = batch.pdf(
        sid,
        "mcam-design-guide.pdf",
        "Engineering plastics design guide: ASTM material selection tables",
        "Mitsubishi Chemical Group, Advanced Materials",
        "https://www.mcam.com/mam/44687/MCG-ENGG-Design-Guide-LIT-EN-230530.pdf",
        "LIT-EN-230530, 2023",
    )
    batch.family(
        "polymer-pbi",
        "Polybenzimidazole (PBI)",
        "engineering-plastics",
        ["polymer", "PBI"],
    )
    batch.family(
        "polymer-uhmw-pe",
        "Ultra-high-molecular-weight polyethylene (UHMW-PE)",
        "engineering-plastics",
        ["polymer", "UHMW-PE"],
    )
    for number, names in MCAM_COLUMNS.items():
        text = document[number - 1].get_text()
        rows = []
        for label, prop, method, printed_unit, source_unit, factor in [
            (
                r"Specific gravity",
                "density",
                "ASTM D792",
                "-",
                "1 (specific gravity)",
                1000,
            ),
            (
                r"Tensile strength,\s*ultimate",
                "tensile_strength",
                "ASTM D638",
                "psi",
                "psi",
                PSI,
            ),
            (
                r"Elongation at break",
                "elongation_at_break",
                "ASTM D638",
                "%",
                "%",
                0.01,
            ),
            (
                r"Tensile modulus",
                "youngs_modulus",
                "ASTM D638",
                "ksi",
                "ksi",
                PSI * 1000,
            ),
            (r"Flexural strength", "flexural_strength", "ASTM D790", "psi", "psi", PSI),
        ]:
            pattern = (
                label
                + r"\s*\n"
                + method
                + r"\n\s*"
                + re.escape(printed_unit)
                + r"\s*\n"
            )
            match = re.search(pattern, text)
            if not match:
                raise ValueError(f"MCG p.{number}: missing {prop}")
            cells = text[match.end() :].splitlines()[: len(names)]
            if not all(numeric(c.replace(",", "")) or c == "-" for c in cells):
                raise ValueError(f"MCG p.{number}/{prop}: unreviewed cells {cells}")
            rows.append((prop, method, source_unit, factor, cells))
        for column, full_name in enumerate(names):
            if full_name == "TIVAR 1000 UHMW-PE colors":
                batch.excluded.append(
                    {
                        "id": full_name,
                        "reason": "Color variants of TIVAR 1000, not additional materials",
                    }
                )
                continue
            aliases = full_name.split(" / ")
            name = aliases[0]
            chemistry = name.split()[-1].replace("PA4.6", "PA46")
            if chemistry not in (
                "PBI",
                "PI",
                "PAI",
                "PEI",
                "PTFE",
                "PEEK",
                "PSU",
                "PPS",
                "POM-C",
                "POM-H",
                "PA46",
                "PA6",
                "PA66",
                "PET",
                "PC",
                "UHMW-PE",
                "PP",
            ):
                raise ValueError(f"MCG unreviewed chemistry: {name}")
            values = []
            for prop, method, unit, factor, cells in rows:
                raw = cells[column]
                if raw == "-":
                    continue
                note = "ASTM data table. Reference specimens machined from stock shapes; guide p. 31. Conditioning and orientation not specified for this row. ASTM and ISO table values are not combined."
                if prop == "density":
                    note += " Approximate density = tabulated specific gravity × 1000 kg/m³, at the reported precision."
                values.append(
                    obs(
                        prop,
                        raw,
                        sid,
                        number,
                        full_name + ", ASTM table column " + str(column + 1),
                        prop,
                        method=method,
                        conditions={"material_state": note},
                        factor=factor,
                        raw_unit=unit,
                        basis="computed" if prop == "density" else "typical",
                    )
                )
            batch.add(
                "mcg-" + slug(name),
                name,
                "polymer-" + slug(chemistry),
                ["polymer", chemistry],
                values,
                "Mitsubishi Chemical Group stock-shape grade; supplier ASTM reference properties.",
                aliases=aliases[1:] + ["MCG " + name, chemistry],
                designations={"Supplier": name},
            )


def kyocera(batch: Batch) -> None:
    """Read simple ceramic table panels with explicit column and unit checks."""
    sid = "kyocera-mechanical-catalog"
    document = batch.pdf(
        sid,
        "kyocera-mechanical.pdf",
        "Fine Ceramics: characteristic tables",
        "KYOCERA",
        "https://global.kyocera.com/prdct/fc/pdf/catalog/mechanical.pdf",
        "Pinned manufacturer mechanical catalog; tables pp. 8 and 10",
    )
    for number, expected_count in [(8, 9), (10, 7)]:
        text = document[number - 1].get_text()
        names = (
            text.split("Material Code (New)\n")[1]
            .split("Material Code (Old)\n")[0]
            .splitlines()
        )
        old_names = (
            text.split("Material Code (Old)\n")[1].split("Appearance\n")[0].splitlines()
        )
        if len(names) != expected_count or len(old_names) != expected_count:
            raise ValueError(f"KYOCERA p.{number}: changed columns")
        rows = []
        for label, prop, method, unit, factor in [
            (r"Density\s*\n\( ＊1\)\ng/cm\n3", "density", "JIS R 1634", "g/cm³", 1000),
            (
                r"Flexural Strength 3 P.B.\nMPa",
                "flexural_strength",
                "JIS R 1601",
                "MPa",
                1e6,
            ),
            (
                r"Young's Modulus of Elasticity\nGPa",
                "youngs_modulus",
                "JIS R 1602",
                "GPa",
                1e9,
            ),
            (
                r"Thermal Conductivity  20°C\nW/\(m · K\)\s*",
                "thermal_conductivity",
                "JIS R 1611",
                "W/(m·K)",
                1,
            ),
            (
                r"Specific Heat Capacity\nJ/\(g · K\)",
                "specific_heat",
                "JIS R 1611",
                "J/(g·K)",
                1000,
            ),
        ]:
            match = re.search(label + r"\s*" + method + r"\n", text)
            if not match:
                raise ValueError(f"KYOCERA p.{number}: missing {prop}")
            cells = text[match.end() :].splitlines()[: len(names)]
            if not all(numeric(c.replace(",", "")) or c == "−" for c in cells):
                raise ValueError(f"KYOCERA p.{number}/{prop}: changed cells {cells}")
            rows.append((prop, method, unit, factor, cells))
        for i, name in enumerate(names):
            chemistry = (
                "alumina"
                if number == 8
                else [
                    "cordierite",
                    "cordierite",
                    "steatite",
                    "forsterite",
                    "titania",
                    "cermet",
                    "cermet",
                ][i]
            )
            values = []
            for prop, method, unit, factor, cells in rows:
                if cells[i] == "−":
                    continue
                conditions = {
                    "material_state": "Typical dense ceramic; properties depend on part configuration and manufacturing process. Three-point bending for flexural strength."
                }
                if prop == "thermal_conductivity":
                    conditions["temperature_K"] = 293.15
                values.append(
                    obs(
                        prop,
                        cells[i],
                        sid,
                        number,
                        name + " (old code " + old_names[i] + ")",
                        prop,
                        method=method,
                        conditions=conditions,
                        factor=factor,
                        raw_unit=unit,
                    )
                )
            batch.add(
                "kyocera-" + slug(name),
                "KYOCERA " + name,
                "ceramics",
                ["ceramic", chemistry],
                values,
                "KYOCERA " + chemistry + " grade.",
                aliases=[name, old_names[i], chemistry],
                designations={"Supplier": name},
            )


def hexcel(batch: Batch) -> None:
    """Add the four woven 8552 laminates, using 25 °C dry warp-direction data."""
    sid = "hexcel-8552"
    old = batch.old_sources[sid]
    batch.pdf(
        sid,
        "hexcel-8552.pdf",
        old["title"],
        old["organization"],
        old["url"],
        old["revision"],
    ).close()
    # Row values transcribed from the rendered source panels. Prepreg resin,
    # weave and reinforcement define the grade; temperature does not.
    for page, code, fiber, weave, rho, strength, modulus in [
        (3, "AGP193-PW", "AS4 3K", "plain weave", "1.57", "828", "68"),
        (3, "AGP280-5H", "AS4 3K", "5-harness satin", "1.57", "876", "67"),
        (4, "SPG196-PW", "IM7 6K", "plain weave", "1.56", "1090", "85"),
        (4, "SPG370-8H", "IM7 6K", "8-harness satin", "1.56", "1014", "86"),
    ]:
        name = "HexPly 8552 " + code
        note = (
            fiber
            + ", "
            + weave
            + "; 37% resin by mass; 25 °C dry; 0° warp direction. Supplier cured laminate reference properties."
        )
        if code == "SPG370-8H":
            note += (
                " Physical header: SPG 370-8H; mechanical header printed SPG 370-SH."
            )
        elif code == "SPG196-PW":
            note += " Physical header: SPG 196-P; mechanical header: SPG 196-PW."
        values = []
        for prop, raw, label, factor, unit in [
            ("density", rho, "Nominal laminate density", 1000, "g/cm³"),
            (
                "tensile_strength",
                strength,
                "0° tensile strength, 25 °C, dry",
                1e6,
                "MPa",
            ),
            ("youngs_modulus", modulus, "0° tensile modulus, 25 °C, dry", 1e9, "GPa"),
        ]:
            conditions = {"material_state": note}
            if prop != "density":
                conditions.update(temperature_K=298.15, orientation="L")
            values.append(
                obs(
                    prop,
                    raw,
                    sid,
                    page,
                    code,
                    label,
                    method="Supplier method not stated on sheet",
                    conditions=conditions,
                    factor=factor,
                    raw_unit=unit,
                )
            )
        batch.add(
            "hexcel-8552-" + slug(code),
            name,
            "composites",
            ["composite", "woven-carbon-epoxy"],
            values,
            note,
            aliases=[code, fiber, "CFRP"],
            designations={"Supplier": code},
        )


def run(source_dir: Path) -> Batch:
    """Reconstruct all accepted source families from their local originals."""
    batch = Batch(source_dir)
    for importer in (schott, ohara, cda, woods, smooth_on, diab, mcam, kyocera, hexcel):
        before = len(batch.records)
        importer(batch)
        print(
            f"{importer.__name__}: {sum(r['record_type'] == 'grade' for r in batch.records[before:])} additions",
            flush=True,
        )
    return batch


def main() -> None:
    """Produce a review candidate or install/check the accepted batch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/private/tmp/materials-expansion-candidate.json"),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    batch = run(args.source_dir)
    materials = [r for r in batch.records if r["record_type"] == "grade"]
    report = {
        "date": DATE,
        "baseline_commit": BASELINE_COMMIT,
        "baseline_authored_sha256": hashlib.sha256(
            json.dumps(batch.baseline, sort_keys=True).encode()
        ).hexdigest(),
        "added_materials": len(materials),
        "added_observations": sum(len(r["observations"]) for r in batch.records),
        "families": dict(Counter(r["family"][0] for r in materials)),
        "material_ids": [r["id"] for r in materials],
        "authored_ids": [r["id"] for r in batch.records],
        "source_ids": list(batch.sources),
        "review_source_ids": sorted(batch.review_source_ids),
        "excluded": batch.excluded,
    }
    if not args.apply and not args.check:
        args.output.write_text(
            json.dumps(
                {
                    "report": report,
                    "materials": batch.records,
                    "sources": list(batch.sources.values()),
                    "documents": list(batch.documents.values()),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in ["added_materials", "added_observations", "families"]
                }
            )
        )
        return
    if len(materials) < 1000:
        raise ValueError(
            "This batch is not complete: fewer than 1,000 distinct additions"
        )
    outputs = [(ROOT / "curated/catalog-expansion-2026-10.json", report, False)]
    for filename, key, additions in [
        ("materials", "materials", batch.records),
        ("sources", "sources", list(batch.sources.values())),
        ("reference-manifest", "documents", list(batch.documents.values())),
    ]:
        path = ROOT / "curated" / (filename + ".json")
        data = json.loads(path.read_text())
        ids = {row["id"] for row in additions} | (
            batch.prior_ids if key == "materials" else batch.prior_source_ids
        )
        data[key] = [row for row in data[key] if row["id"] not in ids] + additions
        if key == "documents":
            data["retrieved_date"] = DATE
        outputs.append((path, data, key == "documents"))
    for path, data, ascii_only in outputs:
        rendered = json.dumps(data, indent=2, ensure_ascii=ascii_only) + "\n"
        if args.check:
            if path.read_text() != rendered:
                raise ValueError(f"{path.name}: differs from the reviewed batch")
        else:
            path.write_text(rendered)
    print(
        f"{'Verified' if args.check else 'Installed'} {len(materials)} distinct materials"
    )


if __name__ == "__main__":
    main()
