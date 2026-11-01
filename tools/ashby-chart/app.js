/* Ashby chart: the chart view, tags, label boxes, selection, axes and page state.
   Pairing and index formulas come from the Python build. This file only presents them. */
import { setupStack } from './stack.js?v=1';
import { setupParallel } from './parallel.js?v=1';
import { setupPanels } from './panels.js?v=1';

const { Database, Axis, runStages, compile, formatValue, clamp, FAMILY_COLORS, FAMILY_NAMES } = window.AshbyEngine;
const $ = id => document.getElementById(id);
// Read from the root element: WebKit can report stale values on body until the next paint.
const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const isPhone = () => matchMedia('(max-width: 820px)').matches;
const finePointer = () => matchMedia('(pointer: fine)').matches;
const el = (tag, props = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === 'class') node.className = value;
    else if (key === 'style') node.style.cssText = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (key in node && key !== 'list') node[key] = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) if (child != null) node.append(child);
  return node;
};
const options = (select, list) => select.replaceChildren(...list.map(([value, text]) => el('option', { value }, text)));

const VIEW_KEY = 'ashby-chart-views', LABEL_KEY = 'ashby-chart-labels', TAG_KEY = 'ashby-chart-tags', LABEL_CAP = 40;
const PALETTE = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#db2777', '#0891b2', '#65a30d', '#ea580c', '#475569'];
const STARTER_VIEWS = [
  { name: 'Stiffness', x: 'rho', y: 'E' }, { name: 'Tensile strength', x: 'rho', y: 'UTS' },
  { name: 'Bending stiffness', x: 'rho', y: 'Ef' }, { name: 'Yield strength', x: 'rho', y: 'Sy' },
  { name: 'Compressive strength', x: 'rho', y: 'Sc' }, { name: 'Stiffness vs compression', x: 'Sc', y: 'E' },
  { name: 'Thermal conductivity', x: 'rho', y: 'k' },
  { name: 'Specific stiffness vs specific strength', x: 'UTS/rho', y: 'E/rho' },
  { name: 'Beam stiffness index', x: 'rho', y: 'E^0.5/rho' },
];

let settings = { theme: 'system', density: 'comfortable', precision: 3 };
try { settings = { ...settings, ...JSON.parse(localStorage.getItem('materials-explorer-settings') || '{}') }; } catch { /* Session settings remain usable. */ }
if (!['light', 'dark', 'system'].includes(settings.theme)) settings.theme = 'system';
if (!['compact', 'comfortable'].includes(settings.density)) settings.density = 'comfortable';
if (![2, 3, 4].includes(Number(settings.precision))) settings.precision = 3;

/* Tags stay in this browser and belong to the material. */
const tags = {
  memory: (() => { try { return JSON.parse(localStorage.getItem(TAG_KEY)) || {}; } catch { return {}; } })(),
  listeners: new Set(),
  write(all) { this.memory = all; try { localStorage.setItem(TAG_KEY, JSON.stringify(all)); } catch { /* Private window: tags last until reload. */ } this.listeners.forEach(f => f()); },
  names() { return Object.keys(this.memory); },
  has(name, id) { return (this.memory[name]?.ids || []).includes(id); },
  of(id) { return Object.keys(this.memory).filter(n => this.memory[n].ids.includes(id)); },
  color(name) { return this.memory[name]?.color || '#475569'; },
  ids(name) { return this.memory[name]?.ids || []; },
  add(name, ids) {
    const all = { ...this.memory };
    const current = all[name] || { color: PALETTE[Object.keys(all).length % PALETTE.length], ids: [] };
    all[name] = { ...current, ids: [...new Set([...current.ids, ...ids])] };
    this.write(all);
  },
  remove(name, ids) { const all = { ...this.memory }; if (all[name]) { all[name] = { ...all[name], ids: all[name].ids.filter(i => !ids.includes(i)) }; this.write(all); } },
  drop(name) { const all = { ...this.memory }; delete all[name]; this.write(all); },
};

const params = new URLSearchParams(location.search);
const ctx = {
  $, el, options, cssVar, isPhone, tags, settings, LABEL_CAP,
  precise: value => Number(value).toPrecision(Number(settings.precision)),
  state: {
    x: 'rho', y: 'E', xLog: true, yLog: true, shape: 'ashby', group: 'family', color: 'family', size: 'none',
    ghosts: true, showPoints: true, ranges: true, isolines: true, pointLabels: false,
    temperature: 'ambient', basis: 'all', families: new Set(), hiddenTags: new Set(), isolate: null, hidden: new Set(),
    find: '', stackOpen: false, resultsOpen: false, brief: null, view: 'chart', paxes: ['rho', 'E', 'UTS'],
    index: '', topN: 5,
  },
  stages: [],
  selection: new Set(), selBox: null, armRegion: false,
  popM: null, popAt: null, selected: null, ranked: [],
  rowByKey: new Map(), passing: [], plotted: [], lines: [],
  pinned: new Map(),
  details: null,
};
const { state } = ctx;
let db, plot, grip = null;

/* ---------- values on the chart ---------- */
ctx.allow = () => (state.temperature === 'ambient' ? o => db.isAmbient(o) : null);
ctx.stageContext = () => ({ allow: ctx.allow(), hasTag: (name, id) => tags.has(name, id) });
ctx.baseRows = () => db.rows.filter(row => state.families.has(row.m.family) && !state.hidden.has(row.m.id) && (!state.isolate || state.isolate.has(row.m.id)));
ctx.passesBasis = point => state.basis === 'all' || (state.basis === 'measured' ? !point.hasBounds : point.hasBounds);
ctx.pointName = point => point.m.name + (point.stateIndex >= 0 ? ' · ' + db.stateName(point.stateIndex) : '');
ctx.axisText = (axis, row) => {
  if (axis.prop) {
    const o = axis.observation(row);
    return o >= 0 ? `${axis.tag} ${db.resultText(o)}` : `${axis.tag} –`;
  }
  return `${axis.tag} ${formatValue(axis.value(row, ctx.allow()))}`;
};

const ramp = t => { const stops = [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]]; const f = clamp(t, 0, 1) * 3.999, i = Math.floor(f), k = f - i; const c = stops[i].map((v, n) => Math.round(v + (stops[i + 1][n] - v) * k)); return `rgb(${c})`; };
const scales = new Map();
function scaleFor(sym) {
  if (!scales.has(sym)) {
    const p = db.bySym[sym].index, values = [];
    for (let o = 0; o < db.obsCount; o++) if (db.obsProp[o] === p && db.display[o] > 0) values.push(Math.log10(db.display[o]));
    const lo = Math.min(...values), hi = Math.max(...values);
    scales.set(sym, { lo, hi, p, f: v => (Math.log10(v) - lo) / (hi - lo || 1) });
  }
  return scales.get(sym);
}
function propValue(scale, row) { const o = row.obs[scale.p]; return o >= 0 ? db.display[o] : NaN; }
ctx.colorFor = row => {
  if (db.bySym[state.color]) { const s = scaleFor(state.color), v = propValue(s, row); return v > 0 ? ramp(s.f(v)) : '#9ca3af'; }
  if (state.color === 'tag') { const t = tags.of(row.m.id).find(n => !state.hiddenTags.has(n)); return t ? tags.color(t) : '#9ca3af'; }
  return FAMILY_COLORS[row.m.family];
};
ctx.visibleTag = m => tags.of(m.id).find(n => !state.hiddenTags.has(n));

