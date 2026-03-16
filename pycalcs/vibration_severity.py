"""
Vibration severity evaluation and fault signature triage tool.
Combines ISO 20816 zone classification with VDI 3839 fault pattern matching.
"""

from __future__ import annotations

import json
import math
from typing import Any

# =============================================================================
# ISO 20816-3 MACHINE TYPE → GROUP MAPPING
# =============================================================================

MACHINE_GROUPS: dict[str, dict[str, Any]] = {
    "motor_large": {
        "display": "Electric Motor (> 15 kW)",
        "group": "1",
        "group_description": "Large machines on rigid foundations, nominal power > 300 kW, shaft height ≥ 315 mm",
        "iso_part": "ISO 20816-3",
        "scope_note": "If power < 15 kW, ISO 20816-3 Part 3 does not apply.",
    },
    "motor_medium": {
        "display": "Electric Motor (15–300 kW)",
        "group": "2",
        "group_description": "Medium machines 15–300 kW on rigid foundations, or > 15 kW on flexible foundations",
        "iso_part": "ISO 20816-3",
        "scope_note": "",
    },
    "pump": {
        "display": "Centrifugal Pump",
        "group": "3",
        "group_description": "Pumps with separate driver, power > 15 kW",
        "iso_part": "ISO 20816-3",
        "scope_note": "For pumps with power ≤ 15 kW consult manufacturer limits.",
    },
    "fan": {
        "display": "Centrifugal Fan / Blower",
        "group": "3",
        "group_description": "Fans and blowers with separate driver",
        "iso_part": "ISO 20816-3",
        "scope_note": "",
    },
    "compressor_centrifugal": {
        "display": "Centrifugal Compressor",
        "group": "1",
        "group_description": "Large turbomachinery on rigid foundations",
        "iso_part": "ISO 20816-3",
        "scope_note": "For reciprocating compressors consider ISO 20816-8.",
    },
    "compressor_reciprocating": {
        "display": "Reciprocating Compressor",
        "group": "1",
        "group_description": "Reciprocating machines",
        "iso_part": "ISO 20816-8",
        "scope_note": "ISO 20816-8 covers compressor system vibration. Consult that standard for full guidance.",
    },
    "generator": {
        "display": "Generator",
        "group": "1",
        "group_description": "Large electrical machines on rigid foundations",
        "iso_part": "ISO 20816-3",
        "scope_note": "For turbogenerators > 50 MW on land, consider ISO 20816-2.",
    },
    "gearbox": {
        "display": "Gearbox / Gear Unit",
        "group": "1",
        "group_description": "Industrial gear units",
        "iso_part": "ISO 20816-9",
        "scope_note": "ISO 20816-9 covers gear unit acceptance testing. This tool applies ISO 20816-3 heuristics only.",
    },
    "general": {
        "display": "General Industrial Machine",
        "group": "2",
        "group_description": "General industrial machinery not covered by a specific part",
        "iso_part": "ISO 20816-3",
        "scope_note": "",
    },
}

# Default placeholder zone limits (mm/s RMS, ISO 20816-3)
# These are INDICATIVE ONLY - users must enter their own values from the standard.
DEFAULT_ZONE_LIMITS: dict[str, dict[str, float]] = {
    "1": {"ab": 2.3, "bc": 4.5, "cd": 7.1},
    "2": {"ab": 3.5, "bc": 7.1, "cd": 11.2},
    "3": {"ab": 3.5, "bc": 7.1, "cd": 11.2},
}

ZONE_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "A": {
        "label": "Zone A — New / Recently Serviced",
        "detail": "Vibration typical of new or recently commissioned machinery in good condition.",
        "action": "No action required. Establish as baseline if first measurement.",
        "css_class": "success",
    },
    "B": {
        "label": "Zone B — Acceptable for Continuous Operation",
        "detail": "Vibration acceptable for unrestricted long-term operation.",
        "action": "Continue normal operation. Monitor trend at scheduled intervals.",
        "css_class": "success",
    },
    "C": {
        "label": "Zone C — Unsatisfactory for Long-Term Operation",
        "detail": "Vibration unsatisfactory for continuous unrestricted operation. Short-term operation acceptable while investigation is initiated.",
        "action": "Investigate cause. Increase monitoring frequency. Plan corrective action.",
        "css_class": "warning",
    },
    "D": {
        "label": "Zone D — Damage Risk",
        "detail": "Vibration severe enough to cause damage to the machine. Immediate action required.",
        "action": "Consider shutdown. Inspect immediately. Do not restart without investigation.",
        "css_class": "danger",
    },
}

# =============================================================================
# FAULT SIGNATURE DATABASE (VDI 3839)
# =============================================================================

