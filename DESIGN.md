# UI Design Guidance

This document captures the preferred UI direction for Engineering Tools calculators. The current
target is a Polestar-inspired minimal UI: clean geometry, restrained color, and high legibility.

**Core Principle:** Every UI decision should serve Progressive Simplicity (fast time-to-value) and Progressive Disclosure (complexity on demand). See `AGENTS.md` for full philosophy.

---

## Visual Language

- Prioritize clean, monochrome surfaces with a single dark accent for CTAs.
- Keep backgrounds solid (no gradients) and use whitespace for separation.
- Reserve semantic colors for status indicators only (success/warning/danger).
- Use hairline borders and subtle shadows; avoid heavy depth effects.

### CSS Variables (Required)

All tools must define these CSS variables in their `:root` block:

```css
:root {
    /* Core palette */
    --primary-color: #0b0d12;
    --primary-light: #f4f5f7;
    --secondary-color: #4b5563;
    --accent-color: #111827;

    /* Semantic colors (for status only) */
    --success-color: #0f766e;
    --warning-color: #b45309;
    --danger-color: #b91c1c;

    /* Text hierarchy */
    --text-color: #111827;
    --text-light: #6b7280;

    /* Surfaces */
    --border-color: #e5e7eb;
    --bg-color: #f8f9fb;
    --bg-card: #ffffff;

    /* Elevation */
    --shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    --shadow-lg: 0 6px 18px rgba(15, 23, 42, 0.08);

    /* Shape */
    --border-radius: 8px;

    /* Typography */
    --font-sans: 'Helvetica Neue', 'Avenir Next', 'Univers', 'Helvetica', system-ui, sans-serif;
    --font-mono: 'SF Mono', 'Menlo', 'Monaco', monospace;
}
```

---

## Typography

- Use a Swiss-style sans serif for body and headings (Helvetica Neue / Avenir Next / Univers).
- Use a clean monospace for numeric readouts (SF Mono / Menlo / Monaco).
- Keep headings crisp with moderate weight and minimal letter spacing.

### Heading Scale

```css
h1 { font-size: 2.25rem; letter-spacing: -0.02em; font-weight: 600; }
h2 { font-size: 1.375rem; font-weight: 600; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; }
h3 { font-size: 1.1rem; font-weight: 600; color: var(--secondary-color); }
h4 { font-size: 0.95rem; font-weight: 600; color: var(--text-color); }
```

---

## Layout & Structure

- Add a centered hero header (`.tool-header`) with the tool name and a concise subtitle.
- Widen the canvas: ~92% width with a 1400px max.
- Use a two-column layout where outputs have slightly more width than inputs.
- Keep card padding generous (24-28px) to reduce visual density.

### Container

```css
.container {
    width: 92%;
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px 0;
}
```

### Two-Column Tool Layout

```css
.tool-layout {
    display: grid;
    grid-template-columns: minmax(360px, 0.9fr) minmax(480px, 1.1fr);
    gap: 28px;
    align-items: start;
}

@media (max-width: 1000px) {
    .tool-layout { grid-template-columns: 1fr; }
}
```

---

## Loading Overlay

**Required for all tools.** Never show a broken or half-loaded UI during Pyodide initialization.

### HTML Structure

```html
<div class="loading-overlay" id="loading-overlay">
    <div class="spinner"></div>
    <div class="loading-text" id="loading-text">Loading Pyodide...</div>
</div>
```

### CSS

```css
.loading-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(255, 255, 255, 0.95);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.loading-overlay.hidden { display: none; }

.spinner {
    width: 50px;
    height: 50px;
    border: 4px solid var(--border-color);
    border-top-color: var(--accent-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-text {
    margin-top: 16px;
    font-weight: 600;
    color: var(--text-color);
}
```

### JavaScript Pattern

```javascript
const loadingText = document.getElementById('loading-text');
loadingText.textContent = 'Loading Pyodide...';
let pyodide = await loadPyodide();

loadingText.textContent = 'Loading Python modules...';
await pyodide.runPythonAsync(`...`);

document.getElementById('loading-overlay').classList.add('hidden');
```

---

## Inputs

- Organize large input sets into tabbed sections (Fastener / Joint / Loading style).
- Pair related inputs in a two-column row (`.input-row`) when it reduces scan time.
- Use 1px input borders with a subtle focus ring to keep the UI clean.
- Remove native select arrows/number spinners if they collide with tooltip icons.
- Tooltips should be larger, wrapped, and shadowed for readability.

