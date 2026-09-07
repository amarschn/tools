# Thread Calculator & Identifier

## Purpose

Choose and specify a thread for a part drawing, then inspect its geometry or
run a preliminary axial-load check when needed:

- Build a short drawing callout and a detailed note for metric, Unified, or pipe threads.
- Prepare product-based procurement notes for metal-forming, plastic-forming, and wood screws.
- Inspect the basic 60° geometry of an ISO metric or Unified thread.
- Find possible nominal threads from external or internal measurements, across metric and inch families.
- Preview actual-size thread comparisons before downloading the PDF, or inspect and download a representative STEP solid, entirely in the browser.
- Screen the smallest included thread whose tensile-stress area meets a direct axial proof-load requirement.

The default **Specify a thread** tab opens on `M10 x 1.5-6H THRU`, with just
family, nominal size, and feature visible. **Design thread for load** and
**Find a thread** use the same result panel: callout or candidate, thread close-up, and the
full detailed note. Dimensions stay visible; each calculated row opens its
equation and substituted values. The family
guide and references sit below the workspace, available from every task.

## Requirements

- Use the standard input-left/output-right layout, three task tabs, and references below them.
- Match the homepage's palette, typography, flat surfaces, and compact controls. Give task tabs a bordered group and a filled active state.
- Keep three controls in Specify and Load. Find starts with measurement type, diameter/units and optional pitch/units, without a family filter.
- Collapse fit/hand, expert manufacturing/material choices, derivations, and theory by default.
- Show dimensions once in compact rows. Use a right-side chevron for expandable rows and none for static labels.
- Use compact inline sections for PDF/CAD settings and previews. Keep the rest of the tool usable while either is open; do not use modals.
- Put a visible help button beside every input label, including expert and product details. Support hover, keyboard focus, and touch.
- Keep fit classes compatible with the thread family and internal/external side.
- Keep the short callout and detailed note derived from the same validated state.
- Keep both copyable texts visible, with an overlapping-squares copy button next to each. Show a checkmark and announce successful copying.
- Require usable full-thread depth for blind holes and length for dimensioned external threads. Allow an explicitly undecided extent for nominal selection.
- Keep drill depth separate; do not infer material, strength grade, pressure rating, or pilot holes.
- Keep the thread profile visible with the geometry result.
- Support external, internal, and engaged profile views.
- Show major diameter, pitch or TPI, pitch diameter, internal minor diameter, tensile-stress area, and lead angle.
- Provide numbered equations, substituted values, variable definitions, and sources in the calculation ledger.
- Support light, dark, and system themes, display density, precision, and auto-update settings.
- Preserve the active section and its relevant inputs in copied links, including legacy calculation links.
- Export the current calculation as CSV and disable result exports while inputs are stale or invalid.
- Show a loading overlay until Pyodide and the Python modules are ready.

## Tasks

### Specify a thread

Select a family, nominal size, and feature on the part. A blind hole or
dimensioned external thread reveals its required usable depth/length input.
Open **Thread details** for fit class, hand, and pipe-connection details.
Defaults are stated in the summary and callout, not buried in an unseen form.

The primary result is a plain-text callout beside a conventional symbolic end
view. Its copy icon copies the displayed callout. The full detailed note is
visible below the thread close-up, with its own copy icon. Review items stay
inside that note rather than repeating in a separate panel. The end view is not
a tolerance drawing. A close-up appears below it for every task. Machine-thread
profiles use the shared geometry equations; pipe and product profiles are
explicitly illustrative, not manufacturing geometry.

The result sheet starts with the callout, with CSV in its header. On wide
screens the profile sits beside the dimensions; narrower outputs stack them.
Load screening evidence sits below the profile. The complete note remains
visible. Calculated rows show their values even when closed; one
click opens the equation, substitution, variable definitions and source. Only
one derivation opens at a time. Static dimensions have no chevron. Load checks
and their limitations appear with the relevant results, including a no-size result.

