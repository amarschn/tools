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

    # Sutherland-type thermal conductivity fit for air.
    # Matches NIST data within 1.5% from 200 K to 700 K.
    thermal_conductivity = (
        0.02414
        * (temperature_k / 273.15) ** 1.5
        * (273.15 + 194.0)
        / (temperature_k + 194.0)
    )
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


def fin_channel_radiation_view_factor(fin_height: float, fin_spacing: float) -> float:
    """
    Effective radiation view factor for a fin channel to the environment.

    For closely spaced fins, most radiation leaving one fin surface strikes
    the adjacent fin (at nearly the same temperature), reducing net radiation
    to ambient. The model treats the channel as two parallel plates of height
    H separated by gap s, open at top and bottom:

        F_eff = s / (s + H)

    Approaches 1 for wide spacing, 0 for deep channels.

    ---References---
    Sparrow, E. M., Cess, R. D. (1978). Radiation Heat Transfer.
    Siegel, R., Howell, J. R. (2002). Thermal Radiation Heat Transfer.
    """
    if fin_height <= 0.0 or fin_spacing <= 0.0:
        return 1.0
    return fin_spacing / (fin_spacing + fin_height)


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

    # Estimate induced channel velocity from chimney-flow energy balance.
    # Q_conv ≈ rho * cp * V * A_channel * dT_air, with dT_air ≈ 0.5 * delta_t.
    air_rise_estimate = max(delta_t * 0.5, 1.0)
    if geometry.open_flow_area > 0:
        channel_velocity_estimate = (
            convection_coefficient
            * geometry.fin_spacing
            * geometry.fin_height
            * delta_t
            / (props.density * props.specific_heat * geometry.open_flow_area * air_rise_estimate)
        )
    else:
        channel_velocity_estimate = 0.0
    channel_velocity_estimate = min(max(channel_velocity_estimate, 0.0), 2.0)
    volumetric_flow_estimate = channel_velocity_estimate * geometry.open_flow_area

    return {
        "convection_coefficient": max(convection_coefficient, 0.0),
        "nusselt_number": nusselt_number,
        "rayleigh_modified": rayleigh_modified,
        "reynolds_number": 0.0,
        "channel_velocity": channel_velocity_estimate,
        "volumetric_flow_rate": volumetric_flow_estimate,
        "pressure_drop": 0.0,
    }


def rectangular_spreading_resistance(
    source_length: float,
    source_width: float,
    base_length: float,
    base_width: float,
    base_thickness: float,
    thermal_conductivity: float,
) -> float:
    """
    Estimate constriction/spreading resistance for a centered rectangular source
    on a rectangular plate.

    Uses the Yovanovich et al. dimensionless approach for a uniform-flux source
    with adiabatic edges:

        R_sp = psi / (k * sqrt(pi * A_s))

    where psi is a function of the relative source size epsilon = sqrt(A_s/A_p)
    and relative thickness tau = t / sqrt(A_p).

    Returns zero when the source footprint equals or exceeds the plate footprint.

    ---References---
    Yovanovich, M. M., Muzychka, Y. S., Culham, J. R. (1999).
        Spreading Resistance of Isoflux Rectangles and Strips on
        Compound Flux Channels.
    Lee, S., Song, S., Au, V., Moran, K. P. (1995).
        Constriction/Spreading Resistance Model for Electronics Packaging.
    """
    if source_length <= 0 or source_width <= 0:
        raise ValueError("Source dimensions must be positive.")
    if base_length <= 0 or base_width <= 0 or base_thickness <= 0:
        raise ValueError("Base dimensions must be positive.")
    if thermal_conductivity <= 0:
        raise ValueError("Thermal conductivity must be positive.")

    source_area = source_length * source_width
    plate_area = base_length * base_width

    if source_area >= plate_area:
        return 0.0

    epsilon = math.sqrt(source_area / plate_area)
    tau = base_thickness / math.sqrt(plate_area)
    psi = (1.0 - epsilon) ** 1.5 / (epsilon * tau + (1.0 - epsilon) ** 1.5)

    return psi / (thermal_conductivity * math.sqrt(math.pi * source_area))


def estimate_bypass_fraction(
    geometry: PlateFinGeometry,
) -> float:
    """
    Estimate the fraction of approach airflow that bypasses the fin array
    in an unducted configuration.

    Uses a first-order model based on fin aspect ratio:
        bypass_fraction approx 1 / (1 + K * sqrt(H/s))

    where K is an empirical constant (~0.5 for typical unducted heatsinks).

    ---References---
    Simons, R. E. (2004). Estimating the Effect of Flow Bypass on
        Parallel Plate-Fin Heat Sink Performance. Electronics Cooling.
    """
    if geometry.fin_spacing <= 0 or geometry.fin_height <= 0:
        return 0.0
    aspect = geometry.fin_height / geometry.fin_spacing
    k_bypass = 0.5
    # Throughput fraction = 1 / (1 + K*sqrt(H/s)); bypass = 1 - throughput.
    throughput = 1.0 / (1.0 + k_bypass * math.sqrt(max(aspect, 0.01)))
    return max(0.0, min(1.0 - throughput, 0.9))


