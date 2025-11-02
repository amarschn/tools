"""Smoke tests for the shared unit conversion helpers."""

from __future__ import annotations

import math
import unittest

from pycalcs import units


class UnitConversionTests(unittest.TestCase):
    """Sanity checks for linear and affine conversions."""

    def test_length_conversion(self) -> None:
        """Feet to metres should match the defined factor."""
        value_ft = 12.0
        converted = units.convert_value("length", "ft", "m", value_ft)
        self.assertAlmostEqual(converted, 12.0 * 0.3048)

    def test_length_astronomical_units(self) -> None:
        """Light-year to metres uses the defined astronomical factor."""
        metres = units.convert_value("length", "ly", "m", 1.0)
        self.assertAlmostEqual(metres, 9.460_730_472_580_8e15)

    def test_temperature_affine(self) -> None:
        """Temperature conversions must handle offsets."""
        freezing_c = units.convert_value("temperature", "°F", "°C", 32.0)
        boiling_f = units.convert_value("temperature", "°C", "°F", 100.0)
        self.assertAlmostEqual(freezing_c, 0.0, places=6)
        self.assertAlmostEqual(boiling_f, 212.0, places=6)

    def test_energy_electronvolt(self) -> None:
        """Electronvolts convert to joules using the elementary charge."""
        joules = units.convert_value("energy", "MeV", "J", 2.0)
        expected = 2.0 * 1.602176634e-13
        self.assertAlmostEqual(joules, expected)

    def test_energy_calorie(self) -> None:
        """Nutritional calories map to joules."""
        joules = units.convert_value("energy", "Cal", "J", 0.5)
        self.assertAlmostEqual(joules, 0.5 * 4184.0)

    def test_current_units(self) -> None:
        """Current conversion handles milliampere to ampere."""
        amps = units.convert_value("current", "mA", "A", 250.0)
        self.assertAlmostEqual(amps, 0.25)

    def test_time_units(self) -> None:
        """Minutes convert to seconds accurately."""
        seconds = units.convert_value("time", "min", "s", 2.5)
        self.assertAlmostEqual(seconds, 150.0)

    def test_linear_stiffness_units(self) -> None:
        """Lbf per inch converts to newton per metre."""
        stiffness = units.convert_value("linear_stiffness", "lbf/in", "N/m", 1.0)
        self.assertAlmostEqual(stiffness, 175.126835, places=6)

    def test_angle_arcminute(self) -> None:
        """Arcminute conversion maps to radians."""
        radians = units.convert_value("angle", "amin", "rad", 30.0)
        self.assertAlmostEqual(radians, 30.0 * (math.pi / (180.0 * 60.0)))

    def test_pressure_ksi(self) -> None:
        """Kilopound per square inch converts to pascals."""
        pascals = units.convert_value("pressure", "ksi", "Pa", 1.0)
        self.assertAlmostEqual(pascals, 6.894757293168e6)

    def test_conversion_factor_linear_only(self) -> None:
        """Multiplicative factor should exist for linear conversions."""
        factor = units.conversion_factor("pressure", "psi", "kPa")
        self.assertAlmostEqual(factor, 6.894757293168)
        with self.assertRaises(ValueError):
            units.conversion_factor("temperature", "°C", "°F")

    def test_convert_units_structure(self) -> None:
        """Top-level helper should report multiplier metadata."""
        result = units.convert_units("force", "kN", "lbf", 5.0)
        self.assertAlmostEqual(result["converted_value"], 5_000.0 / 4.4482216152605, places=6)
        self.assertAlmostEqual(result["base_value"], 5_000.0, places=6)
        self.assertTrue(result["has_multiplier_only"])
        self.assertGreater(result["multiplier"], 0.0)


if __name__ == "__main__":
    unittest.main()
