# Release and Deployment

This document defines the release flow and CI/CD expectations. It is
host-agnostic so you can choose a provider later without changing the process.

## Environments

- Local: developer machine for building and testing.
- Staging: `staging` branch, used for QA and prototypes.
- Production: `main` branch, public release.

Set these when a hosting provider is chosen:
- `STAGING_URL`: TBD
- `PROD_URL`: TBD

## CI/CD Jobs (Expected)

Run on pull requests:
- `checks`: run `pytest` and validate `catalog.json`.
- `preview`: build and publish a temporary preview URL.

Run on branch pushes:
- `deploy-staging`: build and publish `staging`.
- `deploy-prod`: build and publish `main`.

## Release Flow

1. Feature work happens on `feature/*`.
2. Open PR to `staging` for review.
3. Merge to `staging` and validate on the staging site.
4. Open PR from `staging` to `main`.
5. Merge to `main` to deploy production.

## Staging Checklist

- Tests pass (`python -m pytest`).
- Tool renders correctly on the staging site.
- Input validation behaves as expected (edge cases).
- Tool is labeled correctly (Verified, In Review, or Experimental).

## Production Checklist

- All staging checks complete.
- `catalog.json` reflects the intended tool visibility.
- Verified tools include test cases and references.
- Any new badges or labels are consistent with project policy.

## Hotfixes

- Create a branch from `main` (e.g., `hotfix/<issue>`).
- Apply the fix and run tests.
- Open PR to `staging` for quick QA when possible.
- Merge to `main` and deploy.
- Back-merge the hotfix into `staging` if it diverged.

## Rollback

- Revert the offending commit on `main`.
- Let CI redeploy production.

## Tool Release Checklist (REQUIRED before merging any new or changed tool)

The generic checklists above kept missing tool-level UI defects (a legacy tool
shipped with a dark-only hard-coded theme, no settings panel, no tooltips, and an
invisible copy-link button). Run through every item below for any tool you create
**or modify** before merging to `main`. Standards referenced here are defined in
`AGENTS.md` ("Advanced Tool UI Patterns") and embodied in `tools/example_tool*`.

### Theme & appearance
- [ ] Works in **both light and dark** — no hard-coded single-theme colors. All
      colors come from CSS variables (`:root` light defaults + `body[data-theme="dark"]`
      overrides + `@media (prefers-color-scheme: dark)`).
- [ ] Default theme follows the system (`system`/Auto).
- [ ] **Settings panel present** with a Theme toggle (Light / Dark / Auto),
      persisted to `localStorage`.
- [ ] No layout shift / flash of wrong theme on load.

### Inputs & guidance
- [ ] **Every input has a tooltip / help affordance** explaining it.
- [ ] Sensible defaults; the tool loads to a usable, calculable state.
- [ ] Validation handles zero, negative, and extreme values without crashing.
- [ ] Loading overlay shown during Pyodide init (never a broken half-loaded UI).

### Chrome & shared components
- [ ] Copy/share-link button present **and legible in both themes** (the tool
      must define the shared alias vars `--text-color`, `--bg-color`,
      `--border-color`, `--primary-light`, `--success-color`, or use the standard
      variable names, so `shared/url-state.js` renders correctly).
- [ ] Nav back-link + tool title present.
- [ ] Shared includes as applicable: `json-ld.js`, `analytics-autotrack.js`,
      `url-state.js`, and `verdict.js` for decision (pass/fail) tools.

### Results & correctness
- [ ] Primary result is prominent; progressive disclosure available (equations,
      derivation, references).
- [ ] For decision tools: the verdict separates **mandatory** requirements
      (pass/fail) from **advisory** guidance (recommendation) — do not present a
      recommendation as a hard requirement.
- [ ] Export/copy actions work (they fire the `export_action` GA event).

### SEO & catalog (scripted — do not hand-edit)
- [ ] Registered in `catalog.json` with an intent-first title and a unique
      description.
- [ ] Ran `python3 scripts/generate_sitemap.py` and
      `python3 scripts/inject_seo_meta.py` and committed the output.

### Verification (both required)
- [ ] `python -m pytest` is green.
- [ ] **Browser smoke test**: load the tool, run a calculation, confirm no
      console errors and that all controls are visible in both themes. Quick
      manual pass is the minimum; a Playwright drive is preferred, e.g.:
      `NODE_PATH=$(pwd)/node_modules node <script>` loading `/tools/<slug>/`,
      waiting for the calculate button to enable, clicking it, and asserting
      `pageerror`/`console.error` counts are zero.

### Labeling
- [ ] `human-verified` tag applied **only** if a maintainer actually verified the
      math end-to-end; otherwise it stays Experimental.
