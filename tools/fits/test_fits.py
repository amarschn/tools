"""
Test suite for the Engineering Fits Calculator
"""

import pytest
import os
from fits import FitsCalculator

@pytest.fixture
def calculator():
    """Create a FitsCalculator instance for testing."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fits_data_path = os.path.join(current_dir, 'fits.json')
    return FitsCalculator(fits_data_path)

def test_basic_initialization(calculator):
    """Test that calculator initializes with data."""
    assert calculator.fits_data is not None
    assert "common_fits" in calculator.fits_data
    assert "dimension_ranges" in calculator.fits_data

def test_dimension_range_finding(calculator):
    """Test finding correct dimension range."""
    # Test valid dimensions
    assert calculator._find_dimension_range(2.5)["min"] == 1
    assert calculator._find_dimension_range(8.0)["min"] == 6
    
    # Test boundary conditions
    assert calculator._find_dimension_range(3.0)["min"] == 3
    
    # Test invalid dimension
    with pytest.raises(ValueError):
        calculator._find_dimension_range(0.5)

def test_common_fit_calculations(calculator):
    """Test calculations for common fits."""
    # Test H7/h6 sliding fit
    result = calculator.calculate_fit(10.0, "H7/h6")
    assert result["fit_type"] == "clearance"
    assert result["max_clearance"] > 0
    assert result["min_clearance"] >= 0
    
    # Test H7/s6 interference fit
    result = calculator.calculate_fit(10.0, "H7/s6")
    assert result["fit_type"] == "interference"
    assert result["min_clearance"] < 0
    
    # Test invalid fit designation
    with pytest.raises(ValueError):
        calculator.calculate_fit(10.0, "H7/z6")

def test_fit_descriptions(calculator):
    """Test retrieving fit descriptions."""
    description = calculator.get_fit_description("H7/h6")
    assert "sliding" in description.lower()
    assert len(description) > 0

def test_available_fits(calculator):
    """Test getting list of available fits."""
    fits = calculator.get_available_fits()
    assert "H7/h6" in fits
    assert "H7/p6" in fits
    assert len(fits) > 0

def test_tolerance_values(calculator):
    """Test specific tolerance values."""
    result = calculator.calculate_fit(10.0, "H7/h6")
    hole_upper, hole_lower = result["hole_limits"]
    shaft_upper, shaft_lower = result["shaft_limits"]
    
    # Basic checks
    assert hole_upper > hole_lower
    assert shaft_upper > shaft_lower
    assert hole_lower == 0  # H-basis hole system
    
    # Check the actual values are in a reasonable range
    assert 0 < hole_upper < 0.1  # Usually around 0.015-0.018mm for this size
    assert -0.1 < shaft_lower < 0  # Usually around -0.009mm for this size