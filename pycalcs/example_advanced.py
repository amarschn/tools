"""
Example Advanced Module - Demonstrates patterns for complex engineering tools.

This module shows how to structure a pycalcs module for tools that need:
- Database-driven lookups
- Multiple calculation outputs
- Safety factor analysis
- Visualization data generation
- Substituted equation strings for progressive disclosure

This example uses generic "widget analysis" calculations as placeholders.
Replace with your actual domain-specific equations.
"""

from typing import Dict, List, Tuple
import math

# =============================================================================
# MATERIAL DATABASE
# =============================================================================

MATERIALS: Dict[str, Dict[str, float]] = {
    "Standard Alloy": {
        "strength": 250.0,          # MPa
        "modulus": 200.0,           # GPa
        "density": 7850.0,          # kg/m^3
        "cost_factor": 1.0,
        "description": "General purpose material for typical applications",
    },
    "High-Strength Alloy": {
        "strength": 450.0,
        "modulus": 210.0,
        "density": 7900.0,
        "cost_factor": 1.8,
        "description": "Premium material for demanding applications",
    },
    "Lightweight Alloy": {
        "strength": 280.0,
        "modulus": 70.0,
        "density": 2700.0,
        "cost_factor": 2.5,
        "description": "Low density material for weight-critical applications",
    },
    "Economy Grade": {
        "strength": 180.0,
        "modulus": 190.0,
        "density": 7800.0,
        "cost_factor": 0.7,
        "description": "Cost-effective material for non-critical applications",
    },
}


# =============================================================================
# DATABASE LOOKUP FUNCTIONS
# =============================================================================

def get_material_properties(material_name: str) -> Dict[str, float]:
    """
    Look up material properties by name.

    Parameters
    ----------
    material_name : str
        Name of the material (must match key in MATERIALS dict)

    Returns
    -------
    dict
        Material properties including strength, modulus, density, cost_factor

    Raises
    ------
    ValueError
        If material_name is not found in database
    """
    if material_name in MATERIALS:
        return MATERIALS[material_name]
    else:
        raise ValueError(
            f"Unknown material '{material_name}'. "
            f"Valid materials: {list(MATERIALS.keys())}"
        )


def get_available_materials() -> List[str]:
    """Return list of available material names."""
    return list(MATERIALS.keys())


# =============================================================================
# VISUALIZATION DATA GENERATION
# =============================================================================

def generate_response_curve(
    primary_value: float,
    secondary_value: float,
    n_points: int = 50
) -> Dict[str, List[float]]:
    """
    Generate a generic response curve for plotting.

    This creates a damped sinusoidal response as a placeholder.
    Replace with your actual physics.

    Parameters
    ----------
    primary_value : float
        Primary input parameter
    secondary_value : float
        Secondary input parameter
    n_points : int
        Number of points for the curve

    Returns
    -------
    dict
        Contains x_values, y_values arrays for plotting
    """
    # Generate x values from 0 to 10
    x_values = [i * 10.0 / (n_points - 1) for i in range(n_points)]

    # Generate a damped response curve (placeholder)
    omega = primary_value / 10.0
    zeta = secondary_value / 100.0
    y_values = []

    for x in x_values:
        # Damped sinusoidal response
        y = math.exp(-zeta * x) * math.cos(omega * x) * primary_value
        y_values.append(y)

    return {
        "x_values": x_values,
        "y_values": y_values,
        "peak_x": x_values[0],
        "peak_y": primary_value,
    }


def generate_parameter_sensitivity(
    base_value: float,
    result_value: float,
    design_factor: float,
    param_range: Tuple[float, float] = None,
    n_points: int = 30
) -> Dict[str, List[float]]:
    """
    Generate safety factor vs parameter data for sensitivity analysis.

    Parameters
    ----------
    base_value : float
        Current parameter value
    result_value : float
        Current result value
    design_factor : float
        Required design factor
    param_range : tuple, optional
        (min, max) parameter range
    n_points : int
        Number of points

    Returns
    -------
    dict
        Contains parameter values and corresponding outputs
    """
    if param_range is None:
        param_range = (base_value * 0.5, base_value * 2.0)

    p_min, p_max = param_range
    param_values = [p_min + i * (p_max - p_min) / (n_points - 1) for i in range(n_points)]

    # Generate a simple relationship (placeholder)
    # Output increases with sqrt of parameter
    output_values = []
    for p in param_values:
        ratio = p / base_value if base_value > 0 else 1.0
        output = result_value * math.sqrt(ratio)
        output_values.append(output)

    return {
        "param_values": param_values,
        "output_values": output_values,
        "design_factor": design_factor,
        "current_param": base_value,
        "current_output": result_value,
    }