/* ---------- the chart ---------- */
function makePlot() {
  plot = new window.AshbyPlot($('ashby-chart'), {
    padding: { l: 84, r: 14, t: 12, b: 52 }, blobFill: .16,
    tipFormat: row => [el('strong', {}, row.name), el('span', {}, `${FAMILY_NAMES[row.m.family]} · ${row.m.sub_family}`), el('span', {}, ctx.axisText(plot.yAxis, row.point.row)), el('span', {}, ctx.axisText(plot.xAxis, row.point.row))],
    onSelect: (hits, shape) => {
      const xA = plot.xAxis, yA = plot.yAxis;
      if (shape.kind === 'box' && ctx.armRegion) {
        disarm();
        ctx.stages.push({ type: 'region', x: state.x, y: state.y, xLog: state.xLog, yLog: state.yLog, x0: xA.inv(shape.x0), x1: xA.inv(shape.x1), y0: yA.inv(shape.y0), y1: yA.inv(shape.y1), enabled: true });
        setMode('pan');
        refresh();
        return;
      }
      ctx.selBox = shape.kind === 'box' ? { x0: shape.x0, x1: shape.x1, y0: shape.y0, y1: shape.y1 } : null;
      setSelection(hits.map(r => r.key), true);
      closePop();
    },
    onClick: hit => {
      if (hit) { openPop(hit.point); return; }
      closePop();
      clearSelection();
    },
    afterPoints: drawOverlays,
    onPointerDown: pressChart,
    onPointerDrag: dragChart,
    onPointerUp: releaseChart,
    onDraw: positionFloating,
  });
  ctx.plot = plot;
  $('ashby-chart').addEventListener('pointermove', e => {
    if (plot.drag || plot.hover) return;
    const [x, y] = plot.point(e), corner = boxCorner(x, y);
    if (corner) plot.canvas.style.cursor = (corner.xKey === 'left') === (corner.yKey === 'top') ? 'nwse-resize' : 'nesw-resize';
    else if (nearLine(x, y, plot)) plot.canvas.style.cursor = 'ns-resize';
    else if (inBox(x, y)) plot.canvas.style.cursor = 'move';
    else plot.canvas.style.cursor = plot.mode === 'pan' ? 'grab' : 'crosshair';
  });
}
function lineStages() {
  if (!state.xLog || !state.yLog) return [];
  return ctx.stages.filter(s => s.type === 'index' && s.enabled !== false && s.x === state.x && s.y === state.y);
}
function boxScreen(p = plot) {
  if (!ctx.selBox) return null;
  const b = ctx.selBox, x0 = p.sx(b.x0), x1 = p.sx(b.x1), y0 = p.sy(b.y1), y1 = p.sy(b.y0);
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
const nearLine = (x, y, p) => lineStages().find(s => Math.abs(p.sy(s.slope * p.ix(x) + s.c) - y) < 9);
function pressChart(x, y, _e, p) {
  const corner = boxCorner(x, y);
  if (corner) { grip = { kind: 'corner', ...corner }; return true; }
  const line = nearLine(x, y, p);
  if (line) { grip = { kind: 'line', stage: line }; return true; }
  if (inBox(x, y)) { grip = { kind: 'box', x, y, start: { ...ctx.selBox }, moved: false }; return true; }
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
    ctx.selBox = { x0: s.x0 + dx, x1: s.x1 + dx, y0: s.y0 + dy, y1: s.y1 + dy };
    syncBoxSelection();
  } else if (grip.kind === 'corner') {
    if (grip.xKey === 'left') ctx.selBox.x0 = p.ix(x); else ctx.selBox.x1 = p.ix(x);
    if (grip.yKey === 'bottom') ctx.selBox.y0 = p.iy(y); else ctx.selBox.y1 = p.iy(y);
    syncBoxSelection();
  }
}
function releaseChart(x, y, _e, p) {
  if (grip?.kind === 'box' && !grip.moved) {
    const hit = p.nearest(x, y);
    if (hit) openPop(hit.point);
  }
  if (grip?.kind === 'corner') {
    const b = ctx.selBox;
    ctx.selBox = { x0: Math.min(b.x0, b.x1), x1: Math.max(b.x0, b.x1), y0: Math.min(b.y0, b.y1), y1: Math.max(b.y0, b.y1) };
  }
  if (grip?.kind === 'line') refresh(true);
  grip = null;
}
function syncBoxSelection() {
  const b = ctx.selBox, lo = Math.min(b.x0, b.x1), hi = Math.max(b.x0, b.x1), bottom = Math.min(b.y0, b.y1), top = Math.max(b.y0, b.y1);
  setSelection(plot.rows.filter(r => !r.dim && r.tx >= lo && r.tx <= hi && r.ty >= bottom && r.ty <= top).map(r => r.key));
  plot.draw();
}
function drawOverlays(c, p) {
  const ink = cssVar('--text-color'), muted = cssVar('--text-light'), card = cssVar('--bg-card');
  // Lines of equal index value through ranked materials.
  if (state.isolines) {
    const v = p.view;
    c.lineWidth = 1.1; c.setLineDash([3, 4]);
    for (const line of ctx.lines) {
      c.strokeStyle = muted;
      c.beginPath(); c.moveTo(p.sx(v.x0), p.sy(line.slope * v.x0 + line.c)); c.lineTo(p.sx(v.x1), p.sy(line.slope * v.x1 + line.c)); c.stroke();
      const from = Math.max(v.x0, (v.y0 - line.c) / line.slope), to = Math.min(v.x1, (v.y1 - line.c) / line.slope);
      if (to > from) {
        const tx = from + (to - from) * .85;
        c.save(); c.setLineDash([]); c.font = '11px ' + cssVar('--font-sans'); c.textAlign = 'right'; c.lineWidth = 3; c.strokeStyle = card; c.fillStyle = muted; c.lineJoin = 'round';
        c.translate(p.sx(tx), p.sy(line.slope * tx + line.c));
        c.rotate(-Math.atan2(line.slope * (p.plotBox.h / (v.y1 - v.y0)), p.plotBox.w / (v.x1 - v.x0)));
        c.strokeText(line.label, 0, -5); c.fillText(line.label, 0, -5); c.restore();
      }
    }
    c.setLineDash([]); c.lineWidth = 1;
  }
  // Leader lines run from each labelled point to its box.
  c.strokeStyle = muted; c.lineWidth = 1;
  for (const id of labels.keys()) {
    const row = labelRow(id), rect = labelRect(id, p);
    if (!row || !rect) continue;
    const X = p.sx(row.tx), Y = p.sy(row.ty);
    c.beginPath(); c.moveTo(X, Y);
    c.lineTo(clamp(X, rect.x, rect.x + rect.w), clamp(Y, rect.y, rect.y + rect.h)); c.stroke();
    c.fillStyle = card; c.beginPath(); c.arc(X, Y, p.opts.pointSize + 1.5, 0, 7); c.fill();
    c.fillStyle = row.color; c.beginPath(); c.arc(X, Y, p.opts.pointSize, 0, 7); c.fill();
    c.strokeStyle = ink; c.lineWidth = 1.4; c.beginPath(); c.arc(X, Y, p.opts.pointSize + 1.5, 0, 7); c.stroke();
    c.strokeStyle = muted; c.lineWidth = 1;
  }
  // Selection lines, with the side that passes shaded.
  for (const s of lineStages()) {
    const v = p.view, f = t => s.slope * t + s.c;
    c.fillStyle = ink; c.globalAlpha = .045; c.beginPath();
    const edge = s.above ? v.y1 + 40 : v.y0 - 40;
    c.moveTo(p.sx(v.x0), p.sy(f(v.x0))); c.lineTo(p.sx(v.x1), p.sy(f(v.x1))); c.lineTo(p.sx(v.x1), p.sy(edge)); c.lineTo(p.sx(v.x0), p.sy(edge)); c.closePath(); c.fill(); c.globalAlpha = 1;
    c.strokeStyle = ink; c.lineWidth = 1.8; c.setLineDash([8, 5]);
    c.beginPath(); c.moveTo(p.sx(v.x0), p.sy(f(v.x0))); c.lineTo(p.sx(v.x1), p.sy(f(v.x1))); c.stroke(); c.setLineDash([]); c.lineWidth = 1;
    // Put the hint on the part of the line that is actually in view.
    const from = Math.max(v.x0, (v.y0 - s.c) / s.slope), to = Math.min(v.x1, (v.y1 - s.c) / s.slope);
    if (to > from && !p.exporting) {
      const tx = from + (to - from) * .3;
      c.save(); c.translate(p.sx(tx), p.sy(f(tx)));
      c.rotate(-Math.atan2(s.slope * (p.plotBox.h / (v.y1 - v.y0)), p.plotBox.w / (v.x1 - v.x0)));
      c.font = '600 11.5px ' + cssVar('--font-sans'); c.fillStyle = ink;
      c.lineWidth = 3; c.strokeStyle = card; c.lineJoin = 'round';
      const hint = s.brief ? 'Drag: better is up and left' : 'Drag to move';
      c.strokeText(hint, 6, -7); c.fillText(hint, 6, -7); c.lineWidth = 1; c.restore();
    }
  }
  // The selection box stays on the chart so it can be moved and resized.
  const b = boxScreen(p);
  if (b && !p.exporting) {
    c.fillStyle = ink; c.globalAlpha = .06; c.fillRect(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0); c.globalAlpha = 1;
    c.strokeStyle = ink; c.lineWidth = 1.3; c.setLineDash([5, 4]); c.strokeRect(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0); c.setLineDash([]);
    c.fillStyle = card;
    for (const [X, Y] of [[b.x0, b.y0], [b.x1, b.y0], [b.x0, b.y1], [b.x1, b.y1]]) { c.fillRect(X - 4, Y - 4, 8, 8); c.strokeRect(X - 4, Y - 4, 8, 8); }
    c.lineWidth = 1;
  }
}

