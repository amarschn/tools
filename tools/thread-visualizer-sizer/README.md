# Thread Size Finder & Profile Visualizer

## Purpose

This tool handles three early thread-selection tasks in one place:

- Inspect the basic 60° geometry of an ISO metric or Unified thread.
- Rank nominal thread sizes from a measured outside diameter and pitch.
- Screen the smallest included thread whose tensile-stress area meets a direct axial proof-load requirement.

The default view opens on M10 × 1.5 with a calculated profile. No setup is required.

## Requirements

- Keep one input surface, controlled by the Explore, Identify, and Size for load tasks.
- Keep the thread profile visible with the numeric result.
- Support external, internal, and engaged profile views.
- Show major diameter, pitch or TPI, pitch diameter, internal minor diameter, tensile-stress area, and lead angle.
- Provide numbered equations, substituted values, variable definitions, and sources in the calculation ledger.
- Support light, dark, and system themes, display density, precision, and auto-update settings.
- Preserve the active task and its relevant inputs in copied links.
- Export the current calculation as CSV and disable result exports while inputs are stale or invalid.
- Show a loading overlay until Pyodide and the Python modules are ready.

## Tasks

### Explore a size

Choose a thread family and designation. The page draws the profile and reports its basic geometry. The drawing does not include a tolerance class, allowance, coating buildup, or gage limits.

### Identify a thread

Enter the measured external diameter and pitch. Unified threads use outside diameter in inches and thread count in TPI. The tool ranks the nearest three entries in its catalog using relative diameter and pitch residuals.

This is a nominal-size search, not an acceptance test. Confirm a physical part with its specified tolerance class and the correct thread gage.

### Size for load

Enter the direct tensile service load per fastener, a conservative minimum proof strength, and the required proof margin. The proof-strength value must remain valid across every candidate diameter in the selected series.

The tool selects the smallest passing size in its included catalog. It does not claim that no standardized size exists when the catalog limit is reached.

## Calculation core

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

Identification ranks each candidate with:

`s = √[((dₘ - d) / d)² + ((Pₘ - P) / P)²]`

Load sizing uses:

`F_d = n_d F`, `Aₛ,req = F_d / S_p`, and `F_p = S_p Aₛ`

## Included catalog

- ISO metric: 22 entries from M2 × 0.4 through M24 × 3.0, including 15 coarse and 7 fine-pitch entries.
- Unified: 23 entries from #2-56 UNC through 1-12 UNF, including 15 UNC and 8 UNF entries.

The lists come from `ISO_FASTENER_GEOMETRY` and `UTS_FASTENER_GEOMETRY` in `pycalcs.fasteners`. They are useful working subsets, not complete reproductions of ISO 262 or ASME B1.1.

## Load-screen scope

The size screen compares factored direct axial demand with proof strength times tensile-stress area. It omits preload, joint stiffness, external-load sharing, separation, fatigue, shear, thread stripping, engagement length, temperature, and installation scatter. Use the Bolt Torque Calculator for a preloaded-joint analysis.

## References

- [ISO 68-1:2023](https://www.iso.org/standard/85107.html), ISO general purpose screw threads, basic and design profiles for metric threads.
- [ISO 724:2023](https://www.iso.org/standard/85104.html), ISO metric thread basic dimensions.
- [ASME B1.1](https://www.asme.org/codes-standards/find-codes-standards/b1-1-unified-inch-screw-threads-un-unr-thread-form/2019), Unified inch thread form and designation.
- [NASA fastener training material](https://ntrs.nasa.gov/citations/20110016427), tensile-stress area equations.
- [NIST Handbook 28, Part VI](https://nvlpubs.nist.gov/nistpubs/hb/1970/hb28-scan6.pdf), Unified thread stress-area and strength formulas.

## Tests

Run the focused calculation and regression tests from the repository root:

```bash
python3 -B -m pytest tests/test_threads.py tests/test_fasteners.py -q
```

The browser release check covers both themes and responsive layouts, all three tasks, both thread families, copied-link restoration, no-size and invalid states, settings, and CSV export.
