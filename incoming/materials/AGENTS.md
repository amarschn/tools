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

# Source documents

- Keep manufacturer PDFs and other original source documents outside the
  repository and every publicly served directory. Never commit them.
- The public application and all its exports may contain textual citations,
  but must not contain document URLs, embeds, download endpoints, or documents.
- Preserve local owner access through a separate private review directory.
- Future customer document access requires server-side authentication and paid
  entitlement checks, private storage, and reviewed distribution rights. It
  must not be implemented by hiding links or bundling files in the static app.
