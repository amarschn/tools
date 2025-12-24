# UI Design Guidance

This document captures the preferred UI direction for Engineering Tools calculators. The current
target is a Polestar-inspired minimal UI: clean geometry, restrained color, and high legibility.

## Visual Language

- Prioritize clean, monochrome surfaces with a single dark accent for CTAs.
- Keep backgrounds solid (no gradients) and use whitespace for separation.
- Reserve semantic colors for status indicators only (success/warning/danger).
- Use hairline borders and subtle shadows; avoid heavy depth effects.

Suggested CSS variables (tool-local):

```
--primary-color: #0b0d12;
--primary-light: #f4f5f7;
--secondary-color: #4b5563;
--accent-color: #111827;
--success-color: #0f766e;
--warning-color: #b45309;
--danger-color: #b91c1c;
--text-color: #111827;
--text-light: #6b7280;
--border-color: #e5e7eb;
--bg-color: #f8f9fb;
--bg-card: #ffffff;
--shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
--shadow-lg: 0 6px 18px rgba(15, 23, 42, 0.08);
--border-radius: 8px;
--font-sans: 'Helvetica Neue', 'Avenir Next', 'Univers', 'Helvetica', sans-serif;
--font-mono: 'SF Mono', 'Menlo', 'Monaco', monospace;
```

## Typography

- Use a Swiss-style sans serif for body and headings (Helvetica Neue / Avenir Next / Univers).
- Use a clean monospace for numeric readouts (SF Mono / Menlo / Monaco).
- Keep headings crisp with moderate weight and minimal letter spacing.

## Layout & Structure

- Add a centered hero header (`.tool-header`) with the tool name and a concise subtitle.
- Widen the canvas: ~92% width with a 1400px max.
- Use a two-column layout where outputs have slightly more width than inputs.
- Keep card padding generous (24-28px) to reduce visual density.

## Inputs

- Organize large input sets into tabbed sections (Fastener / Joint / Loading style).
- Pair related inputs in a two-column row (`.input-row`) when it reduces scan time.
- Use 1px input borders with a subtle focus ring to keep the UI clean.
- Remove native select arrows/number spinners if they collide with tooltip icons; pad inputs accordingly.
- Tooltips should be larger, wrapped, and shadowed for readability.

## Outputs

- Present key results as a grid of cards with large numeric values.
- Highlight the most important values with a subtle background and accent border.
- Include a second grid for secondary metrics and a pack/system summary grid if needed.
- Add \"indicator\" gauges for safety, capacity, or severity metrics with clear thresholds.
- Use a status banner to summarize acceptability and show recommended adjustments.

## Charts & Background

- Use carded chart containers with titles and consistent spacing.
- When plotting, include legends, axis labels, and clear marker annotations.
- Use equation cards with titles, a single equation, and a concise variable legend list.

## Motion & Feedback

- Apply light fade transitions on tab content; keep hover effects restrained.
- Show a full-screen loading overlay while Pyodide initializes to avoid blank states.

## Implementation Notes

- Maintain tool-local CSS blocks for now; avoid inline styles unless absolutely necessary.
- Keep all UI enhancements within the existing HTML template structure for consistency.
- When adopting these patterns, preserve tool logic and docstring-driven tooltips.
