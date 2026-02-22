/**
 * Unit Systems Module
 *
 * Provides unit system selection and conversion for engineering tools.
 * Loads unit definitions from Python (pycalcs.units) once at startup,
 * then performs all runtime conversions in pure JavaScript for speed.
 *
 * Usage:
 *   1. Include this script after Pyodide is loaded
 *   2. Call await UnitSystems.init(pyodide) after Pyodide is ready
 *   3. Use UnitSystems.toSI(value, quantity) and UnitSystems.fromSI(value, quantity)
 *   4. Use UnitSystems.getUnitLabel(quantity) for display labels
 */

const UnitSystems = (function() {
    'use strict';

    // Storage key for persisting user's unit system preference
    const STORAGE_KEY = 'transparent-tools-unit-system';

    // Default unit system
    const DEFAULT_SYSTEM = 'MMGS';

    // Available unit systems (populated from Python)
    let systems = null;

    // Current active system
    let currentSystem = DEFAULT_SYSTEM;

    // Initialization state
    let initialized = false;

    /**
     * Initialize the unit systems module by loading definitions from Python.
     * Must be called after Pyodide is ready.
     *
     * @param {Object} pyodide - The Pyodide instance
     * @returns {Promise<void>}
     */
    async function init(pyodide) {
        if (initialized) {
            return;
        }

        try {
            // Load unit systems from Python
            const json = await pyodide.runPythonAsync(`
from pycalcs.units import get_unit_systems_for_js
import json
json.dumps(get_unit_systems_for_js())
            `);
            systems = JSON.parse(json);

            // Load saved preference
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved && systems[saved]) {
                currentSystem = saved;
            }

            initialized = true;
        } catch (error) {
            console.error('Failed to initialize unit systems:', error);
            // Fallback to hardcoded minimal systems if Python fails
            systems = getFallbackSystems();
            initialized = true;
        }
    }

    /**
     * Minimal fallback systems if Python loading fails.
     */
    function getFallbackSystems() {
        return {
            MKS: {
                length: { unit: 'm', toSI: 1, fromSI: 1 },
                mass: { unit: 'kg', toSI: 1, fromSI: 1 },
                force: { unit: 'N', toSI: 1, fromSI: 1 },
                pressure: { unit: 'Pa', toSI: 1, fromSI: 1 },
            },
            MMGS: {
                length: { unit: 'mm', toSI: 0.001, fromSI: 1000 },
                mass: { unit: 'g', toSI: 0.001, fromSI: 1000 },
                force: { unit: 'N', toSI: 1, fromSI: 1 },
                pressure: { unit: 'MPa', toSI: 1e6, fromSI: 1e-6 },
            },
            IPS: {
                length: { unit: 'in', toSI: 0.0254, fromSI: 39.3701 },
                mass: { unit: 'lb', toSI: 0.453592, fromSI: 2.20462 },
                force: { unit: 'lbf', toSI: 4.44822, fromSI: 0.224809 },
                pressure: { unit: 'psi', toSI: 6894.76, fromSI: 0.000145038 },
            },
        };
    }

    /**
     * Get the list of available unit system names.
     * @returns {string[]}
     */
    function getAvailableSystems() {
        return systems ? Object.keys(systems) : [DEFAULT_SYSTEM];
    }

    /**
     * Get the current unit system name.
     * @returns {string}
     */
    function getCurrentSystem() {
        return currentSystem;
    }

    /**
     * Set the current unit system.
     * @param {string} systemName - Name of the system (MKS, MMGS, IPS)
     * @param {boolean} persist - Whether to save to localStorage (default: true)
     */
    function setSystem(systemName, persist = true) {
        if (!systems || !systems[systemName]) {
            console.warn(`Unknown unit system: ${systemName}`);
            return;
        }
        currentSystem = systemName;
        if (persist) {
            localStorage.setItem(STORAGE_KEY, systemName);
        }
    }

    /**
     * Get the unit label for a quantity in the current system.
     * @param {string} quantity - The quantity type (e.g., 'length', 'force')
     * @returns {string} - The unit symbol (e.g., 'mm', 'N')
     */
    function getUnitLabel(quantity) {
        if (!systems || !systems[currentSystem]) {
            return '';
        }
        const q = systems[currentSystem][quantity];
        return q ? q.unit : '';
    }

    /**
     * Convert a value from the current unit system to SI base units.
     * @param {number} value - The value in current system units
     * @param {string} quantity - The quantity type
     * @returns {number} - The value in SI units
     */
    function toSI(value, quantity) {
        if (!systems || !systems[currentSystem]) {
            return value;
        }
        const q = systems[currentSystem][quantity];
        if (!q) {
            return value;
        }

        // Handle affine conversions (temperature)
        if (q.type === 'affine') {
            // Linear interpolation: y = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
            // where x0 = 0, x1 = 1, y0 = toSI.zero, y1 = toSI.one
            const slope = q.toSI.one - q.toSI.zero;
            return q.toSI.zero + value * slope;
        }

        // Linear conversion
        return value * q.toSI;
    }

    /**
     * Convert a value from SI base units to the current unit system.
     * @param {number} value - The value in SI units
     * @param {string} quantity - The quantity type
     * @returns {number} - The value in current system units
     */
    function fromSI(value, quantity) {
        if (!systems || !systems[currentSystem]) {
            return value;
        }
        const q = systems[currentSystem][quantity];
        if (!q) {
            return value;
        }

        // Handle affine conversions (temperature)
        if (q.type === 'affine') {
            // Inverse of toSI
            const slope = q.fromSI.one - q.fromSI.zero;
            return q.fromSI.zero + value * slope;
        }

        // Linear conversion
        return value * q.fromSI;
    }

    /**
     * Update all unit labels in the DOM that have data-quantity attributes.
     * Elements with class 'unit-label' or 'unit' and a data-quantity attribute
     * will have their text content updated to the current system's unit.
     */
    function updateAllUnitLabels() {
        const elements = document.querySelectorAll('[data-quantity]');
        elements.forEach(el => {
            const quantity = el.dataset.quantity;
            // Only update elements that are unit labels (not inputs)
            if (el.classList.contains('unit-label') ||
                el.classList.contains('unit') ||
                el.tagName === 'SPAN' && el.parentElement.classList.contains('input-group')) {
                el.textContent = getUnitLabel(quantity);
            }
        });
    }

    /**
     * Convert all input values in the DOM from one system to another.
     * Inputs with data-quantity attributes will have their values converted.
     * @param {string} fromSystem - The source system name
     * @param {string} toSystem - The target system name
     */
    function convertAllInputValues(fromSystem, toSystem) {
        if (!systems || !systems[fromSystem] || !systems[toSystem]) {
            return;
        }

        const inputs = document.querySelectorAll('input[data-quantity]');
        inputs.forEach(input => {
            const quantity = input.dataset.quantity;
            const value = parseFloat(input.value);

            if (isNaN(value)) {
                return;
            }

            // Get conversion info for both systems
            const fromQ = systems[fromSystem][quantity];
            const toQ = systems[toSystem][quantity];

            if (!fromQ || !toQ) {
                return;
            }

            // Convert: value -> SI -> new system
            let siValue;
            if (fromQ.type === 'affine') {
                const slope = fromQ.toSI.one - fromQ.toSI.zero;
                siValue = fromQ.toSI.zero + value * slope;
            } else {
                siValue = value * fromQ.toSI;
            }

            let newValue;
            if (toQ.type === 'affine') {
                const slope = toQ.fromSI.one - toQ.fromSI.zero;
                newValue = toQ.fromSI.zero + siValue * slope;
            } else {
                newValue = siValue * toQ.fromSI;
            }

            // Update input value, preserving reasonable precision
            input.value = Number(newValue.toPrecision(6));
        });
    }

    /**
     * Create a unit system selector dropdown.
     * @param {string} containerId - ID of the container element
     * @param {Function} onChange - Callback when system changes (receives new system name)
     */
    function createSelector(containerId, onChange) {
        const container = document.getElementById(containerId);
        if (!container) {
            return;
        }

        const select = document.createElement('select');
        select.id = 'unit-system-select';
        select.className = 'unit-system-select';

        getAvailableSystems().forEach(system => {
            const option = document.createElement('option');
            option.value = system;
            option.textContent = system;
            option.selected = system === currentSystem;
            select.appendChild(option);
        });

        select.addEventListener('change', (e) => {
            const oldSystem = currentSystem;
            const newSystem = e.target.value;

            // Convert existing input values
            convertAllInputValues(oldSystem, newSystem);

            // Set new system
            setSystem(newSystem);

            // Update labels
            updateAllUnitLabels();

            // Call user callback
            if (onChange) {
                onChange(newSystem);
            }
        });

        container.appendChild(select);
    }

    /**
     * Check if the module is initialized.
     * @returns {boolean}
     */
    function isInitialized() {
        return initialized;
    }

    /**
     * Get the raw systems data (for debugging or advanced use).
     * @returns {Object|null}
     */
    function getRawSystems() {
        return systems;
    }

    // Public API
    return {
        init,
        isInitialized,
        getAvailableSystems,
        getCurrentSystem,
        setSystem,
        getUnitLabel,
        toSI,
        fromSI,
        updateAllUnitLabels,
        convertAllInputValues,
        createSelector,
        getRawSystems,
        STORAGE_KEY,
        DEFAULT_SYSTEM,
    };
})();

// Export for ES modules if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnitSystems;
}
