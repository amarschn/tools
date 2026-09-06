/* Small export controller. PDF and CAD runtimes load only on explicit request. */
(() => {
    'use strict';
    const el = (id) => document.getElementById(id);
    let python, records = [], payload = null, state = null;
    let worker = null, job = 0, timeout = null, snapshot = 0, busy = false, completedJobs = 0;
    const plain = (proxy) => { try { return proxy.toJs({ dict_converter: Object.fromEntries }); } finally { proxy.destroy(); } };
    const download = (blob, filename) => {
        const url = URL.createObjectURL(blob), link = document.createElement('a');
        link.href = url; link.download = filename; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 10000);
    };
    function cancel(message = 'Canceled. You can try again.') {
        job++; clearTimeout(timeout); worker?.terminate(); worker = null; busy = false;
        completedJobs = 0;
        el('step-status').textContent = message;
        el('cancel-thread-step').hidden = true;
        el('download-thread-step').disabled = !payload?.geometry;
    }
    function updateControls() {
        const supported = !!payload?.geometry && window.threadSpecification.section !== 'find';
        el('step-fields').hidden = !supported;
        el('step-scope').textContent = supported
            ? payload.geometry.physical_model.limitation + ' Square ends clip partial turns; model length is not full-thread length.'
            : window.threadSpecification.section === 'find'
                ? 'Select a candidate, then use it in Specify to choose a nominal CAD specimen. Measurements alone do not define a drawing or fit.'
                : 'STEP is available for validated metric and Unified nominal profiles. Pipe needs reference-plane diameters and profile data; forming and wood screws need supplier geometry.';
        if (!supported) return;
        const model = payload.geometry.physical_model;
        const internal = el('step-specimen').value === 'internal';
        el('step-body-group').hidden = !internal;
        el('step-blind-group').hidden = state.feature !== 'blind';
        el('step-defaults').textContent = `Hand: ${state.hand}. Blank length suggests ${(2 * model.major_diameter_mm).toFixed(3)} mm (2d, export only). ${internal ? 'Blank coupon diameter suggests ' + (1.8 * model.major_diameter_mm).toFixed(3) + ' mm. ' : ''}Maximum 20 turns / 250 mm; shorten fine-thread specimens if needed.`;
        el('download-thread-step').disabled = busy;
    }
    el('download-thread-step').addEventListener('click', () => {
        if (!python || !payload?.geometry || busy) return;
        try {
            const model = plain(python.step_model(JSON.stringify({ ...state,
                family: payload.resolved_family, size: payload.resolved_size,
                specimen: el('step-specimen').value, length: el('step-length').value,
                body_diameter: el('step-body').value, blind_coupon: el('step-blind').checked,
            })));
            if (state.feature === 'blind' && model.specimen !== 'internal') throw new Error('For a blind specification, select the separate internal through-thread coupon.');
            const id = ++job;
            busy = true; updateControls(); el('cancel-thread-step').hidden = false;
            el('step-status').textContent = 'Loading CAD worker…';
            worker ||= new Worker(window.threadAssetUrl('thread-cad-worker.js'), { type: 'module' });
            timeout = setTimeout(() => cancel('Export exceeded 90 seconds. Try a shorter specimen.'), 90000);
            worker.onerror = (event) => { event.preventDefault(); cancel('Could not load or run the local CAD kernel. Check the connection and retry; other tools still work.'); };
            worker.onmessage = ({ data }) => {
                if (data.id !== job) return;
                if (data.stage) { el('step-status').textContent = data.stage + '…'; return; }
                clearTimeout(timeout); busy = false; el('cancel-thread-step').hidden = true; updateControls();
                if (data.error) { cancel(data.error); return; }
                const filename = `${model.designation}-${model.hand}-${model.specimen}-${model.length_mm}mm-representative-v1.step`.replace(/[^a-zA-Z0-9._-]/g, '_');
                download(data.blob, filename);
                if (++completedJobs >= 3) { worker.terminate(); worker = null; completedJobs = 0; }
                el('step-status').textContent = `STEP prepared in ${(data.milliseconds / 1000).toFixed(1)} s after kernel initialization. Representative geometry; verify the import in your CAD system.`;
            };
            worker.postMessage({ id, model });
        } catch (error) {
            if (busy) cancel();
            el('step-status').textContent = String(error.message).match(/ValueError: (.+)/)?.[1] || error.message;
        }
    });
    el('cancel-thread-step').addEventListener('click', () => cancel());
    ['step-specimen', 'step-length', 'step-body', 'step-blind'].forEach((id) => el(id).addEventListener('input', () => { if (busy) cancel('Export canceled because specimen inputs changed.'); updateControls(); }));
    document.querySelectorAll('[data-open-print]').forEach((button) => button.addEventListener('click', () => {
        el('print-options').open = true; el('print-options').scrollIntoView({ block: 'center', behavior: 'smooth' }); el('download-thread-pdf').focus();
    }));
    el('download-thread-pdf').addEventListener('click', async () => {
        if (!python) return;
        const finder = window.threadSpecification.section === 'find';
        // An explicit export must flush a pending measurement debounce, even
        // with auto-update off. Never turn a pending shortlist into a common sheet.
        if (finder) window.threadFinder.update();
        const token = snapshot;
        let selected = finder ? window.threadFinder.result?.candidates || []
            : records.filter((row) => row.family === payload?.resolved_family && row.size === payload?.resolved_size);
        const common = el('print-scope').value === 'common' || (finder && !selected.length && !window.threadFinder.result?.pitch_mm);
        if (common) selected = records;
        el('print-status').textContent = 'Preparing vector PDF…';
        el('download-thread-pdf').disabled = true;
        try {
            const { buildComparisonPDF } = await import(window.threadAssetUrl('thread-print.js'));
            const observations = finder ? window.threadFinder.state() : null;
            const options = { paper: el('print-paper').value, side: finder ? observations.side : state?.side,
                url: el('print-private').checked ? window.threadSpecification.shareUrl() : null,
                observations: el('print-private').checked && observations ? `diameter ${observations.diameter || 'unknown'} ${observations.unit}; pitch ${observations.pitch || 'unknown'} ${observations.pitch_unit}; span ${observations.span || '-'} / ${observations.intervals || '-'} intervals` : null };
            const { bytes } = await buildComparisonPDF(selected, options);
            if (token !== snapshot) throw new Error('Inputs changed. Generate a new sheet for the current measurements.');
            download(new Blob([bytes], { type: 'application/pdf' }), `thread-comparison-${options.paper}.pdf`);
            el('print-status').textContent = `${common ? 'Common supported pitches. ' : ''}PDF ready. Print at 100% and measure both calibration checks before comparing.`;
        } catch (error) { el('print-status').textContent = error.message; }
        finally { el('download-thread-pdf').disabled = false; }
    });
    window.threadExports = {
        initialize(module) {
            python = module; records = plain(python.comparison_records());
            const pitches = new Set(records.map((row) => row.pitch_mm.toPrecision(12))).size;
            el('print-scope').options[1].textContent = `All ${pitches} supported pitches (${Math.ceil(pitches / 4)} pages)`;
        },
        invalidate() {
            snapshot++; payload = null;
            if (busy) cancel('Export canceled because the specification changed.');
            el('download-thread-step').disabled = true;
        },
        setSpecification(next, values) {
            const changed = state?.family !== values.family || state?.size !== values.size || state?.side !== values.side;
            payload = next; state = values;
            if (changed) { el('step-length').value = ''; el('step-body').value = ''; el('step-blind').checked = false; el('step-specimen').value = values.side === 'internal' ? 'internal' : 'external'; }
            updateControls();
        },
    };
})();
