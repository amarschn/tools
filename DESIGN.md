# UI Design Guidance

This document captures the preferred UI direction for Engineering Tools calculators. It codifies the
visual language established by the Claude-based fastener torque calculator so new tools share the same
polished, information-dense feel.

## Visual Language

- Use a deep primary hue with a saturated accent for call-to-action emphasis.
- Apply a subtle background gradient to the page; keep cards on clean white surfaces.
- Reserve semantic colors for status (success/warning/danger) and use them consistently across badges,
  gauges, and banners.
- Favor soft drop shadows and a slightly larger corner radius (8-10px) for a modern, confident look.

Suggested CSS variables (tool-local):

```
--primary-color: #1e3a5f;
--primary-light: #f0f4f8;
--secondary-color: #495057;
--accent-color: #2563eb;
--success-color: #059669;
--warning-color: #d97706;
--danger-color: #dc2626;
--text-color: #1f2937;
--text-light: #6b7280;
--border-color: #e5e7eb;
--bg-color: #f8fafc;
--bg-card: #ffffff;
--shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
--shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.1);
--border-radius: 10px;
```

## Typography

- Use a modern sans serif (Inter preferred) for body and headings.
- Use a monospace font (JetBrains Mono preferred) for numeric readouts.
- Increase heading weight (600-700) and tighten letter spacing slightly for h1.

## Layout & Structure

- Add a centered hero header (`.tool-header`) with the tool name and a concise subtitle.
- Widen the canvas: ~92% width with a 1400px max.
- Use a two-column layout where outputs have slightly more width than inputs.
- Keep card padding generous (24-28px) to reduce visual density.

## Inputs

- Organize large input sets into tabbed sections (Fastener / Joint / Loading style).
- Pair related inputs in a two-column row (`.input-row`) when it reduces scan time.
- Use 2px input borders with a soft focus ring (4px glow) to signal interactivity.
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

- Apply light fade/slide transitions on tab content and hover lift on primary buttons.
- Show a full-screen loading overlay while Pyodide initializes to avoid blank states.

## Implementation Notes

- Maintain tool-local CSS blocks for now; avoid inline styles unless absolutely necessary.
- Keep all UI enhancements within the existing HTML template structure for consistency.
- When adopting these patterns, preserve tool logic and docstring-driven tooltips.
