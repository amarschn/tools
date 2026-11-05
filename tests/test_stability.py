"""Independent equilibrium and boundary checks for rigid-body tipping."""

import json
import math

import pytest

from pycalcs import stability as s
from pycalcs.utils import get_documentation

RECT = [[-0.6, -0.4], [0.6, -0.4], [0.6, 0.4], [-0.6, 0.4]]


def test_centered_cart_known_geometry():
    """NHTSA SSF = track/(2h); elementary moments give tan(theta) = SSF."""
    r = s.analyze_tipping()
    e = r["equilibrium"]
    assert r["threshold"]["value"] == pytest.approx(math.degrees(math.atan(2 / 3)))
    assert e["margin"] == pytest.approx(0.4)
    assert e["moment_reserve"] == pytest.approx(100 * s.G * 0.4)
    assert e["reaction_point"] == pytest.approx([0, 0])
    assert e["normal_reaction"] == pytest.approx(100 * s.G)
    assert e["status"] == "positive"


def test_tip_angle_boundary_and_mass_independence():
    angle = math.degrees(math.atan(2 / 3))
    for mass in (1, 100, 3000):
        r = s.analyze_tipping(mass=mass, slope_deg=angle)
        assert r["equilibrium"]["status"] == "threshold"
        assert r["threshold"]["remaining"] == pytest.approx(0, abs=1e-8)
    assert s.analyze_tipping(slope_deg=angle + 0.1)["equilibrium"]["status"] == "beyond"


def test_slope_projection_and_force_balance():
    theta = math.radians(20)
    r = s.analyze_tipping(slope_deg=20)["equilibrium"]
    assert r["reaction_point"] == pytest.approx([0, 0.6 * math.tan(theta)])
    assert r["normal_reaction"] == pytest.approx(100 * s.G * math.cos(theta))
    assert r["moment_reserve"] == pytest.approx(
        100 * s.G * (0.4 * math.cos(theta) - 0.6 * math.sin(theta))
    )


def test_center_offset_and_braking_direction():
    r = s.analyze_tipping(
        cg_x=0.2, load_case="acceleration", accel_direction=180, acceleration=2
    )
    assert r["threshold"]["value"] == pytest.approx(s.G * 0.4 / 0.6)
    assert r["threshold"]["edge"].startswith("Front")
    assert r["equilibrium"]["reaction_point"][0] == pytest.approx(0.2 + 0.6 * 2 / s.G)
    forward = s.analyze_tipping(cg_x=0.2, load_case="acceleration", accel_direction=0)
    assert forward["threshold"]["value"] == pytest.approx(s.G * 0.8 / 0.6)
    assert forward["threshold"]["edge"].startswith("Rear")


def test_turn_direction_and_cross_slope():
    level = s.analyze_tipping(load_case="turn", turn_radius=2, speed=1)
    assert level["threshold"]["value"] == pytest.approx(math.sqrt(2 * s.G * 0.4 / 0.6))
    assert level["equilibrium"]["reaction_point"][1] == pytest.approx(-0.6 / (2 * s.G))
    assert level["threshold"]["edge"].startswith("Right")
    slope = s.analyze_tipping(
        load_case="turn", turn_radius=2, slope_deg=10, downhill_deg=270
    )
    threshold_a = s.G * (
        (0.4 / 0.6) * math.cos(math.radians(10)) - math.sin(math.radians(10))
    )
    assert slope["threshold"]["value"] == pytest.approx(math.sqrt(2 * threshold_a))
    assert slope["threshold"]["value"] < level["threshold"]["value"]


def test_horizontal_push_textbook_moment_balance():
    """Engineering Statics §9.2: at tipping, P z = W d about the toe."""
    r = s.analyze_tipping(load_case="push", force_height=1, force=100)
    assert r["threshold"]["value"] == pytest.approx(392.266)
    assert r["equilibrium"]["moment_reserve"] == pytest.approx(392.266 - 100)
    assert sum(
        c["reserve"] for c in r["equilibrium"]["edges"][2]["contributions"]
    ) == pytest.approx(292.266)


def test_combined_slope_and_force_threshold():
    theta = math.radians(12)
    r = s.analyze_tipping(
        load_case="combined",
        acceleration=0,
        force=100,
        slope_deg=12,
        limit_parameter="force",
    )
    expected = 100 * s.G * (0.4 * math.cos(theta) - 0.6 * math.sin(theta))
    assert r["threshold"]["value"] == pytest.approx(expected)
    r = s.analyze_tipping(
        load_case="combined", acceleration=0, force=100, limit_parameter="slope"
    )
    expected_angle = math.atan(0.4 / 0.6) - math.asin(
        100 / (100 * s.G * math.hypot(0.4, 0.6))
    )
    assert r["threshold"]["value"] == pytest.approx(math.degrees(expected_angle))