**3D & STEP** and **Print comparison** are shaded inline headers below the
results. Each has a right-side chevron; only one export section opens at a time.
Related fields share rows, and settings sit beside a generated preview when
space allows. Collapsing the section cancels pending work and releases preview
resources. You can still change the thread, switch tasks or copy its note.
Changes invalidate stale previews before download. Opening the section does not
load the PDF or CAD runtime. Escape dismisses field help, not the section.

Tool settings also expand in normal page flow, without an overlay or focus trap.
Replacing an edited specification from Find uses inline confirmation with
Replace specification and Keep current buttons. References stay below the workspace.

Pipe diagrams pair an overall tapered/parallel view with a pitch-and-angle
close-up. The annotations include TPI, pitch in inches and millimetres, and the
included flank angle. NPT/NPTF and R/Rc show the 1:16 diameter taper and its
1.790° half-angle to the axis. G and Rp are parallel. ØA and ØB mark diameters
at two planes separated by L, not numerical gage diameters. The catalog does
not yet contain gage-plane diameters or thread-length limits. Both views are
schematic; crest/root details and tolerances are omitted.

Metal-forming, plastic-forming, and wood-screw families instead request an exact
supplier product, screw diameter/length and units, head/drive, and substrate.
Their output stays a procurement draft, with no fabricated generic tapped-hole
designation or calculated load rating.
The size-envelope diagram labels the entered diameter and length in the chosen
units. Unentered dimensions read "not specified." The close-up marks pitch,
flank angle and pilot hole as needing supplier data; it does not assume a
universal forming-screw profile. Head, tip and lobular geometry are not modeled.

### Find a thread

Start with an unknown physical part. Choose external, internal or unsure, then
enter any diameter and pitch readings you have. Units convert the entered
physical measurements. The form starts empty; Try an example enters a labeled
M8-sized example. For known nominal-size browsing, use Specify with an undecided
external extent.

Find searches every metric, UNC, UNF and UNEF specification entry together.
External measurements compare to nominal major diameter; internal bore readings
compare to basic minor diameter. Unknown measurement basis excludes diameter
from ranking. Missing pitch leaves a broad shortlist, not a zero pitch error.
Pipe candidates are pitch-only references because diameter-at-measurement-plane
data are not implemented. NPT and NPTF can remain indistinguishable.

More measurements and filters contains span/interval pitch measurement, form,
hand, optional two-plane taper readings and measurement uncertainty. Eleven
crests span ten intervals. Lead equals pitch only for a single-start thread.
An observed hand is recorded, never inferred from diameter or pitch.

The default diameter comparison window is entered uncertainty (0.05 mm if
blank) plus a separate 0.20 mm external or 0.35 mm internal comparison allowance.
Pitch uses an absolute 0.03 mm window unless changed. These are search heuristics,
not ISO/ASME acceptance limits or confidence percentages. Candidates outside
either supplied window are excluded. Unsupported sizes can return no close match.

Select a row to see its nominal profile and identification note, without a fit
class. Use this candidate opens Specify; fit, hand and extent there are design
choices. Replacing an edited specification requires confirmation. Find retains
its own readings. Versioned links restore measurements; old measured Explore
links open Find and nominal Explore links open Specify.

### Comparison PDFs

The Print comparison section produces a local vector PDF for Letter or A4. **Selected
sizes** starts with up to four current candidates, each on its own labeled row.
Check or uncheck sizes and expand **Add other sizes** to search the catalog,
up to 16 sizes per document. Sizes with the same pitch remain separate. Each
machine-thread row includes its designation, pitch, diameter in mm and inches,
and an actual-size diameter circle. External comparisons use nominal major
diameter; internal comparisons use basic minor diameter, not tolerance limits.
An unsure measurement basis requires an explicit choice for the sheet.

