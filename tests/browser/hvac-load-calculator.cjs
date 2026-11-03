// Drives the HVAC load calculator in Chromium. Run from the repository root with a
// static server already on port 8765:
//   NODE_PATH=$(pwd)/node_modules node tests/browser/hvac-load-calculator.cjs [screenshot-dir]
const { chromium } = require('playwright');
const assert = require('assert');
const path = require('path');

const BASE = process.env.BASE_URL || 'http://localhost:8765';
const shots = process.argv[2];

async function ready(page) {
  await page.waitForSelector('#loading-overlay.hidden', { state: 'attached', timeout: 120000 });
  await page.waitForFunction(() => document.getElementById('calculate-btn').textContent === 'Calculate');
}
const number = (text) => Number(String(text).replace(/[^0-9.-]/g, ''));
async function card(page, label) {
  return page.evaluate((wanted) => {
    const found = [...document.querySelectorAll('#results-grid .result-card')].find((c) => c.querySelector('.label').textContent === wanted);
    return found ? found.querySelector('.value').textContent : null;
  }, label);
}
async function press(page) {
  await page.click('#calculate-btn');
  await page.waitForFunction(() => document.getElementById('stale-note').hidden && document.getElementById('calculate-btn').textContent === 'Calculate');
}
async function step(page, name) { await page.click(`.step-tabs [data-step="${name}"]`); }
async function output(page, name) { await page.click(`.output-tabs [data-output="${name}"]`); }
async function shot(page, name, fullPage = true) {
  if (!shots) return;
  await page.addStyleTag({ content: '*{animation:none!important;transition:none!important}.calc-bar{position:static!important}' });
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(shots, name + '.png'), fullPage });
}

