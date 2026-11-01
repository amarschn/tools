/* Serve the repo root, then pass its Ashby Chart URL to this script.
   BROWSER=webkit or BROWSER=firefox runs the same checks in those engines. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const playwright = require(process.env.PLAYWRIGHT_MODULE || '/opt/homebrew/lib/node_modules/@playwright/test');
const base = process.argv.find(arg => /^https?:/.test(arg)) || 'http://127.0.0.1:8158/tools/ashby-chart/';
const browserName = process.env.BROWSER || 'chromium';
const outDir = process.env.ASHBY_SCREENSHOTS || '/private/tmp';

(async () => {
  const browser = await playwright[browserName].launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'light', serviceWorkers: 'block', acceptDownloads: true });
    await context.route('**/www.googletagmanager.com/**', route => route.fulfill({ body: '', contentType: 'application/javascript' }));
    await context.route('**/google-analytics.com/**', route => route.fulfill({ body: '' }));
    const page = await context.newPage();
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error' && !/Failed to load resource|version mismatch/i.test(message.text())) errors.push(message.text()); });
    page.on('request', request => requests.push(request.url()));
    page.setDefaultTimeout(20000);
    const ready = async () => { await page.locator('#explorer-main[data-state="ready"]').waitFor(); await page.waitForTimeout(40); };
    const rows = () => page.evaluate(() => MaterialsExplorer.getRows());
    const shapes = () => page.evaluate(() => MaterialsExplorer.getShapes());
    const search = async text => { await page.locator('#material-search').fill(text); await page.waitForTimeout(40); };
    const select = async (id, value) => { await page.locator('#tab-show').click(); await page.locator('#' + id).selectOption(value); await page.waitForTimeout(40); };
    const view = async name => { await page.locator('#tab-show').click(); await page.getByRole('button', { name, exact: true }).click(); await page.waitForTimeout(300); };
    const nativeSelection = () => page.evaluate(() => { const s = getSelection(); return { collapsed: s.isCollapsed, text: s.toString().length }; });
    const noSelection = async where => { const s = await nativeSelection(); assert.ok(s.collapsed && !s.text, `${where}: native selection ${JSON.stringify(s)}`); };
    const chartBox = () => page.locator('#ashby-chart canvas').boundingBox();
    const screen = (test, fromEnd) => page.evaluate(([src, end]) => {
      const f = eval(src), pl = MaterialsExplorer.getPlot(), b = pl.plotBox;
      const list = pl.rows.filter(r => !r.dim && pl.sx(r.tx) > b.l + 40 && pl.sx(r.tx) < b.r - 40 && pl.sy(r.ty) > b.t + 40 && pl.sy(r.ty) < b.b - 80).filter(f);
      const row = end ? list.at(-1) : list[0];
      return row && { x: pl.sx(row.tx), y: pl.sy(row.ty), name: row.name, id: row.m.id, key: row.key };
    }, [test, !!fromEnd]);

    await page.goto(base);
    await ready();
    await page.waitForTimeout(200);

    /* ---------- page and SEO ---------- */
    assert.equal(await page.locator('#loading-overlay').isVisible(), false);
    assert.equal(await page.locator('h1').innerText(), 'Ashby Chart');
    assert.equal(await page.title(), 'Ashby Chart | Material Selection');
    assert.match(await page.locator('meta[name="description"]').getAttribute('content'), /Ashby charts/);
    assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'), 'https://transparent.tools/tools/ashby-chart/');
    assert.match(await page.locator('#background summary').innerText(), /Reading an Ashby chart/);
    assert.ok(!requests.some(url => /plotly/i.test(url)), 'Plotly is gone');
    assert.ok(!requests.some(url => /selection-details\.json/.test(url)), 'Citations wait until someone needs them');
    assert.ok(!requests.some(url => /materials\/selection\.json/.test(url)), 'The large pair file is not loaded');
    assert.ok(!requests.some(url => /\/data\/materials\/materials\.json/.test(url)), 'No legacy dataset is requested');
    const baseline = await page.evaluate(() => MaterialsExplorer.getData());
    assert.equal(baseline.counts.materials, 1453);
    assert.match(await page.locator('#data-status').innerText(), /1,453 materials/);
    assert.equal((await rows()).length, 1185);
    assert.equal(await page.locator('#stack').isHidden(), true, 'The stack is an add-on');
    assert.equal(await page.locator('#results-box').isHidden(), true);
    assert.equal(await page.locator('#tab-inspect').getAttribute('tabindex'), '-1');
    const layout = await page.evaluate(() => ({ app: document.querySelector('.first-screen').getBoundingClientRect().bottom, height: innerHeight, doc: document.documentElement.scrollHeight }));
    assert.ok(layout.app <= layout.height + 1, 'The app fits the first screen');
    assert.ok(layout.doc > layout.height, 'The explanation is below it');
    await page.screenshot({ path: `${outDir}/ashby-${browserName}-default.png` });

    /* ---------- shapes ---------- */
    const families = await shapes();
    assert.equal(new Set(families.map(s => s.family)).size, families.length, 'One shape per family');
    assert.ok(families.every(s => s.loops === 1));
    assert.ok(families.some(s => s.label === 'Polymers'));
    const declared = families.reduce((sum, s) => sum + s.outside, 0);
    assert.match(await page.locator('#outside-note').innerText(), new RegExp(`^${declared} isolated`));
    await select('grouping', 'subgroup');
    const subgroupCount = (await shapes()).filter(s => s.family === 'polymer').length;
    assert.ok(subgroupCount > 1, 'Polymer classes stay distinct');
    assert.equal((await rows()).length, 1185, 'Grouping does not change the data');
    let link = new URL(await page.evaluate(() => MaterialsExplorer.getShareUrl()));
    assert.equal(link.searchParams.get('grouping'), 'subgroup');
    await page.goto(link.href); await ready();
    assert.equal(await page.locator('#grouping').inputValue(), 'subgroup');
    assert.equal((await shapes()).filter(s => s.family === 'polymer').length, subgroupCount);
    await select('envelope-mode', 'pebble');
    assert.ok((await shapes()).length > 0);
    await select('envelope-mode', 'none');
    assert.equal((await shapes()).length, 0);
    assert.ok(await page.locator('#setting-points').isChecked());
    assert.ok(await page.locator('#setting-points').isDisabled());
    assert.equal((await rows()).length, 1185);

    // Old links keep working: points-only names, and the earlier outline names.
    for (const oldQuery of ['envelope-mode=points&setting-points=0', 'setting-blobs=0', 'grouping=points']) {
      await page.goto(base + '?' + oldQuery); await ready();
      assert.equal((await shapes()).length, 0, oldQuery);
      assert.equal(await page.locator('#setting-points').isChecked(), true);
    }
    await page.goto(base + '?envelope-mode=hulls&grouping=family&x-prop=density&y-prop=tensile_yield_strength&families=metal,polymer&perf-index=strong_light_tie&temperature-filter=ambient&basis-filter=all&material-search=6061&top-n=3&setting-ranges=1&setting-isolines=1&setting-labels=0');
    await ready();
    assert.equal(await page.locator('#envelope-mode').inputValue(), 'pebble');
    assert.deepEqual((await rows()).map(r => r.state_id).sort(), ['al-6061-t4', 'al-6061-t6'], 'A full old link restores axes, filters and search');
    assert.equal(await page.locator('#perf-index').inputValue(), 'strong_light_tie');
    assert.equal(await page.locator('#top-n').inputValue(), '3');
    await page.goto(base); await ready();

    /* ---------- honest values: titanium, 6061 tempers, bounds, intervals ---------- */
    await search('titanium');
    const titanium = await rows();
    assert.equal(titanium.length, 3);
    const timet = titanium.filter(r => r.temperatures_K.length);
    assert.equal(timet.length, 2);
    assert.ok(timet.every(r => r.temperatures_K.includes(293.15) && r.temperatures_K.includes(295.15)));
    await page.locator('#tab-browse').click();
    await page.locator('#material-list button').filter({ hasText: 'Ti-6Al-4V' }).first().click();
    await page.waitForFunction(() => /°C/.test(document.getElementById('card-props').innerText));
    assert.match(await page.locator('#card-name').innerText(), /Ti-6Al-4V/);
    assert.match(await page.locator('#card-props').innerText(), /20.0 °C/);
    assert.match(await page.locator('#card-props').innerText(), /22.0 °C/);
    assert.match(await page.locator('#card-meta').innerText(), /Room-temperature comparison/);
    assert.ok(requests.some(url => /selection-details\.json/.test(url)), 'Citations load on demand');
    let download = page.waitForEvent('download');
    await page.locator('#export-csv').click();
    const titaniumCsv = await fs.readFile(await (await download).path(), 'utf8');
    assert.match(titaniumCsv, /20.0 °C/); assert.match(titaniumCsv, /22.0 °C/);
    await page.locator('#card-close').click();

    // A material with no value on these axes is still findable, with a chart that can show it.
    await search('elastomer');
    assert.equal((await rows()).length, 0);
    assert.ok(await page.locator('#empty-state').isVisible());
    assert.equal(await page.locator('#material-list button').count(), 110);
    await page.locator('#material-list button').filter({ hasText: 'Mold Max 10' }).first().click();
    await page.getByRole('button', { name: 'Show tensile strength chart', exact: true }).click();
    await page.waitForTimeout(300);
    assert.match(await page.locator('#y-btn').innerText(), /Ultimate tensile strength/);
    assert.equal((await rows()).length, 110);

    // Wood: computed modulus on the main chart, and the printed bending value stays separate.
    await select('temperature-filter', 'ambient');
    await select('basis-filter', 'all');
    await view('Stiffness');
    await search('wood');
    assert.equal((await rows()).length, 107);
    await view('Bending stiffness');
    assert.match(await page.locator('#y-btn').innerText(), /Flexural modulus/);
    assert.equal((await rows()).length, 107);
    await view('Compressive strength');
    assert.equal((await rows()).length, 107);
    await view('Bending stiffness');
    await page.locator('#tab-browse').click();
    await page.locator('#material-list button').filter({ hasText: 'Red alder' }).click();
    await page.waitForFunction(() => /moisture/.test(document.getElementById('card-props').innerText));
    assert.match(await page.locator('#card-props').innerText(), /12.0% moisture/);
    assert.match(await page.locator('#card-props').innerText(), /9.50 GPa/);
    await page.locator('#card-close').click();

    await view('Tensile strength');
    await search('foam');
    assert.equal((await rows()).length, 29);
    await view('Stiffness');
    assert.equal((await rows()).length, 15);
    await search('');

    // 6061 tempers stay separate, and bounds are drawn open and never make a shape.
    await view('Yield strength');
    await search('6061');
    let sixty = await rows();
    assert.equal(sixty.length, 2);
    assert.deepEqual(sixty.map(r => r.state_id).sort(), ['al-6061-t4', 'al-6061-t6']);
    assert.ok(sixty.every(r => r.hasBounds));
    assert.equal((await shapes()).length, 0, 'Bounds do not create a family shape');
    assert.ok(await page.evaluate(() => MaterialsExplorer.getPlot().rows.filter(r => !r.dim).every(r => r.bound)));
    await page.locator('#tab-rank').click();
    await page.locator('#perf-index').selectOption('strong_light_tie');
    await page.waitForTimeout(60);
    const box = await chartBox();
    const upper = await page.evaluate(() => { const pl = MaterialsExplorer.getPlot(), r = pl.rows.filter(x => !x.dim).sort((a, b) => b.ty - a.ty)[0]; return { x: pl.sx(r.tx), y: pl.sy(r.ty) }; });
    await page.mouse.click(box.x + upper.x, box.y + upper.y);
    await page.waitForSelector('#mat:not([hidden])');
    assert.match(await page.locator('#mat h3').innerText(), /T6/);
    assert.match(await page.locator('#mat .vals').innerText(), /≥ 240 MPa/);
    await page.locator('#mat button', { hasText: 'Sources' }).click();
    await page.waitForFunction(() => /Grade-level/.test(document.getElementById('card-props').innerText));
    assert.match(await page.locator('#card-name').innerText(), /T6/);
    assert.match(await page.locator('#card-props').innerText(), /≥ 240/);
    assert.match(await page.locator('#card-props').innerText(), /Grade-level value/);
    for (const details of await page.locator('#card-props details').all()) await details.locator('summary').click();
    assert.match(await page.locator('#card-props').innerText(), /Hydro|HYDRO/);
    assert.match(await page.locator('#card-props').innerText(), /Page 2/);
    assert.match(await page.locator('#card-index').innerText(), /\(2.40e\+8\).*\(2.71e\+3\)/);
    const datasheet = await page.locator('#card-datasheet').getAttribute('href');
    assert.equal(new URL(datasheet).searchParams.get('material'), 'al-6061');
    assert.equal(new URL(datasheet).searchParams.get('state'), 'al-6061-t6');
    // Citations stay selectable, unlike the chart.
    const cite = await page.locator('#card-props .source-detail').last().boundingBox();
    await page.mouse.move(cite.x + 2, cite.y + 5); await page.mouse.down(); await page.mouse.move(cite.x + 90, cite.y + 5, { steps: 4 }); await page.mouse.up();
    assert.ok((await nativeSelection()).text > 0, 'Citations can be copied');
    await page.evaluate(() => getSelection().removeAllRanges());
    await page.screenshot({ path: `${outDir}/ashby-${browserName}-sourced.png` });

    download = page.waitForEvent('download');
    await page.locator('#export-csv').click();
    const csv = await fs.readFile(await (await download).path(), 'utf8');
    assert.match(csv, /Aluminium 6061|al-6061/);
    assert.match(csv, /lower_bound/);
    assert.match(csv, /240000000/);
    assert.match(csv, /Hydro|HYDRO/);
    assert.match(csv, new RegExp(baseline.source_build_id));
    assert.ok(!csv.includes('.pdf'));
    link = new URL(await page.evaluate(() => MaterialsExplorer.getShareUrl()));
    assert.equal(link.searchParams.get('material-search'), '6061');
    assert.ok(link.searchParams.get('point').startsWith('obs-'), 'A link names exact observations');
    await page.goto(link.href); await ready();
    await page.waitForFunction(() => /T6/.test(document.getElementById('card-name').innerText));
    assert.equal((await rows()).length, 2);

    await select('basis-filter', 'measured');
    assert.ok(await page.locator('#empty-state').isVisible());
    assert.equal(await page.locator('#detail-card').isVisible(), false, 'The card closes when its point leaves');
    await select('basis-filter', 'all');
    await search('T6');
    const t6 = new Set((await rows()).map(r => r.material_id)).size;
    assert.ok(t6 > 0, 'State names are searchable');
    await search('');

    // Temperature filter: elevated values are excluded by default and available on request.
    await view('Thermal conductivity');
    const ambient = (await rows()).length;
    await select('temperature-filter', 'all');
    assert.ok((await rows()).length > ambient);
    await select('temperature-filter', 'ambient');

    /* ---------- ranking and index lines ---------- */
    await view('Stiffness');
    await page.locator('#tab-rank').click();
    await page.locator('#perf-index').selectOption('stiff_light_beam');
    await page.waitForTimeout(60);
    assert.ok(await page.locator('#ranking-section').isVisible());
    await page.locator('.index-explanation > summary').click();
    assert.match(await page.locator('#index-derivation').innerText(), /beam/i);
    assert.match(await page.locator('#index-variables').innerText(), /E: Young's modulus/);
    assert.match(await page.locator('#index-source').innerText(), /Ashby/);
    await page.locator('.index-explanation > summary').click();
    const lines = await page.evaluate(() => MaterialsExplorer.getLines());
    assert.ok(lines.length > 0);
    assert.ok(lines.every(l => l.slope === 2), 'A beam line has slope 2 on these axes');
    // Index lines do not stretch the view.
    const before = await page.evaluate(() => ({ ...MaterialsExplorer.getPlot().view }));
    assert.ok(before.y1 < 3.5, 'The modulus axis is not stretched to tens of TPa');
    await page.locator('#tab-show').click();
    await page.locator('#setting-isolines').uncheck();
    await page.locator('#setting-isolines').check();
    assert.deepEqual(await page.evaluate(() => ({ ...MaterialsExplorer.getPlot().view })), before);
    // Swapping axes flips the line and keeps its index.
    await page.keyboard.press('Escape');
    await page.evaluate(() => document.activeElement.blur());
    await page.keyboard.press('x');
    await page.waitForTimeout(300);
    assert.match(await page.locator('#x-btn').innerText(), /Young/);
    assert.equal(await page.locator('#perf-index').inputValue(), 'stiff_light_beam');
    assert.ok((await page.evaluate(() => MaterialsExplorer.getLines())).every(l => Math.abs(l.slope - .5) < 1e-9));
    await page.keyboard.press('x');
    await page.waitForTimeout(300);
    await page.locator('#tab-rank').click();
    await page.locator('#perf-index').selectOption('');
    await page.waitForTimeout(40);

    /* ---------- tag one material, and drag a label box without selecting the page ---------- */
    await page.locator('#tab-show').click();
    let plotBox = await chartBox();
    const wood = await screen("r => r.m.family === 'wood'");
    await page.mouse.click(plotBox.x + wood.x, plotBox.y + wood.y);
    await page.waitForSelector('#mat:not([hidden])');
    assert.ok(!(await page.locator('#mat').innerText()).includes('null'), 'No stray null in the card');
    await page.keyboard.type('Shortlist');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(80);
    const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('ashby-chart-tags')));
    assert.deepEqual(stored.Shortlist.ids, [wood.id], 'Exactly one material is tagged');
    assert.match(await page.locator('#mat .chips').innerText(), /Shortlist/);
    await page.locator('#mat button', { hasText: 'Label on chart' }).click();
    await page.waitForSelector('.label-box');
    await page.waitForTimeout(80);
    assert.equal(await page.locator('#mat').isHidden(), true, 'Adding a label closes the card');
    await noSelection('after adding a label');
    const l0 = await page.locator('.label-box').boundingBox();
    await page.mouse.move(l0.x + 30, l0.y + 12); await page.mouse.down();
    await page.mouse.move(l0.x - 170, l0.y + 180, { steps: 8 });
    await page.waitForTimeout(60);
    const l1 = await page.locator('.label-box').boundingBox();
    assert.ok(Math.abs(l1.x - (l0.x - 200)) < 4 && Math.abs(l1.y - (l0.y + 168)) < 4, 'The box follows the pointer');
    await noSelection('during a label drag');
    await page.mouse.up(); await page.waitForTimeout(60);
    await noSelection('after a label drag');
    assert.equal(await page.locator('#mat').isHidden(), true, 'A drag does not open the card');
    await page.mouse.move(plotBox.x + 300, plotBox.y + 200); await page.mouse.down();
    await page.mouse.move(plotBox.x + 700, plotBox.y + 500, { steps: 6 });
    await noSelection('during a pan');
    await page.mouse.up(); await page.waitForTimeout(60);
    await page.mouse.dblclick(plotBox.x + 300, plotBox.y + 200); await page.waitForTimeout(320);
    await noSelection('after a double-click');

    // The label follows its point on zoom.
    const at = () => page.evaluate(id => { const pl = MaterialsExplorer.getPlot(), r = pl.rows.find(x => x.m.id === id); return [pl.sx(r.tx), pl.sy(r.ty)]; }, wood.id);
    const a0 = await at(), l2 = await page.locator('.label-box').boundingBox();
    await page.mouse.move(plotBox.x + 500, plotBox.y + 400);
    await page.mouse.wheel(0, -120);
    await page.waitForTimeout(120);
    const a1 = await at(), l3 = await page.locator('.label-box').boundingBox();
    assert.ok(Math.abs((l3.x - l2.x) - (a1[0] - a0[0])) < 2, 'A label stays attached when zooming');
    await page.mouse.dblclick(plotBox.x + 90, plotBox.y + 20); await page.waitForTimeout(320);

    // Labels and tags survive a reload, and a link carries labels.
    link = new URL(await page.evaluate(() => MaterialsExplorer.getShareUrl()));
    assert.ok(link.searchParams.get('labels').startsWith(wood.id + '~'), 'A link carries label boxes');
    assert.ok(!link.href.includes('Shortlist'), 'A link does not carry tags');
    await page.reload(); await ready(); await page.waitForTimeout(120);
    assert.equal(await page.locator('.label-box').count(), 1);
    assert.equal(await page.locator('.tag-row').count(), 1);

    // The image export holds the chart and its label, with no page chrome.
    download = page.waitForEvent('download');
    await page.locator('#export-image').click();
    const png = await fs.readFile(await (await download).path());
    assert.deepEqual([...png.subarray(1, 4)].map(c => String.fromCharCode(c)).join(''), 'PNG');
    assert.ok(png.length > 20000, 'The image has content');

    /* ---------- box and lasso ---------- */
    plotBox = await chartBox();
    await page.keyboard.press('b');
    const s = [plotBox.x + 420, plotBox.y + 160], e = [plotBox.x + 660, plotBox.y + 380];
    await page.mouse.move(...s); await page.mouse.down(); await page.mouse.move(...e, { steps: 5 }); await page.mouse.up();
    await page.waitForSelector('#actions:not([hidden])');
    await page.waitForTimeout(80);
    const c0 = await page.locator('#sel-count').innerText();
    await page.evaluate(() => document.activeElement.blur());
    const mid = [(s[0] + e[0]) / 2, (s[1] + e[1]) / 2];
    await page.mouse.move(...mid); await page.mouse.down(); await page.mouse.move(mid[0] + 260, mid[1] - 40, { steps: 8 }); await page.mouse.up();
    await page.waitForTimeout(80);
    const c1 = await page.locator('#sel-count').innerText();
    assert.notEqual(c0, c1, 'Moving the box changes the selection');
    await noSelection('moving the selection box');
    await page.mouse.move(e[0] + 260, e[1] - 40); await page.mouse.down(); await page.mouse.move(e[0] + 330, e[1] + 30, { steps: 4 }); await page.mouse.up();
    await page.waitForTimeout(80);
    const c2 = await page.locator('#sel-count').innerText();
    assert.notEqual(c1, c2, 'A corner resizes the box');
    await page.locator('#sel-filter').click();
    await page.waitForSelector('#stack:not([hidden])');
    assert.equal(await page.locator('.stage').count(), 1);
    assert.equal(`${(await rows()).length} selected`, c2, 'The region stage matches the box');
    await page.locator('.stage button[aria-label="Remove stage"]').click();
    await page.keyboard.press('v');
    await page.evaluate(() => document.activeElement.blur());
    await page.keyboard.press('l');
    plotBox = await chartBox();
    await page.mouse.move(plotBox.x + 300, plotBox.y + 200); await page.mouse.down();
    for (const [dx, dy] of [[300, 0], [300, 300], [0, 300], [0, 0]]) await page.mouse.move(plotBox.x + 300 + dx, plotBox.y + 200 + dy, { steps: 4 });
    await page.mouse.up(); await page.waitForTimeout(80);
    await page.evaluate(() => document.activeElement.blur());
    assert.equal(await page.locator('#sel-filter').isHidden(), true, 'A lasso has no region stage');
    const lassoRows = parseInt(await page.locator('#sel-count').innerText(), 10);
    assert.ok(lassoRows > 0);
    await page.locator('#sel-isolate').click(); await page.waitForTimeout(300);
    assert.ok((await rows()).length >= 1);
    assert.ok(await page.locator('#scope').isVisible());
    await page.locator('#scope button').click(); await page.waitForTimeout(300);
    assert.equal((await rows()).length, 1185);
    // Shortcuts still work after a card closes, which Safari can block by keeping focus on a hidden field.
    await page.keyboard.press('v');
    plotBox = await chartBox();
    const point = await screen("r => r.m.family === 'polymer'");
    await page.mouse.click(plotBox.x + point.x, plotBox.y + point.y);
    await page.waitForSelector('#mat:not([hidden])');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(40);
    await page.keyboard.press('b');
    assert.equal(await page.evaluate(() => MaterialsExplorer.getPlot().mode), 'box', 'Shortcuts work after closing a card');
    await page.keyboard.press('v');

    /* ---------- selection stack ---------- */
    await page.fill('#query', 'E > 200000 MPa'); await page.keyboard.press('Enter'); await page.waitForTimeout(60);
    assert.equal(JSON.parse(new URL(await page.evaluate(() => MaterialsExplorer.getShareUrl())).searchParams.get('stages'))[0].min, 200, 'MPa converts to GPa');
    await page.locator('.stage button[aria-label="Remove stage"]').click();
    await page.fill('#query', 'rho > 5 GPa'); await page.keyboard.press('Enter'); await page.waitForTimeout(40);
    assert.match(await page.locator('#query-msg').innerText(), /kg\/m³/, 'A wrong unit is refused');
    assert.equal(await page.locator('.stage').count(), 0);
    await page.fill('#query', 'UTS > 200'); await page.keyboard.press('Enter');
    await page.fill('#query', 'family metal, composite'); await page.keyboard.press('Enter');
    await page.waitForTimeout(80);
    assert.equal(await page.locator('.stage').count(), 2);
    const funnels = await page.locator('.funnel').allInnerTexts();
    assert.match(funnels[0], /1,453 →/);
    const hist = await page.locator('.hist').first().boundingBox();
    const r0 = await page.locator('#stages .end span').last().innerText();
    await page.mouse.move(hist.x + 5, hist.y + 20); await page.mouse.down(); await page.mouse.move(hist.x + hist.width * .75, hist.y + 20, { steps: 5 }); await page.mouse.up();
    await page.waitForTimeout(80);
    assert.notEqual(await page.locator('#stages .end span').last().innerText(), r0, 'A histogram drag changes the result');
    await page.locator('.stage button[title="Turn off"]').first().click(); await page.waitForTimeout(60);
    await page.locator('.stage button[aria-label="Move stage up"]').first().click(); await page.waitForTimeout(60);
    assert.ok((await page.locator('.stage-title').first().innerText()).startsWith('Family'));
    // Limits read the same row: 6061 passes a yield limit only through its T6 values.
    while (await page.locator('.stage').count()) await page.locator('.stage button[aria-label="Remove stage"]').first().click();
    await page.fill('#query', 'Sy > 200 MPa'); await page.keyboard.press('Enter');
    await search('6061'); await view('Yield strength');
    assert.deepEqual((await rows()).map(r => r.state_id), ['al-6061-t6'], 'A limit does not mix tempers');
    await search('');
    await page.locator('.stage button[aria-label="Remove stage"]').first().click();
    await view('Stiffness');

    // Results, sort, Compare, tag results.
    await page.keyboard.press('r');
    await page.waitForSelector('#results-box:not([hidden])');
    assert.equal(await page.locator('table.results tbody tr').count(), 150);
    assert.match(await page.locator('#result-count').innerText(), /first 150 listed/);
    await page.locator('table.results thead th button').nth(1).click(); await page.waitForTimeout(40);
    await page.locator('table.results td.pin button').first().click();
    await page.locator('table.results td.pin button').nth(1).click();
    await page.locator('#tab-compare').click();
    assert.equal(await page.locator('table.compare thead th').count(), 3);
    await page.locator('#tab-results').click();

    // A selection line.
    await page.locator('#add-line').click(); await page.waitForTimeout(80);
    const n0 = (await rows()).length;
    const cb = await chartBox();
    const lineAt = await page.evaluate(() => { const pl = MaterialsExplorer.getPlot(), st = JSON.parse(new URL(MaterialsExplorer.getShareUrl()).searchParams.get('stages'))[0], X = pl.plotBox.l + pl.plotBox.w * .5; return { X, Y: pl.sy(st.slope * pl.ix(X) + st.c) }; });
    await page.mouse.move(cb.x + lineAt.X, cb.y + lineAt.Y); await page.mouse.down(); await page.mouse.move(cb.x + lineAt.X, cb.y + lineAt.Y - 60, { steps: 5 }); await page.mouse.up();
    await page.waitForTimeout(100);
    assert.ok((await rows()).length < n0, 'Dragging the line up narrows the result');
    await page.locator('.stage button[aria-label="Remove stage"]').first().click();
    // + Region: Esc cancels, then a drag adds a stage.
    await page.locator('#add-region').click();
    assert.ok(await page.locator('#arm-note').isVisible());
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#arm-note').isHidden(), true);
    await page.locator('#add-region').click();
    const rb = await chartBox();
    await page.mouse.move(rb.x + 200, rb.y + 100); await page.mouse.down(); await page.mouse.move(rb.x + 520, rb.y + 300, { steps: 4 }); await page.mouse.up();
    await page.waitForTimeout(100);
    assert.equal(await page.locator('.stage').count(), 1);
    assert.equal(await page.locator('#actions').isHidden(), true);
    await page.locator('.stage button[aria-label="Remove stage"]').first().click();

    /* ---------- design brief ---------- */
    await page.locator('#brief-box summary').click();
    await page.locator('#b-use').click(); await page.waitForTimeout(350);
    assert.match(await page.locator('#y-btn').innerText(), /Young/);
    assert.equal(await page.locator('#perf-index').inputValue(), 'stiff_light_beam');
    assert.match(await page.locator('table.results thead').innerText(), /Index, % of best/);
    assert.match(await page.locator('table.results tbody tr').first().innerText(), /100%/);
    await page.screenshot({ path: `${outDir}/ashby-${browserName}-brief.png` });
    // The strong brief uses yield strength, as the published index does.
    await page.selectOption('#b-driver', 'strong'); await page.waitForTimeout(350);
    assert.match(await page.locator('#y-btn').innerText(), /yield/i);
    assert.equal(await page.locator('#perf-index').inputValue(), 'strong_light_beam');
    await page.selectOption('#b-driver', 'stiff'); await page.selectOption('#b-part', 'plate or panel'); await page.waitForTimeout(350);
    assert.equal(await page.locator('#perf-index').inputValue(), 'stiff_light_plate');
    const url = await page.evaluate(() => MaterialsExplorer.getShareUrl());
    await page.goto(url); await ready(); await page.waitForTimeout(200);
    assert.ok(await page.locator('#stack').isVisible());
    assert.ok(await page.locator('#results-box').isVisible());
    assert.ok(await page.locator('#b-clear').isVisible());
    await page.locator('#b-clear').click(); await page.waitForTimeout(80);
    assert.equal(await page.locator('.stage').count(), 0);
    await page.keyboard.press('s'); await page.keyboard.press('r');

    /* ---------- axis menu ---------- */
    await page.locator('#y-btn').click();
    assert.ok(await page.locator('#pop .prop-row').first().isVisible());
    await page.locator('#pop input[aria-label="Formula"]').fill('E^0.5/rho');
    await page.keyboard.press('Enter'); await page.waitForTimeout(350);
    assert.match(await page.locator('#y-btn').innerText(), /E\^0\.5\/ρ/);
    assert.match(await page.locator('#y-btn').innerText(), /display units/);
    await page.locator('#y-btn').click();
    await page.locator('#pop input[aria-label="Formula"]').fill('E/nope');
    assert.match(await page.locator('#pop .formula-msg').innerText(), /Unknown property/);
    await page.keyboard.press('Enter');
    assert.ok(await page.locator('#pop').isVisible(), 'A bad formula does not plot');
    await page.keyboard.press('Escape');
    download = page.waitForEvent('download');
    await page.locator('#export-csv').click();
    const formulaCsv = await fs.readFile(await (await download).path(), 'utf8');
    assert.match(formulaCsv.split('\r\n')[0], /Chart Y: E\^0\.5\/ρ/);
    assert.match(formulaCsv.split('\r\n')[0], /rho value \(SI\)/);
    await page.locator('#x-btn').click();
    await page.locator('#pop .scale button', { hasText: 'Linear' }).click(); await page.waitForTimeout(300);
    assert.equal(await page.evaluate(() => MaterialsExplorer.getPlot().xAxis.log), false);
    await page.locator('#x-btn').click();
    await page.locator('#pop .scale button', { hasText: 'Log' }).click(); await page.waitForTimeout(300);
    await view('Stiffness');

    /* ---------- parallel ---------- */
    await page.locator('#view-parallel').click();
    await page.waitForSelector('#parallel:not([hidden])'); await page.waitForTimeout(120);
    assert.equal(await page.locator('[data-mode="box"]').isVisible(), false);
    assert.equal(await page.locator('#envelope-mode').isVisible(), false);
    assert.ok(await page.locator('#color').isVisible());
    assert.match(await page.locator('.p-coverage').innerText(), /have all 3 values/);
    const pc = await page.locator('#p-stage canvas').boundingBox();
    const bx = pc.x + 44;
    await page.mouse.move(bx, pc.y + 150); await page.mouse.down(); await page.mouse.move(bx, pc.y + 420, { steps: 6 });
    await noSelection('during a parallel brush');
    await page.mouse.up(); await page.waitForTimeout(100);
    const brushStages = () => page.evaluate(() => JSON.parse(new URL(MaterialsExplorer.getShareUrl()).searchParams.get('stages') || '[]'));
    let st = await brushStages();
    assert.equal(st.length, 1); assert.equal(st[0].expr, 'rho'); assert.ok(st[0].min < st[0].max);
    await page.mouse.move(bx, pc.y + 200); await page.mouse.down(); await page.mouse.move(bx, pc.y + 330, { steps: 4 }); await page.mouse.up(); await page.waitForTimeout(100);
    assert.equal((await brushStages()).length, 1, 'A second drag edits the same stage');
    assert.equal(await page.locator('#stack-count').innerText(), '1');
    await page.keyboard.press('a'); await page.waitForTimeout(120);
    const brushed = (await rows()).length;
    assert.ok(brushed > 0 && brushed < 1185, 'The chart obeys a parallel filter');
    await page.keyboard.press('a'); await page.waitForTimeout(120);
    await page.mouse.click(bx, pc.y + 300); await page.waitForTimeout(100);
    assert.equal((await brushStages()).length, 0, 'Clicking a filtered axis clears it');
    await page.locator('#p-add').click(); await page.waitForTimeout(80);
    assert.equal(await page.locator('.axis-chip').count(), 4);
    await page.locator('.axis-chip button[aria-label$=" left"]').first().click(); await page.waitForTimeout(60);
    await page.locator('.axis-chip button[aria-label^="Remove"]').last().click(); await page.waitForTimeout(60);
    assert.equal(await page.locator('.axis-chip').count(), 3);
    await page.locator('.axis-chip select').nth(0).selectOption('E');
    await page.locator('.axis-chip select').nth(1).selectOption('rho');
    await page.locator('.axis-chip select').nth(2).selectOption('UTS');
    await page.waitForTimeout(80);
    const pc2 = await page.locator('#p-stage canvas').boundingBox();
    let found = 0;
    for (let y = 80; y < pc2.height - 60 && !found; y += 12) {
      await page.mouse.move(pc2.x + pc2.width * .3, pc2.y + y);
      await page.waitForTimeout(15);
      if (await page.locator('#p-stage .ac-tip').isVisible()) found = y;
    }
    assert.ok(found, 'Hover finds a line');
    assert.match(await page.locator('#p-stage .ac-tip').innerText(), /MPa/);
    await page.mouse.click(pc2.x + pc2.width * .3, pc2.y + found);
    await page.waitForSelector('#mat:not([hidden])');
    await page.keyboard.type('From parallel'); await page.keyboard.press('Enter'); await page.waitForTimeout(80);
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('ashby-chart-tags'))['From parallel'].ids.length), 1);
    await page.screenshot({ path: `${outDir}/ashby-${browserName}-parallel.png` });
    await page.keyboard.press('Escape');
    const parallelLink = await page.evaluate(() => MaterialsExplorer.getShareUrl());
    await page.goto(parallelLink); await ready(); await page.waitForTimeout(120);
    assert.ok(await page.locator('#parallel').isVisible());
    assert.equal(await page.locator('.axis-chip').count(), 3);
    await view('Stiffness');
    assert.equal(await page.locator('#parallel').isHidden(), true);

    /* ---------- families, settings, keyboard, dark and phone ---------- */
    for (const button of await page.locator('.family-pill').all()) await button.click();
    await page.waitForTimeout(60);
    assert.ok(await page.locator('#empty-state').isVisible());
    await page.locator('[data-family="metal"]').click(); await page.waitForTimeout(60);
    assert.ok((await rows()).every(r => r.family === 'metal'));
    await page.locator('#all-families').click(); await page.waitForTimeout(60);
    assert.equal((await rows()).length, 1185);
    await page.locator('#tab-show').click();
    await page.locator('#setting-labels').check(); await page.waitForTimeout(40);
    assert.equal(await page.evaluate(() => MaterialsExplorer.getPlot().opts.showPointLabels), true);
    await page.locator('#setting-labels').uncheck();

    await page.locator('#tab-show').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#tab-browse').getAttribute('aria-selected'), 'true');
    assert.equal(await page.locator('#tab-browse').evaluate(el => el === document.activeElement), true);
    await page.keyboard.press('Home');
    assert.equal(await page.locator('#tab-show').getAttribute('aria-selected'), 'true');

    await page.locator('#settings-button').click();
    await page.locator('#theme-control [data-theme="dark"]').click();
    await page.locator('#setting-density').selectOption('compact');
    await page.locator('#setting-precision').selectOption('4');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#settings-button').evaluate(el => el === document.activeElement), true);
    await page.reload(); await ready();
    assert.equal(await page.locator('body').getAttribute('data-theme'), 'dark');
    assert.equal(await page.locator('body').getAttribute('data-density'), 'compact');
    await page.waitForTimeout(150);
    await page.screenshot({ path: `${outDir}/ashby-${browserName}-dark.png` });
    await page.evaluate(() => localStorage.clear());

    // The Materials link uses the format that tool reads, and the datasheet opens.
    const sourcePage = await context.newPage();
    await sourcePage.goto(datasheet);
    await sourcePage.locator('#view').getByText('Aluminium 6061', { exact: false }).first().waitFor();
    assert.match(await sourcePage.locator('#view').innerText(), /T6/);
    await sourcePage.close();

    // Phone layout: no sideways scroll, and the page can still be scrolled past the plot.
    if (browserName !== 'firefox') {
      const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2, serviceWorkers: 'block' });
      await phone.route('**/www.googletagmanager.com/**', route => route.fulfill({ body: '', contentType: 'application/javascript' }));
      const q = await phone.newPage();
      q.on('pageerror', error => errors.push('phone: ' + error.message));
      await q.goto(base); await q.locator('#explorer-main[data-state="ready"]').waitFor(); await q.waitForTimeout(250);
      const noOverflow = async where => assert.equal(await q.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), 0, where);
      await noOverflow('phone chart');
      assert.equal(await q.locator('#side').isHidden(), true);
      const margin = await q.evaluate(() => innerWidth - document.getElementById('wrap').getBoundingClientRect().right);
      assert.ok(margin >= 20, 'A margin stays free for scrolling');
      assert.ok(await q.evaluate(() => document.documentElement.scrollHeight > innerHeight));
      await q.screenshot({ path: `${outDir}/ashby-${browserName}-phone.png` });
      const qb = await q.locator('#ashby-chart canvas').boundingBox();
      const qp = await q.evaluate(() => { const pl = MaterialsExplorer.getPlot(), b = pl.plotBox, r = pl.rows.filter(x => pl.sx(x.tx) > b.l + 20 && pl.sx(x.tx) < b.r - 20 && pl.sy(x.ty) > b.t + 20 && pl.sy(x.ty) < b.b - 20)[0]; return { x: pl.sx(r.tx), y: pl.sy(r.ty) }; });
      await q.touchscreen.tap(qb.x + qp.x, qb.y + qp.y);
      await q.waitForSelector('#mat:not([hidden])');
      const matBox = await q.locator('#mat').boundingBox();
      assert.ok(matBox.x >= 0 && matBox.x + matBox.width <= 390, 'The card fits');
      await q.locator('#mat button[aria-label="Close"]').click();
      await q.locator('#stack-btn').click(); await q.waitForTimeout(80);
      await noOverflow('phone stack');
      await q.locator('#stack-close').click();
      await q.locator('#view-parallel').click(); await q.waitForTimeout(150);
      await noOverflow('phone parallel');
      await q.screenshot({ path: `${outDir}/ashby-${browserName}-phone-parallel.png` });
      await phone.close();
    }

    // The old address still reaches the chart, when a redirect is available.
    if (!new URL(base).hostname.startsWith('127.')) {
      const redirect = new URL('../materials-explorer/', base);
      redirect.searchParams.set('material-search', '6061');
      await page.goto(redirect.href); await ready();
      assert.equal(new URL(page.url()).pathname, new URL(base).pathname);
    }

    // Mismatched builds must fail visibly; retry must recover after fresh data arrives.
    const manifestPattern = '**/tools/materials/release-manifest.json';
    await page.route(manifestPattern, route => route.fulfill({ json: { build_id: 'stale' } }));
    await page.reload();
    await page.locator('#explorer-main[data-state="error"]').waitFor();
    assert.match(await page.locator('#loading-message').innerText(), /versions differ/);
    await page.unroute(manifestPattern);
    await page.locator('#retry-load').click();
    await ready();
    assert.equal(await page.locator('#loading-overlay').isVisible(), false);

    // A details file from another build is refused too.
    const detailsPattern = '**/data/materials/selection-details.json';
    await page.route(detailsPattern, route => route.fulfill({ json: { schema_version: 2, source_build_id: 'stale' } }));
    await page.reload(); await ready();
    await page.locator('#tab-browse').click();
    await page.locator('#material-list button').first().click();
    await page.waitForFunction(() => /versions differ/.test(document.getElementById('card-props').innerText));
    await page.unroute(detailsPattern);

    assert.deepEqual(errors, []);

    // The previous version stays inspectable for comparison.
    if (new URL(base).hostname.startsWith('127.') && browserName === 'chromium') {
      const internal = new URL('../../_internal/prototypes/2026-10-31_ashby-chart-plotly/', base).href;
      for (const file of ['', 'prototypes/before.html']) {
        const old = await context.newPage();
        const oldErrors = [];
        old.on('pageerror', error => oldErrors.push(error.message));
        await old.goto(internal + file);
        await old.locator('#explorer-main[data-state="ready"]').waitFor();
        assert.deepEqual(oldErrors, [], file);
        await old.close();
      }
      for (const prototype of ['a-left-rail', 'b-top-controls', 'c-workspace']) {
        const legacy = await context.newPage();
        const legacyErrors = [];
        legacy.on('pageerror', error => legacyErrors.push(error.message));
        await legacy.goto(new URL(`../../_internal/prototypes/2026-04-11_materials-explorer-ui/${prototype}/`, base).href);
        await legacy.waitForFunction(() => document.getElementById('ashby-chart')?.data?.some(trace => trace.x.length > 0));
        assert.deepEqual(legacyErrors, [], prototype);
        await legacy.close();
      }
    }

    // An installed service worker must refresh an old, cached Materials release.
    if (browserName === 'chromium') {
      const offlineContext = await browser.newContext({ serviceWorkers: 'allow' });
      const offlinePage = await offlineContext.newPage();
      await offlinePage.goto(base);
      await offlinePage.locator('#explorer-main[data-state="ready"]').waitFor();
      await offlinePage.evaluate(async () => {
        await navigator.serviceWorker.register(new URL('../../service-worker.js', location.href).href);
        await navigator.serviceWorker.ready;
      });
      await offlinePage.waitForFunction(() => navigator.serviceWorker.controller);
      const freshBuild = await offlinePage.evaluate(async () => {
        const cacheName = (await caches.keys()).find(name => name.startsWith('tt-cache-'));
        const cache = await caches.open(cacheName);
        await cache.put(new URL('../materials/release-manifest.json', location.href), new Response(JSON.stringify({ build_id: 'old-cached-build' }), { headers: { 'Content-Type': 'application/json' } }));
        await cache.put(new URL('../../data/materials/selection-core.json', location.href), new Response(JSON.stringify({ schema_version: 2, source_build_id: 'old-cached-build' }), { headers: { 'Content-Type': 'application/json' } }));
        return MaterialsExplorer.getData().source_build_id;
      });
      await offlinePage.reload();
      await offlinePage.locator('#explorer-main[data-state="ready"]').waitFor();
      assert.equal(await offlinePage.evaluate(() => MaterialsExplorer.getData().source_build_id), freshBuild);
      await offlineContext.close();
    }

    console.log(JSON.stringify({ passed: true, browser: browserName, grades: baseline.counts.materials }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
