"""Comprehensive tests for pycalcs/units.py unit conversion module.

Tests verify:
- All supported quantities and unit definitions
- Linear conversions (simple multiplier)
- Affine conversions (temperature with offsets)
- Edge cases (zero, negative, extreme values)
- Error handling for invalid inputs
- Reference values against known standards (NIST, BIPM)
"""

import math
import pytest
from pycalcs import units


# =============================================================================
# Test Fixtures and Constants
# =============================================================================

EXPECTED_QUANTITIES = [
    "angle",
    "area",
    "capacitance",
    "current",
    "density",
    "energy",
    "force",
    "length",
    "linear_stiffness",
    "magnetic_flux_density",
    "mass",
    "power",
    "pressure",
    "radiation_dose",
    "rotational_stiffness",
    "temperature",
    "time",
    "torque",
    "velocity",
    "voltage",
    "volume",
]


# =============================================================================
# Test Quantity Listing
# =============================================================================

class TestQuantityListing:
    """Tests for list_supported_quantities function."""

    def test_returns_sorted_list(self):
        """Quantities should be returned in alphabetical order."""
        quantities = units.list_supported_quantities()
        assert quantities == sorted(quantities)

    def test_all_expected_quantities_present(self):
        """All expected quantity types should be available."""
        quantities = units.list_supported_quantities()
        for expected in EXPECTED_QUANTITIES:
            assert expected in quantities, f"Missing quantity: {expected}"

    def test_returns_list_type(self):
        """Function should return a list."""
        result = units.list_supported_quantities()
        assert isinstance(result, list)


# =============================================================================
# Test Unit Listing
# =============================================================================

