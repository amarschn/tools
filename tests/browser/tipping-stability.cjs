/* Real Pyodide integration checks. Serve the repository root on port 8157. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/opt/homebrew/lib/node_modules/@playwright/test');
const base = process.env.TIPPING_TOOL_URL || 'http://127.0.0.1:8157/tools/tipping-stability/';

(async () => {
    const browser = await chromium.launch({ headless: true });
    try {
        const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, serviceWorkers: 'block', colorScheme: 'light' });
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await context.route('**/www.googletagmanager.com/**', (route) => route.fulfill({ contentType: 'application/javascript', body: '' }));
        await context.route('**/google-analytics.com/**', (route) => route.fulfill({ body: '' }));
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', (error) => errors.push(error.message));
        page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
        page.setDefaultTimeout(15000);
        const result = () => page.evaluate(() => window.TippingTool.getResults());
        const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-7, `${a} ≈ ${b}`);
        const boot = async (url = base) => {
            await page.goto(url);
            await page.locator('#tool-main[data-boot-state="ready"]').waitFor({ timeout: 120000 });
            await page.locator('#loading-overlay.hidden').waitFor({ state: 'attached' });
        };
        const calc = async () => {
            await page.locator('#calculate-btn').click();
            await page.waitForFunction(() => document.getElementById('dirty-note').hidden && !document.getElementById('calculate-btn').disabled);
        };
        const openDetails = async (id) => {
            if (await page.locator('#' + id).getAttribute('open') === null) await page.locator(`#${id} > summary`).click();
        };
        const revealInput = async (id) => {
            const parents = await page.locator('#' + id).evaluate((element) => {
                const ids = [];
                for (let parent = element.parentElement; parent; parent = parent.parentElement) if (parent.tagName === 'DETAILS') ids.unshift(parent.id);
                return ids;
            });
            for (const parent of parents) await openDetails(parent);
        };
        const fill = async (id, value) => {
            await revealInput(id);
            if (id === 'downhill_deg') {
                await page.locator('[data-direction-for="downhill_deg"]').selectOption(['0', '90', '180', '270'].includes(String(value)) ? String(value) : 'custom');
                if (['0', '90', '180', '270'].includes(String(value))) return;
            }
            await page.locator('#' + id).fill(String(value));
        };
        const select = async (id, value) => { await revealInput(id); await page.locator('#' + id).selectOption(value); };
        const showFbd = async () => {
            if (await page.locator('#toggle-fbd').getAttribute('aria-expanded') === 'false') await page.locator('#toggle-fbd').click();
        };
        const noOverflow = async () => {
            try {
                await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth + 1, null, { timeout: 5000 });
            } catch (error) {
                console.log(await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, elements: [...document.querySelectorAll('body *')].filter((el) => !el.closest('.table-wrap') && el.getBoundingClientRect().right > innerWidth + 1 && el.checkVisibility({ visibilityProperty: true })).slice(0, 15).map((el) => ({ tag: el.tagName, id: el.id, class: el.getAttribute('class'), right: el.getBoundingClientRect().right })) })));
                await page.screenshot({ path: '/private/tmp/tipping-stability-overflow.png', fullPage: true, animations: 'disabled' });
                throw error;
            }
        };
        const checkDiagramLabels = async () => {
            const issues = await page.evaluate(() => [...document.querySelectorAll('#model-scene, #fbd-scene')].filter((svg) => svg.getClientRects().length).flatMap((svg) => {
                const width = svg.viewBox.baseVal.width, height = svg.viewBox.baseVal.height;
                const boxes = [...svg.querySelectorAll('.diagram-label')].map((label) => ({text:label.textContent,box:label.getBBox()}));
                return boxes.flatMap(({text,box},i) => {
                    const errors = [];
                    if (box.x<0 || box.y<0 || box.x+box.width>width || box.y+box.height>height) errors.push(`${svg.id}: clipped ${text}`);
                    for (const other of boxes.slice(i+1)) {
                        if (box.x<other.box.x+other.box.width && box.x+box.width>other.box.x && box.y<other.box.y+other.box.height && box.y+box.height>other.box.y) errors.push(`${svg.id}: overlapping ${text} / ${other.text}`);
                    }
                    return errors;
                });
            }));
            assert.deepEqual(issues, []);
        };
        await boot();
        near((await result()).threshold.value, 33.690067525979785);
        assert.equal(await page.locator('#advanced-inputs').getAttribute('open'), null);
        assert.equal(await page.locator('#ground-inputs').getAttribute('open'), null);
        assert.equal(await page.locator('#calc-form input:visible, #calc-form select:visible').count(), 4);
        assert.equal(await page.locator('.url-state-share-btn').isVisible(), true);
        assert.equal(await page.locator('#model-scene').isVisible(), true);
        assert.equal(await page.locator('#fbd-scene').isVisible(), false);
        assert.equal(await page.locator('#force-key').isVisible(), false);
        assert.equal(await page.locator('#diagram-inspector').isVisible(), false);
        assert.equal(await page.locator('#plan-plot').isVisible(), false);
        assert.equal(await page.locator('#analysis-details').getAttribute('open'), null);
        assert.equal(await page.locator('#threshold-value').isVisible(), true);
        assert.equal(await page.locator('#model-scene .force-arrow').count(), 0);
        assert.ok(await page.locator('#model-scene [data-mesh="wheel"]').count() > 20);
        await page.screenshot({ path: '/private/tmp/tipping-simple-desktop.png', fullPage: true, animations: 'disabled' });
        await checkDiagramLabels();
        await page.setViewportSize({ width: 390, height: 844 });
        await page.screenshot({ path: '/private/tmp/tipping-simple-mobile.png', fullPage: true, animations: 'disabled' });
        await noOverflow();
        await page.setViewportSize({ width: 1440, height: 1050 });
        await page.locator('#toggle-fbd').focus();
        await page.keyboard.press('Space');
        assert.equal(await page.locator('#fbd-scene').isVisible(), true);
        assert.equal(await page.locator('#diagram-inspector').isVisible(), false);
        await page.locator('.model-workspace').screenshot({ path: '/private/tmp/tipping-fbd-disclosed.png', animations: 'disabled' });
        await openDetails('force-details');
        await select('diagram-edge', 'E1');
        assert.equal(await page.locator('#model-scene').getAttribute('data-edge'), 'E1');
        assert.equal(await page.locator('#fbd-scene').getAttribute('data-edge'), 'E1');
        assert.match(await page.locator('#fbd-subtitle').innerText(), /Right/);
        await page.locator('#force-key [data-entity="W"]').click();
        assert.equal(await page.locator('#force-key [data-entity="W"]').evaluate((el) => el === document.activeElement), true);
        assert.equal(await page.locator('#model-scene [data-entity="W"]').getAttribute('class'), 'force-arrow external linked-active');
        assert.equal(await page.locator('#fbd-scene [data-entity="W"]').getAttribute('class'), 'force-arrow external linked-active');
        assert.match(await page.locator('#diagram-inspector').innerText(), /3D force \(0.00, 0.00, -980.66\) N/);
        await page.locator('#fbd-scene [data-entity="N"]').first().click();
        assert.equal(await page.locator('#force-key [data-entity="N"]').getAttribute('aria-pressed'), 'true');
        await select('diagram-edge', 'E3');
        await page.locator('#force-key [data-entity="G"]').click();
        await page.locator('.model-workspace').screenshot({ path: '/private/tmp/tipping-linked-fbd-light.png', animations: 'disabled' });
        await checkDiagramLabels();
        await page.screenshot({ path: '/private/tmp/tipping-stability-light.png', fullPage: true, animations: 'disabled' });
        await noOverflow();
        await page.locator('[data-for="cg_height"]').focus();
        assert.match(await page.locator('#help-popup').innerText(), /normal to the surface/);
        await page.keyboard.press('Escape');
        await page.locator('[data-derivation="threshold"]').click();
        await page.waitForFunction(() => document.querySelector('#derivation-content mjx-container'));
        assert.match(await page.locator('#derivation-content').innerText(), /Equation \(2\)/);
        await page.locator('#close-derivation').click();
        await page.locator('#diagram-derivation').click();
        assert.match(await page.locator('#derivation-title').innerText(), /Free-body force balance/);
        await page.locator('#close-derivation').click();
        await page.locator('#analysis-details > summary').click();
        assert.equal(await page.locator('#plan-plot').isVisible(), false);
        assert.equal(await page.locator('[data-derivation="threshold"]').getAttribute('aria-expanded'), 'false');
        await page.locator('#toggle-fbd').click();
        assert.equal(await page.locator('#fbd-scene').isVisible(), false);
        assert.equal(await page.locator('#model-scene .force-arrow').count(), 0);
        await page.locator('#toggle-fbd').click();
        await openDetails('analysis-details');

        await select('load_case', 'turn');
        await fill('slope_deg', 10);
        await fill('downhill_deg', 270);
        assert.equal(await page.locator('#dirty-note').isVisible(), true);
        assert.equal(await page.locator('#export-csv').isDisabled(), true);
        assert.equal(await page.locator('#diagram-state').getAttribute('data-state'), 'stale');
        await calc();
        const radians = 10 * Math.PI / 180;
        near((await result()).threshold.value, Math.sqrt(2 * 9.80665 * ((.4 / .6) * Math.cos(radians) - Math.sin(radians))));
        assert.match((await result()).threshold.edge, /Right/);
        assert.equal(await page.locator('#diagram-state').getAttribute('data-state'), 'current');
        const weightArrow = await page.locator('#model-scene [data-entity="W"] .force-shaft').evaluate((line) => ({x1:Number(line.getAttribute('x1')),x2:Number(line.getAttribute('x2')),y1:Number(line.getAttribute('y1')),y2:Number(line.getAttribute('y2'))}));
        near(weightArrow.x1, weightArrow.x2);
        assert.ok(weightArrow.y2 > weightArrow.y1, 'Weight stays vertical downward in the inclined isometric view');
        await page.locator('#force-key [data-entity="I"]').click();
        assert.match(await page.locator('#diagram-inspector').innerText(), /Equivalent inertia/);
        await page.locator('.model-workspace').screenshot({ path: '/private/tmp/tipping-linked-fbd-turn.png', animations: 'disabled' });
        await page.locator('#tab-directions').click();
        assert.equal(await page.locator('#model-scene').isVisible(), true);
        assert.equal(await page.locator('#fbd-scene').isVisible(), true);
        await page.waitForFunction(() => document.getElementById('direction-plot').data?.length === 1);
        assert.equal(await page.locator('#direction-plot').evaluate((el) => el.layout.polar.radialaxis.type), 'linear');
        await page.locator('#tab-directions').focus();
        await page.keyboard.press('ArrowRight');
        assert.equal(await page.locator('#tab-background').getAttribute('aria-selected'), 'true');
        assert.equal(await page.locator('#model-scene').isVisible(), true);
        assert.equal(await page.locator('#theory-equations .equation-card').count(), 11);
        await page.locator('#tab-results').click();

        await select('load_case', 'combined');
        await select('limit_parameter', 'force');
        await fill('acceleration', 0);
        await fill('downhill_deg', 90);
        await fill('force', 100);
        await calc();
        near((await result()).threshold.value, 100 * 9.80665 * (.4 * Math.cos(radians) - .6 * Math.sin(radians)));
        await select('mass_mode', 'components');
        await page.locator('#components-rows tr').nth(1).locator('[data-field="y"]').fill('.15');
        await select('geometry_mode', 'custom');
        await page.locator('#contacts-rows tr').last().locator('button').click();
        await page.locator('#contacts-rows tr').last().locator('[data-field="x"]').fill('0');
        await openDetails('force-inputs');
        await page.locator('[data-add="extra_forces"]').click();
        await page.locator('#extra_forces-rows [data-field="name"]').fill('Arm, vertical load');
        await calc();
        let r = await result();
        assert.equal(r.equilibrium.polygon.length, 3);
        near(r.equilibrium.center[1], .03);
        assert.equal(r.equilibrium.loads.at(-1).name, 'Arm, vertical load');
        assert.equal(r.equilibrium.loads.at(-1).vector[2], -50);
        await page.locator('#force-key [data-entity="P2"]').click();
        assert.match(await page.locator('#diagram-inspector').innerText(), /Arm, vertical load/);
        await page.locator('.model-workspace').screenshot({ path: '/private/tmp/tipping-linked-fbd-combined.png', animations: 'disabled' });

        // The shared link preserves dynamic tables as well as scalar inputs.
        const before = r;
        await select('diagram-edge', 'E1');
        await page.locator('.url-state-share-btn').click();
        const shared = await page.evaluate(() => navigator.clipboard.readText());
        assert.match(shared, /components=/);
        assert.match(shared, /contacts=/);
        assert.match(shared, /extra_forces=/);
        assert.match(shared, /diagram-edge=E1/);
        await boot(shared);
        assert.deepEqual(await result(), before);
        assert.equal(await page.locator('#fbd-scene').getAttribute('data-edge'), 'E1');
        assert.equal(await page.locator('#fbd-scene').isVisible(), false);
        assert.equal(await page.locator('#analysis-details').getAttribute('open'), null);
        assert.match(await page.locator('#ground-summary').innerText(), /10° slope/);
        assert.match(await page.locator('#custom-summary').innerText(), /Component masses.*Custom contacts.*Extra loads/);
        await openDetails('analysis-details');
        const jsonDownload = page.waitForEvent('download');
        await page.locator('#export-json').click();
        const file = await jsonDownload;
        const exported = JSON.parse(await fs.readFile(await file.path(), 'utf8'));
        assert.deepEqual(exported.results, JSON.parse(JSON.stringify(before)));
        assert.equal(exported.inputs.components.length, 2);
        const csvDownload = page.waitForEvent('download');
        await page.locator('#export-csv').click();
        const csvFile = await csvDownload;
        const csv = await fs.readFile(await csvFile.path(), 'utf8');
        assert.match(csv, /Margin \(m\)/);
        assert.match(csv, /Arm, vertical load/);
        assert.match(csv, /Required ground yaw couple/);
        assert.match(csv, /Along edge \(N\)/);
        assert.ok(csv.includes(String(before.equilibrium.moment_reserve)));

        await page.locator('#settings-button').click();
        await page.locator('.settings-panel [data-theme="dark"]').click();
        await page.locator('.settings-panel [data-precision="4"]').click();
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('body').getAttribute('data-theme'), 'dark');
        const contrast = await page.locator('.url-state-share-btn').evaluate((el) => { const s = getComputedStyle(el); return s.color !== s.backgroundColor; });
        assert.equal(contrast, true);
        await page.locator('#advanced-inputs > summary').click();
        await page.screenshot({ path: '/private/tmp/tipping-stability-dark.png', fullPage: true, animations: 'disabled' });
        await page.reload();
        await page.locator('#tool-main[data-boot-state="ready"]').waitFor({ timeout: 120000 });
        assert.equal(await page.locator('body').getAttribute('data-theme'), 'dark');

        await page.setViewportSize({ width: 390, height: 844 });
        await showFbd();
        await openDetails('force-details');
        await openDetails('analysis-details');
        await openDetails('advanced-inputs');
        await noOverflow();
        await page.screenshot({ path: '/private/tmp/tipping-stability-mobile.png', fullPage: true, animations: 'disabled' });
        await page.locator('.model-workspace').screenshot({ path: '/private/tmp/tipping-linked-fbd-mobile.png', animations: 'disabled' });
        await checkDiagramLabels();
        await page.locator('#tab-directions').click();
        await noOverflow();
        await page.screenshot({ path: '/private/tmp/tipping-stability-directions-mobile.png', fullPage: true, animations: 'disabled' });
        await page.locator('#tab-background').click();
        await noOverflow();
        await page.locator('#tab-results').click();
        await page.locator('#settings-button').click();
        await page.locator('.settings-panel [data-density="compact"]').click();
        await page.locator('.settings-panel [data-theme="system"]').click();
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('body').getAttribute('data-theme'), 'system');
        assert.equal(await page.locator('body').getAttribute('data-density'), 'compact');
        await noOverflow();
        await page.locator('#reset-case').click();
        await fill('slope_deg', 90);
        await page.locator('#calculate-btn').click();
        assert.equal(await page.locator('#error-message').isVisible(), true);
        assert.equal(await page.locator('#result-content').isVisible(), false);
        assert.equal(await page.locator('#model-scene').isVisible(), true);
        assert.equal(await page.locator('#diagram-state').getAttribute('data-state'), 'invalid');
        assert.equal(await page.locator('#diagram-edge').isDisabled(), true);
        await fill('slope_deg', 0);
        await calc();
        near((await result()).threshold.value, 33.690067525979785);
        assert.equal(await page.locator('#diagram-edge').isEnabled(), true);
        await select('load_case', 'acceleration');
        await fill('accel_direction', 180);
        await calc();
        near((await result()).threshold.value, 9.80665);
        assert.match((await result()).threshold.edge, /Front/);
        await select('load_case', 'push');
        await calc();
        near((await result()).threshold.value, 392.266);
        if (await page.locator('#advanced-inputs').getAttribute('open') === null) await page.locator('#advanced-inputs > summary').click();
        await fill('force_vertical', 980.665);
        await calc();
        assert.match(await page.locator('#error-message').innerText(), /No compressive/);
        assert.equal(await page.locator('#result-content').isVisible(), false);

        // Collapsing the analysis must never hide the state of the current case.
        await boot();
        await fill('slope_deg', 35);
        await calc();
        assert.match(await page.locator('#status-title').innerText(), /Beyond the tipping threshold/);
        assert.equal(await page.locator('#status-title').isVisible(), true);
        assert.equal(await page.locator('#analysis-details').getAttribute('open'), null);
        assert.equal(await page.locator('#model-scene').isVisible(), true);
        await fill('slope_deg', 20);
        await fill('friction_coefficient', .2);
        await calc();
        assert.match(await page.locator('#model-scope').innerText(), /sliding limit exceeded/);
        assert.equal(await page.locator('#model-scope').getAttribute('data-warning'), 'true');
        assert.equal(await page.locator('#analysis-details').getAttribute('open'), null);

        // The friendly direction picker preserves arbitrary angles and old shared links.
        await fill('slope_deg', 0);
        await fill('friction_coefficient', '');
        await fill('downhill_deg', 37);
        await calc();
        near((await result()).threshold.value, Math.atan(Math.min(.6 / Math.cos(37 * Math.PI / 180), .4 / Math.sin(37 * Math.PI / 180)) / .6) * 180 / Math.PI);
        await page.locator('.url-state-share-btn').click();
        const customDirection = await page.evaluate(() => navigator.clipboard.readText());
        assert.match(customDirection, /downhill_deg=37/);
        await boot(customDirection);
        assert.equal(await page.locator('[data-direction-for="downhill_deg"]').inputValue(), 'custom');
        assert.match(await page.locator('#ground-summary').innerText(), /37° direction/);
        await fill('downhill_deg', 90);
        await select('load_case', 'push');
        assert.equal(await page.locator('#mass').isVisible(), true);
        assert.equal(await page.locator('#advanced-inputs').getAttribute('open'), null);
        await fill('mass', 200);
        await calc();
        near((await result()).threshold.value, 784.532);
        assert.deepEqual(errors, []);
        console.log(JSON.stringify({ checks: 'Progressive disclosure, linked FBD, real Python, all load modes, charts, derivations, tooltips, keyboard tabs, editable tables, share round-trip, exports, themes, mobile, and invalid input recovery passed.', screenshots: ['/private/tmp/tipping-simple-desktop.png', '/private/tmp/tipping-simple-mobile.png', '/private/tmp/tipping-fbd-disclosed.png'] }));
    } finally {
        await browser.close();
    }
})().catch((error) => { console.error(error); process.exitCode = 1; });
