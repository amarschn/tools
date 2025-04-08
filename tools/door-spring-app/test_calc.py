import calc

def test_basic():
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
    assert out["minLen"] > 0
    assert out["maxForce"] > 0

