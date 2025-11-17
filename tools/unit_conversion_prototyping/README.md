# Unit Conversion Prototyping Lab

This folder aggregates experimental user interfaces for unit conversion
workflows. Each sub-tool explores a different interaction model that may
eventually seed the final reusable template.

## Prototype Index

- `pairwise_converter` &mdash; dual dropdown workflow that exposes the base SI mapping.
- `curated_systems` &mdash; radio button presets for domain-specific imperial/metric pairs.
- `scale_explorer` &mdash; side-by-side order-of-magnitude exploration across pressure and velocity bands.

All prototypes reuse common conversion logic implemented in `pycalcs/unit_prototypes.py`.
