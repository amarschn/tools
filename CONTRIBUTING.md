# Contributing

This guide describes the day-to-day development workflow, including how to
prototype new tools safely without deploying to production. For tool creation
standards (templates, docstrings, required files), see `AGENTS.md`.

## Branch Model

- `main`: Production. Only verified or approved releases land here.
- `staging`: Integration and QA. Safe place for prototypes and experiments.
- `feature/*`: All new work starts here.

## Prototype-to-Production Workflow

1. Sync:
   - `git checkout main`
   - `git pull`
2. Create a branch:
   - `git checkout -b feature/<short-name>`
3. Build your tool:
   - Add `/tools/<tool-slug>/index.html` and `README.md`.
   - Add or update `/pycalcs/*.py` functions with full docstrings.
   - Add `/tests/test_<module>.py`.
   - Update `catalog.json` only if you want the tool visible in staging.
4. Run tests:
   - `python -m pytest`
5. Open a PR to `staging`:
   - Mark as Draft if it is experimental or incomplete.
   - CI should run checks and generate a preview URL.
6. Merge to `staging`:
   - Use the staging site for QA and sharing.
7. Promote to production:
   - Open a PR from `staging` to `main`.
   - Use the release checklist in `docs/RELEASE.md`.

## Visibility Rules

- Only `main` is production. Anything merged only to `staging` will not ship.
- Experimental tools are allowed in `staging` and should be clearly labeled
  as experimental in their tool title or tags.
- Tools are visible on a site only if they appear in that branch's
  `catalog.json`.

## Pull Request Checklist

- Tool folder has `index.html` and `README.md`.
- Pycalcs function docstrings follow the required format.
- Tests added or updated.
- `catalog.json` entry added (if the tool should appear in staging or prod).
- `python -m pytest` passes.

## CI Expectations (High Level)

CI should run on every PR and on `staging`/`main` pushes:
- Unit tests (`pytest`)
- `catalog.json` validation (paths exist, JSON is valid)

See `docs/RELEASE.md` for deployment and release details.
