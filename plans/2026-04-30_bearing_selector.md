# Rolling-Element Bearing Selector

Date: 2026-04-30
Status: Proposed plan for critique before implementation

## Problem Statement

Engineers sizing a rotating shaft routinely need to answer: **"Given my radial load, axial load, and shaft speed, which bearing type and size will give me adequate life?"**

Today the workflow is one of:
- Open SKF/Schaeffler/Timken catalog PDFs and run the L10 formulas by hand
- Use vendor calculators that lock you into one supplier's part numbers
- Fall back on rules of thumb that ignore axial load contribution or P-equivalent factors

The ISO 281 L10 calculation is well-defined and dimensionally simple. It maps cleanly onto our existing database-driven, progressive-disclosure pattern (`bolt-torque`, `fits`, `ring-fit`).

## Concept: Bearing Selector

A tool that answers: **"For a given duty point (Fr, Fa, n), what L10 life does each candidate bearing achieve, and which type/size is the right starting point?"**

### Core flow

1. User enters radial load `Fr`, axial load `Fa`, and shaft speed `n` (RPM).
2. User picks a **shaft bore size** (e.g. 25 mm) — the most common entry point in real selection.
3. Tool computes equivalent dynamic load `P` and L10 life for **every candidate bearing in the database that fits that bore**, across multiple types (deep groove ball, angular contact ball, cylindrical roller, tapered roller, spherical roller).
4. Results render as a **comparison table** sorted by L10 life, plus a side-by-side type comparison showing the trade-offs (radial capacity, axial capacity, speed limit, cost-class, mounting complexity).
5. **Static safety factor `s0 = C0 / P0`** flagged separately — important for low-speed or oscillating duty.

### Why this fits the repo pattern

| Pattern | Source | Application here |
|---|---|---|
| Database-driven dropdowns | `fasteners.py` BOLT_GRADES | Bearing series + size table |
| Equivalent load with X/Y factors | ISO 281 | Direct math, no iteration |
| Substituted-equation strings | `fasteners.py` `subst_*` | L10 derivation panel |
| Type comparison table | `fan_selection.py` | Type-vs-type at common duty point |
| Static + dynamic safety factors | `fasteners.py` SF_y, SF_k | s0 (static) and L10 (dynamic) |

## Scope

### In scope (v1)
- **ISO 281:2007** L10 life calculation (basic rating life)
- **5 bearing types**, each with a representative size series:
  - Deep groove ball (62xx, 63xx series)
  - Angular contact ball (72xx series, single row, 30° contact)
  - Cylindrical roller (NU2xx, NU3xx)
  - Tapered roller (302xx, 303xx, 322xx)
  - Spherical roller (222xx, 223xx)
- ~80–120 catalog entries total (representative bores 10–100 mm)
- X/Y factors for combined radial+axial loading
- Static safety factor `s0 = C0 / P0`
- Speed limit check (catalog `n_lim` for grease vs oil)
- Duty point input + bore filter

### Out of scope (v1, leave for v2+)
- Modified rating life `Lnm` (a1, a23 reliability/contamination factors)
- Thrust ball / needle / cam follower / linear bearings
- Preloaded duplex angular-contact pairs (back-to-back, face-to-face)
- Lubricant viscosity selection / κ-ratio
- Shaft / housing fit recommendations (we already have `tools/fits/`)
- Vendor part number cross-reference
- Heat generation / temperature rise

`Lnm` is the obvious v2 add — the data structure should already accommodate the `a1·a_ISO·L10` extension.

## Architecture

### Python module: `pycalcs/bearings.py`

Database-first, single calculation entry point. Mirrors `fasteners.py` structure.

#### Database

```python
BEARING_TYPES: Dict[str, Dict[str, Any]] = {
    "deep_groove_ball": {
        "life_exponent": 3,           # p in (C/P)^p
        "x_factor_radial": 0.56,
        "y_factor_axial_lookup": ...,  # f(Fa/C0) per ISO 281 Table 4
        "min_axial_ratio": 0.014,     # e-value transition
        "description": "...",
        "advantages": [...],
        "limitations": [...],
        "applications": [...],
    },
    "angular_contact_ball": { "life_exponent": 3, ... },
    "cylindrical_roller":   { "life_exponent": 10/3, ... },
    "tapered_roller":       { "life_exponent": 10/3, ... },
    "spherical_roller":     { "life_exponent": 10/3, ... },
}

# One row per catalog bearing; pulled from public ISO/SKF dimension tables
BEARING_CATALOG: List[Dict[str, Any]] = [
    {
        "designation": "6205",
        "type": "deep_groove_ball",
        "bore_mm": 25,
        "od_mm": 52,
        "width_mm": 15,
        "C_dynamic_N": 14000,
        "C0_static_N": 6950,
        "n_lim_grease_rpm": 14000,
        "n_lim_oil_rpm": 17000,
        "mass_kg": 0.13,
    },
    # ... ~80–120 rows
]
```