/* ---------- label boxes: an offset from the material, so they follow pan and zoom ---------- */
const labels = new Map();
const labelNodes = new Map();
const labelId = (materialId, stateId) => materialId + '|' + (stateId || '');
function readLabels() {
  const add = (material, stateId, dx, dy) => { if (db.byId[material]) labels.set(labelId(material, stateId), { material, stateId: stateId || null, dx, dy, key: null }); };
  if (params.has('labels')) {
    for (const item of params.get('labels').split(',').filter(Boolean)) {
      const [material, stateId, dx, dy] = item.split('~');
      add(material, stateId, Number(dx) || 24, Number(dy) || -48);
    }
    return;
  }
  try { for (const [material, stateId, dx, dy] of JSON.parse(localStorage.getItem(LABEL_KEY)) || []) add(material, stateId, dx, dy); } catch { /* No saved labels. */ }
}
function saveLabels() {
  try { localStorage.setItem(LABEL_KEY, JSON.stringify([...labels.values()].map(l => [l.material, l.stateId, Math.round(l.dx), Math.round(l.dy)]))); } catch { /* Private window: labels last until reload. */ }
  syncUrl();
}
/* A label uses the point it was made on until the axes change, then the first available. */
function labelRow(id) {
  const label = labels.get(id);
  if (!label) return null;
  if (label.key && ctx.rowByKey.has(label.key)) return ctx.rowByKey.get(label.key);
  let same = null;
  for (const row of plot.rows) {
    if (row.m.id !== label.material) continue;
    const rowState = row.point.stateIndex >= 0 ? db.states[row.point.stateIndex].id : null;
    if (rowState === label.stateId) return row;
    same ||= row;
  }
  return same;
}
function placeLabel(row) {
  const b = plot.plotBox, w = 180, h = 38;
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
  const row = labelRow(id), label = labels.get(id);
  if (!row || !label) return null;
  const b = p.plotBox, X = p.sx(row.tx), Y = p.sy(row.ty);
  if (X < b.l || X > b.r || Y < b.t || Y > b.b) return null;
  const node = labelNodes.get(id), w = node?.offsetWidth || 180, h = node?.offsetHeight || 38;
  return { x: clamp(X + label.dx, b.l + 2, Math.max(b.l + 2, b.r - w - 2)), y: clamp(Y + label.dy, b.t + 2, Math.max(b.t + 2, b.b - h - 2)), w, h };
}
function renderLabels() {
  const layer = $('labels');
  for (const [id, node] of labelNodes) if (!labels.has(id)) { node.remove(); labelNodes.delete(id); }
  let missing = 0;
  for (const id of labels.keys()) {
    const label = labels.get(id), m = db.byId[label.material], row = labelRow(id);
    if (!row) missing++;
    let node = labelNodes.get(id);
    if (!node) { node = makeLabelNode(id, m, label); labelNodes.set(id, node); layer.append(node); }
    const tag = ctx.visibleTag(m);
    node.style.setProperty('--c', tag ? tags.color(tag) : FAMILY_COLORS[m.family]);
    node.classList.toggle('faded', !!row?.dim);
    node.querySelector('strong').textContent = row ? row.name : m.name;
    node.querySelector('span').textContent = row ? `${ctx.axisText(plot.yAxis, row.point.row)} · ${ctx.axisText(plot.xAxis, row.point.row)}` : '';
  }
  $('label-actions').hidden = labels.size === 0;
  $('label-count').textContent = `${labels.size} label ${labels.size === 1 ? 'box' : 'boxes'}` + (missing ? `, ${missing} with no values on these axes` : '');
  positionFloating();
}
function makeLabelNode(id, m, label) {
  const node = el('div', { class: 'label-box', title: 'Drag to move. Click for tags and details.', 'data-material': m.id },
    el('strong', {}, m.name), el('span', {}),
    el('button', { type: 'button', 'aria-label': `Remove the label on ${m.name}`, title: 'Remove this label', onpointerdown: e => e.stopPropagation(), onclick: e => { e.stopPropagation(); removeLabel(id); } }, '×'));
  let press = null;
  // Stops Safari from starting a text selection when a drag begins on the box.
  node.addEventListener('mousedown', e => e.preventDefault());
  node.addEventListener('pointerdown', e => {
    node.setPointerCapture(e.pointerId);
    press = { x: e.clientX, y: e.clientY, at: [label.dx, label.dy], moved: false };
    node.classList.add('drag');
  });
  node.addEventListener('pointermove', e => {
    if (!press) return;
    const dx = e.clientX - press.x, dy = e.clientY - press.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) press.moved = true;
    label.dx = press.at[0] + dx; label.dy = press.at[1] + dy;
    plot.draw();
  });
  const finish = () => {
    if (!press) return;
    const moved = press.moved;
    press = null;
    node.classList.remove('drag');
    if (moved) {
      // Save where the box actually landed, so it cannot drift off the plot.
      const row = labelRow(id), rect = labelRect(id);
      if (row && rect) { label.dx = rect.x - plot.sx(row.tx); label.dy = rect.y - plot.sy(row.ty); }
      saveLabels();
    } else {
      const row = labelRow(id);
      if (row) openPop(row.point);
    }
  };
  node.addEventListener('pointerup', finish);
  node.addEventListener('pointercancel', finish);
  return node;
}
function addLabels(rows) {
  for (const row of rows) {
    const stateId = row.point.stateIndex >= 0 ? db.states[row.point.stateIndex].id : null, id = labelId(row.m.id, stateId);
    if (labels.has(id)) continue;
    const [dx, dy] = placeLabel(row);
    labels.set(id, { material: row.m.id, stateId, dx, dy, key: row.key });
  }
  saveLabels(); renderLabels(); plot.draw();
}
function removeLabel(id) { labels.delete(id); saveLabels(); renderLabels(); renderPop(false); plot.draw(); }
function pointLabelId(point) { return labelId(point.m.id, point.stateIndex >= 0 ? db.states[point.stateIndex].id : null); }

function positionFloating() {
  for (const [id, node] of labelNodes) {
    const rect = labelRect(id);
    node.hidden = !rect;
    if (rect) node.style.transform = `translate(${Math.round(rect.x)}px, ${Math.round(rect.y)}px)`;
  }
  const mat = $('mat');
  if (ctx.popM && !mat.hidden && !isPhone()) {
    const row = ctx.rowByKey.get(ctx.popM.key), wrap = $('wrap');
    const w = mat.offsetWidth, h = mat.offsetHeight, W = wrap.clientWidth, H = wrap.clientHeight;
    const onParallel = state.view === 'parallel' && ctx.popAt;
    const X = onParallel ? ctx.popAt[0] : row ? plot.sx(row.tx) : W / 2, Y = onParallel ? ctx.popAt[1] : row ? plot.sy(row.ty) : H / 2;
    const left = X + 16 + w > W - 6 ? X - w - 16 : X + 16;
    mat.style.transform = `translate(${Math.round(clamp(left, 6, Math.max(6, W - w - 6)))}px, ${Math.round(clamp(Y - 24, 6, Math.max(6, H - h - 6)))}px)`;
  }
}

