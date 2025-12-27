# Advanced Example Tool Template

This is the **comprehensive template** for complex engineering tools. Use this template when building tools that require:

- Multiple input sections or many parameters
- Safety factor analysis and status assessment
- Multiple visualization tabs
- Detailed derivation panels
- Database-driven dropdowns
- Settings panel with user preferences
- Dark mode and theme support

## When to Use This Template

Use `example_tool_advanced` instead of `example_tool` when your tool has:

| Criteria | Use Basic | Use Advanced |
|----------|-----------|--------------|
| Number of inputs | 3-5 | 6+ |
| Needs safety factors | No | Yes |
| Multiple charts | No | Yes |
| Database lookups | Simple | Complex cascading |
| Derivation depth | Basic | Multi-step |
| User preferences | No | Yes |
| Theme support | No | Yes |

## Features Demonstrated

### 1. Loading Overlay
Full-screen overlay with spinner during Pyodide initialization. Theme-aware (works with dark mode).

### 2. Settings Panel
Slide-out panel with comprehensive user preferences:
- **Auto-calculate**: Update results as inputs change (with 350ms debouncing)
- **Show derivations by default**: Auto-expand derivation panels
- **Show gauge explainers**: Auto-expand safety gauge details
- **Auto-update charts**: Refresh charts when inputs change
- **Theme**: Light, Dark, or System (follows OS preference)
- **Density**: Comfortable or Compact layout
- **Precision**: 2, 3, or 4 decimal places in results
- **Reset to defaults**: One-click restore of default settings
- **LocalStorage persistence**: Settings persist across sessions

### 3. Dark Mode Support
Complete dark theme with CSS variables. Three modes:
- Light: Clean white interface
- Dark: Dark gray interface for low-light conditions
- System: Automatically follows OS light/dark preference

### 4. Material Database Dropdown
Pre-populated dropdown from Python database. No raw value entry needed.

### 5. Advanced Inputs Toggle
Hides infrequently-used parameters by default. Click to reveal.

### 6. Slider with Live Display
Visual parameter adjustment with real-time value feedback and inline tooltips.

### 7. Clickable Result Cards
Click any result to expand its derivation panel. Only one panel open at a time.

### 8. Safety Factor Gauges with Explainers
Visual progress bars with:
- Color-coded status (green/amber/red)
- Threshold markers showing design requirements
- Numeric SF values
- **Clickable explainer panels** with equations, values, and guidance

### 9. Status Banner
Overall assessment with:
- Status icon and title
- Summary message
- Actionable recommendations list

### 10. Interactive Charts (Theme-aware)
Plotly.js charts with:
- Response curve visualization
- Sensitivity analysis (SF vs parameter)
- Chart explanations
- **Automatic theme adaptation** for dark mode

### 11. Comprehensive Background Tab
- Table of contents with anchor links
- Numbered sections
- Equation cards with variable legends
- Callout boxes (info/warning/danger/success)
- References section

### 12. Compact Density Mode
Alternative compact layout with:
- Reduced padding on cards
- Smaller text sizes
- Condensed result displays
- Tighter spacing throughout

## Corresponding Python Module

The `pycalcs/example_advanced.py` module demonstrates:

```python
# Database-driven lookups
MATERIALS = { "Standard Alloy": {...}, ... }
def get_material_properties(name): ...

# Visualization data generation
def generate_response_curve(...) -> Dict[str, List[float]]: ...
def generate_parameter_sensitivity(...) -> Dict[str, List[float]]: ...

# Comprehensive return structure
return {
    # Primary outputs
    "primary_result": ...,
    "secondary_result": ...,

    # Safety assessment
    "safety_factor_a": ...,
    "safety_factor_b": ...,
    "status": "acceptable" | "marginal" | "unacceptable",
    "recommendations": [...],

    # Substituted equations (for derivation panels)
    "subst_primary_result": "LaTeX string with values",

    # Visualization data
    "response_curve": {...},
    "sensitivity_data": {...},
}
```

## Customization Checklist

When adapting this template:

1. [ ] Update `TOOL_MODULE_NAME` and `TOOL_FUNCTION_NAME` in the script config
2. [ ] Update `STORAGE_KEY` to a unique identifier for your tool
3. [ ] Replace material dropdown with your database options
4. [ ] Update input fields to match your function parameters
5. [ ] Match input IDs to docstring parameter names for tooltip population
6. [ ] Update result cards and derivation panels for your outputs
7. [ ] Modify chart plotting functions for your data structure
8. [ ] Update Background tab content for your domain
9. [ ] Configure default settings appropriate for your tool
10. [ ] Test tooltip population from docstring
11. [ ] Verify all derivation panels populate correctly
12. [ ] Test dark mode appearance on all components
13. [ ] Test auto-calculate debouncing behavior

## Settings JavaScript Pattern

The settings system uses this pattern:

```javascript
// Storage key for localStorage
const STORAGE_KEY = 'my-tool-settings';

// Default settings object
const defaultSettings = {
    autoCalc: false,
    showDerivations: false,
    showGauges: false,
    autoCharts: true,
    theme: 'system',
    density: 'comfortable',
    precision: 3
};

// Current settings (loaded from localStorage or defaults)
let settings = { ...defaultSettings };

// Core functions
function loadSettings() { ... }    // Load from localStorage
function saveSettings() { ... }    // Save to localStorage
function applySettings() { ... }   // Apply to DOM
function handleSettingChange(key, value) { ... }
```

## File Structure

```
tools/example_tool_advanced/
├── index.html          # This template
└── README.md           # This file

pycalcs/
└── example_advanced.py # Corresponding Python module
```

## Related Documentation

- `AGENTS.md` - Full patterns documentation
- `DESIGN.md` - CSS specifications for all components
- `tools/example_tool_settings/` - Simpler settings panel example
- `tools/bolt-torque_claude/` - Production example of these patterns
