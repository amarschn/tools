# Materials Explorer Ashby Chart Prototypes

Date: 2026-04-13

Three Plotly-based Ashby chart studies for the Materials Explorer dataset. Each
variant uses the same underlying `E` vs `rho` material map so the envelope and
labeling choices can be compared directly.

## Variants

### A — Smoothed Hull Bubbles
`a-hulls/index.html`

Builds family regions from smoothed convex hulls in log space. Uses direct
family labels inside the bubbles and dotted stiffness-to-weight merit lines.

### B — Covariance Ellipses
`b-ellipses/index.html`

Fits a log-space covariance ellipse to each family. Keeps a more formal legend
and calls out one exemplar material per family.

### C — Territory Ribbons
`c-ribbons/index.html`

Builds ribbon-style envelopes from x-binned upper/lower bounds. Uses a more
restrained monochrome plot style with a compact inline family key.

## How to view

```bash
python3 -m http.server 8000
```

Then open:

- `http://localhost:8000/_internal/prototypes/2026-04-13_materials-explorer-ashby-charts/`
- `http://localhost:8000/_internal/prototypes/2026-04-13_materials-explorer-ashby-charts/a-hulls/`
- `http://localhost:8000/_internal/prototypes/2026-04-13_materials-explorer-ashby-charts/b-ellipses/`
- `http://localhost:8000/_internal/prototypes/2026-04-13_materials-explorer-ashby-charts/c-ribbons/`
