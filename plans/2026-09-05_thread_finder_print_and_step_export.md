# Thread identification, printable comparison sheets, and STEP export
Date: 2026-09-05
Status: Implemented locally; automated checks passed; physical review and release pending

## Decisions proposed

Keep three task tabs: **Specify a thread**, **Design thread for load**, and
**Find a thread**. Replace Explore rather than adding a fourth tab. Find gets
the subtitle "Identify a thread from measurements." It starts with an unknown
physical part, not a known family and designation. Browsing known sizes and
their profiles remains available in Specify, including its nominal-only extent.

Add two distinct exports:

- **Print comparison sheet:** a vector PDF for an ordinary paper printer,
  with actual-size pitch strips and physical scale checks.
- **Download STEP:** a representative CAD solid generated entirely in the
  browser. No STL, geometry server, uploads, or serverless functions.

Keep the homepage-aligned styling, explicit tab boundaries, input-left/result-
right workspace, visible copyable notes, and references below the workspace.
Every new input needs the existing visible, keyboard/touch-accessible help button.
The user approved execution after this plan was written. The implementation
record below distinguishes automated checks from the remaining physical review.

## Current implementation and gaps

`thread-specification.js` currently starts Explore with family and nominal size.
Identification is inside an accordion and requires another checkbox. The user
must choose metric or Unified before searching. `identify_standard_thread` in
`pycalcs/threads.py` always returns nearest entries from that selected catalog,
using relative diameter/pitch distance. It does not account for measurement
uncertainty, internal measurements, or taper.

`pycalcs/thread_specifications.py` has a larger specification catalog, including
UNEF and pipe designations. Machine-thread geometry comes from
`pycalcs/fasteners.py`. Pipe annotations include pitch, flank angle and taper,
but not gage-plane diameters or thread-length limits. Product-specific screws
have entered nominal dimensions, not validated supplier profiles.

The normalized SVG is an educational drawing, not an actual-size print master
or a solid-model definition. There is no STEP export or comparison PDF today.
Preserve the current local work and unrelated changes while implementing this
plan after approval. Earlier plans remain historical records.

## 1. Find a thread

### First screen

Show a measurement form with three primary groups:

1. **What are you measuring?** External screw/thread, internal hole/nut, or unsure.
2. **Measured diameter**, with a nearby mm/in selector and a small measurement
   diagram. The label and guidance follow the selected measurement type.
3. **Pitch**, optional, accepting mm per thread or threads per inch (TPI).
   Include "I don't know the pitch" and a visible Print comparison sheet action.

Do not require a thread-family choice. Search supported metric and inch
families together. Family, straight/tapered/unknown form, hand, measurement
uncertainty and exclusions belong under More measurements and filters.

Start with empty measurement fields and useful instructions, not invented
measurements. Offer an explicitly labeled example. Diameter alone returns a
broad shortlist and a request to measure pitch; missing pitch is not an error.
With no measurements, offer a common-pitch sheet and measurement guidance,
not a default "found" thread. Unit changes convert the physical measurement
rather than reinterpreting the same number in different units.

### Help someone obtain the measurements

- External: illustrate measuring across the crests, not the roots or head.
- Internal: identify the bore/minor-diameter measurement and explain limited
  caliper access. Never pass that value to an external-major-diameter matcher.
  Where the measurement basis is unsupported, offer pitch-only comparison and
  guidance to measure a known mating screw or use a suitable gage.
- Unknown pitch: offer direct pitch, TPI, or distance across several intervals.
  Illustrate counting spaces: eleven crests span ten intervals. Ask for span
  and interval count, not an ambiguous "number of threads."
- Possible taper: reveal two diameter readings, their axial separation, and
  the measurement locations. Unknown is different from zero taper. A taper
  observation narrows families; it does not establish a nominal pipe size.
- Explain that lead per revolution is not necessarily pitch for multi-start
  threads. Do not silently treat a lead measurement as single-start pitch.

New derived quantities belong in Python, with numbered equations, substituted
values and variable legends exposed in the measurement explanation:

- Equation (1): `P = S / n`. P: axial pitch; S: measured span in mm;
  n: positive integer count of pitch intervals.
