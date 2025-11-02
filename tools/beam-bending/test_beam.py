"""Unit tests for the beam bending shared calculations."""

from __future__ import annotations

import unittest

from pycalcs import structures


class BeamBendingSharedTests(unittest.TestCase):
    """Validate section properties and response calculations."""

    def test_rectangular_section_properties(self) -> None:
        """Rectangular section should match textbook formulas."""
        dims = {"width": 0.2, "depth": 0.4}
        props = structures.compute_section_properties("rectangular", dims)

        expected_ix = dims["width"] * dims["depth"] ** 3 / 12.0
        expected_c = dims["depth"] / 2.0

        self.assertAlmostEqual(props["area"], dims["width"] * dims["depth"])
        self.assertAlmostEqual(props["ix"], expected_ix)
        self.assertAlmostEqual(props["section_modulus_top"], expected_ix / expected_c)
        self.assertAlmostEqual(props["section_modulus_bottom"], expected_ix / expected_c)

    def test_simply_supported_point_midspan(self) -> None:
        """Maximum response metrics align with closed-form solutions."""
        span = 5.0
        load = 12_000.0
        modulus = 210e9
        dims = {"width": 0.3, "depth": 0.45}

        props = structures.compute_section_properties("rectangular", dims)
        result = structures.beam_deflection_analysis(
            section_type="rectangular",
            section_dimensions=dims,
            span=span,
            elastic_modulus=modulus,
            load_case="simply_supported_point_midspan",
            load_value=load,
            load_position=None,
            num_points=101,
        )

        expected_delta = load * span**3 / (48 * modulus * props["ix"])
        expected_moment = load * span / 4.0
        expected_shear = load / 2.0

        self.assertAlmostEqual(result["max_deflection"], expected_delta, places=6)
        self.assertAlmostEqual(result["max_bending_moment"], expected_moment, places=6)
        self.assertAlmostEqual(result["max_shear_force"], expected_shear, places=6)

    def test_cantilever_uniform_load(self) -> None:
        """Uniformly loaded cantilever should report textbook maxima."""
        span = 3.5
        w = 5_500.0  # N/m
        modulus = 200e9
        dims = {"width": 0.25, "depth": 0.35}

        props = structures.compute_section_properties("rectangular", dims)
        result = structures.beam_deflection_analysis(
            section_type="rectangular",
            section_dimensions=dims,
            span=span,
            elastic_modulus=modulus,
            load_case="cantilever_uniform",
            load_value=w,
            load_position=None,
            num_points=101,
        )

        expected_delta = w * span**4 / (8 * modulus * props["ix"])
        expected_moment = w * span**2 / 2.0
        expected_shear = w * span
        expected_stress = expected_moment * (dims["depth"] / 2.0) / props["ix"]

        self.assertAlmostEqual(result["max_deflection"], expected_delta, places=6)
        self.assertAlmostEqual(result["max_deflection_position"], span, places=6)
        self.assertAlmostEqual(result["max_bending_moment"], expected_moment, places=6)
        self.assertAlmostEqual(result["max_shear_force"], expected_shear, places=6)
        self.assertAlmostEqual(result["extreme_fiber_stress"], expected_stress, places=6)


if __name__ == "__main__":
    unittest.main()
