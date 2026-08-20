"""
Power screw (jack screw and lead screw) design and analysis.

Covers the sliding-contact screw jack: the torque to raise and lower a load,
mechanical efficiency, whether the screw holds its load when the input torque
is removed, thread and body stresses, column buckling, shaft whirl, and a
side-by-side comparison against a ball screw of the same size.

Sign and unit conventions used throughout this module:

* Lengths are millimetres, forces newtons, torques newton-metres, stresses
  megapascals, speeds rpm.
* "Raise" means driving the load against gravity (screw tightening under load).
  "Lower" means the load-assisted direction.
* A positive lowering torque means torque must be applied to lower the load,
  which is the self-locking case. A negative lowering torque is the holding
  torque a brake has to supply, and the screw back-drives without it.

References
----------
Shigley, *Mechanical Engineering Design*, 10th ed., Section 8-2 "Power Screws"
and 8-3 "Thread Stresses". Oberg et al., *Machinery's Handbook*, 30th ed.,
"Power Transmission Screws" and "Acme Threads". ISO 2904 for metric
trapezoidal thread basic dimensions.
"""

from __future__ import annotations

import math

# --- Thread form data -------------------------------------------------------
#
# half_angle_deg is the thread half angle measured in the axial plane. The
# raising- and lowering-torque expressions carry a sec(alpha) term that
# increases the friction contribution because the normal force on an angled
# flank exceeds the axial load.
#
# depth_factor multiplies the pitch to give the engaged flank height used for
# bearing pressure. pitch_offset_factor multiplies the pitch to give how far
# the pitch diameter sits below the major diameter. The two are equal for the
# power-screw forms, where the pitch line falls halfway down a 0.5p thread, but
# they part company on 60 degree V threads: the flanks overlap by 0.5413p while
# the pitch diameter sits 0.6495p down.
#
# motion_class separates threads cut for moving loads from fastener threads
# pressed into service as jack screws, which works but carries warnings.
#
# clearance_factor multiplies the pitch to give the radial clearance cut below
# the basic minor diameter. Real standards specify this as a fixed length, not
# a fraction of pitch (0.5 mm per flank in ISO 2904 for pitches of 3 to 12 mm,
# 0.010 inch in ASME B1.5), so the proportional factor here is an
# approximation for custom threads. It runs about 0.1 mm high on fine pitches.
# Use the SCREW_PRESETS table, or pass a measured minor diameter, whenever the
# screw is a standard size.
#
# shear_width_screw and shear_width_nut multiply the pitch to give the width of
# the thread base in shear. Square threads shear across half a pitch; the
# angled forms have a wider base on the screw than in the nut.

THREAD_FORMS = {
    "square": {
        "label": "Square",
        "half_angle_deg": 0.0,
        "depth_factor": 0.5,
        "pitch_offset_factor": 0.5,
        "motion_class": "power",
        "clearance_factor": 0.0,
        "shear_width_screw": 0.50,
        "shear_width_nut": 0.50,
        "note": (
            "Highest efficiency of the sliding forms and no radial bursting "
            "load on the nut. Hard to cut, cannot be adjusted for wear, and "
            "the flat root is the weakest in bending."
        ),
    },
    "acme": {
        "label": "Acme (29 deg included)",
        "half_angle_deg": 14.5,
        "depth_factor": 0.5,
        "pitch_offset_factor": 0.5,
        "motion_class": "power",
        "clearance_factor": 0.05,
        "shear_width_screw": 0.77,
        "shear_width_nut": 0.63,
        "note": (
            "The default for jack screws in inch-based practice. Slightly "
            "less efficient than square, but easier to machine and the "
            "tapered flank allows a split nut to take up wear."
        ),
    },
    "stub_acme": {
        "label": "Stub Acme (29 deg, shallow)",
        "half_angle_deg": 14.5,
        "depth_factor": 0.3,
        "pitch_offset_factor": 0.3,
        "motion_class": "power",
        "clearance_factor": 0.05,
        "shear_width_screw": 0.77,
        "shear_width_nut": 0.63,
        "note": (
            "Acme flanks on a 0.3p thread depth. The larger minor diameter "
            "buys column strength at the cost of bearing area, so it suits "
            "long slender jacks."
        ),
    },
    "trapezoidal": {
        "label": "Metric trapezoidal Tr (30 deg included)",
        "half_angle_deg": 15.0,
        "depth_factor": 0.5,
        "pitch_offset_factor": 0.5,
        "motion_class": "power",
        "clearance_factor": 0.05,
        "shear_width_screw": 0.77,
        "shear_width_nut": 0.63,
        "note": (
            "The ISO 2904 metric equivalent of Acme. One degree more flank "
            "angle, so marginally more friction for the same coefficient."
        ),
    },
    "buttress": {
        "label": "Buttress (7 deg load flank)",
        "half_angle_deg": 7.0,
        "depth_factor": 0.5,
        "pitch_offset_factor": 0.5,
        "motion_class": "power",
        "clearance_factor": 0.05,
        "shear_width_screw": 0.60,
        "shear_width_nut": 0.60,
        "note": (
            "Carries load on a near-perpendicular 7 degree flank, so it "
            "approaches square-thread efficiency with a strong root. Only "
            "valid in one load direction: the 45 degree back flank is for "
            "return loads, not the working load."
        ),
    },
    # --- Fastener threads pressed into service as jack screws ---------------
    #
    # Both are the ISO 60 degree fundamental triangle, so they share every
    # proportion. From H = 0.866025p:
    #   pitch diameter  d2 = d - 0.649519p
    #   minor diameter  d3 = d - 1.226869p   (external thread)
    #   flank overlap   H1 = 0.541266p       (5H/8)
    # The clearance factor below is what is left over once the flank overlap is
    # taken off the minor diameter: (1.226869 - 2 x 0.541266) / 2 = 0.072169.
    #
    # Thread base widths come from the ASME B1.1 shear area formulas, which
    # reduce to 0.75p at the screw root and 0.875p at the nut root for the
    # basic profile.
    "metric_coarse": {
        "label": "Metric coarse M (60 deg, threaded rod)",
        "half_angle_deg": 30.0,
        "depth_factor": 0.541266,
        "pitch_offset_factor": 0.649519,
        "motion_class": "fastener",
        "clearance_factor": 0.072169,
        "shear_width_screw": 0.75,
        "shear_width_nut": 0.875,
        "note": (
            "Ordinary threaded rod and bolts. Cheap, available everywhere, and "
            "strongly self-locking because the lead is short and the 30 degree "
            "flank multiplies friction. That same flank angle is why it is "
            "inefficient and wears faster than Acme under repeated motion."
        ),
    },
    "unified": {
        "label": "Unified inch UNC/UNF (60 deg, threaded rod)",
        "half_angle_deg": 30.0,
        "depth_factor": 0.541266,
        "pitch_offset_factor": 0.649519,
        "motion_class": "fastener",
        "clearance_factor": 0.072169,
        "shear_width_screw": 0.75,
        "shear_width_nut": 0.875,
        "note": (
            "The inch equivalent of metric coarse, and dimensionally identical "
            "once the pitch is converted. Same trade: available and self-locking, "
            "but not a motion thread."
        ),
    },
}

# --- End fixity -------------------------------------------------------------
#
# k_buckling is the effective-length factor for Euler/Johnson column buckling.
# beta_l_squared is (beta*L)^2 for the first bending mode, used for whirl.
# Recommended (conservative) buckling factors are used rather than the
# theoretical ones, following AISC practice.

