from __future__ import annotations
from dataclasses import dataclass
from typing import List, Iterable, Dict
from math import sqrt, pi

# --- Physical Constants ---
GAMMA = 1.4  # Ratio of specific heats for air
R = 287.0    # Specific gas constant for dry air (J/kg·K)

# --- Default Edge-Tone Stages ---
# These are typical Strouhal numbers where edge tones are stable.
DEFAULT_STAGES = [0.2, 0.4, 0.7, 1.0, 1.3]

@dataclass
class LockingResult:
    """A dataclass to hold the results of a single locking condition."""
    mode_index: int
    mode_frequency: float
    stage_index: int
    St: float
    required_U: float

def speed_of_sound(T: float) -> float:
    """Calculates the speed of sound in air at a given temperature.

    Args:
        T: Air temperature in Kelvin.

    Returns:
        The speed of sound in m/s.
    """
    return sqrt(GAMMA * R * T)

def open_closed_mode_frequencies(L: float, c: float, n_max: int = 5, end_correction: float = 0.0) -> List[float]:
    """Calculates the resonant frequencies for an open-closed tube (e.g., a simple flute).

    Args:
        L: The physical length of the tube in meters.
        c: The speed of sound in m/s.
        n_max: The maximum number of modes to calculate.
        end_correction: The correction factor to add to the length, in meters.

    Returns:
        A list of resonant frequencies in Hz.
    """
    if L <= 0:
        return []
    if n_max < 1:
        return []
    L_eff = L + end_correction
    # For an open-closed pipe, frequencies are odd multiples of the fundamental.
    return [((2 * n - 1) * c) / (4.0 * L_eff) for n in range(1, n_max + 1)]

def helmholtz_frequency(A: float, V: float, L_eff: float, c: float) -> float:
    """Calculates the resonant frequency of a Helmholtz resonator (e.g., a bottle).

    Args:
        A: The cross-sectional area of the neck in m².
        V: The volume of the cavity in m³.
        L_eff: The effective length of the neck in meters.
        c: The speed of sound in m/s.

    Returns:
        The Helmholtz resonance frequency in Hz.
    """
    if A <= 0 or V <= 0 or L_eff <= 0:
        return 0.0
    return (c / (2.0 * pi)) * ((A / (V * L_eff)) ** 0.5)

def get_locking_table(
    resonator_modes: List[float],
    d: float,
    stages: Iterable[float] = DEFAULT_STAGES
) -> List[LockingResult]:
    """
    Calculates the jet speeds (U) required to lock edge-tone stages to resonator modes.
    """
    results: List[LockingResult] = []
    if d <= 0:
        return []
        
    # For each resonator mode...
    for i, f_mode in enumerate(resonator_modes, start=1):
        # ...calculate the required jet speed for each edge-tone stage.
        for k, St in enumerate(stages, start=1):
            if St <= 0:
                continue
            # The core locking condition: f_mode = f_edge_tone = St * U / d
            # Rearranging for U gives: U = f_mode * d / St
            required_U = f_mode * d / St
            results.append(LockingResult(i, f_mode, k, St, required_U))

    # Sort the table by the jet speed needed for locking.
    results.sort(key=lambda r: r.required_U)
    return results

def format_locking_table(rows: List[LockingResult]) -> List[Dict[str, float]]:
    """Formats the locking results into a list of dictionaries for easy rendering."""
    table = []
    for r in rows:
        table.append({
            "mode_n": r.mode_index,
            "mode_freq_Hz": r.mode_frequency,
            "stage": r.stage_index,
            "St": r.St,
            "U_lock_m_per_s": r.required_U
        })
    return table
