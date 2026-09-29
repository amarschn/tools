# Free-body diagram studies

Date: 2026-09-29

Open [the comparison gallery](index.html) through the local web server:

```sh
python3 -m http.server 8157 --bind 127.0.0.1
```

Visit `http://127.0.0.1:8157/tools/tipping-stability/prototypes/`.
This is a design experiment on `task/tipping-analysis`. A final diagram style
has not been selected for the calculator.

## Comparing the studies

| Study | Technique | What to inspect |
| --- | --- | --- |
| A: Textbook section | Native SVG, surface coordinates | Whether precise force anchors and a plain outline are enough for the main FBD. |
| B: World-oriented section | Canvas 2D, rotated section | Whether vertical gravity makes the slope easier to understand. |
| C: One force at a time | SVG small multiples | Several forces at the same point, along-edge components, and forces with small projected magnitudes. |
| D: Moment about the edge | SVG force line and perpendicular arm | The relationship between application point, line of action, and tipping moment. |
| E: Orbit the assembly | Three.js, orthographic camera | Attachment points and vectors that disappear in a 2D projection. |
| F: Geometry board | JSXGraph SVG renderer | Native arrow/point objects, pan, zoom, and the dependency's effect on implementation and appearance. |
| G: Labels outside the body | SVG with a separate label column | Whether names and values remain legible when several arrows share one point. Select a label to trace its force. |
| H: Plan and section | Linked SVG views | Select a support edge in the plan and check that the adjacent section is easy to identify. |

All studies share eight solver-generated cases and the selected support edge.
The cases include level ground, cross slope, an elevated push, turning on a
slope, a triangular footprint with oblique loads, four forces sharing the mass
center, tipping onset, and an outside reaction. “Inspect force” highlights the
same force across the views. Expand a study or choose it from “View” to give it
the full available width.

Schematic arrow lengths are the default so small forces remain visible.
Proportional mode uses one scale for the projected vectors within each 2D study
and one scale for full 3D vectors in E. A force directed along the viewing axis
has no 2D arrow; its dot/cross symbol marks the application point. C reports
along-edge components, and the force table includes every component.

“Anchor guides” adds crosshairs at physical application points. The review URL
preserves the case, edge, force, study, arrow scale, and guides. Theme follows the
device by default and can be changed in Settings.

## What was wrong with the current diagrams

The current `../visualization.js` shifts W and N sideways in screen coordinates:
10 px in the isometric model and 12 px in the section. T also moves down by 9 px.
Dotted leaders connect the shifted arrows to the original positions. This
separates crowded arrows, but the shafts no longer pass through the displayed
mass center or reaction point. The displacement changes the apparent moment arm.

These studies never translate a force sideways. Applied force arrows start at
their application points. Reaction arrows end at their contact point, so N can
be drawn below R while weight starts at G. Both conventions preserve direction
and line of action. Only text labels move to avoid collisions.

One force per panel solves overlap without moving forces. An orbitable view
provides another way to distinguish coincident projections. Proportional arrow
lengths bring a separate problem: small forces can disappear under a point
marker. The explicit scale selector makes that tradeoff reviewable.

## Research, checked 2026-09-29

The recommendations below are judgments about this tool, based on the linked
project documentation. None of these libraries supplies the tipping solver.

### Meclib: closest specialist reference

