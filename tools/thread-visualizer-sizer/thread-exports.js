/* Lightweight export state. Kernel and viewer load only on Preview 3D. */
(() => {
    'use strict';
    const el = (id) => document.getElementById(id);
    const panelStates = new Map();
    // Dispatch synchronously; native toggle events may arrive after preview starts.
    function syncPanel(panel) {
        if (panelStates.get(panel) === panel.open) return;
        panelStates.set(panel, panel.open);
        if (panel.open) {
            for (const other of panelStates.keys()) {
                if (other !== panel) { other.open = false; syncPanel(other); }
            }
        }
        window.threadFieldHelp.close();
        panel.dispatchEvent(new Event(panel.open ? 'thread-export-open' : 'thread-export-close'));
    }
    function setPanel(panel, open) { panel.open = open; syncPanel(panel); }
    for (const kind of ['print', 'step']) {
        const panel = el(kind + '-options');
        panelStates.set(panel, false);
        const summary = panel.querySelector(':scope > summary');
        summary.addEventListener('click', (event) => {
            event.preventDefault(); setPanel(panel, !panel.open);
        });
        panel.addEventListener('toggle', () => syncPanel(panel));
        document.querySelectorAll('[data-open-' + kind + ']').forEach((button) => {
            button.setAttribute('aria-controls', panel.id);
            button.addEventListener('click', () => { setPanel(panel, true); summary.focus(); });
        });
    }
    let python, payload = null, state = null, model = null, cadNote = '', activated = false;
    let worker = null, job = 0, timeout = null, busy = false, completedJobs = 0;
    let viewer = null, prepared = null, retry = 0;
    const plain = (proxy) => { try { return proxy.toJs({ dict_converter: Object.fromEntries }); } finally { proxy.destroy(); } };
    const detailNote = (base) => base + (cadNote ? '\n\n' + cadNote : '');
    function refreshNote() {
        if (payload?.specification) el('spec-note').textContent = detailNote(payload.specification.note);
    }
    function discard() {
        viewer?.dispose(); viewer = null; prepared = null;
        el('step-preview').hidden = true;
        el('step-preview-callout').textContent = '';
        el('step-view-info').textContent = '';
        ['step-view-edges', 'step-view-section'].forEach((id) => el(id).setAttribute('aria-pressed', 'false'));
        el('download-thread-step').disabled = true;
    }
    function cancel(message = 'Canceled. You can preview again.') {
        job++; clearTimeout(timeout); worker?.terminate(); worker = null; busy = false; completedJobs = 0;
        discard(); el('step-status').textContent = message; el('cancel-thread-step').hidden = true;
        el('preview-thread-step').disabled = !model;
    }
    function updateControls() {
        const supported = !!payload?.geometry && window.threadSpecification.section !== 'find';
        el('step-fields').hidden = !supported;
        el('step-scope').textContent = supported
            ? 'Preview reimports the generated STEP. Finished lead-ins are selectable; fit limits, rounded roots, coating and runout are not modeled.'
            : window.threadSpecification.section === 'find'
                ? 'Use a candidate in Specify before choosing a nominal CAD specimen. Measurements alone do not define a drawing or fit.'
                : 'STEP is available for metric and Unified profiles. Pipe needs reference-plane and profile data; forming and wood screws need supplier geometry.';
        model = null; cadNote = '';
        if (supported) {
            const profile = payload.geometry.physical_model, internal = el('step-specimen').value === 'internal';
            el('step-body-group').hidden = !internal;
            el('step-blind-group').hidden = state.feature !== 'blind';
            el('step-chamfer-fields').hidden = el('step-end-style').value !== 'chamfer';
            el('step-defaults').textContent = `Hand: ${state.hand}. Blank overall length suggests ${(2 * profile.major_diameter_mm).toFixed(3)} mm (2d, export only). ${internal ? 'Blank coupon diameter suggests ' + (1.8 * profile.major_diameter_mm).toFixed(3) + ' mm. ' : ''}Maximum 20 turns / 250 mm; shorten fine-thread specimens if needed.`;
            if (activated && python) {
                try {
                    model = plain(python.step_model(JSON.stringify({ ...state,
                        family: payload.resolved_family, size: payload.resolved_size,
                        specimen: el('step-specimen').value, length: el('step-length').value,
                        body_diameter: el('step-body').value, blind_coupon: el('step-blind').checked,
                        end_style: el('step-end-style').value, ends: el('step-ends').value,
                        chamfer_angle: el('step-chamfer-angle').value, chamfer_depth: el('step-chamfer-depth').value,
                    })));
                    cadNote = model.cad_note;
                    el('step-end-summary').textContent = model.end_condition + ` Full-profile envelope span: ${(model.full_profile_range_mm[1] - model.full_profile_range_mm[0]).toFixed(4)} mm.`;
                } catch (error) {
                    el('step-end-summary').textContent = String(error.message).match(/ValueError: (.+)/)?.[1] || error.message;
                }
            }
        }
        el('preview-thread-step').disabled = !model || busy;
        el('download-thread-step').disabled = !prepared || busy;
        refreshNote(); window.threadFieldHelp.refresh();
    }
    function viewerUnavailable(message) {
        viewer?.dispose(); viewer = null;
        el('step-view').textContent = '3D display unavailable. The checked STEP is still available to download.';
        el('step-view-info').textContent = message + ' Reload the page to retry a failed viewer dependency.';
    }
    el('preview-thread-step').addEventListener('click', () => {
        if (!model || busy) return;
        discard(); const current = model, id = ++job;
        busy = true; el('preview-thread-step').disabled = true; el('cancel-thread-step').hidden = false;
        el('step-status').textContent = 'Loading CAD preview…';
        const viewerUrl = new URL(window.threadAssetUrl('thread-cad-viewer.js'));
        if (retry) viewerUrl.searchParams.set('retry', retry);
        const rendering = import(viewerUrl.href).catch((error) => ({ error }));
        try {
            worker ||= new Worker(window.threadAssetUrl('thread-cad-worker.js'), { type: 'module' });
            timeout = setTimeout(() => cancel('CAD preview exceeded 90 seconds. Try a shorter specimen.'), 90000);
            worker.onerror = (event) => { event.preventDefault(); retry++; cancel('Could not load or run the CAD worker. Check the connection and preview again.'); };
            worker.onmessage = async ({ data }) => {
                if (data.id !== job) return;
                if (data.stage) { el('step-status').textContent = data.stage + '…'; return; }
                if (data.error) { cancel(data.error); return; }
                if (++completedJobs >= 3) { worker.terminate(); worker = null; completedJobs = 0; }
                const module = await rendering;
                if (id !== job) return;
                clearTimeout(timeout);
                prepared = { blob: data.blob, model: current };
                el('step-preview-callout').textContent = current.step_name;
                el('step-preview').hidden = false;
                el('step-view').replaceChildren();
                try {
                    if (module.error) throw module.error;
                    viewer = module.createCADViewer(el('step-view'), data.mesh, current, () => viewerUnavailable('The graphics context was lost.'));
                    el('step-view-info').textContent = `Reimported STEP; ${Math.round(data.mesh.triangles.length / 3).toLocaleString()} display triangles. Display tolerance ${data.mesh.tolerance_mm.toFixed(4)} mm, not a manufacturing tolerance. z = 0 is the start face.`;
                } catch (error) { retry++; viewerUnavailable(error.message); }
                busy = false; el('cancel-thread-step').hidden = true; updateControls();
                el('step-status').textContent = `STEP checked and ready in ${(data.milliseconds / 1000).toFixed(1)} s after kernel initialization. Download saves this solid; changing inputs requires a new preview.`;
                el('step-preview').scrollIntoView({ block: 'nearest' });
            };
            worker.postMessage({ id, model: current, preview: true });
        } catch (error) { retry++; cancel('Could not start CAD preview. ' + error.message); }
    });
    el('download-thread-step').addEventListener('click', () => {
        if (!prepared || busy) return;
        const url = URL.createObjectURL(prepared.blob), link = document.createElement('a');
        link.href = url;
        link.download = `${prepared.model.designation}-${prepared.model.hand}-${prepared.model.specimen}-${prepared.model.length_mm}mm-representative-v2.step`.replace(/[^a-zA-Z0-9._-]/g, '_');
        link.click(); setTimeout(() => URL.revokeObjectURL(url), 10000);
    });
    el('cancel-thread-step').addEventListener('click', () => cancel());
    el('step-view-close').addEventListener('click', () => { cancel('Preview closed.'); el('preview-thread-step').focus(); });
    el('step-view-reset').addEventListener('click', () => viewer?.reset());
    ['edges', 'section'].forEach((kind) => el('step-view-' + kind).addEventListener('click', () => {
        if (!viewer) return;
        const button = el('step-view-' + kind), next = button.getAttribute('aria-pressed') !== 'true';
        button.setAttribute('aria-pressed', String(next)); viewer[kind](next);
    }));
    ['step-specimen', 'step-length', 'step-body', 'step-blind', 'step-end-style', 'step-ends', 'step-chamfer-angle', 'step-chamfer-depth'].forEach((id) => el(id).addEventListener('input', () => {
        cancel('CAD inputs changed. Preview again before downloading.'); activated = true; updateControls();
    }));
    el('step-options').addEventListener('thread-export-open', () => { activated = true; updateControls(); });
    el('step-options').addEventListener('thread-export-close', () => cancel('Preview closed.'));
    document.querySelector('a[href="#thread-end-guidance"]').addEventListener('click', () => {
        setPanel(el('step-options'), false);
        const target = el('thread-end-guidance');
        target.closest('details').open = true;
        target.tabIndex = -1; target.focus();
    });
    window.threadExports = {
        initialize(module) {
            python = module;
            const records = plain(python.comparison_records()); window.threadPrint.initialize(records);
            const pitches = new Set(records.map((row) => row.pitch_mm.toPrecision(12))).size;
            el('print-scope').options[1].textContent = `Common pitch strips (${pitches} pitches / ${Math.ceil(pitches / 4)} pages)`;
        },
        invalidate() {
            payload = null; model = null; cadNote = ''; window.threadPrint.invalidate();
            cancel('Specification changed. Preview again before downloading.');
        },
        setSpecification(next, values) {
            const changed = state?.family !== values.family || state?.size !== values.size || state?.side !== values.side;
            payload = next; state = values;
            if (changed) {
                discard(); el('step-length').value = ''; el('step-body').value = ''; el('step-blind').checked = false;
                el('step-specimen').value = values.side === 'internal' ? 'internal' : 'external';
                el('step-chamfer-depth').value = '';
            }
            updateControls(); window.threadPrint.sync();
        },
        detailNote,
        printContext() { return { section: window.threadSpecification.section, payload, state }; },
    };
})();
