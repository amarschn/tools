"""
Material selection helpers built around Ashby performance indices.

The functions in this module expose lightweight ranking utilities that pair
common minimum-mass design objectives with the canonical dimensionless
performance indices popularised by Ashby. These helpers are intentionally
dependency-free so they can execute inside Pyodide without additional wheels.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Callable, Iterable


@dataclass(frozen=True)
class Material:
    """Simple container for material property data."""

    name: str
    density: float  # kg/m^3
    youngs_modulus: float  # Pa
    tensile_strength: float  # Pa


_CANDIDATE_MATERIALS: tuple[Material, ...] = (
    Material(
        name="Aluminium 6061-T6",
        density=2700.0,
        youngs_modulus=69.0e9,
        tensile_strength=290.0e6,
    ),
    Material(
        name="Low-Carbon Steel",
        density=7850.0,
        youngs_modulus=210.0e9,
        tensile_strength=400.0e6,
    ),
    Material(
        name="Titanium Grade 5",
        density=4420.0,
        youngs_modulus=114.0e9,
        tensile_strength=900.0e6,
    ),
    Material(
        name="Magnesium AZ31B",
        density=1780.0,
        youngs_modulus=45.0e9,
        tensile_strength=230.0e6,
    ),
    Material(
        name="Carbon Fibre/Epoxy (UD)",
        density=1600.0,
        youngs_modulus=135.0e9,
        tensile_strength=1500.0e6,
    ),
    Material(
        name="Glass Fibre/Epoxy",
        density=1900.0,
        youngs_modulus=40.0e9,
        tensile_strength=900.0e6,
    ),
    Material(
        name="CFRP Sandwich Panel",
        density=1200.0,
        youngs_modulus=70.0e9,
        tensile_strength=600.0e6,
    ),
)


def rank_materials_for_ashby(
    design_mode: str,
    minimum_performance_index: float,
    ranked_count: float,
    *,
    materials: Iterable[Material] = _CANDIDATE_MATERIALS,
) -> dict[str, float | str]:
    """
    Rank candidate materials against classical Ashby performance indices.

    This helper implements three minimum-mass design scenarios, each mapped
    to the canonical Ashby performance index. Materials whose index falls
    below a user supplied threshold are discarded and the remaining candidates
    are sorted by descending performance.

    ---Parameters---
    design_mode : str
        Case-sensitive selector for the design objective. Supported values
        are ``stiffness_limited_beam``, ``strength_limited_tie``, and
        ``buckling_limited_column``.
    minimum_performance_index : float
        Lower bound on the Ashby index (dimensionless). Any material that
        does not reach this threshold is filtered out.
    ranked_count : float
        Number of ranked candidates to include in the summary output. The
        value is rounded to the nearest integer and must be positive.

    ---Returns---
    best_material_index : float
        Performance index of the highest-ranking material (dimensionless).
    best_material_density : float
        Density of the highest-ranking material (kg/m^3).
    best_material_modulus : float
        Young's modulus of the highest-ranking material (Pa).
    best_material_strength : float
        Tensile strength of the highest-ranking material (Pa).
    best_material_name : str
        Name of the highest-ranking material.
    ranked_summary : str
        Semicolon-separated list of the top candidates with their indices.

    ---LaTeX---
    M_{\\text{stiffness}} = \\frac{E^{1/2}}{\\rho}
    M_{\\text{strength}} = \\frac{\\sigma_y}{\\rho}
    M_{\\text{buckling}} = \\frac{E^{1/3}\\,\\sigma_y^{2/3}}{\\rho}

    ---References---
    Ashby, M. F. (2011). *Materials Selection in Mechanical Design* (4th ed.).
        Butterworth-Heinemann.
    Callister, W. D., & Rethwisch, D. G. (2018). *Materials Science and
        Engineering: An Introduction* (10th ed.). Wiley.
    """
    mode_factories: dict[str, Callable[[Material], float]] = {
        "stiffness_limited_beam": lambda mat: sqrt(mat.youngs_modulus) / mat.density,
        "strength_limited_tie": lambda mat: mat.tensile_strength / mat.density,
        "buckling_limited_column": lambda mat: (
            mat.youngs_modulus ** (1.0 / 3.0)
            * mat.tensile_strength ** (2.0 / 3.0)
            / mat.density
        ),
    }

    if design_mode not in mode_factories:
        raise ValueError(
            "Unsupported design_mode. Choose one of: "
            + ", ".join(sorted(mode_factories)),
        )
    if minimum_performance_index <= 0.0:
        raise ValueError("minimum_performance_index must be greater than zero.")

    candidate_limit = int(round(ranked_count))
    if candidate_limit <= 0:
        raise ValueError("ranked_count must round to at least 1 candidate.")

    index_function = mode_factories[design_mode]

    ranked_materials: list[tuple[Material, float]] = []
    for material in materials:
        performance_index = index_function(material)
        if performance_index >= minimum_performance_index:
            ranked_materials.append((material, performance_index))

    if not ranked_materials:
        raise ValueError(
            "No materials satisfy the minimum_performance_index constraint."
        )

    ranked_materials.sort(key=lambda pair: pair[1], reverse=True)
    top_materials = ranked_materials[:candidate_limit]
    best_material, best_index = top_materials[0]

    summary_entries = [
        f"{idx + 1}. {material.name} (M = {value:.3e})"
        for idx, (material, value) in enumerate(top_materials)
    ]
    ranked_summary = "; ".join(summary_entries)

    if design_mode == "stiffness_limited_beam":
        substituted = (
            f"M = \\frac{{\\sqrt{{{best_material.youngs_modulus:.3e}}}}}"
            f"{{{best_material.density:.3e}}} = {best_index:.3e}"
        )
    elif design_mode == "strength_limited_tie":
        substituted = (
            f"M = \\frac{{{best_material.tensile_strength:.3e}}}"
            f"{{{best_material.density:.3e}}} = {best_index:.3e}"
        )
    else:
        substituted = (
            f"M = \\frac{{({best_material.youngs_modulus:.3e})^{{1/3}}"
            f" \\times ({best_material.tensile_strength:.3e})^{{2/3}}}}"
            f"{{{best_material.density:.3e}}} = {best_index:.3e}"
        )

    return {
        "best_material_index": best_index,
        "best_material_density": best_material.density,
        "best_material_modulus": best_material.youngs_modulus,
        "best_material_strength": best_material.tensile_strength,
        "best_material_name": best_material.name,
        "ranked_summary": ranked_summary,
        "subst_best_material_index": substituted,
        "subst_best_material_density": (
            f"\\rho = {best_material.density:.3e}\\,\\text{{kg/m^3}}"
        ),
        "subst_best_material_modulus": (
            f"E = {best_material.youngs_modulus:.3e}\\,\\text{{Pa}}"
        ),
        "subst_best_material_strength": (
            f"\\sigma_y = {best_material.tensile_strength:.3e}\\,\\text{{Pa}}"
        ),
    }
