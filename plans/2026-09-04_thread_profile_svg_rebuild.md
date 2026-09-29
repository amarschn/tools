# Thread Profile SVG Rebuild

Date: 2026-09-04
Status: Completed

## Objective

Replace the thread visualizer's generated SVG markup with a stable technical-drawing component. The result should resemble a handbook axial section, keep the internal and external profiles geometrically consistent, and place every dimension line and arrowhead deterministically.

## Problems to correct

- The current renderer rebuilds the entire SVG from JavaScript strings.
- Arrow markers use reference points that do not coincide with their tips, so dimension arrows miss their extension lines.
- Drawing, annotation, and responsive-layout coordinates are mixed in one function.
- Mobile uses a reduced procedural drawing rather than an authored annotation layout.
- Visual checks confirm that the page renders, but they do not protect the drawing against geometry regressions.

## Design

### Persistent SVG structure

Keep one inline SVG in the page. Its definitions, view groups, section fills, outlines, dimension lines, arrowheads, and labels will exist as authored markup. JavaScript will update attributes and text on those elements without replacing the SVG.

### Normalized thread model

Use normalized profile coordinates:

- Pitch: `P = 100`
- Fundamental triangle height: `H = sqrt(3) P / 2 = 86.6025`
- External major crest: `H / 8` below the sharp fundamental crest
- Basic pitch line: `H / 2` below the sharp fundamental crest
- Internal minor crest and external root: derived from the calculation results as fractions of `H`

The same model will generate the external and internal paths. Engaged flanks will therefore share identical points over their contact length.

### Drafting primitives

- Use explicit filled arrowhead polygons whose tips sit exactly on the dimension endpoints.
- Give extension lines a consistent gap from the profile and a short overshoot past the dimension line.
- Use non-scaling strokes for consistent line weight at different viewport sizes.
- Keep section hatching, visible outlines, centerlines, dimensions, and text in separate SVG layers.
- Use a background knockout behind dimension text when a line passes beneath it.

### Responsive layouts

Author desktop and mobile drawing groups in the same SVG. Each group will have its own dimensions and annotations. A media query listener will select the group and matching `viewBox`; it will not shrink desktop annotations into the mobile layout.

## Implementation steps

1. Add the persistent SVG and both layout groups to the tool page.
2. Replace SVG marker arrows with explicit dimension arrowheads.
3. Replace `innerHTML` rendering with normalized profile-path and label updates.
4. Add layout switching for initial load and viewport changes.
5. Remove obsolete procedural-renderer styles and helpers.
6. Check external, internal, and engaged views in light and dark themes at desktop and phone widths.
7. Verify profile contact, dimension endpoints, accessibility text, overflow, tests, and generated metadata.

## Acceptance criteria

- Engaged contact flanks are collinear within SVG coordinate precision.
- Every arrowhead tip equals its dimension-line endpoint.
- Extension lines stop with a visible gap from the thread profile.
- No SVG marker elements remain in the thread drawing.
- Switching views does not replace `#thread-profile-svg` in the DOM.
- Desktop and mobile use different authored annotation layouts.
- The drawing has no horizontal overflow at a 390 px viewport.
- Light and dark themes have legible outlines, hatching, dimensions, and labels.
- Browser checks report no page or console errors.
- The full Python test suite and focused thread tests pass.

## Files in scope

- `tools/thread-visualizer-sizer/index.html`
- `plans/2026-09-04_thread_profile_svg_rebuild.md`
- Generated discoverability files required by the release checklist

## Completion record

- Added one persistent inline SVG with authored desktop and mobile layouts.
- Replaced SVG markers with filled arrowhead polygons whose tips share the dimension-line endpoints.
- Normalized the profile model to `P = 100` and derived both mating profiles from the same fundamental triangle.
- Added responsive layout switching without replacing the SVG node.
- Added opposing section hatches and non-scaling line weights for light and dark themes.
- Added `tests/test_thread_visualizer_ui.py` to protect the SVG structure and pitch-arrow alignment.

Verification completed on 2026-09-04:

- Browser geometry checks found zero marker elements and exact arrow endpoint matches.
- The same SVG node remained mounted through all three view changes and the desktop-to-mobile transition.
- The engaged flank residual was below the SVG coordinate precision.
- The 390 px layout had no horizontal overflow.
- Browser console and page error counts were zero.
- Focused thread and UI tests: 65 passed.
- Full Python 3.13 suite: 1,183 passed.
- Sitemap, SEO injection, and homepage metadata generators completed successfully.
