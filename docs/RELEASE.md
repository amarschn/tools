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
production deploy. A completed task is one verified `task/<short-name>` branch
merged once into local `main`, followed by one push of `main` to GitHub. A
GitHub pull request may be used for review, but it is not required for release.

Keep every development commit, generated-file refresh, and review correction on
the task branch. Do not use `main` for iteration. Do not merge another task until
the current production deployment is published and verified.

Retries, rollbacks, and hotfixes are exceptions. Record the reason when a task
needs more than one production attempt.

### One-time Netlify configuration

Set these values in the Netlify project:

- Production branch: `main`.
- Deploy Previews: enabled when pull requests are used for review.
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
2. Review the task locally or through an optional pull request and Deploy
   Preview.
3. Complete the required checks and the Tool Release Checklist below. Run the
   SEO scripts when the task changes a tool or `catalog.json`.
4. Before merging, confirm:
   - the final task branch is pushed and verified;
   - the Netlify project is not paused;
   - the available credit balance covers Netlify's current production-deploy
     charge;
   - no other production deployment is running;
   - no cleanup or generated-file follow-up is still expected.
5. Release from the command line. If a pull request was used for review, do not
   click its GitHub merge button. Start from a worktree with no staged or
   modified tracked files. Review any untracked files and keep unrelated ones
   out of the merge. Fetch, then compare the four SHAs:

     ```bash
     git fetch origin
     git rev-parse main
     git rev-parse origin/main
     git rev-parse task/<short-name>
     git rev-parse origin/task/<short-name>
     ```

   The two `main` SHAs must match, and the two task-branch SHAs must match. If
   either pair differs, stop and reconcile it before releasing. If the pull
   request was already merged through GitHub, that action has already pushed
   `main` and triggered production: do not merge or push locally. Record the new
   remote `main` SHA and continue at step 7.

   Once both pairs match, merge locally without pushing:

     ```bash
     git switch main
     git merge --no-ff task/<short-name> -m "Merge task/<short-name>: <summary>"
     ```

   Inspect the integrated result and rerun the checks that apply to the task:

     ```bash
     git status --short
     git log --oneline --decorate -3
     git diff --check origin/main..HEAD
     ```

   Push only after the integrated result passes review and testing:

     ```bash
     git push origin main
     ```

   That final command is the task's one production-triggering push.
6. Record the pushed `main` SHA. Do not release the next task yet.
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
9. Record the deployed SHA and live verification result in the task notes or
   pull request. The task is not released until this step is complete.

The public site metadata can confirm the published SHA without a local Netlify
login:

```bash
curl -sS https://api.netlify.com/api/v1/sites/transparent.tools \
  | jq -r '.published_deploy.commit_ref'
```

### Rules that protect the release boundary

- Do not push work-in-progress commits to `main`. The only normal direct push to
  `main` is the single push made after merging a completed task branch locally.
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
be retried with the same commit, but record the retry in the task notes or pull
request.

### Rollback and hotfixes

Use **Publish Deploy** on a retained successful Netlify deploy when production
must be restored immediately. Netlify republishes that existing artifact without
a new build. A rollback does not change `main`, and the next automatic production
deployment will replace it.

After the rollback:

1. Create a `task/<short-name>` hotfix branch from `main`.
2. Revert or fix the problem and run the required checks.
3. Follow the normal release procedure above from step 4, including the SHA
   checks and integrated-main verification before the single push.

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
