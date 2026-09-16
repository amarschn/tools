/* Interface adapted from tools/example_tool_advanced. All mechanics are in Python. */
'use strict';

const TOOL_MODULE_NAME = 'stability';
const TOOL_FUNCTION_NAME = 'analyze_tipping';
const PARAM_ORDER = ['wheelbase', 'track', 'cg_height', 'mass', 'cg_x', 'cg_y', 'load_case', 'slope_deg', 'downhill_deg', 'acceleration', 'accel_direction', 'speed', 'turn_radius', 'turn_direction', 'force', 'force_direction', 'force_height', 'force_x', 'force_y', 'force_vertical', 'friction_coefficient', 'contacts', 'components', 'extra_forces', 'limit_parameter'];
const STORAGE_KEY = 'tipping-stability-settings';
const defaultSettings = { theme: 'system', density: 'comfortable', precision: 2 };
const $ = (id) => document.getElementById(id);
const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let settings = { ...defaultSettings };
let pyodide;
let lastResults = null;
let lastInputs = null;
let lastForm = null;
let selectedEdge = null;
let openDerivation = null;
let dirty = false;
let mathQueue = Promise.resolve();

const editors = {
    components: {
        fields: ['name', 'mass', 'x', 'y', 'z'],
        labels: ['Name', 'Mass (kg), positive', 'Forward coordinate (m)', 'Left coordinate (m)', 'Height above the surface (m)'],
        defaults: [{ name: 'Base', mass: 80, x: 0, y: 0, z: .3 }, { name: 'Payload', mass: 20, x: 0, y: 0, z: 1.8 }],
        blank: { name: 'Payload', mass: 10, x: 0, y: 0, z: .6 },
    },
    contacts: {
        fields: ['x', 'y'], labels: ['Forward ground-contact coordinate (m)', 'Left ground-contact coordinate (m)'],
        defaults: [[-.6, -.4], [.6, -.4], [.6, .4], [-.6, .4]], blank: { x: 0, y: 0 },
    },
    extra_forces: {
        fields: ['name', 'fx', 'fy', 'fz', 'x', 'y', 'z'],
        labels: ['Name', 'Forward force (N)', 'Left force (N)', 'Normal force (N), positive upward', 'Forward application coordinate (m)', 'Left application coordinate (m)', 'Application height (m)'],
        defaults: [], blank: { name: 'Attachment', fx: 0, fy: 0, fz: -50, x: 0, y: 0, z: 1 },
    },
};

function formatNumber(value, precision = settings.precision) {
    if (!Number.isFinite(value)) return 'Not defined';
    if (value !== 0 && (Math.abs(value) >= 1e7 || Math.abs(value) < 10 ** -precision)) return value.toExponential(precision);
    return value.toFixed(precision);
}

function valueWithUnit(value, unit) {
    return `${formatNumber(value)} <span class="unit">${escapeHtml(unit)}</span>`;
}

function typesetMath(elements) {
    mathQueue = mathQueue.then(async () => {
        if (window.MathJax?.startup?.promise) await MathJax.startup.promise;
        if (window.MathJax?.typesetPromise) await MathJax.typesetPromise(elements);
    }).catch(() => {});
    return mathQueue;
}

function applySettings() {
    document.body.dataset.theme = settings.theme;
    document.body.dataset.density = settings.density;
    for (const key of ['theme', 'density', 'precision']) {
        document.querySelectorAll(`.settings-panel [data-${key}]`).forEach((button) => {
            const active = String(settings[key]) === button.dataset[key];
            button.classList.toggle('active', active);
            button.setAttribute('aria-pressed', String(active));
        });
    }
    if (lastResults) renderResults();
}

function toggleSettingsPanel(open) {
    const panel = $('settings-panel');
    panel.classList.toggle('open', open);
    panel.inert = !open;
    panel.setAttribute('aria-hidden', String(!open));
    $('settings-overlay').classList.toggle('open', open);
    $('settings-overlay').setAttribute('aria-hidden', String(!open));
    $('tool-main').inert = open;
    document.querySelector('.navbar').inert = open;
    if (open) $('settings-close').focus();
    else $('settings-button').focus();
}

