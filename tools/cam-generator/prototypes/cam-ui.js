/*
 * cam-ui.js: shared UI for the cam generator prototypes.
 *   CamUI.initPage(key)      navbar, theme toggle, page links
 *   CamUI.LineChart          SVG line chart with crosshair tooltip and drag points
 *   CamUI.CamView            animated cam + follower drawing
 *   CamUI.SegmentEditor      compact rise/fall/dwell editor
 *   CamUI.saveDesign / loadDesign / buildMotion   hand a design between pages
 */
(function (global) {
  'use strict';

  const C = global.CamCore;
  const SETTINGS_KEY = 'cam-prototypes-settings';
  const DESIGN_KEY = 'cam-prototypes-design';

  const PAGES = [
    { key: 'index', title: 'Gallery', href: 'index.html' },
    { key: 'sketch', title: 'A · Motion sketch', href: 'a-motion-sketch.html' },
    { key: 'bench', title: 'B · Workbench', href: 'b-workbench.html' },
    { key: 'space', title: 'C · Sizing map', href: 'c-design-space.html' },
    { key: 'timing', title: 'D · Machine timing', href: 'd-timing.html' },
    { key: 'dyn', title: 'E · Spring & torque', href: 'e-dynamics.html' },
    { key: 'laws', title: 'F · Law lab', href: 'f-law-lab.html' },
    { key: 'make', title: 'G · Make it', href: 'g-make-it.html' },
  ];

  // ---------------------------------------------------------------------------
  // Storage (wrapped: private windows and blocked storage must not break pages)
  // ---------------------------------------------------------------------------
  function readJSON(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }
  function writeJSON(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      /* storage unavailable */
    }
  }

  // ---------------------------------------------------------------------------
  // Page shell
  // ---------------------------------------------------------------------------
  function initPage(key) {
    const settings = readJSON(SETTINGS_KEY, { theme: 'system' });
    document.body.dataset.theme = settings.theme || 'system';
    const nav = document.getElementById('nav');
    if (nav) {
      const page = PAGES.find((p) => p.key === key);
      nav.className = 'navbar';
      nav.innerHTML = `
        <div class="nav-left">
          <a class="nav-brand" href="../">Cam Generator</a>
          <span class="nav-crumb">Prototypes${page && key !== 'index' ? ' / ' + page.title : ''}</span>
        </div>
        <nav class="nav-pages" aria-label="Prototype pages">
          ${PAGES.map((p) => `<a href="${p.href}" class="${p.key === key ? 'current' : ''}">${p.title}</a>`).join('')}
        </nav>
        <div class="nav-right">
          <button class="btn small" id="theme-btn" type="button" title="Theme"></button>
        </div>`;
      const btn = nav.querySelector('#theme-btn');
      const label = () => {
        btn.textContent = { system: 'Theme: auto', light: 'Theme: light', dark: 'Theme: dark' }[document.body.dataset.theme];
      };
      label();
      btn.addEventListener('click', () => {
        const order = ['system', 'light', 'dark'];
        const next = order[(order.indexOf(document.body.dataset.theme) + 1) % 3];
        document.body.dataset.theme = next;
        writeJSON(SETTINGS_KEY, { ...settings, theme: next });
        label();
        document.dispatchEvent(new CustomEvent('themechange'));
      });
    }
    if (!document.querySelector('.toast')) {
      const t = document.createElement('div');
      t.className = 'toast';
      t.setAttribute('role', 'status');
      document.body.appendChild(t);
    }
  }

  function toast(msg) {
    const t = document.querySelector('.toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove('show'), 1800);
  }

  function download(filename, text, mime = 'text/plain') {
    const blob = new Blob([text], { type: mime });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 0);
  }

  // ---------------------------------------------------------------------------
  // Formatting
  // ---------------------------------------------------------------------------
  function fmt(x, digits = 3) {
    if (!Number.isFinite(x)) return x > 0 ? '∞' : '–';
    const ax = Math.abs(x);
    if (ax !== 0 && (ax >= 1e5 || ax < 1e-3)) return x.toExponential(2);
    const d = ax >= 100 ? 0 : ax >= 10 ? 1 : ax >= 1 ? 2 : digits;
    return x.toFixed(Math.max(0, Math.min(d, digits)));
  }

  function niceStep(span, count) {
    const raw = span / Math.max(1, count);
    const mag = 10 ** Math.floor(Math.log10(raw));
    const n = raw / mag;
    return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
  }

  function niceTicks(lo, hi, count = 4) {
    if (!(hi > lo)) {
      hi = lo + 1;
    }
    const step = niceStep(hi - lo, count);
    const start = Math.ceil(lo / step - 1e-9) * step;
    const ticks = [];
    for (let v = start; v <= hi + step * 1e-6; v += step) ticks.push(Math.abs(v) < step * 1e-9 ? 0 : v);
    return { ticks, step, lo: Math.floor(lo / step + 1e-9) * step, hi: Math.ceil(hi / step - 1e-9) * step };
  }

  function cssVar(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
  }

  // ---------------------------------------------------------------------------
  // LineChart
  // ---------------------------------------------------------------------------
  class LineChart {
    constructor(el, opts = {}) {
      this.el = typeof el === 'string' ? document.getElementById(el) : el;
      this.el.classList.add('chart');
      this.o = Object.assign(
        {
          height: 150,
          xDomain: [0, 360],
          xTicks: [0, 60, 120, 180, 240, 300, 360],
          xLabel: 'Cam angle (°)',
          xFormat: (x) => `${x.toFixed(1)}°`,
          xTickFormat: (x) => `${Math.round(x)}°`,
          yTickFormat: null,
          yLabel: '',
          yFormat: (y) => fmt(y),
          pad: { l: 54, r: 14, t: 10, b: 26 },
          showXAxis: true,
          includeZero: true,
          tooltip: true,
        },
        opts,
      );
      this.data = { series: [] };
      this.cursorX = null;
      this.tip = document.createElement('div');
      this.tip.className = 'chart-tip';
      this.tip.hidden = true;
      this.el.appendChild(this.tip);
      this.svgHost = document.createElement('div');
      this.el.insertBefore(this.svgHost, this.tip);
      this._bind();
      if (global.ResizeObserver) {
        let w = 0;
        new ResizeObserver(() => {
          if (this.el.clientWidth !== w) {
            w = this.el.clientWidth;
            this.render();
          }
        }).observe(this.el);
      }
      document.addEventListener('themechange', () => this.render());
    }

    setData(d) {
      this.data = d;
      this.render();
    }

    get width() {
      return Math.max(240, this.el.clientWidth || 600);
    }

    _domain() {
      const d = this.data;
      let lo = Infinity;
      let hi = -Infinity;
      if (d.yDomain) [lo, hi] = d.yDomain;
      else {
        (d.series || []).forEach((s) => {
          if (s.hidden) return;
          for (let i = 0; i < s.y.length; i++) {
            const v = s.y[i];
            if (Number.isFinite(v)) {
              lo = Math.min(lo, v);
              hi = Math.max(hi, v);
            }
          }
        });
        (d.points || []).forEach((p) => {
          lo = Math.min(lo, p.y);
          hi = Math.max(hi, p.y);
        });
        (d.hlines || []).forEach((h) => {
          if (h.fit !== false) {
            lo = Math.min(lo, h.y);
            hi = Math.max(hi, h.y);
          }
        });
        if (this.o.includeZero) {
          lo = Math.min(lo, 0);
          hi = Math.max(hi, 0);
        }
        if (!Number.isFinite(lo)) {
          lo = 0;
          hi = 1;
        }
        if (hi - lo < 1e-12) {
          hi = lo + 1;
        }
        const padY = (hi - lo) * 0.08;
        if (!(this.o.includeZero && lo === 0)) lo -= padY;
        hi += padY;
      }
      const t = niceTicks(lo, hi, this.o.height < 130 ? 3 : 4);
      if (!d.yDomain) {
        lo = Math.min(lo, t.lo);
        hi = Math.max(hi, t.hi);
      }
      return { lo, hi, step: t.step, ticks: t.ticks.filter((v) => v >= lo - 1e-9 && v <= hi + 1e-9) };
    }

    xToPx(x) {
      const { l, r } = this.o.pad;
      const [a, b] = this.o.xDomain;
      return l + ((x - a) / (b - a)) * (this.width - l - r);
    }
    pxToX(px) {
      const { l, r } = this.o.pad;
      const [a, b] = this.o.xDomain;
      return a + ((px - l) / (this.width - l - r)) * (b - a);
    }
    yToPx(y) {
      const { t, b } = this.o.pad;
      const h = this.o.height - t - b;
      return t + (1 - (y - this.ylo) / (this.yhi - this.ylo)) * h;
    }
    pxToY(py) {
      const { t, b } = this.o.pad;
      const h = this.o.height - t - b;
      return this.ylo + (1 - (py - t) / h) * (this.yhi - this.ylo);
    }

    render() {
      const o = this.o;
      const d = this.data;
      const W = this.width;
      const H = o.height;
      const { l, r, t, b } = o.pad;
      const dom = this._domain();
      this.ylo = dom.lo;
      this.yhi = dom.hi;
      const parts = [];
      parts.push(`<svg viewBox="0 0 ${W} ${H}" height="${H}" role="img" aria-label="${o.yLabel || 'chart'}">`);
      // bands
      (d.bands || []).forEach((bd) => {
        const x0 = this.xToPx(bd.x0);
        const x1 = this.xToPx(bd.x1);
        const y0 = bd.y0 !== undefined ? this.yToPx(bd.y1) : t;
        const y1 = bd.y0 !== undefined ? this.yToPx(bd.y0) : H - b;
        parts.push(`<rect x="${x0}" y="${y0}" width="${Math.max(0, x1 - x0)}" height="${Math.max(0, y1 - y0)}" style="fill:${bd.fill || 'var(--primary-light)'};opacity:${bd.opacity ?? 1}"></rect>`);
        if (bd.label) parts.push(`<text class="label" x="${(x0 + x1) / 2}" y="${t + 11}" text-anchor="middle">${bd.label}</text>`);
      });
      // grid
      parts.push('<g class="grid">');
      dom.ticks.forEach((v) => parts.push(`<line x1="${l}" x2="${W - r}" y1="${this.yToPx(v)}" y2="${this.yToPx(v)}"></line>`));
      o.xTicks.forEach((x) => parts.push(`<line x1="${this.xToPx(x)}" x2="${this.xToPx(x)}" y1="${t}" y2="${H - b}"></line>`));
      parts.push('</g>');
      if (dom.lo < 0 && dom.hi > 0) parts.push(`<line class="zero" x1="${l}" x2="${W - r}" y1="${this.yToPx(0)}" y2="${this.yToPx(0)}"></line>`);
      // axes
      parts.push('<g class="axis">');
      const dec = Math.max(0, Math.min(4, -Math.floor(Math.log10(dom.step) + 1e-9)));
      const big = Math.max(Math.abs(dom.lo), Math.abs(dom.hi)) >= 1e5;
      const yTick = o.yTickFormat || ((v) => (big ? v.toExponential(1) : v.toFixed(dec)));
      dom.ticks.forEach((v) => parts.push(`<text x="${l - 6}" y="${this.yToPx(v) + 3.5}" text-anchor="end">${yTick(v)}</text>`));
      if (o.showXAxis) o.xTicks.forEach((x) => parts.push(`<text x="${this.xToPx(x)}" y="${H - b + 15}" text-anchor="middle">${o.xTickFormat(x)}</text>`));
      parts.push('</g>');
      if (o.yLabel) parts.push(`<text class="axis-title" transform="translate(11 ${t + (H - t - b) / 2}) rotate(-90)" text-anchor="middle">${o.yLabel}</text>`);
      // hlines
      (d.hlines || []).forEach((h) => {
        const y = this.yToPx(h.y);
        parts.push(`<line x1="${l}" x2="${W - r}" y1="${y}" y2="${y}" style="stroke:${h.color || 'var(--text-light)'};stroke-width:1;stroke-dasharray:${h.dash || '5 4'}"></line>`);
        if (h.label) parts.push(`<text class="label" x="${W - r - 4}" y="${y - 4}" text-anchor="end">${h.label}</text>`);
      });
      // series
      parts.push(`<clipPath id="clip-${this._id()}"><rect x="${l}" y="${t - 2}" width="${W - l - r}" height="${H - t - b + 4}"></rect></clipPath>`);
      parts.push(`<g clip-path="url(#clip-${this._id()})">`);
      (d.series || []).forEach((s) => {
        if (s.hidden) return;
        let path = '';
        let pen = false;
        const step = Math.max(1, Math.floor(s.x.length / (W * 1.5)));
        for (let i = 0; i < s.x.length; i += i + step >= s.x.length && i !== s.x.length - 1 ? s.x.length - 1 - i : step) {
          const v = s.y[i];
          if (!Number.isFinite(v)) {
            pen = false;
            continue;
          }
          const yy = Math.max(-1e5, Math.min(1e5, this.yToPx(v)));
          path += `${pen ? 'L' : 'M'}${this.xToPx(s.x[i]).toFixed(1)},${yy.toFixed(1)}`;
          pen = true;
        }
        if (s.fill) {
          const y0 = this.yToPx(Math.max(dom.lo, Math.min(dom.hi, 0)));
          parts.push(`<path d="${path}L${this.xToPx(s.x[s.x.length - 1])},${y0}L${this.xToPx(s.x[0])},${y0}Z" style="fill:${s.fill};opacity:${s.fillOpacity ?? 0.12};stroke:none"></path>`);
        }
        parts.push(`<path d="${path}" style="fill:none;stroke:${s.color || 'var(--series-1)'};stroke-width:${s.width || 2};stroke-linejoin:round;stroke-linecap:round;${s.dash ? `stroke-dasharray:${s.dash};` : ''}opacity:${s.opacity ?? 1}"></path>`);
      });
      parts.push('</g>');
      // markers / drag points
      (d.points || []).forEach((p) => {
        const x = this.xToPx(p.x);
        const y = this.yToPx(p.y);
        const rr = p.r || 6;
        const fill = p.fill || 'var(--bg-card)';
        const stroke = p.stroke || 'var(--text-color)';
        if (p.shape === 'square') parts.push(`<rect class="pt" data-id="${p.id ?? ''}" x="${x - rr}" y="${y - rr}" width="${2 * rr}" height="${2 * rr}" rx="2" style="fill:${fill};stroke:${stroke};stroke-width:2;cursor:${p.cursor || 'grab'}"></rect>`);
        else if (p.shape === 'diamond') parts.push(`<path class="pt" data-id="${p.id ?? ''}" d="M${x},${y - rr * 1.2}L${x + rr * 1.2},${y}L${x},${y + rr * 1.2}L${x - rr * 1.2},${y}Z" style="fill:${fill};stroke:${stroke};stroke-width:2;cursor:${p.cursor || 'grab'}"></path>`);
        else parts.push(`<circle class="pt" data-id="${p.id ?? ''}" cx="${x}" cy="${y}" r="${rr}" style="fill:${fill};stroke:${stroke};stroke-width:2;cursor:${p.cursor || 'grab'}"></circle>`);
        // generous invisible hit target
        parts.push(`<circle class="pt hit" data-id="${p.id ?? ''}" cx="${x}" cy="${y}" r="${rr + 8}" style="fill:transparent;cursor:${p.cursor || 'grab'}"></circle>`);
        if (p.label) parts.push(`<text class="label" x="${x}" y="${y - rr - 6}" text-anchor="middle">${p.label}</text>`);
      });
      parts.push(`<line class="crosshair" x1="0" x2="0" y1="${t}" y2="${H - b}" visibility="hidden"></line>`);
      parts.push(`<line class="cursor" x1="0" x2="0" y1="${t}" y2="${H - b}" visibility="hidden"></line>`);
      parts.push(`<rect class="frame" x="${l}" y="${t}" width="${W - l - r}" height="${H - t - b}"></rect>`);
      parts.push('</svg>');
      this.svgHost.innerHTML = parts.join('');
      this.svg = this.svgHost.firstChild;
      this.cross = this.svg.querySelector('.crosshair');
      this.cursorEl = this.svg.querySelector('.cursor');
      this.setCursor(this.cursorX);
    }

    _id() {
      if (!this.__id) this.__id = Math.random().toString(36).slice(2, 8);
      return this.__id;
    }

    setCursor(x) {
      this.cursorX = x;
      if (!this.cursorEl) return;
      if (x === null || x === undefined) {
        this.cursorEl.setAttribute('visibility', 'hidden');
        return;
      }
      const px = this.xToPx(x);
      this.cursorEl.setAttribute('x1', px);
      this.cursorEl.setAttribute('x2', px);
      this.cursorEl.setAttribute('visibility', 'visible');
    }

    _local(evt) {
      const rect = this.svg.getBoundingClientRect();
      const sx = this.width / rect.width;
      return [(evt.clientX - rect.left) * sx, (evt.clientY - rect.top) * sx];
    }

    _bind() {
      const host = this.el;
      host.addEventListener('pointermove', (evt) => {
        if (!this.svg) return;
        const [px, py] = this._local(evt);
        const { l, r, t, b } = this.o.pad;
        const inside = px >= l && px <= this.width - r && py >= t && py <= this.o.height - b;
        if (this.dragging) {
          this.o.onDrag && this.o.onDrag(this.dragging, this.pxToX(px), this.pxToY(py), evt);
          return;
        }
        if (!inside) {
          this._hideHover();
          return;
        }
        const x = this.pxToX(px);
        this.cross.setAttribute('x1', px);
        this.cross.setAttribute('x2', px);
        this.cross.setAttribute('visibility', 'visible');
        if (this.o.onHover) this.o.onHover(x);
        if (this.o.tooltip) this._showTip(x, px, py);
      });
      host.addEventListener('pointerleave', () => {
        if (!this.dragging) this._hideHover();
      });
      host.addEventListener('pointerdown', (evt) => {
        if (!this.svg) return;
        const target = evt.target.closest('.pt');
        const [px, py] = this._local(evt);
        // Detect double-clicks here: a click re-renders the SVG, so the native dblclick never fires.
        const now = performance.now();
        const prev = this._lastDown;
        this._lastDown = { t: now, px, py, id: target ? target.dataset.id : null };
        if (prev && now - prev.t < 400 && Math.hypot(px - prev.px, py - prev.py) < 8 && this.o.onDblClick) {
          this._lastDown = null;
          this.o.onDblClick(this.pxToX(px), this.pxToY(py), prev.id ?? (target ? target.dataset.id : null), evt);
          evt.preventDefault();
          return;
        }
        if (target && this.o.onDragStart) {
          const id = target.dataset.id;
          if (this.o.onDragStart(id, evt) !== false) {
            this.dragging = id;
            host.setPointerCapture(evt.pointerId);
            this.tip.hidden = true;
            evt.preventDefault();
          }
          return;
        }
        if (this.o.onClick) this.o.onClick(this.pxToX(px), this.pxToY(py), evt);
      });
      const end = (evt) => {
        if (this.dragging) {
          const id = this.dragging;
          this.dragging = null;
          try {
            host.releasePointerCapture(evt.pointerId);
          } catch (e) {
            /* already released */
          }
          this.o.onDragEnd && this.o.onDragEnd(id, evt);
        }
      };
      host.addEventListener('pointerup', end);
      host.addEventListener('pointercancel', end);
    }

    _hideHover() {
      if (this.cross) this.cross.setAttribute('visibility', 'hidden');
      this.tip.hidden = true;
      if (this.o.onHover) this.o.onHover(null);
    }

    _showTip(x, px, py) {
      let html = '';
      if (typeof this.o.tooltip === 'function') html = this.o.tooltip(x);
      else {
        const rows = (this.data.series || [])
          .filter((s) => s.name && !s.hidden)
          .map((s) => {
            const i = nearestIndex(s.x, x);
            return `<div><span class="sw" style="background:${s.color || 'var(--series-1)'}"></span>${s.name} <b>${this.o.yFormat(s.y[i])}</b></div>`;
          });
        html = `<div class="muted">${this.o.xFormat(x)}</div>${rows.join('')}`;
      }
      if (!html) {
        this.tip.hidden = true;
        return;
      }
      this.tip.innerHTML = html;
      this.tip.hidden = false;
      const scale = this.el.clientWidth / this.width;
      const tw = this.tip.offsetWidth;
      let left = px * scale + 14;
      if (left + tw > this.el.clientWidth) left = px * scale - tw - 14;
      this.tip.style.left = `${left}px`;
      this.tip.style.top = `${Math.max(0, py * scale - 30)}px`;
    }
  }

  function nearestIndex(xs, x) {
    let lo = 0;
    let hi = xs.length - 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (xs[mid] < x) lo = mid;
      else hi = mid;
    }
    return Math.abs(xs[lo] - x) <= Math.abs(xs[hi] - x) ? lo : hi;
  }

  // ---------------------------------------------------------------------------
  // CamView: animated cam and follower
  // ---------------------------------------------------------------------------
  function polyPath(xs, ys, close = true, step = 1) {
    let d = '';
    for (let i = 0; i < xs.length; i += step) d += `${i ? 'L' : 'M'}${xs[i].toFixed(3)},${ys[i].toFixed(3)}`;
    return d + (close ? 'Z' : '');
  }

  class CamView {
    constructor(el, opts = {}) {
      this.el = typeof el === 'string' ? document.getElementById(el) : el;
      this.el.classList.add('cam-stage');
      this.o = Object.assign({ heat: true, pitch: true, labels: true, aspect: 1 }, opts);
      this.index = 0;
    }

    setDesign(m, f, prof, chk) {
      this.m = m;
      this.f = f;
      this.prof = prof;
      this.chk = chk;
      this._build();
      this.setIndex(this.index);
    }

    _bounds() {
      const { m, f, chk } = this;
      const sMax = Math.max(...m.s);
      const R = chk.rMax;
      let x0 = -R;
      let x1 = R;
      let y0 = -R;
      let y1 = R;
      if (f.type === 'roller') {
        const top = Math.sqrt(Math.max((f.rb + f.rr) ** 2 - (f.e || 0) ** 2, 0)) + sMax + f.rr + 0.55 * f.rb;
        y1 = Math.max(y1, top);
        x0 = Math.min(x0, (f.e || 0) - f.rr * 1.6);
        x1 = Math.max(x1, (f.e || 0) + f.rr * 1.6);
      } else if (f.type === 'flat') {
        y1 = Math.max(y1, f.rb + sMax + 0.6 * f.rb);
        x0 = Math.min(x0, chk.faceMin - 6);
        x1 = Math.max(x1, chk.faceMax + 6);
      } else {
        x1 = Math.max(x1, f.pivot + 8);
        y1 = Math.max(y1, f.arm * 0.9);
        for (let i = 0; i < m.s.length; i += 12) {
          const P = C.pitchFixed(f, m.s[i], 0, 0);
          y1 = Math.max(y1, P.y + f.rr + 4);
          y0 = Math.min(y0, P.y - f.rr - 4);
        }
        y0 = Math.min(y0, -12);
      }
      const pad = 0.08 * Math.max(x1 - x0, y1 - y0);
      return [x0 - pad, y0 - pad, x1 + pad, y1 + pad * 1.6];
    }

    _build() {
      const { m, f, prof, chk } = this;
      // o.bounds lets several views share one scale (e.g. cams on one shaft).
      const [x0, y0, x1, y1] = this.o.bounds || this._bounds();
      this.vb = [x0, y0, x1, y1];
      const W = x1 - x0;
      const H = y1 - y0;
      const hub = Math.max(3, 0.22 * f.rb);
      const limit = chk.phiLimit;
      // Heat overlay on the profile: amber where |phi| > 80% of limit, red past the limit or at undercut.
      let heat = '';
      if (this.o.heat) {
        const runs = { warn: '', bad: '' };
        for (let i = 0; i < m.s.length - 1; i++) {
          const ph = Math.abs(prof.pressure[i]);
          const rho = f.type === 'flat' ? prof.rhoSurf[i] : prof.rhoPitch[i];
          const under = f.type === 'flat' ? rho <= 0 : rho > 0 && rho < f.rr;
          const level = under || ph > limit ? 'bad' : ph > 0.8 * limit ? 'warn' : null;
          if (level) runs[level] += `M${prof.surfX[i].toFixed(3)},${prof.surfY[i].toFixed(3)}L${prof.surfX[i + 1].toFixed(3)},${prof.surfY[i + 1].toFixed(3)}`;
        }
        heat = `<path d="${runs.warn}" style="fill:none;stroke:var(--status-warning);stroke-width:4;stroke-linecap:round;vector-effect:non-scaling-stroke"></path>
                <path d="${runs.bad}" style="fill:none;stroke:var(--status-critical);stroke-width:4;stroke-linecap:round;vector-effect:non-scaling-stroke"></path>`;
      }
      const base = f.type === 'flat' ? f.rb : f.rb;
      const prime = f.type === 'flat' ? 0 : f.rb + f.rr;
      const step = m.s.length > 1500 ? 2 : 1;
      this.el.innerHTML = `
        <svg viewBox="${x0} ${-y1} ${W} ${H}" preserveAspectRatio="xMidYMid meet" style="aspect-ratio:${W}/${H}">
          <g transform="scale(1,-1)">
            <g class="ground"></g>
            <g class="cam" >
              <path class="cam-body" d="${polyPath(prof.surfX, prof.surfY, true, step)}"></path>
              ${heat}
              <circle class="cam-guide" r="${base}"></circle>
              ${this.o.pitch && prime ? `<path class="cam-pitch" d="${polyPath(prof.pitchX, prof.pitchY, true, step)}"></path>` : ''}
              <circle class="cam-hub" r="${hub}"></circle>
              <rect class="cam-hub" x="${-hub * 0.25}" y="${hub * 0.8}" width="${hub * 0.5}" height="${hub * 0.45}"></rect>
              <line x1="${base * 0.92}" y1="0" x2="${base * 0.75}" y2="0" style="stroke:var(--cam-stroke);stroke-width:2;vector-effect:non-scaling-stroke"></line>
            </g>
            <g class="follower"></g>
            <g class="overlay"></g>
          </g>
          <g class="labels"></g>
        </svg>`;
      this.svg = this.el.querySelector('svg');
      this.gCam = this.svg.querySelector('.cam');
      this.gFol = this.svg.querySelector('.follower');
      this.gOv = this.svg.querySelector('.overlay');
      this.gLab = this.svg.querySelector('.labels');
      this.gGround = this.svg.querySelector('.ground');
      this.unit = Math.max(W, H) / 100; // 1% of view, for sizing marks
      this._drawGround();
    }

    _drawGround() {
      const { f, m } = this;
      const u = this.unit;
      const sMax = Math.max(...m.s);
      let g = '';
      if (f.type === 'roller' || f.type === 'flat') {
        const ex = f.type === 'roller' ? f.e || 0 : 0;
        const d = f.type === 'roller' ? Math.sqrt(Math.max((f.rb + f.rr) ** 2 - ex * ex, 0)) : f.rb;
        const yb = d + sMax + (f.type === 'roller' ? f.rr : 0) + 0.18 * f.rb;
        const w = f.type === 'roller' ? f.rr * 0.7 : Math.max(4, 0.12 * f.rb);
        const len = 0.25 * f.rb;
        g += `<rect class="follower-ground" x="${ex - w / 2 - 1.6 * u}" y="${yb}" width="${1.6 * u}" height="${len}"></rect>
              <rect class="follower-ground" x="${ex + w / 2}" y="${yb}" width="${1.6 * u}" height="${len}"></rect>
              <line x1="${ex}" y1="${-2 * u}" x2="${ex}" y2="${yb + len + 4 * u}" style="stroke:var(--text-light);stroke-width:0.8;stroke-dasharray:6 3 1 3;vector-effect:non-scaling-stroke;opacity:.6"></line>`;
      } else {
        const [px, py] = [f.pivot, 0];
        g += `<path d="M${px - 3 * u},${py - 3.5 * u}L${px + 3 * u},${py - 3.5 * u}L${px},${py}Z" class="follower-ground"></path>
              <line x1="${px - 4.5 * u}" y1="${py - 3.5 * u}" x2="${px + 4.5 * u}" y2="${py - 3.5 * u}" class="follower-ground"></line>`;
      }
      g += `<line x1="${-3 * u}" y1="0" x2="${3 * u}" y2="0" style="stroke:var(--text-light);stroke-width:.8;vector-effect:non-scaling-stroke"></line>
            <line x1="0" y1="${-3 * u}" x2="0" y2="${3 * u}" style="stroke:var(--text-light);stroke-width:.8;vector-effect:non-scaling-stroke"></line>`;
      this.gGround.innerHTML = g;
    }

    setIndex(i) {
      if (!this.m) return;
      const { m, f, prof, chk } = this;
      i = Math.max(0, Math.min(m.s.length - 1, Math.round(i)));
      this.index = i;
      const P = C.pose(m, f, prof, i);
      const u = this.unit;
      this.gCam.setAttribute('transform', `rotate(${m.theta[i]})`);
      const sMax = Math.max(...m.s);
      let fol = '';
      let ov = '';
      let lab = '';
      const phi = prof.pressure[i];
      if (f.type === 'roller') {
        const [cx, cy] = P.center;
        const d = Math.sqrt(Math.max((f.rb + f.rr) ** 2 - (f.e || 0) ** 2, 0));
        const top = d + sMax + f.rr + 0.55 * f.rb;
        const w = f.rr * 0.7;
        fol += `<rect class="follower-metal" x="${cx - w / 2}" y="${cy}" width="${w}" height="${top - cy}" rx="${w * 0.1}"></rect>`;
        fol += `<circle class="follower-roller" cx="${cx}" cy="${cy}" r="${f.rr}"></circle><circle class="follower-metal" cx="${cx}" cy="${cy}" r="${Math.max(f.rr * 0.25, 0.8 * u)}"></circle>`;
      } else if (f.type === 'flat') {
        const y = P.faceY;
        const fw = chk.faceMax - chk.faceMin;
        const x0 = chk.faceMin - Math.max(3, fw * 0.12);
        const x1 = chk.faceMax + Math.max(3, fw * 0.12);
        const th = Math.max(2.5, 0.08 * f.rb);
        const w = Math.max(4, 0.12 * f.rb);
        const top = f.rb + sMax + 0.6 * f.rb;
        fol += `<rect class="follower-metal" x="${-w / 2}" y="${y + th}" width="${w}" height="${top - y - th}"></rect>`;
        fol += `<rect class="follower-metal" x="${x0}" y="${y}" width="${x1 - x0}" height="${th}" rx="1"></rect>`;
      } else {
        const [cx, cy] = P.center;
        const [px, py] = P.pivot;
        const w = Math.max(f.rr * 0.7, 2.5 * u);
        const ang = Math.atan2(cy - py, cx - px);
        const len = Math.hypot(cx - px, cy - py);
        fol += `<g transform="translate(${px} ${py}) rotate(${(ang * 180) / Math.PI})"><rect class="follower-metal" x="${-w * 0.6}" y="${-w / 2}" width="${len + w * 0.6}" height="${w}" rx="${w / 2}"></rect></g>`;
        fol += `<circle class="follower-roller" cx="${px}" cy="${py}" r="${w * 0.55}"></circle>`;
        fol += `<circle class="follower-roller" cx="${cx}" cy="${cy}" r="${f.rr}"></circle><circle class="follower-metal" cx="${cx}" cy="${cy}" r="${Math.max(f.rr * 0.25, 0.8 * u)}"></circle>`;
      }
      // Force line (common normal) and direction of follower motion, with pressure-angle arc.
      const [kx, ky] = P.contact;
      const [nx, ny] = P.normal;
      const L = Math.max(f.rr * 3, 14 * u);
      ov += `<line class="force-line" x1="${kx - nx * 2 * u}" y1="${ky - ny * 2 * u}" x2="${kx + nx * L}" y2="${ky + ny * L}"></line>`;
      ov += `<circle class="contact-dot" cx="${kx}" cy="${ky}" r="${1.1 * u}"></circle>`;
      if (f.type !== 'flat') {
        const [cx, cy] = P.center;
        const [mx, my] = P.motion;
        ov += `<line class="motion-line" x1="${cx}" y1="${cy}" x2="${cx + mx * L * 0.9}" y2="${cy + my * L * 0.9}" style="stroke-dasharray:5 3"></line>`;
        const ra = Math.max(f.rr * 1.7, 8 * u);
        const a0 = Math.atan2(my, mx);
        const a1 = Math.atan2(ny, nx);
        let da = a1 - a0;
        while (da > Math.PI) da -= 2 * Math.PI;
        while (da < -Math.PI) da += 2 * Math.PI;
        const ex = cx + ra * Math.cos(a0 + da);
        const ey = cy + ra * Math.sin(a0 + da);
        ov += `<path class="angle-arc" d="M${cx + ra * Math.cos(a0)},${cy + ra * Math.sin(a0)}A${ra},${ra} 0 0 ${da > 0 ? 1 : 0} ${ex},${ey}"></path>`;
        if (this.o.labels) {
          // Put the label beside the follower, on the side the force line leans toward, clear of the stem.
          const side = nx >= 0 ? 1 : -1;
          const lx = cx + side * (f.rr + 4 * u);
          const ly = cy + ra * 0.55;
          lab += `<text class="cam-label mono" x="${lx}" y="${-ly}" style="font-size:${3.4 * u}px;stroke-width:${0.8 * u}px" text-anchor="${side > 0 ? 'start' : 'end'}">φ ${Math.abs(phi).toFixed(1)}°</text>`;
        }
      }
      if (this.o.labels) {
        const [vx0, , , vy1] = this.vb;
        lab += `<text class="cam-label mono" x="${vx0 + 2 * u}" y="${-vy1 + 5 * u}" style="font-size:${3 * u}px;stroke-width:${0.8 * u}px">θ ${m.theta[i].toFixed(0).padStart(3, '\u2007')}°  s ${m.s[i].toFixed(2)} mm</text>`;
      }
      this.gFol.innerHTML = fol;
      this.gOv.innerHTML = ov;
      this.gLab.innerHTML = lab;
    }
  }

  // Simple animation loop helper. speed = degrees of cam per second.
  class Player {
    constructor({ n, onFrame, speed = 60 }) {
      this.n = n;
      this.onFrame = onFrame;
      this.speed = speed;
      this.pos = 0;
      this.playing = false;
      this.hold = false;
      this._tick = this._tick.bind(this);
    }
    play() {
      if (this.playing) return;
      this.playing = true;
      this.last = performance.now();
      requestAnimationFrame(this._tick);
    }
    pause() {
      this.playing = false;
    }
    toggle() {
      this.playing ? this.pause() : this.play();
      return this.playing;
    }
    seekDeg(deg) {
      this.pos = ((deg % 360) + 360) % 360;
      this.onFrame(this.pos);
    }
    _tick(now) {
      if (!this.playing) return;
      const dt = Math.min(0.1, (now - this.last) / 1000);
      this.last = now;
      if (!this.hold) {
        this.pos = (this.pos + this.speed * dt) % 360;
        this.onFrame(this.pos);
      }
      requestAnimationFrame(this._tick);
    }
  }

  // ---------------------------------------------------------------------------
  // Segment editor
  // ---------------------------------------------------------------------------
  const PRESETS = [
    ['drdr', 'Dwell-rise-dwell-return'],
    ['rrr', 'Rise-return-dwell'],
    ['indexer', 'Long dwell indexer'],
    ['valve', 'Valve-style lift'],
  ];

  class SegmentEditor {
    constructor(el, segments, onChange) {
      this.el = typeof el === 'string' ? document.getElementById(el) : el;
      this.segments = segments;
      this.onChange = onChange;
      this.render();
    }

    set(segments) {
      this.segments = segments;
      this.render();
    }

    render() {
      const lawOpts = Object.entries(C.LAWS)
        .map(([k, v]) => `<option value="${k}" title="${v.name}">${v.short || v.name}</option>`)
        .join('');
      this.el.innerHTML = `
        <div class="btn-row" style="margin-bottom:10px">
          <select class="preset" aria-label="Preset motion" style="flex:1">
            <option value="">Load a preset…</option>
            ${PRESETS.map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}
          </select>
        </div>
        <div class="seg-row seg-head"><span>Type</span><span>Motion law</span><span>Angle °</span><span>Lift mm</span><span></span></div>
        <div class="seg-list"></div>
        <div class="btn-row" style="margin-top:8px">
          <button class="btn small add" type="button">+ Segment</button>
          <button class="btn small fill" type="button" title="Resize the last dwell so the total is 360°">Fill to 360°</button>
        </div>
        <div class="seg-status"></div>`;
      const list = this.el.querySelector('.seg-list');
      this.segments.forEach((sg, idx) => {
        const row = document.createElement('div');
        row.className = 'seg-row';
        row.innerHTML = `
          <select class="t" aria-label="Segment ${idx + 1} type"><option value="rise">Rise</option><option value="fall">Fall</option><option value="dwell">Dwell</option></select>
          <select class="l" aria-label="Segment ${idx + 1} law">${lawOpts}</select>
          <input class="d" type="number" min="1" step="1" aria-label="Segment ${idx + 1} angle" value="${sg.duration}">
          <input class="h" type="number" min="0" step="0.5" aria-label="Segment ${idx + 1} lift" value="${sg.lift ?? 0}">
          <button class="x" type="button" aria-label="Remove segment ${idx + 1}">×</button>`;
        row.querySelector('.t').value = sg.type;
        row.querySelector('.l').value = sg.law || 'cycloidal';
        row.querySelector('.l').disabled = sg.type === 'dwell';
        row.querySelector('.h').disabled = sg.type === 'dwell';
        row.addEventListener('input', () => {
          sg.type = row.querySelector('.t').value;
          sg.law = row.querySelector('.l').value;
          sg.duration = Number(row.querySelector('.d').value) || 0;
          sg.lift = Number(row.querySelector('.h').value) || 0;
          row.querySelector('.l').disabled = sg.type === 'dwell';
          row.querySelector('.h').disabled = sg.type === 'dwell';
          this._changed();
        });
        row.querySelector('.x').addEventListener('click', () => {
          this.segments.splice(idx, 1);
          this.render();
          this._changed();
        });
        list.appendChild(row);
      });
      this.el.querySelector('.add').addEventListener('click', () => {
        this.segments.push({ type: 'dwell', duration: 30, lift: 0, law: 'cycloidal' });
        this.render();
        this._changed();
      });
      this.el.querySelector('.fill').addEventListener('click', () => {
        const total = this.segments.reduce((a, s) => a + Number(s.duration), 0);
        let last = [...this.segments].reverse().find((s) => s.type === 'dwell');
        if (!last) {
          last = { type: 'dwell', duration: 0, lift: 0, law: 'cycloidal' };
          this.segments.push(last);
        }
        last.duration = Math.max(1, Number(last.duration) + 360 - total);
        this.render();
        this._changed();
      });
      this.el.querySelector('.preset').addEventListener('change', (e) => {
        if (!e.target.value) return;
        this.segments.splice(0, this.segments.length, ...C.presetSegments(e.target.value));
        this.render();
        this._changed();
      });
      this._status();
    }

    _status() {
      const total = this.segments.reduce((a, s) => a + Number(s.duration || 0), 0);
      let net = 0;
      this.segments.forEach((s) => {
        if (s.type === 'rise') net += Number(s.lift);
        if (s.type === 'fall') net -= Number(s.lift);
      });
      const okT = Math.abs(total - 360) < 1e-6;
      const okN = Math.abs(net) < 1e-6;
      this.el.querySelector('.seg-status').innerHTML = `
        <span class="pill ${okT ? 'good' : 'bad'}">Total ${fmt(total, 1)}°</span>
        <span class="pill ${okN ? 'good' : 'bad'}">Net lift ${fmt(net, 2)} mm</span>`;
    }

    _changed() {
      this._status();
      this.onChange && this.onChange(this.segments);
    }
  }

  // ---------------------------------------------------------------------------
  // Design hand-off between pages
  // ---------------------------------------------------------------------------
  const DEFAULT_DESIGN = {
    motion: { kind: 'segments', segments: C.presetSegments('drdr') },
    follower: { type: 'roller', rb: 40, rr: 10, e: 0, arm: 80, pivot: 100 },
    rpm: 120,
  };

  function loadDesign() {
    const d = readJSON(DESIGN_KEY, null);
    if (!d || !d.motion || !d.follower) return JSON.parse(JSON.stringify(DEFAULT_DESIGN));
    return { ...JSON.parse(JSON.stringify(DEFAULT_DESIGN)), ...d };
  }

  function saveDesign(design, note) {
    writeJSON(DESIGN_KEY, design);
    if (note) toast(note);
  }

  function buildMotion(motion, samples = 720) {
    if (motion.kind === 'keyframes') return C.fromKeyframes(motion.keys, motion.spans || [], { samples, order: motion.order });
    return C.fromSegments(motion.segments, { samples });
  }

  // Motion input block: a segment editor, or a note when the motion came from the sketch page.
  function motionHost(el, design, onChange) {
    const host = typeof el === 'string' ? document.getElementById(el) : el;
    if (design.motion.kind === 'keyframes') {
      host.innerHTML = `<p class="small" style="margin:0 0 8px">Using the motion from <b>Motion Sketch</b> (${design.motion.keys.length} points).</p>
        <div class="btn-row"><a class="btn small" href="a-motion-sketch.html">Edit in Sketch</a><button class="btn small" type="button">Use segments instead</button></div>`;
      host.querySelector('button').addEventListener('click', () => {
        design.motion = { kind: 'segments', segments: C.presetSegments('drdr') };
        motionHost(host, design, onChange);
        onChange();
      });
    } else new SegmentEditor(host, design.motion.segments, () => onChange());
  }

  // Buttons that save the current design and open another prototype.
  function handoffButtons(el, getDesign, keys) {
    const host = typeof el === 'string' ? document.getElementById(el) : el;
    host.classList.add('handoff');
    host.innerHTML = keys
      .map((k) => PAGES.find((p) => p.key === k))
      .map((p) => `<a class="btn small" href="${p.href}" data-key="${p.key}">Open in ${p.title.split('·')[1].trim()} →</a>`)
      .join('');
    host.querySelectorAll('a').forEach((a) =>
      a.addEventListener('click', () => {
        saveDesign(getDesign());
      }),
    );
  }

  global.CamUI = {
    PAGES,
    initPage,
    toast,
    download,
    fmt,
    niceTicks,
    cssVar,
    nearestIndex,
    LineChart,
    CamView,
    Player,
    SegmentEditor,
    polyPath,
    loadDesign,
    saveDesign,
    buildMotion,
    handoffButtons,
    motionHost,
    readJSON,
    writeJSON,
  };
})(window);
