# Materials Selection & Analysis Suite

Date: 2026-04-07
Revised: 2026-04-11 (post-second-critique)
Status: Proposed plan for critique before implementation

Related existing assets:
- `tools/ashby-chart/` — current Ashby chart tool (7 hardcoded materials, text-only ranking)
- `pycalcs/materials.py` — Material dataclass + `rank_materials_for_ashby()`
- `tests/test_materials.py` — 3 parametrized tests
- `tools/deck-material-estimator/` + `pycalcs/decking.py` — building materials cost/quantity
- `pycalcs/heatsinks.py` — 4 heatsink materials (k, emissivity)
- `pycalcs/fasteners.py` — 14 bolt grades (proof/tensile/yield strength, E)
- `pycalcs/interference_fits.py` — 13 material presets (E, ν, σ_y, CTE)
- `pycalcs/fracture_mechanics.py` — 6 composite/polymer fracture materials (K_IC, Paris law, E, σ_uts)
- `pycalcs/beam_analysis.py` — 9 beam materials (E, σ_y, ρ, ν)
- `pycalcs/fatigue.py` — 4 metal + 4 polymer fatigue presets (S-N curve params)
- `pycalcs/polymer_fatigue.py` — 1 detailed polymer preset (PA66-GF50, energy/creep params)
- `pycalcs/resonators.py` — 4 materials (E, ρ)
- `pycalcs/structural_resonance.py` — 4 materials (E, ρ, ν)
- `pycalcs/motor_thermal.py` — 4 material constants (Cp) + motor presets
- `pycalcs/energy_density.py` — 7 energy source presets
- `pycalcs/example_advanced.py` — 4 example materials

Charting precedent: **Plotly 2.27.0** is already used in 25+ tools in this repo.

---

## 1. Vision

Build a suite of browser-based tools for material selection, comparison, and analysis — covering metals, polymers, ceramics, composites, foams, fabrics, natural materials, and soft matter.

