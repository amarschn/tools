# Prototypes Workspace

This directory is for internal UI and interaction R&D that should not ship as
part of the normal public website.

Why this lives under `_internal/`:

- The leading underscore keeps it out of GitHub Pages/Jekyll output.
- It stays outside the public `tools/` tree and out of `catalog.json`.

Guidelines:

- Use this area for exploratory HTML, CSS, and JavaScript prototypes.
- Do not register anything here in public navigation, the sitemap, or the
  catalog.
- Do not store secrets here. This repository is still source-visible even when
  a path is not publicly routed.

Suggested structure:

- `_internal/prototypes/<prototype-name>/index.html`
- `_internal/prototypes/<prototype-name>/README.md`

For local iteration, run the normal local server from the repo root and open the
prototype path directly.