def natural_convection_horizontal_plate_array(
    geometry: PlateFinGeometry,
    surface_temperature: float,
    ambient_temperature: float,
    facing: str = "up",
    pressure_pa: float = 101325.0,
) -> Dict[str, float]:
    """
    Estimate natural convection for a horizontal plate-fin array.

    For fins facing up (heated surface up), uses the McAdams correlation:
        Nu = 0.54 * Ra_L^0.25  (10^4 < Ra_L < 10^7, laminar)
        Nu = 0.15 * Ra_L^0.33  (10^7 < Ra_L < 10^11, turbulent)

    For fins facing down (heated surface down):
        Nu = 0.27 * Ra_L^0.25  (10^5 < Ra_L < 10^10)

    The characteristic length is L_c = A / P for the base footprint.

    ---References---
    McAdams, W. H. (1954). Heat Transmission, 3rd ed.
    Incropera et al. Fundamentals of Heat and Mass Transfer, Table 9.1.
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

    # Characteristic length for horizontal plate: A / P.
    char_length = (geometry.base_length * geometry.base_width) / (
        2.0 * (geometry.base_length + geometry.base_width)
    )
    rayleigh = (
        GRAVITY
        * props.thermal_expansion
        * delta_t
        * char_length ** 3
        / (props.kinematic_viscosity * props.thermal_diffusivity)
    )
    rayleigh = max(rayleigh, 1e-12)

    if facing == "up":
        if rayleigh < 1e7:
            nusselt_number = 0.54 * rayleigh ** 0.25
        else:
            nusselt_number = 0.15 * rayleigh ** (1.0 / 3.0)
    else:
        nusselt_number = 0.27 * rayleigh ** 0.25

    convection_coefficient = nusselt_number * props.thermal_conductivity / char_length

    return {
        "convection_coefficient": max(convection_coefficient, 0.0),
        "nusselt_number": nusselt_number,
        "rayleigh_modified": rayleigh,
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
        # Petukhov friction factor — used for both Nusselt and pressure drop
        # so that the Gnielinski correlation is self-consistent.
        darcy_friction_factor = (0.790 * math.log(reynolds_number) - 1.64) ** -2
        nusselt_number = (
            (darcy_friction_factor / 8.0)
            * (reynolds_number - 1000.0)
            * props.prandtl
            / (
                1.0
                + 12.7 * math.sqrt(darcy_friction_factor / 8.0) * (props.prandtl ** (2.0 / 3.0) - 1.0)
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
    fan_curve_points: list = None,
) -> float:
    """
    Fan pressure at a given flow rate.

    When fan_curve_points is provided (list of [flow, pressure] pairs with at
    least 2 entries), uses piecewise-linear interpolation. Otherwise falls back
    to the simple parabolic model: P = P_max * (1 - (Q/Q_max)^2).
    """
    if fan_curve_points and len(fan_curve_points) >= 2:
        points = sorted(fan_curve_points, key=lambda p: p[0])
        if volumetric_flow_rate <= points[0][0]:
            return points[0][1]
        if volumetric_flow_rate >= points[-1][0]:
            return max(points[-1][1], 0.0)
        for i in range(len(points) - 1):
            if points[i][0] <= volumetric_flow_rate <= points[i + 1][0]:
                frac = (
                    (volumetric_flow_rate - points[i][0])
                    / (points[i + 1][0] - points[i][0])
                )
                return points[i][1] + frac * (points[i + 1][1] - points[i][1])

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
    orientation: str = "vertical",
    source_length: float = 0.0,
    source_width: float = 0.0,
    ducted: bool = True,
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
        Total heat dissipated to air (W). Typical: 5–150 W for electronics, up to
        1 kW+ for industrial. Higher loads demand larger sinks or forced air.
    ambient_temperature : float
        Surrounding air temperature (°C). Typical: 25 °C bench, 40–55 °C inside
        enclosures. Higher ambient shrinks the available ΔT budget.
    target_junction_temperature : float
        Maximum allowable internal source temperature (°C). In electronics this is
        the junction limit from the datasheet. Typical: 85–125 °C for ICs, 150 °C
        for power devices. Lower limits require more aggressive cooling.
    base_length : float
        Heatsink length along the airflow direction (m). Typical: 30–200 mm. Longer
        sinks add fin area but also increase pressure drop and reduce convection
        effectiveness downstream.
    base_width : float
        Total width across the fin array (m). Typical: 30–200 mm. Wider sinks
        accept more fins and more airflow. High sensitivity — often the most
        effective dimension to increase.
    base_thickness : float
        Thickness of the base plate (m). Typical: 3–10 mm. Thicker bases spread
        heat better from small sources but add weight. Low sensitivity unless the
        source is much smaller than the base.
    fin_height : float
        Height of each fin above the base (m). Typical: 10–60 mm. Taller fins add
        area but efficiency drops as conduction path length grows.
    fin_thickness : float
        Thickness of each fin (m). Typical: 0.8–2.0 mm. Thicker fins conduct
        better but reduce channel spacing. Moderate sensitivity in natural
        convection, low in forced.
    fin_count : int
        Number of fins in the array. Typical: 5–40 depending on width. More fins
        add area but narrow the channels, increasing pressure drop and reducing
        natural-convection flow. High sensitivity — there is an optimum.
    material_conductivity : float
        Thermal conductivity of the heatsink material (W/m·K). Aluminium alloys:
        150–220, copper: 380–400, steel: 15–50. Higher conductivity improves fin
        efficiency and spreading.
    surface_emissivity : float
        Total hemispherical emissivity of exposed surfaces (0–1). Anodized Al:
        0.8–0.9, polished Al: 0.05–0.1, painted: 0.85–0.95. Affects radiation
        which can be 25–50% of heat transfer in natural convection.
    airflow_mode : str
        Cooling regime: "natural" = buoyancy-driven, "forced" = known air velocity
        or flow rate, "fan_curve" = fan operating point from curve intersection.
    approach_velocity : float
        Far-field air velocity upstream of the sink (m/s). Typical: 1–5 m/s.
        The model converts this to channel velocity using the open area ratio.
        Used only in forced mode when volumetric_flow_rate is zero.
    volumetric_flow_rate : float
        Measured airflow through the fin channels (m³/s). Typical: 0.001–0.01 m³/s.
        If nonzero, overrides approach_velocity. Used in forced mode.
    fan_max_pressure : float
        Fan static pressure at zero flow (Pa), from the fan datasheet. Typical: 20–
        200 Pa for small axial fans. Used in fan_curve mode.
    fan_max_flow_rate : float
        Fan free-delivery flow rate at zero back-pressure (m³/s). Typical: 0.002–
        0.02 m³/s for 40–120 mm fans. Used in fan_curve mode.
    interface_resistance : float
        Case-to-sink thermal resistance (K/W). Includes TIM, contact pressure,
        and surface finish effects. Typical: 0.05–0.5 K/W depending on TIM.
    junction_to_case_resistance : float
        Source-to-case thermal resistance (K/W). In electronics, from the IC
        junction to the package exterior. Typical: 0.1–2 K/W, from the
        device datasheet. Dominates the total resistance for low-power devices.
    pressure_pa : float
        Ambient air pressure (Pa). Default 101325 Pa (sea level). Lower pressure
        at altitude reduces air density and convection; e.g. ~80 kPa at 2000 m.
    orientation : str
        Heatsink mounting orientation. "vertical" = fins vertical with air rising
        upward, "horizontal_up" = fins pointing up, "horizontal_down" = fins
        pointing down. Affects natural convection correlation only.
    source_length : float
        Length of the heat source footprint (m). Set to 0 to assume full-base
        coverage. When smaller than the base, a spreading resistance penalty is
        computed via the Yovanovich model. Typical: device package size.
    source_width : float
        Width of the heat source footprint (m). Same conventions as source_length.
    ducted : bool
        True if a duct or shroud forces all air through the fins. False if
        unducted, where some airflow bypasses the fin array. Bypass reduces
        effective flow by ~25–50% depending on fin height-to-spacing ratio.

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
            if orientation == "vertical":
                state = natural_convection_plate_array(
                    geometry=geometry,
                    surface_temperature=surface_temperature,
                    ambient_temperature=ambient_temperature,
                    pressure_pa=pressure_pa,
                )
            elif orientation in ("horizontal_up", "horizontal_down"):
                facing = "up" if orientation == "horizontal_up" else "down"
                state = natural_convection_horizontal_plate_array(
                    geometry=geometry,
                    surface_temperature=surface_temperature,
                    ambient_temperature=ambient_temperature,
                    facing=facing,
                    pressure_pa=pressure_pa,
                )
            else:
                raise ValueError(
                    "orientation must be 'vertical', 'horizontal_up', or 'horizontal_down'."
                )
            state["convection_mode_used"] = f"natural_{orientation}"
            return state

        if airflow_mode == "forced":
            if volumetric_flow_rate > 0.0:
                flow_rate = volumetric_flow_rate
            else:
                flow_rate = max(approach_velocity, 0.0) * geometry.frontal_area
            if not ducted:
                bypass = estimate_bypass_fraction(geometry)
                flow_rate *= (1.0 - bypass)
            state = forced_convection_plate_array(
                geometry=geometry,
                surface_temperature=surface_temperature,
                ambient_temperature=ambient_temperature,
                volumetric_flow_rate=flow_rate,
                pressure_pa=pressure_pa,
            )
            state["convection_mode_used"] = "forced"
            if not ducted:
                state["bypass_fraction"] = bypass
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
        # Correct for fin-to-fin view factor.
        radiation_view_factor = fin_channel_radiation_view_factor(
            fin_height=geometry.fin_height,
            fin_spacing=geometry.fin_spacing,
        )
        radiation_coefficient *= radiation_view_factor
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
            "radiation_view_factor": radiation_view_factor,
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

    # Spreading resistance for undersized source footprints.
    eff_source_length = source_length if source_length > 0 else geometry.base_length
    eff_source_width = source_width if source_width > 0 else geometry.base_width
    spreading_r = rectangular_spreading_resistance(
        source_length=eff_source_length,
        source_width=eff_source_width,
        base_length=geometry.base_length,
        base_width=geometry.base_width,
        base_thickness=geometry.base_thickness,
        thermal_conductivity=material_conductivity,
    )
    effective_base_temperature = base_temperature + heat_load * spreading_r
    case_temperature = effective_base_temperature + heat_load * interface_resistance
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
        _upstream_rise = heat_load * (junction_to_case_resistance + interface_resistance)
        _total_rise = target_junction_temperature - ambient_temperature
        recommendations.append(
            f"Required sink Rθ is negative ({required_r_sink:.3f} K/W). "
            f"At {heat_load:.1f} W the upstream path (Rθjc + Rθcs) produces "
            f"{_upstream_rise:.1f} °C of rise, but only {_total_rise:.1f} °C is available "
            f"from ambient to the source limit. "
            "Reduce the heat load, raise the source temperature limit, "
            "or lower the upstream resistances — heatsink geometry changes alone cannot fix this."
        )
    if temperature_margin < 0.0:
        _suggestions: List[str] = []
        if airflow_mode == "natural":
            _suggestions.append("switch to forced convection")
        if geometry.fin_count < 20:
            _suggestions.append(
                f"increase fin count from {geometry.fin_count} to {geometry.fin_count + 4}"
            )
        if geometry.fin_height < 0.05:
            _h_mm = geometry.fin_height * 1000
            _suggestions.append(
                f"increase fin height from {_h_mm:.0f} mm to {_h_mm + 10:.0f} mm"
            )
        if surface_emissivity < 0.5:
            _suggestions.append("use a black anodized finish (emissivity ~0.85)")
        if geometry.base_thickness < 0.006:
            _b_mm = geometry.base_thickness * 1000
            _suggestions.append(
                f"increase base thickness from {_b_mm:.1f} mm to {_b_mm + 2:.1f} mm"
            )
        if _suggestions:
            recommendations.append(
                "Design exceeds thermal budget. Try: " + "; ".join(_suggestions) + "."
            )
        else:
            recommendations.append(
                "Design exceeds thermal budget. Consider a larger heatsink or active cooling."
            )
    if final_state["fin_efficiency"] < 0.7:
        recommendations.append("Fin efficiency is low; consider shorter fins, thicker fins, or higher conductivity material.")
    if airflow_mode in {"forced", "fan_curve"} and final_state["flow_state"]["pressure_drop"] > 75.0:
        recommendations.append("Pressure drop is high relative to small axial fans; reduce fin density or shorten the flow length.")
    if final_state["radiation_heat"] > 0.15 * heat_load:
        recommendations.append("Radiation is materially helping; a high-emissivity finish is beneficial for this design.")
    if spreading_r > 0.01:
        recommendations.append(
            f"Spreading resistance adds {spreading_r:.3f} K/W; consider a thicker base or vapor chamber."
        )
    # Mixed convection Richardson number warning.
    if airflow_mode in ("forced", "fan_curve"):
        _flow = final_state["flow_state"]
        if _flow["reynolds_number"] > 0:
            _film_t = 0.5 * (base_temperature + ambient_temperature)
            _props_check = air_properties(_film_t, pressure_pa=pressure_pa)
            _grashof = (
                GRAVITY * _props_check.thermal_expansion
                * (base_temperature - ambient_temperature)
                * geometry.hydraulic_diameter ** 3
                / _props_check.kinematic_viscosity ** 2
            )
            _richardson = _grashof / (_flow["reynolds_number"] ** 2)
            if _richardson > 0.1:
                recommendations.append(
                    f"Richardson number is {_richardson:.2f} (>0.1); buoyancy effects may be significant. "
                    "Consider verifying with a mixed-convection analysis."
                )
    if not recommendations:
        recommendations.append("Thermal budget is met with reasonable margin under the modeled assumptions.")

    flow_state = final_state["flow_state"]
    effective_coefficient = flow_state["convection_coefficient"] + final_state["radiation_coefficient"]
    cross_section_area = geometry.fin_thickness * geometry.base_length
    wetted_perimeter = 2.0 * (geometry.base_length + geometry.fin_thickness)
    corrected_length = geometry.fin_height + geometry.fin_thickness / 2.0
    m_value = math.sqrt(
        effective_coefficient * wetted_perimeter / (material_conductivity * cross_section_area)
    )
    m_length = m_value * corrected_length
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
        "radiation_view_factor": final_state["radiation_view_factor"],
        "spreading_resistance": spreading_r,
        "bypass_fraction": flow_state.get("bypass_fraction", 0.0),
        "fin_efficiency": final_state["fin_efficiency"],
        "overall_surface_efficiency": final_state["overall_efficiency"],
        "convection_heat_rejected": final_state["convection_heat"],
        "radiation_heat_rejected": final_state["radiation_heat"],
        "heat_rejected": final_state["heat_rejected"],
        "convection_mode_used": flow_state["convection_mode_used"],
        "status": status,
        "recommendations": recommendations,
    }

    # ── Substituted equation strings (LaTeX) ──
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
    result["subst_case_temperature"] = (
        f"T_{{\\mathrm{{case}}}} = T_{{\\mathrm{{base,eff}}}} + Q \\cdot R_{{\\theta,cs}}"
        f" = {effective_base_temperature:.2f} + {heat_load:.3f} \\times {interface_resistance:.4f}"
        f" = {case_temperature:.2f}\\,^\\circ\\mathrm{{C}}"
    )
    result["subst_base_temperature"] = (
        f"T_b = T_\\infty + Q \\cdot R_{{\\theta,\\mathrm{{sink}}}}"
        f" = {ambient_temperature:.2f} + {heat_load:.3f} \\times {sink_r_theta:.4f}"
        f" = {base_temperature:.2f}\\,^\\circ\\mathrm{{C}}"
    )
    result["subst_channel_velocity"] = (
        f"V_{{ch}} = \\frac{{\\dot{{V}}}}{{A_{{\\mathrm{{open}}}}}}"
        f" = \\frac{{{flow_state['volumetric_flow_rate']:.6f}}}{{{geometry.open_flow_area:.6f}}}"
        f" = {flow_state['channel_velocity']:.3f}\\,\\mathrm{{m/s}}"
    )
    result["subst_fin_efficiency"] = (
        "\\eta_f = \\frac{\\tanh(mL_c)}{mL_c},\\;"
        f"mL_c = \\sqrt{{\\frac{{{effective_coefficient:.3f} \\times {wetted_perimeter:.6f}}}"
        f"{{{material_conductivity:.1f} \\times {cross_section_area:.6f}}}}}"
        f" \\times {corrected_length:.6f}"
        f" = {m_length:.4f}"
        f",\\; \\eta_f = {final_state['fin_efficiency']:.4f}"
    )
    result["subst_overall_efficiency"] = (
        f"\\eta_o = 1 - \\frac{{A_f}}{{A_t}}(1 - \\eta_f)"
        f" = 1 - \\frac{{{geometry.fin_area:.6f}}}{{{geometry.total_area:.6f}}}"
        f"(1 - {final_state['fin_efficiency']:.4f})"
        f" = {final_state['overall_efficiency']:.4f}"
    )
    result["subst_pressure_drop"] = (
        "\\Delta P = \\left(f\\frac{L}{D_h} + K_c + K_e\\right)\\frac{\\rho V_{ch}^2}{2}"
        f" = {flow_state['pressure_drop']:.2f}\\,\\mathrm{{Pa}}"
    )

    _h_conv = flow_state["convection_coefficient"]
    _h_rad_raw = final_state["radiation_coefficient"]
    _vf = final_state["radiation_view_factor"]
    result["subst_convection_coefficient"] = (
        f"h_{{\\mathrm{{conv}}}} = \\frac{{\\mathrm{{Nu}} \\cdot k_{{\\mathrm{{air}}}}}}{{D_h}}"
        f" = {flow_state['nusselt_number']:.3f} \\times \\frac{{k_{{\\mathrm{{air}}}}}}{{D_h}}"
        f" = {_h_conv:.3f}\\,\\mathrm{{W/m^2 K}}"
    )
    _ts_k = base_temperature + 273.15
    _ta_k = ambient_temperature + 273.15
    result["subst_radiation_coefficient"] = (
        f"h_{{\\mathrm{{rad}}}} = \\varepsilon \\sigma (T_s^2 + T_\\infty^2)(T_s + T_\\infty) \\cdot F_{{\\mathrm{{eff}}}}"
        f" = {surface_emissivity:.2f} \\times {SIGMA:.4e}"
        f" \\times ({_ts_k:.1f}^2 + {_ta_k:.1f}^2)({_ts_k:.1f} + {_ta_k:.1f})"
        f" \\times {_vf:.3f}"
        f" = {_h_rad_raw:.4f}\\,\\mathrm{{W/m^2 K}}"
    )
    _conv_pct = 100.0 * final_state["convection_heat"] / max(final_state["heat_rejected"], 1e-12)
    _rad_pct = 100.0 * final_state["radiation_heat"] / max(final_state["heat_rejected"], 1e-12)
    result["subst_heat_split"] = (
        f"Q_{{\\mathrm{{conv}}}} = \\eta_o h_{{\\mathrm{{conv}}}} A_t \\Delta T"
        f" = {final_state['convection_heat']:.2f}\\,\\mathrm{{W}}"
        f"\\;({_conv_pct:.1f}\\%),\\quad"
        f"Q_{{\\mathrm{{rad}}}} = \\eta_o h_{{\\mathrm{{rad}}}} A_t \\Delta T"
        f" = {final_state['radiation_heat']:.2f}\\,\\mathrm{{W}}"
        f"\\;({_rad_pct:.1f}\\%)"
    )

    # ── Intermediate values for progressive disclosure ──
    film_t = 0.5 * (base_temperature + ambient_temperature)
    props_final = air_properties(film_t, pressure_pa=pressure_pa)
    result["intermediate_values"] = {
        "film_temperature": film_t,
        "air_density": props_final.density,
        "air_dynamic_viscosity": props_final.dynamic_viscosity,
        "air_thermal_conductivity": props_final.thermal_conductivity,
        "air_specific_heat": props_final.specific_heat,
        "air_prandtl": props_final.prandtl,
        "air_kinematic_viscosity": props_final.kinematic_viscosity,
        "fin_cross_section_area": cross_section_area,
        "fin_wetted_perimeter": wetted_perimeter,
        "fin_corrected_length": corrected_length,
        "fin_m_value": m_value,
        "fin_m_length": m_length,
        "effective_h": effective_coefficient,
        "open_flow_area": geometry.open_flow_area,
        "open_area_ratio": geometry.open_area_ratio,
        "frontal_area": geometry.frontal_area,
        "fin_area": geometry.fin_area,
        "exposed_base_area": geometry.exposed_base_area,
        "total_area": geometry.total_area,
        "radiation_view_factor": _vf,
        "spreading_resistance": spreading_r,
        "effective_base_temperature": effective_base_temperature,
        "rayleigh_or_reynolds": (
            flow_state.get("rayleigh_modified", 0.0)
            if airflow_mode == "natural"
            else flow_state["reynolds_number"]
        ),
    }
    if airflow_mode != "natural":
        _re = flow_state["reynolds_number"]
        _graetz = _re * props_final.prandtl * geometry.hydraulic_diameter / geometry.base_length
        result["intermediate_values"]["graetz_number"] = _graetz
        _sigma = geometry.open_area_ratio
        result["intermediate_values"]["contraction_loss_Kc"] = 0.42 * (1.0 - _sigma**2)
        result["intermediate_values"]["expansion_loss_Ke"] = (1.0 - _sigma) ** 2
        if _re > 0 and _re < 2300:
            _beta = min(max(geometry.fin_spacing / geometry.fin_height, 1e-6), 1.0)
            _f_poi = 24.0 * (1.0 - 1.3553*_beta + 1.9467*_beta**2
                             - 1.7012*_beta**3 + 0.9564*_beta**4 - 0.2537*_beta**5)
            result["intermediate_values"]["darcy_friction_factor"] = _f_poi / _re
            result["intermediate_values"]["flow_regime"] = "laminar"
        elif _re >= 2300:
            result["intermediate_values"]["darcy_friction_factor"] = (
                (0.790 * math.log(_re) - 1.64) ** -2
            )
            result["intermediate_values"]["flow_regime"] = "turbulent"

    # ── Dynamic assumptions list ──
    assumptions: List[str] = [
        "Steady-state analysis — no transient effects modeled.",
        "Isothermal base — the base plate is assumed to be at a uniform temperature "
        "before adding the spreading resistance correction.",
        f"Air properties evaluated at the film temperature "
        f"T_film = ({base_temperature:.1f} + {ambient_temperature:.1f})/2 = {film_t:.1f} °C "
        f"using Sutherland-law fits (valid 200–700 K, actual {film_t + 273.15:.0f} K).",
    ]
    if airflow_mode == "natural":
        if orientation == "vertical":
            assumptions.append(
                "Natural convection: Bar-Cohen/Rohsenow (1984) composite isothermal parallel-plate "
                f"correlation with modified Rayleigh number Ra* = {flow_state.get('rayleigh_modified', 0):.2f}."
            )
        else:
            _ra = flow_state.get("rayleigh_modified", 0)
            _facing = "heated surface up" if orientation == "horizontal_up" else "heated surface down"
            assumptions.append(
                f"Natural convection: McAdams (1954) horizontal plate correlation ({_facing}), "
                f"Ra_L = {_ra:.1f}."
            )
        assumptions.append(
            "Induced channel velocity estimated from chimney-flow energy balance — "
            "treat as approximate."
        )
    else:
        _re = flow_state["reynolds_number"]
        if _re < 2300:
            assumptions.append(
                f"Forced convection: Laminar regime (Re = {_re:.0f} < 2300). "
                "Developing-flow Nusselt number from Muzychka/Yovanovich (2004) combined-entry correlation. "
                "Friction factor from Shah/London rectangular-duct Poiseuille-number fit."
            )
        else:
            assumptions.append(
                f"Forced convection: Turbulent regime (Re = {_re:.0f} > 2300). "
                "Gnielinski correlation for Nusselt number. "
                "Petukhov friction factor used for both heat transfer and pressure drop."
            )
        if not ducted and flow_state.get("bypass_fraction", 0.0) > 0:
            _bp = flow_state["bypass_fraction"]
            assumptions.append(
                f"Unducted configuration — bypass fraction = {_bp:.0%} removed from channel flow "
                "(first-order model: bypass ≈ 1/(1 + 0.5·√(H/s)), per Simons 2003)."
            )
        assumptions.append(
            f"Pressure drop includes Darcy friction (f·L/D_h), entrance contraction (K_c = "
            f"{0.42 * (1.0 - geometry.open_area_ratio**2):.3f}), and exit expansion "
            f"(K_e = {(1.0 - geometry.open_area_ratio)**2:.3f})."
        )

    if airflow_mode == "fan_curve":
        assumptions.append(
            "Fan operating point found by binary-search intersection of parabolic fan curve "
            "with the heatsink system curve (ΔP ∝ Q²)."
        )

    assumptions.append(
        f"Radiation: linearized Stefan-Boltzmann coefficient with ε = {surface_emissivity:.2f}. "
        f"Fin-channel view factor F_eff = s/(s+H) = {_vf:.3f} "
        f"(Sparrow/Cess 1978 parallel-plate model)."
    )
    assumptions.append(
        f"Fin efficiency: straight rectangular fin with corrected tip length "
        f"(L_c = H + t/2 = {corrected_length*1000:.2f} mm). "
        f"η_f = tanh(mL_c)/(mL_c) = {final_state['fin_efficiency']:.3f}."
    )
    assumptions.append(
        f"Overall surface efficiency η_o = {final_state['overall_efficiency']:.3f} "
        f"(A_fin/A_total = {geometry.fin_area/geometry.total_area:.3f})."
    )
    if spreading_r > 0.0:
        assumptions.append(
            f"Spreading resistance R_sp = {spreading_r:.4f} K/W added for source footprint "
            f"{eff_source_length*1000:.1f}×{eff_source_width*1000:.1f} mm on "
            f"{geometry.base_length*1000:.1f}×{geometry.base_width*1000:.1f} mm base "
            "(Yovanovich et al. 1999 dimensionless model)."
        )
    else:
        assumptions.append("Source covers full base — no spreading resistance added.")

    _t_k = film_t + 273.15
    if _t_k < 200.0 or _t_k > 700.0:
        assumptions.append(
            f"WARNING: Film temperature {_t_k:.0f} K is outside the validated range "
            "for the Sutherland air-property fits (200–700 K). Results may be inaccurate."
        )

    result["assumptions"] = assumptions

    # ── Correlation details per output ──
    result["correlation_details"] = {
        "convection_coefficient": {
            "name": (
                "Bar-Cohen/Rohsenow (1984)" if airflow_mode == "natural" and orientation == "vertical"
                else "McAdams (1954)" if airflow_mode == "natural"
                else "Gnielinski" if flow_state["reynolds_number"] >= 2300
                else "Muzychka/Yovanovich (2004)"
            ),
            "reference": (
                "Bar-Cohen, Rohsenow, J. Heat Transfer 106(1), 1984, doi:10.1115/1.3246622"
                if airflow_mode == "natural" and orientation == "vertical"
                else "McAdams, Heat Transmission, 3rd ed., 1954; Incropera et al., Table 9.1"
                if airflow_mode == "natural"
                else "Gnielinski, Int. Chem. Eng. 16:359, 1976; Petukhov, Adv. Heat Transfer 6:503, 1970"
                if flow_state["reynolds_number"] >= 2300
                else "Muzychka, Yovanovich, J. Heat Transfer 126(1), 2004, doi:10.1115/1.1643752"
            ),
            "validity": (
                "Isothermal vertical parallel plates, Ra* > 0"
                if airflow_mode == "natural" and orientation == "vertical"
                else f"Horizontal plate, 10⁴ < Ra_L < 10¹¹"
                if airflow_mode == "natural"
                else "2300 < Re < 5×10⁶, 0.5 < Pr < 2000"
                if flow_state["reynolds_number"] >= 2300
                else "Developing laminar flow in rectangular ducts, Re < 2300"
            ),
        },
        "pressure_drop": {
            "name": (
                "Darcy-Weisbach with rectangular-duct Poiseuille correction"
                if flow_state["reynolds_number"] < 2300
                else "Darcy-Weisbach with Petukhov friction factor"
            ),
            "reference": (
                "Shah, London, Laminar Flow Forced Convection in Ducts, 1978; "
                "Simons, Electronics Cooling, 2003"
            ),
            "validity": "Entrance/exit losses via Kays & London contraction/expansion model.",
        },
        "radiation_coefficient": {
            "name": "Linearized Stefan-Boltzmann with parallel-plate view factor",
            "reference": (
                "Incropera et al., Fundamentals of Heat and Mass Transfer; "
                "Sparrow & Cess, Radiation Heat Transfer, 1978"
            ),
            "validity": "Gray-diffuse surfaces, linearization valid when T_s − T_∞ is moderate.",
        },
        "fin_efficiency": {
            "name": "Straight rectangular fin with corrected tip length",
            "reference": "Incropera et al., Fundamentals of Heat and Mass Transfer, Table 3.5.",
            "validity": "Uniform h over fin surface, 1D conduction along fin height.",
        },
        "spreading_resistance": {
            "name": "Yovanovich dimensionless spreading model",
            "reference": (
                "Yovanovich, Muzychka, Culham (1999), Spreading Resistance of Isoflux Rectangles; "
                "Lee, Song, Au, Moran (1995), Constriction/Spreading Resistance Model"
            ),
            "validity": "Centered rectangular source on rectangular plate, uniform flux, adiabatic edges.",
        },
    }

    return result


def analyze_heatsink_spreading_view(
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
    orientation: str = "vertical",
    source_length: float = 0.0,
    source_width: float = 0.0,
    ducted: bool = True,
    source_x: float = 0.0,
    source_y: float = 0.0,
    grid_x: int = 41,
    grid_y: int = 25,
    sink_thermal_resistance: float = 0.0,
) -> Dict[str, Any]:
    """
    Run the global plate-fin solver, then solve the 2D base spreading field.

    Parameters match ``analyze_plate_fin_heatsink`` with additional source
    position and grid controls.  ``source_x`` and ``source_y`` are the source
    center coordinates measured from the lower-left corner of the base.  If
    zero, the source is centered.

    If ``sink_thermal_resistance`` is provided and > 0, the internal baseline
    solver call is skipped and the provided value is used directly.  This
    avoids redundant computation when the caller already has the baseline
    result.

    Returns a dict with the full baseline result under ``"baseline"`` and
    the spreading field data under ``"spreading"``.
    """
    try:
        from pycalcs.heatsink_spreading import solve_base_spreading_field
    except ImportError:
        from heatsink_spreading import solve_base_spreading_field

    if sink_thermal_resistance > 0:
        baseline = None
        sink_r = sink_thermal_resistance
    else:
        baseline = analyze_plate_fin_heatsink(
            heat_load=heat_load,
            ambient_temperature=ambient_temperature,
            target_junction_temperature=target_junction_temperature,
            base_length=base_length,
            base_width=base_width,
            base_thickness=base_thickness,
            fin_height=fin_height,
            fin_thickness=fin_thickness,
            fin_count=fin_count,
            material_conductivity=material_conductivity,
            surface_emissivity=surface_emissivity,
            airflow_mode=airflow_mode,
            approach_velocity=approach_velocity,
            volumetric_flow_rate=volumetric_flow_rate,
            fan_max_pressure=fan_max_pressure,
            fan_max_flow_rate=fan_max_flow_rate,
            interface_resistance=interface_resistance,
            junction_to_case_resistance=junction_to_case_resistance,
            pressure_pa=pressure_pa,
            orientation=orientation,
            source_length=source_length,
            source_width=source_width,
            ducted=ducted,
        )
        sink_r = baseline["sink_thermal_resistance"]

    eff_source_length = source_length if source_length > 0 else base_length
    eff_source_width = source_width if source_width > 0 else base_width
    eff_source_x = source_x if source_x > 0 else base_length / 2.0
    eff_source_y = source_y if source_y > 0 else base_width / 2.0

    # Flag off-center source in baseline assumptions.
    is_off_center = (
        abs(eff_source_x - base_length / 2.0) > 1e-6
        or abs(eff_source_y - base_width / 2.0) > 1e-6
    )
    if is_off_center and baseline is not None:
        baseline.setdefault("assumptions", []).append(
            "Headline results use a centered-source spreading model (Yovanovich); "
            "see Spread View for off-center effects."
        )

    if sink_r <= 0:
        return {
            "baseline": baseline,
            "spreading": None,
            "spreading_error": "Sink thermal resistance is zero or negative; spreading solve not possible.",
        }

    sources = [{
        "id": "source_1",
        "x_center": eff_source_x,
        "y_center": eff_source_y,
        "length": eff_source_length,
        "width": eff_source_width,
        "power": heat_load,
        "junction_to_case_resistance": junction_to_case_resistance,
        "interface_resistance": interface_resistance,
    }]

    try:
        spreading = solve_base_spreading_field(
            base_length=base_length,
            base_width=base_width,
            base_thickness=base_thickness,
            material_conductivity=material_conductivity,
            ambient_temperature=ambient_temperature,
            sink_thermal_resistance=sink_r,
            sources=sources,
            grid_x=grid_x,
            grid_y=grid_y,
        )
    except ValueError as e:
        return {
            "baseline": baseline,
            "spreading": None,
            "spreading_error": str(e),
        }

    return {
        "baseline": baseline,
        "spreading": spreading,
        "spreading_error": None,
    }


def get_heatsink_sweep_metadata() -> Dict[str, Any]:
    """Return parameter and output definitions for sensitivity analysis."""
    return {
        "parameters": {
            "fin_height": {
                "label": "Fin Height", "unit": "m", "display_unit": "mm",
                "display_scale": 1000, "category": "geometry",
                "default_span": [0.5, 1.5], "min": 0.005, "max": 0.120,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
            },
            "fin_thickness": {
                "label": "Fin Thickness", "unit": "m", "display_unit": "mm",
                "display_scale": 1000, "category": "geometry",
                "default_span": [0.5, 2.0], "min": 0.0003, "max": 0.005,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
            },
            "fin_count": {
                "label": "Fin Count", "unit": "", "display_unit": "",
                "display_scale": 1, "category": "geometry",
                "default_span": [0.5, 2.0], "min": 2, "max": 60,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
                "integer": True,
            },
            "base_thickness": {
                "label": "Base Thickness", "unit": "m", "display_unit": "mm",
                "display_scale": 1000, "category": "geometry",
                "default_span": [0.5, 2.0], "min": 0.001, "max": 0.020,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
            },
            "base_length": {
                "label": "Base Length", "unit": "m", "display_unit": "mm",
                "display_scale": 1000, "category": "geometry",
                "default_span": [0.5, 1.5], "min": 0.020, "max": 0.300,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
            },
            "base_width": {
                "label": "Base Width", "unit": "m", "display_unit": "mm",
                "display_scale": 1000, "category": "geometry",
                "default_span": [0.5, 1.5], "min": 0.020, "max": 0.300,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
            },
            "heat_load": {
                "label": "Heat Load", "unit": "W", "display_unit": "W",
                "display_scale": 1, "category": "thermal",
                "default_span": [0.5, 2.0], "min": 0.5, "max": 500.0,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
            },
            "ambient_temperature": {
                "label": "Ambient Temperature", "unit": "°C", "display_unit": "°C",
                "display_scale": 1, "category": "thermal",
                "default_span": [0.8, 1.2], "min": -40.0, "max": 85.0,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
            },
            "surface_emissivity": {
                "label": "Surface Emissivity", "unit": "", "display_unit": "",
                "display_scale": 1, "category": "thermal",
                "default_span": [0.5, 1.0], "min": 0.02, "max": 0.95,
                "scale": "linear", "modes": ["natural", "forced", "fan_curve"],
            },
            "approach_velocity": {
                "label": "Approach Velocity", "unit": "m/s", "display_unit": "m/s",
                "display_scale": 1, "category": "airflow",
                "default_span": [0.3, 2.0], "min": 0.1, "max": 15.0,
                "scale": "linear", "modes": ["forced"],
            },
        },
        "outputs": {
            "sink_thermal_resistance": {
                "label": "Sink Thermal Resistance", "unit": "K/W", "goal": "minimize",
            },
            "junction_temperature": {
                "label": "Junction Temperature", "unit": "°C", "goal": "minimize",
            },
            "temperature_margin": {
                "label": "Temperature Margin", "unit": "°C", "goal": "maximize",
            },
            "pressure_drop": {
                "label": "Pressure Drop", "unit": "Pa", "goal": "minimize",
            },
            "fin_efficiency": {
                "label": "Fin Efficiency", "unit": "", "goal": "maximize",
            },
        },
    }


def _filter_solver_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Strip keys not accepted by analyze_plate_fin_heatsink."""
    import inspect
    valid = set(inspect.signature(analyze_plate_fin_heatsink).parameters)
    return {k: v for k, v in inputs.items() if k in valid}


