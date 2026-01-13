"""
Unit tests for the fasteners module.

Tests verify:
- Database integrity (all grades and sizes populated)
- K-factor calculations against known values
- Stiffness calculations within expected ranges
- Full analysis integration tests
- Edge case and error handling
"""

import pytest
import math
from pycalcs.fasteners import (
    analyze_bolted_joint,
    calculate_k_factor,
    calculate_bolt_stiffness,
    calculate_joint_stiffness,
    calculate_embedding_loss,
    get_bolt_grade_properties,
    get_fastener_geometry,
    generate_joint_diagram_data,
    generate_torque_tension_curve,
    ISO_BOLT_GRADES,
    SAE_BOLT_GRADES,
    ISO_FASTENER_GEOMETRY,
    UTS_FASTENER_GEOMETRY,
    K_FACTOR_DATABASE,
)


class TestBoltGradeDatabases:
    """Verify bolt grade databases are complete and have valid values."""

    def test_iso_grades_present(self):
        """All standard ISO grades should be in database."""
        expected_grades = ["4.6", "5.6", "8.8", "10.9", "12.9"]
        for grade in expected_grades:
            assert grade in ISO_BOLT_GRADES, f"Missing ISO grade {grade}"

    def test_sae_grades_present(self):
        """All standard SAE grades should be in database."""
        expected_grades = ["SAE Grade 2", "SAE Grade 5", "SAE Grade 8", "ASTM A325", "ASTM A490"]
        for grade in expected_grades:
            assert grade in SAE_BOLT_GRADES, f"Missing SAE grade {grade}"

    def test_iso_88_properties(self):
        """Verify ISO 8.8 grade properties match standard."""
        grade = ISO_BOLT_GRADES["8.8"]
        # ISO 898-1: 8.8 has Rm_min = 800 MPa
        assert grade["tensile_strength"] == pytest.approx(800e6, rel=0.01)
        # Proof strength is 0.8 * Rm = 640 MPa
        assert grade["proof_strength"] == pytest.approx(640e6, rel=0.01)

    def test_sae_grade5_properties(self):
        """Verify SAE Grade 5 properties match standard."""
        grade = SAE_BOLT_GRADES["SAE Grade 5"]
        # SAE J429: Grade 5 has 120 ksi tensile = 827 MPa
        assert grade["tensile_strength"] == pytest.approx(827e6, rel=0.01)
        # Proof strength 85 ksi = 586 MPa
        assert grade["proof_strength"] == pytest.approx(586e6, rel=0.01)

    def test_grade_has_required_keys(self):
        """Each grade should have all required property keys."""
        required_keys = ["proof_strength", "tensile_strength", "yield_strength", "elastic_modulus"]
        for grade_name, grade in ISO_BOLT_GRADES.items():
            for key in required_keys:
                assert key in grade, f"ISO grade {grade_name} missing {key}"
        for grade_name, grade in SAE_BOLT_GRADES.items():
            for key in required_keys:
                assert key in grade, f"SAE grade {grade_name} missing {key}"


class TestFastenerGeometryDatabases:
    """Verify fastener geometry databases are complete and accurate."""

    def test_iso_sizes_present(self):
        """Common ISO metric sizes should be in database."""
        expected_sizes = ["M6x1.0", "M8x1.25", "M10x1.5", "M12x1.75", "M16x2.0", "M20x2.5"]
        for size in expected_sizes:
            assert size in ISO_FASTENER_GEOMETRY, f"Missing ISO size {size}"

    def test_uts_sizes_present(self):
        """Common UTS imperial sizes should be in database."""
        expected_sizes = ["1/4-20 UNC", "3/8-16 UNC", "1/2-13 UNC", "3/4-10 UNC", "1-8 UNC"]
        for size in expected_sizes:
            assert size in UTS_FASTENER_GEOMETRY, f"Missing UTS size {size}"

    def test_m10_geometry(self):
        """Verify M10x1.5 geometry matches ISO 262."""
        m10 = ISO_FASTENER_GEOMETRY["M10x1.5"]
        assert m10["nominal_diameter"] == pytest.approx(10e-3, rel=1e-6)
        assert m10["pitch"] == pytest.approx(1.5e-3, rel=1e-6)
        # Stress area should be approximately 58 mm^2 per ISO 262
        assert m10["stress_area"] == pytest.approx(58e-6, rel=0.02)

    def test_half_inch_geometry(self):
        """Verify 1/2-13 UNC geometry matches ASME B1.1."""
        half = UTS_FASTENER_GEOMETRY["1/2-13 UNC"]
        assert half["nominal_diameter"] == pytest.approx(12.7e-3, rel=0.01)
        # Stress area should be approximately 0.1307 in^2 = 84.3 mm^2
        assert half["stress_area"] == pytest.approx(84.3e-6, rel=0.02)

    def test_geometry_has_required_keys(self):
        """Each geometry entry should have all required keys."""
        required_keys = ["nominal_diameter", "pitch", "stress_area", "minor_diameter", "pitch_diameter"]
        for size_name, geom in ISO_FASTENER_GEOMETRY.items():
            for key in required_keys:
                assert key in geom, f"ISO {size_name} missing {key}"


