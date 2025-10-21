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
* **Consistency:** All tools should share a similar, clean, and simple user interface. This creates a cohesive experience as users navigate between different calculators.
* **Dependency-Free Core:** The core Python library functions should have minimal to no external dependencies to ensure they run smoothly with Pyodide and to avoid versioning conflicts.
* **Visualizations:** Where appropriate, tools should include visualizations (plots, diagrams, etc.) to help users better understand the results and the underlying concepts.
* **Exporting:** Engineering work is still done in Excel and other tools, and that is unlikely to change. Many of the tools in this repo will need some form of export function that can output an Excel document or similar with all calculations in that document to be used locally by a user for verification, modification, and private use.

## Architecture Overview

The project is a static web app hosted on GitHub Pages, with calculations performed client-side using Pyodide.

* **Frontend:** Each tool is a self-contained HTML file. We use a consistent CSS stylesheet for a uniform look and feel. JavaScript is used to handle user input, interact with the Pyodide environment, and update the UI. There should be a relatively straightforward navigation between different tools and within the base `tools` home page.
* **Backend (Client-Side):** We use [Pyodide](https://pyodide.org/) to run Python code directly in the browser. This allows us to write complex calculation logic in Python without needing a server.
* **Core Library (`/py/library.py`):** This is the heart of our project. It contains all the core Python functions for our calculations.
    * **Docstrings are CRITICAL:** Every function in this library *must* have a detailed docstring that includes:
        * A clear description of what the function does.
        * A list of parameters with their types and descriptions.
        * What the function returns.
        * The mathematical equations used, written in LaTeX format.
        * Any references to textbooks, papers, or standards.
* **Tools (`/tools/`):** Each tool lives in its own directory (e.g., `/tools/beam_deflection/`) and consists of at least an `index.html` file. Many of these tools directories will have their own `AGENTS.md` file that further refines what is needed for that tool.

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
    * Add these functions to `/py/library.py`.
    * **Crucially, write excellent docstrings for your new functions.**
4.  **Create the HTML (`index.html`):**
    * You **must** use the official template located at `tools/example_tool` as the starting point for all new tools. Do not start from scratch or another tool.
    * This template is mandatory for all contributors, including AI agents, to ensure consistency and adherence to project principles.
    * Modify the template's placeholder content (inputs, outputs, README section) to fit your specific tool.
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
    * To make your new tool discoverable, you **must** register it in the `_catalog.json` file located in the project's root directory. This file is the central manifest that dynamically powers the main landing page, enabling all filtering, searching, and categorization.
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

All new tools **must** be built using the official `tools/example_tool` template.

* **For AI Agents (Codex, etc.):** When asked to create a new tool, you must first retrieve the contents of `/tools/example_tool/index.html` and use it as the foundational code. All modifications must be made *to this template*.
* **For Human Developers:** Do not copy an existing tool. Start from that template to ensure you have the latest UI structure, styles, and accessibility features.
* **Layout Variants:** Example implementations of compact, stacked, and tabbed input layouts live in `tools/example_tool_compact`, `tools/example_tool_stacked`, and `tools/example_tool_tabbed`. Use them as references for alternate form factors while still basing new tools on the core template.

This mandate enforces our core principles of consistency, usability, and progressive disclosure.

### Python

* **Style:** All Python code must follow the [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/).
* **Type Hinting:** Use type hints for all function signatures (arguments and return values). This improves readability and helps prevent bugs. Example: `def calculate_area(length: float, width: float) -> float:`.
* **Docstrings:** As stated in the architecture overview, detailed docstrings are mandatory for all functions in the core library.
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
* **CSS:** All custom styles should be added to the shared stylesheet to maintain a consistent look and feel. Use descriptive class names and avoid inline styles.
