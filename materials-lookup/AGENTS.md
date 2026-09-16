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
  and regenerate `tools/materials/` through the builder.

# Source documents

- Keep manufacturer PDFs and other original source documents in
  `private-sources/` at the repository root. It is git-ignored apart from its
  README. Never commit them, and never move them under `tools/`.
- The repository publishes its root and the local preview server serves
  untracked files, so treat every path inside it as reachable during
  development. Bind the preview server to 127.0.0.1.
- The public application and all its exports may contain textual citations,
  but must not contain document URLs, embeds, download endpoints, or documents.
- `tests/test_source_documents_stay_private.py` enforces this: no document may
  be tracked, and no document URL may reach the published data.
- Preserve local owner access through a private review directory outside this
  tree, built by `builder/prepare_source_review.py`.
- Future customer document access requires server-side authentication and paid
  entitlement checks, private storage, and reviewed distribution rights. It
  must not be implemented by hiding links or bundling files in the static app.

# Where things live

- This directory is the source of truth. `tools/materials/` is generated
  output; never hand-edit it.
- `builder/` was `scripts/` before this project moved into the tools
  repository, renamed to avoid colliding with that repository's own `scripts/`.
- Anything that must survive a rebuild belongs in `src/index.html`, because the
  published page is regenerated from it.
- The project this came from is closed. There is no upstream to sync with.
