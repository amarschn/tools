# Homepage prototypes

Date: 2026-08-16

These static prototypes read the repository's `/catalog.json` at runtime. They exclude the developer templates, map the remaining tools into eight display groups, and share search, discipline, and review-status logic from `shared.js`. Options A through D are the first batch, E through H are the second, and I through L are the current list-focused batch.

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
- `http://localhost:8000/prototypes/homepage/option-e/`
- `http://localhost:8000/prototypes/homepage/option-f/`
- `http://localhost:8000/prototypes/homepage/option-g/`
- `http://localhost:8000/prototypes/homepage/option-h/`
- `http://localhost:8000/prototypes/homepage/option-i/`
- `http://localhost:8000/prototypes/homepage/option-j/`
- `http://localhost:8000/prototypes/homepage/option-k/`
- `http://localhost:8000/prototypes/homepage/option-l/`

Opening an HTML file directly will not work because the browser blocks its request for `/catalog.json`.

## Third batch: quiet list treatments

Every third-batch option keeps Option F's immediate list filtering and removes its duplicate inspector. Titles use the standard heading scale, the separate site masthead is gone, and no preview appears on hover. Each background tests a sparse SVG dot field without using a gradient.

### Option I: Quiet index

Option I uses `Tool Index` as the only page title. A faint dot field covers the canvas behind the search controls and dense grouped list. There is no preview interface.

### Option J: Search-led calculators

Option J labels the page `Engineering Calculators` and limits the dot field to the search zone. The list sits on a plain surface below it. This tests a little more context without returning to a large hero.

### Option K: Discipline ledger

Option K uses the compact title `Tools` and adds a desktop discipline rail beside the list. The rail becomes a normal filter on small screens. This is the densest browsing treatment in the batch and has no preview.

### Option L: Explicit live preview

Option L keeps a quiet `Tool Index` heading and adds a separate Preview button to each row. The button opens a large live tool page only after activation. The row itself still opens the tool, and hover never starts a preview.

## Second batch: search and tool index

Every second-batch option uses `Engineering Tools` as the page title, followed by search and `Tool Index`. There are no horizontal shelves. Each tool listing is one large link and shows tags, last repository change date, and directory change count. Options E through G use generated SVG images tied to the tool's discipline and title. Option H tests a lazy live-page preview.

### Option E: Full-card index

Option E groups compact cards by discipline. The whole card opens the tool, while hover or keyboard focus shows a larger image beside it. This is the closest replacement for Option D's index with the rejected shelves and small `Open` links removed.

### Option F: Directory with inspector

Option F keeps the index dense and uses a sticky inspector on the right at desktop widths. Moving through rows updates the image, description, tags, status, and repository metadata in one place. The inspector is removed on narrow screens, where each row remains a full-width link.

### Option G: Visual cards

Option G places a small generated image inside each card and enlarges it on hover or keyboard focus. Tags and metadata remain visible without opening the preview. This option uses more vertical space than E, but it gives each listing a visual anchor before interaction.

### Option H: Live preview rows

Option H uses compact rows and creates a non-interactive tool-page preview only after hover or keyboard focus. It tests whether an actual page preview is more useful than a generated image. Loading a tool page on preview costs more bandwidth and browser work, so production would need measurement and a static-thumbnail fallback.

## Prototype metadata

`tool-meta.json` records the last Git change date and commit count for each public tool directory. The interface labels the count as `repository changes`; it is not a semantic version or verification date. Only Fan Type Selector 1.0 and Heatsink Designer & Analysis 1.1 display versions because those values exist in the tools themselves. Directory dates include maintenance changes and do not account for changes in shared Python or frontend files.

## First batch

### Option A: Technical index

Option A treats the catalog as a compact engineering directory. Numbered discipline sections and single-line tool entries fit more information on screen than cards, while the sticky controls keep search close at hand. This is the most direct match for the current design guidance and the cheapest option to maintain. Its tradeoff is a deliberately austere browsing experience.

### Option B: Grouped card grid

Option B keeps the familiar card pattern but puts it inside a clear discipline structure. The sidebar filters the catalog and shows counts that update with search and status changes; on small screens, it becomes a horizontal row of filter buttons. This option asks the least of returning visitors, though the catalog still takes more vertical space than the technical index.

### Option C: Blueprint identity

Option C adds a drafting-inspired identity to the grouped catalog. It uses an SVG dot field, line-art symbols for the eight verified tools, discipline fallback symbols, and a drawing title block. The result has more character without changing the palette or using gradients. Production work would need a careful review of every fallback symbol and the extra visual system it introduces.

### Option D: Search-first shelves

Option D puts an autofocus search box before the catalog and shows up to eight keyboard-selectable matches while the visitor types. Verified, most-used, and new shelves support browsing, and the full grouped index remains at the bottom for breadth and static SEO links. This is the fastest route to a known tool, but the shelf choices need analytics and periodic curation before they can make production claims.

## Shared behavior

All options retain the production verification queue, although the current six priority titles are already verified and therefore do not receive an "Up next" label. Links are converted from catalog-relative paths to root paths so they work from the nested prototype folders. Each listing contains the `BEGIN/END static tool links` comments used by the homepage SEO injector. Every page also includes a `noindex, nofollow` meta directive, and `robots.txt` disallows the full `/prototypes/` path.
