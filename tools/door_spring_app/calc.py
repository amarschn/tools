# calc.py
import math

def door_torque(mass_door, length_door, theta_deg):
    g = 9.81
    w = mass_door * g
    theta_rad = math.radians(theta_deg)
    return w * (length_door / 2.0) * math.cos(theta_rad)

def spring_length(length_door, theta_deg, door_mount_frac, cab_mount_x, cab_mount_y):
    theta_rad = math.radians(theta_deg)
    door_mount_x_ = door_mount_frac * length_door * math.cos(theta_rad)
    door_mount_y_ = door_mount_frac * length_door * math.sin(theta_rad)
    dx = door_mount_x_ - cab_mount_x
    dy = door_mount_y_ - cab_mount_y
    return math.sqrt(dx*dx + dy*dy)

def compute_spring_lengths_over_range(length_door, door_mount_frac, cab_mount_x, cab_mount_y, open_angle):
    angle_step = 3
    angles = list(range(0, open_angle+1, angle_step))
    if angles[-1] != open_angle:
        angles.append(open_angle)
    angles.sort()

    lengths = [spring_length(length_door, a, door_mount_frac, cab_mount_x, cab_mount_y) for a in angles]
    min_len = min(lengths)
    max_len = max(lengths)
    return angles, lengths, min_len, max_len

def spring_force_range(nominal, variation_percent):
    frac = variation_percent / 100.0
    f_min = nominal * (1.0 - frac)
    f_max = nominal * (1.0 + frac)
    return f_min, f_max

def extension_fraction(L, min_len, max_len):
    if abs(max_len - min_len) < 1e-12:
        return 0.5
    return (L - min_len) / (max_len - min_len)

def spring_force_at_extension(f_min, f_max, fraction):
    fraction = min(max(fraction, 0.0), 1.0)
    return f_min + (f_max - f_min) * fraction

def compute_all_angles(
    mass_door, length_door, open_angle,
    door_mount_frac, cab_mount_x, cab_mount_y,
    num_springs, nominal, variation_percent,
    handle_frac
):
    # min/max lengths
    _, _, min_len, max_len = compute_spring_lengths_over_range(length_door, door_mount_frac, cab_mount_x, cab_mount_y, open_angle)
    # spring force range
    f_min, f_max = spring_force_range(nominal, variation_percent)

    results = []
    for theta in range(open_angle + 1):
        dt = door_torque(mass_door, length_door, theta)
        Ls = spring_length(length_door, theta, door_mount_frac, cab_mount_x, cab_mount_y)
        frac = extension_fraction(Ls, min_len, max_len)
        Fs_one = spring_force_at_extension(f_min, f_max, frac)
        Fs_total = Fs_one * num_springs

        # Approx spring torque. We keep the simplistic approach from your JS:
        angle_spring_deg = 30.0  # could refine geometry if needed
        alpha_rad = math.radians(angle_spring_deg)
        lever_arm = (door_mount_frac * length_door) * math.sin(alpha_rad)
        T_spring = Fs_total * lever_arm

        T_net = dt - T_spring

        handle_radius = handle_frac * length_door
        if abs(handle_radius) < 1e-12:
            F_handle = float('inf')
        else:
            F_handle = T_net / handle_radius

        results.append({
            "angle": theta,
            "doorTorque": dt,
            "springLength": Ls,
            "extensionFrac": frac,
            "springForceSingle": Fs_one,
            "springForceTotal": Fs_total,
            "springTorque": T_spring,
            "netTorque": T_net,
            "handleForce": F_handle
        })
    return results

def compute_stroke(results):
    min_len = min(r["springLength"] for r in results)
    max_len = max(r["springLength"] for r in results)
    return (max_len - min_len), min_len, max_len

#
# Helper function that does everything and returns a Python dict
# that JS can easily convert to JSON.
#
def trapdoor_calculate(
    mass_door, length_door, open_angle,
    door_mount_frac, cab_mount_x, cab_mount_y,
    num_springs, spring_nominal, spring_variation,
    handle_frac
):
    results = compute_all_angles(
        mass_door, length_door, open_angle,
        door_mount_frac, cab_mount_x, cab_mount_y,
        num_springs, spring_nominal, spring_variation,
        handle_frac
    )

    stroke, min_len, max_len = compute_stroke(results)
    max_force = max(r["springForceTotal"] for r in results)
    max_handle_force = max(abs(r["handleForce"]) for r in results)

    # We'll return a dictionary with everything needed in the frontend
    # (chart data, numeric results, etc.).
    angles = [r["angle"] for r in results]
    spring_forces = [r["springForceTotal"] for r in results]
    handle_forces = [r["handleForce"] for r in results]

    return {
        "minLen": min_len,
        "maxLen": max_len,
        "stroke": stroke,
        "maxForce": max_force,
        "maxHandleForce": max_handle_force,
        "angles": angles,
        "springForces": spring_forces,
        "handleForces": handle_forces
    }
