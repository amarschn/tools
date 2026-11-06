/* The house as one geometric model. Plan, section, and 3D are projections of it.
   Rooms always tile the rectangular shell: walls move, rooms follow, so gaps and
   overlaps cannot occur. No DOM here, so tests/browser/hvac-model.cjs can fuzz it. */
(function (root) {
  'use strict';
  const MIN_ROOM = 4;     // ft
  const MIN_SHELL = 10;   // ft
  const SNAP = 0.5;       // ft
  const snap = (v) => Math.round(v / SNAP) * SNAP;
  let nextId = 1;
  const id = (p) => `${p}${nextId++}`;

  function create({ area = 2000, aspect = 1.5, stories = 1, height = 8 } = {}) {
    const footprint = area / stories;
    const w = snap(Math.sqrt(footprint * aspect));
    const d = snap(footprint / w);
    const model = { w, d, height, stories, levels: [], openings: [], openingsConfirmed: false, windowPct: 14 };
    for (let l = 0; l < stories; l++) model.levels.push({ rooms: [wholeFloor(model, l)] });
    autoOpenings(model);
    return model;
  }
  function wholeFloor(model, level) {
    const name = model.stories === 1 ? 'Whole house' : `Level ${level + 1}`;
    return { id: id('r'), name, type: 'other', x: 0, y: 0, w: model.w, h: model.d };
  }
  const roomsOf = (model, level) => model.levels[level].rooms;
  const area = (model) => model.levels.reduce((sum, lvl) => sum + lvl.rooms.reduce((a, r) => a + r.w * r.h, 0), 0);
  const sideLength = (model, side) => (side === 'N' || side === 'S' ? model.w : model.d);

  // Assumed windows: a typical share of floor area, evenly spread. Drawn dashed until confirmed.
  function autoOpenings(model) {
    if (model.openingsConfirmed) { clampOpenings(model); return; }
    model.openings = [];
    const total = model.windowPct / 100 * area(model);
    const perimeter = 2 * (model.w + model.d);
    for (let level = 0; level < model.stories; level++) {
      ['N', 'E', 'S', 'W'].forEach((side) => {
        const len = sideLength(model, side);
        const glass = total * len / perimeter / model.stories;
        const count = Math.max(1, Math.round(glass / 15));
        const width = Math.min(snap(glass / count / 5), snap(len / count * 0.7));
        if (width < 1) return;
        for (let i = 0; i < count; i++) {
          model.openings.push({ id: id('o'), level, side, kind: 'window', pos: snap(len * (i + 0.5) / count), width, height: 5, assumed: true });
        }
      });
    }
    const doors = [
      { id: id('o'), level: 0, side: 'S', kind: 'door', pos: snap(model.w * 0.5), width: 3, height: 6.67, assumed: true },
      { id: id('o'), level: 0, side: 'N', kind: 'door', pos: snap(model.w * 0.5), width: 3, height: 6.67, assumed: true },
    ];
    // A window that would sit on a door moves aside, or gives way if the wall is short.
    doors.forEach((door) => {
      model.openings.filter((o) => o.level === 0 && o.side === door.side).forEach((o) => {
        if (Math.abs(o.pos - door.pos) < (o.width + door.width) / 2 + 0.5) o.pos = door.pos + (o.pos >= door.pos ? 1 : -1) * ((o.width + door.width) / 2 + 0.5);
      });
      model.openings.push(door);
    });
    clampOpenings(model);
  }
  /** Keep every wall's openings inside the wall and apart, dropping any that cannot fit. */
  function clampOpenings(model) {
    model.openings = model.openings.filter((o) => o.level < model.stories);
    const walls = new Map();
    model.openings.forEach((o) => {
      const key = `${o.level}${o.side}`;
      if (!walls.has(key)) walls.set(key, []);
      walls.get(key).push(o);
    });
    const keep = new Set();
    walls.forEach((list) => {
      const len = sideLength(model, list[0].side); const end = len - 0.25; const gap = 0.5;
      list.sort((a, b) => a.pos - b.pos);
      // Drop the narrowest openings until the rest fit with gaps between them.
      const fits = (items) => items.reduce((a, o) => a + o.width, 0) + gap * Math.max(items.length - 1, 0) <= end - 0.25;
      let items = list.map((o) => { o.width = Math.max(1, Math.min(o.width, len - 1)); return o; });
      while (items.length && !fits(items)) {
        const narrow = items.reduce((m, o) => (o.width < m.width ? o : m));
        items = items.filter((o) => o !== narrow);
      }
      // Sweep right, then left, so each keeps its place where it can.
      let edge = 0.25;
      items.forEach((o) => { o.pos = Math.max(o.pos, edge + o.width / 2); edge = o.pos + o.width / 2 + gap; });
      edge = end;
      items.slice().reverse().forEach((o) => { o.pos = Math.min(o.pos, edge - o.width / 2); edge = o.pos - o.width / 2 - gap; });
      items.forEach((o) => keep.add(o));
    });
    model.openings = model.openings.filter((o) => keep.has(o));
  }
  function confirmOpenings(model) {
    model.openingsConfirmed = true;
    model.openings.forEach((o) => { o.assumed = false; });
  }

  function setStories(model, stories) {
    while (model.levels.length < stories) {
      const copy = model.levels[model.levels.length - 1].rooms.map((r) => ({ ...r, id: id('r') }));
      model.levels.push({ rooms: copy });
    }
    model.levels.length = stories;
    model.stories = stories;
    if (model.levels.every((l) => l.rooms.length === 1)) model.levels.forEach((l, i) => { l.rooms[0].name = stories === 1 ? 'Whole house' : `Level ${i + 1}`; });
    autoOpenings(model);
  }

  // ---------------------------------------------------------------- shell
  function minShell(model, axis) {
    // The shell cannot shrink past the rooms along that axis at their minimum size.
    let need = MIN_SHELL;
    model.levels.forEach((lvl) => {
      const cuts = new Set(lvl.rooms.map((r) => (axis === 'w' ? r.x : r.y)));
      const columns = cuts.size;
      need = Math.max(need, columns * MIN_ROOM);
    });
    return need;
  }
  /** Move one side of the building to a new coordinate. The far side stays put. */
  function moveShell(model, side, value) {
    const v = snap(value);
    if (side === 'E' || side === 'S') {
      const key = side === 'E' ? 'w' : 'd';
      const pos = side === 'E' ? 'x' : 'y';
      const len = side === 'E' ? 'w' : 'h';
      let lowest = MIN_SHELL;
      model.levels.forEach((lvl) => lvl.rooms.forEach((r) => { if (r[pos] + r[len] === model[key]) lowest = Math.max(lowest, r[pos] + MIN_ROOM); }));
      const next = Math.max(lowest, Math.min(120, v));
      model.levels.forEach((lvl) => lvl.rooms.forEach((r) => { if (r[pos] + r[len] === model[key]) r[len] = next - r[pos]; }));
      model[key] = next;
    } else {
      const key = side === 'W' ? 'w' : 'd';
      const pos = side === 'W' ? 'x' : 'y';
      const len = side === 'W' ? 'w' : 'h';
      let highest = model[key] - MIN_SHELL;
      model.levels.forEach((lvl) => lvl.rooms.forEach((r) => { if (r[pos] === 0) highest = Math.min(highest, r[len] - MIN_ROOM); }));
      const shift = -Math.max(-(120 - model[key]), Math.min(highest, v)); // positive grows the house
      if (shift !== 0) {
        model.levels.forEach((lvl) => lvl.rooms.forEach((r) => {
          if (r[pos] === 0) r[len] += shift; else r[pos] += shift;
        }));
        model[key] += shift;
        model.openings.forEach((o) => {
          const along = side === 'W' ? (o.side === 'N' || o.side === 'S') : (o.side === 'E' || o.side === 'W');
          if (along) o.pos += shift;
        });
      }
    }
    autoOpenings(model);
  }
  /** Map every wall position through one rising function, so rooms stay tiled at any scale. */
  function scaledCuts(model, pos, len, size, factor) {
    const cuts = new Set([0, model[size]]);
    model.levels.forEach((lvl) => lvl.rooms.forEach((r) => { cuts.add(r[pos]); cuts.add(r[pos] + r[len]); }));
    const sorted = [...cuts].sort((a, b) => a - b);
    const map = new Map([[0, 0]]);
    let previous = 0;
    sorted.slice(1).forEach((cut) => {
      const next = Math.max(snap(cut * factor), previous + MIN_ROOM);
      map.set(cut, next);
      previous = next;
    });
    return map;
  }
  /** Scale the whole plan to a new floor area, keeping its proportions. */
  function scaleToArea(model, target) {
    const k = Math.sqrt(target / Math.max(area(model), 1));
    const oldW = model.w; const oldD = model.d;
    const xs = scaledCuts(model, 'x', 'w', 'w', k);
    const ys = scaledCuts(model, 'y', 'h', 'd', k);
    model.w = Math.max(MIN_SHELL, xs.get(oldW));
    model.d = Math.max(MIN_SHELL, ys.get(oldD));
    xs.set(oldW, model.w); ys.set(oldD, model.d);
    model.levels.forEach((lvl) => lvl.rooms.forEach((r) => {
      const x0 = xs.get(r.x); const x1 = xs.get(r.x + r.w); const y0 = ys.get(r.y); const y1 = ys.get(r.y + r.h);
      Object.assign(r, { x: x0, y: y0, w: x1 - x0, h: y1 - y0 });
    }));
    const sx = model.w / oldW; const sy = model.d / oldD;
    model.openings.forEach((o) => { o.pos *= (o.side === 'N' || o.side === 'S') ? sx : sy; });
    autoOpenings(model);
  }

  // ---------------------------------------------------------------- walls
  /** Interior walls as connected runs. Moving one run keeps the tiling intact. */
  function interiorWalls(model, level) {
    const rooms = roomsOf(model, level);
    const out = [];
    const scan = (axis) => {
      const [pos, len, cross, crossLen] = axis === 'v' ? ['x', 'w', 'y', 'h'] : ['y', 'h', 'x', 'w'];
      const lines = new Map();
      rooms.forEach((r) => {
        const edge = r[pos] + r[len];
        if (edge < (axis === 'v' ? model.w : model.d)) {
          if (!lines.has(edge)) lines.set(edge, { a: [], b: [] });
          lines.get(edge).a.push(r);
        }
        if (r[pos] > 0) {
          if (!lines.has(r[pos])) lines.set(r[pos], { a: [], b: [] });
          lines.get(r[pos]).b.push(r);
        }
      });
      lines.forEach(({ a, b }, at) => {
        // Group rooms into runs joined by overlap along the line.
        const items = [...a.map((r) => ({ r, side: 'a' })), ...b.map((r) => ({ r, side: 'b' }))]
          .sort((p, q) => p.r[cross] - q.r[cross]);
        let run = null;
        const flush = () => { if (run) out.push(run); };
        items.forEach(({ r, side }) => {
          const start = r[cross]; const end = r[cross] + r[crossLen];
          if (!run || start > run.end) { flush(); run = { axis, at, start, end, a: [], b: [] }; }
          run.end = Math.max(run.end, end);
          run[side].push(r);
        });
        flush();
      });
    };
    scan('v'); scan('h');
    return out.map((run, i) => {
      const [pos, len] = run.axis === 'v' ? ['x', 'w'] : ['y', 'h'];
      const min = Math.max(...run.a.map((r) => r[pos] + MIN_ROOM));
      const max = Math.min(...run.b.map((r) => r[pos] + r[len] - MIN_ROOM));
      return { ...run, index: i, min, max, ids: [...run.a, ...run.b].map((r) => r.id) };
    });
  }
  function moveWall(model, level, wall, value, others = []) {
    let v = snap(value);
    // Align with other walls when close, the way drafting tools do.
    let guide = null;
    others.forEach((o) => { if (guide === null && Math.abs(o - value) < 0.75) { v = o; guide = o; } });
    v = Math.max(wall.min, Math.min(wall.max, v));
    const [pos, len] = wall.axis === 'v' ? ['x', 'w'] : ['y', 'h'];
    wall.a.forEach((r) => { r[len] = v - r[pos]; });
    wall.b.forEach((r) => { const end = r[pos] + r[len]; r[pos] = v; r[len] = end - v; });
    wall.at = v;
    return { at: v, guide: guide !== null && v === guide ? guide : null };
  }
  function splitRoom(model, level, roomId, axis, at) {
    const rooms = roomsOf(model, level);
    const r = rooms.find((x) => x.id === roomId);
    if (!r) return null;
    const [pos, len] = axis === 'v' ? ['x', 'w'] : ['y', 'h'];
    if (r[len] < MIN_ROOM * 2) return null;
    const cut = Math.max(r[pos] + MIN_ROOM, Math.min(r[pos] + r[len] - MIN_ROOM, snap(at)));
    const fresh = { ...r, id: id('r'), name: 'New room', type: 'other' };
    fresh[pos] = cut; fresh[len] = r[pos] + r[len] - cut;
    r[len] = cut - r[pos];
    rooms.push(fresh);
    return fresh;
  }
  /** Remove a wall only where the two rooms merge into one rectangle. */
  function canRemoveWall(wall) {
    if (wall.a.length !== 1 || wall.b.length !== 1) return false;
    const [cross, crossLen] = wall.axis === 'v' ? ['y', 'h'] : ['x', 'w'];
    return wall.a[0][cross] === wall.b[0][cross] && wall.a[0][crossLen] === wall.b[0][crossLen];
  }
  function removeWall(model, level, wall) {
    if (!canRemoveWall(wall)) return false;
    const [pos, len] = wall.axis === 'v' ? ['x', 'w'] : ['y', 'h'];
    const keep = wall.a[0]; const gone = wall.b[0];
    keep[len] = gone[pos] + gone[len] - keep[pos];
    if (keep.name === 'New room') { keep.name = gone.name; keep.type = gone.type; }
    model.levels[level].rooms = roomsOf(model, level).filter((r) => r !== gone);
    return true;
  }

  // ------------------------------------------------------------- openings
  const GAP = 0.5; // ft of wall kept between openings
  const neighbours = (model, o) => model.openings.filter((x) => x !== o && x.level === o.level && x.side === o.side);
  /** The free stretch of wall around a point, between neighbouring openings and corners. */
  function freeSpan(model, o, around) {
    let low = 0.25; let high = sideLength(model, o.side) - 0.25;
    neighbours(model, o).forEach((x) => {
      const a = x.pos - x.width / 2 - GAP; const b = x.pos + x.width / 2 + GAP;
      if (b <= around) low = Math.max(low, b);
      else if (a >= around) high = Math.min(high, a);
      else { low = high = around; }
    });
    return [low, high];
  }
  function addOpening(model, level, side, pos, kind = 'window') {
    const size = kind === 'door' ? { width: 3, height: 6.67 } : { width: 4, height: 5 };
    if (!model.openingsConfirmed) confirmOpenings(model);
    const o = { id: id('o'), level, side, kind, pos: snap(pos), ...size, assumed: false };
    const [low, high] = freeSpan(model, o, o.pos);
    if (high - low < 1) return null; // the click landed on an existing opening
    o.width = Math.min(o.width, snap(high - low) || 1);
    o.pos = Math.max(low + o.width / 2, Math.min(high - o.width / 2, o.pos));
    model.openings.push(o);
    return o;
  }
  function moveOpening(model, opening, pos) {
    if (!model.openingsConfirmed) confirmOpenings(model);
    const [low, high] = freeSpan(model, opening, opening.pos);
    opening.pos = Math.max(low + opening.width / 2, Math.min(high - opening.width / 2, snap(pos)));
  }
  /** Change the width while keeping one end fixed; dir is +1 to move the right or bottom end. */
  function resizeOpening(model, opening, width, dir = 0) {
    if (!model.openingsConfirmed) confirmOpenings(model);
    const [low, high] = freeSpan(model, opening, opening.pos);
    const left = opening.pos - opening.width / 2; const right = opening.pos + opening.width / 2;
    let w = Math.max(1, snap(width));
    if (dir > 0) { w = Math.min(w, high - left); opening.width = w; opening.pos = left + w / 2; }
    else if (dir < 0) { w = Math.min(w, right - low); opening.width = w; opening.pos = right - w / 2; }
    else { w = Math.min(w, high - low); opening.width = w; opening.pos = Math.max(low + w / 2, Math.min(high - w / 2, opening.pos)); }
  }
  function removeOpening(model, openingId) {
    if (!model.openingsConfirmed) confirmOpenings(model);
    model.openings = model.openings.filter((o) => o.id !== openingId);
  }
  const openingArea = (o) => o.width * o.height;
  const glassArea = (model) => model.openings.filter((o) => o.kind === 'window').reduce((a, o) => a + openingArea(o), 0);

  // ------------------------------------------------------------ to engine
  function exposure(model, room) {
    const sides = {};
    if (room.y === 0) sides.N = [room.x, room.x + room.w];
    if (room.y + room.h === model.d) sides.S = [room.x, room.x + room.w];
    if (room.x === 0) sides.W = [room.y, room.y + room.h];
    if (room.x + room.w === model.w) sides.E = [room.y, room.y + room.h];
    return sides;
  }
  function toEngineRooms(model) {
    const top = model.stories - 1;
    const out = [];
    model.levels.forEach((lvl, level) => lvl.rooms.forEach((room) => {
      const sides = exposure(model, room);
      const walls = {}; const windows = {}; let door = 0;
      Object.entries(sides).forEach(([side, [start, end]]) => {
        walls[side] = end - start;
        model.openings.filter((o) => o.level === level && o.side === side).forEach((o) => {
          const a = Math.max(start, o.pos - o.width / 2); const b = Math.min(end, o.pos + o.width / 2);
          if (b <= a) return;
          const share = (b - a) * o.height;
          if (o.kind === 'door') door += share;
          else windows[side] = (windows[side] || 0) + share;
        });
      });
      out.push({ name: room.name, type: room.type, area: room.w * room.h, walls, windows, door_area: door, top: level === top, ground: level === 0 });
    }));
    return out;
  }
  function check(model) {
    // Invariants the drag code must never break.
    const problems = [];
    model.openings.forEach((o) => neighbours(model, o).forEach((x) => {
      if (o.id < x.id && Math.abs(o.pos - x.pos) < (o.width + x.width) / 2 - 1e-9) problems.push(`openings ${o.id} and ${x.id} overlap`);
    }));
    model.levels.forEach((lvl, l) => {
      const total = lvl.rooms.reduce((a, r) => a + r.w * r.h, 0);
      if (Math.abs(total - model.w * model.d) > 1e-6) problems.push(`level ${l}: rooms cover ${total}, shell is ${model.w * model.d}`);
      lvl.rooms.forEach((r, i) => {
        if (r.w < MIN_ROOM - 1e-9 || r.h < MIN_ROOM - 1e-9) problems.push(`level ${l}: ${r.name} collapsed to ${r.w} x ${r.h}`);
        if (r.x < 0 || r.y < 0 || r.x + r.w > model.w + 1e-9 || r.y + r.h > model.d + 1e-9) problems.push(`level ${l}: ${r.name} outside the shell`);
        lvl.rooms.slice(i + 1).forEach((o) => {
          const w = Math.min(r.x + r.w, o.x + o.w) - Math.max(r.x, o.x); const h = Math.min(r.y + r.h, o.y + o.h) - Math.max(r.y, o.y);
          if (w > 1e-9 && h > 1e-9) problems.push(`level ${l}: ${r.name} overlaps ${o.name}`);
        });
      });
    });
    return problems;
  }

  const api = {
    create, area, setStories, moveShell, scaleToArea, interiorWalls, moveWall, splitRoom, canRemoveWall, removeWall,
    addOpening, moveOpening, resizeOpening, removeOpening, confirmOpenings, autoOpenings, openingArea, glassArea,
    exposure, toEngineRooms, check, roomsOf, sideLength, MIN_ROOM, SNAP, snap,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.HouseModel = api;
})(typeof window !== 'undefined' ? window : globalThis);
