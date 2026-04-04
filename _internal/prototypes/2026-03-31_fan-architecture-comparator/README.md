# Fan Architecture Comparator Prototype

Date: 2026-03-31
Status: Internal R&D prototype

This prototype explores the right interaction model for comparing axial, mixed-flow, and radial fan families before real vendor curves are loaded.

## Core thesis

- Compare architectures as duty envelopes, not as single-point numbers.
- Keep one explicit flow and static-pressure requirement visible at all times.
- Force the non-curve tradeoffs into the same workspace: packaging, contamination, acoustics, and efficiency priority.
- Rank the three families side by side, but keep the logic transparent enough that the user can disagree with it intelligently.
- Treat radial / centrifugal as a family at this stage only. If it wins, the next product state should branch into backward-curved vs forward-curved instead of pretending "centrifugal" is one thing.

## What is in the prototype

- Preset use cases to make the comparison logic legible quickly.
- A flow-pressure envelope chart with a visible duty marker.
- A duty-side physics anchor using specific speed `N_s`, Cordier specific diameter `D_s`, and a predicted wheel diameter at the entered RPM.
- An optional passage-velocity / known-area constraint that derives area, equivalent diameter, and adds packaging / acoustics realism without pretending velocity is an independent duty variable.
- Ranked architecture cards with strengths, cautions, and next-step guidance.
- A radial split panel that branches immediately into forward-curved vs backward-curved logic when the centrifugal family wins.
- A direct handoff button into `tools/fan-curve-explorer/` carrying the duty point and suggested family via query parameters.
- A comparison matrix that exposes what the scoring is really looking at.

## What is intentionally missing

- No vendor curve import.
- No AMCA-certified data.
- No acoustic prediction.
- No motor or FEI optimization.
- No detailed subtype selection inside the radial family.

## If this direction is right

The production tool should probably become a front-end stage ahead of the existing fan curve explorer:

1. Use this architecture triage view to narrow the family.
2. Carry the winning family into the curve-based selector with preloaded education copy, duty-point defaults, and radial subtype hints.
3. Reuse the language already in `pycalcs/fan_curves.py` so the prototype and the shipped tool do not drift apart.