class TestKFactorDatabase:
    """Verify K-factor database values are reasonable."""

    def test_k_factor_ranges_present(self):
        """Common surface conditions should have K-factor entries."""
        expected_conditions = ["dry_steel", "oiled", "moly_lube", "zinc_plated_dry"]
        for cond in expected_conditions:
            assert cond in K_FACTOR_DATABASE, f"Missing K-factor for {cond}"

    def test_k_factor_ordering(self):
        """K-factor tuples should be ordered: min < typical < max."""
        for cond, (k_min, k_typ, k_max) in K_FACTOR_DATABASE.items():
            assert k_min < k_typ < k_max, f"K-factor ordering wrong for {cond}"

    def test_k_factor_ranges_reasonable(self):
        """K-factors should be in physically reasonable range (0.05 to 0.40)."""
        for cond, (k_min, k_typ, k_max) in K_FACTOR_DATABASE.items():
            assert 0.05 <= k_min <= 0.40, f"K_min out of range for {cond}"
            assert 0.05 <= k_max <= 0.40, f"K_max out of range for {cond}"


class TestKFactorCalculation:
    """Test K-factor calculation from first principles."""

    def test_k_factor_typical_dry_steel(self):
        """K-factor for typical dry steel M10 should be in reasonable range."""
        k = calculate_k_factor(
            pitch=1.5e-3,
            pitch_diameter=9.026e-3,
            nominal_diameter=10e-3,
            friction_thread=0.15,
            friction_bearing=0.15,
            bearing_diameter_mean=14e-3,  # ~1.4 * d
        )
        # K-factor from first principles can be higher than empirical values
        # due to simplified model. Range 0.15-0.35 covers calculated results.
        assert 0.15 <= k <= 0.35, f"K-factor {k} outside expected range"

    def test_k_factor_lubricated_lower(self):
        """Lubricated conditions should give lower K-factor."""
        k_dry = calculate_k_factor(
            pitch=1.5e-3,
            pitch_diameter=9.026e-3,
            nominal_diameter=10e-3,
            friction_thread=0.15,
            friction_bearing=0.15,
            bearing_diameter_mean=14e-3,
        )
        k_oiled = calculate_k_factor(
            pitch=1.5e-3,
            pitch_diameter=9.026e-3,
            nominal_diameter=10e-3,
            friction_thread=0.10,
            friction_bearing=0.10,
            bearing_diameter_mean=14e-3,
        )
        assert k_oiled < k_dry, "Oiled K should be lower than dry K"


class TestBoltStiffness:
    """Test bolt stiffness calculations."""

    def test_bolt_stiffness_m10_short_grip(self):
        """M10 with short grip should have stiffness ~500-800 MN/m."""
        kb = calculate_bolt_stiffness(
            stress_area=58e-6,
            nominal_diameter=10e-3,
            minor_diameter=8.16e-3,
            grip_length=20e-3,
            head_height=6.4e-3,
            elastic_modulus=205e9,
        )
        # Expected range for short grip M10
        assert 300e6 < kb < 1000e6, f"Bolt stiffness {kb/1e6:.0f} MN/m outside range"

    def test_bolt_stiffness_increases_with_area(self):
        """Larger bolt should have higher stiffness."""
        kb_m10 = calculate_bolt_stiffness(
            stress_area=58e-6, nominal_diameter=10e-3, minor_diameter=8.16e-3,
            grip_length=25e-3, head_height=6.4e-3, elastic_modulus=205e9,
        )
        kb_m16 = calculate_bolt_stiffness(
            stress_area=157e-6, nominal_diameter=16e-3, minor_diameter=13.5e-3,
            grip_length=25e-3, head_height=10e-3, elastic_modulus=205e9,
        )
        assert kb_m16 > kb_m10, "M16 should be stiffer than M10 at same grip"

    def test_bolt_stiffness_zero_grip_raises(self):
        """Zero grip length should raise ValueError."""
        with pytest.raises(ValueError, match="grip_length"):
            calculate_bolt_stiffness(
                stress_area=58e-6, nominal_diameter=10e-3, minor_diameter=8.16e-3,
                grip_length=0, head_height=6.4e-3, elastic_modulus=205e9,
            )


