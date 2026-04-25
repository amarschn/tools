const BALJE = window.CORDIER_CHART_UTILS;

function baljeEtaGrid(nsValues, dsValues, beta = 5.0) {
    return dsValues.map((ds) => (
        nsValues.map((ns) => {
            const etaPeak = BALJE.cordierEfficiency(ns);
            const dsOpt = BALJE.cordierDs(ns);
            const offset = Math.log(ds / dsOpt);
            return etaPeak * Math.exp(-beta * offset * offset);
        })
    ));
}

function baljeSharedAnnotations(layout, noteText) {
    layout.annotations.push({
        x: 0.02,
        y: 0.98,
        xref: 'paper',
        yref: 'paper',
        xanchor: 'left',
        yanchor: 'top',
        text: noteText,
        showarrow: false,
        font: { size: 12, color: '#475569' },
        bgcolor: 'rgba(255,255,255,0.88)',
        bordercolor: 'rgba(226,232,240,0.95)',
        borderwidth: 1,
        borderpad: 5,
    });
}

function addFamilyRangeBands(layout, opacity = 0.10, y0 = 0, y1 = 1) {
    BALJE.CORDIER_TYPE_ORDER.forEach((typeId) => {
        const meta = BALJE.CORDIER_TYPES[typeId];
        layout.shapes.push({
            type: 'rect',
            xref: 'x',
            yref: 'paper',
            x0: meta.nsMin,
            x1: meta.nsMax,
            y0,
            y1,
            line: { width: 0 },
            fillcolor: BALJE.cordierHexToRgba(meta.color, opacity),
            layer: 'below',
        });
    });
}

function addFamilyRangeLabels(layout, yPaper = 1.02) {
    BALJE.CORDIER_TYPE_ORDER.forEach((typeId) => {
        const meta = BALJE.CORDIER_TYPES[typeId];
        layout.annotations.push({
            x: BALJE.cordierMidLog(meta.nsMin, meta.nsMax),
            y: yPaper,
            xref: 'x',
            yref: 'paper',
            text: meta.label,
            showarrow: false,
            font: { size: 11, color: '#334155' },
            yanchor: 'bottom',
        });
    });
}

function addBaljeOptimumMarkers(traces, options = {}) {
    const anchors = BALJE.buildCordierAnchors();
    traces.push({
        x: anchors.map((item) => item.ns),
        y: anchors.map((item) => item.ds),
        text: anchors.map((item) => item.label),
        mode: 'markers',
        showlegend: false,
        marker: {
            size: options.size || 9,
            color: anchors.map((item) => item.color),
            line: { color: options.stroke || '#ffffff', width: 1.1 },
        },
        hovertemplate: '%{text}<br>N_s = %{x:.2f}<br>D_s = %{y:.2f}<extra>Family optimum</extra>',
    });
}

function renderBaljePrototype12(targetId) {
    const ns = BALJE.cordierLogSpace(0.20, 10.0, 140);
    const ds = BALJE.cordierLogSpace(0.40, 6.0, 120);
    const z = baljeEtaGrid(ns, ds, 5.3);
    const traces = [];
    const layout = BALJE.baseCordierLayout({
        paperBg: '#f6f4ee',
        plotBg: '#f6f4ee',
        gridColor: 'rgba(148, 163, 184, 0.22)',
        axisColor: '#2b2d33',
        textColor: '#1f2937',
    });

    addFamilyRangeBands(layout, 0.06);
    addFamilyRangeLabels(layout);

    traces.push({
        type: 'contour',
        x: ns,
        y: ds,
        z,
        contours: {
            start: 0.60,
            end: 0.90,
            size: 0.05,
            coloring: 'none',
            showlabels: true,
            labelfont: { size: 10, color: '#475569' },
        },
        line: { color: '#7c8aa0', width: 1.1 },
        hovertemplate: 'N_s = %{x:.2f}<br>D_s = %{y:.2f}<br>eta ~ %{z:.2f}<extra>Balje contour</extra>',
        showscale: false,
    });

    BALJE.addCordierLine(traces, { color: '#111827', width: 3.1, name: 'Optimum locus' });
    addBaljeOptimumMarkers(traces, { stroke: '#f6f4ee' });
    BALJE.addLeadHighlight(traces);
    baljeSharedAnnotations(layout, 'Prototype L: line-contour Balje sheet');

    Plotly.react(targetId, traces, layout, { responsive: true, displayModeBar: false });
}

