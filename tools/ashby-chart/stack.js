/* The selection stack and the design brief. A brief sets the axes and index and adds a
   line stage, so both share one filter chain. */
const { Axis, runStages, parseQuery, formatValue, clamp, FAMILY_COLORS, FAMILY_NAMES } = window.AshbyEngine;

/* Each entry names a published performance index, so its equation and source come from the build. */
const BRIEFS = {
  'tie (rod in tension)': { stiff: 'stiff_light_tie', strong: 'strong_light_tie' },
  'beam (in bending)': { stiff: 'stiff_light_beam', strong: 'strong_light_beam' },
  'plate or panel': { stiff: 'stiff_light_plate', strong: 'strong_light_plate' },
};
const DRIVERS = { stiff: 'stiff enough', strong: 'strong enough' };

export function setupStack(ctx) {
  const { $, el, options, cssVar, db, state, tags } = ctx;
  const num = v => (Number.isFinite(v) ? v : null);
  const propOptions = db.props.map(p => [p.symbol, p.display_unit ? `${p.label} (${p.display_unit})` : p.label]);
  const hint = 'Symbols: ' + db.props.map(p => p.symbol).join(' ') + ', or a formula like E^0.5/rho > 0.002';
  const symbolOf = id => db.props.find(p => p.id === id).symbol;
  const refresh = (...args) => ctx.refresh(...args);

  $('query-msg').textContent = hint;
  $('query-form').onsubmit = e => {
    e.preventDefault();
    const input = $('query'), msg = $('query-msg');
    try { ctx.stages.push(parseQuery(db, input.value)); input.value = ''; msg.textContent = hint; msg.classList.remove('bad'); refresh(); }
    catch (error) { msg.textContent = error.message; msg.classList.add('bad'); }
  };
  $('query').addEventListener('keydown', e => e.stopPropagation());
  $('add').append(...[
    ['Family', () => ({ type: 'family', values: Object.keys(FAMILY_NAMES), enabled: true })],
    ['Limit', () => ({ type: 'limit', expr: 'UTS', min: null, max: null, enabled: true })],
    ['Class', () => ({ type: 'class', values: [], enabled: true })],
    ['Source', () => ({ type: 'org', values: [], enabled: true })],
    ['Tag', () => ({ type: 'tag', value: tags.names()[0] || '', enabled: true })],
    ['Search', () => ({ type: 'text', value: '', enabled: true })],
  ].map(([label, make]) => el('button', { type: 'button', onclick: () => { ctx.stages.push(make()); refresh(); } }, '+ ' + label)),
  el('button', { type: 'button', id: 'add-region', title: 'Drag on the chart to add a region', onclick: () => ctx.startRegion() }, '+ Region'),
  el('button', { type: 'button', id: 'add-line', title: 'Add a dashed line you can drag on the chart', onclick: addLine }, '+ Line'));

  function addLine() {
    ctx.setView('chart');
    if (!state.xLog || !state.yLog) { $('query-msg').textContent = 'A selection line needs log scales on both axes.'; $('query-msg').classList.add('bad'); return; }
    const xProp = db.bySym[state.x]?.id, yProp = db.bySym[state.y]?.id;
    const known = Object.values(db.indices).find(i => i.x === xProp && i.y === yProp && i.slope);
    const slope = known ? known.slope : 1, v = ctx.plot.view;
    ctx.stages.push({ type: 'index', x: state.x, y: state.y, slope, c: (v.y0 + v.y1) / 2 - slope * (v.x0 + v.x1) / 2, above: true, enabled: true });
    refresh();
  }
  function stageTitle(s) {
    switch (s.type) {
      case 'family': return 'Family: ' + (s.values.length === Object.keys(FAMILY_NAMES).length ? 'all' : s.values.map(v => FAMILY_NAMES[v]).join(', ') || 'none');
      case 'limit': {
        const axis = new Axis(db, s.expr, false);
        const parts = [s.min != null ? `≥ ${formatValue(s.min)}` : '', s.max != null ? `≤ ${formatValue(s.max)}` : ''].filter(Boolean).join(' and ');
        return `${axis.short} ${parts || '(any)'}${axis.prop && parts && axis.prop.display_unit ? ' ' + axis.prop.display_unit : ''}`;
      }
      case 'class': return 'Class: ' + (s.values.join(', ') || 'choose');
      case 'org': return 'Source: ' + (s.values.join(', ') || 'choose');
      case 'tag': return 'Tag: ' + (s.value || 'choose');
      case 'text': return 'Search: ' + (s.value || 'type');
      case 'region': return `Region on ${new Axis(db, s.y).short} vs ${new Axis(db, s.x).short}`;
      case 'index': return s.brief ? 'Brief: beats the index line' : `${s.above ? 'Above' : 'Below'} line, slope ${s.slope}`;
      default: return s.type;
    }
  }
  const rowsBefore = s => runStages(db, ctx.stages.slice(0, ctx.stages.indexOf(s)), ctx.baseRows(), ctx.stageContext()).rows;
  function histogram(s, inputs) {
    const base = new Axis(db, s.expr, true), allow = ctx.allow();
    const before = rowsBefore(s);
    // One count per observation, so a material with several rows is not counted several times.
    const seen = new Set(), values = [];
    for (const row of before) {
      const v = base.value(row, allow);
      if (!Number.isFinite(v)) continue;
      const key = base.used.map(p => row.obs[p]).join(':');
      if (!seen.has(key)) { seen.add(key); values.push(v); }
    }
    const wrap = el('div', { class: 'hist' }), canvas = el('canvas');
    wrap.append(canvas);
    if (values.length < 2) return wrap;
    const lo = Math.log10(Math.min(...values)), hi = Math.log10(Math.max(...values)) + 1e-6, bins = 44;
    const counts = new Array(bins).fill(0);
    values.forEach(v => { counts[Math.min(bins - 1, Math.floor((Math.log10(v) - lo) / (hi - lo) * bins))]++; });
    const peak = Math.max(...counts);
    const position = v => (v > 0 ? (Math.log10(v) - lo) / (hi - lo) : 0);
    const paint = () => {
      const w = wrap.clientWidth || 300, h = 50, dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = w * dpr; canvas.height = h * dpr;
      const c = canvas.getContext('2d'); c.scale(dpr, dpr);
      const a = s.min != null ? position(s.min) : 0, b = s.max != null ? position(s.max) : 1;
      counts.forEach((n, i) => {
        const pos = (i + .5) / bins;
        c.fillStyle = pos >= a && pos <= b ? cssVar('--text-color') : cssVar('--border-color');
        const bh = n ? Math.max(2, Math.sqrt(n / peak) * (h - 8)) : 0;
        c.fillRect(i / bins * w + .5, h - 4 - bh, w / bins - 1, bh);
      });
      c.fillStyle = cssVar('--text-color');
      for (const f of [clamp(a, 0, 1), clamp(b, 0, 1)]) c.fillRect(f * w - 1, 0, 2, h);
    };
    requestAnimationFrame(paint);
    let side = null;
    const move = e => {
      const r = wrap.getBoundingClientRect(), f = clamp((e.clientX - r.left) / r.width, 0, 1), value = 10 ** (lo + f * (hi - lo));
      const shown = +value.toPrecision(3);
      if (side === 'min') { s.min = f <= .005 ? null : shown; inputs.min.value = s.min ?? ''; } else { s.max = f >= .995 ? null : shown; inputs.max.value = s.max ?? ''; }
      paint(); refresh(true, true);
    };
    wrap.onpointerdown = e => {
      const r = wrap.getBoundingClientRect(), f = (e.clientX - r.left) / r.width;
      const a = s.min != null ? position(s.min) : 0, b = s.max != null ? position(s.max) : 1;
      side = Math.abs(f - a) <= Math.abs(f - b) ? 'min' : 'max';
      wrap.setPointerCapture(e.pointerId); move(e);
    };
    wrap.onpointermove = e => { if (side) move(e); };
    wrap.onpointerup = () => { if (side) { side = null; ctx.renderStages(); ctx.syncUrl(); } };
    return wrap;
  }
  function editor(s) {
    const body = el('div', { class: 'stage-body' });
    if (s.type === 'family') {
      const box = el('div', { class: 'chips' });
      for (const [k, name] of Object.entries(FAMILY_NAMES)) box.append(el('button', { type: 'button', class: 'chip' + (s.values.includes(k) ? '' : ' off'), style: `--c:${FAMILY_COLORS[k]}`, 'aria-pressed': String(s.values.includes(k)), onclick: () => { s.values = s.values.includes(k) ? s.values.filter(v => v !== k) : [...s.values, k]; refresh(); } }, name));
      body.append(box);
    } else if (s.type === 'limit') {
      const min = el('input', { type: 'number', step: 'any', value: s.min ?? '', placeholder: 'min', 'aria-label': 'Minimum', onchange: () => { s.min = num(parseFloat(min.value)); refresh(); } });
      const max = el('input', { type: 'number', step: 'any', value: s.max ?? '', placeholder: 'max', 'aria-label': 'Maximum', onchange: () => { s.max = num(parseFloat(max.value)); refresh(); } });
      const select = el('select', { 'aria-label': 'Property', onchange: () => { s.expr = select.value; s.min = s.max = null; refresh(); } });
      options(select, db.bySym[s.expr] ? propOptions : [[s.expr, s.expr], ...propOptions]);
      select.value = s.expr;
      min.addEventListener('keydown', e => e.stopPropagation()); max.addEventListener('keydown', e => e.stopPropagation());
      body.append(histogram(s, { min, max }), el('div', { class: 'range-row' }, select, min, max));
      const axis = new Axis(db, s.expr, false);
      const bounds = axis.prop ? runStages(db, [s], rowsBefore(s), ctx.stageContext()).rows.filter(row => { const o = row.obs[axis.prop.index]; return o >= 0 && db.isBound(o); }) : [];
      const distinct = new Set(bounds.map(row => row.obs[axis.prop.index])).size;
      if (distinct && (s.min != null || s.max != null)) body.append(el('small', {}, `Includes ${distinct} reported ${distinct === 1 ? 'bound' : 'bounds'}, compared at the reported value.`));
    } else if (s.type === 'class' || s.type === 'org') {
      const counts = new Map();
      for (const row of rowsBefore(s)) {
        const names = s.type === 'class' ? [row.m.group] : row.list.map(o => db.organization(o));
        for (const name of names) { if (!counts.has(name)) counts.set(name, new Set()); counts.get(name).add(row.m.i); }
      }
      const box = el('div', { class: 'chips', style: 'max-height:128px;overflow:auto' });
      [...counts.entries()].sort((a, b) => b[1].size - a[1].size).forEach(([name, set]) => box.append(el('button', { type: 'button', class: 'chip' + (s.values.includes(name) ? '' : ' off'), 'aria-pressed': String(s.values.includes(name)), onclick: () => { s.values = s.values.includes(name) ? s.values.filter(v => v !== name) : [...s.values, name]; refresh(); } }, name, ' ', el('b', {}, set.size))));
      body.append(box);
    } else if (s.type === 'tag') {
      const select = el('select', { 'aria-label': 'Tag', onchange: () => { s.value = select.value; refresh(); } });
      options(select, tags.names().map(n => [n, n]));
      select.value = s.value;
      body.append(tags.names().length ? select : el('small', {}, 'No tags yet. Click a point to tag it.'));
    } else if (s.type === 'text') {
      const input = el('input', { type: 'search', value: s.value, placeholder: 'Name, class or source', style: 'width:100%', oninput: () => { s.value = input.value; refresh(true, true); }, onkeydown: e => e.stopPropagation() });
      body.append(input);
    } else if (s.type === 'index') {
      const flip = el('button', { type: 'button', onclick: () => { s.above = !s.above; refresh(); } }, s.above ? 'Keep above' : 'Keep below');
      const row = el('div', { class: 'range-row' }, flip);
      if (!s.brief) {
        const slope = el('select', { 'aria-label': 'Slope', onchange: () => { s.slope = parseFloat(slope.value); refresh(); } });
        options(slope, [[1, 'Slope 1: tie'], [1.5, 'Slope 1.5: strong beam'], [2, 'Slope 2: stiff beam'], [3, 'Slope 3: stiff plate']]);
        slope.value = s.slope;
        row.append(slope);
      }
      const off = s.x !== state.x || s.y !== state.y;
      body.append(row, el('small', {}, off ? `Set on ${new Axis(db, s.y).short} vs ${new Axis(db, s.x).short}. It still filters on these axes.` : 'Drag the dashed line on the chart.'));
    } else if (s.type === 'region') {
      const a = new Axis(db, s.x), b = new Axis(db, s.y);
      body.append(el('small', {}, `${a.short} ${formatValue(s.x0)} to ${formatValue(s.x1)}; ${b.short} ${formatValue(s.y0)} to ${formatValue(s.y1)}`));
    }
    return body;
  }
  let dragFrom = null;
  ctx.renderStages = () => {
    const host = $('stages'), base = ctx.baseRows(), stages = ctx.stages, { counts } = runStages(db, stages, base, ctx.stageContext());
    const total = new Set(base.map(r => r.m.i)).size;
    const nodes = [el('div', { class: 'start' }, el('span', {}, total === db.materials.length ? 'All materials' : 'Showing, from the chart'), el('span', {}, total.toLocaleString()))];
    if (!stages.length) nodes.push(el('div', { class: 'empty' }, 'No stages yet. Type ', el('code', {}, 'UTS > 200 MPa'), ' above, add one below, or start from a part.'));
    stages.forEach((s, i) => {
      const c = counts[i];
      const card = el('div', { class: 'stage' + (s.enabled === false ? ' off' : '') });
      const top = el('div', { class: 'stage-top', draggable: true,
        ondragstart: e => { dragFrom = i; e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', String(i)); },
        ondragover: e => { e.preventDefault(); card.classList.add('drag-over'); },
        ondragleave: () => card.classList.remove('drag-over'),
        ondrop: e => { e.preventDefault(); if (dragFrom != null && dragFrom !== i) { const [moved] = stages.splice(dragFrom, 1); stages.splice(i, 0, moved); dragFrom = null; refresh(); } },
      },
        el('span', { class: 'stage-title', title: stageTitle(s) }, stageTitle(s)),
        i > 0 ? el('button', { type: 'button', class: 'ghost', title: 'Move up', 'aria-label': 'Move stage up', onclick: () => { [stages[i - 1], stages[i]] = [stages[i], stages[i - 1]]; refresh(); } }, '↑') : null,
        el('button', { type: 'button', class: 'ghost', title: s.enabled === false ? 'Turn on' : 'Turn off', 'aria-pressed': String(s.enabled !== false), onclick: () => { s.enabled = s.enabled === false; refresh(); } }, s.enabled === false ? 'Off' : 'On'),
        el('button', { type: 'button', class: 'ghost', title: 'Remove', 'aria-label': 'Remove stage', onclick: () => { stages.splice(i, 1); if (s.brief) { state.brief = null; renderBrief(); } refresh(); } }, '×'));
      card.append(top, editor(s), el('div', { class: 'funnel' }, el('span', { class: 'bar' }, el('i', { style: `width:${total ? c.after / total * 100 : 0}%` })), el('span', {}, `${c.before.toLocaleString()} → ${c.after.toLocaleString()}`)));
      nodes.push(card);
    });
    nodes.push(el('div', { class: 'end' }, el('span', {}, 'Remaining'), el('span', {}, (counts.at(-1)?.after ?? total).toLocaleString())));
    host.replaceChildren(...nodes);
  };
  ctx.updateFunnels = () => {
    const base = ctx.baseRows(), { counts } = runStages(db, ctx.stages, base, ctx.stageContext()), total = new Set(base.map(r => r.m.i)).size;
    document.querySelectorAll('#stages .funnel').forEach((node, i) => {
      const c = counts[i];
      if (c) { node.lastChild.textContent = `${c.before.toLocaleString()} → ${c.after.toLocaleString()}`; node.querySelector('i').style.width = (total ? c.after / total * 100 : 0) + '%'; }
    });
    const end = document.querySelector('#stages .end span:last-child');
    if (end) end.textContent = (counts.at(-1)?.after ?? total).toLocaleString();
  };
  ctx.setStack = open => {
    state.stackOpen = open;
    $('stack').hidden = !open;
    $('stack-btn').classList.toggle('on', open);
    $('stack-btn').setAttribute('aria-pressed', String(open));
    if (open) ctx.renderStages();
    ctx.syncUrl();
  };
  $('stack-btn').onclick = () => ctx.setStack(!state.stackOpen);
  $('stack-close').onclick = () => ctx.setStack(false);

  /* ---------- design brief ---------- */
  $('b-part').append(...Object.keys(BRIEFS).map(k => el('option', { value: k }, k)));
  $('b-driver').append(...Object.entries(DRIVERS).map(([k, v]) => el('option', { value: k }, v)));
  const known = state.brief && BRIEFS[state.brief.part]?.[state.brief.driver];
  if (state.brief && !known) state.brief = null;
  $('b-part').value = state.brief?.part || 'beam (in bending)';
  $('b-driver').value = state.brief?.driver || 'stiff';
  const chosen = () => db.indices[BRIEFS[$('b-part').value][$('b-driver').value]];
  function renderBrief() {
    const index = chosen();
    $('b-why').replaceChildren('Index ', el('code', {}, 'M = ' + index.expression), `. Higher is better. ${index.source}`);
    $('b-clear').hidden = !state.brief;
    $('brief-box').open = $('brief-box').open || !!state.brief;
  }
  function useBrief() {
    ctx.setView('chart');
    const key = BRIEFS[$('b-part').value][$('b-driver').value], index = db.indices[key];
    const x = symbolOf(index.x), y = symbolOf(index.y);
    ctx.stages = ctx.stages.filter(s => !s.brief);
    state.brief = { part: $('b-part').value, driver: $('b-driver').value };
    const axisX = new Axis(db, x), axisY = new Axis(db, y), allow = ctx.allow();
    const pool = runStages(db, ctx.stages, ctx.baseRows(), ctx.stageContext()).rows;
    // Start the line so about one material in eight passes. Dragging it changes that.
    const scored = pool.map(row => [axisX.value(row, allow), axisY.value(row, allow)]).filter(([a, b]) => Number.isFinite(a) && Number.isFinite(b)).map(([a, b]) => Math.log10(b) - index.slope * Math.log10(a)).sort((a, b) => b - a);
    const c = scored.length ? scored[Math.min(scored.length - 1, Math.floor(scored.length * .12))] : 0;
    ctx.stages.push({ type: 'index', x, y, slope: index.slope, c, above: true, enabled: true, brief: true });
    state.index = key;
    ctx.resetSort();
    ctx.setAxes({ x, y, xLog: true, yLog: true });
    renderBrief();
    ctx.populateIndices();
  }
  $('b-use').onclick = useBrief;
  $('b-part').onchange = $('b-driver').onchange = () => { if (state.brief) useBrief(); else renderBrief(); };
  $('b-clear').onclick = () => { ctx.stages = ctx.stages.filter(s => !s.brief); state.brief = null; state.index = ''; ctx.populateIndices(); refresh(); renderBrief(); };
  renderBrief();
}
