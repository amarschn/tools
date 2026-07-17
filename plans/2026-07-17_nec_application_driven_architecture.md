# NEC Wire Sizing — Application-Driven Architecture (Deep Dive)

Date: 2026-07-17

## The core finding

NEC conductor sizing is **application-driven**: the governing article, the
sizing multipliers, the required inputs, and the overcurrent-device rule all
change depending on *what you are wiring*. The current tool models only ONE
case correctly — a general branch circuit (load current -> ampacity -> OCPD
protects the conductor). For motors, HVAC, and dwelling feeders it gives the
wrong answer because those follow different rules.

Two concrete problems in the current architecture:

### Problem 1 — no application awareness
A motor circuit, an A/C unit, and a subpanel feeder are each sized by a
different NEC article. Example: a motor conductor is **125% of the table FLC**
(not the load you'd type in), and its breaker is **250% of FLC** (an
inverse-time breaker deliberately oversized for inrush) — the breaker does NOT
protect the conductor from overload (that's a separate overload device). The
current tool would size the breaker to "protect the conductor," which is simply
wrong for a motor.

### Problem 2 — termination temperature (110.14(C)) is not modeled
This is the #1 source of the "why does insulation rating matter" confusion. Per
110.14(C): you may use the 90 C column only for *derating math*; the final
ampacity is limited by the **termination** rating (60 C for some small/≤100 A
cases, **75 C in most real equipment**). Correct ampacity =
`min(90C_column × derates, termination_column_ampacity)`. The current tool just
uses whichever insulation column the user picks — so it can overstate ampacity
and it makes users choose a value (60/75/90) they don't understand.

## Verified application rules (sources cross-checked 2026-07-17)

| Application | NEC article | Conductor rule | OCPD rule | Key input(s) |
|---|---|---|---|---|
| General branch circuit | 210, 240 | ampacity ≥ load (×1.25 if continuous) | protects conductor (240.4, 240.6) | load A, continuous? |
| Feeder / subpanel | 215, 310.12 | like branch; **dwelling 83% rule** (100–400 A services/feeders) | protects conductor | load A, dwelling? |
| Motor | 430 | **125% of table FLC** (430.22; FLC from Tables 430.247–.250, NOT nameplate) | **250% of FLC** inverse-time breaker (430.52); overload separate (430.32) | HP or FLC, voltage, phase |
| A/C & refrigeration | 440 | ampacity ≥ nameplate **MCA** | ≤ nameplate **MOCP** | MCA, MOCP |
| EV charger | 625 | continuous ×1.25 | protects conductor | load A |
| Solar PV | 690 | (existing tool) | (existing tool) | link out |
| DC automotive/marine | ABYC | (existing tool) | (existing tool) | link out |

Sources: NEC 430.52/430.22 (motor); 110.14(C) (terminations); 310.12 (dwelling
83%); 440 (MCA/MOCP). Numbers to be re-verified per-cell at build time; tool
stays Experimental until human-verified.

## Proposed architecture: "What are you wiring?" mode

A top-level **application selector** reconfigures the tool:
- **Inputs shown** adapt (motor: HP + voltage + phase; A/C: MCA + MOCP; branch:
  load + continuous).
- **Rules applied** switch to the right article (conductor multiplier, OCPD
  rule, overload note).
- **Guidance surfaced** is application-specific (motor: "breaker is 250% and
  does NOT protect the conductor — overload is separate"; feeder: "dwelling 83%
  option"; termination-temperature defaults).
- **Decision output** names the governing rule + article, so it reads as a
  decision, not a bare number.

### The termination-temperature fix (applies to all applications)
Replace the single confusing "Insulation Rating (60/75/90)" selector with:
- **Termination rating**: 60 C / 75 C (default **75 C** — the common case).
- **Wire insulation**: 75 C (THWN) / 90 C (THHN/XHHW-2), for derating headroom.
Compute ampacity = `min(90C_ampacity × temp × bundling, termination_column)`.
This is the correct NEC method and makes the two settings self-explanatory
(one is "what your breaker/lugs are rated for", the other is "the wire you're
pulling").

## Phased build plan

**Phase 1 — termination-temperature correctness (do first).**
Fix 110.14(C) in the existing engine + UI. Benefits every application, removes
the insulation confusion, and is a self-contained correctness win. Add tests
(e.g., 90 C wire on 75 C terminations is limited to the 75 C column).

**Phase 2 — application selector shell.**
Add the "What are you wiring?" dropdown with: General branch, Feeder/subpanel,
Motor, A/C & HVAC, EV charger (+ links to Solar and DC tools). Start with the
branch/feeder/EV cases (small rule deltas) driving inputs, defaults, and copy.

**Phase 3 — motor & HVAC specializations.**
Motor: HP + voltage + phase -> FLC lookup (Tables 430.248/430.250), 125%
conductor, 430.52 breaker, overload note. A/C: MCA/MOCP inputs. These are the
biggest correctness wins and the highest-intent SEO queries ("motor wire size
calculator", "how to size wire for AC unit").

**Phase 4 — dwelling 310.12 (83%) option** on the feeder application, with the
Table 310.12 shortcut sizes.

## Why this is the right direction (not over-engineering)
- It matches how the NEC is actually organized and how electricians think.
- It turns a generic ampacity calculator into a **decision tool** ("I have a
  5 HP 240 V motor" -> full correct answer with the governing rule).
- Each application is a sharp SEO landing target.
- Phase 1 alone fixes a real correctness bug regardless of the rest.

## Open questions
- One tool with an application selector, or separate pages per application
  (like the wire-family split)? Recommendation: **one NEC tool with a selector**
  (the rule deltas are smaller than the shared UI; separate pages only for
  genuinely different standards like Solar/DC, which are already split).
- How far to take motor/HVAC now vs. after Phase 1 ships.
