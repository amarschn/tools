# Cam generator v2 prototypes

Date: 2026-10-17

Seven working prototypes for the next version of the cam profile generator.
They share one calculation engine and one UI kit, and a design made in one
page carries to the next.

Run them from the repository root:

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000/tools/cam-generator/prototypes/`.

## The pages

| Page | Question it answers | What to try |
| --- | --- | --- |
| [A: Motion Sketch](a-motion-sketch.html) | What should the follower do? | Load "Constant-speed pass" and drag the points. Switch between smooth acceleration and smooth jerk. |
| [B: Follower Workbench](b-workbench.html) | Will this cam push the follower cleanly? | Shrink the base circle until the profile turns red, then press Auto-size. Try the swing-arm follower. |
| [C: Sizing Map](c-design-space.html) | How big does the cam have to be? | Make the rise faster and watch the feasible wedge narrow. Switch the vertical axis to roller size. |
| [D: Machine Timing](d-timing.html) | Do several cams on one shaft collide? | The example starts with a collision. Drag the gate stroke earlier until the interlock clears. |
| [E: Spring & Torque](e-dynamics.html) | Will the follower stay on the cam at speed? | Drag the speed past the jump point, then press "Size spring for this speed". |
| [F: Law Lab](f-law-lab.html) | Which motion law suits this rise? | Rank by ringing and change the follower's natural frequency. |
| [G: Make It](g-make-it.html) | How do I cut it? | Compare plate, grooved and barrel cams. Export a DXF and open it in CAD. |

## Files

- `cam-core.js`: the engine. Motion laws (including modified sine and modified
  trapezoid from the SCCA family), boundary-condition polynomials, profile
  generation for translating roller, flat-faced and oscillating roller
  followers, pressure angle, radius of curvature, spring and torque dynamics,
  residual vibration, resampling and DXF output.
- `cam-ui.js`: line charts with crosshair tooltips and drag handles, the
  animated cam and follower view, the segment editor, the theme toggle and the
  design hand-off between pages (browser `localStorage`, key
  `cam-prototypes-design`).
- `proto.css`: design tokens from `DESIGN.md`, plus the chart palette from the
  data-visualization guidance, in light and dark themes.

## Conventions in the engine

- Cam angle θ is in degrees in the arrays. Derivatives of the lift s are taken
  per radian: v = ds/dθ (mm/rad), a = d²s/dθ² (mm/rad²). Multiply by ω, ω² and
  ω³ for time derivatives.
- The cam turns counter-clockwise. Profiles are in the cam's own frame.
- For a swing-arm follower, s is the arc length at the roller, so ψ = s / L
  for arm length L.
- Pressure angle is measured between the common normal at the contact point
  and the direction the roller centre can move. This one definition covers all
  three follower types.

## Checks that were run

- Peak coefficients for every law match published values: cycloidal
  Cv = 2, Ca = 2π; modified sine Cv = 1.760, Ca = 5.528, Cj = 69.47; modified
  trapezoid Cv = 2, Ca = 4.888, Cj = 61.43; 3-4-5 Ca = 5.774.
- The analytic pitch-curve radius of curvature agrees with a finite-difference
  estimate to 0.001 mm. The fast closed form used by the sizing map agrees with
  the general profile routine exactly.
- Undamped residual vibration for cycloidal motion is zero at whole numbers of
  natural periods, as expected.
- All eight pages load in Chromium with no console errors in light and dark
  themes. A scripted run drags keyframes, adds points, hands a design from A
  to B, selects on the map and drags timing strokes.

## Known limits

- Calculations live in JavaScript so they can run on every drag. Production
  needs the same equations in `pycalcs/cams.py`; see the plan in
  `plans/2026-10-17_cam_generator_v2.md`.
- The dynamics model is a single mass on a spring. Spring surge, follower
  stiffness and friction are left out. The Law Lab covers follower stiffness
  separately.
- The barrel cam groove is offset in the developed plane, which is exact at
  the pitch radius only. A tapered roller or 3D toolpath is out of scope.
- Exports are prototypes. Check every file in CAD and against the printed
  scale bar before cutting metal.
