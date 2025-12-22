"""
Acoustics and whistle physics calculations.

This module contains functions for analyzing whistle acoustics, edge-tone phenomena,
and resonator behavior for musical instruments and fluid-structure interactions.
"""

from math import sqrt, pi
from typing import List, Dict, Any, Union

# Physical constants
GAMMA = 1.4  # Ratio of specific heats for air
R = 287.0    # Specific gas constant for dry air (J/kg·K)


def calculate_whistle_acoustics(
    resonator_type: str,
    temperature: float,
    jet_thickness: float,
    stages: str,
    pipe_length: float = 0.3,
    pipe_end_correction: float = 0.005,
    pipe_n_modes: int = 6,
    helm_neck_area: float = 0.0001,
    helm_cavity_volume: float = 0.0005,
    helm_neck_length: float = 0.02
) -> Dict[str, Any]:
    """
    Analyzes whistle acoustics by calculating resonator frequencies and edge-tone locking conditions.

    This tool models the interaction between a resonator's natural frequencies and the
    edge-tones produced by a jet of air striking an edge (labium). A stable musical note
    occurs when the edge-tone frequency matches a resonator mode, creating "acoustic locking."

    Two resonator models are supported:
    - **Pipe (Open-Closed)**: Models flutes, tin whistles, and similar tube instruments.
      One end is open, one end is closed (or effectively closed). These produce only
      odd harmonics (1st, 3rd, 5th...), giving them a characteristic timbre distinct
      from open-open tubes.
    - **Helmholtz**: Models bottle resonators and cavity-based instruments. The cavity
      air acts as a spring and the neck air as a mass, producing a single dominant mode.

    The edge-tone frequency is given by f_edge = St × U / d, where St is the Strouhal
    number (stage), U is jet velocity, and d is jet thickness. Locking occurs when
    f_edge equals a resonator mode frequency.

    ---Parameters---
    resonator_type : str
        Type of resonator: "pipe" for open-closed tube (one end open, one closed - like flutes, clarinets) or "helmholtz" for cavity resonator (bottle-like instruments). Open-closed tubes produce only odd harmonics (1st, 3rd, 5th...), giving them a distinct timbral character.
    temperature : float
        Air temperature in Kelvin. Affects speed of sound (typical: 293.15 K = 20°C).
    jet_thickness : float
        Thickness of the air jet at the labium in meters (typical: 0.001 m = 1 mm).
    stages : str
        Comma-separated Strouhal numbers for edge-tone stages (e.g., "0.2,0.4,0.7,1.0,1.3"). These represent discrete oscillation modes when a jet strikes an edge. Default values are empirically determined: Stage 1 (St≈0.2) is the fundamental, Stage 2 (St≈0.4) is the first overtone, etc. Based on Powell (1961) jet-edge interaction research.
    pipe_length : float
        [Pipe only] Physical length of the tube in meters (typical: 0.3 m for tin whistle).
    pipe_end_correction : float
        [Pipe only] End correction factor in meters to account for acoustic radiation at the open end. The effective acoustic length is longer than the physical length because sound waves extend slightly beyond the pipe opening. Typical value: 0.6×radius ≈ 0.3-0.4×diameter. For a 15mm bore, use ~0.005m. Without correction, frequencies would be calculated too high.
    pipe_n_modes : int
        [Pipe only] Number of resonant modes to calculate (typical: 6 modes).
    helm_neck_area : float
        [Helmholtz only] Cross-sectional area of resonator neck in m² (typical: 0.0001 m²).
    helm_cavity_volume : float
        [Helmholtz only] Volume of the resonator cavity in m³ (typical: 0.0005 m³).
    helm_neck_length : float
        [Helmholtz only] Effective length of the resonator neck in meters (typical: 0.02 m).

    ---Returns---
    speed_of_sound : float
        Calculated speed of sound in air at the given temperature (m/s).
    resonator_frequencies : list
        List of resonator mode frequencies in Hz (length depends on resonator type and n_modes).
    locking_table : list
        List of dictionaries containing locking conditions. Each entry has: mode_index (int),
        mode_frequency_hz (float), stage_index (int), strouhal_number (float),
        required_velocity_m_s (float). Sorted by required velocity.
    jet_thickness_mm : float
        The input jet thickness converted to millimeters for display purposes.
    resonator_type_display : str
        Human-readable resonator type for display.

    ---LaTeX---
    c = \\sqrt{\\gamma R T}
    f_{\\text{edge}} = \\frac{St \\cdot U}{d}
    f_{n,\\text{pipe}} = \\frac{(2n-1) c}{4 L_{\\text{eff}}}
    f_{\\text{Helmholtz}} = \\frac{c}{2\\pi} \\sqrt{\\frac{A}{V L_{\\text{eff}}}}
    U_{\\text{lock}} = \\frac{f_{\\text{mode}} \\cdot d}{St}
    """
    try:
        # Parse stages
        stage_values = [float(s.strip()) for s in stages.split(',') if s.strip()]
        if not stage_values:
            return {'error': 'No valid stage values provided'}

        # Calculate speed of sound
        if temperature <= 0:
            return {'error': 'Temperature must be positive'}
        c = sqrt(GAMMA * R * temperature)

        # Calculate resonator frequencies based on type
        if resonator_type == "pipe":
            if pipe_length <= 0:
                return {'error': 'Pipe length must be positive'}
            if pipe_n_modes < 1:
                return {'error': 'Number of modes must be at least 1'}

            L_eff = pipe_length + pipe_end_correction
            # Open-closed pipe: odd harmonics only
            freqs = [((2 * n - 1) * c) / (4.0 * L_eff) for n in range(1, pipe_n_modes + 1)]
            display_type = "Pipe (Open-Closed)"

        elif resonator_type == "helmholtz":
            if helm_neck_area <= 0 or helm_cavity_volume <= 0 or helm_neck_length <= 0:
                return {'error': 'Helmholtz parameters must be positive'}

            # Helmholtz resonator: single mode
            f_helm = (c / (2.0 * pi)) * sqrt(helm_neck_area / (helm_cavity_volume * helm_neck_length))
            freqs = [f_helm]
            display_type = "Helmholtz Resonator"
        else:
            return {'error': 'Invalid resonator type'}

        # Calculate locking conditions
        if jet_thickness <= 0:
            return {'error': 'Jet thickness must be positive'}

        locking_table = []
        for mode_idx, f_mode in enumerate(freqs, start=1):
            for stage_idx, St in enumerate(stage_values, start=1):
                if St <= 0:
                    continue
                # Core locking equation: f_edge = St * U / d = f_mode
                # Solving for U: U = f_mode * d / St
                required_U = f_mode * jet_thickness / St

                locking_table.append({
                    'mode_index': mode_idx,
                    'mode_frequency_hz': round(f_mode, 2),
                    'stage_index': stage_idx,
                    'strouhal_number': St,
                    'required_velocity_m_s': round(required_U, 3)
                })

        # Sort by required velocity
        locking_table.sort(key=lambda x: x['required_velocity_m_s'])

        return {
            'speed_of_sound': round(c, 2),
            'resonator_frequencies': [round(f, 2) for f in freqs],
            'locking_table': locking_table,
            'jet_thickness_mm': round(jet_thickness * 1000, 3),
            'resonator_type_display': display_type
        }

    except ValueError as e:
        return {'error': f'Invalid input: {str(e)}'}
    except Exception as e:
        return {'error': str(e)}
