# Ashby Chart roadmap

## October 2 grouping review

- [x] Default to one outline per broad family, with individual grades visible.
- [x] Add a visible Family / Subgroup / Points only control and keep the
      outline-shape choice separate.
- [x] Retain the subgroup prototypes and support earlier points-only links.

## September 30 review

- [x] Rename the public tool and metadata to lead with Ashby Chart.
- [x] Add at least ten distinct sourced grades in each requested family:
      synthetic composites, wood, ceramics, foams, elastomers, and glasses.
- [x] Include titanium in room-temperature comparisons without losing the
      density and modulus test temperatures.
- [x] Replace the current layout with a chart-first workspace, compact controls,
      and a side inspector. Preserve inspectable alternatives.
- [x] Replace inflated family hulls with reviewed subgroup envelopes; keep
      point-only and alternate envelope methods available for comparison.

Completed October 1: 66 additions, 288 total materials. Verification: full
Python suite, source-rebuild and release checks, group geometry checks, and
browser checks for the chart, lookup, and preserved prototype pages.

- [x] Use the Materials lookup catalog for Ashby charts and source inspection.
- [x] Consolidate the old selector URL into one public chart tool.
- [x] Preserve grade, state, condition, range, and specified-limit distinctions.
- [x] Compute rankings and isolines from the shared Python index library.
- [x] Search grades, show data coverage, and share or export the displayed case.
- [ ] Expand curated coverage for material families and properties currently missing.
- [ ] Add explicit test-condition selection beyond temperature and basis filters.
- [ ] Migrate remaining legacy data ingestion and Python APIs to the observation catalog.
