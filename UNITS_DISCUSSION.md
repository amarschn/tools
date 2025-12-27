# Unit System Implementation Discussion

This document captures the architectural options and tradeoffs for implementing user-selectable unit systems across the engineering tools.

## Goal

Allow users to select a unit system (like SolidWorks) from the settings panel:
- **MKS** (SI): m, kg, s, N, Pa
- **MMGS**: mm, g, s, N, MPa (common in mechanical CAD)
- **IPS**: in, lbm, s, lbf, psi (US customary)
- **CGS**: cm, g, s, dyne, erg (scientific, less common)

## Core Principle

**Python calculations should always work in SI (MKS) internally.** This keeps the engineering logic clean, testable, and consistent. The question is where and how to handle conversion to/from the user's preferred display units.

---

## Architectural Options

### Option A: Python-Side Conversion

Each Python module accepts inputs in user's units and returns outputs in user's units.

```python
def calculate_stress(force, area, unit_system='MKS'):
    force_si = convert_to_si(force, 'force', unit_system)
    area_si = convert_to_si(area, 'area', unit_system)

    stress_si = force_si / area_si

    return convert_from_si(stress_si, 'stress', unit_system)
```

| Pros | Cons |
|------|------|
| Self-contained modules | Every Python module needs rewriting |
| Equations can show user's units | Conversion logic scattered across modules |
| | Significant testing burden |

### Option B: Frontend-Side Conversion (JavaScript)

Python always works in SI. JavaScript converts user inputs → SI before calling Python, then converts SI outputs → user units for display.

```javascript
// Before calling Python
const force_si = userForce * UNIT_SYSTEMS[settings.unitSystem].force.toSI;

// After getting results
const stress_display = results.stress / UNIT_SYSTEMS[settings.unitSystem].stress.toSI;
```

| Pros | Cons |
|------|------|
| Python modules unchanged | Two sources of truth (JS + Python) |
| Single conversion layer | Can't pytest the conversion logic |
| Existing tools mostly work | Duplication risk if Python ever needs units |
| Fast runtime conversions | |

### Option C: Python Module via Pyodide

A shared `pycalcs/units.py` module loaded via Pyodide, called for each conversion.

| Pros | Cons |
|------|------|
| Single source of truth | Must wait for Pyodide before any unit operations |
| Python ecosystem (pint, etc.) | Slower - each conversion = Pyodide call |
| Testable with pytest | Heavier for simple operations |
| Docstring/equation integration possible | |

### Option D: Hybrid (Recommended)

**Define conversions in Python, load once into JS, JS does all runtime conversions.**

```python
# pycalcs/units.py
UNIT_SYSTEMS = {
    'MKS': {
        'length': ('m', 1),
        'mass': ('kg', 1),
        'force': ('N', 1),
        'stress': ('Pa', 1),
        'torque': ('N·m', 1),
    },
    'MMGS': {
        'length': ('mm', 0.001),
        'mass': ('g', 0.001),
        'force': ('N', 1),
        'stress': ('MPa', 1e6),
        'torque': ('N·mm', 0.001),
    },
    'IPS': {
        'length': ('in', 0.0254),
        'mass': ('lbm', 0.453592),
        'force': ('lbf', 4.44822),
        'stress': ('psi', 6894.76),
        'torque': ('lbf·in', 0.113),
    },
}

def get_unit_label(quantity: str, system: str) -> str:
    """Get the display unit for a quantity in a given system."""
    return UNIT_SYSTEMS[system][quantity][0]

def get_conversion_factor(quantity: str, system: str) -> float:
    """Get the factor to multiply by to convert TO SI."""
    return UNIT_SYSTEMS[system][quantity][1]
```

```javascript
// After Pyodide loads, grab definitions once
async function loadUnitSystems() {
    const json = await pyodide.runPythonAsync(`
        from pycalcs.units import UNIT_SYSTEMS
        import json
        json.dumps({k: {q: list(v) for q, v in sys.items()}
                    for k, sys in UNIT_SYSTEMS.items()})
    `);
    return JSON.parse(json);
}

// Pure JS for all runtime conversions - fast!
function toSI(value, quantity) {
    const [unit, factor] = UNIT_SYSTEMS[settings.unitSystem][quantity];
    return value * factor;
}

function fromSI(value, quantity) {
    const [unit, factor] = UNIT_SYSTEMS[settings.unitSystem][quantity];
    return value / factor;
}
```

| Benefit | |
|---------|---|
| Single source of truth (Python) | ✓ |
| Fast runtime conversions (JS) | ✓ |
| Python testable | ✓ |
| No Pyodide call per conversion | ✓ |

---

## HTML Implementation Pattern