/* ---------- one material: tag it, label it, compare it, read its sources ---------- */
function syncHighlight() {
  const on = new Set(ctx.selection);
  if (ctx.popM) on.add(ctx.popM.key);
  if (ctx.selected) on.add(ctx.selected.key);
  if (ctx.pane === 'rank') for (const point of ctx.ranked) on.add(point.key);
  plot.selected = on;
  plot.draw();
}
ctx.syncHighlight = syncHighlight;
ctx.openPointCard = (point, at = null) => openPop(point, at);
ctx.closePointCard = () => closePop();
function openPop(point, at = null) { ctx.popM = point; ctx.popAt = at; renderPop(); syncHighlight(); ctx.drawParallel(); }
// Safari keeps focus on a hidden field, which would swallow the keyboard shortcuts, so let go of it first.
const releaseFocus = box => { if (box.contains(document.activeElement)) document.activeElement.blur(); };
function closePop() { releaseFocus($('mat')); ctx.popM = null; ctx.popAt = null; $('mat').hidden = true; syncHighlight(); ctx.drawParallel(); }
function renderPop(focus = true) {
  const box = $('mat');
  if (!ctx.popM) { box.hidden = true; return; }
  const point = ctx.popM, m = point.m, plotRow = ctx.rowByKey.get(point.key) || plot.rows.find(r => r.m.id === m.id), applied = tags.of(m.id), others = tags.names().filter(n => !applied.includes(n));
  const input = el('input', { type: 'text', placeholder: 'New tag, then Enter', 'aria-label': `Tag ${m.name}`, list: 'tag-list', spellcheck: false });
  input.addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Escape') closePop(); });
  const id = pointLabelId(point), labelled = labels.has(id), pinKey = point.key, pinned = ctx.pinned.has(pinKey);
  const vals = state.view === 'parallel'
    ? point.obs.map(o => `${db.propertyOf(o).symbol.replace('rho', 'ρ')} ${db.resultText(o)}`).join(' · ')
    : `${ctx.axisText(plot.yAxis, point.row)} · ${ctx.axisText(plot.xAxis, point.row)}`;
  box.hidden = false;
  box.replaceChildren(...[
    el('header', {}, el('h3', {}, ctx.pointName(point)), el('button', { type: 'button', class: 'ghost', 'aria-label': 'Close', onclick: closePop }, '×')),
    el('p', { class: 'sub' }, `${FAMILY_NAMES[m.family]} · ${m.sub_family}`),
    el('p', { class: 'vals' }, vals),
    applied.length || others.length ? el('div', { class: 'chips' },
      applied.map(t => el('button', { type: 'button', class: 'chip', style: `--c:${tags.color(t)}`, title: `Remove the tag ${t}`, onclick: () => tags.remove(t, [m.id]) }, t, ' ×')),
      others.map(t => el('button', { type: 'button', class: 'chip ghosted', style: `--c:${tags.color(t)}`, title: `Add the tag ${t}`, onclick: () => tags.add(t, [m.id]) }, '+ ', t))) : null,
    el('form', { onsubmit: e => { e.preventDefault(); const name = input.value.trim(); if (name) tags.add(name, [m.id]); } }, input, el('button', { type: 'submit' }, 'Tag')),
    el('div', { class: 'acts' },
      // Adding a label closes this card, because the card would otherwise sit on top of the new box.
      el('button', { type: 'button', class: labelled ? 'on' : '', disabled: !plotRow && !labelled, onclick: () => { if (labelled) { removeLabel(id); renderPop(false); } else { addLabels([plotRow]); closePop(); } } }, labelled ? 'Remove label' : 'Label on chart'),
      el('button', { type: 'button', class: pinned ? 'on' : '', onclick: () => { ctx.togglePin(point); renderPop(false); } }, pinned ? 'Comparing' : 'Compare'),
      el('button', { type: 'button', onclick: () => { closePop(); ctx.showCard(point); } }, 'Sources')),
  ].filter(Boolean));
  positionFloating();
  if (focus && finePointer()) input.focus({ preventScroll: true });
}

/* ---------- several materials: the selection and its action bar ---------- */
function setSelection(keys, focus = false) {
  ctx.selection = new Set(keys);
  syncHighlight();
  const empty = ctx.selection.size === 0 && !ctx.selBox;
  if (empty) releaseFocus($('actions'));
  $('actions').hidden = empty;
  $('sel-count').textContent = `${ctx.selection.size} selected`;
  $('sel-filter').hidden = !ctx.selBox;
  $('sel-zoom').hidden = state.view === 'parallel';
  const label = $('sel-label');
  label.disabled = ctx.selection.size > LABEL_CAP;
  label.title = ctx.selection.size > LABEL_CAP ? `Label up to ${LABEL_CAP} at a time` : 'Put a label box on each of these';
  if (focus && ctx.selection.size && finePointer()) setTimeout(() => $('tag-name').focus({ preventScroll: true }));
}
function clearSelection() { ctx.selBox = null; setSelection([]); plot.draw(); ctx.drawParallel(); }
const selectedRows = () => plot.rows.filter(r => ctx.selection.has(r.key));
const selectedMaterials = () => [...new Set(selectedRows().map(r => r.m.id))];
function applyTag() {
  const name = $('tag-name').value.trim();
  if (!name || !ctx.selection.size) return;
  $('tag-name').value = '';
  const ids = selectedMaterials();
  ctx.selBox = null; setSelection([]);
  tags.add(name, ids);
}
function setMode(mode) {
  plot.mode = mode;
  document.querySelectorAll('[data-mode]').forEach(b => { b.classList.toggle('on', b.dataset.mode === mode); b.setAttribute('aria-pressed', String(b.dataset.mode === mode)); });
  plot.canvas.style.cursor = mode === 'pan' ? 'grab' : 'crosshair';
  if (ctx.armRegion && mode !== 'box') disarm();
}
function disarm() { ctx.armRegion = false; $('arm-note').hidden = true; }
ctx.setMode = setMode;
ctx.armRegion = false;
ctx.startRegion = () => { setView('chart'); clearSelection(); ctx.armRegion = true; setMode('box'); $('arm-note').hidden = false; if (isPhone()) ctx.setStack(false); };

/* ---------- axes ---------- */
function setAxes(changes) {
  Object.assign(state, changes);
  closePop(); ctx.selBox = null; setSelection([]);
  ctx.populateIndices?.();
  refresh(false);
  plot.fit();
}
ctx.setAxes = setAxes;
function coverage(expr, other) {
  const a = new Axis(db, expr), b = new Axis(db, other), allow = ctx.allow(), seen = new Set();
  for (const row of db.rows) if (Number.isFinite(a.value(row, allow)) && Number.isFinite(b.value(row, allow))) seen.add(row.m.i);
  return seen.size;
}
function openAxis(which) {
  const pop = $('pop');
  if (!pop.hidden && pop.dataset.which === which) { pop.hidden = true; return; }
  pop.dataset.which = which; pop.hidden = false;
  const other = which === 'x' ? state.y : state.x, current = which === 'x' ? state.x : state.y, logKey = which + 'Log';
  const counts = db.props.map(p => [p, coverage(p.symbol, other)]).sort((a, b) => b[1] - a[1]);
  const peak = Math.max(1, ...counts.map(c => c[1]));
  const input = el('input', { type: 'text', value: db.bySym[current] ? '' : current, placeholder: 'E^0.5/rho', 'aria-label': 'Formula', spellcheck: false });
  const msg = el('div', { class: 'formula-msg' }, 'Symbols: ' + db.props.map(p => p.symbol).join(', ') + '. Uses the units on the axes.');
  const apply = () => {
    const c = compile(db, input.value);
    if (c.error) { msg.textContent = c.error; msg.classList.add('bad'); return; }
    pop.hidden = true; setAxes({ [which]: input.value.trim() });
  };
  input.oninput = () => {
    if (!input.value.trim()) { msg.textContent = ''; msg.classList.remove('bad'); return; }
    const c = compile(db, input.value);
    msg.classList.toggle('bad', !!c.error);
    msg.textContent = c.error || `${coverage(input.value, other).toLocaleString()} materials would plot`;
  };
  input.onkeydown = e => { e.stopPropagation(); if (e.key === 'Enter') apply(); if (e.key === 'Escape') pop.hidden = true; };
  pop.replaceChildren(
    el('h2', {}, which === 'x' ? 'Horizontal axis' : 'Vertical axis'),
    el('div', { class: 'scale' }, 'Scale ', ...[['Log', true], ['Linear', false]].map(([label, value]) => el('button', { type: 'button', class: state[logKey] === value ? 'on' : '', onclick: () => { pop.hidden = true; setAxes({ [logKey]: value }); } }, label))),
    ...counts.map(([p, n]) => el('button', { type: 'button', class: 'prop-row' + (p.symbol === current ? ' on' : ''), title: p.definition, 'data-prop': p.id, onclick: () => { pop.hidden = true; setAxes({ [which]: p.symbol }); } },
      el('span', {}, p.display_unit ? `${p.label} (${p.display_unit})` : p.label, el('span', { class: 'cov' }, el('i', { style: `width:${n / peak * 100}%` }))), el('span', { class: 'n' }, n.toLocaleString()))),
    el('h2', { style: 'margin-top:10px' }, 'Or write a formula'),
    el('div', { class: 'formula' }, input, el('button', { type: 'button', class: 'primary', onclick: apply }, 'Plot')), msg,
    el('div', { class: 'quick' }, ...['E/rho', 'E^0.5/rho', 'E^(1/3)/rho', 'UTS/rho', 'UTS^(2/3)/rho', 'Sy/E', 'k/rho', 'rho*cp', 'k/(rho*cp)'].map(f => el('button', { type: 'button', onclick: () => { input.value = f; input.oninput(); } }, f))));
  const button = $(which + '-btn').getBoundingClientRect(), host = pop.parentElement.getBoundingClientRect();
  const w = pop.offsetWidth, h = pop.offsetHeight;
  pop.style.left = clamp(which === 'x' ? button.left - host.left + button.width / 2 - w / 2 : 40, 8, Math.max(8, host.width - w - 8)) + 'px';
  pop.style.top = clamp(which === 'x' ? button.top - host.top - h - 8 : (host.height - h) / 2, 8, Math.max(8, host.height - h - 8)) + 'px';
  pop.querySelector('.prop-row.on, .prop-row')?.focus({ preventScroll: true });
  if (!db.bySym[current]) input.focus();
}

