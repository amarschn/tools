import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createSearch, MAX_RESULTS} from '../src/search.mjs';
import {displayUnit, resultText, summaryText, summarize, significant, thicknessText, resultBasis} from '../src/format.mjs';

const output = fileURLToPath(new URL('../../tools/materials/', import.meta.url));
const manifest = JSON.parse(fs.readFileSync(path.join(output, 'release-manifest.json')));
const index = JSON.parse(fs.readFileSync(path.join(output, manifest.index)));
const resolve = createSearch(index);
const routeCases = [
  ['6061', {material:'al-6061'}],
  ['6061-T6', {material:'al-6061', state:'al-6061-t6'}],
  ['6061 T6 extrusion', {material:'al-6061', state:'al-6061-t6', form:'extrusion'}],
  ['density', {property:'density'}],
  ['plastic density', {category:'engineering-plastics', property:'density'}],
  ['PEEK', {category:'polymer-peek'}],
  ['TECAPEEK', {material:'tecapeek'}],
  ['TECAPEEK tensile strength', {material:'tecapeek', property:'ultimate_tensile_strength'}],
  ['ceramic flexural strength', {category:'ceramics', property:'flexural_strength'}],
  ['yield strength', {property:'tensile_yield_strength'}],
  ['stiffness', {property:'youngs_modulus'}],
  ['polymers', {category:'engineering-plastics'}],
  ['2205', {material:'stainless-forta-dx-2205'}],
  ['253 MA', {material:'stainless-therma-253-ma'}],
  ['904L', {material:'stainless-ultra-904l'}],
  ['Alloy 825', {material:'nickel-ultra-alloy-825'}],
  ['N08367', {material:'stainless-ultra-6xn'}],
  ['6063 T6 extrusion', {material:'al-6063', state:'al-6063-t6', form:'extrusion'}],
  ['6005A-T61', {material:'al-6005a', state:'al-6005a-t61'}],
  ['1100-O', {material:'al-1100', state:'al-1100-o'}],
  ['C11000', {material:'cu-c11000'}],
  ['C36000', {material:'cu-c36000'}],
  ['C51000', {material:'cu-c51000'}],
  ['copper thermal conductivity', {category:'copper-alloys', property:'thermal_conductivity'}],
  ['brass density', {category:'brasses', property:'density'}],
  ['bronze density', {category:'bronzes', property:'density'}],
  ['titanium density', {category:'titanium-alloys', property:'density'}],
  ['Ti6Al4V', {material:'ti-6al-4v'}],
  ['Ti6246 DA', {material:'ti-6al-2sn-4zr-6mo', state:'ti-6246-da'}],
  ['steel density', {category:'steels', property:'density'}],
  ['stainless steel density', {category:'stainless-steels', property:'density'}],
  ['carbon steel yield strength', {category:'carbon-steels', property:'tensile_yield_strength'}],
  ['tool steel thermal conductivity', {category:'tool-steels', property:'thermal_conductivity'}],
  ['1045', {material:'steel-atlas-1045'}],
  ['4140', {material:'steel-atlas-4140'}],
  ['4340', {material:'steel-atlas-4340'}],
  ['34CrNiMo6', {material:'steel-atlas-6582'}],
  ['18CrNiMo7-6', {material:'steel-atlas-6587'}],
  ['8620H', {material:'steel-atlas-8620h'}],
  ['12L14', {material:'steel-atlas-12l14fm'}],
  ['O1', {material:'steel-uddeholm-arne'}],
  ['A2', {material:'steel-uddeholm-rigor'}],
  ['D2', {material:'steel-uddeholm-sverker-21'}],
  ['H13', {material:'steel-uddeholm-orvar-supreme'}],
];
for (const [q, expected] of routeCases) assert.deepEqual(resolve(q), {kind:'route', route:expected}, q);
assert.equal(resolve('plastic strength').kind, 'clarify');
assert.deepEqual(resolve('plastic strength', 'ultimate_tensile_strength').route, {category:'engineering-plastics', property:'ultimate_tensile_strength'});
assert.equal(resolve('strongest plastic').kind, 'comparison');
assert.equal(resolve('6061 vs 316L').kind, 'comparison');
assert.equal(resolve('316L').kind, 'matches');
assert.equal(resolve('TECAPEK').matches[0].id, 'tecapeek');
assert.equal(resolve('unobtainium thing').total, 0);
assert.ok(resolve('teca').matches.length <= MAX_RESULTS);

