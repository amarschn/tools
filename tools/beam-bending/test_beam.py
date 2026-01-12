"""Unit tests for the beam bending calculations (beam_analysis module)."""

from __future__ import annotations

import unittest

from pycalcs import beam_analysis


class BeamAnalysisTests(unittest.TestCase):
    """Validate section properties and beam analysis calculations."""

    def test_rectangular_section_properties(self) -> None:
        """Rectangular section should match textbook formulas."""
        dims = {"width": 0.2, "depth": 0.4}
        props = beam_analysis.compute_section_properties("rectangular", dims)

        expected_ix = dims["width"] * dims["depth"] ** 3 / 12.0
        expected_c = dims["depth"] / 2.0

        self.assertAlmostEqual(props["area"], dims["width"] * dims["depth"])
        self.assertAlmostEqual(props["Ix"], expected_ix)
        self.assertAlmostEqual(props["Sx_top"], expected_ix / expected_c)
        self.assertAlmostEqual(props["Sx_bottom"], expected_ix / expected_c)

    def test_circular_section_properties(self) -> None:
        """Circular solid section should match textbook formulas."""
        import math
        dims = {"diameter": 0.1}
        props = beam_analysis.compute_section_properties("circular_solid", dims)

        d = dims["diameter"]
        expected_area = math.pi * d**2 / 4
        expected_ix = math.pi * d**4 / 64
        expected_c = d / 2

        self.assertAlmostEqual(props["area"], expected_area)
        self.assertAlmostEqual(props["Ix"], expected_ix)
        self.assertAlmostEqual(props["Sx_top"], expected_ix / expected_c)

    def test_t_section_asymmetric(self) -> None:
        """T-section should have different c_top and c_bottom."""
        dims = {
            "flange_width": 0.2,
            "flange_thickness": 0.02,
            "stem_depth": 0.18,
            "stem_thickness": 0.02,
        }
        props = beam_analysis.compute_section_properties("t_section", dims)

        # T-section is asymmetric - c_top != c_bottom
        self.assertNotAlmostEqual(props["c_top"], props["c_bottom"])
        # Section moduli should also differ
        self.assertNotAlmostEqual(props["Sx_top"], props["Sx_bottom"])

    def test_simply_supported_point_center(self) -> None:
        """Maximum response metrics align with closed-form solutions."""
        span = 5.0
        load = 12_000.0
        modulus = 210e9
        dims = {"width": 0.3, "depth": 0.45}

        props = beam_analysis.compute_section_properties("rectangular", dims)
        result = beam_analysis.beam_analysis(
            load_case="simply_supported_point_center",
            section_type="rectangular",
            section_dimensions=dims,
            span=span,
            load_value=load,
            elastic_modulus=modulus,
            yield_strength=250e6,
            num_points=101,
        )

        expected_delta = load * span**3 / (48 * modulus * props["Ix"])
        expected_moment = load * span / 4.0
        expected_shear = load / 2.0

        self.assertAlmostEqual(result["max_deflection"], expected_delta, places=6)
        self.assertAlmostEqual(result["max_moment"], expected_moment, places=6)
        self.assertAlmostEqual(result["max_shear"], expected_shear, places=6)

    def test_cantilever_udl(self) -> None:
        """Uniformly loaded cantilever should report textbook maxima."""
        span = 3.5
        w = 5_500.0  # N/m
        modulus = 200e9
        dims = {"width": 0.25, "depth": 0.35}

        props = beam_analysis.compute_section_properties("rectangular", dims)
        result = beam_analysis.beam_analysis(
            load_case="cantilever_udl",
            section_type="rectangular",
            section_dimensions=dims,
            span=span,
            load_value=w,
            elastic_modulus=modulus,
            yield_strength=250e6,
            num_points=101,
        )

        expected_delta = w * span**4 / (8 * modulus * props["Ix"])
        expected_moment = w * span**2 / 2.0
        expected_shear = w * span
        expected_stress = expected_moment * (dims["depth"] / 2.0) / props["Ix"]

        self.assertAlmostEqual(result["max_deflection"], expected_delta, places=6)
        self.assertAlmostEqual(result["max_deflection_position"], span, places=6)
        self.assertAlmostEqual(result["max_moment"], expected_moment, places=6)
        self.assertAlmostEqual(result["max_shear"], expected_shear, places=6)
        self.assertAlmostEqual(result["max_stress"], expected_stress, places=6)

    def test_simply_supported_udl(self) -> None:
        """Simply supported beam with UDL should match textbook values."""
        span = 6.0
        w = 10_000.0  # N/m
        modulus = 200e9
        dims = {"width": 0.2, "depth": 0.4}

        props = beam_analysis.compute_section_properties("rectangular", dims)
        result = beam_analysis.beam_analysis(
            load_case="simply_supported_udl",
            section_type="rectangular",
            section_dimensions=dims,
            span=span,
            load_value=w,
            elastic_modulus=modulus,
            yield_strength=250e6,
        )

        expected_delta = 5 * w * span**4 / (384 * modulus * props["Ix"])
        expected_moment = w * span**2 / 8.0
        expected_shear = w * span / 2.0

        self.assertAlmostEqual(result["max_deflection"], expected_delta, places=6)
        self.assertAlmostEqual(result["max_moment"], expected_moment, places=6)
        self.assertAlmostEqual(result["max_shear"], expected_shear, places=6)

    def test_custom_deflection_ratio(self) -> None:
        """Custom deflection ratio should work correctly."""
        span = 4.0
        load = 10_000.0
        dims = {"width": 0.15, "depth": 0.3}

        result = beam_analysis.beam_analysis(
            load_case="simply_supported_point_center",
            section_type="rectangular",
            section_dimensions=dims,
            span=span,
            load_value=load,
            elastic_modulus=200e9,
            yield_strength=250e6,
            deflection_limit="custom",
            custom_deflection_ratio=500,
        )

        expected_allowable = span / 500
        self.assertAlmostEqual(result["allowable_deflection"], expected_allowable)

    def test_custom_deflection_without_ratio_returns_error(self) -> None:
        """Selecting custom deflection without ratio should return error."""
        dims = {"width": 0.15, "depth": 0.3}

        result = beam_analysis.beam_analysis(
            load_case="simply_supported_point_center",
            section_type="rectangular",
            section_dimensions=dims,
            span=4.0,
            load_value=10_000.0,
            elastic_modulus=200e9,
            yield_strength=250e6,
            deflection_limit="custom",
            custom_deflection_ratio=None,
        )

        self.assertIn("error", result)

    def test_stress_top_bottom_reported(self) -> None:
        """Both top and bottom stresses should be reported."""
        dims = {"width": 0.2, "depth": 0.4}

        result = beam_analysis.beam_analysis(
            load_case="simply_supported_point_center",
            section_type="rectangular",
            section_dimensions=dims,
            span=5.0,
            load_value=10_000.0,
            elastic_modulus=200e9,
            yield_strength=250e6,
        )

        self.assertIn("stress_top", result)
        self.assertIn("stress_bottom", result)
        # For symmetric section, top and bottom should be equal
        self.assertAlmostEqual(result["stress_top"], result["stress_bottom"])


if __name__ == "__main__":
    unittest.main()
