# Ashby Chart

Compare two material properties on an Ashby chart, rank the displayed reference
values by a performance index, and inspect the source of each value. This is
the site's Ashby chart tool. The former `tools/materials-explorer/` address
redirects here.

## Data and calculations

The source of truth is `materials-lookup/curated/`, also used by the Materials
lookup tool. Its published catalog contains 1,453 materials, 101 named states, and
6,410 observations from 585 sources. The chart reports how many materials have compatible values
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

Every point refers to exact observation IDs. Intervals are drawn at their
arithmetic midpoint, with optional range bars. Open markers and inequality
labels distinguish reported bounds from point values. The inspector keeps a
typical bound separate from a guaranteed minimum. Group outlines omit bounds
and describe only the plotted reference observations.

The September 2026 batch adds 11 synthetic composites, 10 woods, 13 ceramics,
12 foams, 10 elastomers, and 10 glasses. Wood bending modulus has its own
property and preset. An October batch adds a computed Young's modulus and
compressive strength for all 107 species and tensile strength for 21, so wood
also plots on the main charts. The rubber sheets report tensile strength and elongation
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
derivations, scope, and isolines. The build measures each formula's exponents,
and a test confirms the browser's values match Python's on every published point.
Rankings use the displayed reference coordinates, including
interval midpoints and bounds. They are screening comparisons, not evidence
that a grade with a higher specified minimum has higher measured performance.

## Using the chart

The chart fills the first screen, with this explanation below it. Pick a chart under
Charts in the Show tab, or click an axis to choose a property. The axis menu ranks
properties by how many materials would plot. It also sets log or linear scale and takes
formulas such as `E^0.5/rho`, which use the units shown on the axes (GPa, MPa, kg/m³).
Formula text goes through a small parser and is never run as code.

Scroll over the plot to zoom and drag to pan. A scroll already moving the page keeps
moving the page. Colour and size can each show another property.

**One material.** Click a point to tag it, add it to Compare, open its sources, or give it
a label box. A label box can be dragged anywhere and stays joined to its point by a line.
Tags belong to the material and stay in this browser. Copy link carries axes, filters and
label boxes. It does not carry tags.

**Several materials.** Box and Lasso select a group to tag, label, zoom to, hide or show
alone. A box stays on the chart and can be moved or resized, and the selection follows it.
**Add to stack** turns it into a filter.

**Selection stack.** Filters opens a chain of stages: family, class, source, tag, search,
limits with a histogram, regions drawn on the chart, and index lines you can drag. Each
stage shows how many materials it removed, and stages can be reordered or switched off.
Typed filters become stages. A unit is converted (`E > 200000 MPa` means 200 GPa) or
refused (`rho > 5 GPa`). A stage tests one compatible row, so a limit can never combine
values from incompatible conditions. A reported minimum is compared at its reported value,
and the stage says how many bounds it includes.

**Start from a part.** The brief inside the stack names a published index from the part and
requirement, sets the axes, and adds its line as a stage. Results then rank by that index.
The "strong" briefs use yield strength because the published index does, so fewer materials
qualify than on the tensile strength chart.

**Parallel.** Shows any number of properties side by side, one line per distinct set of
values. Dragging along an axis adds or edits a limit stage, so the chart and Parallel share
one filter chain. A segment touching a reported bound is dashed. Axes are logarithmic and
take single properties.

**Materials, Inspect and Rank tabs.** Materials lists grades by keyboard, including those
the current axes cannot show, with a chart that can. Inspect shows each observation's value,
kind, basis, conditions, method and citation, plus a link to the full Materials datasheet.
Rank gives an index, its equation, derivation, scope and source, and draws lines of equal
index value.

**Exports.** CSV has values in SI with kind, basis, ranges, citations and the build ID.
Image saves the chart with its labels as a PNG. Theme, density and precision persist locally.

## Group shapes

Ashby ovals are the default: one lightly shaded ellipse per family, or per material class.
Each is the smallest ellipse around the plotted values (Khachiyan's algorithm on the convex
hull), so a dense run of similar grades does not pull it off centre. Smooth pebbles and no
shape are the alternatives.

These rules apply to both:

