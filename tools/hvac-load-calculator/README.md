# HVAC Load Calculator

## Purpose

Calculates residential heating and cooling design loads, room by room, and checks
proposed equipment against them. It answers the same question as a Manual J
calculation using ASHRAE methods and first-principles physics. It is not
ACCA-approved software and does not satisfy a permit that requires it.

## What it does

- **Quick estimate:** ZIP, floor area, stories, build era, and foundation.
- **Details:** walls, ceiling, windows, air leakage, ventilation, ducts, and floors.
- **Rooms:** per-room loads, peak hour, and airflow.
- **Equipment:** cooling at design conditions, heat pump balance point, backup heat,
  annual compressor share, and hours below minimum modulation.
- **Fuel bill check:** a measured heat-loss coefficient from a winter bill.
- **Ranges:** a load range that narrows as assumptions are replaced, a ranking of what
  to measure next, and retrofit savings.

## Requirements

- Every result traces to an equation with the user's numbers, by selecting its row.
- Engineering lives in `pycalcs/hvac_loads.py`. The page holds no load equations.
- Weather is rebuilt from public data with `scripts/build_hvac_climate.py`. Its output
  in `data/` is generated: do not hand-edit it.
- Equipment oversizing limits stay advisory until checked against Manual S Section N2.

## Files

- `index.html`: inputs, results layout, and background copy.
- `tool.js`: form handling, room table, rendering, and export.
- `charts.js`: Plotly charts.
- `data/stations.json`: design conditions and temperature bins by NOAA station.
- `data/zips.txt`: US ZIP centroids from the Census ZCTA gazetteer.
- `test-cases/`: published houses, loadable with "Load inputs".

## Validation

`tests/test_hvac_loads.py` checks the Atlanta example from ASHRAE Fundamentals
Chapter 17 and the Sacramento Manual J report, ASHRAE's driving-force and duct tables,
the moist air equations, and the conduction solver against a finite-difference march.
`tests/browser/hvac-load-calculator.cjs` drives the page.