class TestUnitListing:
    """Tests for list_units function."""

    def test_length_units(self):
        """Length should include standard units."""
        length_units = units.list_units("length")
        expected_symbols = ["m", "mm", "cm", "km", "in", "ft", "yd", "mi"]
        for symbol in expected_symbols:
            assert symbol in length_units

    def test_pressure_units(self):
        """Pressure should include engineering units."""
        pressure_units = units.list_units("pressure")
        expected_symbols = ["Pa", "kPa", "MPa", "bar", "atm", "psi", "ksi"]
        for symbol in expected_symbols:
            assert symbol in pressure_units

    def test_temperature_units(self):
        """Temperature should include all common scales."""
        temp_units = units.list_units("temperature")
        assert "K" in temp_units
        assert "°C" in temp_units
        assert "°F" in temp_units
        assert "°R" in temp_units

    def test_case_insensitive_quantity(self):
        """Quantity lookup should be case-insensitive."""
        upper = units.list_units("LENGTH")
        lower = units.list_units("length")
        mixed = units.list_units("Length")
        assert upper == lower == mixed

    def test_invalid_quantity_raises_error(self):
        """Invalid quantity should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported quantity"):
            units.list_units("invalid_quantity")

    def test_returns_dict_with_names(self):
        """Should return dict mapping symbols to names."""
        length_units = units.list_units("length")
        assert length_units["m"] == "metre"
        assert length_units["ft"] == "foot"


# =============================================================================
# Test Linear Conversions
# =============================================================================

class TestLinearConversions:
    """Tests for simple linear (multiplicative) unit conversions."""

    # Length conversions
    def test_meters_to_feet(self):
        """1 meter = 3.28084 feet (approx)."""
        result = units.convert_value("length", "m", "ft", 1.0)
        assert result == pytest.approx(3.28084, rel=1e-4)

    def test_feet_to_meters(self):
        """1 foot = 0.3048 meters (exact)."""
        result = units.convert_value("length", "ft", "m", 1.0)
        assert result == pytest.approx(0.3048, rel=1e-10)

    def test_inches_to_mm(self):
        """1 inch = 25.4 mm (exact)."""
        result = units.convert_value("length", "in", "mm", 1.0)
        assert result == pytest.approx(25.4, rel=1e-10)

    def test_miles_to_kilometers(self):
        """1 mile = 1.609344 km (exact)."""
        result = units.convert_value("length", "mi", "km", 1.0)
        assert result == pytest.approx(1.609344, rel=1e-10)

    # Force conversions
    def test_newtons_to_lbf(self):
        """1 newton = 0.224809 lbf (approx)."""
        result = units.convert_value("force", "N", "lbf", 1.0)
        assert result == pytest.approx(0.224809, rel=1e-4)

    def test_kip_to_kn(self):
        """1 kip = 4.448222 kN (approx)."""
        result = units.convert_value("force", "kip", "kN", 1.0)
        assert result == pytest.approx(4.448222, rel=1e-4)

    # Pressure conversions
    def test_psi_to_kpa(self):
        """1 psi = 6.894757 kPa (approx)."""
        result = units.convert_value("pressure", "psi", "kPa", 1.0)
        assert result == pytest.approx(6.894757, rel=1e-4)

    def test_bar_to_psi(self):
        """1 bar = 14.5038 psi (approx)."""
        result = units.convert_value("pressure", "bar", "psi", 1.0)
        assert result == pytest.approx(14.5038, rel=1e-4)

    def test_atm_to_pa(self):
        """1 atm = 101325 Pa (exact by definition)."""
        result = units.convert_value("pressure", "atm", "Pa", 1.0)
        assert result == pytest.approx(101325.0, rel=1e-10)

    def test_mpa_to_ksi(self):
        """1 MPa = 0.145038 ksi (approx)."""
        result = units.convert_value("pressure", "MPa", "ksi", 1.0)
        assert result == pytest.approx(0.145038, rel=1e-4)

    # Energy conversions
    def test_joules_to_btu(self):
        """1 BTU = 1055.06 J (IT BTU)."""
        result = units.convert_value("energy", "BTU", "J", 1.0)
        assert result == pytest.approx(1055.06, rel=1e-4)

    def test_kwh_to_mj(self):
        """1 kWh = 3.6 MJ (exact)."""
        result = units.convert_value("energy", "kWh", "MJ", 1.0)
        assert result == pytest.approx(3.6, rel=1e-10)

    # Mass conversions
    def test_kg_to_lb(self):
        """1 kg = 2.20462 lb (approx)."""
        result = units.convert_value("mass", "kg", "lb", 1.0)
        assert result == pytest.approx(2.20462, rel=1e-4)

    def test_slug_to_kg(self):
        """1 slug = 14.5939 kg (approx)."""
        result = units.convert_value("mass", "slug", "kg", 1.0)
        assert result == pytest.approx(14.5939, rel=1e-4)

    # Torque conversions
    def test_nm_to_lbf_ft(self):
        """1 N·m = 0.737562 lbf·ft (approx)."""
        result = units.convert_value("torque", "N·m", "lbf·ft", 1.0)
        assert result == pytest.approx(0.737562, rel=1e-4)

    # Angle conversions
    def test_degrees_to_radians(self):
        """180 degrees = π radians."""
        result = units.convert_value("angle", "deg", "rad", 180.0)
        assert result == pytest.approx(math.pi, rel=1e-10)

    def test_radians_to_degrees(self):
        """π radians = 180 degrees."""
        result = units.convert_value("angle", "rad", "deg", math.pi)
        assert result == pytest.approx(180.0, rel=1e-10)

    # Time conversions
    def test_hours_to_seconds(self):
        """1 hour = 3600 seconds."""
        result = units.convert_value("time", "h", "s", 1.0)
        assert result == pytest.approx(3600.0, rel=1e-10)

    def test_days_to_hours(self):
        """1 day = 24 hours."""
        result = units.convert_value("time", "d", "h", 1.0)
        assert result == pytest.approx(24.0, rel=1e-10)


# =============================================================================
# Test Temperature Conversions (Affine)
# =============================================================================

class TestTemperatureConversions:
    """Tests for temperature conversions with offsets."""

    def test_freezing_point_c_to_k(self):
        """0°C = 273.15 K."""
        result = units.convert_value("temperature", "°C", "K", 0.0)
        assert result == pytest.approx(273.15, rel=1e-10)

    def test_boiling_point_c_to_k(self):
        """100°C = 373.15 K."""
        result = units.convert_value("temperature", "°C", "K", 100.0)
        assert result == pytest.approx(373.15, rel=1e-10)

    def test_freezing_point_f_to_c(self):
        """32°F = 0°C."""
        result = units.convert_value("temperature", "°F", "°C", 32.0)
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_boiling_point_f_to_c(self):
        """212°F = 100°C."""
        result = units.convert_value("temperature", "°F", "°C", 212.0)
        assert result == pytest.approx(100.0, rel=1e-10)

    def test_body_temp_c_to_f(self):
        """37°C = 98.6°F."""
        result = units.convert_value("temperature", "°C", "°F", 37.0)
        assert result == pytest.approx(98.6, rel=1e-4)

    def test_absolute_zero_k_to_c(self):
        """0 K = -273.15°C."""
        result = units.convert_value("temperature", "K", "°C", 0.0)
        assert result == pytest.approx(-273.15, rel=1e-10)

    def test_absolute_zero_k_to_f(self):
        """0 K = -459.67°F."""
        result = units.convert_value("temperature", "K", "°F", 0.0)
        assert result == pytest.approx(-459.67, rel=1e-4)

    def test_rankine_to_kelvin(self):
        """491.67°R = 273.15 K (freezing point of water)."""
        result = units.convert_value("temperature", "°R", "K", 491.67)
        assert result == pytest.approx(273.15, rel=1e-4)

    def test_negative_celsius(self):
        """-40°C = -40°F (unique crossover point)."""
        result = units.convert_value("temperature", "°C", "°F", -40.0)
        assert result == pytest.approx(-40.0, rel=1e-10)


# =============================================================================
# Test Conversion Factor
# =============================================================================

class TestConversionFactor:
    """Tests for conversion_factor function."""

    def test_simple_linear_factor(self):
        """Linear conversions should return a valid factor."""
        factor = units.conversion_factor("length", "ft", "m")
        assert factor == pytest.approx(0.3048, rel=1e-10)

    def test_factor_is_reciprocal(self):
        """Reverse factor should be reciprocal."""
        ft_to_m = units.conversion_factor("length", "ft", "m")
        m_to_ft = units.conversion_factor("length", "m", "ft")
        assert ft_to_m * m_to_ft == pytest.approx(1.0, rel=1e-10)

    def test_temperature_factor_raises_error(self):
        """Temperature conversions with offsets should raise ValueError."""
        with pytest.raises(ValueError, match="offset"):
            units.conversion_factor("temperature", "°C", "K")

    def test_temperature_factor_rankine_to_kelvin(self):
        """Rankine to Kelvin is NOT purely multiplicative (0R != 0K)."""
        # Actually, checking the math: 0°R * (5/9) = 0 K, so it IS multiplicative
        # But the code checks if the zero-point transforms to zero
        factor = units.conversion_factor("temperature", "°R", "K")
        assert factor == pytest.approx(5.0 / 9.0, rel=1e-10)


# =============================================================================
# Test convert_units (High-Level Helper)
# =============================================================================

class TestConvertUnitsHelper:
    """Tests for convert_units high-level function."""

    def test_returns_dict_with_required_keys(self):
        """Should return dict with all expected keys."""
        result = units.convert_units("length", "m", "ft", 1.0)
        assert "converted_value" in result
        assert "base_value" in result
        assert "has_multiplier_only" in result
        assert "multiplier" in result

    def test_linear_conversion_has_multiplier(self):
        """Linear conversions should have has_multiplier_only=True."""
        result = units.convert_units("length", "m", "ft", 1.0)
        assert result["has_multiplier_only"] is True
        assert result["multiplier"] == pytest.approx(3.28084, rel=1e-4)

    def test_temperature_no_multiplier(self):
        """Temperature conversions should have has_multiplier_only=False."""
        result = units.convert_units("temperature", "°C", "K", 0.0)
        assert result["has_multiplier_only"] is False

    def test_base_value_in_si(self):
        """base_value should be in SI base units."""
        result = units.convert_units("length", "ft", "in", 1.0)
        # 1 ft = 0.3048 m (SI base)
        assert result["base_value"] == pytest.approx(0.3048, rel=1e-10)


# =============================================================================
# Test Unit Catalog
# =============================================================================

class TestUnitCatalog:
    """Tests for get_unit_catalog function."""

    def test_catalog_structure(self):
        """Catalog should have nested dict structure."""
        catalog = units.get_unit_catalog()
        assert isinstance(catalog, dict)
        assert "length" in catalog
        assert isinstance(catalog["length"], dict)
        assert "m" in catalog["length"]
        assert "name" in catalog["length"]["m"]
        assert "symbol" in catalog["length"]["m"]

    def test_catalog_has_all_quantities(self):
        """Catalog should contain all supported quantities."""
        catalog = units.get_unit_catalog()
        quantities = units.list_supported_quantities()
        for q in quantities:
            assert q in catalog


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_value(self):
        """Zero should convert to zero for linear units."""
        result = units.convert_value("length", "m", "ft", 0.0)
        assert result == 0.0

    def test_negative_value(self):
        """Negative values should convert correctly."""
        result = units.convert_value("length", "m", "ft", -1.0)
        assert result == pytest.approx(-3.28084, rel=1e-4)

    def test_very_large_value(self):
        """Very large values should convert without overflow."""
        result = units.convert_value("length", "m", "mm", 1e15)
        assert result == pytest.approx(1e18, rel=1e-10)

    def test_very_small_value(self):
        """Very small values should convert without underflow."""
        result = units.convert_value("length", "m", "km", 1e-15)
        assert result == pytest.approx(1e-18, rel=1e-10)

    def test_same_unit_conversion(self):
        """Converting unit to itself should return same value."""
        result = units.convert_value("length", "m", "m", 42.0)
        assert result == 42.0

    def test_identity_conversion_temperature(self):
        """Temperature identity conversion should be exact."""
        result = units.convert_value("temperature", "°C", "°C", 25.0)
        assert result == 25.0


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_quantity(self):
        """Invalid quantity should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported quantity"):
            units.convert_value("invalid", "m", "ft", 1.0)

    def test_invalid_from_unit(self):
        """Invalid from_unit should raise ValueError."""
        with pytest.raises(ValueError, match="not valid"):
            units.convert_value("length", "invalid_unit", "m", 1.0)

    def test_invalid_to_unit(self):
        """Invalid to_unit should raise ValueError."""
        with pytest.raises(ValueError, match="not valid"):
            units.convert_value("length", "m", "invalid_unit", 1.0)

    def test_mismatched_quantity_units(self):
        """Using unit from different quantity should raise error."""
        with pytest.raises(ValueError):
            units.convert_value("length", "Pa", "m", 1.0)  # Pa is pressure


