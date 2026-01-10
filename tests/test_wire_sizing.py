"""Comprehensive tests for pycalcs/wire_sizing.py module.

Tests verify:
- NEC 310.16 ampacity table values
- Temperature correction factors per NEC 310.15(B)
- Bundling adjustment factors per NEC 310.15(C)
- Voltage drop calculations
- Wire size recommendations
- Edge cases and error handling
"""

import math
import pytest
from pycalcs import wire_sizing


# =============================================================================
# Test NEC 310.16 Ampacity Tables
# =============================================================================

class TestAmpacityTables:
    """Tests for NEC 310.16 ampacity values."""

    def test_copper_75c_12awg(self):
        """12 AWG copper at 75°C should be 25A per NEC 310.16."""
        table = wire_sizing.get_ampacity_table("copper", 75)
        assert table["12 AWG"] == 25

    def test_copper_75c_10awg(self):
        """10 AWG copper at 75°C should be 35A per NEC 310.16."""
        table = wire_sizing.get_ampacity_table("copper", 75)
        assert table["10 AWG"] == 35

    def test_copper_75c_8awg(self):
        """8 AWG copper at 75°C should be 50A per NEC 310.16."""
        table = wire_sizing.get_ampacity_table("copper", 75)
        assert table["8 AWG"] == 50

    def test_copper_75c_6awg(self):
        """6 AWG copper at 75°C should be 65A per NEC 310.16."""
        table = wire_sizing.get_ampacity_table("copper", 75)
        assert table["6 AWG"] == 65

    def test_copper_75c_4awg(self):
        """4 AWG copper at 75°C should be 85A per NEC 310.16."""
        table = wire_sizing.get_ampacity_table("copper", 75)
        assert table["4 AWG"] == 85

    def test_copper_75c_2awg(self):
        """2 AWG copper at 75°C should be 115A per NEC 310.16."""
        table = wire_sizing.get_ampacity_table("copper", 75)
        assert table["2 AWG"] == 115

    def test_copper_75c_1_0awg(self):
        """1/0 AWG copper at 75°C should be 150A per NEC 310.16."""
        table = wire_sizing.get_ampacity_table("copper", 75)
        assert table["1/0 AWG"] == 150

    def test_copper_75c_4_0awg(self):
        """4/0 AWG copper at 75°C should be 230A per NEC 310.16."""
        table = wire_sizing.get_ampacity_table("copper", 75)
        assert table["4/0 AWG"] == 230

    def test_copper_60c_values(self):
        """Copper at 60°C should have lower ampacity than 75°C."""
        table_60 = wire_sizing.get_ampacity_table("copper", 60)
        table_75 = wire_sizing.get_ampacity_table("copper", 75)
        for size in table_60:
            if size in table_75:
                assert table_60[size] <= table_75[size]

    def test_copper_90c_values(self):
        """Copper at 90°C should have higher ampacity than 75°C."""
        table_75 = wire_sizing.get_ampacity_table("copper", 75)
        table_90 = wire_sizing.get_ampacity_table("copper", 90)
        for size in table_75:
            if size in table_90:
                assert table_90[size] >= table_75[size]

    def test_aluminum_vs_copper(self):
        """Aluminum should have lower ampacity than copper for same size."""
        cu = wire_sizing.get_ampacity_table("copper", 75)
        al = wire_sizing.get_ampacity_table("aluminum", 75)
        for size in al:
            if size in cu:
                assert al[size] < cu[size]

    def test_aluminum_75c_values(self):
        """Verify specific aluminum 75°C ampacity values."""
        table = wire_sizing.get_ampacity_table("aluminum", 75)
        assert table["6 AWG"] == 50
        assert table["4 AWG"] == 65
        assert table["2 AWG"] == 90
        assert table["1/0 AWG"] == 120

    def test_invalid_material_raises(self):
        """Invalid material should raise ValueError."""
        with pytest.raises(ValueError):
            wire_sizing.get_ampacity_table("silver", 75)

    def test_invalid_temp_rating_raises(self):
        """Invalid temperature rating should raise ValueError."""
        with pytest.raises(ValueError):
            wire_sizing.get_ampacity_table("copper", 100)


