# Thermal Path Budget Tool — Audit Findings

Date: 2026-03-28
Status: Complete audit of Codex implementation

---

## Executive Summary

The implementation is structurally sound. The solver math is correct, the payload shape is close to spec, templates pre-populate well, and the frontend renders from the backend payload without recomputation. The tool is usable today.

The main gaps are: missing dark mode CSS (repo convention violation), overly restrictive validation that contradicts the spec, broken derivation equation extraction, flat derivation display instead of accordion progressive disclosure, and missing expert mode / settings panel.

All 10 tests pass. Hand-verified numerics for series, parallel, and required-segment modes are correct.

---

## Numerical Correctness: PASS

### Verified by hand

**Series chain** (25W, R_jc=0.4, R_cs=0.2, R_sa=2.0, T_amb=40C):
- T_junction = 40 + 25*(0.4+0.2+2.0) = 105.0C. Solver: 105.0C. PASS.
- T_case = 40 + 25*(0.2+2.0) = 95.0C. Solver: 95.0C. PASS.
- T_sink = 40 + 25*2.0 = 90.0C. Solver: 90.0C. PASS.

**Parallel branch** (25W, R_sc=0.2, R_sink=2.0||R_pcb=6.0, T_amb=40C):
- R_eq = 1/(1/2+1/6) = 1.5 K/W. Solver: 1.5 K/W. PASS.
- Q_sink = 37.5/2.0 = 18.75W, Q_pcb = 37.5/6.0 = 6.25W. Solver sums to 25W. PASS.

**Required-segment sizing** (target T_junction=110C, R_jc=0.4, R_cs=0.2):
- R_sa = (110-40)/25 - 0.6 = 2.2 K/W. Solver: 2.2 K/W. PASS.

### Unit conversion in `tim_area_normalized`: CORRECT
`area_cm2 = area_m2 * 10000.0; resistance = impedance / area_cm2` (lines 620-621). The critical 1e4 factor is present and applied in the correct direction.

### Conductance matrix assembly: CORRECT
Fixed-temperature nodes excluded from unknowns, their contributions correctly added to the RHS. Gauss-Jordan with partial pivoting handles arbitrary connected topologies. No numpy dependency — Pyodide-compatible.

### `solve_required_segment`: CORRECT for general topologies
Uses bisection (80 iterations, sub-femto precision). Not limited to series-only formula. Works for parallel/branched networks. Returns the conservative (safe) side of the root.

---

## Critical Findings

### C1. No dark mode CSS

**File:** `index.html`
**Lines:** 22-544 (entire `<style>` block)

No `@media (prefers-color-scheme: dark)` block exists anywhere. No `body.dark-mode` class support. This is a mandatory repo convention per AGENTS.md. The accent color `#111827` will be invisible on dark backgrounds.

**Fix required:** Add a full dark mode block with appropriate variable overrides. Per AGENTS.md, accent color must be `#60a5fa` or similar in dark mode (not `#0066cc`).

---

## High Findings

### H1. `__init__.py` not updated

**File:** `pycalcs/__init__.py`

`thermal_networks` is not imported. The Pyodide loader works around this by fetching the .py file directly, but:
- `from pycalcs import thermal_networks` fails outside the browser
- Breaks the consistency pattern used by every other module
- Tests work only because `from pycalcs.thermal_networks import ...` still resolves

**Fix:** Add `from . import thermal_networks  # noqa: F401`

### H2. Validator rejects multiple heat sources and multiple boundaries as hard errors

**File:** `thermal_networks.py:117-122`

```python
if len(fixed_temperature_nodes) > 1:
    errors.append("The user-facing MVP supports exactly one fixed-temperature boundary node.")
if len(positive_heat_nodes) > 1:
    errors.append("The user-facing MVP supports exactly one positive heat_input_w node.")
```

The spec (section 19 Q2) explicitly recommends allowing multiple heat-input nodes. The solver math handles both cases correctly. The frontend templates default to one of each, which is appropriate progressive simplicity — but the backend should not block valid models.

