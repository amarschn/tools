# Interference Fit Calculator

## Purpose

Size or check a straight cylindrical shaft-hub interference fit. **Size** mode solves for the
diametral interference range from the torque and axial load the joint has to carry. **Check**
mode takes an interference band you already have and reports pressure, slip margin, strength
margin, and fit loss across temperature and speed.

## Core Workflow

1. Pick a mode. Size solves for interference; Check evaluates a fit you already have.
2. Enter the duty: required torque and maximum speed, or the interference band, applied
   torque, operating speed, and operating temperature.
3. Enter fit diameter, hub outside diameter, contact length, and shaft bore.
4. Select shaft and hub materials, and the surface finish on each.
5. Set the service temperature range (Size mode).
6. Calculate.
7. Use Expert Mode to add axial load, pick a friction pair, change safety factors, set the
   slip clearance and length credit, set the assembly temperatures you plan to use, or define
   custom material properties.

Results switch between metric and inch units from the Settings panel. Interference reads in
micrometres or mils, which is how tolerances actually get discussed.

## Primary Outputs

### Size mode
- Required minimum and allowable maximum diametral interference at drawing temperature
- Recommended midpoint target and bilateral manufacturing tolerance
- ISO 286 grading of the resulting window, split evenly between shaft and bore
- Governing service temperature, speed, and member
- Contact pressure, torque capacity, slip safety factor, and strength safety factor
- Every way of assembling the joint, compared on one axis: press force
- Press force at whatever assembly temperatures you plan, and what that saves
- Push-off force

### Check mode
- Contact pressure cold and hot, and the interference left after roughness smoothing
- Slip and strength safety factors across minimum, nominal, and maximum interference
- Temperature at which the fit loses contact pressure
- Interference lost to centrifugal growth at speed
- The same assembly plan and forces

## Model

The lower interference limit comes from the contact pressure needed to resist the vector
combination of circumferential and axial interface traction:

`p_req = SF_slip sqrt((2T/d)^2 + F_a^2) / (mu pi d L_eff)`

Torque and axial load share one friction budget, so they combine as a resultant rather than
being checked one at a time. The pressure converts to diametral interference through the
combined thick-cylinder elastic compliance of the shaft and hub.

Three effects then separate the interference on the drawing from the interference that makes
pressure in service:

- **Roughness smoothing.** Asperity peaks flatten at assembly. Following DIN 7190, the tool
  charges `0.8 (Rz_shaft + Rz_bore)` against the specified diametral interference.
- **Differential thermal expansion**, evaluated at both ends of the service envelope.
- **Centrifugal growth**, from free rotating disk and annulus theory.

The upper limit is solved numerically. Lame contact-pressure stresses are superimposed with
rotating stresses at maximum speed, and the first shaft or hub location to reach its strength
limit governs. Ductile members use von Mises against yield. Brittle members such as gray iron
have no yield point and carry roughly three to four times more compression than tension, so
they use Coulomb-Mohr against separate tensile and compressive strengths.

Contact pressure and micro-slip concentrate at the ends of the joint, so only the first
L/d = 1.5 of contact length is credited with carrying load by default.

## Assembly

Two questions get answered here.

**What would let the parts slip together with no press at all?** The tool solves for that:
hub heating alone, shaft chilling alone, or both together, each checked against what is
physically sensible (liquid nitrogen at the cold end, normal shop practice at the hot end).
Heating alone is the cheapest thing a shop can do, so it wins when it works.

**What does the temperature I actually plan to use leave me to push through?** Enter the hub
and shaft temperatures you intend, and the tool reports the interference still in the way and
the press force it takes, against the cold baseline. This is usually the more useful number,
because fully clearing a fit often needs more heat than the part can take, while heating it
part way removes most of the force. On a 50 mm steel joint with 90 um of interference:

