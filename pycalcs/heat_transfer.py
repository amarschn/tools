"""Heat transfer helper functions for layered systems."""

from __future__ import annotations

from typing import Dict, Iterable, List

IP_R_CONVERSION = 5.678263  # (m²·K)/W → (hr·ft²·°F)/BTU
IP_U_CONVERSION = 0.176110  # W/(m²·K) → BTU/(hr·ft²·°F)
IP_Q_CONVERSION = 3.412142  # W → BTU/hr
IP_Q_FLUX_CONVERSION = 0.317101  # W/m² → BTU/(hr·ft²)


def composite_wall_analysis(
    area: float,
    interior_temperature: float,
    exterior_temperature: float,
    layer_thicknesses: Iterable[float],
    layer_conductivities: Iterable[float],
    interior_convection_coefficient: float | None = None,
    exterior_convection_coefficient: float | None = None,
) -> dict[str, float | List[float] | Dict[str, float] | List[Dict[str, float | str]]]:
    """
    Evaluate steady one-dimensional heat transfer through a layered wall.

    This helper assembles a one-dimensional thermal-resistance network with
    optional convection films on each side and a stack of conduction layers in
    between. It returns not only the overall heat transfer rate and U-value, but
    also the individual resistances, interface temperature profile, and
    conversions to the inch–pound unit system so that envelope calculations can
    be cross-checked against building-code tables.

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
    heat_flux_ip : float
        Heat flux expressed in BTU/(hr·ft^2).
    heat_transfer_rate_ip : float
        Overall heat transfer rate in BTU/hr.
    overall_u_value : float
        Overall heat transfer coefficient (U) in W/m^2·K.
    overall_u_value_ip : float
        Overall heat transfer coefficient expressed in BTU/(hr·ft^2·°F).
    total_thermal_resistance : float
        Total thermal resistance (R_total) in kelvin per watt (K/W).
    total_r_value_ip : float
        Total thermal resistance expressed in (hr·ft^2·°F)/BTU.
    layer_resistances : list
        Thermal resistance contributed by each conduction layer in K/W.
    film_resistances : dict
        Thermal resistance for ``interior`` and ``exterior`` films (when
        provided) in K/W.
    temperature_profile : list
        Ordered list of dictionaries describing the temperature (°C) after each
        resistance element. Each entry contains the keys ``name``,
        ``type`` (ambient, convection, conduction), ``temperature_c``, and
        ``resistance_k_per_w``.
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
    subst_total_r_value_ip : str
        Symbolic substitution used to derive ``total_r_value_ip``.
    subst_heat_transfer_rate : str
        Symbolic substitution used to derive ``heat_transfer_rate``.
    subst_heat_transfer_rate_ip : str
        Symbolic substitution used to derive ``heat_transfer_rate_ip``.
    subst_heat_flux : str
        Symbolic substitution used to derive ``heat_flux``.
    subst_heat_flux_ip : str
        Symbolic substitution used to derive ``heat_flux_ip``.
    subst_overall_u_value : str
        Symbolic substitution used to derive ``overall_u_value``.
    subst_overall_u_value_ip : str
        Symbolic substitution used to derive ``overall_u_value_ip``.
    subst_layer_resistances : list
        Symbolic substitutions for each conduction layer resistance.
    subst_film_resistances : dict
        Symbolic substitutions for the film resistances (if supplied).

    ---References---
    Incropera, F. P., DeWitt, D. P., Bergman, T. L., & Lavine, A. S. (2007).
        *Fundamentals of Heat and Mass Transfer* (6th ed.). Wiley.
    ASHRAE (2017). *Handbook – Fundamentals*, Chapter 26: Heat, Air, and
        Moisture Control in Building Assemblies — Material Properties.
    Cengel, Y. A., & Ghajar, A. J. (2015). *Heat and Mass Transfer*
        (5th ed.). McGraw-Hill Education.
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

    resistances: list[tuple[str, float, str]] = []
    conduction_resistances: List[float] = []
    conduction_substitutions: List[str] = []
    film_resistances: Dict[str, float] = {}
    film_substitutions: Dict[str, str] = {}

    if interior_convection_coefficient is not None:
        if interior_convection_coefficient <= 0:
            raise ValueError("Interior convection coefficient must be greater than zero.")
        interior_film_resistance = 1.0 / (interior_convection_coefficient * area)
        film_resistances["interior"] = interior_film_resistance
        film_substitutions["interior"] = (
            f"R_{{\\text{{film,i}}}} = \\frac{{1}}{{{interior_convection_coefficient} \\times {area}}} = {interior_film_resistance:.6f}"
        )
        resistances.append(
            ("interior_film", interior_film_resistance, "convection")
        )

    for index, (thickness, conductivity) in enumerate(zip(thicknesses, conductivities), start=1):
        resistance = thickness / (conductivity * area)
        conduction_resistances.append(resistance)
        conduction_substitutions.append(
            f"R_{{\\text{{cond,{index}}}}} = \\frac{{{thickness}}}{{{conductivity} \\times {area}}} = {resistance:.6f}"
        )
        resistances.append((f"layer_{index}", resistance, "conduction"))

    if exterior_convection_coefficient is not None:
        if exterior_convection_coefficient <= 0:
            raise ValueError("Exterior convection coefficient must be greater than zero.")
        exterior_film_resistance = 1.0 / (exterior_convection_coefficient * area)
        film_resistances["exterior"] = exterior_film_resistance
        film_substitutions["exterior"] = (
            f"R_{{\\text{{film,o}}}} = \\frac{{1}}{{{exterior_convection_coefficient} \\times {area}}} = {exterior_film_resistance:.6f}"
        )
        resistances.append(
            ("exterior_film", exterior_film_resistance, "convection")
        )

    total_resistance = sum(resistance for _, resistance, _ in resistances)
    delta_temperature = interior_temperature - exterior_temperature

    heat_transfer_rate = delta_temperature / total_resistance
    heat_transfer_rate_ip = heat_transfer_rate * IP_Q_CONVERSION
    heat_flux = heat_transfer_rate / area
    heat_flux_ip = heat_flux * IP_Q_FLUX_CONVERSION
    overall_u_value = 1.0 / (total_resistance * area)
    overall_u_value_ip = overall_u_value * IP_U_CONVERSION
    total_r_value_ip = total_resistance * IP_R_CONVERSION

    temperature_profile: List[Dict[str, float | str]] = [
        {
            "name": "Interior ambient",
            "type": "ambient",
            "temperature_c": float(interior_temperature),
            "resistance_k_per_w": 0.0,
        }
    ]
    running_temperature = interior_temperature
    num_layers = len(thicknesses)

    interface_temperatures: List[float] = []

    for label, resistance, resistance_type in resistances:
        temperature_drop = heat_transfer_rate * resistance
        running_temperature -= temperature_drop

        if label == "interior_film":
            name = "Interior surface (after h_i)"
        elif label.startswith("layer_"):
            index = int(label.split("_")[1])
            if index == num_layers:
                name = f"Exterior surface after layer {index}"
            else:
                name = f"Interface after layer {index}"
        elif label == "exterior_film":
            name = "Exterior ambient (after h_o)"
        else:
            name = label

        temperature_profile.append(
            {
                "name": name,
                "type": resistance_type,
                "temperature_c": round(running_temperature, 6),
                "resistance_k_per_w": resistance,
            }
        )

        if resistance_type == "conduction" or label == "interior_film":
            interface_temperatures.append(round(running_temperature, 6))

    subst_total_resistance = (
        "R_{\\text{total}} = "
        + " + ".join(
            [
                f"{resistance:.6f}"
                for _, resistance, _ in resistances
            ]
        )
        + f" = {total_resistance:.6f}"
    )
    subst_heat_rate = (
        f"\\dot{{Q}} = \\frac{{{interior_temperature} - {exterior_temperature}}}{{{total_resistance:.6f}}} = {heat_transfer_rate:.3f}"
    )
    subst_heat_flux = (
        f"q'' = \\frac{{{heat_transfer_rate:.3f}}}{{{area}}} = {heat_flux:.3f}"
    )
    subst_u_value = (
        f"U = \\frac{{1}}{{{area} \\times {total_resistance:.6f}}} = {overall_u_value:.3f}"
    )
    subst_heat_rate_ip = (
        f"\\dot{{Q}}_{{\\text{{IP}}}} = {heat_transfer_rate:.3f} \\times {IP_Q_CONVERSION:.3f} = {heat_transfer_rate_ip:.3f}"
    )
    subst_heat_flux_ip = (
        f"q''_{{\\text{{IP}}}} = {heat_flux:.3f} \\times {IP_Q_FLUX_CONVERSION:.3f} = {heat_flux_ip:.3f}"
    )
    subst_u_value_ip = (
        f"U_{{\\text{{IP}}}} = {overall_u_value:.3f} \\times {IP_U_CONVERSION:.6f} = {overall_u_value_ip:.3f}"
    )
    subst_total_r_value_ip = (
        f"R_{{\\text{{total,IP}}}} = {total_resistance:.6f} \\times {IP_R_CONVERSION:.3f} = {total_r_value_ip:.3f}"
    )

    return {
        "heat_transfer_rate": float(heat_transfer_rate),
        "heat_transfer_rate_ip": float(heat_transfer_rate_ip),
        "heat_flux": float(heat_flux),
        "heat_flux_ip": float(heat_flux_ip),
        "overall_u_value": float(overall_u_value),
        "overall_u_value_ip": float(overall_u_value_ip),
        "total_thermal_resistance": float(total_resistance),
        "total_r_value_ip": float(total_r_value_ip),
        "layer_resistances": conduction_resistances,
        "film_resistances": film_resistances,
        "temperature_profile": temperature_profile,
        "interface_temperatures": interface_temperatures,
        "subst_total_thermal_resistance": subst_total_resistance,
        "subst_heat_transfer_rate": subst_heat_rate,
        "subst_heat_transfer_rate_ip": subst_heat_rate_ip,
        "subst_heat_flux": subst_heat_flux,
        "subst_overall_u_value": subst_u_value,
        "subst_heat_flux_ip": subst_heat_flux_ip,
        "subst_overall_u_value_ip": subst_u_value_ip,
        "subst_total_r_value_ip": subst_total_r_value_ip,
        "subst_layer_resistances": conduction_substitutions,
        "subst_film_resistances": film_substitutions,
    }
