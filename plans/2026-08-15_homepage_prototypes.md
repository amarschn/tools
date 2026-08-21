# Homepage Prototype Options

Date: 2026-08-15
Status: Convergence prototype complete; awaiting review

## Goal

Prototype three or four homepage redesigns for transparent.tools. The current page works but has three problems:

1. **Weak organization.** 66 tools render as one long card wall split only into "Verified" and "Experimental". The catalog has 24 categories with duplicates ("Reliability" vs "Reliability Engineering", "Aerospace" vs "Aerospace Engineering"), so the category filter is noisy and grouping by it would look broken.
2. **Off-brand styling.** `DESIGN.md` calls for a Polestar-inspired look: monochrome surfaces, no gradients, a single dark accent, hairline borders, Swiss sans-serif. The homepage instead uses a blue gradient hero, blue pill badges, rounded 12px cards, and heavy hover shadows. It reads more "generic SaaS landing page" than "engineering reference".
3. **Low visual interest.** Every card is identical text. Nothing signals what a tool actually does or draws the eye.

This plan is prototypes only. No changes to the production `index.html` in this phase.

## Constraints the prototypes must respect

- **Pure static site, no build step.** Each prototype is a single self-contained HTML file (inline CSS/JS is fine) that fetches `catalog.json` at runtime, same as the current page.
- **SEO static links must survive.** `scripts/inject_seo_meta.py` injects a `<!-- BEGIN static tool links -->` block into `#tool-grid` on the real homepage. Prototypes should include a placeholder comment pair in their listing container so the eventual winner can adopt the same injection without script changes.
- **`catalog.json` is the single source of truth.** Prototypes read it as-is. Any category cleanup happens as a display-side mapping in the prototype JS (see "Shared prework"), not by editing `catalog.json`, so prototypes stay decoupled from data changes.
- **Keep existing behavior available:** search, category filter, verified/experimental status, the "Up Next" priority list, footer links (About, Terms, Ko-fi), Google Analytics can be omitted from prototypes.
- **Copy standards:** run the `avoid-ai-writing` skill on any new user-facing copy (taglines, section blurbs).

## Where prototypes live

```
prototypes/homepage/
  shared.js          # catalog loading, category mapping, search/filter logic
  tool-meta.json     # prototype-only Git dates, repository change counts, sourced versions
  option-a/index.html
  option-b/index.html
  option-c/index.html
  option-d/index.html
  option-e/index.html
  option-f/index.html
  option-g/index.html
  option-h/index.html
  option-i/index.html
  option-j/index.html
  option-k/index.html
  option-l/index.html
  option-m/index.html
  README.md          # one paragraph per option, how to view
```

View with `python -m http.server` from repo root at `http://localhost:8000/prototypes/homepage/option-a/`. Fetch the catalog with an absolute path (`/catalog.json`) so it resolves from the subdirectory. Add `prototypes/` to `robots.txt` disallow so Google never sees duplicate homepages.

## Shared prework (do once, all options use it)

1. **Display-side category taxonomy.** A JS map that collapses the 24 raw categories into 7 or 8 display groups, roughly:
   - Mechanical & Structures (Mechanical Engineering, Structural Engineering, Machine Design, Fasteners)
   - Thermal & Fluids (Thermal Sciences, Fluid Mechanics)
   - Electrical (Electrical Engineering, Energy Storage)
   - Materials & Manufacturing (Materials, Manufacturing, Chemical Engineering)
   - Reliability & Controls (Reliability, Reliability Engineering, Control Systems)
   - Acoustics & Vibration (Acoustics)
   - Reference & Utilities (Reference, Utility, Education, Business, Strategy, Games)
   - Aerospace (Aerospace, Aerospace Engineering)
   Templates category is excluded from the homepage entirely (example_tool* entries are developer scaffolding, not user-facing).
2. **Design tokens.** One `:root` block copied from DESIGN.md (dark `#0b0d12` accent, `#f8f9fb` background, hairline `#e5e7eb` borders, 8px radius, Helvetica Neue stack, SF Mono for numbers). All options share it so the comparison is about layout and organization, not palette.
3. **Tool count sanity check.** Decide whether experimental tools show by default or behind a toggle. Recommendation: show verified first within each group, experimental collapsed behind a "Show experimental (N)" control per group. This alone cuts the visible wall roughly in half.

## Option A: Technical index (dense directory)

