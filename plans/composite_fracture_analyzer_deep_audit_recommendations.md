# Composite Fracture Analyzer — Deep Audit Recommendations

Date: 2026-02-27
Tool: `tools/composite-fracture-analyzer/`
Backend: `pycalcs/fracture_mechanics.py`

## Executive Summary

The tool has a solid overall architecture and uses standard LEFM/Paris-law structure, but it still has theoretical and logical failure modes that can produce contradictory or false-safe outputs. It should not be treated as safety-decision-grade until the critical items below are addressed.

---

## Critical Blockers (Fix Before Safety-Critical Use)

### 1) Enforce Crack-Model Validity Domains

Current behavior allows non-physical crack geometry combinations to pass through the solver.

Required actions:
1. Add backend validation for `a/W` and `a/c` by crack type.
2. Reject out-of-domain conditions with explicit `ValueError` messages.
3. Require `Y > 0` and finite before computing `K_I`.

Minimum domain checks to enforce:
1. `edge`: enforce stated range (currently documented as `a/W < 0.6`).
2. `double_edge`: enforce stated range (`a/W < 0.7`).
3. `through`: enforce `0 < a/W < 1` for the secant form.
4. `elliptical_surface`, `corner`: enforce calibrated `a/c` and `a/W` range supported by the implemented approximation.

Why:
Negative or explosive `Y` values cause non-physical `K_I`, which cascades into invalid safety factors and life predictions.

### 2) Eliminate Contradictory Safety States

Current logic can produce combinations like:
1. `status = acceptable`
2. `fracture_safety_factor = inf`
3. `life_fraction_used = inf`

Required actions:
1. Define status from both fracture and fatigue criteria, not fracture alone.
2. If `cycles_to_failure == 0`, force `status = unacceptable`.
3. If geometry/model invalid, raise error instead of returning computed status.

Why:
A safety status must be a coherent function of all governing checks.

### 3) Correct Infinite-Life and Inspection Semantics

Current behavior sets infinite-life inspection interval to `0`, which reads like “inspect immediately” rather than “no finite failure crossing in this model.”

Required actions:
1. Represent no-finite-failure as `cycles_to_failure = inf`, `inspection_interval = inf` (or explicit `null` with message).
2. Display a clear UI tag: “No K_IC intersection found in modeled ligament.”
3. Avoid using artificial upper crack bounds as if they were physical critical sizes.

Why:
Safety outputs must preserve physical meaning, especially for maintenance planning.

### 4) Harden Input Validation in Backend (Not UI-Only)

Required actions:
1. Validate `crack_orientation` against explicit allowed set.
2. Validate `crack_location_radius_mm >= 0` for solid disks.
3. Validate `design_life_cycles > 0`, `required_fracture_sf > 0`, and sensible lower bounds for engineering use.
4. Validate `crack_aspect_ratio > 0` and range-constrained per selected crack type.

Why:
Backend API must be safe independent of UI controls.

---

## Major Model-Fidelity Improvements

### 5) Clarify and Restrict Use of Advanced Crack Types

`elliptical_surface` and `corner` are currently approximate and can exceed their reliable domain.

Required actions:
1. Either narrow to a documented conservative domain with strict validation, or
2. Replace with a verified formulation and source-domain constraints documented inline.

### 6) Revisit Ligament Definition vs Crack Location

Current ligament width logic is orientation-based and largely independent of crack location.

Required actions:
1. Define crack-type-specific geometry interpretation for rotor sections.
2. If not supported, explicitly constrain supported geometries and show a warning.

Why:
Geometry abstraction should match the chosen `Y` equation assumptions.

### 7) Align Isotropic Rotor Stress Assumption with Composite Messaging

The tool treats composites as effective isotropic, which is acceptable as a first-pass approximation but must be prominent in risk communication.

Required actions:
1. Surface an always-visible warning in results for anisotropy limitation.
2. Require user acknowledgment for critical-use export/report generation.

---

## Documentation and UX Consistency

### 8) Remove Documentation Contradictions

Required actions:
1. Fix docstring text where crack-orientation semantics are reversed/inconsistent.
2. Keep README, background tab, and backend docstring aligned for equation domains and units.

### 9) Improve Failure Messaging Hierarchy

Required actions:
1. If input/model invalid, show hard error and clear prior results.
2. If model is valid but no finite fracture crossing exists, show explicit non-failure-mode banner.
3. If fatigue governs despite fracture SF passing, status must still downgrade.

---

## Verification Plan (Required)

### 10) Add Deterministic Regression Cases

Add tests that lock expected behavior for:
1. Invalid geometry domains (`a/W`, `a/c`) must raise.
2. `Y <= 0` must raise.
3. `critical_crack_reached=False` must produce infinite-life semantics consistently.
4. `cycles_to_failure=0` must force `unacceptable`.

### 11) Add Property-Based Sanity Tests

Randomized checks within valid domain:
1. Increasing RPM should not increase life.
2. Increasing initial crack size should not increase life.
3. Decreasing toughness should not increase fracture SF.
4. All returned primary outputs must be finite or explicitly flagged as `inf` by defined rules.

### 12) Add External Reference Cross-Checks

For representative cases, compare against:
1. Closed-form handbook values where available.
2. A trusted fracture-growth reference workflow/tool for trend agreement.

---

## Acceptance Criteria

The tool can be considered safety-review ready when all are true:
1. No non-physical `Y`, `K_I`, or contradictory status/life combinations can be produced from accepted inputs.
2. All crack models enforce documented validity limits.
3. Status logic integrates fracture and fatigue outcomes consistently.
4. Infinite-life and no-crossing states are represented unambiguously.
5. Regression and property tests cover boundary and randomized valid-domain behavior.
