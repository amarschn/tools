"""Tests for legacy calc.py backward compatibility."""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import calc


def test_basic():
    """Test that legacy trapdoor_calculate function still works."""
    out = calc.trapdoor_calculate(
        mass_door=15,
        length_door=0.8,
        open_angle=90,
        door_mount_frac=0.7,
        cab_mount_x=0.4,
        cab_mount_y=0.1,
        num_springs=1,
        spring_nominal=200,
        spring_variation=10,
        handle_frac=0.9
    )
    # Check legacy return format
    assert "minLen" in out
    assert "maxLen" in out
    assert "stroke" in out
    assert "maxForce" in out
    assert "maxHandleForce" in out
    assert "angles" in out
    assert "springForces" in out
    assert "handleForces" in out

    # Validate values are reasonable
    assert out["minLen"] > 0
    assert out["maxLen"] > out["minLen"]
    assert out["stroke"] > 0
    assert out["maxForce"] == 200  # 200N * 1 spring
    assert len(out["angles"]) > 0
    assert len(out["handleForces"]) == len(out["angles"])


def test_multiple_springs():
    """Test legacy function with multiple springs."""
    out = calc.trapdoor_calculate(
        mass_door=15,
        length_door=0.8,
        open_angle=90,
        door_mount_frac=0.7,
        cab_mount_x=0.4,
        cab_mount_y=0.1,
        num_springs=2,
        spring_nominal=200,
        spring_variation=10,
        handle_frac=0.9
    )
    assert out["maxForce"] == 400  # 200N * 2 springs


if __name__ == "__main__":
    test_basic()
    test_multiple_springs()
    print("All legacy compatibility tests passed!")