**Common pitch strips** groups sizes by pitch instead, without diameter circles.
Use it for a general reference sheet with no measurements. Both layouts include numbered
pitch intervals, simplified actual-size axial profiles where supported, a
worksheet, horizontal and vertical 100 mm checks and a 1 inch check on every
page. Pipe rows have pitch ticks only and explicitly omit diameter comparisons.
No arbitrary schematic is printed as
a physical thread form.

**Preview comparison PDF** renders the generated PDF itself, with previous/next controls
and a list of sizes on the current page. The preview fits the screen; it is not
an on-screen size gage. Download and Open PDF to print reuse those exact bytes.
Changing measurements, selections, paper or options discards the old preview
and disables download until a new preview is ready. Closing it releases the
renderer and document URL.

Print at Actual size / 100%, with Fit and Shrink disabled. Measure both 100 mm
checks before comparing. Fix print settings and reprint if either check is
wrong. Align one crest beside a strip and compare several successive crests.
Wear, parallax, line width and printer resolution limit this aid. It is not a
thread gage; never force an unknown part into another thread.

The optional readings and clickable return link are off by default. PDF points
are computed directly from millimetres (`72 / 25.4`), not screen pixels. Separate
page layouts paginate without resizing geometry. Large diameters get taller
rows. Print does not load CAD code. The pinned PDF.js 6.3.289 renderer, its worker
and pdf-lib load only after Preview comparison PDF, never at tool startup. PDF.js renders
to canvas for viewing; the downloaded and printed PDF retains vector geometry.

### Representative STEP geometry

The 3D & STEP section supports metric/UNC/UNF/UNEF external stud sections and internal
through-thread reference coupons, in either hand. Length and coupon body diameter
are explicit export choices in mm. Blank length suggests 2d and blank coupon
diameter 1.8d, where d is nominal thread diameter. A fine-thread default exceeding
the 20-turn cap requires a shorter entered specimen. Length must be at least
one pitch and no more than 250 mm, with at least one pitch remaining between
chamfers. Blind specifications require an explicit
choice to export a separate through coupon; blind bottoms are not modeled.

The solids have helical surfaces and finished lead-in chamfers at both ends by
default. **End geometry** offers start only, end only, a custom finished angle
and axial chamfer length, or square ends for reference. External chamfers taper
the stud; internal chamfers open the coupon's bore. The suggested 45° angle
and end radius 0.05 pitch beyond the root are representative choices, not
standard table dimensions. Angles are measured from the thread axis.

Opening the CAD options appends a clearly labeled, export-only section to the
visible detailed note. It records the specimen, overall length, end dimensions,
and remaining full-profile envelope span. Copy and CSV include that same text.
The full-profile span excludes the chamfers but is not a guaranteed usable
engagement length: partial turns remain at its boundaries. These export choices
do not change the part drawing's full-thread-length requirement.

For rolled threads, the finished chamfer is not a rolling-blank instruction;
material displacement and tooling affect the blank preparation. ISO 4753 is a
reference for metric external fastener ends only. No end-type compliance is
claimed. Internal notes distinguish the finished entry chamfer from a tap's
cutting lead. Pilot/dog points and rolling-process simulation are not included.

The underlying axial profile is shared with the screen/PDF, with no tolerance
allowance, rounded root, coating or runout. The fit class is a drawing
requirement, not modeled limits. The output is representative nominal geometry,
not manufacturing geometry or a native parametric feature tree. Pipe and
supplier-specific screw STEP exports remain unavailable pending validated data.

**Preview 3D** generates the STEP, reimports it, and meshes the reimported solid
for display. **Download STEP** saves those same checked bytes. Orbit, zoom, pan,
optional edges and an axial section help inspect it; the section changes only
the display, never the downloaded solid. A persistent label identifies nominal
thread, hand, side, length and end treatment. That identification is also embedded
as the STEP product/body name, not just in the download filename.

