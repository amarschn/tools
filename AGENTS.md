# Project Agents: Engineering Tools

This document outlines the vision, architecture, and contribution guidelines for the Engineering Tools project. Our goal is to create a suite of high-quality, educational, and easy-to-use engineering calculators and tools.

## Table of Contents

1. [Project Vision & Philosophy](#project-vision--philosophy)
2. [Core Principles](#core-principles)
3. [Architecture Overview](#architecture-overview)
4. [Contribution Guidelines](#contribution-guidelines)
5. [Git Workflow](#git-workflow)
6. [Coding Practices and Standards](#coding-practices-and-standards)
7. [Roadmap](#roadmap)

## Project Vision & Philosophy

The primary goal of this project is to create a GitHub Pages-hosted web application that provides a collection of powerful and intuitive engineering tools. These tools should serve a dual purpose:

1.  **Calculation and Verification:** Provide quick and accurate calculations for a wide range of engineering problems across various disciplines.
2.  **Education:** Allow users to explore the underlying principles and equations behind the calculations, fostering a deeper understanding of the subject matter.

We aim for a user experience where the initial tool is simple and straightforward, but curiosity is rewarded with detailed, step-by-step explanations available on demand.

## Core Principles

All tools (our "agents") in this repository should adhere to the following principles:

* **Usability First:** The primary function of each tool should be immediately obvious and easy to use. The user should be able to get a useful result with minimal friction.
* **Progressive Disclosure:** Complexity should be hidden by default. Users who want to understand the "nitty-gritty" can use tooltips and expandable dropdowns to reveal detailed explanations, intermediate steps, and the specific equations used. When equations are rendered, list them sequentially with clear numbering (e.g., “Equation (3)”), and include a short variable legend beneath each in the format `symbol: explanation` so readers can immediately interpret every term. The template in `tools/example_tool` illustrates this pattern; follow it when adding new tools.
* **Transparency:** Every calculation should be traceable. The exact equations, including references where applicable, must be accessible to the user. This builds trust and enhances the educational value.
* **Modularity and Reusability:** Each tool is a standalone web page. However, the core calculation logic should be written as generic, well-documented Python functions in a shared library - `/pycalcs`. This promotes code reuse and simplifies maintenance. There should be multiple python files within `/pycalcs`, each containing relevant code for a given field or discipline.
* **Single Source of Truth:** This is related to modularity and reusability, but bears explicit explanation - there should be no duplication of equations or explanations, this will result in errors. For any given variable, equation, or explanation for a phenomena, there should be only ONE place where that is documented.
* **Tool-Local References by Default:** Reference data (datasheets, curves, images, PDFs) should live with the tool that uses them unless multiple tools depend on the same asset. This keeps context tight while still allowing shared promotion when reuse is real.
* **Consistency:** All tools should share a similar, clean, and simple user interface. This creates a cohesive experience as users navigate between different calculators.
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
3.  **Add Python Logic:**
    * Identify the core calculations for your tool.
    * Write one or more Python functions to perform these calculations.
    * Add these functions to the appropriate module under `/pycalcs/` (create a new file if the discipline is not represented yet) and expose them via a clear, importable function.
    * **Crucially, write excellent docstrings for your new functions.**
4.  **Create the HTML (`index.html`):**
    * You **must** use the official template located at `tools/example_tool` as the starting point for all new tools. Do not start from scratch or another tool.
    * This template is mandatory for all contributors, including AI agents, to ensure consistency and adherence to project principles.
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

* **For AI Agents (Codex, etc.):** When asked to create a new tool, you must first retrieve the contents of `/tools/example_tool/index.html` and use it as the foundational code. All modifications must be made *to this template*.
* **For Human Developers:** Do not copy an existing tool. Start from that template to ensure you have the latest UI structure, styles, and accessibility features.
* **Layout Variants:** Example implementations of compact, stacked, and tabbed input layouts live in `tools/example_tool_compact`, `tools/example_tool_stacked`, and `tools/example_tool_tabbed`. Use them as references for alternate form factors while still basing new tools on the core template.

This mandate enforces our core principles of consistency, usability, and progressive disclosure.

### AI Tool Creation Checklist

When creating a new tool, generate these files:

1. **`/pycalcs/<module>.py`** - Calculation function with docstring containing `---Parameters---`, `---Returns---`, and `---LaTeX---` sections. Return a dict with results plus `subst_<key>` strings for showing substituted equations.

2. **`/tools/<tool-slug>/index.html`** - Copy from `/tools/example_tool/index.html`. Update `TOOL_MODULE_NAME`, `TOOL_FUNCTION_NAME`, and `PARAM_ORDER` in the script config. Match input field IDs to parameter names.

3. **`/tests/test_<module>.py`** - At least one nominal test and one with a known/textbook value.

**Reference examples:** `/pycalcs/snapfits.py` and `/tools/snap-fit-cantilever/` show the full pattern.

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

### Visualization Standards

* **Axes + units:** Every plotted axis must be labeled and include units (e.g., `Pressure (kPa)`). Diagrams without axes must label any numeric callouts with units.
* **Legend required:** Always include a legend, even for single-series plots, so the dataset is unambiguous.
* **Scale clarity:** Declare linear vs. log axes explicitly. For log scales, enforce positive-only data and explain any filtered points.
* **Data hygiene:** Never plot NaN/inf values; guard against empty datasets and surface a user-facing warning instead.
* **Annotations:** Any markers, thresholds, or highlights must state their numeric value and match the underlying data.

### Local Environment Setup

To keep WSL and macOS machines aligned without heavy tooling, install the few development dependencies directly:

1. (Optional) create a project virtual environment: `python3 -m venv .venv && source .venv/bin/activate`
2. Install the dev requirements: `python3 -m pip install -r requirements-dev.txt`

This provides `pytest` (and any future lint/test utilities) while leaving the Pyodide-facing code dependency-free.

### Testing & Verification

* **Numerical checks:** Add or update `tests/` cases (use `pytest`, run via `python3 -m pytest`) that exercise new `pycalcs` functions across nominal, edge, and failure inputs. If you introduce a regression-safe fixture (e.g., compare against a known textbook example), document the reference in the test docstring.
* **Docstring parser smoke test:** Run `python -c "from pycalcs import utils, <module>; print(utils.get_documentation('<module>', '<function>'))"` to confirm the docstring splits cleanly before committing.
* **Frontend sanity:** Open the tool in a local static server (e.g., `python -m http.server`) and verify tooltips, tab switching, and error handling. Capture at least one screenshot or screen recording when submitting a PR if the UI meaningfully changes.
* **Graph verification (required):** Any tool that renders a graph, plot, or diagram must include a quick visual check. Capture at least one screenshot after running nominal inputs and review it against this checklist: axis labels and units present, scale type correct (linear/log), legend matches series, data values are finite (no NaN/inf gaps), ranges look physically plausible, and any annotations or highlights map to the right values.
* **Export/visual checks:** When the tool supports exports or plots, download the artifact and ensure units, labels, and legends align with the on-screen values.

## Roadmap

1. **Build shared styling primitives:** Extract the inline CSS from the example tool into a versioned global stylesheet and update all tools to consume it.
2. **Harden automated validation:** Add a lightweight pytest suite for `pycalcs/` along with CI checks that run formatting, docstring parsing smoke tests, and basic numerical regression cases.
3. **Expand catalog coverage:** Prioritise high-impact disciplines (controls, civil structures, power electronics) and backfill READMEs and exports for existing tools before shipping new calculators.
