# Schema lab M0 baseline

Status: frozen Phase 0 evidence for review checkpoint 1

Baseline date: 2026-08-02

## Purpose and baseline identity

This document freezes the two data models and delivery paths that existed when
the M1 synthetic schema lab began. It is an inventory, not Schema Decision 002
and not an approval of either legacy representation.

Measurements were taken from a clean worktree at:

```text
commit  c8d3061e6ac00fe14db24db4bbd85dc7bee8baf6
short   c8d3061 Propose M1 synthetic schema lab plan
date    2026-08-01T09:36:24-05:00
branch  main
```

This document is an uncommitted Phase 0 addition and is intentionally not part
of the measured commit. Artifact sizes are byte counts of the tracked
files at that commit; gzip sizes use Node's zlib at level 9, not HTTP transfer
logs from the local uncompressed development server.

Measurement environment:

```text
Node   v25.8.2
zlib   1.2.12
Python 3.13.12
OS     Darwin 25.5.0 arm64
```

## Frozen versions and entity counts

The original static builder and Prototype 05 are separate baselines. The word
“record” means different things in them and must not be compared without the
typed counts below.

### Original static builder

| Item | Frozen value |
|---|---:|
| Canonical input schema version | `0.1.0` |
| Builder/output-manifest version | `1` |
| Material records | 19 |
| Family records | 6 |
| Grade records | 6 |
| Variant records | 7 |
| Observations | 33 |
| Registered exact properties | 7 |
| Registered condition keys | 7 |
| Source records | 3 |
| Search-index rows | 19 |

All 33 observations are owned by variants. Families and grades own no
observations; the builder generates descendant envelopes for them.

### Prototype 05 synthetic model

| Item | Frozen value |
|---|---:|
| Schema label | `prototype-taxonomy-material-state-observation-0.2` |
| Corpus version | `synthetic-0.2.0` |
| Build label | `ui-lab-2026.07.29.1` |
| Taxa | 27 |
| Material identities | 32 |
| Named states | 38 |
| Observations | 360 |
| Exact properties | 13 |
| Property groups | 5 |
| Materials with direct observations | 12 |
| Materials with one or more named states | 20 |
| Data-bearing lookup records | 50 |
| Intentionally empty taxa | 1 (`thermosets`) |

“50 records” in the Prototype 05 header is specifically 38 named states plus
12 materials with direct observations. It is not the number of material
identities and must not become an ambiguous manifest field.

## Accepted behavior to preserve

The selected Prototype 05 interaction is the acceptance source of truth. A
legacy helper's internal state name is not accepted merely because a test once
asserted it.

- An exact material or named-state query opens a datasheet. A material plus an
  exact property opens the same record focused on that property, with a way to
  show all properties.
- A material identity with named states does not silently merge those states
  into one supposed value. The user can select a state.
- An exact property-only query opens a taxonomy-grouped reference view. A
  category plus property query opens the same view scoped to that category.
- A broad property group such as `strength` or `plastic strength` asks the user
  to choose one exact property before showing numeric results.
- A category-only query browses that category. An empty category is a valid
  zero-coverage result, not a failed search.
- Comparison intent such as `strongest plastic` is unsupported. No result view
  ranks materials by value or labels a winner.
- Taxa are navigation/classification entities and own no observations. Displayed
  category ranges are generated corpus projections, not category facts.
- Default rollups follow one primary taxonomy path. Supplemental
  classifications remain searchable context and do not double-count a subject.
- A property projection uses raw observation endpoints in canonical units. It
  preserves separate coverage, material, state, observation, condition-set, and
  basis counts and reports mixed-condition warnings.
- Multiple observations are retained rather than averaged. Missing data is not
  zero and is not inherited from a material into all of its states.
- Taxonomy and alphabetic order control browsing; numeric endpoints do not.
- Taxonomy breadcrumbs navigate back to the selected section, and hierarchy
  indentation affects only the label column rather than the value/count/action
  tracks.
- Synthetic values remain conspicuously labelled and the UI exposes corpus,
  build, record-count, and search-timing context.