def run_heatsink_1d_sweep(
    baseline_inputs: Dict[str, Any],
    sweep_param: str,
    sweep_values: list,
    output_keys: list = None,
) -> Dict[str, Any]:
    """
    Run a 1D parameter sweep around a baseline heatsink configuration.

    For each value in sweep_values, overrides sweep_param in baseline_inputs,
    calls analyze_plate_fin_heatsink(), and collects the requested output keys.
    """
    if output_keys is None:
        output_keys = ["sink_thermal_resistance", "junction_temperature", "temperature_margin"]

    metadata = get_heatsink_sweep_metadata()
    if sweep_param not in metadata["parameters"]:
        raise ValueError(f"Unknown sweep parameter: {sweep_param}")

    baseline_x = baseline_inputs.get(sweep_param)
    results_series: Dict[str, list] = {key: [] for key in output_keys}
    valid_mask: List[bool] = []
    warnings: List[str] = []

    for val in sweep_values:
        inputs = dict(baseline_inputs)
        if metadata["parameters"][sweep_param].get("integer"):
            inputs[sweep_param] = int(val)
        else:
            inputs[sweep_param] = float(val)
        try:
            result = analyze_plate_fin_heatsink(**_filter_solver_inputs(inputs))
            for key in output_keys:
                results_series[key].append(result.get(key))
            valid_mask.append(True)
        except (ValueError, ZeroDivisionError) as exc:
            for key in output_keys:
                results_series[key].append(None)
            valid_mask.append(False)
            warnings.append(f"At {sweep_param}={val}: {exc}")

    baseline_outputs: Dict[str, Any] = {}
    try:
        baseline_result = analyze_plate_fin_heatsink(**_filter_solver_inputs(baseline_inputs))
        for key in output_keys:
            baseline_outputs[key] = baseline_result.get(key)
    except Exception:
        pass

    return {
        "x_values": list(sweep_values),
        "series": results_series,
        "baseline_x": baseline_x,
        "baseline_outputs": baseline_outputs,
        "valid_mask": valid_mask,
        "warnings": warnings,
    }