### Input Group

```css
.input-group {
    margin-bottom: 1.1rem;
    position: relative;
}

.input-group label {
    display: block;
    font-weight: 500;
    margin-bottom: 6px;
    font-size: 0.875rem;
    color: var(--text-color);
}

.input-group input[type="number"],
.input-group input[type="text"],
.input-group select {
    width: 100%;
    padding: 11px 14px;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    font-size: 0.95rem;
    font-family: var(--font-sans);
    transition: border-color 0.15s ease;
    background: var(--bg-card);
}

.input-group input:focus,
.input-group select:focus {
    outline: none;
    border-color: var(--text-color);
}
```

### Two-Column Input Row

```css
.input-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

@media (max-width: 600px) {
    .input-row { grid-template-columns: 1fr; }
}
```

### Expert Mode Toggle

For progressive simplicity, hide infrequently-used inputs by default and show them via an expert mode toggle.

```css
.advanced-section {
    display: none;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px dashed var(--border-color);
}

/* Show advanced section when expert mode is on */
body.expert-mode .advanced-section { display: block; }
```

### Slider with Live Value Display

```css
.slider-group {
    margin: 0 0 1.5rem 0;
    padding: 16px;
    background: var(--primary-light);
    border-radius: var(--border-radius);
}

.slider-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-weight: 500;
    font-size: 0.875rem;
}

.slider-value {
    font-family: var(--font-mono);
    font-weight: 600;
}

.slider-group input[type="range"] {
    width: 100%;
    height: 6px;
    -webkit-appearance: none;
    background: var(--border-color);
    border-radius: 3px;
    outline: none;
}

.slider-group input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    background: var(--accent-color);
    border-radius: 50%;
    cursor: pointer;
}

.slider-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--text-light);
    margin-top: 4px;
}
```

---

## Outputs

- Present key results as a grid of cards with large numeric values.
- Highlight the most important values with a subtle background and accent border.
- Include a second grid for secondary metrics.
- Add indicator gauges for safety, capacity, or severity metrics with clear thresholds.
- Use a status banner to summarize acceptability and show recommended adjustments.

### Result Cards Grid

```css
.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.result-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    padding: 18px;
    text-align: center;
}

.result-card.highlight {
    background: var(--primary-light);
    border-left: 3px solid var(--accent-color);
}

.result-card .label {
    font-size: 0.85rem;
    color: var(--text-light);
    margin-bottom: 6px;
    font-weight: 500;
}

.result-card .value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--primary-color);
    font-family: var(--font-mono);
}

.result-card .unit {
    font-size: 0.85rem;
    color: var(--text-light);
    margin-left: 4px;
}

.result-card .range {
    font-size: 0.8rem;
    color: var(--text-light);
    margin-top: 6px;
}
```

### Clickable Result Items (for derivation panels)

```css
.result-item {
    background: var(--bg-color);
    padding: 16px;
    border-radius: var(--border-radius);
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    border: 2px solid transparent;
}

.result-item:hover { border-color: var(--border-color); }
.result-item.expanded {
    border-color: var(--accent-color);
    background: var(--primary-light);
}

.result-item .label {
    font-size: 0.8rem;
    color: var(--text-light);
    margin-bottom: 4px;
}

.result-item .value {
    font-size: 1.25rem;
    font-weight: 600;
    font-family: var(--font-mono);
}

.result-item .icon {
    font-size: 0.7rem;
    margin-left: 4px;
    opacity: 0.5;
}
```

---

## Derivation Panels

Click a result to reveal step-by-step derivation. Supports progressive disclosure.

