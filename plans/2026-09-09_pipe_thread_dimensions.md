# Pipe thread dimensions and honest no-match reporting
Date: 2026-09-09
Status: Implemented and verified locally; items 1 and 2 complete

Fixes audit items 1 and 2: pipe threads carry no diameter data, and Find
reports "no close supported match" when the real reason is that it had no
comparable data. Item 5 (metric catalog coverage) is discussed only where it
touches this work, because the coupling question turned out smaller than it
looked.

## What is broken today

`_records()` in `pycalcs/thread_models.py` sets `diameter_mm: None` for every
pipe row, and `find_threads` gates diameter comparison behind
`use_diameter = machine and side != "unsure" and diameter is not None`. Pipe
therefore matches on pitch alone. Measuring a 1/2 NPT male fitting at 0.83 in
across the crests, 14 TPI, tapered, returns six candidates:

    1/2 BSPT   1/2 NPT   1/2 NPTF   3/4 BSPT   3/4 NPT   3/4 NPTF

1/4 and 3/8 NPT share 18 TPI, and 1/2 and 3/4 share 14 TPI, so pitch alone can
never separate them. The tool cannot identify a pipe thread at all. Specify has
the same hole: the details table prints "Diameter at gage plane | Not included".

Separately, filtering Find to NPT and entering only a diameter returns zero
candidates and the status `no-close-supported-match`. That wording tells the
user their thread is not in the catalog. The truth is that the tool discarded
the only measurement they gave.

## The decoupling question

The concern was whether adding pipe dimensions forces the thread catalog apart
from `pycalcs/fasteners.py`. It does not, for two reasons.

First, pipe data is new data. `UNIFIED_PAIRS` and `PIPE_PAIRS` already live in
`thread_specifications.py` with no dependency on `fasteners.py`. The Unified and
pipe size lists are already independent. Only the metric list reads
`ISO_FASTENER_GEOMETRY`. This change adds a pipe table beside the pipe list that
is already there, so it introduces no new coupling and removes none.

Second, when metric coverage is addressed later, the coupling is smaller than it
appears. `_recalculate_fastener_geometry()` in `pycalcs/fasteners.py:840`
overwrites `nominal_diameter`, `pitch`, `stress_area`, `minor_diameter` and
`pitch_diameter` on every record at import, recomputing them from the
designation string. The only values the table actually owns are `head_diameter`
and `head_height`. So `ISO_FASTENER_GEOMETRY` is not a competing source of
thread geometry. It is a list of designations plus head dimensions. Decoupling
means pointing the catalog at a thread-series list instead of at that list of
designations. No numbers get duplicated, and `fasteners.py` does not change.

Recommendation: keep items 1 and 2 free of any decoupling, and treat the metric
series list as its own later change with its own review. Nothing in this plan
depends on that decision.

## Data model

New module `pycalcs/pipe_threads.py` holding the tables and the derivations,
with sources cited in the module docstring the way `thread_specifications.py`
does. Keeping it separate gives one file to audit against the standards and
keeps `thread_specifications.py` from growing another large table.

Store only what each standard publishes as its own anchor, and derive the rest
with the standard's form equations so the tool can show the substitution the way
metric rows already do.

NPT and NPTF, from ASME B1.20.1:

- `D`, outside diameter of the pipe
- `tpi`, threads per inch
- `E0`, pitch diameter at the small end of the external thread
- `L1`, normal hand-tight engagement
- `L2`, effective external thread length

Derived, with `P = 1 / tpi` and thread height `h = 0.8 P`:

    E(x)     = E0 + x / 16          pitch diameter at distance x from the small end
    major(x) = E(x) + 0.8 P
    minor(x) = E(x) - 0.8 P
    E1       = E0 + L1 / 16         pitch diameter at the gage plane

BSPP, from ISO 228-1: major, pitch and minor diameter in millimetres, parallel,
55 degree form with rounded crests and roots, `h = 0.640327 P`.

BSPT, from ISO 7-1: the same form, with the published diameters taken at the
gage plane and the 1:16 taper applied along the axis as above.

`PIPE_PAIRS` becomes derived from the new table so the size list and the
dimension table cannot drift apart.

## Matching model, the part most worth reviewing

A tapered thread has no single diameter. A caliper on a male NPT reads somewhere
between the small end and the last full thread, depending on where it sits. So a
tapered pipe record needs an interval, not a point:

    diameter_min = major at the small end       = E0 + 0.8 P
    diameter_max = major at the end of L2       = E0 + L2 / 16 + 0.8 P

Matching then becomes:

- machine threads: point comparison against the measurement window, unchanged
- parallel pipe (BSPP, and Rp internal): point comparison, same as machine
- tapered pipe: interval comparison, scoring the distance outside the interval,
  zero when the reading falls inside it

`pitch_only` stops being "every pipe row" and becomes a per-record fact, true
only where a family or plane genuinely has no diameter to compare.

Worked check on the 1/2 NPT case above, using values that still need source
confirmation. Band for 1/2 NPT external major diameter is 20.72 mm to 21.56 mm.
The 0.83 in reading is 21.08 mm, inside the band. The 3/4 NPT band starts at
26.03 mm, so 3/4 drops out. Expected result is three candidates instead of six:

    1/2 NPT   1/2 NPTF   1/2 BSPT