# =============================================================================
# Test Temperature Correction Factors
# =============================================================================

class TestTempCorrectionFactors:
    """Tests for NEC 310.15(B) temperature correction factors."""

    def test_30c_ambient_no_correction(self):
        """30°C ambient should give factor of 1.0 for all ratings."""
        assert wire_sizing.get_temp_correction_factor(30, 60) == 1.0
        assert wire_sizing.get_temp_correction_factor(30, 75) == 1.0
        assert wire_sizing.get_temp_correction_factor(30, 90) == 1.0

    def test_40c_ambient_derating(self):
        """40°C ambient should derate ampacity."""
        factor_60 = wire_sizing.get_temp_correction_factor(40, 60)
        factor_75 = wire_sizing.get_temp_correction_factor(40, 75)
        factor_90 = wire_sizing.get_temp_correction_factor(40, 90)

        assert factor_60 == pytest.approx(0.82, rel=0.01)
        assert factor_75 == pytest.approx(0.88, rel=0.01)
        assert factor_90 == pytest.approx(0.91, rel=0.01)

    def test_50c_ambient_derating(self):
        """50°C ambient should significantly derate ampacity."""
        factor_60 = wire_sizing.get_temp_correction_factor(50, 60)
        factor_75 = wire_sizing.get_temp_correction_factor(50, 75)
        factor_90 = wire_sizing.get_temp_correction_factor(50, 90)

        assert factor_60 == pytest.approx(0.58, rel=0.01)
        assert factor_75 == pytest.approx(0.75, rel=0.01)
        assert factor_90 == pytest.approx(0.82, rel=0.01)

    def test_20c_ambient_uprating(self):
        """20°C ambient should allow higher ampacity."""
        factor_60 = wire_sizing.get_temp_correction_factor(20, 60)
        factor_75 = wire_sizing.get_temp_correction_factor(20, 75)
        factor_90 = wire_sizing.get_temp_correction_factor(20, 90)

        assert factor_60 > 1.0
        assert factor_75 > 1.0
        assert factor_90 > 1.0

    def test_60c_insulation_fails_at_60c_ambient(self):
        """60°C insulation cannot operate at 60°C ambient."""
        factor = wire_sizing.get_temp_correction_factor(60, 60)
        assert factor == 0.0

    def test_higher_rating_better_at_high_temps(self):
        """Higher temp rating should perform better at high ambient."""
        factor_60 = wire_sizing.get_temp_correction_factor(45, 60)
        factor_75 = wire_sizing.get_temp_correction_factor(45, 75)
        factor_90 = wire_sizing.get_temp_correction_factor(45, 90)

        assert factor_60 < factor_75 < factor_90


# =============================================================================
# Test Bundling Adjustment Factors
# =============================================================================

class TestBundlingFactors:
    """Tests for NEC 310.15(C) bundling adjustment factors."""

    def test_3_conductors_no_derating(self):
        """3 or fewer conductors should not require derating."""
        assert wire_sizing.get_bundling_factor(1) == 1.0
        assert wire_sizing.get_bundling_factor(2) == 1.0
        assert wire_sizing.get_bundling_factor(3) == 1.0

    def test_4_to_6_conductors(self):
        """4-6 conductors should use 80% factor."""
        assert wire_sizing.get_bundling_factor(4) == 0.80
        assert wire_sizing.get_bundling_factor(5) == 0.80
        assert wire_sizing.get_bundling_factor(6) == 0.80

    def test_7_to_9_conductors(self):
        """7-9 conductors should use 70% factor."""
        assert wire_sizing.get_bundling_factor(7) == 0.70
        assert wire_sizing.get_bundling_factor(8) == 0.70
        assert wire_sizing.get_bundling_factor(9) == 0.70

    def test_10_to_20_conductors(self):
        """10-20 conductors should use 50% factor."""
        assert wire_sizing.get_bundling_factor(10) == 0.50
        assert wire_sizing.get_bundling_factor(15) == 0.50
        assert wire_sizing.get_bundling_factor(20) == 0.50

    def test_21_to_30_conductors(self):
        """21-30 conductors should use 45% factor."""
        assert wire_sizing.get_bundling_factor(21) == 0.45
        assert wire_sizing.get_bundling_factor(30) == 0.45

    def test_large_bundle(self):
        """Large bundles should use minimum factor."""
        assert wire_sizing.get_bundling_factor(50) == 0.35
        assert wire_sizing.get_bundling_factor(100) == 0.35

    def test_invalid_conductor_count(self):
        """Zero or negative conductors should raise error."""
        with pytest.raises(ValueError):
            wire_sizing.get_bundling_factor(0)
        with pytest.raises(ValueError):
            wire_sizing.get_bundling_factor(-1)


