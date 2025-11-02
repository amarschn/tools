"""Reusable unit conversion helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict


@dataclass(frozen=True)
class UnitDefinition:
    """Callable-based unit definition."""

    symbol: str
    name: str
    to_base: Callable[[float], float]
    from_base: Callable[[float], float]


def _linear_unit(symbol: str, name: str, factor: float) -> UnitDefinition:
    """Create a unit with simple linear scaling."""

    return UnitDefinition(
        symbol=symbol,
        name=name,
        to_base=lambda value: value * factor,
        from_base=lambda value: value / factor,
    )


def _affine_unit(
    symbol: str,
    name: str,
    to_base: Callable[[float], float],
    from_base: Callable[[float], float],
) -> UnitDefinition:
    """Create a unit with an affine transformation (offset + scale)."""

    return UnitDefinition(
        symbol=symbol,
        name=name,
        to_base=to_base,
        from_base=from_base,
    )


def _square_unit(symbol: str, name: str, linear_factor: float) -> UnitDefinition:
    """Create an area-like unit derived from a linear factor."""

    factor = linear_factor**2
    return _linear_unit(symbol, name, factor)


def _cubic_unit(symbol: str, name: str, linear_factor: float) -> UnitDefinition:
    """Create a volume-like unit derived from a linear factor."""

    factor = linear_factor**3
    return _linear_unit(symbol, name, factor)


QuantityUnits = Dict[str, Dict[str, UnitDefinition]]


QUANTITY_DEFINITIONS: Dict[str, Dict[str, UnitDefinition]] = {
    "length": {
        "m": _linear_unit("m", "metre", 1.0),
        "mm": _linear_unit("mm", "millimetre", 1e-3),
        "cm": _linear_unit("cm", "centimetre", 1e-2),
        "km": _linear_unit("km", "kilometre", 1e3),
        "in": _linear_unit("in", "inch", 0.0254),
        "ft": _linear_unit("ft", "foot", 0.3048),
        "yd": _linear_unit("yd", "yard", 0.9144),
        "mi": _linear_unit("mi", "statute mile", 1609.344),
        "nmi": _linear_unit("nmi", "nautical mile", 1852.0),
        "au": _linear_unit("au", "astronomical unit", 149_597_870_700.0),
        "ly": _linear_unit("ly", "light-year", 9.460_730_472_580_8e15),
        "pc": _linear_unit("pc", "parsec", 3.085_677_581_491_3673e16),
    },
    "area": {
        "m^2": _linear_unit("m^2", "square metre", 1.0),
        "cm^2": _square_unit("cm^2", "square centimetre", 1e-2),
        "mm^2": _square_unit("mm^2", "square millimetre", 1e-3),
        "km^2": _square_unit("km^2", "square kilometre", 1e3),
        "ha": _linear_unit("ha", "hectare", 1e4),
        "in^2": _square_unit("in^2", "square inch", 0.0254),
        "ft^2": _square_unit("ft^2", "square foot", 0.3048),
        "yd^2": _square_unit("yd^2", "square yard", 0.9144),
        "acre": _linear_unit("acre", "acre", 4046.8564224),
    },
    "volume": {
        "m^3": _linear_unit("m^3", "cubic metre", 1.0),
        "cm^3": _cubic_unit("cm^3", "cubic centimetre", 1e-2),
        "mm^3": _cubic_unit("mm^3", "cubic millimetre", 1e-3),
        "L": _linear_unit("L", "litre", 1e-3),
        "mL": _linear_unit("mL", "millilitre", 1e-6),
        "in^3": _cubic_unit("in^3", "cubic inch", 0.0254),
        "ft^3": _cubic_unit("ft^3", "cubic foot", 0.3048),
        "yd^3": _cubic_unit("yd^3", "cubic yard", 0.9144),
        "gal_us": _linear_unit("gal_us", "US gallon", 3.785411784e-3),
        "gal_imp": _linear_unit("gal_imp", "Imperial gallon", 4.54609e-3),
    },
    "mass": {
        "kg": _linear_unit("kg", "kilogram", 1.0),
        "g": _linear_unit("g", "gram", 1e-3),
        "mg": _linear_unit("mg", "milligram", 1e-6),
        "tonne": _linear_unit("tonne", "metric tonne", 1e3),
        "lb": _linear_unit("lb", "pound mass", 0.45359237),
        "slug": _linear_unit("slug", "slug", 14.59390294),
    },
    "force": {
        "N": _linear_unit("N", "newton", 1.0),
        "kN": _linear_unit("kN", "kilonewton", 1e3),
        "MN": _linear_unit("MN", "meganewton", 1e6),
        "lbf": _linear_unit("lbf", "pound-force", 4.4482216152605),
        "kip": _linear_unit("kip", "kilo-pound-force", 4.4482216152605e3),
    },
    "torque": {
        "N·m": _linear_unit("N·m", "newton metre", 1.0),
        "kN·m": _linear_unit("kN·m", "kilonewton metre", 1e3),
        "lbf·ft": _linear_unit("lbf·ft", "pound-foot", 1.3558179483314004),
        "lbf·in": _linear_unit("lbf·in", "pound-inch", 0.1129848290276167),
    },
    "pressure": {
        "Pa": _linear_unit("Pa", "pascal", 1.0),
        "kPa": _linear_unit("kPa", "kilopascal", 1e3),
        "MPa": _linear_unit("MPa", "megapascal", 1e6),
        "bar": _linear_unit("bar", "bar", 1e5),
        "atm": _linear_unit("atm", "standard atmosphere", 101325.0),
        "psi": _linear_unit("psi", "pound per square inch", 6894.757293168),
        "psf": _linear_unit("psf", "pound per square foot", 47.88025898033584),
        "torr": _linear_unit("torr", "torr", 133.32236842105263),
        "ksi": _linear_unit("ksi", "kilopound per square inch", 6.894757293168e6),
        "Msi": _linear_unit("Msi", "megapound per square inch", 6.894757293168e9),
    },
    "energy": {
        "J": _linear_unit("J", "joule", 1.0),
        "kJ": _linear_unit("kJ", "kilojoule", 1e3),
        "MJ": _linear_unit("MJ", "megajoule", 1e6),
        "Wh": _linear_unit("Wh", "watt-hour", 3600.0),
        "kWh": _linear_unit("kWh", "kilowatt-hour", 3.6e6),
        "BTU": _linear_unit("BTU", "British thermal unit (IT)", 1055.05585262),
        "ft·lbf": _linear_unit("ft·lbf", "foot-pound-force", 1.3558179483314004),
        "eV": _linear_unit("eV", "electronvolt", 1.602176634e-19),
        "keV": _linear_unit("keV", "kiloelectronvolt", 1.602176634e-16),
        "MeV": _linear_unit("MeV", "megaelectronvolt", 1.602176634e-13),
        "GeV": _linear_unit("GeV", "gigaelectronvolt", 1.602176634e-10),
        "Cal": _linear_unit("Cal", "nutritional calorie", 4184.0),
    },
    "power": {
        "W": _linear_unit("W", "watt", 1.0),
        "kW": _linear_unit("kW", "kilowatt", 1e3),
        "MW": _linear_unit("MW", "megawatt", 1e6),
        "hp_mech": _linear_unit("hp_mech", "horsepower (mechanical)", 745.6998715822702),
        "hp_metric": _linear_unit("hp_metric", "horsepower (metric)", 735.49875),
    },
    "current": {
        "A": _linear_unit("A", "ampere", 1.0),
        "kA": _linear_unit("kA", "kiloampere", 1e3),
        "mA": _linear_unit("mA", "milliampere", 1e-3),
        "µA": _linear_unit("µA", "microampere", 1e-6),
        "nA": _linear_unit("nA", "nanoampere", 1e-9),
    },
    "voltage": {
        "V": _linear_unit("V", "volt", 1.0),
        "kV": _linear_unit("kV", "kilovolt", 1e3),
        "MV": _linear_unit("MV", "megavolt", 1e6),
        "mV": _linear_unit("mV", "millivolt", 1e-3),
        "µV": _linear_unit("µV", "microvolt", 1e-6),
    },
    "capacitance": {
        "F": _linear_unit("F", "farad", 1.0),
        "mF": _linear_unit("mF", "millifarad", 1e-3),
        "µF": _linear_unit("µF", "microfarad", 1e-6),
        "nF": _linear_unit("nF", "nanofarad", 1e-9),
        "pF": _linear_unit("pF", "picofarad", 1e-12),
    },
    "magnetic_flux_density": {
        "T": _linear_unit("T", "tesla", 1.0),
        "mT": _linear_unit("mT", "millitesla", 1e-3),
        "µT": _linear_unit("µT", "microtesla", 1e-6),
        "nT": _linear_unit("nT", "nanotesla", 1e-9),
        "G": _linear_unit("G", "gauss", 1e-4),
    },
    "radiation_dose": {
        "Sv": _linear_unit("Sv", "sievert", 1.0),
        "mSv": _linear_unit("mSv", "millisievert", 1e-3),
        "µSv": _linear_unit("µSv", "microsievert", 1e-6),
        "rem": _linear_unit("rem", "roentgen equivalent man", 0.01),
        "Gy": _linear_unit("Gy", "gray", 1.0),
        "rad": _linear_unit("rad", "radiation absorbed dose", 0.01),
    },
    "density": {
        "kg/m^3": _linear_unit("kg/m^3", "kilogram per cubic metre", 1.0),
        "g/cm^3": _linear_unit("g/cm^3", "gram per cubic centimetre", 1e3),
        "lb/ft^3": _linear_unit("lb/ft^3", "pound per cubic foot", 16.01846337396),
        "lb/in^3": _linear_unit("lb/in^3", "pound per cubic inch", 27679.9047102),
    },
    "temperature": {
        "K": _affine_unit(
            "K",
            "kelvin",
            to_base=lambda value: value,
            from_base=lambda value: value,
        ),
        "°C": _affine_unit(
            "°C",
            "degree Celsius",
            to_base=lambda value: value + 273.15,
            from_base=lambda value: value - 273.15,
        ),
        "°F": _affine_unit(
            "°F",
            "degree Fahrenheit",
            to_base=lambda value: (value - 32.0) * (5.0 / 9.0) + 273.15,
            from_base=lambda value: (value - 273.15) * (9.0 / 5.0) + 32.0,
        ),
        "°R": _affine_unit(
            "°R",
            "degree Rankine",
            to_base=lambda value: value * (5.0 / 9.0),
            from_base=lambda value: value * (9.0 / 5.0),
        ),
    },
    "angle": {
        "rad": _linear_unit("rad", "radian", 1.0),
        "deg": _linear_unit("deg", "degree", 3.141592653589793 / 180.0),
        "grad": _linear_unit("grad", "gradian", 3.141592653589793 / 200.0),
        "amin": _linear_unit("amin", "arcminute", 3.141592653589793 / (180.0 * 60.0)),
        "asec": _linear_unit("asec", "arcsecond", 3.141592653589793 / (180.0 * 3600.0)),
    },
    "time": {
        "s": _linear_unit("s", "second", 1.0),
        "ms": _linear_unit("ms", "millisecond", 1e-3),
        "µs": _linear_unit("µs", "microsecond", 1e-6),
        "ns": _linear_unit("ns", "nanosecond", 1e-9),
        "min": _linear_unit("min", "minute", 60.0),
        "h": _linear_unit("h", "hour", 3600.0),
        "d": _linear_unit("d", "day", 86400.0),
        "wk": _linear_unit("wk", "week", 604800.0),
        "yr": _linear_unit("yr", "year", 31_557_600.0),
    },
    "linear_stiffness": {
        "N/m": _linear_unit("N/m", "newton per metre", 1.0),
        "kN/m": _linear_unit("kN/m", "kilonewton per metre", 1e3),
        "lbf/in": _linear_unit("lbf/in", "pound-force per inch", 175.126835),
        "MN/m": _linear_unit("MN/m", "meganewton per metre", 1e6),
    },
    "rotational_stiffness": {
        "N·m/rad": _linear_unit("N·m/rad", "newton metre per radian", 1.0),
        "kN·m/rad": _linear_unit("kN·m/rad", "kilonewton metre per radian", 1e3),
        "lbf·ft/deg": _linear_unit(
            "lbf·ft/deg",
            "pound-foot per degree",
            1.3558179483314004 / (math.pi / 180.0),
        ),
        "kN·m/deg": _linear_unit(
            "kN·m/deg",
            "kilonewton metre per degree",
            1e3 / (math.pi / 180.0),
        ),
    },
}


def list_supported_quantities() -> list[str]:
    """
    Return the canonical list of unit quantity categories.

    ---Returns---
    quantities : list[str]
        Sorted list of quantity identifiers (e.g. ``"length"``, ``"pressure"``).

    ---LaTeX---
    \\text{Quantities} = \\{ q_1, q_2, \\ldots, q_n \\}
    """

    return sorted(QUANTITY_DEFINITIONS.keys())


def list_units(quantity: str) -> dict[str, str]:
    """
    List the available units and descriptions for a quantity.

    ---Parameters---
    quantity : str
        Quantity identifier (e.g. ``"length"``). Case-insensitive.

    ---Returns---
    units : dict[str, str]
        Mapping of unit symbols to plain-language names.

    ---LaTeX---
    u_i = (\\text{symbol}_i,\\, \\text{name}_i) \\quad \\forall i \\in Q
    """

    key = quantity.lower()
    if key not in QUANTITY_DEFINITIONS:
        raise ValueError(f"Unsupported quantity '{quantity}'.")
    return {
        symbol: definition.name
        for symbol, definition in QUANTITY_DEFINITIONS[key].items()
    }


def convert_value(quantity: str, from_unit: str, to_unit: str, value: float) -> float:
    """
    Convert a scalar value between compatible units.

    The conversion is performed by mapping the input to the quantity's base unit
    and then applying the inverse transform of the destination unit.

    ---Parameters---
    quantity : str
        Quantity identifier such as ``"length"``, ``"force"``, or ``"temperature"``.
    from_unit : str
        Symbol for the starting unit (e.g. ``"ft"``).
    to_unit : str
        Symbol for the target unit (e.g. ``"m"``).
    value : float
        Numerical value expressed in the starting unit. Must be finite.

    ---Returns---
    converted_value : float
        Value represented in the requested target unit.

    ---LaTeX---
    x_{\\text{to}} = f_{\\text{to}}^{-1}\\left(f_{\\text{from}}(x_{\\text{from}})\\right)

    ---References---
    NIST Special Publication 811. (2008). *Guide for the Use of the International System of Units (SI)*.
    """

    key = quantity.lower()
    if key not in QUANTITY_DEFINITIONS:
        raise ValueError(f"Unsupported quantity '{quantity}'.")

    units = QUANTITY_DEFINITIONS[key]
    if from_unit not in units:
        raise ValueError(f"Unit '{from_unit}' is not valid for quantity '{quantity}'.")
    if to_unit not in units:
        raise ValueError(f"Unit '{to_unit}' is not valid for quantity '{quantity}'.")

    definition_from = units[from_unit]
    definition_to = units[to_unit]

    base_value = definition_from.to_base(value)
    return definition_to.from_base(base_value)


def conversion_factor(quantity: str, from_unit: str, to_unit: str) -> float:
    """
    Compute the multiplicative factor when no offset is involved.

    For affine conversions (e.g., temperatures with offsets) this function
    raises an error because a constant factor does not exist.

    ---Parameters---
    quantity : str
        Quantity identifier (case-insensitive).
    from_unit : str
        Source unit symbol.
    to_unit : str
        Destination unit symbol.

    ---Returns---
    factor : float
        Multiplicative factor such that ``value_to = factor * value_from``.

    ---LaTeX---
    k = \\frac{f_{\\text{to}}^{-1}\\left(f_{\\text{from}}(x)\\right)}{x} \\quad \\text{(independent of } x \\text{)}
    """

    key = quantity.lower()
    if key not in QUANTITY_DEFINITIONS:
        raise ValueError(f"Unsupported quantity '{quantity}'.")

    units = QUANTITY_DEFINITIONS[key]
    definition_from = units.get(from_unit)
    definition_to = units.get(to_unit)
    if definition_from is None:
        raise ValueError(f"Unit '{from_unit}' is not valid for quantity '{quantity}'.")
    if definition_to is None:
        raise ValueError(f"Unit '{to_unit}' is not valid for quantity '{quantity}'.")

    # Use two sample points to detect affine behaviour.
    sample_a = definition_to.from_base(definition_from.to_base(0.0))
    sample_b = definition_to.from_base(definition_from.to_base(1.0))
    if abs(sample_a) > 1e-12:
        raise ValueError("Conversion includes an offset; a single factor is undefined.")
    return sample_b


def convert_units(quantity: str, from_unit: str, to_unit: str, value: float) -> dict[str, float]:
    """
    High-level helper that returns structured conversion results for the UI.

    ---Parameters---
    quantity : str
        Quantity identifier such as ``"length"`` or ``"pressure"``.
    from_unit : str
        Symbol of the starting unit.
    to_unit : str
        Symbol of the target unit.
    value : float
        Numerical value to convert. Must be a finite real number.

    ---Returns---
    converted_value : float
        Result expressed in the target unit.
    base_value : float
        Intermediate value expressed in the base SI unit for the quantity.
    has_multiplier_only : bool
        Flag indicating whether the conversion is purely multiplicative.
    multiplier : float
        Multiplicative factor when available, otherwise ``0.0``.

    ---LaTeX---
    x_{\\text{base}} = f_{\\text{from}}(x_{\\text{from}}),\\quad
    x_{\\text{to}} = f_{\\text{to}}^{-1}(x_{\\text{base}})

    ---References---
    BIPM. (2019). *The International System of Units (SI)*, 9th edition.
    """

    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError("Value must be a real number.") from exc

    converted = convert_value(quantity, from_unit, to_unit, numeric_value)
    key = quantity.lower()
    base = QUANTITY_DEFINITIONS[key][from_unit].to_base(numeric_value)

    has_multiplier = False
    multiplier = 0.0
    try:
        multiplier = conversion_factor(quantity, from_unit, to_unit)
        has_multiplier = True
    except ValueError:
        has_multiplier = False

    return {
        "converted_value": converted,
        "base_value": base,
        "has_multiplier_only": has_multiplier,
        "multiplier": multiplier,
    }


def get_unit_catalog() -> dict[str, dict[str, dict[str, str]]]:
    """
    Provide a serialisable catalog of quantities and units for client usage.

    ---Returns---
    catalog : dict[str, dict[str, dict[str, str]]]
        Nested mapping ``{quantity: {unit_symbol: {'name': ..., 'symbol': ...}}}``.

    ---LaTeX---
    \\mathcal{C} = \\{ (q, U_q) \\mid q \\in Q \\}
    """

    catalog: dict[str, dict[str, dict[str, str]]] = {}
    for quantity, units in QUANTITY_DEFINITIONS.items():
        catalog[quantity] = {
            symbol: {
                "name": definition.name,
                "symbol": definition.symbol,
            }
            for symbol, definition in units.items()
        }
    return catalog
