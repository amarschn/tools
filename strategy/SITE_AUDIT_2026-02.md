# Site Audit - February 2026

Full codebase review of transparent.tools covering bugs, consistency, SEO, and strategic opportunities.

---

## Critical / Blocking

### 1. `pressure_vessels.py` Syntax Error (Blocks All Tests)

**File:** `pycalcs/pressure_vessels.py:223`
**Introduced:** Commit `2491c06`

Uses a backslash inside an f-string expression, which is illegal in Python <3.12:

```python
f"{thickness_equation} = "  # thickness_equation contains LaTeX backslashes
```

This prevents `pycalcs/__init__.py` from importing, which cascades into **18 of 20 test files failing to collect**. The entire test suite is broken.

**Fix:** Move the backslash-containing variable outside the f-string using string concatenation.

---

## High Priority

### 2. Sitemap is Stale

Four tools added to `catalog.json` but never added to `sitemap.xml`:
- `fatigue-life-estimator`
- `motor-thermal`
- `pressure-vessel`
- `resonator-ringdown`

Conversely, `ashby-chart` is in the sitemap and the filesystem but **missing from `catalog.json`**, so it's invisible on the landing page.

### 3. `og-image.png` Does Not Exist

`index.html` references `https://transparent.tools/og-image.png` in Open Graph and Twitter Card meta tags. The file does not exist in the repo. Every social media share shows a broken preview image.

### 4. Duplicate Local Python Files

Four tools have standalone `.py` files that duplicate what should live in `pycalcs`:

| Tool | Local file | Should use |
|------|-----------|------------|
| `simple_thermal/` | `thermal_calc.py` | `pycalcs.heat_transfer` |
| `wire-sizing/` | `wire_calc.py` | `pycalcs.wire_sizing` |
| `torque-transfer/` | `interference_calc.py` | `pycalcs` (new or existing) |
| `edge_tone/` | `whistle_acoustics.py` | `pycalcs.acoustics` / `pycalcs.resonators` |

These are a maintenance risk: bug fixes to pycalcs won't propagate, and they can't be tested with the centralized test suite.

### 5. No CI/CD Pipeline

No GitHub Actions workflows, no pre-commit hooks. Nothing catches syntax errors before they ship. A single `pytest --co` step on push would prevent the entire class of problem in item 1.

---

## Medium Priority

### 6. Missing READMEs (5 tools)

- `audio-synthesizer`
- `random-generator`
- `rlc-circuit-analyzer`
- `torque-transfer`
- `wire-sizing`

### 7. Low Human-Verified Coverage

Only 6 of 44 tools carry the `human-verified` tag. Safety-adjacent tools should be prioritized:
- `fatigue-life-estimator`
- `pressure-vessel`
- `vibration-isolation-designer`
- `snap-fit-cantilever`
- `motor-thermal`

---

## Strategic / Outside-the-Box Ideas

### A. Structured Data for SEO (JSON-LD)

The tools are a perfect fit for Google's `SoftwareApplication` or `WebApplication` structured data. Adding JSON-LD to each tool page could produce rich search results (star ratings, "Free" pricing badge, category labels). Low effort, high visibility.

### B. Shareable Result URLs

Encode input parameters into URL query strings so users can share a specific calculation:

```
transparent.tools/tools/beam-bending/?load=500&length=2&support=simply-supported
```

One of the most requested features on engineering calculator sites. Creates inbound links organically.

### C. "Compare" Mode (Side-by-Side Parameter Sets)

Let users run the same tool with two parameter sets side by side. Engineers often want to compare Option A vs Option B (two bolt sizes, two isolation mounts, two battery chemistries). A generic two-column diff view on top of the existing architecture would be distinctive.

### D. Offline / PWA Support

Everything already runs client-side. Adding a service worker and manifest would make the site installable as a desktop/mobile app. Engineers on factory floors or in the field often have spotty connectivity. Plays directly to the "runs entirely in your browser" promise.

### E. "Show Your Work" Export

The progressive disclosure architecture already generates substituted equations. Package that into a one-click PDF or printable view:
- Tool name and version
- All inputs with labels and units
- Equations with values substituted
- All outputs
- Timestamp

Engineers need to attach calculation backup to design review reports. This is a genuine workflow gap that most free calculators don't address. (Already on the TODO.md roadmap as "Export Functionality.")

---

## Suggested Priority Order

1. Fix syntax error in `pressure_vessels.py` (5 min)
2. Create `og-image.png` (cosmetic but affects every social share)
3. Update `sitemap.xml` and `catalog.json` to match
4. Set up basic GitHub Actions CI (`pytest --co` + `pytest`)
5. Implement shareable result URLs (highest user-value-per-effort feature)
6. Migrate duplicate local `.py` files into `pycalcs`
7. Add missing READMEs
8. Human-verify safety-adjacent tools