END_FIXITIES = {
    "fixed_free": {
        "label": "Fixed one end, free the other",
        "k_buckling": 2.1,
        "k_buckling_theoretical": 2.0,
        "beta_l_squared": 3.5160,
        "note": "A jack screw standing on its base with an unguided load pad.",
    },
    "pinned_pinned": {
        "label": "Pinned both ends",
        "k_buckling": 1.0,
        "k_buckling_theoretical": 1.0,
        "beta_l_squared": 9.8696,
        "note": "Simple bearings at both ends that carry no moment.",
    },
    "fixed_pinned": {
        "label": "Fixed one end, pinned the other",
        "k_buckling": 0.8,
        "k_buckling_theoretical": 0.7071,
        "beta_l_squared": 15.4182,
        "note": "A clamped bearing at the drive end, a simple support opposite.",
    },
    "fixed_fixed": {
        "label": "Fixed both ends",
        "k_buckling": 0.65,
        "k_buckling_theoretical": 0.5,
        "beta_l_squared": 22.3733,
        "note": "Both ends in moment-carrying bearings. Rare on a jack screw.",
    },
}

# --- Friction pairs ---------------------------------------------------------
#
# Sliding friction is the dominant uncertainty in a power screw. These are
# starting (static) values for the thread flank under load, machine-oiled
# unless stated. Ranges are wide in the literature; the low/high pair here is
# meant to be swept, not treated as a single answer.

FRICTION_PAIRS = {
    "steel_bronze_oiled": {
        "label": "Steel screw / bronze nut, oiled",
        "thread": 0.10,
        "thread_low": 0.08,
        "thread_high": 0.14,
        "collar": 0.09,
    },
    "steel_bronze_dry": {
        "label": "Steel screw / bronze nut, dry",
        "thread": 0.17,
        "thread_low": 0.15,
        "thread_high": 0.20,
        "collar": 0.16,
    },
    "steel_cast_iron_oiled": {
        "label": "Steel screw / cast iron nut, oiled",
        "thread": 0.12,
        "thread_low": 0.10,
        "thread_high": 0.16,
        "collar": 0.11,
    },
    "steel_steel_oiled": {
        "label": "Steel screw / steel nut, oiled",
        "thread": 0.13,
        "thread_low": 0.11,
        "thread_high": 0.17,
        "collar": 0.12,
    },
    "steel_steel_dry": {
        "label": "Steel screw / steel nut, dry",
        "thread": 0.20,
        "thread_low": 0.15,
        "thread_high": 0.25,
        "collar": 0.18,
    },
    "steel_plastic": {
        "label": "Steel screw / acetal or PTFE-filled nut",
        "thread": 0.12,
        "thread_low": 0.08,
        "thread_high": 0.18,
        "collar": 0.12,
    },
}

# --- Nut materials ----------------------------------------------------------
#
# allowable_bearing_mpa follows the safe bearing pressures in Shigley
# Table 8-4 / Machinery's Handbook for the stated rubbing speed band. These
# are wear limits, not strength limits: exceeding them does not break the nut,
# it wears it out. pv_limit_mpa_m_s is the pressure-velocity product above
# which the nut overheats.

NUT_MATERIALS = {
    "bronze": {
        "label": "Bronze (SAE 65 / C90500), low speed",
        "allowable_bearing_mpa": 17.0,
        "pv_limit_mpa_m_s": 1.75,
        "speed_note": "Up to 0.05 m/s rubbing speed.",
    },
    "bronze_medium": {
        "label": "Bronze, medium speed",
        "allowable_bearing_mpa": 11.0,
        "pv_limit_mpa_m_s": 1.75,
        "speed_note": "0.05 to 0.20 m/s rubbing speed.",
    },
    "cast_iron": {
        "label": "Cast iron",
        "allowable_bearing_mpa": 13.0,
        "pv_limit_mpa_m_s": 1.40,
        "speed_note": "Up to 0.04 m/s rubbing speed.",
    },
    "steel": {
        "label": "Steel nut on steel screw",
        "allowable_bearing_mpa": 17.0,
        "pv_limit_mpa_m_s": 1.05,
        "speed_note": "Low speed, intermittent duty only.",
    },
    "acetal": {
        "label": "Acetal / filled thermoplastic",
        "allowable_bearing_mpa": 7.0,
        "pv_limit_mpa_m_s": 0.14,
        "speed_note": "Continuous running; creeps under sustained load.",
    },
    "steel_hex_nut": {
        "label": "Standard steel hex nut (class 8)",
        "allowable_bearing_mpa": 17.0,
        "pv_limit_mpa_m_s": 1.05,
        "speed_note": "Low speed, intermittent duty. Steel on steel galls without grease.",
    },
}

# --- Screw materials --------------------------------------------------------

SCREW_MATERIALS = {
    "steel_1045": {
        "label": "1045 carbon steel, cold drawn",
        "modulus_gpa": 205.0,
        "yield_mpa": 530.0,
        "density_kg_m3": 7850.0,
    },
    "steel_1018": {
        "label": "1018 mild steel, cold drawn",
        "modulus_gpa": 205.0,
        "yield_mpa": 370.0,
        "density_kg_m3": 7870.0,
    },
    "steel_4140_qt": {
        "label": "4140 alloy steel, quenched and tempered",
        "modulus_gpa": 205.0,
        "yield_mpa": 1100.0,
        "density_kg_m3": 7850.0,
    },
    "stainless_304": {
        "label": "304 stainless, annealed",
        "modulus_gpa": 193.0,
        "yield_mpa": 215.0,
        "density_kg_m3": 8000.0,
    },
    "stainless_316": {
        "label": "316 stainless, annealed",
        "modulus_gpa": 193.0,
        "yield_mpa": 205.0,
        "density_kg_m3": 8000.0,
    },
    # Fastener grades, for jacks built from threaded rod. Property class n.m
    # means tensile 100n MPa and yield m/10 of that, so 4.6 is 400/240 and
    # 8.8 is 800/640. Plain rod from a hardware shelf is usually 4.6 or the
    # equivalent A307 Grade A, which is far softer than a purpose-made screw.
    "rod_class_4_6": {
        "label": "Threaded rod, low carbon (class 4.6 / A307A)",
        "modulus_gpa": 205.0,
        "yield_mpa": 240.0,
        "density_kg_m3": 7850.0,
    },
    "rod_class_8_8": {
        "label": "Threaded rod or bolt, class 8.8 (SAE grade 5)",
        "modulus_gpa": 205.0,
        "yield_mpa": 640.0,
        "density_kg_m3": 7850.0,
    },
    "rod_class_10_9": {
        "label": "Threaded rod or bolt, class 10.9 (SAE grade 8)",
        "modulus_gpa": 205.0,
        "yield_mpa": 940.0,
        "density_kg_m3": 7850.0,
    },
    "rod_stainless_a2_70": {
        "label": "Stainless threaded rod, A2-70 (304)",
        "modulus_gpa": 193.0,
        "yield_mpa": 450.0,
        "density_kg_m3": 8000.0,
    },
}

# --- Preset screw sizes -----------------------------------------------------
#
# Inch Acme sizes are the General Purpose (2G) series from ASME B1.5, with
# diameters converted to millimetres. Metric Tr sizes are ISO 2904 coarse.
# Minor diameters are the basic external-thread values, which is what carries
# the column and body stress.

