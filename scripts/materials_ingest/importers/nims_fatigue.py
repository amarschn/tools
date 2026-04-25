"""Importer for the NIMS fatigue CSV subset."""

from __future__ import annotations

from typing import Any

from .base import ParseResult, SourceImporter, clean_value, csv_reader, slugify


class NimsFatigueImporter(SourceImporter):
    importer_id = "nims-fatigue"
    source_id = "nims-fatigue-dataset"
    artifact_type = "csv"
    default_url = (
        "https://raw.githubusercontent.com/George-JieXIONG/Materials-Dataset/main/"
        "Chapter4/NIMS-Fatigue.csv"
    )

    def parse_text(self, text: str) -> ParseResult:
        reader = csv_reader(text)
        materials: list[dict[str, Any]] = []

        for index, row in enumerate(reader):
            carbon = (row.get("C") or "").strip()
            silicon = (row.get("Si") or "").strip()
            manganese = (row.get("Mn") or "").strip()
            temper = (row.get("Temperaing Temperature") or "").strip()
            name = f"NIMS Steel {carbon}C-{silicon}Si-{manganese}Mn (T_temp={temper}C)"

            normalized_temp = (row.get("Normalized Temperature") or "").strip()
            quench_temp = (row.get("Quenching Temperature") or "").strip()
            condition = (
                f"Normalized {normalized_temp}C, "
                f"Quenched {quench_temp}C, "
                f"Tempered {temper}C"
            )

            material: dict[str, Any] = {
                "id": slugify(f"nims-steel-{index}"),
                "name": name,
                "family": "metal",
                "sub_family": "carbon-steel",
                "condition": condition,
                "notes": "Experimental NIMS fatigue data subset.",
            }

            tensile_strength = clean_value(row.get("Tensile Strength"))
            fatigue_strength = clean_value(row.get("Fatigue Strength (10E7 Cycles)"))
            hardness = clean_value(row.get("Hardness"))

            if tensile_strength is not None:
                material["tensile_strength"] = {
                    "value": tensile_strength * 1e6,
                    "basis": "typical",
                }
            if fatigue_strength is not None:
                material["fatigue_endurance_limit"] = {
                    "value": fatigue_strength * 1e6,
                    "basis": "typical",
                    "notes": "Mapped from source column 'Fatigue Strength (10E7 Cycles)'.",
                }
            if hardness is not None:
                material["hardness_vickers"] = {"value": hardness, "basis": "typical"}

            materials.append(material)

        return ParseResult(
            materials=materials,
            report={
                "row_count": len(materials),
                "material_count": len(materials),
                "skipped_unsupported_family_count": 0,
            },
        )
