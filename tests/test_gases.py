"""Tests for pycalcs/gases.py."""

from __future__ import annotations

import pytest

from pycalcs.gases import IDEAL_GAS_CONSTANT_J_PER_MOL_K, solve_ideal_gas_law


def test_solve_pressure_stp_reference_case() -> None:
    """
    STP molar volume reference:
    n = 1 mol, T = 273.15 K, V = 0.022414 m^3 => P ~= 101325 Pa.
    """
    results = solve_ideal_gas_law(
        solve_for="pressure",
        pressure_value=0.0,
        pressure_unit="kPa",
        volume_value=0.022414,
        volume_unit="m^3",
        amount_value=1.0,
        amount_unit="mol",
        temperature_value=273.15,
        temperature_unit="K",
    )

    assert results["pressure_si_pa"] == pytest.approx(101325.0, rel=2e-4)
    assert results["pressure_output"] == pytest.approx(101.325, rel=2e-4)
    assert abs(results["equation_residual_pa_m3"]) < 1e-10
    assert results["solved_variable"] == "pressure"


def test_solve_volume_in_liters() -> None:
    """2 mol at 25 C and 1 atm should occupy about 48.93 L."""
    results = solve_ideal_gas_law(
        solve_for="volume",
        pressure_value=1.0,
        pressure_unit="atm",
        volume_value=0.0,
        volume_unit="L",
        amount_value=2.0,
        amount_unit="mol",
        temperature_value=25.0,
        temperature_unit="degC",
    )

    expected_volume_m3 = (2.0 * IDEAL_GAS_CONSTANT_J_PER_MOL_K * 298.15) / 101325.0
    assert results["volume_si_m3"] == pytest.approx(expected_volume_m3, rel=1e-9)
    assert results["volume_output"] == pytest.approx(expected_volume_m3 * 1000.0, rel=1e-9)
    assert abs(results["equation_residual_pa_m3"]) < 1e-10


def test_solve_amount_with_imperial_mix() -> None:
    """Check amount solving with psi + ft^3 + degF inputs."""
    results = solve_ideal_gas_law(
        solve_for="amount",
        pressure_value=30.0,
        pressure_unit="psi",
        volume_value=2.0,
        volume_unit="ft^3",
        amount_value=0.0,
        amount_unit="mol",
        temperature_value=80.0,
        temperature_unit="degF",
    )

    pressure_pa = 30.0 * 6894.757293168
    volume_m3 = 2.0 * 0.028316846592
    temperature_k = (80.0 - 32.0) * (5.0 / 9.0) + 273.15
    expected_mol = (pressure_pa * volume_m3) / (
        IDEAL_GAS_CONSTANT_J_PER_MOL_K * temperature_k
    )

    assert results["amount_si_mol"] == pytest.approx(expected_mol, rel=1e-9)
    assert results["amount_output"] == pytest.approx(expected_mol, rel=1e-9)
    assert results["solved_variable"] == "amount"


def test_solve_temperature_rankine_output() -> None:
    """Solve temperature and request degR output."""
    results = solve_ideal_gas_law(
        solve_for="temperature",
        pressure_value=200.0,
        pressure_unit="kPa",
        volume_value=0.75,
        volume_unit="m^3",
        amount_value=50.0,
        amount_unit="mol",
        temperature_value=0.0,
        temperature_unit="degR",
    )

    expected_k = (200000.0 * 0.75) / (50.0 * IDEAL_GAS_CONSTANT_J_PER_MOL_K)
    assert results["temperature_si_k"] == pytest.approx(expected_k, rel=1e-9)
    assert results["temperature_output"] == pytest.approx(expected_k * 9.0 / 5.0, rel=1e-9)


def test_invalid_solve_target_raises() -> None:
    with pytest.raises(ValueError, match="solve_for must be one of"):
        solve_ideal_gas_law(
            solve_for="density",
            pressure_value=101325.0,
            pressure_unit="Pa",
            volume_value=1.0,
            volume_unit="m^3",
            amount_value=1.0,
            amount_unit="mol",
            temperature_value=300.0,
            temperature_unit="K",
        )


def test_temperature_below_absolute_zero_raises() -> None:
    with pytest.raises(ValueError, match="temperature_value"):
        solve_ideal_gas_law(
            solve_for="pressure",
            pressure_value=0.0,
            pressure_unit="Pa",
            volume_value=1.0,
            volume_unit="m^3",
            amount_value=1.0,
            amount_unit="mol",
            temperature_value=-500.0,
            temperature_unit="degF",
        )


def test_non_solved_input_must_be_positive() -> None:
    with pytest.raises(ValueError, match="volume_value must be greater than zero"):
        solve_ideal_gas_law(
            solve_for="pressure",
            pressure_value=0.0,
            pressure_unit="Pa",
            volume_value=0.0,
            volume_unit="m^3",
            amount_value=1.0,
            amount_unit="mol",
            temperature_value=300.0,
            temperature_unit="K",
        )


def test_nonfinite_input_rejected() -> None:
    with pytest.raises(ValueError, match="must be a finite number"):
        solve_ideal_gas_law(
            solve_for="pressure",
            pressure_value=0.0,
            pressure_unit="Pa",
            volume_value=float("nan"),
            volume_unit="m^3",
            amount_value=1.0,
            amount_unit="mol",
            temperature_value=300.0,
            temperature_unit="K",
        )
