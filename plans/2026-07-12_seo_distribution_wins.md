# SEO & Distribution Quick Wins

Date: 2026-07-12

## Context

transparent.tools has 60 tools but only a handful of users/week. The bottleneck is
**distribution, not product**. This plan captures low-effort, high-leverage fixes that
make the existing catalog discoverable, plus a prioritized backlog of the
higher-converting tools to build next (because we can't help ourselves).

Diagnostic facts gathered 2026-07-12:
- Sitemap is hand-maintained and drifted: **7 real tools missing**
  (`bearing-selector`, `corrected-thrust`, `fan-curve-explorer`, `fan-type-selector`,
  `materials-explorer`, `motor-topology-explorer`, `transient-heatsink`) and it lists
  6 `example_tool_*` demos that should NOT be indexed.
- **53 / 60 tools have no `<meta name="description">`.**
- **0 / 60 tools have `rel="canonical"`.**
- **0 / 60 tools have OpenGraph / Twitter card tags** → broken/blank social previews.
- `catalog.json` already has a clean `title` + `description` for every tool, so the
  meta gaps are fully scriptable from a single source of truth.
- GA4 is installed (`G-YG3SBRRZFZ`) but no custom events → we have no demand signal
  for which tools people would pay to export.

## Concrete Wins (execute now)

### Win 1 — Self-maintaining sitemap
- Add `scripts/generate_sitemap.py`: reads `catalog.json`, emits `sitemap.xml`.
  - Include static pages (`/`, `/about.html`, `/legal.html`).
  - Exclude `example_tool*` and `unit_conversion_prototyping` (prototypes/demos).
  - `priority` 0.8 for `human-verified` tools, 0.6 otherwise; `changefreq` monthly.
  - Deterministic ordering (verified first, then alpha) so diffs stay clean.
- Wire into `netlify.toml` build `command` so it regenerates on every deploy and
  never drifts again.
- Regenerate `sitemap.xml` now.

### Win 2 — Backfill SEO meta from catalog (scripted, idempotent)
- Add `scripts/inject_seo_meta.py`: for each real tool in `catalog.json`, patch its
  `index.html <head>` **only if the tag is missing**:
  - `<meta name="description">` from catalog `description` (trimmed to ~155 chars).
  - `<link rel="canonical">` to `https://transparent.tools/<path>`.
  - OpenGraph + Twitter card (`og:title`, `og:description`, `og:url`, `og:type`,
    `og:image` → existing `/og-image.png`, `twitter:card=summary_large_image`).
  - Insert block immediately after the `<title>` tag. Idempotent: re-running is a
    no-op. Skips `example_tool*` and prototypes.
- Report per-tool what was added; run it; spot-check 2–3 files.

### Win 3 — GA4 export/demand instrumentation
- Add `shared/analytics-autotrack.js`: a dependency-free script that attaches one
  delegated click listener and fires a GA4 `export_action` event when the user clicks
  anything that looks like export/download/copy (matches by `data-track`, or button
  text / id / class containing export|download|csv|xlsx|pdf|copy). Guards on
  `window.gtag` existing so it's a no-op locally.
- Inject the `<script src="/shared/analytics-autotrack.js" defer></script>` include
  into each real tool head in the same `inject_seo_meta.py` pass (idempotent).
- Result: six months of data on which tools drive export intent → tells us what to
  gate later, instead of guessing.

### Verification
- `python3 scripts/generate_sitemap.py` produces a sitemap whose tool set exactly
  equals `catalog.json` minus excludes.
- Re-running both scripts is a clean no-op (idempotency check via `git diff`).
- Load one patched tool locally (`python -m http.server`) and confirm no console
  errors and head tags render.

## Tool Backlog — build in this order (SEO-converting archetypes)

Rationale: winners are **pass/fail decisions** and **sizing** questions people Google
verbatim, ideally naming a standard. Polish before building new — a strong existing
tool outranks a new weak one.

Tier A — highest search volume / decision-blocking:
1. **Wire size + breaker + voltage-drop (NEC)** — polish existing `wire-sizing`;
   one of the highest-volume engineering searches. Add pass/fail + ampacity table.
2. **Beam deflection L/360 pass-fail checker** — "is this beam ok" with a verdict and
   a client-ready export. Build on `beam-bending`.
3. **Bolt safety-factor / preload check (VDI 2230 / ISO 898-1)** — extend
   `bolt-torque` with a pass/fail SF verdict.

Tier B — strong sizing/selection intent:
4. **Pipe / duct diameter sizing** (flow + pressure drop).
5. **Fan CFM / static-pressure selector** — you have `fan-*`; add a sizing verdict.
6. **Motor current → breaker + wire size** (ties Tier A #1 to motors).

Tier C — named-standard checks (low volume, high intent, great backlinks):
7. **Noise exposure vs OSHA/ISO limit** (build on `simple-acoustics`).
8. **Thermal rise vs insulation class** (build on motor-thermal family).
9. **Pressure vessel per ASME VIII** (harden existing `pressure-vessel`).

Anti-list (do NOT invest in for growth): `random-generator`, `timer-toolkit`,
`circle-basics-demo`, `orders-of-magnitude-atlas` — traffic filler, no decision/export.

## Non-code follow-ups (owner: Drew, cannot be scripted here)
- Submit + verify site in **Google Search Console**; read the Impressions report to
  find which tools already rank. Highest-ROI 10-minute manual task.
- Launch cadence: one sharp single-tool post/month to r/AskEngineers,
  r/MechanicalEngineering, or Show HN. Lead with one tool, never "60 tools".

## Explicitly deferred (per monetization roadmap — needs traffic first)
Ads, premium tier, pay-gated exports, B2B. Revisit only past ~5k visitors/mo.
