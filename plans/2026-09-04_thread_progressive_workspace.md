# Progressive thread workspace

Date: 2026-09-04
Status: Implemented and verified locally; not deployed

## Requested layout

Three task tabs: Specify a thread, Design thread for load, Explore thread.
All three share one result panel: callout, close-up, then expandable dimensions,
calculation evidence, detailed note, and review items. Reference sections live
below the workspace, available from every task without changing tabs.

## Disclosure layers

- Specify defaults to three controls: family, size, and part feature.
- Load defaults to family, axial load, and verified minimum proof strength.
- Explore defaults to family and size; measured identification is expandable.
- Thread details reveal fit, handedness, extent, and load-search assumptions.
- Expert options reveal manufacturing method, material family/specification,
  coating, and inspection. Form tapping and external rolling are distinct.
- Reference theory and sources are collapsed below the task area.

## Implementation and checks

1. Extend the Python specification model with manufacturing/material metadata,
   nominal-only callouts, and a workflow wrapper around existing calculations.
2. Consolidate the UI around one form and result component. Preserve the authored
   SVG and equation ledger, removing the duplicate calculator layout.
3. Reuse the same measured/basic profile for machine threads in every task.
   Clearly label pipe and proprietary-product illustrations as schematic.
4. Preserve independent task state, legacy links, settings, and stale/invalid
   result protections. Expert settings must appear in copied notes.
5. Verify default visible control counts, disclosure keyboard behavior, every
   task, common result/profile synchronization, process/side compatibility,
   material and strength independence, clipboard/URL round trips, mobile, themes,
   and the blank blind-hole regression.

Manufacturing method does not change the standardized nominal profile or earn
an assumed strength/fatigue improvement. A material-family label cannot supply
a proof-strength value. Load design remains a stated axial-tension screen, not
a thread-stripping, fatigue, or pressure-connection design.

Sources for process guidance: Sandvik Coromant Threading Application Guide and
Gühring fluteless-tap guide. Existing thread geometry and catalog sources remain
unchanged. Apply the repository writing skill to the revised page and README.

## Verification

- Full Python suite: 1,314 passed. New cases cover every machine-thread
  specification size, shared result identity, nominal-only extents, process/side
  validation, material/geometry independence, measured matches, no passing size,
  and invalid load inputs.
- Real-Pyodide browser regression passed with no page or console errors.
  Verified three/two-control defaults, keyboard disclosure, independent task
  states, one persistent profile SVG, all 11 families, blank blind depth, expert
  notes, material-change proof reset, and invalid shared-link preservation.
- Clipboard callout/note/link round trips, legacy links, CSV geometry and load
  evidence, manual update/stale export protection, settings persistence, and
  light/dark mobile layouts (390 px and 320 px) passed.
- Inspected desktop, expert, and mobile screenshots. Guide and sources remain
  below the workspace in all tasks; advanced inputs and results start closed.
- JavaScript syntax, Ruff, and git whitespace checks passed. Discoverability
  scripts rerun; SEO injection made no additional changes. Homepage metadata
  must be refreshed again after the eventual release commit.
- Applied the repository writing skill in edit/docs mode: short visible labels,
  explicit limitations, and the longer guidance moved into expandable sections.

Local preview: http://127.0.0.1:8148/tools/thread-visualizer-sizer/.
Work remains on the existing task branch, alongside the user's uncommitted work.
No merge, push, or production deployment was performed.

## September 5 UI refinement

The user requested homepage styling, clearer task tabs, less empty space in the
result panel, and copy icons next to readable text. The task selector now has a
bordered frame and a filled active state. The tool follows the homepage's
palette, left-aligned title, canvas width, flat surfaces, and control shape.

Callout and note copying use overlapping-squares icons with accessible labels
and a temporary checkmark. The full note stays visible; the duplicate review
accordion is removed. Diagram padding is reduced without changing the thread
geometry, and the engaged view retains room for its dimension labels.

Verified locally: 1,316 Python tests passed, plus the real-Pyodide browser suite.
Clipboard text matches the visible callout and complete note; copy icons expose
accessible labels and success feedback. Homepage font/background/title/wordmark
comparisons, explicit tab styling, touch help, and desktop/mobile engaged-label
bounds passed. Inspected light and dark phone screenshots. No deployment.
