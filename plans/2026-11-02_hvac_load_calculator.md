# HVAC Load and Heat Pump Sizing Calculator

Date: 2026-11-02
Status: Built on `task/hvac-load-calculator`

## Goal

Answer "what size AC or heat pump do I need?" better than LoadCalc (free, whole
house only) and Cool Calc ($45 per project to see results), with no account, room
loads, and every number traceable. Target search intent: Manual J, heat pump sizing,
BTU calculator.

## Decisions

- **No ACCA or ASHRAE data tables copied as a product.** Design weather is computed
  from public NOAA ISD-Lite hourly data (`scripts/build_hvac_climate.py`).
- **Cooling is a solved 24-hour design day**, not a table: clear-sky solar, exact
  periodic conduction through wall layers, attic heat balance, and a two-node room
  that finds the capacity for a 3 °F swing, the ASHRAE RHB control assumption.
- **Heating is ASHRAE's UA·dT.** Air leakage is Chapter 17 Equations 8 to 14. Duct
  factors interpolate Chapter 17 Table 6 and adjust for temperature, term by term.
  An earlier direct energy balance overshot Table 6 by 40% or more, so it was dropped.
- **One calibration.** Thermal mass was set once, so the Atlanta room load matches
  ASHRAE. Sacramento is an independent check and was never used for tuning.
- **Equipment upper limits are advisory.** ACCA confirms the 90% lower limit and
  limits by compressor type. Exact upper values only appear in secondary sources.
- **The tool never claims Manual J compliance.** The page says it is not ACCA-approved.

## Honest gaps

- Not ACCA-approved, so it cannot serve where a permit requires approved software.
- No satellite, floor plan, or LiDAR geometry entry, and no duct design yet.
- Two benchmark houses are not field validation.
- No keyword volume data was available when choosing this tool. Check Keyword
  Planner and Search Console after launch.

See `tools/hvac-load-calculator/ROADMAP.md` for next steps.
