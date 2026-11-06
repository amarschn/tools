/* Readouts shared by the guided build and the workbench. */
(function () {
  'use strict';
  const C = () => window.Core; const P = () => window.Proto;
  const fmt = (v, d) => C().fmt(v, d);
  function readouts() {
    const c = C(); const r = c.result; const b = c.band;
    if (!r) return '';
    const row = (label, value, low, high, sub) => {
      const hi = Math.max(high, value) * 1.1;
      const left = (x) => `${(x / hi * 100).toFixed(1)}%`;
      return `<div class="read"><div class="k">${label}</div><div class="v">${fmt(Math.round(value / 100) * 100)}<small>Btu/h</small></div><div class="span" role="img" aria-label="Range ${fmt(low)} to ${fmt(high)} Btu/h"><b style="left:${left(low)};width:${((high - low) / hi * 100).toFixed(1)}%"></b><i style="left:${left(value)}"></i></div><div class="sub">Could be ${fmt(Math.round(low / 100) * 100)} to ${fmt(Math.round(high / 100) * 100)}${sub ? `. ${sub}` : ''}</div></div>`;
    };
    const lo = (k, v) => (b ? b[k] : v); 
    const done = Object.keys(c.ELEMENTS).filter((id) => c.confirmed.has(id)).length;
    return row('Heating load', r.heating_total, lo('heating_low', r.heating_total), lo('heating_high', r.heating_total), `${fmt(r.heating_total / 3412.14, 1)} kW`)
      + row('Cooling load', r.cooling_total, lo('cooling_low', r.cooling_total), lo('cooling_high', r.cooling_total), `${fmt(r.cooling_tons, 1)} tons`)
      + `<div class="read"><div class="k">Model detail</div><div class="v">${done}<small>of ${Object.keys(c.ELEMENTS).length} parts confirmed</small></div><div class="sub">Solid lines on the drawing are confirmed. Dashed lines are still assumptions.</div></div>`;
  }
  /** The estimate at each step, so the reader sees it converge. */
  function ladder(order, labels) {
    const c = C(); const entries = order.filter((id) => c.history[id]);
    if (!entries.length) return '<p class="note">The estimate appears here as you build.</p>';
    const W = 330; const H = 118; const l = 42; const r = 8; const t = 14; const b = 18;
    const chart = (key, color, title) => {
      const all = entries.flatMap((id) => c.history[id][key]); const max = Math.max(...all) * 1.05; const min = Math.min(...all) * 0.9;
      const X = (i) => l + (order.length === 1 ? 0 : i / (order.length - 1)) * (W - l - r); const Y = (v) => H - b - (v - min) / Math.max(max - min, 1) * (H - t - b);
      let s = `<svg viewBox="0 0 ${W} ${H}" class="dwg" style="touch-action:auto" role="img" aria-label="${title} estimate by step"><text class="t-cap" x="${l}" y="10">${title}</text>`;
      [min + (max - min) * .2, min + (max - min) * .8].forEach((v) => { s += `<line x1="${l}" x2="${W - r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--hair)"/><text class="t-dim" x="${l - 4}" y="${Y(v) + 3}" text-anchor="end">${Math.round(v / 1000)}k</text>`; });
      const points = [];
      order.forEach((id, i) => {
        s += `<text class="t-dim" x="${X(i)}" y="${H - 5}" text-anchor="middle">${i + 1}</text>`;
        const h = c.history[id]; if (!h) return;
        const [lo, v, hi] = h[key];
        s += `<line x1="${X(i)}" x2="${X(i)}" y1="${Y(lo)}" y2="${Y(hi)}" stroke="${color}" stroke-width="5" stroke-opacity=".28"/>`;
        points.push([X(i), Y(v)]);
      });
      s += `<path d="${points.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ')}" fill="none" stroke="${color}" stroke-width="1.3"/>`;
      points.forEach((p) => { s += `<circle cx="${p[0]}" cy="${p[1]}" r="2.6" fill="${color}"/>`; });
      return `${s}</svg>`;
    };
    void labels;
    return `<div class="ladder">${chart('heat', 'var(--heat2)', 'Heating')}<div style="height:6px"></div>${chart('cool', 'var(--cool2)', 'Cooling')}</div><p class="note" style="margin:5px 0 0">Bars are the range at each step. A shrinking bar means the model is earning its accuracy.</p>`;
  }
  /** What the chosen equipment does against the load, on one axis per season. */
  function fitChart() {
    const c = C(); const r = c.result; const eq = c.eq; const b = c.band; const sys = P().SYSTEMS[P().state.system];
    const rows = [];
    const add = (name, load, low, high, capacity, fitLow, fitHigh, capLabel, color, extra) => rows.push({ name, load, low, high, capacity, fitLow, fitHigh, capLabel, color, extra });
    const heatCap = sys.furnace ? eq.furnace_pct / 100 * r.heating_total : (eq.hp_capacity_at_design || 0);
    const backup = !sys.furnace && eq.installed_aux_kw ? { value: heatCap + eq.installed_aux_kw * 3412.14, label: `With ${fmt(eq.installed_aux_kw)} kW backup` } : null;
    add('Heating', r.heating_total, b ? b.heating_low : r.heating_total, b ? b.heating_high : r.heating_total, heatCap, r.heating_total, r.heating_total * 1.4, sys.furnace ? 'Furnace output' : 'Heat pump at design', 'var(--heat2)', backup);
    add('Cooling', r.cooling_total, b ? b.cooling_low : r.cooling_total, b ? b.cooling_high : r.cooling_total, eq.cooling_capacity_total, r.cooling_total * 0.9, r.cooling_total * (eq.cooling_limit_pct || 115) / 100, sys.hp ? 'Heat pump at design' : 'AC at design', 'var(--cool2)');
    const W = 760; const rowH = 104; const l = 78; const rr = 70; const H = rows.length * rowH + 26;
    const max = Math.max(...rows.flatMap((x) => [x.high, x.capacity, x.fitHigh, x.extra ? x.extra.value : 0])) * 1.06;
    const X = (v) => l + v / max * (W - l - rr);
    let s = `<svg class="dwg" style="touch-action:auto" viewBox="0 0 ${W} ${H}" role="img" aria-label="Load against equipment capacity">`;
    const step = max > 90000 ? 20000 : max > 45000 ? 10000 : 5000;
    for (let v = 0; v <= max; v += step) s += `<line x1="${X(v)}" x2="${X(v)}" y1="8" y2="${H - 18}" stroke="var(--hair)"/><text class="t-dim" x="${X(v)}" y="${H - 6}" text-anchor="middle">${v / 1000}k</text>`;
    rows.forEach((x, i) => {
      const y = 34 + i * rowH;
      s += `<text class="t-cap" x="6" y="${y + 9}">${x.name}</text>`;
      s += `<rect x="${X(x.fitLow)}" y="${y - 8}" width="${X(x.fitHigh) - X(x.fitLow)}" height="30" fill="none" stroke="var(--success)" stroke-width="1" stroke-dasharray="4 3"/><text class="t-num" x="${X(x.fitHigh) + 5}" y="${y + 11}" style="fill:var(--success)">fits</text>`;
      s += `<rect x="${X(x.low)}" y="${y}" width="${Math.max(X(x.high) - X(x.low), 1)}" height="14" fill="${x.color}" fill-opacity=".22"/>`;
      s += `<line x1="${X(x.load)}" x2="${X(x.load)}" y1="${y - 3}" y2="${y + 17}" stroke="${x.color}" stroke-width="2.4"/><text class="t-num" x="${X(x.load)}" y="${y - 13}" text-anchor="middle" style="fill:${x.color};font-weight:700">Load ${fmt(x.load)}</text>`;
      s += `<path d="M${X(x.capacity)} ${y + 16} l-5 9 h10 z" fill="var(--ink)"/><text class="t-num" x="${X(x.capacity)}" y="${y + 40}" text-anchor="${x.extra ? 'end' : 'middle'}" style="fill:var(--ink)">${x.capLabel} ${fmt(x.capacity)}</text>`;
      if (x.extra) {
        // Backup heat is drawn as its own marker, so it is clear what the compressor alone delivers.
        s += `<line x1="${X(x.capacity)}" x2="${X(x.extra.value)}" y1="${y + 21}" y2="${y + 21}" stroke="var(--ink)" stroke-dasharray="3 3"/><path d="M${X(x.extra.value)} ${y + 16} l-5 9 h10 z" fill="none" stroke="var(--ink)"/><text class="t-num" x="${X(x.extra.value)}" y="${y + 40}" text-anchor="start" style="fill:var(--ink)">${x.extra.label} ${fmt(x.extra.value)}</text>`;
      }
    });
    return `${s}</svg>`;
  }
  window.SharedUI = { readouts, ladder, fitChart };
})();