function renderBaljePrototype13(mainTargetId, sliceTargetId) {
    const ns = BALJE.cordierLogSpace(0.20, 10.0, 140);
    const ds = BALJE.cordierLogSpace(0.40, 6.0, 120);
    const z = baljeEtaGrid(ns, ds, 5.0);
    const traces = [];
    const layout = BALJE.baseCordierLayout({
        paperBg: '#ffffff',
        plotBg: '#ffffff',
        gridColor: '#e5e7eb',
        axisColor: '#0f172a',
        textColor: '#0f172a',
    });

    addFamilyRangeBands(layout, 0.08);
    addFamilyRangeLabels(layout);

    traces.push({
        type: 'contour',
        x: ns,
        y: ds,
        z,
        autocontour: false,
        contours: {
            start: 0.55,
            end: 0.90,
            size: 0.05,
            coloring: 'heatmap',
            showlabels: true,
            labelfont: { size: 10, color: '#0f172a' },
        },
        colorscale: [
            [0.0, '#f8fbff'],
            [0.2, '#dbeafe'],
            [0.45, '#93c5fd'],
            [0.7, '#60a5fa'],
            [1.0, '#1d4ed8'],
        ],
        line: { color: 'rgba(30, 64, 175, 0.55)', width: 1.0 },
        colorbar: {
            title: { text: 'eta' },
            thickness: 12,
            len: 0.74,
        },
        hovertemplate: 'N_s = %{x:.2f}<br>D_s = %{y:.2f}<br>eta ~ %{z:.2f}<extra>Balje field</extra>',
    });

    BALJE.addCordierLine(traces, { color: '#0f172a', width: 2.8, name: 'Optimum locus' });
    addBaljeOptimumMarkers(traces);
    BALJE.addLeadHighlight(traces);
    baljeSharedAnnotations(layout, 'Prototype M: filled Balje field');

    Plotly.react(mainTargetId, traces, layout, { responsive: true, displayModeBar: false });

    const etaSliceLayout = {
        margin: { t: 20, r: 22, b: 54, l: 56 },
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff',
        font: {
            family: "'Helvetica Neue', 'Avenir Next', 'Univers', 'Helvetica', system-ui, sans-serif",
            color: '#0f172a',
        },
        xaxis: {
            title: { text: 'Specific Speed N_s [—]' },
            type: 'log',
            range: [Math.log10(0.20), Math.log10(10.0)],
            tickvals: [0.2, 0.3, 0.5, 1, 2, 3, 5, 10],
            ticktext: ['0.2', '0.3', '0.5', '1', '2', '3', '5', '10'],
            gridcolor: '#e5e7eb',
            showline: true,
            linecolor: '#0f172a',
            linewidth: 1.1,
            mirror: true,
        },
        yaxis: {
            title: { text: 'Peak eta [—]' },
            range: [0.55, 0.94],
            tickformat: '.0%',
            gridcolor: '#e5e7eb',
            showline: true,
            linecolor: '#0f172a',
            linewidth: 1.1,
            mirror: true,
        },
        shapes: [],
        annotations: [],
        showlegend: false,
    };

    addFamilyRangeBands(etaSliceLayout, 0.12, 0, 1);
    addFamilyRangeLabels(etaSliceLayout, 1.01);

    const etaTrace = {
        x: ns,
        y: ns.map((value) => BALJE.cordierEfficiency(value)),
        mode: 'lines',
        line: { color: '#0f172a', width: 2.6 },
        hovertemplate: 'N_s = %{x:.2f}<br>Peak eta ~ %{y:.1%}<extra>Optimum slice</extra>',
    };

    Plotly.react(sliceTargetId, [etaTrace], etaSliceLayout, { responsive: true, displayModeBar: false });
}

