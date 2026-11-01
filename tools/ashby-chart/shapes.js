/* Geometry only. These shapes describe plotted observations, never a population
   distribution or a material family's engineering limits. */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.AshbyShapes = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const FAMILY_NAMES = {
    metal: 'Metals', polymer: 'Polymers', ceramic: 'Ceramics', composite: 'Composites', wood: 'Wood',
    foam: 'Foams', elastomer: 'Elastomers', glass: 'Glasses', concrete: 'Concrete', fiber: 'Fibers',
  };
  const CLASS_LABELS = {
    'ud-carbon-epoxy': 'Carbon / epoxy · UD', 'woven-carbon-epoxy': 'Carbon / epoxy · woven',
    'optical-glass': 'Optical glasses', 'pvc-foam': 'PVC foams', 'pes-foam': 'PES foams',
    'aluminium-titanate': 'Aluminium titanate', 'silicon-carbide': 'Silicon carbides',
    'silicon-nitride': 'Silicon nitrides', 'zirconia-toughened-alumina': 'ZTA',
    'stainless-steel': 'Stainless steels', 'carbon-steel': 'Carbon steels',
  };
  const classLabel = group => CLASS_LABELS[group] || String(group).replaceAll('-', ' ').replace(/^./, c => c.toUpperCase());

  function convexHull(points) {
    const p = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lower = [], upper = [];
    for (const q of p) { while (lower.length > 1 && cross(lower.at(-2), lower.at(-1), q) <= 0) lower.pop(); lower.push(q); }
    for (const q of p.slice().reverse()) { while (upper.length > 1 && cross(upper.at(-2), upper.at(-1), q) <= 0) upper.pop(); upper.push(q); }
    return lower.slice(0, -1).concat(upper.slice(0, -1));
  }
  function chaikin(loop, passes) {
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
  function contains(loop, x, y) {
    let hit = false;
    for (let i = 0, j = loop.length - 1; i < loop.length; j = i++) {
      const [xi, yi] = loop[i], [xj, yj] = loop[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) hit = !hit;
    }
    return hit;
  }
  /* Used when the points are too few or too straight for the enclosing ellipse. */
  function principalEllipse(points, minRadius) {
    const n = points.length;
    const mx = points.reduce((s, p) => s + p[0], 0) / n, my = points.reduce((s, p) => s + p[1], 0) / n;
    let a = 0, b = 0, c = 0;
    for (const [x, y] of points) { a += (x - mx) ** 2; b += (x - mx) * (y - my); c += (y - my) ** 2; }
    const angle = .5 * Math.atan2(2 * b, a - c), cos = Math.cos(angle), sin = Math.sin(angle);
    let r1 = 0, r2 = 0;
    for (const [x, y] of points) {
      r1 = Math.max(r1, Math.abs((x - mx) * cos + (y - my) * sin));
      r2 = Math.max(r2, Math.abs(-(x - mx) * sin + (y - my) * cos));
    }
    return ellipsePoints(mx, my, r1 * 1.15 + minRadius, r2 * 1.15 + minRadius, cos, sin);
  }
  function ellipsePoints(cx, cy, r1, r2, cos, sin) {
    const loop = [];
    for (let i = 0; i < 72; i++) {
      const t = i / 72 * Math.PI * 2, x = r1 * Math.cos(t), y = r2 * Math.sin(t);
      loop.push([cx + x * cos - y * sin, cy + x * sin + y * cos]);
    }
    return { loop, center: [cx, cy] };
  }
  /* Smallest ellipse around the points (Khachiyan's algorithm on the hull), so it follows
     the family's extent and a dense run of similar grades does not pull it off centre. */
  function enclosingEllipse(points, pad) {
    const hull = convexHull(points);
    if (hull.length < 3) return principalEllipse(points, pad);
    const n = hull.length, u = new Array(n).fill(1 / n);
    const invert3 = m => {
      const [a, b, c, d, e, f, g, h, i] = m;
      const A = e * i - f * h, B = f * g - d * i, C = d * h - e * g, det = a * A + b * B + c * C;
      if (Math.abs(det) < 1e-14) return null;
      return [A, c * h - b * i, b * f - c * e, B, a * i - c * g, c * d - a * f, C, b * g - a * h, a * e - b * d].map(v => v / det);
    };
    for (let iter = 0; iter < 400; iter++) {
      const m = new Array(9).fill(0);
      hull.forEach(([x, y], k) => { const q = [x, y, 1]; for (let r = 0; r < 3; r++) for (let s = 0; s < 3; s++) m[r * 3 + s] += u[k] * q[r] * q[s]; });
      const inv = invert3(m);
      if (!inv) return principalEllipse(points, pad);
      let top = -1, at = 0;
      hull.forEach(([x, y], k) => {
        const q = [x, y, 1];
        let v = 0;
        for (let r = 0; r < 3; r++) for (let s = 0; s < 3; s++) v += q[r] * inv[r * 3 + s] * q[s];
        if (v > top) { top = v; at = k; }
      });
      const step = (top - 3) / (3 * (top - 1));
      if (step < 1e-3) break;
      for (let k = 0; k < n; k++) u[k] *= 1 - step;
      u[at] += step;
    }
    let cx = 0, cy = 0;
    hull.forEach(([x, y], k) => { cx += u[k] * x; cy += u[k] * y; });
    let a = 0, b = 0, c = 0;
    hull.forEach(([x, y], k) => { a += u[k] * (x - cx) ** 2; b += u[k] * (x - cx) * (y - cy); c += u[k] * (y - cy) ** 2; });
    const mean = (a + c) / 2, spread = Math.sqrt(Math.max(0, (a - c) ** 2 / 4 + b * b));
    const l1 = mean + spread, l2 = mean - spread;
    if (l2 < 1e-10) return principalEllipse(points, pad);
    const angle = .5 * Math.atan2(2 * b, a - c), cos = Math.cos(angle), sin = Math.sin(angle);
    // The iteration stops slightly early, so scale until every hull point is inside.
    let scale = 0;
    for (const [x, y] of hull) {
      const p = (x - cx) * cos + (y - cy) * sin, q = -(x - cx) * sin + (y - cy) * cos;
      scale = Math.max(scale, p * p / l1 + q * q / l2);
    }
    return ellipsePoints(cx, cy, Math.sqrt(scale * l1) + pad, Math.sqrt(scale * l2) + pad, cos, sin);
  }
  /* The hull with its corners rounded away, enlarged if rounding cut across any point. */
  function pebble(points, pad) {
    const hull = convexHull(points);
    if (hull.length < 3) return principalEllipse(points, pad);
    const cx = hull.reduce((s, p) => s + p[0], 0) / hull.length, cy = hull.reduce((s, p) => s + p[1], 0) / hull.length;
    const grown = hull.map(([x, y]) => { const dx = x - cx, dy = y - cy, r = Math.hypot(dx, dy) || 1; return [x + dx / r * pad, y + dy / r * pad]; });
    let loop = chaikin(grown, 4);
    for (let n = 0; n < 40 && hull.some(([x, y]) => !contains(loop, x, y)); n++) {
      loop = loop.map(([x, y]) => [cx + (x - cx) * 1.03, cy + (y - cy) * 1.03]);
    }
    return { loop, center: [cx, cy] };
  }
  function splitAtGaps(items, gap, read) {
    const parent = items.map((_, i) => i);
    const find = i => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
    const pts = items.map(read);
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
      if ((pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2 < gap * gap) parent[find(i)] = find(j);
    }
    const clusters = new Map();
    items.forEach((item, i) => { const root = find(i); if (!clusters.has(root)) clusters.set(root, []); clusters.get(root).push(item); });
    return [...clusters.values()];
  }

  const FAMILY_GAP = .09, CLASS_GAP_DECADES = .48, CLASS_GAP_LINEAR = .09;

  /* rows: plotted rows with tx, ty, family, group, hasBounds and optional tRange {x:[a,b], y:[c,d]}.
     Reported bounds never define a shape, because a specified minimum is not a measured value.
     Interval endpoints do. A group with one distinct location has no shape. */
  function build(rows, options = {}) {
    const method = options.method || 'ashby', grouping = options.grouping || 'family';
    if (method === 'none' || grouping === 'points') return [];
    const usable = rows.filter(r => !r.hasBounds);
    if (!usable.length) return [];
    const endpoints = usable.flatMap(r => {
      const xs = r.tRange?.x || [r.tx], ys = r.tRange?.y || [r.ty];
      return xs.flatMap(x => ys.map(y => ({ r, p: [x, y] })));
    }).filter(e => Number.isFinite(e.p[0]) && Number.isFinite(e.p[1]));
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const { p } of endpoints) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
    // Normalize on the plotted extent so shapes keep their proportions on any axes.
    const sx = (x1 - x0) * 1.44 || 1, sy = (y1 - y0) * 1.44 || 1, ox = x0 - (x1 - x0) * .22, oy = y0 - (y1 - y0) * .22;
    const norm = p => [(p[0] - ox) / sx, (p[1] - oy) / sy];
    const unnorm = q => [ox + q[0] * sx, oy + q[1] * sy];
    const groups = new Map();
    for (const entry of endpoints) {
      const names = grouping === 'tag' ? (options.tagsOf?.(entry.r) || []) : [grouping === 'subgroup' ? entry.r.group : entry.r.family];
      for (const name of names) {
        const key = grouping === 'tag' ? name : entry.r.family + '|' + name;
        if (!groups.has(key)) {
          groups.set(key, {
            family: entry.r.family, name, entries: [],
            label: grouping === 'family' ? FAMILY_NAMES[name] || name : grouping === 'tag' ? name : classLabel(name),
            color: grouping === 'tag' ? options.tagColor?.(name) : options.colorOf?.(entry.r.family),
          });
        }
        groups.get(key).entries.push(entry);
      }
    }
    const shapes = [];
    for (const group of groups.values()) {
      let parts;
      if (grouping === 'family' || grouping === 'tag') {
        // A few isolated materials stay outside the oval rather than stretching it across
        // empty space. Their points still plot, and the count is reported.
        const entries = group.entries;
        const kept = entries.length < 10 ? entries : splitAtGaps(entries, FAMILY_GAP, e => norm(e.p)).filter(c => c.length >= Math.max(3, entries.length * .02)).flat();
        parts = [kept.length ? kept : entries];
      } else {
        const inDecades = options.xLog !== false && options.yLog !== false;
        parts = inDecades ? splitAtGaps(group.entries, CLASS_GAP_DECADES, e => e.p) : splitAtGaps(group.entries, CLASS_GAP_LINEAR, e => norm(e.p));
      }
      for (const part of parts) {
        const pts = part.map(e => norm(e.p));
        if (pts.length < 2) continue;
        const pad = .014;
        const fitted = method === 'pebble' ? pebble(pts, .018) : enclosingEllipse(pts, pad);
        const inside = new Set(part.map(e => e.r));
        const outside = new Set(group.entries.filter(e => !inside.has(e.r)).map(e => e.r)).size;
        shapes.push({
          key: group.name, family: group.family, label: group.label, color: group.color,
          loops: [fitted.loop.map(unnorm)], center: unnorm(fitted.center),
          count: inside.size, outside: grouping === 'subgroup' ? 0 : outside, kept: part.map(e => e.p), parts: [],
        });
      }
    }
    return shapes;
  }
  return { build, contains, convexHull, enclosingEllipse, pebble, splitAtGaps, classLabel, FAMILY_NAMES };
});
