// Drives the HVAC load calculator with real pointer input. Server on 8765:
//   NODE_PATH=$(pwd)/node_modules node tests/browser/hvac-load-calculator.cjs [screenshot-dir]
// Set BASE_URL=https://transparent.tools/tools/hvac-load-calculator to check production.
const { chromium } = require('playwright');
const assert = require('assert');
const path = require('path');
const BASE = process.env.BASE_URL || 'http://localhost:8765/tools/hvac-load-calculator';
const shots = process.argv[2];

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  async function open(file, options = {}) {
    const context = await browser.newContext({ viewport: { width: 1500, height: 980 }, ...options });
    await context.route(/google-analytics|googletagmanager/, (r) => r.abort());
    const page = await context.newPage();
    page.on('pageerror', (e) => errors.push(`${file}: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push(`${file}: ${m.text()}`); });
    await page.goto(`${BASE}/${file}`);
    await page.waitForSelector('#p-loading.done', { state: 'attached', timeout: 120000 });
    await page.addStyleTag({ content: '*{animation:none!important;transition:none!important;scroll-behavior:auto!important}' });
    await page.waitForTimeout(400);
    return page;
  }
  const shot = async (page, name, fullPage = true) => { if (shots) { await page.waitForTimeout(250); await page.screenshot({ path: path.join(shots, `${name}.png`), fullPage }); } };
  const valid = async (page) => {
    const error = await page.evaluate(() => Core.error);
    assert(!error, `engine error: ${error}`);
    return page.evaluate(() => HouseModel.check(Core.model));
  };
  const heat = (page) => page.evaluate(() => Core.result.heating_total);
  async function dragOn(page, selector, dx, dy) {
    const box = await page.locator(selector).first().boundingBox();
    assert(box, `no element for ${selector}`);
    const x = box.x + box.width / 2; const y = box.y + box.height / 2;
    await page.mouse.move(x, y); await page.mouse.down();
    await page.mouse.move(x + dx, y + dy, { steps: 6 }); await page.mouse.up();
    await page.waitForTimeout(250);
  }
  const clickPlan = async (page, fx, fy) => {
    const box = await page.locator('#dwg-plan').boundingBox();
    const t = await page.evaluate(() => { const v = Core.view.lastTransform; const m = Core.model; return { ...v, w: m.w, d: m.d }; });
    const k = box.width / 620;
    const x = box.x + (t.ox + fx * t.w * t.scale) * k; const y = box.y + (t.oy + fy * t.d * t.scale) * k;
    await page.mouse.move(x, y); await page.waitForTimeout(80); await page.mouse.click(x, y); await page.waitForTimeout(200);
  };

  // ------------------------------------------------------------- D: guided build
  const d = await open('');
  // Search and accessibility basics on the live page.
  assert((await d.title()).includes('Manual J'), 'title names Manual J');
  assert((await d.textContent('h1')).includes('Manual J Alternative'));
  assert.strictEqual(await d.locator('#guide-cooling tbody tr').count(), 7, 'sizing guide table present');
  assert.strictEqual(await d.textContent('.site-nav .brand'), 'transparent.tools');
  assert(await d.locator('.nav-actions button', { hasText: 'Copy Link' }).count() === 1, 'copy link button present');
  const untipped = await d.evaluate(() => [...document.querySelectorAll('#step .fld')].filter((f) => !f.querySelector('.tip')).map((f) => f.querySelector('label').textContent));
  assert.deepStrictEqual(untipped, [], 'every input on step 1 has help');
  await shot(d, 'd1-box');
  assert.strictEqual(await d.locator('#dwg-plan .h-room').count(), 1, 'starts as one box');
  const boxBand = await d.evaluate(() => Core.band);
  assert(boxBand.spread && boxBand.heating_high > boxBand.heating_low * 1.8, 'the box has a wide range');

  // Step 2: drag every outside wall, including the two that move the origin.
  await d.click('[data-step="1"]');
  const m0 = await d.evaluate(() => ({ w: Core.model.w, d: Core.model.d }));
  await dragOn(d, '[data-shell="E"]', 60, 0);
  const m1 = await d.evaluate(() => ({ w: Core.model.w, d: Core.model.d }));
  assert(m1.w > m0.w, 'dragging the east wall out widens the house');
  await dragOn(d, '[data-shell="W"]', -40, 0);
  const m2 = await d.evaluate(() => ({ w: Core.model.w, d: Core.model.d }));
  assert(m2.w > m1.w, 'dragging the west wall out widens the house');
  await dragOn(d, '[data-shell="N"]', 0, 25);
  const m3 = await d.evaluate(() => Core.model.d);
  assert(m3 < m2.d, 'dragging the north wall in shortens the house');
  await dragOn(d, '[data-shell="S"]', 0, -600);
  assert.deepStrictEqual(await valid(d), [], 'shell drag keeps the model valid');
  assert((await d.evaluate(() => Core.model.d)) >= 10, 'a shell cannot collapse');
  // Back to an ordinary shape by typing it.
  for (const [id, v] of [['f-m_w', 50], ['f-m_d', 40]]) {
    await d.evaluate(([i, value]) => { const b = document.getElementById(i); b.value = value; b.dispatchEvent(new Event('change', { bubbles: true })); }, [id, v]);
    await d.waitForTimeout(150);
  }
  assert.deepStrictEqual(await d.evaluate(() => [Core.model.w, Core.model.d]), [50, 40], 'typed size wins');
  await d.waitForTimeout(200);
  await d.selectOption('#f-era', '1980s_90s');
  await d.waitForTimeout(500);
  const eraBand = await d.evaluate(() => Core.band);
  assert(!eraBand.spread, 'the era collapses the wide range');
  await shot(d, 'd2-shape');

  // Step 3: insulation changes the drawing and the load.
  await d.click('[data-step="2"]');
  const untipped3 = await d.evaluate(() => [...document.querySelectorAll('#step .fld')].filter((f) => !f.querySelector('.tip')).map((f) => f.querySelector('label').textContent));
  assert.deepStrictEqual(untipped3, [], 'every insulation input has help');
  const before = await heat(d);
  await d.selectOption('#f-wall_preset', '2x6_r21');
  await d.waitForTimeout(200);
  assert(await heat(d) < before, 'better walls lower the load');
  await d.evaluate(() => { const el = document.querySelector('.deeper'); el.open = true; });
  await d.fill('#f-cavity_r', '19'); await d.locator('#f-cavity_r').blur(); await d.waitForTimeout(250);
  assert(await d.evaluate(() => Proto.state.fields.layer_u > 0), 'layers calculate a U-factor');
  await shot(d, 'd3-insulation');

  // Step 4: add a window, drag it along the wall, resize it.
  await d.click('[data-step="3"]');
  const glass0 = await d.evaluate(() => HouseModel.glassArea(Core.model));
  // Click the middle of the widest free stretch of the north wall.
  const free = await d.evaluate(() => {
    const m = Core.model; const list = m.openings.filter((x) => x.level === 0 && x.side === 'N').sort((a, b) => a.pos - b.pos);
    let best = [0, 0]; let edge = 0;
    list.forEach((x) => { const a = x.pos - x.width / 2; if (a - edge > best[1] - best[0]) best = [edge, a]; edge = x.pos + x.width / 2; });
    if (m.w - edge > best[1] - best[0]) best = [edge, m.w];
    return (best[0] + best[1]) / 2 / m.w;
  });
  const countBefore = await d.evaluate(() => Core.model.openings.length);
  await clickPlan(d, free, 0);
  assert.strictEqual(await d.evaluate(() => Core.model.openings.length), countBefore + 1, 'clicking open wall adds a window');
  const op = await d.evaluate(() => { const o = Core.model.openings.find((x) => x.id === Core.view.selected.opening); return o && { pos: o.pos, side: o.side }; });
  assert(op && op.side === 'N', 'clicking the north wall adds a window there');
  // Slide toward whichever side has open wall; it must stop short of its neighbour.
  const room = await d.evaluate(() => {
    const o = Core.model.openings.find((x) => x.id === Core.view.selected.opening);
    const others = Core.model.openings.filter((x) => x !== o && x.level === o.level && x.side === o.side);
    const left = Math.max(0.25, ...others.filter((x) => x.pos < o.pos).map((x) => x.pos + x.width / 2 + 0.5));
    const right = Math.min(Core.model.w - 0.25, ...others.filter((x) => x.pos > o.pos).map((x) => x.pos - x.width / 2 - 0.5));
    return { left: o.pos - o.width / 2 - left, right: right - (o.pos + o.width / 2), scale: Core.view.lastTransform.scale };
  });
  const dir = room.right >= room.left ? 1 : -1;
  const box = await d.locator('#dwg-plan').boundingBox();
  const px = (ft) => ft * room.scale * box.width / 620;
  await dragOn(d, `[data-op="${await d.evaluate(() => Core.view.selected.opening)}"]`, dir * px(Math.max(room.right, room.left) + 20), 0);
  const moved = await d.evaluate(() => Core.model.openings.find((x) => x.id === Core.view.selected.opening).pos);
  assert(Math.max(room.right, room.left) < 0.5 || Math.sign(moved - op.pos) === dir, 'a window slides along its wall');
  assert.deepStrictEqual(await d.evaluate(() => HouseModel.check(Core.model)), [], 'a sliding window stops at its neighbour');
  // It now touches its neighbour on one side, so widen the other end.
  await dragOn(d, `[data-opend="${-dir}"]`, -dir * 40, 0);
  const wide = await d.evaluate(() => Core.model.openings.find((x) => x.id === Core.view.selected.opening));
  assert(wide.width > 4 || wide.width > op.width, 'an end handle widens a window: ' + JSON.stringify(wide));
  const count = await d.evaluate(() => Core.model.openings.length);
  await clickPlan(d, (wide.pos) / (await d.evaluate(() => Core.model.w)), 0);
  assert.strictEqual(await d.evaluate(() => Core.model.openings.length), count, 'clicking an existing window does not stack another on it');
  assert(await d.evaluate(() => Core.model.openings.every((o) => !o.assumed)), 'drawing a window replaces the guesses');
  assert.notStrictEqual(glass0, await d.evaluate(() => HouseModel.glassArea(Core.model)));
  await d.click('[data-season="summer"]');
  await shot(d, 'd4-windows');

  assert.deepStrictEqual(await valid(d), [], 'windows keep the model valid');
  // Step 5
  await d.click('[data-step="4"]');
  await d.selectOption('#f-duct_location', 'conditioned');
  await d.waitForTimeout(200);
  assert.strictEqual(await d.evaluate(() => Math.round(Core.result.heating.components.ducts)), 0, 'ducts inside lose nothing');
  await d.selectOption('#f-duct_location', 'attic');
  await d.waitForTimeout(300);
  await d.click('[data-season="winter"]');
  await shot(d, 'd5-air');

  // Step 6: walls move, rooms follow, and nothing can overlap.
  await d.click('[data-step="5"]');
  await d.click('[data-typical]');
  await d.waitForTimeout(300);
  assert((await d.locator('#dwg-plan [data-wall]').count()) >= 4, 'typical layout has walls');
  assert.deepStrictEqual(await valid(d), [], 'typical layout tiles');
  const area0 = await d.evaluate(() => HouseModel.area(Core.model));
  for (let i = 0; i < (await d.locator('#dwg-plan [data-wall]').count()); i++) {
    await dragOn(d, `#dwg-plan [data-wall="${i}"]`, 28, 28);
    assert.deepStrictEqual(await valid(d), [], `dragging wall ${i} keeps rooms tiled`);
  }
  assert.strictEqual(await d.evaluate(() => HouseModel.area(Core.model)), area0, 'moving walls keeps the floor area');
  // Extreme drag stops at the minimum room size.
  await dragOn(d, '#dwg-plan [data-wall="0"]', -900, -900);
  assert.deepStrictEqual(await valid(d), [], 'a wall cannot crush a room');
  // Split a room by clicking.
  const n0 = await d.evaluate(() => Core.model.levels[0].rooms.length);
  await d.click('[data-split]');
  await d.waitForTimeout(100);
  await clickPlan(d, 0.2, 0.25);
  assert.strictEqual(await d.evaluate(() => Core.model.levels[0].rooms.length), n0 + 1, 'clicking adds a wall');
  assert.deepStrictEqual(await valid(d), [], 'splitting keeps rooms tiled');
  await d.keyboard.press('Escape');
  await shot(d, 'd6-rooms');

  // Section follows the plan.
  const sec0 = await d.locator('#dwg-section').innerHTML();
  await dragOn(d, '[data-cut]', 80, 0);
  assert.notStrictEqual(sec0, await d.locator('#dwg-section').innerHTML(), 'moving the cut changes the section');
  await d.click('#dwg-cutdir'); await d.waitForTimeout(100);
  await d.click('[data-layout="axon"]'); await d.waitForTimeout(200);
  assert((await d.locator('#dwg-axon polygon').count()) > 8, '3D view draws');
  await shot(d, 'd7-axon');
  await d.click('[data-layout="both"]');

  // Step 7
  await d.click('[data-step="6"]');
  await d.click('[data-sys="heat_pump"]');
  await d.waitForTimeout(350);
  await shot(d, 'd8-system');

  // Step 8: the study runs real sweeps.
  await d.click('[data-step="7"]');
  await d.waitForSelector('.sweep svg', { timeout: 30000 });
  assert((await d.locator('.sweep').count()) >= 3, 'several sweeps');
  assert((await d.locator('.sweep-verdict').first().textContent()).length > 10, 'a sweep states what it means');
  const before2 = await d.locator('.sweep').count();
  await d.locator('.chip:not(.on)').first().click(); await d.waitForTimeout(400);
  assert.strictEqual(await d.locator('.sweep').count(), before2 + 1, 'choosing a variable adds a sweep');
  await d.click('#grid-run');
  await d.waitForSelector('#grid-out svg', { timeout: 60000 });
  assert((await d.locator('#grid-out').textContent()).includes('covers'), 'the grid reports coverage');
  await shot(d, 'd9-study');

  // Fuel bill check.
  await d.evaluate(() => { document.getElementById('bill').open = true; });
  await d.fill('#f-bill_usage', '160'); await d.locator('#f-bill_usage').blur(); await d.waitForTimeout(300);
  assert((await d.textContent('#bill-out')).includes('Your bill implies'), 'bill check reports');

  // Exports: CSV, and a saved house that reopens identically.
  await d.evaluate(() => { document.querySelectorAll('#step details').forEach((x) => { x.open = true; }); });
  const [csv] = await Promise.all([d.waitForEvent('download'), d.click('[data-export="csv"]')]);
  assert.strictEqual(csv.suggestedFilename(), 'hvac-load-calculation.csv');
  const [json] = await Promise.all([d.waitForEvent('download'), d.click('[data-export="json"]')]);
  const savedHeat = await heat(d);
  await d.evaluate(() => { Core.model = HouseModel.create({ area: 900 }); Core.update(); });
  await d.setInputFiles('#import-json', await json.path());
  await d.waitForTimeout(500);
  assert(Math.abs((await heat(d)) - savedHeat) < 1, 'a saved house reopens with the same load');

  // Share link: a fresh page restores the same house.
  await d.waitForTimeout(600);
  const share = await d.evaluate(() => window.UrlState.getShareUrl());
  assert(share.includes('model_json'), 'the share link carries the house');
  const again = await d.context().newPage();
  await again.goto(share);
  await again.waitForSelector('#p-loading.done', { state: 'attached', timeout: 120000 });
  await again.waitForTimeout(500);
  assert(Math.abs((await again.evaluate(() => Core.result.heating_total)) - savedHeat) < 1, 'the share link restores the same load');
  assert.deepStrictEqual(await again.evaluate(() => HouseModel.check(Core.model)), []);
  await again.close();

  // Settings: theme persists and inputs follow it.
  await d.click('#settings-button');
  await d.click('[data-theme-choice="dark"]');
  await d.click('#settings-close');
  assert.strictEqual(await d.evaluate(() => document.documentElement.dataset.theme), 'dark');
  assert.strictEqual(await d.evaluate(() => getComputedStyle(document.querySelector('#step input, #step select')).colorScheme), 'dark', 'native controls follow the theme');
  const contrast = await d.evaluate(() => {
    const lum = (c) => { const [r, g, b] = c.match(/[\d.]+/g).map(Number).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    const el = document.querySelector('#step input, #step select'); const s = getComputedStyle(el);
    const a = lum(s.color); const b = lum(s.backgroundColor); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  });
  assert(contrast > 4.5, 'dark mode input contrast ' + contrast);
  const copyLink = await d.locator('.nav-actions button', { hasText: 'Copy Link' });
  const linkContrast = await copyLink.evaluate((el) => { const s = getComputedStyle(el); return s.color !== s.backgroundColor; });
  assert(linkContrast, 'copy link stays legible in dark mode');
  await d.click('[data-step="5"]'); await d.waitForTimeout(300);
  await shot(d, 'd10-dark');
  await d.evaluate(() => { document.getElementById('about').open = true; });
  await d.waitForSelector('#about mjx-container', { timeout: 30000 });
  assert.deepStrictEqual(await valid(d), []);
  await d.context().close();

  // Phones: no sideways page scroll, on every step.
  const m = await open('', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  for (let i = 0; i < 8; i++) {
    await m.evaluate((n) => window.__build.go(n), i);
    await m.waitForTimeout(i === 7 ? 1200 : 200);
    const over = await m.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    assert(over <= 1, `phone overflow on step ${i + 1}: ${over}px`);
  }
  await m.evaluate(() => window.__build.go(1));
  await m.waitForTimeout(200);
  await shot(m, 'phone-d', false);
  await m.context().close();

  assert.deepStrictEqual(errors, [], 'no page errors');
  await browser.close();
  console.log('PASS');
})().catch((err) => { console.error('FAIL', err); process.exit(1); });
