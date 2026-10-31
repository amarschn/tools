# October 2026 chart staples batch

Date: 2026-10-30

This batch adds **15 material identities and 73 observations**, and gives 8
existing grades the values they needed to plot on the Ashby stiffness chart.
The catalog now contains 1,375 materials, 101 named states, 5,931 observations,
11 registered properties, and 549 source references. No earlier record changed:
an existing grade gains values through a new reference record beside it.

## Why it exists

Before this batch, the default stiffness chart (density against Young's modulus)
had 503 metal points and 447 of them were copper alloys. It had no aluminium, no
carbon or alloy steel, and no magnesium. The older 60-material chart had all of
these, so the move to the curated catalog would have removed them from the
public chart.

## What was added

| Material | Source | Values |
| --- | --- | --- |
| Aluminium 7075, 2024, 5052 | MIL-HDBK-5J | Density, modulus, ultimate and yield limits |
| Magnesium AZ31B | MIL-HDBK-5J | Density, modulus, ultimate and yield limits |
| Inconel 718, 625 | MIL-HDBK-5J | Density, modulus, ultimate and yield limits |
| Titanium CP-3 | MIL-HDBK-5J | Density, modulus, ultimate and yield limits |
| Stainless steel 17-4PH | MIL-HDBK-5J | Density, modulus, ultimate and yield limits |
| Steel AISI 1025 | MIL-HDBK-5J | Density, modulus, ultimate and yield limits |
| Steel AISI 1018 | Elgin Fastener Group data sheet | Density, modulus, typical cold drawn strengths |
| TECAFINE HDPE natural | Ensinger product page | Density, modulus, yield strength |
| Plexiglas G (PMMA) | Altuglas/Arkema brochure | Density, modulus, strengths, elongation, Poisson's ratio |
| Vectorply E-LTM 1808 (GFRP) | Vectorply data sheet | Density, modulus, tensile strength |
| SCHOTT BOROFLOAT 33 | SCHOTT data sheet | Density, modulus, Poisson's ratio, conductivity |
| Pilkington soda-lime float glass | Pilkington ATS-129 | Density, modulus, Poisson's ratio, conductivity, specific heat |

Existing grades that gained values:

| Grade | Added | Source |
| --- | --- | --- |
| Aluminium 6061 | Modulus | MIL-HDBK-5J Table 3.6.2.0(b2) |
| Aluminium 6005A, 6063, 6082, 6262 | Modulus | Aalco T6 extrusion datasheets |
| Steel Atlas 4140, 4340 | Density, modulus | MIL-HDBK-5J Table 2.3.1.0(g2) |
| Steel Atlas 8620H | Density, modulus | Elgin AISI 8620 fact sheet |

## Judgement calls

**MIL-HDBK-5J is cancelled.** MMPDS replaced it and is not free. The cancelled
edition is public, carries exact table locators, and its density and modulus
values remain ordinary reference data. Strength rows are A or S basis minimums
for the stated form and thickness, stored as lower bounds. They are not current
design allowables.

**Values cross a supplier boundary in three places.** The Atlas grades are bar
products from one supplier, and their new density and modulus come from generic
AISI 4140, 4340 and 8620 entries. Each observation says so. Density and modulus
vary little across these steels, and the selection code already treats them as
grade-level physical properties. Strengths are never carried across this way.

**The Elgin 8620 modulus is labelled "typical for steel" in the source.** It is
kept with that wording.

**The Vectorply laminate may be predicted, not tested.** The sheet's disclaimer
warns that laminate values may be computer-generated predictions, and it is a
0°/90° biaxial fabric with chopped mat rather than a unidirectional laminate. It
was the best reachable E-glass source with density, modulus, and strength
together. The material description and each condition note carry this warning.

**Aalco's alloy-level modulus sits on T6 temper pages.** Aalco lists it as a
physical property of the alloy, so it is stored at grade level. Alloy density
stays with the existing Hydro records.

**Plexiglas G is a 2002 brochure.** Its values are averages at 0.236 in nominal
thickness and its own footnote says not to use them for specification.

**Two sources are hosted by someone other than the publisher.** The BOROFLOAT 33
sheet came from Edmund Optics and the E-LTM 1808 sheet from Rock West Composites.
Plexiglas G came from Alro. The citations name the publisher.

## Still missing

These stay off the stiffness chart because no reachable document gives
alloy-specific values. Nothing was estimated to fill them.

- **ASTM A36.** SSAB publishes its strengths, but no accessible document gives
  a density and modulus for it. AISC and FHWA downloads were refused.
- **Aluminium 1060, 1100, 1350, 6005, 6042, 6101, 6105.** No alloy-specific modulus.
- **Steel Atlas 1045, 1214FM, 12L14FM, M1020, M1030, 6580, 6582, 6587, 6657,
  Micro900.** No grade-specific density and modulus. The Atlas handbook now
  sits behind a bot check, which was not bypassed.

Other materials from the older chart were outside this batch: 440C, LDPE,
polystyrene, polyester, Kevlar, concrete, and natural rubber. Copper alloys still
outnumber every other metal class.

## Verification

Every number was read from a rendered page or the pinned HTML before
transcription. `import_chart_staples.py --check` rebuilds the batch from the
hash-pinned private snapshots and compares it with the checked-in files. Tests
in `tests/test_chart_staples.py` cover the values, states, sources, and the rule
that no earlier record changes.
