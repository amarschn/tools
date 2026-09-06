/* Shared task workspace. Geometry, selection and specification rules live in Python. */
(() => {
    'use strict';

    const byId = (id) => document.getElementById(id);
    const form = byId('spec-form');
    const output = byId('spec-output');
    const tabs = [...document.querySelectorAll('.primary-tab')];
    const copyButtons = [byId('copy-drawing-callout'), byId('copy-detailed-note')];
    const copyFeedbackTimers = new Map();
    const defaults = {
        family: 'metric', size: 'M10x1.5', feature: 'through', depth: '', fit: '', hand: 'RH',
        process: 'unspecified', material_family: 'unspecified', material: '', finish: '', inspection: '',
        seal: '', product: '', screw_diameter: '', screw_length: '', product_unit: 'mm', head: '', substrate: '',
        axial_load: '20', proof_strength: '580', design_factor: '1.5', series: 'coarse',
        identify: false, measured_diameter: '9.96', measured_pitch: '1.5', view: 'internal', open: []
    };
    const states = {
        specify: { ...defaults },
        load: { ...defaults, feature: 'nominal', view: 'external' },
        explore: { ...defaults, feature: 'nominal', view: 'external' }
    };
    const featureHome = document.createComment('Essential feature control');
    byId('spec-feature-group').before(featureHome);
    let catalog = {};
    let expert = {};
    let python = null;
    let isAutoUpdate = () => true;
    let drawGeometry = () => {};
    let result = null;
    let timer = null;
    let section = 'specify';
    let currentView = 'internal';
    let specifyEdited = false;
    let transferred = false;

    function plain(proxy) {
        try { return proxy.toJs({ dict_converter: Object.fromEntries }); }
        finally { proxy.destroy(); }
    }

    function options(select, entries, preferred) {
        select.replaceChildren(...entries.map(([value, label]) => new Option(label, value)));
        if (entries.some(([value]) => value === preferred)) select.value = preferred;
    }

    function familyOptions(preferred) {
        const groups = new Map();
        Object.entries(catalog).forEach(([key, family]) => {
            if (section === 'load' && !['metric', 'unc', 'unf'].includes(key)) return;
            if (!groups.has(family.group)) {
                const group = document.createElement('optgroup');
                group.label = family.group;
                groups.set(family.group, group);
            }
            groups.get(family.group).append(new Option(family.label, key));
        });
        byId('spec-family').replaceChildren(...groups.values());
        if ([...byId('spec-family').options].some((option) => option.value === preferred)) byId('spec-family').value = preferred;
    }

    function side() {
        if (catalog[byId('spec-family').value].kind === 'product') return 'product';
        return ['external', 'nominal', 'pipe_external'].includes(byId('spec-feature').value) ? 'external' : 'internal';
    }

    function updateSummaries() {
        byId('thread-details-summary').textContent = [byId('spec-fit').value, byId('spec-hand-group').hidden ? '' : byId('spec-hand').value].filter(Boolean).join(' · ') || 'connection details';
        const process = byId('spec-process').value;
        const material = byId('spec-material-family').value;
        byId('expert-summary').textContent = [
            process !== 'unspecified' ? expert.processes[process]?.label : '',
            material !== 'unspecified' ? expert.materials[material] : ''
        ].filter(Boolean).join(' · ') || 'manufacturing & material';
        byId('identify-summary').textContent = byId('identify-enabled').checked ? 'using measurements' : 'optional';
        window.threadFieldHelp.refresh();
    }

    function updateFeature(preferredFit, preferredProcess) {
        const family = catalog[byId('spec-family').value];
        const classes = family.classes?.[side()] || [];
        const labels = { Rc: 'Rc · tapered internal', Rp: 'Rp · parallel internal', R: 'R · tapered external' };
        options(byId('spec-fit'), classes.map((value) => [value, labels[value] || value]), preferredFit);
        byId('spec-fit-group').hidden = classes.length === 0;
        options(byId('spec-process'), Object.entries(expert.processes)
            .filter(([, method]) => method.sides.includes(side()))
            .map(([key, method]) => [key, method.label]), preferredProcess);
        byId('spec-process-help').textContent = expert.processes[byId('spec-process').value].help;
        const length = byId('spec-feature').value === 'external';
        const needsDepth = family.kind === 'machine' && (length || byId('spec-feature').value === 'blind');
        byId('spec-depth-group').hidden = !needsDepth;
        byId('spec-depth').required = needsDepth;
        byId('spec-depth-label').textContent = 'Minimum full-thread ' + (length ? 'length' : 'depth') + ' (' + family.unit + ')';
        byId('spec-depth').placeholder = 'Required in ' + family.unit;
        updateSummaries();
    }

    function restoreForm(values) {
        familyOptions(values.family);
        const family = catalog[byId('spec-family').value];
        const product = family.kind === 'product';
        const pipe = family.kind === 'pipe';
        options(byId('spec-size'), family.sizes.map((size) => [size, size.replace('x', ' × ')]), values.size || family.default_size);
        options(byId('spec-feature'), pipe
            ? [['pipe_internal', 'Internal pipe thread'], ['pipe_external', 'External pipe thread']]
            : [['through', 'Tapped hole, through'], ['blind', 'Tapped hole, blind'], ['external', 'External thread, with length'], ['nominal', 'External thread, extent undecided']], values.feature);
        options(byId('spec-material-family'), Object.entries(expert.materials), values.material_family);
        [...form.elements].forEach((element) => {
            if (!element.name || ['family', 'size', 'feature', 'fit', 'process', 'material_family'].includes(element.name)) return;
            if (element.type === 'checkbox') element.checked = values[element.name] === true;
            else if (values[element.name] !== undefined && (element.tagName !== 'SELECT' || [...element.options].some((option) => option.value === values[element.name]))) element.value = values[element.name];
        });
        const canIdentify = section === 'explore' && ['metric', 'unc', 'unf'].includes(byId('spec-family').value);
        if (!canIdentify) byId('identify-enabled').checked = false;
        byId('identify-options').hidden = !canIdentify;
        byId('spec-size-group').hidden = product || section === 'load' || byId('identify-enabled').checked;
        byId('spec-feature-group').hidden = product;
        byId('spec-product-fields').hidden = !product;
        byId('thread-details').hidden = product;
        byId('spec-hand-group').hidden = family.kind !== 'machine';
        byId('spec-pipe-fields').hidden = !pipe;
        byId('load-fields').hidden = section !== 'load';
        byId('load-detail-fields').hidden = section !== 'load';
        byId('series-group').hidden = byId('spec-family').value !== 'metric';
        if (section === 'specify') featureHome.after(byId('spec-feature-group'));
        else byId('detail-feature-slot').append(byId('spec-feature-group'));
        byId('spec-family-help').textContent = family.help;
        byId('spec-fit-help').textContent = family.fit_help || '';
        byId('measured-diameter-label').textContent = 'Outside diameter (' + (family.unit === 'mm' ? 'mm' : 'in') + ')';
        byId('measured-pitch-label').textContent = family.unit === 'mm' ? 'Pitch (mm)' : 'Threads per inch (TPI)';
        currentView = values.view || 'external';
        updateFeature(values.fit, values.process);
        form.querySelectorAll('details[id]').forEach((details) => { details.open = (values.open || []).includes(details.id); });
        if (byId('identify-enabled').checked) byId('identify-options').open = true;
        if (values.fit && values.fit !== (family.classes?.[side()] || [])[0]) byId('thread-details').open = true;
        if (values.process !== 'unspecified' || values.material_family !== 'unspecified' || values.material || values.finish || values.inspection) byId('expert-options').open = true;
        byId('spec-input-heading').textContent = { specify: 'Specify a thread', load: 'Design thread for load', explore: 'Explore thread' }[section];
        byId('task-intro').textContent = {
            specify: 'Choose the mating thread and the feature on your part.',
            load: 'Find a candidate size for direct axial tension. Joint and engagement checks remain.',
            explore: 'Choose a nominal thread to inspect its profile, dimensions and drawing designation.'
        }[section];
        byId('spec-update').textContent = section === 'load' ? 'Find candidate thread' : 'Update specification';
    }

    function capture() {
        return { ...Object.fromEntries(new FormData(form)), identify: byId('identify-enabled').checked, view: currentView,
            open: [...form.querySelectorAll('details[id][open]')].map((details) => details.id) };
    }

    function calculationState() {
        const values = { ...capture(), task: section, side: side() };
        const kind = catalog[values.family].kind;
        values.extent = { through: 'thru', blind: 'blind', external: 'length', nominal: 'unspecified' }[values.feature];
        if (kind === 'product') {
            ['fit', 'extent', 'depth', 'hand', 'size', 'seal'].forEach((key) => delete values[key]);
        } else {
            ['product', 'screw_diameter', 'screw_length', 'product_unit', 'head', 'substrate'].forEach((key) => delete values[key]);
            if (kind === 'pipe') {
                values.hand = 'RH';
                delete values.extent;
                delete values.depth;
            } else delete values.seal;
        }
        if (section !== 'load') ['axial_load', 'proof_strength', 'design_factor', 'series'].forEach((key) => delete values[key]);
        if (!values.identify) ['measured_diameter', 'measured_pitch'].forEach((key) => delete values[key]);
        return values;
    }

    function stale() {
        window.clearTimeout(timer);
        result = null;
        window.threadExports.invalidate();
        resetCopyFeedback();
        output.dataset.stale = 'true';
        byId('spec-status').textContent = 'Update required';
        byId('spec-copy-status').textContent = 'Inputs changed. Update the specification before copying.';
        [...copyButtons, byId('export-results')].forEach((button) => { button.disabled = true; });
    }

    function renderSymbol(spec) {
        const product = spec.kind === 'product';
        byId('callout-symbol').toggleAttribute('hidden', product);
        byId('callout-sheet').classList.toggle('product-note', product);
        byId('callout-symbol').setAttribute('aria-description', product
            ? 'Product-specific profile. Use the supplier drawing for thread geometry and pilot-hole details.'
            : spec.kind === 'pipe'
                ? 'Symbolic end view only. Taper, sealing features, and port dimensions are not shown.'
                : 'Conventional end view, not to scale. Dimensional tolerances are not shown.');
        const external = spec.side === 'external';
        byId('callout-major-circle').toggleAttribute('hidden', !external);
        byId('callout-major-circle').setAttribute('class', 'outline');
        byId('callout-minor-circle').toggleAttribute('hidden', external);
        const radius = external ? 28 : 36;
        byId('callout-partial-circle').setAttribute('d', `M64,${78 - radius} A${radius},${radius} 0 1 0 ${64 + radius},78`);
        // Leader and arrow share a single point on the thick outline.
        const contactRadius = external ? 36 : 28;
        const offset = contactRadius / Math.sqrt(2);
        const x = 64 + offset;
        const y = 78 - offset;
        byId('callout-leader').setAttribute('d', `M${x},${y} L122,20 H156`);
        byId('callout-leader-tip').setAttribute('d', `M${x},${y} L${x + 4},${y - 10} L${x + 10},${y - 4} Z`);
        byId('callout-symbol-title').textContent = `${spec.side} thread, conventional end view, symbolic, not to scale`;
    }


    function renderSchematic(spec) {
        window.threadFamilyDiagram.render(spec);
    }

    function render(payload) {
        window.threadFieldHelp.refresh();
        const { specification: spec, geometry, analysis } = payload;
        byId('spec-note-heading').textContent = section === 'find' ? 'Identification note' : 'Detailed specification note';
        window.threadExports.setSpecification(section === 'find' ? null : payload, calculationState());
        byId('machine-profile').hidden = !geometry;
        byId('schematic-profile').hidden = !!geometry || !spec;
        byId('profile-unavailable').hidden = !!spec;
        byId('basic-dimensions').hidden = !geometry;
        byId('calculation-details').hidden = !geometry && !analysis;
        byId('calculation-details').querySelector('.ledger-content').hidden = !geometry;
        ['dimension-details', 'note-details'].forEach((id) => { byId(id).hidden = !spec; });
        byId('result-evidence').hidden = !analysis;
        byId('result-evidence').textContent = !analysis ? '' : section === 'load'
            ? (spec ? 'Proof margin ' + analysis.proof_margin.toFixed(2) + '× · required ' + byId('design_factor').value + '×. Axial tension only.' : 'No included size meets the factored axial demand.')
            : 'Nearest nominal match only. Fit, hand and extent are drawing assumptions, not measured results.';
        byId('spec-result-heading').textContent = spec?.kind === 'product' ? 'Screw specification' : 'Thread specification';
        byId('spec-result-caption').textContent = spec?.status || 'Increase the supported size range or revisit verified design inputs.';
        byId('spec-status').textContent = !spec ? 'No passing size' : section === 'load' ? 'Preliminary' : spec.kind === 'product' ? 'Draft' : 'Review required';
        byId('spec-copy-status').textContent = '';
        if (!spec) {
            byId('drawing-callout').textContent = 'No passing thread in this catalog';
            byId('callout-sheet').classList.add('product-note');
            byId('callout-symbol').toggleAttribute('hidden', true);
            copyButtons.forEach((button) => { button.disabled = true; });
            drawGeometry(null, currentView, analysis);
            output.dataset.stale = 'false';
            return;
        }
        byId('drawing-callout').textContent = spec.callout;
        byId('spec-note').textContent = spec.note;
        byId('spec-breakdown').replaceChildren(...spec.breakdown.map(([label, value]) => {
            const row = document.createElement('div');
            const term = document.createElement('dt');
            const definition = document.createElement('dd');
            term.textContent = label;
            definition.textContent = value;
            row.append(term, definition);
            return row;
        }));
        byId('task-assumptions').textContent = section === 'load'
            ? 'Using ' + byId('design_factor').value + '× proof margin, ' + (byId('spec-family').value === 'metric' ? byId('thread_series').selectedOptions[0].textContent.toLowerCase() : byId('spec-family').value.toUpperCase()) + '. Change assumptions in Thread details. No stripping, fatigue or preload check.'
            : spec.kind === 'machine' ? 'Fit and hand are shown in the callout. Open Thread details to change them.' : 'Confirm the mating connection and supplier requirements before release.';
        renderSymbol(spec);
        document.querySelectorAll('[data-view]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === currentView)));
        if (geometry) drawGeometry(geometry, currentView, analysis);
        else renderSchematic(spec);
        output.dataset.stale = 'false';
        copyButtons.forEach((button) => { button.disabled = false; });
        byId('export-results').disabled = !geometry;
    }

    function update() {
        if (!python) return;
        if (section === 'find') { window.threadFinder.update(); return; }
        window.clearTimeout(timer);
        try {
            const next = plain(python.analyze_thread_workflow(JSON.stringify(calculationState())));
            result = next;
            byId('spec-error').hidden = true;
            byId('spec-depth').removeAttribute('aria-invalid');
            if (next.resolved_size) {
                byId('spec-family').value = next.resolved_family;
                const family = catalog[next.resolved_family];
                options(byId('spec-size'), family.sizes.map((size) => [size, size.replace('x', ' × ')]), next.resolved_size);
            }
            render(next);
            if (transferred && section === 'specify') byId('task-assumptions').textContent = 'Candidate transferred from Find. Fit, hand and extent here are design choices, not conclusions from the measurements. Review Thread details.';
        } catch (error) {
            stale();
            const validationErrors = [...String(error.message || error).matchAll(/^ValueError: (.+)$/gm)];
            if (!validationErrors.length) console.error(error);
            byId('spec-error').textContent = validationErrors.at(-1)?.[1] || 'Could not build the specification. Check the inputs.';
            byId('spec-error').hidden = false;
            byId('spec-status').textContent = 'Input needed';
            byId('spec-copy-status').textContent = 'The previous result is out of date. Resolve the input error before copying.';
            if (byId('spec-depth').required && !(Number(byId('spec-depth').value) > 0)) byId('spec-depth').setAttribute('aria-invalid', 'true');
        }
    }

    function activateTab(focus = false) {
        tabs.forEach((tab) => {
            const active = tab.dataset.section === section;
            tab.setAttribute('aria-selected', String(active));
            tab.tabIndex = active ? 0 : -1;
            if (active && focus) tab.focus();
        });
        byId('thread-task-panel').setAttribute('aria-labelledby', 'tab-' + section);
        byId('thread-task-panel').dataset.task = section;
        form.hidden = section === 'find';
        byId('find-form').hidden = section !== 'find';
        byId('find-results').hidden = section !== 'find';
        if (section === 'find') {
            byId('spec-input-heading').textContent = 'Find a thread';
            byId('task-intro').textContent = 'Identify a thread from measurements. Leave anything you cannot measure blank.';
        }
    }

    function showSection(next, focus = false) {
        window.threadFieldHelp.close();
        if (section !== 'find') states[section] = capture();
        section = ['specify', 'load', 'find'].includes(next) ? next : 'specify';
        if (section !== 'find') restoreForm(states[section]);
        activateTab(focus);
        stale();
        update();
    }

    function openReference(hash) {
        const target = byId(hash.replace(/^#/, ''));
        if (!target?.closest('.thread-reference-area')) return;
        let parent = target;
        while (parent) {
            if (parent.tagName === 'DETAILS') parent.open = true;
            parent = parent.parentElement;
        }
        target.scrollIntoView({ block: 'start' });
    }

    function resetCopyFeedback() {
        copyButtons.forEach((button) => {
            window.clearTimeout(copyFeedbackTimers.get(button));
            button.removeAttribute('data-copied');
            button.setAttribute('aria-label', button.title);
        });
    }

    async function copyText(value, label, button = null) {
        try {
            await navigator.clipboard.writeText(value);
            if (button && button.disabled) return;
            byId('spec-copy-status').textContent = label + ' copied.';
            if (button) {
                window.clearTimeout(copyFeedbackTimers.get(button));
                button.dataset.copied = 'true';
                button.setAttribute('aria-label', label + ' copied');
                copyFeedbackTimers.set(button, window.setTimeout(() => {
                    button.removeAttribute('data-copied');
                    button.setAttribute('aria-label', button.title);
                }, 1600));
            }
        } catch {
            byId('spec-copy-status').textContent = 'Clipboard unavailable. Select and copy the displayed text.';
        }
    }

    function shareUrl() {
        const url = new URL(window.location.href);
        url.search = '';
        url.hash = '';
        url.searchParams.set('task', section);
        if (section === 'find') { window.threadFinder.appendUrl(url); return url.toString(); }
        Object.entries(capture()).forEach(([key, value]) => {
            // Preserve deliberately blank required inputs; a shared invalid load
            // must not silently regain the default proof strength on restore.
            if (key !== 'open') url.searchParams.set('spec_' + key, String(value));
        });
        return url.toString();
    }

    function restoreUrl() {
        const params = new URLSearchParams(window.location.search);
        const requested = params.get('task') || (params.has('mode') ? params.get('mode') === 'size' ? 'load' : 'explore' : params.get('section'));
        const legacyFind = requested === 'explore' && (params.get('spec_identify') === 'true' || params.get('mode') === 'identify');
        section = legacyFind || requested === 'find' ? 'find' : requested === 'load' ? 'load' : 'specify';
        const values = { ...states[section === 'find' ? 'specify' : section] };
        if (requested === 'explore' && !legacyFind) { values.feature = 'nominal'; values.view = 'external'; }
        Object.keys(defaults).forEach((key) => {
            if (params.has('spec_' + key) && key !== 'open') values[key] = key === 'identify' ? params.get('spec_identify') === 'true' : params.get('spec_' + key);
        });
        if (params.has('mode')) {
            values.identify = params.get('mode') === 'identify';
            values.family = params.get('system') === 'unified' ? (params.get('designation')?.endsWith('UNF') ? 'unf' : 'unc') : 'metric';
            const legacy = { designation: 'size', load: 'axial_load', proof: 'proof_strength', factor: 'design_factor', series: 'series', diameter: 'measured_diameter', pitch: 'measured_pitch', view: 'view' };
            Object.entries(legacy).forEach(([oldKey, key]) => { if (params.has(oldKey)) values[key] = params.get(oldKey); });
        }
        if (params.has('spec_side')) values.feature = params.get('spec_side') === 'external' ? 'external' : params.get('spec_extent') === 'blind' ? 'blind' : 'through';
        if (catalog[values.family]?.kind === 'pipe') values.feature = ['external', 'nominal', 'pipe_external'].includes(values.feature) ? 'pipe_external' : 'pipe_internal';
        if (!['external', 'internal', 'engaged'].includes(values.view)) values.view = 'external';
        values.identify = false;
        restoreForm(values);
        if (section === 'find') window.threadFinder.restore(params, legacyFind);
        specifyEdited = section === 'specify' && [...params.keys()].some((key) => key.startsWith('spec_'));
        activateTab();
        if (window.location.hash) requestAnimationFrame(() => openReference(window.location.hash));
        else if (params.get('section') === 'background') requestAnimationFrame(() => openReference('#thread-guide'));
    }

    tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => showSection(tab.dataset.section));
        tab.addEventListener('keydown', (event) => {
            const next = { ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index + tabs.length - 1) % tabs.length, Home: 0, End: tabs.length - 1 }[event.key];
            if (next !== undefined) { event.preventDefault(); showSection(tabs[next].dataset.section, true); }
        });
    });
    document.querySelectorAll('.handbook-toc a').forEach((link) => link.addEventListener('click', () => openReference(link.hash)));
    window.addEventListener('hashchange', () => openReference(window.location.hash));
    document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => {
        currentView = button.dataset.view;
        if (section === 'find') window.threadFinder.present();
        else if (result) render(result);
    }));
    form.addEventListener('submit', (event) => { event.preventDefault(); update(); });
    form.addEventListener('input', (event) => {
        if (section === 'specify') specifyEdited = true;
        if (event.target.tagName === 'SELECT' || event.target.type === 'checkbox') return;
        if (section === 'load' && event.target.id === 'spec-material') byId('proof_strength').value = '';
        stale();
        if (isAutoUpdate()) timer = window.setTimeout(update, 240);
    });
    form.addEventListener('change', (event) => {
        if (section === 'specify') specifyEdited = true;
        if (event.target.id === 'spec-family') {
            const values = { ...capture(), size: '', fit: '', depth: '', hand: 'RH', identify: false };
            values.feature = section === 'specify' ? 'through' : 'nominal';
            values.measured_diameter = values.family === 'metric' ? '9.96' : '.25';
            values.measured_pitch = values.family === 'metric' ? '1.5' : values.family === 'unf' ? '28' : '20';
            ['product', 'screw_diameter', 'screw_length', 'head', 'substrate', 'seal'].forEach((key) => { values[key] = ''; });
            restoreForm(values);
        }
        if (event.target.id === 'spec-feature') {
            updateFeature(undefined, byId('spec-process').value);
            currentView = side() === 'external' ? 'external' : 'internal';
        }
        if (event.target.id === 'spec-process') byId('spec-process-help').textContent = expert.processes[event.target.value].help;
        if (section === 'load' && event.target.id === 'spec-material-family') byId('proof_strength').value = '';
        if (event.target.id === 'identify-enabled') byId('spec-size-group').hidden = event.target.checked;
        updateSummaries();
        stale();
        if (isAutoUpdate()) update();
    });
    byId('copy-drawing-callout').addEventListener('click', () => {
        if (result?.specification) copyText(result.specification.callout, 'Callout', byId('copy-drawing-callout'));
    });
    byId('copy-detailed-note').addEventListener('click', () => {
        if (result?.specification) copyText(result.specification.note, 'Detailed note', byId('copy-detailed-note'));
    });
    byId('export-results').addEventListener('click', () => {
        if (!result?.geometry) return;
        const { geometry, specification, analysis } = result;
        const rows = [['Field', 'Value', 'Unit'], ['Task', section, ''],
            ['Thread family', catalog[result.resolved_family].label, ''],
            ['Designation', result.resolved_size, ''], ['Series', geometry.series, ''],
            ['Callout', specification.callout, ''], ['Detailed note', specification.note, ''],
            ['Major diameter', geometry.nominal_diameter * 1000, 'mm'],
            ['Pitch', geometry.pitch * 1000, 'mm'], ['Threads per inch', geometry.threads_per_inch, 'TPI'],
            ['Basic pitch diameter', geometry.pitch_diameter_basic * 1000, 'mm'],
            ['Basic internal minor diameter', geometry.internal_minor_diameter_basic * 1000, 'mm'],
            ['Profile minor reference', geometry.profile_minor_diameter * 1000, 'mm'],
            ['Tensile stress area', geometry.tensile_stress_area * 1e6, 'mm^2'],
            ['Lead angle', geometry.lead_angle_deg, 'deg']];
        if (analysis?.mode === 'identify') rows.push(
            ['Measured outside diameter', byId('measured_major_diameter').value, geometry.thread_system === 'unified' ? 'in' : 'mm'],
            ['Measured pitch / TPI', byId('measured_pitch').value, geometry.thread_system === 'unified' ? 'TPI' : 'mm'],
            ['Diameter residual', analysis.diameter_difference * 1000, 'mm'],
            ['Pitch residual', analysis.pitch_difference * 1000, 'mm'],
            ['Relative ranking distance', analysis.relative_distance, '']);
        if (analysis?.mode === 'size') rows.push(
            ['Sizing status', analysis.sizing_status, ''],
            ['Service load', byId('axial_load').value, 'kN'],
            ['Entered minimum proof strength', byId('proof_strength').value, 'MPa'],
            ['Required proof margin', byId('design_factor').value, ''],
            ['Factored design load', analysis.design_load / 1000, 'kN'],
            ['Required tensile area', analysis.required_stress_area * 1e6, 'mm^2'],
            ['Proof capacity', analysis.proof_capacity / 1000, 'kN'],
            ['Proof margin', analysis.proof_margin, ''], ['Scope', analysis.limitations, '']);
        const csv = rows.map((row) => row.map((value) => {
            let text = String(value ?? '');
            if (typeof value === 'string' && /^\s*[=+@-]/.test(text)) text = "'" + text;
            return '"' + text.replaceAll('"', '""') + '"';
        }).join(',')).join('\n');
        const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = 'thread-results.csv';
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    });

    window.threadSpecification = {
        get section() { return section; },
        get autoUpdate() { return isAutoUpdate(); },
        get currentState() { return calculationState(); },
        useCandidate(row, hand) {
            if (specifyEdited && !window.confirm('Replace the edited specification with this nominal candidate? Your Find measurements will be kept.')) return;
            states.specify = { ...defaults, family: row.family, size: row.size,
                feature: window.threadFinder.state().side === 'internal' ? 'through' : row.kind === 'pipe' ? 'pipe_external' : 'nominal',
                view: window.threadFinder.state().side === 'internal' ? 'internal' : 'external',
                hand: hand === 'LH' ? 'LH' : 'RH' };
            transferred = true; specifyEdited = true;
            showSection('specify');
        },
        renderCandidate(row, search) {
            if (section !== 'find') return;
            const note = row ? ['POSSIBLE NOMINAL CANDIDATE: ' + row.designation,
                'Measured diameter: ' + (search.diameter_mm == null ? 'not supplied' : search.diameter_mm + ' mm') + '; basis: ' + search.side + '.',
                'Measured pitch: ' + (search.pitch_mm == null ? 'not supplied' : search.pitch_mm + ' mm') + '.',
                'Hand: ' + (search.observations.hand || 'unknown') + '. Fit, material, process and ratings remain unknown.',
                'Source: ' + row.source + '.', '', ...search.warnings].join('\n') : '';
            const changed = row?.id !== (result?.resolved_family + ':' + result?.resolved_size);
            result = { specification: row ? { callout: row.designation, note, breakdown: [['Source', row.source], ['Scope', 'Possible nominal candidate, not a drawing specification']],
                kind: row.kind, family: row.family, side: search.side === 'internal' ? 'internal' : 'external',
                diagram: row.diagram, status: 'Possible candidate; verify before specifying' } : null,
                geometry: row?.geometry, analysis: null, resolved_family: row?.family, resolved_size: row?.size };
            if (changed && row && search.side !== 'unsure') currentView = search.side;
            render(result);
            byId('spec-result-heading').textContent = 'Possible thread candidates';
            byId('spec-result-caption').textContent = 'Diameter and pitch do not establish a fit class or rating.';
            byId('spec-status').textContent = search?.status === 'no-close-supported-match' ? 'No close match' : row ? 'Candidate only' : 'Measurements';
            if (!row) {
                byId('drawing-callout').textContent = 'Select a candidate to inspect its nominal profile';
                byId('profile-unavailable').textContent = 'Known nominal size? Use Specify a thread. Unknown pitch? Print a comparison sheet below.';
            }
            byId('export-results').disabled = true;
        },
        refresh() { if (isAutoUpdate()) update(); },
        refreshDisplay() { if (section === 'find') window.threadFinder.present(); else if (result) render(result); },
        shareUrl,
        copyLink() { return copyText(shareUrl(), 'Link'); },
        initialize(module, autoUpdate, renderer) {
            python = module;
            isAutoUpdate = autoUpdate;
            drawGeometry = renderer;
            catalog = plain(python.specification_catalog());
            expert = plain(python.specification_options());
            restoreUrl();
            byId('spec-update').disabled = false;
            update();
        }
    };
})();
