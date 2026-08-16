# Tool UI Prototype Options

Date: 2026-08-15

## Goal

Prototype four tool-page UI directions, compare them, and converge on a replacement for `tools/example_tool/index.html` as the template every new tool copies. The target qualities, in priority order: instills confidence, cleaner, more engineering-focused. This plan covers the prototype phase; a follow-up plan will cover promoting the winner (likely a hybrid) to the official template and migrating existing tools.

This plan is expected to be iterative. Build the four prototypes, review, then revise this document with the chosen hybrid before templating.

## Why the current template loses confidence

Observed in `tools/example_tool/index.html` and the tools copied from it:

1. **No provenance.** No version, no published date, no revision history, no "checked by", no link to the Python module doing the math. The math transparency exists (equations, substituted values) but the trust layer does not.
2. **Results read as a web form, not an instrument.** Key outputs are inline paragraph text in a gray box. Numbers are not set in the mono font DESIGN.md prescribes, there is no hierarchy between the headline answer and secondary outputs, and units are informal.
3. **Weak loading and empty states.** The Calculate button doubles as the Pyodide loading indicator; the plot area is a dashed placeholder box.
4. **Generic detailing.** `[Expand]` / `[Show Steps]` bracket labels, a developer QA "chart checklist" shown to end users, a footer that still says "Engineering Tools", and stray CSS after `</html>` (example_tool/index.html:529).

## Decisions already made

- **All four directions get built as separate prototypes** so they can be compared uncombined before hybridizing.
- **Both recalculation modes are supported.** Whether a tool uses a Calculate button or live recompute is a per-tool decision, so the template must ship both patterns as first-class options with good states for each (button mode: pending/complete; live mode: debounce, stale indicator, invalid-input handling). Each prototype demonstrates one mode; see per-option notes.
- **Metadata source: `catalog.json` plus a git-derived date script** (decision delegated, rationale below).

## Version and published-date metadata

Every prototype displays, at minimum: tool version, last published date, and verification status with who checked it. Source of truth:

- Add optional fields to each `catalog.json` entry: `version` (string, e.g. "1.2"), `checked_by` (string or null), `revisions` (list of `{version, date, note}` entries, newest first).
- New script `scripts/update_tool_dates.py`, same self-maintaining pattern as `inject_seo_meta.py`: for each tool it runs `git log -1 --format=%as -- tools/<slug>/ pycalcs/<module>.py` and writes `last_published` back into `catalog.json`. Idempotent, run alongside the other SEO scripts.
- Tool pages fetch `/catalog.json` at load (they are Pyodide pages; one more fetch is negligible) and render the metadata block from their own entry, keyed by path. No hand-maintained dates in HTML, and version bumps happen in one file.
- Prototype phase: prototypes read a small `prototypes/tool-ui/meta-sample.json` with the same shape, so nothing touches `catalog.json` until the template is promoted. The script is speced here but built in the promotion phase.

## Where prototypes live

```
prototypes/tool-ui/
  meta-sample.json       # sample catalog entry with version/revisions fields
  option-a/index.html    # Title block
  option-b/index.html    # Datasheet
  option-c/index.html    # Instrument panel
  option-d/index.html    # SaaS polish
  README.md              # one paragraph per option, how to view
```

Constraints:

- Each prototype is one self-contained HTML file using the DESIGN.md `:root` tokens. Real Pyodide wiring is optional; a small inline JS stand-in for `calculate()` (a real formula, e.g. the composite-wall conduction math) is fine and keeps iteration fast. The winner gets wired to the real Pyodide/docstring pipeline during promotion.
- Use one real calculation with 3 to 5 inputs and 2 to 4 outputs across all four prototypes so the comparison is apples to apples. Recommendation: bolt preload / tightening torque, since it exercises a headline result, secondary results, a warning state, and a standards citation (VDI 2230).
- Keep the parts of the current template that already work: equation display with substituted values, expandable intermediate steps, the Background tab concept, tooltips fed by docstrings.
- Add `prototypes/` to `robots.txt` disallow (shared with the homepage prototypes plan if built together).
- Run the `avoid-ai-writing` skill on user-facing copy.

## Option A: Title block (engineering drawing)

The page is framed like a controlled document. A drawing-style title block sits at the top right or bottom of the tool: tool name, REV, published date, DRAWN BY (the tool author or "generated"), CHECKED BY (the human verifier, empty and visibly so for experimental tools), and a small revision-history table behind a disclosure. Section headings carry drawing-note numbering.

