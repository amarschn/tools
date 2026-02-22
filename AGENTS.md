# Project Agents: Engineering Tools

This document outlines the vision, architecture, and contribution guidelines for the Engineering Tools project. Our goal is to create a suite of high-quality, educational, and easy-to-use engineering calculators and tools.

## Table of Contents

1. [Project Vision & Philosophy](#project-vision--philosophy)
2. [The Two Core Principles](#the-two-core-principles)
3. [Core Principles](#core-principles)
4. [Architecture Overview](#architecture-overview)
5. [Contribution Guidelines](#contribution-guidelines)
6. [Git Workflow](#git-workflow)
7. [Coding Practices and Standards](#coding-practices-and-standards)
8. [Python Module Patterns](#python-module-patterns)
9. [Advanced Tool UI Patterns](#advanced-tool-ui-patterns)
   - [Settings Panel (Theme, Density, Precision)](#settings-panel-theme-density-precision)
   - [Dark Mode CSS Variables (CRITICAL)](#dark-mode-css-variables-critical)
10. [Visualization Standards](#visualization-standards)
11. [Testing & Verification](#testing--verification)
12. [Deployment & Hosting](#deployment--hosting)
13. [Tool Roadmaps](#tool-roadmaps)
14. [Roadmap](#roadmap)

## Project Vision & Philosophy

The primary goal of this project is to create a GitHub Pages-hosted web application that provides a collection of powerful and intuitive engineering tools. These tools should serve a dual purpose:

1.  **Calculation and Verification:** Provide quick and accurate calculations for a wide range of engineering problems across various disciplines.
2.  **Education:** Allow users to explore the underlying principles and equations behind the calculations, fostering a deeper understanding of the subject matter.

We aim for a user experience where the initial tool is simple and straightforward, but curiosity is rewarded with detailed, step-by-step explanations available on demand.

Design philosophy and UI direction live in `DESIGN.md` and should be treated as required context for any new tool or visual refresh.

---

## The Two Core Principles

Every tool in this repository **must** embody these two foundational principles. They are not optional features—they define what makes this project unique.

### Progressive Simplicity

> **A tool should be immediately usable with zero learning curve.**

The default state of every tool must be:
- **Minimal inputs visible:** Show only the essential parameters needed for a basic calculation
- **Sensible defaults:** Pre-populate fields with reasonable values so users can click "Calculate" immediately
- **Clear primary output:** The most important result should be visually prominent and instantly understandable
- **Fast time-to-value:** A user should get their first useful result within 10 seconds of loading the tool

**What this means in practice:**
- Hide advanced options behind a toggle (e.g., "Show advanced options")
- Use dropdown selections for common cases instead of requiring users to input raw values
- Group related inputs logically, with the most common at the top
- Provide a loading overlay during initialization—never show a broken or half-loaded UI

### Progressive Disclosure

> **Complexity is available on demand, never forced.**

Every layer of the tool should offer a path to deeper understanding:

| Layer | What the user sees | How to reveal more |
|-------|-------------------|-------------------|
| **L0: Result** | "Torque: 50 N·m" | Click the result card |
| **L1: Equation** | `T = K × d × F` | Expand "Show derivation" |
| **L2: Substituted** | `T = 0.15 × 10mm × 33.4kN = 50.1 N·m` | Visible in derivation panel |
| **L3: Intermediate steps** | K-factor lookup, stress area calculation, etc. | Nested expandable sections |
| **L4: Theory** | Full explanation of torque-tension relationships | "Background" tab |
| **L5: References** | VDI 2230:2015, Shigley's MED Chapter 8 | Links in Background tab |

**What this means in practice:**
- Results are clickable—clicking opens a derivation panel
- Derivation panels show: equation → substituted values → intermediate calculations → final result
- Every calculation can be traced back to its source equation
- Background tabs provide comprehensive educational content with table of contents
- Worked examples help users verify their understanding

### The User Personas

Design every tool for these three users simultaneously:

1. **The Hurried Engineer:** "I just need the number." → Primary result visible immediately, copy-paste ready
2. **The Curious Student:** "How did you get that?" → Click to expand derivation, see substituted equations
3. **The Verifying Expert:** "I need to check your methodology." → Full equations, references, export to verify independently

---

## Core Principles

All tools (our "agents") in this repository should adhere to the following principles:

* **Usability First:** The primary function of each tool should be immediately obvious and easy to use. The user should be able to get a useful result with minimal friction.
* **Progressive Disclosure:** Complexity should be hidden by default. Users who want to understand the "nitty-gritty" can use tooltips and expandable dropdowns to reveal detailed explanations, intermediate steps, and the specific equations used. When equations are rendered, list them sequentially with clear numbering (e.g., "Equation (3)"), and include a short variable legend beneath each in the format `symbol: explanation` so readers can immediately interpret every term.
* **Transparency:** Every calculation should be traceable. The exact equations, including references where applicable, must be accessible to the user. This builds trust and enhances the educational value.
* **Modularity and Reusability:** Each tool is a standalone web page. However, the core calculation logic should be written as generic, well-documented Python functions in a shared library - `/pycalcs`. This promotes code reuse and simplifies maintenance. There should be multiple python files within `/pycalcs`, each containing relevant code for a given field or discipline.
* **Single Source of Truth:** This is related to modularity and reusability, but bears explicit explanation - there should be no duplication of equations or explanations, this will result in errors. For any given variable, equation, or explanation for a phenomena, there should be only ONE place where that is documented.
* **Tool-Local References by Default:** Reference data (datasheets, curves, images, PDFs) should live with the tool that uses them unless multiple tools depend on the same asset. This keeps context tight while still allowing shared promotion when reuse is real.
* **Consistency:** All tools should share a similar, clean, and simple user interface. This creates a cohesive experience as users navigate between different calculators.
* **Design Alignment:** Follow the system-wide visual language and layout guidance in `DESIGN.md` for typography, spacing, and interaction patterns.
* **Dependency-Free Core:** The core Python library functions should have minimal to no external dependencies to ensure they run smoothly with Pyodide and to avoid versioning conflicts.
* **Visualizations:** Where appropriate, tools should include visualizations (plots, diagrams, etc.) to help users better understand the results and the underlying concepts.
* **Exporting:** Engineering work is still done in Excel and other tools, and that is unlikely to change. Many of the tools in this repo will need some form of export function that can output an Excel document or similar with all calculations in that document to be used locally by a user for verification, modification, and private use.

## Architecture Overview

The project is a static web app hosted on GitHub Pages, with calculations performed client-side using Pyodide.

* **Frontend:** Each tool is a self-contained HTML file. We use a consistent CSS stylesheet for a uniform look and feel. JavaScript is used to handle user input, interact with the Pyodide environment, and update the UI. There should be a relatively straightforward navigation between different tools and within the base `tools` home page.
* **Backend (Client-Side):** We use [Pyodide](https://pyodide.org/) to run Python code directly in the browser. This allows us to write complex calculation logic in Python without needing a server.
* **Core Library (`/pycalcs/`):** This package is the heart of our project. It contains the reusable Python functions that power every tool, split into discipline-focused modules (e.g., `structures.py`, `fluids.py`). Shared helpers live in `utils.py`. Keep the package import-safe so that running `from pycalcs import structures` (or similar) inside Pyodide loads the right module without side-effects.
    * **Docstrings are CRITICAL:** Every function in this library *must* have a detailed docstring that includes:
        * A clear description of what the function does.
        * A list of parameters with their types and descriptions.
        * What the function returns.
        * The mathematical equations used, written in LaTeX format.
        * Any references to textbooks, papers, or standards.
* **Tools (`/tools/`):** Each tool lives in its own directory (e.g., `/tools/beam_deflection/`) and consists of at least an `index.html` file. Many of these tools directories will have their own `AGENTS.md` file that further refines what is needed for that tool.
* **Reference Assets:** Default to tool-local storage under `/tools/<tool>/references/` (or within the tool README). If a tool-local reference becomes useful to more than one tool, promote it to a shared root folder such as `/references/<domain>/`, update all tools to link to the shared asset, and delete the duplicated copies. Document the promotion (why it is shared and which tools depend on it) in each tool README to keep the single source of truth clear.

### Reference Promotion Checklist

Use this when a tool-local reference becomes relevant to multiple tools:

1. Move the reference into `/references/<domain>/` with clear naming and minimal duplication.
2. Update every tool that used the local copy to point to the shared asset.
3. Remove the old tool-local copies to keep a single source of truth.
4. Add a short note in each affected tool README stating the shared reference location and dependent tools.
5. Verify links/load paths still work in the browser (relative paths, fetch, etc.).

## Contribution Guidelines

We welcome contributions! To ensure a smooth process, please follow these guidelines.
For the day-to-day workflow and release process, see `CONTRIBUTING.md` and `docs/RELEASE.md`.

### Branching Strategy

* The `main` branch is for the live, deployed version of the tools.
* All new development, whether it's a new tool or a major change to an existing one, should be done in a separate feature branch.
* Create a branch with a descriptive name (e.g., `feature/add-stress-calculator`).
* Once the feature is complete and tested, submit a pull request to merge it into the `main` branch.

### Creating a New Tool

1.  **Create a New Directory:** Add a new directory for your tool under `/tools/`. For example, `/tools/my-new-tool/`.
2.  **Define Requirements in a README.md file:** There must be a README.md file in each tool subdirectory in `/tools/` that contains:
    * The purpose of the tool.
    * The requirements of the tool.
    * If a tool-local `ROADMAP.md` exists, review it before starting work and keep it updated as tasks are completed.
3.  **Add Python Logic:**
    * Identify the core calculations for your tool.
    * Write one or more Python functions to perform these calculations.
    * Add these functions to the appropriate module under `/pycalcs/` (create a new file if the discipline is not represented yet) and expose them via a clear, importable function.
    * **Crucially, write excellent docstrings for your new functions.**
4.  **Create the HTML (`index.html`):**
    * **Choose the right template:**
      - `tools/example_tool/` — Basic tools with few inputs
      - `tools/example_tool_advanced/` — Complex tools with many inputs, safety factors, visualizations
    * This template is mandatory for all contributors, including AI agents, to ensure consistency and adherence to project principles.
    * **Include Google Analytics:** Add the GA4 snippet in the `<head>` after the viewport meta tag. See [Analytics](#analytics) for the required code.
    * Modify the template's placeholder content (inputs, outputs, README section) to fit your specific tool.
    * Update the script constants so the frontend loads the correct Python: set `TOOL_MODULE_NAME` to your `pycalcs/<module>.py` filename (without the `.py`) and `TOOL_FUNCTION_NAME` to the callable you expose. Every form control `id` the template references (`#param1`, `#param2`, etc.) must match the parameter names defined in the docstring so tooltips populate automatically.
    * You will also need to create/update the `README.md` in your tool's folder. The template has a section to display this.
5.  **Add JavaScript:**
    * Write the JavaScript code to:
        * Initialize Pyodide.
        * Load the Python functions from our library.
        * Get user input from the HTML form.
        * Call the relevant Python function with the user's input.
        * Display the results in the designated HTML elements.
    * Implement tooltips and dropdowns to show the equations and step-by-step explanations.
6.  **Testing:**
    * Test your tool with a variety of inputs, including edge cases.
    * Verify that the results are correct.
    * Ensure the UI is responsive and easy to use.
7.  **Add the tool to the catalog**
    * To make your new tool discoverable, you **must** register it in the `catalog.json` file located in the project's root directory. This file is the central manifest that dynamically powers the main landing page, enabling all filtering, searching, and categorization.
    * Add a new JSON object to the array for your tool. Please ensure your entry follows this exact structure:

        ```json
        {
          "title": "Your New Tool's Name",
          "path": "./tools/your-new-tool-folder/",
          "description": "A concise, one-sentence description of what your tool does and why it's useful.",
          "category": ["Primary Discipline", "Secondary Discipline (Optional)"],
          "tags": ["keyword1", "keyword2", "concept3", "visualization"]
        }
        ```

    * **`title`**: The official name of the tool.
    * **`path`**: The relative path to your tool's `index.html` file from the root.
    * **`description`**: A brief summary that will appear on the tool card.
    * **`category`**: The primary engineering discipline(s). Try to use existing categories if they fit.
    * **`tags`**: A list of relevant, lowercase keywords that users might search for.
    * Add the reserved tag `"human-verified"` once a maintainer has personally tested the tool end-to-end; the catalog will surface it with a dedicated badge so users can identify human-reviewed calculators.

    ***This step is critical.*** Without it, your tool will exist in the repository but will not appear on the main tools hub.

8.  **Submit a Pull Request:** Once your tool is ready, submit a pull request to the `main` branch.

## Git Workflow

Here is a simple, step-by-step guide for contributing code using Git. These commands are suitable for both human and AI developers.

1.  **Clone the Repository:**
    If you haven't already, get a copy of the project on your local machine.
    ```bash
    git clone [https://github.com/amarschn/tools.git](https://github.com/amarschn/tools.git)
    cd tools
    ```

2.  **Create a New Branch:**
    Always work on a new branch for your feature or bug fix. Name it descriptively.
    ```bash
    git checkout -b feature/your-feature-name
    ```

3.  **Make Your Changes:**
    Add or edit the files for your new tool or feature.

4.  **Stage and Commit Your Changes:**
    Add your changes to the staging area and commit them with a clear message.
    ```bash
    git add .
    git commit -m "feat: Add new stress calculator tool"
    ```
    *(We recommend following the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.)*

5.  **Push Your Branch:**
    Push your new branch to the remote repository on GitHub.
    ```bash
    git push -u origin feature/your-feature-name
    ```

6.  **Open a Pull Request:**
    Go to the repository on GitHub. You will see a prompt to create a pull request from your newly pushed branch. Click it, fill out the details explaining your changes, and submit it for review.

## Coding Practices and Standards

To maintain a high level of quality and consistency across the project, all contributions should adhere to the following standards.

### Mandatory UI Template (For AI and Human Contributors)

All new tools **must** be built using one of the example tools templates unless explicitly instructed not to.

* **For AI Agents (Codex, etc.):** When asked to create a new tool, you must first retrieve the contents of `/tools/example_tool/index.html` (or `/tools/example_tool_advanced/index.html` for complex tools) and use it as the foundational code. All modifications must be made *to this template*.
* **For Human Developers:** Do not copy an existing tool. Start from a template to ensure you have the latest UI structure, styles, and accessibility features.
* **Layout Variants:** Example implementations of compact, stacked, and tabbed input layouts live in `tools/example_tool_compact`, `tools/example_tool_stacked`, and `tools/example_tool_tabbed`. Use them as references for alternate form factors while still basing new tools on the core template.

This mandate enforces our core principles of consistency, usability, and progressive disclosure.

### AI Tool Creation Checklist

When creating a new tool, generate these files:

1. **`/pycalcs/<module>.py`** - Calculation function with docstring containing `---Parameters---`, `---Returns---`, and `---LaTeX---` sections. Return a dict with results plus `subst_<key>` strings for showing substituted equations.

2. **`/tools/<tool-slug>/index.html`** - Copy from `/tools/example_tool/index.html` or `/tools/example_tool_advanced/index.html`. Update `TOOL_MODULE_NAME`, `TOOL_FUNCTION_NAME`, and `PARAM_ORDER` in the script config. Match input field IDs to parameter names.

3. **`/tests/test_<module>.py`** - At least one nominal test and one with a known/textbook value.

**Reference examples:**
- Simple tool: `/pycalcs/snapfits.py` and `/tools/snap-fit-cantilever/`
- Complex tool: `/pycalcs/fasteners.py` and `/tools/bolt-torque/`

### Python

* **Style:** All Python code must follow the [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/).
* **Type Hinting:** Use type hints for all function signatures (arguments and return values). This improves readability and helps prevent bugs. Example: `def calculate_area(length: float, width: float) -> float:`.
* **Docstrings:** As stated in the architecture overview, detailed docstrings are mandatory for all functions in the core library.
* **Docstring structure:** `pycalcs/utils.py:get_documentation` splits docstrings on `---Parameters---`, `---Returns---`, and `---LaTeX---`, then expects each parameter/return entry to use an unindented `name : type` line followed by indented description lines. The keys you return from the calculation must exactly match the names listed in `---Returns---`. Optional substituted-step strings should be named `subst_<return_key>` so the template can surface them. Start every new tool by copying and adapting the pattern below (from `pycalcs/example.py`):

```python
def calculate_tool(input_a: float, input_b: float) -> dict[str, float]:
    """
    Single-sentence summary of what the function solves.

    Longer context and any assumptions or references go here.

    ---Parameters---
    input_a : float
        One-line purpose, then further detail on units or limits.
    input_b : float
        Repeat the same pattern for each argument.

    ---Returns---
    result_primary : float
        Output meaning and units.
    result_secondary : float
        Clearly state derived values or checks.

    ---LaTeX---
    Equation_1 = \\frac{Input_A}{Input_B}
    Equation_2 = Input_A \\times Input_B
    """
```
* **Error Handling:** Functions should raise specific exceptions for invalid inputs or calculation errors (e.g., `ValueError`, `ZeroDivisionError`). Do not use generic `Exception`. The JavaScript code will be responsible for catching these errors and displaying a user-friendly message.

### JavaScript

* **Style:** Use a consistent code style. We recommend using a tool like [Prettier](https://prettier.io/) to auto-format your code.
* **Modern JavaScript:** Use modern ES6+ features such as `const` and `let` over `var`, arrow functions, and template literals.
* **DOM Interaction:**
    * Use descriptive IDs for elements that will be manipulated by JavaScript.
    * Cache DOM elements in variables if they are accessed multiple times.
    * Handle user input gracefully, providing clear feedback for valid and invalid data.
* **Error Handling:** Use `try...catch` blocks when calling the Pyodide functions to handle any Python exceptions and display appropriate messages to the user.

### HTML/CSS

* **Semantic HTML:** Use semantic HTML5 tags (`<main>`, `<section>`, `<label>`, etc.) to structure your content. This improves accessibility and SEO.
* **Accessibility:** Ensure all tools are accessible. This includes:
    * Using `label` elements for all form inputs.
    * Providing sufficient color contrast.
    * Ensuring all functionality is usable with a keyboard.
* **CSS:** The example template currently ships with an inline `<style>` block; start from it, keep component-specific tweaks inside that block, and only introduce shared rules in the forthcoming global stylesheet (see Roadmap). Use descriptive class names and avoid one-off inline `style=""` attributes so future extraction stays easy.

---

## Python Module Patterns

This section documents proven patterns for structuring `pycalcs` modules, derived from production tools like `fasteners.py`.

### Pattern 1: Database-Driven Calculations

For tools that involve standard components (fasteners, materials, pipe sizes, motor ratings), use lookup dictionaries rather than requiring users to input raw values.

```python
# =============================================================================
# MATERIAL/COMPONENT DATABASES
# =============================================================================

# Example: Bolt grade database with all relevant properties
BOLT_GRADES: Dict[str, Dict[str, float]] = {
    "8.8": {
        "proof_strength": 640e6,      # Pa
        "tensile_strength": 800e6,    # Pa
        "yield_strength": 640e6,      # Pa
        "elastic_modulus": 205e9,     # Pa
        "description": "Medium carbon steel, quenched and tempered",
    },
    "10.9": {
        "proof_strength": 830e6,
        "tensile_strength": 1040e6,
        "yield_strength": 940e6,
        "elastic_modulus": 205e9,
        "description": "Alloy steel, quenched and tempered",
    },
}

# Lookup function with helpful error messages
def get_bolt_properties(grade: str) -> Dict[str, float]:
    """Look up bolt material properties from grade designation."""
    if grade in BOLT_GRADES:
        return BOLT_GRADES[grade]
    else:
        raise ValueError(
            f"Unknown bolt grade '{grade}'. "
            f"Valid grades: {list(BOLT_GRADES.keys())}."
        )
```

**Benefits:**
- Users select from dropdowns instead of typing values
- Reduces input errors
- Embeds engineering knowledge (correct values)
- Single source of truth for material data

**When to use:** Fasteners, materials, pipe schedules, motor frame sizes, standard beam sections, wire gauges, etc.

### Pattern 2: Substituted Equation Strings

Return pre-formatted LaTeX strings showing actual values substituted into equations. This enables the "L2" layer of progressive disclosure.

```python
def analyze_joint(diameter: float, preload: float, k_factor: float) -> Dict:
    # ... calculations ...
    torque = k_factor * diameter * preload

    return {
        # Primary result
        "assembly_torque": torque,

        # Substituted equation for display (note: values formatted for readability)
        "subst_assembly_torque": (
            f"T = K \\times d \\times F_i = "
            f"{k_factor:.3f} \\times {diameter*1000:.1f}\\text{{mm}} "
            f"\\times {preload/1000:.1f}\\text{{kN}} = {torque:.1f}\\text{{N-m}}"
        ),
    }
```

**Naming convention:** `subst_<result_key>` where `<result_key>` matches the output it explains.

### Pattern 3: Visualization Data Generation

For tools with plots, create dedicated functions that return structured data for the frontend to render.

```python
def generate_sensitivity_data(
    nominal_value: float,
    parameter_range: Tuple[float, float],
    n_points: int = 50,
) -> Dict[str, List[float]]:
    """
    Generate data for parameter sensitivity plot.

    Returns dict with arrays ready for Plotly/Chart.js:
    - x_values: Parameter sweep values
    - y_values: Corresponding outputs
    - annotations: Key points to highlight
    """
    x_min, x_max = parameter_range
    x_values = [x_min + i * (x_max - x_min) / (n_points - 1) for i in range(n_points)]
    y_values = [calculate_output(x) for x in x_values]

    return {
        "x_values": x_values,
        "y_values": y_values,
        "nominal_x": nominal_value,
        "nominal_y": calculate_output(nominal_value),
    }
```

**Include in main function return:**
```python
return {
    "primary_result": value,
    # ... other results ...
    "sensitivity_data": generate_sensitivity_data(...),
    "diagram_data": generate_diagram_data(...),
}
```

### Pattern 4: Safety Factors and Status

For engineering analysis tools, return safety factors, utilization percentages, and an overall status assessment.

```python
def analyze_component(...) -> Dict:
    # ... calculations ...

    # Safety factors (dimensionless ratios)
    sf_yield = yield_capacity / max_load
    sf_fatigue = fatigue_limit / alternating_stress

    # Utilization (percentage of capacity used)
    utilization = 100.0 * max_load / yield_capacity

    # Status determination
    min_sf = min(sf_yield, sf_fatigue)
    if min_sf >= 1.5:
        status = "acceptable"
    elif min_sf >= 1.0:
        status = "marginal"
    else:
        status = "unacceptable"

    # Recommendations based on analysis
    recommendations = []
    if sf_yield < 1.5:
        recommendations.append("Consider higher strength material or larger section.")
    if sf_fatigue < 2.0:
        recommendations.append("Review fatigue loading; consider stress relief.")

    return {
        # ... primary results ...
        "safety_factor_yield": sf_yield,
        "safety_factor_fatigue": sf_fatigue,
        "utilization": utilization,
        "status": status,
        "recommendations": recommendations,
    }
```

### Pattern 5: Comprehensive Return Structure

Organize return dictionaries by category for complex tools:

```python
return {
    # === PRIMARY OUTPUTS (what the user asked for) ===
    "assembly_torque": torque,
    "target_preload": preload,

    # === GEOMETRY & MATERIAL (for reference) ===
    "nominal_diameter": d,
    "stress_area": A_s,
    "yield_strength": S_y,

    # === INTERMEDIATE CALCULATIONS (for derivation panels) ===
    "bolt_stiffness": K_b,
    "joint_stiffness": K_j,
    "load_factor": phi,

    # === SAFETY ASSESSMENT ===
    "safety_factor_yield": sf_y,
    "safety_factor_clamp": sf_k,
    "utilization_yield": util_y,
    "status": status,
    "recommendations": recommendations,

    # === VISUALIZATION DATA ===
    "diagram_data": generate_diagram_data(...),
    "sensitivity_data": generate_sensitivity_data(...),

    # === SUBSTITUTED EQUATIONS ===
    "subst_assembly_torque": "T = ...",
    "subst_load_factor": "φ = ...",
}
```

---

## Advanced Tool UI Patterns

This section documents UI patterns for complex tools. See `tools/example_tool_advanced/` for a complete implementation and `tools/bolt-torque/` for a production example.

### Loading Overlay

Always show a loading overlay while Pyodide initializes. Never show a broken or half-loaded UI.

```html
<div class="loading-overlay" id="loading-overlay">
    <div class="spinner"></div>
    <div class="loading-text" id="loading-text">Loading Pyodide...</div>
</div>
```

```javascript
// Update loading text as initialization progresses
loadingText.textContent = 'Loading Pyodide...';
let pyodide = await loadPyodide();

loadingText.textContent = 'Loading Python modules...';
await pyodide.runPythonAsync(`...`);

// Hide when ready
document.getElementById('loading-overlay').classList.add('hidden');
```

### Expert Mode Toggle

Hide infrequently-used parameters behind an expert mode toggle to keep the default view simple.

```html
<!-- Expert Mode Toggle -->
<div class="expert-mode-bar">
    <div>
        <span class="expert-mode-label">Expert Mode</span>
        <span class="expert-mode-hint">Show all parameters</span>
    </div>
    <label class="expert-toggle">
        <input type="checkbox" id="expert-mode-toggle" onchange="toggleExpertMode()">
        <span class="expert-toggle-label" id="expert-mode-status">Off</span>
    </label>
</div>

<!-- Core inputs (always visible) -->
<div class="input-group">
    <label for="main_param">Main Parameter</label>
    <input type="number" id="main_param" value="10">
</div>

<!-- Advanced section (hidden by default, shown when expert mode is on) -->
<div class="advanced-section" id="advanced-inputs">
    <div class="input-group">
        <label for="advanced_param">Advanced Parameter</label>
        <input type="number" id="advanced_param" value="0.5">
    </div>
</div>
```

CSS for expert mode:
```css
.advanced-section { display: none; }
body.expert-mode .advanced-section { display: block; }
```

### Auto-Calculate: When to Use (and When Not To)

Auto-calculate updates results in real-time as inputs change. While convenient for simple tools, it adds complexity and can degrade the user experience for complex calculations.

**Include auto-calculate ONLY when ALL of these are true:**

| Criterion | Threshold |
|-----------|-----------|
| Total inputs | ≤ 5 inputs |
| Calculation time | < 100ms |
| Complexity | No database lookups, iterations, or chart rendering |
| User expectation | Instant feedback expected (e.g., unit converter) |

**Do NOT include auto-calculate when:**

- The tool has safety factor analysis or complex validation
- Calculations take noticeable time (> 200ms)
- Charts need to re-render with each change
- Users need to review inputs before seeing results
- The tool uses the advanced template

**When in doubt, omit auto-calculate.** Users expect a Calculate button. An explicit action also gives users a moment to review their inputs before computation.

The `example_tool` (basic template) includes auto-calculate as an option. The `example_tool_advanced` template does not include it at all—if you're building something complex enough to need the advanced template, you shouldn't have auto-calculate.

### Dynamic Cascading Dropdowns

When selections depend on each other (e.g., fastener standard → size → grade), update options dynamically.

```javascript
const ISO_SIZES = ["M6x1.0", "M8x1.25", "M10x1.5", ...];
const UTS_SIZES = ["1/4-20 UNC", "3/8-16 UNC", ...];

function updateFastenerOptions() {
    const standard = document.getElementById('fastener_standard').value;
    const sizeSelect = document.getElementById('fastener_size');

    sizeSelect.innerHTML = '';
    const sizes = standard === 'ISO' ? ISO_SIZES : UTS_SIZES;

    sizes.forEach(size => {
        const option = document.createElement('option');
        option.value = size;
        option.textContent = size;
        sizeSelect.appendChild(option);
    });
}
```

### Clickable Result Cards with Derivation Panels

Results should be clickable to reveal derivations. Only one derivation panel should be open at a time.

```html
<div class="result-item" data-deriv="torque" onclick="toggleDerivation('torque')">
    <div class="label">Assembly Torque</div>
    <div class="value">50.1 <span class="unit">N·m</span></div>
    <span class="icon">▼</span>
</div>

<div class="derivation-panel" id="deriv-torque">
    <div class="derivation-header">
        <span class="derivation-title">Assembly Torque Derivation</span>
        <button class="derivation-close" onclick="toggleDerivation('torque')">×</button>
    </div>
    <div class="derivation-step">
        <div class="step-title">1. Torque-Tension Equation</div>
        <div class="equation">$$ T = K \cdot d \cdot F_i $$</div>
    </div>
    <div class="derivation-step">
        <div class="step-title">2. Substituted Values</div>
        <div class="equation" id="subst-torque"><!-- Populated by JS --></div>
        <div class="inputs">
            <span class="input-tag">K = 0.150</span>
            <span class="input-tag">d = 10.0 mm</span>
            <span class="input-tag">Fᵢ = 33.4 kN</span>
        </div>
    </div>
    <div class="derivation-step">
        <div class="step-title">Result</div>
        <div class="result-box">T = 50.1 N·m</div>
    </div>
</div>
```

### Safety Factor Gauges

Display safety factors as visual gauges with color-coded status.

```html
<div class="safety-gauge">
    <div class="gauge-label">Yield Safety</div>
    <div class="gauge-bar-container">
        <div class="gauge-bar success" style="width: 75%"></div>
        <div class="gauge-threshold" style="left: 66.7%"></div> <!-- SF=1.5 threshold -->
    </div>
    <div class="gauge-value success">SF = 2.1</div>
</div>
```

**Color coding:**
- `success` (green): SF ≥ 1.5
- `warning` (amber): 1.0 ≤ SF < 1.5
- `danger` (red): SF < 1.0

### Status Banner

Provide an overall assessment with actionable recommendations.

```html
<div class="status-banner acceptable">
    <div class="icon">✓</div>
    <div class="content">
        <h4>Joint Design Acceptable</h4>
        <p>All safety factors meet minimum requirements.</p>
    </div>
</div>

<div class="status-banner marginal">
    <div class="icon">⚠</div>
    <div class="content">
        <h4>Marginal Design</h4>
        <p>One or more safety factors are below recommended values.</p>
        <ul class="recommendations">
            <li>Consider higher strength bolt grade</li>
            <li>Review loading assumptions</li>
        </ul>
    </div>
</div>
```

### Settings Panel (Theme, Density, Precision)

Tools can include a slide-out settings panel for user preferences. See `tools/example_tool_settings/` for the reference implementation and `tools/bolt-torque/` for a production example.

**Standard settings to include:**
- **Theme:** Light / Dark / System (auto)
- **Density:** Comfortable / Compact
- **Precision:** 2 / 3 / 4 decimal places
- **Auto-calculate:** Toggle (only for simple tools per guidelines above)

```html
<!-- Settings button in navbar -->
<div class="nav-actions">
    <button class="settings-button" id="settings-button" type="button">Settings</button>
</div>

<!-- Settings panel (slides in from right) -->
<aside class="settings-panel" id="settings-panel" aria-hidden="true">
    <div class="settings-header">
        <h3>Tool Settings</h3>
        <button class="settings-close" id="settings-close" type="button">Close</button>
    </div>
    <div class="settings-content">
        <!-- Theme selector with segmented buttons -->
        <div class="setting-row">
            <div>
                <div class="setting-label">Theme</div>
                <div class="setting-help">Light, dark, or system default.</div>
            </div>
            <div class="segmented" role="group" aria-label="Theme">
                <button type="button" data-theme="light">Light</button>
                <button type="button" data-theme="dark">Dark</button>
                <button type="button" data-theme="system">Auto</button>
            </div>
        </div>
    </div>
</aside>
```

**JavaScript for settings persistence:**
```javascript
const STORAGE_KEY = 'tool-name-settings';
const defaultSettings = { theme: 'system', density: 'comfortable', precision: 2 };
let settings = { ...defaultSettings };

function loadSettings() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) settings = { ...defaultSettings, ...JSON.parse(stored) };
}

function applySettings() {
    document.body.dataset.theme = settings.theme;
    document.body.dataset.density = settings.density;
}
```

### Dark Mode CSS Variables (CRITICAL)

**⚠️ COMMON MISTAKE: Forgetting to set `color` on form inputs causes illegible text in dark mode.**

The dark mode implementation uses CSS custom properties on the `<body>` element. When `data-theme="dark"` is set (or system preference is dark with `data-theme="system"`), the variables are overridden.

**Light mode (default) variables:**
```css
:root {
    --primary-color: #0b0d12;
    --primary-light: #f4f5f7;
    --secondary-color: #4b5563;
    --accent-color: #111827;
    --text-color: #111827;
    --text-light: #6b7280;
    --border-color: #e5e7eb;
    --bg-color: #f8f9fb;
    --bg-card: #ffffff;
    --shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
    --shadow-lg: 0 6px 18px rgba(15, 23, 42, 0.08);
}
```

**Dark mode variable overrides:**
```css
body[data-theme="dark"] {
    --primary-color: #f9fafb;
    --primary-light: #111827;
    --secondary-color: #9ca3af;
    --accent-color: #f9fafb;
    --text-color: #f9fafb;
    --text-light: #9ca3af;
    --border-color: #1f2937;
    --bg-color: #0b0d12;
    --bg-card: #111827;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
    --shadow-lg: 0 16px 32px rgba(0, 0, 0, 0.55);
}

/* System preference fallback */
@media (prefers-color-scheme: dark) {
    body[data-theme="system"] {
        /* Same overrides as body[data-theme="dark"] */
    }
}
```

**Understanding the color mappings:**

| Variable | Light Mode | Dark Mode | Usage |
|----------|-----------|-----------|-------|
| `--text-color` | `#111827` (near black) | `#f9fafb` (near white) | Primary text, input text |
| `--text-light` | `#6b7280` (gray) | `#9ca3af` (light gray) | Secondary text, hints |
| `--bg-color` | `#f8f9fb` (off-white) | `#0b0d12` (near black) | Page background |
| `--bg-card` | `#ffffff` (white) | `#111827` (dark gray) | Cards, inputs, panels |
| `--border-color` | `#e5e7eb` (light gray) | `#1f2937` (dark gray) | Borders, dividers |
| `--primary-light` | `#f4f5f7` (light) | `#111827` (dark) | Subtle backgrounds |

**⚠️ NAVBAR: Two valid approaches (don't mix them!)**

Choose ONE navbar style and be consistent:

**Option A: Dark navbar (fixed colors)** - Stays dark in both modes. Used by GitHub, Slack, VS Code.
```css
.navbar {
    background: #0b0d12;
    border-bottom: 1px solid #1f2937;
}
.nav-brand { color: #fff; }
.settings-button {
    border: 1px solid rgba(255,255,255,0.2);
    color: #fff;
}
```

**Option B: Adaptive navbar (CSS variables)** - Flips with theme. Background and text must BOTH use variables.
```css
.navbar {
    background-color: var(--bg-card);
    border-bottom: 1px solid var(--border-color);
}
.nav-brand { color: var(--text-color); }
.settings-button {
    border: 1px solid var(--border-color);
    color: var(--text-color);
}
```

**⚠️ WRONG - Mixing approaches causes invisible text:**
```css
.navbar {
    background: var(--primary-color);  /* Flips to white in dark mode */
}
.nav-brand { color: #fff; }  /* Fixed white = invisible on white! */
```

**⚠️ CRITICAL: Input and Select Styling**

Form inputs do NOT inherit `color` from their parent by default in most browsers. You MUST explicitly set both `background-color` AND `color` on all form controls:

```css
/* CORRECT - Always set both background AND text color */
.input-group input[type="number"],
.input-group input[type="text"],
.input-group select {
    background-color: var(--bg-card);
    color: var(--text-color);          /* ← REQUIRED for dark mode! */
    border: 1px solid var(--border-color);
}

/* WRONG - Missing color property causes white text on white background in light mode
   or dark text on dark background in dark mode */
.input-group input {
    background-color: var(--bg-card);
    /* color not set - will be illegible in one mode or the other */
}
```

**Other elements that commonly need explicit color:**
- `<textarea>` elements
- `<select>` options
- Placeholder text (use `::placeholder` pseudo-element)
- Disabled inputs

```css
/* Placeholder text in dark mode */
.input-group input::placeholder {
    color: var(--text-light);
    opacity: 0.7;
}

/* Select dropdown styling */
.input-group select option {
    background-color: var(--bg-card);
    color: var(--text-color);
}
```

**Compact density mode:**
```css
body[data-density="compact"] .card { padding: 18px; }
body[data-density="compact"] .input-group { margin-bottom: 0.85rem; }
body[data-density="compact"] .input-group label { font-size: 0.82rem; }
body[data-density="compact"] .input-group input,
body[data-density="compact"] .input-group select { padding: 9px 12px; font-size: 0.9rem; }
```

### Comprehensive Background Tab

The Background tab should be a complete educational resource with:

1. **Table of Contents** with anchor links
2. **Numbered sections** covering:
   - Overview / Why this matters
   - Key equations with variable legends
   - How to interpret results
   - Worked examples
   - References and standards
3. **Callout boxes** for key insights, warnings, and practical tips
4. **Reference tables** for lookup values (K-factors, material properties, etc.)

```html
<div id="background" class="tab-content">
    <!-- Table of Contents -->
    <div class="toc-card">
        <strong>Contents</strong>
        <ol>
            <li><a href="#bg-overview">Overview</a></li>
            <li><a href="#bg-equations">Key Equations</a></li>
            <li><a href="#bg-interpretation">Interpreting Results</a></li>
            <li><a href="#bg-examples">Worked Examples</a></li>
            <li><a href="#bg-references">References</a></li>
        </ol>
    </div>

    <div id="bg-overview" class="bg-section">
        <h3>1. Overview</h3>
        <p>...</p>
        <div class="callout-warning">
            <strong>Key Insight:</strong> Most failures occur due to...
        </div>
    </div>

    <!-- ... more sections ... -->
</div>
```

---

## Visualization Standards

* **Axes + units:** Every plotted axis must be labeled and include units (e.g., `Pressure (kPa)`). Diagrams without axes must label any numeric callouts with units.
* **Legend required:** Always include a legend, even for single-series plots, so the dataset is unambiguous.
* **Scale clarity:** Declare linear vs. log axes explicitly. For log scales, enforce positive-only data and explain any filtered points.
* **Data hygiene:** Never plot NaN/inf values; guard against empty datasets and surface a user-facing warning instead.
* **Annotations:** Any markers, thresholds, or highlights must state their numeric value and match the underlying data.
* **Mixed-unit plotting:** Do not plot mixed-unit values on the same axis. Use dimensionless ratios or separate charts.
* **Chart explanations:** Every chart should have a brief explanation below it stating what the chart shows and key insights to look for.

---

## Testing & Verification

### Local Environment Setup

To keep WSL and macOS machines aligned without heavy tooling, install the few development dependencies directly:

1. (Optional) create a project virtual environment: `python3 -m venv .venv && source .venv/bin/activate`
2. Install the dev requirements: `python3 -m pip install -r requirements-dev.txt`

This provides `pytest` (and any future lint/test utilities) while leaving the Pyodide-facing code dependency-free.

### Testing Checklist

* **Numerical checks:** Add or update `tests/` cases (use `pytest`, run via `python3 -m pytest`) that exercise new `pycalcs` functions across nominal, edge, and failure inputs. If you introduce a regression-safe fixture (e.g., compare against a known textbook example), document the reference in the test docstring.
* **Docstring parser smoke test:** Run `python -c "from pycalcs import utils, <module>; print(utils.get_documentation('<module>', '<function>'))"` to confirm the docstring splits cleanly before committing.
* **Frontend sanity:** Open the tool in a local static server (e.g., `python -m http.server`) and verify tooltips, tab switching, and error handling. Capture at least one screenshot or screen recording when submitting a PR if the UI meaningfully changes.
* **Graph verification (required):** Any tool that renders a graph, plot, or diagram must include a quick visual check. Capture at least one screenshot after running nominal inputs and review it against this checklist: axis labels and units present, scale type correct (linear/log), legend matches series, data values are finite (no NaN/inf gaps), ranges look physically plausible, and any annotations or highlights map to the right values.
* **Export/visual checks:** When the tool supports exports or plots, download the artifact and ensure units, labels, and legends align with the on-screen values.

---

## Deployment & Hosting

The project is deployed to two hosts simultaneously:

| Host | URL | Config File | Notes |
|------|-----|-------------|-------|
| **Netlify (primary)** | https://transparent.tools | `netlify.toml` | Production domain |
| **GitHub Pages (legacy)** | https://amarschn.github.io | `config.yml` | Still active |

Both deployments are automatic on push to `main`.

### Netlify CLI Commands

```bash
# Install (one-time)
npm install -g netlify-cli

# Authenticate (one-time)
netlify login

# Link repo to Netlify site (one-time, from repo root)
netlify link

# Open admin dashboard
netlify open:admin

# Manual production deploy
netlify deploy --prod

# Preview deploy (generates preview URL for testing)
netlify deploy
```

### Build Configuration

- **Build step:** None (pure static HTML/JS site)
- **Publish directory:** `.` (root)
- **Config:** `netlify.toml` in repo root

### Analytics

All pages include Google Analytics 4 for traffic tracking.

**Measurement ID:** `G-YG3SBRRZFZ`

**Required snippet** (must be in `<head>` of every tool page):

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-YG3SBRRZFZ"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-YG3SBRRZFZ');
</script>
```

**Placement:** Insert immediately after the `<meta name="viewport">` tag.

**Dashboard:** [analytics.google.com](https://analytics.google.com) (requires account access)

### Support & Monetization

- **Ko-fi:** https://ko-fi.com/transparent_tools (link in site footer)

---

## Tool Roadmaps

Some tools include a tool-local `ROADMAP.md` under `tools/<tool>/`. Treat this file as a focused TODO list for future agentic or human work on that tool.

* Keep entries concise and actionable.
* Update the roadmap when completing significant items or when new gaps are discovered.
* Review the roadmap before large changes to ensure alignment with outstanding work.

---

## Roadmap

1. **Build shared styling primitives:** Extract the inline CSS from the example tool into a versioned global stylesheet and update all tools to consume it.
2. **Harden automated validation:** Add a lightweight pytest suite for `pycalcs/` along with CI checks that run formatting, docstring parsing smoke tests, and basic numerical regression cases.
3. **Expand catalog coverage:** Prioritise high-impact disciplines (controls, civil structures, power electronics) and backfill READMEs and exports for existing tools before shipping new calculators.