```css
.derivation-panel {
    display: none;
    background: var(--primary-light);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    padding: 20px;
    margin-bottom: 20px;
}

.derivation-panel.visible {
    display: block;
    animation: fadeIn 0.3s ease;
}

.derivation-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.derivation-title { font-weight: 600; font-size: 1rem; }

.derivation-close {
    background: none;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    color: var(--text-light);
}

.derivation-close:hover { color: var(--text-color); }

.derivation-step {
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-color);
}

.derivation-step:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.derivation-step .step-title {
    font-weight: 500;
    margin-bottom: 8px;
    color: var(--text-color);
}

.derivation-step .equation {
    background: white;
    padding: 12px;
    border-radius: 6px;
    font-size: 0.95rem;
    overflow-x: auto;
}

.derivation-step .inputs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
}

.derivation-step .input-tag {
    background: white;
    border: 1px solid var(--border-color);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-family: var(--font-mono);
}

.derivation-step .result-box {
    background: var(--accent-color);
    color: white;
    padding: 12px 16px;
    border-radius: 6px;
    margin-top: 12px;
    font-family: var(--font-mono);
    font-size: 1rem;
}

/* Color variants for result boxes */
.derivation-step .result-box.good { background: var(--success-color); }
.derivation-step .result-box.marginal { background: var(--warning-color); color: var(--text-color); }
.derivation-step .result-box.bad { background: var(--danger-color); }
```

---

## Safety Factor Gauges

Visual representation of safety margins with semantic coloring.

```css
.safety-section { margin-top: 24px; }
.safety-section h4 { margin-bottom: 16px; color: var(--secondary-color); }

.safety-gauge {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 12px;
    padding: 12px 16px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
}

.gauge-label {
    min-width: 140px;
    font-weight: 600;
    font-size: 0.9rem;
}

.gauge-bar-container {
    flex: 1;
    height: 8px;
    background: var(--border-color);
    border-radius: 4px;
    position: relative;
    overflow: visible;
}

.gauge-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.4s ease;
}

/* Semantic colors */
.gauge-bar.success { background: var(--success-color); }
.gauge-bar.warning { background: var(--warning-color); }
.gauge-bar.danger { background: var(--danger-color); }

.gauge-value {
    min-width: 60px;
    text-align: right;
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 0.9rem;
}

.gauge-value.success { color: var(--success-color); }
.gauge-value.warning { color: var(--warning-color); }
.gauge-value.danger { color: var(--danger-color); }

/* Threshold marker */
.gauge-threshold {
    position: absolute;
    width: 2px;
    height: 16px;
    background: var(--text-color);
    top: -4px;
}
```

### Gauge Color Logic (JavaScript)

```javascript
function getGaugeClass(safetyFactor) {
    if (safetyFactor >= 1.5) return 'success';
    if (safetyFactor >= 1.0) return 'warning';
    return 'danger';
}

function getGaugeWidth(safetyFactor, maxSF = 3.0) {
    return Math.min(100, (safetyFactor / maxSF) * 100) + '%';
}
```

---

## Status Banner

Summarize overall assessment with actionable recommendations.

```css
.status-banner {
    padding: 18px 24px;
    border-radius: var(--border-radius);
    margin-top: 24px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
}

.status-banner .icon { font-size: 1.25rem; }
.status-banner .content h4 { margin-bottom: 4px; }
.status-banner .content p { margin-bottom: 0; font-size: 0.9rem; }

/* Acceptable (green) */
.status-banner.acceptable {
    background: #ecfdf5;
    border: 1px solid var(--success-color);
}
.status-banner.acceptable h4 { color: var(--success-color); }

/* Marginal (amber) */
.status-banner.marginal {
    background: #fffbeb;
    border: 1px solid var(--warning-color);
}
.status-banner.marginal h4 { color: var(--warning-color); }

/* Unacceptable (red) */
.status-banner.unacceptable {
    background: #fef2f2;
    border: 1px solid var(--danger-color);
}
.status-banner.unacceptable h4 { color: var(--danger-color); }

/* Recommendations list */
.recommendations {
    margin-top: 8px;
    padding-left: 20px;
}
.recommendations li {
    font-size: 0.85rem;
    margin-bottom: 4px;
}
```

---

## Charts & Visualizations

- Use carded chart containers with titles and consistent spacing.
- When plotting, include legends, axis labels, and clear marker annotations.
- Every chart needs an explanation of what it shows.

### Chart Container

```css
.chart-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    padding: 18px;
    margin-bottom: 20px;
    overflow-x: auto;
}

.chart-container h4 {
    margin-bottom: 12px;
    font-size: 0.95rem;
    font-weight: 600;
}

.chart-plot {
    width: 100%;
    min-height: 320px;
    min-width: 400px;
}

.chart-explanation {
    margin-top: 12px;
    font-size: 0.85rem;
    color: var(--text-light);
    line-height: 1.5;
    padding: 10px;
    background: var(--primary-light);
    border-radius: 6px;
}

.chart-explanation strong { color: var(--text-color); }

.charts-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
}
```

