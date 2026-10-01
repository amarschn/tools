/* Numerical drawing invariants; no browser or charting dependency required. */
const assert = require('node:assert/strict');
const { roundedHull, splitClusters, build } = require('../../tools/materials-explorer/envelopes.js');
const input = [[0,0], [1,.2], [.4,1], [.5,.4]];
const padding = .055;
const outline = roundedHull(input, padding);
const cross = (a,b,c) => (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
for (const point of input) {
  assert.ok(outline.every((a,i) => cross(a,outline[(i+1)%outline.length],point) >= -1e-10), 'Every endpoint stays enclosed');
}
for (let axis=0;axis<2;axis++) {
  assert.ok(Math.max(...outline.map(p=>p[axis])) <= Math.max(...input.map(p=>p[axis]))+padding+1e-10);
  assert.ok(Math.min(...outline.map(p=>p[axis])) >= Math.min(...input.map(p=>p[axis]))-padding-1e-10);
}
assert.equal(splitClusters([[0,0],[.1,.1],[2,2],[2.1,2.1]]).length, 2, 'Disconnected clusters cannot create a giant hull');
const row = (id,x,y,extra={}) => ({id, material_id:id, family:'metal', classification:['metal','titanium'], x:{value:x}, y:{value:y}, ...extra});
const rows = [row('a',1000,10),row('b',1100,12),row('bound',1,10000,{hasBounds:true})];
for (const mode of ['hulls','ellipses']) {
  const regions = build(rows,'x','y',mode);
  assert.equal(regions.length,1);
  assert.ok(regions[0].points.flat().every(v=>Number.isFinite(v)&&v>0));
  assert.ok(Math.min(...regions[0].points.map(p=>p[0]))>800,'The specified bound must not define an envelope');
}
assert.deepEqual(build(rows,'x','y','points'),[]);
assert.equal(build([row('a',1000,10),row('b',1000,10)],'x','y').length,1,'Coincident values produce a small outline');
console.log('Ashby geometry: containment, bounded padding, cluster separation, degenerate points, and specified-limit exclusion passed.');
