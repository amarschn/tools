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

// Broad families enclose every subgroup and separated cluster in one region.
const polymer = (id,x,y,subgroup) => row(id,x,y,{family:'polymer',classification:['polymer',subgroup]});
const groupedRows = [polymer('pa6-a',1000,2,'PA6'),polymer('pa6-b',1100,2.1,'PA6'),
  polymer('pa6-c',1000,20,'PA6'),polymer('pa6-d',1100,21,'PA6'),
  polymer('peek-a',2000,5,'PEEK'),polymer('peek-b',2100,5.1,'PEEK'),
  row('metal-a',7800,200),row('metal-b',7900,210),
  {...polymer('limit',1e9,1e9,'PA6'),hasBounds:true}];
for (const shape of ['hulls','ellipses']) {
  const families = build(groupedRows,'x','y',shape,'family');
  assert.deepEqual(families.map(r=>r.label),['Polymers','Metals']);
  const region = families[0].points.map(p=>p.map(Math.log10));
  for (const point of groupedRows.filter(r=>r.family==='polymer'&&!r.hasBounds)) {
    const log = [Math.log10(point.x.value),Math.log10(point.y.value)];
    assert.ok(region.every((a,i)=>cross(a,region[(i+1)%region.length],log)>=-1e-10),'Family envelope contains all eligible grades');
  }
  assert.ok(Math.max(...families[0].points.map(p=>p[0]))<10000,'Reported bounds remain excluded');
  const subgroups = build(groupedRows,'x','y',shape,'subgroup').filter(r=>r.family==='polymer');
  assert.equal(subgroups.length,3,'Subgroups keep their original cluster separation');
  assert.deepEqual(build(groupedRows,'x','y',shape,'points'),[]);
}
const interval = row('interval',100,10,{x:{value:100,min:1,max:1000}});
const intervalRegion = build([interval],'x','y')[0];
assert.ok(Math.min(...intervalRegion.points.map(p=>p[0]))<1 && Math.max(...intervalRegion.points.map(p=>p[0]))>1000,'Family view preserves distant interval endpoints');
console.log('Ashby geometry: family containment, subgroup separation, independent shape/grouping, interval endpoints, and bound exclusion passed.');
