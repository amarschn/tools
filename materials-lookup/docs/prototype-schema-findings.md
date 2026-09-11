# Prototype schema findings

Status: working hypothesis for the UI bake-off; not yet adopted by the production
builder.

## Product boundary

The tool is a lookup tool, not a comparison or selection tool.

- A precise material plus a precise property may show observations.
- A category may narrow or browse concrete materials, but never owns values.
- A broad property term asks for clarification.
- A precise property-only query may show taxonomy-grouped observed ranges with
  explicit corpus coverage and condition warnings.
- A comparison request such as “strongest plastic” is identified as out of
  scope instead of returning a ranking.

This removes the need for flat value-ranked material pages, compare controls,
and stored family envelopes from the core interaction.

## Recommended separation

```text
taxonomy ── classifies ──> material ── has ──> named state
                                             │
material or state ── owns ───────────────────┴──> observation
```

### Taxonomy

Examples: metals, engineering plastics, acetals, technical ceramics.

Taxonomy nodes:

- have names, aliases, broader/narrower relationships, and member counts;
- may be empty without creating a broken material record;
- may classify one material through several paths;
- never carry observations or stored property envelopes.

`Engineering plastics` therefore becomes a search scope with concrete members,
not an empty pseudo-material.

For default property rollups, every material also needs one primary browsing
path. Supplemental taxonomy memberships remain searchable but do not contribute
to the default rollup, preventing cross-classified materials from being counted
twice.

### Material identity

A material is something a specification, datasheet, or test report could
independently identify. It may be a standard designation, commercial grade,
species, pure substance, or defined composite system.

Generic chemistry names such as PEEK and POM are normally taxonomy concepts
unless a source explicitly defines a generic reference material. A real
commercial grade can belong to those concepts without inventing a standard-grade
parent.

### Named state

A state is a stable formulation or processing condition that users deliberately
name, such as T6, 30% glass-filled, or a defined laminate layup.

Temperature, specimen direction, thickness, moisture, product geometry, test
basis, and test method normally stay on observations. The synthetic wood record
deliberately has dry/green and longitudinal/radial observations without becoming
four different materials. This boundary will need source-driven exceptions, but
it is less overloaded than the current single `variant` concept.

### Observation

Every observation needs:

- a stable observation ID;
- material ID and optional named-state ID;
- precise property ID and coherent SI value/unit;
- basis, conditions, source ID, and source locator;
- distinct representations for uncertainty, a source-reported range, and
  variation across multiple observations.

Stable IDs are necessary for conflicts, supersession, review decisions, and deep
links.

## Property reference projections

A category/property range is a derived view over observations, not a category
property. For each category:

- collect data-bearing named states plus direct data-bearing materials whose
  primary browsing path descends from that category;
- select only observations with the exact property id and coherent canonical
  unit;
- show the raw observed minimum and maximum without averaging or choosing a
  winner;
- separately report covered subjects, eligible subjects, base materials, named
  states, raw observations, condition sets, and bases;
- flag mixed temperature, orientation, moisture, product form, thickness,
  formulation, layup, test method, or statistical basis;
- label the result “Observed corpus span—not a specification, design range, or
  recommendation,” with corpus/build version.

A zero-coverage category reports no observations. A singleton reports one value,
not an artificial `x–x` range. Drilldowns remain in fixed taxonomy/alphabetic
order and never sort by range endpoint.

## Problems surfaced by the synthetic corpus

1. **Taxonomy and identity are different axes.** The current
   `family → grade → variant` tree makes an empty family look like a material and
   duplicates classification between `parent_id` and `family[]`.
2. **One parent is insufficient.** A glass-filled acetal grade is both an acetal
   and a fiber-reinforced polymer. A taxonomy membership list can express this;
   a single material parent cannot.
3. **Variant means too many things.** Heat treatment, formulation, layup,
   product form, moisture, orientation, and test state do not all have the same
   identity semantics.
4. **Generic chemistry may not be specifiable.** PEEK or POM can be useful search
   concepts without pretending a representative observation exists.
5. **Close designations need identity-only ranking.** AX60/AX61, T6/T651,
   N6/N66, A96/A995, and PU-40/PU-80 should not be separated by incidental
   description text or property values.
6. **Broad property language is not an alias.** “Strength” spans tensile yield,
   ultimate tensile, compressive, flexural, and notched impact properties with
   different meanings and sometimes different dimensions.
7. **Conditions can create several valid answers.** The AX70-T6 and WoodDemo W1
   records contain multiple observations of the same property. The UI must show
   the conditions rather than choose an unexplained representative.
8. **Missingness is meaningful.** Similar grades intentionally have different
   property coverage. Absence cannot be treated as zero or hidden behind an
   inherited family value.
9. **Empty categories are valid.** The fixture contains a thermosets category
   with no records. It should return “0 materials in this prototype,” not a
   blank material page or fabricated envelope.
10. **Reference projections can masquerade as facts.** Property/category spans
    are useful orientation, but they become misleading if stored on categories,
    stripped of coverage labels, or sorted to imply winners.

## Search contract under test

Search keeps categories, material identities, and properties in separate typed
namespaces. It matches explicit aliases longest-phrase-first, removes matched
category/property phrases, and ranks only the remaining identity terms.

Expected cases:

| Query | Expected behavior |
|---|---|
| `tensile strength` | Category-grouped observed ranges, never a flat material ranking |
| `plastic tensile strength` | The same property reference view scoped to polymers |
| `plastic strength` | Polymers scope plus a strength-property chooser; no range until a precise property is chosen |
| `engineering plastics` | Category browse with concrete material count |
| `P100 strength` | P100 material first plus property clarification |
| `P100 tensile strength` | P100 first with tensile observations focused after selection |
| `strength` | Ask for a precise strength property, then open property reference mode |
| `AX60` | AX60 identity first with named states |
| `AX60 T6` | Exact T6 state first |
| `N6` | Exact N6 identity before N66 |
| `glass strength` | Clarify bulk-glass versus fiber-composite category and strength type |
| `strongest plastic` | Explain that comparison/selection is outside scope |
| `thermosets` | Valid empty category |

## Decision still required

The bake-off should decide how much clarification belongs in the search result
surface:

- material-first makes the no-comparison boundary strongest;
- the query resolver handles natural language most explicitly;
- the compact directory is fastest to scan;
- the split inspector is fastest for repeated lookups;
- the dual-mode prototype tests complete datasheets plus property/category
  reference projections.

The schema separation above works with all five. It should be tested against two
real, structurally different sources before replacing the production
family/grade/variant contract.
