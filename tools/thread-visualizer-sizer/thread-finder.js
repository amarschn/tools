/* Find's observations and selection stay independent from design choices. */
(() => {
    'use strict';
    const el = (id) => document.getElementById(id);
    const form = el('find-form');
    let python, result = null, selected = null, timer, count = 5, restoreError = '';
    let units = { unit: 'mm', pitch_unit: 'mm' };
    const plain = (proxy) => {
        try { return proxy.toJs({ dict_converter: Object.fromEntries }); }
        finally { proxy.destroy(); }
    };
    const state = () => Object.fromEntries(new FormData(form));
    const numeric = (value) => value == null ? 'not compared' : Number(value).toFixed(3).replace(/\.?0+$/, '');
    const title = (row) => row.designation + (row.pitch_only ? ' · pitch only' : '');

    function measurementHelp() {
        const side = state().side;
        el('find-diameter-label').textContent = { external: 'Across the crests', internal: 'Bore / minor diameter', unsure: 'Diameter (basis unknown)' }[side];
        el('measurement-title').textContent = side === 'internal' ? 'Internal measurement across opposing thread crests inside the bore' : 'Measure across thread crests, perpendicular to the axis';
        el('measurement-caption').textContent = side === 'internal' ? 'Inside the bore; caliper access is limited' : side === 'unsure' ? 'Confirm the measurement basis before using diameter' : 'Across crests, perpendicular to the axis';
        // A separate bore section, not an external major-diameter illustration.
        el('measurement-outline').setAttribute('d', side === 'internal'
            ? 'M35 12H210V28h-20l-7-8-7 8h-8l-7-8-7 8h-8l-7-8-7 8h-8l-7-8-7 8h-8l-7-8-7 8H35ZM35 58h49l7 8 7-8h8l7 8 7-8h8l7 8 7-8h8l7 8 7-8h8l7 8 7-8h20v16H35Z'
            : 'M35 25h10l7 9 7-9h7l7 9 7-9h7l7 9 7-9h7l7 9 7-9h7l7 9 7-9h7l7 9 7-9h7l7 9 7-9h7l7 9 7-9h7V61h-7l-7-9-7 9h-7l-7-9-7 9h-7l-7-9-7 9h-7l-7-9-7 9h-7l-7-9-7 9h-7l-7-9-7 9h-7l-7-9-7 9H35Z');
        el('measurement-line').setAttribute('d', side === 'internal' ? 'M210 28h42m-42 30h42M242 28v30' : 'M208 25h43m-43 36h43M242 25v36');
        el('measurement-tip').setAttribute('d', side === 'internal' ? 'm242 28-3 7h6zm0 30-3-7h6z' : 'm242 25-3 7h6zm0 36-3-7h6z');
        window.threadFieldHelp.refresh();
    }

    function present() {
        window.threadSpecification.renderCandidate(selected, result);
        const labels = {
            incomplete: 'Start with a diameter or pitch. Not sure of the pitch? Print a comparison sheet.',
            'no-close-supported-match': 'No close supported match. Recheck your measurements or consider a family outside this catalog.',
            ambiguous: `${result?.candidates.length || 0} possible candidates. More than one thread may fit these observations.`,
            'possible-match': 'One close supported candidate. Confirm it with further measurements or proper gaging.',
        };
        el('find-summary').textContent = result ? labels[result.status] : 'Enter measurements to compare supported nominal threads.';
        el('find-candidates').replaceChildren(...(result?.candidates || []).slice(0, count).map((row) => {
            const item = document.createElement('div');
            item.className = 'find-candidate';
            const button = document.createElement('button');
            button.type = 'button'; button.className = 'candidate-select';
            button.setAttribute('aria-pressed', String(selected?.id === row.id));
            const name = document.createElement('strong'); name.textContent = title(row);
            const detail = document.createElement('span');
            detail.textContent = `P ${numeric(row.pitch_mm)} mm · ${numeric(row.tpi)} TPI · difference ${numeric(row.delta_p_mm)} mm`;
            const diameter = document.createElement('span');
            diameter.textContent = row.kind === 'pipe' ? 'Diameter not ranked: measurement-plane data unavailable'
                : row.expected_diameter_mm == null ? 'Diameter basis unknown; pitch comparison only'
                : `${row.basis}: ${numeric(row.expected_diameter_mm)} mm · difference ${numeric(row.delta_d_mm)} mm`;
            button.append(name, detail, diameter);
            button.addEventListener('click', () => { selected = row; present(); });
            item.append(button);
            if (selected?.id === row.id) {
                const transfer = document.createElement('button');
                transfer.type = 'button'; transfer.className = 'btn-secondary'; transfer.textContent = 'Use this candidate in Specify';
                transfer.addEventListener('click', () => window.threadSpecification.useCandidate(row, state().hand));
                item.append(transfer);
            }
            return item;
        }));
        el('find-show-more').hidden = count >= (result?.candidates.length || 0);
        el('find-explanation').replaceChildren(...[...(result?.equations || []), ...(result?.warnings || [])].map((text) => {
            const p = document.createElement('p'); p.textContent = text; return p;
        }));
        measurementHelp();
    }

    function update() {
        if (!python) return;
        clearTimeout(timer);
        try {
            if (restoreError) throw new Error(restoreError);
            result = plain(python.find_threads(JSON.stringify(state())));
            selected = result.candidates.find((row) => row.id === selected?.id) || null;
            el('find-error').hidden = true;
        } catch (error) {
            result = null; selected = null;
            el('find-error').textContent = restoreError || String(error.message).match(/ValueError: (.+)/)?.[1] || 'Check the entered measurements.';
            el('find-error').hidden = false;
        }
        present();
    }

    function changed() {
        clearTimeout(timer);
        restoreError = '';
        selected = null; result = null; count = 5;
        present();
        window.threadExports.invalidate();
        if (window.threadSpecification.autoUpdate) timer = setTimeout(update, 240);
    }
    form.addEventListener('submit', (event) => { event.preventDefault(); update(); });
    form.addEventListener('input', (event) => { if (event.target.tagName !== 'SELECT') changed(); });
    form.addEventListener('change', (event) => {
        const values = state();
        if (event.target.name === 'unit') {
            const factor = values.unit === 'mm' ? 25.4 : 1 / 25.4;
            if (units.unit !== values.unit) ['diameter', 'span', 'second_diameter', 'separation', 'diameter_uncertainty'].forEach((name) => {
                if (values[name] && Number.isFinite(Number(values[name]))) form.elements[name].value = String(Number(values[name]) * factor);
            });
        }
        if (event.target.name === 'pitch_unit' && units.pitch_unit !== values.pitch_unit && Number(values.pitch) > 0) form.elements.pitch.value = String(25.4 / Number(values.pitch));
        units = { unit: values.unit, pitch_unit: values.pitch_unit };
        changed();
    });
    el('find-show-more').addEventListener('click', () => { count += 10; present(); });
    el('find-example').addEventListener('click', () => {
        form.reset(); form.elements.diameter.value = '7.95'; form.elements.pitch.value = '1.25';
        restoreError = '';
        units = { unit: 'mm', pitch_unit: 'mm' }; selected = null; update();
    });

    window.threadFinder = {
        get result() { return result; }, get selected() { return selected; }, state, update, present,
        initialize(module) {
            python = module;
            const records = plain(python.comparison_records());
            for (const family of [...new Set(records.map((row) => row.family))]) el('find-family').add(new Option(family === 'metric' ? 'ISO metric' : family.toUpperCase(), family));
        },
        restore(params, legacy = false) {
            const values = {};
            if (legacy) {
                const inch = params.get('system') === 'unified' || ['unc', 'unf', 'unef'].includes(params.get('spec_family'));
                Object.assign(values, { side: 'external', unit: inch ? 'in' : 'mm', pitch_unit: inch ? 'tpi' : 'mm',
                    diameter: params.get('spec_measured_diameter') || params.get('diameter') || '',
                    pitch: params.get('spec_measured_pitch') || params.get('pitch') || '' });
            } else for (const key of Object.keys(state())) if (params.has('find_' + key)) values[key] = params.get('find_' + key);
            try {
                if (!legacy && params.has('find_version') && params.get('find_version') !== '1') throw new Error('Unsupported saved Find version. Enter new measurements.');
                plain(python.find_threads(JSON.stringify({ ...state(), ...values })));
            } catch (error) { restoreError = 'Saved measurements need review: ' + (String(error.message).match(/ValueError: (.+)/)?.[1] || error.message); }
            for (const [key, value] of Object.entries(values)) form.elements[key].value = value;
            // Invalid select values remain invalid and are rejected by Python.
            units = { unit: form.elements.unit.value, pitch_unit: form.elements.pitch_unit.value };
            const id = params.get('find_selected');
            selected = id ? { id } : null;
        },
        appendUrl(url) {
            url.searchParams.set('find_version', '1');
            for (const [key, value] of Object.entries(state())) if (value !== '') url.searchParams.set('find_' + key, value);
            if (selected) url.searchParams.set('find_selected', selected.id);
        },
    };
})();