function renderBaljePrototype14(leftTargetId, rightTargetId) {
    const leftTraces = [];
    const leftLayout = BALJE.baseCordierLayout({
        paperBg: '#ffffff',
        plotBg: '#ffffff',
        gridColor: '#e5e7eb',
        axisColor: '#0f172a',
        textColor: '#0f172a',
    });

    addFamilyRangeBands(leftLayout, 0.10);
    addFamilyRangeLabels(leftLayout);
    BALJE.addCordierLine(leftTraces, { color: '#0f172a', width: 3.0, name: 'Cordier optimum' });
    BALJE.addAnchorMarkers(leftTraces, leftLayout, {
        size: 9,
        annotate: true,
        offsets: {
            centrifugal_fc: { ax: 12, ay: 18 },
            centrifugal_bc: { ax: 16, ay: -14 },
            mixed: { ax: 16, ay: -14 },
            axial: { ax: 12, ay: -14 },
        },
        labelBg: 'rgba(255,255,255,0.86)',
        labelBorder: 'rgba(203,213,225,0.95)',
    });
    BALJE.addLeadHighlight(leftTraces);
    baljeSharedAnnotations(leftLayout, 'Cordier: one optimum path plus family references');

    Plotly.react(leftTargetId, leftTraces, leftLayout, { responsive: true, displayModeBar: false });

    const rightTraces = [];
    const rightLayout = BALJE.baseCordierLayout({
        paperBg: '#ffffff',
        plotBg: '#ffffff',
        gridColor: '#e5e7eb',
        axisColor: '#0f172a',
        textColor: '#0f172a',
    });

    addFamilyRangeBands(rightLayout, 0.06);
    addFamilyRangeLabels(rightLayout);

    const ns = BALJE.cordierLogSpace(0.20, 10.0, 120);
    const ds = BALJE.cordierLogSpace(0.40, 6.0, 100);
    const z = baljeEtaGrid(ns, ds, 5.0);
    rightTraces.push({
        type: 'contour',
        x: ns,
        y: ds,
        z,
        autocontour: false,
        contours: {
            start: 0.60,
            end: 0.90,
            size: 0.05,
            coloring: 'none',
            showlabels: true,
            labelfont: { size: 10, color: '#475569' },
        },
        line: { color: '#94a3b8', width: 1.0 },
        hovertemplate: 'N_s = %{x:.2f}<br>D_s = %{y:.2f}<br>eta ~ %{z:.2f}<extra>Balje contour</extra>',
        showscale: false,
    });
    BALJE.addCordierLine(rightTraces, { color: '#0f172a', width: 3.0, name: 'Optimum locus' });
    addBaljeOptimumMarkers(rightTraces);
    BALJE.addLeadHighlight(rightTraces);
    baljeSharedAnnotations(rightLayout, 'Balje: the efficiency field wrapped around that path');

    Plotly.react(rightTargetId, rightTraces, rightLayout, { responsive: true, displayModeBar: false });
}

function logEllipseContour(nsCenter, dsCenter, radiusX, radiusY, rotationDeg, count = 220) {
    const cx = Math.log10(nsCenter);
    const cy = Math.log10(dsCenter);
    const rotation = rotationDeg * Math.PI / 180;
    const x = [];
    const y = [];

    for (let index = 0; index <= count; index += 1) {
        const theta = (Math.PI * 2 * index) / count;
        const localX = radiusX * Math.cos(theta);
        const localY = radiusY * Math.sin(theta);
        const rx = localX * Math.cos(rotation) - localY * Math.sin(rotation);
        const ry = localX * Math.sin(rotation) + localY * Math.cos(rotation);
        x.push(10 ** (cx + rx));
        y.push(10 ** (cy + ry));
    }

    return { x, y };
}