- Equation (2): `TPI = 25.4 / P`. TPI: threads per inch; P: pitch in mm.
- Equation (3): `T = abs(d_b - d_a) / L`. T: diameter taper ratio;
  d_a and d_b: diameters at two specified planes; L: their positive axial
  separation, using the same length unit as the diameters.

Tapered/parallel form, diameter and pitch are useful identification observations.
Pipe identification tables are not inspection limits, and some NPT/ISO 7 sizes
are difficult to distinguish by simple measurements. Keep those limitations
visible in the results. [Swagelok identification guide, pp. 7–14](https://www.swagelok.com/downloads/webcatalogs/en/ms-13-77.pdf).

### Search and candidate results

Create a side-aware identification function using normalized records from the
specification catalog, reusing existing parsers and geometry equations. Do not
copy nominal size lists into a new JavaScript database or change load-screen
catalog coverage incidentally.

The first release searches all validated metric/UNC/UNF/UNEF specification
entries, including cross-system lookalikes. Internal searches must use the
correct diameter quantity and disclose that a basic diameter is not a measured
tolerance band. Add pipe diameter matching only after sourced identification
diameters and measurement-plane conventions are recorded and tested. Existing
pipe pitch data can support pitch-only shortlists and print strips earlier.
Product screws remain supplier-dependent; do not rank generic wood/plastic
screws as confirmed machine-thread matches.

Represent supported operations separately on each family/record:
specification, external/internal identification, pitch printing, true-scale
profile printing and STEP modeling. Missing geometry disables only the
unsupported operation and explains the missing data.

Return a shortlist rather than silently selecting a winner. Show three to five
rows initially, with more available and inseparable candidates grouped together.
Each row shows designation, expected diameter with its measurement basis,
pitch/TPI, measured differences, and the next useful measurement. Expand a row
to see its profile, sources and comparison details in the shared result panel.

Use explicit states: incomplete measurements, possible matches, ambiguous,
or no close supported match. Document and test the comparison windows before
shipping them. Measurement uncertainty, known dimensional variation and search
windows must remain distinct from standard acceptance limits. Missing pitch
must not be scored as zero error. A nearest entry outside the comparison
windows can be shown as a reference, never as a successful identification.
Do not convert ranking scores into confidence percentages.

The Find result is a candidate designation and an identification note containing
observations and unresolved checks. It must not acquire an unmeasured 6H/6g or
2A/2B suffix. Do not infer material, manufacturing method, strength, pressure
rating, handedness or fit class from diameter and pitch. NPT versus NPTF may
remain unresolved even when nominal size and pitch agree.

**Use this candidate** transfers an explicitly selected nominal size to Specify.
There, label fit/hand/extent defaults as design choices. Preserve Find's readings
and shortlist. Do not silently overwrite an existing edited specification.

### Preserve existing links and task state

- New links use a versioned Find state with measurement type, units, supplied
  observations, filters and selected candidate. Validate all restored values.
- Existing `section=explore` links with measured identification, and legacy
  `mode=identify` links, open Find with the same physical observations.
- Existing Explore links that only select a nominal size open Specify in
  nominal browsing mode, preserving size, view and relevant explicit settings.
- Switching tasks preserves independent inputs. Measurement changes invalidate
  old candidate selections and their print/export snapshots.

## 2. Printable thread comparison sheet

### Artifact and workflow

Generate a dedicated vector PDF locally, with US Letter and A4 options. Make
Print comparison sheet available before pitch is known and beside a shortlist.
Provide a downloadable PDF when direct printing is unavailable. Do not make
paper export depend on OpenCascade or a 3D viewer.

Default to the candidate pitches on a compact sheet. Also offer a common-pitch
sheet when there is no shortlist. Deduplicate identical pitches and list their
associated candidate families; one matching pitch is not one confirmed thread.
The common sheet should use the same supported pitch catalog and clearly state
its coverage, not imply that every historical thread is included.

Each sheet contains:

- A first-read instruction: print at Actual size / 100%, with fit/shrink disabled.
- Horizontal and vertical 100 mm scale checks, plus a labeled 1 in check.
  Repeat calibration marks and instructions on every page.
- Actual-size repeated pitch ticks/strips, a common starting line and numbered
  intervals. Several aligned intervals expose pitch differences better than
  trying to compare one tiny tooth.
- Candidate designation, pitch in mm and TPI, and the expected measured diameter
  with external/internal/reference-plane context. Diameter comparisons are
  shown only when their data basis is supported.
- True-scale basic profile strips where supported. Keep any enlarged
  explanatory detail in a separate box marked "Enlarged, not for comparison."
  Do not print today's arbitrary pipe/product tooth shapes as actual-size forms.
- A small measurement worksheet and a link back to the saved search, using
  the existing URL-state mechanism without a server-side link shortener.
  Allow observations and the return link to be omitted before sharing the PDF.
- A scope note: preliminary identification aid, not a thread gage or tolerance,
  sealing, pressure, or strength verification.

Instructions should describe placing the screw alongside a strip, aligning
one crest, then checking successive crest positions. The paper is not a
physical mating thread; parallax, the helical shape, wear, line width and printer
resolution limit the comparison. Internal threads may need a measurable mating
part or proper pitch gage. Never advise forcing an unknown thread into a part.

### Physical scale is an acceptance requirement

Use physical model coordinates, not CSS pixels or a screenshot of the responsive
SVG. A single conversion maps millimetres to PDF points: `points = mm * 72/25.4`.
Test that a 25.4 mm span is 72 PDF points and an n-interval strip is n times its
pitch, independently of viewport size, theme, density and display precision.

Lay out separate Letter/A4 pages with conservative printable margins and vector
black lines on white. If content does not fit, paginate or shorten the comparison
window while retaining its pitch. Never scale an entire page down to make it fit.
Check fonts/symbols, minimum line weights and clipping in the generated PDF.

PDF viewers and printer drivers can still resize a geometrically correct file.
Actual size avoids viewer scaling, while Fit changes it; the application cannot
guarantee physical output settings. Require the user to check both calibration
directions before comparing parts. If either check is wrong, fix the print
settings and reprint. Do not silently apply an unverified compensation factor.
[Adobe print-size guidance](https://helpx.adobe.com/acrobat/desktop/print-documents/set-up-and-print-pdfs/page-size.html).

Evaluate a pinned, locally hosted PDF library such as pdf-lib. It supports
browser PDF creation and vector drawing; using it does not require a PDF server.
Draw from shared primitives rather than assuming an arbitrary SVG-to-PDF
conversion preserves dimensions. [pdf-lib documentation](https://pdf-lib.js.org/).

## 3. Browser-only STEP export

### First supported models

Support validated ISO metric and Unified single-start nominal profiles first:

- An external threaded stud section without a head.
- An internal through-thread coupon with an explicitly shown surrounding-body
  diameter. This is a reference specimen, not an inferred part design.
- Right- and left-hand variants and a user-selected representative length.

Use the selected designation's pitch and diameters. Propose a length of 2d when
none is specified, visibly labeled as an export-only default, where d is nominal
major diameter. The implementation must distinguish model length from usable
full-thread length: clipped partial turns at ends are not full threads.
Entry, runout and body-envelope choices must be stated and tested.

Start with plain, explicitly described terminations. Blind-hole bottoms, drill
points, reliefs, heads and supplier lead-ins are subsequent work. A blind-hole
specification must not silently export a through hole: require selection of the
separately labeled reference coupon or explain that matching blind geometry is
not yet supported.

Label every artifact **Representative nominal geometry, not tolerance-controlled
manufacturing geometry**. The selected fit class may appear as an unresolved
drawing requirement, but must not be claimed as modeled until its dimensional
limits are implemented. A STEP solid is not a native parametric CAD feature tree.

Pipe STEP support follows only after diameter-at-reference-plane, thread-length,
root/crest and taper conventions are sourced. Do not use nominal pipe size as
outside diameter or extrude the current schematic. Proprietary forming/wood
screws require validated product geometry before STEP is enabled.

### Runtime and hosting

Use a pinned Replicad/OpenCascade.js build inside a dedicated Web Worker.
The STEP writer runs there too; Replicad exposes a browser Blob export with
explicit model/output units. [Replicad integration](https://replicad.xyz/docs/use-as-a-library/),
[STEP export API](https://replicad.xyz/docs/api/functions/exportSTEP/).

Host the worker, JavaScript and WASM assets with the site. Any bundling/custom
build is a development step; deployment remains ordinary static files. Use
relative asset URLs compatible with both the production root and a GitHub Pages
subpath. Verify MIME types, loading errors, cache versioning and deployment size.
No runtime Node process, pip installation, API keys or external CAD service.

Load the CAD assets only on an explicit Download STEP request. Cache on use,
not in the calculator's initial preload. Repeated exports can reuse the worker;
normal Specify, Find, SVG and print operations must work if CAD loading fails.
Check licensing, notices, redistribution requirements and reproducible build
instructions before adding binary assets.

Use a single-threaded WASM build initially. A background worker keeps work off
the UI thread without requiring a pthread-enabled kernel. Emscripten pthreads
depend on SharedArrayBuffer and COOP/COEP headers; do not add that hosting
requirement in the first version. [Emscripten documentation](https://emscripten.org/docs/porting/pthreads.html).

Snapshot the validated spec/model parameters with a job ID. Show loading,
building and preparing-download stages rather than fictitious percentage
progress. Provide Cancel by terminating the worker, then allow a clean retry.
Discard stale results when inputs change. Dispose kernel objects and Blob URLs,
test repeated exports, and bound length/turn count based on measured resource
use. An unsupported or failed solid must produce an explanation, not an empty
STEP file or a silent server fallback.

Keep the initial model/output unit millimetres with explicit STEP units;
inch designations are converted once at the model boundary. Filenames and
supported STEP product metadata should identify designation, hand, specimen,
length, representation status and model version. Keep the detailed note
available beside the export. Find requires an explicit candidate selection
before it can open a nominal STEP-export workflow.

### Modeling and performance proof before broad support

Prototype a metric external thread and internal coupon, then an inch thread.
Construct helical solids with kernel sweeps/booleans, not faceted pseudo-STEP.
Verify that the generating construction preserves the intended axial profile;
a profile swept normal to a helix must not inadvertently change its axial
flank angles or pitch. Compare sections against the existing 2D geometry.

Measure cold download/startup, warm generation, STEP size, available memory
metrics, cancellation and repeat-export behavior on desktop and a mobile device.
Initial usability targets, not measured promises: nominal warm desktop export
within 5 seconds, visible status immediately, and a bounded job timeout with
retry/cancel. Record the actual results and choose supported length/turn limits
before claiming coverage. If the targets fail, reduce supported complexity or
optimize the build; do not change the static-only requirement.

Reimport the files, check valid closed solids, units, solid count, handedness,
pitch, bounding dimensions and volume. Also open representative files in a CAD
application outside the exporter, preferably the maintainer's normal CAD system.
A file extension or valid STEP header alone is not sufficient verification.

## 4. Shared geometry, separate output layouts

Keep engineering quantities, unit conversions, nominal catalogs and profile
definitions in the dependency-free Python core. Add a versioned, JSON-safe
physical model contract carrying dimensions, axial profile segments, hand,
extent, reference planes, source provenance and representation limitations.
Unknown dimensions stay unknown. Existing machine SVG output must not regress
while normalized geometry is connected to this contract.

```text
Canonical catalog, measurements and physical profile (Python)
  ├─ Find: candidates, measured differences and missing evidence
  ├─ SVG: explanatory views with responsive annotation layouts
  ├─ PDF: actual-size physical coordinates and print annotations
  └─ CAD worker: representative solid and STEP serialization
```

Screen layout, print layout and CAD topology are different consumers. Share
physical geometry, not screen-space coordinates, SVG markup or line-width
choices. Engineering dimensions must not be recalculated independently in
three renderers.

Expected implementation touchpoints, subject to the first model-contract review:

- `pycalcs/threads.py` and `pycalcs/thread_specifications.py`: normalized catalog
  records, side-aware identification and task-state adaptation.
- A focused `pycalcs/thread_models.py` if needed for reusable physical profiles
  and export validation; reuse `fasteners.py` equations rather than duplicating.
- Tool-local Find UI, print renderer, CAD worker and export controls, wired into
  the existing page/CSS/help system. Keep PDF and CAD dependencies separate.
- Python tests, the existing real-Pyodide browser regression, dedicated PDF/STEP
  artifact tests, the tool README, and required release metadata.
- Tool-local references with source/edition/measurement-basis records. Promote
  assets to shared storage only if another tool actually consumes them.

## 5. Implementation order and completion gates

1. **Data and model contract:** inventory supported operations, record missing
   pipe/product data, normalize catalog access, and define measured versus
   nominal versus representative fields. Keep the existing load screen intact.
2. **Small feasibility checks:** generate/reimport one external and one internal
   STEP specimen entirely in-browser; generate a scale-check PDF. Record asset
   size, timing and actual print results before building the full export UI.
3. **Find workflow:** replace Explore, support unknown family and partial
   measurements, implement side-aware candidates and ambiguity states, and
   migrate links/task state. Retain nominal browsing in Specify.
4. **Comparison PDF:** deliver shortlist/common-pitch sheets, Letter/A4 layouts,
   physical calibration marks, safe pagination and printing guidance.
5. **STEP controls:** add validated lengths/specimens, job state, cancellation,
   lazy loading and artifact naming. Expand only across geometry test fixtures
   that pass. No mandatory 3D viewer in this scope.
6. **Integration and release:** verify shared geometry, documentation, exports,
   accessibility and the repository release checklist. Release the approved
   implementation once through the task branch after verification; this
   planning change does not itself merge or deploy the unfinished tool.

Required regression cases:

- Metric versus inch lookalikes, including 1.25 mm pitch versus 20 TPI (1.27 mm);
  unknown pitch; missing diameter; correct interval counting; unit round trips;
  measured uncertainty; out-of-catalog and non-finite/negative inputs.
- Internal minor versus external major diameter; uncertain taper readings;
  nominal pipe fraction versus measured OD; unresolved NPT/NPTF and near NPT/BSP
  pairs; unsupported supplier profiles. No inferred class or strength claims.
- Old Explore/identify links, independent task state, selected-candidate changes,
  visible copy text, invalid/stale export blocking, all help buttons, and 320px
  layouts in light/dark/system themes.
- PDF page boxes, physical point/mm conversion, equal X/Y scale, exact repeated
  pitch spacing, no clipping or fit-to-page shrink, legible monochrome output,
  and separate enlarged illustrations. Browser zoom must not alter PDF geometry.
- STEP small/large catalog sizes, coarse/fine pitch, both hands, external/internal
  specimens, unit conversion, section dimensions, end conditions, solid validity,
  interrupted loading, cancel/retry, repeated downloads and stale-job protection.
- Static-host smoke test with no CAD API requests, no CAD asset fetch during
  ordinary calculator/Find/PDF use, and working asset paths without a development
  server or special cross-origin-isolation headers.

Automation can verify PDF coordinates, not a physical printer. A maintainer
must print the sheets at actual size, measure both calibration directions, and
try known metric and inch specimens before calling the paper comparison
verified. Record paper size, viewer, printer/settings and observed error. Do
not claim a universal identification accuracy from one successful print.

Before releasing implementation, run the full Python and browser suites,
artifact checks and CAD import review. Follow `docs/RELEASE.md`, refresh
discoverability metadata if copy/catalog changes, and apply the repository's
`avoid-ai-writing` edit/docs check to changed user-facing page and README copy.
Do not add the human-verified tag based solely on automated tests.

## Scope exclusions

No STL, cloud CAD processing, arbitrary user CAD uploads, full CAD editor,
automatic recognition from photographs, guaranteed print metrology, tolerance
certification, pressure ratings or thread strength certification. A paper strip
or representative STEP model must not be presented as a manufacturing or
inspection gage. Pipe/proprietary geometry expansion remains gated by sourced
data, not by whether the renderer can draw a plausible shape.

## Implementation record

Updated: 2026-09-06

- Find replaces Explore. The shared Python catalog/model supports partial,
  side-aware cross-system comparisons, explicit uncertainty windows, span/TPI
  and taper equations, candidate selection and legacy-link migration.
- Letter/A4 PDF output uses physical vectors, deduplicated pitches, simplified
  validated profiles, per-page X/Y calibration and a privacy-controlled return
  link. It does not load the CAD dependency.
- STEP uses pinned Replicad 1.1.0 / OCCT 8.0.1 single-thread WASM assets in a
  lazy worker. External/internal and RH/LH fixtures export and reimport. An
  independent installed OCP 7.9.3.1 kernel checks closed solids, volume and 40
  axial/profile/hand sample points per fixture. No STL or server was added.
- An initial boolean produced a valid but unthreaded cylinder. A seam-offset
  construction and bounded fuzzy boolean resolved it; every export now also
  checks the analytical threaded volume. A 40-turn trial failed this check.
  The shipped cap is 20 turns, not the trial 40. Ordinary local generation
  measured about 1.0–4.1 s; the 20-turn fixture took 6.6 s after initialization.
- The existing UI regression, new Find/export browser checks, and ten STEP
  fixtures pass. The full Python suite passes 1,360 tests. Ruff, JavaScript
  syntax and whitespace checks pass. PDF tests inspect decoded vectors and
  verify both calibration directions on every common-sheet page. Letter and
  A4 previews were rendered and visually checked.
- Browser checks include a static path prefix without isolation headers, no
  CAD fetch during Find/PDF use, load-failure recovery, cancellation, stale
  jobs, edited-specification confirmation, unique/help-covered inputs and
  320px light/dark layouts. SEO tags were regenerated from the catalog;
  homepage metadata passes its current-commit check (refresh after release
  commits is still required).
- CAD assets total 23,655,312 raw bytes / 7,354,364 gzip bytes. A local-host
  three-job worker reuse sequence measured 63–71 ms for fresh kernel init
  after module loading, effectively zero for warm init, and 100–163 MiB of
  WASM linear memory. These exclude internet download and other browser RAM.
  Source revisions, license notices and asset reproduction are recorded in
  the tool-local vendor notice. The worker is recycled after three exports.
- A STEP Quick Look thumbnail attempt stalled and was terminated. It does not
  satisfy the manual CAD-app visual review. Physical printer and mobile-device
  performance checks cannot be claimed from the desktop browser tests.

Pending release gates: physical printer calibration on Letter/A4 with known
metric/inch specimens, maintainer CAD-app visual review, mobile-hardware timing,
and the repository production release procedure. No production merge/push has
been performed during this implementation. No human-verified tag was added.

### Cached-tab and startup regression (2026-09-06)

The earlier browser suites blocked service workers. A returning-browser test
reproduced the reported Find failure by caching the pre-Find accepted-tab list
under the unversioned controller URL. New HTML loaded that old controller and
clicking Find kept Specify selected with the measurement form hidden.

The same test exposed serialized startup waits: with network revalidation
delayed by three seconds, a warm load took about nine seconds despite cached
Python sources and interpreter assets. The CAD runtime was not requested.
Catalog initialization and tab updates were milliseconds, not the bottleneck.

Tool-owned assets and Python sources now share generated content-derived URL
keys, including the lazy PDF/CAD controllers. The build refreshes those keys;
a test fails if local edits leave them stale. Python downloads run in parallel
with interpreter initialization. Pinned Pyodide releases and versioned Python
sources use cache-first retrieval. The loader uses CORS so its response can be
stored and reused by the service worker.

Desktop checks measured 0.43–0.49 seconds for warm, delayed-network and offline
startup after the fix, with no calculation revalidation requests. A fresh run
took about 1.1 seconds on the test connection; this is not a cold mobile timing
guarantee. Find selects and highlights while incompatible unversioned code is
still cached. The UI and Find/export suites pass, as do all 1,363 Python tests,
Ruff, cache-key consistency, SEO checks and whitespace checks. Release gates
above are unchanged.

### Naming, standards and PDF preview (2026-09-06)

- Renamed the page and catalog entry to Thread Calculator & Identifier, with
  Metric & Inch Threads in the page title. The existing URL stays valid.
  Regenerated SEO descriptions and added search tags for the covered standards.
- Added linked ISO/ASME coverage notes below the workspace. Numerical tolerance
  limits and pipe gage-plane verification remain unimplemented. VDI 2230 is a
  related reference only, not a claim about the axial-load screen.
- Selected-size sheets keep up to 16 separately labeled sizes, including sizes
  with the same pitch. Each machine-thread row has a true-size diameter circle
  and nominal-major or basic-minor dimension. Common pitch strips remain a
  separate layout. Pipe rows explicitly omit diameter comparisons.
- PDF.js 6.3.289 and its worker load only on Preview comparison PDF. The canvas
  renders the generated vector PDF; download and native print reuse its bytes.
  Edits and panel closure discard the old document. Failed imports can retry.
- The PDF browser test checks download byte identity, selection, unknown basis,
  delayed-load cancellation, retries, pagination, mobile help and both themes.
  It independently checks decoded vectors across 172 pages spanning every
  supported nominal record, both sides, Letter and A4. No scaled diameters,
  clipped vectors or overlapping row bounds were found.
- All 1,363 Python tests and the specification, Find/export, preview and startup
  browser suites pass. Warm startup measured 0.46–0.50 seconds locally, including
  slow-network and offline runs. No PDF or CAD runtime loads at startup.
  Physical printer calibration and the release gates above remain pending.

### Reimported STEP viewer and finished lead-ins (2026-09-07)

- Added Preview 3D before Download STEP. The worker writes STEP, reimports it,
  checks validity and volume, and meshes that reimported solid for the viewer.
  Download reuses the same bytes. The STEP product name and persistent preview
  label identify thread, hand, side, overall length and end treatment.
- Added finished chamfers to both stud ends or coupon entries by default.
  Collapsed end details allow one end, custom finished angle/axial length, or
  square ends. Defaults are representative root-clearance choices, not ISO
  4753 table dimensions. Internal entry dimensions and external tip dimensions
  are checked, with at least one pitch of full-profile span required.
- The visible detailed note, clipboard and CSV share an export-only CAD note.
  It separates overall length from full-profile span and required usable
  engagement. Writing review clarified finished geometry versus rolling-blank
  preparation, internal entry versus tap lead, and reference-only ISO 4753
  coverage. Drawing requirements are not silently changed by export defaults.
- Pinned Three.js 0.180.0 supplies orbit/zoom/pan and optional edges. An axial
  stencil-capped section affects display only. Theme and keyboard support,
  graphics-loss fallback, stale/cancel protection and resource disposal are
  included. Rendering is on demand, not an idle animation loop. The 758,751-byte
  viewer and CAD kernel load only on Preview 3D, with no server or STL added.
- Fourteen STEP fixtures passed independent OCP 7.9.3.1 checks for one valid
  solid, volume and 40 profile/hand samples each. Chamfered fixtures add 32
  surface-neighbor samples per treated end, including one-ended and custom-angle
  cases. Analytical clipped-profile integration independently checks end volume.
- The new viewer browser test passes exact STEP-byte preservation under
  section/edges, embedded identification, clipboard/CSV note equality, keyboard
  controls, no idle redraws, graphics-loss download fallback, cancellation and
  320px light/dark views. Screenshots were visually reviewed. This does not
  replace a maintainer's review in their normal CAD application.
- All 1,379 Python tests pass, along with specification, Find/export, PDF
  preview, CAD preview/artifact and startup browser suites. Ruff, JS syntax,
  cache-key, SEO metadata and whitespace checks pass. Desktop startup measured
  0.87 seconds cold and 0.43–0.47 seconds warm/slow-network/offline, with no
  CAD or viewer runtime requests. Mobile-hardware timing remains unmeasured.
- Chamfered fixtures took roughly 1.2–9.5 seconds for construction and STEP
  round-trip checks after initialization; the longest was a 20-turn fine thread.
  The test sequence reached 199 MiB of WASM linear memory, excluding viewer and
  other browser memory. These are local desktop observations, not guarantees.

Physical print calibration, maintainer CAD-app review and production release
remain pending. No commit, production merge or push was performed for this update.