function bindSettings() {
    try {
        const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        if (['light', 'dark', 'system'].includes(stored.theme)) settings.theme = stored.theme;
        if (['comfortable', 'compact'].includes(stored.density)) settings.density = stored.density;
        if ([2, 3, 4].includes(stored.precision)) settings.precision = stored.precision;
    } catch (_) { /* Storage may be unavailable. Defaults remain usable. */ }
    const save = () => {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)); } catch (_) {}
        applySettings();
    };
    for (const key of ['theme', 'density', 'precision']) {
        document.querySelectorAll(`.settings-panel [data-${key}]`).forEach((button) => button.addEventListener('click', () => {
            settings[key] = key === 'precision' ? Number(button.dataset[key]) : button.dataset[key];
            save();
        }));
    }
    $('settings-reset').addEventListener('click', () => { settings = { ...defaultSettings }; save(); });
    $('settings-button').addEventListener('click', () => toggleSettingsPanel(true));
    $('settings-close').addEventListener('click', () => toggleSettingsPanel(false));
    $('settings-overlay').addEventListener('click', () => toggleSettingsPanel(false));
    $('settings-panel').addEventListener('keydown', (event) => {
        if (event.key !== 'Tab') return;
        const controls = [...$('settings-panel').querySelectorAll('button')];
        if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1).focus(); }
        if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0].focus(); }
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            $('help-popup').hidden = true;
            if ($('settings-panel').classList.contains('open')) toggleSettingsPanel(false);
        }
    });
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (settings.theme === 'system' && lastResults) renderPlots(); });
    applySettings();
}

function showHelp(target) {
    const id = target.dataset.for;
    const text = id ? $('help-' + id)?.textContent : target.title;
    if (!text) return;
    const popup = $('help-popup');
    popup.textContent = text;
    popup.hidden = false;
    const box = target.getBoundingClientRect();
    const width = popup.offsetWidth;
    popup.style.left = Math.max(12, Math.min(innerWidth - width - 12, box.right - width)) + 'px';
    const height = popup.offsetHeight;
    popup.style.top = Math.max(12, Math.min(innerHeight - height - 12, box.bottom + 8)) + 'px';
}

function bindHelp() {
    document.addEventListener('pointerover', (event) => {
        const target = event.target.closest('.tooltip-trigger, .editor-table input');
        if (target) showHelp(target);
    });
    document.addEventListener('pointerout', (event) => {
        if (event.target.closest('.tooltip-trigger, .editor-table input')) $('help-popup').hidden = true;
    });
    document.addEventListener('focusin', (event) => {
        if (event.target.matches('.tooltip-trigger, .editor-table input')) showHelp(event.target);
        else $('help-popup').hidden = true;
    });
    document.addEventListener('click', (event) => {
        const target = event.target.closest('.tooltip-trigger');
        if (target) showHelp(target);
        else $('help-popup').hidden = true;
    });
    window.addEventListener('scroll', () => { $('help-popup').hidden = true; }, true);
}

function parseEditor(key) {
    let rows;
    try { rows = JSON.parse($(key).value); } catch (_) { throw new Error(`The shared ${key.replaceAll('_', ' ')} data is invalid. Reset the example or edit that table.`); }
    if (!Array.isArray(rows) || rows.length > 100) throw new Error(`The ${key.replaceAll('_', ' ')} table must contain at most 100 rows.`);
    return rows;
}

function renderEditor(key, rows) {
    const schema = editors[key];
    const body = $(key + '-rows');
    body.replaceChildren();
    rows.forEach((original, index) => {
        let data = original;
        if (key === 'contacts') data = { x: original?.[0], y: original?.[1] };
        if (key === 'extra_forces') data = { name: original?.name, fx: original?.vector?.[0], fy: original?.vector?.[1], fz: original?.vector?.[2], x: original?.point?.[0], y: original?.point?.[1], z: original?.point?.[2] };
        const tr = document.createElement('tr');
        schema.fields.forEach((field, column) => {
            const td = document.createElement('td');
            const input = document.createElement('input');
            input.type = field === 'name' ? 'text' : 'number';
            input.dataset.field = field;
            input.value = data?.[field] ?? '';
            input.title = schema.labels[column];
            input.setAttribute('aria-label', `Row ${index + 1}: ${schema.labels[column]}`);
            input.setAttribute('aria-describedby', key + '-guide');
            if (field === 'name') input.maxLength = 80;
            else { input.step = 'any'; input.required = true; }
            if (field === 'mass') input.min = '.000000001';
            if (field === 'z') input.min = '0';
            td.append(input);
            tr.append(td);
        });
        const td = document.createElement('td');
        const remove = document.createElement('button');
        remove.type = 'button'; remove.className = 'remove-row'; remove.textContent = '×';
        remove.setAttribute('aria-label', `Remove ${key.replaceAll('_', ' ')} row ${index + 1}`);
        remove.addEventListener('click', () => {
            tr.remove(); serializeEditor(key); syncVisibility(); markDirty();
            document.querySelector(`[data-add="${key}"]`).focus();
        });
        td.append(remove); tr.append(td); body.append(tr);
    });
}

function serializeEditor(key) {
    const rows = [...$(key + '-rows').children].map((tr) => {
        const data = Object.fromEntries([...tr.querySelectorAll('input')].map((input) => [input.dataset.field, input.type === 'number' && input.value !== '' ? Number(input.value) : input.value]));
        if (key === 'contacts') return [data.x, data.y];
        if (key === 'extra_forces') return { name: data.name, vector: [data.fx, data.fy, data.fz], point: [data.x, data.y, data.z] };
        return data;
    });
    $(key).value = JSON.stringify(rows);
    $(key).dispatchEvent(new Event('input', { bubbles: true }));
    return rows;
}

