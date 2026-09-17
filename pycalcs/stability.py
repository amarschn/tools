"""Rigid-body tipping on a planar surface, in SI units.

The surface frame is x forward, y left, z away from the surface. Contacts
transmit compression; tire/suspension deformation and rotational inertia are
excluded. References: Engineering Statics, section 9.2 (slipping vs. tipping),
https://engineeringstatics.org/Chapter_09-slipping-vs--tipping.html; NHTSA,
DOT HS 811 486 (Static Stability Factor). No industry acceptance factor is
implied. Equations and legends for browser disclosure are defined here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

G = 9.80665
THEORY = [
    {
        "id": "mass",
        "title": "Combined mass and center of mass",
        "latex": r"m=\sum_j m_j,\quad \mathbf r_G=\frac{\sum_j m_j\mathbf r_j}{m}",
        "legend": "m: total mass (kg); m_j: component mass (kg); r_j: component center (m); r_G: combined center of mass (m); j: component index.",
    },
    {
        "id": "force",
        "title": "Gravity, inertia, and applied forces",
        "latex": r"\mathbf F=m(\mathbf g-\mathbf a)+\sum_k\mathbf F_k",
        "legend": "F: resultant non-contact force (N); g: gravity in surface coordinates (m/s²); a: actual translational acceleration (m/s²); F_k: applied force (N); k: force index. Inertia acts opposite to acceleration.",
    },
    {
        "id": "moment",
        "title": "Moment about the surface origin",
        "latex": r"\mathbf M=\mathbf r_G\times m(\mathbf g-\mathbf a)+\sum_k\mathbf r_k\times\mathbf F_k",
        "legend": "M: non-contact moment (N·m); r_G: combined center of mass (m); r_k: applied-force position (m); g, a, F_k: as in Equation (2). × denotes the vector cross product.",
    },
    {
        "id": "reaction",
        "title": "Required normal-reaction location",
        "latex": r"N=-F_z,\quad p_x=\frac{M_y}{N},\quad p_y=-\frac{M_x}{N}",
        "legend": "N: total compressive normal reaction (N), required to be positive; F_z: surface-normal force (N); M_x, M_y: moment components (N·m); p_x, p_y: normal-reaction location (m).",
    },
    {
        "id": "margin",
        "title": "Reserve about each support edge",
        "latex": r"d_i=\mathbf n_i\cdot(\mathbf p-\mathbf v_i),\quad R_i=N d_i",
        "legend": "d_i: signed distance to edge i (m); n_i: inward unit normal in the plane; p: normal-reaction location (m); v_i: point on the edge (m); R_i: restoring moment reserve (N·m). Positive is inside; zero is the tipping threshold.",
    },
    {
        "id": "slope",
        "title": "Gravity-only slope limit",
        "latex": r"\theta_{crit}=\tan^{-1}(d/h)",
        "legend": "θ_crit: critical slope toward an edge; d: distance from the level-ground center-of-mass projection to that edge (m); h: center-of-mass height (m). The downhill direction is perpendicular to the edge; other forces are absent.",
    },
    {
        "id": "acceleration",
        "title": "Level-ground acceleration limit",
        "latex": r"a_{crit}=g\frac{d}{h},\quad v_{crit}=\sqrt{a_{crit}r}",
        "legend": "a_crit: acceleration whose inertia points toward the edge (m/s²); g: 9.80665 m/s²; d: edge distance (m); h: center-of-mass height (m); v_crit: steady-turn speed (m/s); r: radius of the center-of-mass path (m). No other loads or slope.",
    },
    {
        "id": "push",
        "title": "Level-ground horizontal push limit",
        "latex": r"P_{crit}=\frac{mgd}{z_P}",
        "legend": "P_crit: horizontal push normal to an edge (N); m: total mass (kg); g: gravitational acceleration (m/s²); d: center-of-mass edge distance (m); z_P: push height (m). Translation is restrained and no other loads act.",
    },
    {
        "id": "friction",
        "title": "Aggregate sliding comparison",
        "latex": r"T=\sqrt{F_x^2+F_y^2},\quad T_{cap}=\mu N",
        "legend": "T: required tangential ground force (N); F_x, F_y: resultant tangential force components (N); T_cap: aggregate friction capacity (N); μ: uniform friction coefficient; N: normal reaction (N). This does not verify individual tire traction or yaw resistance.",
    },
    {
        "id": "contact",
        "title": "Required ground reaction in the free-body diagram",
        "latex": r"\mathbf R_N=(0,0,N),\quad\mathbf R_T=(-F_x,-F_y,0),\quad C_z=-M_z-(\mathbf r_p\times(\mathbf R_N+\mathbf R_T))_z",
        "legend": "R_N: required normal ground force (N); R_T: required tangential ground force (N); N, F_x, F_y: as in Equations (2) and (4); r_p=(p_x,p_y,0): reaction position (m); C_z: required residual ground couple about the surface normal (N·m); M_z: non-contact moment about that normal (N·m). These are required resultants, not verified tire capacities.",
    },
    {
        "id": "section",
        "title": "Projection normal to a support edge",
        "latex": r"u=\mathbf n_i\cdot(\mathbf r_{xy}-\mathbf v_i),\quad F_u=\mathbf n_i\cdot\mathbf F_{xy},\quad F_{out}=n_yF_x-n_xF_y",
        "legend": "u: position inward from edge i (m); n_i=(n_x,n_y): inward unit edge normal; r_xy: in-plane position (m); v_i: edge origin (m); F_xy=(F_x,F_y): in-plane force (N); F_u: force into the footprint (N); F_out: force along the edge, out of the diagram (N). Height z and normal force F_z are unchanged. The diagram is a projection of the 3D force balance.",
    },
]


def _number(value: Any, label: str, minimum: float | None = None) -> float:
    """Validate a scalar in the numerical working range.

    Parameters: value is a numeric input; label identifies it in errors;
    minimum is an optional inclusive lower bound. Returns a finite float
    with absolute value at most 1e9, or raises ValueError. No physical
    equation is used; the bound prevents overflow in moment calculations.
    """
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a finite number.") from exc
    if not math.isfinite(result) or abs(result) > 1e9:
        raise ValueError(f"{label} must be finite and within ±1 billion.")
    if minimum is not None and result < minimum:
        raise ValueError(f"{label} must be at least {minimum:g}.")
    return result


def _vector(values: Sequence[float], length: int, label: str) -> list[float]:
    """Validate a vector of a specified length.

    Parameters: values is a sequence; length is its required dimension;
    label identifies the vector. Returns finite float components or raises
    ValueError. This is input validation with no governing equation.
    """
    if not isinstance(values, (list, tuple)) or len(values) != length:
        raise ValueError(f"{label} needs {length} coordinates.")
    return [_number(v, label) for v in values]


def support_polygon(contacts: Sequence[Sequence[float]]) -> list[list[float]]:
    r"""Find the convex hull of fixed, coplanar ground contacts.

    Parameters
    ----------
    contacts : sequence of sequences
        Three to 100 contact locations [x, y] in meters. Optional z must be 0.
        Duplicate and interior points do not add support area.

    Returns
    -------
    list of lists
        Hull vertices ordered counterclockwise. Collinear input raises ValueError.

    Equations / references
    ----------------------
    Andrew's monotone chain uses the signed cross product
    \(c=(b_x-a_x)(c_y-a_y)-(b_y-a_y)(c_x-a_x)\).
    The convex hull is the compression-only support boundary; see module refs.
    """
    if not isinstance(contacts, (list, tuple)) or not 3 <= len(contacts) <= 100:
        raise ValueError("Provide between 3 and 100 ground contacts.")
    points = []
    for contact in contacts:
        if not isinstance(contact, (list, tuple)) or len(contact) not in (2, 3):
            raise ValueError("Each contact needs x and y coordinates in meters.")
        coords = _vector(contact, len(contact), "Contact")
        if len(coords) == 3 and coords[2] != 0:
            raise ValueError("Contacts must lie on the same plane (z = 0).")
        points.append(tuple(coords[:2]))
    points = sorted(set(points))
    if len(points) < 3:
        raise ValueError("At least three distinct contacts are required.")
    span = max(max(p[i] for p in points) - min(p[i] for p in points) for i in (0, 1))
    if span < 1e-6:
        raise ValueError("The support footprint must span at least 0.000001 m.")
    tolerance = 1e-12 * span * span
    hulls = []
    for ordered in (points, list(reversed(points))):
        half = []
        for p in ordered:
            while len(half) >= 2:
                a, b = half[-2:]
                cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
                if cross > tolerance:
                    break
                half.pop()
            half.append(p)
        hulls.extend(half[:-1])
    if len(hulls) < 3:
        raise ValueError("Contacts must enclose an area, not a straight line.")
    return [list(p) for p in hulls]


def combine_masses(components: Sequence[dict[str, Any]]) -> dict[str, Any]:
    r"""Combine component masses and centers without double counting a base mass.

    Parameters
    ----------
    components : sequence of dict
        One to 100 entries with mass (kg), x, y, z (m), and optional name.
        Masses must be positive and heights nonnegative.

    Returns
    -------
    dict
        mass (kg), center (three coordinates in m), and validated components.

    Equations / references
    ----------------------
    \(m=\sum m_j\), \(\mathbf r_G=\sum m_j\mathbf r_j/m\).
    This is the definition of center of mass for constant gravity.
    """
    if not isinstance(components, (list, tuple)) or not 1 <= len(components) <= 100:
        raise ValueError("Provide between 1 and 100 mass components.")
    rows = []
    for i, row in enumerate(components):
        if not isinstance(row, dict):
            raise TypeError("Each mass component needs mass, x, y, and z.")
        rows.append(
            {
                "name": str(row.get("name", f"Component {i + 1}"))[:80],
                "mass": _number(row.get("mass"), "Component mass", 1e-9),
                "x": _number(row.get("x"), "Component x"),
                "y": _number(row.get("y"), "Component y"),
                "z": _number(row.get("z"), "Component height", 0),
            }
        )
    total = sum(row["mass"] for row in rows)
    center = [
        sum(row["mass"] * row[k] for row in rows) / total for k in ("x", "y", "z")
    ]
    return {"mass": total, "center": center, "components": rows}


def _cross(a: Sequence[float], b: Sequence[float]) -> list[float]:
    r"""Return the 3D cross product of vectors a and b.

    Both parameters have three components; the returned list represents
    \(\mathbf a\times\mathbf b\). Used for force moments \(\mathbf r\times\mathbf F\).
    See the module's statics reference.
    """
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _edges(polygon: list[list[float]]) -> list[dict[str, Any]]:
    r"""Construct edge records for a counterclockwise polygon in meters.

    Returns edge endpoints, IDs, labels, and inward unit normals
    \(\mathbf n=(-\Delta y,\Delta x)/\ell\), where ell is edge length.
    This geometric definition makes inside distances positive.
    """
    records = []
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        side = (
            "Rear"
            if nx > 0.999
            else "Front"
            if nx < -0.999
            else "Right"
            if ny > 0.999
            else "Left"
            if ny < -0.999
            else "Diagonal"
        )
        records.append(
            {
                "id": f"E{i + 1}",
                "label": f"{side} · E{i + 1}",
                "start": a,
                "end": b,
                "normal": [nx, ny],
            }
        )
    return records


def _loads(
    mass: float,
    center: list[float],
    slope: float,
    downhill: float,
    acceleration: Sequence[float],
    forces: list[dict[str, Any]],
) -> dict:
    r"""Assemble non-contact loading in the surface frame.

    mass is kg, center is m, slope/downhill are degrees, acceleration is an
    x/y pair in m/s², and forces contain vector (N), point (m), and name.
    Returns total force, moment, and individual contributions using
    \(\mathbf F=m(\mathbf g-\mathbf a)+\sum\mathbf F_k\) and
    \(\mathbf M=\sum\mathbf r_k\times\mathbf F_k\). See THEORY (2)-(3).
    """
    theta, phi = math.radians(slope), math.radians(downhill)
    gravity = [
        mass * G * math.sin(theta) * math.cos(phi),
        mass * G * math.sin(theta) * math.sin(phi),
        -mass * G * math.cos(theta),
    ]
    entries = [
        {"name": "Gravity", "vector": gravity, "point": center},
        {
            "name": "Inertia",
            "vector": [-mass * acceleration[0], -mass * acceleration[1], 0.0],
            "point": center,
        },
    ] + forces
    entries = [{**e, "moment": _cross(e["point"], e["vector"])} for e in entries]
    return {
        "force": [sum(e["vector"][i] for e in entries) for i in range(3)],
        "moment": [sum(e["moment"][i] for e in entries) for i in range(3)],
        "loads": entries,
    }


def _reserves(loads: dict, edges: list[dict]) -> list[float]:
    r"""Return edge moment reserves and, last, the normal force.

    loads contains force and moment; edges contains inward normals and a
    point on each edge. Values are N·m, except the final value in N.
    \(R_i=n_x M_y-n_y M_x-N(\mathbf n\cdot\mathbf v)\), \(N=-F_z\).
    This is THEORY (4)-(5) without dividing by N, allowing limit searches.
    """
    normal = -loads["force"][2]
    mx, my = loads["moment"][:2]
    return [
        e["normal"][0] * my
        - e["normal"][1] * mx
        - normal * sum(n * v for n, v in zip(e["normal"], e["start"]))
        for e in edges
    ] + [normal]


def evaluate_stability(
    contacts: Sequence[Sequence[float]],
    mass: float,
    center_of_mass: Sequence[float],
    slope_deg: float = 0,
    downhill_deg: float = 90,
    acceleration: Sequence[float] = (0, 0),
    forces: Sequence[dict[str, Any]] | None = None,
    friction_coefficient: float | None = None,
) -> dict[str, Any]:
    r"""Evaluate tipping equilibrium for a rigid assembly on a planar surface.

    Parameters
    ----------
    contacts : sequence
        Ground locations [x, y] in m, at least three noncollinear points.
    mass : float
        Total mass in kg, strictly positive.
    center_of_mass : sequence
        [x, y, z] in m in the surface frame; z must be positive.
    slope_deg, downhill_deg : float
        Slope in [0, 90) degrees and downhill azimuth from +x toward +y.
    acceleration : sequence
        Actual [a_x, a_y] in m/s². Equivalent inertia has the opposite sign.
    forces : sequence or None
        Entries with vector [F_x, F_y, F_z] (N), point [x, y, z] (m), name.
    friction_coefficient : float or None
        Optional nonnegative uniform coefficient for aggregate translation.

    Returns
    -------
    dict
        Polygon, mass, center, resultant force/moment, normal reaction,
        reaction point, signed margins and moments for every edge, governing
        edge, status (positive/threshold/beyond), individual load contributions,
        and optional friction demand/capacity. Zero normal reaction raises
        ValueError because the contact model no longer applies.

    Equations / references
    ----------------------
    THEORY (1)-(5), (9) and the module references define the force/moment
    balance. \(N=-F_z>0\), \(p=(M_y/N,-M_x/N)\),
    \(d_i=\mathbf n_i\cdot(\mathbf p-\mathbf v_i)\).
    Polygon inclusion tests normal equilibrium, not full contact feasibility.
    """
    polygon = support_polygon(contacts)
    mass = _number(mass, "Mass", 1e-9)
    center = _vector(center_of_mass, 3, "Center of mass")
    if center[2] < 1e-6:
        raise ValueError("Center-of-mass height must be at least 0.000001 m.")
    slope = _number(slope_deg, "Slope", 0)
    if slope >= 90:
        raise ValueError("Slope must be less than 90 degrees.")
    downhill = _number(downhill_deg, "Downhill direction")
    accel = _vector(acceleration, 2, "Acceleration")
    mu = (
        None
        if friction_coefficient is None
        else _number(friction_coefficient, "Friction coefficient", 0)
    )
    if forces is None:
        forces = []
    if not isinstance(forces, (list, tuple)) or len(forces) > 100:
        raise ValueError("Provide at most 100 applied forces.")
    validated = []
    for i, f in enumerate(forces):
        if not isinstance(f, dict):
            raise TypeError("Each force needs a vector and an application point.")
        vector = _vector(f.get("vector"), 3, "Applied force")
        point = _vector(f.get("point"), 3, "Force position")
        if point[2] < 0:
            raise ValueError("Applied forces must act on or above the support plane.")
        validated.append(
            {
                "name": str(f.get("name", f"Force {i + 1}"))[:80],
                "vector": vector,
                "point": point,
            }
        )
    edges = _edges(polygon)
    loading = _loads(mass, center, slope, downhill, accel, validated)
    normal = -loading["force"][2]
    if normal <= 1e-12 * mass * G:
        raise ValueError(
            "No compressive ground reaction remains. The ground-contact model no longer applies."
        )
    reaction = [loading["moment"][1] / normal, -loading["moment"][0] / normal]
    for e, reserve in zip(edges, _reserves(loading, edges)):
        e["distance"] = reserve / normal
        e["reserve"] = reserve
        e["contributions"] = [
            {
                "name": row["name"],
                "reserve": _reserves(
                    {"force": row["vector"], "moment": row["moment"]}, [e]
                )[0],
            }
            for row in loading["loads"]
        ]
    governing = min(edges, key=lambda e: e["distance"])
    scale = max(math.dist(e["start"], e["end"]) for e in edges)
    tolerance = scale * 1e-9
    margin = governing["distance"]
    status = (
        "positive"
        if margin > tolerance
        else "beyond"
        if margin < -tolerance
        else "threshold"
    )
    demand = math.hypot(*loading["force"][:2])
    capacity = None if mu is None else mu * normal
    return {
        "polygon": polygon,
        "mass": mass,
        "center": center,
        **loading,
        "normal_reaction": normal,
        "reaction_point": reaction,
        "edges": edges,
        "governing_edge": governing["id"],
        "governing_label": governing["label"],
        "margin": margin,
        "moment_reserve": governing["reserve"],
        "status": status,
        "friction": {
            "coefficient": mu,
            "demand": demand,
            "capacity": capacity,
            "reserve": None if mu is None else capacity - demand,
            "status": "unevaluated"
            if mu is None
            else "exceeded"
            if demand > capacity + 1e-9 * normal
            else "within",
        },
    }


def _first_limit(
    base: list[float], unit: list[float], cosine: list[float] | None = None
) -> dict[str, Any]:
    r"""Find the first boundary of a prescribed load sweep from zero.

    For a linear sweep, base and unit contain reserves at q=0 and q=1.
    For an angular sweep, base is the constant term, unit the sine coefficient,
    and cosine the cosine coefficient in \(R=C+A\cos q+B\sin q\).
    Returns value (float or None), index, and state. Angular values are radians
    in [0, pi/2]. The final constraint is the normal reaction, not an edge.
    All roots are considered, including a tangency; an initially outward
    boundary has zero limit. The algebra follows THEORY (2)-(5).
    """
    initial = base if cosine is None else [c + a for c, a in zip(base, cosine)]
    scales = [
        max(abs(b), abs(u), abs(cosine[i]) if cosine else 0, 1e-15)
        for i, (b, u) in enumerate(zip(base, unit))
    ]
    if any(b < -1e-10 * s for b, s in zip(initial, scales)) or initial[-1] <= 0:
        return {"value": None, "index": None, "state": "baseline_unstable"}
    candidates = []
    for i, (b, u, scale) in enumerate(zip(base, unit, scales)):
        tol = scale * 1e-12
        if cosine is None:
            rate = u - b
            if rate < -tol:
                candidates.append((max(0.0, -b / rate), i))
            elif abs(b) <= tol and abs(rate) <= tol:
                candidates.append((0.0, i))
        else:
            a, c = cosine[i], b
            radius = math.hypot(a, u)
            if radius <= tol:
                if abs(c) <= tol:
                    candidates.append((0.0, i))
                continue
            ratio = -c / radius
            if abs(ratio) > 1 + 1e-12:
                continue
            phase = math.atan2(u, a)
            angle = math.acos(max(-1.0, min(1.0, ratio)))
            for sign in (-1, 1):
                for turn in (-1, 0, 1):
                    root = phase + sign * angle + 2 * math.pi * turn
                    if -1e-10 <= root <= math.pi / 2 + 1e-10:
                        if abs(root) <= 1e-10 and u > tol:
                            continue  # The sweep initially moves into the polygon.
                        candidates.append((max(0.0, min(math.pi / 2, root)), i))
    if not candidates:
        return {"value": None, "index": None, "state": "unbounded"}
    value, index = min(candidates)
    return {"value": value, "index": index, "state": "finite"}


def free_body_diagram(equilibrium: dict[str, Any]) -> dict[str, Any]:
    r"""Describe the required contact wrench and every edge-normal FBD.

    Parameters
    ----------
    equilibrium : dict
        A valid result from evaluate_stability, using SI units and the
        surface-fixed frame. This function does not solve contact feasibility.

    Returns
    -------
    dict
        forces: named W (weight), I (equivalent inertia), P1... (applied),
        N (normal ground reaction), and T (tangential ground reaction), with
        their 3D vectors and application points. contact_couple is the required
        residual couple at the reaction point. sections maps each edge ID to
        2D positions, projected forces, out-of-plane components, and dimensions.
        Ground reactions may be infeasible when the tipping margin is negative.

    Equations / references
    ----------------------
    THEORY (10)-(11) follow from force and moment equilibrium:
    \(\mathbf R=-\mathbf F\),
    \(\mathbf C=-\mathbf M-\mathbf r_p\times\mathbf R\).
    The support-plane tipping model sets C_x and C_y to zero; C_z records the
    yaw demand that a separate contact model would need to verify.
    A projected force contributes restoring reserve \(zF_u-uF_z\).
    See the module's Engineering Statics reference for free-body isolation.
    """
    e = equilibrium
    forces = []
    for index, load in enumerate(e["loads"]):
        force_id = "W" if index == 0 else "I" if index == 1 else f"P{index - 1}"
        forces.append(
            {
                "id": force_id,
                "name": "Weight"
                if index == 0
                else "Equivalent inertia"
                if index == 1
                else load["name"],
                "kind": "inertia" if index == 1 else "external",
                "vector": load["vector"],
                "point": load["point"],
            }
        )
    reaction = [*e["reaction_point"], 0.0]
    forces.extend(
        [
            {
                "id": "N",
                "name": "Required normal reaction",
                "kind": "reaction",
                "vector": [0.0, 0.0, e["normal_reaction"]],
                "point": reaction,
            },
            {
                "id": "T",
                "name": "Required tangential reaction",
                "kind": "reaction",
                "vector": [-e["force"][0], -e["force"][1], 0.0],
                "point": reaction,
            },
        ]
    )
    reaction_moment = _cross(reaction, [-f for f in e["force"]])
    couple = [0.0, 0.0, -e["moment"][2] - reaction_moment[2]]
    sections = {}
    for edge in e["edges"]:
        nx, ny = edge["normal"]
        vx, vy = edge["start"]
        projected = []
        for force in forces:
            x, y, z = force["point"]
            fx, fy, fz = force["vector"]
            u = nx * (x - vx) + ny * (y - vy)
            fu = nx * fx + ny * fy
            projected.append(
                {
                    "id": force["id"],
                    "point": [u, z],
                    "vector": [fu, fz],
                    "out_of_plane": ny * fx - nx * fy,
                    "restoring_moment": z * fu - u * fz,
                }
            )
        sections[edge["id"]] = {
            "center": [
                nx * (e["center"][0] - vx) + ny * (e["center"][1] - vy),
                e["center"][2],
            ],
            "reaction": [edge["distance"], 0.0],
            "support_span": max(
                nx * (p[0] - vx) + ny * (p[1] - vy) for p in e["polygon"]
            ),
            "forces": projected,
            "reserve": edge["reserve"],
        }
    return {"forces": forces, "contact_couple": couple, "sections": sections}


def analyze_tipping(
    wheelbase: float = 1.2,
    track: float = 0.8,
    cg_height: float = 0.6,
    mass: float = 100,
    cg_x: float = 0,
    cg_y: float = 0,
    load_case: str = "slope",
    slope_deg: float = 0,
    downhill_deg: float = 90,
    acceleration: float = 1,
    accel_direction: float = 0,
    speed: float = 1,
    turn_radius: float = 2,
    turn_direction: str = "left",
    force: float = 100,
    force_direction: float = 90,
    force_height: float = 1,
    force_x: float = 0,
    force_y: float = 0,
    force_vertical: float = 0,
    friction_coefficient: float | None = None,
    contacts: list | None = None,
    components: list | None = None,
    extra_forces: list | None = None,
    limit_parameter: str = "slope",
) -> dict[str, Any]:
    r"""Find tipping onset and reserve for a cart or rigid mobile platform.

    One rigid assembly, fixed coplanar contacts, and prescribed translational
    motion. Stationary cases assume rolling is restrained. Rotation, suspension,
    soil deformation, and individual wheel loads are excluded. Reference:
    Engineering Statics §9.2 and NHTSA DOT HS 811 486. THEORY contains numbered
    equations and variable legends for the browser's background and derivations.

    ---Parameters---
    wheelbase : float
        Front-to-rear contact spacing (m), positive. Ignored with custom contacts.
    track : float
        Left-to-right contact spacing (m), positive. Ignored with custom contacts.
    cg_height : float
        Center-of-mass height normal to the surface (m). Minimum 0.000001 m.
    mass : float
        Total mass including payload (kg). Component mode replaces this value.
    cg_x : float
        Center-of-mass offset forward from the footprint center (m).
    cg_y : float
        Center-of-mass offset left from the footprint center (m).
    load_case : str
        slope, acceleration, turn, push, or combined. Slope is active in every case.
    slope_deg : float
        Ground inclination in degrees, from 0 up to but excluding 90.
    downhill_deg : float
        Downhill direction: 0° forward, 90° left, 180° rear, 270° right.
    acceleration : float
        Actual acceleration magnitude (m/s²), nonnegative. Set direction to 180° for braking while traveling forward.
    accel_direction : float
        Actual acceleration direction in degrees from forward toward left. Inertia points the other way.
    speed : float
        Steady-turn speed at the center of mass (m/s), nonnegative.
    turn_radius : float
        Radius of the center-of-mass path (m), strictly positive.
    turn_direction : str
        left or right. Centripetal acceleration is inward; inertia acts outward.
    force : float
        Horizontal applied-force magnitude (N), nonnegative. The force sweep varies this magnitude only.
    force_direction : float
        Horizontal push direction: 0° forward, 90° left, 180° rear, 270° right.
    force_height : float
        Application height normal to the surface (m), nonnegative.
    force_x : float
        Forward coordinate of the force application point (m).
    force_y : float
        Left coordinate of the force application point (m).
    force_vertical : float
        Additional surface-normal force at the same point (N). Positive lifts; negative presses down. Held fixed during the horizontal-force sweep.
    friction_coefficient : float or None
        Uniform Coulomb friction coefficient for restrained contacts. Leave blank to omit the aggregate sliding check. It does not model wheel brakes or yaw resistance.
    contacts : list or None
        Custom contact coordinates [x, y] in meters. At least three points must enclose an area, all on one rigid plane.
    components : list or None
        Component rows with name, mass (kg), x, y, z (m). These replace total mass and center inputs; include the base vehicle.
    extra_forces : list or None
        Additional fixed force rows: name, vector [Fx,Fy,Fz] in N, and point [x,y,z] in m. Active in push and combined cases.
    limit_parameter : str
        In combined mode, vary slope, acceleration, or force from zero, holding the other loads fixed.

    ---Returns---
    equilibrium : dict
        Current forces, moments, edge reserves, support geometry, and friction check, all in SI units.
    threshold : dict
        First tipping or contact-loss boundary from zero for the selected parameter, with value, unit, demand, remaining margin, limiting edge, and sweep state.
    directions : dict
        Gravity-only critical slope versus downhill azimuth, independent of current acceleration and applied forces.
    mass_components : list
        Validated component masses and positions used in this case.
    theory : list
        Numbered equations, descriptions, and variable legends.
    free_body : dict
        Named 3D forces, required contact resultants and yaw couple, and projected forces and dimensions for every edge-normal free-body diagram.
    subst_margin : str
        Substituted equation for current distance and moment reserve.
    subst_reaction : str
        Substituted equation for normal reaction and its location.
    subst_mass : str
        Substituted mass and combined-center result.
    subst_threshold : str
        Constraint equation and substituted boundary for the selected sweep.

    ---LaTeX---
    \mathbf F = m(\mathbf g-\mathbf a)+\sum_k\mathbf F_k
    \mathbf M = \mathbf r_G\times m(\mathbf g-\mathbf a)+\sum_k\mathbf r_k\times\mathbf F_k
    N=-F_z,\quad p_x=M_y/N,\quad p_y=-M_x/N
    d_i=\mathbf n_i\cdot(\mathbf p-\mathbf v_i),\quad R_i=Nd_i
    """
    if load_case not in ("slope", "acceleration", "turn", "push", "combined"):
        raise ValueError("Choose a supported load case.")
    if contacts is None:
        length = _number(wheelbase, "Wheelbase", 1e-6)
        width = _number(track, "Track", 1e-6)
        contacts = [
            [x * length / 2, y * width / 2]
            for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
    mass_model = combine_masses(
        components
        if components is not None
        else [{"name": "Assembly", "mass": mass, "x": cg_x, "y": cg_y, "z": cg_height}]
    )
    mass, center = mass_model["mass"], mass_model["center"]
    slope = _number(slope_deg, "Slope", 0)
    downhill = _number(downhill_deg, "Downhill direction")
    accel = [0.0, 0.0]
    if load_case in ("acceleration", "combined"):
        acceleration = _number(acceleration, "Acceleration", 0)
        phi = math.radians(_number(accel_direction, "Acceleration direction"))
        accel = [acceleration * math.cos(phi), acceleration * math.sin(phi)]
    if load_case == "turn":
        speed = _number(speed, "Speed", 0)
        turn_radius = _number(turn_radius, "Turn radius", 1e-6)
        if turn_direction not in ("left", "right"):
            raise ValueError("Choose left or right for the turn direction.")
        accel = [0.0, (1 if turn_direction == "left" else -1) * speed**2 / turn_radius]
    applied = []
    if load_case in ("push", "combined"):
        force = _number(force, "Horizontal force", 0)
        phi = math.radians(_number(force_direction, "Force direction"))
        point = [
            _number(force_x, "Force x"),
            _number(force_y, "Force y"),
            _number(force_height, "Force height", 0),
        ]
        applied = [
            {
                "name": "Applied push",
                "point": point,
                "vector": [
                    force * math.cos(phi),
                    force * math.sin(phi),
                    _number(force_vertical, "Normal applied force"),
                ],
            }
        ]
        if extra_forces is not None:
            if not isinstance(extra_forces, list):
                raise ValueError("Additional forces must be a list.")
            applied += extra_forces
    current = evaluate_stability(
        contacts, mass, center, slope, downhill, accel, applied, friction_coefficient
    )
    applied = current["loads"][2:]
    edges = current["edges"]
    parameter = (
        limit_parameter
        if load_case == "combined"
        else {"push": "force", "turn": "speed"}.get(load_case, load_case)
    )
    if parameter not in ("slope", "acceleration", "force", "speed"):
        raise ValueError("Choose slope, acceleration, or force for the limit sweep.")
    if load_case == "combined" and parameter == "speed":
        raise ValueError("Choose slope, acceleration, or force for the combined sweep.")

    if parameter == "slope":
        # Assemble C + A cos(theta) + B sin(theta) without reaction division.
        r0 = _reserves(_loads(mass, center, 0, downhill, accel, applied), edges)
        r90 = _reserves(_loads(mass, center, 90, downhill, accel, applied), edges)
        r180 = _reserves(_loads(mass, center, 180, downhill, accel, applied), edges)
        constant = [(p + q) / 2 for p, q in zip(r0, r180)]
        cosine = [(p - q) / 2 for p, q in zip(r0, r180)]
        sine = [p - q for p, q in zip(r90, constant)]
        limit = _first_limit(constant, sine, cosine)
        coefficients = [constant, cosine, sine]
        unit, demand, title = "°", slope, "Critical slope"
        if limit["value"] is not None:
            limit["value"] = math.degrees(limit["value"])
        held = "Vary slope from level ground in the selected downhill direction; hold acceleration and all applied forces fixed."
    else:
        accel0, accel1, forces0, forces1 = accel, accel, applied, applied
        if parameter in ("acceleration", "speed"):
            phi = (
                math.radians(_number(accel_direction, "Acceleration direction"))
                if parameter == "acceleration"
                else (math.pi / 2 if turn_direction == "left" else -math.pi / 2)
            )
            accel0, accel1 = [0, 0], [math.cos(phi), math.sin(phi)]
        else:
            direction = math.radians(force_direction)
            forces0 = [
                {**applied[0], "vector": [0, 0, applied[0]["vector"][2]]}
            ] + applied[1:]
            forces1 = [
                {
                    **applied[0],
                    "vector": [
                        math.cos(direction),
                        math.sin(direction),
                        applied[0]["vector"][2],
                    ],
                }
            ] + applied[1:]
        r0 = _reserves(_loads(mass, center, slope, downhill, accel0, forces0), edges)
        r1 = _reserves(_loads(mass, center, slope, downhill, accel1, forces1), edges)
        limit = _first_limit(r0, r1)
        coefficients = [r0, [b - a for a, b in zip(r0, r1)]]
        unit, demand, title = {
            "acceleration": ("m/s²", acceleration, "Critical acceleration"),
            "speed": ("m/s", speed, "Critical turn speed"),
            "force": ("N", force, "Critical horizontal force"),
        }[parameter]
        if parameter == "speed" and limit["value"] is not None:
            limit["value"] = math.sqrt(limit["value"] * turn_radius)
        held = {
            "acceleration": "Vary actual acceleration from zero in the selected direction; hold slope and applied forces fixed.",
            "force": "Vary the horizontal push from zero; hold its direction, height, normal component, slope, acceleration, and other forces fixed.",
            "speed": "Vary steady-turn speed from zero; hold slope, turn direction, and center-of-mass path radius fixed.",
        }[parameter]
    index = limit["index"]
    label = (
        None
        if index is None
        else "Loss of ground contact"
        if index == len(edges)
        else edges[index]["label"]
    )
    limit.update(
        {
            "parameter": parameter,
            "unit": unit,
            "title": title,
            "demand": demand,
            "edge": label,
            "held": held,
            "remaining": None if limit["value"] is None else limit["value"] - demand,
        }
    )
    # Resolve equal current margins toward the edge reached by the selected sweep.
    if index is not None and index < len(edges):
        tied = edges[index]
        span = max(math.dist(e["start"], e["end"]) for e in edges)
        if abs(tied["distance"] - current["margin"]) <= 1e-9 * span:
            current.update(
                governing_edge=tied["id"],
                governing_label=tied["label"],
                margin=tied["distance"],
                moment_reserve=tied["reserve"],
            )
    directions = {"degrees": [], "tip_angles": []}
    for azimuth in range(0, 361, 5):
        r0 = _reserves(_loads(mass, center, 0, azimuth, [0, 0], []), edges)
        r90 = _reserves(_loads(mass, center, 90, azimuth, [0, 0], []), edges)
        root = _first_limit([0.0] * len(r0), r90, r0)
        directions["degrees"].append(azimuth)
        directions["tip_angles"].append(
            None if root["value"] is None else math.degrees(root["value"])
        )
    if index is None:
        substituted = (
            r"\text{No stable starting point for this sweep.}"
            if limit["state"] == "baseline_unstable"
            else r"\text{No finite tipping boundary in this sweep.}"
        )
    elif parameter == "slope":
        c, a, b = [v[index] for v in coefficients]
        substituted = (
            rf"0={c:.6g}+({a:.6g})\cos\theta+({b:.6g})\sin\theta"
            rf"\quad\Rightarrow\theta={limit['value']:.6g}^\circ"
        )
    else:
        b, rate = [v[index] for v in coefficients]
        symbol = (
            "v^2/r"
            if parameter == "speed"
            else "a"
            if parameter == "acceleration"
            else "P"
        )
        substituted = rf"0={b:.6g}+({rate:.6g})({symbol})"
        if parameter == "speed":
            substituted += rf",\quad r={turn_radius:.6g}\,\mathrm{{m}}"
        substituted += rf"\quad\Rightarrow {('v' if parameter == 'speed' else symbol)}={limit['value']:.6g}"
    p = current["reaction_point"]
    normal = current["normal_reaction"]
    return {
        "equilibrium": current,
        "threshold": limit,
        "directions": directions,
        "mass_components": mass_model["components"],
        "theory": THEORY,
        "free_body": free_body_diagram(current),
        "subst_margin": rf"R_{{{current['governing_edge']}}}={normal:.6g}\times({current['margin']:.6g})={current['moment_reserve']:.6g}\,\mathrm{{N\,m}}",
        "subst_reaction": rf"N={normal:.6g}\,\mathrm{{N}},\quad p_x=\frac{{{current['moment'][1]:.6g}}}{{{normal:.6g}}}={p[0]:.6g}\,\mathrm{{m}},\quad p_y=\frac{{{-current['moment'][0]:.6g}}}{{{normal:.6g}}}={p[1]:.6g}\,\mathrm{{m}}",
        "subst_mass": rf"m={mass:.6g}\,\mathrm{{kg}},\quad\mathbf r_G=({center[0]:.6g},\ {center[1]:.6g},\ {center[2]:.6g})\,\mathrm{{m}}",
        "subst_threshold": substituted,
    }
