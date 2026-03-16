"""
Interference-fit and shrink-fit calculations for cylindrical shaft-hub joints.

This module implements elastic press-fit relations for straight cylindrical
assemblies using the thick-cylinder compliance and stress treatment commonly
presented in Shigley's Mechanical Engineering Design.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


MATERIAL_PRESETS: Dict[str, Dict[str, float | str]] = {
    "steel": {
        "display_name": "Steel (Generic)",
        "youngs_modulus_mpa": 200000.0,
        "poisson_ratio": 0.30,
        "yield_strength_mpa": 350.0,
        "thermal_expansion_e6_per_c": 12.0,
    },
    "steel_1020": {
        "display_name": "Steel 1020",
        "youngs_modulus_mpa": 207000.0,
        "poisson_ratio": 0.292,
        "yield_strength_mpa": 210.0,
        "thermal_expansion_e6_per_c": 11.7,
    },
    "steel_1045_annealed": {
        "display_name": "Steel 1045 (Annealed)",
        "youngs_modulus_mpa": 207000.0,
        "poisson_ratio": 0.292,
        "yield_strength_mpa": 310.0,
        "thermal_expansion_e6_per_c": 11.7,
    },
    "steel_4140_qt": {
        "display_name": "Steel 4140 (Q&T)",
        "youngs_modulus_mpa": 207000.0,
        "poisson_ratio": 0.292,
        "yield_strength_mpa": 655.0,
        "thermal_expansion_e6_per_c": 11.7,
    },
    "steel_4340_qt": {
        "display_name": "Steel 4340 (Q&T)",
        "youngs_modulus_mpa": 207000.0,
        "poisson_ratio": 0.292,
        "yield_strength_mpa": 470.0,
        "thermal_expansion_e6_per_c": 12.3,
    },
    "stainless_steel": {
        "display_name": "Stainless Steel",
        "youngs_modulus_mpa": 193000.0,
        "poisson_ratio": 0.31,
        "yield_strength_mpa": 215.0,
        "thermal_expansion_e6_per_c": 17.3,
    },
    "stainless_304": {
        "display_name": "Stainless 304",
        "youngs_modulus_mpa": 193000.0,
        "poisson_ratio": 0.29,
        "yield_strength_mpa": 207.0,
        "thermal_expansion_e6_per_c": 17.2,
    },
    "stainless_316": {
        "display_name": "Stainless 316",
        "youngs_modulus_mpa": 193000.0,
        "poisson_ratio": 0.29,
        "yield_strength_mpa": 207.0,
        "thermal_expansion_e6_per_c": 16.0,
    },
    "aluminum": {
        "display_name": "Aluminum Alloy",
        "youngs_modulus_mpa": 70000.0,
        "poisson_ratio": 0.33,
        "yield_strength_mpa": 150.0,
        "thermal_expansion_e6_per_c": 23.0,
    },
    "aluminum_2024_t4": {
        "display_name": "Aluminum 2024-T4",
        "youngs_modulus_mpa": 73000.0,
        "poisson_ratio": 0.33,
        "yield_strength_mpa": 324.0,
        "thermal_expansion_e6_per_c": 22.9,
    },
    "aluminum_6061_t6": {
        "display_name": "Aluminum 6061-T6",
        "youngs_modulus_mpa": 69000.0,
        "poisson_ratio": 0.33,
        "yield_strength_mpa": 276.0,
        "thermal_expansion_e6_per_c": 23.6,
    },
    "aluminum_7075_t6": {
        "display_name": "Aluminum 7075-T6",
        "youngs_modulus_mpa": 72000.0,
        "poisson_ratio": 0.33,
        "yield_strength_mpa": 503.0,
        "thermal_expansion_e6_per_c": 23.6,
    },
    "cast_iron": {
        "display_name": "Cast Iron",
        "youngs_modulus_mpa": 150000.0,
        "poisson_ratio": 0.26,
        "yield_strength_mpa": 200.0,
        "thermal_expansion_e6_per_c": 10.8,
    },
    "cast_iron_gray": {
        "display_name": "Cast Iron (Gray)",
        "youngs_modulus_mpa": 170000.0,
        "poisson_ratio": 0.26,
        "yield_strength_mpa": 200.0,
        "thermal_expansion_e6_per_c": 11.0,
    },
    "bronze": {
        "display_name": "Bronze",
        "youngs_modulus_mpa": 110000.0,
        "poisson_ratio": 0.34,
        "yield_strength_mpa": 140.0,
        "thermal_expansion_e6_per_c": 18.0,
    },
    "bronze_bearing": {
        "display_name": "Bronze (Bearing)",
        "youngs_modulus_mpa": 110000.0,
        "poisson_ratio": 0.34,
        "yield_strength_mpa": 140.0,
        "thermal_expansion_e6_per_c": 18.0,
    },
    "brass": {
        "display_name": "Brass",
        "youngs_modulus_mpa": 100000.0,
        "poisson_ratio": 0.35,
        "yield_strength_mpa": 120.0,
        "thermal_expansion_e6_per_c": 20.0,
    },
    "brass_7030": {
        "display_name": "Brass (70/30)",
        "youngs_modulus_mpa": 110000.0,
        "poisson_ratio": 0.34,
        "yield_strength_mpa": 200.0,
        "thermal_expansion_e6_per_c": 19.1,
    },
    "copper": {
        "display_name": "Copper",
        "youngs_modulus_mpa": 117000.0,
        "poisson_ratio": 0.34,
        "yield_strength_mpa": 70.0,
        "thermal_expansion_e6_per_c": 17.0,
    },
    "copper_annealed": {
        "display_name": "Copper (Annealed)",
        "youngs_modulus_mpa": 117000.0,
        "poisson_ratio": 0.34,
        "yield_strength_mpa": 70.0,
        "thermal_expansion_e6_per_c": 16.5,
    },
    "titanium_6al4v": {
        "display_name": "Titanium 6Al-4V",
        "youngs_modulus_mpa": 114000.0,
        "poisson_ratio": 0.342,
        "yield_strength_mpa": 880.0,
        "thermal_expansion_e6_per_c": 8.6,
    },
    "custom": {
        "display_name": "Custom Material",
        "youngs_modulus_mpa": 200000.0,
        "poisson_ratio": 0.30,
        "yield_strength_mpa": 350.0,
        "thermal_expansion_e6_per_c": 12.0,
    },
}


def get_interference_fit_material_presets() -> Dict[str, Dict[str, float | str]]:
    """
    Return the built-in shaft and hub material presets.

    Returns
    -------
    dict
        Material presets keyed by preset name.
    """

    return {
        key: dict(value)
        for key, value in MATERIAL_PRESETS.items()
    }


def _validate_positive(name: str, value: float) -> None:
    """Raise when a value expected to be strictly positive is not."""

    if value <= 0.0:
        raise ValueError(f"{name} must be > 0. Got {value}.")


def _validate_nonnegative(name: str, value: float) -> None:
    """Raise when a value expected to be nonnegative is not."""

    if value < 0.0:
        raise ValueError(f"{name} must be >= 0. Got {value}.")


def _validate_poisson_ratio(name: str, value: float) -> None:
    """Validate a physically meaningful Poisson ratio."""

    if value < 0.0 or value >= 0.5:
        raise ValueError(f"{name} must satisfy 0 <= nu < 0.5. Got {value}.")


def _lookup_material_preset(name: str) -> Dict[str, float | str]:
    """Look up a material preset by key."""

    key = name.strip().lower()
    if key not in MATERIAL_PRESETS:
        valid = ", ".join(sorted(MATERIAL_PRESETS))
        raise ValueError(f"Unknown material preset '{name}'. Valid presets: {valid}.")
    return dict(MATERIAL_PRESETS[key])


def _resolve_material(
    component_label: str,
    material_key: str,
    youngs_modulus_mpa: float,
    poisson_ratio: float,
    yield_strength_mpa: float,
    thermal_expansion_e6_per_c: float,
) -> Dict[str, float | str]:
    """Resolve a shaft or hub material from preset or custom values."""

    if material_key.strip().lower() != "custom":
        preset = _lookup_material_preset(material_key)
        resolved = {
            "material_key": material_key.strip().lower(),
            "display_name": str(preset["display_name"]),
            "youngs_modulus_mpa": float(preset["youngs_modulus_mpa"]),
            "poisson_ratio": float(preset["poisson_ratio"]),
            "yield_strength_mpa": float(preset["yield_strength_mpa"]),
            "thermal_expansion_e6_per_c": float(preset["thermal_expansion_e6_per_c"]),
        }
    else:
        resolved = {
            "material_key": "custom",
            "display_name": f"Custom {component_label.title()} Material",
            "youngs_modulus_mpa": youngs_modulus_mpa,
            "poisson_ratio": poisson_ratio,
            "yield_strength_mpa": yield_strength_mpa,
            "thermal_expansion_e6_per_c": thermal_expansion_e6_per_c,
        }

    _validate_positive(
        f"{component_label} youngs_modulus_mpa",
        float(resolved["youngs_modulus_mpa"]),
    )
    _validate_poisson_ratio(
        f"{component_label} poisson_ratio",
        float(resolved["poisson_ratio"]),
    )
    _validate_positive(
        f"{component_label} yield_strength_mpa",
        float(resolved["yield_strength_mpa"]),
    )
    _validate_nonnegative(
        f"{component_label} thermal_expansion_e6_per_c",
        float(resolved["thermal_expansion_e6_per_c"]),
    )

    return resolved


def _coerce_range(
    nominal: float,
    minimum: float | None,
    maximum: float | None,
) -> tuple[float, float, float]:
    """Resolve a nominal, minimum, and maximum interference triplet."""

    min_value = nominal if minimum is None else minimum
    max_value = nominal if maximum is None else maximum
    _validate_nonnegative("interference_nominal_mm", nominal)
    _validate_nonnegative("interference_min_mm", min_value)
    _validate_nonnegative("interference_max_mm", max_value)

    if min_value > nominal:
        raise ValueError("interference_min_mm must be <= interference_nominal_mm.")
    if nominal > max_value:
        raise ValueError("interference_nominal_mm must be <= interference_max_mm.")

    return min_value, nominal, max_value


def _hub_geometry_factor(fit_diameter_m: float, hub_outer_diameter_m: float) -> float:
    """Return the thick-cylinder compliance factor for the hub."""

    denominator = hub_outer_diameter_m**2 - fit_diameter_m**2
    if denominator <= 0.0:
        raise ValueError("hub_outer_diameter_mm must be greater than shaft_outer_diameter_mm.")
    return (hub_outer_diameter_m**2 + fit_diameter_m**2) / denominator


def _shaft_geometry_factor(
    fit_diameter_m: float,
    shaft_inner_diameter_m: float,
) -> float:
    """Return the thick-cylinder compliance factor for a hollow shaft."""

    if shaft_inner_diameter_m <= 0.0:
        return 1.0

    denominator = fit_diameter_m**2 - shaft_inner_diameter_m**2
    if denominator <= 0.0:
        raise ValueError("shaft_inner_diameter_mm must be less than shaft_outer_diameter_mm.")
    return (fit_diameter_m**2 + shaft_inner_diameter_m**2) / denominator


def _calculate_interface_pressure_mpa(
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    interference_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> float:
    """Calculate interface pressure from elastic diametral interference."""

    if interference_mm <= 0.0:
        return 0.0

    d = shaft_outer_diameter_mm * 1e-3
    D = hub_outer_diameter_mm * 1e-3
    di = shaft_inner_diameter_mm * 1e-3
    delta = interference_mm * 1e-3

    e_h = float(hub_material["youngs_modulus_mpa"]) * 1e6
    nu_h = float(hub_material["poisson_ratio"])
    e_s = float(shaft_material["youngs_modulus_mpa"]) * 1e6
    nu_s = float(shaft_material["poisson_ratio"])

    hub_factor = _hub_geometry_factor(d, D)
    shaft_factor = _shaft_geometry_factor(d, di)

    shaft_term = (1.0 - nu_s) if di <= 0.0 else (shaft_factor - nu_s)
    denominator = (d / e_h) * (hub_factor + nu_h) + (d / e_s) * shaft_term
    if denominator <= 0.0:
        raise ValueError("Calculated interference-fit compliance denominator is not positive.")

    return delta / denominator / 1e6


def _calculate_compliance_data(
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> Dict[str, float]:
    """Return Shigley-style geometry and compliance factors for the fit."""

    d_m = shaft_outer_diameter_mm * 1e-3
    D_m = hub_outer_diameter_mm * 1e-3
    di_m = shaft_inner_diameter_mm * 1e-3

    e_h = float(hub_material["youngs_modulus_mpa"]) * 1e6
    nu_h = float(hub_material["poisson_ratio"])
    e_s = float(shaft_material["youngs_modulus_mpa"]) * 1e6
    nu_s = float(shaft_material["poisson_ratio"])

    hub_geometry_factor = _hub_geometry_factor(d_m, D_m)
    shaft_geometry_factor = _shaft_geometry_factor(d_m, di_m)

    hub_coefficient = hub_geometry_factor + nu_h
    shaft_coefficient = (
        1.0 - nu_s
        if shaft_inner_diameter_mm <= 0.0
        else shaft_geometry_factor - nu_s
    )
    hub_term_m_per_pa = (d_m / e_h) * hub_coefficient
    shaft_term_m_per_pa = (d_m / e_s) * shaft_coefficient
    total_term_m_per_pa = hub_term_m_per_pa + shaft_term_m_per_pa

    return {
        "hub_geometry_factor": hub_geometry_factor,
        "shaft_geometry_factor": shaft_geometry_factor,
        "hub_coefficient": hub_coefficient,
        "shaft_coefficient": shaft_coefficient,
        "hub_term_m_per_pa": hub_term_m_per_pa,
        "shaft_term_m_per_pa": shaft_term_m_per_pa,
        "total_term_m_per_pa": total_term_m_per_pa,
        "total_term_mm_per_mpa": total_term_m_per_pa * 1e9,
    }


def _surface_result(
    location_label: str,
    radius_mm: float,
    radial_mpa: float,
    hoop_mpa: float,
) -> Dict[str, float | str]:
    """Build a single surface-stress payload for UI and test consumption."""

    if abs(radial_mpa) < 1e-12:
        radial_mpa = 0.0
    if abs(hoop_mpa) < 1e-12:
        hoop_mpa = 0.0

    von_mises_mpa = math.sqrt(
        hoop_mpa**2 - hoop_mpa * radial_mpa + radial_mpa**2
    )
    return {
        "location_label": location_label,
        "radius_mm": radius_mm,
        "radial_stress_mpa": radial_mpa,
        "hoop_stress_mpa": hoop_mpa,
        "von_mises_mpa": von_mises_mpa,
    }


def _calculate_member_stresses_mpa(
    pressure_mpa: float,
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> Dict[str, Dict[str, Any]]:
    """Calculate member surface stresses and yield margins for the fit."""

    d = shaft_outer_diameter_mm
    D = hub_outer_diameter_mm
    di = shaft_inner_diameter_mm

    hub_yield = float(hub_material["yield_strength_mpa"])
    shaft_yield = float(shaft_material["yield_strength_mpa"])

    if pressure_mpa <= 0.0:
        zero_surface = _surface_result("Interface / outer surface", d / 2.0, 0.0, 0.0)
        hub_surfaces = {
            "inner_surface": _surface_result("Inner surface", d / 2.0, 0.0, 0.0),
            "outer_surface": _surface_result("Outer surface", D / 2.0, 0.0, 0.0),
        }
        shaft_surfaces: Dict[str, Dict[str, float | str] | None] = {
            "outer_surface": zero_surface,
            "inner_surface": None
            if di <= 0.0
            else _surface_result("Inner bore", di / 2.0, 0.0, 0.0),
        }
        return {
            "hub": {
                "surface_order": ["inner_surface", "outer_surface"],
                "surfaces": hub_surfaces,
                "max_von_mises_mpa": 0.0,
                "yield_safety_factor": float("inf"),
            },
            "shaft": {
                "member_type": "solid" if di <= 0.0 else "hollow",
                "surface_order": (
                    ["outer_surface"]
                    if di <= 0.0
                    else ["outer_surface", "inner_surface"]
                ),
                "surfaces": shaft_surfaces,
                "max_von_mises_mpa": 0.0,
                "yield_safety_factor": float("inf"),
            },
        }

    d_m = d * 1e-3
    D_m = D * 1e-3
    di_m = di * 1e-3

    hub_inner = _surface_result(
        "Inner surface",
        d / 2.0,
        -pressure_mpa,
        pressure_mpa * _hub_geometry_factor(d_m, D_m),
    )
    hub_outer = _surface_result(
        "Outer surface",
        D / 2.0,
        0.0,
        2.0 * pressure_mpa * d_m**2 / (D_m**2 - d_m**2),
    )
    hub_max_vm = max(
        float(hub_inner["von_mises_mpa"]),
        float(hub_outer["von_mises_mpa"]),
    )

    if di_m <= 0.0:
        shaft_outer = _surface_result(
            "Outer surface",
            d / 2.0,
            -pressure_mpa,
            -pressure_mpa,
        )
        shaft_inner = None
        shaft_max_vm = float(shaft_outer["von_mises_mpa"])
        shaft_order = ["outer_surface"]
        shaft_member_type = "solid"
    else:
        shaft_outer = _surface_result(
            "Outer surface",
            d / 2.0,
            -pressure_mpa,
            -pressure_mpa * _shaft_geometry_factor(d_m, di_m),
        )
        shaft_inner = _surface_result(
            "Inner bore",
            di / 2.0,
            0.0,
            -2.0 * pressure_mpa * d_m**2 / (d_m**2 - di_m**2),
        )
        shaft_max_vm = max(
            float(shaft_outer["von_mises_mpa"]),
            float(shaft_inner["von_mises_mpa"]),
        )
        shaft_order = ["outer_surface", "inner_surface"]
        shaft_member_type = "hollow"

    return {
        "hub": {
            "surface_order": ["inner_surface", "outer_surface"],
            "surfaces": {
                "inner_surface": hub_inner,
                "outer_surface": hub_outer,
            },
            "max_von_mises_mpa": hub_max_vm,
            "yield_safety_factor": (
                hub_yield / hub_max_vm if hub_max_vm > 0.0 else float("inf")
            ),
        },
        "shaft": {
            "member_type": shaft_member_type,
            "surface_order": shaft_order,
            "surfaces": {
                "outer_surface": shaft_outer,
                "inner_surface": shaft_inner,
            },
            "max_von_mises_mpa": shaft_max_vm,
            "yield_safety_factor": (
                shaft_yield / shaft_max_vm if shaft_max_vm > 0.0 else float("inf")
            ),
        },
    }


def _generate_stress_distribution(
    pressure_mpa: float,
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    n_hub_points: int = 80,
    n_shaft_points: int = 60,
) -> Dict[str, Any]:
    """Generate radial stress-distribution data for hub and shaft plots."""

    r_fit_mm = shaft_outer_diameter_mm / 2.0
    r_hub_outer_mm = hub_outer_diameter_mm / 2.0
    r_shaft_inner_mm = shaft_inner_diameter_mm / 2.0

    hub_radii_mm = [
        r_fit_mm + i * (r_hub_outer_mm - r_fit_mm) / max(n_hub_points - 1, 1)
        for i in range(n_hub_points)
    ]
    hub_radial: List[float] = []
    hub_hoop: List[float] = []

    if pressure_mpa > 0.0:
        k_h = pressure_mpa * r_fit_mm**2 / (r_hub_outer_mm**2 - r_fit_mm**2)
        for radius_mm in hub_radii_mm:
            hub_radial.append(k_h * (1.0 - r_hub_outer_mm**2 / radius_mm**2))
            hub_hoop.append(k_h * (1.0 + r_hub_outer_mm**2 / radius_mm**2))
    else:
        hub_radial = [0.0 for _ in hub_radii_mm]
        hub_hoop = [0.0 for _ in hub_radii_mm]

    shaft_payload: Dict[str, Any] = {
        "member_type": "solid" if shaft_inner_diameter_mm <= 0.0 else "hollow",
        "radii_mm": [],
        "radial_stress_mpa": [],
        "hoop_stress_mpa": [],
    }
    if shaft_inner_diameter_mm > 0.0:
        shaft_radii_mm = [
            r_shaft_inner_mm
            + i * (r_fit_mm - r_shaft_inner_mm) / max(n_shaft_points - 1, 1)
            for i in range(n_shaft_points)
        ]
        shaft_radial: List[float] = []
        shaft_hoop: List[float] = []
        if pressure_mpa > 0.0:
            k_s = -pressure_mpa * r_fit_mm**2 / (r_fit_mm**2 - r_shaft_inner_mm**2)
            for radius_mm in shaft_radii_mm:
                shaft_radial.append(k_s * (1.0 - r_shaft_inner_mm**2 / radius_mm**2))
                shaft_hoop.append(k_s * (1.0 + r_shaft_inner_mm**2 / radius_mm**2))
        else:
            shaft_radial = [0.0 for _ in shaft_radii_mm]
            shaft_hoop = [0.0 for _ in shaft_radii_mm]
        shaft_payload = {
            "member_type": "hollow",
            "radii_mm": shaft_radii_mm,
            "radial_stress_mpa": shaft_radial,
            "hoop_stress_mpa": shaft_hoop,
        }

    return {
        "hub": {
            "radii_mm": hub_radii_mm,
            "radial_stress_mpa": hub_radial,
            "hoop_stress_mpa": hub_hoop,
        },
        "shaft": shaft_payload,
    }


def _calculate_slip_capacities(
    pressure_mpa: float,
    shaft_outer_diameter_mm: float,
    fit_length_mm: float,
    friction_coefficient: float,
    applied_torque_nm: float,
    applied_axial_force_n: float,
) -> Dict[str, float]:
    """Calculate torque and axial slip capacities under uniform pressure."""

    if pressure_mpa <= 0.0 or friction_coefficient <= 0.0:
        return {
            "normal_force_n": 0.0,
            "torque_capacity_nm": 0.0,
            "axial_capacity_n": 0.0,
            "axial_capacity_kn": 0.0,
            "torque_slip_safety_factor": 0.0 if abs(applied_torque_nm) > 0.0 else float("inf"),
            "axial_slip_safety_factor": 0.0 if abs(applied_axial_force_n) > 0.0 else float("inf"),
            "torque_utilization_percent": float("inf") if abs(applied_torque_nm) > 0.0 else 0.0,
            "axial_utilization_percent": float("inf") if abs(applied_axial_force_n) > 0.0 else 0.0,
        }

    pressure_pa = pressure_mpa * 1e6
    d = shaft_outer_diameter_mm * 1e-3
    L = fit_length_mm * 1e-3
    contact_area = math.pi * d * L
    normal_force = pressure_pa * contact_area
    torque_capacity = normal_force * friction_coefficient * (d / 2.0)
    axial_capacity = normal_force * friction_coefficient

    torque_sf = (
        torque_capacity / abs(applied_torque_nm)
        if abs(applied_torque_nm) > 0.0
        else float("inf")
    )
    axial_sf = (
        axial_capacity / abs(applied_axial_force_n)
        if abs(applied_axial_force_n) > 0.0
        else float("inf")
    )

    return {
        "normal_force_n": normal_force,
        "torque_capacity_nm": torque_capacity,
        "axial_capacity_n": axial_capacity,
        "axial_capacity_kn": axial_capacity / 1000.0,
        "torque_slip_safety_factor": torque_sf,
        "axial_slip_safety_factor": axial_sf,
        "torque_utilization_percent": (
            100.0 * abs(applied_torque_nm) / torque_capacity
            if torque_capacity > 0.0 and abs(applied_torque_nm) > 0.0
            else 0.0
        ),
        "axial_utilization_percent": (
            100.0 * abs(applied_axial_force_n) / axial_capacity
            if axial_capacity > 0.0 and abs(applied_axial_force_n) > 0.0
            else 0.0
        ),
    }


def _thermal_adjusted_interference_mm(
    interference_mm: float,
    shaft_outer_diameter_mm: float,
    reference_temperature_c: float,
    operating_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> float:
    """Adjust diametral interference for differential free thermal expansion."""

    delta_t = operating_temperature_c - reference_temperature_c
    alpha_h = float(hub_material["thermal_expansion_e6_per_c"]) * 1e-6
    alpha_s = float(shaft_material["thermal_expansion_e6_per_c"]) * 1e-6
    thermal_relief = shaft_outer_diameter_mm * (alpha_h - alpha_s) * delta_t
    return interference_mm - thermal_relief


def _fit_loss_temperature_c(
    interference_mm: float,
    shaft_outer_diameter_mm: float,
    reference_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
) -> float | None:
    """Return the temperature where interference falls to zero, if finite."""

    delta_alpha = (
        float(hub_material["thermal_expansion_e6_per_c"])
        - float(shaft_material["thermal_expansion_e6_per_c"])
    ) * 1e-6
    if abs(delta_alpha) < 1e-14:
        return None

    return reference_temperature_c + (
        interference_mm / (shaft_outer_diameter_mm * delta_alpha)
    )


def _assembly_temperatures(
    nominal_interference_mm: float,
    maximum_interference_mm: float,
    assembly_temperature_c: float,
    assembly_clearance_mm: float,
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    reference_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    hub_max_assembly_temp_c: float | None,
    shaft_min_assembly_temp_c: float | None,
) -> Dict[str, Any]:
    """Compute thermal assembly temperatures for hub heating and shaft cooling."""

    required_total_change_mm = maximum_interference_mm + assembly_clearance_mm
    alpha_h = float(hub_material["thermal_expansion_e6_per_c"]) * 1e-6
    alpha_s = float(shaft_material["thermal_expansion_e6_per_c"]) * 1e-6
    d = shaft_outer_diameter_mm

    required_hub_heating_temp_c = None
    required_shaft_cooling_temp_c = None
    combined_hub_heating_temp_c = None
    combined_shaft_cooling_temp_c = None
    combined_delta_t_c = None
    user_delta_t_c = assembly_temperature_c - reference_temperature_c

    if alpha_h > 0.0:
        required_hub_heating_temp_c = reference_temperature_c + (
            required_total_change_mm / (alpha_h * d)
        )
    if alpha_s > 0.0:
        required_shaft_cooling_temp_c = reference_temperature_c - (
            required_total_change_mm / (alpha_s * d)
        )
    if alpha_h > 0.0 and alpha_s > 0.0:
        combined_delta_t_c = required_total_change_mm / ((alpha_h + alpha_s) * d)
        combined_hub_heating_temp_c = reference_temperature_c + combined_delta_t_c
        combined_shaft_cooling_temp_c = reference_temperature_c - combined_delta_t_c

    user_hub_growth_mm = d * alpha_h * user_delta_t_c
    nominal_hub_only_clearance_mm = user_hub_growth_mm - nominal_interference_mm
    maximum_hub_only_clearance_mm = user_hub_growth_mm - maximum_interference_mm
    nominal_hub_only_interference_mm = max(0.0, -nominal_hub_only_clearance_mm)
    maximum_hub_only_interference_mm = max(0.0, -maximum_hub_only_clearance_mm)
    nominal_hub_only_pressure_mpa = _calculate_interface_pressure_mpa(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        interference_mm=nominal_hub_only_interference_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )
    maximum_hub_only_pressure_mpa = _calculate_interface_pressure_mpa(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        interference_mm=maximum_hub_only_interference_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )

    warnings: List[str] = []
    status = "acceptable"

    if maximum_hub_only_clearance_mm < 0.0:
        status = "marginal"
        warnings.append(
            "The user-entered hub assembly temperature does not fully clear the maximum interference case for slip assembly."
        )

    if hub_max_assembly_temp_c is not None and required_hub_heating_temp_c is not None:
        if required_hub_heating_temp_c > hub_max_assembly_temp_c:
            status = "marginal"
            warnings.append(
                "Hub-only heating exceeds the user-defined maximum assembly temperature."
            )
    if shaft_min_assembly_temp_c is not None and required_shaft_cooling_temp_c is not None:
        if required_shaft_cooling_temp_c < shaft_min_assembly_temp_c:
            status = "marginal"
            warnings.append(
                "Shaft-only cooling goes below the user-defined minimum assembly temperature."
            )
    if required_hub_heating_temp_c is not None and required_hub_heating_temp_c > reference_temperature_c + 220.0:
        status = "marginal"
        warnings.append(
            "Hub-only heating requirement is very high; verify material temper and assembly practice."
        )
    if required_shaft_cooling_temp_c is not None and required_shaft_cooling_temp_c < reference_temperature_c - 120.0:
        status = "marginal"
        warnings.append(
            "Shaft-only cooling requirement is very low; verify handling practicality and condensation risk."
        )

    return {
        "governing_interference_mm": maximum_interference_mm,
        "required_total_diameter_change_mm": required_total_change_mm,
        "assembly_temperature_c": assembly_temperature_c,
        "required_hub_heating_temp_c": required_hub_heating_temp_c,
        "required_shaft_cooling_temp_c": required_shaft_cooling_temp_c,
        "combined_hub_heating_temp_c": combined_hub_heating_temp_c,
        "combined_shaft_cooling_temp_c": combined_shaft_cooling_temp_c,
        "combined_delta_t_c": combined_delta_t_c,
        "hub_only_nominal_clearance_mm": nominal_hub_only_clearance_mm,
        "hub_only_maximum_clearance_mm": maximum_hub_only_clearance_mm,
        "hub_only_nominal_interference_mm": nominal_hub_only_interference_mm,
        "hub_only_maximum_interference_mm": maximum_hub_only_interference_mm,
        "hub_only_nominal_pressure_mpa": nominal_hub_only_pressure_mpa,
        "hub_only_maximum_pressure_mpa": maximum_hub_only_pressure_mpa,
        "hub_only_nominal_feasible": nominal_hub_only_clearance_mm >= 0.0,
        "hub_only_maximum_feasible": maximum_hub_only_clearance_mm >= 0.0,
        "status": status,
        "warnings": warnings,
    }


def _evaluate_case(
    interference_mm: float,
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    friction_coefficient: float,
    applied_torque_nm: float,
    applied_axial_force_n: float,
    required_slip_sf: float,
    required_yield_sf: float,
    case_name: str,
    state_name: str,
) -> Dict[str, Any]:
    """Evaluate one fit state at a specified interference."""

    warnings: List[str] = []
    compliance = _calculate_compliance_data(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )
    pressure_mpa = _calculate_interface_pressure_mpa(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        interference_mm=interference_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )
    stresses = _calculate_member_stresses_mpa(
        pressure_mpa=pressure_mpa,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )
    capacities = _calculate_slip_capacities(
        pressure_mpa=pressure_mpa,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        fit_length_mm=fit_length_mm,
        friction_coefficient=friction_coefficient,
        applied_torque_nm=applied_torque_nm,
        applied_axial_force_n=applied_axial_force_n,
    )
    distributions = _generate_stress_distribution(
        pressure_mpa=pressure_mpa,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
    )

    fit_retained = pressure_mpa > 0.0 and interference_mm > 0.0
    hub_sf = float(stresses["hub"]["yield_safety_factor"])
    shaft_sf = float(stresses["shaft"]["yield_safety_factor"])
    torque_sf = float(capacities["torque_slip_safety_factor"])
    axial_sf = float(capacities["axial_slip_safety_factor"])
    min_yield_sf = min(hub_sf, shaft_sf)
    hub_inner = stresses["hub"]["surfaces"]["inner_surface"]
    hub_outer = stresses["hub"]["surfaces"]["outer_surface"]
    shaft_outer = stresses["shaft"]["surfaces"]["outer_surface"]
    shaft_inner = stresses["shaft"]["surfaces"]["inner_surface"]

    check_values: List[float] = [min_yield_sf]
    if abs(applied_torque_nm) > 0.0:
        check_values.append(torque_sf)
    if abs(applied_axial_force_n) > 0.0:
        check_values.append(axial_sf)
    min_check_sf = min(check_values) if check_values else float("inf")

    if not fit_retained:
        status = "unacceptable"
        warnings.append("Interference is zero or negative in this state, so the fit no longer retains contact pressure.")
    elif min_yield_sf < 1.0 or (
        abs(applied_torque_nm) > 0.0 and torque_sf < 1.0
    ) or (
        abs(applied_axial_force_n) > 0.0 and axial_sf < 1.0
    ):
        status = "unacceptable"
    elif min_yield_sf < required_yield_sf or (
        abs(applied_torque_nm) > 0.0 and torque_sf < required_slip_sf
    ) or (
        abs(applied_axial_force_n) > 0.0 and axial_sf < required_slip_sf
    ):
        status = "marginal"
    else:
        status = "acceptable"

    if hub_sf < required_yield_sf:
        warnings.append("Hub yield safety factor is below the requested threshold.")
    if shaft_sf < required_yield_sf:
        warnings.append("Shaft yield safety factor is below the requested threshold.")
    if abs(applied_torque_nm) > 0.0 and torque_sf < required_slip_sf:
        warnings.append("Torque slip safety factor is below the requested threshold.")
    if abs(applied_axial_force_n) > 0.0 and axial_sf < required_slip_sf:
        warnings.append("Axial slip safety factor is below the requested threshold.")

    return {
        "case_name": case_name,
        "state_name": state_name,
        "interference_mm": interference_mm,
        "fit_retained": fit_retained,
        "pressure_mpa": pressure_mpa,
        "members": stresses,
        "stress_distribution": distributions,
        "compliance": compliance,
        "hub_radial_stress_mpa": float(hub_inner["radial_stress_mpa"]),
        "hub_hoop_stress_mpa": float(hub_inner["hoop_stress_mpa"]),
        "hub_von_mises_mpa": float(hub_inner["von_mises_mpa"]),
        "hub_outer_radial_stress_mpa": float(hub_outer["radial_stress_mpa"]),
        "hub_outer_hoop_stress_mpa": float(hub_outer["hoop_stress_mpa"]),
        "hub_outer_von_mises_mpa": float(hub_outer["von_mises_mpa"]),
        "hub_max_von_mises_mpa": float(stresses["hub"]["max_von_mises_mpa"]),
        "hub_yield_safety_factor": hub_sf,
        "shaft_radial_stress_mpa": float(shaft_outer["radial_stress_mpa"]),
        "shaft_hoop_stress_mpa": float(shaft_outer["hoop_stress_mpa"]),
        "shaft_von_mises_mpa": float(shaft_outer["von_mises_mpa"]),
        "shaft_inner_radial_stress_mpa": (
            None if shaft_inner is None else float(shaft_inner["radial_stress_mpa"])
        ),
        "shaft_inner_hoop_stress_mpa": (
            None if shaft_inner is None else float(shaft_inner["hoop_stress_mpa"])
        ),
        "shaft_inner_von_mises_mpa": (
            None if shaft_inner is None else float(shaft_inner["von_mises_mpa"])
        ),
        "shaft_max_von_mises_mpa": float(stresses["shaft"]["max_von_mises_mpa"]),
        "shaft_yield_safety_factor": shaft_sf,
        "yield_safety_factor": min_yield_sf,
        "normal_force_n": float(capacities["normal_force_n"]),
        "torque_capacity_nm": float(capacities["torque_capacity_nm"]),
        "axial_capacity_n": float(capacities["axial_capacity_n"]),
        "axial_capacity_kn": float(capacities["axial_capacity_kn"]),
        "torque_slip_safety_factor": torque_sf,
        "axial_slip_safety_factor": axial_sf,
        "torque_utilization_percent": float(capacities["torque_utilization_percent"]),
        "axial_utilization_percent": float(capacities["axial_utilization_percent"]),
        "status": status,
        "warnings": warnings,
        "governing_safety_factor": min_check_sf,
    }


def _generate_interference_sweep(
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    nominal_interference_mm: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    friction_coefficient: float,
    reference_temperature_c: float,
    operating_temperature_c: float,
    sweep_min_interference_mm: float,
    sweep_max_interference_mm: float,
    n_sweep_points: int,
) -> Dict[str, List[float] | float]:
    """Generate plot-ready interference sweep data."""

    if n_sweep_points < 5:
        raise ValueError("n_sweep_points must be at least 5.")

    span_max = max(sweep_max_interference_mm, nominal_interference_mm * 1.4, 0.01)
    span_min = min(sweep_min_interference_mm, nominal_interference_mm * 0.4, nominal_interference_mm)
    if span_max <= span_min:
        span_max = span_min + max(0.01, nominal_interference_mm)

    interference_values = [
        span_min + i * (span_max - span_min) / (n_sweep_points - 1)
        for i in range(n_sweep_points)
    ]

    reference_pressure: List[float] = []
    operating_pressure: List[float] = []
    torque_capacity: List[float] = []
    axial_capacity_kn: List[float] = []
    hub_vm: List[float] = []
    shaft_vm: List[float] = []

    for interference_mm in interference_values:
        p_ref = _calculate_interface_pressure_mpa(
            shaft_outer_diameter_mm,
            hub_outer_diameter_mm,
            shaft_inner_diameter_mm,
            interference_mm,
            shaft_material,
            hub_material,
        )
        interference_op = _thermal_adjusted_interference_mm(
            interference_mm,
            shaft_outer_diameter_mm,
            reference_temperature_c,
            operating_temperature_c,
            shaft_material,
            hub_material,
        )
        p_op = _calculate_interface_pressure_mpa(
            shaft_outer_diameter_mm,
            hub_outer_diameter_mm,
            shaft_inner_diameter_mm,
            max(0.0, interference_op),
            shaft_material,
            hub_material,
        )
        stresses = _calculate_member_stresses_mpa(
            pressure_mpa=p_ref,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            shaft_material=shaft_material,
            hub_material=hub_material,
        )
        capacities = _calculate_slip_capacities(
            pressure_mpa=p_op,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            friction_coefficient=friction_coefficient,
            applied_torque_nm=0.0,
            applied_axial_force_n=0.0,
        )
        reference_pressure.append(p_ref)
        operating_pressure.append(p_op)
        torque_capacity.append(float(capacities["torque_capacity_nm"]))
        axial_capacity_kn.append(float(capacities["axial_capacity_kn"]))
        hub_vm.append(float(stresses["hub"]["max_von_mises_mpa"]))
        shaft_vm.append(float(stresses["shaft"]["max_von_mises_mpa"]))

    return {
        "interference_mm": interference_values,
        "reference_pressure_mpa": reference_pressure,
        "operating_pressure_mpa": operating_pressure,
        "torque_capacity_nm": torque_capacity,
        "axial_capacity_kn": axial_capacity_kn,
        "hub_von_mises_mpa": hub_vm,
        "shaft_von_mises_mpa": shaft_vm,
        "nominal_interference_mm": nominal_interference_mm,
    }


def _generate_temperature_sweep(
    nominal_interference_mm: float,
    shaft_outer_diameter_mm: float,
    shaft_inner_diameter_mm: float,
    hub_outer_diameter_mm: float,
    reference_temperature_c: float,
    operating_temperature_c: float,
    shaft_material: Dict[str, float | str],
    hub_material: Dict[str, float | str],
    n_points: int = 61,
) -> Dict[str, List[float] | float | None]:
    """Generate plot-ready operating temperature sweep data."""

    fit_loss_temperature = _fit_loss_temperature_c(
        interference_mm=nominal_interference_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        reference_temperature_c=reference_temperature_c,
        shaft_material=shaft_material,
        hub_material=hub_material,
    )

    temp_candidates = [reference_temperature_c - 80.0, operating_temperature_c - 20.0]
    temp_high_candidates = [reference_temperature_c + 140.0, operating_temperature_c + 20.0]
    if fit_loss_temperature is not None:
        temp_candidates.append(fit_loss_temperature - 25.0)
        temp_high_candidates.append(fit_loss_temperature + 25.0)
    t_min = min(temp_candidates)
    t_max = max(temp_high_candidates)
    if t_max <= t_min:
        t_max = t_min + 50.0

    temperature_values = [
        t_min + i * (t_max - t_min) / (n_points - 1)
        for i in range(n_points)
    ]
    operating_interference: List[float] = []
    operating_pressure: List[float] = []

    for temperature_c in temperature_values:
        interference_op = _thermal_adjusted_interference_mm(
            interference_mm=nominal_interference_mm,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            reference_temperature_c=reference_temperature_c,
            operating_temperature_c=temperature_c,
            shaft_material=shaft_material,
            hub_material=hub_material,
        )
        pressure_op = _calculate_interface_pressure_mpa(
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            interference_mm=max(0.0, interference_op),
            shaft_material=shaft_material,
            hub_material=hub_material,
        )
        operating_interference.append(interference_op)
        operating_pressure.append(pressure_op)

    return {
        "temperature_c": temperature_values,
        "operating_interference_mm": operating_interference,
        "operating_pressure_mpa": operating_pressure,
        "fit_loss_temperature_c": fit_loss_temperature,
    }


def analyze_interference_fit(
    shaft_outer_diameter_mm: float,
    hub_outer_diameter_mm: float,
    fit_length_mm: float,
    shaft_inner_diameter_mm: float = 0.0,
    interference_nominal_mm: float = 0.03,
    interference_min_mm: float | None = None,
    interference_max_mm: float | None = None,
    shaft_material: str = "steel",
    hub_material: str = "steel",
    shaft_youngs_modulus_mpa: float = 200000.0,
    shaft_poisson_ratio: float = 0.30,
    shaft_yield_strength_mpa: float = 450.0,
    shaft_thermal_expansion_e6_per_c: float = 12.0,
    hub_youngs_modulus_mpa: float = 200000.0,
    hub_poisson_ratio: float = 0.30,
    hub_yield_strength_mpa: float = 350.0,
    hub_thermal_expansion_e6_per_c: float = 12.0,
    friction_coefficient: float = 0.15,
    reference_temperature_c: float = 20.0,
    assembly_temperature_c: float = 20.0,
    operating_temperature_c: float = 20.0,
    assembly_clearance_mm: float = 0.01,
    applied_torque_nm: float = 0.0,
    applied_axial_force_n: float = 0.0,
    required_slip_sf: float = 1.5,
    required_yield_sf: float = 1.2,
    hub_max_assembly_temp_c: float | None = None,
    shaft_min_assembly_temp_c: float | None = None,
    sweep_min_interference_mm: float = 0.0,
    sweep_max_interference_mm: float = 0.08,
    n_sweep_points: int = 81,
) -> Dict[str, Any]:
    r"""
    Analyze a cylindrical press fit / shrink fit between a shaft and a hub.

    This function evaluates elastic interference-fit pressure, Lamé stresses,
    slip capacity, operating-temperature interference loss, and thermal
    assembly temperatures for a straight cylindrical shaft-hub joint.

    The pressure model follows the classical Shigley-style thick-cylinder
    interference-fit treatment in which diametral interference is the product
    of interface pressure, fit diameter, and the combined radial compliances of
    the hub and shaft.

    ---Parameters---
    shaft_outer_diameter_mm : float
        Shaft outside diameter at the fit, in millimeters.
    hub_outer_diameter_mm : float
        Hub outside diameter, in millimeters. Must exceed the shaft diameter.
    fit_length_mm : float
        Axial engagement length of the fit, in millimeters.
    shaft_inner_diameter_mm : float
        Shaft inside diameter, in millimeters. Use 0 for a solid shaft.
    interference_nominal_mm : float
        Nominal diametral interference at the reference temperature, in mm.
    interference_min_mm : float
        Minimum diametral interference, in mm. If omitted, nominal is used.
    interference_max_mm : float
        Maximum diametral interference, in mm. If omitted, nominal is used.
    shaft_material : str
        Shaft material preset key, or `custom` to use the explicit shaft
        material property inputs.
    hub_material : str
        Hub material preset key, or `custom` to use the explicit hub material
        property inputs.
    shaft_youngs_modulus_mpa : float
        Custom shaft Young's modulus, in MPa, used when `shaft_material` is
        `custom`.
    shaft_poisson_ratio : float
        Custom shaft Poisson ratio, used when `shaft_material` is `custom`.
    shaft_yield_strength_mpa : float
        Custom shaft yield strength, in MPa, used when `shaft_material` is
        `custom`.
    shaft_thermal_expansion_e6_per_c : float
        Custom shaft thermal expansion coefficient, in microstrain per degree C,
        used when `shaft_material` is `custom`.
    hub_youngs_modulus_mpa : float
        Custom hub Young's modulus, in MPa, used when `hub_material` is
        `custom`.
    hub_poisson_ratio : float
        Custom hub Poisson ratio, used when `hub_material` is `custom`.
    hub_yield_strength_mpa : float
        Custom hub yield strength, in MPa, used when `hub_material` is
        `custom`.
    hub_thermal_expansion_e6_per_c : float
        Custom hub thermal expansion coefficient, in microstrain per degree C,
        used when `hub_material` is `custom`.
    friction_coefficient : float
        Friction coefficient used for slip-capacity calculations.
    reference_temperature_c : float
        Reference temperature at which the nominal interference is defined.
    assembly_temperature_c : float
        User-selected assembly temperature used for the bulk same-temperature
        assembly state and for hub-only shrink-fit feasibility reporting.
    operating_temperature_c : float
        Bulk operating temperature used for differential thermal expansion.
    assembly_clearance_mm : float
        Extra temporary diametral clearance required for slip assembly, in mm.
    applied_torque_nm : float
        Applied service torque, in N·m, for torque slip safety factor checks.
    applied_axial_force_n : float
        Applied axial service load, in N, for axial slip safety factor checks.
    required_slip_sf : float
        Required slip safety factor for torque and axial load checks.
    required_yield_sf : float
        Required yield safety factor for shaft and hub stress checks.
    hub_max_assembly_temp_c : float
        Optional maximum acceptable hub heating temperature, in deg C.
    shaft_min_assembly_temp_c : float
        Optional minimum acceptable shaft cooling temperature, in deg C.
    sweep_min_interference_mm : float
        Lower bound for the interference sensitivity sweep, in mm.
    sweep_max_interference_mm : float
        Upper bound for the interference sensitivity sweep, in mm.
    n_sweep_points : float
        Number of points in the interference sensitivity sweep.

    ---Returns---
    reference_case : dict
        Nominal reference-temperature case with pressure, stresses, and capacity.
    assembly_case : dict
        Nominal same-temperature assembly case at `assembly_temperature_c`.
    operating_case : dict
        Nominal operating-temperature case with pressure, stresses, and capacity.
    nominal_case : dict
        Nominal interference results for both reference and operating states.
    minimum_case : dict
        Minimum interference results for both reference and operating states.
    maximum_case : dict
        Maximum interference results for both reference and operating states.
    range_cases : dict
        Dictionary of minimum, nominal, and maximum fit cases.
    assembly : dict
        Thermal assembly temperatures and assembly-status warnings.
    compliance : dict
        Shigley-style geometry and compliance factors for the nominal fit.
    geometry : dict
        Key geometric quantities used by the UI and visualizations.
    state_temperatures_c : dict
        Reference, assembly, and operating temperatures used for the analysis.
    sweep_data : dict
        Plot-ready interference and temperature sweep arrays.
    status : str
        Overall assessment: acceptable, marginal, or unacceptable.
    governing_mode : str
        Governing limiting condition for the overall status.
    warnings : list
        Aggregate warning messages from the analysis.
    recommendations : list
        Action-oriented suggestions derived from the governing checks.
    shaft_material_name : str
        Resolved shaft material display name.
    hub_material_name : str
        Resolved hub material display name.
    fit_loss_temperature_c : float
        Temperature where nominal operating interference becomes zero, if finite.
    minimum_operating_pressure_mpa : float
        Lowest operating pressure across the min/nom/max interference cases.
    maximum_reference_pressure_mpa : float
        Highest reference pressure across the min/nom/max interference cases.
    minimum_yield_safety_factor : float
        Lowest shaft-or-hub yield safety factor across all states.
    minimum_torque_slip_safety_factor : float
        Lowest torque slip safety factor across operating states.
    minimum_axial_slip_safety_factor : float
        Lowest axial slip safety factor across operating states.
    subst_interface_pressure_mpa : str
        Substituted equation string for nominal reference interface pressure.
    subst_operating_interference_mm : str
        Substituted equation string for nominal operating interference.
    subst_torque_capacity_nm : str
        Substituted equation string for nominal operating torque capacity.
    subst_hub_von_mises_mpa : str
        Substituted equation string for nominal hub von Mises stress.

    ---LaTeX---
    \delta_d = p d \left(C_h + C_s\right)
    \delta_{d,op} = \delta_{d,ref} - d \left(\alpha_h - \alpha_s\right)\Delta T
    N = p \pi d L
    T_{max} = \mu N \frac{d}{2}
    F_{ax,max} = \mu N
    \sigma_{vm} = \sqrt{\sigma_\theta^2 - \sigma_\theta \sigma_r + \sigma_r^2}
    """

    _validate_positive("shaft_outer_diameter_mm", shaft_outer_diameter_mm)
    _validate_positive("hub_outer_diameter_mm", hub_outer_diameter_mm)
    _validate_positive("fit_length_mm", fit_length_mm)
    _validate_nonnegative("shaft_inner_diameter_mm", shaft_inner_diameter_mm)
    _validate_nonnegative("friction_coefficient", friction_coefficient)
    _validate_nonnegative("assembly_clearance_mm", assembly_clearance_mm)
    _validate_nonnegative("applied_torque_nm", abs(applied_torque_nm))
    _validate_nonnegative("applied_axial_force_n", abs(applied_axial_force_n))
    _validate_positive("required_slip_sf", required_slip_sf)
    _validate_positive("required_yield_sf", required_yield_sf)
    _validate_nonnegative("sweep_min_interference_mm", sweep_min_interference_mm)
    _validate_nonnegative("sweep_max_interference_mm", sweep_max_interference_mm)

    if hub_outer_diameter_mm <= shaft_outer_diameter_mm:
        raise ValueError("hub_outer_diameter_mm must be greater than shaft_outer_diameter_mm.")
    if shaft_inner_diameter_mm >= shaft_outer_diameter_mm:
        raise ValueError("shaft_inner_diameter_mm must be less than shaft_outer_diameter_mm.")
    if sweep_max_interference_mm < sweep_min_interference_mm:
        raise ValueError("sweep_max_interference_mm must be >= sweep_min_interference_mm.")

    interference_min_mm, interference_nominal_mm, interference_max_mm = _coerce_range(
        interference_nominal_mm,
        interference_min_mm,
        interference_max_mm,
    )

    shaft_props = _resolve_material(
        component_label="shaft",
        material_key=shaft_material,
        youngs_modulus_mpa=shaft_youngs_modulus_mpa,
        poisson_ratio=shaft_poisson_ratio,
        yield_strength_mpa=shaft_yield_strength_mpa,
        thermal_expansion_e6_per_c=shaft_thermal_expansion_e6_per_c,
    )
    hub_props = _resolve_material(
        component_label="hub",
        material_key=hub_material,
        youngs_modulus_mpa=hub_youngs_modulus_mpa,
        poisson_ratio=hub_poisson_ratio,
        yield_strength_mpa=hub_yield_strength_mpa,
        thermal_expansion_e6_per_c=hub_thermal_expansion_e6_per_c,
    )

    case_inputs = {
        "minimum": interference_min_mm,
        "nominal": interference_nominal_mm,
        "maximum": interference_max_mm,
    }
    range_cases: Dict[str, Dict[str, Any]] = {}
    all_warnings: List[str] = []

    for label, reference_interference in case_inputs.items():
        assembly_interference = _thermal_adjusted_interference_mm(
            interference_mm=reference_interference,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            reference_temperature_c=reference_temperature_c,
            operating_temperature_c=assembly_temperature_c,
            shaft_material=shaft_props,
            hub_material=hub_props,
        )
        operating_interference = _thermal_adjusted_interference_mm(
            interference_mm=reference_interference,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            reference_temperature_c=reference_temperature_c,
            operating_temperature_c=operating_temperature_c,
            shaft_material=shaft_props,
            hub_material=hub_props,
        )
        reference_case = _evaluate_case(
            interference_mm=reference_interference,
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_props,
            hub_material=hub_props,
            friction_coefficient=friction_coefficient,
            applied_torque_nm=applied_torque_nm,
            applied_axial_force_n=applied_axial_force_n,
            required_slip_sf=required_slip_sf,
            required_yield_sf=required_yield_sf,
            case_name=label,
            state_name="reference",
        )
        assembly_case = _evaluate_case(
            interference_mm=max(0.0, assembly_interference),
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_props,
            hub_material=hub_props,
            friction_coefficient=friction_coefficient,
            applied_torque_nm=applied_torque_nm,
            applied_axial_force_n=applied_axial_force_n,
            required_slip_sf=required_slip_sf,
            required_yield_sf=required_yield_sf,
            case_name=label,
            state_name="assembly",
        )
        assembly_case["unclamped_interference_mm"] = assembly_interference
        operating_case = _evaluate_case(
            interference_mm=max(0.0, operating_interference),
            shaft_outer_diameter_mm=shaft_outer_diameter_mm,
            shaft_inner_diameter_mm=shaft_inner_diameter_mm,
            hub_outer_diameter_mm=hub_outer_diameter_mm,
            fit_length_mm=fit_length_mm,
            shaft_material=shaft_props,
            hub_material=hub_props,
            friction_coefficient=friction_coefficient,
            applied_torque_nm=applied_torque_nm,
            applied_axial_force_n=applied_axial_force_n,
            required_slip_sf=required_slip_sf,
            required_yield_sf=required_yield_sf,
            case_name=label,
            state_name="operating",
        )
        operating_case["unclamped_interference_mm"] = operating_interference

        range_cases[label] = {
            "reference": reference_case,
            "assembly": assembly_case,
            "operating": operating_case,
        }
        all_warnings.extend(reference_case["warnings"])
        all_warnings.extend(assembly_case["warnings"])
        all_warnings.extend(operating_case["warnings"])

    assembly = _assembly_temperatures(
        nominal_interference_mm=interference_nominal_mm,
        maximum_interference_mm=interference_max_mm,
        assembly_temperature_c=assembly_temperature_c,
        assembly_clearance_mm=assembly_clearance_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        reference_temperature_c=reference_temperature_c,
        shaft_material=shaft_props,
        hub_material=hub_props,
        hub_max_assembly_temp_c=hub_max_assembly_temp_c,
        shaft_min_assembly_temp_c=shaft_min_assembly_temp_c,
    )
    all_warnings.extend(assembly["warnings"])

    nominal_case = range_cases["nominal"]
    minimum_case = range_cases["minimum"]
    maximum_case = range_cases["maximum"]
    reference_case = nominal_case["reference"]
    assembly_case = nominal_case["assembly"]
    operating_case = nominal_case["operating"]

    fit_loss_temperature_c = _fit_loss_temperature_c(
        interference_mm=interference_nominal_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        reference_temperature_c=reference_temperature_c,
        shaft_material=shaft_props,
        hub_material=hub_props,
    )

    all_state_cases = [
        range_cases["minimum"]["reference"],
        range_cases["minimum"]["assembly"],
        range_cases["minimum"]["operating"],
        range_cases["nominal"]["reference"],
        range_cases["nominal"]["assembly"],
        range_cases["nominal"]["operating"],
        range_cases["maximum"]["reference"],
        range_cases["maximum"]["assembly"],
        range_cases["maximum"]["operating"],
    ]

    minimum_yield_safety_factor = min(case["yield_safety_factor"] for case in all_state_cases)
    minimum_operating_pressure_mpa = min(
        range_cases[label]["operating"]["pressure_mpa"] for label in ("minimum", "nominal", "maximum")
    )
    maximum_reference_pressure_mpa = max(
        range_cases[label]["reference"]["pressure_mpa"] for label in ("minimum", "nominal", "maximum")
    )

    minimum_torque_slip_safety_factor = min(
        range_cases[label]["operating"]["torque_slip_safety_factor"]
        for label in ("minimum", "nominal", "maximum")
    )
    minimum_axial_slip_safety_factor = min(
        range_cases[label]["operating"]["axial_slip_safety_factor"]
        for label in ("minimum", "nominal", "maximum")
    )

    governing_candidates: List[tuple[float, str]] = []
    if minimum_case["operating"]["fit_retained"]:
        governing_candidates.append((minimum_yield_safety_factor / required_yield_sf, "yield margin"))
    else:
        governing_candidates.append((0.0, "fit loss at minimum operating interference"))
    governing_candidates.append(
        (minimum_yield_safety_factor / required_yield_sf, "yield margin")
    )
    if abs(applied_torque_nm) > 0.0:
        governing_candidates.append(
            (
                minimum_torque_slip_safety_factor / required_slip_sf,
                "torque slip at operating condition",
            )
        )
    if abs(applied_axial_force_n) > 0.0:
        governing_candidates.append(
            (
                minimum_axial_slip_safety_factor / required_slip_sf,
                "axial slip at operating condition",
            )
        )
    if assembly["status"] != "acceptable":
        governing_candidates.append((0.95, "assembly temperature practicality"))

    governing_ratio, governing_mode = min(governing_candidates, key=lambda item: item[0])

    if not minimum_case["operating"]["fit_retained"]:
        status = "unacceptable"
    elif any(case["yield_safety_factor"] < 1.0 for case in all_state_cases):
        status = "unacceptable"
    elif abs(applied_torque_nm) > 0.0 and minimum_torque_slip_safety_factor < 1.0:
        status = "unacceptable"
    elif abs(applied_axial_force_n) > 0.0 and minimum_axial_slip_safety_factor < 1.0:
        status = "unacceptable"
    elif (
        minimum_yield_safety_factor < required_yield_sf
        or (abs(applied_torque_nm) > 0.0 and minimum_torque_slip_safety_factor < required_slip_sf)
        or (abs(applied_axial_force_n) > 0.0 and minimum_axial_slip_safety_factor < required_slip_sf)
        or assembly["status"] != "acceptable"
    ):
        status = "marginal"
    else:
        status = "acceptable"

    recommendations: List[str] = []
    if not minimum_case["operating"]["fit_retained"]:
        recommendations.append(
            "Increase minimum interference, reduce operating temperature, or use closer thermal expansion coefficients to retain fit."
        )
    if minimum_yield_safety_factor < required_yield_sf:
        recommendations.append(
            "Reduce maximum interference, increase hub wall thickness, or use stronger shaft/hub materials to improve yield margin."
        )
    if abs(applied_torque_nm) > 0.0 and minimum_torque_slip_safety_factor < required_slip_sf:
        recommendations.append(
            "Increase fit length, interference, or friction coefficient to improve torque capacity."
        )
    if abs(applied_axial_force_n) > 0.0 and minimum_axial_slip_safety_factor < required_slip_sf:
        recommendations.append(
            "Increase fit length, interference, or friction coefficient to improve axial slip margin."
        )
    if assembly["status"] != "acceptable":
        recommendations.append(
            "Review thermal assembly strategy; combined heating and cooling may be more practical than a single-sided temperature change."
        )
    if hub_outer_diameter_mm / shaft_outer_diameter_mm < 1.3:
        all_warnings.append(
            "Hub OD is only modestly larger than fit diameter; thin-wall behavior may increase sensitivity to assumptions."
        )

    sweep_data = _generate_interference_sweep(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        fit_length_mm=fit_length_mm,
        nominal_interference_mm=interference_nominal_mm,
        shaft_material=shaft_props,
        hub_material=hub_props,
        friction_coefficient=friction_coefficient,
        reference_temperature_c=reference_temperature_c,
        operating_temperature_c=operating_temperature_c,
        sweep_min_interference_mm=sweep_min_interference_mm,
        sweep_max_interference_mm=sweep_max_interference_mm,
        n_sweep_points=int(n_sweep_points),
    )
    sweep_data["temperature_effect"] = _generate_temperature_sweep(
        nominal_interference_mm=interference_nominal_mm,
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        reference_temperature_c=reference_temperature_c,
        operating_temperature_c=operating_temperature_c,
        shaft_material=shaft_props,
        hub_material=hub_props,
    )
    sweep_data["interference_band"] = {
        "minimum_mm": interference_min_mm,
        "nominal_mm": interference_nominal_mm,
        "maximum_mm": interference_max_mm,
    }

    d = shaft_outer_diameter_mm
    compliance = _calculate_compliance_data(
        shaft_outer_diameter_mm=shaft_outer_diameter_mm,
        hub_outer_diameter_mm=hub_outer_diameter_mm,
        shaft_inner_diameter_mm=shaft_inner_diameter_mm,
        shaft_material=shaft_props,
        hub_material=hub_props,
    )
    denominator_m_per_pa = float(compliance["total_term_m_per_pa"])
    operating_interference_nominal = float(operating_case["unclamped_interference_mm"])

    subst_interface_pressure_mpa = (
        f"\\delta_d = p d (C_h + C_s) \\Rightarrow "
        f"p = \\frac{{{interference_nominal_mm:.4f}\\times10^{{-3}}}}{{{denominator_m_per_pa:.4e}}}"
        f" = {reference_case['pressure_mpa']:.2f}\\text{{ MPa}}"
    )
    subst_operating_interference_mm = (
        f"\\delta_{{d,op}} = \\delta_{{d,ref}} - d(\\alpha_h-\\alpha_s)\\Delta T"
        f" = {interference_nominal_mm:.4f} - {d:.1f}({float(hub_props['thermal_expansion_e6_per_c']):.2f}"
        f" - {float(shaft_props['thermal_expansion_e6_per_c']):.2f})\\times10^{{-6}}"
        f" \\times ({operating_temperature_c:.1f} - {reference_temperature_c:.1f})"
        f" = {operating_interference_nominal:.4f}\\text{{ mm}}"
    )
    subst_torque_capacity_nm = (
        f"T_{{max}} = \\mu p \\pi d L \\frac{{d}}{{2}}"
        f" = {friction_coefficient:.3f} \\times {operating_case['pressure_mpa']:.2f}\\times10^6"
        f" \\times \\pi \\times {d/1000:.4f} \\times {fit_length_mm/1000:.4f}"
        f" \\times \\frac{{{d/1000:.4f}}}{{2}}"
        f" = {operating_case['torque_capacity_nm']:.1f}\\text{{ N·m}}"
    )
    subst_hub_von_mises_mpa = (
        f"\\sigma_{{vm}} = \\sqrt{{\\sigma_\\theta^2 - \\sigma_\\theta\\sigma_r + \\sigma_r^2}}"
        f" = \\sqrt{{{reference_case['hub_hoop_stress_mpa']:.2f}^2 - "
        f"{reference_case['hub_hoop_stress_mpa']:.2f}({reference_case['hub_radial_stress_mpa']:.2f}) + "
        f"{reference_case['hub_radial_stress_mpa']:.2f}^2}}"
        f" = {reference_case['hub_von_mises_mpa']:.2f}\\text{{ MPa}}"
    )

    deduped_warnings = list(dict.fromkeys(all_warnings))
    deduped_recommendations = list(dict.fromkeys(recommendations))

    return {
        "reference_case": reference_case,
        "assembly_case": assembly_case,
        "operating_case": operating_case,
        "nominal_case": nominal_case,
        "minimum_case": minimum_case,
        "maximum_case": maximum_case,
        "range_cases": range_cases,
        "assembly": assembly,
        "compliance": compliance,
        "geometry": {
            "shaft_outer_diameter_mm": shaft_outer_diameter_mm,
            "shaft_inner_diameter_mm": shaft_inner_diameter_mm,
            "hub_outer_diameter_mm": hub_outer_diameter_mm,
            "fit_length_mm": fit_length_mm,
            "shaft_outer_radius_mm": shaft_outer_diameter_mm / 2.0,
            "shaft_inner_radius_mm": shaft_inner_diameter_mm / 2.0,
            "hub_outer_radius_mm": hub_outer_diameter_mm / 2.0,
            "hub_to_shaft_diameter_ratio": hub_outer_diameter_mm / shaft_outer_diameter_mm,
            "shaft_member_type": "solid"
            if shaft_inner_diameter_mm <= 0.0
            else "hollow",
        },
        "materials": {
            "shaft": shaft_props,
            "hub": hub_props,
        },
        "state_temperatures_c": {
            "reference": reference_temperature_c,
            "assembly": assembly_temperature_c,
            "operating": operating_temperature_c,
        },
        "stress_distribution_cases": {
            "reference": reference_case["stress_distribution"],
            "assembly": assembly_case["stress_distribution"],
            "operating": operating_case["stress_distribution"],
        },
        "sweep_data": sweep_data,
        "status": status,
        "governing_mode": governing_mode,
        "warnings": deduped_warnings,
        "recommendations": deduped_recommendations,
        "shaft_material_name": str(shaft_props["display_name"]),
        "hub_material_name": str(hub_props["display_name"]),
        "fit_loss_temperature_c": fit_loss_temperature_c,
        "minimum_operating_pressure_mpa": minimum_operating_pressure_mpa,
        "maximum_reference_pressure_mpa": maximum_reference_pressure_mpa,
        "minimum_yield_safety_factor": minimum_yield_safety_factor,
        "minimum_torque_slip_safety_factor": minimum_torque_slip_safety_factor,
        "minimum_axial_slip_safety_factor": minimum_axial_slip_safety_factor,
        "subst_interface_pressure_mpa": subst_interface_pressure_mpa,
        "subst_operating_interference_mm": subst_operating_interference_mm,
        "subst_torque_capacity_nm": subst_torque_capacity_nm,
        "subst_hub_von_mises_mpa": subst_hub_von_mises_mpa,
    }