SCREW_PRESETS = [
    {"key": "tr12x3", "group": "Trapezoidal (ISO 2904)", "label": "Tr12x3", "form": "trapezoidal",
     "nominal_diameter_mm": 12.0, "pitch_mm": 3.0, "minor_diameter_mm": 8.0},
    {"key": "tr16x4", "group": "Trapezoidal (ISO 2904)", "label": "Tr16x4", "form": "trapezoidal",
     "nominal_diameter_mm": 16.0, "pitch_mm": 4.0, "minor_diameter_mm": 11.0},
    {"key": "tr20x4", "group": "Trapezoidal (ISO 2904)", "label": "Tr20x4", "form": "trapezoidal",
     "nominal_diameter_mm": 20.0, "pitch_mm": 4.0, "minor_diameter_mm": 15.0},
    {"key": "tr24x5", "group": "Trapezoidal (ISO 2904)", "label": "Tr24x5", "form": "trapezoidal",
     "nominal_diameter_mm": 24.0, "pitch_mm": 5.0, "minor_diameter_mm": 18.0},
    {"key": "tr30x6", "group": "Trapezoidal (ISO 2904)", "label": "Tr30x6", "form": "trapezoidal",
     "nominal_diameter_mm": 30.0, "pitch_mm": 6.0, "minor_diameter_mm": 23.0},
    {"key": "tr40x7", "group": "Trapezoidal (ISO 2904)", "label": "Tr40x7", "form": "trapezoidal",
     "nominal_diameter_mm": 40.0, "pitch_mm": 7.0, "minor_diameter_mm": 32.0},
    {"key": "tr50x8", "group": "Trapezoidal (ISO 2904)", "label": "Tr50x8", "form": "trapezoidal",
     "nominal_diameter_mm": 50.0, "pitch_mm": 8.0, "minor_diameter_mm": 41.0},
    {"key": "acme_0500_10", "group": "Acme (ASME B1.5)", "label": '1/2-10 Acme', "form": "acme",
     "nominal_diameter_mm": 12.700, "pitch_mm": 2.540, "minor_diameter_mm": 9.652},
    {"key": "acme_0625_8", "group": "Acme (ASME B1.5)", "label": '5/8-8 Acme', "form": "acme",
     "nominal_diameter_mm": 15.875, "pitch_mm": 3.175, "minor_diameter_mm": 12.192},
    {"key": "acme_0750_6", "group": "Acme (ASME B1.5)", "label": '3/4-6 Acme', "form": "acme",
     "nominal_diameter_mm": 19.050, "pitch_mm": 4.233, "minor_diameter_mm": 14.309},
    {"key": "acme_1000_5", "group": "Acme (ASME B1.5)", "label": '1-5 Acme', "form": "acme",
     "nominal_diameter_mm": 25.400, "pitch_mm": 5.080, "minor_diameter_mm": 19.812},
    {"key": "acme_1250_5", "group": "Acme (ASME B1.5)", "label": '1 1/4-5 Acme', "form": "acme",
     "nominal_diameter_mm": 31.750, "pitch_mm": 5.080, "minor_diameter_mm": 26.162},
    {"key": "acme_1500_4", "group": "Acme (ASME B1.5)", "label": '1 1/2-4 Acme', "form": "acme",
     "nominal_diameter_mm": 38.100, "pitch_mm": 6.350, "minor_diameter_mm": 31.242},
    {"key": "acme_2000_4", "group": "Acme (ASME B1.5)", "label": '2-4 Acme', "form": "acme",
     "nominal_diameter_mm": 50.800, "pitch_mm": 6.350, "minor_diameter_mm": 43.942},

    # Fastener threads, for jacks built from off-the-shelf rod and nuts.
    # d2 and d3 are the ISO/Unified 60 degree basic dimensions; nut_height_mm
    # is the standard hex nut thickness for that size.
    {"key": "m8", "group": "Metric coarse threaded rod", "label": "M8 x 1.25", "form": "metric_coarse",
     "nominal_diameter_mm": 8.0, "pitch_mm": 1.25, "minor_diameter_mm": 6.466,
     "mean_diameter_mm": 7.188, "nut_height_mm": 6.8},
    {"key": "m10", "group": "Metric coarse threaded rod", "label": "M10 x 1.5", "form": "metric_coarse",
     "nominal_diameter_mm": 10.0, "pitch_mm": 1.5, "minor_diameter_mm": 8.160,
     "mean_diameter_mm": 9.026, "nut_height_mm": 8.4},
    {"key": "m12", "group": "Metric coarse threaded rod", "label": "M12 x 1.75", "form": "metric_coarse",
     "nominal_diameter_mm": 12.0, "pitch_mm": 1.75, "minor_diameter_mm": 9.853,
     "mean_diameter_mm": 10.863, "nut_height_mm": 10.8},
    {"key": "m16", "group": "Metric coarse threaded rod", "label": "M16 x 2.0", "form": "metric_coarse",
     "nominal_diameter_mm": 16.0, "pitch_mm": 2.0, "minor_diameter_mm": 13.546,
     "mean_diameter_mm": 14.701, "nut_height_mm": 14.8},
    {"key": "m20", "group": "Metric coarse threaded rod", "label": "M20 x 2.5", "form": "metric_coarse",
     "nominal_diameter_mm": 20.0, "pitch_mm": 2.5, "minor_diameter_mm": 16.933,
     "mean_diameter_mm": 18.376, "nut_height_mm": 18.0},
    {"key": "m24", "group": "Metric coarse threaded rod", "label": "M24 x 3.0", "form": "metric_coarse",
     "nominal_diameter_mm": 24.0, "pitch_mm": 3.0, "minor_diameter_mm": 20.319,
     "mean_diameter_mm": 22.051, "nut_height_mm": 21.5},
    {"key": "m30", "group": "Metric coarse threaded rod", "label": "M30 x 3.5", "form": "metric_coarse",
     "nominal_diameter_mm": 30.0, "pitch_mm": 3.5, "minor_diameter_mm": 25.706,
     "mean_diameter_mm": 27.727, "nut_height_mm": 25.6},
    {"key": "m36", "group": "Metric coarse threaded rod", "label": "M36 x 4.0", "form": "metric_coarse",
     "nominal_diameter_mm": 36.0, "pitch_mm": 4.0, "minor_diameter_mm": 31.093,
     "mean_diameter_mm": 33.402, "nut_height_mm": 31.0},
    {"key": "unc_38_16", "group": "UNC threaded rod", "label": "3/8-16 UNC", "form": "unified",
     "nominal_diameter_mm": 9.525, "pitch_mm": 1.5875, "minor_diameter_mm": 7.577,
     "mean_diameter_mm": 8.494, "nut_height_mm": 8.33},
    {"key": "unc_12_13", "group": "UNC threaded rod", "label": "1/2-13 UNC", "form": "unified",
     "nominal_diameter_mm": 12.700, "pitch_mm": 1.9538, "minor_diameter_mm": 10.303,
     "mean_diameter_mm": 11.431, "nut_height_mm": 11.11},
    {"key": "unc_58_11", "group": "UNC threaded rod", "label": "5/8-11 UNC", "form": "unified",
     "nominal_diameter_mm": 15.875, "pitch_mm": 2.3091, "minor_diameter_mm": 13.042,
     "mean_diameter_mm": 14.375, "nut_height_mm": 13.89},
    {"key": "unc_34_10", "group": "UNC threaded rod", "label": "3/4-10 UNC", "form": "unified",
     "nominal_diameter_mm": 19.050, "pitch_mm": 2.5400, "minor_diameter_mm": 15.934,
     "mean_diameter_mm": 17.400, "nut_height_mm": 16.27},
    {"key": "unc_78_9", "group": "UNC threaded rod", "label": "7/8-9 UNC", "form": "unified",
     "nominal_diameter_mm": 22.225, "pitch_mm": 2.8222, "minor_diameter_mm": 18.763,
     "mean_diameter_mm": 20.392, "nut_height_mm": 19.05},
    {"key": "unc_1_8", "group": "UNC threaded rod", "label": "1-8 UNC", "form": "unified",
     "nominal_diameter_mm": 25.400, "pitch_mm": 3.1750, "minor_diameter_mm": 21.505,
     "mean_diameter_mm": 23.338, "nut_height_mm": 21.83},
]

# Fraction of the axial load taken by the first engaged thread. Thread
# deflection concentrates load at the mouth of the nut instead of sharing it
# evenly, and this is the classic Sopwith/Shigley estimate.
FIRST_THREAD_LOAD_FRACTION = 0.38


# --- Validation helpers -----------------------------------------------------


def _positive(value, name):
    """Coerce to float and require a finite, strictly positive number."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number.")
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number.")
    if number <= 0.0:
        raise ValueError(f"{name} must be greater than zero.")
    return number


def _nonnegative(value, name):
    """Coerce to float and require a finite number that is zero or greater."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number.")
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number.")
    if number < 0.0:
        raise ValueError(f"{name} cannot be negative.")
    return number


