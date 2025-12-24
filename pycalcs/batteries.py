"""
Battery pack runtime estimation helpers.
"""

from __future__ import annotations

import math


def estimate_battery_runtime(
    chemistry: str,
    use_cell_specs: float,
    series_cells: float,
    parallel_cells: float,
    cell_nominal_voltage_v: float,
    cell_capacity_ah: float,
    cell_internal_resistance_ohm: float,
    cell_cutoff_voltage_v: float,
    pack_nominal_voltage_v: float,
    pack_capacity_ah: float,
    pack_internal_resistance_ohm: float,
    pack_cutoff_voltage_v: float,
    load_type: str,
    load_current_a: float,
    load_power_w: float,
    load_resistance_ohm: float,
    converter_efficiency: float,
    duty_cycle: float,
    peukert_exponent: float,
    reference_current_a: float,
    ambient_temperature_c: float,
    reference_temperature_c: float,
    capacity_temp_coeff_per_c: float,
    depth_of_discharge: float,
    state_of_health: float,
) -> dict[str, float]:
    """
    Estimates battery runtime with temperature, Peukert, and internal resistance effects.

    The estimator uses a constant nominal open-circuit voltage and a lumped internal
    resistance to approximate loaded voltage. Capacity is adjusted for temperature,
    usable depth-of-discharge, and state-of-health. A Peukert-style correction
    accounts for higher effective current draw. Chemistry is provided to align UI
    defaults; calculations rely on the numeric parameters supplied.

    ---Parameters---
    chemistry : str
        Battery chemistry label for context (e.g., "li_ion_nmc"); used for UI defaults.
    use_cell_specs : float
        Use cell-level specs when set to 1, otherwise use pack-level inputs.
    series_cells : float
        Number of cells in series (dimensionless, integer > 0 when enabled).
    parallel_cells : float
        Number of cells in parallel (dimensionless, integer > 0 when enabled).
    cell_nominal_voltage_v : float
        Nominal single-cell voltage (V).
    cell_capacity_ah : float
        Single-cell rated capacity (Ah).
    cell_internal_resistance_ohm : float
        Single-cell internal resistance (Ohm).
    cell_cutoff_voltage_v : float
        Minimum per-cell voltage at end-of-discharge (V).
    pack_nominal_voltage_v : float
        Pack nominal voltage when not derived from cells (V).
    pack_capacity_ah : float
        Pack rated capacity when not derived from cells (Ah).
    pack_internal_resistance_ohm : float
        Pack internal resistance when not derived from cells (Ohm).
    pack_cutoff_voltage_v : float
        Pack cutoff voltage when not derived from cells (V).
    load_type : str
        "constant_current", "constant_power", or "constant_resistance".
    load_current_a : float
        Requested constant current at the load side (A); battery current scales by efficiency.
    load_power_w : float
        Load power demand (W) for constant power mode.
    load_resistance_ohm : float
        Load resistance (Ohm) for constant resistance mode (assumed at battery terminals).
    converter_efficiency : float
        Power conversion efficiency from battery to load (0-1); applied to current/power modes.
    duty_cycle : float
        Fraction of time the load is active (0-1).
    peukert_exponent : float
        Peukert exponent (>= 1), higher values reduce effective capacity at high C-rate.
    reference_current_a : float
        Reference current for rated capacity in the Peukert model (A).
    ambient_temperature_c : float
        Ambient or cell temperature (deg C).
    reference_temperature_c : float
        Reference temperature for rated capacity (deg C).
    capacity_temp_coeff_per_c : float
        Capacity change per degree C relative to reference (1/deg C).
    depth_of_discharge : float
        Fraction of rated capacity allowed to be used (0-1).
    state_of_health : float
        Remaining capacity fraction relative to new (0-1).

    ---Returns---
    runtime_hours : float
        Estimated runtime at the specified conditions (h).
    runtime_minutes : float
        Estimated runtime at the specified conditions (min).
    effective_capacity_ah : float
        Capacity after temperature, SOH, DoD, and Peukert adjustments (Ah).
    average_current_a : float
        Average battery current including duty cycle (A).
    average_power_w : float
        Average battery power at loaded voltage (W).
    energy_delivered_wh : float
        Estimated usable energy delivered (Wh).
    loaded_voltage_v : float
        Pack voltage under load (V).
    voltage_sag_v : float
        Voltage drop across internal resistance at load current (V).
    c_rate : float
        Discharge C-rate based on nominal capacity (1/h).
    power_loss_w : float
        Power dissipated as heat in internal resistance (W). Equals I_load^2 * R_pack.
    pack_nominal_voltage_v : float
        Pack nominal voltage after cell aggregation (V).
    pack_capacity_ah : float
        Pack rated capacity after cell aggregation (Ah).
    pack_internal_resistance_ohm : float
        Pack internal resistance after cell aggregation (Ohm).
    pack_cutoff_voltage_v : float
        Pack cutoff voltage after cell aggregation (V).

    ---LaTeX---
    V_{pack} = N_s V_{cell}
    C_{pack} = N_p C_{cell}
    R_{pack} = \\frac{N_s}{N_p} R_{cell}
    I_{load} = \\frac{I_{set}}{\\eta}
    I_{load} = \\frac{V_{pack}}{R_{load} + R_{pack}}
    I_{load} = \\frac{V_{pack} - \\sqrt{V_{pack}^{2} - 4 R_{pack} P_{batt}}}{2 R_{pack}}
    V_{load} = V_{pack} - I_{load} R_{pack}
    V_{sag} = I_{load} R_{pack}
    C_{temp} = C_{pack} \\left[1 + \\alpha (T - T_{ref})\\right]
    C_{usable} = C_{temp} \\cdot SOH \\cdot DoD
    C_{eff} = C_{usable} \\left(\\frac{I_{ref}}{I_{avg}}\\right)^{k-1}
    t = \\frac{C_{eff}}{I_{avg}}
    E = V_{load} C_{eff}
    P_{avg} = V_{load} I_{avg}
    C_{rate} = \\frac{I_{avg}}{C_{pack}}
    P_{loss} = I_{load}^{2} R_{pack}
    """

    use_cell_specs_bool = bool(round(use_cell_specs))

    if use_cell_specs_bool:
        if series_cells <= 0:
            raise ValueError("series_cells must be positive when using cell specs.")
        if parallel_cells <= 0:
            raise ValueError("parallel_cells must be positive when using cell specs.")
        if cell_nominal_voltage_v <= 0:
            raise ValueError("cell_nominal_voltage_v must be positive.")
        if cell_capacity_ah <= 0:
            raise ValueError("cell_capacity_ah must be positive.")
        if cell_internal_resistance_ohm <= 0:
            raise ValueError("cell_internal_resistance_ohm must be positive.")
        if cell_cutoff_voltage_v <= 0:
            raise ValueError("cell_cutoff_voltage_v must be positive.")

        pack_nominal_voltage_v = series_cells * cell_nominal_voltage_v
        pack_capacity_ah = parallel_cells * cell_capacity_ah
        pack_internal_resistance_ohm = (series_cells * cell_internal_resistance_ohm) / parallel_cells
        pack_cutoff_voltage_v = series_cells * cell_cutoff_voltage_v

    if pack_nominal_voltage_v <= 0:
        raise ValueError("pack_nominal_voltage_v must be positive.")
    if pack_capacity_ah <= 0:
        raise ValueError("pack_capacity_ah must be positive.")
    if pack_internal_resistance_ohm < 0:
        raise ValueError("pack_internal_resistance_ohm cannot be negative.")
    if pack_cutoff_voltage_v <= 0:
        raise ValueError("pack_cutoff_voltage_v must be positive.")
    if converter_efficiency <= 0 or converter_efficiency > 1:
        raise ValueError("converter_efficiency must be between 0 and 1.")
    if duty_cycle <= 0 or duty_cycle > 1:
        raise ValueError("duty_cycle must be between 0 and 1.")
    if depth_of_discharge <= 0 or depth_of_discharge > 1:
        raise ValueError("depth_of_discharge must be between 0 and 1.")
    if state_of_health <= 0 or state_of_health > 1:
        raise ValueError("state_of_health must be between 0 and 1.")
    if peukert_exponent < 1:
        raise ValueError("peukert_exponent must be >= 1.")

    temp_factor = 1.0 + capacity_temp_coeff_per_c * (ambient_temperature_c - reference_temperature_c)
    if temp_factor <= 0:
        raise ValueError("Temperature adjustment drives capacity below zero.")

    capacity_temp_ah = pack_capacity_ah * temp_factor
    capacity_usable_ah = capacity_temp_ah * state_of_health * depth_of_discharge

    v_oc = pack_nominal_voltage_v
    r_int = pack_internal_resistance_ohm
    load_type_norm = load_type.strip().lower()

    p_batt = 0.0

    if load_type_norm == "constant_current":
        if load_current_a <= 0:
            raise ValueError("load_current_a must be positive for constant_current.")
        i_load = load_current_a / converter_efficiency
    elif load_type_norm == "constant_resistance":
        if load_resistance_ohm <= 0:
            raise ValueError("load_resistance_ohm must be positive for constant_resistance.")
        i_load = v_oc / (load_resistance_ohm + r_int)
    elif load_type_norm == "constant_power":
        if load_power_w <= 0:
            raise ValueError("load_power_w must be positive for constant_power.")
        p_batt = load_power_w / converter_efficiency
        if r_int > 0:
            discriminant = v_oc**2 - 4 * r_int * p_batt
            if discriminant < 0:
                raise ValueError("Requested power exceeds what the pack can supply.")
            i_load = (v_oc - math.sqrt(discriminant)) / (2 * r_int)
        else:
            i_load = p_batt / v_oc
    else:
        raise ValueError("load_type must be constant_current, constant_power, or constant_resistance.")

    v_load = v_oc - i_load * r_int
    if v_load <= 0:
        raise ValueError("Loaded voltage is non-positive; reduce the load or resistance.")
    if v_load <= pack_cutoff_voltage_v:
        raise ValueError("Loaded voltage is below the cutoff voltage.")

    i_avg = i_load * duty_cycle
    if i_avg <= 0:
        raise ValueError("Average current must be positive.")

    if peukert_exponent > 1:
        if reference_current_a <= 0:
            raise ValueError("reference_current_a must be positive when Peukert exponent > 1.")
        capacity_effective_ah = capacity_usable_ah * (reference_current_a / i_avg) ** (
            peukert_exponent - 1
        )
    else:
        capacity_effective_ah = capacity_usable_ah

    runtime_hours = capacity_effective_ah / i_avg
    runtime_minutes = runtime_hours * 60.0
    average_power_w = v_load * i_avg
    energy_delivered_wh = v_load * capacity_effective_ah
    voltage_sag_v = i_load * r_int
    c_rate = i_avg / pack_capacity_ah
    power_loss_w = i_load * i_load * r_int

    def _fmt(value: float) -> str:
        if value == 0:
            return "0"
        abs_val = abs(value)
        if abs_val >= 1e4 or abs_val < 1e-3:
            return f"{value:.3e}"
        return f"{value:.4f}"

    if load_type_norm == "constant_current":
        subst_current = (
            f"I_{{load}} = \\frac{{I_{{set}}}}{{\\eta}} = "
            f"\\frac{{{_fmt(load_current_a)}}}{{{_fmt(converter_efficiency)}}} = {_fmt(i_load)}"
        )
    elif load_type_norm == "constant_resistance":
        subst_current = (
            f"I_{{load}} = \\frac{{V_{{pack}}}}{{R_{{load}} + R_{{pack}}}} = "
            f"\\frac{{{_fmt(v_oc)}}}{{{_fmt(load_resistance_ohm)} + {_fmt(r_int)}}} = {_fmt(i_load)}"
        )
    else:
        if r_int > 0:
            subst_current = (
                f"I_{{load}} = \\frac{{V_{{pack}} - \\sqrt{{V_{{pack}}^2 - 4 R_{{pack}} P_{{batt}}}}}}"
                f"{{2 R_{{pack}}}} = "
                f"\\frac{{{_fmt(v_oc)} - \\sqrt{{{_fmt(v_oc)}^2 - 4 \\times {_fmt(r_int)} \\times {_fmt(p_batt)}}}}}"
                f"{{2 \\times {_fmt(r_int)}}} = {_fmt(i_load)}"
            )
        else:
            subst_current = (
                f"I_{{load}} = \\frac{{P_{{batt}}}}{{V_{{pack}}}} = "
                f"\\frac{{{_fmt(p_batt)}}}{{{_fmt(v_oc)}}} = {_fmt(i_load)}"
            )

    if use_cell_specs_bool:
        subst_pack_voltage = (
            f"V_{{pack}} = N_s V_{{cell}} = {_fmt(series_cells)} \\times "
            f"{_fmt(cell_nominal_voltage_v)} = {_fmt(pack_nominal_voltage_v)} \\, \\text{{V}}"
        )
        subst_pack_capacity = (
            f"C_{{pack}} = N_p C_{{cell}} = {_fmt(parallel_cells)} \\times "
            f"{_fmt(cell_capacity_ah)} = {_fmt(pack_capacity_ah)} \\, \\text{{Ah}}"
        )
        subst_pack_resistance = (
            f"R_{{pack}} = \\frac{{N_s}}{{N_p}} R_{{cell}} = "
            f"\\frac{{{_fmt(series_cells)}}}{{{_fmt(parallel_cells)}}} \\times "
            f"{_fmt(cell_internal_resistance_ohm)} = {_fmt(pack_internal_resistance_ohm)} \\, \\Omega"
        )
        subst_pack_cutoff = (
            f"V_{{cut}} = N_s V_{{cell,cut}} = {_fmt(series_cells)} \\times "
            f"{_fmt(cell_cutoff_voltage_v)} = {_fmt(pack_cutoff_voltage_v)} \\, \\text{{V}}"
        )
    else:
        subst_pack_voltage = f"V_{{pack}} = {_fmt(pack_nominal_voltage_v)} \\, \\text{{V}}"
        subst_pack_capacity = f"C_{{pack}} = {_fmt(pack_capacity_ah)} \\, \\text{{Ah}}"
        subst_pack_resistance = f"R_{{pack}} = {_fmt(pack_internal_resistance_ohm)} \\, \\Omega"
        subst_pack_cutoff = f"V_{{cut}} = {_fmt(pack_cutoff_voltage_v)} \\, \\text{{V}}"

    subst_temp_capacity = (
        f"C_{{temp}} = C_{{pack}} [1 + \\alpha (T - T_{{ref}})] = "
        f"{_fmt(pack_capacity_ah)} [1 + {_fmt(capacity_temp_coeff_per_c)}"
        f"({ _fmt(ambient_temperature_c)} - {_fmt(reference_temperature_c)})] = "
        f"{_fmt(capacity_temp_ah)} \\, \\text{{Ah}}"
    )
    subst_usable_capacity = (
        f"C_{{usable}} = C_{{temp}} \\cdot SOH \\cdot DoD = {_fmt(capacity_temp_ah)}"
        f" \\times {_fmt(state_of_health)} \\times {_fmt(depth_of_discharge)}"
        f" = {_fmt(capacity_usable_ah)} \\, \\text{{Ah}}"
    )
    if peukert_exponent > 1:
        subst_effective_capacity = (
            f"C_{{eff}} = C_{{usable}} (I_{{ref}} / I_{{avg}})^{{k-1}} = "
            f"{_fmt(capacity_usable_ah)} ({_fmt(reference_current_a)} / {_fmt(i_avg)})"
            f"^{{{_fmt(peukert_exponent)}-1}} = {_fmt(capacity_effective_ah)} \\, \\text{{Ah}}"
        )
    else:
        subst_effective_capacity = (
            f"C_{{eff}} = C_{{usable}} = {_fmt(capacity_usable_ah)} \\, \\text{{Ah}}"
        )
    subst_runtime_hours = (
        f"t = C_{{eff}} / I_{{avg}} = {_fmt(capacity_effective_ah)} / {_fmt(i_avg)}"
        f" = {_fmt(runtime_hours)} \\, \\text{{h}}"
    )
    subst_runtime_minutes = (
        f"t_{{min}} = 60 t = 60 \\times {_fmt(runtime_hours)} = {_fmt(runtime_minutes)} \\, \\text{{min}}"
    )
    subst_voltage_loaded = (
        f"V_{{load}} = V_{{pack}} - I_{{load}} R_{{pack}} = "
        f"{_fmt(v_oc)} - {_fmt(i_load)} \\times {_fmt(r_int)} = {_fmt(v_load)} \\, \\text{{V}}"
    )
    subst_voltage_sag = (
        f"V_{{sag}} = I_{{load}} R_{{pack}} = {_fmt(i_load)} \\times {_fmt(r_int)}"
        f" = {_fmt(voltage_sag_v)} \\, \\text{{V}}"
    )
    subst_average_current = (
        f"{subst_current},\\; I_{{avg}} = I_{{load}} \\cdot \\text{{duty}} = "
        f"{_fmt(i_load)} \\times {_fmt(duty_cycle)} = {_fmt(i_avg)} \\, \\text{{A}}"
    )
    subst_average_power = (
        f"P_{{avg}} = V_{{load}} I_{{avg}} = {_fmt(v_load)} \\times {_fmt(i_avg)}"
        f" = {_fmt(average_power_w)} \\, \\text{{W}}"
    )
    subst_energy = (
        f"E = V_{{load}} C_{{eff}} = {_fmt(v_load)} \\times {_fmt(capacity_effective_ah)}"
        f" = {_fmt(energy_delivered_wh)} \\, \\text{{Wh}}"
    )
    subst_c_rate = (
        f"C_{{rate}} = I_{{avg}} / C_{{pack}} = {_fmt(i_avg)} / {_fmt(pack_capacity_ah)}"
        f" = {_fmt(c_rate)} \\, \\text{{1/h}}"
    )
    subst_power_loss = (
        f"P_{{loss}} = I_{{load}}^2 R_{{pack}} = {_fmt(i_load)}^2 \\times {_fmt(r_int)}"
        f" = {_fmt(power_loss_w)} \\, \\text{{W}}"
    )

    return {
        "runtime_hours": runtime_hours,
        "runtime_minutes": runtime_minutes,
        "effective_capacity_ah": capacity_effective_ah,
        "average_current_a": i_avg,
        "average_power_w": average_power_w,
        "energy_delivered_wh": energy_delivered_wh,
        "loaded_voltage_v": v_load,
        "voltage_sag_v": voltage_sag_v,
        "c_rate": c_rate,
        "power_loss_w": power_loss_w,
        "pack_nominal_voltage_v": pack_nominal_voltage_v,
        "pack_capacity_ah": pack_capacity_ah,
        "pack_internal_resistance_ohm": pack_internal_resistance_ohm,
        "pack_cutoff_voltage_v": pack_cutoff_voltage_v,
        "subst_runtime_hours": subst_runtime_hours,
        "subst_runtime_minutes": subst_runtime_minutes,
        "subst_effective_capacity_ah": subst_effective_capacity,
        "subst_average_current_a": subst_average_current,
        "subst_average_power_w": subst_average_power,
        "subst_energy_delivered_wh": subst_energy,
        "subst_loaded_voltage_v": subst_voltage_loaded,
        "subst_voltage_sag_v": subst_voltage_sag,
        "subst_c_rate": subst_c_rate,
        "subst_power_loss_w": subst_power_loss,
        "subst_pack_nominal_voltage_v": subst_pack_voltage,
        "subst_pack_capacity_ah": subst_pack_capacity,
        "subst_pack_internal_resistance_ohm": subst_pack_resistance,
        "subst_pack_cutoff_voltage_v": subst_pack_cutoff,
    }