/* ---------- side panel: Show ---------- */
/* Panels redraw when filters change. Keyboard users keep their place in the panel. */
function keepFocus(host, render) {
  const controls = () => [...host.querySelectorAll('button, select, input, summary, a')];
  const at = host.contains(document.activeElement) ? controls().indexOf(document.activeElement) : -1;
  render();
  if (at >= 0) { const list = controls(); list[Math.min(at, list.length - 1)]?.focus({ preventScroll: true }); }
}
ctx.keepFocus = keepFocus;
function renderFamilies(available, all) {
  $('family-toggles').replaceChildren(...Object.entries(FAMILY_NAMES).map(([key, name]) => el('button', {
    type: 'button', class: 'chip family-pill' + (state.families.has(key) ? '' : ' off'), style: `--c:${FAMILY_COLORS[key]}`, 'data-family': key,
    'aria-pressed': String(state.families.has(key)),
    title: `${available[key] || 0} of ${all[key] || 0} grades plot on these axes. Click to toggle, double-click for only this family.`,
    onclick: () => { state.families.has(key) ? state.families.delete(key) : state.families.add(key); refresh(); },
    ondblclick: () => { state.families = new Set([key]); refresh(); },
  }, name, ' ', el('b', { class: 'family-count' }, available[key] || 0))));
  const note = $('coverage-note');
  note.replaceChildren();
  for (const [family] of Object.entries(FAMILY_NAMES)) {
    if (!state.families.has(family) || available[family] || !all[family]) continue;
    const material = db.materials.find(m => m.family === family), view = ctx.compatibleView(material);
    if (view) note.append(el('button', { type: 'button', onclick: () => { state.families = new Set([family]); $('material-search').value = ''; state.find = ''; applyView(view); } }, `${FAMILY_NAMES[family]}: view ${view.name.toLowerCase()} →`));
  }
}
function renderTags() {
  const names = tags.names();
  $('tag-empty').hidden = names.length > 0;
  $('tag-list').replaceChildren(...names.map(n => el('option', { value: n })));
  $('tag-rows').replaceChildren(...names.map(name => {
    const ids = tags.ids(name);
    const rows = () => ids.map(id => plot.rows.find(r => r.m.id === id)).filter(Boolean);
    return el('div', { class: 'tag-row' },
      el('button', { type: 'button', class: 'chip' + (state.hiddenTags.has(name) ? ' off' : ''), style: `--c:${tags.color(name)}`, title: 'Show or hide the ring on these materials', onclick: () => { state.hiddenTags.has(name) ? state.hiddenTags.delete(name) : state.hiddenTags.add(name); refresh(); } }, name, ' ', el('b', {}, ids.length)),
      el('button', { type: 'button', class: 'ghost', title: 'Show only this tag', onclick: () => { state.isolate = new Set(ids); refresh(false); } }, 'Only'),
      el('button', { type: 'button', class: 'ghost', title: 'Add this tag to the selection stack', onclick: () => { ctx.stages.push({ type: 'tag', value: name, enabled: true }); ctx.setStack(true); refresh(); } }, 'Stack'),
      el('button', { type: 'button', class: 'ghost', disabled: ids.length > LABEL_CAP, title: ids.length > LABEL_CAP ? `Label up to ${LABEL_CAP} at a time` : 'Label these on the chart', onclick: () => addLabels(rows()) }, 'Label'),
      el('button', { type: 'button', class: 'ghost', title: 'Delete tag', 'aria-label': `Delete ${name}`, onclick: () => { ctx.stages = ctx.stages.filter(s => !(s.type === 'tag' && s.value === name)); tags.drop(name); } }, '×'));
  }));
}
function readViews() { try { return JSON.parse(localStorage.getItem(VIEW_KEY)) || []; } catch { return []; } }
function renderViews() {
  $('views').replaceChildren(...[...STARTER_VIEWS, ...readViews()].map(v => el('button', {
    type: 'button', title: `${new Axis(db, v.y).short} against ${new Axis(db, v.x).short}`, class: v.x === state.x && v.y === state.y ? 'on' : '', 'data-x': v.x, 'data-y': v.y,
    onclick: () => applyView(v),
  }, v.name)));
}
function applyView(v) {
  setView('chart');
  if (Array.isArray(v.stages)) { ctx.stages = JSON.parse(JSON.stringify(v.stages)); state.brief = v.brief || null; }
  setAxes({ x: v.x, y: v.y, xLog: v.xLog ?? true, yLog: v.yLog ?? true });
}
ctx.applyView = applyView;
/* A chart that can show this material, for the suggestion when the current axes cannot. */
ctx.compatibleView = material => {
  const rows = db.rowsByMaterial.get(material.id) || [];
  return STARTER_VIEWS.slice(0, 7).find(v => {
    const a = new Axis(db, v.x), b = new Axis(db, v.y);
    return rows.some(row => Number.isFinite(a.value(row)) && Number.isFinite(b.value(row)));
  }) || null;
};

/* ---------- view switch ---------- */
function setView(name) {
  if (state.view === name && document.body.classList.contains(name === 'parallel' ? 'parallel-on' : 'chart-on')) return;
  state.view = name;
  const on = name === 'parallel';
  document.body.classList.toggle('parallel-on', on);
  document.body.classList.toggle('chart-on', !on);
  $('parallel').hidden = !on;
  $('view-chart').classList.toggle('on', !on); $('view-chart').setAttribute('aria-pressed', String(!on));
  $('view-parallel').classList.toggle('on', on); $('view-parallel').setAttribute('aria-pressed', String(on));
  closePop(); ctx.selBox = null; setSelection([]); disarm();
  ctx.resetParallelHover?.();
  refresh();
}
ctx.setView = setView;

