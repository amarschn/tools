# Tipping and Stability Tool: Specification

Date: 2026-09-16
Status: Implemented and verified on the task branch; publication deferred by the user

The first application is low-speed vehicles, carts, and mobile robots, as selected
by the user. Build a reusable rigid-body equilibrium model that can also support
chairs and freestanding equipment. The initial product estimates tipping onset
and the remaining margin for a specified load case.

## How the disciplines divide the problem

The mechanics overlap, but each industry chooses different support models,
load cases, acceptance criteria, and physical tests.

| Application | Typical analysis | Distinguishing requirements |
| --- | --- | --- |
| Road vehicles | Static rollover propensity, steady cornering, and transient rollover resistance | Suspension and tire deformation, steering history, and individual wheel unloading matter. NHTSA combines a geometric Static Stability Factor with a dynamic driving maneuver. [NHTSA ratings](https://www.nhtsa.gov/ratings) |
| Industrial trucks and forklifts | Longitudinal and lateral stability with a specified payload and lift configuration | The effective support geometry can differ from the wheel footprint. A pivoting rear axle produces the familiar stability triangle. The ISO 22915 series separates tests by truck type and special operating condition. [OSHA stability explanation](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.178AppA), [ISO 22915-1](https://www.iso.org/standard/85873.html) |
| Mobile robots and manipulators | Margin to a tipping edge under gravity, motion, payload movement, and task forces | Arm configuration, external forces, and terrain can change the limiting condition. Research includes force-angle measures that account for inertial and external loading on uneven terrain. [Papadopoulos and Rey](https://nereus.mech.ntua.gr/Documents/pdf_ps/ICRA96.pdf) |
| Agricultural and off-road machinery | Stability in specified machine configurations and terrain conditions | Machine-specific standards determine scope. ISO 16231-1 addresses certain self-propelled agricultural machines and explicitly excludes agricultural tractors covered by other standards. [ISO 16231-1 scope](https://committee.iso.org/cms/live/live/en/sites/isoorg/contents/data/standard/05/59/55941.html?browse=ics) |
| Cranes and lifting equipment | Load capacity versus reach, direction, counterweight, and support configuration | Stability capacity, structural capacity, and ground support are separate checks. ISO 4305 addresses mobile-crane stability calculations under defined surface conditions. [ISO 4305](https://www.iso.org/standard/57220.html), [OSHA load-chart and site criteria](https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926SubpartCCAppC) |
| Chairs and seating | Stability under prescribed loading and chair adjustment configurations | Occupant loading and the positions of feet or casters are central to the model. EN 1022 and ANSI/BIFMA X5.1 provide product-specific test methods. A generic calculation does not reproduce their test programs. [EN 1022 scope](https://www.dinmedia.de/en/standard/din-en-1022/374502363), [BIFMA overview](https://www.bifma.org/page/standardsoverview) |
| Wheelchairs and mobility scooters | Static tipping angles and, for powered chairs, dynamic stability tests | Occupant configuration and anti-tip devices matter. ISO 7176-1 and ISO 7176-2 explicitly separate static and dynamic testing. [Static stability](https://www.iso.org/standard/56817.html), [Dynamic stability](https://www.iso.org/standard/57753.html) |
| Cabinets and storage furniture | Stability with extended drawers, stored contents, and applied loads | Product-specific testing includes configurations such as open drawers and carpet simulation. Clothing-storage-unit requirements have a defined scope, not universal applicability to furniture. [CPSC guidance](https://www.cpsc.gov/Business--Manufacturing/Business-Education/Business-Guidance/Clothing-Storage-Units) |
| Civil structures and foundations | Overturning or eccentricity checks alongside sliding, bearing, and other failure modes | A gravity-supported block shares the basic moment balance. Soil contact, anchors, and structural deformation require additional models. FHWA distinguishes overturning from footing liftoff and shows that methods differ by wall type. [FHWA discussion](https://www.fhwa.dot.gov/publications/research/infrastructure/bridge/14094/004.cfm) |

These references establish the landscape and terminology. Public standard
abstracts are not sufficient to implement a standards compliance mode; that
would require the applicable full text, edition, test setup, and acceptance rules.

## Analysis levels

1. **Static:** gravity, a fixed configuration, slope, and slowly applied loads.
2. **Quasi-static motion:** represent prescribed acceleration by an equivalent
   inertial force while holding the body configuration fixed. This covers an
   idealized steady turn or braking condition.
3. **Transient dynamics:** calculate motion over time, including suspension,
   angular inertia, damping, impacts, changing contacts, and moving loads.

Version 1 covers the first two levels. Low travel speed does not make curb
impacts or abrupt stops quasi-static. The result describes equilibrium loss under
the modeled loading; it does not predict the complete overturning motion.

## First version

Name: **Tipping and Stability**

Location: `tools/tipping-stability/`

Purpose: show how support geometry, center of mass, payload, slope, acceleration,
and applied forces affect the onset of tipping in a rigid cart or mobile robot.

### Supported geometry and configuration

- One rigid assembly on one rigid, planar surface, which may be inclined.
- Rectangular wheel footprint by default, specified by wheelbase and track.
- An advanced editor for three or more fixed, coplanar contact points. Use their
  convex hull, the smallest convex boundary enclosing those points, as the
  support polygon.
- Actual tire or foot contact coordinates define the model. Body dimensions,
  caster mounting positions, and wheel centers above the surface do not.
- One total mass and center of mass, or a component table with mass and position
  for the base, battery, payload, occupant, and other components. These are
  alternative ways to define the same mass model; do not count a payload twice.
- Coordinates use a surface-fixed frame: x forward, y left, z normal to the
  surface and away from it. Show the axes in the diagram.
- Caster orientation remains fixed for a case. A later configuration sweep can
  investigate different contact locations.

Pivoting axles, rocker-bogie mechanisms, suspension compliance, rocking feet,
and noncoplanar terrain need their own support models. A four-wheel footprint
must not silently stand in for one of those systems. The custom triangle in
version 1 represents three rigid ground contacts, not a complete forklift model.

### Load cases

| Case | Inputs beyond geometry and mass | Primary result |
| --- | --- | --- |
| Parked on a slope | Slope magnitude and downhill direction | Critical slope in that direction and remaining angular margin |
| Acceleration or braking | Signed acceleration in the surface plane | Acceleration threshold in the selected direction |
| Steady turn | Speed, turn radius measured at the center-of-mass path, and turn direction | Lateral tipping threshold and corresponding idealized speed |
| Push or pull | Force vector and application point | Force threshold for the chosen direction and point |
| Combined case | Slope plus prescribed acceleration and applied forces | Current signed margin and limiting support edge |

The combined case uses the same equilibrium calculation as the simpler cases.
Threshold calculations must state which parameter is varied and which others
are held fixed. A level-ground turning threshold is not reused unchanged on a
cross slope.

Stationary slope and push cases require a defined restraint against rolling.
Do not use tire friction as a substitute for a brake on a freely rolling wheel.
Version 1 assumes the required rolling restraint or prescribed motion and makes
that assumption visible beside the case inputs.

### Default experience

Start with the rectangular cart and a slope case. Show wheelbase, track,
center-of-mass height, slope magnitude, and downhill direction. Start the center
of mass at the footprint center. Keep offsets, mass components, friction,
additional forces, and custom contacts in expandable sections.

Use an explicit Calculate button and a valid prefilled example. An illustrative
default is a 1.2 m wheelbase, 0.8 m track, 0.6 m center-of-mass height, 100 kg total
mass, and level ground. Defaults are example geometry, not a rated product.

For this default, the ideal lateral tipping angle is 33.69 degrees and the
level-ground lateral acceleration threshold is 0.667 g. State the rigid-body and
contact assumptions next to these results. Mass can remain in advanced inputs
for a pure gravity slope calculation because it cancels from the angle.

### Results and visualizations

- Make the case-specific threshold the primary number, with the current demand
  and remaining margin beside it.
- Show the limiting edge and all edge margins in an expandable table.
- Draw a plan view with contacts, support polygon, center-of-mass projection,
  and the required normal-reaction location. Distinguish the last two points
  when horizontal forces or acceleration are present.
- Draw a side section perpendicular to the limiting edge with gravity,
  applied loads, and the relevant lever arms.
- Provide a direction plot of critical slope or acceleration. It should expose
  the weak direction for triangular, asymmetric, and custom footprints.
- Expand a result to show the equation, substituted inputs, individual moments,
  and final value, following the repository's disclosure pattern.
- Support a shareable case and CSV export of inputs, assumptions, and edge
  results. A formula-bearing Excel export is a later extension.

Use labels such as "Positive tipping margin", "At tipping threshold", and
"Beyond tipping threshold". Any design target is a separate, explicitly chosen
criterion. Do not invent a universal industry safety factor.

## Calculation model

The authoritative calculations belong in a dependency-free Python module, with
the frontend responsible for inputs and drawing. The equations below are the
proposed model and analytical checks, derived from force and moment balance.

### Mass properties

Equation (1):

\[
m = \sum_j m_j, \qquad
\mathbf r_G = \frac{\sum_j m_j\mathbf r_j}{m}
\]

`m`: total mass; `j`: component index; `m_j`: component mass; `r_j`: component
center-of-mass position; `r_G`: combined center-of-mass position.

### Equivalent applied loading

Equation (2):

\[
\mathbf F = m(\mathbf g-\mathbf a) + \sum_k \mathbf F_k
\]

`F`: resultant non-contact force, including equivalent inertia; `g`: gravity
resolved in surface coordinates; `a`: prescribed translational acceleration;
`k`: applied-force index; `F_k`: external applied force. Accelerations and
gravity must use the same coordinate frame.

Equation (3):

\[
\mathbf M = \mathbf r_G\times m(\mathbf g-\mathbf a)
  + \sum_k \mathbf r_k\times\mathbf F_k
\]

`M`: resultant non-contact moment about the surface-frame origin; `r_k`:
application point of force `F_k`; the other terms are defined above.
Independent applied couples can be added later without changing the contact
calculation. Angular acceleration and moving-component inertia are outside
version 1.

### Required normal reaction and tipping margin

Equation (4):

\[
N=-F_z,\qquad
p_x=\frac{M_y}{N},\qquad
p_y=-\frac{M_x}{N}
\]

`N`: total compressive normal reaction; `F_z`: surface-normal component of `F`;
`M_x`, `M_y`: surface-plane components of `M`; `p_x`, `p_y`: location of the
required resultant normal reaction in the support plane. Require `N > 0`.

For fixed compression-only contacts, this point must lie inside the support
polygon to admit a normal-force equilibrium. The boundary is the tipping
threshold. This is a tipping condition, not a complete friction or contact
wrench feasibility test.

Equation (5):

\[
d_i = \mathbf n_i\cdot(\mathbf p-\mathbf v_i),\qquad
M_{\mathrm{reserve},i}=N d_i
\]

`i`: support-edge index; `n_i`: inward unit normal to the edge in the support
plane; `p`: required reaction point; `v_i`: any point on that edge; `d_i`: signed
distance to the edge; `M_reserve,i`: restoring moment reserve about that edge.
Positive reserve lies inside the edge; zero is the limiting condition.

Retain the applied-force breakdown so the derivation can show which loads
stabilize or overturn about a chosen edge. If a moment ratio is displayed,
define its numerator and denominator and handle zero overturning moment.

### Simple analytical checks

For a rigid body initially on level ground with no other applied loads:

Equation (6):

\[
\theta_{\mathrm{crit}}=\tan^{-1}\!\left(\frac d h\right),\qquad
a_{\mathrm{crit}}=g\frac d h
\]

`theta_crit`: slope at tipping when tilted toward an edge about an axis parallel
to it; `a_crit`: acceleration magnitude whose equivalent inertial force acts
toward that edge on level ground; `g`: gravitational acceleration magnitude;
`d`: initial in-plane distance from the center-of-mass projection to that edge;
`h`: center-of-mass height above the plane. These are separate load cases.

For a centered vehicle with rectangular contacts, the lateral value of `d` is
half the track. This gives the familiar ideal geometric ratio of track divided
by twice center-of-mass height. NHTSA calls this ratio the Static Stability
Factor; it is not the complete dynamic rollover assessment.
[NHTSA definition](https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/811486)

For a horizontal push normal to an edge, on level ground with no other applied
loads and enough restraint to prevent translation:

Equation (7):

\[
F_{\mathrm{crit}}=\frac{mgd}{z_F}
\]

`F_crit`: push force at tipping; `z_F`: force application height above the plane;
`m`, `g`, and `d`: as defined above. A 100 kg body with `d = 0.4 m` pushed at
`z_F = 1 m` reaches the ideal tipping threshold at about 392 N.

These relations connect vehicle and furniture cases, while also showing why
mass cancels from the ideal slope and acceleration limits but affects push force.

### Sliding and wheel reactions

Offer an optional aggregate sliding comparison for restrained contacts with an
assumed uniform Coulomb friction coefficient. Label it as a translation check;
it does not prove that each tire can supply the necessary traction or resist
an arbitrary yaw moment. If friction is unknown, report sliding as unevaluated.
The earlier limit can be sliding rather than tipping.
[Engineering Statics](https://engineeringstatics.org/Chapter_09-slipping-vs--tipping.html)

Do not report unique normal forces at four or more individual contacts from
rigid-body equilibrium alone. Their distribution generally needs stiffness,
suspension, or another stated load-sharing model. First individual wheel lift,
loss of equilibrium about a support edge, and completed overturn are different
events.

## Implementation outline

Implementation requirements:

- Start from `tools/example_tool_advanced/index.html` and follow `DESIGN.md`.
- Use `pycalcs/stability.py` for mass combination, contact geometry, applied-load
  equilibrium, edge margins, and parameter-limit searches.
- Expose a documented tool entry point with the repository's parameter, return,
  LaTeX, and `subst_<result_key>` conventions. Avoid duplicating mechanics in JS.
- Add a tool README, a tool-local references directory when assets are needed,
  and focused tests in `tests/test_stability.py`.
- Add catalog and discoverability metadata only with the implemented tool.
- Verify light and dark themes, mobile layout, keyboard access, derivations,
  sharing, and export using the required tool release checklist.

Analytical acceptance cases should include centered and offset rectangles,
three-point supports, gravity-only slope limits, acceleration and braking sign
checks, an applied push, combined loading, an initially unstable payload, zero
normal reaction, degenerate contacts, and a case where sliding precedes tipping.
Check invariance under translation and in-plane rotation of the coordinate
system. The formulas in Equations (6) and (7) provide independent known results.

## Follow-on scope

Chairs and freestanding equipment can reuse the same solver through support,
occupant, and force presets. Their industry test sequences would be separate
features. Next candidates include payload-position sweeps, uncertainty ranges
for center of mass, and a worst-case caster orientation study.

Suspended road vehicles, articulated chassis, curb impact, soft ground,
time-dependent arm motion, rocking after lift-off, and anchored foundations
require additional mechanics. Treat them as separate extensions rather than
extra fields that imply the first model already covers them.

Custom contacts and component mass tables are included in the first version,
behind advanced controls. They support the selected robot and cart applications
and allow later furniture presets to reuse the same calculations.

## Implementation and verification, 2026-09-16

Implemented on `task/tipping-analysis`:

- `pycalcs/stability.py`: convex support hull, component mass properties,
  rigid-body equilibrium, edge reserves, optional aggregate sliding check,
  and analytical slope/acceleration/force/steady-turn thresholds.
- `tools/tipping-stability/`: advanced-template interface, five load cases,
  custom contacts and mass/force tables, footprint and section diagrams,
  gravity-only direction envelope, derivations, share links, CSV and JSON.
- Numbered equations, variable legends, and tooltips come from the Python
  source. Exports use the last calculated case and are disabled after edits.
- Catalog registration, homepage fallback link, sitemap, tool metadata, README,
  and a separate roadmap for future models and export options.

Verification:

- 33 mechanics tests cover independent analytical results, sign conventions,
  coordinate invariance, combined loads, root tangencies, friction, and invalid
  input handling. Ruff checks pass for the new Python module and tests.
- The real-Pyodide browser regression passes all five load modes, diagrams,
  rendered derivations, input help, keyboard tabs, editable tables, share-link
  round trips, downloaded exports, light/dark/automatic themes, persisted
  precision and density, mobile layout, and invalid-input recovery.
- Reviewed desktop light/dark and mobile screenshots. Section labels retain
  their size on narrow screens. The default example is 33.6901°; a level-ground
  100 kg cart pushed at 1 m tips at 392.266 N under the modeled restraint.
- Applied `avoid-ai-writing` in edit mode to the page and README. Simplified
  the acceleration explanation to active voice; retained the technical scope
  and constraints. Re-read both files after the edit.
- Full suite: `python3.13 -m pytest -q` passes with 1,636 tests and 2,611
  subtests. Python 3.13 is required by the existing materials suite; the
  calculation module also runs with the browser's Python environment.
- Generated homepage metadata after the initial task commit. The production
  build command, `python3 scripts/build_site.py`, passes. SEO dry-run reports
  zero pending changes. No `human-verified` badge was added.

The user requested that this work stay on `task/tipping-analysis`. Production
publication is deferred. No merge or push to `main` is authorized by the current
request. Any later publication follows `docs/RELEASE.md`.

### Visualization revision

The user requested an always-present image with a clear link to a free-body
diagram, and chose a fixed isometric schematic. The revision makes the model's
dimensionality explicit: 3D force and moment balance with planar contacts, paired
with a 2D projection normal to the selected edge.

- Physical model and FBD appear together above numerical results, outside tabs.
- The fixed isometric view shows the chassis, contacts, mass locations, inclined
  ground, and labeled forces. Body/wheel dimensions are illustrative.
- Selecting an edge updates both views, the plan view, and the moment table.
  Selecting a force or G highlights it in both views and shows its coordinates,
  projected components, and moment contribution.
- The Python output supplies W, I, P1… , N, T, and the required residual ground
  yaw couple. Required reactions are distinguished from verified wheel capacity.
- Force/component labels are placed without overlapping in the tested cases.
  Leaders preserve their connection to physical points. Out-of-plane force
  components are disclosed in the inspector and beside the FBD.
- Edits and invalid inputs retain the last valid diagram with a visible state
  message. Invalid input clears numerical results and disables the edge and
  derivation controls until a valid calculation succeeds.
- CSV and JSON include the named FBD forces and their numerical components.
- Added analytical tests for full contact-wrench balance and FBD projection.
  There are now 36 tipping tests. The browser regression also covers shared
  labels/edges, vertical gravity on a slope, image persistence, and text bounds
  and overlaps on desktop/mobile layouts.

The revised full suite passes with 1,639 tests and 2,611 subtests. Browser checks
pass in light, dark, and system themes, including the linked diagrams. The
page and README received the required writing review. Changes remain on
`task/tipping-analysis` for the user's review.

### Progressive disclosure revision (2026-09-17)

The user found the revised tool too complex on first use. The starting view now
shows the case and three geometry inputs, one tipping limit, and the fixed
isometric image. Slope and direction have their own disclosure. Platform
customizations open into separate mass, contact, friction, and extra-load
sections. Short summaries identify settings that affect the calculation even
when the controls are closed. Push cases show total mass beside the other
essential inputs.

The image starts with a center-of-mass marker and forward direction. Its
**Show forces & free-body diagram** control adds the linked force overlays and
FBD. Force vectors and the inspector have a further disclosure. A separate
**Explore results & calculations** section contains the result cards, plots,
moment tables, exports, and theory; clicking the main result opens its
derivation directly. This changes presentation only, with all mechanics still
provided by the Python module. The task remains on its branch for review.

Verification passed: 1,639 Python tests and 2,611 subtests, the site build,
and the real-Pyodide browser regression. The browser checks cover the four-input
default, keyboard disclosure and focus, all load cases, linked force selection,
arbitrary downhill angles, shared cases, CSV/JSON downloads, and error recovery.
Tipping and sliding warnings remain visible with the analysis closed. Reviewed
desktop and mobile screenshots in light and dark themes, corrected overflow
from table accessibility labels, and applied the writing review to page and
README copy.
