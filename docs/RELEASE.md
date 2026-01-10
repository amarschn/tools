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
