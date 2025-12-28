// script.js

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM ELEMENTS ---
    const masterPlayButton = document.getElementById('master-play-button');
    const masterVolumeSlider = document.getElementById('master-volume');
    const addOscillatorButton = document.getElementById('add-oscillator-button');
    const oscillatorsContainer = document.getElementById('oscillators-container');
    const waveformPlotDiv = document.getElementById('waveform-plot');
    const fftPlotDiv = document.getElementById('fft-plot');

    // --- AUDIO CONTEXT SETUP ---
    let audioContext;
    let masterGain;
    let analyser;
    const oscillators = {};

    // --- VISUALIZATION ---
    let animationFrameId;
    const FFT_SIZE = 2048;

    // --- STATE ---
    let isPlaying = false;
    let nextOscId = 0;
    const STORAGE_KEY = 'audio-synthesizer-settings';

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
        if (!waveformPlotDiv.layout || !fftPlotDiv.layout) return; // Plots not ready

        // Determine colors from CSS variables
        const computedStyle = getComputedStyle(document.body);
        const bgColor = computedStyle.getPropertyValue('--bg-card').trim();
        const plotBgColor = computedStyle.getPropertyValue('--secondary-bg').trim()
        const textColor = computedStyle.getPropertyValue('--text-color').trim();
        const gridColor = computedStyle.getPropertyValue('--border-color').trim();

        const update = {
            paper_bgcolor: bgColor,
            plot_bgcolor: plotBgColor,
            'font.color': textColor,
            'xaxis.gridcolor': gridColor,
            'yaxis.gridcolor': gridColor,
        };
        Plotly.relayout(waveformPlotDiv, update);
        Plotly.relayout(fftPlotDiv, update);
    }

    function setSegmentedActive(selector, value, dataAttr) {
        document.querySelectorAll(`.settings-panel ${selector}`).forEach(btn => {
            const isActive = btn.dataset[dataAttr] === value;
            btn.classList.toggle('active', isActive);
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
    // INITIALIZATION
    // =================================================================

    function initAudioContext() {
        if (audioContext) return;
        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            masterGain = audioContext.createGain();
            masterGain.gain.value = masterVolumeSlider.value;
            masterGain.connect(audioContext.destination);

            analyser = audioContext.createAnalyser();
            analyser.fftSize = FFT_SIZE;
            masterGain.connect(analyser);
        } catch (e) {
            alert('Web Audio API is not supported in this browser.');
            console.error(e);
        }
    }

    // =================================================================
    // PLOTTING / VISUALIZATION
    // =================================================================

    function initPlots() {
        const plotTheme = {
            paper_bgcolor: 'var(--primary-bg)',
            plot_bgcolor: 'var(--secondary-bg)',
            font: { color: 'var(--text-color)' },
            margin: { t: 30, r: 30, b: 40, l: 40 },
            xaxis: { gridcolor: 'var(--border-color)', zeroline: false },
            yaxis: { gridcolor: 'var(--border-color)', zeroline: false },
        };

        Plotly.newPlot(waveformPlotDiv, [{ y: [] }], {
            ...plotTheme,
            xaxis: { title: 'Time', showticklabels: false },
            yaxis: { title: 'Amplitude', range: [-1.0, 1.0] }
        }, { responsive: true, displayModeBar: false });

        const sampleRate = audioContext?.sampleRate || 44100;
        const fftInitialX = Array.from({ length: FFT_SIZE / 2 }, (_, i) => i * sampleRate / FFT_SIZE);
        Plotly.newPlot(fftPlotDiv, [{ x: fftInitialX, y: [], type: 'bar' }], {
            ...plotTheme,
            xaxis: { title: 'Frequency (Hz)' },
            yaxis: { title: 'Magnitude', range: [0, 255] }
        }, { responsive: true, displayModeBar: false });
        
        updatePlotThemes();
    }

    function draw() {
        if (!isPlaying || !analyser) return;

        const timeDomainData = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(timeDomainData);
        const waveformValues = Array.from(timeDomainData).map(v => (v / 128.0) - 1.0);

        const frequencyData = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(frequencyData);

        Plotly.restyle(waveformPlotDiv, { y: [waveformValues] });
        Plotly.restyle(fftPlotDiv, { y: [frequencyData] });

        animationFrameId = requestAnimationFrame(draw);
    }

    // =================================================================
    // OSCILLATOR MANAGEMENT
    // =================================================================

    function addOscillator() {
        if (!audioContext) initAudioContext();

        const oscId = nextOscId++;
        const osc = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        const initialFreq = 440;
        const initialGain = 0.5;

        osc.frequency.value = initialFreq;
        osc.type = 'sine';
        gainNode.gain.value = initialGain;

        osc.connect(gainNode);
        gainNode.connect(masterGain);
        osc.start();

        oscillators[oscId] = { node: osc, gain: gainNode, id: oscId };
        createOscillatorUI(oscId, initialFreq, initialGain);
    }

    function removeOscillator(oscId) {
        const osc = oscillators[oscId];
        if (osc) {
            osc.node.stop();
            osc.node.disconnect();
            osc.gain.disconnect();
            delete oscillators[oscId];
            document.getElementById(`osc-${oscId}`).remove();
        }
    }

    function createOscillatorUI(oscId, initialFreq, initialGain) {
        const oscState = oscillators[oscId];

        const oscDiv = document.createElement('div');
        oscDiv.className = 'oscillator';
        oscDiv.id = `osc-${oscId}`;
        
        const minFreq = 20;
        const maxFreq = 2000;

        oscDiv.innerHTML = `
            <div class="osc-header">
                <h4>Tone ${oscId + 1}</h4>
                <button class="btn-remove" data-id="${oscId}">&times; Remove</button>
            </div>
            <div class="control-group">
                <label for="freq-${oscId}">Frequency: <span id="freq-val-${oscId}">${initialFreq}</span> Hz</label>
                <input type="range" id="freq-${oscId}" min="0" max="1" step="0.001" value="${freqToSliderVal(initialFreq, minFreq, maxFreq)}" data-id="${oscId}">
            </div>
            <div class="control-group">
                <label for="gain-${oscId}">Gain: <span id="gain-val-${oscId}">${initialGain.toFixed(2)}</span></label>
                <input type="range" id="gain-${oscId}" min="0" max="1" step="0.01" value="${initialGain}" data-id="${oscId}">
            </div>
            <div class="control-group">
                <label>Waveform</label>
                <div class="waveform-selector" data-id="${oscId}">
                    <button class="active" data-type="sine">Sine</button>
                    <button data-type="square">Square</button>
                    <button data-type="sawtooth">Sawtooth</button>
                    <button data-type="triangle">Triangle</button>
                </div>
            </div>
        `;
        oscillatorsContainer.appendChild(oscDiv);

        const freqSlider = oscDiv.querySelector(`#freq-${oscId}`);
        const gainSlider = oscDiv.querySelector(`#gain-${oscId}`);
        const removeButton = oscDiv.querySelector('.btn-remove');
        const waveformButtons = oscDiv.querySelectorAll('.waveform-selector button');

        freqSlider.addEventListener('input', (e) => {
            const sliderVal = parseFloat(e.target.value);
            const newFreq = sliderValToFreq(sliderVal, minFreq, maxFreq);
            oscState.node.frequency.setTargetAtTime(newFreq, audioContext.currentTime, 0.01);
            oscDiv.querySelector(`#freq-val-${oscId}`).textContent = newFreq.toFixed(0);
        });

        gainSlider.addEventListener('input', (e) => {
            const newGain = parseFloat(e.target.value);
            oscState.gain.gain.setTargetAtTime(newGain, audioContext.currentTime, 0.01);
            oscDiv.querySelector(`#gain-val-${oscId}`).textContent = newGain.toFixed(2);
        });
        
        removeButton.addEventListener('click', () => removeOscillator(oscId));

        waveformButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                waveformButtons.forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
                oscState.node.type = e.target.dataset.type;
            });
        });
    }

    // --- Frequency Slider Logarithmic Conversion ---
    function sliderValToFreq(val, min, max) {
        const minLog = Math.log(min);
        const maxLog = Math.log(max);
        return Math.exp(minLog + (maxLog - minLog) * val);
    }

    function freqToSliderVal(freq, min, max) {
        const minLog = Math.log(min);
        const maxLog = Math.log(max);
        return (Math.log(freq) - minLog) / (maxLog - minLog);
    }

    // =================================================================
    // EVENT LISTENERS
    // =================================================================

    masterPlayButton.addEventListener('click', () => {
        if (!audioContext) initAudioContext();

        isPlaying = !isPlaying;
        if (isPlaying) {
            audioContext.resume().then(() => {
                masterPlayButton.textContent = 'Stop';
                masterPlayButton.classList.add('playing');
                draw();
            });
        } else {
            audioContext.suspend().then(() => {
                masterPlayButton.textContent = 'Play';
                masterPlayButton.classList.remove('playing');
                cancelAnimationFrame(animationFrameId);
            });
        }
    });

    masterVolumeSlider.addEventListener('input', (e) => {
        if (masterGain) {
            masterGain.gain.setTargetAtTime(parseFloat(e.target.value), audioContext.currentTime, 0.01);
        }
    });

    addOscillatorButton.addEventListener('click', addOscillator);

    // =================================================================
    // STARTUP
    // =================================================================
    
    loadSettings();
    initAudioContext();
    initPlots();
    applySettings();
    bindSettingsControls();
    addOscillator(); // Start with one oscillator by default
});
