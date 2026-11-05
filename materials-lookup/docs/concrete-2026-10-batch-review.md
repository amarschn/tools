# October 2026 concrete batch

Date: 2026-10-31

This batch adds a **compressive strength** property, a **Concrete** family, **12
materials**, and **46 observations**. The catalog now contains 1,387 materials,
101 named states, 5,977 observations, 12 registered properties, and 560 source
references. No earlier record changed.

## What was added

| Material | Type | Source |
| --- | --- | --- |
| Ductal UHPC | Ultra-high performance concrete | FHWA-HRT-06-103, Table 2 |
| Forton VF-774 GFRC, premix and spray-up | Glass-fibre reinforced concrete | Forton bulletin |
| Sikacrete-650 Tecfast | Rapid repair concrete | Sika data sheet |
| StoCrete TS 108 | Sprayed mortar | Sto data sheet |
| StoCrete RM F, StoCrete SM | Repair mortars | Sto data sheets |
| SikaEmaco-488 CI, Sika MonoTop-112, SikaQuick Pro 1000 | Repair mortars | Sika data sheets |
| Flexcrete Monolite, Emer-Patch Repair 40 | Lightweight repair mortars | Manufacturer data sheets |

## Judgement calls

**Most of these are mortars.** Repair mortars publish density, modulus, and
strength together, and most ready-mix producers do not. Each description says
"not ready-mix concrete" where that applies. This batch does not represent
normal structural concrete, which is the largest remaining gap.

**Densities are not all the same measurement.** Sto, Sika MonoTop and Emer print
fresh density, Flexcrete prints mixed density, Sikacrete-650 prints hardened
density, Forton prints dry density, and SikaEmaco-488 CI does not say. Fresh
density usually runs higher than dry density, so these points are not strictly
comparable on a density axis. Each observation's note records the printed state.

**Compressive tests differ.** The sources use EN 12190, ASTM C 109, and BS 4551,
with different specimen shapes. Strengths from different methods are not directly
interchangeable. Each observation records its method.

**The Ductal values are manufacturer ranges reported by FHWA.** FHWA's own tests
in the same report measured 193 MPa and 52.4 GPa after steam treatment. Those are
not imported here, because that condition needs its own record.

**The Forton modulus sits under its flexural properties.** It is stored as
Young's modulus with a note saying so. The ranges are wide, and the bulletin says
each producer must test its own composite.

**Sikacrete-650 is a lower bound.** The sheet prints >85 MPa, so it plots as a
reported bound, not a measurement.

**SikaQuick Pro 1000 has no density.** It appears on charts without a density
axis, and in the Materials tool.

## Excluded

- **Köster Repair Mortar R4.** The sheet prints two different moduli.
- **Quikrete and Rapid Set mixes.** Reachable sheets give strength but no density
  or modulus, so a single value cannot plot.
- **Normal structural concrete and strength classes.** No reachable producer sheet
  or free standard gives all three values.

## Verification

Values were read from extracted page text. `import_concrete.py --check` rebuilds
the batch from hash-pinned private snapshots and compares it with the checked-in
files. `tests/test_concrete.py` covers the property, values, ranges, bounds, and
density labels.