function initEditors() {
    const params = new URLSearchParams(location.search);
    for (const [key, schema] of Object.entries(editors)) {
        const value = params.has(key) ? $(key).value : JSON.stringify(schema.defaults);
        $(key).defaultValue = JSON.stringify(schema.defaults);
        $(key).value = value;
        try { renderEditor(key, parseEditor(key)); } catch (_) { renderEditor(key, []); }
        $(key + '-rows').addEventListener('input', () => serializeEditor(key));
        document.querySelector(`[data-add="${key}"]`).addEventListener('click', () => {
            let rows;
            try { rows = parseEditor(key); } catch (_) { rows = []; }
            if (rows.length >= 100) return;
            const blank = structuredClone(schema.blank);
            rows.push(key === 'contacts' ? [blank.x, blank.y] : key === 'extra_forces' ? { name: blank.name, vector: [blank.fx, blank.fy, blank.fz], point: [blank.x, blank.y, blank.z] } : blank);
            renderEditor(key, rows); serializeEditor(key); syncVisibility();
            $(key + '-rows').lastElementChild.querySelector('input').focus();
        });
    }
}

function syncVisibility() {
    const mode = $('load_case').value;
    document.querySelectorAll('[data-cases]').forEach((el) => { el.hidden = !el.dataset.cases.split(' ').includes(mode); });
    const custom = $('geometry_mode').value === 'custom';
    $('rectangle-inputs').hidden = custom;
    $('contacts-editor').hidden = !custom;
    const components = $('mass_mode').value === 'components';
    $('single-mass-inputs').hidden = components;
    document.querySelector('[data-group="cg_height"]').hidden = components;
    $('component-summary').hidden = !components;
    $('components-editor').hidden = !components;
    $('extra_forces-editor').hidden = false;
    $('calc-form').querySelectorAll('input:not([hidden]), select').forEach((input) => { input.disabled = Boolean(input.closest('[hidden]')); });
}

function markDirty() {
    if (!lastResults) return;
    dirty = true;
    $('dirty-note').hidden = false;
    $('export-csv').disabled = true;
    $('export-json').disabled = true;
}

function readInputs() {
    const inputs = {};
    const strings = ['load_case', 'turn_direction', 'limit_parameter'];
    for (const key of PARAM_ORDER) {
        if (key in editors) continue;
        const raw = $(key).value;
        if (strings.includes(key)) inputs[key] = raw;
        else if (key === 'friction_coefficient') inputs[key] = raw === '' ? null : Number(raw);
        else if ($(key).disabled) continue;
        else {
            if (raw === '' || !Number.isFinite(Number(raw))) throw new Error(`Enter a finite value for ${key.replaceAll('_', ' ')}.`);
            inputs[key] = Number(raw);
        }
    }
    inputs.contacts = $('geometry_mode').value === 'custom' ? parseEditor('contacts') : null;
    inputs.components = $('mass_mode').value === 'components' ? parseEditor('components') : null;
    inputs.extra_forces = ['push', 'combined'].includes(inputs.load_case) ? parseEditor('extra_forces') : null;
    return inputs;
}

function callPython(inputs) {
    pyodide.globals.set('_tipping_inputs', JSON.stringify(inputs));
    return JSON.parse(pyodide.runPython(`json.dumps(${TOOL_MODULE_NAME}.${TOOL_FUNCTION_NAME}(**json.loads(_tipping_inputs)), allow_nan=False)`));
}

function clearResults(message) {
    lastResults = null;
    lastInputs = null;
    $('error-message').textContent = message;
    $('error-message').hidden = false;
    $('result-content').hidden = true;
    $('results-placeholder').hidden = true;
    $('dirty-note').hidden = true;
    $('direction-note').textContent = 'Calculate a valid case to draw the direction limits.';
    if ($('direction-plot').data) Plotly.purge('direction-plot');
}

async function calculate(event) {
    event?.preventDefault();
    if (!pyodide) return;
    syncVisibility();
    const invalid = $('calc-form').querySelector(':invalid:not(:disabled)');
    if (invalid) {
        let parent = invalid.parentElement;
        while (parent) { if (parent.tagName === 'DETAILS') parent.open = true; parent = parent.parentElement; }
        clearResults('Check the highlighted input. Results are cleared until the case is valid.');
        invalid.reportValidity();
        return;
    }
    $('calculate-btn').disabled = true;
    $('calculate-btn').textContent = 'Calculating…';
    try {
        const inputs = readInputs();
        const result = callPython(inputs);
        lastInputs = inputs;
        lastResults = result;
        lastForm = Object.fromEntries([...$('calc-form').querySelectorAll('input[id], select[id]')].map((el) => [el.id, el.value]));
        selectedEdge = result.equilibrium.governing_edge;
        dirty = false;
        $('dirty-note').hidden = true;
        $('error-message').hidden = true;
        renderResults();
    } catch (error) {
        const lines = String(error.message).trim().split('\n');
        clearResults(lines.at(-1).replace(/^(ValueError|TypeError):\s*/, ''));
    } finally {
        $('calculate-btn').disabled = false;
        $('calculate-btn').textContent = 'Calculate stability';
    }
}

