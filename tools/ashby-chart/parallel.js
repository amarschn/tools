/* Parallel axes. Dragging on an axis edits a limit stage, so both views share one filter chain. */
const { Axis, formatValue, clamp } = window.AshbyEngine;

export function setupParallel(ctx) {
  const { $, el, cssVar, db, state, tags, isPhone } = ctx;
  const pv = { W: 0, H: 0, raf: 0, drag: null, hover: null, rows: [], ranges: {} };
  const pad = { l: 44, r: 44, t: 48, b: 26 };
  const canvas = el('canvas'), tip = el('div', { class: 'ac-tip', hidden: true });
  const hintBox = el('div', { class: 'p-hint' }, 'Drag along an axis to filter. Filters also appear in the stack. Click a filtered axis to clear it.');
  $('p-stage').append(canvas, tip, hintBox);
  const c = canvas.getContext('2d');
  const xAt = i => pad.l + (pv.W - pad.l - pad.r) * i / Math.max(1, state.paxes.length - 1);
  const yAt = (s, v) => pv.H - pad.b - (Math.log10(v) - pv.ranges[s][0]) / (pv.ranges[s][1] - pv.ranges[s][0]) * (pv.H - pad.t - pad.b);
  const valueAt = (s, y) => 10 ** (pv.ranges[s][0] + (pv.H - pad.b - y) / (pv.H - pad.t - pad.b) * (pv.ranges[s][1] - pv.ranges[s][0]));
  const limitStage = s => ctx.stages.find(st => st.type === 'limit' && st.expr === s && st.enabled !== false);

  ctx.updateParallel = (base, allow) => {
    const axes = state.paxes.map(s => new Axis(db, s));
    const lines = [];
    for (const point of db.points(base, axes, allow)) {
      if (!ctx.passesBasis(point)) continue;
      const liveRow = point.rows.find(ctx.rowLive);
      if (liveRow) point.row = liveRow;
      const values = axes.map(a => a.value(point.row, allow));
      if (values.some(v => !Number.isFinite(v))) continue;
      const bounds = axes.map(a => db.isBound(a.observation(point.row)));
      lines.push({ point, m: point.m, values, bounds, anyBound: bounds.some(Boolean), live: !!liveRow, color: ctx.colorFor(point.row) });
    }
    pv.rows = lines;
    pv.ranges = {};
    if (lines.length) state.paxes.forEach((s, i) => {
      const values = lines.map(l => Math.log10(l.values[i])), lo = Math.min(...values), hi = Math.max(...values);
      pv.ranges[s] = hi === lo ? [lo - .5, lo + .5] : [lo, hi];
    });
    if (state.view === 'parallel') { renderBar(); ctx.drawParallel(); }
  };
  ctx.parallelHasLive = () => pv.rows.some(l => l.live);
  ctx.resetParallelHover = () => { pv.hover = null; tip.hidden = true; };
  function ticksFor(lo, hi) {
    const span = hi - lo, out = [];
    const steps = span >= 1.5 ? [1] : span >= .6 ? [1, 2, 5] : [1, 1.5, 2, 3, 5, 7];
    const every = span >= 7 ? 2 : 1;
    for (let d = Math.floor(lo); d <= hi; d += every) for (const k of steps) { const t = d + Math.log10(k); if (t >= lo - 1e-9 && t <= hi + 1e-9) out.push(t); }
    return out.length >= 2 ? out : [lo, hi];
  }
  function path(line) {
    c.beginPath();
    state.paxes.forEach((s, i) => { const X = xAt(i), Y = yAt(s, line.values[i]); i ? c.lineTo(X, Y) : c.moveTo(X, Y); });
    c.stroke();
  }
  /* A segment that touches a reported bound is dashed, because a bound is a limit and not a measured value. */
  function boundPath(line) {
    for (let i = 0; i < state.paxes.length - 1; i++) {
      c.setLineDash(line.bounds[i] || line.bounds[i + 1] ? [4, 3] : []);
      c.beginPath(); c.moveTo(xAt(i), yAt(state.paxes[i], line.values[i])); c.lineTo(xAt(i + 1), yAt(state.paxes[i + 1], line.values[i + 1])); c.stroke();
    }
    c.setLineDash([]);
  }
  function paint() {
    pv.raf = 0;
    if (state.view !== 'parallel') return;
    const rect = $('p-stage').getBoundingClientRect();
    pv.W = rect.width; pv.H = rect.height;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    if (canvas.width !== Math.round(pv.W * dpr) || canvas.height !== Math.round(pv.H * dpr)) {
      canvas.width = Math.round(pv.W * dpr); canvas.height = Math.round(pv.H * dpr);
      canvas.style.width = pv.W + 'px'; canvas.style.height = pv.H + 'px';
    }
    c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, pv.W, pv.H);
    c.fillStyle = cssVar('--plot-color'); c.fillRect(0, 0, pv.W, pv.H);
    if (!pv.rows.length || !pv.W) return;
    const ink = cssVar('--text-color'), muted = cssVar('--text-light'), plotBg = cssVar('--plot-color');
    const on = pv.rows.filter(l => l.live), off = pv.rows.filter(l => !l.live);
    c.lineWidth = 1;
    if (state.ghosts) { c.strokeStyle = cssVar('--ghost-color'); off.forEach(path); }
    c.globalAlpha = on.length > 300 ? .35 : .7;
    for (const line of on) { c.strokeStyle = line.color; if (line.anyBound) boundPath(line); else path(line); }
    c.globalAlpha = 1;
    // Tagged materials stay readable among hundreds of lines.
    c.lineWidth = 2;
    for (const line of on) { const t = ctx.visibleTag(line.m); if (t) { c.strokeStyle = tags.color(t); path(line); } }
    c.strokeStyle = ink; c.lineWidth = 2.6;
    for (const line of pv.rows) if (line.point.key === ctx.popM?.key || line === pv.hover) path(line);
    c.lineWidth = 1;
    const room = (pv.W - pad.l - pad.r) / Math.max(1, state.paxes.length - 1), last = state.paxes.length - 1;
    state.paxes.forEach((s, i) => {
      const X = xAt(i), prop = db.bySym[s];
      c.strokeStyle = muted; c.beginPath(); c.moveTo(X + .5, pad.t); c.lineTo(X + .5, pv.H - pad.b); c.stroke();
      c.textBaseline = 'alphabetic';
      c.textAlign = i === 0 ? 'left' : i === last ? 'right' : 'center';
      const tx = i === 0 ? X - pad.l + 8 : i === last ? X + pad.r - 8 : X;
      c.font = '600 12px ' + cssVar('--font-sans'); c.fillStyle = ink;
      // End titles sit fully on one side of their axis, so they get less room before they hit a neighbour.
      const titleRoom = i === 0 || i === last ? room * .62 : room * .85;
      c.fillText(c.measureText(prop.label).width > titleRoom ? prop.symbol.replace('rho', 'ρ') : prop.label, tx, 18);
      c.font = '11px ' + cssVar('--font-sans'); c.fillStyle = muted;
      c.fillText(prop.display_unit, tx, 33);
      c.textAlign = 'right';
      const [lo, hi] = pv.ranges[s];
      let lastY = Infinity;
      for (const t of ticksFor(lo, hi)) {
        const Y = yAt(s, 10 ** t);
        c.fillStyle = muted; c.fillRect(X - 3, Y, 6, 1);
        if (Math.abs(lastY - Y) < 15) continue;
        lastY = Y;
        c.lineWidth = 3; c.strokeStyle = plotBg; c.lineJoin = 'round';
        c.strokeText(formatValue(10 ** t), X - 6, Y + 4); c.fillText(formatValue(10 ** t), X - 6, Y + 4); c.lineWidth = 1;
      }
      const st = limitStage(s);
      if (st && (st.min != null || st.max != null)) {
        const y0 = st.max != null ? clamp(yAt(s, st.max), pad.t, pv.H - pad.b) : pad.t, y1 = st.min != null ? clamp(yAt(s, st.min), pad.t, pv.H - pad.b) : pv.H - pad.b;
        c.fillStyle = ink; c.globalAlpha = .18; c.fillRect(X - 9, y0, 18, y1 - y0); c.globalAlpha = 1;
        c.strokeStyle = ink; c.strokeRect(X - 9, y0, 18, y1 - y0);
        c.textAlign = i === last ? 'right' : 'left'; c.font = '600 11px ' + cssVar('--font-sans'); c.fillStyle = ink;
        const side = i === last ? X - 13 : X + 13;
        c.lineWidth = 3; c.strokeStyle = plotBg;
        if (st.max != null) { c.strokeText(formatValue(st.max), side, y0 + 10); c.fillText(formatValue(st.max), side, y0 + 10); }
        if (st.min != null) { c.strokeText(formatValue(st.min), side, y1 - 3); c.fillText(formatValue(st.min), side, y1 - 3); }
        c.lineWidth = 1; c.font = '11px ' + cssVar('--font-sans'); c.textAlign = 'right';
      }
    });
  }
  ctx.drawParallel = () => { if (state.view === 'parallel' && !pv.raf) pv.raf = requestAnimationFrame(paint); };
  function nearest(x, y, limit = 7) {
    let best = null, bestD = limit * limit;
    const n = state.paxes.length;
    const seg = clamp(Math.floor((x - xAt(0)) / ((xAt(n - 1) - xAt(0)) / (n - 1) || 1)), 0, n - 2);
    const x0 = xAt(seg), x1 = xAt(seg + 1), k = clamp((x - x0) / (x1 - x0 || 1), 0, 1), a = state.paxes[seg], b = state.paxes[seg + 1];
    for (const line of pv.rows) {
      if (!line.live) continue;
      const ya = yAt(a, line.values[seg]), d = (ya + (yAt(b, line.values[seg + 1]) - ya) * k - y) ** 2;
      if (d < bestD) { bestD = d; best = line; }
    }
    return best;
  }
  function brush(drag, y) {
    let stage = limitStage(drag.s), created = false;
    if (!stage) { stage = { type: 'limit', expr: drag.s, min: null, max: null, enabled: true }; ctx.stages.push(stage); created = true; }
    const top = Math.min(y, drag.y), bottom = Math.max(y, drag.y);
    // A drag that reaches the end of an axis leaves that side open, so rounding cannot drop the last material.
    stage.max = top <= pad.t + 1 ? null : +valueAt(drag.s, top).toPrecision(3);
    stage.min = bottom >= pv.H - pad.b - 1 ? null : +valueAt(drag.s, bottom).toPrecision(3);
    ctx.refresh(true, !created);
  }
  canvas.addEventListener('selectstart', e => e.preventDefault());
  canvas.addEventListener('pointerdown', e => {
    const x = e.offsetX, y = e.offsetY, i = state.paxes.findIndex((_, n) => Math.abs(xAt(n) - x) < 20);
    canvas.setPointerCapture(e.pointerId);
    tip.hidden = true;
    const touch = e.pointerType === 'touch';
    if (i >= 0 && pv.rows.length) {
      // Ranges stay fixed during a drag, because they come from the materials before any filter.
      pv.drag = { s: state.paxes[i], y: clamp(y, pad.t, pv.H - pad.b), moved: false, touch };
    } else pv.drag = { s: null, touch };
  });
  canvas.addEventListener('pointermove', e => {
    const x = e.offsetX, y = e.offsetY, drag = pv.drag;
    if (drag?.s) {
      const at = clamp(y, pad.t, pv.H - pad.b);
      if (Math.abs(at - drag.y) > 3) drag.moved = true;
      if (drag.moved) brush(drag, at);
      return;
    }
    if (drag || !pv.rows.length) return;
    const nearAxis = state.paxes.some((_, n) => Math.abs(xAt(n) - x) < 20);
    canvas.style.cursor = nearAxis ? 'ns-resize' : 'default';
    const hit = nearest(x, y);
    if (hit !== pv.hover) { pv.hover = hit; ctx.drawParallel(); }
    if (hit) {
      tip.replaceChildren(el('strong', {}, ctx.pointName(hit.point)), ...hit.point.obs.map(o => el('span', {}, `${db.propertyOf(o).label}: ${db.resultText(o)}`)));
      tip.hidden = false;
      const w = tip.offsetWidth, h = tip.offsetHeight;
      tip.style.left = clamp(x + 14 + w > pv.W ? x - w - 14 : x + 14, 4, Math.max(4, pv.W - w - 4)) + 'px';
      tip.style.top = clamp(y - h - 10 < 0 ? y + 14 : y - h - 10, 4, Math.max(4, pv.H - h - 4)) + 'px';
      if (!nearAxis) canvas.style.cursor = 'pointer';
    } else tip.hidden = true;
  });
  const release = e => {
    const drag = pv.drag;
    pv.drag = null;
    if (!drag) return;
    if (drag.s && drag.moved) { ctx.refresh(true); return; }
    if (drag.s) {
      const st = limitStage(drag.s);
      if (st && (st.min != null || st.max != null)) { ctx.stages.splice(ctx.stages.indexOf(st), 1); ctx.refresh(true); return; }
    }
    if (e.type === 'pointercancel' || !pv.rows.length) return;
    const stageBox = $('p-stage').getBoundingClientRect(), wrapBox = $('wrap').getBoundingClientRect();
    const hit = nearest(e.offsetX, e.offsetY, drag.touch ? 16 : 7);
    if (hit) ctx.openParallelPoint(hit.point, [e.offsetX + stageBox.left - wrapBox.left, e.offsetY + stageBox.top - wrapBox.top]);
    else ctx.closeParallelPoint();
  };
  canvas.addEventListener('pointerup', release);
  canvas.addEventListener('pointercancel', release);
  canvas.addEventListener('pointerleave', () => { if (!pv.drag && pv.hover) { pv.hover = null; tip.hidden = true; ctx.drawParallel(); } });
  new ResizeObserver(() => ctx.drawParallel()).observe($('p-stage'));
  function renderBar() {
    const n = pv.rows.length, passing = pv.rows.filter(l => l.live).length;
    const materials = new Set(pv.rows.map(l => l.m.i)).size, total = new Set(ctx.baseRows().map(r => r.m.i)).size;
    const coverage = el('span', { class: 'p-coverage' + (materials < 200 ? ' warn' : '') }, `${materials.toLocaleString()} of ${total.toLocaleString()} materials have all ${state.paxes.length} values` + (passing !== n ? `, ${passing.toLocaleString()} of ${n.toLocaleString()} lines pass` : ''));
    const open = document.activeElement?.closest?.('#p-bar') ? document.activeElement.getAttribute('aria-label') : null;
    $('p-bar').replaceChildren(...state.paxes.map((sym, i) => {
      const select = el('select', { 'aria-label': `Axis ${i + 1}`, onchange: () => { state.paxes[i] = select.value; ctx.refresh(); } }, db.props.filter(p => p.symbol === sym || !state.paxes.includes(p.symbol)).map(p => el('option', { value: p.symbol }, p.label)));
      select.value = sym;
      return el('span', { class: 'axis-chip' },
        i > 0 ? el('button', { type: 'button', class: 'ghost', title: 'Move this axis left', 'aria-label': `Move ${db.bySym[sym].label} left`, onclick: () => { [state.paxes[i - 1], state.paxes[i]] = [state.paxes[i], state.paxes[i - 1]]; ctx.refresh(); } }, '←') : null,
        select,
        state.paxes.length > 2 ? el('button', { type: 'button', class: 'ghost', 'aria-label': `Remove ${db.bySym[sym].label}`, title: 'Remove this axis', onclick: () => { state.paxes.splice(i, 1); ctx.refresh(); } }, '×') : null);
    }), state.paxes.length < db.props.length ? el('button', { type: 'button', id: 'p-add', title: 'Adds the property that keeps the most materials. Change it with its menu.', onclick: addAxis }, '+ Add axis') : null, coverage);
    if (open) $('p-bar').querySelector(`[aria-label="${open}"]`)?.focus();
    hintBox.hidden = !n || isPhone();
    const empty = $('p-stage').querySelector('.p-empty');
    if (!n && !empty) $('p-stage').append(el('div', { class: 'p-empty' }, 'No material has all of these values. Remove an axis or turn more families on.'));
    if (n && empty) empty.remove();
  }
  function addAxis() {
    const axes = state.paxes.map(s => new Axis(db, s)), allow = ctx.allow();
    const rows = ctx.baseRows().filter(row => axes.every(a => Number.isFinite(a.value(row, allow))));
    const next = db.props.filter(p => !state.paxes.includes(p.symbol)).map(p => {
      const axis = new Axis(db, p.symbol), seen = new Set();
      for (const row of rows) if (Number.isFinite(axis.value(row, allow))) seen.add(row.m.i);
      return [p.symbol, seen.size];
    }).sort((a, b) => b[1] - a[1])[0]?.[0];
    if (next) { state.paxes.push(next); ctx.refresh(); }
  }
}
