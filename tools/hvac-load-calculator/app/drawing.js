/* Plan, section, and axonometric projections of one HouseModel. Rendering only. */
(function () {
  'use strict';
  const M = () => window.HouseModel;
  const f0 = (v) => Math.round(v).toLocaleString('en-US');
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const feet = (v) => {
    const whole = Math.floor(v + 1e-6); const inches = Math.round((v - whole) * 12);
    return inches === 0 ? `${whole}'-0"` : `${whole}'-${inches}"`;
  };
  const DEFS = `<defs>
    <pattern id="p-earth" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="9" stroke="var(--earth)" stroke-width="1"/></pattern>
    <pattern id="p-conc" width="7" height="7" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="2" r=".6" fill="var(--ink2)"/><circle cx="5" cy="5" r=".5" fill="var(--ink2)"/></pattern>
    <pattern id="p-insul" width="7" height="6" patternUnits="userSpaceOnUse"><path d="M0 3 Q1.75 0 3.5 3 T7 3" fill="none" stroke="var(--ink2)" stroke-width=".7"/></pattern>
    <pattern id="p-assumed" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--ink3)" stroke-width="1"/></pattern>
  </defs>`;

  function dimension(x1, y1, x2, y2, label, offsetText = 0) {
    const horizontal = y1 === y2;
    const tick = (x, y) => (horizontal
      ? `<line class="dim" x1="${x - 3}" y1="${y + 3}" x2="${x + 3}" y2="${y - 3}"/><line class="dim" x1="${x}" y1="${y - 5}" x2="${x}" y2="${y + 5}"/>`
      : `<line class="dim" x1="${x - 3}" y1="${y + 3}" x2="${x + 3}" y2="${y - 3}"/><line class="dim" x1="${x - 5}" y1="${y}" x2="${x + 5}" y2="${y}"/>`);
    const text = horizontal
      ? `<text class="t-dim" x="${(x1 + x2) / 2}" y="${y1 - 4 + offsetText}" text-anchor="middle">${label}</text>`
      : `<text class="t-dim" transform="translate(${x1 - 4 + offsetText},${(y1 + y2) / 2}) rotate(-90)" text-anchor="middle">${label}</text>`;
    return `<line class="dim" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>${tick(x1, y1)}${tick(x2, y2)}${text}`;
  }

  // ------------------------------------------------------------------- plan
  function planTransform(model, frozen) {
    if (frozen) return frozen;
    const W = 620; const H = 470; const margin = { l: 62, r: 40, t: 56, b: 44 };
    const scale = Math.min((W - margin.l - margin.r) / model.w, (H - margin.t - margin.b) / model.d);
    const ox = margin.l + ((W - margin.l - margin.r) - model.w * scale) / 2;
    const oy = margin.t + ((H - margin.t - margin.b) - model.d * scale) / 2;
    return { scale, ox, oy };
  }
  function plan(svg, model, o) {
    const t = o.transform || planTransform(model);
    const X = (v) => t.ox + v * t.scale; const Y = (v) => t.oy + v * t.scale;
    const L = (v) => v * t.scale;
    const rooms = M().roomsOf(model, o.level);
    const walls = M().interiorWalls(model, o.level);
    const ext = Math.max(L(0.5), 4); const int = Math.max(L(0.33), 2.4);
    const parts = [DEFS];
    const assumedShell = !o.confirmed.has('walls');

    // Room fields and overlay
    rooms.forEach((r) => {
      const val = o.overlay ? o.overlay.values[r.id] : null;
      const fill = val !== null && val !== undefined
        ? `color-mix(in srgb, ${o.overlay.color} ${Math.round(5 + 58 * Math.min(1, o.overlay.intensity[r.id] || 0))}%, var(--paper))`
        : (o.selected.room === r.id ? 'var(--room-sel)' : 'var(--paper)');
      parts.push(`<rect class="h-room" data-room="${r.id}" x="${X(r.x)}" y="${Y(r.y)}" width="${L(r.w)}" height="${L(r.h)}" fill="${fill}"/>`);
      if (o.selected.room === r.id && o.overlay) parts.push(`<rect x="${X(r.x) + 2}" y="${Y(r.y) + 2}" width="${L(r.w) - 4}" height="${L(r.h) - 4}" fill="none" stroke="var(--accent)" stroke-width="1.5" pointer-events="none"/>`);
    });
    // Interior walls
    walls.forEach((w) => {
      const a = w.axis === 'v'
        ? { x: X(w.at) - int / 2, y: Y(w.start), width: int, height: L(w.end - w.start) }
        : { x: X(w.start), y: Y(w.at) - int / 2, width: L(w.end - w.start), height: int };
      parts.push(`<rect x="${a.x}" y="${a.y}" width="${a.width}" height="${a.height}" fill="var(--poche)" pointer-events="none"/>`);
    });
    // Exterior walls as poché
    const outer = `M${X(0) - ext} ${Y(0) - ext}H${X(model.w) + ext}V${Y(model.d) + ext}H${X(0) - ext}Z`;
    const inner = `M${X(0)} ${Y(0)}H${X(model.w)}V${Y(model.d)}H${X(0)}Z`;
    parts.push(`<path d="${outer}${inner}" fill-rule="evenodd" fill="${assumedShell ? 'url(#p-assumed)' : 'var(--poche)'}" stroke="var(--ink)" stroke-width=".9" ${assumedShell ? 'stroke-dasharray="5 4"' : ''} pointer-events="none"/>`);

    // Openings
    model.openings.filter((op) => op.level === o.level).forEach((op) => {
      const horiz = op.side === 'N' || op.side === 'S';
      const c = horiz ? X(op.pos) : Y(op.pos);
      const half = L(op.width) / 2;
      const band = op.side === 'N' ? Y(0) - ext : op.side === 'S' ? Y(model.d) : op.side === 'W' ? X(0) - ext : X(model.w);
      const dash = op.assumed ? 'stroke-dasharray="3 2.5"' : '';
      const stroke = op.assumed ? 'var(--ink3)' : 'var(--ink)';
      if (horiz) parts.push(`<rect x="${c - half}" y="${band - .5}" width="${half * 2}" height="${ext + 1}" fill="var(--glassy)" pointer-events="none"/>`);
      else parts.push(`<rect x="${band - .5}" y="${c - half}" width="${ext + 1}" height="${half * 2}" fill="var(--glassy)" pointer-events="none"/>`);
      if (op.kind === 'window') {
        [0, .5, 1].forEach((k) => {
          parts.push(horiz
            ? `<line x1="${c - half}" x2="${c + half}" y1="${band + ext * k}" y2="${band + ext * k}" stroke="${stroke}" stroke-width=".9" ${dash} pointer-events="none"/>`
            : `<line y1="${c - half}" y2="${c + half}" x1="${band + ext * k}" x2="${band + ext * k}" stroke="${stroke}" stroke-width=".9" ${dash} pointer-events="none"/>`);
        });
      } else {
        const inward = op.side === 'N' || op.side === 'W' ? 1 : -1;
        const r = half * 2;
        const hinge = c - half;
        const face = op.side === 'N' ? Y(0) : op.side === 'S' ? Y(model.d) : op.side === 'W' ? X(0) : X(model.w);
        if (horiz) parts.push(`<line x1="${hinge}" y1="${face}" x2="${hinge}" y2="${face + inward * r}" stroke="${stroke}" stroke-width="1.3" ${dash} pointer-events="none"/><path d="M${hinge} ${face + inward * r} A${r} ${r} 0 0 ${inward > 0 ? 0 : 1} ${hinge + r} ${face}" fill="none" stroke="${stroke}" stroke-width=".6" ${dash} pointer-events="none"/>`);
        else parts.push(`<line x1="${face}" y1="${hinge}" x2="${face + inward * r}" y2="${hinge}" stroke="${stroke}" stroke-width="1.3" ${dash} pointer-events="none"/><path d="M${face + inward * r} ${hinge} A${r} ${r} 0 0 ${inward > 0 ? 1 : 0} ${face} ${hinge + r}" fill="none" stroke="${stroke}" stroke-width=".6" ${dash} pointer-events="none"/>`);
      }
    });

    // Labels
    rooms.forEach((r) => {
      const cx = X(r.x + r.w / 2); const cy = Y(r.y + r.h / 2);
      const val = o.overlay ? o.overlay.values[r.id] : null;
      // Text is placed only where it fits, so labels never collide in small rooms.
      const name = rooms.length === 1 && model.stories === 1 ? 'Conditioned floor' : r.name;
      const width = L(r.w) - 8; const height = L(r.h);
      const fits = (text, px) => text.length * px <= width;
      const lines = [];
      const sizeText = `${feet(r.w)} × ${feet(r.h)} · ${f0(r.w * r.h)} ft²`;
      const valueText = val !== null && val !== undefined ? `${f0(val)} ${o.overlay.unit}` : null;
      if (fits(name, 7.2) && height >= 16) lines.push(['t-room', esc(name)]);
      else if (fits(name, 6.2) && height >= 14) lines.push(['t-room small', esc(name)]);
      if (valueText && height >= 16 * (lines.length + 1) && fits(valueText, 6.5)) lines.push(['t-num strong', valueText]);
      if (height >= 16 * (lines.length + 1) + 6 && fits(sizeText, 5.9)) lines.push(['t-sub', sizeText]);
      if (!lines.length && valueText && fits(f0(val), 6.5) && height >= 13) lines.push(['t-num strong', f0(val)]);
      const top = cy - (lines.length - 1) * 7.5 + 3.5;
      lines.forEach(([cls, text], i) => parts.push(`<text class="${cls}" x="${cx}" y="${top + i * 15}" text-anchor="middle" pointer-events="none">${text}</text>`));
    });

    // Dimension strings
    const dimTop = Y(0) - ext - 20; const dimLeft = X(0) - ext - 22;
    parts.push(dimension(X(0), dimTop, X(model.w), dimTop, feet(model.w)));
    parts.push(dimension(dimLeft, Y(0), dimLeft, Y(model.d), feet(model.d)));
    if (rooms.length > 1 && o.tool === 'rooms') {
      const xs = [...new Set(rooms.filter((r) => r.y + r.h === model.d).flatMap((r) => [r.x, r.x + r.w]))].sort((a, b) => a - b);
      const dimBottom = Y(model.d) + ext + 18;
      xs.slice(1).forEach((x, i) => parts.push(dimension(X(xs[i]), dimBottom, X(x), dimBottom, feet(x - xs[i]), 15)));
    }

    // Section cut marker
    if (o.cut) {
      const c = o.cut;
      const a = 16;
      if (c.axis === 'x') {
        const x = X(c.at);
        parts.push(`<line x1="${x}" x2="${x}" y1="${Y(0) - ext - 32}" y2="${Y(model.d) + ext + 30}" stroke="var(--accent)" stroke-width="1.1" stroke-dasharray="14 4 2 4" pointer-events="none"/>`);
        [Y(0) - ext - 40, Y(model.d) + ext + 38].forEach((y) => { parts.push(`<circle cx="${x}" cy="${y}" r="8" fill="var(--paper)" stroke="var(--accent)" stroke-width="1.1" pointer-events="none"/><text class="t-num" x="${x}" y="${y + 3.5}" text-anchor="middle" pointer-events="none" style="fill:var(--accent);font-weight:700">A</text><path d="M${x + 9} ${y} l10 0 m-4 -3 l4 3 l-4 3" fill="none" stroke="var(--accent)" stroke-width="1" pointer-events="none"/>`); });
        parts.push(`<rect class="h-cut" data-cut="1" tabindex="0" role="slider" aria-label="Section cut position" x="${x - a / 2}" y="${Y(0) - ext - 50}" width="${a}" height="${L(model.d) + 2 * ext + 100}"/>`);
      } else {
        const y = Y(c.at);
        parts.push(`<line y1="${y}" y2="${y}" x1="${X(0) - ext - 42}" x2="${X(model.w) + ext + 22}" stroke="var(--accent)" stroke-width="1.1" stroke-dasharray="14 4 2 4" pointer-events="none"/>`);
        [X(0) - ext - 50, X(model.w) + ext + 30].forEach((x) => { parts.push(`<circle cx="${x}" cy="${y}" r="8" fill="var(--paper)" stroke="var(--accent)" stroke-width="1.1" pointer-events="none"/><text class="t-num" x="${x}" y="${y + 3.5}" text-anchor="middle" pointer-events="none" style="fill:var(--accent);font-weight:700">A</text><path d="M${x} ${y - 9} l0 -10 m-3 4 l3 -4 l3 4" fill="none" stroke="var(--accent)" stroke-width="1" pointer-events="none"/>`); });
        parts.push(`<rect class="h-cut" data-cut="1" tabindex="0" role="slider" aria-label="Section cut position" x="${X(0) - ext - 60}" y="${y - a / 2}" width="${L(model.w) + 2 * ext + 100}" height="${a}"/>`);
      }
    }

    // North arrow
    const na = o.rotation * Math.PI / 180; const nx = 590; const ny = 34;
    parts.push(`<g transform="rotate(${o.rotation} ${nx} ${ny})"><circle cx="${nx}" cy="${ny}" r="13" fill="none" stroke="var(--ink2)" stroke-width=".75"/><path d="M${nx} ${ny - 13} L${nx + 5} ${ny + 8} L${nx} ${ny + 4} Z" fill="var(--ink)"/></g><text class="t-cap" x="${nx + Math.sin(na) * 21}" y="${ny - Math.cos(na) * 21 + 4}" text-anchor="middle">N</text>`);

    // Editing handles
    if (o.tool === 'shell') {
      const g = 16;
      [['N', X(0), Y(0) - ext - g / 2, L(model.w), ext + g, 'ns'], ['S', X(0), Y(model.d) - g / 2, L(model.w), ext + g, 'ns'], ['W', X(0) - ext - g / 2, Y(0), ext + g, L(model.d), 'ew'], ['E', X(model.w) - g / 2, Y(0), ext + g, L(model.d), 'ew']].forEach(([side, x, y, w, h, kind]) => {
        parts.push(`<rect class="h-shell ${kind}" data-shell="${side}" tabindex="0" role="slider" aria-label="${side} wall" x="${x}" y="${y}" width="${w}" height="${h}"/>`);
        const cx = x + w / 2; const cy = y + h / 2;
        parts.push(`<circle class="grab" cx="${cx}" cy="${cy}" r="4.5"/>`);
      });
    }
    if (o.tool === 'rooms') {
      walls.forEach((w) => {
        const g = 16; const on = o.selected.wall === w.index && o.selected.wallAxis === w.axis ? ' on' : '';
        parts.push(w.axis === 'v'
          ? `<rect class="h-wall v${on}" data-wall="${w.index}" tabindex="0" role="slider" aria-label="Interior wall" x="${X(w.at) - g / 2}" y="${Y(w.start)}" width="${g}" height="${L(w.end - w.start)}"/>`
          : `<rect class="h-wall h${on}" data-wall="${w.index}" tabindex="0" role="slider" aria-label="Interior wall" x="${X(w.start)}" y="${Y(w.at) - g / 2}" width="${L(w.end - w.start)}" height="${g}"/>`);
      });
      if (o.preview) {
        const p = o.preview;
        parts.push(p.axis === 'v'
          ? `<line x1="${X(p.at)}" x2="${X(p.at)}" y1="${Y(p.start)}" y2="${Y(p.end)}" stroke="var(--accent)" stroke-width="2" stroke-dasharray="6 4" pointer-events="none"/>`
          : `<line y1="${Y(p.at)}" y2="${Y(p.at)}" x1="${X(p.start)}" x2="${X(p.end)}" stroke="var(--accent)" stroke-width="2" stroke-dasharray="6 4" pointer-events="none"/>`);
      }
      if (o.guide !== null && o.guide !== undefined && o.guideAxis) {
        parts.push(o.guideAxis === 'v'
          ? `<line x1="${X(o.guide)}" x2="${X(o.guide)}" y1="${Y(0)}" y2="${Y(model.d)}" stroke="var(--accent)" stroke-width=".8" pointer-events="none"/>`
          : `<line y1="${Y(o.guide)}" y2="${Y(o.guide)}" x1="${X(0)}" x2="${X(model.w)}" stroke="var(--accent)" stroke-width=".8" pointer-events="none"/>`);
      }
    }
    if (o.tool === 'openings') {
      // Each wall accepts a new opening where you click.
      const g = 18;
      [['N', X(0), Y(0) - ext - g / 2, L(model.w), ext + g], ['S', X(0), Y(model.d) - g / 2, L(model.w), ext + g], ['W', X(0) - ext - g / 2, Y(0), ext + g, L(model.d)], ['E', X(model.w) - g / 2, Y(0), ext + g, L(model.d)]].forEach(([side, x, y, w, h]) => {
        parts.push(`<rect data-addwall="${side}" x="${x}" y="${y}" width="${w}" height="${h}" fill="transparent" style="cursor:copy"><title>Click to add here</title></rect>`);
      });
      model.openings.filter((op) => op.level === o.level).forEach((op) => {
        const horiz = op.side === 'N' || op.side === 'S';
        const c = horiz ? X(op.pos) : Y(op.pos); const half = L(op.width) / 2;
        const band = op.side === 'N' ? Y(0) - ext - 7 : op.side === 'S' ? Y(model.d) - 7 : op.side === 'W' ? X(0) - ext - 7 : X(model.w) - 7;
        const thick = ext + 14; const on = o.selected.opening === op.id ? ' on' : '';
        parts.push(horiz
          ? `<rect class="h-op${on}" data-op="${op.id}" tabindex="0" role="button" aria-label="${op.kind}" x="${c - half}" y="${band}" width="${half * 2}" height="${thick}"/>`
          : `<rect class="h-op${on}" data-op="${op.id}" tabindex="0" role="button" aria-label="${op.kind}" x="${band}" y="${c - half}" width="${thick}" height="${half * 2}"/>`);
      });
      // The selected opening's handles go last, so no other hit area covers them.
      const sel = model.openings.find((op) => op.id === o.selected.opening && op.level === o.level);
      if (sel) {
        const op = sel; const horiz = op.side === 'N' || op.side === 'S';
        const c = horiz ? X(op.pos) : Y(op.pos); const half = L(op.width) / 2;
        const band = op.side === 'N' ? Y(0) - ext - 7 : op.side === 'S' ? Y(model.d) - 7 : op.side === 'W' ? X(0) - ext - 7 : X(model.w) - 7;
        const thick = ext + 14;
        [-1, 1].forEach((dir) => parts.push(horiz
          ? `<rect class="h-end v" data-opend="${dir}" x="${c + dir * half - 5}" y="${band - 3}" width="10" height="${thick + 6}" style="fill:var(--accent)"/>`
          : `<rect class="h-end h" data-opend="${dir}" x="${band - 3}" y="${c + dir * half - 5}" width="${thick + 6}" height="10" style="fill:var(--accent)"/>`));
        parts.push(`<text class="t-dim" text-anchor="middle" pointer-events="none" x="${horiz ? c : band + (op.side === 'W' ? -13 : thick + 13)}" y="${horiz ? (op.side === 'N' ? band - 6 : band + thick + 12) : c}" style="fill:var(--accent)">${feet(op.width)}</text>`);
      }
    }
    if (o.liveText) parts.push(`<text class="t-big" x="310" y="${o.liveY || 22}" text-anchor="middle" style="fill:var(--accent)">${esc(o.liveText)}</text>`);
    svg.setAttribute('viewBox', '0 0 620 470');
    svg.innerHTML = parts.join('');
    return t;
  }

  // ---------------------------------------------------------------- section
  function section(svg, model, o) {
    const c = o.cut; const along = c.axis === 'y';   // true: the cut runs east-west
    const span = along ? model.w : model.d;
    const ridgeAlongX = model.w >= model.d;
    const pitch = (o.pitch || 6) / 12;
    const crossRoof = (ridgeAlongX && !along) || (!ridgeAlongX && along);
    const ridgeOffset = ridgeAlongX ? Math.abs(c.at - model.d / 2) : Math.abs(c.at - model.w / 2);
    const halfSpanRoof = ridgeAlongX ? model.d / 2 : model.w / 2;
    const flatRise = Math.max(0, (halfSpanRoof - ridgeOffset)) * pitch;
    const rise = crossRoof ? span / 2 * pitch : flatRise;
    const foundation = o.floor;
    const below = foundation.startsWith('basement') ? 9.5 : foundation.startsWith('crawl') ? 4.5 : 2.5;
    const above = foundation.startsWith('crawl') ? 2 : foundation.startsWith('basement') ? 0.75 : 0.5;
    const hTotal = model.stories * model.height + rise + above + 1.6;
    const W = 620; const H = 470; const ml = 112; const mr = 112; const mt = 40; const mb = 30;
    const scale = Math.min((W - ml - mr) / span, (H - mt - mb) / (hTotal + below));
    const ox = ml + ((W - ml - mr) - span * scale) / 2;
    const groundY = mt + (hTotal) * scale + ((H - mt - mb) - (hTotal + below) * scale) / 2;
    const X = (v) => ox + v * scale; const Z = (z) => groundY - z * scale;
    const L = (v) => v * scale;
    const floor0 = above; const top = floor0 + model.stories * model.height;
    const r = o.result; const winter = o.season === 'winter';
    const ceilR = 1 / o.ceilingU; const wallR = 1 / o.wallU;
    const wallT = Math.max(L(0.22 + Math.min(wallR, 30) / 3.5 / 12), 3.2);
    const insulT = Math.max(L(Math.min(ceilR, 70) / 3.5 / 12), 2);
    const parts = [DEFS];
    const conf = o.confirmed;
    const dash = (key) => (conf.has(key) ? '' : 'stroke-dasharray="5 4"');

    // Earth
    const gx0 = 6; const gx1 = W - 6;
    parts.push(`<rect x="${gx0}" y="${groundY}" width="${gx1 - gx0}" height="${H - groundY - 6}" fill="url(#p-earth)" opacity=".45"/>`);
    parts.push(`<line x1="${gx0}" x2="${gx1}" y1="${groundY}" y2="${groundY}" stroke="var(--ink)" stroke-width="1.3"/>`);
    parts.push(`<text class="t-cap" x="${gx0 + 6}" y="${groundY - 5}">Grade</text>`);

    // Interior air
    const tint = o.overlaySection ? `color-mix(in srgb, ${winter ? 'var(--heat2)' : 'var(--cool2)'} 6%, var(--paper))` : 'var(--paper)';
    parts.push(`<rect x="${X(0)}" y="${Z(top)}" width="${L(span)}" height="${L(top - floor0)}" fill="${tint}"/>`);

    // Foundation
    if (foundation === 'slab') {
      parts.push(`<rect x="${X(0) - wallT}" y="${Z(floor0)}" width="${L(span) + 2 * wallT}" height="${Math.max(L(0.42), 3)}" fill="url(#p-conc)" stroke="var(--ink)" stroke-width="1" ${dash('floor')}/>`);
      [X(0) - wallT, X(span) - L(1) + wallT].forEach((x) => parts.push(`<rect x="${x}" y="${Z(floor0)}" width="${L(1)}" height="${L(above + 1.5)}" fill="url(#p-conc)" stroke="var(--ink)" stroke-width="1" ${dash('floor')}/>`));
    } else {
      const bottom = foundation.startsWith('basement') ? -8.5 : -2.5;
      const thick = Math.max(L(0.67), 4);
      [X(0) - wallT, X(span) + wallT - thick].forEach((x) => parts.push(`<rect x="${x}" y="${Z(floor0)}" width="${thick}" height="${L(floor0 - bottom)}" fill="url(#p-conc)" stroke="var(--ink)" stroke-width="1" ${dash('floor')}/>`));
      parts.push(`<rect x="${X(0) - wallT}" y="${Z(bottom)}" width="${L(span) + 2 * wallT}" height="${Math.max(L(0.4), 3)}" fill="url(#p-conc)" stroke="var(--ink)" stroke-width="1"/>`);
      parts.push(`<rect x="${X(0) - wallT + thick}" y="${Z(floor0) + 2.5}" width="${L(span) + 2 * wallT - 2 * thick}" height="${L(floor0 - bottom) - 2.5}" fill="${foundation === 'basement_conditioned' ? tint : 'var(--paper)'}"/>`);
      parts.push(`<rect x="${X(0)}" y="${Z(floor0)}" width="${L(span)}" height="${Math.max(L(0.85), 5)}" fill="url(#p-insul)" stroke="var(--ink)" stroke-width=".9" ${dash('floor')}/>`);
      parts.push(`<text class="t-cap" x="${X(span / 2)}" y="${Z((floor0 + bottom) / 2) + 4}" text-anchor="middle">${{ crawl_vented: 'Vented crawlspace', crawl_sealed: 'Sealed crawlspace', basement_conditioned: 'Heated basement', basement_unconditioned: 'Unheated basement' }[foundation]}</text>`);
    }

    // Walls with insulation
    [X(0) - wallT, X(span)].forEach((x) => {
      parts.push(`<rect x="${x}" y="${Z(top)}" width="${wallT}" height="${L(top - floor0)}" fill="${conf.has('walls') ? 'url(#p-insul)' : 'url(#p-assumed)'}" stroke="var(--ink)" stroke-width="1.1" ${dash('walls')}/>`);
    });

    // Windows where the cut passes through them
    const endSides = along ? ['W', 'E'] : ['N', 'S'];
    endSides.forEach((side, i) => model.openings.filter((op) => op.side === side && Math.abs(op.pos - c.at) <= op.width / 2).forEach((op) => {
      const base = floor0 + op.level * model.height + (op.kind === 'door' ? 0 : 2.5);
      const x = i === 0 ? X(0) - wallT : X(span);
      const stroke = op.assumed ? 'var(--ink3)' : 'var(--ink)';
      parts.push(`<rect x="${x - .5}" y="${Z(base + op.height)}" width="${wallT + 1}" height="${L(op.height)}" fill="var(--paper)" stroke="${stroke}" stroke-width=".9" ${op.assumed ? 'stroke-dasharray="3 2.5"' : ''}/><line x1="${x + wallT / 2}" x2="${x + wallT / 2}" y1="${Z(base + op.height)}" y2="${Z(base)}" stroke="${stroke}" stroke-width=".9"/>`);
    }));

    // Floors and interior partitions
    for (let l = 0; l < model.stories; l++) {
      const z0 = floor0 + l * model.height; const z1 = z0 + model.height;
      if (l > 0) parts.push(`<rect x="${X(0)}" y="${Z(z0) - 2.5}" width="${L(span)}" height="5" fill="var(--poche)"/>`);
      const rooms = M().roomsOf(model, l).filter((rm) => (along ? rm.y <= c.at && rm.y + rm.h > c.at : rm.x <= c.at && rm.x + rm.w > c.at))
        .sort((a, b) => (along ? a.x - b.x : a.y - b.y));
      rooms.forEach((rm, i) => {
        const start = along ? rm.x : rm.y; const size = along ? rm.w : rm.h;
        if (i > 0) parts.push(`<rect x="${X(start) - 1.3}" y="${Z(z1)}" width="2.6" height="${L(model.height)}" fill="var(--poche)"/>`);
        if (o.selected.room === rm.id) parts.push(`<rect x="${X(start)}" y="${Z(z1)}" width="${L(size)}" height="${L(model.height)}" fill="var(--room-sel)" pointer-events="none"/>`);
        parts.push(`<rect data-room="${rm.id}" class="h-room" x="${X(start)}" y="${Z(z1)}" width="${L(size)}" height="${L(model.height)}" fill="transparent"/>`);
        if (L(size) > 52 && rooms.length > 1 && L(model.height) > 70 && (l > 0 || r === null || r)) parts.push(`<text class="t-room" x="${X(start + size / 2)}" y="${Z(z0 + model.height * 0.78)}" text-anchor="middle" pointer-events="none" style="font-size:9.5px">${esc(rm.name)}</text>`);
      });
    }

    // Ceiling and insulation
    const cathedral = o.ceilingType === 'cathedral';
    parts.push(`<rect x="${X(0)}" y="${Z(top) - insulT}" width="${L(span)}" height="${insulT}" fill="${conf.has('ceiling') ? 'url(#p-insul)' : 'url(#p-assumed)'}" stroke="var(--ink)" stroke-width="1" ${dash('ceiling')}/>`);

    // Roof
    const over = 1.25;
    const roofStroke = { white: 'var(--ink2)', light: 'var(--ink2)', medium: 'var(--ink)', dark: 'var(--ink)' }[o.roofColor || 'medium'];
    const roofWeight = { white: 2, light: 2.4, medium: 3, dark: 4.5 }[o.roofColor || 'medium'];
    if (crossRoof) {
      parts.push(`<path d="M${X(-over)} ${Z(top - over * pitch)} L${X(span / 2)} ${Z(top + rise)} L${X(span + over)} ${Z(top - over * pitch)}" fill="none" stroke="${roofStroke}" stroke-width="${roofWeight}" stroke-linejoin="miter"/>`);
    } else {
      parts.push(`<path d="M${X(-over)} ${Z(top + rise)} H${X(span + over)}" fill="none" stroke="${roofStroke}" stroke-width="${roofWeight}"/><line x1="${X(0)}" x2="${X(0)}" y1="${Z(top)}" y2="${Z(top + rise)}" class="hl"/><line x1="${X(span)}" x2="${X(span)}" y1="${Z(top)}" y2="${Z(top + rise)}" class="hl"/>`);
    }

    // Ducts and equipment
    const ductLoc = o.ductLocation;
    let ductY = null;
    if (o.system.ducted) {
      if (ductLoc === 'attic') ductY = Z(top) - insulT - 7;
      else if (ductLoc === 'conditioned') ductY = Z(top) + 8;
      else if (ductLoc === 'basement' || ductLoc.endsWith('crawl')) ductY = Z(floor0) + Math.max(L(0.85), 5) + 7;
      else ductY = Z(floor0) - 12;
      const d = Math.max(L(0.9), 6);
      parts.push(`<rect x="${X(span * .14)}" y="${ductY - d / 2}" width="${L(span * .72)}" height="${d}" fill="var(--paper)" stroke="${conf.has('ducts') ? 'var(--accent)' : 'var(--ink2)'}" stroke-width="1.2" ${dash('ducts')}/>`);
      [.22, .5, .78].forEach((k) => {
        const down = ductY < Z(top) + 12;
        parts.push(`<line x1="${X(span * k)}" x2="${X(span * k)}" y1="${ductY + (down ? d / 2 : -d / 2)}" y2="${down ? Z(top) + 3 : Z(floor0) - 3}" stroke="${conf.has('ducts') ? 'var(--accent)' : 'var(--ink2)'}" stroke-width="1.2" ${dash('ducts')}/>`);
      });
    }

    // Load diagram: bands off the envelope, like a structural load diagram
    if (r) {
      const color = winter ? 'var(--heat2)' : 'var(--cool2)';
      const flows = o.flows;
      const maxFlux = Math.max(flows.wall.flux, flows.window.flux, flows.ceiling.flux, flows.floor.flux, 0.1);
      const T = (flux) => Math.max(1.5, Math.abs(flux) / maxFlux * 30);
      const band = (x, y, w, h, n, vertical, outward) => {
        let out = `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${color}" fill-opacity=".16" stroke="${color}" stroke-width=".9"/>`;
        for (let i = 0; i < n; i++) {
          if (vertical) {
            const yy = y + (i + 0.5) * h / n; const x1 = outward > 0 ? x : x + w; const x2 = outward > 0 ? x + w : x;
            out += `<line x1="${x1}" x2="${x2}" y1="${yy}" y2="${yy}" stroke="${color}" stroke-width=".75"/><path d="M${x2} ${yy} l${outward > 0 ? -3.5 : 3.5} -2.2 m0 4.4 l${outward > 0 ? 3.5 : -3.5} -2.2" fill="none" stroke="${color}" stroke-width=".75"/>`;
          } else {
            const xx = x + (i + 0.5) * w / n; const y1 = outward > 0 ? y + h : y; const y2 = outward > 0 ? y : y + h;
            out += `<line y1="${y1}" y2="${y2}" x1="${xx}" x2="${xx}" stroke="${color}" stroke-width=".75"/><path d="M${xx} ${y2} l-2.2 ${outward > 0 ? 3.5 : -3.5} m4.4 0 l-2.2 ${outward > 0 ? -3.5 : 3.5}" fill="none" stroke="${color}" stroke-width=".75"/>`;
          }
        }
        return out;
      };
      const label = (x0, y, name, value, anchor0, go) => {
        // Keep every label inside the sheet.
        let x = x0; let anchor = anchor0;
        if (anchor === 'start' && x > W - 92) { x = W - 6; anchor = 'end'; }
        if (anchor === 'end' && x < 92) { x = 6; anchor = 'start'; }
        return labelAt(x, y, name, value, anchor, go);
      };
      const labelAt = (x, y, name, value, anchor, go) => `<g class="h-room" data-go="${go}" tabindex="0" role="button"><text class="t-cap" x="${x}" y="${y}" text-anchor="${anchor}">${name}</text><text class="t-num" x="${x}" y="${y + 13}" text-anchor="${anchor}" style="fill:${color};font-weight:600">${f0(value)} Btu/h</text></g>`;
      const prefix = winter ? 'heat-' : 'cool-';
      const out = winter ? 1 : -1;
      // Left wall band
      const wT = T(flows.wall.flux); const midZ = floor0 + (top - floor0) / 2;
      const lx = X(0) - wallT - wT - 3;
      parts.push(`<g class="h-room" data-go="${prefix}walls">${band(lx, Z(top), wT, L(top - floor0), Math.max(3, Math.round(L(top - floor0) / 14)), true, -out)}</g>`);
      parts.push(label(lx - 5, Z(midZ) - 18, 'Walls', flows.wall.total, 'end', `${prefix}walls`));
      // Right band: windows carried separately
      const gT = T(flows.window.flux); const rx = X(span) + wallT + 3;
      parts.push(`<g class="h-room" data-go="${prefix}windows">${band(rx, Z(top), gT, L(top - floor0), Math.max(3, Math.round(L(top - floor0) / 14)), true, out)}</g>`);
      parts.push(label(rx + gT + 5, Z(midZ) - 18, 'Windows', flows.window.total, 'start', `${prefix}windows`));
      // Ceiling band
      const cT = T(flows.ceiling.flux);
      const cy = Z(top) - insulT - cT - 1;
      parts.push(`<g class="h-room" data-go="${prefix}ceiling">${band(X(span * 0.08), cy, L(span * 0.84), cT, Math.max(5, Math.round(L(span * .84) / 22)), false, out)}</g>`);
      parts.push(label(X(0) - wallT - 8, Z(top) - 34, 'Ceiling', flows.ceiling.total, 'end', `${prefix}ceiling`));
      // Floor band
      const fT = T(flows.floor.flux);
      if (Math.abs(flows.floor.total) > 30) {
        const base = foundation.startsWith('basement') ? Z(-8.5) + Math.max(L(0.4), 3) + 2 : foundation.startsWith('crawl') ? Z(-2.5) + Math.max(L(0.4), 3) + 2 : Z(floor0) + Math.max(L(0.42), 3) + 2;
        parts.push(`<g class="h-room" data-go="${prefix}floor">${band(X(span * 0.08), base, L(span * 0.84), Math.min(fT, H - base - 8), Math.max(5, Math.round(L(span * .84) / 22)), false, flows.floor.total > 0 ? -out : out)}</g>`);
        parts.push(label(X(0) - wallT - 8, Math.min(base + 16, H - 22), 'Floor', flows.floor.total, 'end', `${prefix}floor`));
      }
      // Air and ducts as text call-outs with leaders
      parts.push(label(X(span) + wallT + 8, Z(top) - 34, 'Air leakage', flows.air.total, 'start', `${prefix}infiltration`));
      if (o.system.ducted && ductY !== null && flows.ducts.total > 20) {
        const lxx = X(span * .86);
        parts.push(`<line class="hl" x1="${lxx}" x2="${X(span) + wallT + 6}" y1="${ductY}" y2="${Math.min(Z(top) - 44, ductY - 30)}"/>`);
        parts.push(label(X(span) + wallT + 8, Math.min(Z(top) - 76, ductY - 46), 'Ducts', flows.ducts.total, 'start', `${prefix}ducts`));
      }
      // Temperatures
      // Indoor temperature sits in the widest room on the cut, clear of partitions.
      const cutRooms = M().roomsOf(model, 0).filter((rm) => (along ? rm.y <= c.at && rm.y + rm.h > c.at : rm.x <= c.at && rm.x + rm.w > c.at));
      const widest = cutRooms.sort((a, b) => (along ? b.w - a.w : b.h - a.h))[0];
      const tx = widest ? X((along ? widest.x + widest.w / 2 : widest.y + widest.h / 2)) : X(span / 2);
      const tz = Z(floor0 + model.height * .36);
      parts.push(`<text class="t-big" x="${tx}" y="${tz}" text-anchor="middle" pointer-events="none">${f0(o.tIn)} °F</text>`);
      parts.push(`<text class="t-cap" x="${tx}" y="${tz + 13}" text-anchor="middle" pointer-events="none">Indoor</text>`);
      parts.push(`<text class="t-big" x="14" y="24">${f0(o.tOut)} °F</text><text class="t-cap" x="14" y="37">Outdoor</text>`);
      if (!winter && !cathedral && o.tAttic !== null) parts.push(`<text class="t-num" x="${X(span / 2)}" y="${crossRoof ? Z(top + rise * .34) : Z(top + rise * .6)}" text-anchor="middle" font-weight="600">Attic ${f0(o.tAttic)} °F</text>`);
      if (!winter && o.sun && o.sun.altitude > 0) {
        const a = o.sun.altitude * Math.PI / 180; const fromRight = o.sunFromRight;
        const x0 = fromRight ? X(span) + wallT : X(0) - wallT; const y0 = Z(top - model.height * .3);
        const len = 96;
        const x1 = x0 + (fromRight ? 1 : -1) * Math.cos(a) * len; const y1 = y0 - Math.sin(a) * len;
        const tx = Math.max(30, Math.min(W - 30, x1));
        parts.push(`<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" stroke="var(--ink2)" stroke-width=".8" stroke-dasharray="2 3"/><text class="t-num" x="${tx}" y="${Math.max(y1 - 4, 50)}" text-anchor="middle">Sun ${f0(o.sun.altitude)}°</text>`);
      }
    }

    // Levels
    const levelX = X(span) + wallT + 4;
    if (!r) parts.push(`<text class="t-dim" x="${levelX}" y="${Z(top) + 3}">${feet(top - floor0)}</text>`);
    parts.push(dimension(X(0), H - 12, X(span), H - 12, feet(span)));
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = parts.join('');
  }

  // ------------------------------------------------------------------- axon
  function axon(svg, model, o) {
    const ang = Math.PI / 6;
    const raw = (x, y, z) => [(x - y) * Math.cos(ang), (x + y) * Math.sin(ang) - z];
    const gap = 5;
    const zTop = model.stories * (model.height + gap);
    const pts = [raw(0, 0, 0), raw(model.w, 0, 0), raw(0, model.d, 0), raw(model.w, model.d, 0), raw(0, 0, zTop + model.height), raw(model.w, 0, zTop + model.height)];
    const minX = Math.min(...pts.map((p) => p[0])); const maxX = Math.max(...pts.map((p) => p[0]));
    const minY = Math.min(...pts.map((p) => p[1])); const maxY = Math.max(...pts.map((p) => p[1]));
    const W = 620; const H = 470;
    const scale = Math.min((W - 40) / (maxX - minX), (H - 40) / (maxY - minY));
    const P = (x, y, z) => { const [a, b] = raw(x, y, z); return [(a - minX) * scale + (W - (maxX - minX) * scale) / 2, (b - minY) * scale + (H - (maxY - minY) * scale) / 2]; };
    const poly = (list, attrs) => `<polygon points="${list.map((q) => q.map((n) => n.toFixed(1)).join(',')).join(' ')}" ${attrs}/>`;
    const parts = [DEFS];
    const wallStyle = (key) => `stroke="var(--ink)" stroke-width=".9" ${o.confirmed.has(key) ? '' : 'stroke-dasharray="4 3"'}`;
    for (let level = 0; level < model.stories; level++) {
      const z0 = level * (model.height + gap); const h = model.height; const low = 2.6;
      const rooms = M().roomsOf(model, level);
      // Floor
      parts.push(poly([P(0, 0, z0), P(model.w, 0, z0), P(model.w, model.d, z0), P(0, model.d, z0)], 'fill="var(--paper)" stroke="var(--ink)" stroke-width="1"'));
      rooms.forEach((r) => {
        const val = o.overlay ? o.overlay.values[r.id] : null;
        const fill = val !== null && val !== undefined ? `color-mix(in srgb, ${o.overlay.color} ${Math.round(5 + 58 * Math.min(1, o.overlay.intensity[r.id] || 0))}%, var(--paper))` : (o.selected.room === r.id ? 'var(--room-sel)' : 'transparent');
        parts.push(`<g data-room="${r.id}" data-level="${level}" class="h-room">${poly([P(r.x, r.y, z0), P(r.x + r.w, r.y, z0), P(r.x + r.w, r.y + r.h, z0), P(r.x, r.y + r.h, z0)], `fill="${fill}" stroke="var(--hair)" stroke-width=".7"`)}</g>`);
      });
      // Back walls at full height
      parts.push(poly([P(0, 0, z0), P(model.w, 0, z0), P(model.w, 0, z0 + h), P(0, 0, z0 + h)], `fill="var(--paper)" fill-opacity=".85" ${wallStyle('walls')}`));
      parts.push(poly([P(0, 0, z0), P(0, model.d, z0), P(0, model.d, z0 + h), P(0, 0, z0 + h)], `fill="var(--paper)" fill-opacity=".7" ${wallStyle('walls')}`));
      model.openings.filter((op) => op.level === level && (op.side === 'N' || op.side === 'W')).forEach((op) => {
        const base = z0 + (op.kind === 'door' ? 0 : 2.5); const a = op.pos - op.width / 2; const b = op.pos + op.width / 2;
        const list = op.side === 'N' ? [P(a, 0, base), P(b, 0, base), P(b, 0, base + op.height), P(a, 0, base + op.height)] : [P(0, a, base), P(0, b, base), P(0, b, base + op.height), P(0, a, base + op.height)];
        parts.push(poly(list, `fill="color-mix(in srgb, var(--cool2) 15%, var(--paper))" stroke="${op.assumed ? 'var(--ink3)' : 'var(--ink)'}" stroke-width=".8" ${op.assumed ? 'stroke-dasharray="3 2"' : ''}`));
      });
      // Partitions, cut low
      M().interiorWalls(model, level).sort((a, b) => a.at - b.at).forEach((w) => {
        const list = w.axis === 'v'
          ? [P(w.at, w.start, z0), P(w.at, w.end, z0), P(w.at, w.end, z0 + low), P(w.at, w.start, z0 + low)]
          : [P(w.start, w.at, z0), P(w.end, w.at, z0), P(w.end, w.at, z0 + low), P(w.start, w.at, z0 + low)];
        parts.push(poly(list, 'fill="var(--paper)" stroke="var(--ink2)" stroke-width=".8"'));
      });
      rooms.forEach((r) => {
        if (rooms.length === 1 && model.stories === 1) return;
        const [x, y] = P(r.x + r.w / 2, r.y + r.h / 2, z0 + .3);
        if (r.w * r.h > 60) parts.push(`<text class="t-room" x="${x}" y="${y}" text-anchor="middle" pointer-events="none" style="font-size:9px">${esc(r.name)}</text>`);
      });
      // Front walls cut low, so the rooms read
      parts.push(poly([P(0, model.d, z0), P(model.w, model.d, z0), P(model.w, model.d, z0 + low), P(0, model.d, z0 + low)], `fill="var(--paper)" fill-opacity=".92" ${wallStyle('walls')}`));
      parts.push(poly([P(model.w, 0, z0), P(model.w, model.d, z0), P(model.w, model.d, z0 + low), P(model.w, 0, z0 + low)], `fill="var(--paper)" fill-opacity=".92" ${wallStyle('walls')}`));
      if (level < model.stories - 1) {
        [[0, 0], [model.w, 0], [model.w, model.d], [0, model.d]].forEach(([x, y]) => { const a = P(x, y, z0 + (x === 0 || y === 0 ? h : low)); const b = P(x, y, z0 + h + gap); parts.push(`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="var(--ink3)" stroke-width=".6" stroke-dasharray="2 3"/>`); });
      }
    }
    const [lx, ly] = P(model.w, model.d, -1);
    parts.push(`<text class="t-cap" x="16" y="24">Axonometric</text><text class="t-sub" x="16" y="38">Front walls cut at ${feet(2.6)}. Levels pulled apart.</text><text class="t-num" x="${lx + 6}" y="${ly + 12}"> </text>`);
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = parts.join('');
  }

  window.HouseDrawing = { plan, section, axon, planTransform, feet };
})();