function equationCards(ids, source = lastResults?.theory) {
    if (!source) return '';
    return source.map((equation, i) => ({ ...equation, number: i + 1 })).filter((eq) => !ids || ids.includes(eq.id)).map((eq) => `<div class="equation-card"><strong>Equation (${eq.number}): ${escapeHtml(eq.title)}</strong><span class="equation-expression">\\[${escapeHtml(eq.latex)}\\]</span><p>${escapeHtml(eq.legend)}</p></div>`).join('');
}

function showDerivation(key) {
    openDerivation = openDerivation === key ? null : key;
    renderDerivation();
}

function renderDerivation() {
    $('derivation-panel').hidden = !openDerivation;
    document.querySelectorAll('[data-derivation]').forEach((button) => {
        const active = button.dataset.derivation === openDerivation;
        button.classList.toggle('expanded', active);
        button.setAttribute('aria-expanded', String(active));
    });
    if (!openDerivation || !lastResults) return;
    const { threshold: t, equilibrium: e } = lastResults;
    const details = {
        threshold: { title: t.title, equations: ['force', 'moment', 'margin'], text: t.held, subst: lastResults.subst_threshold },
        margin: { title: 'Margin to the nearest edge', equations: ['margin'], text: `${e.governing_label}: ${formatNumber(e.margin)} m. Moments from individual loads are listed below the diagrams.`, subst: lastResults.subst_margin },
        reaction: { title: 'Ground reaction and moment reserve', equations: ['force', 'moment', 'reaction'], text: `Resultant non-contact force: (${e.force.map((v) => formatNumber(v)).join(', ')}) N. Moment: (${e.moment.map((v) => formatNumber(v)).join(', ')}) N·m.`, subst: lastResults.subst_reaction },
        mass: { title: 'Combined mass and center', equations: ['mass'], text: lastResults.mass_components.map((c) => `${c.name}: ${formatNumber(c.mass)} kg at (${[c.x, c.y, c.z].map((v) => formatNumber(v)).join(', ')}) m.`).join(' '), subst: lastResults.subst_mass },
    }[openDerivation];
    $('derivation-title').textContent = details.title;
    window.MathJax?.typesetClear?.([$('derivation-content')]);
    $('derivation-content').innerHTML = equationCards(details.equations) + `<p>${escapeHtml(details.text)}</p><div class="equation-card"><strong>Substituted values</strong><span class="equation-expression">\\[${escapeHtml(details.subst)}\\]</span></div>`;
    typesetMath([$('derivation-content')]);
}

function renderResults() {
    const { equilibrium: e, threshold: t } = lastResults;
    $('results-placeholder').hidden = true;
    $('result-content').hidden = false;
    $('status-banner').className = 'status-banner ' + e.status;
    $('status-title').textContent = { positive: 'Positive tipping margin', threshold: 'At the tipping threshold', beyond: 'Beyond the tipping threshold' }[e.status];
    $('status-detail').textContent = `${e.governing_label} is the nearest support edge. ${e.status === 'beyond' ? 'The required normal reaction lies outside the support polygon.' : 'This describes normal-force equilibrium for the stated rigid-body model.'}`;
    $('threshold-label').textContent = t.title;
    $('threshold-value').innerHTML = t.state === 'finite' ? valueWithUnit(t.value, t.unit) : `<span class="unit">${t.state === 'baseline_unstable' ? 'No stable start' : 'No finite limit'}</span>`;
    $('threshold-demand').textContent = t.state === 'finite' ? `Current ${formatNumber(t.demand)} ${t.unit} · remaining ${formatNumber(t.remaining)} ${t.unit}` : t.state === 'baseline_unstable' ? 'The zero-load starting point is outside the model’s stable region.' : 'The selected sweep does not exhaust the tipping reserve.';
    $('threshold-note').textContent = `${t.held}${t.edge ? ' Boundary: ' + t.edge + '.' : ''} This is a model threshold, not a rated operating limit.`;
    $('margin-value').innerHTML = valueWithUnit(e.margin * 1000, 'mm');
    $('margin-edge').textContent = e.governing_label + ' · click for derivation';
    $('moment-value').innerHTML = valueWithUnit(e.moment_reserve, 'N·m');
    $('height-value').innerHTML = valueWithUnit(e.center[2], 'm');
    $('mass-value').textContent = `Total mass ${formatNumber(e.mass)} kg · click for components`;
    const f = e.friction;
    $('friction-note').className = 'friction-note ' + f.status;
    $('friction-note').textContent = f.status === 'unevaluated' ? 'Sliding has not been evaluated. Add a friction coefficient under advanced options for an aggregate translation check.' : `Aggregate sliding check: ${f.status === 'exceeded' ? 'friction capacity exceeded' : 'within friction capacity'}. Required ${formatNumber(f.demand)} N; capacity ${formatNumber(f.capacity)} N. Individual tire traction, wheel brakes, and yaw resistance are not evaluated.`;
    $('edge-rows').innerHTML = e.edges.map((edge) => `<tr class="${edge.id === selectedEdge ? 'selected-edge' : ''}"><td><button type="button" class="edge-button" data-edge="${edge.id}">${escapeHtml(edge.label)}</button></td><td class="numeric">${formatNumber(edge.distance)}</td><td class="numeric">${formatNumber(edge.reserve)}</td></tr>`).join('');
    renderSelectedEdge();
    renderDerivation();
    renderPlots();
    $('export-csv').disabled = dirty;
    $('export-json').disabled = dirty;
}

