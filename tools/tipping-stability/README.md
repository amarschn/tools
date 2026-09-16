# Tipping and Stability

Estimate the slope, acceleration, or applied force that brings a rigid cart,
mobile robot, or freestanding assembly to a tipping edge. Compare payload
positions and support layouts, then inspect the forces and moments behind the
result.

## Using the tool

The default example is a centered cart with a 1.2 m wheelbase, 0.8 m track,
100 kg mass, and a center of mass 0.6 m above the surface. It has an ideal
lateral tipping angle of 33.69°. The first result loads with the example;
subsequent edits take effect when you press **Calculate stability**.

Choose a slope, acceleration/braking, steady-turn, push/pull, or combined case.
Slope remains active in every case. In combined mode, select the parameter
whose limit you want to find. The other loads stay fixed.

Coordinates are measured from the footprint center in a frame attached to the
surface: x forward, y left, z away from the surface. Direction angles increase
from forward toward left. An actual acceleration at 180° models braking while
traveling forward. Equivalent inertia acts in the opposite direction.

Expand **Payload, supports & contact** to define an offset center of mass,
component masses, custom contacts, friction, or additional forces. The component
table replaces the total mass and center fields, so include the base assembly.
Custom contacts replace wheelbase and track. A force's positive z component
lifts away from the ground.

## Requirements and supported behavior

- Calculate normal-force equilibrium for one rigid body on fixed, coplanar,
  compression-only contacts. Form the convex hull of the contact points.
- Evaluate the current signed distance and restoring moment reserve at every
  edge, including initially unstable cases.
- Find the first edge or normal-contact boundary as the chosen load parameter
  increases from zero. Report an unstable starting point or an unbounded sweep
  explicitly.
- Include slope in turning and braking limits. Turn radius is the radius of the
  center-of-mass path, and the speed limit assumes a steady turn.
- Compare aggregate tangential demand with a uniform Coulomb friction capacity
  when a coefficient is supplied. Report sliding separately from tipping.
- Draw the support polygon, normal-reaction location, center-of-mass projection,
  and a section normal to a selected edge. A separate direction plot shows
  gravity-only slope limits.
- Expose numbered equations, substituted values, load contributions, and
  references through the result cards and Background tab.
- Preserve scalar inputs and editable tables in share links. Export the last
  calculated case and results as CSV or JSON; disable exports after an edit
  until the case is recalculated.
- Provide keyboard controls, light/dark/automatic themes, compact spacing,
  and selectable result precision.

## Model boundaries

Stationary cases assume restraint against rolling. Tire friction is not a model
of an unlocked wheel brake. The sliding comparison also does not establish
individual tire traction or yaw resistance.

Suspension, pivoting axles, soft ground, noncoplanar contacts, impacts, rotational
inertia, and motion after tipping need additional models. Low speed does not
remove those effects. A forklift with a pivoting axle cannot be represented by
simply entering its four wheel contacts.

The output is a tipping threshold for the stated model, not a rated operating
limit or certification result. Individual normal forces at four or more
contacts generally require a stiffness or load-sharing model.

## Calculation source and verification

[`pycalcs/stability.py`](../../pycalcs/stability.py) is the calculation source.
It defines the equations, variable legends, and parameter explanations rendered
by the page. The interface is adapted from `tools/example_tool_advanced` and
loads the module with Pyodide. No Python dependencies are required.

[`tests/test_stability.py`](../../tests/test_stability.py) covers known geometric
and moment-balance results, combined loading, friction, mass composition,
triangular supports, coordinate invariance, boundary behavior, and invalid
inputs. Run it with:

```sh
python3.13 -m pytest tests/test_stability.py -q
```

The browser regression uses the real Pyodide engine and checks diagrams,
derivations, tables, share-link round trips, downloaded exports, themes,
mobile layout, and invalid-input recovery:

```sh
python3 -m http.server 8157 --bind 127.0.0.1
node tests/browser/tipping-stability.cjs
```

`PLAYWRIGHT_MODULE` can point to an installed Playwright package.
`TIPPING_TOOL_URL` can override the default local tool URL.

## References

- [Engineering Statics, §9.2: Slipping vs. tipping](https://engineeringstatics.org/Chapter_09-slipping-vs--tipping.html)
- [NHTSA DOT HS 811 486: Static Stability Factor](https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/811486)
- [OSHA: Stability of powered industrial trucks](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.178AppA)

References are linked here and in the tool. There are no downloaded reference
assets or industry test protocols in this version.
