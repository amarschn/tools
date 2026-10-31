/* Shared engine for the October 2026 Ashby chart prototypes: data, formula axes,
   chained filters, tags, blob shapes, and a dependency-free canvas chart. */
(function () {
  'use strict';

  const FAMILY_COLORS = {
    metal: '#4e79a7', polymer: '#e15759', ceramic: '#3f9d97', composite: '#f28e2b', wood: '#72964b',
    foam: '#9c755f', elastomer: '#bd66a0', glass: '#8875c4', concrete: '#6f7782', fiber: '#c9a227',
  };
  const FAMILY_NAMES = {
    metal: 'Metals', polymer: 'Polymers', ceramic: 'Ceramics', composite: 'Composites', wood: 'Wood',
    foam: 'Foams', elastomer: 'Elastomers', glass: 'Glasses', concrete: 'Concrete', fiber: 'Fibers',
  };
  const PALETTE = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#db2777', '#0891b2', '#65a30d', '#ea580c', '#475569'];
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
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

  /* ---------- data ---------- */
  let db = null;
  async function load() {
    if (db) return db;
    const started = performance.now();
    const base = document.currentScript?.src || new URL('core.js', location.href).href;
    const url = new URL('data.json', window.AC_BASE || base);
    const raw = await (await fetch(url)).json();
    const props = raw.properties;
    const bySym = Object.fromEntries(props.map(p => [p.sym, p]));
    const materials = raw.materials.map(m => {
      const d = {}, range = {}, meta = {};
      for (const [sym, v] of Object.entries(m.v)) { d[sym] = v[0]; range[sym] = [v[1], v[2]]; meta[sym] = { basis: v[3], source: raw.sources[v[4]], locator: v[5] }; }
      return { id: m.id, name: m.n, family: m.f, cls: m.c, orgs: m.o, d, range, meta, search: (m.n + ' ' + m.f + ' ' + m.c + ' ' + m.o.join(' ')).toLowerCase() };
    });
    db = { props, bySym, materials, indices: raw.indices, byId: Object.fromEntries(materials.map(m => [m.id, m])), loadMs: performance.now() - started };
    return db;
  }

  /* ---------- formula axes: a small parser, so user text is never evaluated as code ---------- */
  function compile(text) {
    const source = String(text).replace(/ρ/g, 'rho').replace(/σ[yᵧ]/g, 'Sy').replace(/·/g, '*').trim();
    const tokens = source.match(/\s*(\d+\.?\d*(?:e[-+]?\d+)?|\.\d+|[A-Za-z]+|[()+\-*/^])/gi);
    if (!tokens || tokens.join('').replace(/\s/g, '') !== source.replace(/\s/g, '')) return { error: 'Use properties, numbers and + - * / ^ ( )' };
    const list = tokens.map(t => t.trim());
    let at = 0;
    const used = new Set();
    const peek = () => list[at];
    function primary() {
      const t = list[at++];
      if (t == null) throw new Error('Formula ends early');
      if (t === '(') { const inner = sum(); if (list[at++] !== ')') throw new Error('Missing )'); return inner; }
      if (t === '-') { const inner = power(); return m => -inner(m); }
      if (/^[\d.]/.test(t)) { const n = parseFloat(t); return () => n; }
      if (db.bySym[t]) { used.add(t); return m => m.d[t]; }
      throw new Error(`Unknown property "${t}"`);
    }
    function power() { const base = primary(); if (peek() === '^') { at++; const exp = power(); return m => Math.pow(base(m), exp(m)); } return base; }
    function product() { let left = power(); while (peek() === '*' || peek() === '/') { const op = list[at++]; const a = left, b = power(); left = op === '*' ? m => a(m) * b(m) : m => a(m) / b(m); } return left; }
    function sum() { let left = product(); while (peek() === '+' || peek() === '-') { const op = list[at++]; const a = left, b = product(); left = op === '+' ? m => a(m) + b(m) : m => a(m) - b(m); } return left; }
    try {
      const fn = sum();
      if (at !== list.length) throw new Error(`Unexpected "${list[at]}"`);
      if (!used.size) throw new Error('Include at least one property');
      return { fn, used: [...used], isProperty: used.size === 1 && db.bySym[source] != null };
    } catch (error) { return { error: error.message }; }
  }

  class Axis {
    constructor(expr, log = true) { this.expr = expr; this.log = log; this.compiled = compile(expr); }
    get ok() { return !this.compiled.error; }
    get prop() { return db.bySym[this.expr]; }
    value(m) {
      if (!this.ok) return NaN;
      const v = this.compiled.fn(m);
      return Number.isFinite(v) && (!this.log || v > 0) ? v : NaN;
    }
    get label() { const p = this.prop; return p ? `${p.label} (${p.unit})` : this.expr.replace(/rho/g, 'ρ').replace(/\*/g, '·'); }
    get short() { const p = this.prop; return p ? p.label : this.expr.replace(/rho/g, 'ρ').replace(/\*/g, '·'); }
    t(v) { return this.log ? Math.log10(v) : v; }
    inv(t) { return this.log ? 10 ** t : t; }
  }

  function formatValue(v) {
    if (!Number.isFinite(v)) return '–';
    const a = Math.abs(v);
    if (a !== 0 && (a >= 1e6 || a < 1e-3)) return v.toExponential(1).replace('e+', 'e');
    return a >= 100 ? Math.round(v).toLocaleString('en-US') : +v.toPrecision(3) + '';
  }
  function formatProp(sym, v) { const p = db.bySym[sym]; return p ? `${formatValue(v)} ${p.unit}`.trim() : formatValue(v); }

  /* ---------- tags live in the browser and are shared across all prototypes ---------- */
  const TAG_KEY = 'ashby-prototype-tags';
  const tagListeners = new Set();
  const tags = {
    read() { try { return JSON.parse(localStorage.getItem(TAG_KEY)) || {}; } catch { return {}; } },
    write(all) { try { localStorage.setItem(TAG_KEY, JSON.stringify(all)); } catch { /* private window: tags last until reload */ } memory = all; tagListeners.forEach(f => f(all)); },
    all() { return memory; },
    names() { return Object.keys(memory); },
    has(name, id) { return (memory[name]?.ids || []).includes(id); },
    of(id) { return Object.keys(memory).filter(n => memory[n].ids.includes(id)); },
    color(name) { return memory[name]?.color || '#475569'; },
    add(name, ids) {
      const all = { ...memory };
      const current = all[name] || { color: PALETTE[Object.keys(all).length % PALETTE.length], ids: [] };
      all[name] = { ...current, ids: [...new Set([...current.ids, ...ids])] };
      tags.write(all);
    },
    remove(name, ids) { const all = { ...memory }; if (all[name]) { all[name] = { ...all[name], ids: all[name].ids.filter(i => !ids.includes(i)) }; tags.write(all); } },
    drop(name) { const all = { ...memory }; delete all[name]; tags.write(all); },
    listen(fn) { tagListeners.add(fn); },
  };
  let memory = tags.read();

  /* ---------- chained filters: each stage narrows the result of the stage before it ---------- */
  function stageTest(stage) {
    switch (stage.type) {
      case 'family': { const set = new Set(stage.values); return m => set.has(m.family); }
      case 'class': { const set = new Set(stage.values); return m => set.has(m.cls); }
      case 'org': { const set = new Set(stage.values); return m => m.orgs.some(o => set.has(o)); }
      case 'text': { const q = stage.value.toLowerCase().trim(); return m => !q || m.search.includes(q); }
      case 'tag': return m => tags.has(stage.value, m.id);
      case 'limit': {
        const axis = new Axis(stage.expr, false);
        return m => { const v = axis.value(m); return Number.isFinite(v) && (stage.min == null || v >= stage.min) && (stage.max == null || v <= stage.max); };
      }
      case 'region': {
        const ax = new Axis(stage.x, stage.xLog), ay = new Axis(stage.y, stage.yLog);
        return m => { const x = ax.value(m), y = ay.value(m); return Number.isFinite(x) && Number.isFinite(y) && x >= stage.x0 && x <= stage.x1 && y >= stage.y0 && y <= stage.y1; };
      }
      case 'index': {
        const ax = new Axis(stage.x), ay = new Axis(stage.y);
        return m => { const x = ax.value(m), y = ay.value(m); if (!Number.isFinite(x) || !Number.isFinite(y)) return false; const c = Math.log10(y) - stage.slope * Math.log10(x); return stage.above ? c >= stage.c : c <= stage.c; };
      }
      default: return () => true;
    }
  }
  function runStages(stages, materials = db.materials) {
    let current = materials;
    const counts = [];
    for (const stage of stages) {
      const before = current.length;
      if (stage.enabled !== false) { const test = stageTest(stage); current = current.filter(test); }
      counts.push({ before, after: current.length });
    }
    return { rows: current, counts };
  }

  /* ---------- blob geometry, built in normalized plot space so shapes look round ---------- */
  function marchingSquares(field, w, h, iso) {
    const segs = new Map();
    const key = (x, y) => Math.round(x * 64) + ':' + Math.round(y * 64);
    const add = (a, b) => { const k = key(a[0], a[1]); if (!segs.has(k)) segs.set(k, []); segs.get(k).push({ a, b }); };
    const lerp = (v0, v1) => (iso - v0) / (v1 - v0 || 1e-9);
    for (let j = 0; j < h - 1; j++) for (let i = 0; i < w - 1; i++) {
      const a = field[j * w + i], b = field[j * w + i + 1], c = field[(j + 1) * w + i + 1], d = field[(j + 1) * w + i];
      const code = (a >= iso ? 8 : 0) | (b >= iso ? 4 : 0) | (c >= iso ? 2 : 0) | (d >= iso ? 1 : 0);
      if (code === 0 || code === 15) continue;
      const T = [i + lerp(a, b), j], R = [i + 1, j + lerp(b, c)], B = [i + lerp(d, c), j + 1], L = [i, j + lerp(a, d)];
      switch (code) {
        case 1: add(L, B); break; case 2: add(B, R); break; case 3: add(L, R); break; case 4: add(R, T); break;
        case 5: add(L, T); add(R, B); break; case 6: add(B, T); break; case 7: add(L, T); break; case 8: add(T, L); break;
        case 9: add(T, B); break; case 10: add(T, R); add(B, L); break; case 11: add(T, R); break; case 12: add(R, L); break;
        case 13: add(R, B); break; case 14: add(B, L); break;
      }
    }
    const loops = [];
    const used = new Set();
    for (const [, list] of segs) for (const seg of list) {
      if (used.has(seg)) continue;
      used.add(seg);
      const loop = [seg.a];
      let next = seg.b, guard = 0;
      while (guard++ < 20000) {
        loop.push(next);
        const options = segs.get(key(next[0], next[1]));
        const follow = options && options.find(s => !used.has(s));
        if (!follow) break;
        used.add(follow);
        next = follow.b;
      }
      if (loop.length > 5) loops.push(loop);
    }
    return loops;
  }
  function chaikin(loop, passes = 2) {
    let p = loop;
    for (let n = 0; n < passes; n++) {
      const out = [];
      for (let i = 0; i < p.length; i++) {
        const a = p[i], b = p[(i + 1) % p.length];
        out.push([a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25], [a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75]);
      }
      p = out;
    }
    return p;
  }
  /* power 1 is true density. Higher powers stop stacked points from inflating a shape:
     a cluster of 500 grows only a little more than one of 50, and halos still melt together. */
  function densityField(points, sigma, w, h, power = 1) {
    const field = new Float32Array(w * h);
    const reach = sigma * (power > 1 ? 2.4 : 3.2), s2 = 2 * sigma * sigma / power;
    for (const [u, v] of points) {
      const cx = u * (w - 1), cy = v * (h - 1);
      const rx = Math.ceil(reach * (w - 1)), ry = Math.ceil(reach * (w - 1) * ((h - 1) / (w - 1)) * (w / h));
      const i0 = Math.max(0, Math.floor(cx - rx)), i1 = Math.min(w - 1, Math.ceil(cx + rx));
      const j0 = Math.max(0, Math.floor(cy - ry)), j1 = Math.min(h - 1, Math.ceil(cy + ry));
      for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
        const du = i / (w - 1) - u, dv = (j / (h - 1) - v) * (h / w);
        field[j * w + i] += Math.exp(-(du * du + dv * dv) / s2);
      }
    }
    if (power > 1) for (let n = 0; n < field.length; n++) if (field[n]) field[n] = Math.pow(field[n], 1 / power);
    return field;
  }
  function convexHull(points) {
    const p = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lower = [], upper = [];
    for (const q of p) { while (lower.length > 1 && cross(lower.at(-2), lower.at(-1), q) <= 0) lower.pop(); lower.push(q); }
    for (const q of p.slice().reverse()) { while (upper.length > 1 && cross(upper.at(-2), upper.at(-1), q) <= 0) upper.pop(); upper.push(q); }
    return lower.slice(0, -1).concat(upper.slice(0, -1));
  }
  function ellipseLoop(points, minRadius, stretch = 2.15) {
    const n = points.length;
    const mx = points.reduce((s, p) => s + p[0], 0) / n, my = points.reduce((s, p) => s + p[1], 0) / n;
    let a = 0, b = 0, c = 0;
    for (const [x, y] of points) { a += (x - mx) ** 2; b += (x - mx) * (y - my); c += (y - my) ** 2; }
    a /= n; b /= n; c /= n;
    const tr = a + c, det = Math.sqrt(Math.max(0, (a - c) ** 2 / 4 + b * b));
    const angle = .5 * Math.atan2(2 * b, a - c);
    const r1 = Math.max(minRadius, stretch * Math.sqrt(Math.max(0, tr / 2 + det)));
    const r2 = Math.max(minRadius, stretch * Math.sqrt(Math.max(0, tr / 2 - det)));
    const loop = [];
    for (let i = 0; i < 56; i++) {
      const t = i / 56 * Math.PI * 2, x = r1 * Math.cos(t), y = r2 * Math.sin(t);
      loop.push([mx + x * Math.cos(angle) - y * Math.sin(angle), my + x * Math.sin(angle) + y * Math.cos(angle)]);
    }
    return loop;
  }

  function splitAtGaps(points, gap) {
    const parent = points.map((_, i) => i);
    const find = i => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
    for (let i = 0; i < points.length; i++) for (let j = i + 1; j < points.length; j++) {
      if ((points[i][0] - points[j][0]) ** 2 + (points[i][1] - points[j][1]) ** 2 < gap * gap) parent[find(i)] = find(j);
    }
    const clusters = new Map();
    points.forEach((p, i) => { const root = find(i); if (!clusters.has(root)) clusters.set(root, []); clusters.get(root).push(p); });
    return [...clusters.values()];
  }

  /* groups: [{key, color, points:[[tx,ty]...]}]. Returns shapes in plot (log/linear) coordinates. */
  function buildBlobs(groups, bounds, options = {}) {
    const method = options.method || 'gooey';
    const softness = options.softness ?? 1;
    const W = 150, H = Math.round(W * (bounds.aspect || .68));
    const sx = bounds.x1 - bounds.x0 || 1, sy = bounds.y1 - bounds.y0 || 1;
    const toNorm = p => [(p[0] - bounds.x0) / sx, (p[1] - bounds.y0) / sy];
    const unGrid = q => [bounds.x0 + q[0] / (W - 1) * sx, bounds.y0 + q[1] / (H - 1) * sy];
    const unNorm = q => [bounds.x0 + q[0] * sx, bounds.y0 + q[1] * sy];
    const out = [];
    for (const group of groups) {
      if (!group.points.length) continue;
      const norm = group.points.map(toNorm);
      const shape = { key: group.key, label: group.label || group.key, color: group.color, loops: [], levels: [], parts: [], center: null };
      if (method === 'gooey' || method === 'contour') {
        const sigma = (method === 'gooey' ? .02 : .018) * softness;
        const field = densityField(norm, sigma, W, H, method === 'gooey' ? 3 : 1);
        if (method === 'gooey') {
          shape.loops = marchingSquares(field, W, H, .42).map(l => chaikin(l).map(unGrid));
        } else {
          const peak = field.reduce((a, b) => Math.max(a, b), 0);
          for (const level of [.42, Math.max(.9, peak * .12), Math.max(1.8, peak * .42)]) {
            if (level > peak) continue;
            shape.levels.push(marchingSquares(field, W, H, level).map(l => chaikin(l).map(unGrid)));
          }
          shape.loops = shape.levels[0] || [];
        }
      } else if (method === 'pebble') {
        const hull = convexHull(norm);
        const cx = hull.reduce((s, p) => s + p[0], 0) / hull.length, cy = hull.reduce((s, p) => s + p[1], 0) / hull.length;
        const pad = .018 * softness;
        const grown = (hull.length > 2 ? hull : ellipseLoop(norm, pad, 1)).map(([x, y]) => { const dx = x - cx, dy = y - cy, r = Math.hypot(dx, dy) || 1; return [x + dx / r * pad, y + dy / r * pad]; });
        shape.loops = [chaikin(grown, 4).map(unNorm)];
      } else if (method === 'classic') {
        // Classic chart: an ellipse per material class, inside a soft family envelope.
        const field = densityField(norm, .026 * softness, W, H, 3);
        shape.loops = marchingSquares(field, W, H, .32).map(l => chaikin(l).map(unGrid));
        const byClass = new Map();
        group.points.forEach((p, i) => { const c = group.classes?.[i] || group.key; if (!byClass.has(c)) byClass.set(c, []); byClass.get(c).push(norm[i]); });
        // A far outlier would stretch one ellipse across empty space, so split each class at large gaps.
        for (const [name, pts] of byClass) for (const cluster of splitAtGaps(pts, .09)) shape.parts.push({ label: name, loop: ellipseLoop(cluster, .011 * softness).map(unNorm), count: cluster.length });
      }
      shape.center = group.points.reduce((s, p) => [s[0] + p[0], s[1] + p[1]], [0, 0]).map(v => v / group.points.length);
      out.push(shape);
    }
    return out;
  }

  /* ---------- canvas chart ---------- */
  function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function niceTicks(lo, hi, count) {
    const span = hi - lo, raw = span / Math.max(2, count), mag = 10 ** Math.floor(Math.log10(raw || 1));
    const step = [1, 2, 5, 10].map(n => n * mag).find(s => s >= raw) || mag * 10;
    const out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + step * .001; v += step) out.push(+v.toFixed(10));
    return out;
  }

  class Plot {
    constructor(host, options = {}) {
      this.host = host;
      this.opts = { padding: { l: 62, r: 16, t: 14, b: 48 }, pointSize: 3.2, showLabels: true, ...options };
      this.canvas = el('canvas', { class: 'ac-canvas' });
      this.tip = el('div', { class: 'ac-tip', hidden: true });
      host.classList.add('ac-plot');
      host.append(this.canvas, this.tip);
      this.ctx = this.canvas.getContext('2d');
      this.rows = []; this.shapes = []; this.view = null; this.fitView = null; this.mode = 'pan';
      this.selected = new Set(); this.hover = null; this.overlay = null; this.pointers = new Map();
      this.ro = new ResizeObserver(() => this.resize()); this.ro.observe(host);
      this.bind(); this.resize();
    }
    resize() {
      const rect = this.host.getBoundingClientRect();
      this.w = Math.max(120, rect.width); this.h = Math.max(120, rect.height);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.canvas.width = this.w * dpr; this.canvas.height = this.h * dpr;
      this.canvas.style.width = this.w + 'px'; this.canvas.style.height = this.h + 'px';
      this.dpr = dpr; this.draw();
    }
    get plotBox() { const p = this.opts.padding; return { l: p.l, t: p.t, r: this.w - p.r, b: this.h - p.b, w: this.w - p.l - p.r, h: this.h - p.t - p.b }; }
    sx(t) { const b = this.plotBox, v = this.view; return b.l + (t - v.x0) / (v.x1 - v.x0) * b.w; }
    sy(t) { const b = this.plotBox, v = this.view; return b.b - (t - v.y0) / (v.y1 - v.y0) * b.h; }
    ix(s) { const b = this.plotBox, v = this.view; return v.x0 + (s - b.l) / b.w * (v.x1 - v.x0); }
    iy(s) { const b = this.plotBox, v = this.view; return v.y0 + (b.b - s) / b.h * (v.y1 - v.y0); }
    /* rows: [{m, x, y (display values), color, dim, ring, size}] */
    setData({ rows, xAxis, yAxis, keepView = false }) {
      this.xAxis = xAxis; this.yAxis = yAxis;
      this.rows = rows.map(r => ({ ...r, tx: xAxis.t(r.x), ty: yAxis.t(r.y) }));
      const live = this.rows.filter(r => !r.dim).length ? this.rows.filter(r => !r.dim) : this.rows;
      const fit = this.computeFit(this.opts.fitAll ? this.rows : live);
      this.fitView = fit;
      if (!keepView || !this.view) this.view = { ...fit };
      this.draw();
    }
    computeFit(rows) {
      if (!rows.length) return { x0: 0, x1: 1, y0: 0, y1: 1 };
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const r of rows) { x0 = Math.min(x0, r.tx); x1 = Math.max(x1, r.tx); y0 = Math.min(y0, r.ty); y1 = Math.max(y1, r.ty); }
      const px = (x1 - x0 || 1) * .09, py = (y1 - y0 || 1) * .1;
      return { x0: x0 - px, x1: x1 + px, y0: y0 - py, y1: y1 + py };
    }
    setShapes(shapes) { this.shapes = shapes || []; this.draw(); }
    fit() { this.animateTo({ ...this.fitView }); }
    animateTo(target) {
      const from = { ...this.view }, start = performance.now();
      const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
      const step = now => {
        const k = reduce ? 1 : clamp((now - start) / 220, 0, 1), e = 1 - (1 - k) ** 3;
        for (const key of ['x0', 'x1', 'y0', 'y1']) this.view[key] = from[key] + (target[key] - from[key]) * e;
        this.draw();
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }
    draw() { if (this.pending || !this.view) return; this.pending = true; requestAnimationFrame(() => { this.pending = false; this.render(); this.opts.onDraw?.(); }); }
    pathFor(ctx, loop) {
      for (let i = 0; i < loop.length; i++) {
        const X = this.sx(loop[i][0]), Y = this.sy(loop[i][1]);
        if (i) ctx.lineTo(X, Y); else ctx.moveTo(X, Y);
      }
      ctx.closePath();
    }
    render() {
      const { ctx, w, h } = this, b = this.plotBox;
      const colors = { text: cssVar('--ink'), muted: cssVar('--ink-2'), grid: cssVar('--grid'), plot: cssVar('--plot'), ghost: cssVar('--ghost'), halo: cssVar('--card') };
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = colors.plot; ctx.fillRect(b.l, b.t, b.w, b.h);
      ctx.font = '11.5px ' + cssVar('--sans'); ctx.lineWidth = 1;
      this.drawAxis(colors);
      ctx.save(); ctx.beginPath(); ctx.rect(b.l, b.t, b.w, b.h); ctx.clip();
      this.drawShapes(colors);
      this.opts.beforePoints?.(ctx, this);
      const size = this.opts.pointSize;
      const ghosts = this.rows.filter(r => r.dim);
      ctx.fillStyle = colors.ghost;
      for (const r of ghosts) { ctx.beginPath(); ctx.arc(this.sx(r.tx), this.sy(r.ty), 1.8, 0, 7); ctx.fill(); }
      if (this.opts.showRanges) this.drawRanges();
      const live = this.rows.filter(r => !r.dim);
      for (const r of live) {
        const X = this.sx(r.tx), Y = this.sy(r.ty);
        if (X < b.l - 12 || X > b.r + 12 || Y < b.t - 12 || Y > b.b + 12) continue;
        const radius = r.size || size;
        ctx.globalAlpha = this.opts.pointAlpha ?? .92;
        ctx.fillStyle = r.color; ctx.beginPath(); ctx.arc(X, Y, radius, 0, 7); ctx.fill();
        ctx.globalAlpha = 1;
        if (r.ring) { ctx.strokeStyle = r.ring; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(X, Y, radius + 2.5, 0, 7); ctx.stroke(); ctx.lineWidth = 1; }
        if (this.selected.has(r.m.id)) { ctx.strokeStyle = colors.text; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(X, Y, radius + 2, 0, 7); ctx.stroke(); ctx.lineWidth = 1; }
      }
      this.opts.afterPoints?.(ctx, this);
      if (this.hover) { ctx.strokeStyle = colors.text; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(this.sx(this.hover.tx), this.sy(this.hover.ty), (this.hover.size || size) + 3, 0, 7); ctx.stroke(); ctx.lineWidth = 1; }
      this.drawShapeLabels(colors);
      this.drawOverlay(colors);
      ctx.restore();
      ctx.strokeStyle = colors.grid; ctx.strokeRect(b.l + .5, b.t + .5, b.w, b.h);
    }
    drawRanges() {
      const { ctx } = this;
      ctx.lineWidth = 1;
      for (const r of this.rows) {
        if (r.dim || !r.range) continue;
        const X = this.sx(r.tx), Y = this.sy(r.ty);
        ctx.strokeStyle = r.color;
        if (r.range.x) { ctx.beginPath(); ctx.moveTo(this.sx(this.xAxis.t(r.range.x[0])), Y); ctx.lineTo(this.sx(this.xAxis.t(r.range.x[1])), Y); ctx.stroke(); }
        if (r.range.y) { ctx.beginPath(); ctx.moveTo(X, this.sy(this.yAxis.t(r.range.y[0]))); ctx.lineTo(X, this.sy(this.yAxis.t(r.range.y[1]))); ctx.stroke(); }
      }
    }
    drawShapes() {
      const { ctx } = this;
      const fill = this.opts.blobFill ?? .2;
      for (const shape of this.shapes) {
        ctx.fillStyle = shape.color; ctx.strokeStyle = shape.color;
        if (shape.levels?.length) {
          shape.levels.forEach((loops, i) => {
            ctx.globalAlpha = fill * (.55 + i * .35); ctx.beginPath(); loops.forEach(l => this.pathFor(ctx, l)); ctx.fill('evenodd');
            ctx.globalAlpha = .7; ctx.lineWidth = 1; ctx.stroke();
          });
        } else if (shape.loops.length) {
          ctx.globalAlpha = shape.parts?.length ? fill * .45 : fill; ctx.beginPath(); shape.loops.forEach(l => this.pathFor(ctx, l)); ctx.fill('evenodd');
          ctx.globalAlpha = shape.parts?.length ? .28 : .75; ctx.lineWidth = 1.2; ctx.stroke();
        }
        for (const part of shape.parts || []) {
          ctx.globalAlpha = fill * 1.25; ctx.beginPath(); this.pathFor(ctx, part.loop); ctx.fill();
          ctx.globalAlpha = .8; ctx.lineWidth = 1; ctx.stroke();
        }
        ctx.globalAlpha = 1; ctx.lineWidth = 1;
      }
    }
    drawShapeLabels(colors) {
      if (!this.opts.showLabels) return;
      const { ctx } = this;
      const placed = [];
      ctx.font = '600 12px ' + cssVar('--sans'); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      const b = this.plotBox;
      const shapes = [...this.shapes].sort((a, c) => c.label.length - a.label.length);
      for (const shape of shapes) {
        if (!shape.center) continue;
        let X = clamp(this.sx(shape.center[0]), b.l + 34, b.r - 34), Y = clamp(this.sy(shape.center[1]), b.t + 12, b.b - 12);
        const tw = ctx.measureText(shape.label).width;
        for (let n = 0; n < 12 && placed.some(p => Math.abs(p.X - X) < (p.tw + tw) / 2 + 6 && Math.abs(p.Y - Y) < 16); n++) Y += Y > b.t + b.h / 2 ? -14 : 14;
        placed.push({ X, Y, tw });
        ctx.lineWidth = 3.5; ctx.strokeStyle = colors.halo; ctx.lineJoin = 'round'; ctx.strokeText(shape.label, X, Y);
        ctx.fillStyle = colors.text; ctx.fillText(shape.label, X, Y);
      }
      ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic'; ctx.lineWidth = 1;
    }
    drawOverlay(colors) {
      const { ctx } = this, o = this.overlay;
      if (!o) return;
      ctx.strokeStyle = colors.text; ctx.fillStyle = colors.text; ctx.setLineDash([5, 4]);
      if (o.kind === 'box') {
        const x = Math.min(o.x0, o.x1), y = Math.min(o.y0, o.y1), wd = Math.abs(o.x1 - o.x0), ht = Math.abs(o.y1 - o.y0);
        ctx.globalAlpha = .08; ctx.fillRect(x, y, wd, ht); ctx.globalAlpha = 1; ctx.strokeRect(x, y, wd, ht);
      } else if (o.kind === 'lasso') {
        ctx.beginPath(); o.path.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath();
        ctx.globalAlpha = .08; ctx.fill(); ctx.globalAlpha = 1; ctx.stroke();
      }
      ctx.setLineDash([]);
    }
    drawAxis(colors) {
      const { ctx } = this, b = this.plotBox, v = this.view;
      ctx.textBaseline = 'middle'; ctx.fillStyle = colors.muted; ctx.strokeStyle = colors.grid;
      const ticks = (axis, lo, hi, room) => {
        if (!axis) return { major: [], minor: [] };
        if (axis.log) {
          const span = hi - lo, major = [], minor = [];
          if (span > 2.6 || room < 3.5) { const step = Math.max(1, Math.ceil(span / room)); for (let d = Math.ceil(lo); d <= hi; d += step) major.push(d); for (let d = Math.floor(lo); d <= hi; d++) if (step === 1 && room > 4) for (const m of [2, 5]) { const t = d + Math.log10(m); if (t >= lo && t <= hi) minor.push(t); } }
          else for (let d = Math.floor(lo); d <= hi; d++) for (const m of (span > 1.2 ? [1, 2, 5] : [1, 1.5, 2, 3, 5, 7])) { const t = d + Math.log10(m); if (t >= lo && t <= hi) major.push(t); }
          return { major, minor };
        }
        return { major: niceTicks(lo, hi, room), minor: [] };
      };
      const tx = ticks(this.xAxis, v.x0, v.x1, b.w / 80), ty = ticks(this.yAxis, v.y0, v.y1, b.h / 46);
      for (const t of tx.minor) { const X = this.sx(t); ctx.globalAlpha = .45; ctx.beginPath(); ctx.moveTo(X, b.t); ctx.lineTo(X, b.b); ctx.stroke(); ctx.globalAlpha = 1; }
      for (const t of ty.minor) { const Y = this.sy(t); ctx.globalAlpha = .45; ctx.beginPath(); ctx.moveTo(b.l, Y); ctx.lineTo(b.r, Y); ctx.stroke(); ctx.globalAlpha = 1; }
      ctx.textAlign = 'center';
      for (const t of tx.major) {
        const X = this.sx(t); if (X < b.l - 1 || X > b.r + 1) continue;
        ctx.beginPath(); ctx.moveTo(X + .5, b.t); ctx.lineTo(X + .5, b.b); ctx.stroke();
        ctx.fillText(formatValue(this.xAxis.inv(t)), X, b.b + 14);
      }
      ctx.textAlign = 'right';
      for (const t of ty.major) {
        const Y = this.sy(t); if (Y < b.t - 1 || Y > b.b + 1) continue;
        ctx.beginPath(); ctx.moveTo(b.l, Y + .5); ctx.lineTo(b.r, Y + .5); ctx.stroke();
        ctx.fillText(formatValue(this.yAxis.inv(t)), b.l - 7, Y);
      }
      ctx.textAlign = 'start';
      if (this.opts.drawAxisTitles !== false && this.xAxis) {
        ctx.fillStyle = colors.muted; ctx.font = '12.5px ' + cssVar('--sans'); ctx.textAlign = 'center';
        ctx.fillText(this.xAxis.label, b.l + b.w / 2, this.h - 12);
        ctx.save(); ctx.translate(15, b.t + b.h / 2); ctx.rotate(-Math.PI / 2); ctx.fillText(this.yAxis.label, 0, 0); ctx.restore();
        ctx.textAlign = 'start'; ctx.font = '11.5px ' + cssVar('--sans');
      }
      ctx.textBaseline = 'alphabetic';
    }
    nearest(x, y, limit = 16) {
      let best = null, bestD = limit * limit;
      for (const r of this.rows) {
        if (r.dim) continue;
        const dx = this.sx(r.tx) - x, dy = this.sy(r.ty) - y, d = dx * dx + dy * dy;
        if (d < bestD) { bestD = d; best = r; }
      }
      return best;
    }
    zoomAt(cx, cy, factor) {
      const X = this.ix(cx), Y = this.iy(cy), v = this.view;
      this.view = { x0: X + (v.x0 - X) * factor, x1: X + (v.x1 - X) * factor, y0: Y + (v.y0 - Y) * factor, y1: Y + (v.y1 - Y) * factor };
      this.draw();
    }
    point(e) { const r = this.canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
    bind() {
      const c = this.canvas;
      c.style.touchAction = 'none';
      c.addEventListener('wheel', e => { e.preventDefault(); const [x, y] = this.point(e); this.zoomAt(x, y, Math.exp(e.deltaY * .0016)); }, { passive: false });
      c.addEventListener('dblclick', () => this.fit());
      c.addEventListener('pointerdown', e => {
        const [x, y] = this.point(e);
        this.pointers.set(e.pointerId, [x, y]);
        c.setPointerCapture(e.pointerId);
        if (this.pointers.size === 2) { this.drag = null; this.overlay = null; const [a, b] = [...this.pointers.values()]; this.pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]) }; return; }
        const handled = this.opts.onPointerDown?.(x, y, e, this);
        if (handled) { this.drag = { kind: 'custom' }; return; }
        if (this.mode === 'box') { this.overlay = { kind: 'box', x0: x, y0: y, x1: x, y1: y }; this.drag = { kind: 'box' }; }
        else if (this.mode === 'lasso') { this.overlay = { kind: 'lasso', path: [[x, y]] }; this.drag = { kind: 'lasso' }; }
        else this.drag = { kind: 'pan', x, y, view: { ...this.view }, moved: false };
      });
      c.addEventListener('pointermove', e => {
        const [x, y] = this.point(e);
        if (this.pointers.has(e.pointerId)) this.pointers.set(e.pointerId, [x, y]);
        if (this.pinch && this.pointers.size === 2) {
          const [a, b] = [...this.pointers.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
          this.zoomAt((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, this.pinch.d / d); this.pinch.d = d; return;
        }
        const drag = this.drag;
        if (!drag) {
          const hit = this.nearest(x, y);
          if (hit !== this.hover) { this.hover = hit; this.showTip(hit, x, y); this.draw(); c.style.cursor = hit ? 'pointer' : (this.mode === 'pan' ? 'grab' : 'crosshair'); }
          else if (hit) this.placeTip(x, y);
          return;
        }
        if (drag.kind === 'custom') { this.opts.onPointerDrag?.(x, y, e, this); return; }
        if (drag.kind === 'pan') {
          const b = this.plotBox, v = drag.view;
          const dx = (x - drag.x) / b.w * (v.x1 - v.x0), dy = (y - drag.y) / b.h * (v.y1 - v.y0);
          if (Math.abs(x - drag.x) + Math.abs(y - drag.y) > 3) drag.moved = true;
          this.view = { x0: v.x0 - dx, x1: v.x1 - dx, y0: v.y0 + dy, y1: v.y1 + dy }; this.hideTip(); c.style.cursor = 'grabbing'; this.draw();
        } else if (drag.kind === 'box') { this.overlay.x1 = x; this.overlay.y1 = y; this.draw(); }
        else if (drag.kind === 'lasso') { this.overlay.path.push([x, y]); this.draw(); }
      });
      const up = e => {
        this.pointers.delete(e.pointerId);
        if (this.pointers.size < 2) this.pinch = null;
        const drag = this.drag; this.drag = null;
        if (!drag) return;
        const [x, y] = this.point(e);
        if (drag.kind === 'custom') { this.opts.onPointerUp?.(x, y, e, this); return; }
        if (drag.kind === 'pan') { c.style.cursor = 'grab'; if (!drag.moved) { const hit = this.nearest(x, y, e.pointerType === 'touch' ? 26 : 16); this.opts.onClick?.(hit, e); } return; }
        const o = this.overlay; this.overlay = null;
        if (drag.kind === 'box' && Math.abs(o.x1 - o.x0) > 4 && Math.abs(o.y1 - o.y0) > 4) {
          const x0 = Math.min(o.x0, o.x1), x1 = Math.max(o.x0, o.x1), y0 = Math.min(o.y0, o.y1), y1 = Math.max(o.y0, o.y1);
          const hits = this.rows.filter(r => { if (r.dim) return false; const X = this.sx(r.tx), Y = this.sy(r.ty); return X >= x0 && X <= x1 && Y >= y0 && Y <= y1; });
          this.opts.onSelect?.(hits, { kind: 'box', x0: this.xAxis.inv(this.ix(x0)), x1: this.xAxis.inv(this.ix(x1)), y0: this.yAxis.inv(this.iy(y1)), y1: this.yAxis.inv(this.iy(y0)) });
        } else if (drag.kind === 'lasso' && o.path.length > 4) {
          const inside = (X, Y) => { let hit = false; for (let i = 0, j = o.path.length - 1; i < o.path.length; j = i++) { const [xi, yi] = o.path[i], [xj, yj] = o.path[j]; if ((yi > Y) !== (yj > Y) && X < (xj - xi) * (Y - yi) / (yj - yi) + xi) hit = !hit; } return hit; };
          this.opts.onSelect?.(this.rows.filter(r => !r.dim && inside(this.sx(r.tx), this.sy(r.ty))), { kind: 'lasso' });
        }
        this.draw();
      };
      c.addEventListener('pointerup', up);
      c.addEventListener('pointercancel', up);
      c.addEventListener('pointerleave', () => { if (!this.drag && this.hover) { this.hover = null; this.hideTip(); this.draw(); } });
    }
    showTip(row, x, y) {
      if (!row) return this.hideTip();
      const format = this.opts.tipFormat || (r => `<strong>${escapeHtml(r.m.name)}</strong><span>${FAMILY_NAMES[r.m.family]} · ${escapeHtml(r.m.cls)}</span><span>${escapeHtml(this.yAxis.short)}: ${formatValue(r.y)}${this.yAxis.prop ? ' ' + this.yAxis.prop.unit : ''}</span><span>${escapeHtml(this.xAxis.short)}: ${formatValue(r.x)}${this.xAxis.prop ? ' ' + this.xAxis.prop.unit : ''}</span>`);
      this.tip.innerHTML = format(row); this.tip.hidden = false; this.placeTip(x, y);
    }
    placeTip(x, y) { const w = this.tip.offsetWidth, h = this.tip.offsetHeight; this.tip.style.left = clamp(x + 14 + w > this.w ? x - w - 14 : x + 14, 4, this.w - w - 4) + 'px'; this.tip.style.top = clamp(y - h - 10 < 0 ? y + 14 : y - h - 10, 4, this.h - h - 4) + 'px'; }
    hideTip() { this.tip.hidden = true; }
  }

  function escapeHtml(text) { return String(text).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

  /* Build chart rows + blob groups for a set of materials and two axes. */
  function chartRows(materials, xAxis, yAxis, opts = {}) {
    const rows = [];
    for (const m of materials) {
      const x = xAxis.value(m), y = yAxis.value(m);
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      rows.push({ m, x, y, color: opts.color ? opts.color(m) : FAMILY_COLORS[m.family], dim: opts.dim ? opts.dim(m) : false, ring: opts.ring ? opts.ring(m) : null, size: opts.size ? opts.size(m) : null, range: opts.range ? opts.range(m) : null });
    }
    return rows;
  }
  function blobGroups(rows, xAxis, yAxis, grouping = 'family') {
    const groups = new Map();
    for (const r of rows) {
      if (r.dim) continue;
      const names = grouping === 'tag' ? tags.of(r.m.id) : [grouping === 'class' ? r.m.cls : r.m.family];
      for (const key of names) {
        if (!groups.has(key)) groups.set(key, {
          key, label: grouping === 'family' ? FAMILY_NAMES[key] : key,
          color: grouping === 'tag' ? tags.color(key) : FAMILY_COLORS[r.m.family], points: [], classes: [],
        });
        const group = groups.get(key);
        group.points.push([xAxis.t(r.x), yAxis.t(r.y)]); group.classes.push(r.m.cls);
      }
    }
    return [...groups.values()];
  }
  function extent(rows, xAxis, yAxis) {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const r of rows) { const tx = xAxis.t(r.x), ty = yAxis.t(r.y); x0 = Math.min(x0, tx); x1 = Math.max(x1, tx); y0 = Math.min(y0, ty); y1 = Math.max(y1, ty); }
    if (!rows.length) return { x0: 0, x1: 1, y0: 0, y1: 1, aspect: .68 };
    const px = (x1 - x0 || 1) * .22, py = (y1 - y0 || 1) * .22;
    return { x0: x0 - px, x1: x1 + px, y0: y0 - py, y1: y1 + py, aspect: .68 };
  }
  function shapesFor(rows, xAxis, yAxis, options = {}) {
    if (options.method === 'none') return [];
    const live = rows.filter(r => !r.dim);
    return buildBlobs(blobGroups(live, xAxis, yAxis, options.grouping), extent(live, xAxis, yAxis), options);
  }

  function downloadCsv(name, header, rows) {
    const quote = v => /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
    const blob = new Blob([[header, ...rows].map(r => r.map(quote).join(',')).join('\n')], { type: 'text/csv' });
    const a = el('a', { href: URL.createObjectURL(blob), download: name }); a.click(); URL.revokeObjectURL(a.href);
  }

  /* Prototype header: every page gets the same switcher back to the gallery. */
  const PAGES = [['a-stack', 'A · Selection stack'], ['b-studio', 'B · Studio'], ['c-axes', 'C · More axes'], ['d-blobs', 'D · Blob lab'], ['e-brief', 'E · Design brief']];
  function header(current) {
    const nav = el('nav', { class: 'ac-nav' }, el('a', { href: '../', class: 'ac-home' }, 'All prototypes'),
      ...PAGES.map(([slug, label]) => el('a', { href: `../${slug}/`, class: slug === current ? 'on' : '' }, label)));
    document.body.prepend(nav);
  }
  function materialCard(m, onClose) {
    const rows = db.props.filter(p => m.d[p.sym] != null).map(p => {
      const meta = m.meta[p.sym], range = m.range[p.sym];
      return el('tr', {}, el('th', {}, p.label),
        el('td', {}, el('strong', {}, formatProp(p.sym, m.d[p.sym])), range[0] !== range[1] ? el('small', {}, ` ${formatValue(range[0])} to ${formatValue(range[1])}`) : null,
          el('small', { class: 'cite' }, `${meta.basis}. ${meta.source[1]}, ${meta.source[0]}. ${meta.locator}`)));
    });
    const tagged = tags.of(m.id);
    return el('div', { class: 'ac-card' },
      el('header', {}, el('div', {}, el('h3', {}, m.name), el('p', {}, `${FAMILY_NAMES[m.family]} · ${m.cls}`)), onClose ? el('button', { class: 'ghost', 'aria-label': 'Close', onclick: onClose }, '×') : null),
      tagged.length ? el('p', { class: 'chips' }, tagged.map(t => el('span', { class: 'chip', style: `--c:${tags.color(t)}` }, t))) : null,
      el('table', {}, el('tbody', {}, rows)));
  }

  window.AC = { load, compile, Axis, Plot, tags, runStages, stageTest, buildBlobs, shapesFor, chartRows, blobGroups, extent, formatValue, formatProp, downloadCsv, header, materialCard, el, clamp, escapeHtml, FAMILY_COLORS, FAMILY_NAMES, PALETTE, get db() { return db; } };
  window.AC_BASE = document.currentScript?.src;
})();