- Search output is capped; the current production shell caps at 50 rows and the
  prototype resolver at 40, both satisfying the accepted maximum of 50.

### Frozen query evidence

The resolver result below is useful migration evidence, but “Visible Prototype
05 route” is the behavior that the schema-backed adapter must reproduce.

| Query | Current resolver evidence | Visible Prototype 05 route to preserve |
|---|---|---|
| `AX60` | `results`; AX60 material first, then its T4/T6/T651 states | Material record with named-state choices |
| `AX60 T6` | `results`; T6 state first | Focused T6 datasheet |
| `P100 tensile strength` | exact property intent; P100 material first | P100 flow focused on ultimate tensile strength, then state choice |
| `AX70 T6 yield` | exact property intent; one T6 state | T6 record with both conditioned yield observations |
| `tensile strength` | resolver says `needs-material` but retains exact property intent | All-category property overview |
| `plastic tensile strength` | polymer scope plus exact property intent | Polymer-scoped property overview |
| `strength` | resolver says `needs-material` but retains the five-member group | Choose one exact strength property, all categories |
| `plastic strength` | `choose-property`, polymer scope | Choose one exact strength property, polymer scope |
| `engineering plastics` | `browse-scope` | Engineering-plastics category browse |
| `thermosets` | `browse-scope`, zero results | Valid empty category |
| `strongest plastic` | `unsupported-comparison` | Unsupported comparison notice |

Prototype 05 currently compensates for the two `needs-material` states by
routing on the retained exact-property or property-group intent before it
examines that state. The new contract should expose the accepted route directly
rather than require this UI-specific exception.

### Frozen property-view evidence

These visible summaries were captured from Prototype 05 at the baseline. They
are regression evidence for the later projection goldens, not adopted category
facts.

| Query | Visible corpus span | Coverage | Other counts | Root categories shown |
|---|---|---|---|---|
| `yield strength` | 71-1008 MPa | 18 of 50 data-bearing records | 9 materials; 19 observations; 11 condition sets; 1 basis | Metals |
| `tensile strength` | 7.8-1710 MPa | 41 of 50 data-bearing records | 23 materials; 41 observations; 24 condition sets; 2 bases | Metals; Polymers and plastics; Composites |
| `plastic tensile strength` | 7.8-209 MPa | 19 of 21 data-bearing records | 12 materials; 19 observations; 11 condition sets; 1 basis | Polymers and plastics |

All three views label the range as an observed corpus span rather than a
specification, design range, or recommendation. The later projection tests must
also freeze exact mixed-condition warnings once their complete condition
signature is extracted from the page.

### Phase 0 executable route delta

After the baseline inventory, the shared resolver gained a compatibility-safe
`route` field while retaining its older `state` field for Prototypes 01-04. A
21-case table-driven fixture now records the accepted dual-mode routes. Bare
`strength` routes to exact-property clarification; precise property-only and
category-plus-property queries route to `property-overview`.

This is an intentional baseline clarification, not a new product feature. Run
`node tests/prototype_search.test.js` to verify the route matrix, result ordering,
intent, 50-row maximum, and search latency guardrail.

## Static-serving baseline

### Tracked artifacts

| Artifact | Role | Raw bytes | Gzip bytes | SHA-256 |
|---|---|---:|---:|---|
| `materials/index.html` | Original search shell, inline CSS and JS | 96,892 | 21,376 | `d6f755cd1d8fee244c4f8e9c42ee57aa363aad4a85101a15c7e7c3a59d3eb02f` |
| `materials/search-index.json` | Eager original index | 36,120 | 7,129 | `e79decc4950c9ae1cc20df973c205bca275c4f08297157781685f0c26e2e35f4` |
| `materials/assets/styles.css` | Shared detail/property-page styles | 16,370 | 3,988 | `493769954e4c723cf54b8d119659e467649b9729991a82ac8cd92dd21bb07208` |
| `prototypes/05-dual-mode.html` | Selected prototype UI | 60,160 | 12,334 | `13c8cbb6c93c09e8aa3e19935e720c1e24ba3167c69b435110d7b510067d96b1` |
| `prototypes/assets/synthetic-corpus.js` | Eager synthetic corpus factory | 30,267 | 7,694 | `b8afa1c3b0b032120f22cb59da1889407250daf892e4092ba570ede39fbf4021` |
| `prototypes/assets/search-core.js` | Shared resolver and access helpers | 21,497 | 5,055 | `557c4da8a8713bbec5fe49f897e83b37a86daeb6ce714bc8e52279501086c294` |