FAULT_SIGNATURES: list[dict[str, Any]] = [
    {
        "id": "unbalance",
        "display_name": "Mass Unbalance",
        "vdi_reference": "VDI 3839-2",
        "short_description": "Rotating mass asymmetry creating a synchronous centrifugal force.",
        "primary_freq": "Dominant 1× RPM in radial direction",
        "direction_pattern": "Radial (H ≈ V). Low axial.",
        "speed_dependency": "Increases with speed² — very sensitive to speed changes.",
        "bearing_types": ["rolling_element", "fluid_film", "unknown"],
        "machine_types": ["all"],
        "direction_scores": {"radial_h": 1.0, "radial_v": 1.0, "axial": 0.2},
        "axial_penalty": True,
        "follow_up": [
            "Measure both horizontal and vertical radial: if both elevated with H ≈ V, unbalance is strongly indicated.",
            "Check phase at 1× RPM with a strobe or phase reference — stable phase consistent with unbalance.",
            "Compare readings at different speeds: if amplitude increases roughly as n², unbalance is likely.",
            "Inspect rotor for missing material, build-up (scale, deposits), or recent maintenance.",
            "Perform dynamic balancing in two planes.",
        ],
    },
    {
        "id": "misalignment_angular",
        "display_name": "Angular Misalignment",
        "vdi_reference": "VDI 3839-3",
        "short_description": "Shaft centerlines intersect at coupling — angular offset.",
        "primary_freq": "High axial vibration at 1× and 2× RPM",
        "direction_pattern": "Axial dominant. 180° phase change across coupling in axial direction.",
        "speed_dependency": "Present at any speed. Worse at higher speeds.",
        "bearing_types": ["rolling_element", "fluid_film", "unknown"],
        "machine_types": ["all"],
        "direction_scores": {"radial_h": 0.3, "radial_v": 0.3, "axial": 1.0},
        "axial_penalty": False,
        "follow_up": [
            "Measure axial vibration at both drive-end and non-drive-end bearings.",
            "Check for 180° phase reversal across the coupling in the axial direction.",
            "Compare axial amplitude at 1× and 2× RPM — both elevated in angular misalignment.",
            "Verify alignment with dial indicators or laser alignment tool.",
            "Check for soft-foot before realignment.",
        ],
    },
    {
        "id": "misalignment_parallel",
        "display_name": "Parallel (Offset) Misalignment",
        "vdi_reference": "VDI 3839-3",
        "short_description": "Shaft centerlines parallel but offset — radial offset at coupling.",
        "primary_freq": "2× RPM typically dominant in radial direction; 1× also present",
        "direction_pattern": "Radial (often horizontal). 180° phase change across coupling radially.",
        "speed_dependency": "Present at any speed.",
        "bearing_types": ["rolling_element", "fluid_film", "unknown"],
        "machine_types": ["all"],
        "direction_scores": {"radial_h": 1.0, "radial_v": 0.7, "axial": 0.3},
        "axial_penalty": False,
        "follow_up": [
            "Check for 2× RPM peak that is similar to or greater than 1× peak in the radial direction.",
            "Measure phase across coupling radially — 180° difference indicates parallel misalignment.",
            "Verify coupling alignment with laser tool.",
            "Inspect coupling for wear or inadequate lubrication.",
            "Check for thermally induced misalignment (measure cold vs. hot).",
        ],
    },
    {
        "id": "looseness_structural",
        "display_name": "Structural / Foundation Looseness",
        "vdi_reference": "VDI 3839-4",
        "short_description": "Loose baseplate, grout, or anchor bolts causing non-linear response.",
        "primary_freq": "Sub-harmonics (0.5×, 0.33×) and/or many harmonics (3×, 4×, 5×…)",
        "direction_pattern": "Vertical direction often shows asymmetric waveform. Phase unstable.",
        "speed_dependency": "Can appear intermittently or change with load.",
        "bearing_types": ["rolling_element", "fluid_film", "unknown"],
        "machine_types": ["all"],
        "direction_scores": {"radial_h": 0.6, "radial_v": 1.0, "axial": 0.3},
        "axial_penalty": False,
        "follow_up": [
            "Inspect all hold-down bolts for tightness.",
            "Check grout condition and baseplate contact.",
            "Look for sub-harmonics (0.5×, 0.33× RPM) in the frequency spectrum.",
            "Perform soft-foot check — loosen one bolt at a time and watch for amplitude change.",
            "Check for cracked welds or broken supports.",
        ],
    },
    {
        "id": "looseness_rotating",
        "display_name": "Rotating Looseness (Bearing Seat / Shaft Fit)",
        "vdi_reference": "VDI 3839-4",
        "short_description": "Loose bearing housing, impeller fit, or keyway — rotating-part looseness.",
        "primary_freq": "Many harmonics of 1× RPM (2×, 3×, 4×…). Phase unstable.",
        "direction_pattern": "Radial. Phase varies between measurements.",
        "speed_dependency": "Often speed-dependent; may appear/disappear with load.",
        "bearing_types": ["rolling_element", "fluid_film", "unknown"],
        "machine_types": ["all"],
        "direction_scores": {"radial_h": 1.0, "radial_v": 1.0, "axial": 0.3},
        "axial_penalty": False,
        "follow_up": [
            "Check for many harmonics of running speed (2×, 3×, 4× etc.) in the spectrum.",
            "Inspect bearing housing fit and any press-fit components for looseness.",
            "Check impeller or coupling hub fit on shaft.",
            "Inspect keyways and keys for wear.",
            "Compare phase readings taken at different times — instability indicates looseness.",
        ],
    },
    {
        "id": "bearing_defect",
        "display_name": "Rolling Element Bearing Defect",
        "vdi_reference": "VDI 3839-5",
        "short_description": "Defect on inner race (BPFI), outer race (BPFO), rolling element (BSF), or cage (FTF).",
        "primary_freq": "Bearing defect frequencies (BPFO, BPFI, BSF, FTF) and their sidebands",
        "direction_pattern": "Any direction. High-frequency acceleration (>1 kHz) elevated.",
        "speed_dependency": "Defect frequencies proportional to speed.",
        "bearing_types": ["rolling_element"],
        "machine_types": ["all"],
        "direction_scores": {"radial_h": 0.9, "radial_v": 1.0, "axial": 0.7},
        "axial_penalty": False,
        "follow_up": [
            "Measure acceleration (not just velocity) — early bearing defects appear as high-frequency energy.",
            "Calculate bearing defect frequencies (BPFO, BPFI, BSF, FTF) from bearing geometry and look for these peaks.",
            "Check for sidebands around defect frequencies at multiples of 1× RPM (sign of advanced defect).",
            "Assess kurtosis or peak-to-RMS ratio (crest factor) — elevated kurtosis indicates impulsive content.",
            "If early stage: increase monitoring frequency and plan bearing replacement at next opportunity.",
            "If advanced: consider urgent replacement — check lubrication, contamination, and load.",
        ],
    },
    {
        "id": "electrical",
        "display_name": "Electrical / Electromagnetic Excitation",
        "vdi_reference": "VDI 3839 (general)",
        "short_description": "Vibration from electromagnetic forces at line frequency or twice line frequency.",
        "primary_freq": "1× and 2× electrical line frequency (50 Hz → 100 Hz; 60 Hz → 120 Hz); pole-pass frequency",
        "direction_pattern": "Radial. Disappears or changes immediately on power cut.",
        "speed_dependency": "Fixed at electrical frequencies, not RPM multiples.",
        "bearing_types": ["rolling_element", "fluid_film", "unknown"],
        "machine_types": ["motor_large", "motor_medium", "generator"],
        "direction_scores": {"radial_h": 0.9, "radial_v": 0.9, "axial": 0.3},
        "axial_penalty": False,
        "follow_up": [
            "Coast down test: switch off power and observe vibration — electrical excitation drops to zero immediately at power-off.",
            "Check for peaks at 1× and 2× line frequency (100 Hz or 120 Hz).",
            "Check stator air gap — uneven gap produces strong 2× line frequency vibration.",
            "Inspect rotor bars for cracks (look for sidebands around 1× at pole-pass frequency).",
            "Check supply voltage balance and for voltage harmonics.",
        ],
    },
]

