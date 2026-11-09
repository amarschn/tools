/* Page chrome for the HVAC load calculator: settings, share links, fuel bill, export. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const P = () => window.Proto; const C = () => window.Core; const M = () => window.HouseModel;
  const STORAGE = 'hvac-load-calculator-settings';
  const defaults = { theme: 'system' };
  let settings = { ...defaults };
  let stepsRef = null; let indexRef = () => 0;

  function readSettings() { try { settings = { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE) || '{}') }; } catch (e) { settings = { ...defaults }; } }
  function writeSettings() { try { localStorage.setItem(STORAGE, JSON.stringify(settings)); } catch (e) { /* private window */ } }
  function applyTheme() {
    const dark = settings.theme === 'dark' || (settings.theme === 'system' && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    document.querySelectorAll('[data-theme-choice]').forEach((b) => { const on = b.dataset.themeChoice === settings.theme; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
    if (Page.onTheme) Page.onTheme();
  }
  function openSettings(open) {
    $('settings').hidden = !open; $('settings-overlay').hidden = !open;
    if (open) $('settings-close').focus();
  }

  // --------------------------------------------------------------- share link
  function saveState() {
    const field = $('model_json'); if (!field || !C().model) return;
    clearTimeout(saveState.timer);
    saveState.timer = setTimeout(() => {
      field.value = JSON.stringify(C().serialize());
      field.dispatchEvent(new Event('input', { bubbles: true }));
    }, 400);
  }
  async function restore() {
    const raw = $('model_json') && $('model_json').value;
    if (!raw) return false;
    try {
      await C().restore(JSON.parse(raw));
      return true;
    } catch (e) {
      const box = $('model-error'); box.hidden = false; box.textContent = 'The shared link could not be read, so the tool started fresh.';
      return false;
    }
  }

  // ------------------------------------------------------------------- bill
  const FUELS = [['gas_therm', 'Natural gas, therms'], ['gas_ccf', 'Natural gas, CCF'], ['propane_gal', 'Propane, gallons'], ['oil_gal', 'Heating oil, gallons'], ['electric_kwh', 'Electric resistance, kWh']];
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const bill = { usage: '', fuel: 'gas_therm', month: 1, hdd: '', eff: 90, base: 0 };
  function billHtml() {
    const st = P().station; const typical = st ? st.hdd[bill.month - 1] : '';
    const f = C().field.bind(C());
    return `<details class="deeper" id="bill" ${bill.usage ? 'open' : ''}><summary>Check it against a fuel bill</summary><div class="deeper-body">
      <p class="note" style="margin:0 0 8px">A winter bill measures your real house, leaks and ducts included. It needs no assumptions about insulation.</p>
      <div class="two">${f('bill_usage', 'Fuel used in a cold month', bill.usage)}${f('bill_fuel', 'Unit', bill.fuel, { options: FUELS })}</div>
      <div class="two">${f('bill_month', 'Billing month', bill.month, { options: MONTHS.map((m, i) => [i + 1, m]) })}${f('bill_hdd', 'Degree days', bill.hdd, { placeholder: String(typical) })}</div>
      <div class="two">${f('bill_eff', 'Efficiency', bill.eff, { unit: '%' })}${f('bill_base', 'Non-heating use', bill.base)}</div>
      <div id="bill-out">${billResult()}</div></div></details>`;
  }
  function billResult() {
    if (!bill.usage) return '';
    const r = C().result; const st = P().station;
    const hdd = bill.hdd !== '' ? Number(bill.hdd) : (st ? st.hdd[bill.month - 1] : 0);
    try {
      const out = P().call('bill_check', { usage: Number(bill.usage), fuel: bill.fuel, efficiency_pct: Number(bill.eff), degree_days: hdd, heating_design_f: r.design.heating_f, baseline_usage: Number(bill.base) || 0 });
      const gap = (r.heating_total / out.measured_design_load - 1) * 100;
      const reading = Math.abs(gap) <= 20 ? 'They agree within normal bill and weather uncertainty.'
        : gap > 0 ? 'The model is higher than the bill. The house may be tighter or better insulated than assumed, or a setback, stove, or space heater may be cutting fuel use.'
          : 'The bill is higher than the model. Look for more leakage or duct loss than assumed, a warmer thermostat, or lower efficiency than the label.';
      return `<div class="sel-box" style="margin-top:6px"><strong>Your bill implies ${C().fmt(Math.round(out.measured_design_load / 100) * 100)} Btu/h</strong> at the design temperature, against ${C().fmt(Math.round(r.heating_total / 100) * 100)} Btu/h from the model (${gap >= 0 ? '+' : ''}${C().fmt(gap)}%). ${reading}<div class="note" style="margin-top:4px">UA from the bill: ${C().fmt(out.measured_ua)} Btu/h·°F, using ${C().fmt(hdd)} degree days.</div></div>`;
    } catch (e) {
      return `<p class="note">${C().esc(String(e.message || e).trim().split('\n').pop())}</p>`;
    }
  }

  // ----------------------------------------------------------------- export
  function exportHtml() {
    return `<details class="deeper"><summary>Save, share, or export</summary><div class="deeper-body export-row">
      <button type="button" class="btn" data-export="csv" data-track="export">Download CSV</button>
      <button type="button" class="btn" data-export="json" data-track="export">Save house (JSON)</button>
      <label class="btn file-btn">Open saved house<input type="file" id="import-json" accept="application/json" hidden></label>
      <button type="button" class="btn" data-export="print" data-track="export">Print</button>
      <p class="note" style="margin:4px 0 0">Copy Link at the top of the page shares this house as it stands.</p></div></details>`;
  }
  function download(name, type, text) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const cell = (v) => { const s = String(v ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  function csv() {
    const r = C().result; const b = C().band || {};
    const rows = [['HVAC load calculation', 'transparent.tools/tools/hvac-load-calculator'], ['Not ACCA-approved software. Review with a qualified designer before buying equipment.'], [],
      ['Result', 'Value', 'Unit'], ['Heating load', Math.round(r.heating_total), 'Btu/h'], ['Heating range low', Math.round(b.heating_low || 0), 'Btu/h'], ['Heating range high', Math.round(b.heating_high || 0), 'Btu/h'],
      ['Sensible cooling', Math.round(r.cooling_sensible), 'Btu/h'], ['Latent cooling', Math.round(r.cooling_latent), 'Btu/h'], ['Total cooling', Math.round(r.cooling_total), 'Btu/h'],
      ['Cooling range low', Math.round(b.cooling_low || 0), 'Btu/h'], ['Cooling range high', Math.round(b.cooling_high || 0), 'Btu/h'], ['Heat loss coefficient', Math.round(r.heat_loss_coefficient), 'Btu/h per F'],
      ['Winter design', r.design.heating_f, 'F'], ['Summer design', r.design.cooling_f, 'F'], [], ['Component', 'Heating Btu/h', 'Cooling Btu/h']];
    ['walls', 'windows', 'doors', 'ceiling', 'floor', 'infiltration', 'ventilation', 'internal', 'ducts'].forEach((k) => rows.push([k, Math.round(r.heating.components[k] || 0), Math.round(r.cooling.components[k] || 0)]));
    rows.push(['latent', 0, Math.round(r.cooling_latent)], [], ['Room', 'ft2', 'Heating Btu/h', 'Cooling Btu/h', 'Peak solar hour', 'Heating cfm', 'Cooling cfm']);
    r.rooms.forEach((x) => rows.push([x.name, x.area, Math.round(x.heating), Math.round(x.cooling), x.peak_hour, Math.round(x.heating_cfm), Math.round(x.cooling_cfm)]));
    rows.push([], ['Engine input', 'Value']);
    Object.entries(P().inputs()).forEach(([k, v]) => { if (k !== 'rooms') rows.push([k, v]); });
    download('hvac-load-calculation.csv', 'text/csv', rows.map((row) => row.map(cell).join(',')).join('\n'));
  }

  function bind(steps, index) {
    stepsRef = steps; indexRef = index;
    document.addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.export === 'csv') csv();
      if (b.dataset.export === 'json') download('hvac-house.json', 'application/json', JSON.stringify(C().serialize(), null, 2));
      if (b.dataset.export === 'print') window.print();
    });
    document.addEventListener('change', async (e) => {
      const t = e.target;
      if (t.id === 'import-json' && t.files[0]) {
        const text = await t.files[0].text();
        try { await C().restore(JSON.parse(text)); C().update(); } catch (err) { const box = $('model-error'); box.hidden = false; box.textContent = String(err.message || err); }
        t.value = '';
        return;
      }
      const key = t.dataset && t.dataset.set;
      if (key && key.startsWith('bill_')) {
        e.stopImmediatePropagation();
        const name = key.slice(5); bill[name] = t.type === 'number' || name === 'month' ? (t.value === '' ? '' : Number(t.value)) : t.value;
        if (name === 'month') { bill.hdd = ''; const hdd = $('f-bill_hdd'); if (hdd) { hdd.value = ''; hdd.placeholder = String(P().station ? P().station.hdd[bill.month - 1] : ''); } }
        $('bill-out').innerHTML = billResult();
      }
    }, true);
  }

  function start() {
    readSettings(); applyTheme();
    $('settings-button').addEventListener('click', () => openSettings(true));
    $('settings-close').addEventListener('click', () => openSettings(false));
    $('settings-overlay').addEventListener('click', () => openSettings(false));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('settings').hidden) openSettings(false); });
    document.querySelectorAll('[data-theme-choice]').forEach((b) => b.addEventListener('click', () => { settings.theme = b.dataset.themeChoice; writeSettings(); applyTheme(); }));
    $('settings-reset').addEventListener('click', () => { settings = { ...defaults }; writeSettings(); applyTheme(); });
    // Equations in the background section render the first time it opens.
    const about = $('about');
    if (about) about.addEventListener('toggle', function typeset() {
      if (!about.open) return;
      const run = () => (window.MathJax && MathJax.typesetPromise ? MathJax.typesetPromise([about]).catch(() => {}) : setTimeout(run, 300));
      run();
      about.removeEventListener('toggle', typeset);
    });
    if (window.matchMedia) matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (settings.theme === 'system') applyTheme(); });
  }

  const Page = { start, bind, billHtml, exportHtml, saveState, restore, onTheme: null };
  window.Page = Page;
})();