The original search route therefore starts with two relevant files totaling
133,012 bytes raw or 28,505 bytes as separately gzipped responses. Prototype 05
starts with three files totaling 111,924 bytes raw or 25,083 bytes as separately
gzipped responses.

The 19 generated files under `materials/records/` total 35,765 raw bytes. They
would be 5,004 bytes if concatenated and compressed as one stream, or 13,127
bytes if all 19 were separately gzipped and transferred. The SHA-256 of the
sorted raw concatenation is
`bafd1359784723092831634bac085bdcdb6d534d84a4544592cb1bb35a665529`.
Neither aggregate represents a normal page load because the current browser
does not request these files.

The corpus factory expands at runtime to JSON equivalent to 164,694 raw / 10,889
gzip bytes, SHA-256
`a5bd006008a783245d2df65ee6840ece6aa94d207d7c95423a6d8d76341c61b2`.
Its observations alone are 142,193 raw / 6,478 gzip bytes, SHA-256
`24b9f01bd72091fa3e65db173a469049b666df30fbd018b20d0cb4d45d8f5f12`.
These are normalized in-memory-size proxies, not additional wire artifacts.

### Original static demo load behavior

1. Inline code in the document head begins a relative
   `fetch("./search-index.json", {cache: "force-cache"})` before the rest of the
   page is parsed.
2. The search input renders while the request is pending. Keystrokes are kept
   and the query runs when the complete index is ready.
3. The browser expands parallel-array rows into objects, maps, normalized
   strings, token sets, postings, and a thesaurus in memory.
4. The eager index contains prose descriptions, up to four numeric headline
   values per material, postings, and both a postings-key list and a separate
   duplicated `token_list`.
5. Search results link to pre-rendered material or property HTML. No current
   browser code consumes `materials/records/*.json`.
6. Detail and property pages are pre-rendered and use the shared stylesheet;
   they do not hydrate from the JSON records.

### Prototype 05 load behavior

1. The HTML parses two ordinary blocking scripts at the end of the document:
   `synthetic-corpus.js`, followed by `search-core.js`.
2. The first script constructs the complete normalized corpus in memory. The
   second constructs material/state/taxon/property maps and search entities.
3. Prototype 05 then constructs another set of maps and computes category
   projections from all 360 observations in the browser, caching rollups in
   memory.
4. Material datasheets and property views read the same eager in-memory corpus;
   opening them makes no data request.

Both paths are static and make no API, database, service-worker, or hosted-search
request. The original index has a stable URL combined with `force-cache`, no
content hash, and no payload build ID. Individual generated record JSON files
also carry neither the input schema version nor the builder version; only the
file-list manifest carries builder version `1`. Emitted record/property links
are root-absolute under `/materials/`, so cache-version mismatch and subpath
hosting are not yet solved.

## Data-model differences

