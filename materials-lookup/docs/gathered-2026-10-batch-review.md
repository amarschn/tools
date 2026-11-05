# October 2026 gathered documents batch

Date: 2026-10-31

This batch adds **66 materials and 198 observations**, and gives 5 existing
aluminium grades a modulus. The catalog now contains 1,453 materials, 101 named
states, 6,175 observations, 12 registered properties, and 585 source references.
No earlier record changed.

The owner gathered 14 documents by hand, because automated downloads were refused.
Several came from web archives, and their citations record the archive address.
Originals are in `private-sources/`, renamed to the flat naming scheme. The owner's
index is in `private-sources/intake-2026-10-31/`, including `moved-files.tsv`.

## What was added

| Material | Records | Source |
| --- | ---: | --- |
| High-strength concrete by composition and strength level | 39 | MN/RC 1998-11, Tables 7.3-A and 7.3-B |
| LDPE | 4 | ExxonMobil LD 150013.BA, LD 2119.LN, LD 33021.07; Plastics International |
| Polystyrene | 5 | Styrolution PS 158K; Kumho GP 125, 125E, 125EB, 150I |
| Unsaturated polyester | 4 | Crystic 198; Polynt Norsodyne, Enydyne, Distitron |
| Natural rubber | 3 | APSOparts NR 40.75-01 and NR 60.01-02; TSE Industries |
| Kevlar yarn | 2 | DuPont Technical Guide, Table II-1 |
| Kevlar, E-glass and carbon epoxy laminates | 6 | ACP Composites reference table |
| ASTM A36 | 1 | AISC 360-16, SSAB, Bushwick Metals |
| C45 / AISI 1045 | 1 | Weerg |
| 440C | 1 | Suppliers Online |
| Modulus for aluminium 1060, 1100, 1350, 6005, 6101 | 5 existing | ASM Handbook Volume 2 |

The batch also adds a **Fibers** family and a chart preset of stiffness against
compressive strength, because the concrete study has no densities.

## Judgement calls

**The concrete points are group averages.** Tables 7.3-A and 7.3-B average the
modulus of mixes that fall in a strength level, by cementitious composition and by
moisture condition when tested. The strength is that level, stored as an interval,
not a measured strength. The per-mix Appendix A and B tables are rotated scans and
were not transcribed; doing so would add many more real points. The importer checks
that each cell's psi and GPa values agree, which guards against misreading the scan.

**The concrete study reports no density for these groups.** None was calculated.
They appear on charts without a density axis, including the new preset. Normal
structural concrete below about 41 MPa is still missing.

**ASM's page layout misleads text extraction.** On printed page 65, "62 GPa" sits
directly above the 1350 heading but belongs to alloy 1199. The 1350 value is 69 GPa,
on page 66. All five ASM values were read from rendered pages.

**A36 draws on three documents.** AISC 360 gives a modulus for structural steel in
general, SSAB gives plate strengths, and a distributor gives density. Each note says
so. Bushwick also prints 29,000 ksi, which agrees.

**C45 is a stand-in for 1045.** Weerg's sheet lists C45 and AISI 1045 as equivalents,
but it comes from a machining service, not a mill. Steel Atlas 1045 stays off the
stiffness chart, because neither Atlas document gives its density or modulus.

**440C's modulus has no printed unit.** The page says 29. 10⁶ psi is inferred from
the magnitude and the note says so. The same page says it has no mechanical data.

**The Kevlar table contradicts itself once.** Table II-1 prints Kevlar 49 modulus as
6.3 x 10⁶ psi beside 112,400 MPa. Table II-2 prints 16.3, which matches. The MPa
values are used. These are dry yarn values, not laminate values, so they plot far
above the laminates.

**Polynt densities are left out.** Each sheet's specific weight is for the liquid
resin. Crystic 198 prints a cured value of 1.22, and its liquid value of 1.11 shows
how far apart they are. Polynt resins plot only on charts without a density axis.

**APSOparts NR 40.75-01's elongation is left out.** It prints 26%, which is
implausible for 40 Shore A natural rubber, and the sister sheet prints 500%.

**The ACP laminates are generic.** Its table says it is for reference only and not a
guarantee of performance. These are the only laminates with compressive strength.

**Natural rubber has no Young's modulus.** None of the sources prints one, so rubber
plots on strength charts only, like the other elastomers.

**LDPE tensile strength at break is below yield on two ExxonMobil grades.** That is
what the sheets print, and each note says so.

**Styrolution PS 158K comes from a third-party copy** hosted by plasticker.de, because
the publisher's copy was not reachable.

## Still missing

- **Normal structural concrete with density.** No reachable source gives all three.
- **Aluminium 6042 and 6105.** No reachable modulus.
- **Steel Atlas 1045, 1214FM, 12L14FM, M1020, M1030, 6580, 6582, 6587, 6657, Micro900.**
  The Atlas documents give neither density nor modulus for them.
- **Compressive strength for metals, ceramics, foams, wood and plastics.** Kyocera,
  Diab, Toray, USDA and Mitsubishi documents already held contain it.

## Verification

The Kevlar, ACP, ASM and concrete tables were read from
rendered pages. Other PDF values were read from extracted text, and web values from
pinned HTML. `import_gathered.py --check` rebuilds the batch from hash-pinned
snapshots. `tests/test_gathered.py` covers values, flags and exclusions.
