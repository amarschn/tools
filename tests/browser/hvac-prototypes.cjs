// Drives the three HVAC prototypes. Server on 8765:
//   NODE_PATH=$(pwd)/node_modules node tests/browser/hvac-prototypes.cjs [screenshot-dir]
const { chromium } = require('playwright');
const assert = require('assert');
const path = require('path');
const BASE = process.env.BASE_URL || 'http://localhost:8765/tools/hvac-load-calculator/prototypes';
const shots = process.argv[2];

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  async function open(file, options = {}) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 950 }, ...options });
    await context.route(/google-analytics|googletagmanager/, (r) => r.abort());
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(`${file}: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push(`${file}: ${m.text()}`); });
    await page.goto(`${BASE}/${file}`);
    await page.waitForSelector('#p-loading.done', { state: 'attached', timeout: 120000 });
    await page.addStyleTag({ content: '*{animation:none!important;transition:none!important}' });
    await page.waitForTimeout(700);
    return page;
  }
  const shot = async (page, name, fullPage = true) => { if (shots) await page.screenshot({ path: path.join(shots, `${name}.png`), fullPage }); };
  const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const setField = async (page, id, value) => {
    await page.evaluate(([i, v]) => {
      const el = document.getElementById(i); el.closest('details').open = true; el.value = v;
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, [id, value]);
    await page.waitForTimeout(250);
  };

  // A: cutaway
  const a = await open('option-a-cutaway.html');
  assert((await a.locator('#stage polygon').count()) > 3, 'arrows drawn');
  await shot(a, 'a1-winter');
  await a.click('[data-sys="heat_pump"]');
  await a.click('#s-summer');
  await a.waitForTimeout(300);
  await shot(a, 'a2-summer-hp');
  const before = await a.locator('#stage').innerHTML();
  await a.fill('#hour', '10');
  await a.locator('#hour').dispatchEvent('input');
  assert.notStrictEqual(before, await a.locator('#stage').innerHTML(), 'hour changes the drawing');
  await a.click('#stage [data-go="cool-windows"] polygon');
  await a.waitForSelector('#drill .vars mjx-container', { timeout: 30000 });
  assert((await a.textContent('#drill')).includes('With your numbers'));
  await shot(a, 'a3-drill');
  await setField(a, 'p-stories', '2');
  await setField(a, 'p-floor', 'basement_conditioned');
  await a.click('[data-sys="ductless"]');
  await a.click('#s-winter');
  await a.waitForTimeout(300);
  await shot(a, 'a4-two-story-basement-ductless');
  await a.click('#p-theme');
  await a.waitForTimeout(300);
  await shot(a, 'a5-dark');
  await a.context().close();

  // B: floor plan
  const b = await open('option-b-floorplan.html');
  assert((await b.locator('#plan .room-rect').count()) >= 5, 'rooms drawn');
  await shot(b, 'b1-heating');
  // The starter layout must tile: rooms equal the footprint, with no gaps or overlaps.
  const tiled = await b.evaluate(() => Proto.state.rooms.reduce((sum, r) => sum + r.area, 0));
  assert(Math.abs(tiled - 2000) <= 40, 'starter rooms fill the floor area: ' + tiled);
  assert(!(await b.locator('#plan-note').textContent()).includes('overlap'), 'starter rooms do not overlap');
  const heatBefore = await b.evaluate(() => Proto.lastResult.heating_total);
  const box = await b.locator('#plan .room-rect').first().boundingBox();
  await b.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await b.mouse.down();
  await b.mouse.up();
  const handle = await b.locator('#plan .handle').boundingBox();
  await b.mouse.move(handle.x + 9, handle.y + 9);
  await b.mouse.down();
  await b.mouse.move(handle.x + 50, handle.y + 50, { steps: 5 });
  await b.mouse.up();
  await b.waitForTimeout(300);
  const heatAfter = await b.evaluate(() => Proto.lastResult.heating_total);
  assert.notStrictEqual(heatBefore, heatAfter, 'resizing a room changes the load');
  await b.click('[data-mode="hour"]');
  await b.waitForTimeout(300);
  await shot(b, 'b2-by-hour');
  await b.click('#room-panel [data-node="room-walls"]');
  await b.waitForSelector('#room-detail mjx-container', { timeout: 30000 });
  await shot(b, 'b3-room-math');
  await b.click('#p-theme');
  await b.click('[data-mode="cooling"]');
  await b.waitForTimeout(300);
  await shot(b, 'b4-dark');
  await b.context().close();

  // C: sizing board
  const c = await open('option-c-sizing-board.html');
  assert(await c.locator('#hp-card').evaluate((el) => el.hidden), 'no heat pump chart for a furnace system');
  await shot(c, 'c1-furnace');
  await c.click('[data-sys="heat_pump"]');
  await c.waitForTimeout(400);
  assert(!(await c.locator('#hp-card').evaluate((el) => el.hidden)), 'heat pump chart appears');
  await shot(c, 'c2-heat-pump');
  await c.click('#b-cool [data-open="cool-windows"] rect');
  await c.waitForSelector('#tree [data-toggle="cool-windows"][aria-expanded="true"]', { timeout: 15000 });
  await c.waitForTimeout(800);
  await shot(c, 'c3-tree');
  await c.click('#p-theme');
  await c.waitForTimeout(400);
  await shot(c, 'c4-dark', false);
  await c.context().close();

  // Phones: no sideways page scroll.
  for (const file of ['option-a-cutaway.html', 'option-b-floorplan.html', 'option-c-sizing-board.html']) {
    const m = await open(file, { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
    assert((await overflow(m)) <= 1, `${file} overflows on a phone by ${await overflow(m)}px`);
    await shot(m, `phone-${file.slice(7, 8)}`, false);
    await m.context().close();
  }

  assert.deepStrictEqual(errors, [], 'no page errors');
  await browser.close();
  console.log('PASS');
})().catch((e) => { console.error('FAIL', e); process.exit(1); });
