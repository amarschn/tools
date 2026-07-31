"use strict";

const assert = require("node:assert/strict");
const { performance } = require("node:perf_hooks");

global.window = global;
global.performance = performance;
require("../prototypes/assets/synthetic-corpus.js");
require("../prototypes/assets/search-core.js");

const corpus = global.MaterialsPrototypeCorpus;
const search = global.MaterialsPrototypeSearch;

assert.equal(corpus.synthetic, true);
assert.equal(search.stats.lookup_record_count, 50);
assert.equal(search.stats.material_count, 32);
assert.equal(search.stats.state_count, 38);
assert.equal(search.stats.observation_count, 360);
assert.equal(search.stats.empty_category_count, 1);

assert.ok(corpus.materials.every((item) => item.id.startsWith("synthetic-")));
assert.ok(corpus.states.every((item) => item.id.startsWith("synthetic-")));
assert.ok(corpus.observations.every((item) => item.id.startsWith("synthetic-")));
assert.ok(corpus.observations.every((item) => item.source_id.startsWith("synthetic-")));

function query(text, options) {
  return search.search(text, options);
}

let result = query("plastic strength");
assert.equal(result.state, "choose-property");
assert.equal(result.scope.id, "polymers");
assert.equal(result.property_intent.id, "strength");
assert.equal(result.property_intent.ids.length, 5);

result = query("plastic strength", { propertyId: "ultimate_tensile_strength" });
assert.equal(result.state, "results");
assert.equal(result.scope.id, "polymers");
assert.equal(result.material_terms, "");

result = query("engineering plastics");
assert.equal(result.state, "browse-scope");
assert.equal(result.scope.id, "engineering-plastics");
assert.ok(result.results.length > 0);
assert.ok(result.results.every((item) => item.kind === "material"));

result = query("P100 strength");
assert.equal(result.state, "choose-property");
assert.equal(result.results[0].id, "synthetic-peakdemo-p100");

result = query("P100 tensile strength");
assert.equal(result.state, "results");
assert.equal(result.property_intent.id, "ultimate_tensile_strength");
assert.equal(result.results[0].id, "synthetic-peakdemo-p100");

result = query("AX60");
assert.equal(result.results[0].id, "synthetic-synal-ax60");
assert.deepEqual(
  result.results.slice(1, 4).map((item) => item.id).sort(),
  [
    "synthetic-synal-ax60-t4",
    "synthetic-synal-ax60-t6",
    "synthetic-synal-ax60-t651"
  ]
);

result = query("AX60 T6");
assert.equal(result.results[0].id, "synthetic-synal-ax60-t6");

result = query("N6");
assert.equal(result.results[0].id, "synthetic-nylondemo-n6");
assert.notEqual(result.results[0].id, "synthetic-nylondemo-n66");

result = query("glass strength");
assert.equal(result.state, "choose-scope");
assert.ok(result.scope_options.length >= 2);

result = query("glass strength", {
  scopeId: "glasses",
  propertyId: "flexural_strength"
});
assert.equal(result.state, "results");
assert.equal(result.scope.id, "glasses");
assert.ok(result.results.length > 0);

result = query("strength");
assert.equal(result.state, "needs-material");

result = query("strongest plastic");
assert.equal(result.state, "unsupported-comparison");

result = query("thermosets");
assert.equal(result.state, "browse-scope");
assert.equal(result.scope.id, "thermosets");
assert.equal(result.results.length, 0);
assert.equal(search.getTaxonRecordCount("thermosets"), 0);

const speedQueries = [
  "AX60",
  "AX60 T651",
  "N6",
  "N66 conditioned",
  "P100 GF30",
  "plastic strength",
  "engineering plastics",
  "glass strength",
  "WoodDemo W1 stiffness",
  "PU80"
];
const timings = [];
for (let pass = 0; pass < 100; pass += 1) {
  for (const text of speedQueries) {
    timings.push(query(text).duration_ms);
  }
}
timings.sort((a, b) => a - b);
const p95 = timings[Math.floor(timings.length * 0.95)];
assert.ok(p95 < 20, `search p95 should be below 20 ms; measured ${p95.toFixed(3)} ms`);

console.log(
  `prototype search checks passed: ${search.stats.lookup_record_count} records, ` +
  `${search.stats.observation_count} observations, p95 ${p95.toFixed(3)} ms`
);
