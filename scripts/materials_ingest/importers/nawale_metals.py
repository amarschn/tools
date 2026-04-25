"""Importer for Nawale metals CSV."""

from __future__ import annotations

from typing import Any

from .base import ParseResult, SourceImporter, clean_value, csv_reader, slugify


class NawaleMetalsImporter(SourceImporter):
    importer_id = "nawale-metals"
    source_id = "nawale-metals-dataset"
    artifact_type = "csv"
    default_url = (
        "https://raw.githubusercontent.com/purushottamnawale/"
        "material-selection-using-machine-learning/master/Data.csv"
    )

    def parse_text(self, text: str) -> ParseResult:
        reader = csv_reader(text)
        materials: list[dict[str, Any]] = []

        for row in reader:
            name = (row.get("Material") or "").strip()
            if not name:
                continue

            condition = (row.get("Heat treatment") or "").strip()
            if condition.lower() == "nan":
                condition = ""
            full_name = f"{name} ({condition})" if condition else name

            material: dict[str, Any] = {
                "id": slugify(f"naw-{full_name}"),
                "name": full_name,
                "family": "metal",
                "sub_family": "alloy",
                "condition": condition or None,
                "notes": f"Nawale Metals Dataset. Std: {row.get('Std', '')}".strip(),
            }

            su = clean_value(row.get("Su"))
            sy = clean_value(row.get("Sy"))
            modulus = clean_value(row.get("E"))
            density = clean_value(row.get("Ro"))
            poisson = clean_value(row.get("mu"))

            if su is not None:
                material["tensile_strength"] = {"value": su * 1e6, "basis": "typical"}
            if sy is not None:
                material["yield_strength"] = {"value": sy * 1e6, "basis": "typical"}
            if modulus is not None:
                material["youngs_modulus"] = {"value": modulus * 1e6, "basis": "typical"}
            if density is not None:
                material["density"] = {"value": density, "basis": "typical"}
            if poisson is not None:
                material["poissons_ratio"] = {"value": poisson, "basis": "typical"}

            materials.append(material)

        return ParseResult(
            materials=materials,
            report={
                "row_count": len(materials),
                "material_count": len(materials),
                "skipped_unsupported_family_count": 0,
            },
        )
