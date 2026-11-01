/* Canvas chart with no library: pan, wheel and pinch zoom, box and lasso, hit testing,
   and drawing for points, reported bounds, intervals and shapes. */
(function (root) {
  'use strict';
  const { clamp, formatValue } = root.AshbyEngine;
  const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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
      this.opts = { padding: { l: 62, r: 16, t: 14, b: 48 }, pointSize: 3.2, ...options };
      this.canvas = document.createElement('canvas');
      this.canvas.className = 'ac-canvas';
      this.tip = document.createElement('div');
      this.tip.className = 'ac-tip';
      this.tip.hidden = true;
      host.classList.add('ac-plot');
      host.append(this.canvas, this.tip);
      this.ctx = this.canvas.getContext('2d');
      this.rows = []; this.shapes = []; this.view = null; this.fitView = null; this.mode = 'pan';
      this.selected = new Set(); this.hover = null; this.overlay = null; this.pointers = new Map(); this.lastScroll = 0;
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
    /* rows: [{key, m, tx, ty, color, dim, ring, size, bound, tRange}] */
    setData({ rows, xAxis, yAxis, keepView = false }) {
      this.xAxis = xAxis; this.yAxis = yAxis;
      this.rows = rows;
      const live = rows.filter(r => !r.dim);
      this.fitView = this.computeFit(live.length ? live : rows);
      if (!keepView || !this.view) this.view = { ...this.fitView };
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
    /* Fit makes room for the outlines, so they are not clipped at the edge of the plot. */
    growFit(shapes, keepView) {
      if (!this.fitView) return;
      const f = this.fitView, mx = (f.x1 - f.x0) * .02, my = (f.y1 - f.y0) * .02;
      for (const shape of shapes) for (const loop of shape.loops) for (const [x, y] of loop) {
        f.x0 = Math.min(f.x0, x - mx); f.x1 = Math.max(f.x1, x + mx); f.y0 = Math.min(f.y0, y - my); f.y1 = Math.max(f.y1, y + my);
      }
      if (!keepView) this.view = { ...f };
    }
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
    draw() {
      if (this.pending || !this.view) return;
      this.pending = true;
      requestAnimationFrame(() => { this.pending = false; this.render(); this.opts.onDraw?.(); });
    }
    pathFor(ctx, loop) {
      for (let i = 0; i < loop.length; i++) {
        const X = this.sx(loop[i][0]), Y = this.sy(loop[i][1]);
        if (i) ctx.lineTo(X, Y); else ctx.moveTo(X, Y);
      }
      ctx.closePath();
    }
    render() {
      const { ctx, w, h } = this, b = this.plotBox;
      const colors = { text: cssVar('--text-color'), muted: cssVar('--text-light'), grid: cssVar('--grid-color'), plot: cssVar('--plot-color'), ghost: cssVar('--ghost-color'), halo: cssVar('--bg-card') };
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      if (this.exporting) { ctx.fillStyle = colors.halo; ctx.fillRect(0, 0, w, h); }
      ctx.fillStyle = colors.plot; ctx.fillRect(b.l, b.t, b.w, b.h);
      ctx.font = '11.5px ' + cssVar('--font-sans'); ctx.lineWidth = 1;
      this.drawAxis(colors);
      ctx.save(); ctx.beginPath(); ctx.rect(b.l, b.t, b.w, b.h); ctx.clip();
      this.drawShapes();
      const size = this.opts.pointSize;
      ctx.fillStyle = colors.ghost;
      for (const r of this.rows) { if (r.dim) { ctx.beginPath(); ctx.arc(this.sx(r.tx), this.sy(r.ty), 1.8, 0, 7); ctx.fill(); } }
      if (this.opts.showRanges) this.drawRanges();
      for (const r of this.rows) {
        if (r.dim) continue;
        const X = this.sx(r.tx), Y = this.sy(r.ty);
        if (X < b.l - 12 || X > b.r + 12 || Y < b.t - 12 || Y > b.b + 12) continue;
        const radius = r.size || size;
        if (this.opts.showPoints !== false) {
          if (r.bound) {
            // An open marker: a reported bound is a limit, not a measured value.
            ctx.globalAlpha = 1; ctx.strokeStyle = r.color; ctx.lineWidth = 1.4;
            ctx.fillStyle = colors.plot; ctx.beginPath(); ctx.arc(X, Y, radius, 0, 7); ctx.fill(); ctx.stroke(); ctx.lineWidth = 1;
          } else {
            ctx.globalAlpha = this.opts.pointAlpha ?? .92;
            ctx.fillStyle = r.color; ctx.beginPath(); ctx.arc(X, Y, radius, 0, 7); ctx.fill();
            ctx.globalAlpha = 1;
          }
        }
        if (r.ring) { ctx.strokeStyle = r.ring; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(X, Y, radius + 2.5, 0, 7); ctx.stroke(); ctx.lineWidth = 1; }
        if (this.selected.has(r.key)) { ctx.strokeStyle = colors.text; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(X, Y, radius + 2, 0, 7); ctx.stroke(); ctx.lineWidth = 1; }
      }
      this.opts.afterPoints?.(ctx, this);
      if (this.hover) { ctx.strokeStyle = colors.text; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(this.sx(this.hover.tx), this.sy(this.hover.ty), (this.hover.size || size) + 3, 0, 7); ctx.stroke(); ctx.lineWidth = 1; }
      if (this.opts.showPointLabels) this.drawPointLabels(colors);
      this.drawShapeLabels(colors);
      this.drawOverlay(colors);
      ctx.restore();
      ctx.strokeStyle = colors.grid; ctx.strokeRect(b.l + .5, b.t + .5, b.w, b.h);
    }
    drawRanges() {
      const { ctx } = this;
      ctx.lineWidth = 1;
      for (const r of this.rows) {
        if (r.dim || !r.tRange) continue;
        const X = this.sx(r.tx), Y = this.sy(r.ty);
        ctx.strokeStyle = r.color;
        if (r.tRange.x) { ctx.beginPath(); ctx.moveTo(this.sx(r.tRange.x[0]), Y); ctx.lineTo(this.sx(r.tRange.x[1]), Y); ctx.stroke(); }
        if (r.tRange.y) { ctx.beginPath(); ctx.moveTo(X, this.sy(r.tRange.y[0])); ctx.lineTo(X, this.sy(r.tRange.y[1])); ctx.stroke(); }
      }
    }
    drawShapes() {
      const { ctx } = this;
      const fill = this.opts.blobFill ?? .16;
      for (const shape of this.shapes) {
        ctx.fillStyle = shape.color; ctx.strokeStyle = shape.color;
        ctx.globalAlpha = fill; ctx.beginPath(); shape.loops.forEach(l => this.pathFor(ctx, l)); ctx.fill('evenodd');
        ctx.globalAlpha = .75; ctx.lineWidth = 1.2; ctx.stroke();
        ctx.globalAlpha = 1; ctx.lineWidth = 1;
      }
    }
    drawPointLabels(colors) {
      const { ctx } = this, b = this.plotBox;
      ctx.font = '10.5px ' + cssVar('--font-sans'); ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
      const taken = [];
      for (const r of this.rows) {
        if (r.dim) continue;
        const X = this.sx(r.tx) + 6, Y = this.sy(r.ty);
        if (X < b.l || X > b.r || Y < b.t || Y > b.b) continue;
        if (taken.length > 400 || taken.some(t => Math.abs(t[1] - Y) < 12 && X < t[0] + t[2] && X + 90 > t[0])) continue;
        const text = r.name || r.m.name, tw = ctx.measureText(text).width;
        taken.push([X, Y, tw]);
        ctx.lineWidth = 3; ctx.strokeStyle = colors.halo; ctx.lineJoin = 'round'; ctx.strokeText(text, X, Y);
        ctx.fillStyle = colors.text; ctx.fillText(text, X, Y);
      }
      ctx.lineWidth = 1; ctx.textBaseline = 'alphabetic';
    }
    drawShapeLabels(colors) {
      if (this.opts.showShapeLabels === false) return;
      const { ctx } = this, placed = [], b = this.plotBox;
      ctx.font = '600 12px ' + cssVar('--font-sans'); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
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
          if (span > 2.6 || room < 3.5) {
            const step = Math.max(1, Math.ceil(span / room));
            for (let d = Math.ceil(lo); d <= hi; d += step) major.push(d);
            for (let d = Math.floor(lo); d <= hi; d++) if (step === 1 && room > 4) for (const m of [2, 5]) { const t = d + Math.log10(m); if (t >= lo && t <= hi) minor.push(t); }
          } else {
            for (let d = Math.floor(lo); d <= hi; d++) for (const m of (span > 1.2 ? [1, 2, 5] : [1, 1.5, 2, 3, 5, 7])) { const t = d + Math.log10(m); if (t >= lo && t <= hi) major.push(t); }
          }
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
      if (this.exporting && this.xAxis) {
        ctx.fillStyle = colors.text; ctx.font = '600 12.5px ' + cssVar('--font-sans'); ctx.textAlign = 'center';
        ctx.fillText(this.xAxis.label, b.l + b.w / 2, this.h - 16);
        ctx.save(); ctx.translate(26, b.t + b.h / 2); ctx.rotate(-Math.PI / 2); ctx.fillText(this.yAxis.label, 0, 0); ctx.restore();
        ctx.textAlign = 'start'; ctx.font = '11.5px ' + cssVar('--font-sans');
      }
      ctx.textBaseline = 'alphabetic';
    }
    /* Draws the chart into a new canvas at twice the size, with axis titles and any extras. */
    toImage(extras) {
      const out = document.createElement('canvas'), scale = 2;
      out.width = this.w * scale; out.height = this.h * scale;
      const keep = { ctx: this.ctx, dpr: this.dpr, hover: this.hover };
      this.ctx = out.getContext('2d'); this.dpr = scale; this.hover = null; this.exporting = true;
      this.render();
      this.ctx.setTransform(scale, 0, 0, scale, 0, 0);
      extras?.(this.ctx, this);
      Object.assign(this, keep); this.exporting = false;
      return out;
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
    wheelZoom(e) {
      // A page scroll that reaches the chart keeps scrolling the page, rather than zooming by surprise.
      if (performance.now() - this.lastScroll < 300) return;
      e.preventDefault();
      const [x, y] = this.point(e);
      this.zoomAt(x, y, Math.exp(e.deltaY * .0016));
    }
    bind() {
      const c = this.canvas;
      c.style.touchAction = 'none';
      addEventListener('scroll', () => { this.lastScroll = performance.now(); }, { passive: true });
      c.addEventListener('selectstart', e => e.preventDefault());
      c.addEventListener('wheel', e => this.wheelZoom(e), { passive: false });
      c.addEventListener('dblclick', () => this.fit());
      c.addEventListener('pointerdown', e => {
        const [x, y] = this.point(e);
        this.pointers.set(e.pointerId, [x, y]);
        c.setPointerCapture(e.pointerId);
        if (this.pointers.size === 2) { this.drag = null; this.overlay = null; const [a, b] = [...this.pointers.values()]; this.pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]) }; return; }
        if (this.opts.onPointerDown?.(x, y, e, this)) { this.drag = { kind: 'custom' }; return; }
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
        const reach = e.pointerType === 'touch' ? 26 : 16;
        if (drag.kind === 'custom') { this.opts.onPointerUp?.(x, y, e, this); return; }
        if (drag.kind === 'pan') { c.style.cursor = 'grab'; if (!drag.moved && e.type === 'pointerup') this.opts.onClick?.(this.nearest(x, y, reach), e); return; }
        const o = this.overlay; this.overlay = null;
        if (drag.kind === 'box' && Math.abs(o.x1 - o.x0) > 4 && Math.abs(o.y1 - o.y0) > 4) {
          const x0 = Math.min(o.x0, o.x1), x1 = Math.max(o.x0, o.x1), y0 = Math.min(o.y0, o.y1), y1 = Math.max(o.y0, o.y1);
          const hits = this.rows.filter(r => { if (r.dim) return false; const X = this.sx(r.tx), Y = this.sy(r.ty); return X >= x0 && X <= x1 && Y >= y0 && Y <= y1; });
          this.opts.onSelect?.(hits, { kind: 'box', x0: this.ix(x0), x1: this.ix(x1), y0: this.iy(y1), y1: this.iy(y0) });
        } else if (drag.kind === 'lasso' && o.path.length > 4) {
          const inside = (X, Y) => { let hit = false; for (let i = 0, j = o.path.length - 1; i < o.path.length; j = i++) { const [xi, yi] = o.path[i], [xj, yj] = o.path[j]; if ((yi > Y) !== (yj > Y) && X < (xj - xi) * (Y - yi) / (yj - yi) + xi) hit = !hit; } return hit; };
          this.opts.onSelect?.(this.rows.filter(r => !r.dim && inside(this.sx(r.tx), this.sy(r.ty))), { kind: 'lasso' });
        } else if (e.type === 'pointerup') {
          // A click with no drag still picks a single material in Box and Lasso modes.
          this.opts.onClick?.(this.nearest(x, y, reach), e);
        }
        this.draw();
      };
      c.addEventListener('pointerup', up);
      c.addEventListener('pointercancel', up);
      c.addEventListener('pointerleave', () => { if (!this.drag && this.hover) { this.hover = null; this.hideTip(); this.draw(); } });
    }
    showTip(row, x, y) {
      if (!row) return this.hideTip();
      this.tip.replaceChildren(...this.opts.tipFormat(row));
      this.tip.hidden = false; this.placeTip(x, y);
    }
    placeTip(x, y) {
      const w = this.tip.offsetWidth, h = this.tip.offsetHeight;
      this.tip.style.left = clamp(x + 14 + w > this.w ? x - w - 14 : x + 14, 4, this.w - w - 4) + 'px';
      this.tip.style.top = clamp(y - h - 10 < 0 ? y + 14 : y - h - 10, 4, this.h - h - 4) + 'px';
    }
    hideTip() { this.tip.hidden = true; }
  }
  root.AshbyPlot = Plot;
})(typeof self !== 'undefined' ? self : this);