- Confidence mechanism: the visual language of documents that engineers already treat as authoritative. An empty CHECKED BY box is itself honest signaling for experimental tools.
- Recalc mode demonstrated: Calculate button.
- Risk: can slide into costume if overdone. Keep the title block small and real; no fake tolerance blocks or sheet numbers without meaning.

## Option B: Datasheet (standards document)

The tool reads like a component datasheet or a standard's worked example. Numbered sections (1 Scope, 2 Inputs, 3 Results, 4 Method, 5 References), formal tables for inputs and results with explicit symbol / value / unit columns, a stated assumptions-and-validity-range block, and a References section citing the actual standards and texts behind the math (VDI 2230, Shigley, ISO 1940) with edition and clause where known.

- Confidence mechanism: citation and rigor. Stating validity ranges ("valid for metric coarse threads M4 to M39") is a bigger trust signal than any styling.
- Recalc mode demonstrated: Calculate button.
- Risk: densest reading experience; needs careful typography so it stays scannable on mobile. The metadata block renders as a document header line (Version, Published, Status) rather than A's boxed title block.

## Option C: Instrument panel

Results styled like bench test equipment. Large mono-digit readouts on dark panels with unit labels, a headline readout visually dominant over secondary readouts, and per-output status indication (in-range, warning, out-of-validity) using the DESIGN.md semantic colors. Inputs are compact and knob-like: steppers, sliders where a range is natural, unit toggles.

- Confidence mechanism: precision feel and immediate feedback; the display treats numbers the way a Fluke meter does.
- Recalc mode demonstrated: live recompute (debounced ~150ms), with a subtle stale/percolating state while recomputing and an explicit invalid-input state (readout shows a dashed blank, not a wrong number).
- Risk: dark readout panels must not fight the light monochrome page; scope the dark treatment to the readout components only. Metadata renders as a small footer strip on the results card (v1.2, published 2026-08-01, verified).

## Option D: SaaS polish

Today's two-column structure executed at Linear/Stripe quality. No metaphor; confidence through evident craftsmanship. Sticky results column that follows scroll, skeleton loading states for the Pyodide boot (replacing the button-as-spinner), keyboard-friendly inputs (arrow-key increments, Enter to calculate), instant input validation with inline messages, tabs replaced by an on-page section rail, and quiet micro-interactions (150ms transitions, focus rings, copy-to-clipboard on results).

- Confidence mechanism: nothing feels broken or generic; the craft is the signal.
- Recalc mode demonstrated: Calculate button, but with the polished loading/validation states that both modes will inherit.
- Risk: least differentiated from every well-made web app. Its real role is defining the interaction-quality baseline the winning hybrid must meet. Metadata renders as a header meta-line with a popover changelog.

## Cross-cutting requirements (all four prototypes)

- Metadata block: version, last published date, verification status, and a revision history reachable in one click. Position varies per option as noted.
- "View source" provenance link pointing at the tool's Python module on GitHub.
- Both recalc modes speced in the README even though each prototype demonstrates one.
- Numeric outputs in `--font-mono`, always with units, sensible significant figures (not `toExponential(4)` for everything).
- A visible assumptions/limitations element, even if only Option B gives it a full section.
- Desktop and ~375px mobile layouts both work.
- Remove the dev-facing chart checklist from user view.

## What "done" looks like for the prototype phase

- Four prototypes rendering the same bolt-torque example from a local server, each with the metadata block populated from `meta-sample.json`.
- Screenshots of each at desktop and mobile widths in `prototypes/tool-ui/screenshots/`.
- README with one paragraph per option and its tradeoff.
- No changes to `tools/`, `catalog.json`, `pycalcs/`, or the SEO scripts.

## Evaluation criteria

1. Would a working engineer trust a number from this page enough to use it in a design review? What on the page earns that?
2. Is the headline answer findable in under 2 seconds after calculation?
3. Does it stay clean at real-tool complexity (bolt-torque has ~15 inputs across tabs, not the prototype's 5)?
4. Migration cost: how much per-tool work to move the 60+ existing tools onto it?

## Expected iteration

After review, revise this plan with the chosen hybrid (a likely shape: B's structure and references, A's title block as the metadata treatment, C's readout styling for the results panel, D's interaction states as baseline). The promotion-phase plan then covers: wiring to Pyodide and the docstring pipeline, the `update_tool_dates.py` script, `catalog.json` field additions, updating DESIGN.md and AGENTS.md, and a migration order for existing tools (verified tools first).
