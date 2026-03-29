/**
 * URL State Module
 *
 * Provides shareable URL functionality for tools on transparent.tools.
 * Serializes input state to URL search params so users can share a link
 * that reproduces their exact configuration.
 *
 * Usage:
 *   Include in any tool page (before </body> or in <head> with defer):
 *   <script src="/shared/url-state.js"></script>
 *
 * The script auto-discovers inputs within .tool-inputs, .card, or <form>
 * elements. On page load it reads URL search params and populates matching
 * inputs by their ID, then fires events so tool calculations re-run.
 *
 * A "Copy Link" button is appended to .tool-header, .nav-actions, or
 * the first <h1>'s parent if those containers exist.
 *
 * Exports window.UrlState with a public getShareUrl() method.
 */
(function () {
    'use strict';

    // --- Configuration ---
    var DEBOUNCE_MS = 500;

    // --- State ---
    var debounceTimer = null;
    var inputElements = [];
    var initialized = false;

    // --- Helpers ---

    /**
     * Collect all eligible input elements on the page.
     * Searches .tool-inputs first, then falls back to form, then .card.
     * Returns an array of input/select elements that have an id attribute.
     */
    function discoverInputs() {
        var selectors = [
            '.tool-inputs input[type="number"]',
            '.tool-inputs input[type="range"]',
            '.tool-inputs input[type="text"]',
            '.tool-inputs select',
            'form input[type="number"]',
            'form input[type="range"]',
            'form input[type="text"]',
            'form select',
            '.card input[type="number"]',
            '.card input[type="range"]',
            '.card input[type="text"]',
            '.card select'
        ];

        var seen = {};
        var results = [];

        for (var i = 0; i < selectors.length; i++) {
            var els = document.querySelectorAll(selectors[i]);
            for (var j = 0; j < els.length; j++) {
                var el = els[j];
                if (!el.id) continue;
                if (seen[el.id]) continue;
                seen[el.id] = true;
                results.push(el);
            }
        }

        return results;
    }

    /**
     * Determine whether a range input is paired with a number input and
     * should be skipped to avoid duplicates.
     *
     * Common pairing patterns in this codebase:
     *   velocity-slider  <->  velocity-input   (suffix: -slider / -input)
     *   base_length_range <-> base_length       (suffix: _range)
     *   fin_count_range   <-> fin_count         (suffix: _range)
     *
     * A range input is considered "paired" if another discovered input
     * (type=number) has an id that is the range id minus its range-suffix.
     */
    function isRedundantRange(el, allInputs) {
        if (el.type !== 'range') return false;

        var id = el.id;
        var baseId = null;

        // Try stripping common suffixes
        if (id.match(/-slider$/))       baseId = id.replace(/-slider$/, '-input');
        else if (id.match(/_slider$/))  baseId = id.replace(/_slider$/, '_input');
        else if (id.match(/-range$/))   baseId = id.replace(/-range$/, '');
        else if (id.match(/_range$/))   baseId = id.replace(/_range$/, '');

        if (!baseId) return false;

        // Check if any of the discovered inputs match the base id
        for (var i = 0; i < allInputs.length; i++) {
            if (allInputs[i].id === baseId && allInputs[i].type === 'number') {
                return true;
            }
        }

        return false;
    }

    /**
     * Get the default value for an input element.
     * For inputs: the HTML attribute "value" (defaultValue).
     * For selects: the option with the "selected" attribute, or the first option.
     */
    function getDefaultValue(el) {
        if (el.tagName === 'SELECT') {
            // Find the option with the selected attribute in HTML
            var options = el.options;
            for (var i = 0; i < options.length; i++) {
                if (options[i].defaultSelected) {
                    return options[i].value;
                }
            }
            // Fall back to first option
            return options.length > 0 ? options[0].value : '';
        }
        // For input elements, defaultValue is the HTML attribute value
        return el.defaultValue;
    }

    /**
     * Get the current value of an input element.
     */
    function getCurrentValue(el) {
        return el.value;
    }

    /**
     * Build a URL with the current input state as search params.
     * Only includes values that differ from their defaults.
     */
    function getShareUrl() {
        var url = new URL(window.location.href);
        // Clear existing search params from our inputs
        url.search = '';

        var params = new URLSearchParams();

        for (var i = 0; i < inputElements.length; i++) {
            var el = inputElements[i];
            var current = getCurrentValue(el);
            var defaultVal = getDefaultValue(el);

            // Skip empty values
            if (current === '' || current === null || current === undefined) continue;

            // Skip values that match the default
            if (current === defaultVal) continue;

            params.set(el.id, current);
        }

        var paramStr = params.toString();
        if (paramStr) {
            url.search = '?' + paramStr;
        }

        return url.toString();
    }

    /**
     * Update the browser URL bar without adding a history entry.
     */
    function updateUrl() {
        var url = getShareUrl();
        try {
            history.replaceState(null, '', url);
        } catch (e) {
            // Silently ignore SecurityError in some contexts
        }
    }

    /**
     * Debounced URL update - called on input changes.
     */
    function scheduleUrlUpdate() {
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }
        debounceTimer = setTimeout(updateUrl, DEBOUNCE_MS);
    }

    /**
     * Read URL search params and populate inputs.
     * Returns true if any values were set from the URL.
     */
    function loadFromUrl() {
        var params = new URLSearchParams(window.location.search);
        var anySet = false;

        if (!params.toString()) return false;

        for (var i = 0; i < inputElements.length; i++) {
            var el = inputElements[i];
            var val = params.get(el.id);

            if (val === null || val === '') continue;

            // For number/range inputs, validate that the value is a number
            if (el.type === 'number' || el.type === 'range') {
                var num = parseFloat(val);
                if (isNaN(num)) continue;
                el.value = num;
            } else {
                // For text and select, set directly
                el.value = val;
            }

            anySet = true;
        }

        return anySet;
    }

    /**
     * Fire input and change events on all inputs that were set from URL,
     * so that tool calculations re-run.
     */
    function fireEventsOnAll() {
        for (var i = 0; i < inputElements.length; i++) {
            var el = inputElements[i];
            try {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (e) {
                // IE fallback (unlikely but safe)
                var evt = document.createEvent('Event');
                evt.initEvent('input', true, true);
                el.dispatchEvent(evt);
                var evt2 = document.createEvent('Event');
                evt2.initEvent('change', true, true);
                el.dispatchEvent(evt2);
            }
        }
    }

    /**
     * Also sync any paired range inputs that were not in our tracked list.
     * When we set a number input from URL params, its paired range slider
     * may need syncing too.
     */
    function syncPairedRanges() {
        var params = new URLSearchParams(window.location.search);

        for (var i = 0; i < inputElements.length; i++) {
            var el = inputElements[i];
            if (el.type !== 'number') continue;

            var val = params.get(el.id);
            if (val === null) continue;

            // Try to find the paired range element
            var id = el.id;
            var rangeCandidates = [
                id.replace(/-input$/, '-slider'),
                id.replace(/_input$/, '_slider'),
                id + '_range',
                id + '-range'
            ];

            for (var j = 0; j < rangeCandidates.length; j++) {
                var rangeEl = document.getElementById(rangeCandidates[j]);
                if (rangeEl && rangeEl.type === 'range') {
                    rangeEl.value = val;
                    try {
                        rangeEl.dispatchEvent(new Event('input', { bubbles: true }));
                        rangeEl.dispatchEvent(new Event('change', { bubbles: true }));
                    } catch (e) {
                        // Silently ignore
                    }
                }
            }
        }
    }

    /**
     * Create and inject the share/copy-link button into the page.
     */
    function createShareButton() {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'url-state-share-btn';
        btn.setAttribute('aria-label', 'Copy shareable link');
        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M6.5 8.5a3.5 3.5 0 0 0 5 0l2-2a3.5 3.5 0 0 0-5-5l-1 1"/>' +
            '<path d="M9.5 7.5a3.5 3.5 0 0 0-5 0l-2 2a3.5 3.5 0 0 0 5 5l1-1"/>' +
            '</svg> Copy Link';

        btn.addEventListener('click', function () {
            var url = getShareUrl();

            // Try clipboard API first, fall back to execCommand
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(function () {
                    showCopied(btn);
                }, function () {
                    fallbackCopy(url, btn);
                });
            } else {
                fallbackCopy(url, btn);
            }
        });

        // Inject styles for the button
        var style = document.createElement('style');
        style.textContent =
            '.url-state-share-btn {' +
            '  display: inline-flex;' +
            '  align-items: center;' +
            '  gap: 6px;' +
            '  border: 1px solid var(--border-color, #e5e7eb);' +
            '  background: var(--bg-card, #ffffff);' +
            '  color: var(--text-color, #111827);' +
            '  font-family: inherit;' +
            '  font-weight: 600;' +
            '  font-size: 0.85rem;' +
            '  padding: 8px 14px;' +
            '  border-radius: 999px;' +
            '  cursor: pointer;' +
            '  transition: background-color 0.15s ease, border-color 0.15s ease;' +
            '  white-space: nowrap;' +
            '  line-height: 1;' +
            '}' +
            '.url-state-share-btn:hover {' +
            '  background: var(--primary-light, #f4f5f7);' +
            '}' +
            '.url-state-share-btn svg {' +
            '  flex-shrink: 0;' +
            '}' +
            '.url-state-share-btn--copied {' +
            '  border-color: var(--success-color, #0f766e);' +
            '  color: var(--success-color, #0f766e);' +
            '}';
        document.head.appendChild(style);

        // Find a suitable container to append the button
        var container = findButtonContainer();
        if (container) {
            container.appendChild(btn);
        }

        return btn;
    }

    /**
     * Find the best container for the share button.
     * Priority:
     *   1. .nav-actions (navbar action area, used by newer tools)
     *   2. .tool-header (main tool header area)
     *   3. Parent of the first <h1> in main or .container
     */
    function findButtonContainer() {
        // 1. .nav-actions
        var navActions = document.querySelector('.nav-actions');
        if (navActions) return navActions;

        // 2. .tool-header
        var toolHeader = document.querySelector('.tool-header');
        if (toolHeader) return toolHeader;

        // 3. Parent of first h1 inside main or .container
        var main = document.querySelector('main') || document.querySelector('.container');
        if (main) {
            var h1 = main.querySelector('h1');
            if (h1 && h1.parentElement) return h1.parentElement;
        }

        return null;
    }

    /**
     * Show "Copied!" confirmation on the button, then revert.
     */
    function showCopied(btn) {
        var original = btn.innerHTML;
        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M13 4L6 11L3 8"/>' +
            '</svg> Copied!';
        btn.classList.add('url-state-share-btn--copied');

        setTimeout(function () {
            btn.innerHTML = original;
            btn.classList.remove('url-state-share-btn--copied');
        }, 2000);
    }

    /**
     * Fallback copy method using a temporary textarea.
     */
    function fallbackCopy(text, btn) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        textarea.style.top = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showCopied(btn);
        } catch (e) {
            // Last resort: prompt user
            window.prompt('Copy this link:', text);
        }
        document.body.removeChild(textarea);
    }

    /**
     * Attach input listeners to all tracked inputs for debounced URL updates.
     */
    function attachListeners() {
        for (var i = 0; i < inputElements.length; i++) {
            (function (el) {
                el.addEventListener('input', scheduleUrlUpdate);
                el.addEventListener('change', scheduleUrlUpdate);
            })(inputElements[i]);
        }
    }

    /**
     * Main initialization. Called on DOMContentLoaded or immediately if
     * the DOM is already loaded.
     */
    function init() {
        if (initialized) return;
        initialized = true;

        // Discover all inputs
        var allInputs = discoverInputs();

        // No inputs found - graceful no-op
        if (allInputs.length === 0) return;

        // Filter out redundant range inputs that are paired with number inputs
        inputElements = [];
        for (var i = 0; i < allInputs.length; i++) {
            if (!isRedundantRange(allInputs[i], allInputs)) {
                inputElements.push(allInputs[i]);
            }
        }

        if (inputElements.length === 0) return;

        // Load state from URL params (if any)
        var didLoad = loadFromUrl();

        if (didLoad) {
            // Sync any paired range sliders
            syncPairedRanges();

            // Fire events so tools recalculate
            fireEventsOnAll();
        }

        // Attach listeners for future changes
        attachListeners();

        // Create the share button
        createShareButton();
    }

    // --- Bootstrap ---

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM already loaded; run on next microtask to let other scripts
        // finish setting up their inputs
        setTimeout(init, 0);
    }

    // --- Public API ---
    window.UrlState = {
        getShareUrl: getShareUrl,
        /** Force re-initialization (e.g. after dynamic inputs are added). */
        refresh: function () {
            initialized = false;
            inputElements = [];
            init();
        }
    };

})();