The "engineering handbook" answer. Kill the cards. Tools render as a dense, scannable directory: category group headings with rule lines, each tool a single row (name, one-line description, status mark, category). Two columns on desktop, one on mobile. Monospace tool counts in the margins. A thin sticky header holds the site name, search box, and status filter.

- Visual interest comes from typography and structure, not decoration: numbered section headings (01 Mechanical & Structures), hairline rules, a small monochrome status glyph per row (filled square = verified, outline = experimental).
- Closest to DESIGN.md, cheapest to build, densest information. Risk: can feel austere; the search box has to be very prominent since there is no visual browsing.

## Option B: Grouped card grid with sidebar nav

Evolution rather than revolution. Keep cards but restyle them to the token set (white, hairline border, subtle shadow, dark "Open" link instead of a blue button). Add a left sidebar (collapsing to a horizontal chip row on mobile) with the display groups and live counts. Clicking a group scrolls to or filters that section. Verified tools sort first inside each group; experimental cards get a muted treatment (slightly desaturated, outline status tag).

- A compact hero replaces the gradient banner: site name, one sentence, search field, and a stat line ("66 calculators, 8 verified, all client-side") set in mono.
- Familiar layout, lowest user relearning cost. Risk: still card-heavy; needs discipline on card height (clamp descriptions to two lines) to look organized.

## Option C: Blueprint identity (visual-forward)

Same structure as B but with a drafting-inspired visual layer for differentiation and memorability:

