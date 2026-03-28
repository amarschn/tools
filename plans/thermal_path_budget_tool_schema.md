# Generic Thermal Path Tool API & Schema Spec

> **Purpose:** Define the canonical data schema, backend API contract, validation rules, and solved-result payload for the future generic thermal-path / resistance-network tool. This document is the coding-adjacent follow-on to [plans/thermal_path_budget_tool_spec.md](/Users/drew/code/tools/plans/thermal_path_budget_tool_spec.md).

---

## 1. Scope of This Document

This document answers the implementation questions left open by the product spec:

- what the canonical network schema should be,
- what `pycalcs/thermal_networks.py` should accept,
- what it should return,
- how the frontend should consume the payload,
- and what should be validated before solving.

This is a **backend/frontend contract** document.

It is intentionally narrower than the product spec.

---

## 2. Design Principles

### 2.1 Canonical graph in the backend

Even if the frontend uses templates, forms, or a staged editor, the backend should solve one canonical representation:

- nodes,
- segments,
- solve mode,
- constraints,
- options.

The frontend may use convenience shapes internally, but it should translate them into this canonical model before calling Python.

### 2.2 One solved payload for all disclosures

The same solved payload should drive:

- summary cards,
- network diagram,
- node table,
- segment table,
- contribution chart,
- derivation panels,
- export.

No separate hand-authored explanation objects should exist outside the solved payload.

### 2.3 SI-first internal units

The backend schema should use a single internal unit system:

- temperature: `degC`
- temperature difference: `K` or `degC`
- heat flow: `W`
- thermal resistance: `K/W`
- area: `m^2`
- thickness / length: `m`
- conductivity: `W/(m*K)`

The frontend can expose friendlier units, but it should normalize to this schema before solving.

### 2.4 Explicit, not magical

Every computed resistance should preserve:

- how it was defined,
- what inputs produced it,
- what equation was used,
- and what its resolved numeric value is.

That metadata is required for progressive disclosure and export.

---

## 3. Recommended Python Module and Functions

The future backend should live primarily in:

- `pycalcs/thermal_networks.py`

Recommended public functions for MVP:

```python
def validate_thermal_network_model(model: dict[str, object]) -> dict[str, object]:
    ...

def solve_thermal_network(model: dict[str, object]) -> dict[str, object]:
    ...

def generate_thermal_network_sensitivity(
    model: dict[str, object],
    segment_ids: list[str],
    variation_fraction: float = 0.2,
    points: int = 21,
) -> dict[str, object]:
    ...
```

### Function responsibilities

`validate_thermal_network_model()`
- schema validation,
- connectivity checks,
- solve-mode-specific checks,
- warnings for questionable but not invalid models.

`solve_thermal_network()`
- canonical solve entry point,
- resolves segment resistances,
- solves node temperatures,
- builds summary / diagnostics / derivations / diagram payload.

`generate_thermal_network_sensitivity()`
- optional helper for the Results tab,
- sweeps one segment at a time,
- returns lightweight plotting data keyed by segment id.

### MVP rule

Do **not** make the frontend call a grab bag of small helper functions for each panel.

The main page should call one solve function and, optionally, one sensitivity function.

---

## 4. Top-Level Model Schema

The canonical input model should use this shape:

```python
{
    "schema_version": "1.0",
    "template_id": "package_to_sink",
    "analysis_mode": "solve_temperatures",
    "network": {
        "id": "main_network",
        "label": "Package to sink budget",
        "notes": "",
        "nodes": [...],
        "segments": [...],
    },
    "solve_target": {...},
    "options": {...},
}
```

### Top-level fields

`schema_version : str`
- Required.
- Start with `"1.0"`.

`template_id : str`
- Required.
- Identifies the frontend template or `"custom"`.
- Used for reporting and applicability messaging, not for solving.

### Recommended MVP `template_id` values

The v1 frontend should standardize on this template set:

- `"simple_chain"`
- `"package_to_sink"`
- `"housing_wall_path"`
- `"dual_path_to_ambient"`
- `"custom"`