The suite should serve three audiences simultaneously (per the project's progressive disclosure philosophy):

- **The hurried engineer** — quickly find the right material for a design constraint, compare candidates, and export results.
- **The curious student** — explore how material families relate to each other, understand trade-offs visually through Ashby charts, and learn the physics behind material indices.
- **The verifying expert** — trace every data point to its source at the property-datum level, inspect the exact performance index equations, and validate selections against known benchmarks.

### Scope boundaries

This is an **educational and preliminary-design screening** tool. It is not:

- A certified material database (like MMPDS or CAMPUS)
- A substitute for detailed design analysis (FEA, fatigue life prediction, corrosion modeling)
- A real-time pricing or procurement system

Every output should carry appropriate confidence indicators (see §4.3) so users understand the provenance and limitations of the data they are using.

---

## 2. Current State & Gap Analysis

### What exists today

| Capability | Status | Limitations |
|---|---|---|
| Material ranking by Ashby index | Working | Only 3 design modes, 7 hardcoded materials |
| Material database | Minimal | 7 materials, 4 properties each (ρ, E, σ_y, name) |
| Interactive Ashby chart | Missing | Placeholder text says "forthcoming" |
| Material comparison | Missing | No side-by-side view |
| Property search/filter | Missing | No way to search by property range |
| Thermal material selection | Missing | No thermal properties in database |
| Cost analysis | Missing | No cost data |
| Manufacturing constraints | Missing | No processability data |
| Export | Missing | No CSV/clipboard export |
| Custom materials | Missing | Users cannot add their own materials |
| Material families visualization | Missing | No family-level grouping or coloring |

### Embedded material data across 16 modules

The repo already contains ~100 discrete material entries scattered across 16 pycalcs modules. These serve as tool-specific presets with specialized properties (fatigue coefficients, Paris law parameters, convection coefficients) that go far beyond what a general-purpose material database should store. See §5.6 for the migration strategy.

### What needs to change

1. **Database**: From 7 hardcoded materials → 150+ materials across all families with property-level sourcing and ranges, stored in structured JSON.
2. **Visualization**: From text-only → interactive Ashby charts (Plotly-based, consistent with existing tools) with logarithmic axes, material family coloring, performance index isolines, and click-to-inspect.
3. **Tools**: From 1 tool → a consolidated Materials Explorer (chart + browse + compare + substitute modes) plus 3–4 specialized analysis tools.
4. **Architecture**: From monolithic function → shared material database layer with reusable Python query functions and a shared JS charting component.

---

## 3. Material Families & Coverage

The database must span at least the following families, with representative grades/alloys in each. Priority labels govern what must be present before a phase ships.

### 3.1 Metals & Alloys

| Sub-family | Representative grades | Priority |
|---|---|---|
| Carbon & low-alloy steels | AISI 1018, 1045, 4140, 4340 | P0 |
| Stainless steels | 304, 316, 17-4 PH, 440C | P0 |
| Tool steels | D2, H13, M2, S7 | P1 |
| Cast irons | Gray, ductile, malleable | P1 |
| Aluminum alloys | 2024-T3, 5052-H32, 6061-T6, 7075-T6 | P0 |
| Titanium alloys | Grade 2 (CP), Grade 5 (Ti-6Al-4V), Grade 23 | P0 |
| Copper alloys | C110, C260 (brass), C510 (phosphor bronze), BeCu | P1 |
| Nickel alloys | Inconel 625, 718; Monel 400; Hastelloy C-276 | P1 |
| Magnesium alloys | AZ31B, AZ91D, WE43 | P1 |
| Zinc alloys | Zamak 3, Zamak 5 | P2 |
| Tungsten & refractory metals | W, Mo, Ta, Nb | P2 |
| Precious metals (ref. only) | Au, Ag, Pt | P2 |

### 3.2 Polymers

| Sub-family | Representative grades | Priority |
|---|---|---|
| Commodity thermoplastics | HDPE, LDPE, PP, PS, PVC | P0 |
| Engineering thermoplastics | PA6, PA66, POM, PC, PBT, PET | P0 |
| High-performance thermoplastics | PEEK, PEI (Ultem), PPS, PAI, LCP | P1 |
| Fluoropolymers | PTFE, FEP, PFA, PVDF | P1 |
| Thermosets | Epoxy (unfilled), phenolic, polyester, vinyl ester | P0 |
| Elastomers | Natural rubber, silicone, neoprene, EPDM, nitrile, FKM (Viton) | P1 |
| Thermoplastic elastomers | TPU, TPE-S (SEBS), TPE-V (TPV) | P2 |

### 3.3 Ceramics & Glasses

| Sub-family | Representative grades | Priority |
|---|---|---|
| Oxide ceramics | Alumina (Al₂O₃), zirconia (ZrO₂), mullite | P1 |
| Non-oxide ceramics | Silicon carbide (SiC), silicon nitride (Si₃N₄), boron carbide (B₄C) | P1 |
| Glass | Soda-lime, borosilicate, fused silica, aluminosilicate | P1 |
| Glass-ceramics | Lithium aluminosilicate (e.g., Zerodur), Macor | P2 |
| Piezoelectrics / functional ceramics | PZT, BaTiO₃ | P2 |

### 3.4 Composites

| Sub-family | Representative grades | Priority |
|---|---|---|
| Carbon fibre reinforced polymer (CFRP) | UD tape, woven fabric, quasi-isotropic layup | P0 |
| Glass fibre reinforced polymer (GFRP) | E-glass/epoxy, S-glass/epoxy | P0 |
| Aramid fibre reinforced polymer (AFRP) | Kevlar 49/epoxy | P1 |
| Short-fibre reinforced thermoplastics | PA66-GF30, PBT-GF30, PP-GF40 | P1 |
| Metal matrix composites (MMC) | Al-SiC, Al-Al₂O₃ | P2 |
| Ceramic matrix composites (CMC) | SiC/SiC, C/C | P2 |
| Sandwich panels | Aluminium honeycomb/CFRP, Nomex honeycomb/GFRP | P1 |

### 3.5 Natural & Bio-derived Materials

| Sub-family | Representative grades | Priority |
|---|---|---|
| Wood (structural) | Douglas fir, oak, birch, balsa, bamboo (∥ and ⊥ grain) | P1 |
| Natural fibres | Flax, hemp, jute, sisal | P2 |
| Leather | Bovine, synthetic (PU-based) | P2 |
| Cork | Natural cork, agglomerated cork | P2 |
| Bone & shell (reference) | Cortical bone, nacre | P2 |

### 3.6 Foams & Cellular Materials

| Sub-family | Representative grades | Priority |
|---|---|---|
| Polymer foams (rigid) | PU rigid foam, PS foam (EPS, XPS), PVC foam | P1 |
| Polymer foams (flexible) | PU flexible foam, PE foam, silicone foam | P1 |
| Metal foams | Aluminium foam (Alporas, Duocel), nickel foam | P2 |
| Ceramic foams | Alumina foam, SiC foam | P2 |
| Syntactic foams | Glass microsphere/epoxy | P2 |
| Aerogels | Silica aerogel, polymer aerogel | P2 |

### 3.7 Fabrics & Textiles

| Sub-family | Representative grades | Priority |
|---|---|---|
| Woven structural fabrics | Carbon fabric, aramid fabric, UHMWPE (Dyneema/Spectra) | P1 |
| Technical textiles | Nomex felt, glass fabric, basalt fabric | P2 |
| Nonwovens & felts | Polyester nonwoven, needle-punched felt | P2 |
| Coated fabrics | Silicone-coated glass, PTFE-coated glass (e.g., Teflon belt) | P2 |

### 3.8 Gels, Hydrogels & Soft Matter

| Sub-family | Representative grades | Priority |
|---|---|---|
| Hydrogels | PVA hydrogel, PAAm hydrogel, alginate gel | P2 |
| Silicone gels | Thermal interface gels, medical-grade silicone gel | P2 |
| Phase-change materials | Paraffin wax, salt hydrates | P2 |

### Priority Key
- **P0** — Must have for Milestone 1 (Foundation). Core engineering materials.
- **P1** — Must have for Milestone 2 (Explorer). Important for breadth and credibility.
- **P2** — Nice to have. Include data stubs; full tool support in later milestones.

---

## 4. Data Model

### 4.1 Design Principles

The critique of the v1 plan correctly identified that a flat scalar-per-property model cannot honestly represent engineering materials. The revised model addresses this with three key changes:

1. **Property values carry their own metadata** — every numeric property can be either a bare scalar (shorthand) or a rich datum object with min/max range, source, condition, and confidence tier.
2. **Provenance lives at the property level**, not just the material level.
3. **Ranges are first-class data**, not collapsed to midpoints — this is fundamental to Ashby-style screening, which is built on property envelopes.

However, the model must remain **a flat JSON file loadable by both Python (`json.loads`) and JavaScript (`fetch + JSON.parse`)** — no relational database, no server, no external dependencies. This rules out a fully normalized entity-relationship model. The design below is the pragmatic middle ground: rich enough for honest engineering data, flat enough for a static-site Pyodide tool.

### 4.2 Property Datum Model

Every numeric property in a material record can be stored in one of two forms:

**Short form** (scalar) — used when the value is well-established, single-condition, and the material-level source applies:
```json
"density": 2700
```

**Rich form** (object) — used when range, condition, source, or confidence matter:
```json
"density": {
  "value": 2700,
  "min": 2690,
  "max": 2710,
  "source_id": "ashby-2011-a1",
  "condition": "20°C",
  "basis": "typical",
  "notes": null
}
```

The query layer treats both forms identically for computation — `get_value(material, "density")` returns the scalar or the `.value` from the object. But the UI can display ranges, source citations, and confidence badges when the rich form is present.

**Fields in the rich form:**

| Field | Type | Required | Description |
|---|---|---|---|
| `value` | float | Yes | Representative value (midpoint of range, or typical value) |
| `min` | float | No | Lower bound of the property range |
| `max` | float | No | Upper bound of the property range |
| `source_id` | string | No | Key into the sources registry (see §4.4). Overrides material-level `default_source_id`. |
| `condition` | string | No | Measurement condition, e.g., "20°C, dry", "150°C", "50% RH", "longitudinal" |
| `basis` | string | No | One of: `typical`, `minimum`, `design_allowable`, `vendor_datasheet`, `handbook_range`, `estimate`. See §4.3. |
| `notes` | string | No | Free-text caveats |

**Why this hybrid approach (not a full entity model):**
- A fully normalized PropertyDatum/SourceRecord/ConditionProfile model would require either nested arrays of datum objects per property (painful to query in pure Python without a database) or a separate relational store (impossible in a static-site Pyodide tool).
- The hybrid model gives 90% of the benefit — per-property provenance, ranges, conditions — with 10% of the complexity.
- Properties that don't need rich metadata stay as bare scalars, keeping the JSON compact.
- The query layer abstracts over both forms, so tools don't need to care.

### 4.3 Confidence Tiers

Every property datum has an implicit or explicit `basis` that communicates how much the user should trust it. This is critical for not blurring screening-grade and design-grade data.

| Basis | Meaning | UI Indicator | Use in Rankings |
|---|---|---|---|
| `handbook_range` | Range from a textbook (e.g., Ashby). Suitable for family-level screening. | Gray dot | Default for Ashby chart envelopes |
| `typical` | Representative single value from a reputable source. Suitable for preliminary design. | Blue dot | Default for ranking/comparison |
| `vendor_datasheet` | From a specific manufacturer's datasheet. Grade-specific but may be optimistic (test conditions may differ from application). | Green dot | Included in rankings |
| `minimum` | Statistical minimum (e.g., B-basis, S-basis from MMPDS). Conservative. | Yellow dot | Can be selected as ranking basis |
| `design_allowable` | Formally qualified design value (A-basis, B-basis). Highest confidence. | Gold dot | Preferred for structural selection |
| `estimate` | Derived, interpolated, or low-confidence. Clearly flagged. | Red dot | **Excluded from rankings by default** |

When `basis` is omitted (bare scalar or rich form without `basis`), it defaults to `typical`.

**Ranking behavior (definitive rule):**
1. The ranking engine uses the `value` field for computation.
2. Materials whose ranking property has `basis: "estimate"` are **excluded by default**. The user can toggle "Include estimates" to opt-in.
3. All other basis tiers (`handbook_range`, `typical`, `vendor_datasheet`, `minimum`, `design_allowable`) are included by default.
4. The UI shows the confidence tier badge next to every ranked value so the user can judge credibility.
5. For **conservative screening**, the user can toggle a "Use min values" mode. When enabled, the ranking engine uses `min` instead of `value` for any property that has a `min` field. When `min` is absent, it falls back to `value`. This makes rankings pessimistic — appropriate for structural selection.
6. For **optimistic screening** (e.g., finding potential candidates before testing), the default `value`-based ranking applies.

This resolves the earlier ambiguity: "estimate" data is excluded (not just flagged), and the conservative/optimistic distinction is an explicit user choice rather than an implicit trust hierarchy.

### 4.4 Source Registry

Instead of a free-text `source` field per material, the database maintains a top-level `sources` object that maps source IDs to structured citations:

```json
{
  "sources": {
    "ashby-2011-a1": {
      "citation": "Ashby, M. F. (2011). Materials Selection in Mechanical Design, 4th ed. Table A1.",
      "type": "textbook",
      "year": 2011
    },
    "matweb-al6061": {
      "citation": "MatWeb: Aluminum 6061-T6. Accessed 2026-03.",
      "type": "online_database",
      "year": 2026,
      "url": "https://www.matweb.com/search/DataSheet.aspx?MatGUID=..."
    },
    "toray-t700s-ds": {
      "citation": "Toray T700S Carbon Fiber Technical Data Sheet, Rev. 5.",
      "type": "vendor_datasheet",
      "year": 2023
    }
  },
  "materials": [ ... ]
}
```

**How it connects:**
- Each material has a `default_source_id` — the fallback source for any property that doesn't specify its own `source_id`.
- Any property in rich form can override with its own `source_id`.
- The UI can render a citation trail: click any property → see source, year, type.

### 4.5 Identity & Classification Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Unique slug, e.g., `al-6061-t6` |
| `name` | string | Yes | Human-readable name, e.g., "Aluminium 6061-T6" |
| `family` | string | Yes | Top-level: `metal`, `polymer`, `ceramic`, `composite`, `natural`, `foam`, `fabric`, `gel` |
| `sub_family` | string | Yes | e.g., `aluminum-alloy`, `engineering-thermoplastic` |
| `record_kind` | string | Yes | One of: `bulk_material`, `lamina`, `laminate`, `sandwich`, `foam`, `fabric`, `product`. See note below. |
| `designation` | string | No | Standards designation (UNS, ISO, ASTM, etc.) |
| `common_names` | string[] | No | Trade names, aliases |
| `default_source_id` | string | Yes | Key into sources registry |
| `condition` | string | No | Material condition, e.g., "T6", "annealed", "30% GF, dry, as-molded" |
| `notes` | string | No | Free-text caveats (e.g., "anisotropic — primary values are ∥ grain") |
| `related_ids` | string[] | No | Links to variants (e.g., dry ↔ conditioned, O ↔ T6, lamina ↔ laminate) |

**`record_kind` values:**
- `bulk_material` — A homogeneous engineering material (steel alloy, polymer resin, glass). Properties are intrinsic.
- `lamina` — A single ply or prepreg. Properties are directional (0°/90°). Used as CLT input.
- `laminate` — A multi-ply layup (e.g., "quasi-isotropic CFRP"). Properties are effective/homogenized. Not CLT input.
- `sandwich` — A sandwich panel system. Properties are system-level, not intrinsic.
- `foam` — A cellular material. Has `relative_density` and `base_material_id`.
- `fabric` — A textile. Uses `areal_density` instead of volumetric `density` as the primary mass metric (see §4.12).
- `product` — A semi-finished product (e.g., specific tube, sheet stock). Rarely used in general screening.

This field matters for axis compatibility (§4.12), ranking validity, and preventing nonsensical cross-family comparisons. The Explorer UI can filter by `record_kind` and warn when comparing records of different kinds.

### 4.6 Property Fields

Properties are organized into groups. Every property uses the datum model (§4.2): either a bare scalar or a rich object.

**Mechanical Properties:**

| Field | Unit | Description | Families with data |
|---|---|---|---|
| `density` | kg/m³ | Bulk density | All |
| `youngs_modulus` | Pa | Tensile elastic modulus | All except gels |
| `shear_modulus` | Pa | Shear modulus (G) | Metals, ceramics, composites |
| `poissons_ratio` | — | Poisson's ratio (ν) | All except fabrics, gels |
| `yield_strength` | Pa | 0.2% offset yield (tensile) | Metals, some polymers |
| `tensile_strength` | Pa | Ultimate tensile strength | All except gels |
| `compressive_strength` | Pa | Ultimate compressive strength | Ceramics, foams, composites, natural |
| `flexural_strength` | Pa | Modulus of rupture | Ceramics, polymers, composites |
| `flexural_modulus` | Pa | Flexural modulus | Polymers, composites |
| `elongation_at_break` | — | Fractional elongation to failure | Metals, polymers |
| `fracture_toughness` | Pa·√m | K_IC plane-strain fracture toughness | Metals, ceramics, some composites |
| `fatigue_endurance_limit` | Pa | Endurance limit at 10⁷ cycles (R=−1) | Metals (note: many polymers/Al alloys have no true endurance limit — use `notes` or `null`) |
| `hardness_vickers` | HV | Vickers hardness | Metals, ceramics |
| `hardness_shore_a` | Shore A | Shore A hardness | Elastomers |
| `hardness_shore_d` | Shore D | Shore D hardness | Rigid polymers |
| `impact_strength_izod` | J/m | Izod impact strength | Polymers |

**Thermal Properties:**

| Field | Unit | Description |
|---|---|---|
| `thermal_conductivity` | W/(m·K) | Thermal conductivity |
| `specific_heat` | J/(kg·K) | Specific heat capacity |
| `cte` | 1/K | Coefficient of thermal expansion (linear) |
| `max_service_temp` | °C | Maximum continuous service temperature |
| `min_service_temp` | °C | Minimum service temperature |
| `melting_point` | °C | Melting point or solidus temperature (crystalline materials only; `null` for amorphous) |
| `glass_transition_temp` | °C | T_g (polymers, glasses; `null` for crystalline metals) |
| `hdt_at_1_8mpa` | °C | Heat deflection temperature at 1.8 MPa (polymers) |
| `flammability_rating` | — | UL 94 rating (V-0, V-1, V-2, HB) or equivalent |

**Note:** `thermal_diffusivity` is intentionally **not** stored as a primary field. It equals k/(ρ·Cₚ) and should be computed by the query layer to avoid consistency errors between stored k, ρ, and Cₚ. The query layer exposes it as a computed virtual property available for plotting and ranking.

**Electrical Properties:**

| Field | Unit | Description |
|---|---|---|
| `electrical_resistivity` | Ω·m | Bulk electrical resistivity |
| `dielectric_constant` | — | Relative permittivity (1 kHz) |
| `dielectric_strength` | V/m | Breakdown voltage per unit thickness |

**Economic & Environmental Properties:**

| Field | Unit | Description |
|---|---|---|
| `price_per_kg` | USD/kg | Approximate raw material cost. **Screening-grade only** — see §4.7. |
| `embodied_energy` | MJ/kg | Cradle-to-gate embodied energy (primary production) |
| `co2_footprint` | kg CO₂/kg | Cradle-to-gate carbon footprint (primary production) |
| `recyclability` | — | `excellent`, `good`, `limited`, `none` |
| `rohs_compliant` | bool | RoHS compliance |

**Processability:**

Rather than boolean flags that flatten complex process-dependent behavior into yes/no, processability is stored as a list of process objects with optional qualifiers:

```json
"processability": [
  {"process": "machining", "rating": "excellent", "notes": "Free-machining grade"},
  {"process": "welding", "rating": "good", "notes": "TIG, MIG; preheat recommended for thick sections"},
  {"process": "casting", "rating": "fair", "notes": "Sand and investment casting; limited fluidity"},
  {"process": "3d_printing", "rating": "good", "notes": "DMLS, EBM"},
  {"process": "forming", "rating": "excellent"}
]
```

Ratings: `excellent`, `good`, `fair`, `poor`, `not_recommended`. This is still a simplification of reality — real manufacturability depends on geometry, section thickness, tolerances, volume, and specific process variants — but it gives users meaningful screening information beyond bare booleans, with `notes` to capture important caveats.

**Filter semantics:** Ratings are ordered numerically for filtering: `excellent` = 4, `good` = 3, `fair` = 2, `poor` = 1, `not_recommended` = 0. When the user applies a hard constraint like "must be weldable":
- The filter checks for a `welding` entry in the material's `processability` array.
- If absent → material is excluded (no data = no claim).
- If present with rating `fair` or better (≥ 2) → material passes.
- If present with `poor` or `not_recommended` (< 2) → material is excluded.
- The threshold of `fair` is the default; the Substitute mode's advanced options allow the user to tighten it to `good` or loosen it to `poor`.

**The tool is explicit that processability ratings are for screening only.** Detailed manufacturing process selection (volume economics, tolerance capabilities, surface finish, joining routes) is out of scope for this suite.

### 4.7 Scoping Notes for Cost & Environmental Data

The critique correctly identified that scalar cost/environmental fields project more certainty than they deserve. The plan addresses this with explicit scoping:

**Cost data rules:**
- All `price_per_kg` values are **order-of-magnitude estimates for raw material in commodity form** (bar stock, pellets, sheet, etc.).
- Every cost datum must use the rich form with `source_id` and a `condition` noting the form (e.g., "bar stock, qty 100 kg").
- The UI displays cost with an explicit "±50% order-of-magnitude" qualifier and the source year.
- No quantity scaling, regional adjustment, or processing-cost modeling — this would require data and models we cannot honestly provide.

**Environmental data rules:**
- Embodied energy and CO₂ footprint are for **primary production only** (cradle-to-gate, not cradle-to-grave).
- Secondary/recycled production values are stored separately when available: `embodied_energy_recycled`, `co2_footprint_recycled`.
- The UI shows the production route (primary vs. recycled) and source year.
- No lifecycle modeling, transport, or use-phase analysis — direct users to dedicated LCA tools for that.

### 4.8 Anisotropy & Directionality

For anisotropic materials (composites, wood, fabrics), directional properties use a structured approach:

```json
{
  "id": "cfrp-ud-t700-epoxy",
  "name": "CFRP UD Tape (T700/Epoxy)",
  "notes": "Unidirectional — all primary values are fibre direction (0°). Use the CLT tool for laminate-level properties.",
  "youngs_modulus": {
    "value": 135e9,
    "condition": "0° (fibre direction)",
    "source_id": "toray-t700s-ds"
  },
  "youngs_modulus_transverse": {
    "value": 10e9,
    "condition": "90° (transverse)",
    "source_id": "toray-t700s-ds"
  },
  "youngs_modulus_shear_12": {
    "value": 5e9,
    "condition": "in-plane shear (1-2)",
    "source_id": "toray-t700s-ds"
  },
  "tensile_strength": {
    "value": 2550e6,
    "condition": "0° (fibre direction)"
  },
  "tensile_strength_transverse": {
    "value": 69e6,
    "condition": "90° (transverse)"
  },
  "shear_strength_12": {
    "value": 95e6,
    "condition": "in-plane shear (1-2)"
  },
  "cte": {
    "value": -0.1e-6,
    "condition": "0° (fibre direction)"
  },
  "cte_transverse": {
    "value": 30e-6,
    "condition": "90° (transverse)"
  }
}
```

For **wood**, the convention is: bare property = along grain (L direction). `_transverse` = across grain (R/T average). Full L/R/T data can be stored with `condition` fields when available.

For **fabrics**: bare property = warp direction. `_transverse` = fill/weft direction. `areal_density` (kg/m²) replaces `density` as the primary mass metric. `weave_type` stored as a classification field.

**This is deliberately simpler than a full orthotropic stiffness tensor.** The CLT tool (§6.4) handles laminate-level stiffness computation from ply properties; the database stores ply-level engineering constants, not full C_ij matrices. For screening and selection, directional engineering constants with clear condition labels are sufficient.

### 4.9 Polymer-Specific Considerations

The critique correctly noted the schema was metal-centric. Additions for polymers:

| Field | Unit | Description |
|---|---|---|
| `water_absorption_24h` | % | Water absorption in 24h immersion (ASTM D570) |
| `moisture_absorption_equilibrium` | % | Equilibrium moisture content at 50% RH |
| `oxygen_permeability` | cm³·mm/(m²·day·atm) | O₂ permeability (packaging films) |
| `uv_resistance` | — | `excellent`, `good`, `fair`, `poor` |
| `chemical_resistance_acids` | — | `excellent`, `good`, `fair`, `poor` |
| `chemical_resistance_bases` | — | `excellent`, `good`, `fair`, `poor` |
| `chemical_resistance_solvents` | — | `excellent`, `good`, `fair`, `poor` |

For conditioned polymers (e.g., PA66 dry vs. conditioned at 50% RH), these are stored as **separate material records** with distinct IDs:

```
pa66-dry          → "PA66 (Dry, as-molded)"
pa66-conditioned  → "PA66 (Conditioned, 50% RH equilibrium)"
```

This avoids overloading a single record with multi-condition data while keeping the query model simple. The `notes` field and a `related_ids` array link conditioned variants to each other.

### 4.10 Foam-Specific Fields

| Field | Type | Unit | Description |
|---|---|---|---|
| `relative_density` | float | — | ρ_foam / ρ_solid (0–1) |
| `cell_type` | string | — | `open`, `closed`, `mixed` |
| `base_material_id` | string | — | Reference to the solid parent material |

### 4.11 Fabric-Specific Fields

| Field | Type | Unit | Description |
|---|---|---|---|
| `areal_density` | float | kg/m² | Mass per unit area (primary mass metric for fabrics) |
| `weave_type` | string | — | `plain`, `twill`, `satin`, `unidirectional`, `nonwoven` |
| `fibre_material_id` | string | — | Reference to the fibre material |

### 4.12 Axis Compatibility & Cross-Family Plotting Rules

Not every numeric property is meaningful for every `record_kind`. The Explorer must prevent nonsensical charts:

1. **Fabrics** (`record_kind: "fabric"`) use `areal_density` (kg/m²) as their mass metric, not volumetric `density` (kg/m³). When the X or Y axis is `density`, fabric records are excluded from the chart. When the axis is `areal_density`, only fabric records are plotted. The UI shows a note explaining why some materials are absent.

2. **Foams** have volumetric `density` (which is meaningful — it's the bulk foam density). They are included in `density`-axis charts.

3. **Performance indices that use `density`** (e.g., E/ρ, σ_y/ρ) automatically exclude fabrics, because the index would be dimensionally wrong. The ranking engine checks `required_properties` against the material's available properties and skips materials with `null` for any required property.

4. **The Compare mode** warns when comparing materials of different `record_kind` (e.g., a bulk alloy vs. a sandwich panel) — "These are different types of records; property comparisons may not be meaningful."

5. **The Browse mode** shows `record_kind` as a filterable column and displays the appropriate mass metric (density or areal_density) for each row.

### 4.13 Composite-Specific Fields

| Field | Type | Unit | Description |
|---|---|---|---|
| `fiber_volume_fraction` | float | — | V_f (0–1). Critical for composites — a 60% V_f CFRP and a 40% V_f one are different materials. |
| `fiber_material_id` | string | — | Reference to the fibre material (e.g., `carbon-t700s`) |
| `matrix_material_id` | string | — | Reference to the matrix material (e.g., `epoxy-generic`) |
| `ply_thickness` | float | m | Nominal cured ply thickness (for CLT input) |

### 4.14 Polymer Display Notes

For **semi-crystalline polymers** (PA, POM, PET, PEEK), both `glass_transition_temp` and `melting_point` may be populated. T_g marks a ductile-to-leathery transition but not failure; the part doesn't fail until near T_m. For **amorphous polymers** (PC, PMMA, PS), T_g is the practical upper limit — the part softens catastrophically. The material card UI should label T_g with context: "T_g (amorphous — service limit)" vs. "T_g (semi-crystalline — secondary transition; see T_m for failure)" based on whether `melting_point` is null or not.

---

## 5. Data Architecture

### 5.1 File Structure

```
data/
└── materials/
    ├── schema.json              # JSON Schema for validation
    ├── materials.json           # The database (sources + materials in one file)
    ├── README.md                # Data sources, citation guide, contribution instructions
    └── validation/
        └── validate.py          # Offline validation script (runs schema checks + consistency)
```

No per-family working files. `materials.json` is the single source of truth. Data entry happens directly in `materials.json` (or via a future contribution workflow). The per-family "sources/" directory from the v1 plan is removed — it created an ambiguous provenance trail.

### 5.2 Why JSON

Alternatives considered:

| Format | JS-native | Py-native (Pyodide) | Nested structures | Human-editable at scale | Git-diffable | Agent-editable | Schema evolution |
|---|---|---|---|---|---|---|---|
| **JSON** | Yes | Yes (stdlib) | Yes | Fair | Yes | Yes (Read/Edit/Grep) | Trivial (add keys) |
| CSV | Trivial parser | Yes (stdlib) | No | Excellent (spreadsheet) | Excellent | Yes | Add columns |
| SQLite | No (needs sql.js) | Yes (stdlib) | Via normalization | No (binary) | No (binary blob) | No (needs SQL via Bash) | ALTER TABLE migrations |
| YAML | No (needs js-yaml) | No (needs PyYAML wheel) | Yes | Good | Yes | Yes | Trivial |
| Python source | No | Yes | Yes | Fair | Yes | Yes | Trivial |

**JSON wins because:**
1. **Both runtimes read it natively** — `fetch().json()` in JS, `json.loads()` in Python stdlib. Zero dependencies.
2. **Supports the rich datum model** — nested `{value, min, max, source_id, basis}` objects fit naturally.
3. **Agent-friendly** — Claude Code can Read, Edit, Grep, and diff JSON files directly. A binary database (SQLite) would require running SQL commands through Bash for every inspection or edit.
4. **Schema evolution is free** — adding a new property is just adding a key. Old records without it parse fine (`null` by default). No migrations, no `ALTER TABLE`, no versioning. This matters when the schema is actively growing.
5. **Git-diffable** — you can see exactly which materials changed in a PR.
6. **Schema-validatable** — JSON Schema catches errors before runtime.

**What JSON is bad at:** hand-editing 1000+ records in a text editor. This is a real pain point that will arrive.

**SQLite was seriously considered and rejected** for three reasons beyond the js-dependency story: (a) binary files are opaque to git — every commit is a full-file replacement with no meaningful diff, blame, or merge; (b) an AI agent cannot inspect or edit it without running SQL through Bash, making collaborative data maintenance much harder; (c) schema migrations become a versioned process when fields change, whereas JSON just gains new keys. The query power of SQL is real, but for the access patterns of this tool (load all, filter in memory, rank), it doesn't buy enough to justify the costs.

### 5.3 Payload Size & Scaling Strategy

**Near-term (Milestones 1–2, ≤ 150 materials):**
- 150 materials × ~40 properties × mixed scalar/rich form ≈ 800 KB–1.2 MB uncompressed
- Gzip compression (Netlify serves automatically) → **100–240 KB transferred**
- Single `materials.json` file. No splitting needed.

**Medium-term (300–1000 materials):**
- Estimated 3–8 MB uncompressed, 400 KB–1 MB gzipped
- Still a single file — Plotly.js alone is ~1 MB gzipped and loads fine
- If load time becomes noticeable, split into: `materials-index.json` (id, name, family, 5 key scalar properties for chart rendering) + `materials-full.json` (lazy-loaded when a material card is opened)

**Long-term (1000+ materials):**
- JSON remains the single format. No CSV authoring layer, no dual-format pipelines — one source of truth in one file type, always.
- If JSON becomes unwieldy at extreme scale, the migration path is a full migration to a different store (not a translation layer on top of JSON). That decision is deferred until the pain is real.
- Tooling to help with bulk edits (validation scripts, schema checks) can improve the JSON editing experience without introducing a second format.

### 5.4 Property Registry

The critique correctly noted that exposing "any two numeric properties" as axes without a registry leads to meaningless plots. The database includes a top-level `property_registry` that defines metadata for each property:

```json
{
  "property_registry": {
    "density": {
      "label": "Density",
      "unit": "kg/m³",
      "display_unit": "kg/m³",
      "display_multiplier": 1,
      "symbol": "ρ",
      "latex": "\\rho",
      "axis_scale": "log",
      "higher_is": "neutral",
      "group": "mechanical",
      "plottable": true,
      "common": true,
      "description": "Bulk density"
    },
    "youngs_modulus": {
      "label": "Young's Modulus",
      "unit": "Pa",
      "display_unit": "GPa",
      "display_multiplier": 1e-9,
      "symbol": "E",
      "latex": "E",
      "axis_scale": "log",
      "higher_is": "better",
      "group": "mechanical",
      "plottable": true,
      "common": true,
      "description": "Tensile elastic modulus"
    },
    "yield_strength": {
      "label": "Yield Strength",
      "unit": "Pa",
      "display_unit": "MPa",
      "display_multiplier": 1e-6,
      "symbol": "σ_y",
      "latex": "\\sigma_y",
      "axis_scale": "log",
      "higher_is": "better",
      "group": "mechanical",
      "plottable": true,
      "common": true,
      "description": "0.2% offset yield strength (tensile)"
    },
    "poissons_ratio": {
      "label": "Poisson's Ratio",
      "unit": null,
      "display_unit": null,
      "display_multiplier": 1,
      "symbol": "ν",
      "latex": "\\nu",
      "axis_scale": "linear",
      "higher_is": "neutral",
      "group": "mechanical",
      "plottable": true,
      "common": false,
      "description": "Poisson's ratio"
    },
    "rohs_compliant": {
      "label": "RoHS Compliant",
      "unit": null,
      "group": "environmental",
      "plottable": false,
      "common": false,
      "description": "RoHS compliance status"
    }
  }
}
```

**Key metadata:**
- `plottable`: boolean — only properties marked `true` appear in axis dropdowns. Booleans, strings, and categorical fields are `false`.
- `common`: boolean — properties marked `true` appear first in axis dropdowns (density, modulus, strength, cost, thermal conductivity, CTE — the 6–8 most frequently used). All other plottable properties appear in an "Advanced" sub-section. This prevents the dropdown from being an overwhelming list of 30+ properties.
- `axis_scale`: `log` or `linear` — default axis scaling. Most mechanical/thermal properties are `log`; Poisson's ratio, elongation are `linear`.
- `higher_is`: `better`, `worse`, or `neutral` — used by the comparator to color-code best/worst.
- `group`: `mechanical`, `thermal`, `electrical`, `economic`, `environmental`, `processability` — for organizing the property browser and filtering axis dropdowns.
- `display_unit` / `display_multiplier`: The unit and multiplier for human-friendly display. **All data is stored in base SI** (Pa, kg/m³, W/(m·K), etc.), but the UI displays in engineering units (GPa, MPa, etc.) by multiplying the stored value by `display_multiplier`. Python calculates in SI; JS displays in `display_unit`. This avoids the "type 210000000000 for steel" problem.

This registry is the **single source of truth** for property display names, units, symbols, and axis behavior across all tools.

### 5.5 Computed Virtual Properties

Some useful quantities are derived from stored properties and should not be stored independently (to avoid consistency errors). The query layer computes these on demand and exposes them alongside stored properties:

| Virtual Property | Formula | Unit |
|---|---|---|
| `thermal_diffusivity` | k / (ρ · Cₚ) | m²/s |
| `specific_stiffness` | E / ρ | Pa·m³/kg |
| `specific_strength` | σ_y / ρ | Pa·m³/kg |
| `volumetric_heat_capacity` | ρ · Cₚ | J/(m³·K) |
| `price_per_m3` | price_per_kg · ρ | USD/m³ |

Virtual properties are included in the property registry with a `computed: true` flag and their formula, so the UI can display them in axis dropdowns and the Background tab can show the derivation.

### 5.6 Migration Strategy for Existing Material Data

The repo already has ~100 material entries across 16 pycalcs modules. The migration strategy:

**Principle: Shared base properties go to `materials.json`. Tool-specific model coefficients stay in the tool module.**

| Module | Data | Migration |
|---|---|---|
| `materials.py` | 7 materials (ρ, E, σ_y) | → Merge into `materials.json`. Refactor `rank_materials_for_ashby()` to load from database. |
| `heatsinks.py` | 4 materials (k, emissivity) | → Base materials (Al 6063-T5, Al 6061-T6, Cu C110) go to `materials.json`. Emissivity (surface-treatment-dependent) stays tool-local as a finish preset. |
| `fasteners.py` | 14 bolt grades | → **Stay tool-local.** These are bolt-grade mechanical property tables, not general material records. The proof strength, tensile strength, and yield strength of a Grade 8.8 bolt depend on the fastener standard, not the base steel. |
| `interference_fits.py` | 13 material presets (E, ν, σ_y, CTE) | → Base materials go to `materials.json`. The tool reads from the database for its preset dropdown. |
| `fracture_mechanics.py` | 6 materials (K_IC, Paris law) | → K_IC goes to `materials.json`. Paris law coefficients (C, m) are **model-specific fatigue parameters**, not material properties — they stay tool-local. |
| `beam_analysis.py` | 9 materials (E, σ_y, ρ, ν) | → Merge base properties into `materials.json`. Tool reads from database. |
| `fatigue.py` | 4 metal + 4 polymer presets | → Base properties (σ_uts, σ_y) go to `materials.json`. Fatigue coefficients (Basquin exponents, surface/size/reliability factors) stay tool-local — these are model-calibrated parameters. |
| `polymer_fatigue.py` | 1 detailed preset (PA66-GF50) | → Base properties to `materials.json`. Energy/creep surrogate coefficients stay tool-local. |
| `resonators.py` | 4 materials (E, ρ) | → Merge into `materials.json`. Tool reads from database. |
| `structural_resonance.py` | 4 materials (E, ρ, ν) | → Merge into `materials.json`. Tool reads from database. |
| `motor_thermal.py` | 4 Cp constants | → Merge into `materials.json`. Motor presets (geometry, winding data) stay tool-local. |
| `decking.py` | 12 building materials | → **Stay tool-local.** These are construction product specifications (cost/ft, board dimensions), not engineering material properties. |
| `energy_density.py` | 7 energy sources | → **Stay tool-local.** Energy density of fuels/batteries is a system-level property, not a material property. |
| `beverages.py` | 4 cup materials | → **Stay tool-local.** Empirical cooling coefficients, not material properties. |
| `example_advanced.py` | 4 example materials | → **Stay as-is.** These are fictional example data. |

**Migration process:**
1. For each module marked "→ Merge," extract the base properties and add the material to `materials.json` (or verify it already exists from direct data entry).
2. Refactor the tool module to accept material properties as function arguments (instead of hardcoded lookups) or to load from the shared database.
3. Keep the tool's preset dropdown working — it should offer the same preset names, but the underlying data comes from `materials.json`.
4. Run existing tests to verify backward compatibility.
5. Tool-local model coefficients (Paris law, fatigue exponents, etc.) stay in their modules, keyed by material ID so they can cross-reference the shared database.

**Identity reconciliation policy:**
Tool presets often use informal names ("Steel", "Aluminum", "Cast Iron") that don't map to a single canonical material. The rules:
- **Generic presets** (e.g., `beam_analysis.py`'s "Structural Steel (A36)") map to specific canonical IDs (e.g., `steel-a36`). The mapping is documented in a comment in the tool module.
- **Family placeholders** (e.g., `resonators.py`'s "Steel (AISI 1020)") map directly to their canonical ID (`steel-1020`).
- **"Custom" presets** stay tool-local. They are not migrated.
- When two tools have the same material with slightly different property values (e.g., beam_analysis and resonators both list "Aluminum 6061-T6" with different E), the database value wins. The tool tests are updated to use the database value. If this changes a test expectation by > 2%, investigate which source is more authoritative before updating.
- **Dual-source period**: During Milestone 4, tools may briefly have both a database lookup and a tool-local fallback. The fallback is removed before Milestone 4 exits. No tool ships with both a database import and a hardcoded duplicate of the same data.

---

## 6. Tool Roadmap

### Design Decision: Product Consolidation

The v1 plan proposed 10 separate standalone tools. The critique correctly identified that browser, comparator, substitution advisor, thermal selector, cost-performance, and multi-objective selector are mostly different views on the same selection engine. As separate tools they would duplicate logic, increase catalog sprawl, and dilute UX coherence.

**Revised structure: 1 primary explorer + 4 specialized analyzers.**

| Tool | Type | Purpose |
|---|---|---|
| **Materials Explorer** | Primary hub | Chart (Ashby), Browse (table), Compare, Substitute — unified tool with mode tabs |
| **CTE Mismatch Calculator** | Standalone analyzer | Thermal stress from dissimilar bonded materials |
| **Foam Property Estimator** | Standalone analyzer | Gibson-Ashby scaling laws |
| **Composite Laminate Estimator** | Standalone analyzer | Classical Laminate Theory |
| **Material Index Reference** | Educational reference | Derivations, scope, and worked examples for all indices |

The Materials Explorer replaces 6 standalone tools with a single tool that has 4 modes (tabs). This means:
- One shared data loading pipeline
- One Plotly chart instance with reconfigurable axes
- One material search/filter engine
- Cross-mode navigation (click material in chart → compare → substitute) without page loads

The thermal selector, cost-performance, and multi-objective workflows become **preset configurations** of the Explorer's chart and ranking modes, not separate tools.

### 6.1 Materials Explorer

**Slug**: `materials-explorer`

**What**: The primary materials tool — an interactive Ashby chart with integrated browsing, comparison, and substitution capabilities.

#### Mode 1: Chart (Ashby Chart)

**User jobs**:
- Pick any two plottable properties for axes (from the property registry)
- See all materials on a log-log scatter, colored by family
- Overlay performance index isolines
- Click any data point to see the material card with full sourced properties
- Filter by family, sub-family, or property range
- Rank and highlight top N materials for a chosen index
- Toggle between pre-built chart presets or build custom axes

**Chart presets** (pre-configured axis pairs + index):
- Young's modulus vs. density (stiffness selection)
- Strength vs. density (strength selection)
- Fracture toughness vs. strength (damage tolerance)
- Thermal conductivity vs. CTE (thermal design)
- Thermal conductivity vs. electrical resistivity (heatsink/insulator selection)
- Price per kg vs. strength (cost-performance)
- Embodied energy vs. strength (eco-selection)

**Visualization stack: Plotly.js** — not Chart.js. The repo already uses Plotly 2.27.0 across 25+ tools. Plotly provides out-of-the-box:
- Log-scale scatter plots
- Hover tooltips with custom HTML
- Click events for data point selection
- Lasso and box selection
- PNG/SVG export via `Plotly.toImage()`
- Legend toggling for family visibility
- Responsive layout

Custom isolines are rendered as Plotly `shapes` (lines with computed start/end points) — this is straightforward for power-law indices on log-log axes where isolines are straight lines with slope determined by the exponent.

**Isoline visibility rules:** Isolines are only meaningful when the selected axes correspond to the variables in the index expression. The rules:
1. Each `PerformanceIndex` declares `required_properties` (e.g., `("youngs_modulus", "density")` for E^(1/2)/ρ) and `chart_x`/`chart_y` (the suggested axis pairing).
2. **Isolines are shown** when the current X and Y axes exactly match `chart_x` and `chart_y` (in either order) for the selected index. The `isoline_slope` is defined for this specific axis pairing.
3. **Isolines are hidden** when the axes do not match the index's required properties. The UI shows a subtle note: "Switch to [suggested axes] to see isolines for this index."
4. For the **custom index** (user-specified exponents on user-selected properties), isolines are always valid because the user is defining both the axes and the index simultaneously — the slope is computed from the exponents.
5. When isolines are hidden, the ranking still works — materials are still scored and highlighted by the index. Only the visual guide lines are suppressed, because drawing them on unrelated axes would be misleading.

**Inputs**:
- X-axis property (dropdown filtered to `plottable: true` properties)
- Y-axis property (dropdown)
- Performance index (dropdown of presets — see §6.2 — or "Custom" which expands exponent inputs)
- Family filter (multi-select checkboxes with family colors)
- Minimum performance index threshold (slider)
- Number of highlighted candidates (1–20)
- Range display toggle (show min/max range bars on data points when available)

**Outputs**:
- Interactive Plotly scatter plot (primary — visible immediately)
- Performance index isolines overlaid on the chart
- Ranked material table below the chart
- Clicked material detail card (drawer/panel, not a separate page)
- Export: PNG/SVG (chart), CSV (table), clipboard

#### Mode 2: Browse (Material Database)

**User jobs**:
- Search for a material by name, designation, or trade name
- Filter by family, property ranges, and processability
- Sort by any column
- Expand a row to see the full material card with all properties, sources, and confidence indicators

**Implementation**: Pure JS table (loads from `materials.json` directly, interactive before Pyodide finishes). Searchable, filterable, sortable. Expandable row detail shows every non-null property with unit, source citation, confidence tier badge, and range (if available).

#### Mode 3: Compare

**User jobs**:
- Select 2–6 materials for side-by-side comparison
- See all shared properties in a comparison table with best/worst color-coding
- View a quantitative comparison chart
- Export comparison

**Visualization**: **Parallel coordinates plot** or **grouped bar chart** rather than radar/spider chart. The critique correctly identified that radar charts are poor defaults for heterogeneous engineering properties — axes with different scales, mixed higher-is-better/worse logic, and sparse null coverage make radar charts misleading. Parallel coordinates (Plotly supports this natively) handle heterogeneous scales naturally and make trade-offs visually obvious.

**Inputs**:
- Material selectors (2–6 searchable dropdowns)
- Property group filter (mechanical, thermal, electrical, all)

**Outputs**:
- Side-by-side comparison table with per-property best/worst highlighting
- Parallel coordinates chart (one line per material, one axis per property)
- Property-by-property percentage delta table
- Source citations for each compared value

**Sparsity filter**: With 40+ properties and typical materials only having 15–25, the comparison table would be 50–70% empty cells. By default, rows where **all** selected materials have `null` for that property are hidden. A toggle ("Show all properties") reveals the full table. This keeps the default view dense and useful.

#### Mode 4: Substitute

**User jobs**:
- Select a reference material
- Choose which properties matter (with weights)
- Set tolerance bands
- See ranked substitution candidates with match scores

**Inputs**:
- Reference material (searchable dropdown)
- Properties to match (checkboxes with weight sliders)
- Tolerance (global % or per-property)
- Hard constraints (family, processability, max temp, etc.)

**Outputs**:
- Ranked candidates with overall match score
- Per-property gap analysis (within/marginal/outside tolerance, color-coded)
- "Compare" button to switch to Compare mode with reference + top candidates pre-loaded

### 6.2 Performance Index Library

The v1 plan had internal inconsistencies and unjustified indices. The revised library is sourced, scoped, and consistent.

**Architecture**: Each index is defined as a structured record, not a free-form expression string:

```python
@dataclass(frozen=True)
class PerformanceIndex:
    id: str                    # e.g., "stiff_light_beam"
    name: str                  # e.g., "Stiff, light beam"
    expression_display: str    # e.g., "E^(1/2) / ρ" (for UI display)
    expression_latex: str      # e.g., "\\frac{E^{1/2}}{\\rho}"
    required_properties: tuple[str, ...]  # e.g., ("youngs_modulus", "density")
    compute: Callable          # function(material) -> float | None
    derivation: str            # One-paragraph derivation summary
    scope: str                 # When this index applies / does not apply
    source: str                # Citation
    maximize: bool             # True = higher is better
    chart_x: str               # Suggested X-axis property for this index
    chart_y: str               # Suggested Y-axis property for this index
    isoline_slope: float       # Slope on log-log chart (for rendering isolines)
```

**Why not free-form expression evaluation**: The v1 plan proposed `rank_by_index(materials, "E**0.5 / density")` with arbitrary expression strings. This has three problems:
1. **Security**: `eval()` on user input is dangerous, even in a Pyodide sandbox.
2. **Null handling**: Arbitrary expressions can't gracefully handle materials missing one of the required properties.
3. **Syntax ambiguity**: `E^0.5` (display) vs. `E**0.5` (Python) vs. `Math.pow(E, 0.5)` (JS) — no unified syntax.

Instead, each index has a named `compute` function in Python that handles null properties (returns None), and the expression string is display-only. Users select from the preset library. A "Custom index" option lets users define new indices by specifying exponents for a generalized form:

$$M = \frac{P_1^{a_1} \cdot P_2^{a_2}}{P_3^{a_3}}$$

where P₁, P₂, P₃ are selected properties and a₁, a₂, a₃ are numeric exponents entered in input fields (not parsed from a string). This is safe, explicit, and null-aware.

**The index library** (all sourced from Ashby 2011 Ch. 5–6 unless noted):

| # | ID | Name | Expression | Scope | Isoline slope (log-log) |
|---|---|---|---|---|---|
| 1 | `stiff_light_tie` | Stiff, light tie | E / ρ | Fixed length, axial stiffness | 1 |
| 2 | `stiff_light_beam` | Stiff, light beam | E^(1/2) / ρ | Fixed length, bending stiffness | 2 |
| 3 | `stiff_light_plate` | Stiff, light plate | E^(1/3) / ρ | Fixed length, bending stiffness (plate) | 3 |
| 4 | `strong_light_tie` | Strong, light tie | σ_y / ρ | Fixed length, yield in tension | 1 |
| 5 | `strong_light_beam` | Strong, light beam | σ_y^(2/3) / ρ | Fixed length, yield in bending | 3/2 |
| 6 | `strong_light_plate` | Strong, light plate | σ_y^(1/2) / ρ | Fixed length, yield in bending (plate) | 2 |
| 7 | `max_elastic_energy_mass` | Max elastic stored energy / mass | σ_y² / (E·ρ) | Springs, elastic energy storage | — |
| 8 | `max_elastic_energy_vol` | Max elastic stored energy / volume | σ_y² / E | Springs, elastic energy storage (fixed vol) | — |
| 9 | `damage_tolerant` | Damage-tolerant design | K_IC / σ_y | Leak-before-break; flaw-tolerant structures | — |
| 10 | `thermal_shock` | Thermal shock resistance | σ_f / (E·α) | Sudden ΔT, resist fracture. Ashby 2011 §11.7 | — |
| 11 | `thermal_distortion` | Thermal distortion resistance | k / (E·α) | Minimize warping under heat flux. Ashby 2011 §11.7 | — |
| 12 | `heat_spreading_mass` | Heat spreading per unit mass | k / ρ | Lightweight heat spreaders (specific thermal conductivity) | 1 |
| 13 | `thermal_storage_vol` | Volumetric thermal storage | ρ·Cₚ | Thermal mass, energy storage. NOT heat sink performance — see scope note. | — |
| 14 | `thermal_insulation` | Thermal insulation | 1 / k | Minimize heat loss | — |
| 15 | `stiff_cheap_beam` | Stiff, cheap beam | E^(1/2) / (ρ·C_m) | Minimum-cost stiff beam. C_m = price_per_kg. | — |
| 16 | `strong_cheap_tie` | Strong, cheap tie | σ_y / (ρ·C_m) | Minimum-cost strong tie. C_m = price_per_kg. | — |

**Scope note on index #13 (was "heat sink" in v1)**: The v1 plan labeled ρ·Cₚ as "Heat sink (max heat dissipation)." The critique correctly identified this as wrong — ρ·Cₚ is volumetric heat capacity (thermal storage), not heat dissipation. Heat sink performance depends on k, fin geometry, and convection coefficient, not volumetric heat capacity. The index is relabeled "Volumetric thermal storage" with appropriate scope.

**Scope note on buckling**: The v1 plan listed "Buckling-limited column" as E^(1/3)·σ_y^(2/3)/ρ in one place and E^(1/2)/ρ in another. These are different indices for different failure modes:
- E^(1/2)/ρ is the standard Euler buckling index (elastic instability, long columns) — equivalent to the stiff-beam index.
- E^(1/3)·σ_y^(2/3)/ρ is a combined buckling + yielding index for intermediate columns.
The v1 inconsistency is resolved: the Euler buckling index is `stiff_light_beam` (#2). There is no separate "combined buckling+yielding" index in the v1 library because it conflates two failure modes without specifying the slenderness regime. It could be added in a future version with proper derivation and scope limits.

### 6.3 CTE Mismatch Calculator

**Slug**: `cte-mismatch`

**What**: Calculate thermal stresses and curvature arising from CTE mismatch between bonded dissimilar materials.

**Scoping (addressing the critique)**: This tool computes **idealized elastic stresses and curvature** in a bimetallic/bilayer strip geometry using Timoshenko's classical theory. It does **not** predict delamination, fatigue, or interfacial failure — those require fracture mechanics, interface toughness data, and cyclic loading models that are beyond the scope of a screening tool. The tool explicitly states this limitation in the UI and README.

**Model**: Timoshenko (1925) bimetallic strip theory only. Suhir's compliant-layer extension is out of scope for v1 (it adds significant complexity for a narrow use case).

**Inputs**:
- Material A (from database or manual entry: CTE, E, ν, thickness)
- Material B (same)
- Temperature at assembly (°C)
- Temperature at operating condition (°C)
- Geometry: strip width, length (for stress calculation)

**Outputs**:
- Curvature κ (1/m)
- Axial stress in each layer (Pa)
- Interfacial shear stress at the ends (Pa) — note: Timoshenko theory gives average; local peeling stresses at free edges are not modeled
- Stress-to-yield ratio for each layer (if materials from database have yield strength)
- Warning banner when stress > 0.5 × yield strength ("approaching yield — elastic model may not be accurate")
- Substituted equations with all values shown

**Equations**:

$$\kappa = \frac{6(\alpha_1 - \alpha_2)(T - T_0)(1 + m)^2}{h\left[3(1 + m)^2 + (1 + mn)\left(m^2 + \frac{1}{mn}\right)\right]}$$

where $m = h_1/h_2$, $n = E_1/E_2$, $h = h_1 + h_2$.

**Files**:
- `pycalcs/cte_mismatch.py` — calculation module
- `tests/test_cte_mismatch.py` — tests
- `tools/cte-mismatch/index.html` — UI
- `tools/cte-mismatch/README.md`

**Acceptance criteria**:
- [ ] Reproduces Timoshenko (1925) examples and Hsueh (2002) validation cases
- [ ] Materials can be selected from database or entered manually
- [ ] Handles silicon-on-FR4 (CTE ~3 vs ~17 ppm/K) and steel-on-aluminum cases
- [ ] Shows clear warning when stress exceeds 50% of yield
- [ ] Does NOT claim to predict delamination or fatigue

### 6.4 Composite Laminate Estimator (CLT)

**Slug**: `composite-laminate-estimator`

**What**: Estimate the effective in-plane and flexural stiffness of a composite laminate from ply properties and stacking sequence using Classical Laminate Theory.

**Models**: Classical Laminate Theory (Jones 1999; Daniel & Ishai 2006).

**Implementation note**: CLT requires 3×3 matrix multiplication, inversion, and rotation transforms. Without NumPy, this is ~80 lines of pure Python. The operations are:
- Q matrix from engineering constants (E₁, E₂, G₁₂, ν₁₂)
- Q-bar rotation for each ply angle
- A, B, D summation over plies
- Inversion of 3×3 for compliance
- Effective engineering constants from compliance

All are straightforward 3×3 operations.

**Inputs**:
- Ply material (from database composites section, or manual: E₁, E₂, G₁₂, ν₁₂, ply thickness, and optionally strengths)
- Stacking sequence text (e.g., `[0/45/-45/90]s`)
- Applied loads (optional: Nx, Ny, Nxy, Mx, My, Mxy)

**Stacking sequence parser**: Must handle:
- `[0/90]s` → symmetric: [0, 90, 90, 0]
- `[0/±45/90]s` → [0, 45, -45, 90, 90, -45, 45, 0]
- `[0/90]2s` → [0, 90, 0, 90, 90, 0, 90, 0]
- `[0_3/90]` → [0, 0, 0, 90]

**Outputs**:
- A, B, D stiffness matrices (displayed as formatted 3×3)
- Effective engineering constants: E_x, E_y, G_xy, ν_xy
- Ply-by-ply stress/strain (if loads applied)
- First ply failure: load multiplier and failing ply (max stress criterion; Tsai-Wu is v2)
- Polar plot of E(θ) showing directional stiffness

**Files**:
- `pycalcs/composite_laminate.py`
- `tests/test_composite_laminate.py`
- `tools/composite-laminate-estimator/index.html`
- `tools/composite-laminate-estimator/README.md`

**Acceptance criteria**:
- [ ] Reproduces Jones (1999) Example 4.3 or equivalent textbook case
- [ ] Symmetric layups produce B ≈ 0 (within float precision)
- [ ] Quasi-isotropic layup [0/±60]s gives E_x ≈ E_y within 1%
- [ ] Stacking sequence parser handles all four notation forms above
- [ ] Polar plot renders correctly in Plotly

### 6.5 Foam Property Estimator

**Slug**: `foam-property-estimator`

**What**: Estimate foam properties from base material properties and relative density using Gibson-Ashby scaling laws.

**Models**: Gibson & Ashby (1997), Chapter 5.

**Inputs**:
- Base material (from database or manual: E_s, σ_ys, k_s, ρ_s)
- Relative density ρ*/ρ_s (0.01–0.5)
- Cell type (open / closed)
- Gas pressure inside cells (for closed-cell; default 1 atm)

**Outputs**:
- Estimated E*, σ*_pl (compressive), k*, ρ*
- Comparison to measured foam data from database (if base material has known foam entries)
- Confidence note: "Gibson-Ashby scaling is accurate to within a factor of ~2 for relative densities 0.05–0.3"

**Files**:
- `pycalcs/foam_properties.py`
- `tests/test_foam_properties.py`
- `tools/foam-property-estimator/index.html`
- `tools/foam-property-estimator/README.md`

**Acceptance criteria**:
- [ ] Reproduces Gibson & Ashby (1997) Table 5.1 examples within stated accuracy
- [ ] Open and closed cell models produce different results
- [ ] Relative density slider is smooth and monotonic
- [ ] Base material from database or manual entry

### 6.6 Material Index Reference

**Slug**: `material-index-reference`

**What**: An educational reference page with full derivations, scope notes, worked examples, and limitations for every performance index in the library. Not a calculator — a reference.

This serves the "verifying expert" and "curious student" personas. Each index gets:
- Full derivation from first principles (not just the formula)
- Scope: when it applies, when it doesn't, what assumptions it makes
- Worked example with real materials and numbers
- Common pitfalls (e.g., "this index assumes the cross-section shape is free; if shape is fixed, use a different index")
- Reference citation

**Relationship to "equations live in docstrings" rule**: The repo's convention is that Python docstrings are the single source of truth for equations. The index reference page does NOT duplicate equations independently — instead, `pycalcs/material_indices.py` stores the `derivation` and `scope` fields in each `PerformanceIndex` dataclass, and the reference page renders them via the standard `get_documentation()` pattern. The long-form derivations live in the module docstring and per-index `derivation` fields, not in standalone HTML. This keeps one source of truth while allowing the reference page to present them in a more readable educational format.

**Files**:
- `tools/material-index-reference/index.html` — renders content from `material_indices.py` docstrings
- `tools/material-index-reference/README.md`
- (The content source is `pycalcs/material_indices.py` — no separate educational text file)

---

## 7. Python & JavaScript Module Design

### 7.1 Python Modules

| Module | Purpose | Key Functions |
|---|---|---|
| `pycalcs/material_db.py` | Database query layer | `load_database()`, `get_value()`, `filter_materials()`, `rank_by_index()`, `compare_materials()`, `find_substitutes()`, `get_computed_property()` |
| `pycalcs/material_indices.py` | Performance index library | `INDICES` dict, `compute_index()`, `get_isoline_points()` |
| `pycalcs/cte_mismatch.py` | CTE mismatch calculator | `calculate_cte_mismatch()` |
| `pycalcs/composite_laminate.py` | CLT calculations | `parse_layup()`, `compute_abd()`, `effective_constants()`, `first_ply_failure()` |
| `pycalcs/foam_properties.py` | Gibson-Ashby scaling | `estimate_foam_properties()` |
| `pycalcs/materials.py` | **Preserved** (backward compat) | `rank_materials_for_ashby()` — refactored to delegate to `material_db.py` |

Each module has a corresponding `tests/test_*.py` file.

### 7.2 JavaScript Modules

| Module | Purpose |
|---|---|
| `shared/ashby-plot.js` | Plotly-based Ashby chart: scatter, isolines, family colors, click handler, export |
| `shared/material-table.js` | Sortable, filterable material table (pure JS, no Pyodide dependency) |
| `shared/material-card.js` | Material detail card renderer (properties, sources, confidence badges) |

### 7.3 Query Layer Design

The `get_value()` function transparently handles both scalar and rich datum forms:

```python
def get_value(material: dict, property_name: str) -> float | None:
    """Extract the numeric value from a property, handling both scalar and rich forms."""
    raw = material.get(property_name)
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, dict):
        return float(raw["value"]) if raw.get("value") is not None else None
    return None

def get_range(material: dict, property_name: str) -> tuple[float, float] | None:
    """Extract min/max range. Returns None for scalar form (no range data)."""
    raw = material.get(property_name)
    if isinstance(raw, dict) and raw.get("min") is not None and raw.get("max") is not None:
        return (float(raw["min"]), float(raw["max"]))
    return None

def get_source(material: dict, property_name: str, sources: dict) -> dict | None:
    """Get the source record for a property datum."""
    raw = material.get(property_name)
    if isinstance(raw, dict) and raw.get("source_id"):
        return sources.get(raw["source_id"])
    return sources.get(material.get("default_source_id"))

def get_basis(material: dict, property_name: str) -> str:
    """Get the confidence tier. Defaults to 'typical' if not specified."""
    raw = material.get(property_name)
    if isinstance(raw, dict):
        return raw.get("basis", "typical")
    return "typical"
```

---

## 8. Data Sourcing Strategy

### Primary Sources (Open / Freely Available)

1. **Ashby, M. F. (2011). *Materials Selection in Mechanical Design*, 4th ed.** — Appendix tables with ~70 material families, property ranges. Primary source for Ashby chart data and index derivations.
2. **Callister & Rethwisch (2018). *Materials Science and Engineering: An Introduction*, 10th ed.** — Property tables in appendices.
3. **MatWeb (matweb.com)** — Free tier provides property data for thousands of specific grades.
4. **ASM International handbooks** — Standard reference for metals data.
5. **CAMPUS plastics database (campusplastics.com)** — Manufacturer-supplied polymer data.
6. **Gibson & Ashby (1997). *Cellular Solids*, 2nd ed.** — Foam scaling laws and data.
7. **Daniel & Ishai (2006). *Engineering Mechanics of Composite Materials*, 2nd ed.** — CLT equations and ply data.
8. **Jones, R. M. (1999). *Mechanics of Composite Materials*, 2nd ed.** — CLT equations, worked examples.
9. **Manufacturer datasheets** — Toray (carbon fibre), DuPont (polymers), 3M (foams), etc.
10. **Hammond & Jones, *ICE Database* (Univ. of Bath)** — Embodied energy and CO₂ data.

### Data Licensing & Redistribution Policy

Material property data exists on a spectrum of openness. The database must respect intellectual property:

**Allowed to commit directly:**
- Individual property values from textbooks (Ashby, Callister, Gibson & Ashby, Jones) — these are factual data, not copyrightable expression. Always cite the source.
- Manufacturer datasheets — published specifically for public use. Cite the datasheet revision.
- MatWeb individual lookups — freely accessible per-property data. Cite the URL and access date.
- ICE Database (University of Bath) — open-access environmental data. Cite.
- Data derived from public standards (e.g., ASTM minimum yield for a grade).

**Citation-only (do not bulk-copy):**
- CES EduPack / Granta databases — proprietary. Individual cross-validation is acceptable ("verified against CES Level 2"), but bulk transcription of their curated ranges is not.
- MMPDS / CMH-17 — controlled distribution. Reference specific table numbers for traceability, but do not reproduce full tables.
- CAMPUS plastics — per-material lookups are free, but systematic scraping violates their terms.

**Blocked:**
- Any source that explicitly prohibits redistribution.
- Data behind paywalls that was not obtained through legitimate access.

Each source in the `sources` registry must have a `type` field (`textbook`, `vendor_datasheet`, `online_database`, `standard`, `handbook`) that makes the licensing category clear.

### Data Quality Rules

- **No invented data.** Every numeric value must be traceable to a source. This means either: (a) the property datum is in rich form with its own `source_id`, or (b) the property is in scalar form and the material's `default_source_id` covers it. The rule is: every material must have a `default_source_id`, and any property whose source differs from the default must use rich form with an explicit `source_id`. This is not the same as requiring `source_id` on every datum — it's requiring that the fallback chain always resolves.
- **Ranges are first-class data.** When a source gives a range, store `min`, `max`, and `value` (midpoint or typical). The Ashby chart can display range bars.
- **Null is better than wrong.** Unknown properties are `null`, not estimated. Tools must handle nulls gracefully (skip in rankings, show "—" in tables).
- **Conditions matter.** Properties are at room temperature (20–25°C) unless the `condition` field says otherwise. For polymers, specify moisture state. For metals, specify heat treatment.
- **Separate records for separate conditions.** PA66 dry vs. conditioned are different records. 6061-O vs. 6061-T6 are different records.

---

## 9. Implementation Milestones

The v1 plan used "sessions" as a scheduling unit, which the critique correctly identified as non-credible. The revised plan uses **milestone-based exits** — each milestone has specific acceptance criteria and can be shipped independently.

### Milestone 1: Foundation

**Scope**: Material database, query layer, property registry, source registry, and basic Ashby chart.

**Exit criteria**:
- [ ] `data/materials/schema.json` exists and validates `materials.json`
- [ ] `materials.json` contains ≥ 60 materials across all P0 families (steels, aluminum, titanium, commodity polymers, engineering polymers, thermosets, CFRP, GFRP)
- [ ] Every material has `default_source_id` pointing to a valid source in the registry
- [ ] For the 5 critical ranking properties (`density`, `youngs_modulus`, `yield_strength`, `tensile_strength`, `thermal_conductivity`), ≥ 50% of non-null datums use rich form with min/max range. These are the properties most used in Ashby charts and performance indices — range data here is essential for credible screening.
- [ ] `pycalcs/material_db.py` passes all unit tests (load, filter, rank, get_value, get_range, get_source, get_basis)
- [ ] `pycalcs/material_indices.py` implements all 16 indices with compute functions
- [ ] `shared/ashby-plot.js` renders a Plotly scatter with family colors and isolines
- [ ] `tools/materials-explorer/index.html` exists with Chart mode working (axes selectable, families toggleable, isolines correct, click-to-inspect shows material card)
- [ ] `tools/ashby-chart/index.html` contains a redirect to `../materials-explorer/` (preserves old bookmarks/links)
- [ ] `catalog.json` updated: old ashby-chart entry replaced with materials-explorer entry
- [ ] Existing `tests/test_materials.py` still pass (backward compat)
- [ ] Offline validation script passes on `materials.json`

**What ships to users**: An interactive Ashby chart with 60+ materials, family coloring, selectable axes, performance index isolines, and click-to-inspect with sourced property cards. Massive upgrade from the current text-only 7-material ranking.

**Slug resolution**: The canonical path is `tools/materials-explorer/`. The old `tools/ashby-chart/index.html` becomes a lightweight redirect page (HTML meta-refresh + JS `window.location` fallback) so existing bookmarks and external links don't break. The catalog entry points to `materials-explorer`. There is no ambiguity: `materials-explorer` is the product, `ashby-chart` is a redirect.

### Milestone 2: Explorer

**Scope**: Full Materials Explorer with all 4 modes (Chart, Browse, Compare, Substitute) and database expansion.

**Exit criteria**:
- [ ] `materials.json` contains ≥ 120 materials across P0 + P1 families
- [ ] Browse mode: searchable, filterable, sortable table with expandable detail cards
- [ ] Compare mode: side-by-side table + parallel coordinates chart for 2–6 materials
- [ ] Substitute mode: weighted property matching with tolerance bands and gap analysis
- [ ] CSV export from browse and compare modes
- [ ] PNG/SVG export from chart and compare modes
- [ ] Cross-mode navigation works (chart → click → compare)
- [ ] Mobile-responsive layout
- [ ] URL state sharing encodes material selections and axis configuration
- [ ] Registered in `catalog.json`
- [ ] `shared/material-table.js` and `shared/material-card.js` implemented and reusable

**What ships to users**: A unified materials selection hub that replaces the old Ashby chart tool and adds browsing, comparison, and substitution capabilities.

### Milestone 3: Analyzers

**Scope**: CTE mismatch, CLT, and foam property tools.

**Exit criteria**:
- [ ] `pycalcs/cte_mismatch.py` + tests + tool HTML + README
- [ ] `pycalcs/composite_laminate.py` + tests + tool HTML + README
- [ ] `pycalcs/foam_properties.py` + tests + tool HTML + README
- [ ] Each tool reproduces at least one textbook validation case
- [ ] Each tool loads material presets from `materials.json`
- [ ] Each tool registered in `catalog.json`
- [ ] Background tabs include derivations and scope notes

**What ships to users**: Three specialized analysis tools that integrate with the materials database.

### Milestone 4: Migration & Polish

**Scope**: Migrate existing tool presets to shared database, expand database, add custom material entry, educational reference page.

**Exit criteria**:
- [ ] `materials.json` contains ≥ 150 materials
- [ ] At least 6 existing tools refactored to read base properties from `materials.json` (interference_fits, beam_analysis, resonators, structural_resonance, heatsinks base materials, fracture_mechanics K_IC)
- [ ] All existing tool tests still pass after migration
- [ ] Custom material entry: user can add a temporary material via a form and see it in the Explorer
- [ ] Material Index Reference page complete with derivations for all 16 indices
- [ ] Test-case JSON files for all new tools
- [ ] Cross-tool deep linking (Explorer → CTE mismatch, Explorer → CLT)
- [ ] `data/materials/README.md` contribution guide complete

---

## 10. File Manifest

### New Files

| File | Purpose |
|---|---|
| `data/materials/schema.json` | JSON Schema for material records |
| `data/materials/materials.json` | The material database (sources + materials) |
| `data/materials/README.md` | Data provenance, citation guide, contribution instructions |
| `data/materials/validation/validate.py` | Offline schema + consistency validation |
| `pycalcs/material_db.py` | Python query layer |
| `pycalcs/material_indices.py` | Performance index library |
| `pycalcs/cte_mismatch.py` | CTE mismatch calculator |
| `pycalcs/composite_laminate.py` | CLT calculations |
| `pycalcs/foam_properties.py` | Gibson-Ashby scaling |
| `tests/test_material_db.py` | Database query tests |
| `tests/test_material_indices.py` | Index computation tests |
| `tests/test_cte_mismatch.py` | CTE mismatch tests |
| `tests/test_composite_laminate.py` | CLT tests |
| `tests/test_foam_properties.py` | Foam property tests |
| `shared/ashby-plot.js` | Plotly-based Ashby chart component |
| `shared/material-table.js` | Sortable/filterable material table |
| `shared/material-card.js` | Material detail card renderer |
| `tools/materials-explorer/index.html` | Materials Explorer (4-mode hub) |
| `tools/materials-explorer/README.md` | |
| `tools/cte-mismatch/index.html` | CTE mismatch tool |
| `tools/cte-mismatch/README.md` | |
| `tools/composite-laminate-estimator/index.html` | CLT tool |
| `tools/composite-laminate-estimator/README.md` | |
| `tools/foam-property-estimator/index.html` | Foam property tool |
| `tools/foam-property-estimator/README.md` | |
| `tools/material-index-reference/index.html` | Index derivations reference |
| `tools/material-index-reference/README.md` | |

### Modified Files

| File | Changes |
|---|---|
| `pycalcs/materials.py` | Refactor to delegate to `material_db.py`; keep public API stable |
| `tools/ashby-chart/index.html` | Replace with redirect page pointing to `../materials-explorer/` |
| `catalog.json` | Replace old ashby-chart entry with materials-explorer; add all new tools |
| `tests/test_materials.py` | Verify backward compatibility |
| `pycalcs/interference_fits.py` | (Milestone 4) Refactor presets to load from database |
| `pycalcs/beam_analysis.py` | (Milestone 4) Refactor presets to load from database |
| `pycalcs/resonators.py` | (Milestone 4) Refactor presets to load from database |
| `pycalcs/structural_resonance.py` | (Milestone 4) Refactor presets to load from database |
| `pycalcs/heatsinks.py` | (Milestone 4) Refactor base material data to load from database |
| `pycalcs/fracture_mechanics.py` | (Milestone 4) Move K_IC to database; keep Paris law params tool-local |

---

## 11. Constraints & Non-Negotiables

1. **No external Python dependencies.** Pure `math`, `json`, `dataclasses`, `typing` only. CLT matrix operations implemented from scratch (~80 lines for 3×3).
2. **Single source of truth.** Equations/parameters in Python docstrings. Material data in `materials.json`. Property metadata in the property registry.
3. **Progressive disclosure.** Every tool immediately usable with sensible defaults. Advanced options in expandable sections.
4. **Loading overlay.** Required for all tools during Pyodide init.
5. **Responsive design.** Single-column layout below 900px.
6. **Mandatory README + tests.** Every tool directory has README.md. Every pycalcs module has test_*.py.
7. **URL state sharing.** Via `shared/url-state.js`.
8. **Catalog registration.** All tools in `catalog.json`.
9. **Plotly for visualization.** Consistent with the 25+ existing tools using Plotly 2.27.0.
10. **Property-level provenance.** Every datum traceable to a source via `source_id` or `default_source_id`.

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Database JSON too large** | Slow first load | Gzip (automatic on Netlify). 150 materials ≈ 1 MB raw → ~150 KB transferred. Monitor; split into index + detail if needed. |
| **Rich datum model inflates JSON** | Larger file, harder to maintain | Allow scalar shorthand for simple properties. Only use rich form where ranges/sources/conditions matter. |
| **CLT without NumPy** | More code to write | 3×3 matrix ops are ~80 lines. Well-understood math. Write once, test thoroughly. |
| **Data entry is enormous** | Blocks tool development | Milestone 1 ships with 60 materials — enough for a useful tool. Expand incrementally in later milestones. |
| **Cost/environmental data unreliable** | Users make bad decisions | Mark as screening-grade with ±50% qualifier. Show source year. Exclude from rankings by default when basis = "estimate". |
| **Property coverage varies by family** | Sparse charts for some families | `null` for unknown properties. UI shows "—". Rankings skip nulls. |
| **Migration breaks existing tools** | Regressions | Milestone 4 (migration) has explicit backward-compat test requirements. Tools keep working during migration — presets read from database but fallback to tool-local data if database load fails. |
| **Plotly bundle size** | Extra 200 KB gzipped | Already loaded in 25+ tools. No incremental cost for materials tools. |

---

## 13. Success Criteria

The materials suite is "done" (Milestone 4 complete) when:

1. **Database**: ≥ 150 materials across ≥ 6 families, with property-level sourcing and confidence tiers.
2. **Ashby Chart**: Interactive Plotly scatter with selectable axes, family coloring, isolines, click-to-inspect with sourced property cards, and export.
3. **Explorer**: Unified tool with browse, compare (parallel coordinates), and substitute modes.
4. **Analysis**: CTE mismatch, CLT, and foam tools each reproduce at least one textbook validation case.
5. **Quality**: Every tool has README, unit tests, and Background tab with derivations.
6. **Provenance**: Every property value traceable to a cited source. Confidence tier visible in the UI.
7. **Performance**: Materials Explorer loads and renders the chart within 5 seconds on typical broadband.
8. **Migration**: ≥ 6 existing tools refactored to use shared database for base material properties.

---

## 14. What This Plan Does NOT Cover

- **Finite element analysis** — out of scope for browser-based tools.
- **Fatigue life prediction** — handled by existing fatigue tools.
- **Creep analysis** — future tool, not part of this suite.
- **Corrosion databases** — too specialized and environment-dependent.
- **Manufacturing process selection** — processability flags are for screening; detailed process selection (volume economics, tolerances, surface finish) requires its own dedicated tool.
- **Real-time pricing** — no server-side capability; cost data is static and screening-grade.
- **User accounts / cloud storage** — fully client-side.
- **Material certification / compliance** — educational/preliminary tool, not a certified database.
- **Viscoelastic spectra, permeability families, swelling models** — these require curve data (not scalar properties) and specialized visualization. They belong in domain-specific tools (e.g., the polymer fatigue tool), not the general materials database.
- **Full orthotropic stiffness tensors** — the database stores engineering constants; the CLT tool computes laminate-level stiffness from those.

---

## Appendix A: Example Material Record (JSON, Rich Form)

```json
{
  "id": "al-6061-t6",
  "name": "Aluminium 6061-T6",
  "family": "metal",
  "sub_family": "aluminum-alloy",
  "record_kind": "bulk_material",
  "designation": "UNS A96061",
  "common_names": ["6061", "6061-T6", "AA6061"],
  "default_source_id": "ashby-2011-a1",
  "condition": "T6 (artificially aged)",
  "notes": "Most common general-purpose aluminium alloy. Wrought.",
  "related_ids": ["al-6061-o"],

  "density": 2700,
  "youngs_modulus": {
    "value": 69e9,
    "min": 68e9,
    "max": 71e9,
    "source_id": "matweb-al6061",
    "basis": "typical"
  },
  "shear_modulus": 26e9,
  "poissons_ratio": 0.33,
  "yield_strength": {
    "value": 276e6,
    "min": 241e6,
    "max": 290e6,
    "source_id": "asm-v2-al",
    "basis": "typical"
  },
  "tensile_strength": {
    "value": 310e6,
    "min": 290e6,
    "max": 340e6,
    "source_id": "asm-v2-al",
    "basis": "typical"
  },
  "compressive_strength": 276e6,
  "elongation_at_break": 0.12,
  "fracture_toughness": {
    "value": 29e6,
    "source_id": "ashby-2011-a1",
    "basis": "handbook_range",
    "notes": "Ashby gives 26–33 MPa·√m for 6000 series"
  },
  "fatigue_endurance_limit": {
    "value": 97e6,
    "source_id": "asm-v2-al",
    "basis": "typical",
    "condition": "R = -1, 10^7 cycles",
    "notes": "Aluminum has no true endurance limit; this is the fatigue strength at 10^7 cycles"
  },
  "hardness_vickers": 107,

  "thermal_conductivity": 167,
  "specific_heat": 896,
  "cte": 23.6e-6,
  "max_service_temp": 170,
  "min_service_temp": -269,
  "melting_point": 582,
  "glass_transition_temp": null,

  "electrical_resistivity": 3.99e-8,

  "price_per_kg": {
    "value": 2.5,
    "source_id": "market-estimate-2024",
    "basis": "estimate",
    "condition": "bar stock, qty 100 kg, US market",
    "notes": "Order-of-magnitude; actual price varies ±50% with form, quantity, and market conditions"
  },
  "embodied_energy": {
    "value": 200,
    "source_id": "ice-bath-2019",
    "basis": "typical",
    "notes": "Primary production, cradle-to-gate"
  },
  "co2_footprint": {
    "value": 12.5,
    "source_id": "ice-bath-2019"
  },
  "recyclability": "excellent",
  "rohs_compliant": true,

  "processability": [
    {"process": "machining", "rating": "excellent"},
    {"process": "welding", "rating": "good", "notes": "TIG, MIG; 4043 or 5356 filler"},
    {"process": "forming", "rating": "good", "notes": "T6 condition; anneal first for deep draws"},
    {"process": "casting", "rating": "fair", "notes": "Sand and investment casting possible"},
    {"process": "3d_printing", "rating": "good", "notes": "DMLS, EBM"}
  ]
}
```

---

## Appendix B: Critique Response Log

### Round 1 (initial critique)

| # | Critique | Response | Section |
|---|---|---|---|
| 1 | Data model too flat | Replaced with hybrid scalar/rich datum model | §4.2 |
| 2 | Ranges collapsed to midpoints | Ranges are now first-class: min/max stored, chart can display range bars | §4.2, §8 |
| 3 | Provenance not audit-grade | Source registry + per-property source_id | §4.4 |
| 4 | Curation pipeline unsafe | Removed per-family working files; single materials.json + validation script | §5.1 |
| 5 | No migration plan | Full migration matrix for all 16 modules | §5.6 |
| 6 | File manifest missing pycalcs modules | All tools now have corresponding pycalcs + test files in manifest | §10 |
| 7 | Schedule not credible | Replaced "sessions" with milestone-based exits with acceptance criteria | §9 |
| 8 | Arbitrary index eval unsafe | Replaced free-form expressions with structured PerformanceIndex records + exponent UI | §6.2 |
| 9 | Inconsistent buckling index | Resolved: Euler = stiff_light_beam; combined index removed with explanation | §6.2 scope note |
| 10 | Heat sink index wrong | Relabeled to "Volumetric thermal storage" with correct scope | §6.2, index #13 |
| 11 | Wrong charting stack | Switched to Plotly (already used in 25+ repo tools) | §6.1 |
| 12 | Payload size unrealistic | Revised estimate: 1 MB raw, ~150 KB gzipped. Split strategy if needed. | §5.3 |
| 13 | No confidence tiers | Added 6-tier basis model | §4.3 |
| 14 | No property registry | Added property_registry with plottable, axis_scale, higher_is, group | §5.4 |
| 15 | Anisotropy model too weak | Expanded with in-plane shear, condition labels, clear scope notes | §4.8 |
| 16 | Schema metal-centric | Added polymer fields (water absorption, chemical resistance, UV). Conditioned variants as separate records. | §4.9 |
| 17 | Processability too coarse | Replaced booleans with process objects (rating + notes) | §4.6 |
| 18 | Too many standalone tools | Consolidated to 1 Explorer (4 modes) + 4 analyzers | §6 design decision |
| 19 | No manufacturability workflow | Explicitly scoped as out-of-scope; processability is screening-only | §4.6, §14 |
| 20 | Cost/environmental too naive | Added explicit scoping rules, ±50% qualifier, source year requirement | §4.7 |
| 21 | CTE tool overclaims | Removed delamination/fatigue claims; explicit limitation statement | §6.3 |
| 22 | Success criteria partly marketing | Removed superlative claims; all criteria now measurable | §13 |
| 23 | Typos and correctness errors | Fixed: rohs_compliant spelling, melting_point clarified (crystalline only), thermal_diffusivity now computed-only | §4.6, §5.5 |
| 24 | Radar chart is poor default | Replaced with parallel coordinates (Plotly-native) | §6.1 Mode 3 |
| 25 | Custom material too loose | Deferred to Milestone 4; form must fill minimum required fields per tool | §9 Milestone 4 |

### Round 2 (Codex critique)

| # | Critique | Response | Section |
|---|---|---|---|
| C1 | Slug ambiguity (ashby-chart vs materials-explorer) | Resolved: `materials-explorer` is canonical, `ashby-chart` becomes redirect | §9 M1, §10 |
| C2 | Ranking semantics inconsistent for `estimate` basis | Definitive 6-rule ranking behavior added; estimate excluded by default; conservative/optimistic modes explicit | §4.3 |
| C3 | Isoline model too simplistic for arbitrary axes | Formalized 5-rule isoline visibility system: show only when axes match index variables | §6.1 |
| C4 | Only one datum per property per record | **Accepted as-is.** Multi-datum arrays per property add enormous query complexity for marginal benefit. Separate records for separate conditions (dry/conditioned, O/T6) is the right pattern for a JSON-based screening tool. | §4.9 |
| C5 | No record_kind field | Added `record_kind`: `bulk_material`, `lamina`, `laminate`, `sandwich`, `foam`, `fabric`, `product` | §4.5 |
| C6 | Sourcing rules conflict (source_id optional vs required) | Clarified: every value traceable via either own `source_id` or material's `default_source_id`. Fallback chain must always resolve. | §8 |
| C7 | No licensing/redistribution policy | Added full policy: allowed (textbooks, datasheets, MatWeb singles), citation-only (CES, MMPDS), blocked (restricted sources) | §8 |
| C8 | Migration identity reconciliation underplanned | Added reconciliation policy: generic→canonical mapping, database-wins rule, dual-source removal deadline | §5.6 |
| C9 | Processability filter semantics undefined | Defined numeric ordering (excellent=4 to not_recommended=0), default threshold (fair ≥ 2), absent = excluded | §4.6 |
| C10 | CSV source of truth conflict | Already fixed in prior revision (CSV authoring layer removed entirely) | §5.3 |
| C11 | Index reference conflicts with docstrings rule | Resolved: reference page renders content from `material_indices.py` docstrings, not independent text | §6.6 |
| C12 | Fabrics with areal_density vs volumetric density | Added axis-compatibility rules: fabrics excluded from density-axis charts, separate areal_density axis, cross-kind warnings | §4.12 |
| C13 | "≥30% rich form" is weak milestone gate | Replaced with: ≥50% rich form for 5 critical ranking properties (density, E, σ_y, σ_uts, k) | §9 M1 |
| C14 | vendor_datasheet trust too high | Softened: "may be optimistic (test conditions may differ)" | §4.3 |

### Round 2 (Gemini critique — practical engineering advice)

| # | Advice | Response | Section |
|---|---|---|---|
| G1 | Add display_unit/display_multiplier to registry | Added: stored in SI, displayed in engineering units (GPa, MPa). `display_multiplier` converts. | §5.4 |
| G2 | Add `common` flag for axis dropdown priority | Added: common properties shown first, others in "Advanced" sub-section | §5.4 |
| G3 | Add fiber_volume_fraction for composites | Added as §4.13 composite-specific fields (V_f, fiber/matrix IDs, ply thickness) | §4.13 |
| G4 | Ensure elongation_at_break is P0 | Already in schema. Will enforce as required for all P0 metals and polymers during data entry. | §4.6 |
| G5 | Galvanic series rank for v2 | Noted for future; out of scope for v1 | — |
| G6 | T_g vs T_m UI labeling for semi-crystalline vs amorphous | Added: UI labels T_g differently based on whether melting_point is null | §4.14 |
| G7 | Sparsity filter in Compare mode | Added: hide rows where all selected materials are null; toggle to show all | §6.1 Mode 3 |
| G8 | "Unit trap" (Pa vs GPa) | Addressed via display_multiplier in property registry | §5.4 |
| G9 | CTE bond layer disclaimer | Already scoped in §6.3; Timoshenko-only, no Suhir for v1, explicit rigid-bond assumption | §6.3 |
| G10 | Custom materials localStorage | Already planned for Milestone 4 | §9 M4 |
| G11 | Cross-tool state passing via URL | Already planned via url-state.js | §9 M4 |
| G12 | "Golden Seven" materials priority | Good advice — Milestone 1's 60-material target ensures these are present with rich data | §9 M1 |
| G13 | Chart → Lasso → Compare → Export flow | This is exactly the Explorer's cross-mode navigation design | §6.1 |
| G14 | Ashby chart range bars (error_x/error_y) | Plotly supports this natively; range display toggle already in inputs | §6.1 |
| G15 | Specific Strength index: clarify σ_y vs σ_uts | The index library uses `yield_strength` for σ_y indices and `tensile_strength` for σ_uts indices; the `required_properties` field makes this explicit | §6.2 |
