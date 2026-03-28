# Thermal Path Budget Tool — Audit Plan

Date: 2026-03-28

---

## 1. Numerical Correctness

### 1.1 Unit conversion in `tim_area_normalized`

The schema mixes `impedance_k_cm2_per_w` (cm^2) with `contact_area_m2` (m^2). The correct conversion is:

```
R = impedance_k_cm2_per_w / (contact_area_m2 * 1e4)
```

If the implementer forgets the `1e4` factor or applies it backwards, the resistance will be off by 10,000x. This is the highest-risk numerical bug because both the input and output can have reasonable-looking magnitudes either way.

### 1.2 Conductance matrix assembly

The solver must build `G * T = Q` where:

- G is the conductance matrix (sum of 1/R on diagonal, -1/R on off-diagonals).
- Fixed-temperature nodes are excluded from unknowns but their contributions must appear in the RHS vector.
- Getting the indexing wrong between "all nodes" and "unknown nodes" is a classic off-by-one source.

Verify by hand-calculating a 3-node series chain and a simple parallel branch case, then comparing to solver output.

### 1.3 All five resistance modes

Verify each mode resolves to the correct scalar `R` in K/W:

- `direct`: passthrough of `resistance_k_per_w`
- `tim_area_normalized`: `R = Z / (A * 1e4)` (unit conversion)
- `tim_conductivity`: `R = t / (k * A)`
- `simple_conduction_slab`: `R = L / (k * A)`
- `solved_unknown`: placeholder handling, not a resistance value until solved

### 1.4 Both solve modes

- `solve_temperatures`: full forward solve, all resistances known.
- `solve_required_segment`: back-solve for one unknown resistance given a target node temperature.

For `solve_required_segment` with parallel paths, the relationship between the unknown resistance and the target temperature is nonlinear. Verify the implementation uses numerical root-finding (bisection/Newton) rather than assuming a series-only formula.

### 1.5 Heat flow and direction

Per-segment heat flow: `Q = delta_T / R`. Direction field should reflect the sign of heat flow relative to the `from_node_id` -> `to_node_id` convention. Verify correctness for both series and branched topologies.

### 1.6 Contribution percentage with parallel paths

The spec defines `contribution_pct = 100 * |delta_T| / total_rise`. In parallel branches, both branches share the same delta_T across shared entry/exit nodes. Summing contribution_pct across all segments will exceed 100%. Verify the implementation handles this explicitly (e.g., using equivalent-group contributions) or at minimum documents the convention.

### 1.7 Effective total resistance with multiple sources

`effective_total_resistance_k_per_w = total_rise / total_heat` is only physically meaningful with one heat source. With multiple sources it becomes an aggregate that can mislead. Verify warnings or caveats are present.

### 1.8 Edge cases

- Zero heat input everywhere: all nodes should equal the boundary temperature.
- Single-segment network (two nodes, one segment).
- Infeasible required-resistance (negative R needed): should report clearly, not crash.
- Boundary-only network (all nodes fixed): trivially solved.
- Very large resistance ratios making one branch negligible.

---

## 2. Validation Function

### 2.1 Hard errors (must block solving)

- Missing required top-level fields.
- Duplicate node ids.
- Duplicate segment ids.
- Segment references nonexistent node id.
- Zero or negative resolved resistance inputs.
- No fixed-temperature node.
- Disconnected network (must use real BFS/DFS, not just "every node appears in a segment").
- More than one `solved_unknown` segment.
- `solve_required_segment` mode without valid `solve_target`.
- `unknown_segment_id` does not match the `solved_unknown` segment.

### 2.2 Warnings (allow solving, surface caution)

- Multiple heat-input nodes when template expects one.
- No node temperature limits defined.
- Large resistance ratios that may make a branch negligible.
- Conduction slab used where spreading effects may dominate.
- Boundary node marked as internal or vice versa.

### 2.3 Normalization

- Fills optional defaults (`heat_input_w` -> 0.0, `notes` -> "").
- Returns a clean normalized model ready for solving.

---

## 3. Schema & Payload Compliance

### 3.1 Solved output payload

Verify every field from the schema spec is present:

