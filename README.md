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

## License
