# TODO

Live work queue. Completed outcomes belong in [PROJECT_LOG.md](PROJECT_LOG.md).

## Next milestone — review and public deployment

The local release candidate is complete. See
[docs/release-candidate.md](docs/release-candidate.md) for the reviewable artifact
and verification evidence.

- [ ] Review the local candidate's material, category and property flows.
- [ ] Choose the hosting destination, public URL, and repository remote.
- [ ] Configure the selected host's HTML revalidation and immutable asset rules.
- [ ] Publish the verified `materials/` artifact as an atomic release after
  deployment authorization, then smoke-test the actual public URL.
- [ ] Decide how source revisions and import reviews will be maintained before
  adding more documents; reconstruction from pinned PDFs is already repeatable.

## Before substantially expanding the catalog

- [ ] Run the deferred 10,000-identity scale fixture and measure topology/index
  alternatives from the original schema-lab serving plan. Current measurements
  qualify this 134-material candidate, not a larger corpus.
- [ ] Implement the separate tools-repository compatibility collapse if that
  integration is still wanted. Legacy navigation redirects are already covered.
- [ ] Broaden the independent source audit and source-revision lifecycle before
  scaling ingestion. Keep numerical facts, exact source labels, and units
  independently reviewable.
- [ ] Add actual uncertainty forms to the factual adapter only when source data
  requires them; unknown forms currently fail rather than lose information.

## Later product decisions

- [ ] How to scope large collections of commercial grades and generic chemistry
  aliases as coverage grows.
- [ ] Whether ratings-only properties belong in a later version.
- [ ] Whether a separate comparison product is warranted after lookup is trusted.

The August M1 Phases 3–5 queue has been superseded for this bounded release by
the September 9 request to complete a local release candidate. The normalized
contract and selected dual-mode behavior are implemented in the release. The
full serving bake-off, tools compatibility export, and universal contract freeze
are not being marked complete by that narrower milestone.
