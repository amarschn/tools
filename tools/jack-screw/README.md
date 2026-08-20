# Jack Screw Designer

Design and check a sliding-contact power screw: a screw jack, a machine lead screw, a clamp
spindle. The tool answers the four questions that decide whether the design works, then the
four that decide whether it survives.

## What it calculates

### Always shown

- Torque to raise the load, split between the thread and the thrust collar.
- Mechanical efficiency, with and without the collar.
- Whether the screw is self-locking, and the brake torque needed if it is not.
- Torque to lower the load, and the force at a hand lever of a given radius.

### Expert mode, once a nut length and a column length are entered

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