- A faint grid-paper background (CSS `linear-gradient` hairlines at low opacity, per DESIGN.md's no-gradient rule this needs a check; if it reads as decoration rather than surface, use a subtle dot grid instead).
- Each tool card gets a small line-art SVG glyph (24x24, single stroke weight, currentColor) drawn from a shared sprite: a beam with load arrow for beam bending, a bolt for torque, a fan curve for fan tools. Start with glyphs for the 8 verified tools plus a per-group default glyph so no card is empty.
- A "title block" footer strip styled like a drawing title block (project name, revision date, sheet number) as a signature detail.
- Highest visual interest and most brand personality. Risk: the SVG sprite is real work; if glyphs are mediocre it looks worse than no glyphs. Scope the prototype to sprite-with-8-real-glyphs and stub the rest.

## Option D: Search-first with curated shelves

Treat the homepage like a reference desk rather than a catalog. A large centered search input dominates above the fold (autofocused, keyboard navigable results as you type). Below it, three or four curated horizontal shelves instead of the full wall:

- "Verified" (the 8 verified tools)
- "Most used" (hand-picked for now; later driven by analytics)
- "New" (last 5 added, derivable from catalog order or a date field)
- A full A-to-Z index at the bottom as plain links grouped by display category (this doubles as the static-link injection target).
- Best fit for the SEO/traffic priority: landing users get to a tool in one action. Risk: hides the breadth of the catalog; the shelves need curation decisions.

## What "done" looks like for the prototype phase

- Options A through M render correctly against the live `catalog.json` from a local server, desktop and ~375px mobile widths.
- Search and status filtering work in each (shared.js).
- Desktop screenshots are saved for Options A through M. Mobile screenshots are also saved for the second, third, and convergence batches, where navigation density and preview behavior are part of the comparison.
- `prototypes/homepage/README.md` summarizes each option in a paragraph with its tradeoff.
- No edits to `index.html`, `catalog.json`, or the SEO scripts.

## First prototype review

Review completed on 2026-08-17 against the real catalog at desktop and 375px mobile widths. All four options preserve search, discipline and review-status filtering, collapsed experimental listings, the verification queue, and the static-link marker contract. Search and the experimental-only filter reveal matching experimental tools without leaving an ineffective disclosure control on screen. The catalog resolves to 57 public tools after the 9 developer templates are excluded: 8 verified and 49 experimental.

The first review selected **Option D's search-first entry over Option A's technical index**:

- Keep D's large keyboard-accessible search and compact result list as the primary route for visitors who know what they need.
- Use A's numbered, two-column discipline index as the complete catalog below search. It shows the site's breadth without returning to a card wall.
- Retain the per-discipline experimental disclosure and the shared eight-group display taxonomy from `shared.js`.
- Use one verified-tools shelf only if it improves the transition between search and the index. Do not publish a "Most used" shelf until analytics can support the claim.
- Treat C's line symbols as an optional later enhancement for verified tools, not a dependency of the first production pass.

Option B remains a useful reference for discipline counts and mobile filter controls, but its repeated cards consume too much vertical space. Option C establishes a credible visual identity, though its symbol library adds maintenance work before it improves finding a tool. The selected hybrid gives search the fastest path and keeps the full catalog readable, static-link compatible, and inexpensive to maintain.

The next review rejected enough of Option D that this first selection is no longer the production recommendation.

## Second review and revised requirements

Feedback on 2026-08-17 kept the large search field and the complete index, then removed the rest of Option D's browsing structure. The next batch follows these rules:

- The page title is `Engineering Tools`. Title headers never use questions, commands, or conversational prompts.
- Search is followed directly by a section titled `Tool Index`.
- There are no Verified, Most used, New, Up next, or other horizontal shelves.
- The index never uses A-to-Z wording.
- Each tool card or row is one large link. A small `Open` link is not a separate click target.
- Tags remain visible on each listing.
- Each listing shows its actual last repository change date and directory commit count. That count is labeled `repository changes`, not version or revision.
- Semantic versions appear only where the tool documents one. The prototype metadata must not infer or invent versions.
- Visual preview treatments must work with keyboard focus as well as hover and must not block mobile navigation.

Options E through H compare full-card grids, a pinned inspector, inline thumbnails with enlarged previews, and a lazy live-page preview. The shared metadata file is derived from Git history and is prototype data only. Production promotion still needs a maintained metadata source that accounts for shared Python and frontend dependencies.

Implementation and desktop/mobile browser review completed on 2026-08-18.

## Third review and revised requirements

Feedback on 2026-08-18 selected Option F as the best starting point. Its dense list and immediate filtering stay. The next batch compares quieter page identities and removes the parts that did not help:

- Page titles stay within the standard heading scale. The title must not dominate the search and index.
- The separate `transparent.tools` masthead is removed from the prototypes. The comparison tests `Tool Index`, `Engineering Calculators`, and `Tools` as direct page names.
- Automatic hover and focus previews are removed. They are visually distracting.
- Repeating list content in a sticky inspector is removed.
- Tags, update dates, repository change counts, versions, discipline filters, and review-status filters remain visible.
- A sparse gray dot field tests an engineering-paper background. It uses a repeating SVG image rather than a CSS gradient.
- The full row remains the primary tool link. Option L adds a separate 44px preview control as a deliberate exception, with a large live-page view that opens only after activation.

The third batch separates those choices:

- **Option I:** quiet `Tool Index`, full-page dot field, dense list, no preview.
- **Option J:** restrained `Engineering Calculators` heading, dots limited to the search zone, clean list, no preview.
- **Option K:** compact `Tools` heading, discipline rail, ledger-style list, no preview.
- **Option L:** quiet `Tool Index`, dense list, and an explicit large live-page preview drawer. Nothing opens on hover or focus.

Production promotion remains a separate task after one direction is selected.

Implementation and desktop/mobile browser review completed on 2026-08-18. Option L's click-only preview was also checked for lazy loading, Escape dismissal, focus restoration, and a 44px mobile control.

## Fourth review and convergence prototype

Feedback on 2026-08-21 selected Option L's click-only preview and kept the dense, immediate filtering from the prior list prototypes. Option M combines those behaviors with a quieter page hierarchy:

- A 52px site header carries a small `transparent.tools` wordmark above the page content.
- `Tool Index` remains the page heading and stays visually stronger than the wordmark.
- The page and compact search toolbar use plain white backgrounds with hairline borders.
- Search, discipline, and review status use one compact toolbar on desktop and stack on mobile.
- Default catalog counts are omitted. A result count appears only while a search or filter is active.
- Preview remains a deliberate button action. Hover and focus do not open or load a preview.
- The preview drawer uses the selected tool name as its heading and gives the live page most of the viewport.

Option M is a prototype. Selecting it for production, extending the site header to every tool, and defining production metadata are separate tasks.

## Evaluation criteria for picking a winner

1. Can a first-time visitor find a specific tool (say, bolt torque) in under 5 seconds?
2. Does it look like a tool an engineer trusts? (DESIGN.md alignment)
3. Does the 57-tool public catalog read as organized rather than overwhelming?
4. How much work to productionize, including keeping `inject_seo_meta.py` compatible?

The first review selected D's search treatment on top of A's index. The second batch retains search and replaces the rest of that proposal with the requirements above.
