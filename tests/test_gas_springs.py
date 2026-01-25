"""Tests for gas_springs module."""
import math
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pycalcs import gas_springs


class TestDoorMoment:
    """Tests for door moment (gravitational torque) calculations."""

    def test_door_moment_at_zero_angle(self):
        """At 0° (horizontal), door moment should be maximum."""
        # 10 kg door, CG at 0.4m from hinge
        moment = gas_springs.calculate_door_moment(
            mass=10.0,
            cg_distance=0.4,
            angle_deg=0.0
        )
        expected = 10.0 * 9.81 * 0.4 * math.cos(0)  # W * L_cg * cos(0) = W * L_cg
        assert abs(moment - expected) < 0.01
        assert abs(moment - 39.24) < 0.01  # 10 * 9.81 * 0.4

    def test_door_moment_at_90_degrees(self):
        """At 90° (vertical), door moment should be zero."""
        moment = gas_springs.calculate_door_moment(
            mass=10.0,
            cg_distance=0.4,
            angle_deg=90.0
        )
        assert abs(moment) < 0.01  # Should be effectively zero

    def test_door_moment_at_45_degrees(self):
        """At 45°, moment should be max * cos(45°)."""
        moment = gas_springs.calculate_door_moment(
            mass=10.0,
            cg_distance=0.4,
            angle_deg=45.0
        )
        expected = 10.0 * 9.81 * 0.4 * math.cos(math.radians(45))
        assert abs(moment - expected) < 0.01

    def test_door_moment_scales_with_mass(self):
        """Moment should scale linearly with mass."""
        moment_10kg = gas_springs.calculate_door_moment(10.0, 0.4, 30.0)
        moment_20kg = gas_springs.calculate_door_moment(20.0, 0.4, 30.0)
        assert abs(moment_20kg - 2 * moment_10kg) < 0.01


class TestSpringGeometry:
    """Tests for spring geometry calculations."""

    def test_spring_length_door_horizontal(self):
        """Test spring length when door is horizontal (θ=0)."""
        geom = gas_springs.calculate_spring_geometry(
            door_mount_distance=0.5,  # Door mount 0.5m from hinge
            frame_mount_x=0.3,  # Frame mount 0.3m forward
            frame_mount_y=-0.2,  # Frame mount 0.2m below
            angle_deg=0.0
        )
        # Door mount at (0.5, 0), frame mount at (0.3, -0.2)
        # Distance = sqrt((0.5-0.3)² + (0-(-0.2))²) = sqrt(0.04 + 0.04) = sqrt(0.08)
        expected_length = math.sqrt(0.08)
        assert abs(geom["spring_length"] - expected_length) < 0.001

    def test_spring_length_door_vertical(self):
        """Test spring length when door is vertical (θ=90)."""
        geom = gas_springs.calculate_spring_geometry(
            door_mount_distance=0.5,
            frame_mount_x=0.3,
            frame_mount_y=-0.2,
            angle_deg=90.0
        )
        # Door mount at (0, 0.5), frame mount at (0.3, -0.2)
        # Distance = sqrt((0-0.3)² + (0.5-(-0.2))²) = sqrt(0.09 + 0.49) = sqrt(0.58)
        expected_length = math.sqrt(0.58)
        assert abs(geom["spring_length"] - expected_length) < 0.001

    def test_lever_arm_calculation(self):
        """Test that lever arm is calculated correctly."""
        geom = gas_springs.calculate_spring_geometry(
            door_mount_distance=0.5,
            frame_mount_x=0.3,
            frame_mount_y=-0.2,
            angle_deg=0.0
        )
        # Cross product formula: |A_x * B_y - A_y * B_x| / L
        # A = (0.3, -0.2), B = (0.5, 0)
        # |0.3 * 0 - (-0.2) * 0.5| / sqrt(0.08) = |0.1| / 0.283 = 0.354
        expected_lever = abs(0.3 * 0 - (-0.2) * 0.5) / math.sqrt(0.08)
        assert abs(geom["lever_arm"] - expected_lever) < 0.001

    def test_door_mount_position_rotates(self):
        """Verify door mount position rotates correctly with angle."""
        # At 0°
        geom_0 = gas_springs.calculate_spring_geometry(0.5, 0.3, -0.2, 0.0)
        assert abs(geom_0["door_mount_x"] - 0.5) < 0.001
        assert abs(geom_0["door_mount_y"] - 0.0) < 0.001

        # At 90°
        geom_90 = gas_springs.calculate_spring_geometry(0.5, 0.3, -0.2, 90.0)
        assert abs(geom_90["door_mount_x"] - 0.0) < 0.001
        assert abs(geom_90["door_mount_y"] - 0.5) < 0.001