# =============================================================================
# BEARING DEFECT FREQUENCY CALCULATION
# =============================================================================


def calculate_bearing_defect_frequencies(
    rpm: float,
    roller_count: int,
    pitch_diameter_mm: float,
    roller_diameter_mm: float,
    contact_angle_deg: float,
) -> dict[str, float]:
    """
    Calculate rolling element bearing defect frequencies.

    ---Parameters---
    rpm : float
        Shaft speed (RPM).
    roller_count : int
        Number of rolling elements.
    pitch_diameter_mm : float
        Bearing pitch circle diameter (mm).
    roller_diameter_mm : float
        Rolling element (ball/roller) diameter (mm).
    contact_angle_deg : float
        Contact angle in degrees (typically 0° for radial, 15°–25° for angular contact).

    ---Returns---
    shaft_hz : float
        Shaft rotation frequency (Hz).
    bpfo_hz : float
        Ball Pass Frequency Outer race (Hz) — outer race defect frequency.
    bpfi_hz : float
        Ball Pass Frequency Inner race (Hz) — inner race defect frequency.
    bsf_hz : float
        Ball Spin Frequency (Hz) — rolling element defect frequency.
    ftf_hz : float
        Fundamental Train (cage) Frequency (Hz).

    ---LaTeX---
    f_{shaft} = \\frac{n}{60}
    BPFO = \\frac{N_r}{2} \\cdot f_{shaft} \\left(1 - \\frac{d_r}{d_p} \\cos\\alpha\\right)
    BPFI = \\frac{N_r}{2} \\cdot f_{shaft} \\left(1 + \\frac{d_r}{d_p} \\cos\\alpha\\right)
    BSF = \\frac{d_p}{2 d_r} \\cdot f_{shaft} \\left(1 - \\left(\\frac{d_r}{d_p}\\right)^2 \\cos^2\\alpha\\right)
    FTF = \\frac{f_{shaft}}{2} \\left(1 - \\frac{d_r}{d_p} \\cos\\alpha\\right)
    """
    if rpm <= 0:
        raise ValueError("rpm must be positive.")
    if roller_count < 3:
        raise ValueError("roller_count must be at least 3.")
    if pitch_diameter_mm <= 0 or roller_diameter_mm <= 0:
        raise ValueError("Bearing diameters must be positive.")
    if roller_diameter_mm >= pitch_diameter_mm:
        raise ValueError("roller_diameter_mm must be less than pitch_diameter_mm.")

    f_s = rpm / 60.0
    alpha = math.radians(contact_angle_deg)
    d_ratio = (roller_diameter_mm / pitch_diameter_mm) * math.cos(alpha)

    bpfo = (roller_count / 2.0) * f_s * (1.0 - d_ratio)
    bpfi = (roller_count / 2.0) * f_s * (1.0 + d_ratio)
    bsf = (pitch_diameter_mm / (2.0 * roller_diameter_mm)) * f_s * (1.0 - d_ratio**2)
    ftf = (f_s / 2.0) * (1.0 - d_ratio)

    return {
        "shaft_hz": round(f_s, 3),
        "bpfo_hz": round(bpfo, 3),
        "bpfi_hz": round(bpfi, 3),
        "bsf_hz": round(bsf, 3),
        "ftf_hz": round(ftf, 3),
    }