[Meclib](https://github.com/mkraska/meclib) builds mechanics illustrations and
interactive free-body diagrams on JSXGraph. Its objects include supports,
loads, bars, ropes, disks, and annotations. It targets Moodle STACK and accepts
object descriptions from Maxima lists.

It is the closest match for a library of mechanics symbols. The STACK feedback
and authoring machinery is unnecessary for this calculator. The repository
overview did not establish reuse permission, so this experiment copies none of
its implementation. Its FBD examples are useful design references.

### PrairieLearn pl-drawing: explicit anchors

[pl-drawing documentation](https://docs.prairielearn.com/pl-drawing/) defines
vectors with an `anchor-is-tail` option, including a vector whose head is at the
anchor. It also describes force, moment, point, and support objects. The
client renderer uses Fabric.js and `mechanicsObjects.js`.

This is the most useful convention to adopt immediately: an arrow object
should carry its application point and whether its head or tail meets it.
The experiments implement that rule independently. The current
[PrairieLearn license](https://raw.githubusercontent.com/PrairieLearn/PrairieLearn/master/LICENSE)
places client JavaScript under AGPL terms with separate provisions for
third-party and other contributed code. No PrairieLearn source is included.

### PrairieDraw: engineering drawings in physical coordinates

[PrairieDraw documentation](https://docs.prairielearn.com/PrairieDraw/) describes
coordinate transforms, arrows, labels, and engineering figure conventions.
The docs explicitly recommend pl-drawing for new PrairieLearn questions.

Study B uses the general approach of drawing in a physical coordinate system
and applying one transform to the body, points, and vectors. It is original
Canvas code, not a PrairieDraw integration. There is no reason to adopt the
older runtime for this prototype.

### JSXGraph: working trial in F

[JSXGraph documentation](https://jsxgraph.org/docs/) covers points, arrows,
segments, polygons, labels, SVG rendering, and interaction. The library offers
MIT and LGPL licensing choices. F uses version 1.13.3 under
[MIT](vendor/LICENSE.MIT), with the runtime vendored for repeatable local review.

F constructs the same scene as A with fixed JSXGraph objects. Pan and zoom come
from the library; this trial uses our shared label positions. It does not yet
exercise JSXGraph's dependent geometry or automatic label placement.

JSXGraph has [dependent points](https://jsxgraph.org/docs/Point.html),
[automatic label positioning](https://jsxgraph.org/docs/Label.html#autoPosition),
and [measurement labels](https://jsxgraph.org/docs/Smartlabel.html). Automatic
positioning searches nearby locations to reduce overlaps; it is disabled by
default. These features deserve a separate trial before deciding whether to
use JSXGraph for diagrams that users can edit by dragging geometry.

For the current calculator, native SVG gives us direct control over drawing
order, arrowheads, text, themes, and standalone vector output. It requires us
to implement coordinate transforms, label layout, and any dragging or zoom.
JSXGraph supplies a geometry model and interactions, but adds its own object
lifecycle, configuration, and dependency updates. The pinned runtime in this
gallery is 969,075 bytes, or about 251 kB compressed with gzip.

Neither option determines the correct application point or solves equilibrium.
Those still come from Python. My preference is a small SVG drawing layer for
generated FBDs, with JSXGraph reserved for geometry that users directly
manipulate. The current A/F comparison alone cannot settle that second use case.

### Three.js: working trial in E

[ArrowHelper](https://threejs.org/docs/pages/ArrowHelper.html) accepts a 3D origin,
unit direction, and length. E uses those objects with OrbitControls and an
orthographic camera. A narrow cylinder replaces each one-pixel WebGL shaft for
legibility; its axis and endpoints remain on the original arrow.

The surface frame rotates into the world frame with the slope. Weight is
vertical in world coordinates. The model, points, and arrows share that
rotation. An open outline avoids opaque geometry hiding the mass center.
Labels are projected separately, so they stay readable while orbiting.

Three.js 0.180.0 and its MIT license already exist in the repository. E reuses
those files, with no duplicate download. If adopted, move the dependency into
a shared vendor directory and update both tools. The 3D view requires WebGL;
the gallery reports an unavailable context while leaving the other studies
usable.

### Konva: an editor option

[Konva Arrow](https://konvajs.org/api/Konva.Arrow.html) has configurable points,
arrowheads, and start/end pointers. It is a general Canvas drawing library.
It would help if users need to draw or rearrange a diagram, but the current
tool generates a known scene. There is no Konva runtime trial here.

## Initial preference

A is the clearest main FBD. D is useful when a user asks how a force contributes
to tipping. E earns its space when 3D attachment points are ambiguous. B makes
slope more apparent, while C handles a crowded load case without displaced
arrows. G provides more space for force names and values. H connects the section
to the footprint and makes edge selection visual. F is an implementation
comparison; its fixed scene does not show all of JSXGraph's capabilities.

## Data and verification

`generate_cases.py` calls the production `pycalcs.stability.analyze_tipping`
function and records its source hash. `cases.json` contains its equilibrium,
free-body, mass, and threshold results. No second stability solver runs in
JavaScript. Regenerate or verify the fixtures with:

```sh
python3 tools/tipping-stability/prototypes/generate_cases.py
python3 tools/tipping-stability/prototypes/generate_cases.py --check
python3 -m pytest tests/test_stability.py -q
node tests/browser/tipping-fbd-prototypes.cjs
```

The browser checks compare W's tail against G and N's head against R in the
rendered SVG. They also check the 3D arrow endpoints against the solver points,
vertical gravity in B, all eight cases and 31 edge combinations in both arrow
scales, force selection, keyboard focus after redraw, linked plan selection,
themes, narrow screens, camera controls, board zoom, and review-link state.
Screenshots go to `/private/tmp/tipping-fbd-prototypes/`.

The outline is illustrative. It does not define additional body geometry or
mass. Reactions show the resultants required for equilibrium; an outside
reaction is infeasible for the modeled contacts. The required residual yaw
couple is listed below the gallery. Individual wheel loads, friction
distribution, and yaw capacity remain outside the solver's scope.
