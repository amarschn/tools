# Circle Basics (Demo)

### Purpose of This Tool

This tool calculates the **area** and **circumference** of a circle from a single input: diameter. It is intentionally minimal so new contributors can see the full workflow (Python docstring to UI tooltips to results) without extra complexity.

### Requirements

#### Python Logic

* A function `calculate_circle_basics(diameter_mm)` in `/pycalcs/circle_basics.py`.
* The function returns a dictionary with `area_mm2`, `circumference_mm`, and substituted equation strings for each result.
* The function must validate that `diameter_mm` is positive and raise `ValueError` otherwise.

#### UI

* The UI must provide one input for diameter (mm) with a sensible default.
* It must show the two results with inline equations and substituted values.
* Background tab must list the two equations with a short variable legend.