def _lookup(table, key, name):
    """Fetch a preset row, raising a message that names the valid keys."""
    if key not in table:
        options = ", ".join(sorted(table))
        raise ValueError(f"Unknown {name} '{key}'. Choose one of: {options}.")
    return table[key]


# --- Geometry ---------------------------------------------------------------


def thread_geometry(
    nominal_diameter_mm,
    pitch_mm,
    starts=1,
    thread_form="acme",
    minor_diameter_mm=0.0,
    mean_diameter_mm=0.0,
):
    """
    Derives the working diameters and lead angle of a power screw thread.

    The mean (pitch) diameter is where the flank friction force acts, so it
    sets the torque. The minor diameter is the smallest section of the screw,
    so it sets the body stress and the column buckling load. Both are computed
    from the basic thread proportions unless measured values are supplied,
    which is the better input when a standard size is being used.

    Basic proportions, with :math:`p` the pitch and :math:`f_d` the form depth
    factor (0.5 for full-depth Acme, square and trapezoidal):

    .. math::
        d_m = d - f_d p
        \\qquad
        d_r = d - 2 f_d p - 2 c p
        \\qquad
        L = n_s p
        \\qquad
        \\lambda = \\arctan\\!\\left(\\frac{L}{\\pi d_m}\\right)

    ---Parameters---
    nominal_diameter_mm : float
        Major (outside) diameter of the screw thread (mm).
    pitch_mm : float
        Axial distance from one thread crest to the next (mm).
    starts : int
        Number of thread starts. A single start gives lead = pitch; multiple
        starts multiply travel per turn at the cost of self-locking.
    thread_form : str
        Key into THREAD_FORMS: square, acme, stub_acme, trapezoidal, buttress.
    minor_diameter_mm : float
        Measured minor (root) diameter (mm). Zero computes it from the form.
    mean_diameter_mm : float
        Measured mean (pitch) diameter (mm). Zero computes it from the form.

    ---Returns---
    major_diameter_mm : float
        Nominal outside diameter of the thread (mm).
    mean_diameter_mm : float
        Diameter at which the flank friction force is taken to act (mm).
    minor_diameter_mm : float
        Root diameter carrying body stress and buckling (mm).
    lead_mm : float
        Axial travel per revolution (mm).
    lead_angle_deg : float
        Helix angle of the thread at the mean diameter (deg).
    thread_half_angle_deg : float
        Flank half angle in the axial plane (deg).
    thread_depth_mm : float
        Engaged flank height used for bearing pressure (mm).
    root_area_mm2 : float
        Cross-sectional area at the minor diameter (mm^2).
    """
    diameter = _positive(nominal_diameter_mm, "Nominal diameter")
    pitch = _positive(pitch_mm, "Pitch")
    form = _lookup(THREAD_FORMS, thread_form, "thread form")

    try:
        start_value = float(starts)
    except (TypeError, ValueError):
        raise ValueError("Number of starts must be a whole number.")
    if not math.isfinite(start_value) or start_value != int(start_value):
        raise ValueError("Number of starts must be a whole number.")
    start_count = int(start_value)
    if start_count < 1:
        raise ValueError("Number of starts must be at least 1.")

    depth = form["depth_factor"] * pitch
    pitch_offset = form["pitch_offset_factor"] * pitch
    if depth * 2.0 >= diameter:
        raise ValueError(
            "Thread depth exceeds the screw radius. Check the pitch against "
            "the nominal diameter."
        )

    mean_diameter = _nonnegative(mean_diameter_mm, "Mean diameter")
    if mean_diameter == 0.0:
        mean_diameter = diameter - pitch_offset

    minor_diameter = _nonnegative(minor_diameter_mm, "Minor diameter")
    if minor_diameter == 0.0:
        minor_diameter = diameter - 2.0 * depth - 2.0 * form["clearance_factor"] * pitch
    if minor_diameter <= 0.0:
        raise ValueError("Minor diameter works out to zero or less.")
    if minor_diameter >= diameter:
        raise ValueError("Minor diameter must be smaller than the nominal diameter.")

    lead = pitch * start_count
    lead_angle = math.degrees(math.atan2(lead, math.pi * mean_diameter))

    return {
        "major_diameter_mm": diameter,
        "mean_diameter_mm": mean_diameter,
        "minor_diameter_mm": minor_diameter,
        "lead_mm": lead,
        "lead_angle_deg": lead_angle,
        "thread_half_angle_deg": form["half_angle_deg"],
        "thread_depth_mm": depth,
        "root_area_mm2": math.pi * minor_diameter ** 2 / 4.0,
    }


# --- Core torque model ------------------------------------------------------


def screw_torques(
    load_n,
    mean_diameter_mm,
    lead_mm,
    thread_friction,
    thread_half_angle_deg=14.5,
    collar_friction=0.0,
    collar_diameter_mm=0.0,
):
    """
    Computes raising torque, lowering torque, and efficiency for a power screw.

    Unwrapping one turn of the thread into an inclined plane and resolving the
    friction force on the flank gives the standard result. With :math:`F` the
    axial load, :math:`d_m` the mean diameter, :math:`L` the lead, :math:`\\mu`
    the thread friction coefficient and :math:`\\alpha` the thread half angle,

    .. math::
        T_R = \\frac{F d_m}{2}
              \\frac{L + \\pi \\mu d_m \\sec\\alpha}
                   {\\pi d_m - \\mu L \\sec\\alpha}
        \\qquad
        T_L = \\frac{F d_m}{2}
              \\frac{\\pi \\mu d_m \\sec\\alpha - L}
                   {\\pi d_m + \\mu L \\sec\\alpha}

    The :math:`\\sec\\alpha` factor is the flank-angle penalty: an angled flank
    needs a normal force larger than the axial load, so it drags more. It drops
    out for a square thread. Thrust collar friction adds
    :math:`T_c = F \\mu_c d_c / 2` to both, acting to resist motion in either
    direction, and is often the larger half of the total on a jack.

    Efficiency is useful work out over work in per revolution:

    .. math::
        e = \\frac{F L}{2 \\pi T_R}

    Reference: Shigley, *Mechanical Engineering Design*, 10th ed., Eqs. 8-1
    through 8-6.

    ---Parameters---
    load_n : float
        Axial load carried by the screw (N).
    mean_diameter_mm : float
        Mean (pitch) diameter of the thread (mm).
    lead_mm : float
        Axial travel per revolution (mm).
    thread_friction : float
        Coefficient of sliding friction on the thread flank (dimensionless).
    thread_half_angle_deg : float
        Flank half angle in the axial plane; 0 for square, 14.5 for Acme (deg).
    collar_friction : float
        Coefficient of friction at the thrust collar or bearing face. Set to
        zero when the load is carried on a rolling thrust bearing.
    collar_diameter_mm : float
        Mean rubbing diameter of the thrust collar (mm).

    ---Returns---
    raise_torque_thread_nm : float
        Torque to raise the load, thread friction only (N*m).
    raise_torque_collar_nm : float
        Torque to raise the load, collar friction only (N*m).
    raise_torque_total_nm : float
        Total torque to raise the load (N*m).
    lower_torque_thread_nm : float
        Thread contribution to lowering torque; negative means the thread
        alone would run away under the load (N*m).
    lower_torque_collar_nm : float
        Collar contribution to lowering torque (N*m).
    lower_torque_total_nm : float
        Total torque to lower the load. Positive means torque must be applied
        to bring the load down. Negative is the holding torque needed to stop
        the load descending on its own (N*m).
    efficiency : float
        Mechanical efficiency raising the load, including collar losses.
    efficiency_thread_only : float
        Mechanical efficiency of the thread alone, ignoring the collar.
    self_locking : bool
        True when the load cannot drive the screw backwards under static
        conditions.
    self_locking_thread_only : bool
        True when the thread alone is self-locking, before crediting the
        collar. This is the honest test for a jack whose collar may be a
        rolling bearing or may be lubricated in service.
    self_locking_margin : float
        Ratio of available friction to the friction needed to hold. Values
        above 1 hold; below 1 back-drive. Thread only.
    holding_torque_nm : float
        Magnitude of the brake torque required to hold the load, zero when
        the screw is self-locking (N*m).
    """
    load = _nonnegative(load_n, "Load")
    mean_diameter = _positive(mean_diameter_mm, "Mean diameter") / 1000.0
    lead = _positive(lead_mm, "Lead") / 1000.0
    mu = _nonnegative(thread_friction, "Thread friction coefficient")
    mu_collar = _nonnegative(collar_friction, "Collar friction coefficient")
    collar_diameter = _nonnegative(collar_diameter_mm, "Collar diameter") / 1000.0

    half_angle = _nonnegative(thread_half_angle_deg, "Thread half angle")
    if half_angle >= 90.0:
        raise ValueError("Thread half angle must be less than 90 degrees.")
    sec_alpha = 1.0 / math.cos(math.radians(half_angle))

    circumference = math.pi * mean_diameter
    mu_effective = mu * sec_alpha

    raise_denominator = circumference - mu_effective * lead
    if raise_denominator <= 0.0:
        raise ValueError(
            "Friction and lead combine so that the screw cannot be driven "
            "forward at all. Reduce the friction coefficient or the lead."
        )

    torque_arm = load * mean_diameter / 2.0
    raise_thread = torque_arm * (lead + mu_effective * circumference) / raise_denominator
    lower_thread = (
        torque_arm
        * (mu_effective * circumference - lead)
        / (circumference + mu_effective * lead)
    )
    collar_torque = load * mu_collar * collar_diameter / 2.0

    raise_total = raise_thread + collar_torque
    lower_total = lower_thread + collar_torque

    efficiency = (load * lead) / (2.0 * math.pi * raise_total) if raise_total > 0.0 else 0.0
    efficiency_thread = (
        (load * lead) / (2.0 * math.pi * raise_thread) if raise_thread > 0.0 else 0.0
    )

    # Self-locking test: the thread holds when mu*sec(alpha) exceeds the
    # tangent of the lead angle, which is what makes lower_thread positive.
    tan_lead_angle = lead / circumference
    margin = mu_effective / tan_lead_angle if tan_lead_angle > 0.0 else float("inf")

    return {
        "raise_torque_thread_nm": raise_thread,
        "raise_torque_collar_nm": collar_torque,
        "raise_torque_total_nm": raise_total,
        "lower_torque_thread_nm": lower_thread,
        "lower_torque_collar_nm": collar_torque,
        "lower_torque_total_nm": lower_total,
        "efficiency": efficiency,
        "efficiency_thread_only": efficiency_thread,
        "self_locking": lower_total > 0.0,
        "self_locking_thread_only": lower_thread > 0.0,
        "self_locking_margin": margin,
        "holding_torque_nm": abs(min(lower_total, 0.0)),
    }