Tag inputs and outputs with their quantity type:

```html
<!-- Input -->
<div class="input-group">
    <label>Force (<span class="unit-label" data-quantity="force">N</span>)</label>
    <input type="number" id="force" data-quantity="force" value="1000">
</div>

<!-- Output -->
<div class="result-item">
    <span class="label">Stress</span>
    <span class="value" id="result-stress" data-quantity="stress">--</span>
    <span class="unit" data-quantity="stress">Pa</span>
</div>
```

On unit system change:
1. Convert all input values to new system
2. Update all unit labels
3. Recalculate (or convert displayed outputs)

---

## The Equation Display Challenge

### The Problem

If a user works in IPS and sees:
- Input: `Force = 225 lbf`
- Output: `Stress = 14.5 psi`
- Equation: `σ = F/A = 1000 N / 0.01 m² = 100000 Pa`

The numbers don't match. The units don't match. It's jarring.

### Why It's Hard to Fix

Unit-aware equations require:
- Python generates different LaTeX per unit system
- Every intermediate value needs conversion
- Every unit symbol needs substitution (`N·m` → `lbf·in`)
- Compound/derived units are complex
- Testing matrix explodes: 4 systems × N equations × edge cases

### Possible Approaches

#### Approach 1: Symbolic + Final Only

Show symbolic equation, then just final substitution in user's units:

```
σ = F / A
σ = 225 lbf / 15.5 in² = 14.5 psi
```

Skip intermediate steps. Easier to generate, still useful.

#### Approach 2: Honest Labeling

Keep SI equations but label them clearly:

```
Calculation (SI units):
σ = F / A = 1000 N / 0.01 m² = 100000 Pa

Result in your units: 14.5 psi
```

Users understand "this is the real math, here's your answer."

#### Approach 3: User Toggle

Setting: `☐ Show derivations in selected units`

Default off (SI). Power users can enable it, accepting some tools may not support it.

#### Approach 4: Phased Rollout

1. **Phase 1**: Inputs/outputs convert, equations stay SI (labeled)
2. **Phase 2**: Add unit-aware equations to high-value tools incrementally
3. Build equation testing as you go, tool by tool

### Recommendation

Start with **Phase 1 + Honest Labeling**. Gets 80% of UX benefit with 20% of effort.

---

## Impact on Existing Tools

| Change Needed | Effort | Notes |
|---------------|--------|-------|
| Add `data-quantity` to HTML inputs | Low | Attribute per input |
| Add `data-quantity` to HTML outputs | Low | Attribute per output |
| Include shared units.js | Low | One script tag |
| Add unit system to settings panel | Low | Copy from template |
| Define OUTPUT_QUANTITIES map | Medium | Map output keys to quantity types |
| Verify Python uses SI internally | Check | Should already be true |
| Python module changes | None | If already SI-based |

---

## Special Cases

### Temperature

Temperature requires offset conversion, not just scaling:

```javascript
temperature: {
    unit: '°C',
    toSI: (v) => v + 273.15,   // to Kelvin
    fromSI: (v) => v - 273.15  // from Kelvin
}
```

Or keep Celsius as "SI-adjacent" and only convert for Fahrenheit:

```javascript
temperature_celsius: { unit: '°C', toSI: 1 },  // no conversion
temperature_fahrenheit: { unit: '°F', toSI: (v) => (v - 32) * 5/9 }  // to Celsius
```

### Angles

Some tools use degrees in UI but radians internally:

```javascript
angle: { unit: '°', toSI: Math.PI / 180 }  // to radians
```

### Derived/Compound Units

Define explicitly to avoid ambiguity:

```javascript
// Don't try to derive stress from force/area automatically
stress: { unit: 'MPa', toSI: 1e6 },  // explicit

// Torque = force × length, but define explicitly
torque: { unit: 'N·mm', toSI: 0.001 },
```

### Dimensionless Quantities

Safety factors, ratios, coefficients - no conversion needed:

```javascript
dimensionless: { unit: '', toSI: 1 }
```

---

## Open Questions

1. **Which unit systems to support initially?** MKS, MMGS, IPS seem essential. CGS?

2. **Tool-specific defaults?** Should bolt-torque default to MMGS, thermal tools to MKS?

3. **Persistence scope?** Global setting across all tools, or per-tool preference?

4. **Docstring units?** Accept mismatch with display, or make docstrings unit-agnostic?

5. **Existing unit converter tool?** How does this relate to `tools/unit-converter/`?

---

## References

- SolidWorks unit system approach
- ISO 80000 (SI units)
- NIST SP 811 (Guide for the Use of the International System of Units)
- Python `pint` library for inspiration on quantity handling