# =============================================================================
# MAIN CALCULATION FUNCTION
# =============================================================================

def analyze_widget(
    primary_dimension: float,
    secondary_dimension: float,
    load_factor: float,
    material: str,
    design_factor: float = 2.0,
    efficiency: float = 0.85,
    temperature_offset: float = 0.0,
    include_correction: bool = True
) -> Dict:
    """
    Analyze a generic widget using placeholder equations.

    This demonstrates the structure for complex analysis functions.
    Replace the equations with your actual domain-specific calculations.

    ---Parameters---
    primary_dimension : float
        Primary geometric dimension in millimeters (mm).
        This is the main sizing parameter for the widget.
        Typical range: 10-500 mm.
    secondary_dimension : float
        Secondary geometric dimension in millimeters (mm).
        Controls the aspect ratio of the widget.
        Typical range: 5-100 mm.
    load_factor : float
        Applied load factor (dimensionless multiplier).
        Represents the intensity of loading conditions.
        1.0 = nominal, higher = more severe.
    material : str
        Material selection from the database. Options include:
        Standard Alloy, High-Strength Alloy, Lightweight Alloy, Economy Grade.
    design_factor : float
        Required safety factor for the design. Typical values:
        1.5 for non-critical, 2.0 for standard, 3.0+ for critical.
    efficiency : float
        System efficiency factor (0.0 to 1.0).
        Accounts for losses and non-ideal behavior.
        Default 0.85 represents typical conditions.
    temperature_offset : float
        Temperature deviation from reference in degrees Celsius.
        Positive = hotter than reference, negative = colder.
        Affects material properties.
    include_correction : bool
        Whether to apply empirical correction factors.
        Enable for real-world accuracy, disable for theoretical values.

    ---Returns---
    primary_result : float
        Main calculated output value (units vary by application).
        This is the key result users are looking for.
    secondary_result : float
        Supporting calculated value (units vary by application).
        Provides additional context for the primary result.
    tertiary_result : float
        Third calculated output for completeness.
    safety_factor_a : float
        First safety factor check (dimensionless).
        Ratio of capacity to demand for failure mode A.
    safety_factor_b : float
        Second safety factor check (dimensionless).
        Ratio of capacity to demand for failure mode B.
    utilization : float
        Percentage of capacity being used (0-100%).
        Lower values indicate more conservative design.
    status : str
        Design acceptability: acceptable, marginal, or unacceptable.
    mass_estimate : float
        Estimated mass in kilograms (kg).

    ---LaTeX---
    R_{primary} = \\frac{D_1 \\cdot D_2 \\cdot \\eta}{L_f}
    R_{secondary} = \\sqrt{D_1^2 + D_2^2} \\cdot k
    SF_A = \\frac{S_{material}}{\\sigma_{max}}
    """
    # === MATERIAL LOOKUP ===
    mat = get_material_properties(material)
    strength = mat["strength"]
    modulus = mat["modulus"]
    density = mat["density"]
    cost_factor = mat["cost_factor"]

    # === TEMPERATURE CORRECTION ===
    temp_factor = 1.0
    if temperature_offset != 0:
        # Simple linear derating (placeholder)
        temp_factor = 1.0 - (temperature_offset / 500.0)
        temp_factor = max(0.5, min(1.1, temp_factor))

    effective_strength = strength * temp_factor

    # === CORRECTION FACTOR ===
    correction = 1.0
    if include_correction:
        # Empirical correction based on geometry (placeholder)
        aspect_ratio = primary_dimension / secondary_dimension if secondary_dimension > 0 else 1.0
        if aspect_ratio > 5:
            correction = 0.92
        elif aspect_ratio < 0.2:
            correction = 0.88
        else:
            correction = 1.0

    # === PRIMARY CALCULATIONS (placeholder equations) ===
    # These are dummy equations - replace with real physics

    # Primary result: scaled product of dimensions and efficiency
    primary_result = (primary_dimension * secondary_dimension * efficiency) / (load_factor * 100)
    primary_result *= correction

    # Secondary result: geometric mean with modulus factor
    secondary_result = math.sqrt(primary_dimension**2 + secondary_dimension**2) * (modulus / 200.0)

    # Tertiary result: ratio calculation
    tertiary_result = (primary_result / secondary_result) * 1000 if secondary_result > 0 else 0

    # === STRESS/CAPACITY ANALYSIS (placeholder) ===
    # Simulated stress based on load and geometry
    simulated_stress = load_factor * 50.0 * (100.0 / primary_dimension)
    max_capacity = effective_strength * efficiency

    # === SAFETY FACTORS ===
    sf_a = max_capacity / simulated_stress if simulated_stress > 0 else float('inf')
    sf_b = sf_a * 0.85  # Second mode has less margin (placeholder)

    utilization = 100.0 / sf_a if sf_a > 0 else 100.0

    # === STATUS DETERMINATION ===
    min_sf = min(sf_a, sf_b)
    if min_sf >= design_factor:
        status = "acceptable"
    elif min_sf >= 1.0:
        status = "marginal"
    else:
        status = "unacceptable"

    # === RECOMMENDATIONS ===
    recommendations = []
    if sf_a < design_factor:
        recommendations.append(f"Increase primary dimension or select stronger material (SF={sf_a:.2f}, required={design_factor:.1f})")
    if sf_b < design_factor:
        recommendations.append("Secondary failure mode margin is low; review design assumptions")
    if temperature_offset > 50:
        recommendations.append("High temperature operation; consider thermal management")
    if not include_correction:
        recommendations.append("Correction factors disabled; results are theoretical only")

    # === MASS ESTIMATE ===
    # Simple volume approximation (placeholder)
    volume_mm3 = primary_dimension * secondary_dimension * (primary_dimension * 0.1)
    volume_m3 = volume_mm3 * 1e-9
    mass_estimate = volume_m3 * density

    # === COST ESTIMATE ===
    cost_estimate = mass_estimate * cost_factor * 10.0  # $/kg base rate (placeholder)

    # === SUBSTITUTED EQUATIONS ===
    subst_primary = (
        f"R_{{primary}} = \\frac{{{primary_dimension:.1f} \\times {secondary_dimension:.1f} \\times {efficiency:.2f}}}"
        f"{{{load_factor:.2f} \\times 100}} = {primary_result:.3f}"
    )

    subst_secondary = (
        f"R_{{secondary}} = \\sqrt{{{primary_dimension:.1f}^2 + {secondary_dimension:.1f}^2}} \\times "
        f"\\frac{{{modulus:.0f}}}{{200}} = {secondary_result:.2f}"
    )

    subst_sf = (
        f"SF_A = \\frac{{{effective_strength:.0f} \\times {efficiency:.2f}}}{{{simulated_stress:.1f}}} = {sf_a:.2f}"
    )

    # === VISUALIZATION DATA ===
    response_curve = generate_response_curve(primary_dimension, secondary_dimension)
    sensitivity_data = generate_parameter_sensitivity(
        primary_dimension, sf_a, design_factor
    )

    # === RETURN COMPREHENSIVE RESULTS ===
    return {
        # === PRIMARY OUTPUTS ===
        "primary_result": primary_result,
        "secondary_result": secondary_result,
        "tertiary_result": tertiary_result,

        # === SAFETY ASSESSMENT ===
        "safety_factor_a": sf_a,
        "safety_factor_b": sf_b,
        "utilization": utilization,
        "status": status,
        "recommendations": recommendations,

        # === GEOMETRY & INPUTS ===
        "primary_dimension": primary_dimension,
        "secondary_dimension": secondary_dimension,
        "aspect_ratio": primary_dimension / secondary_dimension if secondary_dimension > 0 else 0,

        # === MATERIAL ===
        "material_name": material,
        "effective_strength": effective_strength,
        "modulus": modulus,

        # === MASS & COST ===
        "mass_estimate": mass_estimate,
        "cost_estimate": cost_estimate,

        # === INTERMEDIATE VALUES ===
        "temp_factor": temp_factor,
        "correction_factor": correction,
        "simulated_stress": simulated_stress,

        # === SUBSTITUTED EQUATIONS ===
        "subst_primary_result": subst_primary,
        "subst_secondary_result": subst_secondary,
        "subst_safety_factor_a": subst_sf,

        # === VISUALIZATION DATA ===
        "response_curve": response_curve,
        "sensitivity_data": sensitivity_data,
    }
