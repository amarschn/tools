# UI bake-off decision notes

## Requirements held constant

All five directions:

- use the native system font stack;
- use neutral white/gray surfaces with one conventional blue;
- start with search rather than a hero or marketing statement;
- keep record count, corpus version, build version, synthetic status, and search
  timing visible;
- treat categories as non-data-bearing scopes;
- clarify broad properties such as `strength`;
- reject comparison intent rather than ranking materials.

Directions 01–04 show individual values only after one material/state is
selected. Direction 05 additionally shows derived category ranges for precise
property queries, but never treats those ranges as category-owned observations.

## Tradeoffs

| Direction | Strongest quality | Main cost | Best test |
|---|---|---|---|
| 01 · Compact index | Fastest scanning and least visual ceremony | A result table can still feel comparison-adjacent even though it shows availability rather than values | Is a dense directory enough? |
| 02 · Material first | Clearest lookup-only contract and simplest data safety story | Requires one more choice before any property appears | Does material → property feel helpfully focused or annoyingly rigid? |
| 03 · Split inspector | Fastest repeated lookup while retaining context | Most interface machinery and highest visual density | Do users repeatedly inspect several candidates in one session? |
| 04 · Query resolver | Most honest handling of ambiguous natural-language queries | Clarification can feel procedural and leaves more empty space | Do users value explicit interpretation over immediate browsing? |
| 05 · Dual-mode lookup | Serves material-first and property-first intent from one search box | Category rollups require careful coverage and condition labeling | Do grouped reference ranges provide enough orientation without turning into a comparison workspace? |

## Recommended next direction

Direction 05 is the current synthesis under review. It combines **01's compact
utility chrome**, **04's typed clarification**, **03's complete record detail**,
and the material-first discipline tested by **02**. Its new question is whether
property-first category ranges belong in the same fast lookup surface.

That hybrid would behave as follows:

1. Material intent resolves a concrete identity and shows named states when
   required.
2. A material-only query opens the complete datasheet.
3. A material + property query focuses that property and offers “Show all.”
4. A precise property-only query opens category-grouped observed ranges.
5. A category + property query scopes the same overview.
6. `plastic strength` asks for a precise strength type before showing ranges.
7. `strongest plastic` states that selection/ranking is outside scope.

## Questions for review

1. Does 02 feel too restrictive compared with 01?
2. Are 01's availability counts useful, or do they still imply comparison?
3. Is 04's clarification helpful or bureaucratic?
4. Is 03's persistent inspector worth its additional complexity?
5. Do 05's category ranges feel like useful reference context or an accidental
   comparison product?
6. Should generic polymer chemistry names such as PEEK be categories leading to
   concrete commercial grades, or are some generic reference materials valid
   lookup identities?
