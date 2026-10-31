# Ashby chart material additions

Date: 2026-10-01

The batch adds 66 distinct material identities and 232 observations. Earlier
authored material records remain unchanged. Catalog totals are 288 materials,
92 named states, 1,825 observations, 11 registered properties, and 39 sources.
The Materials lookup keeps its approved interface; the chart reads a generated
projection of the same catalog.

| Family | New identities | Primary references |
| --- | ---: | --- |
| Synthetic composites | 11 | Toray 3900, 2511, and 2700 prepreg sheets; Hexcel HexPly 8552 European sheet |
| Wood | 10 | USDA Wood Handbook, FPL-GTR-190, Table 5-3a and Equation (4-12) |
| Ceramics | 13 | KYOCERA Fineceramics Europe material comparison table |
| Foams | 12 | Diab Divinycell H Rev26 and F Rev33, May 2026 |
| Elastomers | 10 | Smooth-On Technical Reference Chart, silicone and urethane rubber |
| Glasses | 10 | SCHOTT Optical Glass Datasheets, 2025 collection |

## Source review

All eleven original snapshots were retrieved on September 30, 2026. Filenames,
SHA-256 hashes, retrieval dates, and document revisions are pinned in
`builder/import_ashby_families.py` and the curated source manifests. PDF tables
were checked against rendered pages, including their headers and footnotes.
The KYOCERA values come from its embedded comparison table. Public records and
exports retain textual citations and page/table locators; document URLs and
original documents remain excluded.

The importer rejects any snapshot whose hash differs. Its small explicit tables
preserve the source strings and conversion factors. This batch does not count
alternate names, colors, product forms, or test conditions as new materials.

## Property decisions

**Composites.** Each identity specifies the resin system and reinforcement.
Density is the cured laminate density, never the neat resin or dry fiber value.
Tensile properties retain their 0° or 90° direction and the supplier cure notes.
Toray 2700 uses only the oven-cured columns, not a mixture of oven and press
data. Hexcel values use the 25 °C dry columns at 35% resin mass fraction and
134 g/m² fiber areal weight. None is labeled quasi-isotropic.

**Wood.** The ten species use small clear specimen data at 12% moisture content
on an oven-dry mass basis. Table 5-3a specific gravity uses oven-dry mass and
volume at 12% moisture. Density therefore includes the water mass:

\[\rho_{12}=1000\,G_{12}(1+0.12)\quad\text{kg/m}^3.\]

Here, rho12 is density at 12% moisture and G12 is the table's specific gravity.
The factor follows Equation (4-12), Chapter 4, printed page 4-10 (PDF page 89
of the complete handbook). Density is labeled computed, with G12 preserved as
the source literal. Modulus of elasticity from the bending test is stored as
`flexural_modulus`; no 10% shear correction or inferred tensile modulus is
applied. Modulus of rupture remains flexural strength. Table 5-3a is on PDF
pages 4 and 7 of the separately published mechanical-properties chapter.

**Ceramics.** Thirteen KYOCERA grades supply density and elastic modulus.
Reported density intervals and ≥ bounds remain intervals and lower bounds.
The supplier describes these as typical laboratory samples, so a ≥ value is
not promoted to a guaranteed minimum. AL24 and AL25 lack modulus and are outside
this batch. The web table's specific-heat units are ambiguous and were excluded.

**Foams.** Eight Divinycell H and four F grades retain nominal average values.
H45 has a reported density of 48 kg/m³; its name is not used as a density value.
H modulus is tensile modulus from ASTM D1623, measured through the thickness.
The F sheet supplies compressive modulus but no tensile modulus, so F grades
appear in strength-density comparisons without invented Young's moduli. The
F density tolerance and flatwise tensile specimen notes remain attached.

**Elastomers.** Five silicone and five polyurethane formulations retain tensile
strength, density, and elongation. Smooth-On states measurement after seven
days at 23 °C. Tensile strength is converted from psi to Pa, elongation from
percent to a ratio, and printed g/cc density to kg/m³. Stress at 100% strain
and Shore hardness are not treated as small-strain Young's modulus.

**Glasses.** Ten named optical compositions retain density, elastic modulus,
Poisson's ratio, conductivity, and specific heat. The source's elastic-modulus
unit, 10³ N/mm², converts to GPa; J/(g·K) converts to J/(kg·K). Each sheet's
revision is retained, including N-FK51A dated December 1, 2023. These property
rows do not state a test temperature, so none is invented.

## Chart integration

The source classification accompanies each material in the derived chart
projection so subgroup shapes do not require a second material database.
Reported bounds are excluded from those shapes. The chart exposes bending
modulus as a separate axis, and suggests alternate axes for materials whose
selected properties are absent.

Titanium was missing because density at 22 °C did not pair with modulus at
20 °C. The projection now permits comparisons within 20–25 °C and records both
temperatures. Known conditions outside that band must match exactly; material
states, product forms, thicknesses, and directions keep their existing checks.
No source observation or recorded temperature is changed by this pairing rule.

## Reproduction and verification

From the repository root, with all eleven pinned snapshots in `private-sources/`:

```sh
python3.13 materials-lookup/builder/import_ashby_families.py --pdf-dir private-sources --check
python3.13 materials-lookup/builder/build_site.py --output ../tools/materials
python3 scripts/build_material_selection.py
python3 scripts/inject_seo_meta.py
python3.13 -m pytest materials-lookup/tests/test_ashby_families.py tests/test_material_selection.py
node tests/browser/ashby-envelopes.cjs
node tests/browser/materials-explorer.cjs
```

Omit `--check` to regenerate this batch. This path preserves earlier curated
records and does not require their original PDFs. Reconstructing every batch
through `import_reference_tables.py` requires the full archive of earlier
source snapshots. Normal site builds need neither PDFs nor network access.

Regression checks cover the six family counts, source-unit conversions,
wood moisture and modulus distinctions, foam and rubber exclusions, laminate
density and cure selection, ceramic bounds, titanium temperatures, private
source documents, chart geometry, and browser interactions.
