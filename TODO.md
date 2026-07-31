# TODO

This is the live work queue. Completed outcomes move to
[`PROJECT_LOG.md`](PROJECT_LOG.md) so this file remains useful rather than
becoming an archive.

## Now — M1 domain-contract prototype

- [ ] Define versioned contracts for taxonomy nodes, material identities, named
  states, observations, properties, conditions, and sources.
- [ ] Add stable IDs and distinguish primary browsing taxonomy from
  supplemental classifications.
- [ ] Define which conditions create named states and which remain attached to
  individual observations.
- [ ] Represent multiple observations, source-reported ranges, uncertainty,
  missingness, basis, and precise source locators without hidden defaults.
- [ ] Define derived category/property projections, coverage counts, and
  mixed-condition warnings.
- [ ] Add schema validators and executable positive and negative examples.
- [ ] Decide whether the taxonomy/material/state/observation contract
  supersedes [`docs/schema-decision.md`](docs/schema-decision.md), then record a
  new decision instead of silently rewriting the old one.

## Next — prove the contract and search behavior

- [ ] Port the current synthetic fixture through the versioned contracts
  without changing the accepted Prototype 05 behavior.
- [ ] Define the boundary between compact search-index records and complete
  material records.
- [ ] Add golden queries for exact IDs, aliases, short tokens, misspellings,
  ambiguous properties, category scopes, and comparison intent.
- [ ] Generate at least 10,000 synthetic records and record index size, query
  latency, render latency, and the 50-row rendering budget.
- [ ] Prove the compatibility export using deterministic synthetic output.
- [ ] Preserve a small repeatable review script for the selected interaction.

## Then — small real-source reality check

- [ ] Select two structurally different, legally usable source documents.
- [ ] Manually model 8–12 material identities and 3–5 substantially different
  properties.
- [ ] Include named states, conditioned or conflicting observations, a
  source-reported range, missing data, and precise citations.
- [ ] Render the real-source slice through the selected interaction and record
  every schema change it forces.
- [ ] Prototype the source-snapshot, candidate-extraction, review, and publish
  lifecycle before scaling ingestion.

## Open product and UI decisions

- [ ] Should singular property counts be hidden or renamed from “1 observation”
  to “1 reported value”?
- [ ] Should the search index contain property values or availability only?
- [ ] How should near-duplicate conditioned observations appear by default?
- [ ] How are commercial materials without standard designations identified?
- [ ] Are ratings-only properties part of v1?
- [ ] Which review and provenance details must remain visible in the compact
  lookup surface?

## Later

- [ ] Reimplement the selected UI cleanly against the frozen contract rather
  than promoting the disposable prototype directly.
- [ ] Expand material and property coverage only after provenance, licensing,
  deterministic rebuild, and offline validation gates pass.
- [ ] Revisit a separate comparison product only after the lookup tool is
  trustworthy.
