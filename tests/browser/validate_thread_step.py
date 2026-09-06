"""Validate browser STEP output using a separate installed OCP/OCCT kernel.

Usage: python3.13 tests/browser/validate_thread_step.py file.step model.json
OCP is a developer-test dependency only. It is never loaded by the website.
"""

import json
import math
import sys
from itertools import pairwise
from pathlib import Path

from OCP import __version__
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepGProp import BRepGProp
from OCP.gp import gp_Pnt
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_IN, TopAbs_OUT, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer


def validate(step_path: str, model: dict) -> dict:
    """Check one closed solid, physical volume, axial profile, pitch and hand."""
    reader = STEPControl_Reader()
    assert reader.ReadFile(step_path) == IFSelect_RetDone
    assert reader.TransferRoots() > 0
    shape = reader.OneShape()
    assert BRepCheck_Analyzer(shape).IsValid()
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = []
    while explorer.More():
        solids.append(explorer.Current())
        explorer.Next()
    assert len(solids) == 1, f"Expected one solid, found {len(solids)}"
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, properties)
    volume = properties.Mass()
    assert abs(volume / model["expected_volume_mm3"] - 1) < 1e-4
    classifier = BRepClass3d_SolidClassifier(solids[0])
    profile = model[model["specimen"]]
    pitch = model["pitch_mm"]
    internal = model["specimen"] == "internal"
    sign = -1 if model["hand"] == "LH" else 1
    samples = 0
    for theta_degrees in [23, 113, 203, 293]:
        theta = math.radians(theta_degrees)
        for fraction in [0.12, 0.27, 0.43, 0.67, 0.88]:
            z = model["length_mm"] / 2 + (fraction - 0.5) * pitch
            phase = (z - sign * (theta_degrees - 23) / 360 * pitch) % pitch
            for (x1, r1), (x2, r2) in pairwise(profile):
                if x1 <= phase <= x2:
                    radius = r1 + (r2 - r1) * (phase - x1) / (x2 - x1)
                    break
            for delta in [-0.003, 0.003]:
                r = radius + delta
                classifier.Perform(
                    gp_Pnt(r * math.cos(theta), r * math.sin(theta), z), 1e-6
                )
                expected = TopAbs_IN if (delta > 0) == internal else TopAbs_OUT
                assert classifier.State() == expected, (
                    model["designation"],
                    model["hand"],
                    model["specimen"],
                    theta_degrees,
                    z,
                    phase,
                    radius,
                    delta,
                    classifier.State(),
                    expected,
                )
                samples += 1
    return {
        "kernel": __version__,
        "solid_count": len(solids),
        "volume_mm3": volume,
        "profile_and_hand_samples": samples,
    }


if __name__ == "__main__":
    print(json.dumps(validate(sys.argv[1], json.loads(Path(sys.argv[2]).read_text()))))
