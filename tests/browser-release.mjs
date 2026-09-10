import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {chromium} from 'playwright';

const output = path.resolve('materials');
await fs.mkdir('test-results', {recursive:true});
const server = http.createServer(async (req,res) => {
  const url = new URL(req.url, 'http://localhost');
  let relative = decodeURIComponent(url.pathname).replace(/^\/nested\/reference\//, '/');
  const root = relative.startsWith('/prototype/') ? path.resolve('prototypes') : output;
  relative = relative.replace(/^\/prototype\//, '/');
  let file = path.resolve(root, '.' + relative);
  if (!file.startsWith(root + path.sep) && file !== root) {res.writeHead(403).end(); return;}
  try {
    const stat = await fs.stat(file);
    if (stat.isDirectory()) file = path.join(file, 'index.html');
    const data = await fs.readFile(file);
    res.writeHead(200, {'Content-Type':{'.html':'text/html','.mjs':'text/javascript','.js':'text/javascript','.css':'text/css','.json':'application/json','.csv':'text/csv'}[path.extname(file)] || 'text/plain'}).end(data);
  } catch {res.writeHead(404).end('Not found');}
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
const report = {hosting:[], assertions:[], consoleErrors:[], pageErrors:[]};
try {
  browser = await chromium.launch({headless:true});
  report.environment = {browser:browser.version(), node:process.version, platform:process.platform, architecture:process.arch};
  const context = await browser.newContext({viewport:{width:1360,height:1000}});
  const page = await context.newPage();
  page.on('pageerror', e => report.pageErrors.push(e.message));
  page.on('console', m => {if(m.type()==='error') report.consoleErrors.push(m.text());});
  const requests = [];
  page.on('request', r => requests.push(r.url()));
  async function settled() {await page.locator('#view[aria-busy="false"]').waitFor();}
  async function go(base, suffix='') {await page.goto(base+suffix);await settled();}
  async function search(q) {await page.locator('#query').fill(q);await page.locator('#search-form').evaluate(f => f.requestSubmit());await settled();}
  if (process.argv.includes('--capture')) {
    for (const variant of ['prototype','release']) {
      const base = variant === 'prototype' ? origin+'/prototype/05-dual-mode.html' : origin+'/';
      await page.goto(base);
      await page.waitForFunction(()=>!document.querySelector('#route-label').textContent.match(/Loading|Opening/));
      await page.screenshot({path:`test-results/${variant}-home.png`,fullPage:true});
      await page.locator('#query').fill(variant === 'prototype' ? 'AX60-T6' : '6061-T6');
      await page.locator('#query').press('Enter');
      await page.locator('.property-section').first().waitFor();
      await page.screenshot({path:`test-results/${variant}-record.png`,fullPage:true});
      await page.locator('#query').fill('tensile strength');
      await page.locator('#query').press('Enter');
      await page.locator('.tree').waitFor();
      await page.locator('.tree > .taxon > summary').first().click();
      await page.locator('.tree > .taxon[open] .node-body > .taxon').first().waitFor();
      await page.screenshot({path:`test-results/${variant}-tree.png`,fullPage:true});
    }
    await browser.close();
    await new Promise(resolve=>server.close(resolve));
    process.exit(0);
  }
  for (const mount of ['/', '/nested/reference/']) {
    const base = origin + mount;
    await context.clearCookies();
    await go(base);
    await page.evaluate(()=>localStorage.clear());
    await go(base);
    assert.equal(await page.locator('.mode-row').count(),2);
    assert.equal(await page.locator('.intro, .search-surface, .brand-mark').count(),0);
    assert.ok((await page.locator('#query').boundingBox()).y < 80);
    const before = requests.length;
    await search('6061-T6');
    await page.getByRole('heading', {name:'Aluminium 6061 · T6',exact:true}).waitFor();
    const newData = requests.slice(before).filter(u=>u.endsWith('.json'));
    assert.equal(newData.length,1,'one lazy payload opens a full datasheet');
    assert.ok(newData[0].includes('/records/al-6061.json'));
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≥ 240 MPa/);
    await page.locator('#unit-system').selectOption('imperial');
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≥ 35 ksi/);
    await page.reload(); await settled();
    assert.equal(await page.locator('#unit-system').inputValue(),'imperial');
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≥ 35 ksi/);
    await page.locator('[data-unit="tensile_yield_strength"]').selectOption('MPa');
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≥ 240 MPa/);
    await page.reload();await settled();
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≥ 240 MPa/);
    const citation = page.locator('#property-tensile_yield_strength .citation a');
    assert.match(await citation.getAttribute('href'), /hydro.*#page=2/);
    await page.locator('#property-tensile_yield_strength .citation summary').click();
    assert.match(await page.locator('#property-tensile_yield_strength .original').innerText(), /110|240/);
    await search('plastic strength');
    await page.locator('.notice strong').filter({hasText:'Which strength?'}).waitFor();
    await page.getByRole('link',{name:'Ultimate tensile strength',exact:true}).click();
    await settled();
    assert.match(page.url(), /intent=ultimate_tensile_strength/);
    assert.match(await page.locator('#route-label').innerText(), /Property overview/);
    assert.ok((await page.locator('[data-result-row]').count()) <= 50);
    await search('PEEK');
    await page.getByRole('heading',{name:'Polyether ether ketone (PEEK)',exact:true,level:1}).waitFor();
    await search('316L');
    await page.locator('.match-list').waitFor();
    assert.ok(await page.locator('[data-result-row]').count() > 1);
    await search('teca');
    await page.locator('.match-list').waitFor();
    assert.equal(await page.locator('[data-result-row]').count(),50);
    await search('strongest plastic');
    await page.locator('.notice strong').filter({hasText:'Comparison is not supported.'}).waitFor();
    await search('TECAPEEK tensile strength');
    await page.getByRole('heading',{name:'TECAPEEK',exact:true}).waitFor();
    assert.equal(await page.locator('.property-section').count(), 1);
    await page.getByRole('link',{name:'Show all properties'}).click(); await settled();
    assert.equal(await page.locator('.property-section').count(), 7);
    await page.goBack(); await settled();
    assert.equal(await page.locator('.property-section').count(), 1);
    await search('6061 T6 extrusion');
    await page.getByRole('heading',{name:'Aluminium 6061 · T6',exact:true}).waitFor();
    assert.match(await page.locator('#view').innerText(), /extrusion/);
    await search('TECAPEEK max service temperature');
    await page.locator('#property-max_service_temperature').waitFor();
    assert.match(await page.locator('#property-max_service_temperature').innerText(), /Unreported/);
    await go(base,'al-6061-t6/');
    await page.getByRole('heading',{name:'Aluminium 6061 · T6',exact:true}).waitFor();
    assert.match(page.url(), /state=al-6061-t6/);
    await go(base,'by/density/');
    await page.getByRole('heading',{name:'Density',exact:true}).waitFor();
    await page.locator('#taxon-metals > summary').click();
    await page.locator('#taxon-aluminium-alloys > summary').click();
    const treeRequests = requests.length;
    await page.locator('#material-al-6061 > summary').click();
    await page.locator('#material-al-6061 .observation').waitFor();
    assert.equal(requests.slice(treeRequests).filter(u=>u.endsWith('/records/al-6061.json')).length,1);
    await page.locator('#unit-system').selectOption('metric');
    await page.locator('#material-al-6061[open] .observation').waitFor();
    assert.match(await page.locator('#material-al-6061 .value').innerText(), /2700 kg\/m³/);
    const cachedRequests = requests.length;
    await page.locator('#material-al-6061 > summary').click();
    await page.waitForFunction(()=>!document.querySelector('#material-al-6061 .observation'));
    await page.locator('#material-al-6061 > summary').click();
    await page.locator('#material-al-6061 .observation').waitFor();
    assert.equal(requests.slice(cachedRequests).filter(u=>u.endsWith('.json')).length,0);
    await page.locator('#material-al-6061 > summary').getByRole('link',{name:'Open focused record'}).click();
    await settled();
    await page.getByRole('heading',{name:'Aluminium 6061',exact:true}).waitFor();
    assert.equal(await page.locator('.property-section').count(),1);
    assert.match(await page.locator('#property-density .value').innerText(), /2700 kg\/m³/);
    await go(base,'?property=tensile_yield_strength&category=aluminium-alloys');
    await page.locator('#material-al-6061 > summary').click();
    await page.locator('#state-al-6061-t6 > summary').click();
    assert.match(await page.locator('#state-al-6061-t6 .value').innerText(), /≥ 240 MPa/);
    await page.locator('#state-al-6061-t6 .citation summary').click();
    await page.locator('[data-unit="tensile_yield_strength"]').selectOption('ksi');
    await page.locator('#state-al-6061-t6[open] .citation details[open]').waitFor();
    assert.match(await page.locator('#state-al-6061-t6 .value').innerText(), /≥ 35 ksi/);
    await page.getByRole('link',{name:'Sources',exact:true}).click(); await settled();
    assert.equal(await page.locator('.source-card').count(),5);
    await go(base, '?q=TECAPEEK+tensile+strength');
    await page.locator('#unit-system').selectOption('metric');
    await page.screenshot({path:`test-results/release-${mount==='/'?'desktop':'subpath'}.png`,fullPage:true});
    report.hosting.push({mount,passed:true});
  }
  // At 320px the search, long record names, values and citations stay in view.
  await page.setViewportSize({width:320,height:800});
  await go(origin+'/?q=TECAPEEK+tensile+strength');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),'320px overflow');
  await page.screenshot({path:'test-results/release-mobile.png',fullPage:true});
  await go(origin+'/?property=thermal_conductivity&category=engineering-plastics');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),'320px overview overflow');
  await page.screenshot({path:'test-results/release-mobile-overview.png',fullPage:true});
  report.assertions.push('320px layout', 'root and subpath deep links', 'units and property overrides survive reload', 'one lazy record request', 'expandable taxonomy and inline observations', 'expanded tree survives unit changes', 'collapsed record reuses cached data', 'clarification and comparison boundary', 'source locators', 'browser history', 'missing property', '50-row cap');
  // Input entered before the index arrives must survive initialization.
  const delayed = await context.newPage();
  await delayed.route('**/index.json', async route => {await new Promise(r=>setTimeout(r,400));await route.continue();});
  await delayed.goto(origin, {waitUntil:'domcontentloaded'});
  await delayed.locator('#query').fill('6061-T4');
  await delayed.getByRole('heading',{name:'Aluminium 6061 · T4',exact:true}).waitFor();
  report.assertions.push('typing during cold load');
  await delayed.close();
  // Mismatched lazy data must fail clearly rather than displaying mixed builds.
  const mismatch = await context.newPage();
  await mismatch.route('**/records/al-6061.json', async route => {
    const response = await route.fetch();const body = await response.json();body.build_id='stale-build';
    await route.fulfill({json:body});
  });
  await mismatch.goto(origin+'/?material=al-6061');
  await mismatch.getByRole('alert').waitFor();
  assert.match(await mismatch.getByRole('alert').innerText(), /versions differ/);
  await mismatch.unroute('**/records/al-6061.json');
  await mismatch.getByRole('button',{name:'Try again'}).click();
  await mismatch.getByRole('heading',{name:'Aluminium 6061',exact:true}).waitFor();
  await mismatch.close();
  report.assertions.push('cache mismatch detection and retry');
  assert.deepEqual(report.pageErrors, []);
  assert.deepEqual(report.consoleErrors, []);
  const external = requests.filter(u=>!u.startsWith(origin));
  assert.deepEqual(external, [], 'normal browsing has no external requests');
  assert.ok(!requests.some(u=>u.includes('synthetic-corpus') || u.endsWith('/catalog.json')), 'browse never fetches the whole corpus');
  await fs.writeFile('test-results/release-browser.json', JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
} finally {
  await browser?.close();
  await new Promise(resolve=>server.close(resolve));
}
