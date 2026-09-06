/* Visible, keyboard- and touch-accessible help for every thread input.
 * Reuses each field's title and live aria-describedby guidance as the source.
 */
(() => {
    'use strict';

    const form = document.getElementById('spec-form');
    const entries = [];
    let active = null;
    let pinned = false;
    let hideTimer = null;

    function close() {
        window.clearTimeout(hideTimer);
        if (active) {
            active.tooltip.hidden = true;
            active.button.setAttribute('aria-expanded', 'false');
        }
        active = null;
        pinned = false;
    }

    function position() {
        if (!active) return;
        const { button, tooltip } = active;
        const anchor = button.getBoundingClientRect();
        const width = document.documentElement.clientWidth;
        const height = window.innerHeight;
        const gutter = 12;
        if (!button.getClientRects().length || anchor.bottom < 0 || anchor.top > height) {
            close();
            return;
        }
        tooltip.style.width = Math.min(360, width - gutter * 2) + 'px';
        tooltip.style.maxHeight = Math.max(80, height - gutter * 2) + 'px';
        const box = tooltip.getBoundingClientRect();
        const left = Math.max(gutter, Math.min(anchor.right - box.width, width - box.width - gutter));
        const below = anchor.bottom + 8;
        const above = anchor.top - box.height - 8;
        const top = below + box.height <= height - gutter ? below : above >= gutter ? above : gutter;
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
    }

    function refresh() {
        entries.forEach((entry) => {
            const { control, label, button, tooltip, introduction, sources } = entry;
            const name = label.textContent.trim();
            const selected = control.tagName === 'SELECT' ? control.selectedOptions[0]?.textContent : '';
            const guidance = sources.map((id) => document.getElementById(id)?.textContent.trim()).filter(Boolean);
            tooltip.textContent = [introduction, selected ? 'Selected: ' + selected + '.' : '', ...guidance].filter(Boolean).join('\n\n');
            button.setAttribute('aria-label', 'Help: ' + name);
        });
        position();
    }

    function show(entry) {
        window.clearTimeout(hideTimer);
        if (active !== entry) close();
        active = entry;
        entry.tooltip.hidden = false;
        entry.button.setAttribute('aria-expanded', 'true');
        refresh();
    }

    function scheduleClose(entry) {
        window.clearTimeout(hideTimer);
        hideTimer = window.setTimeout(() => {
            if (active === entry && !pinned && document.activeElement !== entry.button &&
                !entry.button.matches(':hover') && !entry.tooltip.matches(':hover')) close();
        }, 180);
    }

    document.querySelectorAll('#spec-form input[id], #spec-form select[id], #find-form input[id], #find-form select[id], #thread-export-controls input[id], #thread-export-controls select[id]').forEach((control) => {
        const label = control.labels[0];
        if (!label) return;
        const sources = (control.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
        const introduction = control.getAttribute('title') || '';
        const row = document.createElement('div');
        row.className = 'field-label-row';
        label.before(row);
        row.append(label);

        const tooltip = document.createElement('div');
        tooltip.id = control.id + '-tooltip';
        tooltip.className = 'thread-field-tooltip';
        tooltip.setAttribute('role', 'tooltip');
        tooltip.hidden = true;
        document.body.append(tooltip);

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'thread-help-trigger';
        button.dataset.helpFor = control.id;
        button.dataset.track = 'off';
        button.textContent = '?';
        button.setAttribute('aria-controls', tooltip.id);
        button.setAttribute('aria-describedby', tooltip.id);
        button.setAttribute('aria-expanded', 'false');
        row.append(button);
        // The same description is accessible from the field itself, without
        // a second native tooltip competing with the visible help button.
        control.removeAttribute('title');
        control.setAttribute('aria-describedby', tooltip.id);
        const entry = { control, label, button, tooltip, introduction, sources };
        entries.push(entry);

        button.addEventListener('pointerenter', (event) => {
            if (event.pointerType !== 'touch') show(entry);
        });
        button.addEventListener('pointerleave', () => scheduleClose(entry));
        button.addEventListener('focus', () => show(entry));
        button.addEventListener('blur', (event) => {
            // Keep readable text open when clicking it to select or scroll.
            // Keyboard navigation to another control should dismiss it.
            if (active === entry && (event.relatedTarget || !tooltip.matches(':hover'))) close();
        });
        button.addEventListener('click', () => {
            if (active === entry && pinned) close();
            else { show(entry); pinned = true; }
        });
        tooltip.addEventListener('pointerenter', () => window.clearTimeout(hideTimer));
        tooltip.addEventListener('pointerleave', () => scheduleClose(entry));
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && active) {
            close();
            event.preventDefault();
        }
    });
    document.addEventListener('pointerdown', (event) => {
        if (active && !active.button.contains(event.target) && !active.tooltip.contains(event.target)) close();
    });
    window.addEventListener('resize', position);
    window.addEventListener('scroll', position, { capture: true, passive: true });
    form.addEventListener('toggle', position, true);
    refresh();
    window.threadFieldHelp = { refresh, close };
})();
