"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { performance } = require("node:perf_hooks");

global.window = global;
global.performance = performance;
require("../prototypes/assets/synthetic-corpus.js");
require("../prototypes/assets/search-core.js");

const corpus = global.MaterialsPrototypeCorpus;
const search = global.MaterialsPrototypeSearch;
const golden = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "fixtures", "m0-golden-queries.json"),
    "utf8"
  )
);

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

assert.equal(golden.version, 1);
assert.ok(golden.max_results <= 50);

function propertyIntentSummary(intent) {
  if (!intent) return null;
  return {
    kind: intent.kind,
    id: intent.id,
    ids: intent.ids
  };
}

for (const testCase of golden.cases) {
  const result = query(testCase.query, testCase.options);
  const expected = testCase.expected;
  const context = `${testCase.id} (${JSON.stringify(testCase.query)})`;
  const resultIds = result.results.map((item) => item.id);

  assert.equal(result.route, expected.route, `${context}: route`);
  if (Object.hasOwn(expected, "legacy_state")) {
    assert.equal(result.state, expected.legacy_state, `${context}: legacy state`);
  }
  assert.equal(
    result.scope ? result.scope.id : null,
    expected.scope_id,
    `${context}: scope`
  );
  assert.deepEqual(
    propertyIntentSummary(result.property_intent),
    expected.property_intent,
    `${context}: property intent`
  );
  assert.ok(
    result.results.length <= golden.max_results,
    `${context}: rendered result cap`
  );

  if (Object.hasOwn(expected, "scope_option_ids")) {
    assert.deepEqual(
      result.scope_options.map((item) => item.id),
      expected.scope_option_ids,
      `${context}: scope options`
    );
  }
  if (Object.hasOwn(expected, "material_terms")) {
    assert.equal(result.material_terms, expected.material_terms, `${context}: material terms`);
  }
  if (Object.hasOwn(expected, "result_prefix_ids")) {
    assert.deepEqual(
      resultIds.slice(0, expected.result_prefix_ids.length),
      expected.result_prefix_ids,
      `${context}: ordered result prefix`
    );
  }
  if (Object.hasOwn(expected, "not_first_id")) {
    assert.notEqual(resultIds[0], expected.not_first_id, `${context}: first result`);
  }
  if (Object.hasOwn(expected, "target_within_top")) {
    const rank = resultIds.indexOf(expected.target_within_top.id);
    assert.ok(
      rank >= 0 && rank < expected.target_within_top.limit,
      `${context}: ${expected.target_within_top.id} should rank within top ` +
        expected.target_within_top.limit
    );
  }
  if (Object.hasOwn(expected, "all_result_kinds")) {
    assert.ok(
      result.results.every((item) => item.kind === expected.all_result_kinds),
      `${context}: every result kind should be ${expected.all_result_kinds}`
    );
  }
  if (Object.hasOwn(expected, "minimum_result_count")) {
    assert.ok(
      result.results.length >= expected.minimum_result_count,
      `${context}: minimum result count`
    );
  }
  if (Object.hasOwn(expected, "result_count")) {
    assert.equal(result.results.length, expected.result_count, `${context}: result count`);
  }
  if (Object.hasOwn(expected, "comparison_intent")) {
    assert.equal(
      result.comparison_intent,
      expected.comparison_intent,
      `${context}: comparison intent`
    );
  }
  if (Object.hasOwn(expected, "taxon_record_count")) {
    assert.equal(
      search.getTaxonRecordCount(expected.taxon_record_count.id),
      expected.taxon_record_count.count,
      `${context}: taxon record count`
    );
  }
}

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
  `prototype search checks passed: ${golden.cases.length} golden queries, ` +
  `${search.stats.lookup_record_count} records, ` +
  `${search.stats.observation_count} observations, p95 ${p95.toFixed(3)} ms`
);
