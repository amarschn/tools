# October 2026 wood batch

Date: 2026-10-31

This batch adds **235 observations to the 107 existing wood species** and no new
materials. The catalog now contains 1,453 materials, 101 named states, 6,410
observations, 12 registered properties, and 585 source references. No earlier record
changed.

Every value comes from one document already pinned in the manifest: USDA Forest
Products Laboratory, Wood Handbook FPL-GTR-190, Chapter 5, 2018 errata
(`usda-wood-mechanical.pdf`).

## What was added

| Property | Species | Basis | Source |
| --- | ---: | --- | --- |
| Young's modulus along the grain | 107 | Computed | Table 5-3a bending modulus, 12% moisture, plus 10% |
| Compressive strength along the grain | 107 | Reference | Table 5-3a, compression parallel to grain, 12% moisture |
| Tensile strength along the grain | 21 | Computed | Table 5-7, tested green, adjusted to 12% moisture |

Without these values wood had no Young's modulus or tensile strength, so it was
missing from the two default Ashby charts.

## Judgement calls

**Young's modulus is computed, and says so.** The handbook prints a bending modulus
that includes shear deflection. Table 5-3a footnote c says the modulus can be
increased by 10% to correct for this, and the footnote to Table 5-1 says the
along-grain modulus may be approximated the same way. The record keeps the printed
bending value as its source literal, with `basis: computed`. The printed value also
stays on the separate `flexural_modulus` property, so nothing is overwritten.

**Tensile strength is adjusted from a green test.** Table 5-7 tests green specimens.
Every other wood value in the catalog is at 12% moisture, and pairing a green strength
with a 12% density would mix two states on one point. Footnote a gives average
adjustments of 32% for hardwoods and 13% for softwoods. Those are class averages, not
measurements on the species, and the notes say so. The source literal remains the
printed green value.

**Compressive strength is read directly.** Footnote a defines compression parallel to
grain as maximum crushing strength.

**Wood is anisotropic, and these are along-grain values.** All three properties carry
`orientation: L`. Comparing them with isotropic materials is the usual Ashby chart
convention, but a design loaded across the grain has far lower values.

## How the numbers were checked

Table 5-3a was read by column position. The bending modulus and bending strength in
each matched row had to match the values already in the catalog, which fixes the row.
The compression values were then converted to compare with the separately printed
inch-pound Table 5-3b. Of 107 species, 104 agree within 1.2%.

The other three differ inside the handbook, and the metric values were used:

| Species | Table 5-3a | Table 5-3b | Difference |
| --- | --- | --- | --- |
| Butternut | 36,200 kPa | 5,110 lbf/in² (35,230 kPa) | 2.7% |
| Western hemlock | 49,000 kPa | 7,200 lbf/in² (49,640 kPa) | 1.3% |
| Western white pine | 34,700 kPa, G = 0.35 | 5,040 lbf/in² (34,750 kPa), G = 0.38 | Compression agrees; specific gravity differs |

The Western white pine specific gravity difference affects the density already in the
catalog from Table 5-3a, which this batch leaves alone.

## Left out

- Cedar elm in Table 5-7: no Table 5-3a row, so the catalog has no such species.
- Douglas-fir, interior north, in Table 5-7: the catalog keeps Coast Douglas-fir.
- Redwood in Table 5-7: printed as virgin and young growth, while the catalog keeps
  old-growth redwood. The chapter does not state that the labels mean the same thing.
- Compression and tension across the grain: a different direction from the values
  plotted on these axes.