function chartTheme() {
    const css = getComputedStyle(document.body);
    const color = (name) => css.getPropertyValue('--' + name).trim();
    return { paper: color('bg-card'), text: color('text-color'), grid: color('border-color'), fill: color('primary-light'), muted: color('text-light'), accent: color('accent-color'), reaction: color('warning-color') };
}

function renderPlots() {
    if (!lastResults || !window.Plotly) return;
    const e = lastResults.equilibrium;
    const c = chartTheme();
    const x = e.polygon.map((p) => p[0]);
    const y = e.polygon.map((p) => p[1]);
    const traces = [
        { x: [...x, x[0]], y: [...y, y[0]], type: 'scatter', mode: 'lines', fill: 'toself', fillcolor: c.fill, line: { color: c.accent, width: 1.5 }, name: 'Support polygon', hoverinfo: 'skip' },
        { x, y, type: 'scatter', mode: 'markers', marker: { size: 8, color: c.accent }, name: 'Ground contacts', hovertemplate: 'x %{x:.3f} m<br>y %{y:.3f} m<extra>Hull contact</extra>' },
        { x: [e.center[0]], y: [e.center[1]], type: 'scatter', mode: 'markers', marker: { size: 13, symbol: 'cross-open', color: c.text, line: { width: 2 } }, name: 'Mass center projection', hovertemplate: 'x %{x:.3f} m<br>y %{y:.3f} m<extra>Mass center</extra>' },
        { x: [e.reaction_point[0]], y: [e.reaction_point[1]], type: 'scatter', mode: 'markers', marker: { size: 12, symbol: 'diamond', color: c.reaction }, name: 'Normal reaction', hovertemplate: 'x %{x:.3f} m<br>y %{y:.3f} m<extra>Normal reaction</extra>' },
    ];
    const edge = e.edges.find((item) => item.id === selectedEdge);
    traces.push({ x: [edge.start[0], edge.end[0]], y: [edge.start[1], edge.end[1]], type: 'scatter', mode: 'lines', line: { color: c.reaction, width: 4 }, showlegend: false, hovertemplate: `${escapeHtml(edge.label)}<extra>Selected edge</extra>` });
    const allX = [...x, e.center[0], e.reaction_point[0]], allY = [...y, e.center[1], e.reaction_point[1]];
    const pad = Math.max(Math.max(...x) - Math.min(...x), Math.max(...y) - Math.min(...y)) * .12;
    const common = { paper_bgcolor: c.paper, plot_bgcolor: c.paper, font: { family: 'Helvetica Neue, sans-serif', color: c.text, size: 11 }, margin: { l: 54, r: 14, t: 24, b: 78 }, legend: { orientation: 'h', y: -.25, x: 0, font: { size: 10 } }, uirevision: 'tipping', hovermode: 'closest' };
    const config = { responsive: true, displayModeBar: false, scrollZoom: false };
    Plotly.react('plan-plot', traces, { ...common,
        xaxis: { title: 'x / forward (m)', type: 'linear', gridcolor: c.grid, zerolinecolor: c.grid, range: [Math.min(...allX) - pad, Math.max(...allX) + pad] },
        yaxis: { title: 'y / left (m)', type: 'linear', gridcolor: c.grid, zerolinecolor: c.grid, scaleanchor: 'x', scaleratio: 1, range: [Math.min(...allY) - pad, Math.max(...allY) + pad] },
        annotations: e.edges.map((item) => ({ x: (item.start[0] + item.end[0]) / 2, y: (item.start[1] + item.end[1]) / 2, text: item.id, showarrow: false, xshift: -item.normal[0] * 14, yshift: -item.normal[1] * 14, font: { color: c.muted, size: 10 } })),
    }, config);
    if (!$('directions').hidden) {
        const data = lastResults.directions;
        const finite = data.tip_angles.filter(Number.isFinite);
        $('direction-note').textContent = finite.length ? 'The smallest radius identifies the weakest downhill direction. This geometry-only envelope is separate from the combined-load threshold on the Results tab.' : 'The level-ground center of mass lies outside the support polygon. A gravity-only sweep from level ground has no stable starting point.';
        Plotly.react('direction-plot', [{ type: 'scatterpolar', mode: 'lines', theta: data.degrees, r: data.tip_angles, name: 'Gravity-only tipping slope', line: { color: c.accent, width: 2 }, hovertemplate: 'Downhill %{theta:.0f}°<br>Critical slope %{r:.2f}°<extra></extra>', connectgaps: false }], {
            ...common, margin: { l: 60, r: 60, t: 50, b: 55 }, legend: { orientation: 'h', y: -.16, x: .05 },
            polar: { bgcolor: c.paper, radialaxis: { type: 'linear', range: [0, finite.length ? Math.min(90, Math.ceil(Math.max(...finite) / 10) * 10 + 5) : 90], gridcolor: c.grid, linecolor: c.grid, ticksuffix: '°', angle: 45 }, angularaxis: { direction: 'counterclockwise', rotation: 0, gridcolor: c.grid, linecolor: c.grid, tickmode: 'array', tickvals: [0, 90, 180, 270], ticktext: ['Forward<br>0°', 'Left<br>90°', 'Rear<br>180°', 'Right<br>270°'] } },
        }, config);
    }
}