Source for catalog rows: SKF General Catalogue published dimension tables (publicly available; values match across major makers within ~5%).

#### Core functions

```python
def equivalent_dynamic_load(
    Fr: float, Fa: float, bearing_type: str, C0: float,
) -> Tuple[float, float, float]:
    """Return (P, X, Y) per ISO 281 with type-specific X/Y lookup."""

def L10_life_hours(C: float, P: float, n_rpm: float, life_exponent: float) -> float:
    """L10 = (C/P)^p × 10^6 / (60·n)"""

def static_safety_factor(C0: float, P0: float) -> float:
    """s0 = C0 / P0  — target ≥ 1.0 normal, ≥ 2.0 shock loaded"""

def evaluate_bearing(
    bearing_designation: str, Fr: float, Fa: float, n_rpm: float,
    lubrication: str = "grease",
) -> Dict[str, Any]:
    """Single-bearing analysis: returns L10, s0, speed margin, status, recs."""

def select_bearings(
    Fr: float, Fa: float, n_rpm: float, bore_mm: float,
    types: Optional[List[str]] = None, lubrication: str = "grease",
) -> Dict[str, Any]:
    """
    Main entry point. Filters catalog by bore + types, evaluates each,
    returns comparison data + per-type winner.

    ---Returns---
    candidates : list[dict]
        Per-bearing rows: designation, type, OD, width, P, L10_hours,
        s0, speed_margin, status, subst_L10
    type_summary : dict
        Best candidate per bearing type with key metrics.
    recommendation : dict
        Top overall pick + why; runner-up with trade-off note.
    duty_point : dict
        Echo of inputs for derivation panels.
    """
```

#### Substituted-equation strings (per progressive-disclosure L2)

```python
"subst_P": "P = X·Fr + Y·Fa = 0.56·1500 + 1.71·400 = 1524 N",
"subst_L10": "L10 = (C/P)^p × 10^6 / (60·n)
              = (14000/1524)^3 × 10^6 / (60·1500) = 8731 hours",
"subst_s0": "s0 = C0/P0 = 6950/1900 = 3.66",
```

### HTML tool: `tools/bearing-selector/index.html`

Built from `tools/example_tool_advanced/`. Layout follows `fan-type-selector` since the comparison-table-of-types interaction is the closest match.

#### Sidebar inputs (always visible)
- Radial load `Fr` [N / lbf]
- Axial load `Fa` [N / lbf]
- Shaft speed `n` [RPM]
- Shaft bore `d` [mm / in] — dropdown of catalog bore sizes
- Bearing types — multi-select checkbox group, all on by default

#### Expert mode (collapsed)
- Lubrication: grease / oil (affects speed limit only in v1)
- Required minimum L10 life (hours) — used to color status, default 20,000 h
- Required static safety factor `s0_min` — default 1.0
- Reliability target — placeholder, disabled in v1, enabled when `Lnm` lands

#### Results
- **Top recommendation banner** — "6305 (deep groove ball) — 18,400 h L10, s0 = 4.1"
- **Comparison table** — all qualifying catalog bearings, sortable, color-coded life
- **Type summary cards** (one per bearing type) — best-of-type with trade-off tags
- **Three tabs:**
  1. **Life chart** — bar chart of L10 hours per candidate, threshold line at user's required-life input
  2. **Load capacity vs life** — log-log plot showing each type's L10 sensitivity to load (the `(C/P)^p` shape — flatter for ball, steeper for roller)
  3. **Type details** — full metadata cards (advantages / limitations / mounting / cost-class) like `fan-type-selector` tab 3

#### Equations panel (expandable)
- Equivalent dynamic load `P = X·Fr + Y·Fa` with X/Y lookup explanation
- Basic rating life `L10 = (C/P)^p × 10^6 / (60n)` with `p` value per type
- Static safety factor `s0 = C0/P0`
- Speed limit caveat (lubrication-dependent)

### Test cases

`tools/bearing-selector/test-cases/*.json`:

1. `pure_radial_pump_shaft.json` — 25 mm bore, 2000 N radial, 0 axial, 1750 RPM. Should pick 6205 / 6305.
2. `combined_load_gearbox.json` — 40 mm bore, 5000 N radial, 1500 N axial, 1000 RPM. Angular contact or tapered should win.
3. `low_speed_high_static.json` — 50 mm bore, 20 kN radial, 0 axial, 5 RPM. Static safety factor dominates over L10.
4. `marginal_life.json` — Inputs that yield L10 ~10,000 h (under the 20,000 h target) to verify status banner color logic.
5. `over_speed_warning.json` — Speed exceeds catalog `n_lim_grease` to verify the speed-margin warning surfaces.

### Tests: `tests/test_bearings.py`