Validation should reject unknown template ids in MVP unless the implementation explicitly feature-flags them.

`analysis_mode : str`
- Required.
- Allowed MVP values:
  - `"solve_temperatures"`
  - `"solve_required_segment"`

### Frontend workflow mapping

The product may expose a broader set of user-facing workflows, but they should map to the canonical backend modes like this:

- `Analyze temperatures` -> `"solve_temperatures"`
- `Size one segment for a target` -> `"solve_required_segment"`
- `Budget required sink resistance` -> `"solve_required_segment"` with the sink-to-ambient segment selected as the unknown
- `Compare two path options` -> two separate canonical solves in the frontend, not a third backend mode

`network : dict`
- Required.
- Holds the canonical nodes and segments.

`solve_target : dict`
- Optional for `"solve_temperatures"`.
- Required for `"solve_required_segment"`.

`options : dict`
- Optional.
- Controls reporting, sensitivity, and diagnostics.

---

## 5. Node Schema

Each node must conform to:

```python
{
    "id": "junction",
    "label": "Junction",
    "kind": "internal",
    "heat_input_w": 25.0,
    "fixed_temperature_c": None,
    "max_temperature_c": 125.0,
    "min_temperature_c": None,
    "notes": "",
    "tags": ["source", "limit-bearing"],
}
```

### Node fields

`id : str`
- Required.
- Stable identifier.
- Unique within the network.

`label : str`
- Required.
- User-facing display name.

`kind : str`
- Required.
- Allowed MVP values:
  - `"internal"`
  - `"boundary"`

`heat_input_w : float`
- Optional.
- Default `0.0`.
- Positive means heat is injected into the node.
- Negative is allowed only if the UI intentionally supports a heat sink/source convention; otherwise reject it in MVP.

`fixed_temperature_c : float | None`
- Optional.
- Required for at least one node in the network.
- Boundary nodes typically use this.

`max_temperature_c : float | None`
- Optional.
- Used for status, margin, and required-segment sizing.

`min_temperature_c : float | None`
- Optional.
- Reserved for future use; allowed but ignored in MVP unless explicitly supported.

`notes : str`
- Optional.

`tags : list[str]`
- Optional.
- Used by the frontend for display and routing hints.

### Node rules

- At least one node must have `fixed_temperature_c`.
- A node may have both `heat_input_w` and `max_temperature_c`.
- A node with `fixed_temperature_c` is not solved as an unknown temperature.
- Node ids must be unique.
- The user-facing MVP should expose exactly one positive `heat_input_w` node and exactly one fixed-temperature boundary node.

---

## 6. Segment Schema

Each segment must conform to:

```python
{
    "id": "r_cs",
    "label": "Case to sink interface",
    "from_node_id": "case",
    "to_node_id": "sink",
    "category": "interface",
    "mode": "tim_conductivity",
    "inputs": {...},
    "notes": "",
    "tags": ["tim"],
}
```

### Segment fields

`id : str`
- Required.
- Stable identifier.
- Unique within the network.

`label : str`
- Required.

`from_node_id : str`
- Required.
- Must reference an existing node id.

`to_node_id : str`
- Required.
- Must reference an existing node id.

`category : str`
- Optional.
- Recommended MVP values:
  - `"junction_to_case"`
  - `"interface"`
  - `"conduction"`
  - `"sink_to_ambient"`
  - `"parallel_path"`
  - `"other"`

`mode : str`
- Required.
- Defines how the segment resistance is resolved.

`inputs : dict`
- Required.
- Shape depends on `mode`.

`notes : str`
- Optional.

`tags : list[str]`
- Optional.

### Segment rules

- Segment ids must be unique.
- `from_node_id` and `to_node_id` must differ.
- Multiple segments between the same node pair are allowed.
- Segment direction is for labeling only; the solved heat flow may be positive or negative relative to that direction.

---

## 7. Segment Modes and Mode-Specific Input Schema

The solver should resolve every segment to a scalar thermal resistance `R_segment` in `K/W`.

The original defining inputs must still be preserved in the solved payload.

### 7.1 `direct`

