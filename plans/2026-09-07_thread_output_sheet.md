# Compact thread output sheet
Date: 2026-09-07
Status: Inline revision implemented and verified locally; not committed or deployed

## Current scope

The user rejected modal exports after reviewing the first implementation.
Keep all thread workflows in normal document flow, including Settings and
confirmation before replacing an edited specification from Find.

- Keep one shared result sheet, with a visible callout, dimensions and complete note.
- Place the profile beside the dimensions when the output is wide enough.
  Put load-screen evidence beneath the profile to use that column's space.
- Retain direct equation expansion on calculated rows. Static rows have no chevron.
- Use two compact, shaded export headers with right-side chevrons. Only one
  section opens at a time. Group related fields in rows and place previews
  beside settings when space permits. Collapse cancels work and releases resources.
- Keep normal page interaction and scrolling available during exports.
  Changed inputs invalidate stale previews; download still uses previewed bytes.
- Put CSV in the output header. Leave references below the workspace.
- Preserve touch targets, field help, themes and lazy dependencies.
- Do not change the calculation equations or STEP geometry.

## Verification

- Default, load, Find, pipe and supplier-specific outputs; stale/error states.
- Visible dimensions, current substituted equations and full copy/CSV notes.
- Inline section exclusivity, keyboard operation, help and cancellation.
- Editing the part during an export and confirming/canceling candidate replacement.
- PDF and STEP preview/download regressions with real browser runtimes.
- Desktop and 320px light/dark screenshots; touch targets in a mobile context.
- Startup/cache/offline checks, asset keys, Python suite and metadata checks.

## Local results

The default output at 1440px viewport width is 769px tall, compared with 1021px
in the first sheet implementation: about 25% shorter. Dimensions and the full
note remain visible. The drawing keeps equal axial/radial scale.

The full Python suite passed (1,379 tests). Browser specification, inline sheet,
Find/export, PDF preview, CAD preview and performance checks passed, including
touch-target and collapse-during-job coverage. JavaScript syntax, targeted lint,
asset versions, SEO/homepage metadata and whitespace checks also passed.

Local readiness was 929 ms in a cold browser context, 537 ms warm, 498 ms warm
with a slow network, and 484 ms warm offline. No startup CAD/PDF requests or
observed long tasks. These are local timings, not internet-load guarantees.

The writing-edit pass shortened STEP field labels while keeping definitions
in their tooltips. Existing engineering reference prose was left unchanged.

## Earlier iteration

The first implementation removed the outer dimensions/calculation accordions
and moved exports to native dialogs. It passed local tests, but the user
explicitly rejected the modal interaction. This inline revision supersedes it.

Physical printer/CAD-app review and production release gates from the export
plan remain unchanged. This task does not commit or deploy the working tree.
