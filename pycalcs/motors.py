"""
Motor topology reference data and educational helper functions.

The functions in this module intentionally start as lookup and normalization
helpers. Later build steps add the synthetic performance and control models
that consume the same topology data.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


# Polarity values:
#   "higher_better"  -> normalize so larger numeric values rank higher
#   "lower_better"   -> normalize so smaller numeric values rank higher
#   "context"        -> no universal direction; surface the value but do not score it
#
# Scale (ordinal dimensions only): integer-keyed map from numeric code to label.
# The keys cover the full encoding range; per-topology entries store integers
# from this set in their min/typ/max fields.
TRADEOFF_DIMENSIONS: dict[str, dict[str, Any]] = {
    "torque_density_nm_per_kg": {
        "label": "Torque density by mass",
        "unit": "N-m/kg",
        "kind": "numeric",
        "polarity": "higher_better",
    },
    "torque_density_nm_per_l": {
        "label": "Torque density by volume",
        "unit": "N-m/L",
        "kind": "numeric",
        "polarity": "higher_better",
    },
    "power_density_w_per_kg": {
        "label": "Power density by mass",
        "unit": "W/kg",
        "kind": "numeric",
        "polarity": "higher_better",
    },
    "power_density_w_per_l": {
        "label": "Power density by volume",
        "unit": "W/L",
        "kind": "numeric",
        "polarity": "higher_better",
    },
    "peak_efficiency_percent": {
        "label": "Peak efficiency",
        "unit": "%",
        "kind": "numeric",
        "polarity": "higher_better",
    },
    "speed_range_rpm": {
        "label": "Speed range / max safe speed",
        "unit": "rpm",
        "kind": "numeric",
        "polarity": "higher_better",
    },
    "field_weakening_capability": {
        "label": "Field-weakening capability",
        "unit": "ordinal",
        "kind": "ordinal",
        "polarity": "higher_better",
        "scale": {0: "None", 1: "Limited", 2: "Moderate", 3: "Strong"},
    },
    "cost_usd_per_kw": {
        "label": "Cost band",
        "unit": "$/kW",
        "kind": "numeric",
        "polarity": "lower_better",
    },
    "control_complexity": {
        "label": "Control complexity",
        "unit": "1-5",
        "kind": "ordinal",
        "polarity": "lower_better",
        "scale": {1: "Trivial", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"},
    },
    "cogging_smoothness": {
        "label": "Cogging / smoothness",
        "unit": "1-5",
        "kind": "ordinal",
        "polarity": "higher_better",
        "scale": {1: "Heavy ripple", 2: "Notable ripple", 3: "Some ripple", 4: "Smooth", 5: "Glassy"},
    },
    "audible_noise": {
        "label": "Audible noise character",
        "unit": "1-5",
        "kind": "ordinal",
        "polarity": "lower_better",
        "scale": {1: "Silent", 2: "Soft hum", 3: "Audible whine", 4: "Loud", 5: "Harsh"},
    },
    "self_starting": {
        "label": "Self-starting behavior",
        "unit": "ordinal",
        "kind": "ordinal",
        "polarity": "higher_better",
        "scale": {1: "Needs commutation", 2: "Self-starting"},
    },
    "position_sensor_requirement": {
        "label": "Position-sensor requirement",
        "unit": "ordinal",
        "kind": "ordinal",
        "polarity": "lower_better",
        "scale": {0: "None", 1: "Optional", 2: "Recommended", 3: "Required"},
    },
    "power_factor": {
        "label": "Power factor",
        "unit": "cos(phi)",
        "kind": "numeric",
        "polarity": "higher_better",
    },
    "rotor_inertia": {
        "label": "Rotor inertia",
        "unit": "1-5",
        "kind": "ordinal",
        "polarity": "context",
        "scale": {1: "Very low", 2: "Low", 3: "Medium", 4: "High", 5: "Very high"},
    },
    "magnet_content": {
        "label": "Magnet content",
        "unit": "ordinal",
        "kind": "ordinal",
        "polarity": "lower_better",
        "scale": {0: "None", 1: "Ferrite", 2: "NdFeB", 3: "SmCo"},
    },
    "continuous_peak_ratio": {
        "label": "Continuous-to-peak ratio",
        "unit": "ratio",
        "kind": "numeric",
        "polarity": "higher_better",
    },
}


MOTOR_TOPOLOGIES: dict[str, dict[str, Any]] = {
    "pmsm_spm": {
        "name": "BLDC / PMSM - Surface-Mount PM",
        "short_name": "PMSM (SPM)",
        "family": "Permanent-magnet synchronous",
        "one_sentence": (
            "A surface-magnet synchronous motor trades magnet cost and inverter "
            "complexity for high efficiency, high torque density, and smooth "
            "electronically controlled torque."
        ),
        "description": (
            "The rotor carries permanent magnets on its surface while the stator "
            "creates a rotating magnetic field. Torque is produced because the "
            "rotor magnet flux wants to align with the commanded stator field. "
            "This is the baseline modern BLDC/PMSM architecture used in drones, "
            "servo axes, appliances, pumps, and many compact traction drives."
        ),
        "distinguishing_facts": [
            "No rotor copper loss, so efficiency is often high over a broad load range.",
            "Torque is nearly proportional to q-axis current until voltage or thermal limits dominate.",
            "Surface magnets give limited saliency, so field weakening is useful but not as strong as IPM.",
            "Back-EMF may be sinusoidal or trapezoidal depending on winding and magnet design.",
        ],
        "applications": [
            "drone outrunners",
            "industrial servos",
            "e-bike hub motors",
            "appliance compressors",
            "small pumps and fans",
        ],
        "pros": [
            "High peak efficiency",
            "High torque density",
            "Smooth torque under sinusoidal or FOC drive",
            "No brushes or commutator wear",
        ],
        "cons": [
            "Requires electronic commutation",
            "Uses permanent magnets",
            "Demagnetization risk at high temperature or fault current",
            "Limited field-weakening compared with IPM machines",
        ],
        "applicable_control_methods": [
            "six-step / trapezoidal",
            "sinusoidal",
            "FOC",
            "FOC + field weakening",
            "sensored vs sensorless",
        ],
        "default_parameters": {
            "V_dc": 48.0,
            "I_max": 60.0,
            "k_e": 0.055,
            "R_phase": 0.045,
            "L_d": 0.00008,
            "L_q": 0.00009,
        },
        "tradeoffs": {
            "torque_density_nm_per_kg": {
                "min": 1.5,
                "typ": 4.0,
                "max": 12.0,
                "unit": "N-m/kg",
                "display": "High",
            },
            "torque_density_nm_per_l": {
                "min": 4.0,
                "typ": 14.0,
                "max": 40.0,
                "unit": "N-m/L",
                "display": "High",
            },
            "power_density_w_per_kg": {
                "min": 500.0,
                "typ": 2500.0,
                "max": 8000.0,
                "unit": "W/kg",
                "display": "High",
            },
            "power_density_w_per_l": {
                "min": 1000.0,
                "typ": 4500.0,
                "max": 18000.0,
                "unit": "W/L",
                "display": "High",
            },
            "peak_efficiency_percent": {
                "min": 85.0,
                "typ": 92.0,
                "max": 97.0,
                "unit": "%",
                "display": "85-97%",
            },
            "speed_range_rpm": {
                "min": 3000.0,
                "typ": 12000.0,
                "max": 80000.0,
                "unit": "rpm",
                "display": "Broad, voltage-limited at high speed",
            },
            "field_weakening_capability": {
                "min": 0.0,
                "typ": 1.0,
                "max": 2.0,
                "unit": "ordinal",
                "display": "Limited to moderate",
            },
            "cost_usd_per_kw": {
                "min": 80.0,
                "typ": 200.0,
                "max": 600.0,
                "unit": "$/kW",
                "display": "Medium to high",
            },
            "control_complexity": {
                "min": 2.0,
                "typ": 4.0,
                "max": 5.0,
                "unit": "1-5",
                "display": "Moderate to high",
            },
            "cogging_smoothness": {
                "min": 2.0,
                "typ": 4.0,
                "max": 5.0,
                "unit": "1-5",
                "display": "Smooth with FOC",
            },
            "audible_noise": {
                "min": 1.0,
                "typ": 2.0,
                "max": 4.0,
                "unit": "1-5",
                "display": "Usually quiet; switching whine possible",
            },
            "self_starting": {
                "min": 1.0,
                "typ": 1.0,
                "max": 2.0,
                "unit": "ordinal",
                "display": "With electronic commutation",
            },
            "position_sensor_requirement": {
                "min": 1.0,
                "typ": 2.0,
                "max": 3.0,
                "unit": "ordinal",
                "display": "Optional to common",
            },
            "power_factor": {
                "min": 0.85,
                "typ": 0.95,
                "max": 0.99,
                "unit": "cos(phi)",
                "display": "High under FOC",
            },
            "rotor_inertia": {
                "min": 1.0,
                "typ": 2.0,
                "max": 4.0,
                "unit": "1-5",
                "display": "Low to medium",
            },
            "magnet_content": {
                "min": 2.0,
                "typ": 3.0,
                "max": 3.0,
                "unit": "ordinal",
                "display": "NdFeB or SmCo",
            },
            "continuous_peak_ratio": {
                "min": 0.20,
                "typ": 0.50,
                "max": 0.80,
                "unit": "ratio",
                "display": "Thermal design dependent",
            },
        },
        "references": [
            "Krishnan, Permanent Magnet Synchronous and Brushless DC Motor Drives",
            "Boldea and Nasar, Electric Drives",
            "Hendershot and Miller, Design of Brushless Permanent-Magnet Machines",
        ],
    },
    "induction_squirrel_cage": {
        "name": "Induction - Squirrel Cage",
        "short_name": "Induction",
        "family": "Asynchronous AC",
        "one_sentence": (
            "A squirrel-cage induction motor sacrifices some low-speed efficiency "
            "and power factor for ruggedness, low magnet content, and excellent "
            "industrial practicality."
        ),
        "description": (
            "The stator creates a rotating magnetic field that induces current in "
            "shorted rotor bars. The rotor must lag the stator field slightly; "
            "that lag is slip, and it is the mechanism that creates torque. This "
            "architecture dominates pumps, fans, compressors, conveyors, and "
            "general industrial drives."
        ),
        "distinguishing_facts": [
            "Torque requires slip, so rotor speed is not exactly synchronous speed.",
            "Rotor I-squared-R loss rises with slip and matters most at high torque.",
            "It can run directly from AC mains, but variable-speed use benefits from V/f or vector control.",
            "No permanent magnets are needed, which improves cost and supply-chain robustness.",
        ],
        "applications": [
            "industrial pumps",
            "fans and blowers",
            "compressors",
            "conveyors",
            "machine tools",
        ],
        "pros": [
            "Rugged rotor construction",
            "No brushes or permanent magnets",
            "Low cost per kilowatt",
            "Can self-start from line power when designed for it",
        ],
        "cons": [
            "Slip creates rotor losses",
            "Lower power factor than PM machines",
            "Vector control is needed for high dynamic performance",
            "Efficiency falls at light load and high slip",
        ],
        "applicable_control_methods": [
            "scalar V/f",
            "vector control (rotor-flux)",
            "FOC",
            "FOC + field weakening",
            "direct torque control",
        ],
        "default_parameters": {
            "V_dc": 650.0,
            "I_max": 40.0,
            "k_e": 0.0,
            "R_phase": 0.55,
            "L_d": 0.045,
            "L_q": 0.045,
        },
        "tradeoffs": {
            "torque_density_nm_per_kg": {
                "min": 0.5,
                "typ": 2.0,
                "max": 6.0,
                "unit": "N-m/kg",
                "display": "Medium",
            },
            "torque_density_nm_per_l": {
                "min": 1.0,
                "typ": 6.0,
                "max": 18.0,
                "unit": "N-m/L",
                "display": "Medium",
            },
            "power_density_w_per_kg": {
                "min": 100.0,
                "typ": 900.0,
                "max": 3000.0,
                "unit": "W/kg",
                "display": "Medium",
            },
            "power_density_w_per_l": {
                "min": 250.0,
                "typ": 1600.0,
                "max": 6500.0,
                "unit": "W/L",
                "display": "Medium",
            },
            "peak_efficiency_percent": {
                "min": 75.0,
                "typ": 92.0,
                "max": 97.0,
                "unit": "%",
                "display": "75-97%",
            },
            "speed_range_rpm": {
                "min": 900.0,
                "typ": 3600.0,
                "max": 20000.0,
                "unit": "rpm",
                "display": "Broad with inverter drive",
            },
            "field_weakening_capability": {
                "min": 1.0,
                "typ": 2.0,
                "max": 3.0,
                "unit": "ordinal",
                "display": "Strong with vector control",
            },
            "cost_usd_per_kw": {
                "min": 30.0,
                "typ": 80.0,
                "max": 250.0,
                "unit": "$/kW",
                "display": "Low",
            },
            "control_complexity": {
                "min": 1.0,
                "typ": 3.0,
                "max": 5.0,
                "unit": "1-5",
                "display": "Low to high depending on drive",
            },
            "cogging_smoothness": {
                "min": 3.0,
                "typ": 4.0,
                "max": 5.0,
                "unit": "1-5",
                "display": "Smooth",
            },
            "audible_noise": {
                "min": 1.0,
                "typ": 3.0,
                "max": 5.0,
                "unit": "1-5",
                "display": "Hum and slot noise common",
            },
            "self_starting": {
                "min": 1.0,
                "typ": 2.0,
                "max": 2.0,
                "unit": "ordinal",
                "display": "Yes, if line-start design",
            },
            "position_sensor_requirement": {
                "min": 0.0,
                "typ": 1.0,
                "max": 2.0,
                "unit": "ordinal",
                "display": "Usually not required",
            },
            "power_factor": {
                "min": 0.55,
                "typ": 0.85,
                "max": 0.95,
                "unit": "cos(phi)",
                "display": "Load dependent",
            },
            "rotor_inertia": {
                "min": 2.0,
                "typ": 3.0,
                "max": 5.0,
                "unit": "1-5",
                "display": "Medium to high",
            },
            "magnet_content": {
                "min": 0.0,
                "typ": 0.0,
                "max": 0.0,
                "unit": "ordinal",
                "display": "None",
            },
            "continuous_peak_ratio": {
                "min": 0.40,
                "typ": 0.70,
                "max": 1.00,
                "unit": "ratio",
                "display": "Strong continuous-duty bias",
            },
        },
        "references": [
            "Chapman, Electric Machinery Fundamentals",
            "Boldea and Nasar, The Induction Machine Handbook",
            "Leonhard, Control of Electrical Drives",
        ],
    },
    "dc_brushed_pm": {
        "name": "DC Brushed - Permanent-Magnet Rotor Field",
        "short_name": "DC brushed",
        "family": "Commutator DC",
        "one_sentence": (
            "A brushed DC motor is the simplest torque-control mental model: "
            "voltage sets speed, current sets torque, and the mechanical "
            "commutator handles phase switching."
        ),
        "description": (
            "Permanent magnets provide the field while brushes and a commutator "
            "switch current through the armature windings. It is easy to drive "
            "from DC and excellent for building intuition, but brush wear, "
            "arcing, acoustic noise, and lower power density limit modern use."
        ),
        "distinguishing_facts": [
            "Torque is proportional to armature current in the simple linear model.",
            "Back-EMF rises with speed and naturally reduces current at light load.",
            "The commutator performs the switching that an inverter performs in brushless machines.",
            "Brush friction, wear, and arcing are the defining practical limitations.",
        ],
        "applications": [
            "toys",
            "low-cost actuators",
            "automotive auxiliary drives",
            "handheld tools",
            "educational demos",
        ],
        "pros": [
            "Very simple drive electronics",
            "Good low-speed torque",
            "Intuitive voltage-speed and current-torque behavior",
            "Low entry cost",
        ],
        "cons": [
            "Brush and commutator wear",
            "Electrical noise and arcing",
            "Lower peak efficiency than brushless alternatives",
            "Heat removal is harder from the rotating armature",
        ],
        "applicable_control_methods": [
            "voltage / PWM speed control",
            "current control",
            "closed-loop speed PI",
        ],
        "default_parameters": {
            "V_dc": 24.0,
            "I_max": 15.0,
            "k_e": 0.035,
            "R_phase": 0.25,
            "L_d": 0.001,
            "L_q": 0.001,
        },
        "tradeoffs": {
            "torque_density_nm_per_kg": {
                "min": 0.2,
                "typ": 0.9,
                "max": 2.5,
                "unit": "N-m/kg",
                "display": "Low to medium",
            },
            "torque_density_nm_per_l": {
                "min": 0.5,
                "typ": 3.0,
                "max": 8.0,
                "unit": "N-m/L",
                "display": "Low to medium",
            },
            "power_density_w_per_kg": {
                "min": 50.0,
                "typ": 400.0,
                "max": 1500.0,
                "unit": "W/kg",
                "display": "Low to medium",
            },
            "power_density_w_per_l": {
                "min": 100.0,
                "typ": 900.0,
                "max": 3500.0,
                "unit": "W/L",
                "display": "Low to medium",
            },
            "peak_efficiency_percent": {
                "min": 55.0,
                "typ": 75.0,
                "max": 90.0,
                "unit": "%",
                "display": "55-90%",
            },
            "speed_range_rpm": {
                "min": 1000.0,
                "typ": 6000.0,
                "max": 25000.0,
                "unit": "rpm",
                "display": "Brush and commutator limited",
            },
            "field_weakening_capability": {
                "min": 0.0,
                "typ": 0.0,
                "max": 1.0,
                "unit": "ordinal",
                "display": "Normally none for PM field",
            },
            "cost_usd_per_kw": {
                "min": 20.0,
                "typ": 80.0,
                "max": 250.0,
                "unit": "$/kW",
                "display": "Low",
            },
            "control_complexity": {
                "min": 1.0,
                "typ": 1.0,
                "max": 3.0,
                "unit": "1-5",
                "display": "Low",
            },
            "cogging_smoothness": {
                "min": 1.0,
                "typ": 2.0,
                "max": 4.0,
                "unit": "1-5",
                "display": "Commutation ripple present",
            },
            "audible_noise": {
                "min": 3.0,
                "typ": 4.0,
                "max": 5.0,
                "unit": "1-5",
                "display": "Brush noise and arcing",
            },
            "self_starting": {
                "min": 2.0,
                "typ": 2.0,
                "max": 2.0,
                "unit": "ordinal",
                "display": "Yes from DC supply",
            },
            "position_sensor_requirement": {
                "min": 0.0,
                "typ": 0.0,
                "max": 1.0,
                "unit": "ordinal",
                "display": "None for basic drive",
            },
            "power_factor": {
                "min": None,
                "typ": None,
                "max": None,
                "unit": "cos(phi)",
                "display": "N/A for DC supply",
                "not_applicable": True,
            },
            "rotor_inertia": {
                "min": 2.0,
                "typ": 3.0,
                "max": 5.0,
                "unit": "1-5",
                "display": "Medium to high",
            },
            "magnet_content": {
                "min": 1.0,
                "typ": 1.0,
                "max": 3.0,
                "unit": "ordinal",
                "display": "Ferrite or NdFeB stator magnets",
            },
            "continuous_peak_ratio": {
                "min": 0.25,
                "typ": 0.55,
                "max": 0.85,
                "unit": "ratio",
                "display": "Brush and armature thermal dependent",
            },
        },
        "references": [
            "Chapman, Electric Machinery Fundamentals",
            "Hughes and Drury, Electric Motors and Drives",
            "Boldea and Nasar, Electric Drives",
        ],
    },
}


def calculate_topology_overview(topology: str) -> dict[str, Any]:
    """
    Return the educational overview package for a selected motor topology.

    This is a database-backed lookup used by the first release skeleton. It
    returns prose, typical tradeoff ranges, controls, defaults, and references
    for the selected topology without running a predictive performance model.

    ---Parameters---
    topology : str
        Topology key in the motor database. Initial valid values are
        pmsm_spm, induction_squirrel_cage, and dc_brushed_pm.

    ---Returns---
    topology_key : str
        Canonical key for the selected topology.
    name : str
        Full display name for the selected topology.
    short_name : str
        Compact label suitable for navigation and badges.
    family : str
        Broad motor family for the selected topology.
    one_sentence : str
        High-level explanation of what distinguishes the topology.
    description : str
        Longer educational description of torque production and usage.
    distinguishing_facts : list
        Short facts that define the topology for a learner.
    applications : list
        Common real-world applications.
    pros : list
        Advantages of the topology.
    cons : list
        Limitations and caveats of the topology.
    applicable_control_methods : list
        Control methods that apply to the topology.
    default_parameters : dict
        Representative electrical parameters for later plots.
    tradeoffs : dict
        Typical-range data for the tradeoff dimensions.
    references : list
        Source texts used for the qualitative and typical-range data.

    ---LaTeX---
    Overview(topology) = MOTOR\\_TOPOLOGIES[topology]
    """
    if topology not in MOTOR_TOPOLOGIES:
        valid = ", ".join(MOTOR_TOPOLOGIES)
        raise ValueError(f"Unknown motor topology '{topology}'. Valid topologies: {valid}.")

    overview = deepcopy(MOTOR_TOPOLOGIES[topology])
    overview["topology_key"] = topology
    return overview
