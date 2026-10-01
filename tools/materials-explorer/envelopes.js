/* Geometry only. These regions describe the plotted observations, never a
   population distribution or a material family's engineering limits. */
(() => {
  'use strict';
  const LABELS = {
    'ud-carbon-epoxy': 'Carbon / epoxy · UD', 'woven-carbon-epoxy': 'Carbon / epoxy · woven',
    'optical-glass': 'Optical glasses', 'pvc-foam': 'PVC foams', 'pes-foam': 'PES foams',
    'aluminium-titanate': 'Aluminium titanate', 'silicon-carbide': 'Silicon carbides',
    'silicon-nitride': 'Silicon nitrides', 'zirconia-toughened-alumina': 'ZTA',
    'stainless-steel': 'Stainless steels', 'carbon-steel': 'Carbon steels',
  };
  function hull(points) {
    const sorted = [...new Map(points.map(p => [p.join(','), p])).values()].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cross = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    const half = list => {
      const chain = [];
      for (const p of list) {
        while (chain.length > 1 && cross(chain.at(-2), chain.at(-1), p) <= 0) chain.pop();
        chain.push(p);
      }
      return chain.slice(0, -1);
    };
    return [...half(sorted), ...half(sorted.slice().reverse())];
  }
  function splitClusters(points, maximumGap = .48) {
    const remaining = new Set(points), groups = [];
    while (remaining.size) {
      const seed = remaining.values().next().value, group = [seed];
      remaining.delete(seed);
      for (let i = 0; i < group.length; i++) {
        for (const candidate of remaining) {
          if (Math.hypot(candidate[0] - group[i][0], candidate[1] - group[i][1]) <= maximumGap) {
            remaining.delete(candidate); group.push(candidate);
          }
        }
      }
      groups.push(group);
    }
    return groups;
  }
  function roundedHull(points, padding = .055) {
    // Minkowski sum with a small disk in log space. Unlike corner cutting,
    // this contains every measured endpoint and never expands with group size.
    return hull(points.flatMap(([x, y]) => Array.from({length: 32}, (_, i) => {
      const a = i * Math.PI / 16;
      return [x + padding * Math.cos(a), y + padding * Math.sin(a)];
    })));
  }
  function ellipse(points, padding = .055) {
    // Principal-axis enclosing ellipse, NOT a confidence/probability ellipse.
    const n = points.length;
    const center = [0, 1].map(axis => points.reduce((sum, p) => sum + p[axis], 0) / n);
    const centered = points.map(p => [p[0] - center[0], p[1] - center[1]]);
    const xx = centered.reduce((s, p) => s + p[0] ** 2, 0) / n;
    const yy = centered.reduce((s, p) => s + p[1] ** 2, 0) / n;
    const xy = centered.reduce((s, p) => s + p[0] * p[1], 0) / n;
    const angle = .5 * Math.atan2(2 * xy, xx - yy), c = Math.cos(angle), s = Math.sin(angle);
    const rotated = centered.map(([x, y]) => [c * x + s * y, -s * x + c * y]);
    let a = Math.max(padding, ...rotated.map(p => Math.abs(p[0])));
    let b = Math.max(padding, ...rotated.map(p => Math.abs(p[1])));
    const scale = Math.max(1, ...rotated.map(p => Math.hypot(p[0] / a, p[1] / b)));
    a = a * scale + padding; b = b * scale + padding;
    return Array.from({length: 80}, (_, i) => {
      const t = i * Math.PI / 40, x = a * Math.cos(t), y = b * Math.sin(t);
      return [center[0] + c * x - s * y, center[1] + s * x + c * y];
    });
  }
  function build(rows, x, y, mode = 'hulls') {
    if (mode === 'points') return [];
    const groups = new Map();
    for (const row of rows) {
      if (row.hasBounds) continue;
      const group = row.classification?.at(-1) || row.sub_family;
      const key = row.family + '|' + group;
      if (!groups.has(key)) groups.set(key, {family: row.family, group, points: [], ids: new Set()});
      const entry = groups.get(key);
      entry.ids.add(row.material_id);
      const endpoints = prop => row[prop].min != null ? [row[prop].min, row[prop].max] : [row[prop].value];
      for (const px of endpoints(x)) for (const py of endpoints(y)) {
        if (px > 0 && py > 0) entry.points.push([Math.log10(px), Math.log10(py)]);
      }
    }
    return [...groups.values()].flatMap(group => splitClusters(group.points).map(points => {
      if (points.length < 2) return null;
      const perimeter = (mode === 'ellipses' ? ellipse : roundedHull)(points);
      const center = [0, 1].map(axis => points.reduce((sum, p) => sum + p[axis], 0) / points.length);
      const label = LABELS[group.group] || group.group.replaceAll('-', ' ').replace(/^./, c => c.toUpperCase());
      return {family: group.family, label, count: group.ids.size,
        center: center.map(v => 10 ** v), points: perimeter.map(p => p.map(v => 10 ** v))};
    }).filter(Boolean));
  }
  const api = { build, hull, roundedHull, ellipse, splitClusters };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else window.AshbyRegions = api;
})();
