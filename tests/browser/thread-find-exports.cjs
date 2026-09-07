/* End-to-end Find, vector-PDF scale and lazy/cancelable STEP controls. */
const { chromium } = require('/opt/homebrew/lib/node_modules/@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const url = process.env.THREAD_TOOL_URL || 'http://127.0.0.1:8148/tools/thread-visualizer-sizer/';

(async () => {
    const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
    const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, serviceWorkers: 'block' });
    const errors = [], requests = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('request', (request) => requests.push(request.url()));
    const boot = async (target = url) => {
        await page.goto(target);
        await page.waitForSelector('#tool-main[data-boot-state="ready"]', { timeout: 60000 });
    };
    const update = () => page.locator('#find-update').click();
    const hasCAD = () => requests.some((path) => /replicad|thread-cad-worker/.test(path));
    try {
        await boot();
        assert.equal(await page.evaluate(() => {
            const ids = [...document.querySelectorAll('[id]')].map((node) => node.id);
            return ids.length === new Set(ids).size;
        }), true, 'HTML and generated help IDs must be unique');
        assert.equal(await page.evaluate(() => [...document.querySelectorAll('#find-form input, #find-form select, #thread-export-controls input, #thread-export-controls select')].every((field) => document.querySelector(`[data-help-for="${field.id}"]`) && field.labels.length)), true);
        assert.equal(hasCAD(), false);
        await page.locator('#tab-find').click();
        assert.equal(await page.locator('#find-diameter').inputValue(), '');
        assert.equal(await page.locator('#find-pitch').inputValue(), '');
        assert.equal(await page.locator('.candidate-select').count(), 0);
        await page.locator('#find-diameter').fill('8.4');
        await page.locator('#find-pitch').fill('1.5');
        await page.locator('#find-side').selectOption('internal');
        await update();
        await page.locator('.candidate-select').filter({ hasText: 'M10x1.5' }).click();
        assert.equal(await page.locator('#drawing-callout').innerText(), 'M10x1.5');
        assert.doesNotMatch(await page.locator('#drawing-callout').innerText(), /6H|6g|2A|2B/);
        await page.locator('#find-unit').selectOption('in');
        assert.ok(Math.abs(Number(await page.locator('#find-diameter').inputValue()) * 25.4 - 8.4) < 1e-12);
        assert.equal(await page.locator('#copy-drawing-callout').isDisabled(), true);
        await page.locator('#find-unit').selectOption('mm');
        await page.locator('#find-pitch-unit').selectOption('tpi');
        assert.ok(Math.abs(Number(await page.locator('#find-pitch').inputValue()) - 25.4 / 1.5) < 1e-12);
        await page.locator('#find-pitch-unit').selectOption('mm');
        await update();
        await page.locator('.candidate-select').filter({ hasText: 'M10x1.5' }).click();
        const link = await page.evaluate(() => window.threadSpecification.shareUrl());
        await boot(link);
        assert.equal(await page.locator('#drawing-callout').innerText(), 'M10x1.5');
        assert.equal(await page.locator('#find-side').inputValue(), 'internal');
        await page.locator('#find-more > summary').click();
        await page.locator('#find-span').fill('15');
        await page.locator('#find-intervals').fill('10');
        await update();
        assert.match(await page.locator('#find-explanation').textContent(), /15 \/ 10 = 1.5 mm/);
        await page.locator('#find-more > summary').click();
        await page.locator('#find-pitch').fill('');
        await update();
        await page.locator('#open-print').click();
        await page.locator('#preview-thread-pdf').click();
        const downloadEvent = page.waitForEvent('download');
        await page.locator('#download-thread-pdf').click();
        const pdf = await downloadEvent;
        await pdf.saveAs('/private/tmp/thread-comparison-letter.pdf');
        assert.equal(hasCAD(), false, 'PDF must not load CAD assets');

        const scale = await page.evaluate(async () => {
            const { buildComparisonPDF, mmToPoints } = await import('./thread-print.js');
            const lib = await import('./vendor/pdf-lib-1.17.1/pdf-lib.esm.min.js');
            const record = window.threadFinder.result.candidates.find((row) => row.family === 'metric');
            const check = async (paper) => {
                const { bytes, manifest } = await buildComparisonPDF([record], { paper });
                const doc = await lib.PDFDocument.load(bytes);
                const page = doc.getPage(0);
                const contents = page.node.Contents().asArray().map((ref) => new TextDecoder().decode(lib.decodePDFRawStream(doc.context.lookup(ref)).decode())).join('\n');
                const lines = [...contents.matchAll(/(-?[\d.]+) (-?[\d.]+) m\s+(-?[\d.]+) (-?[\d.]+) l/g)].map((m) => m.slice(1).map(Number));
                const lengths = lines.map(([x1, y1, x2, y2]) => [Math.abs(x2 - x1), Math.abs(y2 - y1)]);
                return { box: page.getSize(), manifest, lengths };
            };
            return { inch: mmToPoints(25.4), letter: await check('letter'), a4: await check('a4') };
        });
        assert.equal(scale.inch, 72);
        assert.ok(Math.abs(scale.letter.box.width - 612) < 1e-9);
        assert.ok(Math.abs(scale.letter.box.height - 792) < 1e-9);
        for (const sheet of [scale.letter, scale.a4]) {
            assert.ok(sheet.lengths.some(([x, y]) => Math.abs(x - 100 * 72 / 25.4) < 1e-8 && y === 0));
            assert.ok(sheet.lengths.some(([x, y]) => Math.abs(y - 100 * 72 / 25.4) < 1e-8 && x === 0));
            assert.ok(sheet.lengths.some(([x, y]) => Math.abs(x - 72) < 1e-8 && y === 0));
        }
        fs.writeFileSync('/private/tmp/thread-pdf-scale-check.json', JSON.stringify(scale, null, 2));
        await page.locator('#print-scope').selectOption('common');
        await page.locator('#print-paper').selectOption('a4');
        await page.locator('#preview-thread-pdf').click();
        const commonEvent = page.waitForEvent('download');
        await page.locator('#download-thread-pdf').click();
        await (await commonEvent).saveAs('/private/tmp/thread-common-a4.pdf');
        assert.equal(hasCAD(), false);
        const commonCheck = await page.evaluate(async (encoded) => {
            const lib = await import('./vendor/pdf-lib-1.17.1/pdf-lib.esm.min.js');
            const doc = await lib.PDFDocument.load(Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0)));
            return doc.getPages().map((page) => {
                const text = page.node.Contents().asArray().map((ref) => new TextDecoder().decode(lib.decodePDFRawStream(doc.context.lookup(ref)).decode())).join('\n');
                const lines = [...text.matchAll(/(-?[\d.]+) (-?[\d.]+) m\s+(-?[\d.]+) (-?[\d.]+) l/g)].map((m) => m.slice(1).map(Number));
                return { size: page.getSize(), horizontal: lines.some(([x, y, a, b]) => Math.abs(a - x - 100 * 72 / 25.4) < 1e-8 && y === b), vertical: lines.some(([x, y, a, b]) => Math.abs(y - b - 100 * 72 / 25.4) < 1e-8 && x === a), clipped: lines.some(([x, y, a, b]) => Math.min(x, y, a, b) < 0 || Math.max(x, a) > page.getWidth() || Math.max(y, b) > page.getHeight()) };
            });
        }, fs.readFileSync('/private/tmp/thread-common-a4.pdf').toString('base64'));
        assert.ok(commonCheck.length > 1);
        assert.ok(commonCheck.every((page) => page.horizontal && page.vertical && !page.clipped));

        await page.locator('#open-print').click();
        await page.locator('#find-span').evaluate((field) => field.value = '');
        await page.locator('#find-intervals').evaluate((field) => field.value = '');
        await page.locator('#find-side').selectOption('external');
        await page.locator('#find-diameter').fill('');
        await page.locator('#find-pitch-unit').selectOption('tpi');
        await page.locator('#find-pitch').fill('27');
        await update();
        await page.locator('.candidate-select').filter({ hasText: /^1\/16 NPT ·/ }).click();
        assert.match(await page.locator('#family-taper-label').textContent(), /1:16/);
        assert.match(await page.locator('#spec-note').textContent(), /PITCH ONLY/);

        await page.locator('#tab-specify').click();
        await page.locator('#spec-family').selectOption('unf');
        await page.locator('#tab-find').click();
        await page.locator('#find-example').click();
        await page.locator('.candidate-select').filter({ hasText: 'M8x1.25' }).click();
        await page.locator('.find-candidate > .btn-secondary').click();
        await page.locator('[data-cancel-replace]').click();
        assert.equal(await page.locator('#tab-find').getAttribute('aria-selected'), 'true');
        assert.equal(await page.locator('#spec-family').inputValue(), 'unf');
        await page.locator('.find-candidate > .btn-secondary').click();
        await page.locator('[data-confirm-replace]').click();
        assert.equal(await page.locator('#tab-specify').getAttribute('aria-selected'), 'true');
        assert.match(await page.locator('#task-assumptions').innerText(), /design choices/);
        await page.locator('#open-step').click();
        await page.locator('#step-length').fill('5');
        await page.locator('#preview-thread-step').click();
        const stepEvent = page.waitForEvent('download');
        await page.locator('#download-thread-step').click();
        const step = await stepEvent;
        assert.match(step.suggestedFilename(), /representative-v2\.step$/);
        assert.equal(hasCAD(), true);
        await page.locator('#preview-thread-step').click();
        await page.locator('#cancel-thread-step').click();
        assert.match(await page.locator('#step-status').innerText(), /Canceled/);
        assert.equal(await page.locator('#download-thread-step').isEnabled(), false);
        assert.equal(await page.locator('#preview-thread-step').isEnabled(), true);
        await page.locator('#preview-thread-step').click();
        // The part remains editable while an inline export is running.
        await page.locator('#spec-family').selectOption('unc');
        assert.equal(await page.locator('#cancel-thread-step').isVisible(), false);
        assert.match(await page.locator('#step-status').innerText(), /changed/);
        await page.waitForFunction(() => document.getElementById('spec-output').dataset.stale === 'false');
        await page.locator('#step-length').fill('5');
        await page.route('**/thread-cad-worker.js?*', (route) => route.abort());
        await page.locator('#preview-thread-step').click();
        await page.waitForFunction(() => document.getElementById('step-status').textContent.includes('Could not load'));
        assert.equal(await page.locator('#preview-thread-step').isEnabled(), true);
        await page.unroute('**/thread-cad-worker.js?*');
        const retry = page.waitForEvent('download');
        await page.locator('#preview-thread-step').click();
        await page.locator('#download-thread-step').click();
        assert.match((await retry).suggestedFilename(), /\.step$/);

        await boot(url + '?section=explore&spec_family=unf&spec_size=1%2F4-28+UNF');
        assert.equal(await page.locator('#tab-specify').getAttribute('aria-selected'), 'true');
        assert.equal(await page.locator('#spec-feature').inputValue(), 'nominal');
        await boot(url + '?task=find&find_version=1&find_diameter=nan');
        assert.equal(await page.locator('#find-error').isVisible(), true);
        assert.match(await page.locator('#find-error').innerText(), /Saved measurements/);
        await boot(url + '?task=find&find_version=77');
        assert.match(await page.locator('#find-error').innerText(), /Unsupported saved Find version/);
        await boot(url);
        await page.locator('#tab-find').click();
        await page.locator('#find-example').click();
        await page.locator('.candidate-select').first().click();
        for (const theme of ['light', 'dark']) {
            await page.setViewportSize({ width: 320, height: 800 });
            await page.evaluate((theme) => document.body.dataset.theme = theme, theme);
            assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
            await page.locator('#find-more > summary').click();
            await page.locator('[data-help-for="find-pitch-uncertainty"]').click();
            assert.equal(await page.locator('#find-pitch-uncertainty-tooltip').isVisible(), true);
            await page.keyboard.press('Escape');
            await page.locator('#find-more > summary').click();
            await page.screenshot({ path: `/private/tmp/thread-find-${theme}-mobile.png`, fullPage: true, animations: 'disabled' });
        }
        await page.setViewportSize({ width: 1280, height: 1000 });
        await page.evaluate(() => document.body.dataset.theme = 'light');
        await page.screenshot({ path: '/private/tmp/thread-find-desktop.png', fullPage: true, animations: 'disabled' });
        // Simulate a static host under a GitHub-Pages-style path prefix. No
        // special headers or API server: each request maps to an existing file.
        await page.route('**/static-mirror/**', async (route) => {
            const mapped = route.request().url().replace('/static-mirror/', '/');
            await route.fulfill({ response: await route.fetch({ url: mapped }) });
        });
        await boot(url.replace('/tools/', '/static-mirror/tools/'));
        assert.equal(await page.evaluate(() => crossOriginIsolated), false);
        await page.locator('#open-step').click();
        await page.locator('#step-length').fill('5');
        await page.locator('#preview-thread-step').click();
        const subpathDownload = page.waitForEvent('download');
        await page.locator('#download-thread-step').click();
        assert.match((await subpathDownload).suggestedFilename(), /\.step$/);
        assert.ok(requests.some((request) => request.includes('/static-mirror/') && request.endsWith('.wasm')));
        assert.ok(requests.filter((request) => /replicad|thread-cad-worker/.test(request)).every((request) => new URL(request).origin === new URL(url).origin));
        assert.deepEqual(errors, []);
        console.log('PASS Find state/units, PDF physical scale, lazy STEP, cancel/stale protection, legacy links, 320px themes and help.');
    } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exit(1); });