class TestSpringForce:
    """Tests for spring force calculations."""

    def test_constant_force_spring(self):
        """Force ratio 1.0 should give constant force."""
        force = gas_springs.calculate_spring_force_linear(
            nominal_force=200.0,
            stroke=0.1,
            current_length=0.25,
            min_length=0.2,
            force_ratio=1.0
        )
        assert abs(force - 200.0) < 0.01

    def test_force_at_min_extension(self):
        """At minimum extension, force should be at compressed value."""
        force = gas_springs.calculate_spring_force_linear(
            nominal_force=200.0,
            stroke=0.1,
            current_length=0.2,  # At min length
            min_length=0.2,
            force_ratio=1.4  # 40% force increase over stroke
        )
        # Compressed force = 200 / sqrt(1.4) ≈ 169
        expected = 200.0 / math.sqrt(1.4)
        assert abs(force - expected) < 1.0

    def test_force_at_max_extension(self):
        """At maximum extension, force should be at extended value."""
        force = gas_springs.calculate_spring_force_linear(
            nominal_force=200.0,
            stroke=0.1,
            current_length=0.3,  # At max length (min + stroke)
            min_length=0.2,
            force_ratio=1.4
        )
        # Extended force = compressed * 1.4
        f_compressed = 200.0 / math.sqrt(1.4)
        expected = f_compressed * 1.4
        assert abs(force - expected) < 1.0


class TestSpringMoment:
    """Tests for spring moment calculations."""

    def test_spring_moment_positive_lever(self):
        """Positive lever arm should give positive moment."""
        moment = gas_springs.calculate_spring_moment(
            spring_force=200.0,
            lever_arm_signed=0.1
        )
        assert abs(moment - 20.0) < 0.01

    def test_spring_moment_negative_lever(self):
        """Negative lever arm should give negative moment."""
        moment = gas_springs.calculate_spring_moment(
            spring_force=200.0,
            lever_arm_signed=-0.1
        )
        assert abs(moment - (-20.0)) < 0.01


class TestHandForce:
    """Tests for hand force calculations."""

    def test_hand_force_positive_net_moment(self):
        """Positive net moment requires upward hand force."""
        force = gas_springs.calculate_hand_force(
            net_moment=20.0,  # Door wants to close
            hand_distance=0.8
        )
        assert abs(force - 25.0) < 0.01  # 20 / 0.8

    def test_hand_force_zero_net_moment(self):
        """Zero net moment requires no hand force."""
        force = gas_springs.calculate_hand_force(
            net_moment=0.0,
            hand_distance=0.8
        )
        assert abs(force) < 0.01


class TestMechanismAnalysis:
    """Tests for full mechanism analysis."""

    def test_basic_analysis_runs(self):
        """Test that basic analysis completes without error."""
        result = gas_springs.analyze_mechanism(
            door_mass=15.0,
            door_length=0.8,
            cg_fraction=0.5,
            door_mount_fraction=0.7,
            frame_mount_x=0.3,
            frame_mount_y=-0.15,
            spring_force=150.0,
            open_angle=90.0
        )

        assert "angles" in result
        assert "door_moments" in result
        assert "spring_moments" in result
        assert "hand_forces" in result
        assert "spring_stroke" in result
        assert len(result["angles"]) > 0
        assert len(result["door_moments"]) == len(result["angles"])

    def test_analysis_angle_range(self):
        """Test that analysis covers full angle range."""
        result = gas_springs.analyze_mechanism(
            door_mass=15.0,
            door_length=0.8,
            cg_fraction=0.5,
            door_mount_fraction=0.7,
            frame_mount_x=0.3,
            frame_mount_y=-0.15,
            spring_force=150.0,
            open_angle=90.0
        )

        assert result["angles"][0] == 0.0
        assert result["angles"][-1] == 90.0

    def test_door_moment_decreases_with_angle(self):
        """Door moment should decrease as angle increases toward 90°."""
        result = gas_springs.analyze_mechanism(
            door_mass=15.0,
            door_length=0.8,
            cg_fraction=0.5,
            door_mount_fraction=0.7,
            frame_mount_x=0.3,
            frame_mount_y=-0.15,
            spring_force=150.0,
            open_angle=90.0
        )

        # Moment at 0° should be greater than at 45°
        assert result["door_moments"][0] > result["door_moments"][45]
        # Moment at 45° should be greater than at 90°
        assert result["door_moments"][45] > result["door_moments"][-1]

    def test_invalid_inputs_raise_errors(self):
        """Test that invalid inputs raise appropriate errors."""
        with pytest.raises(ValueError):
            gas_springs.analyze_mechanism(
                door_mass=-5.0,  # Invalid: negative mass
                door_length=0.8,
                cg_fraction=0.5,
                door_mount_fraction=0.7,
                frame_mount_x=0.3,
                frame_mount_y=-0.15,
                spring_force=150.0
            )

        with pytest.raises(ValueError):
            gas_springs.analyze_mechanism(
                door_mass=15.0,
                door_length=0.8,
                cg_fraction=1.5,  # Invalid: CG beyond door edge
                door_mount_fraction=0.7,
                frame_mount_x=0.3,
                frame_mount_y=-0.15,
                spring_force=150.0
            )


