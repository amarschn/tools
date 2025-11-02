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

    def test_temperature_affine(self) -> None:
        """Temperature conversions must handle offsets."""
        freezing_c = units.convert_value("temperature", "°F", "°C", 32.0)
        boiling_f = units.convert_value("temperature", "°C", "°F", 100.0)
        self.assertAlmostEqual(freezing_c, 0.0, places=6)
        self.assertAlmostEqual(boiling_f, 212.0, places=6)

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