function diagonalRibbonContour(nsMin, nsMax, centerFn, halfWidthFn, count = 180) {
    const ns = BALJE.cordierLogSpace(nsMin, nsMax, count);
    const upper = [];
    const lower = [];

    ns.forEach((value) => {
        const logNs = Math.log10(value);
        const center = centerFn(logNs);
        const halfWidth = typeof halfWidthFn === 'function' ? halfWidthFn(logNs) : halfWidthFn;
        upper.push([value, 10 ** (center + halfWidth)]);
        lower.push([value, 10 ** (center - halfWidth)]);
    });

    return {
        x: [...upper.map((point) => point[0]), ...lower.slice().reverse().map((point) => point[0])],
        y: [...upper.map((point) => point[1]), ...lower.slice().reverse().map((point) => point[1])],
    };
}

function diagonalLine(nsMin, nsMax, lineFn, count = 160) {
    const ns = BALJE.cordierLogSpace(nsMin, nsMax, count);
    return {
        x: ns,
        y: ns.map((value) => 10 ** lineFn(Math.log10(value))),
    };
}

function addContourLabel(layout, x, y, text, opts = {}) {
    layout.annotations.push({
        x,
        y,
        xref: 'x',
        yref: 'y',
        text,
        showarrow: false,
        font: {
            size: opts.size || 10,
            color: opts.color || '#374151',
            family: "'Helvetica Neue', 'Avenir Next', 'Univers', 'Helvetica', system-ui, sans-serif",
        },
        bgcolor: opts.bg || 'rgba(255,255,255,0.80)',
        borderpad: 2,
    });
}