# --- Thread and body stresses ----------------------------------------------


def thread_stresses(
    load_n,
    geometry,
    engagement_length_mm,
    body_torque_nm=0.0,
    thread_form="acme",
):
    """
    Evaluates thread bearing, shear, and root bending plus screw body stress.

    Thread checks divide the load among the engaged threads,
    :math:`n_t = L_e / p`. With :math:`f_d` the form depth factor and
    :math:`w` the flank base width factor:

    .. math::
        \\sigma_{bearing} = \\frac{F}{\\pi d_m f_d p n_t}
        \\qquad
        \\tau_{screw} = \\frac{F}{\\pi d_r w_s p n_t}
        \\qquad
        \\tau_{nut} = \\frac{F}{\\pi d w_n p n_t}

    Root bending treats the thread as a short cantilever, which for the
    square-thread proportions gives :math:`\\sigma_b = 6F/(\\pi d_r n_t p)`.
    The same expression is used for the angled forms, where it is
    conservative because the flank base is wider than :math:`p/2`.

    Threads do not share load evenly. The nut mouth deflects least, so the
    first engaged thread takes roughly 38 percent of the total regardless of
    how many are engaged. Both the evenly-shared and first-thread values are
    returned; the first-thread numbers are the ones to design wear and
    galling against.

    The screw body is checked at the minor diameter under combined axial load
    and torsion, using distortion energy:

    .. math::
        \\sigma' = \\sqrt{\\sigma_{axial}^2 + 3\\tau_{torsion}^2}

    Reference: Shigley, *Mechanical Engineering Design*, 10th ed., Section 8-3.

    ---Parameters---
    load_n : float
        Axial load carried by the thread engagement (N).
    geometry : dict
        Output of thread_geometry(), supplying the working diameters.
    engagement_length_mm : float
        Axial length of nut actually in thread contact (mm).
    body_torque_nm : float
        Torque carried by the screw body at the section being checked (N*m).
    thread_form : str
        Key into THREAD_FORMS, used for the flank width factors.

    ---Returns---
    engaged_threads : float
        Number of threads in contact (dimensionless).
    bearing_pressure_mpa : float
        Flank bearing pressure with load shared evenly (MPa).
    bearing_pressure_first_thread_mpa : float
        Flank bearing pressure on the most heavily loaded thread (MPa).
    screw_thread_shear_mpa : float
        Shear stress at the base of the screw thread (MPa).
    nut_thread_shear_mpa : float
        Shear stress at the base of the nut thread (MPa).
    thread_root_bending_mpa : float
        Bending stress at the root of the screw thread (MPa).
    body_axial_stress_mpa : float
        Axial stress at the minor diameter, positive in compression (MPa).
    body_torsional_shear_mpa : float
        Torsional shear stress at the minor diameter (MPa).
    body_von_mises_mpa : float
        Combined equivalent stress at the minor diameter (MPa).
    """
    load = _nonnegative(load_n, "Load")
    engagement = _positive(engagement_length_mm, "Nut engagement length")
    torque = _nonnegative(body_torque_nm, "Body torque")
    form = _lookup(THREAD_FORMS, thread_form, "thread form")

    pitch = geometry["thread_depth_mm"] / form["depth_factor"]
    mean_diameter = geometry["mean_diameter_mm"]
    minor_diameter = geometry["minor_diameter_mm"]
    major_diameter = geometry["major_diameter_mm"]

    engaged = engagement / pitch
    if engaged < 1.0:
        raise ValueError(
            "Nut engagement is shorter than one pitch. Lengthen the nut or "
            "use a finer thread."
        )

    bearing_area = math.pi * mean_diameter * geometry["thread_depth_mm"] * engaged
    screw_shear_area = math.pi * minor_diameter * form["shear_width_screw"] * pitch * engaged
    nut_shear_area = math.pi * major_diameter * form["shear_width_nut"] * pitch * engaged

    bearing = load / bearing_area
    bearing_first = (
        FIRST_THREAD_LOAD_FRACTION * load
        / (math.pi * mean_diameter * geometry["thread_depth_mm"])
    )

    root_area = geometry["root_area_mm2"]
    axial_stress = load / root_area
    torsional_shear = 16.0 * (torque * 1000.0) / (math.pi * minor_diameter ** 3)

    return {
        "engaged_threads": engaged,
        "bearing_pressure_mpa": bearing,
        "bearing_pressure_first_thread_mpa": bearing_first,
        "screw_thread_shear_mpa": load / screw_shear_area,
        "nut_thread_shear_mpa": load / nut_shear_area,
        "thread_root_bending_mpa": 6.0 * load / (math.pi * minor_diameter * engaged * pitch),
        "body_axial_stress_mpa": axial_stress,
        "body_torsional_shear_mpa": torsional_shear,
        "body_von_mises_mpa": math.sqrt(axial_stress ** 2 + 3.0 * torsional_shear ** 2),
    }


# --- Column buckling --------------------------------------------------------