# =============================================================================
# Test Resistance Calculations
# =============================================================================

class TestResistance:
    """Tests for wire resistance calculations."""

    def test_copper_lower_resistance_than_aluminum(self):
        """Copper should have lower resistance than aluminum."""
        r_cu = wire_sizing.get_resistance_per_meter("10 AWG", "copper", 20)
        r_al = wire_sizing.get_resistance_per_meter("10 AWG", "aluminum", 20)
        assert r_cu < r_al

    def test_larger_wire_lower_resistance(self):
        """Larger wire should have lower resistance."""
        r_12 = wire_sizing.get_resistance_per_meter("12 AWG", "copper", 20)
        r_10 = wire_sizing.get_resistance_per_meter("10 AWG", "copper", 20)
        r_8 = wire_sizing.get_resistance_per_meter("8 AWG", "copper", 20)
        assert r_12 > r_10 > r_8

    def test_resistance_increases_with_temperature(self):
        """Resistance should increase with temperature."""
        r_20 = wire_sizing.get_resistance_per_meter("10 AWG", "copper", 20)
        r_50 = wire_sizing.get_resistance_per_meter("10 AWG", "copper", 50)
        r_75 = wire_sizing.get_resistance_per_meter("10 AWG", "copper", 75)
        assert r_20 < r_50 < r_75

    def test_10awg_copper_resistance_at_20c(self):
        """10 AWG copper at 20°C should match NEC Chapter 9."""
        # NEC gives 1.21 ohms per 1000 ft = 0.00397 ohms/m
        r = wire_sizing.get_resistance_per_meter("10 AWG", "copper", 20)
        assert r == pytest.approx(0.00397, rel=0.01)

    def test_invalid_wire_size(self):
        """Invalid wire size should raise error."""
        with pytest.raises(ValueError):
            wire_sizing.get_resistance_per_meter("15 AWG", "copper", 20)

    def test_invalid_material(self):
        """Invalid material should raise error."""
        with pytest.raises(ValueError):
            wire_sizing.get_resistance_per_meter("10 AWG", "gold", 20)


# =============================================================================
# Test Wire Size Calculation
# =============================================================================