function renderBaljePrototype15(targetId) {
    const traces = [];
    const layout = {
        margin: { t: 28, r: 24, b: 66, l: 76 },
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff',
        font: {
            family: "'Helvetica Neue', 'Avenir Next', 'Univers', 'Helvetica', system-ui, sans-serif",
            color: '#111827',
        },
        xaxis: {
            title: { text: 'Specific speed (N_s)' },
            type: 'log',
            range: [Math.log10(0.001), Math.log10(10000)],
            tickvals: [0.001, 0.003, 0.006, 0.01, 0.03, 0.06, 0.1, 0.3, 0.6, 1, 3, 6, 10, 30, 60, 100, 300, 600, 1000, 3000, 6000, 10000],
            ticktext: ['0.001', '0.003', '0.006', '0.01', '0.03', '0.06', '0.1', '0.3', '0.6', '1', '3', '6', '10', '30', '60', '100', '300', '600', '1000', '3000', '6000', '10000'],
            ticks: 'outside',
            ticklen: 5,
            showline: true,
            linecolor: '#111827',
            linewidth: 1.1,
            mirror: true,
            gridcolor: 'rgba(17,24,39,0.18)',
        },
        yaxis: {
            title: { text: 'Specific diameter (D_s)' },
            type: 'log',
            range: [Math.log10(0.1), Math.log10(100)],
            tickvals: [0.1, 0.3, 0.6, 1, 3, 6, 10, 30, 60, 100],
            ticktext: ['0.1', '0.3', '0.6', '1', '3', '6', '10', '30', '60', '100'],
            ticks: 'outside',
            ticklen: 5,
            showline: true,
            linecolor: '#111827',
            linewidth: 1.1,
            mirror: true,
            gridcolor: 'rgba(17,24,39,0.18)',
        },
        showlegend: false,
        annotations: [],
    };

    const pistonOffsets = [0.16, 0.10, 0.04, -0.02, -0.08, -0.14];
    pistonOffsets.forEach((offset) => {
        const line = diagonalLine(0.0012, 0.18, (logNs) => 1.18 - 0.34 * (logNs + 2.1) + offset);
        traces.push({
            x: line.x,
            y: line.y,
            mode: 'lines',
            line: { color: '#111827', width: 1.2 },
            hoverinfo: 'skip',
        });
    });
    addContourLabel(layout, 0.0016, 40, '0.5');
    addContourLabel(layout, 0.0032, 34, '0.6');
    addContourLabel(layout, 0.006, 24, '0.7');
    addContourLabel(layout, 0.010, 16, '0.8');
    addContourLabel(layout, 0.022, 42, 'S/D = 0.25', { size: 10 });
    layout.annotations.push({
        x: 0.014,
        y: 42,
        xref: 'x',
        yref: 'y',
        text: 'Piston expanders',
        showarrow: true,
        arrowhead: 0,
        ax: 58,
        ay: -18,
        font: { size: 11, color: '#111827' },
        bgcolor: 'rgba(255,255,255,0.84)',
    });

    const dragContours = [
        { ns: 1.1, ds: 19, rx: 0.23, ry: 0.60, rot: 35, label: '0.3', lx: 0.9, ly: 28 },
        { ns: 1.9, ds: 14, rx: 0.21, ry: 0.48, rot: 35, label: '0.4', lx: 1.4, ly: 16 },
        { ns: 3.0, ds: 10, rx: 0.19, ry: 0.38, rot: 35, label: '0.5', lx: 3.2, ly: 9 },
        { ns: 4.8, ds: 7.2, rx: 0.16, ry: 0.28, rot: 35, label: '0.6', lx: 4.7, ly: 6.2 },
    ];
    dragContours.forEach((contour) => {
        const line = logEllipseContour(contour.ns, contour.ds, contour.rx, contour.ry, contour.rot);
        traces.push({
            x: line.x,
            y: line.y,
            mode: 'lines',
            line: { color: '#111827', width: 1.4 },
            hoverinfo: 'skip',
        });
        addContourLabel(layout, contour.lx, contour.ly, contour.label);
    });
    layout.annotations.push({
        x: 0.35,
        y: 17,
        xref: 'x',
        yref: 'y',
        text: 'Drag<br>turbines',
        showarrow: true,
        arrowhead: 0,
        ax: -8,
        ay: 30,
        align: 'center',
        font: { size: 11, color: '#111827' },
        bgcolor: 'rgba(255,255,255,0.84)',
    });

    const hdLines = [
        { label: '0.01', shift: 0.18 },
        { label: '0.02 = h/D', shift: 0.10 },
        { label: '0.04', shift: 0.02 },
        { label: '0.06', shift: -0.05 },
        { label: '0.08', shift: -0.11 },
        { label: '0.1', shift: -0.17 },
    ];
    hdLines.forEach((item, index) => {
        const line = diagonalLine(0.7, 70, (logNs) => 1.48 - 0.55 * logNs + item.shift);
        traces.push({
            x: line.x,
            y: line.y,
            mode: 'lines',
            line: { color: '#374151', width: 1.0, dash: 'dot' },
            opacity: 0.9,
            hoverinfo: 'skip',
        });
        addContourLabel(layout, [1.7, 2.5, 7, 12, 18, 28][index], [28, 19, 10, 6.5, 4.8, 3.7][index], item.label, { size: 10 });
    });

    const turbineRibbons = [
        { width: 0.21, label: '0.6', lx: 90, ly: 2.1 },
        { width: 0.17, label: '0.7', lx: 120, ly: 1.6 },
        { width: 0.13, label: '0.8', lx: 180, ly: 1.20 },
        { width: 0.09, label: '0.9', lx: 320, ly: 0.95 },
    ];
    turbineRibbons.forEach((item) => {
        const contour = diagonalRibbonContour(
            4,
            10000,
            (logNs) => 0.72 - 0.37 * logNs + 0.03 * logNs * logNs,
            item.width,
        );
        traces.push({
            x: contour.x,
            y: contour.y,
            mode: 'lines',
            line: { color: '#111827', width: 1.5 },
            hoverinfo: 'skip',
        });
        addContourLabel(layout, item.lx, item.ly, item.label);
    });

    layout.annotations.push({
        x: 32,
        y: 22,
        xref: 'x',
        yref: 'y',
        text: 'Full admission<br>axial turbines',
        showarrow: true,
        arrowhead: 0,
        ax: 40,
        ay: -10,
        align: 'left',
        font: { size: 11, color: '#111827' },
        bgcolor: 'rgba(255,255,255,0.84)',
    });
    layout.annotations.push({
        x: 16,
        y: 70,
        xref: 'x',
        yref: 'y',
        text: 'Partial admission<br>axial turbines',
        showarrow: true,
        arrowhead: 0,
        ax: -58,
        ay: -6,
        align: 'right',
        font: { size: 11, color: '#111827' },
        bgcolor: 'rgba(255,255,255,0.84)',
    });
    layout.annotations.push({
        x: 110,
        y: 3.0,
        xref: 'x',
        yref: 'y',
        text: 'Operating regime where<br>radial turbines have<br>equivalent performance',
        showarrow: true,
        arrowhead: 0,
        ax: 60,
        ay: -30,
        align: 'left',
        font: { size: 11, color: '#111827' },
        bgcolor: 'rgba(255,255,255,0.84)',
    });
    layout.annotations.push({
        x: 0.0035,
        y: 1.6,
        xref: 'x',
        yref: 'y',
        text: 'Concepts NREC style turbine atlas',
        showarrow: false,
        font: { size: 12, color: '#374151' },
        bgcolor: 'rgba(255,255,255,0.88)',
    });

    Plotly.react(targetId, traces, layout, { responsive: true, displayModeBar: false });
}

