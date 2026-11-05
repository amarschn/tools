# Tipping and Stability: make the analysis visible

Date: 2026-09-30
Status: Proposed next UI pass; preserve and release the current calculator and experiments

## Decision and scope

The next pass should put tipping and sliding results together at the top, keep
the essential inputs beside them, and show the supporting numbers without
opening an accordion. Keep study B's native SVG section and the fixed top-down
footprint. Reduce the space they occupy so the analysis fits around them.

This document records the follow-up work. The current task can close with the
existing calculator and this plan; the redesign remains unimplemented. Preserve
all eight [FBD studies](../tools/tipping-stability/prototypes/) and the
[JSXGraph interaction lab](../tools/tipping-stability/prototypes/jsxgraph-lab.html),
including their fixtures, source, and library assets.

## What is getting in the way

The current layout makes a tipping limit prominent, but gives sliding only a
short note near the diagrams. Its detailed result is inside "Explore results &
calculations", below a second footprint plot. Entering a friction coefficient
requires opening "Customize platform & loads" and then "Check sliding".

The two main diagrams are each 340 px tall on desktop. On a narrow screen they
stack at 290 px each, ahead of the inputs. Captions, diagram controls, a second
footprint, and nested results sections add more vertical distance. Desktop
inputs and the force key can also scroll independently of the page.

Useful engineering results already exist: edge distance, moment reserve,
normal reaction, friction demand, capacity, and reserve. Their presentation
should distinguish essential results from explanations of those results.

## Proposed default workspace

At desktop width, use a compact input column beside one analysis column. Put
both result summaries above the diagrams. Reduce the title area's padding and
keep the title, settings, and sharing controls compact. The analysis column
contains these regions in order:

| Region | Visible content | Interaction |
| --- | --- | --- |
| Tipping and sliding summaries | Two equally prominent checks for the current case | Click a value for its equation and substituted calculation |
| B section and footprint | Larger section with a smaller orientation/support locator; target one 260-300 px row | Select an edge or force; keep front and left fixed in the footprint |
| Results table | Current margin, moment reserve, normal force, tangential demand, friction capacity and reserve | Select a row for its derivation |
| Support-edge table | One row per support edge, with edge distance and moment reserve | Select a row to update the diagrams and force inspector |
| Analysis toolbar | Inspect forces, direction sweep, background, CSV/JSON exports | Open a focused view without expanding the whole page |

For a rectangular footprint, show all four edge rows by default. Custom polygons
can make this table taller; do not cap it with another vertical scroll area.
Always distinguish the governing edge from the edge selected for inspection.

### Tipping summary

Show the current tipping state, critical slope/acceleration/speed/force for the
selected case, current demand in the same units, and remaining headroom. Include
the governing edge and signed distance to it. Preserve the solver's explicit
states for an unstable starting condition, no finite tipping limit, and loss
of compressive contact. Do not turn these into an unqualified green check.

### Sliding summary

Show "Not evaluated: enter friction coefficient" when the coefficient is
blank. Keep that coefficient visible with the essential inputs. Do not assume
a material pair or silently insert a coefficient to produce a pass.

When evaluated, show the required tangential reaction, aggregate friction
capacity, remaining force reserve, and a clear within/exceeded state. A compact
demand-versus-capacity bar can help, provided both numeric values and units stay
visible. Handle zero capacity explicitly instead of displaying an infinite or
undefined percentage. Changing inputs must mark both summaries as out of date.

Keep the model limitation nearby: this is an aggregate restrained-contact
friction check. Individual tire loads, free rolling, brake capacity, and yaw
resistance are not established by it. Use "within modeled capacity" rather
than a general claim that the vehicle is safe.

Keep separate tipping and sliding states. A positive tipping result must not
conceal exceeded or unevaluated friction capacity.

### Inputs and mobile order

Keep the load case, essential geometry, current case demand, relevant slope and
direction, friction coefficient, and Calculate together. A parked-on-slope case
must expose its slope immediately. Show motion or force controls when their
case needs them.

Move component masses, custom contacts, and additional load tables into one
"Edit setup" view with a plain summary of the active customizations in the main
workspace. Avoid nesting another set of accordions inside it. Keep one page
scroll on desktop; remove the input card's independent vertical scroll.

On mobile, place the two compact summaries first, then the essential inputs and
Calculate. Follow with one diagram slot using a "Section / Footprint" switch,
then the results and edge tables. Both views retain the same selection. This
keeps both diagrams available without stacking them ahead of the controls.

### Explanations and detailed views

