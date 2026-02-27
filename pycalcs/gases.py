"""Ideal-gas thermodynamics helpers."""

from __future__ import annotations

import math
from typing import Callable


IDEAL_GAS_CONSTANT_J_PER_MOL_K = 8.31446261815324

_PRESSURE_TO_PA = {
    "Pa": 1.0,
    "kPa": 1.0e3,
    "bar": 1.0e5,
    "atm": 101325.0,
    "psi": 6894.757293168,
}

_VOLUME_TO_M3 = {
    "m^3": 1.0,
    "L": 1.0e-3,
    "mL": 1.0e-6,
    "ft^3": 0.028316846592,
}

_AMOUNT_TO_MOL = {
    "mol": 1.0,
    "kmol": 1000.0,
    "lbmol": 453.59237,
}

_TEMPERATURE_TO_K: dict[str, Callable[[float], float]] = {
    "K": lambda value: value,
    "degC": lambda value: value + 273.15,
    "degF": lambda value: (value - 32.0) * (5.0 / 9.0) + 273.15,
    "degR": lambda value: value * (5.0 / 9.0),
}

_TEMPERATURE_FROM_K: dict[str, Callable[[float], float]] = {
    "K": lambda value: value,
    "degC": lambda value: value - 273.15,
    "degF": lambda value: (value - 273.15) * (9.0 / 5.0) + 32.0,
    "degR": lambda value: value * (9.0 / 5.0),
}

_SOLVE_FOR_OPTIONS = {"pressure", "volume", "amount", "temperature"}


def _validate_unit(unit: str, valid_units: set[str], quantity_name: str) -> None:
    if unit not in valid_units:
        raise ValueError(
            f"Unsupported {quantity_name} unit '{unit}'. "
            f"Valid units: {sorted(valid_units)}."
        )