Required cases:
- **Pure radial, deep groove**: hand-checked against Shigley Example 11-3 (or equivalent textbook problem).
- **Combined load X/Y transition**: confirm we cross the `e` boundary correctly when `Fa/C0` increases.
- **Roller life exponent**: confirm `p = 10/3` produces ~58% longer life than `p = 3` at C/P = 4.
- **Static safety factor**: simple ratio.
- **Bore filter**: `select_bearings(bore_mm=25)` returns only 25 mm bore entries.
- **Speed limit**: lubrication switching changes `n_lim`.
- **Edge cases**: zero axial load (P should equal Fr), `Fa = 0` and `bearing_type = "thrust_*"` should raise (deferred — no thrust types in v1, but signature should reject).

## Key Equations (for the Background tab)

### Basic Rating Life — ISO 281
$$L_{10} = \left(\frac{C}{P}\right)^p \cdot \frac{10^6}{60 \cdot n}$$

- `L10` — life in hours that 90% of a population reaches before fatigue
- `C` — basic dynamic load rating (catalog, N)
- `P` — equivalent dynamic load (N)
- `p` — life exponent: 3 for ball bearings, 10/3 for roller bearings
- `n` — rotational speed (RPM)

### Equivalent Dynamic Load
$$P = X \cdot F_r + Y \cdot F_a$$

`X` and `Y` are looked up from ISO 281 tables based on bearing type and the ratio `Fa/C0`. For deep groove ball bearings, when `Fa/Fr ≤ e`, `P = Fr` (axial component absorbed without penalty).

### Static Safety Factor
$$s_0 = \frac{C_0}{P_0}$$

- `C0` — basic static load rating (catalog, N)
- `P0` — equivalent static load (N), most conservative form: `P0 = max(Fr, X0·Fr + Y0·Fa)`

Targets: `s0 ≥ 1.0` for normal duty, `≥ 1.5` for shock loads, `≥ 2.0` for high precision.

## Open Questions / Decisions Needed

1. **Catalog source** — SKF tables are most complete and publicly published. Acceptable to use SKF dimension/rating numbers as the canonical dataset, cited inline? Or hand-pick a "consensus" set across SKF/Schaeffler/Timken to avoid implying SKF endorsement?
2. **Imperial display** — Tool inputs in N/mm by default with imperial toggle, or both visible? The fastener tool uses an explicit standard dropdown (ISO vs SAE) — bearings have no parallel split, so a unit toggle (`MKS` / `MMGS`) is the cleaner pattern.
3. **Bore-first vs OD-first selection** — bore is the conventional anchor (you size around the shaft). I'm proposing bore-first. Confirm this matches how you'd actually use the tool.
4. **Type comparison when bore varies between types** — a 25 mm tapered roller has very different OD/width than a 25 mm deep-groove ball. Should comparison enforce same bore (current proposal) or also match envelope dimensions when possible?

## Implementation Steps

1. **Build `pycalcs/bearings.py`** — types dict, catalog list (start with ~30 bearings to validate end-to-end, then fill out), core functions, full docstrings with `---Parameters---` / `---Returns---` / `---LaTeX---`.
2. **Write `tests/test_bearings.py`** — at minimum the textbook-validated case before writing any UI.
3. **Scaffold `tools/bearing-selector/`** from `tools/example_tool_advanced/`, point `TOOL_MODULE_NAME` / `TOOL_FUNCTION_NAME` at `bearings.select_bearings`.
4. **Wire sidebar inputs** — bore dropdown populated from catalog, type checkboxes, load+speed.
5. **Render comparison table + recommendation banner** — first cut without charts.
6. **Add Plotly charts** — life bar chart, then load-vs-life log-log.
7. **Build derivation panels** — clickable rows reveal P, L10, s0 substituted strings.
8. **Background tab** — equations, X/Y table excerpt, life-target reference table, references.
9. **Test cases JSON** — 5 cases above.
10. **Add to `catalog.json`** — category `["Mechanical", "Machine Design"]`, tags `["bearing", "L10", "iso-281", "selection", "shaft"]`.
11. **Manual browser verification** — every tab, dark mode, unit toggle, expert mode, sample test case load.
12. **README.md** — purpose, inputs, outputs, equations, references, limitations table.

## Relationship to Other Tools

- **`tools/fits/`** — bearing fit recommendations live there already; bearing-selector should link to it for the "now what fit do I use?" follow-up.
- **`tools/ring-fit/`** — shrink-fit and press-fit interface stresses, useful when mounting tapered or cylindrical bearings.
- **`tools/beam-bending/`** — shaft deflection at bearing locations affects misalignment; out of scope here but worth a "see also" link.

The natural progression: **shaft sizing (beam bending) → bearing selection (this tool) → housing/shaft fit (fits + ring-fit)**.

## References

1. **ISO 281:2007** — Rolling bearings — Dynamic load ratings and rating life
2. **ISO 76:2006** — Rolling bearings — Static load ratings
3. **ABMA Std 9** — Load Ratings and Fatigue Life for Ball Bearings (US equivalent)
4. **SKF General Catalogue** (publicly available PDF) — dimensional and rating tables
5. **Harris & Kotzalas** — *Rolling Bearing Analysis*, 5th Edition, CRC Press
6. **Shigley's Mechanical Engineering Design**, 11th ed., Chapter 11
