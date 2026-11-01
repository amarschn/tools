/* Numerical drawing invariants for the chart's shapes; no browser needed. */
const assert = require('node:assert/strict');
const { build, contains, enclosingEllipse, pebble } = require('../../tools/ashby-chart/shapes.js');

const row = (id, tx, ty, extra = {}) => ({ id, family: 'metal', group: 'titanium', tx, ty, ...extra });
const colorOf = () => '#000';
const shapes = (rows, options = {}) => build(rows, { colorOf, ...options });

// Both shapes enclose the points they are built from.
const square = [[0, 0], [1, .2], [.4, 1], [.5, .4], [.9, .9]];
for (const fit of [enclosingEllipse(square, .01), pebble(square, .02)]) {
  for (const [x, y] of square) assert.ok(contains(fit.loop, x, y), `Point ${x},${y} is enclosed`);
  assert.ok(fit.loop.flat().every(Number.isFinite));
}

// The enclosing ellipse ignores density: piling points on one end does not move it.
const stretched = [[0, 0], [1, 1], [1, 0], [0, 1]];
const piled = [...stretched, ...Array.from({ length: 200 }, () => [.02, .02])];
const a = enclosingEllipse(stretched, .01).center, b = enclosingEllipse(piled, .01).center;
assert.ok(Math.hypot(a[0] - b[0], a[1] - b[1]) < .02, 'A dense cluster does not pull the oval off centre');

// One shape per family with no inner layer, in both methods.
for (const method of ['ashby', 'pebble']) {
  const regions = shapes([row('a', 3, 1), row('b', 3.1, 1.2), row('c', 3.2, 1.05)], { method });
  assert.equal(regions.length, 1);
  assert.equal(regions[0].loops.length, 1);
  assert.deepEqual(regions[0].parts, []);
  assert.equal(regions[0].label, 'Metals');
}

// Reported bounds never define a shape.
const withBound = [row('a', 3, 1), row('b', 3.1, 1.2), row('c', 3.2, 1.05), row('limit', 0, 9, { hasBounds: true })];
for (const method of ['ashby', 'pebble']) {
  const [region] = shapes(withBound, { method });
  assert.ok(Math.min(...region.loops[0].map(p => p[0])) > 2, 'The bound does not stretch the shape');
  assert.ok(Math.max(...region.loops[0].map(p => p[1])) < 3);
}
const onlyBounds = shapes([row('limit', 0, 9, { hasBounds: true })]);
assert.equal(onlyBounds.length, 0);
assert.deepEqual(onlyBounds.skipped, ['Metals']);

// A group drawn mostly from bounds gets no outline, and the result says which.
const mostlyBounds = [row('a', 3, 1), row('b', 3.1, 1.2), row('c', 3.2, 1.05), ...Array.from({ length: 5 }, (_, i) => row('m' + i, 3, 2 + i, { hasBounds: true }))];
const omitted = shapes(mostlyBounds);
assert.equal(omitted.length, 0);
assert.deepEqual(omitted.skipped, ['Metals']);

// Reported interval endpoints do define a shape.
const interval = shapes([row('i', 3, 1, { tRange: { x: [2.5, 3.5] } }), row('b', 3.1, 1.2)]);
assert.ok(contains(interval[0].loops[0], 2.5, 1) && contains(interval[0].loops[0], 3.5, 1), 'Interval endpoints are enclosed');

// A lone point has no shape, and coincident points still produce a small finite one.
assert.equal(shapes([row('a', 3, 1)]).length, 0);
const twin = shapes([row('a', 3, 1), row('b', 3, 1)]);
assert.equal(twin.length, 1);
assert.ok(twin[0].loops[0].flat().every(Number.isFinite));

// In family view an isolated material stays outside, its count is reported, and everything
// else stays inside. Small groups keep every member.
const cluster = Array.from({ length: 60 }, (_, i) => row('c' + i, 3 + (i % 10) * .03, 1 + Math.floor(i / 10) * .03));
const withOutlier = [...cluster, row('far', 9, 9)];
for (const method of ['ashby', 'pebble']) {
  const [region] = shapes(withOutlier, { method });
  assert.equal(region.outside, 1, 'The outlier is counted');
  assert.ok(!contains(region.loops[0], 9, 9), 'The outlier does not stretch the shape');
  for (const r of cluster) assert.ok(contains(region.loops[0], r.tx, r.ty), 'Every other material is enclosed');
}
const [small] = shapes([row('a', 3, 1), row('b', 3.1, 1.1), row('far', 9, 9)]);
assert.equal(small.outside, 0, 'A small family keeps all its members');
assert.ok(contains(small.loops[0], 9, 9));

// Subgroup view separates material types and splits distant clusters.
const poly = (id, tx, ty, group) => row(id, tx, ty, { family: 'polymer', group });
const grouped = [poly('a', 3, 0, 'PA6'), poly('b', 3.04, .03, 'PA6'), poly('c', 3, 1.3, 'PA6'), poly('d', 3.04, 1.32, 'PA6'),
  poly('e', 3.3, .7, 'PEEK'), poly('f', 3.32, .71, 'PEEK'), row('m', 3.9, 2.3), row('n', 3.9, 2.32)];
assert.deepEqual(shapes(grouped).map(r => r.label).sort(), ['Metals', 'Polymers']);
assert.equal(shapes(grouped, { grouping: 'subgroup' }).filter(r => r.family === 'polymer').length, 3);
assert.equal(shapes(grouped, { grouping: 'points' }).length, 0);
assert.equal(shapes(grouped, { method: 'none' }).length, 0);

// Tag grouping draws one shape per tag.
const tagged = shapes(grouped, { grouping: 'tag', tagsOf: r => r.family === 'metal' ? ['Picks'] : [], tagColor: () => '#111' });
assert.deepEqual(tagged.map(r => r.label), ['Picks']);

console.log('Ashby shapes: one oval per family, containment, density independence, bounds, intervals, outliers, subgroups, tags.');
