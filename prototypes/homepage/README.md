# Homepage prototypes

Date: 2026-08-16

These four static prototypes read the repository's `/catalog.json` at runtime. They exclude the developer templates, map the remaining tools into eight display groups, and share search, discipline, and review-status logic from `shared.js`. Experimental tools are collapsed within each group until a visitor opens them, searches for them, or selects the experimental-only filter.

## View the options

From the repository root, run:

```bash
python3 -m http.server 8000
```

Then open one of these pages:

- `http://localhost:8000/prototypes/homepage/option-a/`
- `http://localhost:8000/prototypes/homepage/option-b/`
- `http://localhost:8000/prototypes/homepage/option-c/`
- `http://localhost:8000/prototypes/homepage/option-d/`

Opening an HTML file directly will not work because the browser blocks its request for `/catalog.json`.

## Option A: Technical index

Option A treats the catalog as a compact engineering directory. Numbered discipline sections and single-line tool entries fit more information on screen than cards, while the sticky controls keep search close at hand. This is the most direct match for the current design guidance and the cheapest option to maintain. Its tradeoff is a deliberately austere browsing experience.

## Option B: Grouped card grid

Option B keeps the familiar card pattern but puts it inside a clear discipline structure. The sidebar filters the catalog and shows counts that update with search and status changes; on small screens, it becomes a horizontal row of filter buttons. This option asks the least of returning visitors, though the catalog still takes more vertical space than the technical index.

## Option C: Blueprint identity

Option C adds a drafting-inspired identity to the grouped catalog. It uses an SVG dot field, line-art symbols for the eight verified tools, discipline fallback symbols, and a drawing title block. The result has more character without changing the palette or using gradients. Production work would need a careful review of every fallback symbol and the extra visual system it introduces.

## Option D: Search-first shelves

Option D puts an autofocus search box before the catalog and shows up to eight keyboard-selectable matches while the visitor types. Verified, most-used, and new shelves support browsing, and the full grouped index remains at the bottom for breadth and static SEO links. This is the fastest route to a known tool, but the shelf choices need analytics and periodic curation before they can make production claims.

## Shared behavior

All options retain the production verification queue, although the current six priority titles are already verified and therefore do not receive an "Up next" label. Links are converted from catalog-relative paths to root paths so they work from the nested prototype folders. Each listing contains the `BEGIN/END static tool links` comments used by the homepage SEO injector. Every page also includes a `noindex, nofollow` meta directive, and `robots.txt` disallows the full `/prototypes/` path.