Use when the user already knows the thermal resistance.

```python
{
    "mode": "direct",
    "inputs": {
        "resistance_k_per_w": 0.45
    }
}
```

Required fields:

- `resistance_k_per_w : float`

Validation:

- must be `> 0`

### 7.2 `tim_area_normalized`

Use for datasheet-style TIM impedance values.

```python
{
    "mode": "tim_area_normalized",
    "inputs": {
        "impedance_k_cm2_per_w": 0.35,
        "contact_area_m2": 0.0004
    }
}
```

Required fields:

- `impedance_k_cm2_per_w : float`
- `contact_area_m2 : float`

Equation:

Equation (1)
`R_theta = Z_area / A_contact`

Variable legend:
- `R_theta`: resolved segment thermal resistance, `K/W`
- `Z_area`: area-normalized impedance, `K*cm^2/W`
- `A_contact`: contact area converted to `cm^2`

Validation:

- both values must be `> 0`

### 7.3 `tim_conductivity`

Use when the user knows bondline thickness and conductivity.

```python
{
    "mode": "tim_conductivity",
    "inputs": {
        "bondline_thickness_m": 0.0002,
        "conductivity_w_per_mk": 3.0,
        "contact_area_m2": 0.0004
    }
}
```

Required fields:

- `bondline_thickness_m : float`
- `conductivity_w_per_mk : float`
- `contact_area_m2 : float`

Equation:

Equation (2)
`R_theta = t / (k A)`

Variable legend:
- `R_theta`: resolved segment thermal resistance, `K/W`
- `t`: layer thickness, `m`
- `k`: thermal conductivity, `W/(m*K)`
- `A`: contact area, `m^2`

Validation:

- all values must be `> 0`

### 7.4 `simple_conduction_slab`

Use for a solid layer or bar approximated as 1D conduction.

```python
{
    "mode": "simple_conduction_slab",
    "inputs": {
        "thickness_m": 0.005,
        "conductivity_w_per_mk": 205.0,
        "cross_section_area_m2": 0.0009
    }
}
```

Required fields:

- `thickness_m : float`
- `conductivity_w_per_mk : float`
- `cross_section_area_m2 : float`

Equation:

Equation (3)
`R_theta = L / (k A)`

Variable legend:
- `R_theta`: resolved segment thermal resistance, `K/W`
- `L`: conduction length, `m`
- `k`: thermal conductivity, `W/(m*K)`
- `A`: cross-sectional area normal to heat flow, `m^2`

Validation:

- all values must be `> 0`

### 7.5 `solved_unknown`

Use only in `"solve_required_segment"` mode for the one segment being sized.

```python
{
    "mode": "solved_unknown",
    "inputs": {
        "initial_guess_k_per_w": 1.0,
        "lower_bound_k_per_w": 0.001,
        "upper_bound_k_per_w": 20.0
    }
}
```

Required fields:

- `initial_guess_k_per_w : float`

Optional fields:

- `lower_bound_k_per_w : float`
- `upper_bound_k_per_w : float`

Validation:

- only one segment may use this mode in MVP
- bounds, if given, must satisfy `0 < lower < upper`

### 7.6 Deferred modes

Do not support these in MVP, but reserve room for them:

- `radiation_linearized`
- `datasheet_lookup`
- `temperature_dependent`
- `nonlinear_contact`

---

## 8. Solve Target Schema

`solve_target` is ignored in `"solve_temperatures"` mode unless limits are present for reporting.

It is required in `"solve_required_segment"` mode.

Recommended shape:

```python
{
    "target_node_id": "junction",
    "target_type": "max_temperature",
    "target_value_c": 110.0,
    "unknown_segment_id": "r_sa"
}
```

### Solve target fields

`target_node_id : str`
- Required for `"solve_required_segment"`.
- Must reference an existing node.

`target_type : str`
- Required for `"solve_required_segment"`.
- MVP allowed value:
  - `"max_temperature"`

`target_value_c : float`
- Required for `"solve_required_segment"`.

`unknown_segment_id : str`
- Required for `"solve_required_segment"`.
- Must reference the only segment using `mode == "solved_unknown"`.