Replicad 1.1.0 and its single-thread OCCT 8.0.1 WASM kernel run in a dedicated
worker, loaded only on Preview 3D. Three.js 0.180.0 also loads only then and
renders on interaction, without an idle animation loop. The viewer needs WebGL 2;
if graphics initialization fails or the context is lost, the checked STEP can
still be downloaded. Keyboard controls and both themes are supported. Closing
the preview disposes its graphics resources. All assets are same-origin static files.
There is no STL, upload, CAD API, runtime Node process or cross-origin-isolation
header requirement. Cancel terminates the worker. Changed inputs discard the
job; a 90-second timeout allows retry. Each successful export checks kernel
validity and the expected threaded volume, including analytical chamfer clipping,
then checks STEP round-trip validity and volume before displaying it.
The worker is recycled after three jobs to bound retained kernel memory.

Dependencies, pinned source revisions, license texts and reproduction commands
are documented in [vendor/NOTICE.md](vendor/NOTICE.md).
The CAD runtime is 23,655,312 bytes before compression (7,354,364 bytes with
gzip in the local asset check); the WASM file accounts for 22,980,267 bytes.
The viewer adds 758,751 JavaScript bytes before compression. Actual transfer
size depends on the static host's compression and cache. Neither runtime is
requested during normal calculation, Find, or PDF use.

### Design thread for load

Choose metric, UNC, or UNF; enter direct tensile service load per fastener and
a verified minimum proof strength valid across all candidate sizes. The
required proof margin defaults to 1.5. Change it and metric pitch-series
selection in **Thread details**. The result includes a candidate callout and
the same close-up as the other tasks, with axial-screen limits visible.

The tool selects the smallest passing size in its included catalog. It does not claim that no standardized size exists when the catalog limit is reached.

### Expert options

Choose turned, cut-tapped, form-tapped, rolled, milled, or ground threads where
compatible with the internal/external feature. Product-specific screws instead
allow a supplier-defined process. Add a material family and exact alloy,
condition or hardware grade, finish, and inspection requirement.

Each field has a `?` button beside its label. Hover or focus it to read the
explanation; click or tap to keep it open. Escape, another tap, or a click
outside closes it. Manufacturing and fit help follows the selected method or
family. The help explains what to enter, how it affects the detailed note, and
which checks the tool does not perform.

These choices become drawing-note requirements. They do not alter the standard
basic profile, set proof strength, or assign a strength bonus to formed threads.
Changing material in Load clears the proof-strength input so it must be
reverified. Form tapping displaces a ductile material; its pilot-hole guidance
must come from the tap supplier and actual material, not a cut-tap drill table.

## Calculation core

`pycalcs.thread_specifications` owns specification family metadata, compatible
classes, nominal specification lists, validation, callouts, and notes. Its
`analyze_thread_workflow` adapter joins those outputs to the existing geometry,
identification, and load-screen functions without duplicating their equations.
`thread-specification.js` handles controls, safe text rendering, clipboard,
section tabs, and URL restoration. `thread-specification.css` uses the tool's
existing theme tokens. Specification logic has no dependency on browser state.
`thread-help.js` turns the fields' authored help and live guidance into visible,
screen-reader-associated tooltips without maintaining a second explanation
catalog. Tooltips stay inside the viewport and close when their section collapses.
`thread-family-diagram.js` draws pipe/product schematics from the validated
specification's `diagram` payload. Dimension lines and arrowheads share their
endpoints. The overall and close-up views stack at narrow output widths.

`pycalcs.thread_models` owns the millimetre axial-profile contract, side-aware
Find comparisons and STEP validation. `thread-finder.js` owns measurement state;
`thread-print-ui.js` manages the shortlist, preview lifecycle and downloads;
`thread-print.js` lays out physical PDF vectors; `thread-pdf-preview.js` renders
those bytes with PDF.js. `thread-cad-worker.js` constructs solids, writes and
reimports STEP, and meshes that solid. `thread-cad-viewer.js` displays this mesh.
`thread-exports.js` provides export context, inline section lifecycle handling and CAD job snapshots.
The SVG maps the physical profile into its explanatory layout without defining
a second tooth shape.

