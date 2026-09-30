# Tipping and Stability

Estimate the slope, acceleration, or applied force that brings a rigid cart,
mobile robot, or freestanding assembly to a tipping edge. Compare payload
positions and support layouts, then inspect the forces and moments behind the
result.

The solver uses **3D forces and moments with contacts in one plane**. It finds
tipping onset under static or quasi-static loading. The free-body diagram (FBD)
is a 2D projection normal to a selected support edge.

## Using the tool

The default example is a centered cart with a 1.2 m wheelbase, 0.8 m track,
100 kg mass, and a center of mass 0.6 m above the surface. It has an ideal
lateral tipping angle of 33.69°. The first result loads with the example;
subsequent edits take effect when you press **Calculate stability**.

Choose a slope, acceleration/braking, steady-turn, push/pull, or combined case.
Slope remains active in every case. In combined mode, select the parameter
whose limit you want to find. The other loads stay fixed.

The starting view has four controls: the case, wheelbase, track width, and
center-of-mass height. It shows the platform and one tipping limit. Motion and
force inputs appear when their case is selected; push cases also show total
mass. Open **Slope & direction** to change the ground angle or downhill side.
Choose **Custom angle** for a direction between the four standard sides.

Coordinates are measured from the footprint center in a frame attached to the
surface: x forward, y left, z away from the surface. Direction angles increase
from forward toward left. An actual acceleration at 180° models braking while
traveling forward. Equivalent inertia acts in the opposite direction.

Expand **Customize platform & loads**, then open the section you need: mass
and payload, ground contacts, sliding, or extra loads. Closed sections summarize
the active custom settings. The component table replaces the total mass and
center fields, so include the base assembly. Custom contacts replace wheelbase
and track. A force's positive z component lifts away from the ground.

## Connecting the footprint to the FBD

Study B's world-oriented section was selected for the calculator on 2026-09-29.
The main tool implements its layout in native SVG, keeping linked force selection
and adding no diagram dependency. Projected weight points straight down while
the ground, body outline, and surface axes tilt together.

All eight alternatives remain in the [FBD comparison gallery](prototypes/),
including the original Canvas version of B and the Three.js and JSXGraph trials.
Keep these pages, their saved cases, and the [research notes](prototypes/README.md)
available for future review.

A separate [JSXGraph interaction lab](prototypes/jsxgraph-lab.html) tests
constrained dragging, live moment arms, and automatic label placement. Its
reaction forces and moments come from the same Python equilibrium solver.

A top-down support footprint and B's section are visible together on loading.
The footprint keeps front at the top, left on the left, and right on the right.
Changing slope direction moves the downhill cue and required reaction point;
it does not rotate or foreshorten the footprint. G₀ is the mass center projected
onto the support plane, and R is the required ground-reaction location.
The section shows height and slope, with weight pointing vertically down.
Both views use a linear geometry scale and stay outside the analysis tabs.
**Hide forces & free-body diagram** leaves the footprint visible.
On desktop, long input tables scroll within the input panel so the diagrams
remain beside the controls. On mobile, Calculate returns to the updated diagrams.

Click a force label in the section, or open **Inspect force values &
components** to use the force key. Its application point highlights in the footprint.
The inspector gives its 3D vector and position, its projected components,
and its moment about the selected edge. The edge
selector and clickable support edges update the FBD, footprint, and moment
table together. **Show force balance** opens the source equations.
Footprint edges can also be selected with Tab, then Enter or Space.

The isometric illustration was removed from the main tool on 2026-09-30 after
left/right slopes exposed confusing camera angles and overlapping body faces.
The gallery's orbitable 3D experiment remains available.

Click the main tipping limit for its derivation, or open **Explore results &
calculations** for edge margins, plots, moment tables, exports, and background
equations. Closing these sections leaves the image and primary result visible.

| Label | Meaning |
| --- | --- |
| G | Combined center of mass; m1, m2… locate mass components when supplied |
| G₀ | Mass-center projection onto the support plane in the footprint |
| R | Required ground-reaction location |
| W | Total weight, acting at G |
| I | Equivalent inertia, opposite to prescribed acceleration |
| P1, P2… | Applied loads, at their entered positions |
| N | Required normal ground reaction |
| T | Required tangential ground reaction |

In the FBD, u points inward from the selected edge and z points away from the
support plane. The whole projected section rotates to keep weight vertical.
Its apparent incline can differ from the entered slope for an edge running
obliquely across the hill. h is the mass-center height, dG its distance from the
edge, and dR the required reaction's distance. These distances are available
in the mass-center inspector; dR also appears below the diagram.

Arrow lengths are schematic; the key gives force magnitudes in newtons.
Applied-force arrows start at their application points, and ground-reaction
arrows end at R. Every force arrow stays on its physical line of action.
Only text moves to avoid collisions, with dotted leaders for displaced labels.

Forces along the selected edge lie outside the FBD projection. The inspector
reports those components, and the model explanation reports the residual ground
yaw couple required in addition to N and T. These required reactions do not
prove that individual wheels can supply them. The tool does not calculate
individual wheel loads or yaw capacity.

The image and any open FBD remain after edits or invalid inputs, with a notice
identifying the last calculated case. Numerical results clear when an input is
invalid. Tipping status and any failed sliding check remain in the main view,
even with all analysis sections closed.

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
- Show essential inputs, the top-down footprint and linked FBD, and one primary
  result first. Disclose force values and detailed analysis separately.
  Keep the footprint and any open FBD visible across analysis tabs. The footprint
  shows the support polygon, required reaction, and mass-center projection.
  A direction plot shows gravity-only slope limits.
- Expose numbered equations, substituted values, load contributions, and
  references through the result cards and Background tab.
- Preserve scalar inputs and editable tables in share links. Export the last
  calculated case and results as CSV or JSON; disable exports after an edit
  until the case is recalculated.
- Provide keyboard controls, light/dark/automatic themes, compact spacing,
  and selectable result precision.

## Planned layout changes

The [next UI pass](../../plans/2026-09-30_tipping_stability_ui_streamlining.md)
will put tipping and sliding results together, expose the key results and edge
table, and reduce scrolling. That layout is planned; this README describes the
current calculator. The existing prototype pages will remain available.

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

The browser regression uses the real Pyodide engine and checks the initial
four-control view, keyboard disclosure controls, hidden analysis, diagrams,
derivations, tables, share-link round trips, downloaded exports, themes,
mobile layout, and invalid-input recovery. It also checks matching force/edge
selection and diagram persistence when inputs are edited or invalid. The eight
saved gallery cases also run through the calculator on desktop and mobile,
covering all support edges. Checks verify vertical gravity, exact arrow anchors,
force directions, along-edge symbols, linear geometry, label placement, and
visible reactions outside the footprint. A separate regression checks identical
footprint geometry across left, right, front, and rear slopes, plus keyboard
edge selection and focus after redraw:

```sh
python3 -m http.server 8157 --bind 127.0.0.1
node tests/browser/tipping-stability.cjs
```

`PLAYWRIGHT_MODULE` can point to an installed Playwright package.
`TIPPING_TOOL_URL` or a URL argument can override the default local tool URL.

## References

- [Engineering Statics, §9.2: Slipping vs. tipping](https://engineeringstatics.org/Chapter_09-slipping-vs--tipping.html)
- [NHTSA DOT HS 811 486: Static Stability Factor](https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/811486)
- [OSHA: Stability of powered industrial trucks](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.178AppA)

References are linked here and in the tool. There are no downloaded reference
assets or industry test protocols in this version.
