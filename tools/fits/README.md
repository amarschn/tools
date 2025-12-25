# Engineering Fits Assistant

## Purpose
Provide ISO 286 hole-basis fit calculations with clear tolerance zones, clearance/interference ranges, and fit guidance for common engineering assemblies. ANSI/ASME B4.1 classes are included and mapped to ISO equivalents for sizing guidance.

## Requirements
- Users enter a nominal diameter (mm) and select an ISO fit designation (H/...).
- Output includes hole and shaft deviation limits, actual size limits, and minimum/maximum clearance.
- Visualization shows both tolerance zones against the same deviation axis with legend and units.
- The fit library and descriptions live in `fit_library.json` (single source of truth for fit metadata).
- Uses ISO 286-1 and ISO 286-2 formulas for IT grades and shaft fundamental deviations.
- Surface finish guidance and fit examples are included per fit class.
- Fit system dropdown includes ISO 286 hole-basis and ANSI/ASME B4.1 classes (mapped to ISO equivalents).

## Scope and Assumptions
- Supported diameter range: 1 to 500 mm (ISO diameter steps).
- Supported IT grades: 5 through 16.
- Supported hole letters: H, JS.
- Supported shaft letters: a-h, j/js, k, m, n, p, r, s, t.
- J fits are approximated as centered (js) zones in this implementation.
- ANSI/ASME fits are calculated using the closest ISO equivalent; confirm final limits against B4.1 tables.

## References
- ISO 286-1:2010, Geometrical product specifications (GPS) - ISO code system for tolerances.
- ISO 286-2:2010, Tables of standard tolerance grades and limit deviations.