| Plan | Interference left | Press force | Removed |
| --- | --- | --- | --- |
| Ambient | 90 um | 238 kN | 0% |
| Hub to 100 C | 42 um | 111 kN | 53% |
| Hub to 150 C | 12 um | 31 kN | 87% |
| Hub to 150 C, shaft to -40 C | none, slips on | 0 kN | 100% |

Leave both temperatures blank to assemble at ambient.

The panel reads as an answer rather than a table. It opens with the shortest true sentence
about what to do ("Heat the hub to 186 C and it drops on", or "Press it together with 936 N,
no amount of heating or chilling opens this joint"), then lists every route against the one
number that lets you compare them, the press force it leaves. Routes that cannot be reached
are dimmed and say why, and a temperature nobody could produce reads as "beyond reach" rather
than a spurious figure like -755.3 C.

Both forces are quoted for the tightest interference you would actually build: in Size mode
that is the allowable maximum, which is the same thing as the recommended target plus its
tolerance, and in Check mode it is the maximum you entered. The panel names the number it
used. When no feasible window exists there is no band to release, so the force is quoted
against the required minimum and labelled as such.

Both use the same contact pressure, from the interference left after roughness smoothing.
They differ only in friction: sliding one part into the other galls, so insertion friction
runs above the settled slip value. The multiplier defaults to 1.5, following DIN 7190's
practice of treating the two coefficients separately, and is adjustable in Expert Mode.

## Scope

### Included

- Straight cylindrical press fits and shrink fits, solid or hollow shafts
- Thick-cylinder elastic compliance
- Simultaneous torque and axial traction, combined as a resultant
- Minimum and maximum uniform service temperatures
- Free centrifugal growth and superposed rotating stress
- Surface roughness smoothing loss
- Ductile and brittle failure criteria
- ISO 286 grading of the manufacturing window
- Thermal assembly plan, with press force at whatever assembly temperatures you plan
- Push-off force

### Not Included

- Plastic fits or contained plasticity past first yield, which DIN 7190 permits. The tool is
  conservative for ductile hubs as a result.
- Plane-strain compliance. Stresses and compliance are plane stress, the standard textbook
  treatment. A long hub is closer to plane strain, where the joint is roughly ten percent
  stiffer and the contact pressure correspondingly higher.
- Tapered, keyed, splined, grooved, or split joints
- Shoulders and other axial constraints on centrifugal growth
- Fretting fatigue and micro-slip life
- Thermal gradients, transients, or temperature-dependent properties
- Local end effects and stress concentrations
- ISO 286 fit designations (H7/s6 and the like). The window is graded by IT number only,
  because the tool does not carry the fundamental deviation tables those letters need.

## Materials

Every preset states its condition (annealed, normalized, quenched and tempered, as cast) and
its source, and declares which failure criterion applies. Check the condition before trusting
a number: annealed 4140 and quenched-and-tempered 4140 differ by nearly a factor of two in
yield strength, and that factor lands directly on the allowable interference. The AISI 52100
preset is for through-hardened bearing steel at 65 to 68 HRC, not annealed bar stock.

## References

- Budynas and Nisbett, *Shigley's Mechanical Engineering Design*, interference-fit and
  rotating-disk relations
- Timoshenko and Goodier, *Theory of Elasticity*, Lame cylinders and rotating annuli
- DIN 7190, interference fits: smoothing loss and friction coefficient ranges
- ISO 286-1, tolerance grades
- ASM Metals Handbook, ASTM A48 and A536, and CDA alloy data for the material presets
- ideal-tek, [*Ball bearing steel type CR*](https://www.ideal-tek.com/public/files/550-TDS_Ball_bearing_steel_type_CR.pdf),
  AISI 52100 technical data sheet

## Status

Both modes have automated regression coverage in `tests/test_interference_fits.py` and
`tests/test_interference_fits_audit.py`, and both have been exercised end to end in a browser
across metric and inch units. Treat results as a screening model, not a release calculation.