/* ---------- page state in the address ---------- */
const exprToParam = expr => (db.bySym[expr] ? db.bySym[expr].id : expr);
function exprFromParam(value) {
  if (!value) return null;
  const prop = db.props.find(p => p.id === value);
  if (prop) return prop.symbol;
  return compile(db, value).error ? null : value;
}
/* A shared link is outside input, so keep only stages this page can read. */
function cleanStages(list) {
  if (!Array.isArray(list)) return [];
  const number = v => typeof v === 'number' && Number.isFinite(v);
  const optional = v => v == null || number(v);
  const axis = v => typeof v === 'string' && !compile(db, v).error;
  const strings = v => Array.isArray(v) && v.every(item => typeof item === 'string');
  return list.filter(s => {
    if (!s || typeof s !== 'object') return false;
    switch (s.type) {
      case 'family': case 'class': case 'org': return strings(s.values);
      case 'text': case 'tag': return typeof s.value === 'string';
      case 'limit': return axis(s.expr) && optional(s.min) && optional(s.max);
      case 'region': return axis(s.x) && axis(s.y) && [s.x0, s.x1, s.y0, s.y1].every(number);
      case 'index': return axis(s.x) && axis(s.y) && number(s.slope) && s.slope > 0 && number(s.c);
      default: return false;
    }
  });
}
function readParams() {
  state.x = exprFromParam(params.get('x-prop')) || state.x;
  state.y = exprFromParam(params.get('y-prop')) || state.y;
  state.xLog = params.get('x-scale') !== 'linear';
  state.yLog = params.get('y-scale') !== 'linear';
  // Old links name the earlier shapes: rounded outlines become pebbles, ellipses become ovals.
  const shape = params.get('envelope-mode');
  state.shape = { hulls: 'pebble', ellipses: 'ashby', ashby: 'ashby', pebble: 'pebble', none: 'none', points: 'none' }[shape] || 'ashby';
  const grouping = params.get('grouping');
  if (grouping === 'points' || params.get('setting-blobs') === '0') state.shape = 'none';
  if (['family', 'subgroup', 'tag'].includes(grouping)) state.group = grouping;
  const families = Object.keys(FAMILY_NAMES);
  state.families = new Set(params.has('families') ? params.get('families').split(',').filter(f => families.includes(f)) : families);
  if (params.get('temperature-filter') === 'all') state.temperature = 'all';
  if (['measured', 'limits'].includes(params.get('basis-filter'))) state.basis = params.get('basis-filter');
  state.find = (params.get('material-search') || '').toLowerCase().trim();
  $('material-search').value = params.get('material-search') || '';
  const flag = (key, fallback) => (params.has(key) ? params.get(key) === '1' : fallback);
  // A points-only link always keeps its points visible.
  state.showPoints = state.shape === 'none' ? true : flag('setting-points', true);
  state.ranges = flag('setting-ranges', true);
  state.isolines = flag('setting-isolines', true);
  state.pointLabels = flag('setting-labels', false);
  state.ghosts = flag('ghosts', true);
  if (db.bySym[params.get('color')] || ['family', 'tag'].includes(params.get('color'))) state.color = params.get('color');
  if (db.bySym[params.get('size')]) state.size = params.get('size');
  state.index = params.get('perf-index') || '';
  state.topN = clamp(Math.round(Number(params.get('top-n')) || 5), 1, 20);
  state.stackOpen = params.get('stack') === '1';
  state.resultsOpen = params.get('results') === '1';
  if (params.has('stages')) { try { ctx.stages = cleanStages(JSON.parse(params.get('stages'))); } catch { /* Ignore a damaged link. */ } }
  if (params.has('brief')) { const [part, driver] = params.get('brief').split('~'); state.brief = { part, driver }; }
  if (params.has('axes')) { const known = params.get('axes').split(',').map(id => db.props.find(p => p.id === id)?.symbol).filter(Boolean); if (known.length >= 2) state.paxes = known; }
  if (params.get('view') === 'parallel') state.view = 'parallel';
}
function shareUrl() {
  const url = new URL(location.href);
  url.search = '';
  const set = (k, v) => url.searchParams.set(k, v);
  set('x-prop', exprToParam(state.x)); set('y-prop', exprToParam(state.y));
  if (!state.xLog) set('x-scale', 'linear');
  if (!state.yLog) set('y-scale', 'linear');
  // An explicit empty index must survive restoration of the default chart.
  set('perf-index', state.index); set('top-n', state.topN);
  set('temperature-filter', state.temperature); set('basis-filter', state.basis);
  if ($('material-search').value) set('material-search', $('material-search').value);
  set('setting-points', state.showPoints ? '1' : '0'); set('setting-ranges', state.ranges ? '1' : '0');
  set('setting-isolines', state.isolines ? '1' : '0'); set('setting-labels', state.pointLabels ? '1' : '0');
  if (!state.ghosts) set('ghosts', '0');
  set('families', [...state.families].sort().join(','));
  set('envelope-mode', state.shape);
  set('grouping', state.shape === 'none' ? 'points' : state.group);
  if (state.color !== 'family') set('color', state.color);
  if (state.size !== 'none') set('size', state.size);
  if (state.stackOpen) set('stack', '1');
  if (state.resultsOpen) set('results', '1');
  if (ctx.stages.length) set('stages', JSON.stringify(ctx.stages));
  if (state.brief) set('brief', `${state.brief.part}~${state.brief.driver}`);
  if (state.view === 'parallel') set('view', 'parallel');
  set('axes', state.paxes.map(s => db.bySym[s].id).join(','));
  if (labels.size) set('labels', [...labels.values()].map(l => [l.material, l.stateId || '', Math.round(l.dx), Math.round(l.dy)].join('~')).join(','));
  if (ctx.selected && ctx.details) set('point', ctx.selected.obs.map(o => ctx.details.observations[o].id).join(':'));
  return url;
}
function syncUrl() { try { history.replaceState(null, '', shareUrl()); } catch { /* File previews may restrict history. */ } }
ctx.syncUrl = syncUrl;

/* ---------- everything flows from one refresh ---------- */
const availableCache = new Map();
function familyCounts(xA, yA) {
  const key = `${state.x}|${state.y}|${state.xLog}|${state.yLog}|${state.temperature}`;
  if (!availableCache.has(key)) {
    const allow = ctx.allow(), seen = {}, all = {};
    const add = (bag, family, id) => { (bag[family] ||= new Set()).add(id); };
    for (const m of db.materials) add(all, m.family, m.id);
    for (const row of db.rows) if (Number.isFinite(xA.value(row, allow)) && Number.isFinite(yA.value(row, allow))) add(seen, row.m.family, row.m.id);
    const size = bag => Object.fromEntries(Object.entries(bag).map(([k, v]) => [k, v.size]));
    availableCache.set(key, { available: size(seen), all: size(all) });
  }
  return availableCache.get(key);
}
function refresh(keep = true, light = false) {
  const started = performance.now();
  const xA = new Axis(db, state.x, state.xLog), yA = new Axis(db, state.y, state.yLog);
  ctx.xA = xA; ctx.yA = yA;
  $('x-btn').textContent = xA.label + ' ▾'; $('y-btn').textContent = yA.label + ' ▾';
  const allow = ctx.allow();
  const sizeScale = db.bySym[state.size] ? scaleFor(state.size) : null;
  const base = ctx.baseRows();
  const run = runStages(db, ctx.stages, base, ctx.stageContext());
  const pass = new Set(run.rows), find = state.find;
  const rowLive = row => pass.has(row) && (!find || row.m.search.includes(find));
  ctx.rowLive = rowLive;
  ctx.passing = run.rows;
  const rows = [], liveRows = [];
  for (const point of db.points(base, [xA, yA], allow)) {
    if (!ctx.passesBasis(point)) continue;
    const liveRow = point.rows.find(rowLive), live = !!liveRow;
    if (!live && !state.ghosts) continue;
    if (liveRow) point.row = liveRow;
    const x = xA.value(point.row, allow), y = yA.value(point.row, allow);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    const shapeX = xA.interval(point.row), shapeY = yA.interval(point.row);
    // An interval reaching zero cannot be drawn on a log axis.
    const usable = (range, log) => !log || range[0] > 0;
    const tag = ctx.visibleTag(point.m);
    const row = {
      key: point.key, point, m: point.m, name: ctx.pointName(point), family: point.m.family, group: point.m.group,
      x, y, tx: xA.t(x), ty: yA.t(y), color: ctx.colorFor(point.row), dim: !live,
      ring: state.color === 'tag' ? null : tag ? tags.color(tag) : null,
      size: sizeScale ? (propValue(sizeScale, point.row) > 0 ? 2 + sizeScale.f(propValue(sizeScale, point.row)) * 8 : 2) : null,
      bound: point.hasBounds, hasBounds: point.hasBounds,
      tRange: (shapeX && usable(shapeX, xA.log)) || (shapeY && usable(shapeY, yA.log)) ? {
        ...(shapeX && usable(shapeX, xA.log) ? { x: shapeX.map(v => xA.t(v)) } : {}),
        ...(shapeY && usable(shapeY, yA.log) ? { y: shapeY.map(v => yA.t(v)) } : {}),
      } : null,
    };
    rows.push(row);
    if (live) liveRows.push(row);
  }
  plot.opts.pointAlpha = db.bySym[state.color] ? 1 : .9;
  plot.opts.showRanges = state.ranges;
  plot.opts.showPoints = state.showPoints;
  plot.opts.showPointLabels = state.pointLabels;
  plot.setData({ rows, xAxis: xA, yAxis: yA, keepView: keep });
  ctx.rowByKey = new Map(rows.map(r => [r.key, r]));
  ctx.plotted = liveRows;
  const shapes = window.AshbyShapes.build(liveRows, {
    method: state.shape, grouping: state.group, xLog: state.xLog, yLog: state.yLog,
    colorOf: family => FAMILY_COLORS[family],
    tagsOf: r => tags.of(r.m.id).filter(n => !state.hiddenTags.has(n)), tagColor: name => tags.color(name),
  });
  plot.setShapes(shapes);
  plot.growFit(shapes, keep);
  if (ctx.selBox) syncBoxSelection();
  const outside = shapes.reduce((sum, s) => sum + (s.outside || 0), 0), skipped = shapes.skipped || [];
  $('outside-note').hidden = !outside && !skipped.length;
  $('outside-note').textContent = [
    outside ? `${outside.toLocaleString()} isolated ${outside === 1 ? 'material sits' : 'materials sit'} outside the outlines, so one far point does not stretch a whole family.` : '',
    skipped.length ? `${skipped.join(', ')}: no outline, because most values on these axes are reported bounds.` : '',
  ].filter(Boolean).join(' ');
  $('empty-state').hidden = liveRows.length > 0 || state.view === 'parallel';
  $('export-image').disabled = !rows.length;
  const shown = new Set(liveRows.map(r => r.m.id)).size;
  $('data-status').textContent = `${shown.toLocaleString()} of ${db.core.counts.materials.toLocaleString()} materials · ${liveRows.length.toLocaleString()} points`;
  ctx.updateRanking();
  ctx.updateParallel(base, allow);
  if (!light) {
    if (state.view === 'parallel') {
      const seen = {}, all = {};
      const axes = state.paxes.map(s => new Axis(db, s));
      for (const m of db.materials) (all[m.family] ||= new Set()).add(m.id);
      for (const row of db.rows) if (axes.every(a => Number.isFinite(a.value(row, allow)))) (seen[row.m.family] ||= new Set()).add(row.m.id);
      const size = bag => Object.fromEntries(Object.entries(bag).map(([k, v]) => [k, v.size]));
      keepFocus($('family-toggles'), () => renderFamilies(size(seen), size(all)));
    } else {
      const counts = familyCounts(xA, yA);
      keepFocus($('family-toggles'), () => renderFamilies(counts.available, counts.all));
    }
    keepFocus($('tag-rows'), renderTags);
    keepFocus($('views'), renderViews);
    if (state.stackOpen) keepFocus($('stages'), ctx.renderStages);
  } else if (state.stackOpen) ctx.updateFunnels();
  renderLabels();
  ctx.renderResults();
  ctx.renderBrowser();
  ctx.refreshCard();
  const legend = $('color-legend');
  if (db.bySym[state.color]) {
    const s = scaleFor(state.color);
    legend.replaceChildren(el('div', { class: 'gradient', style: `background:linear-gradient(90deg,${[0, .25, .5, .75, 1].map(ramp).join(',')})` }), el('div', { class: 'gradient-labels' }, el('span', {}, formatValue(10 ** s.lo)), el('span', {}, db.bySym[state.color].display_unit), el('span', {}, formatValue(10 ** s.hi))));
  } else legend.replaceChildren();
  const active = ctx.stages.filter(s => s.enabled !== false).length;
  $('stack-count').textContent = active ? String(active) : '';
  $('results-count').textContent = run.materials.toLocaleString();
  const scope = $('scope'), limited = state.isolate || state.hidden.size;
  const findMatches = find ? run.rows.some(row => row.m.search.includes(find)) : false;
  const findMissing = find && (state.view === 'parallel' ? !ctx.parallelHasLive() : !liveRows.length);
  scope.hidden = !limited && !findMissing;
  scope.replaceChildren(
    findMissing ? (findMatches ? 'Found, but not on these axes' : 'Nothing found') : '',
    ...(limited ? [state.isolate ? ` Only ${state.isolate.size} materials` : ` ${state.hidden.size} hidden`, el('button', { type: 'button', onclick: () => { state.isolate = null; state.hidden.clear(); refresh(false); } }, 'Show all')] : []));
  syncHighlight();
  syncUrl();
  window.__lastRefreshMs = performance.now() - started;
  window.__live = liveRows.length;
}
ctx.refresh = refresh;

