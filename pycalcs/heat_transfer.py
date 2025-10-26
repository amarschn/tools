"""Heat transfer helper functions for layered systems."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence

import math


def _single_mode_fallback(times_rel: Sequence[float], sensor_rise: Sequence[float], ratio: float) -> dict[str, float] | None:
    if len(times_rel) < 3:
        return None
    if max(sensor_rise) <= sensor_rise[0]:
        return None

    span = max(sensor_rise) - sensor_rise[0]
    lower = max(sensor_rise) + max(0.05 * span, 0.1)
    upper = lower + max(5.0, 5.0 * span)
    number_pattern_min = 60

    best_candidate: dict[str, float] | None = None
    best_variance = float("inf")

    def compute_k_values(y_inf: float) -> list[float] | None:
        values: list[float] = []
        for index in range(1, len(times_rel)):
            dt = times_rel[index] - times_rel[index - 1]
            if dt <= 0.0:
                return None
            diff_previous = y_inf - sensor_rise[index - 1]
            diff_current = y_inf - sensor_rise[index]
            if diff_previous <= 0.0 or diff_current <= 0.0:
                return None
            values.append((math.log(diff_previous) - math.log(diff_current)) / dt)
        return values

    for step in range(number_pattern_min):
        y_inf = lower + (upper - lower) * (step + 1) / (number_pattern_min + 1)
        k_values = compute_k_values(y_inf)
        if not k_values:
            continue
        mean_k = sum(k_values) / len(k_values)
        if mean_k <= 0.0:
            continue
        variance = sum((value - mean_k) ** 2 for value in k_values) / len(k_values)
        if variance < best_variance:
            best_variance = variance
            best_candidate = {
                "y_inf": y_inf,
                "k": mean_k,
            }

    if best_candidate is None:
        return None

    k_value = best_candidate["k"]
    a_value = max(k_value * (1.0 + ratio) * 20.0, 1e-6)
    c_value = k_value * (1.0 + ratio)
    b_value = ratio * a_value

    s1 = a_value + b_value + c_value
    s0 = a_value * c_value

    discriminant = s1 * s1 - 4.0 * s0
    if discriminant <= 0.0:
        return None
    sqrt_disc = math.sqrt(discriminant)
    lambda_1 = (-s1 - sqrt_disc) / 2.0
    lambda_2 = (-s1 + sqrt_disc) / 2.0

    return {
        "a": a_value,
        "b": b_value,
        "c": c_value,
        "s1": s1,
        "s0": s0,
        "lambda_1": lambda_1,
        "lambda_2": lambda_2,
    }


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


def estimate_motor_hotspot_temperature(
    times: Sequence[float],
    sensor_temperatures: Sequence[float],
    ambient_temperature: float,
    heat_capacity_ratio: float | None = None,
) -> Dict[str, float | List[float] | Dict[str, float | List[float]]]:
    """
    Estimate an unseen motor hot-spot temperature from cool-down sensor data.

    The routine models the winding as two coupled thermal masses: the concentrated
    hot spot tied to the copper turn bundle and the bulk material near the
    instrumented sensor. Once the motor is de-energised, heat stored in the hot
    spot soaks into the measured region before both nodes reject energy to the
    ambient. Fitting this second-order decay reproduces the immediately-hidden
    hot-spot temperature, extracts the dominant time constants, and reports the
    resistance ratio between the internal path (hot spot → sensor) and the path
    from the sensor to ambient.

    The solver first determines the characteristic sums ``S_1`` and ``S_0`` by a
    least-squares fit to the first and second derivatives of the measured sensor
    trace. These terms define two exponential decay rates: a fast mode that
    quantifies the exchange between the hot spot and the monitored mass, and a
    slower mode representing the heat leak from the sensor mass to ambient.
    When the data contain sufficient curvature, both modes are solved and
    reported through ``λ_1``/``λ_2`` and their associated time constants.

    In field measurements that capture only the immediate soak-out rise, the
    curvature can collapse toward a single exponential. Rather than fail, the
    routine transparently falls back to a first-order model that preserves the
    energy balance implied by the rise. The result is tagged with
    ``model_mode = 'first_order_fallback'`` so users can distinguish between the
    full two-mode fit and the reduced-order approximation.

    A key input is the **heat-capacitance ratio** ``r = C_h / C_s``: the relative
    thermal inertia of the hot spot compared with the monitored mass. When the
    sensor is embedded in iron or epoxy close to a concentrated copper strand,
    the hot spot typically stores less energy (``r`` between 0.15 and 0.5). If the
    sensor is distributed across several slots or laminated core teeth, the
    monitored mass can be comparable to the hot spot (``r`` near 1.0). Supplying
    a reasonable ratio keeps the solution physically meaningful and exposes how
    sensitive the reconstructed hot-spot temperature is to that choice.

    ---Parameters---
    times : Sequence[float]
        Ordered timestamps (s) starting at or immediately after the power
        shutdown. Values must be strictly increasing and contain at least four
        samples.
    sensor_temperatures : Sequence[float]
        Temperature history at the monitored location in degrees Celsius (°C).
        Length must match ``times``.
    ambient_temperature : float
        Assumed uniform ambient temperature (°C) of the cooling medium during
        the transient.
    heat_capacity_ratio : float, optional
        Estimated ratio of the hot-spot thermal capacitance to the monitored
        mass (C_h/C_s). Defaults to 0.35 when omitted. Choose smaller values
        (0.15–0.4) when the sensor sits in a massive frame near a concentrated
        copper strand, and larger values (0.6–1.0+) when the monitored material
        is predominantly copper or the probe measures a lumped average. Must be
        positive and small enough that the quadratic constraint
        \\(S_1^2 - 4(1+r)S_0 \\ge 0\\) is satisfied, where ``r`` is this ratio.

    ---Returns---
    hotspot_temperature : float
        Estimated initial hot-spot temperature (°C) at the instant power was
        removed.
    sensor_model : list of float
        Modelled sensor temperature trace (°C) matching the supplied timestamps.
    hotspot_model : list of float
        Modelled hot-spot temperature trace (°C) inferred from the network.
    time_seconds : list of float
        Time offsets from shutdown (s) corresponding to the model traces.
    parameters : dict
        Identified decay rates (λ₁, λ₂), intermediate coefficients (a, b, c),
        and derived ratios ``heat_capacity_ratio`` (C_h/C_s) and
        ``resistance_ratio`` (R_hs/R_sa).
    ratio_limits : dict
        Minimum and maximum feasible values of C_h/C_s implied by the fitted
        response.
    sensitivity : list of dict
        Optional sensitivity points showing how the inferred hot-spot
        temperature varies with nearby heat-capacitance ratios.
    sensor_initial_temperature : float
        First measured sensor temperature (°C) after shutdown for reference.
    fit_metrics : dict
        Root-mean-square error (°C) between the model and measured sensor data
        and the residual vector.

    ---LaTeX---
    \\begin{align*}
    C_h \\frac{\\mathrm{d}T_h}{\\mathrm{d}t} &= -\\frac{T_h - T_s}{R_{hs}},\\\\
    C_s \\frac{\\mathrm{d}T_s}{\\mathrm{d}t} &= \\frac{T_h - T_s}{R_{hs}} - \\frac{T_s - T_\\infty}{R_{sa}},\\\\
    \\theta_s &= T_s - T_\\infty,\\\\
    \\frac{\\mathrm{d}^2 \\theta_s}{\\mathrm{d}t^2} + (a + b + c) \\frac{\\mathrm{d}\\theta_s}{\\mathrm{d}t} + a c\\,\\theta_s &= 0,\\\\
    \\lambda_{1,2} &= \\frac{- (a + b + c) \\pm \\sqrt{(a + b + c)^2 - 4 a c}}{2},\\\\
    r &= \\frac{C_h}{C_s} = \\frac{b}{a},\\\\
    (1 + r)a^2 - S_1 a + S_0 &= 0,\\\\
    a &= \\frac{S_1 + \\sqrt{S_1^2 - 4(1+r)S_0}}{2(1+r)},\\\\
    T_h(0) &= T_\\infty + \\sum_{i=1}^2 \\frac{a B_i}{\\lambda_i + a},
    \\end{align*}
    where \\(a = 1/(C_h R_{hs})\\), \\(b = 1/(C_s R_{hs})\\), \\(c = 1/(C_s R_{sa})\\),
    and \\(B_i\\) are the exponential coefficients of the sensor response.

    ---Notes---
    - Estimate ``C_h`` by multiplying the mass of the hottest conductor turns by their specific heat.
      Estimate ``C_s`` from the mass of material well-coupled to the sensor; the ratio of these
      products approximates the heat-capacitance ratio ``r``.
    - A quick field estimate: start with ``r = 0.3`` for embedded stator RTDs and check the sensitivity
      table; if the inferred hot spot moves dramatically, bracket the ratio using teardown measurements.
    - Use longer cool-down captures (>5× the fast time constant) to stabilise the exponential fit.
    - The sensor trace may initially climb as heat soaks out of the hidden winding. A monotonic
      "rise then flatten" segment is acceptable—the algorithm does not require the eventual
      decay back to ambient, although providing some flattening improves curvature estimates. When only
      the rising portion is available, the solver falls back to a single-mode approximation and
      flags the result with ``model_mode = 'first_order_fallback'``.

    ---References---
    IEEE Std 112-2017, *IEEE Standard Test Procedure for Polyphase Induction
        Motors and Generators*, Annex A: Thermal Tests.\\
    Boglietti, A., Cavagnino, A., Vaschetto, S. (2011). "Thermal Model of
        Squirrel-Cage Induction Motors for Transient Operation." *IEEE
        Transactions on Industry Applications*, 47(5), 2321-2330.
    IEC 60034-18-42:2017, *Rotating electrical machines – Functional evaluation
        of insulation systems*.\\
    Ellison, A. J., Staton, D., & Chai, S. (2020). "Practical Winding Thermal
        Models for Electric Machines." *IET Electric Power Applications*, 14(3), 398–409.
    """

    times_list = [float(value) for value in times]
    temps_list = [float(value) for value in sensor_temperatures]

    if len(times_list) != len(temps_list):
        raise ValueError("Times and temperature arrays must be the same length.")
    if len(times_list) < 4:
        raise ValueError("At least four samples are required to identify the model.")

    for index in range(1, len(times_list)):
        if times_list[index] <= times_list[index - 1]:
            raise ValueError("Timestamps must be strictly increasing.")

    ambient = float(ambient_temperature)
    time_zero = times_list[0]
    times_rel = [t - time_zero for t in times_list]
    sensor_rise = [temp - ambient for temp in temps_list]

    interior_derivatives: List[float] = []
    interior_second: List[float] = []
    interior_values: List[float] = []

    for i in range(1, len(times_rel) - 1):
        delta_back = times_rel[i] - times_rel[i - 1]
        delta_forward = times_rel[i + 1] - times_rel[i]
        if delta_back <= 0.0 or delta_forward <= 0.0:
            raise ValueError("Timestamps must be strictly increasing.")

        difference_back = sensor_rise[i - 1] - sensor_rise[i]
        difference_forward = sensor_rise[i + 1] - sensor_rise[i]
        denominator = delta_back * delta_forward * (delta_back + delta_forward)
        if abs(denominator) < 1e-12:
            raise ValueError("Sampling interval is too small to compute derivatives.")

        curvature = (difference_back * delta_forward + delta_back * difference_forward) / denominator
        slope = (
            (delta_back * delta_back * difference_forward)
            - (delta_forward * delta_forward * difference_back)
        ) / denominator

        interior_second.append(2.0 * curvature)
        interior_derivatives.append(slope)
        interior_values.append(sensor_rise[i])

    if not interior_values:
        raise ValueError("Unable to form derivative estimates from provided data.")

    rhs_terms = [-value for value in interior_second]
    sum_pp = sum(der * der for der in interior_derivatives)
    sum_yy = sum(val * val for val in interior_values)
    sum_py = sum(der * val for der, val in zip(interior_derivatives, interior_values))
    sum_rhs_p = sum(der * rhs for der, rhs in zip(interior_derivatives, rhs_terms))
    sum_rhs_y = sum(val * rhs for val, rhs in zip(interior_values, rhs_terms))

    determinant = sum_pp * sum_yy - sum_py * sum_py
    if abs(determinant) < 1e-18:
        raise ValueError("Sensor data do not excite a second-order response.")

    s1 = (sum_rhs_p * sum_yy - sum_py * sum_rhs_y) / determinant
    s0 = (sum_pp * sum_rhs_y - sum_py * sum_rhs_p) / determinant

    fallback_context: dict[str, float] | None = None
    failure_detected = False

    if s1 <= 0.0:
        s1_tolerance = max(1e-12, 1e-6 * abs(sum_pp))
        if s1 >= -s1_tolerance:
            s1 = s1_tolerance
        else:
            failure_detected = True

    if not failure_detected and s0 <= 0.0:
        s0_tolerance = max(1e-12, 1e-6 * s1 * s1)
        if s0 >= -s0_tolerance:
            s0 = s0_tolerance
        else:
            failure_detected = True

    if not failure_detected:
        discriminant = s1 * s1 - 4.0 * s0
        failure_detected = discriminant <= 0.0
    else:
        discriminant = s1 * s1 - 4.0 * s0

    if failure_detected:
        ratio_candidate = 0.35 if heat_capacity_ratio is None else float(heat_capacity_ratio)
        fallback_context = _single_mode_fallback(times_rel, sensor_rise, ratio_candidate)
        if fallback_context is None:
            raise ValueError("Fitted decay rates are non-physical; capture more of the soak-out curve.")
        s1 = fallback_context["s1"]
        s0 = fallback_context["s0"]
        discriminant = s1 * s1 - 4.0 * s0

    sqrt_discriminant = math.sqrt(discriminant)
    lambda_1 = (-s1 - sqrt_discriminant) / 2.0
    lambda_2 = (-s1 + sqrt_discriminant) / 2.0

    exponent_1 = [math.exp(lambda_1 * t) for t in times_rel]
    exponent_2 = [math.exp(lambda_2 * t) for t in times_rel]

    sum_e11 = sum(val * val for val in exponent_1)
    sum_e22 = sum(val * val for val in exponent_2)
    sum_e12 = sum(val1 * val2 for val1, val2 in zip(exponent_1, exponent_2))
    sum_e1y = sum(val * rise for val, rise in zip(exponent_1, sensor_rise))
    sum_e2y = sum(val * rise for val, rise in zip(exponent_2, sensor_rise))

    det_exp = sum_e11 * sum_e22 - sum_e12 * sum_e12
    if abs(det_exp) < 1e-18:
        raise ValueError("Unable to separate exponential modes from the data set.")

    b1 = (sum_e1y * sum_e22 - sum_e12 * sum_e2y) / det_exp
    b2 = (sum_e11 * sum_e2y - sum_e12 * sum_e1y) / det_exp

    delta_1 = times_rel[1] - times_rel[0]
    delta_2 = times_rel[2] - times_rel[0]
    diff_1 = sensor_rise[1] - sensor_rise[0]
    diff_2 = sensor_rise[2] - sensor_rise[0]
    boundary_determinant = delta_1 * delta_2 * (delta_1 - delta_2)
    if abs(boundary_determinant) < 1e-12:
        raise ValueError("Initial sampling interval is too small to estimate derivative.")

    slope_0 = (delta_1 * delta_1 * diff_2 - delta_2 * delta_2 * diff_1) / boundary_determinant

    y0 = sensor_rise[0]
    ydot0 = slope_0

    lambdas = (lambda_1, lambda_2)
    coefficients = (b1, b2)

    ratio_default = 0.35
    ratio_value = ratio_default if heat_capacity_ratio is None else float(heat_capacity_ratio)
    if ratio_value <= 0.0:
        raise ValueError("Heat-capacity ratio (C_h/C_s) must be positive.")

    ratio_min_feasible = 1e-3
    ratio_max_feasible = (s1 * s1) / (4.0 * s0) - 1.0
    if ratio_max_feasible <= ratio_min_feasible:
        raise ValueError("Measured decay does not admit a positive heat-capacity ratio.")
    if ratio_value > ratio_max_feasible:
        raise ValueError(
            "Heat-capacity ratio is too large for the fitted response. "
            f"Maximum allowable value is {ratio_max_feasible:.3f}."
        )

    def solve_parameters(ratio: float) -> Dict[str, float] | None:
        if ratio <= 0.0 or ratio > ratio_max_feasible:
            return None
        discriminant_ratio = s1 * s1 - 4.0 * (1.0 + ratio) * s0
        if discriminant_ratio <= 0.0:
            return None
        a_local = (s1 + math.sqrt(discriminant_ratio)) / (2.0 * (1.0 + ratio))
        b_local = ratio * a_local
        if b_local <= 0.0:
            return None
        c_local = s0 / a_local
        hotspot_rise_local = 0.0
        denominators: List[float] = []
        for lam, coeff in zip(lambdas, coefficients):
            shifted = lam + a_local
            if abs(shifted) < 1e-12:
                return None
            denominators.append(shifted)
            hotspot_rise_local += (a_local * coeff) / shifted
        return {
            "a": a_local,
            "b": b_local,
            "c": c_local,
            "hotspot_rise": hotspot_rise_local,
            "denominators": denominators,
            "resistance_ratio": c_local / b_local,
        }

    primary_parameters = solve_parameters(ratio_value)
    if primary_parameters is None:
        raise ValueError("Unable to recover parameters for the chosen heat-capacity ratio.")

    a_value = primary_parameters["a"]
    b_value = primary_parameters["b"]
    c_value = primary_parameters["c"]
    hotspot_rise_initial = primary_parameters["hotspot_rise"]
    denominators = primary_parameters["denominators"]
    resistance_ratio = primary_parameters["resistance_ratio"]
    hotspot_temperature = ambient + hotspot_rise_initial

    sensor_model = [
        ambient + b1 * exponent + b2 * exponent_alt
        for exponent, exponent_alt in zip(exponent_1, exponent_2)
    ]
    hotspot_model = []
    for t_value in times_rel:
        hotspot_offset = 0.0
        for lam, coeff, denom in zip(lambdas, coefficients, denominators):
            hotspot_offset += (a_value * coeff / denom) * math.exp(lam * t_value)
        hotspot_model.append(ambient + hotspot_offset)

    residuals = [predicted - actual for predicted, actual in zip(sensor_model, temps_list)]
    rmse = math.sqrt(
        sum(residual * residual for residual in residuals) / len(residuals)
    )

    time_constants = [-1.0 / lambda_1, -1.0 / lambda_2]

    sensitivity_results: List[Dict[str, float]] = []
    candidate_ratios = []
    if ratio_value > ratio_min_feasible * 1.01:
        candidate_ratios.append(max(ratio_min_feasible, ratio_value * 0.5))
    if ratio_value < ratio_max_feasible * 0.99:
        candidate_ratios.append(min(ratio_max_feasible, ratio_value * 1.5))
    for candidate in candidate_ratios:
        parameters_candidate = solve_parameters(candidate)
        if parameters_candidate is None:
            continue
        sensitivity_results.append(
            {
                "heat_capacity_ratio": float(candidate),
                "hotspot_temperature": float(ambient + parameters_candidate["hotspot_rise"]),
                "resistance_ratio": float(parameters_candidate["resistance_ratio"]),
            }
        )

    return {
        "hotspot_temperature": float(hotspot_temperature),
        "sensor_model": [float(value) for value in sensor_model],
        "hotspot_model": [float(value) for value in hotspot_model],
        "time_seconds": [float(value) for value in times_rel],
        "parameters": {
            "lambda_1": float(lambda_1),
            "lambda_2": float(lambda_2),
            "a": float(a_value),
            "b": float(b_value),
            "c": float(c_value),
            "time_constant_fast": float(time_constants[0]),
            "time_constant_slow": float(time_constants[1]),
            "heat_capacity_ratio": float(ratio_value),
            "resistance_ratio": float(resistance_ratio),
        },
        "ratio_limits": {
            "minimum": float(ratio_min_feasible),
            "maximum": float(ratio_max_feasible),
        },
        "fit_metrics": {
            "rmse": float(rmse),
            "residuals": [float(value) for value in residuals],
        },
        "sensitivity": sensitivity_results,
        "sensor_initial_temperature": float(temps_list[0]),
        "ambient_temperature": float(ambient),
        "model_mode": "first_order_fallback" if fallback_context is not None else "two_mode_fit",
    }
