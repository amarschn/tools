# MJF Buy vs. Outsource Monte Carlo

### Purpose of This Tool

This tool helps manufacturing teams evaluate whether to purchase Multi Jet Fusion
(MJF) printers or continue outsourcing production. It runs a Monte Carlo
simulation to estimate annual savings, probability of reaching break-even, and
the build volume required to recover the capital investment under realistic
uptime, labour, and ancillary infrastructure constraints.

### Requirements

#### Python Logic

* Core calculations live in `pycalcs/manufacturing.py` as the function
  `simulate_mjf_breakeven(...)`.
* The function must return a mapping compatible with the UI, including
  substituted equation strings for progressive disclosure.
* The simulation must:  
  - Sample annual demand and uptime variability.  
  - Account for downtime events and operator availability.  
  - Combine print/cooldown cycle time with labour capacity to limit throughput.  
  - Track cumulative cash flow and generate a representative event log for the best machine count.  
  - Compare internal costs against outsourcing for multiple machine counts while incorporating ancillary capital and annual support costs.

#### UI

* Provide form controls for all model parameters (machine cost, demand stats,
  uptime assumptions, cycle time, labour limits, turnaround targets, support
  capital, annual OPEX, and hybrid sourcing share).
* Display the key metrics for the highest-value machine count, including annual
  savings distribution, break-even statistics, and turnaround deltas.
* Present a detailed per-machine summary list, a cash-flow envelope chart, and an
  annual event log for a representative Monte Carlo run.
* Plot the outsourced-only, in-house, and hybrid cumulative cost curves using Plotly.
* Allow exporting of the full results payload.
* Render numbered equations with variable legends that align with the Python
  docstring.