class TestCalculateWireSize:
    """Tests for calculate_wire_size function."""

    def test_basic_15a_circuit(self):
        """15A circuit should recommend 14 AWG copper."""
        result = wire_sizing.calculate_wire_size(
            current_a=15,
            voltage_v=120,
            length_m=10,
            material="copper",
            insulation_temp_rating=75,
        )
        assert result["recommended_size"] == "14 AWG"
        assert result["ampacity_ok"] is True

    def test_basic_20a_circuit(self):
        """20A circuit: 14 AWG at 75°C has exactly 20A ampacity per NEC 310.16."""
        result = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=10,
            material="copper",
            insulation_temp_rating=75,
        )
        # 14 AWG at 75°C = 20A per NEC 310.16 (just meets requirement)
        # Note: NEC 240.4(D) limits 14 AWG to 15A circuits in practice
        assert result["recommended_size"] == "14 AWG"
        assert result["ampacity_ok"] is True

    def test_30a_circuit(self):
        """30A circuit should recommend 10 AWG copper at 75°C."""
        result = wire_sizing.calculate_wire_size(
            current_a=30,
            voltage_v=120,
            length_m=10,
            material="copper",
            insulation_temp_rating=75,
        )
        assert result["recommended_size"] == "10 AWG"
        assert result["ampacity_ok"] is True

    def test_50a_circuit(self):
        """50A circuit should recommend 8 AWG copper at 75°C."""
        result = wire_sizing.calculate_wire_size(
            current_a=50,
            voltage_v=240,
            length_m=10,
            material="copper",
            insulation_temp_rating=75,
        )
        assert result["recommended_size"] == "8 AWG"
        assert result["ampacity_ok"] is True

    def test_high_ambient_upsize(self):
        """High ambient temp should require larger wire."""
        # At 30°C, 20A needs 12 AWG
        result_30 = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=10,
            ambient_temp_c=30,
        )

        # At 45°C, 20A may need larger wire
        result_45 = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=10,
            ambient_temp_c=45,
        )

        # Higher temp should require same or larger wire
        sizes = wire_sizing.AWG_SIZES
        idx_30 = sizes.index(result_30["recommended_size"])
        idx_45 = sizes.index(result_45["recommended_size"])
        assert idx_45 >= idx_30  # Larger index = larger wire

    def test_bundling_upsize(self):
        """More bundled conductors should require larger wire."""
        result_3 = wire_sizing.calculate_wire_size(
            current_a=25,
            voltage_v=120,
            length_m=10,
            num_conductors=3,
        )

        result_10 = wire_sizing.calculate_wire_size(
            current_a=25,
            voltage_v=120,
            length_m=10,
            num_conductors=10,
        )

        sizes = wire_sizing.AWG_SIZES
        idx_3 = sizes.index(result_3["recommended_size"])
        idx_10 = sizes.index(result_10["recommended_size"])
        assert idx_10 >= idx_3

    def test_aluminum_larger_than_copper(self):
        """Aluminum should require larger wire than copper."""
        result_cu = wire_sizing.calculate_wire_size(
            current_a=50,
            voltage_v=240,
            length_m=10,
            material="copper",
        )

        result_al = wire_sizing.calculate_wire_size(
            current_a=50,
            voltage_v=240,
            length_m=10,
            material="aluminum",
        )

        sizes = wire_sizing.AWG_SIZES
        idx_cu = sizes.index(result_cu["recommended_size"])
        idx_al = sizes.index(result_al["recommended_size"])
        assert idx_al >= idx_cu

    def test_voltage_drop_calculation(self):
        """Voltage drop should be calculated correctly."""
        result = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=30,
            material="copper",
        )

        assert "voltage_drop_v" in result
        assert "voltage_drop_percent" in result
        assert result["voltage_drop_v"] > 0
        assert result["voltage_drop_percent"] > 0

    def test_long_run_high_vdrop(self):
        """Long wire runs should have higher voltage drop."""
        result_short = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=5,
        )

        result_long = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=50,
        )

        assert result_long["voltage_drop_percent"] > result_short["voltage_drop_percent"]

    def test_vdrop_warning(self):
        """Excessive voltage drop should generate warning."""
        result = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=100,  # Very long run
            max_voltage_drop_percent=3.0,
        )

        if result["voltage_drop_percent"] > 3.0:
            assert not result["voltage_drop_ok"]
            assert len(result["warnings"]) > 0

    def test_returns_wire_properties(self):
        """Should return wire physical properties."""
        result = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=10,
        )

        assert "wire_area_mm2" in result
        assert "wire_diameter_mm" in result
        assert result["wire_area_mm2"] > 0
        assert result["wire_diameter_mm"] > 0

    def test_invalid_current_raises(self):
        """Zero or negative current should raise error."""
        with pytest.raises(ValueError):
            wire_sizing.calculate_wire_size(current_a=0, voltage_v=120, length_m=10)
        with pytest.raises(ValueError):
            wire_sizing.calculate_wire_size(current_a=-10, voltage_v=120, length_m=10)

    def test_invalid_voltage_raises(self):
        """Zero or negative voltage should raise error."""
        with pytest.raises(ValueError):
            wire_sizing.calculate_wire_size(current_a=20, voltage_v=0, length_m=10)

    def test_invalid_length_raises(self):
        """Zero or negative length should raise error."""
        with pytest.raises(ValueError):
            wire_sizing.calculate_wire_size(current_a=20, voltage_v=120, length_m=0)