| Area | Original builder `0.1.0` | Prototype 05 reference | Checkpoint implication |
|---|---|---|---|
| Classification | Families are records in the same hierarchy as identities | Taxa are a separate collection | Adopt or reject separation explicitly; taxa must never own observations in the accepted behavior. |
| Identity hierarchy | `family -> grade -> variant` | taxon, material, named state, observation | Map grades to identities and variants to states only when that meaning is valid. |
| Observation owner | Variant only | Material or named state | Direct material values must remain possible; no implicit inheritance. |
| Primary browse path | Encoded by `parent_id`; `family[]` is unregistered search text | First `taxon_ids` entry is treated as primary | Make primary membership explicit; do not reinterpret legacy `family[]` tags automatically. |
| Supplemental classification | No typed relation | Additional `taxon_ids`, including state additions | Preserve as explicit supplemental links and exclude from default counts. |
| Material identity kind | Implied by `record_type` | Free synthetic `identity_kind` string | Define a controlled identity-kind contract without restoring the old hierarchy. |
| State data | Variant `condition` string; observation conditions repeat context | State `fixed_conditions`, also copied into its observations by the fixture factory | Store fixed attributes once and derive effective conditions; reject conflicts. |
| Observation identity | No observation ID | Stable `synthetic-obs-NNNN` IDs | Assign explicit stable IDs and retain an old-path-to-new-ID migration report. |
| Result form | Numeric point plus optional `uncertainty` | Point plus nullable `value_min`/`value_max`; all current bounds are null | Introduce a discriminated point/interval/bound/assertion result; do not infer semantics from nullable columns. |
| Source model | Three-record source registry | Two referenced synthetic source IDs, no source collection | Add synthetic source records; every reference and locator must resolve. |
| Locator | One human-readable string | One human-readable string | Wrap losslessly in a structured locator with a required display label; do not guess page/table fields. |
| Property groups | None | Five explicit groups | Keep a group distinct from any exact property. |
| Search data | Numeric headlines, descriptions, aliases, tags, postings | Full identities plus full observation corpus in memory | Test a typed availability-only index and lazy records/property payloads. |

## Explicit legacy mapping inventory

This inventory accounts for every current namespace before the checkpoint. A
row marked “proposed” still requires approval in the representative example; it
must not be silently embedded in a validator or migration script.

### Entity and relationship mappings

| Legacy input | Proposed canonical destination | Migration rule and status |
|---|---|---|
| Builder `family` record | Taxon | Preserve ID/name/aliases and convert family-to-family `parent_id` to the primary browse parent. Inventory only during M1; the current curated builder is not migrated silently. |
| Builder `grade` record | Material identity | Preserve ID/name/aliases. Its family-record `parent_id` proposes the primary taxon. This mapping is subject to identity review for generic grades. |
| Builder `variant` record | Named state of its grade | Preserve the legacy ID in the mapping report, point the state at the grade material, and attach its observations using both material and state IDs. Do not create a second material merely to retain the old URL shape. |
| Builder `family[]` values | Legacy search tags | Do not automatically create taxonomy links: values such as `metal`, `wrought-aluminium`, and `6xxx` are not registered taxon IDs in that model. Review them as aliases, designations, or supplemental taxonomy individually. |
| Prototype taxon | Taxon | Preserve all 27 IDs and parent relations. Make the parent field explicitly the primary browse parent. |
| Prototype material | Material identity | Preserve all 32 reserved synthetic IDs, names, aliases, identity-kind evidence, and notes. Convert `taxon_ids[0]` to explicit primary membership and the remainder to supplemental membership. |
| Prototype named state | Named state | Preserve all 38 IDs, material references, labels, and aliases. Rename `fixed_conditions` to the approved fixed-attribute field only after checkpoint review. |
| Prototype observation | Observation | Preserve all 360 IDs and material/state/property/source references. Remove state-fixed values duplicated into observation conditions only through a checked migration that proves equality. |
| Builder observation | Observation | All 33 lack IDs. Assign stable IDs deliberately and record each old JSON path; an ID must not be derived from the numeric value. |

Aliases remain free-text search identities. A designation is not an alias, and a
derived phrase such as a material designation plus a state label is a generated
search term rather than a second canonical designation.

### Property-ID mapping

The following table is the complete overlap between the seven builder
properties and the 13 prototype properties.

