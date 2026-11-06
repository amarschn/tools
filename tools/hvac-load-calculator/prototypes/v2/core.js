/* Shared app core for options D and E: one model, its assumptions, and the live estimate. */
(function () {
  'use strict';
  const P = () => window.Proto; const M = () => window.HouseModel; const D = () => window.HouseDrawing;
  const $ = (id) => document.getElementById(id);
  const fmt = (v, d = 0) => (v === null || v === undefined || !Number.isFinite(Number(v))) ? '–' : Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const ELEMENTS = {
    site: { title: 'Location', known: ['heating_design_f', 'cooling_design_f'] },
    shape: { title: 'Size and shape', known: [] },
    walls: { title: 'Walls', known: ['wall_u'] },
    ceiling: { title: 'Ceiling and roof', known: ['ceiling_u'] },
    floor: { title: 'Floor', known: [] },
    openings: { title: 'Windows and doors', known: ['window_pct_of_floor', 'window_u', 'window_shgc'] },
    air: { title: 'Air leakage', known: ['ach50'] },
    ducts: { title: 'Ducts', known: ['duct_leakage_pct', 'duct_r'] },
    rooms: { title: 'Rooms', known: ['occupants'] },
    system: { title: 'Equipment', known: [] },
  };

  const Core = {
    ELEMENTS, model: null, result: null, eq: null, band: null, confirmed: new Set(), history: {},
    view: { level: 0, season: 'winter', hour: 17, layout: 'both', overlay: false, cut: null, tool: 'select', splitting: false, selected: { room: null, opening: null, wall: null, wallAxis: null }, rotation: 0, addKind: 'window', transform: null, preview: null, guide: null, guideAxis: null, liveText: null },
    listeners: [], drillPanel: null, eraConfirmed: false,

    async start() {
      await P().start();
      const s = P().state;
      this.model = M().create({ area: s.floor_area_ft2, stories: 1, height: 8 });
      this.view.cut = { axis: this.model.w >= this.model.d ? 'x' : 'y', at: (this.model.w >= this.model.d ? this.model.w : this.model.d) / 2 };
      this.compute();
    },
    onChange(fn) { this.listeners.push(fn); },
    assumed(id) { return !this.confirmed.has(id); },
    confirm(id) {
      this.confirmed.add(id);
      (ELEMENTS[id].known || []).forEach((k) => P().state.known.add(k));
      if (id === 'openings') M().confirmOpenings(this.model);
    },
    compute() {
      const s = P().state; const m = this.model;
      s.rooms = M().toEngineRooms(m); s.stories = m.stories; s.floor_area_ft2 = M().area(m);
      s.fields.ceiling_height_ft = m.height; s.fields.rotation_deg = this.view.rotation;
      this.result = P().calc(false);
      P().lastResult = this.result;
      this.eq = P().equipment(this.result);
    },
    /** Range on the answer. Until the era is known, it spans what the era could be. */
    computeBand() {
      const s = P().state; const r = this.result;
      if (!this.eraConfirmed) {
        const keep = s.era; const heats = []; const cools = [];
        ['pre1950', '1950s_70s', '1980s_90s', '2000s', 'new_code'].forEach((era) => {
          s.era = era;
          const one = P().calc(false);
          heats.push(one.heating_total); cools.push(one.cooling_total);
        });
        s.era = keep;
        this.band = { heating_low: Math.min(...heats), heating_high: Math.max(...heats), cooling_low: Math.min(...cools), cooling_high: Math.max(...cools), terms: [], spread: true };
      } else {
        const full = P().calc(true);
        this.band = full.uncertainty;
        this.detail = full;
      }
      void r;
    },
    update({ band = true, light = false } = {}) {
      try {
        this.compute();
        this.error = null;
      } catch (e) {
        // Never show a stale answer as if it were current.
        this.error = String(e.message || e).trim().split('\n').pop();
      }
      const banner = document.getElementById('model-error');
      if (banner) { banner.hidden = !this.error; banner.textContent = this.error ? `The calculation stopped: ${this.error}` : ''; }
      this.listeners.forEach((fn) => fn({ light }));
      if (band) {
        clearTimeout(this.bandTimer);
        this.bandTimer = setTimeout(() => {
          try { this.computeBand(); } catch (e) { /* keep the last band */ }
          this.listeners.forEach((fn) => fn({ bandOnly: true }));
        }, 120);
      }
    },
    /** Heat flows for the current season and hour, by envelope part. */
    flows() {
      const r = this.result; const m = this.model; const c = r.cooling; const h = r.heating.components;
      const glass = M().glassArea(m);
      const doorArea = m.openings.filter((o) => o.kind === 'door').reduce((a, o) => a + M().openingArea(o), 0);
      const wallArea = Math.max(2 * (m.w + m.d) * m.height * m.stories - glass - doorArea, 1);
      const footprint = m.w * m.d;
      if (this.view.season === 'winter') {
        return {
          wall: { total: h.walls + h.doors, flux: (h.walls + h.doors) / wallArea },
          window: { total: h.windows, flux: h.windows / Math.max(glass, 1) },
          ceiling: { total: h.ceiling, flux: h.ceiling / footprint },
          floor: { total: h.floor, flux: h.floor / footprint },
          air: { total: h.infiltration + h.ventilation }, ducts: { total: h.ducts },
        };
      }
      const i = this.view.hour - 1; const hours = c.hourly;
      const fixed = c.hourly_fixed[i]; const ratio = c.room_load > 0 ? c.components.ducts / c.room_load : 0;
      return {
        wall: { total: hours.walls[i], flux: hours.walls[i] / wallArea },
        window: { total: hours.windows[i], flux: hours.windows[i] / Math.max(glass, 1) },
        ceiling: { total: hours.ceiling[i], flux: hours.ceiling[i] / footprint },
        floor: { total: hours.floor[i], flux: hours.floor[i] / footprint },
        air: { total: hours.air[i] }, ducts: { total: Math.max(fixed, 0) * ratio },
      };
    },
    overlay() {
      if (!this.view.overlay || !this.result) return null;
      const winter = this.view.season === 'winter'; const r = this.result; const values = {}; let i = 0; let maxIntensity = 0; const unit = 'Btu/h';
      const raw = {};
      this.model.levels.forEach((lvl) => lvl.rooms.forEach((room) => {
        const row = r.rooms[i]; i += 1;
        const v = winter ? row.heating : row.hourly[this.view.hour - 1];
        values[room.id] = v; raw[room.id] = v / Math.max(room.w * room.h, 1);
        maxIntensity = Math.max(maxIntensity, raw[room.id]);
      }));
      // Plan colors follow load per ft², the labels show the load.
      const scaled = {};
      Object.keys(raw).forEach((k) => { scaled[k] = raw[k] / Math.max(maxIntensity, 1e-6); });
      return { values, intensity: scaled, max: 1, unit, color: winter ? 'var(--heat2)' : 'var(--cool2)' };
    },

    // ---------------------------------------------------------------- drawing
    drawOpts() {
      const v = this.view;
      const overlay = this.overlay();
      return { level: v.level, tool: v.tool, selected: v.selected, cut: v.cut, rotation: v.rotation, confirmed: this.confirmed,
        overlay: overlay ? { values: overlay.values, max: 1, unit: overlay.unit, color: overlay.color, intensity: overlay.intensity } : null,
        preview: v.preview, guide: v.guide, guideAxis: v.guideAxis, liveText: v.liveText, transform: v.transform };
    },
    draw() {
      const v = this.view; const planEl = $('dwg-plan'); const secEl = $('dwg-section'); const axEl = $('dwg-axon');
      const o = this.drawOpts();
      if (planEl && planEl.closest('figure').style.display !== 'none') {
        const t = D().plan(planEl, this.model, o);
        v.lastTransform = t;
      }
      if (secEl && secEl.closest('figure').style.display !== 'none' && this.result) {
        const inputs = P().inputs(); const s = P().state; const c = this.result.cooling;
        D().section(secEl, this.model, {
          ...o, floor: s.floor_type, pitch: inputs.roof_pitch || 6, result: this.result, season: v.season,
          ceilingU: inputs.ceiling_u, wallU: inputs.wall_u, ceilingType: inputs.ceiling_type || 'attic', roofColor: s.fields.roof_color || 'medium',
          ductLocation: inputs.duct_location, system: P().SYSTEMS[s.system], flows: this.flows(),
          tIn: v.season === 'winter' ? this.result.design.indoor_heating_f : this.result.design.indoor_cooling_f,
          tOut: v.season === 'winter' ? this.result.design.heating_f : c.t_out[v.hour - 1],
          tAttic: c.t_attic[v.hour - 1], sun: c.sun[v.hour - 1], sunFromRight: v.cut.axis === 'x' ? true : c.sun[v.hour - 1].azimuth < 0,
        });
      }
      if (axEl && axEl.closest('figure').style.display !== 'none') D().axon(axEl, this.model, o);
      const cap = $('cap-section');
      if (cap) cap.textContent = v.season === 'winter' ? 'Bands show heat leaving, deeper where more leaves per ft²' : `Bands show heat arriving at solar hour ${v.hour}`;
      const hint = $('dwg-hint');
      if (hint) hint.textContent = this.hintText();
    },
    hintText() {
      const v = this.view;
      if (v.tool === 'shell') return 'Drag any outside wall to change the house size. Dashed lines are assumptions you have not confirmed yet.';
      if (v.tool === 'openings') return 'Click a wall to add a ' + v.addKind + '. Drag it along the wall. Drag its blue ends to change its width. Press Delete to remove the selected one.';
      if (v.tool === 'rooms') return v.splitting ? 'Click inside a room to add a wall. The wall follows the closest direction. Press Escape to stop.' : 'Drag a wall to resize the rooms on both sides. Click a room to name it. Nothing can overlap, because walls move and rooms follow.';
      return 'Drag the blue A line to move the section. Dashed lines are assumptions you have not confirmed yet.';
    },
    sheetHtml(extra = '') {
      return `<div class="dwg-bar">
        <div class="dwg-tabs" role="group" aria-label="Views">${[['both', 'Plan + section'], ['plan', 'Plan'], ['section', 'Section'], ['axon', '3D']].map(([k, t]) => `<button type="button" data-layout="${k}">${t}</button>`).join('')}</div>
        <div class="dwg-tabs" role="group" aria-label="Season"><button type="button" data-season="winter">Winter</button><button type="button" data-season="summer">Summer</button></div>
        <label id="hour-wrap" style="display:none;align-items:center;gap:6px;flex:1 1 150px;min-width:130px">Hour <input type="range" id="dwg-hour" min="6" max="21" value="17" aria-label="Solar hour"><span id="dwg-hour-val" style="font-family:var(--mono)">17</span></label>
        <label style="display:inline-flex;align-items:center;gap:5px;cursor:pointer"><input type="checkbox" id="dwg-overlay"> Rooms by load</label>
        <div class="dwg-tabs" id="dwg-levels" role="group" aria-label="Level"></div>
        <button type="button" class="dwg-tabs" id="dwg-cutdir" style="padding:7px 11px;font-size:.78rem;cursor:pointer;min-height:36px;color:var(--ink2)">Turn section 90°</button>
        ${extra}
      </div>
      <div class="sheet" id="sheet">
        <figure id="fig-plan"><figcaption>Plan <span>Level <span id="cap-level">1</span></span></figcaption><svg class="dwg" id="dwg-plan" viewBox="0 0 620 470" role="application" aria-label="Floor plan. Drag walls to change the house."></svg></figure>
        <figure id="fig-section"><figcaption>Section A-A <span id="cap-section"></span></figcaption><svg class="dwg" id="dwg-section" viewBox="0 0 620 470" role="img" aria-label="Section through the house with heat flow bands"></svg></figure>
        <figure id="fig-axon" style="display:none"><figcaption>3D</figcaption><svg class="dwg" id="dwg-axon" viewBox="0 0 620 470" role="img" aria-label="Axonometric view of the house"></svg></figure>
      </div>
      <p class="legend-line" id="dwg-hint"></p>`;
    },
    applyLayout() {
      const v = this.view;
      const show = { 'fig-plan': v.layout === 'both' || v.layout === 'plan', 'fig-section': v.layout === 'both' || v.layout === 'section', 'fig-axon': v.layout === 'axon' };
      Object.entries(show).forEach(([id, on]) => { const el = $(id); if (el) el.style.display = on ? '' : 'none'; });
      const sheet = $('sheet'); if (sheet) sheet.classList.toggle('single', v.layout !== 'both');
      document.querySelectorAll('[data-layout]').forEach((b) => b.classList.toggle('on', b.dataset.layout === v.layout));
      document.querySelectorAll('[data-season]').forEach((b) => b.classList.toggle('on', b.dataset.season === v.season));
      const wrap = $('hour-wrap'); if (wrap) wrap.style.display = v.season === 'summer' ? 'inline-flex' : 'none';
      const levels = $('dwg-levels');
      if (levels) {
        levels.style.display = this.model.stories > 1 ? '' : 'none';
        levels.innerHTML = Array.from({ length: this.model.stories }, (_, l) => `<button type="button" data-level="${l}" class="${l === v.level ? 'on' : ''}">Level ${l + 1}</button>`).join('');
      }
      const cap = $('cap-level'); if (cap) cap.textContent = v.level + 1;
    },
    bindDrawing() {
      const v = this.view;
      document.addEventListener('click', (e) => {
        const b = e.target.closest('button'); if (!b) return;
        if (b.dataset.layout) { v.layout = b.dataset.layout; this.applyLayout(); this.draw(); }
        if (b.dataset.season) { v.season = b.dataset.season; this.applyLayout(); this.draw(); }
        if (b.dataset.level) { v.level = Number(b.dataset.level); v.selected.room = null; this.applyLayout(); this.draw(); this.listeners.forEach((fn) => fn({ selection: true })); }
        if (b.id === 'dwg-cutdir') {
          const axis = v.cut.axis === 'x' ? 'y' : 'x';
          v.cut = { axis, at: (axis === 'x' ? this.model.w : this.model.d) / 2 };
          this.draw();
        }
      });
      document.addEventListener('input', (e) => {
        if (e.target.id === 'dwg-hour') { v.hour = Number(e.target.value); $('dwg-hour-val').textContent = v.hour; this.draw(); }
        if (e.target.id === 'dwg-overlay') { v.overlay = e.target.checked; this.draw(); }
      });
      this.bindPlan();
      const section = $('dwg-section');
      if (section) section.addEventListener('click', (e) => {
        const go = e.target.closest('[data-go]');
        if (go && this.drillPanel) { this.drillPanel.open(go.dataset.go); this.listeners.forEach((fn) => fn({ math: true })); return; }
        const room = e.target.closest('[data-room]');
        if (room) { this.selectRoom(room.dataset.room); }
      });
      const ax = $('dwg-axon');
      if (ax) ax.addEventListener('click', (e) => { const room = e.target.closest('[data-room]'); if (room) { v.level = Number(room.dataset.level); this.selectRoom(room.dataset.room); this.applyLayout(); } });
    },
    selectRoom(id) { this.view.selected.room = id; this.draw(); this.listeners.forEach((fn) => fn({ selection: true })); },

    // ------------------------------------------------------------- plan editing
    bindPlan() {
      const svg = $('dwg-plan'); if (!svg) return;
      const v = this.view; const self = this;
      let drag = null; let raf = null;
      const toFeet = (e, fixed) => {
        const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
        const q = pt.matrixTransform(svg.getScreenCTM().inverse());
        const t = fixed || v.transform || v.lastTransform;
        return { x: (q.x - t.ox) / t.scale, y: (q.y - t.oy) / t.scale };
      };
      const refresh = () => {
        if (raf) return;
        raf = requestAnimationFrame(() => { raf = null; self.update({ band: false, light: true }); });
      };
      const wallList = () => M().interiorWalls(self.model, v.level);
      const others = (wall) => {
        const set = new Set();
        wallList().filter((w) => w.axis === wall.axis && !(w.at === wall.at && w.start === wall.start)).forEach((w) => set.add(w.at));
        return [...set];
      };
      svg.addEventListener('pointerdown', (e) => {
        const t = e.target; const d = t.dataset; const at = toFeet(e);
        v.transform = v.lastTransform; // keep the drawing still while dragging
        if (d.shell) {
          drag = { type: 'shell', side: d.shell, sx: at.x, sy: at.y, w: self.model.w, d: self.model.d, moved: false, t0: { ...v.lastTransform } };
        } else if (d.wall !== undefined) {
          const wall = wallList()[Number(d.wall)];
          v.selected.wall = wall.index; v.selected.wallAxis = wall.axis; v.selected.room = null;
          drag = { type: 'wall', wall, others: others(wall), moved: false, origin: wall.at, sx: at.x, sy: at.y };
          self.draw();
          self.listeners.forEach((fn) => fn({ selection: true }));
        } else if (d.opend) {
          const op = self.model.openings.find((o) => o.id === v.selected.opening);
          drag = { type: 'opend', op, dir: Number(d.opend), moved: false };
        } else if (d.op) {
          v.selected.opening = d.op;
          const op = self.model.openings.find((o) => o.id === d.op);
          drag = { type: 'op', op, moved: false, grab: op.pos - ((op.side === 'N' || op.side === 'S') ? at.x : at.y) };
          self.draw();
          self.listeners.forEach((fn) => fn({ selection: true }));
        } else if (d.addwall) {
          const side = d.addwall; const pos = (side === 'N' || side === 'S') ? at.x : at.y;
          const op = M().addOpening(self.model, v.level, side, pos, v.addKind);
          if (op) v.selected.opening = op.id;
          self.confirm('openings');
          self.update();
          v.transform = null;
          return;
        } else if (d.cut) {
          drag = { type: 'cut' };
        } else if (d.room) {
          if (v.tool === 'rooms' && v.splitting && v.preview) {
            const p = v.preview;
            const fresh = M().splitRoom(self.model, v.level, p.room, p.axis, p.at);
            v.preview = null;
            if (fresh) { fresh.name = 'Room ' + (M().roomsOf(self.model, v.level).length); self.confirm('rooms'); v.selected.room = fresh.id; }
            self.update();
          } else {
            v.selected.wall = null; v.selected.opening = null;
            self.selectRoom(d.room);
          }
          v.transform = null;
          return;
        } else { v.selected.opening = null; v.transform = null; self.draw(); return; }
        svg.setPointerCapture(e.pointerId);
        e.preventDefault();
      });
      svg.addEventListener('pointermove', (e) => {
        const at = toFeet(e);
        if (!drag) {
          if (v.tool === 'rooms' && v.splitting) {
            const rooms = M().roomsOf(self.model, v.level);
            const r = rooms.find((x) => at.x >= x.x && at.x <= x.x + x.w && at.y >= x.y && at.y <= x.y + x.h);
            let preview = null;
            if (r) {
              // The wall runs across the room's nearer pair of edges.
              const dx = Math.min(at.x - r.x, r.x + r.w - at.x) / r.w; const dy = Math.min(at.y - r.y, r.y + r.h - at.y) / r.h;
              const axis = dx < dy ? 'v' : 'h';
              const [pos, len, cross, crossLen, value] = axis === 'v' ? ['x', 'w', 'y', 'h', at.x] : ['y', 'h', 'x', 'w', at.y];
              if (r[len] >= M().MIN_ROOM * 2) {
                const cut = Math.max(r[pos] + M().MIN_ROOM, Math.min(r[pos] + r[len] - M().MIN_ROOM, M().snap(value)));
                preview = { room: r.id, axis, at: cut, start: r[cross], end: r[cross] + r[crossLen] };
              }
            }
            const old = v.preview;
            if (JSON.stringify(old) !== JSON.stringify(preview)) { v.preview = preview; v.liveText = preview ? `${D().feet(preview.at - (preview.axis === 'v' ? r.x : r.y))} | ${D().feet((preview.axis === 'v' ? r.x + r.w : r.y + r.h) - preview.at)}` : null; self.draw(); }
          }
          return;
        }
        drag.moved = true;
        if (drag.type === 'shell') {
          const m = self.model; const p0 = toFeet(e, drag.t0); const t0 = drag.t0;
          const before = { w: m.w, d: m.d };
          if (drag.side === 'E') M().moveShell(m, 'E', drag.w + (p0.x - drag.sx));
          if (drag.side === 'S') M().moveShell(m, 'S', drag.d + (p0.y - drag.sy));
          if (drag.side === 'W') M().moveShell(m, 'W', m.w - (drag.w - (p0.x - drag.sx)));
          if (drag.side === 'N') M().moveShell(m, 'N', m.d - (drag.d - (p0.y - drag.sy)));
          // The far wall stays still on screen, and the dragged wall follows the pointer.
          if (drag.side === 'W') { v.transform = { ...t0, ox: t0.ox - (m.w - drag.w) * t0.scale }; if (v.cut.axis === 'x') v.cut.at += m.w - before.w; }
          if (drag.side === 'N') { v.transform = { ...t0, oy: t0.oy - (m.d - drag.d) * t0.scale }; if (v.cut.axis === 'y') v.cut.at += m.d - before.d; }
          self.confirm('shape');
          v.liveText = `${D().feet(m.w)} × ${D().feet(m.d)}   ${fmt(M().area(m))} ft²`;
          if (v.cut.axis === 'x') v.cut.at = Math.min(v.cut.at, m.w - 0.5); else v.cut.at = Math.min(v.cut.at, m.d - 0.5);
        } else if (drag.type === 'wall') {
          const value = drag.wall.axis === 'v' ? at.x : at.y;
          // Rooms move as the wall moves, so wall limits stay current through the drag.
          const fresh = wallList().find((w) => w.axis === drag.wall.axis && w.ids.join() === drag.wall.ids.join()) || drag.wall;
          const out = M().moveWall(self.model, v.level, fresh, value, drag.others);
          drag.wall = fresh;
          v.guide = out.guide; v.guideAxis = out.guide !== null ? fresh.axis : null;
          const a = fresh.a[0]; const b = fresh.b[0];
          v.liveText = `${a.name} ${fmt(a.w * a.h)} ft²  |  ${b.name} ${fmt(b.w * b.h)} ft²`;
        } else if (drag.type === 'op') {
          const op = drag.op; const pos = (op.side === 'N' || op.side === 'S') ? at.x : at.y;
          M().moveOpening(self.model, op, pos + drag.grab);
          self.confirm('openings');
        } else if (drag.type === 'opend') {
          const op = drag.op; const pos = (op.side === 'N' || op.side === 'S') ? at.x : at.y;
          const fixed = op.pos - drag.dir * op.width / 2;
          M().resizeOpening(self.model, op, Math.abs(pos - fixed), drag.dir);
          self.confirm('openings');
          v.liveText = `${D().feet(op.width)} wide`;
        } else if (drag.type === 'cut') {
          const span = v.cut.axis === 'x' ? self.model.w : self.model.d;
          v.cut.at = Math.max(0.5, Math.min(span - 0.5, M().snap(v.cut.axis === 'x' ? at.x : at.y)));
          self.draw();
          return;
        }
        refresh();
      });
      const finish = () => {
        if (!drag) return;
        const moved = drag.moved;
        drag = null; v.guide = null; v.guideAxis = null; v.liveText = null; v.transform = null;
        if (moved) self.update(); else self.draw();
      };
      svg.addEventListener('pointerup', finish);
      svg.addEventListener('pointercancel', finish);
      svg.addEventListener('pointerleave', () => { if (!drag && v.preview) { v.preview = null; v.liveText = null; self.draw(); } });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && v.splitting) { v.splitting = false; v.preview = null; v.liveText = null; self.draw(); self.listeners.forEach((fn) => fn({ selection: true })); }
        const tag = (e.target.tagName || '').toLowerCase();
        if ((e.key === 'Delete' || e.key === 'Backspace') && v.selected.opening && tag !== 'input' && tag !== 'select') {
          M().removeOpening(self.model, v.selected.opening); v.selected.opening = null; self.confirm('openings'); self.update();
        }
        const step = { ArrowLeft: -0.5, ArrowRight: 0.5, ArrowUp: -0.5, ArrowDown: 0.5 }[e.key];
        if (step === undefined || !e.target.dataset) return;
        const d = e.target.dataset;
        if (d.wall !== undefined) {
          const wall = wallList()[Number(d.wall)];
          M().moveWall(self.model, v.level, wall, wall.at + step); e.preventDefault(); self.update();
          const again = svg.querySelector(`[data-wall="${d.wall}"]`); if (again) again.focus();
        } else if (d.shell) {
          const m = self.model; const s = d.shell;
          if (s === 'E') M().moveShell(m, 'E', m.w + step);
          if (s === 'S') M().moveShell(m, 'S', m.d + step);
          if (s === 'W') M().moveShell(m, 'W', step);
          if (s === 'N') M().moveShell(m, 'N', step);
          self.confirm('shape'); e.preventDefault(); self.update();
          const again = svg.querySelector(`[data-shell="${s}"]`); if (again) again.focus();
        } else if (d.cut) {
          v.cut.at += step; e.preventDefault(); self.draw();
          const again = svg.querySelector('[data-cut]'); if (again) again.focus();
        }
      });
    },

    // ---------------------------------------------------------------- inspectors
    field(key, label, value, opts = {}) {
      if (opts.options) return `<div class="fld"><label for="f-${key}">${esc(label)}</label><select id="f-${key}" data-set="${key}">${opts.options.map(([v, t]) => `<option value="${esc(v)}"${String(v) === String(value) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select>${opts.help ? `<div class="help">${esc(opts.help)}</div>` : ''}</div>`;
      return `<div class="fld"><label for="f-${key}">${esc(label)}${opts.unit ? `<span>${esc(opts.unit)}</span>` : ''}</label><input id="f-${key}" data-set="${key}" type="${opts.text ? 'text' : 'number'}" step="any" value="${esc(value ?? '')}"${opts.placeholder ? ` placeholder="${esc(opts.placeholder)}"` : ''}>${opts.help ? `<div class="help">${esc(opts.help)}</div>` : ''}</div>`;
    },
    elementHtml(id) {
      const s = P().state; const f = s.fields; const pre = P().presets; const era = pre.eras[s.era]; const m = this.model; const v = this.view;
      const opts = (table) => Object.entries(table).map(([k, x]) => [k, x.label]);
      const field = this.field.bind(this);
      const deeper = (title, body) => `<details class="deeper"><summary>${esc(title)}</summary><div class="deeper-body">${body}</div></details>`;
      switch (id) {
        case 'site': {
          const st = P().station;
          return field('zip', 'ZIP code', s.zip, { text: true, help: st ? `Using ${st.n}${st.s ? ', ' + st.s : ''}: ${fmt(st.h99)} °F in winter and ${fmt(st.c1)} °F in summer, from ${st.yrs} years of NOAA hourly data.` : '' })
            + deeper('Change the design weather', `<div class="two">${field('heating_design_f', 'Winter design', f.heating_design_f ?? (st ? st.h99 : ''), { unit: '°F' })}${field('cooling_design_f', 'Summer design', f.cooling_design_f ?? (st ? st.c1 : ''), { unit: '°F' })}</div>${field('design_basis', 'Winter basis', f.design_basis || '99', { options: [['99', '99%, standard'], ['99.6', '99.6%, colder']], help: st ? `The colder 99.6% value here is ${fmt(st.h996)} °F. Consider it for a heat pump.` : '' })}`);
        }
        case 'shape':
          return `${field('area', 'Floor area', Math.round(M().area(m)), { unit: 'ft²', help: 'Or drag the outside walls on the plan.' })}
            <div class="two">${field('m_w', 'Length', m.w, { unit: 'ft' })}${field('m_d', 'Width', m.d, { unit: 'ft' })}</div>
            <div class="two">${field('stories', 'Stories', m.stories, { options: [[1, '1'], [2, '2'], [3, '3']] })}${field('height', 'Floor to floor', m.height, { unit: 'ft' })}</div>
            ${field('era', 'When was it built?', this.eraConfirmed ? s.era : '', { options: [['', 'Choose one'], ...opts(pre.eras)], help: 'This one answer sets typical insulation, windows, and leakage, and shrinks the range more than anything else so far.' })}
            ${field('floor_type', 'Foundation', s.floor_type, { options: [['slab', 'Slab on grade'], ['crawl_vented', 'Vented crawlspace'], ['crawl_sealed', 'Sealed crawlspace'], ['basement_conditioned', 'Heated basement'], ['basement_unconditioned', 'Unheated basement']] })}`;
        case 'walls': {
          const u = this.detailWallU();
          return `${field('wall_preset', 'Wall type', f.wall_preset || era.wall_preset, { options: opts(pre.walls), help: `Whole-wall U-factor ${fmt(u, 3)}, about R-${fmt(1 / u, 1)} once framing is counted.` })}
            ${field('wall_absorptance', 'Exterior color', f.wall_absorptance ?? 0.6, { options: [[0.4, 'Light'], [0.6, 'Medium'], [0.9, 'Dark']] })}
            ${deeper('Build it from layers', `<div class="two">${field('cavity_r', 'Cavity insulation', f.cavity_r ?? '', { unit: 'R', placeholder: '13' })}${field('stud', 'Framing', f.stud ?? 4.4, { options: [[4.4, '2x4'], [6.9, '2x6']] })}</div><div class="two">${field('framing', 'Framing share', f.framing ?? 25, { unit: '%' })}${field('cont_r', 'Continuous foam', f.cont_r ?? 0, { unit: 'R' })}</div>${f.layer_u ? `<p class="note">Parallel path result: U ${fmt(f.layer_u, 3)}, whole-wall R-${fmt(1 / f.layer_u, 1)}. Studs bypass the insulation, so this is well below the label.</p>` : '<p class="note">Enter cavity insulation to calculate the wall from its layers.</p>'}`)}`;
        }
        case 'ceiling':
          return `${field('ceiling_preset', 'Ceiling insulation', f.ceiling_preset || era.ceiling_preset, { options: opts(pre.ceilings) })}
            ${field('roof_color', 'Roof surface', f.roof_color || 'medium', { options: [['white', 'White'], ['light', 'Light'], ['medium', 'Medium'], ['dark', 'Dark']], help: 'Changes how hot the attic gets, which the section shows in summer.' })}
            ${deeper('Attic details', `${field('ceiling_type', 'Ceiling type', f.ceiling_type || 'attic', { options: [['attic', 'Under a vented attic'], ['cathedral', 'Cathedral or flat roof']] })}${field('radiant_barrier', 'Radiant barrier', String(f.radiant_barrier || false), { options: [['false', 'No'], ['true', 'Yes']] })}${field('attic_vent_cfm_per_ft2', 'Attic ventilation', f.attic_vent_cfm_per_ft2 ?? 0.3, { unit: 'cfm/ft²' })}`)}`;
        case 'floor': {
          const t = s.floor_type;
          if (t === 'slab') return `${field('slab_edge', 'Slab edge insulation', f.slab_edge || era.slab_edge, { options: [['none', 'None'], ['r5', 'R-5'], ['r10', 'R-10'], ['r15', 'R-15']], help: 'A slab loses most of its heat at the edge, so the perimeter matters more than the area.' })}${field('floor_cover', 'Floor covering', f.floor_cover || 'carpet', { options: [['carpet', 'Mostly carpet'], ['hard', 'Mostly hard floor']] })}`;
          if (t.startsWith('basement')) return `<div class="two">${field('basement_depth_ft', 'Depth below grade', f.basement_depth_ft ?? 7, { unit: 'ft' })}${field('basement_wall_r', 'Wall insulation', f.basement_wall_r ?? 0, { unit: 'R' })}</div>${t === 'basement_unconditioned' ? field('floor_u', 'Floor U-factor', f.floor_u ?? 0.05) : ''}`;
          return `${field('floor_u', 'Floor U-factor', f.floor_u ?? 0.05, { help: 'R-19 between joists is about U 0.05. An uninsulated floor is about U 0.25.' })}${t === 'crawl_sealed' ? field('crawl_wall_r', 'Crawlspace wall insulation', f.crawl_wall_r ?? 10, { unit: 'R' }) : ''}`;
        }
        case 'openings': {
          const op = m.openings.find((o) => o.id === v.selected.opening);
          return `<div class="dwg-tabs" role="group" aria-label="What to add" style="margin-bottom:8px"><button type="button" data-addkind="window" class="${v.addKind === 'window' ? 'on' : ''}">Add window</button><button type="button" data-addkind="door" class="${v.addKind === 'door' ? 'on' : ''}">Add door</button></div>
            ${op ? `<div class="sel-box"><strong>Selected ${esc(op.kind)}</strong>, ${esc(op.side)} wall<div class="two">${field('op_width', 'Width', op.width, { unit: 'ft' })}${field('op_height', 'Height', op.height, { unit: 'ft' })}</div><button type="button" class="btn" data-remove-op>Remove</button></div>` : '<p class="note">Select a window on the plan to change it.</p>'}
            ${field('window_preset', 'Window type', f.window_preset || era.window_preset, { options: opts(pre.windows) })}
            <div class="two">${field('rotation', 'Rotate house', v.rotation, { unit: 'degrees', help: '' })}${field('overhang_depth_ft', 'Eave overhang', f.overhang_depth_ft ?? 1, { unit: 'ft' })}</div>
            ${deeper('Shading and the rating label', `<div class="two">${field('window_u', 'U-factor', f.window_u ?? pre.windows[f.window_preset || era.window_preset].u)}${field('window_shgc', 'SHGC', f.window_shgc ?? pre.windows[f.window_preset || era.window_preset].shgc)}</div>${field('interior_shade', 'Interior shades', f.interior_shade || 'drapes_half', { options: [['none', 'None'], ['light_blinds_half', 'Light blinds, half closed'], ['drapes_half', 'Drapes, half closed'], ['blinds_closed', 'Blinds, closed'], ['cellular_closed', 'Cellular shades, closed']] })}${field('insect_screen', 'Insect screens', f.insect_screen || 'half', { options: [['none', 'None'], ['half', 'On half the windows'], ['full', 'On all windows']] })}${field('site_shade_fraction', 'Sun blocked by trees', f.site_shade_fraction ?? 0, { help: 'A fraction from 0 to 1.' })}`)}`;
        }
        case 'air': {
          const a = f.ach50 ?? era.ach50;
          const pickBand = a <= 3.5 ? 3 : a <= 6 ? 5 : a <= 9 ? 7 : a <= 13 ? 10 : 15;
          return `${field('air_quick', 'How tight does it feel?', f.air_measured ? '' : pickBand, { options: [...(f.air_measured ? [['', 'Using your test result']] : []), [3, 'Very tight, new construction'], [5, 'Fairly tight'], [7, 'Typical'], [10, 'Drafty'], [15, 'Very drafty, older house']], help: 'A guess, and the range on your answer stays wide until it is measured.' })}
            ${deeper('I have a blower door result', `${field('ach50', 'Air changes at 50 Pa', f.air_measured ? f.ach50 : '', { unit: 'ACH50', placeholder: String(a) })}<p class="note">An energy auditor measures this in about an hour. Few other inputs narrow the answer as much in an older house.</p>`)}
            ${deeper('Mechanical ventilation', `${field('ventilation_type', 'Type', f.ventilation_type || 'none', { options: [['none', 'None'], ['exhaust', 'Exhaust fan, continuous'], ['supply', 'Supply fan, continuous'], ['balanced', 'Balanced, no recovery'], ['hrv', 'HRV'], ['erv', 'ERV']] })}${field('ventilation_cfm', 'Flow', f.ventilation_cfm ?? 0, { unit: 'cfm' })}`)}`;
        }
        case 'ducts': {
          const sys = P().SYSTEMS[s.system];
          if (!sys.ducted) return '<p class="note">Ductless systems have no duct losses, so there is nothing to enter here.</p>';
          return `${field('duct_location', 'Where do the ducts run?', f.duct_location || 'attic', { options: [['attic', 'Attic'], ['conditioned', 'Inside conditioned space'], ['vented_crawl', 'Vented crawlspace'], ['sealed_crawl', 'Sealed crawlspace'], ['basement', 'Basement'], ['garage', 'Garage']], help: 'Watch the section as you change this.' })}
            ${deeper('Insulation and tested leakage', `<div class="two">${field('duct_r', 'Insulation', f.duct_r ?? era.duct_r, { unit: 'R' })}${field('duct_leakage_pct', 'Leakage per side', f.duct_leakage_pct ?? era.duct_leakage_pct, { unit: '%' })}</div>`)}`;
        }
        case 'rooms': {
          const room = M().roomsOf(m, v.level).find((r) => r.id === v.selected.room);
          const wall = v.selected.wall !== null ? M().interiorWalls(m, v.level).find((w) => w.index === v.selected.wall && w.axis === v.selected.wallAxis) : null;
          const rows = this.result ? this.result.rooms : [];
          let i = 0; const lookup = {};
          m.levels.forEach((lvl) => lvl.rooms.forEach((r) => { lookup[r.id] = rows[i]; i += 1; }));
          const row = room && lookup[room.id];
          return `<div class="room-buttons"><button type="button" class="btn ${v.splitting ? 'active' : ''}" data-split>${v.splitting ? 'Adding walls. Click a room' : 'Add a wall'}</button><button type="button" class="btn" data-typical>Typical layout</button></div>
            ${room ? `<div class="sel-box">${field('room_name', 'Room', room.name, { text: true })}${field('room_type', 'Used as', room.type, { options: [['living', 'Living'], ['kitchen', 'Kitchen'], ['bedroom', 'Bedroom'], ['bath', 'Bathroom'], ['office', 'Office'], ['other', 'Other']], help: 'Kitchens and living rooms carry more of the internal gains.' })}
              ${row ? `<table class="vars"><tbody><tr><td>Heating</td><td class="v">${fmt(row.heating)}</td><td class="u">Btu/h</td></tr><tr><td>Cooling, peak hour ${row.peak_hour}</td><td class="v">${fmt(row.cooling)}</td><td class="u">Btu/h</td></tr><tr><td>Supply air, heating</td><td class="v">${fmt(row.heating_cfm)}</td><td class="u">cfm</td></tr><tr><td>Supply air, cooling</td><td class="v">${fmt(row.cooling_cfm)}</td><td class="u">cfm</td></tr></tbody></table>` : ''}</div>` : '<p class="note">Select a room or drag a wall.</p>'}
            ${wall ? `<div class="sel-box"><strong>Selected wall</strong> ${M().canRemoveWall(wall) ? '<button type="button" class="btn" data-remove-wall>Remove this wall</button>' : '<p class="note" style="margin:4px 0 0">This wall meets several rooms, so removing it would not leave rectangles.</p>'}</div>` : ''}`;
        }
        default: return '';
      }
    },
    detailWallU() {
      const inp = P().inputs();
      return inp.wall_u;
    },
    bindInspector(root) {
      const self = this;
      root.addEventListener('change', (e) => self.applyField(e));
      root.addEventListener('click', (e) => {
        const b = e.target.closest('button'); if (!b) return;
        const v = self.view; const m = self.model;
        if (b.dataset.addkind) { v.addKind = b.dataset.addkind; self.update({ band: false }); }
        if (b.dataset.removeOp !== undefined) { M().removeOpening(m, v.selected.opening); v.selected.opening = null; self.confirm('openings'); self.update(); }
        if (b.dataset.split !== undefined) { v.splitting = !v.splitting; v.preview = null; self.update({ band: false }); }
        if (b.dataset.removeWall !== undefined) {
          const wall = M().interiorWalls(m, v.level).find((w) => w.index === v.selected.wall && w.axis === v.selected.wallAxis);
          if (wall) { M().removeWall(m, v.level, wall); v.selected.wall = null; v.selected.wallAxis = null; self.update(); }
        }
        if (b.dataset.typical !== undefined) { self.typicalLayout(); self.confirm('rooms'); v.splitting = false; self.update(); }
      });
    },
    typicalLayout() {
      const m = this.model;
      m.levels.forEach((lvl, level) => {
        lvl.rooms = [{ id: 'r' + Math.random().toString(36).slice(2), name: 'x', type: 'other', x: 0, y: 0, w: m.w, h: m.d }];
        const whole = lvl.rooms[0];
        const split = (room, axis, frac) => M().splitRoom(m, level, room.id, axis, axis === 'v' ? room.x + room.w * frac : room.y + room.h * frac);
        const set = (r, name, type) => { r.name = name; r.type = type; };
        if (level === 0 && m.stories === 1) {
          const bottom = split(whole, 'h', .58);
          const right = split(whole, 'v', .55);
          set(whole, 'Living room', 'living');
          const lowerRight = split(right, 'h', .66);
          set(right, 'Kitchen', 'kitchen');
          const hall = split(lowerRight, 'v', .45); set(lowerRight, 'Bath', 'bath'); set(hall, 'Hall', 'other');
          const b2 = split(bottom, 'v', .4); set(bottom, 'Primary bedroom', 'bedroom');
          const b3 = split(b2, 'v', .5); set(b2, 'Bedroom 2', 'bedroom'); set(b3, 'Bedroom 3', 'bedroom');
        } else if (level === 0) {
          const bottom = split(whole, 'h', .6);
          const right = split(whole, 'v', .6); set(whole, 'Living room', 'living'); set(right, 'Kitchen', 'kitchen');
          const entry = split(bottom, 'v', .5); set(bottom, 'Dining', 'other'); set(entry, 'Entry', 'other');
        } else {
          const bottom = split(whole, 'h', .55);
          const b2 = split(whole, 'v', .5); set(whole, 'Primary bedroom', 'bedroom'); set(b2, 'Bedroom 2', 'bedroom');
          const bath = split(bottom, 'v', .42); set(bottom, 'Bedroom 3', 'bedroom');
          const hall = split(bath, 'v', .4); set(bath, 'Bath', 'bath'); set(hall, 'Hall', 'other');
        }
      });
      this.view.selected.room = null;
    },
    async applyField(e) {
      const key = e.target.dataset ? e.target.dataset.set : null;
      if (!key) return;
      const raw = e.target.value; const num = Number(raw); const s = P().state; const f = s.fields; const m = this.model; const v = this.view;
      const owner = { zip: 'site', heating_design_f: 'site', cooling_design_f: 'site', design_basis: 'site', area: 'shape', m_w: 'shape', m_d: 'shape', stories: 'shape', height: 'shape', era: 'shape', floor_type: 'floor', wall_preset: 'walls', wall_absorptance: 'walls', cavity_r: 'walls', stud: 'walls', framing: 'walls', cont_r: 'walls', ceiling_preset: 'ceiling', roof_color: 'ceiling', ceiling_type: 'ceiling', radiant_barrier: 'ceiling', attic_vent_cfm_per_ft2: 'ceiling', slab_edge: 'floor', floor_cover: 'floor', floor_u: 'floor', basement_depth_ft: 'floor', basement_wall_r: 'floor', crawl_wall_r: 'floor', window_preset: 'openings', window_u: 'openings', window_shgc: 'openings', overhang_depth_ft: 'openings', interior_shade: 'openings', insect_screen: 'openings', site_shade_fraction: 'openings', rotation: 'openings', op_width: 'openings', op_height: 'openings', air_quick: null, ach50: 'air', ventilation_type: 'air', ventilation_cfm: 'air', duct_location: 'ducts', duct_r: 'ducts', duct_leakage_pct: 'ducts', room_name: 'rooms', room_type: 'rooms' }[key];
      switch (key) {
        case 'zip': s.zip = raw.trim(); await P().locate(s.zip); ['heating_design_f', 'cooling_design_f'].forEach((k) => delete f[k]); break;
        case 'design_basis': { f.design_basis = raw; const st = P().station; if (st) f.heating_design_f = raw === '99.6' ? st.h996 : st.h99; break; }
        case 'area': if (num > 0) M().scaleToArea(m, num); break;
        case 'm_w': if (num > 0) M().moveShell(m, 'E', num); break;
        case 'm_d': if (num > 0) M().moveShell(m, 'S', num); break;
        case 'stories': M().setStories(m, Number(raw)); v.level = Math.min(v.level, m.stories - 1); this.applyLayout(); break;
        case 'height': if (num > 0) m.height = num; break;
        case 'era': if (raw) { s.era = raw; this.eraConfirmed = true; ['wall_preset', 'ceiling_preset', 'window_preset', 'ach50', 'duct_leakage_pct', 'duct_r', 'slab_edge', 'wall_u', 'layer_u'].forEach((k) => delete f[k]); ['walls', 'ceiling', 'floor', 'air', 'ducts'].forEach((id) => { this.confirmed.delete(id); (ELEMENTS[id].known || []).forEach((k) => s.known.delete(k)); }); } break;
        case 'floor_type': s.floor_type = raw; break;
        case 'rotation': v.rotation = (num % 360 + 360) % 360; break;
        case 'radiant_barrier': f.radiant_barrier = raw === 'true'; break;
        case 'air_quick': if (raw) { f.ach50 = num; delete f.air_measured; this.confirmed.delete('air'); s.known.delete('ach50'); } break;
        case 'ach50': if (raw !== '') { f.ach50 = num; f.air_measured = true; } else { delete f.ach50; delete f.air_measured; } break;
        case 'op_width': { const op = m.openings.find((o) => o.id === v.selected.opening); if (op && num > 0) M().resizeOpening(m, op, num, 0); break; }
        case 'op_height': { const op = m.openings.find((o) => o.id === v.selected.opening); if (op && num > 0) op.height = num; break; }
        case 'room_name': { const r = M().roomsOf(m, v.level).find((x) => x.id === v.selected.room); if (r) r.name = raw; break; }
        case 'room_type': { const r = M().roomsOf(m, v.level).find((x) => x.id === v.selected.room); if (r) r.type = raw; break; }
        case 'cavity_r': case 'stud': case 'framing': case 'cont_r': {
          f[key] = raw === '' ? '' : num;
          if (f.cavity_r !== '' && f.cavity_r !== undefined) {
            const out = P().call('assembly_u', { cavity_r: f.cavity_r, framing_fraction: (f.framing ?? 25) / 100, continuous_r: f.cont_r ?? 0, stud_r: f.stud ?? 4.4 });
            f.layer_u = out.u_value; f.wall_u = out.u_value;
          }
          break;
        }
        case 'wall_preset': delete f.wall_u; delete f.layer_u; f[key] = raw; break;
        case 'wall_absorptance': case 'overhang_depth_ft': case 'site_shade_fraction': case 'heating_design_f': case 'cooling_design_f': case 'attic_vent_cfm_per_ft2': case 'floor_u': case 'basement_depth_ft': case 'basement_wall_r': case 'crawl_wall_r': case 'window_u': case 'window_shgc': case 'ventilation_cfm': case 'duct_r': case 'duct_leakage_pct':
          if (raw === '') delete f[key]; else f[key] = num; break;
        default: f[key] = raw;
      }
      if (owner && !(key === 'era')) this.confirm(owner);
      if (key === 'era' && raw) this.confirmed.add('shape');
      const wasScaled = ['area', 'm_w', 'm_d', 'stories'].includes(key);
      if (wasScaled) { this.confirm('shape'); const span = v.cut.axis === 'x' ? m.w : m.d; v.cut.at = Math.min(v.cut.at, span - .5); }
      this.update();
    },
    recordHistory(stepId) {
      if (!this.result || !this.band) return;
      this.history[stepId] = {
        heat: [this.band.heating_low, this.result.heating_total, this.band.heating_high],
        cool: [this.band.cooling_low, this.result.cooling_total, this.band.cooling_high],
      };
    },
    fmt, esc,
  };
  window.Core = Core;
})();
