# Deck Material Estimator

## Purpose

This tool estimates the quantity, weight, and approximate cost of the primary materials needed for a rectangular residential deck. It turns your layout assumptions—plan dimensions, support spacing, and preferred lumber profiles—into a shopping list that includes decking boards, joists, beams, posts, and footing concrete.

The calculator emphasises traceability: every value is derived from equations documented in the shared Python module, and each result in the UI links back to those expressions.

## Requirements

### Inputs

- Deck length (ft) measured along the ledger or primary support.
- Deck width (ft) projected perpendicular to the ledger.
- Joist spacing (in) between centres.
- Beam spacing (ft) measured from the ledger toward the outer edge.
- Post spacing (ft) along the beam direction.
- Waste allowance (%) applied to linear footage of boards, joists, and beams.
- Decking board selection (profile, cost/ft, weight/ft).
- Framing lumber selection for joists and built-up beams.
- Post size selection.
- Premix concrete bag selection for footings.

### Python Logic

- `pycalcs.decking.estimate_deck_materials(...)` performs all calculations, returning a dictionary of key metrics plus explanatory substitution strings for each equation.
- `pycalcs.decking.list_catalogues()` exposes human-friendly option labels so the UI can stay synchronised with the shared data tables.

### Outputs

- Material counts (board count, joist count, post count, concrete bags).
- Linear footage of decking, joists/rim boards, and beams.
- Estimated cost and weight for each material family plus combined totals.
- Intermediate footing concrete volume.
- Echo of the selected catalogue entries for context.

## Assumptions & Limitations

- The deck is rectangular with uniform joist spacing and built-up beams made from the same stock as the joists.
- Footings are assumed to be cylindrical with a 1.5&nbsp;ft diameter and 2&nbsp;ft depth; adjust post spacing or catalogue data to explore different footing strategies.
- Costs and weights are nominal averages intended for planning; always confirm local pricing and structural requirements before purchasing materials.
