/* Data model for the Ashby chart. Works in the browser and in Node tests.
   Pairing rules live in pycalcs/material_selection.py: the build publishes a table of
   compatible rows, and every view here reads that table. This file holds no pairing logic. */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.AshbyEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const FAMILY_COLORS = {
    metal: '#4e79a7', polymer: '#e15759', ceramic: '#3f9d97', composite: '#f28e2b', wood: '#72964b',
    foam: '#9c755f', elastomer: '#bd66a0', glass: '#8875c4', concrete: '#6f7782', fiber: '#c9a227',
  };
  const FAMILY_NAMES = {
    metal: 'Metals', polymer: 'Polymers', ceramic: 'Ceramics', composite: 'Composites', wood: 'Wood',
    foam: 'Foams', elastomer: 'Elastomers', glass: 'Glasses', concrete: 'Concrete', fiber: 'Fibers',
  };
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  function formatValue(v) {
    if (!Number.isFinite(v)) return '–';
    const a = Math.abs(v);
    if (a !== 0 && (a >= 1e6 || a < 1e-3)) return v.toExponential(1).replace('e+', 'e');
    return a >= 100 ? Math.round(v).toLocaleString('en-US') : +v.toPrecision(3) + '';
  }

  class Database {
    constructor(core) {
      this.core = core;
      this.props = core.properties;
      this.propIndex = new Map(this.props.map((p, i) => [p.id, i]));
      // No prototype, so a typed name such as "constructor" is not mistaken for a property.
      this.bySym = Object.assign(Object.create(null), Object.fromEntries(this.props.map((p, i) => [p.symbol, { ...p, index: i }])));
      this.indices = core.indices;
      const o = core.observations, n = o.value.length;
      this.obsCount = n;
      this.obsMaterial = Int32Array.from(o.material);
      this.obsState = Int32Array.from(o.state);
      this.obsProp = Int32Array.from(o.property);
      this.obsKind = Uint8Array.from(o.kind);
      this.obsBasis = Uint8Array.from(o.basis);
      this.obsOrg = Int32Array.from(o.organization);
      this.si = Float64Array.from(o.value);
      this.display = new Float64Array(n);
      this.minimum = new Float64Array(n);
      this.maximum = new Float64Array(n);
      this.temperature = new Float64Array(n);
      for (let i = 0; i < n; i++) {
        const k = this.props[this.obsProp[i]].display_multiplier;
        this.display[i] = o.value[i] * k;
        this.minimum[i] = o.minimum[i] == null ? NaN : o.minimum[i] * k;
        this.maximum[i] = o.maximum[i] == null ? NaN : o.maximum[i] * k;
        this.temperature[i] = o.temperature[i] == null ? NaN : o.temperature[i];
      }
      this.materials = core.materials.map(([id, name, family, sub_family, group, search], i) => ({ i, id, name, family, sub_family, group, search }));
      this.byId = Object.assign(Object.create(null), Object.fromEntries(this.materials.map(m => [m.id, m])));
      this.states = core.states.map(([id, name]) => ({ id, name }));
      this.organizations = core.organizations;
      const lower = core.kinds.indexOf('lower_bound'), upper = core.kinds.indexOf('upper_bound');
      this.boundKinds = new Set([lower, upper]);
      this.intervalKind = core.kinds.indexOf('interval');
      [this.ambientLow, this.ambientHigh] = core.ambient_temperature_K;
      this.rows = core.rows.map((list, i) => {
        const obs = new Int32Array(this.props.length).fill(-1);
        for (const item of list) obs[this.obsProp[item]] = item;
        return { i, m: this.materials[this.obsMaterial[list[0]]], obs, list };
      });
      this.rowsByMaterial = new Map();
      for (const row of this.rows) {
        if (!this.rowsByMaterial.has(row.m.id)) this.rowsByMaterial.set(row.m.id, []);
        this.rowsByMaterial.get(row.m.id).push(row);
      }
    }
    isBound(o) { return this.boundKinds.has(this.obsKind[o]); }
    isInterval(o) { return this.obsKind[o] === this.intervalKind; }
    isAmbient(o) { const t = this.temperature[o]; return Number.isNaN(t) || (t >= this.ambientLow && t <= this.ambientHigh); }
    kindName(o) { return this.core.kinds[this.obsKind[o]]; }
    basisName(o) { return this.core.bases[this.obsBasis[o]]; }
    organization(o) { return this.organizations[this.obsOrg[o]]; }
    stateName(index) { return index >= 0 ? this.states[index].name : null; }
    propertyOf(o) { return this.props[this.obsProp[o]]; }
    /* Value text with its reported meaning, so a bound never reads as a measurement. */
    resultText(o, format = formatValue) {
      const unit = this.propertyOf(o).display_unit, tail = unit ? ' ' + unit : '';
      if (this.isInterval(o)) return `${format(this.minimum[o])} to ${format(this.maximum[o])}${tail}`;
      const sign = { lower_bound: '≥ ', upper_bound: '≤ ' }[this.kindName(o)] || '';
      return sign + format(this.display[o]) + tail;
    }
    /* Group rows into distinct points on the given axes. Two rows that hold the same
       observations for these properties are one point on this chart. */
    points(rows, axes, allow) {
      const needed = [...new Set(axes.flatMap(axis => axis.used))].sort((a, b) => a - b);
      const groups = new Map();
      for (const row of rows) {
        const list = [];
        let usable = needed.length > 0;
        for (const p of needed) {
          const o = row.obs[p];
          if (o < 0 || (allow && !allow(o))) { usable = false; break; }
          list.push(o);
        }
        if (!usable) continue;
        const key = list.join(':');
        let point = groups.get(key);
        if (!point) {
          let state = -1;
          for (const o of list) if (this.obsState[o] >= 0) { state = this.obsState[o]; break; }
          const temps = [...new Set(list.map(o => this.temperature[o]).filter(t => !Number.isNaN(t)))].sort((a, b) => a - b);
          point = {
            key, m: row.m, obs: list, row, rows: [], stateIndex: state,
            temperatures_K: temps, hasBounds: list.some(o => this.isBound(o)),
          };
          groups.set(key, point);
        }
        point.rows.push(row);
      }
      return [...groups.values()];
    }
    /* Index value from exponents the build measured off the Python formula, in SI. */
    score(index, row, allow) {
      if (!index.exponents) return NaN;
      let value = 1;
      for (const [id, power] of Object.entries(index.exponents)) {
        const o = row.obs[this.propIndex.get(id)];
        if (o === undefined || o < 0 || (allow && !allow(o))) return NaN;
        value *= Math.pow(this.si[o], power);
      }
      return value;
    }
  }

  /* Formula axes: a small parser, so typed text is never run as code. */
  function compile(db, text) {
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
      if (t === '-') { const inner = power(); return get => -inner(get); }
      if (/^[\d.]/.test(t)) { const n = parseFloat(t); return () => n; }
      if (db.bySym[t]) { const p = db.bySym[t].index; used.add(p); return get => get(p); }
      throw new Error(`Unknown property "${t}"`);
    }
    function power() { const base = primary(); if (peek() === '^') { at++; const exp = power(); return get => Math.pow(base(get), exp(get)); } return base; }
    function product() { let left = power(); while (peek() === '*' || peek() === '/') { const op = list[at++]; const a = left, b = power(); left = op === '*' ? get => a(get) * b(get) : get => a(get) / b(get); } return left; }
    function sum() { let left = product(); while (peek() === '+' || peek() === '-') { const op = list[at++]; const a = left, b = product(); left = op === '+' ? get => a(get) + b(get) : get => a(get) - b(get); } return left; }
    try {
      const fn = sum();
      if (at !== list.length) throw new Error(`Unexpected "${list[at]}"`);
      if (!used.size) throw new Error('Include at least one property');
      return { fn, used: [...used], source };
    } catch (error) { return { error: error.message }; }
  }

  class Axis {
    constructor(db, expr, log = true) {
      this.db = db; this.expr = expr; this.log = log;
      this.compiled = compile(db, expr);
      this.prop = db.bySym[expr] || null;
      this.used = this.compiled.used || [];
    }
    get ok() { return !this.compiled.error; }
    /* Read a row at display units. A missing or filtered observation gives NaN. */
    value(row, allow) {
      if (!this.ok) return NaN;
      const v = this.compiled.fn(p => {
        const o = row.obs[p];
        return o < 0 || (allow && !allow(o)) ? NaN : this.db.display[o];
      });
      return Number.isFinite(v) && (!this.log || v > 0) ? v : NaN;
    }
    /* Reported interval on this axis, when the axis is one plain property. */
    interval(row) {
      if (!this.prop) return null;
      const o = row.obs[this.prop.index];
      return o >= 0 && this.db.isInterval(o) ? [this.db.minimum[o], this.db.maximum[o]] : null;
    }
    observation(row) { return this.prop ? row.obs[this.prop.index] : -1; }
    get pretty() { return this.expr.replace(/rho/g, 'ρ').replace(/\*/g, '·'); }
    get label() { const p = this.prop; return p ? (p.display_unit ? `${p.label} (${p.display_unit})` : p.label) : `${this.pretty} (display units)`; }
    get short() { return this.prop ? this.prop.label : this.pretty; }
    get tag() { return this.prop ? this.prop.symbol.replace('rho', 'ρ') : this.pretty; }
    t(v) { return this.log ? Math.log10(v) : v; }
    inv(t) { return this.log ? 10 ** t : t; }
  }

  /* Filter stages test rows, so every limit reads values that are compatible with each other. */
  function stageTest(db, stage, ctx = {}) {
    const allow = ctx.allow;
    switch (stage.type) {
      case 'family': { const set = new Set(stage.values); return row => set.has(row.m.family); }
      case 'class': { const set = new Set(stage.values); return row => set.has(row.m.group); }
      case 'org': { const set = new Set(stage.values); return row => row.list.some(o => set.has(db.organization(o))); }
      case 'text': { const q = String(stage.value || '').toLowerCase().trim(); return row => !q || row.m.search.includes(q); }
      case 'tag': return row => !!ctx.hasTag?.(stage.value, row.m.id);
      case 'limit': {
        const axis = new Axis(db, stage.expr, false);
        return row => {
          const v = axis.value(row, allow);
          return Number.isFinite(v) && (stage.min == null || v >= stage.min) && (stage.max == null || v <= stage.max);
        };
      }
      case 'region': {
        const ax = new Axis(db, stage.x, stage.xLog), ay = new Axis(db, stage.y, stage.yLog);
        return row => {
          const x = ax.value(row, allow), y = ay.value(row, allow);
          return Number.isFinite(x) && Number.isFinite(y) && x >= stage.x0 && x <= stage.x1 && y >= stage.y0 && y <= stage.y1;
        };
      }
      case 'index': {
        const ax = new Axis(db, stage.x), ay = new Axis(db, stage.y);
        return row => {
          const x = ax.value(row, allow), y = ay.value(row, allow);
          if (!Number.isFinite(x) || !Number.isFinite(y)) return false;
          const c = Math.log10(y) - stage.slope * Math.log10(x);
          return stage.above ? c >= stage.c : c <= stage.c;
        };
      }
      default: return () => true;
    }
  }
  const countMaterials = rows => { const seen = new Set(); for (const r of rows) seen.add(r.m.i); return seen.size; };
  function runStages(db, stages, rows, ctx = {}) {
    let current = rows;
    const counts = [];
    for (const stage of stages) {
      const before = countMaterials(current);
      if (stage.enabled !== false) { const test = stageTest(db, stage, ctx); current = current.filter(test); }
      counts.push({ before, after: countMaterials(current) });
    }
    return { rows: current, counts, materials: countMaterials(current) };
  }

  /* Typed filters become ordinary stages: "E > 5", "UTS < 300 MPa", "family metal", "tag shortlist". */
  const STRESS_UNITS = { pa: 1e-6, kpa: 1e-3, mpa: 1, gpa: 1e3 };
  function parseQuery(db, text) {
    const q = String(text).trim();
    let m;
    if ((m = q.match(/^family\s+(.+)$/i))) {
      const wanted = m[1].split(/[, ]+/).map(w => w.toLowerCase()).map(w => Object.keys(FAMILY_NAMES).find(k => k === w || FAMILY_NAMES[k].toLowerCase() === w || k.startsWith(w)));
      if (wanted.includes(undefined)) throw new Error('Families: ' + Object.values(FAMILY_NAMES).join(', '));
      return { type: 'family', values: wanted, enabled: true };
    }
    if ((m = q.match(/^tag\s+(.+)$/i))) return { type: 'tag', value: m[1].trim(), enabled: true };
    if ((m = q.match(/^(?:class|type)\s+(.+)$/i))) {
      const need = m[1].toLowerCase();
      const values = [...new Set(db.materials.map(x => x.group))].filter(c => c.toLowerCase().includes(need));
      if (!values.length) throw new Error(`No class matches "${m[1]}"`);
      return { type: 'class', values, enabled: true };
    }
    if ((m = q.match(/^(.+?)\s*(<=|>=|<|>)\s*(-?[\d.]+)\s*(\S*)$/))) {
      const compiled = compile(db, m[1]);
      if (compiled.error) throw new Error(compiled.error + '. Symbols: ' + db.props.map(p => p.symbol).join(', '));
      let value = parseFloat(m[3]);
      if (m[4]) {
        // Convert stresses, and refuse any other unit rather than quietly reading the number wrong.
        const prop = db.bySym[m[1].trim()], given = m[4].toLowerCase(), own = prop?.display_unit.toLowerCase();
        if (!prop) throw new Error('Leave the unit off a formula');
        if (given !== own) {
          if (!(given in STRESS_UNITS && own in STRESS_UNITS)) throw new Error(`${prop.symbol} is in ${prop.display_unit || 'no unit'}`);
          value = value * STRESS_UNITS[given] / STRESS_UNITS[own];
        }
      }
      return { type: 'limit', expr: m[1].trim(), min: m[2].includes('>') ? value : null, max: m[2].includes('<') ? value : null, enabled: true };
    }
    if (q) return { type: 'text', value: q, enabled: true };
    throw new Error('Type a filter');
  }

  return { Database, Axis, compile, stageTest, runStages, parseQuery, formatValue, clamp, FAMILY_COLORS, FAMILY_NAMES };
});