That is the honest answer. Those three genuinely overlap on diameter and pitch.
The result should then name the discriminator rather than implying a winner:
NPT and NPTF differ from BSPT by flank angle (60 versus 55 degrees), and NPT and
NPTF are separated only by crest and root truncation inspection.

## Code changes

1. `pycalcs/pipe_threads.py`, new. Tables, derivations, and a lookup returning
   diameters and lengths at a named plane.
2. `pycalcs/thread_specifications.py`. `PIPE_PAIRS` derives from the new table.
   The pipe branch of `build_thread_specification` replaces the "Not included"
   row with real rows: major, pitch and minor diameter at the gage plane, hand
   tight engagement `L1`, effective thread length `L2`, and pipe outside
   diameter. The existing note lines stay, including that nominal pipe size is
   not the measured outside diameter.
3. `pycalcs/thread_models.py`. `_records()` populates the diameter fields and
   the taper band for pipe rows. `find_threads` gains the interval comparison
   and per-record `pitch_only`. The blanket "Pipe candidates are PITCH ONLY"
   warning is replaced by a caveat about where along a tapered thread the
   measurement was taken.
4. Capabilities. `identify_external` and `identify_internal` become true for
   pipe families. `print_profile` and `step` stay false, see scope below.
5. Item 2. Separate "nothing could be compared with the observations you gave"
   from "rows were compared and none were close", so the summary can say which.
   Also stop printing the diameter search window in the warnings when no
   diameter was used in the comparison.
6. Copy. The Find summary strings in `thread-specification.js`, the
   standards-coverage table in `index.html` (the lines claiming "Find and print
   compare pitch only" and "No gage-plane diameters" both become false), and the
   README coverage and limits sections.

## Out of scope for this change

Deliberately excluded to keep the diff reviewable:

- To-scale pipe profile drawings and 1:1 print strips. The diameters make these
  possible, but `physical_profile()` is shaped for the 60 degree metric and
  Unified form, and BSP is 55 degrees with rounded crests. That is its own change.
- Pipe STEP export.
- Pipe sizes above 2 in, and NPSM/NPSF (audit items 3 and 4). The table is built
  so adding rows is the only work needed.
- Metric and Unified catalog coverage (item 5).
- Tap drill sizes (item 6).

## Verification

- `tests/test_pipe_threads.py`, new. Every NPT row must satisfy
  `E1 = E0 + L1 / 16` to within a rounding tolerance. This is a real internal
  consistency check from the taper definition, and it catches transcription
  typos in the values I am most likely to get wrong. Spot checks on published
  values for at least 1/8, 1/4, 1/2, 3/4 and 1.
- `tests/test_thread_models.py`. The 1/2 NPT case returns 1/2 NPT and 1/2 NPTF,
  and does not return 3/4. A diameter-only NPT search returns candidates rather
  than a false no-match. A BSPP search still compares as parallel.
- `tests/test_thread_specifications.py`. Pipe breakdowns carry diameters, and
  the "Not included" string is gone.
- `tests/browser/thread-find-exports.cjs`. A pipe identification run end to end.
- Full pytest suite and all seven browser suites, local and against the deploy.

## Sources needed before transcription

Dimensional values only get transcribed from something citable in the README,
matching how the existing entries are handled. ASME B1.20.1 and ISO 228-1 are
both paywalled, so the repo already cites Swagelok MS-13-77 and the Vermont Gage
NPT/NPTF guide for pipe. I will bring the proposed source list for approval
before entering any numbers, and any value without a source stays out rather
than being guessed. The illustrative numbers in this plan are recalled, not
sourced, and all of them are subject to that check.

## How the open questions were resolved

1. `L2` was sourced, so the full band is used. ASME B1.20.1 effective thread
   length is carried for NPT and NPTF, and ISO 7-1 useful thread length for R
   and Rc. The narrower fallback was not needed.
2. Internal comparison uses the minor diameter band, mirroring how internal
   machine threads compare against basic minor diameter.
3. The NPTF callout was left as it is. Changing it sits outside items 1 and 2
   and deserves its own decision.

## What the sources turned out to be

The AmesWeb ASME B1.20.1 chart supplied the NPT anchors, and all ten rows
satisfy `E1 = E0 + L1/16` exactly, which is an identity the table itself does
not encode. The AmesWeb ISO 228-1 chart supplied the BSPP major diameters, and
deriving pitch and minor diameters from them with `h = 0.640327 P` reproduces
the printed values; Engineers Edge and the Wikipedia British Standard Pipe table
agree independently. ISO 7-1 gauge and useful thread lengths came from the
Rastro BSP tables. Every one of these checks runs in `tests/test_pipe_threads.py`.

## Verified

- 1,408 Python tests pass, including 53 new pipe-dimension tests.
- All seven browser suites pass against a local server.
- The worked case behaves as predicted: a 0.83 in, 14 TPI, tapered reading
  returns 1/2 NPT, 1/2 NPTF and 1/2 BSPT rather than six rows, and the result
  names the flank angle and truncation inspection as the discriminators.

## Follow-on work this unblocked

Audit items 3 and 4 are now data entry against the same tables: pipe sizes above
2 in need one row each, and NPSM/NPSF need a table beside the existing ones.
To-scale pipe profiles and pipe STEP remain their own changes, because
`physical_profile()` is still shaped for the 60 degree form.
