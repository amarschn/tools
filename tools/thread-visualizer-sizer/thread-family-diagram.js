/* Pipe-family and supplier-screw schematics. Numeric annotations come from Python. */
(() => {
    'use strict';
    const svg = document.getElementById('family-profile-svg');
    const ns = 'http://www.w3.org/2000/svg';
    const overview = document.getElementById('family-overview');
    const profile = document.getElementById('family-closeup');

    function node(parent, tag, attributes = {}, content) {
        const element = document.createElementNS(ns, tag);
        Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
        if (content !== undefined) element.textContent = content;
        parent.append(element);
        return element;
    }

    const path = (parent, d, attributes = {}) => node(parent, 'path', { d, class: 'thread-line', ...attributes });
    const line = (parent, x1, y1, x2, y2, attributes = {}) => node(parent, 'line', { x1, y1, x2, y2, class: 'dimension-line', ...attributes });
    const label = (parent, x, y, content, attributes = {}) => node(parent, 'text', { x, y, class: 'figure-text', ...attributes }, content);
    const number = (value) => Number(value.toPrecision(6)).toString();

    // Sectioned material is drawn the same way as the calculated profiles: a
    // flat fill under the shared hatch pattern, then the outline on top.
    function material(parent, d, internal, attributes = {}) {
        const { id, ...shared } = attributes;
        node(parent, 'path', { d, class: 'thread-fill', ...(id ? { id } : {}), ...shared });
        node(parent, 'path', { d, class: 'thread-hatch', fill: `url(#family-hatch-${internal ? 'internal' : 'external'})`, ...shared });
    }

    function arrow(parent, tip, toward) {
        const length = Math.hypot(toward[0] - tip[0], toward[1] - tip[1]);
        const ux = (toward[0] - tip[0]) / length;
        const uy = (toward[1] - tip[1]) / length;
        const points = [tip, [tip[0] + 7 * ux - 2 * uy, tip[1] + 7 * uy + 2 * ux],
            [tip[0] + 7 * ux + 2 * uy, tip[1] + 7 * uy - 2 * ux]];
        node(parent, 'polygon', { class: 'dimension-arrow', points: points.map((point) => point.join(',')).join(' ') });
    }

    function dimension(parent, start, end, text, x, y, vertical = false) {
        // family-dimension carries no styling; it groups a line with its arrows.
        const group = node(parent, 'g', { class: 'family-dimension', 'aria-label': text });
        line(group, ...start, ...end);
        arrow(group, start, end);
        arrow(group, end, start);
        label(group, x, y, text, { class: 'dimension-text', 'text-anchor': 'middle',
            ...(vertical ? { transform: `rotate(-90 ${x} ${y})` } : {}) });
    }

    // One vertical rhythm for both panels, sized to sit beside the calculated
    // profiles rather than tower over them. Every y below is drawn against it.
    const HEADING_Y = 10;
    const CAPTION_Y = [136, 150];
    const PANEL_H = 160;

    function layout() {
        const width = svg.parentElement.clientWidth;
        if (!width) return;
        // Stack only when a side-by-side pair would be genuinely cramped. The
        // calculated profile never stacks, and a stacked schematic beside it
        // stands several times taller than the figure it belongs with.
        const narrow = width < 430;
        svg.setAttribute('viewBox', narrow ? `0 0 300 ${2 * PANEL_H + 8}` : `0 0 620 ${PANEL_H + 8}`);
        overview.setAttribute('transform', 'translate(10 4)');
        profile.setAttribute('transform', narrow ? `translate(10 ${PANEL_H + 4})` : 'translate(330 4)');
    }

    function pipeOverview(spec, data) {
        const tapered = data.diameter_taper > 0;
        const internal = spec.side === 'internal';
        label(overview, 0, HEADING_Y, `${internal ? 'INTERNAL' : 'EXTERNAL'} · ${tapered ? 'TAPERED' : 'PARALLEL'}`, { class: 'material-label' });
        const x1 = 42, x2 = 242, axis = 62, lengthY = 112;
        const change = (x2 - x1) * data.diameter_taper / 2;
        const r1 = 26 + (internal ? change : 0);
        const r2 = 26 + (internal ? 0 : change);
        const envelope = `M${x1},${axis - r1} L${x2},${axis - r2} V${axis + r2} L${x1},${axis + r1} Z`;
        if (internal) {
            material(overview, `M${x1},${axis - 40} H${x2} V${axis + 40} H${x1} Z ${envelope}`, true, { 'fill-rule': 'evenodd' });
        } else material(overview, envelope, false);
        path(overview, envelope, { id: 'family-taper-envelope', 'data-diameter-taper': data.diameter_taper });
        line(overview, 26, axis, 264, axis, { class: 'center-line' });
        label(overview, 145, axis - 5, 'Axis', { 'text-anchor': 'middle' });
        if (tapered) line(overview, x1, axis - r1, x2, axis - r1, { class: 'guide-line' });
        [x1, x2].forEach((x, index) => {
            const r = index ? r2 : r1;
            const dx = index ? 258 : 26;
            line(overview, x, axis - r, dx + (index ? 4 : -4), axis - r);
            line(overview, x, axis + r, dx + (index ? 4 : -4), axis + r);
            dimension(overview, [dx, axis - r], [dx, axis + r], index ? 'ØB' : 'ØA', dx + (index ? 14 : -7), axis, true);
            line(overview, x, axis + r + 4, x, lengthY + 5);
        });
        dimension(overview, [x1, lengthY], [x2, lengthY], 'L', 142, lengthY - 5);
        label(overview, 142, CAPTION_Y[0], tapered ? `|ØB − ØA| / L = 1:${number(1 / data.diameter_taper)}` : 'ØA = ØB · no taper', { id: 'family-taper-label', 'text-anchor': 'middle' });
        label(overview, 142, CAPTION_Y[1], `Half-angle to axis: ${data.half_angle_deg.toFixed(3)}°`, { id: 'family-half-angle', 'text-anchor': 'middle' });
    }

    function productOverview(data) {
        label(overview, 0, HEADING_Y, 'NOMINAL SIZE ENVELOPE', { class: 'material-label' });
        const x1 = 58, x2 = 248, axis = 62, top = axis - 24, bottom = axis + 24, lengthY = 112;
        material(overview, `M${x1},${top} H${x2} V${bottom} H${x1} Z`, false);
        path(overview, `M${x1},${top} H${x2} V${bottom} H${x1} Z`);
        line(overview, 46, axis, 264, axis, { class: 'center-line' });
        [top, bottom].forEach((y) => line(overview, 32, y, x1 - 4, y));
        const diameter = data.diameter == null ? 'd: not specified' : `d = ${number(data.diameter)} ${data.unit}`;
        if (data.standard_thread) label(overview, 0, HEADING_Y + 14, data.standard_thread, { 'text-anchor': 'start' });
        dimension(overview, [36, top], [36, bottom], diameter, 25, axis, true);
        [x1, x2].forEach((x) => line(overview, x, bottom + 4, x, lengthY + 5));
        const length = data.length == null ? 'L: not specified' : `L = ${number(data.length)} ${data.unit}`;
        dimension(overview, [x1, lengthY], [x2, lengthY], length, 153, lengthY - 5);
        label(overview, 142, CAPTION_Y[0], data.standard_thread ? 'd: nominal major diameter · L: supplier convention' : 'd, L: supplier size conventions', { 'text-anchor': 'middle' });
        label(overview, 142, CAPTION_Y[1], 'Head, point and drive are not modeled', { 'text-anchor': 'middle' });
    }

    function closeup(data, internal) {
        const pipe = data.kind === 'pipe';
        label(profile, 0, HEADING_Y, pipe ? 'FAMILY PROFILE · IDEALIZED' : 'THREAD DETAIL · ILLUSTRATIVE', { class: 'material-label' });
        const pitch = 80, base = 106, pitchY = 38;
        // Screen-space illustration only. No manufacturing crest/root dimensions
        // or proprietary screw angle are inferred from these proportions.
        // A published flank angle draws a real one; without it the tooth stays
        // an illustration and says so.
        const angled = data.included_angle_deg != null;
        const halfAngle = angled ? data.included_angle_deg * Math.PI / 360 : null;
        const depth = angled ? .32 * pitch / Math.tan(halfAngle) : 48;
        const points = [];
        for (let tooth = 0; tooth < 3; tooth++) {
            [[0, 0], [.1, 0], [.42, -depth], [.58, -depth], [.9, 0], [1, 0]].forEach(([phase, height]) => {
                points.push([20 + (tooth + phase) * pitch, base + height]);
            });
        }
        const d = 'M' + points.map((point) => point.join(',')).join(' L');
        material(profile, `${d} L260,${base + 20} L20,${base + 20} Z`, internal, { id: 'family-profile-section' });
        path(profile, d, { id: 'family-profile-outline' });
        [60, 140].forEach((x) => line(profile, x, base - depth - 4, x, pitchY + 4));
        const pitchText = pipe ? `P = ${data.pitch_in.toFixed(5)} in`
            : data.pitch_mm != null ? `P = ${data.pitch_mm.toFixed(4)} mm`
            : 'P: supplier data needed';
        dimension(profile, [60, pitchY], [140, pitchY], pitchText, 100, pitchY - 8);
        if (angled) {
            const vertex = [60, base - .4 * pitch / Math.tan(halfAngle)];
            const radius = 24;
            const left = [vertex[0] - radius * Math.sin(halfAngle), vertex[1] + radius * Math.cos(halfAngle)];
            const right = [vertex[0] + radius * Math.sin(halfAngle), left[1]];
            path(profile, `M${left.join(',')} A${radius},${radius} 0 0 0 ${right.join(',')}`, { class: 'dimension-line' });
            arrow(profile, left, [left[0] + Math.cos(halfAngle), left[1] + Math.sin(halfAngle)]);
            arrow(profile, right, [right[0] - Math.cos(halfAngle), right[1] + Math.sin(halfAngle)]);
            label(profile, 60, base - 6, `${data.included_angle_deg}°`, { id: 'family-included-angle', class: 'dimension-text', 'text-anchor': 'middle' });
            label(profile, 140, CAPTION_Y[0], `${number(data.tpi)} TPI · P = ${data.pitch_mm.toFixed(4)} mm`, { id: 'family-pitch-label', 'text-anchor': 'middle' });
            label(profile, 140, CAPTION_Y[1], pipe ? 'Crest / root details omitted' : 'Pilot hole: material and engagement dependent', { 'text-anchor': 'middle' });
        } else if (data.tpi != null) {
            label(profile, 140, CAPTION_Y[0], `${number(data.tpi)} TPI · P = ${data.pitch_mm.toFixed(4)} mm`, { id: 'family-pitch-label', 'text-anchor': 'middle' });
            label(profile, 140, CAPTION_Y[1], 'Flank form follows the product', { 'text-anchor': 'middle' });
        } else {
            label(profile, 140, CAPTION_Y[0], 'Flank angle: supplier data needed', { 'text-anchor': 'middle' });
            label(profile, 140, CAPTION_Y[1], 'Pitch and pilot hole: supplier data', { 'text-anchor': 'middle' });
        }
    }

    function render(spec) {
        const data = spec.diagram;
        overview.replaceChildren();
        profile.replaceChildren();
        // One figure, one material: the overview and the close-up hatch alike.
        const internal = data.kind === 'pipe' && spec.side === 'internal';
        if (data.kind === 'pipe') pipeOverview(spec, data);
        else productOverview(data);
        closeup(data, internal);
        const note = data.kind === 'pipe'
            ? 'Schematic only, not to scale. ØA and ØB are diameters at planes L apart. Basic diameters and thread lengths are listed under Specification details; tolerance and gaging limits are not included. The close-up shows nominal pitch and angle; taper is shown in the overall view.'
            : data.standard_thread
            ? `Illustration only, not to scale. d and P are the nominal thread per ${data.standard_thread}; L is the length you entered. Head, point, drive, lobes, lead-in and the pilot or core hole come from the product drawing, and the hole also depends on the material.`
            : "Illustration only, not to scale. d and L show your entered nominal size, using the supplier's measurement conventions. Pitch, flank shape, lobes, lead-in and pilot hole require the exact product drawing.";
        document.getElementById('family-profile-title').textContent = `${spec.family.toUpperCase()} annotated thread schematic`;
        document.getElementById('family-profile-desc').textContent = [overview.textContent, profile.textContent, note].join('. ');
        document.getElementById('family-profile-note').textContent = note;
        layout();
    }

    new ResizeObserver(layout).observe(svg.parentElement);
    window.threadFamilyDiagram = { render };
})();