| Builder ID | Prototype ID | Proposed canonical ID | Status/rationale |
|---|---|---|---|
| `yield_strength` | `tensile_yield_strength` | `tensile_yield_strength` | Proposed rename: the legacy ID omits the tensile test mode. Keep `yield_strength` only as an explicit legacy mapping/search phrase. |
| `tensile_strength` | `ultimate_tensile_strength` | `ultimate_tensile_strength` | Proposed rename: make ultimate strength exact rather than relying on convention. Keep `tensile_strength` as an explicit legacy mapping/search phrase. |
| `youngs_modulus` | `youngs_modulus` | `youngs_modulus` | Preserve. |
| `density` | `density` | `density` | Preserve. |
| `thermal_conductivity` | `thermal_conductivity` | `thermal_conductivity` | Preserve. |
| `elongation_at_break` | `elongation_at_break` | `elongation_at_break` | Preserve. |
| `max_service_temperature` | `max_service_temperature` | `max_service_temperature` | Preserve, while requiring the eventual property definition and conditions to state what “maximum” means. |

Prototype-only exact IDs proposed for preservation are
`compressive_strength`, `flexural_strength`, `notched_impact_strength`,
`flexural_modulus`, `electrical_resistivity`, and `shore_a_hardness`.

The prototype's groups are `strength`, `stiffness`, `conductivity`,
`temperature`, and `hardness`. They remain separate group IDs. In particular,
`strength` must not map to either yield or ultimate tensile strength.

Final canonical IDs and exact property definitions are checkpoint-1 decisions.
Once approved, both old-to-new property mappings must be machine-readable
compatibility data rather than extra canonical property records.

### Designation mapping

The builder contains 31 designation values on 13 records as a map from system
name to a string or list. Frozen system counts are:

| Legacy system key | Values | Proposed stable system ID |
|---|---:|---|
| `AA` | 5 | `aa` |
| `UNS` | 9 | `uns` |
| `EN` | 5 | `en` |
| `AISI` | 4 | `aisi` |
| `SAE` | 4 | `sae` |
| `ISO_polymer_symbol` | 4 | `iso_polymer_symbol` |

Each map value proposes one structured, system-qualified designation entry. The
original value string is preserved exactly; a list becomes multiple entries.
Lower-case system IDs above are provisional until the representative example is
approved.

The prototype contains 32 flat designation strings, one on each material, with
no system. They cannot be migrated as standards-based designations by guessing
from their spelling. Checkpoint 1 must either approve an explicit synthetic
fixture system or preserve them in a clearly typed unqualified legacy field
until reviewed. They must not silently become aliases or claim membership in a
real designation system.

### Condition and state-context mapping

The original condition registry defines `temperature_K`, `product_form`,
`thickness_m`, `orientation`, `cross_sectional_area_m2`, `material_state`, and
`moisture_content_1`.

The prototype uses these observation-condition keys:

```text
fiber_mass_fraction_1    fiber_volume_fraction_1  formulation
layup                    material_state            moisture_content_1
orientation              product_form              reinforcement
temperature_K            thickness_m
```

Its state-fixed keys are:

```text
fiber_mass_fraction_1  formulation  layup  material_state
moisture_content_1     product_form reinforcement
```

`cross_sectional_area_m2` exists only in the builder fixture;
`fiber_mass_fraction_1`, `fiber_volume_fraction_1`, `formulation`, `layup`, and
`reinforcement` are not in its registry. The new condition registry must account
for the union before migration.

The mapping rule proposed for checkpoint 1 is:

- state-recognizable fixed context goes on the named state's approved
  fixed-attribute field;
- test-specific context remains in observation `conditions`;
- `basis` and `test_method` remain top-level observation semantics rather than
  condition keys;
- an observation may repeat a state-fixed key only during legacy migration;
  exact equality is de-duplicated and a conflict is a hard error; and
- a variant's free-text `condition` or `material_state` is not promoted to a
  registered structured attribute until its meaning has been reviewed.

The separate state-versus-condition matrix is authoritative for final legal
placement.

### Observation result, uncertainty, source, and locator mappings

- All 33 builder observations currently contain numeric point values. Thirteen
  carry `uncertainty.kind = implied`; 20 synthetic seed estimates carry
  `uncertainty.kind = range`. Those 20 ranges currently widen generated
  envelopes, but their name does not establish whether they are uncertainty,
  estimated coverage, or a reported interval. Each must be mapped explicitly;
  the migration must not reinterpret it from field shape alone.