### MVP rule

Only one controlling limit should be sized against in the first implementation.

If other node limits exist, they should be reported as secondary checks after the solve.

---

## 9. Options Schema

Recommended shape:

```python
{
    "include_derivations": True,
    "include_diagram_payload": True,
    "include_equivalent_groups": True,
    "sensitivity_segment_ids": ["r_cs", "r_sa"],
    "sensitivity_variation_fraction": 0.2,
    "sensitivity_points": 21
}
```

### Option fields

`include_derivations : bool`
- Optional.
- Default `True`.

`include_diagram_payload : bool`
- Optional.
- Default `True`.

`include_equivalent_groups : bool`
- Optional.
- Default `True`.

`sensitivity_segment_ids : list[str]`
- Optional.
- Used only by the sensitivity helper.

`sensitivity_variation_fraction : float`
- Optional.
- Default `0.2`.

`sensitivity_points : int`
- Optional.
- Default `21`.

---

## 10. Validation Contract

`validate_thermal_network_model()` should return:

```python
{
    "is_valid": True,
    "errors": [],
    "warnings": [],
    "normalized_model": {...}
}
```

### Hard errors

These should make the model unsolvable:

- missing required top-level fields
- unknown `template_id` for the supported MVP template library
- duplicate node ids
- duplicate segment ids
- segment references nonexistent node ids
- zero or negative resolved resistance inputs
- no fixed-temperature node
- more than one fixed-temperature node in the user-facing MVP
- more than one positive heat-input node in the user-facing MVP
- disconnected network
- more than one `solved_unknown` segment in MVP
- `"solve_required_segment"` without a valid `solve_target`
- `unknown_segment_id` mismatch

### Warnings

These should allow solving but surface caution:

- no node temperature limits defined
- very large resistance ratios that may make one branch negligible
- model likely better served by another tool
- conduction slab used where spreading effects may dominate
- boundary node marked as internal or vice versa
- custom topology used where a standard template may be clearer

### Normalization

The validation step should also:

- fill optional defaults,
- coerce absent `heat_input_w` to `0.0`,
- coerce absent `notes` to `""`,
- return a normalized model ready for solving.

---

## 11. Core Solver Output Schema

`solve_thermal_network()` should return one normalized payload that the frontend can render directly.

Recommended top-level shape:

```python
{
    "status": "acceptable",
    "mode": "solve_temperatures",
    "summary": {...},
    "diagnosis": {...},
    "applicability": {...},
    "reporting_basis": {...},
    "nodes": [...],
    "segments": [...],
    "parallel_groups": [...],
    "diagram_payload": {...},
    "derivations": [...],
    "warnings": [...],
    "recommendations": [...],
    "assumptions": [...],
    "normalized_model": {...}
}
```

### Top-level fields

`status : str`
- Overall outcome.
- Recommended MVP values:
  - `"acceptable"`
  - `"marginal"`
  - `"unacceptable"`
  - `"invalid"`

`mode : str`
- Echo of the input `analysis_mode`.

`summary : dict`
- High-level result fields for headline cards.

`diagnosis : dict`
- Action-oriented interpretation for the default Results view.

`applicability : dict`
- Model-fit assessment, caution flags, and routing guidance.

`reporting_basis : dict`
- Explicit conventions used for headline values such as effective total resistance and contribution percentages.

`nodes : list[dict]`
- Solved node results.

`segments : list[dict]`
- Solved segment results.

`parallel_groups : list[dict]`
- Optional equivalent-group summaries for derivations and display.

`diagram_payload : dict`
- Optional graph payload for the UI.

`derivations : list[dict]`
- Canonical derivation objects keyed by subject.

`warnings : list[str]`
- Model and solve warnings.

`recommendations : list[str]`
- Action-oriented suggestions.

`assumptions : list[str]`
- Short explicit modeling assumptions used in this solve.

`normalized_model : dict`
- Echo of the normalized input model.
- Important for export and debugging.

---

## 12. Summary Payload

Recommended `summary` shape:

