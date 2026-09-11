"""Plain-text rendering of a material through the contract.

This exists so the contract can be demonstrated before a UI is wired to it. It
renders the same things the eventual interface must: a range at every level, the
navigable drill-down, provenance, and the display-unit preference.

It is a demo surface, not a serving artifact. Phase 3 decides the real artifact
topology, and Phase 4 connects the prototype.
"""

from __future__ import annotations

from typing import Any, Mapping

from .projections import (
    Corpus,
    active,
    drilldown_levels,
    effective_context,
    span,
)
from .units import (
    conversions_for,
    default_display_unit,
    find_conversion,
    format_significant,
)

INDENT = "  "


def display_span(
    entry: Mapping[str, Any] | None,
    prop: Mapping[str, Any],
    system: str,
) -> str:
    """Render a span in the reader's preferred unit system.

    Never renders more significant figures than the least precise contributing
    observation, so switching units cannot manufacture precision.
    """
    if entry is None:
        return "no data"
    if entry.get("minimum") is None:
        unavailable = entry.get("unavailable_count") or 0
        if unavailable:
            noun = "assertion" if unavailable == 1 else "assertions"
            return f"not reported ({unavailable} explicit {noun})"
        return "no data"

    unit = default_display_unit(prop["quantity_kind"], system) or prop["canonical_unit"]
    conversion = find_conversion(prop["quantity_kind"], unit)
    figures = entry.get("significant_figures") or 3

    def render(value: float) -> str:
        converted = conversion.to_display(value) if conversion else value
        return format_significant(converted, figures)

    low, high = entry["minimum"], entry["maximum"]
    prefix = ""
    if entry.get("includes_bound"):
        prefix = "≥ "  # the source specified a floor, not a value

    if entry.get("singleton"):
        body = f"{prefix}{render(low)} {unit}"
    else:
        body = f"{render(low)}–{render(high)} {unit}"

    count = entry.get("observation_count") or 0
    noun = "reported value" if count == 1 else "reported values"
    return f"{body}  ({count} {noun})"


def render_material(
    corpus: Corpus,
    material_id: str,
    property_id: str | None = None,
    system: str = "metric",
) -> str:
    material = corpus.materials[material_id]
    properties = corpus.properties
    lines: list[str] = []

    path = []
    cursor = material["primary_taxon_id"]
    while cursor:
        taxon = corpus.taxa.get(cursor)
        if taxon is None:
            break
        path.append(taxon["name"])
        cursor = taxon.get("primary_parent_id")
    lines.append(" > ".join(reversed(path)))
    lines.append("")

    designations = material.get("designations") or []
    designation_text = (
        ", ".join(f"{d['value']} ({d['system_id']})" for d in designations)
        if designations
        else "no standard designation"
    )
    lines.append(f"{material['name']}  [{designation_text}]")
    if material.get("supplemental_taxon_ids"):
        also = ", ".join(
            corpus.taxa[t]["name"]
            for t in material["supplemental_taxon_ids"]
            if t in corpus.taxa
        )
        lines.append(f"{INDENT}also classified under: {also}")
    lines.append(f"{INDENT}display units: {system}")
    lines.append("")

    selected = [property_id] if property_id else sorted(
        {
            row["property_id"]
            for row in active(corpus.observations_by_material.get(material_id, []))
        }
    )

    material_observations = active(corpus.observations_by_material.get(material_id, []))

    for chosen in selected:
        prop = properties.get(chosen)
        if prop is None:
            continue
        lines.append(f"{prop['name']}")
        lines.append(
            f"{INDENT}{material['name']}: "
            f"{display_span(span(material_observations, chosen), prop, system)}"
        )

        direct = [row for row in material_observations if not row.get("state_id")]
        direct_span = span(direct, chosen)
        if direct_span:
            lines.append(
                f"{INDENT}{INDENT}reported for the grade itself: "
                f"{display_span(direct_span, prop, system)}"
            )

        for state in corpus.states_by_material.get(material_id, []):
            state_observations = active(
                corpus.observations_by_state.get(state["id"], [])
            )
            state_span = span(state_observations, chosen)
            if state_span is None:
                continue
            lines.append(
                f"{INDENT}{INDENT}{state['name']}: "
                f"{display_span(state_span, prop, system)}"
            )
            for level in drilldown_levels(corpus, material_id, state["id"]):
                key = level["condition_id"]
                for entry in level["values"]:
                    subset = [
                        row
                        for row in state_observations
                        if str((row.get("conditions") or {}).get(key)) == entry["value"]
                    ]
                    narrowed = span(subset, chosen)
                    if narrowed is None:
                        continue
                    lines.append(
                        f"{INDENT * 3}{entry['value']}: "
                        f"{display_span(narrowed, prop, system)}"
                    )
        lines.append("")

    if property_id:
        lines.extend(_provenance(corpus, material_id, property_id))

    return "\n".join(lines).rstrip() + "\n"


def _provenance(corpus: Corpus, material_id: str, property_id: str) -> list[str]:
    lines = ["Provenance"]
    rows = sorted(
        (
            row
            for row in corpus.observations_by_material.get(material_id, [])
            if row["property_id"] == property_id
        ),
        key=lambda row: row["id"],
    )
    if not rows:
        lines.append(f"{INDENT}no observations")
        return lines

    for row in rows:
        context = effective_context(row, corpus)
        context_text = ", ".join(f"{k}={v}" for k, v in context.items()) or "no context"
        status = "" if row.get("status") == "active" else f" [{row['status']}]"
        lines.append(f"{INDENT}{row['id']}{status}")
        lines.append(f"{INDENT * 2}{context_text}")
        lines.append(f"{INDENT * 2}basis: {row.get('basis')}")
        lines.append(
            f"{INDENT * 2}{row.get('source_id')} — "
            f"{(row.get('source_locator') or {}).get('label')}"
        )
    return lines


def render_units(prop: Mapping[str, Any]) -> str:
    """List the display units a property can be shown in."""
    available = conversions_for(prop["quantity_kind"])
    if not available:
        return f"{prop['name']}: {prop['canonical_unit']} only"
    grouped: dict[str, list[str]] = {}
    for conversion in available:
        grouped.setdefault(conversion.system, []).append(conversion.unit)
    parts = [f"{system}: {', '.join(units)}" for system, units in sorted(grouped.items())]
    return f"{prop['name']} ({prop['quantity_kind']}) -> " + "; ".join(parts)
