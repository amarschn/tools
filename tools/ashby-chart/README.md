# Ashby Chart Material Selector

## Purpose

This tool ranks candidate engineering materials using classical Ashby performance indices so designers can quickly screen for minimum-mass solutions. Users choose a design scenario (stiffness-driven beam, strength-limited tie, or buckling-limited column), enforce a minimum acceptable performance index, and specify how many top-ranked candidates to keep. The tool surfaces the highest-performing material, its properties, and a summary list suitable for sketching Ashby plots or exporting into detailed trade studies.

## Requirements

### Python Logic

* Implement `rank_materials_for_ashby(design_mode, minimum_performance_index, ranked_count)` in `pycalcs/materials.py`.
* The function must:
  * Validate inputs (supported design modes, positive thresholds, sensible candidate counts).
  * Calculate the relevant Ashby index for each material in the shared candidate set.
  * Filter out materials below the threshold, sort by index, and return the top `ranked_count`.
  * Provide substituted LaTeX strings for each reported quantity so the UI can show worked steps.
  * Include a docstring that follows the project parsing template with parameters, returns, LaTeX, and references.

### Frontend

* Base the UI on the canonical `tools/example_tool/index.html` template.
* Inputs must use IDs that match the docstring parameter names (`design_mode`, `minimum_performance_index`, `ranked_count`) so the tooltip system auto-populates.
* Results must render every return value, including the textual summary, with expandable details that expose both the governing equation and the substituted numeric expression.
* Provide a background section that describes the Ashby methodology, the candidate database, and how to interpret the performance indices.
* Placeholder visualization should explain that Ashby plots are forthcoming and suggest how to use the ranked summary today.

### Integration

* Register the tool in `catalog.json` so it appears on the landing page.
* Add regression tests in `tests/` to exercise each design scenario and confirm ranking plus validation logic.
* Keep all material property data contained within `pycalcs/materials.py` to preserve the single source of truth requirement. Any future data expansions should follow the same structure.
