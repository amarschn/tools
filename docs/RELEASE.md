# Release and Deployment

Netlify serves the production site at `https://transparent.tools`. The legacy
GitHub Pages site at `https://amarschn.github.io/tools/` is a secondary mirror.
The `main` branch is the intended production revision for both hosts.

## Environments

- Local: developer machine for building and testing.
- Preview: a Netlify Deploy Preview created from a pull request.
- Production: `main`, published at `https://transparent.tools`.

## Netlify production release policy

Under normal operation, one completed task produces one automatic Netlify
production deploy. A completed task is one verified `task/<short-name>` pull
request merged once into `main`.

Keep every development commit, generated-file refresh, and review correction on
the task branch. Do not use `main` for iteration. Do not merge another task until
the current production deployment is published and verified.

Retries, rollbacks, and hotfixes are exceptions. Record the reason when a task
needs more than one production attempt.

### One-time repository and Netlify configuration

Protect `main` with a GitHub branch ruleset before using this workflow:

- Require a pull request before changes can reach `main`.
- Block force pushes.
- Leave the bypass list empty. If an administrator needs bypass rights, grant
  **For pull requests only**, never **Always allow**.

See GitHub's [ruleset setup instructions](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository).

Set these values in the Netlify project:

- Production branch: `main`.
- Deploy Previews: enabled for pull requests.
- Auto publishing: enabled for the production branch.
- Enforce deployment methods: allow production publishing only through the Git
  provider. The setting is under **Project configuration > Build & deploy >
  Continuous deployment**. This prevents CLI, API, MCP, and agent sessions from
  publishing production directly.

Check the team's plan and billing-cycle dates under **Usage & billing**. On
Netlify credit-based plans, successful production deploys consume deploy
credits. Deploy Previews and branch deploys do not consume deploy credits, but
their traffic and other metered services can still use credits. See Netlify's
[credit documentation](https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/how-credits-work/).
As of August 16, 2026, Netlify lists 15 credits per successful production deploy
on a credit-based plan. Check the current charge before each release.

### Normal release procedure

1. Work on `task/<short-name>` and push that branch as often as needed. These
   pushes must not update `main`.
2. Open a pull request to `main`. Use its Deploy Preview for browser testing.
3. Complete the pull request checks and the Tool Release Checklist below. Run
   the SEO scripts when the task changes a tool or `catalog.json`.
4. Before merging, confirm:
   - the Deploy Preview represents the final task branch;
   - the Netlify project is not paused;
   - the available credit balance covers Netlify's current production-deploy
     charge;
   - no other production deployment is running;
   - no cleanup or generated-file follow-up is still expected.
5. Merge the pull request once. The merge method does not affect Netlify. The
   required boundary is one merge action and one push to `main`.
6. Record the new `main` SHA from GitHub. Do not merge the next task yet.
7. Open the [Netlify project](https://app.netlify.com/projects/elaborate-faloodeh-8b0224)
   **Deploys** page and confirm that one production deployment:
   - uses branch `main`;
   - uses the expected Git SHA;
   - reaches **Published**.
8. Verify the live site:
   - load `https://transparent.tools/`;
   - load every changed tool page and one unchanged tool page;
   - run a calculation on each changed tool;
   - check browser console errors and required generated files such as
     `sitemap.xml`.
9. Record the deployed SHA and live verification result in the pull request.
   The task is not released until this step is complete.

The public site metadata can confirm the published SHA without a local Netlify
login:

```bash
curl -sS https://api.netlify.com/api/v1/sites/transparent.tools \
  | jq -r '.published_deploy.commit_ref'
```

### Rules that protect the release boundary

- Do not push directly to `main`. Every change, including a hotfix or
  documentation-only change, must reach `main` through a pull request.
- Do not run `netlify deploy --prod` during the normal release flow.
- Do not create an empty commit to retrigger Netlify. Use **Trigger deploy** in
  the Netlify dashboard after confirming that the project can deploy.
- A retry builds the current branch head, not necessarily the commit attached to
  the old deploy record. Recheck the SHA before publishing.
- `[skip netlify]` and `[skip ci]` are exception tools, not the normal release
  path. On a multi-commit push, a token in the newest commit skips the entire
  push; the next unskipped push includes all accumulated changes. Do not put a
  skip token in a pull request title when its Deploy Preview is needed. See
  Netlify's [deploy management documentation](https://docs.netlify.com/deploy/manage-deploys/manage-deploys-overview/).

### Skipped or failed deployments

If Netlify marks a deploy `skipped` with no deploy time, check **Usage & billing**
and the project's build status first. The build command did not run. Resume the
project or restore capacity, then trigger one deployment of the current `main`
SHA from the dashboard.

If a build starts and fails, read the build log before retrying. Fix repository
code through a reviewed `task/<short-name>` hotfix branch. A provider failure may
be retried with the same commit, but record the retry in the pull request.

### Rollback and hotfixes

Use **Publish Deploy** on a retained successful Netlify deploy when production
must be restored immediately. Netlify republishes that existing artifact without
a new build. A rollback does not change `main`, and the next automatic production
deployment will replace it.

After the rollback:

1. Create a `task/<short-name>` hotfix branch from `main`.
2. Revert or fix the problem and run the required checks.
3. Open and review a pull request to `main`.
4. Merge it once and verify the resulting production deployment by SHA.

Manual CLI production deploys are outside this release policy. Keep Git-only
deployment enforcement enabled. If Git-based deployment is unavailable, publish
a retained successful deploy to restore service, then repair the Git integration
before releasing new code.

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
