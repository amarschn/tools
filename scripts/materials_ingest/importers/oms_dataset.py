"""Importer for the OpenMaterialsSelector CSV dataset."""

from __future__ import annotations

import html
from typing import Any

from .base import ParseResult, SourceImporter, clean_value, csv_reader, guess_family, slugify


class OmsDatasetImporter(SourceImporter):
    importer_id = "oms-dataset"
    source_id = "open-materials-selector-oms"
    artifact_type = "csv"
    default_url = (
        "https://raw.githubusercontent.com/mrealpe/OpenMaterialsSelector/master/datos.csv"
    )

    def parse_text(self, text: str) -> ParseResult:
        reader = csv_reader(text)
        materials: list[dict[str, Any]] = []
        skipped_family = 0

        for row in reader:
            name = html.unescape((row.get("Name") or "").strip())
            category = (row.get("Category") or "").strip()
            if not name or not category:
                continue

            family = guess_family(category)
            if family is None:
                skipped_family += 1
                continue

            density = clean_value(row.get("Density"))
            modulus = clean_value(row.get("Modulus of Elasticity"))

            if density is not None and density < 0.001:
                density = None
            if modulus is not None and modulus < 0.001:
                modulus = None

            if density is None and modulus is None:
                continue

            material: dict[str, Any] = {
                "id": slugify(f"oms-{name}"),
                "name": name,
                "family": family,
                "sub_family": category.lower().replace(";", ","),
                "notes": f"OMS Dataset. URL: {row.get('url', '').strip()}",
            }

            if density is not None:
                material["density"] = {"value": density * 1000.0, "basis": "typical"}
            if modulus is not None:
                material["youngs_modulus"] = {"value": modulus * 1e9, "basis": "typical"}

            materials.append(material)

        return ParseResult(
            materials=materials,
            report={
                "row_count": len(materials) + skipped_family,
                "material_count": len(materials),
                "skipped_unsupported_family_count": skipped_family,
            },
        )
