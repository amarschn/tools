"""
Acoustics and whistle physics calculations.

This module contains functions for analyzing whistle acoustics, edge-tone phenomena,
and resonator behavior for musical instruments and fluid-structure interactions.
"""

from math import log10, pi, sqrt
from typing import Any, Dict, List, Union

# Physical constants
GAMMA = 1.4  # Ratio of specific heats for air
R = 287.0    # Specific gas constant for dry air (J/kg·K)

OCTAVE_BANDS_HZ = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
OCTAVE_WEIGHTING_A = {
    63: -26.2,
    125: -16.1,
    250: -8.6,
    500: -3.2,
    1000: 0.0,
    2000: 1.2,
    4000: 1.0,
    8000: -1.1,
}
OCTAVE_WEIGHTING_C = {
    63: -0.8,
    125: -0.2,
    250: 0.0,
    500: 0.0,
    1000: 0.0,
    2000: -0.2,
    4000: -0.8,
    8000: -3.0,
}
SPREADING_MODELS = {
    "point": {"k": 20.0, "c": 11.0},
    "line": {"k": 10.0, "c": 8.0},
    "plane": {"k": 0.0, "c": 0.0},
}


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


def _parse_level_list(levels: Union[str, List[float], None]) -> List[float]:
    if levels is None:
        return []
    if isinstance(levels, list):
        return [float(value) for value in levels if value is not None]

    text = str(levels).strip()
    if not text:
        return []

    normalized = text.replace(";", ",").replace("\n", ",")
    values = []
    for token in normalized.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(float(token))
    return values


def _logspace(start: float, stop: float, count: int) -> List[float]:
    if count < 2:
        raise ValueError("distance sweep requires at least 2 points")
    ratio = (stop / start) ** (1.0 / (count - 1))
    return [start * (ratio ** idx) for idx in range(count)]


def _linspace(start: float, stop: float, count: int) -> List[float]:
    if count < 2:
        raise ValueError("distance sweep requires at least 2 points")
    step = (stop - start) / (count - 1)
    return [start + step * idx for idx in range(count)]


def _combine_levels(levels_db: List[float]) -> float:
    if not levels_db:
        return float("nan")
    linear_sum = sum(10 ** (level / 10.0) for level in levels_db)
    return 10.0 * log10(linear_sum)