class TestRecommendSpring:
    """Tests for spring recommendation function."""

    def test_recommend_returns_positive_force(self):
        """Recommended force should be positive."""
        result = gas_springs.recommend_spring(
            door_mass=15.0,
            door_length=0.8
        )
        assert result["recommended_force"] > 0
        assert result["optimal_force"] > 0

    def test_recommend_returns_stroke(self):
        """Recommendation should include stroke."""
        result = gas_springs.recommend_spring(
            door_mass=15.0,
            door_length=0.8
        )
        assert result["recommended_stroke"] > 0
        assert result["min_stroke"] > 0

    def test_heavier_door_needs_more_force(self):
        """Heavier door should require more spring force."""
        result_light = gas_springs.recommend_spring(
            door_mass=10.0,
            door_length=0.8
        )
        result_heavy = gas_springs.recommend_spring(
            door_mass=30.0,
            door_length=0.8
        )
        assert result_heavy["recommended_force"] > result_light["recommended_force"]

    def test_longer_door_needs_more_force(self):
        """Longer door should require more spring force (all else equal)."""
        result_short = gas_springs.recommend_spring(
            door_mass=15.0,
            door_length=0.5
        )
        result_long = gas_springs.recommend_spring(
            door_mass=15.0,
            door_length=1.0
        )
        assert result_long["recommended_force"] > result_short["recommended_force"]

    def test_more_springs_reduces_per_spring_force(self):
        """Using more springs should reduce force per spring."""
        result_1_spring = gas_springs.recommend_spring(
            door_mass=15.0,
            door_length=0.8,
            num_springs=1
        )
        result_2_springs = gas_springs.recommend_spring(
            door_mass=15.0,
            door_length=0.8,
            num_springs=2
        )
        # Per-spring force with 2 springs should be roughly half
        assert result_2_springs["recommended_force"] < result_1_spring["recommended_force"]

    def test_safety_factor_applied(self):
        """Recommended force should include safety factor."""
        result = gas_springs.recommend_spring(
            door_mass=15.0,
            door_length=0.8,
            safety_factor=1.5
        )
        # Recommended should be 1.5x optimal
        assert abs(result["recommended_force"] / result["optimal_force"] - 1.5) < 0.1


class TestKnownValues:
    """Tests against known/reference values."""

    def test_typical_trap_door_scenario(self):
        """Test a typical trap door scenario with expected results."""
        # 15 kg door, 0.8m length, uniform (CG at 0.4m)
        # Expected door moment at 0°: 15 * 9.81 * 0.4 = 58.86 N·m
        result = gas_springs.analyze_mechanism(
            door_mass=15.0,
            door_length=0.8,
            cg_fraction=0.5,
            door_mount_fraction=0.7,
            frame_mount_x=0.3,
            frame_mount_y=-0.15,
            spring_force=0.0,  # No spring for this check
            open_angle=90.0
        )

        expected_moment_at_0 = 15.0 * 9.81 * 0.4
        assert abs(result["door_moments"][0] - expected_moment_at_0) < 0.1

    def test_spring_stroke_reasonable_range(self):
        """Spring stroke should be within reasonable range for typical geometry."""
        result = gas_springs.recommend_spring(
            door_mass=15.0,
            door_length=0.8,
            door_mount_fraction=0.7,
            frame_mount_x=0.3,
            frame_mount_y=-0.15
        )
        # For typical geometry, stroke should be roughly 100-300mm
        assert 50 < result["min_stroke"] < 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
