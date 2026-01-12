from __future__ import annotations

import math


def calculate_circle_basics(diameter_mm: float) -> dict[str, float | str]:
    """
    Calculates circle area and circumference from a diameter input.

    This intentionally simple example keeps everything in millimetres to make
    unit tracking obvious while demonstrating the Python-to-UI workflow.

    ---Parameters---
    diameter_mm : float
        Circle diameter in millimetres (mm). Must be positive.

    ---Returns---
    area_mm2 : float
        Circle area in square millimetres (mm^2).
    circumference_mm : float
        Circle circumference in millimetres (mm).

    ---LaTeX---
    A = \\pi \\left(\\frac{d}{2}\\right)^{2}
    C = \\pi d
    """
    diameter = float(diameter_mm)
    if diameter <= 0.0:
        raise ValueError("diameter_mm must be positive.")

    radius = diameter / 2.0
    area = math.pi * radius**2
    circumference = math.pi * diameter

    return {
        "area_mm2": area,
        "circumference_mm": circumference,
        "subst_area_mm2": (
            "A = \\pi (d/2)^2 = "
            f"\\pi ({diameter:.2f}\\text{{ mm}}/2)^2 = {area:.2f}\\text{{ mm}}^2"
        ),
        "subst_circumference_mm": (
            "C = \\pi d = "
            f"\\pi \\times {diameter:.2f}\\text{{ mm}} = {circumference:.2f}\\text{{ mm}}"
        ),
    }
