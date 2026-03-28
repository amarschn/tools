# Heatsink Sensitivity Analysis Plan

## Purpose
Capture a deferred implementation plan for adding parameter sweep and trade-space analysis to the heatsink designer without expanding the current rewrite scope immediately.

## Why Separate Sensitivity Modes
The two analysis modes answer different engineering questions and should stay separate in the UI:

- **1D Sweep** answers: "Which single parameter matters most, and in what direction?"
- **2D Trade Space** answers: "What regions are feasible or attractive when two parameters interact?"

Keeping them separate supports progressive simplicity. The main results flow stays focused on the baseline solve, while deeper exploration remains available on demand.

## Proposed UI Structure
Add the following tabs after the baseline solver is stable:

- `Results`
- `Temperature Ladder`
- `Heat Split`
- `1D Sweep`
- `2D Trade Space`
- `Background`

Both sweep tabs should remain disabled until a baseline calculation has been completed successfully.

## Architecture
All sweep logic should live in Python, not JavaScript. The frontend should remain thin and data-driven.

### Proposed Python API
Add the following functions to `pycalcs/heatsinks.py`:

- `get_heatsink_sweep_metadata() -> dict`
- `run_heatsink_1d_sweep(...) -> dict`
- `run_heatsink_2d_contour(...) -> dict`

### Metadata Responsibilities
`get_heatsink_sweep_metadata()` should be the single source of truth for:

- Sweepable input parameters
- Labels and units
- Categories such as thermal, geometry, and airflow
- Allowed ranges and default spans
- Linear vs. log axis behavior
- Valid airflow modes for each parameter
- Output metrics available for plotting

Suggested metadata shape:

```python
{
    "parameters": {
        "fin_height": {
            "label": "Fin Height",
            "unit": "m",
            "category": "geometry",
            "default_span": [0.5, 1.5],
            "min": 0.002,
            "max": 0.12,
            "scale": "linear",
            "modes": ["natural", "forced", "fan_curve"],
        },
    },
    "outputs": {
        "sink_thermal_resistance": {
            "label": "Sink Thermal Resistance",
            "unit": "K/W",
            "goal": "minimize",
        },
    },
}
```

### 1D Sweep Return Shape
`run_heatsink_1d_sweep(...)` should return:

- `x_values`
- `series`
- `baseline_x`
- `baseline_outputs`
- `valid_mask`
- `warnings`
- `crossings`

### 2D Trade Space Return Shape
`run_heatsink_2d_contour(...)` should return:

- `x_values`
- `y_values`
- `z_values`
- `valid_mask`
- `baseline_point`
- `best_point`
- `constraint_reason_grid` (optional)

## Frontend Model
Keep a small shared state object in the page script:

```javascript
const sweepState = {
  metadata: null,
  baselineInputs: null,
  baselineResults: null,
  oneD: null,
  twoD: null,
};
```

Recommended frontend functions:

- `populateSweepControls(metadata, baselineInputs)`
- `runOneDSweep()`
- `runTwoDContour()`
- `renderSweepPlot(...)`
- `renderContourPlot(...)`

The frontend should avoid parameter-specific branching wherever possible and instead render controls from metadata.

## Recommended v1 Sweep Parameters
These are the strongest initial candidates for sensitivity analysis:

- `fin_height`
- `fin_thickness`
- `fin_count`
- `base_thickness`
- `base_length`
- `base_width`
- `heat_load`
- `ambient_temperature`
- `surface_emissivity`
- `approach_velocity` or `volumetric_flow_rate`, depending on cooling mode

## Deferred for Later
Do not include these in the first sensitivity release:

- Categorical mode changes inside sweeps
- Fan-curve parameter sweeps
- Broad multi-parameter optimization features
- Poorly constrained coupled-variable sweeps

## UX Guidance
### 1D Sweep
This tab should stay fast and focused:

- One parameter selector
- Simple preset ranges such as `±20%`, `±50%`, and `Custom`
- One output metric at a time
- A single primary line chart
- Baseline and best-value markers
- Short summary cards for change magnitude and any limit crossing

### 2D Trade Space
This tab should emphasize interaction and feasibility:

- One X-parameter selector
- One Y-parameter selector
- One output metric at a time
- Sensible grid resolution controls such as `20x20`, `35x35`, and `50x50`
- Contour or heatmap plot
- Baseline marker
- Best feasible point marker
- Optional infeasible-region overlay

## Implementation Order
1. Add sweep metadata in `pycalcs/heatsinks.py`.
2. Implement and test `run_heatsink_1d_sweep(...)`.
3. Build the `1D Sweep` tab and plotting flow.
4. Add `run_heatsink_2d_contour(...)`.
5. Build the `2D Trade Space` tab and feasibility overlays.

## Testing Expectations
Sensitivity analysis should be tested as rigorously as the baseline solver:

- Unit tests for metadata integrity
- Deterministic tests for sweep outputs and baseline markers
- Monotonicity and physics sanity tests where appropriate
- Invalid-range and invalid-geometry handling tests
- UI checks to ensure sweep tabs are gated behind a valid baseline solve