def test_combined_acceleration_force_slope_moment():
    r = s.analyze_tipping(
        load_case="combined",
        acceleration=1,
        accel_direction=270,
        force=100,
        slope_deg=10,
        limit_parameter="acceleration",
    )
    t = math.radians(10)
    expected = (100 * s.G * (0.4 * math.cos(t) - 0.6 * math.sin(t)) - 100) / (100 * 0.6)
    assert r["threshold"]["value"] == pytest.approx(expected)


def test_vertical_force_location_and_loss_of_contact():
    r = s.evaluate_stability(
        RECT, 100, [0, 0, 0.6], forces=[{"point": [0.2, 0, 1], "vector": [0, 0, -100]}]
    )
    assert r["normal_reaction"] == pytest.approx(100 * s.G + 100)
    assert r["reaction_point"][0] == pytest.approx(20 / (100 * s.G + 100))
    with pytest.raises(ValueError, match="No compressive"):
        s.analyze_tipping(load_case="push", force_vertical=100 * s.G)


def test_sliding_precedes_tipping():
    r = s.analyze_tipping(slope_deg=15, friction_coefficient=0.2)
    assert r["equilibrium"]["status"] == "positive"
    assert r["equilibrium"]["friction"]["status"] == "exceeded"
    assert r["threshold"]["value"] > 15
    r = s.analyze_tipping(load_case="push", force_height=0, friction_coefficient=0.2)
    assert r["threshold"]["state"] == "unbounded"


def test_combined_mass_replaces_manual_inputs():
    r = s.analyze_tipping(
        mass=-1,
        cg_height=-1,
        components=[
            {"mass": 80, "x": 0, "y": 0, "z": 0.3},
            {"mass": 20, "x": 0.4, "y": 0.1, "z": 1.3},
        ],
    )
    assert r["equilibrium"]["mass"] == 100
    assert r["equilibrium"]["center"] == pytest.approx([0.08, 0.02, 0.5])
    assert r["threshold"]["value"] == pytest.approx(math.degrees(math.atan(0.38 / 0.5)))


def test_triangle_diagonal_edge_and_duplicate_contacts():
    contacts = [[-1, -1], [1, -1], [0, 1], [0, 0], [-1, -1]]
    r = s.analyze_tipping(contacts=contacts, cg_height=1, downhill_deg=0)
    assert len(r["equilibrium"]["polygon"]) == 3
    assert r["equilibrium"]["margin"] == pytest.approx(1 / math.sqrt(5))
    assert r["threshold"]["value"] == pytest.approx(math.degrees(math.atan(0.5)))


def test_translation_and_rotation_invariance():
    forces = [{"point": [0.1, -0.2, 1], "vector": [50, 70, -20]}]
    original = s.evaluate_stability(
        RECT, 100, [0.05, -0.08, 0.6], 12, 60, [0.3, -0.4], forces
    )
    moved = s.evaluate_stability(
        [[x + 8, y - 3] for x, y in RECT],
        100,
        [8.05, -3.08, 0.6],
        12,
        60,
        [0.3, -0.4],
        [{"point": [8.1, -3.2, 1], "vector": [50, 70, -20]}],
    )
    rotated = s.evaluate_stability(
        [[-y, x] for x, y in RECT],
        100,
        [0.08, 0.05, 0.6],
        12,
        150,
        [0.4, 0.3],
        [{"point": [0.2, 0.1, 1], "vector": [-70, 50, -20]}],
    )
    assert moved["margin"] == pytest.approx(original["margin"])
    assert rotated["moment_reserve"] == pytest.approx(original["moment_reserve"])


def test_unstable_start_does_not_invent_a_threshold():
    r = s.analyze_tipping(cg_y=0.5)
    assert r["equilibrium"]["status"] == "beyond"
    assert r["threshold"]["state"] == "baseline_unstable"
    assert r["threshold"]["value"] is None
    # The current load case can be stable even though the sweep starts outside.
    r = s.analyze_tipping(cg_y=0.5, slope_deg=20, downhill_deg=270)
    assert r["equilibrium"]["status"] == "positive"
    assert r["threshold"]["state"] == "baseline_unstable"


def test_boundary_initially_moves_inward():
    r = s.analyze_tipping(cg_y=0.4, downhill_deg=270)
    assert r["threshold"]["value"] == pytest.approx(math.degrees(math.atan(0.8 / 0.6)))


def test_slope_search_detects_tangent_boundary():
    # R = 1 - (cos(theta) + sin(theta))/sqrt(2) touches zero at 45 degrees.
    r = s._first_limit([1, 1], [-1 / math.sqrt(2), 0], [-1 / math.sqrt(2), 0])
    assert r["value"] == pytest.approx(math.pi / 4)


