"""Coefficient of friction reference data and lookup helpers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Comprehensive Coefficient of Friction Database
#
# This database provides static (mu_s) and kinetic (mu_k) coefficients of friction
# for various material pairs under different conditions.
#
# Data Structure:
# friction_data = {
#     'Material1': {
#         'Material2': {
#             'Condition': {
#                 'static': (min_mu_s, max_mu_s),
#                 'kinetic': (min_mu_k, max_mu_k),
#                 'source':
#             },
#             #... other conditions
#         },
#         #... other material pairs
#     },
#     #... other primary materials
# }
#
# Notes:
# - Material names are standardized and sorted alphabetically for consistent keying.
# - Coefficients are stored as tuples (min_val, max_val) to represent ranges.
#   For single values, min_val and max_val are the same.
# - 'None' indicates that no validated data was found for that coefficient type
#   under the specified condition in the reviewed sources.
# - 'source' lists the identifiers of the original data sources.
#
# Source placeholder citations:
# [35]: General value for PEEK 450G from multiple review papers on tribology.
# [36]: General value for PEEK/PTFE composites from multiple review papers.
# [37]: For CF-PEEK composites, dry, from various sources.
# [38]: For CF-PEEK composites, oil lubricated, from various sources.

RAW_FRICTION_DATA: Dict[str, Dict[str, Dict[str, Dict[str, object]]]] = {
    "Acrylic": {
        "Steel": {
            "Dry_Clean": {"static": (0.4, 0.5), "kinetic": None, "source": [26]},
        }
    },
    "Aluminum": {
        "Aluminum": {
            "Dry_Clean": {"static": (1.05, 1.35), "kinetic": (0.4, 1.4), "source": [7]},
            "Lubricated": {"static": (0.3, 0.3), "kinetic": None, "source": [7]},
        },
        "Mild Steel": {
            "Dry_Clean": {"static": (0.61, 0.61), "kinetic": (0.47, 0.47), "source": [7, 10]},
        },
        "Pine Wood": {
            "Dry_Clean": {"static": (0.22, 0.22), "kinetic": None, "source": [30]},
        },
    },
    "Aluminum Alloy (6061-T6)": {
        "Titanium Alloy (Ti-6Al-4V)": {
            "Dry_Clean": {
                "static": (0.41, 0.41),
                "kinetic": (0.38, 0.38),
                "source": [18, 31],
            }
        }
    },
    "Aluminum-Bronze Alloy": {
        "Steel": {
            "Dry_Clean": {"static": (0.46, 0.46), "kinetic": None, "source": [5]},
        }
    },
    "Asphalt": {
        "Rubber": {
            "Dry_Clean": {"static": (0.68, 0.9), "kinetic": (0.5, 0.8), "source": [7]},
            "Wet": {"static": None, "kinetic": (0.25, 0.75), "source": [7]},
        }
    },
    "Bone": {
        "Synovial Fluid": {
            "Lubricated": {
                "static": (0.016, 0.016),
                "kinetic": (0.015, 0.015),
                "source": [2],
            }
        }
    },
    "Brake Material": {
        "Cast Iron": {
            "Dry_Clean": {"static": (0.4, 0.4), "kinetic": (0.3, 0.3), "source": [5, 19]},
            "Wet": {"static": (0.2, 0.2), "kinetic": None, "source": [19, 32]},
        }
    },
    "Brass": {
        "Cast Iron": {
            "Dry_Clean": {"static": (0.28, 0.3), "kinetic": None, "source": [5, 17]},
        },
        "Steel": {
            "Dry_Clean": {"static": (0.5, 0.51), "kinetic": (0.44, 0.44), "source": [5, 7]},
            "Lubricated": {"static": (0.11, 0.19), "kinetic": None, "source": [7]},
        },
    },
    "Brick": {
        "Wood": {
            "Dry_Clean": {"static": (0.6, 0.6), "kinetic": None, "source": [5, 7]},
        }
    },
    "Bronze": {
        "Cast Iron": {
            "Dry_Clean": {"static": (0.21, 0.22), "kinetic": None, "source": [5, 17]},
        },
        "Steel": {
            "Lubricated": {"static": None, "kinetic": (0.16, 0.17), "source": [5]},
        },
        "Titanium Alloy (Ti-6Al-4V)": {
            "Dry_Clean": {
                "static": (0.36, 0.36),
                "kinetic": (0.27, 0.27),
                "source": [18],
            }
        },
    },
    "Bronze, Sintered": {
        "Steel": {
            "Lubricated": {"static": None, "kinetic": (0.12, 0.13), "source": [5, 19]},
        }
    },
    "Cadmium": {
        "Cadmium": {
            "Dry_Clean": {"static": (0.5, 0.5), "kinetic": None, "source": [5]},
            "Lubricated": {"static": (0.05, 0.05), "kinetic": None, "source": [5]},
        },
        "Chromium": {
            "Dry_Clean": {"static": (0.4, 0.41), "kinetic": None, "source": [5, 19]},
            "Lubricated": {"static": (0.34, 0.35), "kinetic": None, "source": [5, 19]},
        },
        "Mild Steel": {
            "Dry_Clean": {"static": (0.46, 0.46), "kinetic": None, "source": [5, 17]},
        },
    },
    "Carbon": {
        "Carbon": {
            "Dry_Clean": {"static": (0.15, 0.16), "kinetic": None, "source": [5, 19]},
            "Lubricated": {"static": (0.12, 0.14), "kinetic": None, "source": [5, 19]},
        },
        "Steel": {
            "Dry_Clean": {"static": (0.14, 0.14), "kinetic": None, "source": [5, 19]},
            "Lubricated": {"static": (0.11, 0.14), "kinetic": None, "source": [5, 19]},
        },
    },
    "Cast Iron": {
        "Cast Iron": {
            "Dry_Clean": {"static": (1.1, 1.1), "kinetic": (0.15, 0.15), "source": [5, 7]},
            "Lubricated_Grease": {"static": None, "kinetic": (0.07, 0.07), "source": [7]},
        },
        "Copper": {
            "Dry_Clean": {"static": (1.05, 1.05), "kinetic": (0.29, 0.29), "source": [5, 7]},
        },
        "Lead": {
            "Dry_Clean": {"static": None, "kinetic": (0.43, 0.43), "source": [6, 12]},
        },
        "Leather": {
            "Dry_Clean": {"static": (0.6, 0.6), "kinetic": (0.56, 0.56), "source": [7, 25]},
        },
        "Mild Steel": {
            "Dry_Clean": {"static": None, "kinetic": (0.23, 0.23), "source": [6, 12]},
            "Lubricated_Castor_Oil": {
                "static": None,
                "kinetic": (0.133, 0.183),
                "source": [6, 12],
            },
        },
        "Oak": {
            "Dry_Clean": {"static": (0.485, 0.49), "kinetic": None, "source": [5, 17]},
            "Lubricated": {"static": (0.075, 0.08), "kinetic": None, "source": [5, 17]},
        },
        "Paper": {
            "Dry_Clean": {"static": (0.19, 0.19), "kinetic": None, "source": [5]},
        },
        "Steel": {
            "Dry_Clean": {"static": (0.4, 0.4), "kinetic": (0.21, 0.23), "source": [5, 7]},
        },
        "Tin": {
            "Dry_Clean": {"static": None, "kinetic": (0.32, 0.32), "source": [6, 12]},
        },
        "Zinc": {
            "Dry_Clean": {"static": (0.85, 0.85), "kinetic": (0.21, 0.21), "source": [5, 33]},
        },
    },
    "Chromium": {
        "Chromium": {
            "Dry_Clean": {"static": (0.41, 0.41), "kinetic": None, "source": [5]},
            "Lubricated": {"static": (0.34, 0.34), "kinetic": None, "source": [5]},
        }
    },
    "Cobalt": {
        "Cobalt": {
            "Dry_Clean": {
                "static": (0.3, 0.3),
                "kinetic": None,
                "source": [5],
                "notes": "At 70°C",
            }
        }
    },
    "Concrete": {
        "Horseshoe": {
            "Dry_Clean": {"static": (0.67, 0.67), "kinetic": None, "source": [5]},
        },
        "Rubber": {
            "Dry_Clean": {"static": (0.9, 1.0), "kinetic": (0.6, 0.85), "source": [2, 5]},
            "Wet": {"static": (0.3, 0.7), "kinetic": (0.25, 0.75), "source": [2, 7]},
        },
        "Wood": {
            "Dry_Clean": {"static": (0.62, 0.62), "kinetic": None, "source": [5]},
        },
    },
    "Copper": {
        "Copper": {
            "Dry_Clean": {"static": (1.0, 1.6), "kinetic": None, "source": [5, 7]},
            "Lubricated_Grease": {"static": (0.08, 0.08), "kinetic": None, "source": [5, 7]},
            "Dry_Oxide_Film": {"static": (0.76, 0.76), "kinetic": None, "source": [13, 14]},
            "Dry_Sulfide_Film": {"static": (0.74, 0.74), "kinetic": None, "source": [13, 14]},
        },
        "Glass": {
            "Dry_Clean": {"static": (0.68, 0.94), "kinetic": (0.53, 0.53), "source": [5, 7]},
        },
        "Mild Steel": {
            "Dry_Clean": {"static": (0.53, 0.53), "kinetic": (0.36, 0.36), "source": [7, 12]},
            "Lubricated_Oleic_Acid": {
                "static": None,
                "kinetic": (0.18, 0.18),
                "source": [6, 12],
            },
        },
        "Steel": {
            "Dry_Clean": {"static": (0.53, 0.53), "kinetic": (0.36, 0.36), "source": [7, 10]},
        },
        "Tungsten Carbide": {
            "Dry_Clean": {"static": (0.35, 0.35), "kinetic": None, "source": [6, 19]},
        },
    },
    "Copper-Lead Alloy": {
        "Steel": {
            "Dry_Clean": {"static": (0.22, 0.22), "kinetic": None, "source": [5]},
        }
    },
    "Cork": {
        "Iron": {
            "Dry_Clean": {"static": (0.35, 0.35), "kinetic": None, "source": [5]},
        }
    },
    "Diamond": {
        "Diamond": {
            "Dry_Clean": {"static": (0.1, 0.1), "kinetic": None, "source": [5]},
            "Lubricated": {"static": (0.05, 0.1), "kinetic": None, "source": [5]},
        },
        "Metal": {
            "Dry_Clean": {"static": (0.1, 0.15), "kinetic": None, "source": [5]},
            "Lubricated": {"static": (0.1, 0.1), "kinetic": None, "source": [5]},
        },
    },
    "Glass": {
        "Glass": {
            "Dry_Clean": {"static": (0.9, 1.0), "kinetic": (0.4, 0.4), "source": [5, 7]},
            "Lubricated_Grease": {"static": (0.1, 0.6), "kinetic": (0.09, 0.12), "source": [7]},
            "Vacuum": {"static": (0.5, 0.5), "kinetic": None, "source": [20]},
        },
        "Metal": {
            "Dry_Clean": {"static": (0.5, 0.7), "kinetic": None, "source": [5, 7]},
            "Lubricated_Grease": {"static": (0.2, 0.3), "kinetic": None, "source": [5, 7]},
        },
        "Nickel": {
            "Dry_Clean": {"static": (0.78, 0.78), "kinetic": (0.56, 0.57), "source": [5, 12]},
        },
    },
    "Graphite": {
        "Graphite": {
            "Dry_Clean": {"static": (0.1, 0.1), "kinetic": None, "source": [5, 7]},
            "Vacuum": {"static": (0.5, 0.8), "kinetic": None, "source": [7, 19]},
        },
        "Steel": {
            "Dry_Clean": {
                "static": (0.1, 0.1),
                "kinetic": None,
                "source": [5, 7],
                "notes": "Solid Lubricant",
            }
        },
    },
    "Hard Steel": {
        "Babbitt (ASTM 1)": {
            "Dry_Clean": {"static": (0.7, 0.7), "kinetic": (0.33, 0.33), "source": [6, 12]},
            "Lubricated": {
                "static": (0.08, 0.23),
                "kinetic": (0.06, 0.16),
                "source": [6, 12],
                "notes": "Various Oils",
            },
        },
        "Graphite": {
            "Dry_Clean": {"static": (0.21, 0.21), "kinetic": None, "source": [6, 12]},
        },
        "Hard Steel": {
            "Dry_Clean": {"static": (0.78, 0.78), "kinetic": (0.42, 0.42), "source": [6, 12]},
            "Lubricated": {
                "static": (0.0052, 0.23),
                "kinetic": (0.029, 0.12),
                "source": [6, 12],
                "notes": "Various Oils/Greases",
            },
        },
    },
    "Hemp Rope": {
        "Wood": {
            "Dry_Clean": {"static": None, "kinetic": (0.4, 0.7), "source": [5]},
        }
    },
    "Horseshoe": {
        "Rubber": {
            "Dry_Clean": {"static": (0.28, 0.28), "kinetic": None, "source": [5]},
        }
    },
    "Human Skin": {
        "Metal": {
            "Dry_Clean": {"static": (0.8, 1.0), "kinetic": None, "source": [5, 34]},
        }
    },
    "Ice": {
        "Ice": {
            "Dry_Clean": {
                "static": (0.1, 0.5),
                "kinetic": (0.02, 0.09),
                "source": [2, 7],
                "notes": "Temperature Dependent (-80°C to 0°C)",
            }
        },
        "Steel": {
            "Dry_Clean": {"static": (0.03, 0.04), "kinetic": (0.01, 0.02), "source": [2, 7]},
        },
        "Wood": {
            "Dry_Clean": {"static": (0.05, 0.05), "kinetic": None, "source": [5, 7]},
        },
    },
    "Iron": {
        "Iron": {
            "Dry_Clean": {"static": (1.0, 1.0), "kinetic": None, "source": [5, 7]},
            "Lubricated_Grease": {"static": (0.15, 0.2), "kinetic": None, "source": [5, 7]},
        },
        "Tungsten Carbide": {
            "Dry_Clean": {"static": (0.8, 0.8), "kinetic": None, "source": [6, 19]},
        },
    },
    "Leather": {
        "Metal": {
            "Dry_Clean": {"static": (0.4, 0.6), "kinetic": None, "source": [5, 7]},
            "Lubricated": {"static": (0.2, 0.2), "kinetic": None, "source": [19, 25]},
        },
        "Oak": {
            "Dry_Clean": {
                "static": (0.61, 0.61),
                "kinetic": (0.52, 0.52),
                "source": [7, 12],
                "notes": "Parallel to Grain",
            }
        },
        "Wood": {
            "Dry_Clean": {"static": (0.3, 0.4), "kinetic": None, "source": [5, 25]},
        },
    },
    "Magnesium": {
        "Magnesium": {
            "Dry_Clean": {"static": (0.6, 0.6), "kinetic": None, "source": [5]},
            "Lubricated": {"static": (0.079, 0.08), "kinetic": None, "source": [5, 6]},
        }
    },
    "Metal": {
        "Wood": {
            "Dry_Clean": {"static": (0.2, 0.6), "kinetic": (0.3, 0.3), "source": [2, 7]},
            "Wet": {"static": (0.2, 0.2), "kinetic": None, "source": [7, 19]},
        }
    },
    "Mild Steel": {
        "Brass": {
            "Dry_Clean": {"static": (0.51, 0.51), "kinetic": (0.44, 0.44), "source": [6, 12]},
        },
        "Copper": {
            "Dry_Clean": {"static": (0.53, 0.53), "kinetic": (0.36, 0.36), "source": [6, 12]},
        },
        "Lead": {
            "Dry_Clean": {"static": (0.95, 0.95), "kinetic": (0.95, 0.95), "source": [6, 12]},
            "Lubricated_Mineral_Oil": {
                "static": (0.5, 0.5),
                "kinetic": (0.3, 0.3),
                "source": [6, 12],
            },
        },
        "Mild Steel": {
            "Dry_Clean": {"static": (0.74, 0.74), "kinetic": (0.57, 0.57), "source": [6, 12]},
            "Lubricated_Oleic_Acid": {
                "static": None,
                "kinetic": (0.09, 0.09),
                "source": [6, 12],
            },
        },
        "Nickel": {
            "Dry_Clean": {"static": None, "kinetic": (0.64, 0.64), "source": [6, 12]},
        },
        "Phosphor Bronze": {
            "Dry_Clean": {"static": None, "kinetic": (0.34, 0.34), "source": [6, 12]},
            "Lubricated_Mineral_Oil": {
                "static": None,
                "kinetic": (0.173, 0.173),
                "source": [6, 12],
            },
        },
    },
    "Nickel": {
        "Nickel": {
            "Dry_Clean": {"static": (0.7, 1.1), "kinetic": (0.53, 0.53), "source": [5, 7]},
            "Lubricated_Grease": {"static": (0.28, 0.28), "kinetic": (0.12, 0.12), "source": [7, 12]},
        }
    },
    "Nylon": {
        "Nylon": {
            "Dry_Clean": {"static": (0.15, 0.25), "kinetic": None, "source": [5, 7]},
        },
        "Steel": {
            "Dry_Clean": {"static": (0.4, 0.4), "kinetic": None, "source": [7]},
        },
    },
    "Oak": {
        "Oak": {
            "Dry_Clean": {
                "static": (0.62, 0.62),
                "kinetic": (0.48, 0.48),
                "source": [7, 12],
                "notes": "Parallel to Grain",
            },
            "Dry_Clean_Cross_Grain": {
                "static": (0.54, 0.54),
                "kinetic": (0.32, 0.32),
                "source": [7],
            },
        }
    },
    "PEEK": {
        "Steel": {
            "Dry_Clean": {
                "static": (0.4, 0.6),
                "kinetic": (0.4, 0.6),
                "source": [35],
                "notes": "For PEEK 450G. Highly dependent on temp, pressure, and speed."
            },
        }
    },
    "PEEK, Carbon-Fiber-filled": {
        "Steel": {
            "Dry_Clean": {
                "static": (0.2, 0.2),
                "kinetic": (0.2, 0.2),
                "source": [37]
            },
            "Lubricated_Oil": {
                "static": (0.03, 0.07),
                "kinetic": (0.03, 0.07),
                "source": [38]
            }
        }
    },
    "PEEK, PTFE-filled": {
        "Steel": {
            "Dry_Clean": {
                "static": (0.12, 0.15),
                "kinetic": (0.12, 0.15),
                "source": [36],
                "notes": "PTFE acts as a solid lubricant."
            },
        }
    },
    "Phosphor Bronze": {
        "Steel": {
            "Dry_Clean": {"static": (0.35, 0.35), "kinetic": None, "source": [5]},
        }
    },
    "Platinum": {
        "Platinum": {
            "Dry_Clean": {"static": (1.2, 1.2), "kinetic": None, "source": [5, 7]},
            "Lubricated_Grease": {"static": (0.25, 0.25), "kinetic": None, "source": [7]},
        }
    },
    "Plexiglas": {
        "Plexiglas": {
            "Dry_Clean": {"static": (0.8, 0.8), "kinetic": None, "source": [5, 7]},
        },
        "Steel": {
            "Dry_Clean": {"static": (0.4, 0.5), "kinetic": None, "source": [5, 7]},
        },
    },
    "Polyethylene": {
        "Polyethylene": {
            "Dry_Clean": {"static": (0.2, 0.2), "kinetic": None, "source": [7]},
        },
        "Steel": {
            "Dry_Clean": {"static": (0.2, 0.2), "kinetic": None, "source": [5, 7]},
        },
    },
    "Polystyrene": {
        "Polystyrene": {
            "Dry_Clean": {"static": (0.5, 0.5), "kinetic": None, "source": [5, 7]},
        },
        "Steel": {
            "Dry_Clean": {"static": (0.3, 0.35), "kinetic": None, "source": [5, 7]},
        },
    },
    "PTFE": {
        "PTFE": {
            "Dry_Clean": {"static": (0.04, 0.2), "kinetic": (0.04, 0.04), "source": [5, 7]},
        },
        "Steel": {
            "Dry_Clean": {"static": (0.04, 0.2), "kinetic": (0.04, 0.04), "source": [5, 7]},
        },
    },
    "Rubber": {
        "Rubber": {
            "Dry_Clean": {"static": (1.16, 1.16), "kinetic": None, "source": [7]},
        }
    },
    "Sapphire": {
        "Sapphire": {
            "Dry_Clean": {"static": (0.2, 0.2), "kinetic": None, "source": [19, 32]},
        }
    },
    "Shoes": {
        "Ice": {
            "Dry_Clean": {"static": (0.1, 0.1), "kinetic": (0.05, 0.05), "source": [2]},
        },
        "Wood": {
            "Dry_Clean": {"static": (0.9, 0.9), "kinetic": (0.7, 0.7), "source": [2]},
        },
    },
    "Silver": {
        "Silver": {
            "Dry_Clean": {"static": (1.4, 1.4), "kinetic": None, "source": [5, 7]},
            "Lubricated_Grease": {"static": (0.55, 0.55), "kinetic": None, "source": [7]},
        }
    },
    "Snow": {
        "Wood": {
            "Wet": {
                "static": (0.14, 0.14),
                "kinetic": (0.1, 0.1),
                "source": [2, 7],
                "notes": "Waxed Wood at 0°C",
            },
            "Dry": {
                "static": None,
                "kinetic": (0.04, 0.04),
                "source": [2, 7],
                "notes": "Waxed Wood",
            },
        }
    },
    "Steel": {
        "Steel": {
            "Dry_Clean": {"static": (0.5, 0.8), "kinetic": (0.42, 0.57), "source": [5, 7]},
            "Lubricated_Grease": {"static": (0.16, 0.16), "kinetic": (0.07, 0.08), "source": [5, 7]},
            "Lubricated_Oil": {"static": (0.05, 0.23), "kinetic": (0.03, 0.16), "source": [2, 7]},
            "Dry_Oxide_Film": {"static": (0.27, 0.27), "kinetic": None, "source": [13, 14]},
            "Dry_Sulfide_Film": {"static": (0.39, 0.39), "kinetic": None, "source": [13, 14]},
        },
        "Titanium Alloy (Ti-6Al-4V)": {
            "Dry_Clean": {"static": (0.36, 0.36), "kinetic": (0.31, 0.31), "source": [9]},
        },
        "Tungsten Carbide": {
            "Dry_Clean": {"static": (0.4, 0.6), "kinetic": None, "source": [5, 7]},
            "Lubricated": {"static": (0.1, 0.2), "kinetic": None, "source": [19, 34]},
        },
    },
    "Titanium Alloy (Ti-6Al-4V)": {
        "Titanium Alloy (Ti-6Al-4V)": {
            "Dry_Clean": {"static": (0.36, 0.36), "kinetic": (0.3, 0.3), "source": [18]}
        }
    },
    "Tungsten Carbide": {
        "Tungsten Carbide": {
            "Dry_Clean": {"static": (0.2, 0.25), "kinetic": None, "source": [6, 19]},
            "Lubricated": {"static": (0.12, 0.12), "kinetic": None, "source": [6, 19]},
        }
    },
    "Wood": {
        "Wood": {
            "Dry_Clean": {"static": (0.25, 0.5), "kinetic": (0.2, 0.3), "source": [2, 7]},
            "Wet": {"static": (0.2, 0.2), "kinetic": None, "source": [7, 19]},
        }
    },
    "Zinc": {
        "Zinc": {
            "Dry_Clean": {"static": (0.6, 0.6), "kinetic": None, "source": [5]},
            "Lubricated": {"static": (0.04, 0.04), "kinetic": None, "source": [5]},
        }
    },
}


@dataclass
class ConditionRecord:
    """Container for friction data under a specific surface condition."""

    slug: str
    display_name: str
    raw_name: str
    static_min: Optional[float]
    static_max: Optional[float]
    static_typical: Optional[float]
    kinetic_min: Optional[float]
    kinetic_max: Optional[float]
    kinetic_typical: Optional[float]
    notes: str
    sources: Tuple[int, ...]
    reference: str
    applications: List[str]
    comparables: List[str]


@dataclass
class PairRecord:
    """Container describing a material pairing."""

    material_slugs: Tuple[str, str]
    material_names: Tuple[str, str]
    label: str
    conditions: Dict[str, ConditionRecord]


def _slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "material"


def _alias_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _condition_display(raw_name: str) -> str:
    cleaned = raw_name.replace("_", " ").replace("-", " ").strip()
    if not cleaned:
        return "Unspecified"
    return " ".join(word.capitalize() for word in cleaned.split())


def _parse_range(values: Optional[Tuple[Optional[float], Optional[float]]]) -> Tuple[Optional[float], Optional[float]]:
    if values is None:
        return (None, None)
    low, high = values
    low_val = float(low) if low is not None else None
    high_val = float(high) if high is not None else None
    return (low_val, high_val)


def _typical_from_range(range_values: Tuple[Optional[float], Optional[float]]) -> Optional[float]:
    low, high = range_values
    if low is None and high is None:
        return None
    if low is None:
        return high
    if high is None:
        return low
    return (low + high) / 2.0


def _format_reference(sources: Tuple[int, ...]) -> str:
    if not sources:
        return "Source IDs: not specified"
    unique = sorted(set(sources))
    joined = ", ".join(str(entry) for entry in unique)
    return f"Source IDs: {joined}"


MATERIALS: Dict[str, Dict[str, object]] = {}
ALIAS_LOOKUP: Dict[str, str] = {}
PAIR_DATABASE: Dict[Tuple[str, str], PairRecord] = {}


def _register_material(name: str) -> str:
    slug = _slugify(name)
    if slug not in MATERIALS:
        MATERIALS[slug] = {
            "name": name,
            "category": "Materials",
            "summary": "",
            "aliases": set(),
        }
    MATERIALS[slug]["aliases"].add(name)

    candidates = {
        name,
        name.lower(),
        name.upper(),
        name.replace(" ", ""),
        name.replace(" ", "_"),
        name.replace("-", ""),
        slug,
        slug.replace("_", ""),
    }

    for candidate in candidates:
        key = candidate.strip()
        if not key:
            continue
        ALIAS_LOOKUP[key.lower()] = slug
        alias = _alias_key(candidate)
        if alias:
            ALIAS_LOOKUP[alias] = slug

    return slug


def _build_database() -> None:
    for primary_name, partners in RAW_FRICTION_DATA.items():
        primary_slug = _register_material(primary_name)

        for secondary_name, condition_map in partners.items():
            secondary_slug = _register_material(secondary_name)

            pair_key = tuple(sorted((primary_slug, secondary_slug)))
            if pair_key not in PAIR_DATABASE:
                material_names = (
                    MATERIALS[pair_key[0]]["name"],
                    MATERIALS[pair_key[1]]["name"],
                )
                PAIR_DATABASE[pair_key] = PairRecord(
                    material_slugs=pair_key,
                    material_names=material_names,
                    label=f"{material_names[0]} vs {material_names[1]}",
                    conditions={},
                )

            pair_record = PAIR_DATABASE[pair_key]

            for raw_condition, values in condition_map.items():
                condition_slug = _slugify(raw_condition)
                static_range = _parse_range(values.get("static"))
                kinetic_range = _parse_range(values.get("kinetic"))
                notes = str(values.get("notes") or "").strip()
                sources = tuple(int(entry) for entry in values.get("source") or [])

                record = ConditionRecord(
                    slug=condition_slug,
                    display_name=_condition_display(raw_condition),
                    raw_name=raw_condition,
                    static_min=static_range[0],
                    static_max=static_range[1],
                    static_typical=_typical_from_range(static_range),
                    kinetic_min=kinetic_range[0],
                    kinetic_max=kinetic_range[1],
                    kinetic_typical=_typical_from_range(kinetic_range),
                    notes=notes,
                    sources=sources,
                    reference=_format_reference(sources),
                    applications=[],
                    comparables=[],
                )

                pair_record.conditions[condition_slug] = record

    # Finalise material summaries and alias lists.
    participation_counts: Dict[str, int] = {slug: 0 for slug in MATERIALS}
    for pair in PAIR_DATABASE.values():
        for slug in pair.material_slugs:
            participation_counts[slug] += 1

    for slug, meta in MATERIALS.items():
        meta["aliases"] = sorted(set(meta["aliases"]))  # type: ignore[assignment]
        count = participation_counts.get(slug, 0)
        meta["summary"] = (
            f"Appears in {count} recorded contact pair{'s' if count != 1 else ''}."
            if count
            else "Reference material from the friction dataset."
        )


_build_database()


def _describe_range(symbol: str, low: Optional[float], high: Optional[float]) -> str:
    if low is None and high is None:
        return f"{symbol} unavailable"
    if low is None:
        return f"{symbol} ≈ {high:.2f}"
    if high is None:
        return f"{symbol} ≈ {low:.2f}"
    if abs(high - low) < 1e-6:
        return f"{symbol} ≈ {low:.2f}"
    return f"{symbol} range {low:.2f}–{high:.2f}"


def _infer_applications(pair: PairRecord, condition: ConditionRecord) -> List[str]:
    names = {name.lower() for name in pair.material_names}
    applications: List[str] = []
    cond = condition.display_name.lower()

    def has(keyword: str) -> bool:
        return any(keyword in name for name in names)

    def has_all(*keywords: str) -> bool:
        return all(has(keyword) for keyword in keywords)

    def add(message: str) -> None:
        if message not in applications:
            applications.append(message)

    if has("rubber") and (has("concrete") or has("asphalt")):
        add("Roadway traction analysis for tires, treads, or elastomer drive wheels.")
        add("Safety and braking studies on paved or concrete surfaces under varying moisture.")
    elif has("rubber") and has("steel"):
        add("Drive roller and pinch-wheel sizing for material-handling equipment.")
        add("Friction checks for elastomer-coated steel drums and clutches.")
    elif has("ptfe"):
        add("Dry-running bushings and wear strips where ultra-low friction is required.")
        add("Chemical-resistant slide bearings in laboratory or food equipment.")
    elif (has("bronze") and has("steel")) or has("phosphor bronze"):
        add("Plain bearing and bushing design when pairing bronze against steel shafts.")
        add("Machine ways or guides demanding non-galling, low-maintenance contact.")
    elif has("brass") and has("steel"):
        add("Instrument cams and sliders where brass shoes run on polished steel.")
        add("Light-duty lead screws and reciprocating guides with boundary lubrication.")
    elif has("cast iron") and has("steel"):
        add("Machine tool slideways and ways in milling or grinding machines.")
        add("Dry clutch and brake interfaces using cast iron pressure plates.")
    elif has("steel") and len(names) == 1:
        add("Bolted joint slip-factor checks and structural steel friction joints.")
        add("Brake disc, clutch, and emergency dry-running bearing analyses.")
    elif has("graphite"):
        add("Solid lubricant liners or brushes in electrical and mechanical systems.")
        add("Dry-film lubrication design where oil or grease is impractical.")
    elif has("wood") and has("steel"):
        add("Handling equipment and rigging where timber contacts steel hardware.")
        add("Historic machinery restorations using wood-on-steel slide interfaces.")
    elif has_all("wood"):
        add("Furniture slides, clamps, and woodworking fixture design assumptions.")
        add("Heritage mechanism restorations needing wood-on-wood friction data.")
    elif has("leather"):
        add("Band brake and clutch strap design using leather facing materials.")
        add("Grip analysis for leather belting and footwear against mating surfaces.")
    elif has("ice"):
        add("Winter traction and skate or ski performance modelling.")
        add("Cold-environment handling equipment and footwear design.")
    elif has("glass"):
        add("Optics handling fixtures and high-precision positioning stages.")
        add("Vacuum pick-and-place systems for glass substrates and wafers.")
    elif has("copper") and has("steel"):
        add("Sliding electrical contacts such as commutators or grounding brushes.")
        add("Guides and wear plates in corrosive environments needing copper alloys.")
    elif has("aluminum") and has("steel"):
        add("Structural slide joints or telescoping assemblies incorporating aluminum.")
        add("Design of mixed-metal mechanisms with risk of galling or adhesion.")

    if not applications:
        add(
            f"General friction benchmarking for {pair.label.lower()} under {condition.display_name.lower()} contact."
        )
        add("Use as an initial design reference when selecting safety factors or lubricants.")

    return applications


def _generate_context() -> None:
    registry: List[Tuple[PairRecord, ConditionRecord]] = []
    for pair in PAIR_DATABASE.values():
        for condition in pair.conditions.values():
            registry.append((pair, condition))

    value_table: List[Tuple[PairRecord, ConditionRecord, Optional[float], str]] = []
    for pair, condition in registry:
        value = condition.static_typical
        label = "μ_s"
        if value is None and condition.kinetic_typical is not None:
            value = condition.kinetic_typical
            label = "μ_k"
        value_table.append((pair, condition, value, label))

    for idx, (pair, condition, value, label) in enumerate(value_table):
        if value is not None:
            candidates = [
                (other_pair, other_condition, other_value, other_label)
                for jdx, (other_pair, other_condition, other_value, other_label) in enumerate(value_table)
                if jdx != idx and other_value is not None
            ]
            candidates.sort(key=lambda entry: abs(entry[2] - value))
            comparables: List[str] = []
            for other_pair, other_condition, other_value, other_label in candidates[:3]:
                comparables.append(
                    f"{other_pair.label} — {other_condition.display_name} ({other_label} ≈ {other_value:.2f})"
                )
            condition.comparables = comparables
        else:
            condition.comparables = []

        applications = _infer_applications(pair, condition)
        condition.applications = applications

        static_desc = _describe_range("μ_s", condition.static_min, condition.static_max)
        kinetic_desc = _describe_range("μ_k", condition.kinetic_min, condition.kinetic_max)
        summary = f"{condition.display_name} contact: {static_desc}; {kinetic_desc}."
        if condition.notes:
            combined = f"{condition.notes} {summary}"
        else:
            combined = summary
        condition.notes = combined.strip()


_generate_context()


def _normalize_material(name: str) -> str:
    if not name or not name.strip():
        raise ValueError("Material name cannot be empty.")

    candidates = [
        name,
        name.strip(),
        name.lower(),
        name.upper(),
        _slugify(name),
        name.replace(" ", ""),
        name.replace("-", ""),
        name.replace("_", ""),
    ]

    for candidate in candidates:
        lowered = candidate.lower()
        alias = _alias_key(candidate)
        slug = ALIAS_LOOKUP.get(lowered) or ALIAS_LOOKUP.get(alias)
        if slug:
            return slug
        if lowered in MATERIALS:
            return lowered
        if alias in MATERIALS:
            return alias

    slug_candidate = _slugify(name)
    if slug_candidate in MATERIALS:
        return slug_candidate

    raise ValueError(f"Unknown material '{name}'.")


def _normalize_condition(pair: PairRecord, condition: str) -> ConditionRecord:
    slug = _slugify(condition)
    if slug in pair.conditions:
        return pair.conditions[slug]

    alias = _alias_key(condition)
    for record in pair.conditions.values():
        if _alias_key(record.raw_name) == alias or _alias_key(record.display_name) == alias:
            return record

    available = ", ".join(sorted(rec.display_name for rec in pair.conditions.values()))
    raise ValueError(
        f"Surface condition '{condition}' not available for {pair.label}. "
        f"Choose from: {available}"
    )


def lookup_coefficient_of_friction(
    material_a: str,
    material_b: str,
    surface_condition: str,
) -> Dict[str, object]:
    """
    Retrieve reference coefficients of friction for a specified material pairing.

    Values are representative ranges compiled from a consolidated handbook
    dataset. Use them for preliminary design and verification; laboratory
    testing should confirm performance-critical applications.

    ---Parameters---
    material_a : str
        Identifier of the first surface. Use keys from `get_friction_catalog`.
    material_b : str
        Identifier of the mating surface. Order is ignored during lookup.
    surface_condition : str
        Operating condition (for example `Dry Clean` or `Lubricated`) matching
        the available dataset entries for the selected material pair.

    ---Returns---
    material_a_name : str
        Descriptive name of the first surface drawn from the dataset.
    material_b_name : str
        Descriptive name of the second surface drawn from the dataset.
    surface_condition : str
        Normalized surface condition that defines the returned data.
    mu_static_min : float
        Lower bound of the static coefficient of friction (dimensionless).
    mu_static_max : float
        Upper bound of the static coefficient of friction (dimensionless).
    mu_static_typical : float
        Typical static coefficient of friction (mid-point of the range).
    mu_kinetic_min : float
        Lower bound of the kinetic (sliding) coefficient of friction.
    mu_kinetic_max : float
        Upper bound of the kinetic (sliding) coefficient of friction.
    mu_kinetic_typical : float
        Typical kinetic coefficient suitable for steady-state analyses.
    notes : str
        Contextual guidance about assumptions, caveats, or influencing factors.
    typical_applications : list[str]
        Representative use cases where the material pairing is encountered.
    comparable_pairs : list[str]
        Alternative pairings with similar friction performance for comparison.
    reference : str
        Primary references that supplied the quoted coefficient range.

    ---LaTeX---
    \\mu = \\frac{F_{\\mathrm{tangential}}}{F_{\\mathrm{normal}}}
    \\quad \\text{and} \\quad \\mu_k \\lesssim \\mu_s
    """

    slug_a = _normalize_material(material_a)
    slug_b = _normalize_material(material_b)

    pair_key = tuple(sorted((slug_a, slug_b)))
    if pair_key not in PAIR_DATABASE:
        available_pairs = ", ".join(
            f"{MATERIALS[a]['name']} & {MATERIALS[b]['name']}"
            for (a, b) in sorted(PAIR_DATABASE.keys())
        )
        raise ValueError(
            f"No friction data for "
            f"{MATERIALS[slug_a]['name']} against {MATERIALS[slug_b]['name']}. "
            f"Available pairings: {available_pairs}"
        )

    pair = PAIR_DATABASE[pair_key]
    condition_record = _normalize_condition(pair, surface_condition)

    material_a_name = MATERIALS[slug_a]["name"]
    material_b_name = MATERIALS[slug_b]["name"]
    notes = condition_record.notes or "No additional notes provided."

    return {
        "material_a_name": material_a_name,
        "material_b_name": material_b_name,
        "surface_condition": condition_record.display_name,
        "mu_static_min": condition_record.static_min,
        "mu_static_max": condition_record.static_max,
        "mu_static_typical": condition_record.static_typical,
        "mu_kinetic_min": condition_record.kinetic_min,
        "mu_kinetic_max": condition_record.kinetic_max,
        "mu_kinetic_typical": condition_record.kinetic_typical,
        "notes": notes,
        "typical_applications": list(condition_record.applications),
        "comparable_pairs": list(condition_record.comparables),
        "reference": condition_record.reference,
    }


def get_friction_catalog() -> Dict[str, object]:
    """
    Provide metadata describing available material combinations and conditions.

    The catalog enables the frontend UI to populate selectors and present
    guidance without hard-coding data in JavaScript.

    ---Parameters---
    This helper does not require any input arguments.

    ---Returns---
    materials : dict[str, dict[str, object]]
        Mapping of material identifiers to descriptive metadata for UI display.
    combinations : list[dict[str, object]]
        Each entry lists the `pair_key`, participating materials, human-readable
        label, and the supported surface conditions.

    ---LaTeX---
    \\mu_{\\text{pair}} = f(\\text{material}_1, \\text{material}_2, \\text{condition})
    """

    catalog_materials: Dict[str, Dict[str, object]] = {}
    for slug, metadata in MATERIALS.items():
        catalog_materials[slug] = {
            "name": metadata["name"],
            "category": metadata["category"],
            "summary": metadata["summary"],
            "aliases": metadata["aliases"],
        }

    combinations: List[Dict[str, object]] = []
    for pair_key, record in PAIR_DATABASE.items():
        combinations.append(
            {
                "pair_key": "-".join(pair_key),
                "materials": list(pair_key),
                "label": record.label,
                "conditions": sorted(
                    condition.display_name for condition in record.conditions.values()
                ),
            }
        )

    combinations.sort(key=lambda entry: (entry["materials"][0], entry["materials"][1]))

    return {
        "materials": catalog_materials,
        "combinations": combinations,
    }


__all__ = [
    "lookup_coefficient_of_friction",
    "get_friction_catalog",
]
