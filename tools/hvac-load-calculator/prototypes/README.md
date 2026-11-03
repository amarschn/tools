# HVAC load calculator prototypes

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
