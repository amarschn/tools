# HVAC Load Calculator

## Purpose

Calculates residential heating and cooling design loads, room by room, and checks
proposed equipment against them. It answers the same question as a Manual J
calculation using ASHRAE methods and first-principles physics. It is not
ACCA-approved software and does not satisfy a permit that requires it.

## What it does

The house is built as one model in eight steps, each replacing assumptions:

1. A box from a ZIP code and floor area, with the range that implies.
2. Shape, by dragging the outside walls, and the age of the house.
3. Walls, ceiling, and floor, down to wall layers if wanted.
4. Windows and doors placed on the plan.
5. Air leakage and ducts.
6. Rooms, made by adding and dragging walls.
7. The system being sized, against what it delivers on the design day.
8. A stress test: sweeps and two-variable grids of uncertain inputs, a fuel bill
   check, and export.

Plan, section, and 3D are views of the same model. Assumed parts are drawn dashed.

## Requirements

- Every result traces to an equation with the user's numbers, by selecting its row.
- Engineering lives in `pycalcs/hvac_loads.py`. The page holds no load equations.
- Weather is rebuilt from public data with `scripts/build_hvac_climate.py`. Its output
  in `data/` is generated: do not hand-edit it.
- Equipment oversizing limits stay advisory until checked against Manual S Section N2.

## Search terms

The page targets phrases from Google autocomplete, checked 2026-11-02: "free manual j
calculator", "manual j load calculation", "manual s calculator", "heat pump sizing
calculator", and "what size ac for 2000 sq ft". It says "Manual J alternative", never
"Manual J calculator" on its own, because it is not approved Manual J software.
`tests/test_hvac_loads.py` recomputes the guide's sizing tables, so they cannot drift.

## Files

- `index.html`: the step flow, the sizing guide, and background copy.
- `app/model.js`: the house geometry. Rooms always tile the shell, because walls
  move and rooms follow. Windows cannot overlap.
- `app/drawing.js`: plan, section, and 3D views of the model.
- `app/core.js`: assumptions, confirmations, plan editing, and the running estimate.
- `app/study.js`: sensitivity sweeps and grids, each point a full engine run.
- `app/engine.js`: loads Pyodide and the engine, and holds the system choices.
- `app/page.js`: settings, share links, fuel bill check, and export.
- `data/stations.json`: design conditions and temperature bins by NOAA station.
- `data/zips.txt`: US ZIP centroids from the Census ZCTA gazetteer.
- `test-cases/`: published houses as engine inputs, for checking the engine.

## Validation

`tests/test_hvac_loads.py` checks the Atlanta example from ASHRAE Fundamentals
Chapter 17 and the Sacramento Manual J report, ASHRAE's driving-force and duct tables,
the moist air equations, and the conduction solver against a finite-difference march.
`tests/browser/hvac-model.cjs` fuzzes the geometry with 9,000 random edits, and
`tests/browser/hvac-load-calculator.cjs` drives the page with real pointer drags.