- Top level: `status`, `mode`, `summary`, `nodes`, `segments`, `parallel_groups`, `diagram_payload`, `derivations`, `warnings`, `recommendations`, `assumptions`, `normalized_model`.
- Summary: all required fields (`hottest_node_id`, `hottest_node_label`, `hottest_temperature_c`, `reference_node_id`, `reference_temperature_c`, `total_temperature_rise_c`, `total_applied_heat_w`, `effective_total_resistance_k_per_w`, `dominant_segment_id`, `dominant_segment_label`, `dominant_segment_contribution_pct`) plus conditional fields.
- Solved nodes: `id`, `label`, `kind`, `temperature_c`, `fixed_temperature_c`, `heat_input_w`, `net_outgoing_heat_w`, `connected_segment_ids`, plus optional margin/status fields.
- Solved segments: `id`, `label`, `from_node_id`, `to_node_id`, `category`, `mode`, `resolved_resistance_k_per_w`, `heat_flow_w`, `delta_t_c`, `contribution_pct`, `direction`, `is_solved_unknown`, `inputs`, plus `subst_resistance` and `subst_delta_t`.
- Diagram payload: `nodes` (with `rank`, `is_reference`, `is_hottest`), `edges`, `reference_node_id`, `primary_hot_path_node_ids`.
- Derivation objects: `id`, `subject_type`, `subject_id`, `result_key`, `title`, `equation_number`, `equation_latex`, `variable_legend`, `substitution_latex`, `result_value`, `result_units`, `depends_on`, `step_type`.

### 3.2 Sensitivity payload

- `series` array with correct fields per segment sweep.
- Re-solves full network for each perturbation point (no linear shortcuts).

### 3.3 Substitution strings

Every computed resistance and key temperature value should have a corresponding `subst_*` string with LaTeX-formatted substituted values.

---

## 4. Progressive Disclosure (Output Side)

This is the most important design principle in the repo, and the spec explicitly calls this tool out as a model example.

### 4.1 L0 — Summary banner

- Is this the first thing visible on the Results tab?
- Does it show hottest temp, margin, status badge, dominant bottleneck — and nothing else?
- Is the dominant bottleneck called out by label, not just id?
- Are status badges color-coded (green/amber/red)?

### 4.2 L1 — Network breakdown

- Node temperature table and segment contribution table present?
- Are segments sorted by contribution (biggest first)?
- Is there a contribution bar chart or stacked temperature-drop visual?
- Is the network diagram driven by the payload's `diagram_payload`, not a separate hand-authored SVG?
- Does this layer answer "what's driving the result?" without showing any equations?

### 4.3 L2 — Equations and substitution

- Does clicking a result card or segment row expand to show the governing equation?
- Are derivation panels wired to the `derivations` array from the payload?
- Does each panel show equation number, LaTeX equation, substituted values, and result?
- Does only one derivation panel expand at a time (accordion pattern per AGENTS.md)?

### 4.4 L3 — Intermediate logic

- Is the Math tab a separate tab, not interleaved with Results?
- Does it show full node balance equations?
- Are equivalent resistance derivations present for parallel groups?
- Is the required-resistance back-solve shown step-by-step?

### 4.5 L4 — Applicability

- Does the Background tab exist with substantive content?
- Does it explain when to use this tool vs. `simple_thermal` vs. a spreader tool?
- Are the guardrails from spec section 15 surfaced (geometry-dominant problems, multiple distributed sources, radiation dominance, etc.)?

### 4.6 L5 — References

- Background on thermal circuits and the resistor-network analogy?
- Worked mapping recipes (how to turn physical hardware into nodes)?
- Common node definitions?
- External references and caveats?

---

## 5. Progressive Simplicity (Input Side)

### 5.1 Templates as complexity gating

- Does "Package to sink" pre-populate a 4-node series chain with sensible defaults and placeholder resistances?
- Can a user get a meaningful first answer in under a minute with a template?
- Does "Custom network" handle the jump in complexity gracefully, or does it dump the user into a blank editor?

### 5.2 Default vs. expert inputs

- Are only essential inputs visible by default (heat input, ambient temp, key resistances)?
- Is there an expert mode toggle that reveals secondary fields (notes, tags, categories, bounds)?
- Are solve_target inputs hidden when analysis mode is `solve_temperatures`?

