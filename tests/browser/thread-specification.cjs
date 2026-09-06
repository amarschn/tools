/* Real Pyodide browser regression. Serve the repository root on port 8148. */
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/opt/homebrew/lib/node_modules/@playwright/test');
const url = process.env.THREAD_TOOL_URL || 'http://127.0.0.1:8148/tools/thread-visualizer-sizer/';

(async () => {
    const browser = await chromium.launch({ headless: true });
    try {
        const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, serviceWorkers: 'block' });
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', (error) => errors.push(error.message));
        page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
        page.setDefaultTimeout(12000);
        const boot = async (address = url) => {
            await page.goto(address);
            await page.locator('#tool-main[data-boot-state="ready"]').waitFor({ timeout: 120000 });
            await page.locator('#loading-overlay.hidden').waitFor({ state: 'attached' });
        };
        const callout = () => page.locator('#drawing-callout').innerText();
        const select = async (id, value) => { await page.locator('#' + id).selectOption(value); };
        const open = async (id) => {
            if (!await page.locator('#' + id).getAttribute('open').then((value) => value !== null)) await page.locator('#' + id + ' > summary').click();
        };
        const noOverflow = async () => assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
        const checkFamilyDiagram = async () => {
            // Assert text bounds and arrow/line attachment on the drawing itself.
            await page.waitForFunction(() => {
                const svg = document.querySelector('#family-profile-svg');
                return svg.viewBox.baseVal.width === (svg.parentElement.clientWidth < 540 ? 300 : 620);
            });
            const problems = await page.locator('#family-profile-svg').evaluate((svg) => {
                const bounds = svg.getBoundingClientRect();
                const clipped = [...svg.querySelectorAll('text')].filter((text) => {
                    const box = text.getBoundingClientRect();
                    return box.left < bounds.left || box.right > bounds.right || box.top < bounds.top || box.bottom > bounds.bottom;
                }).map((text) => text.textContent);
                const detached = [...svg.querySelectorAll('.family-dimension')].filter((group) => {
                    const line = group.querySelector('line');
                    const tips = [...group.querySelectorAll('polygon')].map((polygon) => [polygon.points[0].x, polygon.points[0].y]);
                    return JSON.stringify(tips) !== JSON.stringify([[line.x1.baseVal.value, line.y1.baseVal.value], [line.x2.baseVal.value, line.y2.baseVal.value]]);
                }).map((group) => group.getAttribute('aria-label'));
                const envelope = svg.querySelector('#family-taper-envelope');
                let taperError = false;
                if (envelope) {
                    const [x1, y1, x2, y2] = envelope.getAttribute('d').match(/-?\d+(?:\.\d+)?/g).map(Number);
                    taperError = Math.abs(2 * Math.abs(y2 - y1) / (x2 - x1) - Number(envelope.dataset.diameterTaper)) > 1e-10;
                }
                return { clipped, detached, taperError };
            });
            assert.deepEqual(problems, { clipped: [], detached: [], taperError: false });
        };
        const visibleControls = () => page.locator('#spec-form input:visible, #spec-form select:visible').count();
        const help = (id) => page.locator('[data-help-for="' + id + '"]');
        const tooltip = (id) => page.locator('#' + id + '-tooltip');
        const tooltipInViewport = async (id) => {
            const box = await tooltip(id).boundingBox();
            assert.ok(box, 'Tooltip is visible for ' + id);
            const viewport = page.viewportSize();
            assert.ok(box.x >= 0 && box.y >= 0 && box.x + box.width <= viewport.width && box.y + box.height <= viewport.height, 'Tooltip stays in the viewport for ' + id);
        };
        await boot();
        console.log('Real Pyodide initialized.');
        assert.equal(await callout(), 'M10 x 1.5-6H THRU');
        assert.equal(await visibleControls(), 3);
        assert.equal(await page.locator('#spec-family option').count(), 11);
        assert.deepEqual(await page.locator('.primary-tab').allTextContents(), ['Specify a thread', 'Design thread for load', 'Find a thread']);
        assert.equal(await page.locator('#spec-form details[open]').count(), 0);
        assert.equal(await page.locator('#spec-output details[open]').count(), 0);
        assert.equal(await page.locator('#spec-note').isVisible(), true);
        assert.equal(await page.locator('#spec-note').evaluate((note) => note.closest('details')), null);
        assert.equal(await page.locator('#spec-note').evaluate((note) => note.scrollHeight <= note.clientHeight + 1), true);
        assert.equal(await page.locator('#review-details').count(), 0);
        assert.equal(await page.locator('#copy-drawing-callout').innerText(), '');
        assert.equal(await page.locator('#copy-detailed-note').innerText(), '');
        assert.equal(await page.locator('#copy-drawing-callout').getAttribute('aria-label'), 'Copy callout');
        assert.equal(await page.locator('#copy-detailed-note').getAttribute('aria-label'), 'Copy detailed note');
        assert.equal(await page.locator('.primary-tabs').evaluate((el) => getComputedStyle(el).borderTopStyle), 'solid');
        const selectedTabColor = await page.locator('#tab-specify').evaluate((el) => getComputedStyle(el).backgroundColor);
        assert.notEqual(selectedTabColor, await page.locator('#tab-find').evaluate((el) => getComputedStyle(el).backgroundColor));
        assert.equal(await page.locator('#spec-form .thread-help-trigger').count(), await page.locator('#spec-form input[id], #spec-form select[id]').count());
        assert.equal(await page.locator('.thread-help-trigger:visible').count(), 3);
        assert.equal(await page.evaluate(() => [...document.querySelectorAll('#spec-form input[id], #spec-form select[id]')].every((control) => {
            const id = control.getAttribute('aria-describedby');
            const button = document.querySelector('[data-help-for="' + control.id + '"]');
            return button?.type === 'button' && button.parentElement.contains(control.labels[0]) &&
                button.getAttribute('aria-describedby') === id && document.getElementById(id)?.textContent.trim().length > 20;
        })), true);
        await page.locator('#thread-details > summary').focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#spec-fit').isVisible(), true);
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#spec-fit').isVisible(), false);
        assert.equal(await page.locator('#thread-references').isVisible(), true);
        assert.equal(await page.evaluate(() => document.querySelector('.thread-reference-area').getBoundingClientRect().top >= document.querySelector('#thread-task-panel').getBoundingClientRect().bottom), true);
        const sharedProfile = await page.locator('#thread-profile-svg').elementHandle();
        await page.screenshot({ path: '/tmp/thread-workspace-desktop.png', fullPage: true, animations: 'disabled' });
        await page.locator('#copy-drawing-callout').click();
        assert.equal(await page.evaluate(() => navigator.clipboard.readText()), await callout());
        assert.equal(await page.locator('#copy-drawing-callout .copied-glyph').isVisible(), true);
        await page.locator('#copy-detailed-note').click();
        assert.equal(await page.evaluate(() => navigator.clipboard.readText()), await page.locator('#spec-note').innerText());
        assert.equal(await page.locator('#copy-detailed-note .copied-glyph').isVisible(), true);
        const home = await context.newPage();
        await home.goto(new URL('../../', url).toString());
        const homepageStyle = await home.evaluate(() => ({
            background: getComputedStyle(document.body).backgroundColor,
            font: getComputedStyle(document.body).fontFamily,
            title: getComputedStyle(document.querySelector('h1')).fontSize,
            brand: document.querySelector('.wordmark').textContent.trim()
        }));
        assert.deepEqual(await page.evaluate(() => ({
            background: getComputedStyle(document.body).backgroundColor,
            font: getComputedStyle(document.body).fontFamily,
            title: getComputedStyle(document.querySelector('h1')).fontSize,
            brand: document.querySelector('.nav-brand').textContent.trim()
        })), homepageStyle);
        await home.screenshot({ path: '/tmp/thread-homepage-style-reference.png', animations: 'disabled' });
        await home.close();

        await open('expert-options');
        for (const [id, explanation] of [
            ['spec-process', /process.*detailed note/s], ['spec-material-family', /broad category/],
            ['spec-material', /6061-T6/], ['spec-finish', /before or after finishing/],
            ['spec-inspection', /plug\/ring gage/]
        ]) {
            await help(id).scrollIntoViewIfNeeded();
            await help(id).hover();
            await tooltipInViewport(id);
            assert.match(await tooltip(id).innerText(), explanation);
            assert.equal(await page.locator('[role="tooltip"]:visible').count(), 1);
            await page.keyboard.press('Escape');
            assert.equal(await tooltip(id).isVisible(), false);
        }
        await help('spec-process').scrollIntoViewIfNeeded();
        await help('spec-process').focus();
        assert.equal(await tooltip('spec-process').isVisible(), true);
        await page.keyboard.press('Enter');
        await page.mouse.move(0, 0);
        assert.equal(await tooltip('spec-process').isVisible(), true);
        await page.keyboard.press('Escape');
        assert.equal(await tooltip('spec-process').isVisible(), false);
        assert.equal(await help('spec-process').evaluate((button) => button === document.activeElement), true);
        await page.keyboard.press('Tab');
        assert.equal(await page.locator('#spec-process').evaluate((control) => control === document.activeElement), true);
        await help('spec-material').click();
        await page.locator('#spec-input-heading').click();
        assert.equal(await tooltip('spec-material').isVisible(), false);
        assert.equal(await callout(), 'M10 x 1.5-6H THRU');
        assert.equal(await page.locator('#spec-output').getAttribute('data-stale'), 'false');
        await page.locator('#expert-options > summary').click();

        await select('spec-feature', 'blind');
        assert.equal(await page.locator('#copy-drawing-callout').isDisabled(), true);
        assert.equal(await page.locator('#spec-error').innerText(), 'Enter a positive usable full-thread depth / length.');
        for (const depth of ['15', '', '0', '-1']) {
            await page.locator('#spec-depth').fill(depth);
            await page.locator('#spec-update').click();
            if (depth === '15') {
                assert.match(await callout(), /15 mm MIN FULL THREAD DEPTH/);
                await page.locator('#copy-detailed-note').click();
                assert.match(await page.evaluate(() => navigator.clipboard.readText()), /drill depth separately/);
            } else {
                assert.equal(await page.locator('#spec-error').innerText(), 'Enter a positive usable full-thread depth / length.');
                assert.equal(await page.locator('#copy-detailed-note').isDisabled(), true);
            }
        }
        await select('spec-feature', 'through');
        await open('expert-options');
        assert.equal(await page.locator('#spec-process option[value="rolled"]').count(), 0);
        await select('spec-process', 'form_tapped');
        await help('spec-process').hover();
        assert.match(await tooltip('spec-process').innerText(), /Form tapped/);
        assert.match(await tooltip('spec-process').innerText(), /without cutting chips/);
        await page.screenshot({ path: '/tmp/thread-expert-tooltip-desktop.png', animations: 'disabled' });
        await page.keyboard.press('Escape');
        await select('spec-material-family', 'aluminium');
        await page.locator('#spec-material').fill('6061-T6');
        await page.locator('#spec-update').click();
        await page.locator('#copy-detailed-note').click();
        assert.match(await page.evaluate(() => navigator.clipboard.readText()), /6061-T6/);
        assert.match(await page.locator('#spec-note').textContent(), /Form tapped/i);
        await page.screenshot({ path: '/tmp/thread-workspace-expert.png', fullPage: true, animations: 'disabled' });

        await page.locator('#tab-load').click();
        assert.equal(await visibleControls(), 3);
        assert.equal(await page.locator('#spec-family option').count(), 3);
        assert.equal(await callout(), 'M10 x 1.5-6g');
        assert.equal(await page.locator('#thread-profile-svg').evaluate((node, original) => node === original, sharedProfile), true);
        assert.match(await page.locator('#result-evidence').innerText(), /Proof margin/);
        await open('calculation-details');
        assert.match(await page.locator('#evidence-heading').innerText(), /Capacity boundary/i);
        await page.locator('#axial_load').fill('1000000');
        await page.locator('#spec-update').click();
        assert.match(await callout(), /No passing thread/);
        assert.match(await page.locator('#evidence-heading').innerText(), /Catalog limit/i);
        assert.equal(await page.locator('#copy-drawing-callout').isDisabled(), true);
        assert.equal(await page.locator('#machine-profile').isVisible(), false);
        await page.locator('#axial_load').fill('20');
        await page.locator('#spec-update').click();
        await open('expert-options');
        await select('spec-process', 'rolled');
        await help('spec-process').hover();
        assert.match(await tooltip('spec-process').innerText(), /Dies displace material/);
        await page.keyboard.press('Escape');
        await select('spec-material-family', 'stainless');
        assert.equal(await page.locator('#proof_strength').inputValue(), '');
        assert.match(await page.locator('#spec-error').innerText(), /verified minimum proof strength/);
        const incompleteLink = await page.evaluate(() => window.threadSpecification.shareUrl());
        assert.equal(new URL(incompleteLink).searchParams.get('spec_proof_strength'), '');
        await page.locator('#proof_strength').fill('450');
        await page.locator('#spec-update').click();
        assert.match(await page.locator('#spec-note').textContent(), /450 MPa/);
        await open('dimension-details');
        const loadDownloadEvent = page.waitForEvent('download');
        await page.locator('#export-results').click();
        const loadDownload = await loadDownloadEvent;
        let loadCsv = '';
        for await (const chunk of await loadDownload.createReadStream()) loadCsv += chunk.toString();
        assert.match(loadCsv, /"Entered minimum proof strength","450","MPa"/);
        assert.match(loadCsv, /"Proof margin"/);
        assert.match(loadCsv, /"Detailed note"/);
        await page.screenshot({ path: '/tmp/thread-workspace-load.png', fullPage: true, animations: 'disabled' });

        await page.locator('#tab-find').click();
        assert.equal(await visibleControls(), 0);
        assert.equal(await page.locator('#find-diameter').inputValue(), '');
        await page.locator('#find-diameter').fill('9.96');
        await page.locator('#find-pitch').fill('1.5');
        await page.locator('#find-update').click();
        await page.locator('.candidate-select').filter({ hasText: 'M10x1.5' }).click();
        assert.equal(await callout(), 'M10x1.5');
        assert.equal(await page.locator('#thread-profile-svg').evaluate((node, original) => node === original, sharedProfile), true);
        await page.locator('[data-view="engaged"]').click();
        assert.match(await page.locator('#thread-svg-title').textContent(), /engaged/);
        assert.equal(await page.locator('#thread-profile-svg').evaluate((svg) => {
            const label = svg.querySelector('[data-thread-layout="desktop"] [data-thread-view="engaged"] [data-label="pitch"]');
            const bounds = label.getBBox();
            return bounds.y + bounds.height < svg.viewBox.baseVal.height;
        }), true);
        await page.locator('#find-pitch').fill('1');
        await page.locator('#find-update').click();
        await page.locator('.candidate-select').filter({ hasText: 'M10x1' }).click();
        assert.equal(await callout(), 'M10x1.0');
        assert.match(await page.locator('#spec-note').textContent(), /POSSIBLE NOMINAL CANDIDATE/);
        await page.locator('#tab-specify').click();
        assert.equal(await page.locator('#spec-material').inputValue(), '6061-T6');
        assert.equal(await page.locator('#spec-process').inputValue(), 'form_tapped');

        await select('spec-family', 'unf');
        await select('spec-feature', 'external');
        await page.locator('#spec-depth').fill('0.5');
        await open('thread-details');
        await select('spec-hand', 'LH');
        assert.equal(await callout(), '1/4-28 UNF-2A-LH\n0.5 in MIN FULL THREAD LENGTH');
        await page.locator('#copy-link').click();
        const shared = await page.evaluate(() => navigator.clipboard.readText());
        await boot(shared);
        assert.equal(await callout(), '1/4-28 UNF-2A-LH\n0.5 in MIN FULL THREAD LENGTH');
        await open('thread-details');
        await select('spec-family', 'npt');
        assert.equal(await callout(), '1/4-18 NPT');
        assert.equal(await page.locator('#spec-fit').isVisible(), false);
        assert.equal(await page.locator('#schematic-profile').isVisible(), true);
        assert.match(await page.locator('#family-profile-note').innerText(), /Schematic only/);
        assert.match(await page.locator('#family-pitch-label').textContent(), /18 TPI/);
        assert.match(await page.locator('#family-taper-label').textContent(), /1:16/);
        assert.equal(await page.locator('#family-included-angle').textContent(), '60°');
        await checkFamilyDiagram();
        await page.locator('#schematic-profile').screenshot({ path: '/tmp/thread-pipe-npt-desktop.png', animations: 'disabled' });
        await select('spec-size', '1/2');
        assert.match(await page.locator('#family-pitch-label').textContent(), /14 TPI/);
        await select('spec-family', 'nptf');
        await select('spec-fit', '2');
        assert.equal(await callout(), '1/4-18 NPTF-2');
        await select('spec-family', 'bspp');
        assert.equal(await callout(), 'G 1/4');
        assert.match(await page.locator('#family-taper-label').textContent(), /no taper/);
        assert.equal(await page.locator('#family-included-angle').textContent(), '55°');
        assert.match(await page.locator('#family-pitch-label').textContent(), /19 TPI/);
        await select('spec-feature', 'pipe_external');
        assert.equal(await callout(), 'G 1/4 A');
        await select('spec-family', 'bspt');
        assert.match(await page.locator('#family-taper-label').textContent(), /1:16/);
        await select('spec-fit', 'Rp');
        assert.equal(await callout(), 'Rp 1/4');
        assert.match(await page.locator('#family-taper-label').textContent(), /no taper/);
        assert.equal(await page.locator('#family-taper-envelope').getAttribute('data-diameter-taper'), '0');
        await checkFamilyDiagram();
        await select('spec-family', 'unef');
        await select('spec-size', '1 1/2-18 UNEF');
        assert.equal(await callout(), '1 1/2-18 UNEF-2B THRU');
        assert.equal(await page.locator('#machine-profile').isVisible(), true);
        await open('dimension-details');
        const downloadEvent = page.waitForEvent('download');
        await page.locator('#export-results').click();
        assert.equal((await downloadEvent).suggestedFilename(), 'thread-results.csv');

        for (const family of ['forming_metal', 'forming_plastic', 'wood']) {
            await select('spec-family', family);
            assert.equal(await page.locator('#spec-product').isVisible(), true);
            assert.equal(await page.locator('#callout-symbol').isVisible(), false);
            assert.match(await callout(), /^DRAFT:/);
            assert.match(await page.locator('#family-overview').textContent(), /d: not specified/);
            assert.match(await page.locator('#family-closeup').textContent(), /supplier data needed/);
            assert.equal(await page.locator('#family-included-angle').count(), 0);
            await checkFamilyDiagram();
        }
        await page.locator('#spec-product').fill('Supplier <img src=x onerror=alert(1)>');
        await page.locator('#spec-screw-diameter').fill('4');
        await page.locator('#spec-screw-length').fill('30');
        await page.locator('#spec-update').click();
        assert.match(await callout(), /<img src=x onerror=alert\(1\)>/);
        assert.equal(await page.locator('#spec-output img').count(), 0);
        assert.match(await page.locator('#family-overview').textContent(), /d = 4 mm/);
        assert.match(await page.locator('#family-overview').textContent(), /L = 30 mm/);
        await page.locator('#schematic-profile').screenshot({ path: '/tmp/thread-product-desktop.png', animations: 'disabled' });
        await open('product-details');
        await select('spec-product-unit', 'in');
        assert.match(await page.locator('#family-overview').textContent(), /L = 30 in/);

        await select('spec-family', 'metric');
        await page.locator('#settings-button').click();
        await page.locator('label.switch').click();
        assert.equal(await page.locator('#setting-auto-update').isChecked(), false);
        await page.locator('#settings-close').click();
        await select('spec-size', 'M4x0.5');
        assert.equal(await page.locator('#copy-drawing-callout').isDisabled(), true);
        assert.equal(await page.locator('#export-results').isDisabled(), true);
        assert.equal(await callout(), 'M10 x 1.5-6H THRU');
        await page.locator('#spec-update').click();
        assert.equal(await callout(), 'M4 x 0.5-6H THRU');
        await page.locator('#settings-button').click();
        await page.locator('label.switch').click();
        await page.locator('[data-setting-theme="dark"]').click();
        await page.locator('[data-setting-density="compact"]').click();
        await page.locator('[data-setting-precision="4"]').click();
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#settings-panel').getAttribute('aria-hidden'), 'true');
        await page.setViewportSize({ width: 390, height: 844 });
        await noOverflow();
        await help('spec-finish').scrollIntoViewIfNeeded();
        await help('spec-finish').click();
        await tooltipInViewport('spec-finish');
        await page.screenshot({ path: '/tmp/thread-expert-tooltip-mobile-dark.png', animations: 'disabled' });
        await page.keyboard.press('Escape');
        await page.screenshot({ path: '/tmp/thread-workspace-mobile-dark.png', fullPage: true, animations: 'disabled' });
        await open('thread-guide');
        await page.locator('.handbook-toc a[href="#thread-references"]').click();
        assert.equal(await page.locator('.reference-sources').getAttribute('open'), '');
        await noOverflow();
        await page.screenshot({ path: '/tmp/thread-workspace-reference-dark.png', fullPage: true, animations: 'disabled' });
        await page.locator('#settings-button').click();
        await page.locator('[data-setting-theme="light"]').click();
        await page.locator('#settings-close').click();
        await page.setViewportSize({ width: 320, height: 800 });
        await noOverflow();
        await help('spec-inspection').scrollIntoViewIfNeeded();
        await help('spec-inspection').click();
        await tooltipInViewport('spec-inspection');
        await page.screenshot({ path: '/tmp/thread-expert-tooltip-mobile-light.png', animations: 'disabled' });
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('.primary-tabs').evaluate((el) => el.scrollWidth <= el.clientWidth), true);
        await boot(url + '?mode=identify&system=unified&diameter=0.25&pitch=20&view=engaged');
        assert.equal(await page.locator('#tab-find').getAttribute('aria-selected'), 'true');
        await page.locator('.candidate-select').filter({ hasText: '1/4-20 UNC' }).click();
        assert.equal(await callout(), '1/4-20 UNC');
        await noOverflow();
        await boot(incompleteLink);
        assert.equal(await page.locator('#tab-load').getAttribute('aria-selected'), 'true');
        assert.equal(await page.locator('#proof_strength').inputValue(), '');
        assert.equal(await page.locator('#copy-drawing-callout').isDisabled(), true);
        assert.match(await page.locator('#spec-error').innerText(), /verified minimum proof strength/);
        await boot();
        assert.equal(await visibleControls(), 3);
        assert.equal(await page.locator('#spec-form details[open]').count(), 0);
        assert.equal(await page.locator('#spec-output details[open]').count(), 0);
        await page.setViewportSize({ width: 390, height: 844 });
        await page.screenshot({ path: '/tmp/thread-workspace-mobile-default.png', fullPage: true, animations: 'disabled' });
        assert.equal(await page.locator('#spec-note').isVisible(), true);
        assert.equal(await page.locator('#spec-note').evaluate((note) => note.scrollHeight <= note.clientHeight + 1), true);
        await page.locator('[data-view="engaged"]').click();
        assert.equal(await page.locator('#thread-profile-svg').evaluate((svg) => {
            const label = svg.querySelector('[data-thread-layout="mobile"] [data-thread-view="engaged"] [data-label="pitch"]');
            const bounds = label.getBBox();
            return bounds.y + bounds.height < svg.viewBox.baseVal.height;
        }), true);
        await page.screenshot({ path: '/tmp/thread-workspace-mobile-engaged.png', fullPage: true, animations: 'disabled' });

        // Each pipe/product family must stay annotated and legible in both themes
        // at the narrowest supported width, including a live resize without reload.
        await page.setViewportSize({ width: 320, height: 800 });
        for (const theme of ['light', 'dark']) {
            await page.locator('#settings-button').click();
            await page.locator(`[data-setting-theme="${theme}"]`).click();
            await page.locator('#settings-close').click();
            for (const family of ['npt', 'nptf', 'bspp', 'bspt', 'forming_metal', 'forming_plastic', 'wood']) {
                await select('spec-family', family);
                await checkFamilyDiagram();
                await noOverflow();
                if (['npt', 'wood'].includes(family)) await page.locator('#schematic-profile').screenshot({ path: `/tmp/thread-${family}-mobile-${theme}.png`, animations: 'disabled' });
            }
        }

        const touchContext = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, serviceWorkers: 'block' });
        const touch = await touchContext.newPage();
        touch.on('pageerror', (error) => errors.push(error.message));
        await touch.goto(url);
        await touch.locator('#tool-main[data-boot-state="ready"]').waitFor({ timeout: 120000 });
        await touch.locator('#loading-overlay.hidden').waitFor({ state: 'attached' });
        await touch.locator('#expert-options > summary').tap();
        const touchHelp = touch.locator('[data-help-for="spec-material-family"]');
        await touchHelp.tap();
        assert.equal(await touch.locator('#spec-material-family-tooltip').isVisible(), true);
        await touch.screenshot({ path: '/tmp/thread-expert-tooltip-touch.png', animations: 'disabled' });
        await touchHelp.tap();
        assert.equal(await touch.locator('#spec-material-family-tooltip').isVisible(), false);
        await touchHelp.tap();
        await touch.locator('#spec-material-family').tap();
        assert.equal(await touch.locator('#spec-material-family-tooltip').isVisible(), false);
        await touchContext.close();
        assert.deepEqual(errors, []);
        console.log('PASS: progressive defaults, shared results, independent task states, expert notes, blind depth, no-size boundary, identification, 11 families, clipboard, links, CSV, references, themes, mobile, pipe taper/pitch, product dimensions, arrow endpoints, and visible help for every input (hover, keyboard, touch and contextual content).');
    } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
