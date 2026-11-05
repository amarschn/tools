# October 2026 material catalog expansion

Date: 2026-10-03

This batch adds **1,072 distinct material identities and 4,033 observations**.
The catalog now contains 1,360 materials, 92 named states, 5,858 observations,
11 registered properties, and 537 source references. Every addition has
density and at least one other positive, sourced property. Taxonomy nodes,
aliases, color variants, and test conditions do not count as materials.

The baseline is commit `e46b6ae`: 288 materials represented by 656 authoring
records. All 656 records survive unchanged. Their ordered, normalized JSON
SHA-256 is recorded in `curated/catalog-expansion-2026-10.json` and checked by
the regression suite. The same ledger lists accepted identities, added source
IDs, and excluded entries with reasons.

| Class | Added materials | Source and scope |
| --- | ---: | --- |
| Metals | 486 | Copper Development Association public UNS alloy references; grade-level physical properties |
| Glasses | 249 | 102 SCHOTT compositions and 147 OHARA compositions; individual glass sheets |
| Polymers | 106 | 64 Mitsubishi Chemical Group engineering plastics and 42 Smooth-On formulations |
| Wood | 97 | USDA Wood Handbook Table 5-3a; additional hardwood and softwood species |
| Elastomers | 97 | Smooth-On silicone, polyurethane, and polysulfide comparison tables |
| Foams | 17 | Diab Divinycell HP, HT, and HCP technical datasheets |
| Ceramics | 16 | KYOCERA mechanical catalog, alumina and silicate/oxide/cermet grades |
| Synthetic composites | 4 | Hexcel HexPly 8552 woven AS4 and IM7 laminates |

Coverage is uneven because the sources differ. Copper alloys and optical
glasses supply large, consistently formatted grade catalogs. This is a sourced
reference collection, not a representative sample of all available materials
or a set of design allowables.

## Source review and exclusions

**Copper alloys.** The importer examines 940 public alloy pages. Existing UNS
designations are excluded before adding a grade. It imports only density,
tensile elastic modulus, conductivity, and specific heat from the physical
property table. Mechanical strength rows depend on temper and product form;
they are not imported as grade-wide strengths. Table headings and units must
match the reviewed layout. Density, conductivity, and specific heat retain the
reported 68 °F temperature. A missing modulus temperature remains missing.

Fourteen cells are deferred because their printed units or decimal placement
are implausible, or because tensile and shear moduli conflict. Examples include
C14750 specific heat of 90 Btu/(lb·°F), C18080 modulus of 185,000 ksi, and C90280
density of 8.81 lb/in³. The importer records the exact rejected literals and
reasons in `CDA_DEFERRED_CELLS` and the batch ledger. It does not repair them by
guessing a decimal or substituting another unit. A new outlier stops the import
for review. A grade losing its only usable property pair is excluded.

Each accepted public alloy page has its own snapshot hash. The downloader uses
public HTML, with two workers, caching, pacing, and bounded retries. It does not
use the authenticated CDA API. When a reviewed single-page download already
exists, both parsing and hashing use that same file rather than a later bulk
download.

**Optical glasses.** SCHOTT values come from each named sheet's Other
Properties panel. The source's 10³ N/mm² is converted to Pa, g/cm³ to kg/m³,
and J/(g·K) to J/(kg·K). Individual sheet revisions remain attached. Repeated
sheets and HT transmission variants are not new compositions for this batch.

OHARA values come from the April 2025 detailed-data collection. The May 2023
pocket catalog, printed page 85, defines its tabulated specific gravity as
density in g/cm³ to the reported precision. OHARA's separate Mechanical
Properties section 5.1 describes room-temperature elastic-wave measurements on
annealed rods. Both supporting references are pinned. Thermal conductivity is
read from the labeled row's actual cell; the PDF's interleaved optical columns
are not used as reading-order data. W/WN transmission variants of included
base glasses are excluded.

**Wood.** Table 5-3a, PDF pages 4–8 of the mechanical-properties chapter,
supplies specific gravity, bending modulus, and modulus of rupture at 12%
moisture. Density includes the water mass:

`rho12 = G12 × 1000 × (1 + 0.12) kg/m³`.

Here, `rho12` is density at 12% moisture and `G12` uses oven-dry mass divided by
volume at that moisture content. The conversion follows Wood Handbook Equation
(4-12), printed page 4-10, PDF page 89 of the full handbook. Density is marked
computed and retains the printed specific gravity. Bending modulus stays
`flexural_modulus`; no Young's modulus or shear correction is invented. The
values describe small clear specimens loaded along the grain. Douglas-fir
regions and redwood growth-age classes are not counted as separate species.
Redwood uses the old-growth row. Rows lacking specific gravity are excluded.

**Smooth-On formulations.** The source is the manufacturer's comparison chart,
using explicit property keys and units. The web chart does not consistently
state test method, specimen age, temperature, or the density specimen's
physical state. Those gaps remain explicit. Values are reference data; the
import does not apply conditions from an older bulletin to every web row.
Rubber stress at 100% strain is not Young's modulus. Separately labeled
six-ply laminate properties are not assigned to neat resin.

Review of the EpoxAcoat technical bulletin also caught laminate strengths in
web fields without a laminate label. That formulation is deferred because its
strength and density describe different specimens. EpoxAcast 655 and
Plasti-Paste EPOXY are deferred pending a verified cured-density pairing; their
bulletins identify mixed/coating density. Those review documents are pinned.
Color and cure-speed variants, regional aliases, additives, and cross-listed
products are excluded. Different hardness or additive formulations can remain
distinct even when a few rounded mechanical values coincide.

