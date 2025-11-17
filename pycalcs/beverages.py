"""
Calculation helpers for beverage serving temperatures.
"""

from __future__ import annotations

import math


_CUP_MATERIAL_COEFFICIENTS: dict[str, float] = {
    "double_walled": 0.028,
    "ceramic": 0.065,
    "glass": 0.085,
    "paper": 0.11,
}

_PREFERENCE_PROFILES: dict[str, dict[str, float]] = {
    "balanced": {
        "flavor_center": 59.0,
        "flavor_sigma": 4.0,
        "flavor_weight": 0.38,
        "aroma_weight": 0.2,
        "safety_weight": 0.22,
        "body_weight": 0.2,
    },
    "sweet": {
        "flavor_center": 56.5,
        "flavor_sigma": 3.2,
        "flavor_weight": 0.42,
        "aroma_weight": 0.16,
        "safety_weight": 0.22,
        "body_weight": 0.2,
    },
    "hot": {
        "flavor_center": 61.5,
        "flavor_sigma": 4.5,
        "flavor_weight": 0.32,
        "aroma_weight": 0.28,
        "safety_weight": 0.2,
        "body_weight": 0.2,
    },
}


def compute_optimal_coffee_serving_temperature(
    initial_temp_c: float,
    ambient_temp_c: float,
    beverage_mass_g: float,
    cup_material: str,
    preference_profile: str,
) -> dict[str, float | str]:
    """
    Estimate an optimal coffee serving temperature and wait time using a
    comfort-flavour model with Newtonian cooling.

    The method samples the utility of beverage temperatures between the thermal
    comfort and burn-risk thresholds (50–70 °C) using a weighted score that
    combines flavour clarity, perceived aroma, body, and oral safety. The
    highest-scoring temperature is reported alongside the minimum wait time
    required for the initially brewed coffee to cool to that level according to
    Newton's law of cooling.

    ---Parameters---
    initial_temp_c : float
        Brew temperature of the coffee in degrees Celsius (°C). Must be greater
        than ``ambient_temp_c`` and between 60 and 98 °C for typical brewing.
    ambient_temp_c : float
        Surrounding ambient temperature in degrees Celsius (°C). Must be between
        0 and 45 °C.
    beverage_mass_g : float
        Mass of the beverage in grams (g). For filter coffee a 240 ml mug is
        approximately 240 g. Must be greater than zero.
    cup_material : str
        Identifier for the vessel. Accepted values are ``"double_walled"``,
        ``"ceramic"``, ``"glass"``, and ``"paper"``.
    preference_profile : str
        Taste profile weighting. Accepted values are ``"balanced"``, ``"sweet"``,
        and ``"hot"``.

    ---Returns---
    optimal_temp_c : float
        Temperature that maximises the composite enjoyment score, expressed in
        degrees Celsius (°C).
    wait_time_min : float
        Minutes required for the drink to cool from ``initial_temp_c`` to
        ``optimal_temp_c`` under Newtonian cooling.
    comfort_score : float
        Normalised enjoyment score (0–100) at ``optimal_temp_c``.
    cooling_constant_per_min : float
        Effective cooling constant k in min⁻¹ derived from the cup and volume.
    subst_wait_time_min : str
        Symbolic substitution showing the cooling-time calculation.
    subst_optimal_temp_c : str
        Note describing the temperature sampling step that produced
        ``optimal_temp_c``.

    ---LaTeX---
    T(t) = T_{amb} + \\left(T_0 - T_{amb}\\right) e^{-k t} \\\\
    U(T) = w_f \\exp\\left(-\\frac{(T - T_f)^2}{2 \\sigma_f^2}\\right)
         + w_a \\left(1 - e^{-b (T - T_a)}\\right)
         + \\frac{w_s}{1 + e^{c (T - T_s)}}
         + \\frac{w_b}{1 + e^{d (T_b - T)}} \\\\
    t^* = -\\frac{1}{k} \\ln \\left( \\frac{T^* - T_{amb}}{T_0 - T_{amb}} \\right)

    ---References---
    Brown, R. J., & Diller, K. R. (2008). Calculated safe hot beverage
        temperature. Journal of Food Engineering, 87(2), 230–236.
    Battista, R. A., Connelly, C. D., & Schmidt, R. J. (1980). Palatability of
        coffee beverages. Journal of Food Science, 45(6), 1616–1618.
    Spence, C. (2017). Hot beverages and safe drinking temperatures. International
        Journal of Gastronomy and Food Science, 7, 5–9.
    """
    if initial_temp_c <= ambient_temp_c:
        raise ValueError("Initial coffee temperature must exceed the ambient temperature.")
    if not 0 <= ambient_temp_c <= 45:
        raise ValueError("Ambient temperature must be within a realistic range of 0–45 °C.")
    if not 60 <= initial_temp_c <= 98:
        raise ValueError("Initial coffee temperature must fall between 60 and 98 °C.")
    if beverage_mass_g <= 0:
        raise ValueError("Beverage mass must be greater than zero.")
    cup_key = cup_material.lower()
    if cup_key not in _CUP_MATERIAL_COEFFICIENTS:
        raise ValueError(f"Cup material '{cup_material}' is not recognised.")
    profile_key = preference_profile.lower()
    if profile_key not in _PREFERENCE_PROFILES:
        raise ValueError(f"Preference profile '{preference_profile}' is not recognised.")

    base_k = _CUP_MATERIAL_COEFFICIENTS[cup_key]
    mass_scale = (240.0 / beverage_mass_g) ** 0.55
    cooling_constant = base_k * mass_scale

    flavour_center = _PREFERENCE_PROFILES[profile_key]["flavor_center"]
    flavour_sigma = _PREFERENCE_PROFILES[profile_key]["flavor_sigma"]
    flavour_weight = _PREFERENCE_PROFILES[profile_key]["flavor_weight"]
    aroma_weight = _PREFERENCE_PROFILES[profile_key]["aroma_weight"]
    safety_weight = _PREFERENCE_PROFILES[profile_key]["safety_weight"]
    body_weight = _PREFERENCE_PROFILES[profile_key]["body_weight"]

    def utility(temp_c: float) -> float:
        flavour = math.exp(-((temp_c - flavour_center) ** 2) / (2 * flavour_sigma**2))
        aroma = 1.0 - math.exp(-0.45 * max(temp_c - 52.0, 0.0))
        safety = 1.0 / (1.0 + math.exp(0.45 * (temp_c - 63.0)))
        body = 1.0 / (1.0 + math.exp(0.6 * (55.0 - temp_c)))
        return (
            flavour_weight * flavour
            + aroma_weight * aroma
            + safety_weight * safety
            + body_weight * body
        )

    search_min = max(50.0, ambient_temp_c + 5.0)
    search_max = min(70.0, initial_temp_c)
    if search_max <= search_min:
        raise ValueError("Search interval for optimal temperature is invalid.")

    best_temp = search_min
    best_score = float("-inf")
    for idx in range(0, int((search_max - search_min) * 10) + 1):
        temp = search_min + idx * 0.1
        score = utility(temp)
        if score > best_score:
            best_score = score
            best_temp = temp

    numerator = best_temp - ambient_temp_c
    denominator = initial_temp_c - ambient_temp_c
    if numerator <= 0 or denominator <= 0:
        wait_time = 0.0
    else:
        wait_time = -math.log(numerator / denominator) / cooling_constant
        wait_time = max(wait_time, 0.0)

    comfort_score = round(100.0 * best_score, 2)

    return {
        "optimal_temp_c": round(best_temp, 1),
        "wait_time_min": round(wait_time, 2),
        "comfort_score": comfort_score,
        "cooling_constant_per_min": round(cooling_constant, 4),
        "subst_wait_time_min": (
            f"t^* = -(1/{cooling_constant:.4f}) * ln((T^* - T_{{amb}})/(T_0 - T_{{amb}})) = {wait_time:.2f} min"
        ),
        "subst_optimal_temp_c": (
            f"Scanned 0.1 deg C increments from {search_min:.1f} to {search_max:.1f} deg C; "
            f"maximum utility {best_score:.3f} reached at {best_temp:.1f} deg C."
        ),
    }