# =============================================================================
# ZONE CLASSIFICATION
# =============================================================================


def _classify_zone(value: float, zone_ab: float, zone_bc: float, zone_cd: float) -> str:
    if value <= zone_ab:
        return "A"
    if value <= zone_bc:
        return "B"
    if value <= zone_cd:
        return "C"
    return "D"


def _convert_to_velocity_rms(
    value: float, quantity: str, operating_rpm: float
) -> tuple[float, str]:
    """
    Convert measurement to approximate velocity RMS for zone comparison.
    Returns (converted_value, note).
    Conversions are approximate — ISO 20816-3 is defined in velocity RMS.
    """
    if quantity == "velocity_rms":
        return value, ""

    note = ""
    if quantity == "displacement_pp":
        # v_rms ≈ (π × f × D_pp) / √2, where f = n/60
        f_hz = operating_rpm / 60.0
        if f_hz > 0:
            v_rms = (math.pi * f_hz * value * 1e-3) / math.sqrt(2)  # µm → mm/s
            note = f"Converted from displacement peak-peak using f = {f_hz:.1f} Hz (approximate)."
            return round(v_rms, 4), note
        return value, "Cannot convert displacement — operating RPM is zero."

    if quantity == "accel_rms":
        # v_rms ≈ a_rms / (2π × f), a in m/s², result in mm/s
        f_hz = operating_rpm / 60.0
        if f_hz > 0:
            v_rms = (value / (2 * math.pi * f_hz)) * 1000.0  # m/s² → mm/s
            note = f"Converted from acceleration RMS using f = {f_hz:.1f} Hz (approximate — broadband conversion)."
            return round(v_rms, 4), note
        return value, "Cannot convert acceleration — operating RPM is zero."

    return value, ""


# =============================================================================
# FAULT SCORING
# =============================================================================


def _score_fault(
    fault: dict[str, Any],
    machine_type: str,
    bearing_type_de: str,
    measurement_direction: str,
    measurement_quantity: str,
    measured_value: float,
    zone: str,
    nominal_power_kw: float,
) -> int:
    """Return a 0–100 score for how well a fault signature matches the inputs."""
    score = 0

    # 1. Machine type applicability (15 pts)
    machine_list = fault["machine_types"]
    if "all" in machine_list or machine_type in machine_list:
        score += 15

    # 2. Bearing type applicability (20 pts)
    bearing_types = fault["bearing_types"]
    if "unknown" in bearing_types or bearing_type_de in bearing_types:
        score += 20
    else:
        # Hard exclusion for bearing-specific faults
        return 0

    # 3. Direction score (35 pts)
    dir_scores = fault["direction_scores"]
    dir_weight = dir_scores.get(measurement_direction, 0.5)
    score += int(dir_weight * 35)

    # 4. Zone severity (10 pts) — high vibration makes faults more likely
    zone_weights = {"A": 3, "B": 6, "C": 9, "D": 10}
    score += zone_weights.get(zone, 5)

    # 5. Measurement quantity context (10 pts)
    # Bearing defects are best detected in acceleration; others in velocity
    if fault["id"] == "bearing_defect":
        if measurement_quantity == "accel_rms":
            score += 10
        elif measurement_quantity == "velocity_rms":
            score += 5
        else:
            score += 3
    else:
        if measurement_quantity == "velocity_rms":
            score += 10
        else:
            score += 6

    # 6. Power/size context (10 pts)
    # All faults equally applicable across sizes
    score += 8

    return min(score, 100)


