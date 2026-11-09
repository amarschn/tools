/* Sensitivity study: every point is a full recalculation in the engine. */
(function () {
  'use strict';
  const P = () => window.Proto; const C = () => window.Core;
  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(Number(v))) ? '–' : Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const nice = (v, unit) => {
    const a = Math.abs(v);
    const digits = a >= 100 || Math.abs(v - Math.round(v)) < 0.05 ? 0 : a >= 10 ? 1 : 2;
    return fmt(v, digits) + (unit ? ` ${unit}` : '');
  };
  const TERM_TO_SWEEP = { ach50: 'ach50', wall_u: 'wall_r', ceiling_u: 'ceiling_r', window_pct_of_floor: 'window_scale_pct', window_u: 'window_u', window_shgc: 'window_shgc', duct_leakage_pct: 'duct_leakage_pct', duct_r: 'duct_r', occupants: 'occupants', heating_design_f: 'heating_design_f', cooling_design_f: 'cooling_design_f' };

  const state = { chosen: null, ranges: {}, gridX: null, gridY: null, metric: 'cooling', grid: null };

  function capacities() {
    const eq = C().eq; const sys = P().SYSTEMS[P().state.system];
    const kw = 3412.14;
    const heat = sys.furnace && !sys.hp ? (eq.furnace_pct / 100 * C().result.heating_total)
      : sys.furnace ? (eq.furnace_pct / 100 * C().result.heating_total)
        : (eq.hp_capacity_at_design || 0) + (eq.installed_aux_kw || 0) * kw;
    return { heat, cool: eq.cooling_capacity_total, sizes: P().sizes(C().result), sys };
  }
  function scale(min, max, a, b) { const k = (b - a) / ((max - min) || 1); return (v) => a + (v - min) * k; }
  function ticks(min, max, n = 4) {
    const span = max - min || 1; const raw = span / n; const mag = 10 ** Math.floor(Math.log10(raw));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || raw;
    const out = []; for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(6));
    return out;
  }

  function sweepChart(sweep, range, cap) {
    const W = 420; const H = 236; const l = 54; const r = 64; const t = 14; const b = 38;
    const ys = [...sweep.heating, ...sweep.cooling_total, cap.heat, cap.cool].filter((v) => Number.isFinite(v) && v > 0);
    const yMax = Math.max(...ys) * 1.06; const X = scale(sweep.values[0], sweep.values[sweep.values.length - 1], l, W - r); const Y = scale(0, yMax, H - b, t);
    const line = (series) => sweep.values.map((v, i) => `${i ? 'L' : 'M'}${X(v).toFixed(1)} ${Y(series[i]).toFixed(1)}`).join(' ');
    let s = `<svg class="dwg" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(sweep.label)} against heating and cooling load">`;
    ticks(0, yMax).forEach((v) => { s += `<line x1="${l}" x2="${W - r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--hair)"/><text class="t-dim" x="${l - 5}" y="${Y(v) + 3}" text-anchor="end">${fmt(v / 1000)}k</text>`; });
    ticks(sweep.values[0], sweep.values[sweep.values.length - 1]).forEach((v) => { s += `<line x1="${X(v)}" x2="${X(v)}" y1="${H - b}" y2="${H - b + 4}" stroke="var(--ink3)"/><text class="t-dim" x="${X(v)}" y="${H - b + 15}" text-anchor="middle">${Math.abs(v) >= 10 ? fmt(v) : fmt(v, v % 1 ? 2 : 0)}</text>`; });
    s += `<line x1="${l}" x2="${W - r}" y1="${H - b}" y2="${H - b}" stroke="var(--ink2)"/>`;
    s += `<text class="t-sub" x="${(l + W - r) / 2}" y="${H - 5}" text-anchor="middle">${esc(sweep.label)} (${esc(sweep.unit)})</text>`;
    s += `<text class="t-sub" transform="translate(12,${(t + H - b) / 2}) rotate(-90)" text-anchor="middle">Load (Btu/h)</text>`;
    // Capacity lines
    [[cap.heat, 'var(--heat2)', 'heat'], [cap.cool, 'var(--cool2)', 'cool']].forEach(([value, color]) => {
      if (value > 0 && value < yMax) s += `<line x1="${l}" x2="${W - r}" y1="${Y(value)}" y2="${Y(value)}" stroke="${color}" stroke-width="1" stroke-dasharray="6 4"/>`;
    });
    // Current value
    if (sweep.current >= sweep.values[0] && sweep.current <= sweep.values[sweep.values.length - 1]) {
      s += `<line x1="${X(sweep.current)}" x2="${X(sweep.current)}" y1="${t}" y2="${H - b}" stroke="var(--ink)" stroke-width="1"/><text class="t-dim" x="${X(sweep.current) + 4}" y="${t + 8}" style="fill:var(--ink)">now ${nice(sweep.current)}</text>`;
    }
    s += `<path d="${line(sweep.heating)}" fill="none" stroke="var(--heat2)" stroke-width="1.8"/><path d="${line(sweep.cooling_total)}" fill="none" stroke="var(--cool2)" stroke-width="1.8"/>`;
    const lastH = sweep.heating[sweep.heating.length - 1]; const lastC = sweep.cooling_total[sweep.cooling_total.length - 1];
    let yh = Y(lastH); let yc = Y(lastC);
    if (Math.abs(yh - yc) < 12) { if (yh < yc) { yc = yh + 12; } else { yh = yc + 12; } }
    s += `<text class="t-sub" x="${W - r + 4}" y="${yh + 3}" style="fill:var(--heat2);font-weight:600">Heating</text><text class="t-sub" x="${W - r + 4}" y="${yc + 3}" style="fill:var(--cool2);font-weight:600">Cooling</text>`;
    if (sweep.current >= sweep.values[0] && sweep.current <= sweep.values[sweep.values.length - 1]) {
      s += `<circle cx="${X(sweep.current)}" cy="${Y(sweep.base_heating)}" r="3" fill="var(--heat2)"/><circle cx="${X(sweep.current)}" cy="${Y(sweep.base_cooling)}" r="3" fill="var(--cool2)"/>`;
    }
    return `${s}</svg>`;
  }
  function verdict(sweep, cap) {
    const lines = [];
    const describe = (loads, capacity, name, what) => {
      if (!(capacity > 0)) return;
      const crossings = P().call('threshold_crossings', { values: sweep.values, loads, capacity });
      const first = loads[0] <= capacity; const last = loads[loads.length - 1] <= capacity;
      if (crossings.length) {
        const at = nice(crossings[0], sweep.unit);
        lines.push(first && !last ? `${what} covers ${name} up to ${at}.` : !first && last ? `${what} covers ${name} once this reaches ${at}.` : `${what} changes between covering and missing ${name} near ${at}.`);
      } else if (first) lines.push(`${what} covers ${name} across this whole range.`);
      else lines.push(`${what} falls short on ${name} across this whole range.`);
    };
    const swing = (loads) => (Math.max(...loads) - Math.min(...loads));
    describe(sweep.cooling_total, cap.cool, 'cooling', `A ${cap.sizes.tons} ton ${cap.sys.hp ? 'heat pump' : 'AC'}`);
    describe(sweep.heating, cap.heat, 'heating', cap.sys.furnace ? `A ${fmt(cap.sizes.furnace / 1000)}k furnace` : `The heat pump with ${fmt(C().eq.installed_aux_kw || 0)} kW of backup`);
    const hs = swing(sweep.heating); const cs = swing(sweep.cooling_total);
    return `<p class="sweep-verdict">${lines.map(esc).join(' ')}</p><p class="note" style="margin:0">Across this range: heating moves ${fmt(hs)} Btu/h, cooling moves ${fmt(cs)} Btu/h.</p>`;
  }

  function tornado() {
    const band = C().band; if (!band || !band.terms || !band.terms.length) return '<p class="note">Choose when the house was built to see which unknowns matter most.</p>';
    const r = C().result;
    const terms = band.terms.slice(0, 8);
    const max = Math.max(...terms.flatMap((t) => [Math.abs(t.heat_low), t.heat_high, Math.abs(t.cool_low), t.cool_high]), 1);
    const W = 840; const rowH = 27; const H = terms.length * rowH + 34; const mid = 200; const half = 145; const gap = 310;
    const X = (v, center) => center + v / max * half;
    let s = `<svg class="dwg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Which unknowns move the load most"><text class="t-cap" x="${mid + half / 2 - 40}" y="16" text-anchor="middle" style="fill:var(--heat2)">Heating, Btu/h</text><text class="t-cap" x="${mid + half + gap - 40}" y="16" text-anchor="middle" style="fill:var(--cool2)">Cooling, Btu/h</text>`;
    const c1 = mid + half - 30; const c2 = c1 + gap;
    terms.forEach((t, i) => {
      const y = 26 + i * rowH;
      s += `<text class="t-sub" x="8" y="${y + 13}" style="fill:var(--ink)">${esc(t.label)}${t.known ? ' (entered)' : ''}</text>`;
      [[t.heat_low, t.heat_high, c1, 'var(--heat2)'], [t.cool_low, t.cool_high, c2, 'var(--cool2)']].forEach(([lo, hi, c, color]) => {
        const a = X(lo, c); const b = X(hi, c);
        s += `<line x1="${c - half}" x2="${c + half}" y1="${y + 9}" y2="${y + 9}" stroke="var(--hair)"/><rect x="${a}" y="${y + 3}" width="${Math.max(b - a, 1)}" height="12" fill="${color}" fill-opacity=".75"/><text class="t-dim" x="${b + 4}" y="${y + 13}">${hi > 0.5 ? '+' + fmt(hi) : 'none'}</text>`;
      });
    });
    s += `<line x1="${c1}" x2="${c1}" y1="22" y2="${H - 4}" stroke="var(--ink)"/><line x1="${c2}" x2="${c2}" y1="22" y2="${H - 4}" stroke="var(--ink)"/></svg>`;
    void r;
    return s;
  }

  function gridChart(grid, cap) {
    const values = state.metric === 'heating' ? grid.heating : grid.cooling_total;
    const capacity = state.metric === 'heating' ? cap.heat : cap.cool;
    const color = state.metric === 'heating' ? 'var(--heat2)' : 'var(--cool2)';
    const flat = values.flat(); const lo = Math.min(...flat); const hi = Math.max(...flat);
    const W = 620; const H = 410; const l = 78; const r = 16; const t = 14; const b = 52;
    const cw = (W - l - r) / grid.x.length; const ch = (H - t - b) / grid.y.length;
    let s = `<svg class="dwg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Load across two uncertain variables">
      <defs><pattern id="p-over" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="var(--ink)" stroke-width="1.1"/></pattern></defs>`;
    let covered = 0;
    values.forEach((row, j) => row.forEach((v, i) => {
      const x = l + i * cw; const y = H - b - (j + 1) * ch;
      const mix = Math.round(8 + 62 * (v - lo) / Math.max(hi - lo, 1));
      const short = capacity > 0 && v > capacity;
      if (!short) covered += 1;
      s += `<rect x="${x}" y="${y}" width="${cw - 1}" height="${ch - 1}" fill="color-mix(in srgb, ${color} ${mix}%, var(--paper))"><title>${esc(grid.label_x)} ${nice(grid.x[i])}, ${esc(grid.label_y)} ${nice(grid.y[j])}: ${fmt(v)} Btu/h</title></rect>`;
      if (short) s += `<rect x="${x}" y="${y}" width="${cw - 1}" height="${ch - 1}" fill="url(#p-over)" opacity=".4" pointer-events="none"/>`;
      s += `<text class="t-dim" x="${x + cw / 2}" y="${y + ch / 2 + 3}" text-anchor="middle" pointer-events="none" style="fill:var(--ink)">${fmt(v / 1000, 1)}k</text>`;
    }));
    grid.x.forEach((v, i) => { s += `<text class="t-dim" x="${l + (i + .5) * cw}" y="${H - b + 14}" text-anchor="middle">${nice(v)}</text>`; });
    grid.y.forEach((v, j) => { s += `<text class="t-dim" x="${l - 6}" y="${H - b - (j + .5) * ch + 3}" text-anchor="end">${nice(v)}</text>`; });
    s += `<text class="t-sub" x="${(l + W - r) / 2}" y="${H - 18}" text-anchor="middle">${esc(grid.label_x)} (${esc(grid.unit_x)})</text><text class="t-sub" transform="translate(14,${(t + H - b) / 2}) rotate(-90)" text-anchor="middle">${esc(grid.label_y)} (${esc(grid.unit_y)})</text>`;
    // Where the house is now
    const inX = grid.current_x >= grid.x[0] && grid.current_x <= grid.x[grid.x.length - 1]; const inY = grid.current_y >= grid.y[0] && grid.current_y <= grid.y[grid.y.length - 1];
    if (inX && inY) {
      const px = l + (grid.current_x - grid.x[0]) / (grid.x[grid.x.length - 1] - grid.x[0]) * (W - l - r - cw) + cw / 2;
      const py = H - b - ch / 2 - (grid.current_y - grid.y[0]) / (grid.y[grid.y.length - 1] - grid.y[0]) * (H - t - b - ch);
      s += `<circle cx="${px}" cy="${py}" r="6" fill="none" stroke="var(--ink)" stroke-width="2"/><line x1="${px - 9}" x2="${px + 9}" y1="${py}" y2="${py}" stroke="var(--ink)"/><line x1="${px}" x2="${px}" y1="${py - 9}" y2="${py + 9}" stroke="var(--ink)"/>`;
    }
    const pct = Math.round(100 * covered / flat.length);
    return { svg: `${s}</svg>`, pct, capacity };
  }

  function render(el) {
    const core = C();
    if (!core.result) return;
    const inputs = P().inputs();
    const table = P().call('get_sweep_parameters', { inputs });
    if (!state.chosen) {
      const terms = (core.band && core.band.terms) || [];
      const mapped = terms.map((t) => TERM_TO_SWEEP[t.key]).filter(Boolean);
      state.chosen = [...new Set([...mapped.slice(0, 3), 'ach50', 'duct_leakage_pct'])].slice(0, 4);
      state.gridX = state.chosen[0]; state.gridY = state.chosen[1] || 'duct_leakage_pct';
    }
    const cap = capacities();
    const chips = Object.entries(table).map(([k, v]) => `<button type="button" class="chip ${state.chosen.includes(k) ? 'on' : ''}" data-chip="${k}" aria-pressed="${state.chosen.includes(k)}">${esc(v.label)}</button>`).join('');
    const options = Object.entries(table).map(([k, v]) => [k, v.label]);
    const sel = (id, value) => `<select id="${id}" data-grid="${id}">${options.map(([k, t]) => `<option value="${k}"${k === value ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select>`;
    const cards = state.chosen.map((k) => {
      const spec = table[k]; const range = state.ranges[k] || { low: spec.low, high: spec.high };
      let body;
      try {
        const sweep = P().call('sensitivity_sweep', { inputs, parameter: k, low: range.low, high: range.high, points: 11 });
        body = sweepChart(sweep, range, cap) + verdict(sweep, cap);
      } catch (e) { body = `<p class="note">${esc(String(e.message || e).trim().split('\n').pop())}</p>`; }
      return `<article class="sweep"><header><strong>${esc(spec.label)}</strong><span class="note">${esc(spec.about)}</span></header>
        <div class="range-row"><label>From <input type="number" step="any" value="${+range.low.toFixed(3)}" data-range="${k}:low" aria-label="${esc(spec.label)} low"></label><label>to <input type="number" step="any" value="${+range.high.toFixed(3)}" data-range="${k}:high" aria-label="${esc(spec.label)} high"></label><span class="note">${esc(spec.unit)}</span></div>${body}</article>`;
    }).join('');
    el.innerHTML = `
      <section class="study-part"><h3>Which unknowns matter most</h3><p class="note">Each bar reruns the whole house with one input at the ends of its likely range. The shorter you can make a bar, by measuring or confirming that input, the narrower your answer gets.</p>${tornado()}</section>
      <section class="study-part"><h3>Sweep the variables you are unsure about</h3><p class="note">Choose any of these. Dashed lines are the capacity of the equipment you chose on the previous step, so you can see where it stops covering the load.</p><div class="chips">${chips}</div><div class="sweeps">${cards}</div></section>
      <section class="study-part"><h3>Two unknowns at once</h3><p class="note">Some effects compound, which single sweeps miss. Hatched cells are where the equipment falls short.</p>
        <div class="range-row"><label>Across ${sel('gridX', state.gridX)}</label><label>Up ${sel('gridY', state.gridY)}</label><div class="dwg-tabs" role="group" aria-label="Metric"><button type="button" data-metric="cooling" class="${state.metric === 'cooling' ? 'on' : ''}">Cooling</button><button type="button" data-metric="heating" class="${state.metric === 'heating' ? 'on' : ''}">Heating</button></div><button type="button" class="btn" id="grid-run">Run 49 calculations</button></div>
        <div id="grid-out"><p class="note">Press run to calculate the grid.</p></div></section>`;
    renderGrid(el);
  }
  function renderGrid(el) {
    const out = el.querySelector('#grid-out');
    if (!state.grid || !out) return;
    const cap = capacities();
    const chart = gridChart(state.grid, cap);
    out.innerHTML = `${chart.svg}<p class="sweep-verdict">${chart.capacity > 0 ? `Your ${state.metric === 'heating' ? 'heating equipment' : (cap.sys.hp ? 'heat pump' : 'AC')} covers ${chart.pct}% of this grid. The cross marks the house as entered.` : ''}</p>`;
  }
  function bind(el) {
    el.addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.chip) {
        const k = b.dataset.chip; const i = state.chosen.indexOf(k);
        if (i >= 0) { if (state.chosen.length > 1) state.chosen.splice(i, 1); } else state.chosen.push(k);
        render(el);
      }
      if (b.dataset.metric) { state.metric = b.dataset.metric; render(el); }
      if (b.id === 'grid-run') {
        const out = el.querySelector('#grid-out'); out.innerHTML = '<p class="note">Calculating...</p>';
        setTimeout(() => {
          try {
            const inputs = P().inputs(); const table = P().call('get_sweep_parameters', { inputs });
            const rx = state.ranges[state.gridX] || table[state.gridX]; const ry = state.ranges[state.gridY] || table[state.gridY];
            state.grid = P().call('sensitivity_grid', { inputs, parameter_x: state.gridX, parameter_y: state.gridY, low_x: rx.low, high_x: rx.high, low_y: ry.low, high_y: ry.high, points: 7 });
            renderGrid(el);
          } catch (err) { out.innerHTML = `<p class="note">${esc(String(err.message || err).trim().split('\n').pop())}</p>`; }
        }, 20);
      }
    });
    el.addEventListener('change', (e) => {
      const t = e.target;
      if (t.dataset.range) {
        const [k, side] = t.dataset.range.split(':');
        const table = P().call('get_sweep_parameters', { inputs: P().inputs() });
        const current = state.ranges[k] || { low: table[k].low, high: table[k].high };
        const next = { ...current, [side]: Number(t.value) };
        if (next.high > next.low) state.ranges[k] = next;
        render(el);
      }
      if (t.dataset.grid) { state[t.dataset.grid] = t.value; state.grid = null; if (state.gridX === state.gridY) { state.gridY = Object.keys(P().call('get_sweep_parameters', { inputs: P().inputs() })).find((k) => k !== state.gridX); } render(el); }
    });
  }
  window.Study = { render, bind, state };
})();