def column_buckling(
    minor_diameter_mm,
    unsupported_length_mm,
    modulus_gpa,
    yield_mpa,
    end_fixity="fixed_free",
):
    """
    Finds the critical compressive load of the screw acting as a column.

    A jack screw in compression is a slender column, and for long screws
    buckling governs long before the material yields. The slenderness ratio
    uses the effective length :math:`L_e = K L` and the radius of gyration of
    the root section, :math:`k = d_r / 4`.

    Which formula applies depends on where the slenderness sits relative to
    the transition value :math:`C_c = \\sqrt{2\\pi^2 E / S_y}`, the point where
    the Euler curve crosses half the yield stress:

    .. math::
        P_{cr} = \\frac{\\pi^2 E A}{(L_e/k)^2}
        \\quad (L_e/k > C_c, \\text{Euler})
        \\qquad
        P_{cr} = A\\left[S_y - \\frac{1}{E}
                 \\left(\\frac{S_y L_e / k}{2\\pi}\\right)^2\\right]
        \\quad (L_e/k \\le C_c, \\text{J. B. Johnson})

    Using Euler below the transition would overpredict the strength of a
    stocky column, because it ignores yielding entirely.

    The effective-length factors in END_FIXITIES are the recommended design
    values rather than the theoretical ones, since real end conditions are
    never as rigid as drawn.

    Reference: Shigley, *Mechanical Engineering Design*, 10th ed.,
    Sections 4-11 and 4-12.

    ---Parameters---
    minor_diameter_mm : float
        Root diameter of the screw, the section that buckles (mm).
    unsupported_length_mm : float
        Free column length between the supports (mm).
    modulus_gpa : float
        Young's modulus of the screw material (GPa).
    yield_mpa : float
        Yield strength of the screw material (MPa).
    end_fixity : str
        Key into END_FIXITIES describing how the ends are held.

    ---Returns---
    slenderness_ratio : float
        Effective length over radius of gyration (dimensionless).
    transition_slenderness : float
        Slenderness at which Euler takes over from Johnson (dimensionless).
    effective_length_mm : float
        Buckling length after applying the end-fixity factor (mm).
    buckling_mode : str
        Either "euler" or "johnson", naming the formula that governed.
    critical_load_n : float
        Compressive load at which the column buckles (N).
    """
    minor_diameter = _positive(minor_diameter_mm, "Minor diameter")
    length = _positive(unsupported_length_mm, "Unsupported length")
    modulus = _positive(modulus_gpa, "Elastic modulus") * 1000.0  # MPa
    yield_strength = _positive(yield_mpa, "Yield strength")
    fixity = _lookup(END_FIXITIES, end_fixity, "end fixity")

    area = math.pi * minor_diameter ** 2 / 4.0
    radius_of_gyration = minor_diameter / 4.0
    effective_length = fixity["k_buckling"] * length
    slenderness = effective_length / radius_of_gyration
    transition = math.sqrt(2.0 * math.pi ** 2 * modulus / yield_strength)

    if slenderness > transition:
        mode = "euler"
        critical = math.pi ** 2 * modulus * area / slenderness ** 2
    else:
        mode = "johnson"
        critical = area * (
            yield_strength
            - (1.0 / modulus) * (yield_strength * slenderness / (2.0 * math.pi)) ** 2
        )

    return {
        "slenderness_ratio": slenderness,
        "transition_slenderness": transition,
        "effective_length_mm": effective_length,
        "buckling_mode": mode,
        "critical_load_n": max(critical, 0.0),
    }


def critical_speed(
    minor_diameter_mm,
    unsupported_length_mm,
    modulus_gpa,
    density_kg_m3=7850.0,
    end_fixity="fixed_free",
):
    """
    Finds the whirl speed of a rotating screw shaft.

    A driven lead screw is a rotating beam. Run it at the first bending
    natural frequency and it whirls: deflection grows, the nut binds, and the
    screw can take a permanent bend. The natural frequency of a uniform beam
    is

    .. math::
        \\omega_n = (\\beta L)^2 \\sqrt{\\frac{E I}{\\rho A L^4}}

    where :math:`(\\beta L)^2` is 3.516 for fixed-free, 9.870 for
    pinned-pinned, 15.418 for fixed-pinned and 22.373 for fixed-fixed. For a
    solid round section :math:`\\sqrt{I/A} = d_r/4`, so the whirl speed scales
    with root diameter over length squared. Doubling the length of a jack
    screw cuts its whirl speed by four.

    Common practice is to run below 80 percent of the computed value, since
    the derivation assumes a uniform, straight, perfectly balanced shaft.

    ---Parameters---
    minor_diameter_mm : float
        Root diameter of the screw (mm).
    unsupported_length_mm : float
        Free span between bearings (mm).
    modulus_gpa : float
        Young's modulus of the screw material (GPa).
    density_kg_m3 : float
        Density of the screw material (kg/m^3).
    end_fixity : str
        Key into END_FIXITIES describing how the ends are held.

    ---Returns---
    critical_speed_rpm : float
        First whirl speed of the screw shaft (rpm).
    recommended_max_speed_rpm : float
        80 percent of the whirl speed (rpm).
    """
    minor_diameter = _positive(minor_diameter_mm, "Minor diameter") / 1000.0
    length = _positive(unsupported_length_mm, "Unsupported length") / 1000.0
    modulus = _positive(modulus_gpa, "Elastic modulus") * 1.0e9  # Pa
    density = _positive(density_kg_m3, "Density")
    fixity = _lookup(END_FIXITIES, end_fixity, "end fixity")

    # sqrt(E*I / (rho*A*L^4)) reduces to sqrt(E/rho) * (d_r/4) / L^2
    omega = fixity["beta_l_squared"] * math.sqrt(modulus / density) * (
        minor_diameter / 4.0
    ) / length ** 2
    rpm = omega * 60.0 / (2.0 * math.pi)

    return {
        "critical_speed_rpm": rpm,
        "recommended_max_speed_rpm": 0.8 * rpm,
    }


# --- Ball screw comparison --------------------------------------------------


def ball_screw_comparison(load_n, lead_mm, direct_efficiency=0.90):
    """
    Computes ball screw torque and back-drive behaviour for the same duty.

    A ball screw replaces sliding friction with rolling contact, so its
    efficiency is a property of the assembly rather than something derived
    from a friction coefficient. Manufacturers quote 0.85 to 0.95 for the
    direct (rotary to linear) direction. The torque follows straight from
    the work balance:

    .. math::
        T = \\frac{F L}{2 \\pi \\eta}

    Back-driving is the reason ball screws change the design rather than just
    shrinking the motor. The reverse efficiency is

    .. math::
        \\eta_{back} = 2 - \\frac{1}{\\eta}

    which is positive for any :math:`\\eta > 0.5`. A ball screw at 90 percent
    has a back-drive efficiency of 0.889, so it will run away under load the
    moment the drive torque is removed. A ball screw jack needs a brake, and
    the brake is not optional.

    ---Parameters---
    load_n : float
        Axial load carried by the screw (N).
    lead_mm : float
        Axial travel per revolution (mm).
    direct_efficiency : float
        Rotary-to-linear efficiency of the ball nut assembly, typically 0.85
        to 0.95 (dimensionless).

    ---Returns---
    raise_torque_nm : float
        Torque to drive the load, thread only (N*m).
    back_drive_efficiency : float
        Linear-to-rotary efficiency (dimensionless).
    back_drive_torque_nm : float
        Torque the load generates at the screw when released. This is the
        minimum brake torque required (N*m).
    self_locking : bool
        True only for the unusual case of a ball screw below 50 percent
        efficiency.
    """
    load = _nonnegative(load_n, "Load")
    lead = _positive(lead_mm, "Lead") / 1000.0
    efficiency = _positive(direct_efficiency, "Ball screw efficiency")
    if efficiency >= 1.0:
        raise ValueError("Ball screw efficiency must be less than 1.")

    back_efficiency = 2.0 - 1.0 / efficiency

    return {
        "raise_torque_nm": load * lead / (2.0 * math.pi * efficiency),
        "back_drive_efficiency": back_efficiency,
        "back_drive_torque_nm": max(load * lead * back_efficiency / (2.0 * math.pi), 0.0),
        "self_locking": back_efficiency <= 0.0,
    }


