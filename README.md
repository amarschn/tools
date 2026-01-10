# Engineering Tools

A collection of browser-based engineering calculators designed for quick calculation, verification, and education.

This repo is unapologetically a testbed for AI tools, with most of the code generated using LLM inputs. Some of the outputs are checked by human experts, some are not. No guarantee is made for correctness unless otherwise stated.

## About The Project

This repository hosts a suite of interactive engineering tools that run directly in your web browser. The primary goal is to provide a resource for students, educators, and professionals who need to perform quick calculations and also want to understand the underlying principles.

Each tool is built with a "progressive disclosure" philosophy: the interface is simple and clean for quick use, but for those who are curious, detailed explanations, equations, and intermediate steps are just a click away.

### Key Features

* **Interactive & Easy to Use:** Get accurate results with a clean and intuitive user interface.

* **Educational:** Explore the exact equations and step-by-step logic behind the calculations.

* **Multi-Disciplinary:** Covering topics in Aerospace, Civil, Mechanical, Chemical Engineering, and Mathematics.

* **Browser-Powered:** All calculations are performed on the client-side using Python via [Pyodide](https://pyodide.org/), so there's no need for a server backend.

## Getting Started

You can access the live tools directly on our GitHub Pages site:

[**https://amarschn.github.io/tools/**](https://www.google.com/search?q=https://amarschn.github.io/tools/)

## General Development Flow

We welcome contributions to expand our collection of tools! The development process is designed to be straightforward.

1. **Create a Branch:** Start by creating a new feature branch for the tool or improvement you want to add (e.g., `feature/fluid-dynamics-calculator`).

2. **Add the Logic:** The core calculation logic is written in Python. Add your functions to the central `/py/library.py` file, making sure to include detailed docstrings with equations and references.

3. **Build the Interface:** Create a new folder for your tool under `/tools/` and add the `index.html` file. This file will contain the user interface, input fields, and the JavaScript needed to interact with your Python functions via Pyodide.

4. **Submit a Pull Request:** Once your tool is complete and tested, submit a pull request to the `main` branch for review.

For a comprehensive guide on our architecture, coding standards, and a detailed step-by-step contribution workflow, please see our [**AGENTS.md**](AGENTS.md) file.
For day-to-day workflow and releases, see [**CONTRIBUTING.md**](CONTRIBUTING.md) and [**docs/RELEASE.md**](docs/RELEASE.md).

## Local Development and Testing

To test your new tool locally before submitting a pull request, you need to run a local web server from the root of the project directory. This allows the browser to correctly load the necessary files, including the Pyodide environment and your Python code.

### Steps to Test Locally

1.  **Navigate to the project root:**
    Open your terminal or command prompt and change to the root directory of the `tools` repository.
    ```bash
    cd path/to/your/tools
    ```

2.  **Start the local server:**
    If you have Python 3 installed, you can use its built-in web server. Run the following command:
    ```bash
    python -m http.server
    ```
    If you are using Python 2, the command is slightly different:
    ```bash
    python -m SimpleHTTPServer
    ```

3.  **View your tool:**
    Once the server is running, it will typically print a message like `Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/)`.
    Open your web browser and go to:
    ```text
    http://localhost:8000
    ```
    From there, you can navigate to the tool you are developing (e.g., `http://localhost:8000/tools/your-new-tool/`). Any changes you save to your HTML, CSS, or JS files will be reflected when you refresh the page.

## License
