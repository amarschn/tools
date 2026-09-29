# Thread specification workflow

Date: 2026-09-04
Status: Implemented and locally verified; not deployed

## Outcome

Make thread selection useful for a part drawing, with an explicit family, fit,
hand, and extent, plus a copyable callout and a detailed note. Restore the normal
tool layout and keep the reference material in Background.

## Plan

1. Add standard top-level tabs: Specify a thread, Geometry & load checks, and
   Background. Preserve existing calculation links and profile views.
2. Add a Python specification model with separate ISO metric, UNC, UNF, UNEF,
   NPT, NPTF, BSPP, BSPT, metal-forming, plastic-forming, and wood-screw workflows.
   Use sourced nominal catalogs. Do not apply machine-thread geometry or proof
   equations to pipe or product-specific screws.
3. Generate short drawing callouts and longer notes from the same validated
   state. Explain fit classes alongside the inputs. Keep thread depth distinct
   from drill depth; identify unfinished design decisions explicitly.
4. Put the callout beside a restrained engineering drawing. Retain the existing
   detailed profile for supported machine threads. For product-specific screws,
   use a procurement note and require a product reference, not invented geometry.
5. Add a Background guide for selection, fit versus strength, pipe sealing,
   self-forming screws, drawing requirements, and inspection, with primary sources.
6. Verify Python validation and callout fixtures, browser interactions, clipboard
   output, saved links, responsive layout, both themes, and existing calculations.

## Boundaries

This is a specification assistant, not a reproduction of Machinery's Handbook.
It does not calculate tolerance limits, pipe pressure ratings, validated pilot
holes for proprietary screws, or joint capacity outside the existing axial
screen. Specialized UNJ/UNR, ACME/Tr, buttress, and multi-start threads are called
out as outside current generated-callout coverage rather than silently treated
as general-purpose machine threads.

## Source checks

- ASME B1.1: Unified form, series, tolerance classes, and designation.
- Optimas manufacturer UNC/UNF/UNEF table: nominal size/pitch pairs only.
- Bossard metric tolerance guide: 6H/6g conventions and fit interpretation.
- Swagelok Thread and End Connection Identification Guide: NPT and ISO pipe families.
- Vermont Gage NPT/NPTF guides: separate gaging systems and Class 1/2 distinction.
- Bossard DIN 7500 and EJOT DELTA PT: product/material-dependent forming screws.

## Verification record

- Implemented all six steps, including 11 families and 147 nominal specification
  choices. Product-specific screw notes are explicitly marked as drafts.
- Existing fine-pitch catalog changes appeared during this work and were kept.
  The specification selector now consumes the same metric catalog; no changes
  to the concurrent axial-screen implementation or its tests were needed.
- Full Python suite: 1,260 passed, including eight additional invalid-depth
  traceback regression cases.
- Exhaustive nominal-pair/class generation test, invalid fit/side/extent tests,
  unit checks, and product-draft checks pass. Ruff checks and formatting pass.
- Real-Pyodide Chromium suite passes: every family, required depth, clipboard,
  detailed-note content, saved-link round trip, legacy identification link,
  escaped supplier text, manual update, settings, and Background references.
- Reviewed desktop light and phone dark/light screenshots. All primary tabs
  remain visible at 320 px, no horizontal page overflow, and dark result text
  resolves to rgb(249, 250, 251) on rgb(17, 24, 39).
- Refreshed catalog-based metadata and homepage fallback links using the SEO
  scripts. Homepage metadata check and git whitespace check pass.
- Applied avoid-ai-writing in edit/docs mode to the changed page and README:
  removed “fictitious” and “invented” framing, retained the concrete scope and
  review requirements, and re-read the edited copy.
- Earlier SVG rebuild and unrelated working-tree changes remain intact. No
  production deployment is part of this local iteration.

### Blind-hole validation follow-up

Reproduced the reported `could not convert string to float: ''` message in
Chromium. The depth validator raised a friendly error, but the browser selected
the first ValueError in its chained traceback, exposing the lower-level cause.
Expected numeric-input failures now suppress that cause, and the browser selects
the final validation exception. Browser regression checks cover empty depth on
selection, clearing an existing depth, zero/negative depth, valid-depth recovery,
external thread length, and returning to a through hole. Copy remains disabled
until the specification is valid. The real-Pyodide browser suite passes.