- All 360 Prototype 05 observations are points. Although they expose nullable
  `value_min` and `value_max` columns, every current bound is null. Interval,
  one-sided-bound, uncertainty, unavailable/not-applicable, and supersession
  cases are additions to the lab rather than frozen legacy evidence.
- Reported values and units must be retained alongside canonical numeric values;
  conversion must not erase the reported form.
- Builder observations inherit material/state ownership from their containing
  variant object. The canonical migration writes explicit material and optional
  state references and checks they agree.
- Builder source IDs resolve through its three-record registry. Prototype
  observations reference `synthetic-fixture` or `synthetic-fixture-b`, but no
  source collection defines either; Phase 1 must add explicit synthetic source
  records before full validation can require reference integrity.
- Every existing `source_locator` string maps losslessly to the required
  human-readable locator label. Optional page/table/row/column fields may be
  added only from explicit fixture knowledge, not by parsing prose heuristically.

### Search and delivery mappings

- Material, state, taxon, exact-property, and property-group identities,
  aliases, structured designations, primary/supplemental scope IDs, and compact
  property availability are candidates for the generated search contract.
- Descriptions, source detail, observation conditions, and numeric headline
  values in the old index are not canonical search fields. Their removal must be
  tested against the frozen query routes rather than assumed harmless.
- Existing postings and `token_list` are derived encoding details, not contract
  entities. The bake-off may regenerate, replace, or omit them.
- `prominence` is a legacy ranking tie-breaker, not material identity data. Any
  retained ranking hint must be explicit generated search metadata.
- Generated family/grade envelopes and Prototype 05 rollup caches map to
  deterministic projections only. They never map back into stored observations
  or taxonomy records.
- Existing record JSON is evidence for a lazy material bundle, but its embedded
  `source_details` duplicates source metadata and it is not currently exercised
  by the browser. The serving lab must derive its own bundle from the approved
  contract.

## Known issues and intentionally retired behavior

These are not accepted compatibility requirements:

- The two legacy entity models are incompatible and neither file shape is the
  new contract by default.
- At the measured commit, the shared resolver returned `needs-material` for
  precise property-only queries and bare `strength`. Phase 0 now exposes the
  accepted route separately while preserving the legacy state for the archived
  prototypes.
- Property projections and their counting rules currently live in Prototype
  05's page script rather than testable domain code.
- Primary taxonomy is implicit in the first `taxon_ids` element.
- State-fixed values are duplicated into observation conditions by the fixture
  factory.
- The prototype has unresolved synthetic source references and only string
  locators.
- Neither corpus contains the full discriminated result cases required by M1.
- The old builder's `uncertainty.kind = range` is semantically ambiguous and is
  used to widen descendant envelopes.
- The old search index eagerly exposes descriptions and numeric headlines;
  Prototype 05 eagerly exposes every observation. Neither boundary has been
  selected by measurement.
- Generated record JSON exists but has no browser consumer.
- `force-cache` on an unhashed stable index URL can pair stale data with newer
  HTML. The build manifest lists owned files but carries no artifact hashes or
  deterministic corpus build ID.
- Root-absolute `/materials/` links make the current generated site dependent on
  one mount path.
- The local `python -m http.server` does not reproduce production compression or
  cache headers, so the gzip figures above are comparable size calculations,
  not observed network transfers.

## Checkpoint-1 boundary

This baseline supplies the migration side of checkpoint 1. Approval is still
required for:

1. exact glossary meanings for taxon, material, named state, observation,
   property, group, condition, source, and locator;
2. the state-versus-observation-condition placement matrix;
3. the representative complete material/state/observation/source example;
4. the proposed canonical property renames;
5. the literal structured designation shape and treatment of unqualified
   synthetic designations; and
6. the discriminated result and uncertainty forms.

No serving topology, validator implementation, builder migration, or factual
data migration is approved merely by accepting this inventory.