### 5.3 Segment mode as progressive input

- Is `direct` (one field) the default segment mode?
- Do `tim_conductivity` (three fields) and other modes only expand their fields when explicitly selected?
- Does the UI avoid showing all possible fields for all modes simultaneously?

---

## 6. Single Payload Drives Everything

The solve function returns one payload; every tab, panel, card, and chart must render from it.

- Does the frontend recompute resistances, contributions, or equivalent groups that the backend already provides? It should not.
- Are derivation panels built from the `derivations` array, or are equations hardcoded in the HTML?
- Does the diagram render from `diagram_payload`, or is it constructed independently from the raw model?
- Does export serialize the solved payload, or reconstruct data separately?

---

## 7. Repo Convention Compliance

### 7.1 Python standards

- Docstrings use exact `---Parameters---`, `---Returns---`, `---LaTeX---` section headers.
- Type hints on all function signatures.
- Specific exceptions (`ValueError`, `ZeroDivisionError`), never generic `Exception`.
- Module added to `pycalcs/__init__.py`.

### 7.2 Frontend standards

- Based on `example_tool_advanced` template.
- Loading overlay while Pyodide initializes.
- Dark mode CSS variables (accent color must not be `#0066cc` in dark mode; use `#60a5fa` or similar).
- Settings panel (theme, density, precision).
- Semantic HTML5, accessibility (labels, contrast, keyboard nav).
- Tabs: Model, Results, Math, Background.

### 7.3 Pyodide integration

- Standard initialization pattern.
- Complex nested JSON model serialized to Python correctly (this tool differs from flat-parameter tools).
- Error handling for validation failures displayed in the UI.

### 7.4 Registration

- `catalog.json` entry with correct category, tags, and path.
- `test-cases/*.json` files with pre-configured inputs.

---

## 8. Likely Codex Shortcomings to Watch For

1. **Flat results dump instead of layered disclosure.** All equations, intermediate values, and tables on one scrollable page instead of gated behind clicks/tabs/accordions.
2. **Missing derivation objects.** Backend returns temperatures and resistances but skips generating the `derivations` array, leaving the Math tab empty or forcing the frontend to reconstruct math.
3. **Templates that are just labels.** Template selector sets `template_id` but does not actually pre-populate node/segment arrays, defeating the time-to-value goal.
4. **No background content.** L4/L5 content requires domain knowledge and prose. Likely stubbed or skipped.
5. **Expert mode not implemented.** Everything visible at once with no toggle.
6. **Series-only `solve_required_segment`.** Works for chains but silently wrong for branched networks.
7. **`subst_*` strings missing or incomplete.** Backend omits substituted equation strings for some or all computed values.
8. **Disconnected network check uses naive approach.** Checks that all node ids appear in segments but does not do real graph traversal.
9. **Frontend recomputes values the backend already provides.** Violates single-source-of-truth.
10. **Pyodide integration uses flat parameter pattern.** This tool requires passing a nested JSON model, not a flat parameter list.

---

## 9. Test Coverage

### 9.1 Required test cases

- Nominal simple series chain (hand-verified temperatures).
- Nominal parallel branch case (hand-verified heat split and temperatures).
- Each resistance mode (direct, tim_area_normalized, tim_conductivity, simple_conduction_slab).
- Required-segment sizing mode (series and branched).
- Duplicate id validation (expect error).
- Disconnected network validation (expect error).
- No boundary node validation (expect error).
- Solved payload completeness (all required fields present).
- Derivation object completeness (all required fields present).

### 9.2 Numerical spot-checks

Hand-calculate reference values for at least:

- 3-node series: Junction (25W) -> Case (R=0.4) -> Sink (R=2.0) -> Ambient (40C). Expected: T_junction = 40 + 25*(0.4+2.0) = 100C.
- Parallel branch: Source (10W) -> splits to Path A (R=4) and Path B (R=6) -> Ambient (25C). Expected: R_eq = 2.4, T_source = 25 + 10*2.4 = 49C, Q_A = 24/4 = 6W, Q_B = 24/6 = 4W.