/* ---------- settings and page chrome ---------- */
function applySettings() {
  document.documentElement.dataset.theme = settings.theme;
  document.body.dataset.density = settings.density;
  $('setting-density').value = settings.density;
  $('setting-precision').value = settings.precision;
  document.querySelectorAll('#theme-control button').forEach(button => {
    button.classList.toggle('active', button.dataset.theme === settings.theme);
    button.setAttribute('aria-pressed', String(button.dataset.theme === settings.theme));
  });
  try { localStorage.setItem('materials-explorer-settings', JSON.stringify(settings)); } catch { /* Use session settings. */ }
}
function settingsPanel(open) {
  $('settings-panel').classList.toggle('open', open);
  $('settings-overlay').classList.toggle('open', open);
  $('settings-panel').setAttribute('aria-hidden', String(!open));
  $('settings-panel').inert = !open;
  (open ? $('settings-close') : $('settings-button')).focus();
}
function bindChrome() {
  $('settings-button').addEventListener('click', () => settingsPanel(true));
  $('settings-close').addEventListener('click', () => settingsPanel(false));
  $('settings-overlay').addEventListener('click', () => settingsPanel(false));
  const redraw = () => { plot?.draw(); ctx.drawParallel?.(); };
  document.querySelectorAll('#theme-control button').forEach(button => button.addEventListener('click', () => { settings.theme = button.dataset.theme; applySettings(); redraw(); }));
  $('setting-density').addEventListener('change', () => { settings.density = $('setting-density').value; applySettings(); });
  $('setting-precision').addEventListener('change', () => { settings.precision = Number($('setting-precision').value); applySettings(); ctx.refreshCard?.(); ctx.updateRanking?.(); });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', redraw);
  $('retry-load').addEventListener('click', () => { if (bound) location.reload(); else init(); });
  applySettings();
}
function bindApp() {
  $('x-btn').onclick = () => openAxis('x');
  $('y-btn').onclick = () => openAxis('y');
  document.addEventListener('pointerdown', e => { if (!$('pop').hidden && !e.target.closest('#pop, .axis-btn')) $('pop').hidden = true; });
  // A drag anywhere on the chart must never become a text selection. Inputs and the card stay selectable.
  $('wrap').addEventListener('selectstart', e => {
    const target = e.target.nodeType === 1 ? e.target : e.target.parentElement;
    if (!target?.closest('input, .mat')) e.preventDefault();
  });
  $('labels').addEventListener('wheel', e => plot.wheelZoom(e), { passive: false });
  $('labels-clear').onclick = () => { labels.clear(); saveLabels(); renderLabels(); renderPop(false); plot.draw(); };
  $('tag-go').onclick = applyTag;
  $('tag-name').onkeydown = e => { if (e.key === 'Enter') applyTag(); e.stopPropagation(); if (e.key === 'Escape') { e.target.blur(); clearSelection(); } };
  $('sel-clear').onclick = clearSelection;
  $('sel-label').onclick = () => addLabels(selectedRows());
  $('sel-isolate').onclick = () => { state.isolate = new Set(selectedMaterials()); clearSelection(); refresh(false); };
  $('sel-hide').onclick = () => { selectedMaterials().forEach(id => state.hidden.add(id)); clearSelection(); refresh(); };
  $('sel-zoom').onclick = () => { const rows = selectedRows(); if (rows.length) plot.animateTo(plot.computeFit(rows)); };
  $('sel-filter').onclick = () => {
    const b = ctx.selBox, xA = plot.xAxis, yA = plot.yAxis;
    if (!b) return;
    ctx.stages.push({ type: 'region', x: state.x, y: state.y, xLog: state.xLog, yLog: state.yLog, x0: xA.inv(Math.min(b.x0, b.x1)), x1: xA.inv(Math.max(b.x0, b.x1)), y0: yA.inv(Math.min(b.y0, b.y1)), y1: yA.inv(Math.max(b.y0, b.y1)), enabled: true });
    clearSelection(); ctx.setStack(true); refresh();
  };
  document.querySelectorAll('[data-mode]').forEach(b => { b.onclick = () => setMode(b.dataset.mode); });
  $('view-chart').onclick = () => setView('chart');
  $('view-parallel').onclick = () => setView('parallel');
  $('reset-view').onclick = () => plot.fit();
  $('side-btn').onclick = () => toggleSide();
  // Right panel controls.
  options($('color'), [['family', 'Family'], ['tag', 'My tags'], ...db.props.map(p => [p.symbol, p.label])]);
  options($('size'), [['none', 'Same size'], ...db.props.map(p => [p.symbol, p.label])]);
  const control = (id, read) => { $(id).onchange = () => { read($(id)); refresh(); }; };
  control('envelope-mode', c => { state.shape = c.value; if (c.value === 'none') { state.showPoints = true; $('setting-points').checked = true; } $('setting-points').disabled = c.value === 'none'; });
  control('grouping', c => { state.group = c.value; });
  control('color', c => { state.color = c.value; });
  control('size', c => { state.size = c.value; });
  control('setting-points', c => { state.showPoints = c.checked; });
  control('setting-ranges', c => { state.ranges = c.checked; });
  control('setting-isolines', c => { state.isolines = c.checked; });
  control('setting-labels', c => { state.pointLabels = c.checked; });
  control('ghosts', c => { state.ghosts = c.checked; });
  control('temperature-filter', c => { state.temperature = c.value; });
  control('basis-filter', c => { state.basis = c.value; });
  $('all-families').onclick = () => { state.families = new Set(Object.keys(FAMILY_NAMES)); $('material-search').value = ''; state.find = ''; refresh(); };
  $('reset-filters').onclick = () => {
    state.families = new Set(Object.keys(FAMILY_NAMES)); $('material-search').value = ''; state.find = '';
    state.temperature = 'ambient'; state.basis = 'all'; state.isolate = null; state.hidden.clear();
    syncControls(); refresh();
  };
  $('save-view').onclick = () => {
    const name = prompt('Name this view', `${new Axis(db, state.y).short} vs ${new Axis(db, state.x).short}`);
    if (!name) return;
    const list = readViews();
    list.push({ name, x: state.x, y: state.y, xLog: state.xLog, yLog: state.yLog, stages: ctx.stages, brief: state.brief });
    try { localStorage.setItem(VIEW_KEY, JSON.stringify(list)); } catch { /* Private window. */ }
    renderViews();
  };
  $('material-search').addEventListener('input', e => { state.find = e.target.value.toLowerCase().trim(); refresh(); });
  $('material-search').addEventListener('keydown', e => {
    e.stopPropagation();
    if (e.key === 'Escape') { e.target.value = ''; state.find = ''; refresh(); e.target.blur(); }
    if (e.key === 'Enter' && state.find && state.view === 'chart') {
      if (ctx.plotted.length === 1) openPop(ctx.plotted[0].point);
      else if (ctx.plotted.length) { ctx.selBox = null; setSelection(ctx.plotted.map(r => r.key), true); plot.draw(); }
    }
  });
  $('copy-link').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(shareUrl().href); $('copy-link').textContent = 'Copied'; }
    catch { $('copy-link').textContent = 'Copy address bar link'; }
    setTimeout(() => { $('copy-link').textContent = 'Copy link'; }, 2200);
  });
  $('export-image').onclick = exportImage;
  tags.listeners.add(() => { refresh(); renderPop(); });
  addEventListener('keydown', e => {
    if ($('settings-panel').getAttribute('aria-hidden') === 'false') {
      if (e.key === 'Escape') settingsPanel(false);
      if (e.key === 'Tab') {
        const controls = [...$('settings-panel').querySelectorAll('button, select')];
        if (e.shiftKey && document.activeElement === controls[0]) { e.preventDefault(); controls.at(-1).focus(); }
        else if (!e.shiftKey && document.activeElement === controls.at(-1)) { e.preventDefault(); controls[0].focus(); }
      }
      return;
    }
    if (e.target.matches('input, select, textarea')) { if (e.key === 'Escape') e.target.blur(); return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const key = e.key.toLowerCase(), chart = state.view === 'chart';
    if (key === '/') { e.preventDefault(); $('material-search').focus(); }
    else if (key === 'a') setView(chart ? 'parallel' : 'chart');
    else if (key === 'v' && chart) setMode('pan');
    else if (key === 'b' && chart) setMode('box');
    else if (key === 'l' && chart) setMode('lasso');
    else if (key === 'f' && chart) plot.fit();
    else if (key === 'x' && chart) setAxes({ x: state.y, y: state.x, xLog: state.yLog, yLog: state.xLog });
    else if (key === 's') ctx.setStack(!state.stackOpen);
    else if (key === 'r') ctx.setResults(!state.resultsOpen);
    else if (key === 'p') toggleSide();
    else if (key === 'escape') {
      if (ctx.armRegion) { disarm(); setMode('pan'); return; }
      clearSelection(); closePop(); $('pop').hidden = true;
    }
  });
}
function toggleSide(open = $('side').hidden) {
  $('side').hidden = !open;
  $('side-btn').classList.toggle('on', open);
  $('side-btn').setAttribute('aria-pressed', String(open));
}
ctx.toggleSide = toggleSide;
function syncControls() {
  $('envelope-mode').value = state.shape; $('grouping').value = state.group;
  $('color').value = state.color; $('size').value = state.size;
  $('setting-points').checked = state.showPoints; $('setting-points').disabled = state.shape === 'none';
  $('setting-ranges').checked = state.ranges; $('setting-isolines').checked = state.isolines; $('setting-labels').checked = state.pointLabels;
  $('ghosts').checked = state.ghosts;
  $('temperature-filter').value = state.temperature; $('basis-filter').value = state.basis;
}
ctx.syncControls = syncControls;
function exportImage() {
  const canvas = plot.toImage((c, p) => {
    const card = cssVar('--bg-card'), line = cssVar('--border-color'), ink = cssVar('--text-color'), muted = cssVar('--text-light');
    for (const [id, node] of labelNodes) {
      const rect = labelRect(id, p);
      if (!rect) continue;
      c.fillStyle = card; c.strokeStyle = line; c.lineWidth = 1;
      c.beginPath(); c.roundRect(rect.x, rect.y, rect.w, rect.h, 5); c.fill(); c.stroke();
      c.fillStyle = node.style.getPropertyValue('--c') || muted; c.fillRect(rect.x, rect.y + 1, 3, rect.h - 2);
      c.textBaseline = 'alphabetic'; c.textAlign = 'left';
      c.font = '600 12px ' + cssVar('--font-sans'); c.fillStyle = ink;
      c.fillText(node.querySelector('strong').textContent, rect.x + 8, rect.y + 15, rect.w - 12);
      c.font = '11px ' + cssVar('--font-sans'); c.fillStyle = muted;
      c.fillText(node.querySelector('span').textContent, rect.x + 8, rect.y + 29, rect.w - 12);
    }
  });
  canvas.toBlob(blob => {
    const url = URL.createObjectURL(blob);
    const anchor = el('a', { href: url, download: 'ashby-chart.png' });
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, 'image/png');
}

/* ---------- loading ---------- */
const fetchJson = async url => {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Data request failed (${response.status}).`);
  return response.json();
};
ctx.fetchJson = fetchJson;
/* Citations load the first time someone opens sources or exports. */
ctx.ensureDetails = () => {
  ctx.detailsPromise ||= fetchJson('../../data/materials/selection-details.json').then(data => {
    if (data.schema_version !== 2 || data.source_build_id !== db.core.source_build_id) throw new Error('The material data versions differ. Reload to update.');
    ctx.details = data;
    syncUrl();
    return data;
  }).catch(error => { ctx.detailsPromise = null; throw error; });
  return ctx.detailsPromise;
};
function showError(error) {
  $('explorer-main').dataset.state = 'error';
  $('loading-message').textContent = 'Could not load the material chart. ' + error.message;
  $('retry-load').hidden = false;
  $('loading-overlay').hidden = false;
}
let bound = false;
async function init() {
  $('loading-overlay').hidden = false;
  $('retry-load').hidden = true;
  $('loading-message').textContent = 'Loading material properties…';
  try {
    const core = await (window.ashbyCore || fetchJson('../../data/materials/selection-core.json'));
    window.ashbyCore = null;
    if (core.loadError) throw new Error(core.loadError);
    if (core.schema_version !== 2) throw new Error('The material data versions differ. Reload to update.');
    db = new Database(core);
    ctx.db = db;
    if (!bound) {
      bound = true;
      readParams();
      makePlot();
      readLabels();
      setupParallel(ctx);
      setupStack(ctx);
      setupPanels(ctx);
      bindApp();
      syncControls();
      if (isPhone()) toggleSide(false);
    }
    const startView = state.view === 'parallel' ? 'parallel' : 'chart';
    state.view = 'chart';
    document.body.classList.add('chart-on');
    ctx.populateIndices();
    refresh(false);
    plot.view = { ...plot.fitView };
    ctx.rowByKey = new Map(plot.rows.map(r => [r.key, r]));
    ctx.setStack(state.stackOpen);
    ctx.setResults(state.resultsOpen);
    renderLabels();
    plot.draw();
    if (startView === 'parallel') setView('parallel');
    if (params.get('point')) {
      const details = await ctx.ensureDetails();
      const wanted = params.get('point').split(':').map(id => details.observations.findIndex(o => o.id === id));
      const key = [...new Set(wanted)].sort((a, b) => a - b).join(':');
      const row = plot.rows.find(r => [...r.point.obs].sort((a, b) => a - b).join(':') === key);
      if (row) ctx.showCard(row.point);
    }
    $('loading-overlay').hidden = true;
    $('explorer-main').dataset.state = 'ready';
    window.__ready = true;
    verifyRelease();
  } catch (error) { showError(error); }
}
/* The manifest is large and only confirms the release, so it follows the first chart. A chart
   from another build still fails visibly rather than showing old values. */
async function verifyRelease() {
  try {
    const manifest = await fetchJson('../materials/release-manifest.json');
    if (db.core.source_build_id !== manifest.build_id) showError(new Error('The material data versions differ. Reload to update.'));
  } catch (error) { showError(error); }
}
window.MaterialsExplorer = {
  getData: () => ({ counts: db.core.counts, source_build_id: db.core.source_build_id }),
  getRows: () => ctx.plotted.map(r => ({
    id: r.key, material_id: r.m.id, state_id: r.point.stateIndex >= 0 ? db.states[r.point.stateIndex].id : null,
    family: r.m.family, name: r.name, temperatures_K: r.point.temperatures_K, hasBounds: r.hasBounds, x: r.x, y: r.y,
  })),
  getLines: () => ctx.lines,
  getShapes: () => plot.shapes.map(s => ({ family: s.family, label: s.label, outside: s.outside, loops: s.loops.length })),
  getSkippedShapes: () => plot.shapes.skipped || [],
  getShareUrl: () => shareUrl().href,
  getPlot: () => plot,
  showCard: (...args) => ctx.showCard(...args),
};
bindChrome();
init();
