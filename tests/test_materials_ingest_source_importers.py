"""Tests for source-specific materials importers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.materials_ingest.import_source_file import import_source_file_to_staging
from scripts.materials_ingest.importers import get_importer


def test_nicoguaro_importer_parses_range_properties():
    importer = get_importer("nicoguaro-common")
    text = "\t".join(
        [
            "Material",
            "Category",
            "Young Modulus low",
            "Young Modulus high",
            "Density low",
            "Density high",
            "Yield Strength low",
            "Yield Strength high",
            "Tensile Strength low",
            "Tensile Strength high",
            "Fracture Toughness low",
            "Fracture Toughness high",
            "Thermal Conductivity low",
            "Thermal Conductivity high",
            "Thermal Expansion low",
            "Thermal Expansion high",
            "Resistivity low",
            "Resistivity high",
        ]
    ) + "\n" + "\t".join(
        [
            "Flexible Foam VLD",
            "Foams",
            "0.3",
            "1.0",
            "16",
            "35",
            "0.01",
            "0.12",
            "0.24",
            "0.85",
            "0.005",
            "0.02",
            "0.036",
            "0.048",
            "120",
            "220",
            "1e20",
            "1e23",
        ]
    )

    result = importer.parse_text(text)
    material = result.materials[0]
    assert material["family"] == "foam"
    assert material["youngs_modulus"]["min"] == 0.3e9
    assert material["yield_strength"]["max"] == 0.12e6


def test_oms_importer_skips_fluids_and_maps_graphite():
    importer = get_importer("oms-dataset")
    text = "\n".join(
        [
            "Name,Category,Density,Modulus of Elasticity,url",
            "Graphite A,\"carbon; graphite\",2.2,12,http://example.com/a",
            "Motor Oil,\"fluid; lubricant\",0.9,0.01,http://example.com/b",
        ]
    )

    result = importer.parse_text(text)
    assert len(result.materials) == 1
    assert result.materials[0]["family"] == "ceramic"
    assert result.report["skipped_unsupported_family_count"] == 1


def test_nims_importer_maps_fatigue_column_to_endurance_limit():
    importer = get_importer("nims-fatigue")
    text = "\n".join(
        [
            "C,Si,Mn,Normalized Temperature,Quenching Temperature,Temperaing Temperature,Tensile Strength,Fatigue Strength (10E7 Cycles),Hardness",
            "0.4,0.2,0.7,850,860,600,950,420,320",
        ]
    )

    result = importer.parse_text(text)
    material = result.materials[0]
    assert "fatigue_endurance_limit" in material
    assert material["fatigue_endurance_limit"]["value"] == 420e6


def test_source_file_import_builds_staging_bundle(tmp_path: Path):
    importer = get_importer("nawale-metals")
    source_file = tmp_path / "nawale.csv"
    source_file.write_text(
        "\n".join(
            [
                "Material,Heat treatment,Std,Su,Sy,E,Ro,mu",
                "Steel A,normalized,GOST,600,400,210000,7850,0.3",
            ]
        ),
        encoding="utf-8",
    )

    bundle = import_source_file_to_staging(
        importer.importer_id,
        source_file,
        source_registry={"sources": []},
        curated_db={
            "property_registry": {
                "tensile_strength": {"unit": "Pa"},
                "yield_strength": {"unit": "Pa"},
                "youngs_modulus": {"unit": "Pa"},
                "density": {"unit": "kg/m^3"},
                "poissons_ratio": {"unit": None},
            }
        },
    )

    assert len(bundle["artifacts"]) == 1
    assert len(bundle["candidate_materials"]) == 1
    assert len(bundle["extracted_datums"]) == 5
    assert bundle["import_report"]["unknown_property_ids"] == {}