**Fix:** Downgrade both to warnings, not hard errors. The solver already handles multi-source and multi-boundary correctly.

### H3. `equation_latex` in derivation objects is broken

**File:** `thermal_networks.py:1182`

```python
"equation_latex": segment["subst_resistance"].split("=")[0].strip(),
```

This splits the substituted string on `=` and takes the first part, yielding just `"R_{\theta} "` — the bare LHS symbol, not the governing equation. The spec expects the actual equation form (e.g., `R_\theta = \frac{t}{kA}`).

**Fix:** Store the governing equation separately during resistance resolution, not extract it from the substitution string.

### H4. Derivation panels are flat, not accordion

**File:** `index.html:1556-1571` (`renderDerivations`)

All derivation cards are rendered simultaneously as a flat list. The spec and AGENTS.md require:
- Clickable result cards that expand to show derivation
- Only one panel open at a time (accordion)
- Derivations linked to their parent result (segment row -> derivation)

**Fix:** Wrap each derivation in a `<details>` element or implement accordion JS, and wire segment table rows to their derivation panels.

### H5. `contribution_pct` silently exceeds 100% for parallel paths

**File:** `thermal_networks.py:868`

For the parallel test case, contributions sum to ~188%. Both parallel branches report 88% because they share the same delta_T. No warning, no documentation of the convention.

**Fix:** Either (a) document this convention explicitly in `reporting_basis`, (b) use equivalent-group contribution for parallel branches, or (c) add a warning when contributions sum to >105%.

---

## Medium Findings

### M1. No expert mode toggle

Everything is visible at once: all segment inputs, all sensitivity controls, the unknown segment row (hidden only by workflow, not by expertise level). The spec calls for progressive simplicity where secondary fields (notes, tags, categories, bounds) are gated behind an expert toggle.

### M2. No settings panel

The advanced template includes a settings panel for theme, density, and precision. This tool has none.

### M3. Segment table not sorted by contribution

**File:** `index.html:1532`

Segments render in definition order, not by contribution. The spec says the breakdown should lead with the biggest bottleneck. Sorting by `contribution_pct` descending would make the table immediately diagnostic.

### M4. No contribution bar chart

The spec calls for a "stacked temperature-drop bar from hot node to ambient" and a "contribution bar chart by segment." Only tables are present.

### M5. Background tab is thin

**File:** `index.html:725-748`

Has three sections (good fit, other tool, governing idea) but is missing:
- Worked example mapping recipes
- Common node definitions (what constitutes a "case" node, etc.)
- External references and caveats
- How to map physical hardware into nodes

This is L4/L5 content that the spec calls out as important for teaching users.

### M6. Missing test coverage

Present (10 tests):
- Series chain, TIM conductivity mode, required-segment sizing, parallel path, multiple heat inputs validation, solved_unknown in wrong mode, no boundary validation, sensitivity sweep, sensitivity minimum points

Missing:
- `tim_area_normalized` mode (the highest-risk numerical mode)
- `simple_conduction_slab` mode
- Disconnected network validation
- Duplicate node/segment id validation
- Segment references nonexistent node
- Payload shape verification (assert all required fields present)
- Derivation object completeness
- Zero heat input edge case
- Infeasible required-resistance (negative R needed)

### M7. No test-cases/*.json files

The AGENTS.md spec and the Parameter JSON Test Cases section require pre-configured input JSON files for tools. None exist.

### M8. Pyodide loader fetches single file only

**File:** `index.html:1704-1712`

The loader downloads only `thermal_networks.py` via `pyfetch`. If the module ever imports from other `pycalcs` modules (e.g., shared TIM utilities), this pattern will break. The standard pattern (`sys.path.insert`) requires the full package to be available.

This works today because `thermal_networks.py` has no intra-package imports, but it's fragile.

---

## Low Findings

### L1. Double validation on successful solves

The frontend calls `validate_thermal_network_model()` then `solve_thermal_network()`. The solver internally calls `validate_thermal_network_model()` again (line 282). This means every successful solve validates twice.

