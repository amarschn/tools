"""Unit coherence checking and affine unit conversion.

Two jobs:

1. Confirm a canonical unit is a coherent SI expression, so canonical values are
   always comparable without consulting a per-property scale factor.
2. Convert between a canonical unit and a permitted display unit.

Conversions are affine (`display = value * factor + offset`) rather than a bare
scale factor, because temperature is not a pure scaling. The legacy prototype
corpus carried `display_scale: 1` for `max_service_temperature` while labelling
the unit "degC", which would render 393.15 K as "393.15 degC". Modelling the
offset explicitly is what makes that class of error impossible.

This module is the substrate for the user unit preference decided at checkpoint
1. It deliberately contains no display policy: choosing metric or imperial is a
serving concern, not a contract concern.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Mapping

# A coherent SI expression: a product of base symbols with optional integer
# exponents, and at most one denominator which may be parenthesized. `1` is the
# dimensionless unit. This mirrors the shape the original builder accepts, so
# `W/(m*K)` and `ohm*m` validate identically in both paths.
_SI_SYMBOL = r"[A-Za-z]+(?:\^-?\d+)?"
_SI_PRODUCT = rf"{_SI_SYMBOL}(?:\*{_SI_SYMBOL})*"
_SI_EXPRESSION_RE = re.compile(
    rf"^(?:1|{_SI_PRODUCT})(?:/(?:{_SI_PRODUCT}|\({_SI_PRODUCT}\)))?$"
)

# Coherent SI units carry no decimal prefix. `MPa` and `g` are legal display
# units but are never canonical, so a canonical unit naming one is an error.
# `kg` is absent deliberately: the kilogram is the SI base unit despite looking
# prefixed, so `kg/m^3` must pass.
_PREFIXED = {
    "MPa", "GPa", "kPa", "hPa", "mPa",
    "g", "mg", "km", "mm", "cm", "um", "nm",
    "kJ", "MJ", "mJ", "kW", "MW", "mW",
}


@dataclass(frozen=True)
class Conversion:
    """`display = canonical * factor + offset`."""

    unit: str
    factor: float
    offset: float = 0.0
    system: str = "metric"

    def to_display(self, value: float) -> float:
        return value * self.factor + self.offset

    def to_canonical(self, value: float) -> float:
        return (value - self.offset) / self.factor


# Display units permitted per quantity kind. The first entry of each system is
# that system's default. Canonical units appear explicitly so a user can always
# choose the stored form.
CONVERSIONS: Mapping[str, tuple[Conversion, ...]] = {
    "pressure": (
        Conversion("MPa", 1e-6, system="metric"),
        Conversion("GPa", 1e-9, system="metric"),
        Conversion("kPa", 1e-3, system="metric"),
        Conversion("Pa", 1.0, system="metric"),
        Conversion("ksi", 1.0 / 6_894_757.293168361, system="imperial"),
        Conversion("psi", 1.0 / 6_894.757293168361, system="imperial"),
    ),
    "mass_density": (
        Conversion("kg/m^3", 1.0, system="metric"),
        Conversion("g/cm^3", 1e-3, system="metric"),
        Conversion("lb/ft^3", 1.0 / 16.018463373960142, system="imperial"),
        Conversion("lb/in^3", 1.0 / 27_679.904710203122, system="imperial"),
    ),
    "dimensionless": (
        Conversion("%", 100.0, system="metric"),
        Conversion("1", 1.0, system="metric"),
    ),
    "thermal_conductivity": (
        Conversion("W/(m*K)", 1.0, system="metric"),
        Conversion("BTU/(hr*ft*degF)", 1.0 / 1.730734666295328, system="imperial"),
    ),
    "electrical_resistivity": (
        Conversion("ohm*m", 1.0, system="metric"),
        Conversion("ohm*cm", 100.0, system="metric"),
    ),
    "temperature": (
        Conversion("degC", 1.0, -273.15, system="metric"),
        Conversion("K", 1.0, system="metric"),
        Conversion("degF", 1.8, -459.67, system="imperial"),
    ),
    "energy_per_length": (
        Conversion("J/m", 1.0, system="metric"),
        Conversion("ft*lb/in", 1.0 / 53.378664089, system="imperial"),
    ),
    "hardness_scale": (
        Conversion("1", 1.0, system="metric"),
    ),
    "ratio": (
        Conversion("1", 1.0, system="metric"),
    ),
    "specific_heat": (
        Conversion("J/(kg*K)", 1.0, system="metric"),
        Conversion("BTU/(lb*degF)", 1.0 / 4186.8, system="imperial"),
    ),
}


def is_coherent_si_unit(unit: object) -> bool:
    """True when `unit` is a coherent SI expression with no decimal prefix."""
    if unit == "1":
        return True
    if not isinstance(unit, str) or not _SI_EXPRESSION_RE.fullmatch(unit):
        return False
    for token in re.split(r"[*/]", unit.replace("(", "").replace(")", "")):
        symbol = token.split("^", 1)[0]
        if symbol in _PREFIXED:
            return False
    return True


def conversions_for(quantity_kind: str) -> tuple[Conversion, ...]:
    return CONVERSIONS.get(quantity_kind, ())


def find_conversion(quantity_kind: str, unit: str) -> Conversion | None:
    for conversion in conversions_for(quantity_kind):
        if conversion.unit == unit:
            return conversion
    return None


def default_display_unit(quantity_kind: str, system: str = "metric") -> str | None:
    for conversion in conversions_for(quantity_kind):
        if conversion.system == system:
            return conversion.unit
    return None


def significant_figures(value: float) -> int:
    """Count the significant figures a decimal literal asserts.

    Used during migration to recover the precision the legacy corpus implied by
    the way it wrote its numbers, so a converted display value never invents
    digits the source never claimed.
    """
    if not math.isfinite(value) or value == 0:
        return 1
    text = repr(abs(float(value)))
    if "e" in text or "E" in text:
        mantissa = text.split("e")[0].split("E")[0]
        digits = mantissa.replace(".", "").rstrip("0")
        return max(1, len(digits))
    if "." in text:
        whole, frac = text.split(".", 1)
        if whole == "0":
            stripped = frac.lstrip("0")
            return max(1, len(stripped.rstrip("0")) or 1)
        return max(1, len((whole + frac).rstrip("0")) or 1)
    return max(1, len(text.rstrip("0")) or 1)


def round_to_significant_figures(value: float, figures: int) -> float:
    if value == 0 or not math.isfinite(value):
        return value
    exponent = math.floor(math.log10(abs(value)))
    return round(value, -(exponent - figures + 1))


def format_significant(value: float, figures: int) -> str:
    """Render `value` to `figures` significant digits.

    Plain decimal notation is used across the magnitudes engineering values
    actually occupy. `%g` alone would render 130 MPa at two significant figures
    as "1.3e+02", which is technically correct and useless on a datasheet.
    """
    if not math.isfinite(value):
        return str(value)
    if value == 0:
        return "0"
    rounded = round_to_significant_figures(value, figures)
    exponent = math.floor(math.log10(abs(rounded)))
    if -4 <= exponent < 12:
        decimals = max(0, figures - 1 - exponent)
        return f"{rounded:.{decimals}f}"
    return f"{rounded:.{figures}g}"