# =============================================================================
# Test Check Wire Size
# =============================================================================

class TestCheckWireSize:
    """Tests for check_wire_size function."""

    def test_adequate_wire_passes(self):
        """Adequate wire size should pass."""
        result = wire_sizing.check_wire_size(
            wire_size="10 AWG",
            current_a=20,
            voltage_v=120,
            length_m=10,
        )
        assert result["check_result"] == "PASS"
        assert result["ampacity_ok"] is True

    def test_undersized_wire_fails(self):
        """Undersized wire should fail."""
        result = wire_sizing.check_wire_size(
            wire_size="14 AWG",
            current_a=30,  # Too much for 14 AWG
            voltage_v=120,
            length_m=10,
        )
        assert result["check_result"] == "FAIL"
        assert result["ampacity_ok"] is False

    def test_vdrop_check_included(self):
        """Voltage drop should be checked."""
        result = wire_sizing.check_wire_size(
            wire_size="12 AWG",
            current_a=20,
            voltage_v=120,
            length_m=50,
            max_voltage_drop_percent=3.0,
        )
        assert "voltage_drop_ok" in result

    def test_margin_calculation(self):
        """Ampacity margin should be calculated."""
        result = wire_sizing.check_wire_size(
            wire_size="10 AWG",
            current_a=20,
            voltage_v=120,
            length_m=10,
        )
        # 10 AWG at 75°C = 35A, load = 20A, margin = 75%
        assert result["ampacity_margin_percent"] > 0

    def test_invalid_wire_size_raises(self):
        """Invalid wire size should raise error."""
        with pytest.raises(ValueError):
            wire_sizing.check_wire_size(
                wire_size="15 AWG",
                current_a=20,
                voltage_v=120,
                length_m=10,
            )


# =============================================================================
# Test Wire Size Ordering
# =============================================================================

class TestWireSizeOrdering:
    """Tests for wire size list ordering."""

    def test_awg_sizes_ordered_small_to_large(self):
        """AWG sizes should be ordered smallest to largest."""
        sizes = wire_sizing.list_wire_sizes()

        # First sizes should be small AWG numbers
        assert sizes[0] == "18 AWG"
        assert sizes[1] == "16 AWG"
        assert sizes[2] == "14 AWG"

        # Last sizes should be large kcmil
        assert "2000 kcmil" in sizes[-1]

    def test_wire_area_increases_with_size(self):
        """Wire area should increase as we go through the list."""
        sizes = wire_sizing.list_wire_sizes()
        prev_area = 0

        for size in sizes:
            if size in wire_sizing.WIRE_AREA_MM2:
                area = wire_sizing.WIRE_AREA_MM2[size]
                assert area > prev_area
                prev_area = area


# =============================================================================
# Test Ampacity Table Data
# =============================================================================

class TestAmpacityTableData:
    """Tests for get_ampacity_table_data function."""

    def test_returns_list_of_dicts(self):
        """Should return list of dictionaries."""
        data = wire_sizing.get_ampacity_table_data("copper", 75)
        assert isinstance(data, list)
        assert len(data) > 0
        assert isinstance(data[0], dict)

    def test_dict_has_required_keys(self):
        """Each entry should have size, ampacity, area, diameter."""
        data = wire_sizing.get_ampacity_table_data("copper", 75)
        for entry in data:
            assert "size" in entry
            assert "ampacity" in entry
            assert "area_mm2" in entry
            assert "diameter_mm" in entry

    def test_values_are_positive(self):
        """All values should be positive."""
        data = wire_sizing.get_ampacity_table_data("copper", 75)
        for entry in data:
            assert entry["ampacity"] > 0
            assert entry["area_mm2"] > 0
            assert entry["diameter_mm"] > 0