`pycalcs.fasteners.calculate_basic_thread_geometry` is the source for shared 60° thread geometry. The existing bolt-joint calculator and this tool now consume the same pitch-diameter and tensile-area values. `pycalcs.threads` adds catalog parsing, nearest-size identification, axial size screening, and the stable browser-facing `analyze_thread` function.

The principal equations are:

1. Fundamental triangle height: `H = √3 P / 2`
2. Basic pitch diameter: `d₂ = d - 3H / 4`
3. Basic internal minor diameter: `D₁ = D - 5H / 4`
4. Metric external root or Unified schematic profile-minor reference
5. Tensile-stress area:
   - ISO metric: `Aₛ = π(d - 0.938194P)² / 4`
   - Unified: `Aₛ = π(d - 0.9743P)² / 4`
6. Single-start lead angle: `λ = tan⁻¹(P / πd₂)`

`d`: nominal major diameter; `D`: internal nominal major diameter; `P`: pitch;
`H`: fundamental triangle height; `d₂`: basic pitch diameter; `D₁`: basic
internal minor diameter; `Aₛ`: tensile-stress area; `λ`: single-start lead angle.

Find filters candidates by the comparison windows described above, then sorts
diameter-backed rows before pitch-only rows. Within each group, the sum of
absolute measured differences divided by their search windows orders the rows.
This is a display order, not a confidence or acceptance rating. Measurement
equations and substitutions appear in Measurement method and limits.

Load sizing uses:

`F_d = n_d F`, `Aₛ,req = F_d / S_p`, and `F_p = S_p Aₛ`

`F`: service axial load; `n_d`: required proof margin; `F_d`: factored demand;
`S_p`: verified minimum proof strength; `Aₛ,req`: required tensile area;
`F_p`: proof capacity.

## Included catalog

The specification catalog contains 147 nominal choices:

- ISO metric: the 35 coarse/fine entries from the calculation catalog, M2 through M24.
- UNC: 25 choices from #1-64 through 2-4.5.
- UNF: 24 choices from #0-80 through 1 1/2-12.
- UNEF: 25 choices from #12-32 through 1 11/16-18.
- NPT and NPTF: 10 nominal pipe sizes each, 1/16 through 2.
- BSPP (G) and ISO 7 (R/Rc/Rp): 9 nominal pipe sizes each, 1/8 through 2.

Three product-based workflows use supplier dimensions: metal-forming,
plastic-forming, and wood screws.

The load screen uses 35 metric and 30 Unified entries. These start
with `ISO_FASTENER_GEOMETRY` and `UTS_FASTENER_GEOMETRY` in `pycalcs.fasteners`,
plus the fine-pitch counterparts maintained in `pycalcs.threads`. The specification
builder reads that metric catalog directly; its larger Unified and pipe lists
contain nominal pairs only. No hardware head dimensions or tolerance limits
are inferred. All lists are working subsets, not complete standards tables.

Basic geometry is available for every metric/Unified specification choice,
including UNEF. Find uses that full specification catalog; load selection uses
the smaller calculation catalog described above. Pipe and product families have no load
selection or calculated manufacturing profile.

UNJ/UNR, ACME/Tr, buttress, Whitworth/BSF, NPS, thread-cutting/tapping-screw
standards, and multi-start callouts are outside the builder's current scope.
Numerical tolerance limits, gage dimensions, tap drills, stripping capacity,
and pipe-port details are not calculated.

## Load-screen scope

The size screen compares factored direct axial demand with proof strength times tensile-stress area. It omits preload, joint stiffness, external-load sharing, separation, fatigue, shear, thread stripping, engagement length, temperature, and installation scatter. Use the Bolt Torque Calculator for a preloaded-joint analysis.

## References

