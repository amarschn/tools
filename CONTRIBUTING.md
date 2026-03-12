# Contributing

This guide describes the day-to-day development workflow, including how to
prototype new tools safely without deploying to production. For tool creation
standards (templates, docstrings, required files), see `AGENTS.md`.

## Branch Model

- `main`: Stable, verified, and close to deployable at all times.
- `task/<short-name>`: One branch per active task. Use it for features, fixes, refactors, and experiments.

## Branching Rules

- Start each non-trivial change from `main`.
- Use one branch per task, not per computer and not per AI agent.
- Reuse the same `task/<short-name>` branch across all computers until the task is complete.
- Push task branches frequently so another machine can resume from the same remote branch.
- Merge back to `main` only after the task is verified.
- Delete the task branch after merge to keep the branch list clean.

## Day-to-Day Workflow

1. Sync:
   - `git switch main`
   - `git pull`
2. Create a branch:
   - `git switch -c task/<short-name>`
3. Build your tool:
   - Add `/tools/<tool-slug>/index.html` and `README.md`.
   - Add or update `/pycalcs/*.py` functions with full docstrings.
   - Add `/tests/test_<module>.py`.
   - Update `catalog.json` if the tool should appear on the site after merge to `main`.
4. Run tests:
   - `python -m pytest`
5. Push your branch:
   - `git push -u origin task/<short-name>`
6. Resume work on another computer:
   - `git fetch`
   - `git switch task/<short-name>`
   - `git pull`
7. Open a PR to `main`:
   - Mark as Draft if the task is still in progress.
   - Merge only after review and verification.

## Visibility Rules

- Only `main` should be treated as the trustworthy branch for shipping or deployment.
- Experimental work belongs on a `task/<short-name>` branch until it is ready.
- Tools are visible on a site only if they appear in that branch's `catalog.json`.

## Pull Request Checklist

- Tool folder has `index.html` and `README.md`.
- Pycalcs function docstrings follow the required format.
- Tests added or updated.
- `catalog.json` entry added (if the tool should appear after merge to `main`).
- `python -m pytest` passes.

## CI Expectations (High Level)

CI should run on every PR and on `main` pushes:
- Unit tests (`pytest`)
- `catalog.json` validation (paths exist, JSON is valid)

See `docs/RELEASE.md` for deployment and release details.
