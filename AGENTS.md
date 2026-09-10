# Interface changes

- The user requires express permission before an interface redesign. Requests
  to finish, integrate, fix, or deploy the project do not authorize changing its
  visual direction or interaction model.
- Prototype 05 (`prototypes/05-dual-mode.html`) is the approved visual and
  interaction reference: compact chrome, direct search, expandable taxonomy,
  and dense value/condition/source rows. Preserve that design when wiring data
  or adding necessary controls.
- Keep UI text brief and functional. Do not add branding, slogans, explanatory
  panels, repeated warnings, or descriptions of the implementation to the main
  lookup flow without express permission. Keep source facts and essential
  distinctions such as minimum limits and test conditions intact.
- Preserve the original prototype files. Make production changes in `src/`
  and regenerate `materials/` through the builder.
