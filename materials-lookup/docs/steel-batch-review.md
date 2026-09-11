# Steel batch — 2026-09-10

Added **21 steel grades, 28 named states and 212 observations**. The catalog
now has **222 materials, 92 states, 1,593 observations and 28 sources**. All
465 previous authoring records and their 1,381 observations remain unchanged.

| Source and group | Grades | Observations |
| --- | ---: | ---: |
| Atlas carbon/free-machining bar | 5 | 45 |
| Atlas through-hardening alloy bar | 4 | 51 |
| Atlas case-hardening alloy bar | 3 | 24 |
| Atlas Micro900 | 1 | 3 |
| Uddeholm tool steels | 8 | 89 |

## Source review

The Atlas Technical Handbook of Bar Products was downloaded from the
publisher. Its front matter says January 2005, edition 1; the download filename
also mentions October 2011. The recorded publication date follows the printed
edition. No present availability or current-standard compliance is inferred.
PDF pages and printed pages differ by two in the selected Atlas sections.

The eight Uddeholm brochures are Arne, Rigor, Sverker 21, Orvar Supreme,
Stavax ESR, Carmo, Caldie and Dievar. Their editions were checked in the
documents, including May 2026 for Stavax ESR and September 2026 for Dievar.
All nine new documents are pinned by URL, size and SHA-256 in the source
manifest. Relevant tables were checked visually alongside text extraction.

Only selected numeric facts and attribution are stored in Git. Whitespace
grouping and decimal commas in selected tool-steel numbers are normalized
to decimal-point notation; numerical values are retained. For whole-MPa
modulus entries such as 210 000, trailing integer zeros do not establish extra
measured precision: the literal is retained but displayed significant figures
are conservative, avoiding an unjustified 210.000 GPa display.
The originals remain in the private review directory outside the repository.

## Engineering steel decisions

- M1020, M1030, 1045, 1214FM and 12L14FM: selected cold-drawn rows from
  sections 4.1.4–4.5.4, PDF pp. 31/33/35/38/40. The handbook labels these
  values as minima but explicitly disclaims guaranteed mechanical properties.
  Preserve them as `lower_bound` results with `typical` basis. The app labels
  them “Typical minimum (not guaranteed)”; they are not measured point values
  or contractual supply minima. Elongation uses the printed 50 mm gauge.
- M1020 and M1030 remain merchant grades. They are not aliases for SAE 1020
  and 1030. D3/D4/D6/D12/D13 special-order grades and alternative chemical
  standards are not created as extra identities. Turned/polished and combined
  hot-finished rows are outside this batch.
- 4140, 6582 (34CrNiMo6), 4340 and 6580 (30CrNiMo8): sections
  4.6.4–4.9.4, PDF pp. 42/45/48/51. Supply minima and specified tensile
  intervals retain their diameter limits. For 4140, the exact condition U/T
  labels are in the locators and notes. Approximate AS1444 comparisons for the
  other grades are not asserted as equivalent heat treatments or standards.
- 8620H, 6587 (18CrNiMo7-6), and 6657 (14NiCrMo13-4): sections
  4.10.6–4.12.6, PDF pp. 55/56/59. These are typical **core** properties
  after carburizing, hardening and tempering at the stated test-section
  diameters, not properties of the case or the annealed supply state. The
  En36A comparison is excluded. No yield value is invented for 6657.
- Micro900 (38MnSiVS5): section 4.13.4.1, PDF p. 60. The state is
  thermomechanically rolled, diameter up to 150 mm. The optional plain
  as-rolled product is not assigned these mechanical properties.
- Diameter limits and exclusive lower boundaries remain exact text in each
  observation's notes and locator. They are not placed in the thickness field
  or converted to falsely inclusive diameter intervals. Structured diameter
  filtering remains a future schema extension. Test temperatures and yield
  offsets are not invented when absent from the tables.

## Tool steel decisions

- Physical tables: Arne p. 3, Rigor p. 4, Sverker 21 p. 3, Orvar Supreme
  p. 4, Stavax ESR p. 4, Carmo p. 4, Caldie p. 3 and Dievar p. 4.
  These are condition-specific properties, not generic grade-wide values or
  soft-annealed delivery properties. Density, modulus, conductivity and specific
  heat retain each printed temperature. Missing cells remain absent.
- Arne/O1, Rigor/A2 and Sverker 21/D2 physical data is at 62 HRC. Orvar
  Supreme/H13 physical data is at 45 ±1 HRC; Stavax ESR (420 modified) is at
  50 HRC. The measured heat-treatment state stays separate from AISI aliases.
- The named `hardness_condition` attribute preserves source HRC/HB labels,
  including intervals. This is not a new numeric hardness property, an inferred
  hardness conversion, or a claim that all heat treatments yielding the same
  hardness produce identical properties. Full stated cycles remain in notes.
- Orvar Supreme has four additional tabulated tensile observations at 45 and
  52 HRC. These are separate from the 45 ±1 HRC physical-table state.
- Stavax ESR conductivity retains the footnote about possible ±15% measurement
  scatter. No statistical distribution or standard deviation is inferred.
  Only its two tensile-strength entries are imported from the mechanical
  table: the additional row headed “Modulus of elasticity” is inconsistent
  with the physical table and is deferred, rather than relabelled as yield.
- Carmo physical data applies to the 240–270 HB delivery condition. Its three
  tensile observations apply to 270 HB specifically. They are separate states.
- Caldie's physical state is 60–61 HRC. Dievar's physical state is 44–46 HRC;
  its nine tensile observations at 44/48/52 HRC retain the short-transverse
  orientation. The physical-table tempering cycle is not copied to the
  different-hardness tensile rows. “Room temperature” stays unquantified.
- Compressive strengths, hardness/strength conversions, impact charts,
  tempering graphs and application ratings are outside this batch. In
  particular, compressive proof strength is not imported as tensile yield.

## Integration and private review

The new Steels category includes carbon, alloy, tool and existing stainless
families. Existing stainless URLs and material identities are preserved.
Original Prototype 05 files, layout and styles remain unchanged. The only
observation-label adjustment makes typical lower bounds explicit.

`scripts/import_reference_tables.py --pdf-dir /private/tmp --check` reconstructs
all 28 snapshots, including `scripts/import_steel_grades.py`. The private
review index is `/private/tmp/materials-source-documents/index.html`; this is
temporary storage, not a durable archive. Public output and exports still
contain text citations only. Paid document access remains a separate milestone.

This is a documented source review, not an independent second-person audit.

Verification: 140 Python tests, 52 release search checks and 21 prototype
golden queries pass, with compiler/browser parity across all 222 records.
Browser checks cover the new steel taxonomy, typical-minimum labels, size and
hardness scope, root/nested hosting and 320px layouts without console or page
errors. All 28 source snapshots reconstruct the import and all 775 public
artifacts pass freshness, hash and source-document exclusion checks.
