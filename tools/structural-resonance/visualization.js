/* Dimensioned geometry and normalized modal motion. Physics comes from Python. */
(() => {
    'use strict';
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const instances = new WeakMap();
    let sequence = 0;

    const style = document.createElement('style');
    style.textContent = `
        .frequency-visual { margin: 20px 0; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
        .frequency-visual .fv-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; padding: 12px 14px; border-bottom: 1px solid var(--border-color); }
        .frequency-visual .fv-views { display: flex; gap: 4px; }
        .frequency-visual button { min-height: 36px; padding: 6px 10px; font-size: .8rem; }
        .frequency-visual button[aria-pressed="true"] { background: var(--primary-light); border-color: var(--text-light); }
        .frequency-visual svg { display: block; width: 100%; height: auto; color: var(--text-color); }
        .frequency-visual svg text { font-family: var(--font-sans); font-size: 14px; fill: var(--text-color); }
        .frequency-visual svg .fv-label { font-size: 13px; fill: var(--text-light); }
        .frequency-visual svg .fv-dimension { font-family: var(--font-mono); font-size: 13px; }
        .frequency-visual svg .fv-small { font-size: 12px; fill: var(--text-light); }
        .frequency-visual .fv-caption { font-size: .75rem; line-height: 1.5; color: var(--text-light); padding: 0 14px 12px; margin: 0; }
        .frequency-visual .fv-stale { font-size: .8rem; padding: 10px 14px; margin: 0; border-top: 1px solid var(--border-color); color: var(--text-color); background: var(--primary-light); }
        .frequency-visual[data-stale="true"] svg { opacity: .55; }
        .frequency-visual.fv-narrow svg text { font-size: 21px; }
        .frequency-visual.fv-narrow svg .fv-label { font-size: 20px; }
        .frequency-visual.fv-narrow svg .fv-dimension { font-size: 19px; }
        .frequency-visual.fv-narrow svg .fv-small { font-size: 17px; }
        .frequency-visual.fv-narrow .fv-separator { display: none; }
        @media(max-width: 520px) { .frequency-visual .fv-toolbar { padding: 8px; gap: 6px; } .frequency-visual button { padding: 6px 8px; font-size: .75rem; } }
    `;
    document.head.append(style);

    function svgNode(tag, attributes = {}, parent = null, content = null) {
        const node = document.createElementNS(SVG_NS, tag);
        Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
        if (content !== null) node.textContent = content;
        if (parent) parent.append(node);
        return node;
    }
    function label(parent, x, y, content, className = 'fv-label', anchor = 'middle') {
        return svgNode('text', { x, y, class: className, 'text-anchor': anchor }, parent, content);
    }
    function line(parent, x1, y1, x2, y2, extra = {}) {
        return svgNode('line', { x1, y1, x2, y2, stroke: 'var(--text-light)', 'stroke-width': 1.2, ...extra }, parent);
    }
    function path(parent, points, extra = {}) {
        return svgNode('path', {
            d: points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(3)},${y.toFixed(3)}`).join(' '),
            fill: 'none', stroke: 'var(--accent-color)', 'stroke-width': 2.5,
            'stroke-linejoin': 'round', 'stroke-linecap': 'round', ...extra,
        }, parent);
    }
    const format = value => {
        const number = Number(value), magnitude = Math.abs(number);
        return magnitude !== 0 && (magnitude < 1e-3 || magnitude >= 1e6)
            ? number.toExponential(3)
            : number.toLocaleString(undefined, { maximumSignificantDigits: 5 });
    };
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

    function dimension(parent, start, end, text, offset = [0, 0]) {
        const [x1, y1] = start, [x2, y2] = end;
        const dx = x2 - x1, dy = y2 - y1, norm = Math.hypot(dx, dy) || 1;
        const nx = -dy / norm, ny = dx / norm;
        line(parent, x1, y1, x2, y2);
        for (const [x, y] of [start, end]) line(parent, x - nx * 5, y - ny * 5, x + nx * 5, y + ny * 5);
        label(parent, (x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1] - 8, text, 'fv-dimension');
    }
    function clampSupport(parent, x, y, direction = -1) {
        line(parent, x, y - 38, x, y + 38, { stroke: 'var(--text-color)', 'stroke-width': 3 });
        for (let offset = -34; offset < 37; offset += 10) line(parent, x, y + offset, x + direction * 13, y + offset + 8);
    }
    function simpleSupport(parent, x, y, roller) {
        svgNode('path', { d: `M${x},${y} l-13,22 h26 Z`, fill: 'var(--bg-card)', stroke: 'var(--text-color)', 'stroke-width': 1.8 }, parent);
        const floor = y + (roller ? 34 : 25);
        if (roller) for (const shift of [-7, 7]) svgNode('circle', { cx: x + shift, cy: y + 27, r: 3, fill: 'none', stroke: 'var(--text-light)' }, parent);
        line(parent, x - 22, floor, x + 22, floor);
    }
    function arrow(parent, x1, y1, x2, y2) {
        line(parent, x1, y1, x2, y2, { stroke: 'var(--accent-color)', 'stroke-width': 2 });
        const angle = Math.atan2(y2 - y1, x2 - x1);
        path(parent, [[x2 - 8 * Math.cos(angle - .45), y2 - 8 * Math.sin(angle - .45)], [x2, y2], [x2 - 8 * Math.cos(angle + .45), y2 - 8 * Math.sin(angle + .45)]], { 'stroke-width': 2 });
    }

    function drawBeam(instance) {
        const { data, base, moving } = instance;
        const g = data.geometry, round = data.section_type.startsWith('circular');
        const tipMass = data.support_type === 'cantilever' ? (data.tip_mass_kg || 0) : 0;
        const activeDepth = round ? g.outer_diameter_mm : data.bending_axis === 'width' ? g.width_mm : g.depth_mm;
        const x0 = 80, x1 = 510, center = 148;
        const depth = clamp(activeDepth / g.length_mm * (x1 - x0), 6, 55);
        svgNode('rect', { x: x0, y: center - depth / 2, width: x1 - x0, height: depth, rx: 1, fill: 'var(--primary-light)', stroke: 'var(--text-light)', 'stroke-width': 1.2 }, base);
        line(base, x0, center, x1, center, { 'stroke-dasharray': '5 5', stroke: 'var(--text-light)' });
        if (data.support_type === 'simply_supported') {
            simpleSupport(base, x0, center + depth / 2, false);
            simpleSupport(base, x1, center + depth / 2, true);
        } else {
            clampSupport(base, x0, center);
            if (data.support_type === 'fixed_fixed') clampSupport(base, x1, center, 1);
        }
        label(base, (x0 + x1) / 2, 55, data.support_type === 'cantilever' ? (tipMass > 0 ? 'Fixed end → attached tip mass' : 'Fixed end → free end') : data.support_type === 'fixed_fixed' ? 'Both ends fixed' : 'Pinned end → roller support');
        let massMarker = null;
        if (tipMass > 0) {
            massMarker = svgNode('circle', {
                cx: x1, cy: center, r: 9, fill: 'var(--bg-card)',
                stroke: 'var(--text-light)', 'stroke-width': 1.5,
                'data-tip-mass': 'geometry',
            }, base);
            label(base, x1, 224, `M = ${format(tipMass)} kg`, 'fv-dimension', 'end');
        }
        line(base, x0, center + 47, x0, 267, { stroke: 'var(--border-color)' });
        line(base, x1, center + 47, x1, 267, { stroke: 'var(--border-color)' });
        dimension(base, [x0, 254], [x1, 254], `L = ${format(g.length_mm)} mm`);
        label(base, (x0 + x1) / 2, 292, round ? 'Side view · bending in the displayed plane' : `Side view · bending through ${data.bending_axis === 'width' ? 'width b' : 'depth h'}`, 'fv-small');

        const section = svgNode('g', {}, base);
        instance.section = section;
        line(section, 553, 55, 553, 280, { stroke: 'var(--border-color)', class: 'fv-separator' });
        label(section, 646, 55, 'Cross-section');
        const cx = 646, cy = 145, sectionWidth = round ? g.outer_diameter_mm : g.width_mm;
        const sectionHeight = round ? g.outer_diameter_mm : g.depth_mm;
        const scale = 86 / Math.max(sectionWidth, sectionHeight);
        const width = sectionWidth * scale, height = sectionHeight * scale;
        if (round) {
            svgNode('circle', { cx, cy, r: width / 2, fill: 'var(--primary-light)', stroke: 'var(--text-color)', 'stroke-width': 1.8 }, section);
            if (data.section_type === 'circular_hollow') svgNode('circle', { cx, cy, r: Math.max(0, width / 2 - g.wall_thickness_mm * scale), fill: 'var(--bg-card)', stroke: 'var(--text-color)', 'stroke-width': 1.3 }, section);
            dimension(section, [cx - width / 2, 217], [cx + width / 2, 217], `D = ${format(g.outer_diameter_mm)}`);
        } else {
            svgNode('rect', { x: cx - width / 2, y: cy - height / 2, width, height, fill: 'var(--primary-light)', stroke: 'var(--text-color)', 'stroke-width': 1.8 }, section);
            if (data.section_type === 'box') {
                const wall = g.wall_thickness_mm * scale;
                svgNode('rect', { x: cx - width / 2 + wall, y: cy - height / 2 + wall, width: width - 2 * wall, height: height - 2 * wall, fill: 'var(--bg-card)', stroke: 'var(--text-color)', 'stroke-width': 1.3 }, section);
            }
            dimension(section, [cx - width / 2, 217], [cx + width / 2, 217], `b = ${format(g.width_mm)}`);
            label(section, cx, 239, `h = ${format(g.depth_mm)} mm`, 'fv-dimension');
        }
        if (data.section_type === 'box' || data.section_type === 'circular_hollow') label(section, cx, 260, `wall = ${format(g.wall_thickness_mm)} mm`, 'fv-small');
        else if (round) label(section, cx, 240, 'Dimensions in mm', 'fv-small');
        if (!round && data.bending_axis === 'width') arrow(section, cx - 14, 92, cx + 14, 92);
        else arrow(section, cx, 91, cx, 69);
        instance.update = phase => {
            moving.replaceChildren();
            if (massMarker) massMarker.setAttribute('stroke', instance.view === 'geometry' ? 'var(--accent-color)' : 'var(--text-light)');
            if (instance.view !== 'mode' || !data.available) return;
            const points = data.x.map((x, i) => [x0 + x * (x1 - x0), center - phase * 48 * data.displacement[i]]);
            path(moving, points, { 'stroke-width': 3 });
            if (tipMass > 0) {
                const end = points[points.length - 1];
                svgNode('circle', {
                    cx: end[0], cy: end[1], r: 9, fill: 'var(--bg-card)',
                    stroke: 'var(--accent-color)', 'stroke-width': 2.5,
                    'data-tip-mass': 'mode',
                }, moving);
            }
        };
    }

    function drawPlate(instance) {
        const { data, base, moving } = instance, g = data.geometry;
        const scale = Math.min(440 / (.85 * g.length_mm + .65 * g.width_mm), 185 / (.22 * g.length_mm + .32 * g.width_mm));
        const sx = Math.max(g.length_mm * scale, 12), sy = Math.max(g.width_mm * scale, 12);
        const origin = [295 - sx * .425 + sy * .325, 173 + sx * .11 + sy * .16];
        const project = (x, y, z = 0) => [origin[0] + x * sx * .85 - y * sy * .65, origin[1] - x * sx * .22 - y * sy * .32 - z * 44];
        const corners = [project(0, 0), project(1, 0), project(1, 1), project(0, 1)];
        svgNode('polygon', { points: corners.map(point => point.join(',')).join(' '), fill: 'var(--primary-light)', stroke: 'var(--text-light)', 'stroke-width': 1.5 }, base);
        for (let i = 0; i < 4; i++) {
            const a = corners[i], b = corners[(i + 1) % 4];
            for (const position of [.2, .5, .8]) {
                const x = a[0] + (b[0] - a[0]) * position, y = a[1] + (b[1] - a[1]) * position;
                svgNode('path', { d: `M${x},${y} l-5,10 h10 Z`, fill: 'var(--bg-card)', stroke: 'var(--text-light)' }, base);
            }
        }
        label(base, 290, 39, 'All four edges simply supported');
        const a0 = project(0, 0), a1 = project(1, 0), b0 = project(0, 1);
        dimension(base, [a0[0] + 10, a0[1] + 45], [a1[0] + 10, a1[1] + 45], `a = ${format(g.length_mm)} mm`, [8, 32]);
        dimension(base, [a0[0] - 32, a0[1] + 15], [b0[0] - 32, b0[1] + 15], `b = ${format(g.width_mm)} mm`, [-20, 25]);
        const section = svgNode('g', {}, base);
        instance.section = section;
        line(section, 553, 55, 553, 280, { stroke: 'var(--border-color)', class: 'fv-separator' });
        label(section, 646, 67, 'Plate section');
        const thickness = clamp(g.thickness_mm / Math.min(g.length_mm, g.width_mm) * 140, 5, 35);
        svgNode('rect', { x: 588, y: 145 - thickness / 2, width: 116, height: thickness, fill: 'var(--primary-light)', stroke: 'var(--text-color)', 'stroke-width': 1.5 }, section);
        label(section, 646, 184, `h = ${format(g.thickness_mm)} mm`, 'fv-dimension');
        arrow(section, 646, 121, 646, 97);
        label(section, 646, 231, 'Out-of-plane motion', 'fv-small');
        label(base, 290, 310, 'Perspective view · support triangles mark the edges', 'fv-small');
        instance.update = phase => {
            moving.replaceChildren();
            if (instance.view !== 'mode' || !data.available) return;
            const xStride = Math.max(1, Math.ceil((data.x.length - 1) / 24));
            const yStride = Math.max(1, Math.ceil((data.y.length - 1) / 24));
            for (let yi = 0; yi < data.y.length; yi += yStride) path(moving, data.x.map((x, xi) => project(x, data.y[yi], phase * data.displacement[yi][xi])), { 'stroke-width': 1.1, opacity: .8 });
            for (let xi = 0; xi < data.x.length; xi += xStride) path(moving, data.y.map((y, yi) => project(data.x[xi], y, phase * data.displacement[yi][xi])), { 'stroke-width': 1.1, opacity: .8 });
        };
    }

    function drawRing(instance) {
        const { data, base, moving } = instance, g = data.geometry;
        const cx = 285, cy = 164, radius = 96;
        const thickness = clamp(g.thickness_mm / g.diameter_mm * 2 * radius, 4, 75);
        svgNode('circle', { cx, cy, r: radius, fill: 'none', stroke: 'var(--primary-light)', 'stroke-width': thickness }, base);
        for (const r of [radius - thickness / 2, radius + thickness / 2]) svgNode('circle', { cx, cy, r, fill: 'none', stroke: 'var(--text-light)', 'stroke-width': 1 }, base);
        svgNode('circle', { cx, cy, r: radius, fill: 'none', stroke: 'var(--text-light)', 'stroke-width': 1, 'stroke-dasharray': '5 5' }, base);
        line(base, cx - 7, cy, cx + 7, cy, { stroke: 'var(--border-color)' });
        line(base, cx, cy - 7, cx, cy + 7, { stroke: 'var(--border-color)' });
        label(base, cx, 33, 'Free circular ring · no supports');
        dimension(base, [cx - radius, 297], [cx + radius, 297], `Mean diameter = ${format(g.diameter_mm)} mm`);
        const section = svgNode('g', {}, base);
        instance.section = section;
        line(section, 480, 55, 480, 280, { stroke: 'var(--border-color)', class: 'fv-separator' });
        label(section, 610, 88, 'Radial wall thickness');
        label(section, 610, 117, `h = ${format(g.thickness_mm)} mm`, 'fv-dimension');
        svgNode('rect', { x: 555, y: 155, width: 110, height: 26, fill: 'var(--primary-light)', stroke: 'var(--text-color)' }, section);
        dimension(section, [687, 155], [687, 181], 'h', [15, 8]);
        label(section, 610, 223, 'Dashed circle: mean diameter', 'fv-small');
        label(section, 610, 244, 'View along the ring axis', 'fv-small');
        instance.update = phase => {
            moving.replaceChildren();
            if (instance.view !== 'mode' || !data.available) return;
            // Convert the Python-supplied radial/tangential vectors to screen coordinates.
            const points = data.theta.map((theta, i) => {
                const cosine = Math.cos(theta), sine = Math.sin(theta);
                const radial = phase * 22 * data.radial[i], tangential = phase * 22 * data.tangential[i];
                return [cx + (radius + radial) * cosine - tangential * sine, cy - (radius + radial) * sine - tangential * cosine];
            });
            path(moving, points, { 'stroke-width': 3 });
        };
    }

    function stop(instance) {
        instance.playing = false;
        cancelAnimationFrame(instance.frame);
        instance.play.textContent = 'Play motion';
        instance.play.setAttribute('aria-pressed', 'false');
    }
    function refreshView(instance) {
        instance.geometryButton.setAttribute('aria-pressed', String(instance.view === 'geometry'));
        instance.modeButton.setAttribute('aria-pressed', String(instance.view === 'mode'));
        instance.play.disabled = instance.view !== 'mode' || !instance.data.available || instance.stale;
        instance.caption.textContent = !instance.data.available
            ? `Geometry shown. ${instance.data.reason || 'This mode is too detailed to draw at this resolution.'}`
            : instance.view === 'mode'
                ? 'Motion is normalized and exaggerated. Animation is slowed for viewing; it does not predict vibration amplitude. Dimensions are schematic.'
                : 'Dimensions and supports used for this calculation. Geometry is schematic.';
        instance.update(instance.phase);
    }
    function create(host) {
        const figure = document.createElement('figure');
        figure.className = 'frequency-visual';
        const toolbar = document.createElement('div');
        toolbar.className = 'fv-toolbar';
        const views = document.createElement('div');
        views.className = 'fv-views';
        views.setAttribute('role', 'group');
        views.setAttribute('aria-label', 'Structure visualization');
        const button = (text, parent) => {
            const element = document.createElement('button');
            element.type = 'button'; element.textContent = text; element.setAttribute('aria-pressed', 'false');
            parent.append(element); return element;
        };
        const geometryButton = button('Geometry', views), modeButton = button('Mode shape', views), play = button('Play motion', toolbar);
        toolbar.prepend(views);
        const svg = svgNode('svg', { viewBox: '0 0 750 335', role: 'img', 'aria-labelledby': `fv-title-${++sequence} fv-desc-${sequence}` });
        const title = svgNode('title', { id: `fv-title-${sequence}` }, svg);
        const description = svgNode('desc', { id: `fv-desc-${sequence}` }, svg);
        const base = svgNode('g', {}, svg), moving = svgNode('g', {}, svg);
        const caption = document.createElement('figcaption'); caption.className = 'fv-caption';
        const staleNote = document.createElement('p'); staleNote.className = 'fv-stale'; staleNote.hidden = true;
        staleNote.textContent = 'Inputs changed. Calculate to update the diagram.';
        figure.append(toolbar, svg, caption, staleNote); host.replaceChildren(figure);
        const instance = { figure, geometryButton, modeButton, play, svg, title, description, base, moving, caption, staleNote, data: null, phase: 1, view: 'mode', playing: false, frame: null, stale: false };
        geometryButton.addEventListener('click', () => { stop(instance); instance.view = 'geometry'; refreshView(instance); });
        modeButton.addEventListener('click', () => { stop(instance); instance.phase = 1; instance.view = 'mode'; refreshView(instance); });
        play.addEventListener('click', () => {
            if (instance.playing) { stop(instance); return; }
            instance.playing = true; play.textContent = 'Pause motion'; play.setAttribute('aria-pressed', 'true');
            const started = performance.now(); let lastFrame = 0;
            const animate = time => {
                if (!instance.playing) return;
                if (time - lastFrame > 30) {
                    instance.phase = Math.cos((time - started) / 1600 * Math.PI * 2);
                    instance.update(instance.phase); lastFrame = time;
                }
                instance.frame = requestAnimationFrame(animate);
            };
            instance.frame = requestAnimationFrame(animate);
        });
        instance.visibility = () => { if (document.hidden) stop(instance); };
        document.addEventListener('visibilitychange', instance.visibility);
        instance.resize = new ResizeObserver(() => layout(instance, host));
        instance.resize.observe(host);
        instance.intersection = new IntersectionObserver(entries => {
            if (entries.some(entry => !entry.isIntersecting)) stop(instance);
        });
        instance.intersection.observe(figure);
        instances.set(host, instance);
        return instance;
    }
    function layout(instance, host) {
        const narrow = host.clientWidth < 480;
        instance.figure.classList.toggle('fv-narrow', narrow);
        instance.svg.setAttribute('viewBox', narrow ? '0 0 560 590' : '0 0 750 335');
        if (instance.section) instance.section.setAttribute('transform', narrow ? `translate(${instance.data.kind === 'ring' ? -325 : -365} 280)` : '');
    }
    function render(host, data) {
        if (!host || !data) return;
        const instance = instances.get(host) || create(host);
        if (instance.data === data) return;
        stop(instance); instance.data = data; instance.phase = 1;
        instance.view = data.available ? 'mode' : 'geometry';
        instance.base.replaceChildren(); instance.moving.replaceChildren();
        const massLabel = data.kind === 'beam' && data.tip_mass_kg > 0 ? ` with ${format(data.tip_mass_kg)} kg point mass at the tip` : '';
        instance.title.textContent = (data.mode_label || `${data.kind} natural-frequency model`) + massLabel;
        instance.description.textContent = 'Dimensioned structural model and selected normalized mode shape. Supports and bending direction are shown. Animation is optional.';
        instance.modeButton.disabled = !data.available;
        if (data.kind === 'beam') drawBeam(instance);
        else if (data.kind === 'plate') drawPlate(instance);
        else if (data.kind === 'ring') drawRing(instance);
        else { instance.update = () => {}; label(instance.base, 375, 165, 'Diagram unavailable for this model.'); }
        layout(instance, host); setStale(host, false); refreshView(instance);
    }
    function setStale(host, stale) {
        const instance = instances.get(host);
        if (!instance) return;
        instance.stale = Boolean(stale); instance.figure.dataset.stale = String(Boolean(stale));
        instance.staleNote.hidden = !stale;
        if (stale) stop(instance);
        if (instance.data) refreshView(instance);
    }
    function destroy(host) {
        const instance = instances.get(host);
        if (!instance) return;
        stop(instance); instance.resize.disconnect(); instance.intersection.disconnect();
        document.removeEventListener('visibilitychange', instance.visibility);
        instances.delete(host); host.replaceChildren();
    }
    window.FrequencyVisualization = { render, setStale, destroy };
})();
