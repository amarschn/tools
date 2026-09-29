"""Deterministic golden projections.

Goldens exist to make the derived semantics reviewable. A change in counting,
range, ordering, or inheritance behaviour shows up as a diff in a checked-in
file rather than as a silently different page.

Every golden is computed from the validated corpus, so regenerating them without
reading the diff would defeat their purpose.
"""

from __future__ import annotations

from typing import Any, Mapping

from .adversarial import _MATERIAL_ID as ADVERSARIAL_MATERIAL_ID
from .projections import (
    Corpus,
    assemble_material_record,
    drilldown_levels,
    effective_context,
    navigation_ranges,
    span,
    taxon_coverage,
)

# One property exercised across every category, chosen because the corpus
# contains empty, singleton, and multi-member coverage for it.
SURVEY_PROPERTY = "ultimate_tensile_strength"

# The aluminium grade whose states differ by temper and whose observations
# differ by product form: the checkpoint 1 drill-down in one material.
DRILLDOWN_MATERIAL_ID = "synthetic-synal-ax70"


def build(dataset: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    corpus = Corpus(dataset)
    return {
        "material-record-adversarial": assemble_material_record(
            corpus, ADVERSARIAL_MATERIAL_ID
        ),
        "material-record-adversarial-with-superseded": assemble_material_record(
            corpus, ADVERSARIAL_MATERIAL_ID, include_superseded=True
        ),
        "navigation-ranges-drilldown": navigation_ranges(
            corpus, DRILLDOWN_MATERIAL_ID, SURVEY_PROPERTY
        ),
        "taxon-coverage-survey": {
            "property_id": SURVEY_PROPERTY,
            "taxa": [
                taxon_coverage(corpus, taxon_id, SURVEY_PROPERTY)
                for taxon_id in sorted(corpus.taxa)
            ],
        },
        "drilldown-levels": {
            "material_id": DRILLDOWN_MATERIAL_ID,
            "states": [
                {
                    "state_id": state["id"],
                    "levels": drilldown_levels(
                        corpus, DRILLDOWN_MATERIAL_ID, state["id"]
                    ),
                }
                for state in corpus.states_by_material.get(DRILLDOWN_MATERIAL_ID, [])
            ],
        },
        "effective-context": {
            "observations": [
                {
                    "observation_id": observation["id"],
                    "state_id": observation.get("state_id"),
                    "stored_conditions": dict(
                        sorted((observation.get("conditions") or {}).items())
                    ),
                    "effective_context": effective_context(observation, corpus),
                }
                for observation in sorted(
                    corpus.observations_by_material.get(DRILLDOWN_MATERIAL_ID, []),
                    key=lambda row: row["id"],
                )[:6]
            ]
        },
        "assertion-handling": {
            "property_spans": [
                {
                    "property_id": property_id,
                    "span": span(
                        corpus.observations_by_material.get(
                            ADVERSARIAL_MATERIAL_ID, []
                        ),
                        property_id,
                    ),
                }
                for property_id in sorted(corpus.properties)
            ]
        },
    }