# =============================================================================
# Test Reference Values (NIST/BIPM Standards)
# =============================================================================

class TestReferenceValues:
    """Tests against official NIST/BIPM reference values."""

    # NIST Reference: https://www.nist.gov/pml/special-publication-811

    def test_inch_exact_definition(self):
        """1 inch = 25.4 mm (exact by international agreement)."""
        result = units.convert_value("length", "in", "mm", 1.0)
        assert result == 25.4  # Exact, no tolerance

    def test_pound_mass_exact_definition(self):
        """1 lb = 0.45359237 kg (exact by international agreement)."""
        result = units.convert_value("mass", "lb", "kg", 1.0)
        assert result == 0.45359237  # Exact

    def test_gallon_us_definition(self):
        """1 US gallon = 3.785411784 L (exact)."""
        result = units.convert_value("volume", "gal_us", "L", 1.0)
        assert result == pytest.approx(3.785411784, rel=1e-10)

    def test_nautical_mile_definition(self):
        """1 nautical mile = 1852 m (exact by definition)."""
        result = units.convert_value("length", "nmi", "m", 1.0)
        assert result == 1852.0  # Exact

    def test_atmosphere_definition(self):
        """1 atm = 101325 Pa (exact by definition)."""
        result = units.convert_value("pressure", "atm", "Pa", 1.0)
        assert result == 101325.0  # Exact

    def test_electronvolt_definition(self):
        """1 eV = 1.602176634e-19 J (exact, 2019 SI redefinition)."""
        result = units.convert_value("energy", "eV", "J", 1.0)
        assert result == 1.602176634e-19  # Exact by definition


