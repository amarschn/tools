"""
Heatsink analysis helpers for air-cooled plate-fin heatsinks.

This module provides a first-principles, steady-state analysis workflow for
straight plate-fin heatsinks. The implementation is intended for early design
work and education: it keeps the governing equations explicit, exposes the
important intermediate quantities, and returns substituted-equation strings for
progressive disclosure in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List


SIGMA = 5.670374419e-8
GRAVITY = 9.80665
AIR_GAS_CONSTANT = 287.058


@dataclass(frozen=True)
class AirProperties:
    """Thermophysical properties of air evaluated at a film temperature."""

    density: float
    dynamic_viscosity: float
    thermal_conductivity: float
    specific_heat: float
    kinematic_viscosity: float
    thermal_diffusivity: float
    prandtl: float
    thermal_expansion: float


@dataclass(frozen=True)
class PlateFinGeometry:
    """Derived geometry for a straight plate-fin heatsink."""

    base_length: float
    base_width: float
    base_thickness: float
    fin_height: float
    fin_thickness: float
    fin_count: int
    channel_count: int
    fin_spacing: float
    hydraulic_diameter: float
    exposed_base_area: float
    fin_area: float
    total_area: float
    open_flow_area: float
    frontal_area: float
    open_area_ratio: float
    volume: float


HEATSINK_MATERIALS: Dict[str, Dict[str, float | str]] = {
    "aluminum_6063_t5": {
        "label": "Aluminum 6063-T5",
        "thermal_conductivity": 201.0,
        "emissivity": 0.10,
    },
    "aluminum_6061_t6": {
        "label": "Aluminum 6061-T6",
        "thermal_conductivity": 167.0,
        "emissivity": 0.10,
    },
    "copper_c110": {
        "label": "Copper C110",
        "thermal_conductivity": 385.0,
        "emissivity": 0.05,
    },
    "black_anodized_aluminum": {
        "label": "Black Anodized Aluminum",
        "thermal_conductivity": 201.0,
        "emissivity": 0.85,
    },
}


def get_heatsink_materials() -> Dict[str, Dict[str, float | str]]:
    """Return the material/finish presets used by the heatsink tool."""

    return HEATSINK_MATERIALS


def air_properties(temperature_c: float, pressure_pa: float = 101325.0) -> AirProperties:
    """
    Estimate air properties near atmospheric pressure.

    The correlations are smooth engineering fits suitable for early heatsink
    design work, not a replacement for a full property package.
    """

    temperature_k = temperature_c + 273.15
    if temperature_k <= 0.0:
        raise ValueError("Temperature must be greater than absolute zero.")
    if pressure_pa <= 0.0:
        raise ValueError("Pressure must be greater than zero.")

    # Sutherland-law viscosity fit.
    dynamic_viscosity = (
        1.716e-5
        * (temperature_k / 273.15) ** 1.5
        * (273.15 + 110.4)
        / (temperature_k + 110.4)
    )
    density = pressure_pa / (AIR_GAS_CONSTANT * temperature_k)

    # Compact fits around room-temperature air.
    thermal_conductivity = 0.0241 * (temperature_k / 273.15) ** 0.9
    specific_heat = 1006.0 + 0.1 * (temperature_k - 300.0)

    kinematic_viscosity = dynamic_viscosity / density
    thermal_diffusivity = thermal_conductivity / (density * specific_heat)
    prandtl = dynamic_viscosity * specific_heat / thermal_conductivity

    return AirProperties(
        density=density,
        dynamic_viscosity=dynamic_viscosity,
        thermal_conductivity=thermal_conductivity,
        specific_heat=specific_heat,
        kinematic_viscosity=kinematic_viscosity,
        thermal_diffusivity=thermal_diffusivity,
        prandtl=prandtl,
        thermal_expansion=1.0 / temperature_k,
    )


def calculate_plate_fin_geometry(
    base_length: float,
    base_width: float,
    base_thickness: float,
    fin_height: float,
    fin_thickness: float,
    fin_count: int,
) -> PlateFinGeometry:
    """Return derived dimensions and areas for a plate-fin heatsink."""

    values = {
        "base_length": base_length,
        "base_width": base_width,
        "base_thickness": base_thickness,
        "fin_height": fin_height,
        "fin_thickness": fin_thickness,
    }
    for name, value in values.items():
        if value <= 0.0:
            raise ValueError(f"{name} must be greater than zero.")
    if fin_count < 2:
        raise ValueError("fin_count must be at least 2.")
    if base_width <= fin_count * fin_thickness:
        raise ValueError("Base width is too small for the requested fin count and thickness.")

    channel_count = fin_count - 1
    fin_spacing = (base_width - fin_count * fin_thickness) / channel_count
    if fin_spacing <= 0.0:
        raise ValueError("Computed fin spacing must be greater than zero.")

    hydraulic_diameter = 2.0 * fin_spacing * fin_height / (fin_spacing + fin_height)
    exposed_base_area = channel_count * fin_spacing * base_length
    fin_area = fin_count * (2.0 * fin_height * base_length + fin_thickness * base_length)
    total_area = exposed_base_area + fin_area
    open_flow_area = channel_count * fin_spacing * fin_height
    frontal_area = base_width * fin_height
    open_area_ratio = open_flow_area / frontal_area
    volume = (
        base_length * base_width * base_thickness
        + fin_count * base_length * fin_height * fin_thickness
    )

    return PlateFinGeometry(
        base_length=base_length,
        base_width=base_width,
        base_thickness=base_thickness,
        fin_height=fin_height,
        fin_thickness=fin_thickness,
        fin_count=fin_count,
        channel_count=channel_count,
        fin_spacing=fin_spacing,
        hydraulic_diameter=hydraulic_diameter,
        exposed_base_area=exposed_base_area,
        fin_area=fin_area,
        total_area=total_area,
        open_flow_area=open_flow_area,
        frontal_area=frontal_area,
        open_area_ratio=open_area_ratio,
        volume=volume,
    )


def linearized_radiation_coefficient(
    emissivity: float,
    surface_temperature_c: float,
    ambient_temperature_c: float,
) -> float:
    """Return a linearized radiation coefficient in W/m^2-K."""

    if not 0.0 < emissivity <= 1.0:
        raise ValueError("emissivity must be in the range (0, 1].")

    surface_temperature_k = surface_temperature_c + 273.15
    ambient_temperature_k = ambient_temperature_c + 273.15
    return emissivity * SIGMA * (
        surface_temperature_k**2 + ambient_temperature_k**2
    ) * (surface_temperature_k + ambient_temperature_k)


def rectangular_fin_efficiency(
    fin_height: float,
    fin_thickness: float,
    fin_length: float,
    heat_transfer_coefficient: float,
    thermal_conductivity: float,
) -> float:
    """Return straight rectangular-fin efficiency with a corrected tip length."""

    if fin_height <= 0.0 or fin_thickness <= 0.0 or fin_length <= 0.0:
        raise ValueError("Fin dimensions must be greater than zero.")
    if heat_transfer_coefficient < 0.0:
        raise ValueError("Heat transfer coefficient cannot be negative.")
    if thermal_conductivity <= 0.0:
        raise ValueError("thermal_conductivity must be greater than zero.")
    if heat_transfer_coefficient == 0.0:
        return 1.0

    cross_section_area = fin_thickness * fin_length
    wetted_perimeter = 2.0 * (fin_length + fin_thickness)
    corrected_length = fin_height + fin_thickness / 2.0
    m_value = math.sqrt(
        heat_transfer_coefficient * wetted_perimeter / (thermal_conductivity * cross_section_area)
    )
    m_length = m_value * corrected_length
    if m_length == 0.0:
        return 1.0
    return math.tanh(m_length) / m_length


def overall_surface_efficiency(
    fin_efficiency: float,
    fin_area: float,
    total_area: float,
) -> float:
    """Return overall surface efficiency for a finned surface."""

    if total_area <= 0.0:
        raise ValueError("total_area must be greater than zero.")
    if fin_area < 0.0:
        raise ValueError("fin_area cannot be negative.")
    return 1.0 - (fin_area / total_area) * (1.0 - fin_efficiency)


def required_sink_thermal_resistance(
    heat_load: float,
    ambient_temperature: float,
    target_junction_temperature: float,
    interface_resistance: float = 0.0,
    junction_to_case_resistance: float = 0.0,
) -> float:
    """
    Compute the sink-to-ambient thermal resistance budget from the full thermal stack.
    """

    if heat_load <= 0.0:
        raise ValueError("heat_load must be greater than zero.")
    if interface_resistance < 0.0 or junction_to_case_resistance < 0.0:
        raise ValueError("Thermal resistances cannot be negative.")
    available_rise = target_junction_temperature - ambient_temperature
    return available_rise / heat_load - interface_resistance - junction_to_case_resistance


def natural_convection_plate_array(
    geometry: PlateFinGeometry,
    surface_temperature: float,
    ambient_temperature: float,
    pressure_pa: float = 101325.0,
) -> Dict[str, float]:
    """
    Estimate natural-convection performance for a vertical plate array.

    Uses the Bar-Cohen/Rohsenow composite isothermal parallel-plate relation.
    """

    delta_t = surface_temperature - ambient_temperature
    if delta_t <= 0.0:
        return {
            "convection_coefficient": 0.0,
            "nusselt_number": 0.0,
            "rayleigh_modified": 0.0,
            "reynolds_number": 0.0,
            "channel_velocity": 0.0,
            "volumetric_flow_rate": 0.0,
            "pressure_drop": 0.0,
        }

    film_temperature = 0.5 * (surface_temperature + ambient_temperature)
    props = air_properties(film_temperature, pressure_pa=pressure_pa)
    rayleigh_modified = (
        GRAVITY
        * props.thermal_expansion
        * delta_t
        * geometry.fin_spacing**4
        / (props.kinematic_viscosity * props.thermal_diffusivity * geometry.fin_height)
    )
    rayleigh_modified = max(rayleigh_modified, 1e-12)
    nusselt_number = (
        576.0 / rayleigh_modified**2 + 2.873 / math.sqrt(rayleigh_modified)
    ) ** -0.5
    convection_coefficient = (
        nusselt_number * props.thermal_conductivity / geometry.fin_spacing
    )

    return {
        "convection_coefficient": max(convection_coefficient, 0.0),
        "nusselt_number": nusselt_number,
        "rayleigh_modified": rayleigh_modified,
        "reynolds_number": 0.0,
        "channel_velocity": 0.0,
        "volumetric_flow_rate": 0.0,
        "pressure_drop": 0.0,
    }


def _laminar_rectangular_duct_friction_factor(reynolds_number: float, aspect_ratio: float) -> float:
    """Return the Darcy friction factor for fully developed laminar flow in a rectangular duct."""

    if reynolds_number <= 0.0:
        return 0.0
    beta = min(max(aspect_ratio, 1e-6), 1.0)
    poisson_term = 24.0 * (
        1.0
        - 1.3553 * beta
        + 1.9467 * beta**2
        - 1.7012 * beta**3
        + 0.9564 * beta**4
        - 0.2537 * beta**5
    )
    return poisson_term / reynolds_number


def forced_convection_plate_array(
    geometry: PlateFinGeometry,
    surface_temperature: float,
    ambient_temperature: float,
    volumetric_flow_rate: float,
    pressure_pa: float = 101325.0,
) -> Dict[str, float]:
    """
    Estimate forced-convection performance and pressure drop for the fin channels.
    """

    if volumetric_flow_rate < 0.0:
        raise ValueError("volumetric_flow_rate cannot be negative.")
    if volumetric_flow_rate == 0.0:
        return {
            "convection_coefficient": 0.0,
            "nusselt_number": 0.0,
            "reynolds_number": 0.0,
            "channel_velocity": 0.0,
            "volumetric_flow_rate": 0.0,
            "pressure_drop": 0.0,
        }

    film_temperature = 0.5 * (surface_temperature + ambient_temperature)
    props = air_properties(film_temperature, pressure_pa=pressure_pa)
    channel_velocity = volumetric_flow_rate / geometry.open_flow_area
    reynolds_number = (
        props.density * channel_velocity * geometry.hydraulic_diameter / props.dynamic_viscosity
    )
    graetz_number = (
        reynolds_number
        * props.prandtl
        * geometry.hydraulic_diameter
        / geometry.base_length
    )

    if reynolds_number < 2300.0:
        nusselt_number = (
            7.54**3 + (1.841 * graetz_number ** (1.0 / 3.0)) ** 3
        ) ** (1.0 / 3.0)
        darcy_friction_factor = _laminar_rectangular_duct_friction_factor(
            reynolds_number, geometry.fin_spacing / geometry.fin_height
        )
    else:
        darcy_friction_factor = 0.3164 * reynolds_number ** -0.25
        friction_term = (0.79 * math.log(reynolds_number) - 1.64) ** -2
        nusselt_number = (
            (friction_term / 8.0)
            * (reynolds_number - 1000.0)
            * props.prandtl
            / (
                1.0
                + 12.7 * math.sqrt(friction_term / 8.0) * (props.prandtl ** (2.0 / 3.0) - 1.0)
            )
        )

    sigma = geometry.open_area_ratio
    contraction_loss = 0.42 * (1.0 - sigma**2)
    expansion_loss = (1.0 - sigma) ** 2
    pressure_drop = (
        darcy_friction_factor * geometry.base_length / geometry.hydraulic_diameter
        + contraction_loss
        + expansion_loss
    ) * 0.5 * props.density * channel_velocity**2

    convection_coefficient = (
        nusselt_number * props.thermal_conductivity / geometry.hydraulic_diameter
    )
    return {
        "convection_coefficient": convection_coefficient,
        "nusselt_number": nusselt_number,
        "reynolds_number": reynolds_number,
        "channel_velocity": channel_velocity,
        "volumetric_flow_rate": volumetric_flow_rate,
        "pressure_drop": pressure_drop,
    }


def fan_curve_pressure(
    volumetric_flow_rate: float,
    fan_max_pressure: float,
    fan_max_flow_rate: float,
) -> float:
    """Simple parabolic fan model spanning free-delivery to shutoff pressure."""

    if fan_max_pressure < 0.0 or fan_max_flow_rate <= 0.0:
        raise ValueError("Fan curve limits must be positive.")
    ratio = min(max(volumetric_flow_rate / fan_max_flow_rate, 0.0), 1.0)
    return fan_max_pressure * (1.0 - ratio**2)


def solve_fan_operating_point(
    geometry: PlateFinGeometry,
    surface_temperature: float,
    ambient_temperature: float,
    fan_max_pressure: float,
    fan_max_flow_rate: float,
    pressure_pa: float = 101325.0,
) -> Dict[str, float]:
    """
    Solve the fan/heatsink operating point by intersecting the fan and system curves.
    """

    if fan_max_pressure < 0.0:
        raise ValueError("fan_max_pressure cannot be negative.")
    if fan_max_flow_rate <= 0.0:
        raise ValueError("fan_max_flow_rate must be greater than zero.")

    lower_flow = 0.0
    upper_flow = fan_max_flow_rate
    for _ in range(60):
        mid_flow = 0.5 * (lower_flow + upper_flow)
        fan_pressure = fan_curve_pressure(mid_flow, fan_max_pressure, fan_max_flow_rate)
        system_pressure = forced_convection_plate_array(
            geometry=geometry,
            surface_temperature=surface_temperature,
            ambient_temperature=ambient_temperature,
            volumetric_flow_rate=mid_flow,
            pressure_pa=pressure_pa,
        )["pressure_drop"]
        if fan_pressure > system_pressure:
            lower_flow = mid_flow
        else:
            upper_flow = mid_flow

    operating_flow = 0.5 * (lower_flow + upper_flow)
    forced_state = forced_convection_plate_array(
        geometry=geometry,
        surface_temperature=surface_temperature,
        ambient_temperature=ambient_temperature,
        volumetric_flow_rate=operating_flow,
        pressure_pa=pressure_pa,
    )
    forced_state["fan_pressure"] = fan_curve_pressure(
        operating_flow, fan_max_pressure, fan_max_flow_rate
    )
    return forced_state


def analyze_plate_fin_heatsink(
    heat_load: float,
    ambient_temperature: float,
    target_junction_temperature: float,
    base_length: float,
    base_width: float,
    base_thickness: float,
    fin_height: float,
    fin_thickness: float,
    fin_count: int,
    material_conductivity: float,
    surface_emissivity: float = 0.85,
    airflow_mode: str = "natural",
    approach_velocity: float = 0.0,
    volumetric_flow_rate: float = 0.0,
    fan_max_pressure: float = 0.0,
    fan_max_flow_rate: float = 0.0,
    interface_resistance: float = 0.0,
    junction_to_case_resistance: float = 0.0,
    pressure_pa: float = 101325.0,
) -> Dict[str, Any]:
    r"""
    Analyze the steady-state performance of a straight plate-fin heatsink in air.

    The solver assumes a uniform base temperature and models the heatsink as a
    finned isothermal surface rejecting heat by convection and radiation. For
    natural convection it uses a vertical parallel-plate correlation. For
    forced flow it models the fin channels as rectangular ducts with a
    developing-flow heat-transfer approximation and a Darcy-style pressure-drop
    estimate. When a fan curve is supplied, the operating point is determined
    by intersecting the fan curve with the sink pressure-drop curve.

    The variable names retain the common electronics notation ``j`` and
    ``Rθjc``, but the upper thermal node can be interpreted more generally as
    the hottest internal source temperature of the mounted part.

    ---Parameters---
    heat_load : float
        Heat that must be rejected to ambient in watts (W).
    ambient_temperature : float
        Ambient air temperature in degrees Celsius (°C).
    target_junction_temperature : float
        Maximum allowable upper source-node temperature in degrees Celsius (°C).
        In electronics this is often the junction temperature limit.
    base_length : float
        Heatsink length in the primary flow direction in metres (m).
    base_width : float
        Total heatsink width across the fin array in metres (m).
    base_thickness : float
        Thickness of the heatsink base in metres (m).
    fin_height : float
        Height of each straight fin above the base in metres (m).
    fin_thickness : float
        Thickness of each fin in metres (m).
    fin_count : int
        Number of straight fins in the array.
    material_conductivity : float
        Thermal conductivity of the heatsink material in W/m·K.
    surface_emissivity : float
        Surface emissivity of the exposed heatsink in the range (0, 1].
    airflow_mode : str
        One of ``natural``, ``forced``, or ``fan_curve``.
    approach_velocity : float
        Approach velocity through the heatsink frontal area in m/s. Used only
        for ``forced`` mode when ``volumetric_flow_rate`` is zero.
    volumetric_flow_rate : float
        Volumetric airflow through the fin channels in m^3/s. Used in
        ``forced`` mode when greater than zero.
    fan_max_pressure : float
        Fan shutoff pressure in pascals (Pa) for ``fan_curve`` mode.
    fan_max_flow_rate : float
        Fan free-delivery flow rate in m^3/s for ``fan_curve`` mode.
    interface_resistance : float
        Thermal resistance from the outer mounting surface to the sink base in K/W.
    junction_to_case_resistance : float
        Thermal resistance from the internal source node to the outer mounting
        surface in K/W. In electronics this is often called junction-to-case
        resistance.
    pressure_pa : float
        Ambient pressure in pascals (Pa), used for air properties.

    ---Returns---
    required_sink_thermal_resistance : float
        Maximum allowed sink-to-ambient thermal resistance in K/W after
        subtracting upstream interface resistances.
    sink_thermal_resistance : float
        Predicted sink-to-ambient thermal resistance in K/W.
    base_temperature : float
        Predicted average heatsink base temperature in degrees Celsius (°C).
    case_temperature : float
        Predicted outer mounting-surface temperature in degrees Celsius (°C).
    junction_temperature : float
        Predicted upper source-node temperature in degrees Celsius (°C).
    temperature_margin : float
        Remaining temperature margin to the target source-node limit in degrees Celsius (°C).
    total_surface_area : float
        Total exposed heatsink area in square metres (m^2).
    fin_spacing : float
        Clear spacing between fins in metres (m).
    hydraulic_diameter : float
        Hydraulic diameter of one fin channel in metres (m).
    channel_velocity : float
        Mean air velocity inside the fin channels in m/s.
    volumetric_flow_rate : float
        Effective airflow through the heatsink channels in m^3/s.
    pressure_drop : float
        Estimated pressure drop through the heatsink in pascals (Pa).
    reynolds_number : float
        Channel Reynolds number based on hydraulic diameter.
    nusselt_number : float
        Average Nusselt number for the active convection model.
    convection_coefficient : float
        Convective heat-transfer coefficient in W/m^2·K.
    radiation_coefficient : float
        Linearized radiation coefficient in W/m^2·K.
    fin_efficiency : float
        Single-fin efficiency for the straight rectangular fins.
    overall_surface_efficiency : float
        Overall surface efficiency accounting for fin efficiency and base area.
    convection_heat_rejected : float
        Portion of total rejected heat associated with convection in watts (W).
    radiation_heat_rejected : float
        Portion of total rejected heat associated with radiation in watts (W).
    heat_rejected : float
        Total rejected heat in watts (W). This should balance ``heat_load``.
    convection_mode_used : str
        Resolved convection mode actually used in the analysis.
    status : str
        ``acceptable``, ``marginal``, or ``unacceptable`` based on source-node margin.
    recommendations : list
        Plain-language recommendations derived from the result.
    subst_required_sink_thermal_resistance : str
        Substituted thermal-budget equation for ``required_sink_thermal_resistance``.
    subst_sink_thermal_resistance : str
        Substituted resistance equation for ``sink_thermal_resistance``.
    subst_junction_temperature : str
        Substituted thermal-stack equation for ``junction_temperature``.
    subst_fin_efficiency : str
        Substituted fin-efficiency equation for ``fin_efficiency``.
    subst_pressure_drop : str
        Substituted channel pressure-drop equation for ``pressure_drop``.

    ---LaTeX---
    R_{\theta,\text{req,sink}} = \frac{T_{j,\max} - T_{\infty}}{Q} - R_{\theta,jc} - R_{\theta,cs} \\
    R_{\theta,\text{sink}} = \frac{T_b - T_{\infty}}{Q} \\
    \eta_f = \frac{\tanh(m L_c)}{m L_c}, \quad
    m = \sqrt{\frac{h_{\text{eff}} P}{k A_c}}, \quad
    \eta_o = 1 - \frac{A_f}{A_t}(1-\eta_f) \\
    Q = \eta_o \, h_{\text{eff}} \, A_t \, (T_b - T_{\infty}), \quad
    h_{\text{eff}} = h_{\text{conv}} + h_{\text{rad}} \\
    \Delta P = \left(f\frac{L}{D_h} + K_c + K_e\right)\frac{\rho V_{ch}^2}{2}

    ---References---
    Bar-Cohen, A., Rohsenow, W. M. (1984). Thermally Optimum Spacing of
        Vertical, Natural Convection Cooled, Parallel Plates.
        Journal of Heat Transfer. https://doi.org/10.1115/1.3246622
    Muzychka, Y. S., Yovanovich, M. M. (2004). Laminar Forced Convection Heat
        Transfer in the Combined Entry Region of Non-Circular Ducts.
        Journal of Heat Transfer. https://doi.org/10.1115/1.1643752
    Simons, R. E. (2003). Estimating Parallel Plate-fin Heat Sink Pressure Drop.
        Electronics Cooling.
    Incropera, F. P., DeWitt, D. P., Bergman, T. L., Lavine, A. S.
        Fundamentals of Heat and Mass Transfer.
    """

    if heat_load <= 0.0:
        raise ValueError("heat_load must be greater than zero.")
    if material_conductivity <= 0.0:
        raise ValueError("material_conductivity must be greater than zero.")
    if interface_resistance < 0.0 or junction_to_case_resistance < 0.0:
        raise ValueError("Thermal resistances cannot be negative.")
    if airflow_mode not in {"natural", "forced", "fan_curve"}:
        raise ValueError("airflow_mode must be one of 'natural', 'forced', or 'fan_curve'.")

    geometry = calculate_plate_fin_geometry(
        base_length=base_length,
        base_width=base_width,
        base_thickness=base_thickness,
        fin_height=fin_height,
        fin_thickness=fin_thickness,
        fin_count=fin_count,
    )
    required_r_sink = required_sink_thermal_resistance(
        heat_load=heat_load,
        ambient_temperature=ambient_temperature,
        target_junction_temperature=target_junction_temperature,
        interface_resistance=interface_resistance,
        junction_to_case_resistance=junction_to_case_resistance,
    )

    def resolve_flow(surface_temperature: float) -> Dict[str, float]:
        if airflow_mode == "natural":
            state = natural_convection_plate_array(
                geometry=geometry,
                surface_temperature=surface_temperature,
                ambient_temperature=ambient_temperature,
                pressure_pa=pressure_pa,
            )
            state["convection_mode_used"] = "natural"
            return state

        if airflow_mode == "forced":
            if volumetric_flow_rate > 0.0:
                flow_rate = volumetric_flow_rate
            else:
                flow_rate = max(approach_velocity, 0.0) * geometry.frontal_area
            state = forced_convection_plate_array(
                geometry=geometry,
                surface_temperature=surface_temperature,
                ambient_temperature=ambient_temperature,
                volumetric_flow_rate=flow_rate,
                pressure_pa=pressure_pa,
            )
            state["convection_mode_used"] = "forced"
            return state

        state = solve_fan_operating_point(
            geometry=geometry,
            surface_temperature=surface_temperature,
            ambient_temperature=ambient_temperature,
            fan_max_pressure=fan_max_pressure,
            fan_max_flow_rate=fan_max_flow_rate,
            pressure_pa=pressure_pa,
        )
        state["convection_mode_used"] = "fan_curve"
        return state

    def evaluate_balance(surface_temperature: float) -> Dict[str, Any]:
        flow_state = resolve_flow(surface_temperature)
        radiation_coefficient = linearized_radiation_coefficient(
            emissivity=surface_emissivity,
            surface_temperature_c=surface_temperature,
            ambient_temperature_c=ambient_temperature,
        )
        effective_coefficient = flow_state["convection_coefficient"] + radiation_coefficient
        fin_efficiency = rectangular_fin_efficiency(
            fin_height=geometry.fin_height,
            fin_thickness=geometry.fin_thickness,
            fin_length=geometry.base_length,
            heat_transfer_coefficient=effective_coefficient,
            thermal_conductivity=material_conductivity,
        )
        overall_efficiency = overall_surface_efficiency(
            fin_efficiency=fin_efficiency,
            fin_area=geometry.fin_area,
            total_area=geometry.total_area,
        )
        temperature_rise = surface_temperature - ambient_temperature
        heat_rejected = overall_efficiency * effective_coefficient * geometry.total_area * temperature_rise
        convection_heat = (
            overall_efficiency
            * flow_state["convection_coefficient"]
            * geometry.total_area
            * temperature_rise
        )
        radiation_heat = (
            overall_efficiency
            * radiation_coefficient
            * geometry.total_area
            * temperature_rise
        )
        return {
            "flow_state": flow_state,
            "radiation_coefficient": radiation_coefficient,
            "fin_efficiency": fin_efficiency,
            "overall_efficiency": overall_efficiency,
            "heat_rejected": heat_rejected,
            "convection_heat": convection_heat,
            "radiation_heat": radiation_heat,
        }

    lower_temperature = ambient_temperature + 1e-6
    upper_temperature = ambient_temperature + 60.0
    upper_state = evaluate_balance(upper_temperature)
    while upper_state["heat_rejected"] < heat_load and upper_temperature < ambient_temperature + 800.0:
        upper_temperature += 40.0
        upper_state = evaluate_balance(upper_temperature)
    if upper_state["heat_rejected"] < heat_load:
        raise ValueError("Requested heat load exceeds modeled heatsink capability below 800 C.")

    lower_state = evaluate_balance(lower_temperature)
    for _ in range(70):
        mid_temperature = 0.5 * (lower_temperature + upper_temperature)
        mid_state = evaluate_balance(mid_temperature)
        if mid_state["heat_rejected"] >= heat_load:
            upper_temperature = mid_temperature
            upper_state = mid_state
        else:
            lower_temperature = mid_temperature
            lower_state = mid_state

    base_temperature = upper_temperature
    final_state = upper_state
    sink_r_theta = (base_temperature - ambient_temperature) / heat_load
    case_temperature = base_temperature + heat_load * interface_resistance
    junction_temperature = case_temperature + heat_load * junction_to_case_resistance
    temperature_margin = target_junction_temperature - junction_temperature

    if temperature_margin >= 5.0:
        status = "acceptable"
    elif temperature_margin >= 0.0:
        status = "marginal"
    else:
        status = "unacceptable"

    recommendations: List[str] = []
    if required_r_sink <= 0.0:
        recommendations.append(
            "Upstream source-to-case and interface resistances consume the full thermal budget."
        )
    if temperature_margin < 0.0:
        recommendations.append("Reduce heat load or increase heatsink surface area and airflow.")
    if final_state["fin_efficiency"] < 0.7:
        recommendations.append("Fin efficiency is low; consider shorter fins, thicker fins, or higher conductivity material.")
    if airflow_mode in {"forced", "fan_curve"} and final_state["flow_state"]["pressure_drop"] > 75.0:
        recommendations.append("Pressure drop is high relative to small axial fans; reduce fin density or shorten the flow length.")
    if final_state["radiation_heat"] > 0.15 * heat_load:
        recommendations.append("Radiation is materially helping; a high-emissivity finish is beneficial for this design.")
    if not recommendations:
        recommendations.append("Thermal budget is met with reasonable margin under the modeled assumptions.")

    flow_state = final_state["flow_state"]
    effective_coefficient = flow_state["convection_coefficient"] + final_state["radiation_coefficient"]
    cross_section_area = geometry.fin_thickness * geometry.base_length
    wetted_perimeter = 2.0 * (geometry.base_length + geometry.fin_thickness)
    corrected_length = geometry.fin_height + geometry.fin_thickness / 2.0
    m_length = math.sqrt(
        effective_coefficient * wetted_perimeter / (material_conductivity * cross_section_area)
    ) * corrected_length
    result = {
        "required_sink_thermal_resistance": required_r_sink,
        "sink_thermal_resistance": sink_r_theta,
        "base_temperature": base_temperature,
        "case_temperature": case_temperature,
        "junction_temperature": junction_temperature,
        "temperature_margin": temperature_margin,
        "total_surface_area": geometry.total_area,
        "fin_spacing": geometry.fin_spacing,
        "hydraulic_diameter": geometry.hydraulic_diameter,
        "channel_velocity": flow_state["channel_velocity"],
        "volumetric_flow_rate": flow_state["volumetric_flow_rate"],
        "pressure_drop": flow_state["pressure_drop"],
        "reynolds_number": flow_state["reynolds_number"],
        "nusselt_number": flow_state["nusselt_number"],
        "convection_coefficient": flow_state["convection_coefficient"],
        "radiation_coefficient": final_state["radiation_coefficient"],
        "fin_efficiency": final_state["fin_efficiency"],
        "overall_surface_efficiency": final_state["overall_efficiency"],
        "convection_heat_rejected": final_state["convection_heat"],
        "radiation_heat_rejected": final_state["radiation_heat"],
        "heat_rejected": final_state["heat_rejected"],
        "convection_mode_used": flow_state["convection_mode_used"],
        "status": status,
        "recommendations": recommendations,
    }
    result["subst_required_sink_thermal_resistance"] = (
        "R_{\\theta,\\mathrm{req,sink}} = "
        f"\\frac{{{target_junction_temperature:.2f} - {ambient_temperature:.2f}}}{{{heat_load:.3f}}}"
        f" - {junction_to_case_resistance:.4f} - {interface_resistance:.4f}"
        f" = {required_r_sink:.4f}\\,\\mathrm{{K/W}}"
    )
    result["subst_sink_thermal_resistance"] = (
        "R_{\\theta,\\mathrm{sink}} = "
        f"\\frac{{{base_temperature:.2f} - {ambient_temperature:.2f}}}{{{heat_load:.3f}}}"
        f" = {sink_r_theta:.4f}\\,\\mathrm{{K/W}}"
    )
    result["subst_junction_temperature"] = (
        f"T_j = {base_temperature:.2f} + {heat_load:.3f}"
        f"\\left({interface_resistance:.4f} + {junction_to_case_resistance:.4f}\\right)"
        f" = {junction_temperature:.2f}\\,^\\circ\\mathrm{{C}}"
    )
    result["subst_fin_efficiency"] = (
        "\\eta_f = \\frac{\\tanh(mL_c)}{mL_c},\\;"
        f"mL_c = \\sqrt{{\\frac{{{effective_coefficient:.3f} \\times {wetted_perimeter:.6f}}}"
        f"{{{material_conductivity:.1f} \\times {cross_section_area:.6f}}}}}"
        f" \\times {corrected_length:.6f}"
        f" = {m_length:.4f}"
        f",\\; \\eta_f = {final_state['fin_efficiency']:.4f}"
    )
    result["subst_pressure_drop"] = (
        "\\Delta P = \\left(f\\frac{L}{D_h} + K_c + K_e\\right)\\frac{\\rho V_{ch}^2}{2}"
        f" = {flow_state['pressure_drop']:.2f}\\,\\mathrm{{Pa}}"
    )
    return result