```python
{
    "hottest_node_id": "junction",
    "hottest_node_label": "Junction",
    "hottest_temperature_c": 102.4,
    "reference_node_id": "ambient",
    "reference_temperature_c": 40.0,
    "total_temperature_rise_c": 62.4,
    "total_applied_heat_w": 25.0,
    "effective_total_resistance_k_per_w": 2.496,
    "dominant_segment_id": "r_sa",
    "dominant_segment_label": "Sink to ambient",
    "dominant_segment_contribution_pct": 61.3,
    "controlling_limit_node_id": "junction",
    "margin_to_limit_c": 7.6,
    "sized_unknown_segment_id": None,
    "sized_unknown_resistance_k_per_w": None
}
```

### Required summary fields

- `hottest_node_id`
- `hottest_node_label`
- `hottest_temperature_c`
- `reference_node_id`
- `reference_temperature_c`
- `total_temperature_rise_c`
- `total_applied_heat_w`
- `effective_total_resistance_k_per_w`
- `dominant_segment_id`
- `dominant_segment_label`
- `dominant_segment_contribution_pct`

### Conditional summary fields

- `controlling_limit_node_id`
- `margin_to_limit_c`
- `sized_unknown_segment_id`
- `sized_unknown_resistance_k_per_w`

### Summary reporting convention

For MVP, define:

`effective_total_resistance_k_per_w = (hottest_temperature_c - reference_temperature_c) / total_applied_heat_w`

Because the user-facing MVP is restricted to one positive heat-input node and one fixed-temperature reference boundary node, this headline value remains unambiguous.

If future revisions relax those constraints, the payload should either:

- document the convention used in `reporting_basis`, or
- set the headline effective resistance to `None` when no honest single number exists.

### Diagnosis payload

Recommended shape:

```python
{
    "dominant_segment_id": "r_sa",
    "dominant_segment_label": "Sink to ambient",
    "dominant_segment_delta_t_c": 38.2,
    "dominant_segment_contribution_pct": 61.3,
    "first_improvement_target_id": "r_sa",
    "first_improvement_target_label": "Sink to ambient",
    "first_improvement_reason": "Largest contribution to total temperature rise.",
    "required_improvement_summary": "Reduce sink-to-ambient resistance to 1.50 K/W or below to meet the selected limit."
}
```

Recommended diagnosis fields:

- `dominant_segment_id`
- `dominant_segment_label`
- `dominant_segment_delta_t_c`
- `dominant_segment_contribution_pct`
- `first_improvement_target_id`
- `first_improvement_target_label`
- `first_improvement_reason`

Conditional diagnosis fields:

- `required_improvement_summary`

### Applicability payload

Recommended shape:

```python
{
    "status": "good_fit",
    "score_label": "Good fit",
    "flags": [],
    "routing_suggestion": None
}
```

Recommended applicability fields:

- `status`
- `score_label`
- `flags`
- `routing_suggestion`

Recommended MVP `status` values:

- `"good_fit"`
- `"use_with_caution"`
- `"better_in_other_tool"`

### Reporting basis payload

Recommended shape:

```python
{
    "reference_boundary_node_id": "ambient",
    "positive_heat_input_node_ids": ["junction"],
    "effective_total_resistance_definition": "(T_hottest - T_ref) / Q_total_positive",
    "contribution_definition": "100 * abs(delta_t_c) / total_temperature_rise_c"
}
```

This object prevents the frontend or exported reports from implying conventions that were never actually defined.

---

## 13. Solved Node Payload

Each solved node should use:

```python
{
    "id": "junction",
    "label": "Junction",
    "kind": "internal",
    "temperature_c": 102.4,
    "fixed_temperature_c": None,
    "heat_input_w": 25.0,
    "net_outgoing_heat_w": 25.0,
    "max_temperature_c": 110.0,
    "margin_to_max_c": 7.6,
    "status": "acceptable",
    "connected_segment_ids": ["r_jc"],
    "notes": "",
    "tags": ["source", "limit-bearing"]
}
```

### Required node result fields

