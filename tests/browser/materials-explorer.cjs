/* Serve the repo root, then pass its Ashby Chart URL to this script. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/opt/homebrew/lib/node_modules/@playwright/test');
const base = process.argv.find(arg => /^https?:/.test(arg)) || 'http://127.0.0.1:8158/tools/materials-explorer/';

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'light', serviceWorkers: 'block' });
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await context.route('**/www.googletagmanager.com/**', route => route.fulfill({ body: '', contentType: 'application/javascript' }));
    await context.route('**/google-analytics.com/**', route => route.fulfill({ body: '' }));
    const page = await context.newPage();
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    page.on('request', request => requests.push(request.url()));
    page.setDefaultTimeout(20000);
    const ready = () => page.locator('#explorer-main[data-state="ready"]').waitFor();
    const select = async (id, value) => {
      const control = page.locator('#' + id);
      if (!(await control.isVisible())) {
        if (id === 'perf-index') await page.locator('#tab-rank').click();
        else await page.locator('#filter-menu > summary').click();
      }
      await control.selectOption(value); await ready();
      if (await page.locator('#filter-menu').getAttribute('open') !== null) await page.locator('#filter-menu > summary').click();
    };
    const groupBy = async value => { await page.locator(`[data-grouping="${value}"]`).click(); await ready(); };
    const regions = () => page.locator('#ashby-chart').evaluate(el => el.data.filter(trace => trace.meta?.region).map(trace => ({family:trace.meta.family, name:trace.name})));
    const near = (a, b) => assert.ok(Math.abs(a - b) <= Math.max(1e-10, Math.abs(b) * 1e-10), `${a} ≈ ${b}`);
    await page.goto(base);
    await ready();
    assert.equal(await page.locator('#loading-overlay').isVisible(), false);
    const baseline = await page.evaluate(() => ({ counts: MaterialsExplorer.getData().counts, rows: MaterialsExplorer.getRows().length, indices: [...document.querySelector('#perf-index').options].map(o => o.value), properties: [...document.querySelector('#x-prop').options].map(o => o.value) }));
    assert.equal(baseline.counts.materials, 288);
    assert.ok(baseline.rows > 150, JSON.stringify(baseline));
    assert.ok(!baseline.properties.includes('price_per_kg'));
    assert.ok(!baseline.properties.includes('max_service_temperature'));
    assert.match(await page.locator('#data-status').innerText(), /288 materials/);
    assert.equal(await page.locator('#perf-index').inputValue(), '');
    assert.equal(await page.locator('h1').innerText(), 'Ashby Chart');
    assert.match(await page.locator('meta[name="description"]').getAttribute('content'), /Ashby charts/);
    assert.ok(await page.locator('.chart-panel').evaluate(el => el.getBoundingClientRect().bottom <= innerHeight));
    assert.equal(await page.locator('#tab-inspect').getAttribute('tabindex'), '-1');
    assert.equal(await page.locator('[data-grouping="family"]').getAttribute('aria-pressed'), 'true');
    const familyRegions = await regions();
    assert.equal(familyRegions.filter(r=>r.family==='polymer').length,1);
    assert.equal(new Set(familyRegions.map(r=>r.family)).size,familyRegions.length,'Each family has only one outline');
    assert.ok(familyRegions.some(r=>r.name==='Polymers (plotted grades)'));
    await page.screenshot({ path: '/private/tmp/ashby-materials-desktop.png', fullPage: true });
    if (process.argv.includes('--preview')) { console.log(JSON.stringify({baseline, errors})); return; }

    // Grouping and outline shape are independent, with unchanged observations.
    for (const mode of ['ellipses', 'hulls']) {
      await select('envelope-mode', mode);
      for (const grouping of ['subgroup','points','family']) {
        await groupBy(grouping);
        const outlines = await regions();
        if (grouping === 'points') {
          assert.equal(outlines.length,0);
          assert.ok(await page.locator('#setting-points').isChecked());
          assert.ok(await page.locator('#envelope-mode').isDisabled());
          assert.equal(await page.locator('#ashby-chart').evaluate(el=>el.data.filter(t=>t.customdata).reduce((sum,t)=>sum+t.customdata.length,0)),baseline.rows);
        } else {
          assert.equal(outlines.filter(r=>r.family==='polymer').length,grouping==='family'?1:12);
          assert.ok(await page.locator('#envelope-mode').isEnabled());
        }
        assert.equal((await page.evaluate(() => MaterialsExplorer.getRows())).length, baseline.rows);
        assert.equal(await page.locator('#envelope-mode').inputValue(),mode);
        const link = new URL(await page.evaluate(() => MaterialsExplorer.getShareUrl()));
        assert.equal(link.searchParams.get('grouping'),grouping);
        assert.equal(link.searchParams.get('envelope-mode'),mode);
      }
    }
    await groupBy('subgroup');
    await page.goto(await page.evaluate(() => MaterialsExplorer.getShareUrl())); await ready();
    assert.equal(await page.locator('[data-grouping="subgroup"]').getAttribute('aria-pressed'),'true');
    assert.equal((await regions()).filter(r=>r.family==='polymer').length,12);
    for (const oldQuery of ['envelope-mode=points&setting-points=0','setting-blobs=0']) {
      await page.goto(base+'?'+oldQuery); await ready();
      assert.equal(await page.locator('[data-grouping="points"]').getAttribute('aria-pressed'),'true');
      assert.equal((await regions()).length,0);
      assert.ok(await page.locator('#setting-points').isChecked());
    }
    await groupBy('family');
    await page.evaluate(() => Plotly.relayout('ashby-chart', {'xaxis.range': [3.63, 3.69], 'yaxis.range': [10.99, 11.1]}));
    await page.waitForFunction(() => document.querySelector('#ashby-chart').layout.xaxis.tickvals.length >= 3);
    const zoomTicks = await page.locator('#ashby-chart').evaluate(el => ({x: el.layout.xaxis.tickvals, y: el.layout.yaxis.ticktext}));
    assert.ok(zoomTicks.x.every(v => v > 4200 && v < 5000), JSON.stringify(zoomTicks));
    assert.ok(zoomTicks.y.every(v => Number(v) < 150), 'Modulus ticks must display GPa after zoom');
    await groupBy('subgroup');
    assert.deepEqual(await page.locator('#ashby-chart').evaluate(el=>el._fullLayout.xaxis.range),[3.63,3.69],'Grouping changes preserve zoom');
    await groupBy('family');
    await page.locator('#reset-view').click(); await ready();

    await page.locator('#material-search').fill('titanium'); await ready();
    const titanium = await page.evaluate(() => MaterialsExplorer.getRows());
    assert.equal(titanium.length, 2);
    assert.ok(titanium.every(row => row.temperatures_K.includes(293.15) && row.temperatures_K.includes(295.15)));
    await page.locator('#material-list button').filter({hasText: 'Ti-6Al-4V'}).click(); await ready();
    await groupBy('subgroup');
    assert.match(await page.locator('#card-name').innerText(), /Ti-6Al-4V/);
    await groupBy('family');
    assert.match(await page.locator('#card-props').innerText(), /20.0 °C/);
    assert.match(await page.locator('#card-props').innerText(), /22.0 °C/);
    const titaniumDownload = page.waitForEvent('download');
    await page.locator('#export-csv').click();
    const titaniumCsv = await fs.readFile(await (await titaniumDownload).path(), 'utf8');
    assert.match(titaniumCsv, /20.0 °C/); assert.match(titaniumCsv, /22.0 °C/);

    // A material missing the chosen property is still discoverable with an explicit alternate chart.
    await page.locator('#tab-browse').click();
    await page.locator('#material-search').fill('wood'); await ready();
    assert.equal((await page.evaluate(() => MaterialsExplorer.getRows())).length, 0);
    assert.equal(await page.locator('#material-list button').count(), 10);
    await page.locator('#material-list button').filter({hasText: 'Red alder'}).click(); await ready();
    await page.getByRole('button', {name: 'Show bending stiffness chart', exact: true}).click(); await ready();
    assert.equal(await page.locator('#y-prop').inputValue(), 'flexural_modulus');
    assert.equal((await page.evaluate(() => MaterialsExplorer.getRows())).length, 10);
    assert.match(await page.locator('#card-props').innerText(), /12.0% moisture/);
    assert.match(await page.locator('#card-props').innerText(), /9.50 GPa/);

    await page.getByRole('button', {name: 'Tensile strength', exact: true}).click(); await ready();
    await page.locator('#material-search').fill('elastomer'); await ready();
    assert.equal((await page.evaluate(() => MaterialsExplorer.getRows())).length, 10);
    await page.locator('#material-search').fill('foam'); await ready();
    assert.equal((await page.evaluate(() => MaterialsExplorer.getRows())).length, 12);
    await page.getByRole('button', {name: 'Stiffness', exact: true}).click(); await ready();
    assert.equal((await page.evaluate(() => MaterialsExplorer.getRows())).length, 8);
    await page.locator('#material-search').fill(''); await ready();
    await select('temperature-filter', 'ambient');
    await select('perf-index', 'stiff_light_beam');
    const domains = await page.locator('#ashby-chart').evaluate(el => [el.layout.xaxis.range, el.layout.yaxis.range]);
    assert.ok(domains[1][1] < 12.5, 'Isolines must not stretch the modulus axis into tens of TPa');
    await page.locator('#filter-menu > summary').click();
    await page.locator('#setting-isolines').focus();
    await page.keyboard.press('Space');
    await ready();
    assert.deepEqual(await page.locator('#ashby-chart').evaluate(el => [el.layout.xaxis.range, el.layout.yaxis.range]), domains);
    await page.keyboard.press('Space');
    await ready();
    await page.locator('#filter-menu > summary').click();
    await page.locator('.index-explanation > summary').click();
    assert.match(await page.locator('#index-derivation').innerText(), /beam/i);
    assert.match(await page.locator('#index-variables').innerText(), /E: Young's modulus/);
    await page.locator('.index-explanation > summary').click();
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({ path: '/private/tmp/ashby-materials-ranking.png', fullPage: true });

    await select('x-prop', 'youngs_modulus');
    await select('y-prop', 'density');
    await select('perf-index', 'stiff_light_beam');
    const reversed = await page.locator('#ashby-chart').evaluate(el => ({ shapes: el.layout.shapes, x: el.layout.xaxis.title.text, y: el.layout.yaxis.title.text, rows: MaterialsExplorer.getRows().slice(0, 3) }));
    assert.match(reversed.x, /modulus/);
    assert.match(reversed.y, /Density/);
    assert.ok(reversed.shapes.length > 0);
    for (const shape of reversed.shapes) near(Math.sqrt(shape.x0) / shape.y0, Math.sqrt(shape.x1) / shape.y1);

    await page.getByRole('button', { name: 'Yield strength', exact: true }).click();
    await ready();
    await select('perf-index', 'strong_light_tie');
    await page.locator('#material-search').fill('6061');
    await ready();
    let rows = await page.evaluate(() => MaterialsExplorer.getRows());
    assert.equal(rows.length, 2);
    assert.deepEqual(rows.map(row => row.state_id).sort(), ['al-6061-t4', 'al-6061-t6']);
    assert.ok(rows.every(row => row.hasBounds));
    const plotted = await page.locator('#ashby-chart').evaluate(el => ({ data: el.data, shapes: el.layout.shapes }));
    assert.ok(plotted.data.filter(trace => trace.customdata).every(trace => trace.marker.symbol.every(symbol => symbol.endsWith('-open'))));
    assert.equal(plotted.data.filter(trace => trace.fill === 'toself').length, 0, 'Bounds do not create a family envelope');
    // With two separated points, a real click on the upper marker selects T6.
    await page.locator('#ashby-chart').scrollIntoViewIfNeeded();
    const markers = page.locator('#ashby-chart .scatterlayer .points path.point');
    const boxes = await markers.evaluateAll(elements => elements.map(el => { const b = el.getBoundingClientRect(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; }));
    const upper = boxes.sort((a, b) => a.y - b.y)[0];
    await page.mouse.click(upper.x, upper.y);
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
    await page.screenshot({ path: '/private/tmp/ashby-materials-sourced.png', fullPage: true });

    const download = page.waitForEvent('download');
    await page.locator('#export-csv').click();
    const csv = await fs.readFile(await (await download).path(), 'utf8');
    assert.match(csv, /al-6061|Aluminium 6061/);
    assert.match(csv, /lower_bound/);
    assert.match(csv, /240000000/);
    assert.match(csv, /Hydro|HYDRO/);
    assert.ok(!csv.includes('.pdf'));
    await page.locator('#copy-link').click();
    const link = await page.evaluate(() => navigator.clipboard.readText());
    assert.equal(new URL(link).searchParams.get('material-search'), '6061');
    await page.goto(link);
    await ready();
    await page.locator('#detail-card:not([hidden])').waitFor();
    assert.match(await page.locator('#card-name').innerText(), /T6/);
    assert.equal((await page.evaluate(() => MaterialsExplorer.getRows())).length, 2);

    await select('basis-filter', 'measured');
    assert.ok(await page.locator('#empty-state').isVisible());
    assert.equal(await page.locator('#export-csv').isDisabled(), true);
    assert.equal(await page.locator('#detail-card').isVisible(), false);
    await select('basis-filter', 'all');
    await page.locator('#tab-browse').click();
    await page.locator('#material-search').fill('T6'); await ready();
    const t6Grades = await page.evaluate(() => new Set(MaterialsExplorer.getRows().map(row => row.material_id)).size);
    assert.ok(t6Grades > 0);
    assert.ok(await page.locator('#material-list button').count() >= t6Grades, 'State search retains the matching grades in the browser');
    await page.locator('#material-search').fill('');
    await ready();
    await page.getByRole('button', { name: 'Thermal conductivity', exact: true }).click();
    await ready();
    const ambient = (await page.evaluate(() => MaterialsExplorer.getRows())).length;
    await select('temperature-filter', 'all');
    assert.ok((await page.evaluate(() => MaterialsExplorer.getRows())).length > ambient);
    await page.locator('#filter-menu > summary').click();
    await page.locator('#setting-labels').click();
    await ready();
    assert.ok(await page.locator('#ashby-chart').evaluate(el => el.data.some(t => t.mode === 'markers+text')));
    await page.locator('#setting-labels').click();
    await page.locator('#filter-menu > summary').click();
    await ready();
    for (const button of await page.locator('.family-pill').all()) await button.click();
    await ready();
    assert.ok(await page.locator('#empty-state').isVisible());
    assert.ok(await page.locator('#ashby-chart').evaluate(el => el.layout.shapes.every(s => [s.x0, s.x1, s.y0, s.y1].every(Number.isFinite))));
    await page.locator('[data-family="metal"]').click();
    await ready();

    await page.locator('#settings-button').click();
    await page.locator('#theme-control [data-theme="dark"]').click();
    await page.locator('#setting-density').selectOption('compact');
    await page.locator('#setting-precision').selectOption('4');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#settings-button').evaluate(el => el === document.activeElement), true);
    await page.reload();
    await ready();
    assert.equal(await page.locator('body').getAttribute('data-theme'), 'dark');
    assert.equal(await page.locator('body').getAttribute('data-density'), 'compact');
    await page.setViewportSize({ width: 390, height: 844 });
    await select('temperature-filter', 'ambient');
    const width = await page.evaluate(() => ({ viewport: innerWidth, content: document.documentElement.scrollWidth }));
    assert.ok(width.content <= width.viewport + 1, JSON.stringify(width));
    assert.equal(await page.locator('#ashby-chart').evaluate(el => el.layout.legend.orientation), 'h');
    await page.screenshot({ path: '/private/tmp/ashby-materials-dark-mobile.png', fullPage: true });
    await page.locator('#ashby-chart').screenshot({ path: '/private/tmp/ashby-materials-mobile-chart.png' });

    const sourcePage = await context.newPage();
    await sourcePage.goto(datasheet);
    await sourcePage.locator('#view').getByText('Aluminium 6061', { exact: false }).first().waitFor();
    assert.match(await sourcePage.locator('#view').innerText(), /T6/);
    await sourcePage.close();

    const redirect = new URL('../ashby-chart/', base);
    redirect.searchParams.set('material-search', '6061');
    redirect.searchParams.set('y-prop', 'tensile_yield_strength');
    await page.goto(redirect.href);
    await ready();
    assert.equal(new URL(page.url()).pathname, new URL(base).pathname);
    assert.equal(await page.locator('#material-search').inputValue(), '6061');
    assert.equal((await page.evaluate(() => MaterialsExplorer.getRows())).length, 2);

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

    assert.ok(!requests.some(url => /\/data\/materials\/materials\.json/.test(url)), 'No legacy 60-material dataset is requested');
    assert.deepEqual(errors, []);

    // Every new experiment remains independently inspectable, including the saved old interface.
    for (const [file, mode, grouping] of [['a-outlines', 'hulls', 'subgroup'], ['b-ellipses', 'ellipses', 'subgroup'], ['c-points', 'hulls', 'points'], ['before', null]]) {
      const experiment = await context.newPage();
      const experimentErrors = [];
      experiment.on('pageerror', error => experimentErrors.push(error.message));
      await experiment.goto(new URL('prototypes/' + file + '.html', base).href);
      const chartPage = mode ? experiment.frameLocator('iframe') : experiment;
      await chartPage.locator('#explorer-main[data-state="ready"]').waitFor();
      if (mode) {
        assert.equal(await chartPage.locator('#envelope-mode').inputValue(), mode);
        assert.equal(await chartPage.locator(`[data-grouping="${grouping}"]`).getAttribute('aria-pressed'), 'true');
      }
      assert.deepEqual(experimentErrors, [], file);
      await experiment.close();
    }

    // Retained prototypes still use the shared component's original API.
    if (new URL(base).hostname === '127.0.0.1') {
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
      await cache.put(new URL('../../data/materials/selection.json', location.href), new Response(JSON.stringify({ schema_version: 1, source_build_id: 'old-cached-build' }), { headers: { 'Content-Type': 'application/json' } }));
      return MaterialsExplorer.getData().source_build_id;
    });
    await offlinePage.reload();
    await offlinePage.locator('#explorer-main[data-state="ready"]').waitFor();
    assert.equal(await offlinePage.evaluate(() => MaterialsExplorer.getData().source_build_id), freshBuild);
    assert.equal(await offlinePage.evaluate(() => MaterialsExplorer.getData().counts.materials), 288);
    await offlineContext.close();

    console.log(JSON.stringify({ passed: true, grades: baseline.counts.materials, defaultPairs: baseline.rows, checks: ['Ashby title and metadata', 'family/subgroup/points grouping independent of shape', 'grouping preserves zoom and selection', 'legacy points-only links and retained experiments', 'titanium with both source temperatures', 'wood, elastomer and foam coverage', 'alternate chart suggestions', 'Python-backed indices and substituted values', 'axis reversal, zoom units and fit', '6061 T4/T6 separation and state search', 'reported-bound markers', 'source citations and lookup link', 'CSV', 'share restoration', 'temperature/basis/family filters', 'empty state', 'labels', 'settings and keyboard controls', 'dark/mobile', 'old URL redirect', 'data mismatch and retry', 'retained prototype API', 'stale service-worker cache refresh'], screenshots: ['/private/tmp/ashby-materials-desktop.png', '/private/tmp/ashby-materials-sourced.png', '/private/tmp/ashby-materials-dark-mobile.png'] }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
