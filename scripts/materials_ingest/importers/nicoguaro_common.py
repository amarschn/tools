"""Importer for nicoguaro common materials TSV."""

from __future__ import annotations

from typing import Any

from .base import ParseResult, SourceImporter, clean_value, csv_reader, guess_family, slugify


class NicoguaroCommonImporter(SourceImporter):
    importer_id = "nicoguaro-common"
    source_id = "nicoguaro-common-materials"
    artifact_type = "tsv"
    default_url = (
        "https://raw.githubusercontent.com/nicoguaro/material_database/master/"
        "materials/common_materials.tsv"
    )

    def parse_text(self, text: str) -> ParseResult:
        reader = csv_reader(text, delimiter="\t")
        materials: list[dict[str, Any]] = []
        skipped_family = 0

        for row in reader:
            name = (row.get("Material") or "").strip()
            category = (row.get("Category") or "").strip()
            if not name or not category:
                continue

            family = guess_family(category)
            if family is None:
                skipped_family += 1
                continue

            material: dict[str, Any] = {
                "id": slugify(f"nic-{name}"),
                "name": name,
                "family": family,
                "sub_family": category.lower(),
                "notes": f"Nicoguaro Common: {category}",
            }

            def add_range_property(
                property_id: str,
                low_key: str,
                high_key: str,
                *,
                factor: float = 1.0,
            ) -> None:
                low = clean_value(row.get(low_key))
                high = clean_value(row.get(high_key))
                if low is None and high is None:
                    return
                if low is not None and high is not None:
                    material[property_id] = {
                        "value": (low + high) / 2.0 * factor,
                        "min": low * factor,
                        "max": high * factor,
                        "basis": "handbook_range",
                    }
                    return
                single = low if low is not None else high
                material[property_id] = {
                    "value": single * factor,
                    "basis": "handbook_range",
                }

            add_range_property("youngs_modulus", "Young Modulus low", "Young Modulus high", factor=1e9)
            add_range_property("density", "Density low", "Density high")
            add_range_property("yield_strength", "Yield Strength low", "Yield Strength high", factor=1e6)
            add_range_property("tensile_strength", "Tensile Strength low", "Tensile Strength high", factor=1e6)
            add_range_property("fracture_toughness", "Fracture Toughness low", "Fracture Toughness high", factor=1e6)
            add_range_property("thermal_conductivity", "Thermal Conductivity low", "Thermal Conductivity high")
            add_range_property("cte", "Thermal Expansion low", "Thermal Expansion high", factor=1e-6)
            add_range_property("electrical_resistivity", "Resistivity low", "Resistivity high", factor=1e-8)

            materials.append(material)

        return ParseResult(
            materials=materials,
            report={
                "row_count": len(materials) + skipped_family,
                "material_count": len(materials),
                "skipped_unsupported_family_count": skipped_family,
            },
        )
