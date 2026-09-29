/* Real browser kernel smoke test; requires the repository served on port 8148. */
const { chromium } = require('/opt/homebrew/lib/node_modules/@playwright/test');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const assert = require('node:assert/strict');

(async () => {
    const browser = await chromium.launch({ headless: true });
    try {
        const page = await browser.newPage();
        page.on('console', (message) => console.log(message.text()));
        await page.goto('http://127.0.0.1:8148/tools/thread-visualizer-sizer/');
        const cases = [
            ['metric', 'M10x1.5', 'external', 'RH', 6],
            ['metric', 'M10x1.5', 'internal', 'RH', 6],
            ['metric', 'M10x1.5', 'external', 'LH', 20],
            ['metric', 'M10x1.5', 'internal', 'LH', 20],
            ['metric', 'M2x0.4', 'external', 'RH', 2],
            ['metric', 'M4x0.5', 'external', 'RH', 10],
            ['unc', '1/4-20 UNC', 'external', 'LH', 6.35],
            ['unc', '1/4-20 UNC', 'internal', 'RH', 6.35],
            ['unef', '1/4-32 UNEF', 'internal', 'LH', 4],
            ['unc', '2-4.5 UNC', 'external', 'RH', 25],
            ['metric', 'M10x1.5', 'external', 'RH', 6, { ends: 'start', chamfer_angle: 30 }],
            ['metric', 'M10x1.5', 'internal', 'LH', 6, { ends: 'end', chamfer_angle: 60, chamfer_depth: .7 }],
            ['metric', 'M10x1.5', 'external', 'LH', 1.5, { end_style: 'square' }],
            ['unc', '1/4-20 UNC', 'internal', 'RH', 6.35, { end_style: 'square' }],
        ];
        for (const [family, size, specimen, hand, length, ends = {}] of cases) {
            const model = JSON.parse(execFileSync('python3.13', ['-c',
                `import json; from pycalcs.thread_models import step_model; print(json.dumps(step_model(json.dumps(${JSON.stringify({family, size, specimen, hand, length, ...ends})}))))`
            ], { encoding: 'utf8' }));
            const result = await page.evaluate((model) => new Promise((resolve, reject) => {
                const worker = window.cadTestWorker ||= new Worker('thread-cad-worker.js', { type: 'module' });
                const timeout = setTimeout(() => { worker.terminate(); reject(new Error('CAD timeout')); }, 90000);
                worker.onerror = (event) => { clearTimeout(timeout); worker.terminate(); reject(new Error(event.message)); };
                worker.onmessage = async ({ data }) => {
                    if (data.stage) { console.log(data.stage); return; }
                    clearTimeout(timeout);
                    window.cadTestJobs = (window.cadTestJobs || 0) + 1;
                    if (window.cadTestJobs % 3 === 0 || data.error) { worker.terminate(); window.cadTestWorker = null; }
                    resolve({ ...data, text: data.blob ? await data.blob.text() : null, blob: undefined });
                };
                worker.postMessage({ id: 1, model, verify: true });
            }), model);
            console.log(specimen, JSON.stringify({ ...result, text: result.text?.slice(0, 150) }));
            assert.ok(!result.error, result.error);
            assert.ok(result.verification.valid);
            assert.ok(Math.abs(result.volume - result.verification.volume) / result.volume < 1e-5);
            assert.ok(Math.abs(result.volume / model.expected_volume_mm3 - 1) < 1e-4);
            const radius = (model.specimen === 'internal' ? model.body_diameter_mm : model.major_diameter_mm) / 2;
            const expectedBounds = [[-radius, -radius, 0], [radius, radius, model.length_mm]];
            result.verification.bounds.forEach((point, end) => point.forEach((value, axis) => assert.ok(Math.abs(value - expectedBounds[end][axis]) < .005, 'Physical bounding dimensions')));
            assert.match(result.text, /MANIFOLD_SOLID_BREP/);
            assert.match(result.text, /SI_UNIT\(.MILLI.,.METRE.\)/);
            assert.ok(result.text.replace(/[\r\n]/g, '').includes(model.step_name), 'Embedded STEP product name (ignoring physical line wrapping)');
            const stem = '/private/tmp/thread-' + `${size}-${specimen}-${hand}-${model.end_style}-${model.ends}`.replace(/[^a-zA-Z0-9._-]/g, '_');
            fs.writeFileSync(stem + '.step', result.text);
            fs.writeFileSync(stem + '.json', JSON.stringify(model));
            const independent = execFileSync('python3.13', ['tests/browser/validate_thread_step.py', stem + '.step', stem + '.json'], { encoding: 'utf8' });
            console.log(size, specimen, hand, independent.trim());
        }
    } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exit(1); });
