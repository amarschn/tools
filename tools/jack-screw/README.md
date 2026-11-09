# Jack Screw Designer

Design and check a sliding-contact power screw: a screw jack, a machine lead screw, a clamp
spindle. The tool answers the four questions that decide whether the design works, then the
four that decide whether it survives.

## Three levels of detail

The tool opens on a load and a screw size, which is enough for a real answer, and adds inputs
only as you ask for more certainty. Each step buys a different class of answer rather than just
more fields to fill in.

| Step | You enter | You get |
| --- | --- | --- |
| Quick | Load, screw size | Torque, efficiency, whether it holds the load |
| Design | Friction pair, thrust collar, drive, nut length, column length and end fixity | Nut wear, screw body stress, column buckling |
| Detailed | Screw and nut material, running speed, design factor | Whirl margin, nut PV, ball screw comparison |

Under the results is a panel listing what the current answer rests on: which values are standing
in for real ones, and which checks have not run at all. Each row has a button that climbs to the
step holding that input and takes you to it. A field you can see is yours to set. A field you
cannot see is either declared in that panel or its check is skipped, because reporting a buckling
load from an invented column length would be worse than reporting nothing.

The step travels with a shared link, so a link always reproduces the answer its sender saw.

## What it calculates

### Quick

- Torque to raise the load, split between the thread and the thrust collar.
- Mechanical efficiency, with and without the collar.
- Whether the screw is self-locking, and the brake torque needed if it is not.
- Torque to lower the load, or the brake torque needed to hold it.

### Design and Detailed

- Force at a hand lever of a given radius, against what a person can actually push.
- Thread flank bearing pressure against the nut material's wear limit, plus the load the
  first engaged thread actually carries.
- Screw thread shear, root bending, and body von Mises stress at the minor diameter under
  combined axial load and drive torque.
- Column buckling, choosing Euler or the Johnson parabola by slenderness.
- Whirl (critical) speed for a driven screw, and the PV product for the nut.
- A side-by-side comparison against a ball screw of the same lead.

## Why self-locking is judged on the thread alone

Collar friction makes the lowering torque look better than it is. A screw whose thread
back-drives, but which holds because a plain collar is dragging on the frame, stops holding
the day someone greases that collar or swaps it for a thrust bearing. The tool reports
self-locking for the thread alone, and flags the collar-only case as critical.

Static self-locking is also not the same as holding under vibration, which lowers the
effective friction coefficient. Anything that has to hold a load unattended gets a mechanical
brake or pawl regardless of what the calculation says.

## Building a jack from threaded rod

The size dropdown carries metric coarse and UNC threaded rod next to the Acme and trapezoidal
power screws. Rod jacks self-lock easily: the 30 degree flank multiplies friction by
`sec 30 = 1.155`, and a coarse fastener pitch is a short lead, so both terms of the self-locking
inequality move the same way. An M20 at a friction coefficient of 0.15 clears it four times over.

The costs are efficiency, around 10 percent, and wear. A sharp V concentrates contact on a narrow
band and cannot be adjusted as it wears, where a split Acme nut can. The tool flags the thread as
a fastener thread so this is stated rather than assumed.

Two things worth setting correctly. Ordinary rod is class 4.6 or A307 Grade A, near 240 MPa yield
and a third of a purpose-made 1045 screw, so the screw material list carries the fastener grades.
And a standard hex nut is about 0.8 diameters thick, below the 1.0 to 1.5 that stops a nut cocking
on the screw. Choosing a rod size fills in the standard hex nut thickness and names the coupling
nut length, which is the usual fix when flank pressure comes out high.

## Inputs

Load, screw size, thread form and a friction pair are enough for a first answer. Standard
sizes are available from a dropdown: ASME B1.5 general purpose Acme and ISO 2904 metric
trapezoidal, each carrying its published minor diameter. A custom thread derives the minor
diameter from proportional root clearance instead, which runs about 0.1 mm optimistic on fine
pitches.

Friction is the largest uncertainty in a power screw. The preset table gives a starting value
and a published range. Check the design at both ends: the low value is the worst case for
holding the load, the high value is the worst case for torque.

## Method

Torque follows the inclined-plane treatment in Shigley, *Mechanical Engineering Design*, 10th
ed., Section 8-2, with the `sec α` flank-angle penalty for non-square threads. Thread stresses
follow Section 8-3. Columns use Euler above the transition slenderness and the J. B. Johnson
parabola below it, from Sections 4-11 and 4-12. Whirl comes from the first bending eigenvalue
of a uniform beam rather than a tabulated constant, which reproduces the published imperial
lead screw formula `N = 4.76e6 × Cs × d_root / L²` to within two percent.

Assumptions and their limits are listed in the tool's Method tab.

## Files

- `../../pycalcs/power_screws.py`: the calculation module.
- `../../tests/test_power_screws.py`: tests, including the Shigley Example 8-1 validation.
- `test-cases/*.json`: six documented scenarios, run as fixtures by the test suite.
