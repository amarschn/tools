# Migrate Hosting: Netlify → Cloudflare Pages

Date: 2026-07-19

## Why

- Netlify ran out of free "deploy credits" — new deploys are blocked, and it now
  effectively requires a paid subscription. We don't want a subscription.
- The site is 100% static (client-side Pyodide, no backend today), so it never
  needs paid hosting.
- Goals that shaped the choice:
  - **Free**, no credit throttling.
  - Ability to make the **repo private later** (see note below).
  - A path to **dynamic features** (Stripe checkout, forms, saved configs) when
    monetization matures — the original reason for moving to Netlify.

## Decision: Cloudflare Pages

Best fit on all three goals:

| | GitHub Pages | Netlify (now) | **Cloudflare Pages (chosen)** |
|---|---|---|---|
| Static hosting | free | credit-walled | **free, unlimited bandwidth** |
| Private repo (free) | ❌ needs public | ✅ | ✅ |
| Serverless functions (free) | ❌ | ✅ (paid tier) | ✅ **Pages Functions, 100k req/day** |
| Runs a build step | ❌ | ✅ | ✅ (build image has Node + Python) |
| Custom domain + HTTPS | ✅ | ✅ | ✅ |
| Cost | $0 | $$ | **$0** |

GitHub Pages was rejected only because its free tier forces the repo public, and
we want the option to go private. Ads, for the record, need **no** special host
(they're client-side JS and work anywhere) — that was never a real reason to pay
Netlify.

## Facts / current state (verified 2026-07-19)

- Repo: `github.com/amarschn/tools`, deploys via git; branch `main`.
- Domain `transparent.tools`, DNS currently managed at **Squarespace** (registrar),
  pointed at Netlify. Legacy GitHub Pages also active at `amarschn.github.io`.
- Static site; `sitemap.xml` is committed (Netlify's build ran
  `scripts/generate_sitemap.py`; other hosts serve the committed file).
- Absolute asset paths (`/shared/...`) require serving from the **domain root** —
  fine on a custom domain.
- `_internal/prototypes/` exists at the repo root; `netlify.toml` redirected
  `/_internal/*` → 404 to hide it. On Cloudflare it would be publicly reachable
  unless we replicate that (see repo prep).
- No `404.html` exists.
- `gh` CLI is not authenticated locally, so repo visibility wasn't confirmed —
  it is almost certainly **public** today (required by the free GitHub Pages it
  currently uses).

## Migration steps

### Step 1 — Repo prep (do in one commit before connecting Cloudflare)
- [ ] Decide build strategy. Simplest/robust: **no build** — serve the static
      root and rely on the committed `sitemap.xml`. (Alternative: set Cloudflare
      build command `python3 scripts/generate_sitemap.py`; its build image has
      Python 3, but the no-build path removes a failure mode. Keep running the
      SEO scripts locally before commits either way — already documented in
      AGENTS.md.)
- [ ] Add a `_redirects` file (Cloudflare Pages supports Netlify-style
      `_redirects`) to preserve hiding of the prototypes, e.g.:
      `/_internal/*  /404.html  404`
- [ ] Add a minimal `404.html`.
- [ ] Optional: keep `netlify.toml` until cutover is confirmed, then delete it.
- [ ] Update docs: `CLAUDE.md` + `AGENTS.md` "Deployment" sections, and the
      README, to describe Cloudflare Pages instead of Netlify.

### Step 2 — Create the Cloudflare Pages project (browser, ~5 min)
- [ ] Create a free Cloudflare account.
- [ ] Dashboard → **Workers & Pages → Create → Pages → Connect to Git** →
      authorize GitHub → select `amarschn/tools`.
- [ ] Config: Production branch `main`; **Build command** empty (or the sitemap
      command); **Build output directory** `/`. Deploy.
- [ ] Verify the site works at the generated `*.pages.dev` URL BEFORE touching
      the domain (check a few tools load, Pyodide runs, dark/light theme).

### Step 3 — Point `transparent.tools` at Cloudflare (browser, ~10 min + propagation)
- [ ] Cloudflare → **Add a site** → `transparent.tools` → it imports existing DNS
      records → note the **two Cloudflare nameservers** it assigns.
- [ ] At **Squarespace** (registrar): change the domain's **nameservers** to the
      two Cloudflare nameservers. (This makes Cloudflare your DNS — free, and adds
      CDN/caching/analytics.)
- [ ] Wait for nameserver propagation (minutes to a few hours; up to 24h).
- [ ] In the Pages project → **Custom domains → add `transparent.tools`** (and
      `www` if desired). Cloudflare auto-creates records (apex via CNAME
      flattening) and provisions HTTPS.
- [ ] Re-check DNS still has the **Google Search Console** verification TXT record
      after the import (re-add if the import dropped it).

### Step 4 — Decommission Netlify (browser)
- [ ] Once `transparent.tools` serves from Cloudflare and looks correct, remove
      the custom domain from the Netlify site (or delete the Netlify site).
- [ ] Delete `netlify.toml` from the repo (cleanup) and commit.

### Step 5 — Make the repo private (browser, whenever ready)
- [ ] GitHub repo → Settings → change visibility to **Private**.
- [ ] Cloudflare Pages keeps deploying (it holds GitHub OAuth access).
- [ ] The legacy `amarschn.github.io` Pages site will stop serving — expected and
      fine (we're off it). Note: going private only protects *future* commits;
      everything already public stays in Git history/forks.

## Stripe checkout (future, once on Cloudflare Pages)

Cloudflare **Pages Functions** provide the serverless backend Stripe needs, free
(100k req/day). Standard hosted-checkout flow:

```
Browser  --click "Buy"-->  /functions/api/checkout   (Pages Function)
                             creates a Stripe Checkout Session with the SECRET key
                             (stored as an encrypted Cloudflare env var)
Browser  <--redirect--   Stripe-hosted checkout page (Stripe handles the card UI)
             payment done --webhook-->  /functions/api/webhook
                                          verify signature, then unlock / email link
```

What it needs when we build it:
- A `/functions/api/checkout.js` function that calls the Stripe API (the `stripe`
  SDK works on the Workers runtime, or call the REST API via `fetch`) to create a
  Checkout Session and return its URL.
- A `/functions/api/webhook.js` function to verify the Stripe signature and
  fulfill (e.g., issue a one-time export/download token or email a link).
- Env vars in Cloudflare Pages settings (encrypted): `STRIPE_SECRET_KEY`,
  `STRIPE_WEBHOOK_SECRET`. Never commit these.
- Ties into the monetization roadmap: "pay-after-result" one-time exports
  (see `strategy/MONETIZATION_ROADMAP.md`). Defer until traffic justifies it.

## Safety / rollback

- The migration is reversible until Step 4: the Netlify deploy stays live until
  you remove its domain, and you validate on `*.pages.dev` before repointing DNS.
- Keep `netlify.toml` in the repo until cutover is confirmed.
- DNS nameserver change is the only hard-to-instant-revert step; verify the
  `*.pages.dev` site first so you're only flipping DNS once.

## Post-migration follow-ups
- Delete `netlify.toml`; update deployment docs.
- Consider a GitHub Action (or Cloudflare build command) to run
  `generate_sitemap.py` + `inject_seo_meta.py` on push, so SEO stays in sync
  without relying on remembering to run them locally.