def calculate_sound_levels(
    conversion_mode: str,
    source_type: str,
    known_level_db: float,
    distance_m: float,
    directivity_q: float,
    distance_min_m: float,
    distance_max_m: float,
    combine_levels_db: str,
    band_weighting: str,
    band_63_db: float,
    band_125_db: float,
    band_250_db: float,
    band_500_db: float,
    band_1000_db: float,
    band_2000_db: float,
    band_4000_db: float,
    band_8000_db: float,
) -> Dict[str, Any]:
    """
    Converts between sound power and pressure levels, combines sources, and summarizes octave-band spectra.

    This tool applies simplified free-field spreading models for point, line, and plane sources
    while also supporting logarithmic level addition for incoherent sources and octave-band
    summaries with optional A/C weighting. Equations align with ISO 9613 for divergence
    guidance and IEC 61672 weighting tables (octave-band approximations).

    ---Parameters---
    conversion_mode : str
        Conversion direction: "swl_to_spl" for source sound power to receiver SPL or
        "spl_to_swl" for inferring SWL from a measured SPL at distance_m.
    source_type : str
        Source geometry model: "point", "line", or "plane" for spherical, cylindrical,
        or planar spreading assumptions.
    known_level_db : float
        The input level in dB. Interpreted as SWL when conversion_mode is "swl_to_spl"
        and as SPL when conversion_mode is "spl_to_swl".
    distance_m : float
        Source-to-receiver distance in meters for the primary conversion.
    directivity_q : float
        Directivity factor Q (dimensionless). Use 1 for free field, 2 for hemisphere,
        4 for wall-floor corner, and 8 for trihedral corner.
    distance_min_m : float
        Minimum distance for the SPL sweep chart (m). Must be positive.
    distance_max_m : float
        Maximum distance for the SPL sweep chart (m). Must exceed distance_min_m.
    combine_levels_db : str
        Comma-separated list of source levels in dB to combine (e.g., "72, 76, 80").
        Leave blank to skip the combination result.
    band_weighting : str
        Octave-band weighting selection: "Z" (flat), "A", or "C".
    band_63_db : float
        Octave-band SPL at 63 Hz (dB).
    band_125_db : float
        Octave-band SPL at 125 Hz (dB).
    band_250_db : float
        Octave-band SPL at 250 Hz (dB).
    band_500_db : float
        Octave-band SPL at 500 Hz (dB).
    band_1000_db : float
        Octave-band SPL at 1000 Hz (dB).
    band_2000_db : float
        Octave-band SPL at 2000 Hz (dB).
    band_4000_db : float
        Octave-band SPL at 4000 Hz (dB).
    band_8000_db : float
        Octave-band SPL at 8000 Hz (dB).

    ---Returns---
    spl_db : float
        Sound pressure level at distance_m in dB re 20 microPascal.
    swl_db : float
        Sound power level in dB re 1 picowatt.
    divergence_loss_db : float
        Geometric spreading loss A_div based on source_type and distance_m (dB).
    directivity_gain_db : float
        Directivity gain G_dir applied from Q (dB).
    combined_level_db : float
        Logarithmically combined level from combine_levels_db (dB). NaN if no inputs.
    combine_count : int
        Count of valid source levels used in the combination.
    octave_overall_db : float
        Overall (Z-weighted) level from the octave-band inputs (dB).
    octave_weighted_db : float
        Overall level after applying the selected octave-band weighting (dB).
    octave_weighting_label : str
        Weighting label applied to octave_weighted_db ("Z", "A", or "C").
    distance_sweep_m : list
        Distances used for the SPL sweep chart (m).
    spl_sweep_db : list
        SPL values corresponding to distance_sweep_m (dB).
    octave_bands_hz : list
        Center frequencies for the octave-band data (Hz).
    octave_levels_db : list
        Octave-band levels for the Z-weighted spectrum (dB).
    octave_weighted_levels_db : list
        Octave-band levels after applying the selected weighting (dB).
    subst_spl_db : str
        Substituted SPL equation for display.
    subst_swl_db : str
        Substituted SWL equation for display.
    subst_divergence_loss_db : str
        Substituted divergence loss equation for display.
    subst_directivity_gain_db : str
        Substituted directivity gain equation for display.
    subst_combined_level_db : str
        Substituted level-combination equation for display.
    subst_octave_overall_db : str
        Substituted octave-band overall equation for display.
    subst_octave_weighted_db : str
        Substituted weighted octave-band equation for display.

    ---LaTeX---
    L_{p} = L_{w} - A_{div} + G_{dir}
    A_{div} = k \\log_{10}(r) + C
    G_{dir} = 10 \\log_{10}(Q)
    L_{tot} = 10 \\log_{10}(\\sum_{i=1}^{N} 10^{L_{i}/10})
    L_{i,w} = L_{i} + W_{i}
    """
    if conversion_mode not in {"swl_to_spl", "spl_to_swl"}:
        raise ValueError("conversion_mode must be 'swl_to_spl' or 'spl_to_swl'")
    if source_type not in SPREADING_MODELS:
        raise ValueError("source_type must be 'point', 'line', or 'plane'")
    if distance_m <= 0:
        raise ValueError("distance_m must be positive")
    if distance_min_m <= 0 or distance_max_m <= 0:
        raise ValueError("distance_min_m and distance_max_m must be positive")
    if distance_max_m <= distance_min_m:
        raise ValueError("distance_max_m must exceed distance_min_m")
    if directivity_q <= 0:
        raise ValueError("directivity_q must be positive")
    if band_weighting not in {"Z", "A", "C"}:
        raise ValueError("band_weighting must be 'Z', 'A', or 'C'")

    model = SPREADING_MODELS[source_type]
    k = model["k"]
    c = model["c"]
    divergence_loss_db = k * log10(distance_m) + c
    directivity_gain_db = 10.0 * log10(directivity_q)

    if conversion_mode == "swl_to_spl":
        swl_db = float(known_level_db)
        spl_db = swl_db - divergence_loss_db + directivity_gain_db
    else:
        spl_db = float(known_level_db)
        swl_db = spl_db + divergence_loss_db - directivity_gain_db

    sweep_points = 45
    if source_type == "point":
        distance_sweep_m = _logspace(distance_min_m, distance_max_m, sweep_points)
    else:
        distance_sweep_m = _linspace(distance_min_m, distance_max_m, sweep_points)

    spl_sweep_db = [
        swl_db - (k * log10(dist) + c) + directivity_gain_db
        for dist in distance_sweep_m
    ]

    combine_levels = _parse_level_list(combine_levels_db)
    combined_level_db = _combine_levels(combine_levels)

    octave_levels_db = [
        float(band_63_db),
        float(band_125_db),
        float(band_250_db),
        float(band_500_db),
        float(band_1000_db),
        float(band_2000_db),
        float(band_4000_db),
        float(band_8000_db),
    ]
    octave_overall_db = _combine_levels(octave_levels_db)

    weighting_map = OCTAVE_WEIGHTING_A if band_weighting == "A" else OCTAVE_WEIGHTING_C
    octave_weighted_levels_db = []
    for band, level in zip(OCTAVE_BANDS_HZ, octave_levels_db):
        if band_weighting == "Z":
            octave_weighted_levels_db.append(level)
        else:
            octave_weighted_levels_db.append(level + weighting_map[band])

    octave_weighted_db = _combine_levels(octave_weighted_levels_db)

    subst_divergence_loss_db = (
        f"A_{{div}} = {k:.1f} \\log_{{10}}({distance_m:.3g}) + {c:.1f}"
        f" = {divergence_loss_db:.2f}"
    )
    subst_directivity_gain_db = (
        f"G_{{dir}} = 10 \\log_{{10}}({directivity_q:.3g})"
        f" = {directivity_gain_db:.2f}"
    )
    subst_spl_db = (
        f"L_{{p}} = {swl_db:.2f} - {divergence_loss_db:.2f} + {directivity_gain_db:.2f}"
        f" = {spl_db:.2f}"
    )
    subst_swl_db = (
        f"L_{{w}} = {spl_db:.2f} + {divergence_loss_db:.2f} - {directivity_gain_db:.2f}"
        f" = {swl_db:.2f}"
    )
    subst_combined_level_db = ""
    if combine_levels:
        sum_terms = " + ".join([f"10^{{{level:.1f}/10}}" for level in combine_levels])
        subst_combined_level_db = (
            f"L_{{tot}} = 10 \\log_{{10}}({sum_terms}) = {combined_level_db:.2f}"
        )

    octave_sum_terms = " + ".join([f"10^{{{level:.1f}/10}}" for level in octave_levels_db])
    subst_octave_overall_db = (
        f"L_{{tot}} = 10 \\log_{{10}}({octave_sum_terms}) = {octave_overall_db:.2f}"
    )
    weighted_terms = " + ".join(
        [f"10^{{{level:.1f}/10}}" for level in octave_weighted_levels_db]
    )
    subst_octave_weighted_db = (
        f"L_{{tot}} = 10 \\log_{{10}}({weighted_terms}) = {octave_weighted_db:.2f}"
    )

    return {
        "spl_db": round(spl_db, 2),
        "swl_db": round(swl_db, 2),
        "divergence_loss_db": round(divergence_loss_db, 2),
        "directivity_gain_db": round(directivity_gain_db, 2),
        "combined_level_db": round(combined_level_db, 2) if combine_levels else float("nan"),
        "combine_count": len(combine_levels),
        "octave_overall_db": round(octave_overall_db, 2),
        "octave_weighted_db": round(octave_weighted_db, 2),
        "octave_weighting_label": band_weighting,
        "distance_sweep_m": distance_sweep_m,
        "spl_sweep_db": spl_sweep_db,
        "octave_bands_hz": OCTAVE_BANDS_HZ,
        "octave_levels_db": octave_levels_db,
        "octave_weighted_levels_db": octave_weighted_levels_db,
        "subst_spl_db": subst_spl_db,
        "subst_swl_db": subst_swl_db,
        "subst_divergence_loss_db": subst_divergence_loss_db,
        "subst_directivity_gain_db": subst_directivity_gain_db,
        "subst_combined_level_db": subst_combined_level_db,
        "subst_octave_overall_db": subst_octave_overall_db,
        "subst_octave_weighted_db": subst_octave_weighted_db,
    }
