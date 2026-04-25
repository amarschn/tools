const CORDIER_REFERENCE = {
    title: 'Specific Speed Performance Effects',
    url: 'https://www.conceptsnrec.com/blog/specific-speed-performance-effects',
};

const CORDIER_TYPE_ORDER = ['centrifugal_fc', 'centrifugal_bc', 'mixed', 'axial'];

const CORDIER_TYPES = {
    centrifugal_fc: {
        label: 'FC centrifugal',
        short: 'FC',
        color: '#b7791f',
        nsMin: 0.30,
        nsMax: 1.20,
        nsOpt: 0.60,
    },
    centrifugal_bc: {
        label: 'BC centrifugal',
        short: 'BC',
        color: '#475569',
        nsMin: 0.30,
        nsMax: 1.50,
        nsOpt: 0.80,
    },
    mixed: {
        label: 'Mixed flow',
        short: 'Mixed',
        color: '#0f766e',
        nsMin: 0.80,
        nsMax: 3.00,
        nsOpt: 1.80,
    },
    axial: {
        label: 'Axial',
        short: 'Axial',
        color: '#2563eb',
        nsMin: 2.00,
        nsMax: 8.00,
        nsOpt: 3.50,
    },
};

const CORDIER_SAMPLE = {
    dutyLabel: '1.00 m3/s at 500 Pa static',
    leadType: 'centrifugal_bc',
};

function cordierLogSpace(min, max, count = 120) {
    const logMin = Math.log10(min);
    const logMax = Math.log10(max);
    return Array.from({ length: count }, (_, index) => {
        const ratio = count === 1 ? 0 : index / (count - 1);
        return 10 ** (logMin + ratio * (logMax - logMin));
    });
}

function cordierDs(specificSpeed) {
    const lnNs = Math.log(Math.max(specificSpeed, 1.0e-9));
    return Math.exp(0.833 - 0.524 * lnNs + 0.008 * lnNs * lnNs);
}

function cordierEfficiency(specificSpeed) {
    const lnNs = Math.log(Math.max(specificSpeed, 1.0e-9));
    return Math.min(0.95, Math.max(0.20, 0.90 + 0.017 * lnNs - 0.059 * lnNs * lnNs));
}

