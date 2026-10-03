# Ashby Chart

Compare two material properties on an Ashby chart, rank the displayed reference
values by a performance index, and inspect the source of each value. This is
the site's Ashby chart tool. The former `tools/ashby-chart/` address redirects
here.

## Data and calculations

The source of truth is `materials-lookup/curated/`, also used by the Materials
lookup tool. Its published catalog contains 1,360 materials, 92 named states, and
5,858 observations from 537 sources. The chart reports how many materials have compatible values
for the selected axes and filters. Properties without positive observations
are not offered on the logarithmic axes.

`pycalcs/material_selection.py` pairs observations of the same grade without
merging named states. Known product forms, thickness ranges, and orientations
must agree. Temperatures must match, except that values within 20–25 °C can
be paired for room-temperature comparison. Both original temperatures remain
visible in the inspector and CSV. This allows titanium density at 22 °C to
appear with modulus at 20 °C without also pairing elevated-temperature data.
A grade-level physical property may accompany a
named state, and the inspector keeps its grade-level scope explicit. An
unspecified condition remains unspecified; paired values do not imply a
shared specimen or test. No missing property is filled from the older generic
material dataset.

Every point refers to two exact observation IDs. Intervals are drawn at their
arithmetic midpoint, with optional range bars. Open markers and inequality
labels distinguish reported bounds from point values. The inspector keeps a
typical bound separate from a guaranteed minimum. Group outlines omit bounds
and describe only the plotted reference observations.

The September 2026 batch adds 11 synthetic composites, 10 woods, 13 ceramics,
12 foams, 10 elastomers, and 10 glasses. Wood bending modulus has its own
property and preset. The rubber sheets report tensile strength and elongation
without a small-strain Young's modulus, so those grades appear in the tensile
strength chart. Divinycell F likewise has no reported tensile modulus in the
selected sheet. Missing properties stay missing. Source decisions are recorded
in [the batch review](../../materials-lookup/docs/ashby-families-review.md).

The October expansion adds 1,072 grades and species: 486 copper alloys, 249
optical glasses, 106 polymers, 97 woods, 97 elastomers, 17 foams, 16 ceramics,
and four woven composites. All have density and at least one other plotted
property; availability still depends on the selected axes. See the
[October source review](../../materials-lookup/docs/catalog-expansion-2026-10-batch-review.md)
for source scope, rejected cells, and duplicate handling.

`pycalcs/material_indices.py` is the single source for performance indices,
derivations, scope, and isolines. The build computes the scores and line
endpoints. The browser filters and presents them without a second copy of the
ranking formulas. Rankings use the displayed reference coordinates, including
interval midpoints and bounds. They are screening comparisons, not evidence
that a grade with a higher specified minimum has higher measured performance.

## Using the chart

Choose a preset or two axes above the plot. Search by name or designation and
toggle families in the compact filter row. The Materials tab lists matching
grades, including those that need different axes or filters. Selecting one of
those grades shows its available properties and a suitable chart preset.
The default temperature filter includes 20–25 °C and values with no stated
temperature. Filters & display holds temperature, result type, and drawing
options. The visible Family / Subgroup / Points only control sets the outline
grouping independently of its shape. The Rank tab offers indices supported by
the chosen property pair.

Click a point or a ranked row to see both source citations, each observation's
conditions, and a link to the full Materials datasheet. CSV exports retain
values in SI, reported kind and basis, ranges, citations, and the source build
identifier. Copy link preserves the chart controls, filters, and selected
point. Theme, density, and displayed precision persist locally. Keyboard users
can select a grade from the Materials list and switch inspector tabs with
arrow keys.

## Group shapes and retained experiments

Family view is the default: one lightly shaded outline for each broad family,
labeled Polymers, Metals, Ceramics, and so on. Individual grade points remain
visible. Subgroup view draws separate outlines for material types such as PEEK
and PA6. Points only removes the outlines and retains the observations and
reported ranges. Grouping is saved in shared links.

The outline shape is a separate control under Filters & display. The
[comparison gallery](prototypes/) preserves the earlier subgroup studies:

| Method | Construction |
| --- | --- |
| A: rounded subgroup outlines | Convex hull of interval endpoints and points, padded by a 0.055-decade disk in log space. |
| B: enclosing ellipses | Principal-axis ellipse enlarged to enclose the same observations. |
| C: points only | Individual observations and interval bars without filled regions. |

Family view encloses all eligible plotted observations in one outline per
family. Subgroups use the source classification and split when their nearest
connecting points are more than 0.48 decades apart in the two-dimensional log
plane. Padding stays fixed as groups grow. A lone point has no group shape. These
regions are drawing aids, not confidence regions or family-wide property
limits. Labels are placed around the regions with overlap checks and leader
lines. Axes display engineering units while coordinates and exports remain SI.

The gallery also preserves the previous interface. The old page uses the
expanded catalog so the layout comparison uses the same data.

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
node tests/browser/ashby-envelopes.cjs
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
