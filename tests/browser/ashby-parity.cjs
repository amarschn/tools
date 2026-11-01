/* The chart's rows must reproduce the published property pairs exactly, and its index
   values must match Python's. No browser needed: node tests/browser/ashby-parity.cjs */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { Database, Axis, runStages, parseQuery, FAMILY_NAMES } = require('../../tools/ashby-chart/engine.js');

const read = name => JSON.parse(fs.readFileSync(path.join(__dirname, '../../data/materials', name), 'utf8'));
const selection = read('selection.json'), core = read('selection-core.json'), details = read('selection-details.json');
const db = new Database(core);
assert.equal(core.source_build_id, selection.source_build_id);
assert.equal(details.source_build_id, selection.source_build_id);
assert.equal(details.observations.length, db.obsCount, 'Details align with the core observations');

const ids = details.observations.map(o => o.id);
const position = new Map(ids.map((id, i) => [id, i]));
const pairKey = (a, b) => [a, b].sort().join('|');
let compared = 0, scored = 0;
for (const [key, chart] of Object.entries(selection.charts)) {
  const [xId, yId] = chart.properties;
  const sym = id => core.properties.find(p => p.id === id).symbol;
  const axes = [new Axis(db, sym(xId)), new Axis(db, sym(yId))];
  const points = db.points(db.rows, axes);
  const fromRows = new Set(points.map(p => (p.obs.length === 1 ? pairKey(ids[p.obs[0]], ids[p.obs[0]]) : pairKey(ids[p.obs[0]], ids[p.obs[1]]))));
  const published = new Map(chart.points.map(p => [pairKey(...p.observations), p]));
  assert.equal(fromRows.size, points.length, `${key}: each pair appears once`);
  assert.deepEqual([...fromRows].sort(), [...published.keys()].sort(), `${key}: rows reproduce the published pairs`);
  compared += published.size;
  for (const point of points) {
    const pub = published.get(point.obs.length === 1 ? pairKey(ids[point.obs[0]], ids[point.obs[0]]) : pairKey(ids[point.obs[0]], ids[point.obs[1]]));
    assert.deepEqual(point.temperatures_K, pub.temperatures_K, `${key}: temperatures`);
    assert.equal(point.m.id, pub.material_id);
    assert.equal(point.stateIndex >= 0 ? db.states[point.stateIndex].id : null, pub.state_id, `${key}: state`);
    for (const indexId of chart.indices) {
      const value = db.score(core.indices[indexId], point.row);
      if (indexId in pub.scores) {
        assert.ok(Math.abs(value - pub.scores[indexId]) <= Math.abs(pub.scores[indexId]) * 1e-6, `${indexId}: ${value} against ${pub.scores[indexId]}`);
        scored++;
      }
    }
  }
}
assert.ok(compared > 17000, 'All charts were compared');

// A three-property point holds only observations that are compatible pair by pair.
const pairs = new Set();
for (const chart of Object.values(selection.charts)) for (const p of chart.points) pairs.add(pairKey(...p.observations));
for (const row of db.rows) {
  assert.ok(row.list.length > 0);
  for (let i = 0; i < row.list.length; i++) for (let j = i + 1; j < row.list.length; j++) {
    assert.ok(pairs.has(pairKey(ids[row.list[i]], ids[row.list[j]])), `Row ${row.i} holds an unpublished pair`);
  }
}

// Each stage reads one row, so a limit cannot mix tempers: T4 alone fails a limit that only T6 meets.
const sixty = () => db.rows.filter(row => row.m.id === 'al-6061');
const passing = runStages(db, [parseQuery(db, 'Sy > 200 MPa')], sixty());
assert.ok(passing.rows.length > 0);
for (const row of passing.rows) assert.equal(db.states[db.obsState[row.obs[db.bySym.Sy.index]]].id, 'al-6061-t6');

// Typed filters convert units or refuse them.
assert.equal(parseQuery(db, 'E > 200000 MPa').min, 200);
assert.equal(parseQuery(db, 'UTS < 1 GPa').max, 1000);
assert.equal(parseQuery(db, 'E > 5').min, 5);
assert.throws(() => parseQuery(db, 'rho > 5 GPa'), /kg\/m³/);
assert.throws(() => parseQuery(db, 'E/rho > 5 GPa'), /formula/);
assert.throws(() => parseQuery(db, 'nope > 5'), /Unknown property/);
assert.equal(parseQuery(db, 'family metal, composite').values.length, 2);
assert.equal(parseQuery(db, 'peek').type, 'text');
assert.ok(Object.keys(FAMILY_NAMES).includes(db.byId['al-6061'].family));

// Formula axes read one row and need every property they name.
const beam = new Axis(db, 'E^0.5/rho');
assert.deepEqual([...beam.used].sort(), [db.bySym.E.index, db.bySym.rho.index].sort());
const row6061 = db.rows.find(row => row.m.id === 'al-6061' && row.obs[db.bySym.E.index] >= 0);
assert.ok(Math.abs(beam.value(row6061) - Math.sqrt(db.display[row6061.obs[db.bySym.E.index]]) / db.display[row6061.obs[db.bySym.rho.index]]) < 1e-12);
assert.ok(new Axis(db, 'rho; alert(1)').compiled.error, 'Formula text is parsed, never run');
assert.ok(new Axis(db, 'constructor').compiled.error);
assert.ok(Number.isNaN(new Axis(db, '-E').value(row6061)), 'A log axis refuses a negative value');

console.log(JSON.stringify({ passed: true, pairsCompared: compared, indexValuesCompared: scored, rows: db.rows.length }));