def _confidence_label(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 50:
        return "Medium"
    if score >= 35:
        return "Low"
    return "Possible"


def _build_matched_indicators(
    fault: dict[str, Any],
    measurement_direction: str,
    bearing_type_de: str,
    zone: str,
) -> list[str]:
    indicators = []

    dir_labels = {"radial_h": "radial horizontal", "radial_v": "radial vertical", "axial": "axial"}
    dir_score = fault["direction_scores"].get(measurement_direction, 0)
    if dir_score >= 0.8:
        indicators.append(
            f"Measurement direction ({dir_labels.get(measurement_direction, measurement_direction)}) "
            f"is consistent with this fault pattern."
        )
    elif dir_score >= 0.5:
        indicators.append(
            f"Measurement direction is partially consistent (this fault can appear in multiple directions)."
        )

    if zone in ("C", "D"):
        indicators.append("Elevated vibration level is consistent with an active fault condition.")

    if fault["id"] == "bearing_defect" and bearing_type_de == "rolling_element":
        indicators.append("Rolling element bearing type confirmed — bearing defect frequencies apply.")

    if not indicators:
        indicators.append("General plausibility based on machine type and measurement context.")

    return indicators


def _build_contra_indicators(
    fault: dict[str, Any],
    measurement_direction: str,
    bearing_type_de: str,
) -> list[str]:
    contras = []

    dir_score = fault["direction_scores"].get(measurement_direction, 0.5)
    if dir_score < 0.4:
        dir_labels = {"radial_h": "radial horizontal", "radial_v": "radial vertical", "axial": "axial"}
        expected = [k for k, v in fault["direction_scores"].items() if v >= 0.8]
        expected_str = " / ".join([dir_labels.get(d, d) for d in expected])
        contras.append(
            f"Measurement direction ({dir_labels.get(measurement_direction, measurement_direction)}) "
            f"is not typical for this fault — expected: {expected_str}."
        )

    if fault["id"] == "bearing_defect" and bearing_type_de == "fluid_film":
        contras.append("Fluid film (journal) bearings — classic rolling element defect frequencies (BPFO etc.) do not apply.")

    if fault["id"] == "misalignment_angular" and measurement_direction in ("radial_h", "radial_v"):
        contras.append(
            "Angular misalignment is primarily detected in the axial direction. "
            "A radial-only measurement may miss the strongest indicator."
        )

    return contras


# =============================================================================
# MAIN EVALUATION FUNCTION
# =============================================================================


def evaluate_vibration(
    machine_type: str,
    nominal_power_kw: float,
    rated_rpm: float,
    operating_rpm: float,
    bearing_type_de: str,
    mounting: str,
    measurement_direction: str,
    vibration_quantity: str,
    measured_value: float,
    machine_group: str,
    zone_ab: float,
    zone_bc: float,
    zone_cd: float,
    baseline_value: float = 0.0,
    previous_value: float = 0.0,
    bearing_roller_count: float = 0.0,
    bearing_pitch_dia_mm: float = 0.0,
    bearing_roller_dia_mm: float = 0.0,
    bearing_contact_angle_deg: float = 0.0,
) -> dict[str, Any]:
    """
    Evaluate vibration severity per ISO 20816-3 and triage probable fault causes per VDI 3839.

    Combines ISO 20816 zone classification with VDI 3839 fault signature pattern matching
    to give engineers both a severity verdict and a ranked list of probable fault types
    from a single measurement.

    ---Parameters---
    machine_type : str
        Machine category key (e.g., 'pump', 'motor_medium'). Drives ISO part selection.
    nominal_power_kw : float
        Rated power of the machine (kW). Must be > 0.
    rated_rpm : float
        Rated shaft speed (RPM). Used for reference; 120–15000 RPM typical scope.
    operating_rpm : float
        Actual shaft speed during measurement (RPM). Used for unit conversions and fault frequencies.
    bearing_type_de : str
        Drive-end bearing type: 'rolling_element', 'fluid_film', or 'unknown'.
    mounting : str
        Machine mounting/foundation: 'rigid', 'flexible', 'skid', or 'unknown'.
    measurement_direction : str
        Direction of vibration measurement: 'radial_h', 'radial_v', or 'axial'.
    vibration_quantity : str
        Measurement quantity: 'velocity_rms' (mm/s), 'displacement_pp' (µm), or 'accel_rms' (m/s²).
    measured_value : float
        Measured vibration amplitude in units matching vibration_quantity.
    machine_group : str
        ISO 20816-3 machine group: '1', '2', or '3'. User-selected from standard.
    zone_ab : float
        Zone A/B boundary (mm/s RMS). Entered by user from their copy of ISO 20816-3.
    zone_bc : float
        Zone B/C boundary (mm/s RMS). Entered by user from their copy of ISO 20816-3.
    zone_cd : float
        Zone C/D boundary (mm/s RMS). Entered by user from their copy of ISO 20816-3.
    baseline_value : float
        Previous known-good measurement in same quantity/location (0 = not provided).
    previous_value : float
        Most recent prior measurement for trend assessment (0 = not provided).
    bearing_roller_count : float
        Number of rolling elements (0 = not provided).
    bearing_pitch_dia_mm : float
        Bearing pitch circle diameter in mm (0 = not provided).
    bearing_roller_dia_mm : float
        Rolling element diameter in mm (0 = not provided).
    bearing_contact_angle_deg : float
        Bearing contact angle in degrees (0 = not provided, default ~0 for radial bearings).

    ---Returns---
    applicable_standard : str
        ISO standard and part applicable to this machine.
    machine_group_description : str
        Description of the selected machine group per ISO 20816-3.
    scope_warnings_json : str
        JSON array of scope warning strings (empty array if none).
    value_for_comparison : float
        Measured value converted to velocity RMS (mm/s) for zone comparison.
    conversion_note : str
        Explanation of unit conversion applied (empty string if velocity was input directly).
    zone : str
        ISO 20816-3 zone: A, B, C, or D.
    zone_label : str
        Zone label with plain-language description.
    zone_detail : str
        Detailed explanation of what the zone means.
    zone_action : str
        Recommended action for this zone.
    zone_css_class : str
        CSS class for zone colour coding: success, warning, or danger.
    delta_baseline_abs : float
        Absolute change from baseline (0 if no baseline provided).
    delta_baseline_pct : float
        Percentage change from baseline (0 if no baseline provided).
    delta_previous_abs : float
        Absolute change from previous measurement (0 if not provided).
    delta_previous_pct : float
        Percentage change from previous measurement (0 if not provided).
    trend : str
        Trend indicator: stable, increasing, decreasing, or insufficient_data.
    fault_matches_json : str
        JSON array of ranked fault match objects (see structure in tool README).
    bearing_freqs_json : str
        JSON object of calculated bearing defect frequencies, or empty string if geometry not provided.
    next_steps_json : str
        JSON array of prioritised next-step strings.
    report_text : str
        Plain-text evaluation report for printing or export.

    ---LaTeX---
    v_{compare} \\approx \\frac{\\pi \\cdot f \\cdot D_{pp}}{\\sqrt{2}} \\quad (\\text{displacement conversion})
    v_{compare} \\approx \\frac{a_{rms}}{2 \\pi f} \\quad (\\text{acceleration conversion})
    """
    # --- Input validation ---
    if nominal_power_kw <= 0:
        raise ValueError("nominal_power_kw must be positive.")
    if rated_rpm <= 0 or operating_rpm <= 0:
        raise ValueError("RPM values must be positive.")
    if measured_value <= 0:
        raise ValueError("measured_value must be positive.")
    if zone_ab <= 0 or zone_bc <= zone_ab or zone_cd <= zone_bc:
        raise ValueError("Zone limits must be positive and in ascending order (A/B < B/C < C/D).")

    valid_machine_types = set(MACHINE_GROUPS.keys())
    if machine_type not in valid_machine_types:
        raise ValueError(f"Unknown machine_type '{machine_type}'. Valid: {sorted(valid_machine_types)}")

    valid_bearings = {"rolling_element", "fluid_film", "unknown"}
    if bearing_type_de not in valid_bearings:
        raise ValueError(f"bearing_type_de must be one of {sorted(valid_bearings)}")

    valid_directions = {"radial_h", "radial_v", "axial"}
    if measurement_direction not in valid_directions:
        raise ValueError(f"measurement_direction must be one of {sorted(valid_directions)}")

    valid_quantities = {"velocity_rms", "displacement_pp", "accel_rms"}
    if vibration_quantity not in valid_quantities:
        raise ValueError(f"vibration_quantity must be one of {sorted(valid_quantities)}")

    # --- Machine info ---
    machine_info = MACHINE_GROUPS.get(machine_type, MACHINE_GROUPS["general"])
    applicable_standard = machine_info["iso_part"]
    machine_group_description = f"Group {machine_group}: {machine_info['group_description']}"

    scope_warnings: list[str] = []
    if machine_info["scope_note"]:
        scope_warnings.append(machine_info["scope_note"])
    if nominal_power_kw < 15:
        scope_warnings.append(
            f"Nominal power {nominal_power_kw} kW is below 15 kW threshold for ISO 20816-3. "
            "Consult manufacturer limits or ISO 20816-7 for smaller pumps."
        )
    if rated_rpm < 120 or rated_rpm > 15000:
        scope_warnings.append(
            f"Rated speed {rated_rpm} RPM is outside the ISO 20816-3 scope of 120–15,000 RPM."
        )

    # --- Unit conversion ---
    value_for_comparison, conversion_note = _convert_to_velocity_rms(
        measured_value, vibration_quantity, operating_rpm
    )

    # --- Zone classification ---
    zone = _classify_zone(value_for_comparison, zone_ab, zone_bc, zone_cd)
    zone_info = ZONE_DESCRIPTIONS[zone]

    # --- Delta / trend ---
    delta_baseline_abs = 0.0
    delta_baseline_pct = 0.0
    if baseline_value > 0:
        delta_baseline_abs = round(value_for_comparison - baseline_value, 4)
        delta_baseline_pct = round((delta_baseline_abs / baseline_value) * 100, 1)
        if abs(delta_baseline_pct) > 25:
            scope_warnings.append(
                f"Vibration has changed {delta_baseline_pct:+.1f}% from baseline — "
                "significant change; investigate cause even if still within zone."
            )

    delta_previous_abs = 0.0
    delta_previous_pct = 0.0
    trend = "insufficient_data"
    if previous_value > 0:
        delta_previous_abs = round(value_for_comparison - previous_value, 4)
        delta_previous_pct = round((delta_previous_abs / previous_value) * 100, 1)
        if delta_previous_pct > 5:
            trend = "increasing"
        elif delta_previous_pct < -5:
            trend = "decreasing"
        else:
            trend = "stable"

    # --- Fault scoring ---
    fault_matches = []
    for fault in FAULT_SIGNATURES:
        score = _score_fault(
            fault,
            machine_type,
            bearing_type_de,
            measurement_direction,
            vibration_quantity,
            value_for_comparison,
            zone,
            nominal_power_kw,
        )
        if score >= 30:
            matched = _build_matched_indicators(fault, measurement_direction, bearing_type_de, zone)
            contras = _build_contra_indicators(fault, measurement_direction, bearing_type_de)
            fault_matches.append(
                {
                    "fault_id": fault["id"],
                    "display_name": fault["display_name"],
                    "vdi_reference": fault["vdi_reference"],
                    "short_description": fault["short_description"],
                    "primary_freq": fault["primary_freq"],
                    "direction_pattern": fault["direction_pattern"],
                    "speed_dependency": fault["speed_dependency"],
                    "score": score,
                    "confidence": _confidence_label(score),
                    "matched_indicators": matched,
                    "contra_indicators": contras,
                    "follow_up": fault["follow_up"],
                }
            )

    fault_matches.sort(key=lambda x: x["score"], reverse=True)
    for i, fm in enumerate(fault_matches):
        fm["rank"] = i + 1

    # --- Bearing defect frequencies ---
    bearing_freqs: dict[str, float] = {}
    if (
        bearing_type_de == "rolling_element"
        and bearing_roller_count > 0
        and bearing_pitch_dia_mm > 0
        and bearing_roller_dia_mm > 0
    ):
        try:
            bearing_freqs = calculate_bearing_defect_frequencies(
                operating_rpm,
                int(bearing_roller_count),
                bearing_pitch_dia_mm,
                bearing_roller_dia_mm,
                bearing_contact_angle_deg if bearing_contact_angle_deg > 0 else 0.0,
            )
        except ValueError:
            pass

    # --- Next steps ---
    next_steps: list[str] = []
    if zone == "D":
        next_steps.append("URGENT: Consider immediate shutdown and inspection — Zone D indicates damage risk.")
    elif zone == "C":
        next_steps.append("Increase monitoring frequency — Zone C indicates unsatisfactory condition.")
        next_steps.append("Investigate probable fault causes listed in the Fault Triage tab.")
        next_steps.append("Plan corrective maintenance — do not allow continued operation without a root-cause investigation.")
    elif zone == "B":
        next_steps.append("Machine is operating within acceptable limits. Continue scheduled monitoring.")

    if trend == "increasing":
        next_steps.append(
            f"Trend is INCREASING (+{delta_previous_pct:.1f}% since last measurement). "
            "Shorten monitoring interval and investigate."
        )
    elif trend == "decreasing":
        next_steps.append(
            f"Trend is decreasing ({delta_previous_pct:.1f}% since last measurement). "
            "Confirm improvement with next scheduled measurement."
        )

    if fault_matches:
        top = fault_matches[0]
        next_steps.append(
            f"Top probable fault: {top['display_name']} ({top['vdi_reference']}, "
            f"{top['confidence']} confidence). "
            "See Fault Triage tab for follow-up measurement actions."
        )

    if not bearing_freqs and bearing_type_de == "rolling_element":
        next_steps.append(
            "Bearing defect frequencies not calculated — enter bearing geometry in Expert Mode "
            "to enable BPFO/BPFI/BSF/FTF calculation."
        )

    next_steps.append(
        "Measure in all three directions (radial-H, radial-V, axial) to improve fault differentiation."
    )

    # --- Report text ---
    direction_labels = {"radial_h": "Radial Horizontal", "radial_v": "Radial Vertical", "axial": "Axial"}
    quantity_labels = {
        "velocity_rms": "Velocity RMS (mm/s)",
        "displacement_pp": "Displacement peak-peak (µm)",
        "accel_rms": "Acceleration RMS (m/s²)",
    }
    report_lines = [
        "VIBRATION EVALUATION REPORT",
        "=" * 50,
        f"Machine Type      : {machine_info['display']}",
        f"Nominal Power     : {nominal_power_kw} kW",
        f"Rated Speed       : {rated_rpm} RPM",
        f"Operating Speed   : {operating_rpm} RPM",
        f"Bearing Type (DE) : {bearing_type_de.replace('_', ' ').title()}",
        f"Standard Applied  : {applicable_standard}",
        f"Machine Group     : {machine_group_description}",
        "",
        "MEASUREMENT",
        "-" * 30,
        f"Direction         : {direction_labels.get(measurement_direction, measurement_direction)}",
        f"Quantity          : {quantity_labels.get(vibration_quantity, vibration_quantity)}",
        f"Measured Value    : {measured_value} ({vibration_quantity})",
        f"Comparison Value  : {value_for_comparison:.3f} mm/s RMS",
    ]
    if conversion_note:
        report_lines.append(f"Conversion Note   : {conversion_note}")
    report_lines += [
        "",
        "ZONE CLASSIFICATION",
        "-" * 30,
        f"Zone Limits Used  : A/B={zone_ab} | B/C={zone_bc} | C/D={zone_cd} mm/s RMS",
        f"Zone Result       : {zone_info['label']}",
        f"Action            : {zone_info['action']}",
    ]
    if baseline_value > 0:
        report_lines.append(f"Delta vs Baseline : {delta_baseline_abs:+.3f} mm/s ({delta_baseline_pct:+.1f}%)")
    if previous_value > 0:
        report_lines.append(f"Trend             : {trend.replace('_', ' ').title()} ({delta_previous_pct:+.1f}% vs previous)")
    if scope_warnings:
        report_lines += ["", "SCOPE WARNINGS", "-" * 30]
        for w in scope_warnings:
            report_lines.append(f"• {w}")
    report_lines += ["", "TOP FAULT CANDIDATES (VDI 3839)", "-" * 30]
    for fm in fault_matches[:3]:
        report_lines.append(f"{fm['rank']}. {fm['display_name']} ({fm['vdi_reference']}) — {fm['confidence']} confidence")
    report_lines += [
        "",
        "NEXT STEPS",
        "-" * 30,
    ]
    for step in next_steps:
        report_lines.append(f"• {step}")
    report_lines += [
        "",
        "DISCLAIMER",
        "-" * 30,
        "This evaluation is based on user-supplied data and general pattern rules from VDI 3839.",
        "Refer to ISO 20816 for authoritative zone limits. Results do not replace qualified",
        "vibration analysis by a certified practitioner.",
    ]

    return {
        "applicable_standard": applicable_standard,
        "machine_group_description": machine_group_description,
        "scope_warnings_json": json.dumps(scope_warnings),
        "value_for_comparison": value_for_comparison,
        "conversion_note": conversion_note,
        "zone": zone,
        "zone_label": zone_info["label"],
        "zone_detail": zone_info["detail"],
        "zone_action": zone_info["action"],
        "zone_css_class": zone_info["css_class"],
        "delta_baseline_abs": delta_baseline_abs,
        "delta_baseline_pct": delta_baseline_pct,
        "delta_previous_abs": delta_previous_abs,
        "delta_previous_pct": delta_previous_pct,
        "trend": trend,
        "fault_matches_json": json.dumps(fault_matches),
        "bearing_freqs_json": json.dumps(bearing_freqs) if bearing_freqs else "",
        "next_steps_json": json.dumps(next_steps),
        "report_text": "\n".join(report_lines),
    }
