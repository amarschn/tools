/* Study F: Studio as the default view, with the selection stack, the design brief,
   single-material tags and movable label boxes on top of it. */
(async () => {
  const { el, Axis, Plot, tags, FAMILY_NAMES, FAMILY_COLORS, formatValue, clamp } = AC;
  AC.header('f-combined');
  const db = await AC.load();
  const $ = id => document.getElementById(id);
  const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const isPhone = () => matchMedia('(max-width: 820px)').matches;
  const num = v => Number.isFinite(v) ? v : null;
  const options = (select, list) => select.replaceChildren(...list.map(([value, text]) => el('option', { value }, text)));
  const propOptions = db.props.map(p => [p.sym, p.unit ? `${p.label} (${p.unit})` : p.label]);
  const VIEW_KEY = 'ashby-prototype-views', LABEL_KEY = 'ashby-prototype-labels', LABEL_CAP = 40;
  const STARTER_VIEWS = [
    { name: 'Stiffness', x: 'rho', y: 'E' }, { name: 'Strength', x: 'rho', y: 'UTS' },
    { name: 'Compression', x: 'rho', y: 'Sc' }, { name: 'Bending', x: 'rho', y: 'Ef' },
    { name: 'Specific stiffness vs specific strength', x: 'UTS/rho', y: 'E/rho' },
    { name: 'Beam stiffness index', x: 'rho', y: 'E^0.5/rho' },
    { name: 'Insulators', x: 'rho', y: 'k' },
  ];
  // Each entry is a published performance index. Slope is the guideline on log axes.
  const BRIEFS = {
    'tie (rod in tension)': { stiff: ['E', 'E', 1, 'E / ρ', 'stiff_light_tie'], strong: ['UTS', 'UTS', 1, 'σ / ρ', 'strong_light_tie'] },
    'beam (in bending)': { stiff: ['E', 'E^0.5', 2, 'E^(1/2) / ρ', 'stiff_light_beam'], strong: ['UTS', 'UTS^(2/3)', 1.5, 'σ^(2/3) / ρ', 'strong_light_beam'] },
    'plate or panel': { stiff: ['E', 'E^(1/3)', 3, 'E^(1/3) / ρ', 'stiff_light_plate'], strong: ['UTS', 'UTS^0.5', 2, 'σ^(1/2) / ρ', 'strong_light_plate'] },
  };
  const DRIVERS = { stiff: 'stiff enough', strong: 'strong enough' };
  const QUERY_HINT = 'Symbols: ' + db.props.map(p => p.sym).join(' ') + ', or a formula like E^0.5/rho > 0.002';

  const state = {
    x: 'rho', y: 'E', xLog: true, yLog: true, shape: 'ashby', group: 'family', color: 'family', size: 'none',
    ranges: false, ghosts: true, families: new Set(Object.keys(FAMILY_NAMES)), hiddenTags: new Set(), isolate: null,
    hidden: new Set(), find: '', stackOpen: false, resultsOpen: false, brief: null, view: 'chart', paxes: ['rho', 'E', 'UTS'],
  };
  let stages = [];
  let selection = new Set(), selBox = null, armRegion = false;
  let popM = null, popAt = null, detailM = null, rowById = new Map(), current = [], grip = null;
  const pinned = new Set();
  let columns = ['Sy', 'UTS', 'k'], sortKey = 'auto', sortDir = -1, resultTab = 'results';

  try {
    const saved = JSON.parse(decodeURIComponent(location.hash.slice(1)));
    if (saved && typeof saved === 'object') {
      for (const key of ['x', 'y', 'xLog', 'yLog', 'shape', 'group', 'color', 'size', 'ghosts', 'stackOpen', 'resultsOpen', 'brief', 'view']) if (key in saved) state[key] = saved[key];
      if (Array.isArray(saved.paxes)) { const known = saved.paxes.filter(s => db.bySym[s]); if (known.length >= 2) state.paxes = known; }
      if (Array.isArray(saved.families)) state.families = new Set(saved.families);
      if (Array.isArray(saved.stages)) stages = saved.stages;
    }
  } catch { /* no shared state in the URL */ }

  /* ---------- the chart ---------- */
  const plot = new Plot($('chart'), {
    padding: { l: 84, r: 14, t: 12, b: 52 }, drawAxisTitles: false,
    onSelect: (hits, shape) => {
      const xA = plot.xAxis, yA = plot.yAxis;
      if (shape.kind === 'box' && armRegion) {
        disarm();
        stages.push({ type: 'region', x: state.x, y: state.y, xLog: state.xLog, yLog: state.yLog, x0: shape.x0, x1: shape.x1, y0: shape.y0, y1: shape.y1, enabled: true });
        setMode('pan');
        refresh();
        return;
      }
      selBox = shape.kind === 'box' ? { x0: xA.t(shape.x0), x1: xA.t(shape.x1), y0: yA.t(shape.y0), y1: yA.t(shape.y1) } : null;
      setSelection(hits.map(r => r.m.id), true);
      closePop();
    },
    onClick: hit => {
      if (hit) { openPop(hit.m); return; }
      closePop();
      clearSelection();
    },
    afterPoints: drawOverlays,
    onPointerDown: pressChart,
    onPointerDrag: dragChart,
    onPointerUp: releaseChart,
    onDraw: positionFloating,
  });

  function lineStages() {
    if (!state.xLog || !state.yLog) return [];
    return stages.filter(s => s.type === 'index' && s.enabled !== false && s.x === state.x && s.y === state.y);
  }
  function boxScreen(p = plot) {
    if (!selBox) return null;
    const x0 = p.sx(selBox.x0), x1 = p.sx(selBox.x1), y0 = p.sy(selBox.y1), y1 = p.sy(selBox.y0);
    return { x0: Math.min(x0, x1), x1: Math.max(x0, x1), y0: Math.min(y0, y1), y1: Math.max(y0, y1) };
  }
  function boxCorner(x, y) {
    const b = boxScreen();
    if (!b) return null;
    for (const [cx, cy, xKey, yKey] of [[b.x0, b.y0, 'left', 'top'], [b.x1, b.y0, 'right', 'top'], [b.x0, b.y1, 'left', 'bottom'], [b.x1, b.y1, 'right', 'bottom']]) {
      if (Math.abs(x - cx) < 9 && Math.abs(y - cy) < 9) return { xKey, yKey };
    }
    return null;
  }
  const inBox = (x, y) => { const b = boxScreen(); return b && x >= b.x0 && x <= b.x1 && y >= b.y0 && y <= b.y1; };
  function nearLine(x, y, p) {
    return lineStages().find(s => Math.abs(p.sy(s.slope * p.ix(x) + s.c) - y) < 9);
  }
  function pressChart(x, y, _e, p) {
    const corner = boxCorner(x, y);
    if (corner) { grip = { kind: 'corner', ...corner }; return true; }
    const line = nearLine(x, y, p);
    if (line) { grip = { kind: 'line', stage: line }; return true; }
    if (inBox(x, y)) { grip = { kind: 'box', x, y, start: { ...selBox }, moved: false }; return true; }
    return false;
  }
  function dragChart(x, y, _e, p) {
    if (!grip) return;
    if (grip.kind === 'line') {
      grip.stage.c = p.iy(y) - grip.stage.slope * p.ix(x);
      refresh(true, true);
    } else if (grip.kind === 'box') {
      if (Math.abs(x - grip.x) + Math.abs(y - grip.y) > 3) grip.moved = true;
      const dx = p.ix(x) - p.ix(grip.x), dy = p.iy(y) - p.iy(grip.y), s = grip.start;
      selBox = { x0: s.x0 + dx, x1: s.x1 + dx, y0: s.y0 + dy, y1: s.y1 + dy };
      syncBoxSelection();
    } else if (grip.kind === 'corner') {
      if (grip.xKey === 'left') selBox.x0 = p.ix(x); else selBox.x1 = p.ix(x);
      if (grip.yKey === 'bottom') selBox.y0 = p.iy(y); else selBox.y1 = p.iy(y);
      syncBoxSelection();
    }
  }
  function releaseChart(x, y, _e, p) {
    if (grip?.kind === 'box' && !grip.moved) {
      const hit = p.nearest(x, y);
      if (hit) openPop(hit.m);
    }
    if (grip?.kind === 'corner') {
      selBox = { x0: Math.min(selBox.x0, selBox.x1), x1: Math.max(selBox.x0, selBox.x1), y0: Math.min(selBox.y0, selBox.y1), y1: Math.max(selBox.y0, selBox.y1) };
    }
    if (grip?.kind === 'line') refresh(true);
    grip = null;
  }
  function syncBoxSelection() {
    const b = selBox, lo = Math.min(b.x0, b.x1), hi = Math.max(b.x0, b.x1), bottom = Math.min(b.y0, b.y1), top = Math.max(b.y0, b.y1);
    setSelection(plot.rows.filter(r => !r.dim && r.tx >= lo && r.tx <= hi && r.ty >= bottom && r.ty <= top).map(r => r.m.id));
    plot.draw();
  }
  $('chart').addEventListener('pointermove', e => {
    if (plot.drag || plot.hover) return;
    const [x, y] = plot.point(e), corner = boxCorner(x, y);
    if (corner) plot.canvas.style.cursor = (corner.xKey === 'left') === (corner.yKey === 'top') ? 'nwse-resize' : 'nesw-resize';
    else if (nearLine(x, y, plot)) plot.canvas.style.cursor = 'ns-resize';
    else if (inBox(x, y)) plot.canvas.style.cursor = 'move';
    else plot.canvas.style.cursor = plot.mode === 'pan' ? 'grab' : 'crosshair';
  });

  function drawOverlays(ctx, p) {
    const ink = cssVar('--ink');
    // Leader lines run from each labelled point to its box.
    ctx.strokeStyle = cssVar('--ink-2'); ctx.lineWidth = 1;
    for (const id of labels.keys()) {
      const row = rowById.get(id), rect = labelRect(id, p);
      if (!row || !rect) continue;
      const X = p.sx(row.tx), Y = p.sy(row.ty);
      ctx.beginPath(); ctx.moveTo(X, Y);
      ctx.lineTo(clamp(X, rect.x, rect.x + rect.w), clamp(Y, rect.y, rect.y + rect.h)); ctx.stroke();
      ctx.fillStyle = cssVar('--card'); ctx.beginPath(); ctx.arc(X, Y, p.opts.pointSize + 1.5, 0, 7); ctx.fill();
      ctx.fillStyle = row.color; ctx.beginPath(); ctx.arc(X, Y, p.opts.pointSize, 0, 7); ctx.fill();
      ctx.strokeStyle = ink; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.arc(X, Y, p.opts.pointSize + 1.5, 0, 7); ctx.stroke();
      ctx.strokeStyle = cssVar('--ink-2'); ctx.lineWidth = 1;
    }
    // Selection lines, with the side that passes shaded.
    for (const s of lineStages()) {
      const v = p.view, f = t => s.slope * t + s.c;
      ctx.fillStyle = ink; ctx.globalAlpha = .045; ctx.beginPath();
      const edge = s.above ? v.y1 + 40 : v.y0 - 40;
      ctx.moveTo(p.sx(v.x0), p.sy(f(v.x0))); ctx.lineTo(p.sx(v.x1), p.sy(f(v.x1))); ctx.lineTo(p.sx(v.x1), p.sy(edge)); ctx.lineTo(p.sx(v.x0), p.sy(edge)); ctx.closePath(); ctx.fill(); ctx.globalAlpha = 1;
      ctx.strokeStyle = ink; ctx.lineWidth = 1.8; ctx.setLineDash([8, 5]);
      ctx.beginPath(); ctx.moveTo(p.sx(v.x0), p.sy(f(v.x0))); ctx.lineTo(p.sx(v.x1), p.sy(f(v.x1))); ctx.stroke(); ctx.setLineDash([]); ctx.lineWidth = 1;
      // Put the hint on the part of the line that is actually in view.
      const from = Math.max(v.x0, (v.y0 - s.c) / s.slope), to = Math.min(v.x1, (v.y1 - s.c) / s.slope);
      if (to > from) {
        const tx = from + (to - from) * .3;
        ctx.save(); ctx.translate(p.sx(tx), p.sy(f(tx)));
        ctx.rotate(-Math.atan2(s.slope * (p.plotBox.h / (v.y1 - v.y0)), p.plotBox.w / (v.x1 - v.x0)));
        ctx.font = '600 11.5px ' + cssVar('--sans'); ctx.fillStyle = ink;
        ctx.lineWidth = 3; ctx.strokeStyle = cssVar('--card'); ctx.lineJoin = 'round';
        const hint = s.brief ? 'Drag: better is up and left' : 'Drag to move';
        ctx.strokeText(hint, 6, -7); ctx.fillText(hint, 6, -7); ctx.lineWidth = 1; ctx.restore();
      }
    }
    // The selection box stays on the chart so it can be moved and resized.
    const b = boxScreen(p);
    if (b) {
      ctx.fillStyle = ink; ctx.globalAlpha = .06; ctx.fillRect(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0); ctx.globalAlpha = 1;
      ctx.strokeStyle = ink; ctx.lineWidth = 1.3; ctx.setLineDash([5, 4]); ctx.strokeRect(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0); ctx.setLineDash([]);
      ctx.fillStyle = cssVar('--card');
      for (const [X, Y] of [[b.x0, b.y0], [b.x1, b.y0], [b.x0, b.y1], [b.x1, b.y1]]) { ctx.fillRect(X - 4, Y - 4, 8, 8); ctx.strokeRect(X - 4, Y - 4, 8, 8); }
      ctx.lineWidth = 1;
    }
  }

  /* ---------- label boxes: stored as an offset from the material, so they follow pan and zoom ---------- */
  const labels = (() => {
    try { return new Map(Object.entries(JSON.parse(localStorage.getItem(LABEL_KEY)) || {}).filter(([id]) => db.byId[id])); } catch { return new Map(); }
  })();
  const labelNodes = new Map();
  function saveLabels() {
    try { localStorage.setItem(LABEL_KEY, JSON.stringify(Object.fromEntries(labels))); } catch { /* private window: labels last until reload */ }
  }
  function placeLabel(id) {
    const row = rowById.get(id), b = plot.plotBox, w = 180, h = 38;
    if (!row) return [24, -48];
    const X = plot.sx(row.tx), Y = plot.sy(row.ty);
    const taken = [...labels.keys()].map(other => labelRect(other, plot)).filter(Boolean);
    for (const [dx, dy] of [[24, -48], [24, 14], [-w - 24, -48], [-w - 24, 14], [24, -94], [24, 60], [-w - 24, -94], [-w - 24, 60], [70, -18], [-w - 70, -18]]) {
      const x = X + dx, y = Y + dy;
      if (x < b.l + 2 || x + w > b.r - 2 || y < b.t + 2 || y + h > b.b - 2) continue;
      if (!taken.some(r => x < r.x + r.w + 4 && x + w + 4 > r.x && y < r.y + r.h + 4 && y + h + 4 > r.y)) return [dx, dy];
    }
    return [24, -48];
  }
  function labelRect(id, p = plot) {
    const row = rowById.get(id), at = labels.get(id);
    if (!row || !at) return null;
    const b = p.plotBox, X = p.sx(row.tx), Y = p.sy(row.ty);
    if (X < b.l || X > b.r || Y < b.t || Y > b.b) return null;
    const node = labelNodes.get(id), w = node?.offsetWidth || 180, h = node?.offsetHeight || 38;
    return { x: clamp(X + at[0], b.l + 2, Math.max(b.l + 2, b.r - w - 2)), y: clamp(Y + at[1], b.t + 2, Math.max(b.t + 2, b.b - h - 2)), w, h };
  }
  const axisTag = axis => axis.prop ? axis.prop.sym.replace('rho', 'ρ') : axis.short;
  const axisValue = (axis, v) => `${axisTag(axis)} ${formatValue(v)}${axis.prop?.unit ? ' ' + axis.prop.unit : ''}`;
  function renderLabels() {
    const layer = $('labels');
    for (const [id, node] of labelNodes) if (!labels.has(id)) { node.remove(); labelNodes.delete(id); }
    let hidden = 0;
    for (const id of labels.keys()) {
      const m = db.byId[id], row = rowById.get(id);
      if (!row) hidden++;
      let node = labelNodes.get(id);
      if (!node) { node = makeLabelNode(m); labelNodes.set(id, node); layer.append(node); }
      const tag = tags.of(id).find(n => !state.hiddenTags.has(n));
      node.style.setProperty('--c', tag ? tags.color(tag) : FAMILY_COLORS[m.family]);
      node.classList.toggle('faded', !!row?.dim);
      node.querySelector('span').textContent = row ? `${axisValue(plot.yAxis, row.y)} · ${axisValue(plot.xAxis, row.x)}` : '';
    }
    $('label-actions').hidden = labels.size === 0;
    $('label-count').textContent = `${labels.size} label ${labels.size === 1 ? 'box' : 'boxes'}` + (hidden ? `, ${hidden} with no values on these axes` : '');
    positionFloating();
  }
  function makeLabelNode(m) {
    const node = el('div', { class: 'label-box', title: 'Drag to move. Click for tags and details.' },
      el('strong', {}, m.name), el('span', {}),
      el('button', { 'aria-label': `Remove the label on ${m.name}`, title: 'Remove this label', onpointerdown: e => e.stopPropagation(), onclick: e => { e.stopPropagation(); removeLabel(m.id); } }, '×'));
    let press = null;
    // Stops Safari from starting a text selection when a drag begins on the box.
    node.addEventListener('mousedown', e => e.preventDefault());
    node.addEventListener('pointerdown', e => {
      node.setPointerCapture(e.pointerId);
      press = { x: e.clientX, y: e.clientY, at: [...labels.get(m.id)], moved: false };
      node.classList.add('drag');
    });
    node.addEventListener('pointermove', e => {
      if (!press) return;
      const dx = e.clientX - press.x, dy = e.clientY - press.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) press.moved = true;
      labels.set(m.id, [press.at[0] + dx, press.at[1] + dy]);
      plot.draw();
    });
    const finish = () => {
      if (!press) return;
      const moved = press.moved;
      press = null;
      node.classList.remove('drag');
      if (moved) {
        // Save where the box actually landed, so it cannot drift off the plot.
        const row = rowById.get(m.id), rect = labelRect(m.id);
        if (row && rect) labels.set(m.id, [rect.x - plot.sx(row.tx), rect.y - plot.sy(row.ty)]);
        saveLabels();
      } else openPop(m);
    };
    node.addEventListener('pointerup', finish);
    node.addEventListener('pointercancel', finish);
    return node;
  }
  function addLabels(ids) {
    for (const id of ids) if (!labels.has(id)) labels.set(id, placeLabel(id));
    saveLabels(); renderLabels(); plot.draw();
  }
  function removeLabel(id) { labels.delete(id); saveLabels(); renderLabels(); renderPop(); plot.draw(); }
  // A drag anywhere on the chart must never become a text selection. Inputs and the cards stay selectable.
  $('wrap').addEventListener('selectstart', e => {
    const target = e.target.nodeType === 1 ? e.target : e.target.parentElement;
    if (!target?.closest('input, .mat, .drawer')) e.preventDefault();
  });
  $('labels').addEventListener('wheel', e => { e.preventDefault(); const [x, y] = plot.point(e); plot.zoomAt(x, y, Math.exp(e.deltaY * .0016)); }, { passive: false });
  $('labels-clear').onclick = () => { labels.clear(); saveLabels(); renderLabels(); renderPop(); plot.draw(); };

  function positionFloating() {
    for (const [id, node] of labelNodes) {
      const rect = labelRect(id);
      node.hidden = !rect;
      if (rect) node.style.transform = `translate(${Math.round(rect.x)}px, ${Math.round(rect.y)}px)`;
    }
    const mat = $('mat');
    if (popM && !mat.hidden && !isPhone()) {
      const row = rowById.get(popM.id), wrap = $('wrap');
      const w = mat.offsetWidth, h = mat.offsetHeight, W = wrap.clientWidth, H = wrap.clientHeight;
      const onParallel = state.view === 'parallel' && popAt;
      const X = onParallel ? popAt[0] : row ? plot.sx(row.tx) : W / 2, Y = onParallel ? popAt[1] : row ? plot.sy(row.ty) : H / 2;
      const left = X + 16 + w > W - 6 ? X - w - 16 : X + 16;
      mat.style.transform = `translate(${Math.round(clamp(left, 6, Math.max(6, W - w - 6)))}px, ${Math.round(clamp(Y - 24, 6, Math.max(6, H - h - 6)))}px)`;
    }
  }

  /* ---------- one material: tag it, label it, compare it ---------- */
  function openPop(m, at = null) { popM = m; popAt = at; renderPop(); plot.selected = new Set([...selection, m.id]); plot.draw(); drawParallel(); }
  // Safari keeps focus on a hidden field, which would swallow the keyboard shortcuts, so let go of it first.
  const releaseFocus = box => { if (box.contains(document.activeElement)) document.activeElement.blur(); };
  function closePop() { releaseFocus($('mat')); popM = null; popAt = null; $('mat').hidden = true; plot.selected = new Set(selection); plot.draw(); drawParallel(); }
  function renderPop(focus = true) {
    const box = $('mat');
    if (!popM) { box.hidden = true; return; }
    const m = popM, row = rowById.get(m.id), applied = tags.of(m.id), others = tags.names().filter(n => !applied.includes(n));
    const input = el('input', { type: 'text', placeholder: 'New tag, then Enter', 'aria-label': `Tag ${m.name}`, list: 'tag-list', spellcheck: false });
    input.addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Escape') closePop(); });
    box.hidden = false;
    box.replaceChildren(...[
      el('header', {}, el('h3', {}, m.name), el('button', { class: 'ghost', 'aria-label': 'Close', onclick: closePop }, '×')),
      el('p', { class: 'sub' }, `${FAMILY_NAMES[m.family]} · ${m.cls}`),
      state.view === 'parallel'
        ? el('p', { class: 'vals' }, state.paxes.filter(s => m.d[s] != null).map(s => `${s.replace('rho', 'ρ')} ${AC.formatProp(s, m.d[s])}`).join(' · '))
        : row ? el('p', { class: 'vals' }, `${axisValue(plot.yAxis, row.y)} · ${axisValue(plot.xAxis, row.x)}`) : el('p', { class: 'vals muted' }, 'No value on these axes.'),
      applied.length || others.length ? el('div', { class: 'chips' },
        applied.map(t => el('button', { class: 'chip', style: `--c:${tags.color(t)}`, title: `Remove the tag ${t}`, onclick: () => tags.remove(t, [m.id]) }, t, ' ×')),
        others.map(t => el('button', { class: 'chip ghosted', style: `--c:${tags.color(t)}`, title: `Add the tag ${t}`, onclick: () => tags.add(t, [m.id]) }, '+ ', t))) : null,
      el('form', { onsubmit: e => { e.preventDefault(); const name = input.value.trim(); if (name) tags.add(name, [m.id]); } }, input, el('button', { type: 'submit' }, 'Tag')),
      el('div', { class: 'acts' },
        // Adding a label closes this card, because the card would otherwise sit on top of the new box.
        el('button', { class: labels.has(m.id) ? 'on' : '', disabled: !row && !labels.has(m.id), onclick: () => { if (labels.has(m.id)) { removeLabel(m.id); renderPop(false); } else { addLabels([m.id]); closePop(); } } }, labels.has(m.id) ? 'Remove label' : 'Label on chart'),
        el('button', { class: pinned.has(m.id) ? 'on' : '', onclick: () => { togglePin(m.id); renderPop(false); } }, pinned.has(m.id) ? 'Comparing' : 'Compare'),
        el('button', { onclick: () => { detailM = m; closePop(); renderDrawer(); } }, 'Sources')),
    ].filter(Boolean));
    positionFloating();
    if (focus && matchMedia('(pointer: fine)').matches) input.focus({ preventScroll: true });
  }
  function renderDrawer() {
    const box = $('drawer');
    box.hidden = !detailM;
    if (detailM) box.replaceChildren(AC.materialCard(detailM, () => { detailM = null; renderDrawer(); }));
  }
  function togglePin(id) { pinned.has(id) ? pinned.delete(id) : pinned.add(id); renderResults(); }

  /* ---------- several materials: the selection and its action bar ---------- */
  function setSelection(ids, focus = false) {
    selection = new Set(ids);
    plot.selected = new Set(selection);
    if (selection.size === 0 && !selBox) releaseFocus($('actions'));
    $('actions').hidden = selection.size === 0 && !selBox;
    $('sel-count').textContent = `${selection.size} selected`;
    $('sel-filter').hidden = !selBox;
    const label = $('sel-label');
    label.disabled = selection.size > LABEL_CAP;
    label.title = selection.size > LABEL_CAP ? `Label up to ${LABEL_CAP} at a time` : 'Put a label box on each of these';
    if (focus && selection.size && matchMedia('(pointer: fine)').matches) setTimeout(() => $('tag-name').focus({ preventScroll: true }));
  }
  function clearSelection() { selBox = null; setSelection([]); plot.draw(); }
  function applyTag() {
    const name = $('tag-name').value.trim();
    if (!name || !selection.size) return;
    $('tag-name').value = '';
    const ids = [...selection];
    selBox = null; setSelection([]);
    tags.add(name, ids);
  }
  $('tag-go').onclick = applyTag;
  $('tag-name').onkeydown = e => { if (e.key === 'Enter') applyTag(); e.stopPropagation(); if (e.key === 'Escape') { e.target.blur(); clearSelection(); } };
  $('sel-clear').onclick = clearSelection;
  $('sel-label').onclick = () => addLabels([...selection]);
  $('sel-isolate').onclick = () => { state.isolate = new Set(selection); clearSelection(); refresh(false); };
  $('sel-hide').onclick = () => { selection.forEach(id => state.hidden.add(id)); clearSelection(); refresh(); };
  $('sel-zoom').onclick = () => {
    const rows = plot.rows.filter(r => selection.has(r.m.id));
    if (rows.length) plot.animateTo(plot.computeFit(rows));
  };
  $('sel-filter').onclick = () => {
    if (!selBox) return;
    const xA = plot.xAxis, yA = plot.yAxis;
    stages.push({ type: 'region', x: state.x, y: state.y, xLog: state.xLog, yLog: state.yLog, x0: xA.inv(Math.min(selBox.x0, selBox.x1)), x1: xA.inv(Math.max(selBox.x0, selBox.x1)), y0: yA.inv(Math.min(selBox.y0, selBox.y1)), y1: yA.inv(Math.max(selBox.y0, selBox.y1)), enabled: true });
    clearSelection(); setStack(true); refresh();
  };
  function setMode(mode) {
    plot.mode = mode;
    document.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('on', b.dataset.mode === mode));
    plot.canvas.style.cursor = mode === 'pan' ? 'grab' : 'crosshair';
    if (armRegion && mode !== 'box') disarm();
  }
  document.querySelectorAll('[data-mode]').forEach(b => { b.onclick = () => setMode(b.dataset.mode); });
  function disarm() { armRegion = false; $('arm-note').hidden = true; }

  /* ---------- axes ---------- */
  function setAxes(changes) {
    Object.assign(state, changes);
    closePop(); selBox = null; setSelection([]);
    refresh(false);
    plot.fit();
  }
  function coverage(expr, other) { const a = new Axis(expr), b = new Axis(other); return db.materials.filter(m => Number.isFinite(a.value(m)) && Number.isFinite(b.value(m))).length; }
  function openAxis(which) {
    const pop = $('pop');
    if (!pop.hidden && pop.dataset.which === which) { pop.hidden = true; return; }
    pop.dataset.which = which; pop.hidden = false;
    const other = which === 'x' ? state.y : state.x, current = which === 'x' ? state.x : state.y, logKey = which + 'Log';
    const counts = db.props.map(p => [p, coverage(p.sym, other)]).sort((a, b) => b[1] - a[1]);
    const peak = Math.max(1, ...counts.map(c => c[1]));
    const input = el('input', { type: 'text', value: db.bySym[current] ? '' : current, placeholder: 'E^0.5/rho', 'aria-label': 'Formula', spellcheck: false });
    const msg = el('div', { class: 'formula-msg' }, 'Symbols: ' + db.props.map(p => p.sym).join(', '));
    const apply = () => {
      const c = AC.compile(input.value);
      if (c.error) { msg.textContent = c.error; msg.classList.add('bad'); return; }
      pop.hidden = true; setAxes({ [which]: input.value.trim() });
    };
    input.oninput = () => {
      if (!input.value.trim()) { msg.textContent = ''; msg.classList.remove('bad'); return; }
      const c = AC.compile(input.value);
      msg.classList.toggle('bad', !!c.error);
      msg.textContent = c.error || `${coverage(input.value, other).toLocaleString()} materials would plot`;
    };
    input.onkeydown = e => { e.stopPropagation(); if (e.key === 'Enter') apply(); };
    pop.replaceChildren(
      el('h2', {}, which === 'x' ? 'Horizontal axis' : 'Vertical axis'),
      el('div', { class: 'scale' }, 'Scale ', ...[['Log', true], ['Linear', false]].map(([label, value]) => el('button', { class: state[logKey] === value ? 'on' : '', onclick: () => { pop.hidden = true; setAxes({ [logKey]: value }); } }, label))),
      ...counts.map(([p, n]) => el('button', { class: 'prop-row' + (p.sym === current ? ' on' : ''), title: p.definition, onclick: () => { pop.hidden = true; setAxes({ [which]: p.sym }); } },
        el('span', {}, p.unit ? `${p.label} (${p.unit})` : p.label, el('span', { class: 'cov' }, el('i', { style: `width:${n / peak * 100}%` }))), el('span', { class: 'n' }, n.toLocaleString()))),
      el('h2', { style: 'margin-top:10px' }, 'Or write a formula'),
      el('div', { class: 'formula' }, input, el('button', { class: 'primary', onclick: apply }, 'Plot')), msg,
      el('div', { class: 'quick' }, ...['E/rho', 'E^0.5/rho', 'E^(1/3)/rho', 'UTS/rho', 'UTS^(2/3)/rho', 'Sy/E', 'k/rho', 'rho*cp', 'k/(rho*cp)'].map(f => el('button', { onclick: () => { input.value = f; input.oninput(); } }, f))));
    const button = $(which + '-btn').getBoundingClientRect(), host = pop.parentElement.getBoundingClientRect();
    const w = pop.offsetWidth, h = pop.offsetHeight;
    pop.style.left = clamp(which === 'x' ? button.left - host.left + button.width / 2 - w / 2 : 40, 8, Math.max(8, host.width - w - 8)) + 'px';
    pop.style.top = clamp(which === 'x' ? button.top - host.top - h - 8 : (host.height - h) / 2, 8, Math.max(8, host.height - h - 8)) + 'px';
    if (!db.bySym[current]) input.focus();
  }
  $('x-btn').onclick = () => openAxis('x');
  $('y-btn').onclick = () => openAxis('y');
  document.addEventListener('pointerdown', e => { if (!$('pop').hidden && !e.target.closest('#pop, .axis-btn')) $('pop').hidden = true; });

  /* ---------- right panel ---------- */
  const shapeSelect = $('shape'), groupSelect = $('group'), colorSelect = $('color'), sizeSelect = $('size');
  options(colorSelect, [['family', 'Family'], ['tag', 'My tags'], ...db.props.map(p => [p.sym, p.label])]);
  options(sizeSelect, [['none', 'Same size'], ...db.props.map(p => [p.sym, p.label])]);
  shapeSelect.value = state.shape; groupSelect.value = state.group; colorSelect.value = state.color; sizeSelect.value = state.size; $('ghosts').checked = state.ghosts;
  shapeSelect.onchange = () => { state.shape = shapeSelect.value; refresh(); };
  groupSelect.onchange = () => { state.group = groupSelect.value; refresh(); };
  colorSelect.onchange = () => { state.color = colorSelect.value; refresh(); };
  sizeSelect.onchange = () => { state.size = sizeSelect.value; refresh(); };
  $('ghosts').onchange = e => { state.ghosts = e.target.checked; refresh(); };
  $('ranges').onchange = e => { state.ranges = e.target.checked; plot.opts.showRanges = state.ranges; refresh(); };
  function renderFamilies(available) {
    $('families').replaceChildren(...Object.entries(FAMILY_NAMES).map(([key, name]) => el('button', {
      class: 'chip' + (state.families.has(key) ? '' : ' off'), style: `--c:${FAMILY_COLORS[key]}`, title: 'Click to toggle. Double-click for only this family.',
      onclick: () => { state.families.has(key) ? state.families.delete(key) : state.families.add(key); refresh(); },
      ondblclick: () => { state.families = new Set([key]); refresh(); },
    }, name, ' ', el('b', {}, available[key] || 0))));
  }
  function renderTags() {
    const names = tags.names();
    $('tag-empty').hidden = names.length > 0;
    $('tag-list').replaceChildren(...names.map(n => el('option', { value: n })));
    $('tag-rows').replaceChildren(...names.map(name => {
      const ids = tags.all()[name].ids;
      return el('div', { class: 'tag-row' },
        el('button', { class: 'chip' + (state.hiddenTags.has(name) ? ' off' : ''), style: `--c:${tags.color(name)}`, title: 'Show or hide the ring on these materials', onclick: () => { state.hiddenTags.has(name) ? state.hiddenTags.delete(name) : state.hiddenTags.add(name); refresh(); } }, name, ' ', el('b', {}, ids.length)),
        el('button', { class: 'ghost', title: 'Show only this tag', onclick: () => { state.isolate = new Set(ids); refresh(false); } }, 'Only'),
        el('button', { class: 'ghost', title: 'Add this tag to the selection stack', onclick: () => { stages.push({ type: 'tag', value: name, enabled: true }); setStack(true); refresh(); } }, 'Stack'),
        el('button', { class: 'ghost', disabled: ids.length > LABEL_CAP, title: ids.length > LABEL_CAP ? `Label up to ${LABEL_CAP} at a time` : 'Label these on the chart', onclick: () => addLabels(ids.filter(id => rowById.has(id))) }, 'Label'),
        el('button', { class: 'ghost', title: 'Delete tag', 'aria-label': `Delete ${name}`, onclick: () => { stages = stages.filter(s => !(s.type === 'tag' && s.value === name)); tags.drop(name); } }, '×'));
    }));
  }
  function readViews() { try { return JSON.parse(localStorage.getItem(VIEW_KEY)) || []; } catch { return []; } }
  function renderViews() {
    $('views').replaceChildren(...[...STARTER_VIEWS, ...readViews()].map(v => el('button', { title: `${v.y} vs ${v.x}`, onclick: () => {
      setView('chart');
      if (Array.isArray(v.stages)) { stages = JSON.parse(JSON.stringify(v.stages)); state.brief = v.brief || null; }
      setAxes({ x: v.x, y: v.y, xLog: v.xLog ?? true, yLog: v.yLog ?? true });
    } }, v.name)));
  }
  $('save-view').onclick = () => {
    const name = prompt('Name this view', `${new Axis(state.y).short} vs ${new Axis(state.x).short}`);
    if (!name) return;
    const list = readViews();
    list.push({ name, x: state.x, y: state.y, xLog: state.xLog, yLog: state.yLog, stages, brief: state.brief });
    try { localStorage.setItem(VIEW_KEY, JSON.stringify(list)); } catch { /* private window */ }
    renderViews();
  };
  const ramp = t => { const stops = [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]]; const f = clamp(t, 0, 1) * 3.999, i = Math.floor(f), k = f - i; const c = stops[i].map((v, n) => Math.round(v + (stops[i + 1][n] - v) * k)); return `rgb(${c})`; };
  const scales = new Map();
  function scaleFor(sym) {
    if (!scales.has(sym)) {
      const values = db.materials.map(m => m.d[sym]).filter(v => v > 0).map(Math.log10), lo = Math.min(...values), hi = Math.max(...values);
      scales.set(sym, { lo, hi, f: v => (Math.log10(v) - lo) / (hi - lo || 1) });
    }
    return scales.get(sym);
  }

  /* ---------- selection stack ---------- */
  function baseMaterials() {
    return db.materials.filter(m => state.families.has(m.family) && !state.hidden.has(m.id) && (!state.isolate || state.isolate.has(m.id)));
  }
  $('query-msg').textContent = QUERY_HINT;
  $('query-form').onsubmit = e => {
    e.preventDefault();
    const input = $('query'), msg = $('query-msg');
    try { stages.push(AC.parseQuery(input.value)); input.value = ''; msg.textContent = QUERY_HINT; msg.classList.remove('bad'); refresh(); }
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
  ].map(([label, make]) => el('button', { onclick: () => { stages.push(make()); refresh(); } }, '+ ' + label)),
  el('button', { id: 'add-region', title: 'Drag on the chart to add a region', onclick: () => { setView('chart'); armRegion = true; clearSelection(); setMode('box'); armRegion = true; $('arm-note').hidden = false; if (isPhone()) setStack(false); } }, '+ Region'),
  el('button', { id: 'add-line', title: 'Add a dashed line you can drag on the chart', onclick: addLine }, '+ Line'));
  function addLine() {
    setView('chart');
    if (!state.xLog || !state.yLog) { $('query-msg').textContent = 'A selection line needs log scales on both axes.'; $('query-msg').classList.add('bad'); return; }
    const known = db.indices.find(i => i.x === state.x && i.y === state.y);
    const slope = known?.expression.includes('1/2') ? 2 : known?.expression.includes('1/3') ? 3 : known?.expression.includes('2/3') ? 1.5 : 1;
    const v = plot.view;
    stages.push({ type: 'index', x: state.x, y: state.y, slope, c: (v.y0 + v.y1) / 2 - slope * (v.x0 + v.x1) / 2, above: true, enabled: true });
    refresh();
  }
  function stageTitle(s) {
    switch (s.type) {
      case 'family': return 'Family: ' + (s.values.length === Object.keys(FAMILY_NAMES).length ? 'all' : s.values.map(v => FAMILY_NAMES[v]).join(', ') || 'none');
      case 'limit': {
        const axis = new Axis(s.expr, false);
        const parts = [s.min != null ? `≥ ${formatValue(s.min)}` : '', s.max != null ? `≤ ${formatValue(s.max)}` : ''].filter(Boolean).join(' and ');
        return `${axis.short} ${parts || '(any)'}${axis.prop && parts ? ' ' + axis.prop.unit : ''}`;
      }
      case 'class': return 'Class: ' + (s.values.join(', ') || 'choose');
      case 'org': return 'Source: ' + (s.values.join(', ') || 'choose');
      case 'tag': return 'Tag: ' + (s.value || 'choose');
      case 'text': return 'Search: ' + (s.value || 'type');
      case 'region': return `Region on ${new Axis(s.y).short} vs ${new Axis(s.x).short}`;
      case 'index': return s.brief ? `Brief: beats the index line` : `${s.above ? 'Above' : 'Below'} line, slope ${s.slope}`;
      default: return s.type;
    }
  }
  function histogram(s, inputs) {
    const base = new Axis(s.expr, true);
    const before = AC.runStages(stages.slice(0, stages.indexOf(s)), baseMaterials()).rows;
    const values = before.map(m => base.value(m)).filter(Number.isFinite);
    const wrap = el('div', { class: 'hist' }), canvas = el('canvas');
    wrap.append(canvas);
    if (values.length < 2) return wrap;
    const lo = Math.log10(Math.min(...values)), hi = Math.log10(Math.max(...values)) + 1e-6, bins = 44;
    const counts = new Array(bins).fill(0);
    values.forEach(v => { counts[Math.min(bins - 1, Math.floor((Math.log10(v) - lo) / (hi - lo) * bins))]++; });
    const peak = Math.max(...counts);
    const position = v => v > 0 ? (Math.log10(v) - lo) / (hi - lo) : 0;
    const paint = () => {
      const w = wrap.clientWidth || 300, h = 50, dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = w * dpr; canvas.height = h * dpr;
      const c = canvas.getContext('2d'); c.scale(dpr, dpr);
      const a = s.min != null ? position(s.min) : 0, b = s.max != null ? position(s.max) : 1;
      counts.forEach((n, i) => {
        const pos = (i + .5) / bins;
        c.fillStyle = pos >= a && pos <= b ? cssVar('--ink') : cssVar('--line');
        const bh = n ? Math.max(2, Math.sqrt(n / peak) * (h - 8)) : 0;
        c.fillRect(i / bins * w + .5, h - 4 - bh, w / bins - 1, bh);
      });
      c.fillStyle = cssVar('--ink');
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
    wrap.onpointerup = () => { side = null; renderStages(); };
    return wrap;
  }
  function editor(s) {
    const body = el('div', { class: 'stage-body' });
    if (s.type === 'family') {
      const box = el('div', { class: 'chips' });
      for (const [k, name] of Object.entries(FAMILY_NAMES)) box.append(el('button', { class: 'chip' + (s.values.includes(k) ? '' : ' off'), style: `--c:${FAMILY_COLORS[k]}`, onclick: () => { s.values = s.values.includes(k) ? s.values.filter(v => v !== k) : [...s.values, k]; refresh(); } }, name));
      body.append(box);
    } else if (s.type === 'limit') {
      const min = el('input', { type: 'number', step: 'any', value: s.min ?? '', placeholder: 'min', 'aria-label': 'Minimum', onchange: () => { s.min = num(parseFloat(min.value)); refresh(); } });
      const max = el('input', { type: 'number', step: 'any', value: s.max ?? '', placeholder: 'max', 'aria-label': 'Maximum', onchange: () => { s.max = num(parseFloat(max.value)); refresh(); } });
      const select = el('select', { 'aria-label': 'Property', onchange: () => { s.expr = select.value; s.min = s.max = null; refresh(); } });
      options(select, db.bySym[s.expr] ? propOptions : [[s.expr, s.expr], ...propOptions]);
      select.value = s.expr;
      body.append(histogram(s, { min, max }), el('div', { class: 'range-row' }, select, min, max));
    } else if (s.type === 'class' || s.type === 'org') {
      const before = AC.runStages(stages.slice(0, stages.indexOf(s)), baseMaterials()).rows, counts = new Map();
      before.forEach(m => (s.type === 'class' ? [m.cls] : m.orgs).forEach(c => counts.set(c, (counts.get(c) || 0) + 1)));
      const box = el('div', { class: 'chips', style: 'max-height:128px;overflow:auto' });
      [...counts.entries()].sort((a, b) => b[1] - a[1]).forEach(([name, n]) => box.append(el('button', { class: 'chip' + (s.values.includes(name) ? '' : ' off'), onclick: () => { s.values = s.values.includes(name) ? s.values.filter(v => v !== name) : [...s.values, name]; refresh(); } }, name, ' ', el('b', {}, n))));
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
      const flip = el('button', { onclick: () => { s.above = !s.above; refresh(); } }, s.above ? 'Keep above' : 'Keep below');
      const row = el('div', { class: 'range-row' }, flip);
      if (!s.brief) {
        const slope = el('select', { 'aria-label': 'Slope', onchange: () => { s.slope = parseFloat(slope.value); refresh(); } });
        options(slope, [[1, 'Slope 1: tie'], [1.5, 'Slope 1.5: strong beam'], [2, 'Slope 2: stiff beam'], [3, 'Slope 3: stiff plate']]);
        slope.value = s.slope;
        row.append(slope);
      }
      const off = s.x !== state.x || s.y !== state.y;
      body.append(row, el('small', {}, off ? `Set on ${new Axis(s.y).short} vs ${new Axis(s.x).short}. It still filters on these axes.` : 'Drag the dashed line on the chart.'));
    } else if (s.type === 'region') {
      const a = new Axis(s.x), b = new Axis(s.y);
      body.append(el('small', {}, `${a.short} ${formatValue(s.x0)} to ${formatValue(s.x1)}; ${b.short} ${formatValue(s.y0)} to ${formatValue(s.y1)}`));
    }
    return body;
  }
  let dragFrom = null;
  function renderStages() {
    const host = $('stages'), base = baseMaterials(), { counts } = AC.runStages(stages, base);
    const total = base.length;
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
        i > 0 ? el('button', { class: 'ghost', title: 'Move up', 'aria-label': 'Move stage up', onclick: () => { [stages[i - 1], stages[i]] = [stages[i], stages[i - 1]]; refresh(); } }, '↑') : null,
        el('button', { class: 'ghost', title: s.enabled === false ? 'Turn on' : 'Turn off', 'aria-pressed': String(s.enabled !== false), onclick: () => { s.enabled = s.enabled === false; refresh(); } }, s.enabled === false ? 'Off' : 'On'),
        el('button', { class: 'ghost', title: 'Remove', 'aria-label': 'Remove stage', onclick: () => { stages.splice(i, 1); if (s.brief) state.brief = null; refresh(); } }, '×'));
      card.append(top, editor(s), el('div', { class: 'funnel' }, el('span', { class: 'bar' }, el('i', { style: `width:${total ? c.after / total * 100 : 0}%` })), el('span', {}, `${c.before.toLocaleString()} → ${c.after.toLocaleString()}`)));
      nodes.push(card);
    });
    nodes.push(el('div', { class: 'end' }, el('span', {}, 'Remaining'), el('span', {}, (counts.at(-1)?.after ?? total).toLocaleString())));
    host.replaceChildren(...nodes);
  }
  function updateFunnels() {
    const base = baseMaterials(), { counts } = AC.runStages(stages, base);
    document.querySelectorAll('#stages .funnel').forEach((node, i) => {
      const c = counts[i];
      if (c) { node.lastChild.textContent = `${c.before.toLocaleString()} → ${c.after.toLocaleString()}`; node.querySelector('i').style.width = (base.length ? c.after / base.length * 100 : 0) + '%'; }
    });
    const end = document.querySelector('#stages .end span:last-child');
    if (end) end.textContent = (counts.at(-1)?.after ?? base.length).toLocaleString();
  }
  function setStack(open) {
    state.stackOpen = open;
    $('stack').hidden = !open;
    $('stack-btn').classList.toggle('on', open);
    if (open) renderStages();
    writeHash();
  }
  $('stack-btn').onclick = () => setStack(!state.stackOpen);
  $('stack-close').onclick = () => setStack(false);

  /* ---------- design brief: sets the axes and adds a line stage, so it lives in the same stack ---------- */
  $('b-part').append(...Object.keys(BRIEFS).map(k => el('option', { value: k }, k)));
  $('b-driver').append(...Object.entries(DRIVERS).map(([k, v]) => el('option', { value: k }, v)));
  $('b-part').value = state.brief?.part || 'beam (in bending)';
  $('b-driver').value = state.brief?.driver || 'stiff';
  function chosenBrief() { return BRIEFS[$('b-part').value][$('b-driver').value]; }
  function renderBrief() {
    const [, , , expression, indexId] = chosenBrief(), index = db.indices.find(i => i.id === indexId);
    $('b-why').replaceChildren('Index ', el('code', {}, 'M = ' + expression), `. Higher is better. ${index.source}` + ($('b-driver').value === 'strong' ? ' The index is written with yield strength. This uses tensile strength for now, since more materials have it.' : ''));
    $('b-clear').hidden = !state.brief;
    $('brief-box').open = $('brief-box').open || !!state.brief;
  }
  function useBrief() {
    setView('chart');
    const [ySym, numerator, slope] = chosenBrief();
    stages = stages.filter(s => !s.brief);
    state.brief = { part: $('b-part').value, driver: $('b-driver').value };
    const pool = AC.runStages(stages, baseMaterials()).rows;
    const mA = new Axis(`${numerator}/rho`);
    const scored = pool.filter(m => Number.isFinite(mA.value(m))).map(m => Math.log10(m.d[ySym]) - slope * Math.log10(m.d.rho)).sort((a, b) => b - a);
    const c = scored.length ? scored[Math.min(scored.length - 1, Math.floor(scored.length * .12))] : 0;
    stages.push({ type: 'index', x: 'rho', y: ySym, slope, c, above: true, enabled: true, brief: true });
    sortKey = 'auto';
    setAxes({ x: 'rho', y: ySym, xLog: true, yLog: true });
    renderBrief();
  }
  $('b-use').onclick = useBrief;
  $('b-part').onchange = $('b-driver').onchange = () => { if (state.brief) useBrief(); else renderBrief(); };
  $('b-clear').onclick = () => { stages = stages.filter(s => !s.brief); state.brief = null; refresh(); renderBrief(); };
  function briefScore() {
    if (!state.brief) return null;
    const entry = BRIEFS[state.brief.part]?.[state.brief.driver];
    if (!entry) return null;
    const axis = new Axis(`${entry[1]}/rho`);
    return m => axis.value(m);
  }

  /* ---------- results and compare ---------- */
  function setResults(open) {
    state.resultsOpen = open;
    $('results-box').hidden = !open;
    $('results-btn').classList.toggle('on', open);
    if (open) renderResults();
    writeHash();
  }
  $('results-btn').onclick = () => setResults(!state.resultsOpen);
  $('tab-results').onclick = () => { resultTab = 'results'; renderResults(); };
  $('tab-compare').onclick = () => { resultTab = 'compare'; renderResults(); };
  options($('add-col'), [['', '+ Column'], ...db.props.map(p => [p.sym, p.label])]);
  $('add-col').onchange = e => { if (e.target.value && !columns.includes(e.target.value)) columns.push(e.target.value); e.target.value = ''; renderResults(); };
  $('tag-apply').onclick = () => { const input = $('tag-input'), name = input.value.trim(); if (name && current.length) { input.value = ''; tags.add(name, current.map(m => m.id)); } };
  $('tag-input').addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Enter') $('tag-apply').click(); });
  $('export').onclick = () => AC.downloadCsv('selection.csv', ['Material', 'Family', ...db.props.map(p => `${p.label} (${p.unit})`)], current.map(m => [m.name, FAMILY_NAMES[m.family], ...db.props.map(p => m.d[p.sym] ?? '')]));
  function setSort(key) { if (sortKey === key) sortDir = -sortDir; else { sortKey = key; sortDir = key === 'name' ? 1 : -1; } renderResults(); }
  function renderResults() {
    if (!state.resultsOpen) return;
    $('tab-results').classList.toggle('on', resultTab === 'results');
    $('tab-compare').classList.toggle('on', resultTab === 'compare');
    $('results-tools').hidden = resultTab !== 'results';
    $('tab-compare').textContent = pinned.size ? `Compare ${pinned.size}` : 'Compare';
    if (resultTab === 'compare') { renderCompare(); return; }
    const score = briefScore();
    const best = score ? Math.max(0, ...current.map(score).filter(Number.isFinite)) : 0;
    const xProp = db.bySym[state.x] ? state.x : null, yProp = db.bySym[state.y] ? state.y : null;
    const cols = [...new Set([yProp, xProp, ...columns])].filter(c => c && db.bySym[c]);
    const key = sortKey === 'auto' ? (score ? 'score' : yProp || cols[0]) : sortKey;
    const read = m => key === 'score' ? score?.(m) : m.d[key];
    const rows = [...current].sort((a, b) => {
      if (key === 'name') return sortDir * a.name.localeCompare(b.name);
      const va = read(a), vb = read(b), okA = Number.isFinite(va), okB = Number.isFinite(vb);
      if (!okA || !okB) return okA ? -1 : okB ? 1 : 0;
      return sortDir * (va - vb);
    });
    const onParallel = state.view === 'parallel';
    const plotted = onParallel ? current.filter(m => state.paxes.every(s => m.d[s] > 0)).length : current.filter(m => { const r = rowById.get(m.id); return r && !r.dim; }).length;
    $('result-count').textContent = `${current.length.toLocaleString()} results, ${plotted.toLocaleString()} on ${onParallel ? 'these axes' : 'this chart'}` + (current.length > 150 ? ', first 150 listed' : '');
    const head = el('tr', {}, el('th', { onclick: () => setSort('name') }, 'Material'),
      score ? el('th', { onclick: () => setSort('score'), title: 'Performance index as a percentage of the best result' }, 'Index, % of best') : null,
      cols.map(c => el('th', { onclick: e => { if (e.shiftKey) { columns = columns.filter(k => k !== c); renderResults(); } else setSort(c); }, title: 'Sort. Shift+click removes the column.' }, db.bySym[c].unit ? `${db.bySym[c].label} (${db.bySym[c].unit})` : db.bySym[c].label)),
      el('th', { 'aria-label': 'Compare' }));
    const body = rows.slice(0, 150).map(m => {
      const s = score?.(m);
      return el('tr', { class: popM?.id === m.id ? 'sel' : '', onclick: () => { if (rowById.get(m.id)) openPop(m); else { detailM = m; renderDrawer(); } } },
        el('td', {}, el('span', { class: 'dot', style: `background:${FAMILY_COLORS[m.family]}` }), m.name),
        score ? el('td', {}, Number.isFinite(s) && best ? Math.round(s / best * 100) + '%' : '–') : null,
        cols.map(c => el('td', {}, m.d[c] != null ? formatValue(m.d[c]) : '–')),
        el('td', { class: 'pin' }, el('button', { class: 'ghost', 'aria-label': pinned.has(m.id) ? 'Remove from comparison' : 'Add to comparison', title: 'Compare', onclick: e => { e.stopPropagation(); togglePin(m.id); } }, pinned.has(m.id) ? '✓' : '+')));
    });
    $('results-scroll').replaceChildren(el('table', { class: 'results' }, el('thead', {}, head), el('tbody', {}, body)));
  }
  function renderCompare() {
    const host = $('results-scroll'), list = [...pinned].map(id => db.byId[id]);
    $('result-count').textContent = '';
    if (!list.length) { host.replaceChildren(el('p', { class: 'compare-empty' }, 'Click a point and choose Compare, or use + in the results.')); return; }
    const props = db.props.filter(p => list.some(m => m.d[p.sym] != null));
    const lowerBetter = new Set(['rho']);
    host.replaceChildren(
      el('div', { style: 'display:flex;gap:4px;padding:6px 10px 0' },
        el('button', { onclick: () => { tags.add('Compared', [...pinned]); } }, 'Save as tag "Compared"'),
        el('button', { disabled: list.length > LABEL_CAP, onclick: () => addLabels(list.filter(m => rowById.has(m.id)).map(m => m.id)) }, 'Label these'),
        el('button', { class: 'ghost', onclick: () => { pinned.clear(); renderResults(); } }, 'Clear')),
      el('table', { class: 'compare' }, el('thead', {}, el('tr', {}, el('th', {}), list.map(m => el('th', { title: m.name }, m.name)))),
        el('tbody', {}, props.map(p => {
          const values = list.map(m => m.d[p.sym]).filter(v => v != null);
          const top = lowerBetter.has(p.sym) ? Math.min(...values) : Math.max(...values);
          return el('tr', {}, el('td', {}, p.unit ? `${p.label} (${p.unit})` : p.label), list.map(m => el('td', { class: list.length > 1 && m.d[p.sym] === top ? 'best' : '' }, m.d[p.sym] != null ? formatValue(m.d[p.sym]) : '–')));
        })))
    );
  }

  /* ---------- parallel axes: dragging on an axis edits a limit stage, so both views share one filter chain ---------- */
  const pv = { W: 0, H: 0, raf: 0, drag: null, hover: null, rows: [], ranges: {}, live: () => true, color: m => FAMILY_COLORS[m.family] };
  const pPad = { l: 44, r: 44, t: 48, b: 26 };
  const pCanvas = el('canvas'), pTip = el('div', { class: 'ac-tip', hidden: true });
  const pHint = el('div', { class: 'p-hint' }, 'Drag along an axis to filter. Filters also appear in the stack. Click a filtered axis to clear it.');
  $('p-stage').append(pCanvas, pTip, pHint);
  const pCtx = pCanvas.getContext('2d');
  const pX = i => pPad.l + (pv.W - pPad.l - pPad.r) * i / Math.max(1, state.paxes.length - 1);
  const pY = (s, v) => pv.H - pPad.b - (Math.log10(v) - pv.ranges[s][0]) / (pv.ranges[s][1] - pv.ranges[s][0]) * (pv.H - pPad.t - pPad.b);
  const pValue = (s, y) => 10 ** (pv.ranges[s][0] + (pv.H - pPad.b - y) / (pv.H - pPad.t - pPad.b) * (pv.ranges[s][1] - pv.ranges[s][0]));
  const limitStage = s => stages.find(st => st.type === 'limit' && st.expr === s && st.enabled !== false);
  function pTicks(lo, hi) {
    const span = hi - lo, out = [];
    const steps = span >= 1.5 ? [1] : span >= .6 ? [1, 2, 5] : [1, 1.5, 2, 3, 5, 7];
    const every = span >= 7 ? 2 : 1;
    for (let d = Math.floor(lo); d <= hi; d += every) for (const k of steps) { const t = d + Math.log10(k); if (t >= lo - 1e-9 && t <= hi + 1e-9) out.push(t); }
    return out.length >= 2 ? out : [lo, hi];
  }
  function pPath(m) {
    pCtx.beginPath();
    state.paxes.forEach((s, i) => { const X = pX(i), Y = pY(s, m.d[s]); i ? pCtx.lineTo(X, Y) : pCtx.moveTo(X, Y); });
    pCtx.stroke();
  }
  function paintParallel() {
    pv.raf = 0;
    if (state.view !== 'parallel') return;
    const rect = $('p-stage').getBoundingClientRect();
    pv.W = rect.width; pv.H = rect.height;
    const dpr = Math.min(devicePixelRatio || 1, 2), ctx = pCtx;
    if (pCanvas.width !== Math.round(pv.W * dpr) || pCanvas.height !== Math.round(pv.H * dpr)) {
      pCanvas.width = Math.round(pv.W * dpr); pCanvas.height = Math.round(pv.H * dpr);
      pCanvas.style.width = pv.W + 'px'; pCanvas.style.height = pv.H + 'px';
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, pv.W, pv.H);
    ctx.fillStyle = cssVar('--plot'); ctx.fillRect(0, 0, pv.W, pv.H);
    if (!pv.rows.length) return;
    const ink = cssVar('--ink'), muted = cssVar('--ink-2'), plotBg = cssVar('--plot');
    const on = pv.rows.filter(pv.live), off = pv.rows.filter(m => !pv.live(m));
    ctx.lineWidth = 1;
    if (state.ghosts) { ctx.strokeStyle = cssVar('--ghost'); off.forEach(pPath); }
    ctx.globalAlpha = on.length > 300 ? .35 : .7;
    for (const m of on) { ctx.strokeStyle = pv.color(m); pPath(m); }
    ctx.globalAlpha = 1;
    // Tagged materials stay readable among hundreds of lines.
    ctx.lineWidth = 2;
    for (const m of on) { const t = tags.of(m.id).find(n => !state.hiddenTags.has(n)); if (t) { ctx.strokeStyle = tags.color(t); pPath(m); } }
    ctx.strokeStyle = ink; ctx.lineWidth = 1.6;
    for (const m of pv.rows) if (selection.has(m.id)) pPath(m);
    ctx.lineWidth = 2.6;
    for (const m of [popM, pv.hover]) if (m && m.d && state.paxes.every(s => m.d[s] > 0)) pPath(m);
    ctx.lineWidth = 1;
    const room = (pv.W - pPad.l - pPad.r) / Math.max(1, state.paxes.length - 1);
    state.paxes.forEach((s, i) => {
      const X = pX(i), prop = db.bySym[s], last = state.paxes.length - 1;
      ctx.strokeStyle = muted; ctx.beginPath(); ctx.moveTo(X + .5, pPad.t); ctx.lineTo(X + .5, pv.H - pPad.b); ctx.stroke();
      ctx.textBaseline = 'alphabetic';
      ctx.textAlign = i === 0 ? 'left' : i === last ? 'right' : 'center';
      const tx = i === 0 ? X - pPad.l + 8 : i === last ? X + pPad.r - 8 : X;
      ctx.font = '600 12px ' + cssVar('--sans'); ctx.fillStyle = ink;
      // End titles sit fully on one side of their axis, so they get less room before they hit a neighbour.
      const titleRoom = i === 0 || i === last ? room * .62 : room * .85;
      ctx.fillText(ctx.measureText(prop.label).width > titleRoom ? prop.sym.replace('rho', 'ρ') : prop.label, tx, 18);
      ctx.font = '11px ' + cssVar('--sans'); ctx.fillStyle = muted;
      ctx.fillText(prop.unit, tx, 33);
      ctx.textAlign = 'right';
      const [lo, hi] = pv.ranges[s];
      let lastY = Infinity;
      for (const t of pTicks(lo, hi)) {
        const Y = pY(s, 10 ** t);
        ctx.fillStyle = muted; ctx.fillRect(X - 3, Y, 6, 1);
        if (Math.abs(lastY - Y) < 15) continue;
        lastY = Y;
        ctx.lineWidth = 3; ctx.strokeStyle = plotBg; ctx.lineJoin = 'round';
        ctx.strokeText(formatValue(10 ** t), X - 6, Y + 4); ctx.fillText(formatValue(10 ** t), X - 6, Y + 4); ctx.lineWidth = 1;
      }
      const st = limitStage(s);
      if (st && (st.min != null || st.max != null)) {
        const y0 = st.max != null ? clamp(pY(s, st.max), pPad.t, pv.H - pPad.b) : pPad.t, y1 = st.min != null ? clamp(pY(s, st.min), pPad.t, pv.H - pPad.b) : pv.H - pPad.b;
        ctx.fillStyle = ink; ctx.globalAlpha = .18; ctx.fillRect(X - 9, y0, 18, y1 - y0); ctx.globalAlpha = 1;
        ctx.strokeStyle = ink; ctx.strokeRect(X - 9, y0, 18, y1 - y0);
        ctx.textAlign = i === last ? 'right' : 'left'; ctx.font = '600 11px ' + cssVar('--sans'); ctx.fillStyle = ink;
        const side = i === last ? X - 13 : X + 13;
        ctx.lineWidth = 3; ctx.strokeStyle = plotBg;
        if (st.max != null) { ctx.strokeText(formatValue(st.max), side, y0 + 10); ctx.fillText(formatValue(st.max), side, y0 + 10); }
        if (st.min != null) { ctx.strokeText(formatValue(st.min), side, y1 - 3); ctx.fillText(formatValue(st.min), side, y1 - 3); }
        ctx.lineWidth = 1; ctx.font = '11px ' + cssVar('--sans'); ctx.textAlign = 'right';
      }
    });
  }
  function drawParallel() { if (state.view === 'parallel' && !pv.raf) pv.raf = requestAnimationFrame(paintParallel); }
  function pNearest(x, y, limit = 7) {
    let best = null, bestD = limit * limit;
    const n = state.paxes.length;
    const seg = clamp(Math.floor((x - pX(0)) / ((pX(n - 1) - pX(0)) / (n - 1) || 1)), 0, n - 2);
    const x0 = pX(seg), x1 = pX(seg + 1), k = clamp((x - x0) / (x1 - x0 || 1), 0, 1), a = state.paxes[seg], b = state.paxes[seg + 1];
    for (const m of pv.rows) {
      if (!pv.live(m)) continue;
      const ya = pY(a, m.d[a]), d = (ya + (pY(b, m.d[b]) - ya) * k - y) ** 2;
      if (d < bestD) { bestD = d; best = m; }
    }
    return best;
  }
  function pBrush(drag, y) {
    let stage = limitStage(drag.s), created = false;
    if (!stage) { stage = { type: 'limit', expr: drag.s, min: null, max: null, enabled: true }; stages.push(stage); created = true; }
    const top = Math.min(y, drag.y), bottom = Math.max(y, drag.y);
    // A drag that reaches the end of an axis leaves that side open, so rounding cannot drop the last material.
    stage.max = top <= pPad.t + 1 ? null : +pValue(drag.s, top).toPrecision(3);
    stage.min = bottom >= pv.H - pPad.b - 1 ? null : +pValue(drag.s, bottom).toPrecision(3);
    refresh(true, !created);
  }
  pCanvas.addEventListener('pointerdown', e => {
    const x = e.offsetX, y = e.offsetY, i = state.paxes.findIndex((_, n) => Math.abs(pX(n) - x) < 20);
    pCanvas.setPointerCapture(e.pointerId);
    pTip.hidden = true;
    pv.drag = i >= 0 && pv.rows.length ? { s: state.paxes[i], y: clamp(y, pPad.t, pv.H - pPad.b), moved: false, touch: e.pointerType === 'touch' } : { s: null, touch: e.pointerType === 'touch' };
  });
  pCanvas.addEventListener('pointermove', e => {
    const x = e.offsetX, y = e.offsetY, drag = pv.drag;
    if (drag?.s) {
      const at = clamp(y, pPad.t, pv.H - pPad.b);
      if (Math.abs(at - drag.y) > 3) drag.moved = true;
      if (drag.moved) pBrush(drag, at);
      return;
    }
    if (drag || !pv.rows.length) return;
    const nearAxis = state.paxes.some((_, n) => Math.abs(pX(n) - x) < 20);
    pCanvas.style.cursor = nearAxis ? 'ns-resize' : 'default';
    const hit = pNearest(x, y);
    if (hit !== pv.hover) { pv.hover = hit; drawParallel(); }
    if (hit) {
      pTip.replaceChildren(el('strong', {}, hit.name), ...state.paxes.map(s => el('span', {}, `${db.bySym[s].label}: ${AC.formatProp(s, hit.d[s])}`)));
      pTip.hidden = false;
      const w = pTip.offsetWidth, h = pTip.offsetHeight;
      pTip.style.left = clamp(x + 14 + w > pv.W ? x - w - 14 : x + 14, 4, Math.max(4, pv.W - w - 4)) + 'px';
      pTip.style.top = clamp(y - h - 10 < 0 ? y + 14 : y - h - 10, 4, Math.max(4, pv.H - h - 4)) + 'px';
      if (!nearAxis) pCanvas.style.cursor = 'pointer';
    } else pTip.hidden = true;
  });
  const pRelease = e => {
    const drag = pv.drag;
    pv.drag = null;
    if (!drag) return;
    if (drag.s && drag.moved) { refresh(true); return; }
    if (drag.s) {
      const st = limitStage(drag.s);
      if (st && (st.min != null || st.max != null)) { stages.splice(stages.indexOf(st), 1); refresh(true); return; }
    }
    if (e.type === 'pointercancel' || !pv.rows.length) return;
    const stageBox = $('p-stage').getBoundingClientRect(), wrapBox = $('wrap').getBoundingClientRect();
    const hit = pNearest(e.offsetX, e.offsetY, drag.touch ? 16 : 7);
    if (hit) openPop(hit, [e.offsetX + stageBox.left - wrapBox.left, e.offsetY + stageBox.top - wrapBox.top]);
    else closePop();
  };
  pCanvas.addEventListener('pointerup', pRelease);
  pCanvas.addEventListener('pointercancel', pRelease);
  pCanvas.addEventListener('pointerleave', () => { if (!pv.drag && pv.hover) { pv.hover = null; pTip.hidden = true; drawParallel(); } });
  new ResizeObserver(drawParallel).observe($('p-stage'));
  function renderParallelBar() {
    const n = pv.rows.length, base = baseMaterials().length, passing = pv.rows.filter(pv.live).length;
    const coverage = el('span', { class: 'p-coverage' + (n < 200 ? ' warn' : '') }, `${n.toLocaleString()} of ${base.toLocaleString()} have all ${state.paxes.length} values` + (passing !== n ? `, ${passing.toLocaleString()} pass` : ''));
    const open = document.activeElement?.closest?.('#p-bar') ? document.activeElement.getAttribute('aria-label') : null;
    $('p-bar').replaceChildren(...state.paxes.map((sym, i) => {
      const select = el('select', { 'aria-label': `Axis ${i + 1}`, onchange: () => { state.paxes[i] = select.value; refresh(); } }, db.props.filter(p => p.sym === sym || !state.paxes.includes(p.sym)).map(p => el('option', { value: p.sym }, p.label)));
      select.value = sym;
      return el('span', { class: 'axis-chip' },
        i > 0 ? el('button', { class: 'ghost', title: 'Move this axis left', 'aria-label': `Move ${db.bySym[sym].label} left`, onclick: () => { [state.paxes[i - 1], state.paxes[i]] = [state.paxes[i], state.paxes[i - 1]]; refresh(); } }, '←') : null,
        select,
        state.paxes.length > 2 ? el('button', { class: 'ghost', 'aria-label': `Remove ${db.bySym[sym].label}`, title: 'Remove this axis', onclick: () => { state.paxes.splice(i, 1); refresh(); } }, '×') : null);
    }), state.paxes.length < db.props.length ? el('button', { id: 'p-add', title: 'Adds the property that keeps the most materials. Change it with its menu.', onclick: () => {
      const rows = baseMaterials().filter(m => state.paxes.every(s => m.d[s] > 0));
      const next = db.props.map(p => p.sym).filter(s => !state.paxes.includes(s)).map(s => [s, rows.filter(m => m.d[s] > 0).length]).sort((a, b) => b[1] - a[1])[0]?.[0];
      if (next) { state.paxes.push(next); refresh(); }
    } }, '+ Add axis') : null, coverage);
    if (open) $('p-bar').querySelector(`[aria-label="${open}"]`)?.focus();
    pHint.hidden = !n || isPhone();
    const empty = $('p-stage').querySelector('.p-empty');
    if (!n && !empty) $('p-stage').append(el('div', { class: 'p-empty' }, 'No material has all of these values. Remove an axis or turn more families on.'));
    if (n && empty) empty.remove();
  }
  function setView(name) {
    if (state.view === name && document.body.classList.contains(name === 'parallel' ? 'parallel-on' : 'chart-on')) return;
    state.view = name;
    const parallelOn = name === 'parallel';
    document.body.classList.toggle('parallel-on', parallelOn);
    document.body.classList.toggle('chart-on', !parallelOn);
    $('parallel').hidden = !parallelOn;
    $('view-chart').classList.toggle('on', !parallelOn); $('view-chart').setAttribute('aria-pressed', String(!parallelOn));
    $('view-parallel').classList.toggle('on', parallelOn); $('view-parallel').setAttribute('aria-pressed', String(parallelOn));
    closePop(); selBox = null; setSelection([]); disarm();
    pv.hover = null; pTip.hidden = true;
    refresh();
  }
  $('view-chart').onclick = () => setView('chart');
  $('view-parallel').onclick = () => setView('parallel');

  /* ---------- everything flows from one refresh ---------- */
  function writeHash() {
    const shared = { view: state.view, paxes: state.paxes, x: state.x, y: state.y, xLog: state.xLog, yLog: state.yLog, shape: state.shape, group: state.group, color: state.color, size: state.size, ghosts: state.ghosts, stackOpen: state.stackOpen, resultsOpen: state.resultsOpen, brief: state.brief, families: [...state.families], stages };
    history.replaceState(null, '', '#' + encodeURIComponent(JSON.stringify(shared)));
  }
  const availableCache = new Map();
  function availableFor(xA, yA) {
    const key = `${state.x}|${state.y}|${state.xLog}|${state.yLog}`;
    if (!availableCache.has(key)) {
      const counts = {};
      AC.chartRows(db.materials, xA, yA).forEach(r => { counts[r.m.family] = (counts[r.m.family] || 0) + 1; });
      availableCache.set(key, counts);
    }
    return availableCache.get(key);
  }
  function refresh(keep = true, light = false) {
    const started = performance.now();
    const xA = new Axis(state.x, state.xLog), yA = new Axis(state.y, state.yLog);
    $('x-btn').textContent = xA.label + ' ▾'; $('y-btn').textContent = yA.label + ' ▾';
    const colorScale = db.bySym[state.color] ? scaleFor(state.color) : null;
    const sizeScale = db.bySym[state.size] ? scaleFor(state.size) : null;
    const visibleTag = m => tags.of(m.id).find(n => !state.hiddenTags.has(n));
    const colorOf = m => {
      if (colorScale) return m.d[state.color] > 0 ? ramp(colorScale.f(m.d[state.color])) : '#9ca3af';
      if (state.color === 'tag') { const t = visibleTag(m); return t ? tags.color(t) : '#9ca3af'; }
      return FAMILY_COLORS[m.family];
    };
    const ringOf = state.color === 'tag' ? null : m => { const t = visibleTag(m); return t ? tags.color(t) : null; };
    const sizeOf = sizeScale ? m => m.d[state.size] > 0 ? 2 + sizeScale.f(m.d[state.size]) * 8 : 2 : null;
    const rangeOf = state.ranges ? m => {
      const xr = db.bySym[state.x] && m.range[state.x], yr = db.bySym[state.y] && m.range[state.y];
      return { x: xr && xr[0] !== xr[1] ? xr : null, y: yr && yr[0] !== yr[1] ? yr : null };
    } : null;
    const base = baseMaterials();
    const { rows: passing, counts } = AC.runStages(stages, base);
    current = passing;
    const pass = new Set(passing.map(m => m.id));
    const find = state.find;
    const live = m => pass.has(m.id) && (!find || m.search.includes(find));
    const rows = AC.chartRows(state.ghosts ? base : base.filter(live), xA, yA, { dim: m => !live(m), color: colorOf, ring: ringOf, size: sizeOf, range: rangeOf });
    plot.opts.pointAlpha = colorScale ? 1 : .9;
    plot.opts.blobFill = .16;
    plot.setData({ rows, xAxis: xA, yAxis: yA, keepView: keep });
    rowById = new Map(plot.rows.map(r => [r.m.id, r]));
    const shapes = AC.shapesFor(rows, xA, yA, { method: state.shape, grouping: state.group });
    plot.setShapes(shapes);
    if (selBox) syncBoxSelection();
    const outside = shapes.reduce((sum, s) => sum + (s.outside || 0), 0);
    $('outside-note').hidden = !outside;
    $('outside-note').textContent = `${outside.toLocaleString()} isolated ${outside === 1 ? 'material sits' : 'materials sit'} outside the ovals, so one far point does not stretch a whole family.`;
    // Parallel axes read the same filters and colours as the chart.
    pv.rows = base.filter(m => state.paxes.every(s => m.d[s] > 0));
    pv.live = live;
    pv.color = colorOf;
    pv.ranges = {};
    if (pv.rows.length) for (const s of state.paxes) {
      const values = pv.rows.map(m => Math.log10(m.d[s])), lo = Math.min(...values), hi = Math.max(...values);
      pv.ranges[s] = hi === lo ? [lo - .5, lo + .5] : [lo, hi];
    }
    if (state.view === 'parallel') { renderParallelBar(); drawParallel(); }
    if (!light) {
      if (state.view === 'parallel') {
        const counts = {};
        db.materials.forEach(m => { if (state.paxes.every(s => m.d[s] > 0)) counts[m.family] = (counts[m.family] || 0) + 1; });
        renderFamilies(counts);
      } else renderFamilies(availableFor(xA, yA));
      renderTags();
      if (state.stackOpen) renderStages();
    } else if (state.stackOpen) updateFunnels();
    renderLabels();
    renderResults();
    const legend = $('color-legend');
    legend.replaceChildren(...(colorScale ? [el('div', { class: 'gradient', style: `background:linear-gradient(90deg,${[0, .25, .5, .75, 1].map(ramp).join(',')})` }), el('div', { class: 'gradient-labels' }, el('span', {}, formatValue(10 ** colorScale.lo)), el('span', {}, db.bySym[state.color].unit), el('span', {}, formatValue(10 ** colorScale.hi)))] : []));
    const active = stages.filter(s => s.enabled !== false).length;
    $('stack-count').textContent = active ? String(active) : '';
    $('results-count').textContent = passing.length.toLocaleString();
    const scope = $('scope'), limited = state.isolate || state.hidden.size;
    const findMatches = find ? passing.filter(m => m.search.includes(find)).length : 0;
    const findMissing = find && (state.view === 'parallel' ? !pv.rows.some(live) : !rows.some(r => !r.dim));
    scope.hidden = !limited && !findMissing;
    scope.replaceChildren(
      findMissing ? (findMatches ? `${findMatches} found, but not on these axes` : 'Nothing found') : '',
      ...(limited ? [state.isolate ? ` Only ${state.isolate.size} materials` : ` ${state.hidden.size} hidden`, el('button', { onclick: () => { state.isolate = null; state.hidden.clear(); refresh(false); } }, 'Show all')] : []));
    writeHash();
    window.__lastRefreshMs = performance.now() - started;
    window.__rows = rows.length;
    window.__live = rows.filter(r => !r.dim).length;
  }
  tags.listen(() => { refresh(); renderPop(); });

  $('fit').onclick = () => plot.fit();
  $('search').oninput = e => { state.find = e.target.value.toLowerCase().trim(); refresh(); };
  $('search').addEventListener('keydown', e => {
    e.stopPropagation();
    if (e.key === 'Escape') { e.target.value = ''; state.find = ''; refresh(); e.target.blur(); }
    if (e.key === 'Enter' && state.find) {
      const hits = plot.rows.filter(r => !r.dim);
      if (hits.length === 1) openPop(hits[0].m);
      else { selBox = null; setSelection(hits.map(r => r.m.id), true); plot.draw(); }
    }
  });
  $('side-btn').onclick = () => { $('side').hidden = !$('side').hidden; $('side-btn').classList.toggle('on', !$('side').hidden); };
  if (isPhone()) $('side').hidden = true;
  $('side-btn').classList.toggle('on', !$('side').hidden);
  addEventListener('keydown', e => {
    if (e.target.matches('input, select, textarea')) { if (e.key === 'Escape') e.target.blur(); return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const key = e.key.toLowerCase(), chart = state.view === 'chart';
    if (key === '/') { e.preventDefault(); $('search').focus(); }
    else if (key === 'a') setView(chart ? 'parallel' : 'chart');
    else if (key === 'v' && chart) setMode('pan');
    else if (key === 'b' && chart) setMode('box');
    else if (key === 'l' && chart) setMode('lasso');
    else if (key === 'f' && chart) plot.fit();
    else if (key === 'x' && chart) setAxes({ x: state.y, y: state.x, xLog: state.yLog, yLog: state.xLog });
    else if (key === 's') setStack(!state.stackOpen);
    else if (key === 'r') setResults(!state.resultsOpen);
    else if (key === 'p') $('side-btn').click();
    else if (key === 'escape') {
      if (armRegion) { disarm(); setMode('pan'); return; }
      clearSelection(); closePop(); $('pop').hidden = true; detailM = null; renderDrawer();
    }
  });

  renderViews();
  renderBrief();
  const startView = state.view === 'parallel' ? 'parallel' : 'chart';
  state.view = 'chart';
  refresh(false);
  plot.view = { ...plot.fitView };
  rowById = new Map(plot.rows.map(r => [r.m.id, r]));
  document.body.classList.add('chart-on');
  if (startView === 'parallel') setView('parallel');
  setStack(state.stackOpen);
  setResults(state.resultsOpen);
  renderLabels();
  plot.draw();
  window.__plot = plot;
  window.__ready = true;
})();
