/* Shared by the HVAC prototypes: real engine, tiered inputs, system choice, drill-down. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(Number(v))) ? '–'
    : Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  const COMPONENTS = {
    windows: { label: 'Windows', color: '--s-windows' }, walls: { label: 'Walls', color: '--s-walls' },
    doors: { label: 'Doors', color: '--s-walls' }, ceiling: { label: 'Ceiling', color: '--s-ceiling' },
    floor: { label: 'Floor', color: '--s-floor' }, infiltration: { label: 'Air leakage', color: '--s-air' },
    ventilation: { label: 'Ventilation', color: '--s-air' }, internal: { label: 'People and appliances', color: '--s-people' },
    ducts: { label: 'Ducts', color: '--s-ducts' }, latent: { label: 'Moisture', color: '--s-latent' },
  };

  const SYSTEMS = {
    furnace_ac: { name: 'Furnace + central AC', blurb: 'Gas or oil heat, separate AC.', sizes: 'Furnace output and AC size', ducted: true, heating: 'furnace', hp: false, furnace: true },
    heat_pump: { name: 'Heat pump', blurb: 'One unit heats and cools, electric backup.', sizes: 'Heat pump size and backup heat', ducted: true, heating: 'heat_pump', hp: true, furnace: false },
    dual_fuel: { name: 'Heat pump + furnace', blurb: 'Dual fuel. Furnace takes over in deep cold.', sizes: 'Heat pump size and furnace output', ducted: true, heating: 'heat_pump', hp: true, furnace: true },
    ductless: { name: 'Ductless mini-split', blurb: 'Wall units, no ducts to lose heat.', sizes: 'Mini-split size and backup heat', ducted: false, heating: 'heat_pump', hp: true, furnace: false },
  };
  const HP_RATIOS = {
    standard: { r17: 0.62, r5: null, min: null, cop47: 3.3, cop17: 2.2, label: 'Standard' },
    variable: { r17: 0.72, r5: null, min: 0.35, cop47: 3.6, cop17: 2.4, label: 'Variable speed' },
    cold: { r17: 0.95, r5: 0.82, min: 0.25, cop47: 3.8, cop17: 2.6, label: 'Cold climate' },
  };
  const TONS = [1, 1.5, 2, 2.5, 3, 3.5, 4, 5];
  const FURNACES = [20000, 30000, 40000, 50000, 60000, 70000, 80000, 100000, 120000];

  const state = {
    zip: '60601', floor_area_ft2: 2000, stories: 1, era: '1980s_90s', floor_type: 'slab', bedrooms: 3,
    system: 'furnace_ac', hpType: 'cold', tons: null, furnace: null, aux_kw: null,
    fields: {}, known: new Set(), rooms: null,
  };

  let callPy = null;
  let engineInputs = new Set();
  let docs = {};
  let presets = null;
  let stations = [];
  let zipTable = null;
  let station = null;
  let binWidth = 5;

  // ---------------------------------------------------------------- engine
  function inputs() {
    const era = presets.eras[state.era];
    const wall = presets.walls[state.fields.wall_preset || era.wall_preset];
    const ceil = presets.ceilings[state.fields.ceiling_preset || era.ceiling_preset];
    const win = presets.windows[state.fields.window_preset || era.window_preset];
    const sys = SYSTEMS[state.system];
    const out = {
      floor_area_ft2: state.floor_area_ft2, stories: state.stories, bedrooms: state.bedrooms, floor_type: state.floor_type,
      wall_u: wall.u, wall_layers: wall.layers, ceiling_u: ceil.u, window_u: win.u, window_shgc: win.shgc,
      ach50: era.ach50, duct_leakage_pct: era.duct_leakage_pct, duct_r: era.duct_r, slab_edge: era.slab_edge,
      heating_system: sys.heating, duct_location: sys.ducted ? 'attic' : 'conditioned',
    };
    if (station) {
      const m = station.tm;
      Object.assign(out, {
        heating_design_f: station.h99, cooling_design_f: station.c1, cooling_wet_bulb_f: station.wb, daily_range_f: station.dr,
        latitude: station.la, elevation_ft: station.el, ground_mean_f: m.reduce((a, b) => a + b, 0) / 12,
        ground_amp_f: (Math.max(...m) - Math.min(...m)) / 2,
      });
    }
    // Only names the engine accepts. Interface-only fields, such as wall layers, stay here.
    Object.entries(state.fields).forEach(([k, v]) => {
      if (!engineInputs.has(k) || v === '' || v === null || v === undefined) return;
      out[k] = v;
    });
    if (!sys.ducted) out.duct_location = 'conditioned';
    if (state.rooms && state.rooms.length) out.rooms = state.rooms;
    return out;
  }
  function calc(detail) {
    return callPy('calculate_hvac_loads', { inputs: inputs(), known_inputs: Array.from(state.known), detail: !!detail });
  }
  function nearest(list, value) { return list.find((x) => x >= value) || list[list.length - 1]; }
  function autosize(result) {
    const sys = SYSTEMS[state.system];
    const design = result.design.heating_f;
    const r = HP_RATIOS[state.hpType];
    const coolTons = Math.max(result.sizing.cooling_tons || 5, 1);
    if (sys.hp && !sys.furnace) {
      const at = design >= 17 ? 1 - (1 - r.r17) * (47 - Math.min(design, 47)) / 30
        : (r.r5 ? Math.max(r.r5 + (design - 5) / 12 * (r.r17 - r.r5), 0.4) : Math.max(r.r17 - (17 - design) * 0.012, 0.3));
      return { tons: Math.max(nearest(TONS, result.heating_total / (12000 * at)), coolTons), furnace: 0 };
    }
    return { tons: coolTons, furnace: sys.furnace ? nearest(FURNACES, result.heating_total) : 0 };
  }
  function sizes(result) {
    const auto = autosize(result);
    return { tons: state.tons ?? auto.tons, furnace: state.furnace ?? auto.furnace };
  }
  function equipment(result) {
    const sys = SYSTEMS[state.system];
    const s = sizes(result);
    const payload = {
      heating_load: result.heating_total, cooling_sensible: result.cooling_sensible, cooling_latent: result.cooling_latent,
      heating_design_f: result.design.heating_f, cooling_design_f: result.design.cooling_f, indoor_heating_f: result.design.indoor_heating_f,
      internal_gain_btuh: result.cooling.internal_sensible,
      cooling_rated_btuh: s.tons * 12000,
      cooling_stages: sys.hp && state.hpType !== 'standard' ? 'variable' : 'single',
    };
    if (sys.furnace) payload.furnace_output_btuh = s.furnace;
    if (sys.hp) {
      const r = HP_RATIOS[state.hpType]; const cap = s.tons * 12000;
      Object.assign(payload, { hp_cap_47: cap, hp_cap_17: Math.round(cap * r.r17), hp_cop_47: r.cop47, hp_cop_17: r.cop17 });
      if (r.r5) payload.hp_cap_5 = Math.round(cap * r.r5);
      if (r.min) payload.hp_min_47 = Math.round(cap * r.min);
      if (station) { payload.bins_start_f = station.b0; payload.bins_hours = station.b; payload.bin_width_f = binWidth; }
      // Backup defaults to what the design hour needs, in 5 kW steps.
      const probe = callPy('evaluate_equipment', { ...payload, aux_kw: 0 });
      const needed = probe.backup_kw_at_design || 0;
      payload.aux_kw = sys.furnace ? 0 : (state.aux_kw ?? Math.ceil(needed / 5 - 1e-6) * 5);
    }
    const out = callPy('evaluate_equipment', payload);
    out.installed_aux_kw = payload.aux_kw || 0;
    return out;
  }

  // -------------------------------------------------------------- location
  const miles = (a, b, c, d) => {
    const r = Math.PI / 180;
    const x = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2;
    return 3958.8 * 2 * Math.asin(Math.sqrt(x));
  };
  async function locate(zip) {
    if (!zipTable) {
      const text = await fetch('data/zips.txt').then((r) => r.text());
      zipTable = new Map();
      text.split('\n').forEach((line) => { const [z, a, o] = line.split(' '); if (z) zipTable.set(z, [Number(a), Number(o)]); });
    }
    const at = zipTable.get(zip);
    if (!at) return null;
    let best = null; let score = Infinity;
    stations.forEach((s) => {
      const value = miles(at[0], at[1], s.la, s.lo) + (14 - s.yrs) * 5;
      if (value < score) { score = value; best = s; }
    });
    station = best;
    return best;
  }

  // ------------------------------------------------------------- level panel
  const presetOptions = (table) => Object.entries(table).map(([k, v]) => [k, v.label]);
  function fieldHtml(f) {
    const current = f.get();
    if (f.options) {
      return `<div class="fld"><label for="${f.id}">${esc(f.label)}</label><select id="${f.id}" data-field="${f.id}">${f.options.map(([v, t]) => `<option value="${esc(v)}"${String(v) === String(current) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select>${f.help ? `<div class="help">${esc(f.help)}</div>` : ''}</div>`;
    }
    return `<div class="fld"><label for="${f.id}">${esc(f.label)}${f.unit ? `<span>${esc(f.unit)}</span>` : ''}</label><input id="${f.id}" data-field="${f.id}" type="${f.text ? 'text' : 'number'}" step="any" value="${esc(current ?? '')}"${f.placeholder ? ` placeholder="${esc(f.placeholder)}"` : ''}>${f.help ? `<div class="help">${esc(f.help)}</div>` : ''}</div>`;
  }
  function levels() {
    const era = () => presets.eras[state.era];
    const ov = (id, key, label, def, extra = {}) => ({ id, label, get: () => state.fields[key] ?? def(), set: (v) => { state.fields[key] = v; }, known: key, ...extra });
    return [
      { title: 'The basics', sub: 'A first answer in five inputs', fields: [
        { id: 'p-zip', label: 'ZIP code', text: true, get: () => state.zip, set: (v) => { state.zip = v; }, relocate: true },
        { id: 'p-area', label: 'Conditioned floor area', unit: 'ft²', get: () => state.floor_area_ft2, set: (v) => { state.floor_area_ft2 = v; } },
        { id: 'p-stories', label: 'Stories above grade', options: [[1, '1'], [2, '2'], [3, '3']], get: () => state.stories, set: (v) => { state.stories = Number(v); } },
        { id: 'p-era', label: 'When was it built?', options: presetOptions(presets.eras), get: () => state.era, set: (v) => { state.era = v; }, help: 'Fills in typical insulation, windows, leakage, and ducts. Later levels replace these guesses.' },
        { id: 'p-floor', label: 'Foundation', options: [['slab', 'Slab on grade'], ['crawl_vented', 'Vented crawlspace'], ['crawl_sealed', 'Sealed crawlspace'], ['basement_conditioned', 'Heated basement'], ['basement_unconditioned', 'Unheated basement']], get: () => state.floor_type, set: (v) => { state.floor_type = v; } },
      ] },
      { title: 'The shell', sub: 'Replace era guesses with what you know', fields: [
        ov('p-wall', 'wall_preset', 'Walls', () => era().wall_preset, { options: presetOptions(presets.walls), known: 'wall_u' }),
        ov('p-ceil', 'ceiling_preset', 'Ceiling insulation', () => era().ceiling_preset, { options: presetOptions(presets.ceilings), known: 'ceiling_u' }),
        ov('p-win', 'window_preset', 'Windows', () => era().window_preset, { options: presetOptions(presets.windows), known: 'window_u' }),
        ov('p-winpct', 'window_pct_of_floor', 'Window area', () => 14, { unit: '% of floor', num: true, known: 'window_pct_of_floor' }),
        ov('p-roof', 'roof_color', 'Roof surface', () => 'medium', { options: [['white', 'White'], ['light', 'Light'], ['medium', 'Medium'], ['dark', 'Dark']], known: null }),
      ] },
      { title: 'Air and ducts', sub: 'Usually the biggest unknowns', fields: [
        ov('p-ach', 'ach50', 'Blower door result', () => era().ach50, { unit: 'ACH50', num: true, help: 'Air changes at 50 Pa. The most valuable single measurement for an older house.' }),
        ov('p-dloc', 'duct_location', 'Where the ducts run', () => 'attic', { options: [['attic', 'Attic'], ['conditioned', 'Inside conditioned space'], ['vented_crawl', 'Vented crawlspace'], ['basement', 'Basement'], ['garage', 'Garage']], known: null }),
        ov('p-dleak', 'duct_leakage_pct', 'Duct leakage per side', () => era().duct_leakage_pct, { unit: '%', num: true }),
        ov('p-dr', 'duct_r', 'Duct insulation', () => era().duct_r, { unit: 'R', num: true }),
      ] },
      { title: 'Expert', sub: 'Every remaining assumption', fields: [
        ov('p-iht', 'indoor_heating_f', 'Winter thermostat', () => 70, { unit: '°F', num: true, known: null }),
        ov('p-ict', 'indoor_cooling_f', 'Summer thermostat', () => 75, { unit: '°F', num: true, known: null }),
        ov('p-swing', 'temperature_swing_f', 'Allowed temperature swing', () => 3, { unit: '°F', num: true, known: null }),
        ov('p-mass', 'construction_mass', 'Thermal mass', () => 'light', { options: [['light', 'Light (frame)'], ['medium', 'Medium'], ['heavy', 'Heavy (masonry)']], known: null }),
        ov('p-hd', 'heating_design_f', 'Winter design temperature', () => (station ? station.h99 : 10), { unit: '°F', num: true }),
        ov('p-cd', 'cooling_design_f', 'Summer design temperature', () => (station ? station.c1 : 90), { unit: '°F', num: true }),
        ov('p-occ', 'occupants', 'Occupants', () => state.bedrooms + 1, { unit: 'people', num: true }),
      ] },
    ];
  }
  function buildLevels(el, onChange) {
    const list = levels();
    const allFields = {};
    list.forEach((lvl) => lvl.fields.forEach((f) => { allFields[f.id] = f; }));
    el.innerHTML = `<div class="confidence" id="confidence"></div>` + list.map((lvl, i) => (
      `<details class="level"${i === 0 ? ' open' : ''}><summary><span class="dot">${i + 1}</span>${esc(lvl.title)}<span class="count">${lvl.fields.length} inputs</span></summary><div class="body"><p class="note" style="margin:0 0 8px">${esc(lvl.sub)}</p>${lvl.fields.map(fieldHtml).join('')}</div></details>`
    )).join('') + `<p class="note" id="station-line" style="margin:8px 0 0"></p>`;
    el.addEventListener('change', async (e) => {
      const f = allFields[e.target.dataset.field];
      if (!f) return;
      const raw = e.target.value;
      f.set(f.num || (!f.options && !f.text) ? (raw === '' ? '' : Number(raw)) : raw);
      if (f.known !== null && f.known !== undefined) state.known.add(f.known);
      if (f.id === 'p-era') { ['wall_preset', 'ceiling_preset', 'window_preset', 'ach50', 'duct_leakage_pct', 'duct_r'].forEach((k) => delete state.fields[k]); state.known.clear(); buildAgain(); return; }
      if (f.relocate) await locate(state.zip);
      onChange();
    });
    function buildAgain() {
      const fresh = el.cloneNode(false); el.replaceWith(fresh); buildLevels(fresh, onChange); onChange();
    }
  }
  function updateConfidence() {
    const box = $('confidence');
    const line = $('station-line');
    if (line && station) line.textContent = `Weather: ${station.n}${station.s ? ', ' + station.s : ''}. ${fmt(station.h99)} °F winter, ${fmt(station.c1)} °F summer, from ${station.yrs} years of NOAA data.`;
    if (!box) return;
    try {
      const r = calc(true);
      const band = r.uncertainty;
      const heat = (band.heating_high - band.heating_low) / 2 / r.heating_total * 100;
      const cool = (band.cooling_high - band.cooling_low) / 2 / r.cooling_total * 100;
      const open = band.terms.find((t) => !t.known);
      const score = Math.max(4, 100 - (heat + cool));
      box.innerHTML = `<strong>How sure is this?</strong> Heating ±${fmt(heat)}%, cooling ±${fmt(cool)}%<div class="bar"><div class="fill" style="width:${score}%"></div></div><span class="note">${open ? `Next best thing to find out: ${esc(open.label.toLowerCase())}.` : 'All major inputs confirmed.'}</span>`;
    } catch (e) { box.textContent = ''; }
  }

  // ---------------------------------------------------------- system picker
  function buildSystem(el, onChange) {
    function draw(result) {
      const sys = SYSTEMS[state.system];
      const s = result ? sizes(result) : { tons: 0, furnace: 0 };
      el.innerHTML = `<div class="sys" role="radiogroup" aria-label="Heating and cooling system">${Object.entries(SYSTEMS).map(([k, v]) => (
        `<button type="button" role="radio" aria-checked="${k === state.system}" data-sys="${k}" class="${k === state.system ? 'on' : ''}"><strong>${esc(v.name)}</strong>${esc(v.blurb)}</button>`
      )).join('')}</div>
      <div class="sizing"><strong>You are sizing:</strong>
        <span>${sys.hp ? 'Heat pump' : 'AC'} <span class="stepper"><button type="button" data-step="tons:-1" aria-label="Smaller">−</button><output>${s.tons} ton</output><button type="button" data-step="tons:1" aria-label="Larger">+</button></span></span>
        ${sys.furnace ? `<span>Furnace output <span class="stepper"><button type="button" data-step="furnace:-1" aria-label="Smaller furnace">−</button><output>${fmt(s.furnace / 1000)}k Btu/h</output><button type="button" data-step="furnace:1" aria-label="Larger furnace">+</button></span></span>` : ''}
        ${sys.hp ? `<select aria-label="Heat pump type" data-hp style="padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--card);min-height:38px">${Object.entries(HP_RATIOS).map(([k, r]) => `<option value="${k}"${k === state.hpType ? ' selected' : ''}>${r.label}</option>`).join('')}</select>` : ''}
        ${(state.tons !== null || state.furnace !== null) ? '<button type="button" class="btn" data-auto>Use suggested sizes</button>' : '<span class="note">Suggested from your load. Change it to test a quote.</span>'}
      </div>`;
    }
    el.addEventListener('click', (e) => {
      const t = e.target;
      if (t.dataset.sys) { state.system = t.dataset.sys; state.tons = null; state.furnace = null; state.aux_kw = null; onChange(); }
      if (t.dataset.auto !== undefined) { state.tons = null; state.furnace = null; onChange(); }
      if (t.dataset.step && Proto.lastResult) {
        const [key, dir] = t.dataset.step.split(':');
        const s = sizes(Proto.lastResult);
        const list = key === 'tons' ? TONS : FURNACES;
        const i = list.indexOf(s[key]);
        state[key] = list[Math.min(list.length - 1, Math.max(0, (i < 0 ? 0 : i) + Number(dir)))];
        onChange();
      }
    });
    el.addEventListener('change', (e) => { if (e.target.dataset.hp !== undefined) { state.hpType = e.target.value; state.tons = null; onChange(); } });
    return draw;
  }

  // -------------------------------------------------------------- fit strip
  function fitStrip(result, eq) {
    const sys = SYSTEMS[state.system];
    const heatCap = (sys.furnace ? (eq.furnace_pct || 0) * result.heating_total / 100 : 0)
      || ((eq.hp_capacity_at_design || 0) + (sys.hp ? (eq.backup_kw_at_design || 0) * 0 : 0));
    const hpOnly = sys.hp && !sys.furnace;
    const row = (title, load, capacity, parts, limit, capLabel, statusText, cls) => {
      const scale = Math.max(load * 1.5, capacity * 1.05, 1);
      const pct = (v) => `${(v / scale * 100).toFixed(1)}%`;
      let left = 0;
      const segs = parts.filter(([, v]) => v > 0).map(([k, v]) => {
        const html = `<div class="fit-seg" title="${esc(COMPONENTS[k].label)}: ${fmt(v)} Btu/h" style="left:${pct(left)};width:${pct(v)};background:var(${COMPONENTS[k].color})"></div>`;
        left += v; return html;
      }).join('');
      const positive = parts.reduce((a, [, v]) => a + Math.max(v, 0), 0) || 1;
      return `<div class="fit-row"><div class="head"><span><strong>${title}</strong> needs ${fmt(load)} Btu/h</span><span class="${cls}">${esc(statusText)}</span></div>
        <div class="fit-track" role="img" aria-label="${title} load ${fmt(load)}, capacity ${fmt(capacity)} Btu/h">${segs.replace(/left:([\d.]+)%;width:([\d.]+)%/g, (m, a, b) => `left:${(a * load / positive).toFixed(2)}%;width:${(b * load / positive).toFixed(2)}%`)}<div class="fit-band" style="left:${pct(load * 0.9)};width:${pct(load * (limit - 0.9))}"></div><div class="fit-mark" style="left:${pct(capacity)}"></div></div>
        <div class="note" style="margin-top:3px">Black mark: ${esc(capLabel)}. Hatched: the size range that fits.</div></div>`;
    };
    const h = result.heating.components; const c = result.cooling.components;
    const heatParts = ['walls', 'windows', 'doors', 'ceiling', 'floor', 'infiltration', 'ventilation', 'ducts'].map((k) => [k, h[k] || 0]);
    const coolParts = ['windows', 'walls', 'doors', 'ceiling', 'infiltration', 'ventilation', 'internal', 'ducts'].map((k) => [k, c[k] || 0]).concat([['latent', result.cooling_latent]]);
    const capC = eq.cooling_capacity_total || 0;
    const pctC = eq.cooling_total_pct || 0;
    const limitC = (eq.cooling_limit_pct || 115) / 100;
    const statusC = pctC < 90 ? ['Too small', 'bad'] : pctC > limitC * 100 ? ['Oversized for cooling', 'warn'] : ['Fits', 'ok'];
    let capH = heatCap; let labelH; let statusH;
    if (hpOnly) {
      const needed = eq.backup_kw_at_design || 0;
      labelH = `heat pump delivers ${fmt(capH)} Btu/h at ${fmt(result.design.heating_f)} °F`;
      statusH = needed > 0 ? [`Needs ${fmt(needed, 1)} kW backup at design`, 'warn'] : ['Compressor covers the design hour', 'ok'];
    } else if (sys.furnace) {
      labelH = `furnace output ${fmt(capH)} Btu/h`;
      const pct = eq.furnace_pct || 0;
      statusH = pct < 100 ? ['Too small', 'bad'] : pct > 140 ? ['Oversized', 'warn'] : ['Fits', 'ok'];
    }
    return `<div class="fit">${row('Heating', result.heating_total, capH, heatParts, hpOnly ? 1.4 : 1.4, labelH, statusH[0], statusH[1])}${row('Cooling', result.cooling_total, capC, coolParts, limitC, `${sys.hp ? 'heat pump' : 'AC'} delivers ${fmt(capC)} Btu/h at ${fmt(result.design.cooling_f)} °F`, `${fmt(pctC)}% of load. ${statusC[0]}`, statusC[1])}</div>`;
  }
  function keyHtml(keys) {
    return `<div class="key">${keys.map((k) => `<span><i style="background:var(${COMPONENTS[k].color})"></i>${esc(COMPONENTS[k].label)}</span>`).join('')}</div>`;
  }

  // ------------------------------------------------------------------ drill
  const tex = (s) => (s ? `\\(${s}\\)` : '');
  function nodeBody(node) {
    const value = `<div class="drill-value">${fmt(node.value, node.digits)}<small>${esc(node.unit)}</small></div>`;
    const vars = node.variables.length ? `<h4>What each symbol means</h4><div class="table-scroll"><table class="vars"><thead><tr><th>Symbol</th><th>Meaning</th><th style="text-align:right">Value</th><th>Unit</th></tr></thead><tbody>${node.variables.map((v) => (
      `<tr><td>${tex(v.symbol)}</td><td>${esc(v.meaning)}</td><td class="v">${v.value === null || v.value === undefined ? 'varies' : typeof v.value === 'number' ? fmt(v.value, Math.abs(v.value) < 1 ? 3 : Math.abs(v.value) < 100 ? 1 : 0) : esc(v.value)}</td><td class="u">${esc(v.unit)}</td></tr>`
    )).join('')}</tbody></table></div>` : '';
    return `${value}<p style="margin:6px 0 0;font-size:.9rem">${esc(node.about)}</p>
      ${node.equation ? `<h4>The equation</h4><div class="eq">${tex(node.equation)}</div>` : ''}
      ${vars}
      ${node.substituted ? `<h4>With your numbers</h4><div class="eq">${tex(node.substituted)}</div>` : ''}
      ${node.meaning ? `<div class="callout">${esc(node.meaning)}</div>` : ''}
      ${node.limits.length ? `<details class="limits"><summary>When this does not apply</summary><ul>${node.limits.map((l) => `<li>${esc(l)}</li>`).join('')}</ul></details>` : ''}
      ${node.reference ? `<div class="ref">${esc(node.reference)}</div>` : ''}`;
  }
  function typeset(el) {
    if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([el]).catch(() => {});
    else setTimeout(() => typeset(el), 300);
  }
  function findPath(root, id, path = []) {
    const here = [...path, root];
    if (root.id === id) return here;
    for (const c of root.children) { const f = findPath(c, id, here); if (f) return f; }
    return null;
  }
  function Drill(el) {
    let current = 'heating';
    function draw() {
      const tree = Proto.lastResult && Proto.lastResult.tree;
      if (!tree) return;
      const path = findPath(tree.heating, current) || findPath(tree.cooling, current) || [tree.heating];
      const node = path[path.length - 1];
      const max = Math.max(...node.children.map((c) => Math.abs(c.unit === 'Btu/h' ? c.value : 0)), 1);
      el.innerHTML = `<div class="crumbs">${path.map((p, i) => (i < path.length - 1 ? `<button type="button" data-go="${p.id}">${esc(p.label)}</button> ›` : `<strong>${esc(p.label)}</strong>`)).join(' ')}</div>
        <div class="drill">${nodeBody(node)}${node.children.length ? `<h4>Made up of</h4>${node.children.map((c) => (
          `<button type="button" class="child" data-go="${c.id}"><span class="name">${esc(c.label)}</span><span class="val">${fmt(c.value, c.digits)} ${esc(c.unit)}</span>${c.unit === 'Btu/h' ? `<span class="meter"><b style="width:${Math.max(0, c.value) / max * 100}%"></b></span>` : ''}</button>`
        )).join('')}` : ''}</div>`;
      typeset(el);
    }
    el.addEventListener('click', (e) => {
      const b = e.target.closest('[data-go]');
      if (b) { current = b.dataset.go; draw(); }
    });
    return { draw, open(id) { current = id; draw(); } };
  }
  function Tree(el) {
    const expanded = new Set(['heating', 'cooling']);
    function rowHtml(node, depth) {
      const isOpen = expanded.has(node.id);
      return `<div style="margin-left:${depth ? 14 : 0}px;border-left:${depth ? '1px solid var(--line)' : '0'};padding-left:${depth ? 8 : 0}px">
        <button type="button" class="child" data-toggle="${node.id}" aria-expanded="${isOpen}"><span class="name">${isOpen ? '▾' : '▸'} ${esc(node.label)}</span><span class="val">${fmt(node.value, node.digits)} ${esc(node.unit)}</span></button>
        ${isOpen ? `<div class="drill" style="padding:4px 4px 10px 10px">${nodeBody({ ...node, value: node.value })}</div>${node.children.map((c) => rowHtml(c, depth + 1)).join('')}` : ''}
      </div>`;
    }
    function draw() {
      const t = Proto.lastResult && Proto.lastResult.tree;
      if (!t) return;
      el.innerHTML = rowHtml(t.heating, 0) + rowHtml(t.cooling, 0);
      typeset(el);
    }
    el.addEventListener('click', (e) => {
      const b = e.target.closest('[data-toggle]');
      if (!b) return;
      const id = b.dataset.toggle;
      if (expanded.has(id)) expanded.delete(id); else expanded.add(id);
      draw();
    });
    return { draw };
  }

  // ------------------------------------------------------------------ start
  function nav(active) {
    const saved = (() => { try { return localStorage.getItem('hvac-proto-theme'); } catch (e) { return null; } })();
    const prefers = window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    document.documentElement.dataset.theme = saved || prefers;
    const header = document.createElement('header');
    header.className = 'pnav';
    header.innerHTML = `<a class="brand" href="../../../index.html">transparent<wbr>.tools</a><span class="tag">Prototype</span>
      <div class="links">${[['option-d-guided-build.html', 'D: Guided build'], ['option-e-workbench.html', 'E: Workbench'], ['option-a-cutaway.html', 'A'], ['option-b-floorplan.html', 'B'], ['option-c-sizing-board.html', 'C']].map(([h, t]) => `<a href="${h}" class="${h.startsWith(active) ? 'on' : ''}">${t}</a>`).join('')}<button type="button" id="p-theme">Theme</button></div>`;
    document.body.prepend(header);
    const cover = document.createElement('div');
    cover.className = 'loading'; cover.id = 'p-loading'; cover.textContent = 'Loading the real calculation engine...';
    document.body.append(cover);
    $('p-theme').addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('hvac-proto-theme', next); } catch (e) { /* private window */ }
      if (Proto.onTheme) Proto.onTheme();
    });
  }
  async function start() {
    const py = await loadPyodide();
    const [u, m] = await Promise.all([fetch('../../pycalcs/utils.py').then((r) => r.text()), fetch('../../pycalcs/hvac_loads.py').then((r) => r.text())]);
    py.FS.writeFile('utils.py', u); py.FS.writeFile('hvac_loads.py', m);
    py.runPython(`
import json, hvac_loads
def _call(name, payload):
    return json.dumps(getattr(hvac_loads, name)(**json.loads(payload)))
def _presets():
    return json.dumps(hvac_loads.get_presets())
def _inputs():
    return json.dumps(sorted(hvac_loads.DEFAULTS))
def _docs():
    import utils
    merged = {}
    for name in ("bill_check", "evaluate_equipment", "calculate_hvac_loads"):
        merged.update(utils.get_documentation("hvac_loads", name).get("parameters", {}))
    return json.dumps(merged)
`);
    const fn = py.globals.get('_call');
    callPy = (name, payload) => JSON.parse(fn(name, JSON.stringify(payload)));
    presets = JSON.parse(py.globals.get('_presets')());
    engineInputs = new Set(JSON.parse(py.globals.get('_inputs')()));
    docs = JSON.parse(py.globals.get('_docs')());
    const climate = await fetch('data/stations.json').then((r) => r.json());
    stations = climate.stations; binWidth = climate.bin_width_f;
    await locate(state.zip);
    if (!window.Core) $('p-loading').classList.add('done');
  }

  window.Proto = {
    call: (name, payload) => callPy(name, payload), inputs, get presets() { return presets; }, locate,
    state, fmt, esc, cssVar, COMPONENTS, SYSTEMS, TONS, nav, start, calc, equipment, sizes, buildLevels, buildSystem,
    updateConfidence, fitStrip, keyHtml, Drill, Tree, get station() { return station; }, get binWidth() { return binWidth; },
    lastResult: null, onTheme: null, get docs() { return docs; }, get stations() { return stations; },
  };
})();