## Reproduce the baseline

Verify the commit and clean starting point before reproducing measurements:

```sh
git rev-parse HEAD
git log -1 --format='%H%n%h %s%n%aI'
git status --short
```

Run the existing validation suites:

```sh
python3 scripts/build_site.py --check
python3 -m unittest discover -s tests -v
node tests/prototype_search.test.js
```

At the frozen commit these report 19 builder records, 7 builder properties, 14
passing Python tests, 50 synthetic lookup records, 360 synthetic observations,
and a prototype-search p95 below its legacy 20 ms threshold. The exact timing is
machine-sensitive.

Reproduce entity counts:

```sh
node - <<'NODE'
const fs = require('fs');
const curated = JSON.parse(fs.readFileSync('curated/materials.json'));
const properties = JSON.parse(fs.readFileSync('registry/properties.json'));
const conditions = JSON.parse(fs.readFileSync('registry/conditions.json'));
const sources = JSON.parse(fs.readFileSync('curated/sources.json'));
const recordTypes = {};
let observations = 0;
for (const material of curated.materials) {
  recordTypes[material.record_type] = (recordTypes[material.record_type] || 0) + 1;
  observations += material.observations.length;
}
console.log({
  schema_version: curated.schema_version,
  materials: curated.materials.length,
  recordTypes,
  observations,
  properties: properties.properties.length,
  conditions: conditions.conditions.length,
  sources: sources.sources.length
});

global.window = global;
require('./prototypes/assets/synthetic-corpus.js');
const corpus = global.MaterialsPrototypeCorpus;
const direct = new Set(
  corpus.observations.filter(item => !item.state_id).map(item => item.material_id)
);
console.log({
  schema_version: corpus.schema_version,
  corpus_version: corpus.corpus_version,
  build_version: corpus.build_version,
  taxa: corpus.taxa.length,
  materials: corpus.materials.length,
  states: corpus.states.length,
  observations: corpus.observations.length,
  properties: corpus.properties.length,
  property_groups: corpus.property_groups.length,
  data_bearing_records: corpus.states.length + direct.size
});
NODE
```

Reproduce raw, gzip, and SHA-256 artifact measurements:

```sh
node - <<'NODE'
const fs = require('fs');
const zlib = require('zlib');
const crypto = require('crypto');
function measure(buffer) {
  return {
    raw: buffer.length,
    gzip: zlib.gzipSync(buffer, {level: 9}).length,
    sha256: crypto.createHash('sha256').update(buffer).digest('hex')
  };
}
for (const path of [
  'materials/index.html',
  'materials/search-index.json',
  'materials/assets/styles.css',
  'prototypes/05-dual-mode.html',
  'prototypes/assets/synthetic-corpus.js',
  'prototypes/assets/search-core.js'
]) console.log(path, measure(fs.readFileSync(path)));

const names = fs.readdirSync('materials/records')
  .filter(name => name.endsWith('.json')).sort();
const records = names.map(name => fs.readFileSync('materials/records/' + name));
const combined = Buffer.concat(records);
console.log('records', {
  count: records.length,
  raw: records.reduce((sum, item) => sum + item.length, 0),
  gzip_combined: zlib.gzipSync(combined, {level: 9}).length,
  gzip_sum_individual: records.reduce(
    (sum, item) => sum + zlib.gzipSync(item, {level: 9}).length, 0
  ),
  sha256_concatenated: measure(combined).sha256
});

global.window = global;
require('./prototypes/assets/synthetic-corpus.js');
console.log(
  'prototype-runtime-corpus',
  measure(Buffer.from(JSON.stringify(global.MaterialsPrototypeCorpus)))
);
console.log(
  'prototype-runtime-observations',
  measure(Buffer.from(JSON.stringify(global.MaterialsPrototypeCorpus.observations)))
);
NODE
```

Use `node tests/prototype_search.test.js` for the checked-in resolver assertions.
The accepted route differences in the query table above are now explicit route
goldens rather than page-specific control flow.