def _require_positive(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    if value <= 0.0:
        raise ValueError(f"{name} must be greater than zero.")


def solve_ideal_gas_law(
    solve_for: str,
    pressure_value: float,
    pressure_unit: str,
    volume_value: float,
    volume_unit: str,
    amount_value: float,
    amount_unit: str,
    temperature_value: float,
    temperature_unit: str,
) -> dict[str, float | str]:
    """
    Solve the ideal gas law for one unknown with common engineering units.

    This solver applies the ideal-gas relation for closed-system state points:
    pressure, volume, amount of substance, and absolute temperature. Users choose
    one unknown (`solve_for`) while providing the other three values and their
    units. Internally, the calculation is performed in SI base units.

    ---Parameters---
    solve_for : str
        Which variable to compute. Must be one of: ``"pressure"``, ``"volume"``,
        ``"amount"``, or ``"temperature"``.
    pressure_value : float
        Pressure value in the selected pressure unit. Required and positive when
        solving for variables other than pressure.
    pressure_unit : str
        Pressure unit symbol. Supported: ``Pa``, ``kPa``, ``bar``, ``atm``, ``psi``.
    volume_value : float
        Volume value in the selected volume unit. Required and positive when
        solving for variables other than volume.
    volume_unit : str
        Volume unit symbol. Supported: ``m^3``, ``L``, ``mL``, ``ft^3``.
    amount_value : float
        Amount of substance in the selected amount unit. Required and positive
        when solving for variables other than amount.
    amount_unit : str
        Amount unit symbol. Supported: ``mol``, ``kmol``, ``lbmol``.
    temperature_value : float
        Temperature value in the selected temperature unit. Required and above
        absolute zero when solving for variables other than temperature.
    temperature_unit : str
        Temperature unit symbol. Supported: ``K``, ``degC``, ``degF``, ``degR``.

    ---Returns---
    pressure_output : float
        Final pressure in the user-selected ``pressure_unit``.
    volume_output : float
        Final volume in the user-selected ``volume_unit``.
    amount_output : float
        Final amount of substance in the user-selected ``amount_unit``.
    temperature_output : float
        Final temperature in the user-selected ``temperature_unit``.
    pressure_si_pa : float
        Final pressure in pascals (Pa).
    volume_si_m3 : float
        Final volume in cubic metres (m^3).
    amount_si_mol : float
        Final amount of substance in moles (mol).
    temperature_si_k : float
        Final temperature in kelvin (K).
    gas_constant_j_per_mol_k : float
        Ideal-gas constant used in the calculation.
    equation_residual_pa_m3 : float
        Residual check ``(P*V - n*R*T)`` in SI units; should be near zero.
    solved_variable : str
        Echo of the solved variable name.

    ---LaTeX---
    P V = n R T
    P = \\frac{n R T}{V}
    V = \\frac{n R T}{P}
    n = \\frac{P V}{R T}
    T = \\frac{P V}{n R}

    ---References---
    Moran, M. J., Shapiro, H. N., Boettner, D. D., & Bailey, M. B. (2018).
    *Fundamentals of Engineering Thermodynamics* (9th ed.). Wiley.
    """
    solve_key = str(solve_for).strip().lower()
    if solve_key not in _SOLVE_FOR_OPTIONS:
        raise ValueError(
            f"solve_for must be one of {sorted(_SOLVE_FOR_OPTIONS)}."
        )

    pressure_unit_clean = str(pressure_unit).strip()
    volume_unit_clean = str(volume_unit).strip()
    amount_unit_clean = str(amount_unit).strip()
    temperature_unit_clean = str(temperature_unit).strip()

    _validate_unit(pressure_unit_clean, set(_PRESSURE_TO_PA), "pressure")
    _validate_unit(volume_unit_clean, set(_VOLUME_TO_M3), "volume")
    _validate_unit(amount_unit_clean, set(_AMOUNT_TO_MOL), "amount")
    _validate_unit(temperature_unit_clean, set(_TEMPERATURE_TO_K), "temperature")

    pressure_input = float(pressure_value)
    volume_input = float(volume_value)
    amount_input = float(amount_value)
    temperature_input = float(temperature_value)

    pressure_si: float | None = None
    volume_si: float | None = None
    amount_si: float | None = None
    temperature_si: float | None = None

    if solve_key != "pressure":
        _require_positive(pressure_input, "pressure_value")
        pressure_si = pressure_input * _PRESSURE_TO_PA[pressure_unit_clean]

    if solve_key != "volume":
        _require_positive(volume_input, "volume_value")
        volume_si = volume_input * _VOLUME_TO_M3[volume_unit_clean]

    if solve_key != "amount":
        _require_positive(amount_input, "amount_value")
        amount_si = amount_input * _AMOUNT_TO_MOL[amount_unit_clean]

    if solve_key != "temperature":
        temperature_si = _TEMPERATURE_TO_K[temperature_unit_clean](temperature_input)
        _require_positive(temperature_si, "temperature_value (absolute)")

    if solve_key == "pressure":
        assert amount_si is not None and temperature_si is not None and volume_si is not None
        pressure_si = (amount_si * IDEAL_GAS_CONSTANT_J_PER_MOL_K * temperature_si) / volume_si
    elif solve_key == "volume":
        assert amount_si is not None and temperature_si is not None and pressure_si is not None
        volume_si = (amount_si * IDEAL_GAS_CONSTANT_J_PER_MOL_K * temperature_si) / pressure_si
    elif solve_key == "amount":
        assert pressure_si is not None and volume_si is not None and temperature_si is not None
        amount_si = (pressure_si * volume_si) / (IDEAL_GAS_CONSTANT_J_PER_MOL_K * temperature_si)
    else:
        assert pressure_si is not None and volume_si is not None and amount_si is not None
        temperature_si = (pressure_si * volume_si) / (amount_si * IDEAL_GAS_CONSTANT_J_PER_MOL_K)

    assert pressure_si is not None
    assert volume_si is not None
    assert amount_si is not None
    assert temperature_si is not None

    _require_positive(pressure_si, "calculated pressure")
    _require_positive(volume_si, "calculated volume")
    _require_positive(amount_si, "calculated amount")
    _require_positive(temperature_si, "calculated temperature")

    pressure_output = pressure_si / _PRESSURE_TO_PA[pressure_unit_clean]
    volume_output = volume_si / _VOLUME_TO_M3[volume_unit_clean]
    amount_output = amount_si / _AMOUNT_TO_MOL[amount_unit_clean]
    temperature_output = _TEMPERATURE_FROM_K[temperature_unit_clean](temperature_si)

    equation_residual = (
        pressure_si * volume_si
        - amount_si * IDEAL_GAS_CONSTANT_J_PER_MOL_K * temperature_si
    )

    if solve_key == "pressure":
        subst_pressure = (
            "P = \\frac{nRT}{V} = "
            f"\\frac{{{amount_si:.6g}\\,\\text{{mol}}"
            f"\\times {IDEAL_GAS_CONSTANT_J_PER_MOL_K:.6g}\\,\\text{{J/(mol*K)}}"
            f"\\times {temperature_si:.6g}\\,\\text{{K}}}}"
            f"{{{volume_si:.6g}\\,\\text{{m^3}}}}"
            f" = {pressure_si:.6g}\\,\\text{{Pa}}"
        )
    else:
        subst_pressure = (
            f"P = {pressure_si:.6g}\\,\\text{{Pa}}"
            "\\quad (\\text{input})"
        )

    if solve_key == "volume":
        subst_volume = (
            "V = \\frac{nRT}{P} = "
            f"\\frac{{{amount_si:.6g}\\,\\text{{mol}}"
            f"\\times {IDEAL_GAS_CONSTANT_J_PER_MOL_K:.6g}\\,\\text{{J/(mol*K)}}"
            f"\\times {temperature_si:.6g}\\,\\text{{K}}}}"
            f"{{{pressure_si:.6g}\\,\\text{{Pa}}}}"
            f" = {volume_si:.6g}\\,\\text{{m^3}}"
        )
    else:
        subst_volume = (
            f"V = {volume_si:.6g}\\,\\text{{m^3}}"
            "\\quad (\\text{input})"
        )

    if solve_key == "amount":
        subst_amount = (
            "n = \\frac{PV}{RT} = "
            f"\\frac{{{pressure_si:.6g}\\,\\text{{Pa}}"
            f"\\times {volume_si:.6g}\\,\\text{{m^3}}}}"
            f"{{{IDEAL_GAS_CONSTANT_J_PER_MOL_K:.6g}\\,\\text{{J/(mol*K)}}"
            f"\\times {temperature_si:.6g}\\,\\text{{K}}}}"
            f" = {amount_si:.6g}\\,\\text{{mol}}"
        )
    else:
        subst_amount = (
            f"n = {amount_si:.6g}\\,\\text{{mol}}"
            "\\quad (\\text{input})"
        )

    if solve_key == "temperature":
        subst_temperature = (
            "T = \\frac{PV}{nR} = "
            f"\\frac{{{pressure_si:.6g}\\,\\text{{Pa}}"
            f"\\times {volume_si:.6g}\\,\\text{{m^3}}}}"
            f"{{{amount_si:.6g}\\,\\text{{mol}}"
            f"\\times {IDEAL_GAS_CONSTANT_J_PER_MOL_K:.6g}\\,\\text{{J/(mol*K)}}}}"
            f" = {temperature_si:.6g}\\,\\text{{K}}"
        )
    else:
        subst_temperature = (
            f"T = {temperature_si:.6g}\\,\\text{{K}}"
            "\\quad (\\text{input})"
        )

    subst_residual = (
        "P V - n R T = "
        f"{pressure_si:.6g}\\times {volume_si:.6g}"
        f" - {amount_si:.6g}\\times {IDEAL_GAS_CONSTANT_J_PER_MOL_K:.6g}\\times {temperature_si:.6g}"
        f" = {equation_residual:.3e}"
    )

    return {
        "pressure_output": pressure_output,
        "volume_output": volume_output,
        "amount_output": amount_output,
        "temperature_output": temperature_output,
        "pressure_si_pa": pressure_si,
        "volume_si_m3": volume_si,
        "amount_si_mol": amount_si,
        "temperature_si_k": temperature_si,
        "gas_constant_j_per_mol_k": IDEAL_GAS_CONSTANT_J_PER_MOL_K,
        "equation_residual_pa_m3": equation_residual,
        "solved_variable": solve_key,
        "subst_pressure_output": subst_pressure,
        "subst_volume_output": subst_volume,
        "subst_amount_output": subst_amount,
        "subst_temperature_output": subst_temperature,
        "subst_equation_residual_pa_m3": subst_residual,
    }
