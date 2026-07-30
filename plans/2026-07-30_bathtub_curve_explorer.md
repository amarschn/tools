# Bathtub Curve Explorer

Date: 2026-07-30
Status: Proposed plan for critique before implementation

## Why this tool

The bathtub curve is the first picture every reliability course draws and one of
the least well served topics online. What exists is mostly a static JPEG with
three labelled regions. Nothing lets an engineer move the parameters and watch
the crossover ages move, which is where the actual decisions live: how long to
burn in, when the useful-life window really ends, whether preventive replacement
beats run-to-failure.

It also fills a gap the MTBF Calculator cannot. A single Weibull hazard,
`h(t) = (β/η)(t/η)^(β-1)`, is strictly monotone, so one fitted distribution can
never draw a bathtub. The curve only appears when several failure modes act at
once. Building it as a separate tool keeps that distinction honest: the MTBF
Calculator estimates from data, this one models from parameters.

"Bathtub curve" is a high-intent search term with weak incumbents, which matters
given that distribution is the current priority over tool count.

## Scope

A parameter-driven explorer, not an estimator. The user sets three competing
failure modes and reads the resulting curves. No data entry, no fitting. The
tool must say plainly that it draws a model, not a measurement, and link to the
MTBF Calculator for the data direction.

## The model

Competing risks: each mode can kill the unit independently, so the hazards add
and the reliabilities multiply.

```
h(t)  = Σ hᵢ(t) = Σ (βᵢ/ηᵢ)(t/ηᵢ)^(βᵢ-1)
R(t)  = exp[ -Σ (t/ηᵢ)^βᵢ ]
H(t)  = Σ (t/ηᵢ)^βᵢ                      (cumulative hazard)
f(t)  = h(t)·R(t)
```

Three modes, each a two-parameter Weibull:

| Mode | Shape | Physical meaning |
|------|-------|------------------|
| Infant mortality | β < 1 (default 0.5) | Manufacturing defects, assembly errors, weak parts |
| Random | β = 1 (fixed) | Externally induced, age-independent failures |
| Wear-out | β > 1 (default 3.0) | Fatigue, erosion, spalling, seal degradation |

Constraining the random mode to β = 1 exactly is deliberate: it makes that
component an exponential with a constant rate, which is what the textbook curve
means, and it removes a free parameter that would otherwise let two modes trade
off against each other without changing the picture.

Each mode gets an enable toggle. Switching modes off is how the tool earns its
keep: turning off infant mortality and wear-out leaves the flat line that the
exponential assumption implies, and the contrast with all three on is the whole
lesson.

## Derived quantities

These are the outputs that turn the picture into a decision, and they are what
separates this from a diagram:

- **Burn-in end**: the age at which infant-mortality hazard drops below the
  random hazard. Screening past this point stops paying.
- **Wear-out onset**: the age at which wear-out hazard rises above the random
  hazard. Preventive replacement starts paying here.
- **Useful-life window**: the span between the two, plus the hazard's minimum and
  the age at which it occurs. Report when the window is empty, which happens
  when wear-out overtakes before infant mortality has settled.
- **Mode share at a chosen age**: what fraction of the hazard each mode
  contributes, as a stacked area or a small breakdown table. Answers "what is
  actually killing my units right now".
- **Reliability and B10 for the combined model**, plus the same for each mode
  alone, so the user can see which mode dominates the number they care about.
- **Optimal preventive replacement age** (stretch): minimise cost rate
  `(c_p·R(T) + c_f·(1-R(T))) / ∫₀ᵀ R(t)dt` given a planned-to-failure cost ratio.
  Only meaningful with a rising hazard, so gate it on wear-out being enabled.

## Visualizations

1. **Hazard rate vs age**, the bathtub itself. Stacked components in light
   colours under the total in a heavy line, so the three regions are visible as
   contributions rather than asserted by shaded background boxes. Markers at the
   burn-in end and wear-out onset. Log-x optional, since real bathtubs span
   decades of time.
2. **Reliability vs age** for the combined model, with each mode alone shown
   faintly.
3. **Failure density** `f(t)`, which is what a histogram of field failures would
   look like and is often more intuitive than hazard for non-specialists.

Reuse the hazard-plot unit autoscaling written for the MTBF Calculator: raw
hazards land around 1e-5/hour and read as a flat line at zero unless rescaled to
failures per million hours.