- `id`
- `label`
- `kind`
- `temperature_c`
- `fixed_temperature_c`
- `heat_input_w`
- `net_outgoing_heat_w`
- `connected_segment_ids`

### Optional node result fields

- `max_temperature_c`
- `margin_to_max_c`
- `status`
- `notes`
- `tags`

---

## 14. Solved Segment Payload

Each solved segment should use:

```python
{
    "id": "r_cs",
    "label": "Case to sink interface",
    "from_node_id": "case",
    "to_node_id": "sink",
    "category": "interface",
    "mode": "tim_conductivity",
    "resolved_resistance_k_per_w": 0.167,
    "heat_flow_w": 25.0,
    "delta_t_c": 4.18,
    "contribution_pct": 6.7,
    "direction": "from_to",
    "is_solved_unknown": False,
    "inputs": {...},
    "notes": "",
    "tags": ["tim"],
    "subst_resistance": "...",
    "subst_delta_t": "..."
}
```

### Required segment result fields

- `id`
- `label`
- `from_node_id`
- `to_node_id`
- `category`
- `mode`
- `resolved_resistance_k_per_w`
- `heat_flow_w`
- `delta_t_c`
- `contribution_pct`
- `direction`
- `is_solved_unknown`
- `inputs`

### Direction field

Recommended values:

- `"from_to"`
- `"to_from"`
- `"zero"`

This lets the frontend render arrows or labels without re-deriving direction.

### Contribution definition

For MVP, define:

`contribution_pct = 100 * abs(delta_t_c) / total_temperature_rise_c`

If multiple heat sources exist later, this may require a more careful definition; the payload should document what convention was used.

---

## 15. Parallel Group Payload

Parallel branches are common enough that the frontend should not need to reconstruct them heuristically.

Recommended shape:

```python
{
    "id": "pg_case_to_ambient",
    "entry_node_id": "case",
    "exit_node_id": "ambient",
    "segment_ids": ["r_case_sink_path", "r_case_pcb_path"],
    "equivalent_resistance_k_per_w": 1.23,
    "heat_split_w": {
        "r_case_sink_path": 18.0,
        "r_case_pcb_path": 7.0
    },
    "subst_equivalent_resistance": "..."
}
```

### MVP note

If exact automatic parallel grouping proves too much for the first implementation, this object may initially be omitted for pure series models and added once simple branch templates are supported.

---

## 16. Diagram Payload

The frontend needs graph data, not a pre-rendered SVG.

Recommended shape:

```python
{
    "nodes": [
        {
            "id": "junction",
            "label": "Junction",
            "temperature_c": 102.4,
            "rank": 0,
            "is_reference": False,
            "is_hottest": True
        }
    ],
    "edges": [
        {
            "id": "r_jc",
            "from_node_id": "junction",
            "to_node_id": "case",
            "resolved_resistance_k_per_w": 0.4,
            "delta_t_c": 10.0,
            "heat_flow_w": 25.0,
            "branch_group_id": None
        }
    ],
    "reference_node_id": "ambient",
    "primary_hot_path_node_ids": ["junction", "case", "sink", "ambient"]
}
```

### Diagram rules

- `rank` should be a simple topological display hint, not a pixel position.
- The frontend owns layout and styling.
- The backend owns the graph content and solved values.

---

## 17. Derivation Payload

Derivations need a canonical structure so the Results and Math tabs stay consistent.

Recommended shape:

```python
{
    "id": "drv_r_cs_resistance",
    "subject_type": "segment",
    "subject_id": "r_cs",
    "result_key": "resolved_resistance_k_per_w",
    "title": "Case to sink interface resistance",
    "equation_number": "Equation (2)",
    "equation_latex": "R_\\theta = \\frac{t}{kA}",
    "variable_legend": [
        {"symbol": "R_\\theta", "meaning": "thermal resistance", "units": "K/W"},
        {"symbol": "t", "meaning": "bondline thickness", "units": "m"},
        {"symbol": "k", "meaning": "thermal conductivity", "units": "W/(m*K)"},
        {"symbol": "A", "meaning": "contact area", "units": "m^2"}
    ],
    "substitution_latex": "R_\\theta = \\frac{0.0002}{3.0 \\times 0.0004} = 0.167\\,\\mathrm{K/W}",
    "result_value": 0.167,
    "result_units": "K/W",
    "depends_on": [],
    "step_type": "segment_resistance"
}
```