function renderSelectedEdge() {
    if (!lastResults) return;
    const e = lastResults.equilibrium;
    const edge = e.edges.find((item) => item.id === selectedEdge);
    $('contribution-heading').textContent = edge.label + ': load contributions';
    $('contribution-rows').innerHTML = edge.contributions.map((row) => `<tr><td>${escapeHtml(row.name)}</td><td class="numeric">${formatNumber(row.reserve)}</td></tr>`).join('');
    $('section-heading').textContent = 'Section normal to ' + edge.label;
    // Projection is for drawing only; all equilibrium quantities come from Python.
    const inward = (point) => (point[0] - edge.start[0]) * edge.normal[0] + (point[1] - edge.start[1]) * edge.normal[1];
    const center = [inward(e.center), e.center[2]];
    const reaction = inward(e.reaction_point);
    const points = [[0, 0], center, [reaction, 0], ...e.loads.map((load) => [inward(load.point), load.point[2]])];
    const minX = Math.min(0, ...points.map((p) => p[0]));
    const maxX = Math.max(...points.map((p) => p[0]), .01);
    const maxZ = Math.max(...points.map((p) => p[1]), .01);
    const width = Math.max(280, $('section-svg').clientWidth || 560);
    $('section-svg').setAttribute('viewBox', `0 0 ${width} 280`);
    const scale = Math.min((width - 140) / Math.max(maxX - minX, .001), 145 / maxZ);
    const origin = (width - (maxX - minX) * scale) / 2 - minX * scale;
    const sx = (value) => origin + value * scale;
    const sz = (value) => 202 - value * scale;
    const heightLabelOnLeft = sx(center[0]) > width - 135;
    const maxForce = Math.max(...e.loads.map((load) => Math.hypot(...load.vector)), 1);
    const arrows = e.loads.filter((load) => Math.hypot(...load.vector) > 1e-12).map((load) => {
        const x = sx(inward(load.point)), y = sz(load.point[2]);
        const dx = (load.vector[0] * edge.normal[0] + load.vector[1] * edge.normal[1]) * 60 / maxForce;
        const dz = -load.vector[2] * 60 / maxForce;
        if (Math.hypot(dx, dz) < .25) return '';
        return `<g><title>${escapeHtml(load.name)}: (${load.vector.map((v) => formatNumber(v)).join(', ')}) N</title><line x1="${x}" y1="${y}" x2="${x + dx}" y2="${y + dz}" stroke="var(--secondary-color)" stroke-width="1.8" marker-end="url(#load-arrow)"/></g>`;
    }).join('');
    $('section-svg').innerHTML = `<defs><marker id="load-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="var(--secondary-color)"/></marker></defs>
        <line x1="20" y1="202" x2="${width - 20}" y2="202" stroke="var(--border-color)"/><line x1="${sx(0)}" y1="202" x2="${sx(maxX) + 25}" y2="202" stroke="var(--text-color)" stroke-width="3"/>
        <line x1="${sx(center[0])}" y1="${sz(center[1])}" x2="${sx(center[0])}" y2="202" stroke="var(--border-color)" stroke-dasharray="4 4"/>
        <line x1="${sx(0)}" y1="35" x2="${sx(0)}" y2="202" stroke="var(--border-color)" stroke-dasharray="4 4"/>
        <text x="${sx(0)}" y="27" text-anchor="middle">Tipping edge · x = 0 m</text>
        ${arrows}
        <circle cx="${sx(center[0])}" cy="${sz(center[1])}" r="6" fill="var(--bg-card)" stroke="var(--text-color)" stroke-width="1.5"/><path d="M${sx(center[0]) - 4},${sz(center[1])} h8 M${sx(center[0])},${sz(center[1]) - 4} v8" stroke="var(--text-color)"/>
        <text x="${sx(center[0]) + (heightLabelOnLeft ? -12 : 12)}" y="${sz(center[1]) - 12}" text-anchor="${heightLabelOnLeft ? 'end' : 'start'}">z = ${formatNumber(center[1])} m</text>
        <path d="M${sx(reaction)},195 l6,7 l-6,7 l-6,-7 z" fill="var(--warning-color)"/>
        <text x="${Math.max(85, Math.min(width - 85, sx(reaction)))}" y="225" text-anchor="middle">Reaction: ${formatNumber(reaction)} m</text>
        <text x="${width / 2}" y="258" text-anchor="middle">x: distance inward from edge (m) →</text>`;
}

