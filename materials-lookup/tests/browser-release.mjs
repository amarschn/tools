import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const project = fileURLToPath(new URL('../', import.meta.url));
const repo = path.resolve(project, '..');
const output = path.join(repo, 'tools/materials');
const results = path.join(project, 'test-results');
await fs.mkdir(results, {recursive:true});
const server = http.createServer(async (req,res) => {
  const url = new URL(req.url, 'http://localhost');
  let relative = decodeURIComponent(url.pathname).replace(/^\/(?:nested\/reference|tools\/materials)\//, '/');
  const shared = relative.startsWith('/shared/') || relative === '/manifest.json';
  const root = shared ? repo : relative.startsWith('/prototype/') ? path.join(project, 'prototypes') : output;
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
  const context = await browser.newContext({viewport:{width:1360,height:1000}, colorScheme:'light'});
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  // Keep analytics events inspectable without sending test traffic to GA.
  await context.route('https://www.googletagmanager.com/**', route => route.fulfill({contentType:'text/javascript', body:''}));
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
      await page.screenshot({path:path.join(results, `${variant}-home.png`),fullPage:true});
      await page.locator('#query').fill(variant === 'prototype' ? 'AX60-T6' : '6061-T6');
      await page.locator('#query').press('Enter');
      await page.locator('.property-section').first().waitFor();
      await page.screenshot({path:path.join(results, `${variant}-record.png`),fullPage:true});
      await page.locator('#query').fill('tensile strength');
      await page.locator('#query').press('Enter');
      await page.locator('.tree').waitFor();
      await page.locator('.tree > .taxon > summary').first().click();
      await page.locator('.tree > .taxon[open] .node-body > .taxon').first().waitFor();
      await page.screenshot({path:path.join(results, `${variant}-tree.png`),fullPage:true});
    }
    await browser.close();
    await new Promise(resolve=>server.close(resolve));
    process.exit(0);
  }
  for (const mount of ['/', '/nested/reference/', '/tools/materials/']) {
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
    const citation = page.locator('#property-tensile_yield_strength .citation');
    assert.match(await citation.innerText(), /Hydro · p\. 2/);
    assert.equal(await citation.locator('a, iframe, embed, object').count(),0);
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
    assert.equal(await page.locator('.source-card').count(),28);
    assert.equal(await page.locator('.source-card a, iframe, embed, object').count(),0);
    for (const file of ['hydro-6061.pdf','hydro-6063.pdf','copper-alloys-guide.pdf','timet-6-4.pdf','atlas-engineering-bar.pdf','uddeholm-arne.pdf','private-sources/index.html']) {
      const response = await context.request.get(base+file);
      assert.equal(response.status(),404,'public document access must be absent');
    }
    await search('2205');
    await page.getByRole('heading',{name:'Stainless steel Forta DX 2205',exact:true}).waitFor();
    assert.match(await page.locator('#property-tensile_yield_strength .value').innerText(), /≥ 72\.5 ksi/);
    assert.match(await page.locator('#property-tensile_yield_strength .citation').innerText(), /Outokumpu · p\. 9/);
    assert.equal(await page.locator('.citation a, iframe, embed, object').count(),0);
    await search('Alloy 825');
    await page.getByRole('heading',{name:'Nickel alloy Ultra Alloy 825',exact:true}).waitFor();
    await page.locator('#unit-system').selectOption('metric');
    await search('6063 T6 extrusion');
    await page.getByRole('heading',{name:'Aluminium 6063 · T6',exact:true}).waitFor();
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≥ 170 MPa/);
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /Thickness: ≤ 3\.1496 mm/);
    await page.locator('#unit-system').selectOption('imperial');
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /Thickness: ≤ 0\.124 in/);
    await search('C11000');
    await page.getByRole('heading',{name:'Copper C11000',exact:true}).waitFor();
    await page.locator('[data-unit="density"]').selectOption('lb/in^3');
    assert.match(await page.locator('#property-density .value').innerText(), /0\.321–0\.323 lb\/in³/);
    await search('bronze density');
    await page.locator('#taxon-bronzes[open]').waitFor();
    await page.locator('#material-cu-c51000 > summary').click();
    await page.locator('#material-cu-c51000 .observation').waitFor();
    await search('Ti6246 DA');
    await page.getByRole('heading',{name:'Titanium Ti-6Al-2Sn-4Zr-6Mo · Duplex annealed',exact:true}).waitFor();
    await page.locator('#property-tensile_yield_strength [id^="test-"] > summary').click();
    await page.locator('#property-tensile_yield_strength [id^="test-"][open]').waitFor();
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≤2\.00 in/);
    await page.locator('#unit-system').selectOption('metric');
    await search('4140');
    await page.getByRole('heading',{name:'Steel Atlas 4140',exact:true}).waitFor();
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≥ 740 MPa/);
    await page.locator('#property-tensile_yield_strength [id^="test-"] > summary').first().click();
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /≤180 mm; AS1444 condition U/);
    await search('1045');
    await page.getByRole('heading',{name:'Steel Atlas 1045',exact:true}).waitFor();
    assert.match(await page.locator('#property-tensile_yield_strength').innerText(), /Typical minimum \(not guaranteed\)/);
    await search('D2');
    await page.getByRole('heading',{name:'Tool steel Uddeholm Sverker 21',exact:true}).waitFor();
    assert.match(await page.locator('#property-density').innerText(), /62 HRC/);
    assert.match(await page.locator('#property-density').innerText(), /7700 kg\/m³/);
    await search('steel density');
    await page.locator('#taxon-steels[open]').waitFor();
    assert.equal(await page.locator('#taxon-steels #taxon-stainless-steels').count(),1);
    await page.locator('#taxon-tool-steels > summary').click();
    await page.locator('#material-steel-uddeholm-arne > summary').click();
    await page.locator('#material-steel-uddeholm-arne .state-node > summary').click();
    await page.locator('#material-steel-uddeholm-arne .observation').first().waitFor();
    await go(base, '?q=TECAPEEK+tensile+strength');
    await page.locator('#unit-system').selectOption('metric');
    await page.screenshot({path:path.join(results, `release-${mount==='/'?'desktop':mount.includes('tools')?'integrated':'subpath'}.png`),fullPage:true});
    report.hosting.push({mount,passed:true});
  }
  // At 320px the search, long record names, values and citations stay in view.
  await page.setViewportSize({width:320,height:800});
  await go(origin+'/?q=TECAPEEK+tensile+strength');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),'320px overflow');
  await page.screenshot({path:path.join(results, 'release-mobile.png'),fullPage:true});
  await go(origin+'/?property=thermal_conductivity&category=engineering-plastics');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),'320px overview overflow');
  await page.screenshot({path:path.join(results, 'release-mobile-overview.png'),fullPage:true});
  for (const query of ['6063 T6 extrusion', 'C11000', 'Ti6246 DA', '1045', 'H13']) {
    await go(origin+'/?q='+encodeURIComponent(query));
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth), query+' mobile overflow');
  }
  await page.screenshot({path:path.join(results, 'release-mobile-steel.png'),fullPage:true});
  report.assertions.push('nonferrous searches and bronze tree', 'one-sided thickness limits in metric and imperial', 'copper source ranges', 'titanium state and size scope');
  report.assertions.push('steel grade searches and inclusive steel taxonomy', 'typical steel minima stay qualified', 'tool steel hardness conditions');
  report.assertions.push('320px layout', 'root and subpath deep links', 'units and property overrides survive reload', 'one lazy record request', 'expandable taxonomy and inline observations', 'expanded tree survives unit changes', 'collapsed record reuses cached data', 'clarification and comparison boundary', 'text-only citations; document paths unavailable', 'new specialty-metal searches', 'browser history', 'missing property', '50-row cap');
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
  const external = requests.filter(u=>!u.startsWith(origin) && !u.startsWith('https://www.googletagmanager.com/'));
  assert.deepEqual(external, [], 'lookup data stays local; only the shared GA script is external');
  assert.ok(!requests.some(u=>u.includes('synthetic-corpus') || u.endsWith('/catalog.json')), 'browse never fetches the whole corpus');
  // Integrated toolbar, first-paint theme preference, sharing and downloads.
  await page.setViewportSize({width:1360,height:1000});
  const integrated = origin + '/tools/materials/';
  await go(integrated, '?q=6061-T6');
  assert.equal(await page.getByRole('link', {name:'Tools',exact:true}).getAttribute('href'), '../../');
  assert.equal(await page.locator('script[type="application/ld+json"]').count(), 2);
  assert.equal(await page.locator('#theme').inputValue(), 'system');
  await page.emulateMedia({colorScheme:'dark'});
  const background = () => page.locator('html').evaluate(el => getComputedStyle(el).backgroundColor);
  assert.equal(await background(), 'rgb(21, 21, 21)');
  for (const theme of ['light', 'dark']) {
    await page.locator('#settings > summary').click();
    await page.locator('#theme').selectOption(theme);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#settings').getAttribute('open'), null);
    await page.reload(); await settled();
    assert.equal(await page.locator('#theme').inputValue(), theme);
    assert.equal(await background(), theme === 'dark' ? 'rgb(21, 21, 21)' : 'rgb(255, 255, 255)');
    await page.locator('#property-tensile_yield_strength .citation summary').click();
    await page.screenshot({path:path.join(results, `release-${theme}.png`), fullPage:true});
    await page.setViewportSize({width:320,height:800});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth));
    await page.locator('#settings > summary').click();
    assert.ok(await page.locator('#theme').isVisible());
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path:path.join(results, `release-mobile-${theme}.png`), fullPage:true});
    await page.keyboard.press('Escape');
    await page.setViewportSize({width:1360,height:1000});
  }
  await page.locator('#copy-link').click();
  assert.equal(await page.evaluate(()=>navigator.clipboard.readText()), page.url());
  await page.waitForFunction(()=>document.querySelector('#copy-link').textContent === 'Copied');
  assert.ok(await page.evaluate(()=>dataLayer.some(event=>event[0]==='event' && event[1]==='export_action' && event[2].tool==='materials')));
  const manifest = JSON.parse(await fs.readFile(path.join(output, 'release-manifest.json'), 'utf8'));
  for (const [label, file] of [['JSON', manifest.catalog], ['CSV', manifest.csv]]) {
    const downloadPromise = page.waitForEvent('download');
    await page.locator('footer').getByRole('link', {name:label,exact:true}).click();
    const download = await downloadPromise;
    assert.equal(await download.failure(), null);
    assert.deepEqual(await fs.readFile(await download.path()), await fs.readFile(path.join(output, file)));
  }
  const recordDownload = page.waitForEvent('download');
  await page.locator('.section-actions').getByRole('link', {name:'JSON',exact:true}).click();
  const record = JSON.parse(await fs.readFile(await (await recordDownload).path(), 'utf8'));
  assert.equal(record.material.id, 'al-6061');
  assert.ok(record.observations.some(o=>o.state_id==='al-6061-t6'));
  await go(integrated, '?q=unobtainium+thing');
  assert.match(await page.locator('#view').innerText(), /No matching material or property/);
  for (const suffix of ['?q=0','?q=-999999999999999999999999']) {
    await go(integrated, suffix);
    assert.equal(await page.getByRole('alert').count(), 0);
    assert.ok((await page.locator('[data-result-row]').count()) <= 50);
  }
  await go(integrated, '?material=al-6061&state=invalid');
  assert.match(await page.getByRole('alert').innerText(), /Unknown state/);
  await page.getByRole('link', {name:'New search',exact:true}).click(); await settled();
  assert.equal(await page.locator('.mode-row').count(), 2);
  assert.deepEqual(report.pageErrors, []);
  assert.deepEqual(report.consoleErrors, []);
  report.assertions.push('system, light and dark themes with persisted preference', '320px settings and source details', 'Tools navigation and structured metadata', 'copy link and export analytics', 'downloaded JSON and CSV match published artifacts', 'invalid query and state recovery');
  await fs.writeFile(path.join(results, 'release-browser.json'), JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
} finally {
  await browser?.close();
  await new Promise(resolve=>server.close(resolve));
}