### Required derivation fields

- `id`
- `subject_type`
- `subject_id`
- `result_key`
- `title`
- `equation_number`
- `equation_latex`
- `variable_legend`
- `substitution_latex`
- `result_value`
- `result_units`
- `depends_on`
- `step_type`

### Supported subject types

- `"summary"`
- `"node"`
- `"segment"`
- `"parallel_group"`

### Why this matters

This structure allows:

- clickable result cards,
- subject-linked drilldown,
- exportable math reports,
- and a single source of truth for equations and substituted values.

---

## 18. Sensitivity Payload

`generate_thermal_network_sensitivity()` should return data keyed by segment id.

Recommended shape:

```python
{
    "series": [
        {
            "segment_id": "r_sa",
            "segment_label": "Sink to ambient",
            "x_resistance_k_per_w": [1.6, 1.7, 1.8],
            "y_hottest_temperature_c": [97.1, 99.8, 102.4],
            "nominal_resistance_k_per_w": 1.8,
            "nominal_hottest_temperature_c": 102.4
        }
    ]
}
```

### MVP rule

The sensitivity helper should vary one segment at a time while holding all others fixed.

That is enough for a first useful diagnosis view.

---

## 19. Frontend Usage Contract

The frontend should follow this flow:

1. Collect inputs from the staged editor or template form.
2. Convert them into the canonical model schema.
3. Call `validate_thermal_network_model()`.
4. If invalid, show errors and stop.
5. If valid, call `solve_thermal_network()` with the normalized model.
6. Render all result views from the returned payload.
7. Optionally call `generate_thermal_network_sensitivity()` using the same normalized model.

If the UI offers `Compare two path options`, it should perform steps 1-7 twice using two independent canonical models, then render the comparison from the two solved payloads.

### Important rule

The frontend should not:

- recompute resistances,
- recompute equivalent branches,
- recompute contributions,
- or build separate derivation math from raw inputs.

Those should come from the backend payload.

---

## 20. Export Contract

The export payload should contain enough information to reconstruct the analysis offline.

At minimum export:

- `normalized_model`
- `summary`
- `diagnosis`
- `applicability`
- `reporting_basis`
- `nodes`
- `segments`
- `parallel_groups`
- `warnings`
- `recommendations`
- `assumptions`
- `derivations`

If a future spreadsheet export is added, it should still be generated from this same solved payload.

---

## 21. Validation and Testing Recommendations

When implementation starts, tests should cover:

- nominal simple series chain
- nominal parallel branch case
- direct resistance mode
- TIM area-normalized mode
- TIM conductivity mode
- conduction slab mode
- required-segment sizing mode
- duplicate id validation
- disconnected network validation
- no boundary node validation
- solved payload completeness
- diagnosis / applicability / reporting-basis completeness
- derivation object completeness

The first test suite should verify not just temperatures, but also payload shape and disclosure completeness.

---

## 22. Recommended MVP Constraint Set

To keep the first implementation controlled, the MVP should impose these limits:

- one connected network only
- exactly one fixed-temperature boundary node in the user-facing v1
- exactly one positive heat-input node in the user-facing v1
- one unknown segment at most
- no arbitrary nonlinear segment models
- no radiation segment mode
- restrained custom topologies only
- compare-two-models handled by the frontend as two separate solves

These limits should be explicit in the UI and the docs.

---

## 23. Immediate Next Coding Step

Once implementation begins, the first coding task should be:

1. create `pycalcs/thermal_networks.py`
2. implement the validation function
3. implement the canonical direct / TIM / slab resistance resolvers
4. implement the series + simple-branch steady-state solver
5. return the normalized summary / node / segment / derivation payload exactly as defined here

That order will establish the core contract before any UI complexity is added.