The page's [standards and coverage table](index.html#standards-coverage) links
ISO 68-1, 724, 261 and 965-1; ASME B1.1, B1.20.1 and B1.20.3; ISO 7-1 and
228-1; and VDI 2230 Part 1. It distinguishes implemented basic dimensions and
designation guidance from reference-only material. No standards-conformance
claim, numeric tolerance limits, pipe gage-plane verification or VDI 2230 joint
calculation is implied. Standards stay in the reference section, not appended
to the tool name as a certification claim.

- [ISO 68-1:2023](https://www.iso.org/standard/85107.html), ISO general purpose screw threads, basic and design profiles for metric threads.
- [ISO 724:2023](https://www.iso.org/standard/85104.html), ISO metric thread basic dimensions.
- [ISO 4753:2011](https://www.iso.org/standard/55928.html), ends of parts with external ISO metric screw threads. Reference only, not a claim that the suggested CAD chamfer matches a standardized end type.
- [CJWinter cylindrical thread-rolling dies](https://www.cjwinter.com/thread-rolling/cylindrical-machine-dies/), blank chamfer preparation and how rolling changes the finished angle.
- [ASME B1.1](https://www.asme.org/codes-standards/find-codes-standards/b1-1-unified-inch-screw-threads-un-unr-thread-form), Unified inch thread form and designation.
- [Optimas UNC, UNF and UNEF table](https://optimas.com/en_gb/technical-resources/unc-and-unf-thread/), nominal size/pitch pairs only.
- [Bossard metric tolerances](https://www.bossard.com/ch-en/-/media/bossard-group/website/documents/technical-resources/en/f-079-en.pdf), ISO 965 fit conventions.
- [Swagelok Thread and End Connection Identification Guide](https://www.swagelok.com/downloads/webcatalogs/en/ms-13-77.pdf), pipe families and nominal sizes.
- [Vermont Gage NPT/NPTF guide](https://vermontgage.com/assets/ea696d90d9/NPT-NPTF-2019.pdf), pipe-thread inspection classes.
- [Bossard DIN 7500](https://www.bossard.com/no-en/product-solutions/product-applications/din-7500/), forming screws in metal.
- [EJOT PT and DELTA PT](https://www.ejot.com/PT-History), plastic-fastening product families.
- [Sandvik Coromant threading guide](https://cdn.sandvik.coromant.com/files/sitecollectiondocuments/downloads/global/technical%20guides/en-gb/c-2920-031.pdf), thread-manufacturing processes.
- [Gühring fluteless taps](https://guhring.com/media/catalogs/044mlrkbbek.pdf), forming-tap process and pilot-hole requirements.
- [Simpson Strong-Tie technical inquiries](https://seblog.strongtie.com/2024/01/common-technical-engineering-inquiries-part-iii-fasteners/), wood-screw application requirements.
- [NASA fastener training material](https://ntrs.nasa.gov/citations/20110016427), tensile-stress area equations.
- [NIST Handbook 28, Part VI](https://nvlpubs.nist.gov/nistpubs/hb/1970/hb28-scan6.pdf), Unified thread stress-area and strength formulas.

## Startup and cached updates

The page fetches its four Python sources in parallel while Pyodide initializes.
The service worker reuses the pinned Pyodide release and versioned Python files
without waiting for network revalidation. A first visit still downloads the
interpreter; PDF and CAD runtimes load only when requested.

The HTML requests tool scripts, stylesheet, Python sources and lazy export
controllers with one content-derived cache key. This prevents new tab markup
from running with an old cached controller. After editing these files, run
`python3 scripts/version_thread_assets.py` before local browser testing. The site
build runs it too; `--check` and the Python tests catch stale generated keys.

`node tests/browser/thread-performance.cjs` checks cold and warm startup, delayed
network responses, offline reloads and an incompatible cached pre-Find controller.
Set `THREAD_PROFILE_VERBOSE=1` to log request and interaction timings.

## Tests

Run the focused calculation and regression tests from the repository root:

```bash
python3 -B -m pytest tests/test_threads.py tests/test_fasteners.py tests/test_thread_specifications.py tests/test_thread_models.py tests/test_thread_visualizer_ui.py -q
```

Run `tests/browser/thread-specification.cjs` with Node against a repo-root HTTP
server. Set `THREAD_TOOL_URL` and `PLAYWRIGHT_MODULE` if the local defaults do not
apply. It loads real Pyodide and checks progressive defaults, a shared result
panel, independent task inputs, expert notes, all 11 families, required depths,
no-size and measured-match boundaries, clipboard text, URL restoration, CSV,
safe text rendering, references below the workspace, mobile layout, and themes.
It also checks help coverage for every field, contextual expert explanations,
keyboard navigation and dismissal, viewport bounds, and touch opening/closing.
Copy tests compare clipboard contents with the visible text. Style checks
compare the tool's light-theme font, background, title size, and wordmark with
the homepage. Both engaged layouts are checked for unclipped pitch labels.
Screenshots are written to `/tmp`.
Pipe/product regressions check size-dependent pitch labels, tapered versus
parallel connections, entered and missing supplier dimensions, SVG arrow
attachment, unclipped labels, and 320px layouts in both themes.

`tests/browser/thread-find-exports.cjs` checks Find/legacy state, unit round trips,
PDF page boxes and exact scale-check vectors, lazy CAD loading, cancellation,
stale jobs and mobile help. `tests/browser/thread-cad-artifacts.cjs` exports and
reimports fourteen fixtures, then calls `validate_thread_step.py` using a separately
installed OCP 7.9.3.1 kernel. These developer tests require Playwright and OCP;
neither is a website runtime dependency.

`tests/browser/thread-cad-preview.cjs` checks the reimported mesh, embedded STEP
name, chamfer detail-note copying, section and edge controls, keyboard input,
stale/canceled jobs, and 320px light/dark views. The browser test uses software
WebGL rendering; that is a test setup, not a site requirement.

`tests/browser/thread-output-sheet.cjs` checks visible dimensions, direct
derivation expansion, current substituted values, chevrons, keyboard operation,
nonmodal settings, inline exports, lazy loading and mobile light/dark layouts.
It also checks that the default desktop output is at least 20% shorter than
the previous 1,021px result sheet, without hiding dimensions or truncating notes.

`tests/browser/thread-pdf-preview.cjs` checks preview-before-download, same-pitch
size separation, selection and pagination, exact PDF download bytes, diameter
references, lazy loading, retry, stale previews and mobile light/dark layouts.

On the local macOS ARM desktop (2026-09-07), chamfered construction plus STEP
round-trip checks took about 1.2–9.5 s across the first ten fixtures after kernel
initialization, with the 20-turn M4 x 0.5 fixture taking 9.5 s. A 40-turn trial failed the threaded-volume
check, so the UI caps exports at 20 turns. These are local measurements, not a
mobile-device or network-speed guarantee. Every fixture passed separate-kernel
closed-solid, volume and 40 axial-profile/handedness sample checks. Chamfered
fixtures also check 32 surface-neighbor points per treated end. One-ended,
custom-angle and square-ended specimens are included.
Repeated-export tests reused each worker for three jobs. Fresh kernel
initialization from the local static host took 63–71 ms after JavaScript module
loading; warm initialization was below the timer's resolution. This is not an
internet cold-download measurement. WASM linear memory ranged from 100 MiB to
about 163 MiB in the original square-ended sequence and reached 199 MiB in the
chamfered sequence, excluding other browser/JavaScript memory.

Release still requires a maintainer's physical Letter/A4 print calibration and
known metric/inch part comparison, plus visual review in their normal CAD app.
Record printer, viewer, paper, settings and measured error before calling the
paper comparison verified. Mobile hardware performance remains unmeasured.
The installed STEP Quick Look thumbnail process did not finish and was stopped;
it is not counted as a visual CAD review.
