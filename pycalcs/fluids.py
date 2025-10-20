"""Fluid mechanics calculation helpers."""

from __future__ import annotations


def compute_reynolds_number(
    velocity: float,
    characteristic_length: float,
    kinematic_viscosity: float | None = None,
    density: float | None = None,
    dynamic_viscosity: float | None = None,
) -> float:
    """
    Calculate the Reynolds number for a fluid flow scenario.

    This helper accepts either a directly supplied kinematic viscosity or the
    combination of density and dynamic viscosity. Exactly one of those
    approaches must be provided. The calculation follows the classic
    definition of the Reynolds number for incompressible flow.

    ---Parameters---
    velocity : float
        Mean flow speed in metres per second (m/s). Must be greater than zero.
    characteristic_length : float
        Representative length scale of the problem in metres (m). For internal
        flows this is typically the hydraulic diameter. Must be greater than zero.
    kinematic_viscosity : float, optional
        Kinematic viscosity of the fluid in square metres per second (m^2/s).
        Provide this when known directly. Must be greater than zero if supplied.
    density : float, optional
        Fluid density in kilograms per cubic metre (kg/m^3). Required when
        the dynamic viscosity approach is used. Must be greater than zero if supplied.
    dynamic_viscosity : float, optional
        Dynamic viscosity in pascal-seconds (Pa·s). Required when the dynamic
        viscosity approach is used. Must be greater than zero if supplied.

    ---Returns---
    reynolds_number : float
        Dimensionless Reynolds number defined as the ratio of inertial to
        viscous forces.

    ---LaTeX---
    \\mathrm{Re} = \\frac{V \\cdot L}{\\nu} = \\frac{\\rho \\cdot V \\cdot L}{\\mu}

    ---References---
    Fox, R. W., McDonald, A. T., & Pritchard, P. J. (2015). *Introduction to Fluid Mechanics* (8th ed.). Wiley.
    """
    if velocity <= 0:
        raise ValueError("Velocity must be greater than zero.")
    if characteristic_length <= 0:
        raise ValueError("Characteristic length must be greater than zero.")

    using_kinematic = kinematic_viscosity is not None
    using_dynamic = density is not None and dynamic_viscosity is not None

    if using_kinematic == using_dynamic:
        raise ValueError(
            "Supply either kinematic viscosity or both density and dynamic viscosity."
        )

    if using_kinematic:
        if kinematic_viscosity is None or kinematic_viscosity <= 0:
            raise ValueError("Kinematic viscosity must be greater than zero.")
        return (velocity * characteristic_length) / kinematic_viscosity

    assert density is not None and dynamic_viscosity is not None

    if density <= 0:
        raise ValueError("Density must be greater than zero.")
    if dynamic_viscosity <= 0:
        raise ValueError("Dynamic viscosity must be greater than zero.")

    return (density * velocity * characteristic_length) / dynamic_viscosity


def classify_reynolds_regime(reynolds_number: float) -> str:
    """
    Categorise the flow regime based on the Reynolds number.

    ---Parameters---
    reynolds_number : float
        Computed Reynolds number (dimensionless). Must be non-negative.

    ---Returns---
    regime : str
        One of ``"laminar"``, ``"transitional"``, or ``"turbulent"``.

    ---LaTeX---
    \\text{Laminar if } \\mathrm{Re} < 2300; \\quad
    \\text{Transitional if } 2300 \\le \\mathrm{Re} \\le 4000; \\quad
    \\text{Turbulent if } \\mathrm{Re} > 4000.
    """
    if reynolds_number < 0:
        raise ValueError("Reynolds number cannot be negative.")
    if reynolds_number < 2300:
        return "laminar"
    if reynolds_number <= 4000:
        return "transitional"
    return "turbulent"


def reynolds_number_analysis(
    velocity: float,
    characteristic_length: float,
    kinematic_viscosity: float | None = None,
    density: float | None = None,
    dynamic_viscosity: float | None = None,
) -> dict[str, float | str]:
    """
    Compute Reynolds number data and flow classification for a user-facing tool.

    This wrapper validates the provided transport properties, delegates the
    calculation to :func:`compute_reynolds_number`, and returns a structured
    mapping that the web UI can render directly.

    ---Parameters---
    velocity : float
        Mean flow speed in metres per second (m/s). Must be greater than zero.
    characteristic_length : float
        Representative length scale of the problem in metres (m). For internal
        flows this is typically the hydraulic diameter. Must be greater than zero.
    kinematic_viscosity : float, optional
        Kinematic viscosity of the fluid in square metres per second (m^2/s).
        Provide this when known directly. Must be greater than zero if supplied.
    density : float, optional
        Fluid density in kilograms per cubic metre (kg/m^3). Required when
        using the dynamic viscosity pathway. Must be greater than zero if supplied.
    dynamic_viscosity : float, optional
        Dynamic viscosity in pascal-seconds (Pa·s). Required when using the
        dynamic viscosity pathway. Must be greater than zero if supplied.

    ---Returns---
    reynolds_number : float
        Dimensionless Reynolds number defined as the ratio of inertial to
        viscous forces.
    flow_regime : str
        Textual classification of the flow regime (laminar, transitional, or turbulent).
    viscosity_path : str
        Indicates whether the calculation used ``"kinematic"`` viscosity or the
        ``"dynamic"`` viscosity route.

    ---LaTeX---
    \\mathrm{Re} = \\frac{V \\cdot L}{\\nu} = \\frac{\\rho \\cdot V \\cdot L}{\\mu} \\\\
    \\text{Laminar if } \\mathrm{Re} < 2300;\\, \\text{Transitional if } 2300 \\le \\mathrm{Re} \\le 4000;\\, \\text{Turbulent if } \\mathrm{Re} > 4000

    ---References---
    Fox, R. W., McDonald, A. T., & Pritchard, P. J. (2015). *Introduction to Fluid Mechanics* (8th ed.). Wiley.
    """
    reynolds = compute_reynolds_number(
        velocity=velocity,
        characteristic_length=characteristic_length,
        kinematic_viscosity=kinematic_viscosity,
        density=density,
        dynamic_viscosity=dynamic_viscosity,
    )
    regime = classify_reynolds_regime(reynolds)

    viscosity_path = "kinematic"
    if kinematic_viscosity is None:
        viscosity_path = "dynamic"

    subst_re_terms = []
    if kinematic_viscosity is not None:
        subst_re_terms.append(
            f"\\mathrm{{Re}} = \\frac{{{velocity} \\times {characteristic_length}}}{{{kinematic_viscosity}}}"
        )
    else:
        assert density is not None and dynamic_viscosity is not None
        subst_re_terms.append(
            f"\\mathrm{{Re}} = \\frac{{{density} \\times {velocity} \\times {characteristic_length}}}{{{dynamic_viscosity}}}"
        )

    subst_regime = (
        f"\\mathrm{{Re}} = {reynolds:.0f} \\Rightarrow \\text{{{regime.title()} flow}}"
    )

    return {
        "reynolds_number": float(reynolds),
        "flow_regime": regime,
        "subst_reynolds_number": subst_re_terms[0],
        "subst_flow_regime": subst_regime,
        "viscosity_path": viscosity_path,
    }
