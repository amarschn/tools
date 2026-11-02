/* HVAC load calculator front end. All engineering lives in pycalcs/hvac_loads.py. */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = 'hvac-load-calculator-settings';
  const defaultSettings = { theme: 'system', density: 'comfortable', expertMode: false };
  let settings = { ...defaultSettings };

  let py = null;            // Pyodide helper: call(fn, payload) -> object
  let presets = null;
  let stations = [];
  let binWidth = 5;
  let zipTable = null;
  let station = null;
  let last = null;
  let lastEquipment = null;
  const known = new Set();
  let rooms = [];
  let chartsDirty = true;
  let openRow = null;

  // Input ids sent to calculate_hvac_loads as numbers or strings.
  const NUMERIC = [
    'floor_area_ft2', 'stories', 'bedrooms', 'heating_design_f', 'cooling_design_f', 'cooling_wet_bulb_f',
    'daily_range_f', 'latitude', 'elevation_ft', 'wall_u', 'wall_absorptance', 'ceiling_u', 'window_u', 'window_shgc',
    'window_pct_of_floor', 'overhang_depth_ft', 'site_shade_fraction', 'ach50', 'ventilation_cfm', 'duct_r',
    'duct_leakage_pct', 'floor_u', 'crawl_wall_r', 'basement_depth_ft', 'basement_wall_r', 'indoor_heating_f',
    'indoor_cooling_f', 'indoor_rh_pct', 'temperature_swing_f', 'design_month', 'ceiling_height_ft', 'aspect_ratio',
    'door_area_ft2', 'door_u', 'occupants', 'rotation_deg', 'window_height_ft', 'overhang_gap_ft', 'roof_pitch',
    'attic_vent_cfm_per_ft2', 'internal_sensible_btuh', 'internal_latent_btuh', 'ventilation_effectiveness',
    'ventilation_latent_effectiveness', 'ground_mean_f', 'ground_amp_f', 'cooling_coil_dt_f', 'flue_fraction',
  ];
  const TEXT = [
    'floor_type', 'ceiling_type', 'roof_color', 'interior_shade', 'insect_screen', 'ventilation_type', 'duct_location',
    'heating_system', 'slab_edge', 'floor_cover', 'construction_mass', 'wall_layers',
  ];
  const WINDOW_SIDES = ['window_area_n', 'window_area_e', 'window_area_s', 'window_area_w'];

  // Which uncertainty term each input confirms.
  const KNOWN_MAP = {
    wall_preset: ['wall_u'], wall_u: ['wall_u'], ceiling_preset: ['ceiling_u'], ceiling_u: ['ceiling_u'],
    window_preset: ['window_u', 'window_shgc'], window_u: ['window_u'], window_shgc: ['window_shgc'],
    window_pct_of_floor: ['window_pct_of_floor'], window_area_n: ['window_pct_of_floor'],
    window_area_e: ['window_pct_of_floor'], window_area_s: ['window_pct_of_floor'],
    window_area_w: ['window_pct_of_floor'], ach50: ['ach50'], duct_leakage_pct: ['duct_leakage_pct'],
    duct_r: ['duct_r'], occupants: ['occupants'], heating_design_f: ['heating_design_f'],
    cooling_design_f: ['cooling_design_f'],
  };
  const ERA_FIELDS = ['wall_preset', 'ceiling_preset', 'window_preset', 'ach50', 'duct_leakage_pct', 'duct_r'];

  const COMPONENTS = [
    ['walls', 'Walls'], ['windows', 'Windows'], ['doors', 'Doors'], ['ceiling', 'Ceiling'], ['floor', 'Floor'],
    ['infiltration', 'Air leakage'], ['ventilation', 'Mechanical ventilation'], ['internal', 'People and appliances'],
    ['ducts', 'Ducts'],
  ];

  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(v)) ? '—'
    : v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  const round100 = (v) => Math.round(v / 100) * 100;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const value = (id) => { const el = $(id); return el ? el.value.trim() : ''; };
  const numberOf = (id) => { const raw = value(id); if (raw === '') return null; const n = Number(raw); return Number.isFinite(n) ? n : NaN; };

  function setValue(id, v) { const el = $(id); if (el) el.value = v === null || v === undefined ? '' : v; }

  // -------------------------------------------------------------- settings
  function loadSettings() {
    try { settings = { ...defaultSettings, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }; }
    catch (e) { settings = { ...defaultSettings }; }
  }
  function saveSettings() { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)); } catch (e) { /* private window */ } }
  function applySettings() {
    document.body.dataset.theme = settings.theme;
    document.body.dataset.density = settings.density;
    document.body.classList.toggle('expert-mode', !!settings.expertMode);
    const toggle = $('expert-mode-toggle');
    if (toggle) toggle.checked = !!settings.expertMode;
    if ($('expert-mode-status')) $('expert-mode-status').textContent = settings.expertMode ? 'On' : 'Off';
    document.querySelectorAll('.settings-panel [data-theme]').forEach((b) => b.classList.toggle('active', b.dataset.theme === settings.theme));
    document.querySelectorAll('.settings-panel [data-density]').forEach((b) => b.classList.toggle('active', b.dataset.density === settings.density));
    chartsDirty = true;
    if (last) renderVisibleCharts();
  }
  function settingsPanel(open) {
    const panel = $('settings-panel'); const overlay = $('settings-overlay');
    panel.classList.toggle('open', open); overlay.classList.toggle('open', open);
    panel.setAttribute('aria-hidden', open ? 'false' : 'true');
    overlay.setAttribute('aria-hidden', open ? 'false' : 'true');
  }
  function bindSettings() {
    $('settings-button').addEventListener('click', () => settingsPanel(true));
    $('settings-close').addEventListener('click', () => settingsPanel(false));
    $('settings-overlay').addEventListener('click', () => settingsPanel(false));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') settingsPanel(false); });
    document.querySelectorAll('.settings-panel [data-theme]').forEach((b) => b.addEventListener('click', () => { settings.theme = b.dataset.theme; saveSettings(); applySettings(); }));
    document.querySelectorAll('.settings-panel [data-density]').forEach((b) => b.addEventListener('click', () => { settings.density = b.dataset.density; saveSettings(); applySettings(); }));
    $('settings-reset').addEventListener('click', () => { settings = { ...defaultSettings }; saveSettings(); applySettings(); });
    $('expert-mode-toggle').addEventListener('change', (e) => { settings.expertMode = e.target.checked; saveSettings(); applySettings(); });
  }

  // ------------------------------------------------------------------ tabs
  function bindTabs() {
    document.querySelectorAll('.step-tabs .tab-link').forEach((btn) => btn.addEventListener('click', () => {
      document.querySelectorAll('.step-tabs .tab-link').forEach((b) => b.classList.toggle('active', b === btn));
      document.querySelectorAll('.step-panel').forEach((p) => p.classList.toggle('active', p.id === 'step-' + btn.dataset.step));
    }));
    document.querySelectorAll('.output-tabs .tab-link').forEach((btn) => btn.addEventListener('click', () => openOutput(btn.dataset.output)));
  }
  function openOutput(name) {
    document.querySelectorAll('.output-tabs .tab-link').forEach((b) => b.classList.toggle('active', b.dataset.output === name));
    document.querySelectorAll('.tool-outputs .tab-content').forEach((t) => { t.style.display = t.id === 'tab-' + name ? 'block' : 'none'; });
    chartsDirty = true;
    renderVisibleCharts();
    if (name === 'background') typeset($('tab-background'));
  }
  const typesetDone = new WeakSet();
  function typeset(el, force) {
    if (!window.MathJax || !MathJax.typesetPromise) { setTimeout(() => typeset(el, force), 400); return; }
    if (!force && typesetDone.has(el)) return;
    typesetDone.add(el);
    MathJax.typesetPromise([el]).catch(() => {});
  }

  // -------------------------------------------------------------- location
  function distanceMiles(lat1, lon1, lat2, lon2) {
    const r = Math.PI / 180;
    const a = Math.sin((lat2 - lat1) * r / 2) ** 2
      + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin((lon2 - lon1) * r / 2) ** 2;
    return 3958.8 * 2 * Math.asin(Math.sqrt(a));
  }
  async function loadZips() {
    if (zipTable) return zipTable;
    const response = await fetch('data/zips.txt');
    if (!response.ok) throw new Error('ZIP table unavailable');
    const text = await response.text();
    zipTable = new Map();
    text.split('\n').forEach((line) => {
      const [zip, lat, lon] = line.split(' ');
      if (zip) zipTable.set(zip, [Number(lat), Number(lon)]);
    });
    return zipTable;
  }
  function stationLabel(s, miles) {
    const place = s.s ? `${s.n}, ${s.s}` : s.n;
    return miles === null ? place : `${place} (${fmt(miles)} mi, ${fmt(s.el)} ft)`;
  }
  async function resolveLocation(applyWeather) {
    const query = value('location_query');
    const select = $('station_id');
    const note = $('station-note');
    note.classList.remove('warn');
    if (!stations.length) { note.textContent = 'Weather data did not load. Enter design conditions on the Details tab.'; note.classList.add('warn'); return; }
    let matches = [];
    let origin = null;
    if (/^\d{5}$/.test(query)) {
      let table = null;
      try { table = await loadZips(); } catch (e) { note.textContent = 'ZIP lookup is unavailable. Try a city name, or enter design conditions on the Details tab.'; note.classList.add('warn'); return; }
      origin = table.get(query);
      if (!origin) { note.textContent = `ZIP ${query} is not in the Census list. Try a nearby ZIP or a city name.`; note.classList.add('warn'); return; }
    } else if (query.length >= 2) {
      const needle = query.toLowerCase();
      const hits = stations.filter((s) => s.n.toLowerCase().includes(needle));
      if (hits.length) origin = [hits[0].la, hits[0].lo];
      else { note.textContent = `No station name contains "${query}". Try a nearby city, a US ZIP, or enter design conditions on the Details tab.`; note.classList.add('warn'); return; }
    } else { note.textContent = 'Enter a ZIP code or a city name.'; return; }
    // A short record is a real weakness, so each missing year counts as 5 extra
    // miles. This prefers a major airport over a nearby part-time or lakefront site.
    const rank = (m) => m.miles + (14 - m.s.yrs) * 5;
    matches = stations
      .map((s) => ({ s, miles: distanceMiles(origin[0], origin[1], s.la, s.lo) }))
      .sort((a, b) => rank(a) - rank(b))
      .slice(0, 6);
    select.innerHTML = matches.map((m) => `<option value="${esc(m.s.id)}">${esc(stationLabel(m.s, m.miles))}</option>`).join('');
    const wanted = select.dataset.wanted;
    if (wanted && matches.some((m) => m.s.id === wanted)) select.value = wanted;
    delete select.dataset.wanted;
    selectStation(select.value, matches, applyWeather);
  }
  function selectStation(id, matches, applyWeather) {
    station = stations.find((s) => s.id === id) || null;
    if (!station) return;
    const match = (matches || []).find((m) => m.s.id === id);
    const miles = match ? match.miles : null;
    const note = $('station-note');
    note.innerHTML = `Winter <strong>${fmt(station.h99)} °F</strong> at 99%, <strong>${fmt(station.h996)} °F</strong> at 99.6%, and about ${fmt(station.lo_typ)} °F in the coldest hours of a typical year. Summer <strong>${fmt(station.c1)} °F</strong> with a ${fmt(station.wb)} °F wet bulb. From ${station.yrs} years of NOAA hourly data.`;
    if (miles !== null && miles > 60) { note.classList.add('warn'); note.innerHTML += ` This station is ${fmt(miles)} miles away, so check that its climate resembles yours.`; }
    if (applyWeather) {
      setValue('heating_design_f', value('design_basis') === '99.6' ? station.h996 : station.h99);
      setValue('cooling_design_f', station.c1);
      setValue('cooling_wet_bulb_f', station.wb);
      setValue('daily_range_f', station.dr);
      setValue('latitude', station.la);
      setValue('elevation_ft', station.el);
      const months = station.tm;
      const mean = months.reduce((a, b) => a + b, 0) / 12;
      setValue('ground_mean_f', mean.toFixed(1));
      setValue('ground_amp_f', ((Math.max(...months) - Math.min(...months)) / 2).toFixed(1));
    }
    updateBillDegreeDays();
  }
  function updateBillDegreeDays() {
    if (!station) return;
    const month = Number(value('bill_month')) || 1;
    setValue('bill_degree_days', station.hdd[month - 1]);
  }

  // ---------------------------------------------------------- preset wiring
  function applyPreset(selectId, table, fields) {
    const key = value(selectId);
    if (key === 'custom' || !table[key]) return;
    Object.entries(fields).forEach(([field, prop]) => setValue(field, table[key][prop]));
    if (selectId === 'wall_preset') setValue('wall_layers', table[key].layers);
  }
  function applyEra() {
    const era = presets.eras[value('era')];
    if (!era) return;
    setValue('wall_preset', era.wall_preset);
    setValue('ceiling_preset', era.ceiling_preset);
    setValue('window_preset', era.window_preset);
    setValue('ach50', era.ach50);
    setValue('duct_leakage_pct', era.duct_leakage_pct);
    setValue('duct_r', era.duct_r);
    setValue('slab_edge', era.slab_edge);
    applyPreset('wall_preset', presets.walls, { wall_u: 'u' });
    applyPreset('ceiling_preset', presets.ceilings, { ceiling_u: 'u' });
    applyPreset('window_preset', presets.windows, { window_u: 'u', window_shgc: 'shgc' });
    ERA_FIELDS.forEach((field) => (KNOWN_MAP[field] || []).forEach((k) => known.delete(k)));
    ['wall_u', 'ceiling_u', 'window_u', 'window_shgc'].forEach((k) => known.delete(k));
  }
  function updateConditional() {
    const floor = value('floor_type');
    document.querySelectorAll('.conditional').forEach((el) => {
      el.hidden = !(el.dataset.floor || '').split(' ').includes(floor);
    });
  }
  function markStale() { if (last) $('stale-note').hidden = false; }

  function bindInputs() {
    const form = $('calc-form');
    form.addEventListener('input', (e) => {
      const id = e.target.id;
      (KNOWN_MAP[id] || []).forEach((k) => known.add(k));
      if (id === 'wall_u') setValue('wall_preset', 'custom');
      if (id === 'ceiling_u') setValue('ceiling_preset', 'custom');
      if (id === 'window_u' || id === 'window_shgc') setValue('window_preset', 'custom');
      markStale();
    });
    $('era').addEventListener('change', applyEra);
    $('wall_preset').addEventListener('change', () => applyPreset('wall_preset', presets.walls, { wall_u: 'u' }));
    $('ceiling_preset').addEventListener('change', () => applyPreset('ceiling_preset', presets.ceilings, { ceiling_u: 'u' }));
    $('window_preset').addEventListener('change', () => applyPreset('window_preset', presets.windows, { window_u: 'u', window_shgc: 'shgc' }));
    $('floor_type').addEventListener('change', updateConditional);
    $('design_basis').addEventListener('change', () => {
      if (station) setValue('heating_design_f', value('design_basis') === '99.6' ? station.h996 : station.h99);
      markStale();
    });
    $('bill_month').addEventListener('change', updateBillDegreeDays);
    $('hp_preset').addEventListener('change', applyHeatPumpPreset);
    $('cooling_rated_tons').addEventListener('change', applyHeatPumpPreset);
    $('equip-suggest').addEventListener('click', suggestHeatPump);
    let locationTimer = null;
    $('location_query').addEventListener('input', () => {
      clearTimeout(locationTimer);
      locationTimer = setTimeout(() => resolveLocation(true), 350);
    });
    $('station_id').addEventListener('change', () => { selectStation(value('station_id'), null, true); markStale(); });
    form.addEventListener('submit', (e) => { e.preventDefault(); calculate(); });
    $('room-add').addEventListener('click', () => { rooms.push(newRoom(`Room ${rooms.length + 1}`)); renderRooms(rooms.length - 1); markStale(); });
    $('room-clear').addEventListener('click', () => { rooms = []; renderRooms(); markStale(); });
    $('room-typical').addEventListener('click', () => { rooms = typicalRooms(); renderRooms(0); markStale(); });
    $('export-csv').addEventListener('click', exportCsv);
    $('export-json').addEventListener('click', exportJson);
    $('import-json').addEventListener('change', importJson);
    $('export-print').addEventListener('click', () => window.print());
  }

  const HP_RATIOS = {
    standard: { r17: 0.62, r5: null, min: null, cop47: 3.3, cop17: 2.2 },
    variable: { r17: 0.72, r5: null, min: 0.35, cop47: 3.6, cop17: 2.4 },
    cold: { r17: 0.95, r5: 0.82, min: 0.25, cop47: 3.8, cop17: 2.6 },
  };
  function applyHeatPumpPreset() {
    const ratios = HP_RATIOS[value('hp_preset')];
    const tons = numberOf('cooling_rated_tons');
    if (!ratios || !tons) return;
    const cap = tons * 12000;
    setValue('hp_cap_47', cap);
    setValue('hp_cap_17', Math.round(cap * ratios.r17));
    setValue('hp_cap_5', ratios.r5 ? Math.round(cap * ratios.r5) : '');
    setValue('hp_min_47', ratios.min ? Math.round(cap * ratios.min) : '');
    setValue('hp_cop_47', ratios.cop47);
    setValue('hp_cop_17', ratios.cop17);
    if (value('cooling_stages') === 'single' && value('hp_preset') !== 'standard') setValue('cooling_stages', 'variable');
    markStale();
  }
  function suggestHeatPump() {
    if (!last) return;
    // Generic cold-climate capacity relative to the 47 °F rating, for choosing a size.
    const design = last.design.heating_f;
    const ratio = design >= 17 ? 0.95 + (Math.min(design, 47) - 17) / 30 * 0.05
      : Math.max(0.82 + (design - 5) / 12 * 0.13, 0.5);
    const sizes = [1, 1.5, 2, 2.5, 3, 3.5, 4, 5];
    const forHeating = sizes.find((t) => t * 12000 * ratio >= last.heating_total) || 5;
    const forCooling = last.sizing.cooling_tons || 5;
    setValue('heating_system', 'heat_pump');
    setValue('cooling_rated_tons', String(Math.max(forHeating, forCooling)));
    setValue('hp_preset', 'cold');
    applyHeatPumpPreset();
    setValue('aux_kw', 0);
    calculate().then(() => {
      // Backup in 5 kW steps, the size electric heat strips are usually sold in.
      const needed = lastEquipment ? lastEquipment.backup_kw_at_design : 0;
      if (needed > 0) {
        setValue('aux_kw', Math.ceil(needed / 5 + 1e-6) * 5);
        return calculate();
      }
      return null;
    }).then(() => openOutput('equip'));
  }

  // ----------------------------------------------------------------- rooms
  const ROOM_TYPES = [['living', 'Living'], ['kitchen', 'Kitchen'], ['bedroom', 'Bedroom'], ['bath', 'Bathroom'], ['office', 'Office'], ['other', 'Other']];
  const SIDES = ['N', 'E', 'S', 'W'];
  function newRoom(name) {
    return { name, type: 'bedroom', area: 150, walls: { N: 0, E: 0, S: 0, W: 0 }, windows: { N: 0, E: 0, S: 0, W: 0 }, door_area: 0, top: true, ground: true };
  }
  function typicalRooms() {
    const area = numberOf('floor_area_ft2') || 2000;
    const stories = Number(value('stories')) || 1;
    const aspect = numberOf('aspect_ratio') || 1.5;
    const basement = value('floor_type') === 'basement_conditioned' ? 1 : 0;
    const footprint = area / (stories + basement);
    const L = Math.sqrt(footprint * aspect);
    const W = footprint / L;
    const windowTotal = (numberOf('window_pct_of_floor') ?? 14) / 100 * area;
    const windowPerSide = windowTotal / 4 / stories;
    const mk = (name, type, share, walls, top, ground, doors = 0) => {
      const sideW = { N: walls.N ? walls.N * L : 0, S: walls.S ? walls.S * L : 0, E: walls.E ? walls.E * W : 0, W: walls.W ? walls.W * W : 0 };
      const win = {};
      SIDES.forEach((side) => { win[side] = Math.round((walls[side] || 0) * windowPerSide); });
      Object.keys(sideW).forEach((k) => { sideW[k] = Math.round(sideW[k]); });
      return { name, type, area: Math.round(share * footprint), walls: sideW, windows: win, door_area: doors, top, ground };
    };
    if (stories === 1) {
      return [
        mk('Living room', 'living', 0.28, { S: 0.6, W: 0.6 }, true, true, 20),
        mk('Kitchen', 'kitchen', 0.15, { N: 0.45, W: 0.4 }, true, true, 20),
        mk('Primary bedroom', 'bedroom', 0.18, { N: 0.4, E: 0.45 }, true, true),
        mk('Bedroom 2', 'bedroom', 0.12, { E: 0.3 }, true, true),
        mk('Bedroom 3', 'bedroom', 0.12, { S: 0.4, E: 0.25 }, true, true),
        mk('Bathroom', 'bath', 0.06, { N: 0.15 }, true, true),
        mk('Hall', 'other', 0.09, {}, true, true),
      ];
    }
    const out = [
      mk('Living room', 'living', 0.45, { S: 0.6, W: 0.6 }, false, true, 20),
      mk('Kitchen', 'kitchen', 0.3, { N: 0.6, W: 0.4 }, false, true, 20),
      mk('Dining', 'other', 0.15, { N: 0.4, E: 0.5 }, false, true),
      mk('Entry and hall', 'other', 0.1, { S: 0.4, E: 0.5 }, false, true),
    ];
    for (let level = 2; level <= stories; level += 1) {
      const top = level === stories;
      const tag = stories > 2 ? ` (level ${level})` : '';
      out.push(mk(`Primary bedroom${tag}`, 'bedroom', 0.35, { N: 0.6, E: 0.5 }, top, false));
      out.push(mk(`Bedroom 2${tag}`, 'bedroom', 0.2, { S: 0.4, E: 0.5 }, top, false));
      out.push(mk(`Bedroom 3${tag}`, 'bedroom', 0.2, { S: 0.6, W: 0.5 }, top, false));
      out.push(mk(`Bathroom${tag}`, 'bath', 0.1, { N: 0.4 }, top, false));
      out.push(mk(`Hall${tag}`, 'other', 0.15, { W: 0.5 }, top, false));
    }
    return out;
  }
  function syncRoomsField() {
    $('rooms_json').value = rooms.length ? JSON.stringify(rooms) : '';
    const total = rooms.reduce((sum, r) => sum + (Number(r.area) || 0), 0);
    const note = $('room-area-note');
    if (!rooms.length) { note.textContent = 'No rooms yet, so the house is treated as one block.'; return; }
    note.textContent = `${rooms.length} rooms, ${fmt(total)} ft². The room table now defines the house, replacing the floor area and window percent. Enter wall length only for walls that face outdoors.`;
  }
  function renderRooms(openIndex) {
    const list = $('room-list');
    list.innerHTML = rooms.map((room, i) => {
      const compass = (kind, label) => `<div>${label}</div>` + SIDES.map((side) => (
        `<input type="number" min="0" step="any" aria-label="${label} ${side}" data-room="${i}" data-kind="${kind}" data-side="${side}" value="${room[kind][side] || ''}">`
      )).join('');
      const options = ROOM_TYPES.map(([v, t]) => `<option value="${v}"${room.type === v ? ' selected' : ''}>${t}</option>`).join('');
      return `<details class="room-card"${i === openIndex ? ' open' : ''}>
        <summary>${esc(room.name)}<span class="room-sub">${fmt(Number(room.area))} ft²</span></summary>
        <div class="room-body">
          <div class="room-grid">
            <div><label for="room-name-${i}">Name</label><input type="text" id="room-name-${i}" data-room="${i}" data-field="name" value="${esc(room.name)}"></div>
            <div><label for="room-type-${i}">Type</label><select id="room-type-${i}" data-room="${i}" data-field="type">${options}</select></div>
            <div><label for="room-area-${i}">Floor area (ft²)</label><input type="number" id="room-area-${i}" min="1" step="any" data-room="${i}" data-field="area" value="${room.area}"></div>
            <div><label for="room-door-${i}">Exterior door (ft²)</label><input type="number" id="room-door-${i}" min="0" step="any" data-room="${i}" data-field="door_area" value="${room.door_area || 0}"></div>
          </div>
          <div class="compass-grid"><div></div>${SIDES.map((s) => `<div class="head">${s}</div>`).join('')}${compass('walls', 'Wall ft')}${compass('windows', 'Glass ft²')}</div>
          <div class="room-flags">
            <label><input type="checkbox" data-room="${i}" data-field="top"${room.top ? ' checked' : ''}> Ceiling exposed</label>
            <label><input type="checkbox" data-room="${i}" data-field="ground"${room.ground ? ' checked' : ''}> Floor exposed</label>
            <button type="button" class="room-remove" data-remove="${i}" aria-label="Remove ${esc(room.name)}">Remove</button>
          </div>
        </div></details>`;
    }).join('');
    syncRoomsField();
  }
  function bindRoomEvents() {
    const list = $('room-list');
    list.addEventListener('input', (e) => {
      const i = Number(e.target.dataset.room);
      if (!Number.isInteger(i) || !rooms[i]) return;
      if (e.target.dataset.kind) rooms[i][e.target.dataset.kind][e.target.dataset.side] = Number(e.target.value) || 0;
      else if (e.target.type === 'checkbox') rooms[i][e.target.dataset.field] = e.target.checked;
      else if (e.target.dataset.field === 'name' || e.target.dataset.field === 'type') rooms[i][e.target.dataset.field] = e.target.value;
      else rooms[i][e.target.dataset.field] = Number(e.target.value) || 0;
      syncRoomsField();
      markStale();
    });
    list.addEventListener('click', (e) => {
      if (e.target.dataset.remove === undefined) return;
      rooms.splice(Number(e.target.dataset.remove), 1);
      renderRooms();
      markStale();
    });
  }

  // ------------------------------------------------------------ calculation
  function collectInputs() {
    const inputs = {};
    NUMERIC.forEach((id) => {
      const n = numberOf(id);
      if (n !== null) inputs[id] = n;
    });
    TEXT.forEach((id) => { inputs[id] = value(id); });
    inputs.radiant_barrier = value('radiant_barrier') === 'true';
    if (WINDOW_SIDES.some((id) => value(id) !== '')) {
      WINDOW_SIDES.forEach((id) => { inputs[id] = numberOf(id) ?? 0; });
    }
    if (rooms.length) inputs.rooms = rooms;
    Object.entries(inputs).forEach(([key, v]) => {
      if (typeof v === 'number' && Number.isNaN(v)) throw new Error(`Check the value entered for ${key.replace(/_/g, ' ')}.`);
    });
    return inputs;
  }
  function showError(message) {
    const box = $('error-box');
    box.textContent = message;
    box.hidden = !message;
  }
  function pyMessage(error) {
    const text = String(error && error.message ? error.message : error);
    const lines = text.trim().split('\n');
    return lines[lines.length - 1].replace(/^\w*Error:\s*/, '');
  }
  function equipmentInputs(result) {
    const payload = {
      heating_load: result.heating_total,
      cooling_sensible: result.cooling_sensible,
      cooling_latent: result.cooling_latent,
      heating_design_f: result.design.heating_f,
      cooling_design_f: result.design.cooling_f,
      indoor_heating_f: result.design.indoor_heating_f,
      internal_gain_btuh: result.cooling.internal_sensible,
      cooling_shr: numberOf('cooling_shr') ?? 0.75,
      cooling_stages: value('cooling_stages'),
      hp_cop_47: numberOf('hp_cop_47') ?? 3.5,
      hp_cop_17: numberOf('hp_cop_17') ?? 2.3,
      aux_kw: numberOf('aux_kw') ?? 0,
    };
    const tons = numberOf('cooling_rated_tons');
    if (tons) payload.cooling_rated_btuh = tons * 12000;
    ['cooling_total_at_design', 'cooling_sensible_at_design', 'hp_cap_47', 'hp_cap_17', 'hp_cap_5', 'hp_min_47', 'hp_lockout_f', 'furnace_output_btuh'].forEach((id) => {
      const n = numberOf(id);
      if (n !== null && !Number.isNaN(n)) payload[id] = n;
    });
    if (station && Math.abs(station.h99 - result.design.heating_f) < 12) {
      payload.bins_start_f = station.b0;
      payload.bins_hours = station.b;
      payload.bin_width_f = binWidth;
    }
    return payload;
  }
  async function calculate() {
    showError('');
    const button = $('calculate-btn');
    button.disabled = true;
    button.textContent = 'Calculating...';
    await new Promise((resolve) => setTimeout(resolve, 20));
    try {
      const inputs = collectInputs();
      const result = py('calculate_hvac_loads', { inputs, known_inputs: Array.from(known), detail: true });
      last = result;
      lastEquipment = py('evaluate_equipment', equipmentInputs(result));
      $('stale-note').hidden = true;
      openRow = null;
      renderAll();
      chartsDirty = true;
      renderVisibleCharts();
    } catch (error) {
      showError(pyMessage(error));
    } finally {
      button.disabled = false;
      button.textContent = 'Calculate';
    }
  }

  // ---------------------------------------------------------------- render
  function renderAll() {
    renderSummary();
    renderBill();
    renderComponents();
    renderTornado();
    renderUpgrades();
    renderDay();
    renderRoomResults();
    renderEquipment();
  }
  function renderSummary() {
    const r = last; const band = r.uncertainty;
    const place = station ? station.n : 'your location';
    const ruleTons = r.floor_area / 500;
    $('summary-sentence').textContent = `This ${fmt(r.floor_area)} ft² house near ${place} loses about ${fmt(round100(r.heating_total))} Btu/h at ${fmt(r.design.heating_f)} °F and needs about ${fmt(r.cooling_tons, 1)} tons of cooling at ${fmt(r.design.cooling_f)} °F. The old 500 ft² per ton rule of thumb would say ${fmt(ruleTons, 1)} tons.`;
    const size = r.sizing;
    const cards = [
      ['Heating load', fmt(round100(r.heating_total)), 'Btu/h', `Range ${fmt(round100(band.heating_low))} to ${fmt(round100(band.heating_high))}. ${fmt(r.heating_total / 3412.14, 1)} kW.`, true],
      ['Cooling load', fmt(round100(r.cooling_total)), 'Btu/h', `Range ${fmt(round100(band.cooling_low))} to ${fmt(round100(band.cooling_high))}. ${fmt(r.cooling_tons, 2)} tons.`, true],
      ['Sensible / latent', `${fmt(round100(r.cooling_sensible))} / ${fmt(round100(r.cooling_latent))}`, '', `Sensible heat ratio ${fmt(r.sensible_heat_ratio, 2)}. Latent is moisture removal.`, false],
      ['Smallest common size', size.cooling_tons ? `${size.cooling_tons} ton` : 'Over 5 tons', '', size.cooling_tons ? `Gives about ${fmt(size.cooling_pct)}% of total and ${fmt(size.cooling_sensible_pct)}% of sensible load here.${size.furnace_output ? ` Furnace output ${fmt(size.furnace_output)} Btu/h.` : ''}` : 'Above the largest common unit, so consider two systems.', false],
      ['Floor area per ton', fmt(r.square_feet_per_ton), 'ft²/ton', 'A higher number is a tighter, smaller load per area.', false],
    ];
    $('results-grid').innerHTML = cards.map(([label, val, unit, note, hi]) => (
      `<div class="result-card${hi ? ' highlight' : ''}"><div class="label">${label}</div><div class="value">${val}${unit ? `<span class="unit">${unit}</span>` : ''}</div><div class="range">${note}</div></div>`
    )).join('');

    const heatSpan = (band.heating_high - band.heating_low) / 2 / r.heating_total * 100;
    const coolSpan = (band.cooling_high - band.cooling_low) / 2 / r.cooling_total * 100;
    const next = band.terms.find((t) => !t.known);
    const nextText = next
      ? ` <strong>${esc(next.label)}</strong> is the largest open question, so pinning it down would narrow the range most.`
      : ' Every major input is confirmed.';
    $('confidence').innerHTML = `With what you have entered, heating is known to about <strong>±${fmt(heatSpan)}%</strong> and cooling to about <strong>±${fmt(coolSpan)}%</strong>.${nextText}`;
  }
  function renderBill() {
    const box = $('bill-result');
    const usage = numberOf('bill_usage');
    if (!usage) { box.innerHTML = ''; return; }
    try {
      const bill = py('bill_check', {
        usage, fuel: value('bill_fuel'), efficiency_pct: numberOf('bill_efficiency_pct') ?? 90,
        degree_days: numberOf('bill_degree_days') ?? 0, heating_design_f: last.design.heating_f,
        baseline_usage: numberOf('bill_baseline') ?? 0,
      });
      const ratio = last.heating_total / bill.measured_design_load;
      const gap = (ratio - 1) * 100;
      let reading;
      if (Math.abs(gap) <= 20) reading = 'They agree within normal bill and weather uncertainty.';
      else if (gap > 0) reading = 'The model is higher than the bill. Inputs may be pessimistic: the house may be tighter or better insulated than assumed, or a thermostat setback, wood stove, or space heater may be reducing fuel use.';
      else reading = 'The bill is higher than the model. Look for more air leakage or duct loss than assumed, an indoor temperature above 70 °F, or an efficiency below the label.';
      box.innerHTML = `<div class="bill-card"><h4>Fuel bill check</h4>Your bill implies a design heat loss of <strong>${fmt(round100(bill.measured_design_load))} Btu/h</strong>, against <strong>${fmt(round100(last.heating_total))} Btu/h</strong> from the model (${gap >= 0 ? '+' : ''}${fmt(gap)}%). ${reading}<div class="deriv-eq" id="bill-eq">\\(${bill.subst_measured_ua}\\,\\text{Btu/h·°F}\\)</div></div>`;
      typeset(box, true);
    } catch (error) {
      box.innerHTML = `<div class="bill-card"><h4>Fuel bill check</h4>${esc(pyMessage(error))}</div>`;
    }
  }
  function renderComponents() {
    const r = last;
    const heat = r.heating.components; const cool = r.cooling.components;
    const maxValue = Math.max(...COMPONENTS.map(([k]) => Math.max(heat[k] || 0, cool[k] || 0)), 1);
    const bar = (v, cls) => {
      const width = Math.max(0, Math.round((v || 0) / maxValue * 70));
      return `<span class="inline-bar ${cls}" style="width:${width}px"></span><span class="num">${v === undefined ? '—' : fmt(v)}</span>`;
    };
    const rows = COMPONENTS.filter(([k]) => Math.abs(heat[k] || 0) > 0.5 || Math.abs(cool[k] || 0) > 0.5).map(([key, label]) => (
      `<tr class="component-row" tabindex="0" role="button" aria-expanded="false" data-key="${key}"><th scope="row">${label}<span class="row-mark" aria-hidden="true">▾</span></th><td class="bar-cell">${bar(heat[key], 'heat')}</td><td class="bar-cell">${bar(cool[key], 'cool')}</td></tr>`
    )).join('');
    const latent = `<tr class="component-row" tabindex="0" role="button" aria-expanded="false" data-key="latent"><th scope="row">Latent (moisture)<span class="row-mark" aria-hidden="true">▾</span></th><td class="bar-cell">—</td><td class="bar-cell">${bar(r.cooling_latent, 'cool')}</td></tr>`;
    $('component-table').innerHTML = `<thead><tr><th scope="col">Source</th><th scope="col">Heating (Btu/h)</th><th scope="col">Cooling (Btu/h)</th></tr></thead>
      <tbody>${rows}${latent}</tbody>
      <tfoot><tr><th scope="row">Total</th><td>${fmt(r.heating_total)}</td><td>${fmt(r.cooling_total)}</td></tr></tfoot>`;
    $('swing-note').textContent = r.derivations.cooling.note;
    document.querySelectorAll('.component-row').forEach((row) => {
      const toggle = () => toggleDerivation(row);
      row.addEventListener('click', toggle);
      row.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
    });
  }
  function toggleDerivation(row) {
    const key = row.dataset.key;
    const existing = document.querySelector('.deriv-row');
    if (existing) {
      existing.previousElementSibling.setAttribute('aria-expanded', 'false');
      existing.remove();
    }
    if (openRow === key) { openRow = null; return; }
    openRow = key;
    row.setAttribute('aria-expanded', 'true');
    const d = last.derivations;
    const blocks = [];
    const block = (title, item) => {
      if (!item) return;
      blocks.push(`<div class="deriv-block"><h5>${title}</h5><div class="deriv-eq">\\(${item.equation}\\)</div><div class="deriv-eq">\\(${item.values}\\)</div><div class="deriv-legend">${esc(item.legend)}</div></div>`);
    };
    block('Heating', d.heating[key]);
    block('Cooling at the peak hour', d.cooling[key]);
    const detail = document.createElement('tr');
    detail.className = 'deriv-row';
    detail.innerHTML = `<td colspan="3">${blocks.join('')}</td>`;
    row.after(detail);
    typeset(detail, true);
  }
  function renderTornado() {
    const band = last.uncertainty;
    const terms = band.terms.slice(0, 6);
    const heatMax = Math.max(...terms.map((t) => Math.max(Math.abs(t.heat_low), Math.abs(t.heat_high))), 1);
    const coolMax = Math.max(...terms.map((t) => Math.max(Math.abs(t.cool_low), Math.abs(t.cool_high))), 1);
    const scale = Math.max(heatMax, coolMax);
    const cell = (low, high, cls) => {
      const left = 50 + low / scale * 50; const right = 50 + high / scale * 50;
      return `<div class="tornado-cell"><div class="tornado-track"><div class="tornado-mid"></div><div class="tornado-bar ${cls}" style="left:${left}%;width:${Math.max(right - left, 0.5)}%"></div></div><div class="tornado-value">${Math.abs(low) < 0.5 && Math.abs(high) < 0.5 ? 'No effect' : `${low < -0.5 ? fmt(low) : '0'} to +${fmt(high)}`}</div></div>`;
    };
    $('tornado').innerHTML = `<div class="tornado-row tornado-head"><div class="tornado-label">Input</div><div>Heating (Btu/h)</div><div>Cooling (Btu/h)</div></div>` + terms.map((t) => (
      `<div class="tornado-row"><div class="tornado-label">${esc(t.label)}${t.known ? '<span class="known">You entered this</span>' : ''}</div>${cell(t.heat_low, t.heat_high, 'heat')}${cell(t.cool_low, t.cool_high, 'cool')}</div>`
    )).join('');
  }
  function renderUpgrades() {
    const rows = last.upgrades.slice(0, 6).map((u) => (
      `<tr><th scope="row">${esc(u.label)}</th><td>${fmt(u.heating_saved)}</td><td>${fmt(u.cooling_saved)}</td></tr>`
    )).join('');
    $('upgrade-table').innerHTML = rows
      ? `<thead><tr><th scope="col">Upgrade</th><th scope="col">Heating saved (Btu/h)</th><th scope="col">Cooling saved (Btu/h)</th></tr></thead><tbody>${rows}</tbody>`
      : '<tbody><tr><td>This house already has the common upgrades.</td></tr></tbody>';
  }
  function renderDay() {
    const c = last.cooling;
    $('hourly-explanation').innerHTML = `<strong>What this shows:</strong> the sensible cooling load each hour with the thermostat held exactly at the setting, stacked by source. Bars below zero are heat leaving through the floor. <strong>Key insight:</strong> the peak of ${fmt(c.fixed_setpoint_peak)} Btu/h falls at solar hour ${c.peak_hour}. The dashed line is the ${fmt(c.room_load)} Btu/h the equipment must supply when the room may drift, because the structure soaks up the difference for a few hours.`;
    const totals = last.orientations.map((o) => o.total);
    const max = Math.max(...totals);
    $('orientation').innerHTML = last.orientations.map((o) => (
      `<div class="orient-row"><div>${o.rotation.toFixed(0)}°</div><div class="orient-track"><div class="orient-bar" style="width:${(o.total / max * 100).toFixed(1)}%"></div></div><div class="orient-value">${fmt(o.total)}</div></div>`
    )).join('');
  }
  function renderRoomResults() {
    const out = $('rooms-output');
    if (!last.rooms.length) {
      out.innerHTML = `<div class="empty-state">No rooms entered, so the house is one block. Open the Rooms tab on the input panel, or <button type="button" class="link-button" id="rooms-go">start from a typical layout</button>. You can then correct each room's walls and glass.</div>`;
      $('rooms-go').addEventListener('click', () => {
        rooms = typicalRooms();
        renderRooms(0);
        document.querySelector('.step-tabs [data-step="rooms"]').click();
        calculate().then(() => openOutput('rooms'));
      });
      return;
    }
    const maxCool = Math.max(...last.rooms.map((r) => r.cooling), 1);
    const maxHeat = Math.max(...last.rooms.map((r) => r.heating), 1);
    const rows = last.rooms.map((r) => (
      `<tr><th scope="row">${esc(r.name)}</th><td>${fmt(r.area)}</td><td class="bar-cell"><span class="inline-bar heat" style="width:${Math.round(r.heating / maxHeat * 50)}px"></span><span class="num">${fmt(r.heating)}</span></td><td class="bar-cell"><span class="inline-bar cool" style="width:${Math.round(r.cooling / maxCool * 50)}px"></span><span class="num">${fmt(r.cooling)}</span></td><td>${r.peak_hour}</td><td>${fmt(r.heating_cfm)}</td><td>${fmt(r.cooling_cfm)}</td></tr>`
    )).join('');
    const sum = (k) => last.rooms.reduce((a, r) => a + r[k], 0);
    const roomPeaks = sum('cooling');
    out.innerHTML = `<div class="table-scroll"><table class="data-table"><thead><tr><th scope="col">Room</th><th scope="col">ft²</th><th scope="col">Heating (Btu/h)</th><th scope="col">Cooling (Btu/h)</th><th scope="col">Peak hour</th><th scope="col">Heating cfm</th><th scope="col">Cooling cfm</th></tr></thead><tbody>${rows}</tbody><tfoot><tr><th scope="row">Sum of rooms</th><td>${fmt(sum('area'))}</td><td>${fmt(sum('heating'))}</td><td>${fmt(roomPeaks)}</td><td></td><td>${fmt(sum('heating_cfm'))}</td><td>${fmt(sum('cooling_cfm'))}</td></tr></tfoot></table></div>
      <div class="chart-explanation"><strong>Reading this table:</strong> each room's cooling is its own peak, whenever it falls, including its share of duct gain. The rooms do not peak together, so their sum is above the ${fmt(last.cooling_sensible)} Btu/h whole-house sensible load. Size the equipment from the whole-house number and size each room's supply air from its row. Airflow assumes a ${fmt(numberOf('cooling_coil_dt_f') ?? 20)} °F cooling air temperature drop.</div>`;
  }
  function renderEquipment() {
    const e = lastEquipment; const r = last;
    const hasAny = e.checks.length > 0;
    $('equip-empty').innerHTML = hasAny ? '' : `<div class="empty-state">Enter a quote on the Equipment input tab to check it. A good starting point for this house is ${r.sizing.cooling_tons ? `${r.sizing.cooling_tons} tons of cooling` : 'more than one system'}${r.sizing.furnace_output ? ` and ${fmt(r.sizing.furnace_output)} Btu/h of furnace output` : ''}.</div>`;
    const verdictEl = $('verdict');
    if (hasAny) {
      const required = e.checks.filter((c) => c.kind === 'required');
      const advisory = e.checks.filter((c) => c.kind === 'advisory');
      const requiredFail = required.filter((c) => !c.ok);
      const advisoryFail = advisory.filter((c) => !c.ok);
      const status = requiredFail.length ? 'fail' : advisoryFail.length ? 'marginal' : 'pass';
      const headline = status === 'pass' ? 'This equipment fits the calculated loads'
        : status === 'marginal' ? 'Meets the loads, with advisory items to review'
          : 'Does not meet a calculated load';
      const checks = {};
      e.checks.forEach((c) => { checks[c.name] = c.ok; });
      window.TransparentVerdict.render(verdictEl, {
        status, headline,
        reasons: requiredFail.concat(advisoryFail).map((c) => `${c.name}: ${c.detail}${c.kind === 'advisory' ? ' (advisory)' : ''}`),
        checks,
      });
    } else verdictEl.innerHTML = '';

    const cards = [];
    if (e.cooling_total_pct !== null) cards.push(['Cooling capacity at design', fmt(e.cooling_capacity_total), 'Btu/h', `${fmt(e.cooling_total_pct)}% of total load. Latent ${fmt(e.cooling_capacity_latent)} Btu/h. Source: ${e.cooling_source}.`]);
    if (e.balance_point_f !== null) cards.push(['Balance point', fmt(e.balance_point_f), '°F', 'Below this the compressor alone cannot keep up.']);
    if (e.backup_kw_at_design !== null) cards.push(['Backup at design', fmt(e.backup_kw_at_design, 1), 'kW', `Heat pump delivers ${fmt(e.hp_pct_of_load_at_design)}% of the load at ${fmt(r.design.heating_f)} °F.`]);
    if (e.heat_pump_energy_share !== null) cards.push(['Heat from the compressor', fmt(e.heat_pump_energy_share * 100), '% of annual heat', `${fmt(e.hours_below_balance)} hours per year need backup.`]);
    if (e.seasonal_cop !== undefined && e.seasonal_cop !== null) cards.push(['Seasonal COP estimate', fmt(e.seasonal_cop, 2), '', `About ${fmt(e.annual_kwh_compressor + e.annual_kwh_backup)} kWh per year, of which ${fmt(e.annual_kwh_backup)} is backup. This uses the typical weather bins and design-day load line, without setbacks or defrost.`]);
    if (e.cycling_hours !== undefined && e.cycling_hours !== null) cards.push(['Hours below minimum output', fmt(e.cycling_hours), 'per year', 'Load is under the lowest speed, so the unit must cycle. An oversized unit raises this.']);
    if (e.furnace_pct !== null) cards.push(['Furnace output', fmt(e.furnace_pct), '% of load', 'Commonly cited upper limit is about 140%.']);
    $('equip-grid').innerHTML = cards.map(([label, val, unit, note]) => (
      `<div class="result-card"><div class="label">${label}</div><div class="value">${val}<span class="unit">${unit}</span></div><div class="range">${note}</div></div>`
    )).join('');

    $('balance-card').hidden = !e.chart;
    $('bins-card').hidden = !(e.chart && station);
    if (e.chart) {
      const balanceText = e.balance_point_f === null ? 'The capacity stays above the load at every temperature shown.'
        : `The lines cross at ${fmt(e.balance_point_f)} °F. Colder than that, backup heat covers the gap.`;
      $('balance-explanation').innerHTML = `<strong>What this shows:</strong> the house's heat loss rises as it gets colder, while heat pump output falls. The load reaches zero near ${fmt(e.t_zero_load_f)} °F, where people and appliances are enough. <strong>Key insight:</strong> ${balanceText}`;
    }
    const rows = e.checks.map((c) => {
      const mark = c.ok ? ['ok', '✓ Pass'] : c.kind === 'required' ? ['bad', '✕ Fail'] : ['warn', '! Review'];
      return `<tr><th scope="row">${esc(c.name)}<div class="cell-note">${c.kind === 'required' ? 'Must meet the load' : /oversized/.test(c.name) ? 'Advisory: commonly cited limit. Check Manual S Section N2.' : 'Advisory'}</div></th><td>${esc(c.detail)}</td><td><span class="status-mark ${mark[0]}">${mark[1]}</span></td></tr>`;
    }).join('');
    $('equip-checks').innerHTML = rows ? `<div class="table-scroll"><table class="data-table"><thead><tr><th scope="col">Check</th><th scope="col">Result</th><th scope="col">Status</th></tr></thead><tbody>${rows}</tbody></table></div>` : '';
  }
  function renderVisibleCharts() {
    if (!last || !window.Plotly) return;
    const visible = (id) => { const el = $(id); return el && el.offsetParent !== null; };
    if (visible('chart-hourly')) {
      window.HvacCharts.hourly($('chart-hourly'), last.cooling);
      window.HvacCharts.temps($('chart-temps'), last.cooling);
    }
    if (lastEquipment && lastEquipment.chart && visible('chart-balance')) {
      window.HvacCharts.balance($('chart-balance'), lastEquipment.chart, lastEquipment, last.design.heating_f);
      if (station && visible('chart-bins')) window.HvacCharts.bins($('chart-bins'), station, binWidth);
    }
    chartsDirty = false;
  }

  // ---------------------------------------------------------------- export
  function download(name, type, text) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const link = document.createElement('a');
    link.href = url; link.download = name;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function csvCell(v) { const s = String(v ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }
  function exportCsv() {
    if (!last) return;
    const r = last;
    const rows = [
      ['HVAC load calculation', 'transparent.tools/tools/hvac-load-calculator'],
      ['Not ACCA-approved software. Review with a qualified designer before buying equipment.'],
      [], ['Result', 'Value', 'Unit'],
      ['Heating load', Math.round(r.heating_total), 'Btu/h'], ['Sensible cooling', Math.round(r.cooling_sensible), 'Btu/h'],
      ['Latent cooling', Math.round(r.cooling_latent), 'Btu/h'], ['Total cooling', Math.round(r.cooling_total), 'Btu/h'],
      ['Cooling', r.cooling_tons.toFixed(2), 'tons'], ['Heat loss coefficient', Math.round(r.heat_loss_coefficient), 'Btu/h per F'],
      ['Heating range low', Math.round(r.uncertainty.heating_low), 'Btu/h'], ['Heating range high', Math.round(r.uncertainty.heating_high), 'Btu/h'],
      ['Cooling range low', Math.round(r.uncertainty.cooling_low), 'Btu/h'], ['Cooling range high', Math.round(r.uncertainty.cooling_high), 'Btu/h'],
      [], ['Component', 'Heating Btu/h', 'Cooling Btu/h'],
    ];
    COMPONENTS.forEach(([k, label]) => rows.push([label, Math.round(r.heating.components[k] || 0), Math.round(r.cooling.components[k] || 0)]));
    rows.push(['Latent', 0, Math.round(r.cooling_latent)], []);
    if (r.rooms.length) {
      rows.push(['Room', 'ft2', 'Heating Btu/h', 'Cooling Btu/h', 'Peak solar hour', 'Heating cfm', 'Cooling cfm']);
      r.rooms.forEach((room) => rows.push([room.name, room.area, Math.round(room.heating), Math.round(room.cooling), room.peak_hour, Math.round(room.heating_cfm), Math.round(room.cooling_cfm)]));
      rows.push([]);
    }
    rows.push(['Solar hour', 'Outdoor F', 'Attic F', 'Sensible load Btu/h']);
    r.cooling.hours.forEach((hour, i) => rows.push([hour, r.cooling.t_out[i].toFixed(1), r.cooling.t_attic[i].toFixed(1), Math.round(r.cooling.hourly_fixed[i])]));
    rows.push([], ['Input', 'Value']);
    Object.entries(collectInputs()).forEach(([k, v]) => { if (k !== 'rooms') rows.push([k, v]); });
    download('hvac-load-calculation.csv', 'text/csv', rows.map((row) => row.map(csvCell).join(',')).join('\n'));
  }
  function allFieldIds() {
    return Array.from(document.querySelectorAll('#calc-form input[id], #calc-form select[id]'))
      .filter((el) => !el.dataset.room && el.id !== 'rooms_json').map((el) => el.id);
  }
  function exportJson() {
    const data = { fields: {}, rooms, known: Array.from(known), station_id: value('station_id') };
    allFieldIds().forEach((id) => { data.fields[id] = $(id).value; });
    download('hvac-load-inputs.json', 'application/json', JSON.stringify(data, null, 2));
  }
  function importJson(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const data = JSON.parse(reader.result);
        // Saved files hold form fields. Test cases hold engine inputs by the same names.
        const fields = data.fields || data;
        if (!data.fields) {
          // A test case lists only what differs, so start it from a clean form.
          allFieldIds().forEach((id) => {
            const el = $(id);
            if (el.tagName === 'SELECT') {
              const preset = Array.from(el.options).find((o) => o.defaultSelected);
              if (preset && id !== 'station_id') el.value = preset.value;
            } else if (id !== 'location_query') el.value = el.defaultValue;
          });
        }
        Object.entries(fields).forEach(([id, v]) => {
          if ($(id) && id !== 'station_id' && id !== 'rooms' && typeof v !== 'object') $(id).value = v;
        });
        if (!data.fields) {
          ['wall_preset', 'ceiling_preset', 'window_preset'].forEach((id) => setValue(id, 'custom'));
          Object.keys(data).forEach((key) => (KNOWN_MAP[key] || []).forEach((k) => known.add(k)));
        }
        rooms = Array.isArray(data.rooms) ? data.rooms : [];
        if (data.fields) known.clear();
        (data.known || []).forEach((k) => known.add(k));
        renderRooms();
        updateConditional();
        if (data.station_id) $('station_id').dataset.wanted = data.station_id;
        if (data.fields) await resolveLocation(false);
        calculate();
      } catch (error) {
        showError('That file could not be read as saved inputs.');
      }
      event.target.value = '';
    };
    reader.readAsText(file);
  }

  // ------------------------------------------------------------------ start
  function populateTooltips(docs) {
    document.querySelectorAll('.tooltip-trigger[data-tooltip="Loading..."]').forEach((tip) => {
      const group = tip.closest('.input-group');
      const input = group && group.querySelector('input, select');
      const text = input && docs[input.id];
      tip.setAttribute('data-tooltip', text || 'See the Background tab for how this input is used.');
    });
  }
  function restoreFromUrl() {
    const params = new URLSearchParams(window.location.search);
    params.forEach((_, key) => (KNOWN_MAP[key] || []).forEach((k) => known.add(k)));
    if (value('rooms_json')) {
      try { rooms = JSON.parse(value('rooms_json')); } catch (e) { rooms = []; }
    }
    return params;
  }
  async function main() {
    const loadingText = $('loading-text');
    loadSettings();
    applySettings();
    bindSettings();
    bindTabs();
    try {
      loadingText.textContent = 'Loading the calculator...';
      const pyodide = await loadPyodide();
      loadingText.textContent = 'Loading the load model...';
      const [utilsCode, moduleCode] = await Promise.all([
        fetch('../../pycalcs/utils.py').then((r) => r.text()),
        fetch('../../pycalcs/hvac_loads.py').then((r) => r.text()),
      ]);
      pyodide.FS.writeFile('utils.py', utilsCode);
      pyodide.FS.writeFile('hvac_loads.py', moduleCode);
      pyodide.runPython(`
import json
import utils
import hvac_loads

def _call(name, payload):
    return json.dumps(getattr(hvac_loads, name)(**json.loads(payload)))

def _docs():
    merged = {}
    for name in ("bill_check", "evaluate_equipment", "calculate_hvac_loads"):
        doc = utils.get_documentation("hvac_loads", name)
        merged.update(doc.get("parameters", {}))
    return json.dumps(merged)

def _presets():
    return json.dumps(hvac_loads.get_presets())
`);
      const callPy = pyodide.globals.get('_call');
      py = (name, payload) => JSON.parse(callPy(name, JSON.stringify(payload)));
      presets = JSON.parse(pyodide.globals.get('_presets')());
      populateTooltips(JSON.parse(pyodide.globals.get('_docs')()));

      loadingText.textContent = 'Loading weather stations...';
      try {
        const climate = await fetch('data/stations.json').then((r) => { if (!r.ok) throw new Error('missing'); return r.json(); });
        stations = climate.stations;
        binWidth = climate.bin_width_f;
      } catch (e) {
        stations = [];
      }

      const params = restoreFromUrl();
      renderRooms();
      bindRoomEvents();
      bindInputs();
      updateConditional();
      const wantedStation = params.get('station_id');
      if (wantedStation) $('station_id').dataset.wanted = wantedStation;
      await resolveLocation(!params.has('heating_design_f'));
      window.addEventListener('resize', () => { chartsDirty = true; });

      await calculate();
      $('loading-overlay').classList.add('hidden');
    } catch (error) {
      loadingText.textContent = 'The calculator could not load: ' + error.message;
      console.error(error);
    }
  }
  if (document.readyState === 'complete') main();
  else window.addEventListener('load', main);
})();