def run_heatsink_2d_contour(
    baseline_inputs: Dict[str, Any],
    x_param: str,
    y_param: str,
    x_values: list,
    y_values: list,
    output_key: str = "sink_thermal_resistance",
) -> Dict[str, Any]:
    """
    Run a 2D parameter sweep and return a contour grid.

    Returns z_values as a 2D list [y_index][x_index].
    """
    metadata = get_heatsink_sweep_metadata()
    if x_param not in metadata["parameters"]:
        raise ValueError(f"Unknown x parameter: {x_param}")
    if y_param not in metadata["parameters"]:
        raise ValueError(f"Unknown y parameter: {y_param}")

    z_values: List[list] = []
    valid_mask: List[list] = []
    best_z = None
    best_point = None
    goal = metadata["outputs"].get(output_key, {}).get("goal", "minimize")

    for y_val in y_values:
        z_row: list = []
        valid_row: List[bool] = []
        for x_val in x_values:
            inputs = dict(baseline_inputs)
            if metadata["parameters"][x_param].get("integer"):
                inputs[x_param] = int(x_val)
            else:
                inputs[x_param] = float(x_val)
            if metadata["parameters"][y_param].get("integer"):
                inputs[y_param] = int(y_val)
            else:
                inputs[y_param] = float(y_val)
            try:
                result = analyze_plate_fin_heatsink(**_filter_solver_inputs(inputs))
                z = result.get(output_key)
                z_row.append(z)
                valid_row.append(True)
                if z is not None:
                    is_better = (
                        best_z is None
                        or (goal == "minimize" and z < best_z)
                        or (goal == "maximize" and z > best_z)
                    )
                    if is_better:
                        best_z = z
                        best_point = {"x": x_val, "y": y_val, "z": z}
            except (ValueError, ZeroDivisionError):
                z_row.append(None)
                valid_row.append(False)
        z_values.append(z_row)
        valid_mask.append(valid_row)

    baseline_point: Dict[str, Any] = {
        "x": baseline_inputs.get(x_param),
        "y": baseline_inputs.get(y_param),
    }
    try:
        bl_result = analyze_plate_fin_heatsink(**baseline_inputs)
        baseline_point["z"] = bl_result.get(output_key)
    except Exception:
        baseline_point["z"] = None

    return {
        "x_values": list(x_values),
        "y_values": list(y_values),
        "z_values": z_values,
        "valid_mask": valid_mask,
        "baseline_point": baseline_point,
        "best_point": best_point,
    }