# =============================================================================
# Test Area and Volume (Derived Units)
# =============================================================================

class TestDerivedUnits:
    """Tests for area and volume derived units."""

    def test_square_feet_to_square_meters(self):
        """1 ft² = 0.09290304 m² (exact)."""
        result = units.convert_value("area", "ft^2", "m^2", 1.0)
        assert result == pytest.approx(0.09290304, rel=1e-10)

    def test_acre_to_square_meters(self):
        """1 acre = 4046.8564224 m² (exact)."""
        result = units.convert_value("area", "acre", "m^2", 1.0)
        assert result == pytest.approx(4046.8564224, rel=1e-10)

    def test_cubic_feet_to_liters(self):
        """1 ft³ = 28.316846592 L."""
        result = units.convert_value("volume", "ft^3", "L", 1.0)
        assert result == pytest.approx(28.316846592, rel=1e-8)

    def test_milliliters_to_cubic_cm(self):
        """1 mL = 1 cm³."""
        result = units.convert_value("volume", "mL", "cm^3", 1.0)
        assert result == pytest.approx(1.0, rel=1e-10)


# =============================================================================
# Test Electrical Units
# =============================================================================

class TestElectricalUnits:
    """Tests for electrical unit conversions."""

    def test_milliamps_to_amps(self):
        """1000 mA = 1 A."""
        result = units.convert_value("current", "mA", "A", 1000.0)
        assert result == pytest.approx(1.0, rel=1e-10)

    def test_microfarads_to_farads(self):
        """1000000 µF = 1 F."""
        result = units.convert_value("capacitance", "µF", "F", 1e6)
        assert result == pytest.approx(1.0, rel=1e-10)

    def test_millivolts_to_volts(self):
        """1000 mV = 1 V."""
        result = units.convert_value("voltage", "mV", "V", 1000.0)
        assert result == pytest.approx(1.0, rel=1e-10)

    def test_gauss_to_tesla(self):
        """10000 G = 1 T."""
        result = units.convert_value("magnetic_flux_density", "G", "T", 10000.0)
        assert result == pytest.approx(1.0, rel=1e-10)