# --- Top-level analysis -----------------------------------------------------


def analyze_jack_screw(
    load_n=25000.0,
    nominal_diameter_mm=32.0,
    pitch_mm=6.0,
    starts=1,
    thread_form="acme",
    thread_friction=0.14,
    collar_friction=0.12,
    collar_diameter_mm=45.0,
    nut_engagement_length_mm=48.0,
    unsupported_length_mm=400.0,
    end_fixity="fixed_free",
    screw_material="steel_1045",
    nut_material="bronze",
    rotational_speed_rpm=0.0,
    lever_arm_mm=0.0,
    ball_screw_efficiency=0.90,
    design_factor=2.0,
    minor_diameter_mm=0.0,
    mean_diameter_mm=0.0,
    screw_modulus_gpa=0.0,
    screw_yield_mpa=0.0,
    screw_density_kg_m3=0.0,
    nut_allowable_bearing_mpa=0.0,
):
    """
    Sizes and checks a sliding-contact jack screw against a single load case.

    Starts from the four numbers that decide whether a jack screw works at
    all: the torque to raise the load, the efficiency, whether it holds the
    load with the input released, and the torque to lower it. Everything else
    is a check on that answer. Thread bearing pressure decides how long the
    nut lasts, column buckling decides whether a long screw stands up, and
    whirl decides how fast a driven screw can turn.

    Self-locking deserves its own note, because it is the property people buy
    a jack screw for and the one most often assumed rather than checked. The
    static condition is :math:`\\mu \\sec\\alpha > \\tan\\lambda`, and it is
    reported here for the thread alone rather than for thread plus collar. A
    thrust bearing can be swapped for a plain collar, the collar can be
    greased, and either change removes collar friction from the holding
    balance. A screw that only holds because of its collar is one maintenance
    task away from dropping its load. Efficiency below about 35 percent is
    the usual rule-of-thumb signal that a screw is self-locking, and it falls
    out of the same inequality. Note also that static self-locking is not the
    same as holding under vibration, which relaxes the effective friction
    coefficient; a jack that must hold a load unattended needs a mechanical
    brake or pawl no matter what this calculation says.

    Reference: Shigley, *Mechanical Engineering Design*, 10th ed., Sections
    8-2 and 8-3; Oberg et al., *Machinery's Handbook*, 30th ed., "Power
    Transmission Screws".

    ---Parameters---
    load_n : float
        Axial load the screw raises or holds (N).
    nominal_diameter_mm : float
        Major (outside) diameter of the screw thread (mm).
    pitch_mm : float
        Axial distance between adjacent thread crests (mm).
    starts : int
        Number of thread starts. More starts means faster travel and lower
        torque per unit lift, but the screw stops being self-locking.
    thread_form : str
        Thread profile: square, acme, stub_acme, trapezoidal or buttress.
    thread_friction : float
        Sliding friction coefficient on the thread flank (dimensionless).
    collar_friction : float
        Friction coefficient at the thrust face. Set to zero when the thrust
        load runs on a rolling bearing (dimensionless).
    collar_diameter_mm : float
        Mean rubbing diameter of the thrust collar (mm).
    nut_engagement_length_mm : float
        Length of nut in thread contact. Zero skips the thread checks (mm).
    unsupported_length_mm : float
        Free column length of the screw. Zero skips buckling and whirl (mm).
    end_fixity : str
        How the screw ends are held: fixed_free, pinned_pinned, fixed_pinned
        or fixed_fixed.
    screw_material : str
        Key into SCREW_MATERIALS for modulus, yield strength and density.
    nut_material : str
        Key into NUT_MATERIALS for the allowable bearing pressure and PV limit.
    rotational_speed_rpm : float
        Screw speed in service. Zero skips speed, power and PV output (rpm).
    lever_arm_mm : float
        Radius at which the operator pushes on a bar or handwheel. Zero skips
        the operator force output (mm).
    ball_screw_efficiency : float
        Direct efficiency assumed for the ball screw comparison, typically
        0.85 to 0.95 (dimensionless).
    design_factor : float
        Target safety factor used to grade the returned margins.
    minor_diameter_mm : float
        Measured minor diameter. Zero derives it from the thread form (mm).
    mean_diameter_mm : float
        Measured mean diameter. Zero derives it from the thread form (mm).
    screw_modulus_gpa : float
        Override for the screw elastic modulus. Zero uses the preset (GPa).
    screw_yield_mpa : float
        Override for the screw yield strength. Zero uses the preset (MPa).
    screw_density_kg_m3 : float
        Override for the screw density. Zero uses the preset (kg/m^3).
    nut_allowable_bearing_mpa : float
        Override for the nut allowable bearing pressure. Zero uses the
        preset (MPa).

    ---Returns---
    geometry : dict
        Working diameters, lead, lead angle and root area.
    torque : dict
        Raising, lowering and holding torques, efficiency and self-locking.
    thread : dict
        Thread and body stresses with their margins, when a nut engagement
        length was given.
    buckling : dict
        Critical column load and safety factor, when a length was given.
    whirl : dict
        Critical speed and the recommended running limit.
    ball_screw : dict
        Torque and back-drive behaviour of an equivalent ball screw.
    duty : dict
        Travel speed, input power, rubbing velocity, PV product and the
        operator force at the given lever arm.
    warnings : list
        Dicts of level and message describing everything worth a second look.
    verdict : str
        Overall grade: ok, caution or unacceptable.
    """
    load = _positive(load_n, "Load")
    factor = _positive(design_factor, "Design factor")
    screw_props = _lookup(SCREW_MATERIALS, screw_material, "screw material")
    nut_props = _lookup(NUT_MATERIALS, nut_material, "nut material")

    modulus = _nonnegative(screw_modulus_gpa, "Screw modulus") or screw_props["modulus_gpa"]
    yield_strength = _nonnegative(screw_yield_mpa, "Screw yield") or screw_props["yield_mpa"]
    density = _nonnegative(screw_density_kg_m3, "Screw density") or screw_props["density_kg_m3"]
    allowable_bearing = (
        _nonnegative(nut_allowable_bearing_mpa, "Nut allowable bearing")
        or nut_props["allowable_bearing_mpa"]
    )

    geometry = thread_geometry(
        nominal_diameter_mm,
        pitch_mm,
        starts,
        thread_form,
        minor_diameter_mm,
        mean_diameter_mm,
    )
    torque = screw_torques(
        load,
        geometry["mean_diameter_mm"],
        geometry["lead_mm"],
        thread_friction,
        geometry["thread_half_angle_deg"],
        collar_friction,
        collar_diameter_mm,
    )

    warnings = []
    verdict_rank = 0  # 0 ok, 1 caution, 2 unacceptable

    def flag(level, message):
        nonlocal verdict_rank
        warnings.append({"level": level, "message": message})
        verdict_rank = max(verdict_rank, {"info": 0, "caution": 1, "critical": 2}[level])

    # --- Fastener thread used as a motion screw
    if THREAD_FORMS[thread_form]["motion_class"] == "fastener":
        flag(
            "info",
            "This is a fastener thread, not a motion thread. It works as a jack "
            "and it self-locks readily, because the short lead and the 30 degree "
            "flank both push that way. The costs are efficiency, which the flank "
            "angle lowers further, and wear: the sharp V concentrates contact on "
            "a narrow band and has no way to take up slack as it wears, where a "
            "split Acme nut does. Fine for a hand jack or occasional adjustment, "
            "poor for anything cycling continuously.",
        )

    # --- Self-locking commentary
    if not torque["self_locking_thread_only"]:
        if torque["self_locking"]:
            flag(
                "critical",
                "The thread alone back-drives. This screw only holds its load "
                "because of thrust collar friction, which disappears if the "
                "collar is greased or replaced with a rolling bearing. Treat "
                "it as non-self-locking and fit a brake.",
            )
        else:
            flag(
                "critical",
                "The screw back-drives under load. A brake or pawl of at least "
                f"{torque['holding_torque_nm']:.1f} N*m is required to hold it.",
            )
    elif torque["self_locking_margin"] < 1.3:
        flag(
            "caution",
            f"Self-locking margin is only {torque['self_locking_margin']:.2f}. "
            "Friction that low is within the scatter of the published data, and "
            "vibration reduces it further. Do not rely on this to hold a load "
            "unattended.",
        )

    if torque["efficiency"] < 0.20:
        # Low efficiency is the price of self-locking, not a fault, so this
        # informs rather than downgrades the verdict. Heat is caught by the
        # PV check, which needs a speed to mean anything.
        flag(
            "info",
            f"Efficiency is {torque['efficiency'] * 100:.0f} percent, which is "
            "normal for a self-locking jack: the friction that wastes the rest "
            "is what holds the load. It does mean most of the input becomes heat "
            "in the nut, so check the PV limit if the screw runs continuously.",
        )

    # --- Thread and body stresses
    thread = {"evaluated": False}
    engagement = _nonnegative(nut_engagement_length_mm, "Nut engagement length")
    if engagement > 0.0:
        thread = thread_stresses(
            load,
            geometry,
            engagement,
            torque["raise_torque_total_nm"],
            thread_form,
        )
        thread["evaluated"] = True
        thread["allowable_bearing_mpa"] = allowable_bearing
        thread["bearing_margin"] = allowable_bearing / thread["bearing_pressure_mpa"]
        thread["bearing_margin_first_thread"] = (
            allowable_bearing / thread["bearing_pressure_first_thread_mpa"]
        )
        thread["body_safety_factor"] = yield_strength / thread["body_von_mises_mpa"]
        # Shear yields at 0.577 Sy under distortion energy.
        thread["shear_safety_factor"] = (
            0.577 * yield_strength / max(thread["screw_thread_shear_mpa"], 1e-9)
        )
        thread["engagement_ratio"] = engagement / geometry["mean_diameter_mm"]

        if thread["bearing_margin"] < 1.0:
            flag(
                "critical",
                f"Thread bearing pressure of {thread['bearing_pressure_mpa']:.1f} MPa "
                f"exceeds the {allowable_bearing:.0f} MPa the nut material tolerates. "
                "The nut will wear out quickly. Lengthen the nut or grow the screw.",
            )
        elif thread["bearing_margin_first_thread"] < 1.0:
            # Published allowables are average-pressure wear limits, so this is
            # context for where the nut wears rather than a limit that is
            # being exceeded.
            flag(
                "info",
                f"The first engaged thread carries about {FIRST_THREAD_LOAD_FRACTION * 100:.0f} "
                f"percent of the load, or {thread['bearing_pressure_first_thread_mpa']:.1f} MPa. "
                "Wear concentrates at the mouth of the nut, which is why a worn "
                "nut develops backlash there first.",
            )

        if thread["body_safety_factor"] < factor:
            flag(
                "critical" if thread["body_safety_factor"] < 1.0 else "caution",
                f"Screw body safety factor is {thread['body_safety_factor']:.2f} against "
                f"a target of {factor:.1f}, combining axial load and drive torque at "
                "the minor diameter.",
            )

        if thread["engaged_threads"] > 10.0:
            flag(
                "info",
                f"{thread['engaged_threads']:.0f} threads are engaged. Beyond about "
                "ten the extra length adds almost no capacity, because thread "
                "deflection keeps the load at the mouth of the nut.",
            )
        if thread["engagement_ratio"] < 1.0:
            flag(
                "caution",
                "Nut engagement is shorter than one mean diameter. Standard practice "
                "is 1.0 to 1.5 diameters so the nut cannot cock on the screw.",
            )

    # --- Buckling and whirl
    buckling = {"evaluated": False}
    whirl = {"evaluated": False}
    length = _nonnegative(unsupported_length_mm, "Unsupported length")
    if length > 0.0:
        buckling = column_buckling(
            geometry["minor_diameter_mm"], length, modulus, yield_strength, end_fixity
        )
        buckling["evaluated"] = True
        buckling["safety_factor"] = buckling["critical_load_n"] / load
        buckling["end_fixity_label"] = END_FIXITIES[end_fixity]["label"]

        if buckling["safety_factor"] < 1.0:
            flag(
                "critical",
                f"The screw buckles at {buckling['critical_load_n'] / 1000.0:.1f} kN, "
                f"below the {load / 1000.0:.1f} kN load. Shorten the column, support "
                "it, or use a larger root diameter.",
            )
        elif buckling["safety_factor"] < factor:
            flag(
                "caution",
                f"Buckling safety factor is {buckling['safety_factor']:.2f} against a "
                f"target of {factor:.1f}. Column strength falls with the square of "
                "length, so any growth in stroke makes this worse fast.",
            )

        whirl = critical_speed(
            geometry["minor_diameter_mm"], length, modulus, density, end_fixity
        )
        whirl["evaluated"] = True

    # --- Duty
    speed = _nonnegative(rotational_speed_rpm, "Rotational speed")
    lever = _nonnegative(lever_arm_mm, "Lever arm")
    duty = {
        "travel_speed_mm_s": geometry["lead_mm"] * speed / 60.0,
        "input_power_w": torque["raise_torque_total_nm"] * 2.0 * math.pi * speed / 60.0,
        "rubbing_velocity_m_s": math.pi * (geometry["mean_diameter_mm"] / 1000.0) * speed / 60.0,
        "operator_force_n": (
            torque["raise_torque_total_nm"] / (lever / 1000.0) if lever > 0.0 else 0.0
        ),
        "pv_value_mpa_m_s": 0.0,
        "pv_limit_mpa_m_s": nut_props["pv_limit_mpa_m_s"],
    }
    if speed > 0.0 and thread["evaluated"]:
        duty["pv_value_mpa_m_s"] = (
            thread["bearing_pressure_mpa"] * duty["rubbing_velocity_m_s"]
        )
        if duty["pv_value_mpa_m_s"] > nut_props["pv_limit_mpa_m_s"]:
            flag(
                "caution",
                f"PV of {duty['pv_value_mpa_m_s']:.2f} MPa*m/s exceeds the "
                f"{nut_props['pv_limit_mpa_m_s']:.2f} limit for this nut material. "
                "The nut will overheat on continuous duty; use an intermittent "
                "cycle or a larger screw.",
            )
    if speed > 0.0 and whirl["evaluated"] and speed > whirl["recommended_max_speed_rpm"]:
        flag(
            "critical" if speed > whirl["critical_speed_rpm"] else "caution",
            f"Running at {speed:.0f} rpm against a whirl speed of "
            f"{whirl['critical_speed_rpm']:.0f} rpm. Stay below 80 percent of "
            "critical or add an intermediate support.",
        )
    if lever > 0.0 and duty["operator_force_n"] > 350.0:
        flag(
            "caution",
            f"A hand lever at this radius needs {duty['operator_force_n']:.0f} N. "
            "Sustained two-handed effort tops out near 350 N, so lengthen the bar "
            "or gear the input.",
        )

    ball_screw = ball_screw_comparison(load, geometry["lead_mm"], ball_screw_efficiency)
    ball_screw["torque_ratio"] = (
        torque["raise_torque_thread_nm"] / ball_screw["raise_torque_nm"]
        if ball_screw["raise_torque_nm"] > 0.0
        else 0.0
    )

    return {
        "geometry": geometry,
        "torque": torque,
        "thread": thread,
        "buckling": buckling,
        "whirl": whirl,
        "ball_screw": ball_screw,
        "duty": duty,
        "materials": {
            "screw_label": screw_props["label"],
            "nut_label": nut_props["label"],
            "screw_modulus_gpa": modulus,
            "screw_yield_mpa": yield_strength,
            "screw_density_kg_m3": density,
            "nut_allowable_bearing_mpa": allowable_bearing,
        },
        "warnings": warnings,
        "verdict": ["ok", "caution", "unacceptable"][verdict_rank],
    }
