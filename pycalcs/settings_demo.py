from __future__ import annotations


def calculate_settings_demo(
    base_value: float,
    scale_factor: float,
    reference_value: float,
) -> dict[str, float]:
    """
    Computes a scaled value and normalizes it to a reference.

    This example function is intentionally simple so UI behavior (auto-calc, theme,
    density, equation visibility) can be demonstrated without heavy computation.

    ---Parameters---
    base_value : float
        Base quantity used as the starting point for scaling.
    scale_factor : float
        Multiplier applied to the base_value.
    reference_value : float
        Reference value used to normalize the scaled result. Must be non-zero.

    ---Returns---
    scaled_value : float
        Scaled value after applying the scale_factor.
    normalized_value : float
        Scaled value divided by the reference_value.
    percent_of_reference : float
        Normalized value expressed as a percentage of the reference.

    ---LaTeX---
    S = B \\times k
    N = \\frac{S}{R}
    P = 100 \\times N
    """
    base = float(base_value)
    scale = float(scale_factor)
    reference = float(reference_value)

    if reference == 0:
        raise ValueError("reference_value must be non-zero.")

    scaled_value = base * scale
    normalized_value = scaled_value / reference
    percent_of_reference = normalized_value * 100.0

    return {
        "scaled_value": scaled_value,
        "normalized_value": normalized_value,
        "percent_of_reference": percent_of_reference,
        "subst_scaled_value": f"S = {base:.3f} \\times {scale:.3f} = {scaled_value:.3f}",
        "subst_normalized_value": f"N = {scaled_value:.3f} / {reference:.3f} = {normalized_value:.3f}",
        "subst_percent_of_reference": f"P = 100 \\times {normalized_value:.3f} = {percent_of_reference:.3f}",
    }
