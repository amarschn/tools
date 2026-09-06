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

    const path = (parent, d, attributes = {}) => node(parent, 'path', { d, class: 'family-outline', ...attributes });
    const line = (parent, x1, y1, x2, y2, attributes = {}) => node(parent, 'line', { x1, y1, x2, y2, class: 'family-dimension-line', ...attributes });
    const label = (parent, x, y, content, attributes = {}) => node(parent, 'text', { x, y, class: 'family-label', ...attributes }, content);
    const number = (value) => Number(value.toPrecision(6)).toString();

    function arrow(parent, tip, toward) {
        const length = Math.hypot(toward[0] - tip[0], toward[1] - tip[1]);
        const ux = (toward[0] - tip[0]) / length;
        const uy = (toward[1] - tip[1]) / length;
        const points = [tip, [tip[0] + 7 * ux - 2 * uy, tip[1] + 7 * uy + 2 * ux],
            [tip[0] + 7 * ux + 2 * uy, tip[1] + 7 * uy - 2 * ux]];
        node(parent, 'polygon', { class: 'family-arrow', points: points.map((point) => point.join(',')).join(' ') });
    }

    function dimension(parent, start, end, text, x, y, vertical = false) {
        const group = node(parent, 'g', { class: 'family-dimension', 'aria-label': text });
        line(group, ...start, ...end);
        arrow(group, start, end);
        arrow(group, end, start);
        label(group, x, y, text, { class: 'family-dimension-text', 'text-anchor': 'middle',
            ...(vertical ? { transform: `rotate(-90 ${x} ${y})` } : {}) });
    }

    function layout() {
        const width = svg.parentElement.clientWidth;
        if (!width) return;
        const narrow = width < 540;
        svg.setAttribute('viewBox', narrow ? '0 0 300 444' : '0 0 620 224');
        overview.setAttribute('transform', 'translate(10 4)');
        profile.setAttribute('transform', narrow ? 'translate(10 224)' : 'translate(330 4)');
    }

    function pipeOverview(spec, data) {
        const tapered = data.diameter_taper > 0;
        const internal = spec.side === 'internal';
        label(overview, 0, 15, `${internal ? 'Internal' : 'External'} · ${tapered ? 'tapered' : 'parallel'}`, { class: 'family-heading' });
        const x1 = 42, x2 = 242, axis = 88;
        const change = (x2 - x1) * data.diameter_taper / 2;
        const r1 = 32 + (internal ? change : 0);
        const r2 = 32 + (internal ? 0 : change);
        const envelope = `M${x1},${axis - r1} L${x2},${axis - r2} V${axis + r2} L${x1},${axis + r1} Z`;
        if (internal) {
            path(overview, `M${x1},34 H${x2} V142 H${x1} Z ${envelope}`, { class: 'family-material', 'fill-rule': 'evenodd' });
        } else path(overview, envelope, { class: 'family-material' });
        path(overview, envelope, { id: 'family-taper-envelope', 'data-diameter-taper': data.diameter_taper });
        line(overview, 26, axis, 264, axis, { class: 'family-axis' });
        label(overview, 145, axis - 6, 'Axis', { class: 'family-muted', 'text-anchor': 'middle' });
        if (tapered) line(overview, x1, axis - r1, x2, axis - r1, { class: 'family-guide' });
        [x1, x2].forEach((x, index) => {
            const r = index ? r2 : r1;
            const dx = index ? 258 : 26;
            line(overview, x, axis - r, dx + (index ? 4 : -4), axis - r);
            line(overview, x, axis + r, dx + (index ? 4 : -4), axis + r);
            dimension(overview, [dx, axis - r], [dx, axis + r], index ? 'ØB' : 'ØA', dx + (index ? 16 : -8), axis, true);
            line(overview, x, axis + r + 4, x, 160);
        });
        dimension(overview, [x1, 155], [x2, 155], 'L', 142, 151);
        label(overview, 142, 184, tapered ? `|ØB − ØA| / L = 1:${number(1 / data.diameter_taper)}` : 'ØA = ØB · no taper', { id: 'family-taper-label', 'text-anchor': 'middle' });
        label(overview, 142, 206, `Half-angle to axis: ${data.half_angle_deg.toFixed(3)}°`, { id: 'family-half-angle', 'text-anchor': 'middle', class: 'family-muted' });
    }

    function productOverview(data) {
        label(overview, 0, 15, 'Nominal size envelope', { class: 'family-heading' });
        const x1 = 58, x2 = 248, top = 52, bottom = 116;
        path(overview, `M${x1},${top} H${x2} V${bottom} H${x1} Z`, { class: 'family-material' });
        path(overview, `M${x1},${top} H${x2} V${bottom} H${x1} Z`);
        line(overview, 46, 84, 264, 84, { class: 'family-axis' });
        [top, bottom].forEach((y) => line(overview, 32, y, x1 - 4, y));
        const diameter = data.diameter == null ? 'd: not specified' : `d = ${number(data.diameter)} ${data.unit}`;
        dimension(overview, [36, top], [36, bottom], diameter, 25, 84, true);
        [x1, x2].forEach((x) => line(overview, x, bottom + 4, x, 158));
        const length = data.length == null ? 'L: not specified' : `L = ${number(data.length)} ${data.unit}`;
        dimension(overview, [x1, 153], [x2, 153], length, 153, 146);
        label(overview, 142, 183, 'd, L: supplier size conventions', { class: 'family-muted', 'text-anchor': 'middle' });
        label(overview, 142, 205, 'Head and tip are not modeled', { class: 'family-muted', 'text-anchor': 'middle' });
    }

    function closeup(data) {
        const pipe = data.kind === 'pipe';
        label(profile, 0, 15, pipe ? 'Family profile · idealized' : 'Thread detail · illustrative', { class: 'family-heading' });
        const pitch = 80, base = 139;
        // Screen-space illustration only. No manufacturing crest/root dimensions
        // or proprietary screw angle are inferred from these proportions.
        const halfAngle = pipe ? data.included_angle_deg * Math.PI / 360 : null;
        const depth = pipe ? .32 * pitch / Math.tan(halfAngle) : 48;
        const points = [];
        for (let tooth = 0; tooth < 3; tooth++) {
            [[0, 0], [.1, 0], [.42, -depth], [.58, -depth], [.9, 0], [1, 0]].forEach(([phase, height]) => {
                points.push([20 + (tooth + phase) * pitch, base + height]);
            });
        }
        const d = 'M' + points.map((point) => point.join(',')).join(' L');
        path(profile, d + ' L260,163 L20,163 Z', { id: 'family-profile-section', class: 'family-material' });
        path(profile, d, { id: 'family-profile-outline' });
        [60, 140].forEach((x) => line(profile, x, base - depth - 4, x, 64));
        const pitchText = pipe ? `P = ${data.pitch_in.toFixed(5)} in` : 'P: supplier data needed';
        dimension(profile, [60, 69], [140, 69], pitchText, 100, 55);
        if (pipe) {
            const vertex = [60, base - .4 * pitch / Math.tan(halfAngle)];
            const radius = 29;
            const left = [vertex[0] - radius * Math.sin(halfAngle), vertex[1] + radius * Math.cos(halfAngle)];
            const right = [vertex[0] + radius * Math.sin(halfAngle), left[1]];
            path(profile, `M${left.join(',')} A${radius},${radius} 0 0 0 ${right.join(',')}`, { class: 'family-dimension-line' });
            arrow(profile, left, [left[0] + Math.cos(halfAngle), left[1] + Math.sin(halfAngle)]);
            arrow(profile, right, [right[0] - Math.cos(halfAngle), right[1] + Math.sin(halfAngle)]);
            label(profile, 60, base - 6, `${data.included_angle_deg}°`, { id: 'family-included-angle', class: 'family-dimension-text', 'text-anchor': 'middle' });
            label(profile, 140, 185, `${number(data.tpi)} TPI · P = ${data.pitch_mm.toFixed(4)} mm`, { id: 'family-pitch-label', 'text-anchor': 'middle' });
            label(profile, 140, 207, 'Crest / root details omitted', { class: 'family-muted', 'text-anchor': 'middle' });
        } else {
            label(profile, 140, 185, 'Flank angle: supplier data needed', { class: 'family-muted', 'text-anchor': 'middle' });
            label(profile, 140, 207, 'Pilot hole: supplier data needed', { class: 'family-muted', 'text-anchor': 'middle' });
        }
    }

    function render(spec) {
        const data = spec.diagram;
        overview.replaceChildren();
        profile.replaceChildren();
        if (data.kind === 'pipe') pipeOverview(spec, data);
        else productOverview(data);
        closeup(data);
        const note = data.kind === 'pipe'
            ? 'Schematic only, not to scale. ØA and ØB are diameters at planes L apart. Gage-plane diameters, thread length and tolerance limits are not yet included. The close-up shows nominal pitch and angle; taper is shown in the overall view.'
            : "Illustration only, not to scale. d and L show your entered nominal size, using the supplier's measurement conventions. Pitch, flank shape, lobes, lead-in and pilot hole require the exact product drawing.";
        document.getElementById('family-profile-title').textContent = `${spec.family.toUpperCase()} annotated thread schematic`;
        document.getElementById('family-profile-desc').textContent = [overview.textContent, profile.textContent, note].join('. ');
        document.getElementById('family-profile-note').textContent = note;
        layout();
    }

    new ResizeObserver(layout).observe(svg.parentElement);
    window.threadFamilyDiagram = { render };
})();
