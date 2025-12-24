"""
Reusable calculations for control system tuning.
"""

from __future__ import annotations


def tune_pid_ultimate_gain(
    ultimate_gain: float,
    ultimate_period: float,
    tuning_rule: str,
    controller_type: str,
) -> dict[str, float]:
    """
    Tunes PI/PID gains from ultimate gain and period using classic closed-loop rules.

    This function applies Ziegler-Nichols or Tyreus-Luyben ultimate gain tuning to
    compute parallel-form gains (Kp, Ki, Kd) along with their equivalent time
    constants (Ti, Td). Ultimate gain Ku and ultimate period Pu are typically
    measured by increasing proportional gain until sustained oscillations appear
    in a closed loop.

    References:
    - J. G. Ziegler and N. B. Nichols, "Optimum Settings for Automatic Controllers," Trans. ASME, 1942.
    - B. D. Tyreus and W. L. Luyben, "Tuning PI Controllers for Integrator/Dead Time Processes," Ind. Eng. Chem. Res., 1992.

    ---Parameters---
    ultimate_gain : float
        Ultimate gain Ku at the onset of sustained oscillations (dimensionless).
    ultimate_period : float
        Ultimate period Pu of the sustained oscillation (s).
    tuning_rule : str
        Rule selection: "ziegler-nichols" or "tyreus-luyben".
    controller_type : str
        Controller mode: "PI" or "PID".

    ---Returns---
    kp : float
        Proportional gain Kp (dimensionless).
    ti : float
        Integral time constant Ti (s).
    td : float
        Derivative time constant Td (s). PI tuning returns 0.
    ki : float
        Integral gain Ki in parallel form, Ki = Kp / Ti (1/s).
    kd : float
        Derivative gain Kd in parallel form, Kd = Kp * Td (s).

    ---LaTeX---
    K_p = C_{K_p} K_u
    T_i = C_{T_i} P_u
    T_d = C_{T_d} P_u
    K_i = \\frac{K_p}{T_i}
    K_d = K_p T_d
    """

    if ultimate_gain <= 0.0:
        raise ValueError("ultimate_gain must be positive.")
    if ultimate_period <= 0.0:
        raise ValueError("ultimate_period must be positive.")

    rule_key = tuning_rule.strip().lower().replace("_", "-").replace(" ", "-")
    type_key = controller_type.strip().lower()

    tuning_table = {
        "ziegler-nichols": {
            "pi": {"kp": 0.45, "ti": 1.0 / 1.2, "td": 0.0},
            "pid": {"kp": 0.6, "ti": 0.5, "td": 1.0 / 8.0},
        },
        "tyreus-luyben": {
            "pi": {"kp": 0.31, "ti": 2.2, "td": 0.0},
            "pid": {"kp": 0.45, "ti": 2.2, "td": 1.0 / 6.3},
        },
    }

    if rule_key not in tuning_table:
        raise ValueError("tuning_rule must be 'ziegler-nichols' or 'tyreus-luyben'.")
    if type_key not in tuning_table[rule_key]:
        raise ValueError("controller_type must be 'PI' or 'PID'.")

    coefficients = tuning_table[rule_key][type_key]
    kp = coefficients["kp"] * ultimate_gain
    ti = coefficients["ti"] * ultimate_period
    td = coefficients["td"] * ultimate_period

    ki = 0.0
    if ti > 0.0:
        ki = kp / ti

    kd = kp * td

    def _fmt(value: float) -> str:
        return f"{value:.4g}"

    results: dict[str, float] = {
        "kp": kp,
        "ti": ti,
        "td": td,
        "ki": ki,
        "kd": kd,
    }

    results["subst_kp"] = (
        "K_p = C_{K_p} K_u = "
        f"{_fmt(coefficients['kp'])} \\times {_fmt(ultimate_gain)}"
        f" = {_fmt(kp)}"
    )
    results["subst_ti"] = (
        "T_i = C_{T_i} P_u = "
        f"{_fmt(coefficients['ti'])} \\times {_fmt(ultimate_period)}"
        f" = {_fmt(ti)} \\text{{s}}"
    )
    results["subst_td"] = (
        "T_d = C_{T_d} P_u = "
        f"{_fmt(coefficients['td'])} \\times {_fmt(ultimate_period)}"
        f" = {_fmt(td)} \\text{{s}}"
    )
    results["subst_ki"] = (
        "K_i = \\frac{K_p}{T_i} = "
        f"\\frac{{{_fmt(kp)}}}{{{_fmt(ti)}}} = {_fmt(ki)} \\text{{s}}^{-1}"
    )
    results["subst_kd"] = (
        "K_d = K_p T_d = "
        f"{_fmt(kp)} \\times {_fmt(td)} = {_fmt(kd)} \\text{{s}}"
    )

    return results