Remove the outer "Explore results & calculations" accordion and the duplicate
Plotly footprint. Keep only one footprint renderer in the main workspace.
Retain the direction sweep as an explicitly named view, with its existing
gravity-only scope visible.

Clicking a result opens a bounded detail panel beside the workspace, or a sheet
on mobile, with equation, variable definitions, substituted values, and source.
It should not scroll the page away from the result. Support Escape, a visible
close button, focus restoration, and keyboard operation. Add a sliding
derivation using the existing Python friction equation and returned values.

The force inspector follows the selected edge and force. Put full vectors and
per-load moment contributions there. Keep the summary and signed edge reserves
visible outside this inspector so the user can assess the case without it.

## Implementation order

1. Surface the existing sliding result and friction input. Put current demand,
   tipping limit, and margin beside it. Preserve all solver values and state
   handling. This gives the largest improvement before rearranging diagrams.
2. Replace the nested results layout with the workspace above. Remove duplicate
   footprint rendering, reduce diagram height, and establish the mobile order.
3. Move derivations and the force inspector into focused panels. Update copy,
   the README, keyboard behavior, and the existing browser regression together.

Start a new task branch from the released main revision when returning to this
work. Extend the current browser tests to check visibility, selection, focus,
and all existing URL/export behavior. New Python tests are needed only if the
solver changes.

## A separate solver enhancement

The current solver evaluates sliding at the entered operating point. Its limit
search finds tipping/contact limits. Those are different outputs: a friction
utilization at the current load cannot establish which failure happens first.

A later "first limit" comparison would need a sliding threshold search along
the same case parameter, with the same fixed inputs and contact assumptions as
the tipping search. Implement that in `pycalcs/stability.py`, with explicit
handling of missing friction, zero capacity, an already-exceeded starting
point, and loss of contact. Verify known slope, acceleration, turn, and force
cases before showing "sliding governs" or "tipping governs" as a swept result.
Keep that enhancement out of the initial layout pass.

## Acceptance checks for the next pass

- At 1440 by 900 with default settings, both check summaries, essential inputs,
  Calculate, and the diagram row fit in the first viewport. The first results
  table starts there. Expanded setup and long custom polygons may extend it.
- At 390 by 844, both summaries appear before a diagram. The essential form and
  Calculate precede the diagram slot; there are never two stacked diagrams.
- Sliding status, demand/capacity, tipping margin, and moment reserve require
  no disclosure click. Each derivation takes one click from its result.
- A case within the tipping limit but beyond friction capacity is unmistakable.
  Blank friction, zero friction, threshold, loss-of-contact, invalid, and stale
  states retain distinct text in both themes.
- No duplicate footprint or independently scrolling input panel remains.
  Default content has no horizontal overflow at 390 px; wide custom data tables
  may scroll horizontally within their labeled region.
- Existing force-attachment and left/right orientation tests pass. Clicking a
  support edge, an edge-table row, or a force keeps the views synchronized.
- Keyboard selection, detail-panel focus, light/dark/system themes, precision,
  loading, URL restoration, exports, and every prototype link still work.

## Current-task release handoff

Release the existing calculator and this plan through the normal single merge
and single production push. The redesign items above remain open in the tool's
roadmap. Complete the release checks in [RELEASE.md](../docs/RELEASE.md) and
record any external prerequisite that prevents the merge.

Preflight on 2026-09-30:

- `python3.13 -m pytest -q`: 1,639 tests and 2,611 subtests pass.
- Calculator browser regression: 62 diagram views plus real Pyodide,
  all load modes, four slope directions, themes, mobile, keyboard operation,
  sharing, exports, and invalid-input recovery pass. Screenshots inspected.
- Prototype browser regression: all eight studies, 62 case/scale combinations,
  and the live JSXGraph lab pass, including dragging and Python comparisons.
- `python3 tools/tipping-stability/prototypes/generate_cases.py --check`: all
  eight fixtures match. Python 3.13's serialization differs only in 62 floating
  values, by at most 1.14e-13; there are no nonnumeric differences. Keep the
  saved fixtures and use their original Python 3.9 generator for the exact
  text check.
- Local and remote main both point to `1087ba0`, which is also the published
  Netlify main revision. The latest public deploy list shows no active deploy.
- The production build and generated homepage metadata check pass. Sitemap and
  SEO scripts ran, documentation links resolve, and the working tree was clean
  after the handoff commit was pushed.
- The user confirmed on 2026-09-30 that the Netlify project is active and has
  at least 15 deployment credits available. This satisfies the account check
  required before merging. Netlify's
  [current rate](https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/how-credits-work/#credit-usage-for-production-deploys)
  is 15 credits per successful production deployment on credit-based plans.
