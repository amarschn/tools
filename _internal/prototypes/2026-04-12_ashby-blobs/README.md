# Ashby Chart with Family Envelopes ("Blobs")

Date: 2026-04-12

Classic Ashby charts draw semi-transparent envelopes around material family
clusters rather than just showing individual points. This prototype implements
that using:

1. **Convex hull** of each family's data points (Andrew's monotone chain)
2. **Expansion** outward from the centroid in log-space (1.35x) to pad the envelope
3. **Catmull-Rom smoothing** (3 subdivision passes) to round the polygon corners
4. Individual material points overlaid on top with labels

## Limitations

With only ~10-20 materials per family, the envelopes are rough. Real Ashby charts
(e.g. CES EduPack) use hundreds of materials per family, giving smoother, more
natural blobs. Adding more materials to the database would improve this
significantly.

Families with fewer than 3 points on a given axis pair cannot form a hull and
are shown as points only.

## View

```
python -m http.server
# http://localhost:8000/_internal/prototypes/2026-04-12_ashby-blobs/
```
