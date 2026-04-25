"""Base types and shared helpers for source-specific importers."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ParseResult:
    """Parsed source materials and a compact parser report."""

    materials: list[dict[str, Any]]
    report: dict[str, Any]


class SourceImporter:
    """Base class for source-specific local-file importers."""

    importer_id: str
    source_id: str
    artifact_type: str
    default_url: str

    def read_text(self, path: str | Path) -> str:
        """Read text from a local source artifact."""
        return Path(path).read_text(encoding="utf-8-sig")

    def parse_text(self, text: str) -> ParseResult:
        """Parse source text into normalized material records."""
        raise NotImplementedError

    def parse_file(self, path: str | Path) -> ParseResult:
        """Read and parse a local source artifact."""
        return self.parse_text(self.read_text(path))


def clean_value(value: Any) -> float | None:
    """Convert a source field to float, preserving legitimate zeros."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"nan", "na", "n/a", "none", "-"}:
        return None

    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def slugify(value: str) -> str:
    """Build a stable ASCII slug from *value*."""
    text = value.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def guess_family(category: str) -> str | None:
    """Map a raw category string to a curated family or ``None`` to skip."""
    c = category.lower()

    if any(token in c for token in ("fluid", "lubricant", "oil", "catalyst", "polyol", "isocyanate", "activator")):
        return None
    if any(token in c for token in ("fabric", "textile", "woven", "nonwoven")):
        return "fabric"
    if "foam" in c:
        return "foam"
    if any(token in c for token in ("gel", "hydrogel")):
        return "gel"
    if any(token in c for token in ("metal", "steel", "alloy", "iron", "brass", "bronze", "aluminum", "copper", "titanium", "magnesium", "zinc", "nickel")):
        return "metal"
    if any(token in c for token in ("polymer", "plastic", "thermoplastic", "thermoset", "elastomer", "nylon", "rubber")):
        return "polymer"
    if any(token in c for token in ("composite", "fiber-reinforced", "fibrous composite")):
        return "composite"
    if any(token in c for token in ("wood", "natural", "cork", "leather", "biological")):
        return "natural"
    if any(token in c for token in ("ceramic", "glass", "oxide", "carbide", "nitride", "concrete", "stone", "graphite", "carbon")):
        return "ceramic"
    return None


def csv_reader(text: str, *, delimiter: str = ",") -> csv.DictReader:
    """Create a ``DictReader`` for source text."""
    return csv.DictReader(io.StringIO(text), delimiter=delimiter)