const prop = id => index.properties.find(p => p.id === id);
const imperial = {system:'imperial', overrides:{}}, metric = {system:'metric', overrides:{}};
const yieldProp = prop('tensile_yield_strength');
const point = {property_id:yieldProp.id, status:'active', result:{kind:'lower_bound', canonical:{value:240e6}, reported:{significant_figures:2}}};
assert.equal(resultText(point, displayUnit(yieldProp, metric)), '≥ 240 MPa');
assert.equal(resultText(point, displayUnit(yieldProp, imperial)), '≥ 35 ksi');
assert.equal(displayUnit(prop('youngs_modulus'), metric).unit, 'GPa');
assert.equal(displayUnit(prop('poissons_ratio'), metric).unit, '1');
assert.equal(displayUnit(prop('specific_heat'), imperial).unit, 'BTU/(lb*degF)');
assert.equal(significant(27679.904710203122*.098, 2), '2700');
assert.equal(thicknessText({minimum:null, maximum:.124*.0254}, 'imperial'), '≤ 0.124 in');
assert.equal(thicknessText({minimum:.5*.0254, maximum:null}, 'metric'), '≥ 12.7 mm');
assert.equal(thicknessText({minimum:.062*.0254, maximum:.124*.0254}, 'metric'), '1.5748–3.1496 mm');
assert.equal(resultBasis({...point, basis:'typical'}), 'Typical minimum (not guaranteed)');
assert.equal(resultBasis({...point, basis:'minimum'}), 'Minimum');
assert.equal(summaryText(summarize([point], yieldProp.id), displayUnit(yieldProp, metric)), '≥ 240 MPa');
const interval = {...point, result:{kind:'interval', canonical:{minimum:470e6, maximum:520e6}, reported:{significant_figures:2}}};
assert.equal(resultText(interval, displayUnit(yieldProp, imperial)), '68–75 ksi');
const uncertain = {...point, result:{...point.result, kind:'point'}, uncertainty:{canonical:{value:5e6}, reported:{significant_figures:1}}};
assert.equal(resultText(uncertain, displayUnit(yieldProp, imperial)), '35 ± 0.7 ksi');
const temperature = {property_id:'max_service_temperature', result:{kind:'point', canonical:{value:373.15}, reported:{significant_figures:3}}, uncertainty:{canonical:{value:5}, reported:{significant_figures:1}}};
assert.equal(resultText(temperature, displayUnit(prop('max_service_temperature'), imperial)), '212 ± 9 °F');
// Browser and compiler summaries must agree for the real catalog, including bounds.
const directory = path.join(output, manifest.index.replace('index.json', 'records/'));
for (const filename of fs.readdirSync(directory)) {
  const record = JSON.parse(fs.readFileSync(directory + filename));
  for (const p of index.properties) {
    const js = summarize(record.observations, p.id), py = record.summaries[p.id];
    for (const prefs of [metric, imperial]) assert.equal(summaryText(js, displayUnit(p,prefs)), summaryText(py, displayUnit(p,prefs)), `${filename}: ${p.id}`);
  }
}
const times=[];
for (let n=0;n<8;n++) for (const [q] of routeCases) {const start=performance.now();resolve(q);if(n>1)times.push(performance.now()-start);}
times.sort((a,b)=>a-b);
console.log(`Release search: ${routeCases.length + 8} routing checks; conversions, bounds, uncertainty, and ${fs.readdirSync(directory).length} record projections passed. Query p95 ${times[Math.floor(times.length*.95)].toFixed(2)} ms. Index ${manifest.index_gzip_bytes} bytes gzip.`);
