# Schema Decision 002 — factual release adapter

Date: 2026-09-09

Status: implemented for local release candidate 1.0.0-rc.1. This records the
bounded release requested on September 9; it is not a claim that every experiment
in the earlier M1 plan has been completed.

## Decision

The public-facing compiler consumes the normalized v0.1.0 contract:
taxonomy → material → named state → observation. It supersedes
[Schema Decision 001](schema-decision.md) for the release path. The earlier
family/grade/variant model remains an authoring compatibility format, converted
deterministically by `release/catalog.py`. It is not a second browser database.

The JSON Schema and semantic validator apply to the factual dataset as well as
the synthetic lab. Properties use `tensile_yield_strength` and
`ultimate_tensile_strength`; the old identifiers remain query/URL aliases.
The source registry's URL, snapshot hash, retrieval date, notes, and original
printed literals live in a lossless citation sidecar because contract v0.1.0
does not define those fields. Each complete material bundle includes that
material's observations and source metadata in one request.

## Real-source mappings

- All 134 grade identities survive. The 111 generic stock-shape/reference-state
  wrappers dissolve; their observations attach to the material, with product
  form retained on the observation. Their old URLs redirect to the material.
- The two 6061 tempers and 22 cold-rolled stainless states survive as 24 named
  states. Product form is a derived, landable level below a material or state.
- Stainless mechanical values in Table 5 belong to the cold-rolled state.
  Table 7 physical values are grade-level observations and are not inherited by
  the state. The original context label remains in observation notes.
- The vague legacy `material_state` key is removed. Machining/specimen prose
  survives verbatim in observation notes; cold rolling is a registered fixed
  attribute. No temperature, humidity or orientation is guessed from a grade.
- Rechecking Hydro page 2 removed one duplicate density entry. The density is
  alloy-wide, not temper-specific. Its original `0.098 lb/in³` now converts
  without the previous premature rounding, retains two significant figures,
  and appears once on the material. The conductivity observations now retain
  the reported 25 °C condition. There are 840 factual observations after this
  documented correction, with every remaining authoring observation preserved.

No schema shape change was needed. The factual condition registry adds
`stock_shape` and `cold_rolled`; the display-unit registry adds heat capacity and
a ratio quantity distinct from percentage strain. Unmapped source result or
uncertainty forms are rejected at the adapter boundary.

## Display and aggregation

Canonical numbers drive display; printed source numbers remain visible for
audit. Metric is the default, with a whole-system imperial switch and persistent
property overrides. Switching the system resets overrides. Affine conversions
apply to values; uncertainty magnitudes use scale only. Display precision is
limited to the reported significant figures.

Numeric category ranges use point values and reported interval endpoints only.
One-sided limits have separate minimum/maximum-limit summaries and coverage.
This is stricter than the lab's original `span` function, which includes a bound
threshold and flags it. The factual compiler and browser implement the stricter
rule and have explicit cross-language parity checks over every material.
Superseded observations are excluded from aggregates. Missing data remains
unreported. Coverage distinguishes material coverage from observation counts.

## Serving decision for this candidate

Use a readable compact identity/availability index, one lazy bundle per material,
and one generated projection per property. Full catalog JSON and CSV are optional
downloads. Search never loads observation values, and routine browsing never
downloads the full catalog. A build hash covers the canonical data, citation
details, serving projections, compiler files, HTML and browser assets.

Versioned data and assets live under content-addressed directories. The HTML
pins one build; a lazy record from another build is rejected with a retry/reload
path. All application and legacy navigation links work at root or under a
directory prefix. No history fallback rewrite is required.

This is measured for 134 materials. The original 10,000-identity benchmark and
alternative-topology bake-off remain deferred, as does the separate tools-repo
compatibility value collapse. Neither is represented as an accomplished gate.
