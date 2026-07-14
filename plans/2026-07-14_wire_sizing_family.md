# Wire Sizing Tool Family — Multi-Standard Expansion

Date: 2026-07-14

## Goal

Expand beyond the NEC tool into a family of standard-specific wire-sizing pages,
each a sharp SEO landing page for a distinct query cluster, all sharing one
calculation engine. Follows the architecture agreed in
`plans/2026-07-12_tier_a_passfail_tools.md` and the NEC build.

## Architecture (settled): one engine, many pages

```
pycalcs/wire_sizing.py   ← shared engine
  shared math: resistance, voltage drop, conductor geometry, verdict banner
  standard-specific DATA plugged in: ampacity tables, derating rules, OCPD/verdict
        │
        ├─ /tools/wire-sizing/          NEC (US premises)        ✅ shipped
        ├─ /tools/dc-wire-sizing/       SAE J1128 / ISO 6722     ← candidate
        ├─ /tools/marine-wire-sizing/   ABYC E-11                ← candidate
        └─ /tools/solar-wire-sizing/    NEC 690 + free-air       ← candidate
```

Each new standard is **additive data + a thin page**, not a new codebase. Reuse
`shared/verdict.js`, the theme/settings/tooltip template from the NEC tool, and
the shared VD/resistance math. Refactor `pycalcs/wire_sizing.py` so the ampacity
table, derating rules, and verdict thresholds are passed in per standard (a
`Standard` config object) rather than hard-coded to NEC.

## Why the standards genuinely differ (do NOT reuse NEC data)

| Standard | Domain | Key differences from NEC | Primary queries |
|----------|--------|--------------------------|-----------------|
| **SAE J1128 / ISO 6722** | Automotive, RV, 12/24/48 V DC, battery banks | Different ampacity (single wire in free air vs bundle; 105 °C+ insulation); voltage drop is the dominant constraint at low V; chassis-ground return; mm² and AWG | "12v wire size calculator", "wire gauge calculator amps", "battery cable size" |
| **ABYC E-11** | Marine (boats) | Ampacity tables for inside vs outside engine spaces; conservative derates; tinned copper; 3%/10% VD categories (critical vs non-critical loads) | "marine wire size", "abyc wire gauge", "boat wiring size" |
| **NEC 690 + free-air** | Solar PV | Free-air ampacity (Table 310.17), 1.25× irradiance + 1.25× continuous stacking, temperature range of arrays | "solar wire size calculator", "pv wire sizing" |

Voltage drop, which is *advisory* under NEC, is often a *design requirement*
(sometimes standard-specified, e.g. ABYC's 3%/10%) in these domains — the verdict
config must express that per standard.

## Data sourcing & verification (critical)

These tables are real published engineering data. Each tool must:
- Encode ampacity/derating from the actual standard (cited in the tool + docstring).
- Ship with `test-cases/*.json` and pytest cases checked against known examples.
- Be tagged **Experimental** until a human verifies the tables/verdicts; only then
  add `human-verified`.
- Follow `docs/RELEASE.md` "Tool Release Checklist" (theme, settings, tooltips,
  legible copy-link, browser smoke test) before merge.

## Build order (confirmed 2026-07-14, one at a time, verify each)

1. **Solar PV (NEC 690)** — first. Smallest lift / most NEC-adjacent (free-air
   Table 310.17 + 690.8 sizing), good to establish the multi-standard pattern.
2. **IEC 60364 (international)** — metric tables + installation-method reference
   current-carrying capacities (Method A–F). Larger data lift.
3. **DC / Automotive (SAE J1128 / ISO 6722)** — highest search volume; single-
   wire free-air automotive ampacity, voltage-drop-led.

(Marine/ABYC not selected.)

## BLOCKER: authoritative ampacity data required per standard

Ampacity tables are safety-relevant published data and must NOT be reproduced
from memory. For each tool, encode from a cited authoritative source and ship
**Experimental** until a human verifies the table. Sources needed:
- Solar: NEC Table 310.17 (free-air ampacity, Cu/Al 60/75/90 °C) + 690.8(A)/(B)
  sizing factors (1.25 × 1.25 = 1.56 × Isc).
- IEC: IEC 60364-5-52 current-carrying-capacity tables by installation method.
- SAE/ISO: SAE J1128 / ISO 6722 single-wire-in-free-air ampacity by gauge/temp.
Confirm the source (or provide datasheet/table) before encoding numbers.

## Engine refactor sketch (pycalcs/wire_sizing.py)

- Introduce a `WIRE_STANDARDS` registry: each entry supplies ampacity table(s),
  temperature/bundle derating functions, OCPD rules (if any), default VD target,
  and whether VD is advisory or required.
- `evaluate_circuit(..., standard="NEC")` dispatches on the registry; existing NEC
  behavior preserved (regression-tested — currently 1016 tests green).
- Keep unit handling (AWG + mm²) shared.

## Cross-linking (SEO + UX)

Each page links to its siblings ("Building/premises wiring? Use the NEC
calculator. Boat? Marine (ABYC).") so users land on the right tool and Google
sees a connected cluster.

## Out of scope (for now)
- Three-phase / conduit-fill optimizers, aircraft (AC 43.13), IEC 60364.
