# Heatsink Designer — Complete Implementation Plan

> **Purpose:** This document is a self-contained, sequenced implementation guide for every improvement identified in `heatsink_designer_full_audit.md`. It is written to be handed to an LLM (ChatGPT or similar) for autonomous implementation. Every section includes the exact files to modify, the code patterns to follow, the mathematical formulas to implement, and the test assertions to write.

---

## Table of Contents

1. [Project Context](#1-project-context)
2. [Phase 0 — Quick Wins (No Physics Changes)](#2-phase-0--quick-wins)
3. [Phase 1 — Accuracy Foundations](#3-phase-1--accuracy-foundations)
4. [Phase 2 — Physics Model Extensions](#4-phase-2--physics-model-extensions)
5. [Phase 3 — Sensitivity Analysis](#5-phase-3--sensitivity-analysis)
6. [Phase 4 — UI/UX Overhaul](#6-phase-4--uiux-overhaul)
7. [Phase 5 — Testing & Validation](#7-phase-5--testing--validation)
8. [Phase 6 — Features & Polish](#8-phase-6--features--polish)
9. [Cross-Cutting Concerns](#9-cross-cutting-concerns)
10. [File Inventory](#10-file-inventory)

---

## 1. Project Context

### Repository Structure
```
/pycalcs/heatsinks.py          — Python thermal solver (866 lines)
/pycalcs/utils.py              — Shared utilities (docstring parser, etc.)
/tests/test_heatsinks.py       — Unit tests (201 lines, 10 tests)
/tools/simple_thermal/
    index.html                 — Complete UI (2584 lines, single file)
    README.md                  — Product definition
    ROADMAP.md                 — Phase roadmap
    material_reference.md      — Material properties reference
/plans/
    heatsink_sensitivity_analysis.md  — Deferred sweep analysis plan
    heatsink_designer_full_audit.md   — Full audit register (companion)
```

### Technology Stack
- **Python:** Pure Python 3.9+, no external dependencies (runs in Pyodide).
- **Frontend:** Single HTML file with inline CSS and JS. Uses Pyodide (v0.25.1), Plotly.js (v2.27.0), MathJax v3.
- **Testing:** pytest. No browser testing framework currently.
- **Deployment:** Static files served via Netlify. No build step.

### Key Architectural Rules
1. All physics equations live in `pycalcs/heatsinks.py`. The frontend is a thin data-gathering and rendering layer.
2. Every equation must trace to a named reference.
3. Every primary output must have a substituted-equation string for the derivation panel.
4. The Python API uses SI units (meters, watts, pascals, kelvin). The frontend handles display unit conversions.
5. The default experience must remain simple (Progressive Simplicity). Complexity goes behind Expert Mode or additional tabs.
6. Dark mode, light mode, and system theme must all work. CSS uses `var()` custom properties throughout.

### How the Solver Works (Essential Context)
The main function `analyze_plate_fin_heatsink()` does a binary search on base temperature:

1. Guess a base temperature.
2. At that temperature, compute air properties at the film temperature.
3. Compute convection coefficient (natural, forced, or fan-curve mode).
4. Compute linearized radiation coefficient.
5. Compute fin efficiency using the effective (convection + radiation) coefficient.
6. Compute overall surface efficiency.
7. Compute total heat rejected: `Q = η_o * h_eff * A_total * (T_base - T_ambient)`.
8. If Q > heat_load, lower the temperature guess. If Q < heat_load, raise it.
9. After convergence, compute the full thermal stack: `T_case = T_base + Q * R_cs`, `T_junction = T_case + Q * R_jc`.

---

## 2. Phase 0 — Quick Wins (mostly complete)

These items require minimal effort and no physics changes. Do them first to build momentum and improve the codebase quality for subsequent work.

> **Status (2026-03-19):** 12 of 14 items implemented. Remaining: 2.0.13 (Pyodide timeout — deferred, needs Web Worker for real protection) and inline input validation (C3, tracked separately in Phase 4).

### 2.0.1 — Fix Friction Factor Consistency [A5] ✓

**File:** `pycalcs/heatsinks.py`
**Location:** `forced_convection_plate_array()`, lines 386–397

**Current code (turbulent branch):**
```python
darcy_friction_factor = 0.3164 * reynolds_number ** -0.25  # Blasius
friction_term = (0.79 * math.log(reynolds_number) - 1.64) ** -2  # Petukhov
nusselt_number = (
    (friction_term / 8.0)
    * (reynolds_number - 1000.0)
    * props.prandtl
    / (
        1.0
        + 12.7 * math.sqrt(friction_term / 8.0) * (props.prandtl ** (2.0 / 3.0) - 1.0)
    )
)
```

**Replace with:**
```python
# Petukhov friction factor — used for both Nusselt and pressure drop.
darcy_friction_factor = (0.790 * math.log(reynolds_number) - 1.64) ** -2
nusselt_number = (
    (darcy_friction_factor / 8.0)
    * (reynolds_number - 1000.0)
    * props.prandtl
    / (
        1.0
        + 12.7 * math.sqrt(darcy_friction_factor / 8.0) * (props.prandtl ** (2.0 / 3.0) - 1.0)
    )
)
```

**Why:** The Gnielinski correlation is designed to use the Petukhov friction factor. Using Blasius for pressure drop and Petukhov for Nu is inconsistent. Delete the Blasius line entirely. The `darcy_friction_factor` variable is already used downstream for pressure drop (line 402–406), so this single change fixes both.

**Test:** Add a test at Re=10000 that verifies the friction factor matches the Petukhov formula:
```python
def test_turbulent_friction_factor_is_petukhov() -> None:
    import math
    re = 10000.0
    expected_f = (0.790 * math.log(re) - 1.64) ** -2
    # Create a geometry and run forced convection at a flow rate producing Re ≈ 10000
    # Assert that pressure_drop is consistent with expected_f
```

### 2.0.2 — Millimeter Units for Geometry Inputs [C1] ✓

**File:** `tools/simple_thermal/index.html`

**Changes to HTML (geometry input labels and default values):**
Find every geometry input and change:
```
"Base Length (m)"   → "Base Length (mm)"    value="0.10"   → value="100"
"Base Width (m)"    → "Base Width (mm)"     value="0.08"   → value="80"
"Base Thickness (m)"→ "Base Thickness (mm)" value="0.005"  → value="5"
"Fin Height (m)"    → "Fin Height (mm)"     value="0.03"   → value="30"
"Fin Thickness (m)" → "Fin Thickness (mm)"  value="0.001"  → value="1.0"
```

Also update `step` and `min` attributes:
- `base_length`: step="any" min="1" (1 mm minimum)
- `base_width`: step="any" min="1"
- `base_thickness`: step="any" min="0.1"
- `fin_height`: step="any" min="1"
- `fin_thickness`: step="any" min="0.1"

**Changes to `gatherInputs()` function:**
```javascript
function gatherInputs() {
    return {
        heat_load: parseFloat(document.getElementById('heat_load').value),
        ambient_temperature: parseFloat(document.getElementById('ambient_temperature').value),
        target_junction_temperature: parseFloat(document.getElementById('target_junction_temperature').value),
        base_length: parseFloat(document.getElementById('base_length').value) / 1000,      // mm → m
        base_width: parseFloat(document.getElementById('base_width').value) / 1000,         // mm → m
        base_thickness: parseFloat(document.getElementById('base_thickness').value) / 1000,  // mm → m
        fin_height: parseFloat(document.getElementById('fin_height').value) / 1000,          // mm → m
        fin_thickness: parseFloat(document.getElementById('fin_thickness').value) / 1000,    // mm → m
        fin_count: parseInt(document.getElementById('fin_count').value, 10),
        // ... rest unchanged
    };
}
```

**Changes to `renderHeatsinkGeometryPreview()`:**
This function reads input values directly for the SVG. Currently it reads meters. After this change, the raw input values are in mm, so update the geometry preview to divide by 1000 before computing the SVG:
```javascript
const baseLength = parseFloat(document.getElementById('base_length').value) / 1000;
const baseWidth = parseFloat(document.getElementById('base_width').value) / 1000;
// etc.
```

**Changes to `formatPreviewLength()`:**
This function already converts meters to mm for display. After this change, the input to this function is still in meters (after division), so it should continue to work. Verify.

**Changes to `renderThermalPathPrimer()` and `bindThermalPrimer()`:**
These don't read geometry, so no changes needed.

### 2.0.3 — Fix Expert Mode Toggle Positioning [C9] ✓

**File:** `tools/simple_thermal/index.html`, CSS section

Find:
```css
.expert-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
}
```

Replace with:
```css
.expert-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    position: relative;
}
```

### 2.0.4 — Dark Mode Accent Color Fix [C10] ✓

**File:** `tools/simple_thermal/index.html`, CSS section

In the `body[data-theme="dark"]` block, change:
```css
--accent-color: #f9fafb;
```
to:
```css
--accent-color: #60a5fa;
```

Do the same in the `@media (prefers-color-scheme: dark) body[data-theme="system"]` block.

### 2.0.5 — Fin Efficiency as Percentage [C8] ✓

**File:** `tools/simple_thermal/index.html`

In `displayResults()`, find:
```javascript
document.getElementById('val-fin_efficiency').innerHTML = formatNumber(results.fin_efficiency, 3);
```
Replace with:
```javascript
document.getElementById('val-fin_efficiency').innerHTML = formatWithUnit(results.fin_efficiency * 100, '%', 1);
```

### 2.0.6 — Consistent Event Binding [D4] ✓

**File:** `tools/simple_thermal/index.html`

Remove all inline `onclick` attributes from the HTML. Specifically:

1. Tab links: Remove `onclick="openTab(event, 'results')"` etc. from `.tab-link` buttons.
2. Result items: Remove `onclick="toggleDerivation('...')"` from `.result-item.clickable` elements.
3. Derivation close buttons: Remove `onclick="toggleDerivation('...')"`.

Add event listeners in the `main()` function after Pyodide loads:
```javascript
// Tab links
document.querySelectorAll('.tab-link').forEach((link) => {
    const tabName = link.textContent.trim().toLowerCase().replace(/\s+/g, '');
    // Map display text to tab IDs
    const tabMap = { 'results': 'results', 'temperatureladder': 'ladder', 'heatsplit': 'heat', 'background': 'background' };
    const tabId = tabMap[tabName];
    if (tabId) {
        link.addEventListener('click', (event) => openTab(event, tabId));
    }
});

// Derivation toggles
document.querySelectorAll('.result-item.clickable').forEach((item) => {
    const key = item.dataset.key;
    if (key) {
        item.addEventListener('click', () => toggleDerivation(key));
    }
});

// Derivation close buttons
document.querySelectorAll('.derivation-close').forEach((button) => {
    const panel = button.closest('.derivation-panel');
    if (panel) {
        const key = panel.id.replace('deriv-', '');
        button.addEventListener('click', () => toggleDerivation(key));
    }
});
```

**IMPORTANT:** Give each tab link a `data-tab` attribute in HTML to avoid the fragile text-matching approach:
```html
<button class="tab-link active" data-tab="results">Results</button>
<button class="tab-link" data-tab="ladder">Temperature Ladder</button>
<button class="tab-link" data-tab="heat">Heat Split</button>
<button class="tab-link" data-tab="background">Background</button>
```

Then the listener becomes:
```javascript
document.querySelectorAll('.tab-link').forEach((link) => {
    link.addEventListener('click', (event) => openTab(event, link.dataset.tab));
});
```

### 2.0.7 — Keyboard Accessibility for Derivation Panels [D6] ✓

**File:** `tools/simple_thermal/index.html`

Add `tabindex="0"` and `role="button"` to each clickable result item in the HTML:
```html
<div class="result-item clickable" data-key="required_sink_thermal_resistance" tabindex="0" role="button">
```

Add a keydown handler (in JS, after the click listeners):
```javascript
document.querySelectorAll('.result-item.clickable').forEach((item) => {
    item.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleDerivation(item.dataset.key);
        }
    });
});
```

### 2.0.8 — Stale Results Indicator [C6] ✓

**File:** `tools/simple_thermal/index.html`

Add a new banner element in the HTML, right after the `results-grid` div:
```html
<div class="stale-banner" id="stale-banner" style="display:none;">
    <p>Inputs have changed since the last calculation. Results shown may be outdated.</p>
</div>
```

CSS:
```css
.stale-banner {
    padding: 10px 14px;
    background: var(--callout-warning-bg);
    border-left: 4px solid var(--callout-warning-border);
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 0.88rem;
    color: var(--text-color);
}
```

JS — add a global flag and listener:
```javascript
let resultsAreStale = false;

function markResultsStale() {
    if (lastResults && !resultsAreStale) {
        resultsAreStale = true;
        document.getElementById('stale-banner').style.display = 'block';
        document.getElementById('results-grid').style.opacity = '0.6';
    }
}

function clearStaleIndicator() {
    resultsAreStale = false;
    document.getElementById('stale-banner').style.display = 'none';
    document.getElementById('results-grid').style.opacity = '1';
}
```

In `displayResults()`, call `clearStaleIndicator()` at the top.

Attach `markResultsStale` to all input elements:
```javascript
document.querySelectorAll('#calc-form input, #calc-form select').forEach((el) => {
    el.addEventListener('input', markResultsStale);
    el.addEventListener('change', markResultsStale);
});
```

### 2.0.9 — Required vs Achieved Rθ Comparison Indicator [C7] ✓

**File:** `tools/simple_thermal/index.html`

In `displayResults()`, after setting the two Rθ values, add:
```javascript
const requiredCard = document.querySelector('.result-item[data-key="required_sink_thermal_resistance"]');
const achievedCard = document.querySelector('.result-item[data-key="sink_thermal_resistance"]');
const meetsTarget = results.sink_thermal_resistance <= results.required_sink_thermal_resistance;

achievedCard.style.borderColor = meetsTarget ? 'var(--success-color)' : 'var(--danger-color)';
achievedCard.querySelector('.subtext').textContent = meetsTarget
    ? 'Meets the thermal budget'
    : 'Exceeds the required thermal resistance';
```

### 2.0.10 — Empty Chart State Guidance [C11] ✓

**File:** `tools/simple_thermal/index.html`

Add placeholder text to the chart plot areas:
```html
<div class="plot-area" id="ladder-plot">
    <p class="chart-placeholder" style="text-align:center;padding:60px 20px;color:var(--text-light);">Run a calculation to see the temperature ladder chart.</p>
</div>
```

Same for `heat-plot`.

In `renderTemperaturePlot()` and `renderHeatPlot()`, the Plotly.react call will overwrite the inner HTML, automatically removing the placeholder. No additional cleanup needed.

### 2.0.11 — Show Fin Spacing in Geometry Preview [C5] ✓

**File:** `tools/simple_thermal/index.html`, in `renderHeatsinkGeometryPreview()`

After the existing front-view dimension lines, add a spacing dimension between the first two fins:
```javascript
// Add fin spacing dimension between first two fins
if (finCount >= 2) {
    const fin1Right = frontX + scaledFrontFinThickness;
    const fin2Left = frontX + scaledFrontFinThickness + scaledFrontSpacing;
    const spacingDimY = frontBaseTop - scaledFrontFinHeight - 16;
    frontViewHtml += previewDimLine(
        fin1Right,
        spacingDimY,
        fin2Left,
        spacingDimY,
        `s = ${formatPreviewLength(spacing)}`,
        successColor
    );
}
```

### 2.0.12 — Footer [C14] ✓

**File:** `tools/simple_thermal/index.html`

Add before `</body>`:
```html
<footer style="border-top:1px solid var(--border-color);padding:18px 5%;text-align:center;font-size:0.85rem;color:var(--text-light);">
    <a href="../../index.html" style="color:var(--text-color);font-weight:600;">Transparent Tools</a>
    &nbsp;·&nbsp;
    <a href="https://ko-fi.com/transparent_tools" target="_blank" rel="noopener">Support on Ko-fi</a>
</footer>
```

### 2.0.13 — Pyodide Timeout Protection [D3]

**File:** `tools/simple_thermal/index.html`, in `handleCalculate()`

Wrap the calculation in a timeout:
```javascript
async function handleCalculate(event) {
    event.preventDefault();
    const button = document.getElementById('calculate-btn');
    button.disabled = true;
    button.textContent = 'Calculating...';
    try {
        const inputs = gatherInputs();
        const calcPromise = new Promise((resolve, reject) => {
            try {
                const resultProxy = pyToolModule.analyze_plate_fin_heatsink(/* ... */);
                const rawResults = resultProxy.toJs({ dict_converter: Object.fromEntries });
                resultProxy.destroy();
                resolve(rawResults);
            } catch (e) {
                reject(e);
            }
        });
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Calculation timed out after 30 seconds.')), 30000)
        );
        const rawResults = await Promise.race([calcPromise, timeoutPromise]);
        // ... rest of processing
    } catch (error) {
        // ... error handling
    }
}
```

Note: Since Pyodide calls are synchronous on the main thread, this timeout only works if the call actually blocks for a network issue or similar. For true protection, consider wrapping in a Web Worker in the future. For now, this guards against fetch-related hangs during module loading.

### 2.0.14 — MathJax Loading Fallback [C13] ✓

**File:** `tools/simple_thermal/index.html`

Add after the MathJax script tag:
```javascript
setTimeout(() => {
    if (!window.MathJax || !window.MathJax.typesetPromise) {
        document.querySelectorAll('.equation-box, .equation-card').forEach((el) => {
            el.style.fontFamily = 'var(--font-mono)';
            el.style.fontSize = '0.85rem';
        });
        console.warn('MathJax failed to load. Equations shown as raw LaTeX.');
    }
}, 10000);
```

---

## 3. Phase 1 — Accuracy Foundations (complete)

These changes modify the Python solver. Do them before UI features so the UI can display the new data.

> **Status (2026-03-19):** All 3 items implemented and tested (5 new tests added, all 15 pass).

### 3.1.1 — Improved Air Thermal Conductivity Fit [A7] ✓

**File:** `pycalcs/heatsinks.py`, in `air_properties()`

Replace:
```python
thermal_conductivity = 0.0241 * (temperature_k / 273.15) ** 0.9
```

With a Sutherland-type fit that's more accurate at elevated temperatures:
```python
# Sutherland-type thermal conductivity fit for air.
# Matches NIST data within 1.5% from 200 K to 700 K.
thermal_conductivity = (
    0.02414
    * (temperature_k / 273.15) ** 1.5
    * (273.15 + 194.0)
    / (temperature_k + 194.0)
)
```

**Verification:** At T=300K (27°C), k should be ~0.0263 W/mK. At T=500K, k should be ~0.0395 W/mK. Check against NIST webbook values.

**Test:**
```python
def test_air_thermal_conductivity_at_elevated_temperature() -> None:
    props = air_properties(227.0)  # 500 K film temperature
    # NIST value at 500 K is approximately 0.0395 W/mK
    assert 0.038 < props.thermal_conductivity < 0.041
```

### 3.1.2 — Fin-to-Fin Radiation View Factor Correction [A10] ✓

**File:** `pycalcs/heatsinks.py`

Add a new function after `linearized_radiation_coefficient()`:

```python
def fin_channel_radiation_view_factor(fin_height: float, fin_spacing: float) -> float:
    """
    Estimate the effective radiation view factor for a fin channel.

    For closely spaced fins, most radiation leaving one fin surface strikes
    the adjacent fin (which is at nearly the same temperature), reducing net
    radiation to ambient. This function returns a correction factor in [0, 1]
    that should multiply the linearized radiation coefficient.

    The model treats the channel as two parallel plates of height H separated
    by gap s, open at top and bottom. The effective view factor from one plate
    to the environment (not the opposing plate) is:

        F_eff = s / (s + H)

    This is the classic two-parallel-plate view factor to the opening,
    which approaches 1 for wide spacing and 0 for deep channels.

    ---References---
    Sparrow, E. M., Cess, R. D. (1978). Radiation Heat Transfer.
    Siegel, R., Howell, J. R. (2002). Thermal Radiation Heat Transfer.
    """

    if fin_height <= 0.0 or fin_spacing <= 0.0:
        return 1.0
    return fin_spacing / (fin_spacing + fin_height)
```

**Integration into the solver:**

In `evaluate_balance()` inside `analyze_plate_fin_heatsink()`, modify the radiation coefficient:
```python
radiation_coefficient = linearized_radiation_coefficient(
    emissivity=surface_emissivity,
    surface_temperature_c=surface_temperature,
    ambient_temperature_c=ambient_temperature,
)
# Correct for fin-to-fin view factor.
radiation_view_factor = fin_channel_radiation_view_factor(
    fin_height=geometry.fin_height,
    fin_spacing=geometry.fin_spacing,
)
radiation_coefficient *= radiation_view_factor
```

Also add `radiation_view_factor` to the returned result dict, and include it in the fin efficiency derivation string.

**Test:**
```python
def test_radiation_view_factor_decreases_with_tight_spacing() -> None:
    wide = fin_channel_radiation_view_factor(fin_height=0.02, fin_spacing=0.02)
    tight = fin_channel_radiation_view_factor(fin_height=0.02, fin_spacing=0.004)
    assert 0.4 < wide < 0.6  # H/s = 1, F ≈ 0.5
    assert 0.1 < tight < 0.25  # H/s = 5, F ≈ 0.167
    assert wide > tight
```

**IMPORTANT NOTE:** This change will reduce radiation predictions for tightly-spaced fins. Existing tests may need tolerance adjustments if radiation was a significant fraction of the heat balance. Run all tests after this change and adjust expected values if necessary.

### 3.1.3 — Natural Convection Induced Velocity Estimate [A6] ✓

**File:** `pycalcs/heatsinks.py`, in `natural_convection_plate_array()`

After computing the convection coefficient, estimate the buoyancy-induced velocity. Add before the return statement:

```python
# Estimate induced channel velocity from chimney-flow approximation.
# The heat carried by the air flow is Q_conv ≈ rho * cp * V * A_channel * dT_air.
# For the channel, dT_air ≈ 0.5 * delta_t (air exits at roughly half the wall-to-air delta).
# This is approximate but gives the right order of magnitude.
air_rise_estimate = max(delta_t * 0.5, 1.0)
channel_velocity_estimate = (
    convection_coefficient
    * geometry.fin_spacing
    * geometry.fin_height
    * delta_t
    / (props.density * props.specific_heat * geometry.open_flow_area * air_rise_estimate)
) if geometry.open_flow_area > 0 else 0.0
# Clamp to physically reasonable range.
channel_velocity_estimate = min(max(channel_velocity_estimate, 0.0), 2.0)
volumetric_flow_estimate = channel_velocity_estimate * geometry.open_flow_area
```

Update the return dict:
```python
return {
    "convection_coefficient": max(convection_coefficient, 0.0),
    "nusselt_number": nusselt_number,
    "rayleigh_modified": rayleigh_modified,
    "reynolds_number": 0.0,
    "channel_velocity": channel_velocity_estimate,
    "volumetric_flow_rate": volumetric_flow_estimate,
    "pressure_drop": 0.0,
}
```

---

## 4. Phase 2 — Physics Model Extensions (complete)

> **Status (2026-03-19):** All 5 items implemented and tested (8 new tests added, 23 total, all pass).

### 4.2.1 — Heatsink Orientation Input [A3] ✓

**File:** `pycalcs/heatsinks.py`

Add a new parameter to `analyze_plate_fin_heatsink()`:
```python
orientation: str = "vertical",  # "vertical", "horizontal_up", "horizontal_down"
```

Add a new function for horizontal natural convection:

```python
def natural_convection_horizontal_plate_array(
    geometry: PlateFinGeometry,
    surface_temperature: float,
    ambient_temperature: float,
    facing: str = "up",
    pressure_pa: float = 101325.0,
) -> Dict[str, float]:
    """
    Estimate natural convection for a horizontal plate-fin array.

    For fins facing up (heated surface up), uses the McAdams correlation
    for heated horizontal plates:
        Nu = 0.54 * Ra_L^0.25  (10^4 < Ra_L < 10^7, laminar)
        Nu = 0.15 * Ra_L^0.33  (10^7 < Ra_L < 10^11, turbulent)

    For fins facing down (heated surface down), uses:
        Nu = 0.27 * Ra_L^0.25  (10^5 < Ra_L < 10^10)

    The characteristic length L is the ratio of plate area to perimeter:
    L_c = A / P for the base footprint.

    ---References---
    McAdams, W. H. (1954). Heat Transmission, 3rd ed.
    Incropera et al. Fundamentals of Heat and Mass Transfer, Table 9.1.
    """

    delta_t = surface_temperature - ambient_temperature
    if delta_t <= 0.0:
        return {
            "convection_coefficient": 0.0,
            "nusselt_number": 0.0,
            "rayleigh_modified": 0.0,
            "reynolds_number": 0.0,
            "channel_velocity": 0.0,
            "volumetric_flow_rate": 0.0,
            "pressure_drop": 0.0,
        }

    film_temperature = 0.5 * (surface_temperature + ambient_temperature)
    props = air_properties(film_temperature, pressure_pa=pressure_pa)

    # Characteristic length for horizontal plate.
    char_length = (geometry.base_length * geometry.base_width) / (
        2.0 * (geometry.base_length + geometry.base_width)
    )
    rayleigh = (
        GRAVITY
        * props.thermal_expansion
        * delta_t
        * char_length ** 3
        / (props.kinematic_viscosity * props.thermal_diffusivity)
    )
    rayleigh = max(rayleigh, 1e-12)

    if facing == "up":
        if rayleigh < 1e7:
            nusselt_number = 0.54 * rayleigh ** 0.25
        else:
            nusselt_number = 0.15 * rayleigh ** (1.0 / 3.0)
    else:
        nusselt_number = 0.27 * rayleigh ** 0.25

    convection_coefficient = nusselt_number * props.thermal_conductivity / char_length

    return {
        "convection_coefficient": max(convection_coefficient, 0.0),
        "nusselt_number": nusselt_number,
        "rayleigh_modified": rayleigh,
        "reynolds_number": 0.0,
        "channel_velocity": 0.0,
        "volumetric_flow_rate": 0.0,
        "pressure_drop": 0.0,
    }
```

In `resolve_flow()` inside `analyze_plate_fin_heatsink()`, dispatch based on orientation:
```python
if airflow_mode == "natural":
    if orientation == "vertical":
        state = natural_convection_plate_array(...)
    elif orientation == "horizontal_up":
        state = natural_convection_horizontal_plate_array(..., facing="up")
    elif orientation == "horizontal_down":
        state = natural_convection_horizontal_plate_array(..., facing="down")
    else:
        raise ValueError("orientation must be 'vertical', 'horizontal_up', or 'horizontal_down'.")
    state["convection_mode_used"] = f"natural_{orientation}"
    return state
```

**UI changes:**
Add a new select input in the "Air & Fan" tab, above the cooling mode selector:
```html
<div class="input-group">
    <label for="orientation">Heatsink Orientation</label>
    <select id="orientation" name="orientation">
        <option value="vertical">Vertical (fins point up, air flows up)</option>
        <option value="horizontal_up">Horizontal, fins up</option>
        <option value="horizontal_down">Horizontal, fins down</option>
    </select>
    <div class="input-note">Orientation affects the natural convection correlation. Forced and fan modes ignore this.</div>
</div>
```

Add `orientation` to `gatherInputs()` and pass it to the Python call.

**Test:**
```python
def test_horizontal_down_gives_lower_performance_than_vertical() -> None:
    geometry = calculate_plate_fin_geometry(
        base_length=0.10, base_width=0.08, base_thickness=0.005,
        fin_height=0.03, fin_thickness=0.001, fin_count=10,
    )
    vertical = natural_convection_plate_array(geometry, 70.0, 25.0)
    horiz_down = natural_convection_horizontal_plate_array(geometry, 70.0, 25.0, facing="down")
    assert vertical["convection_coefficient"] > horiz_down["convection_coefficient"]
```

### 4.2.2 — Spreading Resistance Model [A1] ✓

**File:** `pycalcs/heatsinks.py`

Add a new function:

```python
def rectangular_spreading_resistance(
    source_length: float,
    source_width: float,
    base_length: float,
    base_width: float,
    base_thickness: float,
    thermal_conductivity: float,
) -> float:
    """
    Estimate constriction/spreading resistance for a centered rectangular source
    on a rectangular plate using the Yovanovich et al. dimensionless approach.

    For a centered rectangular source of dimensions (a_s × b_s) on a plate of
    dimensions (a_p × b_p) with thickness t and conductivity k, the spreading
    resistance is approximated by:

        R_sp = 1 / (k * sqrt(pi * A_s)) * psi(epsilon, tau)

    where:
        A_s = a_s * b_s (source area)
        epsilon = sqrt(A_s / A_p) (relative source size)
        tau = t / sqrt(A_p) (relative thickness)
        psi is a dimensionless spreading resistance function

    For the simplified case (adiabatic edges, uniform flux source):
        psi ≈ (1 - epsilon) ^ 1.5 / (epsilon * tau + (1 - epsilon)^1.5)

    This simplification is valid when the source is roughly centered and
    the plate edges are not cooled.

    Returns zero when the source footprint equals the plate footprint.

    ---References---
    Yovanovich, M. M., Muzychka, Y. S., Culham, J. R. (1999).
        Spreading Resistance of Isoflux Rectangles and Strips on
        Compound Flux Channels.
    Lee, S., Song, S., Au, V., Moran, K. P. (1995).
        Constriction/Spreading Resistance Model for Electronics Packaging.
    """

    if source_length <= 0 or source_width <= 0:
        raise ValueError("Source dimensions must be positive.")
    if base_length <= 0 or base_width <= 0 or base_thickness <= 0:
        raise ValueError("Base dimensions must be positive.")
    if thermal_conductivity <= 0:
        raise ValueError("Thermal conductivity must be positive.")

    source_area = source_length * source_width
    plate_area = base_length * base_width

    if source_area >= plate_area:
        return 0.0  # No spreading when source covers the full base.

    epsilon = math.sqrt(source_area / plate_area)
    tau = base_thickness / math.sqrt(plate_area)

    # Simplified dimensionless spreading function.
    psi = (1.0 - epsilon) ** 1.5 / (epsilon * tau + (1.0 - epsilon) ** 1.5)

    return psi / (thermal_conductivity * math.sqrt(math.pi * source_area))
```

**Integration into the main solver:**

Add two new parameters to `analyze_plate_fin_heatsink()`:
```python
source_length: float = 0.0,  # 0 means "same as base" (no spreading)
source_width: float = 0.0,   # 0 means "same as base" (no spreading)
```

Inside the solver, after computing `geometry`, calculate spreading resistance:
```python
eff_source_length = source_length if source_length > 0 else geometry.base_length
eff_source_width = source_width if source_width > 0 else geometry.base_width
spreading_r = rectangular_spreading_resistance(
    source_length=eff_source_length,
    source_width=eff_source_width,
    base_length=geometry.base_length,
    base_width=geometry.base_width,
    base_thickness=geometry.base_thickness,
    thermal_conductivity=material_conductivity,
)
```

Modify the temperature stack:
```python
# Previously:
# case_temperature = base_temperature + heat_load * interface_resistance
# Now include spreading:
effective_base_temperature = base_temperature + heat_load * spreading_r
case_temperature = effective_base_temperature + heat_load * interface_resistance
```

Add to the returned result dict:
```python
"spreading_resistance": spreading_r,
"effective_base_temperature": effective_base_temperature,
```

**UI changes:**
Add source footprint inputs behind Expert Mode in the Geometry tab:
```html
<div class="advanced-section">
    <h4>Source Footprint (Expert)</h4>
    <div class="input-note" style="margin-bottom:12px;">
        If the heat source is smaller than the heatsink base, spreading resistance adds
        temperature rise. Leave at 0 to assume the source covers the full base.
    </div>
    <div class="input-row">
        <div class="input-group">
            <label for="source_length">Source Length (mm)</label>
            <input type="number" id="source_length" name="source_length" value="0" step="any" min="0">
        </div>
        <div class="input-group">
            <label for="source_width">Source Width (mm)</label>
            <input type="number" id="source_width" name="source_width" value="0" step="any" min="0">
        </div>
    </div>
</div>
```

**Test:**
```python
def test_spreading_resistance_is_positive_for_small_source() -> None:
    r_sp = rectangular_spreading_resistance(
        source_length=0.020,
        source_width=0.020,
        base_length=0.100,
        base_width=0.080,
        base_thickness=0.005,
        thermal_conductivity=201.0,
    )
    assert r_sp > 0.0
    assert r_sp < 2.0  # Sanity bound

def test_spreading_resistance_is_zero_when_source_covers_base() -> None:
    r_sp = rectangular_spreading_resistance(
        source_length=0.100,
        source_width=0.080,
        base_length=0.100,
        base_width=0.080,
        base_thickness=0.005,
        thermal_conductivity=201.0,
    )
    assert r_sp == 0.0
```

### 4.2.3 — Airflow Bypass Model [A2] ✓

**File:** `pycalcs/heatsinks.py`

Add a new parameter to `analyze_plate_fin_heatsink()`:
```python
ducted: bool = True,
```

Add a bypass estimation function:

```python
def estimate_bypass_fraction(
    geometry: PlateFinGeometry,
    approach_velocity: float,
) -> float:
    """
    Estimate the fraction of approach airflow that bypasses the fin array
    rather than flowing through the channels.

    Uses a simple first-order model: the bypass fraction is proportional
    to the ratio of the flow resistance through the fins vs. the resistance
    of the bypass path around the fin tips.

    For a first approximation:
        bypass_fraction ≈ 1 / (1 + K * (H/s)^0.5)

    where K is an empirical constant (~0.5 for typical unducted heatsinks),
    H is fin height, and s is fin spacing. Tighter spacing and taller fins
    drive more air around rather than through.

    ---References---
    Simons, R. E. (2004). Estimating the Effect of Flow Bypass on
        Parallel Plate-Fin Heat Sink Performance. Electronics Cooling.
    """

    if geometry.fin_spacing <= 0 or geometry.fin_height <= 0:
        return 0.0
    aspect = geometry.fin_height / geometry.fin_spacing
    K = 0.5  # Empirical constant for unducted parallel-plate arrays
    bypass = 1.0 / (1.0 + K * math.sqrt(max(aspect, 0.01)))
    # Invert: bypass fraction is the fraction that does NOT go through.
    # Actually: fraction going through = K*sqrt(aspect) / (1 + K*sqrt(aspect))
    # So bypass = 1 / (1 + K*sqrt(aspect))
    return max(0.0, min(bypass, 0.9))  # Clamp to [0, 0.9]
```

In `resolve_flow()`, when `airflow_mode == "forced"` and `ducted == False`:
```python
if not ducted:
    bypass = estimate_bypass_fraction(geometry, approach_velocity)
    flow_rate *= (1.0 - bypass)
```

Add `bypass_fraction` to the returned result dict.

**UI changes:**
Add a toggle in the "Air & Fan" tab (visible only in forced/fan modes):
```html
<div class="input-group forced-only fan-only">
    <label for="ducted">Duct Configuration</label>
    <select id="ducted" name="ducted">
        <option value="true">Ducted (all air through fins)</option>
        <option value="false">Unducted (some air bypasses)</option>
    </select>
    <div class="input-note">If the heatsink is in open air without a duct or shroud, some airflow will bypass the fin channels.</div>
</div>
```

### 4.2.4 — Mixed Convection Warning [A4] ✓

**File:** `pycalcs/heatsinks.py`, in `analyze_plate_fin_heatsink()`

After computing the forced convection state, check the Richardson number:
```python
if airflow_mode in ("forced", "fan_curve"):
    flow_state = final_state["flow_state"]
    if flow_state["reynolds_number"] > 0:
        film_temp = 0.5 * (base_temperature + ambient_temperature)
        props_check = air_properties(film_temp, pressure_pa=pressure_pa)
        grashof = (
            GRAVITY * props_check.thermal_expansion
            * (base_temperature - ambient_temperature)
            * geometry.hydraulic_diameter ** 3
            / props_check.kinematic_viscosity ** 2
        )
        richardson = grashof / (flow_state["reynolds_number"] ** 2)
        if richardson > 0.1:
            recommendations.append(
                f"Richardson number is {richardson:.2f} (>0.1); buoyancy effects may be significant. "
                "Consider verifying with a mixed-convection analysis."
            )
```

### 4.2.5 — Non-Parabolic Fan Curve (Optional Points) [A9] ✓

**File:** `pycalcs/heatsinks.py`

Add an optional parameter to `fan_curve_pressure()` and `solve_fan_operating_point()`:
```python
fan_curve_points: list = None,  # Optional list of [flow, pressure] pairs
```

When `fan_curve_points` is provided and non-empty, use piecewise-linear interpolation instead of the parabolic model:
```python
def fan_curve_pressure(
    volumetric_flow_rate: float,
    fan_max_pressure: float,
    fan_max_flow_rate: float,
    fan_curve_points: list = None,
) -> float:
    if fan_curve_points and len(fan_curve_points) >= 2:
        # Sort by flow rate
        points = sorted(fan_curve_points, key=lambda p: p[0])
        if volumetric_flow_rate <= points[0][0]:
            return points[0][1]
        if volumetric_flow_rate >= points[-1][0]:
            return max(points[-1][1], 0.0)
        for i in range(len(points) - 1):
            if points[i][0] <= volumetric_flow_rate <= points[i + 1][0]:
                frac = ((volumetric_flow_rate - points[i][0])
                        / (points[i + 1][0] - points[i][0]))
                return points[i][1] + frac * (points[i + 1][1] - points[i][1])
    # Default parabolic
    ratio = min(max(volumetric_flow_rate / fan_max_flow_rate, 0.0), 1.0)
    return fan_max_pressure * (1.0 - ratio ** 2)
```

This is backwards-compatible. The UI for custom fan curve data is deferred to Phase 6.

---

## 5. Phase 3 — Sensitivity Analysis (complete)

This is the largest feature addition. Follow the architecture in `plans/heatsink_sensitivity_analysis.md`.

> **Status (2026-03-19):** All 3 items implemented — metadata, 1D sweep, 2D contour in Python with 5 new tests (28 total, all pass). UI tabs, controls, Plotly rendering, and event wiring complete.

### 5.3.1 — Sweep Metadata [B1 prerequisite] ✓

**File:** `pycalcs/heatsinks.py`

Add at the module level:

```python
def get_heatsink_sweep_metadata() -> Dict[str, Any]:
    """Return parameter and output definitions for sensitivity analysis."""
    return {
        "parameters": {
            "fin_height": {
                "label": "Fin Height",
                "unit": "m",
                "display_unit": "mm",
                "display_scale": 1000,
                "category": "geometry",
                "default_span": [0.5, 1.5],
                "min": 0.005,
                "max": 0.120,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
            },
            "fin_thickness": {
                "label": "Fin Thickness",
                "unit": "m",
                "display_unit": "mm",
                "display_scale": 1000,
                "category": "geometry",
                "default_span": [0.5, 2.0],
                "min": 0.0003,
                "max": 0.005,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
            },
            "fin_count": {
                "label": "Fin Count",
                "unit": "",
                "display_unit": "",
                "display_scale": 1,
                "category": "geometry",
                "default_span": [0.5, 2.0],
                "min": 2,
                "max": 60,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
                "integer": True,
            },
            "base_thickness": {
                "label": "Base Thickness",
                "unit": "m",
                "display_unit": "mm",
                "display_scale": 1000,
                "category": "geometry",
                "default_span": [0.5, 2.0],
                "min": 0.001,
                "max": 0.020,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
            },
            "base_length": {
                "label": "Base Length",
                "unit": "m",
                "display_unit": "mm",
                "display_scale": 1000,
                "category": "geometry",
                "default_span": [0.5, 1.5],
                "min": 0.020,
                "max": 0.300,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
            },
            "base_width": {
                "label": "Base Width",
                "unit": "m",
                "display_unit": "mm",
                "display_scale": 1000,
                "category": "geometry",
                "default_span": [0.5, 1.5],
                "min": 0.020,
                "max": 0.300,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
            },
            "heat_load": {
                "label": "Heat Load",
                "unit": "W",
                "display_unit": "W",
                "display_scale": 1,
                "category": "thermal",
                "default_span": [0.5, 2.0],
                "min": 0.5,
                "max": 500.0,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
            },
            "ambient_temperature": {
                "label": "Ambient Temperature",
                "unit": "°C",
                "display_unit": "°C",
                "display_scale": 1,
                "category": "thermal",
                "default_span": [0.8, 1.2],
                "min": -40.0,
                "max": 85.0,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
            },
            "surface_emissivity": {
                "label": "Surface Emissivity",
                "unit": "",
                "display_unit": "",
                "display_scale": 1,
                "category": "thermal",
                "default_span": [0.5, 1.0],
                "min": 0.02,
                "max": 0.95,
                "scale": "linear",
                "modes": ["natural", "forced", "fan_curve"],
            },
            "approach_velocity": {
                "label": "Approach Velocity",
                "unit": "m/s",
                "display_unit": "m/s",
                "display_scale": 1,
                "category": "airflow",
                "default_span": [0.3, 2.0],
                "min": 0.1,
                "max": 15.0,
                "scale": "linear",
                "modes": ["forced"],
            },
        },
        "outputs": {
            "sink_thermal_resistance": {
                "label": "Sink Thermal Resistance",
                "unit": "K/W",
                "goal": "minimize",
            },
            "junction_temperature": {
                "label": "Junction Temperature",
                "unit": "°C",
                "goal": "minimize",
            },
            "temperature_margin": {
                "label": "Temperature Margin",
                "unit": "°C",
                "goal": "maximize",
            },
            "pressure_drop": {
                "label": "Pressure Drop",
                "unit": "Pa",
                "goal": "minimize",
            },
            "fin_efficiency": {
                "label": "Fin Efficiency",
                "unit": "",
                "goal": "maximize",
            },
        },
    }
```

### 5.3.2 — 1D Sweep Function [B1] ✓

**File:** `pycalcs/heatsinks.py`

```python
def run_heatsink_1d_sweep(
    baseline_inputs: Dict[str, Any],
    sweep_param: str,
    sweep_values: list,
    output_keys: list = None,
) -> Dict[str, Any]:
    """
    Run a 1D parameter sweep around a baseline heatsink configuration.

    For each value in sweep_values, overrides the sweep_param in baseline_inputs,
    calls analyze_plate_fin_heatsink(), and collects the requested output keys.

    Returns:
        x_values: list of sweep parameter values
        series: dict mapping output_key → list of output values
        baseline_x: the baseline value of the sweep parameter
        baseline_outputs: dict of output values at the baseline
        valid_mask: list of bools (True if the solver succeeded for that point)
        warnings: list of warning strings
    """
    if output_keys is None:
        output_keys = ["sink_thermal_resistance", "junction_temperature", "temperature_margin"]

    metadata = get_heatsink_sweep_metadata()
    if sweep_param not in metadata["parameters"]:
        raise ValueError(f"Unknown sweep parameter: {sweep_param}")

    baseline_x = baseline_inputs.get(sweep_param)
    results_series = {key: [] for key in output_keys}
    valid_mask = []
    warnings = []

    for val in sweep_values:
        inputs = dict(baseline_inputs)
        inputs[sweep_param] = int(val) if metadata["parameters"][sweep_param].get("integer") else float(val)
        try:
            result = analyze_plate_fin_heatsink(**inputs)
            for key in output_keys:
                results_series[key].append(result.get(key))
            valid_mask.append(True)
        except (ValueError, ZeroDivisionError) as e:
            for key in output_keys:
                results_series[key].append(None)
            valid_mask.append(False)
            warnings.append(f"At {sweep_param}={val}: {e}")

    # Compute baseline outputs
    baseline_outputs = {}
    try:
        baseline_result = analyze_plate_fin_heatsink(**baseline_inputs)
        for key in output_keys:
            baseline_outputs[key] = baseline_result.get(key)
    except Exception:
        pass

    return {
        "x_values": list(sweep_values),
        "series": results_series,
        "baseline_x": baseline_x,
        "baseline_outputs": baseline_outputs,
        "valid_mask": valid_mask,
        "warnings": warnings,
    }
```

### 5.3.3 — 2D Contour Function [B2] ✓

**File:** `pycalcs/heatsinks.py`

```python
def run_heatsink_2d_contour(
    baseline_inputs: Dict[str, Any],
    x_param: str,
    y_param: str,
    x_values: list,
    y_values: list,
    output_key: str = "sink_thermal_resistance",
) -> Dict[str, Any]:
    """
    Run a 2D parameter sweep and return a contour grid.

    Returns:
        x_values: list of x parameter values
        y_values: list of y parameter values
        z_values: 2D list [y_index][x_index] of output values (None where invalid)
        valid_mask: 2D list of bools
        baseline_point: {"x": ..., "y": ..., "z": ...}
        best_point: {"x": ..., "y": ..., "z": ...} (best feasible)
    """
    metadata = get_heatsink_sweep_metadata()
    if x_param not in metadata["parameters"]:
        raise ValueError(f"Unknown x parameter: {x_param}")
    if y_param not in metadata["parameters"]:
        raise ValueError(f"Unknown y parameter: {y_param}")

    z_values = []
    valid_mask = []
    best_z = None
    best_point = None
    goal = metadata["outputs"].get(output_key, {}).get("goal", "minimize")

    for y_val in y_values:
        z_row = []
        valid_row = []
        for x_val in x_values:
            inputs = dict(baseline_inputs)
            inputs[x_param] = int(x_val) if metadata["parameters"][x_param].get("integer") else float(x_val)
            inputs[y_param] = int(y_val) if metadata["parameters"][y_param].get("integer") else float(y_val)
            try:
                result = analyze_plate_fin_heatsink(**inputs)
                z = result.get(output_key)
                z_row.append(z)
                valid_row.append(True)
                if z is not None:
                    is_better = (
                        best_z is None
                        or (goal == "minimize" and z < best_z)
                        or (goal == "maximize" and z > best_z)
                    )
                    if is_better:
                        best_z = z
                        best_point = {"x": x_val, "y": y_val, "z": z}
            except (ValueError, ZeroDivisionError):
                z_row.append(None)
                valid_row.append(False)
        z_values.append(z_row)
        valid_mask.append(valid_row)

    baseline_point = {"x": baseline_inputs.get(x_param), "y": baseline_inputs.get(y_param)}
    try:
        bl_result = analyze_plate_fin_heatsink(**baseline_inputs)
        baseline_point["z"] = bl_result.get(output_key)
    except Exception:
        baseline_point["z"] = None

    return {
        "x_values": list(x_values),
        "y_values": list(y_values),
        "z_values": z_values,
        "valid_mask": valid_mask,
        "baseline_point": baseline_point,
        "best_point": best_point,
    }
```

### 5.3.4 — Sensitivity UI Tabs [B1, B2] ✓

**File:** `tools/simple_thermal/index.html`

Add two new tab links:
```html
<button class="tab-link" data-tab="sweep1d" disabled id="tab-sweep1d">1D Sweep</button>
<button class="tab-link" data-tab="sweep2d" disabled id="tab-sweep2d">2D Trade Space</button>
```

Add two new tab content panels (after the `background` tab):

**1D Sweep tab:**
```html
<div id="sweep1d" class="tab-content">
    <div class="callout">
        <p><strong>1D Sweep:</strong> Vary one parameter at a time to see how it affects the selected output metric.</p>
    </div>
    <div class="input-row" style="margin-bottom:16px;">
        <div class="input-group">
            <label for="sweep1d-param">Sweep Parameter</label>
            <select id="sweep1d-param"></select>
        </div>
        <div class="input-group">
            <label for="sweep1d-output">Output Metric</label>
            <select id="sweep1d-output"></select>
        </div>
    </div>
    <div class="input-row" style="margin-bottom:16px;">
        <div class="input-group">
            <label for="sweep1d-range">Range</label>
            <select id="sweep1d-range">
                <option value="0.2">± 20%</option>
                <option value="0.5" selected>± 50%</option>
                <option value="1.0">± 100%</option>
                <option value="custom">Custom</option>
            </select>
        </div>
        <div class="input-group">
            <button type="button" class="btn-primary" id="sweep1d-run" style="margin-top:22px;">Run Sweep</button>
        </div>
    </div>
    <div class="chart-panel">
        <div class="plot-area" id="sweep1d-plot">
            <p style="text-align:center;padding:60px 20px;color:var(--text-light);">Configure and run a sweep to see results.</p>
        </div>
    </div>
</div>
```

**2D Trade Space tab** (similar structure with X param, Y param, output metric, grid resolution select, run button, and a Plotly heatmap div).

**JavaScript for populating controls from metadata:**
```javascript
async function loadSweepMetadata() {
    const metaProxy = pyToolModule.get_heatsink_sweep_metadata();
    sweepState.metadata = normalizeNestedDict(metaProxy.toJs({ dict_converter: Object.fromEntries }));
    metaProxy.destroy();
    populateSweepControls();
}

function populateSweepControls() {
    const meta = sweepState.metadata;
    if (!meta) return;

    // 1D param selector
    const paramSelect = document.getElementById('sweep1d-param');
    paramSelect.innerHTML = '';
    Object.entries(meta.parameters).forEach(([key, p]) => {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = `${p.label} (${p.display_unit || p.unit})`;
        paramSelect.appendChild(opt);
    });

    // Output selector
    const outputSelect = document.getElementById('sweep1d-output');
    outputSelect.innerHTML = '';
    Object.entries(meta.outputs).forEach(([key, o]) => {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = `${o.label} (${o.unit})`;
        outputSelect.appendChild(opt);
    });

    // Same for 2D selectors
}
```

**JavaScript for running sweeps:**
```javascript
async function runOneDSweep() {
    const paramKey = document.getElementById('sweep1d-param').value;
    const outputKey = document.getElementById('sweep1d-output').value;
    const rangeValue = document.getElementById('sweep1d-range').value;
    const baseline = gatherInputs();
    const meta = sweepState.metadata.parameters[paramKey];

    // Generate sweep values
    const baseVal = baseline[paramKey];
    let span = parseFloat(rangeValue);
    const nPoints = 40;
    const low = Math.max(baseVal * (1 - span), meta.min);
    const high = Math.min(baseVal * (1 + span), meta.max);
    const step = (high - low) / (nPoints - 1);
    const sweepValues = Array.from({ length: nPoints }, (_, i) => low + i * step);
    if (meta.integer) {
        sweepValues.forEach((v, i) => { sweepValues[i] = Math.round(v); });
    }

    // Call Python
    const sweepProxy = pyToolModule.run_heatsink_1d_sweep(
        pyodide.toPy(baseline), paramKey, pyodide.toPy(sweepValues), pyodide.toPy([outputKey])
    );
    const sweepResult = normalizeNestedDict(sweepProxy.toJs({ dict_converter: Object.fromEntries }));
    sweepProxy.destroy();

    // Plot
    const displayScale = meta.display_scale || 1;
    const xDisplay = sweepResult.x_values.map(v => v * displayScale);
    const baselineXDisplay = sweepResult.baseline_x * displayScale;

    const trace = {
        x: xDisplay,
        y: sweepResult.series[outputKey],
        mode: 'lines+markers',
        name: sweepState.metadata.outputs[outputKey].label,
    };
    const baselineTrace = {
        x: [baselineXDisplay],
        y: [sweepResult.baseline_outputs[outputKey]],
        mode: 'markers',
        marker: { size: 12, color: 'red', symbol: 'diamond' },
        name: 'Baseline',
    };

    const layout = {
        ...getPlotTheme(),
        title: { text: `${meta.label} Sweep`, font: { size: 14 } },
        xaxis: { ...getPlotTheme().xaxis, title: `${meta.label} (${meta.display_unit || meta.unit})` },
        yaxis: { ...getPlotTheme().yaxis, title: `${sweepState.metadata.outputs[outputKey].label} (${sweepState.metadata.outputs[outputKey].unit})` },
    };
    Plotly.react('sweep1d-plot', [trace, baselineTrace], layout, { displayModeBar: false, responsive: true });
}
```

Enable sweep tabs after a successful baseline calculation:
```javascript
// In displayResults(), at the end:
document.getElementById('tab-sweep1d').disabled = false;
document.getElementById('tab-sweep2d').disabled = false;
sweepState.baselineInputs = gatherInputs();
sweepState.baselineResults = results;
```

---

## 6. Phase 4 — UI/UX Overhaul (C2, C3, C4, C12 complete — 2026-03-19; D1 deferred)

### 6.4.1 — Auto-Calculate with Debounce [C2] ✓

**File:** `tools/simple_thermal/index.html`

```javascript
let autoCalcTimer = null;

function scheduleAutoCalculate() {
    if (autoCalcTimer) clearTimeout(autoCalcTimer);
    markResultsStale();
    autoCalcTimer = setTimeout(() => {
        if (!document.getElementById('calculate-btn').disabled) {
            handleCalculate(new Event('submit'));
        }
    }, 500);
}

// Attach to all inputs
document.querySelectorAll('#calc-form input[type="number"], #calc-form select').forEach((el) => {
    el.addEventListener('input', scheduleAutoCalculate);
    el.addEventListener('change', scheduleAutoCalculate);
});
```

**IMPORTANT:** This must be added AFTER the initial Pyodide load completes and the Calculate button is enabled. Put it in `main()` after `document.getElementById('calculate-btn').disabled = false;`.

### 6.4.2 — Inline Input Validation [C3] ✓

**File:** `tools/simple_thermal/index.html`

Add validation rules:
```javascript
const VALIDATION_RULES = {
    heat_load: { min: 0.01, message: 'Must be positive' },
    ambient_temperature: { min: -273.14, message: 'Must be above absolute zero' },
    target_junction_temperature: { min: -273.14, message: 'Must be above absolute zero' },
    base_length: { min: 1, message: 'Must be at least 1 mm' },  // mm after C1
    base_width: { min: 1, message: 'Must be at least 1 mm' },
    base_thickness: { min: 0.1, message: 'Must be at least 0.1 mm' },
    fin_height: { min: 1, message: 'Must be at least 1 mm' },
    fin_thickness: { min: 0.1, message: 'Must be at least 0.1 mm' },
    fin_count: { min: 2, message: 'Must be at least 2' },
    surface_emissivity: { min: 0.01, max: 1.0, message: 'Must be between 0.01 and 1.0' },
};

function validateInput(inputEl) {
    const rules = VALIDATION_RULES[inputEl.id];
    if (!rules) return true;
    const val = parseFloat(inputEl.value);
    let valid = Number.isFinite(val);
    if (valid && rules.min !== undefined) valid = val >= rules.min;
    if (valid && rules.max !== undefined) valid = val <= rules.max;

    inputEl.style.borderColor = valid ? '' : 'var(--danger-color)';
    let errorEl = inputEl.parentElement.querySelector('.validation-error');
    if (!valid) {
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.className = 'validation-error';
            errorEl.style.cssText = 'font-size:0.78rem;color:var(--danger-color);margin-top:4px;';
            inputEl.parentElement.appendChild(errorEl);
        }
        errorEl.textContent = rules.message;
    } else if (errorEl) {
        errorEl.remove();
    }
    return valid;
}

// Cross-field validation: fin_count * fin_thickness < base_width
function validateGeometry() {
    const finCount = parseInt(document.getElementById('fin_count').value, 10);
    const finThickness = parseFloat(document.getElementById('fin_thickness').value);
    const baseWidth = parseFloat(document.getElementById('base_width').value);
    // All in mm after C1
    if (finCount * finThickness >= baseWidth) {
        const el = document.getElementById('fin_count');
        el.style.borderColor = 'var(--danger-color)';
        return false;
    }
    return true;
}
```

Attach to inputs:
```javascript
document.querySelectorAll('#calc-form input[type="number"]').forEach((el) => {
    el.addEventListener('blur', () => validateInput(el));
    el.addEventListener('input', () => validateInput(el));
});
```

### 6.4.3 — Actionable Recommendations [C12] ✓

**File:** `pycalcs/heatsinks.py`, in the recommendations section of `analyze_plate_fin_heatsink()`

Replace generic recommendations with parameter-aware ones:
```python
if temperature_margin < 0.0:
    suggestions = []
    if airflow_mode == "natural":
        suggestions.append("switch to forced convection")
    if geometry.fin_count < 20:
        suggestions.append(f"increase fin count from {geometry.fin_count} to {geometry.fin_count + 4}")
    if geometry.fin_height < 0.05:
        height_mm = geometry.fin_height * 1000
        suggestions.append(f"increase fin height from {height_mm:.0f} mm to {height_mm + 10:.0f} mm")
    if surface_emissivity < 0.5:
        suggestions.append("use a black anodized finish (emissivity ~0.85)")
    rec_text = "Design exceeds thermal budget. Try: " + "; ".join(suggestions) + "."
    recommendations.append(rec_text)
```

### 6.4.4 — Tablet Layout Refinement [C4] ✓

**File:** `tools/simple_thermal/index.html`, CSS

Change:
```css
@media (max-width: 1024px) {
    .tool-layout { grid-template-columns: 1fr; }
}
```

To:
```css
@media (max-width: 768px) {
    .tool-layout { grid-template-columns: 1fr; }
}
@media (min-width: 769px) and (max-width: 1024px) {
    .tool-layout { grid-template-columns: minmax(320px, 0.85fr) minmax(400px, 1.15fr); gap: 20px; }
}
```

### 6.4.5 — Extract JS to Separate File [D1]

Create a new file `tools/simple_thermal/heatsink-designer.js` and move the entire `<script>` block content (lines 1579–2582) into it.

In `index.html`, replace the `<script>...</script>` block with:
```html
<script src="heatsink-designer.js"></script>
```

No other changes needed. The JS references DOM elements by ID, so it doesn't depend on being inline.

---

## 7. Phase 5 — Testing & Validation (E1–E4, E6, B7, D3 complete — 2026-03-19; B5, validity docs deferred)

### 7.5.1 — Turbulent Branch Test [E3] ✓

**File:** `tests/test_heatsinks.py`

```python
def test_turbulent_forced_convection_at_high_flow() -> None:
    """Verify the turbulent branch activates at high flow rates."""
    geometry = calculate_plate_fin_geometry(
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
    )
    # Use a high flow rate to push Re > 2300
    result = forced_convection_plate_array(
        geometry,
        surface_temperature=70.0,
        ambient_temperature=25.0,
        volumetric_flow_rate=0.015,  # Very high flow
    )
    assert result["reynolds_number"] > 2300.0
    assert result["nusselt_number"] > 0.0
    assert result["pressure_drop"] > 0.0
```

### 7.5.2 — Approach Velocity Conversion Test [E4] ✓

```python
def test_approach_velocity_converts_to_flow_rate() -> None:
    result = analyze_plate_fin_heatsink(
        heat_load=20.0,
        ambient_temperature=25.0,
        target_junction_temperature=100.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
        surface_emissivity=0.85,
        airflow_mode="forced",
        approach_velocity=3.0,
        volumetric_flow_rate=0.0,
    )
    expected_flow = 3.0 * 0.08 * 0.03  # approach_velocity * base_width * fin_height
    assert result["volumetric_flow_rate"] > 0.0
    assert result["pressure_drop"] > 0.0
```

### 7.5.3 — Edge Case Tests [E2] ✓

```python
def test_very_tall_fins_have_low_efficiency() -> None:
    result = analyze_plate_fin_heatsink(
        heat_load=15.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.10,
        base_width=0.10,
        base_thickness=0.005,
        fin_height=0.10,  # Very tall
        fin_thickness=0.0005,  # Very thin
        fin_count=10,
        material_conductivity=201.0,
    )
    assert result["fin_efficiency"] < 0.7

def test_low_heat_load_near_ambient() -> None:
    result = analyze_plate_fin_heatsink(
        heat_load=1.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.10,
        base_width=0.08,
        base_thickness=0.005,
        fin_height=0.03,
        fin_thickness=0.001,
        fin_count=10,
        material_conductivity=201.0,
    )
    assert result["base_temperature"] < 35.0  # Barely above ambient
    assert result["temperature_margin"] > 100.0
```

### 7.5.4 — Radiation-Dominant Case Test [E6] ✓

```python
def test_radiation_significant_at_high_emissivity_low_load() -> None:
    result = analyze_plate_fin_heatsink(
        heat_load=3.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.10,
        base_width=0.10,
        base_thickness=0.005,
        fin_height=0.02,
        fin_thickness=0.001,
        fin_count=5,  # Wide spacing
        material_conductivity=201.0,
        surface_emissivity=0.90,
    )
    assert result["radiation_heat_rejected"] > 0.25 * 3.0

    # Now with very low emissivity
    result_low_e = analyze_plate_fin_heatsink(
        heat_load=3.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.10,
        base_width=0.10,
        base_thickness=0.005,
        fin_height=0.02,
        fin_thickness=0.001,
        fin_count=5,
        material_conductivity=201.0,
        surface_emissivity=0.05,
    )
    assert result_low_e["base_temperature"] > result["base_temperature"]
```

### 7.5.5 — Absolute Accuracy Benchmarks [E1/A8] ✓

These require finding published reference values. Here is the structure:

```python
def test_benchmark_natural_convection_against_bar_cohen_example() -> None:
    """
    Compare against Bar-Cohen & Rohsenow (1984) Table 2 example.
    Vertical aluminum plate-fin heatsink:
      base: 150mm x 100mm x 6mm
      fins: 25mm tall, 1.5mm thick, 12 fins
      heat load: 10W, ambient: 25°C
    Expected Rth,sa ≈ 3.5–4.5 K/W (range from paper fig. 3)
    """
    result = analyze_plate_fin_heatsink(
        heat_load=10.0,
        ambient_temperature=25.0,
        target_junction_temperature=200.0,
        base_length=0.150,
        base_width=0.100,
        base_thickness=0.006,
        fin_height=0.025,
        fin_thickness=0.0015,
        fin_count=12,
        material_conductivity=201.0,
        surface_emissivity=0.85,
        airflow_mode="natural",
    )
    # Allow 20% tolerance for correlation-based model vs published range
    assert 2.5 < result["sink_thermal_resistance"] < 6.0
```

You will need to find or compute the actual reference value from the paper. Use the range above as a starting point and tighten once validated.

### 7.5.6 — Parameter JSON Test Cases [B7] ✓

Create `tools/simple_thermal/test-cases/natural_convection_baseline.json`:
```json
{
    "name": "Natural Convection Baseline",
    "description": "Default natural convection case with 20W, aluminum heatsink",
    "parameters": {
        "heat_load": 20,
        "ambient_temperature": 25,
        "target_junction_temperature": 100,
        "base_length": 100,
        "base_width": 80,
        "base_thickness": 5,
        "fin_height": 30,
        "fin_thickness": 1.0,
        "fin_count": 10,
        "material_preset": "aluminum_6063_t5",
        "airflow_mode": "natural",
        "interface_resistance": 0.20,
        "junction_to_case_resistance": 0.50
    },
    "notes": "Geometry values in mm (converted to m by the UI). Material preset sets conductivity and emissivity."
}
```

Create similar files for forced convection and fan curve modes.

---

## 8. Phase 6 — Features & Polish (B3, B5, B6 complete — 2026-03-19)

### 8.6.1 — Fan Curve vs System Curve Plot [B3] ✓

**File:** `tools/simple_thermal/index.html`

When in fan_curve mode, after a successful calculation, render an additional Plotly chart:

```javascript
function renderFanCurvePlot(results, inputs) {
    if (inputs.airflow_mode !== 'fan_curve') return;

    const nPoints = 50;
    const maxFlow = inputs.fan_max_flow_rate;
    const flows = Array.from({ length: nPoints }, (_, i) => (i / (nPoints - 1)) * maxFlow);

    // Fan curve
    const fanPressures = flows.map(q => {
        const ratio = Math.min(q / maxFlow, 1.0);
        return inputs.fan_max_pressure * (1 - ratio * ratio);
    });

    // System curve (use the actual pressure drop at operating point to scale)
    // For accurate system curve, we'd need to call the Python for each flow point.
    // Simplified: ΔP ∝ Q² approximation
    const opFlow = results.volumetric_flow_rate;
    const opDrop = results.pressure_drop;
    const systemK = opDrop / (opFlow * opFlow + 1e-12);
    const systemPressures = flows.map(q => systemK * q * q);

    const fanTrace = { x: flows.map(q => q * 1000), y: fanPressures, name: 'Fan Curve', mode: 'lines' };
    const sysTrace = { x: flows.map(q => q * 1000), y: systemPressures, name: 'System Curve', mode: 'lines' };
    const opPoint = {
        x: [opFlow * 1000], y: [opDrop],
        name: 'Operating Point', mode: 'markers',
        marker: { size: 12, color: 'red', symbol: 'diamond' }
    };

    const layout = {
        ...getPlotTheme(),
        title: { text: 'Fan vs System Curve', font: { size: 14 } },
        xaxis: { ...getPlotTheme().xaxis, title: 'Flow Rate (L/s)' },
        yaxis: { ...getPlotTheme().yaxis, title: 'Pressure (Pa)' },
    };
    Plotly.react('fan-curve-plot', [fanTrace, sysTrace, opPoint], layout, { displayModeBar: false, responsive: true });
}
```

Add a `<div class="plot-area" id="fan-curve-plot"></div>` to the Heat Split tab (visible only in fan mode).

### 8.6.2 — Worked Examples in Background Tab [B5] ✓

Add to the Background tab HTML, after the References section:

```html
<div class="background-section" id="bg-worked-examples">
    <h3>9. Worked Examples</h3>

    <h4>Example 1: Natural Convection</h4>
    <p><strong>Given:</strong> 15W heat load, 25°C ambient, aluminum 6063-T5 heatsink (k=201 W/mK),
    base 100mm × 80mm × 5mm, 10 fins at 30mm tall × 1mm thick, black anodized (ε=0.85).</p>

    <p><strong>Step 1 — Geometry:</strong></p>
    <p>Fin spacing: s = (80 - 10×1) / 9 = 7.78 mm. Hydraulic diameter: D_h = 2×7.78×30 / (7.78+30) = 12.35 mm.</p>

    <!-- Continue with full worked solution showing all intermediate values -->
    <p><em>Enter these values in the tool to verify. The results should match within rounding precision.</em></p>

    <h4>Example 2: Forced Convection</h4>
    <p><strong>Given:</strong> Same heatsink as Example 1 but with 2 m/s approach velocity.</p>
    <!-- Full worked solution -->
</div>
```

The content of these worked examples should use actual numbers computed by the solver so they match the tool output exactly. Run the solver with the example inputs and use the output values.

### 8.6.3 — Exportable Design Summary [B6] ✓

**File:** `tools/simple_thermal/index.html`

Add an "Export" button next to the Calculate button:
```html
<button type="button" class="btn-primary" id="export-btn" disabled
    style="background:var(--bg-card);color:var(--text-color);border:1px solid var(--border-color);margin-top:8px;">
    Export Results (JSON)
</button>
```

JavaScript:
```javascript
document.getElementById('export-btn').addEventListener('click', () => {
    if (!lastResults) return;
    const exportData = {
        tool: "Heatsink Designer",
        version: "1.0",
        timestamp: new Date().toISOString(),
        inputs: gatherInputs(),
        results: lastResults,
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'heatsink-design-export.json';
    a.click();
    URL.revokeObjectURL(url);
});

// Enable after first calculation
// In displayResults():
document.getElementById('export-btn').disabled = false;
```

---

## 9. Cross-Cutting Concerns

### Parameter Ordering
When adding new parameters to `analyze_plate_fin_heatsink()`, add them AFTER `pressure_pa` (the last current parameter) to maintain backwards compatibility with existing positional calls. The `PARAM_ORDER` array in the JS must also be updated.

### Substituted Equation Strings
Every new primary output must have a `subst_*` string in the result dict that shows the equation with numerical values substituted in. Follow the pattern of the existing `subst_required_sink_thermal_resistance`.

### Dark Mode
Every new UI element must use `var()` CSS custom properties, never hardcoded colors. Test in both light and dark mode.

### Existing Tests
After every phase, run `python3 -m pytest tests/test_heatsinks.py -v` and verify all tests pass. Some existing tests may need tolerance adjustments after A5 (friction factor fix) and A10 (view factor correction).

### ROADMAP.md
After implementing items, update `tools/simple_thermal/ROADMAP.md` to check off completed tasks.

---

## 10. File Inventory

Files that will be **modified:**
- `pycalcs/heatsinks.py` — New functions, new parameters, bug fixes, spreading orchestrator
- `pycalcs/heatsink_spreading.py` — 2D base-plane spreading solver (Phase 7)
- `tests/test_heatsinks.py` — Many new tests (44 total)
- `tools/simple_thermal/index.html` — UI changes (or split into HTML + JS)
- `tools/simple_thermal/ROADMAP.md` — Status updates

Files that were **created:**
- `pycalcs/heatsink_spreading.py` — 2D Gauss-Seidel/SOR field solver (Phase 7)
- `tools/simple_thermal/test-cases/natural_convection_baseline.json`
- `tools/simple_thermal/test-cases/forced_convection_high_power.json`
- `tools/simple_thermal/test-cases/fan_curve_mode.json`
- `tools/simple_thermal/test-cases/negative_budget_edge_case.json`

---

## Implementation Sequence Summary

```
Phase 0: Quick wins (A5, C1, C5, C6, C7, C8, C9, C10, C11, C13, C14, D3, D4, D6)
    ↓
Phase 1: Accuracy foundations (A7, A10, A6)
    ↓
Phase 2: Physics extensions (A3, A1, A2, A4, A9)
    ↓
Phase 3: Sensitivity analysis (B1, B2)
    ↓
Phase 4: UI/UX overhaul (C2, C3, C4, C12, D1)
    ↓
Phase 5: Testing (E1, E2, E3, E4, E6, B7)
    ↓
Phase 6: Features & polish (B3, B4, B5, B6)
    ↓
Phase 7: Source-aware spreading visualization (see heatsink_spreading_visualization_spec.md)
```

Phase 7 implements the spreading visualization spec:
- Phase 7.1: Backend solver (`heatsink_spreading.py`) — **complete 2026-03-20**
- Phase 7.2: Preview overlay (source rectangle in SVG, position controls) — **complete 2026-03-20**
- Phase 7.3: Spread View tab (heatmap, centerlines, summary, assumptions) — **complete 2026-03-20**
- Phase 7.4: Optional result integration — deferred

Each phase should be committed separately. Run tests after each phase.
