/* Startup/interaction profile, including returning visitors with a service worker. */
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/opt/homebrew/lib/node_modules/@playwright/test');
const url = process.env.THREAD_TOOL_URL || 'http://127.0.0.1:8148/tools/thread-visualizer-sizer/';

// Keep the cache exception narrow: mutable data and unpinned CDN versions
// must retain their existing revalidation policy, including on the mirror.
const pinned = runInNewContext(readFileSync('service-worker.js', 'utf8') + '\nisVersionedCalculationAsset;', {
    URL, self: { location: { origin: new URL(url).origin }, addEventListener() {} },
});
assert.equal(pinned('https://cdn.jsdelivr.net/pyodide/v0.25.1/full/pyodide.js'), true);
for (const path of ['latest', 'v0.25']) assert.equal(pinned(`https://cdn.jsdelivr.net/pyodide/${path}/full/pyodide.js`), false);
for (const prefix of ['/', '/tools/']) {
    const path = new URL(prefix + 'pycalcs/thread_models.py', url);
    assert.equal(pinned(path.href), false);
    path.searchParams.set('v', 'thread-0123456789abcdef');
    assert.equal(pinned(path.href), true);
}
for (const path of ['catalog.json', 'data/homepage-tool-meta.json', 'pycalcs/fluids.py']) {
    assert.equal(pinned(new URL('/' + path + '?v=thread-0123456789abcdef', url).href), false);
}

