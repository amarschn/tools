# Tier-A Tool Builds: Decision Pass/Fail Upgrades

Date: 2026-07-12

## Goal

Convert our three highest-search-intent tools from "calculators" into
**decision tools** that answer a pass/fail question and produce a client-ready
artifact. These are the queries people Google verbatim and that convert:
"is this wire big enough", "does this beam pass L/360", "is this bolt safe".

Follow-on from `plans/2026-07-12_seo_distribution_wins.md` (SEO backlog, Tier A).
Rationale: winners are decision-blocking + exportable, ideally naming a standard.

## Shared principles (apply to all three)

- **Verdict-first UI:** a single prominent PASS / FAIL / MARGINAL banner above
  the existing detailed results — obey progressive disclosure (verdict → why →
  numbers → derivation). Do not hide the existing calculations; add a layer.
- **Reuse, don't reinvent:** `thermal-path-budget` and `wire-sizing` already
  contain a verdict/pass-fail pattern — lift its markup/CSS into a small shared
  helper rather than hand-rolling three different banners.
- **One governing standard cited per verdict** (NEC / deflection-limit table /
  VDI 2230) so the result is defensible and SEO-relevant.
- **Export stays a demand signal:** export buttons already fire
  `export_action` via `shared/analytics-autotrack.js`; keep that wired.
- **pycalcs is the single source of truth:** all new logic lands in `pycalcs`
  with docstrings (`---Parameters---/---Returns---/---LaTeX---`) + tests, never
  in tool-local `.py` files.

### Proposed shared helper
`shared/verdict.js` (or a documented CSS block): renders a status banner given
`{status: pass|marginal|fail, headline, reasons[]}`. Built once during the
first tool (wire-sizing), reused by the other two. Keep it dependency-free.

---

## Tool 1 — Wire Sizing (highest search volume; heaviest)

**Current state (better than it looked):**
- Tool fetches `../../pycalcs/wire_sizing.py` — a complete 830-line module with
  full NEC 2020 Table 310.16 (Cu/Al at 60/75/90 °C), temp + bundling derates,
  and voltage-drop. Data is good.
- Local `tools/wire-sizing/wire_calc.py` + `test_wire_calc.py` are **dead code**
  (stubbed tables, not imported). `README.md.txt` / `reference_data.md.txt` have
  `.txt` extensions so they never render.

**Gaps to close:**
1. **Breaker / OCPD sizing** — add NEC 240.6(A) standard ampere ratings
   (15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 110, 125, ...) and the
   240.4 rule (round *up* to next standard size ≤ certain conditions; 240.4(D)
   small-conductor limits for 14/12/10 AWG). Confirm whether `pycalcs.wire_sizing`
   already has any breaker helper; if not, add `select_breaker()` +
   `check_conductor_protection()`.
2. **Unified verdict** combining: ampacity (after derates) ≥ load, voltage drop
   ≤ limit (default 3% branch / 5% total per NEC informational note), and
   breaker protects conductor. Output PASS/MARGINAL/FAIL + the binding
   constraint ("limited by voltage drop at 120 ft").
3. **Cleanup:** delete dead `wire_calc.py` + `test_wire_calc.py`; rename READMEs
   to `.md`; confirm no reference to the deleted files.

**Tasks:**
- [ ] `pycalcs/wire_sizing.py`: add `NEC_STANDARD_BREAKERS`, `select_breaker()`,
      `check_conductor_protection()`, and a top-level `evaluate_circuit()` that
      returns the combined verdict dict.
- [ ] Tests in `tests/test_wire_sizing.py`: breaker rounding, 240.4(D) small-
      conductor caps, verdict for known textbook circuits (e.g. 40 A load / 8 AWG
      Cu 75 °C / 100 ft → check gauge, breaker, VD%).
- [ ] Tool UI: verdict banner + "binding constraint" line; keep existing detail.
- [ ] Delete dead files; fix README extensions; update sitemap/meta scripts n/a
      (catalog unchanged) — but re-run `inject_seo_meta.py` if head edited.
- [ ] `/verify`: drive nominal + failing circuit; confirm verdict flips.

**Effort:** Medium-High. **Verification:** hand-calc 3 circuits vs NEC examples.

---

## Tool 2 — Beam Deflection Pass/Fail (medium)

**Current state:** `beam-bending` is **human-verified**, already computes
deflection, shear, moment, extreme-fibre stress for 4 load cases × several
sections in SI. Logic lives in `pycalcs` (beam module).

**Gap:** no serviceability verdict. Add a deflection-limit check against a
selectable ratio (L/180, L/240, L/360, L/480 — the common IBC Table 1604.3
values) plus an optional absolute limit, and a stress check vs allowable
(yield / safety factor).

**Tasks:**
- [ ] pycalcs: add `deflection_limit_check(delta, span, ratio)` and
      `stress_check(sigma, allowable)`; return ratio achieved (e.g. "L/512") and
      pass/fail. Keep in the existing beam module.
- [ ] Tests: known simply-supported UDL case at L/360 boundary.
- [ ] UI: ratio dropdown (default L/360) + allowable-stress input; verdict banner
      shows both the deflection verdict and the achieved L/x, and the stress
      verdict. Reuse `shared/verdict.js`.
- [ ] `/verify`: toggle a passing beam into failing by shortening the section.

**Effort:** Low-Medium (additive to a verified tool; do NOT alter verified math).

---

## Tool 3 — Bolt Safety-Factor Verdict (lightest)

**Current state:** `bolt-torque` already computes yield, clamping, fatigue, and
shear-slip safety factors per VDI 2230 with full visualizations. The physics is
done.

**Gap:** the safety factors are shown as numbers but there's no single
consolidated PASS/FAIL that flags the *governing* (minimum) safety factor
against user-set thresholds.

**Tasks:**
- [ ] pycalcs (bolt module): add `joint_verdict(safety_factors, thresholds)`
      returning the governing SF, which check binds, and pass/marginal/fail.
      Default thresholds: yield ≥ 1.1, slip ≥ 1.2, fatigue ≥ 1.5 (documented,
      user-overridable).
- [ ] Tests: a joint that passes yield but fails slip → verdict FAIL on slip.
- [ ] UI: verdict banner naming the governing check ("Governed by slip, SF=1.05
      < 1.2"). Reuse `shared/verdict.js`.
- [ ] `/verify`: raise external load until verdict flips.

**Effort:** Low (mostly presentation over existing math).

---

## Build order & branching

Recommended sequence (build the shared helper first, riskiest data work first,
then cheap wins):
1. **Wire Sizing** — build `shared/verdict.js` here; adds breaker logic + cleanup.
2. **Beam Deflection** — reuse helper; additive to verified tool.
3. **Bolt Verdict** — reuse helper; presentation over existing SFs.

- One `task/tier-a-passfail` branch (or one branch per tool if they land
  separately). Keep `main` deployable; merge per tool after `/verify` + pytest.
- No `catalog.json` title/desc change required, but if a `<head>` is edited,
  re-run `scripts/inject_seo_meta.py` (idempotent) before commit.
- After each merge, `pytest tests/` must stay green (currently 999 passing).

## Explicitly out of scope
- New tools beyond these three (see SEO backlog for later ideas).
- PDF/Excel export engine (tracked separately in TODO.md); these tools keep the
  existing export mechanism.
- Re-verifying beam math — it is human-verified; only add layers around it.