function renderBaljePrototype16(targetId) {
    const traces = [];
    const layout = BALJE.baseCordierLayout({
        paperBg: '#ffffff',
        plotBg: '#ffffff',
        gridColor: 'rgba(17,24,39,0.12)',
        axisColor: '#111827',
        textColor: '#111827',
    });

    layout.xaxis.range = [Math.log10(0.20), Math.log10(4.0)];
    layout.yaxis.range = [Math.log10(0.8), Math.log10(8.5)];

    [0.68, 0.72, 0.76, 0.80, 0.84, 0.88].forEach((level) => {
        const env = BALJE.buildEfficiencyEnvelope(level, 5.4, 0.22, 3.6, 180);
        if (!env) return;
        traces.push({
            x: env.ns,
            y: env.ds,
            mode: 'lines',
            line: { color: '#111827', width: 1.2 },
            hoverinfo: 'skip',
        });
        addContourLabel(layout, env.labelNs, env.labelDs, `${Math.round(level * 100)}`, { size: 10 });
    });

    BALJE.addCordierLine(traces, { color: '#111827', width: 3.0, name: 'Actual Cordier line' });

    const baseNs = BALJE.cordierLogSpace(0.25, 3.2, 160);
    const modifiedCurves = [
        { label: 'Re = 2e5', nsFactor: 0.90, dsFactor: 0.93, color: '#475569', dash: 'dot' },
        { label: 'Re = 1e5', nsFactor: 0.78, dsFactor: 0.84, color: '#1d4ed8', dash: 'dash' },
        { label: 'Re = 5e4', nsFactor: 0.66, dsFactor: 0.73, color: '#b91c1c', dash: 'longdash' },
    ];
    modifiedCurves.forEach((curve, index) => {
        const ns = baseNs.map((value) => value * curve.nsFactor);
        const ds = baseNs.map((value) => BALJE.cordierDs(value) * curve.dsFactor);
        traces.push({
            x: ns,
            y: ds,
            mode: 'lines',
            line: { color: curve.color, width: 2.0, dash: curve.dash },
            name: curve.label,
            hovertemplate: `${curve.label}<br>N_s = %{x:.2f}<br>D_s = %{y:.2f}<extra>Modified Cordier</extra>`,
        });
        addContourLabel(layout, ns[Math.floor(ns.length * 0.60)], ds[Math.floor(ds.length * 0.60)] * (1.02 + index * 0.01), curve.label, {
            size: 10,
            color: curve.color,
        });
    });

    layout.legend = {
        orientation: 'h',
        x: 0,
        xanchor: 'left',
        y: -0.18,
        yanchor: 'top',
        font: { size: 11, color: '#111827' },
    };
    layout.showlegend = true;

    layout.annotations.push({
        x: 0.02,
        y: 0.98,
        xref: 'paper',
        yref: 'paper',
        xanchor: 'left',
        yanchor: 'top',
        text: 'MDPI Figure 8 style: standard Balje compressor map + low-Re modified Cordier lines',
        showarrow: false,
        font: { size: 12, color: '#374151' },
        bgcolor: 'rgba(255,255,255,0.90)',
        bordercolor: 'rgba(203,213,225,0.95)',
        borderwidth: 1,
        borderpad: 5,
    });

    Plotly.react(targetId, traces, layout, { responsive: true, displayModeBar: false });
}