### Chart Explanation Pattern

Every chart should have an explanation following this structure:

```html
<div class="chart-container">
    <h4>Chart Title</h4>
    <div id="chart-plot" class="chart-plot"></div>
    <div class="chart-explanation">
        <strong>What this shows:</strong> Brief description of the chart content.
        <strong>Key insight:</strong> The main takeaway the user should understand.
    </div>
</div>
```

---

## Callout Boxes

Use callouts to highlight important information in Background tabs.

```css
/* Info callout (blue) */
.callout-info {
    background: #dbeafe;
    border-left: 4px solid var(--accent-color);
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 8px 8px 0;
}
.callout-info strong { color: var(--accent-color); }

/* Warning callout (amber) */
.callout-warning {
    background: #fef3c7;
    border-left: 4px solid var(--warning-color);
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 8px 8px 0;
}
.callout-warning strong { color: var(--warning-color); }

/* Danger callout (red) */
.callout-danger {
    background: #fef2f2;
    border-left: 4px solid var(--danger-color);
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 8px 8px 0;
}
.callout-danger strong { color: var(--danger-color); }

/* Success callout (green) */
.callout-success {
    background: #d1fae5;
    border-left: 4px solid var(--success-color);
    padding: 12px 16px;
    margin: 16px 0;
    border-radius: 0 8px 8px 0;
}
.callout-success strong { color: var(--success-color); }
```

---

## Background Tab Structure

The Background tab should be a complete educational resource.

### Table of Contents Card

```css
.toc-card {
    background: var(--primary-light);
    padding: 16px 20px;
    border-radius: 8px;
    margin-bottom: 24px;
}

.toc-card strong { color: var(--primary-color); }

.toc-card ol {
    margin: 10px 0 0 20px;
    color: var(--text-light);
    font-size: 0.9rem;
}

.toc-card a { color: var(--accent-color); }
```

### Section Styling

```css
.bg-section {
    margin-bottom: 32px;
}

.bg-section h3 {
    border-bottom: 2px solid var(--accent-color);
    padding-bottom: 8px;
    margin-bottom: 16px;
}

.bg-section h4 {
    margin-top: 20px;
    color: var(--secondary-color);
}
```

### Equation Cards

```css
.equation-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    padding: 16px 20px;
    margin: 16px 0;
}

.equation-card strong {
    display: block;
    margin-bottom: 8px;
    color: var(--secondary-color);
    font-size: 0.9rem;
}

.equation-card .equation-expression {
    display: block;
    margin-bottom: 10px;
    font-size: 1.05rem;
}

.equation-card ul {
    list-style: none;
    padding-left: 0;
    display: grid;
    gap: 6px;
    font-size: 0.85rem;
    color: var(--text-light);
}
```

---

## Motion & Feedback

- Apply light fade transitions on tab content; keep hover effects restrained.
- Show a full-screen loading overlay while Pyodide initializes to avoid blank states.

```css
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

.tab-content {
    display: none;
    animation: fadeIn 0.4s ease;
}

/* Smooth transitions for interactive elements */
button, .result-item, .input-group input, .input-group select {
    transition: all 0.15s ease;
}
```

---

## Responsive Design

### Breakpoints

```css
/* Tablet */
@media (max-width: 1000px) {
    .tool-layout { grid-template-columns: 1fr; }
    .charts-grid { grid-template-columns: 1fr; }
    .input-row { grid-template-columns: 1fr; }
}

/* Mobile */
@media (max-width: 600px) {
    .input-tabs { flex-direction: column; }
    .results-grid { grid-template-columns: 1fr; }
    .safety-gauge { flex-direction: column; align-items: flex-start; }
    .gauge-bar-container { width: 100%; }
}
```

---

## Analytics

All tool pages must include Google Analytics 4 for traffic tracking.

### Required Snippet

Add this in the `<head>` immediately after the `<meta name="viewport">` tag:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-YG3SBRRZFZ"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-YG3SBRRZFZ');
</script>
```

---

## Implementation Notes

- Maintain tool-local CSS blocks for now; avoid inline styles unless absolutely necessary.
- Keep all UI enhancements within the existing HTML template structure for consistency.
- When adopting these patterns, preserve tool logic and docstring-driven tooltips.
- Reference `tools/example_tool_advanced/` for a complete implementation of all patterns.
- Reference `tools/bolt-torque/` for a production example of complex tool patterns.