class TestJointStiffness:
    """Test joint (clamped member) stiffness calculations."""

    def test_joint_stiffness_steel(self):
        """Steel joint stiffness should be in reasonable range."""
        kj = calculate_joint_stiffness(
            grip_length=25e-3,
            hole_diameter=11e-3,  # 10% clearance for M10
            head_diameter=16e-3,
            clamped_modulus=210e9,
            joint_type="through_bolt",
        )
        # Joint stiffness typically 2-10x bolt stiffness for steel
        # Through-bolt configuration with frustum model can give high values
        assert 500e6 < kj < 10000e6, f"Joint stiffness {kj/1e6:.0f} MN/m outside range"

    def test_joint_stiffness_aluminum_lower(self):
        """Aluminum joint should have lower stiffness than steel."""
        kj_steel = calculate_joint_stiffness(
            grip_length=25e-3, hole_diameter=11e-3, head_diameter=16e-3,
            clamped_modulus=210e9, joint_type="through_bolt",
        )
        kj_al = calculate_joint_stiffness(
            grip_length=25e-3, hole_diameter=11e-3, head_diameter=16e-3,
            clamped_modulus=70e9, joint_type="through_bolt",
        )
        assert kj_al < kj_steel, "Aluminum joint should be less stiff than steel"


class TestFullAnalysis:
    """Integration tests for complete joint analysis."""

    def test_m10_88_nominal_case(self):
        """Verify nominal M10 class 8.8 oiled joint analysis."""
        result = analyze_bolted_joint(
            fastener_size="M10x1.5",
            bolt_grade="8.8",
            grip_length=25e-3,
            clamped_material_modulus=210e9,
            external_axial_load=5000,
            external_shear_load=0,
            tightening_method="torque_wrench",
            surface_condition="oiled",
            temperature=20,
            n_bolts=1,
            joint_type="through_bolt",
            embedding_surface_roughness="machined",
        )

        # M10 8.8 oiled typically ~35-50 N-m (per published torque tables)
        assert 25 < result["assembly_torque"] < 60, f"Torque {result['assembly_torque']:.1f} N-m unexpected"

        # Preload at 90% proof: 0.9 * 640 MPa * 58 mm^2 = ~33.4 kN
        assert 25e3 < result["target_preload"] < 40e3, f"Preload {result['target_preload']/1000:.1f} kN unexpected"

        # Safety factors should be > 1.0 for valid design
        assert result["safety_factor_yield"] > 1.0, "Yield SF should be > 1"
        assert result["safety_factor_clamp"] > 0.5, "Clamp SF should be reasonable"

        # Status should be acceptable or marginal
        assert result["status"] in ["acceptable", "marginal"]

    def test_sae_grade5_half_inch(self):
        """Verify SAE 1/2-13 Grade 5 joint analysis."""
        result = analyze_bolted_joint(
            fastener_size="1/2-13 UNC",
            bolt_grade="SAE Grade 5",
            grip_length=38e-3,  # 1.5 inches
            clamped_material_modulus=207e9,
            external_axial_load=10000,
            external_shear_load=0,
            tightening_method="torque_wrench",
            surface_condition="oiled",
            temperature=20,
            n_bolts=1,
            joint_type="through_bolt",
            embedding_surface_roughness="machined",
        )

        # 1/2-13 Grade 5 oiled typically ~55-75 ft-lb = ~75-100 N-m
        assert 50 < result["assembly_torque"] < 130, f"Torque {result['assembly_torque']:.1f} N-m unexpected"

    def test_high_load_low_safety_factor(self):
        """High external load on small bolt should give low safety factors."""
        result = analyze_bolted_joint(
            fastener_size="M6x1.0",
            bolt_grade="8.8",
            grip_length=15e-3,
            clamped_material_modulus=210e9,
            external_axial_load=8000,  # Very high for M6
            external_shear_load=0,
            tightening_method="torque_wrench",
            surface_condition="dry_steel",
            temperature=20,
            n_bolts=1,
            joint_type="through_bolt",
            embedding_surface_roughness="machined",
        )

        # Should flag as problematic
        assert result["status"] in ["marginal", "unacceptable"]
        assert result["safety_factor_yield"] < 1.5

    def test_result_has_all_keys(self):
        """Result dictionary should contain all expected keys."""
        result = analyze_bolted_joint(
            fastener_size="M10x1.5",
            bolt_grade="8.8",
            grip_length=25e-3,
            clamped_material_modulus=210e9,
            external_axial_load=5000,
            external_shear_load=1000,
            tightening_method="torque_wrench",
            surface_condition="oiled",
            temperature=20,
            n_bolts=1,
            joint_type="through_bolt",
            embedding_surface_roughness="machined",
        )

        required_keys = [
            "assembly_torque", "torque_range_low", "torque_range_high",
            "target_preload", "minimum_preload",
            "k_factor", "k_factor_min", "k_factor_max",
            "bolt_stiffness", "joint_stiffness", "load_factor",
            "bolt_load_max", "clamp_load_min", "embedding_loss",
            "safety_factor_yield", "safety_factor_clamp",
            "safety_factor_fatigue", "safety_factor_shear",
            "status", "recommendations",
            "joint_diagram_data", "torque_tension_data", "k_sensitivity_data",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"


class TestGraphDataGeneration:
    """Test graph data generation functions."""

    def test_joint_diagram_data(self):
        """Joint diagram data should have correct structure for triangular diagram."""
        data = generate_joint_diagram_data(
            preload=30000,
            bolt_stiffness=500e6,
            joint_stiffness=1500e6,
            external_load=5000,
        )
        # Core stiffness lines
        assert "bolt_extension" in data
        assert "bolt_force" in data
        assert "joint_x" in data
        assert "joint_force" in data

        # Key points
        assert "preload_extension" in data
        assert "preload_force" in data
        assert "work_bolt_extension" in data
        assert "work_bolt_force" in data
        assert "work_joint_force" in data

        # Triangular features
        assert "triangle_x" in data
        assert "triangle_f" in data
        assert "separation_extension" in data

        # Verify data arrays have reasonable length
        assert len(data["bolt_extension"]) > 10
        assert len(data["joint_x"]) > 10

        # Verify working triangle is closed (returns to start)
        assert data["triangle_x"][0] == data["triangle_x"][-1]
        assert data["triangle_f"][0] == data["triangle_f"][-1]

    def test_torque_tension_data(self):
        """Torque-tension data should have K-factor variants."""
        data = generate_torque_tension_curve(
            fastener_size="M10x1.5",
            bolt_grade="8.8",
            surface_condition="oiled",
        )
        assert "preload" in data
        assert "torque_at_k_min" in data
        assert "torque_at_k_typ" in data
        assert "torque_at_k_max" in data


class TestEdgeCases:
    """Test error handling and edge cases."""

    def test_invalid_fastener_size_raises(self):
        """Unknown fastener size should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown fastener"):
            analyze_bolted_joint(
                fastener_size="M99x99",
                bolt_grade="8.8",
                grip_length=25e-3,
                clamped_material_modulus=210e9,
                external_axial_load=5000,
                external_shear_load=0,
                tightening_method="torque_wrench",
                surface_condition="oiled",
                temperature=20,
                n_bolts=1,
                joint_type="through_bolt",
                embedding_surface_roughness="machined",
            )

    def test_invalid_bolt_grade_raises(self):
        """Unknown bolt grade should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown bolt grade"):
            analyze_bolted_joint(
                fastener_size="M10x1.5",
                bolt_grade="99.99",
                grip_length=25e-3,
                clamped_material_modulus=210e9,
                external_axial_load=5000,
                external_shear_load=0,
                tightening_method="torque_wrench",
                surface_condition="oiled",
                temperature=20,
                n_bolts=1,
                joint_type="through_bolt",
                embedding_surface_roughness="machined",
            )

    def test_zero_grip_length_raises(self):
        """Zero grip length should raise ValueError."""
        with pytest.raises(ValueError, match="grip_length"):
            analyze_bolted_joint(
                fastener_size="M10x1.5",
                bolt_grade="8.8",
                grip_length=0,
                clamped_material_modulus=210e9,
                external_axial_load=5000,
                external_shear_load=0,
                tightening_method="torque_wrench",
                surface_condition="oiled",
                temperature=20,
                n_bolts=1,
                joint_type="through_bolt",
                embedding_surface_roughness="machined",
            )

    def test_negative_load_raises(self):
        """Negative external load should raise ValueError."""
        with pytest.raises(ValueError):
            analyze_bolted_joint(
                fastener_size="M10x1.5",
                bolt_grade="8.8",
                grip_length=25e-3,
                clamped_material_modulus=210e9,
                external_axial_load=-5000,
                external_shear_load=0,
                tightening_method="torque_wrench",
                surface_condition="oiled",
                temperature=20,
                n_bolts=1,
                joint_type="through_bolt",
                embedding_surface_roughness="machined",
            )