# =============================================================================
# Test Power Units
# =============================================================================

class TestPowerUnits:
    """Tests for power unit conversions."""

    def test_mechanical_horsepower(self):
        """1 hp (mechanical) = 745.7 W (approx)."""
        result = units.convert_value("power", "hp_mech", "W", 1.0)
        assert result == pytest.approx(745.7, rel=1e-3)

    def test_metric_horsepower(self):
        """1 hp (metric) = 735.5 W (approx)."""
        result = units.convert_value("power", "hp_metric", "W", 1.0)
        assert result == pytest.approx(735.5, rel=1e-3)

    def test_megawatts_to_kilowatts(self):
        """1 MW = 1000 kW."""
        result = units.convert_value("power", "MW", "kW", 1.0)
        assert result == pytest.approx(1000.0, rel=1e-10)


# =============================================================================
# Test Velocity Units
# =============================================================================

class TestVelocityUnits:
    """Tests for velocity unit conversions."""

    def test_kmh_to_ms(self):
        """100 km/h = 27.778 m/s (approx)."""
        result = units.convert_value("velocity", "km/h", "m/s", 100.0)
        assert result == pytest.approx(27.778, rel=1e-3)

    def test_mph_to_kmh(self):
        """60 mph = 96.5606 km/h."""
        result = units.convert_value("velocity", "mph", "km/h", 60.0)
        assert result == pytest.approx(96.5606, rel=1e-4)

    def test_knots_to_mph(self):
        """1 knot = 1.15078 mph."""
        result = units.convert_value("velocity", "knot", "mph", 1.0)
        assert result == pytest.approx(1.15078, rel=1e-4)


# =============================================================================
# Test Stiffness Units
# =============================================================================

class TestStiffnessUnits:
    """Tests for stiffness unit conversions."""

    def test_linear_stiffness_lbf_per_in(self):
        """1 lbf/in = 175.127 N/m (approx)."""
        result = units.convert_value("linear_stiffness", "lbf/in", "N/m", 1.0)
        assert result == pytest.approx(175.127, rel=1e-3)

    def test_rotational_stiffness(self):
        """Convert N·m/rad to kN·m/rad."""
        result = units.convert_value("rotational_stiffness", "N·m/rad", "kN·m/rad", 1000.0)
        assert result == pytest.approx(1.0, rel=1e-10)


# =============================================================================
# Test Radiation Dose Units
# =============================================================================

class TestRadiationDoseUnits:
    """Tests for radiation dose unit conversions."""

    def test_rem_to_sievert(self):
        """100 rem = 1 Sv."""
        result = units.convert_value("radiation_dose", "rem", "Sv", 100.0)
        assert result == pytest.approx(1.0, rel=1e-10)

    def test_millisievert_to_microsievert(self):
        """1 mSv = 1000 µSv."""
        result = units.convert_value("radiation_dose", "mSv", "µSv", 1.0)
        assert result == pytest.approx(1000.0, rel=1e-10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
