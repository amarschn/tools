"""Stable diagnostic codes and the diagnostic record type.

Codes are part of the contract's public surface: negative fixtures assert on
them, so they must not be renamed to improve prose. Adding a code is a minor
change; renaming or repurposing one is a contract-version change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# --- Document and identity -------------------------------------------------

CONTRACT_VERSION_UNSUPPORTED = "CONTRACT_VERSION_UNSUPPORTED"
ID_MALFORMED = "ID_MALFORMED"
ID_DUPLICATE = "ID_DUPLICATE"
REF_MISSING = "REF_MISSING"

# --- Taxonomy --------------------------------------------------------------

TAXON_CYCLE = "TAXON_CYCLE"
TAXON_PRIMARY_MISSING = "TAXON_PRIMARY_MISSING"
TAXON_MEMBERSHIP_DUPLICATE = "TAXON_MEMBERSHIP_DUPLICATE"
OBSERVATION_TAXON_ATTACHED = "OBSERVATION_TAXON_ATTACHED"

# --- Entity relationships --------------------------------------------------

STATE_MATERIAL_MISMATCH = "STATE_MATERIAL_MISMATCH"
SUPERSEDES_UNKNOWN = "SUPERSEDES_UNKNOWN"
SUPERSEDES_SELF = "SUPERSEDES_SELF"

# --- Registries ------------------------------------------------------------

PROPERTY_UNKNOWN = "PROPERTY_UNKNOWN"
PROPERTY_GROUP_MEMBER_UNKNOWN = "PROPERTY_GROUP_MEMBER_UNKNOWN"
CONDITION_UNKNOWN = "CONDITION_UNKNOWN"
CONDITION_VALUE_INVALID = "CONDITION_VALUE_INVALID"
BASIS_UNKNOWN = "BASIS_UNKNOWN"
SOURCE_UNKNOWN = "SOURCE_UNKNOWN"

# --- Condition placement ---------------------------------------------------
# Adopted at checkpoint 1: a key has exactly one placement, and a state-fixed
# fact is never copied onto an observation.

ATTRIBUTE_PLACEMENT = "ATTRIBUTE_PLACEMENT"
CONDITION_PLACEMENT = "CONDITION_PLACEMENT"
LEGACY_STATE_KEY = "LEGACY_STATE_KEY"
NAVIGABLE_CONDITION_NOT_ENUM = "NAVIGABLE_CONDITION_NOT_ENUM"

# --- Results, units, precision ---------------------------------------------

RESULT_KIND_INVALID = "RESULT_KIND_INVALID"
RESULT_VALUE_NOT_FINITE = "RESULT_VALUE_NOT_FINITE"
RESULT_INTERVAL_ORDER = "RESULT_INTERVAL_ORDER"
RESULT_PRECISION_REQUIRED = "RESULT_PRECISION_REQUIRED"
UNCERTAINTY_AS_INTERVAL = "UNCERTAINTY_AS_INTERVAL"
UNIT_INCOHERENT = "UNIT_INCOHERENT"
UNIT_MISMATCH = "UNIT_MISMATCH"

# --- Provenance ------------------------------------------------------------

SOURCE_LOCATOR_REQUIRED = "SOURCE_LOCATOR_REQUIRED"

# --- Search identity -------------------------------------------------------

ALIAS_COLLISION = "ALIAS_COLLISION"

# --- Structural (JSON Schema) ----------------------------------------------

SCHEMA_VIOLATION = "SCHEMA_VIOLATION"


ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class Diagnostic:
    """One validation finding.

    `path` is a JSON-pointer-style location so tests can assert on placement
    without depending on message prose.
    """

    code: str
    path: str
    message: str
    severity: str = ERROR
    context: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        payload = {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
        }
        if self.context:
            payload["context"] = dict(self.context)
        return payload

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return f"{self.severity.upper()} {self.code} at {self.path}: {self.message}"


def sort_key(diagnostic: Diagnostic) -> tuple:
    """Deterministic ordering so repeated validation output is byte-identical."""
    return (diagnostic.path, diagnostic.code, diagnostic.message)