(async () => {
    const browser = await chromium.launch({ headless: true });
    try {
        const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
        const page = await context.newPage();
        const errors = [];
        const delayedRequests = [];
        page.on('pageerror', (error) => errors.push(error.message));
        await page.addInitScript(() => {
            window.threadTimings = [];
            window.threadLongTasks = [];
            new PerformanceObserver((list) => window.threadLongTasks.push(...list.getEntries().map(({ startTime, duration }) => ({ startTime, duration })))).observe({ type: 'longtask', buffered: true });
            for (const name of ['threadFinder', 'threadExports', 'threadSpecification', 'threadFieldHelp']) {
                let instance;
                Object.defineProperty(window, name, {
                    configurable: true,
                    get: () => instance,
                    set(value) {
                        instance = value;
                        for (const method of ['initialize', 'refresh', 'update', 'present', 'renderCandidate', 'setSpecification']) {
                            if (typeof value[method] !== 'function') continue;
                            const original = value[method];
                            value[method] = function (...args) {
                                const start = performance.now();
                                try { return original.apply(this, args); }
                                finally { window.threadTimings.push({ name: `${name}.${method}`, start, duration: performance.now() - start }); }
                            };
                        }
                    },
                });
            }
        });
        const profile = async (label) => {
            await page.goto(url, { waitUntil: 'domcontentloaded' });
            await page.locator('#tool-main[data-boot-state="ready"]').waitFor({ timeout: 120000 });
            const startup = await page.evaluate(() => ({
                readyMs: performance.getEntriesByName('thread:ready')[0]?.startTime || performance.now(),
                work: window.threadTimings,
                longTasks: window.threadLongTasks,
                resources: performance.getEntriesByType('resource').filter((entry) => !/google|analytics/.test(entry.name)).map(({ name, startTime, duration, transferSize }) => ({ name, startTime, duration, transferSize })),
            }));
            console.log(label, JSON.stringify(process.env.THREAD_PROFILE_VERBOSE ? startup : {
                readyMs: Math.round(startup.readyMs),
                initializeMs: Math.round(startup.work.filter((entry) => entry.name.endsWith('.initialize')).reduce((sum, entry) => sum + entry.duration, 0)),
                longTasks: startup.longTasks.length,
            }));
            await page.locator('#tab-find').click();
            assert.equal(await page.locator('#tab-find').getAttribute('aria-selected'), 'true');
            assert.equal(await page.locator('#find-form').isVisible(), true);
            assert.notEqual(await page.locator('#tab-find').evaluate((el) => getComputedStyle(el).backgroundColor),
                await page.locator('#tab-specify').evaluate((el) => getComputedStyle(el).backgroundColor));
            await page.locator('#find-example').click();
            await page.locator('#find-candidates .candidate-select').first().waitFor();
            const interaction = await page.evaluate((count) => ({ timings: window.threadTimings.slice(count), section: window.threadSpecification.section }), startup.work.length);
            if (process.env.THREAD_PROFILE_VERBOSE) console.log(label + ' interactions', JSON.stringify(interaction));
            const cadRequests = startup.resources.filter(({ name }) => /replicad|opencascade|thread-cad|thread-print|pdf-lib/.test(name));
            assert.deepEqual(cadRequests, [], 'Export runtimes must not load at startup.');
            const modules = startup.resources.filter(({ name }) => /\/pycalcs\/.*\.py/.test(name));
            assert.equal(modules.length, 4);
            assert.ok(Math.max(...modules.map((entry) => entry.startTime)) < Math.min(...modules.map((entry) => entry.startTime + entry.duration)),
                'All Python downloads start before the first one finishes.');
            const version = await page.locator('meta[name="thread-asset-version"]').getAttribute('content');
            assert.ok(modules.every(({ name }) => new URL(name).searchParams.get('v') === version));
            return startup;
        };
        await profile('cold');
        await page.evaluate(() => navigator.serviceWorker.ready);
        await profile('warm');
        // A returning browser can hold the pre-Find controller under this
        // unversioned key. Model its old accepted-tab list, not a fresh context.
        const legacy = readFileSync('tools/thread-visualizer-sizer/thread-specification.js', 'utf8')
            .replace("['specify', 'load', 'find'].includes(next)", "['specify', 'load', 'explore'].includes(next)");
        await page.evaluate(async ({ url, legacy }) => {
            const cache = await caches.open('tt-cache-v3');
            await cache.put(new URL('thread-specification.js', url), new Response(legacy, { headers: { 'Content-Type': 'application/javascript' } }));
        }, { url, legacy });
        const cachedState = await page.evaluate(async (url) => ({
            controller: navigator.serviceWorker.controller?.scriptURL,
            sourceHasLegacyTabs: (await (await fetch(new URL('thread-specification.js', url))).text()).includes("['specify', 'load', 'explore'].includes(next)"),
            keys: await caches.keys(),
        }), url);
        assert.ok(cachedState.controller, 'Exercise the installed service worker, not just the HTTP cache.');
        assert.equal(cachedState.sourceHasLegacyTabs, true, 'The incompatible controller really is cached.');
        await page.goto(url, { waitUntil: 'domcontentloaded' });
        await page.locator('#tool-main[data-boot-state="ready"]').waitFor({ timeout: 120000 });
        await page.locator('#tab-find').click();
        assert.deepEqual(await page.evaluate(() => ({
            section: window.threadSpecification.section,
            selected: document.getElementById('tab-find').getAttribute('aria-selected'),
            hidden: document.getElementById('find-form').hidden,
        })), { section: 'find', selected: 'true', hidden: false });
        console.log('Find works with the incompatible unversioned controller still cached.');
        await page.evaluate(async (url) => {
            const cache = await caches.open('tt-cache-v3');
            await cache.delete(new URL('thread-specification.js', url));
        }, url);
        // Delay revalidation, not cached responses, to model a weak connection
        // or a browser waking up with stalled network requests.
        await context.route(/cdn\.jsdelivr\.net\/pyodide\/|\/pycalcs\/.*\.py/, async (route) => {
            delayedRequests.push(route.request().url());
            await new Promise((resolve) => setTimeout(resolve, 3000));
            await route.continue().catch(() => {});
        });
        await profile('warm, slow network');
        assert.deepEqual(delayedRequests, [], 'A warm calculation must not wait for network revalidation.');
        // Existing cached calculations must also survive a disconnected wake.
        await context.setOffline(true);
        await profile('warm, offline');
        await context.setOffline(false);
        assert.deepEqual(errors, []);
    } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exit(1); });