function renderBaljePrototype17(targetId) {
    const traces = [];
    const layout = BALJE.baseCordierLayout({
        paperBg: '#ffffff',
        plotBg: '#ffffff',
        gridColor: 'rgba(17,24,39,0.12)',
        axisColor: '#111827',
        textColor: '#111827',
    });

    [0.68, 0.72, 0.76, 0.80, 0.84, 0.88].forEach((level) => {
        const env = BALJE.buildEfficiencyEnvelope(level, 5.2, 0.22, 8.0, 180);
        if (!env) return;
        traces.push({
            x: env.ns,
            y: env.ds,
            mode: 'lines',
            line: { color: '#111827', width: level >= 0.84 ? 1.3 : 1.0 },
            hoverinfo: 'skip',
            showlegend: false,
        });
        addContourLabel(layout, env.labelNs, env.labelDs, `${Math.round(level * 100)}`, { size: 10 });
    });

    BALJE.addCordierLine(traces, { color: '#111827', width: 2.7, name: 'Optimum locus' });
    addFamilyRangeBands(layout, 0.10, 0.93, 0.985);
    addFamilyRangeLabels(layout, 1.01);

    const samplePoints = BALJE.buildCordierAnchors();
    traces.push({
        x: samplePoints.map((item) => item.ns),
        y: samplePoints.map((item) => item.ds),
        text: samplePoints.map((item) => item.label),
        mode: 'markers',
        showlegend: false,
        marker: {
            size: 9,
            color: samplePoints.map((item) => item.color),
            line: { color: '#ffffff', width: 1.2 },
        },
        hovertemplate: '%{text}<br>N_s = %{x:.2f}<br>D_s = %{y:.2f}<extra>Family anchor</extra>',
    });

    BALJE.addLeadHighlight(traces);

    layout.annotations.push({
        x: 0.02,
        y: 0.98,
        xref: 'paper',
        yref: 'paper',
        xanchor: 'left',
        yanchor: 'top',
        text: 'Published-style production candidate: field first, family screen second',
        showarrow: false,
        font: { size: 12, color: '#374151' },
        bgcolor: 'rgba(255,255,255,0.90)',
        bordercolor: 'rgba(203,213,225,0.95)',
        borderwidth: 1,
        borderpad: 5,
    });

    Plotly.react(targetId, traces, layout, { responsive: true, displayModeBar: false });
}

window.renderBaljePrototype12 = renderBaljePrototype12;
window.renderBaljePrototype13 = renderBaljePrototype13;
window.renderBaljePrototype14 = renderBaljePrototype14;
window.renderBaljePrototype15 = renderBaljePrototype15;
window.renderBaljePrototype16 = renderBaljePrototype16;
window.renderBaljePrototype17 = renderBaljePrototype17;
