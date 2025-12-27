"""
Legacy module retained for backwards compatibility with the original Sound Level Calculator.

All acoustic calculations now live in pycalcs.acoustics.calculate_sound_levels to keep a single
source of truth for equations, documentation, and testing.
"""

from pycalcs.acoustics import calculate_sound_levels  # noqa: F401