def test_direction_envelope_matches_cardinals():
    data = s.analyze_tipping()["directions"]
    values = dict(zip(data["degrees"], data["tip_angles"]))
    assert values[0] == pytest.approx(45)
    assert values[90] == pytest.approx(math.degrees(math.atan(2 / 3)))
    assert values[180] == pytest.approx(values[0])
    assert values[270] == pytest.approx(values[90])
    assert values[360] == pytest.approx(values[0])


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"mass": 0}, "mass"),
        ({"cg_height": 0}, "height"),
        ({"slope_deg": 90}, "Slope"),
        ({"track": -1}, "Track"),
        ({"wheelbase": float("inf")}, "finite"),
        ({"cg_x": float("nan")}, "finite"),
        ({"friction_coefficient": -0.1}, "Friction"),
        ({"load_case": "turn", "turn_radius": 0}, "radius"),
        ({"load_case": "turn", "turn_direction": "unknown"}, "left or right"),
        ({"load_case": "push", "force_height": -1}, "height"),
        ({"contacts": [[0, 0], [1, 1], [2, 2]]}, "area"),
        ({"contacts": [[0, 0], [1, 0], [0, 1, 0.1]]}, "plane"),
        ({"load_case": "combined", "limit_parameter": "speed"}, "combined"),
        (
            {
                "load_case": "push",
                "extra_forces": [{"point": [0, 0, 0], "vector": [0]}],
            },
            "coordinates",
        ),
    ],
)
def test_invalid_inputs(kwargs, match):
    with pytest.raises(ValueError, match=match):
        s.analyze_tipping(**kwargs)


def test_documentation_and_json_contract():
    docs = get_documentation("pycalcs.stability", "analyze_tipping")
    assert "error" not in docs
    r = s.analyze_tipping()
    assert set(r) == set(docs["returns"])
    assert set(docs["parameters"]) == set(s.analyze_tipping.__annotations__) - {
        "return"
    }
    json.dumps(r, allow_nan=False)


def test_extra_forces_remain_fixed_during_sweep():
    r = s.analyze_tipping(
        load_case="push",
        extra_forces=[{"name": "Cable", "vector": [0, "50", 0], "point": [0, 0, "1"]}],
    )
    assert r["threshold"]["value"] == pytest.approx(392.266 - 50)


def test_fbd_required_contact_wrench_balances_three_dimensional_loads():
    """An eccentric oblique force needs a yaw couple as well as N and T."""
    e = s.evaluate_stability(
        RECT,
        100,
        [0, 0, 0.6],
        forces=[{"vector": [20, -30, 40], "point": [0.2, 0.1, 0.5]}],
    )
    fbd = s.free_body_diagram(e)
    forces = {force["id"]: force for force in fbd["forces"]}
    normal = 980.665 - 40
    assert forces["N"]["vector"] == pytest.approx([0, 0, normal])
    assert forces["T"]["vector"] == pytest.approx([-20, 30, 0])
    assert forces["N"]["point"] == pytest.approx([2 / normal, -19 / normal, 0])
    assert fbd["contact_couple"] == pytest.approx([0, 0, 8 + 320 / normal])
    assert [
        sum(f["vector"][i] for f in fbd["forces"]) for i in range(3)
    ] == pytest.approx([0, 0, 0])
    moments = [s._cross(f["point"], f["vector"]) for f in fbd["forces"]]
    assert [
        sum(m[i] for m in moments) + fbd["contact_couple"][i] for i in range(3)
    ] == pytest.approx([0, 0, 0])


def test_fbd_projection_preserves_the_edge_moment_and_out_of_plane_force():
    """At the left edge, a (20,-30,40) N force has (Fu,Fz)=(30,40) N."""
    result = s.analyze_tipping(
        load_case="push",
        force=0,
        extra_forces=[{"vector": [20, -30, 40], "point": [0.2, 0.1, 0.5]}],
    )
    section = result["free_body"]["sections"]["E3"]
    force = next(force for force in section["forces"] if force["id"] == "P2")
    assert force["point"] == pytest.approx([0.3, 0.5])
    assert force["vector"] == pytest.approx([30, 40])
    assert force["out_of_plane"] == pytest.approx(-20)
    assert force["restoring_moment"] == pytest.approx(3)
    for edge in result["equilibrium"]["edges"]:
        projected = result["free_body"]["sections"][edge["id"]]
        noncontact = [f for f in projected["forces"] if f["id"] not in ("N", "T")]
        assert sum(f["restoring_moment"] for f in noncontact) == pytest.approx(
            edge["reserve"]
        )
        assert sum(f["restoring_moment"] for f in projected["forces"]) == pytest.approx(
            0, abs=1e-10
        )


def test_fbd_reaction_remains_explicitly_required_beyond_the_tipping_edge():
    """An outside reaction is a demand, not a set of feasible wheel forces."""
    result = s.analyze_tipping(slope_deg=40)
    assert result["equilibrium"]["status"] == "beyond"
    section = result["free_body"]["sections"]["E3"]
    assert section["reaction"][0] < 0
    assert (
        len([f for f in result["free_body"]["forces"] if f["kind"] == "reaction"]) == 2
    )
