# Nonferrous metal batch — 2026-09-10

Added **43 material identities, 27 named states and 243 observations**. The
catalog now contains **201 materials, 64 states, 1,381 observations and 19
source documents**. All 348 existing authoring records, including their 1,138
observations, are unchanged as structured data. Alternate names, tempers and
product forms are not counted as additional materials.

| Source | New grades | Observations | Reviewed pages |
| --- | ---: | ---: | --- |
| Hydro, eight alloy datasheets | 11 | 136 | Alloy density on pp. 1/2; extrusion limits on p. 2 |
| thyssenkrupp Copper and Brass Sales, Copper and Alloys guide | 30 | 86 | PDF p. 76, printed p. 74 |
| TIMET, TIMETAL 6-4 | 1 | 10 | p. 1, Tables 1/2 |
| TIMET, TIMETAL 6-2-4-6 | 1 | 11 | p. 1, Tables 1/2/3 |

The source manifest records the exact publisher URLs, byte counts and SHA-256
pins. The manufacturer directory used for Hydro is its
[North America alloy data sheets](https://www.hydro.com/us/us/aluminum/products/extruded-profiles/north-america-resources/north-america-alloy-data-sheets/).
The 6063 source is the June 2026 revision. No current availability claim is
inferred from any source. Original tables were reviewed visually alongside PDF
text extraction. This review is not an independent second-person audit.

## Aluminum

Grades: 1060, 1100, 1350, 6005, 6105, 6005A, 6042, 6063, 6082, 6101 and 6262.
The existing 6061 data remains unchanged.

- Density is alloy-wide. It has no temper, product form or invented temperature.
  The source lb/in³ values are converted without rounding the canonical store.
- Standard tempers are separate states. Mechanical strengths use the printed
  MPa column, with specified minima and specified intervals kept distinct.
  Thermal conductivity is explicitly typical at 25 °C. Unqualified physical
  values use the `reference` basis, without an implied statistical meaning.
- Thickness follows the source inches column, converted exactly to metres.
  Its original bounds remain in each citation. The metric columns often use
  nominal rounded boundaries; they are not mixed with the inch boundaries.
- The elongation footnote exempts shapes thinner than .062 in and specimens
  that cannot accommodate a standard test. The structured elongation thickness
  starts at .062 in, and the specimen exemption remains in the notes. The
  printed 2 in / four-diameter gauge length is retained where supplied; it is
  not inferred for 6262. Missing 1350/6101 elongations remain absent.
- O, H111 and H112 are temper designations, not invented generic heat treatments.
  Selected base tempers from shared T5/T5511 and T6/T6511 rows are imported only
  as T5 or T6; stress-relieved variants are not inferred as additional states.
- Deferred: 6063-T6's second thickness row (1.000 in versus 12.50 mm upper
  bound), 6042's first row (missing inch lower bound versus 10.00 mm), and
  6101-T61/T65 rows with inconsistent dimensional columns. Other unselected
  standard tempers, special tempers, comparison grades and cold-finished rows
  are outside this batch. 1050 has only density in this source and is deferred.

## Copper family

Imported 30 distinct C-number grades, including C11000, C17200, C26000, C36000,
C46400, C51000, C65500, C71500 and C75200. Brasses and bronzes have their own
taxonomy branches beneath copper alloys.

- These are supplier catalog reference values, not manufacturer mechanical
  allowables. The source type is `supplier_catalog`, and the basis is
  `reference`. No annealed or work-hardened state is assigned to physical data.
- Density, conductivity and specific heat retain their 68 °F (20 °C)
  temperature and original imperial literals, including leading decimals.
  C11000 density and C17200/C17300 conductivity remain intervals.
- Conversion constants: 27,679.904710203122 kg/m³ per lb/in³,
  1.730734666295328 W/(m·K) per Btu/(ft·h·°F), and
  4,186.8 J/(kg·K) per Btu/(lb·°F).
- C18200 conductivity spans 68–212 °F, so it is excluded rather than assigned
  to 20 °C. Missing specific heats remain absent. A945, C97 and the sparse
  C67300 row are deferred; C99 is not counted separately from C18700.

## Titanium

- Ti-6Al-4V is the base ASTM Grade 5 identity. ELI and Ru variants are not
  manufactured from a shared physical-property table as extra identities.
  Table 2 conductivity belongs to the mill-annealed state. Specific heat and
  modulus retain their individual temperatures, and modulus intervals retain
  the texture/heat-treatment qualification. Strength charts are not digitized.
- Ti-6Al-2Sn-4Zr-6Mo retains UNS R56260. Table 2 specific heat has no stated
  temperature; none is inferred. Conductivity over 20–25 °C is deferred.
- Table 3's duplex-annealed ≤2.00 in and solution-treated-and-aged ≤2.50 in
  rows retain the rod-diameter-or-thickness restriction in their notes and
  locators, plus heat-treatment cycles and 20 °C test temperature. A rod
  diameter is not incorrectly stored as a thickness-only condition. Larger
  sizes and their directional footnotes are outside this batch.

## Contract and release

The factual adapter explicitly maps the new tempers and heat treatments.
Condition intervals may contain one null endpoint only when the condition
registry enables `nullable_bounds`. Null means the source supplies no limit;
it does not mean zero. Both-null, reversed and nonnumeric intervals fail
validation. Observation result intervals still require two finite bounds.
Thickness displays in mm or inches using the existing unit-system control.
The Prototype 05 layout, styles and original prototype files are unchanged.

`scripts/import_reference_tables.py --pdf-dir /private/tmp --check` reconstructs
all 19 source snapshots, including `scripts/import_nonferrous_metals.py`.
The private review index was refreshed at
`/private/tmp/materials-source-documents/index.html`. These temporary originals
remain outside Git and the preview root; they are not a durable archive.
The public artifact and exports retain text citations only.

Verification: 134 Python tests, 37 release routing checks and 21 prototype
golden queries pass. Browser checks cover root and nested hosting, the bronze
tree, new material/state searches, thickness units, source intervals and 320px
layouts, without console or page errors. All 700 generated artifacts pass the
release gate. The running preview on port 8001 serves the same build manifest.