## Inputs

Progressive simplicity: land on a sensible three-mode curve with no interaction
required. Sliders paired with number boxes, since this tool is about sweeping
parameters rather than entering measurements.

- Infant mortality: enable, β (0.1 to 1.0), η
- Random: enable, MTBF for that mode (more familiar than η, and identical for β=1)
- Wear-out: enable, β (1.0 to 10), η
- Evaluation age for the mode-share breakdown
- Time axis maximum, plus a log-scale toggle
- Preset scenarios: consumer electronics, rolling-element bearing, well-screened
  aerospace part, cheap component with no burn-in. Presets do the teaching that
  documentation cannot.

## Implementation

- `pycalcs/reliability.py` gains `bathtub_hazard_model()`, sitting alongside
  `analyze_reliability()` (component MTBFs to system reliability) and
  `estimate_mtbf()` (data to MTBF). Same docstring contract: `---Parameters---`,
  `---Returns---`, `---LaTeX---`, `---References---`.
- Crossover ages solved by bisection on `h_infant(t) - h_random(t)` and
  `h_wearout(t) - h_random(t)`; both differences are monotone in the region of
  interest, so bisection is safe. Return `None` when a mode is disabled or the
  crossing does not exist rather than clamping to an endpoint.
- Hazard minimum by golden-section search on the total hazard.
- No new dependencies. `math` covers it.
- Tool at `tools/bathtub-curve/`, standard template, settings panel, dark mode,
  the `input-unit` suffix pattern from the MTBF Calculator.
- Cross-link both ways with the MTBF Calculator and the System Reliability
  Calculator.

## Tests

- Single enabled mode reproduces the plain Weibull hazard and reliability.
- Hazards add and reliabilities multiply: `R_total = ∏ Rᵢ` at sampled ages.
- β = 1 alone gives a constant hazard equal to 1/MTBF.
- Crossover ages satisfy `h_infant = h_random` and `h_wearout = h_random` to
  tolerance; `None` when the mode is off.
- Hazard minimum lies between the two crossovers when all three are on.
- Empty-window case: wear-out η pulled below the burn-in end reports no useful
  life rather than a negative span.
- Mode shares at any age sum to 1.
- Monotone reliability, `R(0) = 1`, `R(∞) → 0`.

## Educational content

The background tab carries the argument the picture cannot:

- Why one Weibull cannot bathtub, and why that means the curve is always a
  superposition rather than a distribution.
- That the bathtub describes a **population of parts with several failure
  mechanisms**, and that real field data often shows only one region because
  burn-in removed the left wall and the observation window ended before the right
  one.
- The honest caveat: studies of fielded electronics and of commercial aircraft
  components (the Nowlan and Heap work behind reliability-centred maintenance)
  found that only a minority of items show a pronounced wear-out region at all.
  Scheduled overhaul justified by an assumed right wall can make things worse by
  reintroducing infant mortality at every rebuild. This is the most useful thing
  the tool can teach and most treatments omit it.
- How burn-in trades yield for delivered reliability, and why it stops paying at
  the first crossover.

## References

- O'Connor, P.D.T. and Kleyner, A. Practical Reliability Engineering, 5th ed.
- Ebeling, C.E. An Introduction to Reliability and Maintainability Engineering.
- Abernethy, R.B. The New Weibull Handbook, 5th ed. (competing risks, mode mixing)
- Nowlan, F.S. and Heap, H.F. Reliability-Centered Maintenance, 1978 (the six
  failure patterns, and how rarely the classic bathtub is one of them)
- Klutke, Kiessler and Wortman, "A critical look at the bathtub curve",
  IEEE Transactions on Reliability, 2003

## Open questions

1. Should the random mode be enterable as a FIT rate as well as an MTBF?
   Electronics people live in FIT and would look for it.
2. Is the preventive-replacement optimiser in scope for v1, or does it deserve
   its own tool? It needs a cost ratio, which is a different kind of input from
   everything else here.
3. Worth offering a fourth arbitrary mode for users modelling two distinct
   wear-out mechanisms, or does that dilute the teaching?
4. Should presets be data-derived from published sources, or clearly labelled as
   illustrative shapes? The former is more defensible and much more work.