**Engineering plastics.** Mitsubishi Chemical Group's 2023 design guide,
PDF pages 15–22, supplies the ASTM material-selection columns. These are not
combined with the separate ISO tables. Regional names sharing a column become
aliases of one grade. The TIVAR 1000 color column is not another material.
Specific gravity converts to approximate density at the printed precision and
is marked computed. Tensile strength, tensile modulus, elongation, and flexural
strength preserve ASTM D638/D790 and the psi/ksi distinction. Specimens are
machined from stock shapes; row-specific conditioning and orientation are not
stated and remain unspecified.

**Foams.** The May 2026 HP Rev29, HT Rev17, and HCP Rev23 sheets supply nominal
values at 23 °C. The importer reads nominal and minimum rows separately and
imports nominal values only. HP60 and HT61 both report density of 65 kg/m³;
the grade number is not treated as density. Tensile strength and HP tensile
modulus retain ASTM D1623 and the through-thickness direction. HT and HCP
compression moduli are not relabeled as Young's modulus. The HM sheet was
reviewed but excluded because it lacks a second property supported by this
batch's property registry.

**Ceramics.** KYOCERA's PDF pages 8 and 10 have unambiguous grade columns and
test-method rows. New and old material codes are one identity. Density,
flexural strength, Young's modulus, conductivity, and specific heat preserve
JIS R 1634, R 1601, R 1602, and R 1611 as printed. Conductivity specifies 20 °C;
other rows do not gain an assumed temperature. More complicated panels were
left for a later review.

**Woven composites.** HexPly 8552 pages 3–4 identify four laminates by resin,
reinforcement, and weave. They use 37% resin by mass, cured laminate density,
and 25 °C dry tensile values in the 0° warp direction. Rendered panels were
checked for column alignment: AGP280-5H modulus is 67 GPa, SPG196-PW is 85 GPa,
and SPG370-8H is 86 GPa. Differences between the source's physical and mechanical
header spellings are retained in the notes. None is labeled quasi-isotropic.

## Reconstruction and publication

Original PDFs and HTML stay in the git-ignored `private-sources/` archive.
Published records, JSON, and CSV contain textual citations, exact source
literals, page/row locators, and hashes. Source documents and their URLs remain
outside the public build. Normal site builds use curated JSON and need no PDF
libraries or network connection.

Install the optional reconstruction dependencies from
`materials-lookup/requirements-ingest.txt`. The source manifest names accepted
snapshots; the private CDA discovery cache contains all 940 reviewed pages,
including rejected entries. Preserve that cache to reproduce the exclusion
ledger. The public downloader can obtain a fresh cache for a new review, but a
fresh download is not guaranteed to match the accepted snapshot.

From the repository root:

```sh
python3.13 materials-lookup/builder/import_catalog_expansion.py --source-dir private-sources --check
python3.13 materials-lookup/builder/import_ashby_families.py --pdf-dir private-sources --check
python3.13 materials-lookup/builder/build_site.py --output ../tools/materials
python3 scripts/build_material_selection.py
python3 scripts/inject_seo_meta.py
python3 scripts/generate_sitemap.py
python3.13 -m pytest
npm --prefix materials-lookup test
npm --prefix materials-lookup run test:browser
node tests/browser/ashby-envelopes.cjs
node tests/browser/materials-explorer.cjs
python3.13 materials-lookup/builder/verify_release.py
python3 scripts/build_material_selection.py --check
```

Without `--check` or `--apply`, the October importer writes a candidate to
`/private/tmp/materials-expansion-candidate.json`. `--apply` installs it only
when at least 1,000 distinct additions remain. Full reconstruction through
`import_reference_tables.py` includes this batch and requires every earlier
source archive as well. Rechecking the earlier 66-material batch preserves
later records, ordering, and retrieval dates.

To review this batch's originals without requiring archives from older batches:

```sh
python3.13 materials-lookup/builder/prepare_source_review.py \
  --pdf-dir private-sources \
  --batch-report materials-lookup/curated/catalog-expansion-2026-10.json \
  --output-dir /private/tmp/materials-source-documents-october-2026
```

The batch selection includes supporting method documents and reused sources.
Every selected hash must match before anything is copied. The review directory
must be outside the repository and the preview server's document root.

The Materials interface and all prototype pages are preserved. Both public
tools use the same expanded catalog. The Ashby chart still requires a usable
pair for the chosen axes: wood appears on bending charts and rubber on tensile
strength charts, with no inferred stiffness added to make a point appear.

## Verification results

The full Python run passed 1,691 tests and 2,611 subtests. A subsequent focused
run passed all 50 catalog/release tests after adding the private batch-review
check. Both source import checks reproduce the accepted records. Release
verification passed for 4,201 generated artifacts, and the chart projection
matches the lookup catalog.

The lookup's Node checks cover all 1,360 record projections and report a
12.76 ms search p95 on this machine. Its search index is 61,095 bytes gzip.
Browser checks passed on root and nested mounts, including new-material
searches across eight classes, source details, JSON/CSV, settings, and a
320-pixel layout. The Ashby browser suite passed with 1,024 default
stiffness–density pairs, 107 woods on bending axes, 107 elastomers on tensile
axes, and 29 foams on tensile axes. Both suites reported no browser errors.

The private review index contains 502 hash-verified originals, including reused
source and method documents. Earlier source archives are not all present on
this machine, so the full historical PDF importer was not rerun. The batch
checks and unchanged-baseline hash cover this expansion without replacing
those earlier facts.