const noAnalytics = (context) => context.route(/google-analytics|googletagmanager/, (route) => route.abort());

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1360, height: 900 }, colorScheme: 'light' });
  await noAnalytics(context);
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => {
    // Failed loads are judged by URL below, because this message does not name one.
    if (m.type() === 'error' && !/Failed to load resource|favicon|net::ERR/.test(m.text())) errors.push('console: ' + m.text());
  });
  page.on('response', (r) => {
    if (r.status() < 400) return;
    const analytics = /google-analytics|googletagmanager|favicon/.test(r.url());
    console.log(`  HTTP ${r.status()} ${r.url().slice(0, 90)}${analytics ? ' (analytics, ignored)' : ''}`);
    if (!analytics) errors.push(`HTTP ${r.status()} ${r.url()}`);
  });

  // First load gives a result with no input.
  const start = Date.now();
  await page.goto(`${BASE}/tools/hvac-load-calculator/`);
  await ready(page);
  console.log('Ready in', ((Date.now() - start) / 1000).toFixed(1), 's');
  const heat = number(await card(page, 'Heating load'));
  const cool = number(await card(page, 'Cooling load'));
  console.log('Default Chicago house: heating', heat, 'cooling', cool);
  assert(heat > 30000 && heat < 90000, 'plausible Chicago heating ' + heat);
  assert(cool > 15000 && cool < 60000, 'plausible Chicago cooling ' + cool);
  assert((await page.textContent('#station-note')).includes('NOAA'));
  assert(await page.evaluate(() => [...document.querySelectorAll('.tooltip-trigger')].every((t) => t.dataset.tooltip && t.dataset.tooltip !== 'Loading...')), 'every tooltip filled');
  await shot(page, '01-results-light');

  // ZIP lookup changes the design weather.
  const before = await page.inputValue('#heating_design_f');
  await page.fill('#location_query', '33101');
  await page.waitForFunction((b) => document.getElementById('heating_design_f').value !== b, before);
  await press(page);
  const miamiHeat = number(await card(page, 'Heating load'));
  assert(miamiHeat < heat / 2, 'Miami heats far less than Chicago');
  await page.fill('#location_query', 'Toronto');
  await page.waitForFunction(() => document.getElementById('station-note').textContent.includes('NOAA') && Number(document.getElementById('heating_design_f').value) < 20);
  await page.fill('#location_query', '60601');
  await page.waitForFunction(() => Number(document.getElementById('heating_design_f').value) < 10);

  // The band narrows when an input becomes known.
  await press(page);
  const band = () => page.textContent('#confidence');
  const first = await band();
  await step(page, 'details');
  await page.fill('#ach50', '6');
  await press(page);
  const second = await band();
  assert.notStrictEqual(first, second, 'entering a blower door number changes the band');

  // Derivation opens with real numbers and math.
  await page.click('.component-row[data-key="walls"]');
  await page.waitForSelector('.deriv-row mjx-container', { timeout: 30000 });
  assert((await page.textContent('.deriv-row')).length > 40);
  await shot(page, '02-derivation');
  await page.click('.component-row[data-key="walls"]');
  assert.strictEqual(await page.$('.deriv-row'), null, 'derivation closes');

  // Era preset fills fields.
  await step(page, 'house');
  await page.selectOption('#era', 'new_code');
  await step(page, 'details');
  assert.strictEqual(await page.inputValue('#ach50'), '3');

  // Rooms.
  await step(page, 'rooms');
  await page.click('#room-typical');
  await press(page);
  await output(page, 'rooms');
  const rows = await page.$$eval('#rooms-output tbody tr', (r) => r.length);
  assert(rows >= 5, 'room rows ' + rows);
  await shot(page, '03-rooms');

  // Share link restores rooms and weather.
  const shared = await page.evaluate(() => window.UrlState.getShareUrl());
  assert(shared.includes('rooms_json'), 'rooms in the share link');
  const second_page = await context.newPage();
  await second_page.goto(shared);
  await ready(second_page);
  const roomsRestored = await second_page.$$eval('#room-list .room-card', (r) => r.length);
  assert(roomsRestored >= 5, 'rooms restored ' + roomsRestored);
  await second_page.close();

  // Design day charts.
  await output(page, 'day');
  await page.waitForSelector('#chart-hourly .main-svg');
  await page.waitForSelector('#chart-temps .main-svg');
  assert.strictEqual(await page.$$eval('#orientation .orient-row', (r) => r.length), 8);
  await shot(page, '04-design-day');

  // Equipment.
  await step(page, 'equipment');
  await page.click('#equip-suggest');
  await page.waitForSelector('#chart-balance .main-svg');
  await page.waitForSelector('#chart-bins .main-svg');
  const verdict = await page.textContent('#verdict');
  assert(verdict.length > 10, 'verdict shown');
  assert(!verdict.startsWith('FAIL') && !/\bFail\b/.test(await page.textContent('#equip-checks')), 'the tool does not fail its own suggestion: ' + verdict);
  await shot(page, '05-equipment');
  await page.click('#settings-button');
  await page.click('.settings-panel [data-theme="dark"]');
  await page.click('#settings-close');
  await page.waitForTimeout(500);
  await shot(page, '08-equipment-dark');
  await output(page, 'day');
  await page.waitForTimeout(500);
  await shot(page, '10-design-day-dark');
  await output(page, 'equip');
  await page.click('#settings-button');
  await page.click('.settings-panel [data-theme="light"]');
  await page.click('#settings-close');

  // Fuel bill.
  await step(page, 'bills');
  await page.fill('#bill_usage', '150');
  await press(page);
  await output(page, 'results');
  assert((await page.textContent('#bill-result')).includes('design heat loss'));

  // Bad input shows a clear message and no crash.
  await step(page, 'house');
  await page.fill('#floor_area_ft2', '-5');
  await page.click('#calculate-btn');
  await page.waitForFunction(() => !document.getElementById('error-box').hidden);
  assert((await page.textContent('#error-box')).includes('greater than zero'));
  await page.fill('#floor_area_ft2', '2000');
  await press(page);
  assert(await page.evaluate(() => document.getElementById('error-box').hidden));

  // Exports.
  const [csv] = await Promise.all([page.waitForEvent('download'), page.click('#export-csv')]);
  assert.strictEqual(csv.suggestedFilename(), 'hvac-load-calculation.csv');
  const [json] = await Promise.all([page.waitForEvent('download'), page.click('#export-json')]);
  const saved = await json.path();
  await page.setInputFiles('#import-json', saved);
  await page.waitForTimeout(800);
  await page.setInputFiles('#import-json', path.join('tools/hvac-load-calculator/test-cases/ashrae-atlanta.json'));
  await page.waitForFunction(() => {
    const found = [...document.querySelectorAll('#results-grid .result-card')].find((c) => c.querySelector('.label').textContent === 'Heating load');
    const v = Number(found.querySelector('.value').textContent.replace(/[^0-9]/g, ''));
    return Math.abs(v - 27000) <= 100;
  }, null, { timeout: 15000 });
  console.log('Atlanta test case loaded through the page: heating', await card(page, 'Heating load'));

  // Background math renders.
  await output(page, 'background');
  await page.waitForSelector('#tab-background mjx-container', { timeout: 30000 });
  await shot(page, '06-background');

  // Dark theme: every control stays legible.
  await page.click('#settings-button');
  await page.click('.settings-panel [data-theme="dark"]');
  await page.click('#settings-close');
  await output(page, 'results');
  const contrast = await page.evaluate(() => {
    const luminance = (color) => {
      const [r, g, b] = color.match(/[\d.]+/g).map(Number).map((c) => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const el = document.getElementById('floor_area_ft2');
    const style = getComputedStyle(el);
    const a = luminance(style.color); const b = luminance(style.backgroundColor);
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  });
  assert(contrast > 4.5, 'input contrast in dark mode ' + contrast);
  assert.strictEqual(await page.evaluate(() => getComputedStyle(document.getElementById('floor_area_ft2')).colorScheme), 'dark', 'number arrows follow the dark theme');
  await page.waitForTimeout(300);
  await shot(page, '07-results-dark');
  await page.click('#settings-button');
  await page.click('.settings-panel [data-theme="light"]');
  await page.click('#settings-close');

  // Phone width: no sideways page scroll.
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await noAnalytics(phone);
  const mobile = await phone.newPage();
  mobile.on('pageerror', (e) => errors.push('mobile pageerror: ' + e.message));
  await mobile.goto(`${BASE}/tools/hvac-load-calculator/`);
  await ready(mobile);
  for (const name of ['results', 'day', 'rooms', 'equip', 'background']) {
    await output(mobile, name);
    await mobile.waitForTimeout(300);
    const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    assert(overflow <= 1, `phone overflow on ${name}: ${overflow}px`);
  }
  await output(mobile, 'results');
  await shot(mobile, '09-phone', false);
  await mobile.evaluate(() => document.getElementById('tab-results').scrollIntoView());
  await shot(mobile, '11-phone-results', false);
  await output(mobile, 'day');
  await mobile.waitForSelector('#chart-hourly .main-svg');
  await mobile.evaluate(() => document.getElementById('tab-day').scrollIntoView());
  await shot(mobile, '12-phone-day', false);

  assert.deepStrictEqual(errors, [], 'no page errors');
  await browser.close();
  console.log('PASS');
})().catch((error) => { console.error('FAIL', error); process.exit(1); });
