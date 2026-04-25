"""Registry of source-specific importer implementations."""

from __future__ import annotations

from .base import SourceImporter
from .nawale_metals import NawaleMetalsImporter
from .nicoguaro_common import NicoguaroCommonImporter
from .nims_fatigue import NimsFatigueImporter
from .oms_dataset import OmsDatasetImporter

IMPORTERS: dict[str, SourceImporter] = {
    NicoguaroCommonImporter.importer_id: NicoguaroCommonImporter(),
    NawaleMetalsImporter.importer_id: NawaleMetalsImporter(),
    OmsDatasetImporter.importer_id: OmsDatasetImporter(),
    NimsFatigueImporter.importer_id: NimsFatigueImporter(),
}


def get_importer(importer_id: str) -> SourceImporter:
    """Return the importer implementation for *importer_id*."""
    try:
        return IMPORTERS[importer_id]
    except KeyError as exc:
        valid = ", ".join(sorted(IMPORTERS))
        raise KeyError(f"Unknown importer {importer_id!r}. Valid importers: {valid}.") from exc


def list_importers() -> list[dict[str, str]]:
    """Return lightweight metadata for all available importers."""
    return [
        {
            "importer_id": importer.importer_id,
            "source_id": importer.source_id,
            "artifact_type": importer.artifact_type,
            "default_url": importer.default_url,
        }
        for importer in sorted(IMPORTERS.values(), key=lambda item: item.importer_id)
    ]
