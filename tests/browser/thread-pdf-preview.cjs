/* Real generated-PDF preview, selection, lifecycle and physical-scale regression. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/opt/homebrew/lib/node_modules/@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { execFileSync } = require('node:child_process');
const url = process.env.THREAD_TOOL_URL || 'http://127.0.0.1:8148/tools/thread-visualizer-sizer/';
const records = JSON.parse(execFileSync(process.env.PYTHON || 'python3.13', ['-c',
    'import json; from pycalcs.thread_models import comparison_records; print(json.dumps(comparison_records()))'], { encoding: 'utf8' }));

(async () => {
    const browser = await chromium.launch({ headless: true });
    try {
        const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, serviceWorkers: 'block' });
        page.setDefaultTimeout(15000);
        const errors = [], requests = [];
        page.on('pageerror', (error) => errors.push(error.message));
        page.on('request', (request) => requests.push(request.url()));
        const preview = async () => {
            await page.locator('#preview-thread-pdf').click();
            await page.waitForFunction(() => !document.getElementById('download-thread-pdf').disabled);
        };
        const stale = async () => {
            assert.equal(await page.locator('#download-thread-pdf').isDisabled(), true);
            assert.equal(await page.locator('#print-preview').isVisible(), false);
            assert.equal(await page.locator('#print-thread-pdf').getAttribute('href'), null);
        };
        const openAdd = async () => {
            if (!await page.locator('#print-add-options').evaluate((el) => el.open)) await page.locator('#print-add-options > summary').click();
        };
        const add = async (designation) => {
            await openAdd();
            await page.locator('#print-search').fill(designation);
            await page.locator('#print-add-list .print-choice').filter({ hasText: designation }).first().locator('input').click();
            assert.ok((await page.locator('#print-candidate-list .print-choice span').allTextContents()).some((name) => name.startsWith(designation)));
        };
        await page.goto(url);
        await page.locator('#tool-main[data-boot-state="ready"]').waitFor({ timeout: 60000 });
        assert.equal(await page.locator('h1').innerText(), 'Thread Calculator & Identifier');
        assert.equal(await page.title(), 'Thread Calculator & Identifier | Metric & Inch Threads');
        assert.doesNotMatch(await page.locator('meta[name="description"]').getAttribute('content'), /\.\.\.$/);
        assert.equal(requests.some((path) => /thread-print\.js|thread-pdf-preview|pdfjs-dist|pdf-lib|thread-cad|replicad/.test(path)), false);
        await page.locator('#thread-references').click();
        for (const reference of ['ISO 68-1', 'ISO 724', 'ISO 261', 'ISO 965-1', 'ASME B1.1', 'ASME B1.20.1', 'ASME B1.20.3', 'ISO 7-1', 'ISO 228-1', 'VDI 2230']) {
            assert.ok((await page.locator('#standards-coverage').innerText()).includes(reference), reference);
        }
        await page.locator('#thread-references').click();
        await page.locator('#tab-find').click();
        await page.locator('#find-pitch').fill('1.5');
        await page.locator('#find-update').click();
        await page.locator('#open-print').click();
        assert.equal(await page.locator('#print-candidate-list input:checked').count(), 4);
        const names = await page.locator('#print-candidate-list .print-choice span').allTextContents();
        assert.equal(new Set(names).size, 4, 'Same-pitch candidates stay distinct');
        assert.ok(names.every((name) => name.includes('1.5')));
        await stale();
        assert.equal(requests.some((path) => /pdfjs-dist|pdf-lib/.test(path)), false, 'Opening choices is still lightweight');

        // A failed transitive import must be retryable in the same page.
        await page.route('**/pdf.min.mjs*', (route) => route.abort());
        await page.locator('#preview-thread-pdf').click();
        await page.waitForFunction(() => document.getElementById('print-status').textContent.includes('Could not preview'));
        await stale();
        assert.equal(await page.locator('#preview-thread-pdf').isEnabled(), true);
        await page.unroute('**/pdf.min.mjs*');
        await preview();
        for (const name of names) assert.ok((await page.locator('#print-page-description').innerText()).includes(name));
        assert.match(await page.locator('#print-canvas').getAttribute('aria-label'), /NOMINAL EXTERNAL MAJOR/);
        assert.equal(await page.locator('#print-canvas').evaluate((canvas) => {
            const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
            return pixels.some((value, index) => index % 4 !== 3 && value < 128);
        }), true, 'The actual PDF has been rendered');
        const previewBytes = await page.evaluate(async () => Array.from(new Uint8Array(await (await fetch(document.getElementById('print-thread-pdf').href)).arrayBuffer())));
        const downloadEvent = page.waitForEvent('download');
        await page.locator('#download-thread-pdf').click();
        const download = await downloadEvent;
        const filename = '/private/tmp/thread-selected-sizes-preview.pdf';
        await download.saveAs(filename);
        assert.deepEqual(fs.readFileSync(filename), Buffer.from(previewBytes), 'Download uses the exact previewed bytes');
        await page.locator('#print-preview').screenshot({ path: '/private/tmp/thread-pdf-preview-desktop.png' });
        await page.locator('#print-options').screenshot({ path: '/private/tmp/thread-print-inline-desktop.png' });

        // Close to return to measurements. The old blob is already discarded.
        await page.locator('#open-print').click();
        await page.locator('#find-pitch').fill('1.25');
        await stale();
        await page.locator('#find-update').click();
        await page.locator('#find-side').selectOption('unsure');
        await page.locator('#find-update').click();
        await page.locator('#open-print').click();
        assert.equal(await page.locator('#print-side').isVisible(), true);
        assert.equal(await page.locator('#preview-thread-pdf').isDisabled(), true);
        await page.locator('#print-side').selectOption('internal');
        await preview();
        assert.match(await page.locator('#print-canvas').getAttribute('aria-label'), /BASIC INTERNAL MINOR/);
        await page.locator('#print-paper').selectOption('a4');
        await stale();

        // No result is not an implicit choice of diameter or a silently empty PDF.
        await page.locator('#open-print').click();
        await page.locator('#find-side').selectOption('external');
        await page.locator('#find-diameter').fill('999');
        await page.locator('#find-update').click();
        await page.locator('#open-print').click();
        assert.equal(await page.locator('#print-candidate-list input:checked').count(), 0);
        assert.equal(await page.locator('#preview-thread-pdf').isDisabled(), true);
        await add('1/16 NPT');
        await preview();
        assert.match(await page.locator('#print-canvas').getAttribute('aria-label'), /PITCH ONLY/);
        assert.doesNotMatch(await page.locator('#print-canvas').getAttribute('aria-label'), /NOMINAL EXTERNAL MAJOR/);
        await page.locator('#print-candidate-list input:checked').click();
        await stale();

        // Larger sizes paginate without scaling; all selections remain editable.
        for (const row of records.filter((row) => row.model).slice(-16)) await add(row.designation);
        assert.equal(await page.locator('#print-candidate-list input:checked').count(), 16);
        assert.equal(await page.evaluate(() => {
            const ids = [...document.querySelectorAll('[id]')].map((node) => node.id);
            return ids.length === new Set(ids).size && [...document.querySelectorAll('#print-candidate-list input')].every((input) =>
                input.labels.length && document.querySelector(`[data-help-for="${input.id}"]`));
        }), true, 'Dynamic choices keep unique IDs, labels and help');
        await page.locator('#print-search').fill('M10x1.5');
        await page.locator('#print-add-list input').first().click();
        assert.equal(await page.locator('#print-candidate-list input:checked').count(), 16);
        assert.match(await page.locator('#print-status').innerText(), /up to 16/);
        await page.locator('#print-add-options > summary').click();
        await preview();
        assert.equal(await page.locator('#print-next').isEnabled(), true);
        await page.locator('#print-next').click();
        await page.waitForFunction(() => document.getElementById('print-canvas').dataset.page === '2');
        assert.equal(await page.locator('#print-previous').isEnabled(), true);
        await page.locator('#print-previous').click();
        await page.waitForFunction(() => document.getElementById('print-canvas').dataset.page === '1');

        for (const theme of ['light', 'dark']) {
            await page.setViewportSize({ width: 320, height: 800 });
            await page.evaluate((theme) => document.body.dataset.theme = theme, theme);
            await page.waitForTimeout(250);
            assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, theme + ' mobile overflow');
            const firstId = await page.locator('#print-candidate-list input').first().getAttribute('id');
            await page.locator(`[data-help-for="${firstId}"]`).click();
            assert.equal(await page.locator('#' + firstId + '-tooltip').isVisible(), true);
            await page.keyboard.press('Escape');
            await page.locator('#print-preview').screenshot({ path: `/private/tmp/thread-pdf-preview-${theme}-mobile.png` });
        }
        await page.locator('#close-thread-pdf').click();
        await stale();
        await page.locator('#print-scope').selectOption('common');
        await preview();
        assert.match(await page.locator('#print-canvas').getAttribute('aria-label'), /THREAD PITCH REFERENCE/);
        assert.equal(await page.locator('#print-size-options').isVisible(), false);
        assert.equal(await page.locator('#print-next').isEnabled(), true);

        // Generate the complete catalog in both bases and paper formats, then
        // inspect PDF vector coordinates independently of the layout manifest.
        const scale = await page.evaluate(async (records) => {
            const { buildComparisonPDF, mmToPoints } = await import(window.threadAssetUrl('thread-print.js'));
            const lib = await import('./vendor/pdf-lib-1.17.1/pdf-lib.esm.min.js');
            const reports = [];
            for (const paper of ['letter', 'a4']) for (const side of ['external', 'internal']) {
                const { bytes, manifest } = await buildComparisonPDF(records, { paper, side });
                const doc = await lib.PDFDocument.load(bytes);
                reports.push(...doc.getPages().map((page, index) => {
                    const text = page.node.Contents().asArray().map((ref) => new TextDecoder().decode(lib.decodePDFRawStream(doc.context.lookup(ref)).decode())).join('\n');
                    const lines = [...text.matchAll(/(-?[\d.]+) (-?[\d.]+) m\s+(-?[\d.]+) (-?[\d.]+) l/g)].map((m) => m.slice(1).map(Number));
                    const close = (a, b) => Math.abs(a - b) < 1e-8;
                    const horizontal = (mm) => lines.some(([x, y, a, b]) => close(Math.abs(a - x), mmToPoints(mm)) && close(y, b));
                    const rows = manifest.pages[index].strips;
                    return { paper, side, rows: rows.length,
                        scaledDiameter: rows.some((row) => row.diameter_mm && !horizontal(row.diameter_mm)),
                        calibration: horizontal(100) && horizontal(25.4) && lines.some(([x, y, a, b]) => close(Math.abs(y - b), mmToPoints(100)) && close(x, a)),
                        clipped: lines.some(([x, y, a, b]) => Math.min(x, y, a, b) < 0 || Math.max(x, a) > page.getWidth() || Math.max(y, b) > page.getHeight()),
                        overlapping: rows.some((row, i) => row.bounds_mm[3] > manifest.pages[index].height_mm - 65 || (i && row.bounds_mm[1] < rows[i - 1].bounds_mm[3])),
                    };
                }));
            }
            return reports;
        }, records);
        assert.ok(scale.length > 20);
        assert.ok(scale.every((row) => row.calibration && !row.scaledDiameter && !row.clipped && !row.overlapping), JSON.stringify(scale.filter((row) => !row.calibration || row.scaledDiameter || row.clipped || row.overlapping)));
        assert.equal(scale.reduce((sum, row) => sum + row.rows, 0), 4 * records.length);

        // Closing the panel during a delayed import must discard the pending job.
        await page.reload();
        await page.locator('#tool-main[data-boot-state="ready"]').waitFor({ timeout: 60000 });
        await page.locator('#open-print').click();
        let release;
        const intercepted = new Promise((resolve) => {
            page.route('**/thread-pdf-preview.js?*', (route) => { release = () => route.continue(); resolve(); });
        });
        await page.locator('#preview-thread-pdf').click();
        await intercepted;
        assert.equal(await page.locator('#preview-thread-pdf').isDisabled(), true);
        await page.locator('#open-print').click();
        await stale();
        const loaded = page.waitForResponse((response) => response.url().includes('/thread-pdf-preview.js?'));
        await release();
        await loaded;
        await page.unroute('**/thread-pdf-preview.js?*');
        await page.waitForTimeout(200);
        await stale();
        await page.locator('#open-print').click();
        await preview();
        assert.equal(requests.some((path) => /thread-cad|replicad|opencascade/.test(path)), false);
        assert.deepEqual(errors, []);
        console.log(`PASS PDF preview/download byte identity, same-pitch size selection, lazy/retryable renderer, stale protection, unknown/pipe basis, pagination, mobile help/themes, standards, and ${scale.length} physical-scale pages.`);
    } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exit(1); });
