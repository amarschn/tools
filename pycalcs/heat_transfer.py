"""Heat transfer helper functions for layered systems."""

from __future__ import annotations

from typing import Iterable, List


def composite_wall_analysis(
    area: float,
    interior_temperature: float,
    exterior_temperature: float,
    layer_thicknesses: Iterable[float],
    layer_conductivities: Iterable[float],
    interior_convection_coefficient: float | None = None,
    exterior_convection_coefficient: float | None = None,
) -> dict[str, float | List[float]]:
    """
    Evaluate steady one-dimensional heat transfer through a layered wall.

    This helper assembles a thermal resistance network consisting of optional
    interior/exterior convection films and a series of conduction layers. It
    returns the overall heat transfer rate, heat flux, overall U-value, and the
    temperature at each interface so that users can verify intermediate
    temperature drops.

    ---Parameters---
    area : float
        Exposed wall area in square metres (m^2). Must be greater than zero.
    interior_temperature : float
        Ambient temperature on the hot side in degrees Celsius (°C).
    exterior_temperature : float
        Ambient temperature on the cold side in degrees Celsius (°C).
    layer_thicknesses : iterable of float
        Thickness of each solid layer in metres (m). Length must match
        ``layer_conductivities``. All values must be greater than zero.
    layer_conductivities : iterable of float
        Thermal conductivity for each layer in watts per metre-kelvin (W/m·K).
        Length must match ``layer_thicknesses`` and all values must be greater than zero.
    interior_convection_coefficient : float, optional
        Interior heat transfer coefficient (h_i) in W/m^2·K. When provided it
        models an interior film resistance of 1/(h_i·A). Must be greater than zero.
    exterior_convection_coefficient : float, optional
        Exterior heat transfer coefficient (h_o) in W/m^2·K. When provided it
        models an exterior film resistance of 1/(h_o·A). Must be greater than zero.

    ---Returns---
    heat_transfer_rate : float
        Overall heat transfer rate (Q) in watts (W).
    heat_flux : float
        Heat flux (q'') in watts per square metre (W/m^2).
    overall_u_value : float
        Overall heat transfer coefficient (U) in W/m^2·K.
    total_thermal_resistance : float
        Total thermal resistance (R_total) in kelvin per watt (K/W).
    interface_temperatures : list
        Temperatures at the interior surface, each layer interface, and exterior
        surface in degrees Celsius (°C). The list starts at the interior surface
        (after the interior film, if present) and ends at the exterior ambient.

    ---LaTeX---
    R_\\text{film,i} = \\frac{1}{h_i A},\\quad
    R_j = \\frac{L_j}{k_j A},\\quad
    R_\\text{film,o} = \\frac{1}{h_o A} \\\\
    R_\\text{total} = R_\\text{film,i} + \\sum_j R_j + R_\\text{film,o} \\\\
    Q = \\frac{T_i - T_o}{R_\\text{total}},\\quad
    q'' = \\frac{Q}{A},\\quad
    U = \\frac{1}{A R_\\text{total}}

    ---References---
    Incropera, F. P., DeWitt, D. P., Bergman, T. L., & Lavine, A. S. (2007).
    *Fundamentals of Heat and Mass Transfer* (6th ed.). Wiley.
    """
    if area <= 0:
        raise ValueError("Area must be greater than zero.")

    thicknesses = [float(value) for value in layer_thicknesses]
    conductivities = [float(value) for value in layer_conductivities]

    if not thicknesses:
        raise ValueError("At least one solid layer is required.")
    if len(thicknesses) != len(conductivities):
        raise ValueError("Layer thickness and conductivity lists must be the same length.")
    if any(value <= 0 for value in thicknesses):
        raise ValueError("All layer thicknesses must be greater than zero.")
    if any(value <= 0 for value in conductivities):
        raise ValueError("All layer conductivities must be greater than zero.")

    resistances: list[tuple[str, float]] = []

    if interior_convection_coefficient is not None:
        if interior_convection_coefficient <= 0:
            raise ValueError("Interior convection coefficient must be greater than zero.")
        resistances.append(
            ("interior_film", 1.0 / (interior_convection_coefficient * area))
        )

    for index, (thickness, conductivity) in enumerate(zip(thicknesses, conductivities), start=1):
        resistance = thickness / (conductivity * area)
        resistances.append((f"layer_{index}", resistance))

    if exterior_convection_coefficient is not None:
        if exterior_convection_coefficient <= 0:
            raise ValueError("Exterior convection coefficient must be greater than zero.")
        resistances.append(
            ("exterior_film", 1.0 / (exterior_convection_coefficient * area))
        )

    total_resistance = sum(resistance for _, resistance in resistances)
    delta_temperature = interior_temperature - exterior_temperature

    heat_transfer_rate = delta_temperature / total_resistance
    heat_flux = heat_transfer_rate / area
    overall_u_value = 1.0 / (total_resistance * area)

    interface_temperatures: list[float] = []
    running_temperature = interior_temperature

    for label, resistance in resistances:
        temperature_drop = heat_transfer_rate * resistance
        running_temperature -= temperature_drop

        if label.startswith("layer_") or label == "interior_film":
            interface_temperatures.append(round(running_temperature, 6))

    interface_temperatures.append(exterior_temperature)

    subst_total_resistance = (
        "R_{\\text{total}} = "
        + " + ".join(
            [
                f"{resistance:.6f}"
                for _, resistance in resistances
            ]
        )
        + f" = {total_resistance:.6f}"
    )
    subst_heat_rate = (
        f"Q = \\frac{{{interior_temperature} - {exterior_temperature}}}{{{total_resistance:.6f}}}"
    )
    subst_heat_flux = (
        f"q'' = \\frac{{{heat_transfer_rate:.3f}}}{{{area}}}"
    )
    subst_u_value = (
        f"U = \\frac{{1}}{{{area} \\times {total_resistance:.6f}}}"
    )

    return {
        "heat_transfer_rate": float(heat_transfer_rate),
        "heat_flux": float(heat_flux),
        "overall_u_value": float(overall_u_value),
        "total_thermal_resistance": float(total_resistance),
        "interface_temperatures": interface_temperatures,
        "subst_total_thermal_resistance": subst_total_resistance,
        "subst_heat_transfer_rate": subst_heat_rate,
        "subst_heat_flux": subst_heat_flux,
        "subst_overall_u_value": subst_u_value,
    }