function cordierHexToRgba(hex, alpha) {
    let normalized = String(hex || '').trim().replace('#', '');
    if (normalized.length === 3) {
        normalized = normalized.split('').map((char) => char + char).join('');
    }
    if (!/^[0-9a-fA-F]{6}$/.test(normalized)) {
        return `rgba(0, 0, 0, ${alpha})`;
    }
    const red = Number.parseInt(normalized.slice(0, 2), 16);
    const green = Number.parseInt(normalized.slice(2, 4), 16);
    const blue = Number.parseInt(normalized.slice(4, 6), 16);
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function cordierMidLog(min, max) {
    return 10 ** ((Math.log10(min) + Math.log10(max)) / 2);
}

function buildEfficiencyEnvelope(level, beta = 5.0, nsMin = 0.20, nsMax = 10.0, count = 160) {
    const nsValues = cordierLogSpace(nsMin, nsMax, count);
    const upperNs = [];
    const upperDs = [];
    const lowerNs = [];
    const lowerDs = [];

    nsValues.forEach((ns) => {
        const etaPeak = cordierEfficiency(ns);
        if (level > etaPeak) return;
        const dsOpt = cordierDs(ns);
        const ratio = level / etaPeak;
        const offset = Math.sqrt(Math.max(0, -Math.log(ratio)) / beta);
        upperNs.push(ns);
        upperDs.push(dsOpt * Math.exp(offset));
        lowerNs.push(ns);
        lowerDs.push(dsOpt * Math.exp(-offset));
    });

    if (upperNs.length < 2) {
        return null;
    }

    return {
        ns: [...upperNs, ...lowerNs.slice().reverse()],
        ds: [...upperDs, ...lowerDs.slice().reverse()],
        labelNs: upperNs[Math.floor(upperNs.length * 0.72)],
        labelDs: upperDs[Math.floor(upperDs.length * 0.72)],
    };
}

function buildCordierAnchors() {
    return CORDIER_TYPE_ORDER.map((typeId) => {
        const meta = CORDIER_TYPES[typeId];
        return {
            typeId,
            label: meta.label,
            short: meta.short,
            color: meta.color,
            ns: meta.nsOpt,
            ds: cordierDs(meta.nsOpt),
        };
    });
}

function baseCordierLayout(options = {}) {
    return {
        margin: { t: 30, r: 26, b: 76, l: 84 },
        paper_bgcolor: options.paperBg || '#ffffff',
        plot_bgcolor: options.plotBg || '#ffffff',
        font: {
            family: "'Helvetica Neue', 'Avenir Next', 'Univers', 'Helvetica', system-ui, sans-serif",
            color: options.textColor || '#111827',
        },
        hovermode: 'closest',
        showlegend: Boolean(options.legend),
        legend: options.legend
            ? {
                orientation: 'h',
                x: 0,
                xanchor: 'left',
                y: -0.20,
                yanchor: 'top',
                font: { size: 11 },
            }
            : undefined,
        xaxis: {
            title: { text: 'Specific Speed N<sub>s</sub> [—]' },
            type: 'log',
            range: [Math.log10(0.20), Math.log10(10.0)],
            tickvals: [0.2, 0.3, 0.5, 1, 2, 3, 5, 10],
            ticktext: ['0.2', '0.3', '0.5', '1', '2', '3', '5', '10'],
            ticks: 'outside',
            ticklen: 6,
            tickwidth: 1,
            tickcolor: options.axisColor || '#111827',
            showline: true,
            linewidth: 1.2,
            linecolor: options.axisColor || '#111827',
            mirror: true,
            gridcolor: options.gridColor || '#d7dde5',
            minor: { showgrid: false },
        },
        yaxis: {
            title: { text: 'Specific Diameter D<sub>s</sub> [—]' },
            type: 'log',
            range: [Math.log10(0.40), Math.log10(6.0)],
            tickvals: [0.4, 0.6, 1, 2, 3, 4, 6],
            ticktext: ['0.4', '0.6', '1', '2', '3', '4', '6'],
            ticks: 'outside',
            ticklen: 6,
            tickwidth: 1,
            tickcolor: options.axisColor || '#111827',
            showline: true,
            linewidth: 1.2,
            linecolor: options.axisColor || '#111827',
            mirror: true,
            gridcolor: options.gridColor || '#d7dde5',
            minor: { showgrid: false },
        },
        annotations: [],
        shapes: [],
    };
}

function addCordierLine(traces, options = {}) {
    const ns = cordierLogSpace(0.20, 10.0, 180);
    traces.push({
        x: ns,
        y: ns.map((value) => cordierDs(value)),
        mode: 'lines',
        name: options.name || 'Cordier optimum',
        line: {
            color: options.color || '#111827',
            width: options.width || 3,
            dash: options.dash || 'solid',
        },
        hovertemplate: 'N_s = %{x:.2f}<br>D_s = %{y:.2f}<extra>Cordier optimum</extra>',
    });
}

function addAnchorMarkers(traces, layout, options = {}) {
    const anchors = buildCordierAnchors();
    const showLegend = Boolean(options.legend);

    traces.push({
        x: anchors.map((item) => item.ns),
        y: anchors.map((item) => item.ds),
        text: anchors.map((item) => item.label),
        mode: 'markers',
        name: options.name || 'Family anchor',
        showlegend: showLegend,
        marker: {
            size: options.size || 10,
            color: anchors.map((item) => item.color),
            line: { color: options.stroke || '#ffffff', width: 1.2 },
            symbol: options.symbol || 'circle',
            opacity: options.opacity || 0.95,
        },
        hovertemplate: '%{text}<br>N_s = %{x:.2f}<br>D_s = %{y:.2f}<extra></extra>',
    });

    if (options.annotate) {
        anchors.forEach((item) => {
            const offset = options.offsets?.[item.typeId] || { ax: 16, ay: -14 };
            layout.annotations.push({
                x: item.ns,
                y: item.ds,
                xref: 'x',
                yref: 'y',
                text: item.label,
                showarrow: true,
                arrowhead: 0,
                arrowwidth: 0.9,
                arrowcolor: options.arrowColor || item.color,
                ax: offset.ax,
                ay: offset.ay,
                bgcolor: options.labelBg || 'rgba(255,255,255,0.84)',
                bordercolor: options.labelBorder || 'rgba(203,213,225,0.9)',
                borderwidth: 1,
                borderpad: 4,
                font: { size: 11, color: options.textColor || '#0f172a' },
            });
        });
    }
}

function addLeadHighlight(traces) {
    const lead = CORDIER_TYPES[CORDIER_SAMPLE.leadType];
    traces.push({
        x: [lead.nsOpt],
        y: [cordierDs(lead.nsOpt)],
        mode: 'markers',
        name: 'Lead type',
        showlegend: false,
        marker: {
            size: 15,
            color: '#ffffff',
            symbol: 'diamond',
            line: { color: '#111827', width: 2.1 },
        },
        hovertemplate: `${lead.label}<br>Lead for ${CORDIER_SAMPLE.dutyLabel}<extra></extra>`,
    });
}

function renderCordierPrototype09(targetId) {
    const traces = [];
    const layout = baseCordierLayout({
        paperBg: '#f8f3e7',
        plotBg: '#f8f3e7',
        gridColor: 'rgba(113, 92, 61, 0.16)',
        axisColor: '#45372c',
        textColor: '#2f241c',
    });

    [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90].forEach((level) => {
        const env = buildEfficiencyEnvelope(level, 5.4);
        if (!env) return;
        traces.push({
            x: env.ns,
            y: env.ds,
            mode: 'lines',
            line: {
                color: level >= 0.85 ? '#6f5a42' : '#a08a72',
                width: level >= 0.85 ? 1.4 : 1.0,
                dash: level >= 0.85 ? 'solid' : 'dot',
            },
            showlegend: false,
            hovertemplate: `${Math.round(level * 100)}% potential efficiency<extra></extra>`,
        });
        layout.annotations.push({
            x: env.labelNs,
            y: env.labelDs,
            xref: 'x',
            yref: 'y',
            text: `${Math.round(level * 100)}%`,
            showarrow: false,
            font: { size: 10, color: '#7b6853' },
            bgcolor: 'rgba(248,243,231,0.78)',
        });
    });

    addCordierLine(traces, { color: '#1f1711', width: 3.2 });
    addAnchorMarkers(traces, layout, {
        size: 9,
        annotate: true,
        stroke: '#f8f3e7',
        offsets: {
            centrifugal_fc: { ax: 12, ay: 18 },
            centrifugal_bc: { ax: 16, ay: -18 },
            mixed: { ax: 16, ay: -16 },
            axial: { ax: 12, ay: -16 },
        },
        labelBg: 'rgba(248,243,231,0.88)',
        labelBorder: 'rgba(123,104,83,0.25)',
        textColor: '#372b21',
    });
    addLeadHighlight(traces);

    layout.annotations.push({
        x: 0.985,
        y: 0.98,
        xref: 'paper',
        yref: 'paper',
        xanchor: 'right',
        yanchor: 'top',
        text: 'Prototype A: paper-style contour chart',
        showarrow: false,
        font: { size: 12, color: '#5a4b3d' },
    });

    Plotly.react(targetId, traces, layout, { responsive: true, displayModeBar: false });
}

function renderCordierPrototype10(targetId) {
    const traces = [];
    const layout = baseCordierLayout({
        paperBg: '#ffffff',
        plotBg: '#ffffff',
        gridColor: '#e7ebf0',
        axisColor: '#0f172a',
        textColor: '#0f172a',
    });

    const bands = [
        { level: 0.60, fill: 'rgba(148, 163, 184, 0.10)', line: 'rgba(100, 116, 139, 0.45)' },
        { level: 0.70, fill: 'rgba(100, 116, 139, 0.10)', line: 'rgba(71, 85, 105, 0.55)' },
        { level: 0.80, fill: 'rgba(51, 65, 85, 0.10)', line: 'rgba(51, 65, 85, 0.70)' },
        { level: 0.88, fill: 'rgba(15, 23, 42, 0.08)', line: 'rgba(15, 23, 42, 0.95)' },
    ];

    bands.forEach((band, index) => {
        const env = buildEfficiencyEnvelope(band.level, 5.0);
        if (!env) return;
        traces.push({
            x: env.ns,
            y: env.ds,
            mode: 'lines',
            line: { color: band.line, width: index === bands.length - 1 ? 1.8 : 1.0 },
            fill: 'toself',
            fillcolor: band.fill,
            showlegend: false,
            hovertemplate: `${Math.round(band.level * 100)}% band<extra></extra>`,
        });
    });

    addCordierLine(traces, { color: '#0f172a', width: 2.8 });
    addAnchorMarkers(traces, layout, {
        size: 9,
        stroke: '#ffffff',
        opacity: 1,
    });
    addLeadHighlight(traces);

    CORDIER_TYPE_ORDER.forEach((typeId) => {
        const meta = CORDIER_TYPES[typeId];
        layout.shapes.push({
            type: 'rect',
            xref: 'x',
            yref: 'paper',
            x0: meta.nsMin,
            x1: meta.nsMax,
            y0: 0.93,
            y1: 0.985,
            line: { width: 0 },
            fillcolor: cordierHexToRgba(meta.color, 0.18),
        });
        layout.annotations.push({
            x: cordierMidLog(meta.nsMin, meta.nsMax),
            y: 1.005,
            xref: 'x',
            yref: 'paper',
            text: meta.label,
            showarrow: false,
            yanchor: 'bottom',
            font: { size: 11, color: '#334155' },
        });
    });

    layout.annotations.push({
        x: 0.02,
        y: 0.98,
        xref: 'paper',
        yref: 'paper',
        xanchor: 'left',
        yanchor: 'top',
        text: 'Prototype B: vertical type bars + monochrome efficiency banding',
        showarrow: false,
        font: { size: 12, color: '#475569' },
        bgcolor: 'rgba(255,255,255,0.92)',
    });

    Plotly.react(targetId, traces, layout, { responsive: true, displayModeBar: false });
}

function renderCordierPrototype11(targetId) {
    const traces = [];
    const layout = baseCordierLayout({
        paperBg: '#f7f8fb',
        plotBg: '#f7f8fb',
        gridColor: '#dde4ee',
        axisColor: '#162032',
        textColor: '#162032',
        legend: true,
    });

    const filled = [
        { level: 0.60, fill: 'rgba(191, 219, 254, 0.22)', line: 'rgba(96, 165, 250, 0.24)' },
        { level: 0.70, fill: 'rgba(147, 197, 253, 0.22)', line: 'rgba(59, 130, 246, 0.28)' },
        { level: 0.80, fill: 'rgba(96, 165, 250, 0.18)', line: 'rgba(37, 99, 235, 0.40)' },
        { level: 0.88, fill: 'rgba(30, 64, 175, 0.12)', line: 'rgba(30, 64, 175, 0.65)' },
    ];

    filled.forEach((band, index) => {
        const env = buildEfficiencyEnvelope(band.level, 5.1);
        if (!env) return;
        traces.push({
            x: env.ns,
            y: env.ds,
            mode: 'lines',
            line: { color: band.line, width: 1.1 },
            fill: 'toself',
            fillcolor: band.fill,
            name: index === 0 ? 'Efficiency field' : undefined,
            showlegend: index === 0,
            hovertemplate: `${Math.round(band.level * 100)}% efficiency neighborhood<extra></extra>`,
        });
        layout.annotations.push({
            x: env.labelNs,
            y: env.labelDs,
            xref: 'x',
            yref: 'y',
            text: `${Math.round(band.level * 100)}%`,
            showarrow: false,
            font: { size: 10, color: '#1d4ed8' },
            bgcolor: 'rgba(247,248,251,0.86)',
        });
    });

    addCordierLine(traces, { color: '#0f172a', width: 3.1, name: 'Cordier optimum line' });
    addAnchorMarkers(traces, layout, {
        size: 10,
        legend: true,
        name: 'Family anchor points',
        annotate: true,
        offsets: {
            centrifugal_fc: { ax: 14, ay: 18 },
            centrifugal_bc: { ax: 18, ay: -14 },
            mixed: { ax: 18, ay: -14 },
            axial: { ax: 12, ay: -14 },
        },
        labelBg: 'rgba(255,255,255,0.86)',
        labelBorder: 'rgba(203,213,225,0.95)',
    });
    addLeadHighlight(traces);

    layout.annotations.push({
        x: 0.02,
        y: 0.98,
        xref: 'paper',
        yref: 'paper',
        xanchor: 'left',
        yanchor: 'top',
        text: 'Prototype C: filled atlas-style efficiency islands',
        showarrow: false,
        font: { size: 12, color: '#334155' },
        bgcolor: 'rgba(255,255,255,0.88)',
    });

    Plotly.react(targetId, traces, layout, { responsive: true, displayModeBar: false });
}

window.CORDIER_REFERENCE = CORDIER_REFERENCE;
window.CORDIER_CHART_UTILS = {
    CORDIER_REFERENCE,
    CORDIER_TYPE_ORDER,
    CORDIER_TYPES,
    CORDIER_SAMPLE,
    cordierLogSpace,
    cordierDs,
    cordierEfficiency,
    cordierHexToRgba,
    cordierMidLog,
    buildEfficiencyEnvelope,
    buildCordierAnchors,
    baseCordierLayout,
    addCordierLine,
    addAnchorMarkers,
    addLeadHighlight,
};
window.renderCordierPrototype09 = renderCordierPrototype09;
window.renderCordierPrototype10 = renderCordierPrototype10;
window.renderCordierPrototype11 = renderCordierPrototype11;
