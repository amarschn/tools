# Materials Explorer UI Prototypes

Date: 2026-04-11

Three layout concepts for the Materials Explorer tool. All share the site's
standard design system (CSS variables, dark mode, settings panel, card
components, `input-group` pattern). The difference is how the controls,
chart, and detail pane relate spatially.

## Variants

### A — Left Rail
`a-left-rail/index.html`

Matches the fan-curve-explorer layout: a persistent left rail holds axis
selectors, index picker, and family toggles. The chart and ranking table
occupy the wider right column. Material detail card appears below the chart.

- Pro: Familiar to existing users; controls always visible alongside chart.
- Con: Less horizontal chart space; mobile needs full reflow.

### B — Top Controls
`b-top-controls/index.html`

Controls live in a compact horizontal bar above the chart (preset chips,
axis dropdowns, index selector). Family toggles are integrated into the
Plotly legend. The chart gets full container width. Ranking and detail
expand below.

- Pro: Maximum chart real estate; clean horizontal scan.
- Con: Controls can wrap on narrow screens; more vertical scrolling.

### C — Workspace Split
`c-workspace/index.html`

Full-width chart dominates. A collapsible drawer on the right edge holds
axis config, index settings, and the material detail card. Family toggles
are pill-shaped chips above the chart. Ranking is a slim table below.

- Pro: Chart-first; detail panel doesn't push layout around.
- Con: Drawer interaction is less discoverable; more JS for open/close.

## How to view

```
python -m http.server     # from repo root
# Then open e.g. http://localhost:8000/_internal/prototypes/2026-04-11_materials-explorer-ui/a-left-rail/
```

## What to evaluate

1. Does the control layout feel natural for iterative exploration (changing axes, toggling families, picking indices)?
2. Is the chart large enough for a useful Ashby plot with 60+ data points?
3. Does the material detail card feel integrated or bolted-on?
4. How does it degrade on a ~768px screen?
