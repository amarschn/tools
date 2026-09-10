# Source access and catalog expansion

Decision: 2026-09-10, at the user's request.

## Public release

Keep the current material/property lookup and numerical exports public. A
material's app-generated record is separate from the manufacturer's original
datasheet. Preserve the Prototype 05 interface.

Publish only textual source references: publisher, document title, revision,
page/table locator, source literal, and snapshot hash. Remove original-document
links from the UI and from every JSON/CSV download. Do not ship source PDFs,
document copies, previews, embedded viewers, storage paths, or download URLs.
Enforce this at compilation and release verification, not just in the UI.

## Owner review now

Keep pinned originals and a local review index outside the repository and the
preview server's document root. They remain available to the owner without
being an app feature. The repository stores selected facts and reproducible
import instructions; it does not store source-document binaries. Ignore common
document extensions and reject tracked documents during release verification.

## Paid document access later

- [ ] Review distribution rights for each document before offering hosted
  copies to customers; record allowed uses and revisions privately.
- [ ] Choose durable private object storage, with public access disabled, and
  keep the document-to-object mapping on the server.
- [ ] Add sign-in, billing, and server-side paid-entitlement checks for every
  document request. Fail closed for anonymous, unpaid, expired, or revoked
  accounts.
- [ ] Serve authorized downloads through the server or short-lived signed URLs;
  prevent public/shared caching and avoid permanent document links in the app.
- [ ] Test direct requests, entitlement expiry, cancellation, URL expiry, and
  cache behavior before enabling the feature.

The static release has no customer-document endpoint. Publisher websites remain
outside this application's access controls. Public Git history can retain old
publisher URLs; removing public-build links does not make publisher-hosted
documents private. Do not rewrite history without separate authorization.

## Catalog expansion

Add a bounded batch from primary manufacturer tables or clearly identified
supplier reference tables, prioritizing gaps beyond
the existing engineering plastics, technical ceramics, and basic stainless
grades. Pin each downloaded snapshot by SHA-256. Keep exact printed numbers,
units, page/column locators, conditions, and statistical meaning. Avoid counting
alternate names or product forms as new materials. Review table footnotes and
represent grade-wide physical data separately from condition-specific limits.

Acceptance: new identities resolve in search and category trees, imports
reconstruct the checked-in facts, old facts survive, and the expanded release
still passes the document-exclusion gate. Broader source coverage and the
10,000-identity performance milestone remain separate follow-up work.

## Completed batch — 2026-09-10

Public document exclusion and the private local review index are implemented.
The reviewed batch adds **24 materials and 298 observations**, bringing the
catalog to **158 materials, 37 named states, and 1,138 observations**. Eight
source snapshots are pinned; the original 840 observations are unchanged.

| Manufacturer range | Added identities | Added values | Reviewed tables |
| --- | ---: | ---: | --- |
| [Outokumpu Forta](https://www.outokumpu.com/en/products/product-ranges/forta) | 7 | 49 | Table 5, p. 9; Table 9, p. 12 |
| [Outokumpu Therma](https://www.outokumpu.com/en/products/product-ranges/therma) | 10 | 204 | Tables 5/7, p. 8; Table 14, p. 11 |
| [Outokumpu Ultra](https://www.outokumpu.com/en/products/product-ranges/ultra) | 7 | 45 | Table 10, p. 12; Table 13, p. 14 |

Review decisions:

- Forta DX and EDX 2304 are distinct supplier products despite shared EN/UNS
  numbers. EDX limits use MDS-D35; its elongation is A5, not A80. Coil is retained
  as a product form. Generic duplex averages are not copied onto every grade.
- Therma values retain each temperature, including 600/1000 °C modulus and
  500/800 °C conductivity. Elevated-temperature Rp0.2 and Rm are minimum limits,
  based on the source's EN 10028-7 footnote. Rp1.0, creep strength, and guidance-
  only maximum application temperatures are outside this batch.
- Ultra Alloy 825 belongs under nickel alloys; 2.4858 is recorded as DIN, and
  mechanical values retain the ISO 6208 footnote. Ultra 317L is not assigned the
  conditional EN 1.4438 plate designation. Ultra 6XN remains one supplier grade
  with both printed UNS aliases. Its revision caveat remains in the method.
- Ultra elongation retains the thickness-dependent gauge-length footnote;
  physical values have no cold-rolled state. Ultra 725LN has four physical
  observations and no invented cold-rolled state. Table 13's conductivity
  exception for Ultra 654 SMO is attributed to Outokumpu.

`scripts/import_reference_tables.py --check` reconstructs all eight pinned
snapshots through the existing importer and `scripts/import_specialty_metals.py`.
Pins reject silent document revisions. Publisher prose, document images, and
full datasheets are not checked in or included in the public artifact.

## Additional metals — 2026-09-10

Added 43 nonferrous identities and 243 observations: 11 aluminum grades, 30
copper-family grades and two titanium alloys. Current totals are 201 materials,
64 states, 1,381 observations and 19 pinned sources. See the
[table review and deferred rows](nonferrous-batch-review.md). Private originals
and public document-exclusion checks use the existing workflow.
