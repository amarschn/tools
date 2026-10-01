/* Chart controls and presentation. Property pairing and index calculations
   are generated from the Materials release by pycalcs/material_selection.py. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const PRESETS = [
    { label: 'E vs ρ', x: 'density', y: 'youngs_modulus', index: 'stiff_light_beam' },
    { label: 'Yield vs ρ', x: 'density', y: 'tensile_yield_strength', index: 'strong_light_tie' },
    { label: 'UTS vs ρ', x: 'density', y: 'ultimate_tensile_strength', index: '' },
    { label: 'k vs ρ', x: 'density', y: 'thermal_conductivity', index: 'heat_spreading_mass' },
    { label: 'Heat capacity', x: 'density', y: 'specific_heat', index: 'thermal_storage_vol' },
  ];
  const FAMILY_NAMES = { metal: 'Metals', polymer: 'Polymers', ceramic: 'Ceramics' };
  const VIEW_IDS = ['x-prop', 'y-prop', 'perf-index', 'top-n', 'temperature-filter', 'basis-filter', 'material-search'];
  const DISPLAY_IDS = ['setting-blobs', 'setting-points', 'setting-ranges', 'setting-isolines', 'setting-labels'];
  const initialParams = new URLSearchParams(location.search);
  let DB, chart, rows = [], families = new Set(), selected = null, rendering = 0;
  let settings = { theme: 'system', density: 'comfortable', precision: 3 };
  try { settings = { ...settings, ...JSON.parse(localStorage.getItem('materials-explorer-settings') || '{}') }; } catch { /* Session settings remain usable. */ }
  if (!['light', 'dark', 'system'].includes(settings.theme)) settings.theme = 'system';
  if (!['compact', 'comfortable'].includes(settings.density)) settings.density = 'comfortable';
  if (![2, 3, 4].includes(Number(settings.precision))) settings.precision = 3;

  function applySettings() {
    document.body.dataset.theme = settings.theme;
    document.body.dataset.density = settings.density;
    $('setting-density').value = settings.density;
    $('setting-precision').value = settings.precision;
    document.querySelectorAll('#theme-control button').forEach(button => {
      button.classList.toggle('active', button.dataset.theme === settings.theme);
      button.setAttribute('aria-pressed', String(button.dataset.theme === settings.theme));
    });
    try { localStorage.setItem('materials-explorer-settings', JSON.stringify(settings)); } catch { /* Use session settings. */ }
  }
  const dark = () => settings.theme === 'dark' || (settings.theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
  const precise = value => Number(value).toPrecision(Number(settings.precision));
  function display(value, property) {
    const meta = DB.property_registry[property];
    const unit = meta.display_unit;
    return precise(value * meta.display_multiplier) + (unit ? ' ' + unit : '');
  }
  function resultText(observation) {
    const c = observation.result.canonical, property = observation.property_id;
    if (observation.result.kind === 'interval') return display(c.minimum, property) + ' to ' + display(c.maximum, property);
    const sign = { lower_bound: '≥ ', upper_bound: '≤ ' }[observation.result.kind] || '';
    return sign + display(c.value, property);
  }
  function conditionText(conditions) {
    return Object.entries(conditions).map(([key, value]) => {
      if (key === 'temperature_K') return precise(value - 273.15) + ' °C';
      if (key === 'thickness_m') {
        const lo = value.minimum == null ? 'unspecified' : precise(value.minimum * 1000);
        const hi = value.maximum == null ? 'unspecified' : precise(value.maximum * 1000);
        return `thickness ${lo} to ${hi} mm`;
      }
      return String(value).replaceAll('_', ' ');
    }).join(' · ') || 'Conditions not stated';
  }
  function sourceText(observation) {
    const source = DB.sources[observation.source_id];
    return [source?.organization, source?.title, source?.revision, observation.source_locator.label].filter(Boolean).join('. ');
  }
  function scoreBasis(row) {
    if (row.hasBounds) return 'uses a specified bound';
    if (row.observations.some(o => o.result.kind === 'interval')) return 'uses an interval midpoint';
    return row.observations.map(o => o.basis).filter((value, i, all) => all.indexOf(value) === i).join(' / ');
  }
  function plotProperty(observation) {
    const result = { value: observation.plot_value, kind: observation.result.kind, basis: observation.basis, label: resultText(observation) };
    if (observation.result.kind === 'interval') Object.assign(result, { min: observation.result.canonical.minimum, max: observation.result.canonical.maximum });
    return result;
  }
  function chartData() {
    return DB.charts[[$('x-prop').value, $('y-prop').value].sort().join('|')];
  }
  function populateIndices(preferred = $('perf-index').value) {
    $('perf-index').replaceChildren(new Option('(none)', ''));
    for (const id of chartData().indices) {
      const index = DB.indices[id];
      $('perf-index').appendChild(new Option(index.name + ' (' + index.expression + ')', id));
    }
    $('perf-index').value = chartData().indices.includes(preferred) ? preferred : '';
  }
  function toRow(point) {
    const material = DB.materials[point.material_id], state = DB.states[point.state_id];
    const observations = point.observations.map(id => DB.observations[id]);
    const row = {
      ...material, id: point.id, material_id: material.id, state_id: point.state_id,
      name: material.name + (state ? ' · ' + state.name : ''),
      conditions: point.conditions, condition: conditionText(point.conditions),
      observations, scores: point.scores, isolines: point.isolines || {},
      hasBounds: observations.some(o => ['lower_bound', 'upper_bound'].includes(o.result.kind)),
    };
    for (const observation of observations) row[observation.property_id] = plotProperty(observation);
    return row;
  }
  function filteredRows() {
    const query = $('material-search').value.trim().toLocaleLowerCase();
    return chartData().points.map(toRow).filter(row => {
      if (!families.has(row.family)) return false;
      const temperature = row.conditions.temperature_K;
      if ($('temperature-filter').value === 'ambient' && temperature != null && (temperature < 293.15 || temperature > 298.15)) return false;
      if ($('basis-filter').value === 'measured' && row.hasBounds) return false;
      if ($('basis-filter').value === 'limits' && !row.hasBounds) return false;
      const searchable = [row.name, row.family, row.sub_family, ...row.aliases, ...row.designations.map(d => d.value)].join(' ').toLocaleLowerCase();
      return !query || searchable.includes(query);
    });
  }
  function shareUrl() {
    const url = new URL(location.href);
    url.search = '';
    for (const id of VIEW_IDS) if ($(id).value !== '') url.searchParams.set(id, $(id).value);
    // An explicit empty index must survive restoration of the default preset.
    url.searchParams.set('perf-index', $('perf-index').value);
    for (const id of DISPLAY_IDS) url.searchParams.set(id, $(id).checked ? '1' : '0');
    url.searchParams.set('families', [...families].sort().join(','));
    if (selected) url.searchParams.set('point', selected.id);
    return url;
  }
  function syncUrl() {
    try { history.replaceState(null, '', shareUrl()); } catch { /* File previews may restrict history. */ }
  }
  function showCard(row) {
    selected = row;
    $('card-name').textContent = row.name;
    $('card-meta').textContent = row.sub_family + ' · ' + row.condition;
    const observations = [...new Map(row.observations.map(o => [o.id, o])).values()];
    $('card-props').innerHTML = observations.map(observation => {
      const scope = observation.state_id ? DB.states[observation.state_id].name : 'Grade-level value';
      const kind = observation.result.kind.replaceAll('_', ' ');
      return `<tr><th>${h(DB.property_registry[observation.property_id].label)}</th><td>${h(resultText(observation))}<span class="result-kind">${h(kind)} · ${h(observation.basis)}</span><span class="source-detail">${h(scope)}. ${h(conditionText(observation.conditions))}. ${h(observation.test_method.reported_label)}</span><span class="source-detail">${h(sourceText(observation))}</span></td></tr>`;
    }).join('');
    const indexId = $('perf-index').value;
    $('card-index').textContent = '';
    if (indexId && row.scores[indexId] != null) {
      const index = DB.indices[indexId];
      let substitution = index.expression;
      for (const variable of index.variables) substitution = substitution.replaceAll(variable.symbol, '(' + precise(row[variable.property].value) + ')');
      $('card-index').textContent = `M = ${index.expression} = ${substitution} = ${precise(row.scores[indexId])} using SI values; ${scoreBasis(row)}.`;
    }
    const target = new URL('../materials/', document.baseURI);
    target.searchParams.set('material', row.material_id);
    if (row.state_id) target.searchParams.set('state', row.state_id);
    $('card-datasheet').href = target.href;
    $('detail-card').classList.add('visible');
    syncUrl();
  }
  async function updateChart() {
    if (!DB) return;
    const version = ++rendering;
    $('explorer-main').dataset.state = 'updating';
    const x = $('x-prop').value, y = $('y-prop').value, indexId = $('perf-index').value;
    const index = DB.indices[indexId];
    const count = Math.max(1, Math.min(20, Math.round(Number($('top-n').value) || 5)));
    $('top-n').value = count;
    rows = filteredRows();
    const ranked = index ? rows.filter(row => Number.isFinite(row.scores[indexId])).sort((a, b) => (index.maximize ? -1 : 1) * (a.scores[indexId] - b.scores[indexId]) || a.name.localeCompare(b.name)).slice(0, count) : [];
    const available = new Set(chartData().points.map(p => p.material_id)).size;
    const shown = new Set(rows.map(row => row.material_id)).size;
    $('data-status').textContent = `Materials database: ${shown} of ${DB.counts.materials} grades shown · ${rows.length} property pairs. ${DB.counts.materials - available} grades lack a compatible pair for these axes.`;
    $('empty-state').hidden = rows.length > 0;
    $('export-csv').disabled = rows.length === 0;
    $('index-hint').textContent = chartData().indices.length ? 'Available indices use these two properties.' : 'No ranking index is defined for this property pair.';
    document.querySelectorAll('.preset-chip').forEach((button, i) => button.classList.toggle('active', PRESETS[i].x === x && PRESETS[i].y === y && PRESETS[i].index === indexId));
    $('ranking-section').classList.toggle('visible', ranked.length > 0);
    $('ranking-body').replaceChildren();
    if (index) {
      $('ranking-title').textContent = `Top ${ranked.length}: ${index.name}`;
      $('index-equation').textContent = 'Equation (1): M = ' + index.expression;
      $('index-variables').textContent = 'M: reference index; ' + index.variables.map(variable => {
        const meta = DB.property_registry[variable.property];
        return variable.symbol + ': ' + meta.label + (meta.unit ? ' (' + meta.unit + ')' : '');
      }).join('; ') + '.';
      $('index-derivation').textContent = index.derivation;
      $('index-scope').textContent = index.scope;
      $('index-source').textContent = index.source;
      ranked.forEach((row, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td class="rank-num">${i + 1}</td><td><button type="button" class="material-button">${h(row.name)}</button><span class="source-detail">${h(row.condition)}</span></td><td>${h(FAMILY_NAMES[row.family] || row.family)}</td><td>${h(precise(row.scores[indexId]))}<span class="source-detail">${h(scoreBasis(row))}</span></td>`;
        tr.querySelector('button').addEventListener('click', () => showCard(row));
        $('ranking-body').appendChild(tr);
      });
    }
    let lines = [];
    if (index && $('setting-isolines').checked) {
      const chosen = [ranked[0], ranked[Math.floor(ranked.length / 2)], ranked[ranked.length - 1]].filter(Boolean);
      lines = [...new Map(chosen.map(row => [row.scores[indexId], row])).values()].flatMap(row => {
        const points = row.isolines[indexId];
        if (!points) return [];
        return [{ points: points.map(pair => index.x === x ? pair : [pair[1], pair[0]]), label: 'M = ' + precise(row.scores[indexId]) }];
      });
    }
    if (selected) {
      const fresh = rows.find(row => row.id === selected.id);
      if (fresh) showCard(fresh);
      else { selected = null; $('detail-card').classList.remove('visible'); }
    }
    syncUrl();
    await chart.update(rows, DB.property_registry, {
      xProp: x, yProp: y, families: [...families], highlightIds: ranked.map(row => row.id),
      showRanges: $('setting-ranges').checked, showBlobs: $('setting-blobs').checked,
      showPoints: $('setting-points').checked, showLabels: $('setting-labels').checked,
      isolines: { lines }, dark: dark(),
    });
    if (version === rendering) $('explorer-main').dataset.state = 'ready';
  }
  function redraw() { updateChart().catch(showError); }
  function applyPreset(preset) {
    $('x-prop').value = preset.x;
    $('y-prop').value = preset.y;
    populateIndices(preset.index);
    redraw();
  }
  function buildControls() {
    const properties = Object.entries(DB.property_registry).sort((a, b) => a[1].label.localeCompare(b[1].label));
    for (const id of ['x-prop', 'y-prop']) {
      $(id).replaceChildren();
      for (const [key, meta] of properties) $(id).appendChild(new Option(meta.label + (meta.unit ? ` (${meta.unit})` : ''), key));
    }
    $('x-prop').value = 'density';
    $('y-prop').value = 'youngs_modulus';
    for (const id of ['x-prop', 'y-prop']) if (DB.property_registry[initialParams.get(id)]) $(id).value = initialParams.get(id);
    populateIndices(initialParams.has('perf-index') ? initialParams.get('perf-index') : 'stiff_light_beam');
    for (const id of ['top-n', 'temperature-filter', 'basis-filter', 'material-search']) {
      const value = initialParams.get(id);
      if (value == null) continue;
      if ($(id).tagName === 'SELECT' && ![...$(id).options].some(option => option.value === value)) continue;
      $(id).value = value;
    }
    for (const id of DISPLAY_IDS) if (initialParams.has(id)) $(id).checked = initialParams.get(id) === '1';
    families = new Set(Object.values(DB.materials).map(material => material.family));
    if (initialParams.has('families')) families = new Set(initialParams.get('families').split(',').filter(family => families.has(family)));
    $('family-toggles').replaceChildren();
    for (const family of [...new Set(Object.values(DB.materials).map(material => material.family))].sort()) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'family-pill';
      button.dataset.family = family;
      button.textContent = FAMILY_NAMES[family] || family;
      const reflect = () => { button.classList.toggle('active', families.has(family)); button.setAttribute('aria-pressed', String(families.has(family))); };
      reflect();
      button.addEventListener('click', () => { if (families.has(family)) families.delete(family); else families.add(family); reflect(); redraw(); });
      $('family-toggles').appendChild(button);
    }
    $('preset-chips').replaceChildren();
    PRESETS.forEach(preset => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'preset-chip'; button.textContent = preset.label;
      button.addEventListener('click', () => applyPreset(preset));
      $('preset-chips').appendChild(button);
    });
  }
  function showError(error) {
    $('explorer-main').dataset.state = 'error';
    $('loading-message').textContent = 'Could not load the material chart. ' + error.message;
    $('retry-load').hidden = false;
    $('loading-overlay').hidden = false;
  }
  async function init() {
    $('loading-overlay').hidden = false;
    $('retry-load').hidden = true;
    $('loading-message').textContent = 'Loading material properties…';
    try {
      const json = async url => {
        const response = await fetch(url, { cache: 'no-cache' });
        if (!response.ok) throw new Error(`Data request failed (${response.status}).`);
        return response.json();
      };
      const [data, manifest] = await Promise.all([json('../../data/materials/selection.json'), json('../materials/release-manifest.json')]);
      if (data.schema_version !== 1 || data.source_build_id !== manifest.build_id) throw new Error('The material data versions differ. Reload to update.');
      DB = data;
      chart ||= new AshbyPlot('ashby-chart', { onClick: showCard });
      buildControls();
      await updateChart();
      const restored = rows.find(row => row.id === initialParams.get('point'));
      if (restored) showCard(restored);
      $('loading-overlay').hidden = true;
    } catch (error) { showError(error); }
  }
  function settingsPanel(open) {
    $('settings-panel').classList.toggle('open', open);
    $('settings-overlay').classList.toggle('open', open);
    $('settings-panel').setAttribute('aria-hidden', String(!open));
    $('settings-panel').inert = !open;
    (open ? $('settings-close') : $('settings-button')).focus();
  }
  $('settings-button').addEventListener('click', () => settingsPanel(true));
  $('settings-close').addEventListener('click', () => settingsPanel(false));
  $('settings-overlay').addEventListener('click', () => settingsPanel(false));
  document.addEventListener('keydown', event => {
    if ($('settings-panel').getAttribute('aria-hidden') === 'true') return;
    if (event.key === 'Escape') settingsPanel(false);
    if (event.key === 'Tab') {
      const controls = [...$('settings-panel').querySelectorAll('button, select')];
      if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1).focus(); }
      else if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0].focus(); }
    }
  });
  document.querySelectorAll('#theme-control button').forEach(button => button.addEventListener('click', () => { settings.theme = button.dataset.theme; applySettings(); redraw(); }));
  $('setting-density').addEventListener('change', () => { settings.density = $('setting-density').value; applySettings(); redraw(); });
  $('setting-precision').addEventListener('change', () => { settings.precision = Number($('setting-precision').value); applySettings(); redraw(); });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redraw);
  for (const id of ['x-prop', 'y-prop']) $(id).addEventListener('change', () => { if (DB) { populateIndices(); redraw(); } });
  for (const id of [...VIEW_IDS.slice(2, -1), ...DISPLAY_IDS]) $(id).addEventListener('change', redraw);
  $('material-search').addEventListener('input', redraw);
  $('card-close').addEventListener('click', () => { selected = null; $('detail-card').classList.remove('visible'); $('material-search').focus(); syncUrl(); });
  $('retry-load').addEventListener('click', init);
  $('copy-link').addEventListener('click', async () => {
    if (!DB) return;
    try { await navigator.clipboard.writeText(shareUrl().href); $('copy-link').textContent = 'Copied'; }
    catch { $('copy-link').textContent = 'Copy address bar link'; }
    setTimeout(() => { $('copy-link').textContent = 'Copy link'; }, 2200);
  });
  $('export-csv').addEventListener('click', () => {
    if (!rows.length) return;
    const x = $('x-prop').value, y = $('y-prop').value, indexId = $('perf-index').value;
    const columns = ['observation', 'property', 'value (SI)', 'unit', 'kind', 'minimum', 'maximum', 'basis', 'state', 'conditions', 'test method', 'source'];
    const header = ['Material', 'State', 'Conditions', ...columns.map(name => 'X ' + name), ...columns.map(name => 'Y ' + name), 'Index', 'Reference score', 'Materials build'];
    const fields = observation => [observation.id, observation.property_id, observation.plot_value, observation.result.canonical.unit, observation.result.kind, observation.result.canonical.minimum ?? '', observation.result.canonical.maximum ?? '', observation.basis, DB.states[observation.state_id]?.name || 'Grade-level value', conditionText(observation.conditions), observation.test_method.reported_label, sourceText(observation)];
    const records = rows.map(row => [DB.materials[row.material_id].name, DB.states[row.state_id]?.name || '', conditionText(row.conditions), ...fields(row.observations.find(o => o.property_id === x)), ...fields(row.observations.find(o => o.property_id === y)), indexId, row.scores[indexId] ?? '', DB.source_build_id]);
    const csv = [header, ...records].map(record => record.map(value => '"' + String(value).replaceAll('"', '""') + '"').join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'materials-ashby.csv'; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  applySettings();
  window.MaterialsExplorer = { getData: () => DB, getRows: () => rows, showCard, getShareUrl: () => shareUrl().href };
  init();
})();