Not a bug, but unnecessary work. Either remove the frontend validation call (and let the solver return the invalid payload), or have the solver accept an already-validated normalized model.

### L2. `net_outgoing_heat_w` echoes `heat_input_w`

**File:** `thermal_networks.py:937`

For pass-through nodes (0W input), `net_outgoing_heat_w` is 0.0. This is technically correct (net heat balance at steady state = applied heat), but the user may expect to see the total heat flowing through the node. Consider adding a `total_heat_flow_through_w` field.

### L3. `budget_ambient_segment` workflow has no matching analysis mode

**File:** `index.html:590-591`

A third workflow option `"budget_ambient_segment"` is offered in the dropdown, but the backend only supports `"solve_temperatures"` and `"solve_required_segment"`. The frontend maps it to `"solve_required_segment"` internally (line 1245-1248), so it works. But the naming disconnect may confuse future developers.

### L4. Hardcoded background colors in segment cards

**File:** `index.html:286`

`.segment-card { background: #fbfcfd; }` and `.section-card { background: #fff; }` use hardcoded colors instead of CSS variables. These will not respond to dark mode even after dark mode variables are added.

### L5. Summary `effective_total_resistance_k_per_w` with multiple heat sources

If the multiple-heat-source restriction (H2) is lifted, this field becomes misleading. The current formula `(T_hot - T_ref) / Q_total` is only physically meaningful for a single source. Consider adding a warning or `null`-ing it when multiple sources exist.

---

## Progressive Disclosure Scorecard

| Layer | Spec Requirement | Status |
|-------|-----------------|--------|
| L0 Summary | Status banner + headline cards | GOOD — color-coded banner, 4-5 summary cards |
| L1 Breakdown | Tables + diagram, no equations | PARTIAL — tables and diagram present, but segments not sorted by contribution, no bar chart |
| L2 Equations | Clickable expansion with substituted values | POOR — derivations are on a separate tab, flat (not expandable from results), equation_latex broken |
| L3 Intermediate | Math tab with node balance, parallel groups | PARTIAL — derivation cards present but flat, no node balance equations, no conductance matrix |
| L4 Applicability | Background tab with guidance | PARTIAL — three sections present but thin, missing worked examples and mapping recipes |
| L5 References | External references, common definitions | MISSING — no references, no common node definitions |

## Progressive Simplicity Scorecard

| Aspect | Spec Requirement | Status |
|--------|-----------------|--------|
| Templates pre-populate | Nodes, segments, default modes, placeholder values | GOOD — all 5 templates fully pre-populate |
| Time to first answer | Under 1 minute from template | GOOD — select template, hit Calculate |
| Mode-specific inputs | Only show fields for selected mode | GOOD — each mode shows only its fields |
| Expert mode toggle | Hide secondary inputs | MISSING — everything visible |
| Workflow gating | Hide sizing controls when not needed | GOOD — unknown row hidden in solve_temperatures mode |
| `budget_ambient_segment` shortcut | One-click sizing of the ambient segment | GOOD — nice progressive simplicity touch |

## Single Payload Architecture: GOOD

The frontend calls `solve_thermal_network()` once and renders all views from the payload. Derivations come from `derivations[]`. Diagram renders from `diagram_payload`. No frontend recomputation of resistances, contributions, or equivalent groups.

---

## Recommended Fix Priority

1. **Dark mode CSS** (C1) — required by repo conventions, affects all users
2. **Derivation accordion + equation fix** (H3, H4) — this is the core progressive disclosure mechanism
3. **Relax validator restrictions** (H2) — spec says allow multi-source
4. **`__init__.py` import** (H1) — one-line fix
5. **Sort segment table by contribution** (M3) — quick win for diagnostics
6. **Add missing test coverage** (M6) — especially `tim_area_normalized` mode
7. **Expert mode toggle** (M1) — important for progressive simplicity
8. **Contribution bar chart** (M4) — visual bottleneck identification
9. **Background tab content** (M5) — educational value
10. **Settings panel** (M2) — repo convention for advanced tools
