"""
Engineering Fits Calculator Module

This module handles calculations for ISO engineering fits and tolerances.
All dimensions are handled in millimeters internally.
"""

import json
import os
from typing import Dict, Tuple, Optional

class FitsCalculator:
    def __init__(self, fits_data_path: str):
        """Initialize the calculator with fits data from JSON file."""
        with open(fits_data_path, 'r') as f:
            self.fits_data = json.load(f)
        
    def _find_dimension_range(self, nominal_size: float) -> Dict:
        """Find the appropriate dimension range for a given nominal size."""
        for range_data in self.fits_data["dimension_ranges"]:
            if range_data["min"] <= nominal_size <= range_data["max"]:
                return range_data
        raise ValueError(f"Nominal size {nominal_size} mm is outside supported ranges")

    def _get_IT_grade_value(self, nominal_size: float, IT_grade: int) -> float:
        """Get the IT grade value in micrometers for a given size and grade."""
        range_data = self._find_dimension_range(nominal_size)
        if str(IT_grade) not in range_data["IT"]:
            raise ValueError(f"IT grade {IT_grade} not supported for size {nominal_size}")
        return range_data["IT"][str(IT_grade)]

    def calculate_fit(self, nominal_size: float, fit_name: str) -> Dict:
        """
        Calculate the tolerances and clearances/interferences for a given fit.
        
        Args:
            nominal_size: Nominal dimension in mm
            fit_name: Standard fit designation (e.g., "H7/h6")
            
        Returns:
            Dictionary containing:
            - hole_limits: (upper, lower) deviations in mm
            - shaft_limits: (upper, lower) deviations in mm
            - fit_type: "clearance", "transition", or "interference"
            - max_clearance: Maximum possible clearance (positive) in mm
            - min_clearance: Minimum possible clearance (negative for interference) in mm
            - description: Description of the fit from database
        """
        if fit_name not in self.fits_data["common_fits"]:
            raise ValueError(f"Fit {fit_name} not found in database")

        # Parse fit designation
        hole_spec, shaft_spec = fit_name.split('/')
        hole_letter = hole_spec[0]
        hole_grade = int(hole_spec[1:])
        shaft_letter = shaft_spec[0]
        shaft_grade = int(shaft_spec[1:])

        # Get IT grade values (in μm)
        hole_IT = self._get_IT_grade_value(nominal_size, hole_grade) / 1000  # convert to mm
        shaft_IT = self._get_IT_grade_value(nominal_size, shaft_grade) / 1000  # convert to mm

        # Calculate hole limits (H is always basic hole system)
        hole_upper = hole_IT
        hole_lower = 0

        # Calculate shaft limits based on fundamental deviation
        shaft_data = self.fits_data["fundamental_deviations"]["shaft"][shaft_letter]
        if shaft_letter == 'h':
            shaft_upper = 0
            shaft_lower = -shaft_IT
        elif shaft_letter in ['n', 'p', 's']:
            # Simplified calculation for interference fits
            deviation_multiplier = {'n': 1, 'p': 2, 's': 3}
            base_deviation = deviation_multiplier[shaft_letter] * (hole_IT / 10)
            shaft_upper = base_deviation + shaft_IT
            shaft_lower = base_deviation
        else:
            # For other fits, use transition calculations
            shaft_upper = shaft_IT/2
            shaft_lower = -shaft_IT/2

        # Calculate clearances
        max_clearance = hole_upper - shaft_lower
        min_clearance = hole_lower - shaft_upper

        fit_data = self.fits_data["common_fits"][fit_name]
        
        return {
            "hole_limits": (hole_upper, hole_lower),
            "shaft_limits": (shaft_upper, shaft_lower),
            "fit_type": fit_data["type"],
            "max_clearance": max_clearance,
            "min_clearance": min_clearance,
            "description": fit_data["description"],
            "typical_applications": fit_data["typical_applications"]
        }

    def get_available_fits(self) -> list:
        """Return list of available fit designations."""
        return list(self.fits_data["common_fits"].keys())

    def get_fit_description(self, fit_name: str) -> str:
        """Get the description for a given fit."""
        if fit_name not in self.fits_data["common_fits"]:
            raise ValueError(f"Fit {fit_name} not found in database")
        return self.fits_data["common_fits"][fit_name]["description"]