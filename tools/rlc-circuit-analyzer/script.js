// RLC Circuit Analyzer - script.js

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM ELEMENTS ---
    const tabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');

    const rSlider = document.getElementById('resistance');
    const lSlider = document.getElementById('inductance');
    const cSlider = document.getElementById('capacitance');

    const rValSpan = document.getElementById('r-val');
    const lValSpan = document.getElementById('l-val');
    const cValSpan = document.getElementById('c-val');
    
    const resonantFreqVal = document.getElementById('resonant-freq-val');
    const qFactorVal = document.getElementById('q-factor-val');

    const impedancePlotDiv = document.getElementById('impedance-plot');
    const phasePlotDiv = document.getElementById('phase-plot');

    // --- STATE ---
    let R = 10;
    let L = 100e-6;
    let C = 100e-9;
    const STORAGE_KEY = 'rlc-analyzer-settings';

    // --- SETTINGS ---
    const defaultSettings = { theme: 'system' };
    let settings = { ...defaultSettings };

    // =================================================================
    // SETTINGS MANAGEMENT
    // =================================================================

    function saveSettings() {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    }

    function loadSettings() {
        const stored = localStorage.getItem(STORAGE_KEY);
        settings = stored ? { ...defaultSettings, ...JSON.parse(stored) } : { ...defaultSettings };
    }

    function applySettings() {
        document.body.dataset.theme = settings.theme;
        setSegmentedActive('[data-theme]', settings.theme, 'theme');
        updatePlotThemes();
    }
    
    function updatePlotThemes() {
        if (!impedancePlotDiv.layout || !phasePlotDiv.layout) return;

        const computedStyle = getComputedStyle(document.body);
        const fontColor = computedStyle.getPropertyValue('--text-color').trim();
        const gridColor = computedStyle.getPropertyValue('--border-color').trim();
        const paperBgColor = 'transparent'; 
        const plotBgColor = 'transparent';

        const update = {
            'paper_bgcolor': paperBgColor,
            'plot_bgcolor': plotBgColor,
            'font.color': fontColor,
            'xaxis.gridcolor': gridColor,
            'xaxis.linecolor': gridColor,
            'yaxis.gridcolor': gridColor,
            'yaxis.linecolor': gridColor,
        };
        Plotly.relayout(impedancePlotDiv, update);
        Plotly.relayout(phasePlotDiv, update);
    }

    function setSegmentedActive(selector, value, dataAttr) {
        document.querySelectorAll(`.settings-panel ${selector}`).forEach(btn => {
            btn.classList.toggle('active', btn.dataset[dataAttr] === value);
        });
    }

    function handleSettingChange(key, value) {
        settings[key] = value;
        saveSettings();
        applySettings();
    }

    function toggleSettingsPanel(open) {
        const panel = document.getElementById('settings-panel');
        const overlay = document.getElementById('settings-overlay');
        const isOpen = open ?? !panel.classList.contains('open');
        panel.classList.toggle('open', isOpen);
        overlay.classList.toggle('open', isOpen);
    }

    function bindSettingsControls() {
        document.querySelectorAll('.settings-panel [data-theme]').forEach(btn => {
            btn.addEventListener('click', () => handleSettingChange('theme', btn.dataset.theme));
        });
        document.getElementById('settings-reset').addEventListener('click', () => {
            settings = { ...defaultSettings };
            saveSettings();
            applySettings();
        });
        document.getElementById('settings-button').addEventListener('click', () => toggleSettingsPanel(true));
        document.getElementById('settings-close').addEventListener('click', () => toggleSettingsPanel(false));
        document.getElementById('settings-overlay').addEventListener('click', () => toggleSettingsPanel(false));
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') toggleSettingsPanel(false);
        });
    }

    // =================================================================
    // TAB MANAGEMENT
    // =================================================================
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            tabContents.forEach(content => {
                content.classList.toggle('active', content.id === target);
            });
            
            if (target === 'theory') {
                if (window.MathJax && window.MathJax.typesetPromise) {
                    window.MathJax.typesetPromise();
                }
            } else if (target === 'analysis') {
                window.dispatchEvent(new Event('resize'));
            }
        });
    });

    // =================================================================
    // PLOTTING & CALCULATIONS
    // =================================================================
    function initUI() {
        rSlider.value = R;
        rValSpan.textContent = R;
        lSlider.value = L * 1e6;
        lValSpan.textContent = lSlider.value;
        cSlider.value = C * 1e9;
        cValSpan.textContent = cSlider.value;

        rSlider.addEventListener('input', () => {
            R = parseFloat(rSlider.value);
            rValSpan.textContent = R;
            updateAnalysis();
        });
        lSlider.addEventListener('input', () => {
            L = parseFloat(lSlider.value) * 1e-6;
            lValSpan.textContent = lSlider.value;
            updateAnalysis();
        });
        cSlider.addEventListener('input', () => {
            C = parseFloat(cSlider.value) * 1e-9;
            cValSpan.textContent = cSlider.value;
            updateAnalysis();
        });

        const plotLayout = {
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { color: 'var(--text-color)' },
            margin: { t: 40, r: 30, b: 50, l: 60 },
            xaxis: { 
                type: 'log',
                title: 'Frequency (Hz)',
                gridcolor: 'var(--border-color)', 
                zeroline: false 
            },
            yaxis: {
                gridcolor: 'var(--border-color)',
                zeroline: false
            },
        };

        Plotly.newPlot(impedancePlotDiv, [{}], {
            ...plotLayout,
            yaxis: { ...plotLayout.yaxis, title: 'Impedance (Z) [Ω]' }
        }, { responsive: true, displayModeBar: false });

        Plotly.newPlot(phasePlotDiv, [{}], {
            ...plotLayout,
            yaxis: { ...plotLayout.yaxis, title: 'Phase Angle (φ) [deg]' }
        }, { responsive: true, displayModeBar: false });
    }

    function updateAnalysis() {
        const nPoints = 400;
        const freqMin = 1e3;
        const freqMax = 10e6;
        const logMin = Math.log10(freqMin);
        const logMax = Math.log10(freqMax);
        const logStep = (logMax - logMin) / (nPoints - 1);
        
        const freqs = Array.from({ length: nPoints }, (_, i) => Math.pow(10, logMin + i * logStep));

        const impedance = [];
        const phase = [];
        const twoPi = 2 * Math.PI;

        for (const f of freqs) {
            const xl = twoPi * f * L;
            const xc = 1 / (twoPi * f * C);
            const z = Math.sqrt(R * R + Math.pow(xl - xc, 2));
            impedance.push(z);
            const phi = Math.atan2(xl - xc, R) * (180 / Math.PI);
            phase.push(phi);
        }

        Plotly.react(impedancePlotDiv, [{ x: freqs, y: impedance, type: 'scatter', line: { color: 'var(--accent-color)'} }], impedancePlotDiv.layout);
        Plotly.react(phasePlotDiv, [{ x: freqs, y: phase, type: 'scatter', line: { color: 'var(--accent-color)'} }], phasePlotDiv.layout);

        const f0 = 1 / (twoPi * Math.sqrt(L * C));
        const Q = (1 / R) * Math.sqrt(L / C);

        resonantFreqVal.textContent = formatHertz(f0);
        qFactorVal.textContent = Q.toFixed(2);
    }
    
    function formatHertz(hz) {
        if (hz < 1000) return `${hz.toFixed(2)} Hz`;
        if (hz < 1e6) return `${(hz / 1000).toFixed(2)} kHz`;
        return `${(hz / 1e6).toFixed(2)} MHz`;
    }

    // =================================================================
    // STARTUP
    // =================================================================
    function main() {
        loadSettings();
        initUI();
        applySettings();
        bindSettingsControls();
        updateAnalysis();
    }

    main();
});