# =============================================================================
# Test Insulation Types
# =============================================================================

class TestInsulationTypes:
    """Tests for insulation type data."""

    def test_list_insulation_types(self):
        """Should return dictionary of insulation types."""
        types = wire_sizing.list_insulation_types()
        assert isinstance(types, dict)
        assert len(types) > 0

    def test_common_types_present(self):
        """Common insulation types should be present."""
        types = wire_sizing.list_insulation_types()
        assert "THHN" in types
        assert "THWN" in types
        assert "THW" in types

    def test_types_have_temp_rating(self):
        """Each type should have temperature rating."""
        types = wire_sizing.list_insulation_types()
        for name, info in types.items():
            assert "temp_rating" in info
            assert info["temp_rating"] in (60, 75, 90)


# =============================================================================
# Test Real-World Scenarios
# =============================================================================

class TestRealWorldScenarios:
    """Tests for common real-world applications."""

    def test_residential_15a_branch_circuit(self):
        """Standard 15A residential branch circuit."""
        result = wire_sizing.calculate_wire_size(
            current_a=15,
            voltage_v=120,
            length_m=10,  # ~33 ft shorter home run
            material="copper",
            insulation_temp_rating=75,
        )
        assert result["recommended_size"] == "14 AWG"
        assert result["ampacity_ok"]
        # Voltage drop depends on run length

    def test_residential_20a_branch_circuit(self):
        """Standard 20A residential branch circuit."""
        result = wire_sizing.calculate_wire_size(
            current_a=20,
            voltage_v=120,
            length_m=10,
            material="copper",
            insulation_temp_rating=75,
        )
        # 14 AWG at 75°C = 20A per NEC 310.16
        assert result["recommended_size"] == "14 AWG"
        assert result["ampacity_ok"]

    def test_electric_range_40a_circuit(self):
        """40A electric range circuit."""
        result = wire_sizing.calculate_wire_size(
            current_a=40,
            voltage_v=240,
            length_m=15,
            material="copper",
            insulation_temp_rating=75,
        )
        assert result["recommended_size"] in ("8 AWG", "6 AWG")
        assert result["ampacity_ok"]

    def test_ev_charger_50a_circuit(self):
        """50A EV charger circuit."""
        result = wire_sizing.calculate_wire_size(
            current_a=50,
            voltage_v=240,
            length_m=25,
            material="copper",
            insulation_temp_rating=75,
        )
        assert result["recommended_size"] in ("8 AWG", "6 AWG")
        assert result["ampacity_ok"]

    def test_subpanel_100a_feeder(self):
        """100A subpanel feeder."""
        result = wire_sizing.calculate_wire_size(
            current_a=100,
            voltage_v=240,
            length_m=10,
            material="copper",
            insulation_temp_rating=75,
        )
        # 100A at 75°C needs 3 AWG (100A base) or 1 AWG (130A) for margin
        # The smallest wire with base ampacity >= 100A is 3 AWG (100A)
        assert result["ampacity_ok"]
        assert result["recommended_size"] in ("3 AWG", "2 AWG", "1 AWG")

    def test_dc_solar_string(self):
        """DC solar panel string wiring."""
        result = wire_sizing.calculate_wire_size(
            current_a=10,
            voltage_v=48,
            length_m=30,
            material="copper",
            insulation_temp_rating=90,  # USE-2 for solar
            circuit_type="DC",
            max_voltage_drop_percent=2.0,  # Tighter for efficiency
        )
        assert result["ampacity_ok"]
        # May warn about voltage drop depending on wire size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