function openTab(name, focus = false) {
    for (const button of document.querySelectorAll('[data-tab]')) {
        const active = button.dataset.tab === name;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', String(active));
        button.tabIndex = active ? 0 : -1;
        $(button.dataset.tab).hidden = !active;
        $(button.dataset.tab).classList.toggle('active', active);
        if (active && focus) button.focus();
    }
    if (name === 'background') typesetMath([$('background')]);
    if (lastResults) { renderPlots(); requestAnimationFrame(() => { if (name === 'results') Plotly.Plots.resize('plan-plot'); if (name === 'directions') Plotly.Plots.resize('direction-plot'); }); }
}

function download(name, contents, type) {
    const link = document.createElement('a');
    const url = URL.createObjectURL(new Blob([contents], { type }));
    link.href = url; link.download = name;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportCsv() {
    if (!lastResults || dirty) return;
    const e = lastResults.equilibrium, t = lastResults.threshold;
    const rows = [['Tipping and Stability', 'SI units'], ['Model', 'Rigid assembly; planar compression-only contacts; prescribed translational acceleration; restrained rolling; no suspension or rotational inertia'], [], ['Input', 'Value (SI; angles in degrees)']];
    Object.entries(lastInputs).forEach(([key, value]) => rows.push([key, typeof value === 'object' ? JSON.stringify(value) : value]));
    rows.push([], ['Result', 'Value', 'Unit'], ['Tipping status', e.status, ''], [t.title, t.value ?? t.state, t.unit], ['Current demand', t.demand, t.unit], ['Remaining to threshold', t.remaining ?? '', t.unit], ['Sweep definition', t.held, ''], ['Limiting edge for sweep', t.edge ?? '', ''], ['Minimum edge margin', e.margin, 'm'], ['Moment reserve', e.moment_reserve, 'N*m'], ['Total mass', e.mass, 'kg'], ['Center of mass', JSON.stringify(e.center), 'm'], ['Normal reaction', e.normal_reaction, 'N'], ['Reaction location', JSON.stringify(e.reaction_point), 'm'], ['Friction status', e.friction.status, ''], ['Friction demand', e.friction.demand, 'N'], ['Friction capacity', e.friction.capacity ?? '', 'N'], [], ['Edge', 'Margin (m)', 'Restoring reserve (N*m)']);
    e.edges.forEach((edge) => rows.push([edge.label, edge.distance, edge.reserve]));
    rows.push([], ['Edge', 'Load', 'Restoring moment (N*m)']);
    e.edges.forEach((edge) => edge.contributions.forEach((load) => rows.push([edge.label, load.name, load.reserve])));
    const cell = (value) => {
        let text = String(value);
        if (typeof value === 'string' && /^[=+\-@\t\r]/.test(text)) text = "'" + text;
        return '"' + text.replaceAll('"', '""') + '"';
    };
    download('tipping-stability.csv', rows.map((row) => row.map(cell).join(',')).join('\r\n'), 'text/csv;charset=utf-8');
}

function bindControls() {
    $('calc-form').addEventListener('submit', calculate);
    $('calc-form').addEventListener('input', markDirty);
    $('calc-form').addEventListener('change', () => { syncVisibility(); markDirty(); });
    // Native constraint validation happens before submit; clear previous results here too.
    $('calc-form').addEventListener('invalid', (event) => {
        const details = event.target.closest('details');
        if (details) details.open = true;
        clearResults('Check the highlighted input. Results are cleared until the case is valid.');
    }, true);
    $('reset-case').addEventListener('click', () => {
        $('calc-form').reset();
        for (const [key, schema] of Object.entries(editors)) {
            $(key).value = JSON.stringify(schema.defaults); renderEditor(key, schema.defaults);
        }
        syncVisibility(); markDirty();
        $('load_case').dispatchEvent(new Event('change', { bubbles: true }));
    });
    document.querySelectorAll('[data-tab]').forEach((button) => button.addEventListener('click', () => openTab(button.dataset.tab)));
    document.querySelector('.tabs').addEventListener('keydown', (event) => {
        const tabs = [...document.querySelectorAll('[data-tab]')];
        const index = tabs.indexOf(document.activeElement);
        if (index < 0 || !['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
        openTab(tabs[next].dataset.tab, true);
    });
    document.querySelectorAll('[data-derivation]').forEach((button) => button.addEventListener('click', () => showDerivation(button.dataset.derivation)));
    $('close-derivation').addEventListener('click', () => {
        const key = openDerivation; openDerivation = null; renderDerivation();
        document.querySelector(`[data-derivation="${key}"]`)?.focus();
    });
    $('edge-rows').addEventListener('click', (event) => {
        const button = event.target.closest('[data-edge]');
        if (!button) return;
        selectedEdge = button.dataset.edge;
        $('edge-rows').querySelectorAll('tr').forEach((tr) => tr.classList.toggle('selected-edge', tr.contains(button)));
        renderSelectedEdge(); renderPlots();
    });
    $('export-csv').addEventListener('click', exportCsv);
    $('export-json').addEventListener('click', () => {
        if (!lastResults || dirty) return;
        download('tipping-stability.json', JSON.stringify({ format: 'transparent-tools/tipping-stability/v1', inputs: lastInputs, form: lastForm, results: lastResults }, null, 2), 'application/json');
    });
}

async function loadEngine() {
    $('retry-load').hidden = true;
    $('loading-spinner').hidden = false;
    $('loading-text').textContent = 'Loading the calculation engine…';
    try {
        const responses = await Promise.all(['utils', TOOL_MODULE_NAME].map(async (name) => {
            const response = await fetch(`../../pycalcs/${name}.py`);
            if (!response.ok) throw new Error(`Could not load ${name} (${response.status}).`);
            return [name, await response.text()];
        }));
        pyodide = await loadPyodide();
        for (const [name, source] of responses) pyodide.FS.writeFile(name + '.py', source);
        pyodide.runPython('import json, utils, stability');
        const documentation = JSON.parse(pyodide.runPython("json.dumps(utils.get_documentation('stability', 'analyze_tipping'))"));
        for (const key of PARAM_ORDER) if ($('help-' + key) && documentation.parameters?.[key]) $('help-' + key).textContent = documentation.parameters[key];
        const example = callPython({});
        $('theory-equations').innerHTML = equationCards(null, example.theory);
        $('worked-example').innerHTML = `<p>A centered cart with a 1.2 m wheelbase, 0.8 m track, and a center of mass 0.6 m above the surface has a gravity-only lateral tipping angle of ${formatNumber(example.threshold.value)}°. Its distance to a side edge is 0.4 m.</p>` + equationCards(['slope', 'acceleration', 'push'], example.theory) + `<p>The lateral acceleration threshold is ${formatNumber(callPython({ load_case: 'acceleration', accel_direction: 90 }).threshold.value)} m/s². For a 100 kg cart, a horizontal push at a height of 1 m reaches the ideal threshold at ${formatNumber(callPython({ load_case: 'push' }).threshold.value)} N.</p><p>Moving mass lower increases the angle and acceleration thresholds. Mass alone cancels from those two ideal limits, but changes the force required to tip the cart.</p>`;
        $('calculate-btn').disabled = false;
        await calculate();
        $('loading-overlay').classList.add('hidden');
        $('tool-main').dataset.bootState = 'ready';
        document.querySelector('.url-state-share-btn')?.setAttribute('data-track', 'export');
    } catch (error) {
        pyodide = null;
        $('loading-text').textContent = `The calculation engine could not load. ${error.message}`;
        $('loading-spinner').hidden = true;
        $('retry-load').hidden = false;
        $('tool-main').dataset.bootState = 'error';
    }
}

async function main() {
    // Let the shared URL-state module restore scalar and serialized table inputs.
    await new Promise((resolve) => setTimeout(resolve, 0));
    bindSettings(); bindHelp(); initEditors(); bindControls(); syncVisibility();
    let sectionWidth = 0;
    new ResizeObserver(([entry]) => {
        if (Math.abs(entry.contentRect.width - sectionWidth) < 1) return;
        sectionWidth = entry.contentRect.width;
        if (lastResults) renderSelectedEdge();
    }).observe($('section-svg').parentElement);
    if ($('geometry_mode').value === 'custom' || $('mass_mode').value === 'components') $('advanced-inputs').open = true;
    $('retry-load').addEventListener('click', loadEngine);
    await loadEngine();
}

window.TippingTool = { getResults: () => lastResults, getInputs: () => lastInputs, calculate };
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main, { once: true });
else main();