- Reported bounds never define a shape, because a specified minimum is not a measured value.
- Reported interval endpoints do define a shape.
- A family of 10 or more can leave out very small isolated groups, under 2% of the family and
  more than 9% of the plot's width from the rest, so one far point does not stretch the
  outline. Their points still plot, and the panel says how many.
- A group whose values are mostly reported bounds gets no outline, and the panel names it.
- One value alone has no shape.
- In class view, a class splits where its points are more than 0.48 decades apart.

Shapes are drawing aids. They are not confidence regions or family-wide property limits.

## Data files and speed

| File | Holds | Loaded |
| --- | --- | --- |
| `data/materials/selection-core.json` | Materials, properties, indices, one compact column per observation field, compatible rows | First paint, about 80 KB gzip |
| `data/materials/selection-details.json` | Observation IDs, unrounded values, conditions, methods, notes, citations | First Inspect or CSV, about 190 KB gzip |
| `data/materials/selection.json` | Every published property pair, with scores and isolines | Not by this page. Tests compare against it, and the previous version in `_internal` reads it |

A row is a largest set of observations for a material that are compatible pair by pair, with
at most one per property (`compatible_rows`). Any compatible pair or larger combination sits
in a row, so formula axes and Parallel read the same table as a two-axis chart. Pairing stays
in Python. `tests/browser/ashby-parity.cjs` checks that the rows reproduce all 17,670
published chart points and that index values match Python's. The build stops if one material
needs more than `MAX_ROWS_PER_MATERIAL` rows (the largest today has 125), so a batch with many
conditions gets a review.

Index exponents are measured from each Python formula by `index_exponents`, so the browser
holds no second copy of the equations. Core values are rounded to nine significant figures for
plotting. Exports use the unrounded values.

Measured in Chromium with a cold cache, throttled to 1.6 Mbps and 150 ms latency, gzip on,
median of three loads:

| Measure | Budget | Measured | Previous page |
| --- | --- | --- | --- |
| First chart drawn | Under 1.5 s | 1.1 s | Not measured on this profile; loads 1,486 KB of data plus Plotly |
| Data and code transferred before the chart | | 144 KB | |
| Family toggle, to next frame | Under 50 ms | 9 ms | 84 ms on a local server |

The release manifest is 155 KB gzip and only confirms the build, so it loads after the first
chart. A mismatch then shows an error instead of old values.

## Accessibility

The plot is a canvas, so the Materials tab and the results table offer the same grades and
values to keyboard and screen reader users. Tabs use arrow keys. Motion respects the reduced
motion setting. Wheel zoom works only over the plot, and on phones the plot keeps a margin so
a finger can still scroll the page.

## Build and verify

The generator verifies the catalog hash and records the Materials build ID. The page rejects a
mismatched release instead of showing old values.

```sh
python3 materials-lookup/builder/build_site.py --output ../tools/materials
python3 scripts/build_material_selection.py
python3 scripts/inject_seo_meta.py
python3 scripts/build_material_selection.py --check
python3 -m pytest tests/test_material_selection.py -q
node tests/browser/ashby-envelopes.cjs
node tests/browser/ashby-parity.cjs
node tests/browser/materials-explorer.cjs http://127.0.0.1:8158/tools/ashby-chart/
BROWSER=webkit node tests/browser/materials-explorer.cjs http://127.0.0.1:8158/tools/ashby-chart/
BROWSER=firefox node tests/browser/materials-explorer.cjs http://127.0.0.1:8158/tools/ashby-chart/
```

Run the browser test in WebKit too. Two bugs here showed up only there: dragging started a
text selection, because Safari needs `-webkit-user-select`, and the computed style of `body`
could be stale at first paint, so the chart reads its colours from the root element.

Original source documents stay private. Only textual citations enter chart data and exports.

## Preserved work

The previous Plotly version and its comparison gallery moved to
`_internal/prototypes/2026-10-31_ashby-chart-plotly/`. The interface studies behind this
version are in `_internal/prototypes/2026-10-31_ashby-chart-ui/`, and the build plan is
`plans/2026-10-31_ashby_chart_rebuild.md`. `shared/ashby-plot.js` stays for those older pages.

The older `data/materials/materials.json` and `pycalcs/materials.py` remain for existing Python
API callers and historical studies. Neither supplies this chart. Full migration of those paths
is separate work.
