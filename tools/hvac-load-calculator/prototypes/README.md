# HVAC load calculator prototypes

## Current direction: option D, the guided build

`option-d-guided-build.html` builds the house as one model that gains detail step by
step, from a plain box to rooms and equipment, then ends in a sensitivity study.
`option-e-workbench.html` is the same model with no fixed order. Both use `v2/`:

- `model.js`: the geometry. Rooms always tile the shell, because walls move and rooms
  follow. `tests/browser/hvac-model.cjs` fuzzes it with 9,000 random edits.
- `drawing.js`: plan, section, and 3D views of that one model.
- `core.js`: assumptions, confirmations, plan editing, and the running estimate.
- `study.js`: sweeps and two-variable grids, each point a full engine run.

`tests/browser/hvac-build.cjs` drives both with real pointer drags.

## Earlier options

Three ways to make the calculation visual. All run the real engine in
`pycalcs/hvac_loads.py` through `proto-shared.js`, and all share a system choice,
tiered inputs, and drill-down from a result to its equation, symbols, and numbers.

- `option-a-cutaway.html`: section view of the house with heat flow arrows.
- `option-b-floorplan.html`: draggable floor plan with automatic exterior walls.
- `option-c-sizing-board.html`: load stacked against equipment capacity.

Run `python -m http.server` from the repository root, then open
`/tools/hvac-load-calculator/prototypes/option-a-cutaway.html`.
Prototypes update live as inputs change, unlike the current page. They are excluded
from search with `noindex`.
