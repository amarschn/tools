# Curated Systems Prototype

## Purpose

Prototype a conversion interface that emphasises common imperial ↔ metric
scenarios through presets instead of exposing the full unit catalog.

## Requirements

- Present radio-button scenarios for length, hydraulic pressure, and vehicle velocity.
- Allow switching between "Imperial → Metric" and "Metric → Imperial" directions.
- Display the paired values in both unit systems along with the unit labels.
- Drive all calculations through `pycalcs.unit_prototypes.convert_between_primary_systems`.
