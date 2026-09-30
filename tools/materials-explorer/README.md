# Materials Explorer

Compare two material properties on an Ashby chart, rank the displayed reference
values by a performance index, and inspect the source of each value. This is
the site's Ashby chart tool. The former `tools/ashby-chart/` address redirects
here.

## Data and calculations

The source of truth is `materials-lookup/curated/`, also used by the Materials
lookup tool. Its published catalog contains 222 grades, 92 named states, and
1,593 observations. The chart reports how many grades have compatible values
for the selected axes and filters. Properties without positive observations
are not offered on the logarithmic axes.

`pycalcs/material_selection.py` pairs observations of the same grade without
merging named states. Known temperatures, product forms, thickness ranges, and
orientations must agree. A grade-level physical property may accompany a
named state, and the inspector keeps its grade-level scope explicit. An
unspecified condition remains unspecified; paired values do not imply a
shared specimen or test. No missing property is filled from the older generic
material dataset.

Every point refers to two exact observation IDs. Intervals are drawn at their
arithmetic midpoint, with optional range bars. Open markers and inequality
labels distinguish specified bounds from point values. Family envelopes omit
bounds and enclose only the measured reference points shown; they are not
complete property limits for a material family.

`pycalcs/material_indices.py` is the single source for performance indices,
derivations, scope, and isolines. The build computes the scores and line
endpoints. The browser filters and presents them without a second copy of the
ranking formulas. Rankings use the displayed reference coordinates, including
interval midpoints and bounds. They are screening comparisons, not evidence
that a grade with a higher specified minimum has higher measured performance.

## Using the chart

Choose a preset or two axes. The index menu offers equations supported by that
pair. Search by grade, designation, or state; filter families, temperature, or
measurement/limit basis. The default temperature filter includes 20–25 °C and
values with no stated temperature.

Click a point or a ranked row to see both source citations, each observation's
conditions, and a link to the full Materials datasheet. CSV exports retain
values in SI, reported kind and basis, ranges, citations, and the source build
identifier. Copy link preserves the chart controls, filters, and selected
point. Theme, density, and displayed precision persist locally.

## Build and verify

The shared artifact `data/materials/selection.json` is generated from the
validated public Materials release. It is a derived view, not a separately
maintained database. The generator verifies the catalog hash and records the
Materials build ID. The page rejects mismatched releases instead of falling
back to old values.

```sh
python3 materials-lookup/builder/build_site.py --output ../tools/materials
python3 scripts/build_material_selection.py
python3 scripts/inject_seo_meta.py
python3 scripts/build_material_selection.py --check
python3.13 -m pytest tests/test_material_selection.py -q
node tests/browser/materials-explorer.cjs http://127.0.0.1:8158/tools/materials-explorer/
```

The site build regenerates the chart projection. The lookup and chart share
one authoring source and one published catalog, and the plot uses the existing
Plotly dependency. Original source documents stay private; only textual
citations enter chart data and exports.

## Preserved work

The existing chart studies under `_internal/prototypes/` remain intact. The
older `data/materials/materials.json` and `pycalcs/materials.py` are retained
for existing Python API callers and historical studies; neither supplies this
chart. Full migration of those authoring and ingestion paths remains separate
from this tool consolidation.
