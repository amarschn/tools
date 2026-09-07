/* Lightweight sheet selection. PDF generation and rendering stay lazy. */
(() => {
    'use strict';
    const el = (id) => document.getElementById(id);
    let records = [], checked = new Set(), suggested = [], contextKey = '';
    let epoch = 0, busy = false, documentUrl = null, renderer = null, manifest = null, pageNumber = 1;
    let failedImports = 0, resizeTimer, renderSequence = 0;
    const context = () => window.threadExports.printContext();
    const caption = (row) => `${row.designation}${row.kind === 'pipe' ? ' · pitch only' : ''}`;
    const sourceRows = () => {
        const { section, payload } = context();
        return section === 'find' ? window.threadFinder.result?.candidates || []
            : records.filter((row) => row.family === payload?.resolved_family && row.size === payload?.resolved_size);
    };

    function invalidate(message = 'Sheet inputs changed. Preview again before printing or downloading.') {
        epoch++; busy = false;
        if (renderer) { renderer.destroy().catch(() => {}); renderer = null; }
        if (documentUrl) { URL.revokeObjectURL(documentUrl); documentUrl = null; }
        manifest = null;
        el('print-preview').hidden = true;
        el('print-canvas').width = 0;
        el('print-canvas').height = 0;
        el('print-page-description').textContent = '';
        el('download-thread-pdf').disabled = true;
        el('print-thread-pdf').removeAttribute('href');
        el('print-thread-pdf').hidden = true;
        el('print-status').textContent = message;
        updateControls();
    }

    function updateControls() {
        const common = el('print-scope').value === 'common';
        el('print-size-options').hidden = common;
        const unknown = window.threadSpecification?.section === 'find' && window.threadFinder.state().side === 'unsure';
        el('print-side-group').hidden = !unknown;
        el('preview-thread-pdf').disabled = busy || (!common && (!checked.size || (unknown && !el('print-side').value)));
    }

    function choice(row, prefix) {
        const label = document.createElement('label');
        label.className = 'print-choice';
        const box = document.createElement('input');
        box.type = 'checkbox'; box.id = prefix + records.findIndex((record) => record.id === row.id);
        box.checked = checked.has(row.id);
        box.title = `Include ${row.designation} as its own row. ${row.kind === 'pipe' ? 'Pitch comparison only; diameter and actual-size pipe profile are unavailable.' : 'The diameter and profile are nominal/basic, not acceptance limits.'}`;
        const name = document.createElement('span'); name.textContent = caption(row);
        label.append(box, name);
        box.addEventListener('change', () => {
            if (box.checked && checked.size >= 16) {
                box.checked = false; el('print-status').textContent = 'Compare up to 16 sizes at once. Remove one before adding another.'; return;
            }
            if (box.checked) checked.add(row.id); else checked.delete(row.id);
            invalidate(); renderChoices();
            (el('print-choice-' + records.findIndex((record) => record.id === row.id)) || el('print-search')).focus();
        });
        return label;
    }

    function renderAddList() {
        const query = el('print-search').value.toLowerCase().replace(/\s+/g, '');
        const matches = records.filter((row) => !checked.has(row.id) &&
            (row.designation + row.family).toLowerCase().replace(/\s+/g, '').includes(query));
        el('print-add-list').replaceChildren(...matches.slice(0, 12).map((row) => choice(row, 'print-add-')));
        el('print-add-count').textContent = matches.length > 12 ? `Showing 12 of ${matches.length}. Refine the search to find a size.` : `${matches.length} other supported sizes.`;
        window.threadFieldHelp.register(el('print-add-list'));
    }

    function renderChoices() {
        const ids = new Set([...suggested.map((row) => row.id), ...checked]);
        const rows = [...ids].map((id) => records.find((row) => row.id === id)).filter(Boolean);
        el('print-candidate-list').replaceChildren(...rows.map((row) => choice(row, 'print-choice-')));
        if (!rows.length) el('print-candidate-list').textContent = 'No current candidates. Add sizes below or choose Common pitch strips.';
        window.threadFieldHelp.register(el('print-candidate-list'));
        if (el('print-add-options').open) renderAddList();
        updateControls();
    }

    function sync() {
        if (!records.length || !el('print-options').open) return;
        const current = context(), rows = sourceRows();
        const key = JSON.stringify([current.section, current.section === 'find' ? window.threadFinder.state() : current.state,
            rows.map((row) => row.id)]);
        if (key === contextKey) return;
        contextKey = key;
        suggested = rows.slice(0, 4);
        checked = new Set(suggested.map((row) => row.id));
        invalidate('Choose threads, then preview the comparison PDF.');
        renderChoices();
    }

    async function showPage(number) {
        if (!renderer) return;
        const token = epoch, current = renderer, sequence = ++renderSequence;
        pageNumber = number;
        el('print-previous').disabled = true; el('print-next').disabled = true;
        el('print-page-label').textContent = `Page ${number} of ${current.pages}`;
        try {
            const description = await current.render(number, el('print-canvas'), Math.max(220, el('print-preview-page').clientWidth - 2));
            if (token !== epoch || sequence !== renderSequence) return;
            const names = manifest.pages[number - 1].strips.map((row) => row.designation).join('; ');
            el('print-page-description').textContent = `On this page: ${names}.`;
            el('print-canvas').setAttribute('aria-label', description || `Comparison PDF page ${number}`);
            el('print-canvas').dataset.page = String(number);
            el('print-previous').disabled = number === 1;
            el('print-next').disabled = number === current.pages;
        } catch (error) {
            if (token !== epoch || error.name === 'RenderingCancelledException') return;
            throw error;
        }
    }

    const moduleUrl = (path) => {
        const url = new URL(window.threadAssetUrl(path));
        if (failedImports) url.searchParams.set('retry', failedImports);
        return url.href;
    };
    el('preview-thread-pdf').addEventListener('click', async () => {
        if (busy || !records.length) return;
        if (window.threadSpecification.section === 'find') window.threadFinder.update();
        sync();
        const current = context(), common = el('print-scope').value === 'common';
        const selected = common ? records : [...checked].map((id) => records.find((row) => row.id === id));
        if (!selected.length) return;
        const observations = current.section === 'find' ? window.threadFinder.state() : null;
        const side = observations?.side === 'unsure' ? el('print-side').value : observations?.side || current.state?.side || 'external';
        if (!common && !side) return;
        invalidate('Preparing PDF preview…'); busy = true; updateControls();
        const token = epoch;
        try {
            const [{ buildComparisonPDF }, { createPDFPreview }] = await Promise.all([
                import(moduleUrl('thread-print.js')), import(moduleUrl('thread-pdf-preview.js')),
            ]);
            if (token !== epoch) return;
            const { bytes, manifest: layout } = await buildComparisonPDF(selected, {
                paper: el('print-paper').value, layout: common ? 'pitches' : 'sizes', side,
                url: el('print-private').checked ? window.threadSpecification.shareUrl() : null,
                observations: el('print-private').checked && observations ? `diameter ${observations.diameter || 'unknown'} ${observations.unit}; pitch ${observations.pitch || 'unknown'} ${observations.pitch_unit}; span ${observations.span || '-'} / ${observations.intervals || '-'} intervals` : null,
            });
            if (token !== epoch) return;
            const nextRenderer = await createPDFPreview(bytes);
            if (token !== epoch) { await nextRenderer.destroy(); return; }
            renderer = nextRenderer; manifest = layout;
            documentUrl = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
            el('print-preview').hidden = false;
            await showPage(1);
            if (token !== epoch) return;
            el('download-thread-pdf').disabled = false;
            el('print-thread-pdf').href = documentUrl; el('print-thread-pdf').hidden = false;
            el('print-status').textContent = `${layout.pages.length} ${layout.pages.length === 1 ? 'page' : 'pages'} ready. ${common ? 'Common pitch strips.' : selected.length + ' separately labeled sizes.'} Print at 100%; check both calibration marks.`;
            el('print-preview').scrollIntoView({ block: 'nearest' });
        } catch (error) {
            if (token !== epoch) return;
            failedImports++;
            invalidate('Could not preview the PDF. Check the connection and try again. ' + error.message);
        } finally { if (token === epoch) { busy = false; updateControls(); } }
    });
    el('download-thread-pdf').addEventListener('click', () => {
        if (!documentUrl || el('download-thread-pdf').disabled) return;
        const link = document.createElement('a');
        link.href = documentUrl; link.download = `thread-comparison-${manifest.paper}.pdf`; link.click();
    });
    const turnPage = (number) => showPage(number).catch((error) => invalidate('Could not render this page. Preview again. ' + error.message));
    el('print-previous').addEventListener('click', () => turnPage(pageNumber - 1));
    el('print-next').addEventListener('click', () => turnPage(pageNumber + 1));
    el('close-thread-pdf').addEventListener('click', () => { invalidate('Preview closed.'); el('preview-thread-pdf').focus(); });
    ['print-paper', 'print-scope', 'print-private', 'print-side'].forEach((id) => el(id).addEventListener('change', () => invalidate()));
    el('print-search').addEventListener('input', renderAddList);
    el('print-add-options').addEventListener('toggle', () => { if (el('print-add-options').open) renderAddList(); });
    el('print-options').addEventListener('thread-export-open', sync);
    el('print-options').addEventListener('thread-export-close', () => invalidate(''));
    let width = 0;
    new ResizeObserver(([entry]) => {
        if (Math.abs(entry.contentRect.width - width) < 1) return;
        width = entry.contentRect.width;
        clearTimeout(resizeTimer);
        if (renderer && width && !busy) resizeTimer = setTimeout(() => turnPage(pageNumber), 150);
    }).observe(el('print-preview-page'));
    window.threadPrint = { initialize(rows) { records = rows; }, invalidate, sync };
})();
