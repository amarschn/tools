"""Build the FBD comparison's frozen cases from the production Python solver."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from pycalcs.stability import analyze_tipping  # noqa: E402

CASES = [
    ("level", "Level ground", "Coincident weight and reaction lines test arrow separation.", {}),
    ("slope", "18° cross slope", "The mass center stays fixed while the reaction moves toward the tipping edge.", {"slope_deg": 18}),
    ("push", "High, offset push", "A 220 N push acts at a separate application point, 1.0 m above the surface.",
     {"load_case": "push", "force": 220, "force_height": 1.0, "force_x": .25, "force_y": -.12}),
    ("turn", "Turn on a slope", "Equivalent inertia and gravity act at the same mass center.",
     {"load_case": "turn", "slope_deg": 10, "downhill_deg": 270, "speed": 2.2, "turn_radius": 2}),
    ("oblique", "Triangle + oblique loads", "An asymmetric footprint and forces along the selected edge test the 2D projection.",
     {"load_case": "combined", "slope_deg": 12, "downhill_deg": 35, "acceleration": .7, "accel_direction": 220,
      "force": 110, "force_direction": 120, "force_height": .85, "force_x": .22,
      "contacts": [[-.6, -.45], [.65, 0], [-.5, .5]], "cg_x": -.08, "cg_y": .04,
      "extra_forces": [{"name": "Offset pull", "vector": [-45, 70, 25], "point": [-.3, .2, .75]}]}),
    ("threshold", "At the tipping threshold", "The required reaction reaches the selected support edge.",
     {"slope_deg": 33.690067525979785}),
    ("beyond", "Beyond tipping", "The required reaction lies outside the footprint and cannot be supplied by these contacts.",
     {"slope_deg": 38}),
]


def build_cases() -> dict:
    """Return repeatable diagram fixtures, with source hashes for reproducibility."""
    cases = []
    for key, title, description, inputs in CASES:
        result = analyze_tipping(**inputs)
        cases.append({
            "id": key, "title": title, "description": description,
            "inputs": {"slope_deg": 0, "downhill_deg": 90, **inputs},
            "result": {name: result[name] for name in
                       ("equilibrium", "free_body", "threshold", "mass_components")},
        })
    return {
        "source": "pycalcs/stability.py:analyze_tipping",
        "source_sha256": hashlib.sha256((ROOT / "pycalcs/stability.py").read_bytes()).hexdigest(),
        "cases": cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check that cases.json matches the solver.")
    args = parser.parse_args()
    target = Path(__file__).with_name("cases.json")
    content = json.dumps(build_cases(), indent=2, allow_nan=False) + "\n"
    if args.check:
        if not target.exists() or target.read_text() != content:
            raise SystemExit("cases.json is stale; run generate_cases.py")
        print("Seven FBD cases match the production solver.")
    else:
        target.write_text(content)
        print(f"Wrote {target}")
